#!/usr/bin/env node
/* ============================================================================
   淘汰賽冠軍（M1216、M1148）與練習室的對帳（2026-10-29，一次性分析工具）
   用法：node scripts/recon_tournament.js <M1216 交易明細.csv> <M1148 交易明細.csv> [--data site/data/lab]
   交易明細 CSV 在 claude/elegant-fermi-scpgme 分支的 docs/strategy_lab/tournament/trades/。
   對的是三件事：
     ① 進場訊號：報告每一筆進場（T+1 開盤），練習室同一檔在 T 日收盤是不是也有訊號（同日／前後一個交易日）；
     ② 逐筆統計：報告（限練習室有的股票、2016 年起）對練習室全市場單檔合計：筆數、勝率、賺賠比、平均持有；
     ③ 反向：練習室的訊號有幾成真的被淘汰賽進場（其餘是被持股上限、排序、冷卻期擋掉）。
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const E = require(path.join(ROOT, 'site/lab/engine.js'));
const X = require(path.join(ROOT, 'site/lab/expr.js'));
const STD = require(path.join(ROOT, 'site/lab/standard_defs.js'));
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const di = process.argv.indexOf('--data');
const DIR = di > 0 ? process.argv[di + 1] : path.join(ROOT, 'site/data/lab');
const readJ = (rel) => { const f = path.join(DIR, rel); return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : null; };
const IDX = readJ('index.json'), US = readJ('us.json');
const CH = new Set(IDX.items.filter((x) => x.k === 'stock' && x.ch).map((x) => x.c));

function load(code) {
  const j = readJ('s/' + code + '.json'); if (!j) return null;
  const D = E.decode(j.d, 'D'); E.attachChip(D, readJ('c/' + code + '.json')); E.attachUS(D, US); return D;
}
function csv(file) {
  const rows = fs.readFileSync(file, 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/), head = rows[0].split(',');
  return rows.slice(1).map((r) => { const c = r.split(','), o = {}; head.forEach((h, i) => { o[h] = c[i]; }); return o; });
}
const stat = (pcts, bars) => {
  const w = pcts.filter((x) => x > 0), l = pcts.filter((x) => x < 0), avg = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : NaN);
  return { n: pcts.length, win: pcts.length ? +(w.length / pcts.length * 100).toFixed(1) : null, payoff: +(avg(w) / Math.abs(avg(l))).toFixed(2), avgPct: +avg(pcts).toFixed(2), avgBars: +avg(bars).toFixed(1) };
};

const cache = {};
for (const [k, file] of [['std_m1216', args[0]], ['std_m1148', args[1]]]) {
  const def = STD.DEFS.find((d) => d.id === k), rep = csv(file).filter((t) => CH.has(t.code) && t.entry_date >= '2016-02-01');
  const out = { id: k, reportTradesInUniverse: rep.length };
  let hit0 = 0, hit1 = 0, nAny = 0, miss = [];
  const lab = [], labSig = [];
  const sigDays = {};      // code → Set(進場日期)
  for (const code of CH) {
    const B = cache[code] || (cache[code] = load(code)); if (!B) continue;
    const res = X.compile(def.script, B, { events: [] }); if (!res.sig) continue;
    const cfg = { mode: 'long', capital: 1e6, sizeMode: 'pct', sizeVal: 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: E.instDefaults('stock') };
    const r = E.runStrategy(B, { sig: res.sig, risk: res.risk }, cfg, 'All', null);
    r.trades.forEach((t) => lab.push({ y: new Date(B.day[t.i0] * 86400000).getUTCFullYear(), pct: t.pnlP, bars: t.bars }));
    const s = new Set(); for (let i = 0; i < B.n - 1; i++) if (res.sig.L[i]) s.add(E.dayToStr(B.day[i + 1])); sigDays[code] = { s, B, L: res.sig.L };
  }
  // ① 報告進場在練習室有沒有訊號（T 日收盤的訊號，進場日 T+1）
  for (const t of rep) {
    const o = sigDays[t.code]; if (!o) continue; nAny++;
    const B = o.B, d = Math.round(Date.parse(t.entry_date) / 86400000);
    let i = 0; while (i < B.n && B.day[i] < d) i++;           // i＝進場日那一根（或之後第一根）
    if (i >= B.n || B.day[i] !== d) { miss.push(t.code + ' ' + t.entry_date + '（練習室那天沒有 K 棒）'); continue; }
    if (o.L[i - 1]) hit0++; else if ((o.L[i - 2] || o.L[i])) hit1++; else miss.push(t.code + ' ' + t.entry_date);
  }
  out.signalMatch = { checked: nAny, sameDay: hit0, withinOneBar: hit1, none: nAny - hit0 - hit1, sameDayPct: +(hit0 / nAny * 100).toFixed(1), anyPct: +((hit0 + hit1) / nAny * 100).toFixed(1), missSample: miss.slice(0, 8) };
  // ② 逐筆統計
  out.reportStats = { all: stat(rep.map((t) => +t.ret * 100), rep.map((t) => +t.hold_days)), hold: stat(rep.filter((t) => t.entry_date >= '2021').map((t) => +t.ret * 100), rep.filter((t) => t.entry_date >= '2021').map((t) => +t.hold_days)), train: stat(rep.filter((t) => t.entry_date < '2021').map((t) => +t.ret * 100), rep.filter((t) => t.entry_date < '2021').map((t) => +t.hold_days)) };
  out.labStats = { all: stat(lab.map((t) => t.pct), lab.map((t) => t.bars)), hold: stat(lab.filter((t) => t.y >= 2021).map((t) => t.pct), lab.filter((t) => t.y >= 2021).map((t) => t.bars)), train: stat(lab.filter((t) => t.y <= 2020).map((t) => t.pct), lab.filter((t) => t.y <= 2020).map((t) => t.bars)) };
  // ③ 練習室每個「進場訊號日」有幾成被淘汰賽進場（同一檔同一天）
  const repSet = new Set(rep.map((t) => t.code + '|' + t.entry_date));
  let sigN = 0, sigHit = 0;
  for (const code of Object.keys(sigDays)) for (const dstr of sigDays[code].s) { if (dstr < '2016-02-01') continue; sigN++; if (repSet.has(code + '|' + dstr)) sigHit++; }
  out.labSignals = { signalDays: sigN, takenByTournament: sigHit, pct: +(sigHit / sigN * 100).toFixed(1) };
  console.log(JSON.stringify(out, null, 1));
}
