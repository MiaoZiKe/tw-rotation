/* 雲端與 MSP：一筆雲端帳單，經過 MSP 之後留下多少 —— 族群 `cloud_msp`（software 鏈）

   ★ 型式：純 2D（`scene: null`）。**Andy 2026-09-23 指定不做 3D**
     （原話：「軟體與資訊服務 需補上 2D 圖即可，不用 3D」）。
     這張圖畫的是金流不是零件，轉一圈不會多理解任何一件事。

   ★ 風格基準 ＝ AI 伺服器鏈的族群圖（`server_psu.js`／`liquid_cooling.js`／`switch_wireless.js`）：
     `rs` ＋ `extRow` 把說明外掛成 HTML 卡片、材質走 `D.fx`、字級吃 `--dg-fs-*`（12px 下限）、
     顏色一律 `--dg-*` token，JS 裡一個色碼都沒有。

   ★ 這張圖回答的問題（`q`）：雲端用量長，這一格賺得到多少？
     所以主角是**管子的粗細**：客戶付進來的很粗、付給公有雲原廠的幾乎一樣粗，
     真正留在 MSP 身上的是那一條細的。加值服務那一條比較細，但留下的比例高得多。

   ★ 骨架為什麼這樣決定
     ① 一筆帳單的路徑（終端客戶 → MSP → 公有雲原廠），用線寬表示金額大小；
     ② 同一條路上分兩種生意：轉售／代管（過手）與加值服務（顧問、遷移、維運、資安）；
     ③ 為什麼營收跟著客戶的用量走：轉售那一段是照用量結算的，客戶多開幾台機器，
        MSP 的營收當月就跟著長 —— 這也是它成長快但毛利率被稀釋的原因。

   ★ `data-seg`：**一個都不掛**。`pipeline/groups/supply_chain.yaml` 裡完全沒有 software 這條鏈
     （機器查的：`grep -c software` ＝ 0）。硬掛一個別條鏈的環節就是宣稱錯誤的公司對應。
     代價與 `silicon_wafer.js` 相同：點零件不會篩成分股，所以「誰做的」直接印在畫面上。

   ★ 事實與出處
     · 伊雲谷 6689 是通過 AWS MSP 評鑑的雲端代管業者，營收分雲端服務與儲存產品銷售兩塊，
       並在雲端架構上提供數據分析、AI、資安、ERP／CRM 等加值服務（工商時報、鉅亨網報導）。
       2025 年起公司調整客戶結構、以獲利為優先而非衝營收（工商時報 2025-12 報導）。
       ⚠ 「雲端占營收約 85%」只見於媒體報導的單一數字，**畫面上不寫這個百分比**，只寫定性。
     · 宏碁資訊 6811、精誠 6214 依 groups.yaml 的 note 歸在公有雲代管與轉售、雲端遷移與維運。
     · 總額法／淨額法：IFRS 15 判斷「本人（principal）」或「代理人（agent）」的準則，
       是公開的會計準則，不是任何一家公司的說法；**畫面上不宣稱某一家用哪一種**（查不到）。
     不寫的：各家毛利率、市占率、雲端占比的百分比 —— 沒有可引用的公司自述來源，一個都不編。*/
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
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;

  const C = {
    cust: 'var(--dg-si)', msp: 'var(--dg-accent-2d)', cloud: 'var(--dg-cold)',
    resale: 'var(--dg-mute)', value: 'var(--dg-organic)', money: 'var(--dg-au)',
    warn: 'var(--dg-warn)', use: 'var(--dg-cool)',
  };
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ ① 一筆帳單的路徑
     三欄：客戶（x 16）→ MSP（x 238）→ 公有雲原廠（x 476）。
     ★ 主角是線寬：進來 18、付出去 15、留下 3 —— 三個數字刻意畫成「看得出比例很懸殊」，
       但**不標任何百分比**（各家的實際比例查不到可引用的來源，標了就是編）。*/
  const CUST = { x: 16, y: 74, w: 168, h: 150 };
  const MSP = { x: 238, y: 62, w: 184, h: 174 };
  const CLD = { x: 476, y: 74, w: 168, h: 150 };

  function flow() {
    const g = [];
    // 左：終端客戶
    g.push(part('cm_cust', frame(CUST.x, CUST.y, CUST.w, CUST.h)
      + R(CUST.x, CUST.y, 4, CUST.h, C.cust)
      + T(CUST.x + 14, CUST.y + 24, '終端客戶', 'lbl')
      + ['製造業：ERP 與資料湖', '金融與電商：尖峰流量', '新創與遊戲：一開就是幾十台'].map((s, i) =>
        T(CUST.x + 14, CUST.y + 50 + i * 20, s, 'sub')).join('')
      + T(CUST.x + 14, CUST.y + 126, '付的是「這個月用了多少」', 'sub', null, `fill:${C.money}`)));

    // 右：公有雲原廠（只寫服務名稱，不畫任何商標或包裝）
    g.push(part('cm_cloud', frame(CLD.x, CLD.y, CLD.w, CLD.h)
      + R(CLD.x, CLD.y, 4, CLD.h, C.cloud)
      + T(CLD.x + 14, CLD.y + 24, '公有雲原廠', 'lbl')
      + ['AWS／Azure／GCP', '機器、儲存、頻寬', '照用量計價，牌價公開'].map((s, i) =>
        T(CLD.x + 14, CLD.y + 50 + i * 20, s, 'sub')).join('')
      + T(CLD.x + 14, CLD.y + 126, '大部分的錢最後流到這裡', 'sub', null, `fill:${C.cloud}`)));

    // 中：MSP —— 兩條生意上下疊
    g.push(part('cm_msp', fx.glass(MSP.x, MSP.y, MSP.w, MSP.h, { fill: C.msp, cls: 'part', rx: 9 })
      + T(MSP.x + 14, MSP.y + 24, 'MSP（雲端代管業者）', 'lbl')));
    g.push(part('cm_resale', R(MSP.x + 14, MSP.y + 40, MSP.w - 28, 46, 'var(--dg-step-f)', 'part', 6)
      + R(MSP.x + 14, MSP.y + 40, 4, 46, C.resale)
      + T(MSP.x + 26, MSP.y + 58, '轉售／代管（過手）', 'lbl')
      + T(MSP.x + 26, MSP.y + 76, '收全額、付成本，差額很薄', 'sub')));
    g.push(part('cm_value', R(MSP.x + 14, MSP.y + 96, MSP.w - 28, 62, 'var(--dg-step-f)', 'part', 6)
      + R(MSP.x + 14, MSP.y + 96, 4, 62, C.value)
      + T(MSP.x + 26, MSP.y + 114, '加值服務', 'lbl')
      + T(MSP.x + 26, MSP.y + 132, '顧問、上雲搬遷、維運代管、', 'sub')
      + T(MSP.x + 26, MSP.y + 148, '資安、資料與 AI 專案', 'sub')));

    /* 金流：三條光束共用一個光暈濾鏡（一個濾鏡元素）。
       進 18 粗、出 15 粗、留下 3 —— 比例是示意，不標任何百分比。*/
    const yIn = MSP.y + 63, yOut = MSP.y + 63;
    g.push(fx.beams([
      { d: `M${CUST.x + CUST.w},${yIn} H${MSP.x}`, color: C.money, w: 18 },
      { d: `M${MSP.x + MSP.w},${yOut} H${CLD.x}`, color: C.cloud, w: 15 },
    ], { flow: true }));
    g.push(part('cm_gm', LN(`M${MSP.x + MSP.w / 2},${MSP.y + MSP.h} V${MSP.y + MSP.h + 26}`, C.money, 3, ' class="flow fast"')
      + `<path d="M${MSP.x + MSP.w / 2},${MSP.y + MSP.h + 34} l-6,-10 h12Z" fill="${C.money}"/>`
      + R(MSP.x - 10, MSP.y + MSP.h + 38, MSP.w + 20, 46, 'var(--dg-frame-f)', 'part frame', 7)
      + T(MSP.x + MSP.w / 2, MSP.y + MSP.h + 58, '真正留在 MSP 身上的', 'lbl', 'middle')
      + T(MSP.x + MSP.w / 2, MSP.y + MSP.h + 76, '＝毛利（轉售薄、加值厚）', 'sub', 'middle')));

    g.push(T(CUST.x + CUST.w + 10, yIn - 16, '帳單全額（營收）', 'sub', null, `fill:${C.money}`));
    g.push(T(MSP.x + MSP.w + 10, yOut - 16, '付給原廠（成本）', 'sub', null, `fill:${C.cloud}`));
    return g.join('');
  }

  /* ================================================================ ② 為什麼營收跟著用量走
     六根柱子＝客戶的雲端用量（示意，不是任何一家的實際數字），
     上面壓一條「轉售營收」的折線 —— 兩者同步；旁邊一條幾乎平的「加值服務」線做對照。*/
  const BB = { x: 24, y0: 468, h: 84, w: 34, gap: 18 };
  const USE = [30, 38, 44, 55, 66, 80];

  function usage() {
    const bars = USE.map((v, i) => {
      const x = BB.x + i * (BB.w + BB.gap), h = (v / 100) * BB.h;
      return R(x, BB.y0 - h, BB.w, h, C.use, 'part', 3)
        + T(x + BB.w / 2, BB.y0 + 16, 'M' + (i + 1), 'sub', 'middle');
    }).join('');
    const pt = (i) => [BB.x + i * (BB.w + BB.gap) + BB.w / 2, BB.y0 - (USE[i] / 100) * BB.h - 10];
    const line = 'M' + USE.map((_, i) => pt(i).join(',')).join(' L');
    const flatY = BB.y0 - 26;
    const flat = `M${BB.x + BB.w / 2},${flatY} L${BB.x + 5 * (BB.w + BB.gap) + BB.w / 2},${flatY - 10}`;
    return part('cm_usage', bars
      + fx.beam(line, { color: C.money, w: 2.6, glow: false, flow: true })
      + LN(flat, C.value, 2.6, ' stroke-dasharray="6 5"')
      + T(BB.x, BB.y0 - BB.h - 14, '客戶的雲端用量（示意）', 'lbl')
      + T(BB.x + 320, BB.y0 - BB.h + 2, '轉售營收：跟著用量走', 'sub', null, `fill:${C.money}`)
      + T(BB.x + 320, BB.y0 - BB.h + 20, '加值服務：跟著專案走，', 'sub', null, `fill:${C.value}`)
      + T(BB.x + 320, BB.y0 - BB.h + 38, '不會當月跟上', 'sub', null, `fill:${C.value}`)
      + T(BB.x + 320, BB.y0 - BB.h + 62, '★ 所以「營收成長快」跟', 'sub', null, `fill:${C.warn}`)
      + T(BB.x + 320, BB.y0 - BB.h + 80, '　 「賺得多」不是同一件事', 'sub', null, `fill:${C.warn}`));
  }

  /* ================================================================ 章節 ①：總額法 vs 淨額法 */
  function areaNet() {
    const y0 = 560;
    const bar = (x, y, w, label, col, sub) =>
      R(x, y, w, 26, col, 'part', 5) + T(x + w + 10, y + 17, label, 'sub', null, `fill:${col}`) + (sub ? T(x, y + 44, sub, 'sub') : '');
    return T(16, y0 - 12, '同一筆生意，帳上可以長得完全不一樣', 'hd')
      + part('cm_gross', frame(16, y0, 300, 190)
        + T(30, y0 + 24, '總額法（認列全額）', 'lbl')
        + bar(30, y0 + 40, 260, '營收', C.money)
        + bar(30, y0 + 84, 236, '成本', C.cloud)
        + bar(30, y0 + 128, 24, '毛利', C.value)
        + T(30, y0 + 170, '營收很大、毛利率很低', 'sub', null, `fill:${C.warn}`))
      + part('cm_netm', frame(332, y0, 312, 190)
        + T(346, y0 + 24, '淨額法（只認列差額）', 'lbl')
        + bar(346, y0 + 40, 24, '營收＝差額', C.value)
        + T(346, y0 + 84, '沒有等量的成本要扣', 'sub')
        + bar(346, y0 + 100, 24, '毛利', C.value)
        + T(346, y0 + 148, '營收很小、毛利率很高', 'sub', null, `fill:${C.warn}`)
        + T(346, y0 + 170, '同一筆生意、同樣的獲利金額', 'sub'))
      + frame(16, y0 + 206, 628, 122)
      + T(30, y0 + 230, '所以看這一格要看什麼', 'lbl')
      + ['IFRS 15 用「本人（principal）還是代理人（agent）」判斷該用哪一種：自己承擔主要履約責任與存貨／定價風險的用總額法，只是居中促成的用淨額法。',
        '★ 這張圖不宣稱任何一家用哪一種 —— 查不到可引用的公司自述，判斷也要看每一份合約的條款。',
        '實務上的看法：轉售占比高的時候，營收年增率會很漂亮但毛利率被往下稀釋；要同時看「營收」與「毛利金額」才讀得出真實的成長。',
        '這三句是依公開會計準則寫的通則，不是任何一家公司的說法。'].map((s, i) =>
          T(30, y0 + 252 + i * 18, s, 'sub', null, /^★/.test(s) ? `fill:${C.warn}` : '')).join('');
  }

  /* ================================================================ 章節 ②：三檔台股與沒回答的事 */
  function areaWho() {
    const y0 = 940;
    const co = (i, code, name, lines) => {
      const x = 16 + (i % 2) * 316, y = y0 + Math.floor(i / 2) * 146;
      return part('cm_co_' + code, frame(x, y, 300, 130)
        + R(x, y, 4, 130, C.msp)
        + T(x + 14, y + 24, name, 'lbl')
        + T(x + 14, y + 42, code, 'sub', null, `fill:${C.msp}`)
        + lines.map((s, k) => T(x + 14, y + 66 + k * 18, s, 'sub')).join(''));
    };
    return T(16, y0 - 12, '這張圖上誰做哪一塊（依公司說法與 groups.yaml）', 'hd')
      + co(0, '6689', '伊雲谷', [
        '通過公有雲原廠 MSP 評鑑的雲端代管業者；',
        '營收分雲端服務與儲存產品銷售兩塊，',
        '並在雲端架構上做數據、AI、資安、',
        'ERP／CRM 等加值服務（媒體報導）。',
      ])
      + co(1, '6811', '宏碁資訊', [
        '公有雲代管與轉售、雲端遷移與維運',
        '（groups.yaml 的 note）。',
        '★ 各家的轉售與加值占比查不到',
        '　 可引用的公開數字，不寫。',
      ])
      + co(2, '6214', '精誠', [
        '資訊服務整合商，業務含雲端代管',
        '與企業系統維運（groups.yaml 的 note）。',
      ])
      + part('cm_unknown', frame(332, y0 + 146, 312, 130)
        + T(346, y0 + 170, '這張圖沒有回答的事', 'lbl')
        + ['各家毛利率、市占率、雲端占營收的百分比。',
          '媒體報導過「雲端約占某家八成多」這類數字，',
          '但只有單一來源、沒有公司自述可對照，不寫。',
          '哪一家用總額法、哪一家用淨額法：要看合約',
          '條款，公開資料看不出來，不猜。'].map((s, k) => T(346, y0 + 194 + k * 18, s, 'sub')).join(''));
  }

  function cloudMsp() {
    return `<svg class="dg dgm rs dgcm" viewBox="0 0 ${CW} 1250" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（見 DECISIONS 第 231 條）。
           這張圖一個 data-seg 都沒有，描邊與高亮規則要自己給；顏色一律走 --dg-* token。*/
        svg.dgcm [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgcm [data-part]{cursor:default}
        svg.dgcm [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgcm [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgcm .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgcm .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>

      <text class="ttl ext" x="0" y="0">雲端與 MSP：一筆雲端帳單，經過 MSP 之後留下多少</text>
      <text class="cap ext" x="0" y="0">上半是一筆帳單的路徑：客戶把錢付給 MSP（很粗的那一條），MSP 再把大部分付給公有雲原廠（幾乎一樣粗），真正留下來的是往下那一條細的。★ 同一條路上其實有兩種生意 —— 轉售／代管是過手（金額大、留下少），加值服務（顧問、搬遷、維運、資安）金額小但留下的比例高。下半解釋為什麼營收跟著客戶的雲端用量走：轉售照用量結算，客戶多開幾台機器，當月營收就跟著長。下面兩段是「同一筆生意在帳上可以長得完全不一樣」與「誰做哪一塊」。</text>

      <!-- ================= §1 主畫面（永遠看得到） ================= -->
      ${T(16, 52, '① 一筆雲端帳單的路徑：線越粗＝金額越大', 'hd')}
      ${fx.shadows(`<rect x="${MSP.x + 4}" y="${MSP.y + 4}" width="${MSP.w}" height="${MSP.h}" rx="9"/>`)}
      ${flow()}
      ${T(16, 356, '② 為什麼營收跟著客戶的雲端用量走', 'hd')}
      ${usage()}

      <!-- ================= 說明卡片（HTML；左欄＝客戶與轉售，右欄＝原廠與加值） ================= -->
      ${card({ part: 'cm_cust', no: 1, side: 'l', color: C.cust, ax: CUST.x + 6, ay: CUST.y + 20, title: '終端客戶：付的是「這個月用了多少」', sub: ['雲端不是一次買斷，是照用量按月結算。客戶多開幾台機器、多存幾 TB，帳單當月就變大。'] })}
      ${card({ part: 'cm_msp', no: 2, side: 'l', color: C.msp, ax: MSP.x + 6, ay: MSP.y + 20, title: 'MSP：夾在客戶與原廠中間', sub: ['同時做兩種生意：把原廠的服務轉售給客戶，以及在那之上賣自己的專業。兩種生意的毛利差很多，混在同一個「營收」裡就看不出來。'] })}
      ${card({ part: 'cm_resale', no: 3, side: 'l', color: C.resale, ax: MSP.x + 14, ay: MSP.y + 63, title: '轉售／代管：過手的那一段', sub: ['向原廠拿折扣、照牌價或折後價開給客戶，差額就是它的利潤 —— 金額很大、留下的很薄。', '好處是黏著：客戶的機器一開就在上面跑，換供應商很麻煩。'] })}
      ${card({ part: 'cm_value', no: 4, side: 'r', color: C.value, ax: MSP.x + MSP.w - 14, ay: MSP.y + 127, title: '加值服務：留下的比例高得多', sub: ['把地端系統搬上雲、架構顧問、7×24 代管維運、雲上資安、資料與 AI 專案。', '★ 這一段賣的是人與方法，不是原廠的機器 —— 所以毛利厚，但要有人才做得出來。'] })}
      ${card({ part: 'cm_cloud', no: 5, side: 'r', color: C.cloud, ax: CLD.x + 6, ay: CLD.y + 20, title: '公有雲原廠：大部分的錢流向這裡', sub: ['機器、儲存與頻寬的牌價是公開的，所以轉售這一段很難漲價 —— 客戶查得到原價。'] })}
      ${card({ part: 'cm_gm', no: 6, side: 'r', color: C.money, ax: MSP.x + MSP.w / 2, ay: MSP.y + MSP.h + 60, title: '留下來的才是這一格賺到的', sub: ['進來的很粗、付出去的幾乎一樣粗 —— 看營收會高估這一格的獲利能力。要同時看毛利金額。', '圖上的粗細是示意，不代表任何一家的實際比例。'] })}
      ${card({ part: 'cm_usage', no: 7, side: 'l', order: 7, color: C.use, ax: BB.x + 2 * (BB.w + BB.gap), ay: BB.y0 - 44, title: '用量長，轉售營收當月就跟著長', sub: ['柱子是客戶的雲端用量（示意）、實線是轉售營收 —— 兩條同步，因為轉售本來就是照用量結算的。', '虛線是加值服務：它跟著專案走，不會當月跟上。'] })}
      ${note({ side: 'l', order: 96, title: '示意圖，非實物比例', lines: ['金流的線寬、柱狀圖的高度都是示意，不是任何一家公司的實際數字；圖上只寫服務名稱，不畫任何商標、包裝或產品外觀。'] })}
      ${note({ side: 'r', order: 97, warn: true, title: '★ 看這一格最容易誤讀的一件事', lines: ['轉售占比高的時候，營收年增率會很漂亮，但毛利率同時被稀釋 —— 營收成長快不等於賺得多。', '所以要看「毛利金額」有沒有跟著營收一起長；只長營收不長毛利，多半是轉售的比重變大了。'] })}
      ${note({ side: 'r', order: 98, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: ['供應鏈資料裡沒有「軟體與資訊服務」這條鏈的環節（機器查的：一個都沒有），所以這張圖一個 data-seg 都沒掛 —— 硬掛一個別條鏈的環節，等於宣稱錯誤的公司對應。'] })}

      <!-- ================= ① 總額法 vs 淨額法（預設收合） ================= -->
      ${fold('cm2', '① 同一筆生意，帳上可以長得完全不一樣 —— 總額法與淨額法',
      '為什麼轉售會讓營收很大、毛利率很低；IFRS 15 的本人與代理人', areaNet())}

      <!-- ================= ② 誰做哪一塊 ＋ 沒有回答的事（預設收合） ================= -->
      ${fold('cm3', '② 這張圖上誰做哪一塊，以及沒有回答的事',
      '伊雲谷 6689、宏碁資訊 6811、精誠 6214，以及刻意不寫的那些數字', areaWho())}
    </svg>`;
  }

  window.DG.register('cloud_msp', {
    level: 'group', chain: 'software',
    name: '雲端與 MSP：一筆帳單經過 MSP 之後留下多少',
    draw: cloudMsp, native: CW,
    /* ★ Andy 2026-09-23 指定「軟體與資訊服務需補上 2D 圖即可，不用 3D」—— scene 固定 null。*/
    scene: null,
    q: '雲端用量長，這一格賺得到多少？MSP 是轉售過手還是加值服務？',
    parts: {
      cm_cust: { name: '終端客戶', desc: '雲端照用量按月結算，客戶多開機器、多存資料，帳單當月就變大。' },
      cm_msp: { name: 'MSP（雲端代管業者）', desc: '夾在客戶與公有雲原廠之間，同時做轉售與加值服務兩種生意；兩者毛利差很多，混在同一個營收裡看不出來。' },
      cm_resale: { name: '轉售／代管（過手的那一段）', desc: '向原廠拿折扣、開給客戶，差額就是利潤。金額大、留下的薄；好處是黏著度高。' },
      cm_value: { name: '加值服務', desc: '上雲搬遷、架構顧問、代管維運、雲上資安、資料與 AI 專案。賣的是人與方法，毛利厚但要有人才做得出來。' },
      cm_cloud: { name: '公有雲原廠', desc: '機器、儲存與頻寬的牌價公開，所以轉售這一段很難漲價 —— 客戶查得到原價。' },
      cm_gm: { name: '真正留在 MSP 身上的', desc: '進來的很粗、付出去的幾乎一樣粗，留下的是細的那一條。看營收會高估這一格的獲利能力。線寬為示意。' },
      cm_usage: { name: '用量與營收的連動', desc: '轉售照用量結算，所以營收跟著客戶用量同步走；加值服務跟著專案走，不會當月跟上。柱高為示意。' },
      cm_gross: { name: '總額法（認列全額）', desc: '把客戶付的全額認成營收、把付給原廠的認成成本 —— 營收很大、毛利率很低。' },
      cm_netm: { name: '淨額法（只認列差額）', desc: '只把差額認成營收 —— 營收很小、毛利率很高。獲利金額與總額法相同，差的只是帳怎麼列。' },
      cm_co_6689: { name: '伊雲谷 6689', desc: '通過公有雲原廠 MSP 評鑑的雲端代管業者；營收分雲端服務與儲存產品銷售，並提供數據、AI、資安、ERP／CRM 等加值服務（媒體報導）。' },
      cm_co_6811: { name: '宏碁資訊 6811', desc: '公有雲代管與轉售、雲端遷移與維運服務（groups.yaml 的 note）。' },
      cm_co_6214: { name: '精誠 6214', desc: '資訊服務整合商，業務含雲端代管與企業系統維運（groups.yaml 的 note）。' },
      cm_unknown: { name: '這張圖沒有回答的事', desc: '各家毛利率、市占率、雲端占營收的百分比，以及誰用總額法誰用淨額法 —— 沒有可引用的公司自述來源，一個都不寫。' },
    },
  });
})();
