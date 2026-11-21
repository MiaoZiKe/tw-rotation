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
    if (V2.on) return box2(x, y, w, h, LEG2[m] || m, d, {});   // 第 2 版（style:2）：新色票＋光影；舊圖走下面原本那幾行，一個字都沒改
    const [dx, dy] = d;
    return `<g class="m-${m}${extra ? ' ' + extra : ''}">`
      + `<polygon class="t" points="${pts([[x, y], [x + w, y], [x + w + dx, y + dy], [x + dx, y + dy]])}"/>`
      + `<polygon class="r" points="${pts([[x + w, y], [x + w + dx, y + dy], [x + w + dx, y + h + dy], [x + w, y + h]])}"/>`
      + `<rect class="f" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"/></g>`;
  }
  const rect = (x, y, w, h, cls, rx) => `<rect class="${cls}" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''}/>`;
  const line = (x1, y1, x2, y2, cls) => `<line class="${cls}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}"/>`;
  const circ = (cx, cy, r, fill) => V2.on ? ball2(cx, cy, r, /cu$/.test(fill) ? 'cu' : 'solder', 0, 0) : `<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="url(#${fill})" class="ball"/>`;
  /* 上面（斜面）上的點：原點＋u×寬＋v×深度 */
  const onTop = (x, y, w, d, u, v) => [x + u * w + v * d[0], y + v * d[1]];
  const quadTop = (x, y, w, d, u0, v0, u1, v1) => pts([onTop(x, y, w, d, u0, v0), onTop(x, y, w, d, u1, v0), onTop(x, y, w, d, u1, v1), onTop(x, y, w, d, u0, v1)]);

  /* 共用漸層（id 帶前綴，同一頁多張圖不撞名） */
  function defs(P) {
    if (V2.on) return defs2(P);
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
    if (!V2.on) o.push(`<ellipse class="shadow" cx="300" cy="${Y.pcb + Y.pcbH + 6}" rx="290" ry="9" filter="url(#${P}sh)"/>`);   // 第 2 版不准用模糊濾鏡當影子
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
    const ub = V2.on ? (a, b) => { for (let x = a + 3; x <= b; x += 11) g += circ(x, Y.ub, 4.9, P + 'cu'); }   // 第 2 版：手機上球半徑要 ≥ 2.5px → 放大、減顆數（示意）
      : (a, b) => { for (let x = a; x <= b; x += 8) g += circ(x, Y.ub, Y.ubR, P + 'cu'); };
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
    if (!V2.on) o.push(`<ellipse class="shadow" cx="${X + W / 2 + 50}" cy="${Y + H + 4}" rx="190" ry="10" filter="url(#${P}sh)"/>`);
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

  /* ================================================================== 第 2 版（插圖 JSON 帶 "style": 2 才用）—— 2026-10-17
     Andy 10-17：「自動產精選文章，之後的圖需要再更細緻，顏色不要太單一……這次先不改（指已上架的 HBM 那張）」
     規格：docs/articles/illus_style.md（動畫單位撰寫）。沒帶 style 的舊圖（CoWoS、AI 機櫃、HBM…）完全照上面原本的畫法，不受影響。
     · 色票：27 種 mat × 深淺各一組。tone 0 的 頂／正／側／漸層起訖／邊／高光 直接抄規格 2.3 節的 hex 表；
       tone（−2～+2，每階 L ±0.05）、遠處（L −0.04、C ×0.9）、側面加暗、圓柱、分層這些衍生色照規格 2.2 節的 OKLCH 公式現算。
       色票寫成 CSS 變數（--q-<mat>_<tone>-<面>），深淺主題只換變數值；用到哪一組才把那一組寫進 <style>（不一次塞全部）。
     · 光影：正面由上往下漸層、側面由前往後加暗、頂面前緣高光帶、兩條稜線高光、倒角亮線、邊線 1.0、接觸陰影（只畫在下面那個零件的頂面上、裁在頂面內）、
       深色主題的深色材質加輪廓光。不准模糊濾鏡、外光暈、drop-shadow、閃爍。
     · 細節：規格 3.3 的 9 種舊細節加密度、3.4 的 10 種新細節；一個積木可以掛多種細節（detail 給陣列）。
     · 安全：JSON 的字串一律只拿來比對白名單（mat／detail／type／bmat），進到 SVG 的只有白名單裡的字與夾過值的數字。 */
  const MATS2 = MATS.concat(['logic', 'mold', 'underfill', 'gold', 'tim', 'ceramic']);
  const DETAILS2 = DETAILS.concat(['bumps', 'traces', 'label', 'pads', 'seal', 'screws', 'pins', 'hatch', 'wires', 'mesh']);
  const SHAPES2 = SHAPES.concat(['guide', 'wheel', 'hcyl', 'shell']);   // 10-17 晚：wheel（側視車輪）、hcyl（橫躺圓柱）、shell（車殼／外殼剖面）—— 只有 style:2 認得
  const BMATS = ['solder', 'cu', 'gold'];
  const LEG2 = { gpu: 'chip', hbm: 'mem' };           // 內建 kind 的舊材質名 → 新色票
  const BUILTIN2 = ['chip', 'mem', 'logic', 'si', 'cu', 'solder', 'abf', 'core', 'pcb', 'cap', 'steel', 'dark', 'tray', 'battery', 'gold', 'cold', 'hot', 'plate', 'plastic'];
  const RIM = new Set(['core', 'tray', 'dark', 'plastic', 'rubber', 'mold']);                                          // 深色主題加輪廓光（規格 3.1）
  const LITE = new Set(['si', 'solder', 'plate', 'glass', 'fiber', 'underfill', 'gold', 'tim', 'ceramic']);         // 淺色主題邊線加粗到 1.2（規格 2.1）
  /* OKLCH 參數（規格 2.3 第一張表）：[色相 H, 彩度 C, 正面亮度 L（深）, 正面亮度 L（淺）] */
  const PAL = { chip: [262, 0.135, 0.6, 0.54], mem: [322, 0.1, 0.6, 0.54], logic: [195, 0.085, 0.6, 0.53], si: [255, 0.018, 0.68, 0.66], cu: [55, 0.125, 0.7, 0.6], solder: [85, 0.014, 0.86, 0.8], abf: [105, 0.085, 0.62, 0.58], core: [55, 0.055, 0.47, 0.44], pcb: [155, 0.085, 0.52, 0.5], steel: [250, 0.025, 0.62, 0.58], tray: [255, 0.055, 0.48, 0.5], dark: [262, 0.02, 0.36, 0.38], battery: [232, 0.095, 0.58, 0.52], cold: [245, 0.125, 0.66, 0.56], hot: [35, 0.14, 0.68, 0.58], plate: [72, 0.065, 0.74, 0.66], cap: [60, 0.05, 0.6, 0.56], glass: [215, 0.045, 0.8, 0.74], plastic: [262, 0.02, 0.46, 0.46], fiber: [92, 0.12, 0.82, 0.7], magnet: [240, 0.018, 0.66, 0.62], rubber: [250, 0.01, 0.32, 0.34], mold: [265, 0.012, 0.33, 0.36], underfill: [80, 0.075, 0.8, 0.74], gold: [90, 0.115, 0.78, 0.68], tim: [240, 0.008, 0.72, 0.66], ceramic: [85, 0.018, 0.88, 0.84] };
  /* 規格 2.3 的 hex 表（頂、正、側、漸層起、漸層訖、邊、高光），深色卡片底 #0F1C2F、淺色 #F1F6FA —— 直接抄 */
  const HEX_D = 'chip:749BE2,527ED0,2E549F,5C89DC,446FC0,0C2963,A9BFE6;mem:B48ABB,9C6BA4,704577,A776AF,8D5D94,401E45,CCB5CF;logic:62AAA9,349090,076565,419B9B,208181,023536,A2C6C5;si:AEB5BE,9199A4,686F79,9CA4AE,828A94,3D434A,D4D8DD;cu:F0A877,D9884D,A95F25,E59358,C9783D,6E3602,FDD5BB;solder:F2EEE6,D5D0C7,A8A49B,E1DCD2,C5C0B7,77746D,F7F5F0;abf:A8A46F,8E894A,646024,989454,7F7A3B,383400,C7C6AA;core:8B6E5A,73533D,4A2E1A,7E5C46,65452F,1D0900,A29287;pcb:5F9070,3C7753,154F2F,47825D,2D6945,00220F,92AC9A;steel:98A3AF,7B8895,545F6B,8692A0,6D7986,2B343D,BFC5CB;tray:657993,485F7D,253953,526987,3B516E,041224,8E99A8;dark:50555F,373D48,161B24,414751,2B313B,03060B,72757A;battery:5F9EBF,3484A9,045A7B,408EB4,227599,012D40,9DBDCE;cold:72B5ED,4799D9,1B6EA8,52A4E5,3689C9,014069,B3D6F4;hot:F69880,E1755A,AE4D35,ED8065,CF664C,722612,FEC9BC;plate:DEC2A1,C5A57E,977A57,D0B088,B5956F,654E32,F8E9D6;cap:B09681,977A62,6C523D,A2846C,886B54,3D2919,C9BBB0;glass:BFE2EB,9EC6D0,7599A3,A8D1DB,8EB6C0,4C6970,E7F9FE;plastic:6C727C,525864,2E333D,5C626E,444B56,090D14,8F9298;fiber:FAE091,E0C262,B2963A,EBCD6E,D0B252,7D671A,FFF5D7;magnet:A6AFB7,89949C,606A72,939FA7,7A858D,373E44,CCD2D6;rubber:474B4F,2F3338,0E1216,383C41,23272B,040608,67696B;mold:4A4D53,32353C,111419,3B3E45,26292F,040609,6A6C6F;underfill:F1D7AC,D7B986,A98E5F,E3C491,C7A977,75603B,FEF4E2;gold:EDD288,D4B45A,A68932,DFBF66,C4A44A,725B0F,FFF5D9;tim:BDC1C5,A0A5A9,767B7E,ABB0B4,91969A,4A4E50,E2E5E7;ceramic:F3EEE3,DDD7CA,B0AA9F,E8E2D6,CDC7BA,7E7A71,F8F5EF';
  const HEX_L = 'chip:6288CE,416CBC,1E438C,4B76C8,335DAC,011951,96ACD2;mem:A278A8,8A5A91,5F3466,94649C,7B4C82,300F35,B9A2BC;logic:4C9494,177B7B,055050,278585,046C6C,012222,8CB0AF;si:A8AFB8,8B939D,626A73,969EA8,7C848E,383E45,CDD1D6;cu:CE8959,B8692C,864302,C47438,A85A19,492200,DBB59C;solder:DEDAD2,C2BDB4,969289,CDC8BF,B2ADA4,66635C,F7F5F0;abf:9C9863,827D3E,595517,8C8848,736E2F,2D2A01,BBB99D;core:826552,6A4A35,422612,75543E,5C3D27,140500,99897E;pcb:598A6A,36714E,0D492A,417C57,276340,001C0B,8CA694;steel:8C97A2,6F7C89,49545F,7A8694,616D7A,212A33,B2B8BE;tray:6B7F99,4E6582,2A3E58,586F8D,405774,071629,94A0AE;dark:565B65,3D434D,1A1F28,464C57,303640,03060B,777A80;battery:4D8CAB,1E7296,034964,2C7CA1,036387,011E2B,8AAABB;cold:5395CC,237AB8,025182,3085C4,0A6BA8,012641,94B6D3;hot:D47962,BE563D,8D2E17,CA6147,AD472E,4E0E00,DCAA9C;plate:C4A988,AB8C66,7F6340,B69770,9C7D57,4E381D,DDCEBD;cap:A38A76,8B6E57,614732,957861,7C6049,321F0F,BCAEA3;glass:ACCED7,8BB3BD,638790,96BEC8,7CA3AD,3B585F,DDEFF4;plastic:6C727C,525864,2E333D,5C626E,444B56,090D14,8F9298;fiber:D2B96B,B99C3A,8D7102,C4A746,A98C26,584600,EBDEB6;magnet:99A3AA,7D8890,555F66,87929B,6E7981,2C343A,C0C5C9;rubber:4C5054,34383D,13161A,3D4246,282C30,040608,6D6F71;mold:52555B,3A3D44,181B20,43464D,2D3037,040609,737478;underfill:DDC399,C4A674,977C4E,CFB17F,B49765,644F2A,F7E9D2;gold:CCB269,B49539,876B04,BFA045,A48526,524003,E5D7B1;tim:AAAFB2,8E9397,656A6D,999EA1,7F8488,3A3E40,CFD1D3;ceramic:EDE7DD,D0CABE,A39E93,DBD5C9,C0BAAE,726E65,F8F5EF';
  const HEXT = {};
  [['d', HEX_D], ['l', HEX_L]].forEach(([th, src]) => src.split(';').forEach((row) => { const [m, v] = row.split(':'); (HEXT[m] = HEXT[m] || {})[th] = v.split(',').map((x) => '#' + x); }));
  /* OKLCH → sRGB hex；超出色域時每次降 C 0.002 直到可顯示（規格附錄的做法） */
  function okHex(L, C, H) {
    L = Math.max(0.04, Math.min(0.97, L)); C = Math.max(0, C);
    const hr = H * Math.PI / 180;
    let rgb;
    for (;;) {
      const a = C * Math.cos(hr), b = C * Math.sin(hr);
      const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
      rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
      if (C <= 0 || rgb.every((x) => x >= -1e-9 && x <= 1 + 1e-9)) break;
      C = Math.max(0, C - 0.002);
    }
    return '#' + rgb.map((x) => { x = Math.max(0, Math.min(1, x)); const v = x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055; return Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0'); }).join('').toUpperCase();
  }
  /* 一組色（某 mat、某 tone、遠近）：t 頂 f 正 s 側（前）s1 側（後）g0/g1 正面漸層 e 邊 h 高光 c0/c1 圓柱受光 l1/l2 分層兩色
     back：0 不變；1 遠處（L −0.04、C ×0.9，規格 3.5）；2 錫球後排（L −0.06，規格 3.2） */
  const VN = ['t', 'f', 's', 's1', 'g0', 'g1', 'e', 'h', 'c0', 'c1', 'l1', 'l2'];
  function vcol(m, tone, back, th) {
    const p = PAL[m]; const H = p[0], L = (th === 'l' ? p[3] : p[2]) + 0.05 * tone - (back === 1 ? 0.04 : back === 2 ? 0.06 : 0), C = p[1] * (back === 1 ? 0.9 : 1);
    const o = { t: okHex(L + 0.09, C * 0.85, H), f: okHex(L, C, H), s: okHex(L - 0.14, C * 0.95, H), s1: okHex(L - 0.18, C * 0.95, H), g0: okHex(L + 0.035, C, H), g1: okHex(L - 0.05, C, H),
      e: okHex(L - 0.30, C * 0.8, H), h: okHex(L + 0.20, C * 0.45, H), c0: okHex(L - 0.10, C, H), c1: okHex(L + 0.06, C, H), l1: okHex(L + 0.05, C, H), l2: okHex(L - 0.05, C, H) };
    if (!tone && !back) { const x = HEXT[m][th === 'l' ? 'l' : 'd']; ['t', 'f', 's', 'g0', 'g1', 'e', 'h'].forEach((k, i) => { o[k] = x[i]; }); }
    return o;
  }
  const vkey = (m, tone, back) => m + '_' + (tone < 0 ? 'm' + (-tone) : 'p' + tone) + (back === 1 ? 'b' : back === 2 ? 'c' : '');
  const EMIT = new Set();
  function css2(txt) {
    if (typeof document === 'undefined') return;
    let s = document.getElementById('artIlCss2');
    if (!s) { s = document.createElement('style'); s.id = 'artIlCss2'; s.textContent = CSS2; document.head.appendChild(s); }
    if (txt) s.textContent += txt;
  }
  /* 用到某一組色：第一次用到才把它的 CSS 變數（深、淺）與 .k-<組> 的對照寫進樣式；同時記在這張圖的 defs 清單 */
  function useV(m, tone, back) {
    if (!PAL[m]) m = 'steel';
    tone = Math.max(-2, Math.min(2, Math.round(tone || 0))); back = back === 1 || back === 2 ? back : 0;
    const k = vkey(m, tone, back);
    if (!EMIT.has(k)) {
      EMIT.add(k);
      const d = vcol(m, tone, back, 'd'), l = vcol(m, tone, back, 'l');
      css2(`.ilsvg.ilv2{${VN.map((n) => `--q-${k}-${n}:${d[n]}`).join(';')}}:root[data-theme="light"] .ilsvg.ilv2{${VN.map((n) => `--q-${k}-${n}:${l[n]}`).join(';')}}`
        + `.ilsvg.ilv2 .k-${k}{${VN.map((n) => `--m${n}:var(--q-${k}-${n})`).join(';')}}`);
    }
    if (V2.used) V2.used.add(k);
    return k;
  }
  const qv = (m, n, tone) => `var(--q-${useV(m, tone || 0, 0)}-${n})`;   // 直接拿某材質的某個色（細節用：金接點、銅線、底部填充膠…）
  /* 每張圖一份的漸層（id 帶前綴）＋裁切路徑；stop-color 吃 CSS 變數，換主題只換變數值 */
  function defs2(P) {
    let s = '<defs>';
    (V2.used || new Set()).forEach((k) => {
      const v = (n) => `var(--q-${k}-${n})`;
      s += `<linearGradient id="${P}f-${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${v('g0')}"/><stop offset="1" style="stop-color:${v('g1')}"/></linearGradient>`
        + `<linearGradient id="${P}s-${k}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:${v('s')}"/><stop offset="1" style="stop-color:${v('s1')}"/></linearGradient>`
        + `<linearGradient id="${P}hb-${k}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" style="stop-color:${v('h')};stop-opacity:.35"/><stop offset="1" style="stop-color:${v('h')};stop-opacity:0"/></linearGradient>`
        + `<linearGradient id="${P}c-${k}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:${v('c0')}"/><stop offset=".3" style="stop-color:${v('c1')}"/><stop offset=".7" style="stop-color:${v('f')}"/><stop offset="1" style="stop-color:${v('s')}"/></linearGradient>`
        + `<radialGradient id="${P}b-${k}" cx=".36" cy=".32" r=".75"><stop offset="0" style="stop-color:${v('t')}"/><stop offset=".55" style="stop-color:${v('f')}"/><stop offset="1" style="stop-color:${v('s')}"/></radialGradient>`;
    });
    (V2.vg || new Set()).forEach((k) => {   // 橫躺圓柱的筒身：由上往下受光（只有用到 hcyl 的色組才產生，舊圖的 defs 不變）
      const v = (n) => `var(--q-${k}-${n})`;
      s += `<linearGradient id="${P}v-${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${v('f')}"/><stop offset=".24" style="stop-color:${v('c1')}"/><stop offset=".55" style="stop-color:${v('f')}"/><stop offset="1" style="stop-color:${v('s1')}"/></linearGradient>`;
    });
    s += `<linearGradient id="${P}csx" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--il-shadow)"/><stop offset="1" style="stop-color:var(--il-shadow);stop-opacity:0"/></linearGradient>`
      + `<linearGradient id="${P}csy" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--il-shadow)"/><stop offset="1" style="stop-color:var(--il-shadow);stop-opacity:0"/></linearGradient>`
      + `<linearGradient id="${P}gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--il2-hi);stop-opacity:.06"/><stop offset="1" style="stop-color:var(--il2-hi);stop-opacity:0"/></linearGradient>`;
    return s + (V2.clips || []).join('') + '</defs>';
  }
  const V2 = { on: false, used: null, clips: null, vg: null, P: '', seq: 0 };
  const clipPoly = (points) => { const id = V2.P + 'cp' + (++V2.seq); V2.clips.push(`<clipPath id="${id}"><polygon points="${pts(points)}"/></clipPath>`); return id; };
  const clipRect = (x, y, w, h) => { const id = V2.P + 'cp' + (++V2.seq); V2.clips.push(`<clipPath id="${id}"><rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"/></clipPath>`); return id; };

  /* 方塊（第 2 版）：頂面＋前緣高光帶、側面（由前往後加暗）、正面（由上往下漸層）、兩條稜線高光、倒角亮線、邊線；inner＝細節（畫在同一組裡，吃得到這組的 --m* 色） */
  function box2(x, y, w, h, m, d, o, inner) {
    o = o || {};
    const k = useV(m, o.tone, o.back), [dx, dy] = d, P = V2.P;
    let s = `<g class="qk k-${k}${RIM.has(m) ? ' rim' : ''}${LITE.has(m) ? ' lite' : ''}">`;
    s += `<polygon class="qt" points="${pts([[x, y], [x + w, y], [x + w + dx, y + dy], [x + dx, y + dy]])}"/>`;
    if (Math.abs(dy) >= 2) s += `<polygon class="qb" points="${pts([[x, y], [x + w, y], [x + w + 0.3 * dx, y + 0.3 * dy], [x + 0.3 * dx, y + 0.3 * dy]])}" style="fill:url(#${P}hb-${k})"/>`;
    if (Math.abs(dx) >= 1) s += `<polygon class="qr" points="${pts([[x + w, y], [x + w + dx, y + dy], [x + w + dx, y + h + dy], [x + w, y + h]])}" style="fill:url(#${P}s-${k})"/>`;
    s += `<rect class="qf" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" style="fill:url(#${P}f-${k})"/>`;
    s += o.under || '';
    s += `<path class="qhl" d="M${f1(x + 0.5)},${f1(y)} H${f1(x + w)} L${f1(x + w + dx)},${f1(y + dy)}"/>`;
    const bv = h >= 3 ? `M${f1(x + 0.8)},${f1(y + 1.2)} H${f1(x + w - 0.8)}` : '';
    const sb = h >= 8 && Math.abs(dx) >= 3 ? ` M${f1(x + w + 1.2)},${f1(y + 1.2 * dy / dx + 1.6)} V${f1(y + h + 1.2 * dy / dx - 0.8)}` : '';
    if (bv || sb) s += `<path class="qbv" d="${bv}${sb}"/>`;
    return s + (inner || '') + '</g>';
  }
  /* 球（第 2 版）：放射漸層＋左上高光點＋下方扁橢圓接觸陰影 */
  function ball2(cx, cy, r, m, tone, back) {
    const k = useV(m, tone, back);
    return `<ellipse class="qbs" cx="${f1(cx)}" cy="${f1(cy + r * 0.82)}" rx="${f1(r * 0.8)}" ry="${f1(r * 0.25)}"/>`
      + `<circle class="qball k-${k}" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" style="fill:url(#${V2.P}b-${k})"/>`
      + `<circle class="qbh" cx="${f1(cx - 0.35 * r)}" cy="${f1(cy - 0.35 * r)}" r="${f1(Math.max(0.5, 0.35 * r))}"/>`;
  }

  /* ---- 細節（規格 3.3／3.4）。全部畫在積木 (x,y,w,h) 與深度 dd 的範圍內；k＝這個積木的色組 */
  function det2(name, s, dd, k) {
    const { x, y, w, h } = s; const [dx, dy] = dd; let g = '';
    const top = (u, v) => onTop(x, y, w, dd, u, v);
    if (name === 'layers') {
      const n = Math.max(1, s.n), lh = h / n, uf = qv('underfill', 'f');
      for (let i = 0; i < n; i++) {
        const y0 = y + i * lh;
        g += `<rect class="${i % 2 ? 'ql2' : 'ql1'}" x="${f1(x)}" y="${f1(y0)}" width="${f1(w)}" height="${f1(lh)}"/>`;
        if (Math.abs(dx) >= 1) g += `<polygon class="${i % 2 ? 'qsl2' : 'qsl1'}" points="${pts([[x + w, y0], [x + w + dx, y0 + dy], [x + w + dx, y0 + lh + dy], [x + w, y0 + lh]])}"/>`;
        if (i) g += `<path class="qglue" style="stroke:${uf}" d="M${f1(x)},${f1(y0)} H${f1(x + w)}${Math.abs(dx) >= 1 ? ` L${f1(x + w + dx)},${f1(y0 + dy)}` : ''}"/>`;
      }
    } else if (name === 'vents') {
      for (let xx = x + 6; xx < x + w - 5; xx += 5.5) for (let yy = y + 4; yy < y + h - 4; yy += 5.5) g += `<rect class="qhole" x="${f1(xx)}" y="${f1(yy)}" width="2.8" height="2.8"/><path class="qlip" d="M${f1(xx)},${f1(yy + 3.3)} h2.8"/>`;
    } else if (name === 'ports') {
      const n = Math.max(1, s.n), pw = Math.max(5, (w - 16) / n - 4), au = qv('gold', 'f');
      for (let i = 0; i < n; i++) {
        const px = x + 8 + i * (w - 16) / n, py = y + h * 0.25, ph = h * 0.5;
        g += `<path class="qbv" d="M${f1(px)},${f1(py - 1.2)} h${f1(pw)}"/><rect class="qhole" x="${f1(px)}" y="${f1(py)}" width="${f1(pw)}" height="${f1(ph)}" rx="1"/>`;
        const nc = Math.max(3, Math.floor(pw / 2.2));
        for (let j = 0; j < nc; j++) g += `<rect style="fill:${au}" x="${f1(px + 1 + j * (pw - 2) / nc)}" y="${f1(py + ph * 0.55)}" width="${f1(Math.max(0.6, (pw - 2) / nc - 0.8))}" height="${f1(ph * 0.35)}"/>`;
      }
    } else if (name === 'fins') {
      const n = Math.max(2, s.n);
      for (let i = 0; i < n; i++) if (i % 2 === 0 && i + 1 < n) g += `<rect class="qgap" x="${f1(x + i * w / n)}" y="${f1(y)}" width="${f1(w / n)}" height="${f1(h)}"/>`;
      for (let i = 1; i < n; i++) { const xx = x + i * w / n; g += `<line class="qfin" x1="${f1(xx)}" y1="${f1(y)}" x2="${f1(xx)}" y2="${f1(y + h)}"/><line class="qfin" x1="${f1(xx)}" y1="${f1(y)}" x2="${f1(xx + dx)}" y2="${f1(y + dy)}"/><circle class="qdot" cx="${f1(xx)}" cy="${f1(y + 0.8)}" r=".8"/>`; }
    } else if (name === 'grid') {
      const nu = Math.max(3, s.nu || (s.mat === 'chip' ? 4 : 3)), nv = Math.max(3, s.nv || 3);
      const cell = (u0, v0, u1, v1) => pts([top(u0, v0), top(u1, v0), top(u1, v1), top(u0, v1)]);
      const a = 0.06, b = 0.94;
      const alt = `var(--q-${useV(s.mat, s.tone < 2 ? s.tone + 1 : s.tone - 1, s.back)}-t)`;
      [[1, 0], [nu - 2, nv - 1]].slice(0, nu * nv >= 9 ? 2 : 1).forEach(([i, j]) => { g += `<polygon style="fill:${alt}" points="${cell(a + i * (b - a) / nu, a + j * (b - a) / nv, a + (i + 1) * (b - a) / nu, a + (j + 1) * (b - a) / nv)}"/>`; });
      g += `<polygon class="qseal" points="${cell(a, a, b, b)}"/>`;
      for (let i = 1; i < nu; i++) { const p = top(a + i * (b - a) / nu, a), q = top(a + i * (b - a) / nu, b); g += `<line class="qgrid" x1="${f1(p[0])}" y1="${f1(p[1])}" x2="${f1(q[0])}" y2="${f1(q[1])}"/>`; }
      for (let j = 1; j < nv; j++) { const p = top(a, a + j * (b - a) / nv), q = top(b, a + j * (b - a) / nv); g += `<line class="qgrid" x1="${f1(p[0])}" y1="${f1(p[1])}" x2="${f1(q[0])}" y2="${f1(q[1])}"/>`; }
    } else if (name === 'lines') {
      const n = Math.max(h >= 14 ? 3 : 1, s.n), cu = qv('cu', 'f');
      const ys = []; for (let i = 1; i <= n; i++) ys.push(y + i * h / (n + 1));
      ys.forEach((yy, i) => { g += `<line class="qln${i % 2 ? ' b' : ''}" style="stroke:${cu}" x1="${f1(x + 1)}" y1="${f1(yy)}" x2="${f1(x + w - 1)}" y2="${f1(yy)}"/>`; });
      for (let i = 0; i + 1 < ys.length; i++) for (let j = 0; j < 3; j++) { const xx = x + w * (0.18 + 0.3 * j + 0.07 * (i % 2)); g += `<rect style="fill:${cu}" x="${f1(xx)}" y="${f1(ys[i])}" width="1.6" height="${f1(ys[i + 1] - ys[i])}"/>`; }
    } else if (name === 'vias') {
      const n = Math.max(1, s.n), cu = qv('cu', 'f'), cut = qv('cu', 't');
      for (let i = 0; i < n; i++) { const cx = x + (i + 0.5) * w / n; g += `<rect style="fill:${cu}" x="${f1(cx - 1.4)}" y="${f1(y)}" width="2.8" height="${f1(h)}"/><rect style="fill:${cut}" x="${f1(cx - 2.4)}" y="${f1(y)}" width="4.8" height="1.4"/><rect style="fill:${cut}" x="${f1(cx - 2.4)}" y="${f1(y + h - 1.4)}" width="4.8" height="1.4"/>`; }
    } else if (name === 'fan') {
      const r = Math.min(w, h) / 2 - 4, cx = x + w / 2, cy = y + h / 2, n = Math.max(7, s.n >= 7 && s.n <= 13 ? s.n : 7);
      g += `<circle class="qhole" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"/><circle class="qrim" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"/>`;
      for (let i = 0; i < n; i++) {
        const a = i * 2 * Math.PI / n, a2 = a + 0.55, r0 = r * 0.3, r1 = r * 0.92;
        const p0 = [cx + Math.cos(a) * r0, cy + Math.sin(a) * r0], p1 = [cx + Math.cos(a + 0.25) * r1, cy + Math.sin(a + 0.25) * r1], p2 = [cx + Math.cos(a2) * r1, cy + Math.sin(a2) * r1], p3 = [cx + Math.cos(a + 0.5) * r0, cy + Math.sin(a + 0.5) * r0];
        g += `<path class="qblade" d="M${f1(p0[0])},${f1(p0[1])} Q${f1(cx + Math.cos(a + 0.05) * r * 0.75)},${f1(cy + Math.sin(a + 0.05) * r * 0.75)} ${f1(p1[0])},${f1(p1[1])} L${f1(p2[0])},${f1(p2[1])} Q${f1(cx + Math.cos(a + 0.45) * r * 0.6)},${f1(cy + Math.sin(a + 0.45) * r * 0.6)} ${f1(p3[0])},${f1(p3[1])}Z"/>`
          + `<path class="qedge" d="M${f1(p0[0])},${f1(p0[1])} Q${f1(cx + Math.cos(a + 0.05) * r * 0.75)},${f1(cy + Math.sin(a + 0.05) * r * 0.75)} ${f1(p1[0])},${f1(p1[1])}"/>`;
      }
      g += `<circle class="qhub" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r * 0.3)}"/><path class="qcr" d="M${f1(cx - r * 0.24)},${f1(cy - r * 0.04)} A${f1(r * 0.25)},${f1(r * 0.25)} 0 0 1 ${f1(cx + r * 0.04)},${f1(cy - r * 0.24)}"/>`;
      [[x + 4, y + 4], [x + w - 4, y + 4], [x + 4, y + h - 4], [x + w - 4, y + h - 4]].forEach(([sx, sy]) => { g += `<circle class="qhole" cx="${f1(sx)}" cy="${f1(sy)}" r="1.6"/>`; });
    } else if (name === 'terminals') {
      const tw = Math.min(14, w / 5), th = Math.min(8, h / 3), cy = y + h / 2;
      g += box2(x + w * 0.2, y - th, tw, th, 'gold', [dd[0] * 0.25, dd[1] * 0.25], {}) + box2(x + w * 0.8 - tw, y - th, tw, th, 'steel', [dd[0] * 0.25, dd[1] * 0.25], {});
      g += `<path class="qsign" d="M${f1(x + w * 0.2)},${f1(cy)} h8 M${f1(x + w * 0.2 + 4)},${f1(cy - 4)} v8 M${f1(x + w * 0.8 - 8)},${f1(cy)} h8"/>`;
    } else if (name === 'bumps') {
      const nu = Math.max(6, s.nu || 8), nv = Math.max(3, s.nv || 3), bm = s.bmat, bk = useV(bm, 0, 0);
      const pu = 0.9 * w / nu, rx = Math.max(1.2, Math.min(4.5, pu * 0.32)), ry = rx * Math.min(1, Math.abs(dy / (dx || 1)));
      for (let j = nv - 1; j >= 0; j--) for (let i = 0; i < nu; i++) {
        const p = top(0.05 + (i + 0.5) * 0.9 / nu, 0.1 + (j + 0.5) * 0.8 / nv);
        g += `<ellipse class="qbump" cx="${f1(p[0])}" cy="${f1(p[1])}" rx="${f1(rx)}" ry="${f1(ry)}" style="fill:url(#${V2.P}b-${bk})"/><circle class="qbh" cx="${f1(p[0] - rx * 0.35)}" cy="${f1(p[1] - ry * 0.3)}" r="${f1(Math.max(0.45, rx * 0.3))}"/>`;
      }
    } else if (name === 'traces') {
      const n = Math.max(6, s.n >= 6 ? s.n : 8), cu = qv('cu', 'f'), dl = Math.hypot(dx, dy) || 1, du = 0.22 * dl / Math.max(1, w);
      for (let i = 0; i < n; i++) {
        const u0 = 0.06 + i * 0.8 / Math.max(1, n - 1), sg = i % 2 ? 1 : -1, u1 = Math.max(0.03, Math.min(0.97, u0 + sg * du));
        const a = top(u0, 0.1), b = top(u0, 0.38), c = top(u1, 0.6), e = top(u1, 0.9);
        g += `<path class="qtr" style="stroke:${cu}" d="M${f1(a[0])},${f1(a[1])} L${f1(b[0])},${f1(b[1])} L${f1(c[0])},${f1(c[1])} L${f1(e[0])},${f1(e[1])}"/>`
          + `<rect style="fill:${cu}" x="${f1(a[0] - 1.2)}" y="${f1(a[1] - 0.8)}" width="2.4" height="1.6"/><rect style="fill:${cu}" x="${f1(e[0] - 1.2)}" y="${f1(e[1] - 0.8)}" width="2.4" height="1.6"/>`;
      }
    } else if (name === 'label') {
      [[0.3, 0.7, 0.62], [0.34, 0.66, 0.46], [0.38, 0.58, 0.3]].forEach(([u0, u1, v]) => { const a = top(u0, v), b = top(u1, v); g += `<line class="qmark" x1="${f1(a[0])}" y1="${f1(a[1])}" x2="${f1(b[0])}" y2="${f1(b[1])}"/>`; });
      const pin = top(0.07, 0.8); g += `<circle class="qpin" cx="${f1(pin[0])}" cy="${f1(pin[1])}" r="1.5"/>`;
    } else if (name === 'pads') {
      const n = Math.max(4, s.n >= 4 ? s.n : 6), pm = s.bmat === 'solder' ? 'cu' : s.bmat, pw = Math.min(9, (w - 8) / n * 0.6), ph = Math.min(3.2, h * 0.3);
      for (let i = 0; i < n; i++) { const px = x + 4 + (i + 0.5) * (w - 8) / n - pw / 2; g += `<rect style="fill:${qv(pm, 'f')}" x="${f1(px)}" y="${f1(y + 2)}" width="${f1(pw)}" height="${f1(ph)}"/><path class="qlip2" style="stroke:${qv(pm, 'h')}" d="M${f1(px)},${f1(y + 2.3)} h${f1(pw)}"/>`; }
    } else if (name === 'seal') {
      const z = Math.min(7, h * 0.55), uf = qv('underfill', 'f');
      g += `<polygon class="qfill" style="fill:${uf}" points="${pts([[x, y + h - z], [x, y + h], [x - z * 0.9, y + h]])}"/><polygon class="qfill" style="fill:${uf}" points="${pts([[x + w, y + h - z], [x + w, y + h], [x + w + z * 0.9, y + h]])}"/>`;
    } else if (name === 'screws') {
      const r = Math.max(1.4, Math.min(3, h / 7, w / 12)), st = qv('steel', 't'), ins = r + 2.5;
      [[x + ins, y + ins], [x + w - ins, y + ins], [x + ins, y + h - ins], [x + w - ins, y + h - ins]].forEach(([cx, cy]) => {
        g += `<circle class="qscrew" style="fill:${st}" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"/><path class="qx" d="M${f1(cx - r * 0.6)},${f1(cy)} h${f1(r * 1.2)} M${f1(cx)},${f1(cy - r * 0.6)} v${f1(r * 1.2)}"/><circle class="qbh" cx="${f1(cx - r * 0.4)}" cy="${f1(cy - r * 0.4)}" r="${f1(r * 0.25)}"/>`;
      });
    } else if (name === 'pins') {
      const n = Math.max(8, s.n >= 8 ? s.n : Math.max(8, Math.floor((w - 8) / 5))), pitch = (w - 8) / n, pw = Math.min(2.6, pitch * 0.55), au = qv('gold', 'f');
      for (let i = 0; i < n; i++) { const px = x + 4 + i * pitch + (pitch - pw) / 2; g += `<rect style="fill:${au}" x="${f1(px)}" y="${f1(y + h * 0.5)}" width="${f1(pw)}" height="${f1(h * 0.42)}"/><path class="qlip2" style="stroke:${qv('gold', 'h')}" d="M${f1(px + 0.3)},${f1(y + h * 0.5)} v${f1(h * 0.42)}"/>`; }
    } else if (name === 'hatch' || name === 'mesh') {
      const cp = clipRect(x, y, w, h), st = name === 'hatch' ? 4 : 6;
      let d = '';
      for (let t = -h; t < w + h; t += st) { d += `M${f1(x + t)},${f1(y + h)} L${f1(x + t + h)},${f1(y)} `; if (name === 'mesh') d += `M${f1(x + t)},${f1(y)} L${f1(x + t + h)},${f1(y + h)} `; }
      g += `<path class="${name === 'hatch' ? 'qhatch' : 'qmesh'}" clip-path="url(#${cp})" d="${d.trim()}"/>`;
    } else if (name === 'wires') {
      const n = Math.max(4, s.n >= 4 ? s.n : 5), au = qv('gold', 'f');
      for (let i = 0; i < n; i++) { const sx = x + 3 + i * Math.min(6, (w * 0.4) / n), ex = x - 6 - i * 4, ey = y + h + 2; g += `<path class="qwire" style="stroke:${au}" d="M${f1(sx)},${f1(y + 0.6)} Q${f1((sx + ex) / 2 - 2)},${f1(y - 8 - i * 1.5)} ${f1(ex)},${f1(ey)}"/>`; }
    }
    return g;
  }

  /* ---- 2026-10-17 晚：三個新積木（只在 style:2）—— CEO 退件第二代 Roadster 第一版：「車身只是一條細折線、零件浮在車身外、輪子是兩顆球、馬達是直立圓柱」
     · wheel：側視車輪（深色厚輪胎＋胎紋、輪框、5 輻、輪轂＋螺帽、接地陰影）。x,y＝輪心，r＝半徑；mat＝輪框材質（輪胎固定 rubber）。
     · hcyl：橫躺圓柱（馬達、氣瓶）。x,y,w,h；右端面看得到（跟方塊一樣看得到右側），筒身由上往下受光漸層；detail：fins（散熱環）、layers（色帶）、screws（端面螺栓）、terminals（頂上接頭）。
     · shell：外殼剖面（車殼、機殼）。points＝近側輪廓（閉合，≤ 48 點）、d＝往深處擠出幾倍 depth（看得到頂面、遠側殼）、z＝整個殼往深處推、open＝哪幾條邊不畫頂面（開口）、
       op＝半透明度、cut＝開窗（窗內看得到殼裡的零件）、taper＝兩端收窄、layer＝1 只畫後半／2 只畫前半 —— 零件寫在 layer 1 與 layer 2 之間，就是「畫在殼內」。
     全部只吃白名單（mat）與夾過值的數字。 */
  const hcylRx = (s) => Math.max(2, Math.min(s.h * 0.24, s.w * 0.3));
  function shellPts(s, D) {
    const ox = D[0] * s.z, oy = D[1] * s.z, dx = D[0] * s.d, dy = D[1] * s.d;
    // taper：兩端（左右各 22% 長度內）往中間收窄 —— 俯看時車頭、車尾是圓的，不是一塊長方形；近側與遠側各收一半
    const xs = s.pts.map((p) => p[0]), x0 = Math.min(...xs), x1 = Math.max(...xs), zone = Math.max(1, (x1 - x0) * 0.22);
    const sh = (x) => { const e = Math.max(0, 1 - Math.min(x - x0, x1 - x) / zone); return s.taper * e * e / 2; };
    const F = s.pts.map((p) => { const t = sh(p[0]); return [p[0] + ox + dx * t, p[1] + oy + dy * t]; });
    const B = s.pts.map((p) => { const t = 1 - sh(p[0]); return [p[0] + ox + dx * t, p[1] + oy + dy * t]; });
    return { F, B, cut: s.cut.map((c) => c.map((p) => [p[0] + ox, p[1] + oy])), dd: [dx, dy] };
  }
  function wheel2(s) {
    const { x, y, r } = s, P = V2.P, rk = useV(s.mat, s.tone, s.back), tk = useV('rubber', 0, s.back), tv = (n) => `var(--q-${tk}-${n})`;
    const arc = (rr, a0, a1) => { const p0 = [x + rr * Math.cos(a0), y + rr * Math.sin(a0)], p1 = [x + rr * Math.cos(a1), y + rr * Math.sin(a1)]; return `M${f1(p0[0])},${f1(p0[1])} A${f1(rr)},${f1(rr)} 0 0 1 ${f1(p1[0])},${f1(p1[1])}`; };
    let g = `<ellipse class="qws" cx="${f1(x)}" cy="${f1(y + r * 0.98)}" rx="${f1(r * 1.06)}" ry="${f1(Math.max(2, r * 0.14))}"/>`;
    // 輪胎：深色厚環＋外圈胎紋（虛線環）＋胎壁高光
    g += `<circle class="qtire" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" style="fill:${tv('f')};stroke:${tv('e')}"/>`
      + `<circle class="qtread" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r - 1.6)}" style="stroke:${tv('s1')};stroke-dasharray:${f1(r * 0.09)} ${f1(r * 0.06)}"/>`
      + `<circle class="qwall" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.8)}" style="stroke:${tv('s')}"/>`
      + `<path class="qwhl" style="stroke:${tv('h')};stroke-width:${f1(Math.max(1, r * 0.05))}" d="${arc(r * 0.88, Math.PI * 1.08, Math.PI * 1.55)}"/>`;
    // 輪框：外唇＋內桶（暗）＋碟煞盤＋5 輻＋輪轂＋5 螺帽
    g += `<g class="qk k-${rk}${LITE.has(s.mat) ? ' lite' : ''}"><circle class="qrimo" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.68)}" style="fill:url(#${P}b-${rk})"/>`
      + `<circle class="qhole" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.6)}"/>`
      + `<circle class="qdisc" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.46)}"/><circle class="qring" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.3)}"/>`;
    for (let i = 0; i < 5; i++) {
      const a = -Math.PI / 2 + i * 2 * Math.PI / 5, c = Math.cos(a), sn = Math.sin(a), px = -sn, py = c, w1 = r * 0.085, w2 = r * 0.05, r1 = r * 0.12, r2 = r * 0.61;
      const q = [[x + c * r1 + px * w1, y + sn * r1 + py * w1], [x + c * r2 + px * w2, y + sn * r2 + py * w2], [x + c * r2 - px * w2, y + sn * r2 - py * w2], [x + c * r1 - px * w1, y + sn * r1 - py * w1]];
      g += `<polygon class="qspoke" points="${pts(q)}"/><path class="qsph" d="M${f1(q[0][0])},${f1(q[0][1])} L${f1(q[1][0])},${f1(q[1][1])}"/>`;
    }
    g += `<circle class="qlipr" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.64)}"/>`
      + `<path class="qrimh" d="${arc(r * 0.655, Math.PI * 1.05, Math.PI * 1.6)}"/>`
      + `<circle class="qhubw" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r * 0.15)}" style="fill:url(#${P}b-${rk})"/>`;
    for (let i = 0; i < 5; i++) { const a = -Math.PI / 2 + Math.PI / 5 + i * 2 * Math.PI / 5; g += `<circle class="qnut" cx="${f1(x + Math.cos(a) * r * 0.095)}" cy="${f1(y + Math.sin(a) * r * 0.095)}" r="${f1(Math.max(0.6, r * 0.022))}"/>`; }
    return g + `<circle class="qcap" cx="${f1(x)}" cy="${f1(y)}" r="${f1(Math.max(0.8, r * 0.045))}"/></g>`;
  }
  function hcyl2(s) {
    const { x, y, w, h } = s, P = V2.P, k = useV(s.mat, s.tone, s.back), rx = hcylRx(s), ry = h / 2, cy = y + h / 2;
    V2.vg.add(k);
    let g = `<g class="qk k-${k}${RIM.has(s.mat) ? ' rim' : ''}${LITE.has(s.mat) ? ' lite' : ''}">`
      + `<path class="qf" style="fill:url(#${P}v-${k})" d="M${f1(x + w)},${f1(y)} H${f1(x)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(x)},${f1(y + h)} H${f1(x + w)} Z"/>`;
    const n = Math.max(1, Math.min(24, s.n));
    if (s.details.includes('layers')) for (let i = 0; i < n; i++) { const a = x + w * (i + 0.5) / (n + 0.5), b2 = a + w * 0.4 / (n + 0.5); g += `<path class="qband" d="M${f1(a)},${f1(y + 0.6)} H${f1(b2)} A${f1(rx)},${f1(ry - 0.6)} 0 0 1 ${f1(b2)},${f1(y + h - 0.6)} H${f1(a)} A${f1(rx)},${f1(ry - 0.6)} 0 0 0 ${f1(a)},${f1(y + 0.6)} Z"/>`; }
    if (s.details.includes('fins')) for (let i = 1; i <= n; i++) { const xx = x + w * i / (n + 1); g += `<path class="qfinr" d="M${f1(xx)},${f1(y)} A${f1(rx)},${f1(ry)} 0 0 1 ${f1(xx)},${f1(y + h)}"/><path class="qfinh" d="M${f1(xx - 1.3)},${f1(y + 0.8)} A${f1(rx)},${f1(ry - 0.8)} 0 0 1 ${f1(xx - 1.3)},${f1(y + h - 0.8)}"/>`; }
    g += `<path class="qcylh" style="stroke-width:${f1(Math.max(0.8, h * 0.07))}" d="M${f1(x + 1)},${f1(y + h * 0.24)} H${f1(x + w - 1.5)}"/>`;
    // 右端面（看得到的那一端）：端蓋＋內圈＋軸心
    g += `<ellipse class="qt" cx="${f1(x + w)}" cy="${f1(cy)}" rx="${f1(rx)}" ry="${f1(ry)}"/>`
      + `<ellipse class="qring" cx="${f1(x + w)}" cy="${f1(cy)}" rx="${f1(rx * 0.62)}" ry="${f1(ry * 0.62)}"/>`
      + `<ellipse class="qhub" cx="${f1(x + w)}" cy="${f1(cy)}" rx="${f1(rx * 0.24)}" ry="${f1(ry * 0.24)}"/>`
      + `<path class="qcr" d="M${f1(x + w - rx * 0.55)},${f1(cy - ry * 0.55)} A${f1(rx * 0.8)},${f1(ry * 0.8)} 0 0 1 ${f1(x + w + rx * 0.2)},${f1(cy - ry * 0.78)}"/>`;
    if (s.details.includes('screws')) for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3; g += `<circle class="qscrew" style="fill:${qv('steel', 't')}" cx="${f1(x + w + Math.cos(a) * rx * 0.8)}" cy="${f1(cy + Math.sin(a) * ry * 0.8)}" r="${f1(Math.max(0.6, Math.min(rx, ry) * 0.12))}"/>`; }
    if (s.details.includes('terminals')) g += box2(x + w * 0.42, y - 6, Math.max(4, w * 0.14), 6, 'gold', [0, -2], {});
    return g + '</g>';
  }
  function shell2(s, D) {
    const { F, B, cut, dd } = shellPts(s, D), P = V2.P, k = useV(s.mat, s.tone, s.back), op = s.op;
    let A = 0; for (let i = 0; i < F.length; i++) { const a = F[i], b2 = F[(i + 1) % F.length]; A += a[0] * b2[1] - b2[0] * a[1]; }
    const sg = A >= 0 ? 1 : -1;
    const nrm = (a, b2) => { const ex = b2[0] - a[0], ey = b2[1] - a[1], L = Math.hypot(ex, ey) || 1; return [sg * ey / L, -sg * ex / L]; };   // 往外的法線
    let g = `<g class="qk qshell k-${k}">`;
    if (s.layer !== 2 && (dd[0] || dd[1])) {
      g += `<polygon class="qsb" points="${pts(B)}" style="fill:url(#${P}f-${k});fill-opacity:${f1(op * 0.45 * 100) / 100}"/>`;
      // 看得到的擠出面（頂面、斜面）：法線跟 depth 同向；朝上的用頂色、朝右的用側色
      for (let i = 0; i < F.length; i++) {
        const a = F[i], b2 = F[(i + 1) % F.length], n = nrm(a, b2);
        if (n[0] * dd[0] + n[1] * dd[1] <= 0.01 || s.open.includes(i)) continue;
        const c = n[1] < -0.8 ? 'mt' : n[0] > 0.45 ? 'ms' : 'mf';
        g += `<polygon class="qsf" style="fill:var(--${c});fill-opacity:${f1(Math.min(0.95, op + 0.25) * 100) / 100}" points="${pts([a, b2, B[(i + 1) % F.length], B[i]])}"/>`;
      }
      g += `<polygon class="qso2" points="${pts(B)}"/>`;
    }
    if (s.layer !== 1) {
      // 開窗：用 evenodd 的裁切路徑把窗挖掉（窗超出殼的部分本來就沒有殼可畫，不影響）
      const ring = (q) => 'M' + q.map((p) => f1(p[0]) + ',' + f1(p[1])).join(' L') + ' Z';
      const mid = V2.P + 'cp' + (++V2.seq);
      V2.clips.push(`<clipPath id="${mid}"><path clip-rule="evenodd" d="${ring(F)} ${cut.map(ring).join(' ')}"/></clipPath>`);
      g += `<polygon class="qsk"${cut.length ? ` clip-path="url(#${mid})"` : ''} points="${pts(F)}" style="fill:url(#${P}f-${k});fill-opacity:${op}"/>`;
      if (cut.length) { const cp = clipPoly(F); g += `<g clip-path="url(#${cp})">${cut.map((c) => `<polygon class="qcut" points="${pts(c)}"/><polygon class="qcut2" points="${pts(c)}"/>`).join('')}</g>`; }
      g += `<polygon class="qso" points="${pts(F)}"/>`;
      // 上緣高光：只描朝上的邊，往殼內縮 1.4
      let hl = '';
      for (let i = 0; i < F.length; i++) { const a = F[i], b2 = F[(i + 1) % F.length], n = nrm(a, b2); if (n[1] > -0.45) continue; hl += `M${f1(a[0] - n[0] * 1.4)},${f1(a[1] - n[1] * 1.4)} L${f1(b2[0] - n[0] * 1.4)},${f1(b2[1] - n[1] * 1.4)} `; }
      if (hl) g += `<path class="qshl" d="${hl.trim()}"/>`;
    }
    return g + '</g>';
  }

  /* custom 第 2 版的積木：舊欄位＋tone、back、detail 陣列、nu／nv、bmat、rows、ends、guide（拆開圖的虛線導引） */
  function customSpec2(b) {
    const vw = cnum(b && b.view && b.view[0], 100, 2000, 600), vh = cnum(b && b.view && b.view[1], 80, 2000, 400);
    const D = [cnum(b && b.depth && b.depth[0], -200, 200, 40), cnum(b && b.depth && b.depth[1], -200, 200, -24)];
    const dets = (v) => (Array.isArray(v) ? v : [v]).filter((x) => typeof x === 'string' && DETAILS2.includes(x)).filter((x, i, a) => a.indexOf(x) === i).slice(0, 5);
    const shapes = (Array.isArray(b && b.shapes) ? b.shapes : []).slice(0, 120).filter((s) => s && SHAPES2.includes(s.type) && (pid(s.part) || s.type === 'guide')).map((s) => ({
      part: pid(s.part), type: s.type, mat: MATS2.includes(s.mat) ? s.mat : 'steel', details: dets(s.detail),
      tone: Math.round(cnum(s.tone, -2, 2, 0)), back: cnum(s.back, 0, 1, 0) >= 0.5 ? 1 : 0, bmat: BMATS.includes(s.bmat) ? s.bmat : 'solder',
      x: cnum(s.x, -vw, 2 * vw, 0), y: cnum(s.y, -vh, 2 * vh, 0), w: cnum(s.w, 1, 2 * vw, 40), h: cnum(s.h, 1, 2 * vh, 20),
      d: cnum(s.d, 0, s.type === 'shell' ? 8 : 3, 1), n: Math.round(cnum(s.n, 1, 60, 6)), nu: Math.round(cnum(s.nu, 0, 40, 0)), nv: Math.round(cnum(s.nv, 0, 12, 0)),
      rows: Math.round(cnum(s.rows, 1, 3, 2)), ends: cnum(s.ends, 0, 1, 1) >= 0.5 ? 1 : 0,
      r: cnum(s.r, 0.5, 200, 6), x2: cnum(s.x2, -vw, 2 * vw, 0), y2: cnum(s.y2, -vh, 2 * vh, 0),
      pts: (Array.isArray(s.points) ? s.points : []).slice(0, s.type === 'shell' ? 48 : 20).filter((p) => Array.isArray(p) && p.length === 2).map((p) => [cnum(p[0], -vw, 2 * vw, 0), cnum(p[1], -vh, 2 * vh, 0)]),
      // shell 專用：cut＝開窗（最多 3 個多邊形、每個 ≤ 16 點）、op＝殼的不透明度、z＝整個殼往深處推幾倍 depth、layer＝0 全畫／1 只畫後半（遠側殼＋頂面）／2 只畫前半（近側殼＋開窗）
      cut: s.type === 'shell' && Array.isArray(s.cut) ? s.cut.slice(0, 3).filter(Array.isArray).map((c) => c.slice(0, 16).filter((p) => Array.isArray(p) && p.length === 2).map((p) => [cnum(p[0], -vw, 2 * vw, 0), cnum(p[1], -vh, 2 * vh, 0)])).filter((c) => c.length >= 3) : [],
      op: cnum(s.op, 0.15, 0.9, 0.45), z: cnum(s.z, 0, 3, 0), taper: cnum(s.taper, 0, 0.8, 0), layer: Math.round(cnum(s.layer, 0, 2, 0)),
      open: s.type === 'shell' && Array.isArray(s.open) ? s.open.slice(0, 48).map((v) => Math.round(cnum(v, -1, 47, -1))).filter((v) => v >= 0) : [],   // 不畫頂面的邊（第 i 點→第 i+1 點），例如座艙開口
    }));
    return { vw, vh, D, shapes };
  }
  /* 一個積木的外框（含深度延伸、極柱、球的陰影），給構圖裁切與驗收用 */
  function bbox2(s, D) {
    const dx = D[0] * s.d, dy = D[1] * s.d;
    if (s.type === 'box') { const th = s.details.includes('terminals') ? Math.min(8, s.h / 3) + Math.abs(dy) * 0.25 : 0; return [s.x + Math.min(0, dx), s.y + Math.min(0, dy) - th, s.x + s.w + Math.max(0, dx), s.y + s.h + Math.max(0, dy)]; }
    if (s.type === 'cyl') { const ry = Math.max(2, Math.abs(D[1]) * 0.35); return [s.x, s.y - ry - (s.details.includes('terminals') ? 7 : 0), s.x + s.w, s.y + s.h + ry]; }
    if (s.type === 'balls') { const x2 = s.x2 > s.x ? s.x2 : s.x + s.w, ox = s.rows > 1 ? 0.5 * dx : 0, oy = s.rows > 1 ? 0.5 * dy : 0; return [s.x - s.r + Math.min(0, ox), s.y - s.r + Math.min(0, oy), x2 + s.r + Math.max(0, ox) + (s.rows > 1 ? (x2 - s.x) / Math.max(1, s.n - 1) / 2 : 0), s.y + s.r * 1.1 + Math.max(0, oy)]; }
    if (s.type === 'wheel') return [s.x - s.r * 1.06, s.y - s.r, s.x + s.r * 1.06, s.y + s.r + Math.max(2, s.r * 0.14)];
    if (s.type === 'hcyl') { const rx = hcylRx(s); return [s.x - rx, s.y - (s.details.includes('terminals') ? 7 : 0), s.x + s.w + rx, s.y + s.h]; }
    if (s.type === 'shell') { if (s.pts.length < 3) return null; const P = shellPts(s, D); const all = P.F.concat(P.B); const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]); return [Math.min(...xs) - 1, Math.min(...ys) - 1, Math.max(...xs) + 1, Math.max(...ys) + 1]; }
    if (s.pts.length) { const xs = s.pts.map((p) => p[0]), ys = s.pts.map((p) => p[1]), m = s.type === 'pipe' ? s.r * 1.2 : 3; return [Math.min(...xs) - m, Math.min(...ys) - m, Math.max(...xs) + m, Math.max(...ys) + m]; }
    return null;
  }
  function custom2(P, b) {
    const { D, shapes } = customSpec2(b);
    const o = [], anchors = {};
    const auto = (id, x, y) => { if (id && !anchors[id]) anchors[id] = { x, y }; };
    // 接觸：後畫的方塊 A 底面貼著先畫的方塊 B 的頂面（相距 ≤ 2）→ 陰影畫在 B 的頂面上（裁在 B 的頂面範圍內）
    const boxes = shapes.map((s, i) => ({ s, i })).filter((q) => q.s.type === 'box');
    const shadowOn = {};
    boxes.forEach((A) => boxes.forEach((B) => {
      if (B.i >= A.i) return;
      const a = A.s, c = B.s;
      if (Math.abs(a.y + a.h - c.y) > 2 || Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x) <= 0) return;
      (shadowOn[B.i] = shadowOn[B.i] || []).push(a);
    }));
    shapes.forEach((s, i) => {
      let g = '';
      const dd = [D[0] * s.d, D[1] * s.d];
      if (s.type === 'box') {
        let under = '';
        if (shadowOn[i]) {
          const cp = clipPoly([[s.x, s.y], [s.x + s.w, s.y], [s.x + s.w + dd[0], s.y + dd[1]], [s.x + dd[0], s.y + dd[1]]]);
          shadowOn[i].forEach((a) => {
            const yb = a.y + a.h, adx = D[0] * a.d, ady = D[1] * a.d, L = Math.hypot(adx, ady) || 1, ox = -adx / L * 3.5, oy = -ady / L * 3.5;
            under += `<g clip-path="url(#${cp})"><polygon class="qcs" points="${pts([[a.x + a.w, yb], [a.x + a.w + adx, yb + ady], [a.x + a.w + adx + 3.5, yb + ady], [a.x + a.w + 3.5, yb]])}" style="fill:url(#${P}csx)"/>`
              + `<polygon class="qcs" points="${pts([[a.x, yb], [a.x + a.w, yb], [a.x + a.w + ox, yb + oy], [a.x + ox, yb + oy]])}" style="fill:url(#${P}csy)"/></g>`;
          });
        }
        g += box2(s.x, s.y, s.w, s.h, s.mat, dd, { tone: s.tone, back: s.back, under }, s.details.map((nm) => det2(nm, s, dd)).join(''));
        auto(s.part, s.x + s.w * 0.85, s.y + s.h / 2);
      } else if (s.type === 'cyl') {
        const k = useV(s.mat, s.tone, s.back), rx = s.w / 2, ry = Math.max(2, Math.abs(D[1]) * 0.35), cx = s.x + rx;
        g += `<g class="qk k-${k}${RIM.has(s.mat) ? ' rim' : ''}${LITE.has(s.mat) ? ' lite' : ''}"><path class="qf" style="fill:url(#${P}c-${k})" d="M${f1(s.x)},${f1(s.y)} V${f1(s.y + s.h)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(s.x + s.w)},${f1(s.y + s.h)} V${f1(s.y)} Z"/>`
          + `<ellipse class="qt" cx="${f1(cx)}" cy="${f1(s.y)}" rx="${f1(rx)}" ry="${f1(ry)}"/>`
          + `<path class="qcr" d="M${f1(cx - rx * 0.8)},${f1(s.y - ry * 0.05)} A${f1(rx * 0.85)},${f1(ry * 0.8)} 0 0 1 ${f1(cx - rx * 0.05)},${f1(s.y - ry * 0.78)}"/>`;
        if (s.details.includes('layers')) for (let j = 1; j < s.n; j++) { const yy = s.y + j * s.h / s.n; g += `<path class="qring" d="M${f1(s.x)},${f1(yy)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(s.x + s.w)},${f1(yy)}"/>`; }
        if (s.details.includes('terminals')) g += box2(cx - rx * 0.3, s.y - ry - 6, rx * 0.6, 6, 'gold', [0, -ry * 0.6], {});
        g += `<path class="qbtm" d="M${f1(s.x)},${f1(s.y + s.h)} A${f1(rx)},${f1(ry)} 0 0 0 ${f1(s.x + s.w)},${f1(s.y + s.h)}"/></g>`;
        auto(s.part, s.x + s.w * 0.9, s.y + s.h / 2);
      } else if (s.type === 'balls') {
        // 預設兩排（後排沿深度偏移半個深度、亮度 −0.06、半徑 ×0.9、錯開半格）—— 看得出是一整片陣列
        const x2 = s.x2 > s.x ? s.x2 : s.x + s.w, m = s.mat, pitch = s.n > 1 ? (x2 - s.x) / (s.n - 1) : 0;
        for (let row = s.rows - 1; row >= 0; row--) {
          const ox = row * 0.5 * dd[0] / Math.max(1, s.rows - 1) + (row % 2 ? pitch / 2 : 0), oy = row * 0.5 * dd[1] / Math.max(1, s.rows - 1);
          for (let j = 0; j < s.n - (row % 2 && s.n > 1 ? 1 : 0); j++) { const cx = s.n > 1 ? s.x + j * pitch : s.x; g += ball2(cx + ox, s.y + oy, row ? s.r * 0.9 : s.r, m, s.tone, row ? 2 : s.back); }
        }
        auto(s.part, x2, s.y);
      } else if (s.type === 'pipe' && s.pts.length >= 2) {
        const k = useV(s.mat, s.tone, s.back), d = 'M' + s.pts.map((p) => f1(p[0]) + ',' + f1(p[1])).join(' L');
        const a = s.pts[0], c = s.pts[1], L = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
        let nx = -(c[1] - a[1]) / L, ny = (c[0] - a[0]) / L; if (ny > 0 || (ny === 0 && nx > 0)) { nx = -nx; ny = -ny; }   // 往上（或往左）的法線：內側高光偏這一邊
        const hd = 'M' + s.pts.map((p) => f1(p[0] + nx * 0.25 * s.r) + ',' + f1(p[1] + ny * 0.25 * s.r)).join(' L');
        g += `<g class="qk k-${k}"><path class="qpo" style="stroke-width:${f1(s.r + 1)}" d="${d}"/><path class="qpm" style="stroke-width:${f1(s.r)}" d="${d}"/><path class="qph" style="stroke-width:${f1(Math.max(0.4, 0.35 * s.r))}" d="${hd}"/>`;
        if (s.ends) { const em = s.mat === 'cu' || s.mat === 'gold' ? s.mat : 'steel'; [s.pts[0], s.pts[s.pts.length - 1]].forEach((p) => { g += `<rect class="qend" style="fill:${qv(em, 't')};stroke:${qv(em, 'e')}" x="${f1(p[0] - s.r * 1.1)}" y="${f1(p[1] - s.r * 0.6)}" width="${f1(s.r * 2.2)}" height="${f1(s.r * 1.2)}" rx=".6"/>`; }); }
        g += '</g>';
        const t = Math.min(1, 12 / L); auto(s.part, a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t);
      } else if (s.type === 'wheel') {
        g += wheel2(s); auto(s.part, s.x + s.r, s.y);
      } else if (s.type === 'hcyl') {
        g += hcyl2(s); auto(s.part, s.x + s.w + hcylRx(s) * 0.5, s.y + s.h / 2);
      } else if (s.type === 'shell' && s.pts.length >= 3) {
        g += shell2(s, D); const F = shellPts(s, D).F, e = F.reduce((m, p) => (p[0] > m[0] ? p : m), F[0]); auto(s.part, e[0], e[1]);
      } else if (s.type === 'guide' && s.pts.length >= 2) {
        const p = s.pts, e = p[p.length - 1], q = p[p.length - 2], L = Math.hypot(e[0] - q[0], e[1] - q[1]) || 1, ux = (e[0] - q[0]) / L, uy = (e[1] - q[1]) / L;
        o.push(`<g class="qguide"><path d="M${p.map((z) => f1(z[0]) + ',' + f1(z[1])).join(' L')}"/><polygon points="${pts([e, [e[0] - ux * 5 - uy * 2.6, e[1] - uy * 5 + ux * 2.6], [e[0] - ux * 5 + uy * 2.6, e[1] - uy * 5 - ux * 2.6]])}"/></g>`);
        return;
      }
      if (g && s.part) o.push(`<g data-part="${s.part}">${g}</g>`);
    });
    (Array.isArray(b && b.parts) ? b.parts : []).forEach((p) => {
      const id = pid(p && p.id); if (!id || !anchors[id]) return;
      if (Array.isArray(p.anchor) && p.anchor.length === 2) anchors[id] = { x: cnum(p.anchor[0], -4000, 4000, anchors[id].x), y: cnum(p.anchor[1], -4000, 4000, anchors[id].y) };
      if (p.out != null) anchors[id].out = cnum(p.out, -4000, 4000, anchors[id].y);
    });
    // 構圖：view 依內容裁切（規格 3.5「不准留大片空白」），四邊留 6
    const bb = shapes.map((s) => bbox2(s, D)).filter(Boolean);
    const vb = bb.length ? [Math.min(...bb.map((r) => r[0])) - 6, Math.min(...bb.map((r) => r[1])) - 6] : [0, 0];
    if (bb.length) { vb.push(Math.max(...bb.map((r) => r[2])) + 6 - vb[0], Math.max(...bb.map((r) => r[3])) + 6 - vb[1]); } else vb.push(600, 400);
    return { vb: vb.map(f1), body: defs2(P) + o.join(''), anchors };
  }
  const CSS2 = `
.ilsvg.ilv2{--il-shadow:rgba(0,0,0,.35);--il2-bsh:rgba(0,0,0,.3);--il2-cave:#0a101b;--il2-hi:#ffffff;--il2-guide:rgba(200,214,235,.5)}
:root[data-theme="light"] .ilsvg.ilv2{--il-shadow:rgba(20,30,50,.18);--il2-bsh:rgba(20,30,50,.22);--il2-cave:#343c4c;--il2-hi:#ffffff;--il2-guide:rgba(40,52,74,.5)}
.ilv2 .qt{fill:var(--mt)}
.ilv2 .qt,.ilv2 .qr,.ilv2 .qf{stroke:var(--me);stroke-width:1;stroke-linejoin:round}
:root[data-theme="light"] .ilv2 .lite>.qt,:root[data-theme="light"] .ilv2 .lite>.qr,:root[data-theme="light"] .ilv2 .lite>.qf{stroke-width:1.2}
.ilv2 .qb{stroke:none}
.ilv2 .qhl{fill:none;stroke:var(--mh);stroke-width:1;opacity:.85;stroke-linecap:round;stroke-linejoin:round}
.ilv2 .rim>.qhl{stroke-width:1.2;opacity:1}
:root[data-theme="light"] .ilv2 .rim>.qhl{stroke-width:1;opacity:.85}
.ilv2 .qbv{fill:none;stroke:var(--mh);stroke-width:.8;opacity:.5}
.ilv2 .qcs{stroke:none}
.ilv2 .qbs{fill:var(--il2-bsh)}
.ilv2 .qball{stroke:var(--me);stroke-width:.5}.ilv2 .qbh{fill:var(--il2-hi);opacity:.7}
.ilv2 .qbump{stroke:var(--me);stroke-width:.35}
.ilv2 .ql1{fill:var(--ml1)}.ilv2 .ql2{fill:var(--ml2)}.ilv2 .qsl1{fill:var(--ms)}.ilv2 .qsl2{fill:var(--ms1)}
.ilv2 .qglue{fill:none;stroke-width:.6}
.ilv2 .qhole{fill:var(--il2-cave)}.ilv2 .qlip{fill:none;stroke:var(--mh);stroke-width:.6;opacity:.4}
.ilv2 .qlip2{fill:none;stroke-width:.6;opacity:.9}
.ilv2 .qgap{fill:var(--me);opacity:.08}.ilv2 .qfin{stroke:var(--me);stroke-width:1.1}.ilv2 .qdot{fill:var(--mh)}
.ilv2 .qgrid{stroke:var(--mh);stroke-width:.7;opacity:.75}.ilv2 .qseal{fill:none;stroke:var(--mh);stroke-width:.9;opacity:.9}
.ilv2 .qln{stroke-width:1.1;stroke-dasharray:22 6;opacity:.9}.ilv2 .qln.b{stroke-dasharray:10 4}
.ilv2 .qrim{fill:none;stroke:var(--mh);stroke-width:1}.ilv2 .qblade{fill:var(--mt);stroke:var(--me);stroke-width:.5;opacity:.95}.ilv2 .qedge{fill:none;stroke:var(--mh);stroke-width:.9}
.ilv2 .qhub{fill:var(--mf);stroke:var(--me);stroke-width:.8}.ilv2 .qcr{fill:none;stroke:var(--mh);stroke-width:1.4;opacity:.5;stroke-linecap:round}
.ilv2 .qsign{fill:none;stroke:var(--il2-hi);stroke-width:1.4;stroke-linecap:round}
.ilv2 .qtr{fill:none;stroke-width:.8;opacity:.8;stroke-linejoin:round}
.ilv2 .qmark{stroke:var(--me);stroke-width:1.5;opacity:.35;stroke-linecap:round}.ilv2 .qpin{fill:var(--me);opacity:.55}
.ilv2 .qfill{opacity:.65}
.ilv2 .qscrew{stroke:var(--me);stroke-width:.5}.ilv2 .qx{stroke:var(--me);stroke-width:.6}
.ilv2 .qhatch,.ilv2 .qmesh{fill:none;stroke:var(--me);stroke-width:.6;opacity:.35}
.ilv2 .qwire{fill:none;stroke-width:.6}
.ilv2 .qring{fill:none;stroke:var(--me);stroke-width:.8;opacity:.7}.ilv2 .qbtm{fill:none;stroke:var(--me);stroke-width:1}
.ilv2 .qpo{fill:none;stroke:var(--me);stroke-linecap:round;stroke-linejoin:round}.ilv2 .qpm{fill:none;stroke:var(--mf);stroke-linecap:round;stroke-linejoin:round}
.ilv2 .qph{fill:none;stroke:var(--mh);opacity:.6;stroke-linecap:round;stroke-linejoin:round}.ilv2 .qend{stroke-width:.5}
.ilv2 .qws{fill:var(--il2-bsh)}.ilv2 .qtire{stroke-width:1}.ilv2 .qtread{fill:none;stroke-width:2.6;opacity:.9}.ilv2 .qwall{fill:none;stroke-width:.8;opacity:.8}.ilv2 .qwhl{fill:none;opacity:.55;stroke-linecap:round}
.ilv2 .qrimo{stroke:var(--me);stroke-width:1}.ilv2 .qdisc{fill:var(--ms1);stroke:var(--me);stroke-width:.6}
.ilv2 .qspoke{fill:var(--mf);stroke:var(--me);stroke-width:.6;stroke-linejoin:round}.ilv2 .qsph{fill:none;stroke:var(--mh);stroke-width:.7;opacity:.8}
.ilv2 .qlipr{fill:none;stroke:var(--mh);stroke-width:.8;opacity:.6}.ilv2 .qrimh{fill:none;stroke:var(--mh);stroke-width:1.3;opacity:.85;stroke-linecap:round}
.ilv2 .qhubw{stroke:var(--me);stroke-width:.7}.ilv2 .qnut{fill:var(--ms);stroke:var(--me);stroke-width:.3}.ilv2 .qcap{fill:var(--ms)}
.ilv2 .qband{fill:var(--ms);opacity:.55}.ilv2 .qfinr{fill:none;stroke:var(--me);stroke-width:1.1}.ilv2 .qfinh{fill:none;stroke:var(--mh);stroke-width:.6;opacity:.55}
.ilv2 .qcylh{fill:none;stroke:var(--mh);opacity:.5;stroke-linecap:round}
.ilv2 .qshell .qsb{stroke:none}.ilv2 .qsf{stroke:var(--me);stroke-width:.6;stroke-opacity:.5;stroke-linejoin:round}
.ilv2 .qso,.ilv2 .qso2{fill:none;stroke:var(--me);stroke-width:1.3;stroke-linejoin:round}.ilv2 .qso2{stroke-width:.9;opacity:.45}
.ilv2 .qcut{fill:none;stroke:var(--ms);stroke-width:3.2;stroke-linejoin:round}.ilv2 .qcut2{fill:none;stroke:var(--mh);stroke-width:.8;opacity:.7;stroke-linejoin:round}
.ilv2 .qshl{fill:none;stroke:var(--mh);stroke-width:1.4;opacity:.85;stroke-linecap:round}
.ilv2 .qguide path{fill:none;stroke:var(--il2-guide);stroke-width:1;stroke-dasharray:4 3}.ilv2 .qguide polygon{fill:var(--il2-guide)}
/* 內建 kind（cowos／rack）的第 2 版：舊的細節 class 換成新色票 */
.ilsvg.ilv2 .base{fill:var(--q-logic_p0-f)}.ilsvg.ilv2 .dram1{fill:var(--q-mem_p0-l1)}.ilsvg.ilv2 .dram2{fill:var(--q-mem_p0-l2)}
.ilsvg.ilv2 .rdl{fill:var(--q-si_p0-t);opacity:.7}.ilsvg.ilv2 .cu,.ilsvg.ilv2 .pad{fill:var(--q-cu_p0-f)}.ilsvg.ilv2 .core{fill:var(--q-core_p0-f)}
.ilsvg.ilv2 .cuIn{stroke:var(--q-cu_p0-f);stroke-width:1.1}.ilsvg.ilv2 .hs{stroke:var(--q-cu_p0-h);stroke-width:1.4}
.ilsvg.ilv2 .act{fill:var(--q-chip_p0-s)}.ilsvg.ilv2 .actc{fill:var(--q-solder_p0-f);opacity:.8}
.ilsvg.ilv2 .grid,.ilsvg.ilv2 .gridb{stroke:var(--q-chip_p0-h);opacity:.75}
.ilsvg.ilv2 .cave,.ilsvg.ilv2 .hole,.ilsvg.ilv2 .phole,.ilsvg.ilv2 .slot{fill:var(--il2-cave)}
.ilsvg.ilv2 .vent{stroke:var(--q-steel_p0-e)}
.ilsvg.ilv2 .bezel{fill:var(--q-dark_p0-f);stroke:var(--q-dark_p0-h);stroke-width:.8}.ilsvg.ilv2 .bezel2{fill:var(--q-plastic_p0-f);stroke:var(--q-plastic_p0-h);stroke-width:.8}
.ilsvg.ilv2 .port{fill:var(--il2-cave);stroke:var(--q-gold_p0-f);stroke-width:.6}.ilsvg.ilv2 .hdl,.ilsvg.ilv2 .qd,.ilsvg.ilv2 .rail{fill:var(--q-steel_p0-t)}.ilsvg.ilv2 .rail{stroke:var(--q-steel_p0-t)}
.ilsvg.ilv2 .psum{fill:var(--q-steel_p0-s)}.ilsvg.ilv2 .fan{fill:var(--il2-cave);stroke:var(--q-steel_p0-t)}.ilsvg.ilv2 .fanb{stroke:var(--q-steel_p0-t)}
.ilsvg.ilv2 .led{fill:var(--q-pcb_p0-t)}
.ilsvg.ilv2 .bat{fill:var(--q-battery_p0-f);stroke:var(--q-battery_p0-e)}.ilsvg.ilv2 .term{fill:var(--q-gold_p0-f)}.ilsvg.ilv2 .sign{stroke:var(--il2-hi)}.ilsvg.ilv2 .charge{fill:var(--q-battery_p0-t);opacity:.5}
.ilsvg.ilv2 .postf{fill:var(--q-steel_p0-f);stroke:var(--q-steel_p0-e)}
.ilsvg.ilv2 .pipe{stroke:var(--q-steel_p0-e)}.ilsvg.ilv2 .pipe.cold{fill:var(--q-cold_p0-f)}.ilsvg.ilv2 .pipe.hot{fill:var(--q-hot_p0-f)}
.ilsvg.ilv2 .hose.cold,.ilsvg.ilv2 .tube.cold{stroke:var(--q-cold_p0-f)}.ilsvg.ilv2 .hose.hot,.ilsvg.ilv2 .tube.hot{stroke:var(--q-hot_p0-f)}
.ilsvg.ilv2 .plate{fill:var(--q-plate_p0-f);stroke:var(--q-plate_p0-e)}.ilsvg.ilv2 .platec{fill:var(--q-plate_p0-t);opacity:.8}.ilsvg.ilv2 .plate2{fill:var(--q-cap_p0-f);stroke:var(--q-cap_p0-e)}
.ilsvg.ilv2 .m-steel.r{fill:var(--q-steel_p0-s);stroke:var(--q-steel_p0-e)}.ilsvg.ilv2 .m-steel.t{fill:var(--q-steel_p0-t);stroke:var(--q-steel_p0-e)}
`;

  const KINDS = { cowos: { draw: cowos, parts: COWOS_PARTS }, rack: { draw: rack, parts: RACK_PARTS }, custom: { draw: (P, b) => (V2.on ? custom2(P, b) : custom(P, b)), parts: null } };
  /* 畫一張：style:2 才打開第 2 版（V2.on 只在這次同步呼叫期間為真）；沒帶 style 的舊圖照原本畫 */
  const isV2 = (b) => !!b && Number(b.style) === 2;
  function run(K, P, b) {
    if (!isV2(b)) return K.draw(P, b);
    V2.on = true; V2.P = P; V2.used = new Set(); V2.clips = []; V2.vg = new Set(); V2.seq = 0;
    try {
      if (K.parts) BUILTIN2.forEach((m) => useV(m, 0, 0));
      const r = K.draw(P, b); r.v2 = true; return r;
    } finally { V2.on = false; V2.used = null; V2.clips = null; V2.vg = null; }
  }

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
      const A = run(K, 'ilx_', b).anchors, yy = (id) => { const a = A[id]; return a ? (a.out != null ? a.out : a.y) : 1e9; };
      let pick;
      if (!K.parts) {
        const seen = new Set();
        pick = g.filter((x) => A[x.id] && !seen.has(x.id) && seen.add(x.id)).map((x) => ({ id: x.id, label: String(x.label || x.id), sub: x.sub != null ? String(x.sub) : '' }));
        return pick.sort((a, c) => yy(a.id) - yy(c.id));
      }
      pick = g.length ? K.parts.filter((p) => g.some((x) => x.id === p.id)) : K.parts;
      return pick.slice().sort((a, c) => yy(a.id) - yy(c.id)).map((p) => { const x = g.find((y) => y.id === p.id) || {}; return { id: p.id, label: x.label || p.label, sub: x.sub != null ? x.sub : p.sub }; });
    },
    anchors(k, b) { const K = KINDS[k]; return K ? run(K, 'ilx_', b).anchors : null; },
    draw(k, b) {
      css();
      const K = KINDS[k]; if (!K) return null;
      return run(K, 'il' + (++seq) + '_', b);
    },
    /* 給 scripts/illus_audit.py 與驗收段落用（唯讀）：第 2 版正規化後的積木（白名單＋夾值之後、真正拿去畫的那份）與某材質某主題的色票 */
    spec2: (b) => { const sp = customSpec2(b); sp.shapes.forEach((s) => { s.bb = bbox2(s, sp.D); }); return sp; },
    colors2: (m, tone, back, th) => (PAL[m] ? vcol(m, Math.round(cnum(tone, -2, 2, 0)), back ? 1 : 0, th === 'light' ? 'l' : 'd') : null),
    mats2: () => MATS2.slice(), details2: () => DETAILS2.slice(),
  };
})();
