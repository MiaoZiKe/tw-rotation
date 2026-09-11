"""產生「在瀏覽器窗格執行」的 GitHub Git Data API 推送腳本（gzip 壓縮、必要時分段）。

何時用：Claude 的執行環境連不到 api.github.com（proxy 403），但 Andy 的瀏覽器窗格連得到。
        連得到的話直接 `git push` 就好，不需要這個。

用法：python scripts/gh_push.py [--rm-prefix P]... "commit 訊息" path1 path2 ...   （路徑相對 repo 根目錄）
      token 來源：環境變數 GH_TOKEN，或 repo 根目錄的 .ghtoken（已 gitignore）。
輸出：.gh_push/push_1.js … push_N.js（gitignore）—— 依序貼到瀏覽器窗格的 javascript 工具執行；
     每段只是把 blob 上傳排進背景工作（window.__twJobs），立刻回傳，避免工具逾時；
     最後一段再多排一個 __commit 工作（等所有上傳完成後建 tree/commit/ref）。
     用 status.js 查進度。
"""
from __future__ import annotations
import base64, gzip, json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]          # repo 根目錄
SCR = Path(os.environ.get("GH_PUSH_OUT", REPO / ".gh_push"))   # 輸出目錄（gitignore）
SCR.mkdir(parents=True, exist_ok=True)
# token 只從環境變數或 repo 根目錄的 .ghtoken（gitignore）讀，永遠不寫進版控
TOKEN = os.environ.get("GH_TOKEN") or (REPO / ".ghtoken").read_text().strip()
REPO_SLUG = os.environ.get("GH_REPO", "MiaoZiKe/tw-rotation")
MAX_PART = int(os.environ.get("GH_PUSH_MAX_PART", "22000"))   # 每段腳本的位元組上限（約 8k tokens）；連線不穩時可調大讓單次送完

argv = sys.argv[1:]
rm_prefixes = []
while "--rm-prefix" in argv:
    i = argv.index("--rm-prefix"); rm_prefixes.append(argv[i + 1]); del argv[i:i + 2]
msg, paths = argv[0], argv[1:]
full_msg = msg + "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

entries = []
for p in paths:
    raw = (REPO / p).read_bytes()
    gz = base64.b64encode(gzip.compress(raw, 9)).decode()
    entries.append({"path": p, "gz": gz})

HEAD = f"""const T = {json.dumps(TOKEN)}; const R = {json.dumps(REPO_SLUG)};
const H = {{'Authorization': 'Bearer ' + T, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'}};
const api = async (m, p, b) => {{ let last; for (let i = 0; i < 8; i++) {{ try {{ const r = await fetch('https://api.github.com/repos/' + R + p, {{method: m, headers: H, body: b ? JSON.stringify(b) : undefined}}); const j = await r.json(); if (!r.ok) throw new Error(m + ' ' + p + ' → ' + r.status + ' ' + (j.message||'')); return j; }} catch (e) {{ last = e; if (!/Failed to fetch|→ 5\\d\\d/.test(String(e))) throw e; await new Promise(res => setTimeout(res, 3000 * (i + 1))); }} }} throw last; }};
const gunzip = async (b64) => {{ const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const buf = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(); const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); }};
window.__twTree = window.__twTree || []; window.__twJobs = window.__twJobs || {{}}; window.__twSrc = window.__twSrc || {{}};
const upload = (files) => {{ for (const f of files) {{ window.__twSrc[f.path] = f.gz; window.__twJobs[f.path] = 'running'; (async () => {{ try {{ const b = await api('POST', '/git/blobs', {{content: await gunzip(f.gz), encoding: 'base64'}}); window.__twTree = window.__twTree.filter(t => t.path !== f.path); window.__twTree.push({{path: f.path, mode: '100644', type: 'blob', sha: b.sha}}); window.__twJobs[f.path] = 'done'; }} catch (e) {{ window.__twJobs[f.path] = 'error: ' + e; }} }})(); }} }};
window.__twRetry = () => {{ const bad = Object.entries(window.__twJobs).filter(([k, v]) => k !== '__commit' && String(v).startsWith('error')).map(([k]) => k); upload(bad.map(k => ({{path: k, gz: window.__twSrc[k]}}))); return bad; }};
"""

FINAL = f"""window.__twJobs['__commit'] = 'waiting';
(async () => {{ try {{
  while (Object.entries(window.__twJobs).some(([k, v]) => k !== '__commit' && v === 'running')) await new Promise(r => setTimeout(r, 500));
  const bad = Object.entries(window.__twJobs).filter(([k, v]) => k !== '__commit' && String(v).startsWith('error'));
  if (bad.length) throw new Error('uploads failed: ' + bad.map(b => b[0]).join(','));
  window.__twJobs['__commit'] = 'running';
  const ref = await api('GET', '/git/ref/heads/main'); const base = ref.object.sha;
  const baseCommit = await api('GET', '/git/commits/' + base);
  const rmPrefixes = {json.dumps(rm_prefixes)};
  if (rmPrefixes.length) {{ const full = await api('GET', '/git/trees/' + baseCommit.tree.sha + '?recursive=1'); const have = new Set(window.__twTree.map(t => t.path)); for (const t of full.tree) {{ if (t.type === 'blob' && rmPrefixes.some(p => t.path.startsWith(p)) && !have.has(t.path)) window.__twTree.push({{path: t.path, mode: '100644', type: 'blob', sha: null}}); }} }}
  const newTree = await api('POST', '/git/trees', {{base_tree: baseCommit.tree.sha, tree: window.__twTree}});
  const commit = await api('POST', '/git/commits', {{message: {json.dumps(full_msg)}, tree: newTree.sha, parents: [base]}});
  await api('PATCH', '/git/refs/heads/main', {{sha: commit.sha, force: false}});
  const pushed = window.__twTree.filter(t => t.sha).map(t => t.path); const removed = window.__twTree.filter(t => !t.sha).length; window.__twTree = [];
  window.__twResult = {{pushed, removed, from: base.slice(0,7), to: commit.sha.slice(0,7)}}; window.__twJobs = {{'__commit': 'done'}};
}} catch (e) {{ window.__twJobs['__commit'] = 'error: ' + e; }} }})();
({{queued: Object.keys(window.__twJobs)}})"""

# 分段：每段放盡量多的檔案
parts: list[list[dict]] = [[]]
size = 0
for e in entries:
    n = len(e["gz"]) + len(e["path"]) + 30
    if parts[-1] and size + n > MAX_PART:
        parts.append([]); size = 0
    parts[-1].append(e); size += n

for old in SCR.glob("push_*.js"):
    old.unlink()
for i, part in enumerate(parts, 1):
    body = HEAD + "upload([\n" + ",\n".join(json.dumps(e) for e in part) + "\n]);\n"   # 一檔一行，方便分段閱讀
    body += FINAL if i == len(parts) else "({queued: Object.entries(window.__twJobs).filter(([k,v]) => v === 'running').map(([k]) => k)})"
    (SCR / f"push_{i}.js").write_text(body)
    print(f"push_{i}.js  {len(body):>6} bytes  {[e['path'] for e in part]}")

(SCR / "status.js").write_text("({jobs: window.__twJobs, staged: (window.__twTree||[]).length, result: window.__twResult || null})")
