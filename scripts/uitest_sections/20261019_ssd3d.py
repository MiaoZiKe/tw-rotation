# 驗收段落「SSD3D1019」—— 2026-10-19 Andy：「SSD 也要，請繪圖團隊補 3D 圖」。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、fails、notes… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
#
# 規格：docs/diagram_specs/ssd.md。場景 SCENES.ssd（site/three3d.js），掛在族群 memory_module（site/dg/memory_module.js）。
# 路由 #industry/semiconductor/dg/memory_module。驗的是「畫面真的因此改變」，不是元素存在：
#   ① 1440／390 真的掛得起 3D、零件 11 件、環節對得上規格書
#   ② 真的用滑鼠點零件 → 那張小卡被選起來、卡上的環節就是那個零件的環節、晶片列出規格書寫的台股
#   ③ 爆炸：游標移進畫布（1440）／點背景（390）→ 零件真的離開原位（exMove 由 0 變大、pose 變了）；移出／再點 → 收回
#   ④ 2D 退路：11 個零件的 data-part 都在、點一個零件會被選起來
#   ⑤ 全程沒有網頁錯誤；1440 的卡片兩兩不重疊、字 ≥ 12px；390 的編號鈕兩兩不重疊
#   ⚠ 有 3D，一律 --workers 1。

SSD3D_ROUTE = "industry/semiconductor/dg/memory_module"
SSD3D_PARTS = {
    "ssd_pcb": "hdi_pcb", "ssd_finger": "hdi_pcb", "ssd_ctrl": "storage", "ssd_dram": "dram_nor",
    "ssd_nand": "storage", "ssd_nand_die": "storage", "ssd_pmic": "ic_design", "ssd_ind": "passive_inductor",
    "ssd_mlcc": "passive_comp", "ssd_hs": "thermal", "ssd_socket": "connector",
}
SSD3D_CODES = {"ssd_ctrl": ["8299"], "ssd_nand": ["6239"], "ssd_socket": ["3533"]}
SSD3D_RECTS = r"""(sel) => [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && +getComputedStyle(e).opacity > 0.05)
  .map(e => { const r = e.getBoundingClientRect(); return { k: e.dataset.dgpart || e.textContent.trim(), l: r.left, t: r.top, r: r.right, b: r.bottom }; })"""
SSD3D_MINFS = r"""(sel) => { let m = 99; document.querySelectorAll(sel).forEach(e => { if (!e.getClientRects().length) return;
  e.querySelectorAll('b,i,a,s').forEach(x => { if (!x.textContent.trim() || !x.getClientRects().length) return; m = Math.min(m, parseFloat(getComputedStyle(x).fontSize)); }); }); return m; }"""


def _ssd3d_overlaps(rects, pad=0.5):
    bad = []
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, c = rects[i], rects[j]
            if min(a["r"], c["r"]) - max(a["l"], c["l"]) > pad and min(a["b"], c["b"]) - max(a["t"], c["t"]) > pad:
                bad.append((a["k"], c["k"]))
    return bad


def _ssd3d_open(m, base):
    m.goto(base + "#" + SSD3D_ROUTE, wait_until="domcontentloaded")
    wait_until(m, "() => { const g = document.querySelector('#dg3d'); return !!(g && !g.hidden && g.getClientRects().length); }", 30000, 300)
    m.wait_for_timeout(600)
    m.evaluate("() => document.querySelector('#dgSec') && document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })")
    m.wait_for_timeout(400)
    if not m.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
        b3 = m.query_selector("#dg3d button[data-dm='3d']")
        if b3:
            b3.click()
    wait_until(m, "() => !!(window.Rack3D && window.Rack3D.current && /SSD/.test(window.Rack3D.current.title))", 30000, 300)
    m.wait_for_timeout(1800)
    return m.evaluate("() => !!(window.Rack3D && window.Rack3D.current && /SSD/.test(window.Rack3D.current.title))")


def _ssd3d_hit(m, part):
    """在零件錨點附近掃一小圈，找一個 raycast 真的打得到它本人的像素（被別的零件擋住就換一點）。"""
    pt = m.evaluate("(p) => window.Rack3D.current.pointOf(p)", part)
    if not pt:
        return None
    for dy in (0, 3, -3, 6, -6, 10, 14):
        for dx in (0, -6, 6, -12, 12):
            h = m.evaluate("([x, y]) => window.Rack3D.current.hitAt(x, y)", [pt["x"] + dx, pt["y"] + dy])
            if h == part:
                return (pt["x"] + dx, pt["y"] + dy)
    # 錨點附近都被別的零件擋住 → 在它的螢幕範圍裡掃格子，挑離中心最近、而且打得到它本人的那一點
    return m.evaluate("""(p) => { const v = window.Rack3D.current, r = v.rectOf(p); if (!r) return null;
      const cx = (r.l + r.r) / 2, cy = (r.t + r.b) / 2; let best = null, bd = 1e9;
      for (let x = Math.max(r.l, r.canvas.l + 2); x < Math.min(r.r, r.canvas.r - 2); x += 5)
        for (let y = Math.max(r.t, r.canvas.t + 2); y < Math.min(r.b, r.canvas.b - 2); y += 5) {
          if (v.hitAt(x, y) !== p) continue; const d = Math.hypot(x - cx, y - cy); if (d < bd) { bd = d; best = [x, y]; } }
      return best; }""", part)


def t_ssd3d_1019(b, base):
    T = "SSD3D1019"
    for W, H in ((1440, 900), (390, 844)):
        mob = W < 640
        ctx = b.new_context(viewport={"width": W, "height": H}, is_mobile=mob, has_touch=mob)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('ssd3d')){ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1');"
                            " localStorage.setItem('tw.dg3d','1'); localStorage.setItem('tw.dganim','1'); sessionStorage.setItem('ssd3d','1'); } }catch(e){}")
        m = ctx.new_page()
        errs = []
        m.on("pageerror", lambda e: errs.append(str(e)))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = m.evaluate
        try:
            # ---- ① 掛得起來、零件數與環節 ----
            if not ok(f"【{T}】{W} SSD 3D 場景掛得起來（{SSD3D_ROUTE}）", _ssd3d_open(m, base), J("location.hash")):
                continue
            segs = J("() => window.Rack3D.current.segs()")
            parts = J("() => Object.keys(window.Rack3D.SCENES.ssd.parts.reduce((o, p) => (o[p.part] = p.seg, o), {}))")
            ok(f"【{T}】{W} 零件 11 件（{len(segs)}）", len(segs) == 11, segs)
            seg_of = J("() => window.Rack3D.SCENES.ssd.parts.reduce((o, p) => (o[p.part] = p.seg, o), {})")
            ok(f"【{T}】{W} 每個零件的環節照規格書（docs/diagram_specs/ssd.md §2）", seg_of == SSD3D_PARTS, seg_of)
            st = J("() => window.Rack3D.current.stats()")
            ok(f"【{T}】{W} 效能上限：draw call ≤ 300（{st.get('drawCalls')}）、三角形 ≤ 150,000（{st.get('triangles')}）",
               (st.get("drawCalls") or 0) <= 300 and (st.get("triangles") or 0) <= 150000, st.get("triangles"))
            # ---- ③ 爆炸切換：零件真的離開原位、再收回 ----
            if not mob:
                m.mouse.move(2, 2); m.wait_for_timeout(2600)      # 游標不在畫布上 → 收攏
            v0 = J("() => ({ ex: window.Rack3D.current.stats().exMove, pose: window.Rack3D.current.pose() })")
            if mob:
                bg = None
                cv = J("() => { const r = document.querySelector('#prod3d canvas').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
                for fy in (0.12, 0.2, 0.85):
                    for fx in (0.5, 0.3, 0.7):
                        x, y = cv[0] + cv[2] * fx, cv[1] + cv[3] * fy
                        if J("([x, y]) => window.Rack3D.current.hitAt(x, y)", [x, y]) is None and y > 60 and y < H - 60:
                            bg = (x, y); break
                    if bg:
                        break
                ok(f"【{T}】{W} 找得到畫布上的空白處（點它切換展開）", bool(bg), cv)
                if bg:
                    m.touchscreen.tap(*bg)
            else:
                cv = J("() => { const r = document.querySelector('#prod3d canvas').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                m.mouse.move(cv[0], cv[1], steps=4)
            m.wait_for_timeout(2600)
            v1 = J("() => ({ ex: window.Rack3D.current.stats().exMove, pose: window.Rack3D.current.pose() })")
            moved = sum(1 for a, c in zip(v0["pose"], v1["pose"]) if a != c)
            ok(f"【{T}】{W} 爆炸：零件真的離開原位（離原位最遠 {v0['ex']} → {v1['ex']}、{moved} 個零件位置變了）",
               v1["ex"] > v0["ex"] + 3 and moved >= 5, {"v0": v0["ex"], "v1": v1["ex"], "moved": moved})
            if mob:
                if bg:
                    m.touchscreen.tap(*bg)
            else:
                m.mouse.move(2, 2, steps=3)
            m.wait_for_timeout(2600)
            v2 = J("() => window.Rack3D.current.stats().exMove")
            ok(f"【{T}】{W} 再切一次 → 收回原位（{v1['ex']} → {v2}）", v2 < v1["ex"] - 3, v2)
            # ---- ② 真的點零件 → 小卡選到它、環節對、台股晶片對 ----
            for pid in ("ssd_ctrl", "ssd_nand", "ssd_socket"):
                spot = _ssd3d_hit(m, pid)
                if not ok(f"【{T}】{W} 找得到點得到「{pid}」本人的像素", bool(spot), pid):
                    continue
                if mob:
                    m.touchscreen.tap(*spot)
                else:
                    m.mouse.click(*spot)
                m.wait_for_timeout(900)
                if mob:
                    # 手機：卡片收成底部抽屜（編號＋名稱＋說明＋台股），點零件或編號打開
                    sh = J("""() => { const s = document.getElementById('mSheet'); if (!s || s.hidden || !s.getClientRects().length) return null;
                      return { txt: s.innerText, codes: [...s.querySelectorAll('a[href^="#stock/"]')].map(a => a.getAttribute('href').slice(7)) }; }""")
                    sel = J("() => [...document.querySelectorAll('#prod3d .lbl3d.sel-part')].map(e => ({ part: e.dataset.dgpart, seg: e.dataset.seg }))")
                    picked = (sel and sel[0]["part"] == pid) or bool(sh)
                    ok(f"【{T}】{W} 點「{pid}」→ 被選起來（小卡 {sel}／抽屜 {bool(sh)}）", picked, {"sel": sel, "sheet": (sh or {}).get("txt", "")[:80]})
                    if sh:
                        J("() => window.M3 && M3.closeSheet ? M3.closeSheet() : document.getElementById('mSheetBack') && document.getElementById('mSheetBack').click()")
                        m.wait_for_timeout(500)
                else:
                    sel = J("""() => [...document.querySelectorAll('#prod3d .lbl3d.sel-part')].map(e => ({ part: e.dataset.dgpart, seg: e.dataset.seg,
                      codes: [...e.querySelectorAll('a.chip3d')].map(a => a.getAttribute('href').slice(7)) }))""")
                    hit = [s for s in sel if s["part"] == pid]
                    ok(f"【{T}】{W} 真的點「{pid}」→ 那張小卡被選起來、卡上的環節是 {SSD3D_PARTS[pid]}",
                       bool(hit) and hit[0]["seg"] == SSD3D_PARTS[pid], sel)
                    if hit and pid in SSD3D_CODES:
                        ok(f"【{T}】{W} 「{pid}」小卡列出 {SSD3D_CODES[pid]}（零件自己的 codes，不是環節預設名單）",
                           all(c in hit[0]["codes"] for c in SSD3D_CODES[pid]), hit[0]["codes"])
                    m.mouse.move(2, 2); m.wait_for_timeout(300)
            # NAND 晶粒堆疊：codes:[] → 卡上明說台股無直接對應（不是留白、也不是列外商）
            if not mob:
                die = J("() => { const e = document.querySelector('#prod3d .lbl3d[data-dgpart=\"ssd_nand_die\"]'); return e ? e.querySelector('u.chips3d').textContent : null; }")
                ok(f"【{T}】{W} NAND 晶粒那張卡寫「台股無直接對應」（{die}）", bool(die) and "台股無直接對應" in die, die)
            # ---- ⑤ 文字不重疊、字級 ----
            if mob:
                nums = J(SSD3D_RECTS, "#prod3d .mnumlayer .mnum")
                ok(f"【{T}】{W} 編號鈕有 {len(nums)} 顆、兩兩不重疊", len(nums) >= 8 and not _ssd3d_overlaps(nums), _ssd3d_overlaps(nums)[:5])
            else:
                cards = J(SSD3D_RECTS, "#prod3d .lbl3d")
                ok(f"【{T}】{W} 3D 文字框 11 張、兩兩不重疊", len(cards) == 11 and not _ssd3d_overlaps(cards), {"n": len(cards), "ov": _ssd3d_overlaps(cards)[:5]})
                fs = J(SSD3D_MINFS, "#prod3d .lbl3d")
                ok(f"【{T}】{W} 3D 文字框最小字級 ≥ 12px（{fs}）", fs >= 12, fs)
            # ---- ④ 2D 退路：零件都在、點得到 ----
            b2 = m.query_selector("#dg3d button[data-dm='2d']")
            if b2:
                if mob:
                    b2.tap()
                else:
                    b2.click()
                m.wait_for_timeout(1500)
                got = J("() => [...new Set([...document.querySelectorAll('#prodDiagram [data-part]')].map(e => e.dataset.part))]")
                miss = [k for k in SSD3D_PARTS if k not in got]
                ok(f"【{T}】{W} 2D 退路：11 個零件的 data-part 都在（缺 {miss}）", not miss, got)
                if not mob:
                    J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })"); m.wait_for_timeout(400)
                    tg = m.query_selector("#prodDiagram g[data-part='ssd_dram'] .part")
                    if tg:
                        tg.click(); m.wait_for_timeout(700)
                        on = J("() => !!document.querySelector('#prodDiagram g[data-part=\"ssd_dram\"].sel-part, #prodDiagram g[data-part=\"ssd_dram\"] .sel-part, .dgc.sel-part[data-part=\"ssd_dram\"]')")
                        ok(f"【{T}】{W} 2D 點 DRAM → 被選起來", on, on)
                J("() => { try { localStorage.setItem('tw.dg3d', '1'); } catch (e) {} }")
            ok(f"【{T}】{W} 全程沒有網頁錯誤", not errs, errs[:3])
        finally:
            ctx.close()


# ★ 2026-10-19 Andy：「SSD 也要，請繪圖團隊補 3D 圖」（1440＋390；⚠ --workers 1）
register("SSD3D1019", lambda pg, b, base, code: t_ssd3d_1019(b, base))
