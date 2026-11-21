/* ============================================================================
   台指期策略（原 #futures，Andy 2026-10-28：「台指期也要做成網站頁面」；2026-10-29 搬進交易練習室「台指期」子分頁）
   四塊：今日訊號（F2 台指期 1.3 倍的口數與日程）／前向模擬績效（F2 對 0050 含息）／回測依據（F0～F4 對照）／風險與免責。
   資料 data/futures.json（pipeline/compute/futures_page.py，只讀資料湖 paper/ledger，不另外抓資料）。
   規則說明一律收在標題旁「?」（andy_ui_rules B2）；卡內不重複頁名、不放資料日期在標題（H1）。
   研究用，不是買賣建議，不會下單 —— 免責留在最後一張卡的底部一行。
   由 lab.js 在「台指期」子分頁的第一個區塊呼叫 TwLabFutures.mount(容器)。樣式：site/m4/20261029-lab-futures.css。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const S = { data: null, period: 'all', pts: [] };
  const WD = ['日', '一', '二', '三', '四', '五', '六'];
  const nf = (v, d) => (v == null || Number.isNaN(+v) ? '—' : (+v).toLocaleString('zh-TW', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }));
  const sg = (v, d) => (v == null || Number.isNaN(+v) ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d == null ? 1 : d));
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
  // 2026-11-18 → 「11/18（三）」；日期字串直接當 UTC 算星期，不受瀏覽器時區影響
  const md = (iso) => { if (!iso) return '—'; const [y, m, d] = iso.split('-').map(Number); return `${m}/${d}（${WD[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]}）`; };
  // 結算日前一個「週一到週五」；資料湖不知道未來的休市日，遇國定假日實際日期會順延（寫在「?」裡）
  const prevWeekday = (iso) => { const [y, m, d] = iso.split('-').map(Number); const t = new Date(Date.UTC(y, m - 1, d)); do { t.setUTCDate(t.getUTCDate() - 1); } while (t.getUTCDay() === 0 || t.getUTCDay() === 6); return t.toISOString().slice(0, 10); };

  const hbtn = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}怎麼看">?</button>`;
  const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
  const tile = (l, v, s, c) => `<div class="fu-t ${c || ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div><div class="s" title="${esc(String(s).replace(/<[^>]+>/g, ''))}">${s}</div></div>`;

  function skeleton(root) {
    root.innerHTML = `<div class="fu-wrap" id="fuWrap">
<div class="card" id="fuSigCard">
  <div class="fu-hd"><h3 data-icon="crosshair">今日訊號 ${hbtn('fu-rule', '每月怎麼做')}</h3></div>
  ${how('fu-rule', '永遠持有台指期 1.3 倍，不猜多空、不看均線、不設停損。', [
    '<b>建議曝險</b>＝名目本金的 1.3 倍。口數＝淨值 × 1.3 ÷（台指期收盤 × 每點金額）；大台每點 200 元、微台每點 10 元，這裡以假想本金 1,000 萬元換算。',
    '<b>每月第一個交易日</b>檢查一次口數：實際曝險跟 1.3 倍差超過 0.10 倍才調整，沒超過就不動。',
    '<b>結算前一日轉倉</b>：每月第三個星期三是結算日，前一個交易日把近月換到次月，每次換月多付約 4.5 點成本。日期用「週一到週五」推算，遇國定假日會順延一天。',
    '<b>不擇時、不停損</b>：回測比過「回撤時降到 0.7 倍」與「跌破均線降倍」，都比單純持有差（熔斷在 2009 年後的急速反彈裡是負貢獻），所以不加。',
    '所以：每天只看三件事 —— 現在要幾口、這個月有沒有到檢查日、明後天是不是結算日。其餘什麼都不用做。'])}
  <div class="fu-tiles" id="fuTiles"></div>
</div>
<div class="fu-grid">
  <div class="card" id="fuPerfCard">
    <div class="fu-hd"><h3 data-icon="line">前向模擬績效 ${hbtn('fu-perf', '前向模擬績效')}</h3>
      <div class="seg tiny" id="fuPer" role="tablist" aria-label="期間"></div></div>
    ${how('fu-perf', '這條線是從 2026-10-27 起「照規則做」的假想帳本，不是回測。', [
      '<b>F2</b>＝台指期 1.3 倍，每天盤後算訊號、隔日開盤價成交，已扣手續費、期交稅、滑價與換月成本。',
      '<b>0050 含息</b>＝同日買進、除息金額於除息日再投入，同樣扣成本。',
      '切期間時，起點重設為 0，比的是「那段期間誰多賺」。',
      '所以：要等累積幾個月才有意義；單看幾天的高低沒有參考價值，回測的把握在「五年以上」才成立。'])}
    <div class="fu-tiles k4" id="fuPerfTiles"></div>
    <div class="fu-chart" id="fuChart"></div>
  </div>
  <div class="card" id="fuBtCard">
    <div class="fu-hd"><h3 data-icon="table">回測依據 ${hbtn('fu-bt', '回測依據')}</h3></div>
    ${how('fu-bt', '同一套規則放在過去 20 年，倍數不同結果差多少。', [
      '四個時段的數字＝<b>年化報酬比同期含息 0050 多幾個百分點</b>（正數＝贏）；2017～2020 是附加的一段。',
      '<b>滾動 5 年達標</b>＝任意五年窗口裡，年化贏過 0050 的比例（共 214 個窗口）。',
      '<b>最大回撤</b>＝從高點跌到低點的最大跌幅；全期含 2008，「2009 後」把金融海嘯拿掉。',
      '1.0 倍（F0）在 2015 年後輸 0050；1.5 倍（F3）報酬更高但回撤與風險更大；F4 多了均線這個參數。F2 是「零參數」裡最能撐過各時段的一格。',
      '這是在已被看過的資料上重跑的結果，不是新樣本；2003～2008 的 0050 沒有股利資料、可信度較低。'])}
    <div class="fu-tw"><table class="fu-bt" id="fuBt"></table></div>
    <div class="fu-sc" id="fuScatter"></div>
  </div>
</div>
<div class="card" id="fuRiskCard">
  <div class="fu-hd"><h3 data-icon="scale">風險與免責 ${hbtn('fu-risk', '風險與免責')}</h3></div>
  ${how('fu-risk', '這個策略的風險在帳面回撤，不在被強制平倉。', [
    '回測最大回撤 −69%（含 2008），2009 年後 −39%：槓桿放大了下跌，要能接受帳戶淨值腰斬以上還持續持有。',
    '以 8% 維持保證金率模擬，回測期間沒有被追繳；實際保證金率會隨波動調高，這裡沒有模擬。',
    '2021 年起 1.3 倍的優勢只剩約 2.5 個百分點，若台積電行情消退可能縮小。',
    '期貨有結算、轉倉、保證金與滑價成本，實際成交價可能與帳本不同。',
    '本頁為研究用途，不是買賣建議，不會也不能替你下單。'])}
  <div class="fu-tiles k4" id="fuRiskTiles"></div>
  <div class="fu-foot"><span id="fuDisc"></span></div>
</div>
</div>`;
  }

  function drawSignal() {
    const s = S.data && S.data.signal, el = $('#fuTiles'); if (!el) return;
    if (!s) { el.innerHTML = '<div class="empty" style="grid-column:1/-1">尚無訊號</div>'; el.classList.add('isempty'); return; }
    const roll = s.next_settle ? prevWeekday(s.next_settle) : null;
    el.innerHTML = [
      tile('建議曝險', `${nf(s.target_x, 1)}<small>倍</small>`, '名目本金 × 倍數'),
      tile('大台', `${nf(s.contracts_big, 2)}<small>口</small>`, '每點 200 元・以 1,000 萬計'),
      tile('微台', `${nf(s.contracts_micro, 0)}<small>口</small>`, '每點 10 元・取整數'),
      tile('下次結算日', md(s.next_settle), roll ? `前一日 ${md(roll)} 轉倉` : '—'),
      tile('轉倉提醒', s.roll_tomorrow ? '明天結算' : '今天不用', s.roll_tomorrow ? '請確認近月已換次月' : '結算前一日才換月', s.roll_tomorrow ? 'alert' : ''),
      tile('下次重算口數', md(s.next_check), s.check_tomorrow ? '明天是檢查日' : '每月第一個交易日'),
    ].join('');
  }

  function windowPts() {
    const all = (S.data && S.data.series) || [];
    const per = S.period;
    if (per === 'all' || !all.length) return all;
    const days = { '1m': 31, '3m': 92, '6m': 183 }[per];
    const last = new Date(all[all.length - 1].d + 'T00:00:00Z').getTime();
    return all.filter((p) => last - new Date(p.d + 'T00:00:00Z').getTime() <= days * 86400000);
  }
  // 起點重設為 0：(1+c)/(1+c0)-1
  function rebase(pts) {
    if (!pts.length) return [];
    const f0 = 1 + pts[0].f, b0 = 1 + pts[0].b;
    return pts.map((p) => ({ d: p.d, f: ((1 + p.f) / f0 - 1) * 100, b: ((1 + p.b) / b0 - 1) * 100, nav: p.nav }));
  }

  function drawPeriods() {
    const all = (S.data && S.data.series) || [], seg = $('#fuPer'); if (!seg) return;
    const spanDays = all.length > 1 ? (new Date(all[all.length - 1].d + 'T00:00:00Z') - new Date(all[0].d + 'T00:00:00Z')) / 86400000 : 0;
    const P = [['1m', '1月', 28], ['3m', '3月', 84], ['6m', '6月', 168], ['all', '全部', 0]];
    seg.innerHTML = P.map(([k, t, need]) => {
      const dis = need > spanDays;
      return `<button type="button" role="tab" data-p="${k}" class="${S.period === k ? 'on' : ''}"${dis ? ` disabled title="資料不足：已記錄 ${all.length} 個交易日，需滿 ${t}"` : ''}>${t}</button>`;
    }).join('');
    $$('button[data-p]', seg).forEach((b) => { b.onclick = () => { if (b.disabled) return; S.period = b.dataset.p; drawPeriods(); drawPerf(); }; });
  }

  function drawPerf() {
    const el = $('#fuChart'), tl = $('#fuPerfTiles'); if (!el) return;
    const pts = rebase(windowPts()); S.pts = pts;
    if (!pts.length) { tl.innerHTML = ''; el.innerHTML = ''; A().empty ? A().empty(el, '尚無績效資料') : (el.textContent = '尚無績效資料'); el.classList.add('isempty'); return; }
    el.classList.remove('isempty');
    const last = pts[pts.length - 1], lead = last.f - last.b;
    tl.innerHTML = [
      tile('F2 累積', `<span class="${cls(last.f)}">${sg(last.f, 2)}%</span>`, `${pts.length} 個交易日`),
      tile('0050 含息', `<span class="${cls(last.b)}">${sg(last.b, 2)}%</span>`, '同期、同樣扣成本'),
      tile('領先', `<span class="${cls(lead)}">${sg(lead, 2)}<small>點</small></span>`, 'F2 減 0050'),
      tile('假想淨值', `${nf(last.nav / 10000, 0)}<small>萬</small>`, '本金 1,000 萬'),
    ].join('');
    const CH = A().CH, one = pts.length === 1;
    const line = (name, key, color, w) => ({ name, type: 'line', data: pts.map((p) => +p[key].toFixed(3)), symbol: 'circle', symbolSize: one ? 9 : 5, showSymbol: one || pts.length < 40,
      smooth: false, lineStyle: { width: w, color }, itemStyle: { color },
      areaStyle: key === 'f' ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: A().hexA ? A().hexA(color, 0.28) : color }, { offset: 1, color: A().hexA ? A().hexA(color, 0.02) : color }] } } : undefined,
      markLine: key === 'f' ? { silent: true, symbol: 'none', label: { show: false }, lineStyle: { color: CH.ink3 || CH.ink2, type: 'dashed', width: 1 }, data: [{ yAxis: 0 }] } : undefined });
    A().chart(el, {
      color: [CH.cyan, CH.amber],
      grid: { left: 52, right: 16, top: 36, bottom: 28, containLabel: false },
      legend: { top: 0, left: 0, itemWidth: 14, itemHeight: 3, textStyle: { color: CH.ink2, fontSize: 12 }, data: ['F2 台指期 1.3 倍', '0050 含息'] },
      tooltip: { trigger: 'axis', confine: true, axisPointer: { type: 'line' },
        formatter: (ps) => { const i = ps[0].dataIndex, p = pts[i]; return `<b>${esc(p.d)}</b><br>F2 ${sg(p.f, 2)}%<br>0050 含息 ${sg(p.b, 2)}%<br>差 ${sg(p.f - p.b, 2)} 點`; } },
      xAxis: { type: 'category', data: pts.map((p) => p.d), boundaryGap: pts.length < 3, axisLabel: { color: CH.ink3, fontSize: 12, formatter: (v) => v.slice(5).replace('-', '/') }, axisLine: { lineStyle: { color: CH.line2 || CH.ink3 } }, axisTick: { show: false } },
      yAxis: { type: 'value', scale: true, axisLabel: { color: CH.ink3, fontSize: 12, formatter: (v) => v.toFixed(v % 1 ? 1 : 0) + '%' }, splitLine: { lineStyle: { color: CH.line2 || 'rgba(142,160,196,.2)' } } },
      series: [line('F2 台指期 1.3 倍', 'f', CH.cyan, 2.4), line('0050 含息', 'b', CH.amber, 2)],
    });
  }

  const SHORT = { a: '03-07～14', b: '15～20', c: '21 起', d: '17～20' };   // 欄位窄：全名放 title
  function drawBacktest() {
    const bt = S.data && S.data.backtest, tb = $('#fuBt'); if (!tb) return;
    if (!bt) { tb.innerHTML = ''; return; }
    const g = (v) => `<span class="${cls(v)}">${sg(v, 1)}</span>`;
    const keys = ['a', 'b', 'c', 'd'];
    tb.innerHTML = `<thead>
<tr><th rowspan="2">倍數</th><th colspan="4" class="grp">年化贏 0050 的點數</th><th rowspan="2" title="任意五年窗口年化贏過 0050 的比例">滾動5年<br>達標</th><th rowspan="2" title="全期（含 2008）／2009 後">最大回撤<br>全期／2009後</th></tr>
<tr>${bt.segments.map((s) => `<th title="${esc(s.t)}">${esc(SHORT[s.k] || s.t)}</th>`).join('')}</tr></thead><tbody>${bt.rows.map((r) => `<tr class="${r.pick ? 'pick' : ''}" data-id="${r.id}">
<td title="${esc(r.id)}">${r.id} ${esc(r.name)}</td>${keys.map((k) => `<td>${g(r[k])}</td>`).join('')}
<td>${r.roll5}%</td><td>${r.mdd}%／${r.mdd09}%</td></tr>`).join('')}</tbody>`;
    drawScatter(bt);
  }
  /* 「為什麼選 1.3 倍」的那一張圖：橫軸＝2009 後最大回撤、縱軸＝滾動 5 年達標率。往右上＝又穩又不太痛；F2 是五格裡兩邊都過得去的那一格。 */
  function drawScatter(bt) {
    const el = $('#fuScatter'); if (!el) return;
    const CH = A().CH;
    A().chart(el, {
      grid: { left: 44, right: 24, top: 36, bottom: 34 },
      title: { text: '滾動 5 年達標率（越高越好）對 2009 後最大回撤（越右越小）', left: 0, top: 0, textStyle: { color: CH.ink2, fontSize: 12, fontWeight: 500 } },
      tooltip: { confine: true, formatter: (p) => `<b>${esc(p.data[2])}</b><br>滾動 5 年達標 ${p.data[1]}%<br>2009 後最大回撤 ${p.data[0]}%` },
      xAxis: { type: 'value', min: -50, max: -26, inverse: false, name: '', axisLabel: { color: CH.ink3, fontSize: 12, formatter: '{value}%' }, splitLine: { lineStyle: { color: CH.line2 || 'rgba(142,160,196,.2)' } }, timeGrid: false },
      yAxis: { type: 'value', min: 30, max: 100, axisLabel: { color: CH.ink3, fontSize: 12, formatter: '{value}%' }, splitLine: { lineStyle: { color: CH.line2 || 'rgba(142,160,196,.2)' } } },
      series: [{ type: 'scatter', data: bt.rows.map((r) => ({ value: [r.mdd09, r.roll5, r.id + ' ' + r.name], itemStyle: { color: r.pick ? CH.cyan : CH.violet, borderColor: r.pick ? '#fff' : 'transparent', borderWidth: r.pick ? 2 : 0 }, symbolSize: r.pick ? 18 : 12 })),
        label: { show: true, position: 'right', color: CH.ink, fontSize: 12, formatter: (p) => p.data.value[2].split(' ')[0] } }],
      timeGrid: false,
    });
  }

  function drawRisk() {
    const bt = S.data && S.data.backtest, f2 = bt && bt.rows.find((r) => r.pick), el = $('#fuRiskTiles'); if (!el) return;
    if (f2) el.innerHTML = [
      tile('最大回撤・含 2008', `${f2.mdd}%`, '回測，淨值高點到低點'),
      tile('最大回撤・2009 起', `${f2.mdd09}%`, '回測，不含金融海嘯'),
      tile('10 年內回撤過 −60%', `${f2.pmdd60}%`, '模擬機率'),
      tile('最差五年窗口', `${sg(f2.worst5, 1)}<small>點</small>`, '對 0050 的年化差'),
    ].join('');
    const s = S.data && S.data.signal;
    $('#fuDisc').textContent = `${(S.data && S.data.disclaimer) || '研究用，不是買賣建議，不會下單。'}${s ? ` 資料日期 ${s.date}。` : ''}`;
  }

  let themeBound = false;
  function unmount() {
    ['fuChart', 'fuScatter'].forEach((id) => { const el = document.getElementById(id), c = el && window.echarts && echarts.getInstanceByDom(el); if (c) c.dispose(); });
  }
  async function render(root) {
    root = root || document.getElementById('labFuBox'); if (!root) return;
    skeleton(root);
    let d = null;
    try { d = await A().load('futures', { fallback: null }); } catch (e) { d = null; }
    S.data = d; S.period = 'all';
    if (!d) { root.innerHTML = '<div class="card"><div class="empty">尚無台指期策略資料</div></div>'; root.dataset.ready = 'empty'; return; }
    drawSignal(); drawPeriods(); drawPerf(); drawBacktest(); drawRisk();
    if (!themeBound) { themeBound = true; window.addEventListener('tw:theme', () => { const el = document.getElementById('fuChart'); if (el && el.offsetParent) drawPerf(); }); }
    root.dataset.ready = d.signal ? 'full' : 'empty';
  }
  window.TwLabFutures = { mount: render, unmount, state: S, draw: () => { drawPeriods(); drawPerf(); } };
})();
