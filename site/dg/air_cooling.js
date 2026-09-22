/* 風扇與氣冷模組 —— docs/diagram_plan.md 的第 6 張（族群 `air_cooling`、ai_server 鏈）
   規格書：docs/diagram_specs/air_cooling.md

   ★ 2026-09-22 v2（DECISIONS #238／#239 的最終風格）：
     · 主角改成**沿轉軸的垂直爆炸拆解**：一顆反轉雙轉子風扇由前到後拆成 前扇框 → 前轉子 → 馬達 →
       軸承 → 後轉子 五層，每一層是一片斜投影的圓盤（scale(1,.42)），層與層之間留呼吸空間、
       中軸一條虛線 ＋ 一根貫穿的軸，看得出「怎麼疊回去」；兩組轉子真的在轉、旋向相反。
     · 右上是**一股氣流走完全程**：前面板進氣 → 風扇牆（N+1）→ 導風罩 → 鰭片（疏／密兩種鰭距）→
       後方排氣；熱從晶片 → VC → 熱管 → 鰭片往上走，跟氣流在鰭片處垂直交會（§6-A5）。
     · 右下是 **P-Q 曲線**（這張圖的命題：靜壓比風量重要）—— 座標軸刻意不標數值（§6-Q3）。
     · 十二張說明卡片全部外掛成 HTML（`extRow` 傳 `side`），畫布收到 680 寬；
       軸承四型、軸流 vs 離心、噪音、混合散熱、結論框與流程列收進三段章節（`D.fold()`）。
     · 每張卡片帶 `data-dgcolor`＝那個零件的材質色（鋁／不鏽鋼／銅／磁鐵紫／冷側藍）。
     · 材質走 `D.fx`（`glass`／`beam`／`glowDefs`，diagrams.js 檔尾，波 1b 定的介面；圓盤用它的 class 拼）：
       feGaussianBlur 只掛在穿過導風罩的三條氣流光暈上（#239 的 ≤3），其餘 beam 一律 glow:false。

   ★ 型式：2D／2.5D，**不做真 3D**（規格書 §0 已寫死，`scene: null`）。
     ⚠ 規格書 §0 特別點名一種**假的 3D 理由**：「風扇會轉，所以做 3D 比較生動」——
       那不是理由。「轉起來」是**動畫**，2D／2.5D 一樣做得到（下面的轉子就是 CSS 旋轉），
       跟「要不要真 3D」是兩件事。

   ★ 這張圖跟 `liquid_cooling.js` 是一對，不是競爭關係：
       · 液冷那張的結論之一是「冷板只貼最熱的那幾顆，其餘靠氣流」，這張負責把它畫出來（章節 ③）；
       · 「液冷帶走多少比例的熱」兩張用**同一個字串常數** `SHARE_LINES`（air §7-B2 ＝ liquid §7-B3）；
       · `heatpipe` / `vc` 兩個 data-part 的字串兩張**刻意相同**（規格書 §7-D2）；
       · 冷＝進氣、暖＝排氣的顏色語意與液冷的進／出水側相同（`--dg-cold` / `--dg-hot`）。

   ★ 紅線（這張比另外兩張多一條，因為公開資料品質最弱 —— 規格書 §6-N2）：
       **畫面上一個風扇規格數字都不寫** —— 轉速、CFM、mmH₂O、dBA 全禁。
       另外：軸承壽命的小時數一個都不寫（來源自相矛盾，FDB 竟然低於滾珠，§7-B3）；
       P-Q 曲線的座標軸不標任何數值（§6-Q3）；一櫃的風扇顆數只寫「數百顆」（§7-B4）；
       良率、成本、市占率一個都不寫（§6-N1）。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || !DG.register) return;
  const { STYLE, processBar, extRow, fold, shadow, fx } = DG;

  const SEG = 'thermal';        // 散熱（均熱片 / 液冷）—— ai_server 鏈，YAML 裡查證過存在
  const SEG_A = 'assembly';     // 系統組裝 / 機櫃 —— 只有機殼襯景與流程列的進氣／排氣掛它

  /* ★ 兩張圖共用的那一句（規格書 air §7-B2 ＝ liquid §7-B3）。
     `liquid_cooling.js` 裡有一份**一字不差**的複本 —— 改一邊要改另一邊。
     兩行都掛 `data-share`，驗收會把兩張圖這幾個元素的文字接起來做字串比對。*/
  const SHARE_LINES = ['多數熱由冷板帶走（公開資料約在 7～8 成之間，', '各來源分母不同），其餘仍靠氣流'];
  const shareText = (x, y) => SHARE_LINES.map((s, i) =>
    `<text class="sub" data-share="1" x="${x}" y="${y + i * 18}">${s}</text>`).join('');

  // 這張圖自己的規則（class），色值一律在 index.html 的 --dg-*（art-director 擁有）
  const VARS = `<style>
    .dgair .fine{font-size:var(--dg-fs-min,12px);fill:var(--dg-ink-3,#8ea0c4)}
    .dgair .axis2{stroke:var(--dg-mute);stroke-width:1;stroke-dasharray:3 5;fill:none;opacity:.55}
  </style>`;

  const P = (part, inner, seg) => `<g data-seg="${seg || SEG}" data-part="${part}">${inner}</g>`;
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點；卡片跟零件共用同一個 data-part。
     `color`＝元件色：地基只把它搬到卡片上，這裡順手也寫到 .anc，圓點／色條／引線端點才是同一個顏色。*/
  const card = (o) => {
    const s = extRow({ seg: o.seg === null ? undefined : (o.seg || SEG), part: o.part, title: o.title, sub: o.sub,
      no: o.no, side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };
  /* 流程列補 data-part（規格書 §7-D2）。processBar 卡片化之後開頭是 `<g class="step lrow" data-seg=`，
     舊 regex 對不到 —— main 上「每一個零件都有 data-part」那條一直是紅的，這裡改成對新的開頭。*/
  const pbar = (x, y, steps, w, opts) => {
    let i = 0;
    return processBar(x, y, steps, w, opts)
      .replace(/<g class="step lrow" data-seg="/g, () => `<g class="step lrow" data-part="flow${i++}" data-seg="`);
  };
  const C = { alu: 'var(--dg-alu)', steel: 'var(--dg-steel)', cu: 'var(--dg-cu-lit)', mag: 'var(--dg-mag)', cold: 'var(--dg-cold)', hot: 'var(--dg-hot)', culit: 'var(--dg-cu-lit)' };

  const RAD = Math.PI / 180;
  const pt = (cx, cy, r, a) => `${(cx + r * Math.cos(a * RAD)).toFixed(1)},${(cy + r * Math.sin(a * RAD)).toFixed(1)}`;
  /* 一片扇葉：從輪轂（r0）長到葉尖（r1），而且**從根到尖掃過 sweep 度**。
     那個掃角就是「扇葉有傾角、不是平板」在正面投影上唯一看得見的樣子（§6-F2）——
     掃角為 0 就變成直直的平板，也就看不出旋向。
     `dir` 取 −1 就整組鏡射 ＝ 反轉雙轉子的後面那一組（§6-F4），
     所以傾角與旋向由**同一個常數**控制，不會改了一邊忘了另一邊。*/
  function blade(cx, cy, r0, r1, a, wid, sweep, dir) {
    const s = dir * sweep, w = dir * wid, rm = (r0 + r1) / 2;
    return `M${pt(cx, cy, r0, a)}`
      + `A${r0},${r0} 0 0 ${dir > 0 ? 1 : 0} ${pt(cx, cy, r0, a + w)}`
      + `Q${pt(cx, cy, rm, a + w + s * 0.45)} ${pt(cx, cy, r1, a + w + s)}`
      + `A${r1},${r1} 0 0 ${dir > 0 ? 0 : 1} ${pt(cx, cy, r1, a + s)}`
      + `Q${pt(cx, cy, rm, a + s * 0.45)} ${pt(cx, cy, r0, a)}Z`;
  }
  /* 一整組轉子：葉片都從輪轂長出來（§6-F1），片數是示意（§7-B6：查不到「幾片最好」）。
     ⚠ `.dg .spin` 已經是 transform-box:fill-box / transform-origin:center，**不准再寫 transform-origin 像素值**；
       補一個透明同心圓把邊界框撐成正圓，中心才精準落在轉軸上。*/
  function rotor(cx, cy, r0, r1, n, dir, spin, dur) {
    const a = [`<circle cx="${cx}" cy="${cy}" r="${r1}" fill="none"/>`];
    for (let i = 0; i < n; i++) a.push(`<path class="part" fill="var(--dg-alu)" d="${blade(cx, cy, r0, r1, i * 360 / n, 34, 26, dir)}"/>`);
    return `<g class="${spin === false ? '' : 'spin'}" style="animation-duration:${dur || 2.2}s${dir < 0 ? ';animation-direction:reverse' : ''}">${a.join('')}</g>`;
  }

  function airCooling() {
    const CW = 680;
    // ================================================================ ① 一顆風扇沿轉軸拆開（2.5D 斜投影的圓盤，一層一層）
    const K = 0.42, AX = 170;                        // 圓盤壓扁的比例、中軸的 x
    const Y = { frame: 100, rot1: 180, motor: 250, brg: 302, rot2: 360 };
    // 一片有厚度的圓盤：先畫側壁（下半圈往下拉 T），再畫頂面；inner 畫在頂面座標（未壓扁）裡
    /* 玻璃材質走共用的 D.fx（diagrams.js 檔尾，波 1b 定的介面）：板＝fx.glass、流動＝fx.beam、濾鏡＝fx.glowDefs。
       圓盤（沿轉軸拆開的東西）fx 沒有現成的，這裡用 fx 的 class（fxg／fxb／fxs／fxe／fxr）拼一個：
       側壁（下半圈往下拉 T）＋ 頂面 ＋ sheen ＋ 邊光；inner 畫在頂面座標（未壓扁）裡。*/
    const disc = (cy, r, T, fill, inner) => `<g class="fxg" style="--fxc:${fill}" transform="translate(${AX},${cy}) scale(1,${K})">`
      + `<path class="fxb" d="M${-r},0V${T}A${r},${r} 0 0 0 ${r},${T}V0Z"/><path class="fxr" d="M${-r},0V${T}A${r},${r} 0 0 0 ${r},${T}V0Z"/>`
      + `<circle class="fxb part" r="${r}"/><circle class="fxs" r="${r}"/><circle class="fxe" r="${r}"/>${inner || ''}</g>`;
    /* 前扇框：方形外框、圓形風道、四角鎖孔 —— 「這是鎖在機殼上的工業件」的第一個記號，
       家用電風扇的網罩、立柱、擺頭一律不畫（§6-M1）。*/
    const frame = (() => {
      const S = 75, T = 20, H = 66;
      const sq = (o) => `M${-S + 14},${-S + o}h${2 * S - 28}a14,14 0 0 1 14,14v${2 * S - 28}a14,14 0 0 1 -14,14h-${2 * S - 28}a14,14 0 0 1 -14,-14v-${2 * S - 28}a14,14 0 0 1 14,-14Z`;
      const hole = `M${H},0A${H},${H} 0 1 0 ${-H},0A${H},${H} 0 1 0 ${H},0Z`;
      const holes = [[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sy]) => `<circle cx="${sx * (S - 13)}" cy="${sy * (S - 13)}" r="5" fill="var(--dg-void)"/>`).join('');
      return `<g class="fxg" style="--fxc:var(--dg-alu)" transform="translate(${AX},${Y.frame}) scale(1,${K})">`
        + `<path fill="var(--dg-alu-3)" d="${sq(T)}"/>`
        + `<path class="fxb part" fill-rule="evenodd" d="${sq(0)} ${hole}"/>`
        + `<path class="fxs" fill-rule="evenodd" d="${sq(0)} ${hole}"/><path class="fxe" fill-rule="evenodd" d="${sq(0)} ${hole}"/>`
        + `<path class="fxh" d="M${-S + 16},${-S + 1}H${S - 16}"/>${holes}</g>`;
    })();
    /* 轉子：輪轂是一個短圓柱、七片有傾角的扇葉從它長出來；整組真的在轉（CSS spin，動畫鈕關掉就停）。
       後面那組 dir 取 −1：葉片鏡射、轉向相反（§6-F4）。旋向另外用一個弧形箭頭標出來。*/
    const rotorLayer = (cy, dir, part) => {
      const arcA = dir > 0 ? 200 : 340, arcB = dir > 0 ? 250 : 290;
      const arrow = dir > 0
        ? `<path d="M${pt(0, 0, 76, arcA)}A76,76 0 0 1 ${pt(0, 0, 76, arcB)}" stroke="var(--dg-cold)" stroke-width="1.8" fill="none"/><path d="M${pt(0, 0, 76, arcB)}l-9,-6l-2,10Z" fill="var(--dg-cold)"/>`
        : `<path d="M${pt(0, 0, 76, arcA)}A76,76 0 0 0 ${pt(0, 0, 76, arcB)}" stroke="var(--dg-hot)" stroke-width="1.8" fill="none"/><path d="M${pt(0, 0, 76, arcB)}l9,-6l2,10Z" fill="var(--dg-hot)"/>`;
      return P(part, `<g transform="translate(${AX},${cy}) scale(1,${K})">`
        + `<path fill="var(--dg-hub-dim)" d="M-28,0V22A28,28 0 0 0 28,22V0Z"/>`
        + rotor(0, 0, 28, 64, 7, dir, true, dir > 0 ? 2.2 : 2.4)
        + `<g class="fxg" data-seg="${SEG}" data-part="hub"><circle class="part" r="28" fill="url(#acHub)"/><circle class="fxs" r="28"/><circle r="7" fill="var(--dg-steel-2)"/></g>`
        + arrow + `</g>`);
    };
    // 馬達：轉子磁鐵環（外圈）＋ 定子線圈（內，六個銅繞組）＋ 鐵芯 —— 藏在輪轂裡（§6-F3）
    const motor = disc(Y.motor, 30, 16, 'var(--dg-mag)',
      `<circle r="22" fill="var(--dg-frame)"/>`
      + [0, 1, 2, 3, 4, 5].map(i => `<rect x="-4" y="-21" width="8" height="13" rx="1.5" fill="var(--dg-cu)" transform="rotate(${i * 60})"/>`).join('')
      + `<circle r="6" fill="var(--dg-steel)"/>`);
    // 軸承：小小一圈，套在軸上、卡在軸與輪轂之間（四型的差別收在章節 ②）
    const bearing = disc(Y.brg, 13, 8, 'var(--dg-steel)', `<circle r="5" fill="var(--dg-void)"/>`);
    // 貫穿的軸（畫在圓盤後面，穿過軸承的孔）
    const shaft = `<rect x="${AX - 3}" y="${Y.rot1 + 6}" width="6" height="${Y.rot2 - Y.rot1 - 14}" rx="3" fill="var(--dg-steel)"/>`;
    // 四線接頭：從前扇框左下角出來的四條線（電源／地／轉速回授／PWM，Intel 4-wire 規格；只寫四條各是什麼）
    const wires = `<rect x="86" y="${Y.frame + 24}" width="10" height="22" rx="2" fill="var(--dg-plug)"/>`
      + [['var(--dg-err)', 0], ['var(--dg-ink-3)', 1], ['var(--dg-cold)', 2], ['var(--dg-hot)', 3]].map(([c, i]) =>
        `<path d="M86,${Y.frame + 28 + i * 5}H62" stroke="${c}" stroke-width="2.2" fill="none"/>`).join('');
    const fan = shadow(`<path class="axis2" d="M${AX},44V${Y.rot2 + 40}"/>`
      + `<path d="M${AX - 4},44l4,8l4,-8Z" fill="var(--dg-cold)"/><path d="M${AX - 4},${Y.rot2 + 40}l4,8l4,-8Z" fill="var(--dg-hot)"/>`
      + `<text class="fine" x="${AX + 8}" y="54" style="fill:var(--dg-cold)">進氣（前）</text>`
      + `<text class="fine" x="${AX + 8}" y="${Y.rot2 + 50}" style="fill:var(--dg-hot)">出氣（後）</text>`
      + shaft
      + P('fan_frame', frame) + P('wire4', wires)
      + rotorLayer(Y.rot1, 1, 'blade')
      + P('motor', motor) + P('bearing', bearing)
      + rotorLayer(Y.rot2, -1, 'counter_rot'));

    // ================================================================ ② 一股氣流走完全程：進氣 → 風扇牆 → 導風罩 → 鰭片 → 排氣
    const RK = { x: 344, y: 52, w: 328, h: 200 };
    const FANS = { x: 392, ys: [60, 104, 148, 192], r: 18 };
    /* 風扇牆：一排 ≥3 顆、其中一顆標成備援（§6-W1），一定畫在鰭片**之前**（§6-A1）。*/
    const wall = FANS.ys.map((cy, i) => `<g class="fxg" style="--fxc:var(--dg-frame)"><circle class="fxb part" cx="${FANS.x}" cy="${cy}" r="${FANS.r}"/><circle class="fxs" cx="${FANS.x}" cy="${cy}" r="${FANS.r}"/><circle class="fxe" cx="${FANS.x}" cy="${cy}" r="${FANS.r}"/></g>`
      + rotor(FANS.x, cy, 5, 15, 7, 1, true, 2 + i * 0.25)).join('')
      + `<text class="fine" x="${FANS.x - 34}" y="${FANS.ys[3] + FANS.r + 8}" style="fill:var(--dg-warn)">備援（N+1）</text>`;
    const finStack = (x, n, gap, y0, h) => { const a = []; for (let i = 0; i < n; i++) a.push(fx.glass(x + i * gap, y0, Math.max(3, gap - 4), h, { fill: 'var(--dg-alu)', rx: 1, iso: { dx: 3, dy: -2 } })); return a.join(''); };
    const FIN = { y: 88, h: 90 };
    const air = P('rack', `<rect class="part" x="${RK.x}" y="${RK.y}" width="${RK.w}" height="${RK.h}" rx="8" fill="none" opacity=".5"/>`
      + [0, 1, 2, 3, 4, 5, 6].map(i => `<circle cx="${RK.x + 6}" cy="${RK.y + 26 + i * 26}" r="3" fill="var(--dg-void)"/>`).join('')
      + `<text class="fine" x="${RK.x + 8}" y="${RK.y - 6}" style="fill:var(--dg-cold)">進氣（前面板）</text>`
      + `<text class="fine" x="${RK.x + RK.w - 60}" y="${RK.y - 6}" style="fill:var(--dg-hot)">排氣（後）</text>`
      + `<text class="fine" x="${RK.x + 8}" y="${RK.y + RK.h - 6}" style="fill:var(--dg-ink-3)">機殼／托盤（襯景）</text>`, SEG_A)
      + P('fan_wall', wall)
      /* 導風罩：把氣流「圍」成一條路的薄殼（§6-W2），不是一塊擋板 —— 所以畫成收口的漏斗輪廓 */
      + P('shroud', `<path class="part" fill="none" stroke="var(--dg-alu-2)" stroke-width="2.2" stroke-dasharray="6 4" d="M420,80H470l30,16v94l-30,16H420"/>`)
      + P('fin', `<rect class="part" x="507" y="${FIN.y - 3}" width="129" height="${FIN.h + 6}" rx="3" fill="none"/>` + finStack(510, 6, 9, FIN.y, FIN.h) + finStack(572, 12, 5, FIN.y, FIN.h)
        + `<text class="fine" x="510" y="234">鰭距疏</text><text class="fine" x="580" y="234">鰭距密</text>`)
      + P('heatpipe', fx.glass(506, 184, 134, 10, { fill: 'var(--dg-cu)', cls: 'part', rx: 5 })
        + `<rect x="510" y="187" width="126" height="4" rx="2" fill="var(--dg-vap)"/>`)
      + P('vc', fx.glass(540, 198, 70, 10, { fill: 'var(--dg-cu)', cls: 'part', rx: 2, iso: { dx: 6, dy: -4 } })
        + `<rect x="544" y="201" width="62" height="4" fill="var(--dg-vap)"/>`
        + fx.glass(560, 208, 30, 10, { fill: 'var(--dg-die)', rx: 2, iso: { dx: 6, dy: -4 } }))
      // 熱由下往上（晶片 → VC → 熱管 → 鰭片），氣流由左往右 —— 兩條路徑在鰭片處垂直交會（§6-A5）
      + [556, 575, 594].map((x, i) => `<path class="heat" d="M${x},196l-4,7h8Z" fill="var(--dg-hot)" style="animation-delay:${(i * 0.3).toFixed(1)}s"/>`
        + `<path class="heat" d="M${x},180l-4,7h8Z" fill="var(--dg-hot)" style="animation-delay:${(i * 0.3 + 0.9).toFixed(1)}s"/>`).join('')
      // 氣流：進氣端冷、排氣端暖，同一條線是漸變不是跳色（§6-A6）；全程單向由前到後（§6-A2）
      /* 穿過導風罩的三條氣流是全圖**唯三**掛 feGaussianBlur 的元素（#239 的 ≤3 上限），其餘 beam 一律 glow:false */
      + [96, 128, 160].map((y) => fx.beam(`M${RK.x + 12},${y}H${FANS.x - 22}`, { color: 'var(--dg-cold)', w: 2.4, glow: false, flow: true })
        + fx.beam(`M${FANS.x + 22},${y}H506`, { color: 'url(#acAir)', w: 2.4, glow: true, flow: true })
        + fx.beam(`M634,${y}H${RK.x + RK.w - 6}`, { color: 'var(--dg-hot)', w: 2.4, glow: false, flow: true })
        + `<path d="M${RK.x + RK.w - 10},${y - 5}l10,5l-10,5Z" fill="var(--dg-hot)"/>`).join('')
      // 一顆空氣粒子跑完全程（SMIL，動畫鈕關掉就凍住；路徑相對起點，靜態時就待在流線上）
      + `<g transform="translate(${RK.x + 12},128)"><circle r="3.5" fill="var(--dg-flow-dot)" opacity=".9"><animateMotion dur="4.5s" repeatCount="indefinite" path="M0,0H${RK.w - 20}"/></circle></g>`
      + `<text class="fine" x="${RK.x}" y="266">離開鰭片後還會掃過記憶體、VRM、電源，再從後方排出</text>`;

    // ================================================================ ③ P-Q 曲線（座標軸不標數值，§6-Q3）
    const QX = 372, QY0 = 310, QY1 = 422, QX1 = 660;
    const pq = P('pq_curve', `<path class="axis" d="M${QX},${QY0 - 6}V${QY1}H${QX1}" style="stroke-dasharray:none;stroke:var(--dg-axis)"/>`
      + `<text class="fine" x="${QX + 8}" y="${QY0 - 2}">靜壓 ↑</text>`
      + `<text class="fine" x="${QX1 - 44}" y="${QY1 + 16}">風量 →</text>`
      // 離心：靜壓端高、風量端小；軸流：靜壓端低、風量端大（§6-Q2，畫成一樣或反過來＝不過）
      + `<path d="M${QX},${QY0} C${QX + 60},${QY0 + 10} ${QX + 100},${QY0 + 44} ${QX + 128},${QY1}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
      + `<path d="M${QX},${QY0 + 28} C${QX + 70},${QY0 + 30} ${QX + 130},${QY0 + 36} ${QX + 168},${QY0 + 44} S${QX + 240},${QY0 + 90} ${QX + 268},${QY1}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
      // 系統阻抗曲線：從原點往右上（阻力越大、同樣風量要的靜壓越高）；跟風扇曲線的交點才是工作點（§6-Q1）
      + fx.beam(`M${QX},${QY1} Q${QX + 138},${QY1 - 12} ${QX + 184},${QY0 + 4}`, { color: 'var(--dg-ink-2)', w: 2.2, glow: false, flow: true })
      + `<circle cx="${QX + 164}" cy="${QY0 + 41}" r="6" fill="none" stroke="var(--dg-warn)" stroke-width="2.4"/>`
      + `<text class="fine" x="${QX + 178}" y="${QY0 + 26}" style="fill:var(--dg-warn)">工作點</text>`
      + `<text class="fine" x="${QX + 60}" y="${QY0 + 8}" style="fill:var(--dg-hot)">離心</text>`
      + `<text class="fine" x="${QX + 226}" y="${QY0 + 96}" style="fill:var(--dg-cold)">軸流</text>`
      + `<text class="fine" x="${QX + 192}" y="${QY0 - 2}" style="fill:var(--dg-ink-2)">系統阻抗曲線</text>`
      + `<text class="fine" x="${QX}" y="${QY1 + 16}">座標軸刻意不標數值，只畫關係</text>`);

    // ================================================================ 章節 ②：軸承四型（2×2，同一根軸）
    const BC = { w: 324, h: 156, y0: 486 };
    const bx0 = (i) => 16 + (i % 2) * 332, by0 = (i) => BC.y0 + Math.floor(i / 2) * 168;
    /* ★ 四格一定要**共用同一個「畫軸」的函式**，只換內部細節 —— 這一行就是 §6-B1。
       不同基準畫出來就比不出差別，那正是這四格唯一存在的理由。*/
    function bearingCell(i, title, kind, lines) {
      const cx = bx0(i), cy = by0(i), x = cx + 20, y = cy + 50, w = BC.w - 40;
      const SH = 14;                                   // 軸的粗細：四格完全一樣
      const sh = `<rect x="${x}" y="${y + 30}" width="${w}" height="${SH}" rx="3" fill="var(--dg-steel)"/>`;
      let inner = '';
      if (kind === 'sleeve') {                          // 含油：軸與襯套**直接接觸**
        inner = `<rect x="${x}" y="${y + 18}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`;
      } else if (kind === 'ball') {                     // 滾珠：**看得到鋼珠**
        const balls = [];
        for (let k = 0; k < 10; k++) balls.push(`<circle cx="${x + 12 + k * ((w - 24) / 9)}" cy="${y + 22}" r="6" fill="var(--dg-steel)"/>`
          + `<circle cx="${x + 12 + k * ((w - 24) / 9)}" cy="${y + 52}" r="6" fill="var(--dg-steel)"/>`);
        inner = `<rect x="${x}" y="${y + 8}" width="${w}" height="8" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 58}" width="${w}" height="8" rx="2" fill="var(--dg-alu-2)"/>${balls.join('')}`;
      } else if (kind === 'fdb') {                      // 流體動壓：油膜 ＋ 襯套上有溝槽
        const gr = [];
        for (let k = 0; k < 12; k++) gr.push(`<path d="M${x + 10 + k * ((w - 20) / 11)},${y + 12}l7,8" stroke="var(--dg-void)" stroke-width="2" fill="none"/>`
          + `<path d="M${x + 10 + k * ((w - 20) / 11)},${y + 62}l7,-8" stroke="var(--dg-void)" stroke-width="2" fill="none"/>`);
        inner = `<rect x="${x}" y="${y + 10}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 52}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>${gr.join('')}`
          + `<rect x="${x}" y="${y + 22}" width="${w}" height="8" fill="var(--dg-oil)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="8" fill="var(--dg-oil)"/>`;
      } else {                                          // 磁浮：軸與襯套之間**有可見空隙**
        inner = `<rect x="${x}" y="${y + 4}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 58}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 16}" width="${w}" height="14" fill="var(--dg-void)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="14" fill="var(--dg-void)"/>`
          + [0, 1, 2, 3, 4, 5, 6].map(k => `<text class="fine" x="${x + 14 + k * 42}" y="${y + 28}" style="fill:var(--dg-mag)">N</text>`
            + `<text class="fine" x="${x + 14 + k * 42}" y="${y + 56}" style="fill:var(--dg-mag)">S</text>`).join('');
      }
      return P('brg_' + kind, `<rect class="frame" x="${cx}" y="${cy}" width="${BC.w}" height="${BC.h}" rx="8"/>`
        + `<text class="hd" x="${cx + 14}" y="${cy + 22}">${title}</text>`
        + `<text class="fine" x="${cx + 14}" y="${cy + 42}">${lines[0]}</text>`
        + inner + sh
        + lines.slice(1).map((s, k) => `<text class="fine" x="${cx + 14}" y="${cy + 130 + k * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join(''));
    }

    // ================================================================ 章節 ③：軸流 vs 離心 ＋ 噪音 ＋ 混合散熱
    const AY = 870;
    const cell3 = (x, w, t) => `<rect class="frame" x="${x}" y="${AY}" width="${w}" height="212" rx="8"/><text class="hd" x="${x + 14}" y="${AY + 22}">${t}</text>`;
    const lines3 = (x, ls) => ls.map((s, k) => `<text class="fine" x="${x + 14}" y="${AY + 160 + k * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('');
    const axialCell = P('axial', cell3(16, 210, '軸流（axial）')
      + `<rect x="40" y="${AY + 46}" width="160" height="72" rx="6" fill="var(--dg-frame)" stroke="var(--dg-alu-2)"/>`
      + rotor(120, AY + 82, 12, 30, 7, 1, true, 2.4)
      + `<path class="flow fast" d="M24,${AY + 82}H38" stroke="var(--dg-cold)" stroke-width="3.2" fill="none"/>`
      + `<path class="flow fast" d="M202,${AY + 82}H216" stroke="var(--dg-hot)" stroke-width="3.2" fill="none"/>`
      + `<path d="M212,${AY + 77}l8,5l-8,5Z" fill="var(--dg-hot)"/>`
      + lines3(16, ['進氣與出氣同一個方向（0°）', '風量大，但一遇到阻力就掉得快', '機殼裡大部分位置用這一種']));
    /* 離心／鼓風：**沿軸進、轉 90° 從側面（這裡是往上）出**（§6-A3／3-C）。
       畫成沿軸出＝那就是軸流扇 —— 出風口一定畫在另一個方向，並補一個直角記號把「90°」講死。*/
    const BCx = 344, BCy = AY + 100;
    const centCell = P('centrifugal', cell3(238, 210, '離心／鼓風（blower）')
      + `<rect class="part" x="${BCx - 22}" y="${AY + 40}" width="44" height="32" rx="3" fill="var(--dg-frame)"/>`
      + `<circle class="part" cx="${BCx}" cy="${BCy}" r="40" fill="var(--dg-frame)"/>`
      + `<rect class="part" x="${BCx - 76}" y="${BCy - 15}" width="34" height="30" rx="3" fill="var(--dg-frame)"/>`
      + rotor(BCx, BCy, 10, 27, 9, 1, true, 2.0)
      + `<path class="flow fast" d="M${BCx - 96},${BCy}H${BCx - 48}" stroke="var(--dg-cold)" stroke-width="3.2" fill="none"/>`
      + `<path d="M${BCx - 52},${BCy - 5}l8,5l-8,5Z" fill="var(--dg-cold)"/>`
      + `<path class="flow fast" d="M${BCx},${AY + 52}V${AY + 30}" stroke="var(--dg-hot)" stroke-width="3.2" fill="none"/>`
      + `<path d="M${BCx - 5},${AY + 38}l5,-9l5,9Z" fill="var(--dg-hot)"/>`
      + `<path d="M${BCx + 6},${AY + 58}v12h-12" stroke="var(--dg-warn)" stroke-width="1.4" fill="none"/>`
      + `<text class="fine" x="${BCx + 30}" y="${AY + 54}" style="fill:var(--dg-warn)">90°</text>`
      + lines3(238, ['沿軸進、轉 90° 從側面出', '同尺寸下靜壓比軸流高，', '適合又彎又擠的路徑']));
    const bpf = (() => {
      const x0 = 470, y0 = AY + 40, y1 = AY + 126;
      const peaks = [0, 1, 2].map(i => `<path d="M${x0 + 34 + i * 54},${y1} V${y1 - (64 - i * 18)}" stroke="var(--dg-hot)" stroke-width="${5 - i}" fill="none"/>`
        + `<text class="fine" x="${x0 + 22 + i * 54}" y="${y1 - (70 - i * 18)}" style="fill:var(--dg-hot)">${i === 0 ? 'BPF' : (i + 1) + '×'}</text>`).join('');
      return P('bpf', cell3(460, 204, '噪音：葉片數 × 轉速')
        + `<path class="axis" d="M${x0},${y0}V${y1}H${x0 + 184}" style="stroke-dasharray:none;stroke:var(--dg-axis)"/>`
        + `<path d="M${x0},${y1 - 8}H${x0 + 180}" stroke="var(--dg-ink-3)" stroke-width="1.4" opacity=".5" fill="none"/>` + peaks
        + `<text class="fine" x="${x0 + 138}" y="${y1 - 4}">頻率 →</text>`
        + lines3(460, ['等距葉片把能量集中在這個', '頻率與它的諧波；排成不等距', '就攤成一片、不再是一根尖峰']));
    })();
    // 混合散熱：冷板只貼最熱的那幾顆、其餘零件仍靠氣流（§6-M2；液冷冷板只准出現在這一格，§6-M3）
    const HY = AY + 224;
    const hybrid = P('hybrid', `<rect class="frame" x="16" y="${HY}" width="648" height="150" rx="8"/>`
      + `<text class="hd" x="30" y="${HY + 22}">上了液冷，風扇不會變成零</text>`
      + `<rect x="34" y="${HY + 56}" width="196" height="12" rx="2" fill="var(--dg-pcb)"/>`
      + `<rect x="74" y="${HY + 36}" width="60" height="20" rx="3" fill="var(--dg-cu)"/>`
      + `<rect x="84" y="${HY + 56}" width="40" height="8" fill="var(--dg-die)"/>`
      + `<text class="fine" x="34" y="${HY + 88}" style="fill:var(--dg-cold)">冷板只貼 GPU／部分 CPU</text>`
      + [0, 1, 2, 3].map(i => `<rect x="${262 + i * 26}" y="${HY + 44}" width="16" height="24" rx="2" fill="var(--dg-die)"/>`).join('')
      + [0, 1, 2].map(i => `<path class="flow fast" d="M250,${HY + 38 + i * 14}H420" stroke="url(#acAir)" stroke-width="2.6" fill="none" style="animation-delay:${(i * 0.25).toFixed(2)}s"/>`).join('')
      + `<text class="fine" x="262" y="${HY + 88}" style="fill:var(--dg-hot)">記憶體／VRM／電源／光模組仍靠氣流</text>`
      + `<text class="fine" x="30" y="${HY + 112}">所以液冷機櫃裡還是有「數百顆」風扇。</text>`
      + shareText(30, HY + 130));

    // ================================================================ 說明框（章節 ④）
    const noteBox = (x, y, w, h, t, lines, part) => P(part,
      `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${y + 22}">${t}</text>`
      + lines.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 46 + i * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join(''));

    /* ================================================================ 組裝
       `dg1`：這張圖有兩個 seg（thermal ＋ assembly），`stampParts` 不會自動掛，所以自己掛 —— 作用是 `--dg-glow:none`。
       `rs`：已改造成風格系統（閱讀模式字級升一階、卡片外掛）。*/
    return `<svg class="dg dgm dgair dg1 rs" viewBox="0 0 ${CW} 1830" width="100%" style="display:block">${STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 3.5, soft: 3 })}
        <linearGradient id="acAir" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-cold)"/><stop offset="1" stop-color="var(--dg-hot)"/></linearGradient>
        <radialGradient id="acHub" cx="38%" cy="32%" r="72%">
          <stop offset="0" stop-color="var(--dg-hub-lit)"/><stop offset="1" stop-color="var(--dg-hub-dim)"/></radialGradient>
      </defs>

      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">氣冷：風扇賣的是「推得過去」，不是「吹得多」</text>
      <text class="cap ext" x="0" y="0">家用電風扇前面沒有東西擋，所以比的是風量；伺服器風扇要穿過密排鰭片與擠滿零件的機殼，比的是靜壓。</text>
      <text class="cap ext" x="0" y="0">左邊把一顆反轉雙轉子風扇沿著轉軸拆開（前扇框 → 前轉子 → 馬達 → 軸承 → 後轉子）；右上是一股氣流從前面板走到後方的完整路徑，右下是風壓—風量曲線。軸承四型、軸流與離心、噪音、混合散熱與誰做哪一塊收在下面三段。</text>
      <text class="cap ext" x="0" y="0">示意圖，非實物比例｜扇葉片數、鰭片數與軸承比例均為示意；P-Q 曲線為示意，座標軸不標數值。</text>

      <!-- ================= §1 主畫面（永遠看得到）：爆炸拆解 ＋ 氣流路徑 ＋ P-Q ================= -->
      <text class="hd" x="30" y="24">① 一顆風扇沿轉軸拆開</text>
      <text class="hd" x="${RK.x}" y="24">② 一股氣流走完全程</text>
      <text class="hd" x="${RK.x}" y="292">③ 風壓—風量（P-Q）：交點才是工作點</text>
      ${fan}
      ${air}
      ${pq}

      <!-- 左欄：拆開的那五層 ＋ 四線（錨點在每一層的左端）；右欄：氣流路徑 ＋ P-Q（錨點在右端） -->
      ${card({ part: 'fan_frame', no: 1, side: 'l', ax: 101, ay: Y.frame, color: C.alu, title: '扇框（四角鎖孔）', sub: '鎖在機殼上的工業件 —— 沒有網罩、立柱與擺頭，那是家用電風扇的事' })}
      ${card({ part: 'blade', no: 2, side: 'l', ax: 112, ay: Y.rot1, color: C.alu, title: '扇葉有傾角（片數為示意）', sub: '靠斜面把空氣往後推；葉片數與角度決定同一顆馬達能推出多少風、產生多少噪音' })}
      ${card({ part: 'motor', no: 3, side: 'l', ax: 146, ay: Y.motor, color: C.cu, title: '馬達藏在輪轂裡', sub: '定子線圈在內、轉子磁鐵在輪轂內壁；伺服器風扇長時間高速運轉，馬達要撐得住' })}
      ${card({ part: 'bearing', no: 4, side: 'l', ax: 160, ay: Y.brg, color: C.steel, title: '軸承：在軸與輪轂之間', sub: '含油／滾珠／流體動壓／磁浮四型決定壽命與噪音 —— 機房裡一顆風扇壞掉要有人去換，壽命是錢（四型見 ②）' })}
      ${card({ part: 'counter_rot', no: 5, side: 'l', ax: 112, ay: Y.rot2, color: C.alu, title: '反轉雙轉子（counter-rotating）', sub: '前後兩組葉片旋向相反，後面那組把前面甩出來的旋轉氣流「扶正」，同樣厚度下拉高靜壓' })}
      ${card({ part: 'wire4', no: 6, side: 'l', ax: 60, ay: Y.frame + 35, color: C.hot, title: '四線：電源／地／轉速回授／PWM', sub: '轉速回授讓主機知道這顆有沒有在轉（壞了會報警），PWM 讓主機依溫度調速' })}
      ${card({ part: 'fan_wall', no: 7, side: 'r', ax: FANS.x + FANS.r, ay: FANS.ys[0], color: C.cold, title: '風扇牆與 N+1', sub: '多算一顆，壞掉一顆時剩下的補得上；可以熱插拔 —— 機房不會為了換風扇關機' })}
      ${card({ part: 'shroud', no: 8, side: 'r', ax: 500, ay: 80, color: C.alu, title: '導風罩：把風「圍」到該去的地方', sub: '沒有它，風會走阻力最小的路，繞過最需要散熱的零件' })}
      ${card({ part: 'fin', no: 9, side: 'r', ax: 630, ay: 112, color: C.alu, title: '鰭片才是熱交給空氣的地方', sub: '風扇只是把空氣推過來。鰭越密面積越大，但阻力也越大 —— 又回到 P-Q 曲線' })}
      ${card({ part: 'heatpipe', no: 10, side: 'r', ax: 638, ay: 189, color: C.cu, title: '熱管：先把熱從晶片搬到鰭片', sub: '把熱沿一條線送走；內部是真空腔＋毛細層，不是實心銅（詳見液冷那張）' })}
      ${card({ part: 'vc', no: 11, side: 'r', ax: 608, ay: 203, color: C.culit, title: '均熱板 VC：把點熱源攤成一個面', sub: '當底座貼在晶片上，先攤平再交給熱管與鰭片；同樣是真空腔＋毛細層' })}
      ${card({ part: 'pq_curve', no: 12, side: 'r', ax: QX + 164, ay: QY0 + 41, color: C.hot, title: '風扇不是只有一個「風量」', sub: '同一顆風扇在不同阻力下吹出的量完全不同，風扇曲線與系統阻抗曲線的交點才是工作點。密排鰭片、儲存背板、GPU 隧道都是高阻抗，所以靜壓比風量重要 —— 這就是伺服器風扇跟家用風扇最根本的差別' })}
      ${card({ seg: null, warn: true, note: true, order: 99, side: 'r', title: '點零件篩到的是「供應鏈環節」，不是整個族群', sub: '散熱這一格目前收錄六家，族群有九檔；做風扇與熱管的尼得科超眾 6230、泰碩 3338、力致 3483、元山 6275 不在環節裡，點零件列不出它們。' })}

      <!-- ================= ② 軸承四型（預設收合；座標由 wireFolds 量） ================= -->
      ${fold('air2', '② 軸承四型：含油、滾珠、流體動壓、磁浮', '四格用同一根軸畫；有沒有鋼珠、有沒有油膜、有沒有空隙一眼分得開', `
        <text class="hd" x="16" y="468">軸承四型：四格用同一根軸畫，差別全部在剖面裡（畫面不寫任何壽命小時數 —— 來源自相矛盾）</text>
        ${bearingCell(0, '含油（sleeve）', 'sleeve', ['軸直接在襯套裡轉', '最便宜；潤滑油會耗損，', '★ 所以是四型裡最早變吵的'])}
        ${bearingCell(1, '滾珠（ball）', 'ball', ['兩圈鋼珠把軸撐起來', '壽命明顯長於含油，代價是本身有', '一點滾動噪音；伺服器常用這一型'])}
        ${bearingCell(2, '流體動壓（FDB）', 'fdb', ['襯套刻溝槽 ＋ 一層油膜', '轉起來把油擠成壓力油膜把軸浮起，', '幾乎沒有機械噪音，而且一生都不太變'])}
        ${bearingCell(3, '磁浮（maglev）', 'mag', ['軸與襯套之間有可見空隙', '用磁力把轉子浮起來，', '★ 沒有機械接觸，理論壽命最長'])}`)}

      <!-- ================= ③ 軸流 vs 離心 ＋ 噪音 ＋ 混合散熱 ================= -->
      ${fold('air3', '③ 軸流 vs 離心、噪音從哪裡來、上了液冷為什麼還要風扇', '兩種氣流幾何的 0° 與 90°、葉片數 × 轉速的那個「嗡」、冷板貼哪幾顆', `
        ${axialCell}${centCell}${bpf}${hybrid}`)}

      <!-- ================= ④ 結論框 ＋ 誰做哪一塊 ＋ 沒有回答的事 ＋ 流程列 ================= -->
      ${fold('air4', '④ 跟家用風扇差在哪、這張圖上誰做哪一塊、五格流程列', '靜壓 vs 風量的結論、九檔各自的主體產品、刻意不寫的數字、進氣到排氣的五格', `
        ${noteBox(16, 1290, 324, 206, '伺服器風扇跟家用風扇差在哪', [
          '家用風扇前面沒有東西擋，所以比的是風量；',
          '伺服器風扇要穿過密排鰭片與擠滿零件的機殼，',
          '比的是靜壓。',
          '所以它轉速高、輪轂大、葉片厚，而且常用反轉',
          '雙轉子。代價是吵與耗電 —— 這正是機櫃功率一',
          '上去就得考慮液冷的原因。',
          '★ 不要拿 U 數當散熱規格：1U／2U／4U 這種',
          '　 機殼代號不該被指派一個通用的風量或靜壓',
          '　 目標，兩台 1U 的工作點可以完全不同。',
        ], 'vs_home')}
        ${noteBox(340, 1290, 324, 206, '這張圖上誰做哪一塊（寫「主體是」）', [
          '風扇／鰭片／熱管／VC／氣冷模組 → 散熱環節。',
          '建準 2421＝伺服器風扇；雙鴻 3324＝氣冷模組',
          '與均熱片、奇鋐 3017＝散熱模組（氣冷、水冷',
          '都做）；健策 3653、一詮 2486＝封裝層級均熱片',
          '與補強框。',
          '★ 族群「氣冷與核心組件」9 檔裡，尼得科超眾',
          '　 6230（熱管、均熱板、3D VC）、泰碩 3338',
          '　 （熱管、均熱片、模組）、力致 3483（軸流與',
          '　 離心扇、熱管、均溫板）、元山 6275（風扇馬',
          '　 達與模組）不在散熱環節裡，點零件列不出。',
        ], 'who')}
        ${noteBox(16, 1508, 648, 152, '這張圖沒有回答的事', [
          '任何一顆風扇的轉速、風量、靜壓、噪音值：那是型號層級的東西，而且查到的來源',
          '多半是風扇廠與 PC 零件站的部落格 —— 一個都不寫。',
          '軸承壽命的小時數：查到的數字散得很開，而且 FDB 竟然低於滾珠，與同一批來源的',
          '定性結論互相矛盾 —— 只寫排序，不寫小時數。',
          '各家市占率、良率、單價：查不到可引用的公開數字，不編。',
          '鰭距的具體數值：查不到通用值，只畫疏／密對照。',
        ], 'unknown')}
        <text class="cap" x="16" y="1686">一條氣流走完全程（五格）　★ 風扇（格 2）一定在鰭片（格 4）之前；格 4 才是熱真正交給空氣的地方，風扇只是把空氣推過來</text>
        ${pbar(16, 1694, [
          { seg: SEG_A, t: '進氣', s: '前面板濾網／開孔' },
          { seg: SEG, t: '推動', s: '風扇牆（N+1）' },
          { seg: SEG, t: '導引', s: '導風罩／風道' },
          { seg: SEG, t: '交換', s: '鰭片 ＋ 熱管／VC' },
          { seg: SEG_A, t: '排氣', s: '後方出風' }], 200, { cols: 3 })}
        <text class="cap" x="16" y="1812">資料來源與信心度見 docs/diagram_specs/air_cooling.md。</text>`)}
    </svg>`;
  }

  window.DG.register('air_cooling', {
    level: 'group', chain: 'ai_server',
    name: '氣冷：風扇、風扇牆與散熱模組',
    draw: airCooling, native: 680, scene: null,
    q: '伺服器風扇跟家用風扇差在哪？為什麼都上液冷了，一櫃還是要幾百顆風扇？',
    /* ★ `parts` ＝ 點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       cos 只放代號，而且**只放 supply_chain.yaml 的 companies[].tech 欄自己寫了這個品項的公司**（R3）；
       tech 欄沒寫的就不列，改在 note／none 講清楚為什麼列不出來 —— 不為了讓卡片好看而湊一個對應（R5）。
       這張圖最大的落差在規格書 §7-D3：族群 9 檔、環節 6 家，做風扇與熱管的四家（超眾、泰碩、力致、元山）
       不在環節裡，所以熱管那一格會是「列不出來」，這是誠實的答案不是漏寫。*/
    parts: {
      fan_frame: { name: '扇框（frame／housing）', desc: '方形外框把風扇固定在機殼上，四角有鎖孔；中間的圓孔就是風道。沒有網罩、立柱、擺頭 —— 那是家用電風扇。', cos: ['2421'] },
      blade: { name: '前轉子：扇葉 ＋ 輪轂', desc: '七片有傾角的扇葉從輪轂長出來，靠斜面把空氣往後推；片數為示意（查不到「幾片最好」的通用結論）。', cos: ['2421'] },
      hub: { name: '輪轂（hub）', desc: '中央那個短圓柱，扇葉從它長出來、馬達藏在它裡面。伺服器風扇的輪轂比家用風扇大（馬達要有力）—— 這是外觀觀察，畫面不標比例數字。', cos: ['2421'] },
      motor: { name: '馬達（定子線圈 ＋ 轉子磁鐵）', desc: '藏在輪轂裡：外圈是轉子磁鐵環、裡面是定子的銅繞組與鐵芯。伺服器風扇長時間高速運轉，馬達要撐得住。', cos: ['2421'] },
      bearing: { name: '軸承（在軸與輪轂之間）', desc: '含油／滾珠／流體動壓／磁浮四型決定壽命與噪音；四型的剖面差別在章節 ②。畫面不寫任何壽命小時數（來源自相矛盾）。', cos: ['2421'] },
      counter_rot: { name: '後轉子（反轉雙轉子的第二組）', desc: '前後兩組葉片旋向相反，後面那組把前面甩出來的旋轉氣流「扶正」，同樣厚度下能拉高靜壓；常見於機櫃這類又窄又擠的地方。', cos: ['2421'] },
      wire4: { name: '四線接頭（電源／地／轉速回授／PWM）', desc: 'Intel 4-wire PWM 規格：＋12 V、接地、轉速回授（tach，開集極、每轉兩個脈衝）、PWM 控制。轉速回授讓主機知道它有沒有在轉，PWM 讓主機依溫度調速。', cos: ['2421'] },
      fan_wall: { name: '風扇牆（fan wall，N+1）', desc: '前面板與主機板托盤之間的一排風扇，提供跨全板的高壓氣流；多算一顆做備援，而且可以熱插拔。', cos: ['2421'] },
      shroud: { name: '導風罩（air shroud／duct）', desc: '把氣流圍成一條路的薄殼；沒有它，風會走阻力最小的路、繞過最需要散熱的零件。', cos: [], none: '供應鏈表沒有把導風罩列成任何一家的品項（它通常跟機殼或散熱模組一起出），所以這一格列不出台股 —— 不編一個對應。' },
      fin: { name: '散熱鰭片組（heat sink fin stack）', desc: '一疊等距薄片，熱在這裡交給空氣；鰭越密面積越大、阻力也越大。圖上畫疏／密兩種鰭距對照，鰭距的具體數值查不到通用值，不標。', cos: ['3324'], note: '供應鏈表 tech 欄寫「氣冷模組」的是雙鴻；奇鋐的 tech 欄只列水冷板／Sidecar／CDU／3D VC（族群 note 說它氣冷水冷都做，但 tech 欄沒寫，這裡不補）。' },
      heatpipe: { name: '熱管（heat pipe）', desc: '壓扁貼在底座上、把熱沿一條線送到鰭片；內部是真空腔＋毛細層，不是實心銅（跟液冷那張用同一個零件身分）。', cos: [], none: '散熱環節六家的 tech 欄沒有一家寫熱管。族群裡做熱管的尼得科超眾 6230、泰碩 3338、力致 3483 不在這個環節，所以列不出來 —— 這是族群與環節的落差（規格書 §7-D3），不是沒人做。' },
      vc: { name: '均熱板 VC（vapor chamber，當底座）', desc: '貼在晶片上把點熱源攤成一個面，再交給熱管與鰭片；內部同樣是真空腔＋毛細層＋支撐柱。', cos: ['3017'], note: '供應鏈表 tech 欄寫「3D VC 均熱板」的只有奇鋐；族群裡做均溫板的超眾、泰碩、力致不在這個環節。' },
      pq_curve: { name: '風壓—風量（P-Q）曲線', desc: '同一顆風扇在不同阻力下吹出的量完全不同；風扇曲線與系統阻抗曲線的交點才是工作點。座標軸刻意不標數值 —— 查到的數字來源等級不夠。', cos: ['2421'] },
      brg_sleeve: { name: '含油軸承（sleeve）', desc: '最便宜，軸直接在襯套裡轉。潤滑油會耗損，所以是四型裡最早變吵的。', cos: ['2421'] },
      brg_ball: { name: '滾珠軸承（ball）', desc: '兩圈鋼珠把軸撐起來，壽命明顯長於含油，代價是本身有一點滾動噪音；伺服器與長時間運轉的機器常用這一型。', cos: ['2421'] },
      brg_fdb: { name: '流體動壓軸承（FDB）', desc: '襯套上刻溝槽，轉起來把油擠成一層壓力油膜把軸浮起來；幾乎沒有機械噪音，而且噪音一生都不太變。', cos: ['2421'] },
      brg_mag: { name: '磁浮軸承（maglev）', desc: '用磁力把轉子浮起來，沒有機械接觸，所以理論壽命最長。畫面不寫小時數。', cos: ['2421'] },
      axial: { name: '軸流扇（axial）', desc: '進氣與出氣同一個方向（夾角 0°）。風量大，但一遇到阻力就掉得快；機殼裡大部分的位置用這一種。', cos: ['2421'] },
      centrifugal: { name: '離心／鼓風扇（centrifugal／blower）', desc: '沿軸進、轉 90° 從側面出。同樣尺寸下靜壓比軸流高，適合路徑又彎又擠的地方。', cos: ['2421'], note: '族群裡明列軸流扇與離心扇的力致 3483 不在散熱環節裡，列不出來。' },
      bpf: { name: '噪音：葉片通過頻率（BPF）', desc: '葉片數 × 轉速就是那個「嗡」的頻率；等距葉片把能量集中在這個頻率與它的諧波上，排成不等距就攤成一片。', cos: ['2421'] },
      hybrid: { name: '混合散熱：冷板貼 GPU、風扇吹其餘', desc: '冷板只貼在最熱的那幾顆（GPU／部分 CPU）上；記憶體、VRM、電源、光模組仍靠氣流，所以液冷機櫃裡還是有數百顆風扇。液冷帶走幾成熱：兩個來源分母不同，只寫區間。', cos: ['2421', '3324', '3017'] },
      vs_home: { name: '伺服器風扇跟家用風扇差在哪', desc: '家用比的是風量、伺服器比的是靜壓；所以轉速高、輪轂大、葉片厚、常用反轉雙轉子，代價是吵與耗電。不要拿 U 數當散熱規格。' },
      who: { name: '這張圖上誰做哪一塊', desc: '風扇／鰭片／熱管／VC／氣冷模組都在散熱環節；族群 9 檔裡有 4 家不在環節裡（超眾、泰碩、力致、元山），點零件列不出它們。' },
      unknown: { name: '這張圖沒有回答的事', desc: '風扇規格數字、軸承壽命小時數、市占率、良率、單價、鰭距 —— 來源等級不夠或查不到，一個都不寫。' },
      rack: { name: '機殼／托盤（襯景）', desc: '只畫輪廓不畫細節；氣流從前面板進、後方出，前面的一排孔就是進氣口。' },
      flow0: { name: '流程列：進氣', desc: '前面板濾網／開孔。' },
      flow1: { name: '流程列：推動（風扇牆 N+1）', desc: '多算一顆、可熱插拔；風扇只是把空氣推過來。', cos: ['2421'] },
      flow2: { name: '流程列：導引（導風罩／風道）', desc: '把氣流圍到該去的地方。', cos: [], none: '供應鏈表沒有把導風罩列成任何一家的品項。' },
      flow3: { name: '流程列：交換（鰭片 ＋ 熱管／VC）', desc: '這一格才是熱真正交給空氣的地方。', cos: ['3324', '3017'] },
      flow4: { name: '流程列：排氣', desc: '後方出風；離開鰭片後還會掃過記憶體、VRM、電源。' },
    },
  });
})();
