// node --test workers/ai-office-bridge/test/ —— 收件端：驗證、欄位白名單、限速、讀取、領碼、CORS。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';
import { clean, scrub, sha256 } from '../worker.js';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', MEMBER = 'member-token-0123456789abcdef';

async function setup(opts = {}) {
  let t = opts.t0 || 1_800_000_000_000;
  const acc = fakeAccount();
  const h = makeHub({ ACCOUNT: acc }, { now: () => t });
  const code = opts.noCode ? null : await h.hub.devIssue();
  return { ...h, acc, code, tick: (ms) => { t += ms; }, at: () => t };
}
const post = (h, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...hdr }, body: typeof body === 'string' ? body : JSON.stringify(body) }));
const get = (h, path, hdr = {}) => h.fetch(new Request('https://w' + path, { headers: hdr }));
const bearer = (c) => ({ Authorization: 'Bearer ' + c });
const ev = (event, o = {}) => ({ event, session_id: 'sess-1', project_name: 'tw-rotation', project_hash: 'abcdef0123456789', cloud: true, ...o });

test('驗證：沒有碼、錯的碼一律 401；對的碼收下', async () => {
  const h = await setup();
  assert.equal((await post(h, '/v1/events', ev('SessionStart'))).status, 401);
  assert.equal((await post(h, '/v1/events', ev('SessionStart'), bearer('aio_wrongwrongwrongwrong'))).status, 401);
  const r = await post(h, '/v1/events', ev('SessionStart'), bearer(h.code));
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true, accepted: 1, dropped: 0 });
  // 資料庫只存雜湊，原碼不在任何一張表裡
  const dump = JSON.stringify(h.db.prepare('SELECT * FROM codes').all());
  assert.ok(!dump.includes(h.code));
  assert.ok(dump.includes(await sha256(h.code)));
});

test('驗證：接入碼錯太多次，同一個來源被擋（429）', async () => {
  const h = await setup();
  let last;
  for (let i = 0; i < 22; i++) last = await post(h, '/v1/events', ev('Stop'), { ...bearer('aio_bad_' + i + 'xxxxxxxxxxxx'), 'CF-Connecting-IP': '9.9.9.9' });
  assert.equal(last.status, 429);
  // 別的來源不受影響
  assert.equal((await post(h, '/v1/events', ev('Stop'), { ...bearer('aio_bad_zzzzzzzzzzzzzzzz'), 'CF-Connecting-IP': '8.8.8.8' })).status, 401);
});

test('欄位白名單：提示詞全文、指令、路徑、不認得的欄位都不存；文字遮掉路徑網址信箱檔名', async () => {
  const raw = {
    hook_event_name: 'PreToolUse', session_id: 's1', tool_category: 'dispatch', subagent_type: 'frontend-ui',
    description: '修 /home/andy/tw-rotation/site/app.js 與 site/x.css，參考 https://example.com/a?b=1 寄 a@b.com',
    prompt: '這是派工全文，不能存', tool_input: { command: 'rm -rf /' }, cwd: '/home/andy/tw-rotation', transcript_path: '/home/andy/.claude/x.jsonl',
    secret: 'x', tool_category_x: 1,
  };
  const c = clean(raw);
  assert.equal(c.event, 'PreToolUse');
  for (const k of ['prompt', 'tool_input', 'cwd', 'transcript_path', 'secret', 'tool_category_x']) assert.ok(!(k in c), k + ' 不該被留下');
  assert.ok(!/home|andy|app\.js|x\.css|example\.com|a@b\.com/.test(c.description), c.description);
  assert.ok(c.description.length <= 80);
  assert.equal(clean({ event: 'MessageDisplay', session_id: 's' }), null, '不在白名單的事件整筆丟掉');
  assert.equal(clean({ event: 'PreToolUse', tool_category: 'hack' }).tool_category, undefined, '工具類別只收固定幾種');
  assert.equal(clean({ event: 'SubagentStart', agent_type: '<script>alert(1)</script>' }).agent_type, undefined);
  assert.equal(scrub('金鑰 ' + ['sk', 'live', 'abcdefghijklmnopqrstuvwxyz0123'].join('_') + ' 結束', 80), '金鑰 〔遮蔽〕 結束');
  const h = await setup();
  const r = await post(h, '/v1/events', { events: [raw, { event: 'Weird' }] }, bearer(h.code));
  assert.deepEqual(await r.json(), { ok: true, accepted: 1, dropped: 1 });
  const stored = h.db.prepare('SELECT data FROM events').all().map((x) => x.data).join('\n');
  assert.ok(!/這是派工全文|rm -rf|\/home\/andy/.test(stored), stored);
});

test('長度上限：超過 32KB 413、一次超過 25 筆 413、不是 JSON 400', async () => {
  const h = await setup();
  assert.equal((await post(h, '/v1/events', JSON.stringify({ event: 'Stop', pad: 'x'.repeat(40000) }), bearer(h.code))).status, 413);
  assert.equal((await post(h, '/v1/events', { events: Array.from({ length: 26 }, () => ev('Stop')) }, bearer(h.code))).status, 413);
  assert.equal((await post(h, '/v1/events', '{bad', bearer(h.code))).status, 400);
});

test('限速：同一間辦公室每分鐘超過 300 筆就 429，下一分鐘恢復', async () => {
  const h = await setup();
  for (let i = 0; i < 12; i++) assert.equal((await post(h, '/v1/events', { events: Array.from({ length: 25 }, () => ev('PreToolUse', { tool_category: 'read' })) }, bearer(h.code))).status, 200);
  const r = await post(h, '/v1/events', ev('Stop'), bearer(h.code));
  assert.equal(r.status, 429);
  assert.equal(r.headers.get('Retry-After'), '60');
  h.tick(61_000);
  assert.equal((await post(h, '/v1/events', ev('Stop'), bearer(h.code))).status, 200);
});

test('讀取：派工說明與子 Agent 配對、進行中／交件、工作階段狀態、專案、增量 since', async () => {
  const h = await setup();
  const send = (o) => post(h, '/v1/events', o, bearer(h.code));
  await send(ev('SessionStart', { source: 'startup' }));
  await send(ev('UserPromptSubmit', { prompt_chars: 40, prompt_is_system: false }));
  await send(ev('PreToolUse', { tool_category: 'dispatch', subagent_type: 'frontend-ui', description: '修手機版按鈕' }));
  h.tick(1000);
  await send(ev('SubagentStart', { agent_id: 'ag1', agent_type: 'frontend-ui' }));
  await send(ev('PreToolUse', { agent_id: 'ag1', agent_type: 'frontend-ui', tool_category: 'write' }));
  await send(ev('PermissionRequest', { perm_category: 'command' }));
  let s = await (await get(h, '/v1/office/main/state', bearer(h.code))).json();
  assert.equal(s.initial, true);
  assert.equal(s.projects[0].name, 'tw-rotation');
  assert.equal(s.sessions[0].id, 'sess-1');
  assert.equal(s.sessions[0].flag, 'permission');
  assert.equal(s.sessions[0].perm, 'command');
  assert.equal(s.sessions[0].prompts, 1);
  const a = s.agents.find((x) => x.agent_id === 'ag1');
  assert.equal(a.status, 'running');
  assert.equal(a.description, '修手機版按鈕', 'SubagentStart 拿到前一筆派工的說明');
  assert.equal(a.tool, 'write');
  assert.equal(s.types[0].agent_type, 'frontend-ui');
  assert.equal(s.types[0].running, 1);
  const seq = s.seq;
  h.tick(65_000);
  await send(ev('PreToolUse', { tool_category: 'read' }));    // 主工作階段又動了：等核准的旗子收起
  await send(ev('SubagentStop', { agent_id: 'ag1', agent_type: 'frontend-ui', summary: '按鈕已修好', usage: { input: 100, output: 50, cache_write: 10, cache_read: 999 } }));
  await send(ev('Stop', { summary: '做完了', usage_main: 1234 }));
  s = await (await get(h, '/v1/office/main/state?since=' + seq, bearer(h.code))).json();
  assert.equal(s.initial, false);
  assert.deepEqual(s.events.map((e) => e.event), ['PreToolUse', 'SubagentStop', 'Stop']);
  assert.ok(s.events.every((e) => e.seq > seq));
  const b = s.agents.find((x) => x.agent_id === 'ag1');
  assert.equal(b.status, 'done');
  assert.equal(b.tokens, 160);
  assert.equal(b.duration_ms, 65_000);
  assert.equal(s.sessions[0].flag, null);
  assert.equal(s.sessions[0].state, 'idle');
  assert.equal(s.sessions[0].summary, '做完了');
  assert.equal(s.types[0].done, 1);
  assert.equal(s.ceo.turns, 1);
});

test('讀取：失敗的交件、太久沒消息的子 Agent 標成不明、問問題的旗子', async () => {
  const h = await setup();
  const send = (o) => post(h, '/v1/events', o, bearer(h.code));
  await send(ev('SubagentStart', { agent_id: 'f1', agent_type: 'reviewer' }));
  await send(ev('SubagentStop', { agent_id: 'f1', agent_type: 'reviewer', summary: '失敗：測試沒過' }));
  await send(ev('SubagentStart', { agent_id: 'old', agent_type: 'Explore' }));
  await send(ev('PreToolUse', { tool_category: 'ask' }));
  h.tick(4 * 3600e3);
  const s = await (await get(h, '/v1/office/main/state', bearer(h.code))).json();
  assert.equal(s.agents.find((x) => x.agent_id === 'f1').status, 'failed');
  assert.equal(s.agents.find((x) => x.agent_id === 'old').status, 'unknown');
  assert.equal(s.sessions[0].flag, 'question');
});

test('讀取：辦公室代號對不上 403、沒有身分 401、讀取也有限速', async () => {
  const h = await setup();
  assert.equal((await get(h, '/v1/office/other/state', bearer(h.code))).status, 403);
  assert.equal((await get(h, '/v1/office/main/state')).status, 401);
  let last;
  for (let i = 0; i < 41; i++) last = await get(h, '/v1/office/main/state', bearer(h.code));
  assert.equal(last.status, 429);
});

test('讀取：擁有者用網站登入權杖也能看；一般會員不行', async () => {
  const h = await setup();
  assert.equal((await get(h, '/v1/office/main/state', { 'X-AIO-Session': OWNER, Origin: SITE })).status, 200);
  assert.equal((await get(h, '/v1/office/main/state', { 'X-AIO-Session': MEMBER, Origin: SITE })).status, 401);
  const n = h.acc.calls.length;
  await get(h, '/v1/office/main/state', { 'X-AIO-Session': OWNER, Origin: SITE });
  assert.equal(h.acc.calls.length, n, '擁有者身分快取 10 分鐘，不每次都去問會員 Worker');
});

test('CORS：只開放自家網站；預檢請求回允許的標頭；別的網站 403', async () => {
  const h = await setup();
  const pre = await h.fetch(new Request('https://w/v1/office/main/state', { method: 'OPTIONS', headers: { Origin: SITE, 'Access-Control-Request-Method': 'GET' } }));
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get('Access-Control-Allow-Origin'), SITE);
  assert.match(pre.headers.get('Access-Control-Allow-Headers'), /authorization/);
  const gh = await get(h, '/v1/office/main/state', { ...bearer(h.code), Origin: 'https://miaozike.github.io' });
  assert.equal(gh.headers.get('Access-Control-Allow-Origin'), 'https://miaozike.github.io');
  assert.equal((await h.fetch(new Request('https://w/v1/office/main/state', { method: 'OPTIONS', headers: { Origin: 'https://evil.example' } }))).status, 403);
  const bad = await get(h, '/v1/office/main/state', { ...bearer(h.code), Origin: 'https://evil.example' });
  assert.equal(bad.status, 403);
  assert.equal(bad.headers.get('Access-Control-Allow-Origin'), null);
});

test('領碼：只有擁有者拿得到，而且只顯示一次；換新碼後舊碼立刻失效', async () => {
  const h = await setup({ noCode: true });
  assert.equal((await post(h, '/v1/claim', { t: OWNER })).status, 403, '沒有 Origin（不是從網站來的）拒絕');
  assert.equal((await post(h, '/v1/claim', { t: MEMBER }, { Origin: SITE })).status, 403);
  assert.equal((await post(h, '/v1/claim', { t: 'nobody-token-0123456789abcdef' }, { Origin: SITE })).status, 403);
  const r1 = await (await post(h, '/v1/claim', { t: OWNER }, { Origin: SITE })).json();
  assert.match(r1.code, /^aio_[A-Za-z0-9_-]{32}$/);
  assert.equal((await post(h, '/v1/events', ev('Stop'), bearer(r1.code))).status, 200);
  const r2 = await (await post(h, '/v1/claim', { t: OWNER }, { Origin: SITE })).json();
  assert.equal(r2.exists, true);
  assert.equal(r2.code, undefined, '已經領過：不再給原碼（伺服器也沒有原碼）');
  const r3 = await (await post(h, '/v1/claim', { t: OWNER, rotate: true }, { Origin: SITE })).json();
  assert.ok(r3.code && r3.code !== r1.code && r3.rotated);
  assert.equal((await post(h, '/v1/events', ev('Stop'), bearer(r1.code))).status, 401, '舊碼失效');
  assert.equal((await post(h, '/v1/events', ev('Stop'), bearer(r3.code))).status, 200);
});

test('刪除紀錄：擁有者可以清空事件，接入碼保留', async () => {
  const h = await setup();
  await post(h, '/v1/events', ev('SessionStart'), bearer(h.code));
  assert.equal((await post(h, '/v1/office/main/wipe', { t: MEMBER }, { Origin: SITE })).status, 403);
  assert.equal((await post(h, '/v1/office/main/wipe', { t: OWNER }, { Origin: SITE })).status, 200);
  const s = await (await get(h, '/v1/office/main/state', bearer(h.code))).json();
  assert.equal(s.total_events, 0);
  assert.equal(s.sessions.length, 0);
});

test('沒有綁會員 Worker：領碼回 503（不會讓任何人領走）', async () => {
  const { makeHub: mk } = await import('./harness.mjs');
  const h = mk({});
  const r = await h.fetch(new Request('https://w/v1/claim', { method: 'POST', headers: { Origin: SITE, 'Content-Type': 'application/json' }, body: JSON.stringify({ t: OWNER }) }));
  assert.equal(r.status, 503);
});
