/* 工業自動化：一個會動的軸拆開看 —— docs/diagram_plan_electronics.md 的 E1
   （族群 `factory_automation` 主掛、`machine_tool` 掛同一張，electronics 鏈）

   ---- 2026-09-23 v2（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
        並且需要適當的調整及填充版面間隔，不許有空白」）----
   原本是 980 寬、右邊一整格「這張圖要講的四件事」＋ 十幾行圖例與誠實性標示全部畫在 SVG 裡，
   而且靠 `badge()` 在畫布上寫編號、旁邊再排一行圖例文字 —— 欄寬一窄字就跟著縮小。
   改成跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套：
     · 畫布 980 → **660**（`native: 660`），svg 根掛 `.rs`；
     · 標題與導言 → `text.ext`（HTML 的 .dghead）；零件名、四件事與誠實性標示 → `extRow(side)`
       外掛卡片，畫布上只留編號圓點（引線由 externalize 依實際寬度重算）；
     · 因此 `badge()` 與它配套的那幾行圖例**退場**（編號圓點與名字改由卡片提供，
       一個字都沒少，只是從畫布搬到卡片）；
     · 四個區塊重排成三排：① 縱剖 ＋ 螺帽放大 ／ ② 橫剖 ｜ ③ 諧波 ｜ ④ RV ／ ⑤ 控制鏈（3＋2 折行）；
     · 材質走共用的 `D.fx`（`glass` 當機殼／底座／工作台、`beam` 當控制鏈主線、`glowDefs`）；
     · 顏色一律 `--dg-*` token（本來就沒有寫死色碼，改完再 grep 一次確認）；
     · **既有互動一個都沒動**：`data-part` 清單逐字不變（改前改後比對過），
       這張圖仍然一個 `data-seg` 都不掛（§0-D 第 2 點）。
   ⚠ 舊註解全部保留 —— M1／M3／M6／H1／R3／C1／X3 那幾條紅線還是合約。

   合約＝`docs/diagram_specs/motion_control.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事：

     · §0-A **不做真 3D**（`scene: null`）。五個資訊點裡沒有一個靠「轉一圈」才看得懂：
       鋼珠的回流通道只有剖面看得到、滑塊包住軌道在橫剖上一眼就懂、
       諧波三件是同心層序、RV 是左右兩段、控制鏈是一個流程環。
     · §0-B 交界：**不畫潔淨室與 FFU**（那是晶圓廠廠務那張）、
       **不畫馬達繞組剖面與矽鋼片**（那會跟變壓器 GIS 撞題）、
       **不剖開控制器與驅動器的電路板**（那是 PCB 與被動元件那兩張）。
     · §3-B M3／§6-S3（紅線）**一定要畫得出鋼珠的回流通道**。
       實作上靠 `ballLoop()` 這一支保證：鋼珠是沿著**一條閉合的迴圈**用同一個迴圈灑出來的，
       回流段跟受力段在同一輪產生 —— 漏不掉（畫在迴圈外就是 S3 不過）。
     · §3-C M6／§6-S5（紅線）滑塊是 **ㄇ 形、從上方罩下來包住軌道兩側**。
       `guideBlock()` 產生的是一條 ㄇ 字 path，量得出「左腳在軌道左邊、右腳在軌道右邊、
       腳的下緣低於軌道半高」。
     · §3-D M9／§6-H1（紅線）諧波由外到內是 **剛輪 → 柔輪 → 波產生器**。
       三件寫在同一個陣列裡、用 `forEach` 依序 append，順序改不壞。
     · §3-F M17／§6-C1（紅線）控制鏈**必須是閉的**：回授線真的畫出來、真的接回去，
       而且主鏈箭頭向右、回授箭頭向左。
     · §6-X3（紅線）**6603 富強鑫標的是「射出成型機」**，而且不在「加工機三軸」那一格。

   三個實作上的取捨，寫在這裡不要讓下一個人再想一次
   ---------------------------------------------------
   1. **螺帽另外畫一張放大圖**（§9 的提醒）。整支模組畫在 980 寬裡，螺帽只有 42px ——
      回流通道在 800px 下會被壓到看不見，而那是本圖的紅線。所以主圖畫「整支模組的順序」，
      右邊另開一格「螺帽剖開放大」畫溝槽、鋼珠與回流通道。**放大格與主圖不是同一個比例尺**，
      所以放大格自己標了一行說明，不跟 §6-S13 的同比例尺要求混在一起
      （S13 講的是縱剖與橫剖，那兩格才是同一個比例尺）。
   2. **「誰做的」收進第 ① 段章節列，主畫面只留一行結論。**
      規格書 §0-D 第 1 點原本要求「直接用引線標在零件旁」，理由是當時
      `renderPartCard()` 的第一行是「沒有環節就收起來」—— 沒有環節就完全沒有小卡。
      2026-09-22 之後 main 已經支援「沒有 data-seg 但有 parts 也能開小卡」，
      所以「誰做的」有兩條路可以走：點零件的小卡、以及第 ① 段那張逐件表。
      主畫面改留一行結論，是為了守住 **收合高度 ≤ 700**（Andy 2026-09-22：
      「大小問題導致整理版面塞太滿…希望能一次看到完整資訊」）。
      **收納 ≠ 刪除** —— §5 那張表一個字都沒少，只是分兩層。
   3. **零件一律不掛 `data-seg`**（§0-D 第 2 點）。`supply_chain.yaml` 的 electronics 鏈
      8 個環節裡沒有一格對得上工業自動化或工具機，這 19 檔用代號 grep 也一檔都不在裡面。
      硬掛 `passive_comp` 或 `metal_casing` 會讓小卡列出一群做 MLCC 或做機殼的公司 ——
      **那不是錯畫，那是錯講**。所以這張圖的高亮與小卡走的是「只有 data-part」那條路，
      畫面上也有一行明講「環節色標篩不到它們」。

   顏色一律走既有的 `--dg-*`（新增的五個材質 token 加在 index.html 的 :root，
   而且全部是既有 token 的 color-mix —— 四個配色一換它們自己跟著換）。
   JS 裡一個色碼都沒有。這個檔不碰 `site/diagrams.js`／`site/three3d.js`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function' || !D.fx) return;   // diagrams.js 沒載到就安靜退出
  const { extRow, note, fx } = D;

  /* 畫布寬：2026-09-23 從 980 收到 660。說明文字外掛成 HTML 卡片之後，SVG 只剩「畫」的部分。*/
  const CW = 660;

  /* ================================================================ 小工具 */
  const f1 = (v) => (+v).toFixed(1);
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const C = (cx, cy, r, fill, cls) =>
    `<circle${cls ? ` class="${cls}"` : ''} cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="${fill}"/>`;
  const EL = (cx, cy, rx, ry, fill, cls) =>
    `<ellipse${cls ? ` class="${cls}"` : ''} cx="${f1(cx)}" cy="${f1(cy)}" rx="${f1(rx)}" ry="${f1(ry)}" fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, cls, extra) =>
    `<path${cls ? ` class="${cls}"` : ''} d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${f1(x)}" y="${f1(y)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  /* 零件外框。★ 這張圖**一個 data-seg 都不掛**（§0-D 第 2 點），
     所以 `data-part` 一律要自己寫 —— `stampParts()` 只替掛了環節的節點蓋 dgkey。*/
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;

  /* ---- 2026-09-23 v2 新增（寫法照 `site/dg/liquid_cooling.js`）----
     card()：說明卡片離開 SVG 變成 HTML（externalize），畫布上只留編號圓點；
     卡片與它指的零件**共用同一個 data-part**（這張圖沒有 data-seg，所以只傳 part）。*/
  const card = (o) => {
    const s2 = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no, side: o.side,
      ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
    return o.color ? s2.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s2;
  };
  const wrapCJK = (s2, n) => { const out = []; for (let i = 0; i < s2.length; i += n) out.push(s2.slice(i, i + n)); return out.length ? out : ['']; };
  // 玻璃材質：跟 AI 伺服器那三張同一支 D.fx.glass（機殼、底座、工作台這種「大塊面」才用）
  const slab = (x, y, w, h, fill, o) => fx.glass(x, y, w, h,
    { fill, cls: 'part' + ((o && o.cls) ? ' ' + o.cls : ''), rx: (o && o.r) || 2, iso: o && o.iso });
  /* 元件色（卡片色條、編號圓點、引線端點共用）—— 一律 token、沒有寫死色碼。
     ⚠ 挑的是亮一階的那個：卡片標題印在元件色上要讀得到（liquid_cooling 的銅走過同一條）。*/
  const COL = {
    steel: 'var(--dg-steel)', ball: 'var(--dg-mc-ball)', alu: 'var(--dg-alu)',
    case: 'var(--dg-hub-lit)', flex: 'var(--dg-mc-flex)', cam: 'var(--dg-steel-2)',
    disc: 'var(--dg-mc-disc)', sig: 'var(--dg-accent-2d)', warn: 'var(--dg-warn)',
    oil: 'var(--dg-oil)',
  };

  /* 編號徽章 `badge()` —— **2026-09-23 退場**（Andy：Follow AI 伺服器那三張的風格）。
     原本它在畫布上畫一顆圓 ＋ 一個數字 ＋ 一條引線，名字另外排成一行圖例文字；
     現在編號圓點與名字都由 `extRow`／`card()` 的 HTML 卡片提供（圓點是 .anc，
     引線由 externalize 依實際寬度重算），畫面上的資訊一件都沒少，
     而且字不再跟著畫布縮小 —— 那正是 Andy 從 2026-09-15 講到現在的那件事。
     ⚠ 不要「順手加回來」：加回來就會變成同一個零件有兩顆編號圓點。*/

  /* ================================================================ 區 A ① 單軸模組・縱剖
     §3-A：由左到右 馬達（尾端編碼器）→ 聯軸器 → 軸承座 → 螺桿＋螺帽 → 軸承座。
     M1：馬達與螺桿之間**一定要有聯軸器**（同心度做不到，而且沒有可更換的犧牲件）。
     M2：編碼器在馬達的**尾端**（遠離螺桿那一側）。 */
  const SY = 128, RS = 9;                       // 螺桿軸心 y ／ 軸半徑（橫剖的斷面直徑要一致，S13）
  const SCX0 = 142, SCX1 = 368;                 // 螺桿軸兩端
  const NTX0 = 240, NTW = 42, RN = 20;          // 螺帽左緣／長度／外半徑（42 / 226 ≒ 1/6，S11）

  function axisLong() {
    const g = [];
    // 工作台：同時鎖在螺帽（這一格）與滑塊（橫剖那一格）上 —— S10 兩邊都要有連接線
    g.push(part('mc_table', slab(200, 88, 130, 12, 'var(--dg-alu)', { r: 2 })));
    g.push('<g class="mctiewrap">'
      + LN(`M250,100 L250,${SY - RN}`, 'var(--dg-steel-2)', 2.4, 'mctie')
      + LN(`M292,100 L292,${SY - RN}`, 'var(--dg-steel-2)', 2.4, 'mctie') + '</g>');
    // 編碼器（馬達尾端的小圓盤 ＋ 一條訊號線）
    g.push(part('mc_enc', R(26, SY - 12, 14, 24, 'var(--dg-mc-case)', 'part', 2)
      + C(33, SY, 6, 'var(--dg-el)', 'part')
      + LN(`M26,${SY - 8} L14,${SY - 8}`, 'var(--dg-accent-2d)', 1.4)));
    // 伺服馬達（外殼而已 —— §0-B 不准畫繞組剖面，那會跟重電那張撞題）
    g.push(part('mc_motor', slab(40, SY - 24, 48, 48, 'var(--dg-mc-case)', { r: 4 })
      + LN(`M48,${SY - 16} L48,${SY + 16}`, 'var(--dg-steel-2)', 1)
      + LN(`M80,${SY - 16} L80,${SY + 16}`, 'var(--dg-steel-2)', 1)));
    // 聯軸器（中間一段撓性溝 —— F6 的識別特徵）
    const cp = [];
    for (let i = 0; i < 4; i++) cp.push(LN(`M${99 + i * 4},${SY - 9} L${103 + i * 4},${SY + 9}`, 'var(--dg-steel-2)', 1.2));
    g.push(part('mc_coupling', R(92, SY - 10, 26, 20, 'var(--dg-steel)', 'part', 3) + cp.join('')));
    // 軸承座（固定端 ／ 支撐端，兩端各一 —— S12）
    const brg = (x) => R(x, SY - 16, 20, 32, 'var(--dg-mc-case)', 'part', 3)
      + C(x + 10, SY, 6, 'var(--dg-steel-2)', 'part');
    g.push(part('mc_bearing', brg(122) + brg(348)));
    // 螺桿軸：全圖最長的零件（S11）
    g.push(part('mc_screw', R(SCX0, SY - RS, SCX1 - SCX0, RS * 2, 'var(--dg-steel)', 'part', 1)
      + grooveRow(SCX0 + 8, SCX1 - 8, SY - RS, 3, false)
      + grooveRow(SCX0 + 8, SCX1 - 8, SY + RS, 3, true)));
    // 螺帽（外側有法蘭；裡面的鋼珠與回流通道畫在右邊的放大格）
    g.push(part('mc_nut', R(NTX0, SY - RN, NTW, RN * 2, 'var(--dg-mc-case)', 'part', 3)
      + R(NTX0 - 4, SY - RN - 4, 6, RN * 2 + 8, 'var(--dg-steel-2)', 'part', 2)));
    return g.join('');
  }

  /* 螺桿與螺帽的溝槽：一排**圓弧**凹槽（§3-B M4 —— 畫成 V 形三角就是畫成了一般螺絲）。
     `up` ＝凹槽往上挖（螺桿下表面／螺帽內壁）。畫的是圓弧指令，所以測試量得到「這是弧不是折線」。*/
  function grooveRow(x0, x1, y, r, up, cls) {
    const out = [], n = Math.max(3, Math.floor((x1 - x0) / (r * 3.4)));
    for (let i = 0; i < n; i++) {
      const cx = x0 + (i + 0.5) * ((x1 - x0) / n);
      out.push(PA(`M${f1(cx - r)},${f1(y)} A${r},${r} 0 0 ${up ? 1 : 0} ${f1(cx + r)},${f1(y)} Z`,
        'var(--dg-void)', cls || 'mcgs'));
    }
    return out.join('');
  }

  /* ================================================================ 螺帽剖開放大（§9 的提醒）
     這一格是這張圖的紅線所在：**鋼珠的回流通道**（S3）。
     鋼珠沿著一條**閉合的迴圈**灑：受力段（在溝槽裡）→ 進入循環器 → 回到另一端。
     回流段跟受力段在同一個迴圈裡產生，所以漏不掉。 */
  /* ⚠ 2026-09-23：放大格從 96 寬拉到 184 寬（ZBX1 500 → 588）——
     畫布收到 660 之後第 1 排右半原本會空掉一塊，而這一格正是本圖的紅線（回流通道）。
     鋼珠顆數 N、迴圈的拓樸一個都沒改，只是同一條閉合迴圈被拉長。*/
  const ZY_S = 152, ZY_NI = 146, ZBX0 = 404, ZBX1 = 588, ZRY = 124, ZRB = 7;

  function ballLoop() {
    // 閉合迴圈：受力段（左→右）→ 上升 → 回流段（右→左）→ 下降。y 小的那一段就是回流。
    const pts = [[ZBX0, 149], [ZBX1, 149], [ZBX1 + 10, ZRY], [ZBX0 - 10, ZRY]];
    const seg = [], n = pts.length;
    let per = 0;
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      seg.push({ a: a, b: b, L: L }); per += L;
    }
    const N = 16, out = [];
    for (let i = 0; i < N; i++) {
      let s = (i + 0.5) * (per / N);
      for (let k = 0; k < seg.length; k++) {
        if (s <= seg[k].L) {
          const t = s / seg[k].L;
          out.push([seg[k].a[0] + (seg[k].b[0] - seg[k].a[0]) * t,
            seg[k].a[1] + (seg[k].b[1] - seg[k].a[1]) * t]);
          break;
        }
        s -= seg[k].L;
      }
    }
    return { pts: pts, balls: out };
  }

  function nutZoom() {
    const lp = ballLoop(), g = [];
    const d = `M${lp.pts[0][0]},${lp.pts[0][1]} L${lp.pts[1][0]},${lp.pts[1][1]} `
      + `L${lp.pts[2][0]},${lp.pts[2][1]} L${lp.pts[3][0]},${lp.pts[3][1]} Z`;
    // 螺帽本體（剖開）：外壁 ＋ 內壁；內壁上有對應的圓弧溝槽
    g.push(part('mc_nut', slab(388, 112, 216, 34, 'var(--dg-mc-case)', { r: 3 })
      + R(388, ZY_NI - 2, 216, 4, 'var(--dg-steel-2)', 'part')));
    // 螺桿（放大）：上表面 ＋ 圓弧溝槽
    g.push(part('mc_screw', slab(388, ZY_S, 216, 20, 'var(--dg-steel)', { r: 1 })
      + grooveRow(396, 596, ZY_S, 4, false, 'mcgs')));
    // 螺帽內壁的溝槽（往上挖）
    g.push(part('mc_nut', grooveRow(396, 596, ZY_NI, 4, true, 'mcgn')));
    // ★ 循環器（回流通道）—— 沒有這一條，這支就是鎖緊用的梯形螺桿，不是傳動用的滾珠螺桿
    g.push(part('mc_return', LN(d, 'var(--dg-void)', 18, 'mcret', ' stroke-linejoin="round"')
      + LN(d, 'var(--dg-accent-2d)', 1.2, 'mcretln', ' stroke-dasharray="4 4" stroke-linejoin="round"')));
    // 鋼珠：同一個迴圈灑出來，受力段與回流段都有
    g.push(part('mc_ball', lp.balls.map((p) =>
      C(p[0], p[1], ZRB, 'var(--dg-mc-ball)', 'part mcball')).join('')));
    /* ⚠ 整格包一層 `.mczoom` —— 主圖的螺桿也有 `.mcgs`（溝槽），
       驗收要量「鋼珠同時碰到兩邊的溝」時得分得出哪一組是放大格的。*/
    return `<g class="mczoom">${g.join('')}</g>`;
  }

  /* ================================================================ 區 A ② 單軸模組・橫剖
     §3-C：底座 → 軌道（凸出來）→ 鋼珠（在兩側的圓弧溝裡）→ 滑塊（ㄇ 形罩下來）→ 工作台。
     M6（紅線）：滑塊**必須包住軌道兩側**。放在軌道上面的方塊吃不了側向力與拉拔力。
     M7：兩條平行軌，**螺桿在兩軌之間**（推力不在形心上，工作台會被扭起來）。*/
  /* ⚠ 底座下緣停在 344 —— 底下 358／374／390 是三行標註。
     排版體檢只比「字跟字」有沒有重疊，**字壓在零件上它抓不到**，所以這裡自己算清楚。 */
  const BK_Y0 = 280, BK_Y1 = 316, RL_Y0 = 294, RL_Y1 = 316, BASE_Y = 316;

  // ㄇ 字形滑塊：頂蓋 ＋ 兩支往下包住軌道兩側的腳
  function guideBlock(x0, x1, ix0, ix1) {
    return PA(`M${x0},${BK_Y0} H${x1} V${BK_Y1} H${ix1} V${BK_Y0 + 12} H${ix0} V${BK_Y1} H${x0} Z`,
      'var(--dg-mc-case)', 'part mcblock');
  }

  function axisCross() {
    const g = [];
    // 工作台（鎖在兩個滑塊上 —— S10 的另一半）
    g.push(part('mc_table', slab(48, 262, 236, 12, 'var(--dg-alu)', { r: 2 })));
    g.push('<g class="mctiewrap">'
      + LN(`M86,274 L86,${BK_Y0}`, 'var(--dg-steel-2)', 2.4, 'mctie')
      + LN(`M246,274 L246,${BK_Y0}`, 'var(--dg-steel-2)', 2.4, 'mctie') + '</g>');
    // 底座（鋁擠型，斷面有空腔）
    g.push(part('mc_base', slab(40, BASE_Y, 252, 28, 'var(--dg-alu-2)', { r: 3 })
      + R(56, BASE_Y + 7, 60, 14, 'var(--dg-void)', 'part', 2)
      + R(136, BASE_Y + 7, 60, 14, 'var(--dg-void)', 'part', 2)
      + R(216, BASE_Y + 7, 60, 14, 'var(--dg-void)', 'part', 2)));
    // 軌道 ×2（凸出來，兩側有圓弧溝）
    const rail = (x0) => R(x0, RL_Y0, 36, RL_Y1 - RL_Y0, 'var(--dg-steel)', 'part mcrail', 2);
    g.push(part('mc_rail', rail(68) + rail(228)));
    // 滑塊 ×2（ㄇ 形）
    g.push(part('mc_block', guideBlock(56, 116, 66, 106) + guideBlock(216, 276, 226, 266)));
    // 滾珠：在軌道溝與滑塊溝之間（兩側都有 —— M8）
    const rb = [];
    [68, 104, 228, 264].forEach((cx) => {
      [300, 310].forEach((cy) => { rb.push(C(cx, cy, 3.6, 'var(--dg-mc-ball)', 'part mcrball')); });
    });
    g.push(part('mc_railball', rb.join('')));
    // 螺桿斷面：★ 在兩條軌道之間，直徑與縱剖一致（S13）
    g.push(part('mc_screw', C(166, 305, RS, 'var(--dg-steel)', 'part mcscrewx')
      + C(166, 305, RS - 3.5, 'var(--dg-void)', 'part')));
    return g.join('');
  }

  /* ================================================================ 區 B ① 諧波減速機
     §3-D（H1，紅線）由外到內：剛輪 → 柔輪 → 波產生器。三件寫在同一個陣列、依序 append。
     H2：柔輪是**橢圓**（rx 與 ry 差 25%，遠大於 8% 的下限）。
     H4：輸出從**柔輪**的杯底法蘭出去 —— 輸出件畫在 mc_fs 這個群組裡，不在 mc_cs 裡。 */
  const HX = 386, HY = 310, H_CS = 32, H_CSI = 26;
  const H_FS_RX = 25, H_FS_RY = 20, H_FSI_RX = 22, H_FSI_RY = 17;
  const H_TEETH_CS = 14, H_TEETH_FS = 12;

  function ringTeeth(cx, cy, r, n, inward, cls) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = i * Math.PI * 2 / n, w = Math.PI / n * 0.5, k = inward ? -1 : 1;
      const p = (rr, aa) => `${f1(cx + rr * Math.cos(aa))},${f1(cy + rr * Math.sin(aa))}`;
      out.push(PA(`M${p(r, a - w)} L${p(r + k * 2.6, a - w * 0.5)} L${p(r + k * 2.6, a + w * 0.5)} L${p(r, a + w)} Z`,
        'var(--dg-steel-2)', cls));
    }
    return out.join('');
  }

  function ellipseTeeth(cx, cy, rx, ry, n, cls) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = i * Math.PI * 2 / n, w = Math.PI / n * 0.5;
      const p = (k, aa) => `${f1(cx + (rx + k) * Math.cos(aa))},${f1(cy + (ry + k) * Math.sin(aa))}`;
      out.push(PA(`M${p(0, a - w)} L${p(2.4, a - w * 0.5)} L${p(2.4, a + w * 0.5)} L${p(0, a + w)} Z`,
        'var(--dg-steel-2)', cls));
    }
    return out.join('');
  }

  function harmonic() {
    const g = [];
    /* ★ 順序寫在陣列裡、用 forEach 依序畫 —— H1 因此自動成立，也改不壞。*/
    const layers = [
      () => part('mc_cs', PA(`M${HX - H_CS},${HY} a${H_CS},${H_CS} 0 1 0 ${H_CS * 2},0 a${H_CS},${H_CS} 0 1 0 ${-H_CS * 2},0 Z`
        + `M${HX - H_CSI},${HY} a${H_CSI},${H_CSI} 0 1 1 ${H_CSI * 2},0 a${H_CSI},${H_CSI} 0 1 1 ${-H_CSI * 2},0 Z`,
      'var(--dg-mc-case)', 'part mccs')
        + ringTeeth(HX, HY, H_CSI, H_TEETH_CS, true, 'mccst')),
      () => part('mc_fs', EL(HX, HY, H_FS_RX, H_FS_RY, 'var(--dg-mc-flex)', 'part mcfs')
        + EL(HX, HY, H_FSI_RX, H_FSI_RY, 'var(--dg-void)', 'part mcfsi')
        + ellipseTeeth(HX, HY, H_FS_RX, H_FS_RY, H_TEETH_FS, 'mcfst')
        // 輸出法蘭（杯底）：★ 畫在柔輪這個群組裡 —— 輸出是從柔輪出去，不是從剛輪出去
        + R(HX + H_CS + 4, HY - 9, 18, 18, 'var(--dg-alu)', 'part mcfsout', 2)
        + LN(`M${HX + H_FS_RX},${HY} L${HX + H_CS + 4},${HY}`, 'var(--dg-mc-flex)', 2.4)),
      () => part('mc_wg', EL(HX, HY, 19, 14, 'var(--dg-mc-cam)', 'part mcwg')
        + EL(HX, HY, 21, 16, 'none', 'mcwgb')),
    ];
    layers.forEach((fn) => g.push(fn()));
    return g.join('');
  }

  /* ================================================================ 區 B ② RV 減速機
     §3-E（R1／R2）**兩級**：行星級（靠馬達端，左）→ 曲柄軸 → 擺線級（靠輸出端，右）。
     R3：擺線盤 **2 片**、相位差 180°，外緣是**連續波浪**咬在一圈**圓柱針銷**上。
     ★ 針銷數 ＝ 波浪數 ＋ 1（這是擺線機構本來的關係，所以測試直接量這一條）。
     R4：兩格同一個比例尺，而且 **RV 外徑（41）明顯大於諧波外徑（32）**。 */
  const PX = 700, PY = 306, P_RING = 22;
  const VX = 812, VY = 306, V_HOUSE = 41, V_PIN_R = 34, V_LOBES = 15, V_RB = 28, V_AMP = 4;

  function cycloPath(cx, cy, rb, amp, lobes, phase) {
    const pts = [];
    for (let i = 0; i <= 240; i++) {
      const t = i / 240 * Math.PI * 2, r = rb + amp * Math.cos(lobes * t + phase);
      pts.push(`${f1(cx + r * Math.cos(t))},${f1(cy + r * Math.sin(t))}`);
    }
    return 'M' + pts.join('L') + 'Z';
  }

  function rvReducer() {
    const g = [];
    // 前級：行星齒輪組（★ 一定在靠馬達那一端 —— 本圖的馬達在左邊）
    const pl = [];
    for (let i = 0; i < 3; i++) {
      const a = i * Math.PI * 2 / 3 - Math.PI / 2;
      pl.push(C(PX + 11 * Math.cos(a), PY + 11 * Math.sin(a), 7, 'var(--dg-steel)', 'part mcpgear'));
    }
    g.push(part('mc_planet', PA(`M${PX - P_RING},${PY} a${P_RING},${P_RING} 0 1 0 ${P_RING * 2},0 a${P_RING},${P_RING} 0 1 0 ${-P_RING * 2},0 Z`
      + `M${PX - 18},${PY} a18,18 0 1 1 36,0 a18,18 0 1 1 -36,0 Z`, 'var(--dg-mc-case)', 'part mcplanet')
      + pl.join('') + C(PX, PY, 4.5, 'var(--dg-steel-2)', 'part')));
    // 曲柄軸（偏心）：把前級的轉動變成偏心運動
    g.push(part('mc_crank', LN(`M${PX + P_RING},${PY} L${VX - V_HOUSE},${PY}`, 'var(--dg-steel)', 3.2, 'mccrank')
      + C((PX + P_RING + VX - V_HOUSE) / 2, PY - 5, 4.5, 'var(--dg-mc-cam)', 'part')));
    // 輸出法蘭／殼體（最外）
    g.push(part('mc_rv', PA(`M${VX - V_HOUSE},${VY} a${V_HOUSE},${V_HOUSE} 0 1 0 ${V_HOUSE * 2},0 a${V_HOUSE},${V_HOUSE} 0 1 0 ${-V_HOUSE * 2},0 Z`
      + `M${VX - 38},${VY} a38,38 0 1 1 76,0 a38,38 0 1 1 -76,0 Z`, 'var(--dg-mc-case)', 'part mcrvhouse')));
    // 擺線盤 ×2：相位差 180°（偏心方向相反 ＋ 波浪錯開半個齒）
    g.push(part('mc_cyclo',
      PA(cycloPath(VX + 5, VY, V_RB, V_AMP, V_LOBES, Math.PI), 'var(--dg-steel-2)', 'part mccyclo')
      + PA(cycloPath(VX - 5, VY, V_RB, V_AMP, V_LOBES, 0), 'var(--dg-mc-disc)', 'part mccyclo')));
    // 針齒（針銷）環：一圈圓柱，數量 ＝ 波浪數 ＋ 1
    const pins = [];
    for (let i = 0; i < V_LOBES + 1; i++) {
      const a = i * Math.PI * 2 / (V_LOBES + 1);
      pins.push(C(VX + V_PIN_R * Math.cos(a), VY + V_PIN_R * Math.sin(a), 4, 'var(--dg-mc-ball)', 'part mcpin'));
    }
    g.push(part('mc_pin', pins.join('')));
    return g.join('');
  }

  /* ================================================================ 區 C 控制鏈（閉合的環）
     §3-F（C1，紅線）：主鏈 控制器 → 驅動器 → 馬達 → 減速機／螺桿 → 負載；
     回授 編碼器（在馬達上）→ 驅動器 → 控制器。**只畫單向五格＝畫成了開迴路，那不是伺服。**
     C3：主鏈箭頭一律向右、回授箭頭一律向左。 */
  const CC = [
    { id: 'mc_ctrl', t: '控制器', s: '算出下一毫秒走到哪' },
    { id: 'mc_drive', t: '伺服驅動器', s: '把命令變成電流' },
    { id: 'mc_motor', t: '伺服馬達＋編碼器', s: '轉，並回報轉到哪' },
    { id: 'mc_trans', t: '減速機／滾珠螺桿', s: '放大扭矩／轉變成直線' },
    { id: 'mc_load', t: '負載（工作台、手臂）', s: '真的動了' },
  ];
  /* ★ 框高 32、標題基線 y+13、副標基線 y+28 ＝ 行距 15px。
     這是 `diagrams.js` 的 processBar B3 踩過的同一個病：`.sub` 升到 12px 之後，
     13px 的行距配 12px 的中文字會讓標題與副標的 bbox 互相重疊 1px。 */
  /* ★ 框高 34、標題基線 y+14、副標基線 y+30 ＝ 行距 16px。
     這是 `diagrams.js` 的 processBar B3 踩過的同一個病：`.sub` 升到 12px 之後，
     13px 的行距配 12px 的中文字會讓標題與副標的 bbox 互相重疊 1px。
     ⚠ 2026-09-23：畫布收到 660，五格一列放不下（5×182−22 ＝ 888），改成 **3 ＋ 2 兩列**
       （跟 `diagrams.js` 的 processBar 在窄畫布上的做法同一套）。
       主鏈箭頭一律向右、換列時走一條往下折的連接線；C1／C3 兩條紅線因此仍然成立。*/
  const CBX = 32, CBW = 190, CBG = 14, CBY = 436, CBH = 34, CBCOLS = 3, CBROW = 60;

  function ctrlLoop() {
    const g = [];
    const pos = CC.map((c, i) => ({ x: CBX + (i % CBCOLS) * (CBW + CBG), y: CBY + Math.floor(i / CBCOLS) * CBROW }));
    CC.forEach((c, i) => {
      const { x, y } = pos[i];
      g.push(part(c.id, R(x, y, CBW, CBH, 'var(--dg-step-f)', 'part mccell', 7)
        + `<g pointer-events="none">${T(x + 9, y + 14, c.t, 'lbl')}${T(x + 9, y + 30, c.s, 'sub')}</g>`));
      if (i < CC.length - 1) {
        const n = pos[i + 1], ay = y + CBH / 2;
        if (n.y === y) {
          // 同一列：直接往右
          g.push(LN(`M${x + CBW + 2},${ay} L${n.x - 6},${ay}`, 'var(--dg-accent-2d)', 2, 'mcarr')
            + PA(`M${n.x - 1},${ay} L${n.x - 8},${ay - 4} L${n.x - 8},${ay + 4} Z`, 'var(--dg-accent-2d)', 'mcarrh'));
        } else {
          // 換列：往右一小段 → 往下 → 往左走到下一列的起點 → 進格子（箭頭仍然向右）
          /* ⚠ 換列的連接線走 y+CBH+18，**不是** y+CBH+8 —— 後者是回授線那一條的高度，
             兩條疊在一起會看起來像畫錯（主鏈與回授必須分得開，C3）。*/
          const my = y + CBH + 18;
          g.push(LN(`M${x + CBW + 2},${ay} h6 V${my} H${n.x - 14} V${n.y + CBH / 2} h6`, 'var(--dg-accent-2d)', 2, 'mcarr')
            + PA(`M${n.x - 1},${n.y + CBH / 2} L${n.x - 8},${n.y + CBH / 2 - 4} L${n.x - 8},${n.y + CBH / 2 + 4} Z`, 'var(--dg-accent-2d)', 'mcarrh'));
        }
      }
    });
    /* ★ 回授：起點在馬達（第 3 格，第一列最右）的編碼器，往左接回驅動器與控制器。
       這個環必須是閉的 —— 只畫單向五格＝畫成了開迴路，那不是伺服。
       兩列版的回授線走在**第一列底下 8px** 的那條空隙，不會壓到第二列（第二列從 CBY+48 起）。*/
    const fy = CBY + CBH + 8;
    const mx = pos[2].x + CBW / 2, dx = pos[1].x + CBW / 2, cx = pos[0].x + CBW / 2;
    g.push(part('mc_fb',
      LN(`M${mx},${CBY + CBH} L${mx},${fy} L${cx},${fy} L${cx},${CBY + CBH + 2}`, 'var(--dg-warn)', 2, 'mcfb')
      + LN(`M${dx},${fy} L${dx},${CBY + CBH + 2}`, 'var(--dg-warn)', 1.6, 'mcfbtap')
      + PA(`M${cx},${CBY + CBH + 1} L${cx - 4},${CBY + CBH + 8} L${cx + 4},${CBY + CBH + 8} Z`, 'var(--dg-warn)', 'mcfbarr')
      + PA(`M${cx + 60},${fy} L${cx + 68},${fy - 4} L${cx + 68},${fy + 4} Z`, 'var(--dg-warn)', 'mcfbarr')));
    return g.join('');
  }

  /* ================================================================ 第 ① 段：誰做的 ＋ 裝到哪裡去
     ★ 公司角色的字一律抄 `docs/groups_tide110_evidence.md` 的「歸類理由」欄，
       但**拿掉該表裡的法人用語**（§6-X5 是紅線，證據表本身沒有這條限制）。
     ★ X3（紅線）：6603 富強鑫標的是「射出成型機」，而且**不在「加工機三軸」那一格**。 */
  const WHO = [
    ['滾珠螺桿（螺桿＋螺帽＋鋼珠＋循環器）', '2049 上銀（滾珠螺桿與線性滑軌）、4540 全球傳動（線性傳動）'],
    ['線性滑軌（軌道＋滑塊）', '2049 上銀（滾珠螺桿與線性滑軌）、1597 直得（線性滑軌）'],
    ['伺服馬達／編碼器', '4576 大銀微系統（線性馬達與傳動）。本圖畫的是旋轉馬達＋螺桿，直接驅動的線性馬達架構未畫'],
    ['減速機（諧波與 RV 兩格共用）', '4583 台灣精銳（減速機）。★ 查不到它做的是諧波還是 RV，所以不指定其中一格'],
    ['控制器', '7750 新代（CNC 控制器）'],
    ['聯軸器、軸承座、鋼珠、工作台、底座', '本圖查不到台股的具名對應 —— 查不到就寫查不到，不編一個對應'],
  ];
  const MACH = [
    ['加工機三軸（X／Y／Z）', '4526 東台（綜合加工機）、1583 程泰（車床與加工中心機）、1528 恩德（專用工具機）'],
    ['協作型機器人（手腕與小負載關節走諧波）', '4585 達明（協作型機器人）'],
    ['半導體廠 AMHS 天車與智慧物流', '2464 盟立（半導體廠 AMHS 與智慧物流系統整合）。★ 天車外觀查不到，本圖不畫'],
    ['射出成型機', '★ 6603 富強鑫（射出成型機）—— 它在「CNC 工具機」族群裡，但做的不是切削工具機，所以不在上面那一格'],
  ];

  /* ⚠ 2026-09-23：兩個章節收到 660 寬。長句一個字都沒刪，改成 `wrapCJK` 自動斷行、
     每一列一個粗體標題 ＋ N 行說明（列寬 628 ＝ 畫布 660 減左右各 16）。*/
  const FW = 628, LH = 17;
  function txtRow(id, y, title, body, warn) {
    const lines = wrapCJK(body, 44);
    const h = 18 + lines.length * LH;
    const inner = [T(24, y + 13, title, 'lbl', null, warn ? 'fill:var(--dg-warn)' : '')]
      .concat(lines.map((t, i) => T(24, y + 13 + LH * (i + 1), t, 'sub')));
    return { svg: part(id, R(16, y, FW, h, 'transparent', 'part')
      + `<g pointer-events="none">${inner.join('')}</g>`), h: h + 4 };
  }
  function txtPara(y, body, warn) {
    const lines = wrapCJK(body, 46);
    return { svg: lines.map((t, i) => T(24, y + 13 + LH * i, t, 'sub', null,
      warn ? 'fill:var(--dg-warn)' : '')).join(''), h: 13 + lines.length * LH };
  }

  function foldWho(y0) {
    const g = [];
    let y = y0 + 8;
    g.push(T(24, y + 14, '這張圖上每一個零件，台股是誰做的', 'hd'));
    g.push(T(24, y + 31, '公司角色取自板塊成分股證據表；一個規格數字都不寫', 'sub'));
    y += 40;
    WHO.forEach((r, i) => { const b2 = txtRow('mc_who' + i, y, r[0], r[1]); g.push(b2.svg); y += b2.h; });
    y += 10;
    g.push(T(24, y + 14, '這些傳動件最後裝到哪裡去（4 種機器）', 'hd'));
    y += 24;
    const ids = ['mc_machine', 'mc_robot', 'mc_amhs', 'mc_inject'];
    MACH.forEach((r, i) => { const b2 = txtRow(ids[i], y, r[0], r[1], i === 3); g.push(b2.svg); y += b2.h; });
    y += 8;
    [['★ 2359 所羅門（AI 3D 視覺與機器人整合）沒有畫在控制鏈上 —— 視覺是另一個迴路（感測→辨識→路徑），塞進來會讓這張圖變成兩個環。', 1],
      ['★ 3162 精確（精密加工件）與 8027 鈦昇（自動化與雷射設備）查不到具體做的是哪一種零件與雷射用途，所以只列名、不指到主圖任何一格。', 1],
      ['6215 和椿（自動化設備與系統）、3167 大量（自動化設備）、6739 竹陞科技（半導體自動化軟體與設備）同理，屬於系統整合那一類，不對應本圖的單一零件。', 0],
    ].forEach(([t, w]) => { const r = txtPara(y, t, w); g.push(r.svg); y += r.h + 4; });
    return { svg: g.join(''), h: y - y0 + 10 };
  }

  /* 第 ② 段：氣動那一路（三個零件，跟上面的伺服電動路徑是兩條不同的路） */
  function foldAir(y0) {
    const g = [];
    let y = y0 + 8;
    g.push(T(24, y + 14, '氣動那一路：走的是壓縮空氣，不是伺服馬達', 'hd'));
    g.push(T(24, y + 32, '三點組（過濾＋調壓＋給油）→ 電磁閥（決定氣往哪一腔走）→ 氣缸（活塞被推出去）。', 'sub'));
    g.push(T(24, y + 49, '沒有編碼器回授，所以停不到任意位置 —— 這就是它跟伺服電動軸的分界。', 'sub'));
    const AY = y + 66;
    // 三點組
    g.push(part('mc_air_frl', slab(28, AY, 120, 44, 'var(--dg-mc-case)', { r: 4 })
      + C(54, AY + 22, 9, 'var(--dg-steel)', 'part') + C(86, AY + 22, 9, 'var(--dg-steel)', 'part')
      + C(118, AY + 22, 9, 'var(--dg-oil)', 'part')
      + `<g pointer-events="none">${T(28, AY + 60, '三點組：過濾／調壓／給油', 'sub')}</g>`));
    g.push(LN(`M154,${AY + 22} L184,${AY + 22}`, 'var(--dg-accent-2d)', 2, 'mcairarr')
      + PA(`M190,${AY + 22} L182,${AY + 18} L182,${AY + 26} Z`, 'var(--dg-accent-2d)'));
    // 電磁閥
    g.push(part('mc_air_valve', slab(194, AY, 110, 44, 'var(--dg-mc-case)', { r: 4 })
      + R(206, AY + 10, 40, 24, 'var(--dg-steel)', 'part', 2) + R(252, AY + 10, 40, 24, 'var(--dg-steel-2)', 'part', 2)
      + LN(`M210,${AY + 22} L242,${AY + 22}`, 'var(--dg-accent-2d)', 1.4)
      + LN(`M256,${AY + 14} L288,${AY + 30}`, 'var(--dg-accent-2d)', 1.4)
      + `<g pointer-events="none">${T(194, AY + 60, '電磁閥：切換氣要進哪一腔', 'sub')}</g>`));
    g.push(LN(`M310,${AY + 22} L340,${AY + 22}`, 'var(--dg-accent-2d)', 2, 'mcairarr')
      + PA(`M346,${AY + 22} L338,${AY + 18} L338,${AY + 26} Z`, 'var(--dg-accent-2d)'));
    // 氣缸
    g.push(part('mc_air_cyl', slab(350, AY + 4, 280, 36, 'var(--dg-mc-case)', { r: 4 })
      + R(356, AY + 10, 268, 24, 'var(--dg-void)', 'part', 2)
      + R(444, AY + 8, 16, 28, 'var(--dg-steel)', 'part', 2)
      + R(460, AY + 18, 164, 8, 'var(--dg-steel-2)', 'part', 2)
      + `<g pointer-events="none">${T(350, AY + 60, '氣缸：活塞被壓縮空氣推出去', 'sub')}</g>`));
    let yb = AY + 72;
    const one = txtRow('mc_air', yb, '台股：1590 亞德客-KY（氣動元件）',
      '★ 沒有畫在主圖上：它跟伺服電動軸是兩條並行的路。本圖不寫任何氣壓、缸徑與行程數字（查不到共通值）。');
    g.push(one.svg); yb += one.h;
    return { svg: g.join(''), h: yb - y0 + 10 };
  }

  /* ================================================================ 版面
     ---- 2026-09-23 v2（Andy：Follow AI 伺服器那三張、版面不許有空白）----
     畫布 660、三排：
       第 1 排　① 單軸模組縱剖（左）＋ 螺帽剖開放大（右，拉寬到 184 把整排填滿）
       第 2 排　② 同一支模組橫剖（左）｜ ③ 諧波 ｜ ④ RV（右，同一個比例尺，中間一條分隔線）
       第 3 排　⑤ 控制鏈（3 ＋ 2 兩列，主鏈向右、回授向左，環是閉的）
     零件名、四件事與誠實性標示全部外掛成 HTML 卡片（左右兩欄）；畫布上只剩編號圓點，
     所以舊版的 `badge()` 與它配套的圖例行退場 —— 一個字都沒少，只是換位置。
     viewBox 寫的是「全部展開」的高度；收合是 `wireFolds()` 在執行期改的，
     所以 JS 沒跑到的路徑（縮圖）吃到的仍然是一份座標正確的完整版面。
     ⚠ 章節列刻意不掛 data-seg（掛了按一下展開就把成分股篩掉了）。
     收合時：HTML 標題列 ＋ 三排圖（16～564）＋ 兩條章節列 ＝ 約 660px（上限 700）。*/
  function motionControl() {
    const S1 = 578;
    const w1 = foldWho(S1 + 46);
    const S2 = S1 + 46 + w1.h;
    const w2 = foldAir(S2 + 46);
    const H = S2 + 46 + w2.h + 16;
    return `<svg class="dg dgm rs dgmc" viewBox="0 0 ${CW} ${H}" width="100%" style="display:block">${D.STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）——
           在 SVG 裡它是被當標記解析的，寫一個像標籤的東西進去會把整張樣式表吃掉。
           這張圖一個環節屬性都沒有（§0-D），所以 diagrams.js 那一整組依環節屬性寫的規則
           一條都吃不到：描邊、游標、被點到的高亮全部要在這裡自己給。
           顏色一律走 --dg-*，這裡沒有寫死色票。
           2026-09-23：幾塊大面改用 D.fx.glass 之後自己有細邊（.fxe），所以平時不描邊，
           滑過去 1.4px、被點的那一個 2.4px —— 跟 panel／psu 那幾張同一階（不要「螢光感太重」）。*/
        svg.dgmc [data-part]{cursor:pointer}
        svg.dgmc [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;
          transition:stroke .15s,filter .15s}
        svg.dgmc [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgmc [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.6;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgmc .mcbg{stroke:var(--dg-frame-s);stroke-width:1}
        svg.dgmc .mcwgb{stroke:var(--dg-steel);stroke-width:2.4;fill:none}
      </style>
      <!-- 標題與導言：v2 搬到 HTML 的 .dghead，SVG 裡不畫（字才不會跟著畫布縮小） -->
      <text class="ttl ext" x="0" y="0">工業自動化：一個會動的軸拆開看</text>
      <text class="cap ext" x="0" y="0">一次直線移動、一次關節轉動，各自靠哪幾個零件。上排是一支單軸線性模組的縱剖與螺帽剖開放大，中排是同一支模組的橫剖與兩種減速機（同一個比例尺），下排是控制鏈。左右兩欄的卡片逐件說明，點卡片零件會亮、點零件卡片會亮；下面兩段預設收起來，按標題列就打得開。</text>

      <!-- ================= 第 1 排：① 縱剖 ＋ 螺帽剖開放大 ================= -->
      ${frame(16, 16, 628, 176)}
      ${T(28, 40, '① 單軸線性模組・縱剖：馬達 → 聯軸器 → 軸承座 → 螺桿＋螺帽 → 軸承座', 'hd')}
      ${T(28, 58, '溝槽剖面是圓弧、不是 V 形；沒有回流通道就不是滾珠螺桿', 'sub', null, 'fill:var(--dg-warn)')}
      ${axisLong()}
      ${T(388, 92, '螺帽剖開放大（另一個比例尺）', 'hd')}
      ${nutZoom()}

      <!-- ================= 第 2 排：② 橫剖 ｜ ③ 諧波 ｜ ④ RV ================= -->
      ${frame(16, 204, 300, 168)}
      ${T(28, 226, '② 同一支模組・橫剖', 'hd')}
      <g transform="translate(0,20)">${axisCross()}</g>

      ${frame(328, 204, 316, 168)}
      <path class="mcdiv" d="M434,214 L434,362" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      ${T(338, 226, '③ 諧波減速機', 'hd')}
      <g transform="translate(-14,0)">${harmonic()}</g>
      ${T(442, 226, '④ RV（兩級・同比例尺）', 'hd')}
      <g transform="translate(-230,0)">${rvReducer()}</g>

      <!-- ================= 第 3 排：⑤ 控制鏈（閉合的環，3 ＋ 2 兩列） ================= -->
      ${frame(16, 384, 628, 180)}
      ${T(28, 408, '⑤ 控制鏈：主鏈一律向右、回授一律向左，這個環必須是閉的', 'hd')}
      ${T(28, 426, '只畫單向五格＝畫成了開迴路，那不是伺服', 'sub', null, 'fill:var(--dg-warn)')}
      ${ctrlLoop()}
      ${T(28, 550, '編碼器回授：起點在馬達，方向向左，跟主鏈相反 —— 有這條線才叫伺服', 'sub', null, 'fill:var(--dg-warn)')}

      <!-- ================= 說明卡片（HTML）：左欄縱剖與螺帽、右欄橫剖與兩種減速機 =================
           每一張卡片的 data-part 都跟畫布上的零件**同一個字串**（改造前後逐字比對過），
           所以既有互動一個都沒掉：點卡片亮零件、點零件亮卡片、連 3D 場景 motion_axis 的對應也不變。-->
      ${card({ side: 'l', no: 1, part: 'mc_motor', color: COL.case, ax: 64, ay: 128, title: '伺服馬達（尾端掛編碼器）', sub: '轉，並且回報自己轉到哪裡；本圖只畫外殼、不畫繞組剖面' })}
      ${card({ side: 'l', no: 2, part: 'mc_enc', color: COL.sig, ax: 33, ay: 128, title: '編碼器（回授的起點）', sub: '★ 在馬達的尾端（遠離螺桿那一側）；沒有它就只是一般感應馬達' })}
      ${card({ side: 'l', no: 3, part: 'mc_coupling', color: COL.steel, ax: 105, ay: 128, title: '聯軸器', sub: '★ 馬達與螺桿之間一定要有它；中間那段撓性溝就是識別特徵' })}
      ${card({ side: 'l', no: 4, part: 'mc_bearing', color: COL.case, ax: 132, ay: 128, title: '軸承座（固定端／支撐端）', sub: '兩端各一個：一端吃軸向力、一端只導引，讓螺桿受熱可以伸長' })}
      ${card({ side: 'l', no: 5, part: 'mc_screw', color: COL.steel, ax: 200, ay: 128, title: '滾珠螺桿・螺桿軸', sub: ['把馬達的「轉」變成工作台的「直線走」', '★ 溝槽剖面是圓弧，不是 V 形三角'] })}
      ${card({ side: 'l', no: 6, part: 'mc_nut', color: COL.case, ax: 261, ay: 128, title: '滾珠螺桿・螺帽（含循環器）', sub: '長度約螺桿全長的六分之一；內壁有對應的圓弧溝槽把鋼珠夾住' })}
      ${card({ side: 'l', no: 7, part: 'mc_ball', color: COL.ball, ax: 470, ay: 149, title: '鋼珠（兩點接觸）', sub: '★ 每一顆都同時碰到螺桿溝與螺帽溝 —— 浮在中間就不傳力' })}
      ${card({ side: 'l', no: 8, part: 'mc_return', color: COL.sig, ax: 470, ay: 124, title: '循環器（鋼珠回流通道）', sub: ['★ 這是這張圖的紅線零件：鋼珠走的是一個閉合迴圈', '沒有這條通道的是鎖緊用的梯形螺桿，不是傳動用的滾珠螺桿'] })}
      ${card({ side: 'r', no: 9, part: 'mc_rail', color: COL.steel, ax: 86, ay: 325, title: '線性滑軌・軌道 ×2', sub: '★ 兩條平行軌，而且螺桿在兩軌之間（推力不在形心上會把工作台扭起來）' })}
      ${card({ side: 'r', no: 10, part: 'mc_block', color: COL.case, ax: 66, ay: 310, title: '線性滑軌・滑塊（ㄇ 形）', sub: '★ 從上方罩下來、包住軌道兩側；放在軌道上面的方塊吃不了側向力與拉拔力' })}
      ${card({ side: 'r', no: 11, part: 'mc_base', color: COL.alu, ax: 60, ay: 350, title: '底座（鋁擠型）', sub: '斷面有空腔：同樣重量下拿到比較高的斷面剛性' })}
      ${card({ side: 'r', no: 12, part: 'mc_cs', color: COL.case, ax: 343, ay: 310, title: '諧波①：剛輪（最外，內齒）', sub: '固定不動。三件由外到內是 剛輪 → 柔輪 → 波產生器，順序反了機構不成立' })}
      <!-- ★ 2026-09-23：把「齒數比剛輪少幾齒（常見是 2 齒）」這句補回**永遠看得到**的卡片上。
           660 版改版時這句只剩在點零件才開的小卡（mc_fs.desc）裡，
           可是「柔輪的齒比剛輪少」這個主張是**畫在圖上**的（H3 量得到 14 齒 vs 12 齒）——
           主張畫在哪裡，「那是常見設計、不是物理必然」的但書就要放在哪裡，
           不能讓但書躲在一次點擊後面。 -->
      ${card({ side: 'r', no: 13, part: 'mc_fs', color: COL.flex, ax: 372, ay: 291, title: '諧波②：柔輪（薄壁・被壓成橢圓）', sub: '齒數比剛輪少幾齒（常見是 2 齒，但那是常見設計、不是物理必然）。★ 輸出是從柔輪的杯底法蘭出去，不是從剛輪出去' })}
      ${card({ side: 'r', no: 14, part: 'mc_wg', color: COL.cam, ax: 372, ay: 310, title: '諧波③：波產生器（橢圓凸輪＋薄軸承）', sub: '從裡面把柔輪撐成橢圓；轉一圈柔輪只退幾齒，減速比就是這樣來的' })}
      ${card({ side: 'r', no: 15, part: 'mc_planet', color: COL.steel, ax: 450, ay: 306, title: 'RV①：前級行星齒輪組', sub: '★ 一定在靠馬達那一端；只有一級的不是 RV' })}
      ${card({ side: 'r', no: 16, part: 'mc_cyclo', color: COL.disc, ax: 582, ay: 306, title: 'RV②：擺線盤 ×2（相位差 180°）', sub: '外緣是連續波浪、不是尖齒；針銷數 ＝ 波浪數 ＋ 1' })}
      ${card({ side: 'r', no: 17, part: 'mc_rv', color: COL.case, ax: 582, ay: 269, title: 'RV：輸出法蘭／殼體', sub: '★ 同一個比例尺下外徑明顯大於諧波 —— 大與重就是它的代價' })}
      ${card({ side: 'r', no: 18, part: 'mc_fb', color: COL.warn, ax: 127, ay: 478, title: '編碼器回授線', sub: '★ 有這條線才叫伺服；起點在馬達的編碼器，方向一律往左' })}
      ${note({ side: 'l', order: 96, title: '這張圖要講的四件事',
      lines: ['① 螺桿出力、滑軌只負責「別歪掉」—— 是兩個零件，同一根軸上兩個都要有。',
        '② 兩者都靠鋼珠把滑動摩擦換成滾動，所以兩者都必須有鋼珠回流的路徑。',
        '③ 減速機有兩個家族，不能互換：諧波走手腕與小負載、RV 走基座與重負載。',
        '④ 有編碼器回授才叫伺服：控制器→驅動器→馬達→傳動→負載→回授，環要閉。'] })}
      ${note({ side: 'l', warn: true, order: 97, title: '★ 誰做的（逐件見下面第 ① 段）',
      lines: ['螺桿與滑軌 2049 上銀／4540 全球傳動／1597 直得；馬達 4576 大銀微系統；',
        '減速機 4583 台灣精銳；控制器 7750 新代。',
        '★ 6603 富強鑫做的是射出成型機，不是切削工具機 —— 不在「加工機三軸」那一格。'] })}
      ${note({ side: 'r', order: 98, title: '這張圖沒有回答的事',
      lines: ['示意圖，非實物比例｜各零件的相對尺寸為誇張放大。',
        '不寫任何導程、精度等級、減速比、額定扭矩與市占率數字。',
        '「工業自動化」與「CNC 工具機」目前不在供應鏈資料的環節裡，所以下方的「環節色標」篩不到它們；公司對應寫在卡片、零件小卡與第 ① 段。',
        '氣動、視覺、系統整合三類公司沒有畫在主圖上 —— 見下面兩段。'] })}

      <!-- ================= ① 誰做的 ＋ 裝到哪裡去（預設收合） ================= -->
      ${D.foldBar('mc1', S1, '① 每一個零件是誰做的 ＋ 裝到哪裡去',
    '逐件台股對應 6 條、4 種機器，以及查不到的那幾家')}
      <g class="dgbody" data-fold="mc1" data-y0="${S1 + 46}" data-y1="${S1 + 46 + w1.h}">
        ${w1.svg}
      </g>

      <!-- ================= ② 氣動那一路（預設收合） ================= -->
      ${D.foldBar('mc2', S2, '② 氣動那一路：三點組 → 電磁閥 → 氣缸',
    '3 個零件的剖面與先後順序，以及它跟伺服電動軸的分界（沒有回授）')}
      <g class="dgbody" data-fold="mc2" data-y0="${S2 + 46}" data-y1="${S2 + 46 + w2.h}">
        ${w2.svg}
      </g>
    </svg>`;
  }

  /* `parts` ＝點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
     ★ 這張圖一個環節屬性都沒有，所以 `cos` 一律留空 —— 這 19 檔一檔都不在
       `supply_chain.yaml` 裡，寫進 `cos` 只會被 filter 靜靜丟掉，
       得到一張「少了人卻沒有任何提示」的卡片。公司一律寫進 `none:` 的整句話（R4／R5）。
     ★ 角色描述抄 `docs/groups_tide110_evidence.md`，但拿掉該表裡的法人用語（§6-X5）。 */
  const PARTS = {
    mc_motor: {
      name: '伺服馬達（尾端掛編碼器）',
      desc: '轉，並且回報自己轉到哪裡。★ 沒有尾端那顆編碼器就只是一般感應馬達 —— 「會轉」跟「知道自己轉到哪」是兩件事。本圖只畫外殼，不畫繞組剖面（那會跟變壓器那張撞題）。',
      none: '伺服馬達在台股：4576 大銀微系統（線性馬達與傳動，信心：verified）。本圖畫的是旋轉馬達＋螺桿，直接驅動的線性馬達是另一種架構、本圖未畫。★ 這一檔不在 supply_chain.yaml 的環節裡，所以這張小卡的「做這個的台股」欄列不出它 —— 這裡用文字補。',
    },
    mc_enc: {
      name: '編碼器（回授的起點）',
      desc: '裝在馬達的尾端（遠離螺桿那一側），把「現在轉到哪」送回驅動器與控制器。控制鏈上那條往左的線就是從它出發的。',
      none: '編碼器這一件，本圖查不到台股的具名對應 —— 查不到就寫查不到，不編一個對應。',
    },
    mc_coupling: {
      name: '聯軸器',
      desc: '★ 馬達與螺桿之間一定要有它。直接畫成一根連續的軸就是錯 —— 那表示兩根軸完全同心且剛性連接，實務上做不到，也沒有可更換的犧牲件。中間那一段撓性溝就是它的識別特徵。',
      none: '聯軸器這一件，本圖查不到台股的具名對應。',
    },
    mc_bearing: { name: '軸承座（固定端／支撐端）', desc: '螺桿兩端各一個：一端固定（吃軸向力）、一端支撐（只導引，讓螺桿受熱可以伸長）。兩端都畫成固定端，螺桿熱起來就被自己頂彎。' },
    mc_screw: {
      name: '滾珠螺桿・螺桿軸',
      desc: '把馬達的「轉」變成工作台的「直線走」。★ 表面的溝槽剖面是圓弧（哥德弧或單圓弧），不是 V 形三角 —— V 形那是鎖緊用的螺絲，走的是滑動摩擦。',
      none: '滾珠螺桿在台股：2049 上銀（滾珠螺桿與線性滑軌）、4540 全球傳動（線性傳動）。兩家的終端不同 —— 上銀多在工具機、全球傳動在產業機械（信心：中，來源為產業媒體整理）。★ 兩檔都不在 supply_chain.yaml 裡，所以這張小卡列不出它們。',
    },
    mc_nut: {
      name: '滾珠螺桿・螺帽（含循環器）',
      desc: '套在螺桿上的金屬套筒，長度約螺桿全長的六分之一。內壁有對應的圓弧溝槽把鋼珠夾住，外側有法蘭鎖到工作台上。裡面的鋼珠與回流通道見右邊的放大格。',
      none: '同螺桿軸：2049 上銀、4540 全球傳動。兩檔都不在 supply_chain.yaml 裡。',
    },
    mc_ball: {
      name: '鋼珠（兩點接觸）',
      desc: '★ 每一顆都同時碰到螺桿溝與螺帽溝 —— 浮在中間就不傳力。鋼珠把滑動摩擦換成滾動摩擦，這是滾珠螺桿跟一般螺桿唯一的差別。',
      none: '鋼珠（鋼球）這一件，本圖查不到台股的具名對應。',
    },
    mc_return: {
      name: '循環器（鋼珠回流通道）',
      desc: '★ 這是這張圖的紅線零件：鋼珠沿溝槽滾到螺帽的一端之後，從這條 U 形通道繞回另一端，重新進入溝槽 —— 是一個閉合的迴圈。沒有這條通道的螺桿是鎖緊用的梯形螺桿，不是傳動用的滾珠螺桿。',
      none: '循環器是螺桿廠自己做的零件，本圖查不到獨立供應的台股對應。',
    },
    mc_table: { name: '工作台（滑座）', desc: '同時鎖在螺帽與滑塊上：螺帽推它走、滑塊撐住它不歪。兩個連接都要有 —— 少一個這根軸就不成立。' },
    mc_base: { name: '底座（鋁擠型）', desc: '斷面有空腔的擠型鋁材，兩條軌道固定在它上面。空腔是為了在同樣重量下拿到比較高的斷面剛性。' },
    mc_rail: {
      name: '線性滑軌・軌道',
      desc: '凸出來的一條，兩側有圓弧溝。★ 一定是兩條平行軌，而且螺桿在兩軌之間 —— 螺桿畫在旁邊的話推力不在滑座形心上，工作台會被扭起來。',
      none: '線性滑軌在台股：2049 上銀（滾珠螺桿與線性滑軌）、1597 直得（線性滑軌）。★ 兩檔都不在 supply_chain.yaml 裡，所以這張小卡列不出它們 —— 這裡用文字補。',
    },
    mc_block: {
      name: '線性滑軌・滑塊',
      desc: '★ ㄇ 字形，從上方罩下來、包住軌道的兩側。畫成「一個方塊放在軌道上面」就是錯的 —— 那樣的東西吃不了側向力也吃不了拉拔力，而滑軌存在的理由就是吃這兩種力。滑軌不出力，只負責「別歪掉」與承重。',
      none: '同軌道：2049 上銀、1597 直得。兩檔都不在 supply_chain.yaml 裡。',
    },
    mc_railball: { name: '滑軌用滾珠', desc: '在軌道的圓弧溝與滑塊的圓弧溝之間，兩側各一列。滾珠在滑塊外面就不是滾動導引了。' },
    mc_cs: { name: '剛輪（circular spline）', desc: '★ 諧波減速機的最外圈，內側有齒、固定不動。三件的順序由外到內是 剛輪 → 柔輪 → 波產生器，順序反了機構就不成立（柔輪要被波產生器從裡面撐開、去咬外面的剛輪）。' },
    mc_fs: {
      name: '柔輪（flex spline）',
      desc: '★ 中間那一圈，壁很薄、被波產生器壓成橢圓：長軸兩端咬住剛輪、短軸兩端脫開。齒數比剛輪少幾齒（常見是 2 齒，但那是常見設計、不是物理必然）。輸出是從柔輪的杯底法蘭出去，不是從剛輪出去。',
      none: '減速機在台股：4583 台灣精銳（減速機）。★ 查不到它做的是諧波、RV 還是行星，所以諧波與 RV 兩格不指定其中一格（查不到就寫查不到）。4583 不在 supply_chain.yaml 裡。',
    },
    mc_wg: { name: '波產生器（wave generator）', desc: '最裡面那一件：一顆橢圓凸輪外面套一圈薄軸承。它從裡面把柔輪撐成橢圓，柔輪的長軸兩端因此去咬剛輪 —— 轉一圈，柔輪相對剛輪只退幾齒，減速比就是這樣來的。' },
    mc_planet: { name: 'RV・前級行星齒輪組', desc: '★ 一定在靠馬達那一端。一組行星輪繞著一個太陽輪、外面是內齒圈 —— 這是 RV 的第一級。只有一級的不是 RV。' },
    mc_crank: { name: 'RV・曲柄軸（偏心）', desc: '把前級的轉動變成偏心運動，帶著擺線盤在針齒環裡滾。中段偏心是它的識別特徵。' },
    mc_cyclo: { name: 'RV・擺線盤 ×2', desc: '★ 兩片、相位差 180 度（單片會有不平衡力）。外緣是連續的波浪，不是尖齒 —— 波浪咬在外面那一圈圓柱針銷上。這是 RV 的第二級。' },
    mc_pin: { name: 'RV・針齒（針銷）環', desc: '沿外殼內壁排一圈的圓柱。針銷數比擺線盤的波浪數多一個 —— 擺線盤每轉一圈只退一個針距，減速比就是這樣來的。' },
    mc_rv: {
      name: 'RV 減速機・輸出法蘭／殼體',
      desc: '★ 兩級（行星＋擺線），大、重，但剛性與壽命好、抗衝擊 → 工業機器人的基座與腰部。同一個比例尺下它的外徑明顯大於諧波 —— 大與重就是它的代價，畫成一樣大就把這格對照的意義畫掉了。',
      none: '減速機在台股：4583 台灣精銳（減速機）。★ 查不到它做的是諧波還是 RV，所以兩格共用同一句話、不指定其中一格。4583 不在 supply_chain.yaml 裡。',
    },
    mc_ctrl: {
      name: '控制器',
      desc: '算出每一軸下一毫秒要走到哪。★ 本圖只畫成方塊 —— 剖開畫裡面的電路板會跟 PCB 與被動元件那兩張撞題。',
      none: 'CNC 控制器在台股：7750 新代（CNC 控制器，信心：verified）。★ 7750 不在 supply_chain.yaml 裡，所以這張小卡列不出它 —— 這裡用文字補。',
    },
    mc_drive: { name: '伺服驅動器', desc: '把控制器的命令變成馬達要的電流，同時讀編碼器的回授。本圖只畫成方塊，不剖開畫電路板。' },
    mc_trans: { name: '減速機／滾珠螺桿（傳動段）', desc: '關節轉動走減速機、直線移動走滾珠螺桿 —— 同一條控制鏈上的同一站，換的是機構。' },
    mc_load: { name: '負載（工作台、手臂）', desc: '真的動了的那一端。★ 負載上面加工的是什麼工件不在這張圖的範圍裡。' },
    mc_fb: {
      name: '編碼器回授線',
      desc: '★ 有這條線才叫伺服 —— 沒有回授就只是照表操課，走偏了也不知道。回授的起點在馬達的編碼器（不是在負載），方向一律往左，跟主鏈相反。',
      none: '這是一條訊號路徑，不是一個買得到的零件。',
    },
    mc_machine: {
      name: '加工機三軸（X／Y／Z）',
      desc: '一台加工機的每一個軸裡面，裝的就是上面那一整套：馬達 → 聯軸器 → 螺桿 → 滑軌 → 工作台。',
      none: '整機在台股：4526 東台（綜合加工機）、1583 程泰（車床與加工中心機）、1528 恩德（專用工具機）。★ 6603 富強鑫做的是射出成型機，不在這一格。三檔都不在 supply_chain.yaml 裡。',
    },
    mc_robot: {
      name: '協作型機器人',
      desc: '手腕與小負載關節走諧波減速機（小、輕、精度高）。基座與腰部那種重負載軸走的是 RV。',
      none: '協作型機器人在台股：4585 達明（協作型機器人）。★ 4585 不在 supply_chain.yaml 裡。',
    },
    mc_amhs: {
      name: 'AMHS 天車與智慧物流',
      desc: '半導體廠裡把晶圓盒在機台之間搬來搬去的那一套。★ 本圖不畫天車外觀與軌道配置 —— 查不到可引用的資料，不編一個出來。',
      none: 'AMHS 在台股：2464 盟立（半導體廠 AMHS 與智慧物流系統整合）。★ 2464 不在 supply_chain.yaml 裡。',
    },
    mc_inject: {
      name: '射出成型機（★ 不是切削工具機）',
      desc: '★ 這一格刻意單獨列出來：它是把塑料射進模具的機器，跟本圖畫的切削加工機是兩種東西。把族群名當事實照抄就會畫錯 —— 這是「成分表不等於產品事實」的典型坑。',
      none: '射出成型機在台股：6603 富強鑫（射出成型機）。它在「CNC 工具機」族群裡，但做的不是切削工具機。6603 不在 supply_chain.yaml 裡。',
    },
    mc_air: {
      name: '氣動那一路（整段）',
      desc: '三點組 → 電磁閥 → 氣缸。同樣是「讓東西動」，但走的是壓縮空氣，而且沒有編碼器回授 —— 所以停不到任意位置。這就是它跟伺服電動軸的分界。',
      none: '氣動元件在台股：1590 亞德客-KY（氣動元件，信心：verified）。★ 1590 不在 supply_chain.yaml 裡，所以這張小卡列不出它 —— 這裡用文字補。',
    },
    mc_air_frl: { name: '三點組（過濾＋調壓＋給油）', desc: '壓縮空氣進氣缸之前先過濾、把壓力調到要的值、再給一點油。順序不能對調 —— 先給油再過濾等於把油濾掉。' },
    mc_air_valve: { name: '電磁閥', desc: '決定壓縮空氣往氣缸的哪一腔走，也就決定活塞往哪邊推。它是氣動那一路的開關。' },
    mc_air_cyl: { name: '氣缸', desc: '活塞被壓縮空氣推出去。本圖不寫任何氣壓、缸徑與行程數字（查不到共通值）。' },
  };
  // 第 ① 段那幾列（誰做的逐件表）也給小卡，點哪一列就講那一件
  WHO.forEach((r, i) => {
    PARTS['mc_who' + i] = {
      name: r[0], desc: r[1],
      none: '這一列的公司全部不在 supply_chain.yaml 的環節裡，所以「做這個的台股」欄列不出它們 —— 對應寫在這裡。',
    };
  });

  window.DG.register('factory_automation', {
    level: 'group', chain: 'electronics',
    name: '工業自動化：一個會動的軸拆開看',
    /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0-A 原本寫「不做真 3D」，
       推翻的不是那個理由本身，是它漏掉的另一半（判準見 DECISIONS #247／#251）：
       原本的理由是「五個資訊點裡沒有一個靠轉一圈才看得懂」——
       漏掉的是第六件事：一根軸是一**串**零件（馬達→聯軸器→軸承座→螺桿＋螺帽→滑軌＋滑塊），
       而「誰接誰」只有沿著軸拆開才看得出來；螺帽剖開才看得到鋼珠是一個閉合的迴圈。
       ⚠ 3D 場景跟 `machine_tool` 共用同一個（兩個族群本來就共用同一張 2D）。*/
    draw: motionControl, native: CW, scene: 'motion_axis',
    q: '工廠裡一次直線移動、一次關節轉動，各自靠哪幾個零件？滾珠螺桿跟線性滑軌差在哪？諧波減速機跟 RV 減速機為什麼不能互換？',
    parts: PARTS,
  });
  /* ⚠ 一張圖掛兩個族群：兩列各自宣告、`draw` 指向同一支函式就好。
     **不要**為了這件事去改 `DiagramSlots.pick()` 的查找邏輯（那是全站共用的）——
     `passive_rlc` 已經走過這條路。*/
  window.DG.register('machine_tool', {
    level: 'group', chain: 'electronics',
    name: 'CNC 工具機：它身上的傳動件是誰做的',
    /* 3D 跟 `factory_automation` 指向**同一個場景**（`motion_axis`）——
       兩個族群本來就共用同一張 2D，3D 再開第二份只會變成兩份要一起改的東西。*/
    draw: motionControl, native: CW, scene: 'motion_axis',
    q: '一台加工機的三個軸裡面裝的是什麼？台股做整機的跟做傳動件的是不同的兩群人，各是誰？',
    parts: PARTS,
  });
})();
