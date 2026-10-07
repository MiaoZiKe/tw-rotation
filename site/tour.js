/* ============================================================================
   逐步導覽（spotlight tour）—— window.TwTour（2026-10-07，分支 claude/tour）
   ----------------------------------------------------------------------------
   Andy 10-07 02:35：「平台導覽太爛了，需要有真的導覽的感覺一部一部告訴你總覽看什麼 哪些功能在哪裡，
   分頁是在說明什麼等等」。舊的「平台導覽」（site/legal.js）是一張彈窗列四句話，沒有指著畫面上的任何東西。

   這支做的事：畫面變暗、聚光燈框住「現在在講的那個實際元素」、旁邊一張說明卡（標題＋2～3 行白話＋上一步／下一步／略過）。
     · 需要換頁的步驟自己改 hash、等元素真的畫出來（尺寸連兩次量到一樣）才框；
     · 元素找不到（被功能開關鎖住 data-plk／額度用完 data-qlk／這個寬度沒有）就跳過那一步，絕不卡住；
     · 一套導覽同時涵蓋桌機與手機：每一步列幾個候選選擇器，挑第一個「看得見」的 ——
       側欄（桌機）／底部導覽列（手機）是同一步的兩個候選，不必寫兩套；
     · 鍵盤：← → 換步、Esc 關閉；點遮罩不關（避免誤觸），只有 Esc、✕、「略過」會關。
   入口（不自動彈出 —— 第一次來的訪客不打擾）：
     · 桌機頁首右上角的「導覽」鈕（#twTourBtn，☀／調色盤右邊）：開這一頁的導覽，沒有專屬導覽的頁面開全站導覽；
     · 手機（≤820）右上「⋯」清單多兩列：本頁導覽（#mmTourPage）、全站導覽（#mmTourSite）；
     · 頁尾「平台導覽」（#sfTour）—— 正式站的接線由 legal.js 那邊改成呼叫 TwTour.start()（另一支 agent 負責，這支不碰 legal.js）；
       預覽版（window.TW_PREVIEW）這支先自己接上，讓 Andy 在預覽就能試；
     · 網址帶 ?tour=1（或 ?tour=overview／flow／industry／stock）載入後自動開。
   用語：只講「這張圖在呈現什麼、怎麼讀、可以點哪裡」，不寫任何操作建議（DECISIONS #333 的禁用字）。
   ============================================================================ */
(function () {
  'use strict';
  if (window.TwTour) return;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const isMob = () => window.innerWidth <= 640;
  /* 2026-10-07 平滑化：不再用固定秒數等（sleep 110／160／250／350／400），一律「每一幀看一次，條件成立就走、逾時保底」 */
  const frame = () => new Promise((r) => requestAnimationFrame(() => r()));
  const reduced = () => { try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } };
  async function until(fn, ms) {
    const t0 = performance.now();
    while (performance.now() - t0 < ms) { let v = null; try { v = fn(); } catch (e) { v = null; } if (v) return v; await frame(); }
    return null;
  }
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const tab = (v) => `#tabs .tab[data-view="${v}"]`;

  /* ======================================================================== 導覽內容
     每一步：
       t / d      標題、說明（d 是桌機與 >640 用；m 有寫就是手機 ≤640 用的說明）
       sel        候選選擇器（字串或陣列）：挑第一個看得見的；union:true 時把所有看得見的合成一個框
       route      要先切到哪一頁（hash）；routeRe 符合就算已經在那一頁（不重切）
       view       換頁之後要等到哪一個 .view 打開（"頁面有切換"的依據）
       fast       目標是常駐元素（導覽列、頁首鈕）：先看它在不在，不在就直接跳過、不換頁、不等
       before     框之前先做的事（例如按個股分頁，讓背後的內容跟著換）
     ⚠ 選擇器一律挑「外框」（卡片、整排分頁），不挑 canvas —— 圖還在畫的時候 canvas 尺寸會跳。 */
  const SITE = [
    { t: '全站目錄在這一排', sel: ['#tabsWrap', '#tabs'], route: '#overview', routeRe: /^#?(overview)?$/, view: 'overview', fast: true,
      d: '左邊由上到下分五組：今日市場、資金流水、族群與個股、歷史規律、專案。接下來一格一格看，每一頁各自回答一個問題。',
      m: '最下面這排是主要頁面，其他頁收在「更多」。接下來一格一格看，每一頁各自回答一個問題。' },
    { t: '總覽：今天市場的全貌', sel: tab('overview'), route: '#overview', routeRe: /^#?(overview)?$/, view: 'overview', fast: true,
      d: '大盤三張走勢圖、漲跌家數、資金熱力圖與資金輪盤放在同一頁。第一次來，從這一頁開始看。' },
    { t: '財經日曆：接下來有哪些事', sel: tab('earnings'), route: '#earnings', view: 'earnings', fast: true,
      d: '公司財報、法說會與美國聯準會（FED）的重要日子排在同一張月曆；點月曆上的項目看說明。' },
    { t: '資金流向：錢往哪個族群跑', sel: [tab('flow'), '#tabs .l4subtab[data-parent="flow"]'], union: true, route: '#flow/rotation', routeRe: /^#flow/, view: 'flow', fast: true,
      d: '分三個子頁：資金輪動（族群跑到強弱循環的哪一段）、資金分流樹（錢從大盤分到哪裡）、族群×法人與集中度。' },
    { t: '熱力圖：哪裡熱、哪裡冷', sel: [tab('heatmap'), '#tabs .l4subtab[data-parent="heatmap"]'], union: true, route: '#heatmap', routeRe: /^#heatmap/, view: 'heatmap', fast: true,
      d: '一個方塊是一個族群或題材：方塊越大＝成交值越多，越紅＝漲越多、越綠＝跌越多。分「產業」與「題材」兩頁，點方塊看成分股。' },
    { t: '產業地圖：產業鏈的上下游', sel: tab('industry'), route: '#industry', routeRe: /^#industry$/, view: 'industry', fast: true,
      d: '先挑一條產業鏈，再看裡面的族群、產品剖析圖與供應鏈關聯圖，最後點公司名稱進個股頁。' },
    { t: '市場明細：完整名單', sel: tab('market'), route: '#market', routeRe: /^#market/, view: 'market', fast: true,
      d: '漲跌分佈、站上均線、法人連續買賣與各項排行的完整表格，可以排序、篩選，每一列都點得進個股頁。' },
    { t: '選股策略：用公開條件篩出個股', sel: tab('explore'), route: '#explore', routeRe: /^#explore/, view: 'explore', fast: true,
      d: '每張卡是一組公開條件（獲利、估值、成長、技術、法人、股利、動能），列出符合的個股；點一列看它符合哪幾條。' },
    { t: 'ETF 專區', sel: tab('etf'), route: '#etf', routeRe: /^#etf/, view: 'etf', fast: true,
      d: 'ETF 的分類、殖利率、配息日程與長期報酬比較；只看價格的報酬與含息的報酬分開算。' },
    { t: '週期統計：歷史上的月份規律', sel: tab('season'), route: '#season', view: 'season', fast: true,
      d: '每個族群在 1～12 月的歷史表現：上漲的年數比例、報酬與相對大盤的差距。過去的規律不代表今年會重演。' },
    { t: '自選：你自己的清單', sel: tab('watch'), route: '#watch', view: 'watch', fast: true,
      d: '把想追蹤的股票加進來（最多五頁），看今天的漲跌與走勢。沒登入時，清單只存在這台裝置的瀏覽器。' },
    { t: '更多頁面收在這裡', sel: '#mTabMore', fast: true, only: 'mob',
      d: '市場明細、週期統計、ETF、財經日曆與自選都在「更多」裡，點開就看得到。' },
    { t: '搜尋與今日事件', sel: ['.topbar .search', '#evToggle', '#mSearchBtn'], union: true, fast: true,
      d: '輸入股票代號或簡稱，直接跳到那一檔的個股頁；「事件」打開今日事件：新聞、公告與行事曆，數字是今天的則數。',
      m: '⌕ 輸入股票代號或簡稱，直接跳到那一檔的個股頁。' },
    { t: '右上角：通知、外觀、登入', sel: ['#ntBell', '#l4Tools', '#acctBar', '#moreBtn'], union: true, fast: true,
      d: '鈴鐺是網站公告；☀ 切換明亮／深色；調色盤換版面風格；登入之後，自選清單可以在不同裝置同步。',
      m: '「⋯」裡有今日事件、明亮／深色切換、版面風格，以及這套導覽（本頁導覽、全站導覽）。' },
    { t: '客服', sel: '#supFab', fast: true,
      d: '使用上遇到問題、想回報錯誤或給建議，從右下角這顆留言給我們。' },
    { t: '平台導覽與本頁導覽', sel: ['#twTourBtn', '#twPageTourBtn'], union: true, fast: true,
      d: '右上角「平台導覽」隨時重開這套全站導覽；每一頁頁名旁的「◎ 導覽」則一步步介紹那一頁的每張圖。' },
  ];

  /* 手機（≤640）的總覽與資金流向是「分段」的：一次只顯示一張圖，要先按上面那排（.mspine 步驟、.mpager 分段）才看得到。
     mseg('錢往哪跑', '熱力圖')＝先按含「錢往哪跑」的步驟鈕、再按含「熱力圖」的分段鈕；桌機沒有這兩排，什麼都不做。
     比對時去掉空白：手機把步驟鈕寫成 <em>①</em><b>錢往哪跑</b>，textContent 中間沒有空白。 */
  const mseg = (spine, pager) => async () => {
    const pick = (box, word) => {
      if (!box || !word || !shown(box)) return false;
      const b = $$('button', box).find((x) => (x.textContent || '').replace(/\s+/g, '').indexOf(word) >= 0);
      if (!b) return false;
      if (!b.classList.contains('on') && b.getAttribute('aria-selected') !== 'true') { b.click(); return true; }
      return false;
    };
    /* 切了大段落：等下面那排小分段換成新段落的按鈕（真的畫好）再點，不再固定等 350ms */
    if (pick($('.view.on .mspine'), spine) && pager) {
      await until(() => { const pb = $('.view.on .mpager'); return pb && shown(pb) && $$('button', pb).some((x) => (x.textContent || '').replace(/\s+/g, '').indexOf(pager) >= 0); }, 1500);
    }
    pick($('.view.on .mpager'), pager);
  };

  const OVERVIEW = [
    { t: '四張摘要卡', sel: ['#ovSumTrack', '#hero'], route: '#overview', routeRe: /^#?(overview)?$/, view: 'overview',
      d: '漲跌家數、資金輪盤、資金分流樹、熱門題材各一張，十秒看完今天的大概；點卡片可以看下面更完整的圖。',
      m: '漲跌家數、資金輪盤、資金分流樹、熱門題材各一張，左右滑看全部；點卡片看更完整的圖。' },
    { t: '分段看', sel: ['.view.on .mspine', '.view.on .mpager'], union: true, only: 'mob', before: mseg('錢往哪跑', '資金輪盤'),
      d: '手機上的總覽分成幾段：上面那排切段落，下面那排切同一段裡的不同圖，一次顯示一張。接下來依序打開。' },
    { t: '大盤三張圖', sel: ['#m3Mode', '#m3Grid'], union: true, before: mseg('貴不貴', '大盤'),
      d: '加權指數、櫃買指數、台指期今天怎麼走。左上切「走勢圖／K 線」；虛線＝昨天收盤價，線在虛線上面代表比昨天高。',
      m: '加權指數、櫃買指數、台指期今天怎麼走，左右滑看三張。虛線＝昨天收盤價，線在虛線上面代表比昨天高。' },
    { t: '資金熱力圖', sel: '#ovHeatCard', before: mseg('錢往哪跑', '熱力圖'),
      d: '一格是一個族群，越大＝成交值越多。顏色看近 5 日比近 20 日的資金佔比：紅＝錢在流進、綠＝錢在退出，不是今天的漲跌。' },
    { t: '資金輪盤', sel: '#ovRotCard', before: mseg('錢往哪跑', '資金輪盤'),
      d: '每顆點是一個族群，依「相對強度」與「動能」（都跟大盤比）分成四段，順時針：落後 → 改善 → 領先 → 轉弱。點越大＝成交值佔比越高。' },
    { t: '熱門題材', sel: '#ovThemeCard', before: mseg('錢往哪跑', '熱門題材'),
      d: '讀法跟資金熱力圖一樣，換成題材（例如 AI 伺服器、CoWoS）：方塊大小＝成交值，顏色＝熱度 0～100（資金、法人、新聞合成）。' },
    { t: '昨日資金分流樹', sel: '#ovFlowCard', before: mseg('錢往哪跑', '資金分流樹'),
      d: '昨天收盤，錢從大盤分到哪幾條產業鏈、鏈裡又分到哪些族群；線越粗＝流過的成交值越大。' },
    { t: '漲跌家數分佈', sel: '#ovBreadthCard', before: mseg('貴不貴', '市場寬度'),
      d: '每根直條＝落在那一級漲跌幅的家數，紅漲綠跌。重心偏右＝多數上漲、偏左＝多數下跌，兩頭都高＝漲跌分歧。' },
    { t: '今日事件', sel: '#ovEvents', only: 'mob', before: mseg('理由', '今日事件'),
      d: '當天的新聞、公告與行事曆，依時間排列；點一則看內容。' },
    { t: '看不懂就按「?」', sel: ['#ovHeatCard .howbtn', '#ovRotCard .howbtn', '.view.on .howbtn'], before: mseg('錢往哪跑', '資金輪盤'),
      d: '每張卡標題旁都有一顆「?」，點開是這張圖完整的讀法與資料口徑。' },
  ];

  const FLOW = [
    { t: '資金流向的三個子頁', sel: [tab('flow'), '#tabs .l4subtab[data-parent="flow"]'], union: true, route: '#flow/rotation', routeRe: /^#flow(\/rotation)?$/, view: 'flow', only: 'desk',
      d: '資金輪動、資金分流樹、族群×法人＋集中度。接下來依序打開每一頁。' },
    { t: '分段看', sel: '.view.on .mpager', only: 'mob', route: '#flow/rotation', routeRe: /^#flow/, view: 'flow', before: mseg(null, '輪動'),
      d: '手機上的資金流向分四段：輪動、資金分流樹、法人、集中度，點一段只顯示那一張圖。接下來依序打開。' },
    { t: '資金輪盤', sel: ['#rotClockWrap', '#mRadarFlow'], route: '#flow/rotation', routeRe: /^#flow(\/rotation)?$/, mobRe: /^#flow/, view: 'flow', before: mseg(null, '輪動'),
      d: '每顆點是一個族群。右上「領先」＝相對強度與動能都高於大盤，左下「落後」＝兩者都低；順時針輪動：落後 → 改善 → 領先 → 轉弱。' },
    { t: '資金排行', sel: ['#rankFlowWrap', '#mRank'],
      d: '這段期間各族群成交值佔比的變化：紅＝錢流進、綠＝錢退出，由多到少排。' },
    { t: '篩選與時間', sel: ['#flowRotCard .rotdd', '#flowRotTime'], union: true, only: 'desk',
      d: '上面兩個下拉只看某條產業鏈或某個族群；時間列調整看幾天前到最新，按 ▶ 播放看族群一路怎麼移動，腳印就是走過的路。' },
    { t: '資金分流樹', sel: '#flowSankeyCard', route: '#flow/sankey', routeRe: /^#flow\/sankey/, mobRe: /^#flow/, view: 'flow', before: mseg(null, '資金分流樹'),
      d: '由左到右：台股 → 產業鏈 → 族群 → 代表股。線越粗、圓越大＝錢越多；每一層的 % 都是佔它上一層的比重。' },
    { t: '族群 × 法人', sel: '#flowInstCard', route: '#flow/inst', routeRe: /^#flow\/inst/, mobRe: /^#flow/, view: 'flow', before: mseg(null, '法人'),
      d: '外資、投信、自營商近 20 日的淨買超（張）落在哪些族群，看法人的錢集中在哪裡。' },
    { t: '資金集中度', sel: '#flowConcCard', before: mseg(null, '集中度'),
      d: '成交值前 5（或前 10）大族群佔全市場的比重：比重升高＝錢越來越集中在少數族群，下降＝分散到更多族群。' },
  ];

  /* 剖析圖 2D／3D：按站上那顆分段鈕本人（#dg3d button[data-dm]），不自己改 localStorage —— 行為跟使用者按的一模一樣。
     導覽把模式切到 3D 的話，結束時切回原本的模式（tw.dg3d 是全站共用的記憶，不能因為看了導覽就改掉使用者的偏好）。 */
  const dgMode = (want) => async () => {
    const seg = $('#dg3d');
    if (!seg || seg.hidden || !shown(seg)) return;
    if (touched.dg3d == null) touched.dg3d = seg.dataset.mode || '2d';
    if ((seg.dataset.mode || '2d') === want) return;
    const b = $(`#dg3d button[data-dm="${want}"]`); if (b) b.click();
    if (want === '3d') {   // 等 3D 場景真的掛上（canvas 出現、「載入 3D 中…」消失），最多 6 秒
      await until(() => { const n = $('#dg3dNote'); return $('#prod3d canvas') && !(n && /載入 3D 中/.test(n.textContent || '')); }, 6000);
    }
  };
  const INDUSTRY = [
    { t: '先挑一條產業鏈', sel: '#chainSwitch', route: '#industry', routeRe: /^#industry$/, view: 'industry',
      d: '全市場、半導體、AI 伺服器……每個分頁是一條產業鏈，旁邊的數字是這條鏈各族群收錄的檔數合計。' },
    { t: '全市場族群漲幅與占比', sel: ['#gpHost', '#indMap .card'],
      d: '左邊是成交值前段族群今天的漲跌幅（紅漲綠跌），右邊是成交值占比；右上「產業熱力圖」看完整版圖。' },
    { t: '族群分頁', sel: '#dgPick', route: '#industry/semiconductor', routeRe: /^#industry\/semiconductor/, view: 'industry', before: dgMode('2d'),
      d: '點進一條產業鏈（這裡是半導體）之後，第二排是族群：「族群總覽」看整條鏈，其他每一格是一個族群的產品剖析圖。' },
    { t: '2D 剖析圖怎麼看', sel: ['#prodDiagram', '#dgSec'], before: dgMode('2d'),
      d: '把產品拆成零件的原創示意圖（非實物比例）。圖上每個圓圈編號對應右邊同號的說明卡；下面幾段可以展開看尺寸、製程與各段台股。' },
    { t: '點零件，看是誰做的', sel: ['#prodDiagram .dgc[data-seg]', '#prodDiagram [data-part]', '#prodDiagram [data-seg]'], before: dgMode('2d'),
      d: '圖上的零件或右邊的編號卡都點得下去。下一步示範點一個零件會出現什麼。' },
    { t: '這個零件是誰做的', sel: '#partCard',
      before: async () => {
        await dgMode('2d')();
        const pc = $('#partCard');
        if (pc && !pc.hidden && pc.getClientRects().length) return;
        const p = [$('#prodDiagram .dgc[data-seg]'), $('#prodDiagram [data-part]'), $('#prodDiagram [data-seg]')].find((x) => shown(x));
        if (p) p.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      },
      d: '點了零件，這張小卡列出做這個零件的台股與同一格的外商、進料與出貨；下面的供應鏈關聯圖也會亮起同一個環節。' },
    { t: '切到 3D', sel: '#dg3d', before: dgMode('2d'),
      d: '剖析圖右上這顆「2D｜3D」切換平面圖與立體圖，亮的那一格就是現在的模式。下一步切到 3D。' },
    { t: '3D 立體剖析圖', sel: '#prod3d', before: dgMode('3d'),
      d: '同一組零件改成立體：左鍵拖曳轉動、滾輪拉近拉遠、點兩下回到一開始的視角。立體看得出層與層的上下關係，平面圖適合看編號與細節。',
      m: '同一組零件改成立體：手指拖曳轉動、兩指縮放、點兩下回到一開始的視角。立體看得出層與層的上下關係。' },
    { t: '3D 展示：拆開與自轉', sel: ['#dg3dCtl', '#dgAnim'], union: true, before: dgMode('3d'),
      d: '一切到 3D，零件會從原位慢慢拆開（爆炸拆解），層次一目了然。「動畫：開」場景緩慢自轉、關掉就靜止；「拖曳：轉動」可切成平移，「重設視角」回到原位。' },
    { t: '3D 裡也能點台股', sel: ['#prod3d .chip3d', '#prod3d'], before: dgMode('3d'),
      d: '立體圖旁邊的編號卡跟 2D 是同一套，卡上列出做這個零件的台股，點名稱進個股頁；點畫面上的零件一樣會選起它所屬的環節。' },
    { t: '供應鏈關聯圖', sel: '#relSec', before: dgMode('2d'),
      d: '左邊上游、右邊下游，一欄是一層、每一格是一個環節、格子裡是做這個環節的公司；連線＝具名的供貨關係，線越粗依存度越高。' },
    { t: '環節下拉與收合', sel: ['#segDDBtn', '#relFold'], union: true,
      d: '「環節」下拉只看某幾格；「收合圖」把整張關聯圖收起來；格子右上的箭頭可以單獨展開或收起那一格。' },
    { t: '點公司，跟剖析圖連動', sel: ['#chainMap g.co.chip', '#chainList .co', '#relSec'],
      d: '點關聯圖裡的公司，會選起它所屬的環節：關聯圖只留那一格與上下游，上面剖析圖同一個環節的零件也跟著亮。' },
  ];

  const STOCK_ROUTE = () => (/^#stock\/[0-9A-Za-z]{4,6}/.test(location.hash) ? null : '#stock/2330');
  const stockTab = (t) => () => {
    const b = $(`#stockTabs button[data-t="${t}"]`);
    if (b && shown(b) && !b.classList.contains('on')) { b.click(); touched.stockTab = true; }
  };
  const STOCK = [
    { t: '這檔股票是誰', sel: ['#skIdent', '#mbQuote'], route: STOCK_ROUTE, routeRe: /^#stock\//, view: 'industry',
      d: '名稱、代號、上市或上櫃與現價；下面標出它屬於哪條產業鏈、哪個族群、哪些題材。☆ 把它加進自選。',
      m: '名稱、代號與現價；左右兩側的 ◀ ▶ 直接切換上一檔、下一檔。' },
    { t: 'K 線的工具列', sel: '#skTools',
      d: '分時、1 時、4 時、日、週、月切換週期；「指標」疊加均線、MACD、KD 等；「四週期同看」把四個週期並排比較。',
      m: '分時、1 時、4 時、日、週、月切換週期；「指標」疊加均線、MACD、KD 等。可以左右滑看更多工具。' },
    { t: 'K 線圖', sel: '#chartWrap',
      d: '紅 K＝收盤比開盤高、綠 K＝收盤比開盤低（跟台灣看盤軟體一樣）；下方是成交量。滑鼠滾輪縮放、拖曳看更早的資料。',
      m: '紅 K＝收盤比開盤高、綠 K＝收盤比開盤低；下方是成交量。兩指縮放、左右拖曳看更早的資料。' },
    { t: '下方分頁：總覽、基本資料、指標', sel: ['#stockTabs button[data-t="overview"]', '#stockTabs button[data-t="basics"]', '#stockTabs button[data-t="tags"]'], union: true,
      before: stockTab('overview'), pin: true, only: 'desk',
      d: '總覽＝基本面、籌碼快照、AI 分析三張摘要；基本資料＝公司全名、股本、上市日與所屬族群；指標＝這檔符合哪些條件（例如營收連續成長、創新高）。' },
    { t: '營收、獲利、除權息', sel: ['#stockTabs button[data-t="revenue"]', '#stockTabs button[data-t="profit"]', '#stockTabs button[data-t="dividend"]'], union: true,
      before: stockTab('revenue'), pin: true, only: 'desk',
      d: '營收＝每月營收與年增率；獲利＝每季 EPS、毛利率等三率與本益比河流圖；除權息＝歷年股利、除息日與填息天數。' },
    { t: '法人、資券、大戶／散戶', sel: ['#stockTabs button[data-t="inst"]', '#stockTabs button[data-t="margin"]', '#stockTabs button[data-t="holders"]'], union: true,
      before: stockTab('inst'), pin: true, only: 'desk',
      d: '法人＝外資、投信、自營商每天的買賣超；資券＝融資、融券、當沖與借券；大戶／散戶＝千張以上與 10 張以下持股比例的每週變化。' },
    { t: '公告／新聞', sel: '#stockTabs button[data-t="news"]',
      before: stockTab('news'), pin: true, only: 'desk',
      d: '公開資訊觀測站的重大訊息與相關新聞，依時間排列；點標題看原文。' },
    { t: '手機的分頁列', sel: '#mbTabs', only: 'mob',
      d: 'K 線、基本資料、指標、營收、獲利、除權息、法人、資券、大戶／散戶……左右滑看全部，點一格換下面的內容。' },
    { t: '加入自選', sel: '#mbStar', only: 'mob',
      d: '點 ☆ 把這檔加進自選清單，之後在「自選」頁一次看它今天的漲跌。' },
  ];

  const TOURS = {
    site: { name: '全站導覽', steps: SITE },
    overview: { name: '總覽導覽', steps: OVERVIEW },
    flow: { name: '資金流向導覽', steps: FLOW },
    industry: { name: '產業地圖導覽', steps: INDUSTRY, onEnd: () => { if (touched.dg3d && ($('#dg3d') || {}).dataset?.mode !== touched.dg3d) { const b = $(`#dg3d button[data-dm="${touched.dg3d}"]`); if (b) b.click(); } } },
    stock: { name: '個股頁導覽', steps: STOCK, onEnd: () => { if (touched.stockTab) { const b = $('#stockTabs button[data-t="overview"]'); if (b && !b.classList.contains('on')) b.click(); } } },
  };
  /* 目前這一頁有沒有專屬導覽：沒有就回 null（頁首鈕改開全站導覽） */
  function pageTour(h) {
    const head = String(h == null ? location.hash : h).replace(/^#/, '').split(/[/?]/)[0] || 'overview';
    if (head === 'stock') return 'stock';
    if (head === 'themes') return null;
    return TOURS[head] && head !== 'site' ? head : null;
  }

  /* ======================================================================== 量測工具 */
  /* 看得見＝有尺寸、自己與祖先都沒有 display:none／visibility:hidden／opacity:0，
     而且不在功能鎖（perm.js 的 data-plk、quota.js 的 data-qlk、鎖頭底下的 inert）裡面 —— 被鎖的區塊框起來也看不到東西 */
  function shown(el) {
    if (!el || !el.isConnected) return false;
    /* 導覽進行中 perm.js／quota.js 會撤掉鎖頭與額度卡（見 locks()），所以不再因 data-plk／data-qlk 判成看不見；
       撤除要一個畫格，waitFor 會等到它真的撤掉、尺寸穩定才框 */
    if (el.closest('[hidden],[inert]')) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return false;
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    }
    return true;
  }
  function resolve(st) {
    const sels = [].concat(st.sel || []);
    const out = [];
    for (const s of sels) {
      let els = [];
      try { els = $$(s).filter(shown); } catch (e) { els = []; }
      if (!els.length) continue;
      if (!st.union) return { els: [els[0]], sel: s };
      els.forEach((x) => { if (!out.includes(x)) out.push(x); });
    }
    return out.length ? { els: out, sel: sels.join(' + ') } : null;
  }
  function unionRect(els) {
    let l = Infinity, t = Infinity, r = -Infinity, b = -Infinity;
    els.forEach((e) => { const q = e.getBoundingClientRect(); if (q.width < 1 && q.height < 1) return;
      l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); });
    if (!isFinite(l)) return null;
    return { left: l, top: t, right: r, bottom: b, width: r - l, height: b - t };
  }
  function inFixed(el) {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const p = getComputedStyle(e).position;
      if (p === 'fixed' || p === 'sticky') return true;
    }
    return false;
  }
  /* 畫面上方被黏住的東西（桌機頁首、手機頂欄、手機個股頁的報價列、手機總覽的步驟列）：目標要捲到它們下面。
     sticky 的要用「黏住之後」的位置算（CSS top＋高度）—— 還沒捲之前它在原位，捲過去之後才會蓋到目標；
     目標自己就在那一列裡（或包住那一列）時不算。 */
  function topSafe(els) {
    let y = 0;
    ['#l4Head', '.topbar', '#mbHead', '.view.on .mspine', '.view.on .mpager'].forEach((s) => {
      const e = $(s); if (!e || !shown(e)) return;
      if (els && els.some((t) => t === e || t.contains(e) || e.contains(t))) return;
      const cs = getComputedStyle(e), p = cs.position;
      const r = e.getBoundingClientRect();
      if (p === 'fixed') { if (r.top <= 64 && r.bottom < window.innerHeight / 2) y = Math.max(y, r.bottom); return; }
      if (p !== 'sticky') return;
      const st = parseFloat(cs.top);
      if (!isFinite(st) || st > window.innerHeight / 2) return;
      y = Math.max(y, st + r.height);
    });
    return y;
  }
  /* 畫面下方被黏住的東西（手機底部導覽列）＋手機版說明卡本身 */
  function bottomSafe() {
    let h = 0;
    const nav = $('#tabs');
    if (nav && shown(nav) && getComputedStyle(nav).position === 'fixed') {
      const r = nav.getBoundingClientRect(); if (r.top > window.innerHeight / 2) h = Math.max(h, window.innerHeight - r.top);
    }
    if (isMob() && ui && ui.card) h = Math.max(h, ui.card.offsetHeight + 24);
    return h;
  }
  /* 把目標帶進畫面：常駐元素（側欄、頂欄、底部導覽）只做巢狀容器裡的捲動；其他的捲整頁，放在「頂欄下緣～底部可用處」中間 */
  /* 2026-10-07 平滑化：每一步只捲一次（舊版先 scrollIntoView 再 scrollBy，一步捲兩次、畫面抖一下）。
     常駐元素：只有不在畫面裡才捲它的容器；其他：算好位移量，整頁捲一次（smooth），等捲完（位置連兩幀不變）才回來定位。 */
  async function bring(els, pinTop, my) {
    const first = els[0], vw = window.innerWidth, vh = window.innerHeight;
    const beh = reduced() ? 'auto' : 'smooth';
    const r = unionRect(els); if (!r) return 0;
    if (els.every(inFixed)) {
      if (r.left >= 0 && r.right <= vw && r.top >= 0 && r.bottom <= vh) return 0;
      try { first.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: beh }); } catch (e) { /* 舊瀏覽器 */ }
      await settleScroll(first, my); return 1;
    }
    const top = topSafe(els) + 12, bot = vh - bottomSafe() - 12, avail = bot - top;
    let dy = 0;
    /* pinTop：分頁列這種「按了之後內容出現在它下面」的目標，捲到頂欄正下方，下面才看得到換出來的內容 */
    if (pinTop) dy = r.top - top;
    else if (r.height <= avail) {
      if (r.top < top || r.bottom > bot) dy = r.top - (top + (avail - r.height) / 2);
    } else dy = r.top - top;
    const offX = r.left < 0 || r.right > vw;   // 橫向拖曳容器裡被藏在右邊的：交給 scrollIntoView 一次處理兩個方向
    if (offX) { try { first.scrollIntoView({ block: Math.abs(dy) > 1 ? 'center' : 'nearest', inline: 'nearest', behavior: beh }); } catch (e) { /* 舊瀏覽器 */ } }
    else if (Math.abs(dy) > 1) {
      const maxY = document.documentElement.scrollHeight - vh;
      const to = Math.max(0, Math.min(maxY, window.scrollY + dy));
      if (Math.abs(to - window.scrollY) < 1) return 0;
      window.scrollTo({ top: to, behavior: beh });
      await settleScroll(first, my, to); return 1;
    } else return 0;
    await settleScroll(first, my); return 1;
  }
  /* 捲完＝（有指定終點的話）已經到終點，而且整頁位置與目標位置連兩幀、至少 120ms 沒變（最多 1.2 秒）。
     ⚠ smooth 捲動是下一幀才開始動：只看「連兩幀沒變」會在還沒開始捲之前就判成捲完（實測手機總覽卡片因此先貼頂又跳到貼底）。 */
  async function settleScroll(el, my, to) {
    let last = '', same = 0, since = performance.now();
    await until(() => {
      if (!run || run.seq !== my) return true;
      if (to != null && Math.abs(window.scrollY - to) > 1.5) { last = ''; return false; }
      const q = el.getBoundingClientRect(), sig = Math.round(window.scrollY) + ',' + Math.round(q.top) + ',' + Math.round(q.left), now = performance.now();
      if (sig !== last) { last = sig; same = 0; since = now; return false; }
      same += 1; return same >= 2 && now - since >= 120;
    }, 1200);
  }

  /* ======================================================================== 樣式
     顏色全部吃主題變數（深淺主題只換值不換名字，docs/style_guide.md 三）；字級吃 --fs-*，最小 12。 */
  function injectCSS() {
    if ($('#twTourCss')) return;
    const s = document.createElement('style'); s.id = 'twTourCss';
    s.textContent = `
#twTour{position:fixed;inset:0;z-index:2400;--twt-ease:cubic-bezier(.2,.8,.2,1);--twt-dur:280ms;--twt-ring:var(--accent,var(--cyan,#37e2ff));--twt-dim:rgba(3,7,16,.6)}
:root[data-theme="light"] #twTour{--twt-dim:rgba(15,23,42,.46)}
#twTour .twt-block{position:absolute;inset:0;background:transparent;cursor:default}
#twTour .twt-hole{position:fixed;left:0;top:0;width:0;height:0;border-radius:12px;pointer-events:none;contain:strict;will-change:transform;
  box-shadow:0 0 0 2px var(--twt-ring),0 0 0 6px color-mix(in srgb,var(--twt-ring) 22%,transparent),0 0 30px 8px color-mix(in srgb,var(--twt-ring) 32%,transparent),0 0 0 200vmax var(--twt-dim);
  transition:transform var(--twt-dur) var(--twt-ease),width var(--twt-dur) var(--twt-ease),height var(--twt-dur) var(--twt-ease)}
#twTour.nohole .twt-hole{box-shadow:0 0 0 200vmax var(--twt-dim)}
#twTour .twt-card{position:fixed;left:0;top:0;width:340px;max-width:calc(100vw - 24px);box-sizing:border-box;padding:14px 16px 12px;
  background:var(--panel-2,var(--panel));color:var(--ink);border:1px solid color-mix(in srgb,var(--twt-ring) 45%,var(--line-2,#334));
  border-radius:14px;box-shadow:0 22px 50px -14px rgba(0,0,0,.6),0 0 0 1px rgba(0,0,0,.04);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;will-change:transform,opacity;
  transition:transform var(--twt-dur) var(--twt-ease),opacity 180ms var(--twt-ease)}
#twTour .twt-card.out{opacity:0;pointer-events:none}
#twTour .twt-card.snap,#twTour .twt-hole.snap{transition:none}
#twTour .twt-card.out.snap{transition:none}
#twTour .twt-arrow{position:absolute;width:12px;height:12px;background:inherit;border:inherit;border-right:0;border-bottom:0;transform:rotate(45deg);pointer-events:none}
#twTour .twt-card[data-place="right"] .twt-arrow{left:-7px;transform:rotate(-45deg)}
#twTour .twt-card[data-place="left"] .twt-arrow{right:-7px;transform:rotate(135deg)}
#twTour .twt-card[data-place="bottom"] .twt-arrow,#twTour .twt-card[data-place="sheet-bottom"] .twt-arrow{top:-7px;transform:rotate(45deg)}
#twTour .twt-card[data-place="top"] .twt-arrow,#twTour .twt-card[data-place="sheet-top"] .twt-arrow{bottom:-7px;transform:rotate(225deg)}
#twTour .twt-card[data-place="over"] .twt-arrow,#twTour .twt-card[data-place="center"] .twt-arrow,#twTour .twt-card.noarrow .twt-arrow{display:none}
#twTour .twt-top{display:flex;align-items:center;gap:8px;min-height:24px}
#twTour .twt-eye{font-size:var(--fs-min,12px);font-weight:700;letter-spacing:.06em;color:var(--twt-ring);white-space:nowrap}
#twTour .twt-num{font-family:var(--mono,ui-monospace,monospace);font-variant-numeric:tabular-nums;font-size:var(--fs-min,12px);color:var(--ink-2);white-space:nowrap}
#twTour .twt-x{margin-left:auto;width:28px;height:28px;display:grid;place-items:center;border:0;border-radius:8px;background:transparent;color:var(--ink-2);font-size:14px;cursor:pointer;padding:0}
#twTour .twt-x:hover{background:var(--panel-3,rgba(127,127,127,.15));color:var(--ink)}
#twTour .twt-bar{height:3px;border-radius:3px;background:var(--line,rgba(127,127,127,.25));margin:6px 0 10px;overflow:hidden}
#twTour .twt-bar i{display:block;height:100%;width:100%;transform-origin:left;transform:scaleX(0);background:var(--twt-ring);border-radius:3px;transition:transform var(--twt-dur) var(--twt-ease)}
#twTour h3{margin:0 0 6px;font-size:var(--fs-h3,16px);font-weight:600;line-height:1.35;color:var(--ink)}
#twTour .twt-d{margin:0;font-size:var(--fs-body,14px);line-height:1.6;color:var(--ink-2)}
#twTour .twt-f{display:flex;align-items:center;gap:8px;margin-top:12px}
#twTour .twt-f .sp{flex:1}
#twTour .twt-f button{height:34px;padding:0 14px;border-radius:9px;font-size:var(--fs-sm,13px);font-family:inherit;cursor:pointer;white-space:nowrap}
#twTour .twt-skip{border:0;background:transparent;color:var(--ink-2);padding:0 6px!important}
#twTour .twt-skip:hover{color:var(--ink);text-decoration:underline}
#twTour .twt-prev{border:1px solid var(--line-2,#445);background:transparent;color:var(--ink)}
#twTour .twt-prev:disabled{opacity:.4;cursor:default}
#twTour .twt-next{border:1px solid transparent;background:var(--twt-ring);color:var(--on-accent,#03121b);font-weight:700}
#twTour .twt-next:hover,#twTour .twt-prev:not(:disabled):hover{filter:brightness(1.08)}
#twTour button:focus-visible{outline:2px solid var(--focus,var(--twt-ring));outline-offset:2px}
@media (max-width:640px){
  #twTour .twt-card{width:auto;left:12px;right:12px;max-height:46vh;overflow:auto}
  #twTour .twt-arrow{display:none}
  #twTour .twt-card.hasarrow .twt-arrow{display:block}
}
@media (prefers-reduced-motion:reduce){#twTour .twt-hole,#twTour .twt-card,#twTour .twt-bar i{transition:none}}
/* 頁首右上「導覽」鈕：跟 ☀／調色盤同一列、同高 34、同邊框圓角底色；字一行、寬度固定，換頁不晃 */
#twTourBtn{display:inline-flex;align-items:center;gap:6px;flex:none;height:34px;padding:0 12px;margin:0;box-sizing:border-box;
  border:1px solid var(--t4-ctl-edge,var(--line-2));border-radius:var(--r-sm,9px);background:var(--t4-ctl,var(--panel));color:var(--ink-2);
  font-size:var(--fs-sm,13px);font-family:inherit;line-height:1;cursor:pointer;white-space:nowrap}
#twTourBtn:hover{color:var(--ink);border-color:var(--t4-accent-solid,var(--accent,var(--cyan)))}
#twTourBtn svg{width:16px;height:16px;flex:none;color:var(--t4-accent-solid,var(--accent,var(--cyan)))}
/* 頁名旁「◎ 導覽」：小一號膠囊，跟頁名垂直置中；手機版只留圖示、跟頂欄圓鈕同高 */
#twPageTourBtn{display:inline-flex;align-items:center;gap:5px;flex:none;height:28px;padding:0 10px;margin:0;box-sizing:border-box;
  border:1px solid var(--t4-ctl-edge,var(--line-2));border-radius:999px;background:transparent;color:var(--ink-2);
  font-size:var(--fs-sm,13px);font-family:inherit;line-height:1;cursor:pointer;white-space:nowrap}
#twPageTourBtn[hidden]{display:none}
#twPageTourBtn:hover{color:var(--ink);border-color:var(--t4-accent-solid,var(--accent,var(--cyan)))}
#twPageTourBtn svg{width:14px;height:14px;flex:none;color:var(--t4-accent-solid,var(--accent,var(--cyan)))}
#twPageTourBtn.mob{width:40px;height:40px;padding:0;justify-content:center;border-radius:12px}
#twPageTourBtn.mob svg{width:18px;height:18px}
#morePop .twt-mm .ic{color:var(--accent,var(--cyan))}
`;
    document.head.appendChild(s);
  }

  /* ======================================================================== 畫面 */
  let ui = null;           // { root, hole, card }
  let run = null;          // { id, tour, i, seq, els, sel, skipped:[], place }
  const touched = { stockTab: false, dg3d: null };
  const ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/></svg>';

  function build() {
    injectCSS();
    const root = document.createElement('div');
    root.id = 'twTour';
    root.innerHTML = '<div class="twt-block" aria-hidden="true"></div><div class="twt-hole" id="twTourHole" aria-hidden="true"></div>'
      + '<div class="twt-card" id="twTourCard" role="dialog" aria-modal="true" aria-labelledby="twTourT" aria-describedby="twTourD">'
      + '<i class="twt-arrow" aria-hidden="true"></i>'
      + '<div class="twt-top"><span class="twt-eye" id="twTourEye"></span><span class="twt-num" id="twTourNum"></span>'
      + '<button type="button" class="twt-x" id="twTourX" aria-label="關閉導覽">✕</button></div>'
      + '<div class="twt-bar" aria-hidden="true"><i id="twTourBar"></i></div>'
      + '<h3 id="twTourT"></h3><p class="twt-d" id="twTourD" aria-live="polite"></p>'
      + '<div class="twt-f"><button type="button" class="twt-skip" id="twTourSkip">略過</button><span class="sp"></span>'
      + '<button type="button" class="twt-prev" id="twTourPrev">上一步</button>'
      + '<button type="button" class="twt-next" id="twTourNext">下一步</button></div></div>';
    document.body.appendChild(root);
    ui = { root, hole: $('#twTourHole', root), card: $('#twTourCard', root), arrow: $('.twt-arrow', root) };
    $('#twTourX', root).onclick = () => stop('close');
    $('#twTourSkip', root).onclick = () => stop('skip');
    $('#twTourPrev', root).onclick = () => prev();
    $('#twTourNext', root).onclick = () => next();
    /* 點遮罩不關（避免誤觸）：吃掉事件就好，什麼都不做 */
    $('.twt-block', root).addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); });
  }

  function paintText(st, i, n) {
    const T = TOURS[run.id];
    $('#twTourEye').textContent = T.name;
    /* 第幾步／共幾步只數「這個寬度做得出來的步驟」：手機專用／桌機專用的不算進另一邊；
       常駐元素（fast）現在就量得到在不在（例如手機藏起來的財經日曆、桌機沒有的「更多」），不在的也不算 ——
       不然手機上會顯示「4 / 16」，實際只有 9 步。 */
    const ap = run.tour.steps.map((s, k) => (possible(k) || k === i ? k : -1)).filter((k) => k >= 0);
    const pos = Math.max(0, ap.indexOf(i)), tot = ap.length || n;
    $('#twTourNum').textContent = (pos + 1) + ' / ' + tot;
    $('#twTourBar').style.transform = 'scaleX(' + ((pos + 1) / tot).toFixed(4) + ')';
    $('#twTourT').textContent = st.t;
    $('#twTourD').textContent = (isMob() && st.m) ? st.m : st.d;
    $('#twTourPrev').disabled = prevIndex(i) < 0;
    $('#twTourNext').textContent = isLast(i) ? '完成' : '下一步';
  }
  const applicable = (st) => !(st.only === 'desk' && isMob()) && !(st.only === 'mob' && !isMob());
  /* 這一步現在做得出來嗎：寬度對、沒被跳過過、常駐元素現在就在畫面上（非常駐的要換頁之後才知道，先當作做得出來） */
  function possible(k) {
    const st = run.tour.steps[k];
    if (!st || !applicable(st) || run.skipped.includes(k)) return false;
    return !(st.fast && !resolve(st));
  }
  function prevIndex(i) { for (let k = i - 1; k >= 0; k--) if (possible(k)) return k; return -1; }
  function isLast(i) { const n = run.tour.steps.length; for (let k = i + 1; k < n; k++) if (possible(k)) return false; return true; }

  /* 聚光燈＋說明卡定位。桌機：卡片放在目標的右／左／下／上（放得下的第一個），箭頭指向目標中心；
     都放不下（目標比半個畫面還大）就疊在目標的右下角、不畫箭頭。手機：卡片貼底（目標在下半部就貼頂），箭頭指向目標。 */
  function place(how) {
    if (!run || !ui) return;
    /* ---- 讀（全部量完才寫，同一幀內不交錯讀寫，避免強制同步排版） */
    const vw = window.innerWidth, vh = window.innerHeight, card = ui.card;
    const r0 = run.els ? unionRect(run.els) : null;
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const mob = isMob(), tsm = mob ? topSafeMini() : 0;
    const pad = 6, m = 12, gap = 16;
    let hr = null;
    if (r0) {
      const l = Math.max(4, r0.left - pad), t = Math.max(4, r0.top - pad);
      const r = Math.min(vw - 4, r0.right + pad), b = Math.min(vh - 4, r0.bottom + pad);
      hr = { left: l, top: t, right: Math.max(l + 8, r), bottom: Math.max(t + 8, b) };
      hr.width = hr.right - hr.left; hr.height = hr.bottom - hr.top; hr.cx = hr.left + hr.width / 2; hr.cy = hr.top + hr.height / 2;
    }
    let x, y, where, ax = null, ay = null, hasArrow = false;
    if (mob) {
      const bottomY = vh - ch - m;
      // 目標在卡片底下（例如底部導覽列）就把卡片放上面
      if (hr && hr.bottom > bottomY - 8 && hr.top > ch + m + 8) { where = 'sheet-top'; y = m + tsm; }
      else { where = 'sheet-bottom'; y = bottomY; }
      x = 0;   // 手機卡片左右由 CSS 貼 12px，只上下移
      if (hr && ((where === 'sheet-bottom' && hr.bottom <= y - 4) || (where === 'sheet-top' && hr.top >= y + ch + 4))) {
        hasArrow = true; ax = Math.max(18, Math.min(vw - 2 * m - 18, hr.cx - m)) - 6;
      }
    } else if (!hr) { where = 'center'; x = (vw - cw) / 2; y = (vh - ch) / 2; }
    else {
      const clampX = (v) => Math.max(m, Math.min(vw - cw - m, v)), clampY = (v) => Math.max(m, Math.min(vh - ch - m, v));
      const C = {
        right: () => (hr.right + gap + cw <= vw - m ? [hr.right + gap, clampY(hr.cy - ch / 2)] : null),
        left: () => (hr.left - gap - cw >= m ? [hr.left - gap - cw, clampY(hr.cy - ch / 2)] : null),
        bottom: () => (hr.bottom + gap + ch <= vh - m ? [clampX(hr.cx - cw / 2), hr.bottom + gap] : null),
        top: () => (hr.top - gap - ch >= m ? [clampX(hr.cx - cw / 2), hr.top - gap - ch] : null),
      };
      const order = hr.width > vw * 0.45 ? ['bottom', 'top', 'right', 'left'] : ['right', 'left', 'bottom', 'top'];
      for (const k of order) { const p = C[k](); if (p) { [x, y] = p; where = k; break; } }
      if (!where) { where = 'over'; x = Math.min(vw - cw - 24, hr.right - cw - 16); y = Math.min(vh - ch - 24, Math.max(hr.top + 16, vh - ch - 24)); x = Math.max(m, x); }
      if (where === 'right' || where === 'left') ay = Math.max(14, Math.min(ch - 26, hr.cy - y - 6));
      if (where === 'bottom' || where === 'top') ax = Math.max(14, Math.min(cw - 26, hr.cx - x - 6));
    }
    /* ---- 寫 */
    const snap = how === 'snap' || reduced();
    ui.hole.classList.toggle('snap', snap); card.classList.toggle('snap', snap || card.classList.contains('out'));
    ui.root.classList.toggle('nohole', !hr);
    const hs = ui.hole.style;
    if (hr) { hs.transform = `translate3d(${hr.left}px,${hr.top}px,0)`; hs.width = hr.width + 'px'; hs.height = hr.height + 'px'; }
    else { hs.transform = `translate3d(${vw / 2}px,${vh / 2}px,0)`; hs.width = '0px'; hs.height = '0px'; }
    const arrow = ui.arrow.style;
    arrow.left = ax == null ? '' : ax + 'px'; arrow.top = ay == null ? '' : ay + 'px'; arrow.right = arrow.bottom = '';
    card.classList.toggle('hasarrow', hasArrow);
    card.dataset.place = where;
    const ct = `translate3d(${Math.round(x)}px,${Math.round(y)}px,0)`;
    if (!run.busy && run.placedAt && run.cardXY !== ct) run.cardJumps = (run.cardJumps || 0) + 1;   // 定位好之後說明卡又被搬動（給驗收數）
    if (run.cardXY !== ct) { card.style.transform = ct; run.cardXY = ct; }
    run.place = where;
    run.sig = sigOf(r0);
  }
  const sigOf = (r) => (r ? [r.left, r.top, r.width, r.height].map(Math.round).join(',') : 'none') + '|' + window.innerWidth + 'x' + window.innerHeight;
  /* 說明卡淡出（換頁時）／淡入（定位好之後才淡入 —— 不會先在舊位置出現再跳過去） */
  function cardOut() { if (ui && !reduced()) ui.card.classList.add('out'); }
  function cardIn() {
    if (!ui || !ui.card.classList.contains('out')) return;
    requestAnimationFrame(() => { if (!ui) return; ui.card.classList.remove('snap'); ui.card.classList.remove('out'); });
  }
  function topSafeMini() { const tb = $('.topbar'); return tb && shown(tb) ? Math.max(0, tb.getBoundingClientRect().bottom - 4) : 0; }

  /* 目標跟著版面動（圖晚一點畫完、側欄展開、視窗縮放、使用者自己捲頁）：
     2026-10-07 平滑化：拿掉舊版「每 150ms 量一次、變了就重放」的輪詢補丁。改成事件驅動 ——
     ResizeObserver（目標尺寸變）＋MutationObserver（版面結構變）＋scroll／resize，全部併成下一幀量一次；
     位置真的變了才寫。使用者捲頁時聚光燈直接跟著（不走動畫，不然會拖在後面）。 */
  let ro = null, mo = null, raf = 0, scrolled = false;
  function schedule(e) {
    if (e && e.type === 'scroll') scrolled = true;
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const how = scrolled ? 'snap' : 'anim'; scrolled = false;
      if (!run || run.busy || !ui) return;
      if (run.els && !run.els.every((x) => x.isConnected && shown(x))) {
        const again = resolve(run.tour.steps[run.i]);
        if (again) { run.els = again.els; observe(); } else { next(); return; }
      }
      const r = run.els ? unionRect(run.els) : null;
      if (sigOf(r) !== run.sig) place(how);
    });
  }
  function observe() {
    if (ro) ro.disconnect();
    if (run && run.els && typeof ResizeObserver !== 'undefined') { ro = new ResizeObserver(() => schedule()); run.els.forEach((x) => ro.observe(x)); }
  }
  function watch(on) {
    if (on) {
      window.addEventListener('scroll', schedule, { passive: true, capture: true });
      window.addEventListener('resize', schedule);
      if (typeof MutationObserver !== 'undefined') {
        mo = new MutationObserver((list) => { if (list.some((r) => !ui || !ui.root.contains(r.target))) schedule(); });
        mo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
      }
    } else {
      window.removeEventListener('scroll', schedule, { capture: true });
      window.removeEventListener('resize', schedule);
      if (mo) mo.disconnect();
      if (ro) ro.disconnect();
      mo = ro = null;
      cancelAnimationFrame(raf); raf = 0;
    }
  }

  /* ======================================================================== 走步
     go(i, dir)：從第 i 步開始往 dir 方向找第一個「做得出來」的步驟。做不出來（找不到、被鎖、這個寬度沒有）就記進 skipped、繼續找。
     seq 是防止快速連按：每次 go 都換號，舊的那輪等到一半發現號碼變了就收手。 */
  function routeOk(st) {
    const r = typeof st.route === 'function' ? st.route() : st.route;
    if (!r) return true;
    const h = location.hash || '';
    const re = (isMob() && st.mobRe) || st.routeRe;   // 手機分段不改網址：已經在那一頁就不重切
    return re ? re.test(h) : h === r;
  }
  function viewOn(v) { const e = document.getElementById('v-' + v); return !v || (e && e.classList.contains('on')); }
  /* 等元素真的畫好：每一幀量一次，頁面已切到 view、找得到看得見的元素、位置尺寸「連續至少 2 幀而且至少 120ms」沒變才算穩。
     （舊版每 110ms 輪詢，最快也要 330ms；圖表晚 0.1 秒才長高的那種會被框到半路，框好又被補丁拉一次。） */
  async function waitFor(st, ms, my) {
    let last = null, since = 0, frames = 0, got = null;
    const ok = await until(() => {
      if (!run || run.seq !== my) return 'gone';
      if (!viewOn(st.view)) { last = null; return null; }
      got = resolve(st);
      if (!got) { last = null; return null; }
      const sig = sigOf(unionRect(got.els)), now = performance.now();
      if (sig !== last) { last = sig; since = now; frames = 0; return null; }
      frames += 1;
      return frames >= 2 && now - since >= 120 ? 'ok' : null;
    }, ms);
    if (ok === 'gone') return null;
    if (ok === 'ok') return got;
    return got && viewOn(st.view) && got.els.every(shown) ? got : null;
  }
  /* 換步：
       1. 要換頁 → 說明卡先淡出（不讓舊卡留在新頁上）→ 改 hash
       2. 前置動作（切分段、切 2D／3D、點零件）→ 等元素穩定（上面的 waitFor，不用固定秒數）
       3. 捲一次（smooth），捲完才定位
       4. 聚光燈滑到新位置；說明卡如果是淡出狀態，就先無動畫放到最終位置再淡入（不會先出現在別處再跳）
     seq 防快速連按：每次 go 都換號，舊的那輪等到一半發現號碼變了就收手。 */
  async function go(i, dir) {
    if (!run) return;
    const my = ++run.seq;
    run.busy = true;
    const steps = run.tour.steps;
    while (i >= 0 && i < steps.length) {
      const st = steps[i];
      if (!applicable(st)) { i += dir; continue; }
      if (st.fast && !resolve(st)) { if (!run.skipped.includes(i)) run.skipped.push(i); i += dir; continue; }
      let moved = false;
      if (!routeOk(st)) {
        const r = typeof st.route === 'function' ? st.route() : st.route;
        if (r) { cardOut(); location.hash = r; moved = true; }
      }
      if (st.before) { try { await st.before(); } catch (e) { /* 示範動作失敗就當沒有這一步的前置，照樣去找元素 */ } }
      if (!run || run.seq !== my) return;
      const got = await waitFor(st, moved ? 7000 : (st.fast ? 600 : 2200), my);
      if (!run || run.seq !== my) return;
      if (got) {
        run.skipped = run.skipped.filter((k) => k !== i);
        run.i = i; run.els = got.els; run.sel = got.sel;
        run.placedAt = 0; run.cardJumps = 0;
        run.scrolls = await bring(got.els, !!st.pin, my);
        if (!run || run.seq !== my) return;
        paintText(st, i, steps.length);
        place('anim'); cardIn();
        observe();
        run.busy = false; run.placedAt = performance.now();
        ui.root.dataset.step = String(i);
        ui.root.dataset.sel = got.sel;
        try { $('#twTourNext').focus({ preventScroll: true }); } catch (e) { /* 忽略 */ }
        return;
      }
      /* 元素在這一頁裡、沒被藏起來，只是量不到尺寸（多半是資料載不到、畫不出來）：不跳過整步，改成置中的說明卡 */
      const ghost = [].concat(st.sel || []).map((x) => { try { return $(x); } catch (e) { return null; } })
        .find((e) => e && e.closest('.view.on') && !e.closest('[hidden]') && getComputedStyle(e).display !== 'none');
      if (ghost && !st.fast) {
        run.skipped = run.skipped.filter((k) => k !== i);
        run.i = i; run.els = null; run.sel = '(說明卡)'; run.scrolls = 0; run.placedAt = 0; run.cardJumps = 0;
        paintText(st, i, steps.length);
        $('#twTourD').textContent += '（這一塊目前沒有畫面可以框，先看說明。）';
        place('anim'); cardIn(); observe();
        run.busy = false; run.placedAt = performance.now();
        ui.root.dataset.step = String(i); ui.root.dataset.sel = '';
        return;
      }
      if (!run.skipped.includes(i)) run.skipped.push(i);
      i += dir;
    }
    // 往後走到底＝導覽結束；往前找不到＝停在原來那一步
    if (dir > 0) { stop('done'); return; }
    run.busy = false;
    if (run.i >= 0) { paintText(steps[run.i], run.i, steps.length); place('anim'); cardIn(); }
  }
  function next() { if (!run) return; if (run.i >= 0 && isLast(run.i) && !run.busy) { stop('done'); return; } go(run.i + 1, 1); }
  function prev() { if (!run) return; const k = prevIndex(run.i); if (k >= 0) go(k, -1); }

  function onKey(e) {
    if (!run) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); stop('esc'); return; }
    if (e.key === 'ArrowRight') { e.preventDefault(); e.stopPropagation(); next(); return; }
    if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopPropagation(); prev(); return; }
    if (e.key === 'Tab') {
      // 焦點困在說明卡裡
      const f = $$('button', ui.card).filter((b) => !b.disabled && b.offsetParent !== null);
      if (!f.length) return;
      const a = document.activeElement, first = f[0], last = f[f.length - 1];
      if (!ui.card.contains(a)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && a === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && a === last) { e.preventDefault(); first.focus(); }
    }
  }

  /* 開始前把會擋在導覽上面的東西收起來：今日事件抽屜、⋯ 清單、手機「更多」抽屜 */
  function tidy() {
    const side = $('aside#side.open'), x = $('#evClose'); if (side && x) x.click();
    const mp = $('#morePop'); if (mp && !mp.hidden) { mp.hidden = true; const mb = $('#moreBtn'); if (mb) mb.setAttribute('aria-expanded', 'false'); }
    const back = $('#mSheetBack'); if (back && back.getClientRects().length) back.click();
  }

  function start(id) {
    const key = TOURS[id] ? id : (id === 'page' ? (pageTour() || 'site') : 'site');
    if (run) stop('restart');
    tidy();
    if (!ui) build(); else if (!ui.root.isConnected) document.body.appendChild(ui.root);
    ui.root.hidden = false;
    ui.root.dataset.tour = key;
    touched.stockTab = false; touched.dg3d = null;
    run = { id: key, tour: TOURS[key], i: -1, seq: 0, els: null, sel: '', skipped: [], busy: false, opener: document.activeElement };
    paintText({ t: '載入中…', d: '' }, 0, TOURS[key].steps.length);
    $('#twTourT').textContent = TOURS[key].name;
    place('snap');
    window.addEventListener('keydown', onKey, true);
    watch(true);
    locks();
    go(0, 1);
    return key;
  }
  function stop(why) {
    if (!run) return;
    const r = run; run = null;
    watch(false);
    window.removeEventListener('keydown', onKey, true);
    if (ui) { ui.root.remove(); }
    locks();
    try { if (r.tour.onEnd) r.tour.onEnd(why); } catch (e) { /* 收尾失敗不影響關閉 */ }
    if (why !== 'restart' && r.opener && r.opener.isConnected && r.opener.focus) { try { r.opener.focus({ preventScroll: true }); } catch (e) { /* 忽略 */ } }
  }

  /* 導覽期間訪客也看得到真畫面（Andy 10-07：「導覽即使是訪客 也需要看得到畫面」）：
     開始／結束都丟一個 tw:tour 事件，perm.js（鎖頭）與 quota.js（每日額度卡）收到就重算 ——
     它們重算時看 TwTour.state().on：導覽中一律不蓋、quota 也不扣次；結束時照原規則蓋回來。
     只是畫面層暫停遮罩，資料怎麼載入完全沒動（本來載不到的，那一步改成只顯示說明卡，見 go() 的 fallback）。 */
  function locks() { try { window.dispatchEvent(new CustomEvent('tw:tour', { detail: { on: !!run } })); } catch (e) { /* 舊瀏覽器 */ } }

  /* ======================================================================== 入口 */
  /* 桌機：頁首右上角工具列（#l4Tools）裡、外觀調色盤（#t4Btn）右邊一顆「導覽」。
     ⚠ 不放在頁名旁邊：Andy 10-03「紅框處 只留下 總覽 及當下日期時間（所有分頁都是）」—— 頁名那一格只准有頁名＋時間，
       工具一律在右上角（DECISIONS #312「都放在右上」）；驗收「版面v2結構」也釘著頁首只有 h1／time／div.l4tools 三樣。
     放在 #t4Btn 後面、登入前面：通知鈴／☀／調色盤三顆方鈕的間距驗收（頁首圖示鈕1006）只量那三顆，插在後面不影響它們。
     layout4.js 跨過 820 會拆掉／重建頁首，所以這支每次換頁、縮放都重掛一次（已經在對的位置就不動）。 */
  function mountHeadBtn() {
    const tools = $('#l4Tools');
    let b = $('#twTourBtn');
    if (!tools || !tools.getClientRects().length) { if (b) b.remove(); return; }
    if (!b) {
      b = document.createElement('button');
      b.type = 'button'; b.id = 'twTourBtn';
      b.innerHTML = ICON + '<span>平台導覽</span>';
      b.onclick = () => start('site');
    }
    /* 別支檔（layout4／theme4／account）之後還會把 ☀、調色盤、登入搬進來或重排：盯著工具列，一動就把這顆放回調色盤右邊 */
    if (!tools._twtObs && typeof MutationObserver !== 'undefined') {
      tools._twtObs = new MutationObserver(() => { cancelAnimationFrame(tools._twtRaf); tools._twtRaf = requestAnimationFrame(mountHeadBtn); });
      tools._twtObs.observe(tools, { childList: true });
    }
    const t4 = $('#t4Btn', tools);
    if (t4) { if (b.previousElementSibling !== t4) t4.after(b); }
    else if (b.parentNode !== tools) tools.insertBefore(b, tools.firstChild);
    b.title = '平台導覽：全站每個區塊在哪裡、各自回答什麼問題';
    b.setAttribute('aria-label', '平台導覽（全站導覽）');
  }
  /* ≤820：右上「⋯」清單加兩列（清單本身是 index.html 的靜態節點，只插一次） */
  function mountMore() {
    const pop = $('#morePop'); if (!pop || $('#mmTourPage', pop)) return;
    const mk = (id, txt, fn) => {
      const b = document.createElement('button'); b.type = 'button'; b.id = id; b.className = 'twt-mm';
      b.innerHTML = '<span class="ic">◎</span>' + txt;
      b.onclick = (e) => { e.stopPropagation(); pop.hidden = true; const mb = $('#moreBtn'); if (mb) mb.setAttribute('aria-expanded', 'false'); fn(); };
      return b;
    };
    pop.appendChild(mk('mmTourPage', '本頁導覽', () => start(pageTour() || 'site')));
    pop.appendChild(mk('mmTourSite', '全站導覽', () => start('site')));
  }
  /* 預覽版：頁尾「平台導覽」先接到這套（正式站的接線在 legal.js，由另一支 agent 改） */
  function mountPreviewFoot() {
    if (!window.TW_PREVIEW) return;
    const f = $('#sfTour'); if (!f || f.dataset.twt) return;
    f.dataset.twt = '1';
    f.addEventListener('click', (e) => { e.preventDefault(); e.stopImmediatePropagation(); start('site'); }, true);
  }
  /* ★ 2026-10-07 Andy：「導覽放到每個分頁標題旁 如圖一，原本的地方就改成平台導覽」（蓋掉 10-03「頁首只留頁名及日期時間」，DECISIONS 有記）：
     頁名（#l4Head h1）右邊一顆小鈕「◎ 導覽」＝這一頁的導覽；這一頁沒有專屬導覽就不顯示（不拿全站導覽冒充）。
     ≤820 沒有 #l4Head：放在頂欄搜尋鈕前面（只有圖示，跟頂欄其他圓鈕同一行）。 */
  function mountPageBtn() {
    const id = pageTour();
    const h1 = $('#l4Head h1');
    let b = $('#twPageTourBtn');
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = 'twPageTourBtn';
      b.onclick = () => { const t = pageTour(); if (t) start(t); };
    }
    const desk = !!(h1 && h1.getClientRects().length);
    if (desk) { b.className = 'twpt'; b.innerHTML = ICON + '<span>導覽</span>'; if (b.previousElementSibling !== h1) h1.after(b); }
    else {
      const bar = $('.topbar'), anchor = $('#mSearchBtn') || $('.topbar .search');
      if (!bar || !anchor) { b.remove(); return; }
      b.className = 'twpt mob'; b.innerHTML = ICON;
      if (b.nextElementSibling !== anchor) anchor.before(b);
    }
    b.hidden = !id;
    b.title = id ? TOURS[id].name + '：一步步看這一頁的每張圖在說什麼' : '';
    b.setAttribute('aria-label', id ? TOURS[id].name : '本頁導覽');
  }
  function mountAll() { injectCSS(); mountHeadBtn(); mountPageBtn(); mountMore(); mountPreviewFoot(); }

  function boot() {
    mountAll();
    window.addEventListener('hashchange', () => setTimeout(() => { mountHeadBtn(); mountPageBtn(); }, 0));
    window.addEventListener('resize', () => { clearTimeout(boot.rt); boot.rt = setTimeout(mountAll, 200); });
    // layout4.js 在跨過 820 時會把頁首整個拆掉／重建：盯著 #layout 前面那一段，有變就補掛
    let n = 0; const iv = setInterval(() => { mountAll(); if (++n > 20) clearInterval(iv); }, 500);
    // ?tour=1／?tour=overview：載入後自動開（給預覽與分享連結用；一般訪客不會自動彈出）
    const q = /[?&]tour=([a-z0-9]+)/i.exec(location.search || '');
    if (q) setTimeout(() => start(q[1] === '1' ? 'site' : q[1] === 'page' ? 'page' : q[1]), 1400);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  window.TwTour = {
    start, stop: () => stop('api'), next, prev,
    ids: () => Object.keys(TOURS),
    steps: (id) => (TOURS[id] ? TOURS[id].steps.map((s) => ({ t: s.t, d: s.d, m: s.m || '', only: s.only || '', view: s.view || '',
      route: typeof s.route === 'function' ? s.route() : (s.route || '') })) : null),
    pageTour,
    /* 給驗收腳本：現在在哪一步、框的是誰、框在哪、卡片在哪 */
    state: () => {
      if (!run) return { active: false, on: false };
      const r = run.els ? unionRect(run.els) : null, c = ui.card.getBoundingClientRect(), h = ui.hole.getBoundingClientRect();
      return { active: true, on: true, tour: run.id, i: run.i, n: run.tour.steps.length, busy: run.busy, scrolls: run.scrolls || 0, cardJumps: run.cardJumps || 0, act: !!(run.i >= 0 && run.tour.steps[run.i] && run.tour.steps[run.i].before),
        since: run.placedAt ? Math.round(performance.now() - run.placedAt) : -1, title: $('#twTourT').textContent,
        sel: run.sel, place: run.place, skipped: run.skipped.slice(), hash: location.hash, view: (($('.view.on') || {}).id || ''),
        target: r && { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height },
        hole: { l: h.left, t: h.top, r: h.right, b: h.bottom, w: h.width, h: h.height },
        card: { l: c.left, t: c.top, r: c.right, b: c.bottom, w: c.width, h: c.height },
        vw: window.innerWidth, vh: window.innerHeight };
    },
  };
})();
