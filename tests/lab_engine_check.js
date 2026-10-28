/* 交易練習室回測引擎的數字驗證（node tests/lab_engine_check.js）。
   用人工可以算出來的小序列，把損益、成本算到小數點；另外三個一致性檢查：
   ① 指標與 site/chart.js 的 KInd 同口徑  ② 序列截短重算，前綴訊號不變（沒用到未來資料）
   ③ 帳務恆等：最終權益 ＝ 本金 ＋ Σ每筆淨損益 ＋ 未平倉損益（全策略、隨機序列、多空模式、含成本） */
'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const E = require('../site/lab/engine.js');

let pass = 0;
const near = (a, b, tol, msg) => { assert.ok(Math.abs(a - b) <= (tol || 1e-6), `${msg || ''} 期望 ${b} 實際 ${a}`); pass++; };
const eq = (a, b, msg) => { assert.strictEqual(a, b, msg); pass++; };

function mkBars(rows, tf) {   // rows：[o,h,l,c] ；每根相隔一天
  const n = rows.length, B = { n, tf: tf || 'D', ts: new Float64Array(n), day: new Float64Array(n), dayEnd: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) };
  rows.forEach((r, i) => { B.o[i] = r[0]; B.h[i] = r[1]; B.l[i] = r[2]; B.c[i] = r[3]; B.day[i] = 19000 + i; B.dayEnd[i] = 19000 + i; B.ts[i] = (19000 + i) * 86400; B.v[i] = 1000; });
  return B;
}
const sigOf = (n, o) => { const s = E.mk(n); for (const k in o) o[k].forEach((i) => { s[k][i] = 1; }); return s; };
const base = (inst, extra) => Object.assign({ mode: 'both', capital: 1000000, sizeMode: 'units', sizeVal: 1000, inst, sl: 0, tp: 0, trail: 0, maxLoss: 0 }, extra || {});
const stock0 = () => Object.assign(E.instDefaults('stock'), { feeDisc: 1, feeMin: 0, slip: 0 });
const fut0 = () => Object.assign(E.instDefaults('fut'), { slip: 1 });

/* ---- A. 股票做多：手續費 0.1425% 雙邊、證交稅 0.3% 賣出，算到小數 ---- */
{
  const B = mkBars([[99, 99, 99, 99], [100, 100, 100, 100], [100, 101, 99, 100], [105, 106, 104, 105], [110, 111, 109, 110], [110, 110, 110, 110]]);
  const r = E.run(B, sigOf(6, { L: [1], XL: [3] }), base(stock0()), 0, 5);
  eq(r.trades.length, 1, 'A 筆數');
  const t = r.trades[0];
  eq(t.i0, 2, 'A 進場是訊號後下一根'); eq(t.i1, 4, 'A 出場是訊號後下一根');
  near(t.p0, 100, 1e-9, 'A 進價'); near(t.p1, 110, 1e-9, 'A 出價');
  near(t.gross, 10000, 1e-6, 'A 毛利'); near(t.costs, 142.5 + 156.75 + 330, 1e-6, 'A 成本'); near(t.pnl, 9370.75, 1e-6, 'A 淨損益');
  near(r.stats.net, 9370.75, 1e-6, 'A 淨損益＝權益差'); eq(r.stats.win, 100, 'A 勝率');
  near(r.stats.pf === Infinity ? 1e9 : r.stats.pf, 1e9, 1, 'A 無虧損 PF 為無限');
  near(r.eq[5], 1009370.75, 1e-6, 'A 最後權益');
}

/* ---- B. 台指期做空：每點 200、滑價 1 點、期交稅十萬分之二、手續費每口每邊 40 ---- */
{
  const B = mkBars([[20000, 20000, 20000, 20000], [20000, 20000, 20000, 20000], [20000, 20050, 19950, 20000], [19950, 19950, 19950, 19950], [19900, 19900, 19900, 19900], [19900, 19900, 19900, 19900]]);
  const r = E.run(B, sigOf(6, { S: [1], XS: [3] }), base(fut0(), { sizeVal: 2 }), 0, 5);
  const t = r.trades[0];
  near(t.p0, 19999, 1e-9, 'B 空單進價（賣出滑價低 1 點）'); near(t.p1, 19901, 1e-9, 'B 回補價（買進滑價高 1 點）');
  near(t.gross, 39200, 1e-6, 'B 毛利 98 點×200×2 口');
  near(t.costs, 80 + 80 + 19999 * 400 * 0.00002 + 19901 * 400 * 0.00002, 1e-6, 'B 成本'); near(t.pnl, 38720.8, 1e-6, 'B 淨損益');
}

/* ---- C. 停損／停利／跳空 ---- */
{
  // 進場 100，停損 5% → 95。下一根開 97 最低 94 → 以 95 成交
  const B = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [97, 98, 94, 96], [96, 96, 96, 96]]);
  let r = E.run(B, sigOf(5, { L: [1] }), base(stock0(), { sl: 5 }), 0, 4);
  near(r.trades[0].p1, 95, 1e-9, 'C 停損價成交'); eq(r.trades[0].why, '停損', 'C 原因'); near(r.trades[0].maeP, 5, 1e-9, 'C MAE%');
  // 跳空：開 93 → 以開盤價 93 成交
  const B2 = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [93, 94, 92, 93], [93, 93, 93, 93]]);
  r = E.run(B2, sigOf(5, { L: [1] }), base(stock0(), { sl: 5 }), 0, 4);
  near(r.trades[0].p1, 93, 1e-9, 'C 跳空停損以開盤價成交');
  // 停利 10%：下一根最高 112 → 110 成交；同根停損停利都碰到 → 停損先
  const B3 = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [101, 112, 99, 105], [105, 105, 105, 105]]);
  r = E.run(B3, sigOf(5, { L: [1] }), base(stock0(), { tp: 10 }), 0, 4);
  near(r.trades[0].p1, 110, 1e-9, 'C 停利價成交'); eq(r.trades[0].why, '停利', 'C 停利原因'); near(r.trades[0].mfeP, 10, 1e-9, 'C MFE%');
  const B4 = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [101, 112, 94, 105], [105, 105, 105, 105]]);
  r = E.run(B4, sigOf(5, { L: [1] }), base(stock0(), { tp: 10, sl: 5 }), 0, 4);
  eq(r.trades[0].why, '停損', 'C 同根兩者都碰到，保守算停損'); near(r.trades[0].p1, 95, 1e-9, 'C 同根停損價');
  // 移動停損 10%：最高到 120 → 線 108；下一根最低 107 → 108 成交
  const B5 = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 110, 100, 110], [110, 120, 110, 118], [118, 119, 107, 110], [110, 110, 110, 110]]);
  r = E.run(B5, sigOf(6, { L: [1] }), base(stock0(), { trail: 10 }), 0, 5);
  near(r.trades[0].p1, 108, 1e-9, 'C 移動停損價'); eq(r.trades[0].why, '移動停損', 'C 移動停損原因');
  // 最大單根虧損：權益 100 萬、1000 股，上限 1% ＝ 1 萬 ＝ 每股約 10 元；前收 100 → 約 90
  const B6 = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [99, 99, 85, 86], [86, 86, 86, 86]]);
  r = E.run(B6, sigOf(5, { L: [1] }), base(stock0(), { maxLoss: 1 }), 0, 4);
  near(r.trades[0].p1, 100 - 0.01 * (1000000 - 142.5) / 1000, 1e-9, 'C 最大單根虧損價（基準＝前一根收盤權益，已扣進場手續費）'); eq(r.trades[0].why, 'Close Position (Max intraday Loss)', 'C 標籤');
}

/* ---- D. 多空模式與反手：只做多時，空訊號只平倉不反手 ---- */
{
  const rows = [[100, 100, 100, 100], [100, 100, 100, 100], [100, 100, 100, 100], [105, 105, 105, 105], [110, 110, 110, 110], [112, 112, 112, 112], [108, 108, 108, 108]];
  const B = mkBars(rows);
  const sg = () => sigOf(7, { L: [1], S: [3] });
  let r = E.run(B, sg(), base(stock0(), { mode: 'long' }), 0, 6);
  eq(r.trades.length, 1, 'D 只做多：1 筆'); eq(r.trades[0].dir, 1, 'D 方向'); eq(r.trades[0].i1, 4, 'D 空訊號平倉在下一根開盤');
  r = E.run(B, sg(), base(stock0(), { mode: 'both' }), 0, 6);
  eq(r.trades.length, 1, 'D 多空：多單平倉'); eq(r.open && r.open.dir, -1, 'D 多空：反手開空（未平倉）'); eq(r.open.i0, 4, 'D 反手同一根開盤');
  r = E.run(B, sg(), base(stock0(), { mode: 'short' }), 0, 6);
  eq(r.trades.length, 0, 'D 只做空：多訊號不進場');
}

/* ---- E. 區間：訊號只在區間內生效，from 之前不進場 ---- */
{
  const B = mkBars([[100, 100, 100, 100], [101, 101, 101, 101], [102, 102, 102, 102], [103, 103, 103, 103], [104, 104, 104, 104], [105, 105, 105, 105]]);
  const r = E.run(B, sigOf(6, { L: [0, 3] }), base(stock0()), 2, 5);
  eq(r.trades.length, 0, 'E 未平倉'); eq(r.open.i0, 4, 'E from 之前的訊號被忽略，區間內第一個訊號的下一根進場');
  eq(r.eq.length, 4, 'E 權益長度'); near(r.eq[0], 1000000, 1e-9, 'E 起始權益');
}

/* ---- F. 事件遮罩 ---- */
{
  const B = mkBars(Array.from({ length: 30 }, () => [100, 100, 100, 100]));
  const ev = [{ d: E.dayToStr(19010), t: 'x' }];
  const m = E.eventWindowMask(B, ev, 2, 1);
  eq(m[7], 0, 'F 窗外'); eq(m[8], 1, 'F 窗內起點'); eq(m[10], 1, 'F 事件日'); eq(m[11], 1, 'F 窗內終點'); eq(m[12], 0, 'F 窗外後');
  // 事件濾網：窗內不進場 → 訊號 i=9（下一根 10 在窗內被擋）
  const sg = sigOf(30, { L: [9, 20] });
  const c = base(stock0(), { evt: { on: true, types: ['x'], mode: 'avoid', before: 2, after: 1 } });
  const r = E.runStrategy(B, { sig: sg }, c, 'All', ev);
  eq(r.open.i0, 21, 'F 窗內的訊號被擋，窗外的才進場');
}

/* ---- G. 週、月合成 ---- */
{
  // 19000 是 2022-01-08（星期六）；用真實日期構造：2024-01-01(一) ~ 2024-02-02
  const days = []; for (let d = E.strToDay('2024-01-01'); d <= E.strToDay('2024-02-05'); d++) { const wd = (d + 4) % 7; if (wd !== 0 && wd !== 6) days.push(d); }
  const B = mkBars(days.map((d, i) => [100 + i, 101 + i, 99 + i, 100.5 + i])); B.day = Float64Array.from(days); B.dayEnd = B.day.slice();
  const W = E.resample(B, 'W'); const M = E.resample(B, 'M');
  eq(W.n, 6, 'G 週數（1/1~2/5 共 6 週）'); eq(M.n, 2, 'G 月數');
  near(W.o[0], 100, 1e-9, 'G 週開'); near(W.c[0], 104.5, 1e-9, 'G 週收'); near(W.h[0], 105, 1e-9, 'G 週高'); near(W.l[0], 99, 1e-9, 'G 週低');
  eq(E.dayToStr(W.day[1]), '2024-01-08', 'G 第二週以週一標示');
  eq(E.dayToStr(M.day[1]), '2024-02-01', 'G 二月第一個交易日');
}

/* ---- H. 指標與 chart.js KInd 同口徑 ---- */
{
  const src = fs.readFileSync(path.join(__dirname, '../site/chart.js'), 'utf8');
  const g = { document: {}, window: {}, LightweightCharts: {} }; g.window = g; g.global = g;
  try { vm.runInNewContext(src, g, { filename: 'chart.js' }); } catch (e) { /* 載入時碰到 DOM 沒關係，KInd 在匯出前已定義 */ }
  const K = g.KInd;
  if (!K) { console.log('  ⚠ 無法載入 KInd，略過口徑比對'); } else {
    let s = 7; const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    const n = 300, c = [], h = [], l = []; let p = 100; for (let i = 0; i < n; i++) { p *= 1 + (rnd() - 0.5) * 0.04; c.push(p); h.push(p * (1 + rnd() * 0.01)); l.push(p * (1 - rnd() * 0.01)); }
    const cmp = (a, b, name) => { for (let i = 0; i < n; i++) { const x = a[i], y = b[i]; if ((y == null || Number.isNaN(y)) && (x == null || Number.isNaN(x))) continue; assert.ok(Math.abs(x - y) < 1e-9, `${name}[${i}] ${x} vs ${y}`); } pass++; };
    cmp(E.I.sma(c, 20), K.sma(c, 20), 'sma'); cmp(E.I.ema(c, 12), K.ema(c, 12), 'ema');
    const bb = E.I.boll(c, 20, 2), kb = K.boll(c, 20, 2); cmp(bb.up, kb.up, 'bollup'); cmp(bb.low, kb.low, 'bolllow');
    const m = E.I.macd(c, 12, 26, 9), km = K.macd(c, 12, 26, 9); cmp(m.dif, km.dif, 'dif'); cmp(m.dea, km.dea, 'dea'); cmp(m.osc, km.osc, 'osc');
    cmp(E.I.rsi(c, 14), K.rsi(c, 14), 'rsi');
    const kd = E.I.kd(h, l, c, 9, 3, 3), kk = K.kd(h, l, c, 9, 3, 3); cmp(kd.k, kk.k, 'K'); cmp(kd.d, kk.d, 'D');
  }
}

/* ---- I. 沒有未來資料：截短序列重算，前綴訊號必須完全相同（全部內建策略） ---- */
function randBars(n, seed) {
  let s = seed; const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  const rows = []; let p = 100;
  for (let i = 0; i < n; i++) { const o = p * (1 + (rnd() - 0.5) * 0.01); p = p * (1 + (rnd() - 0.48) * 0.05); const hi = Math.max(o, p) * (1 + rnd() * 0.01), lo = Math.min(o, p) * (1 - rnd() * 0.01); rows.push([o, hi, lo, p]); }
  return mkBars(rows);
}
{
  const Bf = randBars(500, 11), Bs = randBars(500, 11);
  const cut = 350; const sub = {}; for (const k of ['ts', 'day', 'dayEnd', 'o', 'h', 'l', 'c', 'v']) sub[k] = Bs[k].slice(0, cut); sub.n = cut; sub.tf = 'D';
  for (const st of E.STRATS) {
    const a = st.build(Bf, E.defaults(st.id)), b = st.build(sub, E.defaults(st.id));
    for (const k of ['L', 'S', 'XL', 'XS']) for (let i = 0; i < cut; i++) assert.strictEqual(a[k][i], b[k][i], `${st.id}.${k}[${i}] 用到了未來資料`);
    pass++;
  }
}

/* ---- J. 帳務恆等式：全策略 × 多空模式 × 隨機序列 × 含成本與停損 ---- */
{
  let cases = 0, trades = 0;
  for (const st of E.STRATS) for (const mode of ['long', 'short', 'both']) for (const kind of ['stock', 'fut']) {
    const B = randBars(400, 5 + cases);
    const inst = Object.assign(E.instDefaults(kind), kind === 'stock' ? {} : {});
    const cfg = { mode, capital: 1000000, sizeMode: kind === 'fut' ? 'units' : 'pct', sizeVal: kind === 'fut' ? 1 : 80, inst, sl: 4, tp: 9, trail: 6, maxLoss: 0.8 };
    const sig = st.build(B, E.defaults(st.id));
    const r = E.run(B, sig, cfg, 0, B.n - 1);
    const sum = r.trades.reduce((a, t) => a + t.pnl, 0) + (r.open ? r.open.pnl : 0);
    near(r.eq[r.eq.length - 1] - cfg.capital, sum, 1e-4, `${st.id}/${mode}/${kind} 權益差 ＝ Σ損益`);
    r.trades.forEach((t) => { assert.ok(t.i1 >= t.i0, '出場不早於進場'); assert.ok(t.mfe >= -1e-9 && t.mae >= -1e-9, 'MFE/MAE ≥ 0'); });
    cases++; trades += r.trades.length;
  }
  console.log(`  帳務恆等：${cases} 組、${trades} 筆交易`);
}

/* ---- K. 買進持有策略 ＝ 基準線（零成本時報酬相同） ---- */
{
  const B = randBars(200, 3);
  const inst = Object.assign(E.instDefaults('stock'), { feeRate: 0, taxRate: 0, slip: 0, feeMin: 0 });
  const r = E.run(B, E.STRAT.bnh.build(B), { mode: 'long', capital: 1000000, sizeMode: 'pct', sizeVal: 100, inst, sl: 0, tp: 0, trail: 0, maxLoss: 0 }, 0, 199);
  const sh = Math.floor(1000000 / B.o[1]);
  near(r.eq[199], 1000000 - sh * B.o[1] + sh * B.c[199], 1e-6, 'K 買進持有權益（整股）');
}

/* ---- L. 期間鍵 ---- */
{
  const days = []; for (let d = E.strToDay('2020-01-01'); d <= E.strToDay('2024-06-28'); d++) { const wd = (d + 4) % 7; if (wd !== 0 && wd !== 6) days.push(d); }
  const B = mkBars(days.map(() => [1, 1, 1, 1])); B.day = Float64Array.from(days); B.dayEnd = B.day.slice();
  const first = (k) => E.dayToStr(B.day[E.rangeFrom(B, k)]);
  eq(first('All'), '2020-01-01', 'L All'); eq(first('YTD'), '2024-01-01', 'L YTD'); eq(first('1M'), '2024-05-28', 'L 1M'); eq(first('3M'), '2024-03-28', 'L 3M');
  eq(first('6M'), '2023-12-28', 'L 6M'); eq(first('1Y'), '2023-06-28', 'L 1Y'); eq(first('5Y'), '2020-01-01', 'L 5Y 資料不足時從頭');
}


/* ---- M. 停損單進場、跳空、多空同掛（OCA）、加碼、收盤成交、盤中路徑 ---- */
{
  const flat = [100, 100, 100, 100];
  const mkS = (n, o) => { const x = sigOf(n, o.f || {}); x.Lk = 'stop'; x.Sk = 'stop'; x.Lp = new Float64Array(n); x.Sp = new Float64Array(n); return x; };
  // 買進停損單 105：下一根最高 106 → 以 105 成交；若開盤 108 跳空 → 以 108 成交；沒碰到 → 沒成交
  let B = mkBars([flat, flat, [100, 106, 99, 104], flat, flat]);
  let sg = mkS(5, { f: { L: [1] } }); sg.Lp[1] = 105;
  let r = E.run(B, sg, base(stock0()), 0, 4);
  near(r.open.p0, 105, 1e-9, 'M 停損買單成交價'); eq(r.open.i0, 2, 'M 成交那根');
  B = mkBars([flat, flat, [108, 109, 107, 108], flat, flat]); r = E.run(B, sg, base(stock0()), 0, 4);
  near(r.open.p0, 108, 1e-9, 'M 跳空越過掛單價，以開盤價成交');
  B = mkBars([flat, flat, [100, 104, 99, 103], flat, flat]); r = E.run(B, sg, base(stock0()), 0, 4);
  eq(r.open, null, 'M 沒碰到掛單價就取消'); eq(r.trades.length, 0, 'M 沒成交就沒有交易');
  // 多空同掛：上方買停、下方賣停，只成交先碰到的那一邊（這根跳空開低 → 賣）
  sg = mkS(5, { f: { L: [1], S: [1] } }); sg.Lp[1] = 105; sg.Sp[1] = 95;
  B = mkBars([flat, flat, [94, 106, 93, 100], flat, flat]); r = E.run(B, sg, base(stock0()), 0, 4);
  eq(r.open && r.open.dir, -1, 'M OCA：開盤已在賣停之下，賣單先成交'); near(r.open.p0, 94, 1e-9, 'M OCA 成交價（跳空以開盤價）');
  // 加碼：pyramiding 3，連續三根訊號 → 三口；出場一次全平 → 三筆
  B = mkBars(Array.from({ length: 8 }, (_, i) => [100 + i, 100 + i, 100 + i, 100 + i]));
  r = E.run(B, sigOf(8, { L: [1, 2, 3], XL: [5] }), base(stock0(), { pyramiding: 3, sizeVal: 100 }), 0, 7);
  eq(r.trades.length, 3, 'M 加碼三口各一筆'); eq(r.stats.maxLots, 300, 'M 最大持有股數');
  r = E.run(B, sigOf(8, { L: [1, 2, 3], XL: [5] }), base(stock0(), { pyramiding: 1, sizeVal: 100 }), 0, 7);
  eq(r.trades.length, 1, 'M 不加碼只有一口');
  // 收盤即成交：訊號當根收盤價成交
  B = mkBars([[100, 100, 100, 100], [100, 103, 99, 102], [103, 104, 102, 103], flat, flat]);
  r = E.run(B, sigOf(5, { L: [1] }), base(stock0(), { fillOn: 'close' }), 0, 4);
  near(r.open.p0, 102, 1e-9, 'M 收盤即成交價'); eq(r.open.i0, 1, 'M 收盤即成交在同一根');
  // 盤中路徑：開盤離高點較近 → 先高後低 → 停利先成交
  B = mkBars([flat, flat, flat, [100, 111, 88, 100], flat]);
  r = E.run(B, sigOf(5, { L: [1] }), base(stock0(), { tp: 10, sl: 5 }), 0, 4);
  eq(r.trades[0].why, '停利', 'M 路徑先高：停利先'); near(r.trades[0].p1, 110, 1e-9, 'M 停利價');
  B = mkBars([flat, flat, flat, [100, 111, 90, 100], flat]);
  r = E.run(B, sigOf(5, { L: [1] }), base(stock0(), { tp: 10, sl: 5 }), 0, 4);
  eq(r.trades[0].why, '停損', 'M 路徑先低：停損先'); near(r.trades[0].p1, 95, 1e-9, 'M 停損價');
}

/* ---- N. 績效摘要：多、空分開加總等於全部；月報酬 Sharpe／Sortino 可算 ---- */
{
  const B = randBars(900, 21);
  const inst = E.instDefaults('stock');
  const r = E.run(B, E.STRAT.ma2.build(B, E.defaults('ma2')), { mode: 'both', capital: 1000000, sizeMode: 'pct', sizeVal: 90, inst, sl: 0, tp: 0, trail: 0, maxLoss: 0 }, 0, B.n - 1);
  const s = r.stats;
  near(s.long.net + s.short.net, s.all.net, 1e-6, 'N 多＋空淨利＝全部'); eq(s.long.nClosed + s.short.nClosed, s.all.nClosed, 'N 筆數相加');
  near(s.all.net + s.all.openPL, s.net, 1e-4, 'N 已平倉淨利＋未平倉損益＝權益差');
  assert.ok(s.sharpe !== null && Number.isFinite(s.sharpe), 'N Sharpe 有值'); pass++;
  assert.ok(s.dd.length === r.eq.length && s.dd.every((x) => x <= 0), 'N 回撤序列皆 ≤ 0'); pass++;
}

// ⑦ 籌碼（2026-10-29）：全部用手算得出來的小資料
{
  const mkB = (n, day0) => { const B = { n, tf: 'D', ts: new Float64Array(n), day: new Float64Array(n), dayEnd: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n).fill(100) };
    for (let i = 0; i < n; i++) { B.day[i] = day0 + i; B.dayEnd[i] = day0 + i; B.ts[i] = (day0 + i) * 86400; B.o[i] = B.c[i] = B.h[i] = B.l[i] = 100; } return B; };
  const nan = NaN;
  // attachChip：起點之前一律 NaN，序列長度比日 K 短時尾端也是 NaN
  let D = mkB(6, 19002); E.attachChip(D, { s: { fn: 2 }, fn: [5, -3, 4] });
  assert.deepStrictEqual(Array.from(D.chip.fn).map((x) => (Number.isNaN(x) ? 'n' : x)), ['n', 'n', 5, -3, 4, 'n']); pass++;
  // 週 K 合成：流量加總、餘額取該週最後一天（19002 是星期一）
  D = mkB(10, 19002); D.day = Float64Array.from([19002, 19003, 19004, 19005, 19006, 19009, 19010, 19011, 19012, 19013]); D.dayEnd = D.day.slice();
  E.attachChip(D, { s: { fn: 0, mb: 0 }, fn: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], mb: [100, 101, 102, 103, 104, 105, 106, 107, 108, 109] });
  const W = E.resample(D, 'W');
  assert.deepStrictEqual([W.n, Array.from(W.chip.fn), Array.from(W.chip.mb)], [2, [15, 40], [104, 109]]); pass++;
  // 連買連賣、累計
  assert.deepStrictEqual(Array.from(E.streakOf(Float64Array.from([1, 2, -1, -2, -3, 0, 5]))), [1, 2, -1, -2, -3, 0, 1]); pass++;
  assert.deepStrictEqual(Array.from(E.csumOf(Float64Array.from([1, 2, 3, 4, 5]), 3)).map((x) => (Number.isNaN(x) ? 'n' : x)), ['n', 'n', 6, 9, 12]); pass++;
  // 券資比、當沖比
  let B = mkB(3, 19002); B.chip = { sb: Float64Array.from([10, 20, nan]), mb: Float64Array.from([100, 0, 100]), dt: Float64Array.from([20, 30, 40]), fn: Float64Array.from([1, 1, 1]), tr: Float64Array.from([1, 1, 1]), dl: Float64Array.from([1, 1, 1]) };
  assert.deepStrictEqual(Array.from(E.chipSeries(B, 'ratio')).map((x) => (Number.isNaN(x) ? 'n' : x)), [10, 'n', 'n']); pass++;
  assert.deepStrictEqual(Array.from(E.chipSeries(B, 'dtr')), [20, 30, 40]); pass++;
  assert.deepStrictEqual(Array.from(E.chipSeries(B, 'inst')), [3, 3, 3]); pass++;
  // 法人連買：合計 + - 規律  inst = [1,1,1,-1,-1,-1,1,1] → 連買 3 根在 i=2、連賣 3 根在 i=5
  B = mkB(8, 19002); B.chip = { fn: Float64Array.from([1, 1, 1, -1, -1, -1, 1, 1]), tr: new Float64Array(8), dl: new Float64Array(8) };
  let r = E.STRAT.instbuy.build(B, { n: 3, m: 3 });
  assert.deepStrictEqual([Array.from(r.L).indexOf(1), Array.from(r.S).indexOf(1), r.L.reduce((a, b) => a + b), r.S.reduce((a, b) => a + b)], [2, 5, 1, 1]); pass++;
  // 沒有籌碼資料：所有籌碼策略都不出訊號（不能丟錯、不能亂出）
  const B0 = mkB(30, 19002);
  for (const st of E.STRATS.filter((x) => x.needs === 'chip')) { const q = st.build(B0, E.defaults(st.id)); assert.ok(!q.L.some((x) => x) && !q.S.some((x) => x), st.id + ' 沒有籌碼時不出訊號'); pass++; }
  // 集保大戶：資料不足的策略即使有籌碼也不出訊號
  assert.ok(E.STRAT.holders.unavail && !E.STRAT.holders.build(B, {}).L.some((x) => x)); pass++;
  // 突破＋法人買超：價格突破那天法人賣超 → 不進；買超 → 進
  const mkBrk = (instVal) => { const b = mkB(8, 19002); for (let i = 0; i < 8; i++) { b.c[i] = b.o[i] = b.h[i] = b.l[i] = i < 6 ? 100 : (i === 6 ? 110 : 111); } b.chip = { fn: Float64Array.from({ length: 8 }, (_, i) => (i === 6 ? instVal : 0)), tr: new Float64Array(8), dl: new Float64Array(8) }; return b; };
  assert.deepStrictEqual([Array.from(E.STRAT.brkinst.build(mkBrk(-5), { n: 5, m: 3 }).L).indexOf(1), Array.from(E.STRAT.brkinst.build(mkBrk(5), { n: 5, m: 3 }).L).indexOf(1)], [-1, 6]); pass++;
  // 融資策略：餘額 10 根內減 5%（>3%）且收盤站上均線 → 做多；只在剛成立那一根發訊號
  const bm = mkB(40, 19002); for (let i = 0; i < 40; i++) { bm.c[i] = bm.o[i] = bm.h[i] = bm.l[i] = i < 25 ? 100 : 110; }
  bm.chip = { mb: Float64Array.from({ length: 40 }, (_, i) => (i < 25 ? 1000 : 940)) };
  r = E.STRAT.margin.build(bm, { n: 10, x: 3, y: 5 });
  assert.deepStrictEqual(Array.from(r.L).map((x, i) => (x ? i : -1)).filter((i) => i >= 0), [25]); pass++;
}

/* ---- Z. 2026-10-29 實測回報的引擎 P0（先寫成會失敗的測試，修好才通過） ---- */
{   // Z1 股票空單不能虧超過本金：預設維持率 130% 先強平；關掉追繳也要在權益 ≤ 0 時強平並停止交易
  const px = [100, 100, 100, 120, 150, 160, 200, 250, 300, 300, 300];
  const B = mkBars(px.map((v) => [v, v, v, v]));
  const cfgS = (extra) => Object.assign(base(stock0(), { mode: 'short', sizeMode: 'pct', sizeVal: 100 }), extra || {});
  let r = E.run(B, sigOf(11, { S: [0, 9] }), cfgS(), 0, 10);
  assert.ok(r.calls.length >= 1 && /追繳/.test(r.calls[0].why), 'Z1 預設維持率 130% 要強平'); pass++;
  assert.ok(r.stats.ret > -100, 'Z1 虧損不超過本金'); pass++;
  r = E.run(B, sigOf(11, { S: [0, 9] }), cfgS({ marginCall: 0 }), 0, 10);
  assert.ok(r.calls.some((x) => /歸零/.test(x.why)), 'Z1 權益歸零要強平'); pass++;
  eq(r.trades.length, 1, 'Z1 歸零後停止交易，不再開新單'); eq(r.open, null, 'Z1 無剩餘部位');
}
{   // Z2 事件窗「進入就平倉」要在窗口第一根的開盤出場（原本晚一天）
  const B = mkBars(Array.from({ length: 10 }, (_, i) => { const v = 100 + i; return [v, v, v, v]; }));
  const mask = new Uint8Array(10); mask[5] = 1; mask[6] = 1;
  const r = E.run(B, sigOf(10, { L: [0] }), base(stock0(), { mode: 'long', sizeMode: 'pct', sizeVal: 100, exitMask: mask }), 0, 9);
  eq(r.trades[0].i1, 5, 'Z2 窗口第一根(5)開盤平倉');
}
{   // Z3 反手單：進場原因是「做多／做空訊號」，不是「反向訊號」
  const B = mkBars(Array.from({ length: 8 }, (_, i) => { const v = 100 + i; return [v, v, v, v]; }));
  const r = E.run(B, sigOf(8, { L: [0], S: [3] }), base(stock0(), { mode: 'both', sizeMode: 'pct', sizeVal: 100 }), 0, 7);
  eq(r.trades[0].why, '反向訊號', 'Z3 舊單出場原因'); eq(r.opens[0].entryWhy, '做空訊號', 'Z3 反手新單進場原因');
}
{   // Z4 借券費：空單 10 日、年化 3.65% → 每日 0.01%，持有市值 100 萬 × 0.01% × 天數
  const B = mkBars(Array.from({ length: 12 }, () => [100, 100, 100, 100]));
  const inst = Object.assign(stock0(), { borrowFee: 3.65, taxRate: 0, feeRate: 0 });
  const r = E.run(B, sigOf(12, { S: [0], XS: [10] }), base(inst, { mode: 'short', sizeMode: 'units', sizeVal: 10000 }), 0, 11);
  near(r.trades[0].costs, 1000000 * 0.0001 * 10, 1e-6, 'Z4 借券費 10 日 = 1,000 元'); // 第 1~10 根持有
}
{   // Z5 期貨：權益低於維持保證金強平，權益歸零停止；原始保證金不足不能下單
  const px = [10000, 10000, 9800, 9500, 9000, 8000, 8000];
  const B = mkBars(px.map((v) => [v, v, v, v]));
  const inst = Object.assign(E.instDefaults('fut'), { slip: 0, rollCost: 0 });
  const cfg = base(inst, { mode: 'long', capital: 500000, sizeMode: 'units', sizeVal: 1 });
  const r = E.run(B, sigOf(7, { L: [0] }), cfg, 0, 6);
  assert.ok(r.calls.length >= 1 && /追繳|歸零/.test(r.calls[0].why), 'Z5 期貨要強平'); pass++;
  const cfg2 = base(inst, { mode: 'long', capital: 100000, sizeMode: 'units', sizeVal: 1 });   // 10 萬 < 1 口原始保證金（10000×200×10%＝20 萬）
  eq(E.run(B, sigOf(7, { L: [0] }), cfg2, 0, 6).trades.length + (E.run(B, sigOf(7, { L: [0] }), cfg2, 0, 6).opens.length), 0, 'Z5 保證金不足不能下單');
}
{   // Z6 停損／停利／移動停損（點數）
  const B = mkBars([[100, 100, 100, 100], [100, 100, 100, 100], [100, 112, 100, 110], [110, 110, 94, 95], [95, 95, 95, 95]]);
  const r = E.run(B, sigOf(5, { L: [0] }), base(stock0(), { mode: 'long', sizeMode: 'units', sizeVal: 1, slPts: 5 }), 0, 4);
  near(r.trades[0].p1, 95, 1e-9, 'Z6 停損 5 點'); 
  const r2 = E.run(B, sigOf(5, { L: [0] }), base(stock0(), { mode: 'long', sizeMode: 'units', sizeVal: 1, tpPts: 10 }), 0, 4);
  near(r2.trades[0].p1, 110, 1e-9, 'Z6 停利 10 點');
  const r3 = E.run(B, sigOf(5, { L: [0] }), base(stock0(), { mode: 'long', sizeMode: 'units', sizeVal: 1, trailPts: 6, trailStart: 10 }), 0, 4);
  near(r3.trades[0].p1, 106, 1e-9, 'Z6 移動停損：賺 ≥ 10 點啟動，最高 112 退 6 點 = 106');
}

console.log(`lab_engine_check：${pass} 項斷言全數通過`);
