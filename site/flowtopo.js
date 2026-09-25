/* ============================================================================
   資金去向・拓撲版（site/flowtopo.js）—— 原生 Canvas 的微光拓撲、貝茲光纖、粒子流
   ----------------------------------------------------------------------------
   Andy 2026-09-24 回報資金流向頁「資金去向」卡：
     ① 整張卡太大（高度 1700px 以上、要一直捲）→ 1440 寬下整張卡 ≤ 760px，一屏看得完
     ② 最左邊一欄有一排散亂的小點，看起來是壞掉的
     ③ 照他給的參考檔（微光拓撲、貝茲曲線光纖、粒子流）重畫

   分工（刻意這樣切，少碰 app.js，避免和別人撞檔）：
     · app.js 的 renderSankey() 照舊算**資料模型**（四層樹、% 佔上一層、漲跌三角、
       即時／盤後、聚焦壓暗、展開成分股、你點開的個股）—— 那一大段口徑一個字都沒改。
     · 桌機（視窗寬 > 820px）把那棵樹交給這支畫；手機維持原本的 ECharts 樹。
     · 點節點、點背景、提示框的**內容**全部回呼 app.js（同一支處理函式），
       所以下鑽、成分股面板、兩階段點個股的行為跟經典版是同一套，不是再寫一份。

   為什麼控得住高度：個股層改成**只有點開的那個族群才展開**（族群節點右邊長出成分股），
   其餘族群只畫到族群那一層 —— 18 個族群一列 24px，整張圖約 520px。

   ② 的根因（經典版）：小圓點那層 canvas 的節點座標是在 ECharts 畫完那一刻讀一次，
   之後容器長高／面板打開換版面時座標沒有重讀，點就留在舊曲線上，看起來就是左邊一排散點。
   這支的粒子座標每一幀都從**目前的**曲線查表算，版面一變曲線就重算，物理上不會脫線；
   驗收另外量「每顆粒子離它那條曲線的距離」與「根節點左邊有沒有粒子」。

   ★ 2026-09-25 Andy：「維持經典版風格，但傳輸特效需要跟拓撲版一樣」→ 加一個**經典版面**模式
   （opts.layout === 'classic'，桌機預設）：
     · 版面、層級、標籤照經典版（ECharts 樹）：四層都常駐（台股 → 產業鏈 → 族群 → 代表股三檔）、
       欄位等分、葉子等距（同族群間距 1、跨族群 2，和 ECharts tree 的 separation 同一條規則）、
       父節點在第一個與最後一個子節點的正中間、標籤是節點右邊的描邊文字（不是膠囊）、代表股標 % 佔族群、
       圓點大小沿用經典版的 8＋22×√(佔比) 直徑、產業鏈是直立細條。
     · 線與傳輸特效沿用這支的拓撲版那一套（同一組映射，不另寫）：線寬依金額平方根 1～13px、
       發光光纖、粒子速度／密度／明暗依金額拉開、shadowBlur ≤ 6、換日依排名換位的補間、動態開關、減少動態。
   原本的拓撲版（族群點開才長個股、膠囊標籤、卡片 ≤ 760px）照舊留著，opts.layout 不給就是它。

   ★ 2026-09-26 Andy：「資金去向維持經典版的樹狀結構，不要像圖三那樣；樹狀改成如圖四那樣結構；幫我參考圖五」
     （附一支原型 HTML：粒子碰撞激發、擴散震波、雙層光纖）。經典光纖（layout 'classic'）改版，拓撲版不動：
     · 圖三（不要）：產業鏈畫成一根直條、一大把線從直條上扇形散出 → 產業鏈改成**圓點節點**，線一律從圓心出去。
     · 連線（Andy 完整規格，蓋掉對圖四「直角樹」的判讀）：**禁止生硬直線，一律平滑水平切線的三次貝茲**，
       控制點 CP1＝(x0＋dx×0.55, y0)、CP2＝(x0＋dx×0.45, y1)（兩端切線水平、中段轉折比舊的 S 形快一點）。
       四層（根→產業鏈、產業鏈→族群、族群→代表股）一律這條；起點＝父節點圓心那一列（不再在直條上依目標 y 排開），
       粒子沿同一條貝茲的等弧長查表走。線寬仍依金額平方根（粗細對比不變），版面位置不變。
     · 圖五＋原型（要的特效）：
         ① 粒子＝白色核心＋線色光暈（預先畫好的小圖，shadowBlur 只在畫小圖時用一次，≤ 6px）；
         ② 碰撞激發：粒子到站時終點節點 hitFlash ＋0.35（上限 1，逐幀衰減 0.035）→ 外圈放大發光、
            hitFlash > 0.3 核心轉白（漸變，不是一下跳白）、標籤變亮（最上層那張 ftglow 畫布疊一層亮字）；
         ③ 擴散震波：到站時 45% 機率外擴一圈（r → r＋26、每幀 ＋0.85；alpha 0.85 每幀 −0.026；線寬 1.6），顏色＝節點色；
            同時最多 60 圈（CFG.RP_MAX），同一個節點 180ms 內不重複起漣漪（不然大節點會疊成一團同心圓）；
         ④ 雙層光纖：外層寬而淡的光暈管（寬 w×3.2、alpha 0.08）＋內芯（寬 w×0.9、alpha 0.32 起跳）；
         ⑤ 節點常駐一圈淡的底（r＋2、alpha 0.25）—— 靜態的，不脈動（Andy 否決過一直脈動）。
     · 原型的顏色是每條線不同色；這裡照站上規矩：節點、線、粒子一律用**產業鏈色**，紅綠只給漲跌字（▲▼）。
     · 規格的 shadowBlur 24×hitFlash（外光環）、10（漣漪光暈）：前者超過專案硬上限 10px，而且每幀每個節點設
       shadowBlur 在軟體繪圖上很貴 —— 外光環改用預先畫好的放射漸層小圖放大（不是 shadowBlur，半徑照規格 r＋8×hitFlash，
       再外擴 60% 淡出來模擬模糊），漣漪光暈改成底下多描一圈寬 4px、低透明度的同色環。shadowBlur 全張仍 ≤ 6px。

   ★★ 2026-09-26（第二版）Andy：「參考圖顏色更鮮豔」，指出第一版「濁、混亂」四點，附黃金標準
     docs/prototypes/flow_perfect_topology.html（＋鮮豔度參考 ref_vivid_0926.png）。上面第一版的數字以這一段為準：
     1. 去霧：外暈 weight×2.4、alpha 0.09；內芯**固定 1.1px、alpha 0.65**；毛細線 0.7px／0.2、外暈 0.04（drawBaseEl）。
        weight 改成參考稿的 0.8～3.8；透明度照參考稿殘影的穩態畫（見 CFG.EL_TRAIL），和鮮豔度參考圖並排量過。
        粒子白核心、光暈 ≤ 5px、半徑 2.2（主幹）／1.7（族群）／1.3（毛細）。
     2. 節點：4.5～7.5 的實心圓點＋1px 白描邊＋6px 微光，拿掉大發光圈與常駐淡底；碰撞光環 r＋5×hitFlash、alpha ×0.45；
        漣漪 r→r＋16、每幀 ＋0.7、alpha 0.8 每幀 −0.035、線寬 1.2。標籤改成節點右側 6px、高 17px 的深色圓角膠囊
        （名稱＋佔比＋漲跌）；「標籤變亮」與它那張 ftglow 畫布拿掉（黃金標準的字是固定色）。
     3. 曲線張力 CP1＝x0＋dx×0.45、CP2＝x1−dx×0.45；族群用等距垂直槽位（slotPlan：36～42px），同鏈連續排、平行滑入。
     4. 代表股：族群往右一條毛細線到固定 X（寬度 83%），那裡垂直排三檔（小點 1.8px＋「名稱 佔比%」）。
        每檔各自一條毛細線（三條在族群那頭重疊、到尾端才分開 13px），粒子才能照各檔的金額跑、撞到的是那一檔。
     5. 鮮豔：深色主題畫布底 #050a14；產業鏈色改飽和版（CHAIN_HUE_EL）。
     字級照專案下限 12px（參考稿 11／10px），所以代表股間距 13px（參考稿 9px 配 10px 字）。

   ★ 2026-09-26（總覽）Andy：「昨日資金去向這邊 UI 也需要重新設定，但功能照舊」→ 加一個緊湊版 layout:'mini'：
     和經典光纖第二版**同一套視覺**（精緻圓點、細亮光芯＋淡外暈、CP 0.45 對稱貝茲、飽和產業鏈色、17px 膠囊、
     白核心粒子＋碰撞光環／細漣漪），但只有三層（加權指數 → 產業鏈 → 族群，沒有代表股欄）、沒有上方說明列
     （動態開關縮成畫布左上角一顆小鈕）、粒子預算小（CFG.MINI_P_BUDGET）、高度由呼叫端給（總覽那張的高度公式不變）。
     根節點標籤放在圓點正上方（和舊版一樣），產業鏈與族群的膠囊在節點右邊；欄位依「最長的族群標籤」往右靠齊，
     產業鏈那欄夾在根與族群之間、讓膠囊不壓到族群欄（見 layoutMini）。

   ★ 2026-09-26（晚）Andy：「將資金去向只留下經典光纖版本，並且族群後的個股先隱藏，只有游標移動過去會顯示」：
     · 經典光纖（layout 'classic'）的代表股欄（83% 那欄三檔＋毛細線）**預設收起**（S.leafHover）：
       滑鼠移到某個族群的圓點、膠囊或它那一格槽位（那一橫條，從族群圓點左邊一路到畫布右緣）→ 只顯示那個族群的三檔（淡入 180ms），
       移開淡出；點開的族群（展開全部成分股）與你掛上去的個股（虛線）常駐。
     · 收起的代表股：毛細線上不發粒子、原本在跑的收掉（省效能）；看不見的點點不到（pickAt 跳過）。族群節點照樣被撞擊激發。
     · 代表股收起時右邊那欄空出來的寬度讓給版面：族群欄往右移（最多到 66%），代表股欄在「族群膠囊最右緣 ＋ 16px」與 83% 取大者，
       所以滑過顯示時不會蓋到任何族群膠囊（見 layoutClassic）。
     · 觸控（沒有 hover）：點一下族群＝照舊展開全部成分股＋面板（展開時常駐顯示），不另加「點一下先顯示三檔」那一段 —— 不會壞。
     拓撲版（layout 'topo'）程式碼留著，但 app.js 已經沒有入口（三選一分段鈕拿掉）。

   規矩（CLAUDE.md，載入時斷言，違規直接丟錯）：
     · 發光 shadowBlur 4～6px（上限 10，這裡壓 6）；只在預先畫好的粒子小圖上用
     · Canvas 字級 ≥ 12px（setTransform 乘 DPR，字是用 CSS px 算的，不會糊）
     · 紅漲綠跌：紅／綠只拿來畫「比前一天多／少」的三角，不拿來當族群色
     · 動畫有開關（記在 localStorage `tw.flowtopo.motion`），系統「減少動態效果」開著就一律靜態
     · 靜止時不閃：動畫關掉就只畫一張靜態圖，沒有任何計時器
   ============================================================================ */
(function () {
  'use strict';

  const CFG = Object.freeze({
    GLOW_MAX: 6,             // 發光上限（專案硬規矩 ≤10；這張壓到 6）
    GLOW_DARK: 5, GLOW_LIGHT: 4,
    FONT_MIN: 12,
    BADGE_H: 18,
    CURVE_K: 0.45,           // S 形貝茲：控制點水平偏移 = dx × 0.45（兩端切線水平）
    ROW: 24,                 // 一個族群一列的目標高度（px）
    LEAF_ROW: 19,            // 成分股一列（膠囊 18px ＋ 1px 縫）
    H_MIN: 420, H_MAX: 600,  // 畫布高度上下限：1440 寬整張卡 ≤ 760px 就是從這裡來的
    BAR_H: 30,               // 上方那條說明＋動態開關
    PULSE: 0.32,             // 碰撞：節點彈性放大到 1.32 倍，再由彈簧收回
    SPRING_K: 240, SPRING_C: 16,
    RIPPLE_GROW: 12, RIPPLE_SEC: 0.8, RIPPLE_MAX: 24,
    P_MAX: 900,              // 粒子物件池上限
    TWEEN_MS: 480,
    LS_MOTION: 'tw.flowtopo.motion',
    /* 經典版面（layout: 'classic'）：數字全部取自經典版 ECharts 樹（app.js renderSankey 的 series 設定）*/
    CL_LEAF_ROW: 16,         // 一片葉子 16px（經典版的高度公式：葉子數 × 16 ＋ 64）
    CL_H_MIN: 560, CL_H_MAX: 1040, CL_H_MAX_EXP: 1400,   // 經典版的上下限（有族群展開時放到 1400）
    CL_LEFT: 14, CL_RIGHT: 132, CL_TOP: 14, CL_BOTTOM: 18,  // 經典版 left 10（根節點半徑 13 會被裁 3px，所以 14）、right 132
    CL_LABEL_GAP: 7,         // 標籤離節點 7px（經典版 label.distance）
    CL_LEAF_LABEL_W: 120,
    /* 經典版面的粒子預算：四層常駐之後連線從 23 條變 77 條，照同一組映射直接發車會到 650 顆左右、
       每幀成本是拓撲版的 2.5～3 倍（headless 實測 7～9ms）。發車率整體乘同一個係數壓回預算內 ——
       係數對每條線一樣，所以「最密／最疏」的比例（驗收 ×6）不變；「每條線至少一顆」的下限不受影響。*/
    CL_P_BUDGET: 380,
    /* ★ 2026-09-26（第二版）黃金標準 docs/prototypes/flow_perfect_topology.html 的版面數字 */
    EL_SLOT_MAX: 42, EL_SLOT_MIN: 36, EL_PAD: 22,   // 族群槽位高度（參考稿 Math.min(42, (h−60)/n)）、上下留白
    EL_LEAF_SP: 13, EL_LEAF_R: 1.8,                 // 代表股間距（12px 字＋1）、小點半徑 1.8
    EL_BADGE_H: 17,                                 // 標籤膠囊高 17、圓角 3
    /* 黃金標準每幀先蓋一層 rgba(5,10,20,.38) 再重畫線 → 線條的「看起來的」透明度會累積到穩態
       a／(1−(1−a)(1−0.38))：內芯 0.65 → 0.83、外暈 0.09 → 0.21、毛細 0.2 → 0.40、毛細外暈 0.04 → 0.10。
       Andy 附的鮮豔度參考圖就是這個穩態。這裡不做整張殘影（軟體繪圖會掉一半幀率），改成底圖直接畫穩態值。*/
    EL_TRAIL: 0.38,
    /* 緊湊版（layout:'mini'，總覽「昨日資金去向」）：族群一格 22px（舊版 ECharts 的「族群數 × 22 ＋ 46」同一個間距），
       鏈與鏈之間最多空 6px；整張的粒子預算 110 顆（總覽首屏，不能讓載入變重）*/
    MINI_SLOT: 22, MINI_GAP: 6, MINI_P_BUDGET: 110,    // 代表股標籤寬度上限（經典版 132 − 12），超過截斷，全名在提示框
    /* ★ 2026-09-26 經典光纖改貝茲規格＋碰撞激發（數字取自 Andy 給的規格／原型，「每幀」換算成「每 1/60 秒」）*/
    /* 三次貝茲控制點（寫成 x0＋dx×k）：CP1＝(x0＋dx×0.45, y0)、CP2＝(x0＋dx×0.55, y1)＝(x1−dx×0.45, y1)。
       2026-09-26 第二版改前 0.55／0.45（CP 交叉、中段轉折急）→ 改後 0.45／0.55（對稱張力，Andy 黃金標準第 3 點）*/
    CL_CP1: 0.45, CL_CP2: 0.55,
    HIT_ADD: 0.35, HIT_DECAY: 0.035,        // 碰撞激發：每到一顆 +0.35（上限 1），每幀 −0.035
    /* 震波（第二版，黃金標準）：r → r＋16、每幀 ＋0.7、alpha 0.8 每幀 −0.035、線寬 1.2；到站 55% 機率起一圈
       （參考稿 Math.random() > 0.45）；代表股（毛細終點）不起。改前：＋26、＋0.85、0.85 遞減、線寬 1.6、45% */
    RP_GROW: 16,
    RP_STEP: 0.7, RP_A0: 0.8, RP_FADE: 0.035, RP_P: 0.55,
    RP_LW: 1.2,
    RP_MAX: 60, RP_COOL: 180,               // 同時最多 60 圈；同一節點 180ms 內不重複起
  });
  (function assertRules() {
    if (!(CFG.GLOW_MAX <= 6 && CFG.GLOW_DARK <= CFG.GLOW_MAX && CFG.GLOW_LIGHT <= CFG.GLOW_MAX
      && CFG.GLOW_DARK >= 4 && CFG.GLOW_LIGHT >= 4)) throw new Error('flowtopo：發光必須在 4～6px');
    if (CFG.BADGE_H < CFG.FONT_MIN + 4) throw new Error('flowtopo：膠囊放不下 12px 字');
  })();

  const FONT = '"Noto Sans TC", -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif';
  const reduceMQ = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：忽略 */ } };
  /* 動畫開不開：系統要求減少動態 → 一律關（不給覆寫）；否則照使用者存的，沒存過＝開 */
  const motionWanted = () => !reduceMQ.matches && lsGet(CFG.LS_MOTION) !== '0';

  /* 任何 CSS 顏色字串 → [r,g,b]（用 canvas 正規化，吃 #hex / rgb() / 具名色）*/
  const _cc = document.createElement('canvas').getContext('2d');
  const _rgbCache = {};
  function rgbOf(c) {
    if (_rgbCache[c]) return _rgbCache[c];
    let out = [62, 224, 255];
    try {
      _cc.fillStyle = '#000'; _cc.fillStyle = c; const s = _cc.fillStyle;
      if (s[0] === '#') { const n = parseInt(s.slice(1), 16); out = [n >> 16 & 255, n >> 8 & 255, n & 255]; }
      else { const m = s.match(/[\d.]+/g); if (m) out = [+m[0], +m[1], +m[2]]; }
    } catch (e) { /* 保底色 */ }
    _rgbCache[c] = out; return out;
  }
  const rgba = (c, a) => { const [r, g, b] = rgbOf(c); return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, a)).toFixed(3)})`; };
  const mixW = (c, f) => { const [r, g, b] = rgbOf(c); return `rgb(${Math.round(r + (255 - r) * f)},${Math.round(g + (255 - g) * f)},${Math.round(b + (255 - b) * f)})`; };
  const fmtN = (v, d) => (isFinite(v) ? Number(v).toFixed(d) : '—');
  const clean = (s) => String(s == null ? '' : s).replace(/[ ]+$/g, '').trim();

  /* ---- 一次性的樣式（跟著全站 CSS 變數走，深淺主題自動換）---- */
  function injectCSS() {
    if (document.getElementById('flowtopoCSS')) return;
    const st = document.createElement('style');
    st.id = 'flowtopoCSS';
    st.textContent = `
#sankey.ftopo{min-height:0}
.ftopo .ftbar{display:flex;align-items:center;justify-content:space-between;gap:10px;height:${CFG.BAR_H}px;
  font-size:12px;color:var(--ink-3);white-space:nowrap;overflow:hidden}
.ftopo .ftbar .ftleg{overflow:hidden;text-overflow:ellipsis}
.ftopo .ftbar .ftleg b{color:var(--ink-2);font-weight:600}
.ftopo .ftbtn{appearance:none;border:1px solid var(--line-2,var(--line));background:var(--panel-2,transparent);color:var(--ink-2);
  border-radius:8px;font-size:12px;padding:3px 10px;cursor:pointer;line-height:18px;flex:0 0 auto}
.ftopo .ftbtn:hover:not(:disabled){border-color:var(--cyan);color:var(--ink)}
.ftopo .ftbtn[aria-pressed="true"]{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 55%,transparent)}
.ftopo .ftbtn:disabled{opacity:.5;cursor:default}
.ftopo .ftstage .ftbtn.ftcorner{position:absolute;left:6px;top:6px;z-index:5;padding:1px 8px;line-height:16px;opacity:.85}
.ftopo .ftstage{position:relative;width:100%;border-radius:10px;overflow:hidden;
  background:radial-gradient(120% 90% at 8% 50%,color-mix(in srgb,var(--cyan) 5%,transparent),transparent 60%)}
.ftopo .ftstage canvas{position:absolute;left:0;top:0;display:block}
.ftopo .ftstage canvas.ftlab{cursor:default}
.ftopo .ftstage canvas.ftlab.hot{cursor:pointer}
.ftopo .fttip{position:absolute;z-index:6;pointer-events:none;max-width:340px;padding:9px 11px;border-radius:10px;
  background:var(--tip-bg,var(--panel));border:1px solid var(--tip-line,var(--line-2));box-shadow:var(--tip-sh,none);
  color:var(--ink);font-size:12.5px;line-height:1.55;opacity:0;transition:opacity .12s;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.ftopo .fttip.on{opacity:1}
.ftopo .fttip .muted{color:var(--ink-3)}
@media (prefers-reduced-motion:reduce){.ftopo .fttip{transition:none}}`;
    document.head.appendChild(st);
  }

  /* =========================================================================
     一個 host（#sankey）一個實例。render() 可以一直叫（換日期、播放、即時、展開），
     節點與連線用 key 對位、就地更新 —— 粒子不會因為換一天就整批消失重來。
     ========================================================================= */
  function create(host) {
    injectCSS();
    host.classList.add('ftopo');
    host.innerHTML = '';
    const bar = document.createElement('div'); bar.className = 'ftbar';
    const leg = document.createElement('span'); leg.className = 'ftleg';
    const mbtn = document.createElement('button'); mbtn.type = 'button'; mbtn.className = 'ftbtn';
    /* id：資金流向頁那張照舊叫 sankeyMotionBtn；總覽那張（#ovFlow）叫 ovFlowMotionBtn —— 兩頁的 DOM 同時在，id 不能重複 */
    mbtn.id = host.id === 'sankey' ? 'sankeyMotionBtn' : (host.id || 'ft') + 'MotionBtn';
    bar.append(leg, mbtn);
    const stage = document.createElement('div'); stage.className = 'ftstage';
    const cvBase = document.createElement('canvas'), cvFx = document.createElement('canvas'), cvLab = document.createElement('canvas');
    /* 2026-09-26 第二版：第一版為「標籤變亮」加的第四張畫布（ftglow）拿掉 —— 黃金標準的膠囊字是固定色，
       被撞只亮節點；少一張全尺寸 HiDPI 畫布，每幀少一次清除與合成 */
    cvBase.className = 'ftbase'; cvFx.className = 'ftfx'; cvLab.className = 'ftlab';
    [cvBase, cvFx].forEach(c => c.setAttribute('aria-hidden', 'true'));
    cvLab.setAttribute('role', 'img');
    const tipEl = document.createElement('div'); tipEl.className = 'fttip';
    stage.append(cvBase, cvFx, cvLab, tipEl);
    host.append(bar, stage);
    const gB = cvBase.getContext('2d'), gF = cvFx.getContext('2d'), gL = cvLab.getContext('2d');

    const S = {
      host, bar, leg, mbtn, stage, cvBase, cvFx, cvLab, tipEl, gB, gF, gL,
      W: 0, H: 0, DPR: 1, pal: null, opts: {}, model: null,
      nodes: new Map(), links: new Map(), order: [], linkList: [],
      parts: [], pool: [], ripples: [], sprites: {},
      hover: null, raf: 0, lastT: 0, tween: null, twE: 1, alive: true,
      visible: true, motion: motionWanted(), first: true,
      meter: { frames: 0, cost: 0, maxBlur: 0, minFont: Infinity, ts: [], spawned: 0, hits: 0, rpMade: 0, rpPeak: 0 },
    };

    /* 設定發光：一律經過這裡，超過上限直接丟錯 */
    S.glow = (g, color, px) => {
      if (px > CFG.GLOW_MAX) throw new Error('flowtopo：shadowBlur ' + px + ' 超過上限');
      S.meter.maxBlur = Math.max(S.meter.maxBlur, px);
      g.shadowColor = color; g.shadowBlur = px * S.DPR;   // shadowBlur 不吃變換矩陣，乘 DPR 才等於 CSS px
    };
    S.font = (g, px, w) => {
      if (px < CFG.FONT_MIN) throw new Error('flowtopo：字級 ' + px + 'px 低於下限');
      S.meter.minFont = Math.min(S.meter.minFont, px);
      /* 設 ctx.font 每次都要解析整串 CSS 字型（Chrome 上不便宜）；經典版面一張圖約 300 段字，
         跟上一次一樣就不重設。畫布改尺寸會把狀態清掉，所以 sizeCanvases() 會把 __f 一起清掉。*/
      const f = `${w || 500} ${px}px ${FONT}`;
      if (g.__f !== f) { g.font = f; g.__f = f; }
    };

    mbtn.onclick = () => {
      if (reduceMQ.matches) return;
      lsSet(CFG.LS_MOTION, S.motion ? '0' : '1');
      setMotion(S, !S.motion);
    };
    const onMQ = () => setMotion(S, motionWanted());
    try { reduceMQ.addEventListener ? reduceMQ.addEventListener('change', onMQ) : reduceMQ.addListener(onMQ); } catch (e) { /* 舊瀏覽器 */ }
    S.onVis = () => {
      if (document.hidden) return stopLoop(S);
      if (S.pendingDraw && !farAway(S)) layoutAndDraw(S, false, true);
      startLoop(S);
    };
    document.addEventListener('visibilitychange', S.onVis);
    if (window.IntersectionObserver) {
      /* ★ 2026-09-25 效能（perf-2）：露出不到 10% 就當成看不見。
         資金流向頁側欄合併之後整頁變矮（2349px），捲到最底時這張圖只剩上緣 9px 在畫面裡，
         以前 isIntersecting 就算「看得見」，粒子照跑 —— 容器實測主執行緒 5 秒忙 4.5 秒（軟體繪圖的 drawImage），
         使用者看到的卻只是一條 9px 的邊。10% ≈ 56px，再往上捲一點就接著跑。*/
      S.io = new IntersectionObserver((es) => {
        S.visible = es.some(e => e.isIntersecting && e.intersectionRatio >= 0.1);
        if (S.visible) startLoop(S); else stopLoop(S);
      }, { threshold: [0, 0.1, 0.2] });
      S.io.observe(stage);
      /* 首次畫圖延後（見 layoutAndDraw 的 pendingDraw）：捲進畫面就當場畫 */
      S.pendIO = new IntersectionObserver((es) => {
        if (S.alive && S.pendingDraw && es.some(e => e.isIntersecting)) layoutAndDraw(S, false, true);
      });
      S.pendIO.observe(stage);
    }
    if (window.ResizeObserver) {
      S.ro = new ResizeObserver(() => {
        if (!S.alive) return;
        if (!host.isConnected || !stage.isConnected) return destroy(host);
        const w = stage.clientWidth;
        if (w > 0 && Math.abs(w - S.W) >= 1) { S.tween = null; layoutAndDraw(S, false); }
      });
      S.ro.observe(stage);
    }
    wirePointer(S);
    S.cleanupMQ = () => { try { reduceMQ.removeEventListener ? reduceMQ.removeEventListener('change', onMQ) : reduceMQ.removeListener(onMQ); } catch (e) { /* 忽略 */ } };
    host._ft = S;
    return S;
  }

  function destroy(host) {
    const S = host && host._ft; if (!S) return;
    S.alive = false;
    stopLoop(S);
    document.removeEventListener('visibilitychange', S.onVis);
    if (S.io) S.io.disconnect();
    if (S.pendIO) S.pendIO.disconnect();
    if (S.pendIdle && window.cancelIdleCallback) try { cancelIdleCallback(S.pendIdle); } catch (e) { /* 忽略 */ }
    if (S.ro) S.ro.disconnect();
    if (S.cleanupMQ) S.cleanupMQ();
    if (S.bar.parentNode === host) host.removeChild(S.bar);
    if (S.stage.parentNode === host) host.removeChild(S.stage);
    host.classList.remove('ftopo');
    host._ft = null;
  }

  function setMotion(S, on) {
    S.motion = !!on;
    paintMotionBtn(S);
    if (!S.drawn) return;                    // 還沒畫過（首次畫圖延後中）：等真的畫的時候自然照新設定畫
    if (S.motion) { prewarm(S, 3); startLoop(S); }
    else { stopLoop(S); drawStill(S); }
  }
  function paintMotionBtn(S) {
    const b = S.mbtn;
    if (reduceMQ.matches) {
      b.textContent = '動態 關（系統減少動態）'; b.disabled = true; b.setAttribute('aria-pressed', 'false');
      b.title = '你的系統設定了「減少動態效果」，這張圖只畫靜態';
      return;
    }
    b.disabled = false;
    b.textContent = S.motion ? '動態 開' : '動態 關';
    b.setAttribute('aria-pressed', S.motion ? 'true' : 'false');
    b.title = S.motion ? '關掉粒子流動畫（只畫靜態線條，設定會記住）' : '打開粒子流動畫（設定會記住）';
  }

  /* =========================================================================
     資料模型 → 節點／連線（app.js 給的是 ECharts tree 形狀的那棵樹）
     ========================================================================= */
  /* 產業鏈識別色：刻意**不用紅、不用綠**（那兩色在這個站只代表漲跌），也不用族群色盤
     （族群色盤淺色版有好幾個偏紅／偏綠）。一條鏈一個色相，底下的族群、成分股、粒子都同色，
     「錢從哪條河分出去」一眼看得出來。依鏈的 id 固定配色，即時換位時顏色不會跟著換。*/
  const CHAIN_HUE = {
    dark: { semiconductor: '#3ee0ff', ai_server: '#a594ff', electronics: '#ffb454', industry: '#9aa6c4' },
    light: { semiconductor: '#0a86b8', ai_server: '#6a58d6', electronics: '#b7741a', industry: '#6b778f' },
  };
  const CHAIN_MORE = { dark: ['#6aa7ff', '#d7a6ff', '#e6c86a', '#7fd4ff'], light: ['#2f6fd6', '#9152c9', '#94761c', '#1f7fa8'] };
  /* ★ 2026-09-26（第二版，Andy「參考圖顏色更鮮豔」＋黃金標準 docs/prototypes/flow_perfect_topology.html）：
     經典光纖改用飽和版產業鏈色。半導體 #22d3ee、AI 伺服器 #c084fc 取自參考稿；其餘三條鏈挑同亮度、彼此好分辨的飽和色
     （琥珀、石板、靛藍）。仍然**不用紅、不用綠** —— 參考稿把部分族群塗成紅／綠，但沒有一致規則
     （▼22% 是青、▼3% 是綠），站上規矩「紅綠只給漲跌字」照守。淺色主題用同色相的深一階（白底上讀得到）。*/
  const CHAIN_HUE_EL = {
    dark: { semiconductor: '#22d3ee', ai_server: '#c084fc', electronics: '#fbbf24', industry: '#94a3b8', traditional: '#818cf8' },
    light: { semiconductor: '#0891b2', ai_server: '#9333ea', electronics: '#d97706', industry: '#64748b', traditional: '#4f46e5' },
  };
  const ROOT_HUE_EL = { dark: '#38bdf8', light: '#0284c7' };
  function chainHue(S, cid) {
    const t = S.pal.dark ? 'dark' : 'light', m = S.classic ? CHAIN_HUE_EL[t] : CHAIN_HUE[t];
    if (m[cid]) return m[cid];
    const h = [...String(cid)].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 997, 7);
    return CHAIN_MORE[t][h % CHAIN_MORE[t].length];
  }

  function buildModel(S) {
    const M = S.model, o = S.opts, maxV = o.maxV || 1;
    const classic = S.classic = o.layout === 'classic' || o.layout === 'mini';
    S.mini = o.layout === 'mini';
    S.leafHover = classic && !S.mini && o.leafHover !== false;   // 經典光纖：代表股預設收起，滑過族群才顯示
    const ratio = (v) => Math.min(1, Math.max(0, (v || 0) / maxV));
    const seenN = new Set(), seenL = new Set();
    const order = [];
    const up = (key, patch) => {
      let n = S.nodes.get(key);
      if (!n) { n = { key, x: NaN, y: NaN, px: 0, pv: 0, flash: 0, last: -1e9, hf: 0, rpLast: -1e9 }; S.nodes.set(key, n); }
      n.pctFrom = n.pctShown;            // 百分比補間的起點＝畫面上現在顯示的那個數（補間中途換日也連續）
      Object.assign(n, patch); seenN.add(key); order.push(n); return n;
    };
    const link = (from, to, patch) => {
      const key = from.key + '>' + to.key;
      let e = S.links.get(key);
      if (!e) { e = { key, acc: Math.random() }; S.links.set(key, e); }
      Object.assign(e, { from, to }, patch); seenL.add(key); return e;
    };
    const rootHue = classic ? ROOT_HUE_EL[S.pal.dark ? 'dark' : 'light'] : S.pal.cyan;
    const root = up('root', { lv: 0, d: M, name: S.mini && M.name ? clean(M.name) : '台股成交值', hue: rootHue, dot: rootHue, rt: 1, r: 8, dim: false, parent: null });
    root.kids = [];
    let anyLeaves = false;
    /* ★ 2026-09-25 Andy：「拓撲版要跟經典版一樣絲滑」—— 換日期時依當天成交值重新排名，
       節點沿垂直方向滑到新位置（layout() 的補間），不再是「位置固定」。
       產業鏈依鏈的成交值排、族群在鏈內依成交值排；盤後／無資料／0 的一律墊底（它們不參與比較）。
       opts.rank === false 可以關掉（保留舊的固定順序）。Array.sort 是穩定排序，同值不會亂跳。*/
    const rankOn = o.rank !== false;
    const rk = (x) => (x.stale || x.nodata || !(x.value > 0)) ? -1 : x.value;
    const ranked = (arr) => rankOn ? arr.slice().sort((a, b) => rk(b) - rk(a)) : arr;
    ranked(M.children || []).forEach(cd => {
      const kids = ranked(cd.children || []);
      const hue = chainHue(S, cd.chain);
      const c = up('c:' + cd.chain, { lv: 1, d: cd, name: clean(cd.name), hue, dot: hue, rt: ratio((cd.value || 0) / 2),
        dim: !!(cd.itemStyle && cd.itemStyle.opacity < 1), stale: !!cd.stale, parent: root });
      c.kids = [];
      root.kids.push(c);
      // 每條鏈流量第一名的族群：名字粗體（沿用經典版 v2 第 5 批）
      const top = kids.filter(g => (g.value || 0) > 0 && !g.stale).sort((a, b) => b.value - a.value)[0];
      kids.forEach(gd => {
        const dot = hue;
        const g = up('g:' + gd.gid, { lv: 2, d: gd, name: clean(gd.name), hue, dot, rt: ratio(gd.value),
          dim: !!gd.dim, stale: !!gd.stale, nodata: !!gd.nodata, top: top === gd, parent: c,
          open: o.openGid != null && o.openGid === gd.gid,
          // 經典版面：這個族群佔幾個葉子槽位（含 app.js 補的看不見佔位，讓每天縱向空間一樣 —— 和經典版同一招）
          slots: Math.max(1, (gd.children || []).length) });
        g.kids = [];
        c.kids.push(g);
        if (g.open || (classic && !S.mini)) {
          (gd.children || []).forEach(xd => {
            if (xd.placeholder) return;
            const lf = up('l:' + gd.gid + ':' + (xd.code || ('rest' + (xd.restN || ''))), { lv: 3, d: xd,
              name: clean(xd.shown || xd.name), hue, dot: xd.restN ? S.pal.ink3 : dot, rt: ratio(xd.value),
              dim: !!xd.dim, stale: !!xd.stale, picked: !!xd.picked, rest: !!xd.restN, parent: g, kids: [] });
            g.kids.push(lf); anyLeaves = true;
          });
        }
      });
    });
    // 刪掉這一輪不存在的節點與連線（粒子跟著回收）
    for (const k of [...S.nodes.keys()]) if (!seenN.has(k)) S.nodes.delete(k);
    S.order = order;
    S.anyLeaves = anyLeaves;
    // 連線：寬度、顏色、流量（粒子密度／大小／速度都吃 rt）
    const list = [];
    root.kids.forEach(c => {
      list.push(link(root, c, { lv: 0, rt: c.rt, dead: c.dim || c.stale || !(c.d.value > 0) }));
      c.kids.forEach(g => {
        list.push(link(c, g, { lv: 1, rt: g.rt, dead: g.dim || g.stale || g.nodata || !(g.d.value > 0) }));
        g.kids.forEach(lf => list.push(link(g, lf, { lv: 2, rt: lf.rt, dashed: lf.picked || lf.rest,
          dead: lf.dim || lf.stale || !(lf.d.value > 0) })));
      });
    });
    for (const k of [...S.links.keys()]) if (!seenL.has(k)) S.links.delete(k);
    S.linkList = list;
    /* 2026-09-25 Andy：「粗細、快慢、明暗變化加強點，看不出差異」→ 三個維度一起拉開：
         · 線寬 1～13px（族群→個股那段上限 10px）
         · 速度 18～150px/秒（約 8 倍）、發車率 0.15～9.2 顆/秒
         · 明暗（不透明度係數）0.32～1：最小線壓到約三成亮，最大線全亮
       rt 是「佔最大值」，實測活著的線只落在 0.03～0.40，直接吃 rt 最大最小只差 2～3 倍。
       改成在活著的線之間，用平方根尺度做 0～1 正規化（最小那條＝0、最大那條＝1）。*/
    const live = list.filter(e => !e.dead && e.rt > 0).map(e => Math.sqrt(e.rt));
    const sLo = live.length ? Math.min(...live) : 0, sHi = live.length ? Math.max(...live) : 1;
    list.forEach(e => {
      const r = e.rt;
      const q = sHi > sLo ? Math.min(1, Math.max(0, (Math.sqrt(r) - sLo) / (sHi - sLo))) : 1;
      e.w = e.dead ? 0.8 : 1 + (e.lv === 2 ? 9 : 12) * q;
      e.al = e.dead ? 0.35 : 0.32 + 0.68 * q;
      e.pr = 1.1 + 2.0 * q;                              // 粒子半徑 1.1～3.1px
      e.rate = 0.15 + 9 * Math.pow(q, 1.6);              // 每秒發幾顆（錢多 → 密）
      e.spdK = q;                                        // 速度係數 0～1（錢多 → 快）
      /* ★ 2026-09-26 經典光纖（黃金標準）：粒子半徑照層級固定 —— 主幹 2.2／族群 1.7／毛細（代表股）1.3。
         「錢多 → 大」這個維度改由速度、密度、外光暈寬度與亮度承擔（那三個照舊依金額拉開）。*/
      if (classic) e.pr = e.lv === 0 ? 2.2 : e.lv === 1 ? 1.7 : 1.3;
      /* ★ 2026-09-26（第二版）weight 改用黃金標準的尺度：參考稿主幹 3.6～3.8、族群 1.3、毛細 0.8 →
         這裡依金額平方根 0.8～3.8（最粗／最細 4.75 倍）。改前 1～13px：外暈 ×2.4 之後最粗那條是 31px 寬的一片霧，
         和參考圖（主幹外暈約 9px）差最多的就是這裡。粗細對比仍在（外暈寬 1.9～9.1px、粒子密度與速度照舊依金額）。*/
      if (classic) e.w = e.dead ? 0.8 : 0.8 + 3.0 * q;
    });
    // 回收已經不在的連線上的粒子
    for (let i = S.parts.length - 1; i >= 0; i--) {
      const p = S.parts[i];
      if (!S.links.has(p.e.key) || p.e.dead) { S.parts[i] = S.parts[S.parts.length - 1]; S.parts.pop(); S.pool.push(p); }
    }
    S.root = root;
  }

  /* 版面：四欄（有展開的族群才有第四欄）。族群等距槽位、產業鏈之間空 0.7 列、
     成分股以族群為中心往上下排開（夾在畫布內）。回傳這一輪要的畫布高度。*/
  function wantHeight(S) {
    if (S.mini) {
      const nG = S.root.kids.reduce((a, c) => a + c.kids.length, 0);
      return Math.round(S.opts.height || Math.max(300, nG * CFG.MINI_SLOT + 46));
    }
    if (S.classic) return slotPlan(S).H;
    const chains = S.root.kids, nG = chains.reduce((a, c) => a + c.kids.length, 0);
    const slots = nG + 0.7 * Math.max(0, chains.length - 1);
    let h = Math.round(slots * CFG.ROW + 30);
    const nL = S.order.filter(n => n.lv === 3).length;
    if (nL) h = Math.max(h, nL * CFG.LEAF_ROW + 30);
    return Math.max(CFG.H_MIN, Math.min(CFG.H_MAX, h));
  }
  /* ★ 2026-09-26（第二版）經典光纖的槽位規劃（Andy 第 3 點：「二級族群用等距垂直槽位」）：
     族群一個一個排進等高的垂直槽位，slot ＝ 參考稿的 Math.min(42, (h − 60) / n) 同一個邏輯 ——
     這裡的畫布高度是跟著內容長的，所以反過來算：以最高 1040px 為可用高度求 slot，夾在 36～42。
     同一條產業鏈的族群連續排（線平行滑入、不交錯），鏈與鏈之間空半格。
     點開的族群（展開全部成分股）那一格長高到放得下全部成分股（每檔 13px），其餘照舊。
     slot 下限 36：代表股三檔一欄每檔 13px（字 12px，專案字級下限），36 以下相鄰族群的代表股會疊字。*/
  function slotPlan(S) {
    const chains = S.root.kids, n = chains.reduce((a, c) => a + c.kids.length, 0) || 1;
    const gaps = 0.5 * Math.max(0, chains.length - 1);
    let extra = 0;
    chains.forEach(c => c.kids.forEach(g => { if (g.open) extra += Math.max(0, g.kids.length * CFG.EL_LEAF_SP + 16 - CFG.EL_SLOT_MAX); }));
    const slot = Math.max(CFG.EL_SLOT_MIN, Math.min(CFG.EL_SLOT_MAX, (CFG.CL_H_MAX - CFG.EL_PAD * 2 - extra) / (n + gaps)));
    const body = slot * (n + gaps) + chains.reduce((a, c) => a + c.kids.reduce((b, g) => b + (g.open ? Math.max(0, g.kids.length * CFG.EL_LEAF_SP + 16 - slot) : 0), 0), 0);
    const H = Math.max(CFG.CL_H_MIN, Math.round(body + CFG.EL_PAD * 2));
    return { slot, body, H };
  }
  /* 經典光纖的欄位（黃金標準）：根節點貼左、產業鏈 26%、族群 54%、代表股固定在寬度 83%。
     父節點（根、產業鏈）在它第一個與最後一個子節點的正中間（樹狀結構）。*/
  function layoutClassic(S) {
    const W = S.W, H = S.H, root = S.root, chains = root.kids;
    let cols = [CFG.CL_LEFT + 8, W * 0.26, W * 0.54, W * 0.83];
    if (S.leafHover) {
      /* 代表股預設收起：右邊那欄的寬度讓給版面 —— 族群欄往右移（54% → 最多 66%），但要留得下
         「族群膠囊 ＋ 16px 空隙 ＋ 代表股（小點＋最長的「名稱 佔比%」）」，滑過顯示時才不會蓋到任何族群膠囊。
         代表股欄＝max(83%, 族群膠囊最右緣 ＋ 16)；產業鏈欄放在根與族群的 44% 處。*/
      let maxG = 0, maxL = 0;
      chains.forEach(c => c.kids.forEach(g => {
        maxG = Math.max(maxG, elBadgeW(S, g));
        g.kids.forEach(lf => { maxL = Math.max(maxL, Math.min(CFG.CL_LEAF_LABEL_W, elBadgeW(S, lf) - 12)); });
      }));
      const need = 6 + 6 + maxG + 16 + 6 + maxL + 4;       // 族群圓點右半＋膠囊＋空隙＋代表股小點到字＋字＋右緣
      const gX = Math.max(W * 0.54, Math.min(W * 0.66, W - need));
      const lX = Math.min(W - 4 - maxL - 6, Math.max(W * 0.83, gX + 6 + 6 + maxG + 16));
      cols = [CFG.CL_LEFT + 8, CFG.CL_LEFT + 8 + (gX - CFG.CL_LEFT - 8) * 0.44, gX, lX];
    }
    const plan = slotPlan(S), slot = plan.slot;
    S.step = slot; S.slot = slot;
    let y = Math.max(CFG.EL_PAD, (H - plan.body) / 2);   // 內容比最低高度矮時垂直置中
    chains.forEach((c, ci) => {
      if (ci) y += slot * 0.5;
      c.kids.forEach(g => {
        const nL = g.kids.length;
        const gs = g.open ? Math.max(slot, nL * CFG.EL_LEAF_SP + 16) : slot;
        g.tx = cols[2]; g.ty = y + gs / 2; y += gs; g.gs = gs;
        // 族群圓點 4.5～6（依佔比平方根）；盤後／無資料 4.5
        g.r = g.stale || g.nodata ? 4.5 : 4.5 + 1.5 * Math.sqrt(g.rt);
        /* 代表股：固定 X（寬度 83%）垂直排開，以族群的 y 為中心。
           間距：黃金標準 9px 是給 10px 字的；這裡字是 12px（專案下限），改 13px；slot 放不下三檔時用 slot 等分（不小於 12）。*/
        const sp = g.open ? CFG.EL_LEAF_SP : Math.max(12, Math.min(CFG.EL_LEAF_SP, (gs - 4) / Math.max(1, nL)));
        g.kids.forEach((lf, i) => {
          lf.tx = cols[3]; lf.ty = g.ty + (i - (nL - 1) / 2) * sp;
          lf.r = CFG.EL_LEAF_R;
        });
        g.leafSp = sp;
      });
      c.tx = cols[1];
      c.ty = c.kids.length ? (c.kids[0].ty + c.kids[c.kids.length - 1].ty) / 2 : H / 2;
      // 產業鏈圓點 6～7.5（依佔比平方根）
      c.r = c.stale ? 6 : 6 + 1.5 * Math.sqrt(c.rt);
      c.hh = 0; c.cw = 0;
    });
    root.tx = cols[0];
    root.ty = chains.length ? (chains[0].ty + chains[chains.length - 1].ty) / 2 : H / 2;
    root.r = 7.5;
    S.cols = cols;
    return cols;
  }

  /* 緊湊版（總覽）：先量「根／產業鏈／族群」三種膠囊最長的寬度，再決定欄位。總覽右欄的寬度差很多 ——
     側欄收起的 1440～1920 約 450px、1024／900 單欄 450～650px，但**側欄打開**時 1440 只有 294px、1280 只有 241px
     （預設是打開的），所以分兩種排法：
       · 寬（≥ 420px）：族群欄往右靠（最長的族群膠囊剛好收在右緣內），產業鏈膠囊在節點右邊、右緣離族群圓點 ≥ 10px。
       · 窄（< 420px）：產業鏈膠囊改放在節點**正下方**、左右置中（夾在畫布左緣與族群圓點之間），
         寬度先給產業鏈膠囊、剩下給族群（至少 104px）；鏈與鏈之間拉開 12～18px（下方膠囊才不會壓到下一條鏈的圓點），
         族群一格縮成 20px 補回高度 —— 總高度仍是呼叫端給的那個數（不比改前高）。
       兩種都放不下時只截**名稱**（% 永遠完整，全名在提示框）。
     根：貼左，標籤在圓點正上方（右邊整片是分流線）。*/
  function elBadgeW(S, n) {
    const g = S.gL; let w = 12;
    partsOf(S, n).forEach(p => { S.font(g, 12, 600); w += mw(g, p.t.replace(/^\n/, '')); });
    return w;
  }
  function layoutMini(S) {
    const W = S.W, H = S.H, root = S.root, chains = root.kids;
    let maxG = 0, maxC = 0;
    chains.forEach(c => { maxC = Math.max(maxC, elBadgeW(S, c)); c.kids.forEach(g => { maxG = Math.max(maxG, elBadgeW(S, g)); }); });
    const rootX = 12, gR = 6, narrow = S.miniNarrow = W < 420;
    let gX, cX;
    if (!narrow) {
      gX = Math.max(W * 0.5, W - 4 - Math.min(maxG, W * 0.5) - 6 - gR);
      const cMax = gX - gR - 10 - Math.min(maxC, W * 0.3) - 6 - 7;
      cX = Math.max(rootX + 60, Math.min(cMax, W * 0.36));
    } else {
      /* 寬度先給產業鏈膠囊（只有 5 條、名字短），剩下的給族群；族群至少 104px（和舊版 ECharts 窄版同一個下限）。
         241px（1280＋側欄）時兩邊都放不下，只截名稱 */
      const gLab = Math.max(Math.min(104, maxG), Math.min(maxG, W - 28 - maxC));
      gX = W - 4 - gLab - 6 - gR;
      cX = rootX + Math.max(38, (gX - rootX) * 0.42);
      S.miniCR = gX - gR - 4;                           // 產業鏈膠囊（在節點下方）的右界
    }
    const cols = [rootX, cX, gX, W + 6];                 // 第四欄（代表股）不存在：放在畫布外，量標籤時右界＝畫布右緣
    const n = chains.reduce((a, c) => a + c.kids.length, 0) || 1, nc = chains.length;
    let slot, gap, y;
    if (!narrow) {
      slot = CFG.MINI_SLOT;
      gap = nc > 1 ? Math.min(CFG.MINI_GAP, 24 / (nc - 1)) : 0;
      y = Math.max(4, (H - n * slot - gap * Math.max(0, nc - 1)) / 2);
    } else {
      /* 族群一格 19～20px：先保證鏈與鏈之間空得出 16px（下方膠囊 r＋3＋17 ≈ 27px，加上下一條鏈的圓點才放得下），
         剩下的才給族群那一格。18 個族群、5 條鏈、高 442 時算出來約 19.3px（膠囊 17px，上下仍各留 1px 以上）*/
      const top = 4, bot = 26;
      slot = Math.max(19, Math.min(20, (H - top - bot - 16 * Math.max(0, nc - 1)) / n));
      const avail = H - top - bot - n * slot;
      gap = nc > 1 ? Math.max(0, Math.min(18, avail / (nc - 1))) : 0;
      y = top + Math.max(0, (avail - gap * Math.max(0, nc - 1)) / 2);
    }
    S.step = slot; S.slot = slot;
    chains.forEach((c, ci) => {
      if (ci) y += gap;
      c.kids.forEach(g => {
        g.tx = cols[2]; g.ty = y + slot / 2; y += slot;
        g.r = g.stale || g.nodata ? 4.5 : 4.5 + 1.5 * Math.sqrt(g.rt);
      });
      c.tx = cols[1];
      c.ty = c.kids.length ? (c.kids[0].ty + c.kids[c.kids.length - 1].ty) / 2 : H / 2;
      c.r = c.stale ? 5.5 : 5.5 + 1.5 * Math.sqrt(c.rt);
      c.hh = 0; c.cw = 0;
    });
    root.tx = cols[0];
    root.ty = chains.length ? (chains[0].ty + chains[chains.length - 1].ty) / 2 : H / 2;
    root.r = 6;
    S.cols = cols;
    return cols;
  }

  function layout(S) {
    const W = S.W, H = S.H, root = S.root, chains = root.kids;
    const padT = 16, padB = 14;
    const cols = S.mini ? layoutMini(S) : S.classic ? layoutClassic(S) : layoutTopo(S, W, H, root, chains, padT, padB);
    placeTween(S);
    S.cols = cols;
  }
  function layoutTopo(S, W, H, root, chains, padT, padB) {
    const cols = S.anyLeaves ? [26, W * 0.21, W * 0.47, W * 0.75] : [26, W * 0.29, W * 0.64, W];
    const nG = chains.reduce((a, c) => a + c.kids.length, 0);
    const slots = nG + 0.7 * Math.max(0, chains.length - 1);
    const step = (H - padT - padB) / Math.max(1, slots);
    S.step = step;
    let k = 0;
    chains.forEach((c, i) => {
      if (i > 0) k += 0.7;
      c.kids.forEach(g => {
        g.tx = cols[2]; g.ty = padT + (k + 0.5) * step; k += 1;
        g.r = g.stale || g.nodata ? 3 : 3.4 + 4.4 * Math.sqrt(g.rt);
      });
      c.tx = cols[1];
      c.ty = c.kids.length ? (c.kids[0].ty + c.kids[c.kids.length - 1].ty) / 2 : padT + k * step;
    });
    root.tx = cols[0];
    root.ty = chains.length ? (chains[0].ty + chains[chains.length - 1].ty) / 2 : H / 2;
    root.r = 8;
    // 產業鏈節點：直立膠囊，高度＝從它出發的線寬加總（一條河分成幾支）
    chains.forEach(c => {
      const outs = S.linkList.filter(e => e.from === c);
      const span = outs.reduce((a, e) => a + e.w, 0) + 1.6 * Math.max(0, outs.length - 1);
      c.hh = Math.max(6, Math.min(step * 1.6, span / 2 + 2));
      c.r = 3.2; c.cw = 6;
    });
    // 成分股
    chains.forEach(c => c.kids.forEach(g => {
      const n = g.kids.length; if (!n) return;
      const ls = Math.max(CFG.LEAF_ROW, Math.min(24, (H - padT - padB) / n));
      let y0 = g.ty - (n - 1) * ls / 2;
      y0 = Math.max(padT + ls / 2 - 4, Math.min(y0, H - padB - (n - 1) * ls - ls / 2 + 4));
      g.kids.forEach((lf, i) => {
        lf.tx = cols[3]; lf.ty = y0 + i * ls;
        lf.r = lf.stale ? 2.4 : 2.6 + 2.6 * Math.sqrt(lf.rt);
      });
    }));
    return cols;
  }
  function placeTween(S) {
    // 第一次、或動畫關著：直接就位；否則補間（換位、展開、收回都看得到「誰去了哪裡」）
    const moving = S.order.some(n => isFinite(n.x) && (Math.abs(n.x - n.tx) > 0.5 || Math.abs(n.y - n.ty) > 0.5));
    S.order.forEach(n => {
      if (!isFinite(n.x)) {                  // 新長出來的節點：從它的上一層長出來
        const p = n.parent && isFinite(n.parent.x) ? n.parent : null;
        n.x = p ? p.x : n.tx; n.y = p ? p.y : n.ty;
        if (!p) { n.x = n.tx; n.y = n.ty; }
      }
      n.sx = n.x; n.sy = n.y;
    });
    const canTween = S.motion && !S.first && (moving || S.order.some(n => n.sx !== n.tx || n.sy !== n.ty));
    /* 回放連續換日：用等速（linear）而且時長＝一格的間隔，前一段剛走完下一段就接上，
       不會每天「到站停一下再出發」；單次換日（拉Bar、＋／−）用 cubicInOut。*/
    const playing = !!(S.opts.playing && S.opts.playing());
    if (canTween) {
      S.tween = { t0: performance.now(), dur: playing ? (S.opts.playFrame || 650) : (S.tweenMs || CFG.TWEEN_MS), lin: playing };
      S.twE = 0;
    } else { S.tween = null; S.twE = 1; S.order.forEach(n => { n.x = n.tx; n.y = n.ty; }); }
  }

  /* 從一個節點出去的多條線，起點在節點的直徑（或膠囊高度）內依目標 y 排開 →
     平行滑出、不交叉；進入端一律打在節點中心 */
  function ports(S) {
    if (S.classic) { S.linkList.forEach(e => { e.y0 = 0; }); return; }   // 經典光纖：一律從父節點圓心那一列出發（不在直條上排開）
    const byFrom = new Map();
    S.linkList.forEach(e => { if (!byFrom.has(e.from)) byFrom.set(e.from, []); byFrom.get(e.from).push(e); });
    byFrom.forEach((list, from) => {
      list.sort((a, b) => a.to.y - b.to.y);
      const total = list.reduce((a, e) => a + e.w, 0) + 1.6 * Math.max(0, list.length - 1);
      const cap = from.lv === 1 ? from.hh * 2 - 3 : from.lv === 0 ? from.r * 1.5 : Math.max(2, from.r * 1.4);
      const k = total > cap ? cap / total : 1;
      let y = -Math.min(total, cap) / 2;
      list.forEach(e => { e.y0 = (y + e.w * k / 2); y += (e.w + 1.6) * k; });
    });
  }

  /* 受控三次貝茲 S 曲線 ＋ 等弧長查表（粒子沿弧長等速走，彎道不會忽快忽慢；法向量給管內散開用）*/
  function buildCurve(e, classic) {
    const a = e.from, b = e.to;
    let P;
    if (classic) {
      /* ★ 2026-09-26 經典光纖：平滑水平切線三次貝茲。起點在父節點圓心右側 0.4r（圓點畫在上層會蓋住），
         終點在子節點左緣 0.6r；第二版控制點 CP1＝(x0＋dx×0.45, y0)、CP2＝(x1−dx×0.45, y1)（Andy 黃金標準，對稱張力）。*/
      const x0 = a.x + a.r * 0.4, y0 = a.y + (e.y0 || 0), x1 = b.x - b.r * 0.6, y1 = b.y, dx = x1 - x0;
      P = e.p = [x0, y0, x0 + dx * CFG.CL_CP1, y0, x0 + dx * CFG.CL_CP2, y1, x1, y1];
    } else {
      const x0 = a.x + (a.lv === 1 ? 3 : a.r * 0.4), y0 = a.y + (e.y0 || 0), x1 = b.x - (b.lv === 1 ? 3 : b.r * 0.6), y1 = b.y;
      const dx = x1 - x0;
      P = e.p = [x0, y0, x0 + dx * CFG.CURVE_K, y0, x1 - dx * CFG.CURVE_K, y1, x1, y1];
    }
    const N = 64, M = 64;
    const rx = new Float32Array(N + 1), ry = new Float32Array(N + 1), cum = new Float32Array(N + 1);
    for (let i = 0; i <= N; i++) {
      const t = i / N, u = 1 - t, A = u * u * u, B = 3 * u * u * t, C = 3 * u * t * t, D = t * t * t;
      rx[i] = A * P[0] + B * P[2] + C * P[4] + D * P[6]; ry[i] = A * P[1] + B * P[3] + C * P[5] + D * P[7];
      if (i) cum[i] = cum[i - 1] + Math.hypot(rx[i] - rx[i - 1], ry[i] - ry[i - 1]);
    }
    const L = cum[N] || 1;
    const xs = e.xs && e.xs.length === M + 1 ? e.xs : new Float32Array(M + 1);
    const ys = e.ys && e.ys.length === M + 1 ? e.ys : new Float32Array(M + 1);
    const nx = e.nx && e.nx.length === M + 1 ? e.nx : new Float32Array(M + 1);
    const ny = e.ny && e.ny.length === M + 1 ? e.ny : new Float32Array(M + 1);
    let j = 0;
    for (let i = 0; i <= M; i++) {
      const s = L * i / M;
      while (j < N - 1 && cum[j + 1] < s) j++;
      const f = (s - cum[j]) / ((cum[j + 1] - cum[j]) || 1);
      xs[i] = rx[j] + (rx[j + 1] - rx[j]) * f; ys[i] = ry[j] + (ry[j + 1] - ry[j]) * f;
    }
    for (let i = 0; i <= M; i++) {
      const p0 = Math.max(0, i - 1), p1 = Math.min(M, i + 1), tx = xs[p1] - xs[p0], ty = ys[p1] - ys[p0], l = Math.hypot(tx, ty) || 1;
      nx[i] = -ty / l; ny[i] = tx / l;
    }
    Object.assign(e, { L, M, xs, ys, nx, ny });
  }
  function curves(S) { ports(S); S.linkList.forEach(e => buildCurve(e, S.classic)); }


  /* 發光粒子小圖：shadowBlur 只在這裡用一次，每幀只 drawImage（不在迴圈裡設 shadowBlur）*/
  function sprite(S, color) {
    const R = 2.4, pad = S.pal.glow * 2 + 2, size = Math.ceil((R + pad) * 2);
    const c = document.createElement('canvas'); c.width = c.height = Math.ceil(size * S.DPR);
    const g = c.getContext('2d');
    S.glow(g, color, S.pal.glow);
    g.fillStyle = S.pal.dark ? mixW(color, 0.78) : color;
    g.beginPath(); g.arc(c.width / 2, c.height / 2, R * S.DPR, 0, Math.PI * 2); g.fill();
    return { c, size, R };
  }
  /* ★ 2026-09-26（第二版，黃金標準）經典光纖的粒子：白色實心核心＋線色光暈 ≤ 5px（淺色 4px），
     不再外加一大圈放射漸層（第一版的 3.4 倍光暈就是 Andy 說的「濁」的來源之一）。
     shadowBlur 只在畫這張小圖時用一次，每幀只 drawImage。
     淺色主題：白核心在淺底上會變成一個洞 —— 核心改成加深的同色、外面一圈細白邊。*/
  function spriteEl(S, color) {
    const R = 2.4, pad = S.pal.glow * 2 + 2, size = Math.ceil((R + pad) * 2);
    const c = document.createElement('canvas'); c.width = c.height = Math.ceil(size * S.DPR);
    const g = c.getContext('2d'), m = c.width / 2, k = S.DPR;
    S.glow(g, color, S.pal.glow);
    g.beginPath(); g.arc(m, m, R * k, 0, Math.PI * 2);
    if (S.pal.dark) { g.fillStyle = '#ffffff'; g.fill(); }
    else {
      const [r, gg, b] = rgbOf(color);
      g.fillStyle = `rgb(${Math.round(r * 0.72)},${Math.round(gg * 0.72)},${Math.round(b * 0.72)})`; g.fill();
      g.shadowBlur = 0; g.strokeStyle = 'rgba(255,255,255,.9)'; g.lineWidth = 0.8 * k; g.stroke();
    }
    return { c, size, R };
  }
  /* 節點光暈小圖：放射漸層（不用 shadowBlur）。節點的常駐 6px 微光、碰撞時的外光環都用它放大畫。*/
  function haloEl(S, color) {
    const H = 32, c = document.createElement('canvas'); c.width = c.height = Math.ceil(H * 2 * S.DPR);
    const g = c.getContext('2d'), m = c.width / 2;
    const gr = g.createRadialGradient(m, m, 0, m, m, m);
    gr.addColorStop(0, rgba(color, 1)); gr.addColorStop(0.55, rgba(color, 0.5)); gr.addColorStop(1, rgba(color, 0));
    g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
    return { c };
  }
  function sprites(S) {
    S.sprites = {}; S.halos = {};
    S.order.forEach(n => {
      if (S.sprites[n.hue]) return;
      S.sprites[n.hue] = S.classic ? spriteEl(S, n.hue) : sprite(S, n.hue);
      if (S.classic) S.halos[n.hue] = haloEl(S, n.hue);
    });
  }

  /* 關聯（滑過一個節點：它的祖先＋子孫全亮，其餘壓暗）*/
  function related(S, n) {
    if (!S.hover) return true;
    const h = S.hover;
    for (let p = n; p; p = p.parent) if (p === h) return true;       // n 是 h 的子孫（或自己）
    for (let p = h; p; p = p.parent) if (p === n) return true;       // n 是 h 的祖先
    return false;
  }
  const fadeOf = (S, n) => (n.dim ? 0.2 : 1) * (related(S, n) ? 1 : 0.22);

  /* ---- 靜態層：光纖（外層微光管＋內核實心線）---- */
  function drawBase(S) {
    if (S.classic) return drawBaseEl(S);
    const g = S.gB, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    g.lineCap = 'round';
    S.linkList.forEach(e => {
      const p = e.p; if (!p) return;
      const k = Math.min(fadeOf(S, e.from), fadeOf(S, e.to));
      const col = e.dead && !e.to.dim ? P.ink3 : e.hue || e.to.hue;
      g.beginPath(); g.moveTo(p[0], p[1]); g.bezierCurveTo(p[2], p[3], p[4], p[5], p[6], p[7]);
      g.setLineDash(e.dashed ? [4, 3] : []);
      if (!e.dead) {
        g.strokeStyle = rgba(col, (P.dark ? 0.12 : 0.14) * e.al * k);
        g.lineWidth = e.w + 5; g.stroke();                               // 微光外管（只比內核寬 5px，不做大面積泛光）
      }
      g.strokeStyle = rgba(col, (e.dead ? 0.35 : (P.dark ? 0.9 : 0.72) * e.al) * k);
      g.lineWidth = e.w; g.stroke();                                     // 內核實心線（寬度＝e.w，探針量的就是這個）
    });
    g.setLineDash([]);
  }

  /* ★ 2026-09-26（第二版）經典光纖的底圖 —— Andy 第 1 點「去霧」，數字照黃金標準：
       · 外層光暈：寬 weight×2.4（第一版 ×3.2）、alpha 0.09（第一版 0.08 但疊在 3.2 倍寬上，分支匯聚處糊成一片）
       · 內芯：**固定 1.1px、alpha 0.65**（第一版 w×0.9、alpha 0.32 → 粗而暗，就是「濁」）
       · 毛細線（族群 → 代表股）：內芯 0.7px、alpha 0.2，外暈 alpha 0.04
     「錢多 → 粗」這個維度留在外層光暈的寬度（weight 仍是依金額平方根 1～13px）；
     「錢多 → 亮」留在外層光暈的透明度（× 0.55＋0.45×e.al，最大那條＝0.09）與粒子亮度。
     每條線實際用的寬度與透明度記在 e.inW／e.inA／e.outW／e.outA，探針直接讀（驗收量的是畫出去的值）。*/
  const trailEq = (a) => a / (1 - (1 - a) * (1 - CFG.EL_TRAIL));   // 規格的每幀透明度 → 殘影穩態下看起來的透明度
  function drawBaseEl(S) {
    const g = S.gB, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    g.lineCap = 'round';
    const pass = (fn) => S.linkList.forEach(e => {
      const p = e.p; if (!p) return;
      const lvis = e.lv === 2 ? visOf(S, e.to) : 1;         // 代表股收起：毛細線跟著淡出
      if (lvis < 0.01) {                                   // 收起的毛細線不畫，但規格值照樣記（探針讀的是「顯示時會用的」寬度與透明度）
        e.inW = e.dead ? 0.8 : 0.7; e.inA = e.dead ? 0.35 : 0.2;
        e.outW = e.dead ? 0 : e.w * 2.4; e.outA = e.dead ? 0 : 0.04 * (0.55 + 0.45 * e.al);
        e.inAEff = e.dead ? e.inA : trailEq(e.inA); e.outAEff = e.dead ? 0 : trailEq(e.outA);
        return;
      }
      const k = Math.min(fadeOf(S, e.from), fadeOf(S, e.to)) * lvis;
      const col = e.dead && !e.to.dim ? P.ink3 : e.hue || e.to.hue;
      g.beginPath(); g.moveTo(p[0], p[1]); g.bezierCurveTo(p[2], p[3], p[4], p[5], p[6], p[7]);
      fn(e, k, col, e.lv === 2);
    });
    // 先畫全部外層，再畫全部內芯 —— 後畫的外暈不會蓋在先畫的芯上
    g.setLineDash([]);
    pass((e, k, col, cap) => {
      e.outW = e.dead ? 0 : e.w * 2.4;
      e.outA = e.dead ? 0 : (cap ? 0.04 : 0.09) * (0.55 + 0.45 * e.al);
      e.outAEff = e.dead ? 0 : trailEq(e.outA);
      if (e.dead) return;
      g.strokeStyle = rgba(col, e.outAEff * k); g.lineWidth = e.outW; g.stroke();
    });
    pass((e, k, col, cap) => {
      e.inW = e.dead ? 0.8 : cap ? 0.7 : 1.1;
      e.inA = e.dead ? 0.35 : cap ? 0.2 : 0.65;
      e.inAEff = e.dead ? e.inA : trailEq(e.inA);
      g.setLineDash(e.dashed ? [4, 3] : []);
      g.strokeStyle = rgba(col, e.inAEff * k);
      g.lineWidth = e.inW; g.stroke();
    });
    g.setLineDash([]);
  }

  /* ---- 標籤層：節點右側的行內膠囊（名稱　% 佔上一層　▲▼比前一天）---- */
  function partsOf(S, n) {
    const d = n.d, P = S.pal, out = [];
    // 經典版面的代表股整串用 --ink-3（經典版 leaves.label.color）；拓撲版膠囊裡用 --ink-2
    const nameCol = n.lv === 1 ? P.ink : n.lv === 2 ? (n.top ? P.ink : P.ink2) : (S.classic ? P.ink3 : P.ink2);
    const nameW = n.lv === 1 || (n.lv === 2 && n.top) ? 700 : n.lv === 0 ? 700 : 500;
    const nameFs = n.lv === 1 || n.lv === 0 ? 13 : 12;
    if (n.lv === 0) {
      (S.opts.rootLines || ['台股成交值']).forEach((t, i) => out.push({ t: (i ? '\n' : '') + t, c: i ? P.ink3 : P.ink, w: i ? 500 : 700, fs: i ? 12 : 13, name: !i }));
      return out;
    }
    out.push({ t: (n.lv === 2 && n.open && !n.stale ? '▾ ' : '') + (n.rest ? `其餘 ${d.restN} 檔` : n.name), c: nameCol, w: nameW, fs: nameFs, name: true });
    if (n.stale) { out.push({ t: ' 盤後', c: P.ink3, w: 500, fs: 12 }); return out; }
    if (n.nodata) { out.push({ t: ' 無資料', c: P.ink3, w: 500, fs: 12 }); return out; }
    const v = d.value || 0;
    const base = d.base != null ? d.base : (d.share != null && d.share > 0 ? v / d.share : null);
    if (base) {
      // 百分比跟著位置一起補間（S.twE＝補間進度 0～1；沒有補間時就是 1）
      const pNow = v / base * 100, pFrom = n.pctFrom;
      const shown = pFrom != null && isFinite(pFrom) && S.twE < 1 ? pFrom + (pNow - pFrom) * S.twE : pNow;
      n.pctShown = shown;
      out.push({ t: ' ' + fmtN(shown, 1) + '%', c: P.ink3, w: 500, fs: 12 });
    } else n.pctShown = null;
    if (n.lv <= 2 && d.prev != null && d.prev > 0 && v != null) {
      const ch = (v - d.prev) / d.prev * 100;
      if (isFinite(ch)) {
        const key = ch > 1 ? 'up' : ch < -1 ? 'dn' : 'fl';
        out.push({ t: ' ' + (key === 'up' ? '▲' : key === 'dn' ? '▼' : '＝') + fmtN(Math.abs(ch), 0) + '%',
          c: key === 'up' ? P.up : key === 'dn' ? P.down : P.ink3, w: 600, fs: 12, chg: key });
      }
    }
    return out;
  }
  /* 量字寬快取：補間時每幀都要重排標籤（百分比跟著補間），經典版面一張圖約 100 個標籤 ——
     同一個字串＋字型量過就不再量（上限 4000 筆，滿了整包清掉）。*/
  const _mw = new Map();
  function mw(g, t) {
    const key = (g.__f || g.font) + '|' + t;
    let v = _mw.get(key);
    if (v == null) { v = g.measureText(t).width; if (_mw.size > 4000) _mw.clear(); _mw.set(key, v); }
    return v;
  }
  function measureLabels(S) {
    if (S.classic) return measureLabelsClassic(S);
    const g = S.gL, W = S.W, cols = S.cols;
    S.order.forEach(n => {
      const parts = partsOf(S, n).map(p => ({ ...p }));
      const lines = [[]];
      parts.forEach(p => { if (p.t[0] === '\n') { lines.push([]); p.t = p.t.slice(1); } lines[lines.length - 1].push(p); });
      // 右邊界：下一欄的節點左邊 10px；最後一欄貼畫布右緣
      const nextX = n.lv === 0 ? cols[1] - 12 : n.lv === 1 ? cols[2] - 14
        : n.lv === 2 ? (S.anyLeaves ? cols[3] - 14 : W - 4) : W - 4;
      const x = n.lv === 0 ? Math.max(4, n.tx - n.r) : n.tx + (n.lv === 1 ? 7 : n.r + 6);
      const maxW = Math.max(40, nextX - x);
      let bw = 0;
      lines.forEach(line => {
        line.forEach(p => { S.font(g, p.fs, p.w); p.pw = mw(g, p.t); });
        let lw = line.reduce((a, p) => a + p.pw, 0) + 12;
        const nm = line.find(p => p.name);
        if (lw > maxW && nm) {            // 放不下：只截名稱，數字永遠完整（全名在提示框）
          const cs = Array.from(nm.t);
          S.font(g, nm.fs, nm.w);
          for (let k = cs.length - 1; k >= 1 && lw > maxW; k--) {
            nm.t = cs.slice(0, k).join('') + '…';
            const w2 = mw(g, nm.t); lw = lw - nm.pw + w2; nm.pw = w2;
          }
        }
        line.w = lw; bw = Math.max(bw, lw);
      });
      const bh = CFG.BADGE_H + (lines.length - 1) * 15;
      // 根節點：膠囊放在節點正上方（右邊是整片分流線）
      const y = n.lv === 0 ? n.ty - n.r - 8 - bh : n.ty - bh / 2;
      n.lab = { lines, x, y, w: bw, h: bh };
    });
  }
  /* ★ 2026-09-26（第二版）經典光纖的標籤 —— Andy 第 2 點，照黃金標準：
       · 根、產業鏈、族群：節點右側 6px、高 17px 的深色圓角膠囊（rgba(10,20,34,.88)＋1px rgba(255,255,255,.12) 邊、圓角 3），
         內嵌「名稱（#e2f1f8）＋佔比（#7a9bb3）＋漲跌（▲ 紅／▼ 綠）」，600 字重。
         淺色主題：白色膠囊（rgba(255,255,255,.92)＋1px 深色 16% 邊），名稱 #0f1e2e、佔比 #5b7186。
       · 代表股：不畫膠囊，固定 X（寬度 83%）小點右邊 6px 寫「名稱 佔比%」，#8da7bc（淺色 #52667a）。
     ⚠ 字級：參考稿是 11px（膠囊）與 10px（代表股），專案硬規矩是 12px 下限（S.font 低於 12 直接丟錯），
       所以兩者都用 12px；膠囊 17px 高放 12px 字剛好（上下各 2.5px）。
     ▲▼ 的顏色用站上的 --rise／--fall（深色 #ff4d6d／#2ee59d，和參考稿的 #ff5470／#2ee59d 幾乎一樣），
     不另外寫死 —— 全站的漲跌色只有一組。*/
  function elInk(S) {
    return S.pal.dark
      ? { name: '#e2f1f8', share: '#7a9bb3', leaf: '#8da7bc', bg: 'rgba(10,20,34,.88)', line: 'rgba(255,255,255,.12)' }
      : { name: '#0f1e2e', share: '#5b7186', leaf: '#52667a', bg: 'rgba(255,255,255,.92)', line: 'rgba(15,30,50,.16)' };
  }
  function measureLabelsClassic(S) {
    const g = S.gL, W = S.W, cols = S.cols, K = elInk(S);
    S.order.forEach(n => {
      const leaf = n.lv === 3;
      const parts = partsOf(S, n).map(p => ({ ...p, w: leaf ? 500 : 600, fs: 12 }));
      parts.forEach(p => {                               // 顏色照黃金標準換掉（漲跌色不動）
        if (p.chg) return;
        p.c = leaf ? (n.rest ? S.pal.ink3 : K.leaf) : p.name ? K.name : K.share;
      });
      const lines = [[]];
      parts.forEach(p => { if (p.t[0] === '\n') { lines.push([]); p.t = p.t.slice(1); } lines[lines.length - 1].push(p); });
      const x = leaf ? n.tx + 6 : n.tx + n.r + 6;
      const pad = leaf ? 0 : 12;                         // 膠囊左 5、右 7（參考稿 badgeW＝字寬＋12）
      const nextX = n.lv === 0 ? cols[1] - 10 : n.lv === 1 ? cols[2] - 12 : n.lv === 2 ? cols[3] - 10 : W - 4;
      const maxW = S.mini && n.lv === 1 && S.miniNarrow ? Math.max(40, S.miniCR - 2)
        : S.mini && n.lv === 0 ? Math.max(40, W * 0.45) : Math.max(40, nextX - x);   // 緊湊版的根標籤在圓點上方，不受產業鏈欄限制
      let bw = 0;
      lines.forEach(line => {
        line.forEach(p => { S.font(g, p.fs, p.w); p.pw = mw(g, p.t); });
        let lw = line.reduce((a, p) => a + p.pw, 0) + pad;
        const nm = line.find(p => p.name);
        if (lw > maxW && nm) {                           // 放不下：只截名稱，數字永遠完整（全名在提示框）
          const cs = Array.from(nm.t);
          S.font(g, nm.fs, nm.w);
          for (let k = cs.length - 1; k >= 1 && lw > maxW; k--) {
            nm.t = cs.slice(0, k).join('') + '…';
            const w2 = mw(g, nm.t); lw = lw - nm.pw + w2; nm.pw = w2;
          }
        }
        line.w = lw; bw = Math.max(bw, lw);
      });
      const bh = leaf ? 12 : CFG.EL_BADGE_H + (lines.length - 1) * 15;
      if (S.mini && n.lv === 1 && S.miniNarrow) {
        /* 緊湊版・窄：產業鏈膠囊放在圓點正下方（或正上方），左右以圓點置中、夾在 [2, 族群圓點左邊]。
           一條一條放，每次都避開「根的圓點與膠囊、所有產業鏈圓點、已經放好的產業鏈膠囊」：
           依序試 下方置中 → 上方置中 → 下方靠右讓開根 → 上方靠右讓開根，第一個不撞的就用
           （和根節點同一高度的那條鏈 —— 通常是 AI 伺服器 —— 靠這一步躲開根）。*/
        const hit = (b) => (S._miniObs || []).some(o => b.x < o.x + o.w && o.x < b.x + b.w && b.y < o.y + o.h && o.y < b.y + b.h);
        const xc = Math.max(2, Math.min(n.tx - bw / 2, S.miniCR - bw));
        const xr = S.root ? S.root.tx + S.root.r + 4 : 22;
        const cand = [[xc, n.ty + n.r + 3], [xc, n.ty - n.r - 3 - bh], [Math.max(xc, xr), n.ty + n.r + 3], [Math.max(xc, xr), n.ty - n.r - 3 - bh]]
          .filter(([cx, cy]) => cx + bw <= S.miniCR + 0.5 && cy >= 0 && cy + bh <= S.H)
          .map(([cx, cy]) => ({ x: cx, y: cy, w: bw, h: bh }));
        let box = cand.find(b => !hit(b));
        if (!box) {
          /* 四個位置都撞（最窄的 241px：膠囊讓開根之後放不下全名）→ 讓開根、名稱再截短到放得下（% 照樣完整）*/
          const avail = S.miniCR - xr, nm = lines[0].find(p => p.name);
          if (nm) {
            const cs = Array.from(nm.t.replace(/…$/, ''));
            S.font(g, nm.fs, nm.w);
            for (let k = cs.length - 1; k >= 1 && bw > avail; k--) {
              nm.t = cs.slice(0, k).join('') + '…';
              const w2 = mw(g, nm.t); bw = bw - nm.pw + w2; nm.pw = w2; lines[0].w = bw;
            }
          }
          box = [{ x: xr, y: n.ty + n.r + 3, w: bw, h: bh }, { x: xr, y: n.ty - n.r - 3 - bh, w: bw, h: bh }]
            .find(b => !hit(b) && b.y >= 0 && b.y + bh <= S.H) || cand[0] || { x: xc, y: n.ty + n.r + 3, w: bw, h: bh };
        }
        (S._miniObs = S._miniObs || []).push(box);
        n.lab = { lines, x: box.x, y: box.y, w: bw, h: bh, fs: 12, badge: true };
        return;
      }
      if (S.mini && n.lv === 0) {
        /* 緊湊版：根的膠囊在圓點正上方、左緣對齊圓點左緣。順便建「產業鏈膠囊要避開的東西」清單：
           根的圓點與膠囊、每一顆產業鏈圓點（S.order 裡根一定排第一個，所以這裡先建好）。*/
        const box = { x: Math.max(2, n.tx - n.r), y: n.ty - n.r - 5 - bh, w: bw, h: bh };
        S._miniObs = [box, { x: n.tx - n.r - 2, y: n.ty - n.r - 2, w: 2 * n.r + 4, h: 2 * n.r + 4 }];
        (n.kids || []).forEach(c => S._miniObs.push({ x: c.tx - c.r - 2, y: c.ty - c.r - 2, w: 2 * c.r + 4, h: 2 * c.r + 4 }));
        n.lab = { lines, x: box.x, y: box.y, w: bw, h: bh, fs: 12, badge: true };
        return;
      }
      n.lab = { lines, x, y: n.ty - bh / 2, w: bw, h: bh, fs: 12, badge: !leaf };
    });
  }
  function drawLabelsClassic(S) {
    const g = S.gL, K = elInk(S);
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    g.textBaseline = 'middle';
    S.order.forEach(n => {
      const B = n.lab; if (!B) return;
      const ox = n.x - n.tx, oy = n.y - n.ty;
      // 壓暗規則和經典版一樣：被篩掉的 0.35、滑過別條路徑時 0.25；代表股收起時跟著淡出
      const lvs = visOf(S, n); if (lvs < 0.01) return;
      g.globalAlpha = (n.dim ? 0.35 : (related(S, n) ? (n.stale || n.nodata ? 0.6 : 1) : 0.25)) * lvs;
      if (B.badge) {
        g.beginPath();
        if (g.roundRect) g.roundRect(B.x + ox + 0.5, B.y + oy + 0.5, B.w - 1, B.h - 1, 3); else g.rect(B.x + ox + 0.5, B.y + oy + 0.5, B.w - 1, B.h - 1);
        g.fillStyle = K.bg; g.fill();
        g.strokeStyle = K.line; g.lineWidth = 1; g.stroke();
      }
      B.lines.forEach((line, li) => {
        let cx = B.x + ox + (B.badge ? 5 : 0);
        const cy = B.y + oy + (B.badge ? CFG.EL_BADGE_H / 2 : B.h / 2) + 0.5 + li * 15;
        line.forEach(p => { S.font(g, p.fs, p.w); g.fillStyle = p.c; g.fillText(p.t, cx, cy); cx += p.pw; });
      });
    });
    g.globalAlpha = 1;
  }
  function drawLabels(S) {
    if (S.classic) return drawLabelsClassic(S);
    const g = S.gL, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    S.order.forEach(n => {
      const B = n.lab; if (!B) return;
      // 補間中標籤跟著節點走
      const ox = n.x - n.tx, oy = n.y - n.ty;
      const f = fadeOf(S, n);
      g.globalAlpha = n.dim ? 0.38 : (related(S, n) ? 1 : 0.4);
      if (f < 0.3 && S.hover) g.globalAlpha = 0.35;
      g.beginPath();
      if (g.roundRect) g.roundRect(B.x + ox, B.y + oy, B.w, B.h, 4); else g.rect(B.x + ox, B.y + oy, B.w, B.h);
      g.fillStyle = rgba(P.panel, P.dark ? 0.84 : 0.9); g.fill();
      g.strokeStyle = rgba(P.line, P.dark ? 0.9 : 0.8); g.lineWidth = 1; g.stroke();
      g.textBaseline = 'middle';
      B.lines.forEach((line, li) => {
        let cx = B.x + ox + 6;
        const cy = B.y + oy + CFG.BADGE_H / 2 + 0.5 + li * 15;
        line.forEach(p => { S.font(g, p.fs, p.w); g.fillStyle = p.c; g.fillText(p.t, cx, cy); cx += p.pw; });
      });
    });
    g.globalAlpha = 1;
  }

  /* ---- 代表股的顯示（S.leafHover）：目標值 0／1，實際值 n.vis 在迴圈裡 180ms 淡入淡出 ---- */
  function leafWant(S, n) {
    if (n.lv !== 3 || !S.leafHover) return 1;
    const g = n.parent;
    return g && (g.open || g === S.leafHot) || n.picked ? 1 : 0;
  }
  const visOf = (S, n) => (n.lv === 3 && S.leafHover ? (n.vis == null ? leafWant(S, n) : n.vis) : 1);
  function snapVis(S) { S.order.forEach(n => { if (n.lv === 3) n.vis = leafWant(S, n); }); }
  /* 每幀把 vis 往目標推；有變就回傳 true（底圖與標籤要重畫）*/
  function stepVis(S, dt) {
    if (!S.leafHover) return false;
    let moved = false; const k = dt / 0.18;
    S.order.forEach(n => {
      if (n.lv !== 3) return;
      const w = leafWant(S, n), v = n.vis == null ? w : n.vis;
      if (v === w) { n.vis = v; return; }
      n.vis = w > v ? Math.min(w, v + k) : Math.max(w, v - k); moved = true;
    });
    return moved;
  }
  function setLeafHot(S, g) {
    if (!S.leafHover || g === S.leafHot) return;
    S.leafHot = g;
    if (!S.raf) { snapVis(S); drawBase(S); drawLabels(S); drawFx(S, performance.now(), true); }
  }

  /* ---- 動態：粒子、碰撞反饋、彈簧 ---- */
  function spawnOn(S, e, s0) {
    if (S.parts.length >= CFG.P_MAX) return;
    const p = S.pool.pop() || {};
    p.e = e; p.s = s0 || 0; p.jit = 0.9 + Math.random() * 0.2;
    p.off = (Math.random() + Math.random() - 1) * 0.55;       // 近似常態：集中在管中央
    p.a = 0.65 + Math.random() * 0.35;
    S.parts.push(p); S.meter.spawned++;
  }
  /* ★ 2026-09-26 經典光纖的碰撞激發（Andy 原型）：粒子到站 → 終點節點 hitFlash 疊加（上限 1）；
     55% 機率外擴一圈震波（同時 ≤ 60 圈、同一節點 180ms 內不重複）。預熱與被篩掉的節點不激發。*/
  function hitEl(S, n, now, prewarming) {
    if (prewarming || n.dim) return;
    n.hf = Math.min(1, (n.hf || 0) + CFG.HIT_ADD);
    S.meter.hits++;
    if (n.lv !== 3 && Math.random() < CFG.RP_P && S.ripples.length < CFG.RP_MAX && now - (n.rpLast || -1e9) >= CFG.RP_COOL) {
      n.rpLast = now;
      S.ripples.push({ n, r: n.r, r0: n.r, max: n.r + CFG.RP_GROW, a: CFG.RP_A0 });
      S.meter.rpMade++;
      if (S.ripples.length > S.meter.rpPeak) S.meter.rpPeak = S.ripples.length;
    }
  }
  function hit(S, n, now, prewarming) {
    if (S.classic) return hitEl(S, n, now, prewarming);
    if (prewarming || n.dim) return;
    const cool = n.lv === 1 ? 700 : n.lv === 2 ? 900 + 1500 * (1 - Math.sqrt(n.rt)) : 1400;
    if (now - n.last < cool) return;
    n.last = now; n.px = CFG.PULSE; n.pv = 0; n.flash = 1;
    if (S.ripples.length < CFG.RIPPLE_MAX && n.lv <= 2) S.ripples.push({ n, t0: now });
  }
  function update(S, dt, now, prewarming) {
    const sc = Math.max(0.8, Math.min(1.2, S.W / 1100));
    let kR = 1;
    if (S.classic) {                                       // 經典版面：整體發車率壓回粒子預算（見 CFG.CL_P_BUDGET）
      let want = 0;
      S.linkList.forEach(e => { if (e.dead || !e.L || (e.lv === 2 && !leafWant(S, e.to))) return; const v = (18 + 132 * e.spdK) * sc; want += e.rate * e.L / v; });
      const budget = S.mini ? CFG.MINI_P_BUDGET : CFG.CL_P_BUDGET;
      if (want > budget) kR = budget / want;
    }
    S.kRate = kR;
    S.linkList.forEach(e => {
      if (e.dead || !e.L) return;
      e.v = (18 + 132 * e.spdK) * sc;                       // px/秒
      if (e.lv === 2 && S.leafHover && !leafWant(S, e.to)) { e.er = 0; return; }   // 代表股收起：毛細線不發車
      /* 每條活著的線「至少一顆在線上」：發車間隔不超過走完全程的時間 */
      const rate = Math.max(e.rate * kR, e.v / e.L * 1.05); e.er = rate;   // 實際發車率（驗收量通過率用）
      e.acc += rate * dt;
      while (e.acc >= 1) { e.acc -= 1; spawnOn(S, e, Math.random() * e.v * dt); }
    });
    const parts = S.parts;
    for (let i = parts.length - 1; i >= 0; i--) {
      const p = parts[i], e = p.e;
      if (e.lv === 2 && S.leafHover && !leafWant(S, e.to) && visOf(S, e.to) < 0.02) {   // 收起（淡出完）的毛細線：粒子收掉
        parts[i] = parts[parts.length - 1]; parts.pop(); S.pool.push(p); continue;
      }
      p.s += e.v * p.jit * dt;
      if (p.s >= e.L) { hit(S, e.to, now, prewarming); parts[i] = parts[parts.length - 1]; parts.pop(); S.pool.push(p); }
    }
    S.order.forEach(n => {
      if (n.px !== 0 || n.pv !== 0) {
        n.pv += (-CFG.SPRING_K * n.px - CFG.SPRING_C * n.pv) * dt; n.px += n.pv * dt;   // 半隱式歐拉：阻尼衰減
        if (Math.abs(n.px) < 1e-4 && Math.abs(n.pv) < 1e-3) { n.px = 0; n.pv = 0; }
      }
      if (n.flash) { n.flash *= Math.pow(0.94, dt * 60); if (n.flash < 0.01) n.flash = 0; }
      if (n.hf) { n.hf -= CFG.HIT_DECAY * dt * 60; if (n.hf < 0.005) n.hf = 0; }   // 原型：每幀 −0.035（換算成時間，掉幀也一樣快）
    });
    if (S.classic) {                                       // 震波：每幀 r＋0.85、alpha −0.026，到頂或淡光就收
      const k = dt * 60;
      for (let i = S.ripples.length - 1; i >= 0; i--) {
        const rp = S.ripples[i];
        /* 原型（docs/prototypes/capital_flow_impact.html）：alpha 跟半徑同步線性遞減 0.85 → 0，
           等同每幀 −0.026（0.85／26 格 × 0.85px）；代表股外擴只有 16px，照同一條公式縮短 */
        rp.r += CFG.RP_STEP * k; rp.a -= CFG.RP_FADE * k;   // 黃金標準：各自線性（alpha 先到 0，約 23 幀、外擴約 16px）
        if (rp.a <= 0 || rp.r >= rp.max || !S.nodes.has(rp.n.key)) { S.ripples[i] = S.ripples[S.ripples.length - 1]; S.ripples.pop(); }
      }
    } else if (S.ripples.length) S.ripples = S.ripples.filter(r => now - r.t0 < CFG.RIPPLE_SEC * 1000);
  }
  /* 預熱：開畫面就是「已經在流」的穩態，不會先看到右半邊空著 */
  function prewarm(S, sec) {
    const now = performance.now();
    for (let t = 0; t < sec; t += 1 / 30) update(S, 1 / 30, now, true);
    S.order.forEach(n => { n.px = 0; n.pv = 0; n.flash = 0; n.hf = 0; }); S.ripples = [];
  }

  function nodeShape(g, n, r) {
    if (n.lv === 1) {                                // 產業鏈：直立膠囊
      const hh = n.hh * (1 + n.px * 0.5), w = (n.cw || 6) * (1 + n.px);
      g.beginPath();
      if (g.roundRect) g.roundRect(n.x - w / 2, n.y - hh, w, hh * 2, w / 2); else g.rect(n.x - w / 2, n.y - hh, w, hh * 2);
    } else { g.beginPath(); g.arc(n.x, n.y, r, 0, Math.PI * 2); }
  }
  function drawFx(S, now, still) {
    const g = S.gF, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0);
    /* 每幀整張清掉。拖尾不用「整張 destination-out 擦淡」—— 那一步在軟體繪圖（沒有 GPU 的筆電、
       DPR 2）上是整張畫布的合成，實測把幀率砍掉一半；改成每顆粒子自己帶兩顆越來越淡的影子，
       看起來一樣是彗尾，成本只跟粒子數有關。*/
    g.clearRect(0, 0, S.W, S.H);
    if (!still) {
      const parts = S.parts;
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i], e = p.e; if (!e.xs) continue;
        const sp = S.sprites[e.to.hue]; if (!sp) continue;
        const lvis = e.lv === 2 ? visOf(S, e.to) : 1; if (lvis < 0.02) continue;
        const a0 = p.a * e.al * Math.min(fadeOf(S, e.from), fadeOf(S, e.to)) * lvis;
        const sz0 = sp.size * e.pr / sp.R;
        /* 經典版面：慢的粒子彗尾本來就疊在自己身上（7px 內），省掉那兩次 drawImage；快的才畫尾巴 */
        const tails = S.classic ? (e.v > 95 ? 2 : e.v > 50 ? 1 : 0) : 2;
        for (let tail = tails; tail >= 0; tail--) {       // 彗尾：往回 7px、14px 各一顆淡影
          const s = p.s - tail * 7; if (s < 0) continue;
          const f = s / e.L * e.M, k = Math.min(e.M - 1, f | 0), u = f - k, off = p.off * e.w * 0.7;
          const x = e.xs[k] + (e.xs[k + 1] - e.xs[k]) * u + e.nx[k] * off;
          const y = e.ys[k] + (e.ys[k + 1] - e.ys[k]) * u + e.ny[k] * off;
          const sz = sz0 * (1 - tail * 0.18);
          g.globalAlpha = a0 * (tail ? (P.dark ? 0.32 : 0.26) / tail : 1);
          g.drawImage(sp.c, x - sz / 2, y - sz / 2, sz, sz);
        }
      }
      if (S.classic) { drawNodesEl(S, g, P, still); return; }
      g.lineWidth = 1;
      S.ripples.forEach(rp => {          // 外擴震波：1px 細環，ease-out 外擴並淡出
        const q = Math.min(1, (now - rp.t0) / (CFG.RIPPLE_SEC * 1000)), ease = 1 - Math.pow(1 - q, 3), n = rp.n;
        g.globalAlpha = (P.dark ? 0.55 : 0.4) * Math.pow(1 - q, 1.6) * fadeOf(S, n);
        g.strokeStyle = n.dot;
        g.beginPath();
        if (n.lv === 1) {
          const gr = CFG.RIPPLE_GROW * ease;
          if (g.roundRect) g.roundRect(n.x - 3 - gr / 2, n.y - n.hh - gr / 2, 6 + gr, n.hh * 2 + gr, (6 + gr) / 2);
        } else g.arc(n.x, n.y, n.r + CFG.RIPPLE_GROW * ease, 0, Math.PI * 2);
        g.stroke();
      });
    } else if (S.classic) { drawNodesEl(S, g, P, still); return; }
    // 節點：常駐微光（小圖放大）＋ 實心本體（彈性放大）＋ 核心瞬態亮起
    S.order.forEach(n => {
      const f = fadeOf(S, n), col = n.stale || n.nodata ? P.ink3 : n.dot;
      const r = n.r * (1 + n.px);
      const sp = S.sprites[n.hue];
      if (sp && !n.stale && !n.nodata && n.lv !== 1) {
        const gs = sp.size * (r / sp.R) * 0.6;
        g.globalAlpha = (P.dark ? 0.5 : 0.3) * f; g.drawImage(sp.c, n.x - gs / 2, n.y - gs / 2, gs, gs);
      }
      g.globalAlpha = f * (n.stale || n.nodata ? 0.55 : 1);
      g.fillStyle = n.lv === 1 ? col : rgba(col, 0.55 + 0.45 * Math.max(n.rt, n.lv === 0 ? 1 : 0.25));
      nodeShape(g, n, r); g.fill();
      if (n.picked || (n.lv === 2 && n.open)) {         // 你點開的：亮一圈細邊
        g.strokeStyle = P.ink2; g.lineWidth = 1.3; nodeShape(g, n, r + 2); g.stroke();
      }
      if (n.flash > 0.02 && !still) {
        g.globalAlpha = Math.min(1, n.flash) * 0.7 * f;
        g.fillStyle = P.dark ? '#ffffff' : mixW(col, 0.55);
        if (n.lv === 1) { nodeShape(g, { ...n, hh: n.hh * 0.6, px: 0 }, 0); g.fill(); }
        else { g.beginPath(); g.arc(n.x, n.y, r * 0.55, 0, Math.PI * 2); g.fill(); }
      }
    });
    g.globalAlpha = 1;
  }

  /* ★ 2026-09-26（第二版）經典光纖的節點與震波 —— Andy 第 2 點，照黃金標準：
       · 節點：半徑 4.5～7.5 的精緻實心圓點＋1px 白描邊、6px 微光（放射漸層小圖，等效 shadowBlur 6），**不要大發光圈**
         （第一版的常駐 r＋2 淡底與 0.42 倍粒子光暈拿掉了）
       · 碰撞光環：r＋5×hitFlash、alpha hitFlash×0.45（參考稿 shadowBlur 12×hitFlash → 光暈小圖外擴 1.5 倍模擬，不用 shadowBlur）
       · hitFlash > 0.3 核心轉白（0.3～0.6 漸變，不是一下跳白 —— 熱門節點一秒被撞好幾次，跳白會一直閃）
       · 漣漪：r → r＋16、每幀 ＋0.7、alpha 0.8 每幀 −0.035、線寬 1.2，顏色＝節點色（產業鏈色，不是紅綠）
       · 代表股：1.8px 小點（alpha 0.75），被撞時一樣轉白，但不起漣漪（參考稿的毛細終點也不起）
     still（動畫關／減少動態）：不畫震波、不激發，只剩靜態的點。*/
  function drawNodesEl(S, g, P, still) {
    if (!still && S.ripples.length) {
      g.lineWidth = CFG.RP_LW;
      S.ripples.forEach(rp => {
        const n = rp.n;
        g.globalAlpha = Math.max(0, rp.a) * (P.dark ? 1 : 0.8) * fadeOf(S, n);
        g.strokeStyle = n.stale || n.nodata ? P.ink3 : n.dot;
        g.beginPath(); g.arc(n.x, n.y, rp.r, 0, Math.PI * 2); g.stroke();
      });
    }
    S.order.forEach(n => {
      const f = fadeOf(S, n), off = n.stale || n.nodata, col = off ? P.ink3 : n.dot;
      const r = n.r, hf = still ? 0 : (n.hf || 0);
      const ha = S.halos && S.halos[n.hue];
      const wz = Math.max(0, Math.min(1, (hf - 0.3) / 0.3));
      if (n.lv === 3) {                                  // 代表股小點（收起時跟著淡出）
        const lv = visOf(S, n); if (lv < 0.01) return;
        g.globalAlpha = 0.75 * f * lv; g.fillStyle = col;
        g.beginPath(); g.arc(n.x, n.y, r, 0, Math.PI * 2); g.fill();
        if (wz > 0) { g.globalAlpha = wz * f * lv; g.fillStyle = P.dark ? '#ffffff' : mixW(col, 0.6); g.fill(); }
        return;
      }
      if (ha && !off) {                                  // 常駐 6px 微光
        const R = r + 6;
        g.globalAlpha = (P.dark ? 0.42 : 0.22) * f; g.drawImage(ha.c, n.x - R, n.y - R, R * 2, R * 2);
      }
      if (hf > 0.02 && ha && !off) {                     // 碰撞光環 r＋5×hitFlash
        const R = (r + 5 * hf) * 1.5;
        g.globalAlpha = hf * 0.45 * f; g.drawImage(ha.c, n.x - R, n.y - R, R * 2, R * 2);
      }
      g.globalAlpha = f * (off ? 0.6 : 1);
      g.fillStyle = col;
      g.beginPath(); g.arc(n.x, n.y, r, 0, Math.PI * 2); g.fill();
      if (wz > 0) {                                       // 核心轉白（淺色主題轉淡色，不會變成一個洞）
        g.globalAlpha = wz * f; g.fillStyle = P.dark ? '#ffffff' : mixW(col, 0.7); g.fill();
      }
      g.globalAlpha = f * (off ? 0.6 : 1);
      g.strokeStyle = P.dark ? '#ffffff' : 'rgba(255,255,255,.95)'; g.lineWidth = 1; g.stroke();   // 1px 白描邊
      if (n.picked || (n.lv === 2 && n.open)) {         // 你點開的：外面再一圈細邊
        g.globalAlpha = f; g.strokeStyle = P.ink2; g.lineWidth = 1.2;
        g.beginPath(); g.arc(n.x, n.y, r + 3, 0, Math.PI * 2); g.stroke();
      }
    });
    g.globalAlpha = 1;
  }

  /* ---- 迴圈：單一 rAF；分頁在背景、捲出畫面、動畫關掉都停 ---- */
  function frame(S, now) {
    S.raf = 0;
    if (!S.alive) return;
    if (!S.host.isConnected || !S.stage.isConnected) { destroy(S.host); return; }
    if (!S.motion || document.hidden || !S.visible) return;
    if (S.host.offsetParent === null) {            // 換到站內別的分頁：容器還在、只是藏起來 → 慢速探一下就好
      S.idle = setTimeout(() => { S.idle = 0; startLoop(S); }, 600);
      return;
    }
    const t0 = performance.now();
    const rawDt = Math.max(0, (now - S.lastT) / 1000);
    const dt = Math.min(0.05, rawDt); S.lastT = now;
    /* 代表股淡入淡出用真實經過時間（最多 0.25 秒一步）：粒子的 dt 壓在 0.05 是怕掉幀時一口氣跳太遠，
       但淡入淡出若也壓，掉到 7 FPS 時 180ms 會拖成半秒以上 */
    const vdt = Math.min(0.25, rawDt);
    if (S.tween) stepTween(S, now);
    else if (stepVis(S, vdt)) { drawBase(S); drawLabels(S); }
    if (S.tween) stepVis(S, vdt);
    update(S, dt, now, false);
    drawFx(S, now, false);
    const m = S.meter; m.frames++; m.cost += performance.now() - t0;
    m.ts.push(now); while (m.ts.length && now - m.ts[0] > 2000) m.ts.shift();
    S.raf = requestAnimationFrame(t => frame(S, t));
  }
  function startLoop(S) {
    if (S.raf || S.idle || !S.alive || !S.motion || document.hidden || !S.visible || !S.W) return;
    if (S.needWarm) { S.needWarm = false; const t = performance.now(); prewarm(S, 4); S.meter.warmMs = performance.now() - t; }
    S.lastT = performance.now();
    S.raf = requestAnimationFrame(t => frame(S, t));
  }
  function stopLoop(S) {
    if (S.raf) cancelAnimationFrame(S.raf); S.raf = 0;
    if (S.idle) clearTimeout(S.idle); S.idle = 0;
    S.meter.ts.length = 0;
  }
  function drawStill(S) {                          // 靜止：不閃、不動、不留殘影
    S.order.forEach(n => { n.px = 0; n.pv = 0; n.flash = 0; n.hf = 0; n.x = n.tx; n.y = n.ty; });
    snapVis(S);                                      // 代表股：靜止時沒有淡入淡出，直接到位
    S.ripples = []; S.tween = null; S.twE = 1;
    measureLabels(S); curves(S); drawBase(S); drawLabels(S); drawFx(S, performance.now(), true);
  }
  function stepTween(S, now) {
    const tw = S.tween, q = Math.min(1, (now - tw.t0) / tw.dur);
    const e = tw.lin ? q : q < 0.5 ? 4 * q * q * q : 1 - Math.pow(-2 * q + 2, 3) / 2;   // 回放等速／單次 cubicInOut
    S.order.forEach(n => { n.x = n.sx + (n.tx - n.sx) * e; n.y = n.sy + (n.ty - n.sy) * e; });
    S.twE = q >= 1 ? 1 : e;
    measureLabels(S);                                // 百分比同步補間 → 標籤字要重排
    curves(S); drawBase(S); drawLabels(S);
    if (q >= 1) S.tween = null;
  }

  /* ---- 尺寸：HiDPI ---- */
  function sizeCanvases(S) {
    const w = S.stage.clientWidth;
    S.W = w; S.DPR = Math.min(2, window.devicePixelRatio || 1);
    /* ★ 2026-09-26 第二版：經典光纖深色主題的畫布底改成黃金標準的深底 #050a14（鮮豔感主要來自更深的底）；
       拓撲版與淺色主題照舊（卡片底色＋很淡的青色徑向漸層）。*/
    S.stage.style.background = S.classic && S.pal.dark ? '#050a14' : '';
    [S.cvBase, S.cvFx, S.cvLab].forEach(c => {
      const pw = Math.round(S.W * S.DPR), ph = Math.round(S.H * S.DPR);
      if (c.width !== pw || c.height !== ph) { c.width = pw; c.height = ph; c.getContext('2d').__f = null; }
      c.style.width = S.W + 'px'; c.style.height = S.H + 'px';
    });
  }
  /* 畫布不在視窗裡（或分頁在背景）→ 還沒必要當場畫 */
  function farAway(S) {
    if (document.hidden) return true;
    const r = S.stage.getBoundingClientRect();
    return r.top >= window.innerHeight || r.bottom <= 0;
  }
  function layoutAndDraw(S, allowTween, force) {
    if (!S.stage.clientWidth) return;
    const tA = performance.now();
    S.H = wantHeight(S);
    S.stage.style.height = S.H + 'px';
    S.host.style.height = (S.H + barH(S)) + 'px';            // 高度先定（版面不會等圖畫完才長高）
    /* ★ 2026-09-25（開網頁卡頓那批的要求：首次載入不額外變重）：
       資金流向頁一進來，這張卡的畫布剛好在首屏下緣之外。**第一次**畫（配三張全尺寸 HiDPI 畫布、量約 300 段字、
       77 條曲線查表、畫底圖與標籤，容器實測 80～230ms 的長任務）不在載入那一刻做：
       捲進畫面就當場畫（pendIO）；沒捲的話等瀏覽器閒下來再畫（requestIdleCallback，最慢 1.5 秒）——
       和 app.js 的 whenNear 同一個想法。分頁在背景也先不畫（onVis 補）。
       資料模型照算（buildModel 在 render() 裡），所以點擊、探針的節點清單都在。
       畫過一次之後就照舊每次重畫（換日、即時都要當場反映）。*/
    if (!S.drawn && !force && farAway(S)) {
      S.pendingDraw = true;
      if (!S.pendIdle) {
        const ric = window.requestIdleCallback || ((f) => setTimeout(f, 200));
        S.pendIdle = ric(() => { S.pendIdle = 0; if (S.alive && S.pendingDraw && !document.hidden) layoutAndDraw(S, false, true); }, { timeout: 1500 });
      }
      return;
    }
    S.pendingDraw = false; S.drawn = true;
    const prevW = S.W;
    sizeCanvases(S);
    if (!allowTween || prevW !== S.W) S.first = S.first || prevW !== S.W;
    layout(S);
    if (S.tween == null) S.order.forEach(n => { n.x = n.tx; n.y = n.ty; });
    measureLabels(S);
    curves(S);
    if (!S.sprites || S._spriteKey !== spriteKey(S)) { sprites(S); S._spriteKey = spriteKey(S); }
    drawBase(S); drawLabels(S);
    if (S.motion) {
      /* 預熱（先模擬 4 秒讓粒子鋪滿）延到迴圈**真的開始跑**的那一刻才做：
         卡片在首屏下方、分頁在背景時根本不會跑迴圈，首次載入就不必替看不見的動畫付這筆（開網頁卡頓那批的要求）。*/
      if (S.first) S.needWarm = true;
      drawFx(S, performance.now(), true);
      startLoop(S);
    } else drawStill(S);
    S.first = false;
    const dt = performance.now() - tA;
    S.meter.lastDrawMs = dt;
    if (S.meter.firstDrawMs == null) S.meter.firstDrawMs = dt;
  }
  const barH = (S) => (S.mini ? 0 : CFG.BAR_H);             // 緊湊版沒有上方說明列
  const spriteKey = (S) => S.DPR + '|' + S.pal.dark + '|' + (S.classic ? 'el' : 'tp') + '|' + [...new Set(S.order.map(n => n.hue))].join(',');

  /* ---- 滑過／點擊 ---- */
  function pickAt(S, mx, my) {
    let best = null, bd = 1e9;
    for (const n of S.order) {
      if (n.lv === 3 && S.leafHover && !leafWant(S, n)) continue;   // 收起的代表股：看不見就點不到
      const d = n.lv === 1 && !S.classic ? (Math.abs(mx - n.x) <= 8 && Math.abs(my - n.y) <= n.hh + 5 ? 0 : 1e9)
        : Math.hypot(mx - n.x, my - n.y) - (n.r + 6);
      if (d <= 0 && d < bd) { best = n; bd = d; }
      const B = n.lab;
      if (B && mx >= B.x && mx <= B.x + B.w && my >= B.y && my <= B.y + B.h && bd > -1) { best = n; bd = -1; }
    }
    return best;
  }
  function showTip(S, n, mx, my) {
    let html = '';
    try { html = S.opts.tipHTML ? S.opts.tipHTML(n.d) : ''; } catch (e) { html = ''; }
    if (!html) { hideTip(S); return; }
    const t = S.tipEl; t.innerHTML = html; t.classList.add('on');
    const tw = t.offsetWidth, th = t.offsetHeight;
    let x = mx + 14, y = my + 12;
    /* 代表股收起（S.leafHover）時滑到族群，右邊正要淡入那一族的三檔 —— 提示框改放在游標左邊，不要蓋住它們 */
    if (S.leafHover && (n.lv === 2 || n.lv === 3) && mx - tw - 14 >= 4) x = mx - tw - 14;
    if (x + tw > S.W - 4) x = mx - tw - 14;
    if (y + th > S.H - 4) y = my - th - 12;
    t.style.left = Math.max(4, x) + 'px'; t.style.top = Math.max(4, y) + 'px';
  }
  function hideTip(S) { S.tipEl.classList.remove('on'); }
  /* 滑鼠在哪個族群的「那一格槽位」裡：從族群圓點左邊 12px 到畫布右緣、上下半格（點開的族群那格比較高）*/
  function rowGroupAt(S, mx, my) {
    if (!S.leafHover) return null;
    for (const n of S.order) {
      if (n.lv !== 2) continue;
      const half = (n.gs || S.slot || 36) / 2;
      if (Math.abs(my - n.y) <= half && mx >= n.x - n.r - 12) return n;
    }
    return null;
  }
  function setHover(S, n) {
    if (n === S.hover) return;
    S.hover = n;
    drawBase(S); drawLabels(S);
    if (!S.motion || !S.raf) drawFx(S, performance.now(), true);
  }
  function wirePointer(S) {
    const cv = S.cvLab;
    const loc = (ev) => { const b = cv.getBoundingClientRect(); return [ev.clientX - b.left, ev.clientY - b.top]; };
    cv.addEventListener('pointermove', (ev) => {
      const [mx, my] = loc(ev), n = pickAt(S, mx, my);
      cv.classList.toggle('hot', !!n && !(n.d && n.d.placeholder));
      // 代表股要顯示哪一族：滑到族群本身 → 它；滑到代表股 → 它的族群；都不是 → 看在不在哪個族群那一格槽位裡
      setLeafHot(S, n && n.lv === 2 ? n : n && n.lv === 3 ? n.parent : rowGroupAt(S, mx, my));
      if (n) { showTip(S, n, mx, my); setHover(S, n.lv === 0 ? null : n); }
      else { hideTip(S); setHover(S, null); }
    });
    cv.addEventListener('pointerleave', () => { hideTip(S); setHover(S, null); setLeafHot(S, null); cv.classList.remove('hot'); });
    cv.addEventListener('click', (ev) => {
      const [mx, my] = loc(ev), n = pickAt(S, mx, my);
      hideTip(S);
      S.hover = null;
      if (n) { if (S.opts.onPick) S.opts.onPick(n.d, n.lv); }
      else if (S.opts.onBlank) S.opts.onBlank();
    });
  }

  /* =========================================================================
     對外
     ========================================================================= */
  function render(host, tree, opts) {
    if (!host) return 0;
    let S = host._ft;
    if (!S || !S.stage.isConnected || S.stage.parentNode !== host) { if (S) destroy(host); S = create(host); }
    const pal = { ...(opts.pal || {}) };
    pal.glow = pal.dark ? CFG.GLOW_DARK : CFG.GLOW_LIGHT;
    const palKey = JSON.stringify(pal);
    if (S._palKey !== palKey) { S._palKey = palKey; S._spriteKey = ''; S.first = true; }
    const lay = (opts && opts.layout) || 'topo';
    if (S._layout !== lay) { S._layout = lay; S.first = true; S.tween = null; }   // 換版面：直接就位，不從舊版面補間過來
    S.pal = pal; S.opts = opts || {}; S.model = tree;
    S.leg.innerHTML = opts.legend || '';
    /* 緊湊版：說明列整條藏起來，動態開關搬進畫布左上角（同一顆按鈕、同一個 localStorage 設定）。
       左上角：根在左邊中間、線往右上右下散開，左上角那一小塊一直是空的；左下角在窄排法會壓到最後一條鏈的膠囊。*/
    const mini = lay === 'mini';
    S.bar.style.display = mini ? 'none' : '';
    S.mbtn.classList.toggle('ftcorner', mini);
    if (mini && S.mbtn.parentNode !== S.stage) S.stage.appendChild(S.mbtn);
    if (!mini && S.mbtn.parentNode !== S.bar) S.bar.appendChild(S.mbtn);
    paintMotionBtn(S);
    buildModel(S);
    layoutAndDraw(S, true);
    return S.H + barH(S);
  }

  /* 驗收用：量測與探針（_uitest.py 讀這裡；不改任何狀態）*/
  function probe(host) {
    const S = host && host._ft; if (!S) return null;
    const b = S.cvLab.getBoundingClientRect();
    let off = 0, stray = 0, maxOff = 0;
    const sample = [];
    const rootX = S.root ? S.root.x : 0;
    S.parts.forEach((p, i) => {
      const e = p.e; if (!e.xs) return;
      const f = p.s / e.L * e.M, k = Math.min(e.M - 1, f | 0), u = f - k, o2 = p.off * e.w;
      const x = e.xs[k] + (e.xs[k + 1] - e.xs[k]) * u + e.nx[k] * o2;
      const y = e.ys[k] + (e.ys[k + 1] - e.ys[k]) * u + e.ny[k] * o2;
      // 離「目前這條曲線」多遠（查整條表取最近點）
      let dmin = 1e9;
      for (let j = 0; j <= e.M; j++) { const dd = Math.hypot(x - e.xs[j], y - e.ys[j]); if (dd < dmin) dmin = dd; }
      const seg = e.L / e.M;
      const tol = e.w * 1.3 + seg / 2 + 1;
      if (dmin > tol) off++;
      maxOff = Math.max(maxOff, dmin - seg / 2);
      if (x < rootX - 3) stray++;
      if (i % 7 === 0 && sample.length < 60) sample.push([Math.round(x), Math.round(y), e.key]);
    });
    const m = S.meter, ts = m.ts;
    const fps = ts.length > 5 ? (ts.length - 1) / ((ts[ts.length - 1] - ts[0]) / 1000) : 0;
    return {
      W: S.W, H: S.H, total: S.H + barH(S), dpr: S.DPR, motion: S.motion, running: !!S.raf,
      reduce: !!reduceMQ.matches, dark: !!S.pal.dark,
      nodes: S.order.map(n => ({ key: n.key, lv: n.lv, name: n.name, x: Math.round(n.x), y: Math.round(n.y),
        cx: Math.round(b.left + n.x), cy: Math.round(b.top + n.y), r: +(n.r || 0).toFixed(1), dim: !!n.dim,
        stale: !!n.stale, open: !!n.open, picked: !!n.picked, rest: !!n.rest, nodata: !!n.nodata,
        parent: n.parent ? n.parent.key : null,
        value: n.d ? n.d.value : null,
        // ★ 2026-09-26：節點形狀（經典光纖一律圓；拓撲版產業鏈是直條）、碰撞激發讀值、節點色
        shape: (S.classic || n.lv !== 1) ? 'circle' : 'bar', hh: +(n.hh || 0).toFixed(1),
        hf: +(n.hf || 0).toFixed(3), dot: n.dot,
        vis: +visOf(S, n).toFixed(3), want: leafWant(S, n),
        text: n.lab ? n.lab.lines.map(l => l.map(p => p.t).join('')).join(' / ') : '',
        chg: n.lab ? (n.lab.lines[0].find(p => p.chg) || {}).chg || null : null,
        chgColor: n.lab ? (n.lab.lines[0].find(p => p.chg) || {}).c || null : null,
        lab: n.lab ? { x: Math.round(n.lab.x), y: Math.round(n.lab.y), w: Math.round(n.lab.w), h: Math.round(n.lab.h), badge: !!n.lab.badge } : null })),
      links: S.linkList.map(e => ({ key: e.key, lv: e.lv, w: +e.w.toFixed(2), dead: !!e.dead,
        n: S.parts.filter(p => p.e === e).length, rate: +e.rate.toFixed(2), v: +(e.v || 0).toFixed(1), pr: +e.pr.toFixed(2),
        al: +(e.al || 0).toFixed(3), er: +(e.er || 0).toFixed(3), rt: +(e.rt || 0).toFixed(4),
        shown: e.lv === 2 ? leafWant(S, e.to) : 1,          // 2026-09-26（晚）：毛細線現在是不是該顯示（代表股收起時 0）
        from: e.from.key, to: e.to.key,
        // ★ 2026-09-26：這條線的三次貝茲 [x0,y0, cp1x,cp1y, cp2x,cp2y, x1,y1]（驗控制點比例 0.55／0.45）
        cp: e.p ? e.p.map(v => +v.toFixed(2)) : null,
        inW: e.inW == null ? null : e.inW, inA: e.inA == null ? null : e.inA,
        outW: e.outW == null ? null : +e.outW.toFixed(2), outA: e.outA == null ? null : +e.outA.toFixed(4),
        inAEff: e.inAEff == null ? null : +e.inAEff.toFixed(4), outAEff: e.outAEff == null ? null : +e.outAEff.toFixed(4) })),
      particles: S.parts.length, offCurve: off, maxOff: +maxOff.toFixed(2), leftStray: stray, rootX: Math.round(rootX), sample,
      fps: +fps.toFixed(1), frames: m.frames, avgCostMs: m.frames ? +(m.cost / m.frames).toFixed(3) : 0,
      maxBlur: m.maxBlur, minFont: m.minFont === Infinity ? null : m.minFont, spawned: m.spawned,
      layout: S.mini ? 'mini' : S.classic ? 'classic' : 'topo',
      firstDrawMs: m.firstDrawMs == null ? null : +m.firstDrawMs.toFixed(1),
      lastDrawMs: m.lastDrawMs == null ? null : +m.lastDrawMs.toFixed(1),
      warmMs: m.warmMs == null ? null : +m.warmMs.toFixed(1),
      pending: !!S.pendingDraw,
      leafHover: !!S.leafHover, leafHot: S.leafHot ? S.leafHot.key : null,
      ripples: S.ripples.length, rpMax: CFG.RP_MAX, rpPeak: m.rpPeak, rpMade: m.rpMade, hits: m.hits,
      cols: (S.cols || []).map(v => +(+v).toFixed(1)), cp: [CFG.CL_CP1, CFG.CL_CP2],
      slot: S.classic ? +(S.slot || 0).toFixed(1) : null, canvases: S.stage.querySelectorAll('canvas').length,
      stageBg: S.stage.style.background || '',
      tweening: !!S.tween, twE: +(S.twE == null ? 1 : S.twE).toFixed(3), twLin: !!(S.tween && S.tween.lin), hover: S.hover ? S.hover.key : null,
    };
  }
  /* 驗收用：一口氣讓 k 顆粒子「到站」（亂數挑活著的節點），驗震波上限；只在經典光纖有意義 */
  function burst(host, k) {
    const S = host && host._ft; if (!S || !S.classic) return null;
    const live = S.order.filter(n => n.lv > 0 && n.lv < 3 && !n.dim);
    const now = performance.now();
    for (let i = 0; i < k; i++) {                   // 刻意略過每個節點 180ms 的冷卻，只剩「同時 ≤ 60 圈」這道閘
      const n = live[(Math.random() * live.length) | 0]; n.rpLast = -1e9; hitEl(S, n, now, false);
    }
    return { ripples: S.ripples.length, peak: S.meter.rpPeak };
  }
  /* 驗收用：重設幀率量表（開始量之前叫一次）*/
  function resetMeter(host) {
    const S = host && host._ft; if (!S) return;
    S.meter.frames = 0; S.meter.cost = 0; S.meter.ts.length = 0;
  }

  /* 驗收用：把單次換日補間拉長（容器 headless 的 rAF 只有 13～15 FPS，450ms 內只取得到 2～3 個樣本）。傳 0 還原。*/
  function tweenMs(host, ms) { const S = host && host._ft; if (S) S.tweenMs = ms || 0; }
  window.FlowTopo = { render, destroy, probe, resetMeter, CFG, tweenMs, burst,
    has: (host) => !!(host && host._ft), motionWanted };
})();
