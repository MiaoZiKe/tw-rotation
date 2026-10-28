/* ============================================================================
   交易練習室：回測引擎（純前端、無 DOM，可在 Web Worker、瀏覽器主執行緒、Node 三處執行）
   2026-10-28 建。口徑重點：
   ① 訊號在「這根收盤」判定，下一根「開盤」成交；停損停利停等盤中觸價成交（見 run()）。不用到未來資料：
      每個策略只讀 index ≤ i 的值，tests/lab_engine_check.js 會把序列截短重算，驗證前綴訊號完全相同。
   ② 指標與 site/chart.js 的 KInd、pipeline/indicators.py 同口徑：
      SMA 滿 n 筆才有值；EMA 以第一筆起頭（pandas ewm adjust=False）；MACD＝DIF／MACD(訊號線)／OSC；
      RSI＝Wilder，前 n 筆變動簡單平均起頭；KD 9,3,3 初始 50；ATR＝Wilder RMA（首根 TR＝高－低）。
   ③ 台股成本：手續費（預設 0.1425%×折扣、單筆最低 20 元）、證交稅（股票 0.3%、ETF 0.1%，只在賣出那一腿）、滑價。
      台指期：每點 200 元、期交稅十萬分之二（買賣各一次）、手續費每口每邊（可調）。
   ④ 全部用「無值＝NaN」；任何比較遇到 NaN 一律為假。
   ============================================================================ */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LabEngine = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const NaNv = NaN;
  const DAY = 86400;

  /* ---------------------------------------------------------------- 資料解碼與週期合成 */
  const pad = (n) => (n < 10 ? '0' : '') + n;
  function dayToStr(d) { const x = new Date(d * DAY * 1000); return x.getUTCFullYear() + '-' + pad(x.getUTCMonth() + 1) + '-' + pad(x.getUTCDate()); }
  function strToDay(s) { return Math.floor(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 86400000); }

  /** pack：build 端 lab.py 的欄位式差分格式 → 逐根陣列。kind：'D'（t＝日數）或 '60'（t＝自 1970 的分鐘數）。 */
  function decode(pack, kind) {
    const n = pack.c.length;
    const B = { n, tf: kind === '60' ? '60' : 'D', ts: new Float64Array(n), day: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) };
    let t = pack.t, c = 0;
    for (let i = 0; i < n; i++) {
      if (i > 0) t += pack.dt[i - 1];
      c += pack.c[i];
      B.c[i] = c / 100; B.o[i] = (c + pack.o[i]) / 100; B.h[i] = (c + pack.h[i]) / 100; B.l[i] = (c + pack.l[i]) / 100; B.v[i] = pack.v[i];
      if (kind === '60') { B.ts[i] = t * 60; B.day[i] = Math.floor((t * 60 + 8 * 3600) / DAY); }
      else { B.ts[i] = t * DAY; B.day[i] = t; }
    }
    B.dayEnd = B.day.slice();
    return B;
  }

  /** 日 K → 週 K（週一起算、以該週第一個交易日標示）／月 K。vol 加總、高低取極值。 */
  function resample(D, mode) {
    if (mode === 'D' || mode === '60') return D;
    const keyOf = (d) => {
      if (mode === 'W') return d - ((d + 3) % 7);                    // 1970-01-01 是星期四：(d+3)%7＝距星期一幾天
      const x = new Date(d * DAY * 1000); return x.getUTCFullYear() * 12 + x.getUTCMonth();
    };
    const idx = []; let last = null;
    for (let i = 0; i < D.n; i++) { const k = keyOf(D.day[i]); if (k !== last) { idx.push([i, i]); last = k; } else idx[idx.length - 1][1] = i; }
    const n = idx.length;
    const B = { n, tf: mode, ts: new Float64Array(n), day: new Float64Array(n), dayEnd: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) };
    for (let k = 0; k < n; k++) {
      const [a, b] = idx[k];
      B.ts[k] = D.ts[a]; B.day[k] = D.day[a]; B.dayEnd[k] = D.day[b];
      B.o[k] = D.o[a]; B.c[k] = D.c[b];
      let hi = -Infinity, lo = Infinity, v = 0;
      for (let i = a; i <= b; i++) { if (D.h[i] > hi) hi = D.h[i]; if (D.l[i] < lo) lo = D.l[i]; v += D.v[i]; }
      B.h[k] = hi; B.l[k] = lo; B.v[k] = v;
    }
    return B;
  }

  const PPY = { D: 252, W: 52, M: 12, '60': 252 * 5 };       // 一年幾根（Sharpe 年化用）

  /* ---------------------------------------------------------------- 指標（與 KInd／indicators.py 同口徑） */
  const I = {
    sma(a, n) { const o = new Float64Array(a.length).fill(NaNv); let s = 0; for (let i = 0; i < a.length; i++) { s += a[i]; if (i >= n) s -= a[i - n]; if (i >= n - 1) o[i] = s / n; } return o; },
    ema(a, n) { const o = new Float64Array(a.length).fill(NaNv); const k = 2 / (n + 1); let e = null; for (let i = 0; i < a.length; i++) { if (Number.isNaN(a[i])) continue; e = e === null ? a[i] : a[i] * k + e * (1 - k); o[i] = e; } return o; },
    boll(c, n, k) { const m = I.sma(c, n), u = new Float64Array(c.length).fill(NaNv), l = new Float64Array(c.length).fill(NaNv); for (let i = 0; i < c.length; i++) { if (Number.isNaN(m[i])) continue; let s = 0; for (let j = i - n + 1; j <= i; j++) s += (c[j] - m[i]) ** 2; const sd = Math.sqrt(s / n); u[i] = m[i] + k * sd; l[i] = m[i] - k * sd; } return { mid: m, up: u, low: l }; },
    macd(c, f, s, g) { const ef = I.ema(c, f), es = I.ema(c, s); const dif = c.map((_, i) => ef[i] - es[i]); const dea = I.ema(dif, g); return { dif, dea, osc: dif.map((v, i) => v - dea[i]) }; },
    rsi(c, n) {
      const o = new Float64Array(c.length).fill(NaNv); let g = 0, l = 0;
      for (let i = 1; i < c.length; i++) {
        const d = c[i] - c[i - 1]; const up = Math.max(d, 0), dn = Math.max(-d, 0);
        if (i <= n) { g += up; l += dn; if (i === n) { g /= n; l /= n; o[i] = (l === 0 && g === 0) ? NaNv : l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
        else { g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n; o[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); }
      }
      return o;
    },
    kd(h, l, c, n, m1, m2) {
      const K = new Float64Array(c.length).fill(NaNv), D = new Float64Array(c.length).fill(NaNv); let k = 50, d = 50;
      for (let i = n - 1; i < c.length; i++) {
        let hh = -Infinity, ll = Infinity; for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, h[j]); ll = Math.min(ll, l[j]); }
        const rsv = hh === ll ? 50 : (c[i] - ll) / (hh - ll) * 100; k = k * (m1 - 1) / m1 + rsv / m1; d = d * (m2 - 1) / m2 + k / m2; K[i] = k; D[i] = d;
      }
      return { k: K, d: D };
    },
    tr(h, l, c) { const o = new Float64Array(c.length); for (let i = 0; i < c.length; i++) o[i] = i === 0 ? h[0] - l[0] : Math.max(h[i] - l[i], Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])); return o; },
    rma(a, n) { const o = new Float64Array(a.length).fill(NaNv); if (a.length < n) return o; let p = 0; for (let i = 0; i < n; i++) p += a[i]; p /= n; o[n - 1] = p; for (let i = n; i < a.length; i++) { p = (p * (n - 1) + a[i]) / n; o[i] = p; } return o; },
    atr(h, l, c, n) { return I.rma(I.tr(h, l, c), n); },
    highest(a, n) { const o = new Float64Array(a.length).fill(NaNv); for (let i = n - 1; i < a.length; i++) { let m = -Infinity; for (let j = i - n + 1; j <= i; j++) if (a[j] > m) m = a[j]; o[i] = m; } return o; },
    lowest(a, n) { const o = new Float64Array(a.length).fill(NaNv); for (let i = n - 1; i < a.length; i++) { let m = Infinity; for (let j = i - n + 1; j <= i; j++) if (a[j] < m) m = a[j]; o[i] = m; } return o; },
    shift(a, n) { const o = new Float64Array(a.length).fill(NaNv); for (let i = n; i < a.length; i++) o[i] = a[i - n]; return o; },
    /** 拋物線 SAR（Wilder）。回傳 {sar, dir}：dir＋1 多頭（SAR 在價下）、－1 空頭。 */
    sar(h, l, start, inc, max) {
      const n = h.length, sar = new Float64Array(n).fill(NaNv), dir = new Float64Array(n).fill(NaNv);
      if (n < 3) return { sar, dir };
      let up = h[1] + l[1] >= h[0] + l[0], af = start;
      let ep = up ? Math.max(h[0], h[1]) : Math.min(l[0], l[1]);
      let s = up ? Math.min(l[0], l[1]) : Math.max(h[0], h[1]);
      sar[1] = s; dir[1] = up ? 1 : -1;
      for (let i = 2; i < n; i++) {
        let ns = s + af * (ep - s);
        if (up) {
          ns = Math.min(ns, l[i - 1], l[i - 2]);
          if (l[i] < ns) { up = false; ns = ep; ep = l[i]; af = start; }
          else if (h[i] > ep) { ep = h[i]; af = Math.min(af + inc, max); }
        } else {
          ns = Math.max(ns, h[i - 1], h[i - 2]);
          if (h[i] > ns) { up = true; ns = ep; ep = h[i]; af = start; }
          else if (l[i] < ep) { ep = l[i]; af = Math.min(af + inc, max); }
        }
        s = ns; sar[i] = s; dir[i] = up ? 1 : -1;
      }
      return { sar, dir };
    },
    /** Supertrend：trend＋1 多（線在價下）、－1 空。 */
    supertrend(h, l, c, n, mult) {
      const len = c.length, a = I.atr(h, l, c, n), tr = new Float64Array(len).fill(NaNv), line = new Float64Array(len).fill(NaNv);
      let fu = NaNv, fl = NaNv, t = 1, started = false;
      for (let i = 0; i < len; i++) {
        if (Number.isNaN(a[i])) continue;
        const hl2 = (h[i] + l[i]) / 2, u = hl2 + mult * a[i], d = hl2 - mult * a[i];
        if (!started) { fu = u; fl = d; t = c[i] >= hl2 ? 1 : -1; started = true; }
        else {
          const pfu = fu, pfl = fl;
          fu = (u < pfu || c[i - 1] > pfu) ? u : pfu;
          fl = (d > pfl || c[i - 1] < pfl) ? d : pfl;
          if (t === 1 && c[i] < fl) t = -1; else if (t === -1 && c[i] > fu) t = 1;
        }
        tr[i] = t; line[i] = t === 1 ? fl : fu;
      }
      return { trend: tr, line };
    },
    cci(h, l, c, n) { const tp = c.map((_, i) => (h[i] + l[i] + c[i]) / 3), m = I.sma(tp, n), o = new Float64Array(c.length).fill(NaNv); for (let i = n - 1; i < c.length; i++) { let md = 0; for (let j = i - n + 1; j <= i; j++) md += Math.abs(tp[j] - m[i]); md /= n; o[i] = md === 0 ? 0 : (tp[i] - m[i]) / (0.015 * md); } return o; },
    willr(h, l, c, n) { const hh = I.highest(h, n), ll = I.lowest(l, n), o = new Float64Array(c.length).fill(NaNv); for (let i = 0; i < c.length; i++) if (!Number.isNaN(hh[i])) o[i] = hh[i] === ll[i] ? -50 : (hh[i] - c[i]) / (hh[i] - ll[i]) * -100; return o; },
  };

  const up = (a, b, i) => i > 0 && a[i] > b[i] && a[i - 1] <= b[i - 1];       // a 上穿 b（NaN 比較為假）
  const dn = (a, b, i) => i > 0 && a[i] < b[i] && a[i - 1] >= b[i - 1];
  const num = (n) => new Float64Array(n);

  /* ---------------------------------------------------------------- 內建策略（對照 TradingView 內建策略清單）
     build(B, p) → {L,S,XL,XS}：Uint8Array，第 i 根「收盤」時的訊號。L／S＝進多／進空；XL／XS＝只平倉不反手。
     opposite 規則在引擎：持多時 S 也會平多；持空時 L 也會平空（可否反手由多空模式決定）。 */
  const mk = (n) => ({ L: new Uint8Array(n), S: new Uint8Array(n), XL: new Uint8Array(n), XS: new Uint8Array(n) });
  const P = (k, label, def, min, max, step) => ({ k, label, def, min, max, step: step || 1 });

  /* 對照 TradingView 內建策略（docs/tradingview_spec.md 第二節）。預設參數與進場方式照規格書；規格書標〔知〕未核實的部分，
     我們採用的定義寫在每支的 desc 與頁面「?」說明裡。台股慣例：KD 用 9,3,3。
     stop 單：price 陣列＝掛單價，只掛一根 K 棒（沒成交就取消）；沒有 tick 加減（台股各價位升降單位不同，省略）。 */
  const stopsOf = (n) => ({ Lp: new Float64Array(n), Sp: new Float64Array(n), Lk: 'stop', Sk: 'stop' });
  const STRATS = [
    { id: 'barupdn', name: 'BarUpDn（漲跌棒）', cat: '價格型態', desc: '收盤高於開盤且開盤高於前收做多；收盤低於開盤且開盤低於前收做空。內建最大日內虧損 1% 出場。', risk: { maxLoss: 1 }, params: [],
      build(B) { const r = mk(B.n); for (let i = 1; i < B.n; i++) { if (B.c[i] > B.o[i] && B.o[i] > B.c[i - 1]) r.L[i] = 1; if (B.c[i] < B.o[i] && B.o[i] < B.c[i - 1]) r.S[i] = 1; } return r; } },
    { id: 'bb', name: '布林通道', cat: '通道', desc: '收盤由下往上穿越下軌做多；由上往下穿越上軌做空（均值回歸）。', params: [P('n', '週期', 20, 5, 120), P('k', '標準差倍數', 2, 0.5, 4, 0.1)],
      build(B, p) { const r = mk(B.n), b = I.boll(B.c, p.n, p.k); for (let i = 1; i < B.n; i++) { if (up(B.c, b.low, i)) r.L[i] = 1; if (dn(B.c, b.up, i)) r.S[i] = 1; } return r; } },
    { id: 'bbdir', name: '布林通道定向', cat: '通道', desc: '價在中線之上且收盤突破上軌做多、跌回中線出場；價在中線之下且跌破下軌做空、站回中線出場。', params: [P('n', '週期', 20, 5, 120), P('k', '標準差倍數', 2, 0.5, 4, 0.1)],
      build(B, p) { const r = mk(B.n), b = I.boll(B.c, p.n, p.k); for (let i = 1; i < B.n; i++) { if (up(B.c, b.up, i)) r.L[i] = 1; if (dn(B.c, b.low, i)) r.S[i] = 1; if (dn(B.c, b.mid, i)) r.XL[i] = 1; if (up(B.c, b.mid, i)) r.XS[i] = 1; } return r; } },
    { id: 'chbo', name: 'ChannelBreakOut（通道突破）', cat: '通道', desc: '每根收盤後，在前 N 根最高價掛停損買單、前 N 根最低價掛停損賣單，下一根碰到就成交（多空互翻）。', params: [P('n', '回看根數', 5, 2, 250)],
      build(B, p) { const r = Object.assign(mk(B.n), stopsOf(B.n)), hh = I.highest(B.h, p.n), ll = I.lowest(B.l, p.n); for (let i = p.n - 1; i < B.n; i++) { r.L[i] = 1; r.S[i] = 1; r.Lp[i] = hh[i]; r.Sp[i] = ll[i]; } return r; } },
    { id: 'pricech', name: 'Price Channel（收盤突破）', cat: '通道', desc: '收盤突破前 N 根最高價做多、跌破前 N 根最低價做空（下一根開盤成交）。', params: [P('n', '回看根數', 20, 3, 250)],
      build(B, p) { const r = mk(B.n), hh = I.highest(B.h, p.n), ll = I.lowest(B.l, p.n); for (let i = p.n; i < B.n; i++) { if (B.c[i] > hh[i - 1]) r.L[i] = 1; if (B.c[i] < ll[i - 1]) r.S[i] = 1; } return r; } },
    { id: 'consec', name: '連續漲跌（Consecutive Up/Down）', cat: '價格型態', desc: '連續 N 根收盤高於前收做多；連續 M 根收盤低於前收做空。', params: [P('n', '連漲根數', 3, 2, 10), P('m', '連跌根數', 3, 2, 10)],
      build(B, p) { const r = mk(B.n); let u = 0, d = 0; for (let i = 1; i < B.n; i++) { u = B.c[i] > B.c[i - 1] ? u + 1 : 0; d = B.c[i] < B.c[i - 1] ? d + 1 : 0; if (u >= p.n) r.L[i] = 1; if (d >= p.m) r.S[i] = 1; } return r; } },
    { id: 'greedy', name: 'Greedy（貪婪，近似版）', cat: '價格型態', desc: '⚠ TradingView 原版邏輯未核實，這是我們的近似版：收陽且收盤突破前一根最高價追多，跌破前一根最低價就跑；收陰且跌破前低追空，站上前高回補。', params: [],
      build(B) { const r = mk(B.n); for (let i = 1; i < B.n; i++) { if (B.c[i] > B.o[i] && B.c[i] > B.h[i - 1]) r.L[i] = 1; if (B.c[i] < B.l[i - 1]) r.XL[i] = 1; if (B.c[i] < B.o[i] && B.c[i] < B.l[i - 1]) r.S[i] = 1; if (B.c[i] > B.h[i - 1]) r.XS[i] = 1; } return r; } },
    { id: 'inside', name: 'InSide Bar（內包棒）', cat: '價格型態', desc: '這根是被前一根完全包住的內包棒（高低都在前一根之內）時，收紅做多、收黑做空。', params: [],
      build(B) { const r = mk(B.n); for (let i = 1; i < B.n; i++) { if (B.h[i] < B.h[i - 1] && B.l[i] > B.l[i - 1]) { if (B.c[i] > B.o[i]) r.L[i] = 1; else if (B.c[i] < B.o[i]) r.S[i] = 1; } } return r; } },
    { id: 'outside', name: 'OutSide Bar（外包棒）', cat: '價格型態', desc: '這根完全包住前一根（高更高、低更低）時，收紅做多、收黑做空。', params: [],
      build(B) { const r = mk(B.n); for (let i = 1; i < B.n; i++) { if (B.h[i] > B.h[i - 1] && B.l[i] < B.l[i - 1]) { if (B.c[i] > B.o[i]) r.L[i] = 1; else if (B.c[i] < B.o[i]) r.S[i] = 1; } } return r; } },
    { id: 'keltner', name: 'Keltner 通道', cat: '通道', desc: '每根收盤後，在 EMA＋倍數×平均真實區間 的上軌掛停損買單、下軌掛停損賣單（下一根碰到成交）。', params: [P('n', '週期', 20, 5, 120), P('m', '倍數', 1, 0.5, 5, 0.1)],
      build(B, p) { const r = Object.assign(mk(B.n), stopsOf(B.n)), m = I.ema(B.c, p.n), a = I.atr(B.h, B.l, B.c, p.n); for (let i = 0; i < B.n; i++) { if (Number.isNaN(a[i])) continue; r.L[i] = 1; r.S[i] = 1; r.Lp[i] = m[i] + p.m * a[i]; r.Sp[i] = m[i] - p.m * a[i]; } return r; } },
    { id: 'macd', name: 'MACD', cat: '動能', desc: '柱狀體（DIF 減 MACD）由負轉正做多，由正轉負做空。', params: [P('f', '快線', 12, 2, 60), P('s', '慢線', 26, 5, 120), P('g', '訊號線', 9, 2, 30)],
      build(B, p) { const r = mk(B.n), m = I.macd(B.c, p.f, p.s, p.g); for (let i = 1; i < B.n; i++) { if (m.osc[i] > 0 && m.osc[i - 1] <= 0) r.L[i] = 1; if (m.osc[i] < 0 && m.osc[i - 1] >= 0) r.S[i] = 1; } return r; } },
    { id: 'mom', name: '動能（Momentum）', cat: '動能', desc: '動量（收盤減 N 根前收盤）及其一階變化都為正，掛停損買單於當根最高；都為負，掛停損賣單於當根最低。', params: [P('n', '週期', 12, 2, 120)],
      build(B, p) { const r = Object.assign(mk(B.n), stopsOf(B.n)); for (let i = p.n + 1; i < B.n; i++) { const m0 = B.c[i] - B.c[i - p.n], m1 = B.c[i - 1] - B.c[i - 1 - p.n]; if (m0 > 0 && m0 - m1 > 0) { r.L[i] = 1; r.Lp[i] = B.h[i]; } if (m0 < 0 && m0 - m1 < 0) { r.S[i] = 1; r.Sp[i] = B.l[i]; } } return r; } },
    { id: 'ma2', name: '雙均線交叉', cat: '趨勢', desc: '短均線上穿長均線做多，下穿做空。', params: [P('f', '短均線', 9, 2, 120), P('s', '長均線', 18, 5, 250)],
      build(B, p) { const r = mk(B.n), a = I.sma(B.c, p.f), b = I.sma(B.c, p.s); for (let i = 1; i < B.n; i++) { if (up(a, b, i)) r.L[i] = 1; if (dn(a, b, i)) r.S[i] = 1; } return r; } },
    { id: 'ma1', name: '均線交叉', cat: '趨勢', desc: '收盤上穿均線（連續 N 根確認）做多，下穿做空。', params: [P('n', '均線週期', 9, 3, 250), P('k', '確認根數', 1, 1, 5)],
      build(B, p) { const r = mk(B.n), a = I.sma(B.c, p.n); for (let i = p.k; i < B.n; i++) { let u = true, d = true; for (let j = 0; j < p.k; j++) { if (!(B.c[i - j] > a[i - j])) u = false; if (!(B.c[i - j] < a[i - j])) d = false; } if (Number.isNaN(a[i - p.k])) continue; if (u && !(B.c[i - p.k] > a[i - p.k])) r.L[i] = 1; if (d && !(B.c[i - p.k] < a[i - p.k])) r.S[i] = 1; } return r; } },
    { id: 'sar', name: 'Parabolic SAR', cat: '趨勢', desc: '價格翻到 SAR 點之上做多，翻到 SAR 點之下做空（停損反轉；簡化為翻轉當根收盤確認、下一根開盤成交）。', params: [P('s', '起始加速', 0.02, 0.005, 0.1, 0.005), P('i', '加速增量', 0.02, 0.005, 0.1, 0.005), P('m', '加速上限', 0.2, 0.05, 0.5, 0.05)],
      build(B, p) { const r = mk(B.n), s = I.sar(B.h, B.l, p.s, p.i, p.m); for (let i = 2; i < B.n; i++) { if (s.dir[i] === 1 && s.dir[i - 1] === -1) r.L[i] = 1; if (s.dir[i] === -1 && s.dir[i - 1] === 1) r.S[i] = 1; } return r; } },
    { id: 'pivrev', name: 'Pivot Reversal（樞紐反轉）', cat: '價格型態', desc: '出現樞紐高點（左右各 N 根都比它低）後，在該高點掛停損買單，直到被碰到；樞紐低點則掛停損賣單。', params: [P('l', '左側根數', 4, 1, 20), P('r', '右側根數', 2, 1, 10)],
      build(B, p) {
        const r = Object.assign(mk(B.n), stopsOf(B.n)); let le = false, se = false, hp = 0, lp = 0;
        for (let i = p.l + p.r; i < B.n; i++) {
          const k = i - p.r; let isH = true, isL = true;
          for (let j = k - p.l; j <= k + p.r; j++) { if (j === k) continue; if (B.h[j] >= B.h[k]) isH = false; if (B.l[j] <= B.l[k]) isL = false; }
          if (isH) { hp = B.h[k]; le = true; } else if (le && B.h[i] > hp) le = false;
          if (isL) { lp = B.l[k]; se = true; } else if (se && B.l[i] < lp) se = false;
          if (le) { r.L[i] = 1; r.Lp[i] = hp; } if (se) { r.S[i] = 1; r.Sp[i] = lp; }
        }
        return r;
      } },
    { id: 'pivext', name: 'Pivot Extension（樞紐延伸）', cat: '價格型態', desc: '確認出現樞紐低點（左右各 N 根都比它高）→ 做多；確認樞紐高點 → 做空（下一根開盤成交，確認時已過了右側 N 根）。', params: [P('l', '左側根數', 4, 1, 20), P('r', '右側根數', 2, 1, 10)],
      build(B, p) {
        const r = mk(B.n);
        for (let i = p.l + p.r; i < B.n; i++) {
          const k = i - p.r; let isH = true, isL = true;
          for (let j = k - p.l; j <= k + p.r; j++) { if (j === k) continue; if (B.h[j] >= B.h[k]) isH = false; if (B.l[j] <= B.l[k]) isL = false; }
          if (isL) r.L[i] = 1; if (isH) r.S[i] = 1;
        }
        return r;
      } },
    { id: 'rsi', name: 'RSI', cat: '動能', desc: 'RSI 由下往上穿越超賣線做多，由上往下穿越超買線做空（逆勢）。', params: [P('n', '週期', 14, 2, 60), P('lo', '超賣', 30, 5, 50), P('hi', '超買', 70, 50, 95)],
      build(B, p) { const r = mk(B.n), x = I.rsi(B.c, p.n); for (let i = 1; i < B.n; i++) { if (x[i] > p.lo && x[i - 1] <= p.lo) r.L[i] = 1; if (x[i] < p.hi && x[i - 1] >= p.hi) r.S[i] = 1; } return r; } },
    { id: 'supertrend', name: 'Supertrend', cat: '趨勢', desc: '收盤翻到 Supertrend 線之上做多，翻到線之下做空。', params: [P('n', 'ATR 週期', 10, 3, 60), P('m', 'ATR 倍數', 3, 0.5, 8, 0.1)],
      build(B, p) { const r = mk(B.n), s = I.supertrend(B.h, B.l, B.c, p.n, p.m); for (let i = 1; i < B.n; i++) { if (s.trend[i] === 1 && s.trend[i - 1] === -1) r.L[i] = 1; if (s.trend[i] === -1 && s.trend[i - 1] === 1) r.S[i] = 1; } return r; } },
    { id: 'kd', name: 'Stochastic Slow（KD）', cat: '動能', desc: 'K 由下往上穿越 D 且 K 低於超賣線做多；K 由上往下穿越 D 且 K 高於超買線做空。台股慣例 KD 9,3,3（初始 50）。', params: [P('n', 'KD 週期', 9, 3, 60), P('lo', '超賣', 20, 5, 50), P('hi', '超買', 80, 50, 95)],
      build(B, p) { const r = mk(B.n), k = I.kd(B.h, B.l, B.c, p.n, 3, 3); for (let i = 1; i < B.n; i++) { if (up(k.k, k.d, i) && k.k[i] < p.lo) r.L[i] = 1; if (dn(k.k, k.d, i) && k.k[i] > p.hi) r.S[i] = 1; } return r; } },
    { id: 'volty', name: 'Volty Expan Close（波動擴張）', cat: '通道', desc: '每根收盤後，在 收盤＋N 倍平均真實區間 掛停損買單、收盤－N 倍掛停損賣單（下一根碰到成交）。', params: [P('n', '週期', 5, 2, 60), P('m', '倍數', 0.75, 0.25, 3, 0.05)],
      build(B, p) { const r = Object.assign(mk(B.n), stopsOf(B.n)), a = I.sma(I.tr(B.h, B.l, B.c), p.n); for (let i = 0; i < B.n; i++) { if (Number.isNaN(a[i])) continue; r.L[i] = 1; r.S[i] = 1; r.Lp[i] = B.c[i] + p.m * a[i]; r.Sp[i] = B.c[i] - p.m * a[i]; } return r; } },
    { id: 'cci', name: 'CCI', cat: '動能', desc: 'CCI 由下往上穿越 －100 做多，由上往下穿越 ＋100 做空。', params: [P('n', '週期', 20, 5, 100), P('t', '門檻', 100, 50, 200, 10)],
      build(B, p) { const r = mk(B.n), x = I.cci(B.h, B.l, B.c, p.n); for (let i = 1; i < B.n; i++) { if (x[i] > -p.t && x[i - 1] <= -p.t) r.L[i] = 1; if (x[i] < p.t && x[i - 1] >= p.t) r.S[i] = 1; } return r; } },
    { id: 'willr', name: '威廉指標 %R', cat: '動能', desc: '%R 由下往上穿越 －80 做多，由上往下穿越 －20 做空。', params: [P('n', '週期', 14, 5, 60)],
      build(B, p) { const r = mk(B.n), x = I.willr(B.h, B.l, B.c, p.n); for (let i = 1; i < B.n; i++) { if (x[i] > -80 && x[i - 1] <= -80) r.L[i] = 1; if (x[i] < -20 && x[i - 1] >= -20) r.S[i] = 1; } return r; } },
    { id: 'trio', name: '均線多頭排列', cat: '趨勢', desc: '短、中、長三條均線多頭排列（短在長上）且收盤在中均線之上做多，排列破壞出場；不做空。', params: [P('a', '短', 5, 2, 30), P('b', '中', 20, 5, 120), P('c', '長', 60, 20, 250)],
      build(B, p) { const r = mk(B.n), a = I.sma(B.c, p.a), b = I.sma(B.c, p.b), c = I.sma(B.c, p.c); let on = false; for (let i = 0; i < B.n; i++) { const ok = a[i] > b[i] && b[i] > c[i] && B.c[i] > b[i]; if (ok && !on) r.L[i] = 1; if (!ok && on) r.XL[i] = 1; on = ok; } return r; } },
    { id: 'bnh', name: '買進持有', cat: '基準', desc: '第一根進場後一路持有，用來對照其他策略有沒有贏過單純持有。', params: [],
      build(B) { const r = mk(B.n); if (B.n) r.L[0] = 1; return r; } },
  ];
  const STRAT = {}; STRATS.forEach((s) => { STRAT[s.id] = s; });
  function defaults(id) { const o = {}; ((STRAT[id] || {}).params || []).forEach((q) => { o[q.k] = q.def; }); return o; }

  /* ---------------------------------------------------------------- 商品與成本設定 */
  /** 各種標的的預設成本。fee 單位％；slip：股票為％、台指期為點。 */
  function instDefaults(kind) {
    if (kind === 'fut') return { kind: 'fut', mult: 200, futFee: 40, futTax: 0.002, slip: 1, feeMin: 0, feeRate: 0, feeDisc: 1, taxRate: 0 };
    return { kind, mult: 1, futFee: 0, futTax: 0, slip: 0.05, feeMin: 20, feeRate: 0.1425, feeDisc: 1, taxRate: kind === 'stock' ? 0.3 : 0.1 };
  }

  /* ---------------------------------------------------------------- 回測主迴圈 */
  /**
   * run(B, sig, cfg, from, to)
   * cfg：{ mode:'long'|'short'|'both', capital, sizeMode:'pct'|'amount'|'units', sizeVal, pyramiding（同方向最多幾口，預設 1）,
   *        fillOn:'open'（預設，下一根開盤）|'close'（訊號當根收盤）, inst, sl, tp, trail, maxLoss（皆為 %，0＝關）, entryMask, exitMask }
   * sig：{L,S,XL,XS}，另可帶 Lp／Sp（Float64Array 價格）與 Lk／Sk（'stop'｜'limit'）＝做多／做空改用停損單或限價單進場，只掛一根 K 棒，沒成交就取消。
   * 每一口（lot）各自一筆交易紀錄。回傳 { trades, open（未平倉的各口）, eq, bh, stats, from, to }
   *
   * 盤中順序（只有 OHLC 時的假設，與 TradingView 預設相同）：開盤離最高較近 → 開→高→低→收；否則 開→低→高→收。
   * 同一根同時碰到停損與停利時照這個路徑決定誰先；跳空越過價位則以開盤價成交。
   */
  function run(B, sig, cfg, from, to) {
    const n = B.n; from = from == null ? 0 : Math.max(0, from); to = to == null ? n - 1 : Math.min(n - 1, to);
    const inst = cfg.inst, fut = inst.kind === 'fut', mult = inst.mult;
    const longOK = cfg.mode !== 'short', shortOK = cfg.mode !== 'long';
    const pyr = Math.max(1, cfg.pyramiding || 1);
    const feeEff = (inst.feeRate / 100) * inst.feeDisc;
    const slipOf = (p) => (fut ? inst.slip : p * inst.slip / 100);
    const fee = (notional, qty) => (fut ? inst.futFee * qty : Math.max(inst.feeMin, notional * feeEff));
    const tax = (notional, isSell) => (fut ? notional * inst.futTax / 100 : (isSell ? notional * inst.taxRate / 100 : 0));

    let cash = cfg.capital, pos = 0, lots = [], eqPrev = cfg.capital;
    const trades = [], eq = new Float64Array(to - from + 1), bh = new Float64Array(to - from + 1);
    const o0 = B.o[from];
    const equityAt = (c) => { let e = cash; for (const L of lots) e += fut ? pos * L.q * mult * (c - L.p) : pos * L.q * c; return e; };

    function openLot(i, dir, raw, why, mid) {
      const p = dir === 1 ? raw + slipOf(raw) : raw - slipOf(raw);
      const equity = equityAt(raw);
      let q;
      if (cfg.sizeMode === 'units') q = Math.floor(cfg.sizeVal);
      else {
        const budget = cfg.sizeMode === 'amount' ? cfg.sizeVal : equity * cfg.sizeVal / 100;
        q = fut ? Math.floor(budget / (p * mult)) : Math.floor(Math.min(budget, cash) / (p * (1 + feeEff)));
      }
      if (q < 1 || equity <= 0) return false;
      const f = fee(p * q * mult, q), t = tax(p * q * mult, dir === -1);
      if (fut) cash -= f + t; else if (dir === 1) cash -= p * q + f; else cash += p * q - f - t;
      pos = dir;
      lots.push({ q, p, i0: i, fee: f, tax: t, ext: p, mfe: 0, mae: 0, why, mid: !!mid });
      maxQ = Math.max(maxQ, lots.reduce((a, x) => a + x.q, 0));
      return true;
    }
    function closeLot(L, i, raw, why) {
      const p = pos === 1 ? raw - slipOf(raw) : raw + slipOf(raw);
      const exFee = fee(p * L.q * mult, L.q), exTax = tax(p * L.q * mult, pos === 1);
      const gross = pos * (p - L.p) * L.q * mult;
      if (fut) cash += gross - exFee - exTax; else if (pos === 1) cash += p * L.q - exFee - exTax; else cash -= p * L.q + exFee;
      const costs = L.fee + L.tax + exFee + exTax, notional = L.p * L.q * mult;
      trades.push({ dir: pos, i0: L.i0, i1: i, p0: L.p, p1: p, qty: L.q, gross, costs, pnl: gross - costs, pnlP: (gross - costs) / notional * 100, bars: i - L.i0, mfe: L.mfe * L.q * mult, mae: L.mae * L.q * mult, mfeP: L.mfe / L.p * 100, maeP: L.mae / L.p * 100, why, entryWhy: L.why, open: false, notional });
    }
    function closeAll(i, raw, why) { for (const L of lots) closeLot(L, i, raw, why); lots = []; pos = 0; }

    let maxQ = 0;
    let pend = [];   // 前一根收盤決定的單：{dir（1／－1／0＝全平）, kind:'mkt'|'stop'|'limit', price, why}
    function execPending(i, o, h, l) {
      let ocaDone = false;
      // 多空同掛的兩張停損單：開盤已越過價位的先成交；都沒跳空就依盤中路徑（開盤離高點較近 → 先碰買停）
      if (pend.length === 2 && pend[0].oca) {
        const gapBuy = o >= pend[0].price, gapSell = o <= pend[1].price;
        const buyFirst = gapBuy && !gapSell ? true : gapSell && !gapBuy ? false : Math.abs(o - h) < Math.abs(o - l);
        if (!buyFirst) pend = [pend[1], pend[0]];
      }
      for (const od of pend) {
        if (od.oca && ocaDone) continue;      // 多空同時掛單（通道突破）：同一根只成交先碰到的那一邊
        if (od.dir === 0) { if (pos !== 0) closeAll(i, o, od.why); continue; }
        let fill = NaN, mid = false;
        if (od.kind === 'mkt') fill = o;
        else if (od.kind === 'stop') { if (od.dir === 1 ? h >= od.price : l <= od.price) { fill = od.dir === 1 ? Math.max(o, od.price) : Math.min(o, od.price); mid = fill !== o; } }
        else if (od.dir === 1 ? l <= od.price : h >= od.price) { fill = od.dir === 1 ? Math.min(o, od.price) : Math.max(o, od.price); mid = fill !== o; }
        if (Number.isNaN(fill)) continue;
        if (pos === -od.dir) closeAll(i, o, od.why);
        if (pos === 0 || (pos === od.dir && lots.length < pyr)) { if (openLot(i, od.dir, fill, od.why, mid) && od.oca) ocaDone = true; }
      }
      pend = [];
    }
    /** 盤中保護單。回傳這一根後還剩的口。 */
    function protect(i, o, h, l) {
      if (!lots.length) return;
      const d = pos, hiFirst = Math.abs(o - h) < Math.abs(o - l);
      const favFirst = d === 1 ? hiFirst : !hiFirst;
      const keep = [];
      for (const L of lots) {
        const fresh = L.i0 === i;
        if (L.mid) { L.mid = false; L.ext = d === 1 ? Math.max(L.ext, h) : Math.min(L.ext, l); keep.push(L); continue; }   // 盤中才成交的口，這一根不套保護單（高低順序未知）
        const ref = fresh ? L.p : B.c[i - 1];
        // 有利方向的極值（移動停損用）：路徑先有利才算入這一根
        const extNow = favFirst ? (d === 1 ? Math.max(L.ext, h) : Math.min(L.ext, l)) : L.ext;
        let lvl = d === 1 ? -Infinity : Infinity, why = '';
        const cand = (v, w) => { if (d === 1 ? v > lvl : v < lvl) { lvl = v; why = w; } };
        if (cfg.sl > 0) cand(L.p * (1 - d * cfg.sl / 100), '停損');
        if (cfg.trail > 0) cand(extNow * (1 - d * cfg.trail / 100), '移動停損');
        // 最大日內虧損：以前一根收盤（進場那根以成交價）為基準，這一根持倉虧掉前一根收盤權益的 maxLoss% 就出場
        if (cfg.maxLoss > 0) cand(ref - d * (cfg.maxLoss / 100 * eqPrev) / (L.q * mult), 'Close Position (Max intraday Loss)');
        const tl = cfg.tp > 0 ? L.p * (1 + d * cfg.tp / 100) : NaN;
        const advHit = why && (d === 1 ? l <= lvl : h >= lvl), tpHit = cfg.tp > 0 && (d === 1 ? h >= tl : l <= tl);
        const gapAdv = advHit && !fresh && (d === 1 ? o <= lvl : o >= lvl), gapTp = tpHit && !fresh && (d === 1 ? o >= tl : o <= tl);
        let act = null;
        if (advHit && tpHit) act = gapAdv ? 'adv' : gapTp ? 'tp' : (favFirst ? 'tp' : 'adv');
        else if (advHit) act = 'adv'; else if (tpHit) act = 'tp';
        if (act === 'adv') {
          const px = gapAdv ? o : lvl;
          L.mae = Math.max(L.mae, d === 1 ? L.p - px : px - L.p);
          if (favFirst) L.mfe = Math.max(L.mfe, d === 1 ? h - L.p : L.p - l);
          closeLot(L, i, px, why);
        } else if (act === 'tp') {
          const px = gapTp ? o : tl;
          L.mfe = Math.max(L.mfe, d === 1 ? px - L.p : L.p - px);
          if (!advHit) L.mae = Math.max(L.mae, d === 1 ? L.p - l : h - L.p);
          closeLot(L, i, px, '停利');
        } else {
          L.mfe = Math.max(L.mfe, d === 1 ? h - L.p : L.p - l); L.mae = Math.max(L.mae, d === 1 ? L.p - l : h - L.p);
          L.ext = d === 1 ? Math.max(L.ext, h) : Math.min(L.ext, l);
          keep.push(L);
        }
      }
      lots = keep; if (!lots.length) pos = 0;
    }
    function decide(i) {
      const ok = !cfg.entryMask || cfg.entryMask[i] !== 0;
      const out = [];
      const ord = (dir, why) => {
        const k = dir === 1 ? sig.Lk : sig.Sk, pr = dir === 1 ? sig.Lp : sig.Sp;
        if (k && pr && pr[i] > 0 && cfg.fillOn !== 'close') out.push({ dir, kind: k, price: pr[i], why });
        else out.push({ dir, kind: 'mkt', price: 0, why });
      };
      if (pos === 0) {
        const bothStops = sig.L[i] && sig.S[i] && longOK && shortOK && ok && sig.Lk && sig.Sk && sig.Lp && sig.Sp && sig.Lp[i] > 0 && sig.Sp[i] > 0 && cfg.fillOn !== 'close';
        if (bothStops) {
          // 開盤跳空時看哪一邊被先碰到：比較開盤價離哪個掛單價較近的交給 execPending 依序處理，這裡把離上一根收盤較近者放前面
          out.push({ dir: 1, kind: sig.Lk, price: sig.Lp[i], why: '做多訊號', oca: true }, { dir: -1, kind: sig.Sk, price: sig.Sp[i], why: '做空訊號', oca: true });
        } else if (sig.L[i] && longOK && ok) ord(1, '做多訊號'); else if (sig.S[i] && shortOK && ok) ord(-1, '做空訊號');
      } else if (pos === 1) {
        if (sig.S[i]) { if (shortOK && ok) ord(-1, '反向訊號'); else out.push({ dir: 0, kind: 'mkt', price: 0, why: '反向訊號' }); }
        else if (sig.XL[i]) out.push({ dir: 0, kind: 'mkt', price: 0, why: '出場訊號' });
        else if (sig.L[i] && longOK && ok && lots.length < pyr) ord(1, '加碼訊號');
      } else if (sig.L[i]) { if (longOK && ok) ord(1, '反向訊號'); else out.push({ dir: 0, kind: 'mkt', price: 0, why: '反向訊號' }); }
      else if (sig.XS[i]) out.push({ dir: 0, kind: 'mkt', price: 0, why: '出場訊號' });
      else if (sig.S[i] && shortOK && ok && lots.length < pyr) ord(-1, '加碼訊號');
      if (pos !== 0 && cfg.maxBars > 0 && i - lots[0].i0 >= cfg.maxBars) { out.length = 0; out.push({ dir: 0, kind: 'mkt', price: 0, why: '持有逾時' }); }    // 最長持有 N 根
      if (pos !== 0 && cfg.exitMask && cfg.exitMask[i]) { out.length = 0; out.push({ dir: 0, kind: 'mkt', price: 0, why: '事件出場' }); }
      return out;
    }

    for (let i = from; i <= to; i++) {
      const o = B.o[i], h = B.h[i], l = B.l[i], c = B.c[i];
      execPending(i, o, h, l);
      protect(i, o, h, l);
      if (cfg.fillOn === 'close') { pend = decide(i); execPending(i, c, c, c); }      // 收盤即成交：訊號當根收盤價
      const e = equityAt(c);
      eq[i - from] = e; eqPrev = e;
      bh[i - from] = fut ? cfg.capital + (c - o0) * mult * (cfg.sizeMode === 'units' ? cfg.sizeVal : 1) : cfg.capital * c / o0;
      if (i < to && cfg.fillOn !== 'close') pend = decide(i);
    }
    // 區間結束仍有部位：不強制平倉，列為「未平倉」（損益含在淨損益，不進勝率等已平倉統計）
    const openT = lots.map((L) => {
      const c = B.c[to], gross = pos * (c - L.p) * L.q * mult;
      return { dir: pos, i0: L.i0, i1: to, p0: L.p, p1: c, qty: L.q, gross, costs: L.fee + L.tax, pnl: gross - L.fee - L.tax, pnlP: (gross - L.fee - L.tax) / (L.p * L.q * mult) * 100, bars: to - L.i0, mfe: L.mfe * L.q * mult, mae: L.mae * L.q * mult, mfeP: L.mfe / L.p * 100, maeP: L.mae / L.p * 100, why: '未平倉', entryWhy: L.why, open: true, notional: L.p * L.q * mult };
    });
    trades.sort((a, b) => a.i1 - b.i1 || a.i0 - b.i0);
    const stats = computeStats(B, trades, eq, cfg, from, to, openT, maxQ);
    return { trades, open: openT.length ? openT[0] : null, opens: openT, eq, bh, stats, from, to };
  }

  /** 單一方向（0＝全部、1＝多、－1＝空）的績效摘要，欄位對照 TradingView 的 Performance Summary。 */
  function summary(trades, opens, dir, cap) {
    const T = trades.filter((t) => !dir || t.dir === dir), O = opens.filter((t) => !dir || t.dir === dir);
    const wins = T.filter((t) => t.pnl > 0), loss = T.filter((t) => t.pnl < 0), even = T.length - wins.length - loss.length;
    const gp = wins.reduce((a, t) => a + t.pnl, 0), gl = -loss.reduce((a, t) => a + t.pnl, 0);
    const avg = (a, f) => (a.length ? a.reduce((s, t) => s + f(t), 0) / a.length : null);
    const avgW = wins.length ? gp / wins.length : null, avgL = loss.length ? gl / loss.length : null;
    const big = (a, sgnv) => (a.length ? a.reduce((m, t) => (sgnv * t.pnl > sgnv * m.pnl ? t : m), a[0]) : null);
    const bw = big(wins, 1), bl = big(loss, -1);
    return {
      net: gp - gl, netP: (gp - gl) / cap * 100, gp, gl, nClosed: T.length, nOpen: O.length, nWin: wins.length, nLoss: loss.length, nEven: even,
      win: T.length ? wins.length / T.length * 100 : null,
      pf: gl > 0 ? gp / gl : (gp > 0 ? Infinity : null),
      avgTrade: T.length ? (gp - gl) / T.length : null, avgTradeP: avg(T, (t) => t.pnlP),
      avgW, avgL, avgWP: avg(wins, (t) => t.pnlP), avgLP: avg(loss, (t) => t.pnlP), rr: avgL ? avgW / avgL : (avgW ? Infinity : null),
      bigW: bw ? bw.pnl : null, bigWP: bw ? bw.pnlP : null, bigL: bl ? bl.pnl : null, bigLP: bl ? bl.pnlP : null,
      barsAll: avg(T, (t) => t.bars), barsW: avg(wins, (t) => t.bars), barsL: avg(loss, (t) => t.bars),
      openPL: O.reduce((a, t) => a + t.pnl, 0), comm: T.reduce((a, t) => a + t.costs, 0) + O.reduce((a, t) => a + t.costs, 0),
      maxLots: 0,
    };
  }

  /** 月報酬序列（取每個日曆月最後一根的權益）。第一個月以初始資金為基準。 */
  function monthlyReturns(B, eq, from, cap) {
    const out = []; let prev = cap, lastKey = null, lastEq = cap;
    for (let i = 0; i < eq.length; i++) {
      const d = new Date(B.dayEnd[from + i] * DAY * 1000), k = d.getUTCFullYear() * 12 + d.getUTCMonth();
      if (lastKey !== null && k !== lastKey) { out.push(lastEq / prev - 1); prev = lastEq; }
      lastKey = k; lastEq = eq[i];
    }
    if (lastKey !== null) out.push(lastEq / prev - 1);
    return out;
  }
  const RF = 0.02;   // 無風險利率（年化）。TradingView 的預設口徑未核實，我們採 2%，寫在畫面說明裡

  function computeStats(B, trades, eq, cfg, from, to, opens, maxQ) {
    const cap = cfg.capital, last = eq.length ? eq[eq.length - 1] : cap;
    let cum = 0; trades.forEach((t) => { cum += t.pnl; t.cum = cum; });
    opens.forEach((t) => { t.cum = cum + t.pnl; });
    const all = summary(trades, opens, 0, cap), lg = summary(trades, opens, 1, cap), sh = summary(trades, opens, -1, cap);
    let peak = cap, mdd = 0, mddP = 0, trough = cap, ru = 0, ruP = 0;
    const dd = new Float64Array(eq.length);
    for (let i = 0; i < eq.length; i++) {
      if (eq[i] > peak) peak = eq[i]; const d = peak - eq[i]; dd[i] = peak > 0 ? -d / peak * 100 : 0; if (d > mdd) mdd = d; const dp = peak > 0 ? d / peak : 0; if (dp > mddP) mddP = dp;
      if (eq[i] < trough) trough = eq[i]; const r = eq[i] - trough; if (r > ru) ru = r; const rp = trough > 0 ? r / trough : 0; if (rp > ruP) ruP = rp;
    }
    const mr = monthlyReturns(B, eq, from, cap);
    const mean = mr.reduce((a, b) => a + b, 0) / (mr.length || 1), rfm = RF / 12;
    const sd = Math.sqrt(mr.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, mr.length - 1));
    const dsd = Math.sqrt(mr.reduce((a, b) => a + Math.min(0, b - rfm) ** 2, 0) / (mr.length || 1));
    const sharpe = mr.length >= 3 && sd > 0 ? (mean - rfm) / sd * Math.sqrt(12) : null;
    const sortino = mr.length >= 3 && dsd > 0 ? (mean - rfm) / dsd * Math.sqrt(12) : null;
    const days = trades.length ? trades.reduce((a, t) => a + (B.day[Math.min(t.i1, B.n - 1)] - B.day[t.i0]), 0) / trades.length : 0;
    const fut = cfg.inst.kind === 'fut';
    return Object.assign({}, all, {
      all, long: lg, short: sh, ret: (last / cap - 1) * 100, final: last, net: last - cap, mdd, mddP: mddP * 100, runup: ru, runupP: ruP * 100,
      n: all.nClosed, avgBars: all.barsAll || 0, avgDays: days, sharpe, sortino, months: mr.length,
      bhRet: eq.length ? (fut ? (B.c[to] - B.o[from]) * cfg.inst.mult * (cfg.sizeMode === 'units' ? cfg.sizeVal : 1) / cap * 100 : (B.c[to] / B.o[from] - 1) * 100) : 0,
      bhNet: eq.length ? (fut ? (B.c[to] - B.o[from]) * cfg.inst.mult * (cfg.sizeMode === 'units' ? cfg.sizeVal : 1) : cap * (B.c[to] / B.o[from] - 1)) : 0,
      costs: all.comm, hasOpen: opens.length > 0, dd, maxLots: maxQ || 0,
    });
  }

  /* ---------------------------------------------------------------- 區間、事件遮罩 */
  /** 期間鈕 → 起始 index。key：1M 3M 6M YTD 1Y 5Y All（以最後一根的日期往前推）。 */
  function rangeFrom(B, key) {
    if (!B.n || key === 'All') return 0;
    const last = B.dayEnd[B.n - 1], x = new Date(last * DAY * 1000);
    let cut;
    if (key === 'YTD') cut = Math.floor(Date.UTC(x.getUTCFullYear(), 0, 1) / 86400000);
    else { const m = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12, '5Y': 60 }[key]; const d = new Date(Date.UTC(x.getUTCFullYear(), x.getUTCMonth() - m, x.getUTCDate())); cut = Math.floor(d.getTime() / 86400000); }
    for (let i = 0; i < B.n; i++) if (B.dayEnd[i] >= cut) return i;
    return Math.max(0, B.n - 1);
  }

  /** 事件日 → 每根 K 棒是否落在「事件前 before 根～後 after 根」的窗內。 events：[{d:'YYYY-MM-DD', t:type, lag}]；用日 K 的 index 平移，週／月 K 以含該日的那根為準。 */
  function eventWindowMask(B, events, before, after) {
    const m = new Uint8Array(B.n); const days = B.day, dend = B.dayEnd;
    for (const e of events) {
      const d = strToDay(e.d) + (e.lag || 0);
      // 事件日當天或之後第一根
      let k = -1;
      if (B.tf === '60') { for (let i = 0; i < B.n; i++) if (days[i] >= d) { k = i; break; } if (k >= 0) { const perDay = 5; for (let j = k - before * perDay; j <= k + after * perDay + perDay - 1; j++) if (j >= 0 && j < B.n) m[j] = 1; } continue; }
      for (let i = 0; i < B.n; i++) if (dend[i] >= d) { k = i; break; }
      if (k < 0) continue;
      for (let j = k - before; j <= k + after; j++) if (j >= 0 && j < B.n) m[j] = 1;
    }
    return m;
  }

  /** 事件前後報酬統計（日 K）。回傳每個事件類型的平均／中位數／勝率／波動與逐日平均路徑。 */
  function eventStudy(D, events, N) {
    const out = {};
    const days = D.day, n = D.n;
    const dret = new Float64Array(n); for (let i = 1; i < n; i++) dret[i] = D.c[i] / D.c[i - 1] - 1;
    const all = []; for (let i = 1; i < n; i++) all.push(dret[i]);
    const sdAll = Math.sqrt(all.reduce((a, b) => a + b * b, 0) / (all.length || 1));
    for (const e of events) {
      const d = strToDay(e.d) + (e.lag || 0);
      let k = -1; for (let i = 0; i < n; i++) if (days[i] >= d) { k = i; break; }
      if (k < 1) continue;
      const g = out[e.t] || (out[e.t] = { n: 0, path: new Float64Array(2 * N + 1), cnt: new Float64Array(2 * N + 1), pre: [], day0: [], post1: [], postN: [], vol: [], list: [] });
      g.n++;
      // 逐日累積報酬路徑：以事件日前一天收盤（k-1）為基準 0
      const base = D.c[k - 1];
      for (let j = -N; j <= N; j++) { const idx = k + j; if (idx < 0 || idx >= n) continue; g.path[j + N] += D.c[idx] / base - 1; g.cnt[j + N]++; }
      const pre = k - 1 - N >= 0 ? D.c[k - 1] / D.c[k - 1 - N] - 1 : NaN;
      const day0 = dret[k], post1 = k + 1 < n ? D.c[k + 1] / D.c[k - 1] - 1 : NaN, postN = k + N < n ? D.c[k + N] / D.c[k - 1] - 1 : NaN;
      let v = 0, vc = 0; for (let j = k; j <= Math.min(n - 1, k + N); j++) { v += dret[j] * dret[j]; vc++; }
      g.pre.push(pre); g.day0.push(day0); g.post1.push(post1); g.postN.push(postN); g.vol.push(vc ? Math.sqrt(v / vc) : NaN);
      g.list.push({ d: e.d, name: e.name || '', pre, day0, post1, postN });
    }
    const med = (a) => { const b = a.filter((x) => !Number.isNaN(x)).sort((x, y) => x - y); return b.length ? (b.length % 2 ? b[(b.length - 1) / 2] : (b[b.length / 2 - 1] + b[b.length / 2]) / 2) : NaN; };
    const avg = (a) => { const b = a.filter((x) => !Number.isNaN(x)); return b.length ? b.reduce((x, y) => x + y, 0) / b.length : NaN; };
    const winr = (a) => { const b = a.filter((x) => !Number.isNaN(x)); return b.length ? b.filter((x) => x > 0).length / b.length * 100 : NaN; };
    const res = {};
    for (const t in out) {
      const g = out[t];
      res[t] = { n: g.n, pre: { avg: avg(g.pre) * 100, win: winr(g.pre) }, day0: { avg: avg(g.day0) * 100, med: med(g.day0) * 100, win: winr(g.day0) }, post1: { avg: avg(g.post1) * 100, win: winr(g.post1) }, postN: { avg: avg(g.postN) * 100, med: med(g.postN) * 100, win: winr(g.postN) }, vol: avg(g.vol) * 100, volRatio: sdAll > 0 ? avg(g.vol) / sdAll : NaN, path: Array.from(g.path, (x, i) => (g.cnt[i] ? x / g.cnt[i] * 100 : NaN)), list: g.list };
    }
    return res;
  }

  /** 組裝一次回測：策略（內建或自訂已編譯訊號）＋設定＋區間＋事件濾網 */
  function runStrategy(B, strat, cfg, rangeKey, events) {
    const sig = strat.sig || STRAT[strat.id].build(B, Object.assign(defaults(strat.id), strat.params || {}));
    const c2 = Object.assign({}, cfg);
    if (strat.risk) { const r = strat.risk; if (r.sl > 0) c2.sl = r.sl; if (r.tp > 0) c2.tp = r.tp; if (r.trail > 0) c2.trail = r.trail; if (r.maxbars > 0) c2.maxBars = r.maxbars; }    // 自訂策略自帶的風控
    if (cfg.evt && cfg.evt.on && events && events.length) {
      const f = events.filter((e) => cfg.evt.types.includes(e.t));
      const inW = eventWindowMask(B, f, cfg.evt.before | 0, cfg.evt.after | 0);
      if (cfg.evt.mode === 'avoid') c2.entryMask = inW.map((x) => (x ? 0 : 1));
      else c2.entryMask = inW;
      if (cfg.evt.flat) c2.exitMask = cfg.evt.mode === 'avoid' ? inW : null;
    }
    const from = rangeFrom(B, rangeKey || 'All');
    return run(B, sig, c2, from, B.n - 1);
  }

  const api = { decode, resample, PPY, I, STRATS, STRAT, defaults, instDefaults, run, runStrategy, rangeFrom, eventWindowMask, eventStudy, computeStats, dayToStr, strToDay, up, dn, mk };

  /** Worker 訊息處理：load 資料 → run 回測。資料以 key 快取在 worker 內，避免每次重傳。 */
  const cache = {};
  api.handle = function (m) {
    if (m.op === 'load') { cache[m.key] = m.bars; return { ok: 1 }; }
    const B = cache[m.key]; if (!B) throw new Error('worker 沒有資料：' + m.key);
    if (m.op === 'run') {
      const r = runStrategy(B, m.strat, m.cfg, m.range, m.events);
      return { trades: r.trades, open: r.open, opens: r.opens, eq: r.eq, bh: r.bh, stats: r.stats, from: r.from, to: r.to };
    }
    if (m.op === 'study') return eventStudy(B, m.events, m.N || 10);
    if (m.op === 'cmp') {   // 事件條件前後對照：同一策略跑兩次
      const a = runStrategy(B, m.strat, Object.assign({}, m.cfg, { evt: null }), m.range, m.events);
      const b = runStrategy(B, m.strat, m.cfg, m.range, m.events);
      return { base: { stats: a.stats, eq: a.eq }, evt: { stats: b.stats, eq: b.eq } };
    }
    throw new Error('未知的訊息：' + m.op);
  };
  return api;
}));
