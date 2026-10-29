/* ============================================================================
   交易練習室：K 線圖元件（歷史回測與 K 線重播共用）—— 2026-10-28 建
   底層直接用全站的 KChart（site/chart.js）：指標面板（成交量、KD、MACD、RSI）、十字線與圖例、滾輪縮放、副圖拖曳高度都是既有功能；
   繪圖工具用全站的 DrawTools（site/drawtools.js，趨勢線、水平線、方框、測量…），畫的線存在這台裝置的 localStorage。
   這支只補三件事：① 把引擎的逐根資料換成 KChart 的列格式 ② 指標清單的狀態（加／刪／參數／顏色粗細）→ KChart 設定
   ③ 圖表類型（K 線、平均 K、線圖）與進出場箭頭。
   ============================================================================ */
(function () {
  'use strict';
  const LWC = window.LightweightCharts;
  const IND = [
    { id: 'ma', name: '均線 MA', cat: '趨勢', multi: true, p: [['n', '週期', 20, 2, 250]] },
    { id: 'ema', name: 'EMA 指數均線', cat: '趨勢', multi: true, p: [['n', '週期', 20, 2, 250]] },
    { id: 'sar', name: 'SAR 拋物線', cat: '趨勢', p: [['s', '起始', 0.02, 0.001, 0.2], ['i', '加速', 0.02, 0.001, 0.2], ['m', '上限', 0.2, 0.01, 1]] },
    { id: 'st', name: 'Supertrend', cat: '趨勢', p: [['n', 'ATR 週期', 10, 3, 60], ['m', 'ATR 倍數', 3, 0.5, 10]] },
    { id: 'atr', name: 'ATR 平均真實波幅', cat: '波動', p: [['n', '週期', 14, 2, 60]] },
    { id: 'boll', name: '布林通道 BOLL', cat: '波動', p: [['n', '週期', 20, 5, 120], ['k', '倍數', 2, 0.5, 4]] },
    { id: 'vol', name: '成交量', cat: '成交量', p: [] },
    { id: 'kd', name: 'KD 隨機指標', cat: '動能', p: [['n', '週期', 9, 3, 60], ['m1', 'K 平滑', 3, 1, 20], ['m2', 'D 平滑', 3, 1, 20]] },
    { id: 'macd', name: 'MACD', cat: '動能', p: [['f', '快線', 12, 2, 60], ['s', '慢線', 26, 5, 120], ['g', '訊號', 9, 2, 30]] },
    { id: 'rsi', name: 'RSI', cat: '動能', p: [['n', '週期', 14, 2, 60]] },
  ];
  const BY = {}; IND.forEach((x) => { BY[x.id] = x; });
  const TYPES = [['k', 'K 線'], ['ha', '平均 K'], ['line', '線圖']];
  const tfName = (B) => (B.tf === '60' ? '60m' : B.tf === 'W' ? '1w' : B.tf === 'M' ? '1M' : '1d');
  const dayStr = (d) => { const x = new Date(d * 86400000); return x.getUTCFullYear() + '-' + String(x.getUTCMonth() + 1).padStart(2, '0') + '-' + String(x.getUTCDate()).padStart(2, '0'); };
  const ltime = (B, i) => (B.tf === '60' ? B.ts[i] + 8 * 3600 : dayStr(B.day[i]));

  function defaultInd() { return [{ id: 'vol' }]; }
  function newItem(id) { const d = BY[id]; const it = { id }; (d.p || []).forEach(([k, , def]) => { it[k] = def; }); return it; }

  /** 指標清單 → KChart.applyIndicators 的 cfg（簡單均線、布林、成交量、KD、MACD、RSI） */
  function cfgOf(items) {
    const cfg = { ma: [], maColor: [], maWidth: [], lineWidth: 1, st: {} };
    items.forEach((it) => {
      if (it.id === 'ma') { cfg.ma.push(+it.n || 20); cfg.maColor.push(it.color || ''); cfg.maWidth.push(+it.w || 1); }
      else if (it.id === 'boll' && !cfg.boll) { cfg.boll = { n: +it.n || 20, k: +it.k || 2 }; if (it.color || it.w) cfg.st.boll = { c: it.color || undefined, w: +it.w || 1 }; }
      else if (it.id === 'vol') cfg.vol = true;
      else if (it.id === 'kd' && !cfg.kd) { cfg.kd = { n: +it.n || 9, m1: +it.m1 || 3, m2: +it.m2 || 3 }; if (it.color || it.w) cfg.st.kd = { c: it.color || undefined, w: +it.w || 1 }; }
      else if (it.id === 'macd' && !cfg.macd) { cfg.macd = { f: +it.f || 12, s: +it.s || 26, g: +it.g || 9 }; cfg.macdDiv = false; if (it.color || it.w) cfg.st.macd = { c: it.color || undefined, w: +it.w || 1 }; }
      else if (it.id === 'rsi' && !cfg.rsi) { cfg.rsi = { n: +it.n || 14 }; if (it.color || it.w) cfg.st.rsi = { c: it.color || undefined, w: +it.w || 1 }; }
    });
    Object.keys(cfg.st).forEach((k) => { Object.keys(cfg.st[k]).forEach((f) => { if (cfg.st[k][f] === undefined) delete cfg.st[k][f]; }); });
    return cfg;
  }

  function rows(B) { const r = new Array(B.n); for (let i = 0; i < B.n; i++) r[i] = [ltime(B, i), B.o[i], B.h[i], B.l[i], B.c[i], B.v[i]]; return r; }
  /** 平均 K：收＝(開高低收)/4、開＝(前一根平均 K 的開＋收)/2、高低取極值。只用前面的資料，所以重播時不會洩漏未來。 */
  function haRows(B) {
    const r = new Array(B.n); let po = 0, pc = 0;
    for (let i = 0; i < B.n; i++) {
      const c = (B.o[i] + B.h[i] + B.l[i] + B.c[i]) / 4, o = i === 0 ? (B.o[i] + B.c[i]) / 2 : (po + pc) / 2;
      r[i] = [ltime(B, i), o, Math.max(B.h[i], o, c), Math.min(B.l[i], o, c), c, B.v[i]]; po = o; pc = c;
    }
    return r;
  }

  class KView {
    /** o：{ items, drawKey, type } */
    constructor(el, B, o) {
      o = o || {}; this.el = el; this.B = B; this.items = o.items || defaultInd(); this.type = o.type || 'k'; this.drawKey = o.drawKey || '';
      this.R = { k: rows(B), ha: null }; this.upto = B.n - 1;
      this.kc = new window.KChart(el, { tf: tfName(B) });
      this.kc.loadOlder = () => {};          // 往左拖到頭不要去抓別的資料：這裡的資料就是全部
      this.line = null; this.mk = null;
      this.fixScale();
      try { this.chart.applyOptions({ rightPriceScale: { ensureEdgeTickMarksVisible: false } }); } catch (e) { /* 圖剛銷毀 */ }   // 手機 KChart 強制畫最下一格刻度，會把價格軸拉到負數；練習室不要
    }
    /** 進出場箭頭不參與 Y 軸自動縮放：箭頭堆疊會讓價格軸最低衝到負數（台指期「全部」曾到 -7500）。
        自己用可視範圍內的 K 棒高低點算範圍，箭頭再多也撐不動軸。 */
    fixScale() {
      try {
        const self = this;
        this.candle.applyOptions({ autoscaleInfoProvider: (orig) => {
          try {
            const rg = self.chart.timeScale().getVisibleLogicalRange(), d = self.kc.data || [];
            if (!rg || !d.length) return orig();
            let lo = Infinity, hi = -Infinity;
            for (let i = Math.max(0, Math.floor(rg.from)); i <= Math.min(d.length - 1, Math.ceil(rg.to)); i++) { if (d[i].low < lo) lo = d[i].low; if (d[i].high > hi) hi = d[i].high; }
            if (!(hi > lo)) return orig();
            return { priceRange: { minValue: lo, maxValue: hi } };
          } catch (e) { return orig(); }
        } });
      } catch (e) { /* 圖剛銷毀 */ }
    }
    get chart() { return this.kc.chart; }
    get candle() { return this.kc.candle; }
    rowsNow() { if (this.type === 'ha') { if (!this.R.ha) this.R.ha = haRows(this.B); return this.R.ha; } return this.R.k; }
    /** 畫到第 upto 根（含）。keep＝保留目前的取景（重播逐根往前時用）。 */
    set(upto, keep) {
      this.upto = upto == null ? this.B.n - 1 : upto;
      this.kc.setBars(this.rowsNow().slice(0, this.upto + 1), tfName(this.B), !!keep);
      this.applyInd(); this.paintLine();
      try { this.candle.applyOptions({ lastValueVisible: false, priceLineVisible: false }); } catch (e) { /* 圖剛銷毀 */ }   // 右軸最新價標籤會壓到刻度字（不可重疊）
    }
    applyInd(items) {
      if (items) this.items = items;
      try { this.kc.applyIndicators(cfgOf(this.items)); } catch (e) { /* 圖剛銷毀 */ }
      this.paintExtras(); this.volUnit();
    }
    /** 期貨成交量單位是「口」，不是「張」：全站 KChart 的量軸固定除以 1000 寫「張」，這裡針對期貨改寫量軸文字。 */
    volUnit() {
      if (!/口/.test(this.B.vu || '')) return;
      try {
        const ps = this.chart.panes(); if (!ps[1]) return;
        const f = (v) => (Math.abs(v) >= 1e4 ? (v / 1e4).toFixed(1) + '萬口' : Math.round(v) + '口');
        const mob = innerWidth <= 640;   // 手機 KChart 另掛 tickmarksFormatter（寫死「張」），只在手機一併蓋掉；桌機不動
        const pf = mob ? { type: 'custom', minMove: 1, formatter: f, tickmarksFormatter: (a) => a.map((v) => (v < 0 ? '' : v === 0 ? '0' : f(v))) } : { type: 'custom', minMove: 1, formatter: f };
        ps[1].getSeries().forEach((x) => { try { x.applyOptions({ priceFormat: pf }); } catch (e) { /* 不是量序列 */ } });
      } catch (e) { /* 圖剛銷毀 */ }
    }
    /** 全站 KChart 沒有的指標（EMA、SAR、Supertrend、ATR）：另外畫在同一張圖上，公式與回測引擎同一份（LabEngine.I），只畫到目前這一根（重播不洩漏未來）。 */
    paintExtras() {
      (this.ex || []).forEach((x) => { try { this.chart.removeSeries(x); } catch (e) { /* 已移除 */ } });
      this.ex = [];
      const E = window.LabEngine, B = this.B, u = this.upto + 1;
      if (!E || !E.I) return;
      const add = (arr, o, pane) => {
        const sr = this.chart.addSeries(LWC.LineSeries, Object.assign({ priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, o), pane);
        const d = []; for (let i = 0; i < u; i++) if (Number.isFinite(arr[i])) d.push({ time: ltime(B, i), value: arr[i] });
        sr.setData(d); this.ex.push(sr); return sr;
      };
      const pal = ['#ff9f1c', '#2ec4b6', '#e71d36', '#9b5de5'];
      let k = 0;
      this.items.forEach((it) => {
        const col = it.color || pal[k++ % pal.length], w = +it.w || 1;
        try {
          if (it.id === 'ema') add(E.I.ema(B.c, +it.n || 20), { color: col, lineWidth: w });
          else if (it.id === 'sar') { const r = E.I.sar(B.h, B.l, +it.s || 0.02, +it.i || 0.02, +it.m || 0.2); add(r.sar, { color: col, lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2 }); }
          else if (it.id === 'st') {
            const r = E.I.supertrend(B.h, B.l, B.c, +it.n || 10, +it.m || 3), up = new Float64Array(B.n).fill(NaN), dn = new Float64Array(B.n).fill(NaN);
            for (let i = 0; i < B.n; i++) { if (r.trend[i] === 1) up[i] = r.line[i]; else if (r.trend[i] === -1) dn[i] = r.line[i]; }
            add(up, { color: '#e63946', lineWidth: w }); add(dn, { color: '#2a9d8f', lineWidth: w });
          } else if (it.id === 'atr') { const pi = this.chart.panes().length; add(E.I.atr(B.h, B.l, B.c, +it.n || 14), { color: col, lineWidth: w }, pi); try { this.chart.panes()[pi].setStretchFactor(90); } catch (e) { /* 舊版沒有 stretch */ } }
        } catch (e) { /* 圖剛銷毀 */ }
      });
    }
    setType(t) { this.type = t; this.set(this.upto, true); }
    paintLine() {
      const c = this.candle, LW = LWC;
      if (this.line) { try { this.chart.removeSeries(this.line); } catch (e) { /* 忽略 */ } this.line = null; }
      if (this.type !== 'line') { this.restoreColors(); return; }
      const ph = 'rgba(0,0,0,0)';      // 線圖：K 棒本身透明（進出場箭頭與繪圖工具還掛在這條序列上），另畫一條收盤線
      c.applyOptions({ upColor: ph, downColor: ph, borderUpColor: ph, borderDownColor: ph, wickUpColor: ph, wickDownColor: ph });
      this.line = this.chart.addSeries(LW.LineSeries, { color: getComputedStyle(document.documentElement).getPropertyValue('--cyan').trim() || '#3ee0ff', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
      const d = this.kc.data || []; this.line.setData(d.map((x) => ({ time: x.time, value: x.close })));
    }
    restoreColors() {
      const s = getComputedStyle(document.documentElement), up = s.getPropertyValue('--rise').trim() || '#ff4d6d', dn = s.getPropertyValue('--fall').trim() || '#2ee59d';
      this.candle.applyOptions({ upColor: up, downColor: dn, borderUpColor: up, borderDownColor: dn, wickUpColor: up, wickDownColor: dn });
    }
    /** 同一根 K 棒最多一個進場、一個出場標記。 */
    static thin(marks) {
      const seen = {}, out = [];
      marks.forEach((m) => { const k = m.time + '|' + (m.role || m.position); if (!seen[k]) { seen[k] = 1; out.push(m); } });
      return out;
    }
    /** 只畫可視範圍內的標記；可視範圍內超過 400 個就一個都不畫（寧可不畫，也不准糊成色塊蓋住 K 線），放大到夠疏才出現。 */
    applyMarks() {
      let list = this.allMarks || [];
      try {
        const vr = this.chart.timeScale().getVisibleRange();
        if (vr) list = list.filter((m) => m.time >= vr.from && m.time <= vr.to);
      } catch (e) { /* 圖剛銷毀 */ }
      if (list.length > 400) list = [];
      const sig = list.length + '|' + (list[0] ? list[0].time : '') + '|' + (list.length ? list[list.length - 1].time : '');
      if (sig === this.markSig && this.mk) return;
      this.markSig = sig;
      if (!this.mk) this.mk = LWC.createSeriesMarkers(this.candle, list); else this.mk.setMarkers(list);
    }
    /** 價格不可能是負的：下緣留白依可視最低價限縮，讓軸底不低於 0。 */
    clampMargin() {
      try {
        const rg = this.chart.timeScale().getVisibleLogicalRange(), d = this.kc.data || [];
        if (!rg || !d.length) return;
        let lo = Infinity, hi = -Infinity;
        for (let i = Math.max(0, Math.floor(rg.from)); i <= Math.min(d.length - 1, Math.ceil(rg.to)); i++) { if (d[i].low < lo) lo = d[i].low; if (d[i].high > hi) hi = d[i].high; }
        if (!(lo > 0) || !(hi > lo)) return;
        const ps = this.candle.priceScale(), cur = (ps.options() || {}).scaleMargins || {}, t = cur.top != null ? cur.top : 0.2;
        const b = Math.max(0, Math.min(0.08, 0.9 * lo * (1 - t) / hi));
        if (Math.abs((cur.bottom != null ? cur.bottom : 0.08) - b) > 0.002 && this.mgB !== b) { this.mgB = b; ps.applyOptions({ scaleMargins: { top: t, bottom: b } }); }
      } catch (e) { /* 圖剛銷毀 */ }
    }
    setMarkers(marks) {
      this.allMarks = KView.thin(marks); this.markSig = null;
      if (!this.rsub) { this.rsub = true; this.chart.timeScale().subscribeVisibleLogicalRangeChange(() => { this.applyMarks(); this.clampMargin(); }); }
      this.applyMarks(); this.clampMargin();
    }
    enableDraw(barEl) {
      if (!window.DrawTools) return;
      this.kc.enableDrawing(this.drawKey);
      if (barEl) window.DrawTools.mountBar(barEl, { tool: 'cursor', get: () => this.kc.draw || null, onTool: () => {} });
    }
    destroy() { try { this.kc.destroy(); } catch (e) { /* 已銷毀 */ } this.mk = null; this.line = null; }
  }

  window.LabK = { IND, BY, TYPES, defaultInd, newItem, cfgOf, rows, haRows, KView, tfName, ltime };
}());
