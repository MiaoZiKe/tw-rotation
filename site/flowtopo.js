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
     · 圖四（要）：**直角（肘形）樹**＝ECharts tree edgeShape 'polyline' 的分叉點結構。每條邊是
       「父節點往右一段水平 → 在分叉點 x 垂直走到子節點的高度 → 水平接進子節點」，轉角帶小圓角；
       同一個父節點的兄弟共用同一個分叉點 x，所以看起來是一根垂直幹線從最上面的子節點拉到最下面的子節點。
       四層（根→產業鏈、產業鏈→族群、族群→代表股）一致套用；分叉點 x 每一層一個，放在兩欄之間靠父節點那側
       約 40～62%（要讓開父節點的標籤，見 trunkX()）。線寬仍依金額平方根（粗細對比不變），版面位置不變。
     · 圖五＋原型（要的特效）：
         ① 粒子＝白色核心＋線色光暈（預先畫好的小圖，shadowBlur 只在畫小圖時用一次，≤ 6px）；
         ② 碰撞激發：粒子到站時終點節點 hitFlash ＋0.35（上限 1，逐幀衰減 0.035）→ 外圈放大發光、
            hitFlash > 0.3 核心轉白（漸變，不是一下跳白）、標籤變亮（最上層那張 ftglow 畫布疊一層亮字）；
         ③ 擴散震波：到站時 55% 機率外擴一圈（r → r＋26、alpha 0.85 遞減），顏色＝節點色；
            同時最多 60 圈（CFG.RP_MAX），同一個節點 180ms 內不重複起漣漪（不然大節點會疊成一團同心圓）；
         ④ 雙層光纖：外層寬而淡的光暈管＋線身＋中間一條細而亮的芯；
         ⑤ 節點常駐一圈淡的底（r＋2、alpha 0.25）—— 靜態的，不脈動（Andy 否決過一直脈動）。
     · 原型的顏色是每條線不同色；這裡照站上規矩：節點、線、粒子一律用**產業鏈色**，紅綠只給漲跌字（▲▼）。
     · 原型的 shadowBlur 24／25px 超過專案上限 10px —— 改用預先畫好的放射漸層小圖放大（不是 shadowBlur），
       外光環半徑照原型 r＋8×hitFlash，發光範圍只在節點周圍幾 px，不做大面積泛光。

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
    CL_P_BUDGET: 380,    // 代表股標籤寬度上限（經典版 132 − 12），超過截斷，全名在提示框
    /* ★ 2026-09-26 經典光纖改直角樹＋碰撞激發（數字取自 Andy 給的原型，時間型的換算成「每 1/60 秒」）*/
    EL_RAD: 7,               // 直角轉角的小圓角半徑（px）；上下差太小時自動縮
    EL_FRAC_MIN: 0.40, EL_FRAC_MAX: 0.62,   // 分叉點 x 落在兩欄之間的比例（靠父節點那側）
    HIT_ADD: 0.35, HIT_DECAY: 0.035,        // 碰撞激發：每到一顆 +0.35（上限 1），每幀 −0.035
    RP_GROW: 26, RP_GROW_LEAF: 16,          // 震波外擴：r → r＋26（代表股間距只有 16px，縮成 +16）
    RP_STEP: 0.85, RP_FADE: 0.026, RP_A0: 0.85, RP_P: 0.55,   // 每幀 r+0.85、alpha−0.026；到站 55% 機率起一圈
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
.ftopo .ftstage{position:relative;width:100%;border-radius:10px;overflow:hidden;
  background:radial-gradient(120% 90% at 8% 50%,color-mix(in srgb,var(--cyan) 5%,transparent),transparent 60%)}
.ftopo .ftstage canvas{position:absolute;left:0;top:0;display:block}
.ftopo .ftstage canvas.ftlab{cursor:default}
.ftopo .ftstage canvas.ftglow{pointer-events:none}
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
    const mbtn = document.createElement('button'); mbtn.type = 'button'; mbtn.className = 'ftbtn'; mbtn.id = 'sankeyMotionBtn';
    bar.append(leg, mbtn);
    const stage = document.createElement('div'); stage.className = 'ftstage';
    const cvBase = document.createElement('canvas'), cvFx = document.createElement('canvas'), cvLab = document.createElement('canvas');
    /* ★ 2026-09-26：第四張畫布疊在標籤上面、不吃滑鼠 —— 只畫「碰撞激發時標籤變亮」那層亮字（經典光纖才用） */
    const cvGlow = document.createElement('canvas');
    cvBase.className = 'ftbase'; cvFx.className = 'ftfx'; cvLab.className = 'ftlab'; cvGlow.className = 'ftglow';
    [cvBase, cvFx, cvGlow].forEach(c => c.setAttribute('aria-hidden', 'true'));
    cvLab.setAttribute('role', 'img');
    const tipEl = document.createElement('div'); tipEl.className = 'fttip';
    stage.append(cvBase, cvFx, cvLab, cvGlow, tipEl);
    host.append(bar, stage);
    const gB = cvBase.getContext('2d'), gF = cvFx.getContext('2d'), gL = cvLab.getContext('2d'), gG = cvGlow.getContext('2d');

    const S = {
      host, bar, leg, mbtn, stage, cvBase, cvFx, cvLab, cvGlow, tipEl, gB, gF, gL, gG, glowDirty: false,
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
  function chainHue(S, cid) {
    const t = S.pal.dark ? 'dark' : 'light', m = CHAIN_HUE[t];
    if (m[cid]) return m[cid];
    const h = [...String(cid)].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 997, 7);
    return CHAIN_MORE[t][h % CHAIN_MORE[t].length];
  }

  function buildModel(S) {
    const M = S.model, o = S.opts, maxV = o.maxV || 1;
    const classic = S.classic = o.layout === 'classic';
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
    const root = up('root', { lv: 0, d: M, name: '台股成交值', hue: S.pal.cyan, dot: S.pal.cyan, rt: 1, r: 8, dim: false, parent: null });
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
        if (g.open || classic) {
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
    if (S.classic) {                 // 經典版的公式：葉子數 × 16 ＋ 64，夾在 560～1040（有展開 1400）
      const slots = S.root.kids.reduce((a, c) => a + c.kids.reduce((b, g) => b + g.slots, 0), 0);
      const open = S.order.some(n => n.lv === 2 && n.open);
      return Math.max(CFG.CL_H_MIN, Math.min(open ? CFG.CL_H_MAX_EXP : CFG.CL_H_MAX, slots * CFG.CL_LEAF_ROW + 64));
    }
    const chains = S.root.kids, nG = chains.reduce((a, c) => a + c.kids.length, 0);
    const slots = nG + 0.7 * Math.max(0, chains.length - 1);
    let h = Math.round(slots * CFG.ROW + 30);
    const nL = S.order.filter(n => n.lv === 3).length;
    if (nL) h = Math.max(h, nL * CFG.LEAF_ROW + 30);
    return Math.max(CFG.H_MIN, Math.min(CFG.H_MAX, h));
  }
  /* 經典版面：照 ECharts tree（orient LR、orthogonal）的排法 ——
     深度等分欄位；葉子沿縱向等距，同一個族群的相鄰葉子距 1 單位、跨族群 2 單位（ECharts 預設 separation）；
     父節點＝第一個與最後一個子節點的正中間。回傳 cols。*/
  function layoutClassic(S) {
    const W = S.W, H = S.H, root = S.root, chains = root.kids;
    const x0 = CFG.CL_LEFT, u = Math.max(60, (W - CFG.CL_LEFT - CFG.CL_RIGHT) / 3);
    const cols = [x0, x0 + u, x0 + 2 * u, x0 + 3 * u];
    // 先數單位：每個葉子槽位 1，跨族群多 1
    let units = 0, first = true;
    chains.forEach(c => c.kids.forEach(g => { units += (first ? 0 : 2) + (g.slots - 1); first = false; }));
    const top = CFG.CL_TOP, span = H - CFG.CL_TOP - CFG.CL_BOTTOM;
    const step = units > 0 ? span / units : 0;
    S.step = step;
    let k = 0; first = true;
    chains.forEach(c => {
      c.kids.forEach(g => {
        if (!first) k += 2; first = false;
        const y0 = top + k * step;
        k += g.slots - 1;
        const y1 = top + k * step;
        g.tx = cols[2]; g.ty = units > 0 ? (y0 + y1) / 2 : H / 2;
        // 經典版：族群直徑 8＋22×√佔比；盤後／無資料 6
        g.r = g.stale || g.nodata ? 3 : 4 + 11 * Math.sqrt(g.rt);
        g.kids.forEach((lf, i) => {
          lf.tx = cols[3]; lf.ty = y0 + i * step;
          // 經典版：葉子直徑 max(6, 族群公式 × 0.62)
          lf.r = lf.stale ? 2.5 : Math.max(3, (8 + 22 * Math.sqrt(lf.rt)) * 0.31);
        });
      });
      c.tx = cols[1];
      c.ty = c.kids.length ? (c.kids[0].ty + c.kids[c.kids.length - 1].ty) / 2 : H / 2;
    });
    root.tx = cols[0];
    root.ty = chains.length ? (chains[0].ty + chains[chains.length - 1].ty) / 2 : H / 2;
    root.r = 13;                                         // 經典版根節點 symbolSize 26
    /* ★ 2026-09-26 改前→改後：產業鏈 直立細條（高＝出發線寬加總、寬 4）→ **圓點節點**（Andy 圖三：不要直條）。
       半徑 6～12 依佔比平方根（比根節點 13 小一號、和最大的族群差不多），線一律從圓心出去（見 buildElbow）。*/
    chains.forEach(c => {
      c.r = c.stale ? 4 : 6 + 6 * Math.sqrt(c.rt);
      c.hh = 0; c.cw = 0;
    });
    S.cols = cols;
    return cols;
  }

  function layout(S) {
    const W = S.W, H = S.H, root = S.root, chains = root.kids;
    const padT = 16, padB = 14;
    const cols = S.classic ? layoutClassic(S) : layoutTopo(S, W, H, root, chains, padT, padB);
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
    if (S.classic) { S.linkList.forEach(e => { e.y0 = 0; }); return; }   // 直角樹：兄弟共用一根幹線，一律從父節點圓心出發
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
  function buildCurve(e) {
    const a = e.from, b = e.to;
    const x0 = a.x + (a.lv === 1 ? 3 : a.r * 0.4), y0 = a.y + (e.y0 || 0), x1 = b.x - (b.lv === 1 ? 3 : b.r * 0.6), y1 = b.y;
    const dx = x1 - x0;
    const P = e.p = [x0, y0, x0 + dx * CFG.CURVE_K, y0, x1 - dx * CFG.CURVE_K, y1, x1, y1];
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
  function curves(S) { ports(S); S.linkList.forEach(S.classic ? e => buildElbow(S, e) : buildCurve); }

  /* ★ 2026-09-26 經典光纖的直角樹（Andy 圖四）：分叉點 x 一層一個（同層所有父節點共用同一個比例），
     靠父節點那側、要讓開父節點的標籤：x ＝ 那一層標籤最右緣 ＋ 10（取 8px 格，換日時不會每天抖 1～2px），
     夾在兩欄間距的 40%～62%。標籤比 62% 還長（窄桌機）時幹線從標籤底下穿過去（標籤有墊底色，讀得到）。
     只在「版面真的重排」時算（layoutAndDraw／drawStill），補間中每幀重排百分比不重算，幹線不會跟著抖。*/
  function trunkX(S) {
    const cols = S.cols || [];
    S.trunk = [0, 1, 2].map(lv => {
      const pc = cols[lv], cc = cols[lv + 1];
      if (!isFinite(pc) || !isFinite(cc)) return NaN;
      const gap = cc - pc;
      let right = pc;
      S.order.forEach(n => { if (n.lv === lv && n.lab) right = Math.max(right, n.lab.x + n.lab.w); });
      right = Math.ceil((right + 10) / 8) * 8;
      return Math.max(pc + gap * CFG.EL_FRAC_MIN, Math.min(pc + gap * CFG.EL_FRAC_MAX, right));
    });
  }
  /* 一條邊＝水平 → 垂直 → 水平（兩個轉角各一段小圓弧），再做等弧長查表（粒子沿弧長等速走）。
     起點＝父節點圓心（圓點畫在上層會蓋住），終點＝子節點左緣；新長出來的節點補間中 x 還沒到欄位時退化成直線。*/
  function buildElbow(S, e) {
    const a = e.from, b = e.to;
    const x0 = a.x, y0 = a.y, x1 = b.x - (b.r || 3) * 0.6, y1 = b.y;
    let xb = S.trunk && isFinite(S.trunk[a.lv]) ? S.trunk[a.lv] : (x0 + x1) / 2;
    const dy = y1 - y0, sg = dy >= 0 ? 1 : -1, ady = Math.abs(dy);
    const straight = x1 - x0 < 8 || ady < 0.5;
    xb = Math.max(x0 + 2, Math.min(x1 - 2, xb));
    const rad = straight ? 0 : Math.max(0, Math.min(CFG.EL_RAD, ady / 2, xb - x0, x1 - xb));
    e.el = { x0, y0, xb, y1, x1, rad, straight };
    e.p = null;
    // 原始折線（轉角圓弧各取 8 點）
    const px = [x0], py = [y0];
    if (straight) { px.push(x1); py.push(y1); }
    else {
      px.push(xb - rad); py.push(y0);
      for (let i = 1; i <= 8; i++) {                     // 轉角 1：圓心 (xb−rad, y0＋sg·rad)，由上（下）轉向垂直
        const t = i / 8 * Math.PI / 2;
        px.push(xb - rad + Math.sin(t) * rad); py.push(y0 + sg * rad - sg * Math.cos(t) * rad);
      }
      px.push(xb); py.push(y1 - sg * rad);
      for (let i = 1; i <= 8; i++) {                     // 轉角 2：圓心 (xb＋rad, y1−sg·rad)，由垂直轉回水平
        const t = i / 8 * Math.PI / 2;
        px.push(xb + rad - Math.cos(t) * rad); py.push(y1 - sg * rad + sg * Math.sin(t) * rad);
      }
      px.push(x1); py.push(y1);
    }
    const N = px.length - 1, cum = new Float32Array(N + 1);
    for (let i = 1; i <= N; i++) cum[i] = cum[i - 1] + Math.hypot(px[i] - px[i - 1], py[i] - py[i - 1]);
    const L = cum[N] || 1, M = 128;
    const xs = e.xs && e.xs.length === M + 1 ? e.xs : new Float32Array(M + 1);
    const ys = e.ys && e.ys.length === M + 1 ? e.ys : new Float32Array(M + 1);
    const nx = e.nx && e.nx.length === M + 1 ? e.nx : new Float32Array(M + 1);
    const ny = e.ny && e.ny.length === M + 1 ? e.ny : new Float32Array(M + 1);
    let j = 0;
    for (let i = 0; i <= M; i++) {
      const s = L * i / M;
      while (j < N - 1 && cum[j + 1] < s) j++;
      const f = Math.max(0, Math.min(1, (s - cum[j]) / ((cum[j + 1] - cum[j]) || 1)));
      xs[i] = px[j] + (px[j + 1] - px[j]) * f; ys[i] = py[j] + (py[j + 1] - py[j]) * f;
    }
    for (let i = 0; i <= M; i++) {
      const p0 = Math.max(0, i - 1), p1 = Math.min(M, i + 1), tx = xs[p1] - xs[p0], ty = ys[p1] - ys[p0], l = Math.hypot(tx, ty) || 1;
      nx[i] = -ty / l; ny[i] = tx / l;
    }
    Object.assign(e, { L, M, xs, ys, nx, ny });
  }
  function traceElbow(g, e) {
    const q = e.el; g.beginPath(); g.moveTo(q.x0, q.y0);
    if (q.straight) { g.lineTo(q.x1, q.y1); return; }
    g.arcTo(q.xb, q.y0, q.xb, q.y1, q.rad);
    g.arcTo(q.xb, q.y1, q.x1, q.y1, q.rad);
    g.lineTo(q.x1, q.y1);
  }

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
  /* ★ 2026-09-26 經典光纖的粒子（Andy 圖五／原型）：白色核心＋線色光暈。
     光暈用放射漸層畫（不是 shadowBlur），核心的 shadowBlur 只在這裡畫一次（≤ 6px）。
     淺色主題：白核心在淺底上會變成一個洞 —— 核心改成加深的同色、外面一圈細白邊，光暈透明度降一半。*/
  function spriteEl(S, color) {
    const R = 2.4, H = R * 3.4, size = Math.ceil((H + 2) * 2);
    const c = document.createElement('canvas'); c.width = c.height = Math.ceil(size * S.DPR);
    const g = c.getContext('2d'), m = c.width / 2, k = S.DPR;
    const gr = g.createRadialGradient(m, m, 0, m, m, H * k);
    gr.addColorStop(0, rgba(color, S.pal.dark ? 0.62 : 0.34));
    gr.addColorStop(0.45, rgba(color, S.pal.dark ? 0.22 : 0.12));
    gr.addColorStop(1, rgba(color, 0));
    g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
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
  /* 節點外光環：放射漸層（中心不透明、邊緣淡出），碰撞激發時放大到 r＋8×hitFlash。不用 shadowBlur。*/
  function haloEl(S, color) {
    const H = 32, c = document.createElement('canvas'); c.width = c.height = Math.ceil(H * 2 * S.DPR);
    const g = c.getContext('2d'), m = c.width / 2;
    const gr = g.createRadialGradient(m, m, 0, m, m, m);
    gr.addColorStop(0, rgba(color, 1)); gr.addColorStop(0.5, rgba(color, 0.55)); gr.addColorStop(1, rgba(color, 0));
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
    if (S.classic) return drawBaseElbow(S);
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

  /* ★ 2026-09-26 經典光纖的底圖：直角樹的雙層光纖（Andy 原型：外層寬而淡的光暈管＋內層細而亮的芯）。
     三筆：① 外光暈管 寬 w×2.2＋4（原型 ×3.2；最粗線 13px 時會到 42px、兄弟一疊就是一大片泛光，壓到 ×2.2）、
     alpha 0.07；② 線身 寬 w（探針量的線寬就是這個，粗細對比照舊）；③ 芯 寬 w×0.3、往白色混 55%、較亮。
     兄弟共用幹線，所以靠近父節點那段會疊得比較亮 —— 那段本來就是「錢還沒分出去」的總流量，亮是對的。*/
  function drawBaseElbow(S) {
    const g = S.gB, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    g.lineCap = 'round'; g.lineJoin = 'round';
    // 先畫所有外光暈，再畫線身，最後畫芯 —— 不然後畫的光暈會蓋在先畫的芯上，芯看起來斷斷續續
    const pass = (fn) => S.linkList.forEach(e => {
      if (!e.el) return;
      const k = Math.min(fadeOf(S, e.from), fadeOf(S, e.to));
      const col = e.dead && !e.to.dim ? P.ink3 : e.hue || e.to.hue;
      fn(e, k, col);
    });
    g.setLineDash([]);
    pass((e, k, col) => {
      if (e.dead) return;
      traceElbow(g, e); g.strokeStyle = rgba(col, (P.dark ? 0.07 : 0.06) * e.al * k);
      g.lineWidth = e.w * 2.2 + 4; g.stroke();
    });
    pass((e, k, col) => {
      traceElbow(g, e); g.setLineDash(e.dashed ? [4, 3] : []);
      g.strokeStyle = rgba(col, (e.dead ? 0.35 : (P.dark ? 0.58 : 0.5) * e.al) * k);
      g.lineWidth = e.w; g.stroke();
    });
    g.setLineDash([]);
    pass((e, k, col) => {
      if (e.dead || e.dashed || e.w < 2) return;
      traceElbow(g, e);
      g.strokeStyle = P.dark ? rgba(mixW(col, 0.55), 0.85 * e.al * k) : rgba(col, 0.9 * e.al * k);
      g.lineWidth = Math.max(0.8, e.w * 0.3); g.stroke();
    });
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
  /* 經典版面的標籤：節點右邊 7px 的描邊文字（經典版 label.position 'right'、distance 7、
     textBorder 3px 面板色），不畫膠囊底。右邊界＝下一欄節點左邊 8px；代表股寬度上限 120px。
     放不下只截名稱，數字永遠完整（全名在提示框）。n.lab 的框＝字實際佔的範圍（驗收量重疊用）。*/
  function measureLabelsClassic(S) {
    const g = S.gL, W = S.W, cols = S.cols;
    S.order.forEach(n => {
      const parts = partsOf(S, n).map(p => ({ ...p }));
      const lines = [[]];
      parts.forEach(p => { if (p.t[0] === '\n') { lines.push([]); p.t = p.t.slice(1); } lines[lines.length - 1].push(p); });
      const x = n.tx + n.r + CFG.CL_LABEL_GAP;           // 2026-09-26 改前 產業鏈（直條）＋2 → 改後 一律節點半徑（產業鏈也是圓了）
      const nextX = n.lv === 0 ? cols[1] - 10 : n.lv === 1 ? cols[2] - 12 : n.lv === 2 ? cols[3] - 10 : W - 4;
      const maxW = n.lv === 3 ? Math.min(CFG.CL_LEAF_LABEL_W, W - 4 - x) : Math.max(40, nextX - x);
      let bw = 0;
      lines.forEach(line => {
        line.forEach(p => { S.font(g, p.fs, p.w); p.pw = mw(g, p.t); });
        let lw = line.reduce((a, p) => a + p.pw, 0);
        const nm = line.find(p => p.name);
        if (lw > maxW && nm) {
          const cs = Array.from(nm.t);
          S.font(g, nm.fs, nm.w);
          for (let k = cs.length - 1; k >= 1 && lw > maxW; k--) {
            nm.t = cs.slice(0, k).join('') + '…';
            const w2 = mw(g, nm.t); lw = lw - nm.pw + w2; nm.pw = w2;
          }
        }
        line.w = lw; bw = Math.max(bw, lw);
      });
      const fs = Math.max(...lines[0].map(p => p.fs));
      const lh = 15, bh = fs + (lines.length - 1) * lh;     // 字框高＝字級（多行時每行 15px，經典版 lineHeight）
      n.lab = { lines, x, y: n.ty - bh / 2, w: bw, h: bh, fs };
    });
  }
  function drawLabelsClassic(S) {
    const g = S.gL, P = S.pal;
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    /* 描邊寬：經典版是 3（textBorderWidth），但這裡壓在底下的是 1～13px 的發光光纖，3 會被粗線吃掉、
       字邊糊成一團 —— 加到 4.5（字外緣約 2px 面板色），仍然是「描邊文字」而不是膠囊底。*/
    g.textBaseline = 'middle'; g.lineJoin = 'round'; g.lineWidth = 4.5;
    g.strokeStyle = P.panel;
    S.order.forEach(n => {
      const B = n.lab; if (!B) return;
      const ox = n.x - n.tx, oy = n.y - n.ty;
      // 壓暗規則和經典版一樣：被篩掉的 0.35、滑過別條路徑時 0.25（經典版 blur.label.opacity）
      g.globalAlpha = n.dim ? 0.35 : (related(S, n) ? (n.stale || n.nodata ? 0.55 : 1) : 0.25);
      /* 產業鏈與族群的標籤正好壓在往下一層分出去的光纖上（線從節點中心出發、前 150px 幾乎水平），
         只靠描邊時字縫之間還是看得到發光線、讀起來很吵 —— 墊一層半透明面板色（無邊框、不是膠囊），
         看起來仍是「線上的描邊文字」，但字讀得出來。代表股在最右欄、底下沒有線，不墊。根節點的字壓在主幹上，一起墊。*/
      if (n.lv <= 2) {                                    // 根節點的字也壓在主幹上，一起墊
        /* 2026-09-26 改前 0.62／0.7 → 改後 0.84／0.86：直角樹的水平段正好從標籤底下穿到幹線，
           多了一條亮芯之後 0.62 的墊底會讓字縫裡透出一條亮線（字讀起來像被劃掉）*/
        g.fillStyle = rgba(P.panel, P.dark ? 0.84 : 0.86);
        g.beginPath();
        if (g.roundRect) g.roundRect(B.x + ox - 3, B.y + oy - 2, B.w + 6, B.h + 4, 3); else g.rect(B.x + ox - 3, B.y + oy - 2, B.w + 6, B.h + 4);
        g.fill();
      }
      B.lines.forEach((line, li) => {
        let cx = B.x + ox;
        const cy = B.y + oy + B.fs / 2 + li * 15 + 0.5;
        line.forEach(p => {
          S.font(g, p.fs, p.w);
          g.strokeText(p.t, cx, cy);                        // 面板色描邊：壓在線上也讀得到（經典版 textBorder）
          g.fillStyle = p.c; g.fillText(p.t, cx, cy);
          cx += p.pw;
        });
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
    if (Math.random() < CFG.RP_P && S.ripples.length < CFG.RP_MAX && now - (n.rpLast || -1e9) >= CFG.RP_COOL) {
      n.rpLast = now;
      S.ripples.push({ n, r: n.r, max: n.r + (n.lv === 3 ? CFG.RP_GROW_LEAF : CFG.RP_GROW), a: CFG.RP_A0 });
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
      S.linkList.forEach(e => { if (e.dead || !e.L) return; const v = (18 + 132 * e.spdK) * sc; want += e.rate * e.L / v; });
      if (want > CFG.CL_P_BUDGET) kR = CFG.CL_P_BUDGET / want;
    }
    S.kRate = kR;
    S.linkList.forEach(e => {
      if (e.dead || !e.L) return;
      e.v = (18 + 132 * e.spdK) * sc;                       // px/秒
      /* 每條活著的線「至少一顆在線上」：發車間隔不超過走完全程的時間 */
      const rate = Math.max(e.rate * kR, e.v / e.L * 1.05); e.er = rate;   // 實際發車率（驗收量通過率用）
      e.acc += rate * dt;
      while (e.acc >= 1) { e.acc -= 1; spawnOn(S, e, Math.random() * e.v * dt); }
    });
    const parts = S.parts;
    for (let i = parts.length - 1; i >= 0; i--) {
      const p = parts[i], e = p.e;
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
        rp.r += CFG.RP_STEP * k; rp.a -= CFG.RP_FADE * k;
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
        const a0 = p.a * e.al * Math.min(fadeOf(S, e.from), fadeOf(S, e.to));
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

  /* ★ 2026-09-26 經典光纖的節點與震波（Andy 圖五／原型）：
       · 震波：1.2px 細環，r → r＋26、alpha 0.85 遞減，顏色＝節點色（產業鏈色，不是紅綠）
       · 節點：常駐淡底 r＋2（alpha 0.25，靜態不脈動）→ 微光 → 碰撞外光環（r＋8×hitFlash、alpha hitFlash×0.6，
         放射漸層小圖，不用 shadowBlur）→ 實心核心 → hitFlash > 0.3 起核心漸漸轉白（0.3～0.7 線性，不會一下跳白）
       · 標籤變亮：最上層 ftglow 畫布把激發中節點的**名稱**用亮色再描一次（alpha 跟著 hitFlash），
         其餘字（%、▲▼）不動 —— 漲跌色不會被沖淡。
     still（動畫關／減少動態）：不畫震波、不激發、ftglow 清空，只剩靜態的點。*/
  function drawNodesEl(S, g, P, still) {
    if (!still && S.ripples.length) {
      g.lineWidth = 1.2;
      S.ripples.forEach(rp => {
        const n = rp.n;
        g.globalAlpha = Math.max(0, rp.a) * (P.dark ? 1 : 0.75) * fadeOf(S, n);
        g.strokeStyle = n.stale || n.nodata ? P.ink3 : n.dot;
        g.beginPath(); g.arc(n.x, n.y, rp.r, 0, Math.PI * 2); g.stroke();
      });
    }
    S.order.forEach(n => {
      const f = fadeOf(S, n), off = n.stale || n.nodata, col = off ? P.ink3 : n.dot;
      const r = n.r, hf = still ? 0 : (n.hf || 0);
      // 常駐淡底
      g.globalAlpha = 0.25 * f; g.fillStyle = col;
      g.beginPath(); g.arc(n.x, n.y, r + 2, 0, Math.PI * 2); g.fill();
      const sp = S.sprites[n.hue], ha = S.halos && S.halos[n.hue];
      if (sp && !off) {                                  // 常駐微光（粒子小圖放大，和以前一樣）
        const gs = sp.size * (r / sp.R) * 0.42;
        g.globalAlpha = (P.dark ? 0.4 : 0.22) * f; g.drawImage(sp.c, n.x - gs / 2, n.y - gs / 2, gs, gs);
      }
      if (hf > 0.01 && ha && !off) {                     // 碰撞外光環：r＋8×hitFlash
        const R = (r + 8 * hf) * 1.6;
        g.globalAlpha = hf * (P.dark ? 0.6 : 0.4) * f;
        g.drawImage(ha.c, n.x - R, n.y - R, R * 2, R * 2);
      }
      g.globalAlpha = f * (off ? 0.55 : 1);
      g.fillStyle = rgba(col, 0.62 + 0.38 * Math.max(n.rt || 0, n.lv <= 1 ? 1 : 0.25));
      g.beginPath(); g.arc(n.x, n.y, r, 0, Math.PI * 2); g.fill();
      const wz = Math.max(0, Math.min(1, (hf - 0.3) / 0.4));
      if (wz > 0) {                                       // 核心轉白（淺色主題：轉成淡色＋同色邊，不會變成一個洞）
        g.globalAlpha = wz * f;
        g.fillStyle = P.dark ? '#ffffff' : mixW(col, 0.72);
        g.beginPath(); g.arc(n.x, n.y, r * 0.78, 0, Math.PI * 2); g.fill();
      }
      if (n.picked || (n.lv === 2 && n.open)) {         // 你點開的：亮一圈細邊
        g.globalAlpha = f; g.strokeStyle = P.ink2; g.lineWidth = 1.3;
        g.beginPath(); g.arc(n.x, n.y, r + 2.5, 0, Math.PI * 2); g.stroke();
      }
    });
    g.globalAlpha = 1;
    drawGlowLabels(S, still);
  }
  function drawGlowLabels(S, still) {
    const g = S.gG, P = S.pal;
    const hot = still ? [] : S.order.filter(n => (n.hf || 0) > 0.06 && n.lab && !n.dim);
    if (!hot.length && !S.glowDirty) return;             // 上一幀沒畫、這一幀也沒得畫：連清都不用清
    g.setTransform(S.DPR, 0, 0, S.DPR, 0, 0); g.clearRect(0, 0, S.W, S.H);
    S.glowDirty = hot.length > 0;
    if (!hot.length) return;
    g.textBaseline = 'middle';
    hot.forEach(n => {
      const B = n.lab, p = B.lines[0] && B.lines[0][0]; if (!p || !p.name) return;
      g.globalAlpha = Math.min(1, n.hf) * (P.dark ? 0.75 : 0.6) * (related(S, n) ? 1 : 0.3);
      S.font(g, p.fs, p.w);
      g.fillStyle = P.dark ? '#ffffff' : P.ink;
      g.fillText(p.t, B.x + (n.x - n.tx), B.y + (n.y - n.ty) + B.fs / 2 + 0.5);
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
    const dt = Math.min(0.05, Math.max(0, (now - S.lastT) / 1000)); S.lastT = now;
    if (S.tween) stepTween(S, now);
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
    S.ripples = []; S.tween = null; S.twE = 1;
    measureLabels(S); if (S.classic) trunkX(S); curves(S); drawBase(S); drawLabels(S); drawFx(S, performance.now(), true);
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
    /* 標籤變亮那張（ftglow）只有經典光纖用得到；拓撲版縮成 1×1 藏起來，不白佔一張全尺寸 HiDPI 畫布的記憶體與合成 */
    S.cvGlow.style.display = S.classic ? '' : 'none';
    if (!S.classic) { if (S.cvGlow.width !== 1) { S.cvGlow.width = 1; S.cvGlow.height = 1; } S.glowDirty = false; }
    (S.classic ? [S.cvBase, S.cvFx, S.cvLab, S.cvGlow] : [S.cvBase, S.cvFx, S.cvLab]).forEach(c => {
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
    S.host.style.height = (S.H + CFG.BAR_H) + 'px';          // 高度先定（版面不會等圖畫完才長高）
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
    if (S.classic) trunkX(S);                               // 直角樹的分叉點 x（要等標籤量完才知道要讓開多少）
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
  const spriteKey = (S) => S.DPR + '|' + S.pal.dark + '|' + (S.classic ? 'el' : 'tp') + '|' + [...new Set(S.order.map(n => n.hue))].join(',');

  /* ---- 滑過／點擊 ---- */
  function pickAt(S, mx, my) {
    let best = null, bd = 1e9;
    for (const n of S.order) {
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
    if (x + tw > S.W - 4) x = mx - tw - 14;
    if (y + th > S.H - 4) y = my - th - 12;
    t.style.left = Math.max(4, x) + 'px'; t.style.top = Math.max(4, y) + 'px';
  }
  function hideTip(S) { S.tipEl.classList.remove('on'); }
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
      if (n) { showTip(S, n, mx, my); setHover(S, n.lv === 0 ? null : n); }
      else { hideTip(S); setHover(S, null); }
    });
    cv.addEventListener('pointerleave', () => { hideTip(S); setHover(S, null); cv.classList.remove('hot'); });
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
    paintMotionBtn(S);
    buildModel(S);
    layoutAndDraw(S, true);
    return S.H + CFG.BAR_H;
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
      W: S.W, H: S.H, total: S.H + CFG.BAR_H, dpr: S.DPR, motion: S.motion, running: !!S.raf,
      reduce: !!reduceMQ.matches, dark: !!S.pal.dark,
      nodes: S.order.map(n => ({ key: n.key, lv: n.lv, name: n.name, x: Math.round(n.x), y: Math.round(n.y),
        cx: Math.round(b.left + n.x), cy: Math.round(b.top + n.y), r: +(n.r || 0).toFixed(1), dim: !!n.dim,
        stale: !!n.stale, open: !!n.open, picked: !!n.picked, rest: !!n.rest, nodata: !!n.nodata,
        parent: n.parent ? n.parent.key : null,
        value: n.d ? n.d.value : null,
        // ★ 2026-09-26：節點形狀（經典光纖一律圓；拓撲版產業鏈是直條）、碰撞激發讀值、節點色
        shape: (S.classic || n.lv !== 1) ? 'circle' : 'bar', hh: +(n.hh || 0).toFixed(1),
        hf: +(n.hf || 0).toFixed(3), dot: n.dot,
        text: n.lab ? n.lab.lines.map(l => l.map(p => p.t).join('')).join(' / ') : '',
        chg: n.lab ? (n.lab.lines[0].find(p => p.chg) || {}).chg || null : null,
        chgColor: n.lab ? (n.lab.lines[0].find(p => p.chg) || {}).c || null : null,
        lab: n.lab ? { x: Math.round(n.lab.x), y: Math.round(n.lab.y), w: Math.round(n.lab.w), h: Math.round(n.lab.h) } : null })),
      links: S.linkList.map(e => ({ key: e.key, lv: e.lv, w: +e.w.toFixed(2), dead: !!e.dead,
        n: S.parts.filter(p => p.e === e).length, rate: +e.rate.toFixed(2), v: +(e.v || 0).toFixed(1), pr: +e.pr.toFixed(2),
        al: +(e.al || 0).toFixed(3), er: +(e.er || 0).toFixed(3), rt: +(e.rt || 0).toFixed(4),
        from: e.from.key, to: e.to.key,
        // ★ 2026-09-26 直角樹：路徑的五個特徵點（起點、分叉點 x、終點）與查表偏離理想「水平-垂直-水平」折線的最大距離
        el: e.el ? [e.el.x0, e.el.y0, e.el.xb, e.el.y1, e.el.x1, e.el.rad].map(v => +v.toFixed(1)) : null,
        elStraight: !!(e.el && e.el.straight), elDev: e.el ? +elbowDev(e).toFixed(2) : null })),
      particles: S.parts.length, offCurve: off, maxOff: +maxOff.toFixed(2), leftStray: stray, rootX: Math.round(rootX), sample,
      fps: +fps.toFixed(1), frames: m.frames, avgCostMs: m.frames ? +(m.cost / m.frames).toFixed(3) : 0,
      maxBlur: m.maxBlur, minFont: m.minFont === Infinity ? null : m.minFont, spawned: m.spawned,
      layout: S.classic ? 'classic' : 'topo',
      firstDrawMs: m.firstDrawMs == null ? null : +m.firstDrawMs.toFixed(1),
      lastDrawMs: m.lastDrawMs == null ? null : +m.lastDrawMs.toFixed(1),
      warmMs: m.warmMs == null ? null : +m.warmMs.toFixed(1),
      pending: !!S.pendingDraw,
      ripples: S.ripples.length, rpMax: CFG.RP_MAX, rpPeak: m.rpPeak, rpMade: m.rpMade, hits: m.hits,
      trunk: (S.trunk || []).map(v => +(+v).toFixed(1)), cols: (S.cols || []).map(v => +(+v).toFixed(1)),
      glowCanvas: !!S.cvGlow.isConnected,
      tweening: !!S.tween, twE: +(S.twE == null ? 1 : S.twE).toFixed(3), twLin: !!(S.tween && S.tween.lin), hover: S.hover ? S.hover.key : null,
    };
  }
  /* 查表的每一點到「水平 → 垂直 → 水平」理想折線的最大距離（圓角會偏一點點：半徑 7 時約 2px）*/
  function elbowDev(e) {
    const q = e.el;
    const segs = q.straight ? [[q.x0, q.y0, q.x1, q.y1]]
      : [[q.x0, q.y0, q.xb, q.y0], [q.xb, q.y0, q.xb, q.y1], [q.xb, q.y1, q.x1, q.y1]];
    let worst = 0;
    for (let i = 0; i <= e.M; i++) {
      const x = e.xs[i], y = e.ys[i];
      let best = 1e9;
      segs.forEach(([ax, ay, bx, by]) => {
        const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
        const t = l2 ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l2)) : 0;
        best = Math.min(best, Math.hypot(x - ax - dx * t, y - ay - dy * t));
      });
      worst = Math.max(worst, best);
    }
    return worst;
  }
  /* 驗收用：一口氣讓 k 顆粒子「到站」（亂數挑活著的節點），驗震波上限；只在經典光纖有意義 */
  function burst(host, k) {
    const S = host && host._ft; if (!S || !S.classic) return null;
    const live = S.order.filter(n => n.lv > 0 && !n.dim);
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
