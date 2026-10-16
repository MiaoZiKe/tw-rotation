/* 防白嫖（2026-10-16，docs/security/anti_freeload_1016.md 最小有效版本）account-api 端驗收。
   ① 新文章全文只在後端：未登入拿不到、訪客／註冊會員 403、Plus 第 6 篇伺服器端拒絕、重讀不重複計數、Pro／管理者不限、機器路由金鑰驗證
   ② 訪客累計 5 次：訪客編號簽章、同一個 key 重送不重算、無痕（新編號）被同 IP 接住、共用 IP 不誤擋前 3 個人、每週換鹽、8 天／180 天刪除、庫裡沒有原始 IP
   跑法：node --test workers/account-api/tests/anti_freeload.test.mjs */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
const BOT = 'article-bot-key-0123456789abcdef';
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const pending = {};
globalThis.fetch = async (url, init) => {
  if (String(url).startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body); const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  throw new Error('測試不准連外網：' + url);
};
let clock = Date.parse('2026-10-14T04:00:00Z');       // 台北週三
const PUT = 'article-put-key-0123456789abcdef01';
const env = () => ({ ARTICLE_PUT_KEY: PUT, ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', ARTICLE_BOT_KEY: BOT, SEED_PLANS: 'plus,pro', __now: () => clock });
const pj = async (hub, path, body, hd = {}) => {
  const r = await hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': '1.1.1.1', ...hd }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};
const bot = async (hub, body, tok = BOT) => { const r = await hub.fetch(new Request(API + '/v1/articles/jobs/bot', { method: 'POST', headers: { Authorization: 'Bearer ' + tok }, body: JSON.stringify(body) })); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location')); const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 86400 * 20, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await hub.fetch(new Request(API + '/auth/redeem', { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify({ n }) }))).json()).tok;
}
const post = (id, extra = {}) => ({ id, cat: 'know', title: '標題' + id, subtitle: 'SUB-SECRET', summary: 'SUMMARY-SECRET', date: '2026-10-16', blocks: [{ t: 'p', text: 'BODY-SECRET-' + id }], ...extra });
const IDS = Array.from({ length: 8 }, (_, i) => `2026-10-16-know-t${i + 1}`);
async function setup() {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const plus = await login(hub, 'plus@example.com'), pro = await login(hub, 'pro@example.com'), free = await login(hub, 'free@example.com');
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus' })).s, 200);
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pro@example.com', plan: 'pro' })).s, 200);
  for (const id of IDS) assert.equal((await bot(hub, { op: 'put_body', id, json: post(id) })).s, 200);
  return { hub, andy, plus, pro, free };
}
const get = (hub, t, id) => pj(hub, '/v1/articles/get', { t, id });

test('機器路由 put_body：鑰匙錯 403、格式錯 400、太大 413、其他 op 仍限 4KB、list_bodies 看得到、網頁來源不能寫', async () => {
  const { hub } = makeHub(env());
  const id = IDS[0];
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id) }, 'wrong-key-wrong-key-wrong-key')).s, 403, '沒有鑰匙不能寫全文');
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id) }, 'short')).s, 403);
  assert.equal((await bot(hub, { op: 'put_body', id: '../x', json: post(id) })).s, 400, '壞 id');
  assert.equal((await bot(hub, { op: 'put_body', id, json: { title: 'x' } })).s, 400, '沒有 blocks');
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id, { id: 'other-id-xx' }) })).s, 400, 'json.id 必須等於 id');
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id, { blocks: [{ t: 'p', text: 'x'.repeat(210000) }] }) })).s, 413, '單篇上限 200KB');
  assert.equal((await bot(hub, { op: 'open', pad: 'x'.repeat(5000) })).s, 413, '其他 op 仍是 4KB 上限');
  const ok = await bot(hub, { op: 'put_body', id, json: post(id) });
  assert.equal(ok.s, 200); assert.ok(ok.j.bytes > 50);
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id, { title: '改過' }) })).s, 200, '同 id 覆寫（改稿）');
  const l = await bot(hub, { op: 'list_bodies' });
  assert.deepEqual(l.j.bodies.map((x) => x.id), [id]);
  // 一般網頁來源（有 Origin、沒有金鑰）打這支路由：一律 403，且不會經過 originOk
  const web = await hub.fetch(new Request(API + '/v1/articles/jobs/bot', { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify({ op: 'put_body', id: 'web-write-xx', json: post('web-write-xx') }) }));
  assert.equal(web.status, 403);
  assert.equal((await bot(hub, { op: 'list_bodies' })).j.bodies.length, 1, '網頁寫不進去');
  assert.equal((await bot(hub, { op: 'del_body', id })).s, 200);
  assert.equal((await bot(hub, { op: 'list_bodies' })).j.bodies.length, 0);
});

test('最小權限鑰匙 ARTICLE_PUT_KEY：只能 put_body／del_body／list_bodies，不能讀佇列、標狀態、讀頻率；太短的不算；備份權杖不因此能傳全文以外的事', async () => {
  const { hub } = makeHub(env());
  const id = IDS[0];
  assert.equal((await bot(hub, { op: 'put_body', id, json: post(id) }, PUT)).s, 200);
  assert.equal((await bot(hub, { op: 'list_bodies' }, PUT)).j.bodies.length, 1);
  for (const op of ['open', 'schedule']) assert.equal((await bot(hub, { op }, PUT)).s, 403, op + ' 不給 PUT 鑰匙');
  assert.equal((await bot(hub, { op: 'mark', id: 1, status: 'done' }, PUT)).s, 403);
  assert.equal((await bot(hub, { op: 'del_body', id }, PUT)).s, 200);
  const { hub: h2 } = makeHub({ ...env(), ARTICLE_PUT_KEY: 'too-short-key-0123456' });
  assert.equal((await bot(h2, { op: 'list_bodies' }, 'too-short-key-0123456')).s, 403, '少於 24 字的 PUT 鑰匙不算');
  assert.equal((await bot(hub, { op: 'open' })).s, 200, '完整機器鑰匙照舊可用');
});

test('全文：未登入拿不到（401，回應裡沒有內文）；訪客編號、壞權杖一樣；沒有這篇 404', async () => {
  const { hub } = await setup();
  for (const body of [{ id: IDS[0] }, { id: IDS[0], t: 'v1.x.1.1.bad' }]) {
    const r = await pj(hub, '/v1/articles/get', body);
    assert.equal(r.s, 401); assert.ok(!JSON.stringify(r.j).includes('BODY-SECRET'), '回應裡不能有內文');
  }
  const g = (await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k1' })).j.g;
  assert.equal((await pj(hub, '/v1/articles/get', { id: IDS[0] }, { 'X-Tw-Guest': g })).s, 401, '有訪客編號也拿不到全文');
  const other = (await setup()).plus;       // 另一台 Worker（不同簽章金鑰）簽的權杖
  assert.equal((await get(hub, other, IDS[0])).s, 401, '別台 Worker 簽的權杖無效');
});

test('全文：註冊會員（art.read.n 預設 0）403 且沒有內文、也不寫讀過紀錄', async () => {
  const { hub, free } = await setup();
  const r = await get(hub, free, IDS[0]);
  assert.equal(r.s, 403); assert.equal(r.j.error, 'forbidden'); assert.ok(!JSON.stringify(r.j).includes('BODY-SECRET'));
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 0);
});

test('全文：Plus 累計 5 篇（伺服器計數）：1～5 篇可讀、重讀不重複計數、第 6 篇 402 且沒有內文、已讀的永遠能重讀', async () => {
  const { hub, plus } = await setup();
  for (let i = 0; i < 5; i++) {
    const r = await get(hub, plus, IDS[i]);
    assert.equal(r.s, 200, IDS[i]); assert.equal(r.j.post.blocks[0].text, 'BODY-SECRET-' + IDS[i]); assert.equal(r.j.limit, 5); assert.equal(r.j.reads.length, i + 1);
  }
  const again = await get(hub, plus, IDS[0]);
  assert.equal(again.s, 200); assert.equal(again.j.reads.length, 5, '重讀第 1 篇：不增加');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 5);
  const six = await get(hub, plus, IDS[5]);
  assert.equal(six.s, 402); assert.equal(six.j.error, 'quota'); assert.equal(six.j.reads.length, 5);
  assert.ok(!JSON.stringify(six.j).includes('BODY-SECRET'), '第 6 篇回應沒有內文');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 5, '被拒的不計數');
  assert.equal((await get(hub, plus, IDS[4])).s, 200, '額度滿了，已解鎖的仍可重讀');
  assert.equal((await get(hub, plus, 'not-exist-1')).s, 404); assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 5, '不存在的文章不扣額度');
  // 清掉本機資料、換瀏覽器：計數在伺服器 → 同一個帳號換任何環境結果一樣
  const st = await pj(hub, '/v1/total/state', { t: plus, ids: ['art.read.n'] });
  assert.deepEqual(st.j.limits['art.read.n'].used, IDS.slice(0, 5)); assert.equal(st.j.limits['art.read.n'].limit, 5);
});

test('全文：Pro／管理者不限篇數、不寫讀過紀錄；管理區對 Plus 關掉 art.read 或某類別 → 伺服器也 403；到期的 Plus 退回註冊會員', async () => {
  const { hub, andy, pro, plus } = await setup();
  for (const id of IDS) { assert.equal((await get(hub, pro, id)).s, 200); assert.equal((await get(hub, andy, id)).s, 200); }
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 0);
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus', over: { 'art.cat.know': false } })).s, 200);
  assert.equal((await get(hub, plus, IDS[0])).s, 403, '類別被關掉');
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus', over: { 'art.read': false } })).s, 200);
  assert.equal((await get(hub, plus, IDS[0])).s, 403, '整個精選文章被關掉');
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus', over: {}, expires: clock + 3600e3 })).s, 200);
  assert.equal((await get(hub, plus, IDS[0])).s, 200);
  clock += 2 * 3600e3;
  assert.equal((await get(hub, plus, IDS[1])).s, 403, '到期 → 當註冊會員（0 篇）');
  clock -= 2 * 3600e3;
});

test('全文：範本明確寫 art.read.n（Plus 改 3、Pro 寫 999＝不限）→ 伺服器照範本', async () => {
  const { hub, andy, plus } = await setup();
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'art.read.n': 3 } })).s, 200);
  for (let i = 0; i < 3; i++) assert.equal((await get(hub, plus, IDS[i])).s, 200);
  assert.equal((await get(hub, plus, IDS[3])).s, 402);
});

test('今日事件訪客 5 次：訪客編號由伺服器簽發；同一個 key 重送不重算；第 6 次拒絕；偽造編號當新訪客；回應可存回 localStorage', async () => {
  const { hub } = await setup();
  const first = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o1' });
  assert.equal(first.j.ok, true); assert.match(first.j.g, /^g1\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{22}$/); assert.equal(first.j.limit, 5);
  const H = { 'X-Tw-Guest': first.j.g };
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o1' }, H)).j.used.length, 1, '同一個 key 重送：不重算');
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o1' }, H)).j.g, undefined, '有效編號不再發新的');
  for (let i = 2; i <= 5; i++) { const r = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o' + i }, H); assert.equal(r.j.ok, true); assert.equal(r.j.used.length, i); }
  const six = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o6' }, H);
  assert.equal(six.j.ok, false); assert.equal(six.j.why, 'quota'); assert.equal(six.j.used.length, 5);
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'o3' }, H)).j.ok, true, '算過的 key 永遠 ok');
  const st = await pj(hub, '/v1/total/state', { ids: ['events.total', 'art.read.n', 'nope'] }, H);
  assert.deepEqual(Object.keys(st.j.limits), ['events.total', 'art.read.n']);
  assert.equal(st.j.limits['events.total'].used.length, 5); assert.equal(st.j.limits['events.total'].limit, 5); assert.equal(st.j.limits['art.read.n'].limit, 0);
  // 偽造：改簽章／自己編 → 當成新訪客，發新的（用量從 0 開始，但被同 IP 的總量接住，見下一條）
  const forged = first.j.g.slice(0, -2) + 'AA';
  const f = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'x1' }, { 'X-Tw-Guest': forged });
  assert.ok(f.j.g && f.j.g !== forged, '偽造的編號被換掉');
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'x1' }, { 'X-Tw-Guest': 'g1.AAAAAAAAAAAAAAAAAAAAAA.BBBBBBBBBBBBBBBBBBBBBB' })).j.used.length, 1);
  // 壞輸入
  assert.equal((await pj(hub, '/v1/total/use', { id: 'art.read.n', key: 'k' })).s, 400, '只有 events.total 走 use');
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: '<script>' })).s, 400);
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k', t: 'bad.token' })).s, 401);
});

test('無痕視窗（清掉訪客編號＝新編號）：同一個網路被 IP 總量接住；前 3 個編號不受影響（共用 IP 不誤擋）；換 IP 才有新的', async () => {
  const { hub } = await setup();
  const IP = { 'CF-Connecting-IP': '203.0.113.7' };
  const burn = async (n, ip = IP) => {                      // 一個全新的訪客用掉 n 次
    let g = null, last = null;
    for (let i = 0; i < n; i++) { last = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k' + i }, { ...ip, ...(g ? { 'X-Tw-Guest': g } : {}) }); g = g || last.j.g; }
    return last.j;
  };
  for (let u = 1; u <= 3; u++) { const r = await burn(5); assert.equal(r.ok, true, `第 ${u} 個人（同公司同 IP）5 次都該成功`); assert.equal(r.used.length, 5); }
  const fourth = await burn(5);
  assert.equal(fourth.ok, true, '第 4 個編號：IP 總量（5×4＝20）還有 5 次');
  const fifth = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'z1' }, IP);
  assert.equal(fifth.j.ok, false); assert.equal(fifth.j.why, 'ip', '第 5 個全新編號：被同 IP 接住');
  assert.equal(fifth.j.used.length, 0);
  const other = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'z1' }, { 'CF-Connecting-IP': '198.51.100.9' });
  assert.equal(other.j.ok, true, '換了網路（不同 IP）：這是方案已知的限制，會有新的 5 次');
  // IPv6：同一個 /64 視為同一戶
  const v6a = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a' }, { 'CF-Connecting-IP': '2001:db8:1:2:aaaa::1' });
  const v6b = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a' }, { 'CF-Connecting-IP': '2001:db8:1:2:bbbb::9' });
  assert.equal(hub.q('SELECT COUNT(DISTINCT iph) AS c FROM tot_ipg WHERE sub IN (?, ?)', 'g:' + v6a.j.g.split('.')[1], 'g:' + v6b.j.g.split('.')[1])[0].c, 1, 'IPv6 前 64 位元相同 → 同一個雜湊');
});

test('登入者以帳號計：註冊會員預設不限；範本寫了 events.total 就以 uid 計（換裝置不重算）；管理者不限', async () => {
  const { hub, andy, free } = await setup();
  for (let i = 0; i < 8; i++) assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'm' + i, t: free })).j.ok, true);
  assert.equal(hub.q("SELECT COUNT(*) AS c FROM tot_use WHERE sub LIKE 'u:%'")[0].c, 0, '不限的人不寫紀錄');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', feats: { 'events.total': 2 } })).s, 200);
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a1', t: free })).j.ok, true);
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a2', t: free })).j.ok, true);
  const third = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a3', t: free }, { 'CF-Connecting-IP': '9.9.9.9' });   // 換網路也一樣
  assert.equal(third.j.ok, false); assert.equal(third.j.why, 'quota');
  assert.equal((await pj(hub, '/v1/total/use', { id: 'events.total', key: 'a4', t: andy })).j.ok, true, '管理者不限');
});

test('隱私：庫裡沒有任何原始 IP；每週換鹽後舊雜湊整批清掉、同一個 IP 的新雜湊不同；8 天資料刪、訪客 180 天沒出現就刪', async () => {
  const { hub } = await setup();
  const IP = '203.0.113.77';
  const r = await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k1' }, { 'CF-Connecting-IP': IP });
  const dump = JSON.stringify([hub.q('SELECT * FROM tot_ip'), hub.q('SELECT * FROM tot_ipg'), hub.q('SELECT * FROM tot_use'), hub.q('SELECT * FROM tot_guest'), hub.q('SELECT * FROM kv')]);
  assert.ok(!dump.includes(IP), '原始 IP 不得出現在任何表');
  const h1 = hub.q('SELECT iph FROM tot_ipg')[0].iph;
  assert.match(h1, /^[A-Za-z0-9_-]{43}$/);
  // 同一週：同一個 IP → 同一個雜湊（才能累計）
  await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k2' }, { 'CF-Connecting-IP': IP, 'X-Tw-Guest': r.j.g });
  assert.equal(hub.q('SELECT COUNT(DISTINCT iph) AS c FROM tot_ip')[0].c, 1);
  // 下一週（台北週一 00:00 之後）：換鹽 → 舊雜湊被整批刪掉
  clock += 5 * 86400e3;
  await pj(hub, '/v1/total/use', { id: 'events.total', key: 'k3' }, { 'CF-Connecting-IP': IP, 'X-Tw-Guest': r.j.g });
  const h2 = hub.q('SELECT iph FROM tot_ipg')[0].iph;
  assert.notEqual(h2, h1, '同一個 IP 換週後雜湊不同（舊鹽已丟）');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_ip')[0].c, 1, '只剩新一週寫的');
  // 8 天後 cleanup：IP 資料刪；訪客紀錄還在（180 天）
  clock += 9 * 86400e3;
  hub.cleanup();
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_ip')[0].c, 0); assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_ipg')[0].c, 0);
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_guest')[0].c, 1);
  clock += 175 * 86400e3;
  hub.cleanup();
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_guest')[0].c, 0, '180 天沒出現 → 訪客編號與用量一起刪');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM tot_use')[0].c, 0);
});

test('預檢（CORS）允許自訂標頭 X-Tw-Guest；非白名單來源打新路由 403；刪除帳號一併刪讀過紀錄', async () => {
  const { hub, plus } = await setup();
  const pre = await hub.fetch(new Request(API + '/v1/total/use', { method: 'OPTIONS', headers: { Origin: ORIGIN, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type,x-tw-guest' } }));
  assert.equal(pre.status, 204); assert.match(pre.headers.get('Access-Control-Allow-Headers'), /x-tw-guest/);
  const bad = await hub.fetch(new Request(API + '/v1/articles/get', { method: 'POST', headers: { Origin: 'https://evil.example', 'content-type': 'text/plain' }, body: JSON.stringify({ t: plus, id: IDS[0] }) }));
  assert.equal(bad.status, 403, '非白名單來源不能讀全文');
  await get(hub, plus, IDS[0]);
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 1);
  assert.equal((await pj(hub, '/v1/delete', { t: plus })).s, 200);
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_reads')[0].c, 0, '刪帳號 → 讀過紀錄一起刪');
});

test('備份：article_body 在匯出清單裡（全文只存在這裡，沒備份就是單點）；訪客與 IP 表不匯出', async () => {
  const m = await import('../worker.js');
  assert.ok(m.EXPORT_TABLES.includes('article_body'));
  for (const t of ['tot_ip', 'tot_ipg', 'tot_use', 'tot_guest']) assert.ok(!m.EXPORT_TABLES.includes(t), t + ' 不該進備份');
});
