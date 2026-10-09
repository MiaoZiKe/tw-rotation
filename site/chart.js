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
        const label = z.label || `${dem ? '需求' : '供給'}${z.tf ? ' ' + z.tf : ''} ${z.low}–${z.high}`;
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


  /* ---------------------------------------------------------------- SMC 價位線（2026-10-05）
     Andy：「AI 分析／技術分析卡裡提到的價位，需要補在上方 K 線圖，並且這是可以開啟關閉的指標」。
     這一層只負責「畫」：BOS／CHoCH 水平虛線、最近支撐／壓力粗線、停損線，以及圖底一行免責小字。
     價位本身一律由呼叫端（industry.js 的 smcOverlay）從 payload 的 mtf／analysis 取，
     **這裡不算任何東西** —— 圖上的數字跟 AI 卡同一份，不可能兩邊講不一樣。
     需求／供給矩形沿用上面的 ZonesPrimitive（since 起畫、右邊停在最後一根）。
     每條線從 t0（形成那根）畫到最後一根，t0 在可視範圍左邊就從左緣畫起。 */
  /* ★ 2026-10-06（Andy：「所有長條圖…都需要 Y 軸微微區分月份及年份」，DECISIONS #337）：K 線的垂直分隔線。
     lightweight-charts 自己的 vertLines 是「依刻度」畫的、沒辦法分年月，所以用自訂 primitive（畫在最底層、資料線底下）。
     層級與顏色跟 ECharts 那一邊同一份邏輯（site/timegrid.js）：看得到的期間 ≤10 天畫日線（分時）、≤62 天畫週線、
     ≤5 年畫月線＋年線、更長只畫年線；週線／月線圖不畫週線／月線（每根都是新的一週就變成柵欄）。
     每個 pane 掛一個（主圖、成交量、MACD…），host 是 KChart（讀它的 data）。 */
  class TimeGridPrimitive {
    constructor(host) { this.host = host; this.drawn = null; this.lastX = []; this._k = null; this.marks = []; this.tms = []; this.step = 1; this.intraday = false; }
    attached(p) { this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._chart = null; }
    updateAllViews() {}
    refresh() { this._k = null; if (this._req) this._req(); }
    _build() {
      const d = (this.host && this.host.data) || [];
      const k = d.length + '|' + (d.length ? d[0].time + '|' + d[d.length - 1].time : '');
      if (k === this._k) return;
      this._k = k;
      const TG = global.TimeGrid; this.marks = []; this.tms = [];
      if (!TG || d.length < 3) return;
      const ent = d.map(b => {
        const t = b.time;
        if (typeof t === 'number') { const x = new Date(t * 1000); return { y: x.getUTCFullYear(), m: x.getUTCMonth() + 1, d: x.getUTCDate(), hm: String(x.getUTCHours()) + ':' + x.getUTCMinutes(), gran: 'day' }; }
        if (t && typeof t === 'object') return { y: t.year, m: t.month, d: t.day, hm: null, gran: 'day' };
        return TG.parse(String(t));
      });
      if (ent.some(e => !e)) return;
      this.intraday = !!ent[0].hm && typeof d[0].time === 'number';
      this.step = TG.avgStepDays(ent);
      this.marks = TG.marksFromEntries(ent);
    }
    paneViews() { const self = this; return [{ zOrder: () => 'bottom', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      const TG = global.TimeGrid; if (!TG || !self._chart) return;
      if (mediaSize.width < 200 || mediaSize.height < 70) return;      // 太小的縮圖（四週期小圖）不畫，免得線比資料還多；pane 寬不含右側價格軸，大盤三張小卡約 280～292
      self._build(); if (!self.marks.length) return;
      const ts = self._chart.timeScale();
      const lr = ts.getVisibleLogicalRange(); if (!lr) return;
      const visDays = Math.max(0.01, (lr.to - lr.from) * self.step);
      const L = TG.levels(visDays, self.intraday);
      const lo = Math.floor(lr.from) - 1, hi = Math.ceil(lr.to) + 1;
      self.drawn = { year: 0, month: 0, week: 0, day: 0 }; self.lastX = [];
      ctx.save(); ctx.lineWidth = TG.hair(); const dk = TG.densK(visDays);
      const cols = { year: TG.color("year", dk), month: TG.color("month"), week: TG.color("week"), day: TG.color("day") };
      for (const m of self.marks) {
        if (m.i < lo || m.i > hi || !L[m.kind]) continue;
        const a = ts.logicalToCoordinate(m.i - 1), b = ts.logicalToCoordinate(m.i);
        if (a === null || b === null) continue;
        const x = TG.crisp((a + b) / 2);
        if (x < 0 || x > mediaSize.width) continue;
        self.drawn[m.kind]++; self.lastX.push([m.kind, x]);
        ctx.strokeStyle = cols[m.kind];
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, mediaSize.height); ctx.stroke();
      }
      ctx.restore();
    }); } }) }]; }
  }

  class SmcLinesPrimitive {
    constructor() { this.lines = []; this.note = ''; this.lastTime = null; this.placed = []; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    set(lines, note) { this.lines = lines || []; this.note = note || ''; if (this._req) this._req(); }
    setLastTime(t) { this.lastTime = t; if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() { const self = this; return [{ zOrder: () => 'top', renderer: () => ({ draw(target) { target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      self.placed = [];
      if (!self._series || !self._chart) return;
      if (!self.lines.length && !self.note) return;
      const ts = self._chart.timeScale();
      let xEnd = mediaSize.width;
      if (self.lastTime != null) { const e = ts.timeToCoordinate(self.lastTime); if (e !== null && isFinite(e)) xEnd = Math.min(mediaSize.width, e + 6); }
      ctx.save();
      ctx.font = '600 10.5px "Noto Sans TC", "JetBrains Mono", sans-serif';
      const used = self.getAvoid ? self.getAvoid() : [];
      const hit = (r) => used.some(b => r.x < b.x + b.w && r.x + r.w > b.x && r.y < b.y + b.h && r.y + r.h > b.y);
      for (const L of self.lines) {
        const y = self._series.priceToCoordinate(L.price); if (y === null || !isFinite(y)) continue;
        let x0 = 0;
        if (L.t0 != null) { const c = ts.timeToCoordinate(toTime(L.t0)); if (c !== null && isFinite(c)) x0 = c; }
        if (x0 >= xEnd) continue;
        ctx.strokeStyle = L.color; ctx.lineWidth = L.width || 1;
        ctx.setLineDash(L.dash || []);
        ctx.beginPath(); ctx.moveTo(Math.max(0, x0), Math.round(y) + .5); ctx.lineTo(xEnd, Math.round(y) + .5); ctx.stroke();
        ctx.setLineDash([]);
        if (x0 > 0) { ctx.fillStyle = L.color; ctx.beginPath(); ctx.arc(x0, y, 2.5, 0, 7); ctx.fill(); }
        if (!L.label) continue;
        const tw = ctx.measureText(L.label).width;
        // 標籤先試線的上方、再試下方；左右先貼最後一根左邊，撞到就往左挪，全撞就不印（線還在）
        let pos = null;
        // 第一輪只在線段上方找位置；線太短（例如最近幾根才形成的 BOS）第二輪才允許往線段左邊放
        for (const lo of [Math.max(2, x0 + 4), 2]) for (const ly of [y - 4, y + 13]) {
          if (pos) break;
          for (let lx = Math.min(xEnd - tw - 8, mediaSize.width - tw - 8); lx >= lo - 0.1; lx -= 24) {
            const r = { x: lx - 3, y: ly - 10, w: tw + 6, h: 13 };
            if (r.y < 2 || r.y + r.h > mediaSize.height - 2) continue;
            if (!hit(r)) { pos = { lx, ly, r }; break; }
          }
        }
        if (!pos) continue;
        used.push(pos.r);
        self.placed.push({ label: L.label, kind: L.kind, x: pos.r.x, y: pos.r.y, w: pos.r.w, h: pos.r.h });
        ctx.fillStyle = 'rgba(10,16,32,.82)'; ctx.fillRect(pos.r.x, pos.r.y, pos.r.w, pos.r.h);
        ctx.fillStyle = L.color; ctx.textAlign = 'left'; ctx.fillText(L.label, pos.lx, pos.ly);
      }
      if (self.note) {
        ctx.font = '500 10px "Noto Sans TC", sans-serif'; ctx.textAlign = 'left';
        ctx.fillStyle = 'rgba(150,165,200,.8)';
        ctx.fillText(self.note, 8, mediaSize.height - 6);
      }
      ctx.restore();
    }); } }) }]; }
  }

  /* ---------------------------------------------------------------- 繪圖層
     ★ 2026-10-02（DECISIONS #289）整套搬到 site/drawtools.js（DrawTools.Drawings）：
     文字框、橡皮擦、屬性列、選取／拖曳、測量、成交量分佈都住在那裡，這裡只留轉接。
     DRAW_TOOLS／DRAW_COLORS 保留成別名，舊的呼叫端（KUtil.DRAW_*）不用改。 */
  const DRAW_TOOLS = (global.DrawTools && global.DrawTools.TOOLS) || [];
  const DRAW_COLORS = (global.DrawTools && global.DrawTools.COLORS) || ['#3ee0ff'];

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
      if (window.TwGw && window.TwGw.on()) j = await window.TwGw.json(`hist/${code}/p${n}`, { cache: 'force-cache' });   // data-gw：付費檔走 gateway
      else { const r = await fetch(`data/hist/${code}/p${n}.json`, { cache: 'force-cache' }); j = r.ok ? await r.json() : null; }
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
      autoSize: true, layout: { attributionLogo: false, background: { color: C.bg }, textColor: C.text, fontFamily: '"JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace', fontSize: 12, panes: { separatorColor: C.line, separatorHoverColor: 'rgba(62,224,255,.55)', enableResize: true } },
      grid: { vertLines: { color: C.grid, visible: false }, horzLines: { color: C.grid } },   // 設計 v4 §4.1：軸字 11→12、垂直格線關掉
      crosshair: { mode: LWC.CrosshairMode.Normal, vertLine: { labelBackgroundColor: C.panel3 }, horzLine: { labelBackgroundColor: C.panel3 } },
      rightPriceScale: { borderColor: C.line, scaleMargins: { top: 0.08, bottom: 0.08 } },
      timeScale: { borderColor: C.line, timeVisible: true, secondsVisible: false, rightOffset: 4, barSpacing: 7 },
      handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      localization: { locale: 'zh-TW', timeFormatter: (t) => fmtTime(t, h && h.tf) },
    };
  }


  /* ★ 2026-10-09 手機 v2（Andy 09:1x 看 402 寬預覽：「K線圖 走勢圖 Y軸都沒資訊了，需要你完整他」）：
     手機的價格軸只有 60～70px 寬，「48475.74」「47500.00」這種八、九個字的刻度一多就互相壓、最上面那一格被現價標籤蓋掉、
     量軸頂格「20000億」被面板分隔線切一半。只在 html.m4（≤640）改「刻度怎麼寫」，桌機一行不動（桌機守門1008）：
       · 刻度（tickmarksPriceFormatter）：≥ 10,000 寫成 48k／47.5k；≥ 1,000 去小數；其他依刻度間距給 0～2 位小數。
       · 現價標籤與十字游標（priceFormatter）：≥ 1,000 去小數（2585、48476），< 1,000 保留兩位 —— 精確值在圖上方的大字與 OHLC 框。
       · 量軸（自訂格式的量柱）照它自己的單位，不吃上面兩條（大盤量軸的精簡與頂端留白在 market3.js decorVol）。*/
  const isM4 = () => document.documentElement.classList.contains('m4');
  function m4Tick(ps) {
    const a = ps.filter(Number.isFinite), step = a.length > 1 ? Math.abs(a[1] - a[0]) : 1;
    const dec = step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
    return ps.map((v) => {
      const x = Math.abs(v);
      if (x >= 1e4) { const k = v / 1000; return (Math.abs(k - Math.round(k)) < 0.05 ? Math.round(k) : k.toFixed(1)) + 'k'; }
      if (x >= 1000) return String(Math.round(v));
      return v.toFixed(dec);
    });
  }
  function m4Price(v) { return Math.abs(v) >= 1000 ? String(Math.round(v)) : v.toFixed(2); }
  /* 主圖那條序列（K 棒／分時面積線）的格式：自訂格式＋刻度格式，只套在它身上 ——
     ⚠ 不用整張圖的 localization.tickmarksPriceFormatter：那條會連量軸（自訂單位「萬張／億」）一起蓋掉（實測變成「2000000000k」）。*/
  function m4Fmt(series) {
    if (!isM4() || !series) return;
    try { series.applyOptions({ priceFormat: { type: 'custom', minMove: 0.01, formatter: m4Price, tickmarksFormatter: m4Tick } }); } catch (e) { /* 舊版：維持預設 */ }
  }
  class KChart {
    constructor(el, opts) {
      this.el = el; this.opts = Object.assign({ mini: false, tf: '1d' }, opts);
      this.chart = LWC.createChart(el, baseOptions(this.opts));
      /* ★ 2026-10-09 拖曳邊界1009（Andy：「所有圖扁長寬到了就好…不可以還能一直滑過頭超出範圍」）：
         圖表庫預設可以把 K 線往左拖到最新一根的右邊一大片空白、往右拖過第一根、兩指縮小到整段資料只剩中間一小條。
         手機（html.m4）把兩邊釘住：fixLeftEdge＝第一根貼左緣就拖不動、fixRightEdge＝最新一根貼右緣就拖不動，
         兩個一起開也順便讓「縮小」最多縮到整段資料剛好填滿（＝1×），不會再縮出空白。
         只限手機：桌機的右側留白（rightOffset 4 根）與自由拖曳照舊（桌機守門1008）。 */
      if (document.documentElement.classList.contains('m4')) this.chart.applyOptions({ timeScale: { fixLeftEdge: true, fixRightEdge: true } });
      // 手機：價格軸最上／最下那格刻度整個畫在面板裡（不被面板上緣或分隔線切一半；Andy 10-09「Y軸都沒資訊了，需要你完整他」）
      if (isM4()) this.chart.applyOptions({ rightPriceScale: { ensureEdgeTickMarksVisible: true } });
      this.candle = this.chart.addSeries(LWC.CandlestickSeries, { upColor: C.up, downColor: C.down, borderUpColor: C.up, borderDownColor: C.down, wickUpColor: C.up, wickDownColor: C.down, priceLineVisible: true, lastValueVisible: true });
      m4Fmt(this.candle);   // 手機價格軸刻度精簡（見 m4Tick）
      this.zones = new ZonesPrimitive([]); this.candle.attachPrimitive(this.zones);
      this.tgrid = []; { const g0 = new TimeGridPrimitive(this); this.candle.attachPrimitive(g0); this.tgrid.push(g0); this._tgPanes = { 0: g0 }; }   // 時間軸分隔線（DECISIONS #337）
      this.divPrice = new DivPrimitive(); this.candle.attachPrimitive(this.divPrice);
      this.smcLines = new SmcLinesPrimitive(); this.candle.attachPrimitive(this.smcLines);
      // 價位線標籤要避開：左上角圖例、需求／供給區已經印好的標籤（同一個 pane，區域層先畫，所以 placed 已經是這一幀的）
      this.smcLines.getAvoid = () => { const lg = this.legendRect(); return (lg ? [lg] : []).concat(this.zones.placed || []); };
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
      } else {
        /* ★ 2026-10-06 四週期小圖也有 KD／MACD／RSI 副圖了（DECISIONS #335）：副圖左上角要寫是哪個指標，
           不然三個副圖疊在一起分不出誰是誰。只掛標籤層，不掛浮水印／滾輪／回補（那些是整頁大圖的事）。*/
        this.labels = document.createElement('div'); this.labels.className = 'pane-labels mini'; el.appendChild(this.labels);
      }
      /* ★ 2026-09-26（Andy：「幫我將縮放放到圖上位置」）：「重設縮放」鈕從工具列搬進圖裡 ——
         主圖 K 棒區的右下角、價格軸左邊、成交量副圖上方。半透明角標（⌜⌟），滑過才變亮。
         位置跟著主圖面板高度與價格軸寬度走（_layoutCorner），副圖拖大拖小、換指標都會重算。
         為什麼放右下角：時間軸的 rightOffset 在最新一根右邊留了幾根的空白，
         價格軸上的現價標籤在軸上、不在繪圖區 —— 那一格是整張圖最不會蓋到東西的地方。
         四週期同看的每張小圖也各有一顆（重設的是那一張自己的縮放；各格可以各自滾輪縮放）。*/
      if (typeof this.opts.fit === 'function') {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'kfit';
        if (this.opts.fitId) b.id = this.opts.fitId;
        b.title = '重設縮放（雙擊價格軸也可以）'; b.setAttribute('aria-label', '重設縮放');
        b.innerHTML = '<svg viewBox="0 0 18 18"><path d="M3,7 V3 H7 M11,3 H15 V7 M15,11 V15 H11 M7,15 H3 V11"/></svg>';
        // 畫線工具在 el 上用 capture 聽 pointerdown；按這顆不能變成「在圖上點了一筆」
        b.addEventListener('pointerdown', (e) => e.stopPropagation(), true);
        b.onclick = (e) => { e.stopPropagation(); this.opts.fit(this); };
        el.appendChild(b); this.fitEl = b;
        // 小圖：容器長高（勾了副圖）時，重設鈕與副圖標籤一起重排 —— _layoutLabels 會先叫 _layoutCorner
        if (!this._ro) { this._ro = new ResizeObserver(() => this._layoutLabels()); this._ro.observe(el); }
      }
      /* 副圖分隔線拖完（放開滑鼠）面板高度就變了，左上角的面板標題與右下角的重設鈕要跟著重排 ——
         以前只有容器尺寸變（ResizeObserver）才重排，拖完分隔線標題會停在舊的位置。*/
      this._onUp = () => setTimeout(() => { if (!this._dead) this._layoutLabels(); }, 60);
      el.addEventListener('pointerup', this._onUp);
    }
    /* 重設鈕貼在主圖（第 0 個面板）的右下角：right＝價格軸寬＋6、top＝主圖高－鈕高－6。
       還量不到尺寸（0×0 初始化）就先藏起來，下一次重排再出現，不會閃在左上角。*/
    _layoutCorner() {
      const b = this.fitEl; if (!b || this._dead) return;
      let mh = 0, pw = 0;
      try { const ps = this.chart.panes(); mh = ps[0] ? ps[0].getHeight() : 0; pw = this.chart.priceScale('right').width(); } catch (e) { /* 圖已銷毀 */ }
      if (!(mh > 40)) { b.style.visibility = 'hidden'; return; }
      const sz = this.opts.mini ? 24 : 28;
      b.style.visibility = '';
      b.style.top = Math.round(mh - sz - 6) + 'px';
      b.style.right = Math.round((pw || 56) + 6) + 'px';
    }
    setWatermark(text) { if (this.wm) this.wm.textContent = text || ''; }
    // 各指標面板左上角的標題（成交量 / KD(9,3,3) / MACD(12,26,9) / RSI(14)）＋當下數值
    setPaneLabels(map) { this._paneText = map || {}; this._layoutLabels(); }
    _layoutLabels() {
      this._layoutCorner();
      // 主圖高度變了（視窗縮放、副圖拖大拖小）→ 依同一個資訊列高度重算頂端保留比例（reserveTop）
      if (this._resPx != null) this.reserveTop(this._resPx);
      if (!this.labels) return;
      const ps = this.chart.panes(); let top = 0; const tops = ps.map(p => { const t = top; top += p.getHeight() + 1; return t; });
      const strip = this._lblStrip();
      const off = strip ? 3 : 6;
      const html = Object.entries(this.paneIndex).map(([k, i]) => tops[i] == null ? '' : `<div style="top:${tops[i] + off}px">${(this._paneText || {})[k] || ''}</div>`).join('');
      this.labels.innerHTML = html;
      /* ★ 2026-09-29 設計 v4 第二批 2B（01 §4「圖例一律在繪圖區外」）：副圖左上角的標籤（成交量／KD／MACD／RSI ＋ 當下數值）
         以前直接蓋在副圖的資料上 —— 左邊一根大量的量柱、KD 在 80 以上的線，都會鑽到標籤底下。
         整頁大圖（不是總覽小卡 compact、不是四週期小圖 mini）的每個副圖，頂端留一條 LBL_STRIP px 的標籤帶：
         價格軸的 scaleMargins.top＝標籤帶 ÷ 副圖高，資料只畫在標籤帶下面。副圖預設高度同時加高一條標籤帶（_ph），
         所以量柱、指標線可畫的高度跟改前一樣，多出來的高度是從主圖拿的（1440×900：主圖 587 → 563px，仍 ≥ 可視高度 55%）。
         副圖被拖大拖小、指標開關時都會走到這裡，高度一變就重算（sig 沒變就不動，十字游標移動時不會一直 applyOptions）。*/
      if (!strip) return;
      const sig = ps.map(p => Math.round(p.getHeight())).join(',');
      if (sig === this._lblSig) return;
      this._lblSig = sig;
      for (let i = 1; i < ps.length; i++) {
        const h = ps[i].getHeight(); if (!(h > 30)) continue;
        const t = Math.min(0.45, strip / h);
        const ss = ps[i].getSeries ? ps[i].getSeries() : [];
        for (const s of ss) {
          try { const cur = (s.priceScale().options() || {}).scaleMargins || {};
            s.priceScale().applyOptions({ scaleMargins: { top: t, bottom: cur.bottom != null ? cur.bottom : 0.08 } }); } catch (e) { /* 圖剛銷毀 */ }
        }
      }
    }
    /** ★ 2026-10-04（Andy：「K 線圖需要打開都可以看到，如果被遮住就整體下移」）：
        主圖左上角的 OHLC／均線資訊列（#legendOv）是蓋在繪圖區上的。把主圖價格軸的 scaleMargins.top 設成
        「資訊列底緣到主圖頂端的距離 ＋ 6px」÷ 主圖高，K 棒最高點就一定畫在資訊列下面；行數變了（指標開關、視窗變窄折行）
        由呼叫端量完再呼叫，數值沒變就不動（十字游標移動時不會一直 applyOptions）。上限 0.45，避免把 K 棒壓扁。*/
    reserveTop(px) {
      this._resPx = px;
      try {
        const ps = this.chart.panes(); const h = ps[0] ? ps[0].getHeight() : 0; if (!(h > 60)) return;
        const t = Math.max(0.08, Math.min(0.45, (px + 6) / h));
        if (this._resTop != null && Math.abs(this._resTop - t) < 0.004) return;
        this._resTop = t;
        const cur = (this.candle.priceScale().options() || {}).scaleMargins || {};
        this.candle.priceScale().applyOptions({ scaleMargins: { top: t, bottom: cur.bottom != null ? cur.bottom : 0.08 } });
      } catch (e) { /* 圖已銷毀 */ }
    }
    /** 副圖標籤帶的高度（px）；總覽小卡、四週期小圖不留（它們的標籤規格另外一套）。*/
    /*  手機（≤640）也不留：手機的 K 線本來就矮（360～620px），再從主圖拿一條會讓 K 棒被壓扁，手機版面歸 mobile-ui 另外定。*/
    _lblStrip() {
      if (this.opts.mini || this.opts.compact) return 0;
      try { if (!window.matchMedia('(min-width:641px)').matches) return 0; } catch (e) { /* 沒有 matchMedia 就照桌機 */ }
      return KChart.LBL_STRIP;
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
        if (this.zones && this.data.length) { this.zones.setLastTime(this.data[this.data.length - 1].time); this.smcLines.setLastTime(this.data[this.data.length - 1].time); }
        return;
      }
      this.defaultView();
      // 供需區的右邊界要停在最後一根 K 棒，不是畫面右緣
      if (this.zones && this.data.length) { this.zones.setLastTime(this.data[this.data.length - 1].time); this.smcLines.setLastTime(this.data[this.data.length - 1].time); }
    }
    /** 換股／換週期時的預設取景（2026-09-26 從 setBars 抽出來：四週期小圖右下角的「重設縮放」也要回到這個樣子）。*/
    defaultView() {
      if (!this.data || !this.data.length) return;
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
      if (this.zones && this.data.length) { this.zones.setLastTime(this.data[this.data.length - 1].time); this.smcLines.setLastTime(this.data[this.data.length - 1].time); }
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
    /** SMC 疊圖（2026-10-05）：{zones:[{kind,low,high,since,tf,tip}], lines:[{price,t0,color,width,dash,label,kind}], note}
        傳 null 全部清掉。zones 的 since 呼叫端要先對齊成「這個週期裡第一根 ≥ since 的 K 棒時間」，不然週線找不到座標。
        滑過矩形時在圖上浮一張小卡寫 tip（「需求區（日線）1,367.18–1,430.39，形成於 09-xx」）。*/
    setSmc(o) {
      this._smc = o || null;
      this.zones.setZones(o ? o.zones : [], o && o.style ? o.style : null);
      this.smcLines.set(o ? o.lines : [], o ? o.note : '');
      if (!this._smcTip && !this.opts.mini) {
        const tip = document.createElement('div'); tip.className = 'smc-tip'; tip.hidden = true;
        tip.style.cssText = 'position:absolute;z-index:6;pointer-events:none;padding:4px 8px;border-radius:6px;font-size:12px;background:var(--panel-2,#121a30);border:1px solid var(--line-2,#2a3860);color:var(--ink,#e6ecff);white-space:nowrap';
        this.el.appendChild(tip); this._smcTip = tip;
        this.chart.subscribeCrosshairMove((p) => {
          const z = this._smc && p && p.point && p.time != null ? this.smcHit(p.point.x, p.point.y) : null;
          if (!z) { tip.hidden = true; return; }
          tip.textContent = z.tip; tip.hidden = false;
          const w = this.el.clientWidth;
          tip.style.left = Math.min(Math.max(4, p.point.x + 14), Math.max(4, w - tip.offsetWidth - 70)) + 'px';
          tip.style.top = Math.max(4, p.point.y - 30) + 'px';
        });
      }
      if (!o && this._smcTip) this._smcTip.hidden = true;
    }
    /** 座標 (x,y) 落在哪個 SMC 矩形裡（驗收也用這支）：價格在區間內、時間在形成那根之後 */
    smcHit(x, y) {
      if (!this._smc || !(this._smc.zones || []).length) return null;
      const price = this.candle.coordinateToPrice(y); if (price == null) return null;
      const ts = this.chart.timeScale();
      for (const z of this._smc.zones) {
        if (price < z.low || price > z.high) continue;
        const c = z.since != null ? ts.timeToCoordinate(toTime(z.since)) : null;
        if (c !== null && c != null && x < c) continue;
        return z;
      }
      return null;
    }
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
          this._histNote('已經到最早一筆了', 3200);
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
        this._histNote(n ? `已載入到 ${this.data.length ? fmtTime(this.data[0].time, this.tf) : ''}`
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
      if (this.zones && this.data.length) { this.zones.setLastTime(this.data[this.data.length - 1].time); this.smcLines.setLastTime(this.data[this.data.length - 1].time); }
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
      if (this._tgPanes) this._tgPanes = { 0: this._tgPanes[0] };      // 副圖的分隔線 primitive 跟著 series 一起被移除了，下次建 series 再掛
    }
    /* 驗收用：主圖的時間軸分隔線——全部標記各層幾個、這一幀實際畫了幾條（含 x 座標） */
    tgridInfo() {
      const g = this.tgrid && this.tgrid[0]; if (!g) return null;
      g._build();
      const all = { year: 0, month: 0, week: 0, day: 0 }; g.marks.forEach(m => { all[m.kind]++; });
      return { all, drawn: g.drawn, x: g.lastX, panes: Object.keys(this._tgPanes || {}).length };
    }
    _tgAttach(s, pane) {      // 副圖（成交量／KD／MACD／RSI）每個 pane 掛一次時間軸分隔線
      if (!pane || !this._tgPanes || this._tgPanes[pane]) return;
      const g = new TimeGridPrimitive(this); s.attachPrimitive(g); this._tgPanes[pane] = g;
    }
    _line(vals, color, pane, width, opts) {
      const s = this.chart.addSeries(LWC.LineSeries, Object.assign({ color, lineWidth: width || 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, opts || {}), pane || 0);
      /* ★ 2026-09-25：缺值給 whitespace（只有 time），不再整點丟掉、也絕不給 value:null。
         丟掉會讓指標線跟 K 棒的時間軸對不齊（開頭 MA60 前 59 根整段不存在）；
         value:null 則是 Lightweight Charts 正式版不驗、畫圖時內部丟「Value is null」的那種資料。
         用 Number.isFinite 一起擋掉 NaN／Infinity（MA 在稀疏序列、除以 0 的指標都可能產生）。*/
      s.setData(this.data.map((d, i) => Number.isFinite(vals[i]) ? { time: d.time, value: vals[i] } : { time: d.time }));
      this._tgAttach(s, pane);
      return s;
    }
    _hist(vals, colorFn, pane) {
      const s = this.chart.addSeries(LWC.HistogramSeries, { priceLineVisible: false, lastValueVisible: false, priceFormat: pane === 1 && this.cfg && this.cfg.vol ? { type: 'custom', minMove: 1, formatter: (v) => (Math.abs(v) >= 1e7 ? (v / 1e7).toFixed(1) + '萬張' : (v / 1000).toFixed(0) + '張') } : { type: 'price', precision: 2, minMove: 0.01 } }, pane);
      // 同 _line：缺值給 whitespace，NaN／Infinity 一起擋（以前這裡連 NaN 都沒擋）
      s.setData(this.data.map((d, i) => Number.isFinite(vals[i]) ? { time: d.time, value: vals[i], color: colorFn(i) } : { time: d.time }));
      this._tgAttach(s, pane);
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
          if (!Number.isFinite(v)) continue;   // null／NaN／Infinity 都不推（setData 那邊已放 whitespace 佔位）
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
      if (this._paneInit && !this.opts.compact && !this.opts.mini) {
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
      /* 四週期同看的小圖（mini）：成交量副圖吃圖高的 20%（Andy 2026-09-26「四週期成交量呢？」，
         要 18～22%）。一律用比例、不吃使用者在大圖拖出來的 paneH —— 大圖的 100px 放進 300px 的小格就是三分之一。*/
      const PH = this._ph();
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
      if (saved && !this.opts.compact && !this.opts.mini) {
        // 副圖用存檔的高度，主圖自動吃剩下的 —— 那本來就是他拖出來的結果
        Object.keys(this.paneIndex).forEach(k => {
          const h = saved[k];
          if (h > 30) want[this.paneIndex[k]] = h;
        });
      }
      this._applyPaneHeights(want, PH);
      setTimeout(() => { if (!this._dead) this._layoutLabels(); }, 30);
    }
    /** 各面板想要的高度（像素）。拆成方法是為了 setVolRatio() 能在不重建指標的情況下重排。 */
    _ph() {
      const mh0 = this.el.clientHeight || 300;
      /* 四週期小圖（mini）有 opts.indH 時（2026-10-06，個股頁四週期同看）：容器已經依副圖數量撐高了 n × indH，
         KD／MACD／RSI 每個副圖固定吃 indH，主圖與成交量照舊在「扣掉副圖之後的那一段」裡分 50%／20% ——
         所以勾副圖不會把 K 棒壓扁、副圖也不會被等比縮到看不出線（舊的 20% 一套在 300px 小格就只剩 37px）。
         沒給 indH（自選頁的小圖）照舊全部用比例。*/
      const nInd = this.opts.mini && this.cfg ? ['kd', 'macd', 'rsi'].filter(k => this.cfg[k]).length : 0;
      const ih = this.opts.mini && this.opts.indH > 0 && nInd ? this.opts.indH : 0;
      const base = ih ? Math.max(120, mh0 - nInd * ih) : mh0;
      const PH = this.opts.mini
        ? { vol: Math.round(base * 0.2), ind: ih || Math.round(mh0 * 0.2), min: Math.round(base * 0.5) }
        : this.opts.compact
        ? { vol: 52, ind: 58, min: 110 }
        // Andy 2026-09-15：「下面的成交量 MACD 這些指標上下間隔寬點」。
        // 以前實際只有 57~67px；這組在 813px 高的個股頁量到量 96／KD 115／MACD 115，主圖還有 441。
        // 再大就要吃掉主圖了 —— 他同樣在意 K 線圖要大（DECISIONS #101），想更寬可以自己拖，會記住。
        // 設計 v4 2B：副圖頂端多一條標籤帶（KChart.LBL_STRIP），預設高度跟著加，可畫資料的高度不變（見 _layoutLabels）
        : { vol: 100 + this._lblStrip(), ind: 120 + this._lblStrip(), min: 260 };
      /* ★ 2026-09-28 opts.volRatio（只給 mini／compact 用）：量副圖佔圖高的比例。
         總覽大盤三張圖要「拖一張、另外兩張跟著變」（Andy：「成交量縮放只需要抓取其中一條，其他兩條會連動」），
         三張圖高度不一定一樣（展開那張比較高），所以共用的是**比例**不是像素。
         小卡以前每 10 秒重建一次指標就把使用者拖好的量副圖打回 20%（小卡不走 _paneMem），有了這個比例也一併解掉。*/
      const vr = +this.opts.volRatio;
      if ((this.opts.mini || this.opts.compact) && vr >= 0.05 && vr <= 0.8) PH.vol = Math.round((this.opts.mini ? base : mh0) * vr);
      return PH;
    }
    /** 量副圖改成佔圖高 r（0.05～0.8），不重建任何 series、不動可視範圍。沒有量副圖時只記下來，下次建圖用。 */
    setVolRatio(r) {
      if (!(r >= 0.05 && r <= 0.8)) return;
      this.opts.volRatio = r;
      if (this._dead || !this.chart || this.paneIndex.vol == null) return;
      const PH = this._ph(); const want = [0];
      Object.keys(this.paneIndex).forEach(k => { want[this.paneIndex[k]] = k === 'vol' ? PH.vol : PH.ind; });
      try { this._applyPaneHeights(want, PH); } catch (e) { /* 圖剛銷毀 */ }
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
    // 手繪工具在 drawtools.js（DECISIONS #289）；舊的那一組會沿用同一個 localStorage key，所以畫過的線不會不見
    enableDrawing(key) { if (this.draw) this.draw.destroy(); this.draw = global.DrawTools ? new global.DrawTools.Drawings(this, key) : null; return this.draw; }
    destroy() {
      this._dead = true;
      // 這兩個掛在容器上，容器不會跟著圖表一起消失 —— 一定要自己拿掉
      if (this._onWheel) this.el.removeEventListener('wheel', this._onWheel);
      if (this._onDbl) this.el.removeEventListener('dblclick', this._onDbl);
      if (this._onUp) this.el.removeEventListener('pointerup', this._onUp);
      if (this.fitEl && this.fitEl.parentNode) this.fitEl.parentNode.removeChild(this.fitEl);
      // 小圖的副圖標籤層掛在呼叫端的容器上（自選頁會重用同一個容器），跟著拿掉
      if (this.opts.mini && this.labels && this.labels.parentNode) this.labels.parentNode.removeChild(this.labels);
      if (this.draw) this.draw.destroy();
      if (this._ro) this._ro.disconnect();
      // ③ 的監聽與提示：圖表 remove 之後還留著的話，下一次拖曳會踩到已經死掉的 chart
      if (this._onRange) { try { this.chart.timeScale().unsubscribeVisibleLogicalRangeChange(this._onRange); } catch (e) { /* 圖已銷毀 */ } }
      if (this._arm) ['pointerdown', 'wheel', 'touchstart'].forEach(ev => this.el.removeEventListener(ev, this._arm));
      clearTimeout(this._noteT);
      this.chart.remove();
    }
  }

  // ---------------------------------------------------------------- 分時走勢
  /* ★ 2026-09-28（Andy：「K線圖新增分時走勢（Default 設定在上面…）」）：個股頁週期列最左邊的「分時」。
     跟 KChart 分開一個類別，因為要回答的問題不一樣 —— K 線回答「這段期間的價格結構」，
     分時只回答「今天（或最近一個交易日）從開盤到現在，比昨天收盤高還是低、往哪邊走」。
     所以：
       · 一條價格線（面積淡填色），顏色看「最後一點 vs 昨收」：高於昨收紅、低於綠、平盤中性色；
       · 昨收一條虛線（價格軸上標「昨收」），而且價格軸**以昨收為中心上下對稱** ——
         線在虛線上面＝今天漲、下面＝跌，不必看數字；
       · 下方分時量柱（紅＝這一分鐘比上一分鐘漲或平、綠＝跌），單位張；
       · 時間軸固定 09:00～13:30：盤中還沒走到的時段留白（不拉伸），一眼看出「現在盤走到哪」；
       · 不給滾輪縮放與拖曳（位置固定，跟熱力圖同一條規矩 —— 拖走了找不回來比看不清楚更糟），只給十字游標讀數。
     輸入：pts ＝ [[時間(epoch+8h 秒，跟 KChart 的分 K 同口徑), 價, 量(股)], ...]、prev ＝ 昨收、date ＝ 那一天。*/
  const SESSION_START = 9 * 60, SESSION_END = 13 * 60 + 30;
  const KUtil_fmt = (t) => fmtTime(t, '1m').slice(11, 16);
  class TickChart {
    constructor(el, opts) {
      this.el = el; this.opts = Object.assign({}, opts);
      const base = baseOptions({ tf: '1m' });
      base.handleScale = false; base.handleScroll = false;
      base.timeScale = Object.assign({}, base.timeScale, { rightOffset: 0, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true });
      base.localization = { locale: 'zh-TW', timeFormatter: (t) => fmtTime(t, '1m').slice(11) };
      base.layout.panes = Object.assign({}, base.layout.panes, { enableResize: false });
      this.chart = LWC.createChart(el, base);
      this.line = this.chart.addSeries(LWC.AreaSeries, this._areaOpts(true), 0);
      m4Fmt(this.line);   // 手機價格軸刻度精簡（見 m4Tick）
      /* 缺口之後的每一段各用一條面積線（this.more）。圖表庫的線會直接跨過空白點連過去（實測 v5.2.1：
         缺口那 19 分鐘明明是空白點，畫面上還是一條斜線從 10:10 拉到 10:30）—— 斷不開就分成好幾條。*/
      this.more = [];
      /* ★ 2026-10-02（DECISIONS #287）右緣錨點：盤中時間軸要固定畫到 13:30（還沒走到的分鐘是空白點），
         但圖表庫把「最後一個有值的點」當右緣 —— 10:30 打開時 fitContent 把 09:00 推到圖中間、10:30 以後整段切掉
         （實測可見範圍 logical -180～90；改用 setVisibleLogicalRange 硬設，一縮放視窗又被拉回去）。
         所以在 13:30 放一個看不見的點：不畫線、不進價格軸、不標價、十字游標不停在它上面，只負責讓右緣＝13:30。
         ⚠ 這以前沒發作是因為缺口一出現 normalize 就把整天當成「不是分鐘資料」照原樣連線（根因 1），根本不補空白格。*/
      this.anchor = this.chart.addSeries(LWC.LineSeries, {
        color: 'rgba(0,0,0,0)', lineVisible: false, pointMarkersVisible: false, priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerVisible: false, autoscaleInfoProvider: () => null,
      }, 0);
      this.vol = this.chart.addSeries(LWC.HistogramSeries, {
        priceLineVisible: false, lastValueVisible: false,
        priceFormat: { type: 'custom', minMove: 1, formatter: (v) => (Math.abs(v) >= 1e7 ? (v / 1e7).toFixed(1) + '萬張' : (v / 1000).toFixed(0) + '張') },
      }, 1);
      try { const ps = this.chart.panes(); if (ps[0] && ps[1]) { ps[0].setStretchFactor(3); ps[1].setStretchFactor(1); } } catch (e) { /* 舊版沒有 stretch，就用預設等高 */ }
      /* ★ 2026-10-02 缺口（DECISIONS #287）：Yahoo 早盤之後、打開頁面之前那段沒有資料。
         主線在那幾分鐘是空白（斷開），另外用一條淡色虛線把缺口兩端連起來、上面標「此段等待資料」——
         看得出「這裡斷了、不是走勢」，又不會讓線突然消失看起來像壞掉。虛線不吃十字游標、不進價格軸。*/
      this.gapLine = this.chart.addSeries(LWC.LineSeries, {
        color: hexa('#8ea0c4', 70), lineWidth: 1, lineStyle: LWC.LineStyle.Dashed, priceLineVisible: false,
        lastValueVisible: false, crosshairMarkerVisible: false, autoscaleInfoProvider: () => null,
      }, 0);
      this.gapTags = [];
      this.wm = document.createElement('div'); this.wm.className = 'k-wm'; el.appendChild(this.wm);
      this._onGapPos = () => this._placeGapTags();
      try { this.chart.timeScale().subscribeSizeChange(this._onGapPos); } catch (e) { /* 舊版沒有，setData 時仍會擺一次 */ }
      /* 容器變寬變窄（手機轉向、拖瀏覽器）時 LWC 的 sizeChange 不一定會叫（實測 1440 → 390 沒叫，小標留在舊座標跑出圖外），
         再掛一個 ResizeObserver，等圖重排完下一幀重擺。*/
      if (window.ResizeObserver) { this._gapRo = new ResizeObserver(() => requestAnimationFrame(this._onGapPos)); this._gapRo.observe(el); }
      this.prevLine = null; this.prev = null; this.pts = []; this.lo = null; this.hi = null; this.gaps = [];
      this.stats = { setData: 0 };
      TickChart.last = this;
    }
    _areaOpts(lastValue) {
      return { lineWidth: 2, priceLineVisible: false, lastValueVisible: !!lastValue, crosshairMarkerRadius: 3,
               autoscaleInfoProvider: () => this._range() };
    }
    // 價格軸：以昨收為中心上下對稱（見類別註解）；沒有昨收就照資料本身的高低
    _range() {
      if (this.lo == null) return null;
      const p = this.prev;
      if (p == null || !(p > 0)) return { priceRange: { minValue: this.lo, maxValue: this.hi } };
      const d = Math.max(Math.abs(this.hi - p), Math.abs(p - this.lo), p * 0.002);
      return { priceRange: { minValue: p - d, maxValue: p + d } };
    }
    /* 把一天的點整理成「每分鐘一點」：中間沒成交的分鐘沿用上一個價（量 0），盤還沒走到的時段補空白格。
       ⚠ 間隔不是 1 分鐘的資料（資料湖 60 分 K 備援那種，一天 6 點）不補分鐘，照原樣連線 ——
         補成 270 格等於把 5 小時畫成同一個價，那是編的。*/
    static normalize(pts, date, live, gaps, minute) {
      const out = [];
      if (!pts.length) return out;
      gaps = gaps || [];
      const inGap = (t) => gaps.some(g => t >= g[0] && t <= g[1]);
      /* minute＝呼叫端明講「這是每分鐘一點」（即時層）。以前只靠「相鄰兩點都不超過 5 分鐘」判斷，
         Yahoo 停在 10:06、報價從 10:26 開始 —— 中間 20 分鐘一空，整天就被當成「不是分鐘資料」照原樣連線，
         10:06 直接一條斜線拉到 10:26。缺口的分鐘另外標出來，不算進判斷。*/
      const minuteLike = minute != null ? !!minute
        : pts.length >= 2 && pts.every((p, i) => i === 0 || p[0] - pts[i - 1][0] <= 5 * 60);
      const day0 = Date.parse(date + 'T00:00:00Z') / 1000;     // 那一天 00:00（epoch+8h 口徑下的「台北牆鐘」）
      const at = (m) => day0 + m * 60;
      if (!minuteLike) return pts.map(p => ({ time: p[0], value: p[1], v: p[2] || 0 }));
      let j = 0, last = null;
      const firstM = Math.max(SESSION_START, Math.floor((pts[0][0] - day0) / 60));
      const lastM = Math.min(SESSION_END, Math.floor((pts[pts.length - 1][0] - day0) / 60));
      for (let m = SESSION_START; m <= SESSION_END; m++) {
        if (m < firstM) { out.push({ time: at(m) }); continue; }
        if (m > lastM) { if (live) { out.push({ time: at(m) }); continue; } break; }
        if (inGap(at(m))) { out.push({ time: at(m), gap: true }); continue; }
        let v = 0, px = null;
        while (j < pts.length && Math.floor((pts[j][0] - day0) / 60) <= m) { px = pts[j][1]; v += pts[j][2] || 0; j++; }
        if (px != null) last = px;
        if (last == null) { out.push({ time: at(m) }); continue; }
        out.push({ time: at(m), value: last, v });
      }
      return out;
    }
    setData(o) {
      const U = C.up, D = C.down, N = C.text;
      this.prev = o.prev != null && o.prev > 0 ? +o.prev : null;
      const rows = TickChart.normalize(o.pts || [], o.date, !!o.live, o.gaps, o.minute);
      this.gaps = (o.gaps || []).slice();
      const vals = rows.filter(r => r.value != null);
      this.pts = vals;
      this.lo = vals.length ? Math.min(...vals.map(r => r.value)) : null;
      this.hi = vals.length ? Math.max(...vals.map(r => r.value)) : null;
      const last = vals.length ? vals[vals.length - 1].value : null;
      const dir = last == null || this.prev == null ? 0 : last > this.prev + 1e-9 ? 1 : last < this.prev - 1e-9 ? -1 : 0;
      const col = dir > 0 ? U : dir < 0 ? D : N;
      this.dir = dir; this.color = col;
      const look = { lineColor: col, topColor: hexa(col.startsWith('#') ? col : '#8ea0c4', 22), bottomColor: hexa(col.startsWith('#') ? col : '#8ea0c4', 2) };
      /* 主線照缺口切段：第一段（含開盤前的空白格）給 this.line，缺口之後每一段各一條（this.more），
         最後一段帶著「還沒走到」的空白格。只有最後一段在價格軸上標最新價。*/
      const pt = (r) => (r.value == null ? { time: r.time } : { time: r.time, value: r.value });
      const chunks = []; let cur = [];
      rows.forEach(r => { if (r.gap) { if (cur.length) { chunks.push(cur); cur = []; } return; } cur.push(r); });
      if (cur.length || !chunks.length) chunks.push(cur);
      while (this.more.length < chunks.length - 1) this.more.push(this.chart.addSeries(LWC.AreaSeries, this._areaOpts(false), 0));
      const lines = [this.line].concat(this.more);
      lines.forEach((ln, i) => {
        ln.applyOptions(Object.assign({ lastValueVisible: i === chunks.length - 1 }, look));
        ln.setData(i < chunks.length ? chunks[i].map(pt) : []);
      });
      this.segCount = chunks.length;
      let pv = this.prev;
      this.vol.setData(rows.map(r => {
        if (r.value == null) return { time: r.time };
        const c = pv == null || r.value >= pv ? U : D; pv = r.value;
        return { time: r.time, value: r.v || 0, color: hexa(c.startsWith('#') ? c : '#8ea0c4', 60) };
      }));
      if (this.prevLine) { try { this.line.removePriceLine(this.prevLine); } catch (e) { /* 已移除 */ } this.prevLine = null; }
      if (this.prev != null) {
        this.prevLine = this.line.createPriceLine({ price: this.prev, color: N, lineWidth: 1, lineStyle: LWC.LineStyle.Dashed, axisLabelVisible: true, title: '昨收' });
      }
      /* 缺口虛線：每個缺口連「缺口前最後一點」到「缺口後第一點」；兩段之間塞空白，不同缺口不要連成一條。
         缺口格式 [起, 迄, 小標文字?, 滑鼠提示?]（epoch+8h，含頭含尾）。
         左邊沒有點可以連的缺口（開盤到第一根，Yahoo 還沒給今天的 K 棒）只標字、不畫虛線 —— 硬從昨收拉一條線過來就是編的。*/
      const gl = [];
      this.gapSegs = [];
      this.gaps.forEach(g => {
        let a = null, b = null;
        for (const r of rows) { if (r.value == null || r.gap) continue; if (r.time < g[0]) a = r; else if (r.time > g[1] && !b) b = r; }
        if (!b) return;
        this.gapSegs.push({ from: a ? a.time : g[0], to: b.time, g, line: !!a });
        if (!a) return;
        /* 斷開前一段：塞一個空白點。⚠ 時間一定要落在既有的分鐘格上（上一段終點 +60 秒）——
           塞一個不在格上的時間（例如 a.time - 1）會讓共用時間軸多出一格，整張圖的間距跟著歪。*/
        if (gl.length) { const pe = gl[gl.length - 1].time + 60; if (pe < a.time) gl.push({ time: pe }); }
        gl.push({ time: a.time, value: a.value }, { time: b.time, value: b.value });
      });
      // 時間要嚴格遞增（兩個缺口中間只隔一根時，前一段終點＝後一段起點，去掉重複那一點）
      this.gapLine.setData(gl.filter((p, i) => i === 0 || p.time > gl[i - 1].time));
      // 右緣錨點（見建構子）：最後一格比最後一個有值的點還晚（盤中），就在最後一格放一個看不見的點
      const tail = rows.length ? rows[rows.length - 1] : null;
      this.anchor.setData(tail && last != null && tail.value == null ? [{ time: tail.time, value: last }] : []);
      this.chart.timeScale().fitContent();
      this.stats.setData++;
      this.rows = rows;
      this._placeGapTags();
      requestAnimationFrame(() => this._placeGapTags());
    }
    /* 「此段等待資料」的缺口標記：斜線底紋蓋住缺口那幾分鐘的價格區，小標置中（可超出底紋、不超出價格區）。
       跟著圖寬重算（subscribeSizeChange＋ResizeObserver）。⚠ 字 11px（手機 390 的下限）。*/
    _placeGapTags() {
      (this.gapTags || []).forEach(t => t.remove()); this.gapTags = [];
      if (this._dead) return;
      if (!this.gapSegs || !this.gapSegs.length) return;
      const ts = this.chart.timeScale();
      let ph = 0; try { ph = this.chart.panes()[0].getHeight(); } catch (e) { /* 舊版沒有 panes()，用 CSS 的 72% */ }
      this.gapSegs.forEach(sg => {
        const x0 = ts.timeToCoordinate(sg.g[0]), x1 = ts.timeToCoordinate(sg.g[1]);
        if (x0 == null || x1 == null) return;
        const tag = document.createElement('div');
        tag.className = 'tk-gap';
        tag.dataset.from = KUtil_fmt(sg.g[0]); tag.dataset.to = KUtil_fmt(sg.g[1]);
        // ★ 2026-10-06（Andy「不要出現這樣廢話」）：滑過只寫一句「HH:MM～HH:MM 尚無資料」，不寫來源與補資料時間
        tag.title = `${tag.dataset.from}～${tag.dataset.to} 尚無資料`;
        if (!sg.line) tag.dataset.lead = '1';
        const left = Math.round(Math.min(x0, x1)), w = Math.max(2, Math.round(Math.abs(x1 - x0)));
        tag.style.left = left + 'px';
        tag.style.width = w + 'px';
        // 底紋只蓋價格區（不蓋到下面的量）：照價格面板實際高度，拿不到才用 CSS 的 72%
        if (ph > 0) tag.style.height = ph + 'px';
        this.el.appendChild(tag);
        this.gapTags.push(tag);
        /* 小標：缺口比字窄（手機上 19 分鐘只有二十幾 px）也照樣標 —— 字塊置中在缺口上、可以超出底紋，
           但夾在價格區左右邊界裡（不蓋到價格軸）。只有 1～2 分鐘那種小斷（< 8px）不放字，免得滿圖都是小標。*/
        // 2026-10-06：斜線上的小標拿掉（斜線本身就是「這段沒資料」的畫面語言），只在呼叫端明確給字時才放
        if (w >= 8 && sg.g[2]) {
          const sp = document.createElement('span'); sp.textContent = sg.g[2]; tag.appendChild(sp);
          let plotW = 0; try { plotW = ts.width(); } catch (e) { plotW = this.el.clientWidth - 60; }
          const sw = sp.offsetWidth;
          const at = Math.max(2, Math.min(left + (w - sw) / 2, plotW - sw - 2));
          sp.style.left = Math.round(at - left) + 'px';
        }
      });
    }
    setWatermark(text) { if (this.wm) this.wm.textContent = text || ''; }
    // 十字游標：回呼拿到「那一分鐘的點」（null＝離開圖，呼叫端改顯示最後一點）
    onCrosshair(fn) {
      if (this._ch) this.chart.unsubscribeCrosshairMove(this._ch);
      this._ch = (p) => {
        if (!p || p.time == null || !p.point) { fn(null); return; }
        const r = (this.rows || []).find(x => x.time === p.time);
        fn(r && r.value != null ? r : null);
      };
      this.chart.subscribeCrosshairMove(this._ch);
    }
    destroy() {
      if (this._ch) { try { this.chart.unsubscribeCrosshairMove(this._ch); } catch (e) { /* 圖已銷毀 */ } }
      try { this.chart.timeScale().unsubscribeSizeChange(this._onGapPos); } catch (e) { /* 圖已銷毀 */ }
      if (this._gapRo) { this._gapRo.disconnect(); this._gapRo = null; }
      this._dead = true;
      (this.gapTags || []).forEach(t => t.remove()); this.gapTags = [];
      if (this.wm && this.wm.parentNode) this.wm.parentNode.removeChild(this.wm);
      this.chart.remove();
      if (TickChart.last === this) TickChart.last = null;
    }
  }

  KChart.LBL_STRIP = 24;          // 設計 v4 2B：副圖標籤帶（標籤 top 3 ＋ 高 18 ＋ 3px 空隙），見 _layoutLabels
  global.KChart = KChart; global.KInd = ind; global.TickChart = TickChart;
  global.KUtil = { resampleDaily, toTime, fmtTime, colors: C, refreshTheme, DRAW_TOOLS, DRAW_COLORS, ZONE_DEF, hexa, hist: HIST };
})(window);
