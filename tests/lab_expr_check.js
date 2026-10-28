/* 迷你腳本／積木編譯器驗證（node tests/lab_expr_check.js）：
   ① 腳本與同名內建策略訊號完全相同  ② 中英文別名等價  ③ 沒有未來資料  ④ 錯誤訊息有行號  ⑤ 積木 → 腳本 → 訊號 */
'use strict';
const assert = require('assert');
const E = require('../site/lab/engine.js');
const X = require('../site/lab/expr.js');
let pass = 0;
const eq = (a, b, m) => { assert.deepStrictEqual(a, b, m); pass++; };
function randBars(n, seed) {
  let s = seed; const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  const B = { n, tf: 'D', ts: new Float64Array(n), day: new Float64Array(n), dayEnd: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) };
  let p = 100; for (let i = 0; i < n; i++) { const o = p * (1 + (rnd() - 0.5) * 0.01); p *= 1 + (rnd() - 0.48) * 0.05; B.o[i] = o; B.c[i] = p; B.h[i] = Math.max(o, p) * (1 + rnd() * 0.01); B.l[i] = Math.min(o, p) * (1 - rnd() * 0.01); B.day[i] = 19000 + i; B.dayEnd[i] = 19000 + i; B.v[i] = 1000 + rnd() * 500; }
  return B;
}
const same = (a, b, keys) => keys.every((k) => a[k].every((x, i) => x === b[k][i]));
const B = randBars(500, 9);
{   // 隨機籌碼（外資／投信／自營買賣超，張），讓有籌碼的內建策略也能做腳本等價驗證
  let q = 77; const rnd = () => { q = (q * 16807) % 2147483647; return q / 2147483647; };
  B.chip = { fn: Float64Array.from({ length: B.n }, () => Math.round((rnd() - 0.5) * 2000)), tr: Float64Array.from({ length: B.n }, () => Math.round((rnd() - 0.5) * 400)), dl: Float64Array.from({ length: B.n }, () => Math.round((rnd() - 0.5) * 300)) };
}

// ① 腳本＝內建策略
let r = X.compile('若 crossover(sma(close,5), sma(close,20)) 則 進場("多")\n若 crossunder(sma(close,5), sma(close,20)) 則 進場("空")', B);
eq(r.errors, [], '雙均線腳本沒有錯誤');
const ma2 = E.STRAT.ma2.build(B, { f: 5, s: 20 });
assert.ok(same(r.sig, ma2, ['L', 'S']), '雙均線腳本訊號＝內建 ma2'); pass++;
r = X.compile('若 上穿(均線(收盤,5), 均線(收盤,20)) 則 進場("多")\n若 下穿(均線(收盤,5), 均線(收盤,20)) 則 進場("空")', B);
eq(r.errors, [], '中文別名沒有錯誤'); assert.ok(same(r.sig, ma2, ['L', 'S']), '中文別名等價'); pass++;
r = X.compile('若 ta.crossover(ta.sma(close,5), ta.sma(close,20)) 則 strategy.entry("L", strategy.long)\n若 ta.crossunder(ta.sma(close,5), ta.sma(close,20)) 則 strategy.entry("S", strategy.short)', B);
eq(r.errors, [], '英文別名沒有錯誤'); assert.ok(same(r.sig, ma2, ['L', 'S']), '英文別名等價'); pass++;
// RSI
r = X.compile('r = rsi(close,14)\n若 crossover(r, 30) 則 進場("多")\n若 crossunder(r, 70) 則 進場("空")', B);
eq(r.errors, [], 'RSI 腳本沒有錯誤'); assert.ok(same(r.sig, E.STRAT.rsi.build(B, { n: 14, lo: 30, hi: 70 }), ['L', 'S']), 'RSI 腳本＝內建 rsi'); pass++;
// MACD 柱狀體由負轉正
r = X.compile('o = macd_osc(close,12,26,9)\n若 o > 0 且 o[1] <= 0 則 進場("多")\n若 o < 0 且 o[1] >= 0 則 進場("空")', B);
eq(r.errors, [], 'MACD 腳本沒有錯誤'); assert.ok(same(r.sig, E.STRAT.macd.build(B, { f: 12, s: 26, g: 9 }), ['L', 'S']), 'MACD 腳本＝內建 macd'); pass++;
// ② 參數變數：預設值與覆寫
const PS = '快 = 參數("快線", 5)\n慢 = 參數("慢線", 20)\n若 上穿(均線(收盤,快), 均線(收盤,慢)) 則 進場("多")';
r = X.compile(PS, B);
eq(r.params.map((p) => p.k + ':' + p.def), ['快:5', '慢:20'], '參數列表');
const r2 = X.compile(PS, B, { params: { 快: 10, 慢: 30 } });
assert.ok(same(r2.sig, { L: E.STRAT.ma2.build(B, { f: 10, s: 30 }).L }, ['L']), '覆寫參數後訊號改變'); pass++;
// 風控與平倉
r = X.compile('若 close > open 則 進場("多")\n若 close < open 則 平倉("多")\n出場("風控", 停損%=5, 停利%=10, 移動%=3, 最長持有=30)', B);
eq(r.errors, [], '風控腳本沒有錯誤');
eq(r.risk, { sl: 5, tp: 10, trail: 3, maxbars: 30 }, '風控'); assert.ok(r.sig.XL.some((x) => x) && !r.sig.XS.some((x) => x), '平倉只影響多單'); pass++;
// ③ 無未來資料：截短序列前綴相同
const Bs = {}; for (const k of ['ts', 'day', 'dayEnd', 'o', 'h', 'l', 'c', 'v']) Bs[k] = B[k].slice(0, 350); Bs.n = 350; Bs.tf = 'D';
const code = '若 close > highest(high,20)[1] 且 rsi(close,14) > 55 則 進場("多")\n若 close < lowest(low,20)[1] 則 進場("空")\n若 crossunder(close, ema(close,10)) 則 平倉("多")';
const ra = X.compile(code, B), rb = X.compile(code, Bs);
eq(ra.errors, [], '無未來資料腳本沒有錯誤');
for (const k of ['L', 'S', 'XL', 'XS']) for (let i = 0; i < 350; i++) assert.strictEqual(ra.sig[k][i], rb.sig[k][i], `${k}[${i}] 用到未來資料`);
pass++;
// ④ 錯誤訊息
r = X.compile('若 close > 則 進場("多")', B); assert.ok(r.errors.length === 1 && /第 1 行/.test(r.errors[0]), '語法錯誤有行號：' + r.errors[0]); pass++;
r = X.compile('x = 不存在的函式(close)', B); assert.ok(/不認得/.test(r.errors[0]), '未知函式：' + r.errors[0]); pass++;
r = X.compile('若 close[-1] > 0 則 進場("多")', B); assert.ok(/不能看未來/.test(r.errors[0]), '負索引被擋：' + r.errors[0]); pass++;
// ⑤ 積木 → 腳本 → 訊號
const rule = { name: '均線＋RSI', blocks: { le: { join: 'and', rows: [{ kind: 'cmp', op: 'up', a: { t: 'sma', n: 5 }, b: { t: 'sma', n: 20 } }, { kind: 'cmp', op: 'lt', a: { t: 'rsi', n: 14 }, b: { t: 'num', v: 70 } }] }, lx: { join: 'and', rows: [{ kind: 'cmp', op: 'dn', a: { t: 'sma', n: 5 }, b: { t: 'sma', n: 20 } }] } }, risk: { sl: 5, tp: 0, trail: 0, maxbars: 0 } };
const text = X.toScript(rule); r = X.compile(text, B);
eq(r.errors, [], '積木腳本沒有錯誤：' + text);
const up = E.STRAT.ma2.build(B, { f: 5, s: 20 }), rsi = E.I.rsi(B.c, 14);
for (let i = 0; i < B.n; i++) assert.strictEqual(r.sig.L[i], up.L[i] && rsi[i] < 70 ? 1 : 0, 'L[' + i + ']');
pass++;
for (let i = 0; i < B.n; i++) assert.strictEqual(r.sig.XL[i], up.S[i], 'XL[' + i + ']');
pass++;
eq(r.risk, { sl: 5 }, '積木風控');
// 事件條件：窗內才進場
const ev = [{ d: E.dayToStr(19100), t: 'fomc', lag: 0 }];
r = X.compile('若 event("fomc",2,1) 則 進場("多")', B, { events: ev });
const idx = Array.from(r.sig.L).map((x, i) => (x ? i : -1)).filter((i) => i >= 0); eq(idx, [98, 99, 100, 101], '事件窗內為真');
// 引擎：最長持有 N 根
const R = E.run(B, { L: Uint8Array.from(B.c, (_, i) => (i === 10 ? 1 : 0)), S: new Uint8Array(B.n), XL: new Uint8Array(B.n), XS: new Uint8Array(B.n) },
  { mode: 'both', capital: 1000000, sizeMode: 'units', sizeVal: 100, inst: Object.assign(E.instDefaults('stock'), { slip: 0 }), sl: 0, tp: 0, trail: 0, maxLoss: 0, maxBars: 7 }, 0, B.n - 1);
eq(R.trades.length, 1, '最長持有：一筆'); eq(R.trades[0].i1 - R.trades[0].i0, 8, '最長持有 7 根：第 7 根收盤判定、第 8 根開盤出場'); eq(R.trades[0].why, '持有逾時', '原因');
// ⑥ 內建策略 → 腳本：每支有對應寫法的都要與內建策略訊號完全相同（預設參數與改過的參數各驗一次）
{
  let n = 0;
  for (const st of E.STRATS) {
    const tweak = {}; (st.params || []).forEach((q) => { tweak[q.k] = q.def === q.min ? q.def + q.step : (q.k === 'rev' ? q.def : Math.max(q.min, Math.round((q.def * 0.8) / q.step) * q.step)); });
    for (const pr of [E.defaults(st.id), Object.assign(E.defaults(st.id), tweak)]) {
      const text = X.scriptFor(st.id, pr); if (!text) continue;
      const res = X.compile(text, B); assert.deepStrictEqual(res.errors, [], st.id + ' 腳本沒有錯誤：' + text);
      const ref = st.build(B, pr);
      for (const k of ['L', 'S']) for (let i = 0; i < B.n; i++) assert.strictEqual(res.sig[k][i], ref[k][i], `${st.id}.${k}[${i}] 腳本與內建策略不同（參數 ${JSON.stringify(pr)}）`);
      n++;
    }
  }
  assert.ok(n >= 24, '至少 12 支×2 組參數有腳本寫法：' + n); pass++;
  console.log('  內建策略↔腳本：' + n + ' 組一致');
}
{   // 籌碼函式：中英文別名等價、沒有籌碼資料時有看得懂的錯誤
  const a = X.compile('若 streak(chip("法人")) >= 3 則 進場("多")', B), b = X.compile('若 連買賣(籌碼("inst")) >= 3 則 進場("多")', B);
  eq(a.errors, [], '籌碼函式沒有錯誤'); eq(b.errors, [], '籌碼函式（中文別名）沒有錯誤'); assert.ok(same(a.sig, b.sig, ['L', 'S']) && a.sig.L.some((x) => x), '中英文籌碼函式等價且有訊號'); pass++;
  const B0 = randBars(50, 5); const c = X.compile('若 chip("外資") > 0 則 進場("多")', B0);
  assert.ok(c.errors.length === 1 && /沒有籌碼資料/.test(c.errors[0]), '沒籌碼時的錯誤：' + c.errors); pass++;
  const rule = { name: 't', blocks: { le: { join: 'and', rows: [{ kind: 'cmp', op: 'gt', a: { t: 'sinst' }, b: { t: 'num', v: 2 } }] }, lx: { join: 'and', rows: [] }, se: { join: 'and', rows: [] }, sx: { join: 'and', rows: [] } }, risk: {} };
  const d = X.compile(X.toScript(rule), B); eq(d.errors, [], '積木籌碼運算元可編譯'); assert.ok(d.sig.L.some((x) => x), '積木籌碼條件有訊號'); pass++;
}
console.log(`lab_expr_check：${pass} 項斷言全數通過`);
