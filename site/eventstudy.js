/* ============================================================================
   個股「除息／財報公布前後的歷史走勢」（site/eventstudy.js）—— 2026-11-09 P-1107-06
   ----------------------------------------------------------------------------
   Andy 2026-11-09：「02 05 03 04 06」（五項全做）。
   ★ 法遵審查 docs/feature_proposals/p1107_06_legal_review.md 第四節 R1～R15 是硬性條件、第五節是文案（照抄，不改寫）：
     · 只在個股頁（桌機 #stockTabs「歷史統計」、手機 #mbTabs「歷史統計」），一次只看這一檔；不排行、不篩選、不推播、不進分享圖卡（R1、R9、R10）
     · 每一次事件一個點（分布），附樣本數、期間、上漲次數／共幾次、最好、最差、中位數（R3、R4）
     · 樣本 < 5：不給中位數與上漲次數，只列每一次的原始數字＋「樣本太少，不代表趨勢」（R5）
     · 預設「超額（相對大盤）」，可切「原始」；口徑寫明含息、已還原權值、基準不含息（R6）
     · 財報只用實際公告日，缺的季計入「排除 k 次」（R7）；卡內外不出現下一次事件日期、倒數、行事曆連結（R8）
     · 免責放卡內、數字正下方，字級＝正文（R11）；方法說明進「?」（R12）
     · 不出現「勝率」與禁用字（R2）—— _uitest 段「事件歷史統計1109」掃卡片 innerText
   資料：個股 JSON（data/stock/<代號>.json）的 evstudy 鍵（pipeline/compute/eventstudy.py 寫進去；不另外發請求）。
   功能鍵 stock.eventstudy（features.js）：訪客關、註冊會員／Plus／Pro 同權限（每日 5 檔）；Plus 收費解鎖在律師回覆前不開（R14）。
   沒權限時只畫空殼（鎖頭由 perm.js 蓋在 #stockTab／#mbBody 上），不抓資料。
   ============================================================================ */
(function (root) {
  'use strict';
  const KEY = 'stock.eventstudy';
  const A = () => root.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const can = () => { try { return !root.TwPerm || root.TwPerm.can(KEY); } catch (e) { return true; } };
  const S = { code: null, pg: null, host: null, kind: 'div', win: '5', mode: 'ex', data: null, err: '', wait: null };
  const KINDS = { div: { seg: '除息', title: '除息前後的歷史走勢', ev: '除息', day0: '除息交易日' },
    earn: { seg: '財報公布', title: '財報公布前後的歷史走勢', ev: '財報公布', day0: '財報實際公告日' } };
  const pct = (v) => (v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v * 100).toFixed(2) + '%');
  const ucls = (v) => (v == null ? '' : v > 0 ? 'up' : v < 0 ? 'down' : 'muted');
  const ym = (d) => (d ? d.slice(0, 4) + '/' + d.slice(5, 7) : '—');
  const isEtf = () => /^00/.test(String(S.code || ''));

  function css() {
    if (document.getElementById('esCss')) return;
    const st = document.createElement('style'); st.id = 'esCss';
    st.textContent = `
#esCard .eshd{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap}
#esCard .eshd h3{margin:0}
#esCard .eshd .sp{flex:1}
#esCard .seg button[disabled]{opacity:.42;cursor:not-allowed}
#esCard .esduo{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(380px,1fr);gap:var(--sp-3);align-items:start;margin-top:var(--sp-3)}
#esCard .eschart{height:380px;min-height:380px}
#esCard .essub,#esCard .esbasis,#esCard .esdisc,#esCard .esfew,#esCard .esexcl{font-size:var(--fs-sm);line-height:1.55;margin:0}
#esCard .essub{color:var(--ink)}
#esCard .esbasis,#esCard .esexcl{color:var(--ink-2)}
#esCard .esdisc{color:var(--ink-2);margin-top:var(--sp-2)}
#esCard .esfew{color:var(--amber,#d97706);margin-top:4px}
#esCard .eskpi{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-2);margin:var(--sp-2) 0}
#esCard .eskpi > div{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:6px var(--sp-3);min-width:0;display:flex;align-items:baseline;justify-content:space-between;gap:var(--sp-2)}
#esCard .eskpi .k{display:block;font-size:var(--fs-min);color:var(--ink-2);white-space:nowrap}
#esCard .eskpi b{display:block;font-family:var(--mono);font-size:16px;line-height:1.35;white-space:nowrap}
#esCard .estbl{max-height:150px;overflow:auto;border:1px solid var(--line);border-radius:var(--r-sm);margin-top:var(--sp-2)}
#esCard .estbl table{width:100%;border-collapse:collapse;font-size:var(--fs-sm)}
#esCard .estbl th,#esCard .estbl td{padding:4px var(--sp-2);text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
#esCard .estbl th:first-child,#esCard .estbl td:first-child{text-align:left}
#esCard .estbl th{position:sticky;top:0;background:var(--panel-2);color:var(--ink-2);font-weight:600}
#esCard .estbl td{font-family:var(--mono)}
#esCard .esempty{display:flex;align-items:center;justify-content:center;min-height:200px;color:var(--ink-3);font-size:var(--fs-sm);text-align:center;padding:var(--sp-3)}
@media (max-width:1100px){#esCard .esduo{grid-template-columns:1fr}}`;
    document.head.appendChild(st);
  }

  /* 第五節 5-5「?」方法說明（照抄，〔〕換成這一檔的值） */
  function howItems() {
    const K = KINDS[S.kind], d = S.data, E = d && d[S.kind], w = d ? d.windows.find(x => String(x[1]) === S.win) || [5, 5] : [5, 5];
    const items = [`以${K.day0}為第 0 天，計算第 −${w[0]} 天收盤到第 +${w[1]} 天收盤的報酬`,
      '超額報酬＝個股報酬減同期加權指數報酬',
      '個股股價已還原除權息、含息；加權指數不含息',
      '點越分散，代表每次差異越大；只看中位數或上漲次數會忽略最差的那幾次',
      '資料來源：證交所／櫃買中心公開資料'];
    if (S.kind === 'earn') items.splice(3, 0, `缺實際公告日的季度不納入（本檔排除 ${E ? E.excl : 0} 次）`);
    return items.slice(0, 5);
  }
  const HOW_FINE = '事件窗沒走完、或兩端那天沒有收盤（停牌、尚未上市）的那一次不納入。財報實際公告日取自重大訊息「董事會通過財報」，從本站開始收集那天起累積；法定截止日不是公告日，不拿來代替。期貨、選擇權、權證與槓桿／反向／期貨型 ETF 不納入。';

  function shell(body) {
    const K = KINDS[S.kind];
    const seg = (id, lab, opts, cur) => `<div class="seg" id="${id}" role="group" aria-label="${lab}">${opts.map(o => `<button type="button" data-v="${o[0]}" class="${cur === o[0] ? 'on' : ''}"${o[2] ? ` disabled title="${esc(o[2])}"` : ''}>${o[1]}</button>`).join('')}</div>`;
    const tools = seg('esKind', '事件', [['div', KINDS.div.seg], ['earn', KINDS.earn.seg, isEtf() ? 'ETF 沒有財報公布事件' : '']], S.kind)
      + seg('esWin', '前後幾日', [['5', '前後 5 日'], ['20', '前後 20 日']], S.win)
      + seg('esMode', '報酬口徑', [['ex', '超額（相對大盤）'], ['raw', '原始']], S.mode);
    const how = (A() && A().howHTML) ? A().howHTML('', howItems()) : '';
    return `<div class="card" id="esCard" data-kind="${S.kind}" data-win="${S.win}" data-mode="${S.mode}"><div class="eshd"><h3><span id="esTitle">${K.title}</span> `
      + `<button class="howbtn pop" data-how="skes" data-ttl="${K.title}" type="button" aria-label="${K.title}怎麼算">?</button></h3><span class="sp"></span>${tools}</div>`
      + `<div class="howtxt" id="how-skes" hidden>${how}<p class="muted">${HOW_FINE}</p></div>${body}</div>`;
  }

  /** 掛載點：桌機 industry.js renderTab 的「歷史統計」分頁、手機 mobile3.js 的「歷史統計」分頁 */
  function mount(pg, el) {
    if (!el || !pg || !pg.meta) return;
    css();
    const code = String(pg.meta.code);
    if (code !== S.code) { S.data = null; S.kind = 'div'; S.win = '5'; S.mode = 'ex'; }
    S.code = code; S.pg = pg; S.host = el; S.err = '';
    if (!can()) {
      /* 沒權限：只畫空殼（perm.js 在 #stockTab／#mbBody 蓋鎖頭），不抓資料；權限晚一步回來再掛一次 */
      S.wait = { pg, el };
      el.innerHTML = shell('<div class="esempty">此功能需開通</div>');
      return;
    }
    S.wait = null;
    if (!S.data) load(code); else draw();
  }

  /* 資料就在個股 JSON 裡（data/stock/<代號>.json 的 evstudy 鍵，pipeline/compute/eventstudy.py 寫進去）：不另外發請求。
     2026-11-09 第一版是另外一個資料夾 2,200 支檔，GitHub Pages 部署因檔數卡住，改併進個股 JSON。 */
  function load(code) {
    const d = S.pg && S.pg.evstudy;
    S.data = d && d.code === code ? d : { none: true };
    draw();
  }

  /* 目前這個視窗＋口徑的樣本：[{d, d0, q, v, raw, ex}]（依日期）*/
  function rows() {
    const E = S.data && S.data[S.kind]; if (!E) return [];
    const j = S.mode === 'ex' ? 1 : 0;
    return (E.events || []).filter(e => e.r && e.r[S.win]).map(e => ({ d: e.d, d0: e.d0, q: e.q, v: e.r[S.win][j], raw: e.r[S.win][0], ex: e.r[S.win][1] }));
  }

  function body() {
    const D = S.data;
    if (!D) return '<div class="esempty">讀取中…</div>';
    if (D.none) return '<div class="esempty">這一檔目前沒有可統計的除息或財報公布事件</div>';
    const K = KINDS[S.kind], E = D[S.kind] || { events: [], sum: {} }, sm = (E.sum || {})[S.win] || {}, st = sm[S.mode] || { n: 0, few: true };
    const R = rows(), n = R.length, w = D.windows.find(x => String(x[1]) === S.win) || [5, 5];
    const waiting = (E.pending || 0) + (E.events || []).filter(e => !e.r || !e.r[S.win]).length;
    const few = n < (D.min_n || 5);
    // 5-2 副標
    const sub = n ? `過去 ${n} 次${K.ev}（${ym(R[0].d)}～${ym(R[n - 1].d)}），${K.ev}日前 ${w[0]} 日到後 ${w[1]} 日的報酬，每一個點是一次。`
      : `目前沒有可統計的${K.ev}事件（${K.ev}日前 ${w[0]} 日到後 ${w[1]} 日都要有收盤才算）。`;
    const excl = S.kind === 'earn' ? `<p class="esexcl" id="esExcl">缺實際公告日的季度不納入：本檔排除 ${E.excl || 0} 次${E.excl ? `（${esc(E.excl_from)}～${esc(E.excl_to)}）` : ''}。</p>` : '';
    const wait = waiting ? `<p class="esexcl" id="esWait">另有 ${waiting} 次事件窗還沒走完或缺收盤，不納入。</p>` : '';
    // 5-3 數字列（R3：六格都在；R5：樣本 < 5 時中位數、上漲次數、最好、最差一律「—」）
    const cell = (id, k, v, c) => `<div data-k="${id}"><span class="k">${k}</span><b class="${c || ''}">${v}</b></div>`;
    const kpi = `<div class="eskpi" id="esKpi">${cell('n', '樣本數', n + ' 次')}${cell('per', '期間', n ? ym(R[0].d) + '～' + ym(R[n - 1].d) : '—')}`
      + cell('up', '上漲次數', few ? '—' : `${st.up} 次／共 ${st.n} 次`)
      + cell('med', '中位數', few ? '—' : pct(st.med), few ? '' : ucls(st.med))
      + cell('best', '最好', few ? '—' : pct(st.best), few ? '' : ucls(st.best))
      + cell('worst', '最差', few ? '—' : pct(st.worst), few ? '' : ucls(st.worst)) + '</div>';
    const basis = `<p class="esbasis" id="esBasis">口徑：${S.mode === 'ex' ? '相對加權指數的超額報酬' : '個股本身的報酬（不扣大盤）'}，股價已還原除權息、含息；加權指數不含息。</p>`;
    // 5-4 卡內免責（數字正下方）
    const disc = '<p class="esdisc" id="esDisc">以上是這檔股票過去事件的歷史統計，只描述已經發生的事，<b>不代表下一次會一樣，也不構成任何買賣建議</b>。未計交易成本、稅與滑價；樣本少時參考價值更低。</p>';
    // 5-6 樣本不足
    const fewTxt = few && n ? `<p class="esfew" id="esFew">這檔只有 ${n} 次可統計，樣本太少，不代表趨勢。以下列出每一次的原始數字。</p>` : '';
    const tr = R.slice().reverse().map(r => `<tr><td>${esc(r.d)}${S.kind === 'earn' && r.q ? `（${esc(r.q)}）` : ''}</td><td class="${ucls(r.v)}">${pct(r.v)}</td></tr>`).join('');
    const tbl = n ? `<div class="estbl" id="esTbl"><table><thead><tr><th>${K.ev}日</th><th>${S.mode === 'ex' ? '超額報酬' : '報酬'}</th></tr></thead><tbody>${tr}</tbody></table></div>` : '';
    const chart = n ? '<div id="esChart" class="eschart chart"></div>' : `<div class="esempty eschart" id="esChart0">${K.ev}事件累積到第一次就會畫出來</div>`;
    return `<div class="esduo">${chart}<div class="esside"><p class="essub" id="esSub">${sub}</p>${excl}${fewTxt}${kpi}${basis}${disc}${wait}${tbl}</div></div>`;
  }

  function draw() {
    const el = S.host; if (!el) return;
    el.innerHTML = shell(body());
    const c = $('#esCard', el);
    const wire = (id, k) => c.querySelectorAll('#' + id + ' button').forEach(b => b.addEventListener('click', () => {
      if (b.disabled || S[k] === b.dataset.v) return; S[k] = b.dataset.v; draw(); }));
    wire('esKind', 'kind'); wire('esWin', 'win'); wire('esMode', 'mode');
    drawChart();
  }

  function drawChart() {
    const Ap = A(), R = rows(); if (!Ap || !Ap.chart || !R.length || !document.getElementById('esChart')) return;
    const CH = Ap.CH, D = S.data, st = ((D[S.kind].sum || {})[S.win] || {})[S.mode] || {};
    const few = R.length < (D.min_n || 5);
    const lab = S.mode === 'ex' ? '超額報酬' : '報酬';
    const mk = [{ yAxis: 0, lineStyle: { color: CH.ink3, type: 'solid', width: 1 }, label: { show: false } }];
    if (!few && st.med != null) mk.push({ yAxis: +(st.med * 100).toFixed(3), lineStyle: { color: CH.amber || '#f59e0b', type: 'dashed', width: 1.5 },
      label: { show: true, position: 'end', color: CH.ink2, fontSize: 11, lineHeight: 14, formatter: '中位數\n' + pct(st.med) } });
    Ap.chart('esChart', {
      animation: false,
      tooltip: { ...Ap.tip, trigger: 'item', formatter: (p) => { const r = R[p.dataIndex]; if (!r) return '';
        return `<b>${esc(r.d)}${r.q ? '（' + esc(r.q) + '）' : ''}</b><br>${lab} ${pct(r.v)}<br>個股 ${pct(r.raw)}・加權指數 ${pct(r.raw - r.ex)}`; } },
      grid: { left: 48, right: 62, top: 16, bottom: 32 },
      xAxis: { type: 'category', data: R.map(r => r.d), boundaryGap: true, axisTick: { show: false }, axisLine: { lineStyle: { color: CH.line || '#3b4f7f' } },
        axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT, hideOverlap: true, formatter: (v) => v.slice(0, 7).replace('-', '/') } },
      yAxis: { ...Ap.axisStyle, type: 'value', scale: false, axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT, formatter: (v) => v + '%' } },
      series: [{ name: lab, type: 'scatter', symbolSize: 10, data: R.map(r => ({ value: +(r.v * 100).toFixed(3), itemStyle: { color: r.v > 0 ? CH.up : r.v < 0 ? CH.down : CH.ink3 } })),
        markLine: { silent: true, symbol: 'none', data: mk } }],
    }, { notMerge: true });
  }

  root.addEventListener('tw:perm', () => { const w = S.wait; if (w && can() && document.body.contains(w.el)) mount(w.pg, w.el); });
  root.TwEventStudy = { mount, can, KEY, state: () => ({ code: S.code, kind: S.kind, win: S.win, mode: S.mode, n: rows().length, loaded: !!S.data, none: !!(S.data && S.data.none) }) };
})(window);
