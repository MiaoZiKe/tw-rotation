# 驗收段落「流向驗證v4」—— Andy 11-01 20:20：「數據有點太多了 看不懂怎麼用，幫我給個導覽吧」「我還是不知道怎麼使用」
# 「我要的是他可以搭配看 驗證我的數據」。第一屏＝驗證三步驟（選一天→我們的數據說→實際股價怎麼走）＋吻合率；新手導覽；河流／輪盤收進「看細節」。
# 資料一律攔 /data/flowcheck/**，用 scripts/_fc3_fake.py（原型真資料轉成真欄位）。兩條路徑都驗：
#   A. 沒有 verify.json（預覽版吃正式站資料的情況）→ 前端用 day 檔算；B. 有 verify.json（用 pipeline.compute.flowcheck.verify 實際算出）。
# 吻合率的數字另外在這裡用 Python 獨立重算一次，跟畫面比（不准捏造數字）。每一步都驗「畫面真的因此改變」。
# flake8: noqa

def t_flowcheck_v4(b, base):
    import json as _json, re as _re, sys as _sys
    _sys.path.insert(0, str(SITE.parent / "scripts")); _sys.path.insert(0, str(SITE.parent))
    import _fc3_fake as FK
    import pandas as _pd
    from pipeline.compute import flowcheck as _fc
    T = "流向驗證v4"
    FILES = FK.build()
    FILES["next_wave.json"] = FK.next_wave()
    dates = FILES["index.json"]["dates"]
    gids = [g["gid"] for g in FILES["index.json"]["groups"]]
    rows = []
    for d in dates:
        dy = FILES[f"day/{d}.json"]
        for gid, r in dy["groups"].items():
            rows.append({"date": d, "group_id": gid, "turnover_share": r["share"], "dshare": r["dshare"], "chg_pct": r["chg"], "mkt_chg": dy["mkt_chg"], "rel": r["rel"]})
    EXP = _fc.verify(_pd.DataFrame(rows), set(gids), dates, days=len(dates))          # 期望值：後端同一支函式
    # 獨立重算（不用 verify()）：最近 20 日流入前 3「當天跑贏加權」的 k／n
    def indep(win):
        k = n = 0
        for d in dates[-win:]:
            dy = FILES[f"day/{d}.json"]
            c = [(g, r) for g, r in dy["groups"].items() if r["share"] is not None and r["share"] >= 1 and r["dshare"] is not None and r["rel"] is not None]
            c.sort(key=lambda x: -x[1]["dshare"])
            for g, r in c[:3]:
                n += 1; k += 1 if r["rel"] > 0 else 0
        return k, n

    def make_route(with_verify):
        def route(r):
            m = _re.search(r"/data/flowcheck/(.+?\.json)", r.request.url)
            if m and m.group(1) == "verify.json" and with_verify:
                r.fulfill(status=200, content_type="application/json", body=_json.dumps(EXP, ensure_ascii=False))
            elif m and m.group(1) in FILES:
                r.fulfill(status=200, content_type="application/json", body=_json.dumps(FILES[m.group(1)], ensure_ascii=False))
            elif m:
                r.fulfill(status=404, body="")
            else:
                r.continue_()
        return route

    def open_page(W, H, h="#flowcheck", theme="dark", with_verify=False, tour_seen=True):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script("window.TW_LAB_OVERRIDE=true;try{" + ("localStorage.setItem('fc.tour4','1');" if tour_seen else "") + "localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctx.route("**/data/flowcheck/**", make_route(with_verify))
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]} {str(getattr(e, 'stack', ''))[:300]}"))
        pg.goto(base + h, wait_until="load")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click()
        pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
        wait_until(pg, "() => document.querySelectorAll('#fc4Cols .fc4-row').length >= 6", 15000)
        pg.wait_for_timeout(400)
        return ctx, pg

    J = lambda pg, js, *a: pg.evaluate(js, *a)
    v4 = lambda pg: pg.evaluate("() => TwFlowV4.state()")
    rowsig = lambda pg: pg.evaluate("() => [...document.querySelectorAll('#fc4Cols .fc4-row')].map(r => r.innerText.replace(/\\s+/g, ' ')).join('|')")
    tiles = lambda pg: pg.evaluate("() => [...document.querySelectorAll('#fc4Hit .fc4-tile')].map(t => ({ v: t.querySelector('.fc4-tv').textContent, s: t.querySelector('.fc4-ts').textContent, low: t.classList.contains('low') }))")
    OVL = """() => { const bad = []; document.querySelectorAll('#fc4Cols .fc4-row').forEach(row => {
      const cs = [...row.children].filter(c => c.getBoundingClientRect().width > 0 && !c.classList.contains('fc4-say') && getComputedStyle(c).display !== 'none');
      for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) { const a = cs[i].getBoundingClientRect(), c = cs[j].getBoundingClientRect();
        const w = Math.min(a.right, c.right) - Math.max(a.left, c.left), h = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
        if (w > 1.5 && h > 2) bad.push(cs[i].className + '×' + cs[j].className); } }); return bad.slice(0, 5); }"""
    MINFONT = """() => { const out = []; document.querySelectorAll('#fc4Card *').forEach(e => { const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!own) return;
      if (e.closest('[hidden]') || !e.getBoundingClientRect().width) return; const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 11.5) out.push(e.textContent.trim().slice(0, 8) + '=' + fs); }); return out.slice(0, 6); }"""

    # ---------------------------------------------------------------- A. 桌機 1440×900，沒有 verify.json（前端算）
    ctx, pg = open_page(1440, 900)
    s0 = v4(pg)
    DEF = dates[-6]       # 最近一個「已有之後 5 日結果」的交易日（最新日之後還沒滿 5 日）
    ok(f"[{T}] A1 沒有 verify.json 時用 day 檔在前端算（來源 day）、預設日＝最近一個已有 5 日結果的交易日 {DEF}（不是最新日 {dates[-1]}）", s0["src"] == "day" and s0["d"] == DEF, s0)
    ok(f"[{T}] A1b 預設日第一眼就有 ✓／✗：6 張卡的「5 日」判定都不是 —；看細節裡的河流停在同一天", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-c5')].every(c => !/5 日 —/.test(c.innerText))") and J(pg, "() => TwFlowV3.state().date") == DEF, J(pg, "() => TwFlowV3.state().date"))
    ok(f"[{T}] A2 第一屏（1440×900）就看到：吻合率、① 選一天、② 流入前 3、流出前 3 共 6 張卡", J(pg, "() => ['#fc4Hit', '#fc4S1', '#fc4Inn', '#fc4Out'].every(s => { const r = document.querySelector(s).getBoundingClientRect(); return r.height > 0 && r.bottom <= innerHeight; })"), J(pg, "() => ['#fc4Hit','#fc4S1','#fc4Inn','#fc4Out'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().bottom))"))
    txt = J(pg, "() => document.getElementById('fc4Card').innerText")
    ok(f"[{T}] A3 三步驟字樣都在：選一天／我們的數據說／實際股價怎麼走", all(k in txt for k in ("選一天", "我們的數據說", "實際股價怎麼走", "吻合率")), txt[:120])
    ok(f"[{T}] A4 每張卡有名稱、占比、當天漲跌、之後 5 日、判定 ✓／✗／—", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-row')].every(r => r.querySelector('.fc4-nm b').textContent.trim() && /%/.test(r.querySelector('.fc4-c2').textContent) && /%/.test(r.querySelector('.fc4-c3').textContent) && r.querySelectorAll('.fc4-v').length === 2 && /[✓✗—]/.test(r.querySelector('.fc4-c5').textContent))"))
    ok(f"[{T}] A5 每張卡有一句白話說明（含「加權指數」與「吻合」或「不吻合」或「還沒滿 5 個交易日」）", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-say')].every(e => /加權指數/.test(e.textContent) && /吻合|不吻合|還沒/.test(e.textContent))"))
    ok(f"[{T}] A6 同一列的欄位彼此不重疊", not J(pg, OVL), J(pg, OVL))
    # 判定與資料一致：最新日第一張流入卡，用 FILES 重算判定
    last = DEF; dy = FILES[f"day/{last}.json"]
    cand = sorted([(g, r) for g, r in dy["groups"].items() if r["share"] is not None and r["share"] >= 1 and r["dshare"] is not None], key=lambda x: -x[1]["dshare"])
    g1, r1 = cand[0]
    nm1 = next(g["name"] for g in FILES["index.json"]["groups"] if g["gid"] == g1)
    row1 = J(pg, "() => document.querySelector('#fc4Inn .fc4-row').innerText.replace(/\\s+/g, ' ')")
    exp_chg = ("+" if r1["chg"] > 0 else "") + f"{r1['chg']:.1f}%"
    ok(f"[{T}] A7 流入第 1 名＝資料排序第 1（{nm1}、當天 {exp_chg}），判定與 rel 符號一致", nm1 in row1 and exp_chg in row1 and (("當天 ✓" in row1) == (r1["rel"] > 0)), row1)
    # 吻合率：畫面數字＝獨立重算
    t60 = tiles(pg); k60, n60 = indep(60)
    ok(f"[{T}] A8 吻合率（60 日）流入前 3 當天跑贏加權＝獨立重算 {k60}／{n60}（{round(k60 / n60 * 100)}%）", t60[0]["v"] == f"{round(k60 / n60 * 100)}%" and f"{k60}／{n60}" in t60[0]["s"], (t60[0], k60, n60))
    ok(f"[{T}] A9 四格吻合率都有數字與筆數；隨機約 50% 的提示在", len(t60) == 4 and all(re_ok for re_ok in [bool(_re.match(r"^\d+%$|^—$", t["v"])) for t in t60]) and "50%" in J(pg, "() => document.getElementById('fc4Hit').innerText"), t60)
    sig60 = J(pg, "() => document.getElementById('fc4Hit').innerText")
    pg.click("#fc4Win [data-win='20']"); pg.wait_for_timeout(200)
    t20 = tiles(pg); k20, n20 = indep(20)
    ok(f"[{T}] A10 切到 20 日：標題寫「最近 20 個交易日」、數字改成獨立重算 {k20}／{n20}", "最近 20 個交易日" in J(pg, "() => document.getElementById('fc4Hit').innerText") and f"{k20}／{n20}" in t20[0]["s"] and J(pg, "() => document.getElementById('fc4Hit').innerText") != sig60, t20[0])
    ok(f"[{T}] A11 樣本少於 30 筆的格子標「樣本不足」並灰字（20 日×3＝{n20} 筆）", (n20 >= 30) or all(t["low"] and "樣本不足" in t["s"] for t in t20[:1]), t20)
    # ① 換日期
    sig_before = rowsig(pg); mid = dates[len(dates) // 2]
    pg.select_option("#fc4Date", mid); pg.wait_for_timeout(250)
    ok(f"[{T}] B1 下拉換成 {mid}：6 張卡內容改變、狀態日期＝{mid}、之後 5 日有數字", rowsig(pg) != sig_before and v4(pg)["d"] == mid and J(pg, "() => /[+-]\\d/.test(document.querySelector('#fc4Inn .fc4-c4').innerText)"), v4(pg))
    dymid = FILES[f"day/{mid}.json"]
    cm = sorted([(g, r) for g, r in dymid["groups"].items() if r["share"] is not None and r["share"] >= 1 and r["dshare"] is not None], key=lambda x: -x[1]["dshare"])
    exp_name = next(g["name"] for g in FILES["index.json"]["groups"] if g["gid"] == cm[0][0])
    ok(f"[{T}] B2 換日期後流入第 1 名＝該日資料排序第 1（{exp_name}）", exp_name in J(pg, "() => document.querySelector('#fc4Inn .fc4-row .fc4-nm b').textContent"))
    # 之後 5 日：獨立重算第 1 名
    i0 = dates.index(mid); gg = cm[0][0]
    def comp(xs):
        c = 1.0
        for x in xs: c *= 1 + x / 100
        return (c - 1) * 100
    g5 = comp([FILES[f"day/{dates[k]}.json"]["groups"][gg]["chg"] for k in range(i0 + 1, i0 + 6)]); m5 = comp([FILES[f"day/{dates[k]}.json"]["mkt_chg"] for k in range(i0 + 1, i0 + 6)])
    shown = J(pg, "() => document.querySelector('#fc4Inn .fc4-c4').innerText")
    ok(f"[{T}] B3 「之後 5 日」＝獨立重算複利 {g5:+.1f}%，判定 {'✓' if g5 - m5 > 0 else '✗'}", (f"{g5:+.1f}%" in shown) and (("5 日 ✓" in J(pg, "() => document.querySelector('#fc4Inn .fc4-row').innerText")) == (g5 - m5 > 0)), shown)
    pg.click("#fc4Prev"); pg.wait_for_timeout(200)
    ok(f"[{T}] B4 ◀ 前一個交易日、▶ 回來", v4(pg)["d"] == dates[i0 - 1] and (pg.click("#fc4Next") or True) and (pg.wait_for_timeout(200) or True) and v4(pg)["d"] == mid)
    ok(f"[{T}] B5 不在最新日時才有「回最新」，按了回到 {dates[-1]}", J(pg, "() => getComputedStyle(document.getElementById('fc4Latest')).visibility") == "visible" and (pg.click("#fc4Latest") or True) and (pg.wait_for_timeout(250) or True) and v4(pg)["d"] == dates[-1] and J(pg, "() => getComputedStyle(document.getElementById('fc4Latest')).visibility") == "hidden")
    pg.select_option("#fc4Date", dates[-6]); pg.wait_for_timeout(250)
    ok(f"[{T}] B6 剛好滿 5 個交易日的那天（{dates[-6]}）之後 5 日有數字、判定不是 —", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-c4')].every(c => /[+-]\\d/.test(c.innerText)) && [...document.querySelectorAll('#fc4Cols .fc4-c5')].every(c => !/5 日 —/.test(c.innerText))"))
    pg.select_option("#fc4Date", dates[-3]); pg.wait_for_timeout(250)
    ok(f"[{T}] B6 還沒滿 5 個交易日的那天（{dates[-3]}）寫「未滿 5 日」、5 日判定為 —，不亂估", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-c4')].every(c => /未滿 5 日/.test(c.innerText)) && [...document.querySelectorAll('#fc4Cols .fc4-c5')].every(c => /5 日 —/.test(c.innerText))"))
    pg.select_option("#fc4Date", dates[-1]); pg.wait_for_timeout(250)
    ok(f"[{T}] B6 最新日：之後 5 日一律「未滿 5 日」", J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-c4')].every(c => /未滿 5 日/.test(c.innerText))"))
    # 河流同步（日期選到 30 日內時，看細節裡的河流跟著換）
    pg.select_option("#fc4Date", dates[-4]); pg.wait_for_timeout(300)
    ok(f"[{T}] B7 步驟①換日期時，看細節裡的河流日期也跟著換（{dates[-4]}）", J(pg, "() => TwFlowV3.state().date") == dates[-4], J(pg, "() => TwFlowV3.state()"))
    pg.select_option("#fc4Date", dates[-1]); pg.wait_for_timeout(250)
    # 點小卡展開
    ok(f"[{T}] C1 預設全部收起：沒有任何卡展開、看細節也收起", J(pg, "() => document.querySelectorAll('.fc4-item.open').length === 0 && document.getElementById('fc3DetBd').hidden"))
    pg.click("#fc4Inn .fc4-item:nth-child(2) .fc4-row"); pg.wait_for_timeout(700)
    ok(f"[{T}] C2 點流入第 1 張卡：展開、aria-expanded、出現圖與一句說明", J(pg, "() => { const it = document.querySelector('#fc4Inn .fc4-item.open'); return !!it && it.querySelector('.fc4-row').getAttribute('aria-expanded') === 'true' && !it.querySelector('.fc4-panel').hidden && !!it.querySelector('.fc4-chart canvas, .fc4-chart svg') && /加權指數/.test(it.querySelector('.fc4-ps').textContent); }"))
    gopen = v4(pg)["open"]
    lk = J(pg, "() => document.querySelector('.fc4-item.open .fc4-lk').getAttribute('href')")
    ok(f"[{T}] C3 展開後有超連結到該族群頁（{lk}）", lk == "#industry/group/" + gopen and "族群頁" in J(pg, "() => document.querySelector('.fc4-item.open .fc4-lk').textContent"), lk)
    ok(f"[{T}] C4 展開的圖有兩條線＋資金占比長條（族群、加權指數、資金占比）", J(pg, "() => { const c = document.querySelector('.fc4-item.open .fc4-chart'); const i = echarts.getInstanceByDom(c); if (!i) return false; const o = i.getOption(); return o.series.map(s => s.name).join(',').includes('加權指數') && o.series.some(s => s.name === '資金占比'); }"))
    pg.click("#fc4Out .fc4-item:nth-child(2) .fc4-row"); pg.wait_for_timeout(500)
    ok(f"[{T}] C5 再點流出第 1 張卡：新的展開、舊的收起（同一時間只有一張）", J(pg, "() => document.querySelectorAll('.fc4-item.open').length") == 1 and v4(pg)["open"] != gopen and J(pg, "() => !!document.querySelector('#fc4Out .fc4-item.open')"))
    ok(f"[{T}] C6 點卡只展開走勢、不動看細節（河流選取不變、看細節仍收起）；河流選族群改按「在資金河流圖看它」", J(pg, "() => TwFlowV3.state().sel") is None and J(pg, "() => document.getElementById('fc3DetBd').hidden"))
    pg.click("#fc4Out .fc4-item.open .fc4-row"); pg.wait_for_timeout(250)
    ok(f"[{T}] C7 再點同一張＝收起", J(pg, "() => document.querySelectorAll('.fc4-item.open').length") == 0)
    pg.click("#fc4Inn .fc4-item:nth-child(2) .fc4-row"); pg.wait_for_timeout(500)
    gl = v4(pg)["open"]
    pg.click(".fc4-item.open .fc4-lk"); pg.wait_for_timeout(500)
    ok(f"[{T}] C8 點「進族群頁」真的換到族群頁 #industry/group/{gl}", J(pg, "() => location.hash") == "#industry/group/" + gl, J(pg, "() => location.hash"))
    pg.go_back(); pg.wait_for_timeout(800)
    # 看細節
    wait_until(pg, "() => !!document.getElementById('fc3DetTog')", 8000)
    ok(f"[{T}] D1 看細節預設收起、按「展開」後出現河流圖與輪盤切換、河流圖有畫", J(pg, "() => document.getElementById('fc3DetBd').hidden") and (pg.click("#fc3DetTog") or True) and (pg.wait_for_timeout(600) or True) and J(pg, "() => !document.getElementById('fc3DetBd').hidden && !!document.querySelector('#fc3Stage svg') && !!document.querySelector('#fc3View [data-v=wheel]')"))
    pg.click("#fc3View [data-v='wheel']"); pg.wait_for_timeout(400)
    ok(f"[{T}] D2 輪盤保留：切輪盤後主圖換成輪盤", J(pg, "() => TwFlowV3.state().view") == "wheel" and J(pg, "() => !!document.querySelector('#fc3Stage .fc3-wheelwrap, #fc3Stage svg')"))
    pg.click("#fc3DetTog"); pg.wait_for_timeout(200)
    ok(f"[{T}] D3 再按一次收起，頁面回到只剩三步驟", J(pg, "() => document.getElementById('fc3DetBd').hidden"))
    pg.click("#fc4Inn .fc4-item:nth-child(3) .fc4-row"); pg.wait_for_timeout(500)
    gr = v4(pg)["open"]; pg.click(".fc4-item.open [data-act='river']"); pg.wait_for_timeout(900)
    ok(f"[{T}] D3b 按小卡展開區的「在資金河流圖看它」：看細節自動展開、河流選取＝該族群（{gr}）、主圖有畫（列高亮由 v3 段落 ⑥ 驗）", J(pg, "() => !document.getElementById('fc3DetBd').hidden") and J(pg, "() => TwFlowV3.state().sel") == gr and J(pg, "() => !!document.querySelector('#fc3Stage svg')"), J(pg, "() => TwFlowV3.state().sel"))
    sub = J(pg, "() => document.getElementById('fc3SigWrap').innerText")
    ok(f"[{T}] D4 最下方標「訂閱功能預覽（規劃中）」徽章與「之後訂閱會員可使用」，標題改「條件追蹤」，內容照常顯示、沒有上鎖", "訂閱功能預覽（規劃中）" in sub and "之後訂閱會員可使用" in sub and "條件追蹤" in sub and not J(pg, "() => !!document.querySelector('#fc3SigWrap [data-plk], #fc3SigWrap [inert]')"), sub[:120])
    _all = J(pg, "() => document.getElementById('v-flowcheck').textContent")
    _bw = [w for w in ("埋伏", "進場", "出場", "布局", "燈號", "建議買") if w in _all]
    ok(f"[{T}] D4b 法遵：整頁（含收起的區塊）沒有「埋伏、進場、出場、布局、燈號、建議買」字眼", not _bw, _bw)
    ok(f"[{T}] D5 版面順序：吻合率／三步驟在最上、看細節在中間、訂閱預覽在最下", J(pg, "() => { const y = s => document.querySelector(s).getBoundingClientRect().top; return y('#fc4Card') < y('#fc3Detail') && y('#fc3Detail') < y('#fc3SigWrap'); }"))
    ok(f"[{T}] D6 畫面沒有 pageerror、沒有 11px 以下的字", not J(pg, MINFONT), J(pg, MINFONT))
    ctx.close()

    # 網址帶 d= 時以網址為準；▶ 從預設日往後一天
    ctx, pg = open_page(1440, 900, h=f"#flowcheck?d={dates[-3]}")
    ok(f"[{T}] A12 網址帶 ?d={dates[-3]}：以網址為準（不是預設日）、河流同一天；之後 5 日未滿的卡照現在顯示「未滿 5 日」", v4(pg)["d"] == dates[-3] and J(pg, "() => TwFlowV3.state().date") == dates[-3] and J(pg, "() => [...document.querySelectorAll('#fc4Cols .fc4-c4')].every(c => /未滿 5 日/.test(c.innerText))"), v4(pg))
    ctx.close()
    ctx, pg = open_page(1440, 900)
    pg.click("#fc4Next"); pg.wait_for_timeout(300)
    ok(f"[{T}] A13 預設日按 ▶：切到下一天 {dates[-5]}，「回最新」鈕還在（沒到最新）", v4(pg)["d"] == dates[-5] and J(pg, "() => getComputedStyle(document.getElementById('fc4Latest')).visibility") == "visible")
    ctx.close()

    # 客服鈕（右下角固定）不蓋住「看細節」「進階」的展開鈕：捲到頁底後兩顆鈕都在客服鈕範圍外
    for W, H in ((1440, 900), (390, 844)):
        ctx, pg = open_page(W, H, with_verify=True)
        pg.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(600)
        hit = pg.evaluate("""() => { const f = document.getElementById('supFab'); if (!f) return 'no fab'; const fr = f.getBoundingClientRect(), bad = [];
          ['fc3DetTog', 'fcAdvTog'].forEach(id => { const r = document.getElementById(id).getBoundingClientRect();
            if (Math.min(r.right, fr.right) - Math.max(r.left, fr.left) > 0 && Math.min(r.bottom, fr.bottom) - Math.max(r.top, fr.top) > 0) bad.push(id); });
          return bad; }""")
        ok(f"[{T}] A14 {W}px 捲到頁底：客服鈕沒有蓋住「看細節」「進階」的展開鈕", hit == [] or hit == "no fab", hit)
        ctx.close()

    # ---------------------------------------------------------------- B. 有 verify.json（後端實際算出）
    ctx, pg = open_page(1440, 900, with_verify=True)
    s1 = v4(pg)
    ok(f"[{T}] E1 有 verify.json 時直接用它（來源 verify、{s1['n']} 個日期）", s1["src"] == "verify" and s1["n"] == len(dates), s1)
    tv = tiles(pg); kv, nv = indep(60)
    ok(f"[{T}] E2 後端 verify() 與前端畫面一致：60 日流入前 3 當天吻合 {kv}／{nv}", f"{kv}／{nv}" in tv[0]["s"], (tv[0], EXP["stats"]["60"]["inn_day"]))
    st60 = EXP["stats"]["60"]
    ok(f"[{T}] E3 四格筆數都等於後端 stats（n：{st60['inn_day']['n']}／{st60['inn_f5']['n']}／{st60['out_day']['n']}／{st60['out_f5']['n']}）", all(f"／{n} 筆" in t["s"] for t, n in zip(tv, [st60['inn_day']['n'], st60['inn_f5']['n'], st60['out_day']['n'], st60['out_f5']['n']])), tv)
    # 兩條路徑算出來的小卡要一樣
    sv = rowsig(pg); ctx.close()
    ctx, pg = open_page(1440, 900, with_verify=False)
    _a = rowsig(pg)
    ok(f"[{T}] E4 前端算的與後端 verify.json 的 6 張卡逐字相同（兩條路徑口徑一致）", _a == sv, [(x, y) for x, y in zip(_a.split("|"), sv.split("|")) if x != y][:1])
    ctx.close()

    # ---------------------------------------------------------------- C. 新手導覽
    ctx, pg = open_page(1440, 900, tour_seen=False)
    wait_until(pg, "() => window.TwTour && TwTour.state().active && TwTour.state().i === 0 && !TwTour.state().busy", 12000)
    ts = J(pg, "() => TwTour.state()")
    ok(f"[{T}] F1 第一次進來自動跑導覽：流向驗證導覽、共 5 步、停在第 1 步", ts.get("active") and ts.get("tour") == "flowcheck" and ts.get("n") == 5 and ts.get("i") == 0, ts)
    pg.wait_for_timeout(700)
    ts = J(pg, "() => TwTour.state()")
    ok(f"[{T}] F2 第 1 步高亮的是「① 選一天」那一列（遮罩洞與 #fc4S1 重疊）", J(pg, "() => { const h = TwTour.state().hole, r = document.getElementById('fc4S1').getBoundingClientRect(); return Math.min(h.r, r.right) - Math.max(h.l, r.left) > 50 && Math.min(h.b, r.bottom) - Math.max(h.t, r.top) > 10; }"), ts)
    titles = [J(pg, "() => document.getElementById('twTourT').textContent")]
    for k in range(4):
        pg.click("#twTourNext"); pg.wait_for_timeout(1300)
        titles.append(J(pg, "() => document.getElementById('twTourT').textContent"))
    ok(f"[{T}] F3 按「下一步」五次走完 5 步，標題各不同：{' → '.join(titles)}", len(set(titles)) == 5 and J(pg, "() => TwTour.state().i") == 4, titles)
    pg.wait_for_timeout(1200)
    ok(f"[{T}] F4 每步的說明卡不蓋住被框的目標", J(pg, "() => { const s = TwTour.state(); if (!s.card || !s.target) return false; const c = s.card, t = s.target; return Math.min(c.r, t.r) - Math.max(c.l, t.l) < 4 || Math.min(c.b, t.b) - Math.max(c.t, t.t) < 4; }"), J(pg, "() => TwTour.state()"))
    pg.click("#twTourSkip"); pg.wait_for_timeout(300)
    ok(f"[{T}] F5 「跳過導覽」關掉導覽，並記住看過（fc.tour4）", not J(pg, "() => TwTour.state().active") and J(pg, "() => localStorage.getItem('fc.tour4')") == "1")
    pg.reload(wait_until="load"); wait_until(pg, "() => document.querySelectorAll('#fc4Cols .fc4-row').length >= 6", 15000); pg.wait_for_timeout(2200)
    ok(f"[{T}] F6 重新整理後不再自動跳導覽", not J(pg, "() => TwTour.state().active"))
    pg.click("#fc4Tour"); pg.wait_for_timeout(900)
    ok(f"[{T}] F7 按頁內「? 導覽」可重看，回到第 1 步", J(pg, "() => TwTour.state().active && TwTour.state().tour === 'flowcheck' && TwTour.state().i === 0"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    ok(f"[{T}] F8 Esc 關閉導覽、頁面三步驟仍在", not J(pg, "() => TwTour.state().active") and J(pg, "() => document.querySelectorAll('#fc4Cols .fc4-row').length") == 6)
    pg.click("#twPageTourBtn") if pg.locator("#twPageTourBtn").count() and pg.locator("#twPageTourBtn").first.is_visible() else None
    pg.wait_for_timeout(700)
    ok(f"[{T}] F9 頁首右上「導覽」鈕在這一頁開的是流向驗證導覽（不是全站導覽）", (not pg.locator("#twPageTourBtn").count()) or (not pg.locator("#twPageTourBtn").first.is_visible()) or J(pg, "() => TwTour.state().tour") == "flowcheck")
    ctx.close()

    # ---------------------------------------------------------------- D. 手機 390×844
    ctx, pg = open_page(390, 844, with_verify=True)
    ok(f"[{T}] G1 手機：沒有橫向捲軸", J(pg, "() => document.documentElement.scrollWidth <= innerWidth + 1"))
    fs = J(pg, "() => ['#fc4Hit', '#fc4S1', '#fc4Inn', '#fc4Out'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().bottom))")
    ok(f"[{T}] G2 手機第一屏（390×844）看到吻合率＋選一天＋流入前 3＋流出前 3（底邊 {fs} ≤ 844）", all(v <= 844 for v in fs), fs)
    ok(f"[{T}] G3 手機最小字 ≥ 12px、同列欄位不重疊", not J(pg, MINFONT) and not J(pg, OVL), (J(pg, MINFONT), J(pg, OVL)))
    small = J(pg, "() => [...document.querySelectorAll('#fc4S1 button:not(.howbtn), #fc4S1 select, #fc4Win button')].filter(e => e.getBoundingClientRect().width && e.getBoundingClientRect().height < 39.5).map(e => (e.textContent || e.id).trim() + ':' + Math.round(e.getBoundingClientRect().height))")
    ok(f"[{T}] G4 手機觸控：日期列與 20／60 日鈕高 ≥ 40", not small, small)
    sg = rowsig(pg)
    pg.tap("#fc4Prev"); pg.wait_for_timeout(250)
    ok(f"[{T}] G5 手機點 ◀：日期往前一天、6 張卡跟著換", v4(pg)["d"] == dates[-7] and rowsig(pg) != sg)
    pg.tap("#fc4Inn .fc4-item:nth-child(2) .fc4-row"); pg.wait_for_timeout(700)
    ok(f"[{T}] G6 手機點卡：展開圖與族群頁連結，沒有橫捲", J(pg, "() => !!document.querySelector('.fc4-item.open .fc4-chart canvas, .fc4-item.open .fc4-chart svg') && !!document.querySelector('.fc4-item.open .fc4-lk') && document.documentElement.scrollWidth <= innerWidth + 1"))
    ok(f"[{T}] G7 手機展開的說明一句話看得到（桌機列內說明在手機收進展開區）", J(pg, "() => { const p = document.querySelector('.fc4-item.open .fc4-ps'); return !!p && p.getBoundingClientRect().width > 100; }"))
    bot = J(pg, "() => document.getElementById('fc3SigWrap').getBoundingClientRect().bottom + scrollY")
    ok(f"[{T}] G8 手機整頁 ≤ 3 屏（{round(bot)}px ≤ {844 * 3}）", bot <= 844 * 3, bot)
    ctx.close()

    # ---------------------------------------------------------------- E. 淺色主題
    ctx, pg = open_page(1440, 900, theme="light", with_verify=True)
    ok(f"[{T}] H1 淺色主題：吻合率數字與判定徽章的文字對比 ≥ 3（可讀）", J(pg, """() => { const lum = c => { const m = c.match(/[\\d.]+/g).map(Number); const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]); };
      const bg = el => { let e = el; while (e) { const c = getComputedStyle(e).backgroundColor; if (c && !/rgba?\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; e = e.parentElement; } return 'rgb(255,255,255)'; };
      return [...document.querySelectorAll('.fc4-tv, .fc4-v.ok, .fc4-v.bad')].every(e => { const a = lum(getComputedStyle(e).color), c = lum(bg(e)); return (Math.max(a, c) + .05) / (Math.min(a, c) + .05) >= 3; }); }"""))
    ctx.close()


register("流向驗證v4", lambda pg, b, base, code: t_flowcheck_v4(b, base))
