/* ==================================================================================
   信用交易頁「全市場信用風險（官方儀表板）」（2026-11-06，Andy：「每天看儀表板，手動把五個數字（維持率、追繳戶數、追繳金額、
   處分戶數、處分金額）填進網站，並標註來源和日期」）  #market/credit（大盤分頁，接在融資維持率卡下方）
   · 證交所臺股儀表板 https://www.twse.com.tw/dashboard/zh/credit/margin.html 的條款不准自動抓 → 站主人工登錄。
   · 寫成獨立檔：marketfut.js 只在 render() 留一行接點（TwMarginDash.mount），跟同時改信用交易頁的人衝突最少。
   · 閘門：整塊畫在 #mktBody 裡 → 沿用 mkt.credit 的每日次數閘門（features.js veil #mktBody），不另開功能鍵。
   · 資料從哪來（依序）：
       ① 會員 Worker /v1/mdash/get（公開讀；站主寫 /v1/admin/mdash/put、/v1/admin/mdash/del，workers/account-api/margindash.js）
       ② Worker 沒開通（沒設定、端點不存在、連不到）→ 讀 repo 裡的 margin_dashboard_seed.json（Andy 11-05 截圖的兩筆）
          站主在這個模式下按儲存：只存在這台瀏覽器（localStorage tw.mdash.local），表單上明寫「其他人看不到」。
   · 登錄表單只給站主或管理員（跟 livegate／account.js 同一條：/v1/me 的 owner 或 admin）；登入狀態變了（tw:account）當場重畫。
   · 本機驗收：scripts/uitest_sections/20261106_信用風險登錄.py（假的會員 Worker）。
   ================================================================================== */
(function () {
  const URL0 = 'https://www.twse.com.tw/dashboard/zh/credit/margin.html';
  const SRC = '證交所臺股儀表板（人工登錄）';
  const LS = 'tw.mdash.local';
  const F = [
    // [欄位, 卡片名稱, 單位, 小數, 表頭]
    ['mmr', '全市場擔保維持率', '%', 2, '維持率'],
    ['call_n', '追繳戶數', '戶', 0, '追繳戶數'],
    ['call_amt', '追繳金額', '億元', 2, '追繳金額(億)'],
    ['disp_n', '處分戶數', '戶', 0, '處分戶數'],
    ['disp_amt', '處分金額', '億元', 2, '處分金額(億)'],
  ];
  const RULE = {
    mmr: [(v) => v >= 100 && v <= 300, '維持率要介於 100～300'],
    call_n: [(v) => Number.isInteger(v) && v >= 0, '追繳戶數要是 0 以上的整數'],
    disp_n: [(v) => Number.isInteger(v) && v >= 0, '處分戶數要是 0 以上的整數'],
    call_amt: [(v) => v >= 0, '追繳金額不能是負數'],
    disp_amt: [(v) => v >= 0, '處分金額不能是負數'],
  };
  const st = { days: 0, open: false, edit: null, msg: '', tbl: false };
  let cache = null, cacheAt = 0, mode = 'file', ctx = {}, lastBody = null;

  const css = (v, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || d; } catch (e) { return d; } };
  const num = (v, d = 0) => (v == null || Number.isNaN(v)) ? '—' : Number(v).toLocaleString('zh-TW', { minimumFractionDigits: d, maximumFractionDigits: d });
  const sg = (v, d = 0) => (v == null || Number.isNaN(v)) ? '—' : (v > 0 ? '+' : '') + num(v, d);
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
  const md = (d) => String(d || '').slice(5).replace('-', '/');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const dayMs = (d) => Date.parse(d + 'T00:00:00Z');
  const ymd = (ms) => new Date(ms).toISOString().slice(0, 10);

  /** 站主或管理員（跟 livegate.js canLiveUser 同一條規則）。本機驗收另有 TW_MDASH_OVERRIDE（只認 127.0.0.1／localhost）。 */
  function isOwner() {
    try {
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_MDASH_OVERRIDE === true || window.TW_MDASH_OVERRIDE === false)) return window.TW_MDASH_OVERRIDE;
      const A = window.TwAccount; const u = A && typeof A.user === 'function' ? A.user() : null;
      return !!(u && (u.owner === true || u.admin === true));
    } catch (e) { return false; }
  }
  const call = (p, b) => { const A = window.TwAccount; return A && typeof A.call === 'function' ? A.call(p, b) : Promise.resolve(null); };

  /* ---------------- 讀資料 ---------------- */
  const localGet = () => { try { const j = JSON.parse(localStorage.getItem(LS) || 'null'); return j && Array.isArray(j.rows) ? j : null; } catch (e) { return null; } };
  const localSet = (rows) => { try { localStorage.setItem(LS, JSON.stringify({ rows })); return true; } catch (e) { return false; } };
  const sortRows = (rows) => rows.filter((r) => r && /^\d{4}-\d\d-\d\d$/.test(r.d)).sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : 0));
  async function fetchRows(force) {
    if (cache && !force && Date.now() - cacheAt < 60000) return cache;
    let rows = null;
    const j = await call('/v1/mdash/get', {}).catch(() => null);
    if (j && j._s === 200 && Array.isArray(j.rows)) { rows = j.rows; mode = 'server'; }
    if (!rows) {
      mode = 'file';
      try { const r = await fetch('margin_dashboard_seed.json', { cache: 'no-cache' }); if (r.ok) { const s = await r.json(); rows = Array.isArray(s.rows) ? s.rows : []; } } catch (e) { rows = []; }
      // Worker 還沒開通時，站主自己存的那幾筆（只在這台瀏覽器）蓋在種子上面
      const lo = isOwner() ? localGet() : null;
      if (lo) { mode = 'local'; rows = lo.rows; }
    }
    cache = sortRows((rows || []).map((r) => ({ ...r })));
    cacheAt = Date.now();
    return cache;
  }

  /* ---------------- 計算 ---------------- */
  // 某欄最新有值的那一筆、它的前一筆有值、以及「上週同日」（往前 7 天那一天；那天沒登錄就取再往前 3 天內最近的一筆）
  function stat(rows, k) {
    let i = rows.length - 1; while (i >= 0 && rows[i][k] == null) i--;
    if (i < 0) return null;
    const cur = rows[i];
    let p = i - 1; while (p >= 0 && rows[p][k] == null) p--;
    const wk = dayMs(cur.d) - 7 * 86400e3;
    let w = null;
    for (let j = i - 1; j >= 0; j--) { const t = dayMs(rows[j].d); if (t > wk) continue; if (t >= wk - 3 * 86400e3 && rows[j][k] != null) w = rows[j]; break; }
    return { v: cur[k], d: cur.d, dp: p >= 0 ? cur[k] - rows[p][k] : null, pd: p >= 0 ? rows[p].d : null, dw: w ? cur[k] - w[k] : null, wd: w ? w.d : null };
  }
  function lastTradingDay() {
    const m = ctx.meta && ctx.meta.data_date;
    if (m && /^\d{4}-\d\d-\d\d$/.test(m)) return m;
    let t = Date.now() + 8 * 3600e3; let d = new Date(t);
    while (d.getUTCDay() === 0 || d.getUTCDay() === 6) { t -= 86400e3; d = new Date(t); }
    return d.toISOString().slice(0, 10);
  }

  /* ---------------- 畫面 ---------------- */
  const HOW = `<b>全市場信用風險（官方儀表板）怎麼看</b><br>
    這五個數字抄自<a href="${URL0}" target="_blank" rel="noopener">證交所臺股儀表板・信用交易</a>（人工登錄，每筆都標資料日期），口徑是<b>上市＋上櫃、整戶</b>。<br><br>
    <b>全市場擔保維持率</b>：全體信用帳戶「整戶」擔保品市值 ÷ 融資融券借款，由證交所計算公布。跟上面那張「融資維持率（估算）」不同：那張是本站用個股融資餘額 × 收盤價自己推算的趨勢參考，只算融資、不含融券，也不是整戶口徑。<br><br>
    <b>追繳</b>：整戶維持率低於 130%，券商通知投資人在期限內補繳差額。<b>追繳戶數／金額</b>＝當天被通知補繳的戶數與應補金額。<br><br>
    <b>處分</b>：被追繳後沒有在期限內補足，券商把擔保品賣掉（俗稱斷頭）。<b>處分戶數／金額</b>＝當天被處分的戶數與金額。<br><br>
    <b>變化</b>：「較前筆」＝跟前一筆有登錄的日子比；「較上週」＝跟往前 7 天那一天比（那天沒登錄就取再往前 3 天內最近的一筆，都沒有就顯示「—」）。戶數、金額增加標紅、減少標綠（台股慣例）。<br><br>
    <b>最新登錄</b>：儀表板通常盤後公布，最近一個交易日還沒抄進來時，這裡照實寫最新登錄的日期，不會當成今天。`;

  function tiles(rows) {
    return `<div class="md-tiles">${F.map(([k, l, u, d]) => {
      const s = stat(rows, k);
      if (!s) return `<div class="mf-tile md-tile" data-k="${k}"><span class="mf-l">${l}</span><b class="mf-v">—</b><span class="mf-s md-ch">尚未登錄</span></div>`;
      const val = num(s.v, d) + (u === '%' ? '%' : '');
      const unit = u === '%' ? 'pp' : u;
      return `<div class="mf-tile md-tile" data-k="${k}" title="資料日期 ${s.d}・來源：${SRC}"><span class="mf-l">${l}${u === '%' ? '' : `（${u}）`}<small class="md-d">${md(s.d)}</small></span>`
        + `<b class="mf-v">${val}</b>`
        + `<span class="mf-s md-ch"><span class="md-cp ${cls(s.dp)}" title="${s.pd ? '跟 ' + md(s.pd) + ' 比' : '沒有更早的登錄'}">較前筆 ${s.dp == null ? '—' : sg(s.dp, d) + (unit === 'pp' ? ' pp' : '')}</span>`
        + `<span class="md-cw ${cls(s.dw)}" title="${s.wd ? '跟 ' + md(s.wd) + ' 比' : '上週同日沒有登錄'}">較上週 ${s.dw == null ? '—' : sg(s.dw, d) + (unit === 'pp' ? ' pp' : '')}</span></span></div>`;
    }).join('')}</div>`;
  }
  function table(rows, own) {
    const list = rows.slice().reverse();
    const head = `<tr><th class="l">資料日期</th>${F.map((f) => `<th>${f[4]}</th>`).join('')}${own ? '<th>操作</th>' : ''}</tr>`;
    const body = list.length ? list.map((r) => `<tr data-d="${r.d}" title="資料日期 ${r.d}・來源：${SRC}${r.note ? '・備註：' + esc(r.note) : ''}"><td class="l">${md(r.d)}${r.note ? ' <i class="md-nt" aria-label="有備註">註</i>' : ''}</td>${F.map(([k, , u, d]) => `<td class="num">${r[k] == null ? '—' : num(r[k], d) + (u === '%' ? '%' : '')}</td>`).join('')}`
      + (own ? `<td class="md-op"><button type="button" class="btn small md-ed" data-d="${r.d}">修改</button><button type="button" class="btn small md-del" data-d="${r.d}">刪除</button></td>` : '') + `</tr>`).join('')
      : `<tr><td class="l" colspan="${F.length + 1 + (own ? 1 : 0)}">尚無登錄</td></tr>`;
    return `<div class="tw md-scroll"><table id="mdTbl"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
  }
  function form(rows) {
    const e = st.edit ? rows.find((r) => r.d === st.edit) : null;
    const v = (k) => (e && e[k] != null ? e[k] : '');
    const inp = (k, l, ph, im) => `<label class="md-f" data-k="${k}"><span>${l}</span><input type="text" name="${k}" inputmode="${im}" autocomplete="off" placeholder="${ph}" value="${esc(v(k))}"></label>`;
    return `<form class="md-form" id="mdForm" novalidate${st.open ? '' : ' hidden'}>
      <div class="md-fg">
        <label class="md-f" data-k="d"><span>資料日期</span><input type="date" name="d" value="${esc(e ? e.d : lastTradingDay())}" max="2100-12-31" required></label>
        ${inp('mmr', '擔保維持率（%）', '例 159.77', 'decimal')}${inp('call_n', '追繳戶數', '例 2352', 'numeric')}${inp('call_amt', '追繳金額（億元）', '例 26.86', 'decimal')}
        ${inp('disp_n', '處分戶數', '例 222', 'numeric')}${inp('disp_amt', '處分金額（億元）', '例 6.42', 'decimal')}
        <label class="md-f md-fnote" data-k="note"><span>備註（選填）</span><input type="text" name="note" maxlength="120" autocomplete="off" placeholder="例 儀表板 18:00 更新" value="${esc(v('note'))}"></label>
      </div>
      <div class="md-fbar"><button type="submit" class="btn small primary" id="mdSave">${e ? '儲存修改' : '儲存'}</button><button type="button" class="btn small" id="mdCancel">取消</button>
        <span class="md-msg" id="mdMsg" role="status" aria-live="polite"></span></div>
      ${mode !== 'server' ? '<div class="md-warn" id="mdWarn">會員伺服器的登錄功能還沒開通：按儲存只會存在這台瀏覽器，其他訪客暫時看不到。</div>' : ''}
    </form>`;
  }

  function paint(body, rows) {
    const box = body.querySelector('#mdash'); if (!box) return;
    box.querySelectorAll('[_echarts_instance_]').forEach((d) => { try { const i = window.echarts.getInstanceByDom(d); if (i && !i.isDisposed()) i.dispose(); } catch (e) { /* 已收掉 */ } });
    const own = isOwner();
    const last = rows.length ? rows[rows.length - 1].d : null;
    const ltd = lastTradingDay();
    const stale = !last || last < ltd;
    // 期間鈕：照市場明細同款；登錄筆數不足該期間的反灰並寫原因
    const span = rows.length ? (dayMs(last) - dayMs(rows[0].d)) / 86400e3 : 0;
    const DAYS = [[31, '1月'], [92, '3月'], [183, '6月'], [366, '1年'], [0, '全部']];
    const okD = (k) => !k || span >= k * 0.9;
    if (!okD(st.days)) st.days = 0;
    const dayBtns = DAYS.map(([k, l]) => okD(k) ? `<button type="button" data-k="${k}" class="${+k === +st.days ? 'on' : ''}">${l}</button>`
      : `<button type="button" data-k="${k}" disabled aria-disabled="true" title="登錄自 ${rows.length ? md(rows[0].d) : '—'} 起（${rows.length} 筆），不足${l}">${l}</button>`).join('');
    const view = st.days && last ? rows.filter((r) => dayMs(r.d) >= dayMs(last) - st.days * 86400e3) : rows;
    box.dataset.src = mode;
    box.innerHTML = `<div class="mf-bar md-bar"><h4 class="md-ttl">全市場信用風險（官方儀表板）</h4><button class="howbtn pop" data-how="mdash" data-ttl="全市場信用風險" type="button" aria-label="全市場信用風險怎麼看">?</button><div class="howtxt" id="how-mdash" hidden><div class="howbody">${HOW}</div></div>
        <span class="md-last${stale ? ' stale' : ''}" id="mdLast" title="${stale ? '最近交易日 ' + md(ltd) + ' 還沒登錄' : '已登錄到最近交易日'}">最新登錄：${last ? md(last) : '—'}</span>
        <div class="mf-ctl"><span class="md-ok" id="mdOk" role="status">${esc(st.msg)}</span>${own ? `<button type="button" class="btn small primary" id="mdAdd" aria-expanded="${st.open}">${st.open ? '收起登錄' : '＋ 登錄數字'}</button>` : ''}<div class="seg tiny" id="mdDays" role="group" aria-label="期間">${dayBtns}</div></div></div>
      <div class="muted md-sub">來源：<a href="${URL0}" target="_blank" rel="noopener" id="mdSrc">證交所臺股儀表板</a>（人工登錄）</div>
      ${own ? form(rows) : ''}
      ${tiles(rows)}
      <div class="md-split"><div class="md-cbox"><div id="mdChart" class="chart md-chart"></div></div>
        <div class="md-tblbox" data-open="${st.tbl ? 1 : 0}"><button type="button" class="md-tgl" id="mdTgl" aria-expanded="${st.tbl}">每日登錄明細（${rows.length} 筆）<i aria-hidden="true">▾</i></button>${table(view, own)}</div></div>`;
    drawChart(box, view);
    wire(body, box, rows);
  }

  function drawChart(box, rows) {
    const el = box.querySelector('#mdChart'); if (!el || typeof echarts === 'undefined') return null;
    const ink = css('--ink-2', '#9aa7c0');
    const cA = css('--c-short', '#F59E0B'), cB = '#A855F7', cR = css('--c-mgn-ratio', '#E11D48');
    // 維持率軸：範圍窄（例如 157～160）時刻度帶一位小數，不然會出現兩個「160%」
    const mv = rows.map((r) => r.mmr).filter((v) => v != null);
    const rd = mv.length && Math.max(...mv) - Math.min(...mv) < 8 ? 1 : 0;
    const lab = { show: true, position: 'top', fontSize: 12, color: ink, formatter: (q) => (q.value == null || q.value === '' ? '' : num(+q.value, 0)) };
    const opt = {
      grid: { left: 52, right: 60, top: 30, bottom: 26 }, legend: { top: 0, right: 0, textStyle: { color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'category', data: rows.map((r) => md(r.d)), axisLabel: { hideOverlap: true } },
      yAxis: [{ type: 'value', minInterval: 1, axisLabel: { formatter: (v) => num(v, 0) }, splitLine: { lineStyle: { opacity: 0.15 } } },
        { type: 'value', scale: true, axisLabel: { formatter: (v) => num(v, rd) + '%' }, splitLine: { show: false } }],
      series: [
        { name: '追繳戶數(戶)', type: 'bar', barMaxWidth: 28, label: lab, itemStyle: { color: cA, borderRadius: [3, 3, 0, 0] }, data: rows.map((r) => r.call_n) },
        { name: '處分戶數(戶)', type: 'bar', barMaxWidth: 28, label: lab, itemStyle: { color: cB, borderRadius: [3, 3, 0, 0] }, data: rows.map((r) => r.disp_n) },
        { name: '維持率(右軸)', type: 'line', yAxisIndex: 1, connectNulls: true, symbol: 'circle', symbolSize: 7, lineStyle: { width: 2, color: cR }, itemStyle: { color: cR }, data: rows.map((r) => r.mmr) },
      ],
    };
    const c = ctx.chart ? ctx.chart('mdChart', opt) : (() => { const i = echarts.init(el); i.setOption(opt); return i; })();
    // 圖↔表連動（style_guide §18）：滑過圖的某一天 → 明細表那列亮；滑過表的一列 → 圖出那天的提示
    if (c && c.on) {
      const ds = rows.map((r) => r.d);
      const hl = (d) => { box.querySelectorAll('#mdTbl tr.hl').forEach((t) => t.classList.remove('hl')); const tr = d ? box.querySelector(`#mdTbl tr[data-d="${d}"]`) : null; if (tr) tr.classList.add('hl'); };
      c.on('updateAxisPointer', (e) => { const x = e.axesInfo && e.axesInfo[0]; if (x && x.value != null) hl(typeof x.value === 'number' ? ds[x.value] : ds.find((d) => md(d) === x.value)); });
      c.getZr().on('globalout', () => hl(null));
      box.querySelectorAll('#mdTbl tr[data-d]').forEach((tr) => {
        tr.onmouseenter = () => { const i = ds.indexOf(tr.dataset.d); if (i >= 0) try { c.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: i }); } catch (e) { /* 圖已換掉 */ } hl(tr.dataset.d); };
        tr.onmouseleave = () => { try { c.dispatchAction({ type: 'hideTip' }); } catch (e) { /* 圖已換掉 */ } hl(null); };
      });
    }
    return c;
  }

  /* ---------------- 表單 ---------------- */
  function readForm(fm) {
    const fd = new FormData(fm);
    const d = String(fd.get('d') || '').trim();
    const row = { d, note: String(fd.get('note') || '').trim() };
    const errs = [];
    if (!/^\d{4}-\d\d-\d\d$/.test(d) || Number.isNaN(dayMs(d)) || ymd(dayMs(d)) !== d) errs.push(['d', '資料日期格式不對']);
    else if (d > ymd(Date.now() + 8 * 3600e3)) errs.push(['d', '資料日期不能是未來']);
    let n = 0;
    F.forEach(([k]) => {
      const raw = String(fd.get(k) || '').replace(/[,，\s%億元戶]/g, '');
      if (raw === '') { row[k] = null; return; }
      const v = Number(raw);
      if (!/^-?\d+(\.\d+)?$/.test(raw) || !Number.isFinite(v) || !RULE[k][0](v)) { errs.push([k, RULE[k][1]]); return; }
      row[k] = k.endsWith('_n') ? v : Math.round(v * 100) / 100; n++;
    });
    if (!errs.length && !n) errs.push(['mmr', '五個數字至少要填一個']);
    if (row.note.length > 120) errs.push(['note', '備註最多 120 字']);
    return { row, errs };
  }
  async function save(row) {
    if (mode === 'server') {
      const r = await call('/v1/admin/mdash/put', { row });
      if (r && r._s === 200 && Array.isArray(r.rows)) { cache = sortRows(r.rows); cacheAt = Date.now(); return null; }
      return r && r.error ? '伺服器拒絕：' + r.error : '儲存失敗，請稍後再試';
    }
    const rows = (cache || []).filter((x) => x.d !== row.d).concat([row]);
    if (!localSet(sortRows(rows))) return '這台瀏覽器不能存（私密視窗？）';
    cache = sortRows(rows); cacheAt = Date.now(); mode = 'local'; return null;
  }
  async function del(d) {
    if (mode === 'server') {
      const r = await call('/v1/admin/mdash/del', { d });
      if (r && r._s === 200 && Array.isArray(r.rows)) { cache = sortRows(r.rows); cacheAt = Date.now(); return null; }
      return '刪除失敗，請稍後再試';
    }
    const rows = (cache || []).filter((x) => x.d !== d);
    if (!localSet(rows)) return '這台瀏覽器不能存（私密視窗？）';
    cache = rows; cacheAt = Date.now(); mode = 'local'; return null;
  }
  const flash = (body, msg) => { st.msg = msg; paint(body, cache || []); setTimeout(() => { if (st.msg === msg) { st.msg = ''; const o = body.querySelector('#mdOk'); if (o) o.textContent = ''; } }, 4000); };

  function wire(body, box, rows) {
    box.querySelectorAll('#mdDays button').forEach((b) => b.onclick = () => { if (b.disabled) return; st.days = +b.dataset.k; paint(body, rows); });
    const tg = box.querySelector('#mdTgl'); if (tg) tg.onclick = () => { st.tbl = !st.tbl; box.querySelector('.md-tblbox').dataset.open = st.tbl ? 1 : 0; tg.setAttribute('aria-expanded', st.tbl); };
    const add = box.querySelector('#mdAdd');
    if (add) add.onclick = () => { st.open = !st.open; st.edit = null; paint(body, rows); if (st.open) { const i = body.querySelector('#mdForm input[name="mmr"]'); if (i) i.focus(); } };
    const fm = box.querySelector('#mdForm'); if (!fm) return;
    const msg = (t, bad) => { const m = fm.querySelector('#mdMsg'); m.textContent = t; m.classList.toggle('bad', !!bad); };
    const dIn = fm.querySelector('input[name="d"]');
    const dup = () => { const d = dIn.value; msg(d && d !== st.edit && rows.some((r) => r.d === d) ? `${md(d)} 已經登錄過，儲存會覆蓋那天` : ''); };
    dIn.onchange = dup; dup();
    fm.querySelector('#mdCancel').onclick = () => { st.open = false; st.edit = null; paint(body, rows); };
    fm.onsubmit = async (ev) => {
      ev.preventDefault();
      fm.querySelectorAll('.md-f.bad').forEach((x) => x.classList.remove('bad'));
      const { row, errs } = readForm(fm);
      if (errs.length) { errs.forEach(([k]) => { const f = fm.querySelector(`.md-f[data-k="${k}"]`); if (f) f.classList.add('bad'); }); msg(errs.map((e) => e[1]).join('；'), true); return; }
      const btn = fm.querySelector('#mdSave'); btn.disabled = true; msg('儲存中…');
      if (st.edit && st.edit !== row.d) { const e0 = await del(st.edit); if (e0) { btn.disabled = false; msg(e0, true); return; } }   // 修改時改了日期＝搬到新日期
      const e1 = await save(row);
      btn.disabled = false;
      if (e1) { msg(e1, true); return; }
      st.open = false; st.edit = null;
      flash(body, `已儲存 ${md(row.d)}`);
    };
    box.querySelectorAll('.md-ed').forEach((b) => b.onclick = (ev) => { ev.stopPropagation(); st.edit = b.dataset.d; st.open = true; st.tbl = true; paint(body, rows); });
    box.querySelectorAll('.md-del').forEach((b) => b.onclick = async (ev) => {
      ev.stopPropagation();
      if (!b.classList.contains('cf')) { b.classList.add('cf'); b.textContent = '確定刪除？'; setTimeout(() => { if (b.isConnected) { b.classList.remove('cf'); b.textContent = '刪除'; } }, 4000); return; }
      b.disabled = true;
      const e = await del(b.dataset.d);
      if (e) { b.disabled = false; flash(body, e); return; }
      if (st.edit === b.dataset.d) { st.edit = null; st.open = false; }
      flash(body, `已刪除 ${md(b.dataset.d)}`);
    });
  }

  /** marketfut.js 每次重畫信用交易「大盤」分頁後呼叫：在融資維持率卡下方接上這一塊 */
  async function mount(body, opt) {
    ctx = opt || {};
    lastBody = body;
    let box = body.querySelector('#mdash');
    if (!box) { body.insertAdjacentHTML('beforeend', '<div class="card mf-card md-card" id="mdash"><div class="empty">載入中…</div></div>'); box = body.querySelector('#mdash'); }
    const rows = await fetchRows(false);
    if (!box.isConnected) return;
    paint(body, rows);
  }
  window.addEventListener('tw:account', () => { if (lastBody && lastBody.isConnected && lastBody.querySelector('#mdash')) { cache = null; st.open = false; mount(lastBody, ctx); } });

  (function css0() {
    if (document.getElementById('mdStyle')) return;
    const el = document.createElement('style'); el.id = 'mdStyle';
    el.textContent = `.md-card{margin-top:12px}.md-bar{gap:8px}.md-ttl{margin:0;font-size:16px;font-weight:600}
.md-last{font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;border:1px solid var(--line,rgba(142,160,196,.35));color:var(--ink-2,#9aa7c0);white-space:nowrap}
.md-last.stale{border-color:#F59E0B;color:#F59E0B}.md-ok{font-size:12.5px;color:var(--cat-1,#4cc9f0)}.md-sub{font-size:12.5px;margin:-4px 0 8px}.md-sub a{color:var(--cat-1,#4cc9f0)}
.md-tiles{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:0 0 8px}
.md-tile .mf-l{display:flex;gap:6px;align-items:baseline}.md-d{margin-left:auto;font-size:12px;color:var(--ink-3,#8ea0c4)}
.md-ch{display:flex;gap:8px;flex-wrap:wrap}.md-ch .up{color:var(--rise)}.md-ch .down{color:var(--fall)}
.md-split{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,4fr);gap:12px;align-items:stretch}.md-cbox{min-width:0}
.md-chart{width:100%;height:240px}.md-tblbox{min-width:0;display:flex;flex-direction:column}.md-scroll{max-height:240px;overflow:auto}
.md-tgl{display:none}
#mdTbl td,#mdTbl th{text-align:center;white-space:nowrap}#mdTbl td.l,#mdTbl th.l{text-align:left}#mdTbl tr.hl td{background:color-mix(in srgb,var(--cyan,#3ee0ff) 14%,transparent)}
.md-nt{font-style:normal;font-size:11px;padding:0 4px;border-radius:4px;border:1px solid var(--line,rgba(142,160,196,.35));color:var(--ink-3,#8ea0c4)}
.md-op{display:flex;gap:4px;justify-content:center}.md-op .btn{height:24px;padding:0 8px;font-size:12px}.md-del.cf{border-color:var(--rise);color:var(--rise)}
.md-form{border:1px solid var(--cat-1,#4cc9f0);border-radius:8px;padding:12px;margin:0 0 8px}
.md-fg{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 12px}.md-f{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--ink-2,#9aa7c0);min-width:0}
.md-f input{height:32px;padding:0 8px;border-radius:6px;border:1px solid var(--line,rgba(142,160,196,.35));background:transparent;color:inherit;font:inherit;font-size:14px;min-width:0}
.md-f.bad input{border-color:var(--rise)}.md-fnote{grid-column:span 2}
.md-fbar{display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap}.md-msg{font-size:12.5px;color:var(--ink-2,#9aa7c0)}.md-msg.bad{color:var(--rise)}
.md-warn{margin-top:6px;font-size:12px;color:#F59E0B}
@media (max-width:900px) and (min-width:641px){.md-tiles{grid-template-columns:repeat(3,minmax(0,1fr))}.md-split{grid-template-columns:minmax(0,1fr)}.md-fg{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.md-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.md-tiles .md-tile:first-child{grid-column:span 2}
  .md-split{grid-template-columns:minmax(0,1fr)}.md-chart{height:220px}.md-fg{grid-template-columns:repeat(2,minmax(0,1fr))}.md-f input{height:40px;font-size:16px}
  .md-tgl{display:flex;justify-content:space-between;align-items:center;width:100%;height:40px;padding:0 10px;border-radius:8px;border:1px solid var(--line,rgba(142,160,196,.35));background:transparent;color:inherit;font:inherit;font-size:13.5px}
  .md-tblbox[data-open="0"] .md-scroll{display:none}.md-tblbox[data-open="1"] .md-tgl i{transform:rotate(180deg)}.md-scroll{margin-top:6px}
  .md-bar .mf-ctl{margin-left:0;width:100%}
  #mdTbl th:nth-child(4),#mdTbl td:nth-child(4),#mdTbl th:nth-child(6),#mdTbl td:nth-child(6){display:none}}`;
    document.head.appendChild(el);
  })();

  window.TwMarginDash = { mount, _reset: () => { cache = null; st.open = false; st.edit = null; st.days = 0; st.msg = ''; } };
})();
