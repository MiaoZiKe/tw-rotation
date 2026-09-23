/* 企業 SaaS：專案人天制 vs 訂閱制，錢進來的節奏差在哪 —— 族群 `saas`（software 鏈）

   ★ 型式：純 2D（`scene: null`）。**Andy 2026-09-23 指定不做 3D**
     （原話：「軟體與資訊服務 需補上 2D 圖即可，不用 3D」）。
     這張圖畫的是兩種收入模型在時間軸上的形狀，沒有任何立體結構可以繞著看。

   ★ 風格基準 ＝ AI 伺服器鏈的族群圖（`server_psu.js`／`liquid_cooling.js`／`switch_wireless.js`）：
     `rs` ＋ `extRow` 外掛卡片、材質走 `D.fx`、字級 `--dg-fs-*`（12px 下限）、
     顏色一律 `--dg-*` token，JS 裡一個色碼都沒有。

   ★ 這張圖回答的問題（`q`）：為什麼 SaaS 的營收看起來成長慢、但比較穩？
     骨架就直接照這個問題排：**同一個時間軸、兩種模型上下並排**。
       上：專案人天制 —— 人力從第一個月就在燒，收入等驗收那一個月一次認列（一根高柱、其餘是零）。
       下：訂閱制 —— 每個月認一小格；第二年續約的疊在下面、當年新增的疊在上面，變成一道階梯。
     只要把兩張圖的縱軸畫成同一個刻度，「慢」與「穩」就自己看得出來，不必寫任何形容詞。

   ★ `data-seg`（2026-09-23 更新，批次 0923-C／C9）：**掛上了**。
     這張圖剛做出來時 `supply_chain.yaml` 完全沒有 software 這條鏈，所以一個都不敢掛；
     Andy 2026-09-23 授權補資料之後補上了環節 `sw_saas`（自有軟體與訂閱平台），這裡跟著掛。
     ⚠ 這一格的四檔**不是同一種生意**（叡揚是企業軟體、訊連是消費端創作軟體、
       智通還有一塊傳統製造），YAML 的 note 逐家寫明了 —— 掛同一個環節是照 groups.yaml 的族群走，
       不是在宣稱它們做的是同一件事。

   ★ 事實與出處
     · 收入認列的節奏差異（一次性 vs 逐期、合約負債／遞延收入）是 IFRS 15 的通則，
       不是任何一家公司的說法 —— 畫面上寫的是準則的通則。
     · 叡揚資訊 6752：1987 年成立，2009 年起投入雲端 SaaS，商業模式是「訂閱 ＋ 專案並行」
       （公司官網與媒體報導）。公司法說會說明訂閱式營收占比已超過四成、含維護與委外的
       穩定收入占比更高 —— ⚠ 這個數字只見於法說會的第三方整理，**畫面上只寫定性的
       「訂閱與維護等穩定收入已是主體」，不印百分比**；數字留在這段註解裡備查。
     · 6870 騰雲、5203 訊連、8932 智通 依 groups.yaml 的 note 歸在自有企業軟體與訂閱制平台。
       ⚠ 8932 智通在 groups.yaml 裡帶星號註記，本圖不對它的交易狀態做任何宣稱。
     不寫的：各家訂閱占比、續約率、客單價、市占率 —— 沒有可引用的公司自述，一個都不編。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  const CW = 660;

  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const LN = (d, col, w2, extra) => `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  /* ★ 2026-09-23（批次 0923-C／C9）：software 鏈的環節補進 `supply_chain.yaml` 之後，
     這張圖的零件掛得上 `data-seg` 了 —— 環節 ＝ `sw_saas`（自有軟體與訂閱平台），
     成分 ＝ groups.yaml 的 saas 族群（叡揚 6752、騰雲 6870、訊連 5203、智通 8932）。
     ⚠ 兩個零件刻意不掛：`sa_scale`（「兩張圖是同一個刻度」）是**看圖的說明**不是生意，
       `sa_unknown`（沒有回答的事）同理。掛上去等於在說「刻度」也是一門生意。*/
  const SEG = 'sw_saas';
  const NO_SEG = new Set(['sa_scale', 'sa_unknown']);
  const segOf = (id) => (NO_SEG.has(id) ? null : SEG);
  const part = (id, inner) => `<g data-part="${id}"${segOf(id) ? ` data-seg="${segOf(id)}"` : ''}>${inner}</g>`;

  const C = {
    proj: 'var(--dg-hot)', cost: 'var(--dg-mute)', sub1: 'var(--dg-accent-2d)',
    sub2: 'var(--dg-au)', defer: 'var(--dg-si)', warn: 'var(--dg-warn)', ok: 'var(--dg-organic)',
  };
  const card = (o) => {
    // seg 也要傳給卡片：卡片本身就是一個零件節點，沒傳的話點圖會篩、點卡片不會。
    const s = extRow({ part: o.part, seg: segOf(o.part), title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ 共用的時間軸
     兩張圖用**同一組 X**（12 個月）與**同一個縱軸刻度 UNIT**，
     不然「一次認列」與「逐月認列」的對比就只是視覺錯覺。*/
  const MX = 44, MW = 30, MG = 18;                  // 第一個月的左緣、格寬、間距
  const mx = (i) => MX + i * (MW + MG);             // 第 i 個月的左緣（i ＝ 0..11）
  const UNIT = 7.5;                                  // 一個單位金額 ＝ 7.5px（兩張圖共用）

  /* ---------------- 上：專案人天制 ---------------- */
  const PB = 206;                                    // 專案圖的基線
  function project() {
    const g = [frame(16, 64, 628, 166), T(30, 88, '專案人天制：收入等驗收那一個月一次認列', 'lbl')];
    // 人力成本：M1 到 M4 一直在燒（一條連續的淺色帶）
    g.push(part('sa_cost', R(mx(0), PB - 18, mx(3) + MW - mx(0), 18, C.cost, 'part', 3)
      + T(mx(0) + 4, PB - 5, '人力成本從第一個月就在燒', 'sub', null, 'fill:var(--dg-ink)')));
    // 收入：只有 M4 一根高柱
    const h = 12 * UNIT;
    g.push(part('sa_proj_rev', R(mx(3), PB - 18 - h, MW, h, C.proj, 'part', 3)
      + T(mx(3) - 6, 150, '驗收', 'sub', 'end', `fill:${C.proj}`)));
    // 軸與月份
    g.push(T(mx(4) + 10, 128, '← 收入只有驗收那一個月，其餘十一個月是零。', 'sub', null, `fill:${C.warn}`));
    g.push(T(mx(4) + 10, 146, '人卻是十二個月都在。', 'sub'));
    g.push(LN(`M${MX - 10},${PB} H${mx(11) + MW + 8}`, 'var(--dg-axis)', 1));
    for (let i = 0; i < 12; i++) g.push(T(mx(i) + MW / 2, PB + 16, 'M' + (i + 1), 'sub', 'middle'));
    return g.join('');
  }

  /* ---------------- 下：訂閱制 ---------------- */
  const SB = 398;                                    // 訂閱圖的基線
  /* 每個月認一小格。下段＝去年就在的客戶續約，上段＝當年新增 ——
     兩段疊起來就是「階梯」：不是因為單月賣得多，是因為上個月的還在。*/
  const KEEP = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4];
  const NEW = [0, 0.4, 0.8, 1.2, 1.6, 2, 2.4, 2.8, 3.2, 3.6, 4, 4.4];
  function subs() {
    const g = [frame(16, 252, 628, 170), T(30, 276, '訂閱制：每個月認一小格，上個月的還在', 'lbl'),
      T(30, 298, '同樣一張合約，分成十二份逐月認列 —— 所以單月看起來很小。', 'sub'),
      T(30, 316, '深色是上個月就在的客戶續約，淺色才是當月新增；階梯是續約疊出來的。', 'sub')];
    for (let i = 0; i < 12; i++) {
      const hk = KEEP[i] * UNIT, hn = NEW[i] * UNIT;
      g.push(part('sa_sub_m' + i, R(mx(i), SB - hk, MW, hk, C.sub1, 'part', 2)
        + (hn > 1 ? R(mx(i), SB - hk - hn, MW, hn, C.sub2, 'part', 2) : '')));
    }
    g.push(LN(`M${MX - 10},${SB} H${mx(11) + MW + 8}`, 'var(--dg-axis)', 1));
    for (let i = 0; i < 12; i++) g.push(T(mx(i) + MW / 2, SB + 14, 'M' + (i + 1), 'sub', 'middle'));
    // 圖例
    g.push(R(mx(0), SB + 40, 12, 12, C.sub1, null, 2) + T(mx(0) + 18, SB + 50, '續約（上個月就在的客戶）', 'sub'));
    g.push(R(mx(4), SB + 40, 12, 12, C.sub2, null, 2) + T(mx(4) + 18, SB + 50, '當月新增', 'sub'));
    // 「同一個刻度」的提示線：專案那根高柱的高度拉一條虛線過來
    g.push(part('sa_scale', LN(`M${mx(3) + MW},${PB - 18 - 12 * UNIT} H624 V252`, C.warn, 1.4, ' stroke-dasharray="5 5"')
      + T(624, PB - 18 - 12 * UNIT - 8, '同一個刻度', 'sub', 'end', `fill:${C.warn}`)));
    return g.join('');
  }

  /* ================================================================ ③ 三句結論（永遠看得到） */
  const CONC = [
    { id: 'sa_c1', t: '為什麼看起來成長慢', s: ['同樣金額的一張合約，', '專案一次認完、訂閱分十二份，', '當年只認到一部分。'], col: C.warn },
    { id: 'sa_c2', t: '為什麼比較穩', s: ['這個月的營收有一大半', '是上個月就決定的。', '要掉，得客戶真的不續約。'], col: C.ok },
    { id: 'sa_c3', t: '代價是什麼', s: ['前期先付出（開發、獲客），', '收入要好幾年才收回來。'], col: C.cost },
  ];
  function conclusion() {
    return T(16, 486, '③ 所以「成長慢」與「比較穩」是同一件事的兩面', 'hd')
      + CONC.map((c, i) => {
        const x = 16 + i * 212, y = 496;
        return part(c.id, R(x, y, 200, 104, 'var(--dg-frame-f)', 'part frame', 8)
          + R(x, y, 4, 104, c.col)
          + T(x + 14, y + 24, c.t, 'lbl')
          + c.s.map((s, k) => T(x + 14, y + 46 + k * 18, s, 'sub')).join(''));
      }).join('');
  }

  /* ================================================================ 章節 ①：毛利結構與遞延收入 */
  function areaMargin() {
    const y0 = 620;
    const bar = (x, y, w, col) => R(x, y, w, 24, col, 'part', 5);
    return T(16, y0 - 12, '毛利結構：一樣是一塊錢營收，成本長得不一樣', 'hd')
      + part('sa_gm_proj', frame(16, y0, 300, 170)
        + T(30, y0 + 24, '專案人天制', 'lbl')
        + bar(30, y0 + 40, 260, C.proj) + T(30, y0 + 80, '營收（驗收那個月）', 'sub')
        + bar(30, y0 + 92, 180, C.cost) + T(30, y0 + 132, '成本：主要是人天，做一單付一單', 'sub')
        + T(30, y0 + 154, '★ 要長營收就要加人，成本等比例上去', 'sub', null, `fill:${C.warn}`))
      + part('sa_gm_saas', frame(332, y0, 312, 170)
        + T(346, y0 + 24, '訂閱制（自有產品）', 'lbl')
        + bar(346, y0 + 40, 272, C.sub1) + T(346, y0 + 80, '營收（每個月一小格，累積起來）', 'sub')
        + bar(346, y0 + 92, 96, C.cost) + T(346, y0 + 132, '成本：主機、支援，研發前期就投完了', 'sub')
        + T(346, y0 + 154, '★ 多一個客戶不必多一份開發', 'sub', null, `fill:${C.ok}`))
      + T(16, y0 + 204, '收到錢 ≠ 認列營收：遞延收入（合約負債）', 'hd')
      + part('sa_defer', frame(16, y0 + 216, 628, 150)
        + R(40, y0 + 246, 180, 100, C.defer, 'part', 6)
        + T(130, y0 + 300, '合約負債', 'lbl', 'middle')
        + T(130, y0 + 320, '（預收、還沒認列的部分）', 'sub', 'middle')
        + LN(`M${226},${y0 + 296} h60`, C.sub1, 2.6, ' class="flow fast"')
        + `<path d="M296,${y0 + 296} l-10,-5 v10Z" fill="${C.sub1}"/>`
        + ['客戶年繳，錢一次進帳 —— 但依會計準則不能一次認列營收，',
          '要按月把服務「交付」出去才逐月認列。沒認列的那一段掛在合約負債（遞延收入）。',
          '★ 所以合約負債變大通常是好事：它是「已經收到錢、還沒認列的未來營收」。',
          '★ 這是 IFRS 15 的通則，不是任何一家公司的說法；本圖不引用任何一家的實際金額。'].map((s, i) =>
            T(306, y0 + 262 + i * 20, s, 'sub', null, /^★/.test(s) ? `fill:${C.warn}` : '')).join(''));
  }

  /* ================================================================ 章節 ②：四檔台股與沒回答的事 */
  function areaWho() {
    const y0 = 1030;
    const co = (i, code, name, lines) => {
      const x = 16 + (i % 2) * 316, y = y0 + Math.floor(i / 2) * 134;
      return part('sa_co_' + code, frame(x, y, 300, 118)
        + R(x, y, 4, 118, C.sub1)
        + T(x + 14, y + 24, name, 'lbl')
        + T(x + 14, y + 42, code, 'sub', null, `fill:${C.sub1}`)
        + lines.map((s, k) => T(x + 14, y + 66 + k * 18, s, 'sub')).join(''));
    };
    return T(16, y0 - 12, '這張圖上誰做哪一塊（依公司說法與 groups.yaml）', 'hd')
      + co(0, '6752', '叡揚資訊', [
        '自有企業應用軟體，2009 年起投入雲端；',
        '商業模式是訂閱與專案並行，訂閱與維護等',
        '穩定收入已是主體（公司法說會說明）。',
      ])
      + co(1, '6870', '騰雲', ['自有軟體與訂閱制平台', '（groups.yaml 的 note）。'])
      + co(2, '5203', '訊連', ['自有軟體產品，近年往訂閱制轉', '（groups.yaml 的 note）。'])
      + co(3, '8932', '智通', ['自有企業軟體（groups.yaml 的 note）。',
        '★ 這一檔在 groups.yaml 裡帶星號註記，',
        '　 本圖不對它的交易狀態做任何宣稱。'])
      + part('sa_unknown', frame(16, y0 + 282, 628, 122)
        + T(30, y0 + 306, '這張圖沒有回答的事', 'lbl')
        + ['各家的訂閱占比、續約率、客單價、市占率 —— 沒有可引用的公司自述來源，一個數字都不寫。',
          '圖上的柱高、合約長度、十二個月的形狀全部是示意，不是任何一家的實際數字。',
          '「訂閱一定比專案好」這種結論本圖不下：訂閱前期先付出、要好幾年才收回來，這也是它的代價。',
          '這四檔各自的產品線與客戶結構：它們掛在同一個環節底下是照族群歸類，不是在說它們做的是同一種生意。'].map((s, i) =>
            T(30, y0 + 328 + i * 18, s, 'sub')).join(''));
  }

  function saas() {
    return `<svg class="dg dgm rs dgsa" viewBox="0 0 ${CW} 1480" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（見 DECISIONS 第 231 條）。
           ★ 2026-09-23：掛上 data-seg 的零件改吃 diagrams.js 的「.dg [data-seg] …」，
           所以這裡的規則縮到 :not([data-seg])，只服務沒有環節的那兩個零件。*/
        svg.dgsa [data-part]:not([data-seg]) .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgsa [data-part]:not([data-seg]){cursor:default}
        svg.dgsa [data-part]:not([data-seg]):hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgsa [data-part]:not([data-seg]).sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgsa .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgsa .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>

      <text class="ttl ext" x="0" y="0">企業 SaaS：專案人天制 vs 訂閱制</text>
      <text class="cap ext" x="0" y="0">兩張圖用同一條時間軸、同一個縱軸刻度。上面是專案人天制：人力從第一個月就在燒，收入要等驗收那一個月一次認列，所以是一根高柱加一串零。下面是訂閱制：每個月認一小格，深色是上個月就在的客戶續約、淺色是當月新增 —— 疊起來就變成一道階梯。★ 「成長看起來慢」與「比較穩」其實是同一件事：同樣金額的合約分成十二份認，當年只認到一部分，但這個月的營收有一大半是上個月就決定的。下面兩段是毛利結構與遞延收入（合約負債），以及誰做哪一塊。</text>

      <!-- ================= §1 主畫面（永遠看得到） ================= -->
      ${T(16, 52, '① 專案人天制：一根高柱 ＋ 一串零', 'hd')}
      ${fx.shadows(`<rect x="20" y="68" width="628" height="166" rx="9"/><rect x="20" y="256" width="628" height="170" rx="9"/>`)}
      ${project()}
      ${T(16, 244, '② 訂閱制：每個月一小格，疊成一道階梯', 'hd')}
      ${subs()}
      ${conclusion()}

      <!-- ================= 說明卡片（HTML；左欄＝專案，右欄＝訂閱） ================= -->
      ${card({ part: 'sa_cost', no: 1, side: 'l', color: C.cost, ax: mx(0) - 8, ay: PB - 9, title: '人力成本從第一個月就在燒', sub: ['專案是先做後收：人先進場，錢在驗收那一刻才進來。所以案子拖越久，現金流越難看。'] })}
      ${card({ part: 'sa_proj_rev', no: 2, side: 'l', color: C.proj, ax: mx(3) + MW + 6, ay: PB - 18 - 12 * 7.5 + 12, title: '驗收那一個月一次認列', sub: ['單季營收會被幾個大案的驗收時點左右 —— 不是生意變好或變壞，是驗收落在哪一季。', '★ 這也是專案型公司的季度數字很跳的原因。'] })}
      ${card({ part: 'sa_sub_m0', no: 3, side: 'r', color: C.sub1, ax: mx(0) - 8, ay: SB - 4 * 7.5, title: '訂閱：每個月只認一小格', sub: ['同樣金額的合約，分成十二份逐月認列。當年只認到一部分 —— 這就是「看起來成長慢」的全部原因。'] })}
      ${card({ part: 'sa_sub_m11', no: 4, side: 'r', color: C.sub2, ax: mx(11) + MW + 8, ay: SB - 9 * 7.5, title: '階梯不是因為單月賣得多', sub: ['深色那段是上個月就在的客戶續約，淺色那段才是當月新增。★ 階梯往上，是因為舊的沒有掉。'] })}
      ${card({ part: 'sa_scale', no: 5, side: 'r', color: C.warn, ax: 624, ay: PB - 18 - 12 * 7.5, title: '兩張圖是同一個刻度', sub: ['刻意把縱軸畫成一樣 —— 不然「一次認列」與「逐月認列」的對比只是視覺錯覺。'] })}
      ${card({ part: 'sa_c1', no: 6, side: 'l', order: 6, color: C.warn, ax: 10, ay: 542, title: '成長慢：分母被時間拉長了', sub: ['一張同樣金額的合約，專案當年認完、訂閱當年只認一部分。所以轉型訂閱的那幾年，營收年增率會難看。'] })}
      ${card({ part: 'sa_c2', no: 7, side: 'l', order: 7, color: C.ok, ax: 222, ay: 542, title: '穩：這個月的一大半是上個月決定的', sub: ['要掉下來，得客戶真的不續約 —— 而換掉一套已經在用的企業軟體，本身就很貴。'] })}
      ${card({ part: 'sa_c3', no: 8, side: 'r', order: 8, color: C.cost, ax: 434, ay: 542, title: '代價：前期先付出', sub: ['開發與獲客的錢先花掉，收入要好幾年才收回來。★ 所以本圖不下「訂閱一定比專案好」這種結論。'] })}
      ${note({ side: 'l', order: 96, title: '示意圖，非實物比例', lines: ['柱高、合約長度、十二個月的形狀全部是示意，不是任何一家公司的實際數字；合約期間也不一定是十二個月。'] })}
      ${note({ side: 'r', order: 97, warn: true, title: '★ 看這一格要看的三個東西', lines: ['① 訂閱（或稱經常性）收入的占比有沒有在往上；② 合約負債（遞延收入）有沒有跟著長 —— 那是已經收到錢、還沒認列的未來營收；③ 毛利率在轉型期會先被前期投入壓住，要看它有沒有回來。', '這三句是依公開會計準則與訂閱商業模式的通則寫的，不是任何一家公司的說法。'] })}
      ${note({ side: 'r', order: 98, title: '點零件會篩到哪些股票', lines: ['兩種收入模型的每一塊（人力成本、驗收柱、逐月小格、續約階梯、毛利結構、合約負債）與四張公司卡，都掛在「自有軟體與訂閱平台」這個環節上，點下去會篩出這一格的成分股。', '★ 「兩張圖是同一個刻度」那一塊不掛環節 —— 它是看圖的說明，不是一門生意。'] })}

      <!-- ================= ① 毛利結構與遞延收入（預設收合） ================= -->
      ${fold('sa2', '① 毛利結構，以及「收到錢」跟「認列營收」不是同一件事',
      '一塊錢營收背後的成本長得不一樣；合約負債（遞延收入）是什麼', areaMargin())}

      <!-- ================= ② 誰做哪一塊 ＋ 沒有回答的事（預設收合） ================= -->
      ${fold('sa3', '② 這張圖上誰做哪一塊，以及沒有回答的事',
      '叡揚 6752、騰雲 6870、訊連 5203、智通 8932，以及刻意不寫的那些數字', areaWho())}
    </svg>`;
  }

  window.DG.register('saas', {
    level: 'group', chain: 'software',
    name: '企業 SaaS：專案人天制 vs 訂閱制',
    draw: saas, native: CW,
    /* ★ Andy 2026-09-23 指定「軟體與資訊服務需補上 2D 圖即可，不用 3D」—— scene 固定 null。*/
    scene: null,
    q: '為什麼 SaaS 的營收看起來成長慢、但比較穩？訂閱制跟專案人天制差在哪？',
    parts: {
      sa_cost: { name: '專案：人力成本從第一個月就在燒', desc: '專案是先做後收，人先進場、錢在驗收才進來，案子拖越久現金流越難看。' },
      sa_proj_rev: { name: '專案：驗收那一個月一次認列', desc: '單季營收被幾個大案的驗收時點左右，所以專案型公司的季度數字很跳。' },
      sa_sub_m0: { name: '訂閱：每個月認一小格', desc: '同樣金額的合約分成十二份逐月認列，當年只認到一部分 —— 這就是「看起來成長慢」的原因。' },
      sa_sub_m11: { name: '訂閱：階梯是續約疊出來的', desc: '深色是上個月就在的客戶續約、淺色才是當月新增。階梯往上是因為舊的沒有掉，不是單月賣得多。' },
      sa_scale: { name: '兩張圖是同一個刻度', desc: '縱軸刻意畫成一樣，否則「一次認列」與「逐月認列」的對比只是視覺錯覺。' },
      sa_c1: { name: '為什麼看起來成長慢', desc: '分母被時間拉長：轉型訂閱的那幾年，營收年增率會難看。' },
      sa_c2: { name: '為什麼比較穩', desc: '這個月的營收有一大半是上個月就決定的；要掉下來得客戶真的不續約，而換掉一套在用的企業軟體本身就很貴。' },
      sa_c3: { name: '訂閱的代價', desc: '開發與獲客的錢先花掉，收入要好幾年才收回來。所以本圖不下「訂閱一定比專案好」的結論。' },
      sa_gm_proj: { name: '專案的毛利結構', desc: '成本主要是人天，做一單付一單；要長營收就要加人，成本等比例上去。' },
      sa_gm_saas: { name: '訂閱（自有產品）的毛利結構', desc: '成本是主機與支援，研發在前期就投完了；多一個客戶不必多一份開發。' },
      sa_defer: { name: '合約負債（遞延收入）', desc: '客戶年繳、錢一次進帳，但依 IFRS 15 要按月交付服務才逐月認列；沒認列的掛在合約負債。它變大通常是好事 —— 那是已經收到錢、還沒認列的未來營收。' },
      sa_co_6752: { name: '叡揚資訊 6752', desc: '自有企業應用軟體，2009 年起投入雲端；訂閱與專案並行，訂閱與維護等穩定收入已是主體（公司法說會說明）。' },
      sa_co_6870: { name: '騰雲 6870', desc: '自有軟體與訂閱制平台（groups.yaml 的 note）。' },
      sa_co_5203: { name: '訊連 5203', desc: '自有軟體產品，近年往訂閱制轉（groups.yaml 的 note）。' },
      sa_co_8932: { name: '智通 8932', desc: '自有企業軟體（groups.yaml 的 note）。這一檔在 groups.yaml 裡帶星號註記，本圖不對它的交易狀態做任何宣稱。' },
      sa_unknown: { name: '這張圖沒有回答的事', desc: '各家的訂閱占比、續約率、客單價、市占率 —— 沒有可引用的公司自述來源，一個數字都不寫。' },
    },
  });
})();
