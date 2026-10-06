/* 時間軸垂直分隔線（Andy 2026-10-06：「所有長條圖 類似圖一這種都需要 Y 軸微微區分月份及年份」，DECISIONS #337）

   全站所有「橫軸是時間」的圖，背景加很淡的垂直分隔線，讓人一眼分得出月與年。
   這支只放「與圖表函式庫無關」的共用邏輯，兩條路各自接上：
     · ECharts（app.js 的 chart()）：TimeGrid.echartsSeries(option, el) 回傳要補進 series 的 custom 系列；
     · lightweight-charts（chart.js 的 K 線）：TimeGrid.marks() 算出分隔位置，TimeGridPrimitive 自己畫。

   規格（量過、寫在 docs/ui_polish_spec.md 的「時間軸分隔線」一節）：
     · 線寬 1px，不用彩色，只用主題的次要字色 --ink-3 調透明度（深 年 .30／月 .13、淺 年 .32／月 .15、週日 .09～.10）
     · 依「畫面上看得到的期間」自動換層（拖曳縮放時也跟著換）：
         ≤ 10 天  → 日線（交易日分隔）＋ 週／月／年
         ≤ 62 天  → 週線（每週一）＋ 月／年
         ≤ 5 年   → 月線 ＋ 年線
         > 5 年   → 只留年線（月線太密）
       有「時分」的資料（分 K、1 時、4 時）≤ 62 天都用日線。
     · 月資料（每根就是一個月）不畫月線（每根都有一條＝柵欄）；季資料、年資料同理 → 只畫年線／不畫。
     · 線畫在「兩根之間」（類別軸往左半格），不從柱子中間穿過去。*/
(function (g) {
  'use strict';
  const DAY = 86400000;
  const KIND_RANK = { year: 4, month: 3, week: 2, day: 1 };

  /* 'YYYY-MM-DD'／'YYYY/MM/DD'／'YYYYMMDD'／'YYYY-MM'／'YYYYQn'／'YYYY-Qn'，可後接 'T' 或空白加 hh:mm。
     回傳 { y, m(1..12), d(1..31，沒有就 0), hm(有時分才有，否則 null), gran: 'day'|'month'|'quarter'|'year' }；認不得回 null。 */
  function parse(v) {
    if (v == null) return null;
    if (typeof v === 'number') return null;          // 數字不猜（可能是序號、年份、時間戳；時間戳走 time 軸）
    if (typeof v === 'object') v = v.value != null ? v.value : v.name;
    if (typeof v !== 'string') return null;
    let m = /^(\d{4})[-/.]?(\d{2})[-/.]?(\d{2})(?:[T\s]+(\d{2}):(\d{2}))?/.exec(v);
    if (m && +m[2] >= 1 && +m[2] <= 12 && +m[3] >= 1 && +m[3] <= 31 && (v.length === 8 || /[-/.]/.test(v.slice(4, 5)) || v.length >= 10))
      return { y: +m[1], m: +m[2], d: +m[3], hm: m[4] != null ? m[4] + ':' + m[5] : null, gran: 'day' };
    m = /^(\d{4})[-/.](\d{1,2})$/.exec(v);
    if (m && +m[2] >= 1 && +m[2] <= 12) return { y: +m[1], m: +m[2], d: 0, hm: null, gran: 'month' };
    m = /^(\d{4})[-/ ]?Q([1-4])$/i.exec(v);
    if (m) return { y: +m[1], m: (+m[2] - 1) * 3 + 1, d: 0, hm: null, gran: 'quarter' };
    return null;
  }

  function mondayKey(y, m, d) {       // 該日所在那一週的週一（本地曆）— 當週的識別鍵
    const t = new Date(y, m - 1, d || 1);
    const wd = (t.getDay() + 6) % 7;
    return new Date(y, m - 1, (d || 1) - wd).getTime();
  }

  /* 依「可見期間（天）」決定要畫哪幾層。回傳 { year, month, week, day } 四個布林 */
  function levels(spanDays, intraday) {
    const dayMax = intraday ? 62 : 10;
    return {
      year: true,
      month: spanDays <= 5 * 366,
      week: spanDays <= 62,
      day: spanDays <= dayMax,
    };
  }

  /* 類別軸：entries[i] = parse() 的結果（已確認全是日期）。
     回傳 [{ i, kind }]：第 i 根是「新的一年／月／週／日」的第一根（第 0 根不畫）。
     粒度粗的資料自動略過細的層（月資料沒有 week／day／month；季資料同；年資料整個不畫）。 */
  function entryMs(e) { return new Date(e.y, e.m - 1, e.d || 1).getTime(); }
  /* 平均每根幾天：日線 ≈ 1.4（含週末）、週線 ≈ 7、月線 ≈ 30、季 ≈ 91。分隔線的層級要跟「一根代表多久」配合，
     否則週線圖每根都是新的一週、月線圖每根都是新的一月 → 變成每根一條的柵欄。 */
  function avgStepDays(entries) {
    const n = entries.length; if (n < 2) return 1;
    return Math.max(0.01, (entryMs(entries[n - 1]) - entryMs(entries[0])) / DAY / (n - 1));
  }
  function marksFromEntries(entries) {
    const out = [];
    if (!entries.length) return out;
    const g0 = entries[0].gran;
    if (g0 === 'year') return out;
    const step = avgStepDays(entries);
    const monthOK = g0 === 'day' && step < 20;       // 月線圖不畫月線
    const weekOK = g0 === 'day' && step < 4.5;       // 週線圖不畫週線
    for (let i = 1; i < entries.length; i++) {
      const a = entries[i - 1], b = entries[i];
      let kind = null;
      if (b.y !== a.y) kind = 'year';
      else if (monthOK && b.m !== a.m) kind = 'month';
      else if (weekOK && b.d && a.d && mondayKey(b.y, b.m, b.d) !== mondayKey(a.y, a.m, a.d)) kind = 'week';
      else if (g0 === 'day' && b.hm && b.d !== a.d) kind = 'day';    // 只有「分時資料」才畫日線；日線圖每根就是一天
      if (kind) out.push({ i, kind });
    }
    return out;
  }

  /* 時間軸：給 [minMs, maxMs]，依曆法產生年／月／週一／日的位置（本地時間，跟 ECharts 時間軸刻度同一套） */
  function marksFromRange(minMs, maxMs) {
    const out = [];
    if (!(maxMs > minMs)) return out;
    const spanDays = (maxMs - minMs) / DAY;
    const d0 = new Date(minMs);
    // 年、月
    for (let y = d0.getFullYear(), m = d0.getMonth(); ; ) {
      const t = new Date(y, m, 1).getTime();
      if (t > maxMs) break;
      if (t > minMs) out.push({ t, kind: m === 0 ? 'year' : 'month' });
      if (++m > 11) { m = 0; y++; }
    }
    // 週一（只在 ≤ 62 天時才需要，省得長期間塞一堆用不到的資料）
    if (spanDays <= 62) {
      const w = new Date(d0.getFullYear(), d0.getMonth(), d0.getDate());
      w.setDate(w.getDate() + ((8 - w.getDay()) % 7 || 7));   // 下一個週一
      for (; w.getTime() <= maxMs; w.setDate(w.getDate() + 7)) {
        const t = w.getTime();
        if (t > minMs && !out.some(o => o.t === t)) out.push({ t, kind: 'week' });
      }
    }
    // 日（≤ 10 天，或 ≤ 62 天的分時資料 —— 時間軸這邊拿不到「是不是分時」，用 ≤ 10 天）
    if (spanDays <= 10) {
      const w = new Date(d0.getFullYear(), d0.getMonth(), d0.getDate() + 1);
      for (; w.getTime() <= maxMs; w.setDate(w.getDate() + 1)) {
        const t = w.getTime();
        if (t > minMs && !out.some(o => o.t === t)) out.push({ t, kind: 'day' });
      }
    }
    return out.sort((a, b) => a.t - b.t);
  }

  /* 線的顏色：不用彩色，只用主題的次要字色 --ink-3（灰藍／暖灰）調透明度，所以三套版面風格 × 深淺都跟著換。
     原本想用 --line-2，但淺色主題的 --line-2 本來就接近白（≈ #c2cde1 on #f7fafd），α .45 之後量不到線；
     改用 ink-3 之後兩個主題的「線與底色的差」才在同一個量級（量測見 docs/ui_polish_spec.md）。
     深色底上 ink-3 比底亮，淺色底上 ink-3 比底暗，所以 α 兩組：深 月 .13／年 .30，淺 月 .15／年 .32。 */
  const ALPHA = { dark: { year: 0.26, month: 0.15, week: 0.09, day: 0.09 }, light: { year: 0.22, month: 0.14, week: 0.09, day: 0.09 } };
  /* 期間很長、年線本身就很密（上市以來 22 條年線）時，年線再降一級；Andy 17:40「Y 軸線有點粗，不要那麼明顯」 */
  function densK(visDays) { const y = visDays / 365; return y > 20 ? 0.5 : y > 12 ? 0.65 : y > 8 ? 0.8 : 1; }
  /* 線寬一律「1 個裝置像素」（不是 1 CSS px × dpr）、位置對齊裝置像素的半格，高 DPI 不糊不變粗 */
  function crisp(x) { const d = window.devicePixelRatio || 1; return (Math.round(x * d) + 0.5) / d; }
  function hair() { return 1 / (window.devicePixelRatio || 1); }
  function rgb() {
    try {
      const s = getComputedStyle(document.documentElement).getPropertyValue('--ink-3').trim();
      let m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(s);
      if (m) { let h = m[1]; if (h.length === 3) h = h.replace(/./g, '$&$&'); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
      m = /rgba?\((\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(s);
      if (m) return [+m[1], +m[2], +m[3]];
    } catch (e) { /* 取不到就用保底 */ }
    return [111, 126, 163];
  }
  function color(kind, dens) {
    const c = rgb();
    const lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
    const A = lum > 140 ? ALPHA.dark : ALPHA.light;      // ink-3 偏亮＝深色底
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + +(((A[kind] || .1)) * (dens || 1)).toFixed(3) + ')';
  }

  /* ---------------- ECharts ---------------- */
  const SERIES_ID = '__tgrid';
  const arr = (x) => (Array.isArray(x) ? x : x ? [x] : []);

  /* 這個 xAxis 是不是「日期」軸？是的話回傳 { kind:'time'|'category', entries?, avgDays, intraday, marks }；不是回 null */
  function analyzeAxis(x, series, xi) {
    if (!x || typeof x !== 'object' || x.show === false) return null;
    if (x.timeGrid === false) return null;
    if (x.splitLine && x.splitLine.show === true && x.splitLine.keep === true) return null;   // 呼叫端自己畫了格間分隔線（管理區每日直條）
    if (x.type === 'time') {
      let mn = x.min, mx = x.max;
      if (typeof mn !== 'number' || typeof mx !== 'number') {
        mn = Infinity; mx = -Infinity;
        series.forEach(s => {
          if (!s || (s.xAxisIndex || 0) !== xi || !Array.isArray(s.data)) return;
          for (let k = 0; k < s.data.length; k++) {
            const d = s.data[k]; const v = Array.isArray(d) ? d[0] : (d && Array.isArray(d.value) ? d.value[0] : null);
            const t = typeof v === 'number' ? v : (typeof v === 'string' ? Date.parse(v) : NaN);
            if (isFinite(t)) { if (t < mn) mn = t; if (t > mx) mx = t; }
          }
        });
      }
      if (!isFinite(mn) || !isFinite(mx) || mx <= mn) return null;
      return { kind: 'time', marks: marksFromRange(mn, mx), minMs: mn, maxMs: mx };
    }
    if (x.type === 'category' && Array.isArray(x.data) && x.data.length >= 3) {
      const n = x.data.length;
      const step = Math.max(1, Math.floor(n / 24));
      let okN = 0, tot = 0;
      for (let k = 0; k < n; k += step) { tot++; if (parse(x.data[k])) okN++; }
      if (parse(x.data[n - 1])) okN++; tot++;
      if (okN < tot) return null;       // 只要有一個認不得（'11/05'、'09:30'、'W1'、名稱）就整條不畫，寧缺勿錯
      const entries = x.data.map(parse);
      if (entries.some(e => !e)) return null;
      // 必須照時間先後排（有些圖類別軸是倒序或亂序）
      const key = (e) => e.y * 10000 + e.m * 100 + e.d;
      for (let k = 1; k < n; k++) if (key(entries[k]) < key(entries[k - 1])) return null;
      const t0 = new Date(entries[0].y, entries[0].m - 1, entries[0].d || 1).getTime();
      const t1 = new Date(entries[n - 1].y, entries[n - 1].m - 1, entries[n - 1].d || 1).getTime();
      const marks = marksFromEntries(entries);
      return { kind: 'category', marks, n, avgDays: Math.max(0.2, (t1 - t0) / DAY / Math.max(1, n - 1)), intraday: !!entries[0].hm, gran: entries[0].gran };
    }
    return null;
  }

  /* 回傳要附加到 option.series 的 custom 系列陣列（沒有可畫的就回 []） */
  function echartsSeries(option, el) {
    if (!option || typeof option !== 'object' || option.timeGrid === false) return [];
    if (el && ((el.clientHeight && el.clientHeight < 120) || (el.clientWidth && el.clientWidth < 260))) return [];
    const xs = arr(option.xAxis), ys = arr(option.yAxis), ser = arr(option.series);
    if (!xs.length || !ys.length || !ser.length) return [];
    // 水平長條（類別在 y）不處理；沒有任何「畫資料」的系列也不處理
    if (ys.some(y => y && y.type === 'category')) return [];
    const out = [];
    // 有填色面積的圖（本益比河流、營收河流）：底下的線會被色帶蓋住看不到 → 改畫在色帶上面（α 很低，蓋在資料線上也不搶）；其他圖畫在資料底下
    const overFill = ser.some(s => s && (s.areaStyle || (s.type === 'themeRiver')));
    xs.forEach((x, xi) => {
      const a = analyzeAxis(x, ser, xi);
      if (!a || !a.marks.length) return;
      const gi = x.gridIndex || 0;
      let yi = ys.findIndex(y => y && (y.gridIndex || 0) === gi);
      if (yi < 0) yi = 0;
      const data = a.kind === 'time'
        ? a.marks.map(m => [m.t, KIND_RANK[m.kind]])
        : a.marks.map(m => [m.i, KIND_RANK[m.kind]]);
      const isTime = a.kind === 'time';
      const spanDaysFull = isTime ? (a.maxMs - a.minMs) / DAY : a.avgDays * (a.n - 1);
      out.push({
        id: SERIES_ID + xi, type: 'custom', coordinateSystem: 'cartesian2d', xAxisIndex: xi, yAxisIndex: yi,
        data, silent: true, z: overFill ? 3 : 1, zlevel: 0, clip: true, animation: false,
        legendHoverLink: false, tooltip: { trigger: 'none', show: false },
        encode: { x: 0 }, dimensions: ['x', 'rank'],
        emphasis: { disabled: true },
        renderItem: (params, api) => {
          const rank = api.value(1);
          const cs = params.coordSys;
          const px = isTime ? api.size([DAY, 0])[0] : api.size([1, 0])[0];   // 每天（時間軸）／每根（類別軸）幾像素
          if (!(px > 0)) return null;
          const visDays = isTime ? cs.width / px : cs.width / px * a.avgDays;
          const L = levels(Math.min(visDays, spanDaysFull * 1.01 + 1), !!a.intraday);
          const kind = rank === 4 ? 'year' : rank === 3 ? 'month' : rank === 2 ? 'week' : 'day';
          if (!L[kind]) return null;
          let x = api.coord([api.value(0), 0])[0];
          if (!isTime) x -= px / 2;
          x = crisp(x);
          if (x < cs.x || x > cs.x + cs.width) return null;
          return { type: 'line', shape: { x1: x, y1: cs.y, x2: x, y2: cs.y + cs.height }, silent: true,
            style: { stroke: color(kind, densK(visDays)), lineWidth: hair(), fill: 'none' }, z2: 0 };
        },
      });
    });
    return out;
  }

  /* 在 option 上補一組分隔線系列（回傳新的 option；沒有可畫的原樣回傳）。
     ⚠ 只在「整張圖設定」（有 xAxis 與 series 陣列）時補；之後只換 data 的局部更新沒有 xAxis，原樣放行（上一次補的還在）。
     ⚠ 圖例沒寫 data 的，補上「有名字的系列」，不然 ECharts 會把多出來的系列也列進圖例。 */
  function applyToOption(option, el) {
    try {
      if (!option || typeof option !== 'object' || !option.xAxis || !option.series) return option;
      const extra = echartsSeries(option, el);
      if (!extra.length) return option;
      const base = arr(option.series).filter(s => !(s && typeof s.id === 'string' && s.id.indexOf(SERIES_ID) === 0));
      const o = Object.assign({}, option, { series: base.concat(extra) });
      const lg = option.legend;
      if (lg && !Array.isArray(lg) && lg.data == null && lg.show !== false) {
        const names = [];
        base.forEach(s => { if (s && s.name != null && s.name !== '' && names.indexOf(s.name) < 0) names.push(s.name); });
        o.legend = Object.assign({}, lg, { data: names });
      }
      return o;
    } catch (e) { return option; }     // 外觀失敗不能讓圖畫不出來
  }

  g.TimeGrid = { densK, crisp, hair, parse, entryMs, avgStepDays, levels, marksFromEntries, marksFromRange, color, ALPHA, applyToOption, echartsSeries, SERIES_ID, DAY };
})(window);
