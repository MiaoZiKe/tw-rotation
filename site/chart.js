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
        if (i <= n) { g += up; l += dn; if (i === n) { g /= n; l /= n; o[i] = (l === 0 && g === 0) ? null : l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
        else { g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n; o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
      return o; },
    /* MACD 背離（Andy 2026-09-15：「若MACD 出現底背離或是頂背離需要額外標出，因為這是很好的訊號」）
       頂背離：價格創更高的高點、MACD 的高點卻更低 → 動能跟不上，漲勢可能到頂
       底背離：價格創更低的低點、MACD 的低點卻更高 → 賣壓遞減，跌勢可能到底
       用 DIF（快線）當比較基準，這是台股習慣的口徑。
       `left/right` 是找轉折點的視窗：兩側各 n 根都比它低（高）才算一個高（低）點，
       這樣不會把雜訊當轉折。只回最近幾組，圖上不要標滿。 */
    divergence(close, high, low, dif, opt) {
      const o = Object.assign({ left: 5, right: 5, maxGap: 90, minGap: 8, keep: 4 }, opt || {});
      const n = close.length;
      const piv = (arr, hi) => {
        const out = [];
        for (let i = o.left; i < n - o.right; i++) {
          if (arr[i] == null) continue;
          let ok = true;
          for (let j = i - o.left; j <= i + o.right; j++) {
            if (j === i || arr[j] == null) continue;
            if (hi ? arr[j] > arr[i] : arr[j] < arr[i]) { ok = false; break; }
          }
          if (ok) out.push(i);
        }
        return out;
      };
      const res = { top: [], bottom: [] };
      const scan = (arr, hi, bucket) => {
        const ps = piv(arr, hi);
        for (let k = 1; k < ps.length; k++) {
          const i = ps[k - 1], j = ps[k];
          const gap = j - i;
          if (gap < o.minGap || gap > o.maxGap) continue;
          if (dif[i] == null || dif[j] == null) continue;
          const priceUp = arr[j] > arr[i], difUp = dif[j] > dif[i];
          // 頂背離：價更高、DIF 更低；底背離：價更低、DIF 更高
          if (hi ? (priceUp && !difUp) : (!priceUp && difUp)) {
            bucket.push({ i, j, p1: arr[i], p2: arr[j], d1: dif[i], d2: dif[j] });
          }
        }
      };
      scan(high || close, true, res.top);
      scan(low || close, false, res.bottom);
      res.top = res.top.slice(-o.keep);
      res.bottom = res.bottom.slice(-o.keep);
      return res;
    },
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
  /* SMC 供需區。兩件事很重要：
     1. 右邊只畫到「最後一根 K 棒」，不是畫到整個畫面的右緣 ——
        以前填到畫面右緣，平移時兩邊都貼著邊，看起來就像整片色塊黏在畫面上不會動
        （其實有動，但使用者感受不到）。現在右邊界跟著最後一根 K 棒跑，一眼看得出它在動。
     2. 顏色、透明度、線寬全部吃設定，不要寫死 —— 每個人能接受的濃度差很多。 */
  const ZONE_DEF = { demand: '#2ee59d', supply: '#ff4d6d', fill: 14, line: 60, width: 1, label: true };
  const hexa = (hex, pct) => {
    const h = hex.replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const r = parseInt(n.slice(0, 2), 16), g = parseInt(n.slice(2, 4), 16), b = parseInt(n.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${Math.max(0, Math.min(100, pct)) / 100})`;
  };
  class ZonesPrimitive {
    constructor(zones, style) { this.zones = zones || []; this.st = Object.assign({}, ZONE_DEF, style || {}); this._series = null; this._chart = null; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    setZones(z, style) { this.zones = z || []; if (style) this.st = Object.assign({}, ZONE_DEF, style); if (this._req) this._req(); }
    setStyle(style) { this.st = Object.assign({}, ZONE_DEF, style || {}); if (this._req) this._req(); }
    setLastTime(t) { this.lastTime = t; if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() { const self = this; return [{ zOrder: () => 'bottom', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      if (!self._series) return;
      const st = self.st;
      const ts = self._chart && self._chart.timeScale();
      // 右邊界＝最後一根 K 棒的位置（再留一點餘裕），不是畫面右緣
      let xEnd = mediaSize.width;
      if (self.lastTime != null && ts) {
        const e = ts.timeToCoordinate(self.lastTime);
        if (e !== null && isFinite(e)) xEnd = Math.min(mediaSize.width, e + 6);
      }
      const used = [];
      for (const z of self.zones) {
        const y1 = self._series.priceToCoordinate(z.high), y2 = self._series.priceToCoordinate(z.low);
        if (y1 === null || y2 === null) continue;
        const top = Math.min(y1, y2), h = Math.max(2, Math.abs(y2 - y1));
        let x0 = 0;
        if (z.since && ts) { const c = ts.timeToCoordinate(toTime(z.since)); if (c !== null && isFinite(c)) x0 = c; }
        if (x0 >= xEnd) continue;              // 整段在可視範圍右邊，還沒形成
        const xs = Math.max(0, x0), w = xEnd - xs;
        if (w <= 1) continue;
        const dem = z.kind === 'demand';
        const base = dem ? st.demand : st.supply;
        ctx.fillStyle = hexa(base, st.fill);
        ctx.fillRect(xs, top, w, h);
        ctx.strokeStyle = hexa(base, st.line); ctx.lineWidth = st.width || 1;
        ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(xs, top + .5); ctx.lineTo(xEnd, top + .5);
        ctx.moveTo(xs, top + h - .5); ctx.lineTo(xEnd, top + h - .5); ctx.stroke();
        ctx.setLineDash([]);
        // 起點那一側封一條實線，看得出「這個區間是從哪一天開始成立的」
        if (x0 > 1) { ctx.beginPath(); ctx.moveTo(x0 + .5, top); ctx.lineTo(x0 + .5, top + h); ctx.stroke(); }
        if (!st.label) continue;
        const label = `${dem ? '需求' : '供給'}${z.tf ? ' ' + z.tf : ''} ${z.low}–${z.high}`;
        ctx.font = '600 10.5px JetBrains Mono, monospace'; ctx.textAlign = 'left';
        // 標籤放在區間上緣外面，不要蓋在區間中央的 K 棒上
        let ly = top - 3;
        while (used.some(u => Math.abs(u - ly) < 13)) ly -= 13;
        if (ly < 12) ly = top + h + 11;
        used.push(ly);
        const tw = ctx.measureText(label).width;
        // 優先放在最後一根 K 棒右邊的空白處；放不下才退回區間右端
        const lx = (xEnd + 4 + tw <= mediaSize.width - 2) ? xEnd + 4
          : Math.min(Math.max(xEnd - tw - 6, xs + 4), mediaSize.width - tw - 6);
        ctx.fillStyle = 'rgba(10,16,32,.82)'; ctx.fillRect(lx - 3, ly - 10, tw + 7, 13);
        ctx.fillStyle = base; ctx.fillText(label, lx, ly);
      } }); } }) }]; }
  }

  /* ---------------------------------------------------------------- 繪圖層（參考 TradingView）
     支援：趨勢線、射線、水平線、矩形、文字。座標存 {t: 時間, p: 價格}，
     所以縮放平移都會跟著跑，不是畫在畫布上的死線。
     每檔每週期各存一份在 localStorage。 */
  const DRAW_TOOLS = [
    { k: 'cursor', label: '選取', icon: 'M4,2 L4,15 L7.5,11.6 L10,16 L12,15 L9.5,10.7 L14,10.5 Z', pts: 0 },
    { k: 'trend', label: '趨勢線', icon: 'M2,15 L16,3', pts: 2 },
    { k: 'ray', label: '射線', icon: 'M2,15 L16,3 M11,3 L16,3 L16,8', pts: 2 },
    { k: 'hline', label: '水平線', icon: 'M1,9 L17,9', pts: 1 },
    { k: 'rect', label: '矩形', icon: 'M3,4 H15 V14 H3 Z', pts: 2 },
    { k: 'text', label: '文字', icon: 'M3,4 H15 M9,4 V15', pts: 1 },
    { k: 'erase', label: '刪除', icon: 'M4,5 H15 M6,5 V15 H13 V5 M8,8 V13 M11,8 V13', pts: 0 },
  ];
  const DRAW_COLORS = ['#3ee0ff', '#ffd166', '#ff4d6d', '#2ee59d', '#8b7bff', '#e8eeff'];

  class DrawPrimitive {
    constructor(mgr) { this.m = mgr; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    update() { if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() {
      const self = this;
      return [{ zOrder: () => 'top', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
        if (!self._series || !self._chart) return;
        const ts = self._chart.timeScale();
        const X = (t) => { const c = ts.timeToCoordinate(t); return c === null ? null : c; };
        const Y = (p) => self._series.priceToCoordinate(p);
        const all = self.m.shapes.concat(self.m.draft ? [self.m.draft] : []);
        for (const s of all) {
          ctx.save();
          ctx.strokeStyle = s.color || '#3ee0ff'; ctx.fillStyle = s.color || '#3ee0ff';
          ctx.lineWidth = s.w || 1.5; ctx.setLineDash(s.dash ? [5, 4] : []);
          const a = s.a, b = s.b;
          const ax = a ? X(a.t) : null, ay = a ? Y(a.p) : null;
          const bx = b ? X(b.t) : null, by = b ? Y(b.p) : null;
          if (s.kind === 'hline' && ay !== null) {
            ctx.beginPath(); ctx.moveTo(0, ay); ctx.lineTo(mediaSize.width, ay); ctx.stroke();
            ctx.font = '600 10.5px JetBrains Mono, monospace'; ctx.textAlign = 'left';
            const lab = String(Math.round(a.p * 100) / 100);
            ctx.fillStyle = 'rgba(10,16,32,.85)'; ctx.fillRect(3, ay - 12, ctx.measureText(lab).width + 8, 13);
            ctx.fillStyle = s.color; ctx.fillText(lab, 7, ay - 2);
          } else if (s.kind === 'text' && ax !== null && ay !== null) {
            ctx.font = '600 12px "Noto Sans TC", sans-serif'; ctx.textAlign = 'left';
            const t = s.text || '文字';
            const w = ctx.measureText(t).width;
            ctx.fillStyle = 'rgba(10,16,32,.8)'; ctx.fillRect(ax - 3, ay - 13, w + 8, 17);
            ctx.fillStyle = s.color; ctx.fillText(t, ax + 1, ay);
          } else if (ax !== null && ay !== null && bx !== null && by !== null) {
            if (s.kind === 'rect') {
              // fill=true 實心（濃一點看得出範圍）、false 只有框線（不遮住 K 棒）
              if (s.fill) { ctx.globalAlpha = .28; ctx.fillRect(Math.min(ax, bx), Math.min(ay, by), Math.abs(bx - ax), Math.abs(by - ay)); }
              ctx.globalAlpha = 1; ctx.strokeRect(Math.min(ax, bx) + .5, Math.min(ay, by) + .5, Math.abs(bx - ax), Math.abs(by - ay));
            } else {
              let ex = bx, ey = by;
              if (s.kind === 'ray') { const dx = bx - ax, dy = by - ay; const k = dx === 0 ? 9999 : (mediaSize.width - ax) / dx; if (k > 0) { ex = ax + dx * k; ey = ay + dy * k; } }
              ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ex, ey); ctx.stroke();
              if (s === self.m.hot) { ctx.fillStyle = s.color; [[ax, ay], [bx, by]].forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 3.5, 0, 7); ctx.fill(); }); }
            }
          }
          ctx.restore();
        }
      }); } }) }];
    }
  }

  /* 背離連線。把兩個轉折點用虛線連起來並標字，主圖與 MACD 面板各掛一個。
     值是用 index 存的（不是時間），因為 MACD 面板的 series 與主圖共用同一組 index。 */
  class DivPrimitive {
    constructor() { this.items = []; this.times = []; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    set(items, times) { this.items = items || []; this.times = times || []; if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() {
      const self = this;
      return [{ zOrder: () => 'top', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx }) => {
        if (!self._series || !self._chart || !self.items.length) return;
        const ts = self._chart.timeScale();
        ctx.save();
        ctx.font = '700 10.5px "Noto Sans TC", sans-serif';
        for (const it of self.items) {
          const t1 = self.times[it.i], t2 = self.times[it.j];
          if (t1 == null || t2 == null) continue;
          const x1 = ts.timeToCoordinate(t1), x2 = ts.timeToCoordinate(t2);
          const y1 = self._series.priceToCoordinate(it.v1), y2 = self._series.priceToCoordinate(it.v2);
          if (x1 === null || x2 === null || y1 === null || y2 === null) continue;
          const col = it.kind === 'top' ? '#ff4d6d' : '#2ee59d';
          ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1.6;
          ctx.setLineDash([5, 3]);
          ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
          ctx.setLineDash([]);
          [[x1, y1], [x2, y2]].forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 3, 0, 7); ctx.fill(); });
          if (!it.label) continue;
          const up = it.kind === 'top';
          const tx = (x1 + x2) / 2, tyRaw = (y1 + y2) / 2 + (up ? -10 : 16);
          const w = ctx.measureText(it.label).width;
          ctx.fillStyle = hexa('#0a1020', 82);
          ctx.fillRect(tx - w / 2 - 4, tyRaw - 11, w + 8, 14);
          ctx.fillStyle = col; ctx.textAlign = 'center';
          ctx.fillText(it.label, tx, tyRaw);
        }
        ctx.restore();
      }); } }) }];
    }
  }

  class Drawings {
    constructor(kc, key) {
      this.kc = kc; this.key = key; this.shapes = []; this.draft = null; this.tool = 'cursor';
      this.color = DRAW_COLORS[0]; this.w = 1.5; this.hot = null;
      this.fill = false;               // 方框要不要填滿（Andy 2026-09-15）
      this.prim = new DrawPrimitive(this);
      kc.candle.attachPrimitive(this.prim);
      this.load();
      this._bind();
    }
    setTool(t) { this.tool = t; this.kc.el.style.cursor = t === 'cursor' ? '' : (t === 'erase' ? 'not-allowed' : 'crosshair'); this._lock(t !== 'cursor'); }
    setColor(c) { this.color = c; if (this.hot) { this.hot.color = c; this.save(); this.prim.update(); } }
    setWidth(w) { this.w = w; if (this.hot) { this.hot.w = w; this.save(); this.prim.update(); } }
    setFill(on) { this.fill = !!on; if (this.hot) { this.hot.fill = this.fill; this.save(); this.prim.update(); } }
    _lock(on) { this.kc.chart.applyOptions({ handleScroll: { pressedMouseMove: !on, horzTouchDrag: !on }, handleScale: { axisPressedMouseMove: { time: !on, price: !on } } }); }
    _at(e) {
      const r = this.kc.el.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      const t = this.kc.chart.timeScale().coordinateToTime(x);
      const p = this.kc.candle.coordinateToPrice(y);
      return (t === null || p === null) ? null : { t, p, x, y };
    }
    _bind() {
      const el = this.kc.el;
      el.addEventListener('pointerdown', (e) => {
        if (this.tool === 'cursor') return;
        const a = this._at(e); if (!a) return;
        e.preventDefault(); e.stopPropagation();
        if (this.tool === 'erase') { this._eraseAt(a); return; }
        const def = DRAW_TOOLS.find(d => d.k === this.tool);
        if (def.pts === 1) {
          const s = { kind: this.tool, a: { t: a.t, p: a.p }, color: this.color, w: this.w };
          if (this.tool === 'text') { const v = this.kc.opts.onText && this.kc.opts.onText(); s.text = v || '文字'; }
          this.shapes.push(s); this.save(); this.prim.update();
          if (this.kc.opts.onDrawEnd) this.kc.opts.onDrawEnd();
          return;
        }
        this.draft = { kind: this.tool, a: { t: a.t, p: a.p }, b: { t: a.t, p: a.p }, color: this.color, w: this.w, fill: this.fill };
        const start = a;
        /* Andy 2026-09-15：「當拉線時，按著Shift 會主動變成水平線」。
           一併支援垂直：看滑鼠往哪個方向拉得比較多，橫向就鎖成水平（價格不變），
           縱向就鎖成垂直（時間不變）。TradingView 也是這個手感。 */
        const move = (ev) => {
          const b = this._at(ev); if (!b || !this.draft) return;
          let t = b.t, p = b.p;
          if (ev.shiftKey) {
            if (Math.abs(b.x - start.x) >= Math.abs(b.y - start.y)) p = start.p;   // 水平
            else t = start.t;                                                       // 垂直
          }
          this.draft.b = { t, p }; this.draft.shift = !!ev.shiftKey; this.prim.update();
        };
        const up = () => {
          el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up);
          if (this.draft) { this.shapes.push(this.draft); this.draft = null; this.save(); this.prim.update(); }
          if (this.kc.opts.onDrawEnd) this.kc.opts.onDrawEnd();
        };
        el.addEventListener('pointermove', move); el.addEventListener('pointerup', up);
      }, true);
    }
    _eraseAt(a) {
      const ts = this.kc.chart.timeScale();
      const X = (t) => ts.timeToCoordinate(t), Y = (p) => this.kc.candle.priceToCoordinate(p);
      const near = (s) => {
        const ax = X(s.a.t), ay = Y(s.a.p);
        if (s.kind === 'hline') return ay !== null && Math.abs(ay - a.y) < 7;
        if (s.kind === 'text') return ax !== null && ay !== null && Math.abs(ax - a.x) < 60 && Math.abs(ay - a.y) < 12;
        const bx = X(s.b.t), by = Y(s.b.p);
        if (ax === null || bx === null || ay === null || by === null) return false;
        if (s.kind === 'rect') {
          const inX = a.x >= Math.min(ax, bx) - 5 && a.x <= Math.max(ax, bx) + 5;
          const inY = a.y >= Math.min(ay, by) - 5 && a.y <= Math.max(ay, by) + 5;
          return inX && inY;
        }
        const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
        const u = L2 ? Math.max(0, Math.min(1, ((a.x - ax) * dx + (a.y - ay) * dy) / L2)) : 0;
        return Math.hypot(a.x - (ax + u * dx), a.y - (ay + u * dy)) < 7;
      };
      const i = this.shapes.findIndex(near);
      if (i >= 0) { this.shapes.splice(i, 1); this.save(); this.prim.update(); }
    }
    undo() { this.shapes.pop(); this.save(); this.prim.update(); }
    clear() { this.shapes = []; this.save(); this.prim.update(); }
    save() { try { localStorage.setItem(this.key, JSON.stringify(this.shapes)); } catch (e) { /* 私密模式等情況忽略 */ } }
    load() { try { const s = localStorage.getItem(this.key); this.shapes = s ? JSON.parse(s) : []; } catch (e) { this.shapes = []; } }
    destroy() { try { this.kc.candle.detachPrimitive(this.prim); } catch (e) { /* 圖已銷毀 */ } }
  }

  // ---------------------------------------------------------------- 圖表
  /* 主題：色票 C 的預設值是深色，切到明亮主題時由 refreshTheme() 就地改寫。
     Lightweight Charts 的顏色是建圖當下寫進去的，所以換主題一定要把圖重建（app.js 會重跑 route()）。 */
  function refreshTheme() {
    const s = getComputedStyle(document.documentElement);
    const v = (n, d) => (s.getPropertyValue(n) || '').trim() || d;
    C.up = v('--rise', '#ff4d6d'); C.down = v('--fall', '#2ee59d');
    C.bg = v('--chartbg', '#0a1020'); C.text = v('--ink-2', '#a9b6d6');
    C.grid = v('--grid', 'rgba(255,255,255,.05)');
    C.line = v('--line-2', '#2a3860'); C.panel3 = v('--panel-3', '#1a2542');
    return C;
  }

  function baseOptions(h) {
    refreshTheme();
    return {
      autoSize: true, layout: { background: { color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, panes: { separatorColor: C.grid, separatorHoverColor: 'rgba(62,224,255,.25)', enableResize: true } },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: LWC.CrosshairMode.Normal, vertLine: { labelBackgroundColor: C.panel3 }, horzLine: { labelBackgroundColor: C.panel3 } },
      rightPriceScale: { borderColor: C.line, scaleMargins: { top: 0.08, bottom: 0.08 } },
      timeScale: { borderColor: C.line, timeVisible: true, secondsVisible: false, rightOffset: 4, barSpacing: 7 },
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
      this.divPrice = new DivPrimitive(); this.candle.attachPrimitive(this.divPrice);
      this.divPane = null;               // MACD 面板那一條，等 applyIndicators 建好 series 才掛
      this.overlays = []; this.panes = {}; this.priceLines = []; this.markers = null;
      this.bars = []; this.tf = this.opts.tf; this.paneIndex = {};
      if (!this.opts.mini) {
        this.labels = document.createElement('div'); this.labels.className = 'pane-labels'; el.appendChild(this.labels);
        this.wm = document.createElement('div'); this.wm.className = 'k-wm'; el.appendChild(this.wm);
        this._wheelOnPriceAxis();
        this._ro = new ResizeObserver(() => this._layoutLabels()); this._ro.observe(el);
      }
    }
    setWatermark(text) { if (this.wm) this.wm.textContent = text || ''; }
    // 各指標面板左上角的標題（成交量 / KD(9,3,3) / MACD(12,26,9) / RSI(14)）＋當下數值
    setPaneLabels(map) { this._paneText = map || {}; this._layoutLabels(); }
    _layoutLabels() {
      if (!this.labels) return;
      const ps = this.chart.panes(); let top = 0; const tops = ps.map(p => { const t = top; top += p.getHeight() + 1; return t; });
      const html = Object.entries(this.paneIndex).map(([k, i]) => tops[i] == null ? '' : `<div style="top:${tops[i] + 6}px">${(this._paneText || {})[k] || ''}</div>`).join('');
      this.labels.innerHTML = html;
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
    /** keepView：即時 K 每幾秒就重畫一次，不能每次都把畫面拉回最右邊 ——
     *  使用者往左捲去看早盤，下一次更新就被彈回去，等於不能看。
     *  所以即時更新時保留目前的可視範圍，只有「換股票／換週期」才重新定位。 */
    setBars(bars, tf, keepView) {
      const ts = this.chart.timeScale();
      const keep = keepView ? ts.getVisibleLogicalRange() : null;
      const grew = keep && this.data ? bars.length - this.data.length : 0;
      this.tf = tf || this.tf; this.bars = bars;
      this.data = bars.map(b => ({ time: toTime(b[0]), open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] || 0 }));
      this.candle.setData(this.data);
      this.chart.applyOptions({ localization: { timeFormatter: (t) => fmtTime(t, this.tf) }, timeScale: { timeVisible: /[ms]$/.test(this.tf) } });
      if (keep) {
        // 貼著右緣看的人要跟著新棒子走；捲到左邊看歷史的人要留在原地
        const atRight = keep.to >= (this.data.length - grew) - 1.5;
        ts.setVisibleLogicalRange(atRight
          ? { from: keep.from + grew, to: keep.to + grew }
          : { from: keep.from, to: keep.to });
        if (this.zones && this.data.length) this.zones.setLastTime(this.data[this.data.length - 1].time);
        return;
      }
      this.chart.timeScale().scrollToRealTime();
      this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - (this.opts.mini ? 90 : 160)), to: this.data.length + 3 });
      // 供需區的右邊界要停在最後一根 K 棒，不是畫面右緣
      if (this.zones && this.data.length) this.zones.setLastTime(this.data[this.data.length - 1].time);
    }
    setZones(z, style) { this.zones.setZones(z, style); }
    setZoneStyle(style) { this.zones.setStyle(style); }
    clearOverlays() {
      // MACD 面板被移掉時，掛在它上面的背離線也跟著沒了（不清會留著指向已刪除的 series）
      this.divPane = null;
      for (const s of this.overlays) this.chart.removeSeries(s); this.overlays = [];
      for (const k in this.panes) { for (const s of this.panes[k]) this.chart.removeSeries(s); } this.panes = {};
    }
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
      /* 面板高度有兩套：一般（個股頁那種整頁大圖）與 compact（總覽那三張小卡）。
         以前主圖高度寫死「至少 280px」，放進 230px 的小卡就會整個爆出去 ——
         成交量被擠成一條線、指標面板空白、面板標題跑到卡片外面。 */
      const PH = this.opts.compact
        ? { vol: 52, ind: 58, gap: 60, min: 110 }
        : { vol: 90, ind: 110, gap: 105, min: 280 };
      const c = this.data.map(d => d.close), h = this.data.map(d => d.high), l = this.data.map(d => d.low), v = this.data.map(d => d.volume);
      this.values = {};
      // 均線：條數、週期、顏色、粗細都吃 cfg（Andy 2026-09-12「線寬 均線數量 數字 顏色 粗細都要能調」）
      const mc = cfg.maColor || [], mw = cfg.maWidth || [];
      (cfg.ma || []).forEach((n, i) => { const m = ind.sma(c, n); this.values['MA' + n] = m; this.overlays.push(this._line(m, mc[i] || C.ma[i % C.ma.length], 0, mw[i] || cfg.lineWidth || 1)); });
      // 每個指標的顏色／線寬／透明度都可以個別設定（Andy 2026-09-12）
      const st = (k, d) => Object.assign({ w: cfg.lineWidth || 1, o: 100 }, d, (cfg.st || {})[k] || {});
      const col = (hex, o) => hexa(hex, o == null ? 100 : o);
      if (cfg.boll) { const b = ind.boll(c, cfg.boll.n, cfg.boll.k); this.values.BOLL = b;
        const y = st('boll', { c: C.boll }); const cc = col(y.c, y.o);
        this.overlays.push(this._line(b.up, cc, 0, y.w, { lineStyle: 2 }));
        this.overlays.push(this._line(b.mid, cc, 0, y.w));
        this.overlays.push(this._line(b.low, cc, 0, y.w, { lineStyle: 2 })); }
      let pane = 1; this.paneIndex = {};
      const ref = (series, price, color) => series.createPriceLine({ price, color, lineWidth: 1, lineStyle: 3, axisLabelVisible: false, title: '' });
      if (cfg.vol) {
        const y = st('vol', { c: '#ff4d6d', c2: '#2ee59d', o: 55 });
        this.panes.vol = [this._hist(v, (i) => (this.data[i].close >= this.data[i].open ? col(y.c, y.o) : col(y.c2, y.o)), pane)];
        if (cfg.volma) { this.values.VOLMA = ind.sma(v, cfg.volma); this.panes.vol.push(this._line(this.values.VOLMA, '#ffd166', pane, y.w)); }
        this.paneIndex.vol = pane; this._paneH(pane, PH.vol); pane++; }
      if (cfg.kd) { const k = ind.kd(h, l, c, cfg.kd.n, cfg.kd.m1, cfg.kd.m2); this.values.KD = k;
        const y = st('kd', { c: C.k, c2: C.d });
        this.panes.kd = [this._line(k.k, col(y.c, y.o), pane, y.w), this._line(k.d, col(y.c2, y.o), pane, y.w)];
        ref(this.panes.kd[0], 80, 'rgba(255,77,109,.35)'); ref(this.panes.kd[0], 20, 'rgba(46,229,157,.35)');
        this.paneIndex.kd = pane; this._paneH(pane, PH.ind); pane++; }
      this.divergences = { top: [], bottom: [] };
      if (cfg.macd) { const m = ind.macd(c, cfg.macd.f, cfg.macd.s, cfg.macd.g); this.values.MACD = m;
        const y = st('macd', { c: C.dif, c2: C.dea });
        this.panes.macd = [this._hist(m.osc, (i) => (m.osc[i] >= 0 ? col('#ff4d6d', (y.o || 100) * .7) : col('#2ee59d', (y.o || 100) * .7)), pane),
          this._line(m.dif, col(y.c, y.o), pane, y.w), this._line(m.dea, col(y.c2, y.o), pane, y.w)];
        ref(this.panes.macd[1], 0, 'rgba(255,255,255,.18)'); this.paneIndex.macd = pane; this._paneH(pane, PH.ind); pane++;
        /* 背離（Andy 2026-09-15：「是很好的訊號」）。預設開，cfg.macdDiv === false 才關。
           主圖畫價格的那兩個轉折點，MACD 面板畫 DIF 的那兩點 —— 兩條線一起看才看得出「背」在哪。 */
        if (cfg.macdDiv !== false) {
          const dv = ind.divergence(c, h, l, m.dif, cfg.divOpt);
          this.divergences = dv;
          const times = this.data.map(d => d.time);
          const priceItems = [], difItems = [];
          dv.top.forEach(x => {
            priceItems.push({ i: x.i, j: x.j, v1: x.p1, v2: x.p2, kind: 'top', label: '頂背離' });
            difItems.push({ i: x.i, j: x.j, v1: x.d1, v2: x.d2, kind: 'top' });
          });
          dv.bottom.forEach(x => {
            priceItems.push({ i: x.i, j: x.j, v1: x.p1, v2: x.p2, kind: 'bottom', label: '底背離' });
            difItems.push({ i: x.i, j: x.j, v1: x.d1, v2: x.d2, kind: 'bottom' });
          });
          this.divPrice.set(priceItems, times);
          this.divPane = new DivPrimitive();
          this.panes.macd[1].attachPrimitive(this.divPane);
          this.divPane.set(difItems, times);
        } else if (this.divPrice) { this.divPrice.set([], []); } }
      else if (this.divPrice) { this.divPrice.set([], []); }
      if (cfg.rsi) { const r = ind.rsi(c, cfg.rsi.n); this.values.RSI = r;
        const y = st('rsi', { c: C.rsi });
        this.panes.rsi = [this._line(r, col(y.c, y.o), pane, y.w)];
        ref(this.panes.rsi[0], 70, 'rgba(255,77,109,.35)'); ref(this.panes.rsi[0], 30, 'rgba(46,229,157,.35)');
        this.paneIndex.rsi = pane; this._paneH(pane, PH.ind); pane++; }
      this._paneH(0, Math.max(PH.min, this.el.clientHeight - (pane - 1) * PH.gap - 20));
      setTimeout(() => this._layoutLabels(), 30);
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
      // 只留每種訊號最近 5 個，太多會把圖蓋滿
      const keep = []; const cnt = {}; for (let i = m.length - 1; i >= 0; i--) { const k = m[i].text; cnt[k] = (cnt[k] || 0) + 1; if (cnt[k] <= 5) keep.unshift(m[i]); }
      if (!this.markers) this.markers = LWC.createSeriesMarkers(this.candle, keep); else this.markers.setMarkers(keep);
    }
    setPriceLines(lines) { // [{price, title, color}]
      for (const p of this.priceLines) this.candle.removePriceLine(p); this.priceLines = [];
      for (const ln of lines) { if (ln.price == null) continue; this.priceLines.push(this.candle.createPriceLine({ price: ln.price, color: ln.color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: ln.title })); }
    }
    // 第二個參數是游標在圖內的座標，給「跟著游標走的資訊框」用（Andy 2026-09-15 圖一）
    onCrosshair(fn) { this.chart.subscribeCrosshairMove((p) => { if (!p.time) { fn(null, null); return; } const i = this.data.findIndex(d => String(d.time) === String(p.time)); fn(i >= 0 ? i : null, p.point || null); }); }
    fitLast(n) { this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - n), to: this.data.length + 3 }); }
    // K 棒寬度（每根佔幾 px）。Andy 要能自己調，而且預設要寬一點
    setBarSpacing(px) {
      const v = Math.max(2, Math.min(40, +px || 11));
      this.chart.timeScale().applyOptions({ barSpacing: v });
      this._bar = v;
    }
    // 重設整個介面：價格軸自動、時間軸回到最近 n 根（TradingView 右下角那顆的行為）
    resetView(n) { this.candle.priceScale().setAutoScale(true); this.chart.timeScale().resetTimeScale(); this.fitLast(n || 160); }
    enableDrawing(key) { if (this.draw) this.draw.destroy(); this.draw = new Drawings(this, key); return this.draw; }
    destroy() { if (this.draw) this.draw.destroy(); if (this._ro) this._ro.disconnect(); this.chart.remove(); }
  }

  global.KChart = KChart; global.KInd = ind;
  global.KUtil = { resampleDaily, toTime, fmtTime, colors: C, refreshTheme, DRAW_TOOLS, DRAW_COLORS, ZONE_DEF, hexa };
})(window);
