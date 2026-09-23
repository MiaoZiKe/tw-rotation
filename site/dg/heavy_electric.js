/* 變壓器與 GIS 電力路徑 —— docs/diagram_plan.md 的第 14 張（族群 `heavy_electric`、infrastructure 鏈）

   合約＝`docs/diagram_specs/transformer_gis.md`。這個檔只實作，不重新決定規格。
   位階更高的是 `docs/diagram_purpose.md`（R1～R6）：圖不是插圖，是「誰在做什麼」的入口。

   規格書裡已經寫死、這裡照辦的幾件事
   ------------------------------------
     · §3-A 硬規則 1  所有箭頭一律由左（電網）指向右（機櫃）
     · §3-A 硬規則 2  電壓只准降不准升，唯一一次升壓在段 0 而且在進輸電線**之前**
     · §3-A 硬規則 3  ★ GIS 不降壓、配電盤也不降壓 —— 電壓階梯在段 2 與段 4 **必須是平的**
     · §3-A 硬規則 4  GIS 在主變壓器**之前**，中壓配電盤在主變壓器**之後**
     · §3-A 硬規則 5  UPS 在 PDU 之前，PDU 在機櫃之前
     · §3-A 硬規則 6  ★ 電池掛在 UPS 的**直流側**，是一條往下的分支，不是串在輸出上
     · §3-A 硬規則 8  段 0 的再生能源與電網級儲能併在「電網側」，不是併在機房裡
     · §3-C           高壓側朝左、高壓套管明顯高於低壓、散熱片垂直、儲油櫃橫放
     · §4             GIS 是**水平圓筒**不是方箱；乾式變壓器沒有油箱／散熱片／儲油櫃；
                      配電盤是一整排等高金屬櫃、至少一櫃把抽出式斷路器拉出來；
                      電池櫃是一層一層的模組抽屜，不是一顆大方塊
     · §5-A 段 6      **不列任何代號**（機櫃電源屬「伺服器電源與 BBU」題材）
     · §5-E           亞力 1514 必須標「中壓級」；東元 1504 不准寫成「做配電盤／做變壓器」；
                      漢唐 2404 只出現在工程統包帶，而且必須寫「不製造重電設備」
     · §6-C1          在手訂單、市占率、營收占比、能見度年份一律不進圖

   為什麼是「正立面 ＋ 等角厚度」而不是整場等角
   --------------------------------------------
   規格書 §0 要的是 2.5D。這張圖的兩個決定性特徵都靠**正立面**才看得出來：
   GIS 是一排**水平**圓筒（等角會把圓筒壓成斜柱，跟方箱分不出來），
   變壓器的散熱片是**垂直**薄片（等角會把垂直變成斜的，就跟冷氣機的水平橫條混在一起）。
   所以主體畫成正立面，再用頂面與右側面給它厚度。同 `site/dg/ic_substrate.js` 的取捨。

   ★ 顏色怎麼走（這一段不照做，整張圖會變灰）
   --------------------------------------------
   `supply_chain.yaml` 目前只建了 semiconductor／ai_server／electronics 三條鏈，
   **重電這一條一個環節都沒有**（規格書 §6-D：那個 `power` 環節是 AI 伺服器的電源廠，不是電網重電）。
   而 `site/industry.js` 的 highlightSegments() 會對每一個 `[data-seg]` 節點寫上 inline 的
   `--c: segColor(seg)`，未知環節一律回灰 —— 掛了 data-seg 就整張圖灰掉。
   但**不掛 data-seg 就完全點不動**：wireDiagram() 只對 `[data-seg]` 綁 click，
   零件小卡沒有 seg 就直接收起來。
   所以做法是：data-seg 照掛，零件的**視覺**包在一層帶 `--c` 的內層群組裡
   —— inline 寫在子節點上、JS 寫在父節點上，子的贏，材質色就守住了。
   （規格書 §6-D 當時的結論是「一律不帶 data-seg」，那是在**零件小卡還不存在**的時候寫的。）

   ★ data-seg 為什麼是中文：小卡上那顆按鈕會印「環節的 name，找不到就印 id」。
   這條鏈沒有環節，所以直接印 id —— 印中文站名至少那顆鈕是可讀的。
   ⚠ 按下去會是 0 筆，圖上有一行字把這件事寫清楚，不要讓人以為點壞了。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/industry.js`。
   共用工具走 `window.DG`；**JS 裡一個十六進位色碼都沒有**，色值全部走 :root 既有的 --dg-*。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold } = D;

  /* ================================================================ v2 版面（2026-09-23）
     Andy：「傳產與內需 & 基礎建設與能源 2D 圖並沒有調整適當大小，請去調整，調整適當範圍，別浪費空白」。
     ----------------------------------------------------------------
     上一批（W8）已經補過一輪「在 980 的框裡補小圖填空白」，他看過之後說**還是沒調好**。
     真正的問題不是框裡有沒有東西，是**整張圖的尺度**：這一批其餘 12 張已經收到 660／700，
     只有這張與輕油裂解那張還是 980，於是在同樣的欄寬下被縮得比別人小、四周留白比別人多。
     所以改成跟那 12 張（`server_psu`／`foundry`／`silicon_wafer`）完全一致的 v2 版面：
       · svg 根掛 `rs` → `externalize()` 把說明搬成 HTML 卡片（`.dgc`），
         欄寬由 index.html 的 `.dgv2` 容器查詢決定（1440 三欄／800 兩欄／390 單欄），
         **圖檔裡不寫死「右邊留多少 px」**。
       · 畫布 980 → **660**（`native` 同步改）；畫布上只留「畫」的部分。
       · 章節改用 `D.fold()`（範圍由 `getBBox()` 量），不再手寫 y0／y1。
     ⚠ 上一批為了填空白補進去的兩塊：
       · 電壓階梯右上的圖例 → 收窄之後那個位置放不下，圖例文字搬進說明卡片 ⑫「電壓階梯」，
         畫面上仍然看得到粉色豎線與圓點兩種記號（記號本來就是圖，不是文字）。
       · 第二排上方的「每一格出來是幾伏特」對照帶 → 搬成章節 ③ 圖例行的第一句。
       兩塊講的事一個字都沒有消失，只是換了位置。
     沒有放寬的事：`data-part` 22 個一個不改名、一個不減少；九站 `data-seg` 照舊；
     JS 裡一個十六進位色碼都沒有。*/
  const CW = 660;

  /* 兩排主體都是「幾何整組縮小放進 660 的畫布」。★ 文字一律留在縮放群組**外面**：
     字級縮下去就破了 12px 硬下限（DECISIONS #227），所以縮的永遠只有圖形。*/
  const K1 = 0.70, K1X = 4.8, K1Y = 3.8;        // 第一排（電網到變電所）：原圖 x[16,900] y[306,506]
  const f1x = (x) => +(x * K1 + K1X).toFixed(1);
  const f1y = (y) => +(y * K1 + K1Y).toFixed(1);
  const K2 = 0.66, K2X = 5.44, K2Y = -348.4;    // 第二排（廠內配電到機櫃）：原圖 x[16,960] y[634,786]
  const f2x = (x) => +(x * K2 + K2X).toFixed(1);
  const f2y = (y) => +(y * K2 + K2Y).toFixed(1);

  const T = (x, y, t, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${t}</text>`;
  /* 章節裡的編號圓點。★ 章節內**不能**用 `extRow` —— `externalize()` 會把卡片抽到左右欄，
     錨點卻留在收合起來的章節裡，於是出現一張指不到任何東西的孤兒卡片。*/
  const ndot = (x, y, n) =>
    `<g pointer-events="none"><circle class="ndot" cx="${x}" cy="${y}" r="9.5"/>`
    + `<text class="nnum" x="${x}" y="${y}">${String(n).padStart(2, '0')}</text></g>`;

  /* 卡片的元件色（`data-dgcolor`），跟畫面上那個零件的材質色同一個 token */
  const CC = {
    mute: 'var(--dg-mute)', si: 'var(--dg-si)', alu: 'var(--dg-alu)', cu: 'var(--dg-cu)',
    el: 'var(--dg-el)', cer: 'var(--dg-cer)', resin: 'var(--dg-resin)', fws: 'var(--dg-fws)',
    bezel: 'var(--dg-pn-bezel)', accent: 'var(--dg-accent-2d)',
  };
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點與引線。
     ★ `seg` 與 `part` 照舊掛上去 —— externalize 把身分搬到卡片上，點卡片＝點那個零件。*/
  const card = (o) => extRow({
    seg: o.seg, part: o.part, title: o.title, sub: o.sub, no: o.no,
    side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order,
  });

  /* ================================================================ 環節（站）*/
  const G0 = '發電與電網側', G1 = '超高壓輸電', G2 = '變電所開關 GIS', G3 = '主變壓器降壓',
    G4 = '中壓配電', G5 = '不斷電與低壓配電', G6 = '機櫃取電', GE = '工程統包與安裝', GV = '電壓階梯';

  const P = (seg, part, col, inner) =>
    `<g data-seg="${seg}" data-part="${part}"><g class="pw" style="--c:var(${col})">${inner}</g></g>`;

  const V = (c) => `var(${c})`;
  const R = (x, y, w, h, f, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${f}"/>`;

  /* ---------------- 2.5D 機櫃／箱體：正面 ＋ 頂面 ＋ 右側面 */
  const cab = (x, y, w, h, d, a, b, c2) =>
    `<path d="M${x},${y} l${d},${-d * 0.5} h${w} l${-d},${d * 0.5} Z" fill="${V(c2 || a)}"/>`
    + `<path d="M${x + w},${y} l${d},${-d * 0.5} v${h} l${-d},${d * 0.5} Z" fill="${V(b)}"/>`
    + R(x, y, w, h, V(a), 'part');

  /* ---------------- 水平圓筒（★ GIS 的決定性特徵：圓筒不是方箱）
     `fl` ＝法蘭環的 x 位置（每一段之間就是一個氣室分界）。*/
  function hcyl(x, y, w, h, a, b, fl) {
    const s = [R(x, y, w, h, V(a), 'part', h / 2),
      R(x, y + h * 0.58, w, h * 0.34, V(b), '', h * 0.17),
      `<ellipse cx="${(x + w - h * 0.28).toFixed(1)}" cy="${(y + h / 2).toFixed(1)}" rx="${(h * 0.28).toFixed(1)}" ry="${(h / 2).toFixed(1)}" fill="${V(b)}"/>`];
    (fl || []).forEach((fx) => {                    // 法蘭：凸出的環 ＋ 一圈等距小螺栓
      s.push(R(fx - 2.5, y - 2, 5, h + 4, V(b), '', 2));
      s.push(`<circle cx="${fx}" cy="${y + 2.5}" r="1" fill="${V(a)}"/><circle cx="${fx}" cy="${y + h - 2.5}" r="1" fill="${V(a)}"/>`);
    });
    return s.join('');
  }

  /* ---------------- 立式圓筒（乾式變壓器的樹脂線圈、套管柱身） */
  function vcyl(cx, yb, w, h, a, b) {
    const r = w / 2, ry = Math.max(2, w * 0.26), yt = yb - h;
    return `<ellipse cx="${cx}" cy="${yb}" rx="${r}" ry="${ry}" fill="${V(b)}"/>`
      + R(cx - r, yt, w, h, V(a), 'part')
      + R(cx + r * 0.2, yt, r * 0.8, h, V(b))
      + `<ellipse cx="${cx}" cy="${yt}" rx="${r}" ry="${ry}" fill="${V(a)}" stroke="${V(b)}" stroke-width=".8"/>`;
  }

  /* ---------------- 套管（bushing）：錐形柱 ＋ 一疊傘裙。
     ★ §3-C：高壓側（左）明顯比低壓側（右）高、傘裙也多。只表達高低關係，不標尺寸。*/
  function bushing(cx, yb, h, n, a, b) {
    const s = [R(cx - 3, yb - h, 6, h, V(a), 'part')];
    for (let i = 0; i < n; i++) {
      const w = 13 - i * (5 / Math.max(1, n - 1));
      const y = yb - h + 6 + i * ((h - 10) / n);
      s.push(`<ellipse cx="${cx}" cy="${y.toFixed(1)}" rx="${w.toFixed(1)}" ry="2.4" fill="${V(b)}"/>`);
    }
    s.push(`<circle cx="${cx}" cy="${yb - h - 3}" r="3.4" fill="${V(a)}"/>`);
    return s.join('');
  }

  /* ---------------- 垂直散熱薄片（★ §4 一眼認出油浸式變壓器的特徵）
     上下各一根集管接回油箱；畫成水平橫條就變成冷氣機了。*/
  function radiator(x, y, w, h, n, a, b) {
    const fins = [];
    const gap = w / n;
    for (let i = 0; i < n; i++) fins.push(R((x + i * gap + 1).toFixed(1), y + 6, (gap - 2.4).toFixed(1), h - 12, V(a)));
    return R(x - 2, y, w + 4, 7, V(b), 'part', 2) + fins.join('') + R(x - 2, y + h - 7, w + 4, 7, V(b), '', 2);
  }

  /* ---------------- 格子鋼架（輸電鐵塔）：兩支收斂的腿 ＋ 交叉斜撐 ＋ 兩層橫擔 */
  function tower(cx, yb, h, halfB, halfT, col) {
    const yt = yb - h, d = [];
    d.push(`M${cx - halfB},${yb} L${cx - halfT},${yt} M${cx + halfB},${yb} L${cx + halfT},${yt}`);
    const n = 7;
    for (let i = 0; i < n; i++) {
      const t0 = i / n, t1 = (i + 1) / n;
      const y0 = yb - h * t0, y1 = yb - h * t1;
      const w0 = halfB + (halfT - halfB) * t0, w1 = halfB + (halfT - halfB) * t1;
      d.push(`M${(cx - w0).toFixed(1)},${y0.toFixed(1)} L${(cx + w1).toFixed(1)},${y1.toFixed(1)}`);
      d.push(`M${(cx + w0).toFixed(1)},${y0.toFixed(1)} L${(cx - w1).toFixed(1)},${y1.toFixed(1)}`);
      d.push(`M${(cx - w1).toFixed(1)},${y1.toFixed(1)} L${(cx + w1).toFixed(1)},${y1.toFixed(1)}`);
    }
    return `<path class="part" d="${d.join(' ')}" stroke="${V(col)}" stroke-width="1.6" fill="none"/>`;
  }

  /* ---------------- 懸垂絕緣礙子串：一串多片傘裙盤（不是一顆） */
  const insulator = (x, y, n, col) => {
    const a = [`<path d="M${x},${y} V${y + n * 5 + 2}" stroke="${V(col)}" stroke-width="1" fill="none"/>`];
    for (let i = 0; i < n; i++) a.push(`<ellipse cx="${x}" cy="${y + 4 + i * 5}" rx="3.4" ry="1.5" fill="${V(col)}"/>`);
    return a.join('');
  };

  /* ---------------- 比例小人（1.7 m）：單色剪影，不要五官 */
  const person = (x, yb) => `<g pointer-events="none" opacity=".9">
    <circle cx="${x}" cy="${yb - 14}" r="2.6" fill="${V('--dg-mute')}"/>
    <path d="M${x},${yb - 11.4} V${yb - 5} M${x - 3},${yb - 9} H${x + 3} M${x},${yb - 5} l-2.6,5 M${x},${yb - 5} l2.6,5" stroke="${V('--dg-mute')}" stroke-width="1.4" fill="none" stroke-linecap="round"/></g>`;

  const arrow = (d, col, cls, w) =>
    `<path class="${cls || ''}" d="${d}" stroke="${V(col)}" stroke-width="${w || 2}" fill="none" stroke-linecap="round" marker-end="url(#heAr)"/>`;

  const tblock = (seg, part, col, x, y, w, t, subs) =>
    `<g class="lrow" data-seg="${seg}" data-part="${part}"><g class="pw" style="--c:var(${col})">
      <rect class="bg" x="${x - 8}" y="${y - 15}" width="${w}" height="${21 + subs.length * 18}" rx="6"/>
      <circle class="dot" cx="${x + 4}" cy="${y - 4}" r="4"/>
      <text class="lbl" x="${x + 14}" y="${y}">${t}</text>
      ${subs.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 18 + i * 18}">${s}</text>`).join('')}
    </g></g>`;

  /* ================================================================ 電壓階梯帶（§3-B）
     ★ 寫成一個陣列跑迴圈，不手刻每一階（規格書 §7 明講手刻就會刻錯）。
     y 只准變大（＝電壓只准往下掉）；段 2 與段 4 的 y 必須跟前一階**相同**（平的）。
     驗收就是量這件事：`_uitest.py` 直接讀 `.heStep` 這幾條線的 y。

     ★ 2026-09-23 v2：x 座標整組收進 660 的畫布（原本跨 40～940）。
     每一階上面只放電壓（短字串，放得下），下面放「①～⑥」＋兩三個字的站名；
     原本寫在階梯旁邊的整句敘述與圖例搬進說明卡片 ⑫ —— 那不是刪掉，是換了位置。*/
  const LADDER = [
    { x0: 32, x1: 132, y: 74, v: '345 kV', s: '① 輸電' },
    { x0: 132, x1: 236, y: 88, v: '161 kV', s: '② GIS' },
    { x0: 236, x1: 342, y: 110, v: '22.8 kV', s: '③ 主變' },
    { x0: 342, x1: 448, y: 110, v: '22.8 kV', s: '④ 配電盤' },
    { x0: 448, x1: 554, y: 132, v: '380 / 220 V', s: '⑤ 廠內變' },
    { x0: 554, x1: 630, y: 148, v: '機櫃直流', s: '⑥ 機櫃' },
  ];
  function ladder() {
    const seg = LADDER.map((o, i) => {
      const prev = i ? LADDER[i - 1] : null;
      // 粉色豎線＝真的降壓；圓點＝接上但不降壓（開關設備）。這兩個記號本身就是圖例，不必再寫字。
      const drop = prev && prev.y !== o.y
        ? `<path class="hedrop" d="M${o.x0},${prev.y} V${o.y}" stroke="${V('--dg-warn')}" stroke-width="2.2" fill="none"/>`
        : (prev ? `<circle cx="${o.x0}" cy="${o.y}" r="2.6" fill="${V('--dg-accent-2d')}"/>` : '');
      return drop + `<path class="heStep" data-i="${i}" d="M${o.x0},${o.y} H${o.x1}" stroke="${V('--dg-accent-2d')}" stroke-width="2.6" fill="none"/>`
        + `<text class="lbl" x="${o.x0 + 4}" y="${o.y - 8}">${o.v}</text>`
        + `<text class="sub" x="${o.x0 + 4}" y="${o.y + 16}">${o.s}</text>`;
    }).join('');
    // 另一條常見路徑（一次變電所 161→69、二次變電所 69→22.8／11.4）：虛線，不是主線
    const alt = `<path d="M190,88 L236,105 H300 L342,110" stroke="${V('--dg-mute')}" stroke-width="1.6" fill="none" stroke-dasharray="6 5"/>`;
    const concl = `<text class="sub" x="30" y="182" style="fill:var(--dg-warn)">`
      + `★ 六格裡只有三格在動電壓：段 0 升、段 3 降、段 5 降。其餘兩格只切斷與導通，所以階梯必須是平的。</text>`;
    return P(GV, 'he_ladder', '--dg-accent-2d', `<rect class="frame part" x="16" y="30" width="628" height="160" rx="8"/>`)
      + `<g pointer-events="none"><text class="hd" x="30" y="50">① 電壓階梯（示意，階高與電壓不成比例）　★ 降壓的只有變壓器</text>${alt}${seg}${concl}</g>`;
  }

  /* ================================================================ 版面常數 */
  const GA = 486;    // 第一排（電網到變電所）的地面線
  const GB = 768;    // 第二排（廠內配電到機櫃）的地面線

  /* ================================================================ 段 0 發電與電網側（分支） */
  function seg0() {
    return P(G0, 'he_gen', '--dg-mute',
      cab(18, GA - 46, 36, 46, 8, '--dg-mute', '--dg-mute')
      + `<path d="M26,${GA - 46} V${GA - 64} M36,${GA - 46} V${GA - 60}" stroke="${V('--dg-mute')}" stroke-width="2.6" fill="none"/>`
      + cab(66, GA - 34, 28, 34, 6, '--dg-el', '--dg-el')
      + bushing(74, GA - 34, 14, 3, '--dg-cer', '--dg-cer-2')
      + bushing(86, GA - 34, 10, 2, '--dg-cer', '--dg-cer-2'))
      /* ⚠ 2026-09-23 v2：原本這裡還有一行「電廠 → 升壓」的 SVG 文字。
         第一排的幾何在 v2 被整組縮到 0.70，文字跟著縮就會變成 8.4px（破 12px 硬下限），
         所以那句話搬到說明卡片 ①「電廠與升壓變壓器」的第一行 —— 資訊沒有消失，只是換了位置。*/
    + P(G0, 'he_re', '--dg-si',
      // 太陽能板：傾斜面板 ＋ 電池片格線；旁邊一個貨櫃式儲能
      `<path class="part" d="M18,${GA - 96} l36,-14 l14,10 l-36,14Z" fill="${V('--dg-si')}"/>`
      + `<path d="M26,${GA - 99} l36,-14 M34,${GA - 96} l36,-14 M22,${GA - 93} l36,-14" stroke="${V('--dg-si-2')}" stroke-width="1" fill="none"/>`
      + `<path d="M36,${GA - 92} V${GA - 82} M48,${GA - 96} V${GA - 82}" stroke="${V('--dg-si-2')}" stroke-width="1.4" fill="none"/>`
      + cab(78, GA - 100, 40, 22, 7, '--dg-frame', '--dg-frame', '--dg-fws')
      + `<path d="M84,${GA - 94} h28 M84,${GA - 88} h28" stroke="${V('--dg-fws')}" stroke-width="1.2" fill="none"/>`
      + `<path d="M98,${GA - 78} V${GA - 60} H120" stroke="${V('--dg-fws-2')}" stroke-width="1.6" fill="none"/>`);
  }

  /* ================================================================ 段 1 超高壓輸電 */
  function seg1() {
    const cx = 186;
    const phases = [[cx - 30, GA - 148], [cx + 30, GA - 148], [cx, GA - 174]];
    const strings = phases.map(([x, y]) => insulator(x, y, 6, '--dg-cer')).join('');
    return P(G1, 'he_tower', '--dg-alu',
      tower(cx, GA, 174, 26, 9, '--dg-alu')
      + `<path class="part" d="M${cx - 34},${GA - 148} H${cx + 34} M${cx - 20},${GA - 174} H${cx + 20}" stroke="${V('--dg-alu-2')}" stroke-width="3" fill="none"/>`
      + strings
      + phases.map(([x, y]) => `<path d="M${x},${y + 34} H292 M${x},${y + 39} H292" stroke="${V('--dg-cu-dim')}" stroke-width="1.1" fill="none"/>`).join(''))
    + P(G1, 'he_cable', '--dg-cu',
      // 交連聚乙烯（XLPE）電纜剖面：由內到外六層，順序寫死（§4 輸電段）
      `<circle class="part" cx="252" cy="${GA - 40}" r="30" fill="${V('--dg-el')}"/>`
      + `<circle cx="252" cy="${GA - 40}" r="25" fill="${V('--dg-alu-3')}"/>`
      + `<circle cx="252" cy="${GA - 40}" r="21" fill="${V('--dg-el')}"/>`
      + `<circle cx="252" cy="${GA - 40}" r="17" fill="${V('--dg-resin')}"/>`
      + `<circle cx="252" cy="${GA - 40}" r="8" fill="${V('--dg-el')}"/>`
      + `<circle cx="252" cy="${GA - 40}" r="6" fill="${V('--dg-cu')}"/>`
      + `<path d="M252,${GA - 40} L290,${GA - 66}" stroke="${V('--dg-mute')}" stroke-width="1" fill="none"/>`)
    + arrow(`M292,${GA - 20} H322`, '--dg-accent-2d', 'flow');
  }

  /* ================================================================ 段 2 變電所：GIS
     ★ §4：水平圓筒、法蘭接合、斷路器氣室明顯較粗、外殼上有 SF6 密度錶、整體接地。*/
  function seg2() {
    const x0 = 336, x1 = 560;
    const bus = [0, 1, 2].map(i => hcyl(x0, GA - 124 + i * 26, x1 - x0, 15, '--dg-alu', '--dg-alu-2',
      [x0 + 42, x0 + 96, x0 + 150])).join('');
    return P(G2, 'he_gis', '--dg-alu',
      bus
      // 斷路器氣室：比母線筒明顯粗，下面掛一個帶觀察窗的操作機構箱
      + hcyl(x0 + 96, GA - 70, 68, 26, '--dg-alu', '--dg-alu-2', [x0 + 100, x0 + 158])
      + cab(x0 + 110, GA - 42, 40, 30, 7, '--dg-el', '--dg-el')
      + R(x0 + 118, GA - 34, 16, 10, V('--dg-cold'), '', 2)
      // SF6 氣體密度錶：分散在不同氣室上
      + [[x0 + 66, GA - 116], [x0 + 66, GA - 64], [x0 + 176, GA - 90]].map(([gx, gy]) =>
        `<circle cx="${gx}" cy="${gy}" r="4" fill="${V('--dg-cer')}" stroke="${V('--dg-alu-3')}" stroke-width="1"/>`
        + `<path d="M${gx},${gy} l2.6,-2.4" stroke="${V('--dg-el')}" stroke-width="1" fill="none"/>`).join('')
      // 左端：帶傘裙的套管，斜向上接架空線；右端：電纜終端封匣，垂直向下
      + bushing(x0 + 10, GA - 124, 30, 4, '--dg-cer', '--dg-cer-2')
      + R(x1 - 24, GA - 72, 16, 54, V('--dg-alu-2'), '', 4)
      + `<path d="M${x1 - 16},${GA - 18} V${GA}" stroke="${V('--dg-el')}" stroke-width="5" fill="none"/>`
      // 整體接地：粗接地線從外殼拉到地面接地符號
      + `<path d="M${x0 + 20},${GA - 110} V${GA - 6} M${x0 + 12},${GA - 6} h16 M${x0 + 15},${GA - 2} h10 M${x0 + 18},${GA + 2} h4" stroke="${V('--dg-fws')}" stroke-width="2" fill="none"/>`)
    // AIS 對照縮圖：同樣的功能，露天的瓷瓶＋刀閘要佔這麼大一塊地（GIS 存在的理由）
    + P(G2, 'he_ais', '--dg-mute',
      `<path class="part" d="M330,${GA - 152} h34 M336,${GA - 152} v-10 M352,${GA - 152} v-10" stroke="${V('--dg-mute')}" stroke-width="1.4" fill="none"/>`
      + `<path d="M336,${GA - 162} l10,-8 M352,${GA - 162} l-6,4" stroke="${V('--dg-mute')}" stroke-width="1.6" fill="none"/>`
      + [336, 352].map(bx => [0, 1, 2].map(i => `<ellipse cx="${bx}" cy="${GA - 158 + i * 4}" rx="3" ry="1.2" fill="${V('--dg-mute')}"/>`).join('')).join(''))
    + arrow(`M566,${GA - 20} H598`, '--dg-accent-2d', 'flow');
  }

  /* ================================================================ 段 3 主變壓器（油浸式）
     §3-C 由外到內：基礎滾輪 → 油箱 → 側面垂直散熱片 → 箱蓋套管（高壓左、低壓右）
     → 橫放儲油櫃 → 吸濕呼吸器 → 瓦斯電驛 → OLTC 機構箱 → 溫度計與油位計。
     ★ 不畫繞組剖面（§6-B3：查不到可引用來源，寧可不畫也不編）。*/
  function seg3() {
    const tx = 648, tw = 172, ty = GA - 104;
    return P(G3, 'he_tx', '--dg-el',
      R(tx - 10, GA - 8, tw + 20, 8, V('--dg-alu-3'), '', 2)           // 基礎與滾輪軌道
      + `<circle cx="${tx + 16}" cy="${GA - 2}" r="5" fill="${V('--dg-alu-3')}"/><circle cx="${tx + tw - 16}" cy="${GA - 2}" r="5" fill="${V('--dg-alu-3')}"/>`
      + cab(tx, ty, tw, 96, 12, '--dg-el', '--dg-el')
      + `<path d="M${tx + 34},${ty} V${GA - 8} M${tx + 86},${ty} V${GA - 8} M${tx + 138},${ty} V${GA - 8}" stroke="${V('--dg-alu-3')}" stroke-width="1.4" fill="none" opacity=".6"/>`
      // 溫度計與油位計（箱壁上的小圓錶）
      + `<circle cx="${tx + 150}" cy="${ty + 22}" r="5" fill="${V('--dg-cer')}" stroke="${V('--dg-alu-3')}" stroke-width="1"/>`
      + `<circle cx="${tx + 150}" cy="${ty + 42}" r="5" fill="${V('--dg-cer')}" stroke="${V('--dg-alu-3')}" stroke-width="1"/>`)
    + P(G3, 'he_rad', '--dg-alu',
      radiator(tx + tw + 8, ty + 8, 60, 82, 9, '--dg-alu', '--dg-alu-3')
      + `<path d="M${tx + tw},${ty + 14} h10 M${tx + tw},${ty + 84} h10" stroke="${V('--dg-alu-3')}" stroke-width="3" fill="none"/>`)
    + P(G3, 'he_cons', '--dg-el',
      // 儲油櫃：橫放的圓筒，架在油箱上方一側（畫成直立圓桶＝錯）
      hcyl(tx + 18, ty - 30, 92, 22, '--dg-el', '--dg-el', [tx + 52])
      + `<path d="M${tx + 34},${ty - 8} V${ty}" stroke="${V('--dg-el')}" stroke-width="3" fill="none"/>`
      + `<circle cx="${tx + 34}" cy="${ty - 12} " r="5.5" fill="${V('--dg-alu-2')}"/>`     // 瓦斯電驛
      + `<circle cx="${tx + 34}" cy="${ty - 12}" r="2" fill="${V('--dg-cold')}"/>`
      // 吸濕呼吸器：細管 ＋ 一個裝彩色乾燥劑的小玻璃筒
      + `<path d="M${tx + 96},${ty - 8} V${ty + 6} H${tx + 108}" stroke="${V('--dg-el')}" stroke-width="2" fill="none"/>`
      + R(tx + 104, ty + 6, 10, 26, V('--dg-cold'), '', 3)
      + R(tx + 104, ty + 12, 10, 12, V('--dg-hot'), '', 2))
    + P(G3, 'he_bush', '--dg-cer',
      // ★ 高壓側朝左、明顯比低壓側高、傘裙也多（§3-C 硬規則）
      bushing(tx + 30, ty, 62, 6, '--dg-cer', '--dg-cer-2')
      + bushing(tx + 126, ty, 30, 3, '--dg-cer', '--dg-cer-2')
      + `<path d="M598,${GA - 20} H${tx + 24} V${ty - 60}" stroke="${V('--dg-cu-dim')}" stroke-width="1.8" fill="none"/>`
      + `<path d="M${tx + 126},${ty - 34} V${ty - 44} H${tx + tw + 74}" stroke="${V('--dg-cu-dim')}" stroke-width="1.8" fill="none"/>`)
    + P(G3, 'he_oltc', '--dg-el',
      cab(tx - 34, ty + 34, 32, 44, 7, '--dg-el', '--dg-el')
      + R(tx - 28, ty + 42, 20, 12, V('--dg-cold'), '', 2)
      + `<path d="M${tx - 2},${ty + 50} h6" stroke="${V('--dg-alu-3')}" stroke-width="2" fill="none"/>`);
  }

  /* ================================================================ 段 4 中壓配電盤（metal-clad）
     ★ §4：一整排等高等深的金屬櫃、櫃縫等距、每櫃正面分三段、
     至少一櫃把抽出式斷路器拉出來一半（看得到導軌與一次接觸子）、櫃頂有洩壓通道。*/
  function seg4() {
    const y0 = GB - 98, cw = 48, n = 5;
    const cells = [];
    for (let i = 0; i < n; i++) {
      const x = 20 + i * (cw + 4);
      cells.push(cab(x, y0, cw, 98, 9, '--dg-alu-2', '--dg-alu-3', '--dg-alu'));
      // 上段：低壓儀表／電驛室（小方塊電驛、指示燈、電表）
      cells.push(R(x + 6, y0 + 6, cw - 12, 24, V('--dg-frame'), '', 2));
      cells.push(`<circle cx="${x + 12}" cy="${y0 + 12}" r="1.8" fill="${V('--dg-cold')}"/><circle cx="${x + 20}" cy="${y0 + 12}" r="1.8" fill="${V('--dg-hot')}"/>`);
      cells.push(R(x + 10, y0 + 18, 12, 8, V('--dg-alu'), '', 1) + R(x + 26, y0 + 18, 12, 8, V('--dg-alu'), '', 1));
      // 中段：斷路器室　下段：電纜室
      cells.push(R(x + 6, y0 + 36, cw - 12, 30, V('--dg-frame'), '', 2));
      cells.push(R(x + 6, y0 + 72, cw - 12, 20, V('--dg-frame'), '', 2));
      cells.push(`<path d="M${x + 6},${y0 + 70} h${cw - 12}" stroke="${V('--dg-alu-3')}" stroke-width="1" fill="none"/>`);
      // 櫃頂洩壓通道：一片掀起的板
      cells.push(`<path d="M${x + 8},${y0 - 3} l8,-6 h${cw - 22} l-8,6Z" fill="${V('--dg-alu-3')}"/>`);
    }
    // 第三櫃：抽出式斷路器拉出來一半，看得到導軌與一次接觸子
    const dx = 20 + 2 * (cw + 4);
    const draw = R(dx - 26, y0 + 38, 30, 26, V('--dg-alu'), '', 2)
      + `<path d="M${dx - 26},${y0 + 40} H${dx + 6} M${dx - 26},${y0 + 62} H${dx + 6}" stroke="${V('--dg-alu-3')}" stroke-width="1.6" fill="none"/>`
      + `<path d="M${dx + 2},${y0 + 44} h10 M${dx + 2},${y0 + 52} h10 M${dx + 2},${y0 + 58} h10" stroke="${V('--dg-cu')}" stroke-width="2" fill="none"/>`
      + R(dx - 22, y0 + 44, 10, 14, V('--dg-frame'), '', 2);
    return P(G4, 'he_swgr', '--dg-alu', cells.join('') + draw);
  }

  /* ================================================================ 段 5 廠內變壓器 → UPS → PDU
     ★ §4：乾式變壓器「沒有油箱、沒有散熱片、沒有儲油櫃」，看得見三個直立樹脂線圈。
     ★ §3-A 硬規則 6：電池掛在 UPS 的直流側，是往下的分支，不是串在輸出上。*/
  function seg5() {
    const y0 = GB - 92;
    const coils = [326, 350, 374].map(cx => vcyl(cx, GB - 12, 18, 54, '--dg-resin', '--dg-el')).join('');
    return P(G5, 'he_drytx', '--dg-resin',
      R(312, GB - 14, 78, 14, V('--dg-alu-3'), 'part', 2) + coils
      // 百葉金屬護罩（只是罩子，看得穿）
      + `<path d="M308,${GB - 12} V${y0} H394 V${GB - 12}" stroke="${V('--dg-alu-2')}" stroke-width="1.6" fill="none"/>`
      + `<path d="M308,${y0 + 10} h86 M308,${y0 + 20} h86 M308,${y0 + 30} h86" stroke="${V('--dg-alu-2')}" stroke-width="1" fill="none" opacity=".7"/>`)
    + P(G5, 'he_ups', '--dg-alu',
      cab(412, y0 + 8, 56, 84, 9, '--dg-alu-2', '--dg-alu-3', '--dg-alu')
      + R(420, y0 + 16, 40, 18, V('--dg-cold'), '', 2)
      + `<path d="M424,${y0 + 22} h14 M424,${y0 + 28} h24" stroke="${V('--dg-frame')}" stroke-width="1.4" fill="none"/>`
      + `<path d="M420,${y0 + 44} h40 M420,${y0 + 50} h40 M420,${y0 + 56} h40 M420,${y0 + 62} h40 M420,${y0 + 68} h40" stroke="${V('--dg-alu-3')}" stroke-width="1.6" fill="none"/>`)
    + P(G5, 'he_batt', '--dg-cu',
      // ★ 電池櫃是一層一層的電池模組抽屜，看得出分層與極柱（畫成一顆大方塊＝錯）
      cab(490, y0 + 24, 56, 68, 9, '--dg-alu-2', '--dg-alu-3', '--dg-alu')
      + [0, 1, 2, 3].map(i => R(496, y0 + 30 + i * 16, 44, 12, V('--dg-frame'), '', 2)
        + `<circle cx="${502}" cy="${y0 + 36 + i * 16}" r="2" fill="${V('--dg-cu')}"/>`
        + `<circle cx="${534}" cy="${y0 + 36 + i * 16}" r="2" fill="${V('--dg-el')}"/>`).join(''))
    + P(G5, 'he_pdu', '--dg-alu',
      cab(570, y0 + 16, 48, 76, 9, '--dg-alu-2', '--dg-alu-3', '--dg-alu')
      + `<path d="M594,${y0 + 16} V${y0 + 2} H640" stroke="${V('--dg-cu-dim')}" stroke-width="2.2" fill="none"/>`
      + [0, 1, 2, 3, 4].map(i => R(578 + (i % 3) * 13, y0 + 40 + Math.floor(i / 3) * 16, 10, 12, V('--dg-frame'), '', 2)).join(''));
  }

  /* ================================================================ 段 6 機櫃取電
     ★ §4：匯流排槽懸吊在機櫃上方，每隔一段掛一個插接箱往下拉線（不是一堆亂拉的電線）。
     ★ §5-A：這一站**不列任何代號**（機櫃電源屬「伺服器電源與 BBU」題材）。*/
  function seg6() {
    const y0 = GB - 96, rx = [688, 776, 864];
    return P(G6, 'he_busway', '--dg-cu',
      R(670, y0 - 34, 286, 16, V('--dg-alu-2'), 'part', 3)
      + `<path d="M670,${y0 - 28} h286" stroke="${V('--dg-alu-3')}" stroke-width="1.4" fill="none"/>`
      + rx.map(x => R(x + 18, y0 - 18, 20, 14, V('--dg-alu-3'), '', 2)
        + `<path d="M${x + 28},${y0 - 4} V${y0}" stroke="${V('--dg-cu')}" stroke-width="2.4" fill="none"/>`).join('')
      + `<path d="M700,${y0 - 42} V${y0 - 34} M790,${y0 - 42} V${y0 - 34} M880,${y0 - 42} V${y0 - 34}" stroke="${V('--dg-alu-3')}" stroke-width="2" fill="none"/>`)
    + P(G6, 'he_rack', '--dg-pn-bezel',
      rx.map(x => cab(x, y0, 56, 96, 9, '--dg-pn-bezel', '--dg-pn-bezel-d', '--dg-alu-3')
        + [0, 1, 2, 3, 4, 5].map(i => R(x + 5, y0 + 6 + i * 15, 46, 11, V('--dg-frame'), '', 1.5)).join('')).join(''))
    + P(G6, 'he_shelf', '--dg-alu',
      // 電源架：1U 裡並排數個可熱插拔模組，看得出把手與風扇孔
      R(781, y0 + 51, 46, 15, V('--dg-alu-2'), 'part', 2)
      + [0, 1, 2, 3].map(i => R(783 + i * 11, y0 + 53, 9, 11, V('--dg-alu'), '', 1.5)
        + `<path d="M${784 + i * 11},${y0 + 56} h3" stroke="${V('--dg-frame')}" stroke-width="1.4" fill="none"/>`
        + `<circle cx="${789 + i * 11}" cy="${y0 + 61}" r="1.6" fill="${V('--dg-frame')}"/>`).join(''))
    + P(G6, 'he_dcbus', '--dg-cu',
      R(838, y0 + 4, 7, 88, V('--dg-cu'), 'part', 2)
      + R(926, y0 + 4, 7, 88, V('--dg-cu-dim'), '', 2)
      + `<path d="M827,${y0 + 24} h11 M827,${y0 + 48} h11 M827,${y0 + 72} h11" stroke="${V('--dg-cu-lit')}" stroke-width="2" fill="none"/>`);
  }

  /* ================================================================ 章節 ③：第二排（廠內配電 → 機櫃）
     幾何整組縮 0.66 放進 660 的畫布；標註一律在縮放群組外面，用編號圓點 ＋ 底下的圖例行。*/
  function areaRoom() {
    return `<g>
      ${T(16, 18, '④⑤⑥ 資料中心這一側：中壓配電盤分路 → 廠內變壓器降到低壓 → 不斷電系統與 PDU → 機櫃', 'hd')}
      ${T(16, 38, '★ 電池掛在不斷電系統的「直流側」，是一條往下的分支 —— 畫成「市電 → UPS → 電池 → PDU」就是畫錯了。', 'sub')}
      ${T(16, 56, '這一排每一格出來是幾伏特（對到上面那張階梯的段 4～段 5）：配電盤 22.8 kV 不降壓 → 乾式變壓器 380／220 V（★ 只有這一格降壓）→ UPS 與 PDU 也不降壓。', 'cap')}
      <g><g transform="translate(${K2X},${K2Y}) scale(${K2})">
        <g pointer-events="none">
          <path d="M16,${GB} H964" stroke="var(--dg-mute)" stroke-width="1.6" fill="none" opacity=".7"/>
          <!-- 主路徑：一律由左指向右 -->
          <path d="M262,${GB - 40} H306" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none" marker-end="url(#heAr)"/>
          <path d="M396,${GB - 40} H408" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none" marker-end="url(#heAr)"/>
          <path d="M474,${GB - 76} H566" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none" marker-end="url(#heAr)"/>
          <path d="M640,${GB - 94} H666" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none" marker-end="url(#heAr)"/>
          <!-- ★ 電池是從 UPS 直流側往下分出去的一條支線，不是串在輸出上（§3-A 硬規則 6） -->
          <path d="M440,${GB} V${GB + 14} H518 V${GB - 4}" stroke="var(--dg-warn)" stroke-width="2.6" fill="none" stroke-dasharray="8 5"/>
        </g>
        ${seg4()}${seg5()}${seg6()}
      </g></g>
      ${ndot(f2x(148), f2y(690), 1)}
      ${ndot(f2x(350), f2y(700), 2)}
      ${ndot(f2x(440), f2y(700), 3)}
      ${ndot(f2x(518), f2y(720), 4)}
      ${ndot(f2x(594), f2y(700), 5)}
      ${ndot(f2x(760), f2y(646), 6)}
      ${ndot(f2x(700), f2y(720), 7)}
      ${ndot(f2x(804), f2y(740), 8)}
      ${ndot(f2x(930), f2y(700), 9)}
      <rect class="frame" x="16" y="180" width="628" height="174" rx="8"/>
      ${T(30, 204, '這一排每一格是什麼（對到圖上的編號）', 'hd')}
      ${T(30, 226, '① 中壓配電盤（22.8 kV）：一排等高金屬櫃，每櫃一路饋線；第三櫃把抽出式斷路器拉出來一半，', 'sub')}
      ${T(30, 244, '　 看得到導軌與一次接觸子。每櫃正面分三段：儀表／電驛室、斷路器室、電纜室。★ 同樣不降壓。', 'sub')}
      ${T(30, 262, '② 乾式（模鑄）變壓器：降到 380／220 V —— 它沒有油箱、沒有散熱片、沒有儲油櫃，那三個「沒有」就是', 'sub')}
      ${T(30, 280, '　 它的長相；罩子裡看得見三個直立樹脂線圈。', 'sub')}
      ${T(30, 298, '③ UPS（撐到發電機起來那幾分鐘）　④ 電池櫃：一層一層的電池模組抽屜，看得出分層與極柱', 'sub')}
      ${T(30, 316, '⑤ PDU　⑥ 匯流排槽（懸吊在機櫃上方，插接箱往下拉線）　⑦ 機櫃　⑧ 電源架（1U 裡並排可熱插拔模組）', 'sub')}
      ${T(30, 334, '⑨ 直流匯流排。★ 這一站不列代號（屬「伺服器電源與 BBU」題材）。', 'sub')}
    </g>`;
  }

  /* ================================================================ 章節 ④：工程統包與安裝帶（§5-B(b)） */
  function areaEpc() {
    return `<g>
      ${P(GE, 'he_epc', '--dg-fws', '<rect class="frame part" x="16" y="8" width="628" height="120" rx="8"/>')}
      <g pointer-events="none">
        ${T(30, 32, '工程統包與安裝：把這些設備裝起來、接起來的人（橫跨段 3～段 6，不是一台設備）', 'hd')}
        ${T(30, 54, '2404 漢唐｜機電（M&amp;E）統包與廠務系統整合 —— ★ 不製造重電設備。主戰場是半導體晶圓廠的無塵室', 'sub')}
        ${T(30, 72, '　 與廠務機電（含電力系統、二次配、機台 hook-up）。它在本站屬於「廠務工程」族群。', 'sub')}
        ${T(30, 94, '1513 中興電｜設備商兼變電所統包 —— 它同時出現在段 2（做 GIS）與這一帶（做統包），', 'sub')}
        ${T(30, 112, '　 兩個角色不一樣。', 'sub')}
      </g>
    </g>`;
  }

  /* ================================================================ 章節 ⑤：電力路徑六格 */
  function areaFlow() {
    return `<g>
      ${T(16, 18, '電力路徑（六格）　★ GIS 在主變壓器之前（進線側的開關）、中壓配電盤在主變壓器之後；兩者對調就是錯的', 'cap')}
      ${D.processBar(16, 28, [
    { seg: G0, t: '① 發電與升壓', s: '電廠／再生能源＋儲能' },
    { seg: G1, t: '② 超高壓輸電', s: '鐵塔架空線／地下電纜' },
    { seg: G2, t: '③ 變電所：開關與降壓', s: 'GIS 不降壓，變壓器才降壓' },
    { seg: G4, t: '④ 中壓配電', s: '配電盤：同樣不降壓' },
    { seg: G5, t: '⑤ 不斷電與低壓配電', s: '乾式變壓器·UPS·PDU' },
    { seg: G6, t: '⑥ 機櫃取電', s: '匯流排槽·機櫃·電源架' },
  ], 196, { cols: 3 })}
    </g>`;
  }

  /* ================================================================ 整張圖 */
  function transformerGis() {
    return `<svg class="dg dgm rs dghe" viewBox="0 0 ${CW} 450" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ 這一段的註解裡一個角括號都不准出現 —— SVG 裡的 style 是被當標記解析的，
           寫一個長得像標籤的東西進去會讓整張樣式表變成 0 條規則（DECISIONS #231）。

           壓暗只在「真的有主角」的時候才作用：haspart 是 highlightSegments 在
           「這張圖上真的有一個被點的零件」時掛上去的 class。這條鏈在供應鏈資料裡沒有環節，
           所以剛進頁面時可能一個零件都沒被選起來 —— 那時候壓暗只會讓整張圖看不清楚。
           前面那個 svg 型別選擇器是必要的：不加的話特異性跟 diagrams.js 的那一條一樣。*/
        svg.dghe:not(.haspart) [data-seg].dim{opacity:1}
        svg.dghe.haspart [data-seg].dim{opacity:.34}
        /* 螢光感壓下來（AGENTS：要的是精密儀器不是電競 RGB）：只有你點的那一個會發光。
           ★ 發光掛在「零件的內層包裝」（.pw）上，不是掛在每一個 .part 上：
           一站的幾何常常是十幾個形狀（五個配電櫃、三段 GIS 母線筒），
           一個一個加 drop-shadow 就是十幾圈光暈疊在一起。
           掛在 .pw 上只有一圈，而且 .pw 帶的是材質色（外層的 --c 是 JS 寫上去的灰）。
           ⚠ 用 .pw 而不是子選擇器，是因為子選擇器的那個符號是角括號，
             而這個 style 在 SVG 裡是被當標記解析的（DECISIONS #231）。*/
        svg.dghe [data-seg].sel .part{stroke-width:1.6;filter:none}
        svg.dghe [data-seg]:hover .part{stroke-width:1.8;filter:none}
        svg.dghe [data-seg].sel-part .part{stroke-width:2.4;filter:none}
        svg.dghe [data-seg].sel-part .pw{filter:drop-shadow(0 0 5px var(--c))}
        /* 章節裡的編號圓點（不是卡片錨點，所以 diagrams.js 的 .anc 規則吃不到，樣式在這裡自己給） */
        svg.dghe .ndot{fill:var(--dg-accent-2d);opacity:.92}
        svg.dghe .nnum{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);font-weight:700;
          fill:var(--dg-no-ink);dominant-baseline:central;text-anchor:middle}
      </style>
      <defs>
        <marker id="heAr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9Z" fill="var(--dg-accent-2d)"/>
        </marker>
      </defs>
      <!-- 標題與導讀：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">電力路徑：變壓器與 GIS</text>
      <text class="cap ext" x="0" y="0">電廠 → 超高壓輸電 → 變電所開關（GIS）→ 主變壓器降壓 → 中壓配電盤 → 不斷電系統與 PDU → 機櫃電源。★ 降壓的只有變壓器，開關設備不降壓 —— 這是這張圖唯一一條非記不可的規則。灰色虛線＝另一條常見路徑：161 → 69 kV（一次變電所）→ 22.8／11.4 kV（二次變電所）；台灣兩條路徑都存在，一張圖只畫一條主線。資料中心實際受電電壓等級依容量與台電供電可行性而定，圖上為示意。資料中心這一側、工程統包帶與六格流程收在下面三段。</text>

      <!-- ================= §1-a 電壓階梯（永遠看得到；這張圖的命題）================= -->
      ${ladder()}

      <!-- ================= §1-b 第一排：電網 → 變電所（永遠看得到）=================
           幾何整組縮 0.70 放進 660 的畫布；說明全部是 HTML 卡片，畫布上只有編號圓點與引線。-->
      ${T(16, 208, '② 電網這一側：電廠升壓 → 架空線與地下電纜 → 變電所的開關（GIS）→ 主變壓器把電壓拉下來', 'hd')}
      <!-- ⚠ 外面一定要再包一層 g：wireFolds() 的 solidBottom 量的是 svg 直屬子節點的 getBBox()，
           而 getBBox() 不含元素自己的 transform —— 縮放群組直接當 svg 的子節點，量到的會是縮放前的高度，
           於是第一條章節列被推下去、中間空出一大塊（silicon_wafer 那張實測過）。-->
      <g><g transform="translate(${K1X},${K1Y}) scale(${K1})">
        ${seg0()}${seg1()}${seg2()}${seg3()}
        <g pointer-events="none">
          <path d="M16,${GA} H900" stroke="var(--dg-mute)" stroke-width="1.4" fill="none" opacity=".7"/>
          ${person(628, GA)}
        </g>
      </g></g>
      ${T(444, 356, '↑ 1.7 m 比例小人', 'cap')}

      <!-- ================= 說明卡片（HTML，左右兩欄；引線由 externalize 畫，錨點在畫布上）=================
           左欄錨點 x 小於 330、右欄大於 330 —— 引線只從自己那一側進來，不橫越整張圖。-->
      ${card({ seg: GV, part: 'he_ladder', no: 1, side: 'r', color: CC.accent, ax: 636, ay: 110,
    title: '① 電壓階梯：哪幾格降壓、哪幾格不降壓', sub: [
    '★ 這是整張圖的命題：電壓只在變壓器那幾格往下掉（段 0 升、段 3 降、段 5 降）。',
    'GIS（段 2）與中壓配電盤（段 4）只做切斷、導通、隔離、接地，電壓進去多少出來就多少，所以階梯在那兩格必須是平的。',
    '圖例：粉色豎線＝真的降壓（只出現在變壓器）；圓點＝接上但不降壓（開關設備）；灰虛線＝另一條常見路徑。',
    '階高與電壓不成比例（345 kV 到 220 V 差三個數量級，畫不出來）。'] })}
      ${card({ seg: G0, part: 'he_gen', no: 2, side: 'l', color: CC.mute, ax: f1x(36), ay: f1y(460),
    title: '⓪ 電廠與升壓變壓器（電網側）', sub: [
    '電廠 → 升壓：發出來的電先升到超高壓，才進得了輸電線。',
    '★ 唯一一次升壓發生在「進入輸電線之前」，不是之後。畫成灰色剪影，因為它是電網那一端。'] })}
      ${card({ seg: G0, part: 'he_re', no: 3, side: 'l', color: CC.si, ax: f1x(68), ay: f1y(396),
    title: '再生能源與電網級儲能（段 0 分支）', sub: [
    '★ 太陽能與電網級儲能併在「電網側」（段 1 之前），不是併在機房裡。'] })}
      ${card({ seg: G1, part: 'he_tower', no: 4, side: 'l', color: CC.alu, ax: f1x(186), ay: f1y(340),
    title: '① 超高壓輸電（345 kV）：鐵塔架空線', sub: [
    '每相吊一串礙子（一串多片傘裙盤，不是一顆）、導線是分裂的。',
    '市區走地下電纜 —— 台廠做的是「這條線本身」。'] })}
      ${card({ seg: G1, part: 'he_cable', no: 5, side: 'l', color: CC.cu, ax: f1x(252), ay: f1y(446),
    title: '交連聚乙烯（XLPE）電纜剖面', sub: [
    '由內到外六層，順序寫死：導體 → 內半導電層 → XLPE 絕緣 → 外半導電層 → 金屬遮蔽 → 外被。'] })}
      ${card({ seg: G2, part: 'he_ais', no: 6, side: 'l', color: CC.mute, ax: f1x(346), ay: f1y(330),
    title: '對照組：AIS（露天瓷瓶＋裸露刀閘）', sub: [
    '同樣的功能要佔大得多的一塊地 —— 這就是 GIS 存在的理由。'] })}
      ${card({ seg: G2, part: 'he_gis', no: 7, side: 'l', color: CC.alu, ax: f1x(432), ay: f1y(400),
    title: '② 變電所：氣體絕緣開關設備（GIS）', sub: [
    '★ 水平圓筒不是方箱：開關、隔離、接地全部封進充 SF6 的接地金屬圓筒裡。',
    '法蘭接合（每一段之間就是一個氣室分界）、斷路器氣室明顯較粗、外殼上有密度錶、整體接地。',
    '★ 只切斷與導通，「不降壓」；省地，適合空間受限處。'] })}
      ${card({ seg: G3, part: 'he_bush', no: 8, side: 'r', color: CC.cer, ax: f1x(678), ay: f1y(382),
    title: '套管（bushing）：高壓側朝左', sub: [
    '★ 高壓側明顯比低壓側高、傘裙也多。只表達高低關係，不標尺寸。'] })}
      ${card({ seg: G3, part: 'he_tx', no: 9, side: 'r', color: CC.el, ax: f1x(740), ay: f1y(430),
    title: '③ 主變壓器：161 → 22.8 kV', sub: [
    '這一台才是真正把電壓拉下來的。基礎滾輪、油箱、箱壁上的溫度計與油位計。',
    '交期長、產能有限，是這波最卡的一段。★ 不畫繞組剖面（查不到可引用來源，寧可不畫也不編）。'] })}
      ${card({ seg: G3, part: 'he_rad', no: 10, side: 'r', color: CC.alu, ax: f1x(858), ay: f1y(430),
    title: '散熱片（垂直薄片）', sub: [
    '★ 一眼認出油浸式變壓器的特徵：上下各一根集管接回油箱。畫成水平橫條就變成冷氣機了。'] })}
      ${card({ seg: G3, part: 'he_cons', no: 11, side: 'r', color: CC.el, ax: f1x(700), ay: f1y(362),
    title: '儲油櫃、瓦斯電驛與吸濕呼吸器', sub: [
    '★ 儲油櫃是橫放的圓筒，架在油箱上方一側（畫成直立圓桶＝錯）。',
    '呼吸器是一支裝彩色乾燥劑的小玻璃筒；瓦斯電驛在儲油櫃與油箱之間的那根管子上。'] })}
      ${card({ seg: G3, part: 'he_oltc', no: 12, side: 'r', color: CC.el, ax: f1x(630), ay: f1y(430),
    title: '有載分接開關（OLTC）機構箱', sub: [
    '掛在油箱一側的獨立箱體 —— 不停電就能微調匝比。'] })}

      <!-- 結論與警語卡片（沒有錨點，排在編號卡之後） -->
      ${note({ side: 'l', order: 90, color: CC.accent, title: '降壓的只有變壓器', lines: [
    '① 變壓器＝把電壓換掉（段 0 升、段 3 降、段 5 降）。',
    '② 開關設備（GIS、配電盤）＝切斷、導通、隔離、接地，電壓進去多少出來就多少。',
    '③ 所以階梯在段 2 與段 4 是平的。看到往下掉就是錯的。'] })}
      ${note({ side: 'r', order: 91, color: CC.fws, title: '為什麼重電廠吃得到這波', lines: [
    '① 資料中心是特高壓等級的大用戶，自己要一座受電站 —— 等於把圖上段 2 到段 5 全部買一套。',
    '② 電網那一端也要跟著擴建：輸電線、變電所、主變壓器一起排隊。',
    '③ 這條路徑上的東西台廠本來就在做，而且重資產、長交期、要認證。'] })}
      ${note({ side: 'l', order: 98, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: [
    '這條產業鏈（基礎建設與能源）在供應鏈資料裡還沒有建環節，所以這一頁沒有環節色標；零件小卡上那顆「環節 →」按下去會是 0 筆 —— 那不是壞掉。',
    '要篩成分股請用下面的族群卡片與成分股表。點零件只會亮起來，並在小卡上回答「這個零件是誰做的」，不會動到下方清單。'] })}
      ${note({ side: 'r', order: 99, title: '原創等角示意圖，非實物比例', lines: [
    '電壓階梯為示意，階高與電壓不成比例；★ 階梯在 GIS（段 2）與配電盤（段 4）必須是平的 —— 看到階梯在開關那一格往下掉，就是圖畫錯了。',
    '資料中心實際受電電壓等級依容量與台電供電可行性而定，圖上為示意。',
    '本圖不放任何在手訂單、市占率、營收占比或能見度年份（會過期）。'] })}

      <!-- ================= ③ 第二排：廠內配電 → 機櫃（預設收合）================= -->
      ${fold('he2', '③ 資料中心這一側：配電盤 → 乾式變壓器 → UPS ＋ 電池 → PDU → 機櫃',
    '抽出式斷路器拉出來一半、乾式變壓器的三個「沒有」、電池掛在直流側、匯流排槽與電源架', areaRoom())}

      <!-- ================= ④ 工程統包與安裝帶（預設收合）================= -->
      ${fold('he3', '④ 工程統包與安裝：把這些設備裝起來、接起來的人',
    '橫跨段 3～段 6，不是一台設備；2404 漢唐與 1513 中興電各自的角色', areaEpc())}

      <!-- ================= ⑤ 電力路徑六格（預設收合）================= -->
      ${fold('he4', '⑤ 電力路徑（六格）：GIS 在主變壓器之前、配電盤在之後',
    '發電與升壓 → 超高壓輸電 → 變電所 → 中壓配電 → 不斷電與低壓配電 → 機櫃取電', areaFlow())}
    </svg>`;
  }


  /* ================================================================ 註冊
     `parts` ＝點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。

     ★ 這張圖的 R4／R5 處境（跟輕油裂解那張一樣，要先講清楚）：
       `site/data/supply_chain.json` 只有 semiconductor／ai_server／electronics 三條鏈、114 家公司，
       **重電這一條一家都沒有**（實測：1503／1504／1513／1514／1519／1609／1618／3576／2404
       九檔在裡面一個都查不到）。所以 `cos` 填了也撈不到公司卡，小卡會走 `none` 那一列。
       `cos` 仍然照填，因為將來補進 supply_chain.yaml 時這些卡片會自動活過來。
     ★ 公司與角色描述**一個字都不是繪圖端編的**，全部來自規格書 §5-E／§6-A11 已經查證並附來源的那張表
       （各公司官網產品頁、台電承製能力審查說明書、法說會備忘錄）。
       規格書明文禁止的敘述一律不寫：
         · 亞力 1514 的 GIS 一定要標「中壓級（36 kV 級以下）」（§5-E，第二容易被抓的錯）
         · 東元 1504 不准寫成「做配電盤」或「做變壓器」（§6-B8：只查得到營業項目層級）
         · 漢唐 2404 只能出現在工程統包，而且必須寫「不製造重電設備」（§5-B(b)）
     ★ 這一頁的成分股是 `groups.yaml` 的 `heavy_electric` 五檔（1503／1504／1513／1514／1519）。
       1609 大亞在「電器電纜」族群、3576 聯合再生在「太陽能產業」族群（同屬基礎建設與能源鏈，
       下方成分股表看得到）；2404 漢唐在「廠務工程」族群（半導體鏈）；
       1618 合機**本站目前沒有把它放進任何族群**。凡是提到這幾檔，卡片上一律註明它在哪一格，
       不讓人誤以為它們是重電設備族群的成分股。*/
  const NOSC = '（重電這一條鏈在供應鏈資料裡還沒有建環節，所以這張卡撈不到公司卡片；成分股名單在下方表格。）';

  window.DG.register('heavy_electric', {
    level: 'group', chain: 'infrastructure',
    name: '電力路徑：變壓器與 GIS',
    draw: transformerGis, native: CW, scene: null,   /* ★ 2026-09-23：980 → 660（v2 版面，說明外掛成 HTML 卡片）。scene 仍是 null —— 3D 是 Andy 親口否決的。*/
    q: 'AI 資料中心的電從哪裡來？從 345 kV 電網走到機櫃直流，哪幾格是降壓、哪幾格只是開關，台廠站在哪幾格？',
    parts: {
      he_ladder: {
        name: '電壓階梯：哪幾格降壓、哪幾格不降壓',
        desc: '★ 這是整張圖的命題：電壓只在變壓器那幾格往下掉（段 0 升、段 3 降、段 5 降）。GIS（段 2）與中壓配電盤（段 4）只做切斷、導通、隔離、接地，電壓進去多少出來就多少，所以階梯在那兩格必須是平的。階高與電壓不成比例（345 V 到 220 V 差三個數量級，畫不出來）。',
        items: [],
        cos: [],
        none: '這不是一個零件，是這張圖的命題。★ 圖上不放任何在手訂單、市占率或營收占比 —— 那些會過期，而且要用得走供應鏈資料的 as_of／source／confidence 機制，不該寫死在圖裡。',
      },
      he_gen: {
        name: '電廠與升壓變壓器（段 0）',
        desc: '電廠發出來的電先經升壓變壓器升到超高壓，才進得了輸電線 —— ★ 唯一一次升壓發生在「進入輸電線之前」，不是之後。這一格畫成灰色剪影，因為它是電網那一端，不是這張圖的主題。',
        items: ['升壓變壓器'],
        cos: [],
        none: '發電端不在這個族群的範圍內，本圖只把它當成「電從哪裡來」的方向標記。這一格的台電與發電業者不是台股重電設備族群的成分股 —— 查不到就寫查不到，不編一個對應。',
      },
      he_re: {
        name: '再生能源與電網級儲能（段 0 分支）',
        desc: '★ 太陽能與電網級儲能併在「電網側」（段 1 之前），不是併在機房裡。把太陽能板畫在機房屋頂旁邊接進 PDU 是另一件事，不是這張圖。',
        items: ['太陽能模組', '電站系統 EPC', '儲能與能源管理（EMS）'],
        cos: ['3576'],
        none: '這一格在台股對應到 3576 聯合再生：太陽能電池模組製造、電站系統與 EPC、儲能與能源管理（EMS）。★ 它在本站屬於「太陽能產業」族群（同屬基礎建設與能源鏈，下方成分股表看得到），不是「重電設備」族群的成分股。' + NOSC,
      },
      he_tower: {
        name: '輸電鐵塔、懸垂礙子串與分裂導線',
        desc: '格子狀鋼架鐵塔，每一相吊的是「一串」多片傘裙盤的絕緣礙子（不是一顆），導線是分裂導線（同一相多根並行）。345 kV 是台灣目前最高的輸電電壓。',
        items: ['架空導線', '絕緣礙子串'],
        cos: [],
        none: '鐵塔鋼構與礙子本身在本站的族群名單裡沒有對應的台股 —— 查不到就寫查不到，不編一個對應。這一段台廠真正吃得到的是下面那條電纜（見「交連聚乙烯電力電纜剖面」）。',
      },
      he_cable: {
        name: '交連聚乙烯（XLPE）電力電纜剖面',
        desc: '市區走地下電纜。剖面由內到外的順序寫死：導體 → 內半導電層 → 交連聚乙烯（XLPE）絕緣 → 外半導電層 → 金屬遮蔽／被覆 → 外被。台廠在這一段做的就是「這條線本身」。',
        items: ['交連聚乙烯（XLPE）電力電纜', '漆包線', '裸銅線'],
        cos: ['1609', '1618'],
        none: '做這一格的台股：1609 大亞（交連聚乙烯電力電纜，含台電 69／161／345 kV 輸電用線與 25 kV 以下配電用線；另做漆包線，用於變壓器與馬達繞組）與 1618 合機（交連聚乙烯電力電纜為主要營收來源，高壓與超高壓）。★ 1609 在本站屬於「電器電纜」族群（同屬基礎建設與能源鏈）；1618 本站目前沒有把它放進任何族群 —— 兩檔都不是「重電設備」族群的成分股。' + NOSC,
      },
      he_gis: {
        name: '氣體絕緣開關設備（GIS）',
        desc: '★ 決定性特徵是「水平的圓筒」，不是方箱 —— 畫成露天的瓷瓶加裸露刀閘就是畫成了它的對照組（AIS）。GIS 把斷路器、隔離開關、接地開關、比流器、比壓器、匯流排、套管、電纜連接裝置與避雷器，全部封進充 SF6 且充分接地的金屬外殼裡。圓筒之間用法蘭接合，每一段就是一個氣室，外殼上有氣體密度錶；斷路器氣室明顯比母線圓筒粗，下方掛操作機構箱。★ 它只切斷與導通，「不降壓」。',
        items: ['氣體絕緣開關設備（GIS）', '斷路器', '隔離開關', '接地開關'],
        cos: ['1513', '1514'],
        none: '做這一格的台股：1513 中興電（高壓 GIS、發電機、變電所建置）與 1514 亞力（★ 「中壓級」：公司官網揭露的是 36 kV 級以下的 GIS 與 23 kV SF6 GIS，跟 161 kV 級的高壓 GIS 不是同一個等級，不註明等級會讓人以為它做超高壓 GIS）。' + NOSC,
      },
      he_ais: {
        name: '氣中絕緣開關場（AIS）—— GIS 的對照組',
        desc: '同樣的功能，露天的瓷瓶加裸露刀閘加鋼構架要佔大得多的一塊地。★ 這是 GIS 存在的理由（體積小、可靠度高、維護週期長、模組式組合，尤其適用於 69 kV 級以上的變電所），畫在這裡是當對照組，不是 GIS 本身。',
        items: [],
        cos: [],
        none: '這一格是用來對照的縮圖，不是這張圖要指認的產品。做開關設備的台股見旁邊的「氣體絕緣開關設備（GIS）」那一格。',
      },
      he_tx: {
        name: '油浸式電力變壓器：油箱',
        desc: '整條路徑上最大的一件，也是★真正把電壓拉下來的那一台。深灰鋼板油箱、表面有加強肋，底部有軌道式滾輪，箱壁上有溫度計與油位計。電壓只在這種格子往下掉 —— 開關設備不降壓。這一段交期長、產能有限，是這波最卡的一段。',
        items: ['電力變壓器', '油箱'],
        cos: ['1519', '1503'],
        none: '做這一格的台股：1519 華城（電力變壓器為主力，含超高壓等級，兼配電盤與工程承包）與 1503 士電（重電：變壓器、配電盤、高低壓開關；另有電裝品與自動化事業）。' + NOSC,
      },
      he_rad: {
        name: '散熱器（垂直散熱薄片）',
        desc: '★ 一眼認出油浸式變壓器的特徵：側面一排「垂直」的薄片，上下各一根集管接回油箱。畫成水平橫條就變成冷氣機了。變壓器的損耗變成熱，熱靠油循環帶到這一排薄片散掉。',
        items: ['散熱器'],
        cos: ['1519', '1503'],
        none: '散熱器是變壓器的一部分，由變壓器廠整台交出來。做變壓器的台股見「油浸式電力變壓器：油箱」那一格（1519 華城、1503 士電）。' + NOSC,
      },
      he_cons: {
        name: '儲油櫃（油枕）、吸濕呼吸器與瓦斯電驛',
        desc: '★ 儲油櫃是「橫放」的圓筒，架在油箱上方一側（畫成直立圓桶就是畫錯了）。油會熱脹冷縮，儲油櫃就是那個緩衝。儲油櫃下掛吸濕呼吸器（細管接一個裝彩色乾燥劑的小玻璃筒），儲油櫃到油箱的連通管上裝瓦斯電驛 —— 內部有故障放氣時它就動作。',
        items: ['儲油櫃（油枕）', '吸濕呼吸器', '瓦斯電驛'],
        cos: ['1519', '1503'],
        none: '這幾件都是變壓器的附件，由變壓器廠整台交出來。做變壓器的台股見「油浸式電力變壓器：油箱」那一格（1519 華城、1503 士電）。' + NOSC,
      },
      he_bush: {
        name: '高壓側與低壓側套管（bushing）',
        desc: '★ 高壓側朝左（進線）、低壓側朝右（出線），而且「高壓側套管明顯比低壓側高、傘裙也多」 —— 兩側畫一樣高就是畫錯了（絕緣距離的必然結果）。套管的工作是把帶電的導體從油箱裡引出來，同時撐住對地的絕緣。',
        items: ['套管（bushing）'],
        cos: ['1519', '1503'],
        none: '套管是變壓器的一部分，由變壓器廠整台交出來。★ 套管本體（瓷／複合材）的台灣供應商本次查不到可引用的具名來源 —— 查不到就寫查不到，不編一個對應。做變壓器的台股見「油浸式電力變壓器：油箱」那一格。' + NOSC,
      },
      he_oltc: {
        name: '分接頭切換器（OLTC）驅動機構箱',
        desc: '油箱側面一個獨立的方箱，裡面是帶載分接頭切換器的驅動機構（有觀察窗）。電網電壓會飄，OLTC 就是在不停電的情況下換分接頭、把輸出電壓調回來的那一套。',
        items: ['分接頭切換器（OLTC）'],
        cos: ['1519', '1503'],
        none: 'OLTC 通常是變壓器廠外購的專業零件，但「台灣是誰做 OLTC」本次查不到可引用的具名來源 —— 查不到就寫查不到，不編一個對應。整台變壓器的台股見「油浸式電力變壓器：油箱」那一格。' + NOSC,
      },
      he_swgr: {
        name: '中壓配電盤（metal-clad 開關櫃）',
        desc: '★ 一整排等高、等深的金屬櫃並排、櫃縫等距 —— 不是一個大方塊。每一櫃正面分三段：上段是低壓儀表／電驛室（面板上有小方塊電驛、指示燈、電表）、中段是斷路器室、下段是電纜室；至少一櫃把「抽出式斷路器」拉出來一半，看得到導軌與一次接觸子，那就是 metal-clad 跟「一個鐵箱」的差別。櫃頂有洩壓通道。★ 它同樣「不降壓」，電從這裡分岔去各個負載。',
        items: ['中壓配電盤', '抽出式斷路器', '高低壓開關'],
        cos: ['1503', '1514', '1504'],
        none: '做這一格的台股：1503 士電（重電：變壓器、配電盤、高低壓開關）與 1514 亞力（配電盤、高低壓開關櫃）。1504 東元也在這條路徑上，但它的公開資料只支撐到「機電系統與電力能源事業、營業項目含發電／輸電／配電機械，以馬達起家」這個程度 —— 再往下就是編的，所以這裡不寫「東元做配電盤」。' + NOSC,
      },
      he_drytx: {
        name: '乾式（模鑄）變壓器',
        desc: '★ 它的識別特徵是三個「沒有」：沒有油箱、沒有散熱片、沒有儲油櫃。看得見三個直立的環氧樹脂圓柱線圈站在底座上，外面罩一個帶百葉或網孔的金屬護罩。室內（靠近機房）用這一台，因為沒有油就沒有漏油與火載量的問題。它是路徑上的第三次降壓：22.8 kV → 380／220 V。',
        items: ['模鑄型變壓器', '油浸式變壓器', '非晶質變壓器'],
        cos: ['1514', '1503'],
        none: '做這一格的台股：1514 亞力（變壓器：模塑型／油浸式／非晶質）與 1503 士電（重電事業含變壓器）。' + NOSC,
      },
      he_ups: {
        name: '不斷電系統（UPS）主機櫃',
        desc: '正面有顯示面板與進出風百葉。市電斷掉時，UPS 撐住那幾分鐘，等發電機起來接手。★ 它排在 PDU 之前、機櫃之前，順序不能對調。',
        items: ['不斷電系統（UPS）', '通訊電源 SMR'],
        cos: ['1514'],
        none: '做這一格的台股是 1514 亞力：電力電子事業含通訊電源（SMR）、不斷電系統（UPS）、太陽光電變流器與充電樁。' + NOSC,
      },
      he_batt: {
        name: '電池櫃（UPS 的直流側）',
        desc: '★ 電池櫃是一層一層的電池模組抽屜，看得出分層與極柱 —— 畫成一顆大方塊就是畫錯了。而且★它是從 UPS 的「直流側」往下分出去的一條支線，不是串在 UPS 的輸出上：畫成「市電 → UPS → 電池 → PDU」是錯的。',
        items: ['UPS 電池'],
        cos: [],
        none: '資料中心 UPS 的電池櫃「台灣是誰做」本次查不到可引用的具名來源，而且它跟伺服器機櫃裡的備援電池模組（BBU）不是同一件事 —— 查不到就寫查不到，不編一個對應。BBU 屬於「伺服器電源與 BBU」那個族群，不在這張圖上。' + NOSC,
      },
      he_pdu: {
        name: '電力分配單元（PDU）櫃',
        desc: '落地櫃，上方出線，輸出是一排分路開關。它把 UPS 出來的低壓電再分成很多路，送到各排機櫃。順序固定：UPS → PDU → 機櫃。',
        items: ['電力分配單元（PDU）'],
        cos: [],
        none: '資料中心等級的 PDU 櫃「台灣是誰做」本次查不到可引用的具名來源 —— 查不到就寫查不到，不編一個對應。做低壓配電盤與電力電子的台股見「中壓配電盤」與「不斷電系統（UPS）」那兩格。' + NOSC,
      },
      he_busway: {
        name: '匯流排槽（busway）與插接箱',
        desc: '★ 機櫃上方懸吊一條矩形金屬槽，每隔一段掛一個插接箱往下拉線到機櫃 —— 不是一堆亂拉的電線。機櫃功率一路往上，走電纜會粗到拉不動，所以改走匯流排槽。',
        items: ['匯流排槽（busway）', '插接箱'],
        cos: [],
        none: '★ 這一站不列代號：資料中心機櫃側的匯流排槽與機櫃電源屬於「伺服器電源與 BBU」那個題材，不是重電設備族群。這張圖畫到這裡是為了讓路徑走完，不是為了指認台股。',
      },
      he_rack: {
        name: '伺服器機櫃',
        desc: '電力路徑的終點：一整櫃的運算托盤。★ 這一站不列代號 —— 機櫃與機櫃電源是另一條鏈（AI 伺服器）的事，這張圖只負責把「電怎麼走到這裡」講完。',
        items: [],
        cos: [],
        none: '★ 這一站不列代號：機櫃與機櫃電源屬於 AI 伺服器那條鏈，看「AI 伺服器：機櫃與運算托盤」與「伺服器電源：PSU 與 BBU」那兩張圖。',
      },
      he_shelf: {
        name: '電源架（power shelf）與電源供應器模組',
        desc: '機櫃裡的一層，並排數個可熱插拔的電源供應器模組（看得出把手與風扇孔）。它把機櫃拿到的交流電變成機櫃內部用的直流。',
        items: [],
        cos: [],
        none: '★ 這一站不列代號：電源架與電源供應器屬於「伺服器電源與 BBU」那個題材，看「伺服器電源：PSU 與 BBU」那張圖。',
      },
      he_dcbus: {
        name: '機櫃直流匯流排（DC busbar）',
        desc: '機櫃背面一條垂直的銅排，很厚 —— 因為機櫃功率越來越高，同樣的功率在低電壓下就是很大的電流，導體只能越做越粗。這也是業界正在把機櫃直流電壓往上推的原因。★ 這一格的電壓是進行式不是定論，所以圖上不標數字。',
        items: [],
        cos: [],
        none: '★ 這一站不列代號：機櫃直流匯流排屬於「伺服器電源與 BBU」那個題材，不是重電設備族群。',
      },
      he_epc: {
        name: '工程統包與安裝（橫跨段 3～段 6）',
        desc: '★ 這一帶不是一台設備，是「把這些設備裝起來、接起來的人」。它存在的理由就是回答「做工程的公司為什麼會在這張圖上」—— 他們不製造設備，但整座受電站與廠務機電是他們統包起來的。',
        items: ['機電（M&E）統包', '變電所統包'],
        cos: ['2404', '1513'],
        none: '這一帶的台股：2404 漢唐（高科技廠房整廠建置、無塵室統包、機電整合含電力系統、二次配、機台 hook-up；★ 「不製造重電設備」，主戰場是半導體晶圓廠；它在本站屬於「廠務工程」族群，不是重電設備族群的成分股）與 1513 中興電（設備商兼變電所統包 —— 它同時出現在段 2 做 GIS，兩個角色不一樣，不要把它跟漢唐當成同一種公司）。' + NOSC,
      },
    },
  });
})();
