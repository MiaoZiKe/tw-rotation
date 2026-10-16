/* ============================================================================
   全站內容保護：防複製＋浮水印「哩股哩股」（2026-10-16）
   ----------------------------------------------------------------------------
   Andy 2026-10-16：「內容需設定不可被他人複製」「所有分頁 圖表，都需要浮水印 哩股哩股 避免被盜用」
                    「且所有分頁 圖表 內容，且不可被複製，都需要浮水印 哩股哩股 避免被盜用」
   集中在這一支，之後要調透明度、例外名單、提示文字都只改這裡。載入位置：index.html 緊接在
   vendor/echarts.min.js 與 vendor/lightweight-charts.js 之後、chart.js／app.js 之前 —— 這樣所有
   echarts.init 與 LightweightCharts.createChart 建出來的圖都會經過這裡的包裝，不必一張一張改。

   一、防複製（html.twnocopy）
     · CSS：整頁 user-select:none、iOS 長按選單關掉；例外照常可選取：input、textarea、select、contenteditable、[data-copyable]。
     · 事件：copy／cut 攔下（例外同上；選取範圍在輸入框裡的照常）；右鍵（contextmenu）攔下瀏覽器選單，
       但站內自己的右鍵功能（分頁列「還原預設順序」、自訂週期鈕右鍵移除）照跑 —— 只 preventDefault、不 stopPropagation，
       而且提示只在「沒有站內功能接手」時才跳；拖曳（dragstart）攔下，但 [draggable="true"]（分頁拖曳排序）照常。
     · 例外頁：管理區 #admin/*（管理者要複製 email、訂單號）整個不套。
     · 站內的「複製」按鈕：navigator.clipboard.writeText 不經過 copy 事件、不受影響；
       舊瀏覽器退回 execCommand('copy') 時選取的是暫時的 <textarea>（例外名單內），也照常可用。
     · 提示：畫面左下角小提示「本站內容受著作權保護，請勿複製」，2.4 秒自己消失（不用 alert 跳窗）。
     ⚠ 這是「擋一般使用者順手複製」，不是 DRM：開發者工具、截圖都擋不住 —— 截圖靠下面的浮水印。

   二、浮水印
     a. 整頁：body::after 一層 position:fixed、pointer-events:none 的斜向重複「哩股哩股」（內嵌 SVG data URI）。
        偽元素不是 DOM 節點、position:fixed 不佔版面，所以不改任何元素的尺寸與位置（桌機守門的版面指紋不變）。
        深淺主題各一組透明度（--tw-wm）；頁面裡的區塊要自己帶一層時用 background-image:var(--tw-wm)。
     b. ECharts：包住 echarts.init，每個實例的 setOption 都在 graphic 最後面補一個 id=__twwm 的文字
        （圖中央、旋轉約 20 度、silent:true 不擋滑鼠、z 低於系列）；圖自己的 graphic 照留（合併，不覆蓋）。
        getOption() 看不到它（不打亂既有讀 graphic 的程式與驗收）；要看原樣用 getOptionWm()。
     c. K 線（lightweight-charts v5）：包住 LightweightCharts.createChart，在主窗格掛內建的 createTextWatermark。
   驗收：scripts/_uitest.py「精選文章1014」的「全站防複製／浮水印」那幾條。
   ============================================================================ */
(function () {
  'use strict';
  const TXT = '哩股哩股';
  const MSG = '本站內容受著作權保護，請勿複製';
  const root = document.documentElement;
  const isLight = () => root.getAttribute('data-theme') === 'light';
  const inkWm = () => (isLight() ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.06)');

  /* ------------------------------------------------------------------ 樣式（整頁浮水印＋不可選取） */
  const tile = (fill) => 'url("data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="260" height="170" viewBox="0 0 260 170"><text x="130" y="92" text-anchor="middle" font-family="Noto Sans TC,PingFang TC,Microsoft JhengHei,sans-serif" font-size="20" font-weight="700" fill="${fill}" transform="rotate(-20 130 85)">${TXT}</text></svg>`) + '")';
  const css = document.createElement('style');
  css.id = 'twProtectCss';
  css.textContent = `
:root{--tw-wm:${tile('rgba(255,255,255,0.045)')}}
:root[data-theme="light"]{--tw-wm:${tile('rgba(0,0,0,0.05)')}}
html.twwm body::after{content:"";position:fixed;inset:0;z-index:2147483000;pointer-events:none;background-image:var(--tw-wm);background-repeat:repeat;background-size:260px 170px}
html.twnocopy body{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
html.twnocopy input,html.twnocopy textarea,html.twnocopy select,html.twnocopy [contenteditable]:not([contenteditable="false"]),html.twnocopy [contenteditable]:not([contenteditable="false"]) *,
html.twnocopy [data-copyable],html.twnocopy [data-copyable] *{-webkit-user-select:text;user-select:text;-webkit-touch-callout:default}
.twprot-toast{position:fixed;left:16px;bottom:24px;z-index:2147483001;max-width:calc(100vw - 32px);box-sizing:border-box;display:flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;border:1px solid var(--line-2,#2a3860);background:var(--panel-3,#141e36);color:var(--ink,#e8eeff);font-size:13px;line-height:1.4;
  box-shadow:0 8px 24px rgba(0,0,0,.3);pointer-events:none;opacity:0;transform:translateY(6px);transition:opacity .18s,transform .18s}
.twprot-toast.on{opacity:1;transform:none}
.twprot-toast svg{flex:none;color:var(--amber,#f5b041)}
@media (max-width:640px){html.m4 .twprot-toast{left:12px;right:12px;bottom:auto;top:calc(12px + env(safe-area-inset-top,0px));max-width:none;justify-content:center}}`;
  (document.head || root).appendChild(css);
  root.classList.add('twwm');

  /* ------------------------------------------------------------------ 防複製 */
  const isAdmin = () => /^#admin(\/|$)/.test(location.hash || '');
  const sync = () => root.classList.toggle('twnocopy', !isAdmin());
  sync();
  window.addEventListener('hashchange', sync);
  const EXEMPT = 'input,textarea,select,[contenteditable]:not([contenteditable="false"]),[data-copyable]';
  const exempt = (n) => { const el = n && (n.nodeType === 1 ? n : n.parentElement); return !!(el && el.closest && el.closest(EXEMPT)); };
  const on = () => root.classList.contains('twnocopy');
  let toastEl = null, toastT = 0, lastShow = 0;
  function toast() {
    const now = Date.now(); if (now - lastShow < 600 && toastEl && toastEl.classList.contains('on')) return;
    lastShow = now;
    if (!toastEl) {
      toastEl = document.createElement('div'); toastEl.className = 'twprot-toast'; toastEl.id = 'twProtToast';
      toastEl.setAttribute('role', 'status'); toastEl.setAttribute('aria-live', 'polite');
      toastEl.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg><span></span>';
      document.body.appendChild(toastEl);
    }
    toastEl.querySelector('span').textContent = MSG;
    toastEl.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => toastEl.classList.remove('on'), 2400);
  }
  let blocked = 0;
  const block = (e) => { e.preventDefault(); blocked += 1; toast(); };
  ['copy', 'cut'].forEach((t) => document.addEventListener(t, (e) => {
    if (!on()) return;
    const sel = window.getSelection ? window.getSelection() : null;
    if (exempt(e.target) || (sel && sel.rangeCount && exempt(sel.anchorNode) && exempt(sel.focusNode))) return;
    block(e);
  }, true));
  // 右鍵放在 window 的冒泡階段：站內自己的右鍵選單（tabdrag、自訂週期鈕）先跑，它們 preventDefault 過就不再跳提示
  window.addEventListener('contextmenu', (e) => {
    if (!on() || exempt(e.target)) return;
    if (e.defaultPrevented) return;
    block(e);
  });
  document.addEventListener('dragstart', (e) => {
    if (!on()) return;
    const el = e.target && e.target.nodeType === 1 ? e.target : e.target && e.target.parentElement;
    if (el && el.closest && el.closest('[draggable="true"]')) return;   // 站內的拖曳排序
    if (exempt(e.target)) return;
    e.preventDefault();
  }, true);

  /* ------------------------------------------------------------------ ECharts 浮水印 */
  const WM_ID = '__twwm';
  const wmSize = (w, h) => Math.round(Math.max(14, Math.min(64, Math.min(w * 0.085, h * 0.2))));
  function wmEl(inst) {
    const w = inst.getWidth() || 0, h = inst.getHeight() || 0;
    return { type: 'text', id: WM_ID, left: 'center', top: 'middle', silent: true, z: 0, zlevel: 0, rotation: Math.PI / 9,
      invisible: w < 120 || h < 64,   // 迷你走勢圖（一行高）不放：字小到只剩一團灰
      style: { text: TXT, fontSize: wmSize(w, h), fontWeight: 700, fill: inkWm(), fontFamily: '"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif' } };
  }
  const dropWm = (arr) => arr.filter((e) => !(e && e.id === WM_ID));
  function inject(o, el, replace) {
    if (!o || typeof o !== 'object' || Array.isArray(o) || o.baseOption) return o;
    const g = o.graphic;
    if (g == null) return replace ? Object.assign({}, o, { graphic: [el] }) : o;
    if (Array.isArray(g)) {
      if (g.length && g[0] && typeof g[0] === 'object' && Array.isArray(g[0].elements)) {
        const g2 = g.slice(); g2[0] = Object.assign({}, g[0], { elements: dropWm(g[0].elements).concat([el]) }); return Object.assign({}, o, { graphic: g2 });
      }
      return Object.assign({}, o, { graphic: dropWm(g).concat([el]) });
    }
    if (typeof g === 'object') {
      if (Array.isArray(g.elements)) return Object.assign({}, o, { graphic: Object.assign({}, g, { elements: dropWm(g.elements).concat([el]) }) });
      return Object.assign({}, o, { graphic: [g, el] });
    }
    return o;
  }
  function wrapEc(inst) {
    if (!inst || inst.__twwm) return inst;
    inst.__twwm = true;
    const rawSet = inst.setOption.bind(inst), rawGet = inst.getOption.bind(inst), rawResize = inst.resize.bind(inst), rawClear = inst.clear.bind(inst);
    let has = false, fs = 0;
    inst.setOption = function (o, a, b) {
      const replace = !has || a === true || (a && typeof a === 'object' && (a.notMerge || (Array.isArray(a.replaceMerge) ? a.replaceMerge.includes('graphic') : a.replaceMerge === 'graphic')));
      let o2 = o;
      try { const el = wmEl(inst); o2 = inject(o, el, replace); if (o2 !== o || replace) { has = true; fs = el.style.fontSize; } } catch (e) { o2 = o; }
      return rawSet(o2, a, b);
    };
    inst.getOptionWm = rawGet;
    inst.getOption = function () {
      const o = rawGet.apply(null, arguments);
      if (o && Array.isArray(o.graphic)) {
        o.graphic = o.graphic.map((gc) => (gc && Array.isArray(gc.elements) ? Object.assign({}, gc, { elements: dropWm(gc.elements) }) : gc));
        if (o.graphic.every((gc) => !gc || (Array.isArray(gc.elements) && !gc.elements.length))) delete o.graphic;
      }
      return o;
    };
    inst.resize = function () {
      const r = rawResize.apply(null, arguments);
      try {
        if (has) {
          const el = wmEl(inst);
          if (el.style.fontSize !== fs || el.invisible) { fs = el.style.fontSize; rawSet({ graphic: [{ id: WM_ID, invisible: el.invisible, style: { fontSize: fs } }] }, { lazyUpdate: true, silent: true }); }
        }
      } catch (e) { /* 不影響圖本身 */ }
      return r;
    };
    inst.clear = function () { has = false; return rawClear.apply(null, arguments); };
    return inst;
  }
  const EC = window.echarts;
  if (EC && typeof EC.init === 'function' && !EC.__twwm) {
    const rawInit = EC.init;
    try {
      EC.init = function () { return wrapEc(rawInit.apply(this, arguments)); };
      EC.__twwm = true;
    } catch (e) { /* 物件被凍結：不加浮水印，圖照常 */ }
  }

  /* ------------------------------------------------------------------ K 線（lightweight-charts）浮水印 */
  const LW0 = window.LightweightCharts, lwList = [];
  const lwLine = (h) => ({ text: TXT, color: inkWm(), fontSize: Math.round(Math.max(18, Math.min(56, (h || 320) * 0.13))), fontStyle: 'bold' });
  /* ⚠ lightweight-charts 匯出的物件是凍結的（實測 v5.2.1：直接改 createChart 會丟 TypeError）——
     所以換成「複製一份、只換 createChart」的新物件放回 window.LightweightCharts；chart.js 是在這之後才讀它，拿到的就是新的。 */
  if (LW0 && typeof LW0.createChart === 'function' && typeof LW0.createTextWatermark === 'function' && !LW0.__twwm) {
    const rawCreate = LW0.createChart;
    const LW = Object.assign({}, LW0, {
      __twwm: true,
      createChart(el) {
        const ch = rawCreate.apply(LW0, arguments);
        try {
          const node = typeof el === 'string' ? document.getElementById(el) : el;
          const h = node && node.clientHeight;
          if (!(h && h < 90)) {     // 很矮的迷你圖不放
            const wm = LW0.createTextWatermark(ch.panes()[0], { horzAlign: 'center', vertAlign: 'center', lines: [lwLine(h)] });
            ch.__twwm = wm; lwList.push({ ch, wm, h });
            if (lwList.length > 200) lwList.splice(0, lwList.length - 200);
          }
        } catch (e) { /* 浮水印失敗不影響 K 線 */ }
        return ch;
      },
    });
    try { window.LightweightCharts = LW; } catch (e) { /* 唯讀：略 */ }
  }
  // 換深淺主題：K 線浮水印跟著換色（ECharts 換主題時整張重建，會自己吃到新色）
  new MutationObserver(() => {
    for (let i = lwList.length - 1; i >= 0; i--) {
      try { lwList[i].wm.applyOptions({ lines: [lwLine(lwList[i].h)] }); } catch (e) { lwList.splice(i, 1); }
    }
  }).observe(root, { attributes: true, attributeFilter: ['data-theme'] });

  window.TwProtect = {
    TEXT: TXT, MSG, toast,
    blocked: () => blocked,
    lwc: () => lwList.filter((x) => { try { return !!x.ch.chartElement().isConnected; } catch (e) { return false; } }).map(() => TXT),
  };
})();
