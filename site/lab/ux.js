/* ============================================================================
   交易練習室「呈現層」補強（2026-10-30，Andy：「版面、策略、介面所有都需要優化，更符合人性」）
   只做畫面：不碰回測引擎、不碰策略邏輯。目前一件事：
   · 自訂策略還沒選／沒存任何策略時，右側空白處改成「範本卡片」，一點就把範本載進編輯器
     （直接代點原本的「從範本開始」下拉，邏輯仍在 custom.js）。
   所有文字用 esc 輸出，不收 HTML。
   ========================================================================== */
(function () {
  'use strict';
  const root = document.getElementById('v-lab');
  if (!root) return;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function enhance() {
    const mxb = root.querySelector('.cu-mxrow #labMx');   // 手機：入口名稱講清楚匯入、匯出在裡面
    if (mxb && mxb.textContent === '我的策略・範本') mxb.textContent = '我的策略・範本・匯入匯出';
    const ed = root.querySelector('#cuEd'), sel = root.querySelector('#cuTpl');
    if (!ed || !sel || ed.querySelector('.cu-start')) return;
    const note = ed.querySelector('.lab-note');
    if (!note || ed.children.length !== 1 || !/選一個策略/.test(note.textContent)) return;
    const opts = Array.from(sel.options).filter((o) => o.value !== '');
    if (!opts.length) return;
    ed.innerHTML = '<div class="cu-start"><div class="cu-st-h">挑一個範本開始</div><div class="cu-cards">' +
      opts.map((o) => '<button type="button" class="cu-card" data-v="' + esc(o.value) + '">' + esc(o.text) + '</button>').join('') +
      '</div><div class="cu-st-f"><button type="button" class="lab-gear" data-cu-new>空白新增</button></div></div>';
  }
  new MutationObserver(enhance).observe(root, { childList: true, subtree: true });
  root.addEventListener('click', (e) => {
    const t = e.target.closest && e.target.closest('.cu-card,[data-cu-new]'); if (!t) return;
    if (t.hasAttribute('data-cu-new')) { const n = root.querySelector('#cuNew'); if (n) n.click(); return; }
    const sel = root.querySelector('#cuTpl'); if (!sel) return;
    sel.value = t.dataset.v; sel.dispatchEvent(new Event('change', { bubbles: true }));
  });
  enhance();
}());
