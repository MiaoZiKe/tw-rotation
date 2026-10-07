/* ============================================================================
   功能清單（site/features.js）—— 會員功能開放制度的唯一宣告處（Andy 2026-10-02，DECISIONS #288）
   ----------------------------------------------------------------------------
   Andy：「之後會分付費和免費會員，要一個新分頁，用 Switch 或勾選，針對每個會員的 Email 設定可以用哪些功能」。

   這支只放「資料」：全站每個大項目一個開關。誰讀它：
     · site/perm.js       —— 依目前這個人的權限，把關掉的功能蓋上鎖頭（「此功能需開通」）
     · site/admin.js      —— #admin/perm 管理頁，依分類列出開關
     · scripts/_uitest.py —— 「會員權限開關」段落驗每個選擇器真的抓得到、鎖頭真的出現
   後端（workers/account-api/worker.js）刻意**不**抄這份清單（只驗鍵的格式），新增功能不必重新部署 Worker。

   盤點方式（2026-10-02）：grep site/index.html 的 view／card id、site/modules.js 的 27 塊積木、
   industry.js 的個股分頁（STOCK_TABS）與 K 線週期（TF_BUILTIN）、mobile3.js 的手機個股分頁（SK_TABS）、
   live.js 的「即時」開關、theme4.js 的外觀面板、watchlists.js 的分頁上限。

   欄位：
     id     開關的鍵（存在 Worker；**上線後不要改名**，改了等於所有人的設定歸零）
     name   管理頁上的名字
     cat    分類（見 CATS）
     desc   管理頁上的一句說明：關掉之後使用者會看到什麼
     def    預設值。★ 全部 true（上限類是最大值）—— 這次上線不能讓任何人突然看不到功能；
            要收費的功能是管理者在 #admin/perm 把「訪客」或「免費會員」範本關掉，不是改這裡。
     kind   'bool'（開／關）或 'limit'（數量上限，0～max）
     veil   關掉時要蓋上鎖頭的區塊：[選擇器, 條件?]。條件（選擇器）有寫的話，只有它在畫面上抓得到時才蓋 ——
            例如個股「營收」分頁：只有「營收」那顆分頁鈕是 .on 的時候，才把內容區蓋起來。
     mark   關掉時掛上 🔒 小標、但照樣點得下去的鈕（分頁鈕：點進去看到的是鎖頭說明，不是什麼都沒發生）
     block  關掉時掛上 🔒 小標、而且按了不會動作的鈕（只跳一句「此功能需開通」）
   ⚠ 選擇器一律挑「外框」（卡片、區塊），不要挑 canvas／img —— 鎖頭是畫在外框的 ::after 上，替換元素沒有 ::after。
   ============================================================================ */
(function () {
  'use strict';
  var CATS = [
    { id: 'overview', name: '總覽' },
    { id: 'flow', name: '資金流向' },
    { id: 'industry', name: '產業地圖／產業鏈' },
    { id: 'heatmap', name: '熱力圖' },
    { id: 'market', name: '市場明細／週期統計' },
    { id: 'stockk', name: '個股頁：K 線與工具' },
    { id: 'stocktab', name: '個股頁：分頁' },
    { id: 'global', name: '即時與全站工具' },
    { id: 'watch', name: '自選' },
    { id: 'etf', name: 'ETF 專區' },
    /* 2026-10-05（admin-v2，Andy B）：族群觀測。項目不寫死在這裡 —— 由 groups.yaml 產生的 groups_today.json 決定，
       管理頁與鎖頭各自呼叫 addGroups() 補進來（見下面 grpKey 的鍵對照）。*/
    { id: 'grp', name: '族群觀測' },
    { id: 'explore', name: '選股策略' },  // 2026-10-05 新分類（docs/explore_page_spec.md）
    { id: 'earnings', name: '財經日曆' }   // 2026-10-05（晚）新分類（site/earnings.js）
  ];

  /* 個股分頁：桌機（#stockTabs／#stockTab）與手機（#mbTabs／#mbBody）是兩套 DOM、兩套代號，這裡一次宣告兩邊 */
  function stab(id, name, desk, mob, desc) {
    var veil = [], mark = [];
    if (desk) { veil.push(['#stockTab', '#stockTabs button[data-t="' + desk + '"].on']); mark.push('#stockTabs button[data-t="' + desk + '"]'); }
    (mob || []).forEach(function (m) { veil.push(['#mbBody[data-tab="' + m + '"]']); mark.push('#mbTabs button[data-t="' + m + '"]'); });
    return { id: id, name: name, cat: 'stocktab', def: true, kind: 'bool', desc: desc, veil: veil, mark: mark, block: [] };
  }
  /* K 線週期：週期鈕按了不動作；萬一目前就停在被關掉的週期（例如預設「分時」），把圖蓋起來、其他週期照樣能切 */
  function ktf(id, name, tfs, desc) {
    return { id: id, name: name, cat: 'stockk', def: true, kind: 'bool', desc: desc,
      veil: tfs.map(function (t) { return ['#chartWrap', '#tfSeg button[data-tf="' + t + '"].on']; }),
      mark: [], block: tfs.map(function (t) { return '#tfSeg button[data-tf="' + t + '"]'; }) };
  }
  function box(id, cat, name, sel, desc) {
    return { id: id, name: name, cat: cat, def: true, kind: 'bool', desc: desc, veil: sel.map(function (s) { return [s]; }), mark: [], block: [] };
  }

  var LIST = [
    // ---- 總覽
    box('ov.summary', 'overview', '今日摘要卡列', ['#hero'], '大盤圖上方四張摘要卡（漲跌家數、資金輪盤、資金分流樹、熱門題材）'),
    /* #mbIdx：手機總覽的指數列（手機不顯示 #m3，指數改在這一列）—— 2026-10-07 覆蓋稽核補上，不然手機看大盤不吃次數 */
    box('ov.index', 'overview', '大盤三張圖', ['#m3', '#mbIdx'], '加權／櫃買／台指期走勢（含日夜盤、分 K）'),
    box('ov.heat', 'overview', '資金熱力圖', ['#ovHeatCard'], '族群成交值與資金流入流出的熱力方塊'),
    box('ov.theme', 'overview', '熱門題材', ['#ovThemeCard'], '題材熱度熱力圖與成分股'),
    box('ov.rot', 'overview', '資金輪盤', ['#rotClockMiniWrap', '#ovRotKpi'], '總覽右欄的族群強弱輪盤'),
    box('ov.flow', 'overview', '昨日資金分流樹', ['#ovFlowWrap'], '總覽右欄的資金分流樹簡圖'),
    box('ov.breadth', 'overview', '漲跌家數分佈', ['#ovBreadthCard'], '依漲跌幅分級的家數直條（全部／上市／上櫃）'),
    // ---- 資金流向
    box('flow.rot', 'flow', '輪動時鐘＋族群資金排行', ['#flowRotCard'], '族群相對強弱四象限與成交值／法人排行（同一張卡）'),
    box('flow.sankey', 'flow', '資金分流樹（桑基）', ['#flowSankeyCard'], '大盤 → 產業鏈 → 族群的資金分流圖'),
    box('flow.inst', 'flow', '族群 × 法人', ['#flowInstCard'], '三大法人淨買超落在哪些族群'),
    box('flow.conc', 'flow', '資金集中度', ['#flowConcCard'], '前 5／10 大族群佔成交值比重'),
    // ---- 產業
    box('ind.map', 'industry', '產業地圖', ['#indMap'], '產業鏈列表與強弱（產業地圖首頁）'),
    box('ind.groups', 'industry', '族群總覽（長條＋圓餅）', ['#gpSec'], '單一產業鏈裡各族群的漲跌與成交值占比'),
    box('ind.diagram', 'industry', '產業鏈剖析圖（2D）', ['#dgSec'], '產品／製程剖析圖、點零件看供應商'),
    { id: 'ind.3d', name: '3D 剖析圖', cat: 'industry', def: true, kind: 'bool', desc: '剖析圖的 3D 模式（2D 不受影響）',
      veil: [['.dg3dbox']], mark: [], block: ['button[data-dm="3d"]'] },
    box('ind.rel', 'industry', '供應鏈關聯圖', ['#relSec'], '環節詳情與分層關聯圖'),
    // ---- 熱力圖
    box('heat.market', 'heatmap', '全市場熱力圖', ['#indHeat'], '整個台股一次看的產業熱力方塊'),
    box('heat.theme', 'heatmap', '題材資金熱力', ['#themeMapCard'], '題材熱度熱力圖'),
    box('heat.detail', 'heatmap', '題材剖析圖', ['#themeDetail'], '點題材後展開的上中下游剖析'),
    // ---- 市場明細／週期統計
    { id: 'mkt.updown', name: '市場明細：漲跌家數', cat: 'market', def: true, kind: 'bool', desc: '漲跌家數名單',
      veil: [['#mktBody', '#mktSeg2 button[data-k="updown"].on']], mark: ['#mktSeg2 button[data-k="updown"]'], block: [] },
    { id: 'mkt.streak', name: '市場明細：法人連買賣', cat: 'market', def: true, kind: 'bool', desc: '法人連續買賣超四象限',
      veil: [['#mktBody', '#mktSeg2 button[data-k="streak"].on']], mark: ['#mktSeg2 button[data-k="streak"]'], block: [] },
    { id: 'mkt.ma', name: '市場明細：站上均線', cat: 'market', def: true, kind: 'bool', desc: '站上均線名單',
      veil: [['#mktBody', '#mktSeg2 button[data-k="ma"].on']], mark: ['#mktSeg2 button[data-k="ma"]'], block: [] },
    { id: 'mkt.cand', name: '市場明細：今日關注', cat: 'market', def: true, kind: 'bool', desc: '回檔型態／突破型態條件名單',
      veil: [['#mktBody', '#mktSeg2 button[data-k="cand"].on']], mark: ['#mktSeg2 button[data-k="cand"]'], block: [] },
    box('season.month', 'market', '週期統計', ['#v-season'], '族群在各月份的歷史表現（整頁）'),
    // ---- 個股頁：K 線與工具
    ktf('stock.k_day', 'K 線（日／週／月）', ['1d', '1w', '1M'], '日、週、月 K 週期鈕'),
    /* 2026-10-06（DECISIONS #326）：即時只給管理者 —— 非管理者的「分時」是最近交易日的盤後分時（資料湖 60 分 K），名稱拿掉「即時」（id 不改）；
       1／5／15 分 K 只有即時來源，非管理者整排不列，標 adminOnly（訂閱頁的權益對照表不列，免得寫成付費就有）。*/
    ktf('stock.tick', '分時走勢', ['tick'], '分時走勢（管理者盤中即時；其他人看最近交易日的盤後分時）'),
    Object.assign(ktf('stock.k_min', '分 K（1／5／15 分）', ['1m', '5m', '15m'], '短週期分 K（即時來源，只有管理者帳號看得到）'), { adminOnly: true }),
    ktf('stock.k_hour', '1H／4H K 線', ['60m', '240m'], '60 分與 240 分 K'),
    { id: 'stock.mtf', name: '四週期同看', cat: 'stockk', def: true, kind: 'bool', desc: '一次看四個週期的小圖',
      veil: [['#chartWrap', '#mtfGrid']], mark: [], block: ['#mtfBtn'] },
    { id: 'stock.ind', name: '指標設定', cat: 'stockk', def: true, kind: 'bool', desc: 'K 線上的指標開關、參數、顏色（關掉時沿用預設指標）',
      veil: [], mark: [], block: ['#indBtn'] },
    { id: 'stock.draw', name: '畫線工具', cat: 'stockk', def: true, kind: 'bool', desc: 'K 線上畫趨勢線、水平線',
      veil: [['#drawBar']], mark: [], block: ['#drawTgl'] },
    { id: 'stock.ai', name: 'AI 分析', cat: 'stockk', def: true, kind: 'bool', desc: '技術／籌碼／基本／消息四面向的規則式分析',
      /* 2026-10-02（#294）：個股「總覽」分頁也有一份 AI 分析（重點卡 #ovAiBrief ＋ 技術面／基本面／消息面三張細節卡 [data-ai]），一起上鎖；
         技術面訊號那一張是積木 stock.signal，跟著「總覽」分頁這一項走，不跟 AI 分析
         2026-10-02 深夜（#297）：四張併成右欄一張 AI 卡（#ovAiCard），選擇器不變：#ovAiBrief＝卡裡那一行重點、
         #ovFacets [data-ai]＝技術面／基本面／消息面三面。卡片標題與分頁籤不鎖 —— 鎖了就切不到技術面訊號那一面 */
      veil: [['#skAi'], ['#aiCard'], ['#mbBody[data-tab="ai"]'], ['#ovAiBrief'], ['#ovFacets [data-ai]']], mark: ['#mbTabs button[data-t="ai"]'], block: [] },
    // ---- 個股頁：分頁
    // 2026-10-02：排列順序跟著個股分頁的新順序（基本資料搬到總覽旁邊，#294）；id 一個都沒改（改了＝所有人的設定歸零）
    stab('stock.overview', '總覽（技術訊號）', 'overview', [], '個股分頁「總覽」：基本面與籌碼小圖、技術面訊號卡、同業比較'),
    stab('stock.basics', '基本資料', 'basics', ['basic'], '公司基本資料'),
    stab('stock.tags', '指標', 'tags', ['tag'], '個股分頁「指標」'),
    stab('stock.revenue', '營收', 'revenue', ['rev'], '月營收、年增率'),
    stab('stock.profit', '獲利', 'profit', ['profit', 'fin'], '季獲利、三率、本益比（手機的「財務」也算這一項）'),
    stab('stock.dividend', '除權息', 'dividend', ['div'], '股利與除權息'),
    stab('stock.inst', '法人', 'inst', ['inst'], '三大法人買賣超'),
    stab('stock.margin', '資券', 'margin', ['margin'], '融資融券'),
    stab('stock.holders', '大戶／散戶', 'holders', ['big'], '集保大戶與散戶持股'),
    stab('stock.news', '公告／新聞', 'news', ['news'], '重大訊息與新聞'),
    // ---- 即時與全站工具
    /* ★ 2026-10-06（Andy：「所有的即時功能，只有在我這帳號才會出現，其他帳號都隱藏」，DECISIONS #326）：
       即時另外有一道「只有管理者」的閘門（site/livegate.js），這個開關只對管理者自己還有意義；對其他人開或關都一樣看不到。
       adminOnly＝訂閱頁的權益對照表不列。block 拿掉 .ovl-tg：非管理者的那顆只是資料日期標籤，不該掛鎖頭。*/
    { id: 'live.tick', name: '盤中即時（5 秒）', cat: 'global', def: true, kind: 'bool', adminOnly: true,
      desc: '盤中每 5 秒更新報價（2026-10-06 起只有管理者帳號看得到；這個開關對其他人沒有作用）', veil: [], mark: [], block: ['.livetg-b'] },
    { id: 'events', name: '今日事件中心', cat: 'global', def: true, kind: 'bool', desc: '新聞／法說／總經事件抽屜',
      veil: [['#side'], ['#ovEvents']], mark: [], block: ['#evToggle', '#mmEvents'] },
    { id: 'theme', name: '主題外觀', cat: 'global', def: true, kind: 'bool', desc: '切換深淺色與版面風格（關掉時維持目前外觀）',
      veil: [], mark: [], block: ['#themeBtn', '#mmTheme', '#t4Btn', '#t4Pop button', '#mmT4 button'] },
    // ---- 選股探索（2026-10-05）：預設全開；要收費時管理者在 #admin/perm 關「訪客／免費會員」範本
    box('explore.page', 'explore', '選股策略頁（Strategy Lab）', ['#v-explore'], '策略卡片牆與完整名單（整頁）'),
    box('explore.chart', 'explore', '策略卡片牆', ['#slGrid'], '每個策略一張卡、前 3 檔與入選原因'),
    box('explore.combo', 'explore', '篩選條件與資料出處', ['.sl-info'], '每張卡的條件、計算方式、資料日期與出處'),
    box('explore.list', 'explore', '完整名單', ['.sl-ftbl'], '#explore/<策略> 全部符合的公司與原因欄'),
    // ---- ETF 專區（2026-10-05，site/etfpage.js）
    box('etf.list', 'etf', 'ETF 一覽', ['#etfListCard'], 'ETF 卡片清單、分類切換、殖利率與規模'),
    box('etf.popular', 'etf', '最受歡迎前 5 名', ['#etfPopCard'], '各分類內：受益人數週增加／近 20 日成交值前 5 名'),
    box('etf.rettop', 'etf', '報酬率前 5 名', ['#etfRetTopCard'], '各分類內：含息年化報酬前 5 名（跟著期間選擇）'),
    box('etf.yldtop', 'etf', '殖利率前 5 名', ['#etfYldCard'], '各分類內：近 12 個月殖利率前 5 名與平均填息天數'),
    box('etf.calendar', 'etf', '配息行事曆', ['#etfCalCard'], '7 欄月曆：除息日、配息金額、當次殖利率與填息天數'),
    box('etf.returns', 'etf', '報酬比較（自選）', ['#etfRetCard'], '各分類內自選最多 8 檔，比較累積報酬、年化與殖利率'),
    // ---- 財報日曆（2026-10-05，site/earnings.js）：預設全開；要收費時管理者在 #admin/perm 關範本
    box('earn.page', 'earnings', '財經日曆頁（整頁）', ['#v-earnings'], '月曆與右側分析面板（整頁）'),
    box('earn.cal', 'earnings', '行事曆月曆', ['#earnCalCard'], '月曆（公司財報／公司法說／FED 消息）與右側分析面板'),
    // ---- 自選
    box('watch.page', 'watch', '自選清單頁', ['#v-watch'], '自選分頁（整頁）'),
    /* ★ 2026-10-07（Andy：「註冊可以自選一個分頁且10檔股票…plus 可以新增5個分頁、pro 可以不限分頁」，docs/quota_plan.md）：
       def 改成免費會員的值（1 頁／每頁 10 檔）；Plus 5 頁／50 檔、Pro「不限」由 account-api 種範本時寫進 feats。
       「不限」實作上是硬上限：分頁 50、每頁 200 檔（max；admin 選單最後一格顯示「不限」）—— 前端、Worker 都守這兩個數，
       免得一份清單長到拖慢同步。opts＝管理頁下拉的選項（不必列出 0～200 每一個數）、unit＝顯示單位。
       ⚠ 連不到會員伺服器（TwPerm src＝default）時 watchlists.js 退回舊的 5 頁／50 檔 —— 寧可多給，不要誤鎖（perm.js 同一個原則）。*/
    { id: 'watch.tabs', name: '自選分頁數上限', cat: 'watch', def: 1, kind: 'limit', max: 50, unit: '頁', opts: [0, 1, 2, 3, 5, 10, 20, 50],
      desc: '最多能建幾頁自選清單（已經建好的不會被刪，只是不能再新增）', veil: [], mark: [], block: [] },
    { id: 'watch.size', name: '每頁自選檔數上限', cat: 'watch', def: 10, kind: 'limit', max: 200, unit: '檔', opts: [0, 5, 10, 20, 30, 50, 100, 200],
      desc: '每一頁自選清單最多放幾檔（已經放的不會被刪，只是不能再加）', veil: [], mark: [], block: [] }
  ];

  /* ---- 全站權限矩陣 2026-10-08（docs/perm_matrix_1008.md §6；Andy 10-08 原話見那份文件）新增的功能鍵 ----
     兩種：
     ① 動作計次（act）：每日 N 次存在範本的 lims（跟其他功能的「每日瀏覽次數」同一個欄位、同一顆 ∞／N/日 徽章），
        計數在 site/quota.js 的 TwQuota.act(功能鍵, 單位, 對象)，單位＝tab／filter／drill／obj（矩陣 §2）。開關 def:true，
        關掉或次數 0＝不能用。veil 空：這些是「點了才算」的動作，沒有一整塊要蓋，擋下時跳置中卡片。
     ② 同時選取上限（pick）：kind:'limit'，存在 feats；defBy＝範本沒寫時依身分的預設（訪客／註冊會員），付費範本沒寫＝不限（max）。
        不用單一 def：線上的 Plus／Pro 範本沒有這些鍵，只給一個 def 不是訪客沒被擋、就是付費會員被誤擋。
     Worker（account-api）只驗鍵的格式與整數範圍，所以新增鍵**不必重新部署 Worker**。*/
  function act(id, cat, name, unit, desc) { return { id: id, name: name, cat: cat, def: true, kind: 'bool', act: unit, desc: desc, veil: [], mark: [], block: [] }; }
  function pickF(id, cat, name, unit, max, opts, g, fr, desc) { return { id: id, name: name, cat: cat, kind: 'limit', unit: unit, max: max, def: max, opts: opts, defBy: { guest: g, free: fr }, desc: desc, veil: [], mark: [], block: [] }; }
  LIST.push(
    act('flow.sankey.drill', 'flow', '分流樹下鑽個股', 'drill', '資金分流樹點族群展開成個股（右欄變族群內個股排行）；每日次數用完只能看全部族群那一層（資金流向排名）。同一族群同一天重點不重算'),
    act('flow.inst.filter', 'flow', '族群×法人族群篩選', 'filter', '族群×法人左上「族群」下拉每選一個族群算一次（同一族群同一天不重算；選「全部族群」不算）'),
    act('earn.tab', 'earnings', '財經日曆切分頁', 'tab', '月曆切到其他月份（回本月不算）'),
    act('explore.filter', 'explore', '選股策略篩選', 'filter', '子標籤勾選的每一組不同條件算一次（清除不算）'),
    act('etf.calendar.tab', 'etf', '配息行事曆切分頁', 'tab', '配息行事曆切到其他月份（本月不算）'),
    act('etf.list.tab', 'etf', 'ETF 一覽分類分頁', 'tab', 'ETF 總覽的分類分頁（股票型／債券型…）點一個不同的算一次'),
    act('etf.list.filter', 'etf', 'ETF 一覽篩選', 'filter', 'ETF 一覽的排序條件（成交值／規模／殖利率／漲跌）換一個不同的算一次'),
    act('season.pick', 'market', '週期統計切換對象', 'obj', '週期統計換排序月份或換看哪幾個族群（最強／最弱／平均線）'),
    pickF('mkt.grp.pick', 'market', '市場明細族群篩選上限', '個', 999, [0, 3, 5, 10, 20, 30, 50, 999], 5, 10, '漲跌分佈「族群」篩選同時最多勾幾個（右邊清單不限制）'),
    pickF('explore.list.n', 'explore', '選股完整名單顯示檔數', '檔', 999, [0, 3, 5, 10, 20, 50, 100, 999], 5, 20, '完整名單最多顯示前幾檔'),
    pickF('mkt.cand.n', 'market', '今日關注顯示檔數', '檔', 999, [0, 3, 5, 10, 20, 50, 999], 3, 10, '今日關注名單最多顯示前幾檔'),
    pickF('etf.returns.n', 'etf', '報酬比較自選檔數', '檔', 20, [0, 3, 5, 8, 10, 20], 0, 3, '報酬比較同時最多比幾檔（20＝硬上限）'),
    { id: 'etf.cashflow', name: 'ETF 現金流試算', cat: 'etf', def: true, kind: 'bool', route: /^#etf\/inc/, desc: '月配／複利現金流試算（矩陣：只給付費會員）', veil: [['#etfInc']], mark: ['#etfSub button[data-v="inc"]'], block: [] },
    /* 2026-10-08 Andy：「熱力圖如果不是付費會員 都不能有點擊連結功能，但如果是才可以點擊連結到其他分頁」。
       全站樹狀熱力圖（總覽資金熱力圖／熱門題材、熱力圖產業頁／題材頁、各自的放大視窗）點方塊「跳到其他分頁」只有開著才行；
       頁內展開（題材頁點方塊開下方剖析圖、總覽熱門題材換成分股）不受這個開關管，照矩陣次數走。實作在 site/quota.js（heatLinkOk）。
       defBy：範本沒寫時訪客關、註冊會員關，付費範本沒寫＝開。*/
    { id: 'heat.link', name: '熱力圖點擊跳頁', cat: 'heatmap', def: true, kind: 'bool', defBy: { guest: false, free: false },
      desc: '點熱力圖方塊跳到族群／題材／個股頁（關掉：提示框、縮放照常，點了跳升級提示、游標不變手指）', veil: [], mark: [], block: [] },
    { id: 'etf.top3', name: 'ETF 總覽上方三張卡（共用次數）', cat: 'etf', def: true, kind: 'bool', desc: '最受歡迎／報酬率／殖利率前 5 三張卡共用一個每日次數（看一次＝這個分頁打開一次）', veil: [['#etfTri']], mark: [], block: [] }
  );

  /* ---- 瀏覽次數（admin-v3，2026-10-05，蓋掉 sub-v1 的三個 quota.* 開關）
     Andy：「每個功能後面加『瀏覽次數』上限欄位」—— 上限不再是三個獨立的功能，而是**每個功能各自的一個欄位**
     （存在範本的 lims，跟開關 feats 分開；Worker 的 plans.lims，見 worker.js admin-v3 區塊）。
     語意沿用 sub-v1：留空＝不限、0＝不能看、N＝每日 N 次（計數與遮罩在 site/quota.js）。
     原本 quota.stock「個股頁每日檔數」需要一個「整個個股頁」的功能來掛上限 → 新增 stock.page（route 限定 #stock/ 才算）。
     quota.ai → stock.ai 的上限、quota.theme → heat.detail 的上限，不另設功能。 */
  LIST.push({ id: 'stock.page', name: '個股頁（整頁）', cat: 'stocktab', def: true, kind: 'bool', route: /^#stock\//,
    desc: '整個個股頁（關掉＝個股頁蓋鎖頭；設瀏覽次數＝一天能看幾檔，同一檔重複看不重算）', veil: [['#v-industry']], mark: [], block: [] });

  /* ★ 2026-10-07「全站共用每日額度」（quota.all，docs/quota_plan.md、docs/plan_tiers_1007.md）：哪些功能算「研究頁」、會吃共用額度。
     清單＝方案草案裡訪客要計次的那 41 項（總覽、產業地圖首頁、事件、自選、工具類不算 —— 那些是鉤子或不是「看資料」）。
     共用額度存在範本的 dq 欄位（account-api 每日額度區塊；TwPerm.lim('quota.all') 讀它），不是一個開關 —— 所以這裡不另外列一項「quota.all」，
     不然 #admin/perm 會把它畫成一顆開關。單位＝這一頁（site/quota.js 的 pageKey：個股代號／剖析圖／題材／族群／一次造訪）。*/
  var METERED = ["earn.cal", "earn.page", "etf.calendar", "etf.list", "etf.popular", "etf.rettop", "etf.yldtop", "explore.chart", "explore.combo", "explore.list", "explore.page", "flow.conc", "flow.inst", "flow.rot", "flow.sankey", "heat.detail", "heat.market", "heat.theme", "ind.diagram", "ind.groups", "ind.rel", "mkt.cand", "mkt.ma", "mkt.streak", "mkt.updown", "season.month", "stock.ai", "stock.basics", "stock.dividend", "stock.holders", "stock.inst", "stock.k_day", "stock.k_hour", "stock.margin", "stock.news", "stock.overview", "stock.page", "stock.profit", "stock.revenue", "stock.tags", "stock.tick"];
  METERED.forEach(function (id) { var f = LIST.filter(function (x) { return x.id === id; })[0]; if (f) f.metered = true; });

  var BY = {};
  LIST.forEach(function (f) { BY[f.id] = f; });
  /* 範本沒寫這一項時的值：有 defBy（同時選取上限）就依範本代號（guest／free；其他＝付費）挑，沒有就是 def */
  function defOf(f, plan) { return f && f.defBy && Object.prototype.hasOwnProperty.call(f.defBy, plan) ? f.defBy[plan] : f ? f.def : undefined; }
  function defaults(plan) { var o = {}; LIST.forEach(function (f) { o[f.id] = defOf(f, plan); }); return o; }
  function inCat(c) { return LIST.filter(function (f) { return f.cat === c; }); }

  /* ---- 族群鍵（grp.<鍵>）—— Worker 的 FEAT_RE 是 /^[a-z][a-z0-9_.]{1,39}$/，group_id 不一定符合：
     ① 純小寫英數底線（mlcc、ic_substrate、ai_server_odm…，groups.yaml 手寫的 83 個）→ 原樣：grp.mlcc
     ② 有大寫的英數（ind_ETF）→ 轉小寫：grp.ind_etf
     ③ 含中文的自動桶（ind_半導體業、ind_光電業…，build_payload 依法定產業別產生的 34 個）→ 中文那段換成
        FNV-1a 32 位元雜湊的 8 碼十六進位：ind_半導體業 → grp.ind_x<8 碼>。
        用雜湊而不是流水號：族群清單增減時，別的族群的鍵不會跟著位移（流水號一位移，所有人的設定就對錯族群）。
     ④ 太長（> 35 字）→ 前 26 字 ＋ _ ＋ 8 碼雜湊。目前 117 個族群最長 18 字，沒有人走到這條。
     ★ 鍵一旦上線就不要改算法 —— 改了等於所有範本裡的族群開關全部對不到人（同 features 的 id 規矩）。*/
  function fnv(s) { var h = 0x811c9dc5; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return ('0000000' + h.toString(16)).slice(-8); }
  function grpKey(gid) {
    var g = String(gid == null ? '' : gid);
    var low = g.toLowerCase();
    var k;
    if (/^[a-z][a-z0-9_]*$/.test(low)) k = low;
    else {
      var m = /^([a-z][a-z0-9_]*?_)?(.*)$/.exec(low);
      var pre = m && m[1] && /[^\x00-\x7f]/.test(m[2]) ? m[1] : 'g_';
      k = pre + 'x' + fnv(g);
    }
    if (k.length > 35) k = k.slice(0, 26) + '_' + fnv(g);
    return 'grp.' + k;
  }
  /* groups：[{ group_id, group_name, chain }]（groups_today.json 的列）。重複呼叫只補沒有的；回傳這次新增幾個 */
  var CHAIN = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '電子', traditional: '傳產', infrastructure: '基礎建設', software: '軟體', financial: '金融', industry: '法定產業別' };
  function addGroups(groups) {
    var n = 0;
    (groups || []).forEach(function (g) {
      if (!g || !g.group_id) return;
      var id = grpKey(g.group_id);
      if (BY[id]) return;
      var f = { id: id, gid: g.group_id, name: g.group_name || g.group_id, cat: 'grp', def: true, kind: 'bool', chain: g.chain || '',
        desc: (CHAIN[g.chain] || g.chain || '其他') + '・關掉：族群頁模糊＋鎖頭、下拉清單鎖住、熱力圖／排行／輪盤點了不展開',
        veil: [], mark: [], block: [] };
      LIST.push(f); BY[id] = f; n++;
    });
    return n;
  }

  window.TwFeatures = { list: LIST, cats: CATS, byId: function (id) { return BY[id] || null; }, defaults: defaults, defOf: defOf, inCat: inCat, grpKey: grpKey, addGroups: addGroups };
})();
