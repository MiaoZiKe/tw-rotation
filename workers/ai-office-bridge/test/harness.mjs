/* 在 Node 裡跑真的 worker.js：把 Durable Object 的 SQLite（ctx.storage.sql）換成 node:sqlite（跟 workers/account-api/harness.mjs 同一招）。
 * 測試（bridge.test.mjs）與本機開發伺服器（devserver.mjs）共用。 */
import { DatabaseSync } from 'node:sqlite';
import worker, { Hub } from '../worker.js';

export function makeHub(env = {}, opts = {}) {
  const db = new DatabaseSync(':memory:');
  const sql = {
    exec(q, ...args) {
      const st = db.prepare(q);
      const rows = /^\s*(SELECT|WITH|PRAGMA)/i.test(q) ? st.all(...args) : (st.run(...args), []);
      return { toArray: () => rows.map((r) => ({ ...r })) };
    },
  };
  const hub = new Hub({ storage: { sql } }, env);
  if (opts.now) hub.now = opts.now;
  // 讓 worker 的預設入口也能用：env.HUB.get(...).fetch → 這一個 hub
  env.HUB = { idFromName: () => 'hub', get: () => ({ fetch: (req) => hub.fetch(req) }) };
  return { hub, db, env, fetch: (req) => worker.fetch(req, env) };
}

/** 假的會員 Worker：/v1/me 依權杖回答是不是管理者 */
export function fakeAccount(map = { 'owner-token-0123456789abcdef': true, 'member-token-0123456789abcdef': false }) {
  const calls = [];
  return {
    calls,
    async fetch(url, init) {
      calls.push({ url, init });
      const b = JSON.parse(init.body || '{}');
      if (!(b.t in map)) return new Response('{"error":"auth"}', { status: 401 });
      return new Response(JSON.stringify({ user: { name: 'x', email: 'x@example.com', admin: map[b.t] } }), { status: 200 });
    },
  };
}
