/* ============================================================================
   全站「只開放文章」模式（site/site_mode.js，2026-11-26）
   ----------------------------------------------------------------------------
   Andy 11-26：「整站切成『只開放文章』模式」「只有對應的該頻道文章」。
   背景：手機版還沒做完，暫時不讓一般人用網站工具，只開放精選文章。

   ★ 總開關在下面 articlesOnly：true＝只開放文章、false＝完整網站。要切換就改這個值、推 main
     （原本想存伺服器端設定；現成的伺服器設定只有側欄隱藏清單，語意是「隱藏哪些」，硬塞一個反向開關會讓 Worker 的檢查對不上，
      所以先用設定檔。改一個字、部署約 3 分鐘生效）。

   開啟時：
     · 非站主：任何路由（含直接打 #overview、#flow、#stock/2330、空網址）一律導到 #articles；
       左側選單與手機抽屜只剩「精選文章」，搜尋代號、盤中即時列、客服以外的工具入口全部藏起來。
       放行的路由：articles／article（精選文章）、pricing／notices／support（訂閱、公告、客服）、
       terms／privacy／disclaimer／refund／data-deletion／leave（法律頁）。會員登入、註冊、客服鈕照常。
     · 精選文章裡只顯示站主已開眼睛（公開）的頻道分頁與其文章 —— 這是 articles.js 本來就有的規則，這裡不動它。
     · 站主：完整網站照舊，頁首多一條小標「文章模式中（一般人只看得到文章）」，
       旁邊有「以一般人視角預覽」鈕（只改這個瀏覽器、存 sessionStorage，關分頁就回來）。
   ⚠ 這只是畫面層的收斂，不是資料保護：JSON、API 本來就是公開讀取／各有權限閘，沒有改變。
   ============================================================================ */
window.TW_SITE_MODE = {
  articlesOnly: true,   // ★ 要恢復完整網站就改 false
};

(function () {
  'use strict';
  var C = window.TW_SITE_MODE || {};
  if (window.TW_SITE_MODE_OFF) C.articlesOnly = false;   // 驗收腳本專用（_uitest／_preview 在頁面腳本之前設好），一般瀏覽器不會有這個變數
  var root = document.documentElement;
  var PV_KEY = 'tw.artonly.pv';
  /* 放行的路由第一段（其餘一律導去 #articles） */
  var ALLOW = ['articles', 'article', 'pricing', 'notices', 'support', 'terms', 'privacy', 'privacy-promo', 'disclaimer', 'refund', 'data-deletion', 'leave'];

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function ssGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function ssSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* 私密視窗：略 */ } }
  function ssDel(k) { try { sessionStorage.removeItem(k); } catch (e) { /* 略 */ } }

  /* 站主嗎：account.js 載入後問它；之前先讀它存的登入快取（同一份 localStorage），這樣站主第一眼就不會被導走 */
  var settled = false;   // 持權杖但沒有登入快取時，等帳號資料回來（最多 3 秒）才判定身分，免得站主第一次載入被誤導走
  function pending() {
    if (settled || !hasTok()) return false;
    try { var A = window.TwAccount; if ((A && A.user && A.user()) || JSON.parse(lsGet('tw.acct.user') || 'null')) return false; } catch (e) { /* 當作還在等 */ }
    return true;
  }
  function isAdmin() {
    try {
      var A = window.TwAccount;
      if (A && A.user) { var u = A.user(); if (u) return !!u.admin; if (!hasTok()) return false; }
      if (!hasTok()) return false;
      var c = JSON.parse(lsGet('tw.acct.user') || 'null');
      return !!(c && c.admin);
    } catch (e) { return false; }
  }
  function hasTok() { return !!lsGet('tw.acct.tok'); }
  function preview() { return ssGet(PV_KEY) === '1'; }
  /* 這個人現在看到的是「只有文章」嗎 */
  function active() { return !!C.articlesOnly && !pending() && (!isAdmin() || preview()); }

  function headOf() { return decodeURIComponent((location.hash || '').replace(/^#\/?/, '').split('/')[0].split('?')[0] || ''); }
  function guard() {
    if (!active()) return false;
    var h = headOf();
    if (h && ALLOW.indexOf(h) >= 0) return false;
    location.replace('#articles');
    return true;
  }

  function paint() {
    var on = active();
    root.classList.toggle('artonly', on);
    root.classList.toggle('artonly-adm', !!C.articlesOnly && isAdmin() && !on);
    banner();
    if (on) guard();
  }

  /* ---------------- 樣式：只留「精選文章」 ---------------- */
  function css() {
    if (document.getElementById('siteModeCss')) return;
    var s = document.createElement('style'); s.id = 'siteModeCss';
    s.textContent =
      /* 電腦版側欄：大項只留精選文章；組標題、其他子項全藏（精選文章自己的頻道子項屬於它的 data-parent） */
      'html.artonly #tabs .tab:not([data-view="articles"]){display:none!important}' +
      'html.artonly #tabs .l4grp{display:none!important}' +
      'html.artonly #tabs .l4subtab:not([data-parent="articles"]){display:none!important}' +
      /* 手機抽屜：只留精選文章那一列；組標題與其他列藏起來 */
      'html.artonly .m4item[data-v]:not([data-v="articles"]){display:none!important}' +
      'html.artonly .m4grp:not(:has(.m4item[data-v="articles"])) {display:none!important}' +
      'html.artonly .m4gt{display:none!important}' +
      /* 頂欄：搜尋代號、盤中即時列、工具入口 */
      'html.artonly .search,html.artonly #liveBar,html.artonly #liveStat,html.artonly .live,html.artonly #tourBtn,html.artonly .howto,html.artonly #evToggle,html.artonly #twPageTourBtn,html.artonly button#twPageTourBtn,:root.m4.artonly #twPageTourBtn,:root.m4.artonly .m4tools #twPageTourBtn,html.artonly #twTourBtn,html.artonly #m4Search,html.artonly #evDrawer{display:none!important}' +
      /* 站主頁首小標 */
      '#siteModeBar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0;padding:6px 16px;font-size:12.5px;line-height:1.5;background:color-mix(in srgb,var(--amber,#f5a524) 18%,var(--panel,#111));color:var(--ink,#eee);border-bottom:1px solid color-mix(in srgb,var(--amber,#f5a524) 45%,transparent)}' +
      '#siteModeBar b{font-weight:700}' +
      '#siteModeBar button{font:inherit;font-size:12px;min-height:28px;padding:2px 12px;border-radius:999px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer}' +
      '#siteModeBar button:hover{background:color-mix(in srgb,currentColor 14%,transparent)}';
    document.head.appendChild(s);
  }

  /* ---------------- 站主小標＋預覽鈕 ---------------- */
  function banner() {
    var adm = !!C.articlesOnly && isAdmin();
    var bar = document.getElementById('siteModeBar');
    if (!adm) { if (bar) bar.remove(); return; }
    var pv = preview();
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'siteModeBar'; bar.setAttribute('role', 'status');
      var host = document.body; host.insertBefore(bar, host.firstChild);
      bar.addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('button'); if (!b) return;
        if (preview()) { ssDel(PV_KEY); } else { ssSet(PV_KEY, '1'); }
        paint();
        if (preview()) guard();
        window.dispatchEvent(new Event('tw:navhide'));
      });
    }
    bar.innerHTML = '<b>文章模式中</b><span>（一般人只看得到文章' + (pv ? '；你正在用一般人視角預覽' : '') + '）</span>' +
      '<button type="button" id="siteModePv" aria-pressed="' + (pv ? 'true' : 'false') + '">' + (pv ? '回到站主視角' : '以一般人視角預覽') + '</button>' +
      '<span style="opacity:.75">關閉文章模式：把 site/site_mode.js 的 articlesOnly 改成 false、推 main</span>';
  }

  function boot() { css(); paint(); }
  /* 先在最早的時間點決定一次（還沒畫任何東西）：沒登入記號的訪客一進站就直接落在 #articles，不會先閃一下總覽 */
  if (C.articlesOnly && !hasTok() && !preview()) { root.classList.add('artonly'); guard(); }
  window.addEventListener('hashchange', function () { guard(); });
  ['tw:account', 'tw:account-config'].forEach(function (ev) { window.addEventListener(ev, function () { try { var A = window.TwAccount; if (A && A.user && A.user()) settled = true; } catch (e) { /* 等 3 秒保底 */ } paint(); }); });
  window.TwSiteMode = { active: active, paint: paint, allow: ALLOW.slice(), articlesOnly: function () { return !!C.articlesOnly; } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  /* 登入快取還沒被確認前，持有權杖的人可能是站主：3 秒後若仍不是站主就補一次守門 */
  if (hasTok()) setTimeout(function () { settled = true; paint(); }, 3000);
})();
