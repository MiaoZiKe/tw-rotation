/* 精選文章點閱次數（2026-10-16）：不用登入、同 IP 30 分鐘只算一次、壞 id 擋下、stats 一次拿全部 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
let clock = Date.parse('2026-10-16T04:00:00Z');
const env = { ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: 'c', GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock };
const pj = async (hub, path, body, ip = '1.1.1.1') => {
  const r = await hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': ip }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};

test('點閱：不用登入；同 IP 30 分鐘內只算一次；不同 IP 各算；壞 id 擋；stats 拿全部', async () => {
  const { hub } = makeHub(env);
  const id = '2026-10-14-know-cowos';
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 1);
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 1, '同 IP 30 分鐘內不重算');
  assert.equal((await pj(hub, '/v1/articles/view', { id }, '2.2.2.2')).j.views, 2, '不同 IP 算');
  clock += 31 * 60 * 1000;
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 3, '超過 30 分鐘再算');
  assert.equal((await pj(hub, '/v1/articles/view', { id: '<script>' })).s, 400);
  await pj(hub, '/v1/articles/view', { id: '2026-10-14-intro-ai-server' });
  assert.deepEqual((await pj(hub, '/v1/articles/stats', {})).j.views, { '2026-10-14-know-cowos': 3, '2026-10-14-intro-ai-server': 1 });
});
