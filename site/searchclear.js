/* 全站搜尋框「清除」小工具（2026-11-01 Andy：「全站搜尋清單也加清除鈕」）
 * 為什麼做成一支共用的：搜尋框散在十幾個檔案、而且常被 innerHTML 整塊重畫，每處各寫一套會漏、也會不一致。
 * 做法：用 MutationObserver 盯著整頁，凡是 input[type=search]、側欄的 #q、族群搜尋 #cgSearch，
 *   一律在「該 input 後面」補一顆絕對定位的 ×（不包 wrapper、不改既有版面，桌機版面指紋不變）。
 *   有字才顯示；按下去清空、發 input／change 事件讓各處原本的篩選邏輯自己恢復全部清單、焦點留在框內；Esc 也清空。
 * 不要掛的地方：etfpage.js 已有自己的 .srchw ×（另一位設計美編負責）→ 用 .srchw 或 data-sc-skip 排除。
 */
(function () {
  'use strict';
  if (window.TwSearchClear) return;
  var SEL = 'input[type=search], #q, #cgSearch';
  var SKIP = '.srchw, [data-sc-skip]';

  // 樣式跟著 JS 走：深淺主題都用既有 token（--ink-3 / --panel / --line-2），手機 ≤640 放大到 32px
  var st = document.createElement('style');
  st.textContent = '.scx{position:absolute;z-index:3;display:flex;align-items:center;justify-content:center;padding:0;margin:0;border:0;border-radius:50%;'
    + 'background:var(--panel-3,rgba(128,128,128,.18));color:var(--ink-2,#888);font:700 17px/1 var(--sans,system-ui);cursor:pointer}'
    + '.scx[hidden]{display:none}.scx:hover,.scx:focus-visible{background:var(--line-2,rgba(128,128,128,.4));color:var(--ink,#fff);outline:none}'
    + 'input.sc-has{padding-right:36px!important}'
    + 'input.sc-has::-webkit-search-cancel-button{-webkit-appearance:none;display:none}';
  document.head.appendChild(st);
  var list = [];   // 已掛上的 input

  function esc(e) { return e && e.nodeType === 1; }

  function place(inp) {
    var b = inp._scb; if (!b) return;
    var has = !!inp.value, vis = !!inp.offsetParent && inp.offsetWidth > 40;
    if (!has || !vis) { b.hidden = true; inp.classList.remove('sc-has'); return; }
    inp.classList.add('sc-has');
    b.hidden = false;
    var h = inp.offsetHeight, size = Math.min(Math.max(h - 6, 24), 32);
    if (window.matchMedia && matchMedia('(max-width:640px)').matches) size = Math.max(size, 32);
    b.style.width = b.style.height = size + 'px';
    b.style.left = (inp.offsetLeft + inp.offsetWidth - size - 3) + 'px';
    b.style.top = (inp.offsetTop + (h - size) / 2) + 'px';
  }

  function clear(inp) {
    inp.value = '';
    ['input', 'change'].forEach(function (t) { inp.dispatchEvent(new Event(t, { bubbles: true })); });
    // 各處的 input 處理可能整塊重畫把框換掉 → 找回同 id 的新框再聚焦
    var cur = (inp.id && document.getElementById(inp.id)) || inp;
    try { cur.focus(); } catch (e) { }
    place(cur);
  }

  function attach(inp) {
    if (inp._scb && inp._scb.isConnected && inp._scb.previousElementSibling === inp) return;
    if (inp.matches(SKIP) || inp.closest(SKIP)) return;
    if (inp._scb) { try { inp._scb.remove(); } catch (e) { } }
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'scx'; b.hidden = true;
    b.setAttribute('aria-label', '清除搜尋，恢復全部'); b.title = '清除搜尋，恢復全部';
    b.textContent = '×';
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });   // 不讓框失焦（點 × 後焦點留在框內）
    b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); clear(inp); });
    inp.insertAdjacentElement('afterend', b);
    inp._scb = b;
    if (list.indexOf(inp) < 0) list.push(inp);
    if (window.ResizeObserver) { try { new ResizeObserver(function () { place(inp); }).observe(inp); } catch (e) { } }
    place(inp);
  }

  var raf = 0;
  function scan() {
    raf = 0;
    document.querySelectorAll(SEL).forEach(function (i) { if (i.tagName === 'INPUT') attach(i); });
    list = list.filter(function (i) { return i.isConnected; });
    list.forEach(place);
  }
  function sched() { if (!raf) raf = requestAnimationFrame(scan); }

  document.addEventListener('input', function (e) { var t = e.target; if (t && t._scb) place(t); }, true);
  document.addEventListener('focusin', function (e) { var t = e.target; if (t && t._scb) place(t); }, true);
  // Esc：框裡有字就先清字（並擋掉別人把整個面板關掉）；沒字就照原樣
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var t = e.target;
    if (t && t._scb && t.value) { e.preventDefault(); e.stopPropagation(); clear(t); }
  }, true);
  window.addEventListener('resize', sched);
  window.addEventListener('hashchange', sched);
  new MutationObserver(sched).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'class', 'style', 'value'] });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan); else scan();
  window.TwSearchClear = { scan: scan, clear: clear };
})();
