# 驗收段落「辦公室地板不准有黑洞」（2026-11-17 擁有者截圖：站長辦公室俯瞰白天，部門房間之間的走道整片純黑，「這類問題需要避免」）
#
# ★ 這是「通用防呆」：以後只要改辦公室場景（地板、區塊、景觀、燈光、材質、鏡頭、日夜、省電調暗），推 main 前都要跑這一段。
#   做法：不看程式碼對不對，直接看畫面 —— 把 UI 全藏掉、俯瞰截圖，取「建築外框（場景地面範圍投影到螢幕的四邊形）」裡的像素，
#   近黑（R、G、B 都 < 40）的比例必須 ≤ 1%。家具影子、螢幕、深色小物件加起來遠低於 1%，整片走道變黑就會立刻爆。
#   ① 站長辦公室（demo，完整 40×30 部門辦公室）：白天、夜晚各一次
#   ② 區塊模式（非 tw-rotation 的專案，真的收件端）：白天、夜晚各一次；同時檢查「大片空白米色」不存在（建築框內米色鋪面之外沒有露出草地以外的空洞）
#   ② 之二：黃昏、早晨（跟隨現在時間會走過的漸變時段）
#   ③ 額外壓力：站長辦公室白天、夜晚＋睡覺調暗＋關掉陰影（自動降畫質會做的事），仍不准黑
# 環境變數 FLOOR_SHOTS 指到資料夾時存截圖。需要 node 22（區塊模式用真的收件端）；沒有 node 只跳過區塊那兩項。
# flake8: noqa

import io as _io
import json as _json
import os as _os
import shutil as _sh
import socket as _sock
import subprocess as _sp
import tempfile as _tf
import time as _tm
import urllib.request as _ur
from urllib.parse import urlparse as _fup

_FH_TOK = "owner-token-" + "0123456789abcdef"
_FH_PH = "d1" * 8
try:
    _FH_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _FH_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_FH_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_FH_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_FH_NOPROXY = _ur.build_opener(_ur.ProxyHandler({}))
_FH_MAX = 0.01          # 近黑像素比例上限（1%）
_FH_BLACK = 40          # R、G、B 都低於這個值才算近黑


class _FhSrv:
    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _FH_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _FH_NOPROXY.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()

    def events(self, evs):
        req = _ur.Request(self.url + "/v1/events", method="POST", data=_json.dumps({"events": evs}).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.code})
        _FH_NOPROXY.open(req, timeout=5).read()

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _fh_ev(event, sid, name, **k):
    d = {"event": event, "session_id": sid, "project_hash": _FH_PH, "project_name": name, "ts": int(_tm.time() * 1000), "cloud": True}
    d.update(k)
    return d


# 場景地面範圍（區塊模式＝W.blocks.floor() 含邊距；完整辦公室＝0..Lw × 0..Ld）投影到螢幕的四邊形（CSS 像素）
_FH_QUAD = """() => { const W = window.__world, cam = W.camera; cam.updateMatrixWorld();
  let r; if (W.blocks) { const f = W.blocks.floor(); r = { x0: f.x0, x1: f.x1, z0: f.z0, z1: f.z1 }; } else r = { x0: 0, x1: W.layout.size.w, z0: 0, z1: W.layout.size.d };
  const cv = document.getElementById('cv'), bb = cv.getBoundingClientRect();
  const pts = [[r.x0, r.z0], [r.x1, r.z0], [r.x1, r.z1], [r.x0, r.z1]].map(([x, z]) => { const v = cam.position.clone().set(x, 0, z).project(cam); return [bb.left + (v.x + 1) / 2 * bb.width, bb.top + (1 - v.y) / 2 * bb.height]; });
  return { pts, blocks: !!W.blocks, rect: r, w: innerWidth, h: innerHeight }; }"""


def _fh_ratio(pg, name):
    """藏掉全部 UI（只留 3D 畫布）→ 截圖 → 建築外框四邊形內近黑像素的比例。回傳 (比例, 取樣像素數)。"""
    from PIL import Image, ImageDraw
    pg.add_style_tag(content="body * { visibility: hidden !important; } #cv { visibility: visible !important; }")
    pg.wait_for_timeout(400)
    q = pg.evaluate(_FH_QUAD)
    png = pg.screenshot()
    # 防呆的防呆：截圖若幾乎是單一顏色（畫布被藏掉或沒畫出來），不能當成「沒有黑洞」放行
    _im = __import__("PIL.Image", fromlist=["Image"]).open(_io.BytesIO(png)).convert("RGB").resize((64, 40))
    _px = list(_im.getdata())
    q["flat"] = len(set(_px)) < 40
    d = _os.environ.get("FLOOR_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        with open(_os.path.join(d, name), "wb") as f:
            f.write(png)
    im = Image.open(_io.BytesIO(png)).convert("RGB")
    W, H = im.size
    # 框縮進 6%：邊緣是牆的側面與牆影（本來就會暗），要驗的是裡面的走道與地板
    pts = q["pts"]
    cx = sum(p[0] for p in pts) / 4
    cy = sum(p[1] for p in pts) / 4
    poly = [(cx + (x - cx) * 0.94, cy + (y - cy) * 0.94) for x, y in pts]
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    px, mk = im.load(), mask.load()
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    n = bad = 0
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
        for x in range(max(0, int(min(xs))), min(W, int(max(xs)) + 1)):
            if mk[x, y]:
                n += 1
                r, g, b = px[x, y]
                if r < _FH_BLACK and g < _FH_BLACK and b < _FH_BLACK:
                    bad += 1
    return (1.0 if q["flat"] else (bad / n if n else 1.0)), n


def _fh_ctx(b, tm, live=False):
    c = b.new_context(viewport={"width": 1280, "height": 800})
    init = "try{localStorage.setItem('aiOffice.daytime','%s')" % tm
    if live:
        user = _json.dumps({"email": "a@example.com", "name": "站長", "admin": True})
        init += ";localStorage.setItem('tw.acct.tok','" + _FH_TOK + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ")"
    c.add_init_script(init + "}catch(e){}")
    return c


def _fh_demo(b, base, tm, stress=False):
    root = base.split("/index.html")[0].rstrip("/")
    c = _fh_ctx(b, tm)
    pg = c.new_page()
    pg.set_default_timeout(90000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        pg.goto(root + "/office/world.html?demo=1&q=low&pr=0.6", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready", 150000)
        pg.wait_for_timeout(2500)
        tag = ("站長辦公室%s（%s）" % ("＋睡覺調暗＋關陰影" if stress else "", {"day": "白天", "night": "夜晚", "dusk": "黃昏", "morning": "早晨"}[tm]))
        if stress:
            pg.evaluate("() => { const W = __world; W.power.dimTo(0.01, 0.01); W.dim = 0.01; W.daytime.applyDim(); W.renderer.shadowMap.enabled = false; W.sun.castShadow = false; }")
            pg.wait_for_timeout(2500)
        r, n = _fh_ratio(pg, "floor_demo_%s%s.png" % (tm, "_stress" if stress else ""))
        ok("%s：建築外框內近黑像素 ≤ 1%%（取樣 %d 點）" % (tag, n), n > 20000 and r <= _FH_MAX, "近黑 %.2f%%，取樣 %d" % (r * 100, n))
        ok("%s：沒有頁面錯誤" % tag, not errs, errs[:2])
        if tm == "day" and not stress:
            _fh_sim(pg, "站長辦公室", "() => { const m = __world.floorBase.material; m.map = null; m.color.set('#000000'); m.needsUpdate = true; }")
    finally:
        c.close()


def _fh_sim(pg, tag, kill_js):
    """故意把地板塗黑（模擬某些顯示卡上貼圖／著色器壞掉）：護欄必須在幾秒內自己換成純色材質、畫面恢復。"""
    pg.evaluate("() => { __world.floorGuard.on = false; }")   # 先關掉護欄，量「壞掉」的樣子（證明這個驗收抓得到黑洞）
    pg.evaluate(kill_js)
    pg.wait_for_timeout(1200)
    r0, n0 = _fh_ratio(pg, "floor_sim_black.png")
    pg.evaluate("() => { __world.floorGuard.on = true; }")
    ok("%s：模擬地板壞掉時畫面確實變黑（驗收本身有效，近黑 %.0f%%）" % (tag, r0 * 100), r0 > 0.05, r0)   # 完整辦公室的走道只佔建築約 11%，塗黑後近黑 ≥ 5% 就是限額（1%）的 5 倍以上
    got = wait_until(pg, "() => __world.floorGuard && __world.floorGuard.healed > 0", 20000)
    pg.wait_for_timeout(1200)
    r1, n1 = _fh_ratio(pg, "floor_sim_healed.png")
    ok("%s：地板護欄偵測到整片近黑並自動換成純色材質" % tag, got, pg.evaluate("() => __world.floorGuard && __world.floorGuard.last"))
    ok("%s：護欄修復後近黑像素 ≤ 1%%（近黑 %.2f%%）" % (tag, r1 * 100), r1 <= _FH_MAX, r1)


def _fh_blocks(b, base, tm):
    if not _sh.which("node") or not _FH_DEV:
        ok("區塊模式地板：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    root = base.split("/index.html")[0].rstrip("/")
    o = _fup(base)
    srv = _FhSrv("%s://%s" % (o.scheme, o.netloc))
    c = _fh_ctx(b, tm, live=True)
    c.add_init_script("try{localStorage.setItem('aiOffice.live.v1'," + _json.dumps(_json.dumps({"url": srv.url, "login": True})) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    pg = c.new_page()
    pg.set_default_timeout(90000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        srv.events([
            _fh_ev("SessionStart", "fh1", "coffee-shop"),
            _fh_ev("SubagentStart", "fh1", "coffee-shop", agent_id="fa-1", agent_type="planner", description="規劃咖啡廳動線與座位"),
            _fh_ev("SubagentStart", "fh1", "coffee-shop", agent_id="fa-2", agent_type="data-verifier", description="驗證菜單成本資料"),
        ])
        pg.goto(root + "/office/world.html?office=main&project=" + _FH_PH + "&live_poll=800&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready && window.__world.blocks && window.__world.blocks.count() >= 3", 120000)
        pg.wait_for_timeout(3500)   # 地板約 0.6 秒平順長到最終範圍
        tag = "區塊模式（%s）" % ("白天" if tm == "day" else "夜晚")
        q = pg.evaluate(_FH_QUAD)
        ok("%s：確實是區塊模式（W.blocks）" % tag, q["blocks"], q)
        r, n = _fh_ratio(pg, "floor_blocks_%s.png" % tm)
        ok("%s：鋪面外框內近黑像素 ≤ 1%%（取樣 %d 點）" % (tag, n), n > 20000 and r <= _FH_MAX, "近黑 %.2f%%，取樣 %d" % (r * 100, n))
        ok("%s：沒有頁面錯誤" % tag, not errs, errs[:2])
        if tm == "day":
            _fh_sim(pg, "區塊模式", "() => { const m = __world.blocks.floorMesh().material; m.vertexColors = false; m.color.set('#000000'); m.needsUpdate = true; }")
    finally:
        c.close()
        srv.stop()


def _fh_all(pg, b, base, code):
    _fh_demo(b, base, "day")
    _fh_demo(b, base, "night")
    _fh_demo(b, base, "day", stress=True)
    _fh_demo(b, base, "night", stress=True)
    _fh_demo(b, base, "dusk")        # 跟隨現在時間會經過黃昏與清晨，這兩段的光線漸變也不准把地板壓黑
    _fh_demo(b, base, "morning")
    _fh_blocks(b, base, "day")
    _fh_blocks(b, base, "night")


register("辦公室地板不准黑洞", _fh_all)
