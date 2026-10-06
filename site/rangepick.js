/* ============================================================================
   共用「期間」元件（2026-10-06，Andy：「週期切換……可以選擇時段如圖二那樣，切換到不同時間週期也可以在旁邊顯示對應年限日期」）
   長相照管理區流量觀測的期間列（claude/style-guide 分支 site/admin.js 的 .trctl）：
     期間 [下拉] [起始日]～[結束日]
   規則（兩邊一樣，所以抽成一支，不各寫一套）：
     · 切下拉 → 兩個日期框同步顯示該期間實際的起訖日（由呼叫端算好，透過 set() 寫回）
     · 手動改任一個日期 → 下拉自動跳成「起始日期～至今」（value＝'custom'），並把新起訖交給呼叫端
   管理區（admin.js 流量觀測，10-06 合進 main）與 ETF 專區報酬比較（etfpage.js）都用這一支，不要再各寫一套。
   用法：
     el.innerHTML = RangePick.html({ id: 'etfRng', options: [['5y','近 5 年'], …, ['custom','起始日期～至今']], value, from, to, max })
     RangePick.bind(el.querySelector('#etfRng'), { onChange: ({ value, from, to, manual }) => … })
     RangePick.set(el.querySelector('#etfRng'), { value, from, to })
   選項：ids＝{ sel, from, to } 給三個控制項各自的 id（管理區沿用舊 id：admDaysSel／admSince／admUntil，驗收靠它們）；
        custom＝「起始日期～至今」那個選項的值（預設 'custom'；管理區是 'since'）；extra＝接在日期框後面的 HTML（管理區的重新整理鈕與隱私說明）。
   ========================================================================== */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  function injectCSS() {
    if (document.getElementById('rangepickCss')) return;
    const s = document.createElement('style'); s.id = 'rangepickCss';
    /* 字級 13px、控制項高 30px（跟全站 select.etsel 同一套）；窄螢幕允許整組換到下一行，但每個控制項自己不換行 */
    s.textContent = `
.rpk{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:13px;min-width:0}
.rpk label{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2);white-space:nowrap}
.rpk select,.rpk input[type=date]{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:inherit;font-size:13px;box-sizing:border-box}
.rpk input[type=date]{width:138px;padding:0 6px}
.rpk .rpto{color:var(--ink-2)}
.rpk .rpd{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
@media (max-width:520px){.rpk input[type=date]{width:128px}}`;
    document.head.appendChild(s);
  }
  function html(o) {
    injectCSS();
    const max = o.max ? ` max="${esc(o.max)}"` : '', ids = o.ids || {}, I = (k) => (ids[k] ? ` id="${esc(ids[k])}"` : '');
    const min = o.from ? ` min="${esc(o.from)}"` : '';
    return `<div class="rpk${o.cls ? ' ' + esc(o.cls) : ''}"${o.id ? ` id="${esc(o.id)}"` : ''} data-v="${esc(o.value)}" data-custom="${esc(o.custom || 'custom')}"><label>${esc(o.label || '期間')} <select class="rpsel"${I('sel')} aria-label="${esc(o.label || '期間')}">${
      o.options.map(([k, n]) => `<option value="${esc(k)}"${k === o.value ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
      <span class="rpd"><input type="date" class="rpfrom"${I('from')} value="${esc(o.from || '')}"${max} aria-label="起始日期"><span class="rpto trto">～</span><input type="date" class="rpto-in"${I('to')} value="${esc(o.to || '')}"${max}${min} aria-label="結束日期"></span>${o.extra || ''}</div>`;
  }
  function set(el, o) {
    if (!el) return;
    const sel = el.querySelector('.rpsel'), f = el.querySelector('.rpfrom'), t = el.querySelector('.rpto-in');
    if (o.value != null) { sel.value = o.value; el.dataset.v = o.value; }
    if (o.from != null) f.value = o.from;
    if (o.to != null) t.value = o.to;
    if (f.value) t.min = f.value;
  }
  function bind(el, o) {
    if (!el) return;
    const sel = el.querySelector('.rpsel'), f = el.querySelector('.rpfrom'), t = el.querySelector('.rpto-in');
    sel.onchange = () => { el.dataset.v = sel.value; o.onChange({ value: sel.value, from: f.value, to: t.value, manual: false }); };
    const manual = () => {
      if (!f.value) return;
      const cv = el.dataset.custom || 'custom';
      sel.value = cv; el.dataset.v = cv; t.min = f.value;
      o.onChange({ value: cv, from: f.value, to: t.value, manual: true });
    };
    f.onchange = manual; t.onchange = manual;
  }
  window.RangePick = { html, bind, set };
})();
