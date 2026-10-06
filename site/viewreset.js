/* 重新整理＝圖表設定回預設（DECISIONS #307，2026-10-03）。
 *
 * Andy：「需要新增一個功能，當重新整理後，全部圖表設定回 Default」。
 *
 * 為什麼用「載入時清掉」而不是把每個設定改存記憶體：
 *   全站有七十幾個「圖表檢視設定」散在 15 支檔案裡（區間鈕、週期、指標開關、線寬、2D/3D、動畫、
 *   篩選、腳印、分頁籤、AI 面板寬度…），而且很多模組**換頁重畫時會重新去 localStorage 讀一次**
 *   （例如換一檔股票，籌碼區間鈕是從 tw.chipWin 讀回來的）。逐一改成記憶體變數要動幾十個地方，
 *   也會把「同一次瀏覽中切頁仍保留設定」弄丟。
 *   所以做法是：設定照舊寫 localStorage（同一次瀏覽切頁、換股票都還在），
 *   **只有整頁載入（重新整理、重新打開網站）的那一刻**，這支在所有程式之前把「檢視設定」類的鍵刪掉，
 *   後面的程式讀不到 → 一律走各自的預設值。hash 換頁不會重新載入，所以不受影響。
 *
 * ★ 分類原則（Andy 交代：偏向「保留使用者建立的內容，重設檢視狀態」）：
 *   保留：登入與帳號、會員權限快取、自選清單、深淺主題與外觀（風格、側欄收合、剖析圖配色）、
 *         K 線上的手繪物件與畫筆樣式、即時開關（含每張卡的即時開關）、同意條款／導覽看過、
 *         最近搜尋、資料快取（5 秒 K、夜盤報價點、大盤分時快取）。
 *   重設：其他所有「怎麼看這張圖」的選擇。
 *   沒有被列進任何一邊的鍵**預設保留**（寧可少清，不可誤刪使用者的東西）；
 *   `scripts/_uitest.py` 的「重新整理回預設1003」會掃全站原始碼裡每個 'tw.' 鍵，
 *   沒被分類就紅燈 —— 以後新增設定的人一定得在這裡決定它屬於哪一邊。
 *
 * ★ 預覽版（`preview/<名稱>/`）：preview_boot.js 比這支更早把 localStorage 換成加前綴的殼
 *   （實際鍵是 `twpv:<名稱>:<原鍵>`），這支透過殼列舉與刪除，所以只會清到**那份預覽自己的**檢視設定；
 *   正式站的鍵它看不到也碰不到。反過來，正式站列舉到的 `twpv:...` 鍵不符合任何規則 → 保留，不會誤清預覽的。
 *
 * 驗收用的後門：`window.TW_KEEP_VIEW === true` 時不清（只有 _uitest.py 的開機腳本會設，
 * 讓幾百段「先寫 localStorage 再重新整理」來布置情境的既有驗收照舊能布置）。正式程式沒有任何地方設它。
 */
(function () {
  'use strict';

  /* 保留：完全相同的鍵 */
  var KEEP = [
    'tw.theme', 'tw.theme4', 'tw.layout4.nav', 'tw.dg3d.pal',          // 主題與外觀
    'tw.acct.tok', 'tw.acct.user', 'tw.acct.n', 'tw.sess', 'tw.perm',  // 登入、帳號、權限（tw.acct.n／tw.sess 在 sessionStorage）
    'tw.watch', 'tw.watchlists', 'tw.watchlists.u', 'tw.watchcur',     // 自選清單（含目前在第幾頁）
    'tw.draw.style',                                                   // 畫筆樣式（手繪物件本身見下面前綴）
    'tw.consent', 'tw.tour',                                           // 同意條款、新手導覽看過
    'tw.live.proxy', 'tw.live.on', 'tw.sse',                           // 即時來源與開關
    'tw.m3.nightpts', 'tw.m3.futsym',                                  // 資料快取（夜盤報價點、近月合約代號）
    'tw.search.recent',                                                // 最近搜尋
    'tw.notice.banner', 'tw.notice.read',                              // 通知：橫幅關過、哪些讀過（使用者自己的紀錄，不是檢視狀態）
    'tw.quota', 'tw.quota.tab'                                         // 用量計數與分頁識別（資料，tw.quota.tab 在 sessionStorage）
  ];
  /* 保留：前綴 */
  var KEEP_PREFIX = [
    'tw.layout4.',     // 版面 V2 的側欄收合等外觀偏好（tw.layout4.nav 與以後同族的鍵）
    'tw.tabs.',        // 分頁拖曳排過的「順序」（tabdrag.js，DECISIONS #330：順序是使用者設定、保留；「選中哪一個」另算、不存、重新整理回預設）
    'tw.draw.',        // 手繪物件 tw.draw.<代號>.<週期>
    'tw.live.card.',   // 每張卡自己的即時開關
    'tw.livek.',       // 當天收集到的 5 秒序列（資料，不是設定）
    'm3.last.'         // 大盤分時的當天快取（資料）
  ];
  /* 重設：完全相同的鍵 */
  var RESET = [
    'tw.aiSplit', 'tw.aiTab', 'tw.ovAiTab',                            // 個股 AI 面板：分隔線寬、分頁籤
    'tw.aiOpen', 'tw.aiOpenV',                                         // #305 拿掉「展開」後已不讀寫：列在這裡＝把舊瀏覽器留下的值清掉
    'tw.indView',                                                      // 產業地圖「地圖／清單」（預覽分支 claude/industry-map-v2 的新鍵，先分好）
    'tw.candGroups', 'tw.udMkt', 'tw.hmGroup', 'tw.themeColor',        // 篩選與熱力圖分組／配色依據
    'tw.chainFold', 'tw.segExpand', 'tw.relOpen', 'tw.relView',        // 產業鏈／關聯圖的收合展開
    'tw.dgOpen', 'tw.dgPartOpen', 'tw.dganim',                         // 剖析圖：展開、零件卡、動畫
    'tw.dg3d', 'tw.dg3d.drag', 'tw.dg3d.exp',                          // 2D/3D、3D 拖曳模式、爆炸圖展開
    'tw.flowtopo.motion',                                              // 資金去向動畫
    'tw.chipWin', 'tw.chipWinHo', 'tw.hoLines', 'tw.instSeg', 'tw.mgSeg',              // 籌碼分頁：區間、線、分段
    'tw.inst.days', 'tw.inst.to', 'tw.inst.end', 'tw.conc.ma',                       // 法人與集中度的天數／均線勾選
    'tw.revView', 'tw.revWin', 'tw.profitMode', 'tw.periver',          // 營收／獲利／本益比河流圖
    'tw.pe.len', 'tw.pe.end', 'tw.peLineW', 'tw.ms.years',             // 本益比區間、線寬、季節性年數
    'tw.drawbar',                                                      // 繪圖工具列顯示（畫好的線保留）
    'tw.explore.cat',                                                  // 選股策略分類籤（2026-10-06 普查補分類）
    'tw.footDetail',                                                   // 頁尾詳細規範展開：2026-10-06 Andy 要一律收合，已不讀寫，清掉舊值
    'tw.kwide', 'tw.side'                                              // 舊版版面鍵（早就沒人讀，順手清）
  ];
  /* 重設：前綴（KEEP 先比，所以 tw.m3.nightpts 這類資料快取不會被這裡吃掉） */
  var RESET_PREFIX = [
    'tw.m3.',          // 大盤三張圖（線/K、週期、放大、量副圖比例、剖析圖縮放）＋手機版各頁的分段／分頁
    'tw.mia.',         // 手機版「目前看第幾段」
    'tw.rot.',         // 輪動時鐘：天數、腳印、水波、掃描、篩選
    'tw.sankey.',      // 桑基日期滑桿
    'tw.season.',      // 季節性：檢視、列數、顯示數字
    'tw.etf.'          // ETF 頁：分類、期間、熱門依據、報酬口徑、比較勾選（2026-10-06 普查補分類）
  ];
  /* tw.kcfg（K 線指標設定）是一包 JSON：指標開關、參數、線寬、顏色、K 棒寬、週期勾選全部重設，
     只留使用者自己新增的自訂週期（tfs，例如「3 日」「2 週」）—— 那是他建立的東西，不是檢視狀態。*/
  var KCFG = 'tw.kcfg', KCFG_KEEP = ['tfs'];

  function startsAny(k, arr) { for (var i = 0; i < arr.length; i++) if (k.indexOf(arr[i]) === 0) return true; return false; }
  /** 'keep' | 'reset' | 'kcfg' | null（沒分類＝保留） */
  function classify(k) {
    k = String(k || '');
    if (k === KCFG) return 'kcfg';
    if (KEEP.indexOf(k) >= 0 || startsAny(k, KEEP_PREFIX)) return 'keep';
    if (RESET.indexOf(k) >= 0 || startsAny(k, RESET_PREFIX)) return 'reset';
    return null;
  }

  var cleared = [];
  function resetNow(ls) {
    var keys = [], i, k;
    // 先抄一份鍵名再刪：邊列舉邊刪，索引會跳號
    for (i = 0; i < ls.length; i++) { k = ls.key(i); if (k != null) keys.push(k); }
    for (i = 0; i < keys.length; i++) {
      k = keys[i];
      var c = classify(k);
      if (c === 'reset') { ls.removeItem(k); cleared.push(k); }
      else if (c === 'kcfg') {
        var keep = null;
        try {
          var o = JSON.parse(ls.getItem(k) || 'null');
          if (o && typeof o === 'object') {
            KCFG_KEEP.forEach(function (f) {
              if (Array.isArray(o[f]) && o[f].length) { keep = keep || {}; keep[f] = o[f]; }
            });
          }
        } catch (e) { /* 壞掉的 JSON：整包清掉 */ }
        if (keep) ls.setItem(k, JSON.stringify(keep)); else ls.removeItem(k);
        cleared.push(k);
      }
    }
  }

  var skipped = window.TW_KEEP_VIEW === true;
  if (!skipped) {
    try { resetNow(window.localStorage); } catch (e) { /* 私密視窗讀不到 localStorage：本來就不會記任何設定 */ }
  }

  window.TwView = {
    KEEP: KEEP, KEEP_PREFIX: KEEP_PREFIX, RESET: RESET, RESET_PREFIX: RESET_PREFIX, KCFG_KEEP: KCFG_KEEP,
    classify: classify,
    cleared: cleared,     // 這次載入清掉了哪些鍵（驗收讀）
    skipped: skipped      // 這次載入有沒有因為驗收後門而跳過
  };
})();
