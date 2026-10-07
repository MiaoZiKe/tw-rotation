/* ============================================================================
   自選分頁（#watch）—— Andy 2026-09-28：「自選是需要在獨立分頁 在最後一頁，"自選分頁替代"交付清單。
   並且自選分頁是可以至多設定五個分頁可以編輯名稱」

   · 這一支**只做整頁的畫面**。儲存、五頁上限、名字 12 字、每頁 50 檔、登入後雲端同步，全部沿用 site/watchlists.js
     （window.TwWatch，DECISIONS #270）—— 不重寫任何儲存邏輯，所有改動都走 TwWatch 的 API，
     所以「本機 localStorage／登入後雲端」兩條路自動都對。
   · 版面：上面一排清單分頁（最多 5 頁：新增、改名＝雙擊或 ✎、刪除要先確認、桌機可拖曳排序），
     中間一個搜尋框（代號或名稱，Enter 加入第一筆），下面是這一頁的股票表：
     Logo＋名稱＋代號、小走勢（只看不點，2026-10-06 拿掉點了展開大圖）、現價、漲跌幅、成交值、✕ 移除；點一列進個股頁。
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
  let stocks = null, stocksSrc = null, byCode = new Map();

  /* ★ 2026-10-06 根因修正（Andy：自選停在 4 天前）：以前第一次拿到 stocks 就記住、之後永遠用那一份。
     但全站 load() 會「先貼上次存的（IndexedDB 存檔）、網路版到了內容不同再重畫」（app.js Snap／swrSettle）——
     存檔先到時這裡記住的就是**上次開站那天**的現價／漲跌幅，網路版到了重畫也還是舊的，要重新整理才換。
     改成每次都向 load() 要（拿到的就是 App.D 目前那份），換了一份才重建對照表。*/
  function loadStocks() {
    const a = A();
    return (a && a.load ? a.load('stocks', { fallback: [] }) : Promise.resolve([])).then((l) => {
      if (l !== stocksSrc || !stocks) {
        stocksSrc = l;
        stocks = (l || []).filter((r) => r && r.code);
        byCode = new Map(stocks.map((r) => [r.code, r]));
      }
      return stocks;
    });
  }
  /* 小走勢（2026-10-01 改，DECISIONS #282；2026-10-02 v2，DECISIONS #290）：直接用搜尋下拉那一支（App.sparkSVG ＋ data/sparks.json）。
     v2：有 60 分 K 就是最近 5 個交易日每小時（30 點），沒有就是最近 60 日收盤（口徑在 pipeline/compute/sparks.py）；
     有外框、基準虛線、面積、終點圓點，滑上去看期間／起訖／漲跌幅。尺寸用實際像素畫（不要用 CSS 拉伸，圓點會變橢圓）。
     sparks.json 是每次部署產出的靜態檔，不加任何抓取頻率、不碰 mis。*/
  const spkSize = () => (isM() ? { w: 46, h: 20 } : { w: 80, h: 26 });
  function sparkCell(c) {
    const a = A(), z = spkSize(), svg = a && a.sparkSVG ? a.sparkSVG(c, z) : '';
    return `<span class="spkw" data-spk="${esc(c)}" data-w="${z.w}" data-h="${z.h}">${svg}</span>`;
  }

  function injectCSS() {
    if (document.getElementById('wpCss')) return;
    const s = document.createElement('style'); s.id = 'wpCss';
    s.textContent = `
#v-watch .wpcard{margin:0}
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
.wptbl td.nm .t b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wptbl td.nm .t small{margin-left:0}
.wptbl td.nm small{margin-left:6px;color:var(--ink-2);font-size:12px}
.wptbl td.nm .grp{display:block;font-size:12px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis}
.wptbl .del{border:0;background:none;color:var(--ink-2);font-size:15px;cursor:pointer;min-width:32px;min-height:32px}
.wptbl .del:hover{color:#ff6b7a}
.wpempty{padding:28px 12px;text-align:center;color:var(--ink-2);font-size:14px}
.wptbl td.c-sp{width:96px;padding:4px 8px;text-align:center}
/* 2026-10-06（Andy：移除點小走勢圖展開大圖）：小走勢只看不點 —— 不是按鈕、沒有 hover 框；點這一格不換頁也不展開（見 onClick） */
.wpspk{display:inline-flex;align-items:center;justify-content:center;width:88px;height:32px;cursor:default}
.wpspk .spkw{display:inline-flex;align-items:center;justify-content:center;width:80px;height:26px}
.wpspk .spkw:empty::after{content:'—';color:var(--ink-3);font-size:12px}
/* 資料落後（最後一點早於前一交易日）：數字變淡＋虛線底，滑過寫「資料至 MM/DD」；不在畫面上放日期膠囊（DECISIONS #329） */
.wptbl td.wpstale{color:var(--ink-3)!important;text-decoration:underline dotted var(--ink-3);text-underline-offset:3px;cursor:help}
.wpfoot{margin-top:10px;font-size:12px;color:var(--ink-3)}
@media (max-width:640px){
  .wphd h2{font-size:18px}
  .wptab .wpname{max-width:7.5em}
  .wptbl{font-size:14px}
  .wptbl .c-vol{display:none}
  .wptbl td.c-sp{width:52px;padding:4px 2px}
  .wpspk{width:50px}
  .wptbl td.num{padding:8px 3px}
  .wpspk .spkw{width:46px;height:20px}
  .wptbl td,.wptbl th{padding:8px 4px}
  .wptbl td.nm{width:auto;min-width:104px}
  .wptbl td.nm .slogo{display:none}
  .wptbl .del{min-width:28px}
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
    // 休市日（判斷「前一交易日」用）到了再重畫一次落後提示；沒有休市日資料就只跳週末
    if (window.CalGrid && window.CalGrid.load) window.CalGrid.load().then(() => { if (visible()) paintList(); }).catch(() => {});
    { const a = A(); if (a && a.sparkLoad) a.sparkLoad().then(() => { const b = document.getElementById('wpList'); if (b) paintList(); }); }
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
      return `<span class="wptab${on ? ' on' : ''}" data-tab="${esc(t.id)}" draggable="${isM() ? 'false' : 'true'}" title="${esc(t.name)}（${t.codes.length} 檔）">`
        + `<button type="button" class="wpname" role="tab" aria-selected="${on}" data-sel="${esc(t.id)}">${esc(t.name)}<small>${t.codes.length}</small></button>`
        + (on ? `<button type="button" class="wpic ren" data-ren="${esc(t.id)}" aria-label="把「${esc(t.name)}」改名" title="改名">✎</button>`
          + `<button type="button" class="wpic del" data-del-tab="${esc(t.id)}" aria-label="刪除「${esc(t.name)}」這一頁" title="刪除這一頁">✕</button>` : '')
        + '</span>';
    }).join('');
    v.innerHTML = `<div class="card wpcard">
      <div class="wphd"><h2>自選 <button class="howbtn pop" data-how="watch" data-ttl="自選" type="button" aria-label="自選怎麼看">?</button></h2><span class="wpmode" id="wpMode">${esc(mode)}</span><span class="sp"></span><span class="wpcnt" id="wpCnt">${tabs.length}／${T.MAX_TABS} 頁</span></div>
      <div class="wptabs" role="tablist" id="wpTabs">${tabH}
        <button type="button" class="wpnew" id="wpNew" ${full && !(T.capLocked && T.capLocked()) ? 'disabled aria-disabled="true"' : ''} title="${full ? (T.capLocked && T.capLocked() ? `目前方案最多 ${T.MAX_TABS} 頁（需開通）` : `最多 ${T.MAX_TABS} 頁`) : '新增一頁清單'}">＋ 新增分頁${full && T.capLocked && T.capLocked() ? ' 🔒' : ''}</button>
        <span class="wphint" id="wpHint" ${P.hint ? '' : 'hidden'}>${esc(P.hint)}</span></div>
      ${P.confirm ? `<div class="wpconf" id="wpConf"><span>確定刪除「${esc(cur.name)}」（${cur.codes.length} 檔）？</span><button type="button" class="danger" id="wpDelYes">刪除</button><button type="button" id="wpDelNo">取消</button></div>` : ''}
      <div class="wpadd"><input type="search" id="wpQ" placeholder="加入股票：代號或名稱，例如 2330 或 台積電" autocomplete="off" aria-label="搜尋要加入的股票" value="${esc(P.q)}"><ul class="wpres" id="wpRes" hidden></ul></div>
      <div class="wpmsg" id="wpMsg" hidden></div>
      <div id="wpList"></div>
      <div class="howtxt" id="how-watch" hidden></div>
      <div class="wpfoot" title="現價與漲跌幅盤中自動更新；成交值為最近一個交易日盤後">只存代號與清單名稱，不存張數、成本或損益。成交值為盤後數字。</div>
    </div>`;
    paintList();
    const ri = document.getElementById('wpRename');
    if (ri) { ri.focus(); ri.select(); ri.addEventListener('blur', () => finishRename(true)); }
  }

  function paintList() {
    const box = document.getElementById('wpList'), T = W(); if (!box || !T) return;
    const t = T.curTab(), a = A();
    if (!t.codes.length) {
      box.innerHTML = `<div class="wpempty">「${esc(t.name)}」還沒有股票</div>`;
      return;
    }
    const f = a && a.fmt;
    const lag = lagInfo();
    const rows = t.codes.map((c) => {
      const r = byCode.get(c) || { code: c, name: c };
      const cls = f ? f.cls(r.chg_pct) : '';
      // 資料落後（這一列最後一個價早於前一交易日）：不默默顯示舊數字 —— 數字變淡、滑過寫「資料至 MM/DD」
      const old = lag(c), st = old ? ` wpstale" title="資料至 ${esc(old)}（前一交易日的收盤還沒進來）` : '';
      return `<tr data-go="${esc(c)}" tabindex="0"${old ? ` data-stale="${esc(old)}"` : ''}>
        <td class="nm"><div class="in">${a && a.logo ? a.logo(c, r.name, 28) : ''}<div class="t"><b class="wpgo">${esc(r.name || c)}</b><small class="num">${esc(c)}</small>${window.freqBadge ? window.freqBadge(c) : ''}${r.group ? `<span class="grp">${esc(r.group)}</span>` : ''}</div></div></td>
        <td class="c-sp"><span class="wpspk" data-c="${esc(c)}"${old ? ` data-tiphint="資料至 ${esc(old)}"` : ''}>${sparkCell(c)}</span></td>
        <td class="num${st}" data-live="close" data-lc="${esc(c)}">${r.close == null || !f ? '—' : f.n(r.close)}</td>
        <td class="num ${cls}${st}" data-live="chg" data-lc="${esc(c)}">${r.chg_pct == null || !f ? '—' : f.pct(r.chg_pct, 2)}</td>
        <td class="num c-vol">${r.turnover == null || !f ? '—' : f.yi(r.turnover)}</td>
        <td><button type="button" class="del" data-del="${esc(c)}" aria-label="從「${esc(t.name)}」移除 ${esc(r.name || c)}" title="從這一頁移除">✕</button></td></tr>`;
    }).join('');
    box.innerHTML = `<table class="wptbl" id="wpTbl"><thead><tr><th>股票</th><th class="c-sp">走勢</th><th>現價</th><th>漲跌幅</th><th class="c-vol">成交值</th><th><span class="sr" style="position:absolute;left:-9999px">移除</span></th></tr></thead><tbody>${rows}</tbody></table>`;
    if (a && a.logoUpgrade) a.logoUpgrade(box);
  }

  /* 2026-10-06（Andy：「移除點選小走勢圖 出現下方放大走勢跟K線圖功能，並且自選介面需要確保數據是前一天的」）
     ① 點小走勢不再展開（DECISIONS #282 的展開圖、#290 的「展開大圖與小圖逐點相同」整段拿掉）；小走勢照舊顯示、滑過看提示。
     ② 資料落後提示：每一列的「資料日」＝小走勢最後一點的日期（sparks.json 訖日；沒有小走勢就用全站資料日 meta.data_date），
        跟「前一交易日」（台北今天往前找第一個不是週末、不是休市日的日子，休市日讀 tw_holidays.json）比 —— 早於它＝落後。
        落後就把現價／漲跌幅變淡、滑過寫「資料至 MM/DD」，小走勢提示多一行同樣的字；不在畫面上放日期膠囊（DECISIONS #329）。
        為什麼門檻是「前一交易日」而不是「今天」：盤中與 15:30 管線跑完之前，今天的收盤本來就還沒有，那不算落後。*/
  const tpeToday = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);
  function prevTradeDay(today) {
    const C = window.CalGrid, d = new Date(today + 'T00:00:00Z');
    for (let i = 0; i < 20; i++) {
      d.setUTCDate(d.getUTCDate() - 1);
      const k = d.toISOString().slice(0, 10), g = d.getUTCDay();
      if (g === 0 || g === 6) continue;
      if (C && C.holiday && C.holiday(k)) continue;
      return k;
    }
    return '';
  }
  // 'MM/DD' → 'YYYY-MM-DD'（年份取不晚於今天的那一年；跨年 01 月看到 12/31 會退一年）
  function fullDate(md, today) {
    if (!md || md.length < 5) return '';
    let y = +today.slice(0, 4); const k = (yy) => `${yy}-${md.slice(0, 2)}-${md.slice(3, 5)}`;
    if (k(y) > today) y -= 1;
    return k(y);
  }
  function lagInfo() {
    const a = A(), today = tpeToday(), need = prevTradeDay(today);
    const meta = (a && a.D && a.D.meta) || {}, md0 = meta.data_date ? String(meta.data_date).slice(5, 7) + '/' + String(meta.data_date).slice(8, 10) : '';
    return (c) => {
      const sd = a && a.sparkData ? a.sparkData(c) : null, md = (sd && sd.d1) || md0;
      const d = fullDate(md, today);
      return d && need && d < need ? md : '';
    };
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
      /* 2026-10-07：方案上限擋下時 watchlists.js 已經跳出「需升級」卡片（TwWatch.upsell），這裡只留一行提示 */
      if (!id) { setHint(T.capLocked && T.capLocked() ? `🔒 目前方案最多 ${T.MAX_TABS} 頁，升級方案可新增更多` : `最多 ${T.MAX_TABS} 頁`); return; }
      setHint(''); P.editing = id; paint(); return;
    }
    const ad = q('button[data-add]');
    if (ad && !ad.disabled) { T.add(ad.dataset.add); P.q = ''; const i = document.getElementById('wpQ'); if (i) { i.value = ''; i.focus(); } paintRes(); return; }
    const dl = q('button[data-del]'); if (dl) { e.stopPropagation(); T.remove(dl.dataset.del); return; }
    if (q('#wpRename') || q('input')) return;
    if (q('.wpspk')) return;                    // 小走勢只看不點：不展開、也不換頁（2026-10-06 拿掉展開大圖）
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
  /* 會員權限換了（登入、管理者改了上限，DECISIONS #288）：「N／上限 頁」與新增鈕跟著重畫 */
  window.addEventListener('tw:perm', () => { if (visible() && !P.editing) paint(); });
  // watchlists.js 的提示（雲端衝突、放不下）也顯示在這一頁
  window.addEventListener('tw:watchmsg', (e) => { const m = document.getElementById('wpMsg'); if (m) { m.textContent = (e.detail && e.detail.msg) || ''; m.hidden = !m.textContent; } });
  window.TwWatchPage = { render, paint };
})();
