# 驗收段落「科技透明圈客服鈕避讓1028」：手機 390 薪資組成圖例右側金額不被右下角客服鈕（#supFab）蓋住。flake8: noqa
def t_tc_fab(b, base, code):
    T = "科技透明圈客服鈕避讓1028"
    SP = "/tmp/claude-0/-home-user-tw-rotation/d35d4770-19c6-5ef0-b46f-3181b0b89ae3/scratchpad/"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
    n = pg.evaluate("() => document.querySelectorAll('#v-tc .tc-pay ul.tclg li').length")
    if not n:
        print(f"  ⏭ {T}：沒有薪資組成圖例，略過"); c.close(); return
    hit = []
    for i in range(n):
        # 每一列都捲到視窗底部（最容易被固定在右下的客服鈕壓到的位置）再量
        r = pg.evaluate("""(i) => { const li = document.querySelectorAll('#v-tc .tc-pay ul.tclg li')[i];
          li.scrollIntoView({block:'end'}); const f = document.getElementById('supFab'); if (!f) return null;
          const fr = f.getBoundingClientRect(), out = [];
          li.querySelectorAll('span,b,small').forEach(e => { const t = (e.innerText||'').trim(); if (!t) return; const rg = document.createRange(); rg.selectNodeContents(e); const q = rg.getBoundingClientRect();
            if (q.width && q.left < fr.right && q.right > fr.left && q.top < fr.bottom && q.bottom > fr.top) out.push(t + ':' + Math.round(q.left) + '-' + Math.round(q.right)); });
          return {fab: [fr.left, fr.top, fr.right, fr.bottom].map(Math.round), out}; }""", i)
        if r is None: print(f"  ⏭ {T}：沒有客服鈕"); c.close(); return
        pg.wait_for_timeout(80)
        if i == n - 1:
            try: pg.screenshot(path=SP + "fab_" + ("after" if "after" in SP_TAG else "before") + ".png")
            except Exception as e: print("  ⚠ 截圖失敗", e)
        if r["out"]: hit.append((i, r))
    ok(f"{T}：390 寬薪資組成每列圖例文字與客服鈕矩形不相交", not hit, hit[:2])
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])
    c.close()

SP_TAG = "after"
register("科技透明圈客服鈕避讓1028", lambda pg, b, base, code: t_tc_fab(b, base, code))
