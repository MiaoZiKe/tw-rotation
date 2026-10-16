# 驗收段落「ETF月配金額1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）：「ETF 功能 BUG 為何自訂點選沒任何反應，改成 自訂 後面是可以輸入金額／年領 切到 月領 再切到 年領 系統出問題，
#   確保 兩者都是有 金額 可以選擇 月領 就Default 1萬 2萬 5萬 10萬 自訂」
#   根因：抽屜的「金額」組讀的是 #incAmtSeg 後面的 select.m4segsel，drawInc 每次重寫 #incAmtBox 就把它砍掉 → 切年／月後整組消失；
#   「自訂…」只是去改那個 select 再收抽屜，期待頁面上的數字框露出來，但框藏在條件列（.m4dwhide）裡 → 看起來沒反應。
#   驗：360／390／430（is_mobile、has_touch；全部手指 tap，抽屜不關）——
#   ① 年→月→年→月 每一次「金額」組都在、選項對（年領 20／50／100／200 萬＋自訂；月領 1／2／5／10 萬＋自訂）、月領第一次＝1 萬
#   ② 點「自訂」→ 原地變成輸入框（inputmode=decimal、游標在裡面）→ 打 3、Enter → 摘要鈕寫「月領・3萬」、結論句寫「每月領 3.0 萬」
#   ③ 切年領 → 年領自己的 100 萬；再切月領 → 回到自訂 3（各記各的）④ 重新整理 → 單檔 ETF 分頁還是月領 3 萬（tw.etf.inc.pt.s.mon＝30000）
#   1440：桌機金額鈕照舊（年領 4 格、月領 5000／1萬／2萬／3萬＋旁邊數字框），沒有抽屜。
def t_etf_amt_1016(b, base):
    T = "ETF月配金額1016"
    SG = """() => { const g = document.querySelector('#m4EtfSegs .m4dwg[data-g="amt"]');
        return g ? [...g.querySelectorAll('.seg > *')].map(b => (b.dataset.v || '') + (b.classList.contains('on') ? '*' : '')).join(',') : null; }"""
    INFO = """() => ({ btn: ((document.getElementById('m4EtfSet-inc') || {}).textContent || '').replace(/\\s+/g, ''), sq: (document.getElementById('incSQ') || {}).textContent || '',
        pt: localStorage.getItem('tw.etf.inc.pt') || '' })"""
    INIT = "try{ if(!sessionStorage.getItem('ea16')){ localStorage.clear(); sessionStorage.setItem('ea16','1'); } localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}"
    Y = "200000,500000,1000000,2000000,custom"
    M = "10000,20000,50000,100000,custom"
    for W in (360, 390, 430):
        tag = f"【{T}】{W}"
        ctx = b.new_context(viewport={"width": W, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        try:
            ctx.add_init_script(INIT)
            m = ctx.new_page()
            m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
            m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            m.goto(base + "#etf/inc", wait_until="domcontentloaded")
            wait_until(m, "(() => { const b = document.getElementById('m4EtfSet-inc'); return !!(b && b.getClientRects().length); })()", 30000)
            m.wait_for_timeout(1200)
            m.locator("#m4EtfSet-inc").tap(); m.wait_for_timeout(600)

            def mode(v):
                m.locator(f"#m4EtfSegs button[data-g='mode'][data-v='{v}']").tap(); m.wait_for_timeout(700)
                return m.evaluate(SG)
            g0 = m.evaluate(SG)
            ok(f"{tag}①a：年領 → 金額組在、20／50／100／200 萬＋自訂、100 萬亮", g0 is not None and g0.replace("*", "") == Y and "1000000*" in g0, g0)
            seq = [("m", M), ("y", Y), ("m", M), ("y", Y), ("m", M)]
            got = [(v, mode(v)) for v, _ in seq]
            ok(f"{tag}①b：年→月→年→月 切五次，每一次金額組都在、選項跟著換", all(g is not None and g.replace("*", "") == w for (_, g), (_, w) in zip(got, seq)), got)
            ok(f"{tag}①c：月領第一次＝1 萬（沒記過月領金額）", "10000*" in (got[0][1] or ""), got[0])
            i0 = m.evaluate(INFO)
            m.locator("#m4EtfSegs button[data-g='amt'][data-v='custom']").tap(); m.wait_for_timeout(500)
            fi = m.evaluate("() => { const i = document.getElementById('m4AmtIn'); return i ? { f: document.activeElement === i, im: i.inputMode, vis: i.getClientRects().length > 0, fs: parseFloat(getComputedStyle(i).fontSize) } : null; }")
            ok(f"{tag}②a：點「自訂」→ 抽屜原地變成輸入框（inputmode=decimal、游標在裡面、字 ≥ 16px）", bool(fi) and fi["f"] and fi["im"] == "decimal" and fi["vis"] and fi["fs"] >= 16, fi)
            m.locator("#m4AmtIn").fill(""); m.keyboard.type("3"); m.keyboard.press("Enter"); m.wait_for_timeout(1500)
            i1 = m.evaluate(INFO)
            ok(f"{tag}②b：打 3、Enter → 摘要鈕「月領・3萬」、結論句「每月領 3.0 萬」（真的重算）", "月領・3萬" in i1["btn"] and "每月領 3.0 萬" in i1["sq"] and i1["sq"] != i0["sq"], {"前": i0, "後": i1})
            ok(f"{tag}②c：只記在單檔 ETF 分頁（pt.s.mon＝30000）、全域 tw.etf.inc.mon 沒寫", '"mon":30000' in i1["pt"] and m.evaluate("() => localStorage.getItem('tw.etf.inc.mon')") is None, i1["pt"])
            gy = mode("y"); iy = m.evaluate(INFO)
            ok(f"{tag}③a：切年領 → 年領自己的 100 萬（金額組在）", gy is not None and "1000000*" in gy and "年領・100萬" in iy["btn"], (gy, iy["btn"]))
            gm = mode("m"); im_ = m.evaluate(INFO)
            inv = m.evaluate("() => (document.getElementById('m4AmtIn') || {}).value")
            ok(f"{tag}③b：再切月領 → 回到自訂 3 萬（輸入框裡是 3）", gm is not None and gm.endswith("custom*") and inv == "3" and "月領・3萬" in im_["btn"], (gm, inv, im_["btn"]))
            sw = m.evaluate("() => { const s = document.querySelector('#m4EtfSegs .m4dwg[data-g=\"amt\"] .seg'), c = document.querySelector('#m4EtfSegs .m4amtc'); const a = s.getBoundingClientRect(), r = c.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right), Math.round(a.left), Math.round(a.right)]; }")
            ok(f"{tag}③c：自訂輸入框整格在金額列可視範圍內", sw[0] >= sw[2] - 1 and sw[1] <= sw[3] + 1, sw)
            m.keyboard.press("Escape"); m.wait_for_timeout(300)
            m.reload(wait_until="domcontentloaded")
            wait_until(m, "(() => { const b = document.getElementById('m4EtfSet-inc'); return !!(b && b.getClientRects().length); })()", 30000); m.wait_for_timeout(1200)
            i2 = m.evaluate(INFO)
            ok(f"{tag}④：重新整理 → 單檔 ETF 還是月領 3 萬、結論句照 3 萬算", "月領・3萬" in i2["btn"] and "每月領 3.0 萬" in i2["sq"], i2)
            x = m.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
            ok(f"{tag}：整頁不橫捲 {x}", x[0] <= x[1], x)
        finally:
            ctx.close()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    try:
        ctx.add_init_script(INIT)
        m = ctx.new_page()
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(base + "#etf/inc", wait_until="domcontentloaded")
        wait_until(m, "(() => !!document.querySelector('#incAmtSeg button'))()", 30000); m.wait_for_timeout(800)
        y = m.evaluate("() => [...document.querySelectorAll('#incAmtSeg button')].map(b => b.dataset.v).join(',')")
        m.click("#incMode button[data-v='m']"); m.wait_for_timeout(600)
        mm = m.evaluate("() => [[...document.querySelectorAll('#incAmtSeg button')].map(b => b.dataset.v).join(','), !!document.getElementById('incAmt').getClientRects().length, document.querySelectorAll('.m4etfrow').length]")
        ok(f"【{T}】1440：桌機金額鈕照舊（年領 4 格；月領 5000／1萬／2萬／3萬＋數字框）、沒有抽屜鈕",
           y == "200000,500000,1000000,2000000" and mm[0] == "5000,10000,20000,30000" and mm[1] and mm[2] == 0, (y, mm))
    finally:
        ctx.close()


# ★ 2026-10-16 Andy（iPhone）：「ETF 功能 BUG 為何自訂點選沒任何反應…年領 切到 月領 再切到 年領 系統出問題」—— 360／390／430 抽屜裡年月切五次金額組都在、自訂原地輸入 3 重算、各記各的、重整記住；1440 不變
register("ETF月配金額1016", lambda pg, b, base, code: t_etf_amt_1016(b, base), before="手機播放列360")
