/* ============================================================================
   總覽摘要卡列最右邊的「恐慌指數」卡（site/fearcard.js）
   Andy 2026-11-06：「另外需要新增恐慌指數再右上」。
   ----------------------------------------------------------------------------
   資料：data/fear.json（pipeline/compute/ivx.py build_json；只重算這份＝python -m pipeline.compute.ivx）
     · 主視覺＝時速表（ECharts gauge），指針＝本站自算「臺指選擇權隱含波動率」（CBOE 白皮書公式、TXO 月契約近月＋次近月、30 天期），非期交所官方——這句只寫在「?」裡（Andy 11-06：「拿掉 非官方那句」）；
       名稱刻意不用「VIX」（Cboe 商標）。
     · 副數字＝美股恐慌指數 VIX（芝加哥期權交易所，資料湖 intl_daily 的 ^VIX，yfinance）。
     · 狀態＝本站自算序列在「到那天為止」最近 750 個交易日的分位：< 50% 平靜、50～85% 警戒、≥ 85% 恐慌；
       歷史不到 120 天不給標籤（樣本不足），n 一律寫出來。
   為什麼放一支獨立檔：同事同時在改 app.js 的總覽（提示框、漲跌家數字卡），這張卡的邏輯全部放這裡，
   app.js 只留三個接點（renderOvSummary 加卡片、點卡片 → 捲到底部走勢圖並 reveal、畫完 → mounted）。
   卡片長相沿用同一排的 .osc（標題列、比例條、數字、底線），比例條＝分位（0～100%）。
   2026-11-06 第二版（Andy：「圖示需要在優化，文字有點多，曲線圖放在最底下即可」）：卡片只留標題、時速表、大數字＋狀態字、一行「美股 VIX」；
   日期、漲跌、分位、n 全搬進「?」。走勢圖改放在總覽最底下的獨立卡（#ovFearCard，index.html），點摘要卡＝捲過去並亮一下；
   圖的本體（#ovFearFull）是第一次露出（捲到或點卡片）才建，功能鍵 ov.fear 計的是它（site/features.js）。
   ============================================================================ */
(function () {
  'use strict';
  const S = { data: null, loading: null, open: false, chart: null };
  const A = () => window.App || null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const md = (d) => { const s = String(d || ''); return /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(5, 7) + '/' + s.slice(8, 10) : '—'; };
  const n2 = (v) => (v == null || !isFinite(v) ? '—' : Number(v).toFixed(2));
  // 漲跌：數值往上＝紅、往下＝綠（台股慣例，跟全站一致；恐慌指數往上＝市場更緊張）
  // 卡片上漲跌只留一位小數（五張一排時一欄約 93px，兩位小數會把「▲11.57」切掉）；完整圖下方的說明列是兩位
  const chg = (v) => (v == null || !isFinite(v) ? '<em>—</em>' : `<em class="${v > 0 ? 'fz-up' : v < 0 ? 'fz-dn' : ''}" title="較前一個交易日 ${v > 0 ? '+' : ''}${Number(v).toFixed(2)}">${v > 0 ? '▲' : v < 0 ? '▼' : ''}${Math.abs(v).toFixed(1)}</em>`);
  /* 三段顏色（Andy 11-06：「恐慌指數用時速表那樣表示」→ 平靜綠／警戒黃／恐慌紅）。
     ⚠ 這裡的綠／紅是「狀態」不是漲跌：用主題變數 --fall（綠）／--amber／--rise（紅）只是借色，深淺主題自動跟著換。*/
  const ST = { calm: { n: '平靜', v: '--fall', c: 'var(--fall)' }, alert: { n: '警戒', v: '--amber', c: 'var(--amber)' }, panic: { n: '恐慌', v: '--rise', c: 'var(--rise)' } };
  const ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M4.5 16.5a8 8 0 1 1 15 0"/><path d="M12 16.5l4-5.5"/><circle cx="12" cy="16.5" r="1.3"/></svg>';
  const cssv = (name, fb) => { try { const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return v || fb; } catch (e) { return fb; } };

  function load() {
    if (S.data) return Promise.resolve(S.data);
    if (S.loading) return S.loading;
    const a = A();
    S.loading = (a && a.load ? a.load('fear') : fetch('data/fear.json').then((r) => (r.ok ? r.json() : null)))
      .catch(() => null).then((d) => { S.data = d || { tw: null, us: null }; S.loading = null; return S.data; });
    return S.loading;
  }

  /* 時速表的刻度範圍：最近 750 天自算序列的最小～最大，各往外取到 5 的倍數（至少 10～40），
     分段門檻＝50%／85% 分位對應的指數值（跟狀態標籤同一條規則，不另外挑數字）。*/
  function gaugeRange(tw) {
    const hs = ((tw && tw.series) || []).slice(-750).map((p) => p[1]).filter((v) => isFinite(v));
    let lo = Math.min(...hs, tw && tw.value != null ? tw.value : Infinity), hi = Math.max(...hs, tw && tw.value != null ? tw.value : -Infinity);
    if (!isFinite(lo) || !isFinite(hi)) { lo = 10; hi = 40; }
    lo = Math.max(0, Math.floor(lo / 5) * 5); hi = Math.max(lo + 30, Math.ceil(hi / 5) * 5);
    return { lo, hi };
  }

  function inner(d) {
    const tw = d && d.tw, us = d && d.us;
    const st = tw && ST[tw.state];
    /* 卡片只留：大數字＋狀態字（右側）、一行美股 VIX。日期、漲跌、分位、n 全在「?」裡（Andy 11-06：文字有點多；#329 日期不放卡片）。*/
    /* Andy 11-06（看過線上版）：數值放在時速表正下方、排成一行置中「40.0 恐慌 ｜ VIX 28.2」；卡片窄（桌機約 0.7 倍寬）放不下「美股」兩字，
       完整名稱在 title／aria／「?」裡。*/
    const side = !d ? '<span class="muted">載入中…</span>'
      : `<b class="fz-num" data-v="tw" style="color:${st ? st.c : 'var(--ink)'}">${tw ? Number(tw.value).toFixed(1) : '—'}</b>`
        + `<span class="fz-st" style="color:${st ? st.c : 'var(--ink-3)'}">${tw ? (st ? st.n : '樣本不足') : '回補中'}</span>`
        + `<i class="fz-sep" aria-hidden="true"></i><span class="fz-us" data-v="us" title="美股恐慌指數 VIX">VIX <b>${us && us.value != null ? Number(us.value).toFixed(1) : '—'}</b></span>`;
    return { side, st, aria: `恐慌指數 ${n2(tw && tw.value)}${st ? '，' + st.n : ''}；美股 VIX ${n2(us && us.value)}。點一下捲到走勢圖` };
  }
  function card() {
    const o = inner(S.data);
    return `<div class="osc fz" data-k="fear" role="button" tabindex="0" aria-label="${esc(o.aria)}" title="點一下看走勢圖">`
      + `<div class="osc-h"><span class="osc-ic" data-icon="gauge" style="--ic:var(--rise)" aria-hidden="true">${ICON}</span><b class="osc-t">恐慌指數</b>`
      + `<button class="howbtn pop" data-how="ovs-fear" data-ttl="恐慌指數" type="button" aria-label="恐慌指數怎麼看">?</button></div>`
      + `<div class="osc-n fz-body"><div class="fz-g" id="ovFearGauge" role="img" aria-label="${esc(o.aria)}"></div><div class="fz-val">${o.side}</div></div></div>`;
  }
  function howText(d) {
    const m = (d && d.method) || {};
    const lo = Math.round((m.calm || 0.5) * 100), hi = Math.round((m.panic || 0.85) * 100);
    const tw = d && d.tw, us = d && d.us;
    const sg = (v) => (v == null || !isFinite(v) ? '' : `（${v > 0 ? '+' : ''}${Number(v).toFixed(2)}）`);
    const rd = tw ? `<li>最新讀數：台指 ${md(tw.date)} <b>${n2(tw.value)}</b>${sg(tw.chg)}・分位 ${tw.pct != null ? Math.round(tw.pct * 100) + '%' : '—'}・n=${tw.n_hist}`
      + (us ? `；美股 VIX ${md(us.date)} <b>${n2(us.value)}</b>${sg(us.chg)}` : '') + '</li>' : '';
    return '<b class="howq">市場現在有多緊張：選擇權價格隱含的未來 30 天波動。</b><ul>' + rd
      + '<li>時速表的指針＝<b>台指選擇權隱含波動率</b>，本站依期交所公開的臺指選擇權（TXO）每日行情自算，與期交所公布的台指VIX會有差異（非期交所官方數字）</li>'
      + '<li>算法：近月、次近月月契約各履約價的結算價，照芝加哥期權交易所公開的波動率指數白皮書公式，插補成 30 天期，單位是年化 %</li>'
      + `<li>無風險利率固定 ${((m.rate || 0.015) * 100).toFixed(1)}%；近月剩最後兩個交易日就改用次近月＋第三近月（同期交所換月規則）</li>`
      + '<li>資料來源：期交所臺指選擇權每日行情（經 FinMind 開放資料），每天盤後更新</li>'
      + `<li>三段顏色＝今天的值在最近 ${m.window || 750} 個交易日（到今天為止，不含未來）裡的分位：低於 ${lo}% 平靜（綠）、${lo}～${hi}% 警戒（黃）、${hi}% 以上恐慌（紅）；刻度上的分界就是那兩個分位對應的數值</li>`
      + `<li>門檻依據：${lo}%＝中位數（比一半的日子高才開始警戒）；${hi}%≈平均加一個標準差（常態分配下約 84%），不是對著歷史挑出來的數字</li>`
      + `<li>歷史不到 ${m.min_hist || 120} 個交易日只給數字、不給狀態；右邊的 n＝分位用到的天數</li>`
      + '<li>卡片下方的「美股 VIX」＝美股恐慌指數（芝加哥期權交易所），日期是美國交易日，跟台股差一天是正常的</li>'
      + '<li>走勢圖分兩格、共用同一條日期軸：<b>上格</b>放對照指數（台股＝加權指數、櫃買指數；美股＝那斯達克、費城半導體、標普 500），<b>下格</b>放恐慌指數（台股＝台指自算；美股＝美股 VIX）。「台股｜美股」切換看哪一邊，會記住你的選擇</li>'
      + '<li>上格全部<b>以所選期間的第一天當 100</b> 畫相對走勢（各指數點數差太多，直接放一起看不出誰漲得多）；切換期間或拖下方的細拉Bar，起點就跟著重算。提示框裡寫的是各指數當天的實際點數與單日漲跌幅（紅漲綠跌）</li>'
      + `<li>下格背景三段色帶：台指自算用上面講的分位（${lo}%、${hi}% 對應的數值）；美股 VIX 用公開慣例的固定門檻——低於 20 平靜、20～30 警戒、30 以上恐慌。色帶畫的是「現在」的門檻，提示框裡的狀態字是「那一天當下」的狀態</li>`
      + '<li>提示框標的美股日期是美國交易日；台股與美股休市日不同，沒有開盤的那天該指數留空</li>'
      + '<li><b>圖例可以點</b>：點一下關掉／打開那條線（關掉的會變淡、加刪除線）。上格的 Y 軸會依剩下的線重算；全部關掉上格就收起、整張讓給下格；把恐慌指數那條關掉，高低點標示也一起消失。台股、美股各記各的</li>'
      + '<li><b>垂直虛線＝恐慌指數的階段高低點</b>（綠＝波段低點、紅＝波段高點，上下兩格同一天都有線，可以對照當天大盤在哪）。找法：反向變動超過門檻才算轉折——美股 VIX 25%、台指自算 15%；視窗放不下就自動提高門檻，只留最大的幾段。兩條虛線之間的 <b>▲+xx%／▼-xx%</b>＝相鄰兩個高低點之間恐慌指數漲或跌了多少（低點到高點漲、高點到低點跌，紅漲綠跌）。滑到轉折那天，提示框會多一行「波段低點／高點」。怎麼用：低點後恐慌急升通常是風險升溫、高點後回落代表情緒降溫，拿它對照上格大盤同一天的位置</li>'
      + '<li>下格的 Y 軸範圍固定（用全部歷史算一次），切期間或縮放都不會跳動；平靜／警戒／恐慌三段色帶永遠都畫，就算這段期間沒到過恐慌區也看得到紅色區在哪</li>'
      + '<li><b>游標縮放</b>：電腦在圖上滾動滾輪＝以游標位置為中心放大縮小時間軸，按住拖曳＝左右平移；手機用兩指縮放（單指上下滑照常捲頁，左右移動用下方細拉Bar）。縮放後期間鈕會取消亮起，按期間鈕就回到那個期間</li>'
      + '<li>預設看近 3 個月；期間鈕有 1 月／3 月／6 月／1 年／全部，資料不夠長的鈕會反灰</li></ul>';
  }

  /* 時速表本體。每次卡列重畫（換主題、回總覽）節點都是新的，所以每次 refresh 都重新 setOption；顏色當下從主題變數讀。*/
  function drawGauge() {
    const el = document.getElementById('ovFearGauge'); const a = A(); const d = S.data;
    if (!el || !a || !a.chart || !d) return;
    const tw = d.tw;
    const ink = cssv('--ink', '#e8eeff'), line = cssv('--line', '#1e2a48');
    if (!tw) { el.innerHTML = '<div class="fz-na muted">台指自算值回補中</div>'; return; }
    const { lo, hi } = gaugeRange(tw);
    const f = (v) => Math.min(1, Math.max(0, (v - lo) / (hi - lo)));
    /* 淺色主題的 --amber 是給文字用的深琥珀，畫在弧線上偏暗、像橄欖色（Andy 11-06）：弧線的黃改用亮一點的固定值 */
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    const C = { calm: cssv('--fall', '#2ee59d'), alert: light ? '#E0A100' : cssv('--amber', '#ffb454'), panic: cssv('--rise', '#ff4d6d') };
    const stops = tw.q50 != null && tw.q85 != null && tw.state
      ? [[f(tw.q50), C.calm], [f(tw.q85), C.alert], [1, C.panic]]
      : [[1, line]];                                   // 樣本不足：不畫分段（不給狀態就不准用顏色暗示狀態）
    /* 版面：只畫弧與指針（數字、狀態字改在右側 HTML，大而清楚）。圓心貼近底邊、半徑用像素算（ECharts 的 % 在矮卡片會縮成一小團）；
       弧線粗 10、兩端圓頭；分界靠顏色變化（不畫刻度與刻度數字）；指針細長、圓心加一圈與卡底同色的外框，深淺主題都清楚。*/
    const W = el.clientWidth || 90, H = el.clientHeight || 44;
    const CY = H - 7, R = Math.max(20, Math.min(W / 2 - 4, CY - 1));
    const bg = cssv('--panel', '#0d1426');
    a.chart(el, {
      animation: false, m4dz: false, timeGrid: false,
      series: [{
        type: 'gauge', startAngle: 180, endAngle: 0, min: lo, max: hi, splitNumber: 2,
        center: ['50%', CY], radius: R,
        axisLine: { roundCap: true, lineStyle: { width: R > 50 ? 10 : 8, color: stops } },
        pointer: { length: '66%', width: 4, offsetCenter: [0, 0], itemStyle: { color: ink } },
        anchor: { show: true, size: 9, showAbove: true, itemStyle: { color: ink, borderColor: bg, borderWidth: 3 } },
        axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
        title: { show: false }, detail: { show: false },
        data: [{ value: tw.value }],
      }],
    });
    el.dataset.v = String(tw.value); el.dataset.lo = String(lo); el.dataset.hi = String(hi);
  }

  function refresh() {
    const c = document.querySelector('#hero .osc[data-k="fear"]'); if (!c) return;
    const o = inner(S.data);
    const side = c.querySelector('.fz-val'); if (side && side.innerHTML !== o.side) side.innerHTML = o.side;
    c.setAttribute('aria-label', o.aria);
    ['how-ovs-fear', 'how-fearfull'].forEach((id) => { const hb = document.getElementById(id); if (hb) hb.innerHTML = howText(S.data); });
    const host = document.getElementById('hero');
    if (host && S.data) { host.dataset.fearTw = S.data.tw ? String(S.data.tw.value) : ''; host.dataset.fearUs = S.data.us ? String(S.data.us.value) : ''; host.dataset.fearState = (S.data.tw && S.data.tw.state) || ''; }
    drawGauge();
  }

  /* 卡列整排重畫（renderOvSummary）之後：補「?」說明、資料到了就原地換，開著的完整圖重新掛回去 */
  function mounted(host) {
    if (!host) return;
    if (!document.getElementById('how-ovs-fear')) { const b = document.createElement('div'); b.className = 'howtxt'; b.id = 'how-ovs-fear'; b.hidden = true; host.appendChild(b); }
    refresh();
    watch();
    load().then(() => { refresh(); if (S.open) openFull(); });
  }

  /* 走勢圖在總覽最底下的獨立卡（#ovFearCard，index.html）。卡片外框一直在；圖的本體 #ovFearFull 第一次露出才建
     （點摘要卡、或捲到卡片）——功能鍵 ov.fear 的 veil 蓋的是它，沒看到就不計次。預設直接展開（總覽底部只有這一組）。*/
  function openFull() {
    const host = document.getElementById('ovFearCard'); if (!host) return;
    S.open = true;
    let p = document.getElementById('ovFearFull');
    if (!p) {
      p = document.createElement('div'); p.id = 'ovFearFull'; p.className = 'fz-full'; p.setAttribute('aria-label', '恐慌指數走勢圖');
      p.innerHTML = '<div class="fz-cv" id="ovFearChart"></div>';
      host.appendChild(p);
    }
    refresh();
    draw();
  }
  /* 底部卡：標題列（標題、台股｜美股、圖例、期間鈕、「?」）由 index.html 放好；這裡只負責「露出才畫」 */
  function watch() {
    const host = document.getElementById('ovFearCard'); if (!host || host._fzIO) return;
    bindCtl();
    if (typeof IntersectionObserver === 'undefined') { load().then(openFull); return; }
    const io = new IntersectionObserver((es) => { if (es.some((x) => x.isIntersecting)) { io.disconnect(); host._fzIO = null; load().then(openFull); } }, { rootMargin: '200px' });
    host._fzIO = io; io.observe(host);
  }
  function reveal() { load().then(() => { if (!S.open || !document.getElementById('ovFearFull')) openFull(); else draw(); }); }

  /* ======================================================================================
     走勢圖（2026-11-06 第三版，Andy：「這邊的曲線圖優化，我覺得好醜，並且需要搭配大盤走勢圖才可以發現差異」
     「分成台股美股：台股 VIX 就是加權、櫃買；美股就是那斯達克、費城、S&P 比較」）
     ·上下兩格共用同一條時間軸（一個 ECharts、兩個 grid）：上格＝對照指數（期間起點＝100 的相對走勢，因為量級差太多，
       雙 Y 軸會讓兩條線的交會點沒有意義）；下格＝恐慌指數；十字線與提示框兩格連動。
     ·背景三段色帶（平靜／警戒／恐慌）取代原本兩條虛線：台指自算＝50%／85% 分位對應的值；美股 VIX＝公開慣例 20／30。
     ·期間鈕（1月／3月／6月／1年／全部，預設 3 月）＝ 時間軸視窗；視窗一變（按鈕或拖拉Bar）上格就重新以視窗起點為 100。
     ·台股｜美股 的選擇存 localStorage（tw.fear.mkt）。
     ====================================================================================== */
  const LSK = 'tw.fear.mkt';
  const lsGet = (k, d) => { try { return localStorage.getItem(k) || d; } catch (e) { return d; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只影響記不記得 */ } };
  S.mkt = lsGet(LSK, 'tw') === 'us' ? 'us' : 'tw';
  S.per = '3m';
  /* 圖例篩選（Andy 11-09）：台股、美股各自記一份「關掉的線」，key 例如 tw.fear.hide.tw ／ tw.fear.hide.us。 */
  const hideKey = (mk) => 'tw.fear.hide.' + mk;
  const loadHide = (mk) => { try { const a = JSON.parse(lsGet(hideKey(mk), '[]')); return new Set(Array.isArray(a) ? a.filter((x) => typeof x === 'string') : []); } catch (e) { return new Set(); } };
  S.hide = { tw: loadHide('tw'), us: loadHide('us') };
  /* 階段性高低點（zigzag）的轉折門檻：反向變動比例 ≥ 門檻才算新轉折。
     · 美股 VIX 0.25：VIX 日常就會 ±10% 亂跳，單日波動很少連續反向超過 25%；低於這個就是雜訊、高於這個通常是一個「事件」（上半年的 4 月關稅、8 月急殺都過得去）。
     · 台指自算 0.15：它是 30 天期隱含波動率，本身比 VIX 平滑（日變動約 3～5%），門檻取 VIX 的 6 成，才抓得到 3 個月內 2～4 段波段。
     視窗放不下（段數 > PIV_MAX 或相鄰兩點的像素距離放不下百分比標籤）就自動把門檻 × 1.18 再算，寧可少不要擠。 */
  const PIV_TH = { vix: 0.25, ivx: 0.15 };
  const PIV_MAX = { d: 8, m: 5 };
  const PIV_STRIP = 18;                           // 下格上方留給「▲+xx%」標籤的一條空白帶（固定高度，圖不會因為有沒有轉折而上下跳）
  const DAY = 86400000;
  const ts = (d) => Date.parse(d + 'T00:00:00Z');
  const ymd = (t) => new Date(t).toISOString().slice(0, 10);
  const PER = { '1m': 1, '3m': 3, '6m': 6, '1y': 12, all: 0 };
  const rgba = (c, a) => {
    let m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(c).trim());
    if (m) { let h = m[1]; if (h.length === 3) h = h.replace(/./g, '$&$&'); return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`; }
    m = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(String(c)); return m ? `rgba(${m[1]},${m[2]},${m[3]},${a})` : c;
  };
  const fmtN = (v, dp) => (v == null || !isFinite(v) ? '—' : Number(v).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp }));
  /* 美股 VIX 的狀態門檻：公開慣例（20 以下平靜、20～30 警戒、30 以上恐慌）；台指自算用自己的歷史分位（見 howText） */
  const VIX_Q = [20, 30];

  /* 這個市場要畫的東西：上格 top（相對走勢的指數們）、下格 bot（恐慌指數）、色帶門檻 */
  function model() {
    const d = S.data || {}, idx = (d.idx && d.idx[S.mkt]) || {}, hide = S.hide[S.mkt];
    const tw = S.mkt === 'tw';
    const top = tw
      ? [{ k: 'TSE', c: CHc('cyan'), w: 2 }, { k: 'OTC', c: CHc('violet'), w: 1.6 }]
      : [{ k: 'IXIC', c: CHc('cyan'), w: 2 }, { k: 'SOX', c: CHc('violet'), w: 1.6 }, { k: 'GSPC', c: CHc('amber'), w: 1.6 }];
    const tops0 = top.filter((x) => idx[x.k] && idx[x.k].series && idx[x.k].series.length).map((x) => ({ k: x.k, name: idx[x.k].name, c: x.c, w: x.w, raw: idx[x.k].series }));
    let bot0 = null;
    if (tw && d.tw && d.tw.series && d.tw.series.length) {
      const mh = (d.method && d.method.min_hist) || 120;
      bot0 = { k: 'ivx', name: '台指自算', c: CHc('up'), raw: d.tw.series, q: d.tw.q50 != null && d.tw.q85 != null ? [d.tw.q50, d.tw.q85] : null,
        stateAt: (i) => { const p = d.tw.pct_series && d.tw.pct_series[i] ? d.tw.pct_series[i][1] : null; return p == null || i + 1 < mh ? null : p >= ((d.method && d.method.panic) || 0.85) ? 'panic' : p >= ((d.method && d.method.calm) || 0.5) ? 'alert' : 'calm'; } };
    } else if (!tw && d.us && d.us.series && d.us.series.length) {
      bot0 = { k: 'vix', name: '美股 VIX', c: CHc('ink'), raw: d.us.series, q: VIX_Q, stateAt: (i, v) => (v >= VIX_Q[1] ? 'panic' : v >= VIX_Q[0] ? 'alert' : 'calm') };
    }
    [...tops0, ...(bot0 ? [bot0] : [])].forEach((x) => { x.t = x.raw.map((p) => ts(p[0])); x.v = x.raw.map((p) => p[1]); x.off = hide.has(x.k); });
    /* 下格 Y 軸（Andy 11-09：「下方恐慌 統一不要改變，有紅色區域即使沒有達到也需要顯示」）：用「全部歷史」算一次就固定，
       不隨期間／拉Bar／縮放變；三段色帶永遠都畫。上限＝max(歷史最高, 恐慌門檻＋一段不小於警戒區的紅區高度)，上下各留 18% 給轉折點的數值標籤，刻度取 5 的倍數。 */
    if (bot0) {
      const vs = bot0.v.filter((v) => isFinite(v)), gmin = Math.min(...vs), gmax = Math.max(...vs);
      let loR = Math.max(0, gmin), hiR = gmax;
      if (bot0.q) { const [q1, q2] = bot0.q; hiR = Math.max(gmax, q2 + Math.max(q2 - q1, 0.35 * (q2 - loR))); }
      const pad = 0.18 * (hiR - loR);
      bot0.y = { min: Math.max(0, Math.floor((loR - pad) / 5) * 5), max: Math.ceil((hiR + pad) / 5) * 5 };
    }
    return { tops: tops0.filter((x) => !x.off), bot: bot0 && !bot0.off ? bot0 : null, all: [...tops0, ...(bot0 ? [bot0] : [])], tops0, bot0 };
  }
  const CHc = (k) => ((A() && A().CH) || {})[k] || { up: '#ff4d6d', cyan: '#3ee0ff', violet: '#8b7bff', amber: '#ffb454', ink: '#e8eeff' }[k];
  /* 在序列 x 裡找「時間 ≤ t 的最後一筆」；差超過 6 天（長假、沒資料）就當沒有 */
  function at(x, t) {
    let lo = 0, hi = x.t.length - 1, r = -1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (x.t[m] <= t) { r = m; lo = m + 1; } else hi = m - 1; }
    return r >= 0 && t - x.t[r] <= 6 * DAY ? r : -1;
  }
  /* X 軸刻度：視窗內平均取 n 個日期（各往內縮半格，頭尾標籤才不會被切），間隔一致、不會出現「08/29 與 09/01 擠在一起」 */
  const xTicks = (a, b, n) => Array.from({ length: n }, (_, k) => Math.round((a + (k + 0.5) / n * (b - a)) / DAY) * DAY);
  function periodStart(per, xmin, xmax) {
    if (per === 'all') return xmin;
    const d = new Date(xmax); d.setUTCMonth(d.getUTCMonth() - PER[per]);
    return Math.max(xmin, d.getTime());
  }

  /* 依視窗 [a,b] 算出所有「會隨視窗變」的東西：上格以視窗起點為 100 的資料、兩個 Y 軸範圍、色帶 */
  function build(m, a, b) {
    const topSer = m.tops.map((x) => {
      const i0 = x.t.findIndex((t) => t >= a);
      const base = i0 >= 0 ? x.v[i0] : null;
      return { x, base, data: base ? x.t.map((t, i) => [t, x.v[i] / base * 100]) : [] };
    });
    let lo = Infinity, hi = -Infinity;
    topSer.forEach((s) => s.data.forEach((p) => { if (p[0] >= a && p[0] <= b) { lo = Math.min(lo, p[1]); hi = Math.max(hi, p[1]); } }));
    if (!isFinite(lo)) { lo = 95; hi = 105; }
    lo = Math.min(lo, 100); hi = Math.max(hi, 100);
    /* Andy 11-09：「若只有 100 就調整 100 就好，不要上面有那麼多空白」→ 軸的上下限直接貼資料（只留 3% 呼吸），
       不再「進位到刻度的倍數」（原本會多留最多一整格，3 條線都在 100 附近時上面就空一大片）；刻度交給 ECharts 在範圍內挑整數。 */
    const padT = Math.max(0.3, (hi - lo) * 0.03);
    const yTop = { min: Math.floor((lo - padT) * 10) / 10, max: Math.ceil((hi + padT) * 10) / 10 };
    let yBot = { min: 0, max: 40 }, bands = [];
    if (m.bot) {
      yBot = { min: m.bot.y.min, max: m.bot.y.max };      // 固定，不隨視窗變
      if (m.bot.q) {
        const [q1, q2] = m.bot.q;
        [['calm', yBot.min, q1], ['alert', q1, q2], ['panic', q2, yBot.max]].forEach(([k, u, w]) => bands.push({ k, lo: u, hi: w }));
      }
    }
    return { topSer, yTop, yBot, bands };
  }
  /* ======= 階段性高低點（zigzag） =======
     從視窗內第一天起，反向變動比例 ≥ 門檻才確認上一個極值是轉折；最後一段還沒被反向確認的極值也算（它就是目前視窗內的階段高／低點）。 */
  function zigzag(x, a, b, th) {
    const P = []; x.t.forEach((t, i) => { if (t >= a && t <= b && isFinite(x.v[i]) && x.v[i] > 0) P.push([t, x.v[i]]); });
    if (P.length < 3) return [];
    const out = []; let dir = 0, hi = 0, lo = 0;
    for (let i = 1; i < P.length; i++) {
      const v = P[i][1];
      if (dir === 0) {
        if (v > P[hi][1]) hi = i; if (v < P[lo][1]) lo = i;
        const up = lo < i && v >= P[lo][1] * (1 + th), dn = hi < i && v <= P[hi][1] * (1 - th);
        if (up && (!dn || lo < hi)) { out.push({ i: lo, k: 'L' }); dir = 1; hi = i; }
        else if (dn) { out.push({ i: hi, k: 'H' }); dir = -1; lo = i; }
      } else if (dir === 1) {
        if (v > P[hi][1]) hi = i;
        else if (v <= P[hi][1] * (1 - th)) { out.push({ i: hi, k: 'H' }); dir = -1; lo = i; }
      } else {
        if (v < P[lo][1]) lo = i;
        else if (v >= P[lo][1] * (1 + th)) { out.push({ i: lo, k: 'L' }); dir = 1; hi = i; }
      }
    }
    if (dir === 1) out.push({ i: hi, k: 'H' }); else if (dir === -1) out.push({ i: lo, k: 'L' });
    return out.filter((o, j) => j === 0 || o.i !== out[j - 1].i).map((o) => ({ t: P[o.i][0], v: P[o.i][1], k: o.k }));
  }
  let _mc = null;
  const textW = (str, px, bold) => { try { _mc = _mc || document.createElement('canvas').getContext('2d'); _mc.font = (bold ? '700 ' : '400 ') + px + 'px sans-serif'; return _mc.measureText(str).width; } catch (e) { return str.length * px * 0.7; } };
  const pctStr = (p) => (p >= 0 ? '▲+' : '▼-') + Math.abs(Math.round(p)) + '%';
  /* 找出視窗內放得下的轉折：段數 ≤ PIV_MAX，且每相鄰兩點的像素距離放得下那段的百分比標籤（寧可少不要擠）；放不下就門檻 × 1.18 再算 */
  function pivots(m, a, b, W) {
    if (!m.bot || !(b > a) || !(W > 40)) return { pv: [], th: null, segs: [] };
    const mob = S.mob, maxSeg = mob ? PIV_MAX.m : PIV_MAX.d, base = PIV_TH[m.bot.k] || 0.2;
    let th = base, pv = [];
    for (let n = 0; n < 14; n++, th *= 1.18) {
      pv = zigzag(m.bot, a, b, th);
      pv.forEach((q, j) => { q.x = (q.t - a) / (b - a) * W; q.pct = j ? (q.v / pv[j - 1].v - 1) * 100 : null; });
      const ok = pv.length - 1 <= maxSeg && pv.every((q, j) => j === 0 || q.x - pv[j - 1].x >= textW(pctStr(q.pct), 12, true) + 10);
      if (ok) break;
    }
    return { pv, th, segs: pv.slice(1).map((q, j) => ({ t0: pv[j].t, t1: q.t, pct: q.pct, w: textW(pctStr(q.pct), 12, true) })) };
  }
  /* 把轉折變成 ECharts 的疊加層：垂直虛線（上下兩格各一條，貫穿同一天）、轉折點小圓點＋數值、兩點之間的漲跌幅標籤（放在下格上方那條空白帶，不壓線） */
  function overlay(m, r, a, b) {
    const C = stateColors(), ink = cssv('--ink', '#e8eeff'), rise = cssv('--rise', '#ff4d6d'), fall = cssv('--fall', '#2ee59d');
    const W = Math.max(0, (S.cw || 0) - S.grid.l - S.grid.r);
    const o = pivots(m, a, b, W);
    S.pv = o.pv;
    const lines = o.pv.map((q) => ({ xAxis: q.t, lineStyle: { type: 'dashed', width: 1, color: rgba(q.k === 'H' ? C.panic : C.calm, 0.6) } }));
    const pts = [];
    o.pv.forEach((q) => {
      const edgeL = q.x < 22, edgeR = W - q.x < 22;
      pts.push({ coord: [q.t, q.v], symbol: 'circle', symbolSize: 7, itemStyle: { color: q.k === 'H' ? C.panic : C.calm, borderColor: cssv('--panel', '#0d1426'), borderWidth: 1 },
        label: { show: true, position: q.k === 'H' ? 'top' : 'bottom', distance: 3, align: edgeL ? 'left' : edgeR ? 'right' : 'center', formatter: () => fmtN(q.v, 1), color: ink, fontSize: 12, fontFamily: (A() && A().NUM_FONT) || 'monospace' } });
    });
    o.segs.forEach((g) => pts.push({ coord: [(g.t0 + g.t1) / 2, r.yBot.max], symbol: 'rect', symbolSize: 1, itemStyle: { color: 'rgba(0,0,0,0)' },
      label: { show: true, position: 'top', distance: 3, formatter: () => pctStr(g.pct), color: g.pct >= 0 ? rise : fall, fontSize: 12, fontWeight: 700, fontFamily: (A() && A().NUM_FONT) || 'monospace' } }));
    S.segs = o.segs; S.th = o.th;
    return { lines, pts };
  }
  const baseML = (data) => ({ silent: true, symbol: 'none', animation: false, label: { show: false }, lineStyle: { type: 'dashed', width: 1, color: cssv('--ink-3', '#8a94a6'), opacity: 0.6 }, data });
  const stateColors = () => {
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    return { calm: cssv('--fall', '#2ee59d'), alert: light ? '#E0A100' : cssv('--amber', '#ffb454'), panic: cssv('--rise', '#ff4d6d') };
  };
  const stateText = () => ({ calm: cssv('--fall', '#2ee59d'), alert: cssv('--amber', '#ffb454'), panic: cssv('--rise', '#ff4d6d') });
  const bandMark = (bands) => {
    const C = stateColors(), T = stateText(), light = document.documentElement.getAttribute('data-theme') === 'light';
    return { silent: true, animation: false, data: bands.map((b) => [{ yAxis: b.lo, name: ST[b.k].n, itemStyle: { color: rgba(C[b.k], light ? 0.13 : 0.11) }, label: { show: true, position: 'right', color: T[b.k], fontSize: 12, fontWeight: 600, distance: 4 } }, { yAxis: b.hi }]) };
  };

  function tipHtml(m, t) {
    const T = stateText(), ink3 = cssv('--ink-3', '#8a94a6');
    const dot = (c) => `<i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:6px"></i>`;
    const rows = [];
    let head = ymd(t);
    m.tops.forEach((x) => {
      const i = at(x, t); if (i < 0) { rows.push([dot(x.c) + x.name, '—', '']); return; }
      const c = i > 0 ? (x.v[i] / x.v[i - 1] - 1) * 100 : null;
      const cc = c == null ? '' : `<span style="color:${c > 0 ? cssv('--rise', '#ff4d6d') : c < 0 ? cssv('--fall', '#2ee59d') : ink3};margin-left:8px">${c > 0 ? '▲' : c < 0 ? '▼' : ''}${Math.abs(c).toFixed(2)}%</span>`;
      rows.push([dot(x.c) + x.name, fmtN(x.v[i], 2), cc]);
    });
    if (m.bot) {
      const x = m.bot, i = at(x, t);
      if (i < 0) rows.push([dot(x.c) + x.name, '—', '']);
      else { const st = x.stateAt(i, x.v[i]); rows.push([dot(x.c) + x.name, fmtN(x.v[i], 2), st ? `<b style="color:${T[st]};margin-left:8px">${ST[st].n}</b>` : `<span style="color:${ink3};margin-left:8px">樣本不足</span>`]); }
    }
    const pq = m.bot && (S.pv || []).find((q) => Math.abs(q.t - t) <= 0.6 * DAY);
    if (pq) {
      const j = S.pv.indexOf(pq), up = pq.k === 'H';
      rows.push([`<b style="color:${up ? T.panic : T.calm}">波段${up ? '高' : '低'}點</b>`, '', j && pq.pct != null ? `<span style="color:${pq.pct >= 0 ? cssv('--rise', '#ff4d6d') : cssv('--fall', '#2ee59d')}">前一段 ${pq.pct >= 0 ? '▲+' : '▼-'}${Math.abs(pq.pct).toFixed(1)}%</span>` : '<span style="color:' + ink3 + '">視窗起點後第一個轉折</span>']);
    }
    return `<div style="font-size:12px;color:${ink3};margin-bottom:4px">${head}</div>` + rows.map((r) => `<div style="display:flex;gap:14px;justify-content:space-between;align-items:baseline;line-height:20px"><span>${r[0]}</span><span style="font-family:var(--mono);white-space:nowrap"><b>${r[1]}</b>${r[2]}</span></div>`).join('');
  }

  /* 圖例＝篩選鈕（Andy 11-09）：點一下關掉／打開那條線；關掉的變淡＋刪除線，色塊變灰。選擇依台股／美股分開存 localStorage。 */
  function legend(m) {
    const el = document.getElementById('fzLeg'); if (!el) return;
    el.innerHTML = m.all.map((x) => `<button type="button" class="fz-lg${x.off ? ' off' : ''}" data-k="${esc(x.k)}" aria-pressed="${x.off ? 'false' : 'true'}" title="${x.off ? '點一下顯示' : '點一下隱藏'}「${esc(x.name)}」"><i style="--c:${x.c}"></i>${esc(x.name)}</button>`).join('') + (m.tops.length ? '<span class="fz-lg fz-base">上格：期間起點＝100</span>' : '');
  }
  function toggleLine(k) {
    const set = S.hide[S.mkt]; if (set.has(k)) set.delete(k); else set.add(k);
    lsSet(hideKey(S.mkt), JSON.stringify([...set]));
    draw();
  }

  function ctlSync(m, win) {
    document.querySelectorAll('#fzMkt button').forEach((b) => { const on = b.dataset.mkt === S.mkt; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
    const per = S.winPer;
    document.querySelectorAll('#fzPer button').forEach((b) => {
      const on = b.dataset.p === per; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
      const first = S.xmin, need = b.dataset.p === 'all' ? null : periodStart(b.dataset.p, -Infinity, S.xmax);
      const short = need != null && first != null && first > need + 3 * DAY;
      b.disabled = !!short; b.title = short ? `資料從 ${ymd(first)} 才開始，不足${b.textContent}` : '';
    });
  }
  function bindCtl() {
    const root = document.getElementById('ovFearCard'); if (!root || root._fzBound) return; root._fzBound = true;
    root.addEventListener('click', (e) => {
      const lg = e.target.closest && e.target.closest('#fzLeg button.fz-lg'); if (lg) { toggleLine(lg.dataset.k); return; }
      const b = e.target.closest && e.target.closest('#fzMkt button, #fzPer button'); if (!b || b.disabled) return;
      if (b.dataset.mkt) { if (b.dataset.mkt === S.mkt) return; S.mkt = b.dataset.mkt; lsSet(LSK, S.mkt); S.win = null; draw(); }
      else if (b.dataset.p) setPeriod(b.dataset.p);
    });
  }
  function setPeriod(p) {
    S.per = p; const a = periodStart(p, S.xmin, S.xmax);
    S.win = [a, S.xmax];
    const ch = S.chart; if (!ch) return draw();
    ch.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, startValue: a, endValue: S.xmax });
    applyWin(a, S.xmax);
  }
  /* 視窗變了（按期間鈕、拖拉Bar、滾輪）：重算上格基準與兩個 Y 軸、色帶，只更新資料不重建圖 */
  function applyWin(a, b) {
    const ch = S.chart, m = S.m; if (!ch || !m) return;
    S.win = [a, b];
    const r = build(m, a, b);
    const yA = [], xA = [];
    if (S.hasTop) yA.push({ min: r.yTop.min, max: r.yTop.max });
    if (S.hasBot) yA.push({ min: r.yBot.min, max: r.yBot.max });
    yA.forEach(() => xA.push({ axisLabel: { customValues: xTicks(a, b, S.nTick) } }));
    const ov = overlay(m, r, a, b);
    ch.setOption({
      yAxis: yA, xAxis: xA,
      series: [...r.topSer.map((s, i) => Object.assign({ id: 'top-' + s.x.k, data: s.data }, i === 0 ? { markLine: baseML([{ yAxis: 100 }, ...ov.lines]) } : {})),
        ...(m.bot ? [{ id: 'bot-' + m.bot.k, markArea: bandMark(r.bands), markLine: baseML(ov.lines), markPoint: { silent: true, animation: false, data: ov.pts } }] : [])],
    });
    // 視窗剛好等於某顆期間鈕 → 亮那顆；拖成別的範圍 → 全部不亮
    S.winPer = null;
    Object.keys(PER).forEach((k) => { if (Math.abs(periodStart(k, S.xmin, S.xmax) - a) <= 2 * DAY && Math.abs(b - S.xmax) <= 2 * DAY) S.winPer = k; });
    ctlSync(m);
    if (window.App && window.App._fear) { Object.assign(window.App._fear, { per: S.winPer, win: [ymd(a), ymd(b)], base: r.topSer.map((s) => s.base), piv: pivOut(), th: S.th }); }
    const host = document.getElementById('ovFearFull'); if (host) { host.dataset.per = S.winPer || ''; host.dataset.win = ymd(a) + '~' + ymd(b); }
  }

  const pivOut = () => (S.pv || []).map((q, j) => ({ d: ymd(q.t), v: q.v, k: q.k, pct: j ? q.pct : null }));
  function draw() {
    const el = document.getElementById('ovFearChart'); const a = A(); const d = S.data || {};
    if (!el || !a || !a.chart) return;
    const m = model(); S.m = m;
    legend(m);
    if (!m.bot && !m.tops.length) {
      try { const c0 = window.echarts && echarts.getInstanceByDom(el); if (c0) c0.dispose(); } catch (e) { /* 已釋放 */ }
      S.chart = null; S.pv = []; S.segs = [];
      el.innerHTML = '<div class="empty">' + (m.all.length ? '圖例的線都關掉了，點上方圖例可以再打開' : d.tw || d.us ? '這個市場的資料回補中' : '尚無資料') + '</div>'; ctlSync(m);
      const hh = document.getElementById('ovFearFull'); if (hh) hh.dataset.names = '';
      if (window.App) window.App._fear = Object.assign(window.App._fear || {}, { mkt: S.mkt, names: [], piv: [], hidden: [...S.hide[S.mkt]], open: true });
      return;
    }
    const CH = a.CH || {}, ax = a.axisStyle || {};
    const mob = !!(window.matchMedia && (window.matchMedia('(max-width:640px)').matches || window.matchMedia('(pointer:coarse)').matches)); S.mob = mob;
    const all = m.all;
    S.xmin = Math.min(...all.map((x) => x.t[0])); S.xmax = Math.max(...all.map((x) => x.t[x.t.length - 1]));
    const reuse = S.win && S.win[0] >= S.xmin && S.win[1] <= S.xmax;
    const w0 = reuse ? S.win : [periodStart(S.per, S.xmin, S.xmax), S.xmax];
    S.winPer = null; Object.keys(PER).forEach((k) => { if (Math.abs(periodStart(k, S.xmin, S.xmax) - w0[0]) <= 2 * DAY && Math.abs(w0[1] - S.xmax) <= 2 * DAY) S.winPer = k; });
    const r = build(m, w0[0], w0[1]);
    S.win = w0;
    /* Andy 11-09「上下寬度需要在+寬」：整張圖加高約 50%（桌機 330→500、手機 290→410），下格加最多（要放三段色帶、轉折虛線、百分比標籤）；兩格之間的空白帶 PIV_STRIP 放百分比標籤 */
    const grid = mob ? { l: 34, r: 36, top: 6, h1: 128, gap: 14 + PIV_STRIP, h2: 150 } : { l: 40, r: 42, top: 8, h1: 200, gap: 16 + PIV_STRIP, h2: 200 };
    S.grid = grid; S.cw = el.clientWidth;
    /* 只有一格有資料（例如美股對照指數缺）→ 不畫空的另一格，整張圖的高度讓給有資料的那格（Andy 11-09） */
    S.hasTop = m.tops.length > 0; S.hasBot = !!m.bot;
    const both = S.hasTop && S.hasBot, hAll = grid.h1 + grid.gap + grid.h2 - (S.hasBot ? PIV_STRIP : 0);
    const gTop = { left: grid.l, right: grid.r, top: grid.top, height: both ? grid.h1 : hAll };
    const gBot = { left: grid.l, right: grid.r, top: both ? grid.top + grid.h1 + grid.gap : grid.top + PIV_STRIP, height: both ? grid.h2 : hAll };
    const grids = [S.hasTop ? gTop : null, S.hasBot ? gBot : null].filter(Boolean);
    const botIdx = both ? 1 : 0, nG = grids.length, gIdx = nG === 2 ? [0, 1] : [0];
    const ink3 = CH.ink3 || '#8a94a6', grid2 = CH.grid || 'rgba(128,128,128,.12)';
    const yBase = { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: grid2 } }, axisLabel: { color: ink3, fontFamily: a.NUM_FONT, fontSize: 12 } };
    S.nTick = mob ? 4 : 7;
    const spanDays = (w0[1] - w0[0]) / DAY;
    const xLab = (v) => { const s = ymd(v); return (S.win[1] - S.win[0]) / DAY > 400 ? s.slice(0, 4) + '/' + s.slice(5, 7) : s.slice(5, 7) + '/' + s.slice(8, 10); };
    const xBase = (i) => ({ type: 'time', gridIndex: i, min: S.xmin, max: S.xmax, boundaryGap: false, splitLine: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: CH.line || '#2a3860' } },
      axisLabel: i === nG - 1 ? { color: ink3, fontFamily: a.NUM_FONT, fontSize: 12, hideOverlap: true, margin: 8, formatter: xLab, customValues: xTicks(w0[0], w0[1], S.nTick) } : { show: false }, axisPointer: { show: true, lineStyle: { color: ink3, width: 1, type: 'solid', opacity: 0.55 }, label: { show: false } } });
    const ser = [];
    const ov = overlay(m, r, w0[0], w0[1]);
    r.topSer.forEach((s, i) => ser.push({ id: 'top-' + s.x.k, name: s.x.name, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: s.data, showSymbol: false, symbol: 'circle', symbolSize: 6, lineStyle: { width: s.x.w, color: s.x.c }, itemStyle: { color: s.x.c }, emphasis: { disabled: true }, z: 3 - i / 10,
      markLine: i === 0 ? baseML([{ yAxis: 100 }, ...ov.lines]) : undefined }));
    if (m.bot) ser.push({ id: 'bot-' + m.bot.k, name: m.bot.name, type: 'line', xAxisIndex: botIdx, yAxisIndex: botIdx, data: m.bot.t.map((t, i) => [t, m.bot.v[i]]), showSymbol: false, lineStyle: { width: 2.2, color: m.bot.c }, itemStyle: { color: m.bot.c }, emphasis: { disabled: true },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: rgba(m.bot.c, 0.22) }, { offset: 1, color: rgba(m.bot.c, 0) }] } },
      markArea: bandMark(r.bands), markLine: baseML(ov.lines), markPoint: { silent: true, animation: false, data: ov.pts }, z: 3 });
    S.chart = a.chart(el, {
      animation: false, timeGrid: false, m4dz: false,
      axisPointer: { link: [{ xAxisIndex: gIdx }] },
      grid: grids,
      tooltip: Object.assign({}, a.tip || {}, { trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: ink3, opacity: 0.55 } }, confine: true, formatter: (ps) => { const p = Array.isArray(ps) ? ps[0] : ps; const t = p && (p.axisValue != null ? p.axisValue : p.value && p.value[0]); return t == null ? '' : tipHtml(m, +t); } }),
      xAxis: grids.map((_, i) => xBase(i)),
      yAxis: [S.hasTop ? Object.assign({ gridIndex: 0, min: r.yTop.min, max: r.yTop.max, splitNumber: 3 }, yBase, { axisLabel: Object.assign({}, yBase.axisLabel, { hideOverlap: true, showMinLabel: false, showMaxLabel: false, formatter: (v) => String(Math.round(v)) }) }) : null,
        S.hasBot ? Object.assign({ gridIndex: botIdx, min: r.yBot.min, max: r.yBot.max, splitNumber: both ? 3 : 5 }, yBase, { axisLabel: Object.assign({}, yBase.axisLabel, { hideOverlap: true, formatter: (v) => String(Math.round(v)) }) }) : null].filter(Boolean),
      dataZoom: [
        { type: 'slider', xAxisIndex: gIdx, filterMode: 'none', startValue: w0[0], endValue: w0[1], left: grid.l, right: grid.r, bottom: 4, height: mob ? 22 : 12, showDetail: false, brushSelect: false,
          borderColor: 'transparent', backgroundColor: rgba(ink3, 0.12), fillerColor: rgba(CH.cyan || '#3ee0ff', 0.28), handleSize: mob ? 30 : 16, handleStyle: { color: CH.cyan || '#3ee0ff', borderColor: 'transparent' },
          dataBackground: { lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 } }, selectedDataBackground: { lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 } }, moveHandleSize: 0 },
        /* 游標縮放（Andy 11-09「可以用游標縮放」）：桌機＝滾輪以游標位置為中心縮放、按住拖曳平移；手機＝兩指縮放（pinch），單指不攔截
          （zoomOnMouseWheel／moveOnMouseMove 關掉，單指上下滑才能繼續捲頁，左右平移交給下方細拉Bar）。縮放後視窗最短 7 天。 */
        { type: 'inside', xAxisIndex: gIdx, filterMode: 'none', startValue: w0[0], endValue: w0[1], zoomOnMouseWheel: !mob, moveOnMouseWheel: false, moveOnMouseMove: !mob, preventDefaultMouseMove: !mob, minValueSpan: 7 * DAY },
      ],
      series: ser,
    }, { notMerge: true });
    S.chart.off('datazoom');
    S.chart.on('datazoom', () => {
      if (S._rf) cancelAnimationFrame(S._rf);
      S._rf = requestAnimationFrame(() => {
        const o = S.chart && S.chart.getOption(); const z = o && o.dataZoom && o.dataZoom[0]; if (!z) return;
        const a2 = z.startValue != null ? +z.startValue : S.xmin + z.start / 100 * (S.xmax - S.xmin), b2 = z.endValue != null ? +z.endValue : S.xmin + z.end / 100 * (S.xmax - S.xmin);
        if (S.win && Math.abs(a2 - S.win[0]) < DAY / 2 && Math.abs(b2 - S.win[1]) < DAY / 2) return;
        applyWin(a2, b2);
      });
    });
    if (!el._fzRO && typeof ResizeObserver !== 'undefined') {
      /* 寬度變了（轉手機／拉視窗）→ 轉折點與百分比標籤要依新的像素寬度重排（放得下才畫） */
      let lastW = el.clientWidth;
      el._fzRO = new ResizeObserver(() => { const w = el.clientWidth; if (w && Math.abs(w - lastW) > 2 && S.chart && S.win) { lastW = w; S.cw = w; applyWin(S.win[0], S.win[1]); } });
      el._fzRO.observe(el);
    }
    ctlSync(m);
    const host = document.getElementById('ovFearFull');
    if (host) { host.dataset.mkt = S.mkt; host.dataset.per = S.winPer || ''; host.dataset.win = ymd(w0[0]) + '~' + ymd(w0[1]); host.dataset.names = [...m.tops, ...(m.bot ? [m.bot] : [])].map((x) => x.name).join(','); }
    if (window.App) window.App._fear = { mkt: S.mkt, per: S.winPer, win: [ymd(w0[0]), ymd(w0[1])], base: r.topSer.map((s) => s.base), names: [...m.tops, ...(m.bot ? [m.bot] : [])].map((x) => x.name), n: S.xmax > 0 ? Math.round((S.xmax - S.xmin) / DAY) : 0,
      tw: d.tw ? d.tw.series.length : 0, us: d.us ? d.us.series.length : 0, open: true, piv: pivOut(), th: S.th, hidden: [...S.hide[S.mkt]] };
  }
  window.FearCard = { card, mounted, reveal, load, refresh, setPeriod, _s: S };
})();
