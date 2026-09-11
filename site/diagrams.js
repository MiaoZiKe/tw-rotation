/* 產品剖析圖（原創示意 SVG，含動畫）。每個零件帶 data-seg = supply_chain.yaml 的環節 id；
   零件顏色由 industry.js 依環節色（App.L.scolor）注入 --c，所以剖析圖、環節色標、關聯圖、族群卡片顏色一致。
   版面規則：零件畫在中間、說明文字排在右側欄位用引線接過去，文字絕不疊在零件上。 */
(function () {
  'use strict';
  const STYLE = `<style>
    .dg{font-family:"Noto Sans TC",sans-serif}
    .dg text{fill:#a9b6d6;font-size:12px}
    .dg .ttl{font-size:15px;font-weight:700;fill:#e8eeff;letter-spacing:.02em}
    .dg .cap{font-size:11.5px;fill:#6f7ea3}
    .dg .lbl{font-size:12.5px;fill:#e8eeff;font-weight:600}
    .dg .sub{font-size:10.5px;fill:#8ea0c4}
    .dg .tag{font-family:"JetBrains Mono",monospace;font-size:10px;fill:var(--c,#8ea0c4);letter-spacing:.04em}
    .dg .mono{font-family:"JetBrains Mono",monospace}
    .dg [data-seg]{cursor:pointer;transition:opacity .2s}
    .dg [data-seg] .part{transition:stroke .15s,filter .15s;stroke:color-mix(in srgb,var(--c,#3ee0ff) 55%,#2a3860)}
    .dg [data-seg]:hover .part,.dg [data-seg].sel .part{stroke:var(--c,#3ee0ff);stroke-width:2.2;filter:drop-shadow(0 0 7px var(--c,#3ee0ff))}
    .dg [data-seg].sel .lbl,.dg [data-seg]:hover .lbl{fill:var(--c,#3ee0ff)}
    .dg [data-seg] .dot{fill:var(--c,#8ea0c4)}
    .dg [data-seg] .leader{stroke:color-mix(in srgb,var(--c,#8ea0c4) 55%,#1e2a48);stroke-width:1;fill:none}
    .dg [data-seg].sel .leader,.dg [data-seg]:hover .leader{stroke:var(--c);stroke-width:1.6}
    .dg [data-seg].dim{opacity:.3}
    .dg .lrow{cursor:pointer} .dg .lrow rect.bg{fill:transparent} .dg .lrow:hover rect.bg,.dg .lrow.sel rect.bg{fill:color-mix(in srgb,var(--c,#3ee0ff) 12%,transparent)}
    .dg [data-chain]{cursor:pointer} .dg [data-chain]:hover rect{stroke:#3ee0ff}
    .dg .flow{stroke-dasharray:7 7;animation:dgdash 1.4s linear infinite}
    .dg .flow.slow{animation-duration:2.4s} .dg .flow.fast{animation-duration:.9s}
    .dg .flow.rev{animation-direction:reverse}
    @keyframes dgdash{to{stroke-dashoffset:-28}}
    .dg .blink{animation:dgblink 1.6s ease-in-out infinite}
    .dg .blink.b2{animation-delay:.5s}.dg .blink.b3{animation-delay:1s}
    @keyframes dgblink{0%,100%{opacity:.2}50%{opacity:1}}
    .dg .pulse{animation:dgpulse 2.6s ease-in-out infinite}
    @keyframes dgpulse{0%,100%{opacity:.35}50%{opacity:1}}
    .dg .spin{transform-box:fill-box;transform-origin:center;animation:dgspin 2.6s linear infinite}
    @keyframes dgspin{to{transform:rotate(360deg)}}
    .dg .scan{animation:dgscan 3.2s linear infinite}
    @keyframes dgscan{0%{transform:translateY(-60px)}100%{transform:translateY(60px)}}
    .dg .heat{animation:dgheat 2.8s ease-in-out infinite}
    @keyframes dgheat{0%,100%{opacity:.15;transform:translateY(0)}50%{opacity:.6;transform:translateY(-5px)}}
    .dg .drop{animation:dgdrop 2.2s linear infinite}
    .dg .drop.d2{animation-delay:.7s}.dg .drop.d3{animation-delay:1.4s}
    @keyframes dgdrop{0%{opacity:0;transform:translateY(0)}15%{opacity:1}85%{opacity:1}100%{opacity:0;transform:translateY(46px)}}
    /* ---- 等角 3D：每個零件永遠帶自己的環節色（--c），選到就整塊變亮，顏色與族群一致 ---- */
    .dg .p3{--m1:66%;--m2:42%;--m3:26%;--ce:#4a6ea8;cursor:pointer;transition:opacity .2s}
    .dg .p3:hover,.dg .p3.sel{--m1:94%;--m2:66%;--m3:46%}
    .dg .p3.dim{opacity:.2}
    .dg .f1{fill:color-mix(in srgb,var(--c,var(--ce)) var(--m1,66%),#0c1428)}
    .dg .f2{fill:color-mix(in srgb,var(--c,var(--ce)) var(--m2,42%),#080e1c)}
    .dg .f3{fill:color-mix(in srgb,var(--c,var(--ce)) var(--m3,26%),#050a14)}
    .dg .p3 .part{stroke:color-mix(in srgb,var(--c,var(--ce)) 40%,#0a1024);stroke-width:.8;stroke-linejoin:round;transition:stroke .15s,filter .15s}
    .dg .p3:hover .part,.dg .p3.sel .part{stroke:var(--c,var(--ce));stroke-width:1.5;filter:drop-shadow(0 0 6px var(--c,var(--ce)))}
    .dg .p3 .etch{stroke:color-mix(in srgb,var(--c,var(--ce)) 60%,transparent);fill:none;stroke-width:.9}
    .dg .p3 .lit{fill:color-mix(in srgb,var(--c,var(--ce)) 78%,transparent)}
    .dg .p3 .lbl{fill:#e8eeff} .dg .p3:hover .lbl,.dg .p3.sel .lbl{fill:var(--c,var(--ce))}
    .dg .p3 .dot{fill:var(--c,var(--ce))}
    .dg .p3 .leader{stroke:color-mix(in srgb,var(--c,var(--ce)) 50%,#1e2a48);stroke-width:1;fill:none}
    .dg .p3:hover .leader,.dg .p3.sel .leader{stroke:var(--c,var(--ce));stroke-width:1.6}
    .dg .p3 rect.bg{fill:transparent} .dg .p3:hover rect.bg,.dg .p3.sel rect.bg{fill:color-mix(in srgb,var(--c,var(--ce)) 13%,transparent)}
    .dg .grd{stroke:rgba(120,150,210,.14);fill:none;stroke-width:.7}
    .dg .axis{stroke:rgba(120,150,210,.3);stroke-width:1;fill:none;stroke-dasharray:3 4}
    /* ---- 題材供應鏈圖：上游／中游／下游三段 + 站點 + 流動彩帶 + 個股標籤 ---- */
    .dg3 .band rect{fill:rgba(30,42,72,.5);stroke:rgba(120,150,210,.18)}
    .dg3 .band text{font-size:12px;font-weight:600;fill:#a9b6d6;letter-spacing:.03em}
    .dg3 .band.b0 rect{fill:rgba(62,224,255,.10);stroke:rgba(62,224,255,.28)} .dg3 .band.b0 text{fill:#9fe6ff}
    .dg3 .band.b1 rect{fill:rgba(139,123,255,.10);stroke:rgba(139,123,255,.3)} .dg3 .band.b1 text{fill:#c3baff}
    .dg3 .band.b2 rect{fill:rgba(255,180,84,.10);stroke:rgba(255,180,84,.28)} .dg3 .band.b2 text{fill:#ffd79a}
    .dg3 .stn .slot{fill:rgba(18,26,46,.55);stroke:rgba(120,150,210,.12)}
    .dg3 .stn:hover .slot,.dg3 .stn.sel .slot{fill:color-mix(in srgb,var(--c,var(--ce)) 10%,rgba(18,26,46,.7));stroke:var(--c,var(--ce))}
    .dg3 .stn.dim{opacity:.26}
    .dg3 .shadow{fill:rgba(0,0,0,.34)}
    .dg3 .rib{stroke-width:9;stroke-linecap:round}
    .dg3 .rib.bg{stroke:rgba(120,150,210,.13)}
    .dg3 .rib.flow{stroke:rgba(62,224,255,.5);stroke-dasharray:10 16;animation:dgdash 2.2s linear infinite}
    .dg3 .scode{cursor:pointer}
    .dg3 .scode rect{fill:color-mix(in srgb,var(--c,var(--ce)) 14%,rgba(15,23,43,.9));stroke:color-mix(in srgb,var(--c,var(--ce)) 42%,transparent)}
    .dg3 .scode text{font-size:11.5px;fill:#d6e2ff;font-weight:600}
    .dg3 .scode:hover rect{fill:color-mix(in srgb,var(--c,var(--ce)) 34%,rgba(15,23,43,.9));stroke:var(--c,var(--ce))}
    .dg3 .scode:hover text{fill:#fff}
    .dg3 .step .num{fill:color-mix(in srgb,var(--c,var(--ce)) 55%,#0b1226);stroke:color-mix(in srgb,var(--c,var(--ce)) 70%,transparent)}
    .dg3 .step .nn{font-size:11px;font-weight:700;fill:#e8eeff;font-family:"JetBrains Mono",monospace}
  </style>`;

  // 右側說明列：圓點 + 標題 + 副標 + 引線到零件上的 (tx,ty)
  function labelRow(seg, x, y, title, sub, tx, ty, w) {
    w = w || 250;
    const elbow = x - 14;
    return `<g class="lrow" data-seg="${seg}"><rect class="bg" x="${x - 8}" y="${y - 15}" width="${w}" height="34" rx="6"/>
      ${tx != null ? `<path class="leader" d="M${tx},${ty} L${elbow},${ty} L${elbow},${y - 2} L${x - 2},${y - 2}"/>` : ''}
      <circle class="dot" cx="${x + 5}" cy="${y - 2}" r="4"/>
      <text class="lbl" x="${x + 16}" y="${y + 2}">${title}</text><text class="sub" x="${x + 16}" y="${y + 15}">${sub}</text></g>`;
  }
  // 底部流程列：一串步驟方塊，帶移動的光點
  function processBar(x, y, steps, w) {
    w = w || 150; const gap = 12;
    const boxes = steps.map((s, i) => { const bx = x + i * (w + gap); return `<g data-seg="${s.seg}"><rect class="part" x="${bx}" y="${y}" width="${w}" height="34" rx="7" fill="#0f172b"/><text class="lbl" x="${bx + 12}" y="${y + 16}" style="font-size:12px">${s.t}</text><text class="sub" x="${bx + 12}" y="${y + 28}">${s.s}</text></g>`
      + (i < steps.length - 1 ? `<path class="flow fast" d="M${bx + w},${y + 17} L${bx + w + gap},${y + 17}" stroke="#3ee0ff" stroke-width="2"/>` : ''); }).join('');
    const total = steps.length * (w + gap) - gap;
    return `<g>${boxes}<circle r="3" fill="#fff" opacity=".9"><animateMotion dur="6s" repeatCount="indefinite" path="M${x},${y + 17} L${x + total},${y + 17}"/></circle></g>`;
  }
  const chainLink = (chain, x, y, text) => `<g data-chain="${chain}"><rect x="${x}" y="${y}" width="${text.length * 13 + 26}" height="30" rx="8" fill="#0f172b" stroke="#2a3860"/><text class="lbl" x="${x + 13}" y="${y + 19}" style="fill:#3ee0ff;font-weight:600">${text}</text></g>`;

  /* ================================================================ 等角 3D 工具箱
     投影：模型 x 往畫面右下、y 往畫面左下、z 往上。所有題材產品圖共用這一套，
     立體語言（光影、角度、厚度）才會一致，看起來才像同一套產品圖而不是十八張拼圖。
     三個面固定用 f1（頂，最亮）／f2（右，中）／f3（左，最暗），顏色一律由 --c 混出來，
     所以「點族群 → 零件同色」是免費的：改 --c 三個面一起變。 */
  const IX = 0.866, IY = 0.5;
  const px = (x, y) => (x - y) * IX;
  const py = (x, y, z) => (x + y) * IY - (z || 0);
  const P3 = (x, y, z) => px(x, y).toFixed(1) + ',' + py(x, y, z).toFixed(1);
  const fc = (cls, pts) => `<path class="part ${cls}" d="M${pts.join('L')}Z"/>`;
  // 把 2D 內容貼到 z 高度的水平面上（模型座標不變，交給矩陣壓成等角）
  const onTop = (z, inner) => `<g transform="matrix(${IX},${IY},${-IX},${IY},0,${-(z || 0)})">${inner}</g>`;

  // 立方體：(x,y,z) 是底面近角，w/d/h 為 x/y/z 三個方向的長度
  function box(x, y, z, w, d, h, inner) {
    return fc('f2', [P3(x + w, y, z + h), P3(x + w, y + d, z + h), P3(x + w, y + d, z), P3(x + w, y, z)])
      + fc('f3', [P3(x + w, y + d, z + h), P3(x, y + d, z + h), P3(x, y + d, z), P3(x + w, y + d, z)])
      + fc('f1', [P3(x, y, z + h), P3(x + w, y, z + h), P3(x + w, y + d, z + h), P3(x, y + d, z + h)])
      + (inner ? onTop(z + h, inner) : '');
  }
  // 圓柱（馬達、變壓器、減速機、風扇軸）。inner 的座標原點是圓柱中心，方便畫扇葉／鏡頭。
  function cyl(x, y, z, r, h, inner) {
    const cx = px(x, y), cy = py(x, y, z + h), by = py(x, y, z);
    const rx = r * 1.2247, ry = r * 0.7071;
    return `<path class="part f2" d="M${(cx - rx).toFixed(1)},${cy.toFixed(1)} V${by.toFixed(1)} A${rx.toFixed(1)},${ry.toFixed(1)} 0 0 0 ${(cx + rx).toFixed(1)},${by.toFixed(1)} V${cy.toFixed(1)}Z"/>`
      + `<ellipse class="part f1" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}"/>`
      + (inner ? onTop(z + h, `<g transform="translate(${x},${y})">${inner}</g>`) : '');
  }
  // 立起來的面板（顯示器、天線陣列、太陽能板）：沿 x 展開、往 z 長高、厚度 t 沿 y
  function panel(x, y, z, w, h, t, inner) {
    return fc('f2', [P3(x + w, y, z + h), P3(x + w, y + t, z + h), P3(x + w, y + t, z), P3(x + w, y, z)])
      + fc('f1', [P3(x, y, z + h), P3(x + w, y, z + h), P3(x + w, y + t, z + h), P3(x, y + t, z + h)])
      + fc('f3', [P3(x, y, z), P3(x + w, y, z), P3(x + w, y, z + h), P3(x, y, z + h)])
      + (inner ? `<g transform="translate(${px(x, y).toFixed(1)},${py(x, y, z).toFixed(1)}) matrix(${IX},${IY},0,-1,0,0)">${inner}</g>` : '');
  }
  // 沿 3D 折線走的管路／訊號（傳入 [x,y,z] 陣列）
  const wire = (pts, cls, col, w) => `<path class="${cls || ''}" d="M${pts.map(p => P3(p[0], p[1], p[2])).join('L')}" fill="none" stroke="${col || '#3ee0ff'}" stroke-width="${w || 2}" stroke-linecap="round"/>`;
  // 地板格線（放在 onTop(0) 裡，讓場景站得住）
  function floor(w, d, step, x0, y0) {
    const a = []; x0 = x0 || 0; y0 = y0 || 0;
    for (let x = 0; x <= w; x += step) a.push(`M${x0 + x},${y0} L${x0 + x},${y0 + d}`);
    for (let y = 0; y <= d; y += step) a.push(`M${x0},${y0 + y} L${x0 + w},${y0 + y}`);
    return onTop(0, `<path class="grd" d="${a.join(' ')}"/>`);
  }
  // 頂面上的方格陣列（晶片 die、記憶體顆粒、電池芯）
  function cells(x, y, w, d, nx, ny, gap) {
    gap = gap == null ? 2 : gap;
    const cw = (w - gap * (nx + 1)) / nx, ch = (d - gap * (ny + 1)) / ny, a = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++)
      a.push(`<rect class="lit pulse" x="${(x + gap + i * (cw + gap)).toFixed(1)}" y="${(y + gap + j * (ch + gap)).toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="1" style="animation-delay:${(((i + j) % 6) * 0.34).toFixed(2)}s"/>`);
    return a.join('');
  }
  // 零件外框：把幾何、data-part（點了看個股）、data-seg（跟環節同色）綁在一起
  const p3 = (o, inner) => `<g class="p3" data-part="${o.id}"${o.codes && o.codes.length ? ` data-codes="${o.codes.join(',')}"` : ''}${o.seg ? ` data-seg="${o.seg}"` : ''}${o.chain ? ` data-chain="${o.chain}"` : ''}>${inner}</g>`;
  // 右側說明列（3D 版：綁 data-part，不是 data-seg）
  function lrow3(o, x, y, w, i) {
    w = w || 262;
    // 每一列的轉折點錯開，不然七條引線的垂直段會疊成一條粗線，看起來像畫錯
    const elbow = x - 14 - (i || 0) * 8;
    return `<g class="p3 lrow" data-part="${o.id}"${o.codes && o.codes.length ? ` data-codes="${o.codes.join(',')}"` : ''}${o.seg ? ` data-seg="${o.seg}"` : ''}>
      <rect class="bg" x="${x - 8}" y="${y - 15}" width="${w}" height="34" rx="6"/>
      ${o.ax != null ? `<path class="leader" d="M${o.ax.toFixed(1)},${o.ay.toFixed(1)} L${elbow},${o.ay.toFixed(1)} L${elbow},${y - 2} L${x - 2},${y - 2}"/>` : ''}
      <circle class="dot" cx="${x + 5}" cy="${y - 2}" r="4"/>
      <text class="lbl" x="${x + 16}" y="${y + 2}">${o.label}</text><text class="sub" x="${x + 16}" y="${y + 15}">${o.sub || ''}</text></g>`;
  }

  // ================================================================ 半導體：CoWoS 2.5D 剖面
  function hbmStack(x, y, delay) {
    const layers = [];
    for (let i = 0; i < 8; i++) layers.push(`<rect class="pulse" x="${x}" y="${y + i * 12}" width="70" height="10" rx="1.5" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".7" style="animation-delay:${delay + i * .12}s"/>`);
    const tsv = [x + 18, x + 35, x + 52].map(tx => `<line class="flow slow" x1="${tx}" y1="${y - 2}" x2="${tx}" y2="${y + 108}" stroke="rgba(139,123,255,.7)" stroke-width="1.2"/>`).join('');
    return `<g>${layers.join('')}<rect x="${x}" y="${y + 96}" width="70" height="12" rx="1.5" fill="#1f2f5c" stroke="#3ee0ff" stroke-width=".7"/>${tsv}</g>`;
  }
  function semiconductor() {
    const dieCells = []; for (let r = 0; r < 4; r++) for (let c = 0; c < 6; c++) dieCells.push(`<rect class="pulse" x="${522 + c * 27}" y="${150 + r * 22}" width="22" height="17" rx="2" fill="rgba(62,224,255,.22)" style="animation-delay:${((r * 6 + c) % 7) * .28}s"/>`);
    const bumps = (y, r, step, x0, x1, col) => { const a = []; for (let x = x0; x <= x1; x += step) a.push(`<circle cx="${x}" cy="${y}" r="${r}" fill="${col}"/>`); return a.join(''); };
    const tsv = []; for (let x = 340; x <= 860; x += 26) tsv.push(`<line x1="${x}" y1="262" x2="${x}" y2="296" stroke="rgba(62,224,255,.35)" stroke-width="1"/>`);
    const vias = []; for (let x = 330; x <= 870; x += 36) vias.push(`<line x1="${x}" y1="314" x2="${x}" y2="356" stroke="rgba(255,180,84,.45)" stroke-width="1.2"/>`);
    const wafer = (() => { const cx = 126, cy = 300, R = 66; const lines = []; for (let d = -54; d <= 54; d += 18) { const h = Math.sqrt(R * R - d * d) - 2; lines.push(`<line x1="${cx - h}" y1="${cy + d}" x2="${cx + h}" y2="${cy + d}" stroke="#0b1224" stroke-width=".9"/><line x1="${cx + d}" y1="${cy - h}" x2="${cx + d}" y2="${cy + h}" stroke="#0b1224" stroke-width=".9"/>`); } return lines.join(''); })();
    return `<svg class="dg" viewBox="0 0 1220 545" width="100%" style="display:block">${STYLE}
      <defs>
        <linearGradient id="sgSi" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b3f7a"/><stop offset="1" stop-color="#1a2856"/></linearGradient>
        <linearGradient id="sgLid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6b7aa8"/><stop offset=".5" stop-color="#3d4a74"/><stop offset="1" stop-color="#2a3560"/></linearGradient>
        <linearGradient id="sgAbf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d4d38"/><stop offset="1" stop-color="#12331f"/></linearGradient>
        <linearGradient id="sgPcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#173a2a"/><stop offset="1" stop-color="#0f2a1e"/></linearGradient>
        <linearGradient id="sgInter" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#1a2542"/><stop offset=".5" stop-color="#25335f"/><stop offset="1" stop-color="#1a2542"/></linearGradient>
        <linearGradient id="sgWafer" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b4f8c"/><stop offset="1" stop-color="#1c2a55"/></linearGradient>
        <clipPath id="sgWaferClip"><circle cx="126" cy="300" r="66"/></clipPath>
      </defs>
      <text class="ttl" x="16" y="26">CoWoS 2.5D 先進封裝剖面</text>
      <text class="cap" x="16" y="44">由下往上：主機板 → 載板 → 矽中介層 → 邏輯晶片與 HBM → 上蓋。左側是晶片的來路，右側說明對應的供應鏈環節。</text>

      <!-- 左：晶片誕生流程 -->
      <g data-seg="ip_eda"><rect class="part" x="16" y="70" width="220" height="50" rx="8" fill="#0f172b"/><text class="lbl" x="28" y="90">IP / EDA / 設計服務</text><text class="sub" x="28" y="106">矽智財授權、ASIC 設計服務（NRE）</text></g>
      <path class="flow" d="M126,120 L126,144" stroke="#3ee0ff" stroke-width="2"/>
      <g data-seg="ic_design"><rect class="part" x="16" y="146" width="220" height="50" rx="8" fill="#0f172b"/><text class="lbl" x="28" y="166">IC 設計</text><text class="sub" x="28" y="182">GPU / ASIC / 網通晶片，交付 GDS 光罩資料</text></g>
      <path class="flow" d="M126,196 L126,228" stroke="#3ee0ff" stroke-width="2"/>
      <g data-seg="foundry">
        <circle class="part" cx="126" cy="300" r="66" fill="url(#sgWafer)"/>
        <g clip-path="url(#sgWaferClip)">${wafer}<rect class="scan" x="60" y="292" width="132" height="4" fill="rgba(62,224,255,.55)"/></g>
        <rect x="118" y="292" width="16" height="16" rx="2" fill="#3ee0ff" opacity=".9"/>
        <text class="lbl" x="56" y="392">晶圓代工 3nm / 2nm</text><text class="sub" x="42" y="408">300mm 晶圓 → 切割成邏輯晶片；HBM 基底晶片</text>
      </g>
      <path class="flow" d="M196,300 L300,300" stroke="#3ee0ff" stroke-width="2"/><text class="cap" x="206" y="292">切割 → 封裝</text>
      ${chainLink('ai_server', 16, 444, '→ 下游：組裝進 AI 伺服器')}
      <text class="cap" x="16" y="500">示意圖，非實物比例</text><text class="cap" x="16" y="516">零件顏色＝環節色；點零件看供應商</text>

      <!-- 中：剖面（由下往上） -->
      <g data-seg="abf_pcb"><rect class="part" x="300" y="384" width="600" height="32" rx="4" fill="url(#sgPcb)"/>
        <path class="flow slow" d="M316,394 H560 M316,406 H420 M640,394 H884 M700,406 H884" stroke="rgba(255,180,84,.55)" stroke-width="1.4"/>
        <text class="sub" x="312" y="404" style="fill:#c7f2d6">主機板 PCB</text></g>
      <g data-seg="abf_pcb">${bumps(372, 7, 30, 330, 870, '#d9a648')}<text class="sub" x="880" y="366" style="font-size:9.5px">BGA</text></g>
      <g data-seg="abf_pcb"><rect class="part" x="310" y="310" width="580" height="50" rx="4" fill="url(#sgAbf)"/>
        <path d="M318,322 H882 M318,334 H882 M318,346 H882" stroke="rgba(255,255,255,.08)"/>${vias.join('')}
        <text class="sub" x="322" y="329" style="fill:#c7f2d6">ABF 載板（多層增層基板）</text></g>
      <g data-seg="adv_pkg">${bumps(304, 4, 20, 330, 870, '#ffb454')}</g>
      <g data-seg="adv_pkg"><rect class="part" x="320" y="258" width="560" height="42" rx="3" fill="url(#sgInter)"/>
        ${tsv.join('')}<path d="M330,270 H870 M330,280 H870 M330,290 H870" stroke="rgba(62,224,255,.22)"/>
        <path class="flow fast" d="M375,272 H600" stroke="#3ee0ff" stroke-width="2"/><path class="flow fast rev" d="M600,286 H815" stroke="#3ee0ff" stroke-width="2"/>
        <text class="sub" x="332" y="294" style="fill:#9fd8ff">矽中介層 Interposer</text></g>
      <g data-seg="adv_pkg">${bumps(254, 2.5, 10, 340, 870, 'rgba(255,180,84,.85)')}</g>
      <g data-seg="hbm">${hbmStack(340, 142, 0)}${hbmStack(420, 142, .3)}${hbmStack(700, 142, .6)}${hbmStack(780, 142, .9)}<rect class="part" x="336" y="138" width="158" height="116" rx="3" fill="none"/><rect class="part" x="696" y="138" width="158" height="116" rx="3" fill="none"/></g>
      <g data-seg="foundry"><rect class="part" x="510" y="142" width="180" height="108" rx="3" fill="url(#sgSi)"/>${dieCells.join('')}<text class="mono" x="522" y="243" style="font-size:9.5px;fill:#9fd8ff">GPU / ASIC DIE</text></g>
      <g data-seg="osat_test"><rect x="330" y="134" width="540" height="6" fill="#0b1224"/><rect class="part" x="330" y="110" width="540" height="26" rx="5" fill="url(#sgLid)"/>
        ${[380, 460, 540, 620, 700, 780].map((x, i) => `<path class="heat" d="M${x},104 c4,-6 -4,-10 0,-16" stroke="#ff8fab" stroke-width="1.6" fill="none" style="animation-delay:${i * .4}s"/>`).join('')}
        <text class="sub" x="596" y="128" style="fill:#e8eeff" text-anchor="middle">散熱上蓋（Lid）</text></g>

      <!-- 右：說明欄（引線接到零件） -->
      ${labelRow('osat_test', 934, 120, '封裝上蓋 / 最終測試', '封測廠：上蓋、燒機、分選出貨', 870, 122)}
      ${labelRow('hbm', 934, 172, 'HBM3E 記憶體堆疊', '8–12 層 DRAM + 基底晶片，TSV 貫穿', 854, 196)}
      ${labelRow('foundry', 934, 224, 'GPU / ASIC 邏輯晶片', '3nm / 2nm 先進製程晶粒', 690, 230)}
      ${labelRow('adv_pkg', 934, 276, '矽中介層 Interposer', 'CoWoS-S/L：微凸塊、TSV、RDL 佈線', 880, 279)}
      ${labelRow('abf_pcb', 934, 328, 'ABF 載板', '多層增層基板，C4 凸塊接中介層', 890, 335)}
      ${labelRow('abf_pcb', 934, 380, 'BGA → 主機板 PCB', '錫球接到伺服器／加速卡主機板', 900, 400)}

      <!-- 下：製程流程 -->
      <text class="cap" x="300" y="462">製造流程</text>
      ${processBar(300, 470, [{ seg: 'ip_eda', t: '設計', s: 'IP / EDA' }, { seg: 'foundry', t: '晶圓製造', s: '前段製程' }, { seg: 'adv_pkg', t: 'CoWoS 堆疊', s: '中介層 + 晶片 + HBM' }, { seg: 'osat_test', t: '上蓋 / 測試', s: '封測廠' }, { seg: 'abf_pcb', t: '上板', s: '載板 → PCB' }], 152)}
    </svg>`;
  }

  // ================================================================ AI 伺服器：機櫃 + 運算托盤爆炸圖
  function gpuModule(x, y, i) {
    return `<g transform="translate(${x},${y})">
      <rect x="0" y="0" width="80" height="36" rx="3" fill="#163a2a" stroke="#2a3860"/>
      <rect x="8" y="5" width="64" height="26" rx="2" fill="#1a2542" stroke="#2a3860" stroke-width=".7"/>
      <rect x="9" y="7" width="13" height="10" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/><rect x="9" y="19" width="13" height="10" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/>
      <rect x="58" y="7" width="13" height="10" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/><rect x="58" y="19" width="13" height="10" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/>
      <rect x="27" y="7" width="26" height="22" rx="1.5" fill="#1f2f5c" stroke="#3ee0ff" stroke-width=".8"/>
      <rect class="pulse" x="30" y="10" width="20" height="16" fill="rgba(62,224,255,.35)" style="animation-delay:${i * .3}s"/>
    </g>`;
  }
  function aiServer() {
    const K = 0.53; // skewX(-28°) 會把 x 往左移 0.53*y，右欄引線用這個換算
    const sx = (x, y) => Math.round(x - K * y);
    const trays = []; for (let i = 0; i < 8; i++) { const y = 118 + i * 40; trays.push(`<g><rect x="34" y="${y}" width="172" height="32" rx="4" fill="#141e36" stroke="#1e2a48"/>${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<rect class="pulse" x="${52 + j * 17}" y="${y + 9}" width="12" height="14" rx="2" fill="rgba(62,224,255,.28)" stroke="rgba(62,224,255,.5)" stroke-width=".6" style="animation-delay:${((i + j) % 5) * .35}s"/>`).join('')}<circle class="blink b${(i % 3) + 1}" cx="42" cy="${y + 16}" r="2.4" fill="#2ee59d"/><rect x="192" y="${y + 6}" width="8" height="20" rx="1" fill="#0f172b" stroke="#2a3860" stroke-width=".6"/></g>`); }
    const psu = [0, 1, 2, 3, 4, 5].map(j => `<rect x="${40 + j * 28}" y="452" width="24" height="42" rx="2" fill="#2b1f3f" stroke="#2a3860"/><path class="flow" d="M${52 + j * 28},458 V488" stroke="#ffb454" stroke-width="2"/>`).join('');
    const modules = []; for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) modules.push(gpuModule(600 + c * 100, 330 + r * 52, r * 4 + c));
    const cages = [0, 1, 2, 3].map(j => `<rect x="${1004 + j * 14}" y="452" width="11" height="26" rx="1.5" fill="#0f172b" stroke="#2a3860"/><circle class="blink b${(j % 3) + 1}" cx="${1009.5 + j * 14}" cy="${458}" r="1.8" fill="#3ee0ff"/>`).join('');
    const traces = [[590, 470], [640, 458], [720, 476], [800, 462], [880, 472], [940, 460]].map(([x, y], i) => `<path class="flow ${i % 2 ? 'rev' : ''} slow" d="M${x},${y} h${40 + (i % 3) * 20}" stroke="rgba(255,180,84,.5)" stroke-width="1.3"/>`).join('');
    const weave = []; for (let x = 570; x <= 990; x += 22) weave.push(`<line x1="${x}" y1="522" x2="${x}" y2="560" stroke="rgba(120,200,150,.16)"/>`); for (let y = 530; y <= 556; y += 9) weave.push(`<line x1="562" y1="${y}" x2="1000" y2="${y}" stroke="rgba(120,200,150,.16)"/>`);
    return `<svg class="dg" viewBox="0 0 1220 662" width="100%" style="display:block">${STYLE}
      <defs>
        <linearGradient id="agCool" x1="0" x2="1"><stop offset="0" stop-color="#3ee0ff"/><stop offset="1" stop-color="#ff4d6d"/></linearGradient>
        <linearGradient id="agPlate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(62,224,255,.28)"/><stop offset="1" stop-color="rgba(62,224,255,.08)"/></linearGradient>
        <linearGradient id="agPcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#173a2a"/><stop offset="1" stop-color="#10291d"/></linearGradient>
        <linearGradient id="agCcl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#12331f"/><stop offset="1" stop-color="#0c2416"/></linearGradient>
      </defs>
      <text class="ttl" x="16" y="26">AI 伺服器機櫃與 GPU 運算托盤</text>
      <text class="cap" x="16" y="44">左：整機櫃（交換器、8 個運算托盤、電源櫃、液冷 CDU）。中：一個運算托盤拆開由下往上看。右：對應的供應鏈環節。</text>

      <!-- 左：機櫃 -->
      <g data-seg="assembly"><rect class="part" x="20" y="60" width="200" height="550" rx="10" fill="#0f172b"/>${trays.join('')}<text class="sub" x="34" y="112">GPU 運算托盤 ×8</text><text class="lbl" x="28" y="632">整機櫃 Rack（系統組裝）</text></g>
      <g data-seg="switch"><rect class="part" x="34" y="72" width="172" height="30" rx="4" fill="#182a3f"/>${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(j => `<rect class="blink b${(j % 3) + 1}" x="${44 + j * 12}" y="80" width="8" height="10" rx="1" fill="#ffb454"/>`).join('')}<circle class="blink b2" cx="196" cy="87" r="3" fill="#3ee0ff"/><text class="sub" x="150" y="68" style="fill:#e8eeff">ToR 交換器</text></g>
      <g data-seg="power"><rect class="part" x="34" y="446" width="172" height="54" rx="4" fill="#1a1530"/>${psu}<text class="sub" x="34" y="512">電源櫃 PSU / BBU（800V HVDC）</text></g>
      <g data-seg="thermal"><rect class="part" x="34" y="524" width="172" height="76" rx="4" fill="#0e2a33"/>
        <circle class="spin" cx="66" cy="562" r="16" fill="none" stroke="#3ee0ff" stroke-width="2.5" stroke-dasharray="7 6"/><circle cx="66" cy="562" r="4" fill="#3ee0ff"/>
        <text class="lbl" x="94" y="556" style="font-size:12px">CDU</text><text class="sub" x="94" y="571">冷卻液分配 / 熱交換</text><text class="sub" x="94" y="585">冷水進 · 熱水回</text>
        <path class="flow" d="M212,596 V120" stroke="#3ee0ff" stroke-width="2.4"/><path class="flow rev" d="M218,120 V596" stroke="#ff4d6d" stroke-width="2.4"/></g>

      <!-- 中：托盤爆炸圖（skewX 做出斜視角） -->
      <g transform="skewX(-28)">
        <g data-seg="ccl"><rect x="560" y="528" width="440" height="40" rx="3" fill="#0a1d12"/><rect class="part" x="560" y="520" width="440" height="40" rx="3" fill="url(#agCcl)"/>${weave.join('')}</g>
        <g data-seg="abf_pcb"><rect x="560" y="453" width="440" height="40" rx="3" fill="#0b2418"/><rect class="part" x="560" y="445" width="440" height="40" rx="3" fill="url(#agPcb)"/>${traces}
          ${[0, 1, 2].map(j => `<rect x="${640 + j * 120}" y="449" width="70" height="7" rx="1.5" fill="#0f172b" stroke="#2a3860" stroke-width=".7"/>`).join('')}</g>
        <g data-seg="power"><rect class="part" x="470" y="445" width="76" height="40" rx="3" fill="#1a1530"/><path class="flow" d="M478,452 H538 M478,462 H538 M478,472 H538 M478,482 H538" stroke="#ffb454" stroke-width="2"/></g>
        <g data-seg="optical"><rect class="part" x="1000" y="447" width="64" height="36" rx="3" fill="#141e36"/>${cages}</g>
        <g data-seg="adv_pkg"><rect x="580" y="316" width="440" height="110" rx="6" fill="rgba(20,30,54,.55)"/>${modules.join('')}<rect class="part" x="580" y="316" width="440" height="110" rx="6" fill="none"/></g>
        <g data-seg="thermal"><rect class="part" x="560" y="150" width="480" height="120" rx="8" fill="url(#agPlate)"/>
          <path class="flow" d="M580,172 H1020 M580,196 H1020 M580,220 H1020 M580,244 H1020" stroke="url(#agCool)" stroke-width="3.5" fill="none" opacity=".85"/>
          <path class="flow" d="M520,172 H580" stroke="#3ee0ff" stroke-width="3.5"/><path class="flow rev" d="M1020,244 H1080" stroke="#ff4d6d" stroke-width="3.5"/>
          <circle cx="520" cy="172" r="6" fill="#0f172b" stroke="#3ee0ff" stroke-width="2"/><circle cx="1080" cy="244" r="6" fill="#0f172b" stroke="#ff4d6d" stroke-width="2"/>
          <path class="flow slow" d="M600,290 V310 M700,290 V310 M800,290 V310 M900,290 V310 M1000,290 V310" stroke="rgba(62,224,255,.5)" stroke-width="1.2"/></g>
      </g>
      <text class="sub" x="${sx(560, 585)}" y="585">CCL 銅箔基板（板材）</text>
      <text class="sub" x="${sx(560, 508)}" y="508">主機板 高階 PCB · 連接器 · 供電模組</text>
      <text class="sub" x="${sx(580, 442)}" y="442">GPU 模組 ×8（CoWoS 封裝：邏輯晶片 + HBM）</text>
      <text class="sub" x="${sx(560, 146)}" y="146">液冷冷板（冷水進 → 熱水回）+ 快接頭</text>

      <!-- 右：說明欄 -->
      <g data-seg="hyperscaler"><path class="part" d="M954,88 a18,18 0 0 1 34,-8 a16,16 0 0 1 30,10 a14,14 0 0 1 -6,27 h-56 a15,15 0 0 1 -2,-29 z" fill="#0f172b"/>
        ${[0, 1, 2].map(j => `<circle class="drop d${j + 1}" cx="${966 + j * 22}" cy="126" r="2.5" fill="#8b7bff"/>`).join('')}
        <text class="lbl" x="1030" y="94">雲端業者（終端需求）</text><text class="sub" x="1030" y="110">Microsoft / Google / Amazon / Meta</text></g>
      ${labelRow('thermal', 934, 196, '液冷冷板 / CDU', '冷板、快接頭、分歧管；機櫃 CDU 循環', sx(1040, 210), 210)}
      ${labelRow('adv_pkg', 934, 248, 'GPU 模組（CoWoS 封裝）', '邏輯晶片 + HBM 放在矽中介層上', sx(1020, 330), 330)}
      ${labelRow('foundry', 934, 300, 'GPU 晶片・晶圓代工', '3nm / 2nm 邏輯晶粒（看半導體鏈）', sx(946, 356), 356)}
      ${labelRow('hbm', 934, 352, 'HBM 記憶體', '每顆 GPU 旁 4–8 顆 HBM 堆疊', sx(968, 402), 402)}
      ${labelRow('abf_pcb', 934, 404, '主機板 高階 PCB / ABF 載板', '高層數 PCB、連接器、模組載板', sx(1000, 465), 465)}
      ${labelRow('ccl', 934, 456, 'CCL 銅箔基板', '高速低損耗板材，PCB 的原料', sx(1000, 540), 540)}
      ${labelRow('optical', 934, 508, '光通訊 / 矽光子', '800G–1.6T 光模組、CPO（前面板）', sx(1064, 465), 465)}
      ${labelRow('switch', 934, 560, '交換器（ToR / Spine）', '機櫃頂端（左圖上方）接叢集網路', null, null)}

      <!-- 下：流程 -->
      <text class="cap" x="250" y="612">從晶片到交付</text>
      ${processBar(250, 620, [{ seg: 'foundry', t: 'GPU 晶片', s: '晶圓代工' }, { seg: 'adv_pkg', t: 'CoWoS 封裝', s: '＋HBM' }, { seg: 'abf_pcb', t: '模組上板', s: 'PCB / 載板' }, { seg: 'assembly', t: '托盤 → 機櫃', s: '系統組裝' }, { seg: 'hyperscaler', t: '交付 CSP', s: '資料中心' }], 118)}
      ${chainLink('semiconductor', 934, 622, '← 看半導體鏈：晶片怎麼來')}
    </svg>`;
  }

  window.Diagrams = { ai_server: aiServer, semiconductor };
  // 題材產品圖（site/themes3d.js）共用同一套樣式與 3D 工具，兩邊看起來才是同一套產品圖
  window.DG = { STYLE, labelRow, lrow3, processBar, chainLink, IX, IY, px, py, P3, onTop, box, cyl, panel, wire, floor, cells, p3 };
})();
