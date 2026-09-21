/* 伺服器電源 PSU ＋ BBU 電池備援 —— docs/diagram_plan.md 的第 9 張（族群 `server_psu`、ai_server 鏈）

   規格書＝合約：docs/diagram_specs/server_psu.md。下面只記「為什麼這樣畫」，
   事實與來源一律回去看規格書 §7（每一條都標了信心度與出處）。

   ---- 型式：純 2D，不做真 3D（規格書 §0 已經寫死，scene: null）----
   §0 逐項對過 AGENTS §11 的判準「轉一圈真的能多理解一件事嗎」，七項全部不通過：
   降壓級數是**拓樸與數量級**（電壓不是空間）、兩種架構的差別是**少了哪一級**、
   BBU 撐多久是**時間軸**、80 PLUS 是**一張表**、BBU／UPS 掛哪一側是**接線位置**。
   這張圖本質上是一張**電力系統單線圖**，而單線圖的價值就在於把空間拿掉、只留連接關係。
   規格書還特別寫了「電流會流動所以要 3D」**不算理由** —— 流動是動畫，2D 一樣做得到
   （本圖就做了：那顆沿路變小的光點）。要加 3D 就是改規格書重新簽，不准實作時順手加。

   ---- 這張圖的紅線（規格書 §6-N，違反任一條就退回）----
   N1 畫面上沒有任何市占率、良率、成本金額。特別是**台達電的 PSU 市占率**：
      supply_chain.yaml 在 2026-09-19 就因為「查不到出處」把「約 60%」整段拿掉，
      這次搜尋又撈到另一個「70%」的說法、同樣沒有可查證出處 —— 兩個數字打架，
      所以**一個百分比都不寫**（規格書 §7-B2）。
   N2 效率百分比**只出現在效率表裡**，而且一定附 80 PLUS 的條件（230 V／50% 負載／
      冗餘與否）。Titanium 的 95% 與 96% **不是打架、是兩套不同組態**（§7-B1）——
      只寫「Titanium 95%」而不標條件，看起來就像寫錯。
   N3／N4 帶年份的量級一律寫成未來式並附來源年份；低信心的一律不寫成單一數值。
      **BBU 撐多久：三個來源三個答案**（而且對象可能是機櫃級 BBU 也可能是 RAID 卡上的
      BBU，口徑本身就不一致）→ **時間軸上一個秒數、一個分鐘數都不出現**，只寫量級與排序。
      **800 V 省銅**：兩組量化說法的基準完全不同（§7-B4）→ 只寫定性、不寫數字。
      **匯流排電壓**：原廠寫 54 V、技術文寫 50–54 V、VRM 那條寫 48–54 V（§7-B5）
      → 畫面寫「約 50–54 V」並註明各家寫法不同。
      **800 VDC 托盤端的降壓級數**查不到（§7-C）→ 只畫一個方塊並標「級數依設計而異」。
   N5 畫面最底下要講清楚「點零件篩到的是環節，不是整個族群」，而且**BBU 尚未建檔**。

   ---- ★ BBU 的落差（規格書 §7-D4，這張圖最大的坑）----
   `groups.yaml` 有獨立的 `bbu` 族群（6781／3211／4931／3323／6558／6121 共 6 檔），
   但 `supply_chain.yaml` 的 ai_server 鏈**沒有任何 BBU 環節，六個代號全部查無**。
   後果：點 BBU 零件會篩到 `power` 那一格的台達電與光寶科 ——
   跟 MLCC 當初踩到的是同一種錯（圖在講 A、點下去列出 B）。
   YAML 是 Andy 校訂的，這裡一行都不動；**改成在畫面上明講**（底部倒數兩行）。

   ---- data-seg 的掛法（規格書 §7-D，逐一在 YAML 查證過）----
     power      PSU、電源架、卡緣連接器、板上 DC-DC／VRM、晶片、BBU、超級電容、
                時間軸、效率表、兩欄架構對照
     connector  **匯流排 busbar 與電源線組 power whip** —— 這是刻意的：
                `3665 貿聯-KY` 的 tech 就是「Busbar 電源匯流排 / power whip」，
                note 還特別寫「做的是電源傳輸，不是只有訊號線」。**這一段不是電源廠做的。**
     assembly   機櫃虛線框
     不掛       設施側中壓交流、變壓器、機房 UPS（機房基礎設施，不在這條鏈上）

   ---- 色 ----
   AGENTS §15：JS 不准寫死 #xxxxxx。這張圖需要的新色（交流側／直流側／銅排／金手指）
   **全部用既有 --dg-* 混出來**（color-mix），定義在下面那段 scoped style 裡，
   不外洩到別張圖。交流側＝銅色系暖色、直流側＝環節色（--dg-accent），
   兩者都不與漲跌紅綠撞色（規格書 §8 視覺驗收）。

   ---- 版面（規格書 §9：先排版面再放字）----
   這張圖的文字量是三張裡最大的，所以先把欄位切好再放字，不靠縮字級救：
     區 A（y 76–650）  主供電單線圖，左→右降壓；x 16–700 畫圖、x 716 起是說明欄
     區 B（x 16–480）  BBU 與 UPS 的位置對照表 ＋ 四層防線時間軸
     區 C（x 500–976） 現行 50–54 V vs 800 VDC 兩欄並排
     區 D              CRPS 型 PSU 的 2.5D 小圖 ＋ 卡緣連接器放大 ＋ 80 PLUS 效率表
     區 E              流程列（第 1 格與第 2 格之間有一條分界線）
     區 F              三塊結論框 ＋ 底部四行註
   **引線的水平段全部落在空的橫帶上**，所以沒有一條引線從主角身上穿過去。 */
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || typeof DG.register !== 'function') return;
  const { STYLE, labelRow, processBar, onXZ, onYZ, box } = DG;

  const P = 'power', C = 'connector', A = 'assembly';

  /* 這張圖自己的顏色 token。**全部由既有 --dg-* 混出來，一個 #xxxxxx 都沒有。**
     scoped 在 .psu 上，所以不會汙染別張圖；art-director 要換色只要改 index.html
     的 --dg-cu／--dg-cover／--dg-ink，這裡跟著變。 */
  const VARS = `<style>
    .dg.psu{
      --dg-psu-ac:color-mix(in srgb,var(--dg-cu) 82%,var(--dg-cover));      /* 交流側 */
      --dg-psu-gold:color-mix(in srgb,var(--dg-cu) 54%,var(--dg-cover));    /* 鍍金接點 */
      --dg-psu-cu:var(--dg-cu);                                             /* 銅排（亮面） */
      --dg-psu-cu2:color-mix(in srgb,var(--dg-cu) 58%,var(--dg-el));        /* 銅排（暗面） */
      --dg-psu-box:color-mix(in srgb,var(--dg-ink) 7%,transparent);         /* 方塊底 */
      --dg-psu-box2:color-mix(in srgb,var(--dg-ink) 13%,transparent);       /* 方塊底（深一階） */
      --dg-psu-line:color-mix(in srgb,var(--dg-ink-3) 52%,transparent);     /* 一般外框線 */
      --dg-psu-off:color-mix(in srgb,var(--dg-mute) 52%,transparent);       /* 機房基礎設施（不在這條鏈上） */
      --dg-psu-die:color-mix(in srgb,var(--dg-el) 86%,var(--dg-ink-3));     /* 晶片本體 */
    }
    .dg.psu .off{stroke:var(--dg-psu-off);fill:none;stroke-width:1.4}
    .dg.psu .offtx{fill:var(--dg-psu-off)}
    .dg.psu .acw{stroke:var(--dg-psu-ac);fill:none;stroke-width:3;stroke-linecap:round}
    .dg.psu .dcw{stroke:var(--dg-accent);fill:none;stroke-width:3;stroke-linecap:round}
    .dg.psu .thin{stroke:var(--dg-psu-line);fill:none;stroke-width:1}
    .dg.psu .gold{fill:var(--dg-psu-gold)}
    .dg.psu .bd{fill:var(--dg-psu-box)}
    .dg.psu .bd2{fill:var(--dg-psu-box2)}
    .dg.psu .hair{stroke:var(--dg-psu-line);fill:none;stroke-width:var(--dg-hair-w,2);stroke-dasharray:5 5}
    /* ★ 發光收斂（AGENTS：emissive／bloom 壓下來，要「精密儀器」不是「電競 RGB」）。
       這張圖 26 個 [data-seg] 裡有 20 個掛 power，而從族群點進來的**預設狀態**就是
       「power 全部 .sel」—— 用共用的 7px 暈開會糊成一整片光（MLCC 的 B1 同一個病，
       只是它用 .dg1 整個關掉，這張是多環節圖，關掉就看不出選到哪一格了）。
       改成次強 3px／主角 9px：兩層的差別還在（描邊寬 2.2 vs --dg-part-w 3.6 也還在），
       但不刺眼。⚠ 這兩條一定要排在 STYLE 之後、特異性也要比它高，不然蓋不掉。*/
    .dg.psu [data-seg]:hover .part,.dg.psu [data-seg].sel .part{filter:drop-shadow(0 0 3px var(--c))}
    .dg.psu [data-seg].sel-part .part{filter:drop-shadow(0 0 9px var(--c))}
  </style>`;

  /* 兩欄架構對照的匯流排粗細：**兩欄共用這一個常數**（規格書 §6-C3）。
     同樣的功率下電流 ∝ 1 ÷ 電壓，導體截面就跟著走，所以粗細也用 1 ÷ 電壓。
     54 V → 15.0px、800 V → 1.01px。**不寫任何省銅數字**（§7-B4 兩組說法基準不同）。*/
  const BUSK = 810;
  const busH = (v) => +(BUSK / v).toFixed(2);

  function serverPsu() {
    // ---------------------------------------------------------------- 區 A：主供電單線圖
    const RX = 164, RY = 104, RW = 536, RH = 532;        // 機櫃虛線框
    const SHX = 170, SHY = 196, SHW = 180, SHH = 90;     // 電源架
    const BBX = 380, BBY = 230, BBW = 22, BBH = 256;     // 匯流排（厚銅排）
    const TRX = 452, TRW = 248;                          // 托盤左緣與寬
    const LBX = 716, LBW = 260;                          // 右側說明欄

    /* 4 顆 PSU：3 顆在架上、第 4 顆抽出來一點（熱插拔），所以看得出 N＋1（§6-S1）。
       每一顆都要有 PSU 真正的識別特徵：把手、風扇孔、指示燈、**後端卡緣金手指**。
       ⚠ `.spin` 的 keyframes 會設 transform，所以會蓋掉同一個元素上的 translate ——
       一定要外面再包一層負責定位的 <g>，不然扇葉會飛到原點去。*/
    const psuUnit = (x, y, i, out) => {
      const w = 40, h = 70, dx = out ? 10 : 0;
      const fingers = [0, 1, 2, 3, 4].map(j =>
        `<rect class="gold" x="${x + dx + 7 + j * 6}" y="${y + h - 11}" width="3" height="8" rx="1"/>`).join('');
      const blades = [0, 1, 2, 3, 4].map(j =>
        `<path class="thin" d="M0,0 L${(9 * Math.cos(j * 1.2566)).toFixed(1)},${(9 * Math.sin(j * 1.2566)).toFixed(1)}"/>`).join('');
      return `<g>
        <rect class="part bd2" x="${x + dx}" y="${y}" width="${w}" height="${h}" rx="3"/>
        <rect x="${x + dx + 9}" y="${y + 6}" width="22" height="5" rx="2.5" fill="var(--dg-ink-3)"/>
        <circle class="thin" cx="${x + dx + 20}" cy="${y + 30}" r="11"/>
        <g transform="translate(${x + dx + 20},${y + 30})"><g class="spin" style="animation-delay:${(i * 0.4).toFixed(1)}s">${blades}</g></g>
        <circle class="blink b${(i % 3) + 1}" cx="${x + dx + 33}" cy="${y + 13}" r="2.4" fill="var(--dg-accent)"/>
        ${fingers}</g>`;
    };

    // 板上 DC-DC：一個 for 迴圈畫 6 個等距電感（§6-V4：多相＝一排並聯，不是一顆）
    const phases = [];
    for (let i = 0; i < 6; i++) {
      const x = 466 + i * 20;
      phases.push(`<rect class="part bd2" x="${x}" y="398" width="14" height="22" rx="3"/>`
        + `<path class="thin" d="M${x + 2},404 H${x + 12} M${x + 2},409 H${x + 12} M${x + 2},414 H${x + 12}"/>`
        + `<rect x="${x + 2}" y="426" width="10" height="8" rx="1.5" fill="var(--dg-el)"/>`);
    }
    // 受電端晶片：die 上的運算格子（會呼吸；動畫關掉就停）
    const dieCells = [];
    for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++)
      dieCells.push(`<rect class="pulse" x="${614 + c * 14}" y="${400 + r * 14}" width="11" height="11" rx="1.5"
        fill="color-mix(in srgb,var(--dg-accent) 34%,transparent)" style="animation-delay:${(((r * 5 + c) % 6) * 0.32).toFixed(2)}s"/>`);
    /* BBU：電池芯（帶正負極柱）＋ 管理電路 ＋ 連接器金手指。
       極柱與「＋」符號用線段畫，不用 <text> —— 那是元件本身的標記，不是說明文字。
       ★ 這個符號跟機房 UPS 那個「交流→直流→交流 ＋ 旁路」的符號完全不同（§6-P4）。*/
    const cells = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) {
      const x = 198 + c * 36, y = 524 + r * 28;
      cells.push(`<rect class="part bd2" x="${x}" y="${y}" width="30" height="22" rx="2.5"/>`
        + `<rect x="${x + 5}" y="${y - 3}" width="7" height="4" rx="1" fill="var(--dg-psu-gold)"/>`
        + `<rect x="${x + 19}" y="${y - 3}" width="7" height="4" rx="1" fill="var(--dg-ink-3)"/>`
        + `<path class="thin" d="M${x + 5},${y + 12} h7 M${x + 8.5},${y + 8.5} v7 M${x + 19},${y + 12} h7"/>`);
    }
    // 超級電容／LIC：圓柱陣列（側視：柱身 ＋ 頂面橢圓 ＋ 防爆槽），比 BBU 小一號
    const scaps = [];
    for (let i = 0; i < 5; i++) {
      const x = 450 + i * 40;
      scaps.push(`<rect class="part bd2" x="${x}" y="534" width="28" height="38" rx="4"/>`
        + `<ellipse class="thin" cx="${x + 14}" cy="534" rx="14" ry="5" fill="var(--dg-psu-box2)"/>`
        + `<path class="thin" d="M${x + 8},531 H${x + 20} M${x + 14},527 V537"/>`);
    }
    // 其餘運算托盤（同一條路徑，簡化畫）
    const miniTray = (y) => `<g><rect class="bd" x="${TRX}" y="${y}" width="${TRW}" height="30" rx="4" stroke="var(--dg-psu-line)"/>
      ${[0, 1, 2, 3, 4, 5].map(j => `<rect x="${TRX + 8 + j * 9}" y="${y + 10}" width="6" height="11" rx="1.5" fill="var(--dg-psu-off)"/>`).join('')}
      <rect x="${TRX + 70}" y="${y + 8}" width="26" height="15" rx="2" fill="var(--dg-psu-die)"/>
      <text class="sub" x="${TRX + 100}" y="${y + 20}">其餘運算托盤（同一條路徑）</text></g>`;

    // ---------------------------------------------------------------- 區 C：兩欄架構對照
    const AC1 = 506, AC2 = 746, ACW = 224;               // 左欄（現行）／右欄（800 VDC）
    const slot = (n) => 756 + n * 52;                    // 五個插槽的 y（兩欄對齊，才看得出右欄少一格）
    const archBox = (x, n, t, s, extra) => `<g><rect class="part bd" x="${x}" y="${slot(n)}" width="${ACW}" height="42" rx="6"/>
      <text class="lbl" x="${x + 10}" y="${slot(n) + 17}">${t}</text>
      <text class="sub" x="${x + 10}" y="${slot(n) + 33}">${s}</text>${extra || ''}</g>`;
    const busBar = (x, n, v) => `<rect x="${x + ACW - 92}" y="${(slot(n) + 21 - busH(v) / 2).toFixed(2)}" width="82"
      height="${busH(v)}" rx="${Math.min(2, busH(v) / 2)}" fill="var(--dg-psu-cu)"/>`;

    // ---------------------------------------------------------------- 區 B：位置對照表
    const place = [['超級電容／LIC', '直流側', '櫃內', '毫秒等級'],
      ['BBU', '直流側', '櫃內', '比毫秒長，但仍然很短'],
      ['UPS', '交流側', '櫃外（機房）', '撐到發電機起來'],
      ['發電機', '交流側', '廠區', '最長']]
      .map(([a, b, c, d], i) => {
        const y = 766 + i * 26;
        return `<g><rect class="bd" x="16" y="${y - 15}" width="464" height="24" rx="4" opacity="${i % 2 ? '.55' : '0'}"/>
          <text class="lbl" x="26" y="${y}">${a}</text><text class="sub" x="168" y="${y}">${b}</text>
          <text class="sub" x="250" y="${y}">${c}</text><text class="sub" x="354" y="${y}">${d}</text></g>`;
      }).join('');

    /* 四層防線時間軸：**一個秒數都不標、也不按比例**（§6-T2、§7-B3）。
       四條棒子由短到長只表達**排序**，長度不代表任何可引用的數字。*/
    const timeline = [['超級電容／LIC', 52, '毫秒等級：吸收瞬間電流尖峰'],
      ['BBU', 96, '比毫秒長，但仍然很短'],
      ['UPS', 176, '撐到發電機起來'],
      ['發電機', 250, '最長']]
      .map(([n, w, s], i) => {
        const y = 926 + i * 22;
        return `<g><text class="sub" x="16" y="${y + 10}">${n}</text>
          <rect x="120" y="${y}" width="${w}" height="12" rx="6" fill="color-mix(in srgb,var(--dg-accent) ${34 + i * 14}%,transparent)"/>
          <text class="sub" x="${120 + w + 10}" y="${y + 10}">${s}</text></g>`;
      }).join('');

    // ---------------------------------------------------------------- 區 D：效率表
    const effRows = [['Gold', '92%', '92%'], ['Platinum', '94%', '94%'], ['Titanium', '95%', '96%']]
      .map(([a, b, c], i) => {
        const y = 1266 + i * 30;
        return `<g><rect class="bd" x="506" y="${y - 16}" width="464" height="26" rx="4" opacity="${i === 2 ? '1' : (i % 2 ? '.55' : '0')}"/>
          <text class="lbl" x="518" y="${y}">${a}</text><text class="num" x="700" y="${y}">${b}</text>
          <text class="num" x="836" y="${y}">${c}</text></g>`;
      }).join('');

    /* 區 D：CRPS 型 PSU 的 2.5D 小圖。
       兩個可見的側面各放一件識別特徵：x=W 面是**前面板**（把手＋風扇孔），
       y=D 面是**後端卡緣金手指** —— 後端畫成一束電線就認不出是 CRPS（§6-S2）。*/
    const IW = 118, ID = 46, IH = 30;
    const isoFront = onYZ(IW, 0)
      + `<rect x="6" y="7" width="34" height="5" rx="2.5" fill="var(--dg-ink-3)"/>`
      + `<circle class="etch" cx="23" cy="20" r="8"/><circle class="lit" cx="23" cy="20" r="2.5"/>`
      + `</g>`;
    const isoEdge = onXZ(0, ID)
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(j =>
        `<rect class="gold" x="${16 + j * 9}" y="8" width="5" height="15" rx="1"/>`).join('')
      + `</g>`;

    // ---------------------------------------------------------------- 組起來
    return `<svg class="dg dgm psu" viewBox="0 0 980 1806" width="100%" style="display:block">${STYLE}${VARS}
      <defs>
        <linearGradient id="psuCu" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-psu-cu2)"/><stop offset=".45" stop-color="var(--dg-psu-cu)"/><stop offset="1" stop-color="var(--dg-psu-cu2)"/></linearGradient>
        <marker id="psuAr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--dg-accent)"/></marker>
      </defs>

      <text class="ttl" x="16" y="26">伺服器電源：從牆上的電到晶片核心，中間降壓幾次</text>
      <text class="cap" x="16" y="46">這是一張電力單線圖 —— 空間拿掉、只留「誰接在誰後面」。上半是主供電路徑，左下是 BBU 與 UPS 的位置與四層防線，右下是兩種機櫃配電架構的對照。</text>

      <!-- ================= 區 A：主供電路徑（§3-A：不准跳級、電壓由左到右遞減）================= -->
      <text class="hd" x="16" y="80">① 主供電路徑：交流進來 → PSU → 匯流排 → 板上 DC-DC → 晶片核心</text>
      <text class="cap" x="16" y="98">← 這條虛線的左邊是機房基礎設施，不在這條產業鏈上</text>
      <text class="cap" x="330" y="98">虛線的右邊（機櫃內）才是這條鏈上的東西 →</text>
      <path class="hair" d="M152,106 V640"/>

      <!-- 設施側：只畫單線圖符號、不畫實物，也不掛任何 data-seg（§7-D1、§6-M1）。
           ⚠ 這一欄只有 136px 寬，所以每一條引下線都刻意走在文字右邊（x ≥ 110）——
              第一版沒這樣排，量出來三處「線直接劃過字」。 -->
      <g>
        <circle class="off" cx="40" cy="132" r="14"/>
        <path class="off" d="M33,132 q3.5,-6 7,0 t7,0"/>
        <path class="off" d="M40,146 V162"/>
        <circle class="off" cx="34" cy="173" r="11"/><circle class="off" cx="48" cy="173" r="11"/>
        <path class="off" d="M41,184 V200"/>
        <rect class="off" x="16" y="200" width="114" height="8" rx="2"/>
        <text class="lbl offtx" x="62" y="128">中壓交流</text>
        <text class="sub offtx" x="62" y="144">例如 13.8 kV</text>
        <text class="sub offtx" x="66" y="178">變壓器</text>
        <text class="sub offtx" x="16" y="226">機房配電盤</text>
        <text class="sub offtx" x="16" y="244">數百伏特交流</text>
      </g>
      <!-- 交流進機櫃（跨過那條虛線） -->
      <path class="acw flow" d="M126,208 V241 H${SHX}"/>

      <!-- 機房 UPS：接在**交流側**、畫在機櫃虛線框**外面**（§6-P2）。
           符號是「交流 → 直流 → 交流」的雙轉換加旁路，跟 BBU 那疊電池完全不同（§6-P4） -->
      <g>
        <path class="off" d="M110,208 V264"/>
        <text class="lbl offtx" x="16" y="258">機房 UPS</text>
        <rect class="off" x="16" y="264" width="122" height="60" rx="6"/>
        <rect class="off" x="24" y="284" width="26" height="20" rx="3"/>
        <path class="off" d="M29,296 q4,-8 8,0 t8,0"/>
        <rect class="off" x="58" y="284" width="26" height="20" rx="3"/>
        <path class="off" d="M64,291 H78 M64,297 H78"/>
        <rect class="off" x="92" y="284" width="26" height="20" rx="3"/>
        <path class="off" d="M97,296 q4,-8 8,0 t8,0"/>
        <path class="off" d="M30,280 q40,-12 80,0"/>
        <text class="sub offtx" x="16" y="344">接在交流側</text>
        <text class="sub offtx" x="16" y="362">在機櫃外面</text>
        <text class="sub offtx" x="16" y="380">保護整個機房</text>
        <text class="cap offtx" x="16" y="412">※ 設施側與 UPS</text>
        <text class="cap offtx" x="16" y="430">　不掛供應鏈環節，</text>
        <text class="cap offtx" x="16" y="448">　它們是機房基礎</text>
        <text class="cap offtx" x="16" y="466">　建設，不在這條</text>
        <text class="cap offtx" x="16" y="484">　產業鏈上。</text>
      </g>

      <!-- 機櫃虛線框（assembly）：沒有這個框，「櫃內／櫃外」就沒有畫面上的依據（§6-P3） -->
      <g data-seg="${A}" data-part="psu_rack">
        <rect class="part" x="${RX}" y="${RY}" width="${RW}" height="${RH}" rx="10" fill="none" stroke-dasharray="9 7"/>
        <text class="sub" x="176" y="626">機櫃（虛線框內＝櫃內；UPS 與設施電都在框外）</text>
      </g>

      <!-- 電源架 ＋ 4 顆 PSU（power）。第 4 顆抽出來一點＝可熱插拔，也看得出 N＋1（§6-S1／S3） -->
      <text class="sub" x="${SHX}" y="190">電源架 Power Shelf：多顆並排、可抽換</text>
      <g data-seg="${P}" data-part="psu_shelf">
        <rect class="part bd" x="${SHX}" y="${SHY}" width="${SHW}" height="${SHH}" rx="6"/>
      </g>
      <g data-seg="${P}" data-part="psu_unit">
        ${psuUnit(176, 206, 0, false)}${psuUnit(220, 206, 1, false)}${psuUnit(264, 206, 2, false)}${psuUnit(308, 206, 3, true)}
      </g>
      <path class="thin" d="M338,282 V294" marker-end="url(#psuAr)" stroke="var(--dg-accent)"/>
      <text class="sub" x="176" y="310">N＋1：壞一顆不用關機</text>
      <text class="tag" x="316" y="310">熱插拔</text>

      <!-- PSU → 匯流排（直流側從這裡開始） -->
      <path class="dcw flow" d="M${SHX + SHW},258 H${BBX}"/>
      <text class="tag" x="430" y="224">約 50–54 V 直流</text>
      <text class="cap" x="430" y="240">（各家寫法不同：48 V／54 V 都看得到）</text>

      <!-- 直流匯流排：厚銅排、實心，不是圓電線（§6-V3）。掛 connector 不是 power（§7-D2） -->
      <g data-seg="${C}" data-part="psu_busbar">
        <rect class="part" x="${BBX}" y="${BBY}" width="${BBW}" height="${BBH}" fill="url(#psuCu)"/>
        <path class="part" d="M${BBX},${BBY} L${BBX + BBW},${BBY} L${BBX + BBW + 10},${BBY - 10} L${BBX + 10},${BBY - 10} Z" fill="var(--dg-psu-cu)"/>
        <path class="part" d="M${BBX + BBW},${BBY} L${BBX + BBW + 10},${BBY - 10} L${BBX + BBW + 10},${BBY + BBH - 10} L${BBX + BBW},${BBY + BBH} Z" fill="var(--dg-psu-cu2)"/>
      </g>

      <!-- 電源線組 power whip：從匯流排接到托盤（§6-V5），一樣掛 connector -->
      <g data-seg="${C}" data-part="psu_whip">
        ${[303, 343, 426].map(y => `<path class="part" d="M${BBX + BBW},${y} H${TRX}" stroke-width="8" stroke-linecap="round" fill="none"/>
          <path class="flow" d="M${BBX + BBW},${y} H${TRX}" stroke="var(--dg-accent)" stroke-width="2.5" fill="none"/>`).join('')}
      </g>

      <!-- 其餘托盤（簡化）＋ 主托盤（展開） -->
      ${miniTray(288)}${miniTray(328)}
      <rect class="bd" x="${TRX}" y="366" width="${TRW}" height="120" rx="6" stroke="var(--dg-psu-line)"/>
      <text class="sub" x="458" y="380">運算托盤（展開）</text>

      <!-- 板上 DC-DC／VRM：一排 6 個等距電感（多相）＋ 開關元件（§6-V4） -->
      <g data-seg="${P}" data-part="psu_vrm">
        <rect class="part bd" x="460" y="392" width="130" height="52" rx="5"/>
        ${phases.join('')}
      </g>
      <text class="sub" x="460" y="460">多相：一排電感並聯、</text>
      <text class="sub" x="460" y="478">相位錯開輪流工作</text>
      <path class="dcw flow" d="M590,418 H604" marker-end="url(#psuAr)"/>

      <!-- 受電端晶片 -->
      <g data-seg="${P}" data-part="psu_die">
        <rect class="part" x="606" y="392" width="86" height="52" rx="4" fill="var(--dg-psu-die)"/>
        ${dieCells.join('')}
      </g>
      <text class="sub" x="606" y="460">GPU／ASIC</text>
      <text class="sub" x="606" y="478">約 1 V 以下</text>

      <!-- 直流節點：BBU 與超級電容接在**同一個**直流節點上（§6-P5），而且都在虛線框裡 -->
      <circle cx="${BBX + BBW / 2}" cy="${BBY + BBH}" r="4.5" fill="var(--dg-accent)"/>
      <path class="dcw" d="M${BBX + BBW / 2},${BBY + BBH} V500 H340 V516"/>
      <path class="dcw" d="M${BBX + BBW / 2},500 H520 V516"/>

      <!-- BBU（power）：電池芯 ＋ 正負極柱 ＋ 管理電路 ＋ 連接器金手指 -->
      <text class="lbl" x="190" y="510">BBU 電池備援模組</text>
      <g data-seg="${P}" data-part="psu_bbu">
        <rect class="part bd" x="190" y="516" width="180" height="76" rx="6"/>
        ${cells.join('')}
        <rect class="part bd2" x="344" y="524" width="20" height="50" rx="3"/>
        ${[0, 1, 2].map(j => `<circle cx="354" cy="${534 + j * 14}" r="2.6" fill="var(--dg-accent)"/>`).join('')}
        ${[0, 1, 2, 3].map(j => `<rect class="gold" x="${300 + j * 8}" y="592" width="5" height="7" rx="1"/>`).join('')}
      </g>

      <!-- 超級電容／鋰離子電容（power）：比 BBU 小一號，管最短的那一段 -->
      <text class="lbl" x="440" y="510">超級電容／鋰離子電容（LIC）</text>
      <g data-seg="${P}" data-part="psu_scap">
        <rect class="part bd" x="440" y="516" width="220" height="66" rx="6"/>
        ${scaps.join('')}
      </g>

      <!-- 沿路變小的光點：每經過一級就小一圈＝電壓一級一級降下來（示意，不代表任何數字） -->
      <circle r="6" fill="var(--dg-ink)" opacity=".92">
        <animateMotion dur="7s" repeatCount="indefinite" path="M126,208 L126,241 L${BBX + BBW / 2},241 L${BBX + BBW / 2},426 L520,426 L649,426"/>
        <animate attributeName="r" values="6;6;4.4;4.4;2.6;1.4" dur="7s" repeatCount="indefinite"/>
      </circle>

      <!-- 右側說明欄：引線拉到外側文字框，文字絕不壓在零件上（§5） -->
      ${labelRow(P, LBX, 150, 'PSU：交流 → 直流', '多顆並排、可熱插拔，壞一顆不用關機', 350, 200, LBW)}
      ${labelRow(C, LBX, 204, '匯流排 busbar：厚銅排不是電線', '電壓越低電流越大，銅排就要越粗', 412, 262, LBW)}
      ${labelRow(C, LBX, 258, '電源線組 power whip', '匯流排接到托盤；這一段是連接器與線材廠', 430, 426, LBW, 492)}
      ${labelRow(P, LBX, 312, '板上降壓 DC-DC／VRM（多相）', '把幾十伏特降到晶片核心要的零點幾伏特', 590, 386, LBW)}
      ${labelRow(P, LBX, 366, '終點：GPU／ASIC 核心', '電壓很低、電流很大，最後一段要靠近晶片', 692, 418, LBW)}
      ${labelRow(P, LBX, 420, '超級電容／LIC：最短的那一段', '負責瞬間的電流尖峰，更長的交給 BBU', 660, 550, LBW)}
      ${labelRow(P, LBX, 474, 'BBU：接在直流側、在機櫃裡', '電力一閃失就立刻頂上，爭取時間寫回資料', 360, 588, LBW)}
      <text class="cap" x="${LBX}" y="532">★ UPS 接在交流側、機櫃外；BBU 在直流側、</text>
      <text class="cap" x="${LBX}" y="550">　 機櫃內。兩者是互補的兩層，不是誰替代誰。</text>
      <text class="cap" x="${LBX}" y="568">★ BBU 與超級電容接在同一個直流節點上。</text>
      <text class="cap" x="${LBX}" y="596">★ 那顆光點每經過一級就小一圈 ＝ 電壓一級</text>
      <text class="cap" x="${LBX}" y="614">　 一級降下來（示意，不是比例）。</text>
      <text class="cap" x="${LBX}" y="642">★ 每一級都有損耗，而且是連乘的。</text>

      <!-- ================= 區 B：BBU 與 UPS 的位置對照 ＋ 四層防線時間軸 ================= -->
      <g data-seg="${P}" data-part="psu_place">
        <rect class="part frame" x="16" y="672" width="464" height="200" rx="8"/>
        <text class="hd" x="28" y="696">② BBU 不是小一號的 UPS：接的位置本來就不同</text>
        <text class="sub" x="28" y="716">兩者是互補的兩層，不是替代；也有 UPS ＋ BBU 的混合架構。</text>
        <text class="sub" x="26" y="742" style="fill:var(--dg-ink-3)">名稱</text>
        <text class="sub" x="168" y="742" style="fill:var(--dg-ink-3)">接在哪一側</text>
        <text class="sub" x="250" y="742" style="fill:var(--dg-ink-3)">櫃內還是櫃外</text>
        <text class="sub" x="354" y="742" style="fill:var(--dg-ink-3)">管哪一段時間</text>
        ${place}
      </g>
      <g data-seg="${P}" data-part="psu_time">
        <rect class="part frame" x="16" y="884" width="464" height="168" rx="8"/>
        <text class="hd" x="28" y="908">四層防線，各自管一段時間（由短到長）</text>
        ${timeline}
        <text class="cap" x="120" y="1020">時間越來越長 →</text>
        <path class="thin" d="M120,1026 H440" marker-end="url(#psuAr)" stroke="var(--dg-accent)"/>
        <text class="cap" x="28" y="1044" style="fill:var(--dg-warn)">★ 這條軸不標秒數、也不按比例：公開來源說法不一致，講的對象也可能不同。</text>
      </g>

      <!-- ================= 區 C：兩欄架構對照（§3-C：不准混成一張）================= -->
      <text class="hd" x="500" y="696">③ 兩種機櫃配電架構並排：右邊那一欄少掉一級</text>
      <text class="sub" x="500" y="716">兩欄的匯流排用同一個比例尺畫（粗細 ∝ 1 ÷ 電壓），只表達關係，不是實際尺寸。</text>
      <path class="hair" d="M738,726 V1010"/>
      <g data-seg="${P}" data-part="psu_arch">
        <text class="lbl" x="${AC1}" y="744">現行：機櫃內約 50–54 V</text>
        <text class="lbl" x="${AC2}" y="744">800 V 高壓直流（HVDC）</text>
        ${archBox(AC1, 0, '機房交流配電', '交流進機櫃')}
        ${archBox(AC1, 1, '機櫃內電源架', '交流 → 直流 約 50–54 V')}
        ${archBox(AC1, 2, '直流匯流排', '約 50–54 V（粗）', busBar(AC1, 2, 54))}
        ${archBox(AC1, 3, '板上 DC-DC／VRM', '降到晶片核心電壓')}
        ${archBox(AC1, 4, 'GPU／ASIC 晶片', '約 1 V 以下')}
        ${archBox(AC2, 0, '周界整流：交流 → 800 V', '在機房周界就整流成直流')}
        ${archBox(AC2, 2, '直流匯流排', '800 V（細）', busBar(AC2, 2, 800))}
        ${archBox(AC2, 3, '板上降壓', '級數依設計而異')}
        ${archBox(AC2, 4, 'GPU／ASIC 晶片', '約 1 V 以下')}
        <text class="sub" x="${AC2 + 10}" y="${slot(1) + 17}" style="fill:var(--dg-warn)">← 少掉這一級</text>
        <text class="sub" x="${AC2 + 10}" y="${slot(1) + 33}" style="fill:var(--dg-warn)">不必在機櫃內再轉一次</text>
      </g>
      <text class="cap" x="500" y="1032">依公開資料，800 V 高壓直流規劃 2027 年起支援百萬瓦級機櫃 ——</text>
      <text class="cap" x="500" y="1050">是未來式，不是現在已經在跑的架構；目前量產機櫃仍以約 50–54 V 為主。</text>
      <text class="sub" x="500" y="1078">為什麼要跳到 800 V：</text>
      <text class="sub" x="500" y="1096">① 機櫃功率一路往上，低電壓送大功率就要用很粗的銅排</text>
      <text class="sub" x="500" y="1114">② 把電壓拉高，同樣的銅可以送更多功率</text>
      <text class="sub" x="500" y="1132">③ 在機房周界就整流成直流，省掉中間幾次轉換、也少掉幾次損耗</text>
      <text class="cap" x="500" y="1156" style="fill:var(--dg-warn)">※ 省銅的量化說法有兩組、基準完全不同，所以這張圖只寫定性、不寫數字。</text>

      <!-- ================= 區 D：CRPS 型 PSU ＋ 卡緣連接器 ＋ 80 PLUS 效率表 ================= -->
      <text class="hd" x="16" y="1196">④ CRPS 型 PSU：後端是卡緣連接器，不是一束電線</text>
      <g data-seg="${P}" data-part="psu_crps">
        <g class="p3" transform="translate(100,1256)">${box(0, 0, 0, IW, ID, IH)}${isoFront}${isoEdge}</g>
      </g>
      <text class="sub" x="16" y="1356">CRPS 把 PSU 標準化：尺寸、卡緣連接器</text>
      <text class="sub" x="16" y="1374">與管理介面照同一套規格，所以不同家的</text>
      <text class="sub" x="16" y="1392">可以互換，也才做得到 N＋1 與熱插拔。</text>
      <g data-seg="${P}" data-part="psu_cardedge">
        <text class="lbl" x="264" y="1226">卡緣連接器（card-edge）</text>
        <rect class="part bd2" x="270" y="1236" width="186" height="52" rx="3"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(j =>
      `<rect class="gold" x="${278 + j * 13}" y="1242" width="7" height="14" rx="1"/>
           <rect class="gold" x="${278 + j * 13}" y="1268" width="7" height="14" rx="1"/>`).join('')}
        <path class="thin" d="M270,1262 H456"/>
      </g>
      <text class="sub" x="264" y="1308">上下兩排鍍金接點（示意，數量非實物）</text>
      <text class="sub" x="264" y="1326">推進去就接上 —— 熱插拔的前提</text>
      <text class="sub" x="264" y="1344">主機也從這裡讀電壓、電流與告警</text>

      <!-- ⚠ 條件那三行**一定要包在同一個群組裡**（§6-N2：效率百分比只准出現在效率表裡）。
           寫在群組外面的話，驗收會判成「效率表以外的地方出現了百分比」——
           而那正是市占率那種數字混進來的入口。順便把框畫到把它們包住，
           讀者也才不會把「230 V／50% 負載」讀成跟這張表無關的另一段話。 -->
      <g data-seg="${P}" data-part="psu_eff">
        <rect class="part frame" x="500" y="1204" width="476" height="232" rx="8"/>
        <text class="hd" x="512" y="1228">⑤ 80 PLUS 效率等級：管的是 PSU 那一級</text>
        <text class="sub" x="518" y="1250" style="fill:var(--dg-ink-3)">等級</text>
        <text class="sub" x="696" y="1250" style="fill:var(--dg-ink-3)">非冗餘型</text>
        <text class="sub" x="832" y="1250" style="fill:var(--dg-ink-3)">冗餘型</text>
        ${effRows}
        <text class="cap" x="512" y="1382" style="fill:var(--dg-warn)">★ 條件：230 V 輸入、50% 負載率。同一個等級在不同輸入電壓與負載率下門檻不同。</text>
        <text class="cap" x="512" y="1400">★ Titanium 95% 與 96% 不是打架 —— 是非冗餘型與冗餘型兩套組態，條件一樣。</text>
        <text class="cap" x="512" y="1418">※ 匯流排與板上 DC-DC 各級的通用效率值查不到公開來源，只在 PSU 這一級標效率。</text>
      </g>

      <!-- ================= 區 E：流程列（格 1 與格 2 之間那條分界線，§3-D）================= -->
      <text class="hd" x="16" y="1456">⑥ 供電路徑五格</text>
      <g><rect class="bd" x="16" y="1468" width="180" height="40" rx="7" stroke="var(--dg-psu-off)"/>
        <text class="lbl offtx" x="28" y="1484">交流進</text>
        <text class="sub offtx" x="28" y="1500">設施配電（＋機房 UPS）</text></g>
      <path class="hair" d="M202,1460 V1520"/>
      ${processBar(208, 1468, [{ seg: P, t: 'PSU／電源架', s: '交流 → 直流' },
      { seg: C, t: '匯流排', s: '櫃內直流分配（＋BBU）' },
      { seg: P, t: '板上 DC-DC／VRM', s: '降到核心電壓' },
      { seg: P, t: '晶片', s: 'GPU／ASIC' }], 180)}
      <text class="sub" x="16" y="1540" style="fill:var(--dg-warn)">↑ 這條線的左邊是機房基礎設施（不在這條產業鏈上），右邊才是這條鏈上的東西。</text>

      <!-- ================= 區 F：三塊結論框 ================= -->
      <rect class="frame" x="16" y="1562" width="314" height="154" rx="8"/>
      <text class="hd" x="28" y="1586">為什麼每一級的效率都是錢</text>
      <text class="sub" x="28" y="1608">電從牆上到晶片要經過好幾級，</text>
      <text class="sub" x="28" y="1626">每一級都有損耗，而且是連乘的。</text>
      <text class="sub" x="28" y="1644">損耗變成熱，又要再花錢散掉</text>
      <text class="sub" x="28" y="1662">（回到液冷與氣冷那兩張圖）。</text>
      <text class="sub" x="28" y="1680">所以資料中心願意為更高的效率等級</text>
      <text class="sub" x="28" y="1698">付更多錢，也願意為此改整套架構。</text>

      <rect class="frame" x="346" y="1562" width="304" height="154" rx="8"/>
      <text class="hd" x="358" y="1586">這張圖上誰做哪一塊</text>
      <text class="sub" x="358" y="1608">PSU／電源架／板上 DC-DC／BBU／</text>
      <text class="sub" x="358" y="1626">800 V 電源櫃 →「電源」這一格。</text>
      <text class="sub" x="358" y="1644">匯流排 busbar 與 power whip →</text>
      <text class="sub" x="358" y="1662">「連接器／線材」這一格，</text>
      <text class="sub" x="358" y="1680">不是電源廠做的。機櫃 → 系統組裝。</text>
      <text class="sub" x="358" y="1698">設施側與 UPS 不在這條鏈上。</text>

      <rect class="frame" x="666" y="1562" width="310" height="154" rx="8"/>
      <text class="hd" x="678" y="1586">這張圖沒有回答的事</text>
      <text class="sub" x="678" y="1608">① 各家的 PSU 市占率：兩個來源給</text>
      <text class="sub" x="678" y="1626">　 兩個數字、都沒有可查證出處，</text>
      <text class="sub" x="678" y="1644">　 所以一個百分比都不寫。</text>
      <text class="sub" x="678" y="1662">② BBU 到底撐多久：三個來源三個</text>
      <text class="sub" x="678" y="1680">　 答案、口徑還不一致 → 不標秒數。</text>
      <text class="sub" x="678" y="1698">③ 良率、單價、成本：查不到，不編。</text>

      <text class="cap" x="16" y="1740">示意圖，非實物比例｜方塊大小與匯流排粗細僅表達關係，不是實際尺寸</text>
      <text class="cap" x="16" y="1758">時間軸不標秒數：公開來源對 BBU 的持續時間說法不一致</text>
      <text class="cap" x="16" y="1776">點零件篩到的是「供應鏈環節」，不是整個族群；「電源」這一格目前收錄兩家台股（2308 台達電、2301 光寶科）。</text>
      <text class="cap" x="16" y="1794" style="fill:var(--dg-warn)">★ BBU 尚未建檔：供應鏈設定裡 AI 伺服器鏈沒有 BBU 環節，點 BBU 零件篩到的是「電源」這一格，不是做 BBU 的那幾家。</text>
    </svg>`;
  }

  window.DG.register('server_psu', {
    level: 'group', chain: 'ai_server',
    name: '電源：PSU、匯流排、板上降壓與 BBU',
    draw: serverPsu, native: 980, scene: null,
    q: '牆上的電進來，到 GPU 核心的零點幾伏特，中間降壓幾次、每一級是誰做的？BBU 跟機房 UPS 又差在哪？',
  });
})();
