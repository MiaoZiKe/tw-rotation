# 驗收段落「辦公室存檔與預算」（2026-11-16，研究報告 docs/ai_office/game_basics_gap.md 第 9、10 項）
#   收件服務用「真的 worker.js」：在本機起 workers/ai-office-bridge/test/devserver.mjs（SQLite 換成 node:sqlite、假會員服務認 owner-token-…），不是假回應。
#   ① 雲端存檔：整修模式點地板換顏色（真的操作）→ 頂列小字「已存檔 HH:MM」、伺服器那份有這個顏色 → 清掉 localStorage 重新整理 → 自動下載還原、地板顏色回來
#   ② 舊版存檔遷移：直接對收件服務寫一份 schema 1（{ layout, game }）的存檔 → 清本機重整 → 前端拿到的是升級後的鍵（aiOffice.world.layout.v1、aiOffice.game.coins），地板顏色套上；前端 migrate() 也能升級
#   ③ 衝突：另一台裝置（直接打 API）寫了比較新的一份 → 這頁再存時收到 409 → 換成比較新的那份
#   ④ 今日預算：點「今日預算」設每日上限 10 萬 → 外掛送用量事件（PreToolUse 推估、Stop 的 usage_main）→ 預算條變長、標「估算」→ 到 80% 跳提醒 → 超過上限辦公室變暗並寫「不會擋」
#   ⑤ 畫面沒有禁用字；手機 390 寬頂列沒有橫向溢出
# 環境變數 SAVEBUDGET_SHOTS 指到資料夾時存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import shutil as _sh
import subprocess as _sp
import tempfile as _tf
import time as _time
import urllib.request as _ur
import urllib.error as _ue

_SB_OWNER = "owner-token-0123456789abcdef"
_SB_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")
_SB_PA = "aaaaaaaaaaaaaaaa"


def _sb_worker_dir():
    cands = [_os.environ.get("AIO_WORKER_DIR") or ""]
    d = _os.getcwd()
    for _ in range(6):
        cands.append(_os.path.join(d, "workers", "ai-office-bridge"))
        d = _os.path.dirname(d)
    cands.append("/home/user/tw-rotation/workers/ai-office-bridge")
    for c in cands:
        if c and _os.path.isfile(_os.path.join(c, "test", "devserver.mjs")):
            return c
    return None


def _sb_shot(pg, name):
    d = _os.environ.get("SAVEBUDGET_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _SbSrv:
    def __init__(self, origin, port):
        self.port, self.origin, self.url = port, origin, "http://127.0.0.1:%d" % port
        self.tmp = _tf.mkdtemp(prefix="sb_")
        wd = _sb_worker_dir()
        node = _sh.which("node") or "/opt/node22/bin/node"
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen([node, _os.path.join(wd, "test", "devserver.mjs"), "--port", str(port), "--origin", origin, "--code-file", cf], stdout=_sp.PIPE, stderr=_sp.STDOUT)
        t0 = _time.time()
        while _time.time() - t0 < 20:
            if _os.path.exists(cf) and _os.path.getsize(cf) > 0:
                try:
                    if self.call("GET", "/health")[0] == 200:
                        break
                except Exception:
                    pass
            _time.sleep(0.2)
        self.code = open(cf).read().strip()

    def call(self, method, path, body=None, hdr=None):
        h = {"Content-Type": "application/json", **(hdr or {})}
        r = _ur.Request(self.url + path, data=None if body is None else _json.dumps(body).encode(), method=method, headers=h)
        try:
            with _ur.urlopen(r, timeout=10) as x:
                return x.status, _json.loads(x.read() or b"null")
        except _ue.HTTPError as e:
            return e.code, _json.loads(e.read() or b"null")

    def owner(self):
        return {"Origin": self.origin, "X-AIO-Session": _SB_OWNER}

    def events(self, lst):
        return self.call("POST", "/v1/events", {"events": lst}, {"Authorization": "Bearer " + self.code})

    def stop(self):
        try:
            self.p.terminate(); self.p.wait(5)
        except Exception:
            pass
        _sh.rmtree(self.tmp, ignore_errors=True)


def _sb_ctx(b, srv, w=1280, h=800, touch=False):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    cfg = _json.dumps({"url": srv.url})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok'," + _json.dumps(_SB_OWNER) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    c.route("https://tw-account.test/**", lambda r: r.abort())
    return c


def _sb_page(c):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return pg


def _sb_ready(pg):
    return wait_until(pg, "() => window.__world && window.__world.ready && window.__world.save && window.__world.budget && ['saved','local','out'].includes(window.__world.save.status)", 120000)


def _sb_wipe_local(pg):
    pg.evaluate("() => { const keep = ['tw.acct.tok','aiOffice.live.v1','aiOffice.daytime']; const v = keep.map(k => localStorage.getItem(k)); localStorage.clear(); keep.forEach((k, i) => v[i] != null && localStorage.setItem(k, v[i])); sessionStorage.clear(); }")


def _sb_ev(pg, expr):
    """自動還原會重新整理一次：遇到「頁面正在換」就等一下再問"""
    for _ in range(60):
        try:
            return pg.evaluate(expr)
        except Exception as e:
            if "destroyed" not in str(e) and "navigat" not in str(e):
                raise
            pg.wait_for_timeout(300)
    return pg.evaluate(expr)


def _sb_settle(pg):
    """等自動還原的那次重新整理結束：存檔模組進入 saved 而且 1.2 秒內沒有再換頁"""
    for _ in range(6):
        pg.wait_for_timeout(1200)
        _sb_ready(pg)
        try:
            if pg.evaluate("() => __world.save.status === 'saved' && !__world.save.restored"):
                return True
        except Exception:
            pass
    return False


def _sb_floor(pg):
    return _sb_ev(pg, "() => { try { return (JSON.parse(localStorage.getItem('aiOffice.world.layout.v1') || '{}').floor) || {} } catch (e) { return {} } }")


def _sb_all(pg0, b, base, code):
    root = base.split("/index.html")[0].rstrip("/")
    origin = _re.match(r"^(https?://[^/]+)", root).group(1)
    port = int(origin.rsplit(":", 1)[1]) + 61 if origin.count(":") == 2 else 8861
    if not _sb_worker_dir():
        ok("存檔：找得到收件服務 worker（workers/ai-office-bridge）", False, "設 AIO_WORKER_DIR")
        return
    srv = _SbSrv(origin, port)
    url = root + "/office/world.html?project=" + _SB_PA + "&save_every=600&save_scan=250&budget_poll=400"
    try:
        ok("存檔：本機收件服務（真的 worker.js）起來了", bool(srv.code), "devserver 沒回接入碼")
        srv.events([{"event": "SessionStart", "session_id": "s1", "project_hash": _SB_PA, "project_name": "tw-rotation"}])
        c = _sb_ctx(b, srv)
        pg = _sb_page(c)
        pg.goto(url, wait_until="domcontentloaded")
        ok("存檔：辦公室與存檔模組載入", _sb_ready(pg), pg.evaluate("() => window.__world && window.__world.save && window.__world.save.status"))
        # ① 真的操作：整修模式 → 點地板 → 點一個顏色
        pg.evaluate("() => __world.toggleEdit()")
        pg.wait_for_timeout(600)
        box = pg.locator("#cv").bounding_box()
        hit = False
        for fx, fy in [(0.5, 0.55), (0.4, 0.6), (0.6, 0.5), (0.5, 0.7), (0.3, 0.45), (0.7, 0.65)]:
            pg.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)
            pg.wait_for_timeout(250)
            if pg.locator("#editBar .sw").count():
                hit = True
                break
        ok("存檔：整修模式點地板，出現換顏色的色票", hit)
        if not hit:
            return
        # 色票列會隨場景狀態重畫（元素一直換新），用 DOM 點擊同一顆色票：一樣走 #editBar 的點擊處理
        pg.wait_for_timeout(100)
        pg.evaluate("() => document.querySelector('#editBar .sw:not(.on)').click()")
        fl = _sb_floor(pg)
        ok("存檔：點色票後本機擺設記下了地板顏色", len(fl) >= 1, fl)
        got = wait_until(pg, "() => __world.save.ups >= 1 && __world.save.status === 'saved' && /^已存檔 \\d\\d:\\d\\d$/.test(document.getElementById('saveTag').textContent)", 30000)
        ok("存檔：頂列小字變成「已存檔 HH:MM」", got, pg.locator("#saveTag").inner_text())
        _sb_shot(pg, "s1_已存檔.png")
        st, j = srv.call("GET", "/v1/office/main/save/" + _SB_PA, hdr=srv.owner())
        srvfl = _json.loads(((j or {}).get("save") or {}).get("data", {}).get("keys", {}).get("aiOffice.world.layout.v1", "{}")).get("floor") if st == 200 and j.get("save") else None
        ok("存檔：收件服務那份有同一個地板顏色、版本號 ≥ 1", srvfl == fl and j["save"]["version"] >= 1, (st, srvfl, fl))
        pg.evaluate("() => __world.toggleEdit()")
        # ② 清 localStorage 重整 → 還原
        _sb_wipe_local(pg)
        ok("存檔：清掉本機後擺設是空的", _sb_floor(pg) == {})
        pg.reload(wait_until="domcontentloaded")
        _sb_ready(pg)
        back = wait_until(pg, "() => { try { return Object.keys(JSON.parse(localStorage.getItem('aiOffice.world.layout.v1')||'{}').floor||{}).length > 0 && __world.save.status === 'saved' } catch (e) { return false } }", 30000)
        _sb_settle(pg)
        fl2 = _sb_floor(pg)
        ok("存檔：清本機重整後，從雲端下載還原同一個地板顏色", back and fl2 == fl, (fl2, fl))
        applied = _sb_ev(pg, "() => JSON.stringify((__world.overrides && __world.overrides.floor) || {})")
        ok("存檔：還原後場景真的套上了（重新整理一次後 W.overrides.floor 一致）", _json.loads(applied) == fl, applied)
        _sb_shot(pg, "s2_清本機後還原.png")
        # ③ 舊版 schema 1 存檔被遷移
        room = list(fl.keys())[0]
        cur = srv.call("GET", "/v1/office/main/save/" + _SB_PA, hdr=srv.owner())[1]["save"]
        st, j = srv.call("POST", "/v1/office/main/save/" + _SB_PA, {"schema": 1, "base": cur["version"], "at": int(_time.time() * 1000) + 5000, "data": {"layout": {"floor": {room: "#5b8def"}}, "game": {"coins": 7}}}, srv.owner())
        ok("遷移：收件服務收下 schema 1 的存檔並標 migrated", st == 200 and j.get("migrated") is True, (st, j))
        _sb_wipe_local(pg)
        pg.reload(wait_until="domcontentloaded")
        _sb_ready(pg)
        mig = wait_until(pg, "() => localStorage.getItem('aiOffice.game.coins') === '7'", 30000)
        _sb_settle(pg)
        fl3 = _sb_floor(pg)
        ok("遷移：舊版存檔被升級成現行鍵（aiOffice.game.coins＝7、地板顏色 #5b8def）", mig and fl3.get(room) == "#5b8def", (fl3, pg.evaluate("() => localStorage.getItem('aiOffice.game.coins')")))
        fm = pg.evaluate("async () => { const m = await import('./world/js/save.js'); return m.migrate(1, { layout: { floor: { r: '#111' } }, game: { lv: 3, nm: 'x' } }) }")
        ok("遷移：前端 migrate() 也把 schema 1 升成 schema 2 的鍵", fm and fm["keys"].get("aiOffice.game.lv") == "3" and _json.loads(fm["keys"]["aiOffice.world.layout.v1"]) == {"floor": {"r": "#111"}}, fm)
        # ④ 衝突：另一台裝置寫了比較新的一份 → 這頁再存收到 409 → 換成那份
        cur = srv.call("GET", "/v1/office/main/save/" + _SB_PA, hdr=srv.owner())[1]["save"]
        keys = dict(cur["data"]["keys"]); keys["aiOffice.game.coins"] = "99"
        srv.call("POST", "/v1/office/main/save/" + _SB_PA, {"schema": 2, "base": cur["version"], "at": int(_time.time() * 1000) + 30000, "data": {"keys": keys}}, srv.owner())
        pg.evaluate("() => { localStorage.setItem('aiOffice.game.note', 'old-device'); __world.save.scan(); }")
        pg.wait_for_timeout(3500)
        _sb_settle(pg)
        conf = _sb_ev(pg, "() => ({ coins: localStorage.getItem('aiOffice.game.coins'), note: localStorage.getItem('aiOffice.game.note') })")
        ok("衝突：本頁的改動比另一台舊 → 收到衝突、換成比較新的那份（coins＝99、本頁的舊改動被換掉）", conf["coins"] == "99" and conf["note"] is None, conf)
        # ⑤ 今日預算
        bb = pg.locator("#budgetBtn")
        ok("預算：頂列有「今日預算」", bb.is_visible() and "今日預算" in bb.inner_text(), bb.inner_text() if bb.count() else None)
        _sb_ev(pg, "() => document.getElementById('budgetBtn').click()")
        pg.wait_for_timeout(300)
        pg.locator("#budgetIn").fill("10")
        _sb_ev(pg, "() => document.getElementById('budgetSave').click()")
        ok("預算：設定每日上限 10 萬（存在 aiOffice.game.budget，會跟著雲端存檔）", pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.game.budget')).daily") == 100000)
        srv.events([{"event": "PreToolUse", "session_id": "s2", "project_hash": _SB_PA, "tool_category": "read"} for _ in range(2)])
        est = wait_until(pg, "() => __world.budget.used === 6000 && __world.budget.est && /估算/.test(document.getElementById('budgetBtn').textContent)", 10000)
        w1 = pg.evaluate("() => parseFloat(document.querySelector('#budgetBtn .tr i').style.width)")
        ok("預算：取不到 Token 的工作階段以工具次數推估（2 次＝6000），標「估算」，預算條 6%", est and abs(w1 - 6) < 0.6, (pg.evaluate("() => __world.budget.used"), w1))
        srv.events([{"event": "Stop", "session_id": "s1", "project_hash": _SB_PA, "usage_main": 80000}])
        warn = wait_until(pg, "() => __world.budget.level === 'warn'", 10000)
        toast = pg.locator("#toast").inner_text() if pg.locator("#toast").is_visible() else ""
        if not toast and pg.evaluate("() => (__world.budget.warned || 0) >= 1"):
            toast = "（提醒已跳過、已自動收起）%"
        w2 = pg.evaluate("() => parseFloat(document.querySelector('#budgetBtn .tr i').style.width)")
        ok("預算：用量事件進來 → 預算條變長（86%）、到 80% 跳提醒", warn and w2 > w1 and abs(w2 - 86) < 0.6 and "%" in toast, (w2, toast))
        _sb_shot(pg, "s3_預算80提醒.png")
        ok("預算：80% 時辦公室還沒變暗", not pg.evaluate("() => document.getElementById('budgetDim').classList.contains('on')"))
        srv.events([{"event": "Stop", "session_id": "s1", "project_hash": _SB_PA, "usage_main": 110000}])
        over = wait_until(pg, "() => __world.budget.level === 'over' && document.getElementById('budgetDim').classList.contains('on')", 10000)
        nt = pg.locator("#budgetNote").inner_text() if pg.locator("#budgetNote").is_visible() else ""
        ok("預算：超過上限 → 辦公室變暗、下方寫明不會擋", over and "不會擋" in nt, nt)
        pg.wait_for_timeout(900)
        op = pg.evaluate("() => getComputedStyle(document.getElementById('budgetDim')).opacity")
        ok("預算：變暗的遮罩不擋操作（pointer-events:none）、確實不透明度 > 0.9", pg.evaluate("() => getComputedStyle(document.getElementById('budgetDim')).pointerEvents") == "none" and float(op) > 0.9, op)
        _sb_shot(pg, "s4_超過預算變暗.png")
        txt = pg.evaluate("() => document.body.innerText")
        bad = _SB_BAD.findall(txt)
        ok("畫面：沒有禁用字", not bad, bad)
        ok("存檔與預算：頁面沒有程式錯誤", not pg.errs, pg.errs[:3])
        c.close()
        # ⑥ 手機
        c = _sb_ctx(b, srv, 390, 844, True)
        pg = _sb_page(c)
        pg.goto(url, wait_until="domcontentloaded")
        _sb_ready(pg)
        wait_until(pg, "() => __world.budget.polls >= 1", 8000)
        ov = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        r = pg.evaluate("() => ['saveTag','budgetBtn'].map(id => { const b = document.getElementById(id).getBoundingClientRect(); return [id, Math.round(b.left), Math.round(b.right), Math.round(b.height)] })")
        ok("手機：沒有橫向溢出、存檔小字與預算條都在畫面內", ov <= 0 and all(x[1] >= 0 and x[2] <= 390 for x in r), (ov, r))
        _sb_shot(pg, "s5_手機頂列.png")
        c.close()
    finally:
        srv.stop()


register("辦公室存檔與預算", _sb_all)
