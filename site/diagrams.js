/* 產品剖析圖（原創示意 SVG，含動畫）。每個零件帶 data-seg = supply_chain.yaml 的環節 id；
   零件顏色由 industry.js 依環節色（App.L.scolor）注入 --c，所以剖析圖、環節色標、關聯圖、族群卡片顏色一致。
   版面規則：零件畫在中間、說明文字排在右側欄位用引線接過去，文字絕不疊在零件上。 */
(function () {
  'use strict';
  const STYLE = `<style>
    .dg{font-family:"Noto Sans TC",sans-serif;--dg-accent:#3ee0ff}
    /* 零件群組裡的強調色＝那個環節的顏色；群組外（流程箭頭、良率曲線、比例尺）就是固定的青色。
       這兩行是 --dg-accent 唯一的定義處 —— 寫在 :root 的話 var(--c) 會在 :root 就被解析掉，
       每個零件自己的環節色永遠吃不到。 */
    .dg [data-seg],.dg .p3{--dg-accent:var(--c,#3ee0ff)}
    .dg text{fill:var(--dg-ink-2,#a9b6d6);font-size:12px}
    .dg .ttl{font-size:15px;font-weight:700;fill:var(--dg-ink,#e8eeff);letter-spacing:.02em}
    .dg .cap{font-size:11.5px;fill:#6f7ea3}
    .dg .lbl{font-size:12.5px;fill:var(--dg-ink,#e8eeff);font-weight:600}
    .dg .sub{font-size:10.5px;fill:var(--dg-ink-3,#8ea0c4)}
    .dg .tag{font-family:"JetBrains Mono",monospace;font-size:10px;fill:var(--c,var(--dg-ink-3,#8ea0c4));letter-spacing:.04em}
    .dg .mono{font-family:"JetBrains Mono",monospace}
    .dg [data-seg]{cursor:pointer;transition:opacity .2s}
    .dg [data-seg] .part{transition:stroke .15s,filter .15s;stroke:color-mix(in srgb,var(--c,#3ee0ff) 55%,#2a3860)}
    /* B1（art-director 2026-09-21）：發光半徑收成變數。
       一張圖只有一個環節時（MLCC 那種單一族群的量產圖），點任何零件都會讓**全部**零件
       同時加上 .sel —— 14 個群組、11 個元素一起 drop-shadow，那就是 Andy 講的「螢光感太重」，
       而且 0 個被 dim ＝ 這個狀態沒有傳達任何資訊。那種圖掛 .dg1，--dg-glow:none 直接關掉發光。 */
    .dg [data-seg]:hover .part,.dg [data-seg].sel .part{stroke:var(--c,#3ee0ff);stroke-width:2.2;filter:var(--dg-glow,drop-shadow(0 0 7px var(--c,#3ee0ff)))}
    .dg.dg1{--dg-glow:none}
    .dg [data-seg].sel .lbl,.dg [data-seg]:hover .lbl{fill:var(--c,#3ee0ff)}
    .dg [data-seg] .dot{fill:var(--c,var(--dg-ink-3,#8ea0c4))}
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
    .dg .p3 .lbl{fill:var(--dg-ink,#e8eeff)} .dg .p3:hover .lbl,.dg .p3.sel .lbl{fill:var(--c,var(--ce))}
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
    /* ---- 量產圖的字級下限（AGENTS §11：文字最小 12px，手機也是）。
       舊的兩張圖 .sub 是 10.5px、.cap 11.5px、.tag 10px —— 那是 12px 規則之前畫的。
       新圖一律掛 .dgm，整張圖的最小字級被拉到 12px；舊圖不動，避免版面整個位移。 */
    .dgm .sub,.dgm .cap,.dgm .tag{font-size:12px}
    .dgm .lbl{font-size:12.5px}
    .dgm .hd{font-size:12.5px;font-weight:700;fill:var(--dg-ink,#e8eeff)}
    .dgm .num{font-family:"JetBrains Mono",monospace;font-size:12px;fill:#9fb0d0}
    .dgm .frame{fill:rgba(18,26,46,.5);stroke:rgba(120,150,210,.2)}
    .dgm .warn{fill:var(--dg-warn,#ff8fab)}
    /* B2（art-director 2026-09-21）：電荷疊色的透明度從 .26 降到 .12。
       量過：.26 的青色鋪滿整個有效層區，把陶瓷從暖米白 42° 推成偏綠 102°，
       而不鋪的保護層還是 42° —— 讀者會以為兩者是不同材質，但它們是同一種陶瓷。*/
    .dgm .chg{fill:var(--dg-accent);fill-opacity:var(--dg-chg-a,.12)}
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
  /* 底部流程列：一串步驟方塊，帶移動的光點。**共用函式，三張圖都在用。**
     B3（art-director 2026-09-21）：方塊本來高 34、標題基線 y+16、副標基線 y+28 ＝ 行距只有 12px。
     `.dgm .sub` 從 10.5px 升到 12px 之後，12px 的中文字配 12px 行距 ——
     量到 5 對文字的 bbox 互相重疊 1.7～2.0px（800px 與 1100px 都是），副標下緣也頂到框線。
     改成高 40、標題 y+16、副標 y+32（行距 16px）：上緣留 6.6px、下緣留 5.2px。
     光點與箭頭跟著移到新的垂直中線 y+20。 */
  const PB_H = 40, PB_MID = 20;
  function processBar(x, y, steps, w) {
    w = w || 150; const gap = 12;
    const boxes = steps.map((s, i) => { const bx = x + i * (w + gap); return `<g data-seg="${s.seg}"><rect class="part" x="${bx}" y="${y}" width="${w}" height="${PB_H}" rx="7" fill="#0f172b"/><text class="lbl" x="${bx + 12}" y="${y + 16}" style="font-size:12px">${s.t}</text><text class="sub" x="${bx + 12}" y="${y + 32}">${s.s}</text></g>`
      + (i < steps.length - 1 ? `<path class="flow fast" d="M${bx + w},${y + PB_MID} L${bx + w + gap},${y + PB_MID}" stroke="var(--dg-accent)" stroke-width="2"/>` : ''); }).join('');
    const total = steps.length * (w + gap) - gap;
    return `<g>${boxes}<circle r="3" fill="#fff" opacity=".9"><animateMotion dur="6s" repeatCount="indefinite" path="M${x},${y + PB_MID} L${x + total},${y + PB_MID}"/></circle></g>`;
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
  /* 切開面用的兩個平面。剖析圖的重點常常在「切下去看到什麼」，
     而 onTop 只處理水平面，所以補這兩支：
       onXZ(x0,y0)：y = y0 的垂直面（沿 x 展開）—— 疊層剖面就畫在這上面
       onYZ(x0,y0)：x = x0 的垂直面（沿 y 展開）—— 側邊餘白那種「第三個方向」的東西
     兩支都把內容的局部座標定成 (u, v)：u 沿該平面的水平方向、v 就是高度 z。
     ★ 行列式是負的（鏡射），所以**不要把文字放進去**，文字會左右相反。*/
  const onXZ = (x0, y0) => `<g transform="translate(${px(x0, y0).toFixed(1)},${py(x0, y0, 0).toFixed(1)}) matrix(${IX},${IY},0,-1,0,0)">`;
  const onYZ = (x0, y0) => `<g transform="translate(${px(x0, y0).toFixed(1)},${py(x0, y0, 0).toFixed(1)}) matrix(${-IX},${IY},0,-1,0,0)">`;

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

  /* ================================================================ 被動元件：MLCC 疊層剖析
     規格書：docs/diagram_specs/mlcc_stack.md（mechanical-engineer 2026-09-19 簽「可開畫」）。
     這張圖只回答兩件事：**為什麼疊越多層越貴、車規為什麼難做。**

     ---- 事實來源（2026-09-21 用 WebSearch 重新查證過一次，不是照抄規格書）----
     ★ 證據強度先講清楚：這個容器**只有 WebSearch 能用，WebFetch 一律回 EGRESS_BLOCKED**
       （murata.com / ele.kyocera.com / escatec.com / ctee.com.tw 逐一試過都是）。
       所以底下每一條的證據都是「**WebSearch 摘要**」，不是原文 —— 沒有人讀過整篇。
       原文讀不到的地方一律不寫成精確數字；網址留著是給下一個人去讀，不是宣稱我讀過。
       · 介電層 0.5–2 µm、內電極（Ni，BME 賤金屬）約 0.5–0.6 µm、層數 400–1000 層
         → USPTO 專利族 11302478 / 11037727 說明；Murata 官方部落格「next-generation MLCC」
       · 端子由內到外 Cu →〔導電樹脂〕→ Ni → Sn；**樹脂層夾在 Cu 與 Ni 之間**（不是最外層）
         → TDK soft-termination 技術文章 tdk-electronics.tdk.com/.../2237758
           KYOCERA/AVX 樹脂端子 ele.kyocera.com/en/technical/kavx_resinele/
       · 製程順序：流延 → 網印 → 疊層 → 加壓 → 切割 → 排膠 → **燒結** → 研磨 → **端電極** → 電鍍 → 測試編帶
         （燒結一定在端電極之前）→ dron-tech.com/news/the-most-comprehensive-process-flow-of-mlcc/
       · 尺寸代號兩套：EIA 0402 ＝ 公制 1005 ＝ 1.0×0.5 mm；EIA 0201 ＝ 公制 0603；EIA 01005 ＝ 公制 0402
         → blog.knowlescapacitors.com/blog/eia-mlcc-case-sizes-past-and-future
           core-emt.com/imperial-code-vs-metric-code-smd-components-sizes
       · AEC-Q200 涵蓋電性／耐濕／壽命／機械衝擊振動／**基板彎曲** → aecouncil.com AEC_Q004
       · 溫度：端電極燒附 **830–900 °C**（USPTO 專利摘要）vs 規格書引的 Murata「約 800 °C」——
         兩個摘要對不起來，所以畫面寫**區間 800–900 °C**，不挑一個當定論；
         燒結溫度一個摘要說 1050–1200 °C、另一個（Ni 內電極配方）說 1120–1200 °C，
         下限差 70 °C → **畫面乾脆不寫溫度**，只寫「還原氣氛高溫燒結」（見規格書 §6-B5）
       · 2026 村田對部分消費級（GRM／GRJ）與車規（GCM／GCJ／GCG）料號發 EOL，
         最後下單 2028-03-31、最後出貨 2029-03-31 → 工商時報 2026-09-10、鉅亨網、MoneyDJ
     ★ 查不到公開數字的一律不畫：**車規與消費級的良率差距一個百分比都不出現**（規格書 §6-C）。

     ---- 立體語言 ----
     2.5D 等角「切近角」cut-away：把 x≥XC 且 y≥YC 那一塊挖掉，露出兩個切面 ——
       y=YC 的 x–z 切面：**交錯指狀電極**（MLCC 唯一的決定性特徵）
       x=XC 的 y–z 切面：**側邊餘白**（電極不到側面，這是第三個方向上的事，純 2D 剖面看不到）
     端電極的四層（Cu／樹脂／Ni／Sn）另外用右下的 2D 放大剖面講，等角圖上只給金屬帶與分層提示。 */
  function mlccStack() {
    const SEG = 'passive_comp';
    // 模型尺寸。真實 EIA 0402 是 1.0 × 0.5 × 約 0.5 mm；高度在畫面上放大過（畫面已標「非實物比例」）
    const L = 252, W = 126, H = 150;
    const XC = 56, YC = 58;          // 切掉的近角
    const COV = 16;                  // 上下保護層（無電極素坯）
    const TW = 42;                   // 端電極帶寬（構圖比例，畫面不標數字：規格書 §6-B4 信心低）
    const EM = 30;                   // 端部餘白：電極不准碰到對面的端電極（碰到＝短路）
    const SM = 11;                   // 側邊餘白：電極不到側面
    const NEL = 16;                  // 畫 16 層（實際 400～1000 層，畫面另外標）
    const PIT = (H - COV * 2) / NEL, ET = 2.2;
    const ez = (i) => COV + i * PIT + (PIT - ET) / 2;   // 第 i 層電極的下緣 z
    const CX = 411, CY = 226;                            // 等角本體在畫面上的原點
    const ax = (x, y) => (CX + (x - y) * IX).toFixed(1);
    const ay = (x, y, z) => (CY + (x + y) * IY - z).toFixed(1);
    const poly = (cls, fill, pts) => `<path class="${cls}" fill="${fill}" d="M${pts.join('L')}Z"/>`;
    // (u,v) 平面上的矩形；onXZ / onYZ 的局部座標裡 y 就是 v（矩陣已經把方向翻好）
    const RV = (u0, v0, u1, v1) => `M${u0},${v0}H${u1}V${v1}H${u0}Z`;

    // ---------------- 切面 B（y = YC 的 x–z 面）：交錯指狀電極
    const uB = L - XC;                       // 196
    const uCap = (L - 18) - XC;              // 178：端電極內側面（陶瓷在這裡讓出位置）
    const uStop = (L - EM) - XC;             // 166：不連到右端的那一組，停在這裡
    const uTerm = (L - TW) - XC;             // 154：端電極帶的起點
    /* B2：電荷疊色只畫 CHG_AT 這幾段，不是 15 段全鋪。
       鋪滿的話那一片青色就等於「有效層區是另一種材質」；只在幾段之間畫，
       讀起來才是「電荷存在相鄰這兩片電極之間」—— 也正是這張圖要講的事。*/
    const CHG_AT = [3, 6, 9, 12];
    const els = [], chg = [];
    for (let i = 0; i < NEL; i++) {
      const v0 = ez(i), u1 = (i % 2) ? uCap : uStop;   // 奇數層連右端電極、偶數層從左端伸進來
      els.push(`<rect x="0" y="${v0.toFixed(1)}" width="${u1}" height="${ET}" fill="var(--dg-el)"/>`);
      if (i < NEL - 1 && CHG_AT.includes(i)) {
        const g0 = v0 + ET, g1 = ez(i + 1);
        chg.push(`<rect class="chg pulse" x="6" y="${g0.toFixed(1)}" width="${uStop - 12}" height="${(g1 - g0).toFixed(1)}" style="animation-delay:${(i * 0.16).toFixed(2)}s"/>`);
      }
    }
    // 端電極斷面：由外到內 Sn → Ni → Cu（車規在右下的放大圖裡才多一層樹脂）
    const termBand = (d, fill) => `<path fill="${fill}" fill-rule="evenodd" d="${RV(uTerm, d, uB - d, H - d)} ${RV(uTerm, COV, uCap, H - COV)}"/>`;
    const faceB = onXZ(XC, YC)
      + `<rect x="0" y="0" width="${uB}" height="${H}" fill="url(#mcCut)"/>`
      + `<rect x="0" y="0" width="${uB}" height="${COV}" fill="url(#mcCov)"/>`
      + `<rect x="0" y="${H - COV}" width="${uB}" height="${COV}" fill="url(#mcCov)"/>`
      + `<path d="M0,${COV}H${uB}M0,${H - COV}H${uB}" stroke="rgba(30,36,50,.5)" stroke-width=".9" fill="none"/>`
      + chg.join('') + els.join('')
      + termBand(0, 'var(--dg-sn)') + termBand(3, 'var(--dg-ni)') + termBand(6.5, 'var(--dg-cu)')
      + `</g>`;

    // ---------------- 切面 A（x = XC 的 y–z 面）：側邊餘白
    const uA = W - YC, uSide = (W - SM) - YC;
    const elsA = [];
    for (let i = 0; i < NEL; i++) elsA.push(`<rect x="0" y="${ez(i).toFixed(1)}" width="${uSide}" height="${ET}" fill="var(--dg-el)"/>`);
    const faceA = onYZ(XC, YC)
      + `<rect x="0" y="0" width="${uA}" height="${H}" fill="url(#mcCutB)"/>`
      + `<rect x="0" y="0" width="${uA}" height="${COV}" fill="url(#mcCovB)"/>`
      + `<rect x="0" y="${H - COV}" width="${uA}" height="${COV}" fill="url(#mcCovB)"/>`
      + elsA.join('')
      + `<path d="M${uSide},${COV + 2}V${H - COV - 2}" stroke="var(--dg-warn)" stroke-width="1.1" stroke-dasharray="3 3" fill="none"/>`
      + `</g>`;

    // ---------------- 外表面
    const topFace = poly('part', 'url(#mcT)', [P3(0, 0, H), P3(L, 0, H), P3(L, YC, H), P3(XC, YC, H), P3(XC, W, H), P3(0, W, H)]);
    const topTermL = poly('', 'url(#mcMetT)', [P3(0, 0, H), P3(TW, 0, H), P3(TW, W, H), P3(0, W, H)]);
    const topTermR = poly('', 'url(#mcMetT)', [P3(L - TW, 0, H), P3(L, 0, H), P3(L, YC, H), P3(L - TW, YC, H)]);
    const rightFace = poly('part', 'url(#mcMetR)', [P3(L, 0, H), P3(L, YC, H), P3(L, YC, 0), P3(L, 0, 0)]);
    const leftCer = poly('part', 'url(#mcL)', [P3(XC, W, H), P3(TW, W, H), P3(TW, W, 0), P3(XC, W, 0)]);
    const leftTerm = poly('part', 'url(#mcMetL)', [P3(TW, W, H), P3(0, W, H), P3(0, W, 0), P3(TW, W, 0)]);
    // 端電極分層提示：兩條細線，遠看就知道那條金屬帶不是一塊實心
    const hint = `<path d="M${P3(L - 3, 0, H)}L${P3(L - 3, YC, H)}M${P3(L - 7, 0, H)}L${P3(L - 7, YC, H)}" stroke="rgba(255,255,255,.35)" stroke-width=".9" fill="none"/>`;

    const iso = `<g data-seg="${SEG}" data-part="mlcc_body" transform="translate(${CX},${CY})">
      ${topFace}${topTermL}${topTermR}${leftCer}${leftTerm}${rightFace}${hint}${faceA}${faceB}</g>`;

    // ---------------- 左欄：尺寸比較尺（1 mm ＝ 110px）
    const chip = (x, w, h) => {
      const t = Math.max(5, w * 0.17);
      return `<g><rect x="${x}" y="${160 - h}" width="${w}" height="${h}" rx="2" fill="url(#mcT)"/>`
        + `<rect x="${x}" y="${160 - h}" width="${t}" height="${h}" rx="1.5" fill="var(--dg-sn)"/>`
        + `<rect x="${x + w - t}" y="${160 - h}" width="${t}" height="${h}" rx="1.5" fill="var(--dg-sn)"/></g>`;
    };

    // ---------------- 右下：端電極 2D 放大剖面（消費級三層 vs 車規四層）
    function endCut(x, auto) {
      /* 端電極的 2D 放大剖面。畫法：由外到內一層一層疊上去（外層最大、內層最小），
         最後把陶瓷本體壓在上面 —— 這樣每一層自然變成一圈「C」，包住端部五個面的一段。
         ★ 厚薄關係是唯一要對的事：Cu 最厚、樹脂次之、Ni／Sn 最薄（規格書 §6-B3，不標數字）。*/
      /* 畫的是**整顆**的縱剖面（兩端都有端子），不是只有一端 ——
         只畫一端的版本測下來會被讀成「螢幕＋底座」，整顆的輪廓才一眼認得出是 MLCC。*/
      const BL = x + 34, BR = x + 258, BT = 566, BB = 654;     // 陶瓷本體
      const WL = x + 96, WR = x + 196;                          // 端子往本體上包到這裡（左／右）
      /* A3（mechanical-engineer 2026-09-21）：**兩顆的 Sn／Ni／Cu 厚度完全一樣**，
         車規靠「端子整體往外長厚」容納中間那層導電樹脂。
         以前消費級的 Ni 被畫成跟 Cu 一樣厚、而且是車規那顆 Ni 的三倍，
         等於畫面在說「兩顆的差別只有多一層樹脂」但 Ni 自己偷偷變三倍 —— 對照就失效了。
         每一列是 [端面向外的偏移 dx, 上包帶頂緣 y0, 下包帶底緣 y1, 顏色]，
         由外到內排；厚度＝相鄰兩列的差（規格書 §6-B3：只表達厚薄關係，不標數字）。
           端面厚度：Sn 4 ／ Ni 4 ／〔樹脂 6〕／ Cu 12（Cu 最厚）
           上下包帶：Sn 3 ／ Ni 3 ／〔樹脂 5〕／ Cu 8 */
      const lay = auto
        ? [[8, 547, 673, 'var(--dg-sn)'], [12, 550, 670, 'var(--dg-ni)'], [16, 553, 667, 'var(--dg-resin)'], [22, 558, 662, 'var(--dg-cu)']]
        : [[14, 552, 668, 'var(--dg-sn)'], [18, 555, 665, 'var(--dg-ni)'], [22, 558, 662, 'var(--dg-cu)']];
      const OUT = lay[0][0];        // 端子最外緣（焊錫圓角要爬到這裡）
      const shells = lay.map(([dx, y0, y1, c]) =>
        `<rect x="${x + dx}" y="${y0}" width="${WL - x - dx}" height="${y1 - y0}" rx="1.5" fill="${c}"/>`
        + `<rect x="${WR}" y="${y0}" width="${x + 292 - dx - WR}" height="${y1 - y0}" rx="1.5" fill="${c}"/>`).join('');
      // 交錯指狀電極：偶數層連左端、奇數層連右端，兩邊都留餘白（碰到對面＝短路）
      const stubs = [574, 586, 598, 610, 622, 634, 646].map((y, i) =>
        `<rect x="${i % 2 ? BL + 30 : BL}" y="${y}" width="${i % 2 ? BR - BL - 30 : BR - BL - 30}" height="3.4" fill="var(--dg-el)"/>`).join('');
      const pcb = `<rect x="${x}" y="684" width="292" height="10" rx="2" fill="var(--dg-pcb)"/>`
        + `<rect x="${x + 2}" y="678" width="100" height="6" rx="1" fill="var(--dg-cu)"/>`
        + `<rect x="${x + 190}" y="678" width="100" height="6" rx="1" fill="var(--dg-cu)"/>`
        + `<path d="M${x + OUT - 8},678 Q${x + OUT - 3},678 ${x + OUT},660 L${x + OUT},678 Z" fill="var(--dg-sn)"/>`
        + `<path d="M${x + 300 - OUT},678 Q${x + 295 - OUT},678 ${x + 292 - OUT},660 L${x + 292 - OUT},678 Z" fill="var(--dg-sn)"/>`;
      /* A2（2026-09-21 重查，信心高 —— 見檔頭的來源註記）：板彎裂是「45° 裂」。
         起點在**安裝面（底面）、端電極內緣**（termination margin 的起點），
         往**外上方 45°** 走，一直走到端電極 —— 也就是往元件外側、不是往中間。
         舊版兩條都畫成由外往內，方向正好相反。
         這裡從 (WL, BB) 走到 (BL, BB−62)：水平 −62、垂直 −62 ＝ 正好 45°，
         終點落在本體端面，也就是被端電極蓋住的那一面。*/
      const crack = auto ? ''
        : `<path d="M${WL},${BB} L${WL - 16},${BB - 16} L${WL - 24},${BB - 22} L${WL - 40},${BB - 40} L${BL},${BB - 62}" stroke="var(--dg-err)" stroke-width="2.2" fill="none"/>`;
      const relief = auto
        ? `<path d="M${x + 19},624 l0,-18 m-3.5,3.5 l3.5,-3.5 l3.5,3.5" stroke="var(--dg-accent)" stroke-width="1.6" fill="none"/>`
        : '';
      return `<g data-seg="${SEG}" data-part="${auto ? 'mlcc_term_auto' : 'mlcc_term_cons'}">
        <text class="hd" x="${x}" y="526">${auto ? '車規：四層（多一層導電樹脂）' : '消費級：三層'}</text>
        ${shells}<rect class="part" x="${BL}" y="${BT}" width="${BR - BL}" height="${BB - BT}" fill="url(#mcT)"/>${stubs}${pcb}${crack}${relief}
        <text class="sub" x="${x}" y="712" ${auto ? '' : 'style="fill:var(--dg-warn)"'}>${auto ? '樹脂層先變形，把應力吃掉' : '陶瓷直接吃到應力 → 板彎裂'}</text></g>`;
    }

    /* A4：圖例的順序必須跟它正上方那句「由內到外 Cu →〔樹脂〕→ Ni → Sn」一致。
       舊版是由外到內（Sn → Ni → 樹脂 → Cu），一張專門防止順序搞混的圖，
       兩個相反的順序並列在同一個畫面上。*/
    const legend = [['var(--dg-cu)', 'Cu 基底層（最內）', '最厚的一層，銅膏沾附後約 800–900 °C 燒附上去'],
      ['var(--dg-resin)', '導電樹脂（軟端子）', '只有車規／高可靠度品才有；抗板彎，ESR 變高'],
      ['var(--dg-ni)', 'Ni 鎳鍍層', '阻障層，擋焊料把底下的銅吃掉'],
      ['var(--dg-sn)', 'Sn 錫鍍層（最外）', '最外一層，讓焊錫吃得上去']]
      .map(([c, t, s], i) => `<g><rect x="640" y="${548 + i * 44}" width="15" height="15" rx="3" fill="${c}"/>`
        + `<text class="lbl" x="664" y="${560 + i * 44}">${t}</text><text class="sub" x="664" y="${578 + i * 44}">${s}</text></g>`).join('');

    /* class 多一個 `dg1`：**這張圖只有一個環節**（整張 14 個 [data-seg] 全是 passive_comp），
       所以點任何零件都會讓全部零件一起 .sel。發光留著就是「整張圖發青光、0 個被 dim」，
       那個狀態不傳達任何資訊，只剩螢光感。`.dg.dg1{--dg-glow:none}` 把它關掉（B1）。*/
    return `<svg class="dg dgm dg1" viewBox="0 0 980 1046" width="100%" style="display:block">${STYLE}
      <defs>
        <linearGradient id="mcT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer)"/><stop offset="1" stop-color="var(--dg-cer-2)"/></linearGradient>
        <linearGradient id="mcL" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#948c7c"/><stop offset="1" stop-color="#7a7263"/></linearGradient>
        <linearGradient id="mcCut" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer-cut)"/><stop offset="1" stop-color="var(--dg-cer-cut-2)"/></linearGradient>
        <linearGradient id="mcCutB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a09884"/><stop offset="1" stop-color="#8a8270"/></linearGradient>
        <linearGradient id="mcCov" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cover)"/><stop offset="1" stop-color="var(--dg-cover-2)"/></linearGradient>
        <linearGradient id="mcCovB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c6bfab"/><stop offset="1" stop-color="#b8b09c"/></linearGradient>
        <linearGradient id="mcMetT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c9cfd5"/><stop offset="1" stop-color="#a8afb6"/></linearGradient>
        <linearGradient id="mcMetR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#aab1b8"/><stop offset="1" stop-color="#858c94"/></linearGradient>
        <linearGradient id="mcMetL" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a6adb4"/><stop offset="1" stop-color="#7f868d"/></linearGradient>
      </defs>
      <text class="ttl" x="16" y="26">MLCC 積層陶瓷電容：層數怎麼變成容值，也怎麼變成成本</text>
      <text class="cap" x="16" y="46">中間是切開近角的本體 —— 右下切面看「交錯指狀電極」，左下切面看「側邊餘白」。右邊逐層說明，下面是端電極四層與製程。</text>

      <!-- 左欄 ① 尺寸代號 -->
      <text class="hd" x="16" y="84">① 尺寸代號有兩套，別記混</text>
      ${chip(22, 110, 55)}${chip(150, 66, 33)}${chip(234, 44, 22)}
      <path d="M22,178V190M132,178V190M22,184H132" stroke="var(--dg-accent)" stroke-width="1" opacity=".55" fill="none"/>
      <text class="num" x="140" y="189">1 mm</text>
      <text class="sub" x="16" y="214">EIA 0402 ＝ 公制 1005 ＝ 1.0 × 0.5 mm</text>
      <text class="sub" x="16" y="232">EIA 0201 ＝ 公制 0603 ＝ 0.6 × 0.3 mm</text>
      <text class="sub" x="16" y="250">EIA 01005 ＝ 公制 0402 ＝ 0.4 × 0.2 mm</text>

      <!-- 左欄 ② 容值公式 -->
      <rect class="frame" x="16" y="266" width="270" height="86" rx="8"/>
      <text class="hd" x="30" y="288">② 容值是層數堆出來的</text>
      <text class="num" x="30" y="310">C ＝ ε₀ · εr × n × A ÷ d</text>
      <text class="sub" x="30" y="328">n＝層數、A＝重疊面積、d＝單層厚度</text>
      <text class="sub" x="30" y="346">n ↑ 或 d ↓ → 容值 ↑，成本與風險也 ↑</text>

      <!-- 左欄 ③ 板彎裂 -->
      <rect class="frame" x="16" y="366" width="270" height="112" rx="8"/>
      <text class="hd" x="30" y="388">③ 板彎裂（flex crack）</text>
      <path d="M32,432 Q151,408 270,432" stroke="var(--dg-pcb)" stroke-width="9" fill="none" stroke-linecap="round"/>
      <rect x="113" y="410" width="30" height="5" rx="1" fill="var(--dg-cu)"/><rect x="161" y="410" width="30" height="5" rx="1" fill="var(--dg-cu)"/>
      <rect x="123" y="394" width="60" height="16" rx="2" fill="url(#mcT)"/>
      <rect x="123" y="394" width="11" height="16" rx="1.5" fill="var(--dg-sn)"/><rect x="172" y="394" width="11" height="16" rx="1.5" fill="var(--dg-sn)"/>
      <!-- A2：45° 裂。起點在安裝面（底面）的端電極內緣 x=134，往「外」上方 45° 走到端電極 x=123 -->
      <path d="M134,410 L129,405 L127,404 L123,399" stroke="var(--dg-err)" stroke-width="1.8" fill="none"/>
      <!-- A1：三點彎。板子中間上凸（元件在凸面＝受拉面，陶瓷怕拉不怕壓），
           所以受力一定是「兩端往下、中央往上」。舊版兩端朝上＝只會讓中間下凹，跟畫出來的變形相反。 -->
      <path d="M40,437 l0,9 m-3.5,-3.5 l3.5,3.5 l3.5,-3.5M262,437 l0,9 m-3.5,-3.5 l3.5,3.5 l3.5,-3.5" stroke="var(--dg-ink-3)" stroke-width="1.2" fill="none"/>
      <path d="M151,446 l0,-14 m-4,4.5 l4,-4.5 l4,4.5" stroke="var(--dg-ink-3)" stroke-width="1.4" fill="none"/>
      <text class="sub" x="30" y="462">板子受力 → 應力傳到陶瓷本體 → 裂</text>
      <text class="sub" x="30" y="476">車規靠軟端子（導電樹脂）擋這一刀</text>

      <!-- 中：等角切開本體 -->
      ${iso}
      <!-- A6（規格書 §6-C）：省略記號要畫在條紋區**中間**，不是只寫在最底下的文字裡。
           座標是切面 B 上 (u≈85, v≈75) 換算回畫面的位置：x = 409.3 + 0.866u、y = 283 + 0.5u − v。 -->
      <g pointer-events="none">
        <rect x="462" y="232" width="44" height="36" rx="5" fill="url(#mcCov)" stroke="var(--dg-el)" stroke-width="1"/>
        <text class="num" x="484" y="250" text-anchor="middle" style="fill:var(--dg-el);font-weight:700">⋮</text>
        <text class="num" x="484" y="264" text-anchor="middle" style="fill:var(--dg-el);font-weight:700">×N</text>
      </g>

      <!-- 右：說明欄（引線接回零件） -->
      ${labelRow(SEG, 654, 110, '保護層（無電極素坯）', '上下各一疊，不貢獻容值', ax(120, 58), ay(120, 58, 150), 312)}
      ${labelRow(SEG, 654, 164, '介電陶瓷層（鈦酸鋇 BaTiO₃）', '單層 0.5–2 µm；越薄，容值越大', ax(170, 58), ay(170, 58, 118), 312)}
      ${labelRow(SEG, 654, 218, '內部電極（鎳 Ni，BME）', '約 0.5 µm；兩把梳子互插但不相碰', ax(190, 58), ay(190, 58, 88), 312)}
      ${labelRow(SEG, 654, 272, '有效層＝容值的來源', '相鄰兩層重疊的那一塊才算數', ax(150, 58), ay(150, 58, 45), 312)}
      ${labelRow(SEG, 654, 326, '側邊餘白（不產生電容）', '電極不到側面，避免短路', ax(56, 115), ay(56, 115, 20), 312)}
      ${labelRow(SEG, 654, 380, '端電極（包住端部五個面）', '由內到外 Cu → Ni → Sn，兩端對稱', ax(252, 58), ay(252, 58, 40), 312)}
      <text class="sub" x="654" y="434" style="fill:var(--dg-warn)">★ 相鄰兩層電極必定來自相反的兩端，</text>
      <text class="sub" x="654" y="452" style="fill:var(--dg-warn)">　 而且都不碰到對面的端電極 —— 碰到就是短路。</text>

      <!-- 下一段：端電極 2D 放大剖面 -->
      <text class="hd" x="16" y="502">端電極：由內到外 Cu →〔導電樹脂〕→ Ni → Sn，順序不准對調</text>
      ${endCut(16, false)}${endCut(324, true)}
      <text class="hd" x="640" y="526">四層各自在幹嘛（由內到外）</text>
      ${legend}
      <text class="sub" x="16" y="738" style="fill:var(--dg-warn)">★ 把 Ni 畫在 Sn 外面是最常見的錯；樹脂層是夾在 Cu 與 Ni 之間，不是最外層。</text>

      <!-- 製程 -->
      <text class="cap" x="16" y="764">製造流程（十道併成五格）　★ 燒結一定在端電極之前 —— 反過來端電極會先被燒掉</text>
      ${processBar(16, 772, [{ seg: SEG, t: '流延成膜', s: '陶瓷漿料刮成生胚膜' },
    { seg: SEG, t: '網印 ＋ 疊層', s: '交替方向印 Ni 電極' },
    { seg: SEG, t: '加壓 ＋ 切割', s: '壓實後切成單顆' },
    { seg: SEG, t: '排膠 ＋ 燒結', s: '還原氣氛高溫燒結' },
    { seg: SEG, t: '端電極 ＋ 電鍍', s: '800–900 °C 燒附 ＋ 電鍍' }], 184)}

      <!-- 兩個結論 -->
      <rect class="frame" x="16" y="818" width="476" height="140" rx="8"/>
      <text class="hd" x="30" y="840">為什麼疊越多層越貴</text>
      <text class="sub" x="30" y="862">容值 ∝ 層數 ÷ 單層厚度 → 要大容值只有</text>
      <text class="sub" x="30" y="880">兩條路：疊更多層，或把每層做更薄。</text>
      <text class="sub" x="30" y="898">每多一層就多一次網印與疊層，而整顆良率</text>
      <text class="sub" x="30" y="916">是每層良率的連乘 —— 層數越多越陡。</text>
      <text class="sub" x="30" y="934">層變薄 → 粉體要更細、絕緣裕度變小；燒結</text>
      <text class="sub" x="30" y="952">時電極與陶瓷收縮不匹配，容易分層與裂。</text>
      <path class="axis" d="M330,852V936H474"/>
      <path d="M330,858 C362,861 388,872 408,890 S446,924 472,933" stroke="var(--dg-accent)" stroke-width="2" fill="none" opacity=".85"/>
      <text class="sub" x="330" y="850">整顆良率</text><text class="sub" x="404" y="950">層數 →</text>
      <rect class="frame" x="508" y="818" width="458" height="140" rx="8"/>
      <text class="hd" x="522" y="840">車規為什麼難做</text>
      <text class="sub" x="522" y="862">溫度等級（例如 X8R 到 150 °C）要換一套配方，</text>
      <text class="sub" x="522" y="880">不是同一顆貼個標籤。</text>
      <text class="sub" x="522" y="898">車子的板子會彎 → 要加導電樹脂層（軟端子），</text>
      <text class="sub" x="522" y="916">多一道製程，而且 ESR 變高。</text>
      <text class="sub" x="522" y="934">AEC-Q200 全項（含基板彎曲）＋ 零缺陷框架；</text>
      <text class="sub" x="522" y="952">認證與換料時程長，產能一綁就難轉。</text>

      <text class="cap" x="16" y="982">2026 產業變數：村田對部分消費級 GRM／GRJ 與車規 GCM／GCJ／GCG 料號發出 EOL（最後下單 2028/3、最後出貨 2029/3），規格替代與轉單是這一格現在的故事。</text>
      <text class="cap" x="16" y="1002">示意圖，非實物比例｜層數與各層厚度均為示意：圖上畫 16 層電極（⋮ ×N），實際高容量品 400～1000 層以上；介電 0.5–2 µm、內電極約 0.5 µm。</text>
      <!-- A5-a（mechanical-engineer 2026-09-21 複驗）：把「這張圖對應到誰」講清楚。
           零件掛的是 supply_chain.yaml 的 passive_comp 環節，但那一格的名字是
           「被動元件 MLCC／**電阻**」—— 成分跟「被動元件 MLCC」族群不是同一份名單。
           不寫出來的話，讀者會把畫面上出現的每一檔都讀成「這家做 MLCC」。
           ⚠ 這兩行是照 **2026-09-21 更新過的 YAML** 寫的，跟審查意見當時的版本不同：
             · 環節已經補進 3026 禾伸堂與 6173 信昌電（原本漏掉，那才是真正的錯）
             · 凱美的舊 note「主體是鋁質電解電容」已經作廢 —— 更正後的說法是
               晶片電阻約佔其營收 49%，它是**用電阻**進到這一格的，不做 MLCC
           YAML 一行都沒動（成分是 Andy 校訂的，AGENTS §5），這裡只把落差寫在畫面上。 -->
      <text class="cap" x="16" y="1020">零件顏色＝環節色。點零件篩的是「被動元件 MLCC／電阻」這一格：2327 國巨／2492 華新科／2375 凱美／3026 禾伸堂／6173 信昌電。</text>
      <text class="cap" x="16" y="1038">這一格含晶片電阻 —— 凱美是以電阻進到這一格、不做 MLCC；做 MLCC 的是 2327／2492／3026／6173。資料來源與信心度見 docs/diagram_specs/mlcc_stack.md。</text>
    </svg>`;
  }

  /* ================================================================ 剖析圖的掛點（slot）
     2026-09-21 改：以前是「一條產業鏈一張圖」（`window.Diagrams[<chain id>]`），
     所以五張已經寫好的規格書一張都畫不出來 —— 它們畫的全是**族群層級**的東西
     （MLCC／面板／網通板卡在 electronics，輕油裂解在 traditional，變壓器 GIS 在 infrastructure），
     而 electronics 一條鏈就要掛三張、traditional 更是塑化與生技觀光共用一個位子。
     現在：**key 可以是族群 id，也可以是產業鏈 id。**
       查找順序＝ 族群專屬圖 → 這條鏈的預設圖 → 都沒有就不畫。
     `scene` 是對應的 Three.js 場景 id（site/three3d.js 的 SCENES），沒有就是沒有 3D。*/
  const SLOTS = {
    /* ★ 2026-09-21 art-director 獨立量測：這兩張舊圖在**任何寬度都不合格**，
       連 1440 全寬都還沒到 12px（半導體 10.47px、AI 伺服器 11.57px），
       900px 螢幕上只剩 6.26px / 6.92px。Andy 已經講過三次「文字太小」。
       根因和 MLCC 那張完全一樣：產業鏈頁右邊有側欄，欄寬永遠遠小於螢幕寬，
       viewBox 1220 被壓成 ×0.659 —— **字級怎麼調都沒用**。
       這裡先補上 native（一行、不動任何幾何、零回歸風險），
       900px 的縮放從 ×0.659 拉回 ×1.0，最小字級 6.26 → 9.5px。
       ⚠ 還沒到 12px：那要把兩張掛上 .dgm 並**重排版面**（字級一升，labelRow 與
       processBar 的行距會擠在一起），那是另外一批、自己一個 commit，不跟新圖綁在一起。*/
    semiconductor: { level: 'chain', chain: 'semiconductor', name: '半導體：CoWoS 2.5D 封裝剖面', draw: semiconductor, scene: 'semiconductor', native: 1220 },
    ai_server: { level: 'chain', chain: 'ai_server', name: 'AI 伺服器：機櫃與運算托盤', draw: aiServer, scene: 'ai_server', native: 1220 },
    mlcc: { level: 'group', chain: 'electronics', name: '被動元件：MLCC 疊層剖析', draw: mlccStack, scene: 'mlcc', native: 980 },
  };
  const isGroupSlot = (id) => !!(SLOTS[id] && SLOTS[id].level === 'group');
  const isChainSlot = (id) => !!(SLOTS[id] && SLOTS[id].level === 'chain');
  window.DiagramSlots = {
    /* 這一頁現在該畫哪一張？回傳 slot id 或 null。
       groupId 傳進來的是「使用者選到的族群」；沒選就傳 null。*/
    pick(chainId, groupId) {
      if (groupId && isGroupSlot(groupId) && SLOTS[groupId].chain === chainId) return groupId;
      if (chainId && isChainSlot(chainId)) return chainId;
      return null;
    },
    // 這條鏈上有專屬圖的族群（順序不保證，呼叫端自己照成交值排）
    groupsOf(chainId) { return Object.keys(SLOTS).filter(k => isGroupSlot(k) && SLOTS[k].chain === chainId); },
    // 這條鏈「有可能」畫得出圖嗎（鏈層級或任何一個族群層級）—— 上方切換列的小標記用
    anyIn(chainId) { return isChainSlot(chainId) || this.groupsOf(chainId).length > 0; },
    chainDefault(chainId) { return isChainSlot(chainId) ? chainId : null; },
    // 目前有鏈層級圖的鏈（跨鏈面板的縮圖用；以前寫死成 DG_CHAINS）
    chains() { return Object.keys(SLOTS).filter(isChainSlot); },
    draw(id) { return SLOTS[id] ? SLOTS[id].draw() : ''; },
    name(id) { return SLOTS[id] ? SLOTS[id].name : ''; },
    scene(id) { return SLOTS[id] ? (SLOTS[id].scene || null) : null; },
    /* native＝這張圖要用「原尺寸」畫，不准被欄寬壓縮（回傳最小寬度 px，0＝沒宣告）。
       為什麼要有這個：產業鏈頁的 main 只有 1080px（右邊有側欄），1100px 的螢幕更只剩 740，
       量出來 1440→984px(×0.81)、1100→644px(×0.53)、900→444px(×0.36)——
       12px 的字會被壓成 6.3px 甚至 4.4px。這正是 Andy 一直在講的「文字太小」。
       宣告 native 的圖改成「維持原尺寸、欄位不夠寬就左右滑」，字級才守得住。*/
    native(id) { return SLOTS[id] ? (SLOTS[id].native || 0) : 0; },
    has(id) { return !!SLOTS[id]; },
  };
  /* 舊介面留著（`window.Diagrams[<id>]()`）—— 題材圖與驗收腳本還在用。
     新的查找一律走 window.DiagramSlots，不要在別的地方再維護第二份名單。*/
  window.Diagrams = Object.keys(SLOTS).reduce((o, k) => (o[k] = SLOTS[k].draw, o), {});
  // 題材產品圖（site/themes3d.js）共用同一套樣式與 3D 工具，兩邊看起來才是同一套產品圖
  window.DG = { STYLE, labelRow, lrow3, processBar, chainLink, IX, IY, px, py, P3, onTop, onXZ, onYZ, box, cyl, panel, wire, floor, cells, p3 };
})();
