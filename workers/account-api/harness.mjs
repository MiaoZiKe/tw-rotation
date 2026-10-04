/* 在 Node 裡跑真的 worker.js：把 Durable Object 的 SQLite（ctx.storage.sql）換成 node:sqlite。
 *
 * 給兩個地方用：
 *   · tests/account.test.mjs —— 存取控制（等同 Firebase 安全規則）的逐條驗收
 *   · devserver.mjs —— 本機起一個假的 API ＋ 假的 Google，讓 scripts/_uitest.py 走完整的登入流程
 *
 * 只模擬 Durable Object 用到的那幾個介面：sql.exec(...).toArray()、getAlarm／setAlarm。
 */
import { DatabaseSync } from 'node:sqlite';
import { Hub } from './worker.js';

export function makeHub(env = {}) {
  const db = new DatabaseSync(':memory:');
  const sql = {
    exec(q, ...args) {
      const st = db.prepare(q);
      const rows = /^\s*(SELECT|WITH|PRAGMA)/i.test(q) ? st.all(...args) : (st.run(...args), []);
      return { toArray: () => rows.map((r) => ({ ...r })) };
    },
  };
  let alarm = null;
  const state = { storage: { sql, getAlarm: async () => alarm, setAlarm: async (t) => { alarm = t; } } };
  const hub = new Hub(state, env);
  return { hub, db, state, getAlarm: () => alarm };
}
