# 驗收段落「辦公室即時模式」：AI Office 3D 辦公室（site/office/world.html）接上收件端（workers/ai-office-bridge）之後
#   ① 沒接：頂列標章寫「連接我的 Claude」、點開是連接對話框；格式不對的接入碼擋下；填網址＋接入碼 → 真的切到即時模式（存進 localStorage）
#   ② 即時：標章「即時・最後更新 HH:MM」；收件端回來的工作階段＝CEO 開工、子 Agent 進行中、名冊沒有的類型坐進後備座位、
#      等核准（頂列琥珀膠囊）、交件、第二個工作階段＝CEO 分身；示範鈕與模擬鈕藏起來；名牌上的示範等第字章拿掉
#   ③ 沒資料：標章「即時・尚未收到回報」；資訊卡數字全是 0（沒有示範任務）；績效總表是即時版、寫「樣本不足」、示範總表不打開；電力「未提供」
#   ④ 分頁在背景：暫停讀取（請求數不再增加），回到前景立刻讀一次
#   ⑤ 接入碼失效（401）：標章「接入碼失效」；展示模式可以手動切換（切過去停止讀取、示範鈕回來；再切回即時）
# 收件端用 page.route 模擬（https://aio.test），回應格式與 workers/ai-office-bridge/worker.js 的 GET /v1/office/<id>/state 一致。
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（點、填），並驗「畫面／狀態真的改變」。
# 環境變數 LIVE_SHOTS 指到資料夾時，順便把驗收畫面存成截圖（交件用）。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import time as _time
from urllib.parse import urlparse as _up, parse_qs as _pq

_AIO = "https://aio.test"
_CODE = "aio_uitest_code_0123456789abcdefABCD"
_T0 = int(_time.time() * 1000)


def _lv_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _lv_shot(pg, name):
    d = _os.environ.get("LIVE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _Fake:
    """假的收件端：依 since 回增量事件；計數每一次讀取。"""

    def __init__(self, mode="data"):
        self.mode, self.n, self.events, self.sessions, self.agents, self.types = mode, 0, [], [], [], []
        self.status = 200

    def add(self, **e):
        e.setdefault("seq", len(self.events) + 1)
        e.setdefault("rcv", _T0 + e["seq"] * 1000)
        e.setdefault("project_hash", "abcdef0123456789")
        self.events.append(e)

    def body(self, since):
        evs = [e for e in self.events if e["seq"] > since] if since else self.events[-60:]
        return {"office": "main", "now": _T0, "seq": len(self.events), "since": since, "initial": since == 0, "total_events": len(self.events),
                "last_event_at": self.events[-1]["rcv"] if self.events else None,
                "projects": [{"hash": "abcdef0123456789", "name": "tw-rotation", "first": _T0, "last": _T0, "events": len(self.events)}] if self.events else [],
                "sessions": self.sessions, "agents": self.agents, "types": self.types, "ceo": {"sessions": len(self.sessions), "prompts": 1 if self.sessions else 0, "turns": 0},
                "quota": None, "events": evs}

    def handle(self, route):
        req = route.request
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, x-aio-session", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
        u = _up(req.url)
        if u.path.endswith("/state"):
            self.n += 1
            auth = req.headers.get("authorization", "")
            if self.status != 200 or auth != "Bearer " + _CODE:
                return route.fulfill(status=401, body='{"error":"auth"}', headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"})
            since = int((_pq(u.query).get("since") or ["0"])[0])
            return route.fulfill(status=200, body=_json.dumps(self.body(since)), headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"})
        return route.fulfill(status=404, body="{}", headers={"Access-Control-Allow-Origin": "*"})


def _lv_open(b, base, fake, cfg=None, w=1280, h=800, touch=False, poll=700):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    init = "try{localStorage.setItem('aiOffice.daytime','day');" + ("localStorage.setItem('aiOffice.live.v1',%s);" % _json.dumps(_json.dumps(cfg)) if cfg else "localStorage.removeItem('aiOffice.live.v1');") + "}catch(e){}"
    c.add_init_script(init)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.route(_AIO + "/**", fake.handle)
    pg.goto(_lv_root(base) + "/office/world.html?ambient=0&q=low&pr=0.6&live_poll=%d" % poll, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
    return c, pg, got


def _badge(pg):
    return pg.evaluate("() => document.getElementById('aioTxt') && document.getElementById('aioTxt').textContent")


def _shown(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }", sel)


def _seed(f):
    sid = "sess-aaaa"
    f.sessions = [{"id": sid, "project_hash": "abcdef0123456789", "project_name": "tw-rotation", "cloud": True, "started": _T0, "last": _T0 + 5000, "ended": None, "state": "working", "flag": None, "perm": None, "prompts": 1, "turns": 0, "summary": None, "tokens": None}]
    f.agents = [
        {"agent_id": "fe1", "session_id": sid, "project_hash": "abcdef0123456789", "agent_type": "frontend-ui", "description": "修手機版頂列按鈕", "started": _T0, "last": _T0 + 4000, "ended": None, "status": "running", "tool": "write"},
        {"agent_id": "gp1", "session_id": sid, "project_hash": "abcdef0123456789", "agent_type": "general-purpose", "description": "列出檔案", "started": _T0, "last": _T0 + 4000, "ended": None, "status": "running", "tool": "other"},
    ]
    f.types = [{"agent_type": "frontend-ui", "dispatched": 1, "done": 0, "failed": 0, "running": 1, "avg_ms": None, "n_dur": 0, "tokens": None, "n_tokens": 0},
               {"agent_type": "general-purpose", "dispatched": 1, "done": 0, "failed": 0, "running": 1, "avg_ms": None, "n_dur": 0, "tokens": None, "n_tokens": 0}]
    f.add(event="SessionStart", session_id=sid)
    f.add(event="UserPromptSubmit", session_id=sid, prompt_is_system=False)
    f.add(event="PreToolUse", session_id=sid, tool_category="dispatch", subagent_type="frontend-ui", description="修手機版頂列按鈕")
    f.add(event="SubagentStart", session_id=sid, agent_id="fe1", agent_type="frontend-ui")
    f.add(event="SubagentStart", session_id=sid, agent_id="gp1", agent_type="general-purpose")
    return sid


# ───────────────────────── ① 沒接 → 連接對話框 → ② 即時 ─────────────────────────
def t_connect_and_live(b, base):
    f = _Fake()
    sid = _seed(f)
    c, pg, got = _lv_open(b, base, f)
    try:
        ok("即時：辦公室頁載入完成、即時模組在", got)
        if not got:
            return
        ok("沒接：標章寫「連接我的 Claude」", _badge(pg) == "連接我的 Claude", _badge(pg))
        ok("沒接：模式是示範、示範鈕看得到", pg.evaluate("() => __world.live.mode") == "demo" and _shown(pg, "#demoBtn"))
        ok("沒接：沒有任何讀取請求", f.n == 0, f.n)
        pg.click("#aioBadge")
        ok("沒接：點標章打開「連接我的 Claude」對話框", _shown(pg, "#aioPop") and "連接我的 Claude" in pg.inner_text("#aioPop"))
        _lv_shot(pg, "u1_沒接_連接對話框.png")
        pg.fill("#aioIn", "壞掉的 碼")
        pg.click("#aioPop [data-a=code]")
        ok("連接：格式不對的接入碼被擋下並提示", "格式不對" in pg.inner_text("#aioPop") and pg.evaluate("() => __world.live.mode") == "demo")
        pg.click("#aioPop details summary")
        pg.fill("#aioUrl", _AIO)
        pg.click("#aioPop [data-a=url]")
        pg.fill("#aioIn", _CODE)
        pg.click("#aioPop [data-a=code]")
        ok("連接：切到即時模式", wait_until(pg, "() => __world.live.mode === 'live' && __world.live.status === 'ok'", 20000), pg.evaluate("() => [__world.live.mode, __world.live.status, __world.live.msg]"))
        saved = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1') || '{}')")
        ok("連接：網址與接入碼存進這台裝置（localStorage）", saved.get("code") == _CODE and saved.get("url") == _AIO, saved)
        ok("即時：標章「即時・最後更新 HH:MM」", bool(_re.fullmatch(r"即時・最後更新 \d\d:\d\d", _badge(pg) or "")), _badge(pg))
        ok("即時：CEO 開工（工作階段進行中）", pg.evaluate("() => __world.state.session.active"))
        ok("即時：名冊上的同事（frontend-ui）接到真的任務", wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return a && a.phase !== 'idle' && a.task === '修手機版頂列按鈕'; }", 8000))
        ok("即時：名冊沒有的類型（general-purpose）自動坐進後備座位", pg.evaluate("() => { const c = __world.chars.get('x-general-purpose'); return !!c && c.homeSpot && c.homeSpot.name === 'reserve' && __world.state.agents.get('x-general-purpose').phase !== 'idle'; }"))
        ok("即時：示範鈕與模擬鈕藏起來（不讓示範事件混進真資料）", not _shown(pg, "#demoBtn"))
        ok("即時：名牌上沒有示範等第字章", pg.evaluate("() => [...document.querySelectorAll('#labels .tag .gr')].every(e => !e.textContent.trim())"))
        # 等核准
        f.add(event="PermissionRequest", session_id=sid, perm_category="command")
        ok("即時：收件端的等核准 → CEO 等你核准（頂列琥珀膠囊）", wait_until(pg, "() => __world.state.flags.permission && !document.getElementById('flBadge').hidden", 10000))
        ok("即時：等核准只顯示動作類別", "要執行一個指令" in pg.inner_text("#flBadge"), pg.inner_text("#flBadge"))
        # 交件
        f.add(event="PreToolUse", session_id=sid, tool_category="read")
        f.add(event="SubagentStop", session_id=sid, agent_id="fe1", agent_type="frontend-ui", summary="按鈕已修好")
        ok("即時：主工作階段又動了 → 等核准收起", wait_until(pg, "() => !__world.state.flags.permission", 10000))
        ok("即時：交件（frontend-ui 交件中或已完成）", wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return a.phase === 'delivering' || a.done.length > 0; }", 10000))
        _lv_shot(pg, "u2_即時_交件.png")
        # 第二個工作階段 → 分身
        f.sessions.insert(0, {"id": "sess-bbbb", "project_hash": "abcdef0123456789", "project_name": "tw-rotation", "cloud": False, "started": _T0 + 9000, "last": _T0 + 9000, "ended": None, "state": "working", "flag": None, "perm": None, "prompts": 1, "turns": 0})
        f.add(event="SessionStart", session_id="sess-bbbb")
        ok("即時：同時開著第二個工作階段 → CEO 分身出現", wait_until(pg, "() => __world.live.clones.some(c => c.sid === 'sess-bbbb' && c.ch.object3D.visible)", 10000))
        ok("即時：本尊仍是原本的工作階段", pg.evaluate("() => __world.live.primary") == sid)
        pg.click("#aioBadge")
        ok("即時：說明框列出兩個工作階段（CEO 與分身）", "CEO（分身 2）" in pg.inner_text("#aioPop") and "即時模式" in pg.inner_text("#aioPop"))
        ok("即時：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ③ 沒資料：不拿示範數字充數 ─────────────────────────
def t_nodata(b, base):
    f = _Fake()
    c, pg, got = _lv_open(b, base, f, cfg={"url": _AIO, "code": _CODE, "office": "main"})
    try:
        ok("沒資料：載入完成", got)
        if not got:
            return
        ok("沒資料：開頁就是即時模式", wait_until(pg, "() => __world.live.status === 'nodata'", 15000), pg.evaluate("() => __world.live.status"))
        ok("沒資料：標章「即時・尚未收到回報」", _badge(pg) == "即時・尚未收到回報", _badge(pg))
        ok("沒資料：電力寫「未提供」", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 未提供")
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('frontend-ui'))")
        kpi = pg.evaluate("() => [...document.querySelectorAll('#cardKpi b')].map(e => e.textContent)")
        ok("沒資料：資訊卡三格都是 0（沒有示範任務）", kpi == ["0", "0", "0"], kpi)
        ok("沒資料：資訊卡寫資料來源是即時、不推估完成時間", "即時：你的 Claude 回報的事件" in pg.inner_text("#card") and "未提供（即時模式不推估）" in pg.inner_text("#card"))
        ok("沒資料：資訊卡的績效區塊寫樣本不足、沒有示範等第", "樣本不足" in pg.inner_text("#card") and not pg.evaluate("() => !!document.querySelector('#card .gc:not(.g-na)')"))
        pg.click("#card .x")
        pg.click("#rwBtn")
        ok("沒資料：績效總表打開的是即時版（示範總表不打開）", _shown(pg, "#aioLedger") and not _shown(pg, "#ledger"))
        t = pg.inner_text("#aioLedger")
        ok("沒資料：績效總表寫「樣本不足」、沒有示範字樣", "樣本不足" in t and "示範" not in t, t[:200])
        _lv_shot(pg, "u3_沒資料_績效總表.png")
        ok("沒資料：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ④ 背景分頁暫停讀取 ─────────────────────────
def t_background(b, base):
    f = _Fake()
    _seed(f)
    c, pg, got = _lv_open(b, base, f, cfg={"url": _AIO, "code": _CODE, "office": "main"}, poll=600)
    try:
        ok("背景：載入完成", got)
        if not got:
            return
        wait_until(pg, "() => __world.live.status === 'ok'", 15000)
        n0 = f.n
        for _ in range(40):                       # 軟體繪圖很慢，計時器會被拖到；最多等 12 秒看到再讀兩次
            if f.n - n0 >= 2:
                break
            pg.wait_for_timeout(300)
        ok("背景：前景時持續讀取（每 0.6 秒排一次）", f.n - n0 >= 2, f.n - n0)
        pg.evaluate("() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' }); Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')); }")
        pg.wait_for_timeout(400)
        n1 = f.n
        pg.wait_for_timeout(3000)
        ok("背景：分頁在背景時不再讀取", f.n == n1, (n1, f.n))
        ok("背景：計時器已停", pg.evaluate("() => !__world.live.timer"))
        pg.evaluate("() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' }); Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange')); }")
        pg.wait_for_timeout(500)
        ok("背景：回到前景立刻讀一次", f.n > n1, (n1, f.n))
    finally:
        c.close()


# ───────────────────────── ⑤ 接入碼失效、展示模式 ─────────────────────────
def t_auth_and_show(b, base):
    f = _Fake()
    _seed(f)
    f.status = 401
    c, pg, got = _lv_open(b, base, f, cfg={"url": _AIO, "code": _CODE, "office": "main"})
    try:
        ok("失效：載入完成", got)
        if not got:
            return
        ok("失效：收件端回 401 → 標章「接入碼失效」", wait_until(pg, "() => __world.live.status === 'auth'", 15000) and _badge(pg) == "接入碼失效", _badge(pg))
        f.status = 200
        pg.click("#aioBadge")
        pg.click("#aioPop [data-a=now]")
        ok("失效：恢復後按「立即更新」回到正常", wait_until(pg, "() => __world.live.status === 'ok'", 10000))
        pg.click("#aioBadge") if not _shown(pg, "#aioPop") else None
        pg.click("#aioPop [data-a=show]")
        ok("展示模式：切過去＝示範模式、標章寫「展示模式」", pg.evaluate("() => __world.live.mode") == "demo" and _badge(pg) == "展示模式", _badge(pg))
        ok("展示模式：示範鈕回來", _shown(pg, "#demoBtn"))
        n0 = f.n
        pg.wait_for_timeout(2000)
        ok("展示模式：停止讀取收件端", f.n == n0, (n0, f.n))
        ok("展示模式：狀態層清空（不留真資料）", pg.evaluate("() => __world.state.agents.size === 0 && !__world.state.session.active"))
        if not _shown(pg, "#aioPop"):
            pg.click("#aioBadge")
        pg.click("#aioPop [data-a=back]")
        ok("展示模式：按「回到即時模式」又開始讀", wait_until(pg, "() => __world.live.mode === 'live' && __world.live.status === 'ok'", 10000) and f.n > n0)
        # 手機寬：標章與電力、績效總表同一排，不撐出第三排、沒有橫向捲軸
        c2, mp, got2 = _lv_open(b, base, f, cfg={"url": _AIO, "code": _CODE, "office": "main"}, w=390, h=844, touch=True)
        try:
            if got2:
                wait_until(mp, "() => __world.live.status === 'ok'", 15000)
                r = mp.evaluate("() => ['aioBadge', 'pwBtn', 'rwBtn'].map(i => { const e = document.getElementById(i); const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.right)]; })")
                ok("手機：即時標章、電力、績效總表在同一排", len({x[0] for x in r}) == 1 and max(x[1] for x in r) <= 390, r)
                ok("手機：沒有橫向捲軸", mp.evaluate("() => document.documentElement.scrollWidth <= 390"))
                _lv_shot(mp, "u4_手機_即時標章.png")
        finally:
            c2.close()
    finally:
        c.close()


def t_all(b, base):
    for fn in (t_connect_and_live, t_nodata, t_background, t_auth_and_show):
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("即時模式：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室即時模式", lambda pg, b, base, code: t_all(b, base))
