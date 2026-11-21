/* 本機開發／端到端用：在 127.0.0.1 起一個「真的 worker.js」（SQLite 換成 node:sqlite），不需要 Cloudflare 帳號。
 *
 *   node workers/ai-office-bridge/test/devserver.mjs --port 8787 --origin http://127.0.0.1:8000 --code-file /tmp/x/code.txt
 *
 * --code-file：啟動時直接發一組接入碼寫進這個檔（只給本機測試；正式環境只能由擁有者登入網站領碼）。
 * --origin：允許的瀏覽器來源（可以給多個，逗號分隔），本機開的辦公室頁要列在這裡。
 */
import http from 'node:http';
import { writeFileSync } from 'node:fs';
import { makeHub, fakeAccount } from './harness.mjs';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const port = +arg('--port', '8787');
const origins = String(arg('--origin', 'http://127.0.0.1:8000')).split(',').join(' ');
const h = makeHub({ ALLOWED_ORIGINS: origins, ACCOUNT: fakeAccount() });
const codeFile = arg('--code-file', '');
if (codeFile) writeFileSync(codeFile, await h.hub.devIssue());

http.createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;
  const headers = new Headers(); for (const [k, v] of Object.entries(req.headers)) if (typeof v === 'string') headers.set(k, v);
  const r = await h.fetch(new Request('http://127.0.0.1:' + port + req.url, { method: req.method, headers, body: req.method === 'GET' || req.method === 'HEAD' ? undefined : body }));
  const out = Buffer.from(await r.arrayBuffer());
  res.writeHead(r.status, Object.fromEntries(r.headers.entries()));
  res.end(out);
}).listen(port, '127.0.0.1', () => console.log('ai-office-bridge 本機收件端：http://127.0.0.1:' + port));
