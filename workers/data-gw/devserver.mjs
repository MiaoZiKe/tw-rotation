/* 本機的 data-gw：跑真的 worker.js，R2 換成本機資料夾、account-api 換成本機的 devserver。
 *
 * 用法：
 *   node workers/account-api/devserver.mjs --port 8790 --origin http://127.0.0.1:8767
 *   node workers/data-gw/devserver.mjs --port 8791 --origin http://127.0.0.1:8767 --account http://127.0.0.1:8790 --data site/data
 * GW_SECRET 用每次啟動隨機產生的值（不是正式金鑰，也不寫進任何檔案）。
 */
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { randomBytes } from 'node:crypto';
import { makeGw } from './harness.mjs';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const PORT = +arg('port', 8791), ORIGIN = arg('origin', 'http://127.0.0.1:8767');
const DIR = resolve(arg('data', 'site/data'));
const R2 = { async get(k) { try { const s = readFileSync(join(DIR, k), 'utf8'); return { text: async () => s }; } catch (e) { return null; } } };
const { gw } = makeGw({ ALLOWED_ORIGINS: ORIGIN, ACCOUNT_API_URL: arg('account', 'http://127.0.0.1:8790'), ACCOUNT_ORIGIN: ORIGIN,
  GW_SECRET: randomBytes(32).toString('base64url'), DATA: R2, GUEST_CACHE_MS: arg('guest-cache-ms', '60000') });

http.createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const body = Buffer.concat(chunks);
  const headers = new Headers(); for (const [k, v] of Object.entries(req.headers)) headers.set(k, String(v));
  headers.set('CF-Connecting-IP', req.socket.remoteAddress.replace(/^::ffff:/, ''));
  const r = await gw.fetch(new Request(`http://127.0.0.1:${PORT}${req.url}`, { method: req.method, headers, body: ['GET', 'HEAD', 'OPTIONS'].includes(req.method) ? undefined : body }));
  res.writeHead(r.status, Object.fromEntries(r.headers)); res.end(Buffer.from(await r.arrayBuffer()));
}).listen(PORT, '127.0.0.1', () => console.log(`data-gw devserver http://127.0.0.1:${PORT}（資料夾 ${DIR}）`));
