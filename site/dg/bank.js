/* 銀行金融：錢從存款進來、從放款出去，中間那一段就是利差 —— 族群 `bank`（financial 鏈）

   ★ 型式：純 2D（`scene: null`）。**Andy 2026-09-23 指定金融這一鏈只要 2D**
     （原話：「金融麻煩也生成 2D 圖」，格式跟軟體鏈那四張一樣、不用 3D）。
     金融沒有實體零件可以繞著看 —— 這張圖畫的是「錢從哪裡來、經過誰、賺在哪一段」，
     轉一圈不會多理解任何一件事。要改成 3D 就是重新決定題目，不准實作時順手加。

   ★ 風格基準 ＝ AI 伺服器鏈的族群圖（`site/dg/server_psu.js`／`liquid_cooling.js`／
     `switch_wireless.js`），做法直接沿用同鏈路的 `site/dg/cyber_security.js`：
     svg 根掛 `rs` → 說明卡片由 `externalize()` 搬成 HTML（.dgc）排進畫布左右兩欄；
     材質走共用的 `D.fx`；字級吃 `--dg-fs-*`（12px 下限）、行距 16px；
     顏色一律 `--dg-*` token，JS 裡一個色碼都沒有。`native` 660。

   ★ 這張圖回答的問題（`q`）：銀行賺的是什麼？利率變動時哪一段會先動？
     骨架就是照這個問題長出來的，分三段：
       ① 主體＝利差：左邊資金來源（成本）→ 中間利差引擎 → 右邊資金運用（收益）。
          **第二條腿（手續費收入）刻意畫成一條不經過利差引擎的獨立橫帶** ——
          它不佔資產負債表、不吃資本，跟利差是兩種生意，混在一起畫就看不出「兩條腿」。
       ② 稅前獲利的加減式：利息淨收益 ＋ 手續費淨收益 ＋ 金融資產評價 − 信用成本 − 營業費用。
          把「信用成本」畫成減項，是因為它正是利差故事的反面（升息賺利差、同時推高倒帳風險）。
       ③ 升息的時間差（收合章節①）：資產端先重訂價、負債端落後，中間那段就是淨利差擴張的窗口。
          這一段是他點名要的（「利率變動時哪一段會先動」），所以單獨給一個章節、畫成時間軸。

   ★ `data-seg`（2026-09-23 更新，批次 0923-C／C9）：**掛上了**。
     這張圖剛做出來時 `supply_chain.yaml` 裡完全沒有 financial 這條鏈，所以一個都不敢掛。
     Andy 2026-09-23 授權補資料（「若缺資料網路找，CEO 安排」），環節補上之後這裡跟著掛：
       環節 ＝ `fin_bank`（銀行與銀行金控），成分 ＝ groups.yaml 的 bank 族群 16 檔。
     ⚠ 整張圖只有一個環節（見下面 `part()` 的註解），所以點任何零件篩出來的清單都一樣 ——
       那是題目的形狀，不是缺陷。
     ⚠ 金融鏈在 `supply_chain.yaml` 裡**一條邊都沒有**：那份 schema 只有
       supplies／outsources_to／designated_by／produced_by 四種關係，沒有一種表達得了「資金中介」。
       理由逐字寫在 YAML 的 fin_bank 那一段上面。

   ★ 事實與出處（畫面上只寫查得到、而且不只一個來源講得出來的；其餘標示意）
     · 成分與定位：`pipeline/groups/groups.yaml` 的 `bank.note` ——
       「以銀行子公司為主要獲利來源的金控與純銀行股；估值用股價淨值比＋ROE，不用本益比」
       （`valuation_metric: pb_roe`）。畫面上的估值那一段就是照這一條寫的。
     · 2887 台新新光金留在這一格的理由：groups.yaml 的行內註解逐字寫著
       「雖然併入新光金之後壽險部位變大，但實測它對銀行六大的殘差相關中位 +0.42、
        對富邦／國泰只有 +0.36 —— 現在的資金還是把它當銀行股在買」。這是本專案自己的實測，
       畫面上據實標成「本站分群的實測結論」，不冒充公司或媒體的說法。
     · 升息時放款端先動、存款端落後：央行〈我國銀行存放款利差減少原因剖析與因應對策〉
       （cbc.gov.tw 的專題研究）與多家媒體／投顧的 NIM 解讀一致講的是同一個機制 ——
       浮動利率放款按指數利率定期重訂價，定期存款要到期換約才換到新利率。
       **時間長度（幾個月）各家寫法不同，所以畫面上一個月數都不寫，只畫先後順序。**
     · 手續費收入的組成（財富管理、信用卡、聯貸與承銷、信託保管）：金控季報的收入分類通用口徑。
     不寫的：NIM 的百分點數字、逾放比、覆蓋率、各家市占。
       ⚠ 工商時報 2026-09-07 有「第二季本國銀行存放利差維持在 1.37 個百分點的高檔」，
         但那是單一來源、而且是會逐季變動的時點數字 —— 依批次規格第 5 條，
         **畫面上不印，留在這裡備查**。要用請自己回去查當期的央行／金管會統計。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  const CW = 660;

  /* ---------------- 小工具（跟 cyber_security.js 同一套寫法，沒有第二套介面） ---------------- */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const LN = (d, col, w2, extra) => `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  /* ★ 2026-09-23（批次 0923-C／C9）：financial 鏈的環節補進 `supply_chain.yaml` 之後，
     這張圖的零件掛得上 `data-seg` 了 —— 環節 ＝ `fin_bank`（銀行與銀行金控），
     成分 ＝ groups.yaml 的 bank 族群那 16 檔。
     ★ 這張圖**整張只有一個環節**，那是對的不是偷懶：圖上每一塊（存款、放款、手續費、
       加減項、升息時間差、估值）講的都是**同一批公司自己的資產負債表與損益表**，
       不像半導體鏈那樣一格一格換公司。`stampParts()` 會因此自動補上 `.dg1`
       （跟 MLCC 那張圖同一條路），所以點不同零件時「被點的那一個最強、同環節其餘次強」
       的兩層高亮仍然成立。*/
  const SEG = 'fin_bank';
  const segOf = () => SEG;
  const part = (id, inner) => `<g data-part="${id}"${segOf(id) ? ` data-seg="${segOf(id)}"` : ''}>${inner}</g>`;

  /* 元件色（卡片 data-dgcolor ＋ 編號圓點 ＋ 引線端點共用），全部是 index.html 既有的 token。
     語意：負債／成本側走冷色（--dg-cold），資產／收益側走暖色（--dg-au 金），
     利差本體用主強調色，手續費那條腿用有機色（跟利差明顯分開），減項用警示與錯誤色。
     ⚠ 淺色主題下 --dg-steel 與 --dg-au 這兩個 token **當文字對白底只有 2:1 上下**，
       所以這兩個 token 只留給填色、描邊與卡片色條（那幾條共用 CSS 有自己的淺色處理），
       「直接當 SVG 文字的 fill」一律改走 --dg-mute／--dg-pwr。*/

  const C = {
    cost: 'var(--dg-cold)', yield_: 'var(--dg-au)', nim: 'var(--dg-accent-2d)',
    fee: 'var(--dg-organic)', risk: 'var(--dg-err)', opex: 'var(--dg-mute)',
    cap: 'var(--dg-steel)', warn: 'var(--dg-warn)', hot: 'var(--dg-hot)', yieldTx: 'var(--dg-pwr)',
  };
  const card = (o) => {
    // seg 也要傳給卡片：卡片本身就是一個零件節點，沒傳的話點圖會篩、點旁邊那張卡卻不會。
    const s = extRow({ part: o.part, seg: segOf(o.part), title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ ① 負債端：錢從哪裡來（左欄）
     由上往下＝資金成本由低到高。**排序本身就是資訊**：活存最便宜、同業拆借最貴也最快跟著市場動。
     右端的「重訂價」標記是為了替章節①（升息時間差）先埋伏筆 —— 慢／快在這裡就看得到。*/
  const LX = 20;                                    // 全寬那幾排（手續費、加減式、註解）的左緣
  /* ★ 2026-09-26 覆蓋普查（scripts/_dg_overlap.py）：長條原本 38 高、說明與右邊「快／慢」小格擠在同一行，
     閱讀模式字一大，說明就鑽到小格底下（互疊 6px）。長條加高到 52：標題一行、說明一行，小格移到右上角。
     中間的利差引擎跟著往下，對齊兩側長條；下面的手續費、加減式跟著算出來的 y 走。*/
  const BX = 34, LW = 176, BH = 52, BG = 8, BY0 = 86;
  const BARS_B = BY0 + 4 * BH + 3 * BG;               // 兩側長條的下緣  // 負債欄的長條：左緣退到 34，錨點才站得進 20 那一欄
  const SRC = [
    { id: 'bk_demand', t: '活期存款（活儲）', s: '成本最低，量也最大', k: '慢', col: C.cost },
    { id: 'bk_time', t: '定期存款', s: '成本較高，到期才換約', k: '慢', col: C.cost },
    { id: 'bk_wholesale', t: '同業拆借與金融債', s: '直接跟著市場利率走', k: '快', col: C.hot },
    { id: 'bk_equity', t: '自有資本', s: '不用付息，要求 ROE', k: '—', col: C.cap },
  ];

  /* ================================================================ 資產端：錢往哪裡去（右欄）
     由上往下＝收益由低到高，同時風險也由低到高。企業放款與房貸多為浮動利率 → 重訂價「快」。*/
  const RX = 450, RW = 176;
  const USE = [
    { id: 'bk_bond', t: '債券與票券投資', s: '收益低，但流動性好', k: '慢', col: C.cap },
    { id: 'bk_mortgage', t: '房貸', s: '跟指數利率連動', k: '快', col: C.yield_ },
    { id: 'bk_corp', t: '企業放款', s: '浮動利率，定期重訂價', k: '快', col: C.yield_ },
    { id: 'bk_consumer', t: '消金與信用卡', s: '利率最高，風險也最高', k: '快', col: C.risk },
  ];

  const bar = (o, x, y, w) => part(o.id,
    fx.glass(x, y, w, BH, { fill: o.col, cls: 'part', rx: 5 })
    + T(x + 11, y + 20, o.t, 'lbl')
    + T(x + 11, y + 40, o.s, 'sub', null, 'fill:var(--dg-ink)')
    + R(x + w - 28, y + 6, 22, 20, 'var(--dg-step-f)', 'part', 4)
    + T(x + w - 17, y + 21, o.k, 'sub', 'middle', `fill:${o.k === '快' ? C.hot : C.opex}`));

  /* ================================================================ 中間：利差引擎
     兩條橫線（上＝資產收益率、下＝資金成本率）＋ 中間填色的帶子＝淨利差。
     ★ 刻意不標任何百分比：NIM 是逐季變動的時點數字，印上去隔天就過期（檔頭 §事實 最後一條）。*/
  const MX = 220, MW = 220, MY = 96, MH = BARS_B - 96;   // 上緣讓開兩側的欄標題，下緣對齊長條

  function engine() {
    const yTop = MY + 104, yBot = MY + 174;         // 收益率線 / 成本率線
    const g = [frame(MX, MY, MW, MH), T(MX + 13, MY + 24, '銀行：利差引擎', 'hd'),
      T(MX + 13, MY + 42, '把短天期、低成本的錢，', 'sub'),
      T(MX + 13, MY + 58, '換成長天期、較高收益的資產', 'sub')];
    // 淨利差帶（上下兩線之間）
    g.push(part('bk_nim', R(MX + 16, yTop, MW - 32, yBot - yTop, 'var(--dg-frame-f)', 'part', 6)
      + LN(`M${MX + 16},${yTop} H${MX + MW - 16}`, C.yield_, 2.4)
      + LN(`M${MX + 16},${yBot} H${MX + MW - 16}`, C.cost, 2.4)
      + T(MX + 18, yTop - 6, '資產收益率（放款＋投資）', 'sub', null, `fill:${C.yieldTx}`)
      + T(MX + 18, yBot + 16, '資金成本率（存款＋拆借）', 'sub', null, `fill:${C.cost}`)
      + LN(`M${MX + 28},${yTop + 4} V${yBot - 4}`, C.nim, 1.4, ' stroke-dasharray="4 4"')
      + T(MX + MW / 2, yTop + 24, '淨利差', 'lbl', 'middle', `fill:${C.nim}`)
      + T(MX + MW / 2, yTop + 42, '這一段乘上資產規模', 'sub', 'middle')
      + T(MX + MW / 2, yTop + 58, '＝ 利息淨收益', 'sub', 'middle', `fill:${C.nim}`)));
    // 左右進出的光束（左：資金流入；右：資金投出）
    g.push(fx.beams(SRC.map((s, i) => ({ d: `M${BX + LW},${BY0 + i * (BH + BG) + BH / 2} H${MX}`, color: C.cost, w: 1.6 })), { flow: true }));
    g.push(fx.beams(USE.map((s, i) => ({ d: `M${MX + MW},${BY0 + i * (BH + BG) + BH / 2} H${RX}`, color: C.yield_, w: 1.6 })), { flow: true }));
    return g.join('');
  }

  /* ================================================================ ② 第二條腿：手續費收入
     **刻意畫成一條橫跨整張圖、不經過利差引擎的獨立帶子**：它不佔用資產負債表、不吃資本適足，
     跟利差是兩種生意。看得出「兩條腿」，才解釋得了「為什麼有些金控在低利率時代還能長獲利」。*/
  /* ★ 2026-09-26 覆蓋普查：四格的編號原本疊在說明那一行的右端（把說明尾巴蓋掉），
     引線又沿著編號的高度橫著劃過整排字 —— 編號改放在四格的下緣（框內那條留白），引線就只走留白。*/
  const FY = BARS_B + 20, FEE = [
    { id: 'bk_fee_wm', t: '財富管理', s: '基金與保險通路費' },
    { id: 'bk_fee_card', t: '信用卡', s: '刷卡與循環利息' },
    { id: 'bk_fee_syn', t: '聯貸與承銷', s: '安排費，按案子走' },
    { id: 'bk_fee_trust', t: '信託與保管', s: '按受託資產規模收' },
  ];

  function fees() {
    const g = [frame(LX, FY, 620, 74), T(LX + 14, FY + 22, '第二條腿：手續費收入 —— 不佔資產負債表、不吃資本', 'hd', null, `fill:${C.fee}`)];
    const w = 143;
    FEE.forEach((f, i) => {
      const x = LX + 12 + i * (w + 8);
      g.push(part(f.id, R(x, FY + 30, w, 34, 'var(--dg-step-f)', 'part', 6)
        + R(x, FY + 30, 3, 34, C.fee)
        + T(x + 11, FY + 45, f.t, 'lbl')
        + T(x + 11, FY + 59, f.s, 'sub')));
    });
    return g.join('');
  }

  /* ================================================================ ③ 稅前獲利的加減式（永遠看得到）
     ★ 刻意不畫比例：各家的收入結構逐季在變，畫成堆疊圖就是編一個比例出來。
       這一排只講「哪些是加項、哪些是減項」，以及每一項被什麼推動。
     信用成本放在這裡是有意的 —— 它是利差故事的反面：升息賺到利差的同時，借款人的還款壓力也上去。*/
  const PY = FY + 74 + 34, PIT = [
    { id: 'bk_pl_nii', s: '＋', t: '利息淨收益', d: ['利差（價）×', '資產規模（量）'], col: C.nim },
    { id: 'bk_pl_fee', s: '＋', t: '手續費收益', d: ['市場情緒', '與消費力'], col: C.fee },
    { id: 'bk_pl_mkt', s: '＋', t: '資產評價', d: ['自有部位的', '債與股市價'], col: C.cap },
    { id: 'bk_pl_credit', s: '－', t: '信用成本', d: ['呆帳提存：', '景氣的反面'], col: C.risk },
    { id: 'bk_pl_opex', s: '－', t: '營業費用', d: ['人事、通路、', '系統'], col: C.opex },
    { id: 'bk_pl_pbt', s: '＝', t: '稅前淨利', d: ['除以淨值', '＝ ROE'], col: C.yield_ },
  ];

  /* ★ 2026-09-26 覆蓋普查：六格各 96 寬，「＋ 利息淨收益」排同一行、說明一行 7 個字，閱讀模式伸出格子 9～14px、
     還壓進隔壁那格。改成：符號一行、項目名一行、說明照最壞字寬斷行，格高取最高那格。*/
  const PW = 96, PIN = PW - 16;
  const PP = PIT.map((q) => D.para(0, 0, q.d.join(''), PIN, { lh: 17 }));
  const PH = Math.max(76, Math.max.apply(null, PP.map((q) => 60 + q.h + 2)));
  function pnl() {
    const g = [T(LX, PY - 10, '這一格的錢最後怎麼變成獲利：三個加項、兩個減項', 'hd')];
    PIT.forEach((p, i) => {
      const x = LX + i * (PW + 8.8);
      g.push(part(p.id, R(x, PY, PW, PH, 'var(--dg-frame-f)', 'part frame', 8)
        + R(x, PY, 3, PH, p.col)
        + T(x + 11, PY + 20, p.s, 'lbl', null, `fill:${p.col}`)
        + T(x + 11, PY + 40, p.t, 'lbl')
        + D.para(x + 11, PY + 60, p.d.join(''), PIN, { lh: 17 }).svg));
    });
    return g.join('');
  }

  /* ================================================================ 章節①：升息時，哪一段先動
     Andy 這張圖的問題有一半在這裡，所以單獨給一個章節、畫成時間軸而不是文字。
     機制（央行專題研究與多家 NIM 解讀一致）：
       · 資產端：浮動利率放款按指數利率／基準利率定期重訂價 → 跟著升息往上，反應快。
       · 負債端：活存利率調幅小、定存要到期換約才換到新利率 → 落後，反應慢。
     所以升息初期會出現一段「收益先上、成本還沒上」的窗口，淨利差暫時擴張；
     等存款陸續換約完，成本補上來，利差就回吐。降息時整個順序反過來。
     ⚠ **不畫任何月數與百分點**：各家寫法不同（檔頭 §事實），畫面只保證「先後順序」這件事。*/
  function areaRepricing() {
    const y0 = 546, x0 = 34, w = 340, h = 150, base = y0 + h;
    const px = (k) => x0 + 22 + k * ((w - 44) / 4);
    // 資產端：階梯往上（快）
    const aPts = [[0, 0], [1, 0], [1, 34], [2, 34], [2, 58], [3, 58], [3, 70], [4, 70]];
    const lPts = [[0, 0], [1.6, 0], [1.6, 16], [2.6, 16], [2.6, 44], [3.4, 44], [3.4, 62], [4, 62]];
    const toD = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${px(p[0]).toFixed(1)},${(base - 26 - p[1]).toFixed(1)}`).join(' ');
    const band = `${toD(aPts)} L${px(4)},${base - 26 - 62} ` + lPts.slice().reverse().map(p => `L${px(p[0]).toFixed(1)},${(base - 26 - p[1]).toFixed(1)}`).join(' ') + ' Z';
    /* ★ 2026-09-26 覆蓋普查：曲線右端的「資產端／負債端」原本伸出框 11px；框往右加寬 44 把它們收進來，
       右欄兩段說明跟著右移、改成照最壞字寬斷行；最底下那行長圖說（伸出畫布 680px）斷成幾行。*/
    const g = [D.para(LX, y0 - 12 - 21, '升息之後：資產端先動、負債端落後 —— 中間那段就是淨利差擴張的窗口', 620, { cls: 'hd', fs: 18.5, lh: 21 }).svg,
      frame(x0 - 14, y0, w + 28 + 44, h + 30),
      `<path d="${band}" fill="${C.nim}" fill-opacity="var(--dg-chg-a,.12)"/>`,
      LN(`M${x0 + 8},${base - 20} H${x0 + w - 12}`, 'var(--dg-axis)', 1),
      LN(toD(aPts), C.yield_, 2.4),
      LN(toD(lPts), C.cost, 2.4, ' stroke-dasharray="6 5"'),
      T(px(4) + 6, base - 26 - 70, '資產端', 'sub', null, `fill:${C.yield_}`),
      T(px(4) + 6, base - 26 - 56, '負債端', 'sub', null, `fill:${C.cost}`),
      T(x0 + 22, base - 4, '升息', 'sub', 'middle'),
      T(px(2), base - 4, '之後', 'sub', 'middle'),
      T(px(4), base - 4, '換約完', 'sub', 'middle'),
      T(x0 + 8, y0 + 22, '縱軸＝利率水準（相對，不標刻度）', 'sub'),
    ];
    g.push(part('bk_gap', R(px(1) - 2, y0 + 34, px(2.6) - px(1) + 4, h - 46, 'transparent', 'part', 6)
      + LN(`M${px(1)},${y0 + 40} V${base - 26}`, C.nim, 1, ' stroke-dasharray="3 4"')
      + LN(`M${px(2.6)},${y0 + 40} V${base - 26}`, C.nim, 1, ' stroke-dasharray="3 4"')
      + T((px(1) + px(2.6)) / 2, y0 + 52, '利差擴張的窗口', 'lbl', 'middle', `fill:${C.nim}`)));

    // 右欄：兩段文字解釋為什麼會有時間差、以及降息時反過來
    const bx = 448, bw = 192, bin = bw - 24;
    const T1 = '企業放款與房貸多為浮動利率，按指數利率定期重訂價 —— 升息一段時間內就跟著調上去。';
    const T2 = '活存利率調幅小；定期存款要到期換約，才換到新的較高利率。所以成本是「陸續」補上來的。';
    const q1 = D.para(0, 0, T1, bin, { lh: 17 }), q2 = D.para(0, 0, T2, bin, { lh: 17 });
    const bh = Math.max(86, 42 + Math.max(q1.h, q2.h));
    const blk = (i, t, text, id, col) => {
      const by = y0 + i * (bh + 10);
      return part(id, frame(bx, by, bw, bh) + R(bx, by, 3, bh, col)
        + T(bx + 13, by + 22, t, 'lbl')
        + D.para(bx + 13, by + 42, text, bin, { lh: 17 }).svg);
    };
    g.push(blk(0, '為什麼資產端快', T1, 'bk_fast', C.yield_));
    g.push(blk(1, '為什麼負債端慢', T2, 'bk_slow', C.cost));
    const yb = Math.max(y0 + h + 30, y0 + 2 * bh + 10);
    return g.join('') + D.para(LX, yb + 26,
      '示意圖，非實物比例｜曲線只表示先後順序與方向，縱軸不標刻度、橫軸不標月數 —— 各家重訂價週期與存款結構不同，時間長度沒有可引用的統一數字。降息時整個順序反過來：資產端先掉、成本落後，利差先被壓縮。', 620, { cls: 'cap' }).svg;
  }

  /* ================================================================ 章節②：估值、誰在這一格、沒回答的事 */
  function areaWho() {
    const y0 = 820, BW = 300, BIN = BW - 28;
    const warn = (t) => ({ t, style: /^★/.test(t) ? `fill:${C.warn}` : '' });
    // ★ 2026-09-26 覆蓋普查：兩格原本照 12px 寫死斷行（一行 18～22 個字），閱讀模式伸出格子；改成整段照最壞字寬重斷
    const L1 = ['銀行的獲利是「淨值 × ROE」長出來的，淨值本身就是可比的基準，所以市場給的是 PB（股價 ÷ 每股淨值），再用 ROE 決定應該給幾倍 PB —— ROE 高的享有較高 PB。',
      '本站的 groups.yaml 把這一格的 valuation_metric 設成 pb_roe，就是這個理由。',
      '★ 用本益比會被單季的評價損益與呆帳提存扭曲，季與季之間不可比。'].map(warn);
    const L2 = ['依 groups.yaml 的定義：以銀行子公司為主要獲利來源的金控，以及純銀行股。',
      '同樣掛「金融」，壽險金控與證券金控被拆到另外兩格 —— 因為驅動力不同：銀行看利差與放款，壽險看利率與匯率，券商看成交量。三者不該混在一起看。',
      '★ 2887 台新新光金仍留在銀行這一格：本站實測資金仍把它當銀行股在買。'].map(warn);
    const p1 = D.para(0, 0, L1, BIN), p2 = D.para(0, 0, L2, BIN);
    const BH2 = Math.max(p1.h, p2.h) + 48 + 6;
    const box = (i, t, list, id, col) => {
      const x = LX + i * 316;
      return part(id, frame(x, y0, BW, BH2) + R(x, y0, 3, BH2, col)
        + T(x + 14, y0 + 24, t, 'lbl')
        + D.para(x + 14, y0 + 48, list, BIN).svg);
    };
    const NO = ['淨利差的百分點、逾放比、覆蓋率、各家市占 —— 都是逐季變動的時點數字，印在圖上隔天就過期，一個都不寫。',
      '各家的手續費收入占比：各家財報的分類口徑不完全一致，沒有可以直接並排比較的公開數字，所以只畫「有哪幾塊」不畫比例。',
      '升息到淨利差擴張要多久：各家重訂價週期與存款結構不同，查不到可引用的統一數字，所以只畫先後順序。',
      '這 16 檔誰快誰慢：圖上畫的是銀行這門生意的通則，不是任何一家的資產負債結構。'];
    const fy = y0 + BH2 + 16;
    const np = D.para(LX + 14, fy + 46, NO, 620 - 28);
    return D.para(LX, y0 - 12 - 21, '為什麼銀行股看股價淨值比（PB）＋ROE，不看本益比', 620, { cls: 'hd', fs: 18.5, lh: 21 }).svg
      + box(0, '估值：資產負債表就是它的生意', L1, 'bk_val', C.cost)
      + box(1, '這一格收的是哪一種公司', L2, 'bk_scope', C.nim)
      + frame(LX, fy, 620, 46 + np.h)
      + T(LX + 14, fy + 24, '這張圖沒有回答的事', 'lbl')
      + np.svg;
  }

  function bank() {
    return `<svg class="dg dgm rs dgbk" viewBox="0 0 ${CW} 1180" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（見 DECISIONS 第 231 條）。
           ★ 2026-09-23：掛上 data-seg 的零件改吃 diagrams.js 那一整組「.dg [data-seg] …」
           （環節色、hover、.sel／.sel-part），所以這裡的規則全部縮到 :not([data-seg])——
           不縮的話它的選擇器比較強，會把環節色整個蓋掉，等於白掛。*/
        svg.dgbk [data-part]:not([data-seg]) .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgbk [data-part]:not([data-seg]){cursor:default}
        svg.dgbk [data-part]:not([data-seg]):hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgbk [data-part]:not([data-seg]).sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgbk .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgbk .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>

      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">銀行金融：利差是主體，手續費是第二條腿</text>
      <text class="cap ext" x="0" y="0">左邊是錢從哪裡來（存款與拆借，這是成本），右邊是錢往哪裡去（放款與投資，這是收益），中間那條帶子就是淨利差 —— 乘上資產規模就是利息淨收益，這是銀行的主體。★ 橫跨下方的那一條是第二條腿：手續費收入不佔資產負債表、不吃資本適足，跟利差是兩種生意，所以刻意畫成不經過中間引擎的獨立帶子。再往下是稅前獲利的加減式，信用成本被畫成減項 —— 它正是利差故事的反面。展開章節①可以看「升息時哪一段先動」：資產端跟著指數利率快速重訂價，負債端要等存款到期換約，中間那段就是淨利差擴張的窗口。</text>

      <!-- ================= §1 主畫面（永遠看得到） ================= -->
      ${fx.shadows(`<rect x="${BX + 4}" y="${BY0 + 4}" width="${LW}" height="${4 * BH + 3 * BG}" rx="6"/><rect x="${MX + 4}" y="${MY + 4}" width="${MW}" height="${MH}" rx="9"/><rect x="${RX + 4}" y="${BY0 + 4}" width="${RW}" height="${4 * BH + 3 * BG}" rx="6"/>`)}
      ${T(LX, BY0 - 32, '資金來源（負債端）', 'hd')}
      ${T(LX, BY0 - 14, '由上往下＝成本由低到高', 'sub')}
      ${SRC.map((s, i) => bar(s, BX, BY0 + i * (BH + BG), LW)).join('')}
      ${T(RX + RW, BY0 - 32, '資金運用（資產端）', 'hd', 'end')}
      ${T(RX + RW, BY0 - 14, '由上往下＝收益與風險同步升高', 'sub', 'end')}   <!-- ★ 引擎框下移到 y 96 之後，這一行不再壓在框上 -->
      ${USE.map((s, i) => bar(s, RX, BY0 + i * (BH + BG), RW)).join('')}
      ${engine()}
      ${fees()}
      ${pnl()}
      ${D.para(LX, PY + PH + 38, ['示意圖，非實物比例｜方塊的大小不代表實際金額比重；利差帶的寬度是示意，不對應任何一家的淨利差數字。',
      '長條右側的小格（快／慢）＝跟著市場利率重訂價的速度。資金來源與運用只列常見的幾類，實際科目依各家財報分類而異。'], 620, { cls: 'cap' }).svg}

      <!-- ================= 說明卡片（HTML；左欄＝負債與手續費，右欄＝資產與利差） ================= -->
      ${card({ part: 'bk_demand', no: 1, side: 'l', color: C.cost, ax: BX - 14, ay: BY0 + 19, title: '活期存款：最便宜的錢', sub: ['銀行最想要的一塊 —— 利率低、隨時可動用。分行據點與薪轉戶就是在搶這個。', '★ 升息時它的成本上得最慢，所以活存占比高的銀行，升息初期的利差擴張最明顯。'] })}
      ${card({ part: 'bk_time', no: 2, side: 'l', color: C.cost, ax: BX - 14, ay: BY0 + BH + BG + 19, title: '定期存款：要到期才換約', sub: ['成本比活存高，但它落後的特性正是升息初期利差會擴張的原因 —— 舊約還在舊利率上。'] })}
      ${card({ part: 'bk_wholesale', no: 3, side: 'l', color: C.hot, ax: BX - 14, ay: BY0 + 2 * (BH + BG) + 19, title: '同業拆借與金融債：最快反應', sub: ['直接跟市場利率走，升息當下就貴起來。靠這塊撐資金的銀行，升息初期反而先被壓到成本。'] })}
      ${card({ part: 'bk_equity', no: 4, side: 'l', color: C.cap, ax: BX - 14, ay: BY0 + 3 * (BH + BG) + 19, title: '自有資本：不用付息，但有要求', sub: ['股東的錢不用付利息，可是要交出 ROE。資本適足率規定了「這些資本最多能撐起多少放款」——這就是銀行規模的天花板。'] })}
      ${card({ part: 'bk_nim', no: 5, side: 'r', order: 5, color: C.nim, ax: MX + MW - 14, ay: MY + 16, title: '★ 淨利差：這張圖的主體', sub: ['資產收益率減掉資金成本率，再乘上生息資產的規模，就是利息淨收益 —— 多數銀行金控最大的一塊。', '所以銀行的獲利有兩個推力：利差（價）與放款成長（量），兩個要分開看。'] })}
      ${card({ part: 'bk_bond', no: 6, side: 'r', color: C.cap, ax: RX + RW + 14, ay: BY0 + 19, title: '債券與票券：收益低，但賣得掉', sub: ['擺著等流動性用的部位。利率上升時它的市價會跌，會從淨值那一側先反映出來。'] })}
      ${card({ part: 'bk_mortgage', no: 7, side: 'r', color: C.yield_, ax: RX + RW + 14, ay: BY0 + BH + BG + 19, title: '房貸：跟著指數利率走', sub: ['金額大、期限長、擔保品明確，是銀行資產裡最穩的一塊。利率連動，所以升息時收益端跟著上。'] })}
      ${card({ part: 'bk_corp', no: 8, side: 'r', color: C.yield_, ax: RX + RW + 14, ay: BY0 + 2 * (BH + BG) + 19, title: '企業放款：浮動利率、定期重訂價', sub: ['多數按指數利率或基準利率定期重訂價 —— 這就是「資產端反應比較快」的來源。', '景氣好時放款成長帶量、景氣差時倒帳風險上升，量與風險同一件事的兩面。'] })}
      ${card({ part: 'bk_consumer', no: 9, side: 'r', color: C.risk, ax: RX + RW + 14, ay: BY0 + 3 * (BH + BG) + 19, title: '消金與信用卡：利率最高、風險也最高', sub: ['收益率最好的一塊，代價是景氣轉差時呆帳先從這裡冒出來。所以它同時撐著加項（利息）與減項（信用成本）。'] })}
      ${card({ part: 'bk_fee_wm', no: 10, side: 'l', order: 10, color: C.fee, ax: LX + 141, ay: FY + 69, title: '財富管理：跟市場情緒走', sub: ['賣基金與保險收的通路手續費。行情熱、申購多就好；行情冷的時候這一塊掉得比利差快。'] })}
      ${card({ part: 'bk_fee_card', no: 11, side: 'l', order: 11, color: C.fee, ax: LX + 292, ay: FY + 69, title: '信用卡：跟消費力走', sub: ['刷卡手續費隨消費金額走，循環利息則是放款的一種。發卡與收單的規模效應很明顯。'] })}
      ${card({ part: 'bk_fee_syn', no: 12, side: 'r', order: 12, color: C.fee, ax: LX + 443, ay: FY + 69, title: '聯貸與承銷：按案子走', sub: ['大型聯貸案的安排費，單季落差大 —— 有沒有大案子會直接反映在當季的手續費收入上。'] })}
      ${card({ part: 'bk_fee_trust', no: 13, side: 'r', order: 13, color: C.fee, ax: LX + 594, ay: FY + 69, title: '信託與保管：最穩的一塊', sub: ['按受託資產規模收，不靠單筆交易，所以是手續費四塊裡波動最小的。'] })}
      ${card({ part: 'bk_pl_credit', no: 14, side: 'l', order: 14, color: C.risk, ax: LX + 3 * 104.8 + 48, ay: PY + PH + 11, title: '★ 信用成本：利差故事的反面', sub: ['升息讓銀行賺到利差，同時也推高借款人的還款壓力。景氣轉差時呆帳提存會一口氣吃掉好幾季的利差增量。', '所以看這一格不能只看利差往上，要同時看資產品質往哪裡走。'] })}
      ${card({ part: 'bk_pl_pbt', no: 15, side: 'r', order: 15, color: C.yield_, ax: LX + 5 * 104.8 + 48, ay: PY + 87, title: '稅前淨利 ÷ 淨值 ＝ ROE', sub: ['ROE 就是銀行股估值的核心變數：市場願意給幾倍股價淨值比，主要看它能不能長期維持較高的 ROE。'] })}
      ${note({ side: 'l', order: 96, title: '示意圖，非實物比例', lines: ['方塊的大小不代表實際金額比重；利差帶的寬度是示意，不對應任何一家的淨利差數字。資金來源與運用只列常見的幾類，實際科目依各家財報分類而異。'] })}
      ${note({ side: 'l', order: 97, title: '點零件會篩到哪些股票', lines: ['這張圖每一塊都掛在「銀行與銀行金控」這個環節上，點任何一個零件都會篩出 groups.yaml 的 bank 族群那 16 檔 —— 因為圖上講的全部是同一批公司自己的帳。', '★ 所以「點不同零件會列出不同股票」這件事在這張圖上**不會**發生，那是題目本來的形狀，不是壞掉。'] })}
      ${note({ side: 'r', order: 98, title: '這一格的兩個推力：價與量', lines: ['利息淨收益 ＝ 淨利差（價）× 生息資產規模（量）。利差看央行政策與資金行情，規模看放款需求與資本適足的空間 —— 兩個推力可以同時往上，也可能一個上一個下。'] })}
      ${note({ side: 'r', order: 99, warn: true, title: '★ 畫面上刻意不出現的數字', lines: ['淨利差的百分點、逾放比、覆蓋率、市占率一個都沒寫：它們是逐季變動的時點數字，印在圖上隔天就過期。要看當期數字請查央行與金管會的統計。'] })}

      <!-- ================= 章節①：升息時哪一段先動（預設收合） ================= -->
      ${fold('bk2', '① 升息之後，哪一段先動 —— 資產端快、負債端慢',
      '重訂價時間軸、利差擴張的窗口、為什麼會有時間差、降息時怎麼反過來', areaRepricing())}

      <!-- ================= 章節②：估值與成分（預設收合） ================= -->
      ${fold('bk3', '② 為什麼用 PB-ROE 估值、這一格收哪一種公司，以及沒有回答的事',
      'PB-ROE 的理由、與壽險／證券金控的分家依據、刻意不寫的那些數字', areaWho())}
    </svg>`;
  }

  window.DG.register('bank', {
    level: 'group', chain: 'financial',
    name: '銀行金融：利差是主體，手續費是第二條腿',
    draw: bank, native: CW,
    /* ★ Andy 2026-09-23 指定金融鏈「只要 2D 圖，不用 3D」—— scene 固定 null。*/
    scene: null,
    q: '銀行賺的是什麼？利率變動時哪一段會先動？',
    parts: {
      bk_demand: { name: '活期存款（活儲）', desc: '成本最低、量也最大的資金來源。升息時成本上得最慢，所以活存占比高的銀行，升息初期的利差擴張最明顯。' },
      bk_time: { name: '定期存款', desc: '成本比活存高，但要到期換約才換到新利率 —— 這個落後特性正是升息初期利差會擴張的原因。' },
      bk_wholesale: { name: '同業拆借與金融債', desc: '直接跟著市場利率走，升息當下就貴起來。靠這塊撐資金的銀行，升息初期反而先被壓到成本。' },
      bk_equity: { name: '自有資本（股東的錢）', desc: '不用付息，但要交出 ROE。資本適足率規定了這些資本最多能撐起多少放款，是規模的天花板。' },
      bk_nim: { name: '★ 淨利差（利差引擎）', desc: '資產收益率減資金成本率，乘上生息資產規模就是利息淨收益 —— 多數銀行金控最大的一塊。價（利差）與量（放款規模）要分開看。' },
      bk_bond: { name: '債券與票券投資', desc: '收益低但流動性好的部位。利率上升時市價會跌，先從淨值那一側反映出來。' },
      bk_mortgage: { name: '房貸', desc: '金額大、期限長、擔保品明確，是資產裡最穩的一塊；跟指數利率連動，升息時收益端跟著上。' },
      bk_corp: { name: '企業放款', desc: '多為浮動利率、定期重訂價，這就是「資產端反應比較快」的來源。景氣好帶量、景氣差帶倒帳風險。' },
      bk_consumer: { name: '消金與信用卡', desc: '利率最高的一塊，代價是景氣轉差時呆帳先從這裡冒出來 —— 同時撐著加項（利息）與減項（信用成本）。' },
      bk_fee_wm: { name: '手續費：財富管理', desc: '賣基金與保險收的通路手續費，跟市場情緒走；行情冷時掉得比利差快。' },
      bk_fee_card: { name: '手續費：信用卡', desc: '刷卡手續費隨消費金額走，循環利息則屬於放款。發卡與收單有明顯的規模效應。' },
      bk_fee_syn: { name: '手續費：聯貸與承銷', desc: '大型聯貸案的安排費，按案子走，單季落差大。' },
      bk_fee_trust: { name: '手續費：信託與保管', desc: '按受託資產規模收費，不靠單筆交易，是手續費四塊裡波動最小的。' },
      bk_pl_nii: { name: '加項：利息淨收益', desc: '淨利差乘上生息資產規模，銀行獲利的主體。' },
      bk_pl_fee: { name: '加項：手續費淨收益', desc: '不佔資產負債表、不吃資本的第二條腿，跟市場情緒與消費力連動。' },
      bk_pl_mkt: { name: '加項：金融資產評價', desc: '自有部位的債與股隨市價波動，單季可加可減。' },
      bk_pl_credit: { name: '★ 減項：信用成本（呆帳提存）', desc: '利差故事的反面：升息賺到利差的同時也推高借款人的還款壓力，景氣轉差時提存會吃掉好幾季的利差增量。' },
      bk_pl_opex: { name: '減項：營業費用', desc: '人事、分行通路與系統的成本。數位化想壓的就是這一塊。' },
      bk_pl_pbt: { name: '稅前淨利', desc: '除以淨值就是 ROE —— 銀行股估值的核心變數，決定市場願意給幾倍股價淨值比。' },
      bk_gap: { name: '★ 利差擴張的窗口', desc: '升息後資產端已經重訂價、負債端還沒補上來的那一段。等存款陸續換約完，成本補上，利差就回吐。降息時順序反過來。' },
      bk_fast: { name: '為什麼資產端快', desc: '企業放款與房貸多為浮動利率，按指數利率定期重訂價，升息一段時間內就跟著調上去。' },
      bk_slow: { name: '為什麼負債端慢', desc: '活存利率調幅小、定存要到期換約才換到新利率，所以資金成本是陸續補上來的。' },
      bk_val: { name: '估值：PB-ROE 而不是本益比', desc: '銀行的獲利是淨值乘 ROE 長出來的，淨值本身就是可比基準。本站 groups.yaml 把這一格的 valuation_metric 設成 pb_roe 就是這個理由；用本益比會被單季評價損益與呆帳提存扭曲。' },
      bk_scope: { name: '這一格收哪一種公司', desc: '依 groups.yaml：以銀行子公司為主要獲利來源的金控與純銀行股。壽險金控與證券金控被拆到另外兩格，因為驅動力不同（利差與放款 vs 利率與匯率 vs 成交量）。' },
    },
  });
})();
