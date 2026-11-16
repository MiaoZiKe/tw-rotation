# 驗收段落「辦公室專案區塊」（2026-11-16）：新專案的辦公室只有「CEO 區塊＋每位 Agent 一個區塊＋運動場＋無業遊民區」
# 擁有者原話：「我如果開一個新專案，舉例來說我只派幫我規劃咖啡廳，那他只會有 CEO 和 規劃的 Agent 或是 驗證資料的 Agent，
#   在 AI Office 內只會出現 3 個 Block，其他的運動場、無業遊民區，而非用我現有的 Block」
#   ① 咖啡廳專案（名稱不是 tw-rotation）：區塊數＝1（CEO）＋Agent 數；沒有示範的部門房間、會議室、茶水間、佈告欄、示範員工；運動場與無業遊民區照在
#   ② 區塊名稱用派工說明（任務簡稱），沒有說明才用類型名；每個 Agent 坐在自己區塊的桌子前
#   ③ 新 Agent 出現（事件送進收件端）→ 區塊 +1、同排自動置中、名冊多一位，不必重新整理；區塊名稱可後補
#   ④ 運動場能用（有場地、人可以走過去）、火焰（著火只對存在的家具）、拎人、對話框照常
#   ⑤ tw-rotation 專案仍是原本完整的辦公室（部門房間、示範座位）
# 用「真的收件端」（workers/ai-office-bridge/test/devserver.mjs，需 node 22）；環境變數 PB_SHOTS 指到資料夾時存俯瞰截圖。
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
from urllib.parse import urlparse as _pup

_PB_TOK = "owner-token-" + "0123456789abcdef"
_PB_COFFEE, _PB_TW = "e1" * 8, "f1" * 8
try:
    _PB_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _PB_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_PB_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_PB_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_PB_NOPROXY = _ur.build_opener(_ur.ProxyHandler({}))


def _pb_shot(pg, name):
    d = _os.environ.get("PB_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _PbSrv:
    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _PB_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _PB_NOPROXY.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()

    def events(self, evs):
        req = _ur.Request(self.url + "/v1/events", method="POST", data=_json.dumps({"events": evs}).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.code})
        _PB_NOPROXY.open(req, timeout=5).read()

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _pb_ev(event, sid, ph, name, **k):
    d = {"event": event, "session_id": sid, "project_hash": ph, "project_name": name, "ts": int(_tm.time() * 1000), "cloud": True}
    d.update(k)
    return d


_PB_STATE = """() => { const W = window.__world, B = W.blocks;
  const rooms = W.layout.rooms.map(r => ({ id: r.id, name: r.name, kind: r.kind }));
  const vis = [...W.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.isCeo && !c.spec.pet).map(c => ({ id: c.spec.id, sit: c.state === 'sit', at: c.homeSpot && c.homeSpot.name, fid: c.homeSpot && c.homeSpot.fid }));
  const types = {}; for (const i of W.furn.values()) types[i.f.type] = (types[i.f.type] || 0) + 1;
  return { blocks: !!B, n: B ? B.count() : 0, rooms, vis, types, sports: !!(W.sports && W.sports.venues && W.sports.venues.length) || !!W.sports, jobless: !!W.outside, chars: W.chars.size } }"""


_PB_FLOOR = """() => { const W = window.__world, B = W.blocks, T = W.THREE; const rayHit = rc => { const hs = []; W.scene.traverse(o => { if (o.isMesh && !o.isInstancedMesh && o.visible && o.geometry && o.geometry.attributes.position) { try { for (const h of rc.intersectObject(o, false)) hs.push(h); } catch (e) { /* 略 */ } } }); hs.sort((a, b) => a.distance - b.distance); const h = hs[0]; if (!h) return null; const ca = h.object.geometry.attributes.color; if (!ca) return { beige: false }; const i = h.face.a; return { beige: ca.getX(i) > ca.getY(i) + 0.02 && ca.getZ(i) < ca.getY(i) }; }; if (!B) { const rc = new T.Raycaster(), hit = (x, z) => { rc.set(new T.Vector3(x, 20, z), new T.Vector3(0, -1, 0)); const h = rayHit(rc); return !!(h && h.beige); }; return { tw: true, w: W.layout.size.w, d: W.layout.size.d, slab: hit(40.6, 15), grass: hit(44.5, 15), mid: hit(20, 15) }; }
  const f = B.floor(), rs = W.layout.rooms; let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const r of rs) { x0 = Math.min(x0, r.x); x1 = Math.max(x1, r.x + r.w); z0 = Math.min(z0, r.z); z1 = Math.max(z1, r.z + r.d); }
  const m = [f.x0 - x0, x1 - f.x1, f.z0 - z0].map(v => Math.abs(v)), fit = Math.abs(f.x0 - (x0 - 2.2)) < 0.05 && Math.abs(f.x1 - (x1 + 2.2)) < 0.05 && Math.abs(f.z0 - (z0 - 2.2)) < 0.05 && f.z1 >= z1 + 2.2 - 0.05 && f.z1 <= 30.6;
  const rc = new T.Raycaster(), hit = (x, z) => { rc.set(new T.Vector3(x, 20, z), new T.Vector3(0, -1, 0)); const h = rayHit(rc); return !!(h && h.beige); };
  return { f, fit, w: f.x1 - f.x0, d: f.z1 - f.z0, hitIn: hit((x0 + x1) / 2, (z0 + z1) / 2 + 1), hitFar: hit(1.0, 3.0) } }"""

_PB_SCEN = """() => { const W = window.__world, S = W.scenery; if (!S) return { none: true };
  const rd = (r, x, z) => Math.hypot(Math.max(r.x0 - x, 0, x - r.x1), Math.max(r.z0 - z, 0, z - r.z1));
  const rects = [...S.rects]; for (const r of W.layout.rooms) rects.push({ x0: r.x, x1: r.x + r.w, z0: r.z, z1: r.z + r.d, k: 'room' }); if (W.blocks) { const f = W.blocks.floor(); rects.push({ ...f, k: 'floor' }); }
  const items = S.objs.filter(o => o.kind !== 'lake'), lakes = S.objs.filter(o => o.kind === 'lake'), kinds = {}; for (const o of items) kinds[o.kind] = (kinds[o.kind] || 0) + 1;
  const hit = []; for (const o of items) for (const r of rects) if (rd(r, o.x, o.z) < 0.3) hit.push([o.kind, r.k, +o.x.toFixed(1), +o.z.toFixed(1)]);
  const lk = []; for (const L of lakes) { for (let k = 0; k < 48; k++) { const a = k / 48 * 6.283, x = L.x + Math.cos(a) * L.rx, z = L.z + Math.sin(a) * L.rz; for (const r of rects) if (rd(r, x, z) < 0.3) lk.push([r.k, +x.toFixed(1), +z.toFixed(1)]); } }
  const inLake = []; for (const o of items) for (const L of lakes) { const dx = (o.x - L.x) / L.rx, dz = (o.z - L.z) / L.rz; if (dx * dx + dz * dz < 1) inLake.push([o.kind, +o.x.toFixed(1), +o.z.toFixed(1)]); }
  const g = S.mesh && S.mesh.geometry, tri = g ? (g.index ? g.index.count : g.attributes.position.count) / 3 : 0, m = W.scene.getObjectByName('scenery');
  return { n: items.length, max: S.max, lakes: lakes.length, kinds, hit: hit.slice(0, 5), lk: lk.slice(0, 5), inLake: inLake.slice(0, 5), tri, mesh: !!m, deco: W.outdoorDeco, bbox: S.bbox, shadow: !!(S.mesh && S.mesh.castShadow), pick: W.pickFurn.includes(S.mesh) } }"""


def _pb_ctx(b, srv):
    c = b.new_context(viewport={"width": 1280, "height": 800})
    cfg = _json.dumps({"url": srv.url, "login": True})
    user = _json.dumps({"email": "a@example.com", "name": "站長", "admin": True})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','" + _PB_TOK + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    return c


def _pb_enter(pg, base, ph):
    root = base.split("/index.html")[0].rstrip("/")
    pg.goto(root + "/office/world.html?office=main&project=" + ph + "&live_poll=800&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
    return wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.live.data", 120000)


def _pb_main(b, base):
    if not _sh.which("node") or not _os.path.exists(_PB_DEV):
        ok("專案區塊：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    o = _pup(base)
    srv = _PbSrv("%s://%s" % (o.scheme, o.netloc))
    c = _pb_ctx(b, srv)
    try:
        srv.events([
            _pb_ev("SessionStart", "cf1", _PB_COFFEE, "coffee-shop"),
            _pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-1", agent_type="planner", description="規劃咖啡廳動線與座位"),
            _pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-2", agent_type="data-verifier", description="驗證菜單成本資料"),
            _pb_ev("SessionStart", "tw1", _PB_TW, "tw-rotation", agent_files=["inspector", "my-bot"]),
        ])
        pg = c.new_page()
        pg.set_default_timeout(60000)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if _os.environ.get("PB_DEBUG"):
            pg.on("pageerror", lambda e: print("PAGEERR", getattr(e, "stack", e)[:600]))
            pg.on("console", lambda m: print("CONSOLE", m.type, m.text[:300], (m.args[0].evaluate("e => e && e.stack") if m.args and m.type == "error" else "")) if m.type in ("error", "warning") else None)

        # ───── ① 咖啡廳專案：CEO＋2 位 Agent ＝ 3 個區塊 ─────
        got = _pb_enter(pg, base, _PB_COFFEE)
        ok("咖啡廳專案：辦公室載入完成", got)
        wait_until(pg, "() => window.__world.blocks && window.__world.blocks.count() >= 3 && ['planner', 'data-verifier'].every(k => { const c = window.__world.chars.get(k); return c && c.state === 'sit'; })", 60000)
        s = pg.evaluate(_PB_STATE)
        ok("咖啡廳專案：啟用區塊辦公室（W.blocks）", s["blocks"], s)
        ok("咖啡廳專案：區塊數＝1（CEO）＋2 位 Agent ＝ 3", s["n"] == 3 and len(s["rooms"]) == 3, s["rooms"])
        names = [r["name"] for r in s["rooms"]]
        ok("咖啡廳專案：區塊名稱用派工說明（中文任務簡稱），不是英文類型名", any("規劃咖啡廳" in n for n in names) and any("驗證菜單" in n for n in names) and "planner" not in " ".join(names), names)
        bad = [r for r in s["rooms"] if r["id"] in ("meeting", "library", "pantry", "food", "lobby", "lounge", "play", "reserve", "video", "social", "design", "frontend", "industry", "quant", "biz", "ops", "audit", "data", "legal")]
        ok("咖啡廳專案：沒有示範的部門房間、會議室、茶水間、食物區等", not bad, bad)
        ok("咖啡廳專案：沒有示範的佈告欄、沙發、會議桌、白板、冰箱、遊戲機", not any(k in s["types"] for k in ("board", "meeting_table", "whiteboard", "sofa", "fridge", "arcade", "counter", "dining", "pingpong", "bookshelf_x")) and s["types"].get("workstation") == 2 and s["types"].get("ceo_desk") == 1, s["types"])
        ok("咖啡廳專案：看得到的同事只有這 2 位 Agent，各坐自己區塊的桌子，沒有示範的 40 多位", sorted(v["id"] for v in s["vis"]) == ["data-verifier", "planner"] and all(v["sit"] and v["at"] == "seat:" + v["id"] for v in s["vis"]), s["vis"])
        ok("咖啡廳專案：員工運動場不生成（新專案先不開放）、無業遊民區照在", (not s["sports"]) and s["jobless"], s)
        # 區塊置中、同排左右對稱
        pos = pg.evaluate("() => window.__world.layout.rooms.map(r => ({ id: r.id, cx: r.x + r.w / 2, z: r.z }))")
        ag = sorted([p for p in pos if p["id"].startswith("blk_")], key=lambda p: p["cx"])
        ok("咖啡廳專案：2 個 Agent 區塊同一排、左右對稱置中（CEO 在正下方）", len(ag) == 2 and abs((ag[0]["cx"] + ag[1]["cx"]) / 2 - 20.5) < 0.01 and ag[0]["z"] == ag[1]["z"] and ag[0]["z"] < next(p["z"] for p in pos if p["id"] == "ceo"), pos)
        # 鏡頭初始框住全部：3 個區塊、運動場、遊民區都在畫面內
        inview = pg.evaluate("""() => { const W = window.__world, cam = W.camera; cam.updateMatrixWorld(); const out = [];
          const pts = W.layout.rooms.map(r => [r.x + r.w / 2, r.z + r.d / 2, r.id]).concat([[30, 35, 'jobless']]);
          for (const [x, z, id] of pts) { const v = cam.position.clone().set(x, 0.3, z).project(cam); out.push({ id, ok: v.z < 1 && Math.abs(v.x) < 0.98 && Math.abs(v.y) < 0.98 }); } return out; }""")
        ok("咖啡廳專案：鏡頭一進場就框住全部（區塊、無業遊民區都在畫面內）", all(p["ok"] for p in inview), inview)
        sc0 = pg.evaluate(_PB_SCEN)
        ok("咖啡廳專案：戶外景觀有生成（W.outdoorDeco>0）、有灌木、花叢、圓冠樹、松樹、石頭，無業遊民區自身的長椅與營火仍在", (not sc0.get("none")) and sc0["deco"] > 0 and all(sc0["kinds"].get(k, 0) > 0 for k in ("bush", "flower", "tree", "pine", "rock")) and pg.evaluate("() => { const W = window.__world; return !!W.outside && W.outside.seats.length >= 4 && !!W.outside.flame }"), sc0)
        ok("咖啡廳專案：有湖泊（2 個）、物件數 ≤ 上限、合併成單一網格（三角面 < 15 萬）、不投影、不進可點選清單", sc0["lakes"] == 2 and sc0["n"] <= sc0["max"] and sc0["mesh"] and sc0["tri"] < 150000 and not sc0["shadow"] and not sc0["pick"], sc0)
        ok("咖啡廳專案：景觀不壓到地板鋪面、區塊、遊民區、大門步道，樹不在湖裡，湖不壓到鋪面", not sc0["hit"] and not sc0["lk"] and not sc0["inLake"], [sc0["hit"], sc0["lk"], sc0["inLake"]])
        _pb_shot(pg, "pb1_咖啡廳規劃專案_俯瞰.png")
        pg.wait_for_timeout(2000)   # 地板約 0.6 秒平順長到最終範圍
        fl0 = pg.evaluate(_PB_FLOOR)
        ok("咖啡廳專案：外圍米色地板範圍 ≈ 區塊包圍盒＋邊距（不是固定 40×30），空地沒有了", fl0["fit"] and fl0["w"] < 36 and fl0["d"] < 24, fl0)
        ok("咖啡廳專案：區塊中心有米色鋪面、原本 40×30 之外的角落沒有", fl0["hitIn"] and not fl0["hitFar"], fl0)

        # ───── ② 新 Agent 即時長出新區塊（不重新整理）─────
        srv.events([_pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-3", agent_type="menu-writer", description="撰寫菜單文案")])
        got = wait_until(pg, "() => window.__world.blocks.count() >= 4 && window.__world.chars.has('menu-writer') && window.__world.chars.get('menu-writer').state === 'sit'", 60000)
        s2 = pg.evaluate(_PB_STATE)
        ok("新 Agent 加入：區塊 +1（3→4），不必重新整理", got and s2["n"] == 4 and len(s2["rooms"]) == 4, s2["rooms"])
        pos2 = pg.evaluate("() => window.__world.layout.rooms.filter(r => r.id.startsWith('blk_')).map(r => ({ cx: r.x + r.w / 2, z: r.z })).sort((a, b) => a.cx - b.cx)")
        ok("新 Agent 加入：同一排的 3 個區塊重新置中、等距（原本兩個往左右挪）", len(pos2) == 3 and abs(pos2[1]["cx"] - 20.5) < 0.01 and abs((pos2[1]["cx"] - pos2[0]["cx"]) - (pos2[2]["cx"] - pos2[1]["cx"])) < 0.01, pos2)
        ok("新 Agent 加入：舊的兩位座位跟著區塊搬（家在新位置；坐著的就坐在桌前，跑任務被叫去 CEO 面前的不算）", pg.evaluate("""() => ['planner', 'data-verifier', 'menu-writer'].every(k => { const c = window.__world.chars.get(k), s = c.homeSpot; return s && window.__world.spots.includes(s) && (!(c.state === 'sit' && c.atDesk) || Math.hypot(c.object3D.position.x - s.seat.x, c.object3D.position.z - s.seat.z) < 0.6); })"""))
        # 區塊名稱後補：先沒有說明、之後才拿到
        srv.events([_pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-4", agent_type="zz-late")])
        wait_until(pg, "() => window.__world.blocks.count() >= 5", 40000)
        n0 = pg.evaluate("() => window.__world.layout.rooms.filter(r => r.id.startsWith('blk_')).map(r => r.name)")
        ok("沒有派工說明的 Agent：區塊先用類型名（zz late）", any(_re.search(r"zz.late", n) for n in n0), n0)
        pg.wait_for_timeout(1500)   # 地板約 0.6 秒平順長到新範圍
        fl1 = pg.evaluate(_PB_FLOOR)
        ok("加到 4 位 Agent 後：地板跟著變大（比 2 位時寬），仍貼合區塊包圍盒", fl1["fit"] and fl1["w"] > fl0["w"] + 4, [fl0["w"], fl1["w"]])
        _pb_shot(pg, "pb2_新Agent長出新區塊.png")
        # 跟 tw-rotation 示範編制同代號（inspector）的新 Agent：用自己的代號與區塊，不借用示範那位
        srv.events([_pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-5", agent_type="inspector", description="檢查咖啡豆庫存表")])
        wait_until(pg, "() => window.__world.blocks.count() >= 6 && window.__world.chars.has('inspector') && window.__world.chars.get('inspector').state === 'sit'", 40000)
        ins = pg.evaluate("() => { const c = window.__world.chars.get('inspector'); return { zh: c.spec.zh, nick: c.spec.nick, seat: c.homeSpot && c.homeSpot.name, shown: !c.away && c.object3D.visible, room: window.__world.layout.rooms.filter(r => r.id.startsWith('blk_')).map(r => r.name) } }")
        ok("同代號（inspector）的新 Agent：用自己的名牌與區塊，不是 tw-rotation 的監察委員", ins["zh"] == "inspector" and ins["shown"] and ins["seat"] == "seat:inspector" and any("咖啡豆" in n for n in ins["room"]), ins)
        # 再加一位（共 6 位 Agent）：地板繼續跟著擴，截圖留底
        srv.events([_pb_ev("SubagentStart", "cf1", _PB_COFFEE, "coffee-shop", agent_id="cag-6", agent_type="tester", description="試做新菜單")])
        wait_until(pg, "() => window.__world.blocks.count() >= 7 && window.__world.chars.has('tester') && window.__world.chars.get('tester').state === 'sit'", 40000)
        pg.wait_for_timeout(1500)
        fl2 = pg.evaluate(_PB_FLOOR)
        ok("加到 6 位 Agent 後：地板再變大、仍貼合區塊包圍盒、遠角沒有米色空地", fl2["fit"] and fl2["w"] > fl1["w"] + 4 and not fl2["hitFar"], [fl1["w"], fl2["w"], fl2["f"]])
        _pb_shot(pg, "pb2c_6位Agent.png")
        sc2 = pg.evaluate(_PB_SCEN)
        ok("加到 6 位 Agent：景觀跟著往外（包圍盒變大）、仍不壓到新地板／新區塊、湖仍在、物件數 ≤ 上限", sc2["bbox"]["x0"] < sc0["bbox"]["x0"] - 2 and sc2["bbox"]["x1"] > sc0["bbox"]["x1"] + 2 and not sc2["hit"] and not sc2["lk"] and not sc2["inLake"] and sc2["lakes"] == 2 and sc2["n"] <= sc2["max"] and sc2["n"] > 30, [sc0["bbox"], sc2["bbox"], sc2])

        # ───── ③ 火焰、運動場、對話框照常 ─────
        r = pg.evaluate("""() => { const W = window.__world, e = [], F = W.fire; let burn = 0, sp = null, chat = false;
          try { const f = [...W.furn.values()].find(i => i.f.type === 'workstation'), n0 = F.furn.size; const ok = F.igniteFurn(f); burn = ok && F.furn.get(f.f.id).state === 'burning' ? 1 : 0; } catch (x) { e.push('fire:' + x.message); }
          try { chat = !!W.chat || !!document.getElementById('chat'); } catch (x) { e.push('chat:' + x.message); }
          return { err: e, burn, chat, wet: !!(W.sports && W.sports.water), pets: [...W.pets].filter(p => !p.away).length } }""")
        ok("區塊辦公室：存在的家具會著火（桌子燒得起來）、沒有因為缺家具而丟錯", not r["err"] and r["burn"] == 1, r)
        # 運動場整套不生成：沒有 W.sports、沒有「▼ 員工運動場」按鈕、區域選單沒有運動場項目；場景裡也沒有運動場物件
        sp = pg.evaluate("""() => { const W = window.__world; const btn = document.querySelector('.sp-go'); const names = []; W.scene.traverse(o => { if (o.name && /sport|pool|court|billiard/i.test(o.name)) names.push(o.name); });
          return { sports: !!W.sports, btn: !!btn && !btn.hidden && btn.offsetParent !== null, menu: /運動場/.test((document.getElementById('areaPop') || {}).innerHTML || ''), names, walk: W.layout.walkAreas.some(a => /運動場/.test(a.note || '')) } }""")
        ok("新專案不開放運動場：沒有 W.sports、按鈕隱藏、區域選單沒有、尋路範圍沒有、場景沒有運動場物件", not sp["sports"] and not sp["btn"] and not sp["menu"] and not sp["walk"] and not sp["names"], sp)
        # 被燒：只有辦公區內的飲水機當水源（CEO 區塊旁），人會跑過去潑水澆熄、不會往運動場／泳池跑
        wt = pg.evaluate("""() => { const W = window.__world, sp = W.spots.filter(q => q.name === 'water'); return { n: sp.length, inCeo: sp.every(q => { const r = W.layout.rooms.find(x => x.id === 'ceo'); return q.x >= r.x && q.x <= r.x + r.w && q.z >= r.z && q.z <= r.z + r.d; }) } }""")
        ok("區塊辦公室：有一台飲水機在 CEO 區塊內", wt["n"] == 1 and wt["inCeo"], wt)
        who = pg.evaluate("() => { const W = window.__world; const c = W.chars.get('planner'); c.busy = false; c._fireImmuneUntil = 0; c.standAt(14.0, 12.0, Math.PI); W.fire.noHelpers = true; W.fire.ignite(c, 'projblk'); return c.spec.id }")
        got = wait_until(pg, "() => { const c = window.__world.chars.get('planner'); return c._fireImmuneUntil > window.__world.time || c._wetUntil > window.__world.time }", 40000)
        ok("被燒的人跑去辦公區內的飲水機潑水澆熄（身上濕了、不再著火）", got, who)
        pg.wait_for_timeout(2500)
        ok("咖啡廳專案：全程頁面沒有 JS 錯誤", not errs, errs[:3])

        # ───── ④ tw-rotation 仍是完整辦公室 ─────
        got = _pb_enter(pg, base, _PB_TW)
        wait_until(pg, "() => ['inspector', 'my-bot'].every(k => window.__world.chars.has(k) && window.__world.chars.get(k).state === 'sit')", 60000)
        s3 = pg.evaluate(_PB_STATE)
        ids = [r["id"] for r in s3["rooms"]]
        ok("tw-rotation：仍是原本完整辦公室（沒有區塊模式、部門房間與會議室都在）", got and not s3["blocks"] and all(k in ids for k in ("meeting", "video", "audit", "lobby")) and len(s3["rooms"]) >= 19, ids)
        fl3 = pg.evaluate(_PB_FLOOR)
        ok("tw-rotation：外圍地板仍是固定 40×30（含邊距 43×33 的米色鋪面，邊緣外才是草地）", fl3["tw"] and fl3["w"] == 40 and fl3["d"] == 30 and fl3["slab"] and not fl3["grass"], fl3)
        ok("tw-rotation：示範編制的 inspector 照樣坐自己的座位 seat:inspector", any(v["id"] == "inspector" and v["at"] == "seat:inspector" for v in s3["vis"]), s3["vis"])
        ok("tw-rotation：戶外樹叢／灌木／花叢仍照常生成（W.outdoorDeco > 100）", pg.evaluate("() => window.__world.outdoorDeco") > 100, pg.evaluate("() => window.__world.outdoorDeco"))
        sc3 = pg.evaluate(_PB_SCEN)
        ok("tw-rotation：外圍景觀也有（灌木、花、樹、松樹、石頭）、有 2 個湖、物件數 ≤ 上限，且不壓到辦公室／運動場／遊民區／大門步道", (not sc3.get("none")) and sc3["lakes"] == 2 and all(sc3["kinds"].get(k, 0) > 0 for k in ("bush", "flower", "tree", "pine", "rock")) and sc3["n"] <= sc3["max"] and not sc3["hit"] and not sc3["lk"] and not sc3["inLake"], sc3)
        _pb_shot(pg, "pb3_tw-rotation完整辦公室.png")
    finally:
        c.close()
        srv.stop()


register("辦公室專案區塊", lambda pg, b, base, code: _pb_main(b, base))
