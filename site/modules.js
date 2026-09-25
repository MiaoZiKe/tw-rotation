/* ============================================================================
   積木清單（site/modules.js）—— 全站 27 塊積木的唯一宣告處
   ----------------------------------------------------------------------------
   為什麼有這支檔（docs/feature_modules.md §4 第 4 項＋第 12 項，2026-09-24 第一梯次）：
     以前「把一張卡搬到別的地方」要同時改四處：① index.html 的 HTML ② render 函式
     ③ app.js 裡手寫的 `MIA_PAGER`（手機分段表，一串 CSS 選擇器字串）④ `_uitest.py` 的段落對照
     （CLAUDE.md 那張人工表）。四處之間沒有任何東西綁著，改了一處忘了另一處只會在手機上默默少一段。

     現在 ③ 與 ④ 從這一份清單產生：
       · app.js 的 `MIA_PAGER` ＝ `TwModules.pager()`（不再手寫選擇器）
       · `_uitest.py --module <積木id>` 直接照這份清單的 `tests` 挑段落；
         段落「積木清單」驗 27 個 id 跟 docs/feature_modules.md 一致、每個選擇器在畫面上真的抓得到、
         產生出來的手機分段跟畫面上的分段列一模一樣。
     ① ② 還沒動（那是第二梯次的「模組宣告檔＋版面設定」，§4.1 第 4 項）。

   ⚠ 格式刻意寫成**純 JSON**（夾在兩個標記之間），因為 `_uitest.py`（Python）要直接讀它：
     不准在 JSON 裡寫註解、不准尾逗號。為什麼這樣排的理由寫在 `note` 欄位 —— 它是資料，不會丟。

   欄位：
     id        積木 id（跟 docs/feature_modules.md §3 的 27 個一致，驗收會比對）
     name      中文名
     question  回答四問的哪一問（① 錢往哪跑／② 貴不貴／③ 何時進場／④ 別進的理由／知識）
     ask       這塊積木回答的那一句話
     tier      方案層級（docs/compliance_and_tiers.md §2-2；〔推〕＝依同一套原則推的）
     law       法遵顏色（🟢 低／🟡 中低／🟠 中高／🔴 高）
     at        放在哪裡：[{ page, selector[], seg?, step?, ord? }]
                 page      頁面代號（見 PAGES）
                 selector  這塊積木在那一頁的 DOM（全部要一起顯示／一起藏）
                 seg       手機分段導覽（≤640px）裡屬於哪一段；沒有就不參與分段（永遠顯示）
                 step      總覽的主軸動線第幾步（1～4），只有總覽用
                 ord       同一頁裡的段落順序（小的在前）
                 note      為什麼這樣放
     tests     `_uitest.py` 裡驗這塊積木的段落名
   ============================================================================ */
(function () {
  'use strict';

  /* 頁面代號 → 驗收時打開的網址。`stock` 的代號由驗收自己帶（預設 2330）。*/
  var PAGES = /*PAGES-JSON*/{
    "overview": "#overview", "flow": "#flow", "market": "#market/updown", "season": "#season",
    "heatmap": "#heatmap", "industry": "#industry", "chain": "#industry/ai_server", "stock": "#stock/{code}"
  }/*END-PAGES-JSON*/;

  var MODULES = /*MODULES-JSON*/[
    { "id": "flow.clock", "name": "輪動時鐘", "question": "①", "ask": "哪些族群相對大盤在轉強，它們跑到強弱循環的哪一段",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "overview", "step": 1, "seg": "足跡輪盤", "ord": 10,
          "selector": ["#ovRotCard", "#ovRotHead", "#ovRotKpi", "#how-rotm", "#rotClockMiniWrap"],
          "note": "第①步的主圖。它就是「錢往哪個族群跑」最直接的一張圖，以前是總覽中段的一張卡、要捲 1911px 才看得到。#ovRotCard 是跟「資金去向」共用的卡片外殼：桌機一張卡兩件事（量到 1059px），手機拆兩段；兩段都要列外殼，不然另一段會留下一個 34px 高的空卡片（實測）。#ovRotKpi 是手機才長出來的四象限計數（miaRotKpi）。" },
        { "page": "flow", "seg": "輪動", "ord": 10, "selector": ["#flowRotCard"],
          "note": "跟 flow.rank 合併在同一張卡（2026-09-21 Andy：兩張圖合併、共用篩選），所以兩塊積木宣告同一段。" }
      ],
      "tests": ["新-輪動時鐘", "資金輪動合併", "輪動時鐘即時", "輪動象限面板", "批次30-兩層下拉與象限卡", "總覽", "足跡輪盤全部腳印"] },

    { "id": "flow.rank", "name": "資金流向排行", "question": "①", "ask": "這一段時間誰把錢吸走了（成交值／法人淨額的族群排名）",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "flow", "seg": "輪動", "ord": 10, "selector": ["#flowRotCard"] }
      ],
      "tests": ["資金流向", "新-資金流向", "資金輪動合併", "批次7"] },

    { "id": "flow.sankey", "name": "資金去向分流圖", "question": "①", "ask": "錢從大盤分到哪幾條產業鏈、鏈裡又分給哪幾個族群",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "overview", "step": 1, "seg": "資金去向", "ord": 20,
          "selector": ["#ovRotCard", "#ovFlowHead", "#ovFlowWrap"],
          "note": "總覽上的簡版（renderOvFlow）。2026-09-26 桌機改用 flowtopo.js 緊湊版 layout:'mini'（和資金流向頁經典光纖第二版同一套視覺，有粒子），手機 ≤820 仍是 ECharts 樹。外殼 #ovRotCard 與輪動時鐘共用，理由見 flow.clock。2026-09-24 說明精簡：圖下註腳 #ovFlowNote 拿掉，口徑搬進足跡輪盤的「?」。" },
        { "page": "flow", "seg": "資金去向", "ord": 20, "selector": ["#flowSankeyCard"] }
      ],
      "tests": ["新-資金流向", "資金去向經典光纖", "資金去向拓撲", "資金去向拓撲-減少動態", "桑基展開與即時", "批次30-兩層下拉與象限卡", "總覽", "總覽右欄", "資金去向v2", "設計系統v2", "載入效能"] },

    { "id": "flow.heat", "name": "資金熱力圖", "question": "①", "ask": "哪些族群現在佔掉最多成交值，而且是在流入還是流出",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "overview", "step": 1, "seg": "熱力圖", "ord": 30, "selector": ["#ovHeatCard"] }
      ],
      "tests": ["總覽", "熱力圖v2", "縮放掃描", "資金熱力圖下拉", "總覽右欄"] },

    { "id": "flow.inst", "name": "族群 × 法人", "question": "①", "ask": "三大法人的錢進了哪些族群（淨買超張數）",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "flow", "seg": "法人", "ord": 30, "selector": ["#flowInstCard"] }
      ],
      "tests": ["新-資金流向", "批次2"] },

    { "id": "flow.conc", "name": "資金集中度", "question": "①", "ask": "錢是集中在少數幾個族群，還是散開了",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "flow", "seg": "集中度", "ord": 40, "selector": ["#flowConcCard"] }
      ],
      "tests": ["新-資金流向", "批次3"] },

    { "id": "market.treemap", "name": "全市場熱力圖", "question": "①", "ask": "整個台股一次看，錢在哪一塊",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "heatmap", "seg": "產業熱力", "ord": 10, "selector": ["#indHeat"] }
      ],
      "tests": ["熱力圖v2", "批次29-產業分頁"] },

    { "id": "theme.heat", "name": "題材熱度", "question": "①", "ask": "哪些題材在吸金（熱度＝資金佔比變化＋法人＋新聞）",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "overview", "step": 1, "seg": "熱門題材", "ord": 40, "selector": ["#ovThemeCard"],
          "note": "2026-09-24 起總覽上是題材熱力圖（renderOvThemes：方塊＝題材成交值、顏色＝熱度，下拉或點方塊換成成分股），放在資金熱力圖正下方。" },
        { "page": "heatmap", "seg": "題材熱力", "ord": 20, "selector": ["#themeMapCard"],
          "note": "2026-09-24 題材併進熱力圖分頁。段名沿用舊的「題材熱力」—— route() 的 prefer 是用段名找段落的。" }
      ],
      "tests": ["題材", "熱力圖v2", "總覽"] },

    { "id": "chain.overview", "name": "族群總覽（長條＋圓餅）", "question": "①", "ask": "這一條產業鏈裡，哪個族群在漲、哪個族群佔掉最多成交值",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "industry", "selector": ["#gpBar", "#gpPie"] }
      ],
      "tests": ["批次29-產業分頁", "產業", "族群頁", "產業R3審查"] },

    { "id": "index.board", "name": "大盤三張圖", "question": "②", "ask": "加權／櫃買／台指期今天怎麼走（含夜盤）",
      "tier": "免費", "law": "🟢",
      "at": [
        { "page": "overview", "step": 2, "seg": "大盤", "ord": 50, "selector": ["#m3"],
          "note": "跟 market.kpi 同一段：三張走勢圖與 KPI 橫條是同一個問題（今天大盤的體質）。2026-09-24 起三張合進一個大方框（#m3Frame），台指期日夜盤自動切。" }
      ],
      "tests": ["大盤三張圖", "新-大盤三張圖", "夜盤真實fixture", "夜盤推送"] },

    { "id": "market.kpi", "name": "大盤 KPI 橫條", "question": "②", "ask": "今天大盤的體質（加權／成交值／漲跌家數／前五族群佔比）",
      "tier": "免費", "law": "🟢",
      "at": [
        { "page": "overview", "step": 2, "seg": "大盤", "ord": 50, "selector": ["#hero"],
          "note": "2026-09-24：六格收成四格（拿掉今日候選、站上 MA20），搬到三張走勢圖上方做成一條 ≤64px 的橫條。2026-09-26：桌機（>640px）整條搬進大盤三張圖的工具列（#m3Kpis，market3.js placeKpi），手機維持原位；選擇器仍是 #hero。" }
      ],
      "tests": ["總覽", "市場明細"] },

    { "id": "market.breadth", "name": "漲跌家數分佈", "question": "②", "ask": "今天是「大家都在漲」還是「少數幾檔撐盤」（依漲跌幅分級的家數直條）",
      "tier": "免費", "law": "🟢",
      "at": [
        { "page": "overview", "step": 2, "seg": "市場寬度", "ord": 60, "selector": ["#ovBreadthCard"] }
      ],
      "tests": ["總覽"] },

    { "id": "market.streak", "name": "法人連續買賣超", "question": "②", "ask": "法人在誰身上連續買或賣、力道在加大還是收手（四象限，投信／外資／合計，門檻可調）",
      "tier": "免費〔推〕", "law": "🟠",
      "at": [
        { "page": "overview", "step": 2, "seg": "法人買超", "ord": 70, "selector": ["#ovTrustCard"] }
      ],
      "tests": ["總覽", "積木-隱性參數"] },

    { "id": "market.detail", "name": "市場明細名單", "question": "②", "ask": "總覽上那幾個數字，完整名單長什麼樣",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "market", "selector": ["#mktSeg2", "#mktBody"] }
      ],
      "tests": ["市場明細", "批次4"] },

    { "id": "season.month", "name": "週期統計", "question": "②", "ask": "這個族群在這個月份，歷史上通常表現如何",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "season", "selector": ["#seasonHeatCard"],
          "note": "週期統計（#season）：2026-09-24 改版拿掉「逐年明細」「本月歷史最強族群」兩張卡之後只剩這一張，一段就沒有分段的意義（miaPager 也會自己收掉），所以不帶 seg、不參與手機分段。" }
      ],
      "tests": ["季節性"] },

    { "id": "stock.fund", "name": "個股基本面與財報", "question": "②", "ask": "這一檔貴不貴、賺不賺錢（本益比／同業分位／ROE／營收 YoY／除權息）",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "stock", "seg": "財報籌碼", "ord": 30, "selector": ["#stockTabs", "#stockTab"],
          "note": "stock.fund／stock.signal／stock.news／broker.views 共用同一個分頁列（#stockTabs）與內容區（#stockTab），手機上是同一段。" }
      ],
      "tests": ["個股", "新-產業與個股", "積木-個股三卡"] },

    { "id": "cand.board", "name": "今日候選", "question": "③", "ask": "今天有哪些標的符合「A 回檔承接／B 突破追進」的條件",
      "tier": "只准免費", "law": "🔴",
      "at": [
        { "page": "market", "selector": ["#mktSeg2"],
          "note": "2026-09-24 總覽的「今日候選」表整張拿掉（Andy），名單只留在市場明細的「今日候選」分頁（#market/cand）。" }
      ],
      "tests": ["總覽", "市場明細", "排序"] },

    { "id": "stock.kchart", "name": "個股 K 線（含即時分 K）", "question": "③", "ask": "這一檔的價格結構現在長什麼樣",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "stock", "seg": "K 線", "ord": 10, "selector": ["#skChartCard"] }
      ],
      "tests": ["個股", "K線縮放", "個股即時分K", "個股R5"] },

    { "id": "stock.mtf", "name": "多週期 SMC 判讀", "question": "③", "ask": "日／週／月多個週期的結構指向同一個方向嗎",
      "tier": "只准免費", "law": "🔴",
      "at": [
        { "page": "stock", "seg": "判讀", "ord": 20, "selector": ["#mtfCard"],
          "note": "簡版個股頁沒有 #mtfCard —— 抓不到的選擇器會被略過，只剩一段就不畫分段列。" }
      ],
      "tests": ["個股"] },

    { "id": "stock.signal", "name": "技術面訊號卡", "question": "③", "ask": "均線／結構／RSI／KD／MACD／乖離／BOS／CHoCH／假跌破 現在各是什麼狀態",
      "tier": "只准免費", "law": "🔴",
      "at": [
        { "page": "stock", "seg": "財報籌碼", "ord": 30, "selector": ["#stockTabs", "#stockTab"],
          "note": "程式在 site/blocks/stock_signal.js（2026-09-24 從 tabOverview 的長字串拆出來）。" }
      ],
      "tests": ["個股", "積木-個股三卡"] },

    { "id": "events.feed", "name": "今日事件", "question": "④", "ask": "今天有什麼新聞／法說／總經事件會讓我不進場",
      "tier": "免費", "law": "🟡",
      "at": [
        { "page": "overview", "step": 4, "seg": "今日事件", "ord": 90, "selector": ["#ovEvents"],
          "note": "桌機是右側抽屜 <aside id=side>；手機抽屜不能同時當一屏的內容，所以用同一份清單在總覽長一張手機專屬卡片 #ovEvents（miaEvents）。桌機上它不存在 —— 驗收只在手機寬度檢查這個選擇器。" }
      ],
      "tests": ["今日事件", "積木-券商觀點"] },

    { "id": "stock.news", "name": "個股新聞與公告", "question": "④", "ask": "這一檔最近有什麼消息",
      "tier": "免費", "law": "🟢",
      "at": [
        { "page": "stock", "seg": "財報籌碼", "ord": 30, "selector": ["#stockTabs", "#stockTab"] }
      ],
      "tests": ["個股", "積木-券商觀點"] },

    { "id": "broker.views", "name": "券商觀點", "question": "④", "ask": "券商對這一檔怎麼看（目標價／評等／調升調降）",
      "tier": "只准免費", "law": "🔴",
      "at": [
        { "page": "stock", "seg": "財報籌碼", "ord": 30, "selector": ["#stockTabs", "#stockTab"],
          "note": "程式在 site/blocks/broker_views.js：一份輸入、一個出口，同時供應個股頁表格與事件抽屜的「券商」分類。法遵 🔴🔴（士林地院 107 金訴 2）。" }
      ],
      "tests": ["積木-券商觀點", "今日事件"] },

    { "id": "chain.map", "name": "產業地圖", "question": "知識", "ask": "台股分成哪幾條產業鏈，各自現在強弱如何",
      "tier": "免費", "law": "🟢",
      "at": [
        { "page": "industry", "selector": ["#indMap", "#chainSwitch"] }
      ],
      "tests": ["產業", "產業鏈導覽"] },

    { "id": "chain.diagram", "name": "產業鏈剖析圖（2D＋3D）", "question": "知識", "ask": "這個產品／製程裡面到底有什麼零件，台廠站在哪幾格",
      "tier": "免費看／399 匯出／799 商用授權", "law": "🟢",
      "at": [
        { "page": "chain", "selector": ["#dgSec", "#prodDiagram"],
          "note": "單一產業鏈頁（#industry/<chain>）刻意不做手機分段（做過，撤回了）：切成「剖析圖／關聯圖」兩段時 390px 從 2561 收到 844px，但把 #relSec 底下的 #segChips、.seglist 收到第二段，「批次29-產業分頁」「產業關係面板」「新-產業與個股」當場變紅（element is not visible）。那些斷言驗的是「窄畫面照樣點得到個股標籤」，是上一批拍板的行為 —— 既有的拍板優先。要真的分段，得先把那三段驗收一起改。所以這一頁的放置都不帶 seg。" }
      ],
      "tests": ["批次6-N1", "批次6-圖九", "批次13-配色與收納", "批次C4-剖析圖窄欄", "3D零件字彙"] },

    { "id": "chain.segments", "name": "環節詳情與分層關聯圖", "question": "知識", "ask": "這一條鏈分成哪幾個環節，每個環節有哪幾檔台股、哪幾家外商，誰依賴誰",
      "tier": "免費看／399 跨鏈搜尋", "law": "🟢",
      "at": [
        { "page": "chain", "selector": ["#relSec", "#segChips", "#chainMap"] },
        { "page": "stock", "seg": "產業鏈", "ord": 40, "selector": ["#indChain"],
          "note": "個股頁上方的鏈條（renderChainStrip），被 industry.js 搬到 #stockPage 後面。" }
      ],
      "tests": ["產業關係面板", "一般電子鏈", "批次6-圖十", "批次C5-關聯圖標籤", "零件誰做的", "新-產業與個股"] },

    { "id": "theme.diagram", "name": "題材剖析圖", "question": "知識", "ask": "這個題材的上游→中游→下游是誰，台廠站在哪一段",
      "tier": "免費看／399 匯出／799 商用授權", "law": "🟢",
      "at": [
        { "page": "heatmap", "seg": "題材細節", "ord": 30, "selector": ["#themeDetail"],
          "note": "從熱力方塊點進來（#heatmap/theme/<id>）時 route() 用 prefer＝「題材細節」直接翻到這一段。" }
      ],
      "tests": ["題材", "題材2D"] }
  ]/*END-MODULES-JSON*/;

  /* 手機分段表（原本手寫在 app.js 的 `MIA_PAGER`）。
     規則：同一頁、同一步、同段名的放置合成一段；選擇器依積木在清單裡的順序取聯集（重複的只留一個）；
     段落依 `ord` 排（相同 ord 保持清單順序）。沒有 `seg` 的放置不參與分段 —— 那些東西永遠顯示，
     這是刻意的失敗方向：資訊架構改錯最貴的後果是「使用者找不到」，所以漏寫只會多顯示。*/
  function pager() {
    var out = {};
    Object.keys(PAGES).forEach(function (page) {
      var segs = [];
      MODULES.forEach(function (m) {
        (m.at || []).forEach(function (p) {
          if (p.page !== page || !p.seg) return;
          var st = p.step || 0, g = null;
          for (var i = 0; i < segs.length; i++) if (segs[i].n === p.seg && segs[i].st === st) { g = segs[i]; break; }
          if (!g) { g = { st: st, n: p.seg, sel: [], ord: p.ord, k: segs.length }; segs.push(g); }
          if (p.ord < g.ord) g.ord = p.ord;
          p.selector.forEach(function (x) { if (g.sel.indexOf(x) < 0) g.sel.push(x); });
        });
      });
      if (!segs.length) return;
      segs.sort(function (a, b) { return (a.ord - b.ord) || (a.k - b.k); });
      out[page] = segs.map(function (g) {
        // 物件形狀跟以前手寫的一模一樣（{ s, n, sel } 或 { n, sel }），miaPager 一行都不用改
        return g.st ? { s: g.st, n: g.n, sel: g.sel } : { n: g.n, sel: g.sel };
      });
    });
    return out;
  }

  function byId(id) {
    for (var i = 0; i < MODULES.length; i++) if (MODULES[i].id === id) return MODULES[i];
    return null;
  }

  window.TwModules = { list: MODULES, pages: PAGES, pager: pager, byId: byId };
})();
