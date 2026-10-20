/* ==================================================================================
   市場明細「大盤融資維持率」（2026-10-20，Andy 範本「大盤融資維持率 圖3-5」）  #market/margin  data-snap="margin"
   資料 data/market_fut.json（pipeline/compute/mktfut.py，只讀資料湖）。
   寫成獨立檔、app.js 只留兩個接點（MKT 分頁清單＋drawMarket 的派工一行），跟別人同時改市場明細時衝突最少。
   紅漲綠跌（--rise／--fall）。圖照圖表庫 C 款（直條）與折線；週期鈕＝近 30／60／120 日。
   ================================================================================== */
(function () {
  const KINDS = { credit: '信用交易' };
  const SNAP = { credit: 'margin' };
  const st = { days: 126, who: 'foreign', view: 'bal', tab: 'mkt' };
  let H = null, DATA = null, META = null;
  const txColor = () => (document.documentElement.getAttribute('data-theme') !== 'light' ? '#E2E8F0' : '#0F172A');

  const css = (v, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || d; } catch (e) { return d; } };
  const num = (v, d = 0) => (v == null || Number.isNaN(v)) ? '—' : Number(v).toLocaleString('zh-TW', { minimumFractionDigits: d, maximumFractionDigits: d });
  const sg = (v, d = 0) => (v == null || Number.isNaN(v)) ? '—' : (v > 0 ? '+' : '') + num(v, d);
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
  const md = (d) => String(d || '').slice(5);
  const tail = (rows) => (st.days ? rows.slice(-st.days) : rows);

  const HOWS = {
    credit: `<b>信用交易（大盤融資維持率）怎麼看</b><br>融資＝向券商借錢買股票。<b>維持率 ＝ 融資股票總市值 ÷ 融資總餘額 × 100%</b>：數字越高，整體融資部位的安全墊越厚；越接近 130%，越多帳戶面臨追繳。<br>
      · <b>為何是估算</b>：證交所自 2026/07/29 起暫停公布官方整體維持率，這裡自行推算。<br>· <b>算法</b>：融資股票總市值 ＝ Σ(上市個股融資餘額張數 × 1000 × 當日收盤價)（資料湖 margin_daily＋日收價）；融資總餘額＝整體市場融資金額（FinMind 整體市場融資融券 MarginPurchaseMoney）。<br>
      · <b>限制</b>：這是整個上市市場的估算，<b>不是證交所法定的整戶擔保維持率</b>（那需要每戶的借款與擔保品，沒有公開逐戶資料）；只含上市，不含上櫃；融資成本與市值的時間差、當日資料到齊前的日子（不足八成檔數）不收。<br>
      <br><b>大盤融資維持率是什麼？</b> 向券商借錢買股票（融資）時，股票現值對借款的比例。比例越高越安全；大盤整體的數字能看出槓桿部位的「安全墊」還剩多厚。<br><b>130% 追繳門檻是什麼意思？</b> 個別融資帳戶的擔保品現值跌到借款的 130% 以下，券商會通知補錢（追繳），補不上就可能被強制賣出。這條線是個別帳戶的規則；大盤整體數字接近 130% 不代表全面斷頭，因為各戶成本不同（圖上虛線）。<br><b>和證交所公布的維持率一樣嗎？</b> 不一樣。這裡用「上市個股融資餘額 × 收盤價」除以融資總餘額估算整個市場；證交所的整戶擔保維持率要有每戶的借款與擔保品，沒有公開的逐戶資料，所以只能當趨勢參考。想看個股層級請到<a href="#stock">個股頁</a>看融資融券。<br>      · 130% 是個別帳戶追繳線，大盤數字接近它不代表全面斷頭。融資增加標紅、減少標綠（台股慣例）。資料來源：證交所（OpenAPI／FinMind）、資料日期見標題旁。`,
  };

  function howBtn(kind) {
    return `<button class="howbtn pop" data-how="mf-${kind}" data-ttl="${KINDS[kind]}" type="button" aria-label="${KINDS[kind]}怎麼看">?</button>`
      + `<div class="howtxt" id="how-mf-${kind}" hidden><div class="howbody">${HOWS[kind]}</div></div>`;
  }
  const seg = (id, items, cur) => `<div class="seg tiny" id="${id}" role="group">${items.map(([k, l]) =>
    `<button type="button" data-k="${k}" class="${String(k) === String(cur) ? 'on' : ''}">${l}</button>`).join('')}</div>`;
  const tile = (label, val, sub, c) => `<div class="mf-tile"><span class="mf-l">${label}</span><b class="mf-v ${c || ''}">${val}</b><span class="mf-s ${c || ''}">${sub || ''}</span></div>`;
  const empty = (msg) => `<div class="empty">${msg}</div>`;

  function shell(kind, title, sub, ctl, inner, asof) {
    return `<div class="card mf-card" data-snap="${SNAP[kind]}" id="mf-${kind}">
      <div class="row spread mf-head"><h3 style="margin:0">${title} <small class="mf-asof">${asof ? '資料日期 ' + asof : '資料累積中'}</small> ${howBtn(kind)}</h3>
        <div class="mf-ctl">${ctl}</div></div>
      <div class="muted mf-sub">${sub}</div>${inner}</div>`;
  }
  const dayCtl = () => seg('mfDays', [[30, '30日'], [60, '60日'], [120, '120日']], st.days);

  function table(head, rows) {
    return `<div class="tw mf-tbl"><table><thead><tr>${head.map((h, i) => `<th class="${i ? '' : 'l'}">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }

  /* ---------------- 大盤融資維持率（Andy 10-20 範本「大盤融資維持率 圖3-5」） ---------------- */
  const sortSt = { k: 'd', dir: -1 };
  function linkCharts(body, cs, getDates) {
    // 圖與圖、圖與明細表連動（style_guide §18）：滑過任一張圖 → 另一張同一天出提示、表格那天 .hl；點一下＝鎖定那天（.lk），再點取消
    if (typeof echarts === 'undefined') return;
    const inst = cs.filter(Boolean);
    inst.forEach(c => { c.group = 'mfgrp'; });
    try { echarts.connect('mfgrp'); } catch (e) { /* 舊版沒有也不影響單張 */ }
    const rowOf = (d) => body.querySelector(`#mfTbl tr[data-d="${d}"]`);
    const clear = (cls0) => body.querySelectorAll('#mfTbl tr.' + cls0).forEach(r => r.classList.remove(cls0));
    let locked = null;
    const dts = () => getDates();
    const hl = (d) => { clear('hl'); if (d) { const r = rowOf(d); if (r) { r.classList.add('hl'); const box = r.closest('.mf-scroll'); if (box) { const t = r.offsetTop - box.clientHeight / 2; box.scrollTop = Math.max(0, t); } } } };
    inst.forEach(c => {
      c.on('updateAxisPointer', (e) => { const x = e.axesInfo && e.axesInfo[0]; if (x && x.value != null) hl(typeof x.value === 'number' ? dts()[x.value] : dts().find(d => md(d) === x.value)); });
      c.getZr().on('globalout', () => hl(locked));
      c.getZr().on('click', (ev) => { const p = [ev.offsetX, ev.offsetY]; if (!c.containPixel('grid', p)) { locked = null; clear('lk'); return; }
        const idx = c.convertFromPixel({ gridIndex: 0 }, p)[0]; const d = dts()[Math.round(idx)];
        clear('lk'); if (locked === d) { locked = null; return; } locked = d; const r = rowOf(d); if (r) r.classList.add('lk'); });
    });
    body.querySelectorAll('#mfTbl tr[data-d]').forEach(tr => {
      tr.onmouseenter = () => { const i = dts().indexOf(tr.dataset.d); inst.forEach(c => { try { c.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: i }); } catch (e) { /* 圖已換掉 */ } }); hl(tr.dataset.d); };
      tr.onmouseleave = () => hl(locked);
    });
  }
  function rankList(title, list, cls0) {
    return `<div class="mf-rank"><b class="${cls0}">${title}</b>${list.length ? list.map((r, i) => `<a class="mf-rk" href="#stock/${r.code}" title="到個股頁看融資融券"><span class="mf-n">${i + 1}</span><span class="mf-nm">${r.code} ${H.fmt.esc(r.name || '')}</span><span class="num ${cls(r.chg)}">${sg(r.chg / 1000, 2)} 千張</span></a>`).join('') : '<span class="muted">—</span>'}</div>`;
  }
  const grpSel = new Set();
  function paintRank(body, rk) {
    const box = body.querySelector('#mfRankBody'); if (!box || !rk) return;
    const rs = (rk.rows || []).filter(r => !grpSel.size || (r.g || []).some(g => grpSel.has(g)));
    const up = rs.filter(r => r.chg > 0).sort((a, b) => b.chg - a.chg).slice(0, 8), dn = rs.filter(r => r.chg < 0).sort((a, b) => a.chg - b.chg).slice(0, 8);
    box.innerHTML = rankList('增加 Top 8', up, 'up') + rankList('減少 Top 8', dn, 'down');
  }
  function wireRank(body, rk) {
    const dd = body.querySelector('#mfGroupDD'); if (!dd || !rk || !H.msDD) return;
    const cnt = {}; (rk.rows || []).forEach(r => (r.g || []).forEach(g => { cnt[g] = (cnt[g] || 0) + 1; }));
    const names = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a]);
    let ms;
    const sync = () => { ms.sync({ rows: names.map(n => ({ name: n, on: grpSel.has(n), color: css('--cat-1', '#4cc9f0'), val: cnt[n] + ' 檔' })),
      count: `共 ${names.length} 個族群 · 已選 ${grpSel.size} 個（不選＝全市場）`, label: grpSel.size ? `已選 ${grpSel.size} 個` : '全市場', n: grpSel.size }); paintRank(body, rk); };
    ms = H.msDD(dd, { menu: { rf: 'market', kind: 'mfgroup' },
      onToggle: (c) => { if (c.checked) grpSel.add(c.dataset.n); else grpSel.delete(c.dataset.n); sync(); },
      onAll: (vis) => { (vis || names).forEach(n => grpSel.add(n)); sync(); },
      onNone: (vis) => { (vis || names).forEach(n => grpSel.delete(n)); sync(); } });
    sync();
  }
  const MCOLS = [['d', '日期', r => r.d, 'l'], ['ratio', '維持率', r => num(r.ratio, 2) + '%', ''], ['margin_lots', '融資餘額(張)', r => num(r.margin_lots), ''],
    ['margin_chg', '資增減', r => sg(r.margin_chg), 'chg'], ['margin_yi', '融資金額(億)', r => num(r.margin_yi, 0), ''], ['short_lots', '融券餘額', r => num(r.short_lots), ''], ['short_chg', '券增減', r => sg(r.short_chg), 'chg']];

  function drawMargin(body) {
    const m = (DATA && DATA.margin) || {}, all = m.rows || [];
    if (!all.length) { body.innerHTML = shell('credit', '信用交易', '上市融資維持率（估算）、融資融券餘額與加權指數', '', empty('資料累積中：雲端管線抓到第一批資料後會出現在這裡'), null); return; }
    const last = all[all.length - 1], prev = all[all.length - 2] || {};
    const dlt = (a, b) => (a != null && b != null) ? a - b : null;
    const dr = dlt(last.ratio, prev.ratio), dY = dlt(last.margin_yi, prev.margin_yi);
    const dayStale = !!(META && META.data_date && last.d && last.d < META.data_date);
    const hero = `<div class="mf-top"><div class="mf-big"><span class="mf-l">上市融資維持率（估算）<b class="mf-d">${last.d}</b></span><b class="mf-bn ${cls(dr)}">${last.ratio == null ? '—' : num(last.ratio, 2) + '%'}</b>
        <span class="${cls(dr)}">較前日 ${dr == null ? '—' : sg(dr, 2) + ' pp'}</span></div>`;
    const tiles = `<div class="mf-tiles">` + tile('融資餘額（億元）', num(last.margin_yi, 0), '', '')
      + tile('較前日（億元）', sg(dY, 0), '', cls(dY))
      + tile('融券餘額（張）', num(last.short_lots), '', '')
      + tile('融券增減（張）', sg(last.short_chg), '', cls(last.short_chg)) + `</div></div>`;
    const sorted = all.slice().sort((a, b) => { const x = a[sortSt.k], y = b[sortSt.k]; return ((x == null ? -Infinity : x) > (y == null ? -Infinity : y) ? 1 : -1) * sortSt.dir; });
    const tb = `<div class="tw mf-scroll"><table id="mfTbl"><thead><tr>${MCOLS.map(c => `<th class="${c[3] === 'l' ? 'l' : ''} mf-sort${sortSt.k === c[0] ? ' on' : ''}" data-s="${c[0]}">${c[1]}${sortSt.k === c[0] ? (sortSt.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${
      sorted.map(r => `<tr data-d="${r.d}">${MCOLS.map(c => `<td class="${c[3] === 'l' ? 'l' : 'num'} ${c[3] === 'chg' ? cls(r[c[0]]) : ''}">${c[2](r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    const rk = m.rank;
    const rankHtml = rk ? `<div class="mf-ranks"><h4 style="margin:0 0 6px">個股融資餘額增減排行 <small class="mf-asof">${rk.d}（上市）</small></h4>
        <div class="mf-gsel"><div class="rotdd wide msdd" id="mfGroupDD" data-dd="mfgroup">
          <button type="button" class="ddbtn" aria-haspopup="true" aria-expanded="false" title="只看某些族群的個股">族群：<b>全市場</b><i aria-hidden="true">▾</i></button>
          <div class="ddpanel" aria-label="族群（可複選）" hidden>
            <input type="search" class="sndd-q" placeholder="搜尋族群名稱" aria-label="搜尋族群名稱" autocomplete="off">
            <div class="ddbar"><span class="muted sndd-n"></span><button type="button" class="btn small dd-all">全選</button><button type="button" class="btn small dd-none">全不選</button></div>
            <div class="ddlist"></div></div></div></div>
        <div class="mf-rkgrid" id="mfRankBody"></div></div>` : '';
    const isRank = st.tab === 'rank';
    const bar = `<div class="mf-bar"><div class="seg fp-prod mf-tab" id="mfTab" role="group" aria-label="信用交易分頁"><button type="button" data-k="mkt" class="${isRank ? '' : 'on'}">大盤</button><button type="button" data-k="rank" class="${isRank ? 'on' : ''}">個股排行</button></div>${howBtn('credit')}
        <div class="mf-ctl">${dayStale ? '<span class="mf-stale" title="資料日比最近一個交易日舊，雲端管線還沒更新到">資料未更新</span>' : ''}<span class="mf-asof" style="margin:0">資料日期 ${last.d}</span>${isRank ? '' : seg('mfDays', [[21, '1月'], [63, '3月'], [126, '6月'], [250, '1年'], [750, '3年'], [1250, '5年'], [0, '全部']], st.days)}</div></div>`;
    const mktPane = `${hero}${tiles}<div class="mf-split"><div class="mf-charts">
        <div class="mf-cbox"><h4 class="mf-h">融資維持率 × 加權指數</h4><div id="mfChart" class="chart mf-ch"></div></div>
        <div class="mf-cbox"><h4 class="mf-h">大盤融資餘額 × 加權指數</h4><div id="mfChart2" class="chart mf-ch"></div></div></div>
        <div class="mf-tblbox"><h4 class="mf-h">每日明細 <small class="muted">（點欄名排序・點一列鎖定）</small></h4>${tb}</div></div>`;
    body.innerHTML = `<div class="card mf-card" data-snap="margin" id="mf-credit">${bar}${isRank ? (rankHtml || empty('個股排行資料累積中')) : mktPane}</div>`;
    const paint = () => {
    if (isRank) return [];
    const rows = tail(all);
    const rise = css('--rise', '#ff4d6d'), fall = css('--fall', '#2ee59d'), c1 = '#E11D48', cm = '#0EA5E9', c2 = txColor(), c3 = '#F59E0B', ink = css('--ink-2', '#9aa7c0');
    const xs = { type: 'category', data: rows.map(r => md(r.d)), axisLabel: { hideOverlap: true } };
    const grid = { left: 56, right: 56, top: 30, bottom: 28 }, gl = { lineStyle: { opacity: .15 } };
    const ch1 = H.chart('mfChart', { grid, legend: { top: 0, right: 0, textStyle: { color: ink } }, tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } }, xAxis: xs,
      yAxis: [{ type: 'value', scale: true, min: (v) => Math.floor(Math.min(v.min, 130) - 5), axisLabel: { formatter: v => num(v, 0) + '%' }, splitLine: gl }, { type: 'value', scale: true, axisLabel: { formatter: v => num(v, 0) }, splitLine: { show: false } }],
      series: [{ name: '融資維持率(%)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: c1 }, itemStyle: { color: c1 }, data: rows.map(r => r.ratio),
                 markLine: { silent: true, symbol: 'none', lineStyle: { type: 'dashed', color: ink }, label: { formatter: '130% 個別帳戶追繳線', color: ink, position: 'insideEndTop' }, data: [{ yAxis: 130 }] } },
               { name: '加權指數(右軸)', type: 'line', yAxisIndex: 1, symbol: 'none', lineStyle: { width: 2, color: c2 }, itemStyle: { color: c2 }, data: rows.map(r => r.taiex) }] });
    const ch2 = H.chart('mfChart2', { grid: { left: 56, right: 104, top: 40, bottom: 28 }, legend: { top: 0, left: 'center', textStyle: { color: ink } }, tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } }, xAxis: xs,
      yAxis: [{ type: 'value', scale: true, name: '億元', axisLabel: { formatter: v => num(v, 0) }, splitLine: gl },
              { type: 'value', scale: true, name: '指數', axisLabel: { formatter: v => num(v, 0) }, splitLine: { show: false } },
              { type: 'value', scale: true, name: '融券(張)', offset: 52, axisLabel: { formatter: v => num(v / 1000, 0) + 'K' }, splitLine: { show: false } }],
      series: [{ name: '融資餘額(億元)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: cm }, itemStyle: { color: cm }, data: rows.map(r => r.margin_yi) },
               { name: '加權指數', type: 'line', yAxisIndex: 1, symbol: 'none', lineStyle: { width: 2, color: c2 }, itemStyle: { color: c2 }, data: rows.map(r => r.taiex) },
               { name: '融券餘額(張)', type: 'line', yAxisIndex: 2, symbol: 'none', lineStyle: { width: 2, color: c3 }, itemStyle: { color: c3 }, data: rows.map(r => r.short_lots) }] });
    return [ch1, ch2];
    };
    const cs = paint();
    linkCharts(body, cs, () => tail(all).map(r => r.d));
    wireRank(body, rk); 
    body.querySelectorAll('#mfTab button').forEach(b => b.onclick = () => { if (b.dataset.k === st.tab) return; st.tab = b.dataset.k; render('credit', body); });
    const setDays = (v) => { st.days = v; body.querySelectorAll('#mfDays button').forEach(b => b.classList.toggle('on', +b.dataset.k === v)); paint(); };
    body.querySelectorAll('#mfDays button').forEach(b => b.onclick = () => { setDays(+b.dataset.k); });
    body.querySelectorAll('#mfTbl th[data-s]').forEach(th => th.onclick = () => { const k = th.dataset.s; sortSt.dir = sortSt.k === k ? -sortSt.dir : -1; sortSt.k = k; render('credit', body); });
  }

  (function css0() {
    if (document.getElementById('mfStyle')) return;
    const el = document.createElement('style'); el.id = 'mfStyle';
    el.textContent = `.mf-card{margin:0 0 14px;padding:12px 14px}.mf-head{gap:10px;flex-wrap:wrap}.mf-asof{color:var(--ink-3,#8ea0c4);font-weight:400;margin-left:6px}
.mf-ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.mf-sub{font-size:12.5px;margin:6px 0 10px}
.mf-tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 10px}
.mf-tile{display:flex;flex-direction:column;gap:2px;padding:8px 10px;border:1px solid var(--line,rgba(142,160,196,.2));border-radius:8px;min-width:0}
.mf-l{font-size:12px;color:var(--ink-3,#8ea0c4)}.mf-v{font-size:20px;font-variant-numeric:tabular-nums}.mf-s{font-size:12px}
.mf-tile .up,.mf-bn.up,.mf-rank .up,.mf-rk .up,.mf-big .up,#mfTbl .up{color:var(--rise)}.mf-tile .down,.mf-bn.down,.mf-big .down,.mf-rank .down,#mfTbl .down{color:var(--fall)}.mf-tbl{margin-top:10px}
.mf-hero{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0 0 10px}.mf-big{display:flex;flex-direction:column;gap:3px}.mf-bn{font-size:34px;font-variant-numeric:tabular-nums}.mf-sum{margin:4px 0 0;font-size:13px;color:var(--ink-2,#9aa7c0)}
.mf-how{display:flex;flex-direction:column;gap:4px;padding:10px 12px;border:1px solid var(--line,rgba(142,160,196,.2));border-radius:8px;font-size:13px}
.mf-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:14px}.mf-main{min-width:0}.mf-aside{display:flex;flex-direction:column;gap:8px}
.mf-ex{border:1px solid var(--line,rgba(142,160,196,.2));border-radius:8px;padding:8px 10px;font-size:13px}.mf-ex summary{cursor:pointer;font-weight:600}.mf-more{font-size:13px}
.mf-h{margin:14px 0 6px}.mf-note{font-size:12.5px;margin:2px 0}.mf-card .mf-scroll{max-height:340px!important;overflow:auto!important}.mf-sort{cursor:pointer;user-select:none}.mf-sort.on{color:var(--cat-1)}
/* 2026-10-20 版面：頂端一列（大數字＋四格 KPI）、中間兩圖上下＋明細表右側等高、說明全進「?」、個股排行另一個分頁 */
.mf-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 10px}.mf-bar .mf-ctl{margin-left:auto}.mf-stale{font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;border:1px solid #F59E0B;color:#F59E0B;white-space:nowrap}
.mf-top{display:grid;grid-template-columns:minmax(220px,.8fr) minmax(0,2.2fr);gap:12px;align-items:stretch;margin:0 0 10px}.mf-top .mf-tiles{margin:0}.mf-d{margin-left:8px;font-weight:400;color:var(--ink-3,#8ea0c4)}
.mf-split{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,4fr);gap:12px;align-items:stretch}.mf-charts{display:flex;flex-direction:column;gap:6px;min-width:0}.mf-cbox{min-width:0}
.mf-ch{width:100%;height:clamp(170px,calc((100vh - 400px) / 2),300px)}.mf-split .mf-h{margin:4px 0 4px;font-size:14px}
.mf-tblbox{min-width:0;contain:size;display:flex;flex-direction:column}.mf-split .mf-tblbox .mf-scroll{flex:1 1 0;min-height:0;max-height:none!important}
@media (max-width:900px){.mf-top{grid-template-columns:1fr}.mf-split{display:flex;flex-direction:column}.mf-tblbox{contain:none;display:block}.mf-split .mf-tblbox .mf-scroll{max-height:320px!important}.mf-ch{height:220px}}
#mfTbl tr.hl td{background:rgba(76,201,240,.14)}#mfTbl tr.lk td{background:rgba(76,201,240,.26)}
.mf-ranks{margin-top:14px}.mf-gsel{margin:0 0 8px}.mf-rkgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mf-rank{display:flex;flex-direction:column;gap:4px}
.mf-rk{display:flex;gap:8px;align-items:center;padding:3px 6px;border-radius:6px;text-decoration:none;color:inherit}.mf-rk:hover{background:rgba(142,160,196,.12)}.mf-n{width:16px;color:var(--ink-3,#8ea0c4)}.mf-nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}`;
    document.head.appendChild(el);
  })();

  const DRAW = { credit: drawMargin };

  function wire(kind, body) {
    const on = (id, key) => { const el = body.querySelector('#' + id); if (!el) return;
      el.querySelectorAll('button').forEach(b => b.onclick = () => { const v = b.dataset.k; st[key] = key === 'days' ? +v : v; render(kind, body); }); };
    if (kind !== 'credit') on('mfDays', 'days');
  }
  function render(kind, body) { DRAW[kind](body); wire(kind, body); }

  async function draw(kind, body, title, helpers) {
    H = helpers;
    title.innerHTML = '信用交易';
    body.innerHTML = `<div class="card mf-card"><div class="empty">載入中…</div></div>`;
    try { DATA = await H.load('market_fut', { fallback: {} }); } catch (e) { DATA = {}; }
    try { META = await H.load('meta', { fallback: null }); } catch (e) { META = null; }
    if (!body.isConnected || document.getElementById('mktBody') !== body) return;
    render(kind, body);
  }

  window.TwMktFut = { kinds: KINDS, draw, has: (k) => !!KINDS[k] };
})();
