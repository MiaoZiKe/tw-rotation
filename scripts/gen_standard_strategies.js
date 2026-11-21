#!/usr/bin/env node
/* ============================================================================
   產生「標準策略」的預設回測結果 → site/lab/standard_results.json（2026-10-29 建）
   用法：node scripts/gen_standard_strategies.js [--data <資料夾>] [--out <輸出檔>]
   · 資料：預設先找 site/data/lab/（管線每天重算的完整資料），沒有才用 site/lab/sample/（預覽分支 commit 的小樣本）。
   · 回測：直接呼叫 site/lab/engine.js 與 expr.js —— 和網頁上「點範本 → 回測」是同一套程式，數字不是手寫的。
   · 統一設定：只做多、全部資金、訊號收盤後產生→下一根開盤成交、不加碼、成本用站內預設（手續費 0.1425% 不打折、證交稅 0.3%、滑價 0.05%；
     台指期手續費 40 元／口、期交稅 0.002%、滑價 1 點）。期間＝該標的資料全部（和網頁預設「全部」相同）。
   · 接進每日管線：pipeline/build_payload.py 在交易練習室資料產完後呼叫本腳本，數字每天更新。失敗只影響標準策略卡片的數字。
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const E = require(path.join(ROOT, 'site/lab/engine.js'));
const X = require(path.join(ROOT, 'site/lab/expr.js'));
const STD = require(path.join(ROOT, 'site/lab/standard_defs.js'));

const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const OUT = arg('--out') || path.join(ROOT, 'site/lab/standard_results.json');
const cand = [arg('--data'), path.join(ROOT, 'site/data/lab'), path.join(ROOT, 'site/lab/sample')].filter(Boolean);
const DIR = cand.find((d) => fs.existsSync(path.join(d, 'index.json')));
if (!DIR) { console.error('找不到交易練習室資料（site/data/lab 或 site/lab/sample）'); process.exit(1); }
const SOURCE = DIR.includes('sample') ? 'sample' : 'lab';
const readJ = (rel) => { const f = path.join(DIR, rel); return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : null; };
const IDX = readJ('index.json');
const ITEM = Object.fromEntries(IDX.items.map((x) => [x.c, x]));

/* ---------------------------------------------------------------- 資料（和 lab.js 的 loadSeries 同一套解碼） */
const CACHE = {};
function series(code, tf) {
  const k = code + '|' + tf; if (k in CACHE) return CACHE[k];
  let B = null;
  if (tf === '60') {
    const j = readJ('s/' + code + '.60.json'); if (j) B = E.decode(j.d, '60');
  } else {
    const j = readJ('s/' + code + '.json');
    if (j) {
      const D = E.decode(j.d, 'D');
      if (ITEM[code] && ITEM[code].ch) E.attachChip(D, readJ('c/' + code + '.json'));
      E.attachUS(D, readJ('us.json'));
      B = E.resample(D, tf); B.name = j.n; B.kind = j.k;
    }
  }
  CACHE[k] = B; return B;
}

/* ---------------------------------------------------------------- 單次回測 → 摘要 */
const r2 = (x) => (x == null || !Number.isFinite(x) ? null : Math.round(x * 100) / 100);
function yearly(B, from, eq, bh, cap0) {
  const out = {}; let ps = cap0, pb = cap0, y0 = null, ls = cap0, lb = cap0;
  const yr = (i) => new Date(B.dayEnd[from + i] * 86400000).getUTCFullYear();
  const rows = [];
  for (let i = 0; i < eq.length; i++) {
    const y = yr(i);
    if (y0 !== null && y !== y0) { rows.push([y0, (ls / ps - 1) * 100, (lb / pb - 1) * 100]); ps = ls; pb = lb; }
    y0 = y; ls = eq[i]; lb = bh[i];
  }
  if (y0 !== null) rows.push([y0, (ls / ps - 1) * 100, (lb / pb - 1) * 100]);
  return rows.map((r) => [r[0], r2(r[1]), r2(r[2])]);
}
function maxDD(arr) { let pk = -Infinity, m = 0; for (const v of arr) { if (v > pk) pk = v; const d = pk > 0 ? (pk - v) / pk : 0; if (d > m) m = d; } return m * 100; }

function runOne(def, code, tf, keepTrades) {
  const B = series(code, tf); if (!B) return { skip: '沒有這個週期的資料' };
  const it = ITEM[code], kind = it.k, fut = kind === 'fut';
  if (def.needs === 'chip' && !(B.chip && B.chip.tr)) return { skip: '沒有籌碼／月營收資料' };
  let res;
  try { res = X.compile(def.script, B, { events: [], params: {} }); } catch (e) { return { skip: String(e.message || e) }; }
  if (!res.sig) return { skip: res.errors[0] || '編譯失敗' };
  const cap = fut ? STD.CAPITAL.fut : STD.CAPITAL.stock;
  const cfg = { mode: 'long', capital: cap, sizeMode: fut ? 'units' : 'pct', sizeVal: fut ? 1 : 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: E.instDefaults(kind) };
  const out = E.runStrategy(B, { sig: res.sig, risk: res.risk }, cfg, 'All', null);
  const s = out.stats, from = out.from, to = out.to;
  const days = B.dayEnd[to] - B.dayEnd[from], years = Math.max(days / 365.25, 1e-9);
  const ann = (ret) => (ret > -100 ? (Math.pow(1 + ret / 100, 1 / years) - 1) * 100 : -100);
  const bhRet = s.bhRet, ex = out.bh[out.bh.length - 1] / cap * 100 - 100;
  const closed = out.trades.map((t) => ({ d0: E.dayToStr(B.day[t.i0]), d1: E.dayToStr(B.day[Math.min(t.i1, B.n - 1)]), p0: r2(t.p0), p1: r2(t.p1), pct: r2(t.pnlP), bars: t.bars, why: t.why || '' }));
  const worst = closed.slice().sort((a, b) => a.pct - b.pct).slice(0, 5);
  const annS = ann(s.ret), annB = ann(bhRet);
  return {
    sym: code, tf, from: E.dayToStr(B.day[from]), to: E.dayToStr(B.dayEnd[to]), bars: to - from + 1, years: r2(years),
    ret: r2(s.ret), ann: r2(annS), mdd: r2(s.mddP), win: r2(s.all.win), pf: s.all.pf === Infinity ? null : r2(s.all.pf), pfInf: s.all.pf === Infinity,
    n: s.n, nWin: s.all.nWin, nOpen: s.all.nOpen, avgPct: r2(s.all.avgTradeP), avgBars: r2(s.avgBars), costs: Math.round(s.costs),
    bhRet: r2(bhRet), bhAnn: r2(annB), bhMdd: r2(maxDD(Array.from(out.bh))), exAnn: r2(annS - annB),
    yr: yearly(B, from, out.eq, out.bh, cap), worst,
    _trades: keepTrades ? out.trades.map((t) => ({ y: new Date(B.day[t.i0] * 86400000).getUTCFullYear(), pct: t.pnlP, bars: t.bars })) : undefined,
  };
}

/* ---------------------------------------------------------------- 全市場單檔合計（競賽冠軍用）
   淘汰賽的冠軍是「300 檔股票池＋排名＋持股上限」的組合策略，練習室只能一檔一檔單獨回測。
   為了能和報告的逐筆統計（筆數、勝率、賺賠比、平均持有）對帳，這裡把所有有籌碼資料的個股各跑一次，把交易全部合在一起統計。
   訓練期＝2020 年以前（練習室個股日 K 從 2016 年起，所以只有 2016～2020 這一段，和報告的 2012～2020 不同）、保留期＝2021 年起。 */
function poolStats(trs) {
  const f = (a) => {
    const w = a.filter((t) => t.pct > 0), l = a.filter((t) => t.pct < 0), avg = (x, k) => (x.length ? x.reduce((s, t) => s + t[k], 0) / x.length : null);
    const aw = avg(w, 'pct'), al = avg(l, 'pct');
    return { n: a.length, win: a.length ? r2(w.length / a.length * 100) : null, payoff: aw != null && al ? r2(aw / Math.abs(al)) : null, avgPct: r2(avg(a, 'pct')), avgBars: r2(avg(a, 'bars')) };
  };
  return { all: f(trs), train: f(trs.filter((t) => t.y <= 2020)), hold: f(trs.filter((t) => t.y >= 2021)) };
}
function runPool(def) {
  const trs = []; let ns = 0, nUse = 0;
  for (const it of IDX.items) {
    if (it.k !== 'stock' || !it.ch) continue; ns++;
    const r = runOne(def, it.c, 'D', true); if (r.skip) continue; nUse++;
    if (r.n > 0) trs.push(...r._trades);
  }
  return Object.assign({ nStocks: nUse, nCandidates: ns }, poolStats(trs));
}

/* ---------------------------------------------------------------- 主流程 */
const result = {
  version: 1, source: SOURCE, dataThrough: IDX.updated,
  cfg: { stockCapital: STD.CAPITAL.stock, futCapital: STD.CAPITAL.fut, fill: '下一根開盤', pyramiding: 1, side: '只做多', fee: '0.1425%（不打折）', tax: '賣出 0.3%（指數／ETF 0.1%）', slip: '0.05%（台指期 1 點）', futFee: '40 元／口，期交稅 0.002%' },
  symbols: {}, strategies: {},
};
for (const def of STD.DEFS) {
  const runs = [], skipped = [];
  for (const sym of def.syms) {
    if (!ITEM[sym]) continue;
    result.symbols[sym] = { name: ITEM[sym].n, kind: ITEM[sym].k };
    for (const tf of def.tfs) {
      const r = runOne(def, sym, tf);
      if (r.skip) { if (tf === 'D') skipped.push({ sym, tf, why: r.skip }); continue; }
      runs.push(r);
    }
  }
  const D = runs.filter((r) => r.tf === 'D');
  const beat = D.filter((r) => r.exAnn > 0).length, pos = D.filter((r) => r.ann > 0).length;
  const ex = D.map((r) => r.exAnn).sort((a, b) => a - b), med = ex.length ? (ex.length % 2 ? ex[(ex.length - 1) / 2] : (ex[ex.length / 2 - 1] + ex[ex.length / 2]) / 2) : null;
  const ddBetter = D.filter((r) => r.mdd < r.bhMdd).length;
  result.strategies[def.id] = {
    no: def.no, headline: def.headline, runs, skipped, pool: def.pool ? runPool(def) : undefined,
    summary: { nSym: D.length, beatBH: beat, positive: pos, ddBetter, medianExAnn: r2(med), totalTrades: D.reduce((a, r) => a + r.n, 0), minTrades: D.length ? Math.min(...D.map((r) => r.n)) : 0 },
  };
}
fs.writeFileSync(OUT, JSON.stringify(result));
const mb = (fs.statSync(OUT).size / 1024).toFixed(0);
console.log('標準策略結果 →', path.relative(ROOT, OUT), mb + ' KB，資料來源 ' + SOURCE + '（' + IDX.updated + '）');
for (const def of STD.DEFS) {
  const st = result.strategies[def.id], h = st.runs.find((r) => r.sym === def.headline.sym && r.tf === def.headline.tf);
  console.log(String(def.no).padStart(2), def.name.padEnd(22), h ? `${h.sym} 總報酬 ${h.ret}% 年化 ${h.ann}% (買進持有 ${h.bhAnn}%) 回撤 ${h.mdd}% 勝率 ${h.win}% PF ${h.pf} 交易 ${h.n}` : '（無標題結果）', ' | 勝買進持有 ' + st.summary.beatBH + '/' + st.summary.nSym);
}
