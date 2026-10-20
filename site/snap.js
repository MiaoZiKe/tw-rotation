/* snap.js — 自動截圖用的「目標標記」與「就緒判斷」（Andy 2026-10-20：熱力圖等是「需要截圖發布的內容」）
 *
 * 另一組人用 Playwright 截圖發文：他們要的是「截哪一塊」與「那一塊畫完了沒」。
 * 這支只做這兩件事，**不碰任何圖的畫法**：
 *   ① 把每個截圖目標標上 data-snap="<名稱>"（用選擇器對照表 + MutationObserver，各頁重畫後自動補回，
 *      不必逐頁改 render）。名稱清單與選擇器見 docs/social_snap_targets.md。
 *   ② window.TwSnapReady(name) → true/false：該目標「已經畫完、而且即時資料（若適用）已套上」。
 *      判斷：目標在畫面上、裡面有畫好的 canvas／svg（或表格列）、沒有 .isempty，
 *      而且 data-snap-live 不是 pending（pending＝站主開著即時、盤中、還沒輪完一圈；
 *      live＝已套上、close＝收盤資料、err＝抓不到或等超過 60 秒 —— 後兩者視為「已就緒」，截到什麼就是什麼）。
 *   ③ window.TwSnapList() → 目前頁面上找得到的目標名稱（給截圖程式確認路由對了）。
 * 即時只給站主或管理員（livegate.js）；訪客截到的永遠是收盤資料，data-snap-live 一律 close。
 */
(function () {
  'use strict';
  var MAP = {
    'heat-overview': '#ovHeatCard',           // 總覽 #overview：資金熱力圖
    'heat-ovtheme': '#ovThemeCard',           // 總覽 #overview：熱門題材熱力圖
    'heat-industry': '[data-hlcard="ind"]',          // 熱力圖頁 #heatmap/industry：整個台股一次看
    'heat-theme': '#themeMapCard',            // 熱力圖頁 #heatmap/theme：題材資金熱力
    'rot-wheel': '#rotClock::.card',          // 資金流向 #flow：資金輪盤（含右邊族群資金排行長條圖，同一張卡）
    'rot-wheel-mini': '#ovRotCard',           // 總覽：迷你資金輪盤
    'flow-tree': '#flowSankeyCard',           // 資金流向 #flow：資金分流樹（含右側資金流向排名）
    'flow-tree-ov': '#ovFlowCard',            // 總覽：昨日資金分流樹
    'market-streak': '#streakSub::.card',     // 市場明細 #market/streak：法人連續買賣超
    'rotation-wheel': '#rotClockWrap',        // 資金流向 #flow/rotation：輪盤圖本體（不含標題列與控制項）
    'rotation-rank': '#rankFlowWrap',         // 同頁：族群資金排行長條圖本體
    'sankey-tree': '#sankeyWrap',             // #flow/sankey：資金分流樹圖本體（不含右側排名與控制項）
    'heat-season': '#seasonHeatCard'          // 季節性 #season：月度報酬熱力（歷史資料，沒有即時）
  };
  function find(name) {
    var sel = MAP[name]; if (!sel) return null;
    var p = sel.split('::'), el = document.querySelector(p[0]);
    if (el && p[1]) el = el.closest(p[1]);
    return el || null;
  }
  function mark() {
    Object.keys(MAP).forEach(function (n) { var el = find(n); if (el && el.getAttribute('data-snap') !== n) el.setAttribute('data-snap', n); });
  }
  function visible(el) { var r = el.getBoundingClientRect(); return !!el.getClientRects().length && r.width > 20 && r.height > 20; }
  function ready(name) {
    mark();
    var el = document.querySelector('[data-snap="' + name + '"]');
    if (!el || !visible(el)) return false;
    var drawn = Array.prototype.some.call(el.querySelectorAll('canvas,svg'), function (n) {
      if (n.closest('.howbtn,button')) return false; var r = n.getBoundingClientRect(); return r.width > 40 && r.height > 40; })
      || el.querySelectorAll('a[href^="#stock/"], table tbody tr, .skrank li, .rankrow').length >= 3;   // 清單型（法人連續買賣超）：至少 3 列才算畫好
    // 法人連續買賣超是文字清單（排行）或四象限圖：清單模式沒有 canvas，量文字長度（載入中時只有標題列，遠小於 150 字）
    if (!drawn && !(name === 'market-streak' && (el.innerText || '').replace(/\s/g, '').length > 150)) return false;
    if (el.querySelector('.isempty')) return false;
    var host = el.closest('[data-snap-live]');      // 圖本體目標沒有自己的旗標，看所在卡片的
    return (el.getAttribute('data-snap-live') || (host && host.getAttribute('data-snap-live'))) !== 'pending';
  }
  window.TwSnapReady = ready;
  window.TwSnapList = function () { mark(); return Object.keys(MAP).filter(function (n) { return !!document.querySelector('[data-snap="' + n + '"]'); }); };
  var t = null;
  function later() { if (t) return; t = setTimeout(function () { t = null; mark(); }, 200); }
  try { new MutationObserver(later).observe(document.documentElement, { childList: true, subtree: true }); } catch (e) { /* 舊瀏覽器 */ }
  window.addEventListener('hashchange', later);
  document.addEventListener('DOMContentLoaded', mark);
})();
