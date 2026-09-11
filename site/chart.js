/* K 線圖層（TradingView Lightweight Charts 5）：多週期、可勾選指標與參數、SMC 區間、
   滾輪縮放價格軸、四週期同看。指標全部在前端算，參數才能即時調。
   台股慣例：紅漲綠跌；KD 9,3,3；RSI Wilder；MACD DIF/MACD/OSC。 */
(function (global) {
  'use strict';
  const LWC = global.LightweightCharts;
  const C = {
    up: '#ff4d6d', down: '#2ee59d', grid: 'rgba(255,255,255,.05)', text: '#a9b6d6', bg: '#0a1020',
    ma: ['#ffd166', '#3ee0ff', '#8b7bff', '#ff8fab', '#c3ff5b', '#ffffff'],
    boll: 'rgba(139,123,255,.75)', k: '#ffd166', d: '#3ee0ff', j: '#ff8fab',
    dif: '#3ee0ff', dea: '#ffd166', rsi: '#c3ff5b', vol: 'rgba(120,140,190,.55)',
    demand: 'rgba(46,229,157,.16)', supply: 'rgba(255,77,109,.16)',
    demandLine: 'rgba(46,229,157,.6)', supplyLine: 'rgba(255,77,109,.6)',
  };

  // ---------------------------------------------------------------- 指標
  const ind = {
    sma(a, n) { const o = new Array(a.length).fill(null); let s = 0; for (let i = 0; i < a.length; i++) { s += a[i]; if (i >= n) s -= a[i - n]; if (i >= n - 1) o[i] = s / n; } return o; },
    ema(a, n) { const o = new Array(a.length).fill(null); const k = 2 / (n + 1); let e = null; for (let i = 0; i < a.length; i++) { e = e === null ? a[i] : a[i] * k + e * (1 - k); o[i] = e; } return o; },
    boll(c, n, k) { const m = ind.sma(c, n); const u = [], l = []; for (let i = 0; i < c.length; i++) { if (m[i] === null) { u.push(null); l.push(null); continue; } let s = 0; for (let j = i - n + 1; j <= i; j++) s += (c[j] - m[i]) ** 2; const sd = Math.sqrt(s / n); u.push(m[i] + k * sd); l.push(m[i] - k * sd); } return { mid: m, up: u, low: l }; },
    macd(c, f, s, g) { const ef = ind.ema(c, f), es = ind.ema(c, s); const dif = c.map((_, i) => ef[i] - es[i]); const dea = ind.ema(dif, g); return { dif, dea, osc: dif.map((v, i) => v - dea[i]) }; },
    rsi(c, n) { // Wilder：前 n 筆變動簡單平均起頭
      const o = new Array(c.length).fill(null); let g = 0, l = 0;
      for (let i = 1; i < c.length; i++) { const d = c[i] - c[i - 1]; const up = Math.max(d, 0), dn = Math.max(-d, 0);
        if (i <= n) { g += up; l += dn; if (i === n) { g /= n; l /= n; o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
        else { g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n; o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
      return o; },
    kd(h, l, c, n, m1, m2) { const K = [], D = [], J = []; let k = 50, d = 50;
      for (let i = 0; i < c.length; i++) { if (i < n - 1) { K.push(null); D.push(null); J.push(null); continue; }
        let hh = -Infinity, ll = Infinity; for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, h[j]); ll = Math.min(ll, l[j]); }
        const rsv = hh === ll ? 50 : (c[i] - ll) / (hh - ll) * 100; k = k * (m1 - 1) / m1 + rsv / m1; d = d * (m2 - 1) / m2 + k / m2;
        K.push(k); D.push(d); J.push(3 * k - 2 * d); }
      return { k: K, d: D, j: J }; },
  };

  // ---------------------------------------------------------------- 時間工具
  const TZ = 8 * 3600;
  function toTime(t) { // 'YYYY-MM-DD' → business day string；ISO 分 K → epoch(+8h)
    if (typeof t === 'number') return t;
    if (t.length === 10) return t;
    const ms = Date.parse(t); return Math.floor(ms / 1000) + TZ;
  }
  function fmtTime(t, tf) {
    if (typeof t === 'string') return t;
    // 分 K 的 epoch 已經加了 8 小時，所以用 UTC 取出來的就是台北牆鐘時間
    const d = new Date(t * 1000);
    const p = (n) => String(n).padStart(2, '0');
    const s = `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
    return tf && /m$/.test(tf) ? `${s} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}` : s;
  }
  // 日 K → 週 K / 月 K（與後端 W-FRI / MS 同口徑：週以最後一個交易日標示）
  function resampleDaily(bars, mode) {
    const out = []; let cur = null, key = null;
    for (const b of bars) {
      const d = new Date(b[0] + 'T00:00:00Z');
      let k;
      if (mode === 'W') { const day = (d.getUTCDay() + 6) % 7; const mon = new Date(d); mon.setUTCDate(d.getUTCDate() - day); k = mon.toISOString().slice(0, 10); }
      else k = b[0].slice(0, 7);
      if (k !== key) { if (cur) out.push(cur); key = k; cur = [b[0], b[1], b[2], b[3], b[4], b[5] || 0]; }
      else { cur[0] = b[0]; cur[2] = Math.max(cur[2], b[2]); cur[3] = Math.min(cur[3], b[3]); cur[4] = b[4]; cur[5] += (b[5] || 0); }
    }
    if (cur) out.push(cur);
    return out;
  }

  // ---------------------------------------------------------------- 區間（SMC）Primitive
  class ZonesPrimitive {
    constructor(zones, opts) { this.zones = zones || []; this.opts = opts || {}; this._series = null; this._chart = null; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    setZones(z) { this.zones = z || []; if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() { const self = this; return [{ zOrder: () => 'bottom', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      if (!self._series) return;
      const x0 = Math.max(0, mediaSize.width * 0.55);
      for (const z of self.zones) {
        const y1 = self._series.priceToCoordinate(z.high), y2 = self._series.priceToCoordinate(z.low);
        if (y1 === null || y2 === null) continue;
        const top = Math.min(y1, y2), h = Math.max(2, Math.abs(y2 - y1));
        ctx.fillStyle = z.kind === 'demand' ? C.demand : C.supply; ctx.fillRect(x0, top, mediaSize.width - x0, h);
        ctx.strokeStyle = z.kind === 'demand' ? C.demandLine : C.supplyLine; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
        ctx.strokeRect(x0 + 0.5, top + 0.5, mediaSize.width - x0 - 1, h - 1); ctx.setLineDash([]);
        ctx.fillStyle = z.kind === 'demand' ? '#2ee59d' : '#ff4d6d'; ctx.font = '11px JetBrains Mono, monospace'; ctx.textAlign = 'left';
        const label = `${z.kind === 'demand' ? '需求' : '供給'}${z.tf ? ' ' + z.tf : ''} ${z.low}–${z.high}`;
        ctx.fillText(label, x0 + 6, Math.max(12, top - 3));
      } }); } }) }]; }
  }

  // ---------------------------------------------------------------- 圖表
  function baseOptions(h) {
    return {
      autoSize: true, layout: { background: { color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, panes: { separatorColor: 'rgba(255,255,255,.08)', separatorHoverColor: 'rgba(62,224,255,.25)', enableResize: true } },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: LWC.CrosshairMode.Normal, vertLine: { labelBackgroundColor: '#1a2542' }, horzLine: { labelBackgroundColor: '#1a2542' } },
      rightPriceScale: { borderColor: 'rgba(255,255,255,.1)', scaleMargins: { top: 0.08, bottom: 0.08 } },
      timeScale: { borderColor: 'rgba(255,255,255,.1)', timeVisible: true, secondsVisible: false, rightOffset: 4, barSpacing: 7 },
      handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      localization: { locale: 'zh-TW', timeFormatter: (t) => fmtTime(t, h && h.tf) },
    };
  }

  class KChart {
    constructor(el, opts) {
      this.el = el; this.opts = Object.assign({ mini: false, tf: '1d' }, opts);
      this.chart = LWC.createChart(el, baseOptions(this.opts));
      this.candle = this.chart.addSeries(LWC.CandlestickSeries, { upColor: C.up, downColor: C.down, borderUpColor: C.up, borderDownColor: C.down, wickUpColor: C.up, wickDownColor: C.down, priceLineVisible: true, lastValueVisible: true });
      this.zones = new ZonesPrimitive([]); this.candle.attachPrimitive(this.zones);
      this.overlays = []; this.panes = {}; this.priceLines = []; this.markers = null;
      this.bars = []; this.tf = this.opts.tf;
      if (!this.opts.mini) this._wheelOnPriceAxis();
    }
    // 滾輪在價格軸上：縮放上下寬度（TradingView 手感）；圖區內滾輪維持時間縮放
    _wheelOnPriceAxis() {
      this.el.addEventListener('wheel', (e) => {
        const rect = this.el.getBoundingClientRect(); const x = e.clientX - rect.left;
        const w = this.chart.priceScale('right').width();
        if (x < rect.width - w) return;
        e.preventDefault(); e.stopPropagation();
        const ps = this.candle.priceScale(); const r = ps.getVisibleRange(); if (!r) return;
        ps.setAutoScale(false);
        const f = e.deltaY > 0 ? 1.12 : 1 / 1.12; const mid = (r.from + r.to) / 2, half = (r.to - r.from) / 2 * f;
        ps.setVisibleRange({ from: mid - half, to: mid + half });
      }, { passive: false });
      this.el.addEventListener('dblclick', () => this.candle.priceScale().setAutoScale(true));
    }
    setBars(bars, tf) {
      this.tf = tf || this.tf; this.bars = bars;
      this.data = bars.map(b => ({ time: toTime(b[0]), open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] || 0 }));
      this.candle.setData(this.data);
      this.chart.applyOptions({ localization: { timeFormatter: (t) => fmtTime(t, this.tf) }, timeScale: { timeVisible: /m$/.test(this.tf) } });
      this.chart.timeScale().scrollToRealTime();
      this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - (this.opts.mini ? 90 : 160)), to: this.data.length + 3 });
    }
    setZones(z) { this.zones.setZones(z); }
    clearOverlays() { for (const s of this.overlays) this.chart.removeSeries(s); this.overlays = []; for (const k in this.panes) { for (const s of this.panes[k]) this.chart.removeSeries(s); } this.panes = {}; }
    _line(vals, color, pane, width, opts) {
      const s = this.chart.addSeries(LWC.LineSeries, Object.assign({ color, lineWidth: width || 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, opts || {}), pane || 0);
      s.setData(this.data.map((d, i) => vals[i] === null || vals[i] === undefined || Number.isNaN(vals[i]) ? null : { time: d.time, value: vals[i] }).filter(Boolean));
      return s;
    }
    _hist(vals, colorFn, pane) {
      const s = this.chart.addSeries(LWC.HistogramSeries, { priceLineVisible: false, lastValueVisible: false, priceFormat: pane === 1 && this.cfg && this.cfg.vol ? { type: 'custom', minMove: 1, formatter: (v) => (Math.abs(v) >= 1e7 ? (v / 1e7).toFixed(1) + '萬張' : (v / 1000).toFixed(0) + '張') } : { type: 'price', precision: 2, minMove: 0.01 } }, pane);
      s.setData(this.data.map((d, i) => vals[i] === null || vals[i] === undefined ? null : { time: d.time, value: vals[i], color: colorFn(i) }).filter(Boolean));
      return s;
    }
    // cfg = {ma:[5,20,60], boll:{n:20,k:2}, vol:true, kd:{n:9,m1:3,m2:3}, macd:{f:12,s:26,g:9}, rsi:{n:14}}
    applyIndicators(cfg) {
      this.clearOverlays(); this.cfg = cfg;
      const c = this.data.map(d => d.close), h = this.data.map(d => d.high), l = this.data.map(d => d.low), v = this.data.map(d => d.volume);
      this.values = {};
      (cfg.ma || []).forEach((n, i) => { const m = ind.sma(c, n); this.values['MA' + n] = m; this.overlays.push(this._line(m, C.ma[i % C.ma.length], 0, 1)); });
      if (cfg.boll) { const b = ind.boll(c, cfg.boll.n, cfg.boll.k); this.values.BOLL = b; this.overlays.push(this._line(b.up, C.boll, 0, 1, { lineStyle: 2 })); this.overlays.push(this._line(b.mid, C.boll, 0, 1)); this.overlays.push(this._line(b.low, C.boll, 0, 1, { lineStyle: 2 })); }
      let pane = 1;
      if (cfg.vol) { this.panes.vol = [this._hist(v, (i) => (this.data[i].close >= this.data[i].open ? 'rgba(255,77,109,.55)' : 'rgba(46,229,157,.55)'), pane)]; if (cfg.volma) { this.panes.vol.push(this._line(ind.sma(v, cfg.volma), '#ffd166', pane, 1)); } this._paneH(pane, 90); pane++; }
      if (cfg.kd) { const k = ind.kd(h, l, c, cfg.kd.n, cfg.kd.m1, cfg.kd.m2); this.values.KD = k; this.panes.kd = [this._line(k.k, C.k, pane, 1), this._line(k.d, C.d, pane, 1)]; this._paneH(pane, 110); pane++; }
      if (cfg.macd) { const m = ind.macd(c, cfg.macd.f, cfg.macd.s, cfg.macd.g); this.values.MACD = m; this.panes.macd = [this._hist(m.osc, (i) => (m.osc[i] >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)'), pane), this._line(m.dif, C.dif, pane, 1), this._line(m.dea, C.dea, pane, 1)]; this._paneH(pane, 110); pane++; }
      if (cfg.rsi) { const r = ind.rsi(c, cfg.rsi.n); this.values.RSI = r; this.panes.rsi = [this._line(r, C.rsi, pane, 1)]; this._paneH(pane, 90); pane++; }
      this._paneH(0, Math.max(280, this.el.clientHeight - (pane - 1) * 105 - 20));
    }
    _paneH(i, h) { const ps = this.chart.panes(); if (ps[i]) ps[i].setHeight(h); }
    setMarkers(marks) { // {bos:[t], choch:[[t,trend]], sweep_low:[t], sweep_high:[t]}
      const has = new Set(this.data.map(d => String(d.time)));
      const m = [];
      const conv = (t) => toTime(t);
      (marks.bos || []).forEach(t => { const tt = conv(t); if (has.has(String(tt))) m.push({ time: tt, position: 'belowBar', color: '#ffd166', shape: 'arrowUp', text: 'BOS' }); });
      (marks.choch || []).forEach(x => { const tt = conv(x[0]); if (has.has(String(tt))) m.push({ time: tt, position: x[1] > 0 ? 'belowBar' : 'aboveBar', color: x[1] > 0 ? '#ff4d6d' : '#2ee59d', shape: x[1] > 0 ? 'arrowUp' : 'arrowDown', text: 'CHoCH' }); });
      (marks.sweep_low || []).forEach(t => { const tt = conv(t); if (has.has(String(tt))) m.push({ time: tt, position: 'belowBar', color: '#3ee0ff', shape: 'circle', text: '掃蕩' }); });
      (marks.sweep_high || []).forEach(t => { const tt = conv(t); if (has.has(String(tt))) m.push({ time: tt, position: 'aboveBar', color: '#3ee0ff', shape: 'circle', text: '掃蕩' }); });
      m.sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
      if (!this.markers) this.markers = LWC.createSeriesMarkers(this.candle, m); else this.markers.setMarkers(m);
    }
    setPriceLines(lines) { // [{price, title, color}]
      for (const p of this.priceLines) this.candle.removePriceLine(p); this.priceLines = [];
      for (const ln of lines) { if (ln.price == null) continue; this.priceLines.push(this.candle.createPriceLine({ price: ln.price, color: ln.color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: ln.title })); }
    }
    onCrosshair(fn) { this.chart.subscribeCrosshairMove((p) => { if (!p.time) { fn(null); return; } const i = this.data.findIndex(d => String(d.time) === String(p.time)); fn(i >= 0 ? i : null); }); }
    fitLast(n) { this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - n), to: this.data.length + 3 }); }
    destroy() { this.chart.remove(); }
  }

  global.KChart = KChart; global.KInd = ind; global.KUtil = { resampleDaily, toTime, fmtTime, colors: C };
})(window);
