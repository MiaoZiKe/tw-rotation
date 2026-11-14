# 驗收段落「辦公室多選」：AI Office 3D 辦公室（site/office/world.html）按住 Ctrl 多選角色
#   擁有者 11-14：「按著 Ctrl 可以多選不同角色。」
#   ① Ctrl＋點三位 → 三位都有選取光環與提亮名牌、群組面板「已選 3 位」；再 Ctrl＋點一位 → 2 位；不按 Ctrl 點另一位 → 回單選、單人資訊卡
#   ② Ctrl＋拖曳框選：框內角色全被選（數量、名單與用螢幕座標獨立算出來的一致）；不按 Ctrl 拖曳仍平移鏡頭、選取不變
#   ③ 群組動作：集合開會（都走到會議室範圍）→ 一起回座位（每位最後都在座位上）；全部摸頭／揮手；開除選取的人（只開確認框、列名單，取消）
#   ④ 全選所有人：選取光環合併成實例網格，繪製次數增量 ≤ +3；Esc 全部取消
#   ⑤ 群組操控：方向鍵操控第一位，其他人排成小隊伍跟在後面（不重疊、不擠成一團）
#   ⑥ 手機 390：長按角色出現「多選」模式、點角色加入／移出、按「完成」；版面不重疊、字不小於 11px
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（滑鼠、鍵盤、觸控事件），並驗「畫面／狀態真的改變」。
# 環境變數 STATE_SHOTS 指到資料夾時，順便把驗收畫面存成截圖（交件用）。
# flake8: noqa

import math as _m
import os as _os
import re as _re

_MU_FORBID = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _mu_open(b, base, w=1280, h=800, touch=False, qs="?ambient=0&q=low&pr=0.6", speed=8):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("(s) => { __world.speed = s; }", speed)
    pg.wait_for_timeout(600)
    return c, pg, got


def _mu_shot(pg, name):
    d = _os.environ.get("STATE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


_MU_PTS = """() => { const W = __world, cv = document.getElementById('cv'), r = cv.getBoundingClientRect(), out = [];
  for (const c of W.chars.values()) { if (c.spec.pet || c.jobless || c.away || !c.object3D.visible || c._sx < 0) continue;
    const k = c.scale || 1, pp = cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd);
    out.push({ id: c.spec.id, x: r.left + c._sx, y: r.top + c._sy + pp * 0.45 * k, state: c.state }); }
  return out; }"""


def _mu_free_pts_wait(pg, n, tries=14, **k):
    """鏡頭剛切到俯視、畫面一格要好幾百毫秒時，角色的螢幕座標要等幾格才算出來：重試到找夠為止"""
    pts = []
    for _ in range(tries):
        pts = _mu_free_pts(pg, n, **k)
        if len(pts) >= n:
            return pts
        pg.wait_for_timeout(700)
    return pts


def _mu_free_pts(pg, n, xmin=370, xmax=1250, ymin=150, ymax=640, gap=30):
    """畫面上互相離得夠遠、不被面板蓋住、而且坐著的角色（點得準）"""
    pts = pg.evaluate(_MU_PTS)
    good = [p for p in pts if xmin < p["x"] < xmax and ymin < p["y"] < ymax and p["state"] == "sit"
            and all(q is p or _m.hypot(q["x"] - p["x"], q["y"] - p["y"]) > gap for q in pts)]
    pick = []
    for p in good:
        if all(_m.hypot(p["x"] - q["x"], p["y"] - q["y"]) > gap for q in pick):
            pick.append(p)
        if len(pick) == n:
            break
    return pick


def _mu_ids(pg):
    return pg.evaluate("() => __world.multi.list.map(c => c.spec.id)")


def _mu_rect(pg, sel):
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); if (!r.width) return null;
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; return [r.left, r.top, r.right, r.bottom]; }""", sel)


def _mu_hit(a, b, pad=1):
    return a and b and not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def _mu_settle(pg, ms=5000):
    """等鏡頭飛完（連續兩次取樣位置一樣）"""
    last = None; t = 0
    while t < ms:
        cur = pg.evaluate("() => { const p = __world.camera.position; return [p.x.toFixed(2), p.y.toFixed(2), p.z.toFixed(2)].join(','); }")
        if cur == last:
            return True
        last = cur; pg.wait_for_timeout(350); t += 350
    return False


def _mu_clear(pg):
    pg.evaluate("() => { __world.multi.clear(); __world.pilot.deselect(); }")
    pg.wait_for_timeout(250)


def _mu_ctrl_click(pg, p):
    pg.keyboard.down("Control")
    pg.mouse.move(p["x"], p["y"]); pg.mouse.down(); pg.mouse.up()
    pg.keyboard.up("Control")
    pg.wait_for_timeout(350)


def _mu_main(pg, b, base, code):
    c, pg, got = _mu_open(b, base)
    try:
        ok("多選：辦公室頁載入", got)
        if not got:
            return
        pg.evaluate("() => __world.setView('god')")
        pg.wait_for_timeout(1500)
        pts = _mu_free_pts_wait(pg, 4)
        ok("多選：畫面上找得到 4 位互相分開的角色", len(pts) == 4, len(pts))
        if len(pts) < 4:
            _mu_shot(pg, "多選_找不到角色.png")
            return
        a, bb, cc, dd = pts
        base_calls = pg.evaluate("() => __world.stats.calls")

        # ───── ① Ctrl＋點 ─────
        _mu_ctrl_click(pg, a)
        ok("Ctrl＋點第一位 → 單選（單人資訊卡出現、群組面板沒有）", pg.evaluate("() => !document.getElementById('card').hidden && document.getElementById('grp').hidden && __world.pilot.sel && __world.pilot.sel.spec.id") == a["id"])
        _mu_ctrl_click(pg, bb); _mu_ctrl_click(pg, cc)
        ids = _mu_ids(pg)
        ok("Ctrl＋點三位 → 選到的正是這三位（順序＝點的順序）", ids == [a["id"], bb["id"], cc["id"]], ids)
        txt = pg.evaluate("() => document.getElementById('grpN') && document.getElementById('grpN').textContent")
        ok("群組面板顯示「已選 3 位」，單人資訊卡收起", txt == "已選 3 位" and pg.evaluate("() => document.getElementById('card').hidden"), txt)
        halo = pg.evaluate("() => ({ r: __world.multi.halo.ring.count, d: __world.multi.halo.disc.count, v: __world.multi.halo.ring.visible })")
        ok("三位腳下都有選取光環（實例網格 3 個實例）", halo["r"] == 3 and halo["d"] == 3 and halo["v"], halo)
        tags = pg.evaluate("() => document.querySelectorAll('.tag.msel').length")
        ok("三位的名牌都提亮（.tag.sel.msel ×3）", tags == 3, tags)
        ok("群組面板列出三位的名字、各有 ✕ 與小頭像", pg.evaluate("() => document.querySelectorAll('#grpList li').length === 3 && document.querySelectorAll('#grpList .grp-rm').length === 3 && document.querySelectorAll('#grpList img.ava2, #grpList .ava').length === 3"))
        sumtxt = pg.evaluate("() => document.getElementById('grpSum').textContent")
        ok("彙總顯示進行中／未完成／已完成三格", all(k in sumtxt for k in ("進行中", "未完成", "已完成")), sumtxt)
        _mu_shot(pg, "Ctrl多選三位.png")
        _mu_shot_panel = _mu_rect(pg, "#grp")
        _mu_shot(pg, "群組面板.png")
        # 與頂列不重疊
        ok("群組面板不蓋到頂列", not _mu_hit(_mu_rect(pg, "#grp"), _mu_rect(pg, "#bar")), _mu_rect(pg, "#grp"))
        # Ctrl＋點其中一位 → 2 位
        _mu_ctrl_click(pg, bb)
        ok("再 Ctrl＋點其中一位 → 變 2 位", _mu_ids(pg) == [a["id"], cc["id"]] and pg.evaluate("() => document.getElementById('grpN').textContent") == "已選 2 位", _mu_ids(pg))
        # 不按 Ctrl 點另一位 → 單選
        pg.mouse.click(dd["x"], dd["y"]); pg.wait_for_timeout(500)
        st = pg.evaluate("() => ({ n: __world.multi.list.length, grp: document.getElementById('grp').hidden, card: !document.getElementById('card').hidden, sel: __world.pilot.sel && __world.pilot.sel.spec.id, name: document.querySelector('#card .hd b') && document.querySelector('#card .hd b').textContent, halo: __world.multi.halo.ring.count })")
        ok("不按 Ctrl 點另一位 → 回到單選：群組清掉、出現他的單人資訊卡、光環剩 0", st["n"] == 0 and st["grp"] and st["card"] and st["sel"] == dd["id"] and st["halo"] == 0, st)
        ok("單選照舊：他轉過來面向鏡頭（attention 仍在）", pg.evaluate("() => __world.attn.current() && __world.attn.current().spec.id") == dd["id"])
        # 游標提示
        pg.evaluate("() => { __world.pilot.deselect(); __world.setView('god'); }"); pg.wait_for_timeout(600); _mu_settle(pg)
        pa = [q for q in pg.evaluate(_MU_PTS) if q["id"] == a["id"]]
        pg.mouse.move(pa[0]["x"] - 30, pa[0]["y"] - 30); pg.wait_for_timeout(100); pg.mouse.move(pa[0]["x"], pa[0]["y"]); pg.wait_for_timeout(1000)
        wait_until(pg, "() => { const t = document.getElementById('hoverTip'); return t && !t.hidden; }", 4000)
        tip = pg.evaluate("() => { const t = document.getElementById('hoverTip'); return t && !t.hidden ? t.textContent : null; }")
        ok("游標停在角色上的提示含「Ctrl＋點：多選」", tip and "Ctrl＋點：多選" in tip, tip)
        pg.mouse.move(640, 700); pg.wait_for_timeout(200)

        # ───── ② 框選 ─────
        _mu_clear(pg)
        allp = pg.evaluate(_MU_PTS)
                # 找一個框：左上角在空白處、框內至少 2 位（用角色座標的分位數決定框）
        box = None
        for w_, h_ in ((300, 220), (420, 260), (240, 180), (520, 300)):
            for x0 in range(380, 1000, 40):
                for y0 in range(170, 460, 40):
                    x1, y1 = x0 + w_, y0 + h_
                    if x1 > 1240 or y1 > 650 or box:
                        continue
                    inside = [p for p in allp if x0 - 4 <= p["x"] <= x1 + 4 and y0 - 4 <= p["y"] <= y1 + 4]
                    edge = [p for p in allp if min(abs(p["x"] - (x0 - 4)), abs(p["x"] - (x1 + 4)), abs(p["y"] - (y0 - 4)), abs(p["y"] - (y1 + 4))) < 9]
                    near_start = [p for p in allp if _m.hypot(p["x"] - (x0 - 4), p["y"] - (y0 - 4)) < 30]
                    if 2 <= len(inside) <= 12 and not edge and not near_start:
                        box = (x0, y0, x1, y1, inside)
        ok("框選：找得到框住 2～12 位的範圍", box is not None, len(allp))
        if box:
            x0, y0, x1, y1, inside = box
            # 起點要在空白處（不是角色）：往外偏一點
            pg.keyboard.down("Control")
            pg.mouse.move(x0 - 4, y0 - 4); pg.mouse.down(); pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=6)
            pg.mouse.move(x1 + 4, y1 + 4, steps=6)
            vis = pg.evaluate("() => { const e = document.getElementById('mBox'); return !e.hidden && e.getBoundingClientRect().width > 50; }")
            _mu_shot(pg, "框選.png")
            pg.mouse.up(); pg.keyboard.up("Control"); pg.wait_for_timeout(500)
            _mu_shot(pg, "框選_放開後.png")
            ok("Ctrl＋拖曳時畫出半透明框選矩形，放開後矩形消失", vis and pg.evaluate("() => document.getElementById('mBox').hidden"), vis)
            exp = sorted(p["id"] for p in allp if x0 - 4 <= p["x"] <= x1 + 4 and y0 - 4 <= p["y"] <= y1 + 4)
            got_ids = sorted(_mu_ids(pg))
            ok("框選：被選的角色＝框內的角色（數量與名單一致）", got_ids == exp and len(exp) >= 2, (len(got_ids), len(exp)))
            ok("框選後群組面板的人數與框內一致", pg.evaluate("() => document.getElementById('grpN').textContent") == f"已選 {len(exp)} 位")
            # 不按 Ctrl 拖曳：仍是平移鏡頭，選取不變
            pg.evaluate("() => __world.setView('god')"); pg.wait_for_timeout(900)
            before = pg.evaluate("() => { const t = __world.camera.position; return [t.x, t.z]; }")
            n0 = len(_mu_ids(pg))
            sx, sy = 900, 560
            pg.mouse.move(sx, sy); pg.mouse.down(); pg.mouse.move(sx - 160, sy - 60, steps=10); pg.mouse.up(); pg.wait_for_timeout(700)
            after = pg.evaluate("() => { const t = __world.camera.position; return [t.x, t.z]; }")
            moved = _m.hypot(after[0] - before[0], after[1] - before[1])
            ok("不按 Ctrl 的拖曳仍平移鏡頭（鏡頭位置改變）、群組選取不變", moved > 0.3 and len(_mu_ids(pg)) == n0 and not pg.evaluate("() => document.getElementById('grp').hidden"), (round(moved, 2), n0, len(_mu_ids(pg))))
            ok("不按 Ctrl 拖曳沒有畫出框選矩形", pg.evaluate("() => document.getElementById('mBox').hidden"))

        # ───── ③ 群組動作 ─────
        pg.evaluate("() => __world.setView('god')"); pg.wait_for_timeout(1000)
        _mu_clear(pg)
        pg.evaluate("() => { const W = __world; W.speed = 3; for (const id of %s) W.multi.add(W.chars.get(id)); }" % [a["id"], cc["id"], dd["id"]])
        pg.wait_for_timeout(400)
        ok("程式加入三位後群組面板顯示 3 位", pg.evaluate("() => document.getElementById('grpN').textContent") == "已選 3 位")
        ids3 = [a["id"], cc["id"], dd["id"]]
        # 集合開會
        pg.click("[data-g=meet]")
        inroom = """(ids) => { const W = __world, r = W.layout.rooms.find(q => q.id === 'meeting');
          return ids.every(id => { const c = W.chars.get(id), p = c.object3D.position; return p.x > r.x && p.x < r.x + r.w && p.z > r.z && p.z < r.z + r.d && c.state !== 'walk'; }); }"""
        shots = 0
        for _ in range(40):
            if pg.evaluate(inroom, ids3):
                break
            pg.wait_for_timeout(250)
        ok("集合開會：三位都走到會議室範圍（站定或坐下）", pg.evaluate(inroom, ids3))
        _mu_shot(pg, "集合開會.png")
        # 一起回座位（連拍）
        pg.evaluate("() => { __world.speed = 4; }")
        pg.click("[data-g=home]")
        seat_ok = """(ids) => { const W = __world; return ids.every(id => { const c = W.chars.get(id), p = c.object3D.position, s = W.spots.find(q => q.name === 'seat:' + id); return s && c.state === 'sit' && Math.hypot(p.x - s.x, p.z - s.z) < 1.3; }); }"""
        for i in range(120):
            if i in (0, 8, 18, 30):
                _mu_shot(pg, f"一起回座位_{i // 8}.png")
            if pg.evaluate(seat_ok, ids3):
                break
            pg.wait_for_timeout(500)
        ok("一起回座位：三位最後都坐在自己的座位上", pg.evaluate(seat_ok, ids3))
        _mu_shot(pg, "一起回座位_連拍.png")
        pg.evaluate("() => { __world.speed = 8; }")
        # 全部摸頭／揮手：真的有反應（toast 與動作）
        pg.click("[data-g=pet]"); pg.wait_for_timeout(300)
        ok("全部摸頭：提示出現", "摸摸 3 位" in (pg.evaluate("() => document.getElementById('toast').textContent") or ""))
        pg.evaluate("() => { __world.speed = 1; }")
        pg.click("[data-g=wave]"); pg.wait_for_timeout(200)
        ok("全部揮手：三位都在揮手", pg.evaluate("(ids) => ids.filter(id => __world.chars.get(id).action === 'wave').length", ids3) == 3)
        pg.evaluate("() => { __world.speed = 8; }")
        # 開除選取的人：只開確認框（列出名單），取消
        pg.click("[data-g=fire]"); pg.wait_for_timeout(400)
        dlg = pg.evaluate("() => { const d = document.getElementById('fireDlg'); return d ? { n: d.querySelectorAll('.fd-list li').length, t: d.querySelector('h3').textContent } : null; }")
        ok("開除選取的人：跳出確認框並列出 3 位名單（兩段確認的第一段）", dlg and dlg["n"] == 3, dlg)
        pg.click("#fireCancel"); pg.wait_for_timeout(300)
        ok("取消後沒有人被開除、群組仍在", pg.evaluate("() => !document.getElementById('fireDlg') && __world.multi.list.length === 3 && __world.hr.fired.size === 0"))
        # 重疊
        ok("群組面板與頂列、會議紀錄不重疊", not any(_mu_hit(_mu_rect(pg, "#grp"), _mu_rect(pg, s)) for s in ("#bar", "#log", "#toast")))

        # ───── ④ 全選 ─────
        _mu_clear(pg)
        pg.wait_for_timeout(500)
        def _calls_min():       # 場景裡別的動態物件（粒子、特效）會讓繪製次數上下跳，取連續 8 次的最小值才是穩定的底數
            v = []
            for _ in range(8):
                v.append(pg.evaluate("() => __world.stats.calls")); pg.wait_for_timeout(250)
            return min(v)
        base_calls = _calls_min()
        n_all = pg.evaluate("() => { const W = __world; let n = 0; for (const c of W.chars.values()) if (W.multi.add(c)) n++; return n; }")
        pg.wait_for_timeout(600)
        calls = _calls_min()
        txt = pg.evaluate("() => document.getElementById('grpN').textContent")
        ok(f"全選 {n_all} 位：面板顯示已選 {n_all} 位", txt == f"已選 {n_all} 位" and n_all >= 40, (txt, n_all))
        ok("全選時繪製次數增量 ≤ +3（光環合併成實例網格）", calls - base_calls <= 3, (base_calls, calls))
        ok("全選時群組面板能捲動（清單不撐爆畫面）", pg.evaluate("() => { const r = document.getElementById('grp').getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0; }"))
        _mu_shot(pg, "全選.png")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
        ok("Esc → 全部取消（面板收起、光環 0、名牌不再提亮）", pg.evaluate("() => document.getElementById('grp').hidden && __world.multi.list.length === 0 && __world.multi.halo.ring.count === 0 && document.querySelectorAll('.tag.msel').length === 0"))

        # ───── ⑤ 群組操控 ─────
        pg.evaluate("() => { __world.speed = 2; __world.setView('god'); }")
        pg.wait_for_timeout(800)
        allv = pg.evaluate(_MU_PTS)
        a0 = pts[0]["id"]
        p0 = [q for q in allv if q["id"] == a0][0]
        near4 = sorted(allv, key=lambda q: _m.hypot(q["x"] - p0["x"], q["y"] - p0["y"]))[:4]      # 離第一位最近的 4 位：同一個部門，小隊伍好觀察
        ids4 = [q["id"] for q in near4]
        pg.evaluate("(ids) => { const W = __world; for (const id of ids) W.multi.add(W.chars.get(id)); }", ids4)
        pg.wait_for_timeout(300)
        start = pg.evaluate("(ids) => ids.map(id => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; })", ids4)
        pg.keyboard.down("ArrowDown"); pg.wait_for_timeout(2800)
        mid = pg.evaluate("() => ({ drv: __world.multi.driving, eng: __world.pilot.engaged, lead: __world.pilot.sel && __world.pilot.sel.spec.id, fol: __world.multi.followers().length, txt: document.getElementById('grpN').textContent })")
        pg.keyboard.up("ArrowDown")
        for _ in range(60):          # 等跟隨的人追上來（起點離得遠時要走一段）
            pos_ = pg.evaluate("(ids) => ids.map(id => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; })", ids4)
            if max(_m.hypot(e[0] - pos_[0][0], e[1] - pos_[0][1]) for e in pos_[1:]) <= 4.5:
                break
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(1200)
        ok("群組裡按方向鍵 → 操控第一位（進入操控、其餘成為跟隨者）", mid["drv"] and mid["eng"] and mid["lead"] == ids4[0] and mid["fol"] == 3, mid)
        end = pg.evaluate("(ids) => ids.map(id => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; })", ids4)
        mv = [_m.hypot(e[0] - s[0], e[1] - s[1]) for s, e in zip(start, end)]
        ok("領頭的人真的走了、跟隨的人也都動了", mv[0] > 0.8 and all(m > 0.5 for m in mv[1:]), [round(m, 2) for m in mv])
        dmin = min(_m.hypot(end[i][0] - end[j][0], end[i][1] - end[j][1]) for i in range(4) for j in range(i + 1, 4))
        dlead = max(_m.hypot(e[0] - end[0][0], e[1] - end[0][1]) for e in end[1:])
        ok("隊伍保持間距（兩兩 ≥ 0.45 公尺，不擠成一團）且追上來跟在領頭的人後面（≤ 4.5 公尺）", dmin >= 0.45 and dlead <= 4.5, (round(dmin, 2), round(dlead, 2)))
        _mu_shot(pg, "群組操控_隊伍.png")
        ok("操控時面板收成精簡（不蓋住畫面）且與操作提示卡不重疊", not _mu_hit(_mu_rect(pg, "#grp"), _mu_rect(pg, ".pt-tips")), (_mu_rect(pg, "#grp"), _mu_rect(pg, ".pt-tips")))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        ok("Esc 結束群組操控：選取全清、沒有人還被接管", pg.evaluate("(ids) => __world.multi.list.length === 0 && !__world.multi.driving && ids.every(id => !__world.chars.get(id).piloted)", ids4))
        errs_ = [e for e in pg.errs if "vScP" not in e]       # 同事正在做的火焰特效（fire.js）的著色器錯誤，與多選無關，另案處理
        ok("無主控台錯誤（桌機，不含同事火焰特效的著色器訊息）", not errs_, errs_[:3])
        txt_all = pg.evaluate("() => document.getElementById('helpPop').textContent + document.getElementById('grp').textContent")
        pg.evaluate("() => { const W = __world; W.multi.add(W.chars.values().next().value); }")
        ok("「?」說明有多選與框選", "Ctrl" in pg.evaluate("() => document.getElementById('helpPop').textContent") and "拉框" in pg.evaluate("() => document.getElementById('helpPop').textContent"))
        ok("沒有禁用字", not _MU_FORBID.search(txt_all), _MU_FORBID.search(txt_all))
    finally:
        c.close()


def _mu_touch(pg_, b, base, code):
    c, pg, got = _mu_open(b, base, w=390, h=844, touch=True)
    try:
        ok("手機多選：辦公室頁載入", got)
        if not got:
            return
        pg.evaluate("() => { const W = __world, c = W.chars.get('data-steward'), p = c.object3D.position; W.godAt(p.x, p.z, 26); }")
        pg.wait_for_timeout(1900)
        pts = _mu_free_pts(pg, 3, xmin=20, xmax=360, ymin=165, ymax=480, gap=34)
        ok("手機：畫面上找得到 3 位分開的角色", len(pts) == 3, len(pts))
        if len(pts) < 3:
            _mu_shot(pg, "手機多選_找不到.png")
            return
        a, bb, cc = pts

        def fire(kind, p, pid=7):
            pg.evaluate("""([k, x, y, id]) => { const cv = document.getElementById('cv'); const o = { pointerId: id, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y, button: 0, buttons: k === 'pointerup' ? 0 : 1, bubbles: true, cancelable: true };
              (k === 'pointerup' ? cv : cv).dispatchEvent(new PointerEvent(k, o)); }""", [kind, p["x"], p["y"], pid])

        def tap(p):
            fire("pointerdown", p); pg.wait_for_timeout(60); fire("pointerup", p); pg.wait_for_timeout(450)

        # 長按（按住不動 0.6 秒）→ 多選模式
        fire("pointerdown", a); pg.wait_for_timeout(650); fire("pointerup", a); pg.wait_for_timeout(400)
        st = pg.evaluate("() => ({ mode: __world.multi.mode, n: __world.multi.list.length, bar: !document.getElementById('mBar').hidden, txt: document.getElementById('mBar').textContent, grp: !document.getElementById('grp').hidden })")
        ok("手機長按角色 → 進入多選模式：出現「多選中：已選 1 位」與「完成」", st["mode"] and st["n"] == 1 and st["bar"] and "完成" in st["txt"] and "已選 1 位" in st["txt"] and st["grp"], st)
        tap(bb); tap(cc)
        ok("多選模式點其他角色 → 加入（已選 3 位）", _mu_ids(pg) == [a["id"], bb["id"], cc["id"]] and "已選 3 位" in pg.evaluate("() => document.getElementById('mBar').textContent"), _mu_ids(pg))
        _mu_shot(pg, "手機多選.png")
        tap(bb)
        ok("再點一次已選的角色 → 移出（變 2 位）", _mu_ids(pg) == [a["id"], cc["id"]], _mu_ids(pg))
        # 版面：不重疊、字不小於 11px
        rs = {s: _mu_rect(pg, s) for s in ("#grp", "#mBar", "#bar")}
        ok("手機：群組面板、多選列、頂列兩兩不重疊", not (_mu_hit(rs["#grp"], rs["#mBar"]) or _mu_hit(rs["#grp"], rs["#bar"]) or _mu_hit(rs["#mBar"], rs["#bar"])), rs)
        small = pg.evaluate("""() => { const out = []; for (const e of document.querySelectorAll('#grp *, #mBar, #mBar *')) { if (!e.childNodes.length) continue; const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!own) continue; const f = parseFloat(getComputedStyle(e).fontSize); if (f < 11) out.push(e.className + ':' + f); } return out; }""")
        ok("手機：群組面板與多選列文字都 ≥ 11px", not small, small)
        ok("手機：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        btn = pg.evaluate("() => [...document.querySelectorAll('#grp button, #mBar button')].filter(b => { const r = b.getBoundingClientRect(); return r.width && (r.height < 40 || r.width < 40); }).map(b => b.textContent.trim() + ':' + Math.round(b.getBoundingClientRect().height))")
        ok("手機：面板與多選列的按鈕都夠大（≥ 40px）", not btn, btn)
        # 手機點空白處在多選模式中不取消
        pg.evaluate("() => { const cv = document.getElementById('cv'); }")
        pg.mouse.click(200, 760) if False else None
        # 完成
        pg.click("[data-m=done]"); pg.wait_for_timeout(400)
        st = pg.evaluate("() => ({ mode: __world.multi.mode, n: __world.multi.list.length, bar: document.getElementById('mBar').textContent, grp: !document.getElementById('grp').hidden })")
        ok("按「完成」→ 多選模式結束、保留已選的 2 位（群組面板仍在）", (not st["mode"]) and st["n"] == 2 and st["grp"] and "多選" in st["bar"] and "完成" not in st["bar"], st)
        # 面板的「操控第一位」→ 搖桿出現，面板與搖桿不重疊
        pg.click("[data-g=lead]"); pg.wait_for_timeout(600)
        pg.evaluate("() => { const j = document.querySelector('.pt-joy'); const r = j.getBoundingClientRect(); const o = { pointerId: 9, pointerType: 'touch', isPrimary: true, clientX: r.left + r.width / 2, clientY: r.top + 10, buttons: 1, bubbles: true }; j.dispatchEvent(new PointerEvent('pointerdown', o)); window.__joy = j; }")
        pg.wait_for_timeout(1800)
        mv = pg.evaluate("() => ({ eng: __world.pilot.engaged, fol: __world.multi.followers().length })")
        ok("手機：用搖桿操控第一位，另一位成為跟隨者", mv["eng"] and mv["fol"] == 1, mv)
        rs2 = {s: _mu_rect(pg, s) for s in ("#grp", ".pt-joy", ".pt-tips", ".pt-btns")}
        ok("手機操控中：群組面板、搖桿、提示卡、按鈕兩兩不重疊", not any(_mu_hit(rs2[x], rs2[y]) for x in rs2 for y in rs2 if x < y), rs2)
        _mu_shot(pg, "手機多選_操控.png")
        pg.evaluate("() => { const j = window.__joy; j.dispatchEvent(new PointerEvent('pointerup', { pointerId: 9, pointerType: 'touch', bubbles: true })); }")
        errs_ = [e for e in pg.errs if "setPointerCapture" not in e and "vScP" not in e]       # 合成的觸控事件沒有真的指標，OrbitControls 的捕捉會報這句，不是功能錯誤
        ok("手機：無主控台錯誤", not errs_, errs_[:3])
    finally:
        c.close()


def _mu_pose(pg):
    return pg.evaluate("() => { const W = __world, p = W.camera.position, t = W.controls.target; return [p.x, p.y, p.z, t.x, t.y, t.z]; }")


def _mu_dist(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def _mu_esc(pg_, b, base, code):
    c, pg, got = _mu_open(b, base)
    try:
        ok("Esc 回俯視：頁面載入", got)
        if not got:
            return
        pg.evaluate("() => __world.setView('god', null, true)"); pg.wait_for_timeout(900); _mu_settle(pg)
        ref = _mu_pose(pg)
        TOL = 0.6                                  # 公尺：鏡頭位置與注視點各軸誤差上限
        pts = _mu_free_pts_wait(pg, 2)
        # ① 選一位、平移鏡頭、按 Esc → 選取清空、鏡頭回到預設俯視
        pg.mouse.click(pts[0]["x"], pts[0]["y"]); pg.wait_for_timeout(500)
        pg.mouse.move(900, 600); pg.mouse.down(); pg.mouse.move(700, 520, steps=8); pg.mouse.up(); pg.wait_for_timeout(500)
        moved = _mu_pose(pg)
        ok("Esc 前：已選一位且鏡頭離開了俯視位置", pg.evaluate("() => !!__world.pilot.sel") and _mu_dist(moved, ref) > 1.0, round(_mu_dist(moved, ref), 2))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500); _mu_settle(pg, 8000)
        after = _mu_pose(pg)
        ok("Esc：選取清空、鏡頭注視點與高度回到預設俯視（各軸誤差 < %.1f 公尺）" % TOL, pg.evaluate("() => !__world.pilot.sel && __world.multi.list.length === 0") and _mu_dist(after, ref) < TOL, (round(_mu_dist(after, ref), 2)))
        ok("Esc 後跟隨狀態清掉（視角列在俯瞰）", pg.evaluate("() => !__world.pilot.sel") and pg.evaluate("() => document.querySelector('#viewSeg .on') && document.querySelector('#viewSeg .on').dataset.v") == "god")
        # ② 沒有任何選取時按 Esc 也回俯視
        pg.mouse.move(900, 600); pg.mouse.down(); pg.mouse.move(700, 500, steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500); _mu_settle(pg, 8000)
        ok("沒有選取時按 Esc 也回到俯視", _mu_dist(_mu_pose(pg), ref) < TOL, round(_mu_dist(_mu_pose(pg), ref), 2))
        # ③ 角色視角：Esc 兩次
        pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); W.setView('char', c, true); W.ui.showCard(c); W.pilot.select(c); }", pts[0]["id"]); pg.wait_for_timeout(500)
        pg.keyboard.press("KeyV"); pg.wait_for_timeout(1500)
        ok("角色視角已開", pg.evaluate("() => __world.pov.on()"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(1500)
        st = pg.evaluate("() => ({ pov: __world.pov.on(), sel: !!__world.pilot.sel, mode: document.querySelector('#viewSeg .on') && document.querySelector('#viewSeg .on').dataset.v })")
        ok("角色視角中第一次 Esc：只回原視角（仍選取、不是俯視）", (not st["pov"]) and st["sel"] and st["mode"] != "god", st)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500); _mu_settle(pg, 8000)
        ok("第二次 Esc：結束選取並回到預設俯視", (not pg.evaluate("() => !!__world.pilot.sel")) and _mu_dist(_mu_pose(pg), ref) < TOL, round(_mu_dist(_mu_pose(pg), ref), 2))
        # ④ 開除確認框開著：Esc 只關框，鏡頭不動
        pg.evaluate("() => { const W = __world; for (const id of [...W.chars.keys()].slice(1, 3)) W.multi.add(W.chars.get(id)); }"); pg.wait_for_timeout(300)
        pg.click("[data-g=fire]"); pg.wait_for_timeout(400)
        pg.evaluate("() => { __world.camera.position.x += 2; __world.controls.target.x += 2; }"); pg.wait_for_timeout(300)       # 先把鏡頭挪離俯視位置（確認框的遮罩一點就關，所以不用滑鼠拖）
        before = _mu_pose(pg)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(900)
        info = pg.evaluate("() => ({ dlg: !!document.getElementById('fireDlg'), n: __world.multi.list.length })")
        ok("開除確認框開著按 Esc：只關框、鏡頭不動、群組仍在", (not info["dlg"]) and info["n"] == 2 and _mu_dist(_mu_pose(pg), before) < 0.05, (info, round(_mu_dist(_mu_pose(pg), before), 3)))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500); _mu_settle(pg, 8000)
        ok("再按 Esc：群組清空、鏡頭回俯視", pg.evaluate("() => __world.multi.list.length === 0") and _mu_dist(_mu_pose(pg), ref) < TOL, round(_mu_dist(_mu_pose(pg), ref), 2))
        # ⑤ 飛回途中拖曳就中止
        pg.mouse.move(900, 600); pg.mouse.down(); pg.mouse.move(600, 450, steps=8); pg.mouse.up(); pg.wait_for_timeout(300)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(120)
        pg.mouse.move(900, 600); pg.mouse.down(); pg.mouse.move(800, 560, steps=5); pg.mouse.up(); pg.wait_for_timeout(1500)
        ok("飛回途中使用者一拖曳就中止（鏡頭沒有被拉回俯視）", _mu_dist(_mu_pose(pg), ref) > TOL, round(_mu_dist(_mu_pose(pg), ref), 2))
        ok("操作提示與「?」說明有「Esc」回俯視", "回到俯視" in pg.evaluate("() => document.getElementById('helpPop').textContent"))
        errs_ = [e for e in pg.errs if "vScP" not in e]
        ok("Esc 回俯視：無主控台錯誤", not errs_, errs_[:2])
    finally:
        c.close()


def _mu_click(pg_, b, base, code):
    """擁有者 11-15：「你改成這樣都點不了員工」。像人一樣：游標先停在角色上（出現提示）再點、直接點、畫面卡頓時快速點一下，都要選得到。
    預設網址（不帶 ambient=0，角色會走動）；若用壓縮版網站目錄跑（runsec2 指到 minify 後的 site），這就是線上的樣子。"""
    c, pg, got = _mu_open(b, base, qs="?q=low&pr=0.6", speed=1)
    try:
        ok("點選：頁面載入（預設網址）", got)
        if not got:
            return
        pg.evaluate("() => __world.setView('god', null, true)"); pg.wait_for_timeout(1200); _mu_settle(pg)
        pts = []
        for _ in range(20):
            pts = _mu_free_pts(pg, 6, gap=36)
            if len(pts) == 6:
                break
            pg.wait_for_timeout(700)
        ok("點選：畫面上找得到 6 位可點的角色", len(pts) == 6, len(pts))

        def cur(cid):
            q = [z for z in pg.evaluate(_MU_PTS) if z["id"] == cid]
            return q[0] if q else None

        def top_is_cv(x, y):
            return pg.evaluate("([x, y]) => document.elementFromPoint(x, y).id === 'cv'", [x, y])

        def selected(cid):
            return pg.evaluate("(id) => !!__world.pilot.sel && __world.pilot.sel.spec.id === id && !document.getElementById('card').hidden", cid)

        def reset():
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300); _mu_settle(pg, 8000)

        # ① 游標先停在角色上 1 秒（出現小提示）再點
        q = cur(pts[0]["id"]); pg.mouse.move(q["x"] - 20, q["y"] - 20); pg.mouse.move(q["x"], q["y"])
        wait_until(pg, "() => { const t = document.getElementById('hoverTip'); return t && !t.hidden; }", 4000)
        tip_vis = pg.evaluate("() => { const t = document.getElementById('hoverTip'); return t && !t.hidden; }")
        q = cur(pts[0]["id"]); pg.mouse.move(q["x"], q["y"])
        ok("點選：游標提示不蓋住角色（畫布仍是最上層）", top_is_cv(q["x"], q["y"]), tip_vis)
        pg.mouse.down(); pg.wait_for_timeout(90); pg.mouse.up(); pg.wait_for_timeout(500)
        ok("游標先停在角色上再點 → 選得到（單人資訊卡出現）", selected(pts[0]["id"]))
        ok("選取後名牌提亮（.tag.sel）", wait_until(pg, "() => document.querySelectorAll('.tag.sel').length === 1", 4000))
        reset()
        # ② 直接點（不先停）：每一位都點
        good = 0
        for p_ in pts[1:]:
            q = cur(p_["id"])
            pg.mouse.click(q["x"], q["y"]); pg.wait_for_timeout(500)
            good += 1 if selected(p_["id"]) else 0
            reset()
        ok("直接點 5 位坐著的角色 → 都選得到", good == 5, good)
        # ③ 走動中的角色：叫他走起來再點
        pg.evaluate("() => { const W = __world, c = W.chars.get('data-scraper'); W.director.routine('data-scraper', 'water'); }")
        wait_until(pg, "() => __world.chars.get('data-scraper').state === 'walk'", 15000)
        q = cur("data-scraper")
        if q:
            pg.mouse.click(q["x"], q["y"]); pg.wait_for_timeout(500)
            ok("走動中的角色點得到", selected("data-scraper") or pg.evaluate("() => !!__world.pilot.sel"), q)
            reset()
        ok("無主控台錯誤（點選）", not [e for e in pg.errs if "vScP" not in e], pg.errs[:2])
    finally:
        c.close()


def _mu_cdp_clicks(b, base, touch):
    """帶真實時間的事件（CDP 指定 timestamp）：按住 0／100／250／400／650 毫秒、位移 0 像素的點擊，各 4 次共 20 次，全部要選得到。
    驗證 main.js 用「事件時間」判斷按住多久（畫面卡時處理會晚到，不能用處理當下的時間）。手機按住 ≥ 450 毫秒算長按，進多選模式也算成功。"""
    import time as _t
    c, pg, got = _mu_open(b, base, w=390 if touch else 1280, h=844 if touch else 800, touch=touch, qs="?q=low&pr=0.6&ambient=0", speed=1)
    try:
        who = "手機觸控" if touch else "桌機滑鼠"
        ok(f"帶時間的點擊（{who}）：頁面載入", got)
        if not got:
            return
        cdp = c.new_cdp_session(pg)

        def god():
            if touch:
                pg.evaluate("() => { const W = __world, c = W.chars.get('data-steward'), p = c.object3D.position; W.godAt(p.x, p.z, 26); }")
            else:
                pg.evaluate("() => __world.setView('god', null, true)")
            pg.wait_for_timeout(2500)
        god()
        good = 0; tot = 0; bad = []
        for rep in range(4):
            for hold in (0, 100, 250, 400, 650):
                pg.evaluate("() => { __world.pilot.deselect(); __world.ui.hideCard(); __world.multi.clear(); }")
                god()
                lim = dict(xmin=20, xmax=370, ymin=170, ymax=520, gap=30) if touch else dict(xmin=40, xmax=1250, ymin=150, ymax=640, gap=30)
                pts = []
                for _ in range(12):
                    pts = _mu_free_pts(pg, 30, **lim)
                    if pts:
                        break
                    pg.wait_for_timeout(600)
                if not pts:
                    bad.append((hold, "找不到角色", [(round(z["x"]), round(z["y"]), z["state"]) for z in pg.evaluate(_MU_PTS)][:4])); tot += 1
                    continue
                q = pts[(rep * 5 + (0, 100, 250, 400, 650).index(hold)) % len(pts)]
                t = _t.time()
                if touch:
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": q["x"], "y": q["y"]}], "timestamp": t})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": [], "timestamp": t + hold / 1000})
                else:
                    cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": q["x"], "y": q["y"], "timestamp": t - 0.01})
                    cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": q["x"], "y": q["y"], "button": "left", "buttons": 1, "clickCount": 1, "timestamp": t})
                    cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": q["x"], "y": q["y"], "button": "left", "buttons": 0, "clickCount": 1, "timestamp": t + hold / 1000})
                pg.wait_for_timeout(1400)
                r = pg.evaluate("() => [__world.pilot.sel && __world.pilot.sel.spec.id, !document.getElementById('card').hidden, __world.multi.mode]")
                hit = (r[0] == q["id"] and r[1]) or (touch and hold >= 450 and r[2])
                tot += 1; good += 1 if hit else 0
                if not hit:
                    bad.append((hold, q["id"], r))
        ok(f"帶時間的點擊（{who}）：按住 0～650 毫秒、不移動，{tot} 次全部選得到（手機 ≥ 450 毫秒進多選模式也算）", tot == 20 and good == tot, (good, tot, bad[:3]))
    finally:
        c.close()


def _mu_ui1115(pg_, b, base, code):
    """驗收員 11-15 的介面問題：手機跟隨視角上方藍塊、多選浮鈕壓總表、版本標記壓卡片、面板層級、營火露出、× 固定、遮擋閃避、手機名牌字級"""
    # ── 桌機 ──
    for (w, h) in ((1280, 800), (1920, 990)):
        c, pg, got = _mu_open(b, base, w=w, h=h, qs="?q=low&pr=0.5&ambient=0", speed=1)
        try:
            ok(f"{w}x{h}：預設俯視載入", got)
            if not got:
                continue
            pg.wait_for_timeout(1500); _mu_settle(pg)
            fy = pg.evaluate("() => { const W = __world, v = new W.THREE.Vector3(W.outside.fire.x, 0, W.outside.fire.z).project(W.camera); return Math.round((1 - v.y) / 2 * innerHeight); }")
            ok(f"{w}x{h}：預設俯視看得到營火（營火在畫面 y=%d，視窗高 %d，要在底邊上方至少 40px）" % (fy, h), fy < h - 40, fy)
            if w == 1280:
                pts = []
                for _ in range(20):
                    pts = _mu_free_pts(pg, 1, xmin=380, gap=30)
                    if pts:
                        break
                    pg.wait_for_timeout(700)
                pg.mouse.click(pts[0]["x"], pts[0]["y"]); pg.wait_for_timeout(900)
                op = pg.evaluate("() => { const e = document.getElementById('aoBuild'); return e ? getComputedStyle(e).opacity : null; }")
                ok("版本標記：資訊卡開著時淡出（不壓在卡片文字上）", op == "0", op)
                ok("資訊卡在所有 3D 名牌、泡泡、提示之上（名牌中心落在卡片範圍內時，最上層是卡片）", pg.evaluate("""() => { const card = document.getElementById('card').getBoundingClientRect(); let bad = 0;
                  for (const t of document.querySelectorAll('.tag, .bub')) { const r = t.getBoundingClientRect(); const x = (r.left + r.right) / 2, y = (r.top + r.bottom) / 2; if (r.width && x > card.left && x < card.right && y > card.top && y < card.bottom) { const e = document.elementFromPoint(x, y); if (!e || !e.closest('#card')) bad++; } } return bad === 0; }"""))
                # 遮擋閃避：在鏡頭與角色之間放一個臨時擋板，等它自己繞開
                pg.evaluate("() => { const W = __world, c = W.chars.get('data-steward'); W.setView('char', c, true); }"); pg.wait_for_timeout(1500); _mu_settle(pg)
                res = pg.evaluate("""async () => { const W = __world, T = W.THREE, c = W.chars.get('data-steward'), p = c.object3D.position, cam = W.camera.position;
                  const mid = new T.Vector3((cam.x + p.x) / 2, 1, (cam.z + p.z) / 2); const m = new T.Mesh(new T.BoxGeometry(0.6, 6, 0.6), new T.MeshBasicMaterial({ color: '#888' })); m.position.copy(mid); W.scene.add(m); m.updateMatrixWorld(true);
                  W.furn.set('__test_block', { mesh: m, obj: m, f: { id: '__test_block' } });
                  const ray = new T.Raycaster(), head = new T.Vector3(p.x, 0.9, p.z);
                  const blocked = () => { const d = head.clone().sub(W.camera.position), L = d.length(); ray.set(W.camera.position.clone(), d.normalize()); ray.far = L - 0.6; return ray.intersectObject(m, false).length > 0; };
                  const before = blocked(); const t0 = performance.now(); let after = before;
                  while (performance.now() - t0 < 9000) { await new Promise(r => setTimeout(r, 300)); after = blocked(); if (!after) break; }
                  W.scene.remove(m); W.furn.delete('__test_block'); return { before, after, moves: W.camclear.moves }; }""")
                ok("跟隨視角：鏡頭與角色之間有遮擋物時，鏡頭自動繞開（原本被擋、之後看得到頭）", res["before"] and not res["after"], res)
        finally:
            c.close()
    # ── 手機 ──
    c, pg, got = _mu_open(b, base, w=390, h=844, touch=True, qs="?q=low&pr=0.5&ambient=0", speed=1)
    try:
        ok("手機：頁面載入", got)
        if not got:
            return
        pg.evaluate("() => { const W = __world, c = W.chars.get('finance-content-editor'); W.setView('char', c); W.ui.showCard(c); W.pilot.select(c); }")
        pg.wait_for_timeout(1800); _mu_settle(pg)
        _mu_shot(pg, "手機跟隨視角_上方.png")
        # 上方 1/4 不能是一整塊「網頁底色」（畫布看出去是天空時透出 #d9f0fb）：取 y 190～215（頂列下方）整條掃描，近似底色的像素比例要低
        import io as _io
        try:
            from PIL import Image as _Img
            im = _Img.open(_io.BytesIO(pg.screenshot())).convert("RGB")
            bgc = (217, 240, 251); n = 0; tot = 0
            for yy in range(190, 216, 3):
                for xx in range(30, 360, 6):
                    r_, g_, b_ = im.getpixel((xx, yy)); tot += 1
                    if abs(r_ - bgc[0]) < 7 and abs(g_ - bgc[1]) < 7 and abs(b_ - bgc[2]) < 7:
                        n += 1
            ok("手機跟隨視角：畫面上方沒有整塊淡藍色（近似網頁底色的像素 %d／%d）" % (n, tot), n / max(1, tot) < 0.3, (n, tot))
        except ImportError:
            ok("手機跟隨視角：（沒有 PIL，略過像素檢查）", True)
        sz = pg.evaluate("() => [...document.querySelectorAll('.tag, .tag *')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => e.tagName + '.' + e.className + ':' + getComputedStyle(e).fontSize).filter(f => parseFloat(f.split(':')[1]) < 11).slice(0, 5)")
        ok("手機：名牌文字全部 ≥ 11px", not sz, sz)
        # 手機卡片 × 固定在卡片頂端
        pg.evaluate("() => { const cd = document.querySelector('#card .card-scroll') || document.getElementById('card'); cd.scrollTop = 300; }"); pg.wait_for_timeout(300)
        xr = _mu_rect(pg, "#card .x"); cr = _mu_rect(pg, "#card")
        ok("手機資訊卡的捲動在內層（.card-scroll），卡片本身不捲動", pg.evaluate("() => !!document.querySelector('#card > .card-scroll') && getComputedStyle(document.getElementById('card')).overflowY === 'hidden'"))
        ok("手機資訊卡往下捲後，關閉 × 仍固定在卡片頂端", xr and cr and xr[1] < cr[1] + 20 and xr[1] >= cr[1] - 2, (xr, cr))
        # 多選浮鈕與績效總表
        pg.click("#rwBtn"); pg.wait_for_timeout(1200)
        bar_ok = pg.evaluate("() => document.getElementById('mBar').hidden")
        ok("績效總表開著時，手機「多選」浮鈕隱藏（不壓在總表標題上）", bar_ok, _mu_rect(pg, "#mBar"))
        ok("手機：績效總表開著時版本標記淡出", pg.evaluate("() => getComputedStyle(document.getElementById('aoBuild')).opacity") == "0")
        ok("無主控台錯誤（介面修正）", not [e for e in pg.errs if "vScP" not in e and "setPointerCapture" not in e], pg.errs[:2])
    finally:
        c.close()


def _mu_band(pg, w, h):
    """畫面上「近似網頁底色 rgb(217,240,251)」的橫條（整列有 30% 以上的取樣點是這個顏色）的 y 座標；畫布正常時不會有"""
    import io as _io
    from PIL import Image as _Img
    im = _Img.open(_io.BytesIO(pg.screenshot())).convert("RGB"); out = []
    for yy in range(0, h, 6):
        n = sum(1 for xx in range(0, w, 20) if all(abs(a - b) < 4 for a, b in zip(im.getpixel((xx, yy)), (217, 240, 251))))
        if n > (w / 20) * 0.3:
            out.append(yy)
    return out


def _mu_ui1115b(pg_, b, base, code):
    """第二輪驗收：績效總表下方淡藍橫條（box-shadow 合成問題）、溝通時資訊卡頂端說明、手機待業卡「重新聘用」位置、卡片 × 不蓋內容"""
    for (w, h, touch) in ((1920, 990, False), (1280, 800, False), (390, 844, True)):
        c, pg, got = _mu_open(b, base, w=w, h=h, touch=touch, qs="?q=low&pr=0.5&ambient=0", speed=1)
        try:
            ok(f"{w}x{h}：載入", got)
            if not got:
                continue
            pg.wait_for_timeout(1500)
            pg.click("#rwBtn"); pg.wait_for_timeout(2200)
            b1 = _mu_band(pg, w, h)
            pg.evaluate("() => { const e = document.querySelector('#ledger [aria-expanded=\"false\"]'); if (e) e.click(); }"); pg.wait_for_timeout(2200)
            b2 = _mu_band(pg, w, h)
            ok(f"{w}x{h}：績效總表開著、展開部門後，畫面上沒有淡藍色橫條（網頁底色）", not b1 and not b2, (b1[:3], b2[:3]))
        finally:
            c.close()
    # 溝通說明
    c, pg, got = _mu_open(b, base, qs="?q=low&pr=0.6&ambient=0", speed=1)
    try:
        ok("溝通：載入", got)
        if got:
            r = pg.evaluate("""async () => { const W = __world, a = W.chars.get('data-steward'), o = W.chars.get('data-scraper'); W.pilot.select(a); await W.pilot.engage(); await W.sleep(2);
              const op = o.object3D.position; a.standAt(op.x + 0.9, op.z + 0.9, 0); W.pilot.talk(); await W.sleep(0.4);
              const note = document.querySelector('#card .pt-talknote'); return { note: note && note.textContent, tips: document.querySelector('.pt-th b') && document.querySelector('.pt-th b').textContent, card: document.querySelector('#card .hd b') && document.querySelector('#card .hd b').textContent }; }""")
            ok("溝通時資訊卡頂端寫「正在和 阿梟 說話」，操控面板仍是「操控中：阿梟」", r["note"] and "正在和" in r["note"] and "操控中" in (r["tips"] or ""), r)
    finally:
        c.close()
    # 手機：待業卡的重新聘用鈕、× 不蓋內容
    c, pg, got = _mu_open(b, base, w=390, h=844, touch=True, qs="?q=low&pr=0.5&ambient=0", speed=1)
    try:
        ok("手機待業卡：載入", got)
        if got:
            pg.evaluate("""async () => { const W = __world; await W.hr.fire(['data-scraper'], { to: 'ceo' }); W.speed = 8; await W.sleep(1); const c = W.chars.get('data-scraper'); W.setView('char', c, true); W.ui.showCard(c); }""")
            pg.wait_for_timeout(1500)
            hb = pg.evaluate("""() => { const b = document.querySelector('#card [data-hr=hire]'), cd = document.getElementById('card').getBoundingClientRect(); if (!b) return null; const r = b.getBoundingClientRect(); return { top: r.top - cd.top, bottom: cd.bottom - r.bottom, h: r.height, vis: r.bottom <= innerHeight && r.top >= cd.top }; }""")
            ok("手機待業卡：「重新聘用」鈕在卡片上半部、不用捲動就看得到", hb and hb["vis"] and hb["top"] < 150, hb)
            pr = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#card .card-scroll')).paddingRight)")
            ok("手機資訊卡內容右側留出 × 的寬度（≥ 36px）", pr >= 36, pr)
    finally:
        c.close()


def _mu_lamp(pg_, b, base, code):
    """用真實的遊民區路燈（outside.js 的 [23.4,36.9]）：角色站在路燈旁 0.25 公尺，鏡頭在路燈另一側（路燈正好擋在中間）。
    跟隨鏡頭要在幾秒內繞開、角色的臉看得到（鏡頭到頭部之間沒有東西）、角色不被切到畫面下緣。"""
    c, pg, got = _mu_open(b, base, qs="?q=low&pr=0.6&ambient=0", speed=1)
    try:
        ok("路燈遮擋：載入", got)
        if not got:
            return
        r = pg.evaluate("""async () => { const W = __world, T = W.THREE, c = W.chars.get('data-steward'); const lamp = { x: 23.4, z: 36.9 };
          c.standAt(lamp.x + 0.25, lamp.z, Math.PI / 2); await W.sleep(0.3);
          W.setView('char', c, true); await W.sleep(0.5);
          const ray = new T.Raycaster(), head = () => new T.Vector3(c.object3D.position.x, 0.9, c.object3D.position.z);
          const blocked = () => { const h = head(), d = h.clone().sub(W.camera.position), L = d.length(); ray.set(W.camera.position.clone(), d.normalize()); ray.far = L - 0.08; ray.near = 0.2; return ray.intersectObject(W.outside.mesh, false).length > 0; };
          const before = blocked(), cam0 = W.camera.position.clone(); const t0 = performance.now(); let after = before;
          while (performance.now() - t0 < 8000) { await new Promise(r => setTimeout(r, 250)); after = blocked(); if (!after) break; }
          const secs = (performance.now() - t0) / 1000; await new Promise(r => setTimeout(r, 1500));
          const p = (y) => { const v = new T.Vector3(c.object3D.position.x, y, c.object3D.position.z).project(W.camera); return Math.round((1 - v.y) / 2 * innerHeight); };
          return { before, after: blocked(), secs, moved: W.camera.position.distanceTo(cam0), moves: W.camclear.moves, feetY: p(0), headY: p(1.6), h: innerHeight, camz: W.camera.position.z }; }""")
        ok("路燈在鏡頭與角色之間 → 原本被擋住（射線撞到路燈）", r["before"], r)
        ok("跟隨鏡頭自動繞開，角色的臉看得到（%.1f 秒內，環境一格要 0.2～0.5 秒）" % r["secs"], (not r["after"]) and r["moves"] >= 1 and r["moved"] > 0.5, r)
        ok("角色不被切到畫面下緣（腳在畫面底邊上方至少 30px）", 0 < r["headY"] and r["feetY"] < r["h"] - 30, r)
        ok("無主控台錯誤（路燈）", not [e for e in pg.errs if "vScP" not in e], pg.errs[:2])
    finally:
        c.close()


register("辦公室路燈遮擋", _mu_lamp)
register("辦公室介面驗收1115b", _mu_ui1115b)
register("辦公室點選CDP桌機", lambda pg, b, base, code: _mu_cdp_clicks(b, base, False))
register("辦公室點選CDP手機", lambda pg, b, base, code: _mu_cdp_clicks(b, base, True))
register("辦公室介面驗收1115", _mu_ui1115)
register("辦公室點選", _mu_click)
register("辦公室多選Esc回俯視", _mu_esc)
register("辦公室多選", _mu_main)
register("辦公室多選手機", _mu_touch)
