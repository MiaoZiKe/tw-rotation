/* ============================================================================
   積木 `stock.mtf`　個股頁「AI 分析」（多週期＋籌碼＋基本＋消息，規則式自動判讀）　法遵 🔴
   ----------------------------------------------------------------------------
   Andy 2026-09-26（#stock/3026 禾伸堂）：「觀望部分需要標示 AI 分析，並且需要說明原因；
   AI 分析是可以收納的選項，與多週期合併，裡面分析需要分不同時間週期的說明（只到週級別）
   → 這是技術面，需要有籌碼面、基本面、消息面看法」。
   Andy 2026-09-27（#stock/2618，紅框圈標題列右半邊的空白）：
   「AI 分析 需要在右上角出現，並且技術面 籌碼面 基本面 消息面 用標籤頁切換」。

   ── 改前（09-26 晚）→ 改後（09-27）──────────────────────────────────────────
   改前：右上只有一行結論＋四個小標籤＋「看分析 ↓」；完整分析是 K 線與分頁之間一張很長的卡（#aiCard），
         四個面向上下排開，要一路往下捲。標題列右半邊大半是空的。
   改後：整塊 AI 分析（#skAi）住進 K 線卡的右上角：
         · 第一列：「AI 分析」＋「規則式自動判讀，非投資建議」＋「?」＋收合鈕
         · 第二列：結論（條件未齊／條件成立／偏空＋一句帶數字的原因，#skAiLine）
         · 第三列：四顆標籤「技術面｜技術面訊號｜基本面｜消息面」（09-28 籌碼面換成技術面訊號），每顆附判讀小字，一次只顯示一個面向
         · 內容區（#aiBody）固定高度、超過就在區內捲動 —— 不撐高標題列、不把 K 線往下推
         K 線與分頁之間那張長卡、「看分析 ↓／展開分析 ▾」跳轉鈕一起拿掉。

   版面（為什麼是「右欄跨兩列」）：
     K 線卡夠寬時（≥ WIDE px，ResizeObserver 量卡片本身，不看視窗 —— 開關右側事件欄、⤢ 寬版都會變寬窄），
     卡片改成兩欄格線：左欄上面是名稱／現價（#skHead）、下面是 K 線工具列（#skTools）；
     右欄是 #skAi，**跨這兩列**。這樣 AI 區可用的高度＝名稱區＋工具列的高度，
     工具列被擠窄時會自己折成兩行，剛好把那兩列撐高給 AI 區用，而不是整塊疊在 K 線上面。
     ★ 兩欄一路用到卡片 600px（＝桌機／平板全部寬度；只有開著右側事件欄又把視窗拉很窄才會低於它）。
       量過（2618，K 線頂端 y；改前＝09-26 版，右上一行結論）：
                     1440   1100    900    800    700
         改前         332    402    402    395    489
         單欄（舊門檻）   —      —    534    515    609   ← AI 區疊在名稱區下面，K 線多掉 120px
         兩欄（新門檻） 379    411    411    408    502   ← 左欄變窄、名稱區與工具列自己折行，AI 區吃那個高度
       所以窄卡片也走兩欄：AI 區窄到 380px 以下時（container query，量的是 AI 區自己不是視窗），
       標籤改成「面向名在上、判讀小字在下」、技術面週期列與支撐壓力改單欄，四顆標籤才排得進 300px。
     卡片 < 600 才退回單欄：AI 區排在名稱區下面、工具列上面，內容區改矮一點（見 CSS 的 --aibh）。
     手機（≤640，mobile v3 分段）：app.js 的 miaStock 把 #skAi 整個節點搬進分段用的空殼 #aiCard
     （「AI 分析」那一段），內容區不限高、不在區內捲（它自己就是一整段，捲頁面就好，不要捲中捲）。
   ★ 2026-10-02 改版（Andy #stock/3189 三張截圖，DECISIONS #293；上面量測表是改前的數字）：
     · AI 區的高度**不再由內容決定**（contain:size），格線高度只看左欄（保底 --aiH）：展開／收合左欄與 K 線一個像素都不動。
     · 兩欄中間多一條可拖的分隔線 #skSplit（存 tw.aiSplit，雙擊還原 44%），左欄最小寬＝工具列一行放得下。
     · 兩欄的門檻改成「視窗 > 820 而且卡片放得下」；≤820 上下排，內容區改成往下開的浮層（不推 K 線，進頁面收著）。
     · 現價列的五顆標籤（技術分…分 K 完整）搬到工具列（industry.js #skTags），左欄因此少一行。
     · 預設改成「只看重點」（Andy「上方的 AI 分析只寫重點」）：收合＝標題列＋一行結論（跟總覽的 briefText 同一句）＋四顆面向膠囊，
       點膠囊捲到下面「總覽」分頁的 AI 卡並切到那一面（#ovAiCard，#297）；按「展開」才看各週期細節（兩欄撐滿右欄、單欄是浮層，都不推左側）。
       保底高度改掛在分隔線上（--aiH 寫在卡片），收合時 AI 區只有內容那麼高。

   狀態（兩個 localStorage）：
     · tw.aiOpen：（#305 起不再使用）以前記內容區收合／展開。2026-10-03 拿掉「展開」鈕：K 線卡裡只剩一行結論＋四列面向判讀，
       點一列捲到總覽 AI 卡（完整版在那裡）；手機 #aiCard 裡內容區一律打開。
       收合時按標籤：K 線卡裡（桌機）＝捲到下面「總覽」的 AI 卡並切到那一面（#297）；手機（#aiCard）＝展開並切到那一面。
     · tw.aiTab：選中的面向（tech／sig／fund／news），重新整理後還在。沒記過＝技術面。
     · tw.aiSplit（2026-10-02）：兩欄時右欄占「左欄＋右欄」的比例（0～1），拖分隔線時寫、雙擊分隔線刪掉＝回預設。
     ⚠ 單欄（≤820）的浮層不讀也不寫 tw.aiOpen：浮層是點了才開的，進頁面一律收著。

   ⚠ 誠實標示：內容全部來自 payload 的 `analysis`（pipeline/compute/analysis.py），
     是寫死的規則＋數字組出來的，**不是大型語言模型**。標題寫「AI 分析」是 Andy 要的字樣，
     旁邊一定緊接「規則式自動判讀，非投資建議」，「?」裡寫清楚依哪些規則與資料。
     所有文字是描述式／條件式（「目前…」「若…則…」），不寫指示性的交易用語（pytest 在擋）。

   規則（跟 stock_signal.js 同一套積木規矩）：
     · 一份輸入：個股頁 JSON（讀 analysis、verdict、mtf.summary 三個欄位，其餘不讀）
     · 出口：html(pg, fmt) → 整塊 HTML；mount(pg, host, fmt) → 畫進 host（#skAi）並掛事件
     · 這支檔不載入時，industry.js 不畫 #skAi／#aiCard，其他照常（可以單獨關閉）
   ============================================================================ */
(function () {
  'use strict';

  const KEY = 'tw.aiOpen';
  const TAB_KEY = 'tw.aiTab';
  /* ★ 2026-10-02（Andy #stock/3189，DECISIONS #293）兩欄的判準改了：
     改前：卡片 ≥ 600px 就兩欄（800 寬也是兩欄，左欄 400px，現價列與工具列各折兩三行）。
     改後：① 視窗 > NARROW（820）才兩欄 —— ≤820 照 Andy 說的「上下排列」，分隔線也不出現；
           ② 卡片要放得下「左欄最小寬（工具列一行放得下）＋分隔線＋右欄 AI_MIN」，放不下（例如右側事件欄開著）一樣退單欄。
     右欄寬度＝tw.aiSplit（右欄占「左＋右」的比例，拖分隔線時寫）；沒存過＝AI_DEF（跟改前的 44% 一樣，沒拖過的人看不出差別）。*/
  const SPLIT_KEY = 'tw.aiSplit';
  const NARROW = 820;
  const AI_MIN = 300;      // 右欄最窄：四顆標籤疊成兩行後每顆約 70px 放得下
  const AI_DEF = 0.44;
  const SPLIT_W = 20;      // 分隔線那一欄的寬（跟 CSS grid-template-columns 第二欄同一個數字）
  const LEFT_FLOOR = 360;  // 左欄最小寬的下限（現價＋漲跌＋即時徽章一行約 330px）
  const TAG_MIN = 46;      // 工具列標籤區最窄＝「⋯ N」那一顆（industry.js fitTags；CSS .sktmore 寬度不超過這個數）
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* ★ 2026-09-28（Andy：「將 "AI分析" 內容替換掉 籌碼 -> 技術面訊號」）：第二顆標籤「籌碼面」換成「技術面訊號」。
     理由：籌碼已經拆成個股頁下方「法人｜資券｜大戶／散戶」三個獨立分頁，AI 區再放一份籌碼摘要是重複；
     換成總覽「技術面訊號」卡那九顆燈（均線、結構、RSI、KD、MACD、乖離、BOS、CHoCH、假跌破），燈號從 StockSignal.lights() 拿，兩處永遠一致。
     payload 的 analysis.facets.chip 照舊產出（其他地方可能在讀），這裡不再顯示。
     舊的 tw.aiTab＝'chip' 讀不到 → readTab 退回技術面。*/
  /* ★ 2026-10-04（Andy：「技術已經有了，為何還多一個技術面訊號」「這邊需要的是 技術面、籌碼面、基本面、消息面」）：
     ① 「技術面訊號」併進「技術面」：點技術面＝原本的技術面內容＋九顆訊號燈那一列（均線／結構／RSI／KD／MACD／乖離／BOS／CHoCH／假跌破），
        徽章照舊是技術面的偏多／偏空，旁邊附燈號計數（5多0空）—— 兩個都在講技術，分成兩顆只是讓人多猜一次差在哪。
     ② 第二顆換回「籌碼面」：判讀直接用 payload 的 analysis.facets.chip（pipeline/compute/analysis.py chip_facet，規則見 chipHTML 上方註解），
        前端只補兩條「已在頁面上」的數字（自營商 20 日、當沖率／融券），不改它的判讀、不加新的資料抓取。
     第三欄是簡稱：寬度不夠時（容器查詢）改顯示「技術／籌碼／基本／消息」。舊的 tw.aiTab＝'sig' 讀不到 → 退回技術面。*/
  const FACETS = [['tech', '技術面', '技術'], ['chip', '籌碼面', '籌碼'], ['fund', '基本面', '基本'], ['news', '消息面', '消息']];
  const nmHTML = (nm, sh) => `<span class="nm"><span class="nl">${nm}</span><span class="ns" aria-hidden="true">${sh}</span></span>`;
  // 紅漲綠跌：偏多用 .pos（紅）、偏空用 .neg（綠）；留意＝琥珀色
  const toneCls = (lb) => lb === '偏多' ? 'pos' : lb === '偏空' ? 'neg' : lb === '留意' ? 'warn' : '';
  const stanceCls = (s) => s === '條件成立' ? 'A' : s === '偏空' ? 'N' : 'W';   // 狀態字樣見 analysis.py ST_*（#333 改中性）

  /* ★ 2026-10-03（#305）：「展開／收合」拿掉，tw.aiOpen 不再讀寫（KEY 只留著給 _key 出口，舊驗收在清它）。
     改前 #293 的「預設收合＋換版清一次 tw.aiOpenV」一起退場。*/
  function readTab() {
    try { const v = localStorage.getItem(TAB_KEY); if (FACETS.some(f => f[0] === v)) return v; } catch (e) { /* 忽略 */ }
    return 'tech';
  }
  function saveTab(v) { try { localStorage.setItem(TAB_KEY, v); } catch (e) { /* 忽略 */ } }
  function readSplit() {
    try { const v = parseFloat(localStorage.getItem(SPLIT_KEY)); if (v > 0.05 && v < 0.95) return v; } catch (e) { /* 私密視窗 */ }
    return null;
  }
  function saveSplit(v) { try { localStorage.setItem(SPLIT_KEY, String(Math.round(v * 1000) / 1000)); } catch (e) { /* 忽略 */ } }
  function clearSplit() { try { localStorage.removeItem(SPLIT_KEY); } catch (e) { /* 忽略 */ } }
  /* AI 區現在是哪一種版面：side＝K 線卡右欄（兩欄）／stack＝K 線卡單欄（內容區是浮層）／away＝手機搬進 #aiCard。
     只有 stack 的展開收合不讀也不寫 tw.aiOpen（浮層是點了才開的東西，進頁面就攤開會蓋住工具列與 K 線）。*/
  function modeOf(host) {
    const card = document.getElementById('skChartCard');
    if (!card || host.parentElement !== card) return 'away';
    return card.classList.contains('aiside') ? 'side' : 'stack';
  }

  function css() {
    if (document.getElementById('stockAiCss')) return;
    const st = document.createElement('style');
    st.id = 'stockAiCss';
    st.textContent = `
/* ---- K 線卡兩欄（視窗 > 820、卡片放得下左欄最小寬＋分隔線＋右欄 300px 時，JS 加 .aiside）----
   三欄格線：左欄（名稱／現價／工具列／短註）｜分隔線 #skSplit（20px，可拖）｜右欄 #skAi（寬度＝--aiW，JS 算好寫進來）。
   ★ 2026-10-02（Andy #stock/3189，DECISIONS #293）：
     ① AI 區 contain:size —— **它的內容高度不參與決定格線多高**，格線高度只由左欄決定（再保底 --aiH）；
        AI 區 stretch 撐滿那個高度，內容在區內捲。展開／收合／換面向都只改 AI 區裡面，左欄與 K 線一個像素都不動。
        改前：AI 區高度＝內容高度，左欄矮（例如沒有短註、標籤搬走之後）時展開就把左欄與 K 線往下推，收合又彈回來。
     ② 分隔線可拖，拖完存 tw.aiSplit（右欄占「左＋右」的比例）；雙擊還原預設 44%。左欄最窄＝工具列一行放得下的寬度。
     ③ ≤820 不出現分隔線、改單欄上下排（見下面 :not(.aiside) 那段）。*/
#skChartCard.aiside{display:grid;grid-template-columns:minmax(0,1fr) 20px var(--aiW,44%);column-gap:0;align-items:start;
  grid-template-rows:1fr auto auto}
#skChartCard.aiside>*{grid-column:1 / -1;min-width:0}
#skChartCard.aiside>#skHead{grid-column:1;grid-row:1;align-self:start}
/* 工具列貼在左欄底部＝緊貼 K 線；AI 區保底高度比左欄高時多出來的空白落在名稱區與工具列之間，不落在工具列與 K 線之間 */
#skChartCard.aiside>#skTools{grid-column:1;grid-row:2;align-self:end}
/* 短註（此檔暫無分時資料／分時來源）住在左欄工具列下面（設計 v4 ⑤b，theme4.css 也有同一條；這裡寫一份是為了不依賴主題檔）。
   ★ 2026-10-02（#293）：兩欄時短註**固定佔一行**——只顯示一行（太長出「…」，滑過看全文、點一下展開），沒有短註時也留著那一行（看不見）。
   理由：左欄現在決定格線高度，短註「藏 ↔ 一行 ↔ 兩行」會直接推 K 線；而它是非同步變的（分時資料最多等 8 秒才知道有沒有、
   沒有就自動改日 K 換一句話）—— 驗收實測 3026 一進頁 K 線自己往上跳 18px。改前 AI 區比左欄高，把這個跳動吃掉了，所以以前看不到。
   格線第一列給 1fr：AI 區保底高度比左欄高時，多出來的空白落在名稱區與工具列之間，工具列與短註照舊貼著 K 線。*/
#skChartCard.aiside>#liveNote{grid-column:1;grid-row:3;align-self:end;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}
#skChartCard.aiside>#liveNote.open{white-space:normal;cursor:default}
#skChartCard.aiside>#liveNote[hidden]{display:block;visibility:hidden}
/* 保底高度 --aiH 掛在分隔線上（它永遠跨三列、永遠在）：格線高度＝max(左欄, --aiH)，跟 AI 區展開收合無關 */
#skChartCard.aiside>#skSplit{grid-column:2;grid-row:1 / span 3;align-self:stretch;min-height:var(--aiH,190px)}
/* 右欄不畫外框，左邊那條線由分隔線畫（拖曳的把手就是那條線） */
/* 收合（重點模式）：AI 區只有內容那麼高（標題＋一行結論＋膠囊，一定比格線矮，不會撐高格線）；
   展開：撐滿格線（stretch）＋contain:size（內容再長也不參與決定格線高度），內容區在區內捲 */
#skChartCard.aiside>#skAi{grid-column:3;grid-row:1 / span 3;align-self:start;margin-top:0;padding-left:4px}
/* 分隔線：20px 寬的拖曳區，中間畫 1px 的線；滑過／拖曳中／鍵盤聚焦變成青色、中間出現握把 */
#skSplit{display:none}
#skChartCard.aiside>#skSplit{display:block;position:relative;cursor:col-resize;touch-action:none;outline:none;min-width:0}
#skSplit::before{content:'';position:absolute;top:0;bottom:0;left:50%;width:1px;transform:translateX(-50%);background:var(--line)}
#skSplit::after{content:'';position:absolute;left:50%;top:50%;width:4px;height:30px;border-radius:2px;transform:translate(-50%,-50%);
  background:var(--ink-3);opacity:0;transition:opacity .15s}
#skSplit:hover::before,#skSplit.drag::before,#skSplit:focus-visible::before{width:2px;background:var(--cyan)}
#skSplit:hover::after,#skSplit.drag::after,#skSplit:focus-visible::after{opacity:.85;background:var(--cyan)}
/* 拖曳中：整頁游標都是 col-resize、不准選到字（滑鼠跑出分隔線外也一樣） */
body.sksplitting,body.sksplitting *{cursor:col-resize!important;user-select:none!important;-webkit-user-select:none!important}
/* 內容區高度（2026-10-02 起，#293）：兩欄時＝AI 區高度（左欄高度，保底 --aiH）扣掉標題／結論／標籤，不再是固定 132px；
   改前是「內容區保底 132px、AI 區用內容撐高格線」，左欄矮的時候展開就推 K 線（Andy 要拿掉的那個跳動）。
   單欄時內容區是浮層（見 .aibody 那段），--aibh 只剩手機以外的退路用得到。*/
/* container：AI 區自己多寬決定標籤排法（兩欄時跟著卡片寬窄變、手機搬進 #aiCard 又是另一個寬度，看視窗寬猜不準）*/
/* --aiH：兩欄時 AI 區的保底高度＝標題＋結論＋標籤的實際高度＋內容區 90px（JS sizeAi 量好寫在卡片上、由分隔線 #skSplit 的 min-height 撐住格線；190 只是量到之前的預設）。
   左欄比它高（有短註那一行時約 200px）就照左欄走、K 線不被它推；左欄比它矮時 K 線比左欄低一點，但**展開收合都是同一個位置**。*/
#skAi{--aibh:132px;display:flex;flex-direction:column;gap:5px;min-width:0;container:aibox / inline-size}
#skChartCard:not(.aiside)>#skAi{--aibh:110px;margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
/* 單欄（退路）：標題與結論併成同一列（標題｜結論｜收合），省下一整列 ≈ 25px。
   這不只是好看：工具列每往下 1px，K 線「指標 ▾」下拉在矮視窗下方的空間就少 1px ——
   少到 320px 以下它會改往上開（placePop 的判準），蓋住 AI 區。結論太長就在中間那欄自己折行。*/
#skChartCard:not(.aiside)>#skAi{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:12px;row-gap:5px;align-items:center}
#skChartCard:not(.aiside)>#skAi>.aihead{display:contents}
#skChartCard:not(.aiside)>#skAi>.aihead>h3{grid-column:1;grid-row:1}
#skChartCard:not(.aiside)>#skAi>.aisum{grid-column:2;grid-row:1}
#skChartCard:not(.aiside)>#skAi>.aitabs,#skChartCard:not(.aiside)>#skAi>.aibody{grid-column:1 / -1}
#skAi .aihead{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
#skAi .aihead h3{margin:0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:15px}
#skAi .aihead h3 small{font-size:12px;letter-spacing:-.04em;color:var(--ink-3,var(--ink-2));font-weight:400;order:2;flex-basis:100%;line-height:1.5}
#skAi .aisum{display:flex;align-items:baseline;gap:8px;min-width:0;font-size:13.5px;color:var(--ink-2);line-height:1.45}
#skAi .aisum .grade{flex:none;white-space:nowrap}
#skAi .aisum .aibrief{min-width:0}
.grade.N{background:rgba(46,229,157,.16);color:var(--fall)}
/* 四顆標籤：一列排滿、等寬；每顆＝面向名＋判讀小字 */
/* 2026-09-28：第二顆從「籌碼面」換成「技術面訊號」（名字多兩個字＋小字「4多2空」），等寬四欄在 1100 寬會溢出壓到隔壁 →
   第二欄給 1.4 倍寬；真的還是放不下時，判讀小字自己換到第二行（flex-wrap），絕不溢出按鈕。*/
/* 2026-10-04：第二顆改回「籌碼面」（跟其他三顆一樣三個字），四欄回到等寬 */
#skAi .aitabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;border-bottom:1px solid var(--line)}
/* 面向名：全名／簡稱兩份，平常顯示全名；寬度不夠的容器查詢才換簡稱（見下面 @container）*/
.aitab .nm .ns,.ovtag .nm .ns{display:none}
.aicnt{font-size:12px;font-weight:500;color:var(--ink-3);white-space:nowrap}
.aicnt.pos{color:var(--rise)} .aicnt.neg{color:var(--fall)}
#skAi .aitab{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:0 6px;min-width:0;padding:4px 4px 5px;border:0;
  border-bottom:2px solid transparent;margin-bottom:-1px;background:none;color:var(--ink-2);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
#skAi .aitab:hover{color:var(--ink)}
#skAi .aitab.on{color:var(--ink);font-weight:700;border-bottom-color:var(--cyan)}
#skAi .aitab .aitag{font-weight:500}
/* ★ 2026-10-03（Andy：「AI 分析標籤上下排列、字放大；展開功能取消，下方總覽分頁已經有完整版」，DECISIONS #305）：
   K 線卡裡（桌機兩欄／單欄）的四顆面向標籤改成**一列一個**的清單：左邊面向名、右邊判讀（偏多紅／中性灰／偏空綠／留意琥珀），字 14px。
   改前是一排 12px 的小膠囊＋最右邊「展開 ▾」：小膠囊要瞇著看，展開後的內容又跟下面總覽 AI 卡一模一樣（兩份）。
   點一列＝捲到下面「總覽」分頁的 AI 卡、切到那一面（gotoFacet，原地捲、不換頁）；右邊的「›」提示點得下去。
   K 線卡裡沒有「選中」這回事（內容區不顯示），所以 .on 不畫任何樣式。
   單欄（≤820）：四列直排會把 K 線往下推約 90px，改成 2×2（每格照樣左名右判讀）。手機（#aiCard 裡）照舊是標籤頁＋內容區。*/
#skChartCard>#skAi .aitabs{display:flex;flex-direction:column;gap:3px;border:0;margin-top:2px}
#skChartCard>#skAi .aitab{display:flex;flex-direction:row;flex-wrap:nowrap;justify-content:space-between;align-items:center;gap:10px;width:100%;
  min-height:29px;padding:3px 8px 3px 11px;margin:0;border:0;border-radius:8px;background:var(--panel-3);
  font-size:14px;font-weight:400;color:var(--ink);text-align:left;white-space:nowrap}
#skChartCard>#skAi .aitab .nm{font-size:14px;min-width:0;overflow:hidden;text-overflow:ellipsis}
#skChartCard>#skAi .aitab .aitag{margin-left:auto;font-size:14px;font-weight:600;padding:1px 9px;line-height:20px}
#skChartCard>#skAi .aitab::after{content:'›';flex:none;color:var(--ink-3);font-size:16px;line-height:1}
#skChartCard>#skAi .aitab.on{font-weight:400;border:0;color:var(--ink);background:var(--panel-3)}
#skChartCard>#skAi .aitab:hover{background:color-mix(in srgb,var(--cyan) 12%,var(--panel-3))}
#skChartCard>#skAi .aitab:hover::after{color:var(--cyan)}
#skChartCard>#skAi .aitab:focus-visible{outline:2px solid var(--focus,var(--cyan));outline-offset:1px}
/* ★ 2026-10-04（Andy：「4 個指標需要並排（同一列）」）：單欄從 2×2 改成一列四顆；放不下先縮字、再換簡稱、最後收掉燈號計數 */
#skChartCard:not(.aiside)>#skAi .aitabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px 6px}
#skChartCard:not(.aiside)>#skAi .aitab{gap:6px;padding:3px 6px 3px 9px}
#skChartCard:not(.aiside)>#skAi .aitab::after{display:none}
@container aibox (max-width:760px){
  #skChartCard:not(.aiside)>#skAi .aitab,#skChartCard:not(.aiside)>#skAi .aitab .nm,#skChartCard:not(.aiside)>#skAi .aitab .aitag{font-size:12.5px}
  #skChartCard:not(.aiside)>#skAi .aitab .aitag{padding:1px 6px}
}
@container aibox (max-width:640px){
  #skChartCard:not(.aiside)>#skAi .aitab .nl{display:none} #skChartCard:not(.aiside)>#skAi .aitab .ns{display:inline}
}
@container aibox (max-width:520px){ #skChartCard:not(.aiside)>#skAi .aitab .aicnt{display:none} }
/* 桌機（K 線卡裡）內容區一律不顯示：完整內容在下面總覽分頁的 AI 卡（手機搬進 #aiCard 之後才會用到它）*/
#skChartCard>#skAi>.aibody{display:none!important}
/* K 線卡裡的結論一律只佔一行（太長出「…」，滑過看全文；完整原因在展開後的技術面裡）。
   展開時也不換行：兩欄的保底高度是照「展開時標題＋結論＋標籤」量的，結論在 1100 寬會折成兩三行，保底就多出 40px、左欄工具列被推離價格一大段（截圖看到的）。*/
#skChartCard>#skAi .aibrief{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.aitag{padding:1px 7px;border-radius:6px;font-size:12px;background:var(--panel-3);color:var(--ink-2);white-space:nowrap}
.aitag.pos{background:rgba(255,77,109,.16);color:var(--rise)} .aitag.neg{background:rgba(46,229,157,.16);color:var(--fall)}
.aitag.warn{background:rgba(255,180,84,.16);color:var(--amber)}
/* 內容區：固定高度、區內捲動（不撐高標題列）。收合＝整個 hidden */
#skAi .aibody{height:var(--aibh);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;padding-right:4px;min-width:0}
/* 兩欄：內容區吃 AI 區剩下的高度（AI 區高度由左欄決定，見上面 contain:size），比內容矮就在區內捲 */
#skChartCard.aiside>#skAi .aibody{flex:1 1 0;height:auto;min-height:0}
/* 單欄（≤820，或卡片放不下兩欄）：內容區改成**浮層**往下展開、蓋在工具列與 K 線上面，不佔版面 ——
   展開／收合 K 線都不動（同一條 #293）。浮層是「點了才開」的東西：進頁面一律收著（不讀 tw.aiOpen、也不寫），
   點外面／按 Esc／再按「收合 ▴」就收。*/
#skChartCard:not(.aiside)>#skAi{position:relative}
#skChartCard:not(.aiside)>#skAi>.aibody{position:absolute;left:0;right:0;top:calc(100% + 6px);z-index:40;height:auto;max-height:min(340px,60vh);
  background:var(--panel);border:1px solid var(--line-2);border-radius:10px;padding:10px 12px;
  box-shadow:0 18px 36px -14px rgba(0,0,0,.6)}
/* 下面還有字 → 底部淡出一條，提示「區內還能往下捲」（捲到底就拿掉）*/
#skAi .aibody.more{-webkit-mask-image:linear-gradient(#000 calc(100% - 22px),transparent);mask-image:linear-gradient(#000 calc(100% - 22px),transparent)}
/* ★ 2026-10-06（全站驗收「標題圖示」紅字）：每一面最上面那一句判讀（「週線多頭、日線多頭；進出場條件：觀望」「九顆燈號：紅＝偏多 5…」）
   改前是 <h4> —— 它是一整句讀數，不是標題；放在 .card 裡就被當成卡片標題，退回預設圖示、讀屏軟體也會把它念成標題。
   改成段落（.aiwhyl），字級、顏色跟改前一樣（13px、--ink-2），畫面看起來不變。*/
:is(#skAi,#tagTech) .aiwhyl{margin:0 0 4px;font-size:13px;font-weight:400;color:var(--ink-2);line-height:1.5}
:is(#skAi,#tagTech) ul{margin:2px 0 0;padding-left:18px;color:var(--ink-2);font-size:13px;line-height:1.55}
:is(#skAi,#tagTech) li{margin:2px 0}
:is(#skAi,#tagTech) .aitfs{display:grid;grid-template-columns:auto auto 1fr;gap:4px 10px;align-items:baseline;font-size:13px}
:is(#skAi,#tagTech) .aitfs .tfn{color:var(--ink-3);white-space:nowrap}
:is(#skAi,#tagTech) .aitfs .aitag{justify-self:start}
:is(#skAi,#tagTech) .aitfs .tfp{color:var(--ink-2);line-height:1.5;min-width:0}
:is(#skAi,#tagTech) .aisub{margin-top:8px;font-size:12.5px;color:var(--ink-3);font-weight:600}
:is(#skAi,#tagTech) .ailv{display:grid;grid-template-columns:1fr 1fr;gap:10px}
:is(#skAi,#tagTech) .ailv .k{background:var(--panel-3);border-radius:9px;padding:5px 9px;margin-top:5px;font-size:12.5px}
:is(#skAi,#tagTech) .ailv .k b{font-family:var(--mono)}
/* 逐條條件用「按鈕＋hidden」而不是 <details>：收起來的 <details> 內容在 Chrome 仍量得到外框，
   _preview 的文字重疊掃描會把它跟下面的支撐壓力區判成重疊（2026-09-26 實測）。*/
:is(#skAi,#tagTech) .aick{margin-top:6px;font-size:12.5px;color:var(--ink-2)}
:is(#skAi,#tagTech) .aickbtn{background:none;border:0;padding:2px 0;color:var(--ink-3);cursor:pointer;font:inherit;text-align:left}
:is(#skAi,#tagTech) .aickbtn:hover{color:var(--cyan)}
:is(#skAi,#tagTech) .ck{display:flex;gap:6px;margin:3px 0} :is(#skAi,#tagTech) .ck .m{flex:none;width:14px;font-weight:700}
:is(#skAi,#tagTech) .ck.ok .m{color:var(--rise)} :is(#skAi,#tagTech) .ck.no .m{color:var(--ink-3)}
#skAi .ainews a{color:var(--cyan)}
#skAi .ainews .kind{font-size:11.5px;color:var(--ink-3);margin-right:4px}
/* #skAi .aiasof（「資料到 YYYY-MM-DD」）2026-10-06 拿掉（DECISIONS #329） */
/* AI 區窄（兩欄的窄卡片、手機）：標籤疊成兩行、標題列不讓收合鈕掉到第二行、「?」緊跟在「AI 分析」後面
   （改前手機上「?」會自己孤零零掉到第二行），技術面週期列與支撐壓力改單欄 */
@container aibox (max-width:380px){
  #skAi .aihead{flex-wrap:nowrap;align-items:flex-start}
  #skAi .aihead h3{flex:1 1 auto;min-width:0;row-gap:2px}
  #skAi .aihead h3 small{order:2;flex-basis:100%}
  #skAi .aitab{flex-direction:column;gap:2px;padding:4px 2px 6px}
  #skAi .aitab .nl{display:none} #skAi .aitab .ns{display:inline} #skAi .aitab .aicnt{display:none}
  #skAi .aitfs{grid-template-columns:auto 1fr} #skAi .aitfs .tfp{grid-column:1 / -1;margin:-2px 0 4px}
  #skAi .ailv{grid-template-columns:1fr}
}
/* ★ 2026-10-05 指標分頁「技術分析」卡（#tagTech）：同一份 techHTML／sigHTML，完整攤開不限高、不捲動 */
/* 2026-10-07：免責不另起框（style_guide 第 10 條）—— 改前是有底色、有框的提示塊，改後跟全站同一行灰色小字 */
#tagTech .ttwarn{margin:2px 0 10px;color:var(--ink-3,var(--ink-2));font-size:12px;font-weight:400;line-height:1.5}
#tagTech .tthead{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
#tagTech .tthead small{color:var(--ink-3)}
#tagTech .aickbtn{display:none}
@media (max-width:820px){#tagTech .aitfs{grid-template-columns:auto 1fr} #tagTech .aitfs .tfp{grid-column:1 / -1;margin:-2px 0 4px} #tagTech .ailv{grid-template-columns:1fr}}
/* ★ 2026-10-06（全站驗收「一屏看完1003」紅字：1440×900 這張卡 966px，比可視高 851 高，要捲才看得完；DECISIONS #308 的一屏規則）：
   卡片夠寬（≥ 760px，1440 桌機是 1184）時內容排成左右兩欄 —— 左＝四個週期、綜合原因、若…則…、支撐壓力（讀的）；
   右＝逐條條件、九顆訊號燈（對照用的清單）。內容一個字都沒少、照樣完整攤開不捲動（10-05 Andy 要的「完整」），
   只是不再疊成一條長柱：1440 實測 966 → 約 560px。卡片窄（平板、側欄開著）照舊一欄，左欄內容在上、右欄在下。*/
#tagTech{container:tt / inline-size}
@container tt (min-width:760px){
  #tagTech .ttcols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:28px;align-items:start}
  #tagTech .ttside>.aick{margin-top:8px}
}
/* 手機分段用的空殼：桌機永遠是空的，不留一塊空卡 */
#aiCard:empty{display:none}
@media (max-width:640px){
  #aiCard>#skAi{margin-top:0;border:0;padding:0}
  /* 標籤疊法、標題列不折行等窄版規則在上面的 @container（AI 區 ≤380px 就套，手機一定套到）*/
  #skAi .aibody{height:auto;max-height:none;overflow:visible}
  #skAi .aibody.more{-webkit-mask-image:none;mask-image:none}
}`;
    document.head.appendChild(st);
  }

  // 四顆標籤：面向名＋判讀小字（technical why 放 title，滑過看得到依據）
  /* 技術面訊號：九顆燈的多空計數（缺值的燈不算）。標籤小字寫「4 多 2 空」—— 只數燈，不下結論 */
  function sigCount(pg, fmt) {
    const L = window.StockSignal && window.StockSignal.lights ? window.StockSignal.lights((pg && pg.summary) || {}, fmt) : [];
    const pos = L.filter(x => x[2] > 0).length, neg = L.filter(x => x[2] < 0).length;
    return { L, pos, neg, label: L.length ? `${pos}多${neg}空` : '資料缺', tone: pos > neg ? 'pos' : neg > pos ? 'neg' : '' };
  }
  function tabs(an, cur, sig) {
    const f = (an && an.facets) || {};
    return facetList(f, sig).map(t => {
      const on = t.k === cur;
      return `<button type="button" role="tab" class="aitab${on ? ' on' : ''}" id="aiTab-${t.k}" data-facet="${t.k}" aria-selected="${on}" aria-controls="aiPanel-${t.k}" title="${esc(t.tip)}">`
        + `${nmHTML(t.nm, t.sh)}<span class="aitag ${t.cls}">${esc(t.lb)}</span>${t.cnt}</button>`;
    }).join('');
  }
  /* 四顆面向的共用描述（K 線卡 #skAi 與總覽 #ovAiCard 同一份）：技術面的徽章＝技術面判讀，旁邊小字＝九顆燈的多空計數 */
  function facetList(f, sig) {
    return FACETS.map(([k, nm, sh]) => {
      const x = f[k] || {};
      const lb = x.label || '資料缺';
      let tip = x.why || '';
      let cnt = '';
      if (k === 'tech' && sig && sig.L.length) {
        cnt = `<span class="aicnt ${sig.tone}" data-sigcnt="${sig.pos}-${sig.neg}">${sig.label}</span>`;
        tip = (tip ? tip + '\n' : '') + `九顆技術燈號：偏多 ${sig.pos}、偏空 ${sig.neg}`;
      }
      return { k, nm, sh, lb, cls: toneCls(lb), tip, cnt };
    });
  }
  /* ★ 2026-10-04 籌碼面內容。判讀（偏多／偏空／中性）與前四條一律照 payload analysis.facets.chip（pipeline chip_facet）：
       · 三大法人 20 日淨買賣超佔同期成交量 ≥ 3% → ±1；5 日同向且 ≥ 5% → 再 ±0.5
       · 集保千張大戶一週 ±0.3 個百分點 → ±0.5
       · 融資餘額 20 日 +10%（籌碼往散戶走）→ −0.5；−10% → +0.5
       · 合計 ≥ 1 偏多、≤ −1 偏空，其餘中性
     前端只補兩條「參考、不計分」的數字（都是個股頁已載入的 payload，不新抓）：
       · 自營商 20 日買賣超（inst_v3.daily 第 4 欄，單位股 ÷1000）—— 管線那條只寫外資、投信
       · 近 5 日平均當沖率、融券餘額 20 日變化（margin 的 daytrade_ratio／short_balance）
     不計分的理由：當沖率高低沒有方向性，融券增加可能是看空也可能是軋空的燃料 —— 規則寫不出單一方向，就只列數字不下結論。*/
  function chipExtra(pg) {
    const out = [];
    const rows = (pg && pg.inst_v3 && pg.inst_v3.daily) || [];
    if (rows.length) {
      const n = Math.min(20, rows.length);
      const d = rows.slice(-n).reduce((a, r) => a + (Number(r[3]) || 0), 0) / 1000;
      out.push(`自營商 ${n} 日${d >= 0 ? '買超' : '賣超'} ${Math.abs(Math.round(d)).toLocaleString()} 張`);
    }
    const cols = (pg && pg.margin_columns) || [];
    const mg = (pg && pg.margin) || [];
    const iD = cols.indexOf('daytrade_ratio'), iS = cols.indexOf('short_balance');
    const bits = [];
    if (iD >= 0) {
      const v = mg.slice(-5).map(r => Number(r[iD])).filter(x => isFinite(x) && x > 0);
      if (v.length) bits.push(`近 ${v.length} 日平均當沖率 ${(v.reduce((a, b) => a + b, 0) / v.length).toFixed(1)}%`);
    }
    if (iS >= 0 && mg.length >= 21) {
      const a = Number(mg[mg.length - 21][iS]), b = Number(mg[mg.length - 1][iS]);
      if (isFinite(a) && isFinite(b) && a > 0) bits.push(`融券餘額 ${Math.round(b).toLocaleString()} 張（20 日 ${((b - a) / a * 100 >= 0 ? '+' : '')}${((b - a) / a * 100).toFixed(1)}%）`);
    }
    if (bits.length) out.push(bits.join('、'));
    return out;
  }
  function chipHTML(pg, x) {
    if (!x) return '<div class="empty">籌碼面資料缺</div>';
    const ex = chipExtra(pg);
    return `${why(x)}${ul(x.points)}${ex.length ? `<div class="aisub">參考（不計入判讀）</div>${ul(ex)}` : ''}`;
  }
  function sigHTML(pg, sig) {
    if (!sig.L.length) return '<div class="empty">技術面訊號資料缺</div>';
    const v = (pg && pg.verdict) || {};
    return `<p class="aiwhyl">九顆燈號：紅＝偏多 ${sig.pos}、綠＝偏空 ${sig.neg}、灰＝中性或未出現</p>
      <div class="lights aisig" id="aiSig">${sig.L.map(window.StockSignal.chip).join('')}</div>
      <ul>
        <li>均線看 5／20／60／120 日排列；結構看高低點是否墊高</li>
        <li>RSI 50 以上、K 在 D 上、MACD 柱為正＝短線偏多</li>
        <li>BOS＝突破前高；CHoCH＝結構轉向；假跌破＝破底又收回</li>
      </ul>
      ${v.invalidation ? `<div class="aisub">失效條件：${esc(v.invalidation)}</div>` : ''}`;
  }

  // 一面的判讀一句話：段落不是標題（見 CSS .aiwhyl 的註解）
  const why = (x) => x && x.why ? `<p class="aiwhyl">${esc(x.why)}</p>` : '';
  const ul = (arr) => arr && arr.length ? `<ul>${arr.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : '';
  const panel = (k, cur, inner) => `<div class="aisec" role="tabpanel" id="aiPanel-${k}" data-facet="${k}" aria-labelledby="aiTab-${k}"${k === cur ? '' : ' hidden'}>${inner}</div>`;

  function techHTML(t, fmt) {
    if (!t) return '<div class="empty">技術面資料缺</div>';
    const tfs = (t.tfs || []).map(r => `<span class="tfn" data-tf="${esc(r.tf)}">${esc(r.label)}</span>`
      + `<span class="aitag ${r.trend > 0 ? 'pos' : r.trend < 0 ? 'neg' : ''}">${esc(r.word)}</span>`
      + `<span class="tfp">${esc((r.points || []).join('・'))}</span>`).join('');
    const ck = t.checks;
    const ckList = (arr) => (arr || []).map(c => `<div class="ck ${c.ok ? 'ok' : 'no'}"><span class="m">${c.ok ? '✓' : '✗'}</span><span><b>${esc(c.name)}</b>：${esc(c.text)}</span></div>`).join('');
    const lv = t.levels || {};
    const zrow = (z) => `<div class="k"><span class="muted">${esc(z.label || '')}</span> <b>${esc(fmt.n(z.low))} – ${esc(fmt.n(z.high))}</b> <span class="muted">距 ${esc(fmt.pct(z.dist_pct))}</span></div>`;
    return `<div class="aitfs" id="aiTfs">${tfs}</div>
      <div class="aisub">綜合：<span class="grade ${stanceCls(t.stance)}">${esc(t.stance || '—')}</span> 的原因</div>
      <ul class="aiwhy" id="aiWhy">${(t.reasons || []).map(x => `<li>${esc(x)}</li>`).join('') || '<li>—</li>'}</ul>
      ${t.ifs && t.ifs.length ? `<div class="aisub">若…則…（狀態會在什麼情況下改變）</div>${ul(t.ifs)}` : ''}
      ${t.plan ? `<div class="aisub">${esc(t.plan)}</div>` : ''}
      ${ck ? `<div class="aick"><button type="button" class="aickbtn" aria-expanded="false">▸ 逐條條件：回檔型態 ${ck.met_a}/${ck.n_a}・突破型態 ${ck.met_b}/${ck.n_b}</button><div class="aickbody" hidden>
        <div class="aisub">回檔型態（A）</div>${ckList(ck.a)}
        <div class="aisub">突破型態（B）</div>${ckList(ck.b)}
        ${ck.risk && ck.risk.a ? `<div class="ck ${ck.risk.a.ok ? 'ok' : 'no'}"><span class="m">${ck.risk.a.ok ? '✓' : '✗'}</span><span><b>停損距離</b>：${esc(ck.risk.a.text)}</span></div>` : ''}
      </div></div>` : ''}
      <div class="aisub">支撐／壓力區（1 小時～週線，由近到遠）</div>
      <div class="ailv"><div>${(lv.support || []).map(zrow).join('') || '<div class="k muted">下方沒有通過門檻的需求區</div>'}</div>
        <div>${(lv.resistance || []).map(zrow).join('') || '<div class="k muted">上方沒有通過門檻的供給區</div>'}</div></div>`;
  }

  function newsHTML(x) {
    if (!x) return '<div class="empty">消息面資料缺</div>';
    const items = (x.items || []).map(it => {
      const d = esc(String(it.date || '').slice(5));
      if (it.kind === '新聞' && it.url) {
        return `<li><span class="kind">新聞</span><span class="mono">${d}</span> <a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a></li>`;
      }
      return `<li><span class="kind">${esc(it.kind)}</span><span class="mono">${d}</span> <a href="#" data-aitab="news">${esc(it.title)}</a></li>`;
    }).join('');
    return `${why(x)}${ul(x.points)}
      ${items ? `<div class="aisub">最新 ${(x.items || []).length} 則</div><ul class="ainews">${items}</ul>` : ''}`;
  }

  function html(pg, fmt) {
    css();
    const an = pg && pg.analysis;
    const v = (pg && pg.verdict) || {};
    /* 內容區先一律收著：掛上去之後 watchWidth 依版面決定 —— K 線卡裡永遠收著（CSS 也藏）、手機 #aiCard 裡永遠打開 */
    const open = false;
    const cur = readTab();
    /* ★ 2026-10-02（#293）預設只看重點：說明第一條講「點小標籤看細節、展開看各週期」，其餘照舊（「?」最多 5 條） */
    const how = window.App && window.App.howHTML ? window.App.howHTML('四個面向的規則式判讀。', [
      '四格＝技術、籌碼、基本、消息面各自判讀',
      '技術面旁「5多0空」＝九顆技術燈偏多、偏空顆數',
      '籌碼面＝法人買賣超、融資增減、大戶週變化計分',
      '各面向不加總、非投資建議',
    ]) : '';
    const head = `<div class="aihead"><h3>AI 分析 <small data-warn id="aiWarn" role="note" title="由固定規則與公開資料自動產生（技術評分、SMC 結構、九顆技術燈號、法人與融資、集保大戶、本益比分位、營收與 EPS、公告新聞），非投資建議">${esc(discLine())}</small>
        <button class="howbtn pop" data-how="ai" type="button" aria-label="AI 分析怎麼看">?</button></h3></div>
      <div class="howtxt" id="how-ai" hidden>${how}</div>`;
    const hd = (an && an.headline) || {};
    const stance = hd.stance || v.verdict || '—';
    // 一行結論跟「總覽」分頁的 AI 分析重點同一句（briefText：回檔 a/6、突破 b/5；停損 x%），兩處不會講不一樣的話
    const brief = an ? briefText(pg) : (hd.brief || ((v.reasons || [])[0] || ''));
    const sum = `<div class="aisum" id="skAiLine" data-readout><span class="grade ${stanceCls(stance)}" id="skAiStance">${esc(stance)}</span><span class="aibrief" title="${esc(brief)}">${esc(brief)}</span></div>`;
    if (!an) {
      const sm = pg && pg.mtf && pg.mtf.summary;
      return head + `<div class="aisum" id="skAiLine" data-readout><span class="aibrief">${sm && sm.headline ? esc(sm.headline) : '資料不足'}</span></div>
        <div class="aibody" id="aiBody"${open ? '' : ' hidden'}><div class="empty">尚無 AI 分析資料</div></div>`;
    }
    const f = an.facets || {};
    const sig = sigCount(pg, fmt);
    return head + sum
      + `<div class="aitabs" role="tablist" aria-label="AI 分析面向" id="aiTabs">${tabs(an, cur, sig)}</div>
      <div class="aibody" id="aiBody" data-readout${open ? '' : ' hidden'}>
        ${panel('tech', cur, techHTML(f.tech, fmt) + `<div class="aisub">技術面訊號</div>` + sigHTML(pg, sig))}
        ${panel('chip', cur, chipHTML(pg, f.chip))}
        ${panel('fund', cur, `${why(f.fund)}${ul((f.fund || {}).points) || '<div class="empty">基本面資料缺</div>'}`)}
        ${panel('news', cur, newsHTML(f.news))}
      </div>`;
  }

  /* ★ 2026-10-03（#305）「展開／收合」鈕拿掉：內容區只在手機（#aiCard 裡，away）打開，K 線卡裡（side／stack）永遠收著。
     以前的 tw.aiOpen（記住展開與否）、單欄浮層（dismissable）一起退場。*/
  function setOpen(host, v) {
    const body = host.querySelector('#aiBody');
    if (body) body.hidden = !v;
    host.classList.toggle('aiopen', !!v);
    moreHint(host);
  }

  function setTab(host, k) {
    host.querySelectorAll('.aitab').forEach(b => { const on = b.dataset.facet === k; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
    host.querySelectorAll('.aisec[role="tabpanel"]').forEach(p => { p.hidden = p.dataset.facet !== k; });
    const body = host.querySelector('#aiBody'); if (body) body.scrollTop = 0;   // 換面向從頭讀
    moreHint(host);
  }
  function moreHint(host) {
    const b = host.querySelector('#aiBody'); if (!b) return;
    b.classList.toggle('more', !b.hidden && b.scrollTop + b.clientHeight < b.scrollHeight - 4);
  }

  /* 左欄最小寬＝工具列「一行放得下」要的寬度：週期鈕、＋、指標、四週期同看、?（看得見的才算）＋標籤區收成「⋯」那顆＋間距。
     週期鈕的顆數是使用者自己勾的（＋ 自訂週期），所以每次都量，不寫死。量不到（工具列還沒畫）就用下限。*/
  function leftMin(card) {
    const tb = card.querySelector('#skTools');
    if (!tb) return LEFT_FLOOR;
    const gap = parseFloat(getComputedStyle(tb).columnGap) || 8;
    let w = 0, n = 0;
    for (const el of tb.children) {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.position === 'absolute' || cs.position === 'fixed') continue;
      n++;
      if (el.classList.contains('sp')) continue;                       // 彈簧：寬 0，但吃一個間距
      // 標籤區最少要留「⋯ N」那一顆的寬；用固定值不用量的 —— 量的話「⋯」出現／消失會讓門檻跳幾 px，卡在門檻上會兩欄單欄來回切
      if (el.id === 'skTags') { w += TAG_MIN; continue; }
      w += el.getBoundingClientRect().width;
    }
    return Math.max(LEFT_FLOOR, Math.ceil(w + gap * Math.max(0, n - 1)));
  }
  function innerW(card) {
    const cs = getComputedStyle(card);
    return card.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
  }
  // 比例 → 右欄像素，夾在 [AI_MIN, 卡片內寬 − 分隔線 − 左欄最小寬] 之間
  function aiPx(card, ratio) {
    const avail = innerW(card) - SPLIT_W;
    const max = avail - leftMin(card);
    return Math.max(AI_MIN, Math.min(max, Math.round(ratio * avail)));
  }

  /* AI 區保底高度：量「標題＋結論＋四列面向」實際多高（AI 區越窄，結論越容易折成兩行）。
     ★ 2026-10-03（#305）：內容區在 K 線卡裡不再出現，不必再替它多留 BODY_MIN（改前＝標題列＋膠囊＋90px 內容區）。
     只在版面變（視窗、卡片、分隔線）時量。*/
  function sizeAi(card, host) {
    if (!card.classList.contains('aiside')) { card.style.removeProperty('--aiH'); return; }
    const last = host.querySelector('#aiTabs') || host.querySelector('#skAiLine');
    const fixed = last && last.getClientRects().length ? last.getBoundingClientRect().bottom - host.getBoundingClientRect().top : 0;
    if (fixed > 0) card.style.setProperty('--aiH', Math.ceil(fixed + 2) + 'px');
  }

  /* 分隔線（#skSplit）：拖曳改右欄寬、放開存 tw.aiSplit；雙擊還原；鍵盤左右鍵每次 2%。
     只在 .aiside（兩欄）時看得到（CSS），≤820 與手機不出現。*/
  function wireSplit(card, host, fit) {
    let sp = card.querySelector('#skSplit');
    if (!sp) {
      sp = document.createElement('div');
      sp.id = 'skSplit';
      sp.tabIndex = 0;
      sp.setAttribute('role', 'separator');
      sp.setAttribute('aria-orientation', 'vertical');
      sp.setAttribute('aria-label', '拖曳調整左右寬度（雙擊還原）');
      sp.title = '拖曳調整左右寬度・雙擊還原';
      card.insertBefore(sp, host);
    }
    const setRatio = (r, save) => {
      const avail = innerW(card) - SPLIT_W;
      const px = aiPx(card, r);
      card.style.setProperty('--aiW', px + 'px');
      sizeAi(card, host);
      sp.setAttribute('aria-valuenow', String(Math.round((1 - px / avail) * 100)));   // 左欄占幾 %（separator 的值＝前一塊的大小）
      if (save) saveSplit(px / avail);
      return px / avail;
    };
    sp.setAttribute('aria-valuemin', '0'); sp.setAttribute('aria-valuemax', '100');
    sp.onpointerdown = (e) => {
      if (e.button !== 0 || !card.classList.contains('aiside')) return;
      e.preventDefault();
      try { sp.setPointerCapture(e.pointerId); } catch (er) { /* 舊瀏覽器 */ }
      const cs = getComputedStyle(card);
      const right = card.getBoundingClientRect().right - (parseFloat(cs.borderRightWidth) || 0) - (parseFloat(cs.paddingRight) || 0);
      const avail = innerW(card) - SPLIT_W;
      let cur = null;
      sp.classList.add('drag'); document.body.classList.add('sksplitting');
      const move = (ev) => {
        // 游標在分隔線中間：右欄寬＝內容區右緣 − 游標 x − 半條分隔線
        cur = setRatio((right - ev.clientX - SPLIT_W / 2) / avail, false);
      };
      const up = () => {
        sp.removeEventListener('pointermove', move); sp.removeEventListener('pointerup', up); sp.removeEventListener('pointercancel', up);
        sp.classList.remove('drag'); document.body.classList.remove('sksplitting');
        if (cur != null) saveSplit(cur);
        moreHint(host);
      };
      sp.addEventListener('pointermove', move); sp.addEventListener('pointerup', up); sp.addEventListener('pointercancel', up);
    };
    sp.ondblclick = (e) => { e.preventDefault(); clearSplit(); fit(); };
    sp.onkeydown = (e) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      const avail = innerW(card) - SPLIT_W;
      const now = (parseFloat(card.style.getPropertyValue('--aiW')) || AI_DEF * avail) / avail;
      setRatio(now + (e.key === 'ArrowLeft' ? 0.02 : -0.02), true);   // 往左＝分隔線往左＝右欄變寬
    };
    return setRatio;
  }

  /* 卡片寬窄 → 兩欄／單欄。量的是 K 線卡本身（右側事件欄開關、⤢ 寬版都會改它）＋視窗寬（≤820 一律單欄）。
     ⚠ 手機（≤640）#skAi 已被搬去 #aiCard，這裡一律拿掉 .aiside，免得卡片留一個空的右欄。
     版面換了（兩欄 ↔ 單欄 ↔ 手機）就重套展開狀態：兩欄／手機讀 tw.aiOpen，單欄浮層一律收著。*/
  function watchWidth(host) {
    const card = document.getElementById('skChartCard');
    if (!card) return;
    let setRatio = null;
    const fit = () => {
      const lm = leftMin(card);
      const on = host.parentElement === card && getComputedStyle(host).display !== 'none' && window.innerWidth > NARROW && innerW(card) >= lm + SPLIT_W + AI_MIN;
      if (card.classList.contains('aiside') !== on) card.classList.toggle('aiside', on);
      if (on) { const r = readSplit(); setRatio(r == null ? AI_DEF : r, false); }
      else card.style.removeProperty('--aiW');
      const mode = modeOf(host);
      if (host._mode !== mode) { host._mode = mode; setOpen(host, mode === 'away'); }
      sizeAi(card, host);
      moreHint(host);
    };
    setRatio = wireSplit(card, host, fit);
    fit();
    if (card._aiRO) card._aiRO.disconnect();
    if (window.ResizeObserver) {
      card._aiRO = new ResizeObserver(fit);
      card._aiRO.observe(card);
      // 週期鈕被勾掉／加上、指標鈕的「已開 N」變長 → 左欄最小寬跟著變，卡片本身的大小卻沒變，所以這幾顆也要看
      ['#tfSeg', '#indBtn', '#mtfBtn'].forEach(s => { const e = card.querySelector(s); if (e) card._aiRO.observe(e); });
    }
    card._aiFit = fit;
  }

  function mount(pg, host, fmt) {
    if (!host) return;
    css();
    host.innerHTML = html(pg, fmt);
    host._mode = null;           // 新內容：讓 watchWidth 的第一次 fit 依版面重套展開狀態
    host.querySelectorAll('.aitab').forEach(b => b.onclick = () => {
      const k = b.dataset.facet;
      saveTab(k); setTab(host, k);
      /* K 線卡裡（桌機兩欄／單欄）的每一列＝捲到下面「總覽」分頁的 AI 卡並切到那一面（原地捲，不換頁）；
         手機（#aiCard 裡）是標籤頁，切換下面內容區那一面（#305 起內容區在手機一律打開）。*/
      if (modeOf(host) !== 'away') gotoFacet(host, k);
    });
    // 標籤列支援方向鍵（WAI-ARIA tabs 的慣例）
    const tl = host.querySelector('#aiTabs');
    if (tl) tl.onkeydown = (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      // K 線卡裡每一列是「捲到總覽 AI 卡」的按鈕，不是標籤頁：方向鍵只移焦點、不觸發捲動
      const brief = modeOf(host) !== 'away';
      const bs = [...tl.querySelectorAll('.aitab')]; const i = bs.indexOf(document.activeElement);
      if (brief) { if (i >= 0) { bs[(i + (e.key === 'ArrowRight' ? 1 : bs.length - 1)) % bs.length].focus(); e.preventDefault(); } return; }
      if (i < 0) return;
      const n = bs[(i + (e.key === 'ArrowRight' ? 1 : bs.length - 1)) % bs.length];
      n.focus(); n.click(); e.preventDefault();
    };
    const ckb = host.querySelector('.aickbtn');
    if (ckb) ckb.onclick = () => {
      const body = ckb.nextElementSibling; const open = body.hidden;
      body.hidden = !open; ckb.setAttribute('aria-expanded', String(open));
      ckb.textContent = (open ? '▾' : '▸') + ckb.textContent.slice(1);
    };
    // 重大訊息沒有外部網址：點標題切到下方「公告 / 新聞」分頁（站內既有的那一頁，有觀測站連結與全文摘要）
    host.querySelectorAll('[data-aitab]').forEach(a => a.onclick = (e) => {
      e.preventDefault();
      const b = document.querySelector(`#stockTabs button[data-t="${a.dataset.aitab}"]`);
      if (b) { b.click(); try { b.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (er) { b.scrollIntoView(); } }
    });
    const bd = host.querySelector('#aiBody');
    if (bd) bd.addEventListener('scroll', () => moreHint(host), { passive: true });
    watchWidth(host);
    requestAnimationFrame(() => moreHint(host));
  }

  /* 小標籤 → 下面「總覽」分頁的 AI 卡（#ovAiCard，ovCard 畫的），並把卡裡的分頁籤切到同一面。
     ★ 2026-10-02 深夜（Andy：總覽改三欄、AI 四面向併成一張卡，DECISIONS #297）：改前是捲到四張細節卡裡的那一張；
       四張併成一張之後，「捲到那一張」就變成「捲到 AI 卡、切到那一面的分頁籤」—— 一次只顯示一面，切過去才看得到。
     不在總覽分頁就先按「總覽」鈕切過去（分頁內容是非同步畫的，最多等 1.5 秒）；捲到卡片上緣並閃一下。
     那一面沒有內容（例如資料缺、或擋掉了 stock.signal）就退回原地展開看那一面，不讓點擊落空。*/
  function gotoFacet(host, k) {
    const find = () => { const c = document.getElementById('ovAiCard'); return c && c.querySelector(`#ovFacets > [data-facet="${k}"]`) ? c : null; };
    const go = (c) => {
      setOvTab(c, k, true);
      try { c.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { c.scrollIntoView(); }
      c.classList.remove('flash'); void c.offsetWidth; c.classList.add('flash');
      clearTimeout(c._ovT); c._ovT = setTimeout(() => c.classList.remove('flash'), 1500);
    };
    let c = find();
    if (c) { go(c); return; }
    const ob = document.querySelector('#stockTabs button[data-t="overview"]');
    if (ob && !ob.classList.contains('on')) ob.click();
    const t0 = Date.now();
    const wait = () => {
      c = find();
      if (c) { go(c); return; }
      if (Date.now() - t0 < 1500) { setTimeout(wait, 60); return; }
      // 找不到 AI 卡（或那一面沒內容，例如擋掉了 stock.signal）：停在總覽分頁就好 —— #305 起 K 線卡裡沒有內容區可以原地展開
    };
    setTimeout(wait, 30);
  }

  // app.js miaStock 搬完節點後叫一次，讓兩欄／單欄立刻跟上（不必等 ResizeObserver）
  function refit() { const c = document.getElementById('skChartCard'); if (c && c._aiFit) c._aiFit(); }

  /* ==========================================================================
     ★ 2026-10-02（Andy 五張截圖，DECISIONS #294）個股「總覽」分頁裡的 AI 分析：
       · brief()      —— 最上面一張「AI 分析重點」：結論一個詞（條件未齊／條件成立／偏空）＋一行帶數字的原因
                         （「回檔型態 4/6、突破型態 4/5；停損距離 21.3% 超過 8%」）＋四顆小標籤（技術面／技術面訊號／基本面／消息面）。
                         點標籤＝捲到下面那一張細節卡、閃一下（原地，不跳頁）。
       · facetCards() —— 三張細節小卡（技術面、基本面、消息面）。第二張「技術面訊號」是積木 stock.signal 的出口，
                         由 industry.js 夾在中間，這支不重畫九顆燈（兩處同一份 lights()）。
       · facetHead()  —— 細節卡上面那一行小標題（「AI 分析・各面向細節」＋非投資建議）。（#297 起拿掉：標題併進 ovCard 的卡片標題）
       · bindOverview(root) —— 掛標籤捲動、技術面卡「看細節」原地展開、重大訊息點了切「公告／新聞」分頁。（#297 起標籤＝卡內切換）
     為什麼技術面卡要放小圖：Andy「能用小圖表示的就用小圖」—— 回檔／突破兩套型態的成立條數畫成點（●●●●○○），
     停損距離畫成一條有「8% 上限」刻度的進度條，超過上限一眼就看得到；長句子（原因、逐條條件、若…則…）收進「看細節」。
     ⚠ K 線卡右上角那一份（#skAi，mount）這裡一個字都沒改 —— 頂部版面是另一支分支（claude/stock-head-layout）在改。
       兩份共用同一份 payload 的 analysis 與同一支 sigCount／stanceCls／toneCls，數字不會分家。
     ⚠ id 一律 ov 開頭（ovF-tech、how-ovai…），不跟 #skAi 裡的 aiTfs／how-ai 撞號（兩份同時在頁面上）。

     ★ 2026-10-02 深夜改版（Andy 看了 #294 上線版說「誤解了」，DECISIONS #297）：
       改前：最上面一張「AI 分析重點」＋下面「各面向細節」四張卡並排（技術面那張 1.45 倍寬）。
       改後：**合成一張卡 ovCard()**，放在總覽三欄的右欄：
         標題「AI 分析」＋緊貼的「規則式自動判讀，非投資建議」（#269）→ 一行重點（brief）→ 一排膠囊分頁籤
         （技術面｜技術面訊號｜基本面｜消息面，樣式＝「法人」分頁「外資｜投信｜自營商｜合計」那組 .seg，每顆帶原本的小判讀）
         → 卡裡一次只顯示一面（點籤在同一張卡內切換，不捲動、不跳頁）。選哪一面存 tw.ovAiTab，沒存過＝技術面。
       為什麼一次只顯示一面：三欄裡右欄只有約 500px 寬，四張細節卡疊起來會比左、中兩欄長兩三倍，整頁被右欄撐長。
       四張細節卡的內容一個字都沒改（facetCards 照舊產出、技術面訊號照舊是 StockSignal.view 的出口），
       只是在卡裡壓平（不再是卡中卡）、標題交給分頁籤（每一面原本的 h3 在卡裡藏起來，籤上已經寫了名稱與判讀）。
       顯示哪一面用 #ovFacets 的 data-cur ＋ CSS 決定，**不改各面那個節點的屬性** —— 技術面訊號那一面要跟積木出口一字不差（_uitest 積木-個股三卡在比 outerHTML）。
     ========================================================================== */
  function ovCss() {
    if (document.getElementById('stockAiOvCss')) return;
    const st = document.createElement('style');
    st.id = 'stockAiOvCss';
    st.textContent = `
/* 合併後的 AI 卡（#297）：標題＋免責 → 一行重點 → 膠囊分頁籤 → 一次一面 */
#ovAiCard{display:flex;flex-direction:column;gap:10px;min-width:0;scroll-margin-top:80px;container:ovai / inline-size}
#ovAiCard>h3{margin:0;display:flex;flex-wrap:wrap;align-items:center;column-gap:8px;row-gap:2px}
#ovAiCard>h3 small[data-warn]{order:2;flex-basis:100%;font-size:12px;letter-spacing:-.04em;color:var(--ink-3,var(--ink-2));font-weight:400;line-height:1.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:help}
#ovAiCard.flash{animation:ovflash 1.4s ease-out 1}
@keyframes ovflash{0%{box-shadow:0 0 0 2px var(--cyan)}100%{box-shadow:0 0 0 2px transparent}}
@media (prefers-reduced-motion:reduce){#ovAiCard.flash{animation:none;box-shadow:0 0 0 2px var(--cyan)}}
#ovAiCard .ovline{display:flex;align-items:baseline;gap:10px;min-width:0;font-size:15px;color:var(--ink);line-height:1.5}
#ovAiCard .ovline .grade{flex:none;white-space:nowrap}
#ovAiCard .ovline .ovbrief{min-width:0}
/* 膠囊分頁籤：外框、底色、選中態都吃全站 .seg（跟「法人」分頁同一組），這裡只補「四顆撐滿一列、每顆帶小判讀」。
   卡內寬度 < 430px（手機、或兩欄時右欄很窄）四顆排不下一列 → 2×2，不讓第四顆單獨掉到第二行 */
/* ★ 2026-10-04（Andy 截圖：選中的「技術面訊號」藥丸蓋住左右的字）：改前 repeat(4,auto)＋min-width:0＋nowrap，
   卡片窄於四顆自然寬度總和時格子被壓、字溢出蓋到隔壁。改成固定 2×2：每顆至少半張卡寬，1640～390 都放得下，不再依容器寬度猜斷點。*/
/* ★ 2026-10-04（Andy：「4 個指標需要並排（同一列），若會跌到文字就縮小或名稱簡化」）：2×2 → 一列四顆。
   四面向變成 技術面／籌碼面／基本面／消息面（三個字），技術面多一個燈號計數小字所以給它自然寬（flex:auto），其餘均分。
   寬度不足依序：① 字縮到 12px（不再小）② 收掉技術面的燈號計數（可有可無的附註，先讓）③ 名稱換簡稱「技術／籌碼／基本／消息」。
   實測卡片內寬：1640＝508、1440＝433（三欄的右欄）、1100＝535、800＝774 —— 1440 落在 ②，全名保住。任何寬度都不換行、不重疊、不裁切（_uitest 量每顆 scrollWidth）。*/
#ovAiCard .ovseg{display:flex;flex-wrap:nowrap;gap:4px;align-self:stretch;min-width:0}
#ovAiCard .ovseg .ovtag{flex:1 1 auto;display:inline-flex;align-items:center;justify-content:center;gap:5px;min-width:0;min-height:32px;white-space:nowrap;padding:0 8px;font-size:13px}
#ovAiCard .ovseg .ovtag .aicnt{font-size:12px}
@container ovai (max-width:560px){
  #ovAiCard .ovseg .ovtag{font-size:12px;padding:0 5px;gap:4px}
  #ovAiCard .ovseg .ovtag .aitag{padding:0 4px}
}
@container ovai (max-width:470px){ #ovAiCard .ovseg .ovtag .aicnt{display:none} }
@container ovai (max-width:400px){ #ovAiCard .ovseg .ovtag .nl{display:none} #ovAiCard .ovseg .ovtag .ns{display:inline} }
#ovAiCard .ovseg .ovtag .aitag{font-size:12px;padding:0 6px}
/* 選中那顆底色是青色：判讀小標改成卡片底色的小膠囊，紅綠字才讀得到（直接疊在青底上對比不夠）*/
#ovAiCard .ovseg .ovtag.on .aitag{background:var(--panel);font-weight:600}
#ovAiCard .ovseg .ovtag:focus-visible{outline:2px solid var(--focus,var(--cyan));outline-offset:2px}
/* 一次一面：#ovFacets 的 data-cur 決定顯示哪一面；各面壓平（不是卡中卡），標題交給分頁籤 */
#ovAiCard #ovFacets{min-width:0}
#ovAiCard #ovFacets>[data-facet]{display:none;background:none;border:0;border-radius:0;box-shadow:none;padding:0;margin:0;min-width:0}
#ovAiCard #ovFacets[data-cur="tech"]>[data-facet="tech"],#ovAiCard #ovFacets[data-cur="sig"]>[data-facet="sig"],
#ovAiCard #ovFacets[data-cur="chip"]>[data-facet="chip"],#ovAiCard #ovFacets[data-cur="fund"]>[data-facet="fund"],#ovAiCard #ovFacets[data-cur="news"]>[data-facet="news"]{display:block}
#ovAiCard #ovFacets>[data-facet]>h3{display:none}
/* 技術面訊號（StockSignal.view 那張）併進技術面：技術面那一面顯示時，它接在下面，小標題留著（「技術面訊號 5多0空」）*/
#ovAiCard #ovFacets[data-cur="tech"]>[data-facet="sig"]{display:block;margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
#ovAiCard #ovFacets>[data-facet="sig"]>h3{display:block;margin:0;font-size:12.5px;font-weight:600;color:var(--ink-3)}
#ovAiCard #ovFacets>[data-facet] .lights{margin-top:0!important}
/* 每一面最上面那一句判讀：段落不是標題（2026-10-06 從 <h4> 改，理由同 K 線卡那份的 .aiwhyl） */
.ovfacet .ovwhy{margin:0 0 6px;font-size:13px;font-weight:400;color:var(--ink-2);line-height:1.5}
.ovfacet ul{margin:4px 0 0;padding-left:18px;color:var(--ink-2);font-size:13px;line-height:1.55}
.ovfacet li{margin:3px 0}
.ovfacet .ovsub{margin-top:10px;font-size:12.5px;color:var(--ink-3);font-weight:600}
/* 技術面：週期列（週期名｜多空小標｜敘述）*/
.ovtfs{display:grid;grid-template-columns:auto auto minmax(0,1fr);gap:5px 8px;align-items:baseline;font-size:13px}
.ovtfs .tfn{color:var(--ink-3);white-space:nowrap}
.ovtfs .aitag{justify-self:start}
.ovtfs .tfp{color:var(--ink-2);line-height:1.5;min-width:0}
/* 型態條件：成立幾條畫成點、停損距離畫成有上限刻度的進度條 */
.ovck{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:6px 10px;align-items:center;margin-top:6px;font-size:13px}
.ovck .ckn{color:var(--ink-2);white-space:nowrap}
.ovck .dots{display:flex;gap:4px;flex-wrap:wrap}
.ovck .dots i{width:9px;height:9px;border-radius:50%;background:color-mix(in srgb,var(--ink-3) 30%,transparent)}
.ovck .dots i.on{background:var(--cyan)}
.ovck b{font-family:var(--mono);font-weight:600;color:var(--ink);white-space:nowrap}
.ovck b.warn{color:var(--amber)}
.ovck .meter{height:8px}
.ovlv{margin-top:8px;font-size:12.5px;color:var(--ink-2);line-height:1.55}
.ovlv b{font-family:var(--mono);font-weight:600;color:var(--ink)}
.ovmore{margin-top:8px;background:none;border:0;padding:4px 0;color:var(--cyan);font:inherit;font-size:13px;cursor:pointer;text-align:left}
.ovmore:hover{text-decoration:underline}
.ovdet .ck{display:flex;gap:6px;margin:3px 0;font-size:12.5px;color:var(--ink-2)} .ovdet .ck .m{flex:none;width:14px;font-weight:700}
.ovdet .ck.ok .m{color:var(--rise)} .ovdet .ck.no .m{color:var(--ink-3)}
.ovnews a{color:var(--cyan)}
.ovnews .kind{font-size:11.5px;color:var(--ink-3);margin-right:4px}
.ovasof{margin-top:8px;font-size:12px;color:var(--ink-3)}
@media (max-width:640px){#ovAiCard .ovline{font-size:14.5px}}`;
    document.head.appendChild(st);
  }

  /* 一行重點：有兩套型態條件就一律用「回檔 a/6、突破 b/5；停損 x% 超過／在 8% 內」（Andy 給的格式），
     沒有才退回管線的 headline.brief（例如資料不足時的一句話）*/
  function briefText(pg) {
    const an = pg && pg.analysis;
    const ck = an && an.facets && an.facets.tech && an.facets.tech.checks;
    if (ck && ck.n_a) {
      const ra = ck.risk && ck.risk.a;
      let t = `回檔型態 ${ck.met_a}/${ck.n_a}、突破型態 ${ck.met_b}/${ck.n_b}`;
      if (ra && ra.pct != null) t += `；停損距離 ${Number(ra.pct).toFixed(1)}% ${ra.ok ? '在' : '超過'} ${Number(ra.max != null ? ra.max : 8).toFixed(0)}%${ra.ok ? ' 內' : ''}`;
      return t;
    }
    const hd = (an && an.headline) || {};
    const v = (pg && pg.verdict) || {};
    return hd.brief || (v.reasons || [])[0] || '';
  }
  function facetTags(pg, fmt) {
    const an = (pg && pg.analysis) || {};
    const f = an.facets || {};
    return facetList(f, sigCount(pg, fmt));
  }
  /* 總覽 AI 卡選哪一面（tw.ovAiTab）。跟 K 線卡那一份的 tw.aiTab 分開存：兩份同時在頁面上，
     在總覽切面向不該順手把頂部那一份也換掉（頂部收合時點小標籤會切這一份，見 gotoFacet）。*/
  const OV_TAB_KEY = 'tw.ovAiTab';
  function readOvTab(have) {
    let v = null;
    try { v = localStorage.getItem(OV_TAB_KEY); } catch (e) { /* 私密視窗 */ }
    if (v === 'sig') v = 'tech';           // 舊值：技術面訊號已併進技術面
    if (v && v !== 'sig' && have.includes(v)) return v;
    return have.includes('tech') ? 'tech' : have[0];
  }
  /* 切到某一面：改 #ovFacets 的 data-cur（CSS 依它顯示那一面）＋籤的選中態；save＝寫 localStorage。那一面不存在就回 false。*/
  function setOvTab(root, k, save) {
    const fac = root && root.querySelector('#ovFacets');
    if (k === 'sig') k = 'tech';             // 技術面訊號＝技術面那一面的下半
    if (!fac || !fac.querySelector(`:scope > [data-facet="${k}"]`)) return false;
    fac.dataset.cur = k;
    root.querySelectorAll('#ovAiTags .ovtag').forEach(b => { const on = b.dataset.facet === k; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; });
    if (save) { try { localStorage.setItem(OV_TAB_KEY, k); } catch (e) { /* 忽略 */ } }
    return true;
  }
  /* 一行重點（#ovAiBrief，data-ai＝跟著「AI 分析」那一項上鎖）。標題不放在這塊裡：上鎖時只糊掉結論，標題與免責字樣照樣看得到 */
  function brief(pg) {
    const an = pg && pg.analysis;
    const v = (pg && pg.verdict) || {};
    const hd = (an && an.headline) || {};
    const stance = hd.stance || v.verdict || '—';
    return `<div id="ovAiBrief" data-ai><div class="ovline" id="ovAiLine" data-readout><span class="grade ${stanceCls(stance)}">${esc(stance)}</span>`
      + `<span class="ovbrief">${esc(an ? briefText(pg) : '尚無資料')}</span></div>${an ? ckCells(pg) : ''}</div>`;
  }
  /* ★ 2026-10-02 深夜（#297）總覽右欄那一張 AI 卡。sig＝StockSignal.view 的輸出（industry.js 給；擋掉 stock_signal.js 時是空字串，那一面就不出現）。*/
  /* ★ 2026-10-07（Andy 01:15：AI 分析上方加一行「依公開資料統計計算、不構成投資建議或參考」，一行小字、不另起欄位）：
     改前標題旁琥珀色「規則式自動判讀，非投資建議」→ 改後跟全站同一句（App.DISC_LINE）、灰色 12px、排在標題下一行（整句看得到）。*/
  function discLine() { return (window.App && window.App.DISC_LINE) || '以下為依公開資料統計計算之結果，不構成任何投資建議或參考'; }

  /* ==========================================================================
     ★ 2026-10-10（Andy：「AI 分析需要搭配圖示上去，幫我修正這邊」，附圖＝個股「總覽」分頁的 #ovAiCard）
     改前：四顆籤只有字；每一面內容是純文字條列（「外資 20 日賣超 4,295 張、投信 20 日買超 3,828 張」），
           要自己在腦中比大小、判方向。
     改後（只在桌機 >640；手機 ≤640／html.m4 新元素一律 display:none，條列文字照舊，版面一個像素不變）：
       · 四顆籤前面各一個線條圖示（TwIcons 同一套：技術＝K 棒、籌碼＝人群、基本＝財報、消息＝新聞），
         判讀小標前加方向符號（▲偏多紅／▼偏空綠／—中性灰，CSS ::before，不動 .aitag 的文字）。
       · 一行重點下面兩組小格子：回檔型態 6 格亮 4 格、突破型態 5 格亮 1 格 —— 「差幾條」一眼看到。
       · 每一條指標＝左邊小圖示＋上面一張小圖＋下面原本那一行字：
           技術面：九顆燈號的紅／灰／綠比例條；籌碼面：外資／投信／自營商 20 日正負橫條（紅買綠賣、長度依張數）、
           法人 5／20 日與融資的箭頭數字徽章、千張大戶持股進度條＋週變化徽章；
           基本面：同業分位進度條、月營收 YoY 三根小直條、近四季 EPS 四根小直條；消息面：7 天／30 天則數橫條。
     數字一律從同一份 payload 取（法人橫條＝inst_v3.daily 最近 20 日加總，跟管線 chip_facet 同一個算法；
     其餘從管線寫好的那一行字裡讀數字），圖跟字講的永遠是同一個數。
     法遵：只畫事實數字，不加任何指示性字眼；免責那一行原封不動。
     ========================================================================== */
  /* ★ 2026-10-10 第二版（Andy 看了線上版：「圖標需要再優化，可以參考行事曆上面的格式，並且需要調整適當寬度」）
     改前（第一版）：每條左邊一顆 24px 有底色的方塊圖示，小圖只有內容那麼寬 —— 營收 3 根、EPS 4 根直條擠在左半邊，右半邊空白。
     改後：照「財經日曆／ETF 配息行事曆」那一家的格式：
       · 圖示＝小線條圖示（13px、不加底塊），跟一個粗體小標題排在同一行（財經日曆右側清單、面板小節 .sec h4 那個樣子）；
         顏色語彙同日曆：技術＝紫、籌碼＝青、基本＝琥珀、消息＝萊姆。
       · 數字＝日曆面板上方那排「數字格」（1px 框、8px 圓角、上小標下大數字，ETF 配息面板的「最近一次配息／當次殖利率／平均填息」）
         —— 幾格就等分整列，吃滿卡片寬度。
       · 有升降的數字用日曆的外框膠囊徽章（1px currentColor、999px 圓角）：▲ 紅、▼ 綠。
       · 直條＝日曆面板同一支小圖 CalGrid.mini（同色漸層、3px 圓角、滑過加亮、點了選取），寬度＝整張卡；
         數字寫在柱上、期別寫在柱下（HTML 等分格，跟圖的類別格對齊）。
       · 法人正負橫條、燈號比例條、則數橫條都拉滿可用寬度。
     手機規則不變：這些全部只在 >640 且非 html.m4 顯示，手機看到的仍是原本的條列文字。 */
  const DIRCH = (lb) => lb === '偏多' ? 'up' : lb === '偏空' ? 'down' : lb === '中性' ? 'flat' : '';
  const FICON = { tech: ['candle', 'tech'], chip: ['users', 'chip'], fund: ['file', 'fund'], news: ['news', 'event'] };
  const svgI = (k, s) => (window.TwIcons && window.TwIcons.svg ? window.TwIcons.svg(k, s || 15) : '');
  const sgn = (v) => (v > 0 ? 'pos' : v < 0 ? 'neg' : '');
  const numS = (v, d) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: d || 0, minimumFractionDigits: d || 0 });
  const toN = (s) => Number(String(s).replace(/,/g, ''));
  const arrow = (v) => (v > 0 ? '▲' : v < 0 ? '▼' : '—');
  /* 外框膠囊徽章（日曆 .badge 同款）：數字往上 ▲ 紅、往下 ▼ 綠、0 灰 —— 只講數字往哪邊動，不下結論 */
  const badge = (v, txt, cap) => `<span class="vzbd ${sgn(v)}" data-v="${v}">${cap ? `<small>${esc(cap)}</small>` : ''}<i aria-hidden="true">${arrow(v)}</i>${esc(txt)}</span>`;
  /* 數字格（日曆面板上方那排）：上＝小標、下＝數字（＋單位）；v 給了就依正負上紅綠色並加 ▲▼ */
  const tile = (lab, num, unit, v) => `<span class="vzk${v != null ? ' ' + sgn(v) : ''}"${v != null ? ` data-v="${v}"` : ''}><small>${esc(lab)}</small><b>${v != null && v !== 0 ? `<i aria-hidden="true">${arrow(v)}</i>` : ''}${esc(num)}${unit ? `<em>${esc(unit)}</em>` : ''}</b></span>`;
  const tiles = (arr) => `<div class="vzks" style="--n:${arr.length}">${arr.join('')}</div>`;
  /* 一條指標：（標題列＝小線條圖示＋粗體小標＋右側徽章）＋整列寬的小圖 ＋ 原本那一行字。手機 .vzb 藏起來，剩 .vzt＝改前的 <li> 文字 */
  const vzRow = (icon, tone, title, right, viz, text, extra) => `<li class="vzr"${extra || ''}><div class="vzc"><div class="vzb">`
    + `<div class="vzh" data-tone="${tone}"><span class="vzi" aria-hidden="true">${svgI(icon, 13)}</span><b>${esc(title)}</b>${right ? `<span class="vzhr">${right}</span>` : ''}</div>`
    + `${viz ? `<div class="vzviz">${viz}</div>` : ''}</div><span class="vzt">${esc(text)}</span></div></li>`;
  /* 正負橫條（D 款的正負版）：中線在中間，買超往右（紅）、賣超往左（綠），長度＝|張數|／三條裡最大的那一條 */
  function instBars(pg) {
    const rows = (pg && pg.inst_v3 && pg.inst_v3.daily) || [];
    if (!rows.length) return '';
    const n = Math.min(20, rows.length), last = rows.slice(-n);
    const sum = (i) => last.reduce((a, r) => a + (Number(r[i]) || 0), 0) / 1000;
    const L = [['外資', sum(1)], ['投信', sum(2)], ['自營商', sum(3)]].map(([k, v]) => [k, Math.round(v)]);
    const mx = Math.max(1, ...L.map(x => Math.abs(x[1])));
    return `<div class="vzinst" id="ovInstBars" role="img" aria-label="${n} 日法人買賣超：${L.map(x => `${x[0]} ${numS(x[1])} 張`).join('、')}">`
      + L.map(([k, v]) => {
        const w = (Math.abs(v) / mx * 50).toFixed(1);
        return `<div class="vzib" data-who="${k}" data-v="${v}"><span class="vzn">${k}</span><span class="vztrack"><i class="${sgn(v)}" style="--w:${w}%"></i></span><b class="${sgn(v)}">${numS(v)}</b></div>`;
      }).join('') + `<div class="vzlg"><span><i class="pos"></i>買超（往右）</span><span><i class="neg"></i>賣超（往左）</span><span>單位：張</span></div></div>`;
  }
  function chipRows(pg, pts) {
    return (pts || []).map(p => {
      let m;
      if ((m = p.match(/^三大法人近 5 日(買超|賣超) ([\d,]+) 張、近 (\d+) 日(買超|賣超) ([\d,]+) 張(?:（佔同期成交量 ([+-]?[\d.]+)%）)?/))) {
        const v5 = toN(m[2]) * (m[1] === '賣超' ? -1 : 1), v20 = toN(m[5]) * (m[4] === '賣超' ? -1 : 1);
        const k = [tile('近 5 日', numS(v5).replace(/^[+−]/, ''), '張', v5), tile(`近 ${m[3]} 日`, numS(v20).replace(/^[+−]/, ''), '張', v20)];
        if (m[6] != null) k.push(tile('佔同期成交量', `${Math.abs(Number(m[6])).toFixed(1)}`, '%', Number(m[6])));
        return vzRow('landmark', 'chip', '三大法人合計', '', tiles(k), p, ' data-vz="inst"');
      }
      if (/^外資 \d+ 日/.test(p)) return vzRow('users', 'chip', '外資／投信／自營商', '', instBars(pg), p, ' data-vz="inst3"');
      if ((m = p.match(/^融資餘額 ([\d,]+) 張(?:，近 5 日(增加|減少) ([\d,]+) 張)?(?:、近 20 日(增加|減少) ([\d,]+) 張（([+-]?[\d.]+)%）)?/))) {
        const d5 = m[3] != null ? toN(m[3]) * (m[2] === '減少' ? -1 : 1) : null;
        const p20 = m[6] != null ? Number(m[6]) : null;
        const k = [tile('融資餘額', m[1], '張')];
        if (d5 != null) k.push(tile('近 5 日', numS(d5).replace(/^[+−]/, ''), '張', d5));
        if (p20 != null) k.push(tile('近 20 日', Math.abs(p20).toFixed(1), '%', p20));
        return vzRow('wallet', 'chip', '融資', '', tiles(k), p, ' data-vz="margin"');
      }
      if ((m = p.match(/^千張大戶持股 ([\d.]+)%(?:.*?較前一週 ([+-]?[\d.]+) 個百分點)?(?:、較 4 週前 ([+-]?[\d.]+))?/))) {
        const h = Number(m[1]);
        const right = (m[2] != null ? badge(Number(m[2]), `${Math.abs(Number(m[2])).toFixed(2)}pp`, '1 週') : '')
          + (m[3] != null ? badge(Number(m[3]), `${Math.abs(Number(m[3])).toFixed(2)}pp`, '4 週') : '');
        const viz = `<div class="vzbar"><span class="meter vzmeter" style="--p:${Math.max(0, Math.min(100, h)).toFixed(1)}%" role="img" aria-label="千張大戶持股 ${h}%"><i></i></span><b class="vzpct">${h.toFixed(2)}%</b></div>`;
        return vzRow('pie', 'chip', '千張大戶持股', right, viz, p, ' data-vz="holder"');
      }
      return vzRow('bars', 'chip', '籌碼', '', '', p);
    }).join('');
  }
  /* 小直條（月營收 YoY、近四季 EPS）：日曆面板那支 CalGrid.mini，整張卡寬；數字在柱上、期別在柱下（HTML 等分格對齊圖的類別格） */
  function miniCols(list, kind) {
    const vals = list.map(x => x[1]);
    const fmtV = (v) => (kind === 'yoy' ? numS(v, 1) + '%' : v.toFixed(2));
    const col = kind === 'yoy' ? ((v) => (v < 0 ? 'var(--fall)' : 'var(--rise)')) : ((v) => (v < 0 ? 'var(--fall)' : 'var(--amber)'));
    const chart = window.CalGrid && window.CalGrid.mini ? window.CalGrid.mini({
      labels: list.map(x => x[0]), bars: { vals, color: col, name: kind === 'yoy' ? '營收年增率' : 'EPS' },
      tip: (i) => `${esc(list[i][0])}　<b>${esc(fmtV(list[i][1]))}</b>`,
      aria: list.map(x => `${x[0]} ${fmtV(x[1])}`).join('、'),
    }) : '';
    const row = (cls, f) => `<div class="${cls}" style="--n:${list.length}">${list.map(f).join('')}</div>`;
    return `<div class="vzcols" data-kind="${kind}">`
      + row('vzcv', ([, v]) => `<b class="${v < 0 ? 'neg' : kind === 'eps' ? 'cat' : 'pos'}" data-v="${v}">${esc(fmtV(v))}</b>`)
      + chart + row('vzcl', ([k]) => `<small>${esc(k)}</small>`) + `</div>`;
  }
  function fundRows(pts) {
    return (pts || []).map(p => {
      let m;
      if ((m = p.match(/^(本益比|股價淨值比|股價營收比) ([\d.]+) 倍(?:.*?中位 ([\d.]+) 倍、分位 (\d+)%)?/))) {
        const pct = m[4] != null ? Number(m[4]) : null;
        const k = [tile(m[1], m[2], '倍')];
        if (m[3] != null) k.push(tile('同族群中位', m[3], '倍'));
        if (pct != null) k.push(tile('同業分位', String(pct), '%'));
        const viz = tiles(k) + (pct != null ? `<div class="vzbar"><span class="meter vzmeter" style="--p:${pct}%;--c:var(--amber)" role="img" aria-label="同業分位 ${pct}%"><i></i><b class="tick" style="left:50%" title="中位"></b></span><small>分位 0～100（中線＝同族群中位）</small></div>` : '');
        return vzRow('scale', 'fund', '估值', '', viz, p, ' data-vz="pe"');
      }
      if (/^月營收 YoY/.test(p)) {
        const L = [...p.matchAll(/(\d\d-\d\d) ([+-][\d.]+)%/g)].map(x => [x[1], Number(x[2])]);
        const st = p.match(/連續 (\d+) 個月年增/);
        return vzRow('bars-up', 'fund', '月營收年增率（近 3 個月）', st ? `<span class="vztag">連續 ${esc(st[1])} 個月年增</span>` : '', L.length ? miniCols(L, 'yoy') : '', p, ' data-vz="yoy"');
      }
      if (/^近四季 EPS/.test(p)) {
        const L = [...p.matchAll(/(\d{4}Q\d) (-?[\d.]+)/g)].map(x => [x[1].slice(2), Number(x[2])]);
        const g = p.match(/，([+-]\d+)%）/);
        return vzRow('coins', 'fund', '近四季 EPS（元）', g ? badge(Number(g[1]), `${Math.abs(Number(g[1]))}%`, '較前四季') : '', L.length ? miniCols(L, 'eps') : '', p, ' data-vz="eps"');
      }
      return vzRow('file', 'fund', '基本面', '', '', p);
    }).join('');
  }
  function newsRows(x) {
    const c = x.counts || {};
    return (x.points || []).map(p => {
      const ann = /^重大訊息/.test(p), nws = /^相關新聞/.test(p);
      if ((ann || nws) && c.m30 != null) {
        const a7 = ann ? c.m7 : c.n7, a30 = ann ? c.m30 : c.n30, mx = Math.max(1, c.m30 || 0, c.n30 || 0);
        const viz = `<div class="vzcnt" data-n7="${a7}" data-n30="${a30}">`
          + `<span class="vzcr"><small>近 7 天</small><span class="vztrack1"><em style="--w:${(a7 / mx * 100).toFixed(0)}%"></em></span><b>${a7}<em>則</em></b></span>`
          + `<span class="vzcr"><small>近 30 天</small><span class="vztrack1"><i style="--w:${(a30 / mx * 100).toFixed(0)}%"></i></span><b>${a30}<em>則</em></b></span></div>`;
        return vzRow(ann ? 'bell' : 'news', 'event', ann ? '重大訊息（公司公告）' : '相關新聞', '', viz, p, ` data-vz="${ann ? 'ann' : 'news'}"`);
      }
      return vzRow('news', 'event', '消息', '', '', p);
    }).join('');
  }
  /* 九顆燈號的紅／灰／綠比例條（技術面最上面），整列寬 */
  function sigBar(sig) {
    if (!sig || !sig.L || !sig.L.length) return '';
    const n = sig.L.length, mid = n - sig.pos - sig.neg;
    const viz = `<div class="vzbar"><span class="vzratio" id="ovSigBar" data-pos="${sig.pos}" data-neg="${sig.neg}" role="img" aria-label="九顆技術燈號：偏多 ${sig.pos}、中性 ${mid}、偏空 ${sig.neg}">`
      + `<i class="pos" style="flex:${sig.pos}"></i><i class="mid" style="flex:${mid}"></i><i class="neg" style="flex:${sig.neg}"></i></span></div>`
      + `<div class="vzlg"><span><i class="pos"></i>偏多 ${sig.pos}</span><span><i class="mid"></i>中性或未出現 ${mid}</span><span><i class="neg"></i>偏空 ${sig.neg}</span></div>`;
    return `<ul class="vz vzonly"><li class="vzr" data-vz="sig"><div class="vzc"><div class="vzb"><div class="vzh" data-tone="tech"><span class="vzi" aria-hidden="true">${svgI('pulse', 13)}</span><b>九顆技術燈號</b>`
      + `<span class="vzhr"><span class="vztag">${sig.pos}多${sig.neg}空</span></span></div><div class="vzviz">${viz}</div></div></div></li></ul>`;
  }
  /* 一行重點下面的兩組小格子（回檔 6 格、突破 5 格，成立幾條亮幾格），兩組各占半列、格子等分撐滿 */
  function ckCells(pg) {
    const ck = pg && pg.analysis && pg.analysis.facets && pg.analysis.facets.tech && pg.analysis.facets.tech.checks;
    if (!ck || !ck.n_a) return '';
    const g = (nm, met, n, k) => `<span class="cg" data-ck="${k}" data-met="${met}" data-n="${n}" title="${nm} ${n} 條中 ${met} 條成立"><em>${nm}</em><span class="cells">${Array.from({ length: n }, (_, i) => `<i class="${i < met ? 'on' : ''}"></i>`).join('')}</span><b>${met}/${n}</b></span>`;
    return `<div class="ovcells" id="ovCkCells" role="img" aria-label="回檔型態 ${ck.n_a} 條中 ${ck.met_a} 條成立、突破型態 ${ck.n_b} 條中 ${ck.met_b} 條成立">${g('回檔型態', ck.met_a, ck.n_a, 'a')}${g('突破型態', ck.met_b, ck.n_b, 'b')}</div>`;
  }
  function vzCss() {
    if (document.getElementById('stockAiVzCss')) return;
    const st = document.createElement('style');
    st.id = 'stockAiVzCss';
    /* 預設（含手機）全部藏起來；只有桌機（>640 且不是 html.m4）才打開 —— 手機那份版面一個像素都不動（HANDOFF 跨 session 分工）*/
    const D = 'html:not(.m4) #ovAiCard';
    st.textContent = `
#ovAiCard .vzb,#ovAiCard .ovcells,#ovAiCard .aiico,#ovAiCard .vzonly{display:none}
@media (min-width:641px){
${D} .aiico{display:inline-flex;flex:none;width:15px;height:15px;color:var(--ink-3)}
${D} .aiico svg{width:15px;height:15px}
${D} .ovtag.on .aiico,${D} .ovtag:hover .aiico{color:inherit}
/* 四顆籤多了圖示＋方向符號，一列放不下（1440 三欄的右欄只有約 430px）→ 卡片窄於 640px 時每顆排成兩行：
   上＝圖示＋面向名、下＝▲偏多 判讀；寬卡片（≥640，例如 800 視窗單欄）照舊一行。任何寬度都不裁切、不重疊。*/
@container ovai (max-width:640px){
  ${D} .ovseg .ovtag{display:grid;grid-template-columns:auto auto;justify-content:center;align-content:center;column-gap:5px;row-gap:3px;padding:5px 4px}
  ${D} .ovseg .ovtag .aitag{grid-column:1 / -1;justify-self:center}
  ${D} .ovseg .ovtag .aicnt{display:none}
  ${D} .ovseg .ovtag .nl{display:inline} ${D} .ovseg .ovtag .ns{display:none}
}
${D} .aitag[data-dir]::before{margin-right:3px;font-size:12px}
${D} .aitag[data-dir="up"]::before{content:'▲'}
${D} .aitag[data-dir="down"]::before{content:'▼'}
${D} .aitag[data-dir="flat"]::before{content:'—'}
/* 小格子：兩組各占半列，格子等分（像日曆的日期格：1px 框、3px 圓角）*/
${D} .ovcells{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;margin-top:2px;font-size:12.5px;color:var(--ink-2);line-height:1.3}
${D} .ovcells .cg{display:flex;align-items:center;gap:6px;min-width:0}
${D} .ovcells em{font-style:normal;color:var(--ink-3);white-space:nowrap}
${D} .ovcells .cells{display:flex;gap:3px;flex:1 1 auto;min-width:0}
${D} .ovcells .cells i{flex:1 1 0;height:11px;border-radius:3px;border:1px solid var(--line);background:var(--panel-2)}
${D} .ovcells .cells i.on{background:color-mix(in srgb,var(--cyan) 70%,var(--panel-2));border-color:var(--cyan)}
${D} .ovcells b{font-family:var(--mono);font-weight:600;color:var(--ink)}
/* 每一條：標題列（小線條圖示＋粗體小標＋右側徽章）→ 整列寬小圖 → 原文（灰）。像日曆面板的小節（.sec）：上面一條細線分隔 */
${D} ul.vz{display:block;list-style:none;padding-left:0;margin:4px 0 0}
${D} ul.vz>li.vzr{display:block;margin:0;padding:8px 0 7px;border-top:1px solid var(--line)}
${D} ul.vz>li.vzr:first-child{border-top:0;padding-top:2px}
${D} .vzc{display:flex;flex-direction:column;gap:5px;min-width:0}
${D} .vzb{display:flex;flex-direction:column;gap:6px;min-width:0}
${D} .vzh{display:flex;align-items:center;gap:6px;min-width:0;font-size:13.5px;--tc:var(--cyan)}
${D} .vzh[data-tone="tech"]{--tc:var(--violet,#a78bfa)} ${D} .vzh[data-tone="fund"]{--tc:var(--amber)} ${D} .vzh[data-tone="event"]{--tc:var(--lime,var(--amber))}
${D} .vzi{display:inline-flex;flex:none;color:var(--tc)} ${D} .vzi svg{width:13px;height:13px;display:block}
${D} .vzh>b{font-weight:600;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
${D} .vzhr{margin-left:auto;display:flex;gap:6px;flex:none;align-items:center}
${D} .vzviz{min-width:0;width:100%}
${D} .vzt{font-size:12.5px;color:var(--ink-3);line-height:1.5}
/* 外框膠囊（日曆 .badge）：▲ 紅、▼ 綠 */
${D} .vzbd{display:inline-flex;align-items:baseline;gap:3px;padding:0 8px;border-radius:999px;border:1px solid currentColor;font-size:12px;line-height:18px;white-space:nowrap;color:var(--ink-3)}
${D} .vzbd i{font-style:normal;font-size:12px} ${D} .vzbd small{font-size:12px;color:var(--ink-3);margin-right:2px}
${D} .vzbd.pos{color:var(--rise)} ${D} .vzbd.neg{color:var(--fall)}
${D} .vztag{font-size:12px;padding:0 8px;border-radius:999px;background:var(--panel-3);color:var(--ink-2);white-space:nowrap;line-height:18px}
/* 數字格（ETF 配息面板上方那排）：等分整列 */
${D} .vzks{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:6px}
${D} .vzk{display:flex;flex-direction:column;align-items:center;gap:1px;padding:4px 6px 5px;border:1px solid var(--line);border-radius:8px;background:var(--panel-2);min-width:0}
${D} .vzk small{font-size:12px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
${D} .vzk b{font:600 15px var(--mono);color:var(--ink);white-space:nowrap}
${D} .vzk b i{font-style:normal;font-size:12px;margin-right:2px} ${D} .vzk b em{font-size:12px;font-weight:400;font-style:normal;color:var(--ink-3);margin-left:2px}
${D} .vzk.pos b{color:var(--rise)} ${D} .vzk.neg b{color:var(--fall)}
/* 進度條／比例條：整列寬 */
${D} .vzbar{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;min-width:0}
${D} .vzbar small{flex-basis:100%;font-size:12px;color:var(--ink-3)}
${D} .vzmeter{flex:1 1 auto;max-width:none;height:10px}
${D} .vzpct{font:600 13px var(--mono);color:var(--ink);flex:none}
${D} .vzratio{display:flex;flex:1 1 auto;height:10px;border-radius:3px;overflow:hidden;background:var(--panel-3);gap:1px}
${D} .vzratio i.pos,${D} .vzlg i.pos{background:var(--rise)} ${D} .vzratio i.neg,${D} .vzlg i.neg{background:var(--fall)}
${D} .vzratio i.mid,${D} .vzlg i.mid{background:color-mix(in srgb,var(--ink-3) 35%,transparent)}
${D} .vzlg{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:4px;font-size:12px;color:var(--ink-3)}
${D} .vzlg span{display:inline-flex;align-items:center;gap:5px}
${D} .vzlg i{display:inline-block;width:10px;height:10px;border-radius:3px}
/* 法人正負橫條：D 款（3px 小圓角、極淡底軌、同色漸層 55%→實色；賣超往左，漸層方向相反），整列寬 */
${D} .vzinst{display:flex;flex-direction:column;gap:5px}
${D} .vzib{display:grid;grid-template-columns:48px minmax(0,1fr) 76px;align-items:center;gap:8px}
${D} .vzib .vzn{font-size:12.5px;color:var(--ink-2)}
${D} .vzib b{font:600 13px var(--mono);text-align:right;color:var(--ink-2)}
${D} .vztrack{position:relative;height:12px;border-radius:3px;background:var(--panel-3)}
${D} .vztrack::after{content:'';position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--ink-3);opacity:.6}
${D} .vztrack>i{position:absolute;top:0;bottom:0;width:var(--w,0%)}
${D} .vztrack>i.pos{left:50%;border-radius:0 3px 3px 0;background:linear-gradient(90deg,color-mix(in srgb,var(--rise) 55%,transparent),var(--rise))}
${D} .vztrack>i.neg{right:50%;border-radius:3px 0 0 3px;background:linear-gradient(270deg,color-mix(in srgb,var(--fall) 55%,transparent),var(--fall))}
${D} b.pos{color:var(--rise)} ${D} b.neg{color:var(--fall)}
/* 直條（CalGrid.mini）：整列寬；數字列與期別列跟圖的類別格等分對齊（圖左右各留 2px）*/
${D} .vzcols{display:flex;flex-direction:column;gap:2px;width:100%}
${D} .vzcols .cgmini{height:64px}
${D} .vzcv,${D} .vzcl{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));padding:0 2px;text-align:center}
${D} .vzcv b{font:600 13px var(--mono);color:var(--ink-2)} ${D} .vzcv b.cat{color:var(--ink)}
${D} .vzcl small{font:12px var(--mono);color:var(--ink-3)}
/* 消息面：近 7 天／近 30 天兩列橫條，整列寬 */
${D} .vzcnt{display:flex;flex-direction:column;gap:5px}
${D} .vzcr{display:grid;grid-template-columns:56px minmax(0,1fr) 44px;align-items:center;gap:8px}
${D} .vzcr small{font-size:12px;color:var(--ink-3)}
${D} .vzcr b{font:600 13px var(--mono);color:var(--ink);text-align:right} ${D} .vzcr b em{font-size:12px;font-weight:400;font-style:normal;color:var(--ink-3);margin-left:2px}
${D} .vztrack1{position:relative;height:12px;border-radius:3px;background:var(--panel-3)}
${D} .vztrack1>i,${D} .vztrack1>em{position:absolute;left:0;top:0;bottom:0;width:var(--w,0%);border-radius:0 3px 3px 0;
  background:linear-gradient(90deg,color-mix(in srgb,var(--amber) 55%,transparent),var(--amber))}
}`;
    document.head.appendChild(st);
  }
  function ovCard(pg, fmt, sig) {
    ovCss(); css(); vzCss();
    const an = pg && pg.analysis;
    const fc = facetCards(pg, fmt) || {};
    /* 技術面訊號那張（StockSignal.view 的出口，一字不改）緊接在技術面後面，CSS 讓它跟技術面同時顯示（data-cur="tech"）。
       沒有 AI 分析（fc.tech 空）時它自己當技術面那一面。*/
    const panes = [['tech', fc.tech], ['sig', sig], ['chip', fc.chip], ['fund', fc.fund], ['news', fc.news]].filter(x => x[1]);
    const have = panes.map(x => x[0]).filter(k => k !== 'sig');
    if (sig && !fc.tech) have.unshift('tech');
    const cur = have.length ? readOvTab(have) : '';
    const how = window.App && window.App.howHTML ? window.App.howHTML('', [
      '一行重點＝回檔、突破兩套型態成立幾條＋停損距離',
      '四顆籤＝技術、籌碼、基本、消息面',
      '技術面含九顆訊號燈，籤上「5多0空」是燈號計數',
      '籌碼面看法人、融資、大戶；當沖、融券只列參考',
      '各面向不加總、非投資建議',
    ]) : '';
    const tg = facetTags(pg, fmt).filter(t => have.includes(t.k));
    const tabs = tg.length >= 2 ? `<div class="seg ovseg" id="ovAiTags" role="tablist" aria-label="AI 分析四個面向">${tg.map(t => {
      const on = t.k === cur;
      return `<button type="button" class="ovtag${on ? ' on' : ''}" role="tab" data-facet="${t.k}" id="ovT-${t.k}" aria-selected="${on}" tabindex="${on ? 0 : -1}" aria-controls="ovF-${t.k}" title="${esc(t.tip)}">`
        + `<span class="aiico" aria-hidden="true">${svgI((FICON[t.k] || FICON.tech)[0], 15)}</span>`
        + `${nmHTML(t.nm, t.sh)}<span class="aitag ${t.cls}"${DIRCH(t.lb) ? ` data-dir="${DIRCH(t.lb)}"` : ''}>${esc(t.lb)}</span>${t.cnt}</button>`; }).join('')}</div>` : '';
    return `<div class="card" id="ovAiCard"><h3>AI 分析 <small data-warn role="note" title="由固定規則與公開資料自動產生（技術評分、SMC 結構、九顆技術燈號、法人與融資、集保大戶、本益比分位、營收與 EPS、公告新聞），非投資建議">${esc(discLine())}</small>`
      + ` <button class="howbtn pop" data-how="ovai" type="button" aria-label="AI 分析怎麼看">?</button>`
      + `</h3><div class="howtxt" id="how-ovai" hidden>${how}</div>`
      + brief(pg) + tabs
      + (panes.length ? `<div class="ovpanes" id="ovFacets" data-cur="${cur}" data-n="${panes.length}">${panes.map(x => x[1]).join('')}</div>` : '')
      + `</div>`;
  }
  function techCard(t, fmt, sig) {
    if (!t) return '';
    const tag = `<span class="aitag ${toneCls(t.label)}">${esc(t.label || '資料缺')}</span>`;
    /* 1 小時、4 小時都沒資料而且原因一樣 → 併成一列，不重複兩次同一句話 */
    let tfs = (t.tfs || []).slice();
    const nod = tfs.filter(r => r.trend == null && (r.tf === '60m' || r.tf === '240m'));
    if (nod.length === 2 && (nod[0].points || []).join() === (nod[1].points || []).join()) {
      tfs = [{ tf: '60m+240m', label: '1 小時／4 小時', trend: null, word: nod[0].word, points: nod[0].points }].concat(tfs.filter(r => !nod.includes(r)));
    }
    const rows = tfs.map(r => `<span class="tfn" data-tf="${esc(r.tf)}">${esc(r.label)}</span><span class="aitag ${r.trend > 0 ? 'pos' : r.trend < 0 ? 'neg' : ''}">${esc(r.word)}</span>`
      + `<span class="tfp">${esc((r.points || []).join('・'))}</span>`).join('');
    const ck = t.checks;
    let ckHTML = '';
    if (ck && ck.n_a) {
      const dots = (met, n) => `<span class="dots" role="img" aria-label="${n} 條中 ${met} 條成立">${Array.from({ length: n }, (_, i) => `<i class="${i < met ? 'on' : ''}"></i>`).join('')}</span>`;
      const ra = ck.risk && ck.risk.a;
      let risk = '';
      if (ra && ra.pct != null) {
        const mx = Number(ra.max != null ? ra.max : 8), pct = Number(ra.pct);
        const top = Math.max(mx * 2, pct * 1.15);           // 刻度範圍：至少到上限的兩倍，超過時多留 15% 讓點不貼邊
        risk = `<span class="ckn">停損距離</span><span class="meter" style="--p:${Math.min(100, pct / top * 100).toFixed(1)}%;--c:${ra.ok ? 'var(--cyan)' : 'var(--amber)'}" role="img" aria-label="停損距離 ${pct.toFixed(1)}%，上限 ${mx}%"><i></i><b class="tick" style="left:${(mx / top * 100).toFixed(1)}%" title="上限 ${mx}%"></b></span>`
          + `<b class="${ra.ok ? '' : 'warn'}" data-risk="${pct}">${pct.toFixed(1)}%</b>`;
      }
      ckHTML = `<div class="ovsub">型態條件（成立幾條）</div><div class="ovck" id="ovCk">`
        + `<span class="ckn">回檔型態</span>${dots(ck.met_a, ck.n_a)}<b data-met="${ck.met_a}/${ck.n_a}">${ck.met_a}/${ck.n_a}</b>`
        + `<span class="ckn">突破型態</span>${dots(ck.met_b, ck.n_b)}<b data-met="${ck.met_b}/${ck.n_b}">${ck.met_b}/${ck.n_b}</b>${risk}</div>`;
    }
    const lv = t.levels || {};
    const z = (a) => (a && a[0] ? `<b>${esc(fmt.n(a[0].low))}–${esc(fmt.n(a[0].high))}</b>（${esc(a[0].label || '')}，距 ${esc(fmt.pct(a[0].dist_pct))}）` : '');
    const lvHTML = `<div class="ovlv">最近支撐 ${z(lv.support) || '<span class="muted">下方沒有通過門檻的需求區</span>'}<br>最近壓力 ${z(lv.resistance) || '<span class="muted">上方沒有通過門檻的供給區</span>'}</div>`;
    const ckList = (arr) => (arr || []).map(c => `<div class="ck ${c.ok ? 'ok' : 'no'}"><span class="m">${c.ok ? '✓' : '✗'}</span><span><b>${esc(c.name)}</b>：${esc(c.text)}</span></div>`).join('');
    const det = `<div class="ovdet" id="ovTechDet" hidden>
        <div class="ovsub">綜合：${esc(t.stance || '—')} 的原因</div><ul>${(t.reasons || []).map(x => `<li>${esc(x)}</li>`).join('') || '<li>—</li>'}</ul>
        ${ck ? `<div class="ovsub">回檔型態（A）逐條</div>${ckList(ck.a)}<div class="ovsub">突破型態（B）逐條</div>${ckList(ck.b)}` : ''}
        ${t.ifs && t.ifs.length ? `<div class="ovsub">若…則…（狀態會在什麼情況下改變）</div><ul>${t.ifs.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
        ${t.plan ? `<div class="ovsub">${esc(t.plan)}</div>` : ''}</div>`;
    return `<div class="card ovfacet" id="ovF-tech" data-facet="tech" data-ai><h3>技術面 ${tag}</h3>${t.why ? `<p class="ovwhy">${esc(t.why)}</p>` : ''}
      ${sigBar(sig)}<div class="ovtfs" id="ovTfs">${rows}</div>${ckHTML}${lvHTML}
      <button type="button" class="ovmore" id="ovTechMore" aria-expanded="false" aria-controls="ovTechDet">▸ 看細節：原因・逐條條件・若…則…</button>${det}</div>`;
  }
  function chipFacet(pg, x) {
    if (!x) return '';
    const ex = chipExtra(pg);
    return `<div class="card ovfacet" id="ovF-chip" data-facet="chip" data-ai><h3>籌碼面 <span class="aitag ${toneCls(x.label)}">${esc(x.label || '資料缺')}</span></h3>`
      + `${x.why ? `<p class="ovwhy">${esc(x.why)}</p>` : ''}${x.points && x.points.length ? `<ul class="vz">${chipRows(pg, x.points)}</ul>` : '<div class="empty">籌碼面資料缺</div>'}`
      + `${ex.length ? `<div class="ovsub">參考（不計入判讀）</div>${ul(ex)}` : ''}</div>`;
  }
  function fundFacet(x) {
    if (!x) return '';
    return `<div class="card ovfacet" id="ovF-fund" data-facet="fund" data-ai><h3>基本面 <span class="aitag ${toneCls(x.label)}">${esc(x.label || '資料缺')}</span></h3>`
      + `${x.why ? `<p class="ovwhy">${esc(x.why)}</p>` : ''}${x.points && x.points.length ? `<ul class="vz">${fundRows(x.points)}</ul>` : '<div class="empty">基本面資料缺</div>'}</div>`;
  }
  function newsFacet(x) {
    if (!x) return '';
    const items = (x.items || []).slice(0, 4).map(it => {
      const d = esc(String(it.date || '').slice(5));
      const ttl = esc(String(it.title || '').replace(/\s+/g, ''));
      if (it.kind === '新聞' && it.url) return `<li><span class="kind">新聞</span><span class="mono">${d}</span> <a href="${esc(it.url)}" target="_blank" rel="noopener">${ttl}</a></li>`;
      return `<li><span class="kind">${esc(it.kind)}</span><span class="mono">${d}</span> <a href="#" data-ovtab="news">${ttl}</a></li>`;
    }).join('');
    return `<div class="card ovfacet" id="ovF-news" data-facet="news" data-ai><h3>消息面 <span class="aitag ${toneCls(x.label)}">${esc(x.label || '資料缺')}</span></h3>`
      + `${x.why ? `<p class="ovwhy">${esc(x.why)}</p>` : ''}${x.points && x.points.length ? `<ul class="vz">${newsRows(x)}</ul>` : ''}${items ? `<div class="ovsub">最新 ${Math.min(4, (x.items || []).length)} 則</div><ul class="ovnews">${items}</ul>` : ''}</div>`;
  }
  function facetCards(pg, fmt) {
    ovCss(); css();
    const an = pg && pg.analysis;
    if (!an) return null;
    const f = an.facets || {};
    return { tech: techCard(f.tech, fmt, sigCount(pg, fmt)), chip: chipFacet(pg, f.chip), fund: fundFacet(f.fund), news: newsFacet(f.news) };
  }
  function bindOverview(root) {
    if (!root) return;
    // 10-10 第二版：營收 YoY／EPS 小直條是日曆面板那支 CalGrid.mini，innerHTML 之後要 mount 才畫得出來
    if (window.CalGrid && window.CalGrid.mount) { try { window.CalGrid.mount(root.querySelector('#ovAiCard') || root); } catch (e) { /* 小圖畫不出來不影響其他 */ } }
    /* ★ #297：分頁籤＝在同一張卡內切換那一面（改前＝捲到下面那一張細節卡）。不捲動、不跳頁 */
    const tabs = [...root.querySelectorAll('#ovAiTags .ovtag')];
    tabs.forEach(b => b.onclick = () => setOvTab(root, b.dataset.facet, true));
    // 方向鍵左右換籤（WAI-ARIA tabs 慣例），焦點跟著走
    const tl = root.querySelector('#ovAiTags');
    if (tl) tl.onkeydown = (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const i = tabs.indexOf(document.activeElement); if (i < 0) return;
      const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      n.focus(); n.click(); e.preventDefault();
    };
    const mb = root.querySelector('#ovTechMore');
    if (mb) mb.onclick = () => {
      const d = root.querySelector('#ovTechDet'); if (!d) return;
      const open = d.hidden; d.hidden = !open;
      mb.setAttribute('aria-expanded', String(open));
      mb.textContent = (open ? '▾ 收起細節' : '▸ 看細節：原因・逐條條件・若…則…');
    };
    // 重大訊息沒有外部網址：點標題切到「公告 / 新聞」分頁（站內既有的那一頁）
    root.querySelectorAll('[data-ovtab]').forEach(a => a.onclick = (e) => {
      e.preventDefault();
      const b = document.querySelector(`#stockTabs button[data-t="${a.dataset.ovtab}"]`);
      if (b) { b.click(); try { b.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (er) { b.scrollIntoView(); } }
    });
  }

  /* ★ 2026-10-05（Andy：「這邊技術面，在上方『指標』需要新增，可以看到技術分析，但記得標明這不構成投資建議」）：
     個股頁「指標」分頁頂部的技術分析卡。內容＝AI 卡技術面面板同一個 techHTML＋sigHTML（不另寫一份邏輯，兩處永遠一致），
     差別只在：① 完整攤開（逐條條件直接展開、不限高、不捲動）② 卡頂固定一行免責 ③ id 改 tt 前綴 —— AI 卡同時在頁面上，id 不能撞。*/
  function techCardHTML(pg, fmt) {
    css();
    const an = pg && pg.analysis;
    const t = an && an.facets && an.facets.tech;
    const sig = sigCount(pg, fmt);
    const body = an ? ttCols((techHTML(t, fmt) + `<div class="aisub" data-tt="sig">技術面訊號</div>` + sigHTML(pg, sig))
      .replace(/id="ai(Tfs|Why|Sig)"/g, 'id="tt$1"').replace('<div class="aickbody" hidden>', '<div class="aickbody">'))
      : '<div class="empty">尚無技術分析資料</div>';
    return `<div class="card" id="tagTech"><div class="tthead"><h3>技術分析</h3>${t && t.stance ? `<span class="grade ${stanceCls(t.stance)}">${esc(t.stance)}</span>` : ''}</div>
      <div class="ttwarn" id="ttWarn" role="note">${esc(discLine())}</div>${body}</div>`;
  }
  /* 2026-10-06 一屏看完：把同一份 techHTML＋sigHTML 分成左右兩欄（CSS 只在卡寬 ≥ 760 才並排，見 #tagTech .ttcols）。
     左＝讀的（四週期、綜合原因、若…則…、規則推算、支撐壓力）；右＝對照清單（逐條條件 .aick、「技術面訊號」小標以後的九顆燈）。
     用 DOM 分組而不是另寫一份 HTML：內容永遠跟 AI 卡技術面那一面同一支 techHTML 產出，兩處不會分家。*/
  function ttCols(html) {
    const box = document.createElement('div');
    box.innerHTML = html;
    const L = [], R = [];
    let sigOn = false;
    [...box.childNodes].forEach(n => {
      if (n.nodeType === 1 && n.dataset.tt === 'sig') sigOn = true;
      if (n.nodeType === 3 && !n.textContent.trim()) return;           // 樣板字串裡的換行空白
      (sigOn || (n.nodeType === 1 && n.classList.contains('aick')) ? R : L).push(n);
    });
    const out = (arr, cls) => `<div class="${cls}">${arr.map(n => (n.nodeType === 1 ? n.outerHTML : esc(n.textContent))).join('')}</div>`;
    return `<div class="ttcols">${out(L, 'ttmain')}${out(R, 'ttside')}</div>`;
  }
  window.StockAI = { id: 'stock.mtf', html, techCardHTML, mount, refit, brief, briefText, facetCards, ovCard, bindOverview, _key: KEY, _tabKey: TAB_KEY, _ovTabKey: OV_TAB_KEY, _splitKey: SPLIT_KEY };
})();
