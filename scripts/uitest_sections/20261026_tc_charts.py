# 驗收段落「科技透明圈圖表1026」：樣本統計圖表化＋LOGO。flake8: noqa
def t_tc_charts_1026(b, base, code):
    T = "科技透明圈圖表1026"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#tc/stats", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    ch = lambda i: pg.evaluate("(i)=>{const e=document.getElementById(i);const c=e&&echarts.getInstanceByDom(e);if(!c)return 0;const s=c.getOption().series;return (s[0].data||[]).length}", i)
    nb = ch("tcChBase")
    if not nb:
        print(f"  ⏭ {T}：沒有樣本，略過"); c.close(); return
    ok(f"{T}：底薪／年薪／筆數三張圖都畫出", nb >= 1 and ch("tcChAnn") >= 1 and ch("tcChN") >= 1, (nb, ch("tcChAnn"), ch("tcChN")))
    ok(f"{T}：圖有高度、不橫向捲動", pg.evaluate("()=>document.getElementById('tcChBase').offsetHeight>100 && document.documentElement.scrollWidth<=innerWidth+1"))
    rows = lambda: pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-rkr')].map(r=>r.dataset.co+'|'+r.querySelector('.tc-rkv b').innerText)")
    r0 = rows()
    ok(f"{T}：公司排行有列，每列有 LOGO 圖或字標", len(r0) >= 1 and pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-rkr')].every(r=>r.querySelector('.tc-lg i').innerText.trim()&&r.querySelector('.tc-lg'))"), len(r0))
    ok(f"{T}：有網域的列 img 帶 alt／lazy／no-referrer", pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-lg img')].every(i=>i.alt&&i.loading==='lazy'&&i.referrerPolicy==='no-referrer')"))
    pg.click("#tcRank .seg[data-rk=m] button[data-v=base]"); pg.wait_for_timeout(300)
    r1 = rows()
    ok(f"{T}：切「底薪」→ 排行數字真的變", r1 != r0 and pg.evaluate("()=>document.querySelector('#tcRank .seg[data-rk=m] button.on').dataset.v")=="base", (r0[:2], r1[:2]))
    btns = pg.evaluate("()=>[...document.querySelectorAll('#tcRank .seg[data-rk=ind] button')].map(b=>b.dataset.v)")
    if len(btns) > 2:
        pg.click(f"#tcRank .seg[data-rk=ind] button[data-v='{btns[1]}']"); pg.wait_for_timeout(300)
        ok(f"{T}：篩產業 → 列數變且都屬該產業", len(rows()) <= len(r1) and pg.evaluate("(v)=>[...document.querySelectorAll('#tcRank .tc-rkr')].every(r=>r.getAttribute('href').startsWith('#tc/'+v+'/'))", btns[1]), len(rows()))
    ok(f"{T}：文字數字明細保留（收合在圖下）", pg.evaluate("()=>!!document.querySelector('#v-tc details.tc-raw .tc-st')"))
    pg.click("#tcRank .tc-rkr >> nth=0"); pg.wait_for_timeout(700)
    ok(f"{T}：點排行一列 → 進公司頁、標題旁有 LOGO", "#tc/" in pg.url and pg.url.count("/") >= 1 and pg.evaluate("()=>!!document.querySelector('#v-tc .tc-cinfo h4 .tc-lg')"), pg.url)
    pg.goto(base + "#tc/foundry", wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    ok(f"{T}：公司卡有 LOGO", pg.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-co')].every(c=>c.querySelector('.tc-lg'))"))
    # 圖片全擋 → 退成字標
    pg.route("**/s2/favicons**", lambda r: r.abort())
    pg.goto(base + "#tc/foundry", wait_until="domcontentloaded"); pg.reload(wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
    ok(f"{T}：LOGO 載入失敗 → 圖被移除、字標仍在", pg.evaluate("()=>document.querySelectorAll('#v-tc .tc-lg img').length===0 && [...document.querySelectorAll('#v-tc .tc-lg')].every(l=>l.querySelector('i').innerText.trim())"))
    c.close()
    m = b.new_context(viewport={"width": 390, "height": 844}); m.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    mp = m.new_page(); mp.goto(base + "#tc/stats", wait_until="domcontentloaded"); mp.wait_for_timeout(2500)
    ok(f"{T}：手機 390 不橫向捲動、排行列存在", mp.evaluate("()=>document.documentElement.scrollWidth<=innerWidth+1 && document.querySelectorAll('#tcRank .tc-rkr').length>0"))
    m.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])

register("科技透明圈圖表1026", lambda pg, b, base, code: t_tc_charts_1026(b, base, code))
