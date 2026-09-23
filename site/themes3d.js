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
  /* ★ 2026-09-23：新零件庫要畫剖面（onXZ）與直接算螢幕座標（P3），所以多取這兩支；
     同時**拿掉 cells** —— 它會自動加 `lit pulse`，正是 Andy 講過三次的「螢光感太重」的來源。*/
  const { STYLE, px, py, P3, onTop, onXZ, box, cyl, panel, wire } = D;

  const CW = 1180, PADX = 22, GAPX = 12;
  const ART_Y = 214;          // 3D 物件站的地面線
  const BAND_Y = 76;          // 上游／中游／下游 標題列
  const CAP_Y = 256;          // 站點標題
  /* 個股標籤的起點不再寫死（原本是 300）：2026-09-23 每一格多了第三行「圖：…」，
     起點改成由 chainScene 依實際的說明行數算（CY），不然第三行會直接撞上標籤。*/
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
    /* ★ 2026-09-23：畫布寬可以自己決定，理由跟爆炸圖那邊一樣 ——
       1440 螢幕上題材頁放圖的那一欄只有 996px，1180 的畫布永遠要左右滑。
       十七張一起收到 980（Andy 已經在 AI 伺服器那張看過並接受這個做法）。*/
    const CANW = o.cw || CW;
    const W = Math.floor((CANW - PADX * 2 - GAPX * (n - 1)) / n);
    /* 說明行數不再寫死兩行：個股標籤的起點跟著最長的那一格讓開，
       不然第三行「圖：…」會直接撞上標籤（processBar 那個老毛病）。*/
    const nsub = Math.max(2, ...st.map(x => (x.sub || []).length));
    const CY = CAP_Y + 19 + nsub * 17 - 8;
    const slot = (i) => PADX + i * (W + GAPX);
    let maxRows = 1;
    const body = st.map((s, i) => {
      const x = slot(i), cx = x + W / 2;
      const ch = chips(s.codes, x, CY, W); maxRows = Math.max(maxRows, ch.rows);
      const sub = (s.sub || []).map((t, j) => `<text class="sub" x="${x}" y="${CAP_Y + 19 + j * 17}">${esc(t)}</text>`).join('');
      return `<g class="p3 stn" data-part="${s.id}" data-codes="${(s.codes || []).join(',')}"${s.seg ? ` data-seg="${s.seg}"` : ''}>
        <rect class="slot" x="${x - 7}" y="${BAND_Y + 16}" width="${W + 14}" height="${CY - BAND_Y - 12 + ch.rows * CHIP_ROW}" rx="10"/>
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
    const sy = CY + maxRows * CHIP_ROW + 30;
    const H = sy + 82;
    const steps = (o.steps || []).length;
    const sw = steps ? Math.floor((CANW - PADX * 2 - 10 * (steps - 1)) / steps) : 0;
    const strip = (o.steps || []).map((s, i) => {
      const x = PADX + i * (sw + 10);
      return `<g class="p3 step" data-part="${s.p || ''}"><rect class="part f2" x="${x}" y="${sy}" width="${sw}" height="40" rx="8"/>
        <circle class="num" cx="${x + 18}" cy="${sy + 20}" r="10.5"/><text class="nn" x="${x + 18}" y="${sy + 24.5}" text-anchor="middle">${i + 1}</text>
        <text class="lbl" x="${x + 36}" y="${sy + 16}">${esc(s.t)}</text>
        <text class="sub" x="${x + 36}" y="${sy + 32}">${esc(s.s || '')}</text></g>`
        // ★ 2026-09-23：改吃 --dg-accent-2d（「不屬於任何零件」的強調色）。
        // 原本是寫死的青色色碼，在淺色主題下過亮；token 在深淺兩套各有一組值。
        + (i < steps - 1 ? `<path class="flow fast" d="M${x + sw},${sy + 20} L${x + sw + 10},${sy + 20}" stroke="var(--dg-accent-2d)" stroke-width="2"/>` : '');
    }).join('');
    return `<svg class="dg dg3" data-cw="${CANW}" viewBox="0 0 ${CANW} ${H}" width="100%" style="display:block">${STYLE}${AI_STYLE}${MAT_STYLE}
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
      // 沒覆寫版面的圖（其他七張）維持原本寫死的 +26 / −44 —— 虛線位置一格都不能動
      if (!E.MH) {
        const a0 = rowY(i) + 26, b0 = rowY(i + 1) - 44;
        return `<path class="etch" d="M${E.X},${a0} V${b0}" stroke-dasharray="4 7"/>`
          + `<path class="etch" d="M${E.X - 5},${b0 - 9} L${E.X},${b0} L${E.X + 5},${b0 - 9}" fill="none"/>`;
      }
      /* 有覆寫版面的圖（AI 伺服器）零件畫得大，列與列之間只剩十幾 px，虛線硬塞進去不是被切掉
         就是插進下一個零件裡。改成**一條連續的對位軸畫在所有零件後面**（零件是實心的，
         所以只在縫隙看得到），箭頭放在兩個零件中間那個空檔 —— 這才是爆炸圖標準的畫法。*/
      const m = rowY(i) + E.ROW / 2 - 22;
      return `<path class="etch" d="M${E.X - 5},${m - 7} L${E.X},${m + 2} L${E.X + 5},${m - 7}" fill="none"/>`;
    }).join('') + (E.MH ? `<path class="etch" d="M${E.X},${rowY(0) - 22} V${rowY(n - 1) - 22}" stroke-dasharray="4 7"/>` : '');
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
        // ★ 2026-09-23（全題材那一輪）：原本寫死的青色色碼已換成 --dg-accent-2d。
        // 全檔十三筆寫死色碼在這一輪一起清掉，淺色主題下不會再過亮。
        + (i < steps - 1 ? `<path class="flow fast" d="M${x + sw},${sy + 20} L${x + sw + 10},${sy + 20}" stroke="var(--dg-accent-2d)" stroke-width="2"/>` : '');
    }).join('');
    const axis = `<text class="cap" x="${PADX}" y="${E.UNIT_Y || (E.TOP - 58)}">${esc(o.unit || '整機爆炸拆解（由上而下）')}</text>` + guides;
    return `<svg class="dg dg3" data-cw="${W}" viewBox="0 0 ${W} ${H}" width="100%" style="display:block">${STYLE}${AI_STYLE}${MAT_STYLE}${o.style || ''}
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

  /* ================================================================ 零件庫（2026-09-23 全題材改版）
     改版前的問題（Andy 看 AI 伺服器那張時指出的）：五層都是同一塊格子板換五種顏色，
     顏色拿掉就完全一樣。所以這一批的判準只有一句：
       **讀者不點、不轉、關掉文字標籤，也要能從形狀本身認出每一格是什麼零件。**
     每支函式上面那一行寫的就是「它靠什麼被認出來」—— 那是它存在的理由，不是裝飾。

     三條共通規矩：
       1. **不用 D.cells()**。它會自動加 `lit pulse`，那就是改版前「藍色晶片一直在呼吸」的來源
          （Andy 講過三次「螢光感太重」）。自體發光只留給狀態燈（.ai-led）、流體流向（.flow）、
          光纖與光束（.m-beam／.m-fib）。
       2. 顏色一律走 --dg-* token。材料本身有顏色的（鋁、銅、金、鋼、矽、玻璃、陶瓷、樹脂、油）
          用 mat() 換材質，其餘讓 f1/f2/f3 吃環節色 —— 右邊卡片與左邊零件的連動才不會斷。
       3. 等角投影下一個扁平物件的螢幕寬高比上限 ＝ 0.866/0.5 ＝ 1.73；chainScene 的格子在
          980 畫布上只有 177px 寬，所以鏈上的零件模型座標控制在 x,y ∈ ±44、z ≤ 60。 */

  /* ---------------------------------------------------------------- 材質樣式表（2026-09-23）
     為什麼需要它：等角的三個面（f1 頂／f2 右／f3 左）預設吃**環節色**，
     那正是改版前「五層都是同一塊板換五種顏色」的根源。
     但「鋁鰭片」「銅排」「玻璃」「陶瓷套管」「電芯」是靠**材料顏色**被認出來的 ——
     所以這裡讓每個 .m-* 只宣告三個面的顏色，共用 .mt 那一條規則套上去。
     ⚠ 只有「材料本身就有顏色」的東西才脫離環節色，其餘一律留給 f1/f2/f3，
       右邊卡片與左邊零件的連動（點成員 → 圖上同色亮起）才不會斷。
     ⚠ 值全部是 --dg-* token，深淺兩個主題各有一組，所以淺色不會整片變灰。
     ⚠ 這段註解裡不准出現角括號（DECISIONS #231：SVG 裡的 style 會被當標記解析）。*/
  const MAT_STYLE = `<style>
    .dg3 .mt .f1{fill:var(--fa)} .dg3 .mt .f2{fill:var(--fb)} .dg3 .mt .f3{fill:var(--fc)}
    .dg3 .m-al{--fa:var(--dg-alu);--fb:var(--dg-alu-2);--fc:var(--dg-alu-3)}
    .dg3 .m-st{--fa:var(--dg-steel);--fb:var(--dg-steel-2);--fc:color-mix(in srgb,var(--dg-steel-2) 72%,var(--dg-sh0))}
    .dg3 .m-cu{--fa:var(--dg-cu-lit);--fb:var(--dg-cu);--fc:var(--dg-cu-dim)}
    .dg3 .m-au{--fa:var(--dg-au);--fb:color-mix(in srgb,var(--dg-au) 78%,var(--dg-sh0));--fc:color-mix(in srgb,var(--dg-au) 60%,var(--dg-sh0))}
    .dg3 .m-sn{--fa:var(--dg-sn);--fb:var(--dg-ni);--fc:color-mix(in srgb,var(--dg-ni) 70%,var(--dg-sh0))}
    .dg3 .m-ni{--fa:var(--dg-ni);--fb:color-mix(in srgb,var(--dg-ni) 80%,var(--dg-sh0));--fc:color-mix(in srgb,var(--dg-ni) 60%,var(--dg-sh0))}
    .dg3 .m-si{--fa:var(--dg-si);--fb:var(--dg-si-2);--fc:var(--dg-die)}
    .dg3 .m-epi{--fa:color-mix(in srgb,var(--dg-si) 64%,var(--dg-sn));--fb:var(--dg-si);--fc:var(--dg-si-2)}
    .dg3 .m-emc{--fa:color-mix(in srgb,var(--dg-emc) 82%,var(--dg-sn));--fb:var(--dg-emc);--fc:color-mix(in srgb,var(--dg-emc) 74%,var(--dg-sh0))}
    .dg3 .m-pcb{--fa:var(--dg-pcb);--fb:var(--dg-pcb-2);--fc:color-mix(in srgb,var(--dg-pcb-2) 72%,var(--dg-sh0))}
    .dg3 .m-core{--fa:var(--dg-core);--fb:var(--dg-core-2);--fc:color-mix(in srgb,var(--dg-core-2) 72%,var(--dg-sh0))}
    .dg3 .m-abf{--fa:var(--dg-abf);--fb:var(--dg-abf-2);--fc:color-mix(in srgb,var(--dg-abf-2) 74%,var(--dg-sh0))}
    .dg3 .m-pp{--fa:var(--dg-pp);--fb:color-mix(in srgb,var(--dg-pp) 80%,var(--dg-sh0));--fc:color-mix(in srgb,var(--dg-pp) 62%,var(--dg-sh0))}
    .dg3 .m-cloth{--fa:var(--dg-yarn);--fb:var(--dg-weave);--fc:color-mix(in srgb,var(--dg-weave) 72%,var(--dg-sh0))}
    .dg3 .m-cer{--fa:var(--dg-cer);--fb:var(--dg-cer-2);--fc:var(--dg-cer-cut)}
    .dg3 .m-res{--fa:color-mix(in srgb,var(--dg-resin) 82%,var(--dg-sn));--fb:var(--dg-resin);--fc:color-mix(in srgb,var(--dg-resin) 70%,var(--dg-sh0))}
    .dg3 .m-gl{--fa:var(--dg-glass);--fb:color-mix(in srgb,var(--dg-glass) 78%,var(--dg-sh0));--fc:color-mix(in srgb,var(--dg-glass) 60%,var(--dg-sh0))}
    .dg3 .m-gl .part{fill-opacity:.62}
    .dg3 .m-fluid{--fa:var(--dg-cold);--fb:var(--dg-cold-2);--fc:var(--dg-cold-2)}
    .dg3 .m-fluid .part{fill-opacity:.5}
    .dg3 .m-oil{--fa:color-mix(in srgb,var(--dg-oil) 72%,var(--dg-cer));--fb:var(--dg-oil);--fc:color-mix(in srgb,var(--dg-oil) 66%,var(--dg-sh0))}
    .dg3 .m-cell{--fa:color-mix(in srgb,var(--dg-alu) 64%,var(--dg-cu));--fb:color-mix(in srgb,var(--dg-alu-2) 60%,var(--dg-cu));--fc:color-mix(in srgb,var(--dg-alu-3) 62%,var(--dg-cu))}
    .dg3 .m-mag{--fa:color-mix(in srgb,var(--dg-mag) 82%,var(--dg-sn));--fb:var(--dg-mag);--fc:color-mix(in srgb,var(--dg-mag) 70%,var(--dg-sh0))}
    .dg3 .m-wick{--fa:var(--dg-wick);--fb:color-mix(in srgb,var(--dg-wick) 78%,var(--dg-sh0));--fc:color-mix(in srgb,var(--dg-wick) 60%,var(--dg-sh0))}
    .dg3 .m-sol{--fa:var(--dg-sr);--fb:var(--dg-sr-2);--fc:color-mix(in srgb,var(--dg-sr-2) 72%,var(--dg-sh0))}
    .dg3 .m-hv{--fa:color-mix(in srgb,var(--dg-hot) 76%,var(--dg-sn));--fb:var(--dg-hot);--fc:var(--dg-hot-2)}
    .dg3 .m-flex{--fa:var(--dg-mc-flex,color-mix(in srgb,var(--dg-steel) 58%,var(--dg-cu)));--fb:color-mix(in srgb,var(--dg-steel-2) 60%,var(--dg-cu));--fc:color-mix(in srgb,var(--dg-steel-2) 72%,var(--dg-sh0))}
    .dg3 .m-cam{--fa:var(--dg-mc-cam,color-mix(in srgb,var(--dg-steel-2) 72%,var(--dg-el)));--fb:var(--dg-steel-2);--fc:color-mix(in srgb,var(--dg-steel-2) 66%,var(--dg-sh0))}
    .dg3 .m-damp{--fa:color-mix(in srgb,var(--dg-tim) 84%,var(--dg-sn));--fb:var(--dg-tim);--fc:color-mix(in srgb,var(--dg-tim) 68%,var(--dg-sh0))}
    /* 換了材質的零件不吃 --m1/2/3，所以 hover／選取時原本那一階「變亮」會失效。
       在群組上加一點亮度（不是在 .part 上，免得蓋掉它自己的描邊與光暈）——
       這樣「點一格 → 那一格亮起來」在材質零件上也還在，互動一個都沒掉。*/
    .dg3 .p3:hover .mt,.dg3 .p3.sel .mt{filter:brightness(1.1)}
    .dg3 .p3.sel-part .mt{filter:brightness(1.18)}
    /* ---- 線、孔、光：這幾個不是「面」，所以直接給筆畫或填色 ---- */
    .dg3 .m-hole{fill:var(--dg-sh0);fill-opacity:.5;stroke:none}
    .dg3 .m-wind{fill:none;stroke:var(--dg-cu);stroke-width:2.4;stroke-opacity:.9}
    .dg3 .m-ring{fill:none;stroke:var(--dg-alu-2);stroke-width:4.5;stroke-linecap:round}
    .dg3 .m-pipe{fill:none;stroke:var(--dg-cu);stroke-width:5;stroke-linecap:round;stroke-linejoin:round}
    .dg3 .m-cable{fill:none;stroke:var(--dg-resin);stroke-width:3.4;stroke-linecap:round}
    .dg3 .m-hvcable{fill:none;stroke:var(--dg-hot);stroke-width:5;stroke-linecap:round;stroke-opacity:.9}
    .dg3 .m-flexline{fill:none;stroke:var(--dg-cu);stroke-width:1.6;stroke-opacity:.85;stroke-dasharray:5 4}
    .dg3 .m-fib{fill:none;stroke:var(--dg-sw-fiber);stroke-width:1.8;stroke-opacity:.85;stroke-linecap:round}
    .dg3 .m-pull{fill:none;stroke:var(--dg-hot);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}
    .dg3 .m-grating{fill:var(--dg-au);fill-opacity:.85;stroke:none}
    .dg3 .m-eye{fill:none;stroke:var(--dg-sig);stroke-width:1.4;stroke-opacity:.9}
    /* 光束／波束：唯一保留的「自體發光」之一。用實色低透明度，不加 filter，
       科技與閱讀兩種模式都只是一塊半透明的錐形，不會變成電競 RGB。*/
    .dg3 .m-beam{fill:var(--dg-sig);fill-opacity:.26;stroke:var(--dg-sig);stroke-opacity:.45;stroke-width:.8}
  </style>`;

  // 材質外衣：把一組零件包進去就換一種材料色（每個 .m-* 只定義 --fa/--fb/--fc 三個面，規則在 MAT_STYLE）
  const mat = (c, s) => `<g class="mt ${c}">${s}</g>`;
  // 頂面上的孔（螺栓孔、通孔、銑槽）
  const bolt = (pts, r) => pts.map(p => `<circle class="m-hole" cx="${p[0]}" cy="${p[1]}" r="${r || 3}"/>`).join('');
  // 一排圓柱：電芯、套管、電容、滾輪都靠「一排圓的」被認出來
  const cylRow = (x0, y0, dx, dy, z, r, h, n, inner) => {
    let s = '';
    for (let i = 0; i < n; i++) s += cyl(x0 + dx * i, y0 + dy * i, z, r, h, inner || '');
    return s;
  };
  // 接點陣列：載板的 pad、BGA 球墊、陣列天線的貼片（畫在頂面或立面都可以）
  const padArr = (x, y, w, d, nx, ny, cls) => {
    const a = [], cw = w / nx, ch = d / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++)
      a.push(`<rect class="${cls || 'ai-au'}" x="${(x + i * cw + cw * .2).toFixed(1)}" y="${(y + j * ch + ch * .2).toFixed(1)}" width="${(cw * .6).toFixed(1)}" height="${(ch * .6).toFixed(1)}" rx="1"/>`);
    return a.join('');
  };
  // 繞組／線圈：一圈一圈的銅線。看到它就知道是馬達、變壓器、音圈、電感
  const winding = (cx, cy, rx, ry, n, dy) => {
    const a = [];
    for (let i = 0; i < n; i++) a.push(`<ellipse class="m-wind" cx="${cx.toFixed(1)}" cy="${(cy + i * dy).toFixed(1)}" rx="${rx}" ry="${ry}"/>`);
    return a.join('');
  };
  // 垂直面（沿 x 展開）上的蝕刻：onXZ 只回開標籤，所以統一包成這支，免得有人忘了收尾
  const faceXZ = (x0, y0, inner) => onXZ(x0, y0) + inner + '</g>';
  // 錐狀光束／波束：從 a 點打到 b 半徑 r 的圓面上（雷射、天線波束、曝光光路共用）
  const beam = (a, b, r) => `<path class="m-beam" d="M${P3(a[0], a[1], a[2])} L${P3(b[0] - r, b[1] - r, b[2])} L${P3(b[0] + r, b[1] + r, b[2])}Z"/>`;

  /* ---------------- 材料與晶圓 ---------------- */
  // 單晶棒切晶圓：一根帶錐頭的圓柱 ＋ 旁邊切下來的三片薄片（「還是材料」的樣子）
  const dIngot = () => pad(40, 24)
    + mat('m-si', cyl(-16, -4, 0, 19, 46, '') + cyl(-16, -4, 46, 12, 10, ''))
    + mat('m-si', [0, 1, 2].map(i => cyl(18 + i * 3, 10 + i * 9, 2 + i * 3, 16, 2.6, '')).join(''));
  // 晶圓：圓盤 ＋ 棋盤狀晶粒 ＋ 定位缺口（缺口是「這是晶圓不是盤子」的關鍵）
  const dWafer = () => {
    const d = [];
    for (let x = -30; x < 30; x += 10) for (let y = -30; y < 30; y += 10)
      if ((x + 5) * (x + 5) + (y + 5) * (y + 5) < 810) d.push(`<rect class="etch" x="${x}" y="${y}" width="8.4" height="8.4" rx=".6" fill="none"/>`);
    d.push('<path class="etch" d="M-4,-31 l4,7 l4,-7" fill="none"/>');
    return pad(42, 26) + mat('m-si', cyl(0, 0, 0, 32, 6, d.join('')));
  };
  // 磊晶片：晶圓上再長幾層越縮越小的薄膜，邊緣看得到台階（磊晶＝長出來的層）
  const dEpiWafer = () => pad(42, 26) + mat('m-si', cyl(0, 0, 0, 31, 6, ''))
    + [0, 1, 2].map(i => mat('m-epi', cyl(0, 0, 6 + i * 3, 28 - i * 5, 3, i === 2 ? `<circle class="etch" r="16" fill="none"/>` : ''))).join('');
  // 玻纖布捲 ＋ 樹脂桶：一捲帶經緯紋理的布，旁邊一個圓桶（PCB 的原料就是這兩樣）
  const dClothRoll = () => pad(42, 26)
    + mat('m-cloth', cyl(-16, -10, 6, 18, 0, '') + box(-42, -18, 0, 54, 16, 30, ''))
    + mat('m-cloth', faceXZ(-42, -18, `<path class="etch" d="M4,6 H50 M4,14 H50 M4,22 H50 M12,3 V28 M24,3 V28 M36,3 V28 M48,3 V28"/>`))
    + mat('m-res', cyl(26, 20, 0, 15, 32, `<circle class="etch" r="10" fill="none"/>`));
  // 玻璃板：兩片半透明薄板疊著 ＋ 表面斜向高光（透光才像玻璃，實心方塊不像）
  const dGlassPane = () => {
    const hl = [];
    for (let i = 0; i < 4; i++) hl.push(`M${P3(-30 + i * 17, -22, 12)} L${P3(-14 + i * 17, 22, 12)}`);
    return pad(44, 27)
      + mat('m-gl', box(-40, -28, 0, 80, 56, 4, '') + box(-34, -22, 8, 68, 44, 4, ''))
      + `<path class="ai-seam" d="${hl.join(' ')}"/>`;
  };
  // 電纜捲盤：兩片側板夾一捲纜 ＋ 斷面露出的銅芯 ＋ 拉出來的一段（捲盤＝電線電纜）
  const dCableDrum = () => pad(38, 24)
    + mat('m-st', cyl(0, 0, 0, 33, 5, '') + cyl(0, 0, 42, 33, 5, ''))
    + mat('m-cu', cyl(0, 0, 5, 23, 37, ''))
    + mat('m-cu', faceXZ(0, -23, `<path class="etch" d="M-16,10 H16 M-16,18 H16 M-16,26 H16 M-16,34 H16"/>`))
    + `<path class="m-cable" d="M${P3(23, 0, 40)} C${P3(44, 10, 34)} ${P3(50, 26, 16)} ${P3(50, 34, 4)}"/>`;

  /* ---------------- 設備與機台 ---------------- */
  // 濕製程機台：兩個開口藥液槽（看得到液面與流動）＋ 一支門型搬運臂（「濕」就是看得到液面）
  const dWetBench = () => pad(40, 25)
    + box(-42, -26, 0, 84, 52, 24, '')
    + [-38, 4].map(x => box(x, -18, 24, 34, 36, 10, '')
      + mat('m-fluid', box(x + 3, -15, 24, 28, 30, 8, `<path class="ai-chan" d="M${x + 7},-8 H${x + 29} M${x + 7},6 H${x + 29}"/>`))).join('')
    + mat('m-st', box(-4, -34, 34, 8, 8, 26, '') + box(-4, -34, 60, 42, 8, 5, '') + box(30, -34, 34, 8, 8, 26, ''));
  // 雷射加工機：龍門橫樑 ＋ 雷射頭 ＋ 往下收斂的光束打在工作台上（光束就是識別特徵）
  const dLaserTool = () => pad(40, 25)
    + box(-40, -26, 0, 80, 52, 12, grid2(-40, -26, 80, 52, 4, 3))
    + mat('m-al', box(-40, -6, 12, 8, 12, 42, '') + box(32, -6, 12, 8, 12, 42, '') + box(-40, -6, 54, 80, 12, 8, ''))
    + mat('m-st', box(-8, -4, 44, 16, 8, 10, ''))
    + beam([0, 0, 44], [0, 0, 12], 4)
    + `<circle class="ai-led" cx="${px(0, 0).toFixed(1)}" cy="${py(0, 0, 12).toFixed(1)}" r="3"/>`;
  // 壓合機：上下兩片厚壓板 ＋ 四根導柱 ＋ 中間一疊板材 ＋ 往下壓的箭頭（多層板是壓出來的）
  const dPress = () => pad(40, 25)
    + mat('m-st', box(-38, -26, 0, 76, 52, 9, ''))
    + [[-35, -23], [29, -23], [-35, 19], [29, 19]].map(p => mat('m-st', cyl(p[0] + 3, p[1] + 3, 9, 4, 48, ''))).join('')
    + mat('m-pcb', [0, 1, 2, 3].map(i => box(-26, -18, 11 + i * 5, 52, 36, 3.4, '')).join(''))
    + mat('m-st', box(-38, -26, 34, 76, 52, 11, grid2(-38, -26, 76, 52, 3, 2)))
    + `<path class="etch" d="M${px(0, -32).toFixed(1)},${(py(0, -32, 52) - 12).toFixed(1)} v12 m-5,-5 l5,5 l5,-5" fill="none"/>`;
  // 電鍍槽：槽體 ＋ 液面 ＋ 兩根銅陽極棒 ＋ 掛在中間的待鍍板（濕製程的金屬化那一段）
  const dPlateBath = () => pad(38, 24)
    + box(-38, -26, 0, 76, 52, 28, '')
    + mat('m-fluid', box(-34, -22, 8, 68, 44, 18, `<path class="ai-chan" d="M-28,-12 H28 M-28,2 H28 M-28,16 H28"/>`))
    + mat('m-cu', box(-27, -16, 12, 5, 32, 30, '') + box(22, -16, 12, 5, 32, 30, ''))
    + mat('m-pcb', box(-8, -16, 16, 6, 32, 28, ''))
    + wire([[0, -26, 50], [0, -26, 42]], 'flow', 'var(--dg-pwr)', 2.4);
  // 晶圓載具 FOUP：方盒 ＋ 頂部吊環 ＋ 前門 ＋ 裡面一疊晶圓槽（吊環是它最好認的地方）
  const dFoup = () => pad(34, 22)
    + mat('m-res', box(-28, -22, 0, 56, 44, 44, ''))
    + mat('m-res', box(-10, -8, 44, 20, 16, 5, '') + cyl(0, 0, 49, 9, 4, `<circle class="etch" r="5" fill="none"/>`))
    + mat('m-si', faceXZ(-26, 22, [0, 1, 2, 3, 4].map(i => `<rect class="etch" x="6" y="${8 + i * 7}" width="36" height="3" rx="1" fill="none"/>`).join('')))
    + box(-28, 20, 0, 56, 3, 44, '')
    + `<circle class="ai-led" cx="${px(-20, 20).toFixed(1)}" cy="${py(-20, 20, 38).toFixed(1)}" r="2.6"/>`;
  // 精密零件：一片帶螺栓孔的法蘭 ＋ 波紋管 ＋ 一根軸（設備廠上游賣的就是這種東西）
  const dPrecisionPart = () => pad(36, 23)
    + mat('m-st', cyl(0, 0, 0, 29, 7, bolt([[-20, 0], [20, 0], [0, -20], [0, 20], [-14, -14], [14, 14]], 3.2) + `<circle class="etch" r="13" fill="none"/>`))
    + mat('m-st', [0, 1, 2, 3, 4].map(i => cyl(0, 0, 7 + i * 6, i % 2 ? 11 : 15, 5, '')).join(''))
    + mat('m-st', cyl(0, 0, 37, 7, 16, ''));
  // 測試分類機：上方探針卡（一排探針往下）＋ 下方待測晶粒盤 ＋ 側邊出料軌道（封測那一段）
  const dTestHandler = () => pad(38, 24)
    + box(-38, -24, 0, 76, 48, 16, '')
    + mat('m-al', box(-24, -16, 24, 44, 34, 12, grid2(-24, -16, 44, 34, 3, 2)))
    + [[-14, -8], [0, -8], [14, -8], [-14, 6], [0, 6], [14, 6]]
      .map(p => `<path class="ai-seam" d="M${P3(p[0], p[1], 24)} L${P3(p[0], p[1], 19)}"/>`).join('')
    + mat('m-si', box(-20, -12, 16, 36, 26, 3, padArr(-20, -12, 36, 26, 4, 3, 'ai-seam')))
    + mat('m-st', box(30, -6, 16, 24, 12, 4, ''));
  // 晶圓廠：無塵室廠房 ＋ 屋頂一整排風機 ＋ 側面管線橋（資本支出最後蓋成的樣子）
  const dFab = () => pad(42, 26)
    + box(-42, -28, 0, 84, 56, 30, '')
    + box(-38, -24, 30, 76, 48, 5, '')
    + [0, 1, 2].map(i => [0, 1].map(j => cyl(-26 + i * 26, -12 + j * 24, 35, 8, 5, blades(6, 6))).join('')).join('')
    + mat('m-st', cyl(-40, 22, 30, 4, 18, '') + box(-56, 18, 46, 18, 8, 5, ''))
    + aiFace(-38, 28, 2, [0, 1, 2].map(i => `<rect class="ai-port" x="${14 + i * 22}" y="4" width="14" height="12" rx="1"/>`).join(''));

  /* ---------------- 晶片、封裝與板 ---------------- */
  // 裸晶盤：切割後的晶粒一顆一顆排在圓框膜上（顆粒製造＝還沒封裝的「一顆一顆」）
  const dDieTray = () => {
    let s = '';
    for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++)
      if (i * i + j * j <= 5) s += box(i * 13 - 5, j * 13 - 5, 4, 10, 10, 3.4, '');
    return pad(40, 25) + mat('m-st', cyl(0, 0, 0, 36, 4, '')) + mat('m-si', s);
  };
  // CoWoS 封裝：中央大邏輯晶粒 ＋ 兩側各四疊 HBM ＋ 底下矽中介層 ＋ 一排錫球（見 vaPackage）
  const dCowosPkg = () => pad(44, 27)
    + mat('m-pcb', box(-42, -28, 0, 84, 56, 5, trace(-42, -28, 84, 56, 4)))
    + aiBalls(-34, 27, 34, 27, 9)
    + mat('m-si', box(-36, -23, 5, 72, 46, 3, ''))
    + mat('m-emc', box(-11, -16, 8, 22, 32, 11, grid2(-11, -16, 22, 32, 2, 3)))
    + [[-32, -20], [-21, -20], [-32, 2], [-21, 2], [14, -20], [25, -20], [14, 2], [25, 2]]
      .map(p => mat('m-si', aiPile(p[0], p[1], 8, 9, 18, 4, 2.2, .9))).join('');
  // 封裝成品：載板 ＋ 金屬上蓋 ＋ 底部整排錫球（有上蓋＝封裝好了，跟裸露的封裝分得開）
  const dSubstrateBga = () => pad(44, 27)
    + mat('m-pcb', box(-40, -28, 0, 80, 56, 6, ''))
    + aiBalls(-32, 27, 32, 27, 9) + aiBalls(38, -20, 38, 20, 7)
    + mat('m-al', box(-34, -22, 6, 68, 44, 10, ''))
    + mat('m-au', onTop(6, aiGold(-32, 24, 60, 5, 10)));
  // 控制 IC：方形黑體 ＋ 四邊露出的引腳 ＋ 第一腳圓點（QFN 的樣子）
  const dQfnChip = () => {
    const pins = [];
    for (let i = 0; i < 5; i++) {
      pins.push(box(-22 + i * 10, -30, 1, 7, 4, 4, ''), box(-22 + i * 10, 26, 1, 7, 4, 4, ''),
        box(-30, -22 + i * 10, 1, 4, 7, 4, ''), box(26, -22 + i * 10, 1, 4, 7, 4, ''));
    }
    return pad(36, 23)
      + mat('m-emc', box(-26, -26, 0, 52, 52, 12, `<circle class="ai-seam" cx="-18" cy="-18" r="4" fill="none"/>`))
      + mat('m-sn', pins.join(''));
  };
  // HBM 堆疊：一疊薄晶粒（層與層之間留得出接縫）＋ 貫穿的 TSV 銅柱 ＋ 底下邏輯基底
  const dHbmStack = () => pad(36, 23)
    + mat('m-pcb', box(-30, -24, 0, 60, 48, 5, ''))
    + mat('m-si', box(-26, -20, 5, 52, 40, 5, '') + aiPile(-24, -18, 10, 48, 36, 8, 3.4, 1.4))
    + [[-14, -8], [0, 4], [12, -10]].map(p => wire([[p[0], p[1], 5], [p[0], p[1], 48]], '', 'var(--dg-cu)', 2)).join('');
  // 記憶體模組：一條長板 ＋ 一排顆粒 ＋ 板緣金手指（長條加金手指＝插進插槽的模組）
  const dDimm = () => pad(44, 26)
    + mat('m-pcb', box(-44, -6, 0, 88, 12, 28, ''))
    + mat('m-emc', [0, 1, 2, 3].map(i => box(-36 + i * 19, -7, 8, 14, 2, 13, '')).join(''))
    + mat('m-au', faceXZ(-44, -6, aiGold(8, 1, 72, 5, 14) + `<rect class="ai-seam" x="34" y="0" width="5" height="7" fill="none"/>`));
  // CCL 銅箔基板：上下兩片銅箔夾著膠片的三明治，側邊看得出三層（單層板畫不出這個剖面）
  const dCcl = () => pad(44, 27)
    + mat('m-cu', box(-40, -28, 0, 80, 56, 3, ''))
    + mat('m-pp', box(-40, -28, 3, 80, 56, 9, ''))
    + mat('m-cu', box(-40, -28, 12, 80, 56, 3, ''))
    + mat('m-pp', faceXZ(-40, 28, `<path class="etch" d="M4,4 H66 M4,9 H66 M14,3 V14 M30,3 V14 M46,3 V14 M62,3 V14"/>`))
    + mat('m-cu', box(-32, -20, 15, 24, 16, 2.4, '') + box(6, 4, 15, 24, 16, 2.4, ''));
  // ABF 載板：厚核心層 ＋ 往上兩階增層 ＋ 頂面晶片接點陣列 ＋ 貫穿核心的銅柱
  const dAbfSub = () => pad(42, 26)
    + mat('m-core', box(-38, -26, 0, 76, 52, 12, ''))
    + mat('m-abf', box(-34, -23, 12, 68, 46, 4, '') + box(-30, -20, 16, 60, 40, 4, ''))
    + mat('m-au', onTop(20, padArr(-22, -14, 44, 28, 6, 4)))
    + [[-28, -20], [0, 0], [26, 18]].map(p => wire([[p[0], p[1], 0], [p[0], p[1], 20]], '', 'var(--dg-cu)', 1.4)).join('');
  // TGV 玻璃通孔：玻璃板打滿貫穿孔，其中幾個孔壁已經鍍上銅（玻璃基板的門檻就在這）
  const dTgvPane = () => pad(44, 27)
    + mat('m-gl', box(-40, -28, 0, 80, 56, 10, holes(-40, -28, 80, 56, 7, 5, 2.6)))
    + [[-24, -16], [-4, 0], [18, 12], [6, -18]].map(p => mat('m-cu', cyl(p[0], p[1], 0, 3.4, 10, ''))).join('');
  // 軟板 FPC：一條彎折起來的薄帶 ＋ 兩端連接器（會彎＝軟板，硬板畫不出這個）
  const dFpc = () => {
    const P = [[-40, 0, 4], [-18, 0, 4], [-2, 0, 22], [16, 0, 22], [30, 0, 8], [42, 0, 8]];
    const up = P.map(p => P3(p[0], p[1] - 9, p[2])).join('L');
    const dn = P.slice().reverse().map(p => P3(p[0], p[1] + 9, p[2])).join('L');
    return pad(38, 22)
      + `<path class="part f2" d="M${up}L${dn}Z"/>`
      + `<path class="m-flexline" d="M${P.map(p => P3(p[0], p[1], p[2] + .8)).join('L')}"/>`
      + mat('m-emc', box(-46, -11, 4, 9, 22, 7, '') + box(40, -11, 8, 9, 22, 7, ''));
  };
  // 手機主機板：板子 ＋ 開蓋的屏蔽罩 ＋ 接出去的軟板（屏蔽罩＋軟板＝手機板，不是伺服器板）
  const dSlpBoard = () => pad(42, 26)
    + mat('m-pcb', box(-38, -26, 0, 76, 52, 5, trace(-38, -26, 76, 52, 4)))
    + mat('m-al', box(-32, -20, 5, 34, 26, 8, grid2(-32, -20, 34, 26, 2, 2)))
    + mat('m-emc', box(4, -20, 5, 24, 20, 7, '') + box(4, 4, 5, 24, 14, 5, ''))
    + mat('m-al', box(-32, 8, 5, 30, 12, 4, ''))
    + `<path class="m-flexline" d="M${P3(28, 10, 6)} L${P3(46, 10, 6)} L${P3(54, 10, 16)}"/>`;

  /* ---------------- 設計、IP 與高速介面 ---------------- */
  // 矽智財積木：幾塊帶凸榫的方塊拼在底板上（IP ＝ 買現成的積木來拼，不是自己畫每一顆電晶體）
  const dIpBlocks = () => {
    const B = [[-34, -24, 28, 22, 14], [-2, -24, 30, 20, 10], [-34, 2, 26, 22, 18], [-2, 0, 32, 24, 12]];
    return pad(40, 25) + box(-40, -30, 0, 80, 62, 4, grid2(-40, -30, 80, 62, 6, 5))
      + B.map(b => box(b[0], b[1], 4, b[2], b[3], b[4], '') + box(b[0] + b[2] / 2 - 4, b[1] + b[3], 4, 8, 4, b[4] * .5, '')).join('');
  };
  // 晶片佈局圖：一塊晶片上劃分出大小不一的功能區 ＋ 四邊一圈 I/O（設計服務交出去的東西）
  const dFloorplan = () => {
    const io = [];
    for (let i = 0; i < 6; i++) io.push(`<rect class="ai-au" x="${-34 + i * 12}" y="-31" width="8" height="3" rx="1"/><rect class="ai-au" x="${-34 + i * 12}" y="28" width="8" height="3" rx="1"/>`);
    return pad(42, 26)
      + mat('m-si', box(-38, -28, 0, 76, 56, 6, ''))
      + [[-32, -22, 28, 22], [2, -22, 30, 16], [-32, 4, 20, 20], [-8, -2, 18, 26], [14, -2, 20, 12], [14, 12, 20, 12]]
        .map(r => box(r[0], r[1], 6, r[2], r[3], 4, grid2(r[0], r[1], r[2], r[3], 2, 2))).join('')
      + mat('m-au', onTop(6, io.join('')));
  };
  // 高速介面：晶片邊緣拉出四對成雙的差動走線 ＋ 一個眼圖（「成對」是 SerDes 的識別特徵）
  const dSerdes = () => {
    const a = [];
    for (let i = 0; i < 4; i++) { const y = -14 + i * 9; a.push(`M-4,${y} H32 M-4,${y + 3} H32`); }
    return pad(40, 25)
      + mat('m-pcb', box(-38, -26, 0, 76, 52, 5, ''))
      + mat('m-emc', box(-32, -16, 5, 26, 30, 10, grid2(-32, -16, 26, 30, 2, 2)))
      + mat('m-cu', onTop(5, `<path class="etch" d="${a.join(' ')}"/>`))
      + `<path class="m-eye" d="M${px(22, 22).toFixed(1)},${py(22, 22, 26).toFixed(1)} q9,-11 18,0 q-9,11 -18,0Z"/>`;
  };

  /* ---------------- 光通訊 ---------------- */
  // 雷射二極體：TO 金屬罐 ＋ 三根接腳 ＋ 前方發散的光束（會發光的那一顆）
  const dLaserDiode = () => pad(32, 21)
    + mat('m-st', cyl(0, 0, 6, 18, 4, '') + cyl(0, 0, 10, 14, 20, `<circle class="etch" r="8" fill="none"/>`))
    + mat('m-st', [-8, 0, 8].map(x => cyl(x, 0, -14, 2.2, 20, '')).join(''))
    + beam([0, 0, 30], [0, -40, 44], 13)
    + `<circle class="ai-led" cx="${px(0, 0).toFixed(1)}" cy="${py(0, 0, 30).toFixed(1)}" r="3.4"/>`;
  // 光引擎：晶片上蛇行的光波導 ＋ 兩端光柵耦合器 ＋ 側面接出去的光纖（波導＝矽光子）
  const dPhotonicDie = () => pad(40, 25)
    + mat('m-si', box(-36, -26, 0, 72, 52, 7, ''))
    + mat('m-si', onTop(7, `<path class="ai-chan" d="M-30,-20 H10 q10,0 10,10 t-10,10 H-30 q-10,0 -10,10 t10,10 H26"/>`
      + `<circle class="m-grating" cx="-30" cy="-20" r="4"/><circle class="m-grating" cx="26" cy="20" r="4"/>`))
    + `<path class="m-fib" d="M${P3(36, 20, 7)} L${P3(58, 30, 12)} L${P3(76, 30, 6)}"/>`
    + `<path class="m-fib" d="M${P3(36, 14, 7)} L${P3(58, 24, 16)} L${P3(76, 24, 10)}"/>`;
  // 光收發模組：長方鋁殼 ＋ 前端兩個光口與插著的光纖 ＋ 後端金手指 ＋ 拉環（拉環最好認）
  const dOsfp = () => pad(42, 24)
    + mat('m-al', box(-42, -14, 0, 74, 28, 16, grid2(-42, -14, 74, 28, 5, 2)))
    + mat('m-al', box(32, -12, 2, 8, 24, 12, ''))
    + mat('m-res', cyl(38, -5, 8, 4, 7, '') + cyl(38, 5, 8, 4, 7, ''))
    + `<path class="m-fib" d="M${P3(42, -5, 12)} L${P3(66, -14, 20)}"/><path class="m-fib" d="M${P3(42, 5, 12)} L${P3(66, 6, 20)}"/>`
    + mat('m-au', faceXZ(-42, -14, aiGold(2, 1, 20, 5, 6)))
    + `<path class="m-pull" d="M${P3(-42, -12, 8)} L${P3(-58, -12, 8)} L${P3(-58, 12, 8)} L${P3(-42, 12, 8)}"/>`;
  // 交換器：1U 機箱 ＋ 前面板兩排埠 ＋ 插上去的光纖（一整排埠＝網通，不是又一台伺服器）
  const dSwitchBox = () => {
    const ports = [];
    for (let r = 0; r < 2; r++) for (let i = 0; i < 10; i++)
      ports.push(`<rect class="ai-port" x="${(5 + i * 6.6).toFixed(1)}" y="${3 + r * 7}" width="5" height="5" rx=".8"/>`);
    ports.push('<circle class="ai-led" cx="71" cy="9" r="2.4"/>');
    return pad(42, 25)
      + box(-42, -20, 0, 84, 40, 5, '')
      + box(-42, -20, 5, 84, 40, 18, grid2(-42, -20, 84, 40, 5, 2))
      + aiFace(-42, 20, 5, ports.join(''))
      + [0, 1, 2].map(i => `<path class="m-fib" d="M${px(-30 + i * 16, 20).toFixed(1)},${py(-30 + i * 16, 20, 12).toFixed(1)} c-6,16 -18,20 -30,${26 + i * 6}"/>`).join('');
  };
  // 相位陣列天線：一整片規則的貼片陣列 ＋ 背面饋線 ＋ 斜出去的波束（陣列＝相位陣列）
  const dPhaseArray = () => pad(40, 25)
    + mat('m-pcb', box(-38, -30, 0, 76, 60, 6, ''))
    + mat('m-au', onTop(6, padArr(-34, -26, 68, 52, 5, 4)))
    + mat('m-cu', faceXZ(-38, 30, `<path class="etch" d="M6,2 H60 M20,2 V6 M40,2 V6"/>`))
    + beam([0, 0, 6], [-16, -16, 66], 24);
  // 用戶終端 CPE：一片方形平板天線 ＋ 斜撐底座 ＋ 一條電源線（家裡那一台）
  const dCpe = () => pad(34, 22)
    + mat('m-res', panel(-28, -4, 24, 56, 42, 6, grid2(0, 0, 56, 42, 5, 4)))
    + mat('m-st', box(-6, -2, 0, 12, 22, 26, '') + box(-20, 12, 0, 40, 10, 5, ''))
    + wire([[20, 17, 3], [46, 28, 3]], 'flow slow', 'var(--dg-pwr)', 2)
    + beam([0, -4, 62], [0, -44, 86], 22)
    // 旁邊那台是家用路由（sub 寫的就是「終端設備與家用路由」）：單一片天線又瘦又高，
    // fit() 縮完只剩 72px 寬，右邊留一大片白；補上這台才填得滿，語意也對得上。
    + aiShift(112, mat('m-res', box(-18, -14, 0, 36, 28, 16, ''))
      + aiFace(-18, 14, 0, `<rect class="ai-port" x="4" y="3" width="8" height="5" rx="1"/><rect class="ai-port" x="15" y="3" width="8" height="5" rx="1"/><circle class="ai-led" cx="27" cy="6" r="2"/>`)
      + mat('m-st', cyl(-12, -14, 16, 2, 20, '') + cyl(12, -14, 16, 2, 20, '')));
  // 衛星本體：方形艙體 ＋ 兩片展開的太陽翼 ＋ 底下碟型天線與打向地面的波束（太陽翼＝衛星）
  const dSatellite = () => pad(34, 22)
    + box(-16, -16, 30, 32, 32, 24, grid2(-16, -16, 32, 32, 2, 2))
    + mat('m-sol', panel(-62, -7, 38, 44, 16, 3, grid2(0, 0, 44, 16, 5, 2)) + panel(18, -7, 38, 44, 16, 3, grid2(0, 0, 44, 16, 5, 2)))
    + mat('m-al', cyl(0, 0, 22, 13, 8, `<circle class="etch" r="7" fill="none"/>`) + cyl(0, 0, 18, 4, 6, ''))
    + beam([0, 0, 18], [0, 0, -34], 26);

  // 射頻模組：掀開一半的金屬屏蔽罩 ＋ 裡面的功率放大器與濾波器 ＋ 同軸接頭（屏蔽罩＝射頻）
  const dRfModule = () => pad(38, 24)
    + mat('m-pcb', box(-36, -24, 0, 72, 48, 5, trace(-36, -24, 72, 48, 3)))
    + mat('m-emc', box(-28, -16, 5, 20, 16, 8, '') + box(-4, -16, 5, 14, 12, 6, ''))
    + mat('m-cer', cylRow(-24, 8, 13, 0, 5, 5, 12, 3, `<circle class="etch" r="3" fill="none"/>`))
    + mat('m-al', box(4, -20, 5, 30, 36, 12, grid2(4, -20, 30, 36, 2, 2)))
    + mat('m-st', cyl(36, 0, 5, 5, 12, '') + cyl(36, 0, 17, 3, 6, ''));

  /* ---------------- 電源、散熱與重電 ---------------- */
  // 電源管理板：小板 ＋ 控制 IC ＋ 一排電感方塊 ＋ 三顆電解電容（電感＋電容＝電源級）
  const dPmicBoard = () => pad(40, 25)
    + mat('m-pcb', box(-38, -22, 0, 76, 44, 5, trace(-38, -22, 76, 44, 3)))
    + mat('m-emc', box(-32, -16, 5, 22, 22, 8, `<circle class="ai-seam" cx="-28" cy="-12" r="3" fill="none"/>`))
    + mat('m-mag', [0, 1, 2, 3].map(i => box(-4 + i * 11, -18, 5, 8, 14, 9, '')).join(''))
    + mat('m-al', cylRow(0, 10, 14, 0, 5, 6, 14, 3, `<path class="etch" d="M-4,0 H4"/>`))
    + wire([[-38, 14, 8], [-58, 14, 8]], 'flow', 'var(--dg-pwr)', 2.4);
  // PSU 電源模組：1U 長盒 ＋ 前面板風扇口與把手 ＋ 內部鰭片與銅排 ＋ 後端金手指
  const dPsuModule = () => pad(44, 25)
    + box(-46, -16, 0, 92, 32, 20, '')
    + mat('m-al', aiFins(-40, -12, 20, 38, 24, 9, 12))
    + mat('m-cu', box(6, -12, 20, 26, 24, 7, ''))
    + aiFace(-46, 16, 0, `<circle class="ai-vent" cx="18" cy="11" r="9"/><path class="ai-vent" d="M9,11 H27 M18,2 V20"/>`
      + `<rect class="ai-port" x="40" y="5" width="30" height="5" rx="1.4"/><circle class="ai-led" cx="78" cy="8" r="2.4"/>`)
    + mat('m-au', faceXZ(-46, -16, aiGold(20, 1, 52, 5, 10)));
  // BBU 電池模組：兩排並聯的圓柱電芯 ＋ 上面的鎳片匯流排 ＋ 保護板 ＋ 正負極柱（極柱＝電池）
  const dBbuPack = () => pad(42, 25)
    + box(-42, -22, 0, 84, 44, 5, '')
    + mat('m-cell', cylRow(-34, -14, 14, 0, 5, 6.2, 24, 6, `<circle class="etch" r="3" fill="none"/>`)
      + cylRow(-34, 2, 14, 0, 5, 6.2, 24, 6, `<circle class="etch" r="3" fill="none"/>`))
    + mat('m-ni', box(-38, -17, 29, 76, 6, 2.4, '') + box(-38, -1, 29, 76, 6, 2.4, ''))
    + mat('m-pcb', box(-38, 12, 29, 76, 8, 3, trace(-38, 12, 76, 8, 1)))
    + mat('m-cu', box(-44, -18, 31, 6, 10, 9, '')) + mat('m-al', box(38, -18, 31, 6, 10, 9, ''))
    + wire([[-41, -13, 40], [-60, -13, 40]], 'flow', 'var(--dg-pwr)', 2.6);
  // 銅匯流排：兩片厚銅排 ＋ 一排螺栓孔 ＋ 陶瓷絕緣支柱（厚、扁、帶孔＝母線，不是電線）
  const dBusbar = () => pad(42, 25)
    + mat('m-cu', box(-44, -16, 14, 88, 12, 6, bolt([[-34, -10], [-6, -10], [22, -10], [38, -10]], 2.8))
      + box(-44, 4, 14, 88, 12, 6, bolt([[-34, 10], [-6, 10], [22, 10], [38, 10]], 2.8)))
    + mat('m-cer', [-34, 0, 34].map(x => cyl(x, -4, 0, 6, 14, '') + cyl(x, -4, 6, 8, 2, '')).join(''))
    + wire([[44, -10, 20], [66, -10, 20]], 'flow', 'var(--dg-pwr)', 3);
  // 供電機櫃：機櫃 ＋ 一層層電源架 ＋ 背面垂直貫穿的兩條銅匯流排（電從側邊垂直送上去）
  const dPowerRack = () => {
    let s = pad(34, 22) + box(-28, -22, 0, 56, 44, 5, '') + box(-28, -22, 5, 6, 44, 76, '') + box(-28, -22, 5, 56, 5, 76, '');
    for (let i = 0; i < 5; i++) {
      const z = 9 + i * 14;
      s += box(-20, -16, z, 46, 32, 10, '')
        + aiFace(-20, 20, z, `<circle class="ai-vent" cx="10" cy="5" r="3.4"/><rect class="ai-port" x="20" y="3" width="16" height="4" rx="1"/><circle class="ai-led" cx="41" cy="5" r="2"/>`);
    }
    s += mat('m-cu', box(24, -20, 6, 5, 10, 74, '') + box(24, -6, 6, 5, 10, 74, '')) + box(-28, -22, 81, 56, 44, 5, '');
    /* 右邊再擺一座「被供電的」IT 機櫃：一座櫃子又高又窄，fit() 會被高度綁住，
       縮完只剩 85px 寬、右邊留一大片白。兩座並排才填得滿，也才看得出來「電是送給整排機櫃的」。*/
    return s + aiShift(150, dRack());
  };
  // 均熱片與熱管：扁平均熱板（切開露出毛細結構）＋ 兩根彎折出去的銅熱管（彎管＝熱管）
  const dVaporChamber = () => {
    const wick = [];
    for (let i = 0; i < 7; i++) wick.push(`M-36,${-22 + i * 7} H36`);
    return pad(42, 26)
      + mat('m-cu', box(-40, -26, 0, 80, 52, 4, '') + box(-40, -26, 8, 80, 52, 4, ''))
      + mat('m-wick', box(-38, -24, 4, 76, 48, 4, `<path class="etch" d="${wick.join(' ')}" stroke-dasharray="3 3"/>`))
      + [0, 1].map(i => `<path class="m-pipe" d="M${P3(-34, -14 + i * 26, 14)} L${P3(20, -14 + i * 26, 14)} L${P3(42, -14 + i * 26, 30)} L${P3(60, -14 + i * 26, 30)}"/>`).join('');
  };
  // 風扇模組：方形扇框 ＋ 四角螺栓孔 ＋ 中央輪轂與扇葉 ＋ 旁邊一組鰭片（框＋輪轂＝風扇）
  const dFanMod = () => pad(38, 24)
    + mat('m-al', box(-30, -30, 0, 60, 60, 14, bolt([[-24, -24], [24, -24], [-24, 24], [24, 24]], 3.4)
      + `<circle class="m-hole" cx="0" cy="0" r="24"/>`))
    + mat('m-al', cyl(0, 0, 6, 9, 10, `<circle class="etch" r="5" fill="none"/>`))
    + onTop(13, blades(22, 7))
    + mat('m-al', aiShift(78, aiFins(-26, -22, 0, 52, 44, 24, 11)));
  // 薄型散熱模組：離心風扇（蝸殼加側向出風口）＋ 扁熱管 ＋ 薄鰭片（跟軸流風扇分得開）
  const dThinCool = () => pad(40, 24)
    + mat('m-al', cyl(-18, 0, 0, 23, 9, `<circle class="etch" r="16" fill="none"/>`))
    + onTop(9, `<g transform="translate(${px(-18, 0).toFixed(1)},${py(-18, 0, 0).toFixed(1)})">${blades(15, 11)}</g>`)
    + mat('m-al', box(-4, -10, 0, 8, 20, 9, ''))
    + mat('m-al', aiFins(6, -12, 0, 30, 24, 10, 10))
    + mat('m-cu', box(-20, -4, 9, 54, 8, 3, ''));
  // 水冷板：表面蛇行流道 ＋ 兩顆快接頭（藍進橘出，語意色在兩個主題都固定）
  const dColdPlate = () => pad(42, 26)
    + box(-40, -30, 0, 80, 60, 5, '')
    + box(-36, -26, 5, 72, 52, 9, aiSerpent(-36, -26, 72, 52, 5))
    + mat('m-st', cyl(-22, -30, 14, 7, 13, '') + cyl(24, -30, 14, 7, 13, '') + cyl(-22, -30, 12, 9, 3, '') + cyl(24, -30, 12, 9, 3, ''))
    + wire([[-22, -30, 27], [-22, -62, 31]], 'flow', 'var(--dg-cold)', 2.8)
    + wire([[24, -62, 31], [24, -30, 27]], 'flow rev', 'var(--dg-hot)', 2.8);
  // CDU：幫浦 ＋ 板式熱交換器鰭片 ＋ 下方一整排快接頭的分歧管（分歧管排是它的識別特徵）
  const dCdu = () => pad(38, 24)
    + box(-36, -24, 0, 72, 48, 18, '')
    + mat('m-st', cyl(-20, -6, 18, 12, 16, `<circle class="etch" r="6" fill="none"/>`) + cyl(-20, -6, 34, 6, 6, ''))
    + mat('m-al', aiFins(6, -16, 18, 26, 30, 18, 10))
    + mat('m-st', box(-36, 24, 22, 72, 5, 7, ''))
    + [0, 1, 2, 3].map(i => mat('m-st', cyl(-26 + i * 18, 26, 29, 4, 7, ''))).join('')
    + wire([[-36, 18, 9], [-60, 18, 9]], 'flow', 'var(--dg-cold)', 2.6)
    + wire([[60, -16, 9], [36, -16, 9]], 'flow rev', 'var(--dg-hot)', 2.6);
  // 液冷機櫃：機櫃 ＋ 側邊兩根垂直分歧管 ＋ 每一層接出去的進回水軟管（有水管＝液冷）
  const dLiquidRack = () => {
    let s = pad(34, 22) + box(-28, -22, 0, 58, 44, 5, '') + box(-28, -22, 5, 6, 44, 78, '') + box(-28, -22, 5, 58, 5, 78, '');
    for (let i = 0; i < 5; i++) {
      const z = 9 + i * 14;
      s += box(-20, -16, z, 48, 32, 10, '')
        + aiFace(-20, 20, z, `<rect class="ai-port" x="6" y="3" width="26" height="4" rx="1"/><circle class="ai-led" cx="41" cy="5" r="2"/>`)
        + wire([[28, -14, z + 5], [38, -14, z + 5]], 'flow', 'var(--dg-cold)', 1.8)
        + wire([[38, 2, z + 5], [28, 2, z + 5]], 'flow rev', 'var(--dg-hot)', 1.8);
    }
    s += mat('m-st', cyl(38, -14, 5, 5, 78, '') + cyl(38, 2, 5, 5, 78, '')) + box(-28, -22, 83, 58, 44, 5, '');
    // 旁邊擺一台 CDU：語意上本來就是一組（水由 CDU 送進機櫃），版面上也補掉右邊那片白
    return s + aiShift(160, dCdu());
  };
  // 變壓器：油箱 ＋ 兩側散熱片 ＋ 頂上三根陶瓷套管（三根套管一眼就是變壓器）
  const dTransformer = () => pad(36, 23)
    + mat('m-oil', box(-30, -22, 0, 60, 44, 40, grid2(-30, -22, 60, 44, 2, 2)))
    + mat('m-st', aiFins(-36, -20, 4, 6, 40, 32, 2, 2.6) + aiFins(30, -20, 4, 6, 40, 32, 2, 2.6))
    + mat('m-cer', [-16, 0, 16].map(x => cyl(x, 0, 40, 5, 9, '') + cyl(x, 0, 49, 7, 3, '') + cyl(x, 0, 52, 6, 3, '') + cyl(x, 0, 55, 5, 4, '')).join(''))
    + wire([[30, 18, 20], [54, 18, 20]], 'flow', 'var(--dg-pwr)', 2.4);
  // 開關配電盤：三個並排的櫃體 ＋ 面板儀表與操作把手 ＋ 頂部銅母線槽（一排櫃＋把手＝配電盤）
  const dSwitchgear = () => {
    let s = pad(40, 24) + box(-42, -18, 0, 84, 36, 5, '');
    for (let i = 0; i < 3; i++) {
      const x = -42 + i * 28;
      s += box(x, -18, 5, 27, 36, 46, '')
        + aiFace(x, 18, 5, `<circle class="ai-vent" cx="8" cy="34" r="5"/><rect class="ai-port" x="15" y="30" width="8" height="8" rx="1"/>`
          + `<rect class="ai-port" x="6" y="16" width="16" height="6" rx="1"/><circle class="ai-led" cx="19" cy="41" r="2"/><path class="ai-vent" d="M6,8 h16"/>`);
    }
    return s + mat('m-cu', box(-42, -20, 51, 84, 8, 6, '')) + wire([[42, -16, 54], [64, -16, 54]], 'flow', 'var(--dg-pwr)', 2.4);
  };
  // 大型馬達：帶散熱筋的圓柱機殼 ＋ 前端端蓋與伸出的軸 ＋ 上方接線盒 ＋ 底座（接線盒＋底座＝重電）
  const dBigMotor = () => {
    const ribs = [];
    // ⚠ x 要收在圓柱半徑內（±18），沿 ±24 畫會超出表面，變成幾條飄在旁邊的直線（2026-09-23 實測）
    for (let i = 0; i < 7; i++) ribs.push(`<path class="ai-seam" d="M${P3(-18 + i * 6, -18, 14)} L${P3(-18 + i * 6, -18, 46)}"/>`);
    return pad(38, 24)
      + mat('m-al', cyl(0, 0, 10, 24, 40, `<circle class="etch" r="16" fill="none"/>`))
      + ribs.join('')
      + mat('m-st', cyl(0, 0, 50, 20, 5, bolt([[-12, 0], [12, 0], [0, -12], [0, 12]], 2.6)) + cyl(0, 0, 55, 7, 15, ''))
      + mat('m-st', box(-34, -6, 0, 68, 12, 10, bolt([[-28, 0], [28, 0]], 3)))
      + box(-12, -30, 38, 24, 14, 13, '')
      + wire([[0, -30, 45], [0, -54, 45]], 'flow', 'var(--dg-pwr)', 2.4);
  };
  // 機電統包／變電站：一排戶外機櫃 ＋ 儲能櫃 ＋ 架空管線橋（工程現場的樣子）
  const dSubstation = () => pad(42, 26)
    + box(-44, -26, 0, 88, 52, 5, '')
    + [0, 1, 2].map(i => box(-40 + i * 27, -20, 5, 24, 24, 28, grid2(-40 + i * 27, -20, 24, 24, 1, 2))
      + aiFace(-40 + i * 27, 4, 5, `<rect class="ai-port" x="5" y="16" width="14" height="6" rx="1"/><circle class="ai-led" cx="18" cy="7" r="2"/>`)).join('')
    + mat('m-st', box(4, 10, 5, 40, 14, 22, grid2(4, 10, 40, 14, 3, 1)))
    + aiFace(4, 24, 5, `<rect class="ai-port" x="5" y="12" width="12" height="5" rx="1"/><rect class="ai-port" x="21" y="12" width="12" height="5" rx="1"/><circle class="ai-led" cx="30" cy="4" r="2"/>`)
    + mat('m-st', cyl(-38, -24, 33, 3, 15, '') + cyl(34, -24, 33, 3, 15, '') + box(-38, -26, 48, 72, 5, 4, ''))
    + wire([[-44, 16, 20], [-64, 16, 20]], 'flow', 'var(--dg-pwr)', 2.6);
  // 機櫃（通用）：兩根立柱 ＋ 一層層托盤 ＋ 每層把手與一顆狀態燈（看得出是很多台疊起來）
  const dRack = () => {
    const RX = -28, RY = -22, RW = 56, RD = 44;
    let s = pad(32, 21) + box(RX, RY, 0, RW, RD, 6, '') + box(RX, RY, 6, 6, RD, 78, '')
      + box(RX + RW - 6, RY, 6, 6, RD, 78, '') + box(RX, RY, 6, RW, 5, 78, '');
    for (let i = 0; i < 6; i++) {
      const z = 10 + i * 12;
      s += box(RX + 6, RY + 5, z, RW - 12, RD - 9, 8, '')
        + aiFace(RX + 6, RY + RD - 4, z, `<rect class="ai-port" x="4" y="2" width="14" height="4" rx="1"/><circle class="ai-led" cx="${RW - 20}" cy="4" r="2"/>`);
    }
    return s + box(RX, RY, 84, RW, RD, 6, '');
  };

  // 機櫃＋筆電並排：用在「伺服器與 PC」那一格。單獨一座機櫃又瘦又高，
  // 縮到格子裡只剩 78px 寬、兩邊各留一大塊白；並排才填得滿，也才對得上那一格的標題。
  // ⚠ aiShift 只往右推，整組的重心會偏右 —— 不往左搬回一半，最後一格會頂出畫布右緣
  //   （2026-09-23 實測：右邊溢出 80px）。外面那層 aiShift 就是在做這件事。
  const dRackPc = () => aiShift(-73, dRack() + aiShift(124, dLaptop()));

  /* ---------------- 機械、機器人與載具 ---------------- */
  // 諧波減速機：外圈剛輪齒 ＋ 薄壁柔輪杯 ＋ 中間橢圓波產生器（橢圓凸輪是它獨有的）
  const dHarmonic = () => {
    const teeth = [];
    for (let i = 0; i < 24; i++) { const t = i * Math.PI / 12; teeth.push(`M${(Math.cos(t) * 25).toFixed(1)},${(Math.sin(t) * 25).toFixed(1)} L${(Math.cos(t) * 30).toFixed(1)},${(Math.sin(t) * 30).toFixed(1)}`); }
    return pad(34, 22)
      + mat('m-st', cyl(0, 0, 0, 31, 16, `<path class="etch" d="${teeth.join(' ')}"/>`))
      + mat('m-flex', cyl(0, 0, 4, 21, 20, `<circle class="etch" r="17" fill="none"/>`))
      + mat('m-cam', onTop(24, `<ellipse class="part f1" rx="16" ry="9"/><ellipse class="etch" rx="8" ry="4.5" fill="none"/>`))
      + mat('m-st', cyl(0, 0, 24, 5, 12, ''));
  };
  // 伺服馬達：機殼 ＋ 露出來的定子繞組 ＋ 前端軸 ＋ 後端編碼器與出線（繞組＋編碼器）
  const dServoMotor = () => pad(32, 21)
    + mat('m-st', cyl(0, 0, 0, 21, 8, ''))
    + winding(px(0, 0), py(0, 0, 10), 18, 10, 5, -5)
    + mat('m-al', cyl(0, 0, 34, 21, 10, `<circle class="etch" r="13" fill="none"/>`))
    + mat('m-st', cyl(0, 0, 44, 6, 15, ''))
    + mat('m-res', cyl(0, 0, -13, 14, 13, `<circle class="etch" r="8" fill="none"/>`))
    + `<path class="m-cable" d="M${P3(13, -13, -4)} L${P3(34, -28, 0)}"/>`;
  // 驅動器：兩側鰭片的外殼 ＋ 面板狀態燈與通訊埠 ＋ 底下一排螺絲端子（端子排＝工業驅動器）
  const dDriver = () => {
    const term = [];
    for (let i = 0; i < 5; i++) term.push(`<rect class="ai-port" x="${4 + i * 7.4}" y="6" width="5" height="5" rx=".8"/>`);
    return pad(34, 22)
      + box(-22, -18, 0, 44, 36, 46, '')
      + mat('m-al', aiFins(-27, -16, 4, 5, 32, 40, 2, 2.4) + aiFins(22, -16, 4, 5, 32, 40, 2, 2.4))
      + aiFace(-22, 18, 0, `<rect class="ai-port" x="6" y="28" width="20" height="9" rx="1"/><circle class="ai-led" cx="33" cy="33" r="2.4"/>` + term.join(''))
      + mat('m-cu', box(-18, 18, 4, 36, 4, 5, ''));
  };
  // 視覺與力覺：雙目相機（兩顆鏡頭）＋ 底下一圈帶螺栓孔的力覺感測環（雙鏡頭＋環）
  const dVisionSensor = () => pad(32, 21)
    + mat('m-st', cyl(0, 0, 0, 20, 12, `<circle class="etch" r="12" fill="none"/>` + bolt([[-13, 0], [13, 0], [0, -13], [0, 13]], 2.4)))
    + mat('m-st', box(-4, -4, 12, 8, 8, 10, ''))
    + box(-30, -12, 22, 60, 22, 16, grid2(-30, -12, 60, 22, 4, 1))
    + mat('m-gl', cyl(-16, -12, 30, 7, 6, `<circle class="etch" r="4" fill="none"/>`) + cyl(16, -12, 30, 7, 6, `<circle class="etch" r="4" fill="none"/>`))
    + `<circle class="ai-led" cx="${px(0, -12).toFixed(1)}" cy="${py(0, -12, 36).toFixed(1)}" r="2.4"/>`;
  // 六軸手臂：底座 ＋ 兩節臂 ＋ 關節圓柱 ＋ 末端夾爪（關節圓柱＋夾爪＝手臂）
  const dRobotArm = () => pad(32, 21)
    + mat('m-st', cyl(-22, 10, 0, 18, 9, ''))
    + cyl(-22, 10, 9, 13, 15, '')
    + box(-27, 4, 24, 12, 12, 32, '')
    + cyl(-21, 10, 56, 9, 10, '')
    + box(-21, 5, 58, 44, 11, 11, grid2(-21, 5, 44, 11, 4, 1))
    + cyl(21, 10, 52, 8, 8, '')
    + mat('m-st', box(19, 6, 38, 8, 9, 14, '') + box(15, 5, 30, 6, 4, 9, '') + box(15, 13, 30, 6, 4, 9, ''));
  // 無刷馬達＋螺旋槳：外轉子杯 ＋ 露出的定子繞組 ＋ 上面兩葉槳（槳＝無人機動力）
  const dPropMotor = () => pad(34, 22)
    + mat('m-al', cyl(0, 0, 0, 6, 8, ''))
    + winding(px(0, 0), py(0, 0, 10), 14, 8, 3, -4)
    + mat('m-al', cyl(0, 0, 14, 17, 13, `<circle class="etch" r="10" fill="none"/>` + bolt([[-9, 0], [9, 0]], 2.4)))
    + onTop(29, `<path class="part f1" d="M-42,-2 q23,-9 42,0 q-23,9 -42,0Z"/><path class="part f1" d="M42,2 q-23,9 -42,0 q23,-9 42,0Z"/>`)
    + mat('m-st', cyl(0, 0, 27, 3.4, 7, ''))
    + `<path class="m-cable" d="M${P3(0, 8, 4)} L${P3(16, 28, 2)}"/>`;
  // 線束與連接器：兩個帶插針的接頭 ＋ 中間紮成一束的線 ＋ 中段束環（一束線＋接頭）
  const dHarness = () => {
    const cab = [];
    for (let i = 0; i < 3; i++) {
      const y = -6 + i * 6;
      cab.push(`<path class="m-cable" d="M${P3(-28, y, 14)} C${P3(-8, y, 24 + i * 2)} ${P3(10, y, 24)} ${P3(30, y, 14)}"/>`);
    }
    return pad(38, 22)
      + mat('m-res', box(-46, -12, 6, 18, 24, 16, padArr(-46, -12, 18, 24, 3, 3, 'ai-port')))
      + mat('m-res', box(30, -12, 6, 18, 24, 16, padArr(30, -12, 18, 24, 3, 3, 'ai-port')))
      + cab.join('')
      + mat('m-res', box(-6, -10, 18, 14, 20, 8, ''));
  };
  // 飛控板：小方板 ＋ 中央 IMU ＋ 四角減震柱 ＋ 外接 GPS 天線（減震柱是飛控的識別特徵）
  const dFlightCtrl = () => pad(36, 23)
    + [[-22, -22], [16, -22], [-22, 16], [16, 16]].map(p => mat('m-damp', cyl(p[0] + 3, p[1] + 3, 0, 5, 8, ''))).join('')
    + mat('m-pcb', box(-26, -26, 8, 52, 52, 4, trace(-26, -26, 52, 52, 4)))
    + mat('m-emc', box(-9, -9, 12, 18, 18, 7, `<circle class="ai-seam" cx="-5" cy="-5" r="2.6" fill="none"/>`))
    + mat('m-res', box(16, 16, 12, 18, 18, 4, '') + cyl(25, 25, 16, 3, 10, ''))
    + `<circle class="ai-led" cx="${px(-18, 18).toFixed(1)}" cy="${py(-18, 18, 12).toFixed(1)}" r="2.4"/>`;
  // 三軸雲台：兩層同心的環 ＋ 中間球形相機（同心環＝雲台，固定相機畫不出這個）
  const dGimbal = () => pad(30, 20)
    + mat('m-al', box(-26, -3, 40, 52, 6, 6, '') + box(-26, -3, 22, 6, 6, 20, '') + box(20, -3, 22, 6, 6, 20, ''))
    + `<path class="m-ring" d="M${P3(-22, 0, 24)} A24,14 0 0 0 ${P3(22, 0, 24)}"/>`
    + cyl(0, 0, 6, 13, 15, `<circle class="etch" r="8" fill="none"/>`)
    + mat('m-gl', cyl(0, -13, 9, 6, 7, `<circle class="etch" r="3.4" fill="none"/>`))
    + `<circle class="ai-led" cx="${px(9, -9).toFixed(1)}" cy="${py(9, -9, 19).toFixed(1)}" r="2"/>`;
  // 四旋翼：中央機身 ＋ 四支機臂 ＋ 四組槳 ＋ 底下吊掛的酬載（四臂對稱＝無人機）
  const dDrone = () => pad(40, 26)
    + box(-13, -13, 14, 26, 26, 12, grid2(-13, -13, 26, 26, 2, 2))
    + mat('m-al', box(11, -4, 18, 26, 8, 4, '') + box(-37, -4, 18, 26, 8, 4, '') + box(-4, 11, 18, 8, 26, 4, '') + box(-4, -37, 18, 8, 26, 4, ''))
    + [[36, 0], [-36, 0], [0, 36], [0, -36]].map(p => mat('m-al', cyl(p[0], p[1], 22, 5, 7, ''))
      + onTop(29, `<g transform="translate(${p[0]},${p[1]})"><path class="part f1" d="M-20,-1.6 q11,-6 20,0 q-11,6 -20,0Z"/><path class="part f1" d="M20,1.6 q-11,6 -20,0 q11,-6 20,0Z"/></g>`)).join('')
    + cyl(0, 0, 4, 7, 10, `<circle class="etch" r="4" fill="none"/>`)
    + mat('m-st', box(-16, -4, 8, 6, 8, 6, '') + box(10, -4, 8, 6, 8, 6, ''));
  // 強固型電腦：無風扇鰭片機殼 ＋ 兩側把手 ＋ 面板上一排圓形軍規連接器（鰭片殼＋圓接頭）
  const dRuggedPc = () => {
    const io = [];
    for (let i = 0; i < 3; i++) io.push(`<circle class="ai-port" cx="${14 + i * 20}" cy="12" r="6"/><circle class="ai-vent" cx="${14 + i * 20}" cy="12" r="3.4"/>`);
    io.push('<circle class="ai-led" cx="62" cy="24" r="2.4"/>');
    return pad(38, 24)
      + box(-34, -20, 0, 68, 40, 26, '')
      + mat('m-al', aiFins(-34, -20, 26, 68, 40, 9, 13))
      + mat('m-st', box(-40, -6, 8, 6, 12, 5, '') + box(34, -6, 8, 6, 12, 5, ''))
      + aiFace(-34, 20, 0, io.join(''));
  };
  // 軍規圓形連接器：圓殼 ＋ 外圈卡榫齒環 ＋ 裡面的插針陣列（卡榫齒環＝軍規，民用接頭沒有）
  const dMilConnector = () => {
    const kn = [];
    for (let i = 0; i < 18; i++) { const t = i * Math.PI / 9; kn.push(`M${(Math.cos(t) * 19).toFixed(1)},${(Math.sin(t) * 19).toFixed(1)} L${(Math.cos(t) * 24).toFixed(1)},${(Math.sin(t) * 24).toFixed(1)}`); }
    const pins = [[0, 0], [-9, 0], [9, 0], [0, -9], [0, 9], [-7, -7], [7, 7], [7, -7], [-7, 7]]
      .map(p => `<circle class="ai-au" cx="${p[0]}" cy="${p[1]}" r="2.6"/>`).join('');
    return pad(30, 20)
      + mat('m-st', cyl(0, 0, 0, 19, 22, '') + cyl(0, 0, 22, 24, 8, `<path class="etch" d="${kn.join(' ')}"/>`))
      + mat('m-res', cyl(0, 0, 30, 16, 4, ''))
      + mat('m-au', onTop(34, pins))
      + `<path class="m-cable" d="M${P3(0, 0, 0)} L${P3(0, 26, -4)}"/>`;
  };
  // 軍機：機身 ＋ 後掠主翼 ＋ 垂尾 ＋ 座艙罩（後掠翼跟客機的平直翼分得開）
  const dPlane = () => pad(42, 25)
    + box(-40, -5, 16, 80, 10, 10, '')
    + `<path class="part f1" d="M${P3(-6, -40, 20)} L${P3(14, -6, 20)} L${P3(14, 6, 20)} L${P3(-6, 40, 20)} L${P3(-18, 40, 20)} L${P3(2, 6, 20)} L${P3(2, -6, 20)} L${P3(-18, -40, 20)}Z"/>`
    + `<path class="part f1" d="M${P3(-38, -16, 20)} L${P3(-28, -5, 20)} L${P3(-28, 5, 20)} L${P3(-38, 16, 20)}Z"/>`
    + panel(-40, -2, 26, 16, 16, 4, '')
    + mat('m-st', cyl(40, 0, 21, 5, 6, `<circle class="etch" r="3" fill="none"/>`))
    + mat('m-gl', box(22, -4, 26, 14, 8, 5, ''));
  // 艦艇：修長船體 ＋ 上層建築 ＋ 桅杆 ＋ 側面貼的相位陣列雷達板（雷達板＝軍艦不是貨船）
  const dShip = () => pad(46, 24)
    + box(-44, -10, 0, 82, 20, 13, '')
    + `<path class="part f1" d="M${P3(-44, -10, 13)} L${P3(38, -10, 13)} L${P3(46, 0, 13)} L${P3(38, 10, 13)} L${P3(-44, 10, 13)}Z"/>`
    + box(-16, -8, 13, 32, 16, 17, grid2(-16, -8, 32, 16, 3, 1))
    + mat('m-al', panel(-14, -9, 17, 14, 10, 2, grid2(0, 0, 14, 10, 3, 2)))
    + mat('m-st', box(-4, -3, 30, 6, 6, 18, '') + box(-10, -3, 44, 18, 6, 3, ''))
    + mat('m-st', box(26, -4, 13, 10, 8, 7, '') + cyl(31, 0, 20, 2.4, 13, ''));
  // 滑板底盤：底盤框 ＋ 中間鋪滿的電池模組 ＋ 前後兩顆驅動馬達 ＋ 四輪（電池鋪滿＝電動車）
  const dEvChassis = () => {
    let cells = '';
    for (let i = 0; i < 5; i++) for (let j = 0; j < 2; j++) cells += box(-38 + i * 15, -18 + j * 18, 14, 12, 15, 9, '');
    return pad(48, 28)
      + [[-32, -26], [32, -26], [-32, 26], [32, 26]].map(p => mat('m-res', cyl(p[0], p[1], 0, 10, 12, `<circle class="etch" r="5" fill="none"/>`))).join('')
      + mat('m-al', box(-44, -22, 8, 88, 44, 6, ''))
      + mat('m-cell', cells)
      // ⚠ 頂板只蓋右半邊：整片蓋上去會把電池模組完全遮住，
    //   而「中間鋪滿電池」正是這一格的識別特徵（2026-09-23 第一版就是這樣被蓋掉的）。
    + mat('m-al', box(2, -22, 23, 42, 44, 3, grid2(2, -22, 42, 44, 3, 2)))
      + mat('m-st', cyl(-32, 0, 10, 11, 14, `<circle class="etch" r="6" fill="none"/>`) + cyl(32, 0, 10, 11, 14, `<circle class="etch" r="6" fill="none"/>`))
      + wire([[-32, -26, 14], [-32, 0, 14]], 'flow', 'var(--dg-pwr)', 2);
  };
  // 逆變器／車載充電器：鋁壓鑄外殼與鰭片 ＋ 三顆功率模組 ＋ 直流母線電容 ＋ 三相出線
  const dInverter = () => pad(40, 25)
    + mat('m-al', box(-38, -24, 0, 76, 48, 10, '') + aiFins(-38, -26, 10, 76, 5, 8, 12))
    + mat('m-emc', [0, 1, 2].map(i => box(-28 + i * 20, -10, 10, 16, 20, 8, grid2(-28 + i * 20, -10, 16, 20, 1, 2))).join(''))
    + mat('m-al', cylRow(-18, 14, 20, 0, 10, 8, 15, 2, `<path class="etch" d="M-5,0 H5"/>`))
    + mat('m-cu', box(-40, -22, 10, 6, 14, 6, ''))
    + [0, 1, 2].map(i => wire([[38, -14 + i * 12, 14], [60, -14 + i * 12, 14]], 'flow', 'var(--dg-pwr)', 2.6)).join('');
  // 高壓線束與充電槍：槍頭（帶插孔）＋ 兩條粗纜 ＋ 另一端環狀銅端子（充電槍＝電動車線束）
  const dHvHarness = () => {
    const cab = [0, 1].map(i => `<path class="m-hvcable" d="M${P3(-24, -6 + i * 12, 18)} C${P3(0, -6 + i * 12, 28)} ${P3(20, -6 + i * 12, 28)} ${P3(40, -6 + i * 12, 14)}"/>`).join('');
    return pad(38, 22)
      + mat('m-hv', box(-46, -14, 8, 22, 28, 18, padArr(-46, -14, 22, 28, 2, 3, 'ai-port')))
      + mat('m-hv', cyl(-35, 0, 26, 9, 7, ''))
      + cab
      + mat('m-cu', cyl(42, -6, 12, 5, 3, `<circle class="etch" r="2.4" fill="none"/>`) + cyl(42, 6, 12, 5, 3, `<circle class="etch" r="2.4" fill="none"/>`))
      + mat('m-res', box(-8, -12, 24, 14, 24, 7, ''));
  };
  // 沖壓結構件：折邊鈑金 ＋ 一排焊點 ＋ 兩個安裝孔（折邊＋焊點＝沖壓件，實心方塊不是）
  const dStamping = () => {
    const spot = [];
    for (let i = 0; i < 5; i++) spot.push(`<circle class="ai-seam" cx="${-30 + i * 15}" cy="-13" r="2.6" fill="none"/><circle class="ai-seam" cx="${-30 + i * 15}" cy="13" r="2.6" fill="none"/>`);
    return pad(40, 24)
      + box(-40, -22, 0, 80, 4, 10, '') + box(-40, 18, 0, 80, 4, 10, '')
      + `<path class="part f1" d="M${P3(-40, -20, 10)} L${P3(40, -20, 10)} L${P3(40, 20, 10)} L${P3(-40, 20, 10)}Z"/>`
      + onTop(10, bolt([[-26, 0], [26, 0]], 5) + spot.join(''))
      + mat('m-st', box(-10, -8, 10, 20, 16, 6, ''));
  };
  // 車規 MCU 與感測器：一顆貼散熱片的 MCU ＋ 一顆圓柱感測器 ＋ 一個短接頭（車上那三樣）
  const dMcuSensor = () => pad(38, 24)
    + mat('m-pcb', box(-36, -22, 0, 72, 44, 5, trace(-36, -22, 72, 44, 3)))
    + mat('m-emc', box(-30, -14, 5, 26, 26, 8, ''))
    + mat('m-al', box(-28, -12, 13, 22, 22, 3, grid2(-28, -12, 22, 22, 3, 3)))
    + mat('m-st', cyl(12, -8, 5, 9, 15, `<circle class="etch" r="5" fill="none"/>`))
    + mat('m-res', box(6, 8, 5, 22, 12, 9, padArr(6, 8, 22, 12, 3, 1, 'ai-port')));
  // 鏡頭模組：一疊直徑漸變的鏡片 ＋ 鏡筒 ＋ 音圈馬達繞組 ＋ 底下影像感測器（一疊鏡片＝鏡頭）
  const dLensModule = () => pad(30, 20)
    + mat('m-si', box(-20, -20, 0, 40, 40, 5, padArr(-20, -20, 40, 40, 4, 4, 'ai-seam')))
    + mat('m-res', box(-19, -19, 5, 38, 38, 24, ''))
    + winding(px(0, 0), py(0, 0, 14), 17, 9, 3, -5)
    + mat('m-gl', [0, 1, 2, 3].map(i => cyl(0, 0, 29 + i * 5, 14 - i * 2, 4, i === 3 ? `<circle class="etch" r="7" fill="none"/>` : '')).join(''))
    + mat('m-res', cyl(0, 0, 49, 14, 3, ''));
  // 手機整機：機身 ＋ 掀起來的玻璃背蓋 ＋ 露出的電池與主機板 ＋ 三鏡頭（爆開＝組裝那一段）
  const dPhone = () => pad(28, 32)
    + mat('m-al', box(-19, -38, 0, 38, 76, 5, ''))
    + mat('m-cell', box(-15, -6, 5, 30, 30, 7, `<path class="etch" d="M-12,2 H12 M-12,12 H12 M-12,22 H12"/>`))
    + mat('m-pcb', box(-15, -34, 5, 30, 24, 4, trace(-15, -34, 30, 24, 2)))
    + `<path class="ai-seam" d="M${P3(-19, -38, 12)} L${P3(-19, -38, 22)} M${P3(19, 38, 12)} L${P3(19, 38, 22)}"/>`
    + mat('m-gl', box(-19, -38, 22, 38, 76, 3, ''))
    + mat('m-gl', [0, 1, 2].map(i => cyl(-8 + (i % 2) * 11, -28 + Math.floor(i / 2) * 11, 25, 4.4, 3, '')).join(''));
  // 筆電：掀開的螢幕 ＋ 鍵盤面與觸控板（掀開的角度是筆電最好認的輪廓）
  const dLaptop = () => {
    const keys = [];
    for (let i = 0; i < 9; i++) for (let j = 0; j < 4; j++) keys.push(`<rect class="ai-vent" x="${-23 + i * 5.2}" y="${-15 + j * 5.6}" width="4" height="4.4" rx=".6"/>`);
    return pad(42, 26)
      + box(-38, -22, 0, 76, 48, 5, '')
      + onTop(5, `<rect class="ai-port" x="-24" y="-16" width="48" height="24" rx="1.4"/>` + keys.join('')
        + `<rect class="ai-port" x="-10" y="12" width="20" height="10" rx="1.4"/>`)
      + panel(-38, -22, 5, 76, 44, 4, grid2(0, 0, 76, 44, 1, 1));
  };
  // CNC 中框：金屬框 ＋ 銑出來的兩個凹槽與螺絲柱 ＋ 側邊天線斷點（凹槽＋斷點＝中框）
  const dCncCase = () => pad(34, 30)
    + mat('m-al', box(-22, -40, 0, 44, 80, 12, ''))
    + mat('m-al', onTop(12, `<rect class="m-hole" x="-17" y="-35" width="34" height="30" rx="3"/><rect class="m-hole" x="-17" y="2" width="34" height="32" rx="3"/>`
      + bolt([[-19, -37], [19, -37], [-19, 37], [19, 37], [-19, -1], [19, -1]], 2.4)))
    + [-24, 4].map(y => `<path class="ai-seam" d="M${P3(22, y, 0)} L${P3(22, y, 12)} M${P3(22, y + 8, 0)} L${P3(22, y + 8, 12)}"/>`).join('');
  // 主機板：板 ＋ 兩條記憶體插槽 ＋ 供電電感 ＋ 一條 M.2 插槽（插槽＝主機板，不是模組板）
  const dMainboard = () => pad(44, 27)
    + mat('m-pcb', box(-42, -28, 0, 84, 56, 5, trace(-42, -28, 84, 56, 5)))
    + mat('m-res', box(-36, -22, 5, 8, 42, 7, '') + box(-24, -22, 5, 8, 42, 7, ''))
    + mat('m-emc', box(-8, -20, 5, 24, 24, 9, grid2(-8, -20, 24, 24, 2, 2)))
    + mat('m-mag', [0, 1, 2, 3].map(i => box(20, -20 + i * 8, 5, 12, 6, 7, '')).join(''))
    + mat('m-au', onTop(5, aiGold(-14, 12, 34, 7, 8)))
    + mat('m-st', box(-38, 18, 5, 16, 8, 3, ''));
  // 端側 SoC：掀蓋露出分區大小不同的 CPU／GPU／NPU ＋ 底部錫球（三塊不等大＝異質運算）
  const dSocNpu = () => pad(40, 25)
    + mat('m-pcb', box(-34, -26, 0, 68, 52, 5, ''))
    + aiBalls(-26, 25, 26, 25, 8)
    + mat('m-si', box(-28, -21, 5, 56, 42, 5, ''))
    + [[-26, -19, 22, 18], [-26, 2, 22, 16], [0, -19, 26, 24], [0, 8, 26, 10]]
      .map(r => box(r[0], r[1], 10, r[2], r[3], 6, grid2(r[0], r[1], r[2], r[3], 2, 2))).join('')
    + mat('m-emc', box(-32, -23, 14, 6, 46, 4, ''));
  // 端側記憶體與儲存：一顆 LPDDR 疊在基板上（PoP）＋ 一條 M.2 固態硬碟（疊起來＝端側省面積）
  const dMemSsd = () => pad(42, 25)
    + mat('m-pcb', box(-42, -20, 0, 44, 40, 5, ''))
    + mat('m-emc', box(-36, -14, 5, 32, 28, 8, '') + box(-33, -11, 13, 26, 22, 7, grid2(-33, -11, 26, 22, 2, 2)))
    + aiBalls(-36, 15, -4, 15, 6)
    + mat('m-pcb', box(6, -10, 0, 36, 20, 4, ''))
    + mat('m-emc', box(12, -7, 4, 12, 14, 6, '') + box(28, -7, 4, 10, 14, 5, ''))
    + mat('m-au', onTop(4, aiGold(7, -8, 5, 16, 2)));

  /* ★ 爆炸圖的共用版面（2026-09-23）：AI 伺服器那張量出來的一組數字，其餘七張沿用。
     為什麼要沿用而不是各自調：1440 螢幕上題材頁放圖的那一欄只有 996px，
     預設畫布 1180 代表**每一張都要左右滑**；收到 980 才是「一次看完」。
     MW/MH 的比例 212/122＝1.74，貼著等角投影的寬高比上限 1.73，框不會空一半；
     SLOT_MIN 讓右邊五張說明卡等高貼齊，中間不留白條。*/
  const EX980 = { X: 182, TOP: 182, UNIT_Y: 68, ROW: 140, MW: 212, MH: 122, LX: 376, LW: 582, CHIP_DY: 34, SLOT_MIN: 112 };
  /* ================================================================ 十八個題材 */
  const T = {};

  T.cowos = () => chainScene({
    title: 'CoWoS 先進封裝：一顆 AI 加速器怎麼做出來',
    cap: '設計定案 → 投片 → 中介層上把邏輯晶粒與 HBM 拼起來 → 封測上蓋 → 裝到載板與主機板。台廠在每一段都有位置。',
    cw: 980,
    stations: [
      S('equip', 0, '設備與材料', ['暫時鍵合、電鍍、載具', '擴產先反映在這', '圖：藥液槽＋搬運臂'], ['3680', '6187', '3583', '3131'], 'adv_pkg', dWetBench),
      S('design', 0, 'IC 設計與 IP', ['GPU / ASIC 規格定案', '矽智財與設計服務', '圖：晶片功能區佈局'], ['3443', '3661', '3529'], 'ip_eda', dFloorplan, 1.35),
      S('foundry', 1, '晶圓代工', ['3nm / 2nm 邏輯晶粒', 'HBM 基底也在這', '圖：晶圓＋定位缺口'], ['2330'], 'foundry', dWafer, 1.4),
      S('stack', 1, '中介層與 HBM', ['CoWoS：TSV、微凸塊', '一顆 GPU 旁 4–8 顆', '圖：大晶粒＋八疊 HBM'], ['2330', '3711', '2408'], 'adv_pkg', dCowosPkg, 1.3),
      S('pkg', 2, '載板封測出貨', ['ABF 載板、上蓋、燒機', '接到加速卡主機板', '圖：金屬上蓋＋錫球'], ['3037', '8046', '6239', '3711'], 'abf_pcb', dSubstrateBga, 1.3),
    ],
    steps: [{ p: 'design', t: '設計定案', s: 'IP / EDA' }, { p: 'foundry', t: '投片', s: '晶圓製造' }, { p: 'stack', t: '中介層堆疊', s: 'CoWoS' },
    { p: 'pkg', t: '封測上蓋', s: 'OSAT' }, { p: 'pkg', t: '上板', s: '載板 → PCB' }],
  });

  T.hbm_memory = () => chainScene({
    title: 'HBM 與記憶體：從一顆 DRAM 到一條模組',
    cap: 'DRAM 顆粒疊起來用 TSV 打穿變成 HBM；台廠主力在利基型記憶體、控制 IC、模組與封測這幾段。',
    cw: 980,
    stations: [
      S('dram', 0, 'DRAM 顆粒', ['利基型 DRAM 與 NOR', '報價循環是股價主軸', '圖：切好的裸晶排在框上'], ['2408', '2344', '3006', '2337'], 'hbm', dDieTray, 1.4),
      S('stackp', 1, 'TSV 堆疊封裝', ['8–12 層疊起來打通孔', '良率由封測把關', '圖：一疊薄晶粒＋銅柱'], ['2330', '6239', '3711'], 'adv_pkg', dHbmStack, 1.15),
      S('ctrl', 1, '控制 IC 與韌體', ['NAND 控制器與介面', '決定模組規格上限', '圖：四邊出腳的小封裝'], ['8299', '6526'], 'ic_design', dQfnChip, 1.3),
      S('module', 2, '模組與儲存', ['DIMM、SSD、工控記憶體', '出海量最大的一段', '圖：長條板＋金手指'], ['4967', '3260', '5289'], 'hbm', dDimm, 1.25),
      S('server', 2, 'AI 伺服器與 PC', ['模型越大吃越多記憶體', '終端拉貨才是源頭', '圖：機櫃＋端側筆電'], ['6669', '2382'], 'assembly', dRackPc, 0.72),
    ],
    steps: [{ p: 'dram', t: '顆粒製造', s: '2408 / 2344' }, { p: 'stackp', t: '堆疊封裝', s: 'TSV' }, { p: 'ctrl', t: '控制 IC', s: '8299' },
    { p: 'module', t: '模組組裝', s: '4967 / 3260' }, { p: 'server', t: '終端出貨', s: '伺服器 / PC' }],
  });

  T.pcb_ccl = () => chainScene({
    title: '高階 PCB 與 CCL：一片板子是怎麼壓出來的',
    cap: 'PCB 是元件之間的「道路系統」。玻纖布＋樹脂＋銅箔壓成 CCL，再蝕刻、鑽孔、電鍍、壓合成多層板與載板。',
    cw: 980,
    stations: [
      S('glass', 0, '玻纖布與樹脂', ['板材的骨架與黏著', '決定尺寸穩定度', '圖：布捲＋樹脂桶'], ['1815', '1303'], 'ccl', dClothRoll, 1.15),
      S('ccl', 0, 'CCL 銅箔基板', ['樹脂含浸玻纖壓銅箔', '高速低損耗是主戰場', '圖：銅／膠片／銅三明治'], ['2383', '6274', '6213'], 'ccl', dCcl, 1.3),
      S('press', 1, '蝕刻鑽孔壓合', ['層數＝難度', 'AI 板要 20 層以上', '圖：壓板＋導柱＋板疊'], ['3044', '2313', '5469'], 'abf_pcb', dPress),
      S('abf', 1, 'ABF 載板', ['晶片直接坐上去那層', '台廠寡占、看擴產', '圖：核心層＋增層階梯'], ['3037', '8046', '3189'], 'abf_pcb', dAbfSub, 1.3),
      S('fpc', 2, '軟板與終端', ['FPC、軟硬結合板', '伺服器、手機、車用', '圖：彎折的薄帶'], ['6269', '2368'], 'assembly', dFpc, 1.4),
    ],
    steps: [{ p: 'ccl', t: '覆銅板', s: 'CCL 板材' }, { p: 'press', t: '蝕刻', s: '做出線路' }, { p: 'press', t: '鑽孔', s: '微孔加工' },
    { p: 'abf', t: '電鍍', s: '孔壁導通' }, { p: 'abf', t: '壓合', s: '多層疊起' }],
    flowTitle: 'PCB 製作流程（點一格＝點上面那個環節）',
  });

  T.glass_substrate = () => chainScene({
    title: '玻璃基板：下一代封裝載板',
    cap: '玻璃比有機載板更平整、翹曲更小、可做更大尺寸。難的是在玻璃上打出 TGV 通孔並把孔壁鍍上銅。',
    cw: 980,
    stations: [
      S('material', 0, '玻璃與材料', ['玻璃核心、乾膜、銅箔', '目前多半仰賴進口', '圖：兩片透光薄板'], ['4770', '1303', '2383'], 'ccl', dGlassPane, 1.3),
      S('laser', 0, '雷射加工設備', ['打孔設備與治具', '最先吃到訂單那段', '圖：龍門＋往下的光束'], ['6187', '3413', '3680'], 'adv_pkg', dLaserTool),
      S('tgv', 1, 'TGV 玻璃通孔', ['雷射打孔＋蝕刻擴孔', '孔徑與側壁是門檻', '圖：打滿孔、孔壁鍍銅'], ['6187', '3680'], 'adv_pkg', dTgvPane, 1.3),
      S('plating', 1, '金屬化與 RDL', ['孔壁鍍銅、重佈線層', '濕製程設備受惠', '圖：電鍍槽＋陽極棒'], ['3131', '3583'], 'adv_pkg', dPlateBath, 1.2),
      S('pkg', 2, '載板與先進封裝', ['玻璃載板放晶粒', '放量等製程成熟', '圖：上蓋封裝＋錫球'], ['3037', '8046', '6271'], 'abf_pcb', dSubstrateBga, 1.3),
    ],
    steps: [{ p: 'material', t: '玻璃備料', s: '4770 / 1303' }, { p: 'laser', t: '雷射打孔', s: '6187 / 3413' }, { p: 'tgv', t: 'TGV 成孔', s: '蝕刻擴孔' },
    { p: 'plating', t: '電鍍 RDL', s: '3131 / 3583' }, { p: 'pkg', t: '晶片貼裝', s: '2330 / 3711' }],
  });

  T.asic_ip = () => chainScene({
    title: 'ASIC 與矽智財：一顆客製晶片的組成',
    cap: '客戶出規格，設計服務廠把各家 IP（運算核、高速介面、記憶體控制、類比）拼成一顆 SoC，再交給晶圓代工投片。',
    cw: 980,
    stations: [
      S('ip', 0, '矽智財授權', ['RISC-V 核、記憶體 IP', '收授權金＋權利金', '圖：帶凸榫的積木'], ['3529', '6643'], 'ip_eda', dIpBlocks, 1.3),
      S('phy', 0, '高速介面 IP', ['SerDes / PCIe / UCIe', 'chiplet 能不能拼靠它', '圖：成對差動線＋眼圖'], ['4966', '6104', '6415'], 'ip_eda', dSerdes, 1.4),
      S('service', 1, '設計服務 NRE', ['從規格到量產一條龍', '認列跟著專案走', '圖：晶片功能區佈局'], ['3443', '3661'], 'ip_eda', dFloorplan, 1.35),
      S('foundry', 1, '投片：晶圓代工', ['設計定案後的夥伴', '先進製程排隊', '圖：晶圓＋定位缺口'], ['2330'], 'foundry', dWafer, 1.4),
      S('client', 2, '封測與客戶量產', ['封測、模組與出貨', 'CSP 自研晶片是主力', '圖：探針卡＋晶粒盤'], ['3711', '8299', '5269'], 'osat_test', dTestHandler, 1.25),
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
  /* ★ 2026-09-23：AI_STYLE 與 MAT_STYLE 現在由兩種場景**無條件**注入。
     踩過的坑：新零件庫在鏈圖裡也用 .ai-au／.ai-port／.ai-led／.ai-seam，
     但那幾條規則只在 AI_STYLE 裡，而 AI_STYLE 原本只靠 o.style 傳給爆炸圖 ——
     結果鏈圖上的金手指、埠、狀態燈會變成沒有樣式的黑色實心。
     T.ai_server 仍然會再傳一次 o.style，重覆一份規則沒有副作用，所以那張圖一個字都不必動。*/
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
    unit: '整機爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('pmic', 0, '電源管理 IC', ['數位電源控制與轉換', '效率每個百分點都算',
        '圖上：小板上一顆控制 IC、一排電感方塊與三顆電解電容'], ['6415', '3529', '6533'], 'ic_design', dPmicBoard),
      S('psu', 1, 'PSU 電源模組', ['伺服器電源供應器', 'AI 機櫃用量倍增',
        '圖上：1U 長盒，前面板風扇口與把手，內部鰭片與銅排，後端金手指'], ['2308', '6409', '6412'], 'power', dPsuModule),
      S('bbu', 1, 'BBU 備援電池', ['掉電時撐住不當機', '模組化可熱抽換',
        '圖上：兩排並聯圓柱電芯、上面鎳片匯流排、右側保護板與正負極柱'], ['3211', '2489'], 'power', dBbuPack),
      S('busbar', 2, '匯流排與機構件', ['高壓直流送電到每層', '滑軌、連接器與通路',
        '圖上：兩片帶螺栓孔的厚銅排，架在三根陶瓷絕緣支柱上'], ['2059', '3033', '3023'], 'power', dBusbar),
      S('rack', 2, '機櫃與資料中心', ['整櫃供電架構改版', '電力是擴機房的瓶頸',
        '圖上：機櫃裡一層層電源架，背面兩條銅匯流排垂直貫穿'], ['2382', '6669'], 'assembly', dPowerRack),
    ],
    steps: [{ p: 'pmic', t: '電源 IC', s: '6415 / 3529' }, { p: 'psu', t: 'PSU 模組', s: '2308 / 6409' }, { p: 'bbu', t: 'BBU', s: '3211' },
    { p: 'busbar', t: '匯流與機構', s: '2059 / 3023' }, { p: 'rack', t: '機櫃整合', s: '2382 / 6669' }],
  });

  T.thermal = () => explodeScene({
    title: '散熱與液冷：熱從晶片怎麼被帶出機房',
    cap: '單顆 GPU 破千瓦，風冷已經不夠。價值一路從均熱片、風扇往水冷板、快接頭與機櫃 CDU 移動。',
    unit: '整機爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('vc', 0, '均熱片與熱管', ['VC 均熱板、熱管', '風冷世代的主力',
        '圖上：扁平均熱板切開露出毛細結構，兩根銅熱管彎折出去'], ['3653', '6230', '3013'], 'thermal', dVaporChamber),
      S('fan', 0, '風扇與散熱模組', ['前端進氣與機櫃風牆', '風冷仍是多數機種',
        '圖上：方形扇框、四角螺栓孔、中央輪轂與七片扇葉，旁邊一組鰭片'], ['2421', '6230'], 'thermal', dFanMod),
      S('plate', 1, '水冷板 Cold Plate', ['直接貼晶片帶走熱', 'AI 機櫃逐步標配',
        '圖上：板面蛇行流道，兩顆快接頭一藍一橘（進水／出水）'], ['3017', '3324'], 'thermal', dColdPlate),
      S('cdu', 1, 'CDU 與快接頭', ['幫浦、熱交換、分歧管', '漏液是最大風險',
        '圖上：櫃內一顆幫浦、一組熱交換鰭片，下方一排快接頭的分歧管'], ['8996', '2308', '6122'], 'thermal', dCdu),
      S('rack', 2, 'AI 機櫃與機房', ['整櫃液冷與冷卻水', '功耗越高越往這走',
        '圖上：機櫃側邊兩根垂直分歧管，每一層都接出進回水軟管'], ['6669', '2382'], 'assembly', dLiquidRack),
    ],
    steps: [{ p: 'vc', t: '均熱片', s: '3653 / 6230' }, { p: 'plate', t: '水冷板', s: '3017 / 3324' }, { p: 'cdu', t: '快接管件', s: '8996' },
    { p: 'cdu', t: 'CDU', s: '8996 / 2308' }, { p: 'rack', t: '機房冷卻', s: '資料中心' }],
  });

  T.silicon_photonics = () => chainScene({
    title: '矽光子與 CPO：電變成光，再送進機房',
    cap: '上游是化合物磊晶與雷射二極體，中游把光引擎做進交換晶片旁邊（CPO），下游是光收發模組與交換器。',
    cw: 980,
    stations: [
      S('epi', 0, '化合物磊晶', ['砷化鎵、磷化銦基板', '高頻元件的底材', '圖：晶圓上長出的薄膜台階'], ['2455', '8086'], 'optical', dEpiWafer, 1.35),
      S('ld', 0, '雷射二極體 LD', ['把電訊號轉成光', '光纖通訊的心臟', '圖：金屬罐＋三腳＋光束'], ['3081', '8086'], 'optical', dLaserDiode, 1.15),
      S('engine', 1, '光引擎／矽光子', ['調變器與光波導', 'CPO 封到 ASIC 旁', '圖：蛇行波導＋光柵'], ['2330', '4966'], 'optical', dPhotonicDie, 1.3),
      S('module', 1, '光收發模組', ['800G–1.6T 模組', '台廠營收主力', '圖：鋁殼＋拉環＋光口'], ['4979', '4977', '3163', '6442'], 'optical', dOsfp, 1.25),
      S('dc', 2, '交換器與機房', ['交換晶片與叢集網路', '需求來自訓練流量', '圖：一整排埠＋光纖'], ['2345', '5388'], 'switch', dSwitchBox, 1.2),
    ],
    steps: [{ p: 'epi', t: '磊晶材料', s: '2455 / 8086' }, { p: 'ld', t: '雷射元件', s: '3081' }, { p: 'engine', t: '光引擎', s: '2330' },
    { p: 'module', t: '模組組裝', s: '4979 / 4977' }, { p: 'dc', t: '交換器', s: '2345' }],
  });

  T.semi_equipment = () => chainScene({
    title: '半導體設備與材料：資本支出落在哪裡',
    cap: '晶圓廠的資本支出會依序流向材料、設備零件、製程機台與載具。台廠多半切在濕製程、零件與耗材這幾段。',
    cw: 980,
    stations: [
      S('wafer', 0, '矽晶圓與材料', ['矽晶圓、靶材、化學品', '耗材跟著產能走', '圖：單晶棒切成薄片'], ['6182', '1785', '4763', '6165'], 'foundry', dIngot, 1.1),
      S('parts', 0, '設備零件模組', ['機台零件與精密加工', '設備廠的上游', '圖：法蘭＋波紋管＋軸'], ['3413', '6187'], 'foundry', dPrecisionPart, 1.25),
      S('wet', 1, '濕製程與清洗', ['清洗、蝕刻、電鍍機台', '台廠最有位置那段', '圖：藥液槽＋搬運臂'], ['3131', '3583'], 'foundry', dWetBench),
      S('pod', 1, '晶圓載具 FOUP', ['光罩盒與傳載具', '先進製程才用得到', '圖：方盒＋吊環＋晶圓槽'], ['3680'], 'foundry', dFoup, 1.2),
      S('fab', 2, '晶圓廠資本支出', ['擴產與製程升級', '訂單能見度的源頭', '圖：廠房＋屋頂風機'], ['2330', '3711', '5434'], 'foundry', dFab, 1.1),
    ],
    steps: [{ p: 'wafer', t: '材料備料', s: '6182 / 1785' }, { p: 'parts', t: '設備零件', s: '3413' }, { p: 'wet', t: '製程機台', s: '3131 / 3583' },
    { p: 'pod', t: '載具搬運', s: '3680' }, { p: 'fab', t: '晶圓廠量產', s: '2330' }],
  });

  T.apple_chain = () => chainScene({
    title: '蘋果供應鏈：一支手機是怎麼組起來的',
    cap: '晶片與鏡頭是最上游，中間是板材、軟板與機殼結構件，最後由 EMS 整機組裝出貨。規格年年改，量體看終端銷售。',
    cw: 980,
    stations: [
      S('soc', 0, 'SoC 與晶片', ['A / M 系列獨家代工', '射頻與電源 IC 也在這', '圖：分區的運算核＋錫球'], ['2330', '2454'], 'foundry', dSocNpu, 1.4),
      S('lens', 0, '光學鏡頭模組', ['鏡頭、潛望式模組', '規格升級帶動單價', '圖：一疊鏡片＋音圈繞組'], ['3008', '3406'], 'assembly', dLensModule, 1.25),
      S('board', 1, '板材軟板載板', ['SLP 主機板、FPC', '封裝載板也在這', '圖：屏蔽罩＋接出的軟板'], ['3037', '6269'], 'abf_pcb', dSlpBoard, 1.35),
      S('case', 1, '機殼與結構件', ['CNC 機殼與中框', '單價高、良率關鍵', '圖：銑削凹槽＋天線斷點'], ['2474'], 'assembly', dCncCase, 1.4),
      S('ems', 2, '整機組裝出貨', ['EMS 組裝與品牌出貨', '量體最大、毛利最薄', '圖：掀開背蓋＋電池主板'], ['2317', '4938', '3231', '2382'], 'assembly', dPhone, 1.3),
    ],
    steps: [{ p: 'soc', t: '晶片', s: '2330 / 2454' }, { p: 'lens', t: '零組件', s: '3008 / 3406' }, { p: 'board', t: '模組', s: '3037 / 6269' },
    { p: 'ems', t: '整機組裝', s: '2317 / 4938' }, { p: 'ems', t: '品牌出貨', s: '終端銷售' }],
  });

  T.edge_ai_pc = () => explodeScene({
    title: '邊緣 AI 與 AI PC：算力搬到裝置端',
    cap: '端側推論靠 SoC 裡的 NPU，吃記憶體容量也吃散熱。台廠的位置在 ODM 板卡組裝、散熱電源與品牌整機。',
    unit: '整機爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('soc', 0, 'SoC 與 NPU', ['端側推論算力', '定義了什麼叫 AI PC',
        '圖上：掀蓋露出大小不同的 CPU／GPU／NPU 分區，底下一排錫球'], ['2454', '6533'], 'ic_design', dSocNpu),
      S('mem', 0, '記憶體與儲存', ['端側模型吃容量', 'DRAM / SSD 同步升級',
        '圖上：LPDDR 疊在基板上（PoP），旁邊一條 M.2 固態硬碟'], ['4967', '3260', '8299'], 'hbm', dMemSsd),
      S('board', 1, '板卡與 ODM 組裝', ['主機板設計與代工', '出貨量最大的一段',
        '圖上：主機板上兩條記憶體插槽、一條 M.2 插槽與供電電感'], ['2324', '2382', '3231', '2356'], 'assembly', dMainboard),
      S('power', 1, '電源與散熱模組', ['薄型化＋散熱的難題', '續航與電源管理',
        '圖上：離心風扇（側向出風）＋扁熱管＋薄鰭片，跟機櫃的軸流風扇不同'], ['2301', '2308'], 'thermal', dThinCool),
      S('brand', 2, '品牌整機與邊緣機台', ['品牌定義規格吃毛利', '工控與邊緣伺服器',
        '圖上：掀開螢幕的筆電，看得到鍵盤陣列與觸控板'], ['2357', '2353', '2377', '3005'], 'assembly', dLaptop),
    ],
    steps: [{ p: 'soc', t: 'SoC / NPU', s: '2454' }, { p: 'mem', t: '記憶體', s: '4967 / 8299' }, { p: 'board', t: '板卡組裝', s: '2324 / 2382' },
    { p: 'power', t: '散熱電源', s: '2301' }, { p: 'brand', t: '品牌出貨', s: '2357 / 2353' }],
  });

  T.robotics = () => explodeScene({
    title: '機器人：一個關節的價值分佈',
    cap: '一個關節 ＝ 減速機 ＋ 伺服馬達 ＋ 編碼器 ＋ 驅動器。人形機器人的關節數是工業手臂的好幾倍，量起來零組件先受惠。',
    unit: '一個關節的爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('reducer', 0, '減速機與傳動', ['諧波／行星減速機', '精度決定重複定位',
        '圖上：外圈剛輪齒、薄壁柔輪杯，中間那顆橢圓凸輪就是波產生器'], ['2049', '4583', '1590'], null, dHarmonic),
      S('motor', 0, '伺服馬達', ['扭力密度與散熱', '大廠自製比例高',
        '圖上：機殼中段露出定子繞組，前端伸出軸，後端是編碼器與出線'], ['1503', '1504'], 'power', dServoMotor),
      S('ctrl', 1, '控制器與驅動', ['運動控制與驅動器', '加上 AI 推論晶片',
        '圖上：兩側鰭片外殼、面板狀態燈與通訊埠、底下一排螺絲端子'], ['2464', '6215'], 'ic_design', dDriver),
      S('vision', 1, '視覺與感測', ['相機模組、力覺感測', '抓取能力的關鍵',
        '圖上：上面是雙目相機（兩顆鏡頭），底下那圈是力覺感測環'], ['3059', '2359'], 'ic_design', dVisionSensor),
      S('maker', 2, '整機與代工組裝', ['人形機器人整機代工', '線束連接器一起吃',
        '圖上：底座、兩節臂與關節圓柱，末端是兩指夾爪'], ['2317', '3665'], 'assembly', dRobotArm),
    ],
    steps: [{ p: 'reducer', t: '零組件', s: '2049 / 1590' }, { p: 'motor', t: '馬達', s: '1503 / 1504' }, { p: 'ctrl', t: '控制器', s: '2464 / 6215' },
    { p: 'vision', t: '感測整合', s: '3059 / 2359' }, { p: 'maker', t: '整機組裝', s: '2317' }],
  });

  T.drone = () => explodeScene({
    title: '無人機：一架四旋翼的供應鏈',
    cap: '馬達與螺旋槳決定推力，飛控與導航決定能不能自己飛，光電酬載決定它拿來做什麼。台廠以零組件與整機認證為主。',
    unit: '整機爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('motor', 0, '無刷馬達與螺旋槳', ['推力與續航的核心', '四顆同步調速',
        '圖上：外轉子杯下方露出定子繞組，上面是兩葉槳與固定螺栓'], ['8033', '2231'], 'power', dPropMotor),
      S('conn', 0, '連接器與線束', ['軍規連接器與線材', '可靠度的隱形門檻',
        '圖上：兩個插針接頭，中間三條線紮成一束並套上束環'], ['3023', '3675'], null, dHarness),
      S('fc', 1, '飛控與導航', ['飛控板、IMU、定位', '抗干擾是軍規重點',
        '圖上：板子四角的減震柱、中央 IMU，右上角那塊是 GPS 天線'], ['6237', '2367'], 'ic_design', dFlightCtrl),
      S('payload', 1, '光電酬載與雲台', ['相機、紅外線、測距', '決定任務型態',
        '圖上：兩層同心環（雲台的軸），中間吊著球形相機'], ['3059', '2634'], 'ic_design', dGimbal),
      S('maker', 2, '整機與軍民用標案', ['國家隊整機廠', '認證與交期是門檻',
        '圖上：四支機臂對稱張開、四組槳，機腹吊掛酬載'], ['2634', '3402', '8033'], 'assembly', dDrone),
    ],
    steps: [{ p: 'conn', t: '零組件', s: '2231 / 3023' }, { p: 'motor', t: '動力系統', s: '8033' }, { p: 'fc', t: '飛控導航', s: '6237 / 2367' },
    { p: 'payload', t: '酬載整合', s: '3059' }, { p: 'maker', t: '整機交付', s: '2634 / 3402' }],
  });

  T.satellite = () => explodeScene({
    title: '低軌衛星：天上與地面各拿到什麼',
    cap: '衛星本體幾乎都是國外業者。台廠的錢主要在地面段：射頻元件、相位陣列天線、用戶終端與網通設備。',
    unit: '由零件到系統的爆炸拆解（由上而下）：左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('epi', 0, '化合物半導體', ['砷化鎵磊晶與晶片', '高頻元件的底材',
        '圖上：晶圓上再長出幾層越縮越小的薄膜，邊緣看得到台階'], ['2455', '8086'], 'optical', dEpiWafer),
      S('rf', 0, '射頻元件與模組', ['功率放大、濾波、混頻', '規格門檻高',
        '圖上：掀開一半的金屬屏蔽罩，裡面是功率放大器與三顆濾波器'], ['3491', '2314'], 'optical', dRfModule),
      S('ant', 1, '天線與相位陣列', ['波束成形與饋源', '地面站與終端都要',
        '圖上：一整片規則排列的貼片陣列，背面是饋線，斜上方是波束'], ['3491', '2314'], 'switch', dPhaseArray),
      S('cpe', 1, '用戶終端 CPE', ['終端設備與家用路由', '出海量最大的一段',
        '圖上：一片方形平板天線架在斜撐底座上，拉一條電源線'], ['6285', '4906', '5388', '3704'], 'switch', dCpe),
      S('op', 2, '衛星與電信營運', ['星系營運與網通回傳', '台廠賣零組件給它',
        '圖上：本體兩側展開太陽翼，底下是碟型天線與打向地面的波束'], ['2345', '6143'], 'switch', dSatellite),
    ],
    steps: [{ p: 'epi', t: '磊晶材料', s: '2455 / 8086' }, { p: 'rf', t: '射頻元件', s: '3491' }, { p: 'ant', t: '天線模組', s: '3491 / 2314' },
    { p: 'cpe', t: '終端設備', s: '6285 / 4906' }, { p: 'op', t: '營運商', s: '海外客戶' }],
  });

  T.ev_auto = () => explodeScene({
    title: '車用與電動車：台廠切在哪幾塊',
    cap: '滑板底盤裡是電池包，前後軸各一顆馬達，中間是電控與車載充電器。台廠強項在電源、線束連接器與金屬結構件。',
    unit: '整車爆炸拆解（由上而下）：每一層都畫成它真正的樣子，左圖看形狀、右卡看誰在做',
    style: AI_STYLE, cw: 980, ex: EX980,
    layers: [
      S('metal', 0, '金屬與結構件', ['沖壓件、車燈、扣件', '毛利穩、看車廠拉貨',
        '圖上：折邊鈑金、兩個安裝孔，邊緣那排小圈是焊點'], ['1536', '2228', '1319', '6605'], 'assembly', dStamping),
      S('sensor', 0, '車用電子與感測', ['胎壓、感測器、MCU', '車規認證是門檻',
        '圖上：貼散熱片的車規 MCU、一顆圓柱感測器與一個短接頭'], ['2231', '6533'], 'ic_design', dMcuSensor),
      S('power', 1, '電源電控與 OBC', ['逆變器、車載充電器', '台廠最有位置的一段',
        '圖上：鋁壓鑄殼與鰭片、三顆功率模組、兩顆直流母線電容、三相出線'], ['2308', '6409'], 'power', dInverter),
      S('harness', 1, '線束與連接器', ['高壓線束、充電槍', '電動化帶動單車用量',
        '圖上：左邊是充電槍頭，兩條橘色高壓纜拉到右邊的環狀銅端子'], ['3665', '3023', '2059'], 'power', dHvHarness),
      S('oem', 2, '整車與車廠', ['系統整合與代工', '終端是國外品牌',
        '圖上：滑板底盤，中間鋪滿電池模組，前後軸各一顆驅動馬達'], ['2317'], 'assembly', dEvChassis),
    ],
    steps: [{ p: 'metal', t: '結構件', s: '1536 / 2228' }, { p: 'sensor', t: '車用電子', s: '2231' }, { p: 'power', t: '電源電控', s: '2308 / 6409' },
    { p: 'harness', t: '線束整合', s: '3665 / 3023' }, { p: 'oem', t: '整車出貨', s: '國外車廠' }],
  });

  T.defense = () => chainScene({
    title: '軍工國防：預算最後變成哪些載具',
    cap: '國防預算最後變成船、飛機與無人載具，再加上雷達電戰與軍規零組件。訂單期長、認列慢，看的是能見度不是單季。',
    cw: 980,
    stations: [
      S('parts', 0, '軍規零組件', ['氣動元件與精密件', '認證期長、黏著度高', '圖：圓接頭＋卡榫齒環'], ['2231', '1590'], null, dMilConnector, 1.35),
      S('rugged', 0, '強固型電腦電戰', ['軍規電腦與雷達', '毛利高於商規', '圖：鰭片機殼＋圓形接頭'], ['3005'], 'ic_design', dRuggedPc, 1.2),
      S('aero', 1, '航太結構與 MRO', ['機體結構、葉片、維修', '長約帶來穩定現金流', '圖：後掠翼＋座艙罩'], ['2634'], 'assembly', dPlane, 1.2),
      S('uav', 1, '軍用無人機', ['偵蒐與攻擊型整機', '國家隊標案', '圖：四臂對稱＋酬載'], ['8033', '3402'], 'assembly', dDrone, 1.25),
      S('ship', 2, '艦艇與國防標案', ['海軍艦艇與商船', '交期長、能見度高', '圖：艦橋側面的雷達板'], ['2208', '5871'], 'assembly', dShip, 1.25),
    ],
    steps: [{ p: 'parts', t: '軍規零件', s: '2231 / 1590' }, { p: 'rugged', t: '次系統', s: '3005' }, { p: 'aero', t: '結構整合', s: '2634' },
    { p: 'uav', t: '整機交付', s: '8033 / 3402' }, { p: 'ship', t: '維修 MRO', s: '長約' }],
  });

  T.heavy_electric = () => chainScene({
    title: '重電與電網：電從電廠送到機房',
    cap: '變壓器 → 開關配電盤 → 電纜匯流 → 使用端，旁邊再掛儲能。AI 資料中心的用電讓這條老產業的交期與報價一起上來。',
    cw: 980,
    stations: [
      S('cable', 0, '銅材與電線電纜', ['銅價連動的基本盤', '電網擴建先拉貨', '圖：捲盤＋斷面銅芯'], ['1609', '1618'], null, dCableDrum, 1.1),
      S('transformer', 1, '變壓器', ['交期最長、報價最硬', '台電與機房搶產能', '圖：油箱＋三根陶瓷套管'], ['1519', '1513'], 'power', dTransformer, 1.15),
      S('switchgear', 1, '開關與配電盤', ['GIS、開關箱、配電', '跟著變壓器一起出貨', '圖：三櫃並排＋操作把手'], ['1514', '1503'], 'power', dSwitchgear),
      S('motor', 1, '馬達與重電設備', ['大型馬達與發電機', '工業需求的溫度計', '圖：散熱筋機殼＋接線盒'], ['1504'], 'power', dBigMotor, 1.1),
      S('epc', 2, '統包工程與需求端', ['機電統包與儲能', '資料中心與電廠', '圖：戶外機櫃＋管線橋'], ['2404', '3576', '1519'], 'assembly', dSubstation),
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
