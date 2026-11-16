# 驗收段落「辦公室動作圖示與連線燈」（2026-11-16 第二批第 1～3 項）：AI 辦公室（site/office/world.html）即時模式
#   ① 真實工具事件 → 角色動作＋頭上小圖示：讀檔＝翻書（read）、寫檔＝打字（type）、跑測試＝盯螢幕（think）、搜尋＝放大鏡（magnify）、派子 Agent＝打電話（phone）；
#      閒置 N 秒（網址 ?toolanim_idle=12）圖示收起、動作回到打字；圖示上不會出現檔名或指令
#   ② 派出子 Agent：名冊沒有的新類型長出新同事，派工者（CEO）與他之間畫出連線；交件後連線淡出並移除
#   ③ 連線健康燈：正常＝綠；收件服務回 500＝紅、寫「斷線」、CEO 頭上掛「失聯」；恢復＝綠、跳「連線恢復了」、失聯圖示拿掉；示範模式不顯示燈
# 收件服務用 page.route 模擬（https://aio.test），回應格式與 workers/ai-office-bridge/worker.js 的 GET /v1/office/<id>/state 一致（含 sessions.tool／tool_at）。
# 環境變數 LIVE_SHOTS 指到資料夾時，順便存截圖。
# flake8: noqa

import json as _json
import os as _os
import time as _time
from urllib.parse import urlparse as _up, parse_qs as _pq

_TA_AIO = "https://aio.test"
_TA_CODE = "aio_uitest_code_0123456789abcdefABCD"
_TA_PH = "abcdef0123456789"
_TA_SID = "sess-ta01"


def _ta_now():
    return int(_time.time() * 1000)


class _TaFake:
    def __init__(self):
        self.events, self.agents, self.n, self.status = [], [], 0, 200
        t = _ta_now()
        self.sessions = [{"id": _TA_SID, "project_hash": _TA_PH, "project_name": "tw-rotation", "cloud": True, "started": t, "last": t, "ended": None, "state": "working", "flag": None, "perm": None, "prompts": 1, "turns": 0, "summary": None, "tokens": None, "tool": None, "tool_at": None}]

    def add(self, **e):
        e["seq"] = len(self.events) + 1
        e["rcv"] = _ta_now()
        e.setdefault("project_hash", _TA_PH)
        e.setdefault("session_id", _TA_SID)
        self.events.append(e)
        s = self.sessions[0]
        s["last"] = e["rcv"]
        if e["event"] == "PreToolUse" and not e.get("agent_id") and e.get("tool_category") not in (None, "ask"):
            s["tool"], s["tool_at"] = e["tool_category"], e["rcv"]

    def body(self, since):
        evs = [e for e in self.events if e["seq"] > since] if since else self.events[-60:]
        types = sorted({a["agent_type"] for a in self.agents})
        return {"office": "main", "now": _ta_now(), "seq": len(self.events), "since": since, "initial": since == 0, "total_events": len(self.events),
                "last_event_at": self.events[-1]["rcv"] if self.events else None, "project": None,
                "projects": [{"hash": _TA_PH, "name": "tw-rotation", "first": _ta_now(), "last": _ta_now(), "events": len(self.events)}],
                "sessions": self.sessions, "agents": self.agents,
                "types": [{"agent_type": t, "dispatched": 1, "done": 0, "failed": 0, "running": 1} for t in types],
                "ceo": {"sessions": 1, "prompts": 1, "turns": 0}, "roster": [], "quota": None, "events": evs,
                "inbox": {"queued": 0, "active": 0, "rev": 0, "last_pull": None}}

    def handle(self, route):
        req = route.request
        H = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, x-aio-session", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
        u = _up(req.url)
        if u.path.endswith("/state"):
            self.n += 1
            if self.status != 200:
                return route.fulfill(status=self.status, body='{"error":"boom"}', headers=H)
            since = int((_pq(u.query).get("since") or ["0"])[0])
            return route.fulfill(status=200, body=_json.dumps(self.body(since)), headers=H)
        return route.fulfill(status=404, body="{}", headers=H)


def _ta_shot(pg, name):
    d = _os.environ.get("LIVE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


_TA_ICON = "(w) => { const x = (__world.toolanim.state() || []).find(q => q.who === w); return x ? x.cat : null; }"
_TA_ACT = "(w) => { const c = __world.chars.get(w); return c ? [c.state, c.action] : null; }"


def _ta_wait_icon(pg, who, cat, ms=12000):
    return wait_until(pg, "() => (%s)(%s) === %s" % (_TA_ICON, _json.dumps(who), _json.dumps(cat)), ms)


def t_office_toolanim(b, base):
    f = _TaFake()
    f.add(event="SessionStart")
    f.add(event="UserPromptSubmit", prompt_is_system=False)
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 1280, "height": 800})
    cfg = {"url": _TA_AIO, "office": "main", "code": _TA_CODE}
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.game.tour','1');localStorage.setItem('aiOffice.live.v1',%s);}catch(e){}" % _json.dumps(_json.dumps(cfg)))
    pg = c.new_page()
    pg.set_default_timeout(120000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(_TA_AIO + "/**", f.handle)
    try:
        pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6&live_poll=600&toolanim_idle=12", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.toolanim && window.__world.health", 90000)
        ok("動作圖示：辦公室載入、三支新模組都在（toolanim／links／health）", got)
        if not got:
            return
        ok("即時：接上假收件服務", wait_until(pg, "() => __world.live.mode === 'live' && __world.live.status === 'ok'", 20000), pg.evaluate("() => [__world.live.mode, __world.live.status, __world.live.msg]"))
        wait_until(pg, "() => { const c = __world.chars.get('ceo'); return c && c.state === 'sit'; }", 30000)
        ceo_sit = pg.evaluate("() => __world.chars.get('ceo').state") == "sit"
        # ① 主工作階段的工具類別 → CEO 動作＋圖示
        for cat, act, name in (("read", "read", "讀檔＝翻書"), ("write", "type", "寫檔＝打字"), ("test", "think", "跑測試＝盯螢幕"), ("search", "magnify", "搜尋＝放大鏡")):
            f.add(event="PreToolUse", tool_category=cat)
            hit = _ta_wait_icon(pg, "ceo", cat)
            st = pg.evaluate(_TA_ACT, "ceo")
            ok("動作圖示：%s（CEO 頭上圖示 %s、動作 %s）" % (name, cat, act), hit and (not ceo_sit or st[1] == act), [pg.evaluate("() => __world.toolanim.state()"), st])
            if cat == "test":
                pg.wait_for_timeout(400)
                _ta_shot(pg, "ta1_CEO跑測試_盯螢幕圖示.png")
        pg.wait_for_timeout(700)
        icon_ok = pg.evaluate("() => { const e = document.querySelector('#taLayer .ta-i[data-who=ceo]'); if (!e) return null; const r = e.getBoundingClientRect(); return { w: r.width, vis: getComputedStyle(e).display !== 'none' && r.left > 0 && r.top > 0, title: e.title }; }")
        ok("動作圖示：圖示真的畫在畫面上（看得到、在視窗內）", icon_ok and icon_ok["w"] >= 20 and icon_ok["vis"], icon_ok)
        ok("動作圖示：圖示只寫工具種類，不含檔名或指令", icon_ok and icon_ok["title"] in ("搜尋中",), icon_ok)
        # ② 派子 Agent：CEO 打電話 → 新同事出現 → 連線
        f.add(event="PreToolUse", tool_category="dispatch", subagent_type="qa-runner", description="跑一輪驗收")
        hit = _ta_wait_icon(pg, "ceo", "dispatch")
        st = pg.evaluate(_TA_ACT, "ceo")
        ok("動作圖示：派子 Agent＝打電話（圖示 dispatch、動作 phone）", hit and (not ceo_sit or st[1] == "phone"), st)
        n_before = pg.evaluate("() => __world.chars.size")
        t = _ta_now()
        f.agents = [{"agent_id": "agq1", "session_id": _TA_SID, "project_hash": _TA_PH, "agent_type": "qa-runner", "description": "跑一輪驗收", "started": t, "last": t, "ended": None, "status": "running", "tool": None, "tool_at": None}]
        f.add(event="SubagentStart", agent_id="agq1", agent_type="qa-runner")
        got_link = wait_until(pg, "() => (__world.links.state() || []).some(x => x.aid === 'agq1' && !x.ending && x.from === 'ceo' && x.to)", 15000)
        who = pg.evaluate("() => { const id = __world.state.byAgentId.get('agq1'); return id || null; }")
        ok("子 Agent：名冊沒有的類型長出新同事（角色數增加、對得到代號）", who and pg.evaluate("(w) => !!__world.chars.get(w)", who) and pg.evaluate("() => __world.chars.size") >= n_before, [who, n_before, pg.evaluate("() => __world.chars.size")])
        ok("子 Agent：派工者（CEO）與新同事之間出現連線", got_link, pg.evaluate("() => __world.links.state()"))
        drawn = wait_until(pg, "() => { const g = document.querySelector('#lkLayer g[data-aid=agq1]'); const p = g && g.querySelector('path:not(.halo)'); return p && p.getAttribute('d') && g.style.display !== 'none' && p.getBoundingClientRect().width > 4; }", 8000)
        ok("子 Agent：連線真的畫在畫面上（SVG 弧線有長度）", drawn, pg.evaluate("() => __world.links.state()"))
        f.add(event="PreToolUse", agent_id="agq1", agent_type="qa-runner", tool_category="test")
        ok("動作圖示：子 Agent 的工具事件掛在他自己頭上（跑測試）", who and _ta_wait_icon(pg, who, "test"), pg.evaluate("() => __world.toolanim.state()"))
        pg.wait_for_timeout(500)
        _ta_shot(pg, "ta2_派子Agent_連線與圖示.png")
        # 閒置 12 秒 → CEO 圖示收起、動作回打字
        gone = wait_until(pg, "() => (%s)('ceo') === null" % _TA_ICON, 30000)
        st = pg.evaluate(_TA_ACT, "ceo")
        ok("動作圖示：閒置 N 秒後 CEO 圖示收起、工具動作結束（回打字或日常小動作，不再停在打電話／放大鏡）", gone and (not ceo_sit or st[1] not in ("phone", "magnify", "read", "think")), st)
        # 交件 → 連線淡出、移除
        f.agents[0].update(status="done", ended=_ta_now())
        f.add(event="SubagentStop", agent_id="agq1", agent_type="qa-runner", summary="驗收全過")
        ending = wait_until(pg, "() => (__world.links.state() || []).some(x => x.aid === 'agq1' && x.ending)", 10000)
        ok("子 Agent：交件後連線進入淡出", ending, pg.evaluate("() => __world.links.state()"))
        ok("子 Agent：淡出完成後連線移除", wait_until(pg, "() => !(__world.links.state() || []).some(x => x.aid === 'agq1') && !document.querySelector('#lkLayer g[data-aid=agq1]')", 6000), pg.evaluate("() => __world.links.state()"))
        # ③ 連線健康燈
        f.add(event="PreToolUse", tool_category="read")
        g = wait_until(pg, "() => __world.health.level === 'g' && !document.getElementById('aioHealth').hidden", 10000)
        ok("連線燈：正常時是綠燈、頂列看得到", g, pg.evaluate("() => [__world.health.level, __world.health.text]"))
        hl = pg.evaluate("() => { const e = document.getElementById('aioHealth'), b = document.getElementById('aioBadge'); const r = e.getBoundingClientRect(), q = b.getBoundingClientRect(); return { w: r.width, overlap: !(r.right <= q.left || r.left >= q.right || r.bottom <= q.top || r.top >= q.bottom), txt: e.textContent }; }")
        ok("連線燈：在頂列、不壓到「即時」標章", hl["w"] > 10 and not hl["overlap"], hl)
        f.status = 500
        red = wait_until(pg, "() => __world.health.level === 'r'", 15000)
        txt = pg.evaluate("() => [__world.health.text, document.getElementById('aioHlTxt').textContent, document.getElementById('aioHealth').className]")
        ok("連線燈：收件服務出錯 → 紅燈、明講「斷線」與自動重連", red and "斷線" in txt[0] and "重連" in txt[0] and " r" in txt[2], txt)
        ok("連線燈：斷線時 CEO 頭上掛「失聯」，不假裝在工作", wait_until(pg, "() => (%s)('ceo') === 'lost'" % _TA_ICON, 4000), pg.evaluate("() => __world.toolanim.state()"))
        n0 = f.n
        pg.wait_for_timeout(3500)
        ok("連線燈：斷線期間自動重試（指數退避，請求仍持續但變慢）", f.n > n0 and pg.evaluate("() => __world.live.fails") >= 2, [f.n - n0, pg.evaluate("() => __world.live.fails")])
        _ta_shot(pg, "ta3_斷線紅燈_失聯.png")
        f.status = 200
        f.add(event="PreToolUse", tool_category="write")
        pg.click("#aioHealth")   # 按燈＝立刻重試
        green = wait_until(pg, "() => __world.health.level === 'g'", 20000)
        ok("連線燈：恢復 → 綠燈、計一次恢復", green and pg.evaluate("() => __world.health.nUp") >= 1, pg.evaluate("() => [__world.health.level, __world.health.text, __world.health.nUp]"))
        ok("連線燈：恢復後「失聯」圖示拿掉", wait_until(pg, "() => (%s)('ceo') !== 'lost'" % _TA_ICON, 4000), pg.evaluate("() => __world.toolanim.state()"))
        toast = pg.evaluate("() => __world.health.lastToast === '連線恢復了'")
        ok("連線燈：恢復時跳出「連線恢復了」提示", toast)
        _ta_shot(pg, "ta4_恢復綠燈.png")
        # 示範模式：燈不顯示
        pg.evaluate("() => __world.live.enterDemo()")
        ok("連線燈：示範模式不顯示", wait_until(pg, "() => document.getElementById('aioHealth').hidden", 4000))
        bad = [w for w in ("價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵") if w in pg.evaluate("() => (document.getElementById('aioHealth').title || '') + document.getElementById('taLayer').innerText")]
        ok("動作圖示／連線燈：畫面沒有禁用字", not bad, bad)
        ok("動作圖示：過程沒有頁面錯誤", not errs, errs[:3])
    finally:
        c.close()
    # 手機寬：燈只剩圓點、不撐爆頂列
    f2 = _TaFake()
    f2.add(event="SessionStart")
    f2.add(event="PreToolUse", tool_category="read")
    c2 = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    c2.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.game.tour','1');localStorage.setItem('aiOffice.live.v1',%s);}catch(e){}" % _json.dumps(_json.dumps(cfg)))
    pg = c2.new_page()
    pg.route(_TA_AIO + "/**", f2.handle)
    try:
        pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6&live_poll=600", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.health && window.__world.health.level === 'g'", 90000)
        m = pg.evaluate("() => { const e = document.getElementById('aioHealth'); const r = e.getBoundingClientRect(); return { w: r.width, right: r.right, vw: innerWidth, sw: document.documentElement.scrollWidth, span: getComputedStyle(e.querySelector('span')).display }; }") if got else None
        ok("連線燈（手機 390）：綠燈、只剩圓點、沒有橫向捲動", got and m["span"] == "none" and m["right"] <= m["vw"] and m["sw"] <= m["vw"], m)
        _ta_shot(pg, "ta5_手機_綠燈.png")
    finally:
        c2.close()


register("辦公室動作圖示與連線燈", lambda pg, b, base, code: t_office_toolanim(b, base))
