# 驗收段落「手機3D分頁1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 手機3D分頁1016（Andy iPhone 實機：「嚴重問題，產業地圖切換到3D圖之後 其他分頁不能使用」）
#   病因一（Chromium 也重現得到）：3D 點編號開了底部抽屜之後，上方分頁列被抽屜背景 #mSheetBack 蓋住 ——
#     手指點分頁＝點背景，只關抽屜、分頁不切，看起來就是「點不動」。修法：點背景照舊關，手指底下若是分頁類就順手交給它（mobile3.js TAPTHRU）。
#   病因二（iOS 才有，這裡用「touchend 被 preventDefault＝瀏覽器不補發 click」模擬）：分頁鈕灰一下卻沒切。
#     修法：mobile4.js 的分頁保險絲 —— 原地點放開 450ms 內沒收到 click 就補一個（data-m4tapfix 記補了幾次）。
#   病因三：iOS 長按跳「拷貝｜使用 Google 搜尋」→ 3D 畫布、編號、引線、分頁列在手機一律 user-select:none＋-webkit-touch-callout:none（site/m4/20261016-02-3d-noselect.css；原本在 mobile4.css 末節），開關抽屜清掉選取。
#   全部用 touchscreen.tap（真的手指點）；360／390／430 三種寬度。
M43DPOP_ST = r"""() => { const s = document.getElementById('mSheet'), k = document.getElementById('mSheetBack');
  const vis = e => !!(e && !e.hidden && e.getClientRects().length && getComputedStyle(e).display !== 'none');
  const big = [...document.querySelectorAll('body *')].filter(e => { const c = getComputedStyle(e); if (c.position !== 'fixed') return false;
    const r = e.getBoundingClientRect(); return r.width >= innerWidth * 0.9 && r.height >= innerHeight * 0.5 && c.display !== 'none' && c.visibility !== 'hidden' && c.pointerEvents !== 'none' && +c.opacity > 0.01; }).map(e => e.id || e.className);
  return { sheet: vis(s), scrim: vis(k), big, hash: location.hash, sel: (getSelection() || {}).rangeCount || 0,
    bodyOv: getComputedStyle(document.body).overflowY, htmlOv: getComputedStyle(document.documentElement).overflowY, drawer: !!(window.TwM4 && TwM4.isOpen()) }; }"""
M43DPOP_XY = r"""(q) => { let e = null;
  if (q.startsWith('txt:')) { const [sel, re] = q.slice(4).split('|'); e = [...document.querySelectorAll(sel)].find(x => new RegExp(re).test(x.textContent)); }
  else e = document.querySelector(q);
  if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"""


def t_m4_3dpop_1016(b, base):
    T = "手機3D分頁1016"
    SHOT = os.environ.get("TW_M43DPOP_SHOT")
    for W, H in ((360, 780), (390, 844), (430, 932)):
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2 if SHOT else 1, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('m43p')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1');"
                            " localStorage.setItem('tw.m4.3danim','0'); sessionStorage.setItem('m43p','1'); } }catch(e){}")
        m = ctx.new_page()
        m.on("pageerror", lambda e, W=W: fails.append(f"{T} {W} pageerror: {e}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = m.evaluate
        st = lambda: J(M43DPOP_ST)

        def tapq(q, wait=900):
            xy = J(M43DPOP_XY, q)
            if xy:
                m.touchscreen.tap(*xy); m.wait_for_timeout(wait)
            return xy

        def open3d(dg):
            m.goto(base + "#industry/semiconductor/dg/" + dg, wait_until="domcontentloaded")
            wait_until(m, "() => { const g = document.querySelector('#dg3d'); return !!(g && g.getClientRects().length && document.querySelector('#dgPick')); }", 30000, 300)
            m.wait_for_timeout(600)
            if J("() => document.querySelector('#prod3d').hidden"):
                J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })"); m.wait_for_timeout(500)
                tapq("#dg3d button[data-dm='3d']")
            got = wait_until(m, "() => { const h = document.querySelector('#prod3d'); return !!(h && !h.hidden && h.querySelector('.mnumlayer .mnum')); }", 30000, 300)
            # 分頁列與 3D 編號同時在畫面上（Andy 截圖的姿勢）：把子分頁列捲到頂欄下方
            J("() => { const r = document.querySelector('#dgPick').getBoundingClientRect(); scrollBy(0, r.top - 130); }"); m.wait_for_timeout(1200)
            return got

        def tapnum():
            xy = J("() => { const b = [...document.querySelectorAll('#prod3d .mnumlayer .mnum')].find(b => { const r = b.getBoundingClientRect(); return r.top > 220 && r.bottom < innerHeight - 90; });"
                   " if (!b) return null; const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
            if xy:
                m.touchscreen.tap(*xy); m.wait_for_timeout(900)
            return st()
        try:
            # ---- 0. 防選字：3D 畫布、編號、引線、分頁列在手機都不能被選字（iOS 不跳「拷貝｜Google 搜尋」）----
            if not ok(f"【{T}】{W} 晶圓代工切進 3D 有編號", open3d("foundry")):
                continue
            # Chromium 不認得 -webkit-touch-callout，cssText 會把它丟掉 → 直接讀樣式表原文確認規則在、而且跟 #prod3d 寫在同一段
            #   （2026-10-16 拆檔：這一段從 mobile4.css 尾巴搬到 m4/20261016-02-3d-noselect.css）
            css = J("() => fetch('m4/20261016-02-3d-noselect.css', { cache: 'no-store' }).then(r => r.text())") or ""
            sec = css[css.find("2026-10-16 手機 3D 不准跳出"):] if "2026-10-16 手機 3D 不准跳出" in css else ""
            callout = "-webkit-touch-callout:none" in sec and "#prod3d" in sec and ".mnumlayer" in sec
            us = J("""() => { const q = s => document.querySelector(s); const u = e => e ? getComputedStyle(e).userSelect || getComputedStyle(e).webkitUserSelect : 'missing';
              return { canvas: u(q('#prod3d canvas')), num: u(q('#prod3d .mnumlayer .mnum')), lead: u(q('#prod3d .mnumlayer svg')), tab: u(q('#dgPick .segchip')), chain: u(q('#chainSwitch button')) }; }""")
            us["callout"] = callout
            ok(f"【{T}】{W} 3D 畫布／編號／引線／分頁列 user-select:none、樣式表有 -webkit-touch-callout:none（{us}）",
               all(us[k] == "none" for k in ("canvas", "num", "lead", "tab", "chain")) and us["callout"], us)
            # ---- 1. 點編號 → 抽屜 → 點背景關 → 子分頁、母分頁、側欄都點得動 ----
            s1 = tapnum()
            ok(f"【{T}】{W} 點 3D 編號開底部抽屜（{s1['sheet']}）", s1["sheet"] and s1["scrim"], s1)
            if SHOT:
                m.screenshot(path=os.path.join(SHOT, f"m43dpop_{W}_1_sheet.png"))
            # 掛一段文字選取（模擬 iOS 長按選到字）→ 關抽屜時要清掉
            J("() => { const t = document.querySelector('#dgTitle'); if (t) { const r = document.createRange(); r.selectNodeContents(t); const s = getSelection(); s.removeAllRanges(); s.addRange(r); } }")
            # 點背景：抽屜正上方、分頁列下面的空白（不是分頁）
            bk = J("() => { const sh = document.getElementById('mSheet').getBoundingClientRect(); return [innerWidth / 2, Math.max(300, sh.top - 40)]; }")
            m.touchscreen.tap(*bk); m.wait_for_timeout(700)
            s2 = st()
            ok(f"【{T}】{W} 點背景：抽屜關、背景拿掉、沒有全頁遮罩殘留（{s2['big']}）、選取清掉（{s2['sel']}）",
               not s2["sheet"] and not s2["scrim"] and not s2["big"] and s2["sel"] == 0, s2)
            y0 = J("scrollY"); m.mouse.wheel(0, 300); m.wait_for_timeout(500); J("scrollBy(0, 200)"); m.wait_for_timeout(300)
            ok(f"【{T}】{W} 關抽屜後頁面捲得動（{y0} → {J('scrollY')}）、body 沒被鎖（{s2['bodyOv']}）", J("scrollY") > y0 and s2["bodyOv"] != "hidden", [y0, s2])
            J("() => { const r = document.querySelector('#dgPick').getBoundingClientRect(); scrollBy(0, r.top - 130); }"); m.wait_for_timeout(500)
            J("() => { const c = [...document.querySelectorAll('#dgPick .segchip')].find(x => /矽晶圓/.test(x.textContent)); if (c) c.scrollIntoView({ inline: 'center', block: 'nearest' }); }"); m.wait_for_timeout(400)
            tapq("txt:#dgPick .segchip|矽晶圓", 1500)
            ok(f"【{T}】{W} 關抽屜後點子分頁「矽晶圓」切得過去（{J('location.hash')}）", J("location.hash").endswith("/dg/silicon_wafer"), J("location.hash"))
            J("() => { const c = document.querySelector('#chainSwitch button[data-c=\"ai_server\"]'); if (c) { c.scrollIntoView({ inline: 'center', block: 'nearest' }); } }"); m.wait_for_timeout(400)
            tapq("#chainSwitch button[data-c='ai_server']", 2000)
            ok(f"【{T}】{W} 點母分頁「AI 伺服器」切得過去（{J('location.hash')}）", "ai_server" in J("location.hash"), J("location.hash"))
            tapq("#m4Burger", 700)
            ok(f"【{T}】{W} 點側欄漢堡鈕打得開導覽抽屜", st()["drawer"], st())
            J("() => window.TwM4 && TwM4.close()"); m.wait_for_timeout(300)
            # ---- 2. 不關抽屜，直接點上方子分頁（隔著背景）：抽屜關、分頁一下就切 ----
            open3d("foundry")
            s3 = tapnum()
            ok(f"【{T}】{W} 再開一次 3D 抽屜", s3["sheet"], s3)
            tapq("txt:#dgPick .segchip|HBM", 1500)
            s4 = st()
            ok(f"【{T}】{W} 抽屜開著直接點子分頁「HBM」：抽屜關掉、背景拿掉、一下就切過去（{s4['hash']}）",
               not s4["sheet"] and not s4["scrim"] and s4["hash"].endswith("/dg/hbm"), s4)
            if SHOT:
                m.screenshot(path=os.path.join(SHOT, f"m43dpop_{W}_2_tapthru.png"))
            # ---- 3. 模擬 iOS 把 click 吞掉（touchend 被 preventDefault＝瀏覽器不補發 click）：分頁保險絲要補上 ----
            J("() => document.addEventListener('touchend', e => e.preventDefault(), { once: true, passive: false, capture: true })")
            J("() => { const c = [...document.querySelectorAll('#dgPick .segchip')].find(x => /先進封裝/.test(x.textContent)); if (c) c.scrollIntoView({ inline: 'center', block: 'nearest' }); }"); m.wait_for_timeout(400)
            tapq("txt:#dgPick .segchip|先進封裝", 1500)
            ok(f"【{T}】{W} click 被吞掉時（iOS 灰一下沒切那種），分頁保險絲補上、照樣切到「先進封裝」（{J('location.hash')}）",
               J("location.hash").endswith("/dg/ai_adv_packaging"), J("location.hash"))
            # 正常點（click 有到）不准補第二次：點一次母分頁，保險絲計數應該是 0
            J("() => { const c = document.querySelector('#chainSwitch button[data-c=\"semiconductor\"]'); if (c) { delete c.dataset.m4tapfix; c.scrollIntoView({ inline: 'center', block: 'nearest' }); } }"); m.wait_for_timeout(300)
            tapq("#chainSwitch button[data-c='semiconductor']", 1200)
            fx = J("() => { const c = document.querySelector('#chainSwitch button[data-c=\"semiconductor\"]'); return c ? (c.dataset.m4tapfix || '0') : 'gone'; }")
            ok(f"【{T}】{W} 正常點分頁時保險絲不補第二下（補了 {fx} 次）", fx in ("0", "gone"), fx)
        finally:
            ctx.close()
    # 桌機：保險絲與點背景轉交都不作用（1440 沒有 #mSheetBack 可見、分頁 user-select 照舊）
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    try:
        pg.goto(base + "#industry/semiconductor/dg/foundry", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.querySelector('#dgPick .segchip')", 30000, 300)
        # 手機規則全部掛在 :root.m4 且 ≤640 底下；桌機沒有 m4 class、寬度 1440 → 物理上套不到（版面指紋另由 桌機守門1008 比對）
        u = pg.evaluate("() => ({ m4: document.documentElement.classList.contains('m4'), w: innerWidth, back: !!(document.getElementById('mSheetBack') && document.getElementById('mSheetBack').getClientRects().length) })")
        ok(f"【{T}】1440 桌機不是 html.m4、沒有抽屜背景（{u}）", not u["m4"] and u["w"] > 640 and not u["back"], u)
    finally:
        pg.close()


# ★ 2026-10-16 Andy iPhone：「產業地圖切換到3D圖之後 其他分頁不能使用」（360／390／430 觸控＋1440 守桌機；⚠ --workers 1）
register("手機3D分頁1016", lambda pg, b, base, code: t_m4_3dpop_1016(b, base), after="手機3D編號1010")
