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
         · 第二列：結論（觀望／可留意／偏空＋一句帶數字的原因，#skAiLine）
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

   狀態（兩個 localStorage）：
     · tw.aiOpen：內容區收合／展開。收合時只留結論列＋四顆標籤小字。沒記過：桌機展開、手機收起。
       收合時按任何一顆標籤＝展開並切到那一面（標籤本身就是入口，不另外放一顆「展開分析」）。
     · tw.aiTab：選中的面向（tech／sig／fund／news），重新整理後還在。沒記過＝技術面。

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
  const WIDE = 600;        // K 線卡寬度 ≥ 這個值才走「右欄跨兩列」（量測表在檔頭；窄卡片兩欄比單欄少推 K 線約 100px）
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* ★ 2026-09-28（Andy：「將 "AI分析" 內容替換掉 籌碼 -> 技術面訊號」）：第二顆標籤「籌碼面」換成「技術面訊號」。
     理由：籌碼已經拆成個股頁下方「法人｜資券｜大戶／散戶」三個獨立分頁，AI 區再放一份籌碼摘要是重複；
     換成總覽「技術面訊號」卡那九顆燈（均線、結構、RSI、KD、MACD、乖離、BOS、CHoCH、假跌破），燈號從 StockSignal.lights() 拿，兩處永遠一致。
     payload 的 analysis.facets.chip 照舊產出（其他地方可能在讀），這裡不再顯示。
     舊的 tw.aiTab＝'chip' 讀不到 → readTab 退回技術面。*/
  const FACETS = [['tech', '技術面'], ['sig', '技術面訊號'], ['fund', '基本面'], ['news', '消息面']];
  // 紅漲綠跌：偏多用 .pos（紅）、偏空用 .neg（綠）；留意＝琥珀色
  const toneCls = (lb) => lb === '偏多' ? 'pos' : lb === '偏空' ? 'neg' : lb === '留意' ? 'warn' : '';
  const stanceCls = (s) => s === '可留意' ? 'A' : s === '偏空' ? 'N' : 'W';

  function readOpen() {
    try { const v = localStorage.getItem(KEY); if (v === '1' || v === '0') return v === '1'; } catch (e) { /* 私密視窗 */ }
    return !(window.innerWidth <= 640);
  }
  function saveOpen(v) { try { localStorage.setItem(KEY, v ? '1' : '0'); } catch (e) { /* 忽略 */ } }
  function readTab() {
    try { const v = localStorage.getItem(TAB_KEY); if (FACETS.some(f => f[0] === v)) return v; } catch (e) { /* 忽略 */ }
    return 'tech';
  }
  function saveTab(v) { try { localStorage.setItem(TAB_KEY, v); } catch (e) { /* 忽略 */ } }

  function css() {
    if (document.getElementById('stockAiCss')) return;
    const st = document.createElement('style');
    st.id = 'stockAiCss';
    st.textContent = `
/* ---- K 線卡兩欄（卡片夠寬時，JS 加 .aiside）：右欄 #skAi 跨「名稱區」與「工具列」兩列 */
/* 右欄最窄 300px：四顆標籤疊成兩行後每顆約 70px 放得下；最寬 44%，左欄（名稱／現價／工具列）至少留一半多 */
#skChartCard.aiside{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,44%);column-gap:20px;align-items:start}
#skChartCard.aiside>*{grid-column:1 / -1;min-width:0}
#skChartCard.aiside>#skHead{grid-column:1;grid-row:1;align-self:start}
/* 工具列貼在左欄底部＝緊貼 K 線；AI 區比左欄高時多出來的空白落在名稱區與工具列之間，不落在工具列與 K 線之間 */
#skChartCard.aiside>#skTools{grid-column:1;grid-row:2;align-self:end}
/* 右欄不畫外框（外框＋內距要多吃 22px 高度＝K 線多被推 22px），只用左側一條分隔線跟名稱區分開 */
#skChartCard.aiside>#skAi{grid-column:2;grid-row:1 / span 2;align-self:stretch;margin-top:0;
  border-left:1px solid var(--line);padding-left:18px}
/* 內容區高度：兩欄時 132px（量過：1440 左欄＝名稱區 121＋工具列 50 ＝ 171px，AI 區固定部分約 95px，
   132 讓 K 線最多被推約 55px；卡片再窄一點工具列會折行，左欄變高、內容區自動吃掉多出來的高度）。
   單欄（卡片 < WIDE＝600，只剩「右側事件欄開著＋視窗很窄」會走到）時 AI 區只能排在名稱區下面、一定會推 K 線，所以壓到 110px（約 5～6 行，底部淡出提示還能捲）。*/
/* container：AI 區自己多寬決定標籤排法（兩欄時跟著卡片寬窄變、手機搬進 #aiCard 又是另一個寬度，看視窗寬猜不準）*/
#skAi{--aibh:132px;display:flex;flex-direction:column;gap:5px;min-width:0;container:aibox / inline-size}
#skChartCard:not(.aiside)>#skAi{--aibh:110px;margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
/* 單欄（退路）：標題與結論併成同一列（標題｜結論｜收合），省下一整列 ≈ 25px。
   這不只是好看：工具列每往下 1px，K 線「指標 ▾」下拉在矮視窗下方的空間就少 1px ——
   少到 320px 以下它會改往上開（placePop 的判準），蓋住 AI 區。結論太長就在中間那欄自己折行。*/
#skChartCard:not(.aiside)>#skAi{display:grid;grid-template-columns:auto minmax(0,1fr) auto;column-gap:12px;row-gap:5px;align-items:center}
#skChartCard:not(.aiside)>#skAi>.aihead{display:contents}
#skChartCard:not(.aiside)>#skAi>.aihead>h3{grid-column:1;grid-row:1}
#skChartCard:not(.aiside)>#skAi>.aisum{grid-column:2;grid-row:1}
#skChartCard:not(.aiside)>#skAi>.aihead>.btn{grid-column:3;grid-row:1}
#skChartCard:not(.aiside)>#skAi>.aitabs,#skChartCard:not(.aiside)>#skAi>.aibody{grid-column:1 / -1}
#skAi .aihead{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
#skAi .aihead h3{margin:0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:15px}
#skAi .aihead h3 small{font-size:12px;color:var(--amber);font-weight:500}
#skAi .aihead .btn{min-height:26px;padding:0 10px}
#skAi .aisum{display:flex;align-items:baseline;gap:8px;min-width:0;font-size:13.5px;color:var(--ink-2);line-height:1.45}
#skAi .aisum .grade{flex:none;white-space:nowrap}
#skAi .aisum .aibrief{min-width:0}
.grade.N{background:rgba(46,229,157,.16);color:var(--fall)}
/* 四顆標籤：一列排滿、等寬；每顆＝面向名＋判讀小字 */
/* 2026-09-28：第二顆從「籌碼面」換成「技術面訊號」（名字多兩個字＋小字「4多2空」），等寬四欄在 1100 寬會溢出壓到隔壁 →
   第二欄給 1.4 倍寬；真的還是放不下時，判讀小字自己換到第二行（flex-wrap），絕不溢出按鈕。*/
#skAi .aitabs{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr) minmax(0,1fr) minmax(0,1fr);gap:4px;border-bottom:1px solid var(--line)}
#skAi .aitab{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:0 6px;min-width:0;padding:4px 4px 5px;border:0;
  border-bottom:2px solid transparent;margin-bottom:-1px;background:none;color:var(--ink-2);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
#skAi .aitab:hover{color:var(--ink)}
#skAi .aitab.on{color:var(--ink);font-weight:700;border-bottom-color:var(--cyan)}
#skAi .aitab .aitag{font-weight:500}
#skAi:not(.aiopen) .aitab.on{font-weight:400;border-bottom-color:transparent;color:var(--ink-2)}
#skAi:not(.aiopen) .aitabs{border-bottom-color:transparent}
.aitag{padding:1px 7px;border-radius:6px;font-size:12px;background:var(--panel-3);color:var(--ink-2);white-space:nowrap}
.aitag.pos{background:rgba(255,77,109,.16);color:var(--rise)} .aitag.neg{background:rgba(46,229,157,.16);color:var(--fall)}
.aitag.warn{background:rgba(255,180,84,.16);color:var(--amber)}
/* 內容區：固定高度、區內捲動（不撐高標題列）。收合＝整個 hidden */
#skAi .aibody{height:var(--aibh);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;padding-right:4px;min-width:0}
#skChartCard.aiside>#skAi .aibody{flex:1 1 var(--aibh);height:auto;min-height:var(--aibh)}
/* 下面還有字 → 底部淡出一條，提示「區內還能往下捲」（捲到底就拿掉）*/
#skAi .aibody.more{-webkit-mask-image:linear-gradient(#000 calc(100% - 22px),transparent);mask-image:linear-gradient(#000 calc(100% - 22px),transparent)}
#skAi .aisec h4{margin:0 0 4px;font-size:13px;font-weight:400;color:var(--ink-2)}
#skAi ul{margin:2px 0 0;padding-left:18px;color:var(--ink-2);font-size:13px;line-height:1.55}
#skAi li{margin:2px 0}
#skAi .aitfs{display:grid;grid-template-columns:auto auto 1fr;gap:4px 10px;align-items:baseline;font-size:13px}
#skAi .aitfs .tfn{color:var(--ink-3);white-space:nowrap}
#skAi .aitfs .aitag{justify-self:start}
#skAi .aitfs .tfp{color:var(--ink-2);line-height:1.5;min-width:0}
#skAi .aisub{margin-top:8px;font-size:12.5px;color:var(--ink-3);font-weight:600}
#skAi .ailv{display:grid;grid-template-columns:1fr 1fr;gap:10px}
#skAi .ailv .k{background:var(--panel-3);border-radius:9px;padding:5px 9px;margin-top:5px;font-size:12.5px}
#skAi .ailv .k b{font-family:var(--mono)}
/* 逐條條件用「按鈕＋hidden」而不是 <details>：收起來的 <details> 內容在 Chrome 仍量得到外框，
   _preview 的文字重疊掃描會把它跟下面的支撐壓力區判成重疊（2026-09-26 實測）。*/
#skAi .aick{margin-top:6px;font-size:12.5px;color:var(--ink-2)}
#skAi .aickbtn{background:none;border:0;padding:2px 0;color:var(--ink-3);cursor:pointer;font:inherit;text-align:left}
#skAi .aickbtn:hover{color:var(--cyan)}
#skAi .ck{display:flex;gap:6px;margin:3px 0} #skAi .ck .m{flex:none;width:14px;font-weight:700}
#skAi .ck.ok .m{color:var(--rise)} #skAi .ck.no .m{color:var(--ink-3)}
#skAi .ainews a{color:var(--cyan)}
#skAi .ainews .kind{font-size:11.5px;color:var(--ink-3);margin-right:4px}
#skAi .aiasof{margin-top:8px;font-size:12px;color:var(--ink-3)}
/* AI 區窄（兩欄的窄卡片、手機）：標籤疊成兩行、標題列不讓收合鈕掉到第二行、「?」緊跟在「AI 分析」後面
   （改前手機上「?」會自己孤零零掉到第二行），技術面週期列與支撐壓力改單欄 */
@container aibox (max-width:380px){
  #skAi .aihead{flex-wrap:nowrap;align-items:flex-start}
  #skAi .aihead h3{flex:1 1 auto;min-width:0;row-gap:2px}
  #skAi .aihead h3 small{order:2;flex-basis:100%}
  #skAi .aihead .btn{flex:none}
  #skAi .aitab{flex-direction:column;gap:2px;padding:4px 2px 6px}
  #skAi .aitfs{grid-template-columns:auto 1fr} #skAi .aitfs .tfp{grid-column:1 / -1;margin:-2px 0 4px}
  #skAi .ailv{grid-template-columns:1fr}
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
    return FACETS.map(([k, nm]) => {
      const x = f[k] || {};
      const lb = k === 'sig' ? sig.label : (x.label || '資料缺');
      const cls = k === 'sig' ? sig.tone : toneCls(lb);
      const tip = k === 'sig' ? `九顆技術燈號：偏多 ${sig.pos}、偏空 ${sig.neg}` : (x.why || '');
      const on = k === cur;
      return `<button type="button" role="tab" class="aitab${on ? ' on' : ''}" id="aiTab-${k}" data-facet="${k}" aria-selected="${on}" aria-controls="aiPanel-${k}" title="${esc(tip)}">`
        + `<span class="nm">${nm}</span><span class="aitag ${cls}">${esc(lb)}</span></button>`;
    }).join('');
  }
  function sigHTML(pg, sig) {
    if (!sig.L.length) return '<div class="empty">技術面訊號資料缺</div>';
    const v = (pg && pg.verdict) || {};
    return `<h4>九顆燈號：紅＝偏多 ${sig.pos}、綠＝偏空 ${sig.neg}、灰＝中性或未出現</h4>
      <div class="lights aisig" id="aiSig">${sig.L.map(window.StockSignal.chip).join('')}</div>
      <ul>
        <li>均線看 5／20／60／120 日排列；結構看高低點是否墊高</li>
        <li>RSI 50 以上、K 在 D 上、MACD 柱為正＝短線偏多</li>
        <li>BOS＝突破前高；CHoCH＝結構轉向；假跌破＝破底又收回</li>
      </ul>
      ${v.invalidation ? `<div class="aisub">失效條件：${esc(v.invalidation)}</div>` : ''}`;
  }

  const why = (x) => x && x.why ? `<h4>${esc(x.why)}</h4>` : '';
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
    const open = readOpen();
    const cur = readTab();
    const how = window.App && window.App.howHTML ? window.App.howHTML('這一塊：四個面向的規則式判讀。', [
      '「AI 分析」是寫死的規則算的，非語言模型',
      '技術：SMC 結構、均線、RSI、支撐壓力',
      '狀態＝回檔、突破兩套型態條件是否成立',
      '訊號＝均線、RSI、KD 等九顆燈；基本看估值營收',
      '消息只數公告新聞；四面向不加總、非建議',
    ]) : '';
    const head = `<div class="aihead"><h3>AI 分析 <small data-warn id="aiWarn" title="這一塊由固定規則與公開資料自動產生（技術評分、SMC 結構、回檔與突破兩套條件、九顆技術燈號、本益比分位、營收與 EPS、公告新聞則數），不是大型語言模型，也不是任何人的投資建議。同一份資料永遠得到同一段文字。">規則式自動判讀，非投資建議</small>
        <button class="howbtn pop" data-how="ai" type="button" aria-label="AI 分析怎麼看">?</button></h3>
      <button class="btn small" id="aiTgl" type="button" aria-expanded="${open}" aria-controls="aiBody">${open ? '收合 ▴' : '展開 ▾'}</button></div>
      <div class="howtxt" id="how-ai" hidden>${how}</div>`;
    const hd = (an && an.headline) || {};
    const stance = hd.stance || v.verdict || '—';
    const brief = hd.brief || ((v.reasons || [])[0] || '');
    const sum = `<div class="aisum" id="skAiLine" data-readout><span class="grade ${stanceCls(stance)}" id="skAiStance">${esc(stance)}</span><span class="aibrief">${esc(brief)}</span></div>`;
    if (!an) {
      const sm = pg && pg.mtf && pg.mtf.summary;
      return head + `<div class="aisum" id="skAiLine" data-readout><span class="aibrief">${sm && sm.headline ? esc(sm.headline) : '資料不足'}</span></div>
        <div class="aibody" id="aiBody"${open ? '' : ' hidden'}><div class="empty">AI 分析資料準備中（下一次盤後更新後出現）</div></div>`;
    }
    const f = an.facets || {};
    const sig = sigCount(pg, fmt);
    return head + sum
      + `<div class="aitabs" role="tablist" aria-label="AI 分析面向" id="aiTabs">${tabs(an, cur, sig)}</div>
      <div class="aibody" id="aiBody" data-readout${open ? '' : ' hidden'}>
        ${panel('tech', cur, techHTML(f.tech, fmt))}
        ${panel('sig', cur, sigHTML(pg, sig))}
        ${panel('fund', cur, `${why(f.fund)}${ul((f.fund || {}).points) || '<div class="empty">基本面資料缺</div>'}`)}
        ${panel('news', cur, newsHTML(f.news))}
        <div class="aiasof">資料到 ${esc(an.as_of || '—')}</div>
      </div>`;
  }

  function setOpen(host, v) {
    const body = host.querySelector('#aiBody'), tgl = host.querySelector('#aiTgl');
    if (body) body.hidden = !v;
    if (tgl) { tgl.textContent = v ? '收合 ▴' : '展開 ▾'; tgl.setAttribute('aria-expanded', String(v)); }
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

  /* 卡片寬窄 → 兩欄／單欄。量的是 K 線卡本身（右側事件欄開關、⤢ 寬版都會改它），不是視窗寬。
     ⚠ 手機（≤640）#skAi 已被搬去 #aiCard，這裡一律拿掉 .aiside，免得卡片留一個空的右欄。*/
  function watchWidth(host) {
    const card = document.getElementById('skChartCard');
    if (!card) return;
    const fit = () => {
      const on = host.parentElement === card && window.innerWidth > 640 && card.clientWidth >= WIDE;
      if (card.classList.contains('aiside') !== on) card.classList.toggle('aiside', on);
      moreHint(host);
    };
    fit();
    if (card._aiRO) card._aiRO.disconnect();
    if (window.ResizeObserver) { card._aiRO = new ResizeObserver(fit); card._aiRO.observe(card); }
    card._aiFit = fit;
  }

  function mount(pg, host, fmt) {
    if (!host) return;
    css();
    host.innerHTML = html(pg, fmt);
    setOpen(host, readOpen());
    const tgl = host.querySelector('#aiTgl');
    if (tgl) tgl.onclick = () => { const v = host.querySelector('#aiBody').hidden; saveOpen(v); setOpen(host, v); };
    host.querySelectorAll('.aitab').forEach(b => b.onclick = () => {
      const k = b.dataset.facet;
      saveTab(k); setTab(host, k);
      // 收合時按標籤＝展開並看那一面（標籤就是入口）
      if (host.querySelector('#aiBody') && host.querySelector('#aiBody').hidden) { saveOpen(true); setOpen(host, true); }
    });
    // 標籤列支援方向鍵（WAI-ARIA tabs 的慣例）
    const tl = host.querySelector('#aiTabs');
    if (tl) tl.onkeydown = (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const bs = [...tl.querySelectorAll('.aitab')]; const i = bs.indexOf(document.activeElement);
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

  // app.js miaStock 搬完節點後叫一次，讓兩欄／單欄立刻跟上（不必等 ResizeObserver）
  function refit() { const c = document.getElementById('skChartCard'); if (c && c._aiFit) c._aiFit(); }

  window.StockAI = { id: 'stock.mtf', html, mount, refit, _key: KEY, _tabKey: TAB_KEY };
})();
