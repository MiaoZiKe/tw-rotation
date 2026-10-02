/* ============================================================================
   自選分頁（#watch）—— Andy 2026-09-28：「自選是需要在獨立分頁 在最後一頁，"自選分頁替代"交付清單。
   並且自選分頁是可以至多設定五個分頁可以編輯名稱」

   · 這一支**只做整頁的畫面**。儲存、五頁上限、名字 12 字、每頁 50 檔、登入後雲端同步，全部沿用 site/watchlists.js
     （window.TwWatch，DECISIONS #270）—— 不重寫任何儲存邏輯，所有改動都走 TwWatch 的 API，
     所以「本機 localStorage／登入後雲端」兩條路自動都對。
   · 版面：上面一排清單分頁（最多 5 頁：新增、改名＝雙擊或 ✎、刪除要先確認、桌機可拖曳排序），
     中間一個搜尋框（代號或名稱，Enter 加入第一筆），下面是這一頁的股票表：
     Logo＋名稱＋代號、小走勢（點了在下面展開大圖）、現價、漲跌幅、成交值、✕ 移除；點一列進個股頁。
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
  const P = { editing: null, confirm: false, q: '', hint: '', drag: null, exp: null, mode: 'line', tf: '1d' };
  let expK = null, expSeq = 0;   // 展開圖的 KChart 本人（換列／收起要 destroy）、非同步載入的序號（快速連點只畫最後一次）
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
  /* 小走勢（2026-10-01 改，DECISIONS #282）：直接用搜尋下拉那一支（App.sparkSVG ＋ data/sparks.json）——
     分時優先、沒分時用近 20 日收盤，顏色、口徑跟搜尋一模一樣。sparks.json 是每次部署產出的靜態檔，
     不加任何抓取頻率、不碰 mis。App.sparkLoad 對 404 也安靜回空，所以沒有主控台紅字的問題了。*/
  function sparkCell(c) {
    const a = A(), svg = a && a.sparkSVG ? a.sparkSVG(c) : '';
    return `<span class="spkw" data-spk="${esc(c)}">${svg}</span>`;
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
.wpspk{display:inline-flex;align-items:center;justify-content:center;width:88px;height:32px;padding:0;border:1px solid transparent;border-radius:7px;background:none;cursor:pointer}
.wpspk:hover,.wpspk[aria-expanded="true"]{border-color:var(--line-2);background:var(--panel-2)}
.wpspk[aria-expanded="true"]{border-color:var(--cyan)}
.wpspk .spkw{display:inline-flex;width:72px;height:22px}
.wpspk .spk{width:72px;height:22px;display:block;overflow:visible}
.wpspk .spk polyline{fill:none;stroke-width:1.4;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.wpspk .spk.up polyline{stroke:var(--rise)}
.wpspk .spk.down polyline{stroke:var(--fall)}
.wpspk .spk.flat polyline{stroke:var(--ink-3)}
.wpspk .spkw:empty::after{content:'—';color:var(--ink-3);font-size:12px}
.wptbl tr.wpexp{cursor:default}
.wptbl tr.wpexp:hover{background:none}
.wptbl tr.wpexp>td{padding:6px 8px 12px;text-align:left;white-space:normal;background:var(--panel-2)}
.wpxbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px}
.wpxbar .grp{display:inline-flex;border:1px solid var(--line-2);border-radius:8px;overflow:hidden}
.wpxbar button{height:30px;min-width:44px;padding:0 10px;border:0;background:var(--panel);color:var(--ink-2);font-size:13px;cursor:pointer}
.wpxbar button.on{background:var(--panel-3);color:var(--ink);font-weight:700;box-shadow:inset 0 -2px 0 var(--cyan)}
.wpxbar .note{font-size:12px;color:var(--ink-3)}
.wpxc{height:290px;position:relative}
.wpxc .empty{height:100%;display:flex;align-items:center;justify-content:center;color:var(--ink-2);font-size:13px}
.wpfoot{margin-top:10px;font-size:12px;color:var(--ink-3)}
@media (max-width:640px){
  .wphd h2{font-size:18px}
  .wptab .wpname{max-width:7.5em}
  .wptbl{font-size:14px}
  .wptbl .c-vol{display:none}
  .wptbl td.c-sp{width:52px;padding:4px 2px}
  .wpspk{width:50px}
  .wptbl td.num{padding:8px 3px}
  .wpspk .spkw,.wpspk .spk{width:48px;height:18px}
  .wpxc{height:260px}
  .wptbl tr.wpexp>td{padding:6px 4px 10px}
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
    { const a = A(); if (a && a.sparkLoad) a.sparkLoad().then(() => { const b = document.getElementById('wpList'); if (b) b.querySelectorAll('.spkw[data-spk]:empty').forEach((x) => { x.innerHTML = a.sparkSVG(x.dataset.spk); }); }); }
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
    if (P.exp && !t.codes.includes(P.exp)) P.exp = null;
    const rows = t.codes.map((c) => {
      const r = byCode.get(c) || { code: c, name: c };
      const cls = f ? f.cls(r.chg_pct) : '';
      const on = P.exp === c;
      return `<tr data-go="${esc(c)}" tabindex="0"${on ? ' class="on"' : ''}>
        <td class="nm"><div class="in">${a && a.logo ? a.logo(c, r.name, 28) : ''}<div class="t"><b class="wpgo">${esc(r.name || c)}</b><small class="num">${esc(c)}</small>${r.group ? `<span class="grp">${esc(r.group)}</span>` : ''}</div></div></td>
        <td class="c-sp"><button type="button" class="wpspk" data-exp="${esc(c)}" aria-expanded="${on}" aria-label="展開 ${esc(r.name || c)} 的走勢圖" title="點一下在下面展開大圖，再點一次收起">${sparkCell(c)}</button></td>
        <td class="num" data-live="close" data-lc="${esc(c)}">${r.close == null || !f ? '—' : f.n(r.close)}</td>
        <td class="num ${cls}" data-live="chg" data-lc="${esc(c)}">${r.chg_pct == null || !f ? '—' : f.pct(r.chg_pct, 2)}</td>
        <td class="num c-vol">${r.turnover == null || !f ? '—' : f.yi(r.turnover)}</td>
        <td><button type="button" class="del" data-del="${esc(c)}" aria-label="從「${esc(t.name)}」移除 ${esc(r.name || c)}" title="從這一頁移除">✕</button></td></tr>`
        + (on ? expRow(c) : '');
    }).join('');
    killExp();
    box.innerHTML = `<table class="wptbl" id="wpTbl"><thead><tr><th>股票</th><th class="c-sp">走勢</th><th>現價</th><th>漲跌幅</th><th class="c-vol">成交值</th><th><span class="sr" style="position:absolute;left:-9999px">移除</span></th></tr></thead><tbody>${rows}</tbody></table>`;
    if (P.exp) drawExp();
    if (a && a.logoUpgrade) a.logoUpgrade(box);
  }

  /* 展開圖（2026-10-01，Andy：點走勢圖在那一列下方展開放大一點的圖，可切走勢／K 線、K 線要能切週期）。
     同時只展開一列；再點同一格就收起。資料全部走個股頁那條路（Industry.watchBars：stock/<代號>.json、m60/<代號>.json），
     只在使用者點開的那一檔才載，沒有輪詢。
       走勢＝有 60 分 K 就畫最近 5 個交易日的每小時收盤（看得到這週盤中怎麼走），沒有就畫最近 60 日收盤；
       K 線＝KChart（個股頁四週期小圖同一個元件、mini 模式），週期 日／週／1時／4時。*/
  const TFS = [['1d', '日'], ['1w', '週'], ['60m', '1時'], ['240m', '4時']];
  function expRow(c) {
    const mb = (m, t) => `<button type="button" data-xm="${m}" class="${P.mode === m ? 'on' : ''}" aria-pressed="${P.mode === m}">${t}</button>`;
    const tb = TFS.map(([k, t]) => `<button type="button" data-xtf="${k}" class="${P.tf === k ? 'on' : ''}" aria-pressed="${P.tf === k}">${t}</button>`).join('');
    return `<tr class="wpexp" data-exp-row="${esc(c)}"><td colspan="6"><div class="wpxbar"><span class="grp" role="group" aria-label="圖的種類">${mb('line', '走勢')}${mb('k', 'K 線')}</span>`
      + (P.mode === 'k' ? `<span class="grp" role="group" aria-label="K 線週期">${tb}</span>` : '')
      + `<span class="note" id="wpxNote"></span></div><div class="wpxc" id="wpxC"></div></td></tr>`;
  }
  function killExp() {
    if (expK) { try { expK.destroy(); } catch (e) { /* 已銷毀 */ } expK = null; }
    const c = document.getElementById('wpxC');
    if (c && window.echarts) { const i = window.echarts.getInstanceByDom(c); if (i) i.dispose(); }
  }
  async function drawExp() {
    const code = P.exp, box = document.getElementById('wpxC'), note = document.getElementById('wpxNote');
    const I = window.Industry, a = A();
    if (!box || !code) return;
    if (!I || !I.watchBars) { box.innerHTML = '<div class="empty">圖表元件還沒載入，請重新整理</div>'; return; }
    const seq = ++expSeq;
    box.dataset.state = 'loading';
    box.innerHTML = '<div class="empty">載入中…</div>';
    const tf = P.mode === 'k' ? P.tf : '1d';
    const r = await I.watchBars(code, tf);
    if (seq !== expSeq || P.exp !== code || document.getElementById('wpxC') !== box) return;
    killExp(); box.innerHTML = '';
    box.dataset.mode = P.mode; box.dataset.tf = P.mode === 'k' ? tf : '';
    if (P.mode === 'line') {
      let pts, lbl;
      const h = r.h60 || [];
      if (h.length >= 6) {
        const days = [...new Set(h.map((x) => String(x[0]).slice(0, 10)))].slice(-5);
        pts = h.filter((x) => days.includes(String(x[0]).slice(0, 10))).map((x) => [String(x[0]).slice(5, 16).replace('T', ' '), +x[4]]);
        lbl = `最近 ${days.length} 個交易日・每小時收盤`;
      } else {
        pts = (r.daily || []).slice(-60).map((x) => [String(x[0]).slice(5), +x[4]]);
        lbl = `最近 ${pts.length} 個交易日收盤（這檔沒有 1 小時分 K）`;
      }
      if (note) note.textContent = lbl;
      if (pts.length < 2) { box.innerHTML = '<div class="empty">這檔還沒有走勢資料</div>'; box.dataset.state = 'empty'; return; }
      const up = pts[pts.length - 1][1] >= pts[0][1];
      const col = getComputedStyle(document.documentElement).getPropertyValue(up ? '--rise' : '--fall').trim() || (up ? '#ff4d5e' : '#22c55e');
      const vals = pts.map((p) => p[1]);
      const ax = (a && a.axisStyle) || {};
      a.chart(box, {
        animation: false, grid: { left: 8, right: 54, top: 10, bottom: 24, containLabel: false },
        tooltip: { trigger: 'axis', valueFormatter: (v) => (a.fmt ? a.fmt.n(v) : v) },
        xAxis: Object.assign({}, ax, { type: 'category', data: pts.map((p) => p[0]), boundaryGap: false, axisLabel: Object.assign({}, ax.axisLabel || {}, { fontSize: 11, hideOverlap: true, alignMinLabel: 'left', alignMaxLabel: 'right' }) }),
        // scale:true 讓 ECharts 自己挑整數刻度：以前手算 min／max 會在 4,900 底下多冒一個 4,878，兩個標籤疊在一起
        yAxis: Object.assign({}, ax, { type: 'value', position: 'right', scale: true, axisLabel: Object.assign({}, ax.axisLabel || {}, { fontSize: 11 }) }),
        series: [{ type: 'line', data: vals, showSymbol: false, lineStyle: { width: 1.6, color: col }, areaStyle: { color: col, opacity: 0.08 } }],
      });
      box.dataset.n = String(pts.length);
    } else {
      const bars = r.bars || [];
      if (note) note.textContent = bars.length >= 2 ? `${bars.length} 根・滾輪可縮放` : '';
      if (bars.length < 2 || !window.KChart) { box.innerHTML = `<div class="empty">${esc(r.why || '這個週期尚無資料')}</div>`; box.dataset.state = 'empty'; box.dataset.n = '0'; return; }
      expK = new window.KChart(box, { mini: true, tf, fit: (kc) => kc.defaultView() });
      expK.setBars(bars, tf);
      expK.applyIndicators({ ma: [5, 20], vol: true });
      box.dataset.n = String(bars.length);
    }
    box.dataset.state = 'ok';
    box.dataset.seq = String(seq);
  }
  function toggleExp(c) { P.exp = P.exp === c ? null : c; paintList(); }

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
    const sx = q('button[data-exp]'); if (sx) { toggleExp(sx.dataset.exp); return; }
    const xm = q('button[data-xm]'); if (xm) { if (P.mode !== xm.dataset.xm) { P.mode = xm.dataset.xm; paintList(); } return; }
    const xt = q('button[data-xtf]'); if (xt) { if (P.tf !== xt.dataset.xtf) { P.tf = xt.dataset.xtf; paintList(); } return; }
    if (q('tr.wpexp')) return;                  // 展開圖裡面點哪裡都不帶走
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
