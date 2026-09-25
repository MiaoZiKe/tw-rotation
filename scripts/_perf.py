"""載入效能量測（R6 方法；2026-09-25 perf-2 收進 repo，免得每次重寫）。
量「首次開某一頁」：FCP、boot 完成、可互動（boot 之後 5 秒內沒有新長任務的起點）、TBT、最長長任務、
每個長任務的來源函式（CDP CPU profile）、JSON 逐檔大小、script 總量。
用法：python scripts/_perf.py [--cpu 1|4] [--net none|slow] [--hash overview] [--tag name] [--site site] [--out 目錄]
      比對兩版：python scripts/_perf_matrix.py new=site old=/某處/舊版/site --cpu 1,4 --rep 3
⚠ 先要有 site/data/*.json（python -m pipeline.build_payload，SKIP_INTRADAY=1 可省分 K）。
⚠ 數字受容器負載影響很大（同一版連跑兩次可差 ±500ms），比較兩版一律交錯跑、看中位數。
"""
import argparse, json, sys, threading, time, gzip, os, collections, tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = None

ap = argparse.ArgumentParser()
ap.add_argument('--cpu', type=float, default=1)
ap.add_argument('--net', default='none')
ap.add_argument('--hash', default='overview')
ap.add_argument('--tag', default='base')
ap.add_argument('--port', type=int, default=0)
ap.add_argument('--site', default=str(Path(__file__).resolve().parent.parent / 'site'))
ap.add_argument('--out', default=str(Path(tempfile.gettempdir()) / 'tw_perf'))
ap.add_argument('--width', type=int, default=1440)
ap.add_argument('--settle', type=float, default=10)
a = ap.parse_args()
SITE = Path(a.site)
OUT = Path(a.out); (OUT / 'shots').mkdir(parents=True, exist_ok=True)


class Q(SimpleHTTPRequestHandler):
    def log_message(self, *x):
        pass


srv = ThreadingHTTPServer(('127.0.0.1', a.port), partial(Q, directory=str(SITE)))
a.port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

INIT = r"""
(() => {
  window.__R6 = { jp: [], lt: [], lag: [], marks: {} };
  const t0 = performance.now();
  // JSON 解析時間（Response.json 包一層；語意相同）
  const oj = Response.prototype.json;
  Response.prototype.json = async function () {
    const url = this.url; const txt = await this.text();
    const s = performance.now(); const o = JSON.parse(txt); const d = performance.now() - s;
    window.__R6.jp.push({ url: url.replace(/^.*\/data\//, 'data/').replace(/\?.*$/, ''), bytes: txt.length, ms: +d.toFixed(1), at: +s.toFixed(0) });
    return o;
  };
  try {
    new PerformanceObserver(l => l.getEntries().forEach(e => window.__R6.lt.push({ s: +e.startTime.toFixed(0), d: +e.duration.toFixed(0) }))).observe({ type: 'longtask', buffered: true });
  } catch (e) {}
  // 事件迴圈延遲：每 50ms 打一拍，量實際晚到多少（使用者點下去會卡多久的近似）
  let last = performance.now();
  const hb = setInterval(() => { const n = performance.now(); const lag = n - last - 50; if (lag > 50) window.__R6.lag.push({ at: +last.toFixed(0), lag: +lag.toFixed(0) }); last = n; if (n > 60000) clearInterval(hb); }, 50);
  // boot 完成點：Live.start() 在 route() 之後才被叫
  let _L;
  Object.defineProperty(window, 'Live', { configurable: true, get() { return _L; }, set(v) {
    _L = v; if (v && v.start) { const s = v.start; v.start = function () { window.__R6.marks.bootDone = performance.now(); return s.apply(this, arguments); }; } } });
  let _A;
  Object.defineProperty(window, 'App', { configurable: true, get() { return _A; }, set(v) { _A = v; if (!window.__R6.marks.app) window.__R6.marks.app = performance.now(); } });
})();
"""

CATS = ['devtools.timeline', 'disabled-by-default-devtools.timeline', 'v8.execute', 'toplevel',
        'blink.user_timing', 'loading', 'v8', 'disabled-by-default-v8.compile']

with sync_playwright() as p:
    br = p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--disable-dev-shm-usage'])
    ctx = br.new_context(viewport={'width': a.width, 'height': 900}, service_workers='block')
    pg = ctx.new_page()
    pg.add_init_script(INIT)
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console.' + m.type + ': ' + m.text) if m.type in ('error',) else None)
    cdp = ctx.new_cdp_session(pg)
    cdp.send('Network.enable')
    cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
    if a.cpu != 1:
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': a.cpu})
    if a.net == 'slow':   # 約 20Mbps／RTT 40ms（一般辦公室或 4G）
        cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 40,
                 'downloadThroughput': 20e6 / 8, 'uploadThroughput': 5e6 / 8})
    cdp.send('Profiler.enable')
    cdp.send('Profiler.setSamplingInterval', {'interval': 200})
    cdp.send('Profiler.start')
    br.start_tracing(page=pg, categories=CATS)
    t_nav = time.time()
    pg.goto(f'http://127.0.0.1:{a.port}/index.html#{a.hash}', wait_until='load', timeout=120000)
    t_load = time.time() - t_nav
    pg.wait_for_function('window.__R6 && window.__R6.marks.bootDone', timeout=120000)
    pg.wait_for_timeout(int(a.settle * 1000))
    trace = br.stop_tracing()
    prof = cdp.send('Profiler.stop')['profile']
    r6 = pg.evaluate('window.__R6')
    nav = pg.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0];
      const p = performance.getEntriesByType('paint').map(x => [x.name, +x.startTime.toFixed(0)]);
      return { dcl: +n.domContentLoadedEventEnd.toFixed(0), load: +n.loadEventEnd.toFixed(0), paint: p,
        res: performance.getEntriesByType('resource').map(r => ({ n: r.name.replace(/^http:\\/\\/[^/]+\\//, '').replace(/\\?.*$/, ''),
          t: r.initiatorType, s: +r.startTime.toFixed(0), e: +r.responseEnd.toFixed(0), sz: r.decodedBodySize })) }; }""")
    pg.screenshot(path=str(OUT / 'shots' / f'perf_{a.tag}.png'))
    br.close()
srv.shutdown()

tr = json.loads(trace)
ev = tr['traceEvents'] if isinstance(tr, dict) else tr
# 找主執行緒
tn = {}
for e in ev:
    if e.get('ph') == 'M' and e.get('name') == 'thread_name':
        tn[(e['pid'], e['tid'])] = e['args']['name']
mains = [k for k, v in tn.items() if v == 'CrRendererMain']
# 取有最多事件的那個 CrRendererMain
cnt = collections.Counter((e.get('pid'), e.get('tid')) for e in ev if (e.get('pid'), e.get('tid')) in mains)
main = cnt.most_common(1)[0][0]
mev = [e for e in ev if (e.get('pid'), e.get('tid')) == main and e.get('ph') in ('X', 'B', 'E')]
# navigationStart
ns = [e['ts'] for e in ev if e.get('name') == 'navigationStart' and (e.get('pid'), e.get('tid')) == main]
nav0 = min(ns) if ns else min(e['ts'] for e in mev)
# 以 X 事件為主（Chrome timeline 大多是 X）
X = [e for e in mev if e.get('ph') == 'X' and 'dur' in e]
tasks = [e for e in X if e['name'] == 'RunTask']
if not tasks: tasks = [e for e in X if e['name'] == 'ThreadControllerImpl::RunTask']
long = [t for t in tasks if t['dur'] > 50000]

def children(t):
    s, en = t['ts'], t['ts'] + t['dur']
    return [e for e in X if e is not t and s <= e['ts'] < en]

KEYS = {'EvaluateScript', 'v8.compile', 'v8.compileModule', 'FunctionCall', 'TimerFire', 'FireAnimationFrame', 'ParseHTML',
        'Layout', 'UpdateLayoutTree', 'Paint', 'PrePaint', 'Layerize', 'EventDispatch', 'MajorGC', 'MinorGC', 'V8.GC_MARK_COMPACTOR',
        'RunMicrotasks', 'XHRReadyStateChange', 'ResourceReceivedData', 'v8.run', 'v8.evaluateModule', 'ScheduleStyleRecalculation',
        'HitTest', 'UpdateLayerTree', 'Commit', 'ParseAuthorStyleSheet', 'v8.parseOnBackground', 'IntersectionObserverController::computeIntersections', 'ProfileCall'}

# CPU profile：每個 sample 對應函式，用來把長任務落到「哪支檔案哪個函式」
nodes = {n['id']: n for n in prof['nodes']}
parent = {}
for n in prof['nodes']:
    for c in n.get('children', []):
        parent[c] = n['id']
ts = prof['startTime']; samples = []
dts = prof['timeDeltas'][1:] + [0]
for sid, dt, w in zip(prof['samples'], prof['timeDeltas'], dts):
    ts += dt; samples.append((ts, sid, w / 1000.0))

def frame(nid):
    cf = nodes[nid]['callFrame']
    u = cf.get('url', '').replace(f'http://127.0.0.1:{a.port}/', '').split('?')[0]
    return (cf.get('functionName') or '(anonymous)', u, cf.get('lineNumber', -1) + 1)

def stack(nid):
    out = []
    while nid in nodes:
        f = frame(nid)
        out.append(f)
        nid = parent.get(nid)
        if nid is None:
            break
    return out  # leaf → root

def prof_in(s, en):
    self_c = collections.Counter(); incl = collections.Counter(); n = 0
    for t, sid, w in samples:
        if s <= t < en:
            n += 1
            st = stack(sid)
            self_c[st[0]] += w
            seen = set()
            for f in st:
                if f[1] and f not in seen:
                    seen.add(f); incl[f] += w
    return n, self_c, incl

rows = []
for t in long:
    ch = children(t)
    agg = collections.Counter(); detail = collections.Counter()
    for c in ch:
        if c['name'] in KEYS:
            agg[c['name']] += c['dur']
            d = c.get('args', {}).get('data', {}) or {}
            if c['name'] == 'EvaluateScript':
                detail['eval ' + (d.get('url', '').split('/')[-1].split('?')[0])] += c['dur']
            elif c['name'] == 'FunctionCall':
                detail[f"call {d.get('functionName') or '(anon)'} @{(d.get('url') or '').split('/')[-1].split('?')[0]}:{d.get('lineNumber')}"] += c['dur']
            elif c['name'] == 'ParseHTML':
                detail['ParseHTML'] += c['dur']
            elif c['name'] == 'TimerFire':
                detail['TimerFire'] += 0
    n, sc, inc = prof_in(t['ts'], t['ts'] + t['dur'])
    # 最有代表性的自家函式（inclusive 最高、而且不是最外層）
    top_incl = [(f"{f[0]} @{f[1]}:{f[2]}", round(c, 1)) for f, c in inc.most_common(8) if f[1]]
    top_self = [(f"{f[0]} @{f[1]}:{f[2]}", round(c, 1)) for f, c in sc.most_common(6)]
    allk = collections.Counter()
    for c in ch: allk[c['name']] += c['dur']
    evs = [(c['name'], round(c['dur']/1000,1), {k: v for k, v in (c.get('args', {}).get('data', {}) or {}).items() if k in ('url','functionName','lineNumber','timerId','type','stackTrace')}) for c in ch if c['dur'] > 5000][:25]
    rows.append({'evs': evs, 'all_ms': {k: round(v/1000) for k, v in allk.most_common(8)}, 'start_ms': round((t['ts'] - nav0) / 1000), 'dur_ms': round(t['dur'] / 1000),
                 'kinds_ms': {k: round(v / 1000) for k, v in agg.most_common(6)},
                 'detail_ms': {k: round(v / 1000) for k, v in detail.most_common(5)},
                 'prof_incl_ms': top_incl, 'prof_self_ms': top_self})

# 全程彙總：每支 JS 檔花了多少（inclusive by url 的 self time）
by_url = collections.Counter(); by_fn = collections.Counter()
for t, sid, w in samples:
    f = frame(sid)
    by_url[f[1] or f[0]] += w
    by_fn[f] += w
_n, _sc, _inc = prof_in(-1e18, 1e18)
incl_global = [(f"{f[0]} @{f[1]}:{f[2]}", round(c)) for f, c in _inc.most_common(200) if f[1] and not f[1].startswith('vendor/')][:60]
tot_kinds = collections.Counter()
for e in X:
    if e['name'] in ('EvaluateScript', 'v8.compile', 'FunctionCall', 'ParseHTML', 'Layout', 'UpdateLayoutTree', 'Paint', 'MajorGC', 'MinorGC', 'TimerFire', 'FireAnimationFrame', 'RunMicrotasks'):
        tot_kinds[e['name']] += e['dur']
fcp = dict(nav['paint']).get('first-contentful-paint')
boot = r6['marks'].get('bootDone')
# TTI 近似：bootDone 之後第一個 5 秒內沒有長任務的窗口的起點
lt_ends = sorted([(r['start_ms'], r['start_ms'] + r['dur_ms']) for r in rows])
tti = boot or 0
for s, e in lt_ends:
    if e > tti and s < tti + 5000:
        tti = e
tbt = sum(max(0, r['dur_ms'] - 50) for r in rows if fcp and r['start_ms'] >= fcp)

res = {'tag': a.tag, 'cpu': a.cpu, 'net': a.net, 'hash': a.hash, 'width': a.width,
       'fcp_ms': fcp, 'dcl_ms': nav['dcl'], 'load_ms': nav['load'], 'app_ms': round(r6['marks'].get('app', 0)),
       'boot_done_ms': round(boot or 0), 'tti_approx_ms': tti, 'tbt_ms': tbt,
       'long_tasks': len(rows), 'long_total_ms': sum(r['dur_ms'] for r in rows),
       'longest_ms': max([r['dur_ms'] for r in rows] or [0]),
       'lag_events': r6['lag'][:40],
       'json_parse': sorted(r6['jp'], key=lambda x: x['at']),
       'resources': nav['res'],
       'kinds_total_ms': {k: round(v / 1000) for k, v in tot_kinds.most_common()},
       'self_by_url_ms': [(u, round(c)) for u, c in by_url.most_common(20)],
       'self_by_fn_ms': [(f"{f[0]} @{f[1]}:{f[2]}", round(c)) for f, c in by_fn.most_common(30)],
       'rows': rows, 'errors': errs, 'incl_global': incl_global}
(OUT / f'perf_{a.tag}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: res[k] for k in ('tag', 'fcp_ms', 'dcl_ms', 'load_ms', 'app_ms', 'boot_done_ms', 'tti_approx_ms', 'tbt_ms', 'long_tasks', 'long_total_ms', 'longest_ms')}, ensure_ascii=False))
js = [r for r in nav['res'] if r['n'].endswith('.js')]
dj = [r for r in nav['res'] if r['n'].startswith('data/') and r['n'].endswith('.json')]
print('script_total_kb', round(sum(r['sz'] or 0 for r in js) / 1024), 'n', len(js), '| json_total_kb', round(sum(r['sz'] or 0 for r in dj) / 1024), 'n', len(dj))
print('json:', ', '.join(f"{r['n'].split('/')[-1]}={round((r['sz'] or 0) / 1024)}k@{r['s']}" for r in sorted(dj, key=lambda r: -(r['sz'] or 0))))
print('errors', errs[:5])
