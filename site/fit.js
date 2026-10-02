/* ==================================================================================
   一屏看完（2026-10-03，分支 claude/fit-screen，DECISIONS #306）

   Andy 原話：「版面上下太大，希望是一個電腦螢幕大小可看到完整圖表，幫我上下寬度調整窄一點適當」。
   規格：每張圖表卡（含標題列與控制列）完整落在一屏可視高度內 —— 1920×1080 瀏覽器可視高約 950、1440×900 約 800。

   這支只做一件事：告訴各張圖「你在卡裡面最多可以多高」。它不畫任何東西、不碰路由與側欄。
     Fit.desk()          桌機（≥821px）才套用；手機（≤820）完全不動
     Fit.cap()           一張卡最高多少 px ＝ 視窗高 − 跳轉列 49 − 上下邊距各 12（跳轉列黏在最上面，卡片捲到頂時只剩視窗高 − 49 可看）
     Fit.room(el, opt)   el 在「它的那張 .card」裡最高可以多高（卡高上限 − 卡裡面除了 el 以外的東西）
                           opt.mode 'total'（預設）＝ 卡高 − el 高 ＝ 卡裡 el 以外全部佔的高度
                                    'above'＝ el 上緣到卡上緣 ＋ 卡的下內距（卡裡 el 旁邊還有別欄比較高時用，例如輪盤旁邊的排行）
                           opt.min   下限（再窄圖就沒法看了，寧可卡超出一點）
                           opt.below 'above' 模式下，el 下面還有多少 px 的別的東西
     Fit.on(fn[, el])    視窗尺寸變了（去抖動 150ms）就呼叫 fn；給 el 時，el 所在那張卡的高度變了也呼叫；回傳取消函式。
                           各張圖的「高度＝算出來的」，所以視窗高度變了（F11、縮放視窗）要自己重算 ——
                           ECharts 的 ResizeObserver 只看容器，容器沒變就不會重算。
   ⚠ 只有「高度」跟著視窗走；寬度仍然是原本的欄寬，所以改動只出現在「卡原本比一屏高」的那幾張，
     矮於一屏的卡（熱力圖、市場明細、自選……）一個 px 都不變。
   ================================================================================== */
(function () {
  'use strict';
  var DESK = 821;
  var BAR_FALLBACK = 49;     // 跳轉列高（layout4.css：32 按鈕 ＋ 上下內距 8×2 ＋ 1 框線）
  var MARGIN = 24;           // 卡片上緣與下緣各留 12
  var subs = [];

  function desk() { return window.innerWidth >= DESK; }
  function bar() {
    var j = document.getElementById('l4Jump');
    return (j && !j.hidden && j.offsetHeight) || BAR_FALLBACK;
  }
  function cap() { return Math.max(480, window.innerHeight - bar() - MARGIN); }

  function room(el, opt) {
    opt = opt || {};
    var min = opt.min || 0;
    if (!el || !desk()) return Infinity;
    var card = el.closest ? el.closest('.card') : null;
    if (!card) return Infinity;
    var cr = card.getBoundingClientRect(), er = el.getBoundingClientRect();
    if (!(cr.height > 0) || !(er.height >= 0)) return Infinity;
    var chrome;
    if (opt.mode === 'above') {
      var cs = getComputedStyle(card);
      chrome = (er.top - cr.top) + (parseFloat(cs.paddingBottom) || 0) + (parseFloat(cs.borderBottomWidth) || 0) + (opt.below || 0);
    } else {
      chrome = cr.height - er.height;
    }
    return Math.max(min, Math.floor(cap() - chrome));
  }

  var lastW = window.innerWidth, lastH = window.innerHeight, timer = 0;
  window.addEventListener('resize', function () {
    if (window.innerWidth === lastW && window.innerHeight === lastH) return;
    lastW = window.innerWidth; lastH = window.innerHeight;
    clearTimeout(timer);
    timer = setTimeout(function () {
      subs.slice().forEach(function (fn) { try { fn(); } catch (e) { /* 一張圖壞了不要拖累其他張 */ } });
    }, 150);
  });
  /* Fit.on(fn)      ：視窗尺寸變了才呼叫 fn。
     Fit.on(fn, el)  ：另外盯著 el 所在的那張 .card —— 卡的高度變了（控制列晚一步長出來、說明展開、換篩選）也呼叫 fn。
                       為什麼要盯卡：el 的高度是「卡高上限 − 卡裡其他東西」算出來的，其他東西晚一步才出現時，
                       第一次算的值就偏大，卡會超出一屏；ECharts／Canvas 的 ResizeObserver 只看容器本身，不會醒。
                       fn 必須是「重算並套用」（冪等）：套用後卡高又變一次，fn 再算出同一個值就收斂。 */
  function on(fn, el) {
    subs.push(fn);
    var ro = null, t = 0;
    var card = el && el.closest ? el.closest('.card') : null;
    if (card && typeof ResizeObserver !== 'undefined') {
      var last = Math.round(card.getBoundingClientRect().height);
      ro = new ResizeObserver(function () {
        var h = Math.round(card.getBoundingClientRect().height);
        if (Math.abs(h - last) < 2) return;
        last = h;
        clearTimeout(t);
        t = setTimeout(function () { try { fn(); } catch (e) { /* 一張圖壞了不要拖累其他張 */ } }, 80);
      });
      ro.observe(card);
    }
    return function () {
      var i = subs.indexOf(fn); if (i >= 0) subs.splice(i, 1);
      if (ro) ro.disconnect(); clearTimeout(t);
    };
  }

  window.Fit = { desk: desk, cap: cap, room: room, on: on };
})();
