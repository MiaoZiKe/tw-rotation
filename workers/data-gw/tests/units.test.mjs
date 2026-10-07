/* 動作計次單位（docs/perm_matrix_1008.md §2）：前端 site/quota.js 與 workers/data-gw/tiers.js 必須產生同一組字串。
   跑法：node --test workers/data-gw/tests/ */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { actUnit, UNIT_KINDS } from '../tiers.js';

function loadFront() {
  const src = fs.readFileSync(fileURLToPath(new URL('../../../site/quota.js', import.meta.url)), 'utf8');
  const noop = () => {};
  const store = {};
  const win = { addEventListener: noop, dispatchEvent: noop };
  const ctx = {
    window: win, location: { hash: '', search: '' }, setTimeout: () => 0, clearTimeout: noop,
    sessionStorage: { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } },
    document: { readyState: 'complete', addEventListener: noop, querySelector: () => null, querySelectorAll: () => [], getElementById: () => null },
    console,
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return win.TwQuota;
}

test('前端 TwQuota.actUnit 與 data-gw actUnit 同一組字串', () => {
  const Q = loadFront();
  assert.ok(Q && Q.actUnit, 'site/quota.js 有輸出 actUnit');
  assert.deepEqual([...Q.UNIT_KINDS], UNIT_KINDS, '單位清單一致');
  const cases = [['drill', 'ai_server_odm'], ['filter', 'ic_substrate'], ['tab', '2026-11'], ['tab', '債券型'], ['filter', 'tech|AI,伺服器'],
    ['obj', 't.cowos'], ['obj', 'c.semiconductor'], ['obj', 'p.top'], ['obj', 'm.9'], ['filter', 'yield'], ['drill', 'ind_半導體業'],
    ['filter', 'a_very_long_group_identifier_x'], ['view', 'etf.abc']];
  for (const [k, o] of cases) assert.equal(Q.actUnit(k, o), actUnit(k, o), `${k} ${o}`);
  assert.equal(actUnit('drill', 'mlcc'), 'drill.mlcc');
  assert.equal(actUnit('obj', 't.cowos'), 't.cowos', 'obj 沿用畫面計次的 key');
  assert.match(actUnit('tab', '債券型'), /^x[0-9a-f]+$/, '中文 → 雜湊');
  for (const [k, o] of cases) assert.match(actUnit(k, o), /^[0-9A-Za-z_.-]{1,24}$/, 'account-api QUOTA_KEY_RE 收得下');
});
