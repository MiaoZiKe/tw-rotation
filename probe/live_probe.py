# 臨時探測：正式網域台指期夜盤即時（不進 main）
import json, sys, time, os
from playwright.sync_api import sync_playwright
BASE = os.environ.get("BASE", "https://liguligu-puipui.com/")
FORCE = os.environ.get("FORCE", "1") == "1"
OUT = os.environ.get("OUT", "out")
os.makedirs(OUT, exist_ok=True)
USER = {"email": "probe@example.com", "name": "probe", "owner": True, "admin": True, "plan": "pro", "id": "u_probe"}
log = {"req": [], "resp": [], "fail": [], "console": [], "frames": []}
def now(): return time.strftime("%H:%M:%S")
with sync_playwright() as p:
    BRW = os.environ.get("BRW", "chromium"); DEV = os.environ.get("DEV", "")
    br = getattr(p, BRW).launch()
    kw = dict(p.devices[DEV]) if DEV else {"viewport": {"width": 1440, "height": 900}}
    ctx = br.new_context(timezone_id="Asia/Taipei", locale="zh-TW", **kw)
    EXTRA = json.loads(os.environ.get("EXTRA_LS", "{}"))
    if EXTRA:
        ctx.add_init_script("(() => { try { if (location.hostname.indexOf('liguligu') >= 0 && !sessionStorage.getItem('_px')) { sessionStorage.setItem('_px','1'); const o = %s; for (const k in o) localStorage.setItem(k, o[k]); } } catch (e) {} })();" % json.dumps(EXTRA))
    ctx.add_init_script("""(() => { try { if (location.hostname.indexOf('liguligu') >= 0 && !localStorage.getItem('tw.acct.tok')) {
      localStorage.setItem('tw.acct.tok', 'probe-fake-tok');
      localStorage.setItem('tw.acct.user', JSON.stringify(%s)); } } catch (e) {} })();""" % json.dumps(USER))
    def acct(route):
        u = route.request.url
        if "/v1/me" in u and "/v1/me/" not in u:
            route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps({"user": USER, "tok": "probe-fake-tok"}))
        else:
            route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body='{"ok":true}')
    ctx.route("**/v1/**", acct)
    ctx.route("**/auth/**", acct)
    if os.environ.get("BLOCK_BRIDGE") == "1":
        ctx.route("https://miaozike.github.io/tw-rotation/taifex_bridge.html*", lambda r: r.abort("failed"))
    pg = ctx.new_page()
    KEY = ("deno", "taifex", "bridge", "tw-quote", "github.io", "/fut")
    def interesting(u): return any(k in u for k in KEY)
    pg.on("console", lambda m: log["console"].append(f"{now()} [{m.type}] {m.text[:400]}"))
    pg.on("pageerror", lambda e: log["console"].append(f"{now()} [pageerror] {str(e)[:400]}"))
    def onreq(r):
        if interesting(r.url): log["req"].append(f"{now()} {r.method} {r.url} frame={r.frame.url[:80] if r.frame else ''} origin={r.headers.get('origin')}")
    def onresp(r):
        if interesting(r.url):
            h = r.headers
            log["resp"].append(f"{now()} {r.status} {r.url} acao={h.get('access-control-allow-origin')} via={h.get('x-tw-via')} xfo={h.get('x-frame-options')} csp={h.get('content-security-policy')}")
    def onfail(r):
        if interesting(r.url): log["fail"].append(f"{now()} FAIL {r.url} {r.failure}")
    pg.on("request", onreq); pg.on("response", onresp); pg.on("requestfailed", onfail)
    mainresp = pg.goto(BASE + "#overview", wait_until="domcontentloaded", timeout=60000)
    log["main_headers"] = dict(mainresp.headers) if mainresp else None
    pg.wait_for_timeout(8000)
    if FORCE:
        try: pg.evaluate("() => window.Market3 && window.Market3.forceClock && window.Market3.forceClock('night')")
        except Exception as e: log["console"].append("forceClock err " + str(e))
    pg.wait_for_timeout(int(os.environ.get("WAIT","30000")))
    st = pg.evaluate("""() => { const ss = document.getElementById('futSess'); const f = document.getElementById('twFutBridge');
      const M = window.Market3 || {};
      return { build: (document.querySelector('meta[name="tw:build"]')||{}).content, origin: location.origin,
        allowed: !!(window.TwLive && window.TwLive.allowed && window.TwLive.allowed()),
        brg: (window.Live && window.Live.taifexBridge) ? window.Live.taifexBridge() : null,
        deno: (window.Live && window.Live.taifexProxy) ? window.Live.taifexProxy() : null,
        session: M.session, shown: M.shown, via: M.futVia, dwhy: M.futDenoWhy,
        label: ss ? ss.textContent : null, why: ss ? ss.dataset.why : null, title: ss ? ss.title : null,
        iframe: f ? f.src : null,
        scripts: [...document.scripts].map(s => s.src).filter(s => /live|market3/.test(s)) }; }""")
    log["state"] = st
    log["frames"] = [f.url for f in pg.frames]
    # 直連 Deno 在頁面裡會怎麼壞
    log["direct"] = pg.evaluate("""async () => { try { const r = await fetch('https://tw-taifex.miaozike.deno.net/fut?session=night', {cache:'no-store'});
        return 'status ' + r.status + ' type ' + r.type; } catch (e) { return 'throw ' + e.name + ': ' + e.message; } }""")
    pg.screenshot(path=f"{OUT}/overview.png", full_page=False)
    try:
        card = pg.query_selector('.m3-card[data-id="FUT"]')
        if card: card.screenshot(path=f"{OUT}/futcard.png")
    except Exception: pass
    br.close()
json.dump(log, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1))
