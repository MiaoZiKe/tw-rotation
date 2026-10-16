/* ============================================================================
   精選文章的「具象插圖」（{"t":"illus","kind":"cowos"|"rack", ...}）—— 2026-10-16
   ----------------------------------------------------------------------------
   Andy 2026-10-16 看著 CoWoS 文章那張平平的色塊長條剖面：
     「像是這種有提到特定元件，需要繪圖出來，更具像化，我指的就是這種圖要穿差一點」
   → 文章提到具體元件時，畫成看得出是哪個零件的插圖（2.5D 斜視剖面＋厚度＋明暗），不再用色塊長條。

   這支只負責「畫」：每種 kind 回傳一段 SVG（幾何、材質）與各零件的錨點（引線要對到的那一點）。
   說明文字（每層名稱＋一句話）在文章 JSON 的 parts 裡；版面、引線、手機編號由 site/articles.js 的 illus 區塊處理。

   為什麼是 2.5D SVG、不是 three3d.js：文章是讀的，不需要轉；SVG 輕、手機不吃力、深淺主題只換 CSS 變數。
   顏色一律走 CSS 變數（--il-*，深淺各一組），SVG 裡沒有任何寫死的白或黑。
   文字不畫在 SVG 裡（會跟著縮小）：名稱與說明全部是 HTML，字級固定 ≥ 12px。

   事實依據（只畫結構與相對大小，比例示意）：
   · CoWoS-S 由上而下：運算晶片＋HBM → 微凸塊 → 矽中介層（重佈線＋TSV）→ C4 凸塊 → ABF 載板 → 錫球（BGA）→ 主機板
     （沿用 site/dg/ai_adv_packaging.js 規格書 docs/diagram_specs/ic_package.md 的查證：µbump 30–60 µm、C4 節距 150–200 µm 的量級）
     → 圖上只表達「微凸塊 < C4 < 錫球」的大小順序，不畫真實比例。
   · AI 機櫃（GB200 NVL72 一類，2026-10-16 WebSearch：ServeTheHome 拆解、HPE QuickSpecs、Gigabyte DLB2 規格書摘要）：
     18 個 1U 運算托盤＋9 個 1U NVLink 交換器托盤（在中段）、電源架分在上下、頂端管理交換器、
     背面有液冷分歧管與電源匯流排；各家擺放順序不一 → 托盤數量與位置一律標「示意」。
   ============================================================================ */
(function () {
  'use strict';
  const f1 = (n) => Math.round(n * 10) / 10;
  const pts = (a) => a.map((p) => f1(p[0]) + ',' + f1(p[1])).join(' ');

  /* 斜視方塊：前面（剖面）＋上面＋右側面；d＝深度向量（往右上） */
  function box(x, y, w, h, m, d, extra) {
    const [dx, dy] = d;
    return `<g class="m-${m}${extra ? ' ' + extra : ''}">`
      + `<polygon class="t" points="${pts([[x, y], [x + w, y], [x + w + dx, y + dy], [x + dx, y + dy]])}"/>`
      + `<polygon class="r" points="${pts([[x + w, y], [x + w + dx, y + dy], [x + w + dx, y + h + dy], [x + w, y + h]])}"/>`
      + `<rect class="f" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"/></g>`;
  }
  const rect = (x, y, w, h, cls, rx) => `<rect class="${cls}" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''}/>`;
  const line = (x1, y1, x2, y2, cls) => `<line class="${cls}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}"/>`;
  const circ = (cx, cy, r, fill) => `<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="url(#${fill})" class="ball"/>`;
  /* 上面（斜面）上的點：原點＋u×寬＋v×深度 */
  const onTop = (x, y, w, d, u, v) => [x + u * w + v * d[0], y + v * d[1]];
  const quadTop = (x, y, w, d, u0, v0, u1, v1) => pts([onTop(x, y, w, d, u0, v0), onTop(x, y, w, d, u1, v0), onTop(x, y, w, d, u1, v1), onTop(x, y, w, d, u0, v1)]);

  /* 共用漸層（id 帶前綴，同一頁多張圖不撞名） */
  function defs(P) {
    const ball = (id, m) => `<radialGradient id="${P}${id}" cx=".36" cy=".3" r=".75"><stop offset="0" style="stop-color:color-mix(in srgb,var(${m}) 35%,var(--il-hi))"/>`
      + `<stop offset=".55" style="stop-color:var(${m})"/><stop offset="1" style="stop-color:color-mix(in srgb,var(${m}) 55%,var(--il-lo))"/></radialGradient>`;
    return `<defs>${ball('sol', '--il-sol')}${ball('cu', '--il-cu')}
      <linearGradient id="${P}gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--il-hi);stop-opacity:.18"/><stop offset="1" style="stop-color:var(--il-hi);stop-opacity:0"/></linearGradient>
      <filter id="${P}sh" x="-10%" y="-200%" width="120%" height="500%"><feGaussianBlur stdDeviation="6"/></filter></defs>`;
  }

  /* ------------------------------------------------------------------ CoWoS-S 剖面（2.5D 斜視） */
  const COWOS_PARTS = [
    { id: 'gpu', label: 'GPU 運算晶片', sub: 'GPU 或客製化 AI 晶片，放在正中間' },
    { id: 'hbm', label: 'HBM 高頻寬記憶體', sub: '多層 DRAM 垂直疊起，靠矽穿孔（TSV）上下相通' },
    { id: 'ubump', label: '微凸塊', sub: '把晶片與 HBM 接到中介層的細小接點（最小的一種）' },
    { id: 'interposer', label: '矽中介層', sub: '上層重佈線連通晶片與 HBM；矽穿孔（TSV）往下接' },
    { id: 'c4', label: 'C4 凸塊', sub: '中介層與載板之間，比微凸塊大一級的接點' },
    { id: 'abf', label: 'ABF 載板', sub: '多層線路，把中介層的細線轉成較粗的線路' },
    { id: 'bga', label: '錫球（BGA）', sub: '封裝底部最大的焊點，焊到主機板上' },
    { id: 'board', label: '伺服器主機板', sub: '承載整顆封裝的電路板（PCB）' },
  ];
  function cowos(P) {
    const D = [40, -24];
    // 各層前緣的 y（由上而下）。薄層刻意加厚（示意），大小順序：微凸塊 < C4 < 錫球
    const Y = { die: 150, dieH: 100, ub: 254, ubR: 3.4, ip: 258, ipH: 38, c4: 306, c4R: 9.4, sb: 316, sbH: 74, bga: 404, bgaR: 13.4, pcb: 418, pcbH: 44 };
    const o = [];
    o.push(`<ellipse class="shadow" cx="300" cy="${Y.pcb + Y.pcbH + 6}" rx="290" ry="9" filter="url(#${P}sh)"/>`);
    // 主機板：綠色多層板，內層銅線＋板面幾顆被動元件
    let g = box(20, Y.pcb, 540, Y.pcbH, 'pcb', D);
    g += line(20, Y.pcb + 14, 560, Y.pcb + 14, 'cuIn') + line(20, Y.pcb + 29, 560, Y.pcb + 29, 'cuIn');
    [[26, 0.35], [40, 0.66], [538, 0.3], [550, 0.7]].forEach(([x, v]) => { const p = onTop(x, Y.pcb, 0, D, 0, v); g += box(p[0], p[1] - 5, 10, 5, 'cap', [5, -3]); });
    o.push(`<g data-part="board">${g}</g>`);
    // 錫球（BGA）：最大的一排球
    g = '';
    for (let i = 0; i < 15; i++) { const x = 78 + i * 31.3; g += rect(x - 8, Y.pcb - 1.5, 16, 2, 'pad') + circ(x, Y.bga, Y.bgaR, P + 'sol'); }
    o.push(`<g data-part="bga">${g}</g>`);
    // ABF 載板：上下增層（細銅線＋微孔）夾著核心層（鍍通孔）
    g = box(60, Y.sb, 472, Y.sbH, 'abf', D);
    const cT = Y.sb + 22, cH = 30;
    g += rect(60, cT, 472, cH, 'core');
    for (let x = 84; x < 520; x += 38) g += rect(x, cT, 3.4, cH, 'cu');
    [Y.sb + 6, Y.sb + 15, cT + cH + 7, cT + cH + 16].forEach((y, k) => {
      for (let x = 66 + (k % 2) * 11; x < 520; x += 34) { const len = 14 + ((x * 7 + k * 13) % 11); g += rect(x, y - 0.9, Math.min(len, 530 - x), 1.8, 'cu'); }
      for (let x = 72 + k * 9; x < 520; x += 46) g += rect(x, y, 1.8, 9, 'cu');
    });
    o.push(`<g data-part="abf">${g}</g>`);
    // C4 凸塊：中介層下方，中等大小
    g = '';
    for (let x = 116; x <= 476; x += 24) g += circ(x, Y.c4, Y.c4R, P + 'sol');
    o.push(`<g data-part="c4">${g}</g>`);
    // 矽中介層：上層重佈線（RDL）＋垂直 TSV（對齊 C4）
    g = box(100, Y.ip, 392, Y.ipH, 'si', D);
    g += rect(100, Y.ip, 392, 9, 'rdl');
    for (let x = 104; x < 488; x += 13) g += rect(x, Y.ip + 2, 7 + (x % 3), 1.3, 'cu');
    for (let x = 110; x < 488; x += 17) g += rect(x, Y.ip + 5.5, 9, 1.2, 'cu');
    for (let x = 116; x <= 476; x += 24) g += rect(x - 1.4, Y.ip + 9, 2.8, Y.ipH - 9, 'cu');
    // 高速通道：晶片 ↔ HBM 在中介層裡直接連線（亮一點的那兩條）
    g += `<path class="hs" d="M208,${Y.ip} V${Y.ip + 4} H178 V${Y.ip} M384,${Y.ip} V${Y.ip + 4} H414 V${Y.ip}"/>`;
    o.push(`<g data-part="interposer">${g}</g>`);
    // 微凸塊：晶片與 HBM 底下密密一排小圓點
    g = '';
    const ub = (a, b) => { for (let x = a; x <= b; x += 8) g += circ(x, Y.ub, Y.ubR, P + 'cu'); };
    ub(117, 182); ub(206, 386); ub(411, 476);
    o.push(`<g data-part="ubump">${g}</g>`);
    // HBM 堆疊：底層邏輯晶粒＋8 層 DRAM，三條 TSV 貫穿；每側前後兩疊（沿深度方向）
    const hbm = (x, v0, v1) => {
      const ox = x + v0 * D[0], oy = Y.die + v0 * D[1], dd = [D[0] * (v1 - v0), D[1] * (v1 - v0)], w = 74, h = Y.dieH;
      let s = box(ox, oy, w, h, 'hbm', dd);
      s += rect(ox, oy + h - 14, w, 14, 'base');
      const lh = (h - 14) / 8;
      for (let i = 0; i < 8; i++) s += rect(ox, oy + i * lh, w, lh - 1.2, i % 2 ? 'dram2' : 'dram1');
      [0.26, 0.5, 0.74].forEach((u) => { s += rect(ox + u * w - 1, oy + 2, 2, h - 6, 'cu'); });
      s += `<rect class="gl" x="${f1(ox)}" y="${f1(oy)}" width="${w}" height="${h}" fill="url(#${P}gl)"/>`;
      return s;
    };
    const gpu = () => {
      const x = 200, y = Y.die, w = 192, h = Y.dieH;
      let s = box(x, y, w, h, 'gpu', D);
      s += rect(x, y + h - 9, w, 9, 'act');
      for (let i = 0; i < 24; i++) s += rect(x + 4 + i * 7.9, y + h - 7, 3.2, 5, 'actc');
      // 晶片上面看得到的格子（運算單元示意）
      [1 / 3, 2 / 3].forEach((u) => { const a = onTop(x, y, w, D, u, 0.08), b = onTop(x, y, w, D, u, 0.92); s += line(a[0], a[1], b[0], b[1], 'grid'); });
      { const a = onTop(x, y, w, D, 0.04, 0.5), b = onTop(x, y, w, D, 0.96, 0.5); s += line(a[0], a[1], b[0], b[1], 'grid'); }
      s += `<polygon class="gridb" points="${quadTop(x, y, w, D, 0.04, 0.08, 0.96, 0.92)}"/>`;
      s += `<rect class="gl" x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#${P}gl)"/>`;
      return s;
    };
    // 畫的順序＝離觀看者遠的先畫（深度大的先、同深度左邊先）
    o.push(`<g data-part="hbm" data-k="back">${hbm(112, 0.55, 1)}</g>`);
    o.push(`<g data-part="hbm" data-k="front">${hbm(112, 0, 0.45)}</g>`);
    o.push(`<g data-part="gpu">${gpu()}</g>`);
    o.push(`<g data-part="hbm" data-k="back">${hbm(406, 0.55, 1)}</g>`);
    o.push(`<g data-part="hbm" data-k="front">${hbm(406, 0, 0.45)}</g>`);
    return {
      vb: [0, 104, 612, Y.pcb + Y.pcbH + 18 - 104], body: defs(P) + o.join(''),
      // 錨點（SVG 座標）：引線從這一點出發；out＝先垂直走到這個 y 再往右（避免穿過別的零件）
      anchors: {
        gpu: { x: 362, y: Y.die - 12, out: 110 }, hbm: { x: 466, y: Y.die + 40 }, ubump: { x: 467, y: Y.ub }, interposer: { x: 470, y: Y.ip + 24 },
        c4: { x: 476, y: Y.c4 }, abf: { x: 508, y: Y.sb + 37 }, bga: { x: 78 + 14 * 31.3, y: Y.bga }, board: { x: 540, y: Y.pcb + 22 },
      },
    };
  }

  /* ------------------------------------------------------------------ AI 機櫃（拆掉前門、側板開窗） */
  const RACK_PARTS = [
    { id: 'frame', label: '機殼與滑軌', sub: '鋼構機櫃，托盤沿兩側滑軌推進拉出' },
    { id: 'psu', label: '電源架', sub: '一排電源供應器，把市電轉成整櫃用的直流電' },
    { id: 'compute', label: '運算托盤', sub: '每盤放 GPU 與 CPU，整櫃十幾盤' },
    { id: 'coldplate', label: '冷板與水管', sub: '冷板貼在晶片上，冷卻液流過把熱帶走' },
    { id: 'switch', label: '交換器托盤', sub: '在機櫃中段，讓櫃內所有 GPU 互傳資料' },
    { id: 'manifold', label: '液冷分歧管', sub: '冷液（藍）送進、熱液（紅）回收，快接頭接到每一盤' },
    { id: 'bbu', label: 'BBU 備援電池', sub: '停電時先頂住，撐到備援電源接手' },
  ];
  function rack(P) {
    const D = [118, -64];
    const X = 110, Y = 100, W = 240, H = 440, post = 12;
    const ix = X + post, iw = W - 2 * post;
    const o = [];
    o.push(`<ellipse class="shadow" cx="${X + W / 2 + 50}" cy="${Y + H + 4}" rx="190" ry="10" filter="url(#${P}sh)"/>`);
    // 側板（開窗看到背面的分歧管）＋頂板
    let g = `<polygon class="m-steel r" points="${pts([[X + W, Y], [X + W + D[0], Y + D[1]], [X + W + D[0], Y + H + D[1]], [X + W, Y + H]])}"/>`;
    const win = (u0, u1, y0, y1) => pts([[X + W + u0 * D[0], y0 + u0 * D[1]], [X + W + u1 * D[0], y0 + u1 * D[1]], [X + W + u1 * D[0], y1 + u1 * D[1]], [X + W + u0 * D[0], y1 + u0 * D[1]]]);
    g += `<polygon class="cave" points="${win(0.08, 0.94, Y + 22, Y + H - 24)}"/>`;
    g += `<polygon class="m-steel t" points="${pts([[X, Y], [X + W, Y], [X + W + D[0], Y + D[1]], [X + D[0], Y + D[1]]])}"/>`;
    for (let k = 1; k <= 7; k++) { const a = onTop(X, Y, W, D, 0.14, k / 8.5), b = onTop(X, Y, W, D, 0.86, k / 8.5); g += line(a[0], a[1], b[0], b[1], 'vent'); }
    o.push(`<g data-part="frame" data-k="body">${g}</g>`);
    // 托盤配置（由上而下；高度為示意）
    const rows = [['tor', 14], ['psu', 30], ['cmp', 24], ['cmp', 24], ['cmp', 24], ['cmp', 24], ['sw', 20], ['sw', 20], ['sw', 20], ['cmp', 24], ['cmp', 24], ['cmp', 24], ['cmp', 24], ['psu', 30], ['bbu', 30]];
    const gap = 2.4, tot = rows.reduce((s, r) => s + r[1], 0) + gap * (rows.length - 1);
    let y = Y + 8 + (H - 16 - tot) / 2;
    const at = {}; const PULL = 10;   // 第 11 列（下半段第 2 盤運算托盤）拉出來
    // 分歧管：側板窗內、靠背面的兩根直管（藍冷、紅熱），每一盤運算托盤有一對軟管接過去
    const pipeX = (u) => X + W + u * D[0];
    g = '';
    const yTop = Y + 30, yBot = Y + H - 30;
    [[0.8, 'cold'], [0.88, 'hot']].forEach(([u, k]) => {
      const px = pipeX(u), py0 = yTop + u * D[1], py1 = yBot + u * D[1];
      g += `<rect class="pipe ${k}" x="${f1(px - 3.5)}" y="${f1(py0)}" width="7" height="${f1(py1 - py0)}" rx="3.5"/>`;
    });
    o.push(`<g data-part="manifold">${g}</g>`);
    const hoses = [];
    rows.forEach((r, i) => {
      const h = r[1];
      at[i] = { y, h, k: r[0] };
      if (r[0] === 'cmp') {
        [[0.8, 'cold'], [0.88, 'hot']].forEach(([u, k]) => {
          const yy = y + h / 2 + u * D[1], a = [pipeX(u) - 3, yy], b = [pipeX(0.2), y + h / 2 + 0.2 * D[1]];
          hoses.push(`<path class="hose ${k}" d="M${f1(a[0])},${f1(a[1])} L${f1(b[0])},${f1(b[1] + (k === 'hot' ? 2 : -2))}"/><circle class="qd" cx="${f1(a[0])}" cy="${f1(a[1])}" r="2.6"/>`);
        });
      }
      y += h + gap;
    });
    o.push(`<g data-part="manifold" data-k="hose">${hoses.join('')}</g>`);
    // 前面：機櫃內部底色＋每一盤的前面板
    o.push(`<rect class="cave" x="${ix}" y="${Y}" width="${iw}" height="${H}"/>`);
    const front = (i) => {
      const { y: ry, h, k } = at[i];
      let s = '';
      if (k === 'cmp') {
        s += rect(ix + 1, ry, iw - 2, h, 'bezel', 2);
        for (let x = ix + 26; x < ix + iw - 30; x += 6) for (let yy = ry + 5; yy < ry + h - 4; yy += 5) s += rect(x, yy, 2.6, 2.6, 'hole');
        s += rect(ix + 6, ry + 4, 12, h - 8, 'hdl', 2) + rect(ix + iw - 18, ry + 4, 12, h - 8, 'hdl', 2);
        s += `<circle class="led" cx="${f1(ix + 22)}" cy="${f1(ry + h / 2)}" r="1.8"/>`;
      } else if (k === 'sw' || k === 'tor') {
        s += rect(ix + 1, ry, iw - 2, h, 'bezel2', 2);
        const n = k === 'tor' ? 20 : 16, pw = k === 'tor' ? 6 : 8, ph = h - (k === 'tor' ? 6 : 8);
        for (let j = 0; j < n; j++) s += rect(ix + 14 + j * ((iw - 28) / n), ry + (h - ph) / 2, pw, ph, 'port', 1);
      } else if (k === 'psu') {
        s += rect(ix + 1, ry, iw - 2, h, 'bezel2', 2);
        const n = 6, mw = (iw - 14) / n;
        for (let j = 0; j < n; j++) {
          const mx = ix + 7 + j * mw;
          s += rect(mx + 1, ry + 3, mw - 2, h - 6, 'psum', 2);
          s += `<circle class="fan" cx="${f1(mx + mw / 2 - 4)}" cy="${f1(ry + h / 2)}" r="${f1(h / 2 - 6)}"/>`;
          s += line(mx + mw / 2 - 4 - (h / 2 - 7), ry + h / 2, mx + mw / 2 - 4 + (h / 2 - 7), ry + h / 2, 'fanb') + line(mx + mw / 2 - 4, ry + 7, mx + mw / 2 - 4, ry + h - 7, 'fanb');
          s += rect(mx + mw - 11, ry + 6, 3, h - 12, 'hdl', 1) + `<circle class="led" cx="${f1(mx + mw - 5)}" cy="${f1(ry + 8)}" r="1.5"/>`;
        }
      } else if (k === 'bbu') {
        s += rect(ix + 1, ry, iw - 2, h, 'bezel2', 2);
        const n = 4, mw = (iw - 14) / n;
        for (let j = 0; j < n; j++) {
          const mx = ix + 7 + j * mw, by = ry + 6, bh = h - 12, bw = mw - 18;
          s += rect(mx + 3, by, bw, bh, 'bat', 2) + rect(mx + 3 + bw, by + bh / 2 - 3, 4, 6, 'term', 1);   // 電池本體＋正極凸頭
          const cy = by + bh / 2;
          s += line(mx + 9, cy, mx + 15, cy, 'sign') + line(mx + 12, cy - 3, mx + 12, cy + 3, 'sign');   // ＋
          s += line(mx + bw - 9, cy, mx + bw - 3, cy, 'sign');   // －
          s += rect(mx + 9 + 9, by + 3, Math.max(4, bw - 32), bh - 6, 'charge', 1);
        }
      }
      return s;
    };
    let F = '';
    rows.forEach((r, i) => {
      if (i === PULL) { F += rect(ix + 1, at[i].y, iw - 2, at[i].h, 'slot', 1); return; }
      const part = r[0] === 'cmp' ? 'compute' : r[0] === 'sw' ? 'switch' : r[0] === 'psu' ? 'psu' : r[0] === 'bbu' ? 'bbu' : 'tor';
      F += `<g data-part="${part}" data-row="${i}">${front(i)}</g>`;
    });
    o.push(F);
    // 前柱（滑軌）：兩根立柱，一排方孔
    g = rect(X, Y, post, H, 'postf') + rect(X + W - post, Y, post, H, 'postf');
    for (let yy = Y + 6; yy < Y + H - 4; yy += 8) g += rect(X + 4, yy, 4, 4, 'phole') + rect(X + W - post + 4, yy, 4, 4, 'phole');
    g += `<polygon class="m-steel r" points="${pts([[X + W, Y], [X + W + 4, Y - 2], [X + W + 4, Y + H - 2], [X + W, Y + H]])}"/>`;
    o.push(`<g data-part="frame" data-k="post">${g}</g>`);
    // 拉出來的那盤：往前（左下）滑出，上面看得到 4 塊 GPU 冷板＋2 塊 CPU 冷板與藍紅水管
    const pr = at[PULL], pd = [D[0] * 0.42, D[1] * 0.42], fx = ix + 1 - D[0] * 0.42, fy = pr.y - D[1] * 0.42, tw = iw - 2;
    o.push(`<g data-part="compute" data-k="pulled">${box(fx, fy, tw, pr.h, 'tray', pd)}</g>`);
    g = '';
    const plate = (u0, u1, v0, v1, cls) => `<polygon class="${cls}" points="${quadTop(fx, fy, tw, pd, u0, v0, u1, v1)}"/>`;
    [[0.06, 0.2], [0.24, 0.38], [0.62, 0.76], [0.8, 0.94]].forEach(([u0, u1]) => { g += plate(u0, u1, 0.18, 0.62, 'plate') + plate(u0 + 0.03, u1 - 0.03, 0.27, 0.53, 'platec'); });
    [[0.43, 0.57, 0.22, 0.42], [0.43, 0.57, 0.5, 0.7]].forEach(([u0, u1, v0, v1]) => { g += plate(u0, u1, v0, v1, 'plate2'); });
    [0.13, 0.31, 0.69, 0.87, 0.5].forEach((u, j) => {
      const a = onTop(fx, fy, tw, pd, u - 0.02, 0.62), b = onTop(fx, fy, tw, pd, u - 0.02, 1.0), c = onTop(fx, fy, tw, pd, u + 0.02, 0.62), d = onTop(fx, fy, tw, pd, u + 0.02, 1.0);
      if (j === 4) { const e = onTop(fx, fy, tw, pd, u, 0.7), z = onTop(fx, fy, tw, pd, u, 1.0); g += `<path class="tube cold" d="M${f1(e[0] - 3)},${f1(e[1])} L${f1(z[0] - 3)},${f1(z[1])}"/><path class="tube hot" d="M${f1(e[0] + 3)},${f1(e[1])} L${f1(z[0] + 3)},${f1(z[1])}"/>`; return; }
      g += `<path class="tube cold" d="M${f1(a[0])},${f1(a[1])} L${f1(b[0])},${f1(b[1])}"/><path class="tube hot" d="M${f1(c[0])},${f1(c[1])} L${f1(d[0])},${f1(d[1])}"/>`;
    });
    o.push(`<g data-part="coldplate">${g}</g>`);
    // 前面板
    g = rect(fx + 1, fy, tw - 2, pr.h, 'bezel', 2);
    for (let x = fx + 26; x < fx + tw - 30; x += 6) for (let yy = fy + 5; yy < fy + pr.h - 4; yy += 5) g += rect(x, yy, 2.6, 2.6, 'hole');
    g += rect(fx + 6, fy + 4, 12, pr.h - 8, 'hdl', 2) + rect(fx + tw - 18, fy + 4, 12, pr.h - 8, 'hdl', 2);
    // 滑軌（拉出來的那段）
    g += line(fx - 2, fy + pr.h + 1.5, ix - 2, pr.y + pr.h + 1.5, 'rail') + line(fx + tw + 2, fy + pr.h + 1.5, ix + iw + 2, pr.y + pr.h + 1.5, 'rail');
    o.push(`<g data-part="compute" data-k="pulled">${g}</g>`);
    const cp = onTop(fx, fy, tw, pd, 0.87, 0.4);
    const mid = (k, n) => { const idx = Object.keys(at).filter((i) => at[i].k === k).map(Number); const i = idx[n == null ? Math.floor(idx.length / 2) : n]; return at[i].y + at[i].h / 2; };
    const P_ = (u, yy) => [X + W + u * D[0], yy + u * D[1]];
    const mf = P_(0.88, Y + H * 0.66);   // 放在交換器與拉出那盤之間的高度，引線才不跟運算托盤那條交叉
    return {
      vb: [40, 20, 470, 540], body: defs(P) + o.join(''),
      anchors: {
        frame: { x: X + W - post / 2, y: Y + 12 },
        psu: { x: ix + iw - 40, y: mid('psu', 0) },
        compute: { x: ix + iw - 40, y: mid('cmp', 1) },
        manifold: { x: mf[0], y: mf[1] },
        switch: { x: ix + iw - 40, y: mid('sw') },
        coldplate: { x: cp[0], y: cp[1], out: null },
        bbu: { x: ix + iw - 40, y: mid('bbu', 0) },
      },
    };
  }

  /* ------------------------------------------------------------------ 通用「大致剖析圖」（kind＝custom：由文章 JSON 描述部件）
     Andy 10-16 追加：「不只這些 是只要設備 都要繪製他的大致剖析圖」→ 任何設備／實體產品都要能畫，不能每種都寫死在程式裡。
     做法：文章 JSON 用幾種積木描述部件（有厚度的方塊、圓柱、一排球、管線），每個積木掛一個 part（＝說明的 id）、
     一種材質（白名單）、可選的細節（白名單：分層、散熱孔、連接埠、鰭片、格線、線路、通孔、風扇、極柱）。
     JSON 裡的字串一律不進 SVG（只拿來比對白名單），數字一律夾在範圍內 —— 文章 JSON 不可能塞出任何標記。
     {"t":"illus","kind":"custom","view":[寬,高],"depth":[dx,dy],
      "shapes":[{"part":"id","type":"box","x":..,"y":..,"w":..,"h":..,"mat":"steel","detail":"fins","n":12,"d":1}, …],
      "parts":[{"id":"id","label":"名稱","sub":"一句話","anchor":[x,y],"out":y}]}
     畫的順序＝陣列順序（後面的蓋前面的）：先畫後面／下面的，再畫前面／上面的。 */
  const MATS = ['chip', 'mem', 'si', 'cu', 'solder', 'abf', 'core', 'pcb', 'steel', 'tray', 'dark', 'battery', 'cold', 'hot', 'plate', 'cap', 'glass', 'plastic', 'fiber', 'magnet', 'rubber'];
  const DETAILS = ['layers', 'vents', 'ports', 'fins', 'grid', 'lines', 'vias', 'fan', 'terminals'];
  const SHAPES = ['box', 'cyl', 'balls', 'pipe'];
  const cnum = (v, lo, hi, fb) => { const x = Number(v); return Number.isFinite(x) ? Math.max(lo, Math.min(hi, x)) : fb; };
  const pid = (v) => (typeof v === 'string' && /^[A-Za-z0-9_-]{1,32}$/.test(v) ? v : '');
  function customSpec(b) {
    const vw = cnum(b && b.view && b.view[0], 100, 2000, 600), vh = cnum(b && b.view && b.view[1], 80, 2000, 400);
    const D = [cnum(b && b.depth && b.depth[0], -200, 200, 40), cnum(b && b.depth && b.depth[1], -200, 200, -24)];
    const shapes = (Array.isArray(b && b.shapes) ? b.shapes : []).slice(0, 80).filter((s) => s && SHAPES.includes(s.type) && pid(s.part)).map((s) => ({
      part: pid(s.part), type: s.type, mat: MATS.includes(s.mat) ? s.mat : 'steel', detail: DETAILS.includes(s.detail) ? s.detail : '',
      x: cnum(s.x, -vw, 2 * vw, 0), y: cnum(s.y, -vh, 2 * vh, 0), w: cnum(s.w, 1, 2 * vw, 40), h: cnum(s.h, 1, 2 * vh, 20),
      d: cnum(s.d, 0, 3, 1), n: Math.round(cnum(s.n, 1, 60, 6)), r: cnum(s.r, 0.5, 200, 6), x2: cnum(s.x2, -vw, 2 * vw, 0), y2: cnum(s.y2, -vh, 2 * vh, 0),
      pts: (Array.isArray(s.points) ? s.points : []).slice(0, 20).filter((p) => Array.isArray(p) && p.length === 2).map((p) => [cnum(p[0], -vw, 2 * vw, 0), cnum(p[1], -vh, 2 * vh, 0)]),
    }));
    return { vw, vh, D, shapes };
  }
  function custom(P, b) {
    const { vw, vh, D, shapes } = customSpec(b);
    const o = [], anchors = {};
    const auto = (id, x, y) => { if (!anchors[id]) anchors[id] = { x, y }; };
    shapes.forEach((s) => {
      let g = '';
      const dd = [D[0] * s.d, D[1] * s.d];
      if (s.type === 'box') {
        g += box(s.x, s.y, s.w, s.h, s.mat, dd);
        const { x, y, w, h, n } = s;
        if (s.detail === 'layers') for (let i = 0; i < n; i++) g += rect(x, y + i * h / n, w, h / n - Math.min(1.2, h / n / 4), i % 2 ? 'ly2' : 'ly1');
        if (s.detail === 'vents') for (let xx = x + 8; xx < x + w - 6; xx += 6) for (let yy = y + 4; yy < y + h - 4; yy += 5) g += rect(xx, yy, 2.6, 2.6, 'hole');
        if (s.detail === 'ports') for (let i = 0; i < n; i++) g += rect(x + 8 + i * (w - 16) / n, y + h * 0.25, Math.max(2, (w - 16) / n - 3), h * 0.5, 'port', 1);
        if (s.detail === 'fins') for (let i = 1; i < n; i++) { const xx = x + i * w / n; g += line(xx, y, xx, y + h, 'fin') + line(xx, y, xx + dd[0], y + dd[1], 'fin'); }
        if (s.detail === 'grid') { [1 / 3, 2 / 3].forEach((u) => { const a = onTop(x, y, w, dd, u, 0.1), c = onTop(x, y, w, dd, u, 0.9); g += line(a[0], a[1], c[0], c[1], 'grid'); }); const a = onTop(x, y, w, dd, 0.05, 0.5), c = onTop(x, y, w, dd, 0.95, 0.5); g += line(a[0], a[1], c[0], c[1], 'grid'); }
        if (s.detail === 'lines') for (let i = 1; i <= n; i++) g += line(x, y + i * h / (n + 1), x + w, y + i * h / (n + 1), 'cuIn');
        if (s.detail === 'vias') for (let i = 0; i < n; i++) g += rect(x + (i + 0.5) * w / n - 1.4, y, 2.8, h, 'cu');
        if (s.detail === 'fan') { const r = Math.min(w, h) / 2 - 3, cx = x + w / 2, cy = y + h / 2; g += `<circle class="fan" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"/>`; for (let i = 0; i < 5; i++) { const a = i * 2 * Math.PI / 5; g += `<path class="blade" d="M${f1(cx)},${f1(cy)} Q${f1(cx + Math.cos(a) * r * 0.9)},${f1(cy + Math.sin(a) * r * 0.2)} ${f1(cx + Math.cos(a + 0.6) * r * 0.9)},${f1(cy + Math.sin(a + 0.6) * r * 0.9)}Z"/>`; } g += `<circle class="hub" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r * 0.28)}"/>`; }
        if (s.detail === 'terminals') { const tw = Math.min(14, w / 5), th = Math.min(8, h / 3); g += rect(x + w * 0.2, y - th, tw, th, 'term', 1) + rect(x + w * 0.8 - tw, y - th, tw, th, 'term', 1); const cy = y + h / 2; g += line(x + w * 0.2, cy, x + w * 0.2 + 8, cy, 'sign') + line(x + w * 0.2 + 4, cy - 4, x + w * 0.2 + 4, cy + 4, 'sign') + line(x + w * 0.8 - 8, cy, x + w * 0.8, cy, 'sign'); }
        auto(s.part, x + w * 0.85, y + h / 2);
      } else if (s.type === 'cyl') {
        // 直立圓柱：上面一個橢圓、側面、下緣半個橢圓（w＝直徑，h＝高）
        const rx = s.w / 2, ry = Math.max(2, Math.abs(D[1]) * 0.35), cx = s.x + rx;
        g += `<g class="m-${s.mat}"><path class="f" d="M${f1(s.x)},${f1(s.y)} V${f1(s.y + s.h)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(s.x + s.w)},${f1(s.y + s.h)} V${f1(s.y)} Z"/>`
          + `<ellipse class="t" cx="${f1(cx)}" cy="${f1(s.y)}" rx="${f1(rx)}" ry="${f1(ry)}"/></g>`;
        if (s.detail === 'layers') for (let i = 1; i < s.n; i++) { const yy = s.y + i * s.h / s.n; g += `<path class="ring" d="M${f1(s.x)},${f1(yy)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(s.x + s.w)},${f1(yy)}"/>`; }
        if (s.detail === 'terminals') g += rect(cx - rx * 0.3, s.y - ry - 6, rx * 0.6, 7, 'term', 1);
        auto(s.part, s.x + s.w * 0.9, s.y + s.h / 2);
      } else if (s.type === 'balls') {
        // 一排球：從 (x, y) 到 (x2, y)，n 顆，半徑 r（焊球、凸塊、滾珠……）
        const x2 = s.x2 > s.x ? s.x2 : s.x + s.w;
        for (let i = 0; i < s.n; i++) { const cx = s.n > 1 ? s.x + i * (x2 - s.x) / (s.n - 1) : s.x; g += circ(cx, s.y, s.r, P + (s.mat === 'cu' ? 'cu' : 'sol')); }
        auto(s.part, x2, s.y);
      } else if (s.type === 'pipe' && s.pts.length >= 2) {
        g += `<path class="tube ${s.mat === 'hot' ? 'hot' : s.mat === 'cold' ? 'cold' : 'gen m-' + s.mat}" style="stroke-width:${f1(cnum(s.r, 0.5, 30, 2.2))}" d="M${s.pts.map((p) => f1(p[0]) + ',' + f1(p[1])).join(' L')}"/>`;
        const a = s.pts[0], c = s.pts[1], L = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1, t = Math.min(1, 12 / L); auto(s.part, a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t);   // 起點往第二點走一小段（起點常被別的部件蓋住）
      }
      if (g) o.push(`<g data-part="${s.part}" class="m-${s.mat}">${g}</g>`);   // 外層也掛材質：分層、鰭片這些細節才吃得到 --m
    });
    // 文章 JSON 指定的錨點／out 蓋過自動錨點
    (Array.isArray(b && b.parts) ? b.parts : []).forEach((p) => {
      const id = pid(p && p.id); if (!id || !anchors[id]) return;
      if (Array.isArray(p.anchor) && p.anchor.length === 2) anchors[id] = { x: cnum(p.anchor[0], -vw, 2 * vw, anchors[id].x), y: cnum(p.anchor[1], -vh, 2 * vh, anchors[id].y) };
      if (p.out != null) anchors[id].out = cnum(p.out, -vh, 2 * vh, anchors[id].y);
    });
    return { vb: [0, 0, vw, vh], body: defs(P) + o.join(''), anchors };
  }

  const KINDS = { cowos: { draw: cowos, parts: COWOS_PARTS }, rack: { draw: rack, parts: RACK_PARTS }, custom: { draw: custom, parts: null } };

  const CSS = `
:root{--il-gpu:#5f87d8;--il-hbm:#2a9d93;--il-dram1:#36b3a6;--il-dram2:#24857c;--il-base:#1d6a63;--il-si:#9a907a;--il-rdl:#c9bf9f;--il-cu:#e39555;--il-sol:#c4ccd8;
  --il-abf:#8a6a4a;--il-core:#5e4732;--il-pcb:#2f7a62;--il-cap:#c9a46a;--il-hs:#7fe7ff;--il-act:#9fb7ee;
  --il-steel:#56637e;--il-bezel:#232c40;--il-bezel2:#2b3550;--il-hole:#0c111c;--il-port:#0e1422;--il-hdl:#8d9ab4;--il-psu:#3a4663;--il-fan:#18202f;
  --il-bat:#3d5a8a;--il-charge:#7fc8ff;--il-term:#d6b36a;--il-cold:#4aa3ff;--il-hot:#ff7a55;--il-plate:#d8945a;--il-plate2:#c7a07a;--il-tray:#4a5675;--il-cave:#0a0f1a;--il-led:#5fe3a0;
  --il-glass:#7fb6d9;--il-plastic:#3b4252;--il-fiber:#f2c14e;--il-magnet:#8c96a8;--il-rubber:#2a2f3a;--il-shadow:rgba(0,0,0,.55);--il-hi:#ffffff;--il-lo:#000000;--il-sign:#ffffff;--il-edge:rgba(0,0,0,.45)}
:root[data-theme="light"]{--il-gpu:#4f78cc;--il-hbm:#2c968c;--il-dram1:#41b1a4;--il-dram2:#2b8a80;--il-base:#22706a;--il-si:#b2a78b;--il-rdl:#d9d0b4;--il-cu:#c9702f;--il-sol:#a9b2c2;
  --il-abf:#a07a52;--il-core:#76583b;--il-pcb:#3b8c70;--il-cap:#b48a48;--il-hs:#0aa0c8;--il-act:#8fa8e0;
  --il-steel:#8592ab;--il-bezel:#3a445c;--il-bezel2:#4a5570;--il-hole:#1a2030;--il-port:#1c2333;--il-hdl:#c3cbdb;--il-psu:#5a6684;--il-fan:#2a3242;
  --il-bat:#4b6ea6;--il-charge:#9fd6ff;--il-term:#c39a45;--il-cold:#2a7fd8;--il-hot:#e2572f;--il-plate:#c97f42;--il-plate2:#b78c63;--il-tray:#6b7896;--il-cave:#2a3142;--il-led:#2fbf7a;
  --il-glass:#9ccbe8;--il-plastic:#5a6274;--il-fiber:#c99a1e;--il-magnet:#9aa3b3;--il-rubber:#3a404c;--il-shadow:rgba(30,40,60,.28);--il-hi:#ffffff;--il-lo:#1a2030;--il-sign:#ffffff;--il-edge:rgba(20,25,40,.4)}
.ilsvg{display:block;width:100%;height:auto;overflow:visible}
.ilsvg [class^="m-"]{--m:var(--il-steel)}
.ilsvg .m-gpu{--m:var(--il-gpu)}.ilsvg .m-hbm{--m:var(--il-hbm)}.ilsvg .m-si{--m:var(--il-si)}.ilsvg .m-abf{--m:var(--il-abf)}.ilsvg .m-pcb{--m:var(--il-pcb)}
.ilsvg .m-cap{--m:var(--il-cap)}.ilsvg .m-steel{--m:var(--il-steel)}.ilsvg .m-tray{--m:var(--il-tray)}
.ilsvg .m-chip{--m:var(--il-gpu)}.ilsvg .m-mem{--m:var(--il-hbm)}.ilsvg .m-cu{--m:var(--il-cu)}.ilsvg .m-solder{--m:var(--il-sol)}.ilsvg .m-core{--m:var(--il-core)}
.ilsvg .m-dark{--m:var(--il-bezel)}.ilsvg .m-battery{--m:var(--il-bat)}.ilsvg .m-cold{--m:var(--il-cold)}.ilsvg .m-hot{--m:var(--il-hot)}.ilsvg .m-plate{--m:var(--il-plate)}
.ilsvg .m-glass{--m:var(--il-glass)}.ilsvg .m-plastic{--m:var(--il-plastic)}.ilsvg .m-fiber{--m:var(--il-fiber)}.ilsvg .m-magnet{--m:var(--il-magnet)}.ilsvg .m-rubber{--m:var(--il-rubber)}
.ilsvg .ly1{fill:color-mix(in srgb,var(--m) 88%,var(--il-hi))}.ilsvg .ly2{fill:color-mix(in srgb,var(--m) 80%,var(--il-lo))}
.ilsvg .fin{stroke:color-mix(in srgb,var(--m) 55%,var(--il-lo));stroke-width:1.2}
.ilsvg .ring{fill:none;stroke:color-mix(in srgb,var(--m) 55%,var(--il-lo));stroke-width:1}
.ilsvg .blade{fill:color-mix(in srgb,var(--il-hdl) 70%,var(--il-fan));opacity:.85}.ilsvg .hub{fill:var(--il-hdl)}
.ilsvg .tube.gen{stroke:var(--m)}
.ilsvg .f{fill:var(--m)}.ilsvg .t{fill:color-mix(in srgb,var(--m) 70%,var(--il-hi))}.ilsvg .r{fill:color-mix(in srgb,var(--m) 62%,var(--il-lo))}
.ilsvg .f,.ilsvg .t,.ilsvg .r{stroke:var(--il-edge);stroke-width:.6;stroke-linejoin:round}
.ilsvg .shadow{fill:var(--il-shadow)}
.ilsvg .cu{fill:var(--il-cu)}.ilsvg .cuIn{stroke:color-mix(in srgb,var(--il-cu) 60%,var(--il-pcb));stroke-width:1.2;stroke-dasharray:22 6}
.ilsvg .pad{fill:var(--il-cu)}.ilsvg .ball{stroke:var(--il-edge);stroke-width:.4}
.ilsvg .core{fill:var(--il-core)}.ilsvg .rdl{fill:var(--il-rdl);opacity:.55}
.ilsvg .hs{fill:none;stroke:var(--il-hs);stroke-width:1.6;stroke-linejoin:round}
.ilsvg .base{fill:var(--il-base)}.ilsvg .dram1{fill:var(--il-dram1)}.ilsvg .dram2{fill:var(--il-dram2)}
.ilsvg .gl{pointer-events:none}
.ilsvg .act{fill:color-mix(in srgb,var(--il-act) 55%,var(--il-gpu))}.ilsvg .actc{fill:var(--il-act);opacity:.75}
.ilsvg .grid{stroke:color-mix(in srgb,var(--il-gpu) 45%,var(--il-hi));stroke-width:.9;opacity:.8}.ilsvg .gridb{fill:none;stroke:color-mix(in srgb,var(--il-gpu) 45%,var(--il-hi));stroke-width:.9;opacity:.8}
.ilsvg .cave{fill:var(--il-cave)}.ilsvg .vent{stroke:color-mix(in srgb,var(--il-steel) 55%,var(--il-lo));stroke-width:2;stroke-linecap:round}
.ilsvg .bezel{fill:var(--il-bezel);stroke:var(--il-edge);stroke-width:.6}.ilsvg .bezel2{fill:var(--il-bezel2);stroke:var(--il-edge);stroke-width:.6}
.ilsvg .hole{fill:var(--il-hole)}.ilsvg .hdl{fill:var(--il-hdl)}.ilsvg .port{fill:var(--il-port);stroke:color-mix(in srgb,var(--il-hdl) 50%,transparent);stroke-width:.5}
.ilsvg .psum{fill:var(--il-psu)}.ilsvg .fan{fill:var(--il-fan);stroke:var(--il-hdl);stroke-width:.8}.ilsvg .fanb{stroke:var(--il-hdl);stroke-width:.7;opacity:.7}
.ilsvg .led{fill:var(--il-led)}
.ilsvg .bat{fill:var(--il-bat);stroke:var(--il-edge);stroke-width:.6}.ilsvg .term{fill:var(--il-term)}.ilsvg .sign{stroke:var(--il-sign);stroke-width:1.4;stroke-linecap:round}
.ilsvg .charge{fill:var(--il-charge);opacity:.55}
.ilsvg .slot{fill:var(--il-cave);stroke:var(--il-edge);stroke-width:.6}
.ilsvg .postf{fill:var(--il-steel);stroke:var(--il-edge);stroke-width:.6}.ilsvg .phole{fill:var(--il-cave)}
.ilsvg .pipe{stroke:var(--il-edge);stroke-width:.6}.ilsvg .pipe.cold{fill:var(--il-cold)}.ilsvg .pipe.hot{fill:var(--il-hot)}
.ilsvg .hose,.ilsvg .tube{fill:none;stroke-width:2.2;stroke-linecap:round}.ilsvg .hose.cold,.ilsvg .tube.cold{stroke:var(--il-cold)}.ilsvg .hose.hot,.ilsvg .tube.hot{stroke:var(--il-hot)}
.ilsvg .qd{fill:var(--il-hdl)}
.ilsvg .plate{fill:var(--il-plate);stroke:var(--il-edge);stroke-width:.6}.ilsvg .platec{fill:color-mix(in srgb,var(--il-plate) 70%,var(--il-hi));opacity:.7}.ilsvg .plate2{fill:var(--il-plate2);stroke:var(--il-edge);stroke-width:.6}
.ilsvg .rail{stroke:var(--il-hdl);stroke-width:2.4;stroke-linecap:round}
.ilsvg [data-part]{transition:opacity .15s}
`;
  function css() {
    if (document.getElementById('artIlCss')) return;
    const s = document.createElement('style'); s.id = 'artIlCss'; s.textContent = CSS; document.head.appendChild(s);
  }
  let seq = 0;
  window.TwArtIllus = {
    has: (k) => Object.prototype.hasOwnProperty.call(KINDS, k),
    /* 說明清單：內建 kind ＝ 預設說明（文章 JSON 的 parts 只換文字、只列幾個就只標那幾個）；custom ＝ 文章 JSON 的 parts（id 要對得到圖上的部件）。
       編號由上而下（照錨點高度排），說明欄的順序才會跟圖上的層一致、引線不交叉 */
    parts(k, given, b) {
      const K = KINDS[k]; if (!K) return [];
      const g = Array.isArray(given) ? given.filter((x) => x && pid(x.id)) : [];
      const A = K.draw('ilx_', b).anchors, yy = (id) => { const a = A[id]; return a ? (a.out != null ? a.out : a.y) : 1e9; };
      let pick;
      if (!K.parts) {
        const seen = new Set();
        pick = g.filter((x) => A[x.id] && !seen.has(x.id) && seen.add(x.id)).map((x) => ({ id: x.id, label: String(x.label || x.id), sub: x.sub != null ? String(x.sub) : '' }));
        return pick.sort((a, c) => yy(a.id) - yy(c.id));
      }
      pick = g.length ? K.parts.filter((p) => g.some((x) => x.id === p.id)) : K.parts;
      return pick.slice().sort((a, c) => yy(a.id) - yy(c.id)).map((p) => { const x = g.find((y) => y.id === p.id) || {}; return { id: p.id, label: x.label || p.label, sub: x.sub != null ? x.sub : p.sub }; });
    },
    anchors(k, b) { const K = KINDS[k]; return K ? K.draw('ilx_', b).anchors : null; },
    draw(k, b) {
      css();
      const K = KINDS[k]; if (!K) return null;
      return K.draw('il' + (++seq) + '_', b);
    },
  };
})();
