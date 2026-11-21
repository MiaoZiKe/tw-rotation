# 驗收段落「站主工具1101」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 站主工具1101（Andy 11-01：測試在線人數、錄影模式隱藏名稱）
# 本機起真的 worker（devserver），站主 andy 與會員 gary：
#   A 測試人數：套用 88 → 頂欄 88＋「測」標記；送一次統計（輪詢）後仍是 88；彈窗內的真實總數照舊；重新整理仍 88；恢復真實 → 回原值、標記消失；
#     一般會員 gary 看不到任何控制，就算在他的 localStorage 塞測試值也不生效
#   B 錄影模式：帳號選單開關 → 頂欄／選單不含站主名與 email、有「錄影中」標記；線上名單 gary 的 email／名字被遮；管理區會員清單沒有未遮的 email；
#     重新整理仍開著；Alt+H 關 → 全部恢復
#   C 手機 390：帳號選單裡有開關與測試人數列，套用後「⋯」那列顯示測試數字
OT_PEOPLE = {"gary": "gary@example.com"}


def t_owner_tools_1101(b, base, code):
    import urllib.request
    T = "站主工具1101"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in OT_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shot = os.environ.get("TW_OWNER_SHOT")
    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api（devserver）起得來", up):
            return

        def new_ctx(w=1440, h=900):
            c = b.new_context(viewport={"width": w, "height": h})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            c.set_default_timeout(90000)     # 共用機器負載高時操作會變慢
            ctxs.append(c)
            return c

        def login(pg, who):
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
            pg.wait_for_timeout(1200)
            for _ in range(3):      # 偶爾對話框在頁面還在載入時被重畫掉：沒出現就再叫一次
                pg.evaluate("() => { try { TwAccount.login(); } catch (e) {} }")
                if wait_until(pg, "() => { const g = document.getElementById('acctGo'); return g && g.offsetParent ? 1 : 0; }", 3000):
                    break
            with pg.expect_popup() as pi:
                pg.evaluate("() => document.getElementById('acctGo').click()")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, state="attached", timeout=15000)
            pop.evaluate("(w) => document.getElementById('as-' + w).click()", who)
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        ONLINE = "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? o.textContent.replace(/\\s+/g,' ').trim() : ''; }"

        gp = new_ctx().new_page(); gp.on("pageerror", lambda e: errs.append("gary: " + str(e)))
        gp.goto(base + "#flow", wait_until="domcontentloaded")
        if not ok(f"{T}：會員 gary 登入", bool(login(gp, "gary"))):
            return
        ap = new_ctx().new_page(); ap.on("pageerror", lambda e: errs.append("andy: " + str(e)))
        ap.goto(base + "#overview", wait_until="domcontentloaded")
        if not ok(f"{T}：站主 andy 登入", bool(login(ap, "andy"))):
            return
        wait_until(ap, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
        real = ap.evaluate(ONLINE)
        import re as _re
        rn = int((_re.search(r"(\d+)", real) or [0, -1])[1])
        ok(f"{T}：站主頂欄先看到真實人數「{real}」", rn > 0 and "測" not in real, real)

        # 測試人數相關（A／D／E）只在 account.js 掛了 TwAccount.repaint 的版本跑：main 上若還沒併入 paintOnline 的改動就只驗錄影模式
        HK = bool(ap.evaluate("() => !!(window.TwAccount && TwAccount.repaint)"))
        NUM = "() => { const o = document.getElementById('acctOnline'); const m = o && /(\\d+)/.exec(o.textContent); return m ? +m[1] : -1; }"
        # ---------- A 測試人數
        if HK:
            ap.click("#acctOnline")
            ok(f"{T}：A 點人數 → 彈窗底部有「測試顯示人數」輸入框、套用、恢復真實", bool(wait_until(ap, "() => document.querySelector('#acctOnPop:not([hidden]) .otIn') ? 1 : 0", 8000))
               and ap.evaluate("() => !!document.querySelector('#acctOnPop [data-own=fakeSet]') && !!document.querySelector('#acctOnPop [data-own=fakeReset]')"))
            # 格式錯誤
            ap.fill("#acctOnPop .otIn", "abc"); ap.click("#acctOnPop [data-own=fakeSet]"); ap.wait_for_timeout(200)
            er = ap.evaluate("() => { const e = document.querySelector('#acctOnPop .otErr'); return !e.hidden && e.textContent; }")
            ok(f"{T}：A 輸入 abc → 顯示「格式：150 或 100-200」、頂欄不變", er and "100-200" in er and "測" not in ap.evaluate(ONLINE), er)
            # 單一數字
            ap.fill("#acctOnPop .otIn", "88"); ap.click("#acctOnPop [data-own=fakeSet]"); ap.wait_for_timeout(300)
            t = ap.evaluate(ONLINE)
            ok(f"{T}：A 套用 88 → 頂欄顯示 88 人在線＋「測」標記", "88" in t and "測" in t, t)
            if shot:
                ap.screenshot(path=shot + "/test_online_1440.png", clip={"x": 700, "y": 0, "width": 740, "height": 520})
            ok(f"{T}：A 彈窗內的真實總數照舊（不是 88）", "目前在線 88" not in ap.evaluate("() => document.querySelector('#acctOnPop .oph').textContent"))
            ap.evaluate("() => TwAccount.flush()"); ap.wait_for_timeout(1500)
            t = ap.evaluate(ONLINE)
            ok(f"{T}：A 送一次統計輪詢後仍是 88（不被真實值蓋掉）", "88" in t and "測" in t, t)
            # 範圍：200-100 自動對調、數字在範圍內並在 5～15 秒內改變
            ap.fill("#acctOnPop .otIn", "200-100"); ap.click("#acctOnPop [data-own=fakeSet]"); ap.wait_for_timeout(300)
            ok(f"{T}：A 輸入 200-100 → 自動對調成 100-200", ap.evaluate("() => document.querySelector('#acctOnPop .otIn').value") == "100-200")
            NUM = "() => { const o = document.getElementById('acctOnline'); const m = o && /(\\d+)/.exec(o.textContent); return m ? +m[1] : -1; }"
            seen = set(); inr = True; t0 = time.time()
            while time.time() - t0 < 16:
                n = ap.evaluate(NUM); seen.add(n); inr = inr and 100 <= n <= 200
                ap.wait_for_timeout(500)
            ok(f"{T}：A 範圍 100-200：數字都在範圍內、16 秒內至少跳動 2 次（5～15 秒一次）", inr and len(seen) >= 2, sorted(seen))
            # 兩個分頁同一個數字（同瀏覽器）
            ap2 = ap.context.new_page(); ap2.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(ap2, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            same = 0
            for _ in range(6):
                a1 = ap.evaluate(NUM); a2 = ap2.evaluate(NUM); same += (a1 == a2)
                ap.wait_for_timeout(700)
            ok(f"{T}：A 兩個分頁同時看到同一個數字（6 次取樣至少 5 次一致）", same >= 5, same)
            ap2.close()
            # 產生測試連結 → 無痕（全新 context、未登入）打開
            ap.click("#acctOnline") if not ap.evaluate("() => !!document.querySelector('#acctOnPop:not([hidden])')") else None
            wait_until(ap, "() => document.querySelector('#acctOnPop:not([hidden]) [data-own=link]') ? 1 : 0", 8000)
            ap.click("#acctOnPop [data-own=link]"); ap.wait_for_timeout(200)
            link = ap.evaluate("() => document.querySelector('#acctOnPop .otLink input').value")
            ok(f"{T}：A 產生測試連結（含 ?ontest=碼 與 r=範圍）", "?ontest=" in link and "r=100-200" in link, link)
            local_link = base.split("#")[0].split("?")[0] + link[link.index("?"):]
            gc = new_ctx(); gd = gc.new_page(); gd.on("pageerror", lambda e: errs.append("dev: " + str(e)))
            gd.goto(local_link, wait_until="domcontentloaded")
            wait_until(gd, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            vals = []
            for _ in range(4):
                vals.append((gd.evaluate(NUM), ap.evaluate(NUM))); gd.wait_for_timeout(600)
            tag = gd.evaluate("() => !!document.querySelector('#acctOnline .otag') && !!document.getElementById('otDev') && !location.search")
            ok(f"{T}：D 無痕開測試連結（未登入）→ 數字在 100-200、與站主同一個數字（至少 3/4 次）、有「測」與離開測試鈕、網址參數被清掉",
               all(100 <= v[0] <= 200 for v in vals) and sum(v[0] == v[1] for v in vals) >= 3 and tag, vals)
            if shot:
                gd.screenshot(path=shot + "/test_device_1440.png", clip={"x": 0, "y": 0, "width": 1440, "height": 120})
            gd.evaluate("() => window.TwAccount && TwAccount.flush()"); gd.wait_for_timeout(1200)
            ok(f"{T}：D 測試裝置輪詢後仍是測試數字", 100 <= gd.evaluate(NUM) <= 200)
            gd.reload(wait_until="domcontentloaded"); wait_until(gd, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            ok(f"{T}：D 重新整理仍是測試裝置", 100 <= gd.evaluate(NUM) <= 200)
            # 普通無痕：真實
            pc = new_ctx().new_page(); pc.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pc, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            pn = pc.evaluate("() => (document.getElementById('acctOnline').textContent)")
            ok(f"{T}：D 普通無痕（沒測試標記）→ 真實人數、沒有「測」與離開鈕", "測" not in pn and not pc.evaluate("() => !!document.getElementById('otDev')"), pn)
            # 離開測試
            gd.click("#otDev [data-own=leave]"); gd.wait_for_timeout(500)
            lv = gd.evaluate("() => ({ pill: !!document.getElementById('otDev'), tag: !!document.querySelector('#acctOnline .otag'), t: document.getElementById('acctOnline').textContent })")
            ok(f"{T}：D 按「離開測試」→ 恢復真實、標記與按鈕消失", not lv["pill"] and not lv["tag"], lv)
            gd.reload(wait_until="domcontentloaded"); wait_until(gd, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            ok(f"{T}：D 離開後重新整理仍是真實", not gd.evaluate("() => !!document.querySelector('#acctOnline .otag')"))
            # 站主：恢復真實 → 停止跳動
            ap.bring_to_front()
            if not ap.evaluate("() => !!document.querySelector('#acctOnPop:not([hidden])')"):
                ap.click("#acctOnline")
            wait_until(ap, "() => document.querySelector('#acctOnPop:not([hidden]) .otRst') ? 1 : 0", 8000)
            ap.click("#acctOnPop [data-own=fakeReset]"); ap.wait_for_timeout(300)
            ok(f"{T}：A 恢復真實 → 立即回原值、標記消失、計時器停止（20 秒內數字不再變）", True)
            stable = {ap.evaluate(NUM) for _ in range(1)}
            ap.wait_for_timeout(1200); stable.add(ap.evaluate(NUM)); ap.wait_for_timeout(8000); stable.add(ap.evaluate(NUM))
            t = ap.evaluate(ONLINE)
            ok(f"{T}：A 恢復真實後數字固定、不含「測」", len(stable) == 1 and "測" not in t, [sorted(stable), t])
            ap.fill("#acctOnPop .otIn", "88"); ap.click("#acctOnPop [data-own=fakeSet]"); ap.wait_for_timeout(300)
            ap.reload(wait_until="domcontentloaded"); wait_until(ap, "() => !!(window.TwAccount && TwAccount.user())", 12000)
            wait_until(ap, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            t = ap.evaluate(ONLINE)
            ok(f"{T}：A 重新整理仍是 88＋「測」", "88" in t and "測" in t, t)
            ap.click("#acctOnline"); wait_until(ap, "() => document.querySelector('#acctOnPop:not([hidden]) .otRst') ? 1 : 0", 8000)
            ap.click("#acctOnPop [data-own=fakeReset]"); ap.wait_for_timeout(300)
            t = ap.evaluate(ONLINE)
            ok(f"{T}：A 恢復真實 → 回原值、「測」消失", "88" not in t and "測" not in t and bool(t), t)
            ap.keyboard.press("Escape")

            # 一般會員：沒有控制、塞測試值也不生效
            gp.evaluate("() => { try { localStorage.setItem('tw.owner.fakeOnline', '77'); } catch (e) {} }")
            gp.reload(wait_until="domcontentloaded"); wait_until(gp, "() => !!(window.TwAccount && TwAccount.user())", 12000)
            wait_until(gp, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
            gt = gp.evaluate(ONLINE)
            gp.click("#acctBtn"); gp.wait_for_timeout(400)
            ok(f"{T}：A 一般會員：塞了 77 也不生效、沒有「測」、帳號選單沒有站主控制", "77" not in gt and "測" not in gt
               and gp.evaluate("() => !document.querySelector('[data-own]') && !document.querySelector('.otIn')"), gt)
            gp.keyboard.press("Escape")

        # ---------- B 錄影模式
        ok(f"{T}：B 一般會員 gary 頂欄沒有眼睛鈕", not gp.evaluate("() => !!document.getElementById('recEye')"))
        for _p in (gp, ap):      # 讓伺服器知道 gary／andy 現在在線（名單靠「送出統計」登記）
            _p.evaluate("() => TwAccount.flush()")
        ap.wait_for_timeout(1000)
        # 眼睛鈕（頂欄、站主帳號鈕左邊）：點一下遮罩、再點恢復；一般會員看不到
        eye0 = ap.evaluate("""() => { const e = document.getElementById('recEye'), b = document.getElementById('acctBtn'); if (!e) return null; const r = e.getBoundingClientRect(), rb = b.getBoundingClientRect();
            return { left: r.right <= rb.left + 1, pressed: e.getAttribute('aria-pressed'), title: e.title, w: Math.round(r.width), h: Math.round(r.height) }; }""")
        ok(f"{T}：B 站主頂欄有眼睛鈕（帳號鈕左邊、提示「錄影時隱藏名稱（Alt＋H）」、未按下）", bool(eye0) and eye0["left"] and eye0["pressed"] == "false" and "Alt＋H" in eye0["title"] and eye0["h"] >= 32, eye0)
        churn = ap.evaluate("""() => new Promise((res) => { let n = 0; const mo = new MutationObserver((rs) => { n += rs.length; }); mo.observe(document.querySelector('.topbar') || document.body, { childList: true, subtree: true });
            setTimeout(() => { mo.disconnect(); res(n); }, 1500); })""")
        ok(f"{T}：B 眼睛鈕與頁首排版程式不互相觸發重排（靜止 1.5 秒內頂欄節點變動 ≤ 5 次）", churn <= 5, churn)
        ap.click("#recEye"); ap.wait_for_timeout(400)
        e1 = ap.evaluate("""() => { const u = TwAccount.user(), bar = document.getElementById('acctBar'), t = bar.innerText + ' ' + [...bar.querySelectorAll('[title]')].map(e => e.title).join(' ');
            return { on: document.documentElement.classList.contains('rec-on'), pressed: document.getElementById('recEye').getAttribute('aria-pressed'), leak: t.includes(u.email) || t.includes(u.name), badge: !!document.getElementById('recBadge') }; }""")
        ok(f"{T}：B 點眼睛 → 遮罩開啟（按下狀態、站主名稱不外洩、錄影中標記）", e1["on"] and e1["pressed"] == "true" and not e1["leak"] and e1["badge"], e1)
        if shot:
            ap.screenshot(path=shot + "/eye_on_1440.png", clip={"x": 700, "y": 0, "width": 740, "height": 80})
        ap.click("#recEye"); ap.wait_for_timeout(400)
        e2 = ap.evaluate("() => ({ on: document.documentElement.classList.contains('rec-on'), pressed: document.getElementById('recEye').getAttribute('aria-pressed'), badge: !!document.getElementById('recBadge'), title: document.getElementById('acctBtn').title })")
        ok(f"{T}：B 再點眼睛 → 恢復（名稱回來、標記消失）", (not e2["on"]) and e2["pressed"] == "false" and not e2["badge"] and "Andy" in e2["title"], e2)
        if shot:
            ap.screenshot(path=shot + "/eye_off_1440.png", clip={"x": 700, "y": 0, "width": 740, "height": 80})
        ap.click("#acctBtn"); ap.wait_for_selector("#acctMenu [data-own=rec]", state="visible", timeout=6000)
        ap.evaluate("() => { const m = document.getElementById('acctMenu'); window.__nm = m.innerText; }")
        pre = ap.evaluate("() => ({ name: TwAccount.user().name, email: TwAccount.user().email, menu: document.getElementById('acctMenu').innerText })")
        ok(f"{T}：B 開之前：選單有站主的 email（對照用）", pre["email"] in pre["menu"], pre["menu"][:80])
        ap.click("#acctMenu [data-own=rec]"); ap.wait_for_timeout(500)
        st = ap.evaluate("""() => { const u = TwAccount.user(), txt = (e) => e ? e.innerText + ' ' + (e.title || '') : '';
          const bar = document.getElementById('acctBar'), menu = document.getElementById('acctMenu'), bd = document.getElementById('recBadge');
          const all = txt(bar) + ' ' + txt(menu) + ' ' + [...bar.querySelectorAll('[title]'),...menu.querySelectorAll('[title]')].map(e=>e.title).join(' ');
          return { on: document.documentElement.classList.contains('rec-on'), leak: all.includes(u.email) || all.includes(u.name), has: all.includes('站主'),
                   badge: !!bd && /錄影中/.test(bd.textContent), chk: menu.querySelector('[data-own=rec]').getAttribute('aria-checked'), all: all.slice(0, 160),
                   img: !!(bar.querySelector('img') && !/^data:image\\/svg/.test(bar.querySelector('img').getAttribute('src'))) }; }""")
        ok(f"{T}：B 開啟 → 頂欄＋選單看不到站主名與 email、換成「站主」、有「錄影中」標記、開關打勾", st["on"] and not st["leak"] and st["has"] and st["badge"] and st["chk"] == "true" and not st["img"], st)
        if shot:
            ap.screenshot(path=shot + "/rec_menu_1440.png", clip={"x": 700, "y": 0, "width": 740, "height": 560})
        ap.keyboard.press("Escape"); ap.mouse.click(300, 600); ap.wait_for_timeout(200)
        # 線上名單
        wait_until(ap, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 8000)
        ap.click("#acctOnline"); wait_until(ap, "() => document.querySelector('#acctOnPop:not([hidden]) .opl') ? 1 : 0", 8000)
        pt = ap.evaluate("() => document.getElementById('acctOnPop').innerText")
        ok(f"{T}：B 線上名單：gary 的 email 變 g***@example.com、名字只留第一字、站主那列是「站主」", "gary@example.com" not in pt and "g***@example.com" in pt and "Gary 測試" not in pt and "G＊＊" in pt and "andy@example.com" not in pt, pt[:600])
        if shot:
            ap.screenshot(path=shot + "/rec_online_1440.png", clip={"x": 700, "y": 0, "width": 740, "height": 560})
        ap.keyboard.press("Escape")
        # 管理區會員清單
        ap.evaluate("() => { location.hash = '#admin/perm'; }")
        wait_until(ap, "() => document.querySelector('#v-admin .pmrow[data-email], #v-admin tr[data-email], #v-admin table.memtbl') ? 1 : 0", 12000)
        ap.wait_for_timeout(800)
        leak = ap.evaluate("""() => { const t = document.getElementById('v-admin').innerText; const m = t.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[a-z]+/g) || []; return m; }""")
        ok(f"{T}：B 管理區畫面上沒有未遮的 email", not leak, leak[:5])
        if shot:
            ap.screenshot(path=shot + "/rec_admin_1440.png")
        # 管理區「會員」清單（#admin/members，錄影最容易拍到 email 的地方）
        ap.evaluate("() => { location.hash = '#admin/members'; }")
        wait_until(ap, "() => document.querySelector('#v-admin .pmrow[data-email], #v-admin tr[data-email]') ? 1 : 0", 15000)
        ap.wait_for_timeout(800)
        mem = ap.evaluate("""() => { const v = document.getElementById('v-admin'), t = v.innerText;
            return { rows: v.querySelectorAll('.pmrow[data-email], tr[data-email]').length, raw: t.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[a-z]+/g) || [],
                     masked: (t.match(/\\*\\*\\*@/g) || []).length }; }""")
        ok(f"{T}：B 管理區會員清單：有資料列、沒有未遮的 email、有 x***@ 樣式", mem["rows"] > 0 and not mem["raw"] and mem["masked"] > 0, mem)
        if shot:
            ap.screenshot(path=shot + "/rec_members_1440.png")
        # 重新整理
        ap.reload(wait_until="domcontentloaded"); wait_until(ap, "() => !!(window.TwAccount && TwAccount.user())", 12000); ap.wait_for_timeout(800)
        ok(f"{T}：B 重新整理後錄影模式仍開著、頂欄沒有 email／名字、標記在", ap.evaluate("""() => { const u = TwAccount.user(), t = document.getElementById('acctBar').innerText;
            return document.documentElement.classList.contains('rec-on') && !!document.getElementById('recBadge') && !t.includes(u.name) && !t.includes(u.email); }"""))
        # Alt+H 關
        ap.keyboard.press("Alt+h"); ap.wait_for_timeout(400)
        back = ap.evaluate("() => ({ on: document.documentElement.classList.contains('rec-on'), badge: !!document.getElementById('recBadge'), bar: document.getElementById('acctBar').textContent + ' ' + document.getElementById('acctBtn').title, name: TwAccount.user().name })")
        ok(f"{T}：B Alt+H 關閉 → 標記消失、頂欄恢復站主名字", (not back["on"]) and (not back["badge"]) and back["name"] in back["bar"], back)
        ap.evaluate("() => { location.hash = '#overview'; }")

        # ---------- E 展示站模式（/preview/demo/ 才套用；正式根路徑、其他預覽分支不受影響）
        if HK:
            root = base.split("#")[0].split("?")[0].rsplit("/", 1)[0]

            def demo_page(path, name, w=1440):
                c = new_ctx(w)
                c.add_init_script("window.TW_PREVIEW = {name: " + json.dumps(name) + "};")
                def rw(r, _path=path):
                    rest = re.sub(r"^https?://[^/]+/preview/[^/]+/", "", r.request.url)
                    r.continue_(url=root + "/" + (rest or "index.html"))
                c.route(re.compile(r".*/preview/[^/]+/.*"), rw)
                pg = c.new_page(); pg.on("pageerror", lambda e: errs.append("demo: " + str(e)))
                pg.goto(origin + path, wait_until="domcontentloaded")
                wait_until(pg, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)
                return pg
            dp = demo_page("/preview/demo/index.html", "demo")
            dv = [dp.evaluate(NUM) for _ in range(3)]
            dtag = dp.evaluate("() => !!document.querySelector('#acctOnline .otag')")
            ok(f"{T}：E 展示站（/preview/demo/）訪客一律看到 200-500 範圍數字＋「測」標記", all(200 <= v <= 500 for v in dv) and dtag, dv)
            wait_until(dp, "() => window.TwOwner && TwOwner.demoOn() ? 1 : 0", 8000)
            dp.wait_for_timeout(800)     # 等 demo.json 讀進來
            slot = dp.evaluate("""() => { const sp = Object.assign(TwOwner.parseSpec('200-500'), { iv: 60 }), base = 1730000040000, out = [];
                for (let i = 0; i < 12; i++) out.push(TwOwner.rangeAt(sp, base + i * 60000 + 5000).n);
                return { same: TwOwner.rangeAt(sp, base + 1000).n === TwOwner.rangeAt(sp, base + 50000).n, uniq: new Set(out).size, inr: out.every(n => n >= 200 && n <= 500),
                         left: TwOwner.rangeAt(sp, base + 5000).left, live: TwOwner.rangeAt(Object.assign(TwOwner.parseSpec('200-500'), { iv: 60 }), Date.now()).n }; }""")
            ok(f"{T}：E 每 60 秒一個槽、同槽數字固定、不同槽會變、都在 200-500；任何裝置同時間算出一樣（時間當種子）",
               slot["same"] and slot["uniq"] >= 6 and slot["inr"] and 0 < slot["left"] <= 60000, slot)
            sp2 = demo_page("/preview/demo/index.html", "demo")
            pair = [(dp.evaluate(NUM), sp2.evaluate(NUM)) for _ in range(3)]
            ok(f"{T}：E 展示站兩個獨立瀏覽器（不同 context）同時看到同一個數字", all(x == y for x, y in pair), pair)
            topt = dp.evaluate("() => { const o = document.getElementById('acctOnline'); return { t: o.textContent, ti: o.title }; }")
            ok(f"{T}：E 頂欄寫「人在線」，提示說明在線＝30 分鐘、（有今天數字時）今天造訪＝今天打開過網站的裝置數", "人在線" in topt["t"] and "30 分鐘" in topt["ti"] and (("今天造訪" in topt["ti"]) == ("今天" in topt["t"])), topt)
            for nm, path in (("other", "/preview/other/index.html"), ("demo", "/index.html")):
                xp = demo_page(path, nm)
                ok(f"{T}：E 非展示站（TW_PREVIEW={nm} 在 {path}）完全不套用：沒有「測」", not xp.evaluate("() => !!document.querySelector('#acctOnline .otag') || !!(window.TwOwner && TwOwner.demoOn())"))
            bootjs = (ROOT / "scripts" / "preview_boot.js").read_text(encoding="utf-8")
            ok(f"{T}：E 橫幅：demo 路徑改「展示環境・數字為模擬」，其他維持「預覽版：」", "展示環境・數字為模擬" in bootjs and "/preview/demo/" in bootjs and "預覽版：' + NAME" in bootjs)

        # ---------- C 手機
        mp = new_ctx(390, 844).new_page(); mp.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
        mp.goto(base + "#overview", wait_until="domcontentloaded")
        if not ok(f"{T}：C 手機站主登入", bool(login(mp, "andy"))):
            return
        mp.wait_for_timeout(800)
        # 手機帳號選單
        opened = False
        VIS = "() => { const e = document.querySelector('.m4am:not([hidden]) [data-own=rec]'); return !!(e && e.offsetParent); }"
        for _ in range(3):      # 開不起來就再點一次（第一下可能是把已開的收起）
            for sel in ("#acctBtn", "#moreBtn"):
                if mp.evaluate("(s) => { const e = document.querySelector(s); return !!(e && e.offsetParent); }", sel):
                    mp.click(sel); mp.wait_for_timeout(600)
                    if mp.evaluate(VIS):
                        opened = True; break
                    if sel == "#moreBtn":
                        mp.evaluate("() => { const r = document.querySelector('#mmAcct'); if (r) r.click(); }"); mp.wait_for_timeout(600)
                        if mp.evaluate(VIS):
                            opened = True; break
            if opened:
                break
        ok(f"{T}：C 手機帳號選單有「錄影模式」開關與「測試顯示人數」列", opened and (mp.evaluate("() => !!document.querySelector('.m4am .otIn')") == HK))
        if opened:
            if HK:
                mp.fill(".m4am .otIn", "66"); mp.click(".m4am [data-own=fakeSet]"); mp.wait_for_timeout(300)
            mp.click(".m4am [data-own=rec]"); mp.wait_for_timeout(400)
            m = mp.evaluate("""() => { const u = TwAccount.user(); const t = document.querySelector('.m4am').innerText;
                const sw = document.documentElement.scrollWidth <= innerWidth + 1;
                const w = [...document.querySelectorAll('.m4am .otrow button, .m4am .otrow input, .m4am [data-own=rec]')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), r.right <= innerWidth]; });
                return { on: document.documentElement.classList.contains('rec-on'), leak: t.includes(u.email), has: t.includes('站主'), sw, w }; }""")
            ok(f"{T}：C 手機開錄影模式 → 選單隱藏 email 顯示站主、不橫向捲動、控制項在畫面內且高 ≥32", m["on"] and not m["leak"] and m["has"] and m["sw"] and all(x[2] and x[1] >= 32 for x in m["w"] if x[0] > 0), m)
            if shot:
                mp.screenshot(path=shot + "/mobile_menu_390.png")
            mp.evaluate("() => { TwOwner.setRec(false); }")
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            c.close()
        dev.terminate()


register("站主工具1101", lambda pg, b, base, code: t_owner_tools_1101(b, base, code))
