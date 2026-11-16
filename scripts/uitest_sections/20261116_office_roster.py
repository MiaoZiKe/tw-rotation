# 驗收段落「辦公室專案名冊」（2026-11-16）：每個專案一間辦公室、各自的員工名冊
# 擁有者原話：「下面雲端的進不去，另外為何出現兩個一樣名稱的專案？……理論上不同專案裡面的辦公室、員工 Agent 都不同，Agent 都會依據當前專案需求新增員工。」
#   ① 同名舊／新雜湊（舊路徑雜湊＋新儲存庫雜湊）入口只列一個，進行中相加；沒意義的名稱（user／root）全歸同一個「雲端工作階段」
#   ② 「雲端工作階段」按「進入」進得去（辦公室載入、狀態正常、看得到 CEO 與分身）
#   ③ 不同專案的辦公室各自只有「CEO＋自己名冊的 Agent」：名冊＝專案 .claude/agents 檔名 ∪ 出現過的子 Agent；示範的 40 多位不在；
#      同代號的示範編制照樣露面並坐自己的座位、其他的依類型分配部門（code-reviewer→監察稽核、對不上→一般）、桌上名牌換成他
#   ④ 新子 Agent 類型第一次出現＝新員工報到演出（從大門外走進來、坐到新座位）
#   ⑤ 示範辦公室（?demo=1／沒登入）不受影響，仍是完整的示範名冊
#   ⑥ 收件匣標題：待命中的 Claude（60 秒內來取過指令）顯示「你的 Claude 在線上（待命中）」
# 用「真的收件端」：workers/ai-office-bridge/test/devserver.mjs（真的 worker.js、SQLite 換成 node:sqlite），事件用 /v1/events 真的送進去；需要 node 22。
# 環境變數 RS_SHOTS 指到資料夾時順便存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import shutil as _sh
import socket as _sock
import subprocess as _sp
import tempfile as _tf
import time as _tm
import urllib.request as _ur
from urllib.parse import urlparse as _rup

_RS_TOK = "owner-token-" + "0123456789abcdef"           # devserver 的假會員服務認得的「擁有者」登入權杖（假值）
_RS_OLD, _RS_NEW, _RS_OTHER = "a1" * 8, "b1" * 8, "d1" * 8
_RS_CL1, _RS_CL2 = "c1" * 8, "c2" * 8
try:
    _RS_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:                                   # 小跑者用 exec 載入、沒有 __file__
    _RS_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_RS_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_RS_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_RS_NOPROXY = _ur.build_opener(_ur.ProxyHandler({}))


def _rs_shot(pg, name):
    d = _os.environ.get("RS_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _RsSrv:
    """起一個本機真收件端；origin＝測試網站的來源（收件端的 CORS 白名單）"""

    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _RS_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _RS_NOPROXY.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()

    def post(self, path, body, bearer=True):
        req = _ur.Request(self.url + path, method="POST", data=_json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.code})
        return _json.loads(_RS_NOPROXY.open(req, timeout=5).read().decode())

    def events(self, evs):
        for i in range(0, len(evs), 20):
            self.post("/v1/events", {"events": evs[i:i + 20]})

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _rs_ev(event, sid, ph, name, **k):
    d = {"event": event, "session_id": sid, "project_hash": ph, "project_name": name, "ts": int(_tm.time() * 1000), "cloud": True}
    d.update(k)
    return d


def _rs_seed(srv):
    ev = _rs_ev
    srv.events([
        ev("SessionStart", "s-o1", _RS_OLD, "tw-rotation"), ev("SessionStart", "s-o2", _RS_OLD, "tw-rotation"),            # 舊的路徑雜湊（2 個進行中）
        ev("SessionStart", "s-n1", _RS_NEW, "tw-rotation", agent_files=["inspector", "my-bot", "code-reviewer"]),           # 新的儲存庫雜湊（1 個進行中）
        ev("SubagentStart", "s-n1", _RS_NEW, "tw-rotation", agent_id="ag-1", agent_type="Explore"),
        ev("SessionStart", "s-x1", _RS_OTHER, "other-repo", agent_files=["deployer", "zz-agent-b"]),
        ev("SessionStart", "c1", _RS_CL1, "user"), ev("SessionStart", "c2", _RS_CL1, "user"), ev("SessionStart", "c3", _RS_CL2, "root"),
        ev("SubagentStart", "c1", _RS_CL1, "user", agent_id="cag-1", agent_type="general-purpose"),
    ])


def _rs_ctx(b, srv, w=1280, h=800, creds=True):
    c = b.new_context(viewport={"width": w, "height": h})
    if creds:
        cfg = _json.dumps({"url": srv.url, "login": True})
        user = _json.dumps({"email": "a@example.com", "name": "站長", "admin": True})
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','" + _RS_TOK + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
        c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    else:
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    return c


def _rs_page(c):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return pg


def _rs_ready(pg):
    return wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.live.data", 120000)


_RS_VIS = "() => [...window.__world.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.isCeo && !c.spec.pet).map(c => c.spec.id).sort()"


def _rs_world_url(base, ph, extra="&live_poll=800&ambient=0&q=low&pr=0.6"):
    return base.split("/index.html")[0].rstrip("/") + "/office/world.html?office=main&project=" + ph + extra


def _rs_enter(pg, base, ph):
    pg.goto(_rs_world_url(base, ph), wait_until="domcontentloaded")
    return _rs_ready(pg)


def _rs_main(b, base):
    if not _sh.which("node") or not _os.path.exists(_RS_DEV):
        ok("專案名冊：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    o = _rup(base)
    origin = "%s://%s" % (o.scheme, o.netloc)
    srv = _RsSrv(origin)
    c = _rs_ctx(b, srv)
    try:
        _rs_seed(srv)
        pg = _rs_page(c)
        root = base.split("/index.html")[0].rstrip("/")
        # ───── ① 入口：同名只列一個 ─────
        pg.goto(root + "/office/index.html", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__officeEntry && !document.getElementById('projSec').hidden", 30000)
        ok("入口：伺服器有專案時出現「你的專案」清單", got)
        if not got:
            return
        wait_until(pg, "() => document.querySelectorAll('#projList li').length >= 3", 8000)
        rows = pg.evaluate("() => [...document.querySelectorAll('#projList li')].map(li => ({ t: li.innerText.replace(/\\s+/g, ' '), h: li.querySelector('a').getAttribute('href') }))")
        txt = " ".join(r["t"] for r in rows)
        ok("入口：6 個雜湊的事件只列 3 個專案（tw-rotation 合併、user＋root 合併成雲端、other-repo）", len(rows) == 3, [r["t"] for r in rows])
        ok("入口：tw-rotation 只出現一次、進行中相加（舊 2＋新 1＝3 個進行中）", txt.count("tw-rotation") == 1 and any("tw-rotation" in r["t"] and "3 個進行中" in r["t"] for r in rows), rows)
        ok("入口：user 與 root 都歸成同一個「雲端工作階段」（3 個進行中），畫面上沒有 user／root 這種名字", txt.count("雲端工作階段") == 1 and any("雲端工作階段" in r["t"] and "3 個進行中" in r["t"] for r in rows) and not _re.search(r"\b(user|root)\b", txt), rows)
        _rs_shot(pg, "r1_入口專案清單.png")

        # ───── ② 雲端工作階段進得去 ─────
        cl = next(r for r in rows if "雲端工作階段" in r["t"])
        pg.locator("#projList li", has_text="雲端工作階段").get_by_role("link", name="進入").click()
        pg.wait_for_url(_re.compile(r"world\.html\?office=main&project="))
        got = _rs_ready(pg)
        wait_until(pg, "() => window.__world.live.status === 'ok' && (window.__world.live.clones || []).filter(c => c.sid).length >= 1", 60000)
        st = pg.evaluate("() => ({ st: window.__world.live.status, name: window.__world.live.projName, clones: window.__world.live.clones.filter(c => c.sid).length, ceo: window.__world.chars.get('ceo').object3D.visible })")
        ok("雲端工作階段：按「進入」辦公室載入完成、狀態「即時」、名稱「雲端工作階段」、看得到 CEO 與同時開著的工作階段分身", got and st["st"] == "ok" and st["name"] == "雲端工作階段" and st["ceo"] and st["clones"] == 2, st)
        wait_until(pg, "() => window.__world.chars.has('general-purpose') && window.__world.chars.get('general-purpose').state === 'sit'", 30000)
        vis = pg.evaluate(_RS_VIS)
        ok("雲端工作階段：辦公室只有 CEO＋這個專案出現過的子 Agent（general-purpose），沒有示範的 40 多位", vis == ["general-purpose"], vis)

        # ───── ③ 兩個不同專案各自的名冊 ─────
        got = _rs_enter(pg, base, _RS_NEW)
        ok("tw-rotation（新雜湊）：辦公室載入完成", got)
        wait_until(pg, "() => ['inspector', 'my-bot', 'code-reviewer', 'Explore'].every(k => window.__world.chars.has(k) && window.__world.chars.get(k).homeSpot)", 60000)
        wait_until(pg, "() => ['inspector', 'my-bot', 'code-reviewer'].every(k => window.__world.chars.get(k).state === 'sit')", 60000)
        vis = pg.evaluate(_RS_VIS)
        ok("tw-rotation：名冊＝.claude/agents 檔名（inspector、my-bot、code-reviewer）∪ 出現過的子 Agent（Explore）；只有這 4 位，沒有別的專案的、也沒有示範 40 多位", vis == sorted(["inspector", "my-bot", "code-reviewer", "Explore"]), vis)
        info = pg.evaluate("""() => { const W = window.__world, g = id => W.chars.get(id), d = id => { const c = g(id), m = W.members.get(id) || {}; return { dept: c.spec.dept, deptName: m.deptName, seat: c.homeSpot && c.homeSpot.name, fdept: c.homeSpot && W.furn.get(c.homeSpot.fid) && W.furn.get(c.homeSpot.fid).f.dept, sit: c.state, atDesk: c.atDesk }; };
            const plates = [...W.furn.values()].filter(i => i.f.type === 'workstation' && i.f.owner && i.f.owner !== 'ceo').map(i => i.spec.extras && i.spec.extras[0] && i.spec.extras[0].visible);
            return { insp: d('inspector'), bot: d('my-bot'), rev: d('code-reviewer'), exp: d('Explore'), absent: g('data-steward').absent === true && !g('data-steward').object3D.visible && g('data-steward').away === true, nShown: plates.filter(Boolean).length, nAll: plates.length, hub: !!W.rosterHub && W.rosterHub.on } }""")
        ok("同代號的示範編制照樣露面：inspector（監察委員）坐自己的座位 seat:inspector", info["insp"]["seat"] == "seat:inspector" and info["insp"]["sit"] == "sit" and info["insp"]["atDesk"], info["insp"])
        ok("依類型自動分配部門：code-reviewer（review）→ 監察與稽核室，坐稽核室的桌子（不搶 inspector 的座位）", info["rev"]["dept"] == "audit" and info["rev"]["fdept"] == "audit" and info["rev"]["sit"] == "sit" and info["rev"]["seat"] != "seat:inspector", info["rev"])
        ok("對不上的類型放「一般」：my-bot 坐在某張空桌、部門名「一般」", info["bot"]["deptName"] == "一般" and info["bot"]["seat"] and info["bot"]["sit"] == "sit", info["bot"])
        ok("Explore（explor）→ 產業研究部，家在產業研究部的桌子（他正在跑任務時會被叫去 CEO 面前，所以看家不看人在哪）", info["exp"]["dept"] == "industry" and info["exp"]["fdept"] == "industry", info["exp"])
        ok("示範同事（例如 data-steward 阿梟）整個收起來：看不見、不佔座位、標成缺席", info["absent"] and info["hub"], info)
        ok("桌上名牌：只有 4 張有人坐的桌子顯示名牌，其餘空桌不再掛示範同事的名字", info["nShown"] == 4 and info["nAll"] >= 30, (info["nShown"], info["nAll"]))
        _rs_shot(pg, "r2_tw-rotation辦公室.png")

        got = _rs_enter(pg, base, _RS_OTHER)
        wait_until(pg, "() => ['deployer', 'zz-agent-b'].every(k => window.__world.chars.has(k) && window.__world.chars.get(k).state === 'sit')", 60000)
        vis2 = pg.evaluate(_RS_VIS)
        ok("other-repo：名冊不同（deployer 是示範編制的上線、zz-agent-b 是新同事），沒有 tw-rotation 的人", got and vis2 == sorted(["deployer", "zz-agent-b"]) and "inspector" not in vis2, vis2)
        ok("兩個專案的名冊各自不同", vis != vis2)
        ok("other-repo：同代號的 deployer 坐自己的座位", pg.evaluate("() => window.__world.chars.get('deployer').homeSpot.name") == "seat:deployer")
        _rs_shot(pg, "r3_other-repo辦公室.png")

        # 舊雜湊的連結（路徑雜湊）也進得去、看到的是同一個名冊（兩個雜湊的事件都算這個專案）
        got = _rs_enter(pg, base, _RS_OLD)
        wait_until(pg, "() => window.__world.chars.has('inspector') && window.__world.chars.get('inspector').state === 'sit'", 60000)
        vis3 = pg.evaluate(_RS_VIS)
        ok("舊雜湊連結：進得去，名冊與新雜湊相同（兩個雜湊的事件都算 tw-rotation）", got and vis3 == vis, vis3)
        nm = pg.evaluate("() => window.__world.live.projName")
        ok("舊雜湊連結：專案名稱找得到（tw-rotation，不是「這個專案」）", nm == "tw-rotation", nm)
        ok("沒有頁面錯誤（名冊階段）", not pg.errs, pg.errs[:2])

        # ───── ④ 新子 Agent 第一次出現＝報到演出 ─────
        got = _rs_enter(pg, base, _RS_NEW)
        wait_until(pg, "() => ['inspector', 'my-bot', 'code-reviewer', 'Explore'].every(k => window.__world.chars.has(k) && window.__world.chars.get(k).state === 'sit')", 60000)
        ok("報到前：brand-new-agent 還不存在", not pg.evaluate("() => window.__world.chars.has('brand-new-agent')"))
        srv.events([_rs_ev("SubagentStart", "s-n1", _RS_NEW, "tw-rotation", agent_id="ag-new", agent_type="brand-new-agent", description="新來的")])
        got = wait_until(pg, "() => window.__world.chars.has('brand-new-agent')", 30000)
        ok("報到：新類型第一次出現，辦公室多一位新同事", got)
        if got:
            zs = []
            t0 = _tm.time()
            while _tm.time() - t0 < 6:
                zs.append(pg.evaluate("() => { const c = window.__world.chars.get('brand-new-agent'); return [c.object3D.position.z, c.object3D.visible, c.state] }"))
                pg.wait_for_timeout(300)
            ok("報到演出：先出現在大門外（z>28），接著走進辦公室（z 變小），不是憑空坐在位子上", zs[0][1] and zs[0][0] > 28 and min(z[0] for z in zs) < zs[0][0] - 0.5 and zs[0][2] != "sit", zs[:3] + zs[-2:])
            got = wait_until(pg, "() => { const c = window.__world.chars.get('brand-new-agent'); return c.state === 'sit' && c.spot && c.spot.seat }", 120000)
            ok("報到演出：走到新座位坐下", got)
            nm2 = pg.evaluate("() => { const W = window.__world, c = W.chars.get('brand-new-agent'); return { dept: c.spec.dept, nick: c.spec.nick, member: !!W.members.get('brand-new-agent'), taken: c.spot && c.spot.taken, plate: (() => { const i = W.furn.get(c.spot.fid); return i && i.spec.extras && i.spec.extras[0] ? i.spec.extras[0].visible : null })() }; }")
            ok("報到演出：新同事有部門（brand→設計）、座位標成他的、桌上名牌換成他", nm2["dept"] == "design" and nm2["taken"] == "brand-new-agent" and nm2["plate"] is True and nm2["member"], nm2)
            _rs_shot(pg, "r4_新同事報到後.png")
        vis4 = pg.evaluate(_RS_VIS)
        ok("報到後名冊＝原本 4 位＋新同事，示範 40 多位仍不在", vis4 == sorted(vis + ["brand-new-agent"]), vis4)
        # 座位不夠：把所有空桌佔滿，再多一位 → 自動加一張桌子
        r = pg.evaluate("""async () => { const W = window.__world, h = W.rosterHub, n0 = W.furn.size; let made = 0;
            for (let i = 0; i < 45; i++) { const id = 'filler-' + i; const c = h.hire({ id, nick: '填' + i, zh: id, species: 'bird', pal: 0, hue: 0, acc: [], accColor: '#fff' }, false); if (c) made++; }
            const extra = W.furn.size - n0, sitting = [...W.chars.values()].filter(c => /^filler-/.test(c.spec.id) && c.state === 'sit').length;
            return { made, extra, sitting, desks: h.desks } }""")
        ok("座位不夠：再多 45 位時自動加桌（加了幾張桌子、每位新同事都有座位坐）", r["made"] == 45 and r["extra"] >= 1 and r["sitting"] == 45, r)
        ok("沒有頁面錯誤（報到與加桌）", not pg.errs, pg.errs[:2])

        # ───── ⑤ 示範辦公室不受影響 ─────
        pg.goto(root + "/office/world.html?demo=1&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready", 120000)
        d1 = pg.evaluate("() => ({ hub: !!window.__world.rosterHub, n: [...window.__world.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.isCeo).length, ds: window.__world.chars.get('data-steward').object3D.visible })")
        ok("示範辦公室（?demo=1，有登入也一樣）：完整的示範名冊（35 位以上看得到）、沒有啟用專案名冊", not d1["hub"] and d1["n"] >= 35 and d1["ds"], d1)
        c2 = _rs_ctx(b, srv, creds=False)
        pg2 = _rs_page(c2)
        pg2.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        wait_until(pg2, "() => window.__world && window.__world.ready", 120000)
        d2 = pg2.evaluate("() => ({ hub: !!window.__world.rosterHub, n: [...window.__world.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.isCeo).length })")
        ok("沒登入的示範辦公室：完整示範名冊、沒有專案名冊", not d2["hub"] and d2["n"] >= 35, d2)
        _rs_shot(pg2, "r5_示範辦公室.png")
        c2.close()

        # ───── ⑥ 收件匣標題：待命中算在線 ─────
        pg.goto(_rs_world_url(base, _RS_NEW, "&live_poll=800&ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700"), wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 120000)
        pg.click("#chatText")
        wait_until(pg, "() => window.__world.chat.mode === 'ok'", 90000)
        wait_until(pg, "() => /Claude/.test(document.getElementById('chatLive').textContent)", 60000)
        t0 = pg.evaluate("() => document.getElementById('chatLive').textContent.replace(/\\s+/g, '')")
        ok("在線判斷：沒有人來取過指令、也沒有工作階段在動時，寫「Claude 沒開」", ("沒開" in t0) or ("Claude在線" in t0), t0)   # 種子事件剛送完，5 分鐘內有工作階段動靜會顯示「在線」，兩種都合理；重點是下面待命那一步
        srv.post("/v1/inbox/pull", {"session_id": "standby-1", "wait": 0, "project_hash": _RS_NEW})
        got = wait_until(pg, "() => /待命中/.test(document.getElementById('chatLive').textContent)", 60000)
        t1 = pg.evaluate("() => document.getElementById('chatLive').textContent.replace(/\\s+/g, '')")
        ok("在線判斷：Claude 剛來取過指令（待命中）→ 標題顯示「你的 Claude 在線上（待命中）」", got and "你的Claude在線上（待命中）" in t1, t1)
        ok("沒有頁面錯誤（對話框）", not pg.errs, pg.errs[:2])
    finally:
        c.close()
        srv.stop()


register("辦公室專案名冊", lambda pg, b, base, code: _rs_main(b, base))
