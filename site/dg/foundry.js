/* 晶圓代工：一顆電晶體與一個製程迴圈 —— docs/diagram_plan_semiconductor.md 的 S1
   （族群 `foundry`、semiconductor 鏈）

   合約＝`docs/diagram_specs/foundry_process.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事：

     · §0-A **不做真 3D**（`scene: null`）。六個資訊點裡有五個是「剖面／平面上的關係」，
       3D 只會把它們擋住；而且鰭寬是 nm 級、晶圓是 300 mm 級，差七個數量級。
       回頭加 3D 的唯一條件寫在 §0-A，「看起來比較立體」不算理由。
     · §0-B 交界：**不畫中介層、CoWoS、HBM、微凸塊、底填、載板**（那是封裝那兩張），
       **不畫切割打線模封測試**（那是 S5），**不畫 SiC／GaN 功率元件**（那是第三代半導體）。
       這張圖的終點是「一片還沒被切開的完成品晶圓」。
     · §3-A F6／§6-T7（紅線）**GAA 的閘極金屬要填進每一對相鄰奈米片之間的縫**，
       而且最上片上方、最下片下方也要有。只畫在最上面那片上方＝畫的是 FinFET。
       實作上這一條靠 `gaaLayers()` 裡那個**同一個迴圈**保證：金屬與片在同一輪產生，
       漏不掉最底下那一層。
     · §3-D N4（紅線）**背面供電只出現在 A16 那一格**。N2 是正面供電。
       畫錯是可以查證的事實錯誤，所以「背面供電」這四個字在這個檔的節點列裡只出現在 A16。
     · §3-A F3／§6-T3 **鰭高 > 鰭寬 × 2**。這裡是 76 / 16 ＝ 4.75 倍。
       這是「畫面可辨識性的下限規則」，不是真實比例的宣稱（§7-B5）。
     · §7-C **一個良率、成本、市占率、產能數字都不寫**。畫面上唯二的數字是
       製程迴圈的層數／光罩數區間（標「來源：業界整理」）與 N2 的效能敘述（標「相對 N3E」）。

   三個實作上的取捨，寫在這裡不要讓下一個人再想一次
   ---------------------------------------------------
   1. **三格電晶體用同一支 `txCell()`**，同一組基準座標（基板 298～352、通道面 298）、
      同一套材質色，只換「閘極包覆路徑」與「通道形狀」——§3-A F1／§6-T1 因此自動成立。
   2. **源極／汲極的剖面位置是誠實的妥協**：FinFET 與 GAA 畫的是「垂直於鰭／片」的橫剖面，
      嚴格說源汲不在這個切面上。但 §6-T10 要求三格都看得到源汲，
      所以把它們畫在切面兩端，並在每一格底下寫一行「剖面兩端的源／汲為示意，不與閘極同一切面」，
      不假裝它們跟閘極在同一個平面上。
   3. **節點列沒有用 `D.processBar()`**：那支的方塊只放得下標題＋副標兩行，
      而節點列每一格要放「結構／時程／效能／供電」四件事，而且它會多帶一顆
      `animateMotion` 的白點 —— §9 明寫「動畫只做一件事（一個點沿著迴圈跑）」。
      所以底下自己寫了一支 `nodeCell()`。這是共用工具跟規格衝突時的例外，不是「自己造第二套」。

   顏色一律走既有的 `--dg-*`（沒有新增任何 token，也沒有動 index.html 的 :root），
   JS 裡一個 #xxxxxx 都沒有。這個檔不碰 `site/diagrams.js`／`site/three3d.js`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;   // diagrams.js 沒載到就安靜退出

  const W = 980, SEG = 'foundry';

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${+x.toFixed(1)}" y="${+y.toFixed(1)}" width="${+w.toFixed(1)}" height="${+h.toFixed(1)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  /* 零件外框。這張圖**每一個零件都掛 data-seg="foundry"**（§7-D1 第 1 點：
     電晶體與製程迴圈確實就是晶圓代工廠在做的事，掛對了）。*/
  const part = (id, inner) => `<g data-part="${id}" data-seg="${SEG}">${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${+x.toFixed(1)}" y="${+y.toFixed(1)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;

  /* 一支「閘極管到這一面」的箭頭。三格共用同一支 —— §6-T8 要數得出 1／3／4 支，
     所以每一支都是一個 `path.arw`，數 path.arw 就是數面數。*/
  function arw(x0, y0, x1, y1) {
    const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len, hx = -uy, hy = ux, H = 5.5, B = 3.4;
    const bx = x1 - ux * H, by = y1 - uy * H;
    return `<path class="arw" d="M${x0.toFixed(1)},${y0.toFixed(1)} L${bx.toFixed(1)},${by.toFixed(1)}" `
      + `stroke="var(--dg-accent-2d)" stroke-width="1.8" fill="none"/>`
      + `<path class="arwh" d="M${x1.toFixed(1)},${y1.toFixed(1)} L${(bx + hx * B).toFixed(1)},${(by + hy * B).toFixed(1)} `
      + `L${(bx - hx * B).toFixed(1)},${(by - hy * B).toFixed(1)}Z" fill="var(--dg-accent-2d)"/>`;
  }

  /* ================================================================ 區 A：三格電晶體

     三格共用的基準（§3-A F1／§6-T1：同一個放大倍率、同一套材質色、同一個剖面方向）：
       基板頂面 y=298、基板底 y=352；結構往上長，最高不超過 y=130。
     每一格 304 寬，內容區 X+16 ～ X+288，中線 cx = X+152。*/
  /* 區 A 是**唯一留在主畫面**的一區（Andy 2026-09-22：「圖片及文字縮小一半…希望能一次看到完整資訊」）。
     它就是這張圖的命題 —— 三代電晶體改的都是同一件事。其餘四塊收進章節列。
     `TXDY` 把三格的幾何整體往上提，讓格子從 436 高瘦到 340；**字一個都沒縮**（12px 是硬下限）。*/
  const CELL_W = 304, CA_Y = 52, CA_H = 340, TXDY = -38;
  const SUB_T = 298, SUB_B = 352;

  // 鰭：**高 76 ／ 寬 16 ＝ 4.75 倍**（§6-T3 要求 > 2 倍）。改這兩個數字之前先看那一條。
  const FIN_W = 16, FIN_H = 76;
  // 奈米片：**寬 96 ／ 厚 12 ＝ 8 倍**（§6-T6 要求 > 3 倍）。片數 3（§3-A F5 要求 2～4）。
  const SH_W = 96, SH_T = 12, SH_N = 3, GM_T = 20;   // GM_T＝片與片之間那層閘極金屬的厚度

  /* GAA 的疊構。**金屬與片在同一個迴圈裡產生**（§9 的提醒：畫在迴圈外最容易漏掉最底下那一層，
     那就是 T7 不過）。回傳由下往上的 y 界，metals 一定比 sheets 多一個。*/
  function gaaLayers(bottom) {
    const sheets = [], metals = [];
    let y = bottom;
    for (let i = 0; i < SH_N; i++) {
      y -= GM_T; metals.push(y);          // 先鋪一層金屬（第一輪＝最下面那一片的「下方」）
      y -= SH_T; sheets.push(y);          // 再放一片
    }
    y -= GM_T; metals.push(y);            // 最上面那一片的「上方」也要有
    return { sheets: sheets, metals: metals, top: y };
  }

  function txCell(X, kind) {
    const cx = X + 152, L0 = cx - 136, R0 = cx + 136;
    const g = [];

    // ---- 共用：矽基板（三格同一個位置、同一個顏色）
    g.push(part('fd_sub', R(L0, SUB_T, R0 - L0, SUB_B - SUB_T, 'var(--dg-si-2)', 'part', 2)));

    if (kind === 'planar') {
      /* 一 平面：通道是**一條水平薄層**，閘極**只從上方蓋下來**（§3-A F2／§6-T2）。
         閘極包到側面＝那不是平面電晶體。*/
      g.push(part('fd_sd', R(L0 + 8, 272, 82, 26, 'var(--dg-organic)', 'part', 2)
        + R(cx + 46, 272, 82, 26, 'var(--dg-organic)', 'part', 2)));
      g.push(part('fd_planar', R(cx - 46, 288, 92, 10, 'var(--dg-si)', 'part', 1)));      // 通道
      g.push(part('fd_hk', R(cx - 46, 282, 92, 6, 'var(--dg-sn)', 'part')));              // 閘極介電層（極薄）
      g.push(part('fd_spacer', R(cx - 58, 252, 12, 36, 'var(--dg-mute)', 'part', 1)
        + R(cx + 46, 252, 12, 36, 'var(--dg-mute)', 'part', 1)));
      g.push(part('fd_gate', R(cx - 46, 252, 92, 30, 'var(--dg-steel)', 'part', 2)));
      g.push(part('fd_face1', arw(cx, 214, cx, 246)));                                    // 1 面
      g.push(`<g pointer-events="none">${T(cx, 206, '閘極只管得到通道的一面', 'lbl', 'middle')}</g>`);

    } else if (kind === 'fin') {
      /* 二 FinFET：**垂直於鰭的橫剖面**。閘極是 ㄇ 字形、真的罩到兩個側面，
         而**鰭的最底部埋在 STI 裡、沒有被包到**（§3-A F4／§6-T4）。
         兩片平行的鰭（§6-T5：單鰭看不出「鰭是重複單元」）。*/
      const fx = [cx - 52, cx + 36];                       // 兩片鰭的左緣，節距 88
      g.push(part('fd_sd', R(L0 + 8, 246, 44, 52, 'var(--dg-organic)', 'part', 2)
        + R(cx + 84, 246, 44, 52, 'var(--dg-organic)', 'part', 2)));
      g.push(part('fd_fin', fx.map(x => R(x, SUB_T - FIN_H, FIN_W, FIN_H, 'var(--dg-si)', 'part', 1)).join('')));
      // STI 只淹到鰭的下部（26／76），上面 50px 才是被閘極包住的那一段
      g.push(part('fd_sti', R(L0, 272, R0 - L0, 26, 'var(--dg-el)', 'part', 1)));
      /* ㄇ 字形一律用**填色的多邊形**畫，不用 stroke。
         理由：`diagrams.js` 的 `.dg [data-seg] .part{stroke:…}` 是 CSS，
         它會蓋掉 SVG 的 `stroke` 呈現屬性 —— 用 stroke 畫出來的閘極會變成
         「一條細細的環節色外框」，看起來完全不像一塊金屬。填色不受影響。*/
      const uShape = (x, out, topOut, inn, topIn, bot) =>
        `M${x - out},${bot} L${x - out},${topOut} L${x + FIN_W + out},${topOut} L${x + FIN_W + out},${bot} `
        + `L${x + FIN_W + inn},${bot} L${x + FIN_W + inn},${topIn} L${x - inn},${topIn} L${x - inn},${bot}Z`;
      g.push(part('fd_hk', fx.map((x) => PA(uShape(x, 3, 219, 0, 222, 272), 'var(--dg-sn)', 'part')).join('')));
      g.push(part('fd_gate', fx.map((x) => PA(uShape(x, 15, 207, 3, 219, 272), 'var(--dg-steel)', 'part')).join('')));
      // 三面：上、左、右各一支，指向左邊那片鰭的閘極
      g.push(part('fd_face3', arw(cx - 44, 184, cx - 44, 204)
        + arw(cx - 84, 248, cx - 70, 248) + arw(cx - 2, 248, cx - 18, 248)));
      /* 鰭底那一段管不到 —— 這就是 FinFET 的極限。
         **這裡刻意只畫一個虛線框、不放文字**：格子只有 304 寬，任何一行說明放進來
         都會壓到零件或伸出格外。那句話改放在下面的說明行（警語色那兩行）。*/
      g.push(`<g pointer-events="none">${LN(`M${cx - 58},271 L${cx - 26},271 L${cx - 26},299 L${cx - 58},299Z`,
        'var(--dg-warn)', 1.4, ' stroke-dasharray="4 3"')}</g>`);
      // 右上角的等角輔助圖（灰階、不搶主角）：一條長鰭橫躺、閘極橫跨過去
      g.push(part('fd_fin_iso', '<g opacity=".72">'
        + PA(`M${cx + 56},196 L${cx + 122},164 L${cx + 130},168 L${cx + 64},200Z`, 'var(--dg-mute)', 'part')
        + PA(`M${cx + 56},196 L${cx + 64},200 L${cx + 64},212 L${cx + 56},208Z`, 'var(--dg-mute)', 'part')
        + PA(`M${cx + 84},190 L${cx + 100},182 L${cx + 108},186 L${cx + 92},194Z`, 'var(--dg-steel)', 'part')
        + PA(`M${cx + 84},190 L${cx + 92},194 L${cx + 92},208 L${cx + 84},204Z`, 'var(--dg-steel)', 'part')
        + '</g>' + T(cx + 6, 158, '等角輔助：閘極跨過鰭', 'sub')));

    } else {
      /* 三 GAA 奈米片 —— 本圖的主角。
         **每兩片之間都有閘極金屬，最上片上方與最下片下方也有**（§3-A F6／§6-T7，紅線）。
         介電層**繞著每一片走一圈**（封閉細框，§3-A F7）。*/
      const lay = gaaLayers(292);
      const sx = cx - SH_W / 2, mx = cx - SH_W / 2 - 14, mw = SH_W + 28;
      // 先鋪金屬（四層水平 ＋ 兩條側邊），片與介電層畫在它上面
      /* 金屬層左右各多伸 8px，剛好把「片與片之間、閘極與源汲之間」那一段補滿 ——
         內間隙壁只存在於**片**那幾層（它的工作是把閘極跟源汲擋開），
         金屬層那幾層如果不補滿，畫面上會出現兩條看起來像破洞的黑縫。*/
      g.push(part('fd_gaa',
        lay.metals.map((y) => R(mx - 8, y, mw + 16, GM_T, 'var(--dg-steel)', 'part gm', 1)).join('')
        + R(mx, lay.top, 14, 292 - lay.top, 'var(--dg-steel)', 'part gs', 1)
        + R(mx + mw - 14, lay.top, 14, 292 - lay.top, 'var(--dg-steel)', 'part gs', 1)));
      g.push(part('fd_sheet', lay.sheets.map(y => R(sx, y, SH_W, SH_T, 'var(--dg-si)', 'part', 1)).join('')));
      g.push(part('fd_hk', lay.sheets.map(y =>
        `<rect class="part" x="${(sx - 3).toFixed(1)}" y="${(y - 3).toFixed(1)}" width="${SH_W + 6}" height="${SH_T + 6}" rx="2" fill="none" stroke="var(--dg-sn)" stroke-width="2"/>`).join('')));
      // 內間隙壁：夾在閘極與源汲之間，每一片兩端各一塊
      g.push(part('fd_spacer', lay.sheets.map(y =>
        R(mx - 8, y - 3, 8, SH_T + 6, 'var(--dg-mute)', 'part') + R(mx + mw, y - 3, 8, SH_T + 6, 'var(--dg-mute)', 'part')).join('')));
      // 源汲磊晶：**把所有奈米片的端部一起接起來**（§3-A F9／§6-T9）
      g.push(part('fd_sd', R(L0 + 8, lay.top, mx - 8 - (L0 + 8), 292 - lay.top, 'var(--dg-organic)', 'part', 2)
        + R(mx + mw + 8, lay.top, (R0 - 8) - (mx + mw + 8), 292 - lay.top, 'var(--dg-organic)', 'part', 2)));
      // 四面：上、下、左、右，圍著中間那一片
      const mid = lay.sheets[1], mc = mid + SH_T / 2;
      g.push(part('fd_face4', arw(cx - 22, mid - 16, cx - 22, mid - 3)
        + arw(cx - 22, mid + SH_T + 16, cx - 22, mid + SH_T + 3)
        + arw(mx - 2, mc, sx - 4, mc) + arw(mx + mw + 2, mc, sx + SH_W + 4, mc)));
      // 可變片寬（NanoFlex，示意）：兩疊寬窄不同的片，灰階小圖，**不寫任何寬度數字**（§7-B2）
      g.push(part('fd_flex', '<g opacity=".7">'
        + [0, 1, 2].map(i => R(L0 + 14, 142 + i * 11, 26, 6, 'var(--dg-mute)', 'part', 1)).join('')
        + [0, 1, 2].map(i => R(L0 + 52, 142 + i * 11, 48, 6, 'var(--dg-mute)', 'part', 1)).join('')
        + '</g>' + T(L0 + 14, 134, '片寬可調（NanoFlex，示意）', 'sub')));
    }
    return g.join('');
  }

  /* 每一格的說明行。**一行最多 21 個字**（格子內寬 272px ÷ 12px ≒ 22）——
     超過就會伸進隔壁格，而那是字級與重疊都量不到的一種壞法。
     `wi` ＝要上警語色的行索引。*/
  /* 每一格的說明行從七行砍到三行（Andy：「同一件事在標題、說明列、標註講三次，留一次」）。
     砍掉的那幾行講的東西**沒有消失**：片寬片厚比、源汲磊晶接住所有片端、STI 埋住鰭底，
     圖上本來就畫得出來，而且零件小卡裡逐條寫著。
     一行最多 24 個字（格子內寬 272px）；`wi` ＝要上警語色的行索引。*/
  const TX = [
    {
      k: 'planar', x: 16, no: '一', nm: '平面（Planar）', fa: '閘極管到 1 面', wi: [],
      cap: ['通道是一條水平的薄層，閘極只從',
        '正上方蓋下來 —— 只管一面，關不住',
        '的漏電從其餘三面跑掉。'],
    },
    {
      k: 'fin', x: 334, no: '二', nm: 'FinFET（鰭式）', fa: '閘極管到 3 面', wi: [2],
      cap: ['把通道立起來變成一片鰭，閘極就',
        '罩住頂＋左＋右三面（鰭高是鰭寬 4.75 倍）。',
        '★ 虛線框那一段鰭底包不到，那就是盡頭。'],
    },
    {
      k: 'gaa', x: 652, no: '三', nm: 'GAA 奈米片', fa: '閘極管到 4 面', wi: [],
      cap: ['閘極金屬鑽進每一片之間的縫，上下',
        '左右四面都管得到 —— 這就是',
        'Gate-All-Around。'],
    },
  ];

  function areaA() {
    return TX.map((o) => {
      const cap = o.cap.map((s, i) => T(o.x + 16, 350 + i * 18, s, 'sub', null,
        o.wi.indexOf(i) >= 0 ? 'fill:var(--dg-warn)' : '')).join('');
      return `<g>${frame(o.x, CA_Y, CELL_W, CA_H)}
        ${T(o.x + 16, CA_Y + 22, o.no + '、' + o.nm, 'hd')}
        ${T(o.x + CELL_W - 16, CA_Y + 22, o.fa, 'lbl', 'end', 'fill:var(--dg-accent-2d)')}
        <g transform="translate(0,${TXDY})">${txCell(o.x, o.k)}</g>
        ${T(o.x + 16, 330, '（剖面兩端的源／汲為示意，不與閘極同切面）', 'cap')}
        ${cap}</g>`;
    }).join('');
  }

  /* ================================================================ 區 B（左）：三級縮放尺
     §3-E：由大到小 晶圓 → 晶粒 → 電晶體，三級之間有引線；
     晶圓要有 **notch**，而且**邊緣那一圈是殘缺的方格**（切不出完整晶粒的邊緣損失）。*/
  const WF = { cx: 112, cy: 632, r: 54, cell: 13, gap: 1.4 };

  function waferTop() {
    const pitch = WF.cell + WF.gap, cells = [];
    const n = Math.ceil((WF.r * 2) / pitch) + 2;
    const x0 = WF.cx - (n * pitch) / 2, y0 = WF.cy - (n * pitch) / 2;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const x = x0 + i * pitch, y = y0 + j * pitch;
        /* 四個角都在圓內＝完整晶粒；只要有一個角在圓外就是**殘缺**的那一圈。
           兩種格子分開上色，「邊緣損失」才看得到（§3-E Z2：畫成整片都是完整方格
           等於把邊緣損失畫不見了）。*/
        const cor = [[x, y], [x + WF.cell, y], [x, y + WF.cell], [x + WF.cell, y + WF.cell]];
        const d = cor.map((c) => Math.hypot(c[0] - WF.cx, c[1] - WF.cy));
        if (Math.min.apply(null, d) > WF.r) continue;              // 整格在圓外，不畫
        const full = Math.max.apply(null, d) <= WF.r;
        cells.push(R(x, y, WF.cell, WF.cell, full ? 'var(--dg-si)' : 'var(--dg-si-2)', full ? 'wcell' : 'wedge', 1));
      }
    }
    return `<clipPath id="fdWf"><circle cx="${WF.cx}" cy="${WF.cy}" r="${WF.r}"/></clipPath>`
      + `<circle class="part" cx="${WF.cx}" cy="${WF.cy}" r="${WF.r}" fill="var(--dg-void)"/>`
      + `<g clip-path="url(#fdWf)">${cells.join('')}</g>`
      // notch：晶圓的識別特徵（§3-E Z3）。不是一個完美的圓。
      + PA(`M${WF.cx - 7},${WF.cy - WF.r + 0.5} L${WF.cx},${WF.cy - WF.r + 12} L${WF.cx + 7},${WF.cy - WF.r + 0.5}Z`, 'var(--dg-bg)', 'notch');
  }

  function areaB() {
    /* 三級的名稱一律放在圖形**上方同一列**（y=572）。放下方會跟底下那四行說明擠在一起 ——
       1440 與 800 各量到兩對重疊 10～12px，那正是 `_preview.py` 專門在抓的壞法。*/
    const dieX = 246, dieY = 598, dieW = 68, tzX = 386, tzY = 612;
    const blocks = [[6, 6, 26, 20], [36, 6, 26, 12], [36, 22, 26, 18], [6, 30, 18, 32], [28, 42, 34, 20]];
    return `<g>${frame(16, 514, 484, 258)}
      ${T(32, 540, '三級縮放尺：一片晶圓 → 一顆晶粒 → 一顆電晶體', 'hd')}
      ${part('fd_wafer', T(WF.cx, 572, '12 吋（300 mm）晶圓俯視', 'lbl', 'middle') + waferTop())}
      ${LN(`M${WF.cx + WF.r + 6},${WF.cy} L${dieX - 10},${dieY + dieW / 2}`, 'var(--dg-accent-2d)', 1.6)}
      ${part('fd_die', T(dieX + dieW / 2, 572, '一顆晶粒', 'lbl', 'middle')
      + R(dieX, dieY, dieW, dieW, 'var(--dg-si-2)', 'part', 3)
      + blocks.map((b) => R(dieX + b[0], dieY + b[1], b[2], b[3], 'var(--dg-si)', 'part', 1)).join(''))}
      ${LN(`M${dieX + dieW + 8},${dieY + dieW / 2} L${tzX - 8},${tzY + 22}`, 'var(--dg-accent-2d)', 1.6)}
      ${part('fd_zoom', T(tzX + 39, 572, '一顆電晶體', 'lbl', 'middle')
      + R(tzX, tzY, 78, 44, 'var(--dg-void)', 'part', 3)
      + R(tzX + 8, tzY + 28, 62, 8, 'var(--dg-si)', 'part', 1)
      + R(tzX + 22, tzY + 12, 34, 12, 'var(--dg-steel)', 'part', 1))}
      ${T(32, 706, '邊緣這一圈切不出完整晶粒（顏色較暗的那些格子）', 'sub')}
      ${T(32, 724, '—— 晶圓越大，浪費掉的邊緣比例越小。', 'sub')}
      ${T(32, 742, '同一個缺陷密度下，晶粒越大、報廢的比例越高。', 'sub')}
      ${T(32, 760, '格數為示意；本圖不寫任何良率、產能與片數。', 'cap')}</g>`;
  }

  /* ================================================================ 區 B（右）：閘極堆疊放大格
     §3-C：由下到上 通道 → 界面層 → high-k → 功函數金屬 → 填充金屬。
     G1 high-k 在功函數金屬底下、G2 介電層是全圖最薄的層之一、
     G3 **不准畫成「二氧化矽 ＋ 複晶矽」**（先進節點早就是 high-k／金屬閘）。*/
  /* `ly` ＝這一層的標註文字排在第幾列。**不能用層的中線當標註的 y** ——
     high-k（8px）與界面層（4px）的中線只差 6px，兩行 12px 的字一定重疊（量到 8px）。
     所以標註走固定列距 26px，再用斜引線接回各自那一層。*/
  const GS = [
    { t: '填充金屬（fill metal）', y: 592, h: 40, ly: 600, c: 'var(--dg-steel)' },
    { t: '功函數金屬（work-function metal）', y: 632, h: 20, ly: 626, c: 'var(--dg-ni)' },
    { t: 'high-k 介電層（例：HfO2）', y: 652, h: 8, ly: 652, c: 'var(--dg-tim)' },
    { t: '界面層（interfacial layer）', y: 660, h: 4, ly: 678, c: 'var(--dg-sn)' },
    { t: '通道（矽／奈米片）', y: 664, h: 30, ly: 704, c: 'var(--dg-si)' },
  ];
  function areaB2() {
    const x = 540, w = 150, lx = 706;
    return `<g>${frame(512, 514, 452, 258)}
      ${T(528, 540, '閘極堆疊放大格（三格共用）', 'hd')}
      ${T(528, 560, '由下到上：界面層 → high-k → 功函數金屬 → 填充金屬。', 'sub')}
      ${part('fd_gate_stack', GS.map((o) => R(x, o.y, w, o.h, o.c, 'part', 1)).join(''))}
      ${GS.map((o) => LN(`M${x + w},${o.y + o.h / 2} L${lx - 10},${o.ly - 4}`, 'var(--dg-mute)', 1)
      + T(lx, o.ly, o.t, 'sub')).join('')}
      ${T(528, 734, '★ 先進節點是 high-k／金屬閘（HKMG）—— 畫成「二氧化矽＋複晶矽」', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(528, 752, '　 等於畫了一個二十年前的結構。介電層是全圖最薄的層之一。', 'sub', null, 'fill:var(--dg-warn)')}</g>`;
  }

  /* ================================================================ 區 C：製程迴圈環（九站）
     §3-B：**必須是閉合的環**（最後一站有一條線回到第一站），順序寫死，
     而且環的正中央要寫「這個環要繞 80～120 次」——沒有這句，這張圖的命題就不見了（P7）。
     站點角度用 i * 360/9 算（§9 的提醒：手刻九組座標最容易把順序寫錯）。*/
  const RING = { cx: 252, cy: 1040, r: 150, bw: 84, bh: 32, ar: 205 };
  const STEPS = [
    { id: 'fd_clean', n: '1', t: '清洗', s: '每一輪的開頭與結尾都要洗', m: '高純度化學品、超純水' },
    { id: 'fd_depo', n: '2', t: '沉積', s: '長出這一層的材料（CVD／ALD／PVD 濺鍍）', m: '靶材（PVD）、前驅氣體（CVD／ALD）' },
    { id: 'fd_resist', n: '3', t: '塗光阻', s: '先塗底部抗反射層（BARC），再塗光阻', m: 'BARC、光阻 —— BARC 在光阻底下' },
    { id: 'fd_litho', n: '4', t: '曝光', s: '把光罩上的圖案投影下來', m: 'DUV 193 nm／EUV 13.5 nm；EUV 只用在最關鍵的那幾層' },
    { id: 'fd_dev', n: '5', t: '顯影', s: '把曝到光的（或沒曝到的）洗掉，光阻變成罩幕', m: '顯影液、邊緣去膜（EBR）' },
    { id: 'fd_etch', n: '6', t: '蝕刻', s: '照著光阻的洞往下刻', m: '蝕刻氣體' },
    { id: 'fd_strip', n: '7', t: '去光阻', s: '光阻用完就拔掉，然後再洗一次', m: '去光阻液' },
    { id: 'fd_cmp', n: '8', t: 'CMP', s: '把這一層磨平，下一層才有平的地方站', m: '研磨液、研磨墊、鑽石碟' },
    { id: 'fd_metro', n: '9', t: '量測檢測', s: '量厚度、量線寬、找缺陷', m: '本圖只畫製程步驟，不畫任何機台外觀' },
  ];
  const ang = (i) => (-90 + i * (360 / STEPS.length)) * Math.PI / 180;
  const pt = (i, r) => [RING.cx + r * Math.cos(ang(i)), RING.cy + r * Math.sin(ang(i))];

  function ring() {
    const boxes = STEPS.map((s, i) => {
      const p = pt(i, RING.r);
      return part(s.id,
        R(p[0] - RING.bw / 2, p[1] - RING.bh / 2, RING.bw, RING.bh, 'var(--dg-step-f)', 'part st', 7)
        + T(p[0], p[1] + 5, s.n + '　' + s.t, 'lbl', 'middle'));
    }).join('');
    /* 九段箭頭，i → i+1（**含最後一段回到第一站**，少了它環就不閉合＝P1 不過）。
       一律順時針。*/
    const arrows = STEPS.map((s, i) => {
      const a0 = ang(i) + 0.30, a1 = ang(i + 1) - 0.30, r = RING.r;
      const x0 = RING.cx + r * Math.cos(a0), y0 = RING.cy + r * Math.sin(a0);
      const x1 = RING.cx + r * Math.cos(a1), y1 = RING.cy + r * Math.sin(a1);
      const tx = -Math.sin(a1), ty = Math.cos(a1), ex = Math.cos(a1), ey = Math.sin(a1);
      return `<path class="rarr" d="M${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)}" `
        + 'stroke="var(--dg-accent-2d)" stroke-width="2" fill="none" opacity=".85"/>'
        + `<path class="rarrh" d="M${(x1 + tx * 7).toFixed(1)},${(y1 + ty * 7).toFixed(1)} `
        + `L${(x1 - tx * 3 + ex * 5).toFixed(1)},${(y1 - ty * 3 + ey * 5).toFixed(1)} `
        + `L${(x1 - tx * 3 - ex * 5).toFixed(1)},${(y1 - ty * 3 - ey * 5).toFixed(1)}Z" fill="var(--dg-accent-2d)"/>`;
    }).join('');
    // FEOL 弧在 BEOL 弧之前（順時針較早的位置）（§3-B P8）
    const d2r = (d) => d * Math.PI / 180;
    const arc = (a0, a1, col) => {
      const r = RING.ar;
      const x0 = RING.cx + r * Math.cos(a0), y0 = RING.cy + r * Math.sin(a0);
      const x1 = RING.cx + r * Math.cos(a1), y1 = RING.cy + r * Math.sin(a1);
      return `<path class="part phase" d="M${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)}" stroke="${col}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
    };
    // 沿著環跑的那個點＝「一層」。這是這張圖**唯一**的動畫（§9）。
    const motion = `M${RING.cx},${RING.cy - RING.r} A${RING.r},${RING.r} 0 1 1 ${RING.cx},${RING.cy + RING.r} A${RING.r},${RING.r} 0 1 1 ${RING.cx},${RING.cy - RING.r}`;
    return `<g>
      <circle cx="${RING.cx}" cy="${RING.cy}" r="${RING.r}" fill="none" stroke="var(--dg-frame-s)" stroke-width="1"/>
      ${arrows}${boxes}
      ${part('fd_feol', arc(d2r(-124), d2r(-48), 'var(--dg-si)')
      + T(RING.cx, 866, 'FEOL 先做', 'lbl', 'middle'))}
      ${part('fd_beol', arc(d2r(-24), d2r(52), 'var(--dg-cu)')
      + T(386, 1222, 'BEOL 後做', 'lbl'))}
      ${part('fd_loop', `<circle class="part" cx="${RING.cx}" cy="${RING.cy}" r="98" fill="var(--dg-frame-f)"/>`
      + T(RING.cx, RING.cy - 28, '這個環要繞', 'sub', 'middle')
      + T(RING.cx, RING.cy - 4, '80～120 次', 'hd', 'middle')
      + T(RING.cx, RING.cy + 20, '約 90 道光罩', 'sub', 'middle')
      + T(RING.cx, RING.cy + 40, '一片晶圓在廠裡 3～4 個月', 'sub', 'middle')
      + T(RING.cx, RING.cy + 60, '（來源：業界整理，會過期）', 'cap', 'middle'))}
      <circle r="4.5" fill="var(--dg-accent-2d)"><animateMotion dur="11s" repeatCount="indefinite" path="${motion}"/></circle>
    </g>`;
  }

  function stepList() {
    return STEPS.map((s, i) => {
      const y = 840 + i * 44;
      return `<g>${T(488, y + 14, s.n + '　' + s.t + ' —— ' + s.s, 'lbl')}${T(488, y + 32, '吃：' + s.m, 'sub')}</g>`;
    }).join('');
  }

  /* ================================================================ 區 D：節點列（四格＋兩條分界線）
     §3-D：順序 N5 → N3 → N2 → A16；分界線 一「FinFET ↔ GAA」在 **N3 與 N2 之間**、
     二「正面供電 ↔ 背面供電」在 **N2 與 A16 之間**；
     N4（紅線）**背面供電只准出現在 A16 那一格**，所以只有最後一個 NODES 項目寫得到它。*/
  const NODES = [
    { t: 'N5', st: 'FinFET', a: ['成熟的 FinFET 世代。', '供電：正面。'] },
    { t: 'N3', st: 'FinFET（最後一代）', a: ['業界普遍視為最後也最成熟的', 'FinFET 世代。', '供電：正面。'] },
    { t: 'N2', st: 'GAA 奈米片（第一代）', a: ['2025 年底進入量產。相對 N3E：', '同功耗 +10～15% 速度，或同速度', '−25～30% 功耗、密度 +15% 以上。', '供電：正面。'] },
    { t: 'A16', st: 'GAA ＋ 背面供電', a: ['Super Power Rail：把供電網搬到', '晶圓背面。2026 下半年製程就緒，', '放量時程各家說法不一。'] },
  ];
  function nodeCell(o, i) {
    const x = 16 + i * 238, y = 1308;
    return `<g>${frame(x, y, 226, 124)}
      ${T(x + 14, y + 26, o.t, 'hd')}
      ${T(x + 212, y + 26, o.st, 'lbl', 'end', 'fill:var(--dg-accent-2d)')}
      ${o.a.map((s, j) => T(x + 14, y + 50 + j * 18, s, 'sub')).join('')}</g>`;
  }
  function areaD() {
    const div = (x, t) => LN(`M${x},1304 L${x},1436`, 'var(--dg-warn)', 2, ' stroke-dasharray="6 4"')
      + T(x, 1296, t, 'lbl', 'middle', 'fill:var(--dg-warn)');
    return `<g>${part('fd_node', NODES.map(nodeCell).join(''))}${div(486, 'FinFET ↔ GAA')}${div(724, '正面供電 ↔ 背面供電')}</g>`;
  }

  /* ================================================================ 整張圖 */
  function foundryProcess() {
    /* class 多一個 `dg1`：這張圖**全部零件都掛同一個 `foundry` 環節**，
       點任何一個都會讓所有零件一起 .sel —— `.dg.dg1` 的 `--dg-glow:none` 就是為這種圖留的，
       不然畫面上會同時有二十幾個東西在發光（Andy：「螢光感太重」）。*/
    /* 版面（Andy 2026-09-22：「圖片及文字縮小一半…希望能一次看到完整資訊」）
       ------------------------------------------------------------------
       主畫面只留**這張圖的命題**（三格電晶體）＋ 誰做的一句話 ＋ 四行誠實性標示；
       其餘四塊收進章節列，**預設收合、按了打得開**（`wireFolds`，MLCC 那張同一套）。
       收合後的高度 ＝ 第一條章節列的 y（492）＋ 四條列 × 46 ＋ 16 ＝ **692px**，
       1440×900 一個畫面看得完。

       ★ 為什麼「誰做的」只留一句在主畫面、細節收進第五段：
         `docs/diagram_purpose.md` R1／R4 要求「誰做的」與「台股沒人做的要明說」看得見，
         但那一整塊是 6 行、110px。折衷是**把結論留在主畫面**（台股只有 2330、
         7 檔裡有 4 檔不在資料裡），逐段名單收進章節 —— 資訊沒有不見，只是分兩層。

       viewBox 寫的是「全部展開」的高度；收合是 `wireFolds()` 在執行期改的，
       所以 JS 沒跑到的路徑（縮圖）吃到的仍然是一份座標正確的完整版面。
       ⚠ 章節列刻意不掛 data-seg —— 掛了的話點一下展開就順便把成分股篩掉了。*/
    const S1 = 492, S2 = 800, S3 = 1300, S4 = 1514;
    return `<svg class="dg dgm dgfd dg1" viewBox="0 0 ${W} 1724" width="100%" style="display:block">${D.STYLE}
      ${T(16, 24, '晶圓代工：一顆電晶體與一個製程迴圈', 'ttl')}
      ${T(16, 42, '三代電晶體改的都是同一件事 —— 閘極能管到通道的幾個面（1 → 3 → 4）。底下四段預設收起來，按標題列就打得開。', 'cap')}

      ${areaA()}

      ${T(16, 410, '★ 誰做的：先進節點（N3／N2／A16）台股只有 2330 台積電；族群 7 檔裡有 4 檔不在供應鏈資料裡 —— 逐段名單見第 ⑤ 段。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 430, '示意圖，非實物比例｜各層厚度與尺寸均為誇張放大', 'cap')}
      ${T(16, 446, '本圖講矽邏輯製程；化合物半導體（GaAs／SiC／GaN）代工見「第三代半導體」那張', 'cap')}
      ${T(16, 462, '本圖止於「一片做完的晶圓」；切割、封裝、測試見「傳統封裝與測試」那張', 'cap')}
      ${T(16, 478, '節點效能數字為媒體整理（2026），會過期；本圖不寫任何良率、成本、市占率與產能數字', 'cap')}

      <!-- ================= ② 尺度：晶圓 → 晶粒 → 電晶體，以及閘極堆疊（預設收合） ================= -->
      ${D.foldBar('fd2', S1, '② 尺度：晶圓 → 晶粒 → 電晶體，以及閘極堆疊',
      '12 吋晶圓俯視（notch、邊緣殘缺方格）、晶粒、閘極堆疊四層放大格')}
      <g class="dgbody" data-fold="fd2" data-y0="${S1 + 46}" data-y1="${S1 + 46 + 262}">
        <g transform="translate(0,${S1 + 46 - 510})">${areaB()}${areaB2()}</g>
      </g>

      <!-- ================= ③ 製程迴圈：九站走完回到第一站（預設收合） ================= -->
      ${D.foldBar('fd3', S2, '③ 製程迴圈：九站走完回到第一站，要繞 80～120 次',
      '閉合的九站環、每一站吃什麼材料、FEOL 與 BEOL 的先後')}
      <g class="dgbody" data-fold="fd3" data-y0="${S2 + 46}" data-y1="${S2 + 46 + 451}">
        <g transform="translate(0,${S2 + 46 - 777})">
          ${T(16, 790, '製程迴圈：每一個圖案層都要走一次這九站，走完回到第一站，再走下一層', 'hd')}
          ${T(16, 810, '順序不准對調：顯影在曝光之後、蝕刻在顯影之後、去光阻在蝕刻之後、CMP 在沉積與蝕刻之後。', 'sub')}
          ${T(16, 828, '外圈兩條弧：FEOL（電晶體本身）先做、BEOL（上面那幾十層金屬線）後做 —— 不能反過來。', 'sub')}
          ${ring()}${stepList()}
        </g>
      </g>

      <!-- ================= ④ 節點演進（預設收合） ================= -->
      ${D.foldBar('fd4', S3, '④ 節點演進：N5 → N3 → N2 → A16',
      '兩條分界線畫在哪裡；背面供電是 A16 的事，不是 N2 的事')}
      <g class="dgbody" data-fold="fd4" data-y0="${S3 + 46}" data-y1="${S3 + 46 + 165}">
        <g transform="translate(0,${S3 + 46 - 1271})">
          ${T(16, 1284, '節點演進：N5 → N3 → N2 → A16（時間往右）', 'hd')}
          ${areaD()}
        </g>
      </g>

      <!-- ================= ⑤ 這張圖上每一段台股是誰（預設收合） ================= -->
      ${D.foldBar('fd5', S4, '⑤ 這張圖上每一段台股是誰',
      '先進節點／成熟製程／化合物半導體代工各是誰，以及 4 檔的落差')}
      <g class="dgbody" data-fold="fd5" data-y0="${S4 + 46}" data-y1="${S4 + 46 + 148}">
        <g transform="translate(0,${S4 + 46 - 1440})">
          ${frame(16, 1452, 940, 92)}
          ${T(30, 1476, '這張圖上的段，台股是誰', 'hd')}
          ${T(30, 1498, '先進邏輯節點（N3／N2／A16）：2330 台積電（供應鏈資料的 tech 欄寫的是「N3/N2 先進製程, CoWoS-L, SoIC」）。', 'sub')}
          ${T(30, 1516, '成熟製程：2303 聯電、6770 力積電、5347 世界先進（5347 不在供應鏈資料裡）。6770 跟英特爾的關係不是邏輯製程代工，是供矽電容與矽中介層。', 'sub')}
          ${T(30, 1534, '化合物半導體代工：3105 穩懋、8086 宏捷科、4991 環宇-KY —— 跟本圖畫的矽邏輯製程不是同一件事，本圖不畫其結構。', 'sub')}
          ${T(16, 1566, '★ 本圖的「誰做的」取自供應鏈資料的「晶圓代工」環節（目前 3 家）；族群成分股有 7 檔 ——', 'sub', null, 'fill:var(--dg-warn)')}
          ${T(16, 1584, '　 另外 4 檔（5347 世界先進／3105 穩懋／8086 宏捷科／4991 環宇-KY）不在供應鏈資料裡，所以零件小卡列不出它們。那不是壞掉。', 'sub', null, 'fill:var(--dg-warn)')}
        </g>
      </g>
    </svg>`;
  }

  window.DG.register('foundry', {
    level: 'group', chain: 'semiconductor',
    name: '晶圓代工：一顆電晶體與一個製程迴圈',
    draw: foundryProcess, native: 980, scene: null,
    q: '一顆電晶體從平面變成 FinFET 再變成 GAA，到底改了什麼？為什麼一片晶圓要繞同一個迴圈幾百次？N3 跟 N2 差在哪？',
    /* `parts` ＝點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       規則（§7-E）：`cos` **只准放真的在 supply_chain.yaml 裡的代號**（查不到就靜靜消失，
       比寫錯更難發現）；那四檔不在資料裡的族群成分股一律寫進 `none:` 的文字。*/
    parts: {
      fd_planar: {
        name: '平面電晶體的通道',
        desc: '通道是基板表面下一條水平的薄層，閘極只從正上方蓋下來 —— 只管得到一面，其餘三面關不住。',
        none: '平面電晶體是所有代工廠都做過的世代，這一格講的是結構演進的起點，不是某一家的產品。',
      },
      fd_fin: {
        name: '鰭（fin）',
        desc: '把通道立起來變成一片直立的鰭，閘極就能罩住頂面與兩個側面 —— 三面。圖上鰭高畫成鰭寬的 4.75 倍；這是畫面可辨識性的下限，不是真實比例的宣稱。',
        none: 'FinFET 世代的先進節點在台股由 2330 台積電承擔（供應鏈資料 tech：N3/N2 先進製程）；5347 世界先進是成熟製程代工、不在供應鏈資料的晶圓代工環節裡，所以這張小卡列不出它。',
      },
      fd_sti: {
        name: '淺溝槽隔離（STI）',
        desc: '填在鰭與鰭之間的下半段，只淹到鰭的下部。被它埋住的那一段鰭，閘極包不到 —— 那就是 FinFET 走到盡頭的地方。',
      },
      fd_gaa: {
        name: '閘極金屬（填進每一片之間）',
        desc: '★ 這是「Gate-All-Around」這個名字的全部意義：金屬不只在最上面那片的上方，而是填進每一對相鄰奈米片之間的縫，最下面那片的下方也有。只畫在最上面＝畫的是 FinFET。',
        cos: ['2330'],
        none: 'GAA 奈米片節點（N2）目前在台股只有 2330 台積電做得到。這不是市占宣稱，是「誰有這個節點」的事實陳述；沒有查到任何良率或產能數字，所以這裡不寫。',
      },
      fd_sheet: {
        name: '奈米片（nanosheet）',
        desc: '2～4 片水平堆疊、彼此不相連；片寬遠大於片厚（本圖 8 倍）—— 正方形斷面那是奈米線（nanowire），不是奈米片。片寬可以調：要速度就加寬、要省電就變窄（NanoFlex，示意）。',
        cos: ['2330'],
        none: 'GAA 奈米片節點（N2）目前在台股只有 2330 台積電做得到。',
      },
      fd_flex: {
        name: '可變片寬（NanoFlex，示意）',
        desc: '同一個元件庫裡片寬可以不同：加寬換速度、變窄換省電。可以調到多寬多窄、一個庫裡有幾種片寬，查到的摘要沒有講，所以圖上只畫寬窄兩疊，不寫任何數字。',
        cos: ['2330'],
        none: '這是 N2／A16 世代的元件設計手段，台股走到這個節點的只有 2330 台積電。',
      },
      fd_gate: {
        name: '閘極（ㄇ 字形／全包覆）',
        desc: '平面只蓋在通道上方、FinFET 罩住鰭的三面、GAA 包住每一片的四面 —— 三格改的都是同一件事：閘極能管到幾個面。',
      },
      fd_gate_stack: {
        name: '閘極堆疊（high-k／金屬閘）',
        desc: '由下到上：界面層 → high-k 介電層 → 功函數金屬 → 填充金屬。先進節點早就不是「二氧化矽＋複晶矽」了，畫成複晶矽閘等於畫二十年前的結構。',
        none: '閘極堆疊的材料不是代工廠自己做的 —— 前驅物與靶材見「前段製程材料」那張。這一層的材料台股有做，但不在這一格。',
      },
      fd_hk: {
        name: '閘極介電層',
        desc: '全圖最薄的層之一。平面與 FinFET 是沿著通道表面貼一層；GAA 是繞著每一片走一圈（每片外圍一個封閉的細框）。',
        none: '介電層的前驅物（high-k 的金屬有機源）不是代工廠自己做的，見「前段製程材料」那張。',
      },
      fd_spacer: {
        name: '間隙壁（spacer／inner spacer）',
        desc: '把閘極跟源／汲擋開。GAA 的內間隙壁在每一片的兩端，夾在閘極金屬與源汲磊晶之間 —— 沒有它，閘極會跟源汲短路。',
      },
      fd_sd: {
        name: '源極／汲極（S／D）',
        desc: '一律在通道的左右兩端。GAA 那格的源汲磊晶把所有奈米片的端部一起接起來，不是一片接一個。FinFET 與 GAA 畫的是垂直於鰭／片的橫剖面，源汲嚴格說不在這個切面上 —— 圖上畫在兩端是示意。',
      },
      fd_sub: {
        name: '矽基板',
        desc: '三格共用同一塊基板、同一個位置、同一個顏色 —— 三格的意義就在「可以互相比較」，用不同畫法讀者就無法比較。',
        none: '這張圖的起點（一片空白晶圓）是上一張圖的終點。做 12 吋晶圓的台股是 6488 環球晶／5483 中美晶／6182 合晶／3532 台勝科／8028 昇陽半導體 —— 這五家全部不在供應鏈資料裡，見「矽晶圓：從熔湯到一片鏡面」那張。',
      },
      fd_fin_iso: {
        name: '等角輔助圖：閘極橫跨過鰭',
        desc: '一條長鰭橫躺、閘極橫跨過去。它只是幫忙把「三面包覆」這件事立體化，刻意畫成灰階、不搶主角。',
      },
      fd_face1: { name: '閘極控制面：1 面', desc: '平面電晶體的閘極只從上方蓋下來。管得越少面，漏電越關不住。' },
      fd_face3: { name: '閘極控制面：3 面', desc: 'FinFET 的閘極罩住鰭的頂面與兩個側面 —— 鰭底那一段埋在 STI 裡，管不到。' },
      fd_face4: { name: '閘極控制面：4 面', desc: 'GAA 的閘極金屬鑽進每一片之間，上下左右四面都管得到。管得越多面，同樣速度下越省電。' },
      fd_loop: {
        name: '製程迴圈（繞 80～120 次）',
        desc: '晶圓廠不是「一次做完」，是同一個迴圈繞好幾十次：每一個圖案層都要走一次清洗 → 沉積 → 塗光阻 → 曝光 → 顯影 → 蝕刻 → 去光阻 → CMP → 量測。層數與光罩數是區間、來源是業界整理，不是某一個節點的確定值。',
        none: '整個迴圈是晶圓代工廠自己在廠內跑的。迴圈上每一站吃的材料與用的機台分別是另外兩張圖（前段製程材料／晶圓廠機台）。',
      },
      fd_clean: { name: '第 1 站 清洗', desc: '每一輪的開頭與結尾都要洗。吃高純度化學品與超純水。' },
      fd_depo: { name: '第 2 站 沉積', desc: '長出這一層的材料（CVD／ALD／PVD 濺鍍）。PVD 吃靶材，CVD／ALD 吃前驅氣體。' },
      fd_resist: { name: '第 3 站 塗光阻', desc: '★ 先塗底部抗反射層（BARC），再塗光阻 —— BARC 是「底部」抗反射層，畫在光阻上面就是上下顛倒。' },
      fd_litho: {
        name: '第 4 站 曝光',
        desc: '把光罩上的圖案投影下來。DUV 193 nm／EUV 13.5 nm；EUV 只用在最關鍵的那幾層，其餘仍是 DUV。',
        none: '曝光機（DUV／EUV）由 ASML（荷）獨家供應 EUV，台股沒有廠商做曝光機。台股在這一段做的是耗材與零組件（光阻、BARC、EBR、光罩傳送盒）—— 見「前段製程材料」與「晶圓廠機台」那兩張。',
      },
      fd_dev: { name: '第 5 站 顯影', desc: '把曝到光的（或沒曝到的）洗掉，光阻變成罩幕。一定在曝光之後 —— 反了就是「先洗掉再曝光」。' },
      fd_etch: { name: '第 6 站 蝕刻', desc: '照著光阻的洞往下刻。一定在顯影之後 —— 光阻顯影完才是罩幕，先蝕刻就沒有罩幕可用。' },
      fd_strip: { name: '第 7 站 去光阻', desc: '光阻用完就拔掉。一定在蝕刻之後 —— 蝕刻之前把光阻拔掉等於整片被刻光。' },
      fd_cmp: {
        name: '第 8 站 CMP（化學機械研磨）',
        desc: '把這一層磨平，下一層才有平的地方站。一定在沉積與蝕刻之後、下一輪塗光阻之前。',
        none: 'CMP 這一站吃的鑽石碟由 1560 中砂做（信心：中，來源為投顧與產業媒體整理）。★ 1560 不在供應鏈資料裡，所以小卡列不出它 —— 這裡用文字補。',
      },
      fd_metro: { name: '第 9 站 量測檢測', desc: '量厚度、量線寬、找缺陷。本圖只畫製程步驟，不畫任何機台外觀 —— 機台是「晶圓廠機台」那張。' },
      fd_feol: { name: 'FEOL（前段）', desc: '做電晶體本身。FEOL 做完才做 BEOL，不能反過來。' },
      fd_beol: { name: 'BEOL（後段）', desc: '做上面那幾十層金屬線。它跟 FEOL 走的是同一個迴圈，只是層的內容不同。' },
      fd_wafer: {
        name: '12 吋晶圓俯視',
        desc: '圓形加上一個 notch 與規則排列的方格。邊緣那一圈切不出完整晶粒（圖上顏色較暗的格子）—— 晶圓越大，浪費掉的邊緣比例越小。格數為示意，實際數量視晶粒大小而定。',
        none: '這張圖的起點是一片空白晶圓。做 12 吋晶圓的台股是 6488 環球晶／5483 中美晶／6182 合晶／3532 台勝科／8028 昇陽半導體 —— 五家全部不在供應鏈資料裡，見「矽晶圓：從熔湯到一片鏡面」那張。',
      },
      fd_die: { name: '一顆晶粒', desc: '晶圓上被切線分開的一格。同一個缺陷密度下，晶粒越大、報廢的比例越高（只寫關係，本圖不寫任何良率數字）。' },
      fd_zoom: { name: '放大到一顆電晶體', desc: '從晶圓到晶粒再到電晶體，三級之間差七個數量級（300 mm 對 nm）。所以這張圖一律是誇張放大的示意。' },
      fd_node: {
        name: '節點演進 N5 → N3 → N2 → A16',
        desc: 'N3 是最後一代 FinFET、N2 是第一代 GAA，分界線畫在 N3 與 N2 之間。背面供電（Super Power Rail）是 A16 的事，不是 N2 的事 —— N2 仍是正面供電，畫錯是可以查證的事實錯誤。',
        note: 'A16 的放量時程各家說法不一（原廠技術頁寫 2026 下半年製程就緒，媒體一邊說 2026 年底量產、一邊說遞延到 2027）。所以畫面上只寫「製程就緒」與「說法不一」，不挑一個當定論。',
        none: '節點路線圖是產業的共同路線，不是任何一家的產品規劃。台股走到 GAA 的只有 2330 台積電。',
      },
    },
  });
})();
