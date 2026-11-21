/* 在 Node 裡跑真的 data-gw worker.js：Durable Object 的 SQLite → node:sqlite；R2 → 記憶體 Map。
 * 給 tests/gw.test.mjs 與 devserver.mjs 用。
 */
import { DatabaseSync } from 'node:sqlite';
import { Gw } from './worker.js';

export function fakeR2(files = {}) {
  const m = new Map(Object.entries(files).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
  return { map: m, async get(k) { return m.has(k) ? { text: async () => m.get(k) } : null; }, async put(k, v) { m.set(k, String(v)); } };
}

export function makeGw(env = {}) {
  const db = new DatabaseSync(':memory:');
  const sql = {
    exec(q, ...args) {
      const st = db.prepare(q);
      const rows = /^\s*(SELECT|WITH|PRAGMA)/i.test(q) ? st.all(...args) : (st.run(...args), []);
      return { toArray: () => rows.map((r) => ({ ...r })) };
    },
  };
  const gw = new Gw({ storage: { sql } }, env);
  return { gw, db };
}
