# 驗收段落「手機修正1016b」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）四件：
#   ①「出現可以一直往下滑的問題需要處理 限制適當範圍」：右側事件抽屜關著時寬 0，新聞清單在 0 寬裡逐字換行撐到兩萬 px 高，iOS 算進整頁捲動
#     → 關著時抽屜裡不排版（mobile4.js .m4shut）；頁尾下方留白 72 → 12。驗：手指往上滑到底，頁尾底離視窗底 ≤ 40；scrollHeight ≤ 頁尾底 + 40；
#     固定定位的框不准藏著比自己高的內容（0 寬／0 高卻 scrollHeight 很大＝iOS 會漏出去的那種）；抽屜真的打開時新聞清單照樣看得到。
#   ②「確保所有內容不要重疊」：資金輪動摘要句壓到免責一行（左欄直向 flex 被限高時兩者被壓縮）→ 手機不准壓縮。驗：自然狀態＋人為限高 560px 兩種都不相交。
#   ③「圖三重疊到樹狀圖」：資金分流樹「動態 開」搬進卡片標題列 → 鈕與畫布不相交、手指點一下真的切換；頂欄 360 寬每一顆不互相重疊、都在視窗內。
#   ④「"?" 圖示太大」：手機「?」視覺 ≤ 20px、字 ≥ 12px，點在圓外 13px 處（::after 觸控區）仍打開說明。
#   ⑤ 1440 桌機：同一顆「動態」鈕仍在畫布右上角的說明列、「?」仍是 22px（點了才出現的狀態，桌機守門涵蓋不到，這裡另外驗）。
FIX1016B_ROUTES = ["overview", "flow/rotation", "flow/sankey", "industry", "stock/2330", "heatmap/industry", "heatmap/theme", "season", "etf", "watch", "account", "pricing"]
FIX1016B_SCROLL_JS = """() => { const f = document.getElementById('siteFoot'); const fb = f && f.getClientRects().length ? f.getBoundingClientRect().bottom + scrollY : null;
  const leak = []; for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e); if (s.display === 'none' || s.position !== 'fixed') continue;
    if ((e.clientWidth === 0 || e.clientHeight === 0) && e.scrollHeight > innerHeight + 1) leak.push((e.id ? '#' + e.id : e.tagName) + ' sh=' + e.scrollHeight); }
  const sd = document.getElementById('side');
  return { sh: document.scrollingElement.scrollHeight, fb: fb == null ? null : Math.round(fb), H: innerHeight, sy: Math.round(scrollY),
           vgap: fb == null ? null : Math.round(scrollY + innerHeight - fb), leak, side: sd ? sd.scrollHeight : 0 }; }"""


def _fix1016b_swipe_bottom(c, pg):
    cdp = c.new_cdp_session(pg)
    for _ in range(12):
        cdp.send("Input.synthesizeScrollGesture", {"x": 200, "y": 600, "yDistance": -1500, "gestureSourceType": "touch", "speed": 6000})
        if pg.evaluate("() => Math.ceil(scrollY + innerHeight) >= document.scrollingElement.scrollHeight - 1"):
            break
    pg.wait_for_timeout(400)


def _fix1016b_rect(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); "
                       "return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; }", sel)


def _fix1016b_hit(a, b2):
    return bool(a and b2 and min(a[2], b2[2]) - max(a[0], b2[0]) > 0 and min(a[3], b2[3]) - max(a[1], b2[1]) > 0)


def t_m4_fix_1016b(b, base):
    T = "手機修正1016b"
    for w in (360, 390, 430):
        c = b.new_context(viewport={"width": w, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(((getattr(e, "stack", None) or str(e)) + " @" + pg.url.split("#")[-1])[:400]))
        # ① 頁尾以下不再一直滑
        for h in FIX1016B_ROUTES:
            pg.goto(base + "#" + h, wait_until="domcontentloaded")
            if not ok(f"【{T}】{w} #{h}：手機版就緒", bool(wait_until(pg, "() => document.documentElement.classList.contains('m4')", 20000))):
                continue
            pg.wait_for_timeout(2500)
            # 等版面穩定（前一頁的內容收掉、這一頁的卡畫完）再滑：scrollHeight 連兩次一樣
            wait_until(pg, "() => { const h = document.scrollingElement.scrollHeight; const o = window.__fx16h; window.__fx16h = h; return o === h; }", 8000, 500)
            _fix1016b_swipe_bottom(c, pg)
            g = pg.evaluate(FIX1016B_SCROLL_JS)
            ok(f"【{T}】{w} #{h}：手指滑到底 → 頁面不比一屏高，或 scrollHeight（{g['sh']}）≤ 頁尾底（{g['fb']}）+ 40 且頁尾底離視窗底 ≤ 40",
               g["fb"] is not None and (g["sh"] <= g["H"] + 1 or (g["sh"] <= g["fb"] + 40 and g["vgap"] <= 40)), g)
            ok(f"【{T}】{w} #{h}：沒有固定定位的框藏著比視窗還高的內容（關著的事件抽屜 scrollHeight {g['side']} ≤ 視窗高）",
               not g["leak"] and g["side"] <= g["H"], g)
        # 抽屜真的打開：新聞清單有東西、寬 > 250；關上 → 又收起來
        pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        pg.evaluate("() => window.twSetSide(true)"); pg.wait_for_timeout(500)
        o = pg.evaluate("() => { const s = document.getElementById('side'), l = document.getElementById('evList'); return { w: Math.round(s.getBoundingClientRect().width), lh: Math.round(l.getBoundingClientRect().height), n: l.querySelectorAll('.ev').length, cls: s.className }; }")
        ok(f"【{T}】{w}：事件抽屜打開 → 寬 > 250、新聞清單真的排出來（{o['n']} 則）", o["w"] > 250 and o["lh"] > 100 and "m4shut" not in o["cls"], o)
        pg.evaluate("() => window.twSetSide(false)"); pg.wait_for_timeout(700)
        o2 = pg.evaluate("() => ({ sh: document.getElementById('side').scrollHeight, cls: document.getElementById('side').className, H: innerHeight })")
        ok(f"【{T}】{w}：事件抽屜關上 → 滑出動畫後收起（m4shut）、scrollHeight ≤ 視窗高", "m4shut" in o2["cls"] and o2["sh"] <= o2["H"], o2)
        # ② 資金輪動摘要句 × 免責一行
        pg.goto(base + "#flow/rotation", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.querySelector('#flowRotCard .t4-lede') && document.querySelector('#flowRotCard .t4-lede').textContent.length > 5", 15000)
        pg.wait_for_timeout(800)
        for tag, js in (("自然狀態", "() => 0"), ("左欄被限高 560px（模擬 iOS）", "() => { document.querySelector('#flowRotCard .rotleft').style.height = '560px'; }")):
            pg.evaluate(js); pg.wait_for_timeout(200)
            d, l, hd = _fix1016b_rect(pg, "#flowRotDisc"), _fix1016b_rect(pg, "#flowRotCard .t4-lede"), _fix1016b_rect(pg, "#flowRotCard .rothead h3")
            ok(f"【{T}】{w} 資金輪動（{tag}）：摘要句不壓到免責一行、也不壓到標題", d and l and hd and not _fix1016b_hit(d, l) and not _fix1016b_hit(hd, l), {"disc": d, "lede": l, "h3": hd})
        # ④「?」視覺 ≤ 20px、字 ≥ 12px；點在圓外 13px（觸控區）仍打開說明
        pg.evaluate("() => { document.querySelector('#flowRotCard .rotleft').style.height = ''; scrollTo(0, 0); }"); pg.wait_for_timeout(300)
        q = pg.evaluate("""() => [...document.querySelectorAll('.view.on .howbtn.pop')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect();
            return { w: Math.round(r.width), h: Math.round(r.height), fs: parseFloat(getComputedStyle(e).fontSize), x: r.left + r.width / 2, y: r.top + r.height / 2 }; })""")
        ok(f"【{T}】{w} 資金輪動頁每一顆「?」視覺 ≤ 20px、字 ≥ 12px（{len(q)} 顆）", len(q) >= 1 and all(x["w"] <= 20 and x["h"] <= 20 and x["fs"] >= 12 for x in q), q[:4])
        if q:
            x0, y0 = q[0]["x"] + 13, q[0]["y"]
            hit = pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest('.howbtn.pop')); }", [x0, y0])
            pg.touchscreen.tap(x0, y0); pg.wait_for_timeout(600)
            op = pg.evaluate("() => { const p = document.getElementById('howPop'); return !!(p && !p.hidden && p.getClientRects().length && p.textContent.trim().length > 10); }")
            ok(f"【{T}】{w}：手指點在「?」圓外 13px → 還在觸控區內、說明真的打開", hit and op, {"hit": hit, "open": op})
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        # ③ 資金分流樹「動態」鈕在標題列、不蓋樹；手指點一下真的切換
        pg.goto(base + "#flow/sankey", wait_until="domcontentloaded")
        if ok(f"【{T}】{w} 資金分流樹：「動態」鈕出現", bool(wait_until(pg, "() => { const b = document.getElementById('sankeyMotionBtn'); return !!(b && b.getClientRects().length && document.querySelector('#flowSankeyCard .ftstage')); }", 20000))):
            pg.wait_for_timeout(600)
            bt, stg = _fix1016b_rect(pg, "#sankeyMotionBtn"), _fix1016b_rect(pg, "#flowSankeyCard .ftstage")
            inhd = pg.evaluate("() => !!document.getElementById('sankeyMotionBtn').closest('#flowSankeyCard > .row.spread')")
            ok(f"【{T}】{w} 資金分流樹：「動態」鈕在卡片標題列、跟樹的畫布不相交、在視窗內", inhd and not _fix1016b_hit(bt, stg) and bt[0] >= 0 and bt[2] <= w, {"btn": bt, "stage": stg})
            t0 = pg.evaluate("() => document.getElementById('sankeyMotionBtn').getAttribute('aria-pressed')")
            pg.locator("#sankeyMotionBtn").tap(); pg.wait_for_timeout(400)
            t1 = pg.evaluate("() => [document.getElementById('sankeyMotionBtn').getAttribute('aria-pressed'), document.getElementById('sankeyMotionBtn').textContent]")
            ok(f"【{T}】{w} 資金分流樹：手指點「動態」→ 開／關真的切換（{t1[1]}）", t1[0] != t0, (t0, t1))
            pg.locator("#sankeyMotionBtn").tap(); pg.wait_for_timeout(300)
            ok(f"【{T}】{w} 資金分流樹：只有一顆「動態」鈕（重畫沒有留下重複的 id）", pg.evaluate("() => document.querySelectorAll('#sankeyMotionBtn').length") == 1)
        # 總覽「資金流向」分段的昨日資金分流樹也一樣
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => document.querySelectorAll('#v-overview > .mpager > button').length === 3", 20000); pg.wait_for_timeout(1500)
        pg.locator("#v-overview > .mpager > button", has_text="資金流向").first.tap()
        if wait_until(pg, "() => { const b = document.getElementById('ovFlowMotionBtn'); return !!(b && b.getClientRects().length); }", 15000):
            bt, stg = _fix1016b_rect(pg, "#ovFlowMotionBtn"), _fix1016b_rect(pg, "#ovFlow .ftstage")
            ok(f"【{T}】{w} 總覽昨日資金分流樹：「動態」鈕不蓋樹", not _fix1016b_hit(bt, stg) and bt[2] <= w, {"btn": bt, "stage": stg})
        ok(f"【{T}】{w}：沒有 JS 錯誤", not errs, errs[:3])
        c.close()
        # ③ 頂欄（訪客＋全站額度圓環＋本頁限制）每一顆不重疊、都在視窗內
        PR = _gp_presets()
        c, _s, _t = _sub_ctx(b, None, width=w, feats=dict(PR["guest"]["feats"]), lims=dict(PR["guest"]["lims"]), dq=12, touch=True)
        q2 = c.new_page(); q2.goto(base + "#stock/2330", wait_until="domcontentloaded")
        okr = wait_until(q2, "() => { const e = document.getElementById('twQRing'); return !!(e && !e.hidden && e.getClientRects().length); }", 15000); q2.wait_for_timeout(1500)
        tb = q2.evaluate("""() => [...document.querySelectorAll('.topbar :is(button,a,img)')].filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && !e.closest('[hidden]'))
            .filter(e => { const r = e.getBoundingClientRect(); return r.width > 8 && r.top < 70; }).map(e => { const r = e.getBoundingClientRect();
            return [e.id || e.className.toString().slice(0, 12), Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; })""")
        bad = [(a[0], z[0]) for i, a in enumerate(tb) for z in tb[i + 1:] if _fix1016b_hit(a[1:], z[1:]) and not (a[1] <= z[1] and a[3] >= z[3] and a[2] <= z[2] and a[4] >= z[4]) and not (z[1] <= a[1] and z[3] >= a[3] and z[2] <= a[2] and z[4] >= a[4])]
        out = [x[0] for x in tb if x[1] < 0 or x[3] > w]
        ok(f"【{T}】{w} 頂欄（額度圓環＋本頁限制）：{len(tb)} 顆互不重疊、全部在視窗內", bool(okr) and not bad and not out, {"bad": bad, "out": out, "items": tb})
        c.close()
    # ⑤ 1440 桌機：動態鈕與「?」維持原樣
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
    pg = c.new_page(); pg.goto(base + "#flow/sankey", wait_until="domcontentloaded")
    if wait_until(pg, "() => { const b = document.getElementById('sankeyMotionBtn'); return !!(b && b.getClientRects().length); }", 20000):
        d = pg.evaluate("() => { const b = document.getElementById('sankeyMotionBtn'), h = document.querySelector('#flowSankeyCard .howbtn.pop').getBoundingClientRect(); "
                        "return { bar: !!b.closest('.ftstage > .ftbar.ftfloat'), m4hd: b.classList.contains('ftm4hd'), hw: Math.round(h.width), shut: document.getElementById('side').classList.contains('m4shut') }; }")
        ok(f"【{T}】1440：「動態」鈕仍浮在畫布右上角說明列、「?」仍 22px、事件抽屜沒有 m4shut", d["bar"] and not d["m4hd"] and d["hw"] == 22 and not d["shut"], d)
    else:
        ok(f"【{T}】1440：資金分流樹「動態」鈕出現", False)
    c.close()


# ★ 2026-10-16 Andy（iPhone）：「可以一直往下滑…限制適當範圍」「確保所有內容不要重疊」「圖三重疊到樹狀圖」「"?" 圖示太大」—— 頁尾底、摘要×免責、動態鈕×樹、頂欄、「?」尺寸＋觸控區（360／390／430＋1440 對照）
register("手機修正1016b", lambda pg, b, base, code: t_m4_fix_1016b(b, base), after="手機帳號選單登入框1016")
