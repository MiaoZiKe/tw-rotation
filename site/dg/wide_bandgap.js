/* 第三代半導體功率元件（SiC / GaN）—— docs/diagram_plan.md 的第 12 張
   （族群 `wide_bandgap`、semiconductor 鏈）

   合約＝`docs/diagram_specs/wide_bandgap.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的四件事：

     · §0 **不做真 3D**（`scene: null`）。六個資訊點裡有五個是「剖面上的層」，
       而且層厚差五、六個數量級（2DEG 是原子層級、基板數百 µm），3D 一渲染薄層就消失。
       要加 3D 的唯一條件是「功率模組內部的立體配置」，而那**應該另開一張圖**。
     · §3 四組最容易畫錯的順序全部寫死在下面各段的註解裡（W1–W21）。
       最重要的一組是 **W6／W11：兩支電流箭頭的方向差 90 度**（SiC 垂直、GaN 橫向）——
       缺了這一組，整張圖就只是兩疊有顏色的方塊。
     · §7-D1 **一個 `data-seg` 都不掛**（N6）。`supply_chain.yaml` 的 semiconductor 鏈
       14 格裡**沒有一格對應第三代半導體**，而三個看起來像的候選都會產生錯誤宣稱：
         foundry        → 等於宣稱「漢磊做先進邏輯代工」＋「台積電做 SiC 功率元件」
         semi_material  → 那一格是靶材與貴金屬回收（1785 光洋科），不是長晶／磊晶
         optical_epi    → 它確實是磊晶，但 chain 是 ai_server，掛跨鏈的 seg 在半導體鏈的圖上
                          環節色標根本不會有對應的 chip，點下去只會半動半不動
       **誠實的代價是：這張圖是純知識圖，點零件不會篩成分股。** 比掛一個錯的環節好。
     · §7-C7 **不畫穩懋與宏捷科**。一次 `WebSearch` 的摘要把這兩檔台股直接譯成
       「Transphorm」「Power Integrations」，那是摘要自己湊的；沒有獨立查證過它們在
       功率 GaN 上的定位，所以這張圖不畫它們，也不在任何地方宣稱它們做什麼。

   ⚠ 兩個實作上的取捨，寫在這裡不要讓下一個人再想一次
   ---------------------------------------------------
   1. **不能用 `D.processBar()`**：那支會輸出 `data-seg="…"`，這張圖依 N6 一個都不能有
      （seg 傳 undefined 會變成字串 "undefined"，那比沒掛更糟）。所以底下自己寫了一支
      `pbar()`，只有 `data-part`。這是共用工具跟規格衝突時的例外，不是「自己造第二套」。
   2. **沒有 `data-seg` ＝ 沒有零件小卡**：`site/industry.js` 的 `wireDiagram()` 只對
      `[data-seg]` 綁點擊，`renderPartCard()` 也在 `if (!seg)` 就把小卡藏起來。
      所以「這一塊是誰做的」全部**印在畫面上**（右下說明框 ＋ 流程列的台股標示線），
      不是留白。下面的 `parts:` 照 `docs/diagram_purpose.md` §4 寫齊，
      等 industry.js 支援「沒有 seg 也能開小卡」就會自己亮起來。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/three3d.js`。
   色值一律走 `--dg-*`，JS 裡一個 #xxxxxx 都沒有。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  /* ★ 2026-09-23（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
     並且需要適當的調整及填充版面間隔，不許有空白」）
     -------------------------------------------------------------------------
     原本：980 寬，上半是兩個 464 寬的大框（左 SiC、右 GaN），框內下半用四列
           `crow()` 自己畫的說明列；中段兩個框、下面兩個結論框。
           框與框之間、框內標註列右邊都留著大片空白，而且 464 寬的框裡塞 440 寬的說明列，
           字只能寫得很短。
     現在：跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套
           （DECISIONS #238／#239 的 v2 風格）：
             · svg 根掛 `rs` → `externalize()` 把說明卡片搬成 HTML（.dgc）排進畫布左右兩欄，
               欄寬由 index.html 的 .dgv2 容器查詢決定 —— 版面自己填滿，這個檔不再寫死欄位。
               `crow()` 因此整支退場，改用共用的 `extRow`（卡片 ＋ 畫布上的編號圓點 ＋ 引線）。
             · 畫布收到 **660**（主角寬），`native` 跟著改；主畫面只留「SiC 垂直 vs GaN 橫向」
               這一組對照（這張圖的命題），溝槽閘／GaN-on-SiC／Cascode 收進章節 ①。
             · 材質走共用介面 `D.fx`（`glowDefs`／`glass`／`beam`／`shadows`）。
             · 章節改用 `D.fold()`（範圍由 getBBox 量），不再自己排 y。
     沒有放寬的事：**一個 `data-seg` 都不掛**（§7-D1／N6 照舊），22 個 `data-part` 一個不改名。*/
  const CW = 660;

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const E = (cx, cy, rx, ry, fill, cls) =>
    `<ellipse${cls ? ` class="${cls}"` : ''} cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}"/>`;
  const P = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const line = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;

  /* 元件色（卡片 data-dgcolor ＋ 編號圓點 ＋ 引線端點共用），全部是 index.html 既有的 token */
  const C = {
    si: 'var(--dg-si)', si2: 'var(--dg-si-2)', org: 'var(--dg-organic)', org2: 'var(--dg-organic-2)',
    sr: 'var(--dg-sr)', sr2: 'var(--dg-sr-2)', alu: 'var(--dg-alu)', el: 'var(--dg-el)',
    steel: 'var(--dg-steel)', au: 'var(--dg-au)', emc: 'var(--dg-emc)', cyan: 'var(--dg-accent-2d)',
    warn: 'var(--dg-warn)', mute: 'var(--dg-mute)', cover: 'var(--dg-cover)',
  };
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點 ＋ 引線。
     ⚠ 這張圖沒有 data-seg，所以 `extRow` 不傳 seg —— 卡片仍然畫得出來，
        只是跟現況一樣點了不會篩成分股（N6 的既定代價，不是壞掉）。*/
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };
  /* 一顆沿著路徑跑的電荷。路徑字串跟箭頭是分開的兩條 —— 箭頭是靜止時就看得見的那一條，
     這顆點只是在同一條路線上跑。按「動畫：關」之後 svg.pauseAnimations() 會把它停住。*/
  const charge = (d) =>
    `<circle r="3.4" fill="${C.cyan}"><animateMotion dur="3.2s" repeatCount="indefinite" path="${d}"/></circle>`;
  /* 電流箭頭。**SiC 與 GaN 用同一支函式**，只有 (dx, dy) 差 90 度 ——
     W11 要求的「同樣式、方向差 90 度」就是這一行保證的。*/
  function arrow(x, y, dx, dy, col, w2) {
    const L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, x2 = x + dx, y2 = y + dy, a = 6;
    return line(`M${x},${y} L${x2},${y2}`, col, w2 || 2.6)
      + P(`M${x2},${y2} L${(x2 - ux * 11 - uy * a).toFixed(1)},${(y2 - uy * 11 + ux * a).toFixed(1)}`
        + ` L${(x2 - ux * 11 + uy * a).toFixed(1)},${(y2 - uy * 11 - ux * a).toFixed(1)}Z`, col);
  }

  /* ================================================================ 左：SiC MOSFET 垂直剖面
     由下到上（W2）：汲極金屬 → n⁺ 基板 → n⁻ 漂移層 → p-body／n⁺ source → 閘極氧化層 → 閘極 → 源極金屬。
     W1：**汲極在背面（296–310）、源極與閘極在正面（126–160）** —— 三個電極畫在同一面就是 GaN 不是 SiC。
     W3：基板 84px、漂移層 52px —— 基板**畫得比漂移層厚**（基板是機械支撐，漂移層是磊晶長的）。
     W4：閘極氧化層 3px，是全圖最薄的一層之一，而且一定夾在閘極與半導體之間。
     W5：n⁺ 源極區被 p-body 包住（左右與下方都有 p-body），沒有碰到 n⁻ 漂移層。
     W6：電流箭頭**垂直**，由正面往背面。
     W7／W8：平面閘那一格標出 JFET 區；溝槽閘那一格**沒有** JFET 區，而且閘極真的挖進半導體裡。
     W9（S9）：兩格**用同一支函式**，只有閘極那一段的參數不同。
     2026-09-23：金屬與半導體大塊改走 `fx.glass`（玻璃板材質，跟 AI 伺服器那三張同一套），
     幾何一個數字都沒動 —— 兩格仍然是同一支函式產生的。*/
  function sicCell(ox, trench) {
    const g = [];
    const slab = (x, y, w, h, fill, rx) => fx.glass(x, y, w, h, { fill, cls: 'part', rx: rx || 1 });
    g.push(part('wbg_sic_drain', slab(ox + 2, 296, 200, 14, C.steel)));
    g.push(part('wbg_sic_sub', slab(ox + 2, 212, 200, 84, C.si2)));
    g.push(part('wbg_sic_drift', slab(ox + 2, 160, 200, 52, C.si)
      + `<g opacity=".18">${R(ox + 2, 160, 200, 52, 'var(--dg-ink)')}</g>`
      + line(`M${ox + 2},212 H${ox + 202}`, C.cover, 1.2)));
    if (trench) {
      // 溝槽：閘極從表面往下挖進半導體，兩塊 p-body 緊貼溝槽兩側；JFET 區被消掉
      g.push(part('wbg_sic_body', R(ox + 34, 160, 52, 26, C.org, 'part')
        + R(ox + 118, 160, 52, 26, C.org, 'part')));
      g.push(part('wbg_sic_src', R(ox + 40, 160, 26, 12, C.sr, 'part')
        + R(ox + 138, 160, 26, 12, C.sr, 'part')
        + slab(ox + 2, 126, 200, 14, C.alu)
        + R(ox + 40, 140, 26, 20, C.alu, 'part') + R(ox + 138, 140, 26, 20, C.alu, 'part')));
      g.push(part('wbg_sic_trench', R(ox + 86, 160, 32, 44, C.el, 'part')
        + line(`M${ox + 86},160 V204 H${ox + 118} V160`, C.cover, 3)
        + R(ox + 86, 146, 32, 14, C.el, 'part')));
      g.push(part('wbg_sic_i', arrow(ox + 102, 210, 0, 82, C.cyan)
        + charge(`M${ox + 102},150 V292`)));
    } else {
      g.push(part('wbg_sic_body', R(ox + 18, 160, 52, 26, C.org, 'part')
        + R(ox + 134, 160, 52, 26, C.org, 'part')));
      g.push(part('wbg_sic_src', R(ox + 24, 160, 26, 12, C.sr, 'part')
        + R(ox + 154, 160, 26, 12, C.sr, 'part')
        + slab(ox + 2, 126, 200, 14, C.alu)
        + R(ox + 24, 140, 26, 20, C.alu, 'part') + R(ox + 154, 140, 26, 20, C.alu, 'part')));
      // JFET 區：兩個 p-body 之間被夾住的那條窄路（只有平面閘才有）
      g.push(part('wbg_sic_jfet', `<g opacity=".45">${R(ox + 70, 160, 64, 36, C.warn, 'part')}</g>`
        + line(`M${ox + 70},160 V196 M${ox + 134},160 V196`, C.warn, 1.4)));
      g.push(part('wbg_sic_gox', R(ox + 62, 145, 80, 12, C.el, 'part')
        + R(ox + 62, 157, 80, 3, C.cover, 'part')));
      g.push(part('wbg_sic_i', arrow(ox + 102, 198, 0, 94, C.cyan)
        + charge(`M${ox + 102},140 V292`)));
    }
    return g.join('');
  }

  /* ================================================================ 右：GaN HEMT 橫向剖面
     W9：**2DEG 畫在 AlGaN／GaN 界面的 GaN 那一側**（界面在 yTop+12，2DEG 畫在 yTop+15）——
        畫在 AlGaN 裡或兩層正中央都是錯的（那是極化誘發、長在 GaN 這一側的）。
     W10：源、閘、汲**三個電極全部在上表面**，背面一個電極都沒有。
     W11：電流箭頭**橫向**，與 SiC 那支同樣式、方向差 90 度。
     W12：AlGaN 阻障層 12px **比** GaN 通道層 30px **薄**。
     W13：GaN-on-Si 的緩衝層畫 6 層（厚）、GaN-on-SiC 畫 2 層（薄）—— 晶格失配差很多。
     W14：p-GaN **夾在閘極金屬與 AlGaN 之間**。
     2026-09-23：原本是「x／y 全部寫死在呼叫端」，畫布收窄之後只要改一個數字就會全歪，
     所以改成 `ganCell(x0, w, yTop, …)` 一支把電極與 p-GaN 一起算 —— 兩個基板版本共用它。*/
  function ganCell(x0, w, yTop, nBuf, subFill, id, withGate) {
    const buf = [], bh = 20 / nBuf;
    for (let i = 0; i < nBuf; i++) buf.push(R(x0, yTop + 42 + i * bh, w, bh - 0.6, C.org2, 'part'));
    const gx = x0 + w / 2 - 22;
    const stack = part(id + '_sub', fx.glass(x0, yTop + 62, w, 54, { fill: subFill, cls: 'part', rx: 1 }))
      + part('wbg_gan_buf', buf.join(''))
      + part('wbg_gan_ch', fx.glass(x0, yTop + 12, w, 30, { fill: C.sr2, cls: 'part', rx: 1 }))
      + part('wbg_gan_bar', fx.glass(x0, yTop, w, 12, { fill: C.sr, cls: 'part', rx: 1 }))
      + part('wbg_2deg', line(`M${x0 + 2},${yTop + 15} H${x0 + w - 2}`, C.au, 2.6));
    if (!withGate) return stack;
    return stack
      + part('wbg_gan_elec', R(x0 + 10, yTop - 18, 46, 18, C.alu, 'part')
        + R(x0 + w - 56, yTop - 18, 46, 18, C.alu, 'part')
        + R(gx, yTop - 24, 44, 18, C.el, 'part'))
      + part('wbg_pgan', R(gx + 4, yTop - 6, 36, 6, C.org, 'part'))
      + part('wbg_gan_i', arrow(x0 + 60, yTop + 27, w - 118, 0, C.cyan)
        + charge(`M${x0 + 36},${yTop + 27} H${x0 + w - 14}`));
  }

  /* Cascode（W15）：**對外控制端是低壓 Si MOSFET 的閘極**，GaN 的閘極接到 Si 的源極。
     2026-09-23：從寫死的 842/124 改成吃 (x, y)，才搬得進章節 ①。*/
  function cascode(x, y) {
    return part('wbg_cascode', `${R(x, y, 36, 26, C.el, 'part', 3)}${R(x, y + 36, 36, 26, C.sr2, 'part', 3)}
      ${line(`M${x + 18},${y + 26} V${y + 36}`, C.cyan, 2)}
      ${line(`M${x - 28},${y + 13} H${x}`, C.cyan, 1.6)}
      ${line(`M${x},${y + 49} H${x - 28} V${y + 31} H${x + 18}`, C.cyan, 1.6)}
      ${arrow(x - 56, y + 13, 24, 0, C.warn, 2)}
      ${line(`M${x + 18},${y - 12} V${y} M${x + 18},${y + 62} V${y + 74}`, C.cyan, 2)}
      ${T(x + 42, y + 17, '低壓 Si', 'sub')}
      ${T(x + 42, y + 53, '常開 GaN', 'sub')}`);
  }

  /* ================================================================ 電壓／頻率帶狀圖（章節 ②）
     W16：三條帶**必須互相重疊** —— 650V 那一段是 GaN 與 SiC 同時存在的區域，
          畫成三個互不相交的方塊就是在宣稱一件不成立的事。
     W17：不准出現「一定要選 X」這種絕對句，一律寫「大致在 …」。
     W18：軸上只標量級刻度，**不標任何市占或出貨量**。
     2026-09-23：框寬 464 → 628（畫布收窄但版面變滿），刻度換算跟著吃新的 X1。*/
  function bandChart(x, y, w) {
    const X0 = x + 74, X1 = x + w - 24;
    const tick = (frac, t) => {
      const px = X0 + (X1 - X0) * frac;
      return line(`M${px},${y + 52} V${y + 158}`, 'var(--dg-axis, var(--dg-line-mix))', 1, ' stroke-dasharray="3 4"')
        /* ★ 2026-09-26 覆蓋普查：刻度字原本一律從 px−16 靠左起筆，最右那一格「1700V+」比別人長，
           右緣伸出外框 3.6px（字壓在框線上）。改成置中對齊刻度線；最右那一格靠右對齊、收在框內 10px。*/
        + (frac >= 1
          ? `<text class="sub" x="${X1 + 14}" y="${y + 176}" text-anchor="end">${t}</text>`
          : `<text class="sub" x="${px}" y="${y + 176}" text-anchor="middle">${t}</text>`);
    };
    const bar = (frac0, frac1, yy, fill) =>
      R(X0 + (X1 - X0) * frac0, yy, (X1 - X0) * (frac1 - frac0), 26, fill, 'part', 5);
    return `<g data-part="wbg_band">
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="210" rx="9"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">誰守哪一段（大致的範圍，而且是重疊的）</text>
      <text class="sub" x="${x + 14}" y="${y + 44}">縱軸往上＝切換頻率越高　橫軸往右＝耐壓越高</text>
      ${tick(0, '100V')}${tick(0.42, '650V')}${tick(0.72, '1200V')}${tick(1, '1700V+')}
      <g opacity=".62">${bar(0, 0.52, y + 56, C.sr)}</g>
      <g opacity=".62">${bar(0.3, 1, y + 92, C.si)}</g>
      <g opacity=".62">${bar(0, 0.86, y + 128, C.mute)}</g>
      <text class="lbl" x="${x + 14}" y="${y + 74}">GaN</text>
      <text class="lbl" x="${x + 14}" y="${y + 110}">SiC</text>
      <text class="lbl" x="${x + 14}" y="${y + 146}">Si</text>
      <text class="sub" x="${x + 14}" y="${y + 196}">1200V GaN 已在送樣但仍屬特殊品，邊界正在移動（來源：產業媒體，2026）。</text></g>`;
  }

  /* ================================================================ 長晶 → 晶碇 → 切片（2.5D 小圖，章節 ②）
     這是整張圖唯一「有立體感才說得清楚」的一段（§0 判定：2.5D 就夠，不值得開一個 WebGL 場景）。*/
  function boule(x, y, w) {
    const cx = x + 120, top = y + 70, h = 74, rx = 38, ry = 13;
    const discs = [];
    for (let i = 0; i < 4; i++) {
      const dx = x + 268 + i * 48;
      discs.push(E(dx, y + 118, 30, 11, C.si, 'part')
        + E(dx, y + 112, 30, 11, C.si2, 'part'));
    }
    return `<g data-part="wbg_boule">
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="210" rx="9"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">長晶（PVT 昇華法）→ 晶碇 → 切片</text>
      <text class="sub" x="${x + 14}" y="${y + 44}">高溫下原料昇華、在籽晶上重新凝結長成晶碇，再用線鋸切成晶片</text>
      ${fx.glass(cx - rx, top, rx * 2, h, { fill: C.si2, cls: 'part', rx: 2 })}
      ${E(cx, top, rx, ry, C.si, 'part')}
      ${E(cx, top + h, rx, ry, C.si2, 'part')}
      ${arrow(cx + rx + 12, y + 112, 30, 0, C.cyan, 2.4)}
      ${discs.join('')}
      <text class="sub" x="${x + 84}" y="${y + 172}">晶碇（boule）</text>
      <text class="sub" x="${x + 250}" y="${y + 172}">線鋸切片 → 研磨 → 拋光（CMP）</text>
      <text class="sub" x="${x + 14}" y="${y + 196}" style="fill:${C.warn}">★ 缺陷（微管、基面差排）在長晶這一步就決定了，後面救不回來。</text></g>`;
  }

  /* ================================================================ 流程列（六格，第六格是灰的；章節 ③）
     ⚠ 不用 `D.processBar()` —— 那支會輸出 data-seg，這張圖依 N6 一個都不能有（檔頭有說明）。
     W19／W20：長晶 → 切片 → 研磨拋光 → **磊晶** → 元件製造，**磊晶一定在切片與拋光之後**。
     W21：第 4、5 格底下有台股標示線；第 1～3 格誠實標「本圖查不到具名對應」。
     2026-09-23：畫布 660 放不下六格橫排（原本 145×6 ＋ 間距 ＝ 950），改成 **3 ＋ 3 兩列**，
     列與列之間用一條往下折的線接起來 —— 順序照樣讀得出來，也不用把字縮小。*/
  const STEPS = [
    ['① 長晶', 'PVT 昇華法', 0],
    ['② 切片', '線鋸切成晶片', 0],
    ['③ 研磨拋光', '研磨 → 拋光 CMP', 0],
    ['④ 磊晶', 'CVD 長出漂移層', 1],
    ['⑤ 元件製造', '閘極、通道、電極', 1],
    ['⑥ 封裝模組', '不在這張圖', 2],
  ];
  function pbar(x, y) {
    const w = 196, gap = 20, cols = 3, rowH = 66;
    return `<g data-part="wbg_flow">${STEPS.map((s, i) => {
      const bx = x + (i % cols) * (w + gap), by = y + Math.floor(i / cols) * rowH;
      const off = s[2] === 2;
      const ink = off ? ` style="fill:${C.mute}"` : '';
      let link = '';
      if (i < STEPS.length - 1) {
        link = (i % cols === cols - 1)
          ? line(`M${bx + w},${by + 22} h8 V${by + 54} H${x - 8} V${by + rowH + 22} h8`, C.cyan, 2)
          : line(`M${bx + w + 2},${by + 22} h${gap - 4}`, C.cyan, 2);
      }
      return R(bx, by, w, 44, 'var(--dg-step-f, var(--dg-frame))', 'part', 7)
        + (off ? line(`M${bx},${by} h${w} v44 h${-w}Z`, C.mute, 1.4, ' stroke-dasharray="5 4"') : '')
        + (s[2] === 1 ? line(`M${bx},${by + 44} h${w}`, C.cyan, 3) : '')
        + `<text class="lbl" x="${bx + 12}" y="${by + 18}"${ink}>${s[0]}</text>`
        + `<text class="sub" x="${bx + 12}" y="${by + 34}"${ink}>${s[1]}</text>` + link;
    }).join('')}</g>`;
  }

  /* ================================================================ 章節內容 */
  function areaVariants() {
    /* ★ 2026-09-23：三欄（24／300／500）在淺色主題（字大一階）量到三對字疊在一起 ——
       660 寬裝不下三欄說明。改成**兩欄**：左欄一整格溝槽閘，右欄上下放 GaN-on-SiC 與 Cascode。
       內容一句都沒刪，只有換欄與斷行。*/
    return `<g>
      <!-- ★ 2026-09-26 覆蓋普查：閱讀模式（字大一階）這一行比 660 寬的畫布多出 10px、尾巴被切掉 —— 拆成兩行，字一個都沒刪 -->
      ${T(16, 362, '① 另外兩種做法：溝槽閘（消掉 JFET 區）、GaN-on-SiC（緩衝層薄）、', 'hd')}
      ${T(16, 381, 'Cascode（常關）', 'hd')}
      ${T(24, 408, '溝槽閘：把閘極挖進去', 'lbl')}
      ${T(24, 428, '兩格同一比例、同一畫法，', 'sub')}
      ${T(24, 446, '只有閘極那一段不同 —— 溝槽', 'sub')}
      ${T(24, 464, '把 JFET 區消掉了。', 'sub')}
      <!-- ★ 2026-09-26 覆蓋普查（Andy 抓到的那一格）：剖面原本平移 316，頂部的源極金屬落在 y≈442，
           正好壓在上面三行說明的第 2～3 行（基線 446／464）上。往下移 40（頂部 ≈482，離最後一行留 14px），
           圖註跟著下移；右欄與整段的高度不受影響（右欄最低到 820）。剖面本身一筆都沒改。 -->
      <g transform="translate(0,356)">${sicCell(24, true)}</g>
      ${T(24, 680, '（幾何與主畫面那一格完全一致）', 'cap')}

      ${T(330, 408, 'GaN-on-SiC：緩衝層薄', 'lbl')}
      ${T(330, 428, '長在 Si 上晶格差約 17%，要厚過渡；', 'sub')}
      ${T(330, 446, '長在 SiC 上只差約 3.5%，兩層就夠。', 'sub')}
      ${ganCell(330, 190, 470, 2, C.si2, 'wbg_gan_sic', false)}
      ${T(330, 606, '（這一格只畫疊構，電極與 p-GaN 見主畫面那一格）', 'cap')}

      ${T(330, 646, 'Cascode：控制端是那顆 Si', 'lbl')}
      ${T(330, 666, '低壓 Si 串一顆常開 GaN；', 'sub')}
      ${T(330, 684, '對外控制的是那顆 Si 的閘極。', 'sub')}
      ${cascode(400, 712)}
      ${T(16, 820, '示意圖，非實物比例｜溝槽深度、緩衝層層數與 Cascode 的封裝內配置均為示意。', 'cap')}</g>`;
  }

  function areaMarket() {
    return `<g>${bandChart(16, 700, 628)}${boule(16, 930, 628)}</g>`;
  }
  function areaFlow() {
    return `<g>
      ${T(16, 1180, '這條鏈分五段，順序不准對調 —— 磊晶是長在「已經拋好的晶片表面」上的，', 'cap')}
      ${T(16, 1198, '畫在切片之前整條流程的意義就消失了。', 'cap')}
      ${pbar(16, 1212)}
      ${T(16, 1372, '▲ 青色底線的兩格＝台股目前指得出名字的那兩段（見下面那兩個框）。', 'sub', null, `fill:${C.cyan}`)}
      ${T(16, 1392, '★ 第 ①～③ 段（長晶／切片／研磨拋光）：本圖查不到台股的具名對應 —— 查不到就寫查不到。', 'sub', null, `fill:${C.warn}`)}

      ${frame(16, 1412, 628, 128)}
      ${T(30, 1436, '為什麼是這兩種材料', 'hd')}
      ${T(30, 1458, '① 能隙寬 → 崩潰電場高 → 同樣耐壓所需的漂移層更薄 → 導通電阻低、損耗小、元件可以更小', 'sub')}
      ${T(30, 1478, '② SiC 的導熱好 → 同樣的損耗更容易散掉 → 功率密度可以更高', 'sub')}
      ${T(30, 1498, '③ 這兩件事在「高壓 ＋ 每一瓦都算錢」的地方最值錢 —— 所以主戰場是車用（主驅逆變器、', 'sub')}
      ${T(30, 1518, '　 車載充電器 OBC）與電源（充電樁、光伏逆變器）', 'sub')}

      ${frame(16, 1552, 628, 148)}
      ${T(30, 1576, '台股在哪一段', 'hd')}
      ${T(30, 1598, '「第三代半導體」族群目前只收兩檔，兩家同屬漢民集團：', 'sub')}
      ${T(30, 1618, '· 3016 嘉晶 —— ④ 磊晶（台灣少數能量產 SiC 與 GaN 磊晶者）', 'sub')}
      ${T(30, 1638, '· 3707 漢磊 —— ⑤ 元件製造（SiC／GaN 功率半導體晶圓代工）', 'sub')}
      ${T(30, 1658, '另有 5347 世界先進取得台積電 GaN 技術授權（來源：媒體報導，2025–2026），', 'sub')}
      ${T(30, 1678, '但它掛在別的族群。', 'sub')}</g>`;   /* ★ 2026-09-26 覆蓋普查：閱讀模式這一行伸出框 13px → 拆兩行、框加高 20 */
  }

  /* ================================================================ 整張圖 */
  function wideBandgap() {
    return `<svg class="dg dgm rs dgwbg" viewBox="0 0 ${CW} 1700" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           這張圖**一個 data-seg 都沒有**（§7-D1），所以 diagrams.js 那一整組
           「.dg [data-seg] …」的規則一條都吃不到 —— 描邊、引線的 fill、
           被點到的高亮，全部要在這裡自己給。
           顏色一律走 --dg-*（四個配色都換得掉），JS 與這裡都沒有寫死色票。*/
        svg.dgwbg [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;
          transition:stroke .15s,filter .15s}
        svg.dgwbg [data-part]{cursor:default}
        svg.dgwbg [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgwbg [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgwbg .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgwbg .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">第三代半導體：SiC 守高壓、GaN 搶高頻 —— 台股卡在哪一段</text>
      <text class="cap ext" x="0" y="0">「寬能隙」換到的是「同樣耐壓下，漂移層可以做得更薄」。結構決定戰場：SiC 讓電流垂直穿過整片晶片（汲極在背面），GaN 讓電流橫著在表面下的一層電子氣裡跑（三個電極都在上表面）—— 兩支電流箭頭方向差 90 度，這就是整張圖的命題。本圖只講功率元件；射頻 GaN 與 LED 不在此圖。溝槽閘／GaN-on-SiC／Cascode、電壓頻率帶狀圖、長晶到切片、五段流程與台股名單收在下面三段。</text>

      <!-- ================= §1 兩種結構並排（永遠看得到）：左垂直、右橫向 ================= -->
      ${T(24, 58, 'SiC MOSFET：垂直導通', 'hd')}
      ${T(24, 78, '電流穿過整片晶片，耐壓靠厚度', 'sub')}
      ${T(24, 98, '汲極在背面、源極與閘極在正面', 'sub', null, `fill:${C.warn}`)}
      ${T(306, 58, 'GaN HEMT：橫向導通', 'hd')}
      ${T(306, 78, '電流在表面下的一層電子氣裡跑', 'sub')}
      ${T(306, 98, '三個電極都在上表面、背面沒有電極', 'sub', null, `fill:${C.warn}`)}
      ${fx.shadows(`<rect x="35" y="132" width="200" height="184" rx="3"/><rect x="309" y="190" width="292" height="122" rx="3"/>`)}
      ${sicCell(30, false)}
      ${ganCell(306, 292, 184, 6, C.emc, 'wbg_gan', true)}
      <!-- ⚠ 左欄的圖說一行最多 22 個字（30 → 306 只有 276px），超過就會伸進右欄那一格
           —— 2026-09-23 第一版就是這樣在 1440 撞到「GaN-on-Si…」那一行。-->
      ${T(30, 330, '平面閘（DMOS）：留著 JFET 區。', 'cap')}
      ${T(30, 348, '溝槽閘把它消掉，見第 ① 段。', 'cap')}
      ${T(30, 366, '青色箭頭＝電流，垂直貫穿晶片。', 'cap')}
      ${T(306, 330, 'GaN-on-Si：晶格差得多，緩衝層要厚（6 層）。', 'cap')}
      ${T(306, 348, '三個電極都在上表面，背面沒有電極。', 'cap')}
      ${T(306, 366, '青色箭頭＝電流，橫著跑 —— 與左邊差 90 度。', 'cap')}

      <!-- ================= 說明卡片（HTML，左欄＝SiC；右欄＝GaN） ================= -->
      ${card({ part: 'wbg_sic_drift', no: 1, side: 'l', color: C.si, ax: 36, ay: 186, title: '漂移層＝耐壓的來源', sub: ['崩潰電場高 → 同樣耐壓只要更薄的一層 → 導通電阻低、損耗小。'] })}
      ${card({ part: 'wbg_sic_sub', no: 2, side: 'l', color: C.si2, ax: 36, ay: 254, title: 'n⁺ SiC 基板（長晶切出來的）', sub: ['機械支撐 ＋ 導電；它比漂移層厚得多，品質決定磊晶好不好長。'] })}
      ${card({ part: 'wbg_sic_gox', no: 3, side: 'l', color: C.el, ax: 132, ay: 151, title: '閘極氧化層（MOSFET 的定義特徵）', sub: ['夾在閘極與半導體之間，是全圖最薄的一層之一 —— 少了它就不是 MOSFET。'] })}
      ${card({ part: 'wbg_sic_jfet', no: 4, side: 'l', color: C.warn, ax: 132, ay: 178, title: 'JFET 區（只有平面閘才有）', sub: ['兩個 p-body 把電流夾成一條窄路；溝槽閘把閘極挖進去就消掉它（見第 ① 段）。'] })}
      ${card({ part: 'wbg_sic_src', no: 5, side: 'l', color: C.alu, ax: 54, ay: 133, title: '源極金屬 ＋ n⁺ 源極區', sub: ['★ 源極與閘極都在正面。n⁺ 源極區被 p-body 包住，沒有碰到漂移層。'] })}
      ${card({ part: 'wbg_sic_body', no: 6, side: 'l', color: C.org, ax: 62, ay: 172, title: 'p-body', sub: ['把源極區包住，也是通道形成的地方；兩塊 p-body 之間就是 JFET 區。'] })}
      ${card({ part: 'wbg_sic_drain', no: 7, side: 'l', color: C.steel, ax: 66, ay: 303, title: '汲極金屬（★ 在背面）', sub: ['三個電極畫在同一面的話，那畫的就是 GaN 不是 SiC。'] })}
      ${card({ part: 'wbg_sic_i', no: 8, side: 'l', color: C.cyan, ax: 132, ay: 250, title: '電流：垂直貫穿（正面 → 背面）', sub: ['跟右邊 GaN 那支箭頭同樣式、方向差 90 度 —— 缺了這一組，兩邊只是有顏色的方塊。'] })}
      ${card({ part: 'wbg_2deg', no: 9, side: 'r', color: C.au, ax: 592, ay: 199, title: '二維電子氣 2DEG（界面的 GaN 那一側）', sub: ['界面自己長出一層電子；跑得快 → 切換可以到 MHz 級。畫在 AlGaN 裡是錯的。'] })}
      ${card({ part: 'wbg_gan_bar', no: 10, side: 'r', color: C.sr, ax: 322, ay: 190, title: 'AlGaN 阻障層（比通道層薄）', sub: ['靠它與 GaN 的極化差，在界面誘發出 2DEG。'] })}
      ${card({ part: 'wbg_gan_ch', no: 11, side: 'r', color: C.sr2, ax: 592, ay: 218, title: 'GaN 通道層', sub: ['2DEG 就長在它靠近界面的那一側；電流整段都在這裡橫著跑。'] })}
      ${card({ part: 'wbg_gan_buf', no: 12, side: 'r', color: C.org2, ax: 592, ay: 238, title: '緩衝層：厚薄由基板決定', sub: ['長在 Si 上晶格差約 17%，要厚過渡（本格畫 6 層）；長在 SiC 上只差約 3.5%。'] })}
      ${card({ part: 'wbg_gan_sub', no: 13, side: 'r', color: C.emc, ax: 592, ay: 273, title: '基板（本格是 Si）', sub: ['★ 背面沒有電極 —— GaN HEMT 的三個電極全部在上表面，所以它做不上高壓。'] })}
      ${card({ part: 'wbg_gan_elec', no: 14, side: 'r', color: C.alu, ax: 578, ay: 175, title: '源／閘／汲：三個都在上表面', sub: ['跟 SiC 最明顯的差別。閘極在中間、源汲在兩側。'] })}
      ${card({ part: 'wbg_pgan', no: 15, side: 'r', color: C.org, ax: 452, ay: 181, title: 'p-GaN 閘（常關做法之一）', sub: ['夾在閘極金屬與 AlGaN 之間，把閘下的 2DEG 耗盡 → 常關。另一種做法是 Cascode（第 ① 段）。'] })}
      ${card({ part: 'wbg_gan_i', no: 16, side: 'r', color: C.cyan, ax: 470, ay: 211, title: '電流：橫向（在 2DEG 裡）', sub: ['與左邊 SiC 那支同樣式、方向差 90 度。'] })}
      ${note({ side: 'r', order: 0, warn: true, title: '★ 這一格在供應鏈資料裡還沒有對應環節', lines: ['所以點零件不會篩成分股 —— 那不是壞掉。硬掛 foundry／semi_material 會在公開網站上產生錯誤宣稱（例如「漢磊做先進邏輯代工」「光洋科做矽晶圓」），所以一個都不掛。誰做哪一段直接印在第 ③ 段的兩個框裡。'] })}
      ${note({ side: 'l', order: 98, title: '示意圖，非實物比例', lines: ['各層厚度均為示意：基板數百 µm、漂移層數十 µm、AlGaN 阻障層數十 nm、2DEG 是原子層級 —— 真實比例畫不出來。'] })}
      ${note({ side: 'l', order: 99, title: '這張圖不畫的事', lines: ['射頻 GaN 與 LED（同樣是 GaN，但應用、客戶與台股完全不同一批）；任何良率、成本與產能數字。', '★ 另有兩檔化合物半導體代工股，一次搜尋摘要把它們直接譯成兩家美國公司 —— 那組對應是摘要自己湊的，沒有獨立查證過，所以這張圖連名字都不寫（§7-C7）。'] })}

      <!-- ================= ① 溝槽閘 ／ GaN-on-SiC ／ Cascode（預設收合） ================= -->
      ${fold('wbg1', '① 另外兩種做法：溝槽閘、GaN-on-SiC、Cascode',
      '溝槽閘把閘極挖進去消掉 JFET 區；長在 SiC 上緩衝層只要兩層；Cascode 的控制端是那顆 Si', areaVariants())}

      <!-- ================= ② 誰守哪一段 ＋ 長晶到切片（預設收合） ================= -->
      ${fold('wbg2', '② 誰守哪一段（重疊的帶狀圖）＋ 長晶 → 晶碇 → 切片',
      '三條帶必須互相重疊；缺陷在長晶那一步就決定了，後面救不回來', areaMarket())}

      <!-- ================= ③ 五段流程 ＋ 台股在哪一段（預設收合） ================= -->
      ${fold('wbg3', '③ 這條鏈分五段（第六段不在這張圖）＋ 台股在哪一段',
      '磊晶一定在切片與拋光之後；青色底線的兩格＝台股指得出名字的那兩段', areaFlow())}
    </svg>`;
  }

  window.DG.register('wide_bandgap', {
    level: 'group', chain: 'semiconductor',
    name: '第三代半導體：SiC 與 GaN 功率元件',
    draw: wideBandgap, native: CW, scene: 'wide_bandgap',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
                       那個判斷被推翻的理由寫在 site/three3d.js 的 SCENES.wide_bandgap 檔頭（一句話：這張圖最重要的那件事本來就是三維的）。2D 的 data-part 與 3D 的 part 是同一組，所以切過去還是選著同一個零件。*/
    q: 'SiC 跟 GaN 差在哪？為什麼一個守高壓、一個守高頻？台股是在做材料還是做元件？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       ⚠ 這張圖**一個 data-seg 都沒有**（§7-D1／N6），而 `site/industry.js` 的
       `renderPartCard()` 在 `if (!seg)` 就把小卡藏起來 —— 所以**現在一張小卡都不會出現**。
       這裡照樣逐件寫齊，理由跟 `power_inductor.js` 一樣：
         ① 這是這份對應該住的地方；② industry.js 一支援就自己亮起來；
         ③ 在那之前，「誰做的」已經印在畫面上（流程列的台股標示線 ＋ 右下說明框），不是留白。
       每一條的 `none` 都照 R4／R5 寫：查得到就寫是誰，查不到就明講查不到。*/
    parts: {
      wbg_sic_drift: {
        name: 'n⁻ 漂移層（磊晶長出來的）',
        desc: '這一層的厚度就是耐壓。寬能隙 → 崩潰電場高 → 承受同樣電壓需要的材料更薄 → 電阻低、損耗小、元件可以做小。它比底下的基板薄得多，因為它是長上去的，不是切出來的。',
        none: '★ 供應鏈資料（supply_chain.yaml）的半導體鏈 14 格裡沒有一格對應第三代半導體，所以這張圖不掛環節、點了不會篩。做這一段（磊晶）的台股是 3016 嘉晶（台灣少數能量產 SiC 與 GaN 磊晶者，信心：中，來源為投資研究平台整理）。',
      },
      wbg_sic_sub: {
        name: 'n⁺ SiC 基板',
        desc: '機械支撐＋導電。這一片的品質決定上面能不能長出好磊晶 —— 微管與基面差排這類缺陷在長晶那一步就決定了，後面救不回來。',
        none: '★ 長晶、切片、研磨拋光這三段，本圖**查不到台股的具名對應**（換了三組關鍵字只撈到「概念股清單」式的整理）。6488 環球晶有 SiC 基板業務，但它在 groups.yaml 掛的是「矽晶圓」族群、不在這一格，所以本圖不把它畫進來（R5：查不到就寫查不到，不編一個對應）。',
      },
      wbg_sic_gox: {
        name: '閘極氧化層 ＋ 閘極',
        desc: '氧化層夾在閘極與半導體之間，是全圖最薄的一層之一 —— 沒有這一層就不叫 MOSFET（閘極直接碰到半導體那是 JFET 或 HEMT）。它同時是 SiC 的長期可靠度課題之一。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。做元件製造（含閘極、通道、電極）的台股是 3707 漢磊（SiC／GaN 功率半導體晶圓代工，信心：中）。',
      },
      wbg_sic_jfet: {
        name: 'JFET 區（只有平面閘才有）',
        desc: '兩個 p-body 之間被夾成的一條窄路，是平面閘導通電阻的一部分。溝槽閘把閘極垂直挖進去就消掉它、單元節距可以更小 —— 代價是阻斷時溝槽處的電場集中，威脅閘極氧化層的長期可靠度。',
        none: '這是元件結構上的一塊區域，不是一個可以外購的零件。做這一段的是元件代工（見閘極那一條）。',
      },
      wbg_sic_trench: {
        name: '溝槽閘（Trench）',
        desc: '閘極真的挖進半導體裡的一條溝。消掉 JFET 區、通道遷移率較高、單元可以做更密；代價是溝槽底部的電場集中。這一格**不該有** JFET 區 —— 有就是把兩種結構混在一起了。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。台股在元件製造那一段是 3707 漢磊。',
      },
      wbg_sic_body: {
        name: 'p-body 與 n⁺ 源極區',
        desc: '通道就在 p-body 的表面。n⁺ 源極區一定被 p-body 包住，不能直接碰到 n⁻ 漂移層 —— 碰到就等於把元件短路掉了。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_sic_src: {
        name: '源極金屬（正面）',
        desc: '蓋住正面大部分，靠兩個接觸窗下去接到 n⁺ 源極與 p-body。它和閘極在同一面、和背面的汲極分屬兩側 —— 這就是「垂直元件」的定義。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_sic_drain: {
        name: '汲極金屬（背面）',
        desc: '在背面。電流從正面的源極穿過整片晶片到這裡 —— 三個電極畫在同一面就是 GaN HEMT，不是 SiC MOSFET。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_sic_i: {
        name: '電流路徑（垂直）',
        desc: '源極 → 通道 → JFET 區 → 漂移層 → 基板 → 背面汲極。方向是垂直的，耐壓靠的是漂移層的厚度。它跟 GaN 那支箭頭是同一個樣式、方向差 90 度 —— 那一組對比是這張圖最重要的視覺事實。',
        none: '這是一條示意的電流路徑，不是零件。',
      },
      // ---- GaN
      wbg_2deg: {
        name: '二維電子氣（2DEG）',
        desc: 'AlGaN 與 GaN 貼在一起，界面自己長出一層電子（極化誘發）。它在界面的 **GaN 那一側**，不是在 AlGaN 裡、也不是在兩層正中央。電子跑得快，所以切換可以到 MHz 級。',
        none: '★ 這一格在供應鏈資料裡沒有對應環節。長 GaN 疊層（磊晶）的台股是 3016 嘉晶。',
      },
      wbg_gan_buf: {
        name: '緩衝層（AlN／AlGaN）',
        desc: 'GaN 長在 Si 上晶格差得多（約 17%），要厚的 AlN／AlGaN 過渡；長在 SiC 上只差約 3.5%，可以薄很多。兩者畫成一樣厚就是把這件事抹掉了。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。台股在磊晶那一段是 3016 嘉晶。',
      },
      wbg_gan_ch: {
        name: 'GaN 通道層',
        desc: '2DEG 就長在它的上表面。它比上面的 AlGaN 阻障層厚。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_gan_bar: {
        name: 'AlGaN 阻障層',
        desc: '比底下的 GaN 通道層薄。它和 GaN 的界面就是 2DEG 的所在，三個電極都做在它的上表面。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_gan_sub: {
        name: 'GaN 的基板（Si 或 SiC）',
        desc: 'GaN 功率元件多半長在 Si 或 SiC 基板上。Si 便宜且相容既有 CMOS 廠，但晶格失配大、緩衝層要厚；SiC 導熱好、失配小，但貴。',
        none: '★ 這一格在供應鏈資料裡沒有對應環節，而且基板（長晶／切片／拋光）那三段本圖查不到台股的具名對應。',
      },
      wbg_gan_elec: {
        name: '源極／閘極／汲極（都在上表面）',
        desc: '三個電極全部做在同一個上表面、背面一個都沒有 —— 這就是「橫向元件」。也正因為是橫向，它受表面崩潰限制，主流停在 650V 級。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。做元件的台股是 3707 漢磊。',
      },
      wbg_pgan: {
        name: 'p-GaN 閘（常關做法之一）',
        desc: 'GaN 原生是「常開」的（零偏壓下 2DEG 就導通）。在 AlGaN 上長一層 p 型 GaN，內建電位把閘極底下的 2DEG 耗盡，零偏壓時就不導通了。p-GaN 一定在閘極金屬與 AlGaN 之間。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      wbg_cascode: {
        name: 'Cascode（常關做法之二）',
        desc: '一顆低壓常關的 Si MOSFET 串一顆常開的 GaN HEMT。**對外控制的是那顆 Si 的閘極**，GaN 的閘極接到 Si 的源極 —— 畫反就把整個電路講錯了。',
        none: '這是一種電路組態，不是單一零件；圖上只畫組態，不畫料號。',
      },
      wbg_gan_sic_sub: {
        name: '對照：GaN-on-SiC',
        desc: '同一套疊層長在 SiC 基板上：晶格只差約 3.5%，緩衝層可以薄很多，而且 SiC 的導熱比 Si 好。代價是基板貴。',
        none: '★ 這一格在供應鏈資料裡沒有對應環節；SiC 基板那一段本圖查不到台股的具名對應。',
      },
      wbg_gan_i: {
        name: '電流路徑（橫向）',
        desc: '源極 → 2DEG → 汲極，橫著在表面下跑。跟 SiC 那支箭頭同樣式、方向差 90 度 —— 一眼分辨兩種元件就靠這一組。',
        none: '這是一條示意的電流路徑，不是零件。',
      },
      // ---- 其餘
      wbg_band: {
        name: '電壓／頻率分工帶',
        desc: 'GaN 大致在 100V–650V 這一帶（1200V 已在送樣但仍屬特殊品）；SiC 大致在 650V–1700V 以上。三條帶**是重疊的**，650V 那一段兩者都在打 —— 畫成井水不犯河水就是錯的。',
        note: '⚠ 兩個來源給的邊界不是同一件事，而且邊界正在移動。所以圖上一律寫「大致在 …」，不寫硬邊界、不寫「一定要選 X」。',
        none: '這是一張分工帶狀圖，不是零件。',
      },
      wbg_boule: {
        name: '長晶 → 晶碇 → 切片',
        desc: 'PVT（物理氣相傳輸／昇華法）在高溫下讓原料昇華、在籽晶上重新凝結長成晶碇，再用多線鋸切片、研磨、化學機械拋光（CMP）到可以長磊晶的表面。微管與基面差排這類缺陷在長晶這一步就決定了。',
        none: '★ 長晶、切片、研磨拋光這三段，本圖**查不到台股的具名對應**。6488 環球晶有 SiC 基板業務但掛在「矽晶圓」族群，本圖不把它畫進來（R5）。',
      },
      wbg_flow: {
        name: '這條鏈的五段（第六段不在這張圖）',
        desc: '長晶 → 切片 → 研磨拋光 → 磊晶 → 元件製造，順序不准對調：磊晶是長在已經拋好的晶片表面上的。第六格（封裝模組）是灰的，因為那是另一張圖的主題。',
        none: '★ 台股目前指得出名字的是第 ④、⑤ 段：3016 嘉晶（磊晶）、3707 漢磊（元件代工），兩家同屬漢民集團（信心：中，來源為投資研究平台整理，不是公司自己的文件）。第 ①～③ 段查不到具名對應，第 ⑥ 段沒查。',
      },
    },
  });
})();
