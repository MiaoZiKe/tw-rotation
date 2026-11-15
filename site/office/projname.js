// 專案名稱的共用小工具（入口頁 entry.js 與辦公室頁 world/js/live.js 共用，所以放在 window.AIOProj）。
// 為什麼要有：雲端工作階段沒掛儲存庫時，工作目錄是 /home/user，外掛送來的專案名就是「user」，
//   「user」「root」「tmp」這種名字對人沒有意義，統一顯示成「雲端工作階段」，名牌寫「雲端工作階段 CEO」。
(function () {
  'use strict';
  var NONAME = /^(user|users|root|home|tmp|temp|workspace|workspaces|work|mnt|opt|var|app|runner|ubuntu|admin|sandbox|project|projects|repo|repos|src|code|dev|data|claude)$/i;
  var CLOUD = '雲端工作階段';
  function label(name) { var t = String(name == null ? '' : name).replace(/\s+/g, ' ').trim(); return !t || NONAME.test(t) ? CLOUD : t; }
  function trunc(s, n) { var a = Array.from(String(s)); return a.length > n ? a.slice(0, n - 1).join('') + '…' : String(s); }
  function ago(ms, now) {
    if (!ms) return '還沒有活動';
    var d = Math.max(0, (now || Date.now()) - ms), m = Math.floor(d / 60000);
    if (m < 1) return '剛剛';
    if (m < 60) return m + ' 分鐘前';
    var h = Math.floor(m / 60); if (h < 24) return h + ' 小時前';
    return Math.floor(h / 24) + ' 天前';
  }
  window.AIOProj = { label: label, trunc: trunc, ago: ago, CLOUD: CLOUD, isCloud: function (n) { return label(n) === CLOUD; } };
})();
