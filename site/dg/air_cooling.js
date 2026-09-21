/* 風扇與氣冷模組 —— docs/diagram_plan.md 的第 6 張（族群 `air_cooling`、ai_server 鏈）
   規格書：docs/diagram_specs/air_cooling.md

   ★ 型式：2D 為主（風扇剖面、軸承四型剖面、風壓風量曲線、風扇牆平面）
     ＋ 2.5D 等角（扇框與扇葉的組裝關係）為輔。**不做真 3D**（規格書 §0 已寫死，`scene: null`）。
     ⚠ 規格書 §0 特別點名一種**假的 3D 理由**：「風扇會轉，所以做 3D 比較生動」——
       那不是理由。「轉起來」是**動畫**，2D／2.5D 一樣做得到（下面的扇葉就是 CSS 旋轉），
       跟「要不要真 3D」是兩件事。軸承四型、P-Q 曲線、氣流夾角這三件事
       **轉一圈都不會多理解**，其中 P-Q 曲線 3D 根本畫不了。

   ★ 這張圖跟 `liquid_cooling.js` 是一對，不是競爭關係：
       · 液冷那張的結論之一是「冷板只貼最熱的那幾顆，其餘靠氣流」，這張負責把它畫出來；
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
  const { STYLE, labelRow, processBar } = DG;

  const SEG = 'thermal';        // 散熱（均熱片 / 液冷）—— ai_server 鏈，YAML 裡查證過存在
  const SEG_A = 'assembly';     // 系統組裝 / 機櫃 —— 只有機殼襯景掛它

  /* ★ 兩張圖共用的那一句（規格書 air §7-B2 ＝ liquid §7-B3）。
     `liquid_cooling.js` 裡有一份**一字不差**的複本 —— 改一邊要改另一邊。
     兩行都掛 `data-share`，驗收會把兩張圖這幾個元素的文字接起來做字串比對。*/
  const SHARE_LINES = ['多數熱由冷板帶走（公開資料約在 7～8 成之間，', '各來源分母不同），其餘仍靠氣流'];
  const shareText = (x, y) => SHARE_LINES.map((s, i) =>
    `<text class="sub" data-share="1" x="${x}" y="${y + i * 18}">${s}</text>`).join('');

  /* 這一組色票與 `liquid_cooling.js` 的完全相同（規格書 §8：冷／暖語意兩張必須一致）。
     ⚠ `--dg-*` 的家本來在 `site/index.html` 的 :root，但這一批不准動 index.html，
       所以先定義在圖自己的 scoped style 裡：色值只出現在這一個區塊，
       底下所有形狀一律 `var(--dg-*)`。之後 art-director 要收進 :root，整塊搬過去即可。*/
  /* 這張圖的材質色 token 已經在 2026-09-21 深夜收進 `site/index.html` 的 :root（art-director 擁有）。
     收進去的理由：配色切換（html 的 data-dgpal）在 :root 那一層蓋不掉圖自己 scope 裡的變數，
     不收就等於「休閒配色只有一張圖有效」。**是同值搬家，值一個都沒改。**
     這裡只留下這張圖自己的**規則**（class 定義），那些不是 token，不該進 :root。*/
  const VARS = `<style>
    .dgair .fine{font-size:var(--dg-fs-min,12px);fill:var(--dg-ink-3,#8ea0c4)}
  </style>`;

  const P = (part, inner, seg) => `<g data-seg="${seg || SEG}" data-part="${part}">${inner}</g>`;
  const row = (part, ...a) => labelRow(...a).replace('<g class="lrow"', `<g class="lrow" data-part="${part}"`);

  /* 流程列補 data-part：規格書 §7-D2 要求每一個 [data-seg] 都要有身分，
     否則 `stampParts` 會自動補「環節 id ＋ 文件順序」，圖上零件一換順序就對不起來。
     共用的 `DG.processBar` 不吃 data-part（它是既有共用函式，這一批不准動 diagrams.js），
     所以在呼叫端把 key 注進去 —— 跟上面 `row()` 同一個做法：
     **沿用共用函式產出的幾何，只多綁一個身分**。*/
  const pbar = (x, y, steps, w) => {
    let i = 0;
    return processBar(x, y, steps, w)
      .replace(/<g data-seg="/g, () => `<g data-part="flow${i++}" data-seg="`);
  };


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
     ⚠ `diagrams.js` 的 `.dg .spin` 已經設了 `transform-box:fill-box; transform-origin:center`，
       所以這裡**不准再寫 `transform-origin: <x>px <y>px`** —— 在 fill-box 座標系裡那個像素值
       是相對於元素自己的邊界框，不是 SVG 使用者座標，寫下去整組扇葉會飛到畫面外面去
       （第一版就是這樣，六組轉子全部跑到別的區塊上）。
       改成靠 `center`，再補一個透明的同心圓把邊界框**撐成正圓**，
       中心就精準落在轉軸上（葉片本身等角排列，但圓弧端點不保證對稱）。*/
    function rotor(cx, cy, r0, r1, n, dir, spin, dur) {
    const a = [`<circle cx="${cx}" cy="${cy}" r="${r1}" fill="none"/>`];
    for (let i = 0; i < n; i++) a.push(`<path class="part" fill="var(--dg-alu)" d="${blade(cx, cy, r0, r1, i * 360 / n, 34, 26, dir)}"/>`);
    return `<g class="${spin === false ? '' : 'spin'}" style="animation-duration:${dur || 2.2}s${dir < 0 ? ';animation-direction:reverse' : ''}">${a.join('')}</g>`;
  }

  function airCooling() {
    // ================================================================ ② 2.5D 等角：一顆風扇
    /* 扇框往右上長出厚度（2.5D），前面板挖一個圓孔（風道），轉子裝在孔裡。
       四角有鎖孔 —— 那是「這顆是鎖在機殼上的工業風扇」而不是家用電風扇的第一個記號。*/
    const FX = 150, FY = 288, FR = 106;        // 前面板中心與半邊長
    const DX = 26, DY = -14;                   // 厚度方向
    const frame = (() => {
      const x0 = FX - FR, y0 = FY - FR, s = FR * 2;
      const hole = `M${FX + 98},${FY} A98,98 0 1 0 ${FX - 98},${FY} A98,98 0 1 0 ${FX + 98},${FY}Z`;
      const holes = [[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sy]) =>
        `<circle cx="${FX + sx * (FR - 15)}" cy="${FY + sy * (FR - 15)}" r="7" fill="var(--dg-void)"/>`).join('');
      return `<rect x="${x0 + DX}" y="${y0 + DY}" width="${s}" height="${s}" rx="12" fill="var(--dg-alu-2)" opacity=".8"/>`
        + `<path fill="var(--dg-alu-2)" d="M${x0},${y0}L${x0 + DX},${y0 + DY}L${x0 + s + DX},${y0 + DY}L${x0 + s},${y0}Z"/>`
        + `<path fill="var(--dg-alu-3)" d="M${x0 + s},${y0}L${x0 + s + DX},${y0 + DY}L${x0 + s + DX},${y0 + s + DY}L${x0 + s},${y0 + s}Z"/>`
        + `<path class="part" fill="var(--dg-alu)" fill-rule="evenodd" d="M${x0 + 12},${y0}h${s - 24}a12,12 0 0 1 12,12v${s - 24}a12,12 0 0 1 -12,12h-${s - 24}a12,12 0 0 1 -12,-12v-${s - 24}a12,12 0 0 1 12,-12Z ${hole}"/>`
        + holes;
    })();
    const hub = `<circle class="part" cx="${FX}" cy="${FY}" r="38" fill="url(#acHub)"/>`
      + `<circle cx="${FX}" cy="${FY}" r="9" fill="var(--dg-steel-2)"/>`;

    // ================================================================ ① 風扇剖面（氣流左 → 右）
    const CX0 = 330, CX1 = 618, AXIS = 292;     // 剖面左右界與轉軸高度
    const section = (() => {
      const top = `<rect class="part" x="${CX0}" y="182" width="${CX1 - CX0}" height="16" rx="3" fill="var(--dg-alu)"/>`;
      const bot = `<rect class="part" x="${CX0}" y="386" width="${CX1 - CX0}" height="16" rx="3" fill="var(--dg-alu)"/>`;
      // 輪轂：馬達藏在裡面（§6-F3，不可以畫在扇框上）
      const hubR = `<rect class="part" x="428" y="250" width="96" height="84" rx="8" fill="var(--dg-alu-2)"/>`;
      const magnet = `<rect x="434" y="256" width="84" height="10" rx="2" fill="var(--dg-mag)"/>`
        + `<rect x="434" y="318" width="84" height="10" rx="2" fill="var(--dg-mag)"/>`;
      const coils = [0, 1, 2, 3].map(i => `<rect x="${448 + i * 16}" y="272" width="10" height="40" rx="2" fill="var(--dg-cu)"/>`).join('');
      const shaft = `<rect x="408" y="${AXIS - 5}" width="140" height="10" rx="4" fill="var(--dg-steel)"/>`;
      // 扇葉在剖面上是斜的（同一個傾角常數的另一種畫法）
      const bl = (y0, dir) => [0, 1].map(i => {
        const x = 440 + i * 52;
        return `<path class="part" fill="var(--dg-alu)" d="M${x},${y0}l26,${dir * -46}l18,7l-26,${dir * 46}Z"/>`;
      }).join('');
      // 氣流：進出同一個方向（軸流的定義，§6-A4／3-C），顏色由冷漸變到暖（§6-A6）
      const flow = [218, 250, 334, 366].map((y, i) =>
        `<path class="flow fast" d="M${CX0 + 8},${y}H${CX1 - 8}" stroke="url(#acAir)" stroke-width="3" fill="none" style="animation-delay:${(i * 0.2).toFixed(1)}s"/>`
        + `<path d="M${CX1 - 14},${y - 5}l10,5l-10,5Z" fill="var(--dg-hot)"/>`).join('');
      // 四線接頭：電源／地／轉速回授 tach／PWM（Intel 4-wire 規格；畫面只寫四條各是什麼）
      const wires = [['var(--dg-err)', '＋12 V'], ['var(--dg-ink-3)', '接地'], ['var(--dg-cold)', '轉速回授 tach'], ['var(--dg-hot)', 'PWM 控制']]
        .map(([c, t], i) => `<path d="M${CX0 + 6},${412 + i * 16}h34" stroke="${c}" stroke-width="2.6" fill="none"/>`
          + `<text class="fine" x="${CX0 + 46}" y="${416 + i * 16}">${t}</text>`).join('');
      return top + bot + flow + bl(250, 1) + bl(334, -1) + hubR + magnet + coils + shaft
        + `<circle cx="418" cy="${AXIS}" r="11" fill="none" stroke="var(--dg-steel)" stroke-width="3"/>`
        + `<circle cx="538" cy="${AXIS}" r="11" fill="none" stroke="var(--dg-steel)" stroke-width="3"/>`
        + `<text class="fine" x="${CX0}" y="176" style="fill:var(--dg-cold)">進氣</text>`
        + `<text class="fine" x="${CX1 - 28}" y="176" style="fill:var(--dg-hot)">出氣</text>`
        + `<text class="fine" x="392" y="${AXIS + 34}">軸承</text><text class="fine" x="546" y="${AXIS + 34}">軸承</text>`
        + wires;
    })();

    // ================================================================ ③ 軸承四型（同一根軸）
    const BCELL = [16, 256, 496, 736], BW = 228, BY = 500, BH = 196;
    /* ★ 四格一定要**共用同一個「畫軸」的函式**，只換內部細節 —— 這一行就是 §6-B1。
       不同基準畫出來就比不出差別，那正是這四格唯一存在的理由。*/
    function bearing(i, title, kind, lines) {
      const x = BCELL[i] + 20, y = BY + 62, w = BW - 40;
      const SH = 14;                                   // 軸的粗細：四格完全一樣
      // 軸本身四格完全一樣（小標已經寫在區塊標題上，這裡不再重複一次）
      const shaft = `<rect x="${x}" y="${y + 30}" width="${w}" height="${SH}" rx="3" fill="var(--dg-steel)"/>`;
      let inner = '';
      if (kind === 'sleeve') {                          // 含油：軸與襯套**直接接觸**
        inner = `<rect x="${x}" y="${y + 18}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`;
      } else if (kind === 'ball') {                     // 滾珠：**看得到鋼珠**
        const balls = [];
        for (let k = 0; k < 8; k++) balls.push(`<circle cx="${x + 12 + k * ((w - 24) / 7)}" cy="${y + 22}" r="6" fill="var(--dg-steel)"/>`
          + `<circle cx="${x + 12 + k * ((w - 24) / 7)}" cy="${y + 52}" r="6" fill="var(--dg-steel)"/>`);
        inner = `<rect x="${x}" y="${y + 8}" width="${w}" height="8" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 58}" width="${w}" height="8" rx="2" fill="var(--dg-alu-2)"/>${balls.join('')}`;
      } else if (kind === 'fdb') {                      // 流體動壓：油膜 ＋ 襯套上有溝槽
        const gr = [];
        for (let k = 0; k < 9; k++) gr.push(`<path d="M${x + 10 + k * ((w - 20) / 8)},${y + 12}l7,8" stroke="var(--dg-void)" stroke-width="2" fill="none"/>`
          + `<path d="M${x + 10 + k * ((w - 20) / 8)},${y + 62}l7,-8" stroke="var(--dg-void)" stroke-width="2" fill="none"/>`);
        inner = `<rect x="${x}" y="${y + 10}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 52}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>${gr.join('')}`
          + `<rect x="${x}" y="${y + 22}" width="${w}" height="8" fill="var(--dg-oil)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="8" fill="var(--dg-oil)"/>`;
      } else {                                          // 磁浮：軸與襯套之間**有可見空隙**
        inner = `<rect x="${x}" y="${y + 4}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 58}" width="${w}" height="12" rx="2" fill="var(--dg-alu-2)"/>`
          + `<rect x="${x}" y="${y + 16}" width="${w}" height="14" fill="var(--dg-void)"/>`
          + `<rect x="${x}" y="${y + 44}" width="${w}" height="14" fill="var(--dg-void)"/>`
          + [0, 1, 2, 3, 4].map(k => `<text class="fine" x="${x + 16 + k * 38}" y="${y + 28}" style="fill:var(--dg-mag)">N</text>`
            + `<text class="fine" x="${x + 16 + k * 38}" y="${y + 56}" style="fill:var(--dg-mag)">S</text>`).join('');
      }
      return P('brg_' + kind, `<rect class="frame" x="${BCELL[i]}" y="${BY}" width="${BW}" height="${BH}" rx="8"/>`
        + `<text class="hd" x="${BCELL[i] + 14}" y="${BY + 24}">${title}</text>`
        + `<text class="fine" x="${BCELL[i] + 14}" y="${BY + 44}">${lines[0]}</text>`
        + inner + shaft
        + lines.slice(1).map((s, k) => `<text class="fine" x="${BCELL[i] + 14}" y="${BY + 158 + k * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join(''));
    }

    // ================================================================ ④ 軸流 vs 離心
    const AY = 722;
    const axialCell = P('axial', `<rect class="frame" x="16" y="${AY}" width="228" height="212" rx="8"/>`
      + `<text class="hd" x="30" y="${AY + 24}">軸流（axial）</text>`
      + `<rect x="46" y="${AY + 50}" width="168" height="76" rx="6" fill="var(--dg-frame)" stroke="var(--dg-alu-2)"/>`
      + rotor(130, AY + 88, 14, 34, 7, 1, true, 2.4)
      + `<path class="flow fast" d="M30,${AY + 88}H44" stroke="var(--dg-cold)" stroke-width="3.4" fill="none"/>`
      + `<path class="flow fast" d="M216,${AY + 88}H232" stroke="var(--dg-hot)" stroke-width="3.4" fill="none"/>`
      + `<path d="M228,${AY + 83}l8,5l-8,5Z" fill="var(--dg-hot)"/>`
      + `<text class="fine" x="30" y="${AY + 148}">進氣與出氣同一個方向（夾角 0°）</text>`
      + `<text class="fine" x="30" y="${AY + 170}">風量大，但一遇到阻力就掉得快。</text>`
      + `<text class="fine" x="30" y="${AY + 192}">機殼裡大部分的位置用這一種。</text>`);
    /* 離心／鼓風：**沿軸進、轉 90° 從側面（這裡是往上）出**（§6-A3／3-C）。
       畫成沿軸出＝那就是軸流扇，不是離心扇 —— 所以出風口一定要畫在另一個方向，
       而且進氣箭頭與出氣箭頭之間補一個直角記號，把「90°」這件事講死。*/
    const BCx = 372, BCy = AY + 108, BOx = 372;
    const centCell = P('centrifugal', `<rect class="frame" x="256" y="${AY}" width="228" height="212" rx="8"/>`
      + `<text class="hd" x="270" y="${AY + 24}">離心／鼓風（blower）</text>`
      + `<rect class="part" x="${BOx - 24}" y="${AY + 46}" width="48" height="34" rx="3" fill="var(--dg-frame)"/>`
      + `<circle class="part" cx="${BCx}" cy="${BCy}" r="44" fill="var(--dg-frame)"/>`
      + `<rect class="part" x="296" y="${BCy - 17}" width="34" height="34" rx="3" fill="var(--dg-frame)"/>`
      + rotor(BCx, BCy, 11, 30, 9, 1, true, 2.0)
      + `<path class="flow fast" d="M272,${BCy}H322" stroke="var(--dg-cold)" stroke-width="3.4" fill="none"/>`
      + `<path d="M318,${BCy - 5}l8,5l-8,5Z" fill="var(--dg-cold)"/>`
      + `<path class="flow fast rev" d="M${BOx},${AY + 56}V${AY + 34}" stroke="var(--dg-hot)" stroke-width="3.4" fill="none"/>`
      + `<path d="M${BOx - 5},${AY + 42}l5,-9l5,9Z" fill="var(--dg-hot)"/>`
      + `<path d="M${BOx + 6},${AY + 62}v12h-12" stroke="var(--dg-warn)" stroke-width="1.4" fill="none"/>`
      + `<text class="fine" x="${BOx + 32}" y="${AY + 58}" style="fill:var(--dg-warn)">90°</text>`
      + `<text class="fine" x="270" y="${AY + 174}">沿軸進、轉 90° 從側面出。同樣</text>`
      + `<text class="fine" x="270" y="${AY + 192}">尺寸下靜壓比軸流高，適合彎路徑。</text>`);

    // ================================================================ ⑤ P-Q 曲線（座標軸不標數值）
    const QX = 512, QY0 = AY + 58, QY1 = AY + 176, QX1 = 950;
    const pq = P('pq_curve', `<rect class="frame" x="496" y="${AY}" width="468" height="212" rx="8"/>`
      + `<text class="hd" x="510" y="${AY + 24}">風壓—風量（P-Q）：交點才是工作點</text>`
      + `<path class="axis" d="M${QX},${QY0 - 8}V${QY1}H${QX1}" style="stroke-dasharray:none;stroke:rgba(120,150,210,.45)"/>`
      + `<text class="fine" x="${QX + 8}" y="${QY0 - 10}">靜壓 ↑</text>`
      + `<text class="fine" x="${QX1 - 58}" y="${QY1 - 8}">風量 →</text>`
      // 離心：靜壓端高、風量端小
      + `<path d="M${QX},${QY0} C${QX + 60},${QY0 + 10} ${QX + 110},${QY0 + 40} ${QX + 150},${QY1}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
      // 軸流：靜壓端低、風量端大
      + `<path d="M${QX},${QY0 + 44} C${QX + 110},${QY0 + 54} ${QX + 250},${QY0 + 76} ${QX + 372},${QY1}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
      // 系統阻抗曲線：從原點往右上（阻力越大、同樣風量要的靜壓越高）
      + `<path class="flow slow" d="M${QX},${QY1} Q${QX + 210},${QY1 - 20} ${QX + 300},${QY0 + 6}" stroke="var(--dg-ink-2)" stroke-width="2.2" fill="none"/>`
      + `<circle cx="${QX + 242}" cy="${QY0 + 58}" r="6" fill="none" stroke="var(--dg-warn)" stroke-width="2.4"/>`
      + `<path d="M${QX + 248},${QY0 + 54}L${QX + 286},${QY0 + 34}" stroke="var(--dg-warn)" stroke-width="1.2" fill="none"/>`
      + `<text class="fine" x="${QX + 290}" y="${QY0 + 36}" style="fill:var(--dg-warn)">工作點</text>`
      + `<text class="fine" x="${QX + 158}" y="${QY0 + 18}" style="fill:var(--dg-hot)">離心</text>`
      + `<text class="fine" x="${QX + 330}" y="${QY0 + 96}" style="fill:var(--dg-cold)">軸流</text>`
      + `<text class="fine" x="${QX + 96}" y="${QY1 - 14}" style="fill:var(--dg-ink-2)">系統阻抗曲線</text>`
      + `<text class="fine" x="510" y="${AY + 192}">座標軸刻意不標數值 —— 這張圖只畫關係，不畫數字。</text>`);

    // ================================================================ ⑥ 氣流路徑：進氣 → 排氣
    const WY = 966;
    /* 風扇牆：一排 ≥3 顆，其中**一顆標成備援（N+1）**（§6-W1）。
       風扇牆一定畫在鰭片**之前**（§6-A1，反過來＝不過）。*/
    const wall = [0, 1, 2, 3].map((i) => {
      const cy = WY + 68 + i * 62, spare = i === 3;
      return `<circle class="part" cx="150" cy="${cy}" r="27" fill="var(--dg-frame)"/>`
        + rotor(150, cy, 8, 24, 7, 1, true, 2 + i * 0.25)
        + (spare ? `<text class="fine" x="182" y="${cy + 4}" style="fill:var(--dg-warn)">備援（N+1）</text>` : '');
    }).join('');
    const finStack = (x, n, gap, h) => {
      const a = [];
      for (let i = 0; i < n; i++) a.push(`<rect x="${x + i * gap}" y="${WY + 64}" width="${Math.max(3, gap - 4)}" height="${h}" rx="1" fill="var(--dg-alu)"/>`);
      return a.join('');
    };

    // ================================================================ ⑦ 混合散熱 ＋ 噪音
    const HY = 1244;
    const bpf = (() => {
      const x0 = 520, y0 = HY + 44, y1 = HY + 128, sp = [0, 1, 2];
      const floorLine = `<path d="M${x0},${y1 - 8}H${x0 + 400}" stroke="var(--dg-ink-3)" stroke-width="1.4" opacity=".5" fill="none"/>`;
      const peaks = sp.map(i => `<path d="M${x0 + 70 + i * 116},${y1} V${y1 - (64 - i * 18)}" stroke="var(--dg-hot)" stroke-width="${5 - i}" fill="none"/>`
        + `<text class="fine" x="${x0 + 58 + i * 116}" y="${y1 - (70 - i * 18)}" style="fill:var(--dg-hot)">${i === 0 ? 'BPF' : (i + 1) + '×'}</text>`).join('');
      return `<path class="axis" d="M${x0},${y0}V${y1}H${x0 + 404}" style="stroke-dasharray:none;stroke:rgba(120,150,210,.45)"/>`
        + floorLine + peaks
        + `<text class="fine" x="${x0 + 330}" y="${y1 - 6}">頻率 →</text>`;
    })();

    // ================================================================ 說明框
    const noteBox = (x, y, w, h, t, lines, part, extra) => P(part,
      `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${y + 24}">${t}</text>`
      + lines.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 48 + i * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('')
      + (extra || ''));

    // ================================================================ 組裝
    /* class 多一個 `dg1`（理由與 `liquid_cooling.js` 同一條，那邊寫得比較長）：
       `stampParts` 只在單一 data-seg 時自動掛它，這張有兩個（thermal ＋ assembly），
       所以自己掛 —— 它的作用是 `--dg-glow:none`。全圖三十幾個零件幾乎全是 thermal，
       不關掉的話點一個零件會讓三十幾個群組一起發光（「螢光感太重」）。
       層次改由描邊寬與 `--dg-sib-o` 表達，驗收量的是這三層的 computed style 真的不同。*/
    return `<svg class="dg dgm dgair dg1" viewBox="0 0 980 1780" width="100%" style="display:block">${STYLE}${VARS}
      <defs>
        <linearGradient id="acAir" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-cold)"/><stop offset="1" stop-color="var(--dg-hot)"/></linearGradient>
        <radialGradient id="acHub" cx="38%" cy="32%" r="72%">
          <stop offset="0" stop-color="var(--dg-hub-lit)"/><stop offset="1" stop-color="var(--dg-hub-dim)"/></radialGradient>
        <linearGradient id="acFin" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-cold)"/><stop offset="1" stop-color="var(--dg-hot)"/></linearGradient>
      </defs>

      <text class="ttl" x="16" y="26">氣冷：風扇賣的是「推得過去」，不是「吹得多」</text>
      <text class="cap" x="16" y="46">家用電風扇前面沒有東西擋，所以比的是風量；伺服器風扇要穿過密排鰭片與擠滿零件的機殼，比的是靜壓。</text>
      <text class="cap" x="16" y="64">左邊是一顆風扇的外觀與剖面，下面依序是軸承四型、風壓風量曲線、整條氣流路徑，以及「上了液冷為什麼還要風扇」。</text>

      <!-- ========== ①② 一顆風扇 ========== -->
      <text class="hd" x="16" y="122">② 外觀（2.5D）：扇框、扇葉、輪轂</text>
      ${P('fan_frame', frame)}
      ${P('blade', rotor(FX, FY, 38, 98, 7, 1, true, 2.2))}
      ${P('hub', hub)}
      <text class="fine" x="16" y="418">四角有鎖孔、輪轂佔的比例大（馬達要有力），</text>
      <text class="fine" x="16" y="436">而且扇葉是斜的 —— 靠斜面把空氣往後推。</text>

      <text class="hd" x="330" y="122">① 剖面：馬達在輪轂裡，軸承在軸與輪轂之間</text>
      ${P('motor', section)}

      ${row('blade', SEG, 648, 150, '扇葉有傾角（片數為示意）', '靠斜面把空氣往後推；葉片數與角度決定風量與噪音', 248, 220, 300)}
      ${row('hub', SEG, 648, 204, '馬達藏在輪轂裡', '伺服器風扇長時間高速運轉，馬達要撐得住', 476, 292, 300)}
      ${row('fan_frame', SEG, 648, 258, '扇框（四角鎖孔）', '這是鎖在機殼上的工業件，不是有網罩與立柱的家用扇', 256, 182, 300)}
      ${row('wire4', SEG, 648, 312, '四線：電源／地／轉速回授／PWM', '轉速回授讓主機知道它有沒有在轉，PWM 讓主機依溫度調速', 400, 428, 300)}
      ${row('counter_rot', SEG, 648, 366, '反轉雙轉子（counter-rotating）', '前後兩組葉片旋向相反，後面那組把旋轉氣流扶正', null, null, 300)}
      <g data-seg="${SEG}" data-part="counter_rot">
        <rect class="frame" x="648" y="396" width="300" height="84" rx="8"/>
        <text class="fine" x="662" y="416">反轉雙轉子：前後兩組葉片旋向相反</text>
        ${rotor(700, 450, 6, 18, 7, 1, true, 1.8)}${rotor(752, 450, 6, 18, 7, -1, true, 1.8)}
        <path d="M682,444A24,24 0 0 1 718,432" stroke="var(--dg-cold)" stroke-width="1.8" fill="none"/><path d="M712,428l8,3l-6,6Z" fill="var(--dg-cold)"/>
        <path d="M770,444A24,24 0 0 0 734,432" stroke="var(--dg-hot)" stroke-width="1.8" fill="none"/><path d="M740,428l-8,3l6,6Z" fill="var(--dg-hot)"/>
        <text class="fine" x="786" y="444">後面那組把前面甩出來的</text>
        <text class="fine" x="786" y="462">旋轉氣流「扶正」，拉高靜壓</text>
      </g>

      <!-- ========== ③ 軸承四型（同一根軸） ========== -->
      <text class="hd" x="16" y="${BY - 10}">③ 軸承四型：四格用同一根軸畫，差別全部在剖面裡（畫面不寫任何壽命小時數 —— 來源自相矛盾）</text>
      ${bearing(0, '含油（sleeve）', 'sleeve', ['軸直接在襯套裡轉', '最便宜；潤滑油會耗損，', '★ 所以是四型裡最早變吵的'])}
      ${bearing(1, '滾珠（ball）', 'ball', ['兩圈鋼珠把軸撐起來', '壽命明顯長於含油，代價是', '本身有一點滾動噪音；伺服器常用'])}
      ${bearing(2, '流體動壓（FDB）', 'fdb', ['襯套刻溝槽 ＋ 一層油膜', '轉起來把油擠成壓力油膜把軸浮起，', '幾乎沒有機械噪音，而且一生都不太變'])}
      ${bearing(3, '磁浮（maglev）', 'mag', ['軸與襯套之間有可見空隙', '用磁力把轉子浮起來，', '★ 沒有機械接觸，理論壽命最長'])}

      <!-- ========== ④⑤ 軸流 vs 離心 ＋ P-Q ========== -->
      <text class="hd" x="16" y="${AY - 10}">④ 兩種氣流幾何，和「同一顆風扇在不同阻力下吹出的量完全不同」</text>
      ${axialCell}${centCell}${pq}

      <!-- ========== ⑥ 整條氣流路徑 ========== -->
      <text class="hd" x="16" y="${WY - 10}">⑤ 一條氣流走完全程：風扇只是把空氣推過來，熱是在鰭片交給空氣的</text>
      ${P('rack', `<rect class="part" x="16" y="${WY}" width="948" height="252" rx="10" fill="none" opacity=".5"/>`
      + `<text class="fine" x="820" y="${WY + 244}" style="fill:var(--dg-ink-3)">機殼／托盤（襯景）</text>`, SEG_A)}
      ${P('fan_wall', `<rect x="40" y="${WY + 24}" width="18" height="212" rx="4" fill="var(--dg-frame)" stroke="var(--dg-alu-2)"/>`
      + [0, 1, 2, 3, 4, 5, 6].map(i => `<circle cx="49" cy="${WY + 40 + i * 28}" r="5" fill="var(--dg-void)"/>`).join('')
      + `<text class="fine" x="34" y="${WY + 18}" style="fill:var(--dg-cold)">進氣（前面板）</text>` + wall
      + `<text class="fine" x="120" y="${WY + 18}">風扇牆</text>`)}
      ${P('shroud', `<path class="part" fill="none" stroke="var(--dg-alu-2)" stroke-width="2.4" stroke-dasharray="6 4" d="M250,${WY + 36}H360l40,28v104l-40,28H250"/>`
      + `<text class="fine" x="256" y="${WY + 28}">導風罩：把風「圍」到該去的地方</text>`)}
      ${P('fin', finStack(420, 9, 14, 96) + finStack(560, 18, 8, 96)
      + `<text class="fine" x="420" y="${WY + 52}">鰭距疏</text><text class="fine" x="560" y="${WY + 52}">鰭距密（面積大、阻力也大）</text>`
      + `<text class="fine" x="420" y="${WY + 178}" style="fill:var(--dg-warn)">★ 這一格才是熱真正交給空氣的地方</text>`)}
      ${P('heatpipe', `<rect class="part" x="424" y="${WY + 166}" width="288" height="14" rx="7" fill="var(--dg-cu)"/>`
      + `<rect x="430" y="${WY + 170}" width="276" height="6" rx="3" fill="var(--dg-vap)"/>`
      + `<text class="fine" x="726" y="${WY + 178}">熱管（內部是空的）</text>`)}
      ${P('vc', `<rect class="part" x="470" y="${WY + 186}" width="196" height="16" rx="3" fill="var(--dg-cu)"/>`
      + `<rect x="476" y="${WY + 190}" width="184" height="8" fill="var(--dg-vap)"/>`
      + `<rect x="534" y="${WY + 202}" width="68" height="12" rx="2" fill="var(--dg-die)"/>`
      + `<text class="fine" x="676" y="${WY + 200}">VC ＋ 晶片</text>`
      + [500, 560, 620].map((x, i) => `<path class="flow slow" d="M${x},${WY + 184}V${WY + 164}" stroke="var(--dg-hot)" stroke-width="2.2" fill="none" style="animation-delay:${(i * 0.4).toFixed(1)}s"/>`).join('')
      + `<text class="fine" x="424" y="${WY + 228}" style="fill:var(--dg-hot)">熱往上走、氣流往右走 —— 兩條路徑垂直交會</text>`)}
      ${[0, 1, 2, 3].map(i => `<path class="flow fast" d="M64,${WY + 54 + i * 52}H${240}" stroke="url(#acAir)" stroke-width="3" fill="none" style="animation-delay:${(i * 0.2).toFixed(1)}s"/>`
      + `<path class="flow fast" d="M712,${WY + 54 + i * 52}H900" stroke="url(#acAir)" stroke-width="3" fill="none" style="animation-delay:${(i * 0.2).toFixed(1)}s"/>`
      + `<path d="M896,${WY + 49 + i * 52}l10,5l-10,5Z" fill="var(--dg-hot)"/>`).join('')}
      <text class="fine" x="840" y="${WY + 18}" style="fill:var(--dg-hot)">排氣（後方）</text>
      <text class="fine" x="790" y="${WY + 206}">記憶體／VRM／電源／光模組</text>
      <text class="fine" x="790" y="${WY + 224}">也靠這股氣流</text>

      <!-- ========== ⑦ 混合散熱 ＋ 噪音 ========== -->
      ${P('hybrid', `<rect class="frame" x="16" y="${HY}" width="472" height="150" rx="8"/>`
      + `<text class="hd" x="30" y="${HY + 24}">上了液冷，風扇不會變成零</text>`
      + `<rect x="34" y="${HY + 58}" width="196" height="12" rx="2" fill="var(--dg-pcb)"/>`
      + `<rect x="74" y="${HY + 38}" width="60" height="20" rx="3" fill="var(--dg-cu)"/>`
      + `<rect x="84" y="${HY + 58}" width="40" height="8" fill="var(--dg-die)"/>`
      + `<text class="fine" x="34" y="${HY + 90}" style="fill:var(--dg-cold)">冷板只貼 GPU／部分 CPU</text>`
      + [0, 1, 2, 3].map(i => `<rect x="${262 + i * 26}" y="${HY + 46}" width="16" height="24" rx="2" fill="var(--dg-die)"/>`).join('')
      + [0, 1, 2].map(i => `<path class="flow fast" d="M250,${HY + 40 + i * 14}H400" stroke="url(#acAir)" stroke-width="2.6" fill="none" style="animation-delay:${(i * 0.25).toFixed(2)}s"/>`).join('')
      + `<text class="fine" x="262" y="${HY + 90}" style="fill:var(--dg-hot)">記憶體／VRM／電源仍靠氣流</text>`
      + `<text class="fine" x="30" y="${HY + 116}">所以液冷機櫃裡還是有「數百顆」風扇。</text>`
      + shareText(30, HY + 134))}
      ${P('bpf', `<rect class="frame" x="496" y="${HY}" width="468" height="150" rx="8"/>`
      + `<text class="hd" x="510" y="${HY + 24}">葉片數 × 轉速 ＝ 那個「嗡」的頻率</text>` + bpf
      + `<text class="fine" x="510" y="${HY + 144}">等距葉片把能量集中在這個頻率與它的諧波；排成不等距就攤成一片。</text>`)}

      <!-- ========== ⑧ 說明框 ========== -->
      ${noteBox(16, 1414, 472, 186, '伺服器風扇跟家用風扇差在哪', [
        '家用風扇前面沒有東西擋，所以比的是風量；伺服器風扇要',
        '穿過密排鰭片與擠滿零件的機殼，比的是靜壓。',
        '所以它轉速高、輪轂大、葉片厚，而且常用反轉雙轉子。',
        '代價是吵與耗電 —— 這正是機櫃功率一上去就得考慮液冷的原因。',
        '★ 不要拿 U 數當散熱規格：1U／2U／4U 這種機殼代號不該被指派',
        '　 一個通用的風量或靜壓目標，兩台 1U 的工作點可以完全不同。',
      ], 'vs_home')}
      ${noteBox(504, 1414, 460, 186, '這張圖沒有回答的事', [
        '任何一顆風扇的轉速、風量、靜壓、噪音值：那是型號層級的東西，',
        '而且查到的來源多半是風扇廠與 PC 零件站的部落格 —— 一個都不寫。',
        '軸承壽命的小時數：查到的數字散得很開，而且 FDB 竟然低於滾珠，',
        '與同一批來源的定性結論互相矛盾 —— 只寫排序，不寫小時數。',
        '各家市占率、良率、單價：查不到可引用的公開數字，不編。',
        '鰭距的具體數值：查不到通用值，所以只畫疏／密對照。',
      ], 'unknown')}

      <!-- ========== ⑨ 流程列 ========== -->
      <text class="cap" x="16" y="1630">一條氣流走完全程（五格）　★ 風扇（格 2）一定在鰭片（格 4）之前</text>
      ${pbar(16, 1638, [
      { seg: SEG_A, t: '進氣', s: '前面板濾網／開孔' },
      { seg: SEG, t: '推動', s: '風扇牆（N+1）' },
      { seg: SEG, t: '導引', s: '導風罩／風道' },
      { seg: SEG, t: '交換', s: '鰭片 ＋ 熱管／VC' },
      { seg: SEG_A, t: '排氣', s: '後方出風' }], 176)}
      <text class="fine" x="580" y="1700" style="fill:var(--dg-warn)">★ 格 4 才是熱真正交給空氣的地方；風扇只是把空氣推過來。</text>

      <text class="cap" x="16" y="1730">示意圖，非實物比例｜扇葉片數、鰭片數與軸承比例均為示意</text>
      <text class="cap" x="16" y="1748">P-Q 曲線為示意，座標軸不標數值。資料來源與信心度見 docs/diagram_specs/air_cooling.md</text>
      <text class="cap" x="16" y="1766" style="fill:var(--dg-warn)">點零件篩到的是「供應鏈環節」，不是整個族群；散熱這一格目前收錄六家，族群有九檔</text>
    </svg>`;
  }

  window.DG.register('air_cooling', {
    level: 'group', chain: 'ai_server',
    name: '氣冷：風扇、風扇牆與散熱模組',
    draw: airCooling, native: 980, scene: null,
    q: '伺服器風扇跟家用風扇差在哪？為什麼都上液冷了，一櫃還是要幾百顆風扇？',
  });
})();
