/* 輕油裂解廠 —— docs/diagram_plan.md 的第 13 張（族群 `petrochemical`、traditional 鏈）

   合約＝`docs/diagram_specs/naphtha_cracker.md`。這個檔只實作，不重新決定規格。
   位階更高的是 `docs/diagram_purpose.md`（R1～R6）：圖不是插圖，是「誰在做什麼」的入口。

   規格書裡已經寫死、這裡照辦的幾件事
   ------------------------------------
     · §3-A 硬規則 1  煉油廠與裂解廠是**兩個廠**（石油腦從左邊界外進來）
     · §3-A 硬規則 3  急冷 → 壓縮 → 分離，順序不准對調
     · §3-A 硬規則 4  碳數由小到大脫出：冷箱／脫甲烷 → 脫乙烷 → 脫丙烷 → 脫丁烷
     · §3-A 硬規則 5  精餾塔一定排在對應的「脫某某塔」之後
     · §3-A 硬規則 6  丁二烯從**混合碳四**抽取，不從爐子直接拉一條線
     · §3-A 硬規則 7  芳香烴來自**裂解汽油加氫後**的抽取
     · §3-A 硬規則 8  ★ PTA 的原料是對二甲苯（PX），走芳香烴線 —— **不接在乙烯下面**
     · §3-A 硬規則 9  ★ 苯乙烯（SM）同時吃乙烯與苯，所以它一定有**兩條線匯進來**
     · §3-A 硬規則 10 PVC 不是乙烯直接聚合：乙烯＋氯 → EDC → VCM → PVC，中間看得到 VCM
     · §3-A 硬規則 12 氫氣與甲烷是**回頭當燃料的分支**，不是並排的第五支產品
     · §3-D           裂解價差帶是**靜態**的，不標任何數值，而且倒掛那張插圖不可省略
     · §4             冷箱是方箱不是塔；六支塔高度明顯不一樣；丙烯與丁二烯是**球槽**
     · §5-E           四檔成分股每一檔都要在圖上找得到；★ 台泥 1101 不准出現
     · §6-C1          價差、產能、市占、營收占比、EPS 一律不進圖

   為什麼是「正立面 ＋ 等角厚度」而不是整場等角
   --------------------------------------------
   規格書 §0-E 要的是 2.5D。一座裂解廠的資訊有一半在「誰高誰矮」
   （爐子高、脫甲烷塔更高、球槽矮、冷箱是矮方箱）。整場等角會把每一支塔壓成 30 度斜柱，
   六支塔的高度差在斜面上看不出來 —— 那正是 §4 要求「一排等高的圓柱＝錯」的那一條。
   所以塔與槽畫成**正立面**（高度差一眼看得出），再用頂橢圓與右側暗面給它厚度，
   方箱類（爐體、冷箱）畫成 2.5D 方箱。這跟 `site/dg/ic_substrate.js` 的取捨是同一套理由。

   ★ 顏色怎麼走（這一段不照做，整張圖會變灰）
   --------------------------------------------
   `supply_chain.yaml` 目前只建了 semiconductor／ai_server／electronics 三條鏈，
   **石化鏈一個環節都沒有**。而 `site/industry.js` 的 highlightSegments() 會對每一個
   `[data-seg]` 節點寫上 inline 的 `--c: segColor(seg)`，未知的環節 id 一律回灰
   —— 也就是「掛了 data-seg 就整張圖灰掉」。
   但是**不掛 data-seg 就完全點不動**：wireDiagram() 只對 `[data-seg]` 綁 click，
   零件小卡（renderPartCard）第一行就是「沒有 seg 就把卡片收起來」。
   兩邊都不能放棄，所以做法是：
     · `data-seg` 照掛（＝可以點、有小卡、兩層高亮都活著）
     · 每個零件的**視覺**包在一層帶 `--c` 的內層群組裡 ——
       inline 樣式寫在**子節點**上，JS 寫在父節點上，子的贏，材質色就守住了
   這樣 `.part` 的描邊、發光、引線、說明列全部拿到材質色，不是灰色。
   （規格書 §6-D 當時的結論是「一律不帶 data-seg」，那是在**零件小卡還不存在**的時候寫的；
     小卡上線之後那條會讓這張圖變成「畫得出來但點不動」，所以改走上面這條。）

   ★ data-seg 為什麼是中文
   ------------------------
   小卡上那顆按鈕會印「供應鏈環節的 name，找不到就印 id」。石化鏈在 YAML 裡沒有環節，
   所以直接印 id —— 印 nc_s2 這種東西沒有人看得懂，印中文站名至少那顆鈕是可讀的。
   ⚠ 按下去會是 0 筆（這條鏈沒有環節資料），所以圖上有一行字直接把這件事寫出來，
   不要讓人以為點壞了（做法同 ic_substrate 的「台股掛零」那兩行）。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/industry.js`。
   共用工具一律走 `window.DG`；**JS 裡一個十六進位色碼都沒有**，色值全部走 :root 既有的 --dg-*
   （這一輪刻意沒有新增 token —— 新 token 要住在 index.html 的 :root，而那個檔現在多人共用）。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;   // diagrams.js 沒載到就安靜退出
  const { extRow, note, fold } = D;

  /* ================================================================ v2 版面（2026-09-23）
     Andy：「傳產與內需 & 基礎建設與能源 2D 圖並沒有調整適當大小，請去調整，調整適當範圍，別浪費空白」。
     ----------------------------------------------------------------
     上一批的做法是「在 980 的框裡補小圖填空白」，他看過之後說**還是沒調好** —— 以他的為準，換做法。
     真正的問題不是「框裡有沒有東西」，是**整張圖的尺度**：這一批其餘 12 張已經收到 660／700，
     只有這張與重電那張還是 980，於是在同樣的欄寬下被縮得比別人小、四周留白比別人多。
     所以改成跟那 12 張（`server_psu`／`foundry`／`silicon_wafer`）完全一致的 v2 版面：
       · svg 根掛 `rs` → `externalize()` 把說明搬成 HTML 卡片（`.dgc`），
         欄寬由 index.html 的 `.dgv2` 容器查詢決定（1440 三欄／800 兩欄／390 單欄），
         **圖檔裡不寫死「右邊留多少 px」**。
       · 畫布 980 → **660**（`native` 同步改）；畫布上只留「畫」的部分，
         說明文字、圖例、結論行全部變卡片。
       · 章節改用 `D.fold()`（範圍由 `getBBox()` 量），不再手寫 y0／y1 與 translate。
     ⚠ 上一批為了填空白補進去的兩塊（三格裂解價差小卡、芳香烴車道的 B／T／PX 分支標註）：
       前者留著（收窄成三格 196 寬，它本來就是這張圖的命題），
       後者在 660 的尺度下會變成硬塞 —— 改成章節 ② 裡的編號 ④ ＋ 圖例行，
       **它講的事一個字都沒有消失**，只是換了位置。
     沒有放寬的事：`data-part` 23 個一個不改名、一個不減少；六站 `data-seg` 照舊；
     JS 裡一個十六進位色碼都沒有。*/
  const CW = 660;

  /* 兩排主體都是「幾何整組縮小放進 660 的畫布」。★ 文字一律留在縮放群組**外面**：
     字級縮下去就破了 12px 硬下限（DECISIONS #227），所以縮的永遠只有圖形。*/
  const K1 = 0.65, K1X = 5.6, K1Y = -90.5;      // 第一排（裂解廠本體）：原圖 x[16,975] y[210,444]
  const f1x = (x) => +(x * K1 + K1X).toFixed(1);
  const f1y = (y) => +(y * K1 + K1Y).toFixed(1);
  const K2 = 0.66, K2X = 5.44, K2Y = -349.2;    // 第二排（基本原料與下游）：原圖 x[16,960] y[620,800]
  const f2x = (x) => +(x * K2 + K2X).toFixed(1);
  const f2y = (y) => +(y * K2 + K2Y).toFixed(1);

  const T = (x, y, t, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${t}</text>`;
  /* 章節裡的編號圓點。★ 章節內**不能**用 `extRow` —— `externalize()` 會把卡片抽到左右欄，
     錨點卻留在收合起來的章節裡，於是出現一張指不到任何東西的孤兒卡片。
     所以章節裡的標註一律是畫布上的編號圓點 ＋ 底下一段圖例行。*/
  const ndot = (x, y, n) =>
    `<g pointer-events="none"><circle class="ndot" cx="${x}" cy="${y}" r="9.5"/>`
    + `<text class="nnum" x="${x}" y="${y}">${String(n).padStart(2, '0')}</text></g>`;

  /* 卡片的元件色（`data-dgcolor`），跟畫面上那個零件的材質色同一個 token */
  const CC = {
    mute: 'var(--dg-mute)', steel: 'var(--dg-steel)', cold: 'var(--dg-cold)', el: 'var(--dg-el)',
    alu: 'var(--dg-alu)', cer: 'var(--dg-cer)', cover: 'var(--dg-cover)', fws: 'var(--dg-fws)',
    accent: 'var(--dg-accent-2d)',
  };
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點與引線。
     ★ `seg` 與 `part` 照舊掛上去 —— externalize 會把身分搬到卡片上，
     點卡片＝點那個零件（互動一個都沒少）。*/
  const card = (o) => extRow({
    seg: o.seg, part: o.part, title: o.title, sub: o.sub, no: o.no,
    side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order,
  });

  /* ================================================================ 環節（站）與零件身分
     六站＝§3-E 的六格流程，data-seg 用中文站名（理由見檔頭）。*/
  const S1 = '原料進料', S2 = '裂解與急冷', S3 = '壓縮與淨化',
    S4 = '深冷分離', S5 = '四支基本原料', S6 = '下游衍生物';

  /* 零件外框：data-seg（站）＋ data-part（零件身分）＋ 一層帶材質色的內包裝。
     內包裝是刻意的，不是多餘的群組 —— 見檔頭「顏色怎麼走」。*/
  const P = (seg, part, col, inner) =>
    `<g data-seg="${seg}" data-part="${part}"><g class="pw" style="--c:var(${col})">${inner}</g></g>`;

  const V = (c) => `var(${c})`;
  const R = (x, y, w, h, f, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${f}"/>`;

  /* ---------------- 立式圓筒（塔、儲槽、反應器）
     底弧 → 筒身 → 右側暗面 → 頂蓋，四層疊出圓筒感。
     `man` ＝人孔、`lad` ＝直梯與環狀平台 —— §4：「沒有這三件的圓柱不是塔，是柱子」。*/
  function vessel(cx, yb, w, h, a, b, opt) {
    opt = opt || {};
    const r = w / 2, ry = Math.max(2.2, w * 0.26), yt = yb - h;
    const s = [`<ellipse cx="${cx}" cy="${yb}" rx="${r}" ry="${ry}" fill="${V(b)}"/>`,
      R(cx - r, yt, w, h, V(a), 'part'),
      R(cx + r * 0.2, yt, r * 0.8, h, V(b)),
      `<ellipse cx="${cx}" cy="${yt}" rx="${r}" ry="${ry}" fill="${V(a)}" stroke="${V(b)}" stroke-width=".8"/>`];
    if (opt.man) {                       // 等距人孔（塔的標準特徵）
      const n = Math.max(2, Math.floor(h / 26));
      for (let i = 1; i <= n; i++) s.push(`<circle cx="${(cx - r * 0.42).toFixed(1)}" cy="${(yb - h * i / (n + 1)).toFixed(1)}" r="2.1" fill="${V(b)}"/>`);
    }
    if (opt.lad) {                       // 外掛直梯 ＋ 兩層環狀平台
      const lx = cx - r - 3;
      const rungs = [];
      for (let y = yt + 8; y < yb - 4; y += 7) rungs.push(`M${lx},${y.toFixed(1)} h4`);
      s.push(`<path d="M${lx},${yt + 4} V${yb - 2} M${lx + 4},${yt + 4} V${yb - 2} ${rungs.join(' ')}" stroke="${V(b)}" stroke-width=".7" fill="none" opacity=".9"/>`);
      s.push(`<path d="M${cx - r - 5},${(yt + h * 0.34).toFixed(1)} h${w + 10} M${cx - r - 5},${(yt + h * 0.68).toFixed(1)} h${w + 10}" stroke="${V(b)}" stroke-width="1.2" fill="none" opacity=".75"/>`);
    }
    if (opt.ins) {                       // 包保冷：外面再罩一圈金屬皮（比筒身胖一圈）
      s.unshift(R(cx - r - 3, yt - 3, w + 6, h + 5, V(opt.ins)));
    }
    return s.join('');
  }

  /* ---------------- 臥式圓筒（換熱器、分液罐、壓縮機機殼）
     ★ §4：急冷換熱器「短粗、兩端法蘭」；壓縮機是「一根軸串多個機殼」。*/
  const drum = (x, y, w, h, a, b) =>
    R(x, y, w, h, V(a), 'part', h / 2)
    + `<ellipse cx="${(x + w - h * 0.3).toFixed(1)}" cy="${(y + h / 2).toFixed(1)}" rx="${(h * 0.3).toFixed(1)}" ry="${(h / 2).toFixed(1)}" fill="${V(b)}"/>`;

  /* ---------------- 2.5D 方箱（爐體、冷箱）：正面 ＋ 頂面 ＋ 右側面 */
  const cab = (x, y, w, h, d, a, b, c2) =>
    `<path d="M${x},${y} l${d},${-d * 0.5} h${w} l${-d},${d * 0.5} Z" fill="${V(c2 || a)}"/>`
    + `<path d="M${x + w},${y} l${d},${-d * 0.5} v${h} l${-d},${d * 0.5} Z" fill="${V(b)}"/>`
    + R(x, y, w, h, V(a), 'part');

  /* ---------------- 球槽（sphere）
     ★ §4：「丙烯與丁二烯是球槽：球形 ＋ 數支支柱 ＋ 赤道一圈走道。畫成開頂圓筒＝錯」。*/
  function sphere(cx, cy, r, yb, a, b) {
    const legs = [-0.78, -0.3, 0.3, 0.78].map(k =>
      `M${(cx + r * k).toFixed(1)},${(cy + r * Math.sqrt(Math.max(0, 1 - k * k)) * 0.86).toFixed(1)} L${(cx + r * k * 1.06).toFixed(1)},${yb}`).join(' ');
    return `<circle class="part" cx="${cx}" cy="${cy}" r="${r}" fill="${V(a)}"/>`
      + `<path d="M${cx},${cy - r} A${(r * 0.42).toFixed(1)},${r} 0 0 0 ${cx},${cy + r} A${r},${r} 0 0 0 ${cx},${cy - r}Z" fill="${V(b)}" opacity=".3"/>`
      + `<ellipse cx="${cx}" cy="${cy}" rx="${r}" ry="${(r * 0.26).toFixed(1)}" fill="none" stroke="${V(b)}" stroke-width="1.1" opacity=".9"/>`
      + `<path d="${legs}" stroke="${V(b)}" stroke-width="1.6" fill="none"/>`;
  }

  /* ---------------- 直立蛇行爐管（radiant coil）
     ★ §4 決定性特徵：「直立的蛇行爐管站在爐膛裡，不是一個臥式大圓桶。缺了這個整格就報廢」。
     螢光感照 AGENTS §11 壓下來 —— 只用 --dg-hot 的線色表示高溫，不加發光。*/
  function coil(x0, yTop, yBot, n, gap) {
    const d = [];
    for (let i = 0; i < n; i++) {
      const x = x0 + i * gap;
      d.push(`M${x},${yTop} V${yBot}`);
      if (i < n - 1) {                       // U 形彎頭：上下交替，才是「蛇行」
        const y = i % 2 === 0 ? yBot : yTop, k = i % 2 === 0 ? 4 : -4;
        d.push(`M${x},${y} q${gap / 2},${k} ${gap},0`);
      }
    }
    return `<path d="${d.join(' ')}" stroke="${V('--dg-hot')}" stroke-width="2" fill="none" stroke-linecap="round" opacity=".92"/>`;
  }

  /* ---------------- 比例小人（1.7 m）：單色剪影，不要五官（§2 第 14 列） */
  const person = (x, yb) => `<g pointer-events="none" opacity=".9">
    <circle cx="${x}" cy="${yb - 14}" r="2.6" fill="${V('--dg-mute')}"/>
    <path d="M${x},${yb - 11.4} V${yb - 5} M${x - 3},${yb - 9} H${x + 3} M${x},${yb - 5} l-2.6,5 M${x},${yb - 5} l2.6,5" stroke="${V('--dg-mute')}" stroke-width="1.4" fill="none" stroke-linecap="round"/></g>`;

  // 箭頭（流向）。`cls` 傳 'flow' 就會跑虛線動畫（動畫鈕關得掉）。
  const arrow = (d, col, cls, w) =>
    `<path class="${cls || ''}" d="${d}" stroke="${V(col)}" stroke-width="${w || 2}" fill="none" stroke-linecap="round" marker-end="url(#ncAr)"/>`;

  /* 說明列：站題 ＋ 數行副標。綁同一個 data-part，所以點文字＝點那個零件。*/
  const tblock = (seg, part, col, x, y, w, t, subs) =>
    `<g class="lrow" data-seg="${seg}" data-part="${part}"><g class="pw" style="--c:var(${col})">
      <rect class="bg" x="${x - 8}" y="${y - 15}" width="${w}" height="${21 + subs.length * 18}" rx="6"/>
      <circle class="dot" cx="${x + 4}" cy="${y - 4}" r="4"/>
      <text class="lbl" x="${x + 14}" y="${y}">${t}</text>
      ${subs.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 18 + i * 18}">${s}</text>`).join('')}
    </g></g>`;

  /* 裂解價差的三個情境小卡（§3-D：靜態、不標任何數值）。
     ★ 2026-09-23 v2：寬度與 y 改成參數 —— 660 的畫布放不下原本 140 寬 ×3 靠右排的版面，
       現在三格各 196 寬、從 x=16 排到 x=628（＝畫布左右各留 16），中間不留空白。
     k：0＝產品線在上（賺）、1＝兩條線靠近（薄）、2＝產品線在下（倒掛）。*/
  function spreadCase(x, y0, w, title, col, k, lines) {
    const yT = y0 + 20, yB = y0 + 54;                  // 小卡裡那兩條線的上下界
    const prod = k === 2 ? yB : (k === 1 ? yT + 22 : yT);   // 產品線
    const cost = k === 2 ? yT : (k === 1 ? yT + 30 : yB);   // 成本線（石油腦）
    const a = Math.min(prod, cost), b = Math.max(prod, cost);
    return `<g>`
      + `<rect x="${x}" y="${y0}" width="${w}" height="98" rx="6" fill="none" stroke="${V(col)}" stroke-opacity=".38"/>`
      + `<text class="lbl" x="${x + 10}" y="${y0 + 16}" style="fill:${V(col)}">${title}</text>`
      + `<rect x="${x + 10}" y="${a}" width="${w - 20}" height="${Math.max(3, b - a)}" fill="${V(col)}" opacity=".18"/>`
      + `<path d="M${x + 10},${prod} H${x + w - 10}" stroke="${V('--dg-accent-2d')}" stroke-width="2" fill="none"/>`
      + `<path d="M${x + 10},${cost} H${x + w - 10}" stroke="${V('--dg-mute')}" stroke-width="2" fill="none" stroke-dasharray="6 4"/>`
      + lines.map((t, i) => `<text class="sub" x="${x + 10}" y="${y0 + 70 + i * 16}"${k === 2 ? ` style="fill:${V(col)}"` : ''}>${t}</text>`).join('')
      + `</g>`;
  }

  /* ================================================================ 版面常數 */
  const GA = 410;          // 第一排（裂解廠本體）的地面線
  const GB = 700;          // 第二排：烯烴車道的基線
  const GC = 790;          // 第二排：芳香烴車道的基線

  /* ================================================================ 段 1 原料進料 */
  function seg1() {
    return P(S1, 'nc_refinery', '--dg-mute',
      cab(18, GA - 46, 34, 46, 7, '--dg-mute', '--dg-mute')
      + `<path d="M26,${GA - 46} V${GA - 62} M34,${GA - 46} V${GA - 58} M42,${GA - 46} V${GA - 66}" stroke="${V('--dg-mute')}" stroke-width="2.4" fill="none"/>`)
    + P(S1, 'nc_naphtha_tank', '--dg-steel',
      vessel(112, GA, 64, 42, '--dg-steel', '--dg-steel-2', { lad: 1 })
      // 浮頂：頂面再往下一階的一圈環狀走道，看得出「頂是浮的」
      + `<ellipse cx="112" cy="${GA - 36}" rx="25" ry="6" fill="${V('--dg-steel-2')}"/>`
      + `<ellipse cx="112" cy="${GA - 39}" rx="25" ry="6" fill="none" stroke="${V('--dg-steel')}" stroke-width="1"/>`)
    + P(S1, 'nc_ethane', '--dg-cold',
      `<path d="M20,${GA - 96} H96 V${GA - 50}" stroke="${V('--dg-cold')}" stroke-width="2.4" fill="none" stroke-dasharray="6 5"/>`
      + `<path d="M28,${GA - 100} h10 M52,${GA - 100} h10 M76,${GA - 100} h10" stroke="${V('--dg-cold-2')}" stroke-width="3" fill="none"/>`)
    + arrow(`M146,${GA - 22} H186`, '--dg-accent-2d', 'flow');
  }

  /* ================================================================ 段 2 裂解爐與急冷 */
  function seg2() {
    const fx = 196, fw = 58, fTop = GA - 132;
    return P(S2, 'nc_furnace', '--dg-el',
      cab(fx, fTop, fw, 132, 9, '--dg-el', '--dg-el')                       // 輻射段爐膛
      + cab(fx - 3, fTop - 22, fw + 6, 22, 9, '--dg-el', '--dg-el')          // 對流段
      + R(fx + 22, fTop - 62, 13, 40, V('--dg-el'), 'part')                  // 煙囪
      + coil(fx + 9, fTop + 10, GA - 20, 7, 6.6)
      + `<path d="M${fx + 5},${GA - 8} h${fw - 10}" stroke="${V('--dg-hot-2')}" stroke-width="3" fill="none" opacity=".85"/>`
      + `<path d="M${fx + 10},${GA - 4} l3,-5 l3,5 M${fx + 26},${GA - 4} l3,-5 l3,5 M${fx + 42},${GA - 4} l3,-5 l3,5" stroke="${V('--dg-hot')}" stroke-width="1.4" fill="none"/>`
      + `<circle cx="${fx + 51}" cy="${fTop + 46}" r="3" fill="${V('--dg-hot-2')}"/>`)
    + P(S2, 'nc_tle', '--dg-alu',
      drum(262, GA - 92, 44, 20, '--dg-alu', '--dg-alu-2')
      + R(260, GA - 94, 4, 24, V('--dg-alu-3'))
      + R(304, GA - 94, 4, 24, V('--dg-alu-3'))
      + `<path d="M254,${GA - 82} H262" stroke="${V('--dg-hot-2')}" stroke-width="2.4" fill="none"/>`)
    + P(S2, 'nc_quench', '--dg-steel',
      vessel(336, GA, 30, 118, '--dg-steel', '--dg-steel-2', { man: 1, lad: 1 })
      + vessel(392, GA, 30, 104, '--dg-steel', '--dg-steel-2', { man: 1, lad: 1 })
      // 塔底大管徑循環回流管接回塔中段 —— §4「這是『洗』的視覺證據」
      + `<path d="M324,${GA - 6} H314 V${GA - 74} H322" stroke="${V('--dg-steel-2')}" stroke-width="4" fill="none"/>`
      + `<path d="M380,${GA - 6} H370 V${GA - 66} H378" stroke="${V('--dg-steel-2')}" stroke-width="4" fill="none"/>`
      + `<path d="M308,${GA - 82} H321" stroke="${V('--dg-hot-2')}" stroke-width="2.4" fill="none"/>`
      + `<path d="M351,${GA - 96} H377" stroke="${V('--dg-steel-2')}" stroke-width="2.4" fill="none"/>`)
    + arrow(`M408,${GA - 30} H448`, '--dg-accent-2d', 'flow');
  }

  /* ================================================================ 段 3 壓縮與淨化 */
  function seg3() {
    const bx = 456, by = GA - 44;
    const casings = [0, 30, 60, 90].map(i => drum(bx + 4 + i, by - 26, 26, 24, '--dg-alu', '--dg-alu-2')).join('');
    const inter = [0, 34, 68].map(i => drum(bx + 6 + i, by + 6, 28, 12, '--dg-alu-2', '--dg-alu-3')).join('');
    return P(S3, 'nc_compressor', '--dg-alu',
      R(bx, by, 132, 8, V('--dg-alu-3'), 'part')            // 鋼底座
      + casings
      + `<path d="M${bx + 2},${by - 14} H${bx + 136}" stroke="${V('--dg-alu-3')}" stroke-width="2.6" fill="none"/>`  // 一根軸串起來
      + drum(bx + 136, by - 32, 34, 32, '--dg-alu-2', '--dg-alu-3')   // 一端的大型驅動機
      + inter
      + `<path d="M${bx + 10},${by + 18} V${GA}" stroke="${V('--dg-alu-3')}" stroke-width="1.4" fill="none"/>`
      + `<path d="M${bx + 120},${by + 18} V${GA}" stroke="${V('--dg-alu-3')}" stroke-width="1.4" fill="none"/>`)
    + P(S3, 'nc_caustic', '--dg-steel',
      vessel(614, GA, 18, 104, '--dg-steel', '--dg-steel-2', { man: 1 }))
    + P(S3, 'nc_dryer', '--dg-steel',
      vessel(640, GA, 15, 62, '--dg-steel', '--dg-steel-2')
      + vessel(660, GA, 15, 62, '--dg-steel', '--dg-steel-2')
      + `<path d="M640,${GA - 68} V${GA - 76} H660 V${GA - 68}" stroke="${V('--dg-steel-2')}" stroke-width="1.6" fill="none"/>`)
    + arrow(`M672,${GA - 26} H700`, '--dg-accent-2d', 'flow');
  }

  /* ================================================================ 段 4 深冷分離塔組
     ★ §3-B 的順序寫死在這個陣列裡，跑迴圈畫（規格書 §7 明講「別手刻，手刻就會刻錯順序」）。
     高度也寫在陣列裡：脫甲烷最高最粗（包保冷）、脫丁烷最矮 —— §4「一排等高的圓柱＝錯」。*/
  const TOWERS = [
    { cx: 758, w: 26, h: 117, ins: 1, t: '脫甲烷塔' },
    { cx: 800, w: 18, h: 88, t: '脫乙烷塔' },
    { cx: 840, w: 14, h: 114, t: '乙烯精餾塔' },
    { cx: 878, w: 18, h: 78, t: '脫丙烷塔' },
    { cx: 916, w: 14, h: 108, t: '丙烯精餾塔' },
    { cx: 952, w: 18, h: 56, t: '脫丁烷塔' },
  ];
  function seg4() {
    const towers = TOWERS.map(o => {
      const r = o.w / 2;
      return vessel(o.cx, GA, o.w, o.h, '--dg-steel', '--dg-steel-2', { man: 1, lad: 1, ins: o.ins ? '--dg-cold-2' : null })
        // 頂部回流冷凝器（臥式）＋ 底部再沸器 ＋ 旁邊一台小泵 —— §4 的三件套
        + drum(o.cx + r + 2, GA - o.h - 2, 12, 6, '--dg-alu', '--dg-alu-2')
        + drum(o.cx + r + 2, GA - 13, 10, 5, '--dg-alu', '--dg-alu-2')
        + R(o.cx + r + 3, GA - 6, 6, 5, V('--dg-alu-3'));
    }).join('');
    // 塔底往下一支塔（碳數由小到大）：每一段都是「底出重的」
    const link = TOWERS.slice(0, -1).map((o, i) =>
      `M${o.cx + o.w / 2 + 2},${GA - 22} H${TOWERS[i + 1].cx - TOWERS[i + 1].w / 2 - 2}`).join(' ');
    return P(S4, 'nc_coldbox', '--dg-cold',
      cab(704, GA - 96, 42, 96, 10, '--dg-cold-2', '--dg-cold-2', '--dg-cold')
      + R(706, GA - 92, 38, 88, V('--dg-cold'), '', 3)
      // 結霜：表面一層霜紋
      + `<path d="M710,${GA - 84} h30 M710,${GA - 70} h22 M714,${GA - 56} h26 M710,${GA - 42} h18 M716,${GA - 28} h24" stroke="${V('--dg-cer')}" stroke-width="1.6" fill="none" opacity=".55"/>`
      + `<path d="M704,${GA - 96} h42 M704,${GA} h42" stroke="${V('--dg-cold-2')}" stroke-width="2" fill="none"/>`)
    + P(S4, 'nc_towers', '--dg-steel', towers
      + `<path d="${link}" stroke="${V('--dg-steel-2')}" stroke-width="2.2" fill="none"/>`)
    + P(S4, 'nc_hydro', '--dg-alu',
      vessel(820, GA, 14, 30, '--dg-alu', '--dg-alu-2')
      + vessel(897, GA, 14, 30, '--dg-alu', '--dg-alu-2'));
  }

  /* ================================================================ 第二排：四支基本原料 → 下游衍生物
     §3-C 的五條線在這裡逐條畫出起點與終點。**起點一律是產出它的那一座槽／那一組塔。** */
  function laneProducts() {
    return P(S5, 'nc_c2_tank', '--dg-cold',
      vessel(58, GB, 44, 74, '--dg-cold', '--dg-cold-2', { ins: '--dg-cer', lad: 1 })
      + R(32, GB, 52, 5, V('--dg-steel-2')))
    + P(S5, 'nc_sphere', '--dg-cer',
      sphere(140, GB - 26, 22, GB, '--dg-cer', '--dg-cer-2')
      + sphere(200, GB - 20, 17, GB, '--dg-cer', '--dg-cer-2'))
    + P(S5, 'nc_bd_extract', '--dg-steel',
      vessel(248, GB, 16, 66, '--dg-steel', '--dg-steel-2', { man: 1 })
      + vessel(274, GB, 16, 58, '--dg-steel', '--dg-steel-2', { man: 1 })
      + drum(290, GB - 18, 22, 12, '--dg-steel', '--dg-steel-2'))
    + P(S5, 'nc_btx', '--dg-alu',
      vessel(58, GC, 26, 34, '--dg-alu', '--dg-alu-2')
      + vessel(112, GC, 16, 62, '--dg-steel', '--dg-steel-2', { man: 1 })
      + vessel(140, GC, 16, 54, '--dg-steel', '--dg-steel-2', { man: 1 })
      + `<path d="M74,${GC - 30} H104" stroke="${V('--dg-alu-2')}" stroke-width="2" fill="none"/>`);
  }

  function laneDown() {
    const silo = (cx, yb, w, h) => vessel(cx, yb - 12, w, h, '--dg-cover', '--dg-cover-2')
      + `<path d="M${cx - w / 2},${yb - 12} L${cx - w * 0.16},${yb - 1} H${cx + w * 0.16} L${cx + w / 2},${yb - 12}Z" fill="${V('--dg-cover-2')}"/>`
      + `<circle cx="${cx - w * 0.22}" cy="${yb + 4}" r="1.8" fill="${V('--dg-cover')}"/>`
      + `<circle cx="${cx + w * 0.1}" cy="${yb + 5}" r="1.8" fill="${V('--dg-cover')}"/>`
      + `<circle cx="${cx - w * 0.02}" cy="${yb + 2}" r="1.8" fill="${V('--dg-cover')}"/>`;
    return P(S6, 'nc_pe_pp', '--dg-cover',
      silo(378, GB, 34, 52) + silo(420, GB, 34, 52) + silo(462, GB, 34, 52))
    + P(S6, 'nc_eg', '--dg-steel',
      vessel(524, GB, 15, 46, '--dg-steel', '--dg-steel-2', { man: 1 })
      + vessel(548, GB, 15, 38, '--dg-steel', '--dg-steel-2', { man: 1 })
      + drum(560, GB - 14, 20, 10, '--dg-steel', '--dg-steel-2'))
    + P(S6, 'nc_pvc', '--dg-alu',
      // 乙烯＋氯 → EDC → VCM → PVC：中間一定看得到 VCM（§3-A 硬規則 10）
      R(606, GB - 46, 26, 18, V('--dg-alu-2'), 'part', 3)
      + R(606, GB - 22, 26, 18, V('--dg-alu-2'), '', 3)
      + `<path d="M619,${GB - 28} V${GB - 22}" stroke="${V('--dg-alu-3')}" stroke-width="1.6" fill="none"/>`
      + vessel(672, GB, 40, 50, '--dg-alu', '--dg-alu-2')
      + R(668, GB - 66, 8, 16, V('--dg-alu-3'))                       // 攪拌軸
      + drum(660, GB - 78, 24, 13, '--dg-alu-2', '--dg-alu-3')        // 頂部馬達
      + `<path d="M664,${GB - 22} h16 M664,${GB - 34} h16" stroke="${V('--dg-alu-3')}" stroke-width="1.4" fill="none"/>`
      + R(650, GB - 52, 44, 5, V('--dg-alu-3')))                      // 保溫夾套
    + P(S6, 'nc_sm', '--dg-alu',
      vessel(800, 738, 22, 46, '--dg-alu', '--dg-alu-2')
      + vessel(832, 738, 22, 46, '--dg-alu', '--dg-alu-2')
      + `<path d="M800,${738 - 50} H832" stroke="${V('--dg-alu-2')}" stroke-width="2" fill="none"/>`)
    + P(S6, 'nc_pta', '--dg-cer',
      vessel(906, GC, 36, 56, '--dg-alu', '--dg-alu-2')
      + drum(926, GC - 24, 30, 14, '--dg-cer', '--dg-cer-2')
      + `<path d="M924,${GC - 4} l6,-6 l6,6Z" fill="${V('--dg-cer')}"/>`
      + `<circle cx="942" cy="${GC - 3}" r="1.6" fill="${V('--dg-cer')}"/>`
      + `<circle cx="950" cy="${GC - 5}" r="1.4" fill="${V('--dg-cer')}"/>`);
  }

  /* ================================================================ 第二排的四條產品線
     §3-C 的五條線：**起點一律是產出它的那一座槽／那一組塔**。
     2026-09-23 v2：從主體抽成一支函式，因為它跟第二排的設備一起被縮放進章節 ②。*/
  function laneLines() {
    return `<g pointer-events="none">
      <path d="M84,${GB - 40} H352" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <path d="M482,${GB - 40} H500" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <path d="M578,${GB - 40} H598" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <path d="M634,${GB - 34} H644" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <!-- 乙烯 → 乙苯 → SM：第一條匯進 SM 的線 -->
      <path d="M700,${GB - 40} H772 V712 H786" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <!-- 苯（來自芳香烴抽取）→ SM：第二條匯進 SM 的線。★ §3-A 硬規則 9：只畫一條＝錯 -->
      <path d="M158,${GC - 40} H752 V726 H786" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <!-- PX（同樣來自芳香烴抽取）→ PTA。★ §3-A 硬規則 8：不准接在乙烯下面 -->
      <path d="M158,${GC - 14} H884" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <!-- 丙烯 → PP、丁二烯 → 抽取 → 合成橡膠與 ABS -->
      <path d="M164,${GB - 6} H300 V${GB - 34} H356" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <path d="M219,${GB - 6} H234" stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none" marker-end="url(#ncAr)"/>
      <!-- 芳香烴那條車道：抽取出來的三支各往哪裡去（上一批補的那一段敘事，v2 保留，標註改走編號 ④） -->
      <path d="M168,${GC - 26} H780" stroke="var(--dg-alu-2)" stroke-width="1.6" fill="none" opacity=".55" marker-end="url(#ncAr)"/>
      <path d="M228,${GC - 26} v-10 M400,${GC - 26} v-10 M572,${GC - 26} v-10" stroke="var(--dg-alu-2)" stroke-width="1.4" fill="none" opacity=".7"/>
    </g>`;
  }

  /* ================================================================ 章節 ②：第二排（基本原料與下游）
     幾何整組縮 0.66 放進 660 的畫布；標註一律在縮放群組外面，用編號圓點 ＋ 底下的圖例行。*/
  function areaLanes() {
    return `<g>
      ${T(16, 18, '⑤⑥ 四支基本原料與它們的下游：四支的景氣各自獨立，一支好不代表整廠的帳好看', 'hd')}
      ${T(16, 38, '★ 丁二烯從混合碳四抽出來；芳香烴從裂解汽油加氫後抽出來；PTA 的原料是對二甲苯（PX）不是乙烯。', 'sub')}
      <g><g transform="translate(${K2X},${K2Y}) scale(${K2})">
        <path d="M16,${GB} H700" stroke="var(--dg-mute)" stroke-width="1.6" fill="none" opacity=".6"/>
        <path d="M16,${GC} H960" stroke="var(--dg-mute)" stroke-width="1.6" fill="none" opacity=".6"/>
        ${laneLines()}${laneProducts()}${laneDown()}
      </g></g>
      ${ndot(f2x(58), f2y(660), 1)}
      ${ndot(f2x(170), f2y(676), 2)}
      ${ndot(f2x(272), f2y(668), 3)}
      ${ndot(f2x(105), f2y(762), 4)}
      ${ndot(f2x(420), f2y(672), 5)}
      ${ndot(f2x(542), f2y(676), 6)}
      ${ndot(f2x(650), f2y(660), 7)}
      ${ndot(f2x(816), f2y(700), 8)}
      ${ndot(f2x(930), f2y(762), 9)}
      <rect class="frame" x="16" y="196" width="628" height="156" rx="8"/>
      ${T(30, 220, '這一排每一格是什麼（對到圖上的編號）', 'hd')}
      ${T(30, 242, '① 乙烯低溫儲槽（包厚保冷）　② 丙烯與丁二烯球槽　③ 丁二烯抽取單元（萃取蒸餾）', 'sub')}
      ${T(30, 260, '④ 裂解汽油加氫 ＋ 芳香烴（BTX）抽取：苯（B）→ 苯乙烯 SM；甲苯（T）多半再轉成苯與二甲苯；', 'sub')}
      ${T(30, 278, '　 二甲苯／對二甲苯（PX）→ 純對苯二甲酸 PTA。', 'sub')}
      ${T(30, 296, '⑤ PE／PP 造粒與粒料倉　⑥ EG／可塑劑　⑦ EDC → VCM → PVC 聚合釜', 'sub')}
      ${T(30, 314, '⑧ 苯乙烯 SM：★ 兩條線匯進來（乙烯＋苯）　⑨ PTA 氧化反應器（成品是白色粉體，不是粒）', 'sub')}
      ${T(30, 332, '烯烴線＝PE·PP·PVC·EG（日用塑膠與化工品）；芳香烴線＝SM·PTA（ABS 與聚酯的原料）。', 'sub')}
    </g>`;
  }

  /* ================================================================ 章節 ③：製造流程六格 */
  function areaFlow() {
    return `<g>
      ${T(16, 18, '製造流程（六格）　★ 急冷一定在壓縮之前、壓縮一定在分離之前；分離塔組依碳數由小到大脫出', 'cap')}
      ${D.processBar(16, 28, [
    { seg: S1, t: '① 原料進料', s: '石油腦儲槽（可摻乙烷）' },
    { seg: S2, t: '② 裂解與急冷', s: '爐管裂解 → 急冷' },
    { seg: S3, t: '③ 壓縮與淨化', s: '壓縮 → 鹼洗 → 乾燥' },
    { seg: S4, t: '④ 深冷分離', s: '冷箱 → 六支塔' },
    { seg: S5, t: '⑤ 四支基本原料', s: '乙烯·丙烯·丁二烯·芳香烴' },
    { seg: S6, t: '⑥ 下游衍生物', s: 'PE·PP·PVC·EG·SM·PTA' },
  ], 196, { cols: 3 })}
    </g>`;
  }

  /* ================================================================ 整張圖 */
  function naphthaCracker() {
    return `<svg class="dg dgm rs dgnc" viewBox="0 0 ${CW} 440" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ 這一段的註解裡一個角括號都不准出現 —— SVG 裡的 style 是被當標記解析的，
           寫一個長得像標籤的東西進去會讓整張樣式表變成 0 條規則（DECISIONS #231）。

           為什麼這張圖要多這三行（量出來的，不是手癢）
           --------------------------------------------
           進到這一頁時，industry.js 會把「這個族群對應到哪些環節」當成選起來的那一組。
           石化族群在供應鏈資料裡唯一對得到的是 1303 南亞，而南亞的節點掛在
           「銅箔／玻纖布／樹脂」那一格 —— 也就是說，選起來的那一格**不在這張圖上**，
           於是全部零件被判成 dim、整張圖用 opacity .3 畫出來。
           那不是「有東西被選起來」，那是「一張看不清楚的圖」。

           修法：壓暗只在**真的有主角的時候**才作用。
           haspart 是 highlightSegments 在「這張圖上真的有一個被點的零件」時掛上去的 class。
           前面那個 svg 型別選擇器是必要的：不加的話特異性跟 diagrams.js 的那一條一樣，
           會被後載入的蓋掉（同 ic_substrate 的 dgabf 那一段）。*/
        svg.dgnc:not(.haspart) [data-seg].dim{opacity:1}
        svg.dgnc.haspart [data-seg].dim{opacity:.34}
        /* 螢光感壓下來（AGENTS：要的是精密儀器不是電競 RGB）。
           一站有 3 到 7 個零件，選一站就是一整排同時發光 —— 那個狀態不傳達資訊，
           所以只有「你點的那一個」會發光，同站其餘只是描邊粗一階。
           ★ 發光掛在「零件的內層包裝」（.pw）上，不是掛在每一個 .part 上：
           一站的幾何常常是十幾個形狀（六支塔 ＋ 十二個冷凝器與再沸器），
           一個一個加 drop-shadow 就是十幾圈光暈疊在一起 —— 那正是「螢光感太重」。
           掛在 .pw 上只有一圈，而且 .pw 帶的是材質色（外層的 --c 是 JS 寫上去的灰）。
           ⚠ 用 .pw 而不是子選擇器，是因為子選擇器的那個符號是角括號，
             而這個 style 在 SVG 裡是被當標記解析的（DECISIONS #231）。*/
        svg.dgnc [data-seg].sel .part{stroke-width:1.6;filter:none}
        svg.dgnc [data-seg]:hover .part{stroke-width:1.8;filter:none}
        svg.dgnc [data-seg].sel-part .part{stroke-width:2.4;filter:none}
        svg.dgnc [data-seg].sel-part .pw{filter:drop-shadow(0 0 5px var(--c))}
        /* 章節裡的編號圓點（不是卡片錨點，所以 diagrams.js 的 .anc 規則吃不到，樣式在這裡自己給） */
        svg.dgnc .ndot{fill:var(--dg-accent-2d);opacity:.92}
        svg.dgnc .nnum{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);font-weight:700;
          fill:var(--dg-no-ink);dominant-baseline:central;text-anchor:middle}
      </style>
      <defs>
        <marker id="ncAr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9Z" fill="var(--dg-accent-2d)"/>
        </marker>
        <marker id="ncArM" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9Z" fill="var(--dg-mute)"/>
        </marker>
      </defs>
      <!-- 標題與導讀：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">輕油裂解廠：一進多出與裂解價差</text>
      <text class="cap ext" x="0" y="0">石油腦 → 裂解爐 → 急冷 → 壓縮 → 分離塔組 → 乙烯／丙烯／丁二烯／芳香烴 → 下游。賺的是產品價格減掉進料成本的那一段，不是產品價格本身。一種原料進去、四支基本原料一次全部出來 ——「一進多出」是這座廠的本質，也是「石化景氣」其實是四條線各自景氣的原因。左邊界外是煉油廠：它跟裂解廠是兩個廠。四支基本原料與下游、製造流程六格收在下面兩段。</text>

      <!-- ================= §1-a 裂解廠本體（永遠看得到）=================
           幾何整組縮 0.65 放進 660 的畫布；說明全部是 HTML 卡片，畫布上只有編號圓點與引線。-->
      ${T(16, 18, '① 裂解廠本體：石油腦進去，一次全部斷成小分子', 'hd')}
      ${T(16, 36, '左邊界外是煉油廠 —— 它跟裂解廠是兩個廠；灰虛線＝氫氣／甲烷回爐當燃料（副產，不是第五支產品）。', 'cap')}
      <!-- ⚠ 外面一定要再包一層 g：wireFolds() 的 solidBottom 量的是 svg 直屬子節點的 getBBox()，
           而 getBBox() 不含元素自己的 transform —— 縮放群組直接當 svg 的子節點，量到的會是縮放前的高度，
           於是第一條章節列被推下去、中間空出一大塊（silicon_wafer 那張實測過）。-->
      <g><g transform="translate(${K1X},${K1Y}) scale(${K1})">
        <!-- 氫氣與甲烷：從冷箱／脫甲烷塔頂分出去，回頭當燃料（§3-A 硬規則 12） -->
        <path d="M740,240 H262 V${GA - 158}" stroke="var(--dg-mute)" stroke-width="2.2" fill="none" stroke-dasharray="9 7" marker-end="url(#ncArM)"/>
        ${seg1()}${seg2()}${seg3()}${seg4()}
        <g pointer-events="none">
          <path d="M16,${GA} H975" stroke="var(--dg-mute)" stroke-width="1.6" fill="none" opacity=".7"/>
          ${person(690, GA)}
        </g>
        <!-- 管廊：石化廠最好認的特徵，架高、貫穿全廠（§4 全廠） -->
        ${P('全廠', 'nc_piperack', '--dg-fws', `<g>
          <rect class="part" x="16" y="${GA + 8}" width="684" height="16" rx="3" fill="var(--dg-fws-2)"/>
          <path d="M16,${GA + 11} H700 M16,${GA + 16} H700 M16,${GA + 21} H700" stroke="var(--dg-fws)" stroke-width="2" fill="none"/>
          <path d="M60,${GA + 24} v10 M180,${GA + 24} v10 M300,${GA + 24} v10 M420,${GA + 24} v10 M540,${GA + 24} v10 M660,${GA + 24} v10" stroke="var(--dg-fws-2)" stroke-width="2.4" fill="none"/>
        </g>`)}
      </g></g>
      ${T(462, 192, '↑ 1.7 m 比例小人', 'cap')}

      <!-- ================= §1-b 裂解價差（永遠看得到；這張圖的命題）================= -->
      ${T(16, 222, '② 裂解價差：賺的是這一段的厚度（圖上不寫任何數值）', 'hd')}
      ${P('裂解價差', 'nc_spread', '--dg-accent-2d', '<rect class="frame part" x="16" y="234" width="628" height="114" rx="8"/>')}
      <g pointer-events="none">
        ${spreadCase(16, 242, 196, '價差還在', '--dg-accent-2d', 0, ['產品線在上、成本線在下，', '中間這一段就是賺的厚度。'])}
        ${spreadCase(224, 242, 196, '價差變薄', '--dg-warn', 1, ['石油腦漲、乙烯沒跟上 →', '兩條線靠近，厚度變薄。'])}
        ${spreadCase(432, 242, 196, '價差倒掛', '--dg-err', 2, ['產品線掉到成本線下 →', '開越多賠越多，只能減產。'])}
      </g>

      <!-- ================= 說明卡片（HTML，左右兩欄；引線由 externalize 畫，錨點在畫布上）=================
           左欄錨點 x 小於 330、右欄大於 330 —— 引線只從自己那一側進來，不橫越整張圖。-->
      ${card({ seg: S1, part: 'nc_refinery', no: 1, side: 'l', color: CC.mute, ax: f1x(35), ay: f1y(388),
    title: '煉油廠（界外，不是這座廠的一部分）', sub: ['石油腦是煉油廠的產品、裂解廠的原料 —— 兩者是不同的廠。'] })}
      ${card({ seg: S1, part: 'nc_naphtha_tank', no: 2, side: 'l', color: CC.steel, ax: f1x(112), ay: f1y(390),
    title: '① 原料進料：石油腦浮頂儲槽', sub: ['矮而寬、頂蓋浮在液面上（頂面低一截，看得出一圈環狀走道）。', '成本就從這一槽開始算 —— 裂解價差下面那條線指的就是它。'] })}
      ${card({ seg: S1, part: 'nc_ethane', no: 3, side: 'l', color: CC.cold, ax: f1x(58), ay: f1y(314),
    title: '乙烷進料分支（另一種吃法）', sub: ['改吃乙烷，乙烯收率高，但丙烯、丁二烯、芳香烴會變少。', '方向有來源、比例沒有，所以圖上只寫方向、不寫百分比。'] })}
      ${card({ seg: S2, part: 'nc_furnace', no: 4, side: 'l', color: CC.el, ax: f1x(225), ay: f1y(330),
    title: '② 裂解爐：直立蛇行爐管站在爐膛裡', sub: ['石油腦在爐管裡以約 750–900 °C 裂成小分子，停留不到一秒。', '爐子不是「挑出乙烯」，是把大分子打斷 —— 斷出來的一次全都有。'] })}
      ${card({ seg: S2, part: 'nc_tle', no: 5, side: 'l', color: CC.alu, ax: f1x(284), ay: f1y(328),
    title: '急冷換熱器（TLE）', sub: ['短粗、兩端法蘭。一出爐就要急冷，不然剛裂好的會反應掉。'] })}
      ${card({ seg: S2, part: 'nc_quench', no: 6, side: 'l', color: CC.steel, ax: f1x(336), ay: f1y(330),
    title: '急冷油塔與急冷水塔（兩支）', sub: ['塔底那條明顯大管徑的循環回流管接回塔中段，就是「洗」的證據。', '★ 急冷一定在壓縮之前。'] })}
      ${card({ seg: '全廠', part: 'nc_piperack', no: 7, side: 'l', color: CC.fws, ax: f1x(300), ay: f1y(428),
    title: '管廊（pipe rack）', sub: ['一排架高的平行管束貫穿全廠 —— 石化廠一眼認得出的特徵。'] })}
      ${card({ seg: S3, part: 'nc_compressor', no: 8, side: 'r', color: CC.alu, ax: f1x(522), ay: f1y(372),
    title: '③ 壓縮與淨化：裂解氣壓縮機組', sub: ['★ 一根軸串起多個機殼、一端接一台大型驅動機，不是一顆小方塊。', '每段之間各有一組段間冷卻器與分液罐。'] })}
      ${card({ seg: S3, part: 'nc_caustic', no: 9, side: 'r', color: CC.steel, ax: f1x(614), ay: f1y(340),
    title: '鹼洗塔（脫酸性氣體）', sub: ['明顯比分離塔細的一支高塔，夾在壓縮機的段與段之間。'] })}
      ${card({ seg: S3, part: 'nc_dryer', no: 10, side: 'r', color: CC.steel, ax: f1x(650), ay: f1y(370),
    title: '乾燥器（一開一備的兩支吸附塔）', sub: ['水沒除乾淨，後面的深冷會結冰堵塔 —— 這一格是深冷分離的門票。'] })}
      ${card({ seg: S4, part: 'nc_coldbox', no: 11, side: 'r', color: CC.cold, ax: f1x(725), ay: f1y(350),
    title: '④ 深冷分離：冷箱（方箱，不是塔）', sub: ['★ 包厚保冷、表面結霜的方箱。先把氫氣分出來，剩下的才進脫甲烷塔。', '氫氣與甲烷回頭當燃料（圖上那條灰虛線），不是並排的第五支產品。'] })}
      ${card({ seg: S4, part: 'nc_towers', no: 12, side: 'r', color: CC.steel, ax: f1x(840), ay: f1y(320),
    title: '分離塔組：六支塔，高度明顯不一樣', sub: ['脫甲烷（最高最粗、包保冷）→ 脫乙烷 → 乙烯精餾 → 脫丙烷 → 丙烯精餾 → 脫丁烷。', '塔頂出乙烯與丙烯；脫丁烷塔頂＝混合碳四（丁二烯的來源）、塔底＝裂解汽油（芳香烴的來源）。'] })}
      ${card({ seg: S4, part: 'nc_hydro', no: 13, side: 'r', color: CC.alu, ax: f1x(820), ay: f1y(390),
    title: '碳二／碳三加氫反應器', sub: ['成對出現，除掉乙炔與丙炔，乙烯與丙烯才到得了聚合級。', '位置固定在「脫某某塔之後、精餾塔之前」。'] })}
      ${card({ seg: '裂解價差', part: 'nc_spread', no: 14, side: 'r', color: CC.accent, ax: 635, ay: 290,   /* ★ 2026-09-26 覆蓋普查：640 時編號「14」右緣伸出價差框 4px → 往內 5 */
    title: '裂解價差（crack spread）', sub: ['上面那條線＝產品（乙烯／丙烯）賣得掉的價，下面那條＝石油腦的成本。', '兩條線的絕對高度沒有意義，有意義的只有中間那一段的厚度。', '石油腦漲、乙烯沒跟上 → 變薄；薄到倒掛 → 開越多賠越多。', '示意，不代表任何時點的實際價差；這條帶只跨裂解廠自己那一段。'] })}

      <!-- 結論與警語卡片（沒有錨點，排在編號卡之後） -->
      ${note({ side: 'l', order: 90, color: CC.accent, title: '為什麼是「一進多出」', lines: [
    '① 裂解爐不是「挑出乙烯」，是把大分子打斷，斷出來的東西一次全部都有。',
    '② 所以一座廠同時在賣四種東西，各自有各自的行情 —— 乙烯好、丁二烯爛，整廠的帳不見得好看。',
    '③ 進料換了（石油腦 → 乙烷），乙烯收率高，但丙烯、丁二烯、芳香烴會變少。',
    '④ 方向有來源、比例沒有 —— 所以這裡只寫方向，不寫任何百分比。'] })}
      ${note({ side: 'r', order: 91, color: CC.cover, title: '四寶站在不同段，看的價差不是同一個', lines: [
    '6505 台塑化：最上游（進料與裂解），烯烴事業生產乙烯、丙烯、丁二烯。',
    '1301 台塑：烯烴衍生物 —— PVC 與 PP 為主，另有 PE、EVA。',
    '1326 台化：芳香烴與聚酯原料線 —— PX、苯、SM、PTA、ABS。',
    '1303 南亞：化工品（EG、可塑劑）與塑膠加工，但電子材料（玻纖布、銅箔、CCL）與聚酯同為其主要事業 —— 它早就不只是石化股。'] })}
      ${note({ side: 'l', order: 98, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: [
    '這條產業鏈（傳產與內需）在供應鏈資料裡還沒有建環節，所以這一頁沒有環節色標；零件小卡上那顆「環節 →」按下去會是 0 筆 —— 那不是壞掉。',
    '要篩成分股請用下面的族群卡片與成分股表。點零件只會亮起來，並在小卡上回答「這個零件是誰做的」，不會動到下方清單。'] })}
      ${note({ side: 'r', order: 99, title: '原創等角示意圖，非實物比例', lines: [
    '分離塔組以「順序分離流程」為例，不同專利商的流程不同；裂解價差為示意，不代表任何時點的實際價差。',
    '不描繪任何真實廠區；火炬、冷卻水塔等公用與安全設施未畫（不在製程主路徑上）。',
    '資料來源與信心度見 docs/diagram_specs/naphtha_cracker.md §6；本圖不放任何價差數字、產能噸數、市占率、營收占比或 EPS（會過期）。',
    '族群成分：1301 台塑／1303 南亞／1326 台化／6505 台塑化／1314 中石化／1312 國喬／1304 台聚。'] })}

      <!-- ================= ② 第二排：四支基本原料 → 下游衍生物（預設收合）================= -->
      ${fold('nc2', '③ 四支基本原料與它們的下游：烯烴線與芳香烴線',
    '乙烯／丙烯／丁二烯／芳香烴各往哪裡去、PVC 中間的 VCM、SM 兩條線匯進來、PTA 走 PX 不走乙烯', areaLanes())}

      <!-- ================= ③ 製造流程六格（預設收合）================= -->
      ${fold('nc4', '④ 製造流程（六格）：順序不准對調',
    '原料進料 → 裂解與急冷 → 壓縮與淨化 → 深冷分離 → 四支基本原料 → 下游衍生物', areaFlow())}
    </svg>`;
  }


  /* ================================================================ 註冊
     `parts` ＝點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。

     ★ 這張圖的 R4／R5 處境跟別張不一樣，要先講清楚：
       `site/data/supply_chain.json` 目前只有 semiconductor／ai_server／electronics 三條鏈、
       114 家公司，**石化鏈一家都沒有**（實測：1301／1303／1326／6505 四檔在裡面一個都查不到）。
       所以 `cos` 填了也撈不到公司卡 —— 小卡會走 `none` 那一列。
       `cos` 還是照填，理由是**將來石化鏈補進 supply_chain.yaml 時這些卡片會自動活過來**；
       在那之前由 `none` 誠實回答「做這一段的是誰、為什麼這裡沒有公司卡」。
     ★ 公司與角色描述**一個字都不是繪圖端編的**，全部來自規格書 §5-E／§6-A 已經查證並附來源的那張表
       （台塑化官網六輕計畫、台塑官網、台化營業項目、南亞官網公司簡介）。
       規格書沒有支撐的敘述一律不寫 —— 例如「台塑化是台灣唯一的輕油裂解廠」（§5-E 明文禁止）、
       「台塑、台化沒有裂解爐」（§6-B6：查不到可引用的否定來源）。
     ★ `items` 填的是**基本原料與產品的通用名稱**，不是具名的公司對公司料號 ——
       石化鏈在 supply_chain 的 edges 裡一條邊都沒有，所以不可能對到 confidence 標籤。*/
  const NOSC = '（石化鏈在供應鏈資料裡還沒有建環節，所以這張卡撈不到公司卡片；成分股名單在下方表格。）';
  const FPCC = '6505 台塑化：烯烴事業生產乙烯、丙烯及丁二烯等石化基本原料，供應集團下游。';

  window.DG.register('petrochemical', {
    level: 'group', chain: 'traditional',
    name: '輕油裂解廠：一進多出與裂解價差',
    draw: naphthaCracker, native: CW, scene: null,   /* ★ 2026-09-23：980 → 660（v2 版面，說明外掛成 HTML 卡片）。scene 仍是 null —— 3D 是 Andy 親口否決的。*/
    q: '一座輕油裂解廠裡有哪些設備、石油腦進去之後為什麼是四支產品一次全部出來？台塑四寶各站在哪一段、看的是哪一種價差？',
    parts: {
      nc_refinery: {
        name: '煉油廠（石油腦的來源，不是這座廠的一部分）',
        desc: '石油腦（輕油）是煉油廠的產品、裂解廠的原料 —— 兩者是不同的廠。常壓／減壓蒸餾塔、催化裂解的提升管都在煉油廠那一邊，不在裂解廠裡。圖上把它畫在左邊界外、只畫灰色剪影，就是為了守住這條界線。',
        items: ['石油腦（輕油）'],
        cos: [],
        none: '這一格是「原料從哪裡來」的方向標記，不是某一家公司的設備。台灣的煉油與裂解在同一個集團內時常整合在一起，但「哪一座煉油廠供給哪一座裂解廠」本次查不到可引用的通用結論 —— 查不到就寫查不到，不編一個對應。',
      },
      nc_naphtha_tank: {
        name: '石油腦浮頂儲槽',
        desc: '矮而寬的立式圓筒，頂蓋是浮在液面上的（頂面比槽壁低一截，看得出一圈環狀走道）—— 浮頂是為了減少揮發損失。成本就從這一槽開始算：裂解價差下面那條線指的就是它。',
        items: ['石油腦（輕油）'],
        cos: ['6505'],
        none: `做這一段（進料與裂解）的台股是 ${FPCC}${NOSC}`,
      },
      nc_ethane: {
        name: '乙烷進料分支（另一種吃法）',
        desc: '裂解爐也可以改吃乙烷。乙烷裂解的乙烯收率遠高於石油腦，但丙烯、丁二烯、芳香烴會跟著變少 —— 也就是「換進料＝換掉四支產品的比例」。圖上畫成一條帶保冷的支線，不是主線。',
        items: ['乙烷（進料）'],
        cos: ['6505'],
        none: `${FPCC}進料切換的方向有來源、比例數字沒有，所以圖上只寫方向、不寫任何百分比。${NOSC}`,
      },
      nc_furnace: {
        name: '裂解爐：輻射段爐管、對流段與煙囪',
        desc: '★ 決定性特徵是「直立的蛇行爐管站在爐膛裡」，不是一個臥式大圓桶。石油腦在爐管裡以約 750–900 °C 斷成小分子，停留時間不到一秒；爐體上方接一段對流段回收熱量，再接煙囪。爐子不是「挑出乙烯」，是把大分子打斷 —— 斷出來的東西一次全部都有。',
        items: ['石油腦（進料）', '裂解氣（出料）'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_tle: {
        name: '急冷換熱器（TLE）',
        desc: '緊接在爐出口的一組短粗換熱器，兩端有法蘭。反應時間以秒計，一出爐就要急冷，不然剛裂好的分子會繼續反應掉 —— 所以爐出口不是直接接到塔，中間一定有這一組。',
        items: ['裂解氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_quench: {
        name: '急冷油塔與急冷水塔（兩支，不是一支）',
        desc: '裂解氣先在油洗塔裡與急冷油逆流接觸、進一步降溫並回收熱量，再用水冷卻。塔底那條明顯大管徑的循環回流管接回塔中段，就是「洗」的視覺證據。★ 急冷一定在壓縮之前。',
        items: ['裂解氣', '急冷油', '急冷水'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_compressor: {
        name: '裂解氣壓縮機組（多段）',
        desc: '★ 一根軸串起多個機殼，一端接一台大型驅動機 —— 畫成一顆小方塊就是畫錯了。每一段之間各有一組段間冷卻器與分液罐。壓縮把裂解氣升壓，後面的深冷分離才做得下去。',
        items: ['裂解氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_caustic: {
        name: '鹼洗塔（脫酸性氣體）',
        desc: '明顯比分離塔細的一支高塔，夾在壓縮機的段與段之間，把裂解氣裡的酸性氣體洗掉。順序是：壓縮一至三段 → 鹼洗 → 再壓縮四至五段 → 乾燥。',
        items: ['裂解氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_dryer: {
        name: '乾燥器（一開一備的兩支吸附塔）',
        desc: '兩支一模一樣的立式吸附塔並聯，一支在用、一支在再生。水沒有除乾淨，後面的深冷分離會結冰堵塔 —— 這一格就是深冷分離的門票。',
        items: ['裂解氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_coldbox: {
        name: '冷箱（cold box）',
        desc: '★ 這是一個包厚保冷層、表面會結霜的方箱，不是塔 —— 畫成塔就是畫錯了。裡面把裂解氣冷到很低的溫度，先把氫氣分出來，剩下的才進脫甲烷塔。',
        items: ['裂解氣', '氫氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_towers: {
        name: '分離塔組：六支塔，高度明顯不一樣',
        desc: '由左到右：脫甲烷塔（最高最粗、包保冷）→ 脫乙烷塔 → 乙烯精餾塔 → 脫丙烷塔 → 丙烯精餾塔 → 脫丁烷塔（最矮）。碳數由小到大依序脫出，而且每一支精餾塔一定排在對應的「脫某某塔」之後。每支塔塔頂出輕的、塔底往下一支塔，頂部有回流冷凝器、底部有再沸器、旁邊一台泵 —— 沒有這三件的圓柱不是塔，是柱子。',
        items: ['乙烯', '乙烷', '丙烯', '丙烷', '混合碳四', '裂解汽油'],
        cos: ['6505'],
        none: `${FPCC}分離塔組以「順序分離流程」為例，不同專利商的流程不同（圖上已標）。${NOSC}`,
      },
      nc_hydro: {
        name: '碳二／碳三加氫反應器',
        desc: '短粗的立式圓筒，成對出現，把餾分裡的乙炔、丙炔等雜質加氫除掉，乙烯與丙烯才到得了聚合級。位置固定在「脫某某塔之後、精餾塔之前」。規格書把這一格的細節標成低～中信心，所以圖上只表達位置關係。',
        items: ['乙烯', '丙烯', '氫氣'],
        cos: ['6505'],
        none: `${FPCC}${NOSC}`,
      },
      nc_piperack: {
        name: '管廊（pipe rack）',
        desc: '一排架高的平行管束貫穿全廠 —— 這是石化廠一眼認得出的特徵，也是「各單元之間是用管子連起來的」這件事的畫面證據。地上亂拉的管子不是管廊。',
        items: [],
        cos: ['6505'],
        none: `管廊是廠區的公用設施，屬於廠的一部分。這座廠的營運方是 ${FPCC}${NOSC}`,
      },
      nc_spread: {
        name: '裂解價差（crack spread）',
        desc: '產品價格減掉原料成本的那一段。上面那條線是乙烯／丙烯賣得掉的價，下面那條是石油腦的成本 —— 兩條線的絕對高度沒有意義，有意義的只有中間那一段的厚度。石油腦漲、乙烯沒跟上就變薄，薄到倒掛就是開越多賠越多。',
        items: [],
        cos: [],
        none: '這不是一個零件，是這張圖的主旨。★ 圖上不放任何價差數字、產能噸數、市占率或營收占比 —— 那些會過期，而且要用得走供應鏈資料的 as_of／source／confidence 機制，不該寫死在圖裡。',
      },
      nc_c2_tank: {
        name: '乙烯低溫儲槽',
        desc: '立式圓筒，外面包一層厚保冷、再罩金屬皮，所以看起來比一般儲槽胖一圈。乙烯是這座廠最大宗的產品，下游是 PE、EG（經環氧乙烷）、VCM → PVC，以及乙苯 → 苯乙烯。',
        items: ['乙烯'],
        cos: ['6505'],
        none: `基本原料這一段是 ${FPCC}${NOSC}`,
      },
      nc_sphere: {
        name: '丙烯與丁二烯球槽（sphere）',
        desc: '★ 液化氣體放在球槽裡：球形 ＋ 數支支柱 ＋ 赤道一圈走道 —— 畫成開頂圓筒就是畫錯了（那是水池或常壓儲槽）。丙烯的下游是 PP、丙烯腈、丙烯酸酯；丁二烯的下游是合成橡膠與 ABS。',
        items: ['丙烯', '丁二烯'],
        cos: ['6505'],
        none: `基本原料這一段是 ${FPCC}${NOSC}`,
      },
      nc_bd_extract: {
        name: '丁二烯抽取單元（萃取蒸餾）',
        desc: '★ 丁二烯不是從裂解爐直接接一條線出來的：它是從脫丁烷塔的產物「混合碳四」裡抽出來的。兩支中等高度的塔加一個溶劑回收槽，用萃取蒸餾把丁二烯分離出來。',
        items: ['混合碳四', '丁二烯'],
        cos: ['6505', '1326'],
        none: `基本原料這一段是 ${FPCC}丁二烯的下游（合成橡膠、ABS）在台股對應到 1326 台化：營業項目含丁二烯與 ABS。${NOSC}`,
      },
      nc_btx: {
        name: '裂解汽油加氫 ＋ 芳香烴抽取（BTX）',
        desc: '★ 芳香烴不是從分離塔頂直接出來的：脫丁烷塔底的那一支叫「裂解汽油」，要先加氫、再抽取，才叫芳香烴（苯、甲苯、二甲苯）。苯往下走到苯乙烯（SM），對二甲苯（PX）往下走到 PTA。',
        items: ['裂解汽油', '苯', '對二甲苯（PX）'],
        cos: ['6505', '1326'],
        none: `裂解與基本原料這一段是 ${FPCC}芳香烴與聚酯原料那一條線在台股對應到 1326 台化：營業項目含 PX、苯、苯乙烯（SM）、PTA、ABS、PP。${NOSC}`,
      },
      nc_pe_pp: {
        name: '聚乙烯（PE）與聚丙烯（PP）造粒與粒料倉',
        desc: '一組筒倉加底部錐斗出料 —— 成品是「粒」，這是它跟 PTA（白色粉體）在圖上最好認的差別。PE 吃乙烯、PP 吃丙烯，是日用塑膠的兩大宗。',
        items: ['乙烯', '丙烯', '聚乙烯（PE）', '聚丙烯（PP）'],
        cos: ['1301', '1326'],
        none: '做這一格的台股是 1301 台塑：主要業務含聚氯乙烯（PVC）、聚丙烯（PP）、高密度聚乙烯、EVA、低密度聚乙烯、LLDPE、丙烯酸酯等塑膠原料；PP 另有 1326 台化（營業項目含 PP）。' + NOSC,
      },
      nc_pvc: {
        name: 'EDC → VCM → 聚氯乙烯（PVC）聚合釜',
        desc: '★ PVC 不是乙烯直接聚合：路徑是 乙烯＋氯 → 二氯乙烷（EDC）→ 氯乙烯（VCM）→ PVC，中間一定要看得到 VCM 這一格。聚合釜是立式反應釜，頂部有攪拌軸與馬達、外面有保溫夾套 —— 畫成塔就是畫錯了。',
        items: ['乙烯', '二氯乙烷（EDC）', '氯乙烯（VCM）', '聚氯乙烯（PVC）'],
        cos: ['1301'],
        none: '做這一格的台股是 1301 台塑：主要業務含聚氯乙烯（PVC）、氯乙烯、液鹼。' + NOSC,
      },
      nc_eg: {
        name: '乙二醇（EG）與可塑劑',
        desc: 'EG 來自乙烯（經環氧乙烷 EO），是聚酯的另一半原料；可塑劑則是讓 PVC 變軟的添加物。兩支小塔加一組儲槽就是這一格在圖上的樣子。',
        items: ['乙烯', '乙二醇（EG）', '可塑劑'],
        cos: ['1303'],
        none: '做這一格的台股是 1303 南亞：化工產品含乙二醇（EG）、雙酚 A、可塑劑、酞酸酐。★ 但南亞不只是石化 —— 它的事業橫跨塑膠加工、化工產品、電子材料、聚酯四塊，其中電子材料（玻纖絲、玻纖布、環氧樹脂、銅箔、銅箔基板）才是它在本站供應鏈資料裡掛節點的地方（銅箔／玻纖布／樹脂那一格）。只寫「南亞做石化」會誤導。' + NOSC,
      },
      nc_sm: {
        name: '苯乙烯（SM）：兩條線匯進來的那一格',
        desc: '★ 這一格是整張圖唯一有兩條線同時進來的地方：乙烯＋苯 → 乙苯 → 脫氫 → 苯乙烯。只畫一條線就是畫錯了。SM 往下是 ABS 與 PS。',
        items: ['乙烯', '苯', '苯乙烯（SM）'],
        cos: ['1326'],
        none: '做這一格的台股是 1326 台化：營業項目含苯乙烯（SM）、苯、ABS、PS。★ 台化的主戰場是芳香烴與聚酯原料那一條線 —— 把它跟 6505 台塑化放在同一段（裂解）是錯的。' + NOSC,
      },
      nc_pta: {
        name: '純對苯二甲酸（PTA）氧化反應器與結晶乾燥',
        desc: '★ PTA 的原料是對二甲苯（PX），走芳香烴那條線 —— 不是乙烯。這是這張圖最容易被內行人一眼抓到的錯。一個大立式氧化反應器接一段結晶與乾燥，成品是白色粉體（不是粒）。PTA 加 EG 就是聚酯。',
        items: ['對二甲苯（PX）', '純對苯二甲酸（PTA）'],
        cos: ['1326'],
        none: '做這一格的台股是 1326 台化：台灣 PTA 的領導廠商，在芳香烴鏈扮演重要供應角色。' + NOSC,
      },
    },
  });
})();
