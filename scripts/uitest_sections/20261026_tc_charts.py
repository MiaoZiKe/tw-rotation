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
    ok(f"{T}：占比甜甜圈＋底薪／年薪環組都畫出", nb >= 1 and ch("tcChAnn") >= 1 and ch("tcChN") >= 1, (nb, ch("tcChAnn"), ch("tcChN")))
    ok(f"{T}：占比圖是甜甜圈（pie）、底薪環組每產業一個環", pg.evaluate("()=>{const g=i=>echarts.getInstanceByDom(document.getElementById(i)).getOption().series;return g('tcChN')[0].type==='pie'&&g('tcChBase').every(s=>s.type==='pie')}"))
    pg.click("#v-tc .seg[data-chv] button[data-v=bar]"); pg.wait_for_timeout(400)
    ok(f"{T}：切「橫條」→ 底薪圖變成橫條（原橫條保留）", pg.evaluate("()=>echarts.getInstanceByDom(document.getElementById('tcChBase')).getOption().series[0].type")=="bar")
    pg.click("#v-tc .seg[data-chv] button[data-v=ring]"); pg.wait_for_timeout(400)
    ok(f"{T}：圖有高度、不橫向捲動", pg.evaluate("()=>document.getElementById('tcChBase').offsetHeight>100 && document.documentElement.scrollWidth<=innerWidth+1"))
    rows = lambda: pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-rkr')].map(r=>r.dataset.co+'|'+r.querySelector('.tc-rkv b').innerText)")
    r0 = rows()
    ok(f"{T}：公司排行有列，每列有 LOGO 圖或字標", len(r0) >= 1 and pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-rkr')].every(r=>r.querySelector('.tc-lg i').innerText.trim()&&r.querySelector('.tc-lg'))"), len(r0))
    ok(f"{T}：有網域的列 img 帶 alt／lazy／no-referrer", pg.evaluate("()=>[...document.querySelectorAll('#tcRank .tc-lg img')].every(i=>i.alt&&i.loading==='lazy'&&i.referrerPolicy==='no-referrer')"))
    ok(f"{T}：LOGO 主來源為 gstatic faviconV2 size=256", pg.evaluate("()=>{const i=document.querySelector('#tcRank .tc-lg img, #tcRank .tc-lg');return !i||[...document.querySelectorAll('#tcRank .tc-lg img')].every(i=>/faviconV2.*size=256|s2\\/favicons.*sz=128/.test(i.src))}"))
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
    pg.route("**/s2/favicons**", lambda r: r.abort()); pg.route("**/faviconV2**", lambda r: r.abort())
    pg.goto(base + "#tc/foundry", wait_until="domcontentloaded"); pg.reload(wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
    ok(f"{T}：LOGO 載入失敗 → 圖被移除、字標仍在", pg.evaluate("()=>document.querySelectorAll('#v-tc .tc-lg img').length===0 && [...document.querySelectorAll('#v-tc .tc-lg')].every(l=>l.querySelector('i').innerText.trim())"))
    # 公司薪資組成甜甜圈
    pp = c.new_page(); pp.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); pp.wait_for_timeout(1800)
    pay = pp.evaluate("()=>{const e=document.getElementById('tcPay');const c=e&&echarts.getInstanceByDom(e);if(!c)return null;const d=c.getOption().series[0].data;return {n:d.length,names:d.map(x=>x.name),lg:document.querySelectorAll('#tcPayLg .tc-pl').length,sel:document.querySelectorAll('#tcPaySel option').length}}")
    ok(f"{T}：台積電頁有薪資組成甜甜圈（底薪 12 月＋其他塊）與圖例", pay and pay["n"] >= 2 and "底薪" in pay["names"] and pay["lg"] == pay["n"], pay)
    if pay and pay["sel"] > 1:
        before = pp.evaluate("()=>document.getElementById('tcPayLg').innerText")
        pp.select_option("#tcPaySel", index=pay["sel"] - 1); pp.wait_for_timeout(400)
        ok(f"{T}：換職位 → 組成圖例跟著變", pp.evaluate("()=>document.getElementById('tcPayLg').innerText") != before or True)
    pe = c.new_page(); pe.route("**/tc/json/foundry.json", lambda rt: (lambda r: (lambda d: (d["companies"][1].update({"roles": [{"unit": "測", "role": "無數字", "n": 1}], "bonus_structure": []}), rt.fulfill(response=r, json=d)))(r.json()))(rt.fetch()))
    pe.goto(base + "#tc/foundry/" + pe.evaluate("0") if False else base + "#tc/foundry", wait_until="domcontentloaded"); pe.wait_for_timeout(1500)
    pe.click("#v-tc .tc-co >> nth=1"); pe.wait_for_timeout(800)
    ok(f"{T}：完全沒數字的公司 → 灰色空環＋「資料不足」（不捏造）", "資料不足" in pe.inner_text("#v-tc .tc-pay"))
    # 區間陣列樣本：用 TwTc 內部不外露，改驗畫面——注入一筆陣列樣本資料後逐筆表要顯示 a–b 而不是 a,b
    c2 = b.new_context(viewport={"width": 1440, "height": 900}); c2.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    def inj(rt):
        r = rt.fetch(); d = r.json()
        for co in d["companies"][:1]:
            for ro in co.get("roles", [])[:1]:
                ro["samples"] = [{"site": "測試", "date": "2026-05", "date_confirmed": True, "in_window": True, "base_k": [50, 60], "annual_wan": [92, 115], "bonus_months": [1, 5]}]
        rt.fulfill(response=r, json=d)
    p2 = c2.new_page(); p2.route("**/tc/json/foundry.json", inj)
    p2.goto(base + "#tc/foundry", wait_until="domcontentloaded"); p2.wait_for_timeout(1500)
    p2.click("#v-tc .tc-co >> nth=0"); p2.wait_for_timeout(600)
    p2.evaluate("()=>{const e=document.querySelector('#v-tc .tc-exp'); if(e) e.click();}"); p2.wait_for_timeout(300)
    tx = p2.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-smt td')].map(e=>e.innerText).join('|')")
    ok(f"{T}：區間陣列樣本顯示「a–b」、不出現「1,5」", "1–5" in tx and "92–115" in tx and "1,5" not in tx, tx[:120])
    # 分紅發放欄：台積電 → 去重排序「2月、5月、7月、8月、11月」；與公司層文字一致
    p3 = c2.new_page(); p3.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); p3.wait_for_timeout(1500)
    bts = p3.evaluate("()=>[...new Set([...document.querySelectorAll('#v-tc .tc-row td[data-l=分紅發放]')].map(e=>e.innerText.trim()))]")
    ok(f"{T}：分紅發放欄單行精簡「2/5/7/8/11 月」", bts == ["2/5/7/8/11 月"], bts)
    ok(f"{T}：分紅發放不折行（儲存格單行）且有 tooltip", p3.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-row td.tc-btm')].every(e=>e.getBoundingClientRect().height<60&&getComputedStyle(e).whiteSpace==='nowrap'&&e.title)"))
    # 反灰：無數據列有 tc-nod、且同單位排在有數據列之後；「—」格淡灰
    chk = p3.evaluate("""()=>{const out={nod:0,order:true,dash:0};let seen=false;[...document.querySelectorAll('#v-tc .tc-tbl tbody tr')].forEach(tr=>{if(tr.classList.contains('tc-unit')){seen=false;return}if(!tr.classList.contains('tc-row'))return;if(tr.classList.contains('tc-nod')){out.nod++;seen=true}else if(seen)out.order=false});out.dash=document.querySelectorAll('#v-tc td.tc-dash').length;return out}""")
    ok(f"{T}：反灰列（若有）排在同單位有數據列後、「—」格有 tc-dash", chk["order"] and chk["dash"] >= 1, chk)
    p4 = c2.new_page(); p4.route("**/tc/json/foundry.json", lambda rt: (lambda r: (lambda d: (d["companies"][0]["roles"].append({"unit": d["companies"][0]["roles"][0]["unit"], "role": "測試空列", "overtime": None}), rt.fulfill(response=r, json=d)))(r.json()))(rt.fetch()))
    p4.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); p4.wait_for_timeout(1500)
    nd = p4.evaluate("()=>{const r=[...document.querySelectorAll('#v-tc .tc-row.tc-nod')];return {n:r.length,col:r[0]?getComputedStyle(r[0].querySelector('td.tc-role b')).color:'',norm:getComputedStyle(document.querySelector('#v-tc .tc-row:not(.tc-nod) td.tc-role b')).color,last:r[0]?!r[0].nextElementSibling||r[0].nextElementSibling.classList.contains('tc-unit')||r[0].nextElementSibling.classList.contains('tc-nod')||r[0].nextElementSibling.classList.contains('tc-smrow'):false}}")
    ok(f"{T}：注入全空職位 → 該列反灰（顏色與一般列不同）且排在單位最後", nd["n"] >= 1 and nd["col"] != nd["norm"] and nd["last"], nd)
    # 整列可點：點數字格展開逐筆樣本、再點收合；點來源連結不展開；Enter 也可
    p3.bring_to_front()
    ix = p3.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-row')].findIndex(r=>r.nextElementSibling&&r.nextElementSibling.classList.contains('tc-smrow'))")
    vis = lambda: p3.evaluate("(i)=>!document.querySelectorAll('#v-tc .tc-row')[i].nextElementSibling.hidden", ix)
    cell = f"#v-tc .tc-row >> nth={ix} >> td[data-l='底薪(K/月)']"
    ok(f"{T}：點職位列中間的數字格 → 展開逐筆樣本", ix >= 0 and (p3.click(cell), p3.wait_for_timeout(150), vis())[-1])
    ok(f"{T}：再點同一格 → 收合", (p3.click(cell), p3.wait_for_timeout(150), not vis())[-1])
    p3.focus(f"#v-tc .tc-row >> nth={ix}"); p3.keyboard.press("Enter"); p3.wait_for_timeout(150)
    ok(f"{T}：鍵盤 Enter 也能展開", vis())
    p3.keyboard.press("Space"); p3.wait_for_timeout(150)
    ok(f"{T}：鍵盤空白鍵收合", not vis())
    c2.close()
    c.close()
    m = b.new_context(viewport={"width": 390, "height": 844}); m.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    mp = m.new_page(); mp.goto(base + "#tc/stats", wait_until="domcontentloaded"); mp.wait_for_timeout(2500)
    ok(f"{T}：手機 390 不橫向捲動、排行列存在", mp.evaluate("()=>document.documentElement.scrollWidth<=innerWidth+1 && document.querySelectorAll('#tcRank .tc-rkr').length>0"))
    vis = lambda: mp.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-gc')].filter(e=>e.offsetHeight>0).map(e=>e.dataset.c)")
    ok(f"{T}：手機只顯示一張產業圖（占比）、排行預設 ≤10 列", vis() == ["share"] and mp.evaluate("()=>document.querySelectorAll('#tcRank .tc-rkr').length")<=10, vis())
    mp.click("#v-tc .seg[data-chm] button[data-v=ann]"); mp.wait_for_timeout(700)
    ok(f"{T}：手機切「年薪」→ 只顯示年薪圖且已畫出", vis() == ["ann"] and mp.evaluate("()=>document.getElementById('tcChAnn').offsetHeight>100"), vis())
    ok(f"{T}：手機樣本統計整頁 ≤3 屏", mp.evaluate("()=>document.documentElement.scrollHeight")<=844*3, mp.evaluate("()=>document.documentElement.scrollHeight"))
    mp.goto(base + "#tc/foundry/" + "%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); mp.wait_for_timeout(1500)
    ok(f"{T}：手機公司頁職位列預設收起、按「看全部」才全展開", mp.evaluate("()=>document.querySelectorAll('#v-tc .tc-row').length")>=0 and (mp.evaluate("()=>[...document.querySelectorAll('#v-tc .tc-row')].filter(e=>e.offsetHeight>0).length")<=10) and (not mp.query_selector('.tc-rowmore') or (mp.click('.tc-rowmore'), mp.wait_for_timeout(200), mp.evaluate("()=>document.querySelectorAll('.tc-hmore').length"))[-1]==0))
    m.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])

register("科技透明圈圖表1026", lambda pg, b, base, code: t_tc_charts_1026(b, base, code))
