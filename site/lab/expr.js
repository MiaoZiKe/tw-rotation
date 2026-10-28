/* ============================================================================
   交易練習室：迷你策略腳本（類 Pine 子集，JS 直譯；規格 docs/tradingview_spec.md 3.7）—— 2026-10-28 建
   積木式編輯器產生的條件也走這支（積木 → 文字 → 這裡編譯），所以只有一條編譯路徑。
   · 序列函式全部只用「這一根與之前」的資料（無未來資料）；x[n] 取前 n 根，n 必須 ≥ 0。
   · 同時接受中文與英文別名（TradingView 的 ta.sma、ta.crossover、strategy.entry…），會 Pine 的人可以貼簡單的策略。
   · 不支援：迴圈、陣列、自訂函式、request.security（跨週期）。
   範例：
     // 均線交叉＋RSI 濾網
     快 = 參數("快線", 5)
     慢 = 參數("慢線", 20)
     若 上穿(均線(收盤,快), 均線(收盤,慢)) 且 rsi(收盤,14) < 70 則 進場("多")
     若 下穿(均線(收盤,快), 均線(收盤,慢)) 則 平倉("多")
     出場("風控", 停損%=5, 停利%=10, 移動%=3, 最長持有=30)
   ============================================================================ */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./engine.js'));
  else root.LabExpr = factory(root.LabEngine);
}(typeof self !== 'undefined' ? self : this, function (E) {
  'use strict';
  const I = E.I;

  /* ---------------------------------------------------------------- 別名 */
  const ALIAS = {
    收盤: 'close', 開盤: 'open', 最高: 'high', 最低: 'low', 成交量: 'volume', 均線: 'sma', 指數均線: 'ema', 上穿: 'crossover', 下穿: 'crossunder',
    最高價: 'highest', 最低價: 'lowest', 絕對值: 'abs', 最大: 'max', 最小: 'min', 漲跌: 'change', 平均真實區間: 'atr', 真實區間: 'tr',
    進場: 'entry', 平倉: 'closepos', 出場: 'exitrisk', 策略: 'strategy', 參數: 'param', 事件: 'event', 做多: 'long', 做空: 'short', 多: 'long', 空: 'short', 全部: 'all',
    停損: 'sl', '停損%': 'sl', 停利: 'tp', '停利%': 'tp', 移動: 'trail', '移動%': 'trail', 移動停損: 'trail', '移動停損%': 'trail', 最長持有: 'maxbars',
    且: 'and', 或: 'or', 非: 'not', 若: 'if', 則: 'then', 'kd_k': 'kd_k', 'kd_d': 'kd_d',
  };
  const norm = (name) => {
    let n = String(name);
    if (ALIAS[n]) return ALIAS[n];
    n = n.toLowerCase();
    n = n.replace(/^(ta|math)\./, '');
    const map = { 'strategy.entry': 'entry', 'strategy.close': 'closepos', 'strategy.close_all': 'closepos', 'strategy.exit': 'exitrisk', 'strategy.long': 'long', 'strategy.short': 'short', 'strategy.risk.max_intraday_loss': 'exitrisk', 'input.int': 'param', 'input.float': 'param', input: 'param', 'macd.dif': 'macd_dif', 'macd.dea': 'macd_dea', 'macd.osc': 'macd_osc', stoch_k: 'kd_k', stoch_d: 'kd_d' };
    return map[n] || ALIAS[n] || n;
  };

  /* ---------------------------------------------------------------- 詞法 */
  function tokenize(src, line) {
    const out = []; let i = 0;
    const isId = (c) => /[A-Za-z_一-鿿]/.test(c), isIdc = (c) => /[A-Za-z0-9_一-鿿.%]/.test(c);
    while (i < src.length) {
      const c = src[i];
      if (/\s/.test(c)) { i++; continue; }
      if (/[0-9]/.test(c) || (c === '.' && /[0-9]/.test(src[i + 1] || ''))) { let j = i; while (j < src.length && /[0-9.]/.test(src[j])) j++; out.push({ t: 'num', v: parseFloat(src.slice(i, j)) }); i = j; continue; }
      if (c === '"' || c === "'" || c === '“') { const q = c === '“' ? '”' : c; let j = i + 1; while (j < src.length && src[j] !== q) j++; out.push({ t: 'str', v: src.slice(i + 1, j) }); i = j + 1; continue; }
      if (isId(c)) { let j = i; while (j < src.length && isIdc(src[j])) j++; let w = src.slice(i, j); if (w.endsWith('.')) { w = w.slice(0, -1); j--; } out.push({ t: 'id', v: w }); i = j; continue; }
      const two = src.slice(i, i + 2);
      if (['>=', '<=', '==', '!=', '&&', '||', '<>'].includes(two)) { out.push({ t: 'op', v: two === '<>' ? '!=' : two }); i += 2; continue; }
      if ('+-*/%()[],=<>!'.includes(c)) { out.push({ t: 'op', v: c }); i++; continue; }
      throw new Error('第 ' + line + ' 行：看不懂的符號「' + c + '」');
    }
    return out;
  }

  /* ---------------------------------------------------------------- 語法（Pratt） */
  function parseExpr(toks, line) {
    let p = 0;
    const peek = () => toks[p], next = () => toks[p++];
    const isOp = (v) => peek() && peek().t === 'op' && peek().v === v;
    const word = (t) => (t && t.t === 'id' ? norm(t.v) : null);
    const PREC = { or: 1, and: 2, '==': 4, '!=': 4, '<': 5, '>': 5, '<=': 5, '>=': 5, '+': 6, '-': 6, '*': 7, '/': 7, '%': 7 };
    const opName = (t) => { if (!t) return null; if (t.t === 'op') return t.v === '||' ? 'or' : t.v === '&&' ? 'and' : t.v; if (t.t === 'id') { const w = word(t); return w === 'and' || w === 'or' ? w : null; } return null; };
    function primary() {
      const t = next(); if (!t) throw new Error('第 ' + line + ' 行：算式寫到一半');
      let node;
      if (t.t === 'num') node = { k: 'num', v: t.v };
      else if (t.t === 'str') node = { k: 'str', v: t.v };
      else if (t.t === 'op' && t.v === '(') { node = expr(0); if (!isOp(')')) throw new Error('第 ' + line + ' 行：少了右括號'); next(); }
      else if (t.t === 'op' && t.v === '-') node = { k: 'neg', a: primary() };
      else if (t.t === 'op' && t.v === '!') node = { k: 'not', a: primary() };
      else if (t.t === 'id') {
        const w = word(t);
        if (w === 'not') node = { k: 'not', a: expr(3) };
        else if (isOp('(')) {
          next(); const args = [], kw = {};
          while (!isOp(')')) {
            if (!peek()) throw new Error('第 ' + line + ' 行：函式「' + t.v + '」少了右括號');
            if (peek().t === 'id' && toks[p + 1] && toks[p + 1].t === 'op' && toks[p + 1].v === '=') { const key = norm(next().v); next(); kw[key] = expr(0); }
            else args.push(expr(0));
            if (isOp(',')) next();
          }
          next(); node = { k: 'call', f: w, args, kw, raw: t.v };
        } else node = { k: 'id', v: t.v, w };
      } else throw new Error('第 ' + line + ' 行：這裡不該出現「' + (t.v === undefined ? '' : t.v) + '」');
      while (isOp('[')) { next(); const n = expr(0); if (!isOp(']')) throw new Error('第 ' + line + ' 行：少了 ]'); next(); node = { k: 'idx', a: node, n }; }
      return node;
    }
    function expr(minP) {
      let left = primary();
      for (;;) {
        const nm = opName(peek()); const pr = nm ? PREC[nm] : undefined;
        if (pr === undefined || pr < minP || pr === 0) break;
        next(); const right = expr(pr + 1); left = { k: 'bin', op: nm, a: left, b: right };
      }
      return left;
    }
    const e = expr(0);
    if (p < toks.length) throw new Error('第 ' + line + ' 行：算式後面多了「' + (toks[p].v === undefined ? '' : toks[p].v) + '」');
    return e;
  }

  /* ---------------------------------------------------------------- 求值（回傳 number 或 Float64Array） */
  function makeEnv(B, ctx) {
    const n = B.n, vars = {}, params = [], cache = {};
    const FIELDS = { close: B.c, open: B.o, high: B.h, low: B.l, volume: B.v, hl2: Float64Array.from(B.c, (_, i) => (B.h[i] + B.l[i]) / 2) };
    const ser = (a) => { if (a instanceof Float64Array) return a; const o = new Float64Array(n); o.fill(+a); return o; };
    const num = (a, what) => { if (typeof a === 'number') return a; if (a instanceof Float64Array) { const v = a[a.length - 1]; if (Number.isFinite(v)) return v; } throw new Error('「' + what + '」需要是一個固定的數字'); };
    const map2 = (a, b, f) => {
      if (typeof a === 'number' && typeof b === 'number') return f(a, b);
      const A = ser(a), Bs = ser(b), o = new Float64Array(n); for (let i = 0; i < n; i++) o[i] = f(A[i], Bs[i]); return o;
    };
    const bool = (x) => (x ? 1 : 0);
    const fn = {
      sma: (a, k) => I.sma(ser(a), num(k, '週期')), ema: (a, k) => I.ema(ser(a), num(k, '週期')), rma: (a, k) => I.rma(ser(a), num(k, '週期')),
      rsi: (a, k) => I.rsi(ser(a), num(k, '週期')), highest: (a, k) => I.highest(ser(a), num(k, '週期')), lowest: (a, k) => I.lowest(ser(a), num(k, '週期')),
      change: (a, k) => { const m = k === undefined ? 1 : num(k, '期數'), A = ser(a), o = new Float64Array(n).fill(NaN); for (let i = m; i < n; i++) o[i] = A[i] - A[i - m]; return o; },
      atr: (k) => I.atr(B.h, B.l, B.c, num(k === undefined ? 14 : k, '週期')), tr: () => I.tr(B.h, B.l, B.c),
      kd_k: (k) => I.kd(B.h, B.l, B.c, num(k === undefined ? 9 : k, '週期'), 3, 3).k, kd_d: (k) => I.kd(B.h, B.l, B.c, num(k === undefined ? 9 : k, '週期'), 3, 3).d,
      macd_dif: (a, f, s) => I.macd(ser(a), num(f === undefined ? 12 : f, '快線'), num(s === undefined ? 26 : s, '慢線'), 9).dif,
      macd_dea: (a, f, s, g) => I.macd(ser(a), num(f === undefined ? 12 : f, '快線'), num(s === undefined ? 26 : s, '慢線'), num(g === undefined ? 9 : g, '訊號')).dea,
      macd_osc: (a, f, s, g) => I.macd(ser(a), num(f === undefined ? 12 : f, '快線'), num(s === undefined ? 26 : s, '慢線'), num(g === undefined ? 9 : g, '訊號')).osc,
      bb_up: (a, k, m) => I.boll(ser(a), num(k, '週期'), num(m === undefined ? 2 : m, '倍數')).up, bb_mid: (a, k, m) => I.boll(ser(a), num(k, '週期'), num(m === undefined ? 2 : m, '倍數')).mid, bb_low: (a, k, m) => I.boll(ser(a), num(k, '週期'), num(m === undefined ? 2 : m, '倍數')).low,
      cci: (k) => I.cci(B.h, B.l, B.c, num(k === undefined ? 20 : k, '週期')), willr: (k) => I.willr(B.h, B.l, B.c, num(k === undefined ? 14 : k, '週期')),
      sar_dir: (s, i2, m) => I.sar(B.h, B.l, num(s === undefined ? 0.02 : s, '起始'), num(i2 === undefined ? 0.02 : i2, '增量'), num(m === undefined ? 0.2 : m, '上限')).dir,
      supertrend_dir: (k, m) => I.supertrend(B.h, B.l, B.c, num(k === undefined ? 10 : k, '週期'), num(m === undefined ? 3 : m, '倍數')).trend,
      crossover: (a, b) => { const A = ser(a), Bs = ser(b), o = new Float64Array(n); for (let i = 1; i < n; i++) o[i] = bool(A[i] > Bs[i] && A[i - 1] <= Bs[i - 1]); return o; },
      crossunder: (a, b) => { const A = ser(a), Bs = ser(b), o = new Float64Array(n); for (let i = 1; i < n; i++) o[i] = bool(A[i] < Bs[i] && A[i - 1] >= Bs[i - 1]); return o; },
      abs: (a) => (typeof a === 'number' ? Math.abs(a) : a.map(Math.abs)), max: (a, b) => map2(a, b, Math.max), min: (a, b) => map2(a, b, Math.min),
      nz: (a, d) => { const v = d === undefined ? 0 : d; return typeof a === 'number' ? (Number.isFinite(a) ? a : v) : a.map((x) => (Number.isFinite(x) ? x : v)); },
      event: (t, b, a) => {   // 事件窗：這一根是否落在「某類事件前 b 根～後 a 根」內（日 K 為日數；週月 K 為根數）
        const ev = (ctx.events || []).filter((e) => e.t === t.s); const m = E.eventWindowMask(B, ev, num(b === undefined ? 0 : b, '事件前'), num(a === undefined ? 0 : a, '事件後')); return Float64Array.from(m);
      },
    };
    function ev(node) {
      switch (node.k) {
        case 'num': return node.v;
        case 'str': return { s: node.v };
        case 'neg': { const a = ev(node.a); return typeof a === 'number' ? -a : a.map((x) => -x); }
        case 'not': { const a = ev(node.a); return typeof a === 'number' ? bool(!a) : a.map((x) => bool(!x)); }
        case 'id': {
          const w = node.w;
          if (Object.prototype.hasOwnProperty.call(vars, node.v)) return vars[node.v];
          if (FIELDS[w]) return FIELDS[w];
          if (w === 'long') return 1; if (w === 'short') return -1; if (w === 'all') return 0;
          throw new Error('不認得「' + node.v + '」（可用：收盤、開盤、最高、最低、成交量，或你自己定義的變數）');
        }
        case 'idx': { const a = ser(ev(node.a)), k = num(ev(node.n), '[]'); if (k < 0) throw new Error('x[n] 的 n 不能小於 0（不能看未來）'); const o = new Float64Array(n).fill(NaN); for (let i = k; i < n; i++) o[i] = a[i - k]; return o; }
        case 'bin': {
          const a = ev(node.a), b = ev(node.b), op = node.op;
          const F = { '+': (x, y) => x + y, '-': (x, y) => x - y, '*': (x, y) => x * y, '/': (x, y) => (y === 0 ? NaN : x / y), '%': (x, y) => x % y, '>': (x, y) => bool(x > y), '<': (x, y) => bool(x < y), '>=': (x, y) => bool(x >= y), '<=': (x, y) => bool(x <= y), '==': (x, y) => bool(x === y), '!=': (x, y) => bool(x !== y), and: (x, y) => bool(x && y), or: (x, y) => bool(x || y) }[op];
          return map2(a, b, F);
        }
        case 'call': {
          const f = fn[node.f]; if (!f) throw new Error('不認得函式「' + node.raw + '」');
          if (node.f === 'event') return f(ev(node.args[0]), node.args[1] ? ev(node.args[1]) : undefined, node.args[2] ? ev(node.args[2]) : undefined);
          return f(...node.args.map(ev));
        }
        default: throw new Error('算式有誤');
      }
    }
    return { ev, vars, params, n };
  }

  /* ---------------------------------------------------------------- 編譯：整份腳本 → 訊號 */
  /** compile(text, B, ctx) → { sig, risk, params, errors, name }；ctx：{ params:{變數名:值}, events:[...] } */
  function compile(text, B, ctx) {
    ctx = ctx || {};
    const n = B.n, errors = [], params = [], risk = {};
    const sig = { L: new Uint8Array(n), S: new Uint8Array(n), XL: new Uint8Array(n), XS: new Uint8Array(n) };
    let name = '';
    const env = makeEnv(B, ctx);
    const lines = String(text || '').split(/\r?\n/);
    lines.forEach((raw, idx) => {
      const ln = idx + 1; let line = raw.replace(/\/\/.*$/, '').trim(); if (!line) return;
      try {
        const toks = tokenize(line, ln);
        // 若 條件 則 動作
        const w0 = toks[0] && toks[0].t === 'id' ? norm(toks[0].v) : null;
        if (w0 === 'if') {
          let k = toks.findIndex((t, i) => i > 0 && t.t === 'id' && norm(t.v) === 'then');
          if (k < 0) throw new Error('第 ' + ln + ' 行：「若 … 則 …」少了「則」');
          const cond = env.ev(parseExpr(toks.slice(1, k), ln)), act = parseExpr(toks.slice(k + 1), ln);
          if (act.k !== 'call' || !['entry', 'closepos'].includes(act.f)) throw new Error('第 ' + ln + ' 行：「則」後面要接 進場(…) 或 平倉(…)');
          const dirOf = (a) => { for (const x of act.args) { if (x.k === 'str') { const s = norm(x.v); if (s === 'long' || /^(buy|bull)$/.test(s)) return 1; if (s === 'short' || /^(sell|bear)$/.test(s)) return -1; } else if (x.k === 'id') { const s = norm(x.v); if (s === 'long') return 1; if (s === 'short') return -1; if (s === 'all') return 0; } } return a; };
          const d = dirOf(act.f === 'entry' ? 1 : 0);
          const c = typeof cond === 'number' ? Float64Array.from({ length: n }, () => cond) : cond;
          const tgt = act.f === 'entry' ? (d === -1 ? sig.S : sig.L) : (d === 1 ? [sig.XL] : d === -1 ? [sig.XS] : [sig.XL, sig.XS]);
          (Array.isArray(tgt) ? tgt : [tgt]).forEach((arr) => { for (let i = 0; i < n; i++) if (c[i]) arr[i] = 1; });
          return;
        }
        const wc = toks[0] && toks[0].t === 'id' ? norm(toks[0].v) : null;
        if (toks[1] && toks[1].t === 'op' && toks[1].v === '=' && toks[0].t === 'id' && !(toks[2] && toks[2].t === 'op' && toks[2].v === '=')) {   // 指定：x = 算式
          const vn = toks[0].v, rhs = parseExpr(toks.slice(2), ln);
          if (rhs.k === 'call' && rhs.f === 'param') {
            const label = rhs.args[0] && rhs.args[0].k === 'str' ? rhs.args[0].v : vn, defv = rhs.args[1] ? env.ev(rhs.args[1]) : 0;
            const v = ctx.params && ctx.params[vn] != null ? +ctx.params[vn] : defv;
            params.push({ k: vn, label, def: defv }); env.vars[vn] = v;
          } else env.vars[vn] = env.ev(rhs);
          return;
        }
        if (wc === 'strategy') { const e = parseExpr(toks, ln); if (e.args[0] && e.args[0].k === 'str') name = e.args[0].v; return; }
        if (wc === 'exitrisk' || wc === 'param') {
          const e = parseExpr(toks, ln);
          Object.keys(e.kw).forEach((k) => { if (['sl', 'tp', 'trail', 'maxbars'].includes(k)) risk[k] = env.ev(e.kw[k]); });
          // 位置參數：出場("名稱", 5, 10) 不支援，避免猜錯
          return;
        }
        throw new Error('第 ' + ln + ' 行：看不懂這一行（寫法：若 條件 則 進場("多")、x = 算式、出場("風控", 停損%=5)）');
      } catch (e) { errors.push(e.message || String(e)); }
    });
    if (!errors.length && !sig.L.some((x) => x) && !sig.S.some((x) => x) && lines.some((l) => l.trim() && !/^\s*\/\//.test(l))) errors.push('這份腳本沒有任何進場訊號（至少要有一行「若 條件 則 進場("多")」）');
    return { sig: errors.length ? null : sig, risk, params, errors, name };
  }

  /* ---------------------------------------------------------------- 積木 → 腳本文字 */
  const OPD = {   // 積木裡可選的運算元：fmt 把參數轉成腳本片語
    close: { name: '收盤價', p: [], fmt: () => 'close' }, open: { name: '開盤價', p: [], fmt: () => 'open' }, high: { name: '最高價', p: [], fmt: () => 'high' }, low: { name: '最低價', p: [], fmt: () => 'low' }, volume: { name: '成交量', p: [], fmt: () => 'volume' },
    sma: { name: '均線 SMA', p: [['n', '週期', 20]], fmt: (v) => `sma(close,${v.n})` }, ema: { name: '指數均線 EMA', p: [['n', '週期', 20]], fmt: (v) => `ema(close,${v.n})` },
    rsi: { name: 'RSI', p: [['n', '週期', 14]], fmt: (v) => `rsi(close,${v.n})` }, kdk: { name: 'KD 的 K', p: [['n', '週期', 9]], fmt: (v) => `kd_k(${v.n})` }, kdd: { name: 'KD 的 D', p: [['n', '週期', 9]], fmt: (v) => `kd_d(${v.n})` },
    dif: { name: 'MACD 快線 DIF', p: [['f', '快', 12], ['s', '慢', 26]], fmt: (v) => `macd_dif(close,${v.f},${v.s})` }, dea: { name: 'MACD 訊號線', p: [['f', '快', 12], ['s', '慢', 26], ['g', '訊號', 9]], fmt: (v) => `macd_dea(close,${v.f},${v.s},${v.g})` }, osc: { name: 'MACD 柱狀體', p: [['f', '快', 12], ['s', '慢', 26], ['g', '訊號', 9]], fmt: (v) => `macd_osc(close,${v.f},${v.s},${v.g})` },
    bbu: { name: '布林上軌', p: [['n', '週期', 20], ['k', '倍數', 2]], fmt: (v) => `bb_up(close,${v.n},${v.k})` }, bbm: { name: '布林中軌', p: [['n', '週期', 20], ['k', '倍數', 2]], fmt: (v) => `bb_mid(close,${v.n},${v.k})` }, bbl: { name: '布林下軌', p: [['n', '週期', 20], ['k', '倍數', 2]], fmt: (v) => `bb_low(close,${v.n},${v.k})` },
    atr: { name: 'ATR', p: [['n', '週期', 14]], fmt: (v) => `atr(${v.n})` }, hh: { name: '前 N 日最高價（不含今天）', p: [['n', '週期', 20]], fmt: (v) => `highest(high,${v.n})[1]` }, ll: { name: '前 N 日最低價（不含今天）', p: [['n', '週期', 20]], fmt: (v) => `lowest(low,${v.n})[1]` },
    vma: { name: '成交量均線', p: [['n', '週期', 5]], fmt: (v) => `sma(volume,${v.n})` }, chg: { name: 'N 日漲跌（元）', p: [['n', '期數', 5]], fmt: (v) => `change(close,${v.n})` },
    num: { name: '固定數字', p: [['v', '數字', 0]], fmt: (v) => String(v.v) },
  };
  const CMP = { up: ['上穿', (a, b) => `crossover(${a},${b})`], dn: ['下穿', (a, b) => `crossunder(${a},${b})`], gt: ['大於', (a, b) => `${a} > ${b}`], lt: ['小於', (a, b) => `${a} < ${b}`], ge: ['大於等於', (a, b) => `${a} >= ${b}`], le: ['小於等於', (a, b) => `${a} <= ${b}`] };
  const opText = (o) => { const d = OPD[o.t] || OPD.close, v = {}; d.p.forEach(([k, , def]) => { v[k] = o[k] != null && o[k] !== '' ? Number(o[k]) : def; }); return d.fmt(v); };
  function rowText(r) {
    if (r.kind === 'event') return (r.not ? 'not ' : '') + `event("${r.type}",${Number(r.before) || 0},${Number(r.after) || 0})`;
    const c = CMP[r.op] || CMP.gt; return c[1](opText(r.a), opText(r.b));
  }
  const blockText = (b) => (b && b.rows && b.rows.length ? b.rows.map((r) => '(' + rowText(r) + ')').join(b.join === 'or' ? ' or ' : ' and ') : '');
  /** 規則 JSON → 腳本文字（給編譯與「看腳本」用） */
  function toScript(rule) {
    const o = [`策略("${(rule.name || '我的策略').replace(/"/g, '')}")`], B = rule.blocks || {};
    const add = (key, action) => { const t = blockText(B[key]); if (t) o.push(`若 ${t} 則 ${action}`); };
    add('le', '進場("多")'); add('lx', '平倉("多")'); add('se', '進場("空")'); add('sx', '平倉("空")');
    const r = rule.risk || {}, kv = [];
    if (r.sl > 0) kv.push(`停損%=${r.sl}`); if (r.tp > 0) kv.push(`停利%=${r.tp}`); if (r.trail > 0) kv.push(`移動%=${r.trail}`); if (r.maxbars > 0) kv.push(`最長持有=${r.maxbars}`);
    if (kv.length) o.push(`出場("風控", ${kv.join(', ')})`);
    return o.join('\n');
  }

  /** 內建策略 → 同一套規則的腳本文字（給「另存為我的策略」用）。回傳 null＝這支沒有對應的腳本寫法。
      tests/lab_expr_check.js 逐支驗證：腳本編譯出來的訊號與內建策略完全相同。 */
  function scriptFor(id, p) {
    const q = (k, d) => (p && p[k] != null ? p[k] : d), L = [];
    const both = (l, s) => { L.push('若 ' + l + ' 則 進場("多")'); L.push('若 ' + s + ' 則 進場("空")'); };
    switch (id) {
      case 'ma2': both(`crossover(sma(close,${q('f', 9)}), sma(close,${q('s', 18)}))`, `crossunder(sma(close,${q('f', 9)}), sma(close,${q('s', 18)}))`); break;
      case 'ma1': if (q('k', 1) !== 1) return null; both(`crossover(close, sma(close,${q('n', 9)}))`, `crossunder(close, sma(close,${q('n', 9)}))`); break;
      case 'rsi': L.push(`r = rsi(close,${q('n', 14)})`); both(`crossover(r, ${q('lo', 30)})`, `crossunder(r, ${q('hi', 70)})`); break;
      case 'macd': L.push(`o = macd_osc(close,${q('f', 12)},${q('s', 26)},${q('g', 9)})`); both('o > 0 且 o[1] <= 0', 'o < 0 且 o[1] >= 0'); break;
      case 'bb': both(`crossover(close, bb_low(close,${q('n', 20)},${q('k', 2)}))`, `crossunder(close, bb_up(close,${q('n', 20)},${q('k', 2)}))`); break;
      case 'pricech': both(`close > highest(high,${q('n', 20)})[1]`, `close < lowest(low,${q('n', 20)})[1]`); break;
      case 'kd': L.push(`k = kd_k(${q('n', 9)})`, `d = kd_d(${q('n', 9)})`); both(`crossover(k, d) 且 k < ${q('lo', 20)}`, `crossunder(k, d) 且 k > ${q('hi', 80)}`); break;
      case 'supertrend': L.push(`t = supertrend_dir(${q('n', 10)},${q('m', 3)})`); both('t > 0 且 t[1] < 0', 't < 0 且 t[1] > 0'); break;
      case 'cci': L.push(`x = cci(${q('n', 20)})`); both(`x > ${-q('t', 100)} 且 x[1] <= ${-q('t', 100)}`, `x < ${q('t', 100)} 且 x[1] >= ${q('t', 100)}`); break;
      case 'willr': L.push(`x = willr(${q('n', 14)})`); both('x > -80 且 x[1] <= -80', 'x < -20 且 x[1] >= -20'); break;
      case 'barupdn': both('close > open 且 open > close[1]', 'close < open 且 open < close[1]'); break;
      case 'inside': both('high < high[1] 且 low > low[1] 且 close > open', 'high < high[1] 且 low > low[1] 且 close < open'); break;
      case 'outside': both('high > high[1] 且 low < low[1] 且 close > open', 'high > high[1] 且 low < low[1] 且 close < open'); break;
      case 'consec': { const up = [], dn = []; for (let i = 0; i < q('n', 3); i++) up.push(`close${i ? '[' + i + ']' : ''} > close[${i + 1}]`); for (let i = 0; i < q('m', 3); i++) dn.push(`close${i ? '[' + i + ']' : ''} < close[${i + 1}]`); both(up.join(' 且 '), dn.join(' 且 ')); break; }
      default: return null;
    }
    return L.join('\n');
  }

  return { compile, tokenize, parseExpr, toScript, scriptFor, rowText, blockText, OPD, CMP, norm };
}));
