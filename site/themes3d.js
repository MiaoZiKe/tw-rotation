/* 題材產品圖：每個題材一張「上游 → 中游 → 下游」的等角 3D 供應鏈剖析圖。
   版面參考 Andy 2026-09-12 給的三張圖（光通訊供應鏈剖析／PCB 是什麼／伺服器爆炸圖）：
     一排 3D 物件由左到右說故事，物件之間用流動的彩帶接起來，
     每個物件正下方直接寫標題＋兩行說明＋該環節的台股（代號直接可點），
     最下面一條編號製程／產業鏈流程。
   共用 site/diagrams.js 的 window.DG 3D 工具箱，所以題材圖跟產業鏈剖析圖是同一套立體語言。
   每個站點帶 data-part（點了列出對應個股）與 data-seg（跟供應鏈環節同色），
   顏色由 app.js 注入 --c（DECISIONS #48），所以「點成員 → 圖上同色亮起」全站一致。 */
(function () {
  'use strict';
  const D = window.DG; if (!D) return;
  const { STYLE, px, py, onTop, box, cyl, panel, wire, cells } = D;

  const CW = 1180, PADX = 22, GAPX = 12;
  const ART_Y = 214;          // 3D 物件站的地面線
  const BAND_Y = 76;          // 上游／中游／下游 標題列
  const CAP_Y = 256;          // 站點標題
  const CHIP_Y = 300;         // 個股標籤起點
  const BANDS = ['上游：關鍵材料與設備', '中游：核心元件與製造', '下游：系統、模組與應用'];
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ---------------------------------------------------------------- 個股標籤（直接可點）
  const nameOf = (c) => (window.Link && window.Link.cname[c]) || '';
  /* ★ 2026-09-21 art-director：晶片上的字從 11.5px 升到 12px（--dg-fs-min，字級下限）。
     字一長，**盒子與列距一定要跟著長**，不然就是 processBar 那個老毛病重演一次 ——
     所以這三個數字（估寬的 11.5、盒高 19、列距 23）是同一組，不准只改其中一個。
     估寬用 12.5/字：中文字在 12px 下大約就是 12px 寬，多的 0.5 是安全邊。*/
  const CHIP_H = 21, CHIP_ROW = 25;
  function chips(codes, x, y, maxW) {
    let cx = x, cy = y, out = '';
    (codes || []).forEach(code => {
      const nm = nameOf(code), t = nm ? code + ' ' + nm : code;
      const w = Math.round(32 + (nm ? nm.length * 12.5 : 0) + 12);
      if (cx > x && cx + w > x + maxW) { cx = x; cy += CHIP_ROW; }
      out += `<g class="scode" data-code="${code}"><rect x="${cx}" y="${cy}" width="${w}" height="${CHIP_H}" rx="5"/>`
        + `<text x="${cx + 7}" y="${cy + 14.8}">${esc(t)}</text></g>`;
      cx += w + 6;
    });
    return { svg: out, rows: Math.round((cy - y) / CHIP_ROW) + 1 };
  }

  // ---------------------------------------------------------------- 場景外框
  function chainScene(o) {
    const st = o.stations, n = st.length;
    const W = Math.floor((CW - PADX * 2 - GAPX * (n - 1)) / n);
    const slot = (i) => PADX + i * (W + GAPX);
    let maxRows = 1;
    const body = st.map((s, i) => {
      const x = slot(i), cx = x + W / 2;
      const ch = chips(s.codes, x, CHIP_Y, W); maxRows = Math.max(maxRows, ch.rows);
      const sub = (s.sub || []).map((t, j) => `<text class="sub" x="${x}" y="${CAP_Y + 19 + j * 17}">${esc(t)}</text>`).join('');
      return `<g class="p3 stn" data-part="${s.id}" data-codes="${(s.codes || []).join(',')}"${s.seg ? ` data-seg="${s.seg}"` : ''}>
        <rect class="slot" x="${x - 7}" y="${BAND_Y + 16}" width="${W + 14}" height="${CHIP_Y - BAND_Y - 12 + ch.rows * CHIP_ROW}" rx="10"/>
        <g transform="translate(${cx},${ART_Y}) scale(${s.k || 1})">${s.art()}</g>
        <text class="lbl" x="${x}" y="${CAP_Y}">${esc(s.label)}</text>${sub}${ch.svg}</g>`;
    }).join('');
    // 物件之間的流動彩帶（參考光通訊那張圖的「上游流到下游」）
    const ribbon = st.slice(0, -1).map((s, i) => {
      const a = slot(i) + W - 4, b = slot(i + 1) + 4, m = (a + b) / 2;
      const d = `M${a},${ART_Y - 40} C${m},${ART_Y - 40} ${m},${ART_Y - 62} ${b},${ART_Y - 62}`;
      return `<path class="rib bg" d="${d}" fill="none"/><path class="rib flow" d="${d}" fill="none"/>`;
    }).join('');
    const bands = [0, 1, 2].map(b => {
      const idx = st.map((s, i) => (s.band === b ? i : -1)).filter(i => i >= 0);
      if (!idx.length) return '';
      const x = slot(idx[0]) - 7, w = slot(idx[idx.length - 1]) + W + 7 - x;
      return `<g class="band b${b}"><rect x="${x}" y="${BAND_Y - 19}" width="${w}" height="26" rx="7"/>
        <text x="${x + 13}" y="${BAND_Y - 1}">${BANDS[b]}</text></g>`;
    }).join('');
    const sy = CHIP_Y + maxRows * CHIP_ROW + 30;
    const H = sy + 82;
    const steps = (o.steps || []).length;
    const sw = steps ? Math.floor((CW - PADX * 2 - 10 * (steps - 1)) / steps) : 0;
    const strip = (o.steps || []).map((s, i) => {
      const x = PADX + i * (sw + 10);
      return `<g class="p3 step" data-part="${s.p || ''}"><rect class="part f2" x="${x}" y="${sy}" width="${sw}" height="40" rx="8"/>
        <circle class="num" cx="${x + 18}" cy="${sy + 20}" r="10.5"/><text class="nn" x="${x + 18}" y="${sy + 24.5}" text-anchor="middle">${i + 1}</text>
        <text class="lbl" x="${x + 36}" y="${sy + 16}">${esc(s.t)}</text>
        <text class="sub" x="${x + 36}" y="${sy + 32}">${esc(s.s || '')}</text></g>`
        + (i < steps - 1 ? `<path class="flow fast" d="M${x + sw},${sy + 20} L${x + sw + 10},${sy + 20}" stroke="#3ee0ff" stroke-width="2"/>` : '');
    }).join('');
    return `<svg class="dg dg3" viewBox="0 0 ${CW} ${H}" width="100%" style="display:block">${STYLE}
      <text class="ttl" x="${PADX}" y="26">${esc(o.title)}</text>
      <text class="cap" x="${PADX}" y="46">${esc(o.cap)}</text>
      ${bands}${ribbon}${body}
      <text class="cap" x="${PADX}" y="${sy - 9}">${esc(o.flowTitle || '產業鏈流程（點一格＝點上面那個環節）')}</text>${strip}
      <text class="cap" x="${PADX}" y="${H - 12}">原創等角示意圖，非實物比例；每個環節的顏色＝族群色，點環節或點代號都會進個股頁</text>
    </svg>`;
  }
  const S = (id, band, label, sub, codes, seg, art, k) => ({ id, band, label, sub, codes, seg, art, k });

  /* ---------------------------------------------------------------- 爆炸圖（拆解圖）
     參考 Andy 給的華南投顧「機架式伺服器機構爆炸圖」：把一台機器由上而下拉開，
     每一層用引線拉到右邊標註「這一層是什麼、誰在做」。
     組裝型的題材（伺服器、電源、散熱、AI PC、機器人、車、衛星、無人機）用這個版面，
     材料型的（PCB/CCL、HBM、CoWoS、玻璃基板）維持 chainScene 的分層剖面。
     station 的資料結構與 chainScene 完全一樣，所以點擊、顏色、成員連動都共用同一套。 */
  const EX = { X: 306, TOP: 150, ROW: 124, LX: 628, LW: 530, K: 1.5 };

  /* ★ 2026-09-23：版面參數改成「每張圖可以自己覆寫」（o.ex）。
     為什麼不直接改 EX：這一輪只做 AI 伺服器那一張，其餘七張爆炸圖（電源、散熱、AI PC、
     機器人、無人機、衛星、車用）**必須維持原樣**，所以覆寫值只由 T.ai_server 傳進來，
     沒傳的圖吃的還是原本那組數字，版面一個像素都不會動。
       MW／MH   零件框的寬高（fit() 會把零件等比縮進這個框）。
                等角投影下一個扁平物件的寬高比上限是 0.866/0.5＝1.73，
                所以 MW/MH 設到 1.73 附近才不會「框很寬、零件只佔一半」。
       SLOT_MIN 右側說明卡的最小高度。設了之後卡片等高、上下貼齊，
                不會像改版前那樣每張卡之間留一條空白。*/
  function explodeScene(o) {
    const E = Object.assign({}, EX, o.ex || {});
    /* ★ 畫布寬度可以自己決定。量出來的事實（2026-09-23）：1440 螢幕上題材頁放圖的那一欄
       只有 996px，而預設畫布是 1180px —— 也就是**這張圖在 Andy 的螢幕上永遠要左右滑**，
       而 Andy 這一輪要的就是「只需要提供圖片給讀者閱讀」。所以 AI 伺服器這張把畫布收到 980，
       1440 下一次看完、不必滑。其他圖沒傳 cw，吃的還是 1180，版面不動。*/
    const W = o.cw || CW;
    const MW = E.MW || 196, MH = E.MH || (E.ROW - 26);
    // 引線起點：有覆寫 MW 的圖貼著零件框右緣算；沒覆寫的維持原本寫死的 +152（其他圖的引線不能位移）
    const AX = E.MW ? Math.round(E.X + MW / 2 + 12) : E.X + 152;
    const ly = o.layers, n = ly.length;
    const rowY = (i) => E.TOP + i * E.ROW;
    let maxRows = 1;
    // 零件之間的虛線對位軸＋箭頭：爆炸圖的關鍵視覺提示「這些是同一台拆開的」
    const guides = ly.slice(0, -1).map((s, i) => {
      /* 對位軸的起訖點：有覆寫 MH 的圖照零件實際佔的高度算（不然箭頭會插進下一個零件裡），
         沒覆寫的圖維持原本寫死的 +26 / −44 —— 其他七張爆炸圖的虛線位置一格都不能動。*/
      const a = E.MH ? rowY(i) - 22 + MH / 2 + 6 : rowY(i) + 26;
      const b = E.MH ? rowY(i + 1) - 22 - MH / 2 - 10 : rowY(i + 1) - 44;
      if (b - a < 12) return '';
      return `<path class="etch" d="M${E.X},${a} V${b}" stroke-dasharray="4 7"/>`
        + `<path class="etch" d="M${E.X - 5},${b - 9} L${E.X},${b} L${E.X + 5},${b - 9}" fill="none"/>`;
    }).join('');
    const rows = ly.map((s, i) => {
      const y = rowY(i);
      // 說明行數不一樣，標籤的起點就要跟著讓；沒覆寫的圖維持原本的 +18（其他七張爆炸圖不受影響）
      const ch = chips(s.codes, E.LX, y + (E.CHIP_DY == null ? 18 : E.CHIP_DY), E.LW - 10);
      maxRows = Math.max(maxRows, ch.rows);
      const sub = (s.sub || []).map((t, j) =>
        `<text class="sub" x="${E.LX}" y="${y - 6 + j * 17}">${esc(t)}</text>`).join('');
      // 引線：從零件右緣往右拉一段、折一次、接到標註區
      const d = `M${AX},${y - 12} H${E.LX - 66} L${E.LX - 34},${y - 26} H${E.LX - 8}`;
      const slotH = Math.max(52 + (s.sub || []).length * 17 + ch.rows * CHIP_ROW, E.SLOT_MIN || 0);
      return `<g class="p3 stn ex" data-part="${s.id}" data-codes="${(s.codes || []).join(',')}"${s.seg ? ` data-seg="${s.seg}"` : ''}>
        <rect class="slot" x="${E.LX - 14}" y="${y - 46}" width="${E.LW + 14}" height="${slotH}" rx="9"/>
        <g class="art" data-cx="${E.X}" data-cy="${y - 22}" data-mh="${MH}" data-mw="${MW}"
           transform="translate(${E.X},${y}) scale(${(s.k || 1) * E.K})">${s.art()}</g>
        <path class="leader" d="${d}"/><circle class="lit" cx="${AX}" cy="${y - 12}" r="3.2"/>
        <text class="lbl" x="${E.LX}" y="${y - 26}">${esc(s.label)}</text>
        <text class="tag" x="${E.LX + 10 + esc(s.label).length * 13}" y="${y - 26}">${BAND_TAG[s.band] || ''}</text>
        ${sub}${ch.svg}</g>`;
    }).join('');
    const sy = rowY(n - 1) + Math.max(34 + maxRows * CHIP_ROW + 22, E.SLOT_MIN ? E.SLOT_MIN - 20 : 0);
    const H = sy + 82;
    const steps = (o.steps || []).length;
    const sw = steps ? Math.floor((W - PADX * 2 - 10 * (steps - 1)) / steps) : 0;
    const strip = (o.steps || []).map((s, i) => {
      const x = PADX + i * (sw + 10);
      return `<g class="p3 step" data-part="${s.p || ''}"><rect class="part f2" x="${x}" y="${sy}" width="${sw}" height="40" rx="8"/>
        <circle class="num" cx="${x + 18}" cy="${sy + 20}" r="10.5"/><text class="nn" x="${x + 18}" y="${sy + 24.5}" text-anchor="middle">${i + 1}</text>
        <text class="lbl" x="${x + 36}" y="${sy + 16}">${esc(s.t)}</text>
        <text class="sub" x="${x + 36}" y="${sy + 32}">${esc(s.s || '')}</text></g>`
        // ⚠ 這個 #3ee0ff 是舊的寫死色碼（淺色主題下會過亮）。這一輪只做 AI 伺服器那一張，
        // 動它會一起改到其他七張爆炸圖，所以留給「全部題材那一輪」跟零件庫裡另外 12 個一起換掉。
        + (i < steps - 1 ? `<path class="flow fast" d="M${x + sw},${sy + 20} L${x + sw + 10},${sy + 20}" stroke="#3ee0ff" stroke-width="2"/>` : '');
    }).join('');
    const axis = `<text class="cap" x="${PADX}" y="${E.UNIT_Y || (E.TOP - 58)}">${esc(o.unit || '整機爆炸拆解（由上而下）')}</text>` + guides;
    return `<svg class="dg dg3" data-cw="${W}" viewBox="0 0 ${W} ${H}" width="100%" style="display:block">${STYLE}${o.style || ''}
      <text class="ttl" x="${PADX}" y="26">${esc(o.title)}</text>
      <text class="cap" x="${PADX}" y="46">${esc(o.cap)}</text>
      ${axis}${rows}
      <text class="cap" x="${PADX}" y="${sy - 9}">${esc(o.flowTitle || '組裝流程（點一格＝點上面那一層）')}</text>${strip}
      <text class="cap" x="${PADX}" y="${H - 12}">原創等角爆炸示意圖，非實物比例；每一層的顏色＝族群色，點層或點代號都會進個股頁</text>
    </svg>`;
  }
  const BAND_TAG = ['上游', '中游', '下游'];

  /* ================================================================ 3D 物件庫
     每個物件都畫在模型原點附近（約 ±50），放進站點時再平移縮放，
     十八張圖共用同一批零件，立體角度、光影與厚度才會一致。 */
  const grid2 = (x, y, w, d, n, m) => { const a = []; for (let i = 1; i < n; i++) a.push(`M${x + w * i / n},${y} V${y + d}`); for (let j = 1; j < m; j++) a.push(`M${x},${y + d * j / m} H${x + w}`); return `<path class="etch" d="${a.join(' ')}"/>`; };
  const holes = (x, y, w, d, n, m, r) => { const a = []; for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) a.push(`<circle class="etch" cx="${(x + w * (i + .5) / n).toFixed(1)}" cy="${(y + d * (j + .5) / m).toFixed(1)}" r="${r || 2.4}"/>`); return a.join(''); };
  const trace = (x, y, w, d, n) => { const a = []; for (let j = 0; j < n; j++) { const yy = y + d * (j + .5) / n; a.push(`M${x + 5},${yy} H${x + w * .45} M${x + w * .55},${yy} H${x + w - 5}`); } return `<path class="etch" d="${a.join(' ')}" stroke-dasharray="6 4"/>`; };
  const blades = (r, n) => { const a = []; n = n || 7; for (let i = 0; i < n; i++) { const t = i * 2 * Math.PI / n; a.push(`M0,0 q${(Math.cos(t) * r * .8).toFixed(1)},${(Math.sin(t) * r * .8).toFixed(1)} ${(Math.cos(t + .5) * r).toFixed(1)},${(Math.sin(t + .5) * r).toFixed(1)}`); } return `<path class="etch spin" d="${a.join(' ')}"/>`; };
  const pad = (w, d) => onTop(0, `<ellipse class="shadow" cx="0" cy="0" rx="${w}" ry="${d}"/>`);

  // 晶格（磊晶材料、玻纖、樹脂這類原材料）
  function vLattice() {
    const P = []; for (const x of [-24, 24]) for (const y of [-24, 24]) for (const z of [8, 56]) P.push([x, y, z]);
    let e = '';
    P.forEach((a, i) => P.forEach((b, j) => { if (j <= i) return; if (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) === 48) e += wire([a, b], 'etch', '', 1.4); }));
    const nodes = P.concat([[0, 0, 32]]).map(p => `<circle class="lit" cx="${px(p[0], p[1]).toFixed(1)}" cy="${py(p[0], p[1], p[2]).toFixed(1)}" r="5"/>`).join('');
    return pad(44, 26) + e + nodes;
  }
  // 晶圓
  function vWafer() {
    const d = []; for (let x = -34; x <= 24; x += 13) for (let y = -34; y <= 24; y += 13) if ((x + 5) * (x + 5) + (y + 5) * (y + 5) < 1000) d.push(`<rect class="lit pulse" x="${x}" y="${y}" width="11" height="11" rx="1" style="animation-delay:${(((x + y) / 13 % 5) + 5) * .22}s"/>`);
    return pad(46, 28) + cyl(0, 0, 0, 38, 9, d.join(''));
  }
  // 晶片封裝（上面一顆小 die）
  function vChip() {
    return pad(46, 28) + box(-36, -32, 0, 72, 64, 11, trace(-36, -32, 72, 64, 4))
      + box(-20, -18, 11, 40, 36, 9, cells(-20, -18, 40, 36, 3, 3))
      + [-24, 4].map(y => box(-42, y, 2, 6, 20, 5) + box(36, y, 2, 6, 20, 5)).join('');
  }
  // 分層堆疊（HBM、CCL 壓合、封裝疊層）
  function vStack(n, h) {
    n = n || 5; h = h || 8;
    let s = pad(44, 27);
    for (let i = 0; i < n; i++) s += box(-32 + i * 1.5, -26 + i * 1.5, i * (h + 2.5), 64 - i * 3, 52 - i * 3, h, i === n - 1 ? grid2(-32 + i * 1.5, -26 + i * 1.5, 64 - i * 3, 52 - i * 3, 4, 3) : '');
    s += [-18, 0, 18].map(x => wire([[x, 0, 2], [x, 0, n * (h + 2.5)]], 'flow slow', 'rgba(255,255,255,.4)', 1.2)).join('');
    return s;
  }
  // 模組／收發器（前面板帶埠）
  function vModule() {
    return pad(48, 26) + box(-44, -20, 0, 88, 40, 24, grid2(-44, -20, 88, 40, 4, 2))
      + [0, 1, 2].map(i => box(44, -14 + i * 10, 5, 7, 7, 12)).join('')
      + [0, 1, 2].map(i => wire([[51, -10 + i * 10, 11], [78, -10 + i * 10, 11]], 'flow fast', '#3ee0ff', 1.4)).join('');
  }
  // 主機板
  function vBoard() {
    return pad(50, 30) + box(-46, -36, 0, 92, 72, 8, trace(-46, -36, 92, 72, 5))
      + box(-20, -14, 8, 34, 30, 9, cells(-20, -14, 34, 30, 3, 3))
      + box(16, -30, 8, 22, 18, 6) + box(16, 4, 8, 22, 18, 6) + box(-42, -30, 8, 16, 54, 5, grid2(-42, -30, 16, 54, 1, 4));
  }
  // 機櫃
  function vRack() {
    let t = pad(32, 22) + box(-24, -22, 0, 48, 44, 108, '');
    for (let i = 0; i < 7; i++) t += box(-20, -26, 8 + i * 14, 40, 4, 10, '') + `<g class="blink b${i % 3 + 1}">${wire([[-16, -26, 13 + i * 14], [8, -26, 13 + i * 14]], '', 'rgba(62,224,255,.85)', 1.6)}</g>`;
    return t;
  }
  // 機台（設備、CDU、配電盤）
  function vMachine() {
    return pad(34, 22) + box(-26, -24, 0, 52, 48, 62, grid2(-26, -24, 52, 48, 2, 3))
      + box(-16, -14, 62, 32, 28, 14, cells(-16, -14, 32, 28, 2, 2))
      + wire([[-26, 24, 20], [-52, 24, 20]], 'flow', '#ffb454', 2);
  }
  const vMotor = () => pad(28, 18) + cyl(0, 0, 0, 22, 42, blades(18, 9)) + box(-8, -8, -6, 16, 16, 6);
  const vCoil = () => pad(30, 19) + cyl(0, 0, 0, 24, 30, `<circle class="etch" r="15"/><circle class="etch" r="8"/>`)
    + [0, 1, 2].map(i => wire([[24, 0, 22 - i * 7], [60, -16, 26 - i * 7]], 'flow slow', '#ffb454', 1.8)).join('');
  const vPanel = () => pad(40, 24) + box(-14, -12, 0, 28, 24, 6) + panel(-38, -3, 6, 76, 54, 5, grid2(0, 0, 76, 54, 6, 4));
  const vPhone = () => pad(26, 32) + box(-18, -38, 0, 36, 76, 5, '') + box(-16, -36, 5, 32, 72, 4, grid2(-16, -36, 32, 72, 2, 5))
    + box(-13, -33, 9, 26, 66, 3, '') + cyl(8, -28, 12, 5, 3, `<circle class="lit" r="3"/>`);
  const vLaptop = () => pad(42, 26) + box(-38, -26, 0, 76, 52, 6, grid2(-38, -26, 76, 52, 6, 3))
    + panel(-38, -26, 6, 76, 46, 4, grid2(0, 0, 76, 46, 5, 3));
  const vCamera = () => pad(26, 18) + box(-22, -18, 0, 44, 36, 12, '')
    + cyl(-8, 0, 12, 11, 22, `<circle class="lit" r="6"/>`) + cyl(12, 0, 12, 8, 16, `<circle class="lit" r="4"/>`);
  const vBattery = () => pad(40, 26) + box(-36, -24, 0, 72, 48, 20, cells(-36, -24, 72, 48, 5, 2))
    + wire([[36, 0, 20], [60, 0, 20]], 'flow', '#ffb454', 2.4);
  function vCold() {
    const a = []; for (let i = 0; i < 5; i++) a.push(`M-28,${-20 + i * 10} H28`);
    return pad(40, 26) + box(-36, -28, 0, 72, 56, 8, '') + box(-32, -24, 8, 64, 48, 12, `<path class="etch flow" d="${a.join(' ')}" stroke-dasharray="8 5"/>`)
      + wire([[-36, -20, 18], [-64, -20, 18]], 'flow', '#3ee0ff', 2.6) + wire([[36, 20, 18], [64, 20, 18]], 'flow rev', '#ff4d6d', 2.6);
  }
  const vFan = () => pad(30, 19) + box(-26, -26, 0, 52, 52, 10, '') + cyl(0, 0, 10, 22, 16, blades(19, 7));
  const vLaser = () => pad(34, 20) + box(-30, -16, 0, 60, 32, 20, grid2(-30, -16, 60, 32, 3, 2))
    + `<g class="pulse">${wire([[30, 0, 10], [96, 0, 10]], '', '#ff8fab', 3)}</g>` + cyl(30, 0, 4, 6, 12, '');
  const vGlass = () => pad(44, 28) + box(-40, -30, 0, 80, 60, 7, holes(-40, -30, 80, 60, 7, 5, 2.2))
    + box(-34, -24, 9, 68, 48, 5, grid2(-34, -24, 68, 48, 5, 3));
  const vTransformer = () => pad(32, 21) + box(-26, -22, 0, 52, 44, 44, grid2(-26, -22, 52, 44, 3, 3))
    + [-14, 0, 14].map(x => cyl(x, 0, 44, 6, 22, '')).join('') + wire([[26, 22, 20], [56, 22, 20]], 'flow', '#ffb454', 2.2);
  const vDC = () => pad(46, 28) + box(-44, -24, 0, 88, 48, 4, '')
    + [-28, 0, 28].map((x, i) => box(x - 12, -16, 4, 24, 32, 58 + (i === 1 ? 14 : 0), grid2(x - 12, -16, 24, 32, 1, 4))).join('');
  const vCar = () => pad(48, 28) + [[-30, -24], [30, -24], [-30, 24], [30, 24]].map(([x, y]) => cyl(x, y, 0, 9, 12, '')).join('')
    + box(-44, -24, 8, 88, 48, 12, cells(-44, -24, 88, 48, 5, 2))
    + box(-24, -16, 20, 48, 32, 14, grid2(-24, -16, 48, 32, 3, 2));
  const vShip = () => pad(48, 24) + box(-46, -14, 0, 92, 28, 16, grid2(-46, -14, 92, 28, 6, 2))
    + box(-14, -10, 16, 30, 20, 16, grid2(-14, -10, 30, 20, 2, 2)) + cyl(6, 0, 32, 4, 14, '');
  const vPlane = () => pad(44, 26) + box(-44, -7, 14, 88, 14, 12, '') + box(-10, -42, 16, 22, 84, 6, grid2(-10, -42, 22, 84, 1, 6))
    + box(-40, -18, 16, 12, 36, 5, '') + panel(-44, -3, 26, 16, 16, 4, '');
  const vDrone = () => pad(40, 26) + box(-12, -12, 16, 24, 24, 12, grid2(-12, -12, 24, 24, 2, 2))
    + box(10, -4, 20, 24, 8, 5) + box(-34, -4, 20, 24, 8, 5) + box(-4, 10, 20, 8, 24, 5) + box(-4, -34, 20, 8, 24, 5)
    + [[34, 0], [-34, 0], [0, 34], [0, -34]].map(([x, y]) => cyl(x, y, 24, 6, 8, blades(20, 3))).join('');
  const vSat = () => pad(34, 22) + box(-16, -16, 34, 32, 32, 26, grid2(-16, -16, 32, 32, 2, 2))
    + panel(-66, -8, 44, 48, 18, 3, grid2(0, 0, 48, 18, 4, 2)) + panel(18, -8, 44, 48, 18, 3, grid2(0, 0, 48, 18, 4, 2))
    + `<g class="pulse">${wire([[0, 0, 34], [0, 0, 0]], '', '#3ee0ff', 1.6)}</g>`;
  const vArm = () => pad(30, 20) + box(-24, -22, 0, 48, 44, 12, grid2(-24, -22, 48, 44, 2, 2))
    + cyl(0, 0, 12, 16, 26, holes(-10, -10, 20, 20, 2, 2, 2.4)) + box(-6, -8, 38, 58, 16, 12, grid2(-6, -8, 58, 16, 4, 1))
    + cyl(46, 0, 50, 7, 10, `<circle class="lit" r="4"/>`);

  /* ================================================================ 十八個題材 */
  const T = {};

  T.cowos = () => chainScene({
    title: 'CoWoS 先進封裝：一顆 AI 加速器怎麼做出來',
    cap: '設計定案 → 投片 → 中介層上把邏輯晶粒與 HBM 拼起來 → 封測上蓋 → 裝到載板與主機板。台廠在每一段都有位置。',
    stations: [
      S('equip', 0, '設備與材料', ['暫時鍵合、電鍍、載具', '晶圓廠擴產先反映在這'], ['3680', '6187', '3583', '3131'], 'adv_pkg', vMachine),
      S('design', 0, 'IC 設計與 IP', ['GPU / ASIC 規格定案', '矽智財與設計服務'], ['3443', '3661', '3529'], 'ip_eda', vChip),
      S('foundry', 1, '晶圓代工', ['3nm / 2nm 邏輯晶粒', 'HBM 基底晶片也在這'], ['2330'], 'foundry', vWafer),
      S('stack', 1, '中介層 ＋ HBM 堆疊', ['CoWoS-S/L：TSV、微凸塊', '一顆 GPU 旁 4–8 顆 HBM'], ['2330', '3711', '2408'], 'adv_pkg', vStack),
      S('pkg', 2, '載板、封測與出貨', ['ABF 載板、上蓋、燒機', '接到加速卡主機板'], ['3037', '8046', '6239', '3711'], 'abf_pcb', vBoard, .96),
    ],
    steps: [{ p: 'design', t: '設計定案', s: 'IP / EDA' }, { p: 'foundry', t: '投片', s: '晶圓製造' }, { p: 'stack', t: '中介層堆疊', s: 'CoWoS' },
    { p: 'pkg', t: '封測上蓋', s: 'OSAT' }, { p: 'pkg', t: '上板', s: '載板 → PCB' }],
  });

  T.hbm_memory = () => chainScene({
    title: 'HBM 與記憶體：從一顆 DRAM 到一條模組',
    cap: 'DRAM 顆粒疊起來用 TSV 打穿變成 HBM；台廠主力在利基型記憶體、控制 IC、模組與封測這幾段。',
    stations: [
      S('dram', 0, 'DRAM / 快閃顆粒', ['利基型 DRAM 與 NOR', '報價循環是股價主軸'], ['2408', '2344', '3006', '2337'], 'hbm', vChip),
      S('stackp', 1, 'TSV 堆疊封裝', ['8–12 層疊起來打通孔', '良率由封測把關'], ['2330', '6239', '3711'], 'adv_pkg', vStack, 1.05),
      S('ctrl', 1, '控制 IC 與韌體', ['NAND 控制器與介面', '決定模組的規格上限'], ['8299', '6526'], 'ic_design', vChip, .92),
      S('module', 2, '模組與儲存', ['DIMM、SSD、工控記憶體', '出海量最大的一段'], ['4967', '3260', '5289'], 'hbm', vModule),
      S('server', 2, 'AI 伺服器與 PC', ['模型越大吃越多記憶體', '終端拉貨才是需求源頭'], ['6669', '2382'], 'assembly', vRack, .9),
    ],
    steps: [{ p: 'dram', t: '顆粒製造', s: '2408 / 2344' }, { p: 'stackp', t: '堆疊封裝', s: 'TSV' }, { p: 'ctrl', t: '控制 IC', s: '8299' },
    { p: 'module', t: '模組組裝', s: '4967 / 3260' }, { p: 'server', t: '終端出貨', s: '伺服器 / PC' }],
  });

  T.pcb_ccl = () => chainScene({
    title: '高階 PCB 與 CCL：一片板子是怎麼壓出來的',
    cap: 'PCB 是元件之間的「道路系統」。玻纖布＋樹脂＋銅箔壓成 CCL，再蝕刻、鑽孔、電鍍、壓合成多層板與載板。',
    stations: [
      S('glass', 0, '玻纖布與樹脂', ['板材的骨架與黏著', '決定尺寸穩定度'], ['1815', '1303'], 'ccl', vLattice),
      S('ccl', 0, 'CCL 銅箔基板', ['樹脂含浸玻纖＋壓銅箔', '高速低損耗是主戰場'], ['2383', '6274', '6213'], 'ccl', vStack, .95),
      S('press', 1, '蝕刻鑽孔與壓合', ['多層壓合，層數＝難度', 'AI 板要 20 層以上'], ['3044', '2313', '5469'], 'abf_pcb', vMachine),
      S('abf', 1, 'ABF 載板', ['晶片直接坐上去那一層', '台廠寡占、擴產看訂單'], ['3037', '8046', '3189'], 'abf_pcb', vBoard, .95),
      S('fpc', 2, '軟板與終端應用', ['FPC、軟硬結合板', '伺服器、手機、車用'], ['6269', '2368'], 'assembly', vPhone),
    ],
    steps: [{ p: 'ccl', t: '覆銅板', s: 'CCL 板材' }, { p: 'press', t: '蝕刻', s: '做出線路' }, { p: 'press', t: '鑽孔', s: '微孔加工' },
    { p: 'abf', t: '電鍍', s: '孔壁導通' }, { p: 'abf', t: '壓合', s: '多層疊起' }],
    flowTitle: 'PCB 製作流程（點一格＝點上面那個環節）',
  });

  T.glass_substrate = () => chainScene({
    title: '玻璃基板：下一代封裝載板',
    cap: '玻璃比有機載板更平整、翹曲更小、可做更大尺寸。難的是在玻璃上打出 TGV 通孔並把孔壁鍍上銅。',
    stations: [
      S('material', 0, '玻璃與關鍵材料', ['玻璃核心、乾膜、銅箔', '目前多半仰賴進口'], ['4770', '1303', '2383'], 'ccl', vGlass),
      S('laser', 0, '雷射加工設備', ['打孔設備與治具', '最先吃到訂單的一段'], ['6187', '3413', '3680'], 'adv_pkg', vLaser, .95),
      S('tgv', 1, 'TGV 玻璃通孔', ['雷射打孔＋蝕刻擴孔', '孔徑與側壁是門檻'], ['6187', '3680'], 'adv_pkg', vGlass, .95),
      S('plating', 1, '金屬化與 RDL', ['孔壁鍍銅、重佈線層', '濕製程設備受惠'], ['3131', '3583'], 'adv_pkg', vMachine),
      S('pkg', 2, '載板與先進封裝', ['玻璃載板上放晶粒與 HBM', '放量要等製程成熟'], ['3037', '8046', '6271'], 'abf_pcb', vBoard, .95),
    ],
    steps: [{ p: 'material', t: '玻璃備料', s: '4770 / 1303' }, { p: 'laser', t: '雷射打孔', s: '6187 / 3413' }, { p: 'tgv', t: 'TGV 成孔', s: '蝕刻擴孔' },
    { p: 'plating', t: '電鍍 RDL', s: '3131 / 3583' }, { p: 'pkg', t: '晶片貼裝', s: '2330 / 3711' }],
  });

  T.asic_ip = () => chainScene({
    title: 'ASIC 與矽智財：一顆客製晶片的組成',
    cap: '客戶出規格，設計服務廠把各家 IP（運算核、高速介面、記憶體控制、類比）拼成一顆 SoC，再交給晶圓代工投片。',
    stations: [
      S('ip', 0, '矽智財授權', ['RISC-V 核、記憶體 IP', '收授權金＋權利金'], ['3529', '6643'], 'ip_eda', vLattice),
      S('phy', 0, '高速介面 IP', ['SerDes / PCIe / UCIe', 'chiplet 能不能拼靠它'], ['4966', '6104', '6415'], 'ip_eda', vChip, .92),
      S('service', 1, '設計服務（NRE）', ['從規格到量產一條龍', '認列跟著專案走'], ['3443', '3661'], 'ip_eda', vBoard, .95),
      S('foundry', 1, '投片：晶圓代工', ['設計定案後的量產夥伴', '先進製程排隊'], ['2330'], 'foundry', vWafer),
      S('client', 2, '封測與客戶量產', ['封測、模組與終端出貨', 'CSP 自研晶片是主需求'], ['3711', '8299', '5269'], 'osat_test', vRack, .92),
    ],
    steps: [{ p: 'ip', t: 'IP 授權', s: '3529 / 6643' }, { p: 'service', t: '設計服務', s: '3443 / 3661' }, { p: 'foundry', t: '投片', s: '2330' },
    { p: 'client', t: '封測', s: '3711' }, { p: 'client', t: '客戶量產', s: 'CSP / 網通' }],
  });


  /* ================================================================ AI 伺服器專用零件庫（2026-09-23）
     Andy：「題材分頁 每個題材的圖都需要優化的更細緻點，只需要提供圖片給讀者閱讀即可」。
     「只需要提供圖片給讀者閱讀」＝ 讀者不點、不滑、不轉，光看圖就要認得出每一層是什麼零件。
     改版前的五層是同一塊格子板換五種顏色（藍／粉／灰／黃／紫），顏色一拿掉就全部一樣 ——
     所以這一輪的判準是**形狀要帶出那個零件真正的識別特徵**，不是把面數畫多。

     五層各自靠什麼被認出來（這就是每支函式存在的理由）：
       1 vaPackage  中央一顆最大最厚的邏輯晶粒 ＋ 兩側各四疊 HBM（層與層之間看得到接縫）
                    ＋ 底下薄薄一片矽中介層 ＋ 載板底面一排錫球 → 這是「一顆封裝」不是一塊板子
       2 vaPcbStack 板材一層一層往內縮的階梯剖面（多層壓合）＋ 表面銅走線 ＋ 板緣一排金手指
                    ＋ 右側屏蔽連接器籠 → 這是「一疊板材與連接」不是一塊單層 PCB
       3 vaPowerCool 左：電源模組（一排直立散熱鰭片 ＋ 銅匯流排）
                     右：液冷板（表面蛇行流道 ＋ 兩顆進出水快接頭，藍進橘出）→ 兩件事並置
       4 vaTray      抽屜狀：前面板有把手與一整排散熱開孔，裡面看得到並排的 GPU 模組（帶鰭片）與風扇
       5 vaRackPair  左：運算機櫃（一格一格托盤堆疊、每格有把手與狀態燈）
                     右：網通機櫃（ToR 交換器一排埠 ＋ 垂下來的光纖束）

     等角投影的兩條硬限制，寫在這裡免得下次有人重踩：
       · 一個扁平物件的螢幕寬高比上限 ＝ 0.866/0.5 ＝ 1.73。框開到 2.6:1，零件只會佔一半寬。
       · 想把兩個物件「並排」而不長高，要往 (+Δx, −Δy) 擺 —— 那等於純水平位移，
         所以這裡直接用 aiShift() 做螢幕座標的水平平移，比算模型座標好讀也不會算錯。
     色碼：一律 --dg-* token（AI_STYLE）。只有「材料本身就有顏色」的東西才脫離環節色
     （金手指＝金、匯流排＝銅、錫球＝錫、冷卻水藍進橘出），其餘讓 f1/f2/f3 吃環節色，
     右邊卡片與左邊零件的連動才不會斷。 */
  const AI_STYLE = `<style>
    .dg3 .ai-au{fill:var(--dg-au);stroke:color-mix(in srgb,var(--dg-au) 55%,var(--dg-sh0));stroke-width:.4}
    .dg3 .ai-cu .f1{fill:color-mix(in srgb,var(--dg-cu) 80%,var(--dg-sn))}
    .dg3 .ai-cu .f2{fill:var(--dg-cu)}
    .dg3 .ai-cu .f3{fill:color-mix(in srgb,var(--dg-cu) 72%,var(--dg-sh0))}
    .dg3 .ai-ball{fill:var(--dg-sn);fill-opacity:.85;stroke:none}
    .dg3 .ai-port{fill:var(--dg-sh0);fill-opacity:.55;stroke:var(--dg-sn);stroke-opacity:.3;stroke-width:.6}
    .dg3 .ai-vent{fill:none;stroke:var(--dg-sh0);stroke-opacity:.5;stroke-width:1.1}
    .dg3 .ai-led{fill:var(--dg-cold);fill-opacity:.9;stroke:none}
    .dg3 .ai-chan{fill:none;stroke:var(--dg-cold);stroke-opacity:.8;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
    .dg3 .ai-seam{fill:none;stroke:var(--dg-sh0);stroke-opacity:.45;stroke-width:.7}
  </style>`;

  // 純螢幕水平位移：等角裡把第二個物件擺到右邊又不讓整體長高，用這支最穩（理由見上面那段）
  const aiShift = (dx, inner) => `<g transform="translate(${dx},0)">${inner}</g>`;
  // 一排錫球（BGA）：封裝底下才有這一圈，是「這是封裝」的第一眼特徵
  const aiBalls = (x0, y0, x1, y1, n) => {
    const a = [];
    for (let i = 0; i < n; i++) {
      const t = n === 1 ? 0 : i / (n - 1), x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t;
      a.push(`<ellipse class="ai-ball" cx="${px(x, y).toFixed(1)}" cy="${py(x, y, -3).toFixed(1)}" rx="4" ry="2.7"/>`);
    }
    return a.join('');
  };
  // 一疊薄片：HBM 就是靠「看得出是一疊」被認出來的，所以層與層之間一定要留得出接縫
  const aiPile = (x, y, z, w, d, n, t, gap) => {
    let s = ''; gap = gap == null ? 1.2 : gap;
    for (let i = 0; i < n; i++) s += box(x, y, z + i * (t + gap), w, d, t, '');
    return s;
  };
  // 散熱鰭片：一排立起來的薄板。看到鰭片就知道這是散熱件（電源模組、GPU 模組共用）
  const aiFins = (x, y, z, w, d, h, n, th) => {
    let s = ''; th = th || 2.4;
    const step = (w - th) / Math.max(1, n - 1);
    for (let i = 0; i < n; i++) s += box(x + i * step, y, z, th, d, h, '');
    return s;
  };
  /* 金手指：板緣一排金色細條（畫在頂面，所以用模型座標）。
     n 條沿著 x 排開、每條往 y 方向延伸 d —— 方向要跟板緣垂直，
     排錯方向就變成「貼在板子中間的一塊黃斑」（2026-09-23 第一版踩過）。*/
  const aiGold = (x, y, w, d, n) => {
    const a = [], step = w / n;
    for (let i = 0; i < n; i++)
      a.push(`<rect class="ai-au" x="${(x + i * step + step * .22).toFixed(1)}" y="${y}" width="${(step * .56).toFixed(1)}" height="${d}" rx="1"/>`);
    return a.join('');
  };
  // 蛇行流道：水冷板的識別特徵（進水 → 在板內繞一圈 → 出水）
  const aiSerpent = (x, y, w, d, n) => {
    const step = d / n, a = [];
    for (let i = 0; i < n; i++) {
      const yy = (y + step * (i + .5)).toFixed(1);
      a.push(`M${x + 5},${yy} H${(x + w - 5).toFixed(1)}`);
      if (i < n - 1) a.push(`M${(i % 2 ? x + 5 : x + w - 5).toFixed(1)},${yy} V${(y + step * (i + 1.5)).toFixed(1)}`);
    }
    return `<path class="ai-chan" d="${a.join(' ')}"/>`;
  };
  /* 垂直面上的開孔陣列（托盤前面板的散熱孔、交換器的埠、托盤把手旁的狀態燈）。
     y=y0 的那個立面，局部座標 (u, v)：u 沿 +x、v 是從 z0 往上量的高度。
     ⚠ z0 不能省：交換器裝在機櫃上段，從地面量的話埠會畫到櫃子底下（2026-09-23 第一版就是這樣）。
     ⚠ 這個矩陣的行列式是負的（鏡射），所以不要把文字放進來。*/
  const aiFace = (x0, y0, z0, inner) => `<g transform="translate(${px(x0, y0).toFixed(1)},${py(x0, y0, z0 || 0).toFixed(1)}) matrix(0.866,0.5,0,-1,0,0)">${inner}</g>`;

  // ---- 第 1 層：GPU / ASIC 與封裝 ----------------------------------------
  function vaPackage() {
    // 載板：最底最大、表面走線，邊緣露出一圈 —— 晶片是「坐在」載板上，不是跟它同一塊
    return pad(80, 48)
      + box(-76, -48, 0, 152, 96, 6, trace(-76, -48, 152, 96, 5))
      + aiBalls(-64, 46, 64, 46, 12) + aiBalls(74, -38, 74, 38, 8)   // 底面兩排錫球
      // 矽中介層：比載板小一圈、薄很多；CoWoS 的關鍵就是這一片把晶粒和 HBM 接在一起
      + box(-62, -39, 6, 124, 78, 4, '')
      // 邏輯晶粒：正中央最大最厚的一塊，一眼過去的主角
      + box(-19, -27, 10, 38, 54, 16, grid2(-19, -27, 38, 54, 3, 4))
      // 左右各四疊 HBM（2 欄 × 2 列），每疊四片 → 看得出來是「一疊」而不是一塊方糖
      + [[-57, -35], [-38, -35], [-57, 3], [-38, 3], [23, -35], [42, -35], [23, 3], [42, 3]]
        .map(([x, y]) => aiPile(x, y, 10, 16, 32, 4, 3.2)).join('');
  }

  // ---- 第 2 層：板材、載板與連接 ------------------------------------------
  function vaPcbStack() {
    // 五片板材一層一層往內縮：階梯狀的邊緣就是「多層壓合」的剖面感（單層板畫不出這個）
    let s = pad(74, 46);
    for (let i = 0; i < 5; i++) {
      const x = -68 + i * 5, y = -44 + i * 3.5, w = 136 - i * 10, d = 88 - i * 7, z = i * 4.6;
      s += box(x, y, z, w, d, 3.4, i === 4 ? trace(x, y, w, d, 4) : '');
    }
    const tx = -48, ty = -30, tz = 4 * 4.6 + 3.4;   // 最上面那片的頂面
    return s
      // 板緣一排金手指：連接器插進去的地方，PCB 圖少了它就只是一塊板子
      + onTop(tz, aiGold(tx + 40, ty + 44, 50, 14, 9))
      // 屏蔽連接器籠：靠近觀者那一角的方盒 ＋ 三個往外凸的埠口（QSFP 籠就是長這樣）
      + box(tx + 60, ty + 4, tz, 32, 32, 18, '')
      + [4, 14, 24].map(dy => box(tx + 92, ty + dy, tz + 5, 5, 7, 10, '')).join('')
      // 貫穿導通孔：三條穿過整疊的虛線，說明「層跟層之間是通的」
      + [[-20, -8], [8, 6], [30, -18]].map(([x, y]) => wire([[x, y, 0], [x, y, tz + 2]], 'etch', 'var(--dg-cu)', 1.3)).join('');
  }

  // ---- 第 3 層：電源與散熱（兩件事並置，不是一塊板） -------------------------
  function vaPowerCool() {
    // 左：電源模組 —— 底下是模組本體，上面一排直立鰭片，左邊拉出一條銅匯流排
    const psu = box(-56, -28, 0, 68, 56, 15, '')
      + aiFins(-51, -23, 15, 58, 46, 24, 10)
      + `<g class="ai-cu">${box(-82, -12, 4, 28, 22, 8, '')}</g>`
      + box(-56, 22, 0, 68, 6, 15, holes(-56, 22, 68, 6, 6, 1, 1.8));
    // 右：液冷板 —— 表面蛇行流道 ＋ 兩顆快接頭，藍色進水、橘色出水（語意色，兩個主題都固定）
    const cold = box(-42, -34, 0, 88, 68, 6, '')
      + box(-38, -30, 6, 80, 60, 11, aiSerpent(-38, -30, 80, 60, 5))
      + cyl(-24, -34, 17, 8, 15, '') + cyl(26, -34, 17, 8, 15, '')
      + cyl(-24, -34, 15, 10, 3, '') + cyl(26, -34, 15, 10, 3, '')   // 快接頭的套環，少了它只是兩根柱子
      + wire([[-24, -34, 32], [-24, -76, 36]], 'flow', 'var(--dg-cold)', 2.8)
      + wire([[26, -76, 36], [26, -34, 32]], 'flow rev', 'var(--dg-hot)', 2.8);
    return pad(78, 46) + psu + aiShift(104, cold);
  }

  // ---- 第 4 層：GPU 運算托盤（抽屜） ----------------------------------------
  function vaTray() {
    const X0 = -94, Y0 = -38, W = 188, D = 78;
    let s = pad(88, 46) + box(X0, Y0, 0, W, D, 5, '')                 // 托盤底板
      + box(X0, Y0, 5, 5, D, 13, '') + box(X0 + W - 5, Y0, 5, 5, D, 13, '')   // 左右側牆
      + box(X0, Y0, 5, W, 5, 13, '');                                  // 後牆
    // 前面板：比側牆高，上面有兩支把手與一整排散熱開孔 —— 這是「抽屜」最強的識別特徵
    const FY = Y0 + D - 6;
    s += box(X0, FY, 0, W, 6, 26, '')
      + box(X0 + 14, FY + 6, 8, 26, 4, 5, '') + box(X0 + W - 40, FY + 6, 8, 26, 4, 5, '')
      + aiFace(X0, FY + 6, 0, (() => {
        const a = [];
        for (let i = 0; i < 22; i++) for (let j = 0; j < 3; j++)
          a.push(`<circle class="ai-vent" cx="${(10 + i * 7.8).toFixed(1)}" cy="${(6 + j * 6).toFixed(1)}" r="2"/>`);
        // 狀態燈：一顆就夠，不需要整排在閃
        a.push(`<circle class="ai-led" cx="${(W - 12).toFixed(1)}" cy="20" r="2.6"/>`);
        return a.join('');
      })());
    // 裡面：四塊並排的 GPU 模組（每塊底下是基板、上面是鰭片），前緣三顆風扇
    for (let i = 0; i < 4; i++) {
      const x = X0 + 12 + i * 42;
      s += box(x, Y0 + 10, 5, 34, 40, 4, '') + aiFins(x + 3, Y0 + 13, 9, 28, 34, 15, 6);
    }
    for (let i = 0; i < 3; i++) {
      const x = X0 + 28 + i * 56;
      s += cyl(x, Y0 + 60, 5, 13, 11, blades(11, 7)) ;
    }
    return s;
  }

  // ---- 第 5 層：整機櫃與網通 ----------------------------------------------
  function vaRackPair() {
    // 左：運算機櫃 —— 一格一格的托盤堆疊，每格前面有把手與一顆狀態燈（看得出是「很多台疊起來」）
    const RX = -48, RY = -28, RW = 96, RD = 56;
    let rack = box(RX, RY, 0, RW, RD, 7, '')                       // 底座
      + box(RX, RY, 7, 7, RD, 96, '') + box(RX + RW - 7, RY, 7, 7, RD, 96, '')   // 兩側立柱
      + box(RX, RY, 7, RW, 6, 96, '');                              // 背板
    for (let i = 0; i < 6; i++) {
      const z = 11 + i * 14, fy = RY + RD - 5;
      rack += box(RX + 7, RY + 6, z, RW - 14, RD - 11, 10, '')
        + box(RX + 18, fy, z + 3, 18, 4, 4, '') + box(RX + RW - 36, fy, z + 3, 18, 4, 4, '')
        + aiFace(RX + 7, fy, z, `<circle class="ai-led" cx="${RW - 26}" cy="5" r="2.4"/>`);
    }
    rack += box(RX, RY, 103, RW, RD, 7, '');                        // 頂蓋
    // 右：網通機櫃 —— ToR 交換器一整排埠，底下垂下來一束光纖（「網通」的識別特徵）
    const SX = -34, SY = -24, SW = 70, SD = 48;
    let net = box(SX, SY, 0, SW, SD, 7, '')
      + box(SX, SY, 7, 6, SD, 82, '') + box(SX + SW - 6, SY, 7, 6, SD, 82, '')
      + box(SX, SY, 7, SW, 5, 82, '');
    // 交換器本體擺在上段：前面板一整排埠
    const swz = 58, fy = SY + SD - 4;
    net += box(SX + 6, SY + 5, swz, SW - 12, SD - 9, 13, '')
      + aiFace(SX + 6, fy, swz, (() => {
        const a = [];
        // 兩排埠：ToR 交換器的前面板就是一整排 QSFP，這是「網通」而不是「又一台伺服器」的識別特徵
        for (let r = 0; r < 2; r++) for (let i = 0; i < 9; i++)
          a.push(`<rect class="ai-port" x="${(5 + i * 5.8).toFixed(1)}" y="${3 + r * 5}" width="4.2" height="3.6" rx=".8"/>`);
        return a.join('');
      })());
    // 光纖束：從交換器前面板垂下來再繞到左邊的運算機櫃（兩櫃之間是連著的）
    // 光纖束：從交換器前面板垂下來、往左拉回運算機櫃。
    // 終點要真的落在左櫃身上，停在半空中會看起來像「線斷掉」而不是「兩櫃之間連著」。
    net += [0, 1, 2, 3].map(i => {
      const sx = px(SX + 10 + i * 9, fy), sy0 = py(SX + 10 + i * 9, fy, swz + 2);
      return `<path class="ai-fib" d="M${sx.toFixed(1)},${sy0.toFixed(1)} C${(sx - 20).toFixed(1)},${(sy0 + 30).toFixed(1)} ${(sx - 86 - i * 5).toFixed(1)},${(sy0 + 26).toFixed(1)} ${(sx - 128 - i * 6).toFixed(1)},${(sy0 + 66 + i * 5).toFixed(1)}" fill="none" stroke="var(--dg-opt,var(--dg-cold))" stroke-width="1.7" stroke-opacity=".75"/>`;
    }).join('');
    // 下半部是配線盤：一格一格、每格前面板一排埠（空白層板看起來只是「架子」，不是網通設備）
    for (let i = 0; i < 3; i++) {
      const z = 12 + i * 13;
      net += box(SX + 6, SY + 5, z, SW - 12, SD - 9, 8, '')
        + aiFace(SX + 6, fy, z, (() => {
          const a = [];
          for (let k = 0; k < 10; k++) a.push(`<rect class="ai-port" x="${(4 + k * 5.4).toFixed(1)}" y="2.4" width="3.6" height="3.4" rx=".8"/>`);
          return a.join('');
        })());
    }
    net += box(SX, SY, 89, SW, SD, 6, '');   // 頂蓋：少了它上面是開口，看起來像半成品
    return pad(80, 46) + rack + aiShift(196, net);
  }

  /* AI 伺服器：2026-09-23 改版。零件全部換成上面那套專用件（識別特徵見 vaPackage 上方那段），
     版面用 o.ex 自己覆寫（框更寬、卡片等高），其他七張爆炸圖一個像素都沒動。
     每一層第三行 sub 是新加的「看圖看什麼」—— 圖是主角，那一行是圖的使用說明。*/
  T.ai_server = () => explodeScene({
    title: 'AI 伺服器：從一顆晶片到一座機櫃',
    cap: '晶片與封裝是成本主體，往下是板材與載板，再往下是電源與散熱，最後由 ODM 組成托盤與整機櫃交給雲端業者。',
    unit: '整機爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE,
    cw: 980,
    ex: { X: 182, TOP: 182, UNIT_Y: 68, ROW: 140, MW: 212, MH: 122, LX: 376, LW: 582, CHIP_DY: 34, SLOT_MIN: 112 },
    layers: [
      S('chip', 0, 'GPU / ASIC 與封裝', ['邏輯晶粒＋HBM＋CoWoS', '整櫃成本的最大塊',
        '圖上：中央大晶粒、兩側各四疊 HBM、底下矽中介層與一排錫球'], ['2330', '3661', '3711'], 'foundry', vaPackage),
      S('board', 0, '板材、載板與連接', ['高層數低損耗 PCB', 'CCL、載板與連接器',
        '圖上：板材一層層往內縮的壓合階梯、表面銅走線、板緣金手指與連接器籠'], ['2383', '3037', '2368', '3665'], 'abf_pcb', vaPcbStack),
      S('power', 1, '電源與散熱', ['800V HVDC、BBU', '水冷板、CDU、風扇',
        '圖上：左邊電源模組帶鰭片與銅匯流排，右邊水冷板走蛇行流道，藍進橘出'], ['2308', '6409', '3017', '3324'], 'thermal', vaPowerCool),
      S('tray', 1, 'GPU 運算托盤', ['ODM 板卡與托盤組裝', '出貨量能見度最高',
        '圖上：抽屜狀機構，前面板有把手與散熱開孔，裡面四塊 GPU 模組與三顆風扇'], ['2382', '6669', '3231', '2356'], 'assembly', vaTray),
      S('rack', 2, '整機櫃與網通', ['整櫃交付、ToR 交換器', '終端是雲端業者',
        '圖上：左櫃是一格格托盤堆疊，右櫃是 ToR 交換器的埠排與垂下來的光纖束'], ['2317', '2345', '5388'], 'switch', vaRackPair),
    ],
    steps: [{ p: 'chip', t: '晶片與封裝', s: '2330 / 3711' }, { p: 'board', t: '上板', s: '3037 / 2383' }, { p: 'power', t: '電源散熱', s: '2308 / 3017' },
    { p: 'tray', t: '托盤組裝', s: '2382 / 6669' }, { p: 'rack', t: '整櫃交付', s: '資料中心' }],
  });

  T.power_bbu = () => explodeScene({
    title: '伺服器電源與 BBU：機櫃的心臟',
    cap: '單櫃功耗從十幾 kW 跳到上百 kW，電源模組數量、電壓規格（800V HVDC）與備援電池全部跟著改版。',
    layers: [
      S('pmic', 0, '電源管理 IC', ['數位電源控制與轉換', '效率每個百分點都算'], ['6415', '3529', '6533'], 'ic_design', vChip),
      S('psu', 1, 'PSU 電源模組', ['伺服器電源供應器', 'AI 機櫃用量倍增'], ['2308', '6409', '6412'], 'power', vModule),
      S('bbu', 1, 'BBU 備援電池', ['掉電時撐住不當機', '模組化可熱抽換'], ['3211', '2489'], 'power', vBattery, .92),
      S('busbar', 2, '匯流排與機構件', ['高壓直流送電到每層', '滑軌、連接器與通路'], ['2059', '3033', '3023'], 'power', vCoil),
      S('rack', 2, '機櫃與資料中心', ['整櫃供電架構改版', '電力是擴機房的瓶頸'], ['2382', '6669'], 'assembly', vRack, .92),
    ],
    steps: [{ p: 'pmic', t: '電源 IC', s: '6415 / 3529' }, { p: 'psu', t: 'PSU 模組', s: '2308 / 6409' }, { p: 'bbu', t: 'BBU', s: '3211' },
    { p: 'busbar', t: '匯流與機構', s: '2059 / 3023' }, { p: 'rack', t: '機櫃整合', s: '2382 / 6669' }],
  });

  T.thermal = () => explodeScene({
    title: '散熱與液冷：熱從晶片怎麼被帶出機房',
    cap: '單顆 GPU 破千瓦，風冷已經不夠。價值一路從均熱片、風扇往水冷板、快接頭與機櫃 CDU 移動。',
    layers: [
      S('vc', 0, '均熱片與熱管', ['VC 均熱板、熱管', '風冷世代的主力'], ['3653', '6230', '3013'], 'thermal', vStack, .9),
      S('fan', 0, '風扇與散熱模組', ['前端進氣與機櫃風牆', '風冷仍是多數機種'], ['2421', '6230'], 'thermal', vFan),
      S('plate', 1, '水冷板 Cold Plate', ['直接貼晶片帶走熱', 'AI 機櫃逐步標配'], ['3017', '3324'], 'thermal', vCold, .95),
      S('cdu', 1, 'CDU 與快接頭', ['幫浦、熱交換、分歧管', '漏液是最大風險'], ['8996', '2308', '6122'], 'thermal', vMachine),
      S('rack', 2, 'AI 機櫃與機房', ['整櫃液冷與機房冷卻水', '功耗越高越往這走'], ['6669', '2382'], 'assembly', vRack, .92),
    ],
    steps: [{ p: 'vc', t: '均熱片', s: '3653 / 6230' }, { p: 'plate', t: '水冷板', s: '3017 / 3324' }, { p: 'cdu', t: '快接管件', s: '8996' },
    { p: 'cdu', t: 'CDU', s: '8996 / 2308' }, { p: 'rack', t: '機房冷卻', s: '資料中心' }],
  });

  T.silicon_photonics = () => chainScene({
    title: '矽光子與 CPO：電變成光，再送進機房',
    cap: '上游是化合物磊晶與雷射二極體，中游把光引擎做進交換晶片旁邊（CPO），下游是光收發模組與交換器。',
    stations: [
      S('epi', 0, '化合物磊晶材料', ['砷化鎵、磷化銦基板', '高速高頻元件的底材'], ['2455', '8086'], 'optical', vLattice),
      S('ld', 0, '雷射二極體 LD', ['把電訊號轉成光訊號', '光纖通訊裡的心臟'], ['3081', '8086'], 'optical', vLaser, .92),
      S('engine', 1, '光引擎 / 矽光子晶片', ['調變器與光波導', 'CPO 把它封到 ASIC 旁'], ['2330', '4966'], 'optical', vChip),
      S('module', 1, '光收發模組', ['800G–1.6T 模組', '目前台廠營收主力'], ['4979', '4977', '3163', '6442'], 'optical', vModule),
      S('dc', 2, '交換器與資料中心', ['交換晶片與叢集網路', '需求來自 AI 訓練流量'], ['2345', '5388'], 'switch', vDC, .95),
    ],
    steps: [{ p: 'epi', t: '磊晶材料', s: '2455 / 8086' }, { p: 'ld', t: '雷射元件', s: '3081' }, { p: 'engine', t: '光引擎', s: '2330' },
    { p: 'module', t: '模組組裝', s: '4979 / 4977' }, { p: 'dc', t: '交換器', s: '2345' }],
  });

  T.semi_equipment = () => chainScene({
    title: '半導體設備與材料：資本支出落在哪裡',
    cap: '晶圓廠的資本支出會依序流向材料、設備零件、製程機台與載具。台廠多半切在濕製程、零件與耗材這幾段。',
    stations: [
      S('wafer', 0, '矽晶圓與特用材料', ['矽晶圓、靶材、化學品', '耗材跟著產能走'], ['6182', '1785', '4763', '6165'], 'foundry', vWafer),
      S('parts', 0, '設備零件與模組', ['機台零件與精密加工', '設備廠的上游'], ['3413', '6187'], 'foundry', vMachine, .9),
      S('wet', 1, '濕製程與清洗設備', ['清洗、蝕刻、電鍍機台', '台廠最有位置的一段'], ['3131', '3583'], 'foundry', vMachine),
      S('pod', 1, '晶圓載具 FOUP', ['EUV 光罩盒與傳載具', '先進製程才用得到'], ['3680'], 'foundry', vModule, .9),
      S('fab', 2, '晶圓廠資本支出', ['擴產與製程升級', '訂單能見度的源頭'], ['2330', '3711', '5434'], 'foundry', vDC, .95),
    ],
    steps: [{ p: 'wafer', t: '材料備料', s: '6182 / 1785' }, { p: 'parts', t: '設備零件', s: '3413' }, { p: 'wet', t: '製程機台', s: '3131 / 3583' },
    { p: 'pod', t: '載具搬運', s: '3680' }, { p: 'fab', t: '晶圓廠量產', s: '2330' }],
  });

  T.apple_chain = () => chainScene({
    title: '蘋果供應鏈：一支手機是怎麼組起來的',
    cap: '晶片與鏡頭是最上游，中間是板材、軟板與機殼結構件，最後由 EMS 整機組裝出貨。規格年年改，量體看終端銷售。',
    stations: [
      S('soc', 0, 'SoC 與晶片', ['A / M 系列由代工獨家', '射頻與電源 IC 也在這'], ['2330', '2454'], 'foundry', vChip),
      S('lens', 0, '光學鏡頭與相機', ['鏡頭、潛望式模組', '規格升級帶動單價'], ['3008', '3406'], 'assembly', vCamera),
      S('board', 1, '板材、軟板與載板', ['SLP 主機板、FPC', '封裝載板也在這'], ['3037', '6269'], 'abf_pcb', vBoard, .95),
      S('case', 1, '機殼與結構件', ['CNC 機殼與中框', '單價高、良率是關鍵'], ['2474'], 'assembly', vStack, .9),
      S('ems', 2, '整機組裝出貨', ['EMS 組裝與品牌出貨', '量體最大、毛利最薄'], ['2317', '4938', '3231', '2382'], 'assembly', vPhone),
    ],
    steps: [{ p: 'soc', t: '晶片', s: '2330 / 2454' }, { p: 'lens', t: '零組件', s: '3008 / 3406' }, { p: 'board', t: '模組', s: '3037 / 6269' },
    { p: 'ems', t: '整機組裝', s: '2317 / 4938' }, { p: 'ems', t: '品牌出貨', s: '終端銷售' }],
  });

  T.edge_ai_pc = () => explodeScene({
    title: '邊緣 AI 與 AI PC：算力搬到裝置端',
    cap: '端側推論靠 SoC 裡的 NPU，吃記憶體容量也吃散熱。台廠的位置在 ODM 板卡組裝、散熱電源與品牌整機。',
    layers: [
      S('soc', 0, 'SoC 與 NPU', ['端側推論算力', '定義了什麼叫 AI PC'], ['2454', '6533'], 'ic_design', vChip),
      S('mem', 0, '記憶體與儲存', ['端側模型吃容量', 'DRAM / SSD 同步升級'], ['4967', '3260', '8299'], 'hbm', vModule, .92),
      S('board', 1, '板卡與 ODM 組裝', ['主機板設計與代工', '出貨量最大的一段'], ['2324', '2382', '3231', '2356'], 'assembly', vBoard, .95),
      S('power', 1, '電源與散熱模組', ['薄型化＋散熱的難題', '續航與電源管理'], ['2301', '2308'], 'thermal', vFan, .9),
      S('brand', 2, '品牌整機與邊緣機台', ['品牌定義規格吃毛利', '工控與邊緣伺服器'], ['2357', '2353', '2377', '3005'], 'assembly', vLaptop),
    ],
    steps: [{ p: 'soc', t: 'SoC / NPU', s: '2454' }, { p: 'mem', t: '記憶體', s: '4967 / 8299' }, { p: 'board', t: '板卡組裝', s: '2324 / 2382' },
    { p: 'power', t: '散熱電源', s: '2301' }, { p: 'brand', t: '品牌出貨', s: '2357 / 2353' }],
  });

  T.robotics = () => explodeScene({
    title: '機器人：一個關節的價值分佈',
    cap: '一個關節 ＝ 減速機 ＋ 伺服馬達 ＋ 編碼器 ＋ 驅動器。人形機器人的關節數是工業手臂的好幾倍，量起來零組件先受惠。',
    layers: [
      S('reducer', 0, '減速機與傳動', ['諧波／行星減速機', '精度決定重複定位'], ['2049', '4583', '1590'], null, vCoil),
      S('motor', 0, '伺服馬達', ['扭力密度與散熱', '大廠自製比例高'], ['1503', '1504'], 'power', vMotor),
      S('ctrl', 1, '控制器與驅動', ['運動控制與驅動器', '加上 AI 推論晶片'], ['2464', '6215'], 'ic_design', vBoard, .95),
      S('vision', 1, '視覺與感測', ['相機模組、力覺感測', '抓取能力的關鍵'], ['3059', '2359'], 'ic_design', vCamera),
      S('maker', 2, '整機與代工組裝', ['人形機器人整機代工', '線束連接器一起吃'], ['2317', '3665'], 'assembly', vArm, .95),
    ],
    steps: [{ p: 'reducer', t: '零組件', s: '2049 / 1590' }, { p: 'motor', t: '馬達', s: '1503 / 1504' }, { p: 'ctrl', t: '控制器', s: '2464 / 6215' },
    { p: 'vision', t: '感測整合', s: '3059 / 2359' }, { p: 'maker', t: '整機組裝', s: '2317' }],
  });

  T.drone = () => explodeScene({
    title: '無人機：一架四旋翼的供應鏈',
    cap: '馬達與螺旋槳決定推力，飛控與導航決定能不能自己飛，光電酬載決定它拿來做什麼。台廠以零組件與整機認證為主。',
    layers: [
      S('motor', 0, '無刷馬達與螺旋槳', ['推力與續航的核心', '四顆同步調速'], ['8033', '2231'], 'power', vMotor),
      S('conn', 0, '連接器與線束', ['軍規連接器與線材', '可靠度的隱形門檻'], ['3023', '3675'], null, vCoil),
      S('fc', 1, '飛控與導航', ['飛控板、IMU、定位', '抗干擾是軍規重點'], ['6237', '2367'], 'ic_design', vBoard, .95),
      S('payload', 1, '光電酬載與雲台', ['相機、紅外線、測距', '決定任務型態'], ['3059', '2634'], 'ic_design', vCamera),
      S('maker', 2, '整機與軍民用標案', ['國家隊整機廠', '認證與交期是門檻'], ['2634', '3402', '8033'], 'assembly', vDrone, .95),
    ],
    steps: [{ p: 'conn', t: '零組件', s: '2231 / 3023' }, { p: 'motor', t: '動力系統', s: '8033' }, { p: 'fc', t: '飛控導航', s: '6237 / 2367' },
    { p: 'payload', t: '酬載整合', s: '3059' }, { p: 'maker', t: '整機交付', s: '2634 / 3402' }],
  });

  T.satellite = () => explodeScene({
    title: '低軌衛星：天上與地面各拿到什麼',
    cap: '衛星本體幾乎都是國外業者。台廠的錢主要在地面段：射頻元件、相位陣列天線、用戶終端與網通設備。',
    layers: [
      S('epi', 0, '化合物半導體', ['砷化鎵磊晶與晶片', '高頻元件的底材'], ['2455', '8086'], 'optical', vLattice),
      S('rf', 0, '射頻元件與模組', ['功率放大、濾波、混頻', '規格門檻高'], ['3491', '2314'], 'optical', vChip, .92),
      S('ant', 1, '天線與相位陣列', ['波束成形與饋源', '地面站與終端都要'], ['3491', '2314'], 'switch', vPanel, .95),
      S('cpe', 1, '用戶終端 CPE', ['終端設備與家用路由', '出海量最大的一段'], ['6285', '4906', '5388', '3704'], 'switch', vModule),
      S('op', 2, '衛星與電信營運', ['星系營運與網通回傳', '台廠賣零組件給它'], ['2345', '6143'], 'switch', vSat, .95),
    ],
    steps: [{ p: 'epi', t: '磊晶材料', s: '2455 / 8086' }, { p: 'rf', t: '射頻元件', s: '3491' }, { p: 'ant', t: '天線模組', s: '3491 / 2314' },
    { p: 'cpe', t: '終端設備', s: '6285 / 4906' }, { p: 'op', t: '營運商', s: '海外客戶' }],
  });

  T.ev_auto = () => explodeScene({
    title: '車用與電動車：台廠切在哪幾塊',
    cap: '滑板底盤裡是電池包，前後軸各一顆馬達，中間是電控與車載充電器。台廠強項在電源、線束連接器與金屬結構件。',
    layers: [
      S('metal', 0, '金屬與結構件', ['沖壓件、車燈、扣件', '毛利穩、看車廠拉貨'], ['1536', '2228', '1319', '6605'], 'assembly', vStack, .9),
      S('sensor', 0, '車用電子與感測', ['胎壓、感測器、MCU', '車規認證是門檻'], ['2231', '6533'], 'ic_design', vChip, .92),
      S('power', 1, '電源電控與 OBC', ['逆變器、車載充電器', '台廠最有位置的一段'], ['2308', '6409'], 'power', vModule),
      S('harness', 1, '線束與連接器', ['高壓線束、充電槍', '單車用量隨電動化增加'], ['3665', '3023', '2059'], 'power', vCoil),
      S('oem', 2, '整車與車廠', ['系統整合與代工', '終端是國外品牌'], ['2317'], 'assembly', vCar, .95),
    ],
    steps: [{ p: 'metal', t: '結構件', s: '1536 / 2228' }, { p: 'sensor', t: '車用電子', s: '2231' }, { p: 'power', t: '電源電控', s: '2308 / 6409' },
    { p: 'harness', t: '線束整合', s: '3665 / 3023' }, { p: 'oem', t: '整車出貨', s: '國外車廠' }],
  });

  T.defense = () => chainScene({
    title: '軍工國防：預算最後變成哪些載具',
    cap: '國防預算最後變成船、飛機與無人載具，再加上雷達電戰與軍規零組件。訂單期長、認列慢，看的是能見度不是單季。',
    stations: [
      S('parts', 0, '軍規零組件', ['氣動元件與精密件', '認證期長、黏著度高'], ['2231', '1590'], null, vCoil),
      S('rugged', 0, '強固型電腦與電戰', ['軍規電腦與雷達次系統', '毛利高於商規'], ['3005'], 'ic_design', vBoard, .95),
      S('aero', 1, '航太結構與 MRO', ['機體結構、葉片、維修', '長約帶來穩定現金流'], ['2634'], 'assembly', vPlane, .95),
      S('uav', 1, '軍用無人機', ['偵蒐與攻擊型整機', '國家隊標案'], ['8033', '3402'], 'assembly', vDrone, .9),
      S('ship', 2, '艦艇與國防標案', ['海軍艦艇與商船', '交期長、能見度高'], ['2208', '5871'], 'assembly', vShip, .95),
    ],
    steps: [{ p: 'parts', t: '軍規零件', s: '2231 / 1590' }, { p: 'rugged', t: '次系統', s: '3005' }, { p: 'aero', t: '結構整合', s: '2634' },
    { p: 'uav', t: '整機交付', s: '8033 / 3402' }, { p: 'ship', t: '維修 MRO', s: '長約' }],
  });

  T.heavy_electric = () => chainScene({
    title: '重電與電網：電從電廠送到機房',
    cap: '變壓器 → 開關配電盤 → 電纜匯流 → 使用端，旁邊再掛儲能。AI 資料中心的用電讓這條老產業的交期與報價一起上來。',
    stations: [
      S('cable', 0, '銅材與電線電纜', ['銅價連動的基本盤', '電網擴建先拉貨'], ['1609', '1618'], null, vCoil),
      S('transformer', 1, '變壓器', ['交期最長、報價最硬', '台電與機房搶產能'], ['1519', '1513'], 'power', vTransformer),
      S('switchgear', 1, '開關與配電盤', ['GIS、開關箱、配電', '跟著變壓器一起出貨'], ['1514', '1503'], 'power', vMachine),
      S('motor', 1, '馬達與重電設備', ['大型馬達與發電機', '工業需求的溫度計'], ['1504'], 'power', vMotor),
      S('epc', 2, '統包工程與需求端', ['機電統包與儲能', '資料中心與電廠'], ['2404', '3576', '1519'], 'assembly', vDC, .95),
    ],
    steps: [{ p: 'cable', t: '銅材電纜', s: '1609 / 1618' }, { p: 'transformer', t: '變壓器', s: '1519 / 1513' }, { p: 'switchgear', t: '開關配電', s: '1514 / 1503' },
    { p: 'motor', t: '設備整合', s: '1504' }, { p: 'epc', t: '統包交付', s: '2404 / 台電' }],
  });

  /* 爆炸圖的零件高矮差很多（機櫃比晶片高一倍以上），字串階段算不出實際尺寸，
     所以 SVG 進 DOM 之後再量一次 bbox，把每個零件等比縮到自己那一列的框裡並置中。
     app.js 插完圖就呼叫這支；沒有爆炸圖的題材直接跳過。 */
  function fit(root) {
    if (!root) return;
    nativeWidth(root);
    root.querySelectorAll('.p3.stn.ex > g.art').forEach(art => {
      const cx = +art.dataset.cx, cy = +art.dataset.cy;
      const mh = +art.dataset.mh, mw = +art.dataset.mw;
      if (!mh) return;
      art.removeAttribute('transform');
      let bb;
      try { bb = art.getBBox(); } catch (e) { return; }
      if (!bb || !bb.height || !bb.width) return;
      const k = Math.max(.45, Math.min(1.85, Math.min(mh / bb.height, mw / bb.width)));
      const tx = cx - (bb.x + bb.width / 2) * k;
      const ty = cy - (bb.y + bb.height / 2) * k;
      art.setAttribute('transform', `translate(${tx.toFixed(1)},${ty.toFixed(1)}) scale(${k.toFixed(3)})`);
    });
  }

  /* ---------------------------------------------------------------- 原尺寸（native）
     ★ 2026-09-21 art-director，量出來的事實：
       題材圖的 viewBox 寬是 CW＝1180，而它掛的那張卡在 1440 螢幕上是 1344px（放大 1.139 倍），
       在 **800px 螢幕上只剩 940px（壓成 0.797 倍）** —— 12px 的字被壓成 9.56px，
       整張圖 44～57 個文字節點全部低於下限。**這跟字級無關，字級怎麼調都沒用**
       （產業鏈剖析圖 2026-09-21 已經踩過同一個坑，DECISIONS #226）。
     修法跟那邊一模一樣：圖維持原尺寸、欄位不夠寬就左右滑。
     為什麼寫在這裡而不是 app.js：`fit()` 本來就是「SVG 進 DOM 之後再量一次」的那支，
     app.js 插完圖一定會呼叫它 —— 這一批不動 app.js。
     ⚠ 代價寫清楚：800px 一次看得到 940/1180＝80%，390px 只看得到 33%，要左右滑。
     這是 #226 已經拍板的取捨（字級守住優先），不是新的決定。*/
  function nativeWidth(root) {
    const svg = root && root.querySelector('svg');
    if (!svg) return;
    root.style.overflowX = 'auto';
    root.style.overflowY = 'hidden';
    // 每張圖的畫布寬可能不一樣（AI 伺服器收到 980），沒寫 data-cw 的就是預設 1180
    svg.style.minWidth = ((+svg.dataset.cw || CW)) + 'px';
  }

  window.ThemeDiagrams = T;
  window.ThemeDiagrams.fit = fit;
})();
