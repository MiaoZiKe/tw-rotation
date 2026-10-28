#!/usr/bin/env node
/* 對帳補充：淘汰賽報告的進場，練習室那天「沒有訊號」時，是哪一個條件沒過？（scripts/recon_tournament.js 的延伸，一次性分析）
   用法：node scripts/recon_why.js <交易明細.csv> m1216|m1148 */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const E = require(path.join(ROOT, 'site/lab/engine.js'));
const DIR = path.join(ROOT, 'site/data/lab');
const readJ = (rel) => JSON.parse(fs.readFileSync(path.join(DIR, rel), 'utf8'));
const IDX = readJ('index.json'), US = readJ('us.json'), CH = new Set(IDX.items.filter((x) => x.k === 'stock' && x.ch).map((x) => x.c));
const which = process.argv[3];
const rows = fs.readFileSync(process.argv[2], 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/), head = rows[0].split(',');
const rep = rows.slice(1).map((r) => { const c = r.split(','), o = {}; head.forEach((h, i) => { o[h] = c[i]; }); return o; }).filter((t) => CH.has(t.code) && t.entry_date >= '2016-02-01');
const roll = (a, v, i, n) => { let s = 0, w = 0; for (let k = i - n + 1; k <= i; k++) { s += a[k] || 0; w += v[k]; } return s / w * 100; };
const fails = {}, near = [];
let total = 0;
for (const t of rep) {
  const j = readJ('s/' + t.code + '.json'), B = E.decode(j.d, 'D'); E.attachChip(B, readJ('c/' + t.code + '.json')); E.attachUS(B, US);
  const d = Math.round(Date.parse(t.entry_date) / 86400000); let i = 0; while (i < B.n && B.day[i] < d) i++;
  if (i >= B.n || B.day[i] !== d || i < 12) continue; const k = i - 1, C = B.chip;
  const inst = (a) => (C.fn[a] || 0) + (C.tr[a] || 0) + (C.dl[a] || 0);
  const instArr = Array.from({ length: B.n }, (_, a) => inst(a));
  const conds = which === 'm1216'
    ? { 法人5日占比: roll(instArr, B.v, k, 5) > 1, 營收年增: C.ry[k] > 20, 公布後天數: C.ra[k] <= 5 }
    : { 外資10日占比: roll(C.fn, B.v, k, 10) > 0.5, 投信10日: roll(C.tr, B.v, k, 10) > 0, 營收年增: C.ry[k] > 20, 公布後天數: C.ra[k] <= 3 };
  total++;
  const bad = Object.keys(conds).filter((x) => !conds[x]);
  if (!bad.length) continue;
  bad.forEach((x) => { fails[x] = (fails[x] || 0) + 1; });
  if (near.length < 6) near.push(t.code + ' ' + t.entry_date + ' 沒過：' + bad.join('、') + '（法人5日占比 ' + (which === 'm1216' ? roll(instArr, B.v, k, 5).toFixed(2) : roll(C.fn, B.v, k, 10).toFixed(2)) + '%，年增 ' + C.ry[k] + '，公布後第 ' + C.ra[k] + ' 天）');
}
console.log(JSON.stringify({ checked: total, 條件沒過的次數: fails, 例: near }, null, 1));
