// 版本標記（2026-11-15）：左下角小字，讓擁有者一眼看出瀏覽器拿到的是不是最新版。
// 每次推預覽前更新 BUILD（提交代號＋台北時間）。這支檔不被其他程式依賴，載入失敗也不影響辦公室。
(function () {
  var BUILD = '761b6cb3・11月16日 17:18';
  function show() {
    if (document.getElementById('aoBuild')) return;
    var el = document.createElement('div');
    el.id = 'aoBuild';
    el.textContent = '版本 ' + BUILD;
    el.setAttribute('aria-label', '辦公室版本 ' + BUILD);
    el.style.cssText = 'position:fixed;left:8px;bottom:6px;z-index:5;font:11px/1.4 system-ui,sans-serif;color:rgba(60,48,40,.62);background:rgba(255,250,242,.7);padding:1px 7px;border-radius:8px;pointer-events:none;user-select:none';
    document.body.appendChild(el);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show); else show();
})();
