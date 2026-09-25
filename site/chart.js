/* K 線圖層（TradingView Lightweight Charts 5）：多週期、可勾選指標與參數、SMC 區間、
   滾輪縮放價格軸、四週期同看。指標全部在前端算，參數才能即時調。
   台股慣例：紅漲綠跌；KD 9,3,3；RSI Wilder；MACD DIF/MACD/OSC。 */
(function (global) {
  'use strict';
  const LWC = global.LightweightCharts;
  const C = {
    up: '#ff4d6d', down: '#2ee59d', grid: 'rgba(255,255,255,.05)', text: '#a9b6d6', bg: '#0a1020',
    /* 第六條均線在深色主題是白的。淺色主題底色就是 #ffffff，白線畫上去等於沒畫
       （Andy 2026-09-16「切換回白色 UI 後需要更改的顏色」），所以 refreshTheme() 會換掉它。*/
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
    // 畫面內每根 K 棒佔的框（影線高低＋棒寬），區間標籤避讓用
    _candleRects(ts, width) {
      const out = []; let data = [];
      try { data = this._series.data() || []; } catch (e) { return out; }
      const vr = ts.getVisibleLogicalRange && ts.getVisibleLogicalRange();
      const i0 = vr ? Math.max(0, Math.floor(vr.from) - 1) : 0, i1 = vr ? Math.min(data.length - 1, Math.ceil(vr.to) + 1) : data.length - 1;
      const bs = ts.options ? Math.max(2, (ts.options().barSpacing || 6) * 0.8) : 6;
      for (let i = i0; i <= i1; i++) {
        const d = data[i]; if (!d || d.high == null) continue;
        const x = ts.timeToCoordinate(d.time); if (x === null || x < -bs || x > width + bs) continue;
        const yh = this._series.priceToCoordinate(d.high), yl = this._series.priceToCoordinate(d.low);
        if (yh === null || yl === null) continue;
        out.push({ x: x - bs / 2, y: Math.min(yh, yl), w: bs, h: Math.max(1, Math.abs(yl - yh)) });
      }
      return out;
    }
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
      const used = [];                         // 已放好的標籤框 {x,y,w,h}
      self.placed = []; self.skipped = 0;      // 驗收讀這兩個（有幾個標籤放得下、幾個因為撞到而省略）
      let avoidAll = null, candles = null;     // 第一個要放標籤時才算（沒開標籤就不花這個時間）
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
        const tw = ctx.measureText(label).width;
        /* ★ 2026-09-25（審查 R5：「需求 日線 2395–2457」「需求 日線 2277–2357」壓在 K 棒和 CHoCH 上、
           字疊在一起；四週期同看的週線格「掃蕩」疊三個）。以前只避「其他區間標籤的 y」，
           x 不看、BOS／CHoCH／掃蕩標記不看、左上角的圖例也不看。改成：
           候選位置（區間上緣外 → 區間下緣外 → 區間內上緣）×（最後一根右邊的空白 → 區間右端 → 區間左端）
           逐一試，**撞到已放好的標籤、K 線上的訊號標記、或圖例**就換下一個；全部都撞就這一個不印
           （＝同一價位附近只留一個；區間本身的色帶仍然畫著，滑過去看價格軸就知道範圍）。*/
        if (!avoidAll) avoidAll = self.getAvoid ? self.getAvoid().rects(ts, self._series) : [];
        if (!candles) candles = self._candleRects(ts, mediaSize.width);
        const hitIn = (arr, r) => arr.some(b => r.x < b.x + b.w && r.x + r.w > b.x && r.y < b.y + b.h && r.y + r.h > b.y);
        const ys = [top - 3, top + h + 11, top + 11].filter(y => y >= 12 && y <= mediaSize.height - 4);
        const xsC = [];
        if (xEnd + 4 + tw <= mediaSize.width - 2) xsC.push(xEnd + 4);
        const xR = Math.min(Math.max(xEnd - tw - 6, xs + 4), mediaSize.width - tw - 6);
        // 從區間右端往左每 12px 試一格，找 K 棒之間的空檔
        for (let x = xR; x >= xs + 4; x -= 12) xsC.push(x);
        let pos = null;
        /* 兩輪：第一輪連 K 棒也避開；找不到才第二輪只避「標籤／訊號標記／圖例」（字框有深底，壓在 K 棒上還讀得到）。
           兩輪都找不到＝這一帶已經被別的字佔滿，這個標籤就不印。*/
        for (const tier of [2, 1]) {
          const block = tier === 2 ? used.concat(avoidAll, candles) : used.concat(avoidAll);
          for (const ly of ys) { for (const lx of xsC) { const r = { x: lx - 3, y: ly - 10, w: tw + 7, h: 13 }; if (!hitIn(block, r)) { pos = { lx, ly, r }; break; } } if (pos) break; }
          if (pos) break;
        }
        if (!pos) { self.skipped = (self.skipped || 0) + 1; continue; }
        used.push(pos.r);
        self.placed = (self.placed || []).concat([{ label, x: pos.r.x, y: pos.r.y, w: pos.r.w, h: pos.r.h }]);
        ctx.fillStyle = 'rgba(10,16,32,.82)'; ctx.fillRect(pos.r.x, pos.r.y, pos.r.w, pos.r.h);
        ctx.fillStyle = base; ctx.fillText(label, pos.lx, pos.ly);
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
  // 最後一個原本是 #e8eeff（近白），淺色主題畫在白底上等於沒畫；改成中性灰兩邊都看得見
  const DRAW_COLORS = ['#3ee0ff', '#ffd166', '#ff4d6d', '#2ee59d', '#8b7bff', '#8ea0c4'];

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
        self.lastLabels = [];
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
          const tx = (x1 + x2) / 2;
          let tyRaw = (y1 + y2) / 2 + (up ? -10 : 16);
          const w = ctx.measureText(it.label).width;
          /* ★ 2026-09-25（審查 R5：「頂背離」落在左上角圖例底下，被圖例的模糊底色蓋住）。
             字框撞到圖例就改放到連線的另一側（頂背離放線下、底背離放線上）。*/
          const lg = self.getLegend ? self.getLegend() : null;
          const box = (ty) => ({ x: tx - w / 2 - 4, y: ty - 11, w: w + 8, h: 14 });
          const onLg = (b) => lg && b.x < lg.x + lg.w && b.x + b.w > lg.x && b.y < lg.y + lg.h && b.y + b.h > lg.y;
          if (onLg(box(tyRaw))) {
            const alt = up ? Math.max(y1, y2) + 18 : Math.min(y1, y2) - 8;
            tyRaw = onLg(box(alt)) ? lg.y + lg.h + 14 : alt;
          }
          self.lastLabels = (self.lastLabels || []).concat([{ label: it.label, ...box(tyRaw) }]);
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

  // ---------------------------------------------------------------- ③ 歷史無限回溯
  /* 往左拖到頭就自動載入更舊的 K 棒。
     - 資料來自 `data/hist/<代號>/p<N>.json`，由 `pipeline/build_payload.py` 從資料湖產出：
       p0 是「個股頁那 1,250～1,500 根再往前的第一段」，p1 更舊，依此類推。
       每一份自己帶 `prev`：prev 是 null 就代表**這已經是資料湖裡最早的一段**，
       前端看到 null 就收手，不會再往下打請求（Andy 要的「拖到最早一筆要停下來」）。
     - 快取放在模組層，key 是代號：換週期、離開再回到同一檔都不會重抓。
       `fetches` / `hits` 是驗收用的 —— 「有沒有重抓」這件事一樣不能用眼睛猜。
     - 為什麼存的是「日線」而不是各週期各存一份：週線月線本來就由日線在前端合成
       （`KUtil.resampleDaily`），存日線一份，三個週期共用。*/
  const HIST = Object.create(null);
  /* 目錄檔：哪幾檔有更舊的歷史、各有幾段。
     沒有它的話，全市場 2,341 檔裡那 1,996 檔沒有更舊歷史的股票，
     每拖一次就打一次 404 —— console 會噴錯，而 `_preview.py` 的 console.error
     關卡會當場抓到（2026-09-23 我第一版就是這樣被它擋下來的）。*/
  let HIST_INDEX = null;
  async function histIndex() {
    if (HIST_INDEX) return HIST_INDEX;
    try {
      const r = await fetch('data/hist/index.json', { cache: 'force-cache' });
      HIST_INDEX = r.ok ? await r.json() : { codes: {} };
    } catch (e) { HIST_INDEX = { codes: {} }; }
    return HIST_INDEX;
  }
  function histState(code) {
    return HIST[code] || (HIST[code] = { pages: {}, daily: [], next: 0, done: false, fetches: 0, hits: 0 });
  }
  async function histFetch(code, n) {
    const st = histState(code);
    if (st.pages[n] !== undefined) { st.hits++; return st.pages[n]; }
    st.fetches++;
    let j = null;
    try {
      const r = await fetch(`data/hist/${code}/p${n}.json`, { cache: 'force-cache' });
      j = r.ok ? await r.json() : null;
    } catch (e) { j = null; }
    st.pages[n] = j;      // 連「沒有這一段」都要記下來，不然每拖一次就再打一次 404
    return j;
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
    /* ★ 指標色在淺色主題整組換掉（Andy 2026-09-16
         「一開始製作是黑色底，很多數據都是白色線條及文字…檢查所有切換回白色 UI 後需要更改的顏色」）。
       深色主題那組是螢光色（#ffd166 黃、#3ee0ff 青、#c3ff5b 螢光綠），
       它們同時用在**線**和**圖例文字**上。切到淺色之後：
         - 線畫在 #ffffff 的圖表底上 → 幾乎看不見
         - 圖例文字印在近白色的工具列上 → 實測對比度只有 1.44～1.58（近乎隱形）
       所以淺色主題換成同色系但壓深的版本，色相不變（使用者認得出哪條是哪條），亮度夠。
       第六條均線在深色是白的，淺色一定要換，不然等於沒畫。*/
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    if (light) {
      C.ma = ['#a16207', '#0e7490', '#5b21b6', '#be185d', '#3f6212', '#2b3a5c'];
      C.k = '#a16207'; C.d = '#0e7490'; C.j = '#be185d';
      C.dif = '#0e7490'; C.dea = '#a16207'; C.rsi = '#3f6212';
      C.boll = 'rgba(91,33,182,.7)';
      C.vol = 'rgba(71,85,105,.45)';
    } else {
      C.ma = ['#ffd166', '#3ee0ff', '#8b7bff', '#ff8fab', '#c3ff5b', '#ffffff'];
      C.k = '#ffd166'; C.d = '#3ee0ff'; C.j = '#ff8fab';
      C.dif = '#3ee0ff'; C.dea = '#ffd166'; C.rsi = '#c3ff5b';
      C.boll = 'rgba(139,123,255,.75)';
      C.vol = 'rgba(120,140,190,.55)';
    }
    return C;
  }

  function baseOptions(h) {
    refreshTheme();
    return {
      /* panes.enableResize：面板之間可以用滑鼠拖大拖小（Andy 2026-09-15
         「下方MACD KD 成交量等範圍上下可以拉大」）。分隔線本來用 grid 的顏色，幾乎看不見，
         使用者不會知道那裡可以拉 —— 改成明顯一點，hover 再亮起來。 */
      autoSize: true, layout: { attributionLogo: false, background: { color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, panes: { separatorColor: C.line, separatorHoverColor: 'rgba(62,224,255,.55)', enableResize: true } },
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
      // 左上角圖例（#legendOv）在主圖座標裡佔的框；背離字與區間標籤都要避開它
      this.divPrice.getLegend = () => this.legendRect();
      this.zones.getAvoid = () => ({ rects: (ts, series) => {
        const out = []; const lg = this.legendRect(); if (lg) out.push(lg);
        (this._markBoxes || []).forEach(m => {
          const x = ts.timeToCoordinate(m.time); if (x === null) return;
          const yp = series.priceToCoordinate(m.pos === 'aboveBar' ? m.hi : m.lo); if (yp === null) return;
          const hw = Math.max(14, m.text.length * 4.2);     // 標記的字寬（中英混排的粗估，寧大勿小）
          out.push(m.pos === 'aboveBar' ? { x: x - hw, y: yp - 34, w: hw * 2, h: 34 } : { x: x - hw, y: yp, w: hw * 2, h: 34 });
        });
        return out;
      } });
      this.divPane = null;               // MACD 面板那一條，等 applyIndicators 建好 series 才掛
      this.overlays = []; this.panes = {}; this.priceLines = []; this.markers = null;
      this.bars = []; this.tf = this.opts.tf; this.paneIndex = {};
      /* ②③ 的狀態。
         stats 是驗收用的計數器 —— 「有沒有重畫整張圖」這件事沒有計數器就只能用眼睛猜，
         而用眼睛猜正是以前放過一堆錯的原因（`_uitest.py` 會直接讀這幾個數字）。
           setData  整條重灌了幾次（換股／換週期／回補歷史才該 +1）
           tick     走過幾次「只更新尾巴」的快路
           point    總共推了幾個單點（K 棒 + 各指標線）
           rebuild  指標 series 整組重建了幾次 */
      this.stats = { setData: 0, tick: 0, point: 0, rebuild: 0, backfill: 0 };
      this._feeds = [];          // 每條指標線怎麼從 values 取值（只更新尾巴時用）
      this._tailFrom = null;     // setBars 判定「只有這個 index 之後變了」
      this._histAdded = 0;       // ③ 已經往左補了幾根
      if (!this.opts.mini) {
        this.labels = document.createElement('div'); this.labels.className = 'pane-labels'; el.appendChild(this.labels);
        this.wm = document.createElement('div'); this.wm.className = 'k-wm'; el.appendChild(this.wm);
        this._wheelOnPriceAxis();
        this._ro = new ResizeObserver(() => this._layoutLabels()); this._ro.observe(el);
        this._initHistory();          // ③ 往左拖到頭就自動補更舊的 K 棒
        /* 驗收用的把手：`_uitest.py` 要能拿到「畫面上那張大 K 線圖」本人，
           才驗得了「灌一筆報價之後最後一根真的變了、而且前面的棒子沒被動到」。
           只記整頁大圖（mini／compact 的小卡不覆蓋它）。*/
        KChart.last = this;
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
    /* 滾輪在價格軸上：縮放上下寬度（TradingView 手感）；圖區內滾輪維持時間縮放。

       這兩個 listener 掛在容器 `#lwc` 上，而容器是**跨圖表活著的**（換股票、換週期時
       KChart 會重建，但 #lwc 本身留著）。所以一定要在 destroy() 時拿掉 ——
       不拿掉的話，舊圖表已經 remove 了，listener 還在，下次滑到價格軸上一滾就噴
       「Cannot read properties of undefined」，而且每重建一次就多疊一層。 */
    _wheelOnPriceAxis() {
      this._onWheel = (e) => {
        if (this._dead) return;
        const rect = this.el.getBoundingClientRect(); const x = e.clientX - rect.left;
        const w = this.chart.priceScale('right').width();
        if (x < rect.width - w) return;
        e.preventDefault(); e.stopPropagation();
        const ps = this.candle.priceScale(); const r = ps.getVisibleRange(); if (!r) return;
        ps.setAutoScale(false);
        const f = e.deltaY > 0 ? 1.12 : 1 / 1.12; const mid = (r.from + r.to) / 2, half = (r.to - r.from) / 2 * f;
        ps.setVisibleRange({ from: mid - half, to: mid + half });
      };
      this._onDbl = () => { if (!this._dead) this.candle.priceScale().setAutoScale(true); };
      this.el.addEventListener('wheel', this._onWheel, { passive: false });
      this.el.addEventListener('dblclick', this._onDbl);
    }
    /** keepView：即時 K 每幾秒就重畫一次，不能每次都把畫面拉回最右邊 ——
     *  使用者往左捲去看早盤，下一次更新就被彈回去，等於不能看。
     *  所以即時更新時保留目前的可視範圍，只有「換股票／換週期」才重新定位。 */
    setBars(bars, tf, keepView) {
      const ts = this.chart.timeScale();
      /* ② 即時更新的快路。
         盤中每幾秒送進來的那一份 bars，跟上一份的差別只有「最後一根被改掉」
         （或多了一根新的）。以前不分青紅皂白整條 setData 重灌，於是
         每一輪都是整張圖重畫一次 —— Andy 說的「要等資料整批換掉才會跳」就是這件事。
         現在先比對一次：只有尾巴不一樣，就走 candle.update() 單點更新。*/
      if (keepView && (!tf || tf === this.tf) && this.data && this.data.length && bars && bars.length) {
        const d = this._tailDiff(bars);
        if (d >= 0) { this._applyTail(bars, d); return; }
      }
      this._histAdded = 0;      // 整條重灌＝回補的那些也沒了，重新算起
      this._histDailyUsed = 0;  // 快取裡的更舊日線要重新接一次（換週期時就是走這條）
      this._lastCum = null;     // 換股／換週期，即時量的基準也要跟著歸零
      this.stats.setData++;
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
      /* 畫面上要放幾根，用「想要的每根寬度」除出來，不要寫死 160 根。
         寫死的話視窗一窄（或手機），160 根攤在 700px 上就只剩 4px 一根。*/
      const want = this._bar || (this.opts.mini ? 6 : 11);
      const room = Math.max(240, (this.el.clientWidth || 900) - 70);
      const n = Math.max(30, Math.min(this.data.length, Math.round(room / want)));
      this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - n), to: this.data.length + 3 });
      /* ★ 換股票或換週期時把價格軸交還給自動縮放。
         上面那段 wheel（在價格軸上滾滾輪縮放）會把 autoScale 關掉，而且是**永久**關掉 ——
         接著切到 15 分，價格軸還留著日線那個 240–480 的範圍，而當天只走 330–345，
         K 棒就被壓成一條線。Andy 2026-09-15：「切換到不同時間週期，K棒會很窄」。
         只在 !keepView 時做：即時更新每幾秒跑一次，那時要尊重使用者自己拉的範圍。*/
      this.candle.priceScale().setAutoScale(true);
      // 供需區的右邊界要停在最後一根 K 棒，不是畫面右緣
      if (this.zones && this.data.length) this.zones.setLastTime(this.data[this.data.length - 1].time);
    }
    /** 新舊兩份 bars 的差在哪一根。
     *  回傳「從第幾根開始不一樣」；只要有任何一根**舊資料的最後一根之前**被改過，
     *  就回 -1（＝不是單純的即時更新，必須整條重灌）。
     *  允許多出 1~3 根：換日、或是連續兩輪之間跨了一根分 K。 */
    _tailDiff(nb) {
      const ob = this.bars;
      if (!ob || !ob.length) return -1;
      const grew = nb.length - ob.length;
      if (grew < 0 || grew > 3) return -1;
      const same = (a, b) => !!a && !!b && String(a[0]) === String(b[0])
        && a[1] === b[1] && a[2] === b[2] && a[3] === b[3] && a[4] === b[4] && (a[5] || 0) === (b[5] || 0);
      for (let i = 0; i < ob.length - 1; i++) if (!same(ob[i], nb[i])) return -1;
      return ob.length - 1;
    }
    /** 只把 from 之後那幾根推進圖裡。前面的棒子一根都不碰。 */
    _applyTail(nb, from) {
      const ts = this.chart.timeScale();
      const keep = ts.getVisibleLogicalRange();
      const grew = nb.length - this.bars.length;
      this.bars = nb;
      for (let i = from; i < nb.length; i++) {
        const b = nb[i];
        const p = { time: toTime(b[0]), open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] || 0 };
        this.data[i] = p;
        /* ★ 一定要傳「複本」給 update()。
           Lightweight Charts 的 update() 會**就地改寫**你傳進去的那個物件，
           把 `time: '2026-09-22'` 換成 `{year, month, day}`。傳 this.data[i] 本人的話，
           我們自己那份資料的 time 就變成物件了 —— 而 industry.js 的游標資訊框是
           `KUtil.fmtTime(d.time, tf)`，拿到物件就印成 `NaN-NaN-NaN`（2026-09-23 實測，
           截圖抓到的）。setData() 不會這樣，只有 update() 會，所以以前沒踩到。*/
        this.candle.update({ time: p.time, open: p.open, high: p.high, low: p.low, close: p.close, volume: p.volume });
        this.stats.point++;
      }
      this.data.length = nb.length;
      this.stats.tick++;
      this._tailFrom = from;     // 接下來 applyIndicators 會用它決定只更新尾巴
      /* 多了一根的時候：貼著右緣看的人要跟著新棒子走。
         捲到左邊看歷史的人什麼都不用做 —— 新棒子接在右邊，舊棒子的 index 沒有變，
         所以可視的邏輯範圍原封不動就是「留在原地」。*/
      if (grew > 0 && keep && keep.to >= (nb.length - grew) - 1.5) {
        ts.setVisibleLogicalRange({ from: keep.from + grew, to: keep.to + grew });
      }
      if (this.zones && this.data.length) this.zones.setLastTime(this.data[this.data.length - 1].time);
    }
    /** ② 直接把一筆即時報價灌進「當根 K 棒」。
     *
     *  q = { price, volume(累計張數), time:'HH:MM:SS', date:'YYYY-MM-DD' }，形狀就是
     *  `live.js` 的 `normalise()` 產出、`Live.quotes[code]` 裡放的那個。
     *
     *  兩件事要分清楚：
     *   - **還在同一根**：高 = max(高, 價)、低 = min(低, 價)、收 = 價（開盤價不動）。
     *   - **跨到下一根**：開 = 高 = 低 = 收 = 價，**開一根新的**，不是把舊的那根改掉。
     *  量：日／週／月線的當天量，mis 給的就是「當天累計」，直接用它才對（累加會重複算）；
     *  分 K 的一根只佔幾分鐘，所以用「這一輪累計 − 上一輪累計」的增量累加上去。
     *  回傳 'update' / 'new' / null，驗收時才看得出到底發生了哪一種。 */
    applyQuote(q) {
      if (!q || q.price == null || !this.bars || !this.bars.length) return null;
      const last = this.bars[this.bars.length - 1];
      const key = this._bucketOf(q);
      if (key == null) return null;
      const price = +q.price;
      const cum = q.volume == null ? null : +q.volume * 1000;   // mis 給張，資料湖存股
      const dv = (cum == null || this._lastCum == null || cum < this._lastCum) ? 0 : cum - this._lastCum;
      const daily = this.tf === '1d' || this.tf === '1w' || this.tf === '1M';
      let nb;
      if (String(key) > String(last[0])) {
        // 跨根：開一根新的
        const vol = daily && this.tf === '1d' ? (cum || 0) : dv;
        nb = this.bars.concat([[key, price, price, price, price, vol]]);
      } else if (String(key) === String(last[0])) {
        const b = last.slice();
        b[2] = Math.max(b[2], price); b[3] = Math.min(b[3], price); b[4] = price;
        if (this.tf === '1d' && cum != null) b[5] = cum;          // 當天累計就是這一根的量
        else b[5] = (b[5] || 0) + dv;                             // 週／月／分 K 用增量往上加
        nb = this.bars.slice(); nb[nb.length - 1] = b;
      } else {
        return null;   // 報價比圖上最後一根還舊（假日／停牌），不要動
      }
      this._lastCum = cum;
      const kind = nb.length > this.bars.length ? 'new' : 'update';
      const d = this._tailDiff(nb);
      if (d < 0) return null;
      this._applyTail(nb, d);
      if (this.cfg) this.applyIndicators(this.cfg);   // 指標跟著重算，線不能跟 K 棒對不起來
      return kind;
    }
    /** 這筆報價該落在哪一根上（日線＝日期字串；週／月線＝當下那一根的標籤；分 K＝epoch）。*/
    _bucketOf(q) {
      const date = String(q.date || '').replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
      const last = this.bars[this.bars.length - 1];
      if (this.tf === '1d') return date || last[0];
      if (this.tf === '1w' || this.tf === '1M') {
        /* 週／月線的那一根一直是「當週／當月」，只有跨週跨月才換 —— 而換的時候
           那一根的標籤是「該週最後一個交易日」，盤中不可能事先知道，
           所以直接用今天的日期當新的一根（收盤後資料湖會給正式的那一根）。*/
        if (!date) return last[0];
        return this._sameBucket(String(last[0]), date) ? last[0] : date;
      }
      const m = /^(\d+)m$/.exec(this.tf || '');
      if (!m || typeof last[0] !== 'number') return null;
      const step = +m[1] * 60;
      const ts = Date.parse(`${date || ''}T${q.time || '00:00:00'}`);
      if (!isFinite(ts)) return null;
      return Math.floor((Math.floor(ts / 1000) + TZ) / step) * step;
    }
    _sameBucket(a, b) {
      if (this.tf === '1M') return a.slice(0, 7) === b.slice(0, 7);
      const mon = (x) => { const d = new Date(x + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7)); return d.toISOString().slice(0, 10); };
      return mon(a) === mon(b);
    }
    setZones(z, style) { this.zones.setZones(z, style); }
    setZoneStyle(style) { this.zones.setStyle(style); }
    /* ③ 掛上「拖到左邊界就補」的監聽。只有日／週／月線做得到 ——
       分 K 的資料湖只留 60 分（730 天）與當天，往前補不到東西。*/
    _initHistory() {
      if (this.opts.mini) return;
      this._onRange = (r) => {
        if (!r || this._dead) return;
        /* ★ 資料還沒進來就不要動作。
           實測踩到：圖表剛 createChart、還沒 setBars 的那一瞬間，
           Lightweight Charts 會先發一次「空資料的可視範圍」（from 在 0 附近），
           當場就被當成「使用者拖到左邊界了」——於是一打開個股頁就自動下載一段
           根本沒人要看的歷史（多 49KB），而且畫面會無故往左長 1,000 根。
           回溯要由**使用者真的拖**觸發，不是由建圖觸發。*/
        if (!this.data || this.data.length < 50) return;
        /* ★ 而且要**使用者真的動過這張圖**才算數。
           歷史短的股票（只有 100 多根）一打開，左邊界本來就在畫面裡，
           不設這道閘門的話「開啟個股頁」本身就會被當成「拖到頭了」，
           於是還沒碰它就先下載一段。回補是使用者的動作換來的，不是開頁換來的。*/
        if (!this._histArmed) return;
        // 左邊界還剩不到 12 根就先去要下一段，等使用者拖到底才要就會看到一段空白
        if (r.from > 12) return;
        this.loadOlder();
      };
      this.chart.timeScale().subscribeVisibleLogicalRangeChange(this._onRange);
      this._arm = () => { this._histArmed = true; };
      ['pointerdown', 'wheel', 'touchstart'].forEach(ev =>
        this.el.addEventListener(ev, this._arm, { passive: true }));
    }
    /** 這張圖現在畫的是哪一檔。優先吃呼叫端給的，其次是 industry.js 寫在圖上的
     *  `_liveKey`（'代號|週期'），最後才從網址推 —— 個股頁的網址就是 #stock/<代號>。*/
    histCode() {
      if (this.opts.code) return String(this.opts.code);
      if (this._liveKey) return String(this._liveKey).split('|')[0];
      const m = /#stock\/([A-Za-z0-9]+)/.exec(global.location ? global.location.hash || '' : '');
      return m ? m[1] : null;
    }
    histReady() { return ['1d', '1w', '1M'].indexOf(this.tf) >= 0 && !!this.histCode(); }
    /** 載入更舊的一段。回傳「這一次真的多了幾根」。 */
    async loadOlder() {
      if (this.opts.mini || this._dead || !this.histReady()) return 0;
      const code = this.histCode();
      const st = histState(code);
      if (this._loading) return 0;
      /* 快取裡已經有、但「這張圖」還沒接上去的，先直接接 —— 不打網路。
         換週期（日→週）、離開再回到同一檔都會走這條路：圖表是新的、快取是舊的。
         這也是「拖過一次之後再拖不會重抓」的實作點。*/
      if (st.daily.length > (this._histDailyUsed || 0)) {
        st.hits++;
        this._histDailyUsed = st.daily.length;
        const n0 = this._prependHistory(st.daily);
        if (n0) return n0;
      }
      if (st.done) return 0;                    // 已經到最早一筆就收手，不要無限打請求
      this._loading = true;
      this._histNote('載入更早的 K 棒…');
      try {
        const idx = await histIndex();
        const pages = (idx.codes || {})[code];
        if (!pages || st.next >= pages) {
          // 這一檔在資料湖裡沒有比個股頁更舊的歷史（回補還沒跑到它）
          st.done = true;
          this._histNote(pages ? '已經到最早一筆了' : '這一檔的更早歷史還在回補，目前只有畫面上這一段', 3200);
          return 0;
        }
        const j = await histFetch(code, st.next);
        if (!j || !j.bars || !j.bars.length) {
          st.done = true;
          this._histNote('已經到最早一筆了', 2600);
          return 0;
        }
        st.next += 1;
        if (j.prev === null || j.prev === undefined) st.done = true;
        st.daily = j.bars.concat(st.daily);      // 由舊到新
        // await 中間可能換過股票或週期，接回去之前再確認一次現在畫的還是同一檔
        if (this._dead || this.histCode() !== code || !this.histReady()) return 0;
        this._histDailyUsed = st.daily.length;
        const n = this._prependHistory(st.daily);
        this._histNote(n ? `已回補到 ${this.data.length ? fmtTime(this.data[0].time, this.tf) : ''}`
          : '已經到最早一筆了', 2600);
        return n;
      } catch (e) {
        this._histNote('更早的資料載入失敗', 3000);
        histState(code).done = true;
        return 0;
      } finally {
        this._loading = false;
      }
    }
    /** 把「目前累積到的所有更舊日線」接到現有 K 棒前面。
     *  每次都從頭接一次（而不是「這次只接新的那一段」）是刻意的：
     *  週線／月線要跨段合成，一段一段接會在接縫處切出半根假的週 K。 */
    _prependHistory(olderDaily) {
      if (!olderDaily || !olderDaily.length || !this.data.length) return 0;
      const base = this.bars.slice(this._histAdded || 0);   // 原本呼叫端給的那一份
      if (!base.length) return 0;
      let older = olderDaily;
      if (this.tf === '1w') older = resampleDaily(olderDaily, 'W');
      else if (this.tf === '1M') older = resampleDaily(olderDaily, 'M');
      /* 邊界那一根可能跟現有第一根落在同一週／同一月 —— 那會變成兩根半截的週 K。
         寧可丟掉我們自己合的那一根（現有第一根本來就在圖上），也不要多畫一根假的。*/
      const anchor = String(base[0][0]);
      const keepBar = (b) => (this.tf === '1d'
        ? String(b[0]) < anchor
        : !this._sameBucket(anchor, String(b[0])) && String(b[0]) < anchor);
      const add = older.filter(keepBar);
      if (add.length <= (this._histAdded || 0)) return 0;
      const ts = this.chart.timeScale();
      const keep = ts.getVisibleLogicalRange();
      const grew = add.length - (this._histAdded || 0);
      this.bars = add.concat(base);
      this.data = this.bars.map(b => ({ time: toTime(b[0]), open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] || 0 }));
      this.candle.setData(this.data);
      this.stats.setData++; this.stats.backfill++;
      this._histAdded = add.length;
      /* 左邊多了資料，MA／KD／RSI 的起頭全部要重算（這正是回補的價值：
         以前畫面最左邊那 60 根的均線是「沒有前文」的，現在才是對的），所以整組重建。*/
      this._tailFrom = null; this._feeds = [];
      if (this.cfg) this.applyIndicators(this.cfg);
      // 視野往右平移 grew 根，使用者眼前的那一段不能因為左邊長出東西就跳掉
      if (keep) ts.setVisibleLogicalRange({ from: keep.from + grew, to: keep.to + grew });
      if (this.zones && this.data.length) this.zones.setLastTime(this.data[this.data.length - 1].time);
      return grew;
    }
    /* 「載入中」「已經到最早一筆」那一小塊字。
       樣式寫在 JS 裡是刻意的 —— CSS 在 index.html，那支檔案這批不准動。*/
    _histNote(msg, ms) {
      if (this.opts.mini || !this.el) return;
      let el = this._noteEl;
      if (!el) {
        el = this._noteEl = document.createElement('div');
        el.className = 'k-histnote';
        /* 位置：左下角、時間軸上面一點。
           不放左上角是因為那裡是 `.pane-labels`（游標資訊框「日期 開 高 低 收…」那一行），
           疊上去會把它蓋掉 —— 實測截圖就是被蓋住看不見。*/
        el.style.cssText = 'position:absolute;left:12px;bottom:34px;z-index:4;pointer-events:none;'
          + 'font:600 11.5px/1.5 "Noto Sans TC",sans-serif;padding:3px 9px;border-radius:999px;'
          + 'background:rgba(10,16,32,.78);color:#a9b6d6;border:1px solid rgba(62,224,255,.35)';
        this.el.appendChild(el);
      }
      /* 顏色跟著主題走。不要用 hexa(C.bg) 去算 —— `--chartbg` 在淺色主題有可能是
         rgb()/rgba() 字串而不是 #hex，算出來會退回深色底，配上淺色主題的深色文字
         就是深底深字（＝看不見）。直接依主題給兩組固定值，最不會出事。*/
      const lightTheme = document.documentElement.getAttribute('data-theme') === 'light';
      el.style.color = C.text;
      el.style.background = lightTheme ? 'rgba(255,255,255,.94)' : 'rgba(10,16,32,.82)';
      el.style.borderColor = C.line;
      el.textContent = msg || '';
      el.style.display = msg ? '' : 'none';
      clearTimeout(this._noteT);
      if (ms) this._noteT = setTimeout(() => { if (this._noteEl) this._noteEl.style.display = 'none'; }, ms);
    }
    /* 驗收用：這一檔的回溯狀態（抓了幾次、命中快取幾次、到底了沒）。*/
    histStats() {
      const code = this.histCode();
      const st = code ? HIST[code] : null;
      return { code, added: this._histAdded || 0, bars: this.data ? this.data.length : 0,
        fetches: st ? st.fetches : 0, hits: st ? st.hits : 0, done: st ? !!st.done : false,
        pages: st ? Object.keys(st.pages).length : 0 };
    }
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
    /* ★ 指標值一律「全量重算」，即時更新那條路也一樣（_calc）。
       這是紅線：前端 KInd 與 Python 端必須同口徑同種子（KD 初始 50、RSI Wilder 用 SMA 種子）。
       如果為了省時間另外寫一套「只算最後一根」的增量公式，同一個指標就會有兩份實作，
       兩份遲早漂開，而且漂開的時候沒有任何測試擋得住。
       真正貴的從來不是「算」（1,500 根全部算完 < 2ms），是「畫」——
       所以省的是畫：即時更新只把最後那一根用 series.update() 推進去（見 _updateTail）。*/
    _calc(cfg) {
      const c = this.data.map(d => d.close), h = this.data.map(d => d.high),
        l = this.data.map(d => d.low), v = this.data.map(d => d.volume);
      const V = { VOL: v };
      (cfg.ma || []).forEach(n => { V['MA' + n] = ind.sma(c, n); });
      if (cfg.boll) V.BOLL = ind.boll(c, cfg.boll.n, cfg.boll.k);
      if (cfg.vol && cfg.volma) V.VOLMA = ind.sma(v, cfg.volma);
      if (cfg.kd) V.KD = ind.kd(h, l, c, cfg.kd.n, cfg.kd.m1, cfg.kd.m2);
      if (cfg.macd) {
        V.MACD = ind.macd(c, cfg.macd.f, cfg.macd.s, cfg.macd.g);
        V.DIV = cfg.macdDiv === false ? { top: [], bottom: [] }
          : ind.divergence(c, h, l, V.MACD.dif, cfg.divOpt);
      }
      if (cfg.rsi) V.RSI = ind.rsi(c, cfg.rsi.n);
      /* 本益比河流的倍數線由 industry.js 算好掛在 this.peBands 上 —— 這裡只負責畫，
         因為近四季 EPS 是財報那一層的事，圖表這層不該知道財報怎麼算。*/
      V.PE = (this.peBands && this.peBands.length) ? this.peBands : null;
      return V;
    }
    /* 背離畫在 canvas 上（DivPrimitive），不是 series，所以重算完直接換一組點就好。*/
    _setDiv(V) {
      const dv = (V && V.DIV) || { top: [], bottom: [] };
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
      if (this.divPrice) this.divPrice.set(priceItems, times);
      if (this.divPane) this.divPane.set(difItems, times);
    }
    /* 這一輪的「指標組成指紋」。指紋一樣＝series 的種類與條數沒變，才可以只更新尾巴；
       只要使用者勾了新指標、改了參數或換了顏色，指紋就不同，一律走重建。*/
    _cfgKey(cfg) {
      const pe = (this.peBands || []).map(b => `${b.mult}/${b.color}/${b.width}/${b.alpha}`).join(',');
      try { return JSON.stringify(cfg) + '|' + pe; } catch (e) { return 'x' + Math.random(); }
    }
    /** ② 只更新尾巴：K 棒已經在 setBars 裡用 candle.update() 推進去了，
     *  這裡把每一條指標線最後那幾點也推進去 —— 整張圖不重畫，前面的棒子一根都不動。 */
    _updateTail(cfg, from) {
      this.cfg = cfg;
      const V = this._calc(cfg);
      this.values = V;
      const n = this.data.length, i0 = Math.max(0, from);
      for (const f of this._feeds) {
        for (let i = i0; i < n; i++) {
          const v = f.pick(V, i);
          if (v === null || v === undefined || Number.isNaN(v)) continue;
          // 同上：update() 會就地改寫傳進去的物件，所以每次都給一個新的
          const p = { time: this.data[i].time, value: v };
          if (f.color) p.color = f.color(V, i);
          f.s.update(p);
          this.stats.point++;
        }
      }
      this._setDiv(V);
      this.stats.tick++;
    }
    applyIndicators(cfg) {
      /* ② 即時更新的快路：資料只有尾巴變（setBars 判定的）、而且指標組成也沒變
         → 只推最後那幾點，不重建任何 series。
         以前盤中每幾秒就整組 removeSeries + addSeries + setData 重建一次，
         那正是「要等資料整批換掉才會跳」與副圖高度一直跳動的來源。*/
      if (this._tailFrom != null && this._feeds.length && this._cfgKey(cfg) === this._indKey) {
        const from = this._tailFrom; this._tailFrom = null;
        this._updateTail(cfg, from);
        return;
      }
      this._tailFrom = null;
      /* ★ 2026-09-25：重建之前先記住每個副圖**現在**的高度（按名字記，拿掉的面板也留著）。
         以前重建時只在第一次套 cfg.paneH，之後一律用預設高度 —— 關掉 KD 再打開，
         使用者拖好的主圖／成交量高度就被打回預設（驗收 `個股`「切指標之後主圖高度不會自己跳回去」）。
         這條以前沒紅，是因為點籤的正中間會點到參數框、根本沒切到；R5 把籤改成整顆都是開關之後才現形。*/
      if (this._paneInit && !this.opts.compact) {
        try {
          const cur = this.paneHeights();
          const sum = Object.values(cur).reduce((a, v) => a + (v || 0), 0);
          /* _applyPaneHeights 用容器 clientHeight 當分母算權重，但面板實際高度加起來比它少（分隔線佔掉的），
             直接把量到的高度當權重，每重建一次副圖就縮 ~4%（實測 115→110→106→102）。先換算回權重的尺度。*/
          const k = sum > 0 && this.el.clientHeight > 120 ? this.el.clientHeight / sum : 1;
          delete cur.main;
          Object.keys(cur).forEach(n => { cur[n] = cur[n] * k; });
          this._paneMem = Object.assign(this._paneMem || {}, cur);
        } catch (e) { /* 忽略 */ }
      }
      this.clearOverlays(); this.cfg = cfg;
      this._indKey = this._cfgKey(cfg); this._feeds = [];
      this.stats.rebuild++;
      /* 面板高度有兩套：一般（個股頁那種整頁大圖）與 compact（總覽那三張小卡）。
         以前主圖高度寫死「至少 280px」，放進 230px 的小卡就會整個爆出去 ——
         成交量被擠成一條線、指標面板空白、面板標題跑到卡片外面。 */
      const PH = this.opts.compact
        ? { vol: 52, ind: 58, min: 110 }
        // Andy 2026-09-15：「下面的成交量 MACD 這些指標上下間隔寬點」。
        // 以前實際只有 57~67px；這組在 813px 高的個股頁量到量 96／KD 115／MACD 115，主圖還有 441。
        // 再大就要吃掉主圖了 —— 他同樣在意 K 線圖要大（DECISIONS #101），想更寬可以自己拖，會記住。
        : { vol: 100, ind: 120, min: 260 };
      const V = this._calc(cfg);
      this.values = V;
      // 均線：條數、週期、顏色、粗細都吃 cfg（Andy 2026-09-12「線寬 均線數量 數字 顏色 粗細都要能調」）
      const mc = cfg.maColor || [], mw = cfg.maWidth || [];
      (cfg.ma || []).forEach((n, i) => {
        const key = 'MA' + n;
        const s = this._line(V[key], mc[i] || C.ma[i % C.ma.length], 0, mw[i] || cfg.lineWidth || 1);
        this.overlays.push(s);
        this._feeds.push({ s, pick: (VV, j) => (VV[key] ? VV[key][j] : null) });
      });
      if (V.PE) {
        V.PE.forEach((b, bi) => {
          const s = this._line(b.vals, hexa(b.color, b.alpha == null ? 70 : b.alpha), 0, b.width || 1, {
            lineStyle: 2,
            /* 倍數線離現價可以很遠（9.5 倍 ≈ 189、25 倍 ≈ 497），讓它們參與自動縮放的話
               價格軸會被拉成 160–520，K 棒又被壓扁 —— 那正是 Andy 抱怨過的事。
               所以這幾條線「畫得出來但不影響取景」：落在畫面外就切掉，
               想看得更遠可以在價格軸上滾滾輪。*/
            autoscaleInfoProvider: () => null,
          });
          this.overlays.push(s);
          this._feeds.push({ s, pick: (VV, j) => (VV.PE && VV.PE[bi] ? VV.PE[bi].vals[j] : null) });
        });
      }
      // 每個指標的顏色／線寬／透明度都可以個別設定（Andy 2026-09-12）
      const st = (k, d) => Object.assign({ w: cfg.lineWidth || 1, o: 100 }, d, (cfg.st || {})[k] || {});
      const col = (hex, o) => hexa(hex, o == null ? 100 : o);
      if (cfg.boll) {
        const y = st('boll', { c: C.boll }); const cc = col(y.c, y.o);
        const up = this._line(V.BOLL.up, cc, 0, y.w, { lineStyle: 2 });
        const mid = this._line(V.BOLL.mid, cc, 0, y.w);
        const low = this._line(V.BOLL.low, cc, 0, y.w, { lineStyle: 2 });
        this.overlays.push(up, mid, low);
        this._feeds.push({ s: up, pick: (VV, j) => VV.BOLL.up[j] },
          { s: mid, pick: (VV, j) => VV.BOLL.mid[j] },
          { s: low, pick: (VV, j) => VV.BOLL.low[j] });
      }
      let pane = 1; this.paneIndex = {}; const want = [0];
      const ref = (series, price, color) => series.createPriceLine({ price, color, lineWidth: 1, lineStyle: 3, axisLabelVisible: false, title: '' });
      if (cfg.vol) {
        const y = st('vol', { c: '#ff4d6d', c2: '#2ee59d', o: 55 });
        const volColor = (i) => (this.data[i].close >= this.data[i].open ? col(y.c, y.o) : col(y.c2, y.o));
        const hs = this._hist(V.VOL, volColor, pane);
        this.panes.vol = [hs];
        this._feeds.push({ s: hs, pick: (VV, j) => VV.VOL[j], color: (VV, j) => volColor(j) });
        // 量能均線：跟其他指標一樣吃色票（寫死 #ffd166 的話，淺色主題的圖例文字對比只有 1.44）
        if (cfg.volma) {
          const s = this._line(V.VOLMA, C.ma[0], pane, y.w);
          this.panes.vol.push(s);
          this._feeds.push({ s, pick: (VV, j) => (VV.VOLMA ? VV.VOLMA[j] : null) });
        }
        this.paneIndex.vol = pane; want[pane] = PH.vol; pane++; }
      if (cfg.kd) {
        const y = st('kd', { c: C.k, c2: C.d });
        const sk = this._line(V.KD.k, col(y.c, y.o), pane, y.w), sd = this._line(V.KD.d, col(y.c2, y.o), pane, y.w);
        this.panes.kd = [sk, sd];
        this._feeds.push({ s: sk, pick: (VV, j) => VV.KD.k[j] }, { s: sd, pick: (VV, j) => VV.KD.d[j] });
        ref(sk, 80, 'rgba(255,77,109,.35)'); ref(sk, 20, 'rgba(46,229,157,.35)');
        this.paneIndex.kd = pane; want[pane] = PH.ind; pane++; }
      this.divergences = { top: [], bottom: [] };
      this.divPane = null;
      if (cfg.macd) {
        const y = st('macd', { c: C.dif, c2: C.dea });
        const oscColor = (i) => (V.MACD.osc[i] >= 0 ? col('#ff4d6d', (y.o || 100) * .7) : col('#2ee59d', (y.o || 100) * .7));
        const ho = this._hist(V.MACD.osc, oscColor, pane);
        const sdif = this._line(V.MACD.dif, col(y.c, y.o), pane, y.w);
        const sdea = this._line(V.MACD.dea, col(y.c2, y.o), pane, y.w);
        this.panes.macd = [ho, sdif, sdea];
        this._feeds.push({ s: ho, pick: (VV, j) => VV.MACD.osc[j], color: (VV, j) => (VV.MACD.osc[j] >= 0 ? col('#ff4d6d', (y.o || 100) * .7) : col('#2ee59d', (y.o || 100) * .7)) },
          { s: sdif, pick: (VV, j) => VV.MACD.dif[j] },
          { s: sdea, pick: (VV, j) => VV.MACD.dea[j] });
        // 零軸跟著主題走，白色在淺色主題看不見
        ref(sdif, 0, C.line);
        /* ★ 2026-09-23 修回來的一行：下面這三個指派原本被寫在上一行的 `//` 註解後面，
           整段被吃掉了（7643b14 那次把註解補在同一行的尾巴）。後果是
           MACD 面板沒有登記 paneIndex（左上角標題不見）、pane 沒有 ++，
           於是 RSI 被畫進 MACD 那一格 —— 兩條完全不同尺度的線疊在一起。*/
        this.paneIndex.macd = pane; want[pane] = PH.ind; pane++;
        /* 背離（Andy 2026-09-15：「是很好的訊號」）。預設開，cfg.macdDiv === false 才關。
           主圖畫價格的那兩個轉折點，MACD 面板畫 DIF 的那兩點 —— 兩條線一起看才看得出「背」在哪。 */
        if (cfg.macdDiv !== false) {
          this.divPane = new DivPrimitive();
          sdif.attachPrimitive(this.divPane);
        }
      }
      this._setDiv(V);
      if (cfg.rsi) {
        const y = st('rsi', { c: C.rsi });
        const s = this._line(V.RSI, col(y.c, y.o), pane, y.w);
        this.panes.rsi = [s];
        this._feeds.push({ s, pick: (VV, j) => VV.RSI[j] });
        ref(s, 70, 'rgba(255,77,109,.35)'); ref(s, 30, 'rgba(46,229,157,.35)');
        this.paneIndex.rsi = pane; want[pane] = PH.ind; pane++; }
      /* 使用者自己拖過的高度優先。
         ★ 只在「這張圖第一次套指標」時做一次。
         Andy 2026-09-15：「底下每次更新都會動到我調整好的上下範圍會一直出現跳動，很麻煩」——
         盤中每 5 秒就會重跑一次 applyIndicators，每次都重套一遍等於把他拖好的位置一直重設。
         重建圖表（換股票／換週期）時 _paneInit 會是 undefined，那時才套。 */
      const saved = this._paneInit ? (this._paneMem || null) : cfg.paneH;
      this._paneInit = true;
      if (saved && !this.opts.compact) {
        // 副圖用存檔的高度，主圖自動吃剩下的 —— 那本來就是他拖出來的結果
        Object.keys(this.paneIndex).forEach(k => {
          const h = saved[k];
          if (h > 30) want[this.paneIndex[k]] = h;
        });
      }
      this._applyPaneHeights(want, PH);
      setTimeout(() => this._layoutLabels(), 30);
    }
    /* 面板高度一次全部套上去。
       ★ 不可以逐一呼叫 `pane.setHeight()`。Lightweight Charts 的 `setHeight` 內部是
       「把目標面板設成這個高度，剩下的差額平均分給其他面板」，而且它讀的是**上一次排版後**的高度 ——
       同一輪裡連續呼叫四次，後面三次看到的都還是最初的那組數字，等於把前面的設定一次次抹掉，
       最後一次（主圖）又把所有副圖推回原狀。2026-09-15 量到的後果：
       `PH.vol = 120 / PH.ind = 150` 寫了等於沒寫，實際是主圖 610、量與 KD、MACD 各 57 —— 就是 Andy 說的「太窄」。
       改用 stretch factor：它是相對值，圖表高度 × 自己的權重 ÷ 權重總和，一次設完就是最終比例，
       不受排版時機影響。權重直接用「想要的像素」，加起來剛好等於圖表高度時就是所見即所得。 */
    _applyPaneHeights(want, PH) {
      const ps = this.chart.panes();
      if (!ps || ps.length < 2) return;
      /* 基準高度用容器的 clientHeight，不是 `sum(pane.getHeight())`。
         後者在 applyIndicators 執行的當下常常還是上一次排版的值（實測 813px 的容器量到 1464），
         算出來的主圖權重就會偏大 —— 症狀是副圖比例對、但全部被壓扁（實測 64/80/80 而不是 120/150/150）。 */
      const total = (this.el.clientHeight > 120 ? this.el.clientHeight : 0)
        || ps.reduce((s, p) => s + (p.getHeight() || 0), 0) || 600;
      const subs = [];
      for (let i = 1; i < ps.length; i++) subs.push(Math.max(30, want[i] || PH.ind));
      let used = subs.reduce((s, h) => s + h, 0);
      // 副圖總高度不能把主圖擠沒了；擠到了就等比縮小副圖
      const room = Math.max(60, total - PH.min);
      if (used > room) { const k = room / used; for (let i = 0; i < subs.length; i++) subs[i] = Math.max(30, subs[i] * k); used = room; }
      const main = Math.max(PH.min, total - used);
      ps[0].setStretchFactor(main);
      for (let i = 1; i < ps.length; i++) ps[i].setStretchFactor(subs[i - 1]);
    }
    /** 目前每個面板的高度，形狀是 {main, vol, kd, macd, rsi}。拖完存起來下次沿用。 */
    paneHeights() {
      const ps = this.chart.panes();
      const out = { main: ps[0] ? Math.round(ps[0].getHeight()) : 0 };
      Object.keys(this.paneIndex).forEach(k => {
        const p = ps[this.paneIndex[k]];
        if (p) out[k] = Math.round(p.getHeight());
      });
      return out;
    }
    legendRect() {
      const lg = this.el && this.el.querySelector && this.el.querySelector('.legend-ov');
      if (!lg || !lg.offsetWidth || !lg.offsetHeight || lg.hidden) return null;
      const a = lg.getBoundingClientRect(), b = this.el.getBoundingClientRect();
      return { x: a.left - b.left, y: a.top - b.top, w: a.width, h: a.height };
    }
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
      /* ★ 2026-09-25（審查 R5：週線格的「掃蕩」疊了三個、CHoCH 跟掃蕩擠在一起）。
         同一側（K 棒上方／下方）靠得太近（約 60px 內，換算成根數）的標記併成一個：字寫成「CHoCH·掃蕩×3」，
         顏色與箭頭用最重要的那個（CHoCH > BOS > 掃蕩），位置落在最後一根。*/
      const idx = new Map(this.data.map((d, i) => [String(d.time), i]));
      const PRI = { CHoCH: 3, BOS: 2, '掃蕩': 1 };
      // 「幾根內算同一處」跟著棒寬走：字大約 60px 寬，棒越密要併的範圍越大（月線、四週期小格）
      let bsp = 7; try { bsp = this.chart.timeScale().options().barSpacing || 7; } catch (e) { /* 忽略 */ }
      const NEAR = Math.max(2, Math.min(12, Math.ceil(60 / bsp)));
      const merged = [];
      keep.forEach(mk => {
        const i = idx.get(String(mk.time));
        let prev = null; for (let j = merged.length - 1; j >= 0; j--) { if (merged[j].position === mk.position) { prev = merged[j]; break; } }
        if (prev && i != null && prev._i != null && i - prev._i <= NEAR) {
          prev._items.push(mk); prev._i = i; prev.time = mk.time;
          if ((PRI[mk.text] || 0) > (PRI[prev._lead.text] || 0)) prev._lead = mk;
        } else merged.push({ time: mk.time, position: mk.position, _i: i, _items: [mk], _lead: mk });
      });
      const out = merged.map(g => {
        const c = {}; g._items.forEach(x => { c[x.text] = (c[x.text] || 0) + 1; });
        const text = Object.keys(c).sort((a, b) => (PRI[b] || 0) - (PRI[a] || 0)).map(k => k + (c[k] > 1 ? '×' + c[k] : '')).join('·');
        return { time: g.time, position: g.position, color: g._lead.color, shape: g._lead.shape, text };
      });
      // 給區間標籤避讓用：每個標記落在哪根 K 棒、畫在上面還是下面
      this._markBoxes = out.map(o => { const d = this.data[idx.get(String(o.time))] || {}; return { time: o.time, pos: o.position, hi: d.high, lo: d.low, text: o.text }; });
      this.markerList = out.map((o, k) => ({ ...o, i: merged[k]._i }));   // 驗收讀這個（i＝落在第幾根）
      if (!this.markers) this.markers = LWC.createSeriesMarkers(this.candle, out); else this.markers.setMarkers(out);
    }
    setPriceLines(lines) { // [{price, title, color}]
      for (const p of this.priceLines) this.candle.removePriceLine(p); this.priceLines = [];
      for (const ln of lines) { if (ln.price == null) continue; this.priceLines.push(this.candle.createPriceLine({ price: ln.price, color: ln.color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: ln.title })); }
    }
    // 第二個參數是游標在圖內的座標，給「跟著游標走的資訊框」用（Andy 2026-09-15 圖一）
    onCrosshair(fn) { this.chart.subscribeCrosshairMove((p) => { if (!p.time) { fn(null, null); return; } const i = this.data.findIndex(d => String(d.time) === String(p.time)); fn(i >= 0 ? i : null, p.point || null); }); }
    fitLast(n) { this.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, this.data.length - n), to: this.data.length + 3 }); }
    /* 驗收用：主圖價格軸現在顯示的上下界。
       切週期後沒有重新自動縮放的話，這裡會留著上一個週期的範圍 —— K 棒被壓扁就是這樣來的。*/
    priceRange() {
      try {
        const r = this.candle.priceScale().getVisibleRange();
        return r ? { from: +r.from.toFixed(2), to: +r.to.toFixed(2) } : null;
      } catch (e) { return null; }
    }
    // K 棒寬度（每根佔幾 px）。Andy 要能自己調，而且預設要寬一點
    setBarSpacing(px) {
      const v = Math.max(2, Math.min(40, +px || 11));
      this.chart.timeScale().applyOptions({ barSpacing: v });
      this._bar = v;
    }
    // 重設整個介面：價格軸自動、時間軸回到最近 n 根（TradingView 右下角那顆的行為）
    resetView(n) { this.candle.priceScale().setAutoScale(true); this.chart.timeScale().resetTimeScale(); this.fitLast(n || 160); }
    enableDrawing(key) { if (this.draw) this.draw.destroy(); this.draw = new Drawings(this, key); return this.draw; }
    destroy() {
      this._dead = true;
      // 這兩個掛在容器上，容器不會跟著圖表一起消失 —— 一定要自己拿掉
      if (this._onWheel) this.el.removeEventListener('wheel', this._onWheel);
      if (this._onDbl) this.el.removeEventListener('dblclick', this._onDbl);
      if (this.draw) this.draw.destroy();
      if (this._ro) this._ro.disconnect();
      // ③ 的監聽與提示：圖表 remove 之後還留著的話，下一次拖曳會踩到已經死掉的 chart
      if (this._onRange) { try { this.chart.timeScale().unsubscribeVisibleLogicalRangeChange(this._onRange); } catch (e) { /* 圖已銷毀 */ } }
      if (this._arm) ['pointerdown', 'wheel', 'touchstart'].forEach(ev => this.el.removeEventListener(ev, this._arm));
      clearTimeout(this._noteT);
      this.chart.remove();
    }
  }

  global.KChart = KChart; global.KInd = ind;
  global.KUtil = { resampleDaily, toTime, fmtTime, colors: C, refreshTheme, DRAW_TOOLS, DRAW_COLORS, ZONE_DEF, hexa, hist: HIST };
})(window);
