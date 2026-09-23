/* 資安防護：一層一層擋，擋不住的交給 SOC —— 族群 `cyber_security`（software 鏈）

   ★ 型式：純 2D（`scene: null`）。**Andy 2026-09-23 指定不做 3D**
     （原話：「軟體與資訊服務 需補上 2D 圖即可，不用 3D」）。
     這張圖的內容本來也沒有立體結構可以繞著看 —— 它畫的是「錢從哪裡來、經過誰」，
     不是一個零件的剖面。要改成 3D 就是重新決定題目，不准實作時順手加。

   ★ 風格基準 ＝ AI 伺服器鏈的族群圖（`site/dg/server_psu.js`／`liquid_cooling.js`／
     `switch_wireless.js`）：svg 根掛 `rs` → 說明卡片由 `externalize()` 搬成 HTML（.dgc）
     排進畫布左右兩欄；材質走共用的 `D.fx`；字級吃 `--dg-fs-*`（12px 下限）、行距 16px；
     顏色一律 `--dg-*` token，JS 裡一個色碼都沒有。

   ★ 這張圖回答的問題（`q`）：這一格賺的是產品授權還是人力服務？為什麼客戶集中在政府與金融？
     所以骨架不是「防火牆長什麼樣」，而是三段：
       ① 攻擊面 → 縱深防禦四層 → 核心資產（擋得住的在這裡擋掉）
       ② 擋不住的怎麼辦：各層的日誌送進 SOC → 關聯分析 → 告警 → 通報與應變（這一段是「人」）
       ③ 所以收入分成三種型態，認列節奏完全不同（產品授權／委外服務／專案建置）

   ★ `data-seg` 的處理：**一個都不掛**。`pipeline/groups/supply_chain.yaml` 裡
     完全沒有 software 這條鏈（機器查的：`grep -c software` ＝ 0），沒有任何環節 id 對得上。
     硬掛一個別條鏈的環節＝在 public 網站上宣稱錯誤的公司對應，所以寧可不掛。
     代價：點零件不會篩成分股、拿不到環節色 —— 跟 `silicon_wafer.js`／`wide_bandgap.js` 同樣的
     既定取捨，不是壞掉。因此「誰做的」直接印在畫面上。

   ★ 事實與出處（畫面上只寫查得到的，其餘標示意）
     · 安碁資訊 6690 是 SOC 委外監控業者，提供 7×24 即時監控、分析與通報 —— 公司自己的服務頁
       （acercsi.com「SOC 資安委外監控服務」）。客戶以政府為主、其次金融與製造：
       投資分析平台（優分析／方格子）寫「政府占六到七成」—— **單一來源等級，畫面上只寫定性的
       「政府與金融為主」（與 groups.yaml 的 note 一致），不寫百分比。**
     · 政府採購為什麼是法遵驅動：《資通安全管理法》要求公務機關委外辦理資通系統建置、維運或
       資通服務時，應選任適當受託者並監督其資安管理機制（全國法規資料庫）；
       行政院國家資通安全會報技術服務中心辦理「資安服務廠商評鑑」，分類含 SOC 服務。
     · 金融業：金管會推動金融資安聯防、設有 F-ISAC（金融資安資訊分享與分析中心）。
     · 中華資安 7765 為中華電信集團的資安子公司（groups.yaml 的 note）。
     不寫的：市占率、合約金額、各家收入結構的百分比 —— 查不到可引用的公開數字，一個都不編。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  const CW = 660;

  /* ---------------- 小工具（跟 silicon_wafer.js 同一套寫法，沒有第二套介面） ---------------- */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const LN = (d, col, w2, extra) => `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${x}" y="${y}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  // 這張圖沒有 data-seg，data-part 一律自己寫（沒有 seg 時 stampParts 自動補的 key 會退化成序號）
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;

  /* 元件色（卡片 data-dgcolor ＋ 編號圓點 ＋ 引線端點共用），全部是 index.html 既有的 token */
  const C = {
    threat: 'var(--dg-err)', hot: 'var(--dg-hot)', net: 'var(--dg-cold)', edr: 'var(--dg-cool)',
    idp: 'var(--dg-si)', data: 'var(--dg-steel)', asset: 'var(--dg-au)', soc: 'var(--dg-accent-2d)',
    people: 'var(--dg-organic)', mute: 'var(--dg-mute)', warn: 'var(--dg-warn)',
  };
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ ① 縱深防禦（左欄）
     由上往下＝由外到內。每一層是一塊玻璃板，右端掛「產品／服務」標記 ——
     這張圖的主命題就在這個標記上：**同一條縱深上，有些層賣的是盒子，有些層賣的是人。** */
  const LX = 24, LW = 262;                      // 左欄的左緣與寬
  const LAYERS = [
    { id: 'cs_net', y: 118, t: '網路邊界', s: '防火牆／WAF／DDoS 清洗', k: '產品', col: C.net },
    { id: 'cs_edr', y: 166, t: '端點', s: '防毒／EDR 端點偵測與回應', k: '產品', col: C.edr },
    { id: 'cs_idp', y: 214, t: '身分與存取', s: '多因子驗證／特權帳號管理', k: '產品', col: C.idp },
    { id: 'cs_data', y: 262, t: '應用與資料', s: '弱點掃描／加密／備份與還原', k: '產品＋服務', col: C.data },
  ];
  const LH = 36;

  function defense() {
    const g = [];
    // 攻擊面：三種常見的進入點（示意，不指名任何工具或事件）
    const th = ['網路釣魚', '對外服務漏洞', '供應鏈與委外'];
    g.push(part('cs_surface', th.map((t, i) => {
      const x = LX + i * 88;
      return fx.glass(x, 68, 82, 28, { fill: C.threat, cls: 'part', rx: 6 })
        + T(x + 41, 86, t, 'sub', 'middle', 'fill:var(--dg-ink)');
    }).join('') + T(LX, 60, '攻擊面（從哪裡進來）', 'hd')));

    // 四層防護板
    LAYERS.forEach((L) => {
      g.push(part(L.id, fx.glass(LX, L.y, LW, LH, { fill: L.col, cls: 'part', rx: 5 })
        + T(LX + 12, L.y + 16, L.t, 'lbl')
        + T(LX + 12, L.y + 30, L.s, 'sub')
        + R(LX + LW - 68, L.y + 8, 60, 20, 'var(--dg-step-f)', 'part', 4)
        + T(LX + LW - 38, L.y + 22, L.k, 'sub', 'middle', `fill:${L.col}`)));
    });

    // 核心資產（要守的東西）
    g.push(part('cs_asset', fx.glass(LX + 46, 314, 170, 40, { fill: C.asset, cls: 'part', rx: 6 })
      + T(LX + 131, 331, '核心系統與個資', 'lbl', 'middle')
      + T(LX + 131, 347, '政府：民眾資料｜金融：帳務', 'sub', 'middle')));

    /* 攻擊路徑：一條往下的紅虛線，在前三層各被擋掉一次（小叉），
       第四層旁邊留一條「漏過去」的細線接到右邊的 SOC —— 沒有一層擋得住全部，
       這就是為什麼一定要有監控與應變（§① 到 §② 的橋）。*/
    const stop = (y) => `<g><circle cx="${LX + LW - 96}" cy="${y}" r="7" fill="var(--dg-frame-f)" stroke="${C.threat}" stroke-width="1.4"/>`
      + LN(`M${LX + LW - 100},${y - 4}l8,8M${LX + LW - 92},${y - 4}l-8,8`, C.threat, 1.6) + `</g>`;
    g.push(part('cs_path', LN(`M${LX + LW - 96},100 V${LAYERS[3].y + LH + 6}`, C.threat, 2, ' stroke-dasharray="6 5" class="flow"')
      + LAYERS.slice(0, 3).map(L => stop(L.y + LH / 2)).join('')
      + LN(`M${LX + LW - 96},${LAYERS[3].y + LH + 6} h26`, C.threat, 2, ' class="flow fast"')
      + `<path d="M${LX + LW - 66},${LAYERS[3].y + LH + 6} l-10,-5 v10Z" fill="${C.threat}"/>`
));
    return g.join('');
  }

  /* ================================================================ ② SOC（右欄）
     四格由上往下＝一條處理線。第三、四格特別標「人」—— 這兩格是委外服務的收入來源。*/
  const SX = 330, SW = 314;
  const STEPS = [
    { id: 'cs_log', t: '① 日誌收集', s: '各層設備的事件全部送進來', k: '機器' },
    { id: 'cs_corr', t: '② 關聯分析', s: '把分散的事件串成一次攻擊', k: '機器＋規則' },
    { id: 'cs_alert', t: '③ 告警與研判', s: '7×24 值班：這是誤報還是真的', k: '★ 人' },
    { id: 'cs_ir', t: '④ 通報與應變', s: '通知客戶、隔離、復原、事後報告', k: '★ 人' },
  ];

  function soc() {
    const g = [frame(SX, 60, SW, 294), T(SX + 14, 80, '資安監控中心（SOC）：擋不住的在這裡被看見', 'hd')];
    // 左邊四層的日誌往右送進 SOC（一條共用光暈的多光束＝一個濾鏡元素）
    g.push(fx.beams(LAYERS.map(L => ({ d: `M${LX + LW},${L.y + LH / 2} H${SX}`, color: C.soc, w: 1.6 })), { flow: true }));
    STEPS.forEach((s, i) => {
      const y = 94 + i * 62;
      g.push(part(s.id, R(SX + 14, y, SW - 28, 52, 'var(--dg-step-f)', 'part', 7)
        + T(SX + 26, y + 20, s.t, 'lbl')
        + T(SX + 26, y + 38, s.s, 'sub')
        + T(SX + SW - 52, y + 20, s.k, 'sub', 'end', `fill:${/人/.test(s.k) ? C.people : C.mute}`)));
      if (i < STEPS.length - 1) g.push(LN(`M${SX + SW / 2},${y + 52} v10`, C.soc, 2, ' class="flow"'));
    });
    return g.join('');
  }

  /* ================================================================ ③ 三種收入型態（永遠看得到）
     ★ 刻意不畫比例：各家的收入結構查不到可引用的公開數字，畫成圓餅就是編一個比例出來。
       畫面上只講「錢怎麼進來、什麼時候認列、規模長大時成本跟著長多少」。*/
  const REV = [
    { id: 'cs_rev_prod', t: '產品授權（自有／代理）', a: '一次性授權 ＋ 每年維護', b: '人力不必等比例增加',
      c: '代理的那一段是過手', col: C.net },
    { id: 'cs_rev_svc', t: '委外服務（SOC 監控）', a: '按月／按年收，逐月認列', b: '最穩：到期才會不見',
      c: '要養 7×24 的人', col: C.people },
    { id: 'cs_rev_proj', t: '專案建置與顧問', a: '按人天，驗收才認列', b: '看案子，季度落差大',
      c: '做不完就要外包', col: C.mute },
  ];
  function revenue() {
    return T(16, 386, '這一格的錢怎麼進來：三種型態，認列節奏完全不同', 'hd')
      + REV.map((r, i) => {
        const x = 16 + i * 212, y = 396;
        return part(r.id, R(x, y, 200, 88, 'var(--dg-frame-f)', 'part frame', 8)
          + R(x, y, 4, 88, r.col)
          + T(x + 14, y + 20, r.t, 'lbl')
          + T(x + 14, y + 40, r.a, 'sub')
          + T(x + 14, y + 58, r.b, 'sub')
          + T(x + 14, y + 76, r.c, 'sub', null, `fill:${r.col}`));
      }).join('');
  }

  /* ================================================================ 章節 ①：為什麼客戶是政府與金融 */
  function areaWhy() {
    const y0 = 520;
    const box = (i, t, lines, id) => {
      const x = 16 + i * 316;
      return part(id, frame(x, y0, 300, 184) + T(x + 14, y0 + 24, t, 'lbl')
        + lines.map((s, k) => T(x + 14, y0 + 48 + k * 18, s, 'sub', null, /^★/.test(s) ? `fill:${C.warn}` : '')).join(''));
    };
    return T(16, y0 - 12, '資安的採購有一大塊不是「想買」，是「規定要買」', 'hd')
      + box(0, '政府：法遵驅動的採購', [
        '《資通安全管理法》要求公務機關委外辦理',
        '資通系統建置、維運或資通服務時，',
        '要選任適當的受託者並監督其資安機制。',
        '國家資通安全會報技術服務中心辦理',
        '「資安服務廠商評鑑」，分類包含 SOC 服務 ——',
        '評鑑過的名單就是機關委外的參考。',
        '★ 所以預算跟著法規與年度編列走，',
        '　 不完全跟著景氣走。',
      ], 'cs_gov')
      + box(1, '金融：主管機關與聯防機制', [
        '金管會推動金融資安聯防，設有 F-ISAC',
        '（金融資安資訊分享與分析中心），',
        '把攻擊情資在同業之間分享。',
        '金融機構本身有資安人力與稽核要求，',
        '委外監控是把 7×24 的值班交出去。',
        '★ 這一段不寫任何金額與市占：',
        '　 查不到可引用的公開數字，不編。',
      ], 'cs_fin')
      + T(16, y0 + 206, '示意圖，非實物比例｜防護層只畫四層代表縱深的概念，實際分層依各家架構而異；攻擊路徑為示意，不對應任何真實事件。', 'cap');
  }

  /* ================================================================ 章節 ②：兩檔台股與這張圖沒回答的事 */
  function areaWho() {
    const y0 = 800;
    const co = (i, code, name, lines) => {
      const x = 16 + i * 316;
      return part('cs_co_' + code, frame(x, y0, 300, 150)
        + R(x, y0, 4, 150, C.soc)
        + T(x + 14, y0 + 24, name, 'lbl')
        + T(x + 14, y0 + 42, code, 'sub', null, `fill:${C.soc}`)
        + lines.map((s, k) => T(x + 14, y0 + 66 + k * 18, s, 'sub')).join(''));
    };
    return T(16, y0 - 12, '這張圖上誰做哪一塊（依公司自己的說法與 groups.yaml）', 'hd')
      + co(0, '6690', '安碁資訊', [
        '提供 7×24 的 SOC 資安委外監控、',
        '事件分析與通報（公司服務頁）。',
        '客戶以政府為主，其次金融與製造。',
        '★ 收入偏「服務」那一欄。',
      ])
      + co(1, '7765', '中華資安', [
        '中華電信集團的資安子公司，',
        '提供資安監控與防護服務。',
        '★ 各家的收入結構百分比查不到',
        '　 可引用的公開數字，不寫。',
      ])
      + frame(16, y0 + 166, 628, 122)
      + T(30, y0 + 190, '這張圖沒有回答的事', 'lbl')
      + ['市占率、合約金額、各家產品與服務的收入占比 —— 查不到可引用的公開出處，一個數字都不寫。',
        '「政府占安碁營收六到七成」只見於投資分析平台的單一來源，沒有公司自己的說法可以對照，所以畫面上只寫定性的「以政府與金融為主」。',
        '資安產品的技術優劣、各家工具的比較：這張圖講的是錢從哪裡來，不做產品評比。',
        '點零件不會篩成分股：供應鏈資料裡沒有 software 這條鏈的環節，硬掛一個環節等於宣稱錯誤的公司對應。'].map((s, i) =>
          T(30, y0 + 212 + i * 18, s, 'sub')).join('');
  }

  function cyberSecurity() {
    return `<svg class="dg dgm rs dgcs" viewBox="0 0 ${CW} 1120" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（見 DECISIONS 第 231 條）。
           這張圖一個 data-seg 都沒有，所以 diagrams.js 那一整組「.dg [data-seg] …」
           的描邊與高亮規則一條都吃不到，要在這裡自己給。顏色一律走 --dg-* token。*/
        svg.dgcs [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgcs [data-part]{cursor:default}
        svg.dgcs [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgcs [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgcs .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgcs .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>

      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">資安防護：一層一層擋，擋不住的交給 SOC</text>
      <text class="cap ext" x="0" y="0">左邊是縱深防禦：攻擊從外面進來，網路邊界、端點、身分、應用與資料一層一層擋；沒有任何一層擋得住全部，所以每一層的日誌都送進右邊的資安監控中心（SOC）。★ 這張圖真正要回答的是「這一格賺的是產品授權還是人力服務」——每一層右端都標了它賣的是盒子還是人，SOC 的第③④格（研判、通報應變）是 7×24 的人力，那就是委外服務的收入來源。下面兩段是「為什麼客戶集中在政府與金融」與「誰做哪一塊」。</text>

      <!-- ================= §1 主畫面（永遠看得到） ================= -->
      ${fx.shadows(`<rect x="${LX + 4}" y="122" width="${LW}" height="236" rx="8"/><rect x="${SX + 4}" y="64" width="${SW}" height="294" rx="9"/>`)}
      ${defense()}
      ${soc()}
      ${revenue()}

      <!-- ================= 說明卡片（HTML；左欄＝縱深防禦，右欄＝SOC 與收入） ================= -->
      ${card({ part: 'cs_surface', no: 1, side: 'l', color: C.threat, ax: 292, ay: 82, title: '攻擊面：從哪裡進來', sub: ['釣魚信、對外服務的漏洞、以及委外與供應鏈 —— 三條都是示意，不對應任何真實事件。', '攻擊面越大，要守的層數越多；這就是資安預算長大的原因。'] })}
      ${card({ part: 'cs_net', no: 2, side: 'l', color: C.net, ax: 14, ay: LAYERS[0].y + 18, title: '網路邊界：賣的是盒子', sub: ['防火牆、WAF、DDoS 清洗。台廠這一層多半是代理國外原廠的產品 —— 代理是過手，毛利薄。'] })}
      ${card({ part: 'cs_edr', no: 3, side: 'l', color: C.edr, ax: 14, ay: LAYERS[1].y + 18, title: '端點：防毒與 EDR', sub: ['每一台電腦與伺服器上的那一支程式。授權按台數與年份收，續約是穩定收入。'] })}
      ${card({ part: 'cs_idp', no: 4, side: 'l', color: C.idp, ax: 14, ay: LAYERS[2].y + 18, title: '身分與存取：誰可以進來', sub: ['多因子驗證與特權帳號管理。近年攻擊多半不是「打破牆」，是「拿到鑰匙」。'] })}
      ${card({ part: 'cs_data', no: 5, side: 'l', color: C.data, ax: 14, ay: LAYERS[3].y + 18, title: '應用與資料：產品 ＋ 服務混著賣', sub: ['弱點掃描、加密、備份與還原。掃描報告要有人讀、修補要有人跟 —— 這一層開始出現人力服務。'] })}
      ${card({ part: 'cs_asset', no: 6, side: 'l', color: C.asset, ax: 60, ay: 334, title: '要守的東西：核心系統與個資', sub: ['政府守的是民眾資料與公共服務，金融守的是帳務與客戶資料 —— 兩者出事的代價都不是錢可以了結的，所以採購的理由是法遵不是效率。'] })}
      ${card({ part: 'cs_path', no: 7, side: 'l', color: C.threat, ax: LX + LW - 96, ay: 107, title: '沒有一層擋得住全部', sub: ['前三層擋掉大部分，總有一條會漏過去。★ 承認這件事，才有 SOC 存在的理由 —— 資安的目標不是「零事件」，是「早點發現、快點收拾」。'] })}
      ${card({ part: 'cs_log', no: 8, side: 'r', color: C.soc, ax: SX + SW - 14, ay: 120, title: '① 日誌收集：機器做的', sub: ['四層設備的事件全部送進來。這一段是設備與平台，不太吃人力。'] })}
      ${card({ part: 'cs_corr', no: 9, side: 'r', color: C.soc, ax: SX + SW - 14, ay: 182, title: '② 關聯分析：規則與經驗', sub: ['把分散在不同設備的事件串成一次攻擊。規則寫得好不好，就是各家 SOC 的差別。'] })}
      ${card({ part: 'cs_alert', no: 10, side: 'r', color: C.people, ax: SX + SW - 14, ay: 244, title: '③ 告警與研判：★ 這裡開始是人', sub: ['7×24 有人值班，判斷這是誤報還是真的。機器一天丟出幾千筆，要有人讀。', '這一格就是「委外」兩個字的實體 —— 客戶自己養不起三班制，所以交出去。'] })}
      ${card({ part: 'cs_ir', no: 11, side: 'r', color: C.people, ax: SX + SW - 14, ay: 306, title: '④ 通報與應變：★ 也是人', sub: ['通知客戶、協助隔離與復原、出事後報告。按月或按年收費、逐月認列，合約到期才會不見。'] })}
      ${card({ part: 'cs_rev_prod', no: 12, side: 'l', order: 12, color: C.net, ax: 10, ay: 440, title: '產品授權：規模可以長，毛利看是不是自有', sub: ['自有產品的毛利高；代理國外原廠的那一段是過手，毛利薄 —— 同樣叫「產品收入」，兩者差很多。'] })}
      ${card({ part: 'cs_rev_svc', no: 13, side: 'r', order: 13, color: C.people, ax: 222, ay: 440, title: '委外服務：最穩，但要養人', sub: ['按月／按年收、逐月認列，續約率就是它的護城河。代價是人力成本跟著客戶數走，不像軟體可以無限複製。'] })}
      ${card({ part: 'cs_rev_proj', no: 14, side: 'r', order: 14, color: C.mute, ax: 434, ay: 440, title: '專案建置：看案子，季度落差大', sub: ['按人天報價、驗收才認列，所以單季營收會被幾個大案的驗收時點左右。'] })}
      ${note({ side: 'l', order: 97, title: '示意圖，非實物比例', lines: ['防護層只畫四層代表「縱深」這個概念，實際分層依各家架構而異；攻擊路徑與攻擊面為示意，不對應任何真實事件，也不指名任何產品或廠牌。'] })}
      ${note({ side: 'l', order: 98, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: ['供應鏈資料裡沒有「軟體與資訊服務」這條鏈的環節（機器查的：一個都沒有），所以這張圖一個 data-seg 都沒掛。那不是壞掉，是誠實 —— 硬掛一個別條鏈的環節，等於在 public 網站上宣稱錯誤的公司對應。'] })}
      ${note({ side: 'r', order: 99, warn: true, title: '★ 這一格的景氣跟誰連動', lines: ['政府採購跟著法規與年度預算編列走、金融跟著主管機關的要求走 —— 兩者都不是純粹的景氣循環。所以看這一格不要只看終端需求，要看法規與預算的時程。', '這一句是本圖的推論（依《資通安全管理法》的委外規定與金管會的聯防機制推出來的），不是任何一家公司的說法。'] })}

      <!-- ================= ① 為什麼客戶是政府與金融（預設收合） ================= -->
      ${fold('cs2', '① 為什麼客戶集中在政府與金融 —— 法遵驅動的採購',
      '資通安全管理法的委外規定、資安服務廠商評鑑、金融資安聯防 F-ISAC', areaWhy())}

      <!-- ================= ② 誰做哪一塊 ＋ 沒有回答的事（預設收合） ================= -->
      ${fold('cs3', '② 這張圖上誰做哪一塊，以及沒有回答的事',
      '安碁資訊 6690、中華資安 7765，以及刻意不寫的那些數字', areaWho())}
    </svg>`;
  }

  window.DG.register('cyber_security', {
    level: 'group', chain: 'software',
    name: '資安防護：一層一層擋，擋不住的交給 SOC',
    draw: cyberSecurity, native: CW,
    /* ★ Andy 2026-09-23 指定「軟體與資訊服務需補上 2D 圖即可，不用 3D」—— scene 固定 null。*/
    scene: null,
    q: '資安這一格賺的是產品授權還是人力服務？為什麼客戶集中在政府與金融？',
    parts: {
      cs_surface: { name: '攻擊面（從哪裡進來）', desc: '釣魚信、對外服務的漏洞、委外與供應鏈三條路徑，均為示意，不對應任何真實事件。攻擊面越大要守的層數越多，這是資安預算長大的原因。' },
      cs_net: { name: '網路邊界（防火牆／WAF／DDoS）', desc: '縱深防禦最外面一層，賣的是產品。台廠這一層多半是代理國外原廠，代理屬於過手，毛利薄。' },
      cs_edr: { name: '端點（防毒／EDR）', desc: '每一台電腦與伺服器上的那一支程式，授權按台數與年份收，續約是穩定收入。' },
      cs_idp: { name: '身分與存取（多因子驗證／特權帳號）', desc: '近年多數攻擊不是打破牆而是拿到鑰匙，所以身分這一層的權重越來越高。' },
      cs_data: { name: '應用與資料（弱點掃描／加密／備份）', desc: '產品與服務混著賣的一層：掃描報告要有人讀、修補要有人跟。' },
      cs_asset: { name: '核心系統與個資（要守的東西）', desc: '政府守民眾資料與公共服務、金融守帳務與客戶資料。出事的代價不是錢可以了結，所以採購的理由是法遵。' },
      cs_path: { name: '漏過去的那一條', desc: '沒有任何一層擋得住全部。承認這件事才有 SOC 存在的理由 —— 目標不是零事件，是早點發現、快點收拾。' },
      cs_log: { name: 'SOC ①：日誌收集', desc: '各層設備的事件全部送進監控中心。這一段靠設備與平台，不太吃人力。' },
      cs_corr: { name: 'SOC ②：關聯分析', desc: '把分散的事件串成一次攻擊。規則寫得好不好就是各家 SOC 的差別。' },
      cs_alert: { name: 'SOC ③：告警與研判（人）', desc: '7×24 有人值班判斷誤報或真事件。客戶自己養不起三班制，所以委外 —— 這一格就是委外服務的收入來源。' },
      cs_ir: { name: 'SOC ④：通報與應變（人）', desc: '通知客戶、協助隔離與復原、事後報告。按月或按年收費、逐月認列。' },
      cs_rev_prod: { name: '收入型態：產品授權', desc: '一次性授權＋每年維護。自有產品毛利高，代理國外原廠那一段是過手、毛利薄。' },
      cs_rev_svc: { name: '收入型態：委外服務', desc: '按月／按年收、逐月認列，最穩定；代價是人力成本跟著客戶數走，不像軟體可以無限複製。' },
      cs_rev_proj: { name: '收入型態：專案建置與顧問', desc: '按人天報價、驗收才認列，單季營收會被大案的驗收時點左右。' },
      cs_gov: { name: '政府：法遵驅動的採購', desc: '《資通安全管理法》要求公務機關委外時選任適當受託者並監督其資安機制；國家資通安全會報技術服務中心辦理資安服務廠商評鑑，分類含 SOC 服務。' },
      cs_fin: { name: '金融：主管機關與聯防機制', desc: '金管會推動金融資安聯防、設有金融資安資訊分享與分析中心（F-ISAC），把情資在同業之間分享。' },
      cs_co_6690: { name: '安碁資訊 6690', desc: '提供 7×24 的 SOC 資安委外監控、事件分析與通報（公司服務頁）。客戶以政府為主，其次金融與製造。' },
      cs_co_7765: { name: '中華資安 7765', desc: '中華電信集團的資安子公司，提供資安監控與防護服務。' },
    },
  });
})();
