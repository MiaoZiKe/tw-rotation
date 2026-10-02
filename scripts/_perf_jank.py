"""卡頓量測（2026-10-01，DECISIONS #284；Andy：「整體畫面卡頓有點多」）。
由 `python scripts/_perf.py --jank ...` 進入（也可直接 python scripts/_perf_jank.py）。

量三件事，全部在本機站台（site/）＋真圖表庫、Chrome DevTools Protocol：
  ① 每頁首屏：boot 完成、靜下來（2 秒無長任務）的時間、長任務（>50ms）次數／總時長、
     主執行緒忙碌比例（CDP Performance.getMetrics 的 TaskDuration ÷ 牆鐘）、JS 記憶體（GC 後）、DOM 節點數。
  ② 停留（預設總覽、資金流向各 60 秒）：攔截假 Worker（fake-worker.test）回「每輪都在跳」的報價，
     看每 5 秒一輪造成多少長任務、主執行緒忙多久、ECharts setOption／lightweight-charts setData 幾次、
     requestAnimationFrame 幾次、ResizeObserver 回呼幾次。
  ③ 切頁 N 輪：每輪後強制 GC，記 JS 記憶體、DOM 節點、存活／已脫離畫面卻沒 dispose 的圖表實例。

⚠ live.js 用台北時間判斷盤中（09:00～13:35、平日）；不在盤中時本腳本會把頁面的 Date 平移到當天 10:30 台北，
  計時器照真實時間跑（只動「現在幾點」，不動 setTimeout）。
⚠ 數字受容器負載影響（同一版連跑可差 ±30%），比較前後一律同一輪交錯跑、看 CPU 時間欄。

用法：python scripts/_perf.py --jank [--cpu 1|4] [--width 1440|390] [--pages overview,flow,...]
                               [--dwell 60] [--dwell-pages overview,flow] [--switch 10] [--only load,dwell,switch]
                               [--site site] [--tag 名稱] [--out 目錄]
"""
import argparse, json, random, threading, time, tempfile, statistics, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('--cpu', type=float, default=1)
ap.add_argument('--width', type=int, default=1440)
ap.add_argument('--pages', default='overview,flow,industry,stock/2330,themes,season,watch')
ap.add_argument('--dwell', type=float, default=60)
ap.add_argument('--dwell-pages', default='overview,flow')
ap.add_argument('--switch', type=int, default=10)
ap.add_argument('--only', default='load,dwell,switch')
ap.add_argument('--settle', type=float, default=8)
ap.add_argument('--site', default=str(Path(__file__).resolve().parent.parent / 'site'))
ap.add_argument('--tag', default='jank')
ap.add_argument('--gc-each', action='store_true', help='切頁階段每換一頁都 GC，記每一頁的監聽／節點／記憶體增量（找洩漏用）')
ap.add_argument('--warm', type=int, default=0, help='切頁階段前 N 輪不計入每頁增量（第一次進頁的建置成本不算洩漏）')
ap.add_argument('--attr', action='store_true', help='記錄 rAF／setOption／setData 的呼叫來源（有額外成本，只拿來找兇手）')
ap.add_argument('--out', default=str(Path(tempfile.gettempdir()) / 'tw_perf'))
a = ap.parse_args()
ONLY = set(a.only.split(','))
OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)


class Q(SimpleHTTPRequestHandler):
    def log_message(self, *x):
        pass


srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(Q, directory=str(a.site)))
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{PORT}/index.html'

# ---------------------------------------------------------------- 頁面內的計數器
INIT = r"""
(() => {
  const J = window.__J = { lt: [], ec: { init: 0, dispose: 0, setOption: 0, resize: 0 },
    lw: { create: 0, remove: 0, setData: 0, update: 0, applyOptions: 0 }, raf: 0, ro: 0, io: 0,
    ecSet: new Set(), lwSet: [], listeners: {} };
  // 不在盤中 → 把 Date 平移到台北 10:30（只平移「現在」，計時器照真時間）
  try {
    const s = new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }); const tp = new Date(s);
    const m = tp.getHours() * 60 + tp.getMinutes(), w = tp.getDay();
    const intr = w > 0 && w < 6 && m >= 545 && m <= 800;
    if (!intr && !window.__NOSHIFT) {
      const target = new Date(tp); target.setHours(10, 30, 0, 0);
      while (target.getDay() === 0 || target.getDay() === 6) target.setDate(target.getDate() - 1);
      const off = target - tp; const RD = Date;
      function D(...x) { if (!(this instanceof D)) return new RD(RD.now() + off).toString(); return x.length ? new RD(...x) : new RD(RD.now() + off); }
      D.prototype = RD.prototype; D.now = () => RD.now() + off; D.UTC = RD.UTC; D.parse = RD.parse;
      window.Date = D; J.shiftMs = off;
    }
  } catch (e) {}
  try { new PerformanceObserver(l => l.getEntries().forEach(e => J.lt.push([+e.startTime.toFixed(0), +e.duration.toFixed(0)]))).observe({ type: 'longtask', buffered: true }); } catch (e) {}
  J.by = {};
  const who = (k) => { if (!window.__JATTR) return; const st = (new Error().stack || '').split('\n').slice(2).map(x => x.trim()).filter(x => !/__J|_perf|vendor\/|<anonymous>/.test(x));
    const f = (k === 'raf' ? st.slice(0, 1) : st.filter(x => !/c\.setOption|inst\.setOption/.test(x)).slice(0, 2)).join(' < ') || '?'; const key = k + ' ' + f.replace(/https?:\/\/[^/]+\//g, '').replace(/\?[^:)]*/g, ''); J.by[key] = (J.by[key] || 0) + 1; };
  const rq = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = function (cb) { J.raf++; who('raf'); return rq(cb); };
  const RO = window.ResizeObserver;
  if (RO) window.ResizeObserver = class extends RO { constructor(cb) { super((...x) => { J.ro++; return cb(...x); }); } };
  const ael = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (t, f, o) {
    if (/^(scroll|mousemove|pointermove|resize|wheel|touchmove)$/.test(t)) J.listeners[t] = (J.listeners[t] || 0) + 1;
    if (window.__JATTR > 1) who('ael:' + t);
    return ael.call(this, t, f, o);
  };
  const wrapEc = (ec) => {
    if (!ec || ec.__jw) return ec; ec.__jw = 1;
    const init = ec.init;
    ec.init = function (dom) {
      const inst = init.apply(this, arguments); J.ec.init++; J.ecSet.add(inst);
      const so = inst.setOption; inst.setOption = function () { J.ec.setOption++; who('setOption'); return so.apply(this, arguments); };
      const rs = inst.resize; inst.resize = function () { J.ec.resize++; return rs.apply(this, arguments); };
      const dp = inst.dispose; inst.dispose = function () { J.ec.dispose++; J.ecSet.delete(inst); return dp.apply(this, arguments); };
      return inst;
    };
    const dis = ec.dispose;
    ec.dispose = function (x) {
      try { const inst = x && x.getDom ? x : ec.getInstanceByDom(x); if (inst && !inst.isDisposed()) { J.ec.dispose++; J.ecSet.delete(inst); } } catch (e) {}
      return dis.apply(this, arguments);
    };
    return ec;
  };
  // UMD 先指派空物件再往裡面填（factory(global.echarts = {})）→ 讀取時才包（init 已經存在才包）
  let _ec; Object.defineProperty(window, 'echarts', { configurable: true, get() { if (_ec && _ec.init && !_ec.__jw) wrapEc(_ec); return _ec; }, set(v) { _ec = v; } });
  const wrapLw = (L) => {
    if (!L || L.__jw) return L; L.__jw = 1;
    const cc = L.createChart;
    const wrapSeries = (s) => {
      if (!s || s.__jw) return s; s.__jw = 1;
      const sd = s.setData, up = s.update;
      if (sd) s.setData = function () { J.lw.setData++; who('setData'); return sd.apply(this, arguments); };
      if (up) s.update = function () { J.lw.update++; return up.apply(this, arguments); };
      return s;
    };
    const created = function (el) {
      const ch = cc.apply(this, arguments); J.lw.create++; const rec = { el: typeof el === 'string' ? document.getElementById(el) : el, ch, removed: false }; J.lwSet.push(rec);
      Object.keys(Object.getPrototypeOf(ch)).concat(Object.keys(ch)).forEach(k => {
        if (/^add.*Series$/.test(k) && typeof ch[k] === 'function') { const f = ch[k]; ch[k] = function () { return wrapSeries(f.apply(this, arguments)); }; }
      });
      const rm = ch.remove; ch.remove = function () { J.lw.remove++; rec.removed = true; return rm.apply(this, arguments); };
      const ao = ch.applyOptions; ch.applyOptions = function () { J.lw.applyOptions++; return ao.apply(this, arguments); };
      return ch;
    };
    try { Object.defineProperty(L, 'createChart', { configurable: true, writable: true, value: created }); } catch (e) { try { L.createChart = created; } catch (e2) {} }
    return L;
  };
  let _lw; Object.defineProperty(window, 'LightweightCharts', { configurable: true, get() { return _lw; }, set(v) { try { _lw = wrapLw(Object.assign({}, v)); } catch (e) { _lw = v; } } });
  window.__Jsnap = () => {
    let ecLeak = 0, ecLive = 0; const leakIds = [];
    J.ecSet.forEach(i => { try { if (i.isDisposed()) return; ecLive++; const d = i.getDom(); if (!d.isConnected) { ecLeak++; leakIds.push(d.id || ('.' + d.className)); } } catch (e) {} });
    let lwLive = 0, lwLeak = 0;
    J.lwSet.forEach(r => { if (r.removed) return; lwLive++; if (r.el && !r.el.isConnected) lwLeak++; });
    return { leakIds, ec: Object.assign({}, J.ec), lw: Object.assign({}, J.lw), raf: J.raf, ro: J.ro, ecLive, ecLeak, lwLive, lwLeak,
      dom: document.getElementsByTagName('*').length, lt: J.lt.length, ltSum: J.lt.reduce((s, x) => s + x[1], 0),
      listeners: Object.assign({}, J.listeners), by: Object.entries(J.by).sort((x, y) => y[1] - x[1]).slice(0, window.__JATTR > 1 ? 40 : 12), reqs: window.Live ? window.Live.reqs : null };
  };
})();
"""

# ---------------------------------------------------------------- 假 Worker：每一輪價格都在跳（最壞情況）
_px = {}


def fake_worker(route):
    u = urlparse(route.request.url)
    if u.path.endswith('/quote'):
        ex = (parse_qs(u.query).get('ex_ch') or [''])[0]
        arr = []
        now = time.time()
        for tok in [t for t in ex.split('|') if t]:
            c = tok.split('_', 1)[-1].split('.')[0]
            y = _px.setdefault(c + 'y', 100 + (hash(c) % 900))
            p = _px.get(c, y) * (1 + random.uniform(-0.004, 0.004))
            _px[c] = p
            arr.append({'c': c, 'n': '測' + c, 'ex': tok[:3], 'd': time.strftime('%Y%m%d'), 'z': f'{p:.2f}',
                        'tv': '3', 'y': f'{y:.2f}', 'o': f'{y:.2f}', 'h': f'{max(p, y):.2f}', 'l': f'{min(p, y):.2f}',
                        'v': str(int(now) % 100000), 't': time.strftime('%H:%M:%S'), 'tlong': str(int(now * 1000))})
        route.fulfill(status=200, content_type='application/json; charset=utf-8', body=json.dumps({'rtcode': '0000', 'msgArray': arr}))
    elif u.path.endswith('/chart'):
        # 大盤分時（market3.js fetchOne）：09:00 起每分鐘一點，最後一點每輪都在動
        cid = (parse_qs(u.query).get('id') or ['t00'])[0]
        y = 20000.0 if cid != 'o00' else 250.0
        tp = time.gmtime(time.time() + 8 * 3600)
        day0 = int(time.time() // 86400 * 86400) - 8 * 3600 + 9 * 3600    # 今天台北 09:00（UTC 毫秒基準）
        n = max(5, min(270, (tp.tm_hour - 9) * 60 + tp.tm_min)) if 9 <= tp.tm_hour < 14 else 90
        pts, c = [], y
        rnd = random.Random(cid)
        for i in range(n):
            c *= 1 + rnd.uniform(-0.001, 0.001)
            pts.append({'t': str((day0 + i * 60) * 1000), 'c': f'{c:.2f}', 's': str(rnd.randint(100, 900))})
        c *= 1 + random.uniform(-0.001, 0.001); pts[-1]['c'] = f'{c:.2f}'
        route.fulfill(status=200, content_type='application/json; charset=utf-8', body=json.dumps({
            'rtcode': '0000', 'infoArray': [{'n': cid, 'd': time.strftime('%Y%m%d'), 't': time.strftime('%H:%M:%S'),
                                             'y': f'{y:.2f}', 'o': f'{y:.2f}', 'h': f'{y * 1.01:.2f}', 'l': f'{y * .99:.2f}',
                                             'z': f'{c:.2f}', 'v': '630917'}],
            'ohlcArray': pts, 'staticObj': {'tv': '123456'}}))
    else:
        route.fulfill(status=404, body='')


def block_ext(route):
    h = urlparse(route.request.url).hostname or ''
    if h in ('127.0.0.1', 'localhost'):
        return route.continue_()
    if h == 'fake-worker.test':
        return fake_worker(route)
    return route.abort()


def new_page(br):
    ctx = br.new_context(viewport={'width': a.width, 'height': 900 if a.width > 600 else 844}, service_workers='block',
                         is_mobile=a.width < 600, has_touch=a.width < 600)
    ctx.add_init_script("try{localStorage.setItem('tw.live.proxy','https://fake-worker.test')}catch(e){}")
    if a.attr:
        ctx.add_init_script('window.__JATTR = %d;' % (2 if 'switch' in ONLY and a.only == 'switch' else 1))
    ctx.add_init_script(INIT)
    ctx.route('**/*', block_ext)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    cdp = ctx.new_cdp_session(pg)
    cdp.send('Performance.enable')
    cdp.send('HeapProfiler.enable')
    if a.cpu != 1:
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': a.cpu})
    return ctx, pg, cdp, errs


def metrics(cdp):
    m = {x['name']: x['value'] for x in cdp.send('Performance.getMetrics')['metrics']}
    return m


def heap_mb(cdp, gc=True):
    if gc:
        cdp.send('HeapProfiler.collectGarbage')
    return round(metrics(cdp)['JSHeapUsedSize'] / 1048576, 1)


def wait_quiet(pg, quiet_ms=2000, cap=60000):
    """等到「最後一個長任務結束後 quiet_ms 毫秒都沒新的」，回傳靜下來的時間點（performance.now）。"""
    t0 = time.time()
    while time.time() - t0 < cap / 1000:
        r = pg.evaluate('() => { const l = window.__J.lt; const n = performance.now(); const e = l.length ? Math.max(...l.map(x => x[0] + x[1])) : 0; return [n, e]; }')
        if r[0] - r[1] >= quiet_ms:
            return r[1]
        pg.wait_for_timeout(250)
    return None


res = {'tag': a.tag, 'cpu': a.cpu, 'width': a.width, 'load': [], 'dwell': [], 'switch': None}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--disable-dev-shm-usage'])

    # ---------------- ① 每頁首屏
    if 'load' in ONLY:
        for h in a.pages.split(','):
            ctx, pg, cdp, errs = new_page(br)
            m0 = metrics(cdp); w0 = time.time()
            pg.goto(f'{BASE}#{h}', wait_until='load', timeout=120000)
            try:
                pg.wait_for_function('window.Live && window.App', timeout=60000)
            except Exception:
                pass
            q = wait_quiet(pg, cap=int(a.settle * 1000) + 30000)
            pg.wait_for_timeout(int(a.settle * 1000))
            m1 = metrics(cdp); wall = time.time() - w0
            sn = pg.evaluate('__Jsnap()')
            fcp = pg.evaluate("() => { const e = performance.getEntriesByName('first-contentful-paint')[0]; return e ? Math.round(e.startTime) : null; }")
            lt = pg.evaluate('window.__J.lt')
            row = {'page': h, 'fcp_ms': fcp, 'quiet_ms': round(q) if q is not None else None,
                   'lt_n': len(lt), 'lt_ms': sum(x[1] for x in lt), 'lt_max': max([x[1] for x in lt] or [0]),
                   'busy_pct': round(100 * (m1['TaskDuration'] - m0['TaskDuration']) / wall, 1),
                   'script_ms': round(1000 * (m1['ScriptDuration'] - m0['ScriptDuration'])),
                   'layout_ms': round(1000 * (m1['LayoutDuration'] - m0['LayoutDuration'])),
                   'style_ms': round(1000 * (m1['RecalcStyleDuration'] - m0['RecalcStyleDuration'])),
                   'heap_mb': heap_mb(cdp), 'dom': sn['dom'], 'ec_live': sn['ecLive'], 'lw_live': sn['lwLive'],
                   'setOption': sn['ec']['setOption'], 'raf': sn['raf'], 'ro': sn['ro'], 'errs': errs[:3]}
            if a.attr: row['by'] = sn['by']
            res['load'].append(row)
            print('LOAD', json.dumps(row, ensure_ascii=False), flush=True)
            ctx.close()

    # ---------------- ② 停留：盤中即時每 5 秒一輪
    if 'dwell' in ONLY:
        for h in a.dwell_pages.split(','):
            ctx, pg, cdp, errs = new_page(br)
            pg.goto(f'{BASE}#{h}', wait_until='load', timeout=120000)
            pg.wait_for_function('window.Live && window.App', timeout=60000)
            wait_quiet(pg, cap=40000)
            pg.wait_for_timeout(3000)
            s0 = pg.evaluate('__Jsnap()'); m0 = metrics(cdp); t0 = pg.evaluate('performance.now()')
            per = []
            prev, pm = s0, m0
            for i in range(int(a.dwell // 5)):
                pg.wait_for_timeout(5000)
                s1 = pg.evaluate('__Jsnap()'); m1 = metrics(cdp)
                per.append({'lt_n': s1['lt'] - prev['lt'], 'lt_ms': s1['ltSum'] - prev['ltSum'],
                            'busy_ms': round(1000 * (m1['TaskDuration'] - pm['TaskDuration'])),
                            'script_ms': round(1000 * (m1['ScriptDuration'] - pm['ScriptDuration'])),
                            'layout_ms': round(1000 * (m1['LayoutDuration'] - pm['LayoutDuration'])),
                            'style_ms': round(1000 * (m1['RecalcStyleDuration'] - pm['RecalcStyleDuration'])),
                            'setOption': s1['ec']['setOption'] - prev['ec']['setOption'],
                            'ec_init': s1['ec']['init'] - prev['ec']['init'],
                            'lw_setData': s1['lw']['setData'] - prev['lw']['setData'],
                            'lw_update': s1['lw']['update'] - prev['lw']['update'],
                            'raf': s1['raf'] - prev['raf'], 'ro': s1['ro'] - prev['ro'],
                            'reqs': (s1['reqs'] or 0) - (prev['reqs'] or 0), 'dom': s1['dom']})
                prev, pm = s1, m1
            tot = {k: sum(x[k] for x in per) for k in per[0] if k != 'dom'}
            n = len(per)
            row = {'page': h, 'secs': n * 5, 'per5s_avg': {k: round(v / n, 1) for k, v in tot.items()},
                   'busy_pct': round(100 * tot['busy_ms'] / (n * 5000), 1), 'total': tot,
                   'heap_mb': heap_mb(cdp), 'dom_end': per[-1]['dom'], 'dom_start': s0['dom'], 'errs': errs[:3]}
            if a.attr: row['by'] = pg.evaluate('__Jsnap()')['by']
            res['dwell'].append(row)
            print('DWELL', json.dumps(row, ensure_ascii=False), flush=True)
            ctx.close()

    # ---------------- ③ 切頁 N 輪：洩漏
    if 'switch' in ONLY:
        ctx, pg, cdp, errs = new_page(br)
        pages = a.pages.split(',')
        pg.goto(f'{BASE}#{pages[0]}', wait_until='load', timeout=120000)
        pg.wait_for_function('window.Live && window.App', timeout=60000)
        wait_quiet(pg, cap=40000)
        rounds = []; per_page = {}
        m0 = metrics(cdp); w0 = time.time()
        for r in range(a.switch):
            for h in pages[1:] + pages[:1]:
                b = pg.evaluate('__Jsnap()')
                if a.gc_each:
                    cdp.send('HeapProfiler.collectGarbage'); mb = metrics(cdp)
                pg.evaluate(f"location.hash = '#{h}'")
                pg.wait_for_timeout(1500)
                e = pg.evaluate('__Jsnap()')
                if a.gc_each:
                    cdp.send('HeapProfiler.collectGarbage'); me = metrics(cdp)
                d = per_page.setdefault(h, {'ec_init': 0, 'ec_dispose': 0, 'ec_leak_new': 0, 'lw_create': 0, 'lw_remove': 0, 'dom': 0, 'leak_ids': set()})
                d['ec_init'] += e['ec']['init'] - b['ec']['init']; d['ec_dispose'] += e['ec']['dispose'] - b['ec']['dispose']
                d['ec_leak_new'] += e['ecLeak'] - b['ecLeak']; d['lw_create'] += e['lw']['create'] - b['lw']['create']
                d['lw_remove'] += e['lw']['remove'] - b['lw']['remove']; d['dom'] = e['dom']
                d['leak_ids'] |= set(e['leakIds']) - set(b['leakIds'])
                if a.gc_each and r >= a.warm:
                    d['listeners_d'] = d.get('listeners_d', 0) + int(me['JSEventListeners'] - mb['JSEventListeners'])
                    d['nodes_d'] = d.get('nodes_d', 0) + int(me['Nodes'] - mb['Nodes'])
                    d['heap_kb_d'] = d.get('heap_kb_d', 0) + int((me['JSHeapUsedSize'] - mb['JSHeapUsedSize']) / 1024)
            sn = pg.evaluate('__Jsnap()')
            rounds.append({'round': r + 1, 'heap_mb': heap_mb(cdp), 'dom': sn['dom'], 'ec_live': sn['ecLive'],
                           'ec_leak': sn['ecLeak'], 'ec_init': sn['ec']['init'], 'ec_dispose': sn['ec']['dispose'],
                           'lw_live': sn['lwLive'], 'lw_leak': sn['lwLeak'], 'lw_create': sn['lw']['create'],
                           'listeners': sn['listeners'], 'nodes_cdp': int(metrics(cdp)['Nodes']),
                           'jsListeners': int(metrics(cdp)['JSEventListeners'])})
            if a.attr:
                rounds[-1]['by'] = sn['by']
            print('SWITCH', json.dumps(rounds[-1], ensure_ascii=False), flush=True)
        m1 = metrics(cdp)
        res['switch'] = {'rounds': rounds, 'busy_pct': round(100 * (m1['TaskDuration'] - m0['TaskDuration']) / (time.time() - w0), 1),
                         'per_page': {k: dict(v, leak_ids=sorted(v['leak_ids'])[:10]) for k, v in per_page.items()}, 'errs': errs[:5]}
        print('PERPAGE', json.dumps(res['switch']['per_page'], ensure_ascii=False), flush=True)
        ctx.close()
    br.close()
srv.shutdown()
fn = OUT / f'jank_{a.tag}_w{a.width}_c{int(a.cpu)}.json'
fn.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print('寫入', fn)
