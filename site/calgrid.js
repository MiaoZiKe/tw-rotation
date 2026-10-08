/* ============================================================================
   共用月曆格小模組（2026-10-06，Andy：「週末就反灰色、國定假日標上日曆」「ETF 日曆也優化」）
   財報日曆（earnings.js）與 ETF 配息行事曆（etfpage.js）共用，不各寫一套：
     · 週六日格反灰（.cg-we）、台股休市日格底色＋小字「國慶日・休市」（.cg-hol／.cg-hl）
     · 一屏的格高自適應 fit()
   休市日資料：site/tw_holidays.json（由 scripts/gen_holidays.py 從 pipeline/calendar/tw_holidays.yaml 產生，來源與查證日寫在 YAML）。
   ========================================================================== */
(function () {
  'use strict';
  const S = { days: {}, p: null };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  function injectCSS() {
    if (document.getElementById('calgridCss')) return;
    const s = document.createElement('style'); s.id = 'calgridCss';
    s.textContent = `
.cg-we:not(.today):not(.out):not(.sel){background:color-mix(in srgb,var(--ink) 14%,var(--panel))!important;color:var(--ink-3)!important}
.cg-we:not(.out) .dn b{color:var(--ink-3)!important}
.cg-hol:not(.today):not(.out):not(.sel){background:color-mix(in srgb,var(--violet) 16%,var(--panel-2))!important}
.cg-hl{display:block;font-size:12px;line-height:16px;color:var(--violet);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
/* 面板小圖（ECharts）：高度跟以前的 SVG 一樣 84px，版面不動 */
.cgmini{width:100%;height:84px;display:block}
@media (max-width:640px){.cg-hl[data-s]{text-overflow:clip}.cg-hl[data-s]>.cg-hf{display:none}.cg-hl[data-s]::after{content:attr(data-s)}}`;
    document.head.appendChild(s);
  }
  function load() {
    injectCSS();
    if (S.p) return S.p;
    S.p = fetch('tw_holidays.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).then((j) => {
      S.days = (j && j.days) || {}; return S.days;
    }).catch(() => S.days);
    return S.p;
  }
  const isWeekend = (k) => { const g = new Date(k + 'T00:00:00Z').getUTCDay(); return g === 0 || g === 6; };
  const holiday = (k) => S.days[k] || null;
  /* 加在格子 class 上的字串（含前導空白） */
  const cls = (k) => (isWeekend(k) ? ' cg-we' : '') + (holiday(k) ? ' cg-hol' : '');
  /* 格內小字「國慶日・休市」；非休市日回空字串。
     滑過提示只寫「X・台股休市（證交所公告）」：tw_holidays.json 的 verified 是查證紀錄（WebSearch 摘要、資料湖交易日對照），
     讀者用不到，10-06 廢話普查第二輪拿掉（只留在 pipeline/calendar/tw_holidays.yaml）。 */
  /* 2026-10-08（Andy：「所有日曆若是不夠放下全部文字，至少留重點」）：手機（≤640）格子窄，只放兩字簡稱（國慶、光復），不出現「國慶日…」；桌機照舊全名 */
  const short2 = (h) => String(h).replace(/[（(].*$/, '').slice(0, 2);
  const tag = (k) => { const h = holiday(k); return h ? `<span class="cg-hl" data-s="${esc(short2(h))}" title="${esc(h)}・台股休市（證交所公告）"><span class="cg-hf">${esc(h)}・休市</span></span>` : ''; };
  /* 一屏格高：格高＝（視窗剩下的高度 − 星期列 − 間距）÷ 列數，夾在 min～max；回傳格高 */
  function fit(grid, rows, min, max, gap, extra) {
    const top = grid.getBoundingClientRect().top + window.scrollY;
    const avail = window.innerHeight - top - 26 - (extra || 0);
    return Math.max(min, Math.min(max, Math.floor((avail - 20 - rows * gap) / rows)));
  }
  /* ==========================================================================
     面板小圖（2026-10-08，Andy：「日曆圖內的長條圖都要優化，符合我們原本要的漸層效果及回應互動效果」）
     以前是手刻 SVG：平的實心方塊、沒圓角、滑過只有瀏覽器原生 title（要停一秒才出來、手機完全沒有）。
     全站長條的漸層／圓角／寬度規格只寫在 App.chart() 的包裝層（softenOption → BAR.apply，docs/chart_library.md C 款），
     手刻 SVG 吃不到，所以改成走 App.chart()：
       · 直條：同色漸層（柱頂實色 → 柱底 45%）、頂端 3px 圓角、寬 ≤ 12px —— 全部由包裝層套，這裡不重寫一份
       · 折線：自己的縱軸（跟直條不同單位），寬 2、圓端、圓點，畫在直條上面
       · 滑過（或手指點到）那一欄：該根加亮＋2px 外框、其他根變淡；提示框掛在 body（tipSafe），卡片裁不到
       · 點直條：選取那根（其他維持淡）、呼叫 spec.onPick(i) 讓面板把下方表格對應列一起亮；再點一次取消
       · 手機（沒有滑鼠）：第一下＝提示、第二下＝選取（chart_library「通用點擊規則」）
     用法：html 裡放 CalGrid.mini(spec) 回傳的占位 div，innerHTML 之後呼叫 CalGrid.mount(容器)。
     spec = { labels:[…], bars:{ vals, color: css 色或 (v,i)=>色, name }, line:{ vals, color, name }, tip:(i)=>HTML, onPick:(i|null)=>{}, aria }
     ⚠ 色可以寫 'var(--amber)'：畫的當下才讀 CSS 變數，深淺主題各自對（換主題會整頁重畫）。
     ⚠ 圖內不放任何文字（數值標籤、軸字都關）：日期與圖例由各面板用 HTML 寫在圖下方，字級守得住 12px 下限。 */
  const MINI = {}, LIVE = new Set();
  let seq = 0;
  const cssv = (c) => {
    const m = /^var\((--[\w-]+)\)$/.exec(String(c || '').trim());
    if (!m) return c;
    try { return getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || c; } catch (e) { return c; }
  };
  function mini(spec) {
    injectCSS();
    const id = 'cgm' + (++seq);
    MINI[id] = spec;
    return `<div class="cgmini" id="${id}" data-cgm="${id}" role="img" aria-label="${esc(spec.aria || '')}"></div>`;
  }
  const touchOnly = () => { try { return window.matchMedia('(hover: none)').matches; } catch (e) { return false; } };
  function optionOf(el) {
    const A = window.App, CH = A.CH, sp = el._cgm, sel = el._cgSel;
    const n = (sp.labels || []).length, R = (A.barStyle && A.barStyle.R) || 3;
    const series = [];
    if (sp.bars) {
      const fixed = typeof sp.bars.color === 'function' ? null : cssv(sp.bars.color || 'var(--cat-1)');
      series.push({
        id: 'b', type: 'bar', name: sp.bars.name || '', barWidth: '56%', z: 2,
        label: { show: false },
        itemStyle: { borderRadius: [R, R, 0, 0], ...(fixed ? { color: fixed } : {}) },
        emphasis: { focus: 'self', blurScope: 'series', itemStyle: { borderColor: CH.ink, borderWidth: 2 } },
        blur: { itemStyle: { opacity: 0.32 } },
        data: sp.bars.vals.map((v, i) => {
          const o = { value: v == null || !isFinite(v) ? null : v };
          const it = {};
          if (!fixed) it.color = cssv(sp.bars.color(v, i));
          if (v != null && v < 0) it.borderRadius = [0, 0, R, R];         // 往下長的負值：圓角在遠端（柱底）
          if (sel != null) { if (i === sel) { it.borderColor = CH.ink; it.borderWidth = 2; } else it.opacity = 0.32; }
          if (Object.keys(it).length) o.itemStyle = it;
          return o;
        }),
      });
    }
    if (sp.line) {
      const lc = cssv(sp.line.color || 'var(--cyan)');
      series.push({
        id: 'l', type: 'line', name: sp.line.name || '', yAxisIndex: sp.bars ? 1 : 0, z: 3,
        data: sp.line.vals.map((v) => (v == null || !isFinite(v) ? null : v)), connectNulls: true,
        symbol: 'circle', symbolSize: 5, showSymbol: true,
        lineStyle: { color: lc, width: 2 }, itemStyle: { color: lc },
        emphasis: { scale: 1.6, focus: 'none' },
      });
    }
    const base0 = sp.bars && sp.bars.vals.some((v) => v != null && v < 0);
    return {
      animation: true, timeGrid: false,
      grid: { left: 2, right: 2, top: 6, bottom: 4 },
      tooltip: {
        ...A.tip, trigger: 'axis', confine: false,
        axisPointer: { type: 'shadow', shadowStyle: { color: A.hexA ? A.hexA(CH.ink, 0.07) : 'rgba(128,128,128,.08)' } },
        formatter: (ps) => { const p = Array.isArray(ps) ? ps[0] : ps; return p && sp.tip ? sp.tip(p.dataIndex) : ''; },
      },
      xAxis: { type: 'category', data: sp.labels || Array.from({ length: n }, (_, i) => String(i)), show: false, boundaryGap: true },
      yAxis: [
        { type: 'value', show: true, min: base0 ? null : 0, splitNumber: 3, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { show: false },
          splitLine: { lineStyle: { color: CH.grid, opacity: 0.6 } } },
        { type: 'value', show: false, scale: true },
      ],
      series,
    };
  }
  function draw(el) {
    const A = window.App; if (!A || !A.chart) return null;
    const c = A.chart(el, optionOf(el));
    el.dataset.sel = el._cgSel == null ? '' : String(el._cgSel);
    return c;
  }
  /* 選取第 i 根（null＝取消）；fromUser＝使用者在圖上點的（要通知面板）。表格點列時面板也呼叫這一支，雙向連動。 */
  function pick(el, i, quiet) {
    if (!el || !el._cgm) return;
    el._cgSel = i == null || i < 0 ? null : i;
    draw(el);
    if (!quiet && el._cgm.onPick) el._cgm.onPick(el._cgSel);
  }
  function bind(el, c) {
    if (!c || el._cgBound === c) return;
    el._cgBound = c;
    const hov = (i) => {
      if (i === el._cgHov) return;
      el._cgHov = i;
      c.dispatchAction({ type: 'downplay', seriesIndex: 0 });
      if (i != null) c.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: i });
      el.dataset.hov = i == null ? '' : String(i);
    };
    c.on('updateAxisPointer', (e) => {
      const ai = e && e.axesInfo && e.axesInfo[0];
      hov(ai && ai.value != null ? +ai.value : null);
    });
    c.on('globalout', () => hov(null));
    c.getZr().on('click', (ev) => {
      const n = (el._cgm.labels || []).length; if (!n) return;
      let i;
      // ⚠ 用 gridIndex 才會回 [x, y]；用 xAxisIndex 只回一個數字（第一版就是這樣讀成 undefined、點了沒反應）
      try { const v = c.convertFromPixel({ gridIndex: 0 }, [ev.offsetX, ev.offsetY]); i = Math.round(Array.isArray(v) ? v[0] : v); } catch (e) { return; }
      if (!(i >= 0 && i < n)) return;
      if (touchOnly() && el._cgTap !== i) { el._cgTap = i; c.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: i }); hov(i); return; }   // 手機第一下：只提示
      el._cgTap = null;
      pick(el, el._cgSel === i ? null : i);
    });
    el.style.cursor = 'pointer';
  }
  /* 把容器裡還沒畫的占位 div 畫出來；順手把已經不在頁面上的舊圖 dispose（面板每次重畫都是 innerHTML 整塊換掉） */
  function mount(root) {
    LIVE.forEach((el) => {
      if (el.isConnected) return;
      LIVE.delete(el);
      try { const c = window.echarts && window.echarts.getInstanceByDom(el); if (c) c.dispose(); } catch (e) { /* 已經沒了 */ }
    });
    (root || document).querySelectorAll('.cgmini[data-cgm]').forEach((el) => {
      if (!el._cgm) { el._cgm = MINI[el.dataset.cgm]; delete MINI[el.dataset.cgm]; }
      if (!el._cgm) return;
      if (el._cgSel === undefined) el._cgSel = el._cgm.sel == null ? null : el._cgm.sel;
      bind(el, draw(el));
      LIVE.add(el);
    });
  }
  window.CalGrid = { mini, mount, pick, load, cls, tag, holiday, isWeekend, fit, days: () => S.days };
})();
