# 驗收段落「頻道規劃1104」—— Andy 11-04：「幫我在我那網頁新增頻道規劃 母分頁 方便我管理 觀看」。
# 真的操作：管理者進得去／一般人看不到入口也進不去、切子分頁內容換掉、展開選題、切排程階段、
# 390 寬無橫向溢出、缺頻道 JSON 顯示「整理中」。
# 頻道資料用攔截：stock 當「缺檔」（404）、tech_transparency 給一份小假資料（不依賴另兩個頻道是否已寫好）、ai_intro 用真檔。
# flake8: noqa

def t_channels(b, base):
    import json as _json, re as _re
    T = "頻道規劃1104"
    FAKE = {"id": "tech_transparency", "no": 2, "name": "測試頻道乙", "status": "測試中", "status_kind": "live",
            "tagline": "測試標語乙", "audience": {"main": "測試受眾"}, "pillars": [{"name": "測試支柱", "share": 100, "topics": ["題一", "題二"]}],
            "schedule": [{"phase": "階段甲", "weeks": "第 1 週", "summary": "甲", "rows": [{"day": "週一", "time": "20:00", "platform": "Threads", "type": "甲型", "mode": "手動", "minutes": 10}]}],
            "goals": {"short": {"label": "短期", "items": ["乙短一"]}, "mid": {"label": "中期", "items": ["乙中一"]}, "long": {"label": "長期", "items": ["乙長一"]}},
            "decisions": [{"q": "測試題", "options": "A／B", "rec": "A", "status": "待決定"}]}

    def route(r):
        m = _re.search(r"/channels/(stock|tech_transparency)\.json", r.request.url)
        if m and m.group(1) == "stock":
            r.fulfill(status=404, body="")
        elif m:
            r.fulfill(status=200, content_type="application/json", body=_json.dumps(FAKE, ensure_ascii=False))
        else:
            r.continue_()

    def open_page(W, H, adm, h="#channels"):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script(f"window.TW_LAB_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}}catch(e){{}}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctx.route("**/channels/*.json", route)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.goto(base + h, wait_until="load")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click()
        pg.wait_for_timeout(1200)
        return ctx, pg

    TAB = "() => { const t = document.querySelector('#tabs .tab[data-view=channels], .tab[data-view=channels]'); return !!t && t.getBoundingClientRect().width > 0 && getComputedStyle(t).display !== 'none'; }"
    OVF = "() => document.documentElement.scrollWidth - window.innerWidth"

    # ---- 管理者桌機
    ctx, pg = open_page(1440, 900, True)
    ok(f"[{T}] 管理者：html 有 ch-adm、側欄看得到「頻道規劃」", pg.evaluate("() => document.documentElement.classList.contains('ch-adm')") and pg.evaluate(TAB))
    wait_until(pg, "() => document.querySelectorAll('#v-channels .ch-ov tbody tr').length >= 3", 15000)
    ok(f"[{T}] 總覽：三個頻道各一列", pg.evaluate("() => document.querySelectorAll('#v-channels .ch-ov tbody tr').length") == 3)
    ok(f"[{T}] 缺檔頻道（stock）顯示「整理中」而不是壞掉", "整理中" in (pg.evaluate("() => (document.querySelector('#v-channels .ch-ov tr.ch-wait')||{}).textContent||''")))
    ov_txt = pg.evaluate("() => document.querySelector('#v-channels .ch').innerText")
    ok(f"[{T}] 總覽：ai_intro 那列有狀態徽章與目標第一條", pg.evaluate("() => { const r=[...document.querySelectorAll('#v-channels .ch-ov tbody tr')].find(x=>x.textContent.includes('AI 介紹')); return !!r && !!r.querySelector('.ch-st') && r.querySelectorAll('.ch-g3 span').length===3; }"))
    # 「?」真的開關
    pg.locator("#v-channels .ch-q").first.click(); pg.wait_for_timeout(150)
    ok(f"[{T}] 「?」點了展開說明", pg.evaluate("() => !document.querySelector('#v-channels .ch-pop').hidden"))
    pg.locator("#v-channels .ch-q").first.click(); pg.wait_for_timeout(150)
    ok(f"[{T}] 「?」再點收起", pg.evaluate("() => document.querySelector('#v-channels .ch-pop').hidden"))
    # 切子分頁：ai_intro（真檔）
    pg.locator("#v-channels .ch-tabs a[data-ch=ai_intro]").click(); pg.wait_for_timeout(500)
    ok(f"[{T}] 切到 ai_intro：網址與內容換掉", pg.evaluate("() => location.hash") == "#channels/ai_intro" and "AI 介紹頻道" in pg.evaluate("() => document.querySelector('#v-channels .ch-top h3').textContent") and pg.evaluate("() => document.querySelector('#v-channels .ch').innerText") != ov_txt)
    ok(f"[{T}] 單頻道頁：目標三欄、支柱卡、排程階段鈕都有畫", pg.evaluate("() => document.querySelectorAll('#v-channels .ch-gc').length") == 3 and pg.evaluate("() => document.querySelectorAll('#v-channels .ch-pil').length") >= 3 and pg.evaluate("() => document.querySelectorAll('#v-channels .ch-ptabs button').length") >= 2)
    ok(f"[{T}] 收展區塊預設全部收起", pg.evaluate("() => document.querySelectorAll('#v-channels details.ch-sec[open]').length") == 0 and pg.evaluate("() => document.querySelectorAll('#v-channels details.ch-sec').length") >= 6)
    # 展開選題
    ok(f"[{T}] 選題預設收起", pg.evaluate("() => !document.querySelector('#v-channels .ch-tp').open"))
    pg.locator("#v-channels .ch-tp summary").first.click(); pg.wait_for_timeout(200)
    ok(f"[{T}] 點「選題」展開，題目看得到", pg.evaluate("() => { const d=document.querySelector('#v-channels .ch-tp'); const li=d.querySelector('li'); return d.open && li.getBoundingClientRect().height>0; }"))
    # 切排程階段
    s0 = pg.evaluate("() => document.querySelector('#v-channels .ch-sbody').innerText"); r0 = pg.evaluate("() => document.querySelectorAll('#v-channels .ch-sbody tbody tr').length")
    pg.locator("#v-channels .ch-ptabs button").nth(1).click(); pg.wait_for_timeout(200)
    s1 = pg.evaluate("() => document.querySelector('#v-channels .ch-sbody').innerText")
    ok(f"[{T}] 切排程階段：表格內容真的換了、第二顆鈕亮起", s1 != s0 and pg.evaluate("() => document.querySelectorAll('#v-channels .ch-ptabs button')[1].classList.contains('on')"), f"{r0}→{pg.evaluate('() => document.querySelectorAll(\"#v-channels .ch-sbody tbody tr\").length')}")
    # 展開手動或自動區塊
    pg.locator("#v-channels details.ch-sec summary").first.click(); pg.wait_for_timeout(200)
    ok(f"[{T}] 點收展標題列：區塊內容展開", pg.evaluate("() => { const d=document.querySelector('#v-channels details.ch-sec'); return d.open && d.querySelector('table').getBoundingClientRect().height>0; }"))
    # 切到另一個有（假）資料的頻道，內容換成它
    pg.locator("#v-channels .ch-tabs a[data-ch=tech_transparency]").click(); pg.wait_for_timeout(500)
    ok(f"[{T}] 切到頻道②：顯示該頻道內容（不是上一個的）", "測試頻道乙" in pg.evaluate("() => document.querySelector('#v-channels .ch-top h3').textContent") and "AI 介紹" not in pg.evaluate("() => document.querySelector('#v-channels .ch').innerText"))
    # 缺檔頻道頁
    pg.locator("#v-channels .ch-tabs a[data-ch=stock]").click(); pg.wait_for_timeout(500)
    ok(f"[{T}] 缺檔頻道頁：顯示「整理中」、頁面沒壞", pg.evaluate("() => !!document.querySelector('#v-channels .ch-waitcard') && document.querySelector('#v-channels .ch-waitcard').innerText.includes('整理中')"))
    ok(f"[{T}] 桌機無橫向溢出", pg.evaluate(OVF) <= 0, pg.evaluate(OVF))
    ctx.close()

    # ---- 管理者手機 390
    ctx, pg = open_page(390, 844, True, h="#channels/ai_intro")
    wait_until(pg, "() => document.querySelector('#v-channels .ch-top')", 15000); pg.wait_for_timeout(400)
    ok(f"[{T}] 手機 390：頻道頁無橫向溢出", pg.evaluate(OVF) <= 0, pg.evaluate(OVF))
    ok(f"[{T}] 手機第一屏看得到頂卡摘要與目標卡開頭", pg.evaluate("() => { const t=document.querySelector('#v-channels .ch-top').getBoundingClientRect(); const g=document.querySelector('#v-channels .ch-gc').getBoundingClientRect(); return t.top < 700 && t.bottom < 844 && g.top < 844; }"))
    ok(f"[{T}] 手機：選項表格可手指橫拖（外框可捲、頁面不溢出）", pg.evaluate("() => { const sc=document.querySelector('#v-channels .ch-sbody .ch-scroll'); return !!sc && sc.scrollWidth > sc.clientWidth && getComputedStyle(sc).overflowX==='auto'; }"))
    ok(f"[{T}] 手機：最小字級 >= 11px", pg.evaluate("() => [...document.querySelectorAll('#v-channels *')].filter(e=>e.children.length===0 && e.textContent.trim() && e.getBoundingClientRect().width>0).every(e=>parseFloat(getComputedStyle(e).fontSize)>=11)"))
    pg.evaluate("() => { location.hash = '#channels'; }"); wait_until(pg, "() => document.querySelectorAll('#v-channels .ch-ov tbody tr').length >= 3", 10000)
    ok(f"[{T}] 手機：總覽無橫向溢出（表格自己橫拖）", pg.evaluate(OVF) <= 0 and pg.evaluate("() => { const sc=document.querySelector('#v-channels .ch-scroll'); return sc.scrollWidth > sc.clientWidth; }"), pg.evaluate(OVF))
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 管理者手機抽屜列得出「頻道規劃」", pg.evaluate("() => [...document.querySelectorAll('#m4Drawer [data-v], .m4item')].some(e => e.dataset.v === 'channels')"))
    ctx.close()

    # ---- 一般訪客
    ctx, pg = open_page(1440, 900, False, h="#overview")
    ok(f"[{T}] 一般人：html 沒有 ch-adm、側欄看不到「頻道規劃」", (not pg.evaluate("() => document.documentElement.classList.contains('ch-adm')")) and not pg.evaluate(TAB))
    pg.evaluate("() => { location.hash = '#channels'; }"); pg.wait_for_timeout(500)
    pg.evaluate("() => window.dispatchEvent(new Event('tw:account'))"); pg.wait_for_timeout(1500)
    ok(f"[{T}] 一般人：直接開 #channels 被導回 #overview、沒畫出內容", pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => document.querySelectorAll('#v-channels .ch-tabs').length") == 0, pg.evaluate("() => location.hash"))
    ctx.close()
    ctx, pg = open_page(1440, 900, False, h="#channels/ai_intro")
    pg.wait_for_timeout(6500)
    ok(f"[{T}] 一般人：網址一開始就是 #channels/ai_intro，6 秒內導回 #overview", pg.evaluate("() => location.hash") == "#overview", pg.evaluate("() => location.hash"))
    ctx.close()
    ctx, pg = open_page(390, 844, False, h="#overview")
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 一般人：手機抽屜沒有「頻道規劃」", pg.evaluate("() => !document.querySelector('.m4item[data-v=channels]')"))
    ctx.close()


register("頻道規劃1104", lambda pg, b, base, code: t_channels(b, base))
