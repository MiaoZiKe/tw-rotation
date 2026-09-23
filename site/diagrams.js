/* 產品剖析圖（原創示意 SVG，含動畫）。每個零件帶 data-seg = supply_chain.yaml 的環節 id；
   零件顏色由 industry.js 依環節色（App.L.scolor）注入 --c，所以剖析圖、環節色標、關聯圖、族群卡片顏色一致。
   版面規則：零件畫在中間、說明文字排在右側欄位用引線接過去，文字絕不疊在零件上。 */
(function () {
  'use strict';
  /* 畫面上真正用的環節色。--c 是 industry.js 用 inline style 寫在零件上的環節色（inline 贏過任何樣式表，
     所以不能直接覆寫它）；--cc 是消費端的換算結果：深色＋科技 ＝ 原色，其餘組合往 --dg-seg-mix 混
     （螢光組印在紙底會刺眼、壓深組印在深底會消失）。--ce 是等角零件沒有環節色時的預設色。*/
  const CC = 'var(--cc,var(--c,var(--ce,var(--dg-iso-c))))';
  /* 主角零件的環境光落影（閱讀模式才有值）：畫圖的人把主角包進 D.shadow(inner) 就好；
     這個 filter 用 feDropShadow 而不是 CSS drop-shadow，是因為它可以指定 dy（光從上面來）。*/
  const SHADOW_DEFS = '<defs><filter id="dgSoftShadow" x="-12%" y="-12%" width="124%" height="130%">'
    + '<feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="var(--dg-drop)"/></filter></defs>';
  const STYLE = `<style>
    /* ================ 風格系統（art-director 2026-09-22，規格 docs/diagram_specs/_STYLE.md）================
       這段是每一張剖析圖共用的樣式表，**全部吃 :root 的 --dg-* token**，
       兩種模式（科技／閱讀）靠 html 的 data-dgpal 切換 —— 這裡一個色值都不寫。
       ⚠ 這段註解裡不准出現角括號：這個 style 是 SVG 裡的 style，
         瀏覽器會把它當標記解析，寫一個像標籤的東西進去會把整張樣式表吃掉（DECISIONS #231）。*/
    .dg{font-family:"Noto Sans TC",sans-serif;--dg-accent:var(--dg-accent-2d)}
    /* --cc 的定義處。零件群組裡的強調色＝那個環節的顏色；群組外（流程箭頭、良率曲線）就是 --dg-accent-2d。
       寫在 :root 的話 var(--c) 會在 :root 就被解析掉，每個零件自己的環節色永遠吃不到。*/
    .dg [data-seg]{--cc:var(--c,var(--dg-accent-2d))}
    .dg .p3,.dg .stn,.dg .scode{--cc:var(--c,var(--ce,var(--dg-accent-2d)))}
    :root[data-dgpal="read"] .dg [data-seg],:root[data-theme="light"] .dg [data-seg]{
      --cc:color-mix(in srgb,var(--c,var(--dg-accent-2d)) var(--dg-seg-k,100%),var(--dg-seg-mix,#000))}
    :root[data-dgpal="read"] .dg .p3,:root[data-dgpal="read"] .dg .stn,:root[data-dgpal="read"] .dg .scode,
    :root[data-theme="light"] .dg .p3,:root[data-theme="light"] .dg .stn,:root[data-theme="light"] .dg .scode{
      --cc:color-mix(in srgb,var(--c,var(--ce,var(--dg-accent-2d))) var(--dg-seg-k,100%),var(--dg-seg-mix,#000))}
    .dg [data-seg],.dg .p3{--dg-accent:var(--cc)}
    /* 字級一律走 :root 的 --dg-fs-*（art-director 擁有）：科技 12px 起、閱讀 13px 起，這裡不准出現第二套數字。*/
    .dg text{fill:var(--dg-ink-2);font-size:var(--dg-fs-min)}
    .dg .ttl{font-size:var(--dg-fs-ttl);font-weight:700;fill:var(--dg-ink);letter-spacing:.02em}
    .dg .cap{font-size:var(--dg-fs-min);fill:var(--dg-ink-3)}
    .dg .lbl{font-size:var(--dg-fs-lbl);fill:var(--dg-ink);font-weight:600}
    .dg .sub{font-size:var(--dg-fs-min);fill:var(--dg-ink-3)}
    .dg .tag{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);fill:var(--cc,var(--dg-ink-3));letter-spacing:.04em}
    .dg .mono{font-family:"JetBrains Mono",monospace}
    /* ---- 零件 ---- */
    .dg [data-seg]{cursor:pointer;transition:opacity .2s}
    .dg [data-seg] .part{transition:stroke .15s,filter .15s;stroke:color-mix(in srgb,${CC} 55%,var(--dg-part-mix))}
    /* B1（art-director 2026-09-21）：發光半徑收成變數。單一環節的圖（.dg1）與閱讀模式 --dg-glow:none 直接關掉。*/
    .dg [data-seg]:hover .part,.dg [data-seg].sel .part{stroke:${CC};stroke-width:2.2;filter:var(--dg-glow,drop-shadow(0 0 7px ${CC}))}
    .dg.dg1{--dg-glow:none}
    /* 兩層高亮（2026-09-21 晚間）：.sel-part ＝ 你剛剛點的那一個（最強）；.sel ＝ 同環節其餘（次強）。*/
    .dg [data-seg].sel-part .part{stroke:${CC};stroke-width:var(--dg-part-w,3.6);
      filter:var(--dg-glow,drop-shadow(0 0 var(--dg-part-r,11px) ${CC}))}
    .dg [data-seg].sel-part .lbl,.dg [data-seg].sel-part .hd{font-weight:700}
    .dg.dg1.haspart [data-seg].sel:not(.sel-part){opacity:var(--dg-sib-o,.4)}
    .dg [data-seg].sel .lbl,.dg [data-seg]:hover .lbl{fill:${CC}}
    .dg [data-seg] .dot{fill:${CC}}
    .dg [data-seg].dim{opacity:.3}
    .dg .hero{filter:var(--dg-hero-sh,none)}
    /* ---- 引線：細線 ＋ 端點小圓（D.pointer）。科技的端點帶光暈（--dg-node-glow），閱讀只留實心圓點 ---- */
    .dg .leader{stroke:var(--dg-lead,color-mix(in srgb,${CC} 55%,var(--dg-line-mix)));stroke-width:var(--dg-lead-w,1);fill:none}
    .dg [data-seg].sel .leader,.dg [data-seg]:hover .leader,.dg .p3.sel .leader,.dg .p3:hover .leader{stroke:${CC};stroke-width:var(--dg-lead-sel-w,1.6)}
    .dg .anchor{fill:var(--card-c,${CC});stroke:var(--dg-bg);stroke-width:1;r:var(--dg-node-r,2.8px);
      filter:var(--dg-glow,drop-shadow(0 0 var(--dg-node-glow,3px) var(--card-c,${CC})))}
    :root[data-dgpal="read"] .dg .anchor{filter:none}
    /* v2 版面（Andy 2026-09-22「左右對齊、版面更滿、依螢幕大小變化」）：卡片離開 SVG 變成 HTML（index.html 的 .dgc），
       SVG 裡只留「資料來源」的 .lrow.ext（永遠不畫）與畫布上的錨點群組 .anc（編號圓點／小圓）。
       .anc 沒有零件身分：它的 sel／sel-part／dim 是 diagrams.js 從對應的卡片鏡射過來的，點它＝點卡片。*/
    .dg .ext{display:none}
    .dg .anc{--cc:var(--c,var(--dg-accent-2d));--card-c:var(--dg-card-c,var(--cc,var(--dg-ink)));cursor:pointer;transition:opacity .2s}
    :root[data-dgpal="read"] .dg .anc,:root[data-theme="light"] .dg .anc{--cc:color-mix(in srgb,var(--c,var(--dg-accent-2d)) var(--dg-seg-k,100%),var(--dg-seg-mix,#000))}
    .dg .anc .anchor.no{r:9.5px;stroke-width:1.2}
    .dg .anc .non{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);font-weight:700;fill:var(--dg-no-ink);dominant-baseline:central;text-anchor:middle;pointer-events:none}
    .dg .anc.dim{opacity:.3}
    .dg .anc.sel-part .anchor{stroke:var(--dg-ink);stroke-width:2}
    :root[data-dgpal="read"] .dg .anc .anchor.no{fill:color-mix(in srgb,var(--card-c) 18%,var(--dg-bg));stroke:var(--card-c)}
    :root[data-dgpal="read"] .dg .anc.sel-part .anchor.no{fill:color-mix(in srgb,var(--card-c) 34%,var(--dg-bg));stroke:var(--dg-ink)}
    /* ---- 說明卡片（labelRow／lrow3／processBar／chainLink 共用）：圓角矩形、細邊、左側色條、編號圓點 ----
       --card-c ＝ 這張卡的元件色。畫圖的人用 inline style 的 --dg-card-c 或 data-dgcolor 指定，
       沒指定就落回環節色 --cc，再沒有就 --dg-ink。3D 的 DOM 標籤（index.html 的 .lbl3d）吃同一個介面。
       SVG 的 rect 吃不到 backdrop-filter，所以這裡的「磨砂玻璃」＝半透明實色（--dg-card-f）。*/
    .dg .lrow{cursor:pointer;--card-c:var(--dg-card-c,var(--cc,var(--dg-ink)))}
    .dg .p3:not(.lrow) rect.bg{fill:transparent}
    .dg .p3:not(.lrow):hover rect.bg,.dg .p3:not(.lrow).sel rect.bg{fill:color-mix(in srgb,${CC} 13%,transparent)}
    .dg .p3:not(.lrow).sel-part rect.bg{fill:color-mix(in srgb,${CC} 28%,transparent)}
    .dg .lrow rect.bg,.dg rect.card{fill:var(--dg-card-f);stroke:color-mix(in srgb,var(--card-c,var(--dg-ink)) 40%,var(--dg-card-s));stroke-width:1;
      rx:var(--dg-card-r,8px);filter:var(--dg-card-sh,none);transition:fill .15s,stroke .15s}
    .dg .lrow .cbar{fill:var(--card-c)}
    .dg .lrow .no{fill:var(--card-c);r:var(--dg-no-r,9.5px)}
    .dg .lrow .non{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);font-weight:700;fill:var(--dg-no-ink);dominant-baseline:central;text-anchor:middle}
    .dg .lrow:hover rect.bg,.dg .lrow.sel rect.bg{stroke:var(--card-c);fill:color-mix(in srgb,var(--card-c) 12%,var(--dg-card-f))}
    /* 主角那一張卡：底再深一階 ＋ 光暈（科技）／落影（閱讀）。要排在上面那條之後，不然特異性一樣會被蓋掉。*/
    .dg .lrow.sel-part rect.bg{stroke:var(--card-c);stroke-width:1.6;fill:color-mix(in srgb,var(--card-c) 26%,var(--dg-card-f));
      filter:var(--dg-glow,drop-shadow(0 0 var(--dg-card-glow-r,6px) color-mix(in srgb,var(--card-c) 60%,transparent)))}
    :root[data-dgpal="read"] .dg .lrow.sel-part rect.bg{filter:var(--dg-card-sh,none)}
    /* 閱讀模式的卡片：標題不換成元件色（深灰字才讀得到，色相由色條／圓點／邊框扛），
       編號圓點改成「粉彩底 ＋ 元件色的環 ＋ 深灰數字」—— 白字印在壓深過的粉彩上量出來只有 4.05:1。*/
    :root[data-dgpal="read"] .dg [data-seg].sel .lbl,:root[data-dgpal="read"] .dg [data-seg]:hover .lbl,
    :root[data-dgpal="read"] .dg .p3.sel .lbl,:root[data-dgpal="read"] .dg .p3:hover .lbl{fill:var(--dg-ink)}
    :root[data-dgpal="read"] .dg .lrow .no{fill:color-mix(in srgb,var(--card-c) 18%,var(--dg-bg));stroke:var(--card-c);stroke-width:1.2}
    .dg [data-chain]{cursor:pointer} .dg [data-chain]:hover rect{stroke:var(--dg-accent-2d)}
    /* ---- 流動（光／液／訊號）：虛線在跑。閱讀模式不發光，科技模式也只讓端點與主角發光，線本身不發光 ---- */
    .dg .flow{stroke-dasharray:7 7;animation:dgdash 1.4s linear infinite}
    .dg .flow.slow{animation-duration:2.4s} .dg .flow.fast{animation-duration:.9s}
    .dg .flow.rev{animation-direction:reverse}
    @keyframes dgdash{to{stroke-dashoffset:-28}}
    .dg .blink{animation:dgblink 1.6s ease-in-out infinite}
    .dg .blink.b2{animation-delay:.5s}.dg .blink.b3{animation-delay:1s}
    @keyframes dgblink{0%,100%{opacity:.2}50%{opacity:1}}
    .dg .pulse{animation:dgpulse 2.6s ease-in-out infinite}
    @keyframes dgpulse{0%,100%{opacity:.35}50%{opacity:1}}
    .dg .spin{transform-box:fill-box;transform-origin:center;animation:dgspin 2.6s linear infinite}
    @keyframes dgspin{to{transform:rotate(360deg)}}
    .dg .scan{animation:dgscan 3.2s linear infinite}
    @keyframes dgscan{0%{transform:translateY(-60px)}100%{transform:translateY(60px)}}
    .dg .heat{animation:dgheat 2.8s ease-in-out infinite}
    @keyframes dgheat{0%,100%{opacity:.15;transform:translateY(0)}50%{opacity:.6;transform:translateY(-5px)}}
    .dg .drop{animation:dgdrop 2.2s linear infinite}
    .dg .drop.d2{animation-delay:.7s}.dg .drop.d3{animation-delay:1.4s}
    @keyframes dgdrop{0%{opacity:0;transform:translateY(0)}15%{opacity:1}85%{opacity:1}100%{opacity:0;transform:translateY(46px)}}
    /* ---- 等角 3D：每個零件永遠帶自己的環節色，三個面往 --dg-sh1/2/3 混（閱讀模式這三個是亮灰、中灰、深灰 ＝ 粉彩） ---- */
    .dg .p3{--m1:66%;--m2:42%;--m3:26%;--ce:var(--dg-iso-c);cursor:pointer;transition:opacity .2s}
    .dg .p3:hover,.dg .p3.sel{--m1:94%;--m2:66%;--m3:46%}
    .dg .p3.sel-part{--m1:100%;--m2:78%;--m3:58%}
    .dg .p3.dim{opacity:.2}
    .dg .f1{fill:color-mix(in srgb,${CC} var(--m1,66%),var(--dg-sh1))}
    .dg .f2{fill:color-mix(in srgb,${CC} var(--m2,42%),var(--dg-sh2))}
    .dg .f3{fill:color-mix(in srgb,${CC} var(--m3,26%),var(--dg-sh3))}
    .dg .p3 .part{stroke:color-mix(in srgb,${CC} 40%,var(--dg-sh0));stroke-width:.8;stroke-linejoin:round;transition:stroke .15s,filter .15s}
    .dg .p3:hover .part,.dg .p3.sel .part{stroke:${CC};stroke-width:1.5;filter:var(--dg-glow,drop-shadow(0 0 6px ${CC}))}
    /* 等角零件不動描邊寬（它的線本來就只有 .8，拉到 3.6 會變成一團黑）—— .sel-part 靠 --m1/2/3 再亮一階 ＋ 暈開半徑加大 */
    .dg .p3.sel-part .part{filter:var(--dg-glow,drop-shadow(0 0 var(--dg-part-r,11px) ${CC}))}
    .dg .p3 .etch{stroke:color-mix(in srgb,${CC} 60%,transparent);fill:none;stroke-width:.9}
    .dg .p3 .lit{fill:color-mix(in srgb,${CC} 78%,transparent)}
    .dg .p3 .lbl{fill:var(--dg-ink)} .dg .p3:hover .lbl,.dg .p3.sel .lbl{fill:${CC}}
    .dg .p3 .dot{fill:${CC}}
    .dg .grd{stroke:var(--dg-grd);fill:none;stroke-width:.7}
    .dg .axis{stroke:var(--dg-axis);stroke-width:1;fill:none;stroke-dasharray:3 4}
    /* ---- 題材供應鏈圖：上游／中游／下游三段 + 站點 + 流動彩帶 + 個股標籤（全部改吃 --dg-band-*／slot／rib／chip） ---- */
    .dg3 .band rect{fill:var(--dg-band-f);stroke:var(--dg-band-s)}
    .dg3 .band text{font-size:var(--dg-fs-min);font-weight:600;fill:var(--dg-ink-2);letter-spacing:.03em}
    .dg3 .band.b0 rect{fill:var(--dg-b0-f);stroke:var(--dg-b0-s)} .dg3 .band.b0 text{fill:var(--dg-b0-ink)}
    .dg3 .band.b1 rect{fill:var(--dg-b1-f);stroke:var(--dg-b1-s)} .dg3 .band.b1 text{fill:var(--dg-b1-ink)}
    .dg3 .band.b2 rect{fill:var(--dg-b2-f);stroke:var(--dg-b2-s)} .dg3 .band.b2 text{fill:var(--dg-b2-ink)}
    .dg3 .stn .slot{fill:var(--dg-slot-f);stroke:var(--dg-slot-s)}
    .dg3 .stn:hover .slot,.dg3 .stn.sel .slot{fill:color-mix(in srgb,${CC} 10%,var(--dg-slot-f2));stroke:${CC}}
    .dg3 .stn.dim{opacity:.26}
    .dg3 .shadow{fill:var(--dg-drop)}
    .dg3 .rib{stroke-width:9;stroke-linecap:round}
    .dg3 .rib.bg{stroke:var(--dg-rib-bg)}
    .dg3 .rib.flow{stroke:var(--dg-rib-flow);stroke-dasharray:10 16;animation:dgdash 2.2s linear infinite}
    .dg3 .scode{cursor:pointer}
    .dg3 .scode rect{fill:color-mix(in srgb,${CC} 14%,var(--dg-chip-f));stroke:color-mix(in srgb,${CC} 42%,transparent)}
    .dg3 .scode text{font-size:var(--dg-fs-min);fill:var(--dg-chip-ink);font-weight:600}
    .dg3 .scode:hover rect{fill:color-mix(in srgb,${CC} 34%,var(--dg-chip-f));stroke:${CC}}
    .dg3 .scode:hover text{fill:var(--dg-ink)}
    .dg3 .step .num{fill:color-mix(in srgb,${CC} 55%,var(--dg-num-mix));stroke:color-mix(in srgb,${CC} 70%,transparent)}
    .dg3 .step .nn{font-size:var(--dg-fs-min);font-weight:700;fill:var(--dg-ink);font-family:"JetBrains Mono",monospace}
    /* ---- 量產圖專屬：.hd（區塊小標）與 .num（數字）。12px 是 .dg 的基準，.dgm 不再負責字級 ---- */
    .dgm .hd{font-size:var(--dg-fs-hd);font-weight:700;fill:var(--dg-ink)}
    .dgm .num{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min);fill:var(--dg-ink-2)}
    .dgm .frame{fill:var(--dg-frame-f);stroke:var(--dg-frame-s)}
    .dgm .warn{fill:var(--dg-warn)}
    /* B2（art-director 2026-09-21）：電荷疊色的透明度 .12（.26 會把陶瓷的色相整個推掉）*/
    .dgm .chg{fill:var(--dg-accent);fill-opacity:var(--dg-chg-a,.12)}
    /* ---- 漸進揭露：章節列（收合 ≠ 刪除，每一條列上都寫著裡面有什麼） ---- */
    .dg .dgfold{cursor:pointer}
    .dg .dgfold .fbar{fill:var(--dg-frame-f);stroke:var(--dg-frame-s);transition:fill .15s,stroke .15s}
    .dg .dgfold:hover .fbar{stroke:var(--dg-accent);fill:color-mix(in srgb,var(--dg-accent) 10%,transparent)}
    .dg .dgfold .fsign{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-hd);font-weight:700;fill:var(--dg-accent)}
    .dg .dgfold .fhint{fill:var(--dg-ink-3)}
    .dg .dgfold:hover .fhint,.dg .dgfold:hover .hd{fill:var(--dg-accent)}
    /* ---- 2.5D 材質（D.fx：玻璃板／發光／光束；參考圖 docs/diagram_refs/2d_panel_dark_light.webp）----
       兩種模式共用同一支函式，差別只在這幾個 --fx-* 旋鈕：科技＝深底、玻璃較透、光束發光；
       閱讀＝米白底、玻璃較白（sheen 拉高）、光束只留約四成的柔光（diagram_refs/README.md 蓋掉了「閱讀不發光」）。
       sheen 用 --dg-sn（錫，兩種模式都是近白）、暗面用 --dg-sh0，所以一個色值都不寫死。*/
    .dg{--fx-body:.6;--fx-sheen:.3;--fx-shade:.36;--fx-edge:.55;--fx-hl:.5;--fx-glow-a:.85;--fx-shadow-a:.9}
    :root[data-dgpal="read"] .dg{--fx-body:.7;--fx-sheen:.58;--fx-shade:.16;--fx-edge:.5;--fx-hl:.75;--fx-glow-a:.38;--fx-shadow-a:.6}
    /* 裝飾面（sheen／邊線／高光／暗面）不吃滑鼠：真滑鼠點在方塊正中央要落到 .part 那一塊上，不是落到疊在上面的 sheen
       （Playwright 的 click 打的是元素外框中心，2026-09-22 就是這樣點不到 ABF 膜的） */
    .dg .fxg .fxs,.dg .fxg .fxst,.dg .fxg .fxe,.dg .fxg .fxh,.dg .fxg .fxr{pointer-events:none}
    .dg .fxg .fxb{fill:var(--fxc,var(--dg-steel));fill-opacity:var(--fx-body)}
    .dg .fxg .fxt{fill:var(--fxc,var(--dg-steel));fill-opacity:calc(var(--fx-body) * .8)}
    .dg .fxg .fxs{fill:url(#fxSheen)} .dg .fxg .fxst{fill:url(#fxSheenT)}
    .dg .fxg .fxr{fill:var(--dg-sh0);fill-opacity:var(--fx-shade)}
    .dg .fxg .fxe{fill:none;stroke:color-mix(in srgb,var(--fxc,var(--dg-steel)) 55%,var(--dg-sn));stroke-opacity:var(--fx-edge);stroke-width:1;stroke-linejoin:round}
    .dg .fxg .fxh{fill:none;stroke:var(--dg-sn);stroke-opacity:var(--fx-hl);stroke-width:1;stroke-linecap:round}
    .dg .fxsh{fill:var(--dg-drop);opacity:var(--fx-shadow-a)}
    .dg .fxbeam .fxb-glow{fill:none;stroke:var(--fxc,var(--dg-accent-2d));stroke-width:calc(var(--fxw,2.2) * 3);opacity:var(--fx-glow-a);stroke-linecap:round;stroke-linejoin:round}
    .dg .fxbeam .fxb-core{fill:none;stroke:var(--fxc,var(--dg-accent-2d));stroke-width:var(--fxw,2.2);opacity:.95;stroke-linecap:round;stroke-linejoin:round}
    .dg .fxbeam .fxb-flow{fill:none;stroke:var(--dg-sn);stroke-width:calc(var(--fxw,2.2) * .55);stroke-dasharray:5 11;opacity:.9;stroke-linecap:round;animation:dgdash 1.6s linear infinite}
    .dg .fxbeam .fxdh{fill:var(--fxc,var(--dg-accent-2d));fill-opacity:calc(var(--fx-glow-a) * .35)}
    .dg .fxbeam .fxd{fill:var(--fxc,var(--dg-accent-2d));stroke:var(--dg-sn);stroke-width:.8;stroke-opacity:var(--fx-hl)}
  </style>` + SHADOW_DEFS;

  /* ================================================================ 零件身分（兩層高亮用）
     問題：高亮以前只綁 `data-seg`，所以「點一個零件」在程式裡等於「選一個環節」。
     多環節的圖還說得通，但**單一環節的圖**（MLCC 14 個零件全掛 passive_comp，
     docs/diagram_plan.md 後面 13 張多數也是）就退化成「14 個全部 .sel、0 個 dim」——
     點下去畫面完全沒有事情發生。要修就得先認得出「你剛剛點的是哪一個」。

     `data-part` 是那個身分。沒有標 data-part 的舊零件（說明列、流程列、半導體與
     AI 伺服器那兩張的大部分群組）由 stampParts() 自動補一個「環節 id ＋ 文件順序」，
     所以**不用先把 13 張圖都補完 data-part**，這個行為就已經到位。
     自動補的 key 只在同一張圖裡有意義（2D 與 3D 對不起來），
     真的要讓 2D 點完切到 3D 還是同一個狀態，就替兩邊標同一個 data-part。*/
  function stampParts(host) {
    if (!host) return;
    host.querySelectorAll('svg').forEach((svg) => {
      /* v2：先把 .lrow.ext 變成 HTML 卡片（它們的零件身分搬到卡片上），再替 SVG 裡剩下的零件蓋 dgkey。
         縮圖（.xmini）與非 .dgwrap 的容器不外掛：那裡只要主角。*/
      /* ★ 2026-09-22（restyle-w1b）：同一個 #prodDiagram 會連續裝好幾張圖（AI 伺服器鏈的圖別切換列
         在同一頁換圖，industry.js 只換 host.innerHTML）。v2 的判斷以前寫在 host.dataset.dgv2 上，
         換第二張 v2 的圖時那個旗標還在 → externalize 直接 return → 第二張的卡片全部沒外掛。
         改成「看這張 svg 自己有沒有被包進 .dgcanvas」；上一張留下的觀察器與 class 由 teardownV2 收掉。*/
      const v2 = svg.classList.contains('rs') && host.classList && host.classList.contains('dgwrap') && !host.closest('.xmini');
      if (v2) externalize(host, svg);
      else if (host.dataset && host.dataset.dgv2 === '1') teardownV2(host);   // 上一張是 v2、這一張不是：殘留清掉
      const ns = [].slice.call(svg.querySelectorAll('[data-seg]'));
      ns.forEach((n, i) => { n.dataset.dgkey = n.getAttribute('data-part') || (n.getAttribute('data-seg') + ':' + i); });
      /* 單一環節的圖自己判定，不要求畫圖的人記得加 class ——
         「忘了加」正是這個缺陷會被複製 13 次的原因。*/
      if (ns.length && new Set(ns.map(n => n.getAttribute('data-seg'))).size === 1) svg.classList.add('dg1');
      /* 卡片的元件色介面（docs/diagram_restyle_plan.md）：畫圖的人可以寫 data-dgcolor="#xxxxxx"，
         CSS 讀不到 data 屬性，這裡搬成 inline 的 --dg-card-c，STYLE 的 .lrow 就吃得到。*/
      svg.querySelectorAll('[data-dgcolor]').forEach((n) => { n.style.setProperty('--dg-card-c', n.getAttribute('data-dgcolor')); });
      /* v2 的 HTML 卡片不在 svg 裡，上面那圈蓋不到它：這裡補零件身分（有 data-part 就用它，沒有就用錨點 id）。
         同一個 key 只有這張卡片有 —— 錨點群組沒有身分，所以「主角剛好一個」仍然成立。*/
      host.querySelectorAll('.dgc[data-seg]').forEach((c) => { if (!c.dataset.dgkey) c.dataset.dgkey = c.getAttribute('data-part') || ('card:' + c.dataset.anc); });
      wireFolds(svg);
    });
  }

  /* ================================================================ 漸進揭露（章節展開／收合）
     為什麼掛在 stampParts 裡：`site/industry.js` 是別人也在改的檔，而 stampParts 本來就是
     「圖插進 DOM 之後會被呼叫一次」的那個掛點（wireDiagram 會呼叫它），
     所以收合機制可以完全住在 diagrams.js 裡，不必去動 industry.js。

     版面怎麼算（兩種宣告法，這裡都吃）
     ----------------------------------
     不論哪一種，這裡只做一件事：**由上往下重新堆一次**，收合的段落跳過，
     最後把 viewBox 的高度改掉。差別只在「每一段佔掉的垂直範圍」從哪裡來：

       ① 手寫（`data-y0` / `data-y1`）：段落畫在自己的自然位置，範圍寫在屬性上。
          好處是 JS 沒跑到也不會壞 —— 靜態 SVG 本身就是一份全部展開、座標正確的版面。
       ② 自動（`data-auto="1"`，`D.fold()` 產出的就是這種）：範圍由 `getBBox()` 量出來。
          ⚠ 代價要講清楚：自動模式的**章節列畫在區域座標 y=0**，位置完全靠 transform，
            所以「JS 沒跑到」時那幾條列會疊在圖的最上面。目前沒有這種路徑
            （`wireDiagram()` 一定會呼叫 `stampParts()`），但哪天有人要做不跑 JS 的縮圖，
            這就是要先處理的那一件事。換到的是：十三張量產圖的段落大量用 transform 疊出來，
            手算 y0/y1 等於把同一份座標抄第二遍，抄錯不會報錯、只會歪掉。

     ⚠ 章節列刻意**不掛 data-seg** —— 掛了的話 wireDiagram 會把它接成「點零件」，
       按一下展開就順便把成分股篩掉了。*/
  /* ================================================================ v2 版面：卡片離開 SVG（Andy 2026-09-22）
     externalize(host, svg)：
       1. 把 svg 包進 .dgcanvas；svg 寬度＝viewBox 寬（原尺寸，不放大 —— 放大會讓高度破 700）
       2. text.ext（標題／說明）→ .dghead
       3. g.lrow.ext → .dgc（HTML 卡片），放進 .dgcol.l／.dgcol.r；零件身分（data-seg／part／codes／alias）搬到卡片上，
          SVG 群組拿掉身分 —— highlight 與點擊都只認卡片，主角永遠剛好一個
       4. .dglead（絕對定位的 svg）畫引線：卡片邊緣 → 畫布欄外側 → 錨點。ResizeObserver 一動就重算，
          章節開合（viewBox 變高）、切模式也重算。卡片在畫布下面（單欄）時不畫引線，靠編號對照
       5. 錨點群組 .anc 鏡射卡片的 sel／sel-part／dim 與 --c（MutationObserver），點錨點＝點卡片
     版面本身（幾欄、多寬）全在 index.html 的 .dgv2 容器查詢裡，這裡不量寬度。*/
  const SVGNS = 'http://www.w3.org/2000/svg';
  /* 把上一張 v2 圖留在容器上的東西收掉：觀察器（不收的話每次 resize 都會對著已經被丟掉的 DOM 重算）、
     tw:dgpal 監聽器、容器上的 class 與旗標。externalize 開頭與「換成非 v2 的圖」都會呼叫。*/
  function teardownV2(host) {
    const o = host.__dgv2;
    if (o) {
      try { if (o.ro) o.ro.disconnect(); } catch (e) { /* 忽略 */ }
      try { if (o.mo) o.mo.disconnect(); } catch (e) { /* 忽略 */ }
      window.removeEventListener('tw:dgpal', o.later); window.removeEventListener('resize', o.later);
      host.__dgv2 = null;
    }
    delete host.dataset.dgv2; host.classList.remove('dgv2', 'dg1', 'haspart');
  }
  function externalize(host, svg) {
    if (svg.closest('.dgcanvas')) return;                 // 這一張已經外掛過（同一張圖被 stamp 兩次）
    const exts = [].slice.call(svg.querySelectorAll('g.lrow.ext'));
    const heads = [].slice.call(svg.querySelectorAll('text.ext'));
    if (!exts.length && !heads.length) return;
    teardownV2(host);                                     // 上一張圖（同一個容器）的殘留先清掉
    host.dataset.dgv2 = '1'; host.classList.add('dgv2');
    const vb = svg.viewBox && svg.viewBox.baseVal;
    /* 容器查詢只對**後代**生效（元素不能查自己的寬），所以 .dgwrap 當容器、格線另外包一層 .dggrid */
    const grid = document.createElement('div'); grid.className = 'dggrid';
    svg.parentNode.insertBefore(grid, svg);
    const canvas = document.createElement('div'); canvas.className = 'dgcanvas';
    grid.appendChild(canvas); canvas.appendChild(svg);
    if (vb && vb.width) { svg.style.width = vb.width + 'px'; svg.style.minWidth = vb.width + 'px'; svg.style.maxWidth = 'none'; }
    host.style.overflowX = ''; host.style.overflowY = '';        // 捲動交給 .dgcanvas，不是整個容器
    if (heads.length) {
      const hd = document.createElement('div'); hd.className = 'dghead';
      heads.forEach((t) => { const e = document.createElement(t.classList.contains('ttl') ? 'b' : 'span'); e.textContent = t.textContent; hd.appendChild(e); });
      grid.insertBefore(hd, canvas);
    }
    /* 卡片全部住在一個 .dgcards 裡，左右欄（.dgcol.l／.r）只是分組：
       三欄時 .dgcards 是 display:contents，兩個 .dgcol 各自站到格線的 l／r；
       併成一欄（兩欄堆疊、單欄）時反過來 —— .dgcol 變 display:contents，卡片直接排進 .dgcards，
       並照 data-order（＝編號；公式 0、警語 99）排，讀者才對得到圖上圓點的順序。*/
    const cards = document.createElement('div'); cards.className = 'dgcards'; grid.appendChild(cards);
    const cols = {};
    const col = (side) => {
      const k = side === 'l' ? 'l' : 'r';
      if (!cols[k]) { const c = document.createElement('div'); c.className = 'dgcol ' + k; cols[k] = c; if (k === 'l') cards.insertBefore(c, cards.firstChild); else cards.appendChild(c); }
      return cols[k];
    };
    const pairs = [];
    exts.forEach((g) => {
      const card = document.createElement('div');
      card.className = 'dgc' + (g.dataset.note ? ' note' : '') + (g.dataset.warn ? ' warn' : '');
      ['seg', 'part', 'codes', 'alias', 'dgcolor'].forEach((k) => { if (g.dataset[k] != null) card.dataset[k] = g.dataset[k]; });
      card.dataset.anc = g.dataset.anc;
      if (g.dataset.order != null) card.style.order = g.dataset.order;
      if (g.dataset.dgcolor) card.style.setProperty('--dg-card-c', g.dataset.dgcolor);
      const c0 = g.style.getPropertyValue('--c'); if (c0) card.style.setProperty('--c', c0);
      if (g.dataset.no != null) { const n = document.createElement('span'); n.className = 'no'; n.textContent = String(g.dataset.no).padStart(2, '0'); card.appendChild(n); }
      const bd = document.createElement('div'); bd.className = 'bd';
      const t = g.querySelector('text.lbl'); if (t) { const b = document.createElement('b'); b.textContent = t.textContent; bd.appendChild(b); }
      g.querySelectorAll('text.sub').forEach((x) => { const i = document.createElement('i'); i.textContent = x.textContent; bd.appendChild(i); });
      card.appendChild(bd);
      col(g.dataset.side).appendChild(card);
      ['seg', 'part', 'codes', 'alias'].forEach((k) => { delete g.dataset[k]; });   // 身分搬走，SVG 那份只剩資料來源
      const anc = svg.querySelector(`g.anc[data-for="${g.dataset.anc}"]`);
      if (anc) {
        if (c0) anc.style.setProperty('--c', c0);
        anc.addEventListener('click', (e) => { e.stopPropagation(); card.click(); });
        pairs.push({ card, anc });
      }
    });
    const lead = document.createElementNS(SVGNS, 'svg'); lead.setAttribute('class', 'dglead'); grid.appendChild(lead);
    const relayout = () => {
      const hr = grid.getBoundingClientRect();
      const ox = hr.left, oy = hr.top;
      lead.setAttribute('width', grid.clientWidth); lead.setAttribute('height', grid.clientHeight);
      const cr = canvas.getBoundingClientRect();
      let out = '';
      pairs.forEach(({ card, anc }) => {
        ['sel', 'sel-part', 'dim'].forEach((k) => anc.classList.toggle(k, card.classList.contains(k)));
        const cc = card.style.getPropertyValue('--c'); if (cc) anc.style.setProperty('--c', cc);
        const dot = anc.querySelector('.anchor'); if (!dot) return;
        const a = dot.getBoundingClientRect(), c = card.getBoundingClientRect();
        if (!a.width || !c.width) return;
        const nb = card.querySelector('.no'); const nr = nb ? nb.getBoundingClientRect() : null;
        const cy = (nr ? nr.top + nr.height / 2 : c.top + c.height / 2) - oy;
        const acx = a.left + a.width / 2 - ox, acy = a.top + a.height / 2 - oy, ar = a.width / 2 + 1;
        let d = null;
        if (c.right <= cr.left + 2) d = `M${(c.right - ox).toFixed(1)},${cy.toFixed(1)} H${(cr.left - ox - 8).toFixed(1)} V${acy.toFixed(1)} H${(acx - ar).toFixed(1)}`;
        else if (c.left >= cr.right - 2) d = `M${(c.left - ox).toFixed(1)},${cy.toFixed(1)} H${(cr.right - ox + 8).toFixed(1)} V${acy.toFixed(1)} H${(acx + ar).toFixed(1)}`;
        if (!d) return;                                   // 卡片在畫布下面（單欄）：靠編號對照，不畫引線
        const cls = (card.classList.contains('sel-part') ? 'sel-part' : card.classList.contains('sel') ? 'sel' : '') + (card.classList.contains('dim') ? ' dim' : '');
        out += `<path d="${d}" class="${cls}"${cc ? ` style="--c:${cc}"` : ''}/>`;
      });
      lead.innerHTML = out;
      host.classList.toggle('dg1', svg.classList.contains('dg1'));
      host.classList.toggle('haspart', svg.classList.contains('haspart'));
    };
    svg.__dgRelayout = relayout;
    let queued = false;
    const later = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; relayout(); }); };
    const obs = { later, ro: null, mo: null };
    if (window.ResizeObserver) { obs.ro = new ResizeObserver(later); obs.ro.observe(host); }
    else window.addEventListener('resize', later);
    if (window.MutationObserver) {
      obs.mo = new MutationObserver((recs) => {
        if (recs.some((r) => r.target === svg || (r.target.classList && r.target.classList.contains('dgc')))) later();
      });
      obs.mo.observe(host, { attributes: true, subtree: true, attributeFilter: ['class', 'style'] });
    }
    window.addEventListener('tw:dgpal', later);
    host.__dgv2 = obs;                                    // 換下一張圖時 teardownV2 靠這個把觀察器收掉
    relayout(); requestAnimationFrame(relayout); setTimeout(relayout, 300);
  }

  /* ================================================================ 量完再縮（風格系統 2026-09-22）
     閱讀模式把字級整組升一階（12 → 13px），為 12px 排的整行說明會多出 5～8%，
     原本剛好貼著畫布右緣的那幾行就頂出去、被 overflow:hidden 切掉。
     這裡對每一個「右緣超出 viewBox」的 text 設 textLength（spacingAndGlyphs），
     只准壓 ≤ 12% —— 再多字會變形，那是版面要改的事，不是這裡該硬撐的。
     切模式（tw:dgpal 事件）、開章節（wireFolds 的 paint）之後都會重算。
     這是共用機制，沒有動任何一張圖的幾何；科技模式下量出來 0 行需要壓。*/
  function fitTexts(svg) {
    const vb = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 0; if (!vb) return;
    const lim = vb - 4;
    svg.querySelectorAll('text').forEach((t) => {
      if (t.hasAttribute('textLength')) { t.removeAttribute('textLength'); t.removeAttribute('lengthAdjust'); }
      let b, m; try { b = t.getBBox(); m = t.getCTM(); } catch (e) { return; }
      if (!b || !b.width || !m) return;
      let want;
      const row = t.parentNode && t.parentNode.closest ? t.parentNode.closest('.lrow') : null;
      const card = row ? row.querySelector('rect.bg') : null;
      if (card && !t.classList.contains('non')) {
        // 卡片裡的字：不准超出卡片右緣（同一個群組、同一個座標系，直接比）
        const cr = parseFloat(card.getAttribute('x')) + parseFloat(card.getAttribute('width')) - 6;
        if (b.x + b.width <= cr) return;
        want = cr - b.x;
      } else {
        const sx = m.a || 1;                                 // 局部座標到畫布座標的縮放（只有 translate 時是 1）
        const left = m.a * b.x + m.c * b.y + m.e, right = left + b.width * sx;
        if (right <= lim) return;
        want = (lim - left) / sx;
      }
      if (want / b.width < 0.88) return;
      t.setAttribute('lengthAdjust', 'spacingAndGlyphs');
      t.setAttribute('textLength', want.toFixed(1));
    });
  }
  window.addEventListener('tw:dgpal', () => { document.querySelectorAll('svg.dg').forEach(fitTexts); });

  /* 一條章節列佔掉的垂直空間（框 36 ＋ 列距 6）。
     2026-09-22 從 46 收到 42：一張圖最多四條，省下來的 16px 直接變成畫布高度的餘裕，
     而 36px 的框裝 13.5px 的標題還有 11px 的上下留白，點擊區也還夠大。*/
  const FOLD_H = 42;
  const FOLD_PT = 14, FOLD_PB = 22;  // 自動量測時，內容上緣／下緣各留的空白

  /* 章節內容的範圍，**跳過走 animateMotion 的元素**（restyle-w1b 2026-09-22 抓到的）。
     processBar 那顆光點是 `circle r=3` 沒有 cx/cy、位置全靠 animateMotion；getBBox() 量的是元素自己的座標系，
     不含動畫的位移，所以永遠回 (-3,-3)。一個章節裡只要有流程列，整段的 bbox.y 就變成 -3，
     wireFolds 算出來的 off 跟著錯 —— 章節一打開，內容被推到下面一千多 px 的地方，中間一片空白
     （MLCC 的 ③、伺服器電源的 ④、ABF 的 ③ 都中）。這裡改成遞迴取聯集、跳過帶 animateMotion 的元素。*/
  function bodyBBox(el) {
    /* 做法：把「直接帶 animateMotion 的元素」暫時 display:none（getBBox 不算 display:none 的東西），
       量整個群組的 getBBox()（它會把子孫的 transform 算進去 —— 章節裡的 translate 群組很多，自己遞迴會漏掉），
       量完再還原。*/
    const moving = [].slice.call(el.querySelectorAll('animateMotion')).map((a) => a.parentNode).filter(Boolean);
    const saved = moving.map((n) => n.getAttribute('display'));
    moving.forEach((n) => n.setAttribute('display', 'none'));
    let b = null;
    try { b = el.getBBox(); } catch (e) { b = null; }
    moving.forEach((n, i) => { if (saved[i] == null) n.removeAttribute('display'); else n.setAttribute('display', saved[i]); });
    return b;
  }

  function wireFolds(svg) {
    if (svg.dataset.dgFold === '1') { fitTexts(svg); return; }   // 同一張圖被 stamp 兩次不要重複綁，但字要重量
    const all = [].slice.call(svg.querySelectorAll('g.dgfold[data-fold],g.dgbody[data-fold]'));
    if (!all.length) { fitTexts(svg); return; }
    /* ★ 自動量測（art-director 2026-09-22）：掛 `data-auto="1"` 的段落**不在原始碼裡宣告 y0/y1**，
       由這裡量 getBBox() 得到。為什麼要這樣做：十三張量產圖的段落大量用 transform 疊出來
       （`<g transform="translate(0,D)">` 套好幾層），手算 y0/y1 等於把同一份座標抄第二遍 ——
       抄錯了不會報錯，只會版面歪掉，而且以後別人動一行內容就得回來重抄一次。
       量不到（圖還沒可見、瀏覽器還沒排版）就**整支放棄，不留半套狀態**：
       沒有標記 dgFold，下一次 stampParts 會再試一次，在那之前畫面維持
       「全部展開、座標正確」的原始版面 —— 這正是 DECISIONS #232 要的那個保險。
       MLCC 那張手寫 y0/y1 的版本完全不受影響（沒有 data-auto，走下面的 else）。*/
    const rows = [];
    for (let i = 0; i < all.length; i++) {
      const g = all[i], body = g.classList.contains('dgbody');
      let off, h;
      if (g.getAttribute('data-auto') === '1') {
        if (body) {
          let b = null;
          try { b = bodyBBox(g); } catch (e) { b = null; }
          if (!b || !(b.height > 0)) { fitTexts(svg); return; }   // 量不到 → 放棄，維持全部展開
          off = b.y - FOLD_PT; h = b.height + FOLD_PT + FOLD_PB;
        } else {
          // 章節列畫在自己的區域座標 0～36，位置整個交給下面的重新堆疊
          off = 0; h = FOLD_H;
        }
      } else {
        const y0 = parseFloat(g.getAttribute('data-y0')), y1 = parseFloat(g.getAttribute('data-y1'));
        if (!Number.isFinite(y0) || !Number.isFinite(y1)) continue;
        off = y0; h = y1 - y0;
      }
      rows.push({ el: g, id: g.getAttribute('data-fold'), body, off, h });
    }
    const bodies = rows.filter((r) => r.body);
    if (!rows.length || !bodies.length) { fitTexts(svg); return; }
    svg.dataset.dgFold = '1';
    const bars = rows.filter((r) => !r.body);
    /* 第一條章節列擺在哪裡 —— 兩個候選取**大**的那一個：
         ① 第一段內容的上緣往上退一列（手寫 y0/y1 的版本沿用舊算法，
            MLCC 算出來跟以前一模一樣：638 − 46 ＝ 592，所以這條改寫沒有動到既有版面）
         ② **永遠看得到那一段（§1）的底部**再往下 8px
       只取 ① 會踩到一個很難看的錯：原始碼裡 §1 與第一段內容之間如果不到 46px，
       章節列就會壓在 §1 的最後幾行字上面。取 max 之後，「原始碼留多少空隙」不再是
       畫圖的人要記得的事 —— 這正是這一版要拿掉的那種隱形規矩。*/
    let solidBottom = -Infinity;
    const inFold = (n) => { for (let p = n; p && p !== svg; p = p.parentNode) { if (p.hasAttribute && p.hasAttribute('data-fold')) return true; } return false; };
    [].slice.call(svg.children).forEach((c) => {
      if (c.tagName === 'defs' || c.tagName === 'style' || inFold(c)) return;
      let b = null; try { b = c.getBBox(); } catch (e) { b = null; }
      if (b && b.height >= 0 && Number.isFinite(b.y)) solidBottom = Math.max(solidBottom, b.y + b.height);
    });
    /* ★ 候選 ① 只對**手寫 y0/y1** 的段落有意義（內容畫在自己的自然位置）。自動量測的段落會被整段重新平移，
       它的靜態 y 只是「JS 沒跑到時的保險版面」—— 拿來決定章節列的位置，等於讓保險版面的留白變成正式版面的空白。
       （restyle-w1b 2026-09-22：修掉 bodyBBox 的 animateMotion 假 bbox 之後才看出來 —— MLCC 的 574 是靠那個假 bbox
       把候選 ① 壓到負數才成立的；改成只看手寫段落，MLCC／PSU／ABF 三張的章節列都回到 §1 底部 ＋ 8。）*/
    const manual = bodies.filter((r) => r.el.getAttribute('data-auto') !== '1');
    let base = Math.max(manual.length ? Math.min.apply(null, manual.map((r) => r.off)) - FOLD_H : -Infinity,
      solidBottom > -Infinity ? solidBottom + 8 : -Infinity);
    if (!Number.isFinite(base)) base = Math.min.apply(null, bodies.map((r) => r.off)) - FOLD_H;
    const W = (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) || 980;
    const PAD = 10;               // 最後一條章節列底下留的空白
    const open = new Set();                           // 預設全部收合
    function paint() {
      let cur = base;
      rows.forEach((r) => {
        if (r.body && !open.has(r.id)) { r.el.setAttribute('display', 'none'); return; }
        r.el.removeAttribute('display');
        r.el.setAttribute('transform', 'translate(0,' + (cur - r.off).toFixed(1) + ')');
        cur += r.h;
      });
      bars.forEach((r) => {
        const on = open.has(r.id);
        r.el.classList.toggle('open', on);
        // 章節列寬度跟著畫布寬（v2 的畫布可以是 660 而不是 980；fold()／foldBar() 畫的是 948）
        const fb = r.el.querySelector('.fbar'); if (fb) fb.setAttribute('width', W - 32);
        const hx = r.el.querySelector('.fhint'); if (hx) hx.setAttribute('x', W - 32);
        const sg = r.el.querySelector('.fsign'), hi = r.el.querySelector('.fhint');
        if (sg) sg.textContent = on ? '－' : '＋';
        // 收合時寫「裡面有什麼」，展開時寫「怎麼收回去」—— 兩種狀態都看得出還能做什麼
        if (hi) {
          const full = on ? '－ 收合這一段' : ('＋ 展開：' + (r.el.getAttribute('data-hint') || ''));
          hi.textContent = full;
          /* ★ 提示文字自己讓路（art-director 2026-09-22）。
             標題靠左、提示靠右，兩邊都是變動長度的中文 —— 只要有人把標題寫長一點
             就會撞在一起，而且是**畫面上兩行字疊在一起**那種最難看的錯。
             2026-09-22 第一版就撞了兩張（載板 27px、伺服器電源 452px）。
             與其訂一條「標題不准超過幾個字」的隱形規矩（沒有人會記得，也沒有東西會擋），
             不如讓它在執行期自己量：撞到就把提示從尾巴砍掉、補上刪節號，
             砍到剩六個字還是撞就整個藏起來（標題本來就講得完整）。*/
          const tt = r.el.querySelector('.hd');
          if (tt) {
            let txt = full, guard = 0;
            const hit = () => { try { const a = tt.getBBox(), b = hi.getBBox(); return a.x + a.width + 12 > b.x; } catch (e) { return false; } };
            while (hit() && txt.length > 6 && guard++ < 60) { txt = txt.slice(0, -3) + '…'; hi.textContent = txt; }
            hi.setAttribute('display', hit() ? 'none' : 'inline');
            // 砍短了就把全文掛成 tooltip（v2 的 660 寬畫布幾乎每一條都會砍）
            let tt2 = r.el.querySelector(':scope > title');
            if (!tt2) { tt2 = document.createElementNS('http://www.w3.org/2000/svg', 'title'); r.el.appendChild(tt2); }
            tt2.textContent = full;
          }
        }
      });
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + Math.round(cur + PAD));
      fitTexts(svg);                                  // 剛展開的段落也要量一次
      if (svg.__dgRelayout) svg.__dgRelayout();       // v2：錨點位置變了，引線要重畫
    }
    bars.forEach((r) => {
      r.el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (open.has(r.id)) open.delete(r.id); else open.add(r.id);
        paint();
      });
    });
    paint();
  }

  /* 章節列（**舊寫法，新圖請用下面的 `fold()`**）：自己算好 y、自己配一個
     `<g class="dgbody" data-fold data-y0 data-y1>`。2026-09-22 之後沒有人再用它 ——
     留著只是因為它還掛在 `window.DG` 上，外面的圖檔可能有人接。*/
  function foldBar(id, y, title, hint, h) {
    h = h || 46;
    return `<g class="dgfold" data-fold="${id}" data-hint="${hint}" data-y0="${y}" data-y1="${y + h}">
      <rect class="fbar" x="16" y="${y}" width="948" height="38" rx="9"/>
      <text class="fsign" x="38" y="${y + 24}" text-anchor="middle">＋</text>
      <text class="hd" x="58" y="${y + 24}">${title}</text>
      <text class="sub fhint" x="948" y="${y + 24}" text-anchor="end">＋ 展開：${hint}</text>
    </g>`;
  }
  /* ★ 章節（章節列 ＋ 內容）一次寫完，y 座標交給 wireFolds() 在執行期量（art-director 2026-09-22）。

     為什麼要有這一支，而不是照 MLCC 那樣手寫 y0/y1
     ------------------------------------------------
     Andy 2026-09-22：「所有 2D 3D 圖的圖片及文字縮小一半…希望能一次看到完整資訊」。
     「文字縮小一半」跟 12px 下限（DECISIONS #227）在物理上衝突 —— 12 → 6px 沒人讀得懂，
     所以**縮的是版面不是字級**：把一張 1800px 高的圖收成 700px 以內，其餘收進章節。
     十三張量產圖要一起改，手寫 y0/y1 就是把每張圖的座標抄第二遍（而且是抄在別的地方），
     抄錯不會報錯、只會歪掉。改成量 bbox：**畫圖的人只要決定「哪一段收起來、收起來要寫什麼」**。

     用法（inner 就是原本那一段的原始碼，一個字都不用改）：
       ${D.fold('psu2', '② BBU 與四層防線', 'BBU 接的位置、四層防線各管多久', `...原本那一段...`)}

     `hint` 要寫**裡面有什麼**，不是「更多」——「更多」等於叫人先點開再猜，
     那就不是收納，是把東西藏起來（DECISIONS #232 紅線 2）。*/
  function fold(id, title, hint, inner) {
    return `<g class="dgfold" data-fold="${id}" data-hint="${hint}" data-auto="1">
      <rect class="fbar" x="16" y="0" width="948" height="36" rx="9"/>
      <text class="fsign" x="38" y="23" text-anchor="middle">＋</text>
      <text class="hd" x="58" y="23">${title}</text>
      <text class="sub fhint" x="948" y="23" text-anchor="end">＋ 展開：${hint}</text>
    </g><g class="dgbody" data-fold="${id}" data-auto="1">${inner}</g>`;
  }

  /* 這個零件是不是「被點的那一個」。`data-alias` 是給「2D 拆成兩塊、3D 只有一塊」那種
     對不齊的情況用的（例如 MLCC 的端電極：2D 有消費級與車規兩張放大剖面，3D 只有一圈端電極）。*/
  function partHit(node, key) {
    if (!key || !node) return false;
    if (node.dataset.dgkey === key) return true;
    /* ★ 2026-09-22：也比 `data-part`。
       `stampParts()` 只替**掛了 `data-seg`** 的節點蓋 `dgkey`，
       所以「刻意不掛環節」的圖（矽晶圓、第三代半導體 —— 那兩條鏈在
       supply_chain.yaml 裡根本沒有對應的環節，硬掛就是宣稱錯的公司）
       上面的零件永遠拿不到 dgkey，比對必然落空 → 點了小卡開得起來、主角卻不會亮。
       dgkey 本來就是從 data-part 推出來的，所以直接比它是同一件事，不是放寬。*/
    if (node.dataset.part === key) return true;
    const al = node.getAttribute('data-alias');
    return !!al && al.split(',').indexOf(key) >= 0;
  }

  /* ================================================================ 共用元件（風格系統 2026-09-22）
     規格：docs/diagram_specs/_STYLE.md §3～§5。API 跟改造之前一模一樣，只多了可選的編號 `no`：
       labelRow(seg, x, y, title, sub, tx, ty, w, dropY, no)
       lrow3(o, x, y, w, i, no)
       processBar(x, y, steps, w)   steps[i].no 可選
     視覺全部在 STYLE 的 .lrow／.card／.leader／.anchor 那幾條，兩種模式靠 token 換。*/

  /* 引線（D.pointer）：從零件上的錨點 (ax,ay) 走到卡片邊緣 (bx,by)，細線 ＋ 端點小圓。
     預設「先水平到轉折點、再垂直、再水平進卡片邊緣」；傳 drop 就改成「先垂直走到 drop、再水平過去」
     （繞過主角而不是穿過它 —— MLCC 的「側邊餘白」就是這樣）。
     opts：{elbow: 轉折點的 x（預設 bx−6）, drop: 先垂直走到的 y, node:false ＝ 不畫端點}
     端點的樣式全在 STYLE 的 .anchor：科技帶光暈、閱讀只留實心圓點。*/
  function pointer(ax, ay, bx, by, opts) {
    opts = opts || {};
    const elbow = opts.elbow != null ? opts.elbow : bx - 6;
    const d = opts.drop != null
      ? `M${ax},${ay} L${ax},${opts.drop} L${elbow},${opts.drop} L${elbow},${by} L${bx},${by}`
      : `M${ax},${ay} L${elbow},${ay} L${elbow},${by} L${bx},${by}`;
    return `<path class="leader" d="${d}"/>` + (opts.node === false ? '' : `<circle class="anchor" cx="${ax}" cy="${ay}" r="2.8"/>`);
  }
  /* 卡片左側：色條 ＋（編號圓點｜原本的小圓點）。沒給編號時小圓點的位置跟改造前一樣，文字也不動；
     給了編號才把文字往右挪 3px 讓出圓點（編號卡是新東西，沒有既有版面要守）。*/
  function cardHead(x, y, no) {
    const bar = `<rect class="cbar" x="${x - 8}" y="${y - 6}" width="3" height="22" rx="1.5"/>`;
    if (no == null) return bar + `<circle class="dot" cx="${x + 5}" cy="${y - 2}" r="4"/>`;
    const n = String(no).padStart(2, '0');
    return bar + `<circle class="no" cx="${x + 6.5}" cy="${y + 5}" r="9.5"/><text class="non" x="${x + 6.5}" y="${y + 5}">${n}</text>`;
  }
  /* 右側說明卡：卡片 ＋ 標題 ＋ 副標 ＋ 引線到零件上的 (tx,ty)。**共用函式，每一張圖都在用。**
     行距 16px、底框 40（art-director 2026-09-21 量過的，字級升到 12 之後 13px 行距會相貼）。
     `dropY`（P4-a）：錨點在主體另一側時傳它，引線先垂直走到 dropY 再水平過去，繞過主角。
     引線停在卡片左緣（x−8），不再伸進卡片裡 —— 卡片現在是有底色的，線進去會看起來像畫錯。*/
  /* ================================================================ v2：卡片離開 SVG（Andy 2026-09-22）
     「這邊的版面需要左右對齊，可以適當分配左右間隔，讓版面更滿，看起來舒適，並且會依據螢幕大小變化」。
     做法：畫圖的人照舊呼叫 labelRow／lrow3，只多傳 `side`（'l'／'r'）——
     那一列就不再畫在 SVG 裡，而是留下一個「資料來源」群組（.lrow.ext，永遠不顯示）
     ＋ 畫布上的錨點（.anc：有編號就是編號圓點、沒有就是小圓）。
     stampParts() 之後由 externalize() 把它變成 HTML 卡片（index.html 的 .dgc），
     放進畫布左右兩欄，並用一層 svg（.dglead）畫引線 —— 寬度變了引線跟著重算，沒有寫死座標。
     卡片是 HTML，所以文字自己換行、欄寬多寬都不會擠；SVG 只剩畫布本身（MLCC 從 980 縮到 660 寬）。
     互動一個都沒少：卡片本身就是 `[data-seg]`／`[data-part]` 節點，industry.js 的
     wireDiagram／highlightSegments 把它當零件對待（點卡片亮零件、點零件亮卡片、點背景恢復）。*/
  let ANC = 0;
  function extRow(o) {
    const id = 'anc' + (++ANC);
    const subs = Array.isArray(o.sub) ? o.sub : (o.sub ? [o.sub] : []);
    const attrs = `data-anc="${id}" data-side="${o.side === 'l' ? 'l' : 'r'}"`
      + (o.seg ? ` data-seg="${o.seg}"` : '') + (o.part ? ` data-part="${o.part}"` : '')
      + (o.codes && o.codes.length ? ` data-codes="${o.codes.join(',')}"` : '') + (o.alias ? ` data-alias="${o.alias}"` : '')
      + (o.color ? ` data-dgcolor="${o.color}"` : '') + (o.no != null ? ` data-no="${o.no}"` : '')
      + (o.warn ? ' data-warn="1"' : '') + (o.note ? ' data-note="1"' : '')
      + ` data-order="${o.order != null ? o.order : (o.no != null ? o.no : (o.warn ? 99 : 50))}"`;
    const row = `<g class="lrow ext" ${attrs}><text class="lbl" x="0" y="0">${o.title}</text>${subs.map(t => `<text class="sub" x="0" y="0">${t}</text>`).join('')}</g>`;
    if (o.ax == null) return row;
    const n = o.no != null ? String(o.no).padStart(2, '0') : '';
    return row + `<g class="anc" data-for="${id}">` + (n
      ? `<circle class="anchor no" cx="${o.ax}" cy="${o.ay}" r="9.5"/><text class="non" x="${o.ax}" y="${o.ay}">${n}</text>`
      : `<circle class="anchor" cx="${o.ax}" cy="${o.ay}" r="2.8"/>`) + `</g>`;
  }
  /* 沒有錨點的說明卡（公式、結論、警語）。lines 可以是字串或陣列；warn＝警語樣式 */
  const note = (o) => extRow({ side: o.side, title: o.title, sub: o.lines, no: o.no, warn: o.warn, note: true, color: o.color, order: o.order });

  function labelRow(seg, x, y, title, sub, tx, ty, w, dropY, no, side) {
    if (side) return extRow({ seg, title, sub, no, side, ax: tx, ay: ty });
    w = w || 250;
    const L = x - 8, T = x + (no != null ? 19 : 16);
    return `<g class="lrow" data-seg="${seg}"><rect class="bg" x="${L}" y="${y - 15}" width="${w}" height="40" rx="8"/>
      ${tx != null ? pointer(tx, ty, L, y - 2, { elbow: x - 14, drop: dropY }) : ''}${cardHead(x, y, no)}
      <text class="lbl" x="${T}" y="${y + 2}">${title}</text><text class="sub" x="${T}" y="${y + 18}">${sub}</text></g>`;
  }
  /* 底部流程列：一串步驟卡片，帶移動的光點。步驟可以給 no（編號圓點）。
     B3（art-director 2026-09-21）：卡片高 40、標題 y+16、副標 y+32（行距 16px）。*/
  const PB_H = 40, PB_MID = 20, PB_ROW = 58;
  /* opts.cols：一列放幾格。窄畫布（660）放不下五格 184 寬的步驟，分成 3＋2 兩列，
     列與列之間用一條往下折的流動線接起來，光點沿著同一條折線跑。*/
  function processBar(x, y, steps, w, opts) {
    w = w || 150; const gap = 12, cols = (opts && opts.cols) || steps.length;
    const pos = steps.map((s, i) => ({ bx: x + (i % cols) * (w + gap), by: y + Math.floor(i / cols) * PB_ROW }));
    let dot = '';
    const boxes = steps.map((s, i) => {
      const { bx, by } = pos[i], num = s.no != null, tx = bx + (num ? 30 : 12);
      const no = num ? `<circle class="no" cx="${bx + 15}" cy="${by + PB_MID}" r="9.5"/><text class="non" x="${bx + 15}" y="${by + PB_MID}">${String(s.no).padStart(2, '0')}</text>` : '';
      let link = '';
      dot += (i ? ' L' : 'M') + `${bx},${by + PB_MID} L${bx + w},${by + PB_MID}`;
      if (i < steps.length - 1) {
        const nx = pos[i + 1];
        if (nx.by === by) link = `M${bx + w},${by + PB_MID} L${nx.bx},${by + PB_MID}`;
        else { link = `M${bx + w},${by + PB_MID} h6 V${by + PB_H + 9} H${nx.bx - 6} V${nx.by + PB_MID} h6`; dot += ` L${bx + w + 6},${by + PB_MID} L${bx + w + 6},${by + PB_H + 9} L${nx.bx - 6},${by + PB_H + 9} L${nx.bx - 6},${nx.by + PB_MID}`; }
      }
      return `<g class="step lrow" data-seg="${s.seg}"><rect class="part bg card" x="${bx}" y="${by}" width="${w}" height="${PB_H}" rx="7"/>${no}<text class="lbl" x="${tx}" y="${by + 16}">${s.t}</text><text class="sub" x="${tx}" y="${by + 32}">${s.s}</text></g>`
        + (link ? `<path class="flow fast" d="${link}" fill="none" stroke="var(--dg-accent)" stroke-width="var(--dg-flow-w,2)"/>` : '');
    }).join('');
    return `<g>${boxes}<circle r="3" fill="var(--dg-flow-dot)" opacity=".9"><animateMotion dur="${steps.length > cols ? 8 : 6}s" repeatCount="indefinite" path="${dot}"/></circle></g>`;
  }
  const chainLink = (chain, x, y, text) => `<g class="lrow" data-chain="${chain}"><rect class="bg card" x="${x}" y="${y}" width="${text.length * 13 + 26}" height="30" rx="8"/><text class="lbl" x="${x + 13}" y="${y + 19}" style="fill:var(--dg-accent-2d);font-weight:600">${text}</text></g>`;
  /* 爆炸拆解的間距：層與層之間要有「呼吸空間」（Andy 2026-09-22 的參考圖）。
       explode(n, {y0, h, gap}) → 2D 垂直拆解：回第 i 層的 y（由上往下），h 是每層高、gap 是呼吸空間
       explodeZ(heights, gap)  → 2.5D 垂直拆解：回每一層底面的 z（由下往上），heights 是每層厚度
     預設 gap 18：小於 12 看起來像疊在一起、大於 30 引線會拉太長（_STYLE.md §4）。*/
  const EXPLODE_GAP = 18;
  function explode(n, o) { o = o || {}; const y0 = o.y0 || 0, h = o.h || 24, gap = o.gap != null ? o.gap : EXPLODE_GAP; return Array.from({ length: n }, (_, i) => y0 + i * (h + gap)); }
  function explodeZ(hs, gap) { gap = gap != null ? gap : EXPLODE_GAP; let z = 0; return hs.map((h) => { const z0 = z; z += h + gap; return z0; }); }
  /* 主角的環境光落影：把主角包進去就好。閱讀模式吃 --dg-hero-sh（柔和落影），科技是 none。*/
  const shadow = (inner, cls) => `<g class="hero${cls ? ' ' + cls : ''}">${inner}</g>`;

  /* ================================================================ 等角 3D 工具箱
     投影：模型 x 往畫面右下、y 往畫面左下、z 往上。所有題材產品圖共用這一套，
     立體語言（光影、角度、厚度）才會一致，看起來才像同一套產品圖而不是十八張拼圖。
     三個面固定用 f1（頂，最亮）／f2（右，中）／f3（左，最暗），顏色一律由 --c 混出來，
     所以「點族群 → 零件同色」是免費的：改 --c 三個面一起變。 */
  const IX = 0.866, IY = 0.5;
  const px = (x, y) => (x - y) * IX;
  const py = (x, y, z) => (x + y) * IY - (z || 0);
  const P3 = (x, y, z) => px(x, y).toFixed(1) + ',' + py(x, y, z).toFixed(1);
  const fc = (cls, pts) => `<path class="part ${cls}" d="M${pts.join('L')}Z"/>`;
  // 把 2D 內容貼到 z 高度的水平面上（模型座標不變，交給矩陣壓成等角）
  const onTop = (z, inner) => `<g transform="matrix(${IX},${IY},${-IX},${IY},0,${-(z || 0)})">${inner}</g>`;
  /* 切開面用的兩個平面。剖析圖的重點常常在「切下去看到什麼」，
     而 onTop 只處理水平面，所以補這兩支：
       onXZ(x0,y0)：y = y0 的垂直面（沿 x 展開）—— 疊層剖面就畫在這上面
       onYZ(x0,y0)：x = x0 的垂直面（沿 y 展開）—— 側邊餘白那種「第三個方向」的東西
     兩支都把內容的局部座標定成 (u, v)：u 沿該平面的水平方向、v 就是高度 z。
     ★ 行列式是負的（鏡射），所以**不要把文字放進去**，文字會左右相反。*/
  const onXZ = (x0, y0) => `<g transform="translate(${px(x0, y0).toFixed(1)},${py(x0, y0, 0).toFixed(1)}) matrix(${IX},${IY},0,-1,0,0)">`;
  const onYZ = (x0, y0) => `<g transform="translate(${px(x0, y0).toFixed(1)},${py(x0, y0, 0).toFixed(1)}) matrix(${-IX},${IY},0,-1,0,0)">`;

  // 立方體：(x,y,z) 是底面近角，w/d/h 為 x/y/z 三個方向的長度
  function box(x, y, z, w, d, h, inner) {
    return fc('f2', [P3(x + w, y, z + h), P3(x + w, y + d, z + h), P3(x + w, y + d, z), P3(x + w, y, z)])
      + fc('f3', [P3(x + w, y + d, z + h), P3(x, y + d, z + h), P3(x, y + d, z), P3(x + w, y + d, z)])
      + fc('f1', [P3(x, y, z + h), P3(x + w, y, z + h), P3(x + w, y + d, z + h), P3(x, y + d, z + h)])
      + (inner ? onTop(z + h, inner) : '');
  }
  // 圓柱（馬達、變壓器、減速機、風扇軸）。inner 的座標原點是圓柱中心，方便畫扇葉／鏡頭。
  function cyl(x, y, z, r, h, inner) {
    const cx = px(x, y), cy = py(x, y, z + h), by = py(x, y, z);
    const rx = r * 1.2247, ry = r * 0.7071;
    return `<path class="part f2" d="M${(cx - rx).toFixed(1)},${cy.toFixed(1)} V${by.toFixed(1)} A${rx.toFixed(1)},${ry.toFixed(1)} 0 0 0 ${(cx + rx).toFixed(1)},${by.toFixed(1)} V${cy.toFixed(1)}Z"/>`
      + `<ellipse class="part f1" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}"/>`
      + (inner ? onTop(z + h, `<g transform="translate(${x},${y})">${inner}</g>`) : '');
  }
  // 立起來的面板（顯示器、天線陣列、太陽能板）：沿 x 展開、往 z 長高、厚度 t 沿 y
  function panel(x, y, z, w, h, t, inner) {
    return fc('f2', [P3(x + w, y, z + h), P3(x + w, y + t, z + h), P3(x + w, y + t, z), P3(x + w, y, z)])
      + fc('f1', [P3(x, y, z + h), P3(x + w, y, z + h), P3(x + w, y + t, z + h), P3(x, y + t, z + h)])
      + fc('f3', [P3(x, y, z), P3(x + w, y, z), P3(x + w, y, z + h), P3(x, y, z + h)])
      + (inner ? `<g transform="translate(${px(x, y).toFixed(1)},${py(x, y, z).toFixed(1)}) matrix(${IX},${IY},0,-1,0,0)">${inner}</g>` : '');
  }
  // 沿 3D 折線走的管路／訊號（傳入 [x,y,z] 陣列）
  const wire = (pts, cls, col, w) => `<path class="${cls || ''}" d="M${pts.map(p => P3(p[0], p[1], p[2])).join('L')}" fill="none" stroke="${col || 'var(--dg-accent-2d)'}" stroke-width="${w || 2}" stroke-linecap="round"/>`;
  // 地板格線（放在 onTop(0) 裡，讓場景站得住）
  function floor(w, d, step, x0, y0) {
    const a = []; x0 = x0 || 0; y0 = y0 || 0;
    for (let x = 0; x <= w; x += step) a.push(`M${x0 + x},${y0} L${x0 + x},${y0 + d}`);
    for (let y = 0; y <= d; y += step) a.push(`M${x0},${y0 + y} L${x0 + w},${y0 + y}`);
    return onTop(0, `<path class="grd" d="${a.join(' ')}"/>`);
  }
  // 頂面上的方格陣列（晶片 die、記憶體顆粒、電池芯）
  function cells(x, y, w, d, nx, ny, gap) {
    gap = gap == null ? 2 : gap;
    const cw = (w - gap * (nx + 1)) / nx, ch = (d - gap * (ny + 1)) / ny, a = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++)
      a.push(`<rect class="lit pulse" x="${(x + gap + i * (cw + gap)).toFixed(1)}" y="${(y + gap + j * (ch + gap)).toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="1" style="animation-delay:${(((i + j) % 6) * 0.34).toFixed(2)}s"/>`);
    return a.join('');
  }
  // 零件外框：把幾何、data-part（點了看個股）、data-seg（跟環節同色）綁在一起
  const p3 = (o, inner) => `<g class="p3" data-part="${o.id}"${o.codes && o.codes.length ? ` data-codes="${o.codes.join(',')}"` : ''}${o.seg ? ` data-seg="${o.seg}"` : ''}${o.chain ? ` data-chain="${o.chain}"` : ''}>${inner}</g>`;
  // 右側說明卡（3D 版：綁 data-part，不是 data-seg）。跟 labelRow 同一個卡片，只差身分是零件。
  function lrow3(o, x, y, w, i, no, side) {
    if (side) return extRow({ seg: o.seg, part: o.id, codes: o.codes, alias: o.alias, title: o.label, sub: o.sub, no, side, ax: o.ax != null ? o.ax.toFixed(1) : null, ay: o.ay != null ? o.ay.toFixed(1) : null });
    w = w || 262;
    // 每一列的轉折點錯開，不然七條引線的垂直段會疊成一條粗線，看起來像畫錯
    const elbow = x - 14 - (i || 0) * 8;
    const L = x - 8, T = x + (no != null ? 19 : 16);
    return `<g class="p3 lrow" data-part="${o.id}"${o.codes && o.codes.length ? ` data-codes="${o.codes.join(',')}"` : ''}${o.seg ? ` data-seg="${o.seg}"` : ''}>
      <rect class="bg" x="${L}" y="${y - 15}" width="${w}" height="40" rx="8"/>
      ${o.ax != null ? pointer(o.ax.toFixed(1), o.ay.toFixed(1), L, y - 2, { elbow }) : ''}${cardHead(x, y, no)}
      <text class="lbl" x="${T}" y="${y + 2}">${o.label}</text><text class="sub" x="${T}" y="${y + 18}">${o.sub || ''}</text></g>`;
  }

  /* ================================================================ 半導體鏈的 2D CoWoS 剖面：**已退場**（DECISIONS #234，2026-09-22）
     Andy：「圖二 圖三 是否重疊題材，是的話幫我刪除一個」。查證屬實 ——
     這裡原本的 `semiconductor()` 與 `site/dg/ai_adv_packaging.js` 畫的是**同一顆 CoWoS 封裝的剖面**，
     兩張自己宣告的問題也幾乎一樣（「一顆 AI 晶片是怎麼被封在一起的」vs「被包起來時裡面多了哪幾層」）。
     分工只存在於設計文件裡，不存在於使用者的螢幕上。

     退場 ≠ 刪內容。三塊東西全部搬到 `ai_adv_packaging`，一塊都沒有丟：
       · 右側「每一層對應到哪個供應鏈環節」→ 每一列右端的環節標籤
       · 底下「設計 → 晶圓製造 → CoWoS 堆疊 → 上蓋測試 → 上板」→ 那張圖的整鏈流程列
       · 3D 場景 `SCENES.semiconductor` → `ai_adv_packaging` 的 `scene`
         （Andy 這一輪要的是把 3D 畫得更細緻，不是拿掉）
     順帶解決兩筆技術債：那張是唯一還沒收到 980 的 `native: 1220`，而且有 95 個寫死的色值。

     半導體鏈的入口因此變成**圖別選單**（跟 AI 伺服器鏈同一個模式）。
     ⚠ 跨鏈面板（E6「ABF 這種跨類別環節要同時出現兩張架構圖」）仍然要兩張縮圖，
       所以 `chains()` 改成「有**代表圖**的鏈」—— 半導體的代表圖就是 `ai_adv_packaging`
       （它在 register 裡宣告 `rep: true`）。 */
  /* ================================================================ AI 伺服器：機櫃 ＋ 運算托盤爆炸圖
     ---- 2026-09-23 v2（Andy：「AI 伺服器機櫃與 GPU 運算托盤 2D 請 Follow 其他族群風格更新」）----
     這張圖是 2026-09-21 之前畫的，跟 `site/dg/*.js` 那 19 張新族群圖對不起來。這一輪四件事：

       1. **寫死色碼歸零**：原本 35 個 `#xxxxxx` / `rgba(...)` 全部換成 `--dg-*` token 與 `D.fx.*`
          （對照表見下面 AG_COLORS）。深色「科技」與淺色「閱讀」兩種模式都成立 ——
          以前淺色主題上這張圖是一塊深藍底的孤島，token 換了它也不會變。
       2. **字級**：畫布上的字一律走 STYLE 的 `.hd` / `.lbl` / `.sub` / `.cap`（＝ `--dg-fs-*`，12px 下限），
          說明文字全部搬進 HTML 卡片（`extRow` 傳 `side`），行距由卡片自己的 line-height 決定；
          畫布寬度從 1220 收到 700（native 跟著改）—— 1220 在 900px 欄寬上被壓成 ×0.57，
          字級怎麼調都沒用（DECISIONS #226）。
       3. **版面左右不浪費空白**：卡片離開 SVG 之後由 `externalize()` 排到畫布左右兩欄
          （三欄／畫布＋右欄／單欄由 index.html 的 .dgv2 容器查詢決定），畫布本身只剩主角：
          左欄整機櫃（20..188）、右欄運算托盤爆炸圖（226..660），中間留 38px 的呼吸帶，
          右下角原本的空白補上「×N 機櫃 → 資料中心」那一段，底下流程列拉滿整個畫布寬。
       4. **互動一個都沒掉**：11 個繪圖群組的 `data-seg` / `data-part` 與改造前**逐字相同**
          （ag_rack／ag_tor／ag_psu／ag_cdu／ag_coldplate／ag_gpu／ag_pcb／ag_vrm／ag_optic／ag_ccl／ag_csp），
          所以 `three3d.js` 的 SCENES.ai_server 靠 data-part 做的 2D↔3D 同步（含 ag_cdu 的
          `alias: ['ag_coldplate']`）原封不動；說明卡片跟改造前的 `labelRow` 一樣**只掛 data-seg、不掛 data-part**
          —— 掛了的話卡片與零件會同時變成主角，「主角剛好一個」那條驗收就會紅。

     ---- 色碼對照（AG_COLORS）：左邊是改造前寫死的值，右邊是現在吃的 token ----
       #0f172b 機櫃／盒體內部     → var(--dg-void)      切面上的空隙／腔體背景（淺色是 #e8e5dd）
       #141e36 托盤／光模組盒體   → var(--dg-frame)     框與盒的底
       #182a3f ToR 盒體           → var(--dg-frame)
       #1a1530 電源櫃／VRM 盒體   → var(--dg-frame)     ＋ 電力橘的線條做區別（不再用紫底）
       #0e2a33 CDU 盒體           → var(--dg-frame)
       #2b1f3f PSU 單體           → var(--dg-alu)（鋁殼，fx.glass 的 fill）
       #1e2a48 / #2a3860 細框線   → .thin / .hair（var(--dg-ink-3) 加透明度）
       #163a2a GPU 模組載板       → var(--dg-abf)       ABF 增層膜（模組載板就是 ABF 載板）
       #1a2542 模組中介層         → var(--dg-si-2)      矽中介層
       #3a2a5c + #8b7bff HBM      → var(--dg-si)        矽；改用「堆疊分層線」當識別特徵
       #1f2f5c + #3ee0ff 邏輯晶粒 → var(--dg-die)       矽裸晶
       rgba(62,224,255,.28/.35)   → var(--dg-sig)       訊號藍（語意色，兩種模式都有對比表）
       #3ee0ff 冷卻水進／指示燈   → var(--dg-cold)（水）／var(--dg-sig)（訊號）
       #ff4d6d 冷卻水回           → var(--dg-hot)       出水（熱）★ 語意色
       #ffb454 供電              → var(--dg-pwr)       電力橘 ★ 語意色
       #2ee59d 狀態燈            → var(--dg-cool)      刻意不用 #2ee59d：那是台股「跌」的綠
       rgba(255,180,84,.5) 走線   → .trace（var(--dg-cu-lit)，銅走線就該是銅色）
       rgba(120,200,150,.16) 織紋 → .weave（var(--dg-weave)，玻纖織紋）
       #e8eeff 文字              → STYLE 的 .lbl／.sub（var(--dg-ink)／var(--dg-ink-3)）
       #0a1d12 / #0b2418 底面     → 取消（改用 fx.glass 的等角側面，厚度由材質自己表現）
       rgba(20,30,54,.55) 襯底    → 取消（GPU 那一層本來就是一塊等角玻璃板）
       agCool／agPcb／agCcl 三條漸層維持吃 `--dg-ag-*`（它們本來就是 token，淺色模式另有一組值）。*/
  const AG_VARS = `<style>
    .dgag .thin{stroke:var(--dg-ink-3);stroke-opacity:.55;fill:none;stroke-width:1}
    .dgag .hair{stroke:var(--dg-ink-3);stroke-opacity:.34;fill:none;stroke-width:.8}
    .dgag .box{fill:var(--dg-frame)}
    .dgag .cavity{fill:var(--dg-void)}
    .dgag .gold{fill:var(--dg-sw-gold)}
    .dgag .die{fill:var(--dg-die)}
    .dgag .si{fill:var(--dg-si)}
    .dgag .sicut{fill:var(--dg-si-2)}
    .dgag .abf{fill:var(--dg-abf)}
    .dgag .weave{stroke:var(--dg-weave);stroke-opacity:.5;fill:none;stroke-width:.8}
    .dgag .trace{stroke:var(--dg-cu-lit);stroke-opacity:.8;fill:none;stroke-width:1.3}
    .dgag .pwr{stroke:var(--dg-pwr);fill:none;stroke-width:2;stroke-linecap:round}
    .dgag .fine{fill:var(--dg-ink-3)}
    /* 發光只給主角（DECISIONS #238「暗色可發光但只給流動線與被選零件」）：
       同環節其餘 .sel 不發光、描邊細一階。兩條都要排在共用 STYLE 之後、特異性也要高過它。*/
    svg.dg.dgag [data-seg].sel .part{filter:none;stroke-width:1.6}
    svg.dg.dgag [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
  </style>`;

  /* GPU 模組（CoWoS 封裝）：ABF 模組載板 → 矽中介層 → 中央邏輯晶粒 ＋ 兩側各 2 顆 HBM 堆疊。
     ★ HBM 的識別特徵是「一疊 DRAM」，所以每一顆都畫三條分層線 ——
       Andy 2026-09-16：「特徵比多邊形數重要」。只有最外面那塊載板掛 .part
       （`.part` 的描邊吃環節色，全部都掛的話點一下會整顆模組描邊變粗、糊成一團）。*/
  function gpuModule(x, y, i) {
    const W = 98, H = 26;
    const hbm = (hx, hy) => `<rect class="si" x="${hx}" y="${hy}" width="12" height="8" rx="1"/>`
      + `<path class="hair" d="M${hx},${hy + 2}h12M${hx},${hy + 4}h12M${hx},${hy + 6}h12"/>`;
    return `<g transform="translate(${x},${y})">
      <rect class="abf part" x="0" y="0" width="${W}" height="${H}" rx="2"/>
      <rect class="sicut" x="6" y="3" width="${W - 12}" height="${H - 6}" rx="1.5"/>
      ${hbm(9, 5)}${hbm(9, 14)}${hbm(77, 5)}${hbm(77, 14)}
      <rect class="die" x="27" y="5" width="44" height="16" rx="1.5"/>
      <rect class="pulse" x="30" y="8" width="38" height="10" rx="1" fill="var(--dg-sig)" opacity=".22" style="animation-delay:${(i * 0.3).toFixed(1)}s"/>
      <path class="hair" d="M27,5h44v16h-44Z"/></g>`;
  }

  function aiServer() {
    const CW = 700;                       // 畫布寬＝主角寬（SLOTS 的 native 跟著改）
    const ISO = { dx: 16, dy: -9 };       // 等角玻璃板往右後上擠出去的位移（爆炸拆解共用）
    /* 說明卡片（v2）：卡片離開 SVG 變成 HTML（diagrams.js 的 externalize），畫布上只留編號圓點。
       ⚠ 這裡**刻意只傳 seg、不傳 part**：卡片與繪圖群組若共用同一個 data-part，
         點一下會有兩個節點同時 .sel-part，「主角剛好一個」那條驗收就紅。
         改造前的 labelRow 也是只掛 data-seg，所以這是「照舊」不是「放寬」。*/
    const card = (o) => {
      const s = extRow({ seg: o.seg, title: o.title, sub: o.sub, no: o.no, side: o.side,
        ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
      return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
    };
    const C = { cool: 'var(--dg-cold)', hot: 'var(--dg-hot)', pwr: 'var(--dg-pwr)', sig: 'var(--dg-sig)',
      cu: 'var(--dg-cu-lit)', si: 'var(--dg-si)', abf: 'var(--dg-abf)', steel: 'var(--dg-steel)',
      gold: 'var(--dg-sw-gold)', mute: 'var(--dg-mute)' };

    // ================================================================ ① 整機櫃（左欄 20..188）
    const RX = 20, RW = 168, TRX = 34, TRW = 142;          // 機櫃外框、托盤左緣與寬
    /* 8 個運算托盤：每個托盤 8 顆 GPU ＋ 一顆狀態燈 ＋ 後端連接器。
       托盤 y ＝ 98 起、每 28 一層（高 24、呼吸 4），最後一層 98+7*28+24 ＝ 318。*/
    const trays = [];
    for (let i = 0; i < 8; i++) {
      const y = 98 + i * 28;
      const chips = [0, 1, 2, 3, 4, 5, 6, 7].map(j =>
        `<rect class="pulse" x="${46 + j * 14}" y="${y + 6}" width="11" height="12" rx="1.5" fill="var(--dg-sig)" opacity=".22" style="animation-delay:${((i + j) % 5) * 0.35}s"/>`).join('');
      trays.push(`<g><rect class="box" x="${TRX}" y="${y}" width="${TRW}" height="24" rx="3"/>`
        + `<rect class="hair" x="${TRX}" y="${y}" width="${TRW}" height="24" rx="3" fill="none"/>${chips}`
        + `<circle class="blink b${(i % 3) + 1}" cx="${TRX + 6}" cy="${y + 12}" r="2.4" fill="var(--dg-cool)"/>`
        + `<rect class="cavity" x="${TRX + TRW - 10}" y="${y + 5}" width="7" height="14" rx="1"/></g>`);
    }
    /* 電源櫃：6 顆 CRPS 電源，每顆都有風扇與底部金手指 —— 那是 PSU 的識別特徵。*/
    const psu = [0, 1, 2, 3, 4, 5].map(j => {
      const x = 38 + j * 23;
      const fingers = [0, 1, 2].map(k => `<rect class="gold" x="${x + 4 + k * 5}" y="${376}" width="3" height="6" rx="1"/>`).join('');
      const blades = [0, 1, 2, 3, 4].map(k =>
        `<path class="thin" d="M0,0 L${(6 * Math.cos(k * 1.2566)).toFixed(1)},${(6 * Math.sin(k * 1.2566)).toFixed(1)}"/>`).join('');
      return fx.glass(x, 348, 20, 34, { fill: 'var(--dg-alu)', rx: 2 })
        + `<circle class="thin" cx="${x + 10}" cy="${364}" r="7"/>`
        + `<g transform="translate(${x + 10},364)"><g class="spin" style="animation-delay:${(j * 0.4).toFixed(1)}s">${blades}</g></g>`
        + fingers;
    }).join('');
    /* 液冷 CDU：泵（會轉）＋ 板式熱交換器（一疊波紋薄板）＋ 四個口。*/
    const plates = [0, 1, 2, 3, 4, 5, 6].map(j =>
      `<path class="hair" d="M${96 + j * 10},420 v34"/>`).join('');
    const cdu = `<rect class="box" x="${TRX}" y="412" width="${TRW}" height="50" rx="3"/>`
      + `<circle class="spin" cx="62" cy="437" r="14" fill="none" stroke="var(--dg-cool)" stroke-width="2.5" stroke-dasharray="7 6"/>`
      + `<circle cx="62" cy="437" r="4" fill="var(--dg-cool)"/>`
      + `<rect class="cavity" x="90" y="418" width="80" height="38" rx="2"/>${plates}`;
    /* 機櫃內的冷／熱水立管：冷水由 CDU 往上送到每一層托盤、熱水回 CDU（語意色 --dg-cold／--dg-hot）。
       glow:false ＝ 不吃光暈濾鏡（一張圖的 feGaussianBlur 預算是 3 個元素，#239）。*/
    const pipes = fx.beam(`M181,452 V92`, { color: 'var(--dg-cold)', w: 2.4, flow: true, glow: false })
      + fx.beam(`M187,92 V452`, { color: 'var(--dg-hot)', w: 2.4, flow: true, glow: false });

    // ================================================================ ② 運算托盤爆炸拆解（右欄 226..660）
    const SX = 226, SW = 418;                              // 等角板的左緣與寬（+dx 之後右緣 660）
    const slab = (x, y, w, h, fill, r) => fx.glass(x, y, w, h, { fill, cls: 'part', rx: r || 3, iso: ISO });
    // 液冷冷板：四條流道由冷到熱（agCool 漸層，吃 --dg-ag-cool / -2）
    const chan = [0, 1, 2, 3].map(k =>
      `<path class="hair" d="M${SX + 8},${60 + k * 7} H${SX + SW - 8}" stroke-width="5.6" stroke-opacity=".7"/>`
      + `<path class="flow" d="M${SX + 8},${60 + k * 7} H${SX + SW - 8}" stroke="url(#agCool)" stroke-width="3.2" fill="none"/>`).join('');
    // 進出水口：冷水從上面進、熱水從上面回（立管 ＋ 端點光點；進水那一條是全圖唯一吃光暈的光束）
    const ports = fx.beam(`M${SX + 70},38 V52`, { color: 'var(--dg-cold)', w: 3, flow: true, dots: [[SX + 70, 38]] })
      + fx.beam(`M${SX + SW - 70},52 V38`, { color: 'var(--dg-hot)', w: 3, flow: true, glow: false, dots: [[SX + SW - 70, 38]] })
      + `<text class="fine" x="${SX + 78}" y="42">冷水進</text>`
      + `<text class="fine" x="${SX + SW - 62}" y="42">熱水回</text>`;
    // 8 顆 GPU 模組：2 列 × 4
    const modules = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) modules.push(gpuModule(SX + 4 + c * 104, 132 + r * 30, r * 4 + c));
    // 主機板：銅走線 ＋ 三組連接器插槽（高階 PCB 的識別特徵）
    const traces = [[SX + 30, 246], [SX + 90, 252], [SX + 160, 246], [SX + 230, 258], [SX + 300, 250]]
      .map(([x, y], i) => `<path class="trace flow ${i % 2 ? 'rev' : ''} slow" d="M${x},${y} h${44 + (i % 3) * 18}"/>`).join('');
    const slots = [0, 1, 2].map(j => `<rect class="gold" x="${SX + 60 + j * 110}" y="242" width="64" height="4" rx="1"/>`).join('');
    // CCL 銅箔基板：玻纖織紋（經緯兩個方向）
    const weave = [];
    for (let x = SX + 10; x <= SX + SW - 10; x += 20) weave.push(`<path class="weave" d="M${x},302 v18"/>`);
    for (let y = 306; y <= 318; y += 6) weave.push(`<path class="weave" d="M${SX + 6},${y} h${SW - 12}"/>`);
    // 層與層之間往上的小熱箭頭：看得出「熱由下往上走、拆開之後怎麼疊回去」
    const gaps = [[200, 226], [272, 296]].map(([a, b]) =>
      `<path class="hair" d="M${SX + SW / 2},${b} V${a} m-4,6 l4,-6 l4,6"/>`).join('');

    // ================================================================ ③ 誰在買：資料中心（右下，原本是空白）
    const racks = [0, 1, 2, 3].map(j => {
      const x = SX + 10 + j * 36;
      return `<rect class="hair" x="${x}" y="414" width="24" height="52" rx="2" fill="none"/>`
        + [0, 1, 2, 3, 4].map(k => `<rect class="cavity" x="${x + 4}" y="${420 + k * 10}" width="16" height="6" rx="1"/>`).join('');
    }).join('');

    return `<svg class="dg dgm dgag rs" viewBox="0 0 ${CW} 620" width="100%" style="display:block">${STYLE}${AG_VARS}
      <defs>${fx.glowDefs({ r: 3.5, soft: 3 })}
        <linearGradient id="agCool" gradientUnits="userSpaceOnUse" x1="${SX}" y1="0" x2="${SX + SW}" y2="0"><stop offset="0" stop-color="var(--dg-ag-cool)"/><stop offset="1" stop-color="var(--dg-ag-cool-2)"/></linearGradient>
        <linearGradient id="agPcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-ag-pcb)"/><stop offset="1" stop-color="var(--dg-ag-pcb-2)"/></linearGradient>
        <linearGradient id="agCcl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-ag-ccl)"/><stop offset="1" stop-color="var(--dg-ag-ccl-2)"/></linearGradient>
      </defs>

      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">AI 伺服器機櫃與 GPU 運算托盤</text>
      <text class="cap ext" x="0" y="0">左邊是一整座機櫃（頂端交換器、8 個運算托盤、電源櫃、液冷 CDU）；右邊把其中一個運算托盤由上往下拆開 —— 由外到內，熱由下往上走。</text>
      <text class="cap ext" x="0" y="0">每一張說明卡片對應畫布上同號的圓點；點卡片或點零件，同一個環節的零件會一起亮，下方流程列也跟著標起來。</text>

      <text class="hd" x="${RX}" y="24">① 整機櫃</text>
      <text class="hd" x="${SX}" y="24">② 一個運算托盤拆開：由外到內，熱由下往上</text>

      <!-- ===================== ① 整機櫃 ===================== -->
      <g data-seg="assembly" data-part="ag_rack">
        ${fx.glass(RX, 40, RW, 430, { fill: 'var(--dg-frame)', cls: 'part', rx: 8 })}
        ${trays.join('')}${pipes}
        <text class="sub" x="${RX + 6}" y="336">GPU 運算托盤 ×8</text>
        <text class="lbl" x="${RX}" y="486">整機櫃 Rack（系統組裝）</text>
      </g>
      <g data-seg="switch" data-part="ag_tor">
        <rect class="box part" x="${TRX}" y="52" width="${TRW}" height="28" rx="3"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(j => `<rect class="blink b${(j % 3) + 1}" x="${TRX + 8 + j * 10}" y="60" width="7" height="9" rx="1" fill="var(--dg-pwr)"/>`).join('')}
        <circle class="blink b2" cx="${TRX + TRW - 10}" cy="66" r="3" fill="var(--dg-sig)"/>
      </g>
      <g data-seg="power" data-part="ag_psu">
        <rect class="box part" x="${TRX}" y="344" width="${TRW}" height="42" rx="3"/>${psu}
        <text class="sub" x="${RX + 6}" y="402">電源櫃 PSU ×6（交流進、直流匯流排出）</text>
      </g>
      <g data-seg="thermal" data-part="ag_cdu">${cdu}
        <rect class="hair" x="${TRX}" y="412" width="${TRW}" height="50" rx="3" fill="none"/>
        <rect class="part" x="${TRX}" y="412" width="${TRW}" height="50" rx="3" fill="none"/></g>

      <!-- ===================== ② 運算托盤爆炸拆解 ===================== -->
      ${shadow(`${ports}
        <g data-seg="thermal" data-part="ag_coldplate">${slab(SX, 52, SW, 34, 'var(--dg-cu-lit)')}${chan}</g>
        ${gaps}
        <g data-seg="adv_pkg" data-part="ag_gpu">${slab(SX, 126, SW, 66, 'var(--dg-alu)')}${modules.join('')}</g>
        <g data-seg="power" data-part="ag_vrm">${slab(SX + 6, 200, 70, 20, 'var(--dg-frame)', 2)}
          <path class="pwr" d="M${SX + 12},206 h58 M${SX + 12},212 h58 M${SX + 12},218 h58"/></g>
        <g data-seg="optical" data-part="ag_optic">${slab(SX + SW - 76, 200, 70, 20, 'var(--dg-frame)', 2)}
          ${[0, 1, 2, 3].map(j => `<rect class="cavity" x="${SX + SW - 70 + j * 15}" y="204" width="11" height="12" rx="1.5"/><circle class="blink b${(j % 3) + 1}" cx="${SX + SW - 64.5 + j * 15}" cy="207" r="1.8" fill="var(--dg-sw-fiber)"/>`).join('')}</g>
        <g data-seg="abf_pcb" data-part="ag_pcb">${slab(SX, 236, SW, 26, 'url(#agPcb)')}${traces}${slots}</g>
        <g data-seg="ccl" data-part="ag_ccl">${slab(SX, 296, SW, 22, 'url(#agCcl)')}${weave.join('')}</g>`)}

      <!-- ===================== ③ 誰在買：一整座資料中心 ===================== -->
      <text class="hd" x="${SX}" y="358">③ 誰在買：機櫃 ×N ＝ 一座資料中心</text>
      <g data-seg="hyperscaler" data-part="ag_csp">
        <path class="part" d="M${SX + 268},408 a34,34 0 0 1 66,-16 a31,31 0 0 1 58,19 a26,26 0 0 1 -11,51 h-108 a27,27 0 0 1 -5,-54 z" fill="var(--dg-void)"/>
        ${[0, 1, 2].map(j => `<circle class="drop d${j + 1}" cx="${SX + 292 + j * 42}" cy="464" r="2.5" fill="var(--dg-sig)"/>`).join('')}
      </g>
      <g pointer-events="none">${racks}
        <path class="flow slow" d="M${SX + 156},436 H${SX + 262}" stroke="var(--dg-accent-2d)" stroke-width="1.6" fill="none"/>
        <text class="fine" x="${SX}" y="484">×N 機櫃 · 電力與冷卻先到位，才輪到晶片</text><text class="fine" x="${SX + 278}" y="492">整櫃整櫃地買</text>
      </g>

      <!-- 左欄卡片：機櫃這一側（錨點在左邊零件上） -->
      ${card({ seg: 'switch', no: 1, side: 'l', ax: TRX + 4, ay: 66, color: C.sig, title: 'ToR 交換器（機櫃頂端）', sub: '往上接叢集網路（scale-out）：InfiniBand 或 Ethernet' })}
      ${card({ seg: 'assembly', no: 2, side: 'l', ax: RX + 4, ay: 250, color: C.steel, title: '整機櫃 Rack（系統組裝）', sub: '19 吋機櫃、滑軌、鈑金；整櫃出貨前做燒機與水路壓測' })}
      ${card({ seg: 'power', no: 3, side: 'l', ax: TRX + 4, ay: 365, color: C.pwr, title: '電源櫃 PSU ／ BBU', sub: '交流進、機櫃內直流匯流排出；800V HVDC 是下一世代（示意）' })}
      ${card({ seg: 'thermal', no: 4, side: 'l', ax: TRX + 4, ay: 437, color: C.cool, title: '液冷 CDU（冷卻液分配）', sub: '泵 ＋ 板式熱交換器；冷水送進每一層托盤、熱水回機房' })}
      ${card({ seg: 'power', no: 5, side: 'l', ax: SX + 8, ay: 210, color: C.pwr, title: '板上供電模組 VRM', sub: '12V／48V 再降到晶片要的電壓，就在 GPU 旁邊' })}

      <!-- 右欄卡片：拆解那一疊（錨點在等角板的右端） -->
      ${card({ seg: 'thermal', no: 6, side: 'r', ax: SX + SW - 6, ay: 70, color: C.cool, title: '液冷冷板 ＋ 快接頭', sub: '直接貼在 GPU 上；冷板、分歧管、UQD 快接頭都在這一環' })}
      ${card({ seg: 'adv_pkg', no: 7, side: 'r', ax: SX + SW - 6, ay: 160, color: C.abf, title: 'GPU 模組 ×8（CoWoS 封裝）', sub: '邏輯晶粒 ＋ HBM 一起放在矽中介層上，再打到模組載板' })}
      ${card({ seg: 'hbm', no: 8, side: 'r', ax: SX + 19, ay: 140, color: C.si, title: 'HBM 記憶體（堆疊的那幾疊）', sub: '每顆 GPU 旁 4–8 顆；一顆就是十幾層 DRAM 用 TSV 打通' })}
      ${card({ seg: 'foundry', no: 9, side: 'r', ax: SX + 57, ay: 140, color: C.si, title: 'GPU 邏輯晶粒・晶圓代工', sub: '3nm／2nm 的那一塊（看半導體鏈那幾張）' })}
      ${card({ seg: 'optical', no: 10, side: 'r', ax: SX + SW - 6, ay: 210, color: 'var(--dg-sw-fiber)', title: '光通訊 ／ 矽光子', sub: '800G–1.6T 前面板可插拔光模組；CPO 把光引擎搬到交換 ASIC 旁' })}
      ${card({ seg: 'abf_pcb', no: 11, side: 'r', ax: SX + SW - 6, ay: 248, color: C.gold, title: '主機板 高階 PCB ／ ABF 載板', sub: '高層數主機板、連接器插槽、模組載板' })}
      ${card({ seg: 'ccl', no: 12, side: 'r', ax: SX + SW - 6, ay: 306, color: 'var(--dg-weave)', title: 'CCL 銅箔基板', sub: '低損耗板材，PCB 的原料；織紋那一層就是玻纖布' })}
      ${card({ seg: 'hyperscaler', no: 13, side: 'r', ax: SX + 272, ay: 424, color: C.sig, title: '雲端業者（終端需求）', sub: '超大規模雲端業者、主權 AI、Neocloud —— 整櫃整櫃地買' })}
      ${card({ seg: 'assembly', warn: true, note: true, order: 99, side: 'l', title: '點零件篩到的是「供應鏈環節」，不是整個族群', sub: '同一個環節可能同時收了好幾個族群的公司；族群與環節的落差在關聯圖上看得比較清楚。' })}

      <!-- ===================== ④ 從晶片到交付 ===================== -->
      <text class="hd" x="${RX}" y="512">④ 從晶片到交付</text>
      ${processBar(RX, 524, [{ seg: 'foundry', t: 'GPU 晶粒', s: '晶圓代工' }, { seg: 'adv_pkg', t: 'CoWoS 封裝', s: '＋ HBM' }, { seg: 'abf_pcb', t: '模組上板', s: 'PCB ／ 載板' }, { seg: 'assembly', t: '托盤 → 機櫃', s: '系統組裝' }, { seg: 'hyperscaler', t: '交付 CSP', s: '資料中心' }], 118)}
      ${chainLink('semiconductor', RX, 572, '← 看半導體鏈：晶片怎麼來')}
      <text class="cap" x="244" y="584">示意圖，非實物比例｜托盤內的零件數量、層數與厚度比例均為示意；</text>
      <text class="cap" x="244" y="602">機櫃配置（托盤數、供電與冷卻做法）依機種而異。</text>
    </svg>`;
  }

  /* ================================================================ 被動元件：MLCC 疊層剖析
     規格書：docs/diagram_specs/mlcc_stack.md（mechanical-engineer 2026-09-19 簽「可開畫」）。
     這張圖只回答兩件事：**為什麼疊越多層越貴、車規為什麼難做。**

     ---- 事實來源（2026-09-21 用 WebSearch 重新查證過一次，不是照抄規格書）----
     ★ 證據強度先講清楚：這個容器**只有 WebSearch 能用，WebFetch 一律回 EGRESS_BLOCKED**
       （murata.com / ele.kyocera.com / escatec.com / ctee.com.tw 逐一試過都是）。
       所以底下每一條的證據都是「**WebSearch 摘要**」，不是原文 —— 沒有人讀過整篇。
       原文讀不到的地方一律不寫成精確數字；網址留著是給下一個人去讀，不是宣稱我讀過。
       · 介電層 0.5–2 µm、內電極（Ni，BME 賤金屬）約 0.5–0.6 µm、層數 400–1000 層
         → USPTO 專利族 11302478 / 11037727 說明；Murata 官方部落格「next-generation MLCC」
       · 端子由內到外 Cu →〔導電樹脂〕→ Ni → Sn；**樹脂層夾在 Cu 與 Ni 之間**（不是最外層）
         → TDK soft-termination 技術文章 tdk-electronics.tdk.com/.../2237758
           KYOCERA/AVX 樹脂端子 ele.kyocera.com/en/technical/kavx_resinele/
       · 製程順序：流延 → 網印 → 疊層 → 加壓 → 切割 → 排膠 → **燒結** → 研磨 → **端電極** → 電鍍 → 測試編帶
         （燒結一定在端電極之前）→ dron-tech.com/news/the-most-comprehensive-process-flow-of-mlcc/
       · 尺寸代號兩套：EIA 0402 ＝ 公制 1005 ＝ 1.0×0.5 mm；EIA 0201 ＝ 公制 0603；EIA 01005 ＝ 公制 0402
         → blog.knowlescapacitors.com/blog/eia-mlcc-case-sizes-past-and-future
           core-emt.com/imperial-code-vs-metric-code-smd-components-sizes
       · AEC-Q200 涵蓋電性／耐濕／壽命／機械衝擊振動／**基板彎曲** → aecouncil.com AEC_Q004
       · 溫度：端電極燒附 **830–900 °C**（USPTO 專利摘要）vs 規格書引的 Murata「約 800 °C」——
         兩個摘要對不起來，所以畫面寫**區間 800–900 °C**，不挑一個當定論；
         燒結溫度一個摘要說 1050–1200 °C、另一個（Ni 內電極配方）說 1120–1200 °C，
         下限差 70 °C → **畫面乾脆不寫溫度**，只寫「還原氣氛高溫燒結」（見規格書 §6-B5）
       · 2026 村田對部分消費級（GRM／GRJ）與車規（GCM／GCJ／GCG）料號發 EOL，
         最後下單 2028-03-31、最後出貨 2029-03-31 → 工商時報 2026-09-10、鉅亨網、MoneyDJ
     ★ 查不到公開數字的一律不畫：**車規與消費級的良率差距一個百分比都不出現**（規格書 §6-C）。

     ---- 立體語言 ----
     2.5D 等角「切近角」cut-away：把 x≥XC 且 y≥YC 那一塊挖掉，露出兩個切面 ——
       y=YC 的 x–z 切面：**交錯指狀電極**（MLCC 唯一的決定性特徵）
       x=XC 的 y–z 切面：**側邊餘白**（電極不到側面，這是第三個方向上的事，純 2D 剖面看不到）
     端電極的四層（Cu／樹脂／Ni／Sn）另外用右下的 2D 放大剖面講，等角圖上只給金屬帶與分層提示。 */
  function mlccStack() {
    const SEG = 'passive_comp';
    // 模型尺寸。真實 EIA 0402 是 1.0 × 0.5 × 約 0.5 mm；高度在畫面上放大過（畫面已標「非實物比例」）
    const L = 252, W = 126, H = 150;
    const XC = 56, YC = 58;          // 切掉的近角
    const COV = 16;                  // 上下保護層（無電極素坯）
    const TW = 42;                   // 端電極帶寬（構圖比例，畫面不標數字：規格書 §6-B4 信心低）
    const EM = 30;                   // 端部餘白：電極不准碰到對面的端電極（碰到＝短路）
    const SM = 11;                   // 側邊餘白：電極不到側面
    const NEL = 16;                  // 畫 16 層（實際 400～1000 層，畫面另外標）
    const PIT = (H - COV * 2) / NEL, ET = 2.2;
    const ez = (i) => COV + i * PIT + (PIT - ET) / 2;   // 第 i 層電極的下緣 z
    /* ★ 2026-09-21 深夜（art-director；Andy：「排版有點奇怪…可以收納就收納」）
       主角的位置與大小整個重算，理由是**版面改了**，不是「想放大一點」：
         · 左欄三個區塊全部離開主畫面 —— 容值公式移到右側說明欄的最上面
           （它是這張圖的命題，本來就該跟六條逐層說明在同一欄），
           板彎裂與尺寸代號收進下面的章節。
         · 於是主角從「被左欄右緣 286 與右欄左緣 674 夾住的 352px 帶子」
           變成「整個左半邊都是它的」：x 56 到 640。
       S 的上限一樣是算出來的：橫向 584/327.3 ＝ 1.78、
       垂直 452/305 ＝ 1.48 —— **垂直才是真正的限制**，所以取 1.48。
       再大就得往下長，而往下長會把右欄六條說明列一起推下去，讀起來反而更散。
       幾何一行都沒動：S 是純等比縮放，mechanical-engineer 簽過的層序、餘白、
       切法、端子順序完全不受影響。*/
    /* ★ 2026-09-22 v2：標題與說明搬到 HTML 的 .dghead、六條說明與公式／警語搬到左右欄的 HTML 卡片，
       SVG 只剩主角 —— 畫布從 980 縮到 660 寬，主角往上移 72px（標題原本佔的位置），幾何一行沒動。*/
    const CX = 217.5, CY = 250;                          // 等角本體在畫面上的原點
    const S = 1.48;
    const ax = (x, y) => (CX + S * (x - y) * IX).toFixed(1);
    const ay = (x, y, z) => (CY + S * ((x + y) * IY - z)).toFixed(1);
    /* 主角最低點（「側邊餘白」那條引線要繞到它下面）。
       以前寫成 (L+W)*IY ＝ 189，那是**近角還沒切掉**時的最低點；
       切掉之後真正最低的是 (L, YC) ＝ 155 —— 中間 34px 全是空的，
       等於在主角下面白白墊高 50px。*/
    const BOT = CY + S * (L + YC) * IY;
    /* 省略記號「⋮ ×N」的位置：切面 B 的局部座標 (u≈85, v≈75) 換算回畫面。
       以前寫死成 (484, 250)，主角一放大就跟條紋區脫鉤 —— 現在跟著 S 走。*/
    const NX = +(CX + S * (px(XC, YC) + IX * 85)).toFixed(1);
    const NY = +(CY + S * (py(XC, YC, 0) + IY * 85 - 75)).toFixed(1);
    const poly = (cls, fill, pts) => `<path class="${cls}" fill="${fill}" d="M${pts.join('L')}Z"/>`;
    // (u,v) 平面上的矩形；onXZ / onYZ 的局部座標裡 y 就是 v（矩陣已經把方向翻好）
    const RV = (u0, v0, u1, v1) => `M${u0},${v0}H${u1}V${v1}H${u0}Z`;

    // ---------------- 切面 B（y = YC 的 x–z 面）：交錯指狀電極
    const uB = L - XC;                       // 196
    const uCap = (L - 18) - XC;              // 178：端電極內側面（陶瓷在這裡讓出位置）
    const uStop = (L - EM) - XC;             // 166：不連到右端的那一組，停在這裡
    const uTerm = (L - TW) - XC;             // 154：端電極帶的起點
    /* B2：電荷疊色只畫 CHG_AT 這幾段，不是 15 段全鋪。
       鋪滿的話那一片青色就等於「有效層區是另一種材質」；只在幾段之間畫，
       讀起來才是「電荷存在相鄰這兩片電極之間」—— 也正是這張圖要講的事。*/
    const CHG_AT = [3, 6, 9, 12];
    const els = [], chg = [];
    for (let i = 0; i < NEL; i++) {
      const v0 = ez(i), u1 = (i % 2) ? uCap : uStop;   // 奇數層連右端電極、偶數層從左端伸進來
      els.push(`<rect x="0" y="${v0.toFixed(1)}" width="${u1}" height="${ET}" fill="var(--dg-el)"/>`);
      if (i < NEL - 1 && CHG_AT.includes(i)) {
        const g0 = v0 + ET, g1 = ez(i + 1);
        chg.push(`<rect class="chg pulse" x="6" y="${g0.toFixed(1)}" width="${uStop - 12}" height="${(g1 - g0).toFixed(1)}" style="animation-delay:${(i * 0.16).toFixed(2)}s"/>`);
      }
    }
    // 端電極斷面：由外到內 Sn → Ni → Cu（車規在右下的放大圖裡才多一層樹脂）
    const termBand = (d, fill) => `<path fill="${fill}" fill-rule="evenodd" d="${RV(uTerm, d, uB - d, H - d)} ${RV(uTerm, COV, uCap, H - COV)}"/>`;
    const faceB = onXZ(XC, YC)
      + `<rect x="0" y="0" width="${uB}" height="${H}" fill="url(#mcCut)"/>`
      + `<rect x="0" y="0" width="${uB}" height="${COV}" fill="url(#mcCov)"/>`
      + `<rect x="0" y="${H - COV}" width="${uB}" height="${COV}" fill="url(#mcCov)"/>`
      + `<path d="M0,${COV}H${uB}M0,${H - COV}H${uB}" stroke="var(--dg-edge)" stroke-opacity=".55" stroke-width=".9" fill="none"/>`
      + chg.join('') + els.join('')
      + termBand(0, 'var(--dg-sn)') + termBand(3, 'var(--dg-ni)') + termBand(6.5, 'var(--dg-cu)')
      + `</g>`;

    // ---------------- 切面 A（x = XC 的 y–z 面）：側邊餘白
    const uA = W - YC, uSide = (W - SM) - YC;
    const elsA = [];
    for (let i = 0; i < NEL; i++) elsA.push(`<rect x="0" y="${ez(i).toFixed(1)}" width="${uSide}" height="${ET}" fill="var(--dg-el)"/>`);
    const faceA = onYZ(XC, YC)
      + `<rect x="0" y="0" width="${uA}" height="${H}" fill="url(#mcCutB)"/>`
      + `<rect x="0" y="0" width="${uA}" height="${COV}" fill="url(#mcCovB)"/>`
      + `<rect x="0" y="${H - COV}" width="${uA}" height="${COV}" fill="url(#mcCovB)"/>`
      + elsA.join('')
      + `<path d="M${uSide},${COV + 2}V${H - COV - 2}" stroke="var(--dg-warn)" stroke-width="var(--dg-hair-w,2)" stroke-dasharray="5 4" fill="none"/>`
      + `</g>`;

    // ---------------- 外表面
    const topFace = poly('part', 'url(#mcT)', [P3(0, 0, H), P3(L, 0, H), P3(L, YC, H), P3(XC, YC, H), P3(XC, W, H), P3(0, W, H)]);
    const topTermL = poly('', 'url(#mcMetT)', [P3(0, 0, H), P3(TW, 0, H), P3(TW, W, H), P3(0, W, H)]);
    const topTermR = poly('', 'url(#mcMetT)', [P3(L - TW, 0, H), P3(L, 0, H), P3(L, YC, H), P3(L - TW, YC, H)]);
    const rightFace = poly('part', 'url(#mcMetR)', [P3(L, 0, H), P3(L, YC, H), P3(L, YC, 0), P3(L, 0, 0)]);
    const leftCer = poly('part', 'url(#mcL)', [P3(XC, W, H), P3(TW, W, H), P3(TW, W, 0), P3(XC, W, 0)]);
    const leftTerm = poly('part', 'url(#mcMetL)', [P3(TW, W, H), P3(0, W, H), P3(0, W, 0), P3(TW, W, 0)]);
    // 端電極分層提示：兩條細線，遠看就知道那條金屬帶不是一塊實心
    const hint = `<path d="M${P3(L - 3, 0, H)}L${P3(L - 3, YC, H)}M${P3(L - 7, 0, H)}L${P3(L - 7, YC, H)}" stroke="var(--dg-sn)" stroke-opacity=".38" stroke-width=".9" fill="none"/>`;

    const iso = `<g data-seg="${SEG}" data-part="mlcc_body" data-hero="mlcc_body" transform="translate(${CX},${CY}) scale(${S})">
      ${topFace}${topTermL}${topTermR}${leftCer}${leftTerm}${rightFace}${hint}${faceA}${faceB}</g>`;

    /* ---------------- 左欄：尺寸比較尺（降權後 1 mm ＝ 79px）
       P2（art-director 2026-09-21）：這一塊是**附註**，卻是整張圖最先被看到的東西 ——
       它站在閱讀起點（左上角），而且用了跟主角一模一樣的陶瓷漸層 url(#mcT) 與錫色端子
       var(--dg-sn)。兩個條件湊在一起，讀者的第一眼會停在附註上。
       降權的做法是**拿掉材質、不是拿掉資訊**：
         · 顏色改成單一 --dg-mute 的兩階透明度（輪廓＝本體＋兩個端子，一個都沒少）
         · 尺寸縮到 0.72（比例尺同步縮，1 mm 仍然量得準）
         · 位置從左欄最上面移到左欄最下面（見下方的閱讀順序）
       三套代號、雙標尺寸、比例尺一個字都沒刪。*/
    const chip = (x, w, h, by) => {
      const t = Math.max(4, w * 0.17);
      return `<g><rect x="${x}" y="${by - h}" width="${w}" height="${h}" rx="2" fill="var(--dg-mute)" opacity=".45"/>`
        + `<rect x="${x}" y="${by - h}" width="${t}" height="${h}" rx="1.5" fill="var(--dg-mute)" opacity=".85"/>`
        + `<rect x="${x + w - t}" y="${by - h}" width="${t}" height="${h}" rx="1.5" fill="var(--dg-mute)" opacity=".85"/></g>`;
    };

    // ---------------- 右下：端電極 2D 放大剖面（消費級三層 vs 車規四層）
    function endCut(x, auto) {
      /* 端電極的 2D 放大剖面。畫法：由外到內一層一層疊上去（外層最大、內層最小），
         最後把陶瓷本體壓在上面 —— 這樣每一層自然變成一圈「C」，包住端部五個面的一段。
         ★ 厚薄關係是唯一要對的事：Cu 最厚、樹脂次之、Ni／Sn 最薄（規格書 §6-B3，不標數字）。*/
      /* 畫的是**整顆**的縱剖面（兩端都有端子），不是只有一端 ——
         只畫一端的版本測下來會被讀成「螢幕＋底座」，整顆的輪廓才一眼認得出是 MLCC。*/
      const BL = x + 34, BR = x + 258, BT = 566, BB = 654;     // 陶瓷本體
      const WL = x + 96, WR = x + 196;                          // 端子往本體上包到這裡（左／右）
      /* A3（mechanical-engineer 2026-09-21）：**兩顆的 Sn／Ni／Cu 厚度完全一樣**，
         車規靠「端子整體往外長厚」容納中間那層導電樹脂。
         以前消費級的 Ni 被畫成跟 Cu 一樣厚、而且是車規那顆 Ni 的三倍，
         等於畫面在說「兩顆的差別只有多一層樹脂」但 Ni 自己偷偷變三倍 —— 對照就失效了。
         每一列是 [端面向外的偏移 dx, 上包帶頂緣 y0, 下包帶底緣 y1, 顏色]，
         由外到內排；厚度＝相鄰兩列的差（規格書 §6-B3：只表達厚薄關係，不標數字）。
           端面厚度：Sn 4 ／ Ni 4 ／〔樹脂 6〕／ Cu 12（Cu 最厚）
           上下包帶：Sn 3 ／ Ni 3 ／〔樹脂 5〕／ Cu 8 */
      const lay = auto
        ? [[8, 547, 673, 'var(--dg-sn)'], [12, 550, 670, 'var(--dg-ni)'], [16, 553, 667, 'var(--dg-resin)'], [22, 558, 662, 'var(--dg-cu)']]
        : [[14, 552, 668, 'var(--dg-sn)'], [18, 555, 665, 'var(--dg-ni)'], [22, 558, 662, 'var(--dg-cu)']];
      const OUT = lay[0][0];        // 端子最外緣（焊錫圓角要爬到這裡）
      const shells = lay.map(([dx, y0, y1, c]) =>
        `<rect x="${x + dx}" y="${y0}" width="${WL - x - dx}" height="${y1 - y0}" rx="1.5" fill="${c}"/>`
        + `<rect x="${WR}" y="${y0}" width="${x + 292 - dx - WR}" height="${y1 - y0}" rx="1.5" fill="${c}"/>`).join('');
      // 交錯指狀電極：偶數層連左端、奇數層連右端，兩邊都留餘白（碰到對面＝短路）
      const stubs = [574, 586, 598, 610, 622, 634, 646].map((y, i) =>
        `<rect x="${i % 2 ? BL + 30 : BL}" y="${y}" width="${i % 2 ? BR - BL - 30 : BR - BL - 30}" height="3.4" fill="var(--dg-el)"/>`).join('');
      const pcb = `<rect x="${x}" y="684" width="292" height="10" rx="2" fill="var(--dg-pcb)"/>`
        + `<rect x="${x + 2}" y="678" width="100" height="6" rx="1" fill="var(--dg-cu)"/>`
        + `<rect x="${x + 190}" y="678" width="100" height="6" rx="1" fill="var(--dg-cu)"/>`
        + `<path d="M${x + OUT - 8},678 Q${x + OUT - 3},678 ${x + OUT},660 L${x + OUT},678 Z" fill="var(--dg-sn)"/>`
        + `<path d="M${x + 300 - OUT},678 Q${x + 295 - OUT},678 ${x + 292 - OUT},660 L${x + 292 - OUT},678 Z" fill="var(--dg-sn)"/>`;
      /* A2（2026-09-21 重查，信心高 —— 見檔頭的來源註記）：板彎裂是「45° 裂」。
         起點在**安裝面（底面）、端電極內緣**（termination margin 的起點），
         往**外上方 45°** 走，一直走到端電極 —— 也就是往元件外側、不是往中間。
         舊版兩條都畫成由外往內，方向正好相反。
         這裡從 (WL, BB) 走到 (BL, BB−62)：水平 −62、垂直 −62 ＝ 正好 45°，
         終點落在本體端面，也就是被端電極蓋住的那一面。*/
      const crack = auto ? ''
        : `<path d="M${WL},${BB} L${WL - 16},${BB - 16} L${WL - 24},${BB - 22} L${WL - 40},${BB - 40} L${BL},${BB - 62}" stroke="var(--dg-err)" stroke-width="2.2" fill="none"/>`;
      const relief = auto
        ? `<path d="M${x + 19},624 l0,-18 m-3.5,3.5 l3.5,-3.5 l3.5,3.5" stroke="var(--dg-accent)" stroke-width="1.6" fill="none"/>`
        : '';
      /* data-alias：2D 與 3D 的切塊方式不一樣，對不上的地方在這裡接起來。
           · 3D 只有一圈「端電極」（mlcc_term），2D 拆成消費級與車規兩張放大剖面
           · 3D 的「PCB 焊墊與焊錫」（mlcc_pad）在 2D 就是畫在這兩張剖面底下的那塊板子與焊錫圓角
         所以從 3D 點這兩顆、切回 2D 時這兩塊都算「你剛剛點的那一個」，
         不會出現「同環節全部退一階、卻沒有任何主角」的空狀態。*/
      return `<g data-seg="${SEG}" data-part="${auto ? 'mlcc_term_auto' : 'mlcc_term_cons'}" data-alias="mlcc_term,mlcc_pad">
        <text class="hd" x="${x}" y="526">${auto ? '車規：四層（多一層導電樹脂）' : '消費級：三層'}</text>
        ${shells}<rect class="part" x="${BL}" y="${BT}" width="${BR - BL}" height="${BB - BT}" fill="url(#mcT)"/>${stubs}${pcb}${crack}${relief}
        <text class="sub" x="${x}" y="712" ${auto ? '' : 'style="fill:var(--dg-warn)"'}>${auto ? '樹脂層先變形，把應力吃掉' : '陶瓷直接吃到應力 → 板彎裂'}</text></g>`;
    }

    /* ================= 版面（art-director 2026-09-21 深夜）=================
       Andy：「MLCC 圖片排版我覺得有點奇怪，幫我優化，需要更直觀且看起來更舒服，
              可以收納就收納」。

       改之前的毛病（量過的）：畫布被切成 8 塊、73 個文字節點、1421 個中文字，
       主角只佔畫布 12.88% —— 一眼掃過去八塊一樣重，那不是資訊豐富，是沒有主次。
       上一輪只能「降權」（附註不准穿主角的材質、不准站在閱讀起點），因為當時**不准收**。
       這一次有「可以收納就收納」的授權，所以改成**漸進揭露**：

         主畫面（永遠看得到）＝ 這張圖的命題本身
           標題 → ① 容值公式 → 主角（等角切開的本體）→ 六條逐層說明 → 短路警語
         其餘三段收進章節列，按了就打開：
           ② 端電極四層 ＋ 板彎裂　③ 製造流程 ＋ 為什麼越貴　④ 尺寸代號與資料來源

       ★ 收納不是刪除：每一條章節列上都寫著「裡面有什麼」（幾張圖、幾層、幾行），
         所以收合狀態下讀者知道還有什麼可以看；而且 JS 沒跑到時，
         靜態 SVG 本身就是一份「全部展開」的完整版面（縮圖走的就是這條路）。

       ★ 為什麼容值公式搬到右欄最上面：它是「層數怎麼變成容值」這句標題的展開式，
         跟底下六條逐層說明講的是同一件事（哪一層在做什麼）。
         放在左上角時它跟主角互相搶第一眼；放在同一欄的最上面，閱讀順序就只有一條線：
         公式（為什麼要疊）→ 六條（疊了什麼）→ 警語（疊錯會怎樣）。 */
    /* ================= 版面（v2，art-director 2026-09-22）=================
       Andy：「這邊的版面需要左右對齊，可以適當分配左右間隔，讓版面更滿，看起來舒適，並且會依據螢幕大小變化」。
       §1 ＝ 主角本體（660 寬畫布）；六條說明、公式、警語全是 HTML 卡片（labelRow 多傳 side）：
         左欄：① 公式、01 保護層、05 側邊餘白（錨點在主角左半邊）
         右欄：02 介電、03 內部電極、04 有效層、06 端電極、警語
       欄數與寬度由 index.html 的 .dgv2 容器查詢決定（≥1280 三欄、960～1279 畫布＋右欄、更窄單欄卡片在下面）。
       三段章節用 D.fold()（座標由 wireFolds 量），內容重排到 660 寬：一個字都沒刪，只有斷行與位置變了。*/
    const CW = 660;
    // 四層圖例（順序＝正上方那句「由內到外 Cu →〔樹脂〕→ Ni → Sn」，A4 修過的，不准倒回去）；2×2 排
    const legend = [['var(--dg-cu)', 'Cu 基底層（最內）', '最厚的一層，銅膏沾附後約 800–900 °C 燒附上去'],
      ['var(--dg-resin)', '導電樹脂（軟端子）', '只有車規／高可靠度品才有；抗板彎，ESR 變高'],
      ['var(--dg-ni)', 'Ni 鎳鍍層', '阻障層，擋焊料把底下的銅吃掉'],
      ['var(--dg-sn)', 'Sn 錫鍍層（最外）', '最外一層，讓焊錫吃得上去']]
      .map(([c, t, sb], i) => { const x = 16 + (i % 2) * 324, y = 846 + Math.floor(i / 2) * 48;
        return `<g><rect x="${x}" y="${y - 12}" width="15" height="15" rx="3" fill="${c}"/>`
          + `<text class="lbl" x="${x + 24}" y="${y}">${t}</text><text class="sub" x="${x + 24}" y="${y + 18}">${sb}</text></g>`; }).join('');

    /* class 多一個 `dg1`：**這張圖只有一個環節**（整張 [data-seg] 全是 passive_comp），
       點任何零件都會讓全部零件一起 .sel。發光留著就是「整張圖發青光、0 個被 dim」，
       `.dg.dg1{--dg-glow:none}` 把它關掉（B1）。`rs` ＝ 已改造成風格系統（閱讀模式字級升一階、卡片外掛）。
       viewBox 的高度是「全部展開」的靜態版面；收合與章節位置由 wireFolds() 在執行期算。*/
    return `<svg class="dg dgm dg1 rs" viewBox="0 0 ${CW} 1760" width="100%" style="display:block">${STYLE}
      <defs>
        <linearGradient id="mcT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer)"/><stop offset="1" stop-color="var(--dg-cer-2)"/></linearGradient>
        <linearGradient id="mcL" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer-sh)"/><stop offset="1" stop-color="var(--dg-cer-sh-2)"/></linearGradient>
        <linearGradient id="mcCut" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer-cut)"/><stop offset="1" stop-color="var(--dg-cer-cut-2)"/></linearGradient>
        <linearGradient id="mcCutB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cer-cutb)"/><stop offset="1" stop-color="var(--dg-cer-cutb-2)"/></linearGradient>
        <linearGradient id="mcCov" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cover)"/><stop offset="1" stop-color="var(--dg-cover-2)"/></linearGradient>
        <linearGradient id="mcCovB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-cover-b)"/><stop offset="1" stop-color="var(--dg-cover-b-2)"/></linearGradient>
        <linearGradient id="mcMetT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-met-t)"/><stop offset="1" stop-color="var(--dg-met-t-2)"/></linearGradient>
        <linearGradient id="mcMetR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-met-r)"/><stop offset="1" stop-color="var(--dg-met-r-2)"/></linearGradient>
        <linearGradient id="mcMetL" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-met-l)"/><stop offset="1" stop-color="var(--dg-met-l-2)"/></linearGradient>
      </defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">MLCC 積層陶瓷電容：層數怎麼變成容值，也怎麼變成成本</text>
      <text class="cap ext" x="0" y="0">中間是切開近角的本體 —— 右下切面看「交錯指狀電極」，左下切面看「側邊餘白」。兩側逐層說明；端電極、製程、尺寸代號收在下面三段裡。</text>

      <!-- ================= §1 主畫面：主角（永遠看得到） ================= -->
      ${iso}
      <!-- A6（規格書 §6-C）：省略記號要畫在條紋區**中間**，不是只寫在最底下的文字裡。 -->
      <g pointer-events="none">
        <rect x="${NX - 23}" y="${NY - 19}" width="46" height="38" rx="5" fill="url(#mcCov)" stroke="var(--dg-el)" stroke-width="1"/>
        <text class="num" x="${NX}" y="${NY}" text-anchor="middle" style="fill:var(--dg-el);font-weight:700">⋮</text>
        <text class="num" x="${NX}" y="${NY + 15}" text-anchor="middle" style="fill:var(--dg-el);font-weight:700">×N</text>
      </g>

      <!-- 左欄：① 容值公式（命題本身，所以排在最上面）、01、05 -->
      ${note({ side: 'l', order: 0, title: '① 容值是層數堆出來的', lines: ['C ＝ ε₀ · εr × n × A ÷ d', 'n＝層數、A＝重疊面積、d＝單層厚度', 'n ↑ 或 d ↓ → 容值 ↑，成本與風險也 ↑'] })}
      ${labelRow(SEG, 0, 0, '保護層（無電極素坯）', '上下各一疊，不貢獻容值', ax(120, 58), ay(120, 58, 150), 0, null, 1, 'l')}
      ${labelRow(SEG, 0, 0, '側邊餘白（不產生電容）', '電極不到側面，避免短路', ax(56, 115), ay(56, 115, 20), 0, null, 5, 'l')}
      ${note({ side: 'l', order: 7, title: '⋮ ×N ＝ 中間省略掉的層', lines: ['畫面上只畫 16 層電極，看得出交錯的規律就夠；', '實際高容量品 400～1000 層以上（示意圖，非實物比例）。'] })}
      <!-- 右欄：02、03、04、06、警語 -->
      ${labelRow(SEG, 0, 0, '介電陶瓷層（鈦酸鋇 BaTiO₃）', '單層 0.5–2 µm；越薄，容值越大', ax(170, 58), ay(170, 58, 118), 0, null, 2, 'r')}
      ${labelRow(SEG, 0, 0, '內部電極（鎳 Ni，BME）', '約 0.5 µm；兩把梳子互插但不相碰', ax(190, 58), ay(190, 58, 88), 0, null, 3, 'r')}
      ${labelRow(SEG, 0, 0, '有效層＝容值的來源', '相鄰兩層重疊的那一塊才算數', ax(150, 58), ay(150, 58, 45), 0, null, 4, 'r')}
      ${labelRow(SEG, 0, 0, '端電極（包住端部五個面）', '由內到外 Cu → Ni → Sn，兩端對稱', ax(252, 58), ay(252, 58, 40), 0, null, 6, 'r')}
      ${note({ side: 'r', warn: true, title: '★ 相鄰兩層電極必定來自相反的兩端', lines: ['而且都不碰到對面的端電極 —— 碰到就是短路。'] })}

      <!-- ================= ② 端電極四層 ＋ 板彎裂（預設收合；座標由 wireFolds 量） ================= -->
      ${fold('mc2', '② 端電極四層 ＋ 板彎裂：為什麼車規賣得比消費級貴', '消費級／車規兩張放大剖面、四層各自在幹嘛、板彎裂示意', `
        <text class="hd" x="16" y="586">端電極：由內到外 Cu →〔導電樹脂〕→ Ni → Sn，順序不准對調</text>
        <g transform="translate(0,86)">${endCut(16, false)}${endCut(324, true)}</g>
        <text class="hd" x="16" y="824">四層各自在幹嘛（由內到外）</text>${legend}
        <text class="sub" x="16" y="940" style="fill:var(--dg-warn)">★ 把 Ni 畫在 Sn 外面是最常見的錯；樹脂層是夾在 Cu 與 Ni 之間，不是最外層。</text>
        <!-- 板彎裂：整塊沿用原本的座標，只把它往下搬（translate），內容一個字都沒改 -->
        <g transform="translate(0,790)">
          <rect class="frame" x="16" y="170" width="270" height="128" rx="8"/>
          <text class="hd" x="30" y="192">② 板彎裂（flex crack）</text>
          <path d="M32,236 Q151,212 270,236" stroke="var(--dg-pcb)" stroke-width="9" fill="none" stroke-linecap="round"/>
          <rect x="113" y="214" width="30" height="5" rx="1" fill="var(--dg-cu)"/><rect x="161" y="214" width="30" height="5" rx="1" fill="var(--dg-cu)"/>
          <rect x="123" y="198" width="60" height="16" rx="2" fill="url(#mcT)"/>
          <rect x="123" y="198" width="11" height="16" rx="1.5" fill="var(--dg-sn)"/><rect x="172" y="198" width="11" height="16" rx="1.5" fill="var(--dg-sn)"/>
          <!-- A2：45° 裂。起點在安裝面（底面）的端電極內緣 x=134，往「外」上方 45° 走到端電極 x=123 -->
          <path d="M134,214 L129,209 L127,208 L123,203" stroke="var(--dg-err)" stroke-width="1.8" fill="none"/>
          <!-- A1：三點彎。板子中間上凸（元件在凸面＝受拉面，陶瓷怕拉不怕壓），所以受力一定是「兩端往下、中央往上」。 -->
          <path d="M40,241 l0,9 m-3.5,-3.5 l3.5,3.5 l3.5,-3.5M262,241 l0,9 m-3.5,-3.5 l3.5,3.5 l3.5,-3.5" stroke="var(--dg-ink-3)" stroke-width="1.2" fill="none"/>
          <path d="M151,250 l0,-14 m-4,4.5 l4,-4.5 l4,4.5" stroke="var(--dg-ink-3)" stroke-width="1.4" fill="none"/>
          <text class="sub" x="30" y="266">板子受力 → 應力傳到陶瓷本體 → 裂</text>
          <text class="sub" x="30" y="282">車規靠軟端子（導電樹脂）擋這一刀</text>
        </g>
        <!-- 「車規為什麼難做」在板彎裂旁邊：它就是那張小圖的結論。660 寬放不下一行一句，三句各斷成兩行，一個字都沒改。 -->
        <rect class="frame" x="300" y="960" width="344" height="146" rx="8"/>
        <text class="hd" x="314" y="982">車規為什麼難做</text>
        <text class="sub" x="314" y="1004">溫度等級（例如 X8R 到 150 °C）要換一套配方，</text>
        <text class="sub" x="314" y="1022">不是同一顆貼個標籤。</text>
        <text class="sub" x="314" y="1044">車子的板子會彎 → 要加導電樹脂層（軟端子），</text>
        <text class="sub" x="314" y="1062">多一道製程，而且 ESR 變高。</text>
        <text class="sub" x="314" y="1084">AEC-Q200 全項（含基板彎曲）＋ 零缺陷框架；</text>
        <text class="sub" x="314" y="1102">認證與換料時程長，產能一綁就難轉。</text>`)}

      <!-- ================= ③ 製造流程 ＋ 為什麼越貴（預設收合） ================= -->
      ${fold('mc3', '③ 怎麼做出來的：十道製程併成五格，以及為什麼疊越多層越貴', '五格製程流程、整顆良率隨層數下滑的曲線', `
        <text class="cap" x="16" y="1112">製造流程（十道併成五格）　★ 燒結一定在端電極之前 —— 反過來端電極會先被燒掉</text>
        ${processBar(16, 1122, [{ seg: SEG, t: '流延成膜', s: '陶瓷漿料刮成生胚膜' },
    { seg: SEG, t: '網印 ＋ 疊層', s: '交替方向印 Ni 電極' },
    { seg: SEG, t: '加壓 ＋ 切割', s: '壓實後切成單顆' },
    { seg: SEG, t: '排膠 ＋ 燒結', s: '還原氣氛高溫燒結' },
    { seg: SEG, t: '端電極 ＋ 電鍍', s: '800–900 °C 燒附 ＋ 電鍍' }], 200, { cols: 3 })}
        <rect class="frame" x="16" y="1236" width="628" height="150" rx="8"/>
        <text class="hd" x="30" y="1258">為什麼疊越多層越貴</text>
        <text class="sub" x="30" y="1280">容值 ∝ 層數 ÷ 單層厚度 → 要大容值只有</text>
        <text class="sub" x="30" y="1298">兩條路：疊更多層，或把每層做更薄。</text>
        <text class="sub" x="30" y="1316">每多一層就多一次網印與疊層，而整顆良率</text>
        <text class="sub" x="30" y="1334">是每層良率的連乘 —— 層數越多越陡。</text>
        <text class="sub" x="30" y="1352">層變薄 → 粉體要更細、絕緣裕度變小；燒結</text>
        <text class="sub" x="30" y="1370">時電極與陶瓷收縮不匹配，容易分層與裂。</text>
        <g transform="translate(130,412)">
          <path class="axis" d="M330,852V936H474"/>
          <path d="M330,858 C362,861 388,872 408,890 S446,924 472,933" stroke="var(--dg-accent)" stroke-width="2" fill="none" opacity=".85"/>
          <text class="sub" x="330" y="850">整顆良率</text><text class="sub" x="404" y="950">層數 →</text>
        </g>`)}

      <!-- ================= ④ 尺寸代號、這一格有誰、資料來源（預設收合） ================= -->
      ${fold('mc4', '④ 尺寸代號有兩套、這一格是哪幾家、資料來源與免責', '三種尺寸的實體比例尺、EIA 與公制對照、成分名單與 2026 產業變數', `
        <text class="hd" x="16" y="1432">③ 尺寸代號有兩套，別記混</text>
        <!-- 尺寸尺是附註級：單色 --dg-mute、不穿主角的陶瓷材質（上一輪降權的結論，維持） -->
        <g transform="translate(0,1074)">
          ${chip(22, 79, 40, 396)}${chip(114, 48, 24, 396)}${chip(174, 32, 16, 396)}
          <path d="M22,410V422M101,410V422M22,416H101" stroke="var(--dg-mute)" stroke-width="1" opacity=".7" fill="none"/>
          <text class="num" x="109" y="421" style="fill:var(--dg-mute)">1 mm</text>
        </g>
        <text class="sub" x="250" y="1460">EIA 0402 ＝ 公制 1005 ＝ 1.0 × 0.5 mm</text>
        <text class="sub" x="250" y="1478">EIA 0201 ＝ 公制 0603 ＝ 0.6 × 0.3 mm</text>
        <text class="sub" x="250" y="1496">EIA 01005 ＝ 公制 0402 ＝ 0.4 × 0.2 mm</text>
        <!-- A5-a（mechanical-engineer 複驗）：把「這張圖對應到誰」講清楚。
             零件掛的是 supply_chain.yaml 的 passive_comp 環節，但那一格的名字是
             「被動元件 MLCC／**電阻**」—— 成分跟「被動元件 MLCC」族群不是同一份名單。 -->
        <rect class="frame" x="16" y="1516" width="404" height="132" rx="8"/>
        <text class="cap" x="30" y="1540">零件顏色＝環節色。點零件篩的是「被動元件</text>
        <text class="cap" x="30" y="1558">MLCC／電阻」這一格：2327 國巨／2492 華新科／</text>
        <text class="cap" x="30" y="1576">2375 凱美／3026 禾伸堂／6173 信昌電。</text>
        <text class="cap" x="30" y="1594">這一格含晶片電阻 —— 凱美是以電阻進到這一格、</text>
        <text class="cap" x="30" y="1612">不做 MLCC；做 MLCC 的是 2327／2492／3026／6173。</text>
        <text class="cap" x="30" y="1630">資料來源與信心度見 docs/diagram_specs/mlcc_stack.md。</text>
        <text class="cap" x="16" y="1672">2026 產業變數：村田對部分消費級 GRM／GRJ 與車規 GCM／GCJ／GCG 料號發出 EOL</text>
        <text class="cap" x="16" y="1690">（最後下單 2028/3、最後出貨 2029/3），規格替代與轉單是這一格現在的故事。</text>
        <text class="cap" x="16" y="1712">示意圖，非實物比例｜層數與各層厚度均為示意：圖上畫 16 層電極（⋮ ×N），</text>
        <text class="cap" x="16" y="1730">實際高容量品 400～1000 層以上；介電 0.5–2 µm、內電極約 0.5 µm。</text>`)}
    </svg>`;
  }

  /* ================================================================ 剖析圖的掛點（slot）
     2026-09-21 改：以前是「一條產業鏈一張圖」（`window.Diagrams[<chain id>]`），
     所以五張已經寫好的規格書一張都畫不出來 —— 它們畫的全是**族群層級**的東西
     （MLCC／面板／網通板卡在 electronics，輕油裂解在 traditional，變壓器 GIS 在 infrastructure），
     而 electronics 一條鏈就要掛三張、traditional 更是塑化與生技觀光共用一個位子。
     現在：**key 可以是族群 id，也可以是產業鏈 id。**
       查找順序＝ 族群專屬圖 → 這條鏈的預設圖 → 都沒有就不畫。
     `scene` 是對應的 Three.js 場景 id（site/three3d.js 的 SCENES），沒有就是沒有 3D。*/
  const SLOTS = {
    /* ★ 2026-09-21 art-director 獨立量測：這兩張舊圖在**任何寬度都不合格**，
       連 1440 全寬都還沒到 12px（半導體 10.47px、AI 伺服器 11.57px），
       900px 螢幕上只剩 6.26px / 6.92px。Andy 已經講過三次「文字太小」。
       根因和 MLCC 那張完全一樣：欄寬永遠遠小於螢幕寬，viewBox 1220 被壓成 ×0.659
       —— **字級怎麼調都沒用**。分兩步修完：
         第一步（已做）native：圖維持原尺寸，900px 的縮放從 ×0.659 拉回 ×1.0。
         第二步（已做，分支 claude/dg-typo）字級標準：12px 變成 .dg 的基準
         （--dg-fs-min），labelRow／lrow3 的行距同步從 13px 改成 16px ——
         那正是「字級一升就會擠在一起」的那件事，不是順手改的，
         是先量到 MLCC 已經有六對重疊 1.00px 才動的。
       現在量到的畫面真實字級：1440 13.22px／800 12.00px／390 12.00px。*/
    /* ★ 2026-09-21（Andy）：`q` ＝**這張圖回答哪一個具體問題**，一定要寫。
       它不是裝飾文案 —— 圖別選單就是靠它讓人在「還沒點進去」的時候就知道
       自己要不要點；沒有 `q` 的圖等於在叫人先點進去再猜。
       寫法：一句話、問句、講到「所以我該怎麼用」，不要只描述圖上有什麼。*/
    /* ⚠ `semiconductor` 這個鏈層級的檔位在 2026-09-22 退場了（DECISIONS #234）——
       它跟 `ai_adv_packaging` 畫的是同一顆 CoWoS 封裝的剖面。理由與「內容搬到哪裡」
       寫在本檔上方那段註解。半導體鏈現在走圖別選單，跟 AI 伺服器鏈同一個模式。*/
    ai_server: { level: 'chain', chain: 'ai_server', name: 'AI 伺服器：機櫃與運算托盤', draw: aiServer, scene: 'ai_server', native: 700,   /* ★ 2026-09-23 v2：畫布從 1220 收到 700（卡片外掛成 HTML），native 跟著改 */
      q: '一座 AI 機櫃裡到底裝了什麼？運算托盤、散熱、電源、交換器各佔一塊，台廠站在哪幾格？' },
    mlcc: { level: 'group', chain: 'electronics', name: '被動元件：MLCC 疊層剖析', draw: mlccStack, scene: 'mlcc', native: 660,
      q: '一顆 MLCC 裡面疊了什麼？為什麼車規賣得比消費級貴，又為什麼板子一彎它就裂？',
      /* ★ 2026-09-21：`parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
         為什麼 MLCC 這張特別需要精修：**整張圖只有一個環節**（14 個 [data-seg] 全是 passive_comp），
         所以預設那條路（零件的 data-seg → 該環節的台股）會讓 14 個零件給出一模一樣的答案 ——
         等於沒有回答「這個零件是誰做的」。這裡只覆寫真的有差別的那幾個，其餘照預設走。
         `cos` 只放代號，**「這家在這裡負責什麼」一律讀 supply_chain.json 的 companies[].tech**
         （R3：不准在圖上寫出 YAML 裡沒有的角色描述）。*/
      parts: {
        mlcc_body: {
          name: '陶瓷本體與交錯內電極',
          desc: '陶瓷介電層與鎳（Ni）內電極一層一層疊出來的本體。容值來自「相鄰兩片電極重疊的那一塊」，所以層數越多、每層越薄，容值越大 —— 貴的也是這件事，不是體積。',
          /* 這一格共 5 家，但「做 MLCC 的」只有這 4 家：2375 凱美是以晶片電阻進到這一格的。
             依據不是我的判斷，是 supply_chain.yaml 自己的 note 與圖下方那行註腳（#228①）。*/
          cos: ['2327', '2492', '3026', '6173'],
          note: '同一格還有 2375 凱美，但它是以晶片電阻與鋁質電解電容進到這一格、不做 MLCC，所以這個零件沒有列它。',
        },
        // 端電極：2D 拆成消費級／車規兩張放大剖面、3D 只有一圈（data-alias 接起來），
        // 三個 key 指向同一件事，所以內容寫在 SLOTS 後面一次指派給三個 key（見下方）
        mlcc_pad: {
          name: 'PCB 焊墊與焊錫',
          desc: 'PCB 上的焊墊與焊錫。板子受力時應力就是從這裡傳進陶瓷，車規靠導電樹脂軟端子擋這一刀。',
          cos: [],
          none: '焊墊在板子上，不屬於被動元件這一格 —— 做板子的是 PCB 廠，看「PCB 硬板：多層板剖面與走線」那張圖。',
        },
      },
    },
  };
  /* 端電極三個 key 內容相同，寫一次就好（避免三份文字日後改到不同步）。*/
  SLOTS.mlcc.parts.mlcc_term = SLOTS.mlcc.parts.mlcc_term_cons = SLOTS.mlcc.parts.mlcc_term_auto = {
    name: '端電極（包住端部五個面）',
    desc: '包住兩個端部的金屬帶，由內到外是銅（Cu）→〔車規多一層導電樹脂〕→ 鎳（Ni）→ 錫（Sn）。樹脂層夾在 Cu 與 Ni 之間，不是最外層 —— 它是車規擋板彎裂的那一層。',
    cos: ['2327', '2492', '3026', '6173'],
    note: '端電極是 MLCC 廠自己做的一道製程（燒附 → 鍍 Ni → 鍍 Sn），不是外購零件，所以這裡列的就是做 MLCC 的那幾家。',
  };
  const isGroupSlot = (id) => !!(SLOTS[id] && SLOTS[id].level === 'group');
  const isChainSlot = (id) => !!(SLOTS[id] && SLOTS[id].level === 'chain');
  window.DiagramSlots = {
    /* 這一頁現在該畫哪一張？回傳 slot id 或 null。
       groupId 傳進來的是「使用者選到的族群」；沒選就傳 null。*/
    pick(chainId, groupId) {
      if (groupId && isGroupSlot(groupId) && SLOTS[groupId].chain === chainId) return groupId;
      if (chainId && isChainSlot(chainId)) return chainId;
      return null;
    },
    // 這條鏈上有專屬圖的族群（順序不保證，呼叫端自己照成交值排）
    groupsOf(chainId) { return Object.keys(SLOTS).filter(k => isGroupSlot(k) && SLOTS[k].chain === chainId); },
    // 這條鏈「有可能」畫得出圖嗎（鏈層級或任何一個族群層級）—— 上方切換列的小標記用
    anyIn(chainId) { return isChainSlot(chainId) || this.groupsOf(chainId).length > 0; },
    chainDefault(chainId) { return isChainSlot(chainId) ? chainId : null; },
    // 這張圖掛在哪一條鏈上（路由要驗「網址上的 slot 真的屬於這條鏈」，不然貼錯網址會畫出別條鏈的圖）
    chainOf(id) { return SLOTS[id] ? SLOTS[id].chain : null; },
    // 'chain'＝整條鏈的架構圖（點進鏈就直接看到）；'group'＝單一產品，要有自己的網址
    level(id) { return SLOTS[id] ? SLOTS[id].level : null; },
    // 這張圖回答哪一個問題（圖別選單與標題都讀它）
    q(id) { return SLOTS[id] ? (SLOTS[id].q || '') : ''; },
    /* 這條鏈拿哪一張圖當「代表圖」（跨鏈面板 E6 的縮圖用）。
       ★ 2026-09-22：以前這裡直接等於「鏈層級的架構圖」。半導體鏈那張退場之後
       （DECISIONS #234），如果還是綁在鏈層級，跨鏈面板就只剩一張縮圖 ——
       而那個面板的整個意義就是「同一個環節在**兩條**鏈上的位置不一樣」。
       所以改成：鏈層級的圖優先，沒有就找這條鏈上宣告 `rep: true` 的族群圖。*/
    rep(chainId) {
      if (isChainSlot(chainId)) return chainId;
      return Object.keys(SLOTS).find(k => isGroupSlot(k) && SLOTS[k].chain === chainId && SLOTS[k].rep) || null;
    },
    // 目前有代表圖的鏈（跨鏈面板的縮圖用；以前寫死成 DG_CHAINS）
    chains() {
      const seen = new Set();
      Object.keys(SLOTS).forEach(k => { const c = SLOTS[k].chain; if (c && this.rep(c)) seen.add(c); });
      return [...seen];
    },
    draw(id) { return SLOTS[id] ? SLOTS[id].draw() : ''; },
    name(id) { return SLOTS[id] ? SLOTS[id].name : ''; },
    scene(id) { return SLOTS[id] ? (SLOTS[id].scene || null) : null; },
    /* native＝這張圖要用「原尺寸」畫，不准被欄寬壓縮（回傳最小寬度 px，0＝沒宣告）。
       為什麼要有這個：產業鏈頁的 main 只有 1080px（右邊有側欄），1100px 的螢幕更只剩 740，
       量出來 1440→984px(×0.81)、1100→644px(×0.53)、900→444px(×0.36)——
       12px 的字會被壓成 6.3px 甚至 4.4px。這正是 Andy 一直在講的「文字太小」。
       宣告 native 的圖改成「維持原尺寸、欄位不夠寬就左右滑」，字級才守得住。*/
    native(id) { return SLOTS[id] ? (SLOTS[id].native || 0) : 0; },
    /* 這張圖有沒有「零件 → 誰做的」精修對應（key＝data-part）。
       回 null ＝沒有精修，小卡就走預設的那條路（data-seg → 該環節的台股與料號）。
       ★ 這份對應**只住在繪圖端**（SLOTS 或 site/dg/<slot>.js 的 register 定義），
         不准寫進 pipeline/groups/supply_chain.yaml —— 那份是 Andy 校訂的成分表。*/
    parts(id) { return (SLOTS[id] && SLOTS[id].parts) || null; },
    has(id) { return !!SLOTS[id]; },
  };
  /* 舊介面留著（`window.Diagrams[<id>]()`）—— 題材圖與驗收腳本還在用。
     新的查找一律走 window.DiagramSlots，不要在別的地方再維護第二份名單。*/
  window.Diagrams = Object.keys(SLOTS).reduce((o, k) => (o[k] = SLOTS[k].draw, o), {});
  // 題材產品圖（site/themes3d.js）共用同一套樣式與 3D 工具，兩邊看起來才是同一套產品圖
  window.DG = { STYLE, SHADOW_DEFS, labelRow, lrow3, note, extRow, processBar, foldBar, fold, chainLink, pointer, cardHead, explode, explodeZ, EXPLODE_GAP, shadow, fitTexts, externalize, stampParts, partHit, IX, IY, px, py, P3, onTop, onXZ, onYZ, box, cyl, panel, wire, floor, cells, p3 };

  // ===== 2.5D 材質（玻璃／發光／光束）=====
  /* Andy 2026-09-22 晚的參考圖（docs/diagram_refs/2d_panel_dark_light.webp）翻成三支可重用的 helper。
     視覺語言：**帶厚度、圓角、半透明漸層的玻璃板**；發光只給流動與光束；亮＝米白底＋柔陰影、暗＝深藍底＋發光；
     兩版構圖相同、只換材質與光 —— 所以這三支不吃模式參數，模式差異全在 STYLE 的 --fx-* 旋鈕與 --dg-* token。

     效能（#239）：feGaussianBlur 一張圖最多 3 個「元素」。beam() 的光暈是一條路徑、shadows() 的柔陰影是**一個群組**
     （群組套一次濾鏡算一個元素），所以「一條主光束 ＋ 一組陰影 ＋ 一個靜態光點」剛好用完預算。
     `glowDefs()` 一張圖只放一次（<defs> 裡），濾鏡 id 固定 fxGlow／fxSoft，漸層 fxSheen／fxSheenT；
     縮圖那條 uniqIds 會連 url(#…) 一起加後綴，所以同一頁兩張圖不會撞。

       fx.glowDefs({r, soft})         → <defs> 內容：光暈濾鏡、柔陰影濾鏡、兩個共用漸層（白光 sheen）
       fx.glass(x, y, w, h, o)        → 2D 玻璃方塊；o.iso={dx,dy} 就變成**等角玻璃板**（頂面 ＋ 前面 ＋ 右側面）
                                        o：fill（css 顏色，一律 token）、t（2D 的厚度，往右下擠出）、rx、cls（加在前面那塊上，例如 'part'）、
                                           attrs（加在群組上）、top（頂面上要疊的內容，畫在頂面座標系：原點＝前緣左端）
       fx.beam(d, o)                  → 光束：blur 光暈（o.glow≠false）＋ 實線 ＋ 流動虛線（o.flow）＋ 端點光點（o.dots=[[x,y],…]）
                                        o.color 一律 token（電力 --dg-pwr、訊號 --dg-sig、液冷 --dg-cool），o.w 線寬
       fx.shadows(shapes)             → 把一串形狀（已含 x/y 位移）包成一個柔陰影群組（一次濾鏡）
       fx.beams([{d,color,w,dots}], o)→ 多條光束共用**一個**光暈濾鏡（面板的 R／G／B 三道穿層光束＝一個元素）
       fx.molecule(cx,cy,rx,ry,ang)   → 液晶分子小橢球（帶高光；角度 0 躺平、−70 立起來）*/
  const fx = {
    glowDefs(o) {
      o = o || {};
      const r = o.r != null ? o.r : 4, s = o.soft != null ? o.soft : 3;
      return `<filter id="fxGlow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="${r}"/></filter>`
        + `<filter id="fxSoft" x="-30%" y="-40%" width="160%" height="200%"><feGaussianBlur stdDeviation="${s}"/></filter>`
        + `<linearGradient id="fxSheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dg-sn)" style="stop-opacity:var(--fx-sheen)"/><stop offset=".55" stop-color="var(--dg-sn)" stop-opacity="0"/></linearGradient>`
        + `<linearGradient id="fxSheenT" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--dg-sn)" style="stop-opacity:var(--fx-sheen)"/><stop offset=".7" stop-color="var(--dg-sn)" stop-opacity="0"/></linearGradient>`;
    },
    glass(x, y, w, h, o) {
      o = o || {};
      const rx = o.rx != null ? o.rx : 6, cls = o.cls ? ' ' + o.cls : '';
      const st = o.fill ? ` style="--fxc:${o.fill}"` : '';
      const at = o.attrs ? ' ' + o.attrs : '';
      if (o.iso) {
        const dx = o.iso.dx, dy = o.iso.dy;                  // 頂面往右後上擠出去的位移（dy 是負的）
        const top = `M${x},${y} L${x + w},${y} L${x + w + dx},${y + dy} L${x + dx},${y + dy}Z`;
        const right = `M${x + w},${y} L${x + w + dx},${y + dy} L${x + w + dx},${y + h + dy} L${x + w},${y + h}Z`;
        return `<g class="fxg"${st}${at}>`
          + `<path class="fxb" d="${right}"/><path class="fxr" d="${right}"/>`
          + `<path class="fxt" d="${top}"/><path class="fxst" d="${top}"/>`
          + (o.top ? `<g transform="translate(${x},${y})">${o.top}</g>` : '')
          + `<rect class="fxb${cls}" x="${x}" y="${y}" width="${w}" height="${h}" rx="${Math.min(rx, h / 2)}"/>`
          + `<rect class="fxs" x="${x}" y="${y}" width="${w}" height="${h}" rx="${Math.min(rx, h / 2)}"/>`
          + `<path class="fxe" d="${top}"/><path class="fxe" d="${right}"/>`
          + `<rect class="fxe" x="${x}" y="${y}" width="${w}" height="${h}" rx="${Math.min(rx, h / 2)}"/>`
          + `<path class="fxh" d="M${x + 2},${y} L${x + w - 2},${y}"/></g>`;
      }
      const t = o.t || 0;
      return `<g class="fxg"${st}${at}>`
        + (t ? `<rect class="fxb" x="${x + t}" y="${y + t}" width="${w}" height="${h}" rx="${rx}"/><rect class="fxr" x="${x + t}" y="${y + t}" width="${w}" height="${h}" rx="${rx}"/>` : '')
        + `<rect class="fxb${cls}" x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>`
        + `<rect class="fxs" x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>`
        + `<rect class="fxe" x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>`
        + `<path class="fxh" d="M${x + rx},${y + 1.5} L${x + w - rx},${y + 1.5}"/></g>`;
    },
    beam(d, o) {
      o = o || {};
      const st = `style="${o.color ? `--fxc:${o.color};` : ''}${o.w ? `--fxw:${o.w}` : ''}"`;
      const dots = (o.dots || []).map(([px_, py_]) =>
        `<circle class="fxdh" cx="${px_}" cy="${py_}" r="${(o.dotR || 3) * 2.4}"/><circle class="fxd" cx="${px_}" cy="${py_}" r="${o.dotR || 3}"/>`).join('');
      return `<g class="fxbeam${o.cls ? ' ' + o.cls : ''}" ${st}${o.attrs ? ' ' + o.attrs : ''}>`
        + (o.glow === false ? '' : `<path class="fxb-glow" d="${d}" filter="url(#fxGlow)"/>`)
        + `<path class="fxb-core" d="${d}"/>`
        + (o.flow ? `<path class="fxb-flow" d="${d}"/>` : '')
        + dots + `</g>`;
    },
    shadows(inner) { return `<g class="fxsh" filter="url(#fxSoft)" pointer-events="none">${inner}</g>`; },
    /* ---- restyle-w2b 2026-09-22：面板那張要 R／G／B 三道光束穿層，三條各自套 beam() 就吃掉三個 feGaussianBlur 元素。
       beams(list, o)：**多條光束共用一個光暈濾鏡**（光暈那一層是一個帶 filter 的群組＝算一個元素）。
         list＝[{d, color, w, dots}]，o 同 beam()（flow／glow／dotR／cls／attrs）。顏色一律 token。
       單條光束仍然走 beam()，介面沒動。*/
    beams(list, o) {
      o = o || {};
      const one = (b, cls) => `<path class="${cls}" d="${b.d}" style="${b.color ? `--fxc:${b.color};` : ''}${b.w ? `--fxw:${b.w}` : ''}"/>`;
      const dots = list.map((b) => (b.dots || []).map(([px_, py_]) =>
        `<circle class="fxdh" cx="${px_}" cy="${py_}" r="${(o.dotR || 3) * 2.4}" style="--fxc:${b.color}"/><circle class="fxd" cx="${px_}" cy="${py_}" r="${o.dotR || 3}" style="--fxc:${b.color}"/>`).join('')).join('');
      return `<g class="fxbeam${o.cls ? ' ' + o.cls : ''}"${o.attrs ? ' ' + o.attrs : ''}>`
        + (o.glow === false ? '' : `<g filter="url(#fxGlow)">${list.map((b) => one(b, 'fxb-glow')).join('')}</g>`)
        + list.map((b) => one(b, 'fxb-core')).join('')
        + (o.flow ? list.map((b) => one(b, 'fxb-flow')).join('') : '')
        + dots + `</g>`;
    },
    /* 液晶分子：一顆帶高光的小橢球（cx, cy, rx, ry, 旋轉角度, 顏色 token）。躺平＝角度 0、立起來＝角度 −70。*/
    molecule(cx, cy, rx, ry, ang, fill) {
      return `<g transform="translate(${cx},${cy}) rotate(${ang || 0})"><ellipse rx="${rx}" ry="${ry}" fill="${fill || 'var(--dg-pn-rod)'}" opacity=".92"/>`
        + `<ellipse cx="${(-rx * .3).toFixed(1)}" cy="${(-ry * .35).toFixed(1)}" rx="${(rx * .42).toFixed(1)}" ry="${(ry * .3).toFixed(1)}" fill="var(--dg-sn)" style="fill-opacity:var(--fx-hl)"/></g>`;
    },
  };
  window.DG.fx = fx;

  /* ★ 2026-09-21：一張圖一個檔（`site/dg/<slot>.js`）。
     `docs/diagram_plan.md` 排了 14 張，全部塞進這個檔會變成兩千多行，
     而且**多個人同時畫不同的圖就會一直撞在同一個檔上** ——
     這是 Andy 說「一口氣把所有圖完成」之後第一個會卡住的地方。

     所以這裡開一支註冊介面，每張圖在自己的檔裡呼叫：
         window.DG.register('pcb_rigid', {
           level: 'group', chain: 'ai_server', name: '…', draw: fn,
           native: 980, q: '這張圖回答什麼問題', scene: null,
         });
     `site/index.html` 已經把 14 個檔位的 <script> 一次寫好，
     **所以新增一張圖不需要再動 index.html**（那個檔一動就會跟別人撞）。
     還沒畫的檔只有一行註解、不呼叫 register，SLOTS 裡就不會多出空的項目。

     順序：`diagrams.js` → `dg/*.js` → `industry.js`（都是同步 <script>，
     所以 industry.js 讀 DiagramSlots 時 14 張已經註冊完了）。*/
  window.DG.register = function (id, def) {
    if (!id || !def || typeof def.draw !== 'function') {
      console.warn('[DG.register] 略過不合格的註冊：', id);   // 壞掉的一張不該讓整頁掛掉
      return;
    }
    if (SLOTS[id]) { console.warn('[DG.register] 重複註冊，後面的蓋掉前面的：', id); }
    SLOTS[id] = def;
    window.Diagrams[id] = def.draw;     // 舊介面同步（題材圖與驗收腳本還在用）
  };
})();
