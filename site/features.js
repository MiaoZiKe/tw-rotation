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
    { id: 'watch', name: '自選' }
  ];

  /* 個股分頁：桌機（#stockTabs／#stockTab）與手機（#mbTabs／#mbBody）是兩套 DOM、兩套代號，這裡一次宣告兩邊 */
  function stab(id, name, desk, mob, desc) {
    var veil = [], mark = [];
    if (desk) { veil.push(['#stockTab', '#stockTabs button[data-t="' + desk + '"].on']); mark.push('#stockTabs button[data-t="' + desk + '"]');
      /* 2026-10-03 手機 V2（#314）：手機分頁列（#mbTabs）改用跟桌機同一組代號、內容就是桌機那一頁（#stockTab），鎖頭標記跟著掛 */
      mark.push('#mbTabs button[data-t="' + desk + '"]'); }
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
    box('ov.summary', 'overview', '今日摘要卡列', ['#hero'], '大盤圖上方四張摘要卡（漲跌家數、資金輪盤、資金去向、熱門題材）'),
    box('ov.index', 'overview', '大盤三張圖', ['#m3'], '加權／櫃買／台指期走勢（含日夜盤、分 K）'),
    box('ov.heat', 'overview', '資金熱力圖', ['#ovHeatCard'], '族群成交值與資金流入流出的熱力方塊'),
    box('ov.theme', 'overview', '熱門題材', ['#ovThemeCard'], '題材熱度熱力圖與成分股'),
    box('ov.rot', 'overview', '資金輪盤', ['#rotClockMiniWrap', '#ovRotKpi'], '總覽右欄的族群強弱輪盤'),
    box('ov.flow', 'overview', '昨日資金去向', ['#ovFlowWrap'], '總覽右欄的資金去向簡圖'),
    box('ov.breadth', 'overview', '漲跌家數分佈', ['#ovBreadthCard'], '依漲跌幅分級的家數直條（全部／上市／上櫃）'),
    // ---- 資金流向
    box('flow.rot', 'flow', '輪動時鐘＋資金流向排行', ['#flowRotCard'], '族群相對強弱四象限與成交值／法人排行（同一張卡）'),
    box('flow.sankey', 'flow', '資金去向（桑基）', ['#flowSankeyCard'], '大盤 → 產業鏈 → 族群的資金分流圖'),
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
    { id: 'mkt.cand', name: '市場明細：今日候選', cat: 'market', def: true, kind: 'bool', desc: '回檔承接／突破追進候選名單',
      veil: [['#mktBody', '#mktSeg2 button[data-k="cand"].on']], mark: ['#mktSeg2 button[data-k="cand"]'], block: [] },
    box('season.month', 'market', '週期統計', ['#v-season'], '族群在各月份的歷史表現（整頁）'),
    // ---- 個股頁：K 線與工具
    ktf('stock.k_day', 'K 線（日／週／月）', ['1d', '1w', '1M'], '日、週、月 K 週期鈕'),
    ktf('stock.tick', '分時即時', ['tick', '5s'], '當日分時走勢與 5 秒線'),
    ktf('stock.k_min', '分 K（1／5／15 分）', ['1m', '5m', '15m'], '短週期分 K'),
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
    { id: 'live.tick', name: '盤中即時（5 秒）', cat: 'global', def: true, kind: 'bool',
      desc: '盤中每 5 秒更新報價；關掉＝看盤後資料（卡片上的「即時」鈕按了不動作）', veil: [], mark: [], block: ['.livetg-b', '.ovl-tg'] },   // .ovl-tg＝總覽摘要卡右上角的即時開關（DECISIONS #296）
    { id: 'events', name: '今日事件中心', cat: 'global', def: true, kind: 'bool', desc: '新聞／法說／總經事件抽屜',
      veil: [['#side'], ['#ovEvents']], mark: [], block: ['#evToggle', '#mmEvents'] },
    { id: 'theme', name: '主題外觀', cat: 'global', def: true, kind: 'bool', desc: '切換深淺色與版面風格（關掉時維持目前外觀）',
      veil: [], mark: [], block: ['#themeBtn', '#mmTheme', '#t4Btn', '#t4Pop button', '#mmT4 button'] },
    // ---- 自選
    box('watch.page', 'watch', '自選清單頁', ['#v-watch'], '自選分頁（整頁）'),
    { id: 'watch.tabs', name: '自選分頁數上限', cat: 'watch', def: 5, kind: 'limit', max: 5,
      desc: '最多能建幾頁自選清單（已經建好的不會被刪，只是不能再新增）', veil: [], mark: [], block: [] }
  ];

  var BY = {};
  LIST.forEach(function (f) { BY[f.id] = f; });
  function defaults() { var o = {}; LIST.forEach(function (f) { o[f.id] = f.def; }); return o; }
  function inCat(c) { return LIST.filter(function (f) { return f.cat === c; }); }

  window.TwFeatures = { list: LIST, cats: CATS, byId: function (id) { return BY[id] || null; }, defaults: defaults, inCat: inCat };
})();
