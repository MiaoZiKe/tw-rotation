/* 標準策略驗證（node tests/lab_standard_check.js）：
   ① 每組一個「手算可驗證」的小案例（成本設 0、開高低收同價，進出場價與 K 棒位置可用紙筆算出來；參數縮小到能手算，預設值寫在 site/lab/standard_defs.js）
   ② 積木寫法與腳本寫法的訊號、風控完全相同（有積木的 8 組）
   ③ 結果檔 site/lab/standard_results.json 存在、10 組齊全、年度報酬與回撤合理 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const E = require('../site/lab/engine.js');
const X = require('../site/lab/expr.js');
const STD = require('../site/lab/standard_defs.js');
let pass = 0;
const near = (a, b, tol, m) => { assert.ok(Math.abs(a - b) <= (tol || 1e-6), `${m || ''} 期望 ${b} 實際 ${a}`); pass++; };
const eq = (a, b, m) => { assert.deepStrictEqual(a, b, m); pass++; };
const def = (id) => STD.DEFS.find((d) => d.id === id);

/** 開=高=低=收 的日 K（日期連續日數，預設）；days 可自訂（週 K 案例要真的星期） */
function bars(c, o) {
  o = o || {}; const n = c.length;
  const B = { n, tf: 'D', ts: new Float64Array(n), day: new Float64Array(n), dayEnd: new Float64Array(n), o: Float64Array.from(c), h: Float64Array.from(c), l: Float64Array.from(c), c: Float64Array.from(c), v: Float64Array.from(o.v || c.map(() => 1000)) };
  for (let i = 0; i < n; i++) { B.day[i] = o.days ? o.days[i] : 19000 + i; B.dayEnd[i] = B.day[i]; B.ts[i] = B.day[i] * 86400; }
  if (o.chip) B.chip = o.chip;
  return B;
}
const stock0 = () => Object.assign(E.instDefaults('stock'), { feeDisc: 1, feeMin: 0, slip: 0, feeRate: 0, taxRate: 0 });
function trial(id, B, params, inst, cfgx) {
  const d = def(id), res = X.compile(d.script, B, { events: [], params: params || {} });
  assert.deepStrictEqual(res.errors, [], id + ' 編譯錯誤'); pass++;
  const cfg = Object.assign({ mode: 'long', capital: 1000000, sizeMode: 'pct', sizeVal: 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: inst || stock0() }, cfgx || {});
  return E.runStrategy(B, { sig: res.sig, risk: res.risk }, cfg, 'All', null);
}
function one(r, i0, i1, p0, p1, m) {
  eq(r.trades.length + r.opens.length, 1, m + ' 只有一筆交易'); const t = r.trades[0];
  eq([t.i0, t.i1], [i0, i1], m + ' 進出場 K 棒位置'); near(t.p0, p0, 1e-9, m + ' 進場價'); near(t.p1, p1, 1e-9, m + ' 出場價');
  return t;
}

/* 1 雙均線：快 2、慢 3。收盤 [10,10,10,8,12,14,6,5,5,5]
   MA2 = 9,10,13,10,5.5…；MA3 = 9.33,10,11.33,10.67,8.33…
   第 5 根 MA2(13) 上穿 MA3(11.33)（第 4 根兩者都是 10，不算穿越）→ 第 6 根開盤 6 買進；第 6 根 MA2(10) 下穿 MA3(10.67) → 第 7 根開盤 5 賣出 → −16.67% */
{ const r = trial('std_ma', bars([10, 10, 10, 8, 12, 14, 6, 5, 5, 5]), { 快: 2, 慢: 3, 停損值: 0 });
  near(one(r, 6, 7, 6, 5, '1').pnlP, -100 / 6, 1e-6, '1 報酬'); }

/* 2 MACD：快 2、慢 3、訊號 2（EMA 係數 2/3、1/2、2/3）。前 6 根 10，第 6 根起 20。
   第 6 根 DIF = 16.667−15 = 1.667、DEA = 1.111（前一根都是 0）→ DIF 上穿且在零軸上；第 8 根 DIF 0.880 < DEA 1.019（前一根 1.389 > 1.296）→ 下穿
   進場在第 7 根開盤、出場在第 9 根開盤，價格都是 20 */
{ const c = [10, 10, 10, 10, 10, 10, 20, 20, 20, 20, 20, 20];
  one(trial('std_macd', bars(c), { 快: 2, 慢: 3, 訊: 2, 停損值: 0 }), 7, 9, 20, 20, '2'); }

/* 3 Supertrend：ATR 週期 1、倍數 1（ATR＝真實區間）。收盤 [10,10,10,8,8,8,11,11,11,7,7,7]（開高低收同價，真實區間＝與前收之差）
   第 3 根收 8 < 下軌 10 → 翻空；第 6 根收 11 > 上軌 8 → 翻多（訊號）→ 第 7 根開盤 11 買進；第 9 根收 7 < 下軌 11 → 翻空 → 第 10 根開盤 7 賣出 → −36.36% */
{ const t = one(trial('std_st', bars([10, 10, 10, 8, 8, 8, 11, 11, 11, 7, 7, 7]), { 期: 1, 倍: 1 }), 7, 10, 11, 7, '3');
  near(t.pnlP, -400 / 11, 1e-6, '3 報酬'); }

/* 4 KD+RSI：KD 週期 2、RSI 週期 2，收盤 [10,11,10,11,11,9,9,9]
   第 3 根：K = 62.96 上穿 D = 55.56，K > 50，RSI = 75 > 50 → 第 4 根開盤 11 買進
   第 5 根：K = 39.1 下穿 D = 50.8（RSI 也掉到 15）→ 第 6 根開盤 9 賣出 */
one(trial('std_kdrsi', bars([10, 11, 10, 11, 11, 9, 9, 9]), { kn: 2, rn: 2, 停損值: 0 }), 4, 6, 11, 9, '4');

/* 5 唐奇安＋量增：突破 3 日、出場 2 日、均量 3 日。收盤 [10,10,10,10,12,12,12,9,9,9]，量第 4 根 300 其餘 100
   第 4 根收 12 > 前 3 日高 10，量 300 > 均量 166.7 → 第 5 根開盤 12 買進；第 7 根收 9 < 前 2 日低 12 → 第 8 根開盤 9 賣出 → −25% */
{ const t = one(trial('std_brk', bars([10, 10, 10, 10, 12, 12, 12, 9, 9, 9], { v: [100, 100, 100, 100, 300, 100, 100, 100, 100, 100] }), { 進: 3, 出: 2, 量: 3, 停損值: 0 }), 5, 8, 12, 9, '5');
  near(t.pnlP, -25, 1e-9, '5 報酬'); }

/* 6 布林＋RSI：布林 2 期 1 倍（母體標準差 → 下軌＝兩日最低、中軌＝兩日平均）、RSI 2 期 < 40。收盤 [12,10,8,6,7,8,7,9,9]
   第 4 根收 7 站上下軌 6（前一根 6 ≤ 下軌 6），RSI = 33.3 < 40 → 第 5 根開盤 8 買進；
   第 7 根收 9 站上中軌 8（前一根 7 ≤ 7.5）→ 第 8 根開盤 9 賣出 → +12.5%（第 7 根也穿下軌但 RSI 76，且已持倉） */
{ const t = one(trial('std_revert', bars([12, 10, 8, 6, 7, 8, 7, 9, 9]), { 週: 2, 倍: 1, 低: 40, rn: 2, 停損值: 0, 持有: 20 }), 5, 8, 8, 9, '6');
  near(t.pnlP, 12.5, 1e-9, '6 報酬'); }

/* 7 週 K 定方向＋日 K 進場：週均線 2 週、日均線 2 日。每週 5 個交易日（週一起算），收盤：
   第 1 週 10、第 2 週 12、第 3 週 14；第 4 週 14,13,15,15,15（整數，避免浮點誤差）；第 5 週 16,10,10,10,10
   週均線只用「收完的週」：第 4 週起 = (12+14)/2 = 13、比 5 根前的 11 高，多頭成立；日線 2 日均線被收盤上穿且收盤 > 週均線時進場 */
{ const c = [10, 10, 10, 10, 10, 12, 12, 12, 12, 12, 14, 14, 14, 14, 14, 14, 13, 15, 15, 15, 16, 10, 10, 10, 10];
  const days = c.map((_, i) => 19723 + 7 * Math.floor(i / 5) + (i % 5));       // 19723 是 2024-01-01（星期一）
  const t = one(trial('std_mtf', bars(c, { days }), { 週數: 2, 日數: 2, 停損值: 0 }), 18, 22, 15, 10, '7');
  near(t.pnlP, -100 / 3, 1e-6, '7 報酬'); }

/* 8 投信連買：投信買賣超 [+,+,+,+,−,−,−,−,+]，連買 3 日（第 2 根）進場 → 第 3 根開盤 11；連賣 3 日（第 6 根）出場 → 第 7 根開盤 9 */
{ const tr = Float64Array.from([1, 1, 1, 1, -1, -1, -1, -1, 1]);
  one(trial('std_trust', bars([10, 10, 10, 11, 11, 12, 12, 9, 9], { chip: { tr } }), { 停損值: 0 }), 3, 7, 11, 9, '8'); }

/* 9 營收動能＋新高：營收動能門檻 110、新高 3 日、出場 2 日線。營收動能 [100×3, 120…]，收盤 [10,10,10,12,12,12,9,9,9]
   第 3 根 營收 120 ≥ 110 且收 12 > 前 3 日高 10 → 第 4 根開盤 12 買進；第 6 根收 9 < 2 日均 10.5 → 第 7 根開盤 9 賣出 */
{ const rv = Float64Array.from([100, 100, 100, 120, 120, 120, 120, 120, 120]);
  one(trial('std_rev', bars([10, 10, 10, 12, 12, 12, 9, 9, 9], { chip: { rv } }), { 門檻: 110, 高: 3, 線: 2, 停損值: 0 }), 4, 7, 12, 9, '9'); }

/* 10 台指期 200 日線（縮成 3 日）：收盤 [10,10,10,12,12,9,9,9]，3 日均 = 10,10.67,11.33,11,10,9
   第 3 根收 12 站上 10.67（前一根 10 ≤ 10）→ 第 4 根開盤 12 買 1 口；第 5 根收 9 跌破 11（前一根 12 ≥ 11.33）→ 第 6 根開盤 9 賣出；毛損 (9−12)×200 = −600 */
{ const inst = Object.assign(E.instDefaults('fut'), { slip: 0, rollCost: 0, futFee: 0, futTax: 0 });
  const r = trial('std_tx200', bars([10, 10, 10, 12, 12, 9, 9, 9]), { 週: 3 }, inst, { capital: 5000000, sizeMode: 'units', sizeVal: 1 });
  near(one(r, 4, 6, 12, 9, '10').gross, -600, 1e-6, '10 毛損'); }

/* 11 M1216：法人 2 日（縮小）買超占成交量 > 1%、營收年增 > 20%、公布後 ≤ 5 日、最長持有 3 根（停損與移動停損關掉）
   法人買賣超（外資）[0,0,0,5,5,0,…]、成交量每根 100：第 3 根 (0+5)/200 = 2.5% > 1%，營收年增 30%、公布後第 0 天 → 訊號 → 第 4 根開盤 12 買進
   持有滿 3 根（第 7 根收盤判斷）→ 第 8 根開盤 9 賣出 → −25% */
{ const chip = { fn: Float64Array.from([0, 0, 0, 5, 5, 0, 0, 0, 0, 0]), tr: new Float64Array(10), dl: new Float64Array(10), ry: Float64Array.from([0, 0, 0, 30, 30, 30, 30, 30, 30, 30]), ra: Float64Array.from([99, 99, 99, 0, 1, 2, 3, 4, 5, 6]) };
  const B = bars([10, 10, 10, 12, 12, 12, 12, 12, 9, 9], { chip, v: new Array(10).fill(100) });
  const d = def('std_m1216'), res = X.compile(d.script.replace('chip_pct("法人",5)', 'chip_pct("法人",2)'), B, { events: [], params: { 停損值: 0, 移動值: 0, 持有: 3 } });
  eq(res.errors, [], '11 編譯'); const cfg = { mode: 'long', capital: 1000000, sizeMode: 'pct', sizeVal: 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: stock0() };
  const t = one(E.runStrategy(B, { sig: res.sig, risk: res.risk }, cfg, 'All', null), 4, 8, 12, 9, '11');
  near(t.pnlP, -25, 1e-9, '11 報酬');
  const B2 = bars([10, 10, 10, 12, 12, 12, 12, 12, 9, 9], { v: new Array(10).fill(100), chip: Object.assign({}, chip, { ra: Float64Array.from([99, 99, 99, 6, 7, 8, 9, 10, 11, 12]) }) });   // 公布後第 6 天以後才符合 → 不進場
  const r2 = X.compile(d.script.replace('chip_pct("法人",5)', 'chip_pct("法人",2)'), B2, { events: [], params: { 停損值: 0, 移動值: 0, 持有: 3 } });
  assert.ok(r2.sig === null && /沒有任何進場訊號/.test(r2.errors[0]), '11 公布後超過 5 個交易日不會有任何進場訊號'); pass++; }

/* 12 M1148：外資 2 日（縮小）占成交量 > 0.5% 且投信同期買超、營收年增 > 20%、公布後 ≤ 3 日、停損 4.9%
   第 3 根：外資 (0+5)/200 = 2.5% > 0.5%、投信 2 > 0 → 訊號 → 第 4 根開盤 12 買進；第 5 根開盤跳空 11 低於停損價 11.412 → 以開盤價 11 賣出 → −8.33% */
{ const chip = { fn: Float64Array.from([0, 0, 0, 5, 0, 0, 0, 0, 0]), tr: Float64Array.from([0, 0, 0, 2, 2, 0, 0, 0, 0]), dl: new Float64Array(9), ry: Float64Array.from([0, 0, 0, 30, 30, 30, 30, 30, 30]), ra: Float64Array.from([99, 99, 99, 0, 1, 2, 3, 4, 5]) };
  const B = bars([10, 10, 10, 12, 12, 11, 11, 11, 11], { chip, v: new Array(9).fill(100) });
  const d = def('std_m1148'), res = X.compile(d.script.replace('chip_pct("外資",10)', 'chip_pct("外資",2)').replace('chip_pct("投信",10)', 'chip_pct("投信",2)'), B, { events: [] });
  eq(res.errors, [], '12 編譯'); const cfg = { mode: 'long', capital: 1000000, sizeMode: 'pct', sizeVal: 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: stock0() };
  const t = one(E.runStrategy(B, { sig: res.sig, risk: res.risk }, cfg, 'All', null), 4, 5, 12, 11, '12');
  near(t.pnlP, -100 / 12, 1e-6, '12 報酬'); }

/* ② 積木＝腳本 */
const DIR = fs.existsSync(path.join(__dirname, '../site/data/lab/index.json')) ? path.join(__dirname, '../site/data/lab') : path.join(__dirname, '../site/lab/sample');
const readJ = (rel) => JSON.parse(fs.readFileSync(path.join(DIR, rel), 'utf8'));
const IDX = readJ('index.json').items;
function series(code) { const j = readJ('s/' + code + '.json'), D = E.decode(j.d, 'D'); if ((IDX.find((x) => x.c === code) || {}).ch) E.attachChip(D, readJ('c/' + code + '.json')); E.attachUS(D, readJ('us.json')); return D; }
const blank = () => ({ name: '', blocks: { le: { join: 'and', rows: [] }, lx: { join: 'and', rows: [] }, se: { join: 'and', rows: [] }, sx: { join: 'and', rows: [] } }, risk: {} });
let nb = 0;
for (const d of STD.DEFS) {
  if (!d.blocks) continue; nb++;
  const code = d.needs ? '2330' : (d.headline.sym === 'TX' ? 'TX' : 'TAIEX'), B = series(code);
  const a = X.compile(d.script, B, { events: [] }), rule = STD.toRule(d, blank), b = X.compile(X.toScript(rule), B, { events: [] });
  eq(a.errors, [], d.id + ' 腳本無錯'); eq(b.errors, [], d.id + ' 積木無錯');
  for (const k of ['L', 'XL', 'S', 'XS']) { assert.ok(a.sig[k].every((x, i) => x === b.sig[k][i]), d.id + ' 積木與腳本的 ' + k + ' 訊號相同'); pass++; }
  assert.ok(a.sig.L.some((x) => x), d.id + ' 在真實資料上至少有一次進場訊號'); pass++;
  const z = { sl: 0, tp: 0, trail: 0, maxbars: 0 };
  eq(Object.assign({}, z, a.risk), Object.assign({}, z, d.risk), d.id + ' 風控相同（腳本 vs 預設）');
  eq(Object.assign({}, z, b.risk), Object.assign({}, z, d.risk), d.id + ' 積木風控');
}
eq(nb, 10, '有積木的組數');

/* ③ 結果檔 */
{ const f = path.join(__dirname, '../site/lab/standard_results.json'); assert.ok(fs.existsSync(f), '結果檔存在'); pass++;
  const R = JSON.parse(fs.readFileSync(f, 'utf8'));
  eq(Object.keys(R.strategies).length, 12, '12 組齊全（10 組標準＋2 組競賽冠軍）');
  for (const d of STD.DEFS) {
    const s = R.strategies[d.id], h = s.runs.find((r) => r.sym === d.headline.sym && r.tf === d.headline.tf);
    assert.ok(h && h.n > 0, d.id + ' 有主要回測'); pass++;
    assert.ok(h.yr.length >= 5 && h.mdd >= 0 && h.mdd <= 100, d.id + ' 年度與回撤合理'); pass++;
  } }
console.log(`lab_standard_check：${pass} 項斷言全數通過`);
