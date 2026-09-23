/* 電商零售：漏斗很漂亮，錢卡在履約 —— 族群 `ecommerce`（software 鏈）

   ★ 型式：純 2D（`scene: null`）。**Andy 2026-09-23 指定不做 3D**
     （原話：「軟體與資訊服務 需補上 2D 圖即可，不用 3D」）。
     這張圖講的是「一筆訂單的成本結構」，不是一個零件的剖面。

   ★ 風格基準 ＝ AI 伺服器鏈的族群圖（`server_psu.js`／`liquid_cooling.js`／`switch_wireless.js`）：
     `rs` ＋ `extRow` 外掛卡片、材質走 `D.fx`、字級 `--dg-fs-*`（12px 下限）、
     顏色一律 `--dg-*` token，JS 裡一個色碼都沒有。

   ★ 這張圖回答的問題（`q`）：電商的規模長大，獲利為什麼不一定跟著長？
     骨架分成三段，左右並排是刻意的對比：
       ① 左邊漏斗（造訪 → 加入購物車 → 成交訂單 → × 客單價 ＝ GMV）：這一段的成本會被攤薄，
          因為網站、系統、行銷不會因為多賣一單就多做一份。
       ② 右邊履約（倉儲 → 揀貨包裝 → 配送到府）：**這一段每一單都要重做一次** ——
          箱子、人、車不會因為訂單變多就變便宜。
       ③ 下面把兩條線疊在一起：訂單數往上、履約成本幾乎平行跟上，所以規模長大不等於獲利長大。
     換句話說，這張圖的主角不是漏斗，是**漏斗右邊那一段**。

   ★ `data-seg`：**一個都不掛**。`pipeline/groups/supply_chain.yaml` 裡完全沒有 software 這條鏈
     （機器查的：`grep -c software` ＝ 0），硬掛就是宣稱錯誤的公司對應。
     代價與 `silicon_wafer.js` 相同：點零件不會篩成分股，所以「誰做的」直接印在畫面上。

   ★ 事實與出處
     · 履約為什麼是成本卡點：富邦媒（momo）在高峰期曾租下超過 50 座衛星倉，這類倉租約短、面積小、
       難以導入自動化，揀貨出貨效率與人力成本都壓不下來；而且單一衛星倉存的品項有限，
       一張訂單湊不齊就得從別的倉分開出貨，等於一張單拆成好幾筆配送成本 —— 數位時代報導。
       公司的轉型方向是自建大型物流中心、減少對衛星倉的依賴（同來源）。
       ⚠ 報導裡的「140 億自建倉儲」是資本支出規模，**畫面上不寫金額**：那是單一媒體的數字，
         而且與「每一單的成本」不是同一件事。這裡只引用它的結構性理由。
     · 5321 美而快依 groups.yaml 的 note 歸在網路通路品牌。
     · 漏斗的算式（造訪 × 轉換率 × 客單價 ＝ 成交金額）是電商的通用定義，不是任何一家的說法。
     不寫的：轉換率、客單價、毛利率、市占率、履約成本占比 —— 沒有可引用的公司自述，一個都不編。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  const CW = 660;

  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, extra) => `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;

  const C = {
    traf: 'var(--dg-cold)', cart: 'var(--dg-cool)', order: 'var(--dg-accent-2d)',
    gmv: 'var(--dg-au)', ful: 'var(--dg-hot)', box: 'var(--dg-organic)',
    warn: 'var(--dg-warn)', mute: 'var(--dg-mute)',
  };
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ ① 漏斗（左欄）
     三段梯形由寬到窄，寬度只代表「一段比一段少」，**不代表任何轉換率**
     （各家的轉換率查不到可引用的公開數字，畫成刻度就是編）。*/
  const FX0 = 24, FCX = 24 + 140;                    // 漏斗左緣與中軸
  const FUN = [
    { id: 'ec_traffic', y: 78, h: 44, w0: 280, w1: 216, t: '造訪（流量）', s: '廣告、搜尋、App 推播、回訪', col: C.traf },
    { id: 'ec_cart', y: 140, h: 44, w0: 216, w1: 148, t: '加入購物車（轉換）', s: '商品頁、價格、評價、到貨速度', col: C.cart },
    { id: 'ec_order', y: 202, h: 44, w0: 148, w1: 96, t: '成交訂單', s: '付款完成的那一筆', col: C.order },
  ];
  function funnel() {
    const g = [T(16, 60, '① 漏斗：這一段的成本會被攤薄', 'hd')];
    FUN.forEach((f) => {
      const l0 = FCX - f.w0 / 2, r0 = FCX + f.w0 / 2, l1 = FCX - f.w1 / 2, r1 = FCX + f.w1 / 2;
      g.push(part(f.id, PA(`M${l0},${f.y} L${r0},${f.y} L${r1},${f.y + f.h} L${l1},${f.y + f.h}Z`, f.col, 'part')
        + T(FCX, f.y + 19, f.t, 'lbl', 'middle', 'fill:var(--dg-ink)')
        + T(FCX, f.y + 36, f.s, 'sub', 'middle', 'fill:var(--dg-ink)')));
    });
    // × 客單價 ＝ GMV
    g.push(part('ec_aov', R(FX0, 262, 280, 34, 'var(--dg-step-f)', 'part', 6)
      + T(FCX, 284, '× 客單價（一筆多少錢）', 'lbl', 'middle')));
    g.push(part('ec_gmv', fx.glass(FX0, 306, 280, 46, { fill: C.gmv, cls: 'part', rx: 7 })
      + T(FCX, 326, '＝ 成交金額（GMV）', 'lbl', 'middle')
      + T(FCX, 344, '★ GMV 不等於營收 —— 見下面第 ① 段', 'sub', 'middle', `fill:${C.warn}`)));
    return g.join('');
  }

  /* ================================================================ ② 履約（右欄）
     三格縱排，每一格右側都標「每一單重做一次」—— 這張圖的主命題就在這三個字上。*/
  const HX = 344, HW = 300;
  const FUL = [
    { id: 'ec_wh', t: '① 倉儲', s: ['貨要先擺在某個倉裡。', '倉租、盤點、呆滯都是固定要付的。'] },
    { id: 'ec_pick', t: '② 揀貨與包裝', s: ['一張單要有人走過去、拿下來、裝箱。', '箱子、緩衝材、人 —— 每一單都要一份。'] },
    { id: 'ec_ship', t: '③ 配送到府（最後一哩）', s: ['一台車、一個司機、一趟路。', '越快到貨，單趟能送的件數越少。'] },
  ];
  function fulfil() {
    const g = [T(HX - 4, 60, '② 履約：每一單都要重做一次', 'hd'), frame(HX, 70, HW, 282)];
    FUL.forEach((f, i) => {
      const y = 82 + i * 90;
      g.push(part(f.id, R(HX + 12, y, HW - 24, 76, 'var(--dg-step-f)', 'part', 7)
        + R(HX + 12, y, 4, 76, C.ful)
        + T(HX + 26, y + 22, f.t, 'lbl')
        + f.s.map((s, k) => T(HX + 26, y + 42 + k * 18, s, 'sub')).join('')));
      if (i < FUL.length - 1) g.push(LN(`M${HX + HW / 2},${y + 76} v14`, C.ful, 2, ' class="flow"'));
    });
    // 訂單從左邊漏斗流進履約
    g.push(fx.beam(`M${FCX + 48},224 H${HX}`, { color: C.order, w: 3, flow: true }));
    g.push(T(FCX + 54, 216, '成交的訂單流進來', 'sub', null, `fill:${C.order}`));
    return g.join('');
  }

  /* ================================================================ ③ 兩條線疊在一起（永遠看得到）
     訂單數往上、履約成本幾乎平行跟上；固定成本那一條才是被攤薄的。*/
  const GB = { x: 44, y0: 500, h: 96, w: 556 };
  const ORD = [20, 30, 42, 52, 66, 78, 88, 100];
  function scaleChart() {
    const sx = (i) => GB.x + i * (GB.w / (ORD.length - 1));
    const sy = (v) => GB.y0 - (v / 100) * GB.h;
    const path = (vals) => 'M' + vals.map((v, i) => `${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join(' L');
    const FULC = ORD.map(v => v * 0.92);                 // 履約成本：幾乎跟著訂單走
    const FIX = ORD.map((_, i) => 34 - i * 1.6);          // 每單分攤到的固定成本：被攤薄
    return T(16, 400, '③ 規模長大，成本裡只有一部分會被攤薄', 'hd')
      + part('ec_scale', LN(`M${GB.x - 12},${GB.y0} H${GB.x + GB.w + 12}`, 'var(--dg-axis)', 1)
        + fx.beams([
          { d: path(ORD), color: C.order, w: 2.8 },
          { d: path(FULC), color: C.ful, w: 2.8 },
        ], { flow: true })
        + LN(path(FIX), C.mute, 2.4, ' stroke-dasharray="6 5"')
        + T(GB.x, 424, '訂單數（示意）', 'sub', null, `fill:${C.order}`)
        + T(GB.x + 130, 424, '履約成本：幾乎平行跟上', 'sub', null, `fill:${C.ful}`)
        + T(GB.x + 330, 424, '每單分攤到的固定成本：被攤薄', 'sub', null, `fill:${C.mute}`)
        + T(GB.x, GB.y0 + 22, '★ 所以電商長大，獲利不一定跟著長 —— 要看履約那一段有沒有被壓下來。', 'sub', null, `fill:${C.warn}`));
  }

  /* ================================================================ 章節 ①：GMV 不等於營收 */
  function areaGmv() {
    const y0 = 620;
    const bar = (x, y, w, col) => R(x, y, w, 26, col, 'part', 5);
    return T(16, y0 - 12, 'GMV、營收、毛利 —— 三個不同的數字', 'hd')
      + part('ec_own', frame(16, y0, 300, 186)
        + T(30, y0 + 24, '自營（貨是自己的）', 'lbl')
        + bar(30, y0 + 40, 260, C.gmv) + T(30, y0 + 80, 'GMV 幾乎全部認成營收', 'sub')
        + bar(30, y0 + 92, 216, C.mute) + T(30, y0 + 132, '扣掉進貨成本', 'sub')
        + bar(30, y0 + 144, 44, C.box) + T(80, y0 + 162, '毛利（再扣履約才是賺的）', 'sub'))
      + part('ec_plat', frame(332, y0, 312, 186)
        + T(346, y0 + 24, '平台（貨是別人的）', 'lbl')
        + bar(346, y0 + 40, 272, C.gmv) + T(346, y0 + 80, 'GMV 很大，但只認抽成那一段', 'sub')
        + bar(346, y0 + 92, 44, C.box) + T(396, y0 + 110, '＝營收', 'sub')
        + T(346, y0 + 144, '★ 同樣的 GMV，兩種模式的營收差很多；', 'sub', null, `fill:${C.warn}`)
        + T(346, y0 + 162, '　 比較兩家之前要先確認是哪一種。', 'sub', null, `fill:${C.warn}`))
      + T(16, y0 + 222, '履約成本的三個槓桿（結構性的，不是砍價砍得出來的）', 'hd')
      + [['倉：自建還是租', '租來的衛星倉約期短、面積小，難導入自動化，揀貨效率與人力成本都壓不下來；自建大型物流中心才有空間放自動化設備。'],
        ['單：湊不湊得齊', '一張訂單如果在同一個倉湊不齊，就要從別的倉分開出貨 —— 一張單變成好幾筆配送成本。品項要擺對地方。'],
        ['最後一哩：自己送還是外包', '越快到貨，一趟車能送的件數越少。速度是賣點，也是成本。']].map(([t, s], i) =>
          part('ec_lever' + i, frame(16 + i * 212, y0 + 234, 200, 128)
            + T(30 + i * 212, y0 + 258, t, 'lbl')
            + s.replace(/(.{1,15})/g, '$1\n').split('\n').filter(Boolean).slice(0, 6)
              .map((ln, k) => T(30 + i * 212, y0 + 280 + k * 18, ln, 'sub')).join(''))).join('')
      + T(16, y0 + 380, '來源：倉儲轉型與衛星倉的結構性問題引自數位時代對富邦媒物流轉型的報導；金額與資本支出數字本圖不引用。', 'cap');
  }

  /* ================================================================ 章節 ②：兩檔台股與沒回答的事 */
  function areaWho() {
    const y0 = 1060;
    const co = (i, code, name, lines) => {
      const x = 16 + i * 316;
      return part('ec_co_' + code, frame(x, y0, 300, 140)
        + R(x, y0, 4, 140, C.order)
        + T(x + 14, y0 + 24, name, 'lbl')
        + T(x + 14, y0 + 42, code, 'sub', null, `fill:${C.order}`)
        + lines.map((s, k) => T(x + 14, y0 + 66 + k * 18, s, 'sub')).join(''));
    };
    return T(16, y0 - 12, '這張圖上誰做哪一塊（依公司說法與 groups.yaml）', 'hd')
      + co(0, '8454', '富邦媒', [
        '線上零售平台；近年把倉儲從大量租用',
        '衛星倉轉向自建大型物流中心，',
        '目的就是把履約那一段的效率拉起來',
        '（數位時代報導）。',
      ])
      + co(1, '5321', '美而快', [
        '網路通路品牌（groups.yaml 的 note）。',
        '★ 各家的履約成本占比、轉換率、客單價',
        '　 都查不到可引用的公開數字，不寫。',
      ])
      + part('ec_unknown', frame(16, y0 + 156, 628, 140)
        + T(30, y0 + 180, '這張圖沒有回答的事', 'lbl')
        + ['轉換率、客單價、毛利率、市占率、履約成本占營收的比例 —— 沒有可引用的公司自述來源，一個數字都不寫。',
          '漏斗三段的寬度、下面折線的高度全部是示意，不代表任何一家的實際數字。',
          '各家是自營、平台還是混合：公開資料能看到大方向，但比例看不出來，所以圖上只講兩種模式的差別，不替任何一家歸類。',
          '媒體報導過的資本支出金額（例如自建倉儲投入多少億）本圖不引用：那是單一來源，而且跟「每一單的成本」不是同一件事。',
          '點零件不會篩成分股：供應鏈資料裡沒有 software 這條鏈的環節，硬掛一個環節等於宣稱錯誤的公司對應。'].map((s, i) =>
            T(30, y0 + 202 + i * 18, s, 'sub')).join(''));
  }

  function ecommerce() {
    return `<svg class="dg dgm rs dgec" viewBox="0 0 ${CW} 1400" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（見 DECISIONS 第 231 條）。
           這張圖一個 data-seg 都沒有，描邊與高亮規則要自己給；顏色一律走 --dg-* token。*/
        svg.dgec [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgec [data-part]{cursor:default}
        svg.dgec [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgec [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgec .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgec .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>

      <text class="ttl ext" x="0" y="0">電商零售：漏斗很漂亮，錢卡在履約</text>
      <text class="cap ext" x="0" y="0">左邊是大家熟悉的漏斗：造訪 → 加入購物車 → 成交訂單，再乘上客單價就是成交金額（GMV）。這一段的成本會被攤薄 —— 網站、系統、行銷不會因為多賣一單就多做一份。★ 真正的主角是右邊那一欄：倉儲、揀貨包裝、配送到府，「每一單都要重做一次」，箱子、人、車不會因為訂單變多就變便宜。最下面把兩條線疊在一起：訂單數往上，履約成本幾乎平行跟上，只有每單分攤到的固定成本被攤薄 —— 這就是「規模長大，獲利不一定跟著長」的全部原因。下面兩段是 GMV 與營收的差別、履約成本的三個槓桿，以及誰做哪一塊。</text>

      <!-- ================= §1 主畫面（永遠看得到） ================= -->
      ${fx.shadows(`<rect x="${FX0 + 4}" y="310" width="280" height="46" rx="7"/><rect x="${HX + 4}" y="74" width="${HW}" height="282" rx="9"/>`)}
      ${funnel()}
      ${fulfil()}
      ${scaleChart()}

      <!-- ================= 說明卡片（HTML；左欄＝漏斗，右欄＝履約） ================= -->
      ${card({ part: 'ec_traffic', no: 1, side: 'l', color: C.traf, ax: FCX - 140, ay: 100, title: '造訪：買流量的錢', sub: ['廣告、搜尋、App 推播、回訪。流量可以用錢買到 —— 所以這一段的競爭最後會反映在行銷費用上。'] })}
      ${card({ part: 'ec_cart', no: 2, side: 'l', color: C.cart, ax: FCX - 108, ay: 162, title: '轉換：商品頁、價格、到貨速度', sub: ['同樣的流量，轉換率差一點點，訂單數就差很多。★ 「明天就到」本身就是轉換率的一部分 —— 而它是履約在撐。'] })}
      ${card({ part: 'ec_order', no: 3, side: 'l', color: C.order, ax: FCX - 74, ay: 224, title: '成交訂單：漏斗結束，成本才開始', sub: ['付款完成的那一刻，這一單的收入就定了；但要花的錢才正要開始 —— 貨還在倉裡。'] })}
      ${card({ part: 'ec_aov', no: 4, side: 'l', color: C.mute, ax: FX0 + 6, ay: 279, title: '客單價：一筆多少錢', sub: ['同樣一趟配送，一單 500 元跟一單 2,000 元的履約成本差不多 —— 所以客單價直接決定履約划不划算。'] })}
      ${card({ part: 'ec_gmv', no: 5, side: 'l', color: C.gmv, ax: FX0 + 6, ay: 329, title: 'GMV ≠ 營收', sub: ['自營是把貨賣掉、GMV 幾乎全部認成營收；平台只認抽成那一段。比較兩家之前要先確認是哪一種。'] })}
      ${card({ part: 'ec_wh', no: 6, side: 'r', color: C.ful, ax: HX + HW - 12, ay: 120, title: '倉儲：貨要先擺在某個地方', sub: ['倉租、盤點、呆滯都是固定要付的。★ 租來的衛星倉約期短、面積小，難導入自動化 —— 這就是為什麼會想自建。'] })}
      ${card({ part: 'ec_pick', no: 7, side: 'r', color: C.ful, ax: HX + HW - 12, ay: 210, title: '揀貨與包裝：每一單都要一份', sub: ['有人走過去、拿下來、裝箱。箱子、緩衝材、人力 —— 訂單多一倍，這裡就要多一倍。'] })}
      ${card({ part: 'ec_ship', no: 8, side: 'r', color: C.ful, ax: HX + HW - 12, ay: 300, title: '最後一哩：速度是賣點，也是成本', sub: ['越快到貨，一趟車能送的件數越少。★ 一張單如果在同一個倉湊不齊，還要分開出貨 —— 一張單變成好幾筆配送成本。'] })}
      ${card({ part: 'ec_scale', no: 9, side: 'r', order: 9, color: C.warn, ax: GB.x + GB.w, ay: 500 - 0.92 * 96, title: '兩條線幾乎平行', sub: ['訂單數往上，履約成本跟著往上；被攤薄的只有每單分攤到的固定成本（虛線那條）。', '所以看這一格不要只看營收年增率，要看履約那一段有沒有被壓下來。折線為示意。'] })}
      ${note({ side: 'l', order: 96, title: '示意圖，非實物比例', lines: ['漏斗三段的寬度只代表「一段比一段少」，不代表任何轉換率；下面折線的高度也是示意。畫面上不畫任何商標、包裝或產品外觀。'] })}
      ${note({ side: 'r', order: 97, warn: true, title: '★ 這一格跟軟體那三格不一樣', lines: ['資安、雲端、SaaS 賣的是人與授權，多一個客戶不必多搬一次貨；電商每成交一單就要真的把一個箱子送到一個人手上。', '所以同樣放在「軟體與資訊服務」這條鏈底下，這一格的成本結構其實比較接近零售與物流。'] })}
      ${note({ side: 'r', order: 98, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: ['供應鏈資料裡沒有「軟體與資訊服務」這條鏈的環節（機器查的：一個都沒有），所以這張圖一個 data-seg 都沒掛 —— 硬掛一個別條鏈的環節，等於宣稱錯誤的公司對應。'] })}

      <!-- ================= ① GMV 與營收、履約的三個槓桿（預設收合） ================= -->
      ${fold('ec2', '① GMV 不等於營收，以及履約成本的三個槓桿',
      '自營與平台的帳長得不一樣；倉、單、最後一哩', areaGmv())}

      <!-- ================= ② 誰做哪一塊 ＋ 沒有回答的事（預設收合） ================= -->
      ${fold('ec3', '② 這張圖上誰做哪一塊，以及沒有回答的事',
      '富邦媒 8454、美而快 5321，以及刻意不寫的那些數字', areaWho())}
    </svg>`;
  }

  window.DG.register('ecommerce', {
    level: 'group', chain: 'software',
    name: '電商零售：漏斗很漂亮，錢卡在履約',
    draw: ecommerce, native: CW,
    /* ★ Andy 2026-09-23 指定「軟體與資訊服務需補上 2D 圖即可，不用 3D」—— scene 固定 null。*/
    scene: null,
    q: '電商的規模長大，獲利為什麼不一定跟著長？成本卡在哪一段？',
    parts: {
      ec_traffic: { name: '造訪（流量）', desc: '廣告、搜尋、App 推播、回訪。流量可以用錢買到，所以這一段的競爭最後反映在行銷費用上。' },
      ec_cart: { name: '加入購物車（轉換）', desc: '同樣的流量，轉換率差一點訂單數就差很多。「明天就到」本身就是轉換率的一部分，而它是履約在撐。' },
      ec_order: { name: '成交訂單', desc: '付款完成的那一刻收入就定了，但要花的錢才正要開始 —— 貨還在倉裡。' },
      ec_aov: { name: '客單價', desc: '同樣一趟配送，一單 500 元跟一單 2,000 元的履約成本差不多，所以客單價直接決定履約划不划算。' },
      ec_gmv: { name: '成交金額（GMV）', desc: 'GMV 不等於營收：自營幾乎全部認成營收、平台只認抽成那一段。比較兩家之前要先確認是哪一種。' },
      ec_wh: { name: '履約①：倉儲', desc: '倉租、盤點、呆滯都是固定要付的。租來的衛星倉約期短、面積小、難導入自動化，這是自建大型物流中心的理由（數位時代報導）。' },
      ec_pick: { name: '履約②：揀貨與包裝', desc: '有人走過去、拿下來、裝箱。箱子、緩衝材、人力 —— 訂單多一倍，這裡就要多一倍。' },
      ec_ship: { name: '履約③：配送到府（最後一哩）', desc: '越快到貨，一趟車能送的件數越少。一張單在同一個倉湊不齊就要分開出貨，一張單變成好幾筆配送成本。' },
      ec_scale: { name: '訂單數與履約成本幾乎平行', desc: '被攤薄的只有每單分攤到的固定成本。所以看這一格不要只看營收年增率，要看履約那一段有沒有被壓下來。折線為示意。' },
      ec_own: { name: '自營（貨是自己的）', desc: 'GMV 幾乎全部認成營收，再扣進貨成本才是毛利，扣掉履約才是真的賺的。' },
      ec_plat: { name: '平台（貨是別人的）', desc: 'GMV 很大，但只認抽成那一段當營收。同樣的 GMV，兩種模式的營收差很多。' },
      ec_lever0: { name: '槓桿①：倉是自建還是租', desc: '租來的衛星倉約期短、面積小，難導入自動化；自建大型物流中心才有空間放自動化設備。' },
      ec_lever1: { name: '槓桿②：一張單湊不湊得齊', desc: '同一個倉湊不齊就要從別的倉分開出貨，一張單變成好幾筆配送成本。品項要擺對地方。' },
      ec_lever2: { name: '槓桿③：最後一哩自己送還是外包', desc: '越快到貨，一趟車能送的件數越少。速度是賣點，也是成本。' },
      ec_co_8454: { name: '富邦媒 8454', desc: '線上零售平台；近年把倉儲從大量租用衛星倉轉向自建大型物流中心，目的是把履約那一段的效率拉起來（數位時代報導）。' },
      ec_co_5321: { name: '美而快 5321', desc: '網路通路品牌（groups.yaml 的 note）。' },
      ec_unknown: { name: '這張圖沒有回答的事', desc: '轉換率、客單價、毛利率、市占率、履約成本占比 —— 沒有可引用的公司自述來源，一個數字都不寫；媒體報導過的資本支出金額也不引用。' },
    },
  });
})();
