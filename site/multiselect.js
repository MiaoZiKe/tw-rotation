/* ============================================================================
   site/multiselect.js —— 全站共用的「下拉多選」篩選元件（window.TwMS）
   ----------------------------------------------------------------------------
   ★ 2026-10-06（Andy 截圖：市場明細 → 漲跌分佈卡「族群篩選」展開成一大片族群膠囊牆，
     底下還寫「還有 101 個族群在下面，往下捲」）原話：
     「改下拉式清單篩選，確認是否其他還有這樣的功能未被更改，一併改成這樣」。

   為什麼要一支「共用」的，而不是在漲跌分佈那裡再寫一次：
     · 膠囊牆的問題不是長得醜，是**它會把版面撐高**：一打開，下面的圖整個被往下推 120～200px，
       收起來又彈回去 —— 違反 docs/style_guide.md 第 4 條「互動不晃動」。
       下拉面板浮在畫面上（position:fixed），開關都不改任何一張卡的高度。
     · 以後任何「選項很多的篩選」都要長同一個樣子（style_guide 第五節「篩選選項多 → 共用下拉多選」），
       各頁各寫一份就會像以前一樣一頁一個樣、一邊修 bug 另一邊漏。
   外觀照選股策略「子標籤：不限 ▾」那一顆（explore.js 的 .sl-dd／.sl-ddm）：
     按鈕一行「族群：不限 ▾ ／ 族群：晶圓代工 ▾ ／ 族群：已選 3 ▾」，有篩選時換主色。

   用法：
     const ms = TwMS.mount(hostEl, {
       id: 'distGroups',            // 全站唯一。同一個 id 重新 mount（容器被 innerHTML 換掉）會接手上一個的開合狀態
       label: '族群',               // 按鈕前綴「族群：」
       items: [{ v: '晶圓代工', t: '晶圓代工', g: 'semiconductor', n: 9, title: '…' }, …],
       groups: [{ k: 'semiconductor', t: '半導體' }, …],   // 分組順序與標題（可省略＝不分組）
       selected: Set | Array | null,                       // null／空＝不限
       onChange: (set|null) => {…},                         // 每勾一下就叫一次（即時篩選）
       placeholder: '搜尋族群…', width: '11em', none: '不限',
     });
     ms.set({ items, selected }); ms.value(); ms.open(); ms.close();

   語意（刻意和 Excel 的「全部打勾＝全部」不同，跟選股策略子標籤一致）：
     · 一個都沒勾＝不限（不篩選）；勾了就**只看勾起來的那幾個**。
     · 「全選」＝把目前看得到的（有搜尋字就是搜尋結果）全部勾起來；「清除」＝全部取消、回到不限。
     · 分組標題可以點：那一組（目前看得到的）全勾／全取消。

   ⚠ 面板掛在 <body> 底下、position:fixed，**不是**放在卡片裡：
     卡片有 overflow:hidden（.eqpair>.card）、backdrop-filter（HUD 主題的卡片模糊）、fit.js 的 transform，
     任何一個都會把 absolute 面板切掉或把 fixed 的定位基準換掉。掛在 body 就三種都不受影響；
     代價是捲動／縮放視窗時要自己跟著按鈕重新定位（place()），按鈕捲出畫面或被藏起來就收起。
   ============================================================================ */
(function () {
  'use strict';
  if (window.TwMS) return;

  const REG = {};   // id → 目前掛著的實例
  const MEM = {};   // id → { open, q, top, focusQ, caret }：容器整塊重畫、重新 mount 時沿用（例如「⚡ 即時」每 5 秒重畫）
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const toSet = (x) => { if (!x) return new Set(); const s = new Set(x instanceof Set ? [...x] : x); return s; };

  /* 樣式只注入一次。值一律走主題變數（深／淺、HUD／專業／休閒都會跟著換），
     px 只出現在元件自己的尺寸 token（--ms-*），頁面要改寬度就覆寫 --ms-w。 */
  function css() {
    if (document.getElementById('twms-css')) return;
    const s = document.createElement('style');
    s.id = 'twms-css';
    s.textContent = `
.twms,.twms-pan{--ms-acc:var(--t4-accent-solid,var(--accent,var(--cyan)));--ms-h:30px;--ms-list-h:320px}
.twms{position:relative;display:inline-flex;min-width:0;max-width:100%;vertical-align:middle;flex:none}
.twms-btn{appearance:none;font:inherit;font-size:var(--fs-sm,13px);line-height:1;height:var(--ms-h);width:var(--ms-w,11em);max-width:100%;
  display:inline-flex;align-items:center;gap:2px;padding:0 var(--sp-2,8px) 0 var(--sp-3,12px);box-sizing:border-box;
  border-radius:var(--r-sm,8px);border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink-2);cursor:pointer;
  white-space:nowrap;text-align:left;transition:border-color .12s,color .12s}
.twms-btn .twms-k{flex:none}
.twms-btn b{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;font-weight:400;color:inherit}
.twms-btn i{flex:none;font-style:normal;padding-left:4px;color:inherit}
.twms-btn:hover,.twms.open .twms-btn{border-color:var(--ms-acc);color:var(--ink)}
.twms.on .twms-btn{border-color:var(--ms-acc);color:var(--ms-acc)}
.twms.on .twms-btn b{font-weight:700}
.twms-btn:focus-visible{outline:2px solid var(--ms-acc);outline-offset:1px}
.twms-pan{position:fixed;z-index:1200;box-sizing:border-box;display:flex;flex-direction:column;min-height:0;
  padding:var(--sp-2,8px);border-radius:var(--r-md,10px);border:1px solid var(--line-2);background:var(--panel);color:var(--ink);
  box-shadow:0 8px 24px rgba(0,0,0,.35);font-size:var(--fs-sm,13px);line-height:1.3}
.twms-q{flex:none;box-sizing:border-box;width:100%;height:var(--ms-h);padding:0 10px;font:inherit;font-size:var(--fs-sm,13px);
  border-radius:var(--r-sm,8px);border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink)}
.twms-q::placeholder{color:var(--ink-3)}
.twms-q:focus{outline:none;border-color:var(--ms-acc)}
.twms-bar{flex:none;display:flex;align-items:center;gap:var(--sp-2,8px);margin:var(--sp-2,8px) 0 var(--sp-1,4px);white-space:nowrap}
.twms-bar button{appearance:none;font:inherit;font-size:var(--fs-min,12px);height:26px;padding:0 10px;border-radius:7px;
  border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);cursor:pointer}
.twms-bar button:hover{border-color:var(--ms-acc)}
.twms-bar button:disabled{opacity:.45;cursor:default;border-color:var(--line-2)}
.twms-n{margin-left:auto;color:var(--ink-3);font-family:var(--mono);font-size:var(--fs-min,12px);font-variant-numeric:tabular-nums}
.twms-list{flex:1 1 auto;min-height:0;max-height:var(--ms-list-h);overflow-y:auto;overscroll-behavior:contain;
  display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px var(--sp-2,8px);align-content:start;
  border-top:1px solid var(--line);padding-top:var(--sp-1,4px);scrollbar-width:thin}
.twms-list::-webkit-scrollbar{width:6px}
.twms-list::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:999px}
.twms-gh{grid-column:1/-1;position:sticky;top:0;z-index:1;display:flex;align-items:center;gap:6px;appearance:none;border:0;margin:0;
  background:var(--panel);color:var(--ink-3);font:inherit;font-size:var(--fs-min,12px);font-weight:700;padding:6px 6px 3px;cursor:pointer;text-align:left}
.twms-gh:hover{color:var(--ink)}
.twms-gh em{margin-left:auto;font-style:normal;font-weight:400;font-family:var(--mono);font-variant-numeric:tabular-nums}
.twms-gh.some,.twms-gh.all{color:var(--ms-acc)}
.twms-o{display:flex;align-items:center;gap:6px;min-width:0;padding:4px 6px;border-radius:6px;color:var(--ink-2);cursor:pointer;white-space:nowrap}
.twms-o input{flex:none;margin:0;accent-color:var(--ms-acc);cursor:pointer}
.twms-o span{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis}
.twms-o em{flex:none;font-style:normal;font-family:var(--mono);font-size:var(--fs-min,12px);color:var(--ink-3);font-variant-numeric:tabular-nums}
.twms-o:hover{background:var(--panel-2);color:var(--ink)}
.twms-o.on{color:var(--ms-acc)}
.twms-o.on span{font-weight:600}
.twms-o.zero span{opacity:.55}
.twms-none{grid-column:1/-1;padding:14px 6px;color:var(--ink-3);text-align:center}
/* 搜尋時用 hidden 藏列：上面的 display:flex 會蓋掉瀏覽器預設的 [hidden]{display:none}，要自己補回來 */
.twms-pan [hidden]{display:none!important}
@media (max-width:420px){.twms-list{grid-template-columns:minmax(0,1fr)}}
@media (prefers-reduced-motion:reduce){.twms-btn{transition:none}}`;
    document.head.appendChild(s);
  }

  function mount(host, cfg) {
    if (!host || !cfg || !cfg.id) return null;
    css();
    const id = String(cfg.id);
    const mem = MEM[id] || (MEM[id] = { open: false, q: '', top: 0, focusQ: false, caret: 0 });
    // 同一個 id 已經有實例（容器被整塊換掉、或同一個容器重畫）：舊的把面板收走，開合狀態交給新的接手
    if (REG[id]) REG[id]._detach(true);

    let items = cfg.items || [];
    let groups = cfg.groups || null;
    let sel = toSet(cfg.selected);
    let pan = null, qi = null, lst = null, raf = 0;
    const label = cfg.label || '篩選';
    const none = cfg.none || '不限';

    host.classList.add('twms');
    host.dataset.ms = id;
    if (cfg.width) host.style.setProperty('--ms-w', cfg.width);
    host.innerHTML = `<button type="button" class="twms-btn" aria-haspopup="listbox" aria-expanded="false"><span class="twms-k">${esc(label)}：</span><b></b><i aria-hidden="true">▾</i></button>`;
    const btn = host.querySelector('.twms-btn');

    const textOf = (v) => { const it = items.find((x) => x.v === v); return it ? (it.t || it.v) : v; };
    const paintBtn = () => {
      // 勾到的值如果已經不在選項裡（例如換了市場別），不算數 —— 按鈕上的摘要要跟畫面一致
      const n = sel.size;
      const val = n === 0 ? none : n === 1 ? textOf([...sel][0]) : `已選 ${n}`;
      btn.querySelector('b').textContent = val;
      btn.title = n ? `${label}：${[...sel].map(textOf).join('、')}` : `${label}：${none}（點開勾選，可搜尋、可複選）`;
      host.classList.toggle('on', n > 0);
      host.dataset.n = String(n);
    };
    const emit = () => {
      paintBtn();
      paintCount();
      if (cfg.onChange) cfg.onChange(sel.size ? new Set(sel) : null);
    };

    /* ---------- 面板 ---------- */
    const build = () => {
      pan = document.createElement('div');
      pan.className = 'twms-pan';
      pan.dataset.ms = id;
      pan.setAttribute('role', 'dialog');
      pan.setAttribute('aria-label', `${label}篩選`);
      pan.innerHTML = `<input type="search" class="twms-q" placeholder="${esc(cfg.placeholder || `搜尋${label}…`)}" aria-label="${esc(cfg.placeholder || `搜尋${label}`)}" autocomplete="off">
        <div class="twms-bar"><button type="button" class="twms-all">全選</button><button type="button" class="twms-clr">清除</button><span class="twms-n"></span></div>
        <div class="twms-list" role="listbox" aria-multiselectable="true" aria-label="${esc(label)}"></div>`;
      qi = pan.querySelector('.twms-q');
      lst = pan.querySelector('.twms-list');
      qi.value = mem.q || '';
      qi.addEventListener('input', () => { mem.q = qi.value.trim(); filter(); });
      qi.addEventListener('focus', () => { mem.focusQ = true; });
      qi.addEventListener('blur', () => { mem.focusQ = false; });
      pan.querySelector('.twms-all').onclick = () => { visible().forEach((it) => sel.add(it.v)); syncChecks(); emit(); };
      pan.querySelector('.twms-clr').onclick = () => { if (!sel.size) return; sel.clear(); syncChecks(); emit(); };
      lst.addEventListener('change', (e) => {
        const c = e.target; if (!c || c.type !== 'checkbox' || c.dataset.v == null) return;
        if (c.checked) sel.add(c.dataset.v); else sel.delete(c.dataset.v);
        syncChecks(); emit();
      });
      lst.addEventListener('click', (e) => {
        const h = e.target.closest('.twms-gh'); if (!h) return;
        const vis = visible().filter((it) => (it.g || '') === h.dataset.g);
        const allOn = vis.length && vis.every((it) => sel.has(it.v));
        vis.forEach((it) => { if (allOn) sel.delete(it.v); else sel.add(it.v); });
        syncChecks(); emit();
      });
      lst.addEventListener('scroll', () => { mem.top = lst.scrollTop; }, { passive: true });
      pan.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); btn.focus(); } });
      renderList();
    };
    const renderList = () => {
      if (!lst) return;
      const byG = new Map();
      items.forEach((it) => { const k = it.g || ''; if (!byG.has(k)) byG.set(k, []); byG.get(k).push(it); });
      const order = groups ? groups.map((g) => g.k).filter((k) => byG.has(k)) : [];
      byG.forEach((_, k) => { if (!order.includes(k)) order.push(k); });
      const gt = (k) => { const g = groups && groups.find((x) => x.k === k); return g ? g.t : (k || ''); };
      const showHead = order.length > 1 || (order.length === 1 && order[0] !== '');
      lst.innerHTML = order.map((k) => (showHead ? `<button type="button" class="twms-gh" data-g="${esc(k)}" title="這一組全選／全取消">${esc(gt(k) || '其他')}<em></em></button>` : '')
        + byG.get(k).map((it) => `<label class="twms-o${sel.has(it.v) ? ' on' : ''}${it.n === 0 ? ' zero' : ''}" data-v="${esc(it.v)}" data-g="${esc(k)}" data-s="${esc(((it.t || it.v) + ' ' + gt(k)).toLowerCase())}"${it.title ? ` title="${esc(it.title)}"` : ` title="${esc(it.t || it.v)}"`}>`
          + `<input type="checkbox" data-v="${esc(it.v)}"${sel.has(it.v) ? ' checked' : ''}><span>${esc(it.t || it.v)}</span>${it.n != null ? `<em>${esc(it.n)}</em>` : ''}</label>`).join('')).join('')
        + '<div class="twms-none" hidden>找不到符合的選項</div>';
      filter();
      syncChecks();
    };
    const visible = () => items.filter((it) => {
      const o = lst && lst.querySelector(`.twms-o[data-v="${CSS.escape(it.v)}"]`);
      return o ? !o.hidden : true;
    });
    const filter = () => {
      if (!lst) return;
      const k = (mem.q || '').toLowerCase();
      let shown = 0;
      lst.querySelectorAll('.twms-o').forEach((o) => { const on = !k || o.dataset.s.includes(k); o.hidden = !on; if (on) shown++; });
      lst.querySelectorAll('.twms-gh').forEach((h) => { h.hidden = !lst.querySelector(`.twms-o[data-g="${CSS.escape(h.dataset.g)}"]:not([hidden])`); });
      const nn = lst.querySelector('.twms-none'); if (nn) nn.hidden = shown > 0;
      paintCount();
    };
    const syncChecks = () => {
      if (!lst) return;
      lst.querySelectorAll('.twms-o').forEach((o) => {
        const on = sel.has(o.dataset.v);
        o.classList.toggle('on', on);
        const c = o.querySelector('input'); if (c.checked !== on) c.checked = on;
      });
      lst.querySelectorAll('.twms-gh').forEach((h) => {
        const its = items.filter((it) => (it.g || '') === h.dataset.g);
        const n = its.filter((it) => sel.has(it.v)).length;
        h.querySelector('em').textContent = `${n}/${its.length}`;
        h.classList.toggle('all', n > 0 && n === its.length);
        h.classList.toggle('some', n > 0 && n < its.length);
      });
      paintCount();
    };
    const paintCount = () => {
      if (!pan) return;
      const n = pan.querySelector('.twms-n');
      if (n) n.textContent = `已選 ${sel.size}／${items.length}`;
      const c = pan.querySelector('.twms-clr'); if (c) c.disabled = !sel.size;
    };

    /* 定位：貼著按鈕下緣、左緣對齊；右邊放不下就改成右緣對齊；下面空間不夠且上面比較大就往上開。
       高度只在「視窗裡放得下」的範圍內縮放，面板永遠整個在視窗裡（390px 也一樣）。 */
    const place = () => {
      raf = 0;
      if (!pan) return;
      const r = btn.getBoundingClientRect();
      const vw = document.documentElement.clientWidth || window.innerWidth, vh = window.innerHeight, M = 8;
      // 按鈕被藏起來（換頁、分段切走）或整個捲出畫面 → 收起來，不留一塊浮在半空中的面板
      if (!host.isConnected || (!r.width && !r.height) || r.bottom < 0 || r.top > vh) { close(); return; }
      const w = Math.min(cfg.panelWidth || 360, vw - 2 * M);
      pan.style.width = w + 'px';
      let left = r.left;
      if (left + w > vw - M) left = r.right - w;
      left = Math.max(M, Math.min(left, vw - w - M));
      pan.style.left = Math.round(left) + 'px';
      const below = vh - r.bottom - 4 - M, above = r.top - 4 - M;
      const want = cfg.maxHeight || 440;
      if (below >= Math.min(want, 280) || below >= above) {
        pan.style.top = Math.round(r.bottom + 4) + 'px'; pan.style.bottom = '';
        pan.style.maxHeight = Math.max(120, Math.min(want, below)) + 'px';
      } else {
        pan.style.top = ''; pan.style.bottom = Math.round(vh - r.top + 4) + 'px';
        pan.style.maxHeight = Math.max(120, Math.min(want, above)) + 'px';
      }
    };
    const schedule = () => { if (!raf) raf = requestAnimationFrame(place); };

    /* ---------- 開合 ---------- */
    const onDown = (e) => { const t = e.target; if (host.contains(t) || (pan && pan.contains(t))) return; close(); };
    const onKey = (e) => { if (e.key === 'Escape' && pan) { close(); try { btn.focus({ preventScroll: true }); } catch (x) { /* 舊瀏覽器 */ } } };
    const onScroll = (e) => { if (pan && e.target && e.target.nodeType === 1 && pan.contains(e.target)) return; schedule(); };
    const onHash = () => close();
    const listen = (on) => {
      const f = on ? 'addEventListener' : 'removeEventListener';
      document[f]('pointerdown', onDown, true);
      document[f]('keydown', onKey);
      window[f]('scroll', onScroll, true);
      window[f]('resize', schedule);
      window[f]('hashchange', onHash);
    };
    function open(restore) {
      if (pan) return;
      // 同一時間只開一個：別的 TwMS 先收起來
      Object.keys(REG).forEach((k) => { if (k !== id && REG[k].isOpen()) REG[k].close(); });
      if (!restore) { mem.q = ''; mem.top = 0; }
      build();
      document.body.appendChild(pan);
      mem.open = true;
      host.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');
      place();
      if (!pan) return;                       // place() 判定按鈕看不見 → 已經收掉
      lst.scrollTop = mem.top || 0;
      listen(true);
      const coarse = window.matchMedia && window.matchMedia('(pointer:coarse)').matches;
      if (restore ? mem.focusQ : !coarse) {
        try { qi.focus({ preventScroll: true }); const c = Math.min(mem.caret || qi.value.length, qi.value.length); qi.setSelectionRange(c, c); } catch (x) { /* 舊瀏覽器 */ }
      }
    }
    function close() {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      if (!pan) { mem.open = false; return; }
      listen(false);
      pan.remove();
      pan = qi = lst = null;
      mem.open = false; mem.q = ''; mem.top = 0; mem.focusQ = false;
      host.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    }
    btn.addEventListener('click', (e) => { e.stopPropagation(); if (pan) close(); else open(false); });

    const api = {
      id, host,
      isOpen: () => !!pan,
      open: () => open(false),
      close,
      value: () => (sel.size ? new Set(sel) : null),
      set(o) {
        o = o || {};
        if (o.items) items = o.items;
        if (o.groups) groups = o.groups;
        if ('selected' in o) sel = toSet(o.selected);
        paintBtn();
        if (pan) { renderList(); lst.scrollTop = mem.top || 0; }
      },
      panel: () => pan,
      /* 換手：同一個 id 重新 mount 時，舊實例把面板收走，但開合狀態、搜尋字、捲動位置、焦點留在 MEM 給新的接手。*/
      _detach(handover) {
        if (pan) {
          const keep = { q: mem.q, top: lst ? lst.scrollTop : mem.top, focusQ: document.activeElement === qi, caret: qi ? (qi.selectionStart || 0) : 0 };
          listen(false);
          if (raf) { cancelAnimationFrame(raf); raf = 0; }
          pan.remove(); pan = qi = lst = null;
          Object.assign(mem, keep, { open: !!handover });
        }
        if (REG[id] === api) delete REG[id];
      },
    };
    REG[id] = api;
    paintBtn();
    if (mem.open) open(true);
    return api;
  }

  window.TwMS = {
    mount,
    get: (id) => REG[id] || null,
    closeAll: () => Object.keys(REG).forEach((k) => REG[k].close()),
  };
})();
