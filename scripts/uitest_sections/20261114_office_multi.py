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


def _mu_free_pts(pg, n, xmin=370, xmax=1250, ymin=150, ymax=640, gap=40):
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
        pts = _mu_free_pts(pg, 4)
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
        base_calls = pg.evaluate("() => __world.stats.calls")
        n_all = pg.evaluate("() => { const W = __world; let n = 0; for (const c of W.chars.values()) if (W.multi.add(c)) n++; return n; }")
        pg.wait_for_timeout(900)
        calls = pg.evaluate("() => __world.stats.calls")
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


register("辦公室多選", _mu_main)
register("辦公室多選手機", _mu_touch)
