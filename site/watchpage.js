/* ============================================================================
   自選分頁（#watch）—— Andy 2026-09-28：「自選是需要在獨立分頁 在最後一頁，"自選分頁替代"交付清單。
   並且自選分頁是可以至多設定五個分頁可以編輯名稱」

   · 這一支**只做整頁的畫面**。儲存、五頁上限、名字 12 字、每頁 50 檔、登入後雲端同步，全部沿用 site/watchlists.js
     （window.TwWatch，DECISIONS #270）—— 不重寫任何儲存邏輯，所有改動都走 TwWatch 的 API，
     所以「本機 localStorage／登入後雲端」兩條路自動都對。
   · 版面：上面一排清單分頁（最多 5 頁：新增、改名＝雙擊或 ✎、刪除要先確認、桌機可拖曳排序），
     中間一個搜尋框（代號或名稱，Enter 加入第一筆），下面是這一頁的股票表：
     Logo＋名稱＋代號、現價、漲跌幅、小走勢（有 sparks 資料才出現）、成交值、✕ 移除；點一列進個股頁。
   · 現價／漲跌幅標了 data-live，盤中即時層（live.js）會直接更新這兩格，跟站上其他表格同一套。
   · 為什麼是新檔：app.js 同時有好幾位 agent 在改（個股頁、搜尋、K 線），整頁 UI 放在自己的檔案裡撞檔面積最小；
     app.js 只多了路由那一行。樣式也由本檔自己注入（同 watchlists.js 的做法）。
   驗收：scripts/_uitest.py「自選獨立分頁」。
   ========================================================================== */
(function () {
  'use strict';
  const W = () => window.TwWatch;
  const A = () => window.App;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const isM = () => window.matchMedia('(max-width: 640px)').matches;
  const P = { editing: null, confirm: false, q: '', hint: '', drag: null };
  let stocks = null, byCode = new Map();

  function loadStocks() {
    if (stocks) return Promise.resolve(stocks);
    const a = A();
    return (a && a.load ? a.load('stocks', { fallback: [] }) : Promise.resolve([])).then((l) => {
      stocks = (l || []).filter((r) => r && r.code);
      byCode = new Map(stocks.map((r) => [r.code, r]));
      return stocks;
    });
  }
  /* 小走勢：另一位 agent 正在做 sparks.json（搜尋下拉用）。這裡**不自己去抓** —— 檔案還沒上線前去抓會 404，
     _preview 會把那一行主控台錯誤當成紅燈。等它被載進 App.D.sparks（搜尋那邊載過一次就有）才畫，沒有就整欄不出現。
     接受兩種形狀：{代號: [收盤…]} 或 {data: {代號: [收盤…]}}。*/
  function sparkOf(code) {
    const a = A(), d = a && a.D && a.D.sparks;
    if (!d || typeof d !== 'object') return null;
    const src = d.data && typeof d.data === 'object' ? d.data : d;
    const v = src[code];
    const arr = Array.isArray(v) ? v : (v && Array.isArray(v.c) ? v.c : null);
    return arr && arr.filter((x) => typeof x === 'number' && isFinite(x)).length >= 2 ? arr.filter((x) => typeof x === 'number' && isFinite(x)) : null;
  }
  function sparkSVG(arr) {
    const w = 72, h = 22, lo = Math.min(...arr), hi = Math.max(...arr), sp = hi - lo || 1;
    const pts = arr.map((v, i) => `${(i / (arr.length - 1) * w).toFixed(1)},${(h - 2 - (v - lo) / sp * (h - 4)).toFixed(1)}`).join(' ');
    const up = arr[arr.length - 1] >= arr[0];
    return `<svg class="wpspark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(${up ? '--rise' : '--fall'})" stroke-width="1.4"/></svg>`;
  }

  function injectCSS() {
    if (document.getElementById('wpCss')) return;
    const s = document.createElement('style'); s.id = 'wpCss';
    s.textContent = `
#v-watch .wpcard{max-width:1100px;margin:0 auto}
.wphd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.wphd h2{margin:0;font-size:20px}
.wphd .wpmode{font-size:13px;color:var(--ink-2)}
.wphd .sp{flex:1}
.wphd .wpcnt{font-size:13px;color:var(--ink-2)}
.wptabs{display:flex;flex-wrap:wrap;gap:6px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:8px}
.wptab{display:inline-flex;align-items:center;gap:2px;height:36px;border:1px solid var(--line-2);border-radius:9px;background:var(--panel-2);color:var(--ink-2);
  font-size:14px;max-width:100%}
.wptab.on{border-color:var(--cyan);color:var(--ink);background:var(--panel-3);font-weight:700}
.wptab.dragover{outline:2px dashed var(--cyan);outline-offset:2px}
.wptab>button{border:0;background:none;color:inherit;font:inherit;cursor:pointer;height:34px;padding:0 6px}
.wptab .wpname{padding:0 4px 0 12px;max-width:11em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wptab .wpname small{margin-left:6px;color:var(--ink-2);font-weight:400;font-size:12px}
.wptab .wpic{font-size:13px;color:var(--ink-2);min-width:28px}
.wptab .wpic:hover{color:var(--cyan)}
.wptab .wpic.del:hover{color:#ff6b7a}
.wptab input{height:30px;width:9em;font-size:14px;border:1px solid var(--cyan);border-radius:7px;background:var(--panel-2);color:var(--ink);padding:0 8px;margin:0 3px}
.wpnew{height:36px;padding:0 12px;border:1px dashed var(--cyan);border-radius:9px;background:none;color:var(--cyan);font-size:14px;cursor:pointer}
.wpnew:disabled{border-color:var(--line-2);color:var(--ink-3);cursor:not-allowed}
.wphint{font-size:12.5px;color:var(--amber)}
.wpconf{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px;padding:8px 10px;border-radius:8px;background:var(--panel-2);font-size:14px}
.wpconf button{height:32px;padding:0 12px;border:1px solid var(--line-2);border-radius:7px;background:var(--panel);color:var(--ink);font-size:13px;cursor:pointer}
.wpconf button.danger{color:#ff6b7a;border-color:rgba(255,107,122,.5)}
.wpadd{position:relative;margin:10px 0 6px;max-width:460px}
.wpadd input{width:100%;box-sizing:border-box;height:38px;font-size:14px;padding:0 12px;border:1px solid var(--line-2);border-radius:9px;background:var(--panel-2);color:var(--ink)}
.wpres{position:absolute;left:0;right:0;top:40px;z-index:20;list-style:none;margin:0;padding:4px 0;background:var(--panel);border:1px solid var(--line-2);border-radius:9px;
  box-shadow:0 10px 30px rgba(0,0,0,.35);max-height:300px;overflow:auto}
.wpres[hidden]{display:none}
.wpres button{display:flex;gap:10px;align-items:center;width:100%;padding:8px 12px;border:0;background:none;color:var(--ink);font-size:14px;cursor:pointer;text-align:left}
.wpres button:hover{background:var(--row-hover)}
.wpres button:disabled{opacity:.55;cursor:default}
.wpres em{margin-left:auto;font-style:normal;color:var(--cyan);font-size:13px}
.wpres .num{color:var(--ink-2)}
.wpmsg{margin:6px 0;padding:6px 10px;border-radius:7px;background:var(--panel-3);font-size:13px}
.wpmsg[hidden]{display:none}
.wptbl{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px}
.wptbl th{font-size:12.5px;color:var(--ink-2);font-weight:600;text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
.wptbl th:first-child{text-align:left}
.wptbl td{padding:8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.wptbl tbody tr{cursor:pointer}
.wptbl tbody tr:hover{background:var(--row-hover)}
.wptbl td.nm{text-align:left;max-width:0;width:40%}
.wptbl td.nm .in{display:flex;align-items:center;gap:8px;min-width:0}
.wptbl td.nm .t{min-width:0;overflow:hidden;text-overflow:ellipsis}
.wptbl td.nm small{margin-left:6px;color:var(--ink-2);font-size:12px}
.wptbl td.nm .grp{display:block;font-size:12px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis}
.wptbl .del{border:0;background:none;color:var(--ink-2);font-size:15px;cursor:pointer;min-width:32px;min-height:32px}
.wptbl .del:hover{color:#ff6b7a}
.wpempty{padding:28px 12px;text-align:center;color:var(--ink-2);font-size:14px}
.wpfoot{margin-top:10px;font-size:12px;color:var(--ink-3)}
@media (max-width:640px){
  .wphd h2{font-size:18px}
  .wptab .wpname{max-width:7.5em}
  .wptbl{font-size:14px}
  .wptbl .c-vol,.wptbl .c-sp{display:none}
  .wptbl td,.wptbl th{padding:8px 4px}
  .wptbl td.nm{width:auto}
  .wpadd{max-width:none}
}`;
    document.head.appendChild(s);
  }

  function el() { return document.getElementById('v-watch'); }
  function visible() { const v = el(); return !!v && v.classList.contains('on'); }

  function render() {
    injectCSS();
    const v = el(); if (!v) return;
    if (!v.dataset.wired) {
      v.dataset.wired = '1';
      v.addEventListener('click', onClick);
      v.addEventListener('dblclick', onDbl);
      v.addEventListener('keydown', onKey);
      v.addEventListener('input', (e) => { if (e.target.id === 'wpQ') { P.q = e.target.value; paintRes(); } });
      v.addEventListener('focusin', (e) => { if (e.target.id === 'wpQ') paintRes(); });
      v.addEventListener('dragstart', onDragStart);
      v.addEventListener('dragover', onDragOver);
      v.addEventListener('dragleave', (e) => { const t = e.target.closest && e.target.closest('.wptab'); if (t) t.classList.remove('dragover'); });
      v.addEventListener('drop', onDrop);
      v.addEventListener('dragend', () => { P.drag = null; v.querySelectorAll('.dragover').forEach((x) => x.classList.remove('dragover')); });
    }
    paint();
    loadStocks().then(() => { paintList(); paintRes(); });
    const a = A(); if (a && a.logoMapLoad) a.logoMapLoad().then(() => { if (a.logoUpgrade) a.logoUpgrade(el()); });
  }

  function paint() {
    const v = el(), T = W(); if (!v || !T) return;
    const tabs = T.tabs(), cur = T.curTab();
    const acctOn = !!(window.TwAccount && window.TwAccount.on && window.TwAccount.on());
    const mode = T.mode() === 'cloud' ? '已同步到你的帳號' : (acctOn ? '存在這台裝置（登入後可跨裝置同步）' : '存在這台裝置');
    const full = tabs.length >= T.MAX_TABS;
    const tabH = tabs.map((t) => {
      const on = t.id === cur.id;
      if (P.editing === t.id) {
        return `<span class="wptab on" data-tab="${esc(t.id)}"><input id="wpRename" value="${esc(t.name)}" maxlength="12" aria-label="新的清單名稱"></span>`;
      }
      return `<span class="wptab${on ? ' on' : ''}" data-tab="${esc(t.id)}" draggable="${isM() ? 'false' : 'true'}" title="${esc(t.name)}（${t.codes.length} 檔）${on ? '・雙擊改名' : ''}${isM() ? '' : '・可拖曳排序'}">`
        + `<button type="button" class="wpname" role="tab" aria-selected="${on}" data-sel="${esc(t.id)}">${esc(t.name)}<small>${t.codes.length}</small></button>`
        + (on ? `<button type="button" class="wpic ren" data-ren="${esc(t.id)}" aria-label="把「${esc(t.name)}」改名" title="改名">✎</button>`
          + `<button type="button" class="wpic del" data-del-tab="${esc(t.id)}" aria-label="刪除「${esc(t.name)}」這一頁" title="刪除這一頁">✕</button>` : '')
        + '</span>';
    }).join('');
    v.innerHTML = `<div class="card wpcard">
      <div class="wphd"><h2>自選</h2><span class="wpmode" id="wpMode">${esc(mode)}</span><span class="sp"></span><span class="wpcnt" id="wpCnt">${tabs.length}／${T.MAX_TABS} 頁</span></div>
      <div class="wptabs" role="tablist" id="wpTabs">${tabH}
        <button type="button" class="wpnew" id="wpNew" ${full ? 'disabled aria-disabled="true"' : ''} title="${full ? `最多 ${T.MAX_TABS} 頁` : '新增一頁清單'}">＋ 新增分頁</button>
        <span class="wphint" id="wpHint" ${P.hint ? '' : 'hidden'}>${esc(P.hint)}</span></div>
      ${P.confirm ? `<div class="wpconf" id="wpConf"><span>確定刪除「${esc(cur.name)}」（${cur.codes.length} 檔）？</span><button type="button" class="danger" id="wpDelYes">刪除</button><button type="button" id="wpDelNo">取消</button></div>` : ''}
      <div class="wpadd"><input type="search" id="wpQ" placeholder="加入股票：代號或名稱，例如 2330 或 台積電" autocomplete="off" aria-label="搜尋要加入的股票" value="${esc(P.q)}"><ul class="wpres" id="wpRes" hidden></ul></div>
      <div class="wpmsg" id="wpMsg" hidden></div>
      <div id="wpList"></div>
      <div class="wpfoot">只存股票代號與清單名稱，不存張數、成本或損益。點一列進個股頁；現價與漲跌幅盤中會自動更新，成交值是最近一個交易日盤後的數字。</div>
    </div>`;
    paintList();
    const ri = document.getElementById('wpRename');
    if (ri) { ri.focus(); ri.select(); ri.addEventListener('blur', () => finishRename(true)); }
  }

  function paintList() {
    const box = document.getElementById('wpList'), T = W(); if (!box || !T) return;
    const t = T.curTab(), a = A();
    if (!t.codes.length) {
      box.innerHTML = `<div class="wpempty">「${esc(t.name)}」還沒有股票。用上面的搜尋框打代號或名稱加入，或在個股頁按 ☆。</div>`;
      return;
    }
    const f = a && a.fmt;
    const anySpark = t.codes.some((c) => sparkOf(c));
    const rows = t.codes.map((c) => {
      const r = byCode.get(c) || { code: c, name: c };
      const cls = f ? f.cls(r.chg_pct) : '';
      const sp = anySpark ? sparkOf(c) : null;
      return `<tr data-go="${esc(c)}" tabindex="0">
        <td class="nm"><div class="in">${a && a.logo ? a.logo(c, r.name, 28) : ''}<div class="t"><b>${esc(r.name || c)}</b><small class="num">${esc(c)}</small>${r.group ? `<span class="grp">${esc(r.group)}</span>` : ''}</div></div></td>
        <td class="num" data-live="close" data-lc="${esc(c)}">${r.close == null || !f ? '—' : f.n(r.close)}</td>
        <td class="num ${cls}" data-live="chg" data-lc="${esc(c)}">${r.chg_pct == null || !f ? '—' : f.pct(r.chg_pct, 2)}</td>
        ${anySpark ? `<td class="c-sp">${sp ? sparkSVG(sp) : ''}</td>` : ''}
        <td class="num c-vol">${r.turnover == null || !f ? '—' : f.yi(r.turnover)}</td>
        <td><button type="button" class="del" data-del="${esc(c)}" aria-label="從「${esc(t.name)}」移除 ${esc(r.name || c)}" title="從這一頁移除">✕</button></td></tr>`;
    }).join('');
    box.innerHTML = `<table class="wptbl" id="wpTbl"><thead><tr><th>股票</th><th>現價</th><th>漲跌幅</th>${anySpark ? '<th class="c-sp">走勢</th>' : ''}<th class="c-vol">成交值</th><th><span class="sr" style="position:absolute;left:-9999px">移除</span></th></tr></thead><tbody>${rows}</tbody></table>`;
    if (a && a.logoUpgrade) a.logoUpgrade(box);
  }

  function paintRes() {
    const ul = document.getElementById('wpRes'), T = W(); if (!ul || !T) return;
    const k = (P.q || '').trim().toUpperCase(), have = new Set(T.curTab().codes);
    const hit = !k || !stocks ? [] : stocks.filter((r) => r.code.startsWith(k) || String(r.name || '').toUpperCase().includes(k)).slice(0, 8);
    ul.innerHTML = hit.map((r) => `<li><button type="button" data-add="${esc(r.code)}" ${have.has(r.code) ? 'disabled' : ''}><span class="num">${esc(r.code)}</span><b>${esc(r.name)}</b><em>${have.has(r.code) ? '已在這頁' : '＋ 加入'}</em></button></li>`).join('')
      || (k && stocks ? '<li class="wpempty" style="padding:10px">找不到這個代號或名稱</li>' : '');
    ul.hidden = !ul.innerHTML;
    if (!ul.hidden) {
      const a = A();
      if (a && a.dismissable) a.dismissable(ul, () => { ul.hidden = true; }, { also: [document.getElementById('wpQ')] });
    }
  }

  function setHint(h) { P.hint = h; const e = document.getElementById('wpHint'); if (e) { e.textContent = h; e.hidden = !h; } }
  function finishRename(save) {
    const ri = document.getElementById('wpRename'); if (!ri || !P.editing) return;
    const id = P.editing, v = ri.value; P.editing = null;
    if (save && v.trim()) W().rename(id, v); else paint();
  }
  function go(c) { location.hash = '#stock/' + c; }

  function onClick(e) {
    const T = W(); if (!T) return;
    const q = (s) => e.target.closest(s);
    const sel = q('button[data-sel]');
    if (sel) { P.confirm = false; setHint(''); if (sel.dataset.sel !== T.cur()) T.setCur(sel.dataset.sel); return; }
    const ren = q('button[data-ren]'); if (ren) { P.editing = ren.dataset.ren; paint(); return; }
    const dt = q('button[data-del-tab]'); if (dt) { P.confirm = true; paint(); return; }
    if (q('#wpDelNo')) { P.confirm = false; paint(); return; }
    if (q('#wpDelYes')) { P.confirm = false; T.delTab(T.cur()); return; }
    if (q('#wpNew')) {
      const id = T.newTab('');
      if (!id) { setHint(`最多 ${T.MAX_TABS} 頁，要新增請先刪掉一頁`); return; }
      setHint(''); P.editing = id; paint(); return;
    }
    const ad = q('button[data-add]');
    if (ad && !ad.disabled) { T.add(ad.dataset.add); P.q = ''; const i = document.getElementById('wpQ'); if (i) { i.value = ''; i.focus(); } paintRes(); return; }
    const dl = q('button[data-del]'); if (dl) { e.stopPropagation(); T.remove(dl.dataset.del); return; }
    if (q('#wpRename') || q('input')) return;
    const tr = q('tr[data-go]'); if (tr) go(tr.dataset.go);
  }
  function onDbl(e) {
    const b = e.target.closest('button[data-sel]'); if (!b) return;
    e.preventDefault(); P.editing = b.dataset.sel; if (b.dataset.sel !== W().cur()) W().setCur(b.dataset.sel); paint();
  }
  function onKey(e) {
    if (e.target.id === 'wpRename') {
      if (e.key === 'Enter') { e.preventDefault(); finishRename(true); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finishRename(false); }
      return;
    }
    if (e.target.id === 'wpQ') {
      if (e.key === 'Enter') { e.preventDefault(); const b = document.querySelector('#wpRes button[data-add]:not([disabled])'); if (b) b.click(); }
      else if (e.key === 'Escape') { const u = document.getElementById('wpRes'); if (u) u.hidden = true; }
      return;
    }
    const tr = e.target.closest && e.target.closest('tr[data-go]');
    if (tr && e.key === 'Enter' && e.target === tr) go(tr.dataset.go);
  }
  // 拖曳排序（桌機）：把分頁拖到另一個分頁上＝排到它的位置
  function onDragStart(e) {
    const t = e.target.closest && e.target.closest('.wptab[draggable="true"]'); if (!t) return;
    P.drag = t.dataset.tab;
    try { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', P.drag); } catch (x) { /* 略 */ }
  }
  function onDragOver(e) {
    const t = e.target.closest && e.target.closest('.wptab'); if (!t || !P.drag || t.dataset.tab === P.drag) return;
    e.preventDefault(); t.classList.add('dragover');
  }
  function onDrop(e) {
    const t = e.target.closest && e.target.closest('.wptab'); if (!t || !P.drag) return;
    e.preventDefault();
    const T = W(), to = T.tabs().findIndex((x) => x.id === t.dataset.tab);
    if (to >= 0 && T.moveTab) T.moveTab(P.drag, to);
    P.drag = null;
  }

  window.addEventListener('tw:watch', () => { if (visible() && !P.editing) paint(); });
  // watchlists.js 的提示（雲端衝突、放不下）也顯示在這一頁
  window.addEventListener('tw:watchmsg', (e) => { const m = document.getElementById('wpMsg'); if (m) { m.textContent = (e.detail && e.detail.msg) || ''; m.hidden = !m.textContent; } });
  window.TwWatchPage = { render, paint };
})();
