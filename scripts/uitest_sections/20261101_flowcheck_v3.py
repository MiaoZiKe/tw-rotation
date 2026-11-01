# 驗收段落「流向驗證v3」—— Andy 11-01：「這還是太亂了 資訊太雜看不懂…站在想使用介面但不想花太多時間的人進行安排」
# 「資金輪盤 資金樹 都需要放在同一張圖 觀看走勢圖變化」「最後也需要有實際使用案例 不管是成功失敗都需要透過驗證來證明我們的數據工具成效」。
# 規格 docs/design/20261101_flowcheck_v3.md 5.5。資料一律攔 /data/flowcheck/**，用 scripts/_fc3_fake.py 造（原型裡的真資料轉成真欄位），
# 所以本機有沒有 site/data/flowcheck 結果都一樣。每一步都驗「畫面真的因此改變」。
# 由 _uitest.py 用 exec 載入，ok()／wait_until()／fails／SITE 直接可用。
# flake8: noqa

def t_flowcheck_v3(b, base):
    import json as _json, re as _re, sys as _sys
    _sys.path.insert(0, str(SITE.parent / "scripts"))
    import _fc3_fake as FK
    T = "流向驗證v3"
    FILES = FK.build()
    NW = FK.next_wave()
    FILES["next_wave.json"] = NW

    def route(r):
        m = _re.search(r"/data/flowcheck/(.+?\.json)", r.request.url)
        if m and m.group(1) in FILES:
            r.fulfill(status=200, content_type="application/json", body=_json.dumps(FILES[m.group(1)], ensure_ascii=False))
        elif m:
            r.fulfill(status=404, body="")
        else:
            r.continue_()

    def open_page(W, H, h="#flowcheck", theme="dark"):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script("try{localStorage.setItem('fc.tour4','1');localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctx.route("**/data/flowcheck/**", route)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]} {str(getattr(e, 'stack', ''))[:300]}"))
        pg.goto(base + h, wait_until="load")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click()
        pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
        # v4（11-01 20:20）：河流／輪盤收進「看細節」、預設收起 → 這段先展開再驗；新手導覽用 fc.tour4 擋掉
        wait_until(pg, "() => document.querySelectorAll('#fc3Ans .fc3-chip').length >= 6 && !!document.getElementById('fc3DetTog')", 15000)
        pg.evaluate("() => { if (document.getElementById('fc3DetBd').hidden) document.getElementById('fc3DetTog').click(); }")
        wait_until(pg, "() => !!document.querySelector('#fc3Stage svg')", 15000)
        pg.wait_for_timeout(500)
        return ctx, pg

    J = lambda pg, js, *a: pg.evaluate(js, *a)
    st = lambda pg: pg.evaluate("() => TwFlowV3.state()")
    card_h = lambda pg: pg.evaluate("() => Math.round(document.getElementById('fc3Card').getBoundingClientRect().height)")
    sig = lambda pg: pg.evaluate("() => document.getElementById('fc3Stage').innerHTML.length + '|' + document.getElementById('fc3Sent').textContent")

    OVERLAP = """() => { const els = [...document.querySelectorAll('#fc3Stage svg text')].filter(e => e.textContent.trim() && e.getBoundingClientRect().width > 0);
      const rs = els.map(e => [e.textContent.trim(), e.getBoundingClientRect()]); const bad = [];
      for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) { const a = rs[i][1], c = rs[j][1];
        const w = Math.min(a.right, c.right) - Math.max(a.left, c.left), h = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
        if (w > 1.5 && h > 2) bad.push(rs[i][0] + ' × ' + rs[j][0]); }
      return bad.slice(0, 6); }"""
    MINFONT = """() => { const out = []; document.querySelectorAll('#fc3root *').forEach(e => { if (!e.childNodes.length) return;
      const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!own) return;
      if (e.closest('[hidden]') || !e.getBoundingClientRect().width) return;
      const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 12) out.push(e.tagName + ':' + e.textContent.trim().slice(0, 8) + '=' + fs); }); return out.slice(0, 6); }"""
    LABELS = """() => { const svg = document.querySelector('#fc3Stage svg.fc3-svg'); if (!svg) return ['no svg'];
      const L = [...svg.querySelectorAll('text.fc3-halo')].map(e => ({ n: e.textContent, r: e.getBoundingClientRect() })), bad = [];
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const a = L[i].r, c = L[j].r;
        if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > -2 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > -2) bad.push('標籤相碰 ' + L[i].n + '×' + L[j].n); }
      const pts = [...svg.querySelectorAll('g.fc3-pt')].map(g => { const c = g.querySelector('circle').getBoundingClientRect(); return { g: g.dataset.g, x: c.left + c.width / 2, y: c.top + c.height / 2 }; });
      L.forEach(l => { const n = pts.filter(p => p.x > l.r.left && p.x < l.r.right && p.y > l.r.top && p.y < l.r.bottom).length; if (n > 1) bad.push('標籤「' + l.n + '」壓在 ' + n + ' 個點中心上'); });
      return bad.slice(0, 6); }"""
    RGSCAN = """() => { const probe = v => { const e = document.createElement('i'); e.style.color = 'var(' + v + ')'; document.body.appendChild(e); const c = getComputedStyle(e).color; e.remove(); return c; };
      const R = probe('--rise'), G = probe('--fall'), bad = []; const isRG = c => c === R || c === G;
      document.querySelectorAll('#fc3root *').forEach(e => { const cs = getComputedStyle(e), tag = e.tagName.toLowerCase();
        if (['path', 'rect', 'circle'].includes(tag) && (isRG(cs.fill) || isRG(cs.stroke))) bad.push(tag + ' ' + (e.getAttribute('class') || ''));
        if (isRG(cs.backgroundColor)) bad.push('bg ' + tag + ' ' + e.className);
        if (!['svg', 'g', 'polyline', 'line', 'path', 'rect', 'circle', 'title'].includes(tag) && isRG(cs.color)) {
          const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
          if (own.trim() && !/\\d/.test(own)) bad.push('text ' + tag + ':' + own.trim().slice(0, 10)); } });
      return bad.slice(0, 6); }"""

    # ---------------------------------------------------------------- 桌機 1440×900
    ctx, pg = open_page(1440, 900)
    s0 = st(pg)
    ok(f"[{T}] ① 進頁：預設河流、30 日、最新日、主圖有畫", s0["view"] == "river" and s0["win"] == 30 and s0["date"] == FILES["index.json"]["latest"] and J(pg, "() => document.querySelectorAll('#fc3Stage g.fc3-row').length") == 10, s0)
    ok(f"[{T}] ① 流入 3＋流出 3 共 6 張卡，每張有名稱與當天漲跌", J(pg, "() => [...document.querySelectorAll('#fc3Ans .fc3-chip')].every(c => c.querySelector('.n').textContent && /%/.test(c.querySelector('.v').textContent))") and J(pg, "() => document.querySelectorAll('#fc3Ans .fc3-chip').length") == 6)
    ok(f"[{T}] ① 一句白話結論有寫出第 1 名與「加權指數」", "加權指數" in J(pg, "() => document.getElementById('fc3Sent').textContent"))
    ok(f"[{T}] ① 卡片寫「今日 +x 百分點」（不再是看不懂的「占比 +x」）", J(pg, "() => [...document.querySelectorAll('#fc3Ans .fc3-chip .v .a')].every(e => /今日 [+-]?\\d+\\.\\d+ 百分點/.test(e.textContent))"))
    _day = FILES["index.json"]["latest"]; _gs = FILES[f"day/{_day}.json"]["groups"]; _nm = {g["gid"]: g["name"] for g in FILES["index.json"]["groups"]}
    _r = sorted([k for k, v in _gs.items() if (v["share"] or 0) >= 1 and v["dshare"] is not None], key=lambda k: -_gs[k]["dshare"])
    _want_in = [_nm[k] for k in _r[:3]]; _want_out = [_nm[k] for k in _r[::-1][:3]]
    _got = J(pg, "() => [...document.querySelectorAll('#fc3Ans .fc3-chip')].map(e => e.title)")
    ok(f"[{T}] ① 流入前 3／流出前 3 與資料算出的一致（占比 ≥ 1% 才參與）：{_got}", _got == _want_in + _want_out, (_got, _want_in, _want_out))
    top_det = J(pg, "() => Math.round(document.getElementById('fc3Detail').getBoundingClientRect().top)")
    ok(f"[{T}] ② 1440×900 一屏（v4）：第一屏是驗證三步驟，「看細節」（河流／輪盤）的標題列也在 900px 內（頂＝{top_det}）；河流主圖在它裡面、不再佔首屏", top_det <= 900, top_det)
    ok(f"[{T}] ② 沒有三輪盤並排／三者同向籤／琥珀時間軸標記（已拿掉）", J(pg, "() => !document.querySelector('#fcW_strength, #fcSame, .fc-marks, #fcTl')"))
    ok(f"[{T}] ② 進階預設收起（收展預設收起準則）", J(pg, "() => !document.getElementById('fcAdv').classList.contains('open') && !document.querySelector('#fcAdv .fc-bd').offsetParent"))
    ok(f"[{T}] ② 桌機沒有橫向捲軸", J(pg, "() => document.documentElement.scrollWidth <= innerWidth + 1"))
    ok(f"[{T}] ③ 河流文字框不重疊", not J(pg, OVERLAP), J(pg, OVERLAP))
    ok(f"[{T}] ③ 最小字 ≥ 12px", not J(pg, MINFONT), J(pg, MINFONT))
    ok(f"[{T}] ③ 紅綠只出現在漲跌（色帶／點／底色沒有紅綠，紅綠文字都帶數字）", not J(pg, RGSCAN), J(pg, RGSCAN))

    # 版面不晃：換日期／窗口／切河流輪盤／點卡，主圖卡 rect 高度都一樣
    h0 = card_h(pg); sg0 = sig(pg)
    pg.evaluate("() => { const r = document.getElementById('fc3Range'); r.value = r.min; r.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(300)
    s1 = st(pg)
    ok(f"[{T}] ④ 拖滑桿到窗口起點：日期真的變、結論句與主圖跟著換、顯示「回最新」", s1["t"] < s0["t"] and sig(pg) != sg0 and J(pg, "() => getComputedStyle(document.getElementById('fc3Latest')).visibility") == "visible", s1)
    hs = [card_h(pg)]
    pg.click("#fc3Win [data-w='10']"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    s2 = st(pg)
    ok(f"[{T}] ④ 切 10 日：窗口真的變（滑桿下限上移、日期落在窗口內）", s2["win"] == 10 and J(pg, "() => +document.getElementById('fc3Range').min") == s2["T"] - 10 and s2["t"] >= s2["T"] - 10, s2)
    pg.click("#fc3Win [data-w='20']"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    pg.click("#fc3View [data-v='wheel']"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    ok(f"[{T}] ④ 輪盤視圖：畫出圓點，且點數 ≥ 20", J(pg, "() => document.querySelectorAll('#fc3Stage g.fc3-pt').length") >= 20)
    ok(f"[{T}] ④ 輪盤文字框不重疊", not J(pg, OVERLAP), J(pg, OVERLAP))
    ok(f"[{T}] ④ 輪盤標籤兩兩不相碰（留 2px 間隙）、不壓在點中心上", not J(pg, LABELS), J(pg, LABELS))
    _fn = J(pg, "() => (TwFlowV3.state(), document.querySelector('.fc3-sname') ? document.querySelector('.fc3-sname').textContent : '')")
    ok(f"[{T}] ④ 焦點族群（右側面板寫的那個）在輪盤上有標籤", J(pg, "(n) => [...document.querySelectorAll('#fc3Stage text.fc3-halo')].some(e => n.indexOf(e.textContent.replace('…', '')) === 0)", _fn.strip()), _fn)
    ok(f"[{T}] ④ 輪盤沒有箭頭（marker）", J(pg, "() => !document.querySelector('#fc3Stage marker, #fc3Stage [marker-end]')"))
    pp = J(pg, "() => [...document.querySelectorAll('#fc3Stage g.fc3-pt')].map(e => ({g: e.dataset.g, x: +e.dataset.x, y: +e.dataset.y, r: +e.dataset.r}))")
    pairs = sorted(((((a['x'] - c['x']) ** 2 + (a['y'] - c['y']) ** 2) ** .5, a, c) for i, a in enumerate(pp) for c in pp[i + 1:]), key=lambda z: z[0])[:3]
    pg.evaluate("() => document.getElementById('fc3Stage').scrollIntoView({ block: 'center', behavior: 'instant' })"); pg.wait_for_timeout(1200)     # v4：主圖在「看細節」裡、離首屏較遠，座標點擊前先捲到可見
    sb = J(pg, "() => { const r = document.querySelector('#fc3Stage svg.fc3-svg').getBoundingClientRect(); return [r.left, r.top]; }")
    good = 0
    for d_, a, c in pairs:
        small = a if a['r'] <= c['r'] else c
        pg.mouse.click(sb[0] + small['x'], sb[1] + small['y']); pg.wait_for_timeout(250)
        good += st(pg)["sel"] == small['g']
    ok(f"[{T}] ④ 輪盤點最擠的 3 對點：點小點的中心，選到的就是它（不被蓋住的大點吃掉），選到 {good}/3", good == 3, (good, [(round(d_, 1), a['g'], c['g']) for d_, a, c in pairs]))
    ok(f"[{T}] ④ 被選的點畫在最上層（最後一個 fc3-pt）並有標籤", J(pg, "(g) => { const l = [...document.querySelectorAll('#fc3Stage g.fc3-pt')]; return l[l.length - 1].dataset.g === g; }", st(pg)["sel"]))
    pg.click("#fc3Ans .fc3-grp:nth-child(2) .fc3-chip:nth-child(2)"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    g_pick = st(pg)["sel"]
    pg.click("#fc3View [data-v='river']"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    pg.click("#fc3Win [data-w='30']"); pg.wait_for_timeout(300); hs.append(card_h(pg))
    ok(f"[{T}] ⑤ 換日期／窗口／切河流輪盤／點卡：主圖卡高度不變（{sorted(set(hs + [h0]))}）", len(set(hs + [h0])) == 1, hs + [h0])

    # 選取：點卡、點列、點輪盤的點三處一致；再點取消；切視圖不丟
    ok(f"[{T}] ⑥ 點流出第 2 張卡：選取＝它、卡片高亮、河流該列高亮", bool(g_pick) and J(pg, "(g) => !!document.querySelector('#fc3Ans .fc3-chip.on[data-g=\"' + g + '\"]') && !!document.querySelector('#fc3Stage g.fc3-row.on[data-g=\"' + g + '\"]')", g_pick), g_pick)
    pg.click("#fc3View [data-v='wheel']"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑥ 切到輪盤：選取沒有丟（同一個族群、輪盤右側面板寫它的名字）", st(pg)["sel"] == g_pick and J(pg, "(g) => document.querySelector('.fc3-side .fc3-sname').textContent.includes(window.TwFlowV3 && document.querySelector('#fc3Ans .fc3-chip.on .n').textContent.slice(0, 3))", g_pick))
    pts = pg.locator("#fc3Stage g.fc3-pt"); other = None
    for i in range(min(pts.count(), 40)):
        gid = pts.nth(i).get_attribute("data-g")
        if gid != g_pick:
            other = gid; pts.nth(i).click(force=True); break
    pg.wait_for_timeout(300)
    ok(f"[{T}] ⑥ 點輪盤的一個點：選取換成它、河流卡片同步高亮", st(pg)["sel"] == other and J(pg, "(g) => !!document.querySelector('#fc3Ans .fc3-chip.on[data-g=\"' + g + '\"]') || !document.querySelector('#fc3Ans .fc3-chip.on')", other), (st(pg)["sel"], other))
    pg.click("#fc3View [data-v='river']"); pg.wait_for_timeout(300)
    pg.locator(f"#fc3Stage g.fc3-row[data-g='{other}']").click(); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑥ 在河流再點同一列：取消選取，高亮消失，提示不殘留", st(pg)["sel"] is None and J(pg, "() => !document.querySelector('#fc3Stage g.fc3-row.on') && document.getElementById('fc3Tip').style.display !== 'block'"))
    box = pg.locator("#fc3Stage g.fc3-row").nth(1).bounding_box()
    pg.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] / 2); pg.wait_for_timeout(200)
    ok(f"[{T}] ⑥ 滑過一列：出現提示（名稱、占比、當天漲跌、加權）", J(pg, "() => { const t = document.getElementById('fc3Tip'); return t.style.display === 'block' && /占比/.test(t.textContent) && /加權/.test(t.textContent); }"))
    pg.mouse.move(5, 5); pg.wait_for_timeout(200)

    # 播放：畫面真的改變，到尾自動停；點「回最新」
    pg.evaluate("() => { const r = document.getElementById('fc3Range'); r.value = +r.max - 3; r.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(200)
    t0 = st(pg)["t"]; sg1 = sig(pg)
    pg.click("#fc3Play"); pg.wait_for_timeout(1300)
    t1 = st(pg)["t"]
    ok(f"[{T}] ⑦ 按播放：日期往後走、畫面與結論句真的換（{t0}→{t1}）", t1 > t0 and sig(pg) != sg1, (t0, t1))
    pg.wait_for_timeout(2200)
    s3 = st(pg)
    ok(f"[{T}] ⑦ 播放到最新日自動停、按鈕回到 ▶", (not s3["playing"]) and s3["t"] == s3["T"] - 1 and J(pg, "() => document.getElementById('fc3Play').textContent.trim()") == "▶", s3)
    pg.evaluate("() => { const r = document.getElementById('fc3Range'); r.value = +r.min; r.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(200)
    pg.click("#fc3Latest"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑦ 按「回最新」：回到最新日、按鈕隱藏", st(pg)["t"] == st(pg)["T"] - 1 and J(pg, "() => getComputedStyle(document.getElementById('fc3Latest')).visibility") == "hidden")
    ok(f"[{T}] ⑦ 網址帶狀態（#flowcheck?…d= 或 v=）可分享", "flowcheck" in J(pg, "() => location.hash"))

    # 今天的訊號
    sg_txt = J(pg, "() => document.getElementById('fc3SigWrap').innerText")
    ok(f"[{T}] ⑧ 條件追蹤列首屏一行（法遵口吻）：標題「條件追蹤：外資＋投信 10 日買超前 20% 的族群」、「條件成立的族群」、「歷史統計不代表未來結果，非投資建議」，只列族群", "條件追蹤：外資＋投信 10 日買超前 20% 的族群" in sg_txt and "條件成立的族群" in sg_txt and "歷史統計不代表未來結果，非投資建議" in sg_txt, sg_txt[:160])
    pg.click("[data-sig='toggle']"); pg.wait_for_timeout(300)
    sg_row = sg_txt
    sg_txt = J(pg, "() => document.getElementById('fc3SigWrap').innerText")
    ok(f"[{T}] ⑧ 點開證據：出現四句固定說明（2024～2025、2012～2019、2026、空頭）與候選族群連結", all(k in sg_txt for k in ("2024", "2012", "2026", "空頭", "+0.96%", "+0.50%", "0.19%", "前瞻紀錄：收集中", "臨界")) and J(pg, "() => document.querySelectorAll('#fc3Sig [data-sig=pick]').length") >= 1, [k for k in ('2024','2012','2026','空頭','+0.96%','+0.50%','0.19%','前瞻紀錄：收集中','臨界') if k not in sg_txt])
    _four = J(pg, "() => document.querySelector('#fc3Sig .fc3-four').innerText")
    import re as _re2
    _pcts = _re2.findall(r"\d+\.(\d+)%", _four)
    ok(f"[{T}] ⑧ 證據句沒有「Rank IC」、改白話（相關 -0.01）、百分比一律兩位小數", "Rank IC" not in sg_txt and "相關 -0.01" in _four and _pcts and all(len(x) == 2 for x in _pcts), (_four, _pcts))
    _bw = ("推薦", "買進", "HBM", "埋伏", "進場", "出場", "布局", "燈號", "建議買")
    ok(f"[{T}] ⑧ 全區沒有「推薦」「買進」「埋伏」「進場」「出場」「布局」「燈號」「建議買」字樣、不列個股", not any(w in sg_txt for w in _bw), [w for w in _bw if w in sg_txt])
    ok(f"[{T}] ⑧ 條件追蹤列底部揭示「歷史統計不代表未來結果，非投資建議」；展開按鈕寫「看歷史統計」，表頭是「平均／比全部族群好的期數比例／樣本數」", "歷史統計不代表未來結果，非投資建議" in sg_row and "看歷史統計" in sg_row and all(k in sg_txt for k in ("平均（比全部族群多", "樣本數", "好的期數比例")), sg_row)
    pg.click("#fc3Sig [data-sig='pick']"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑧ 點候選族群：主圖選取它", st(pg)["sel"] is not None)
    pg.click("[data-sig='toggle']"); pg.wait_for_timeout(200)

    # 進階：分段切換、每段真的有內容
    pg.click("#fcAdvTog"); pg.wait_for_timeout(600)
    ok(f"[{T}] ⑨ 點「展開」進階：分段列出現、預設顯示「驗證與案例」", J(pg, "() => document.getElementById('fcAdv').classList.contains('open') && document.querySelectorAll('#fcAdvSeg button').length === 9 && !document.getElementById('fcAP_cases').hidden"))
    wait_until(pg, "() => document.querySelectorAll('#fcCases .fc3-case').length >= 6", 6000)
    n_ok = J(pg, "() => document.querySelectorAll('#fcCases .fc3-case.ok').length"); n_bad = J(pg, "() => document.querySelectorAll('#fcCases .fc3-case.bad').length")
    ok(f"[{T}] ⑨ 驗證與案例：成功 {n_ok} 例、失敗 {n_bad} 例（各 ≥ 3）", n_ok >= 3 and n_bad >= 3)
    cs_txt = J(pg, "() => document.getElementById('fcCases').innerText")
    ok(f"[{T}] ⑨ 整體統計：413 筆、+1.24%、-0.92%、46.0%、保留樣本 1,158 筆 49.7%、第二版案例日期與數字、白話三句", "413" in cs_txt and "+1.24%" in cs_txt and "0.92%" in cs_txt and "46.0%" in cs_txt and "1,158" in cs_txt and "49.7%" in cs_txt and "不能當成穩定獲利工具" in cs_txt and "2026-03-17" in cs_txt and "+45.2%" in cs_txt and "-31.0%" in cs_txt, cs_txt[:160])
    ok(f"[{T}] ⑨ 案例區標題寫明是「綜合分數 A」，與上面的條件追蹤是不同方法", "綜合分數 A" in cs_txt and "條件追蹤" in cs_txt and "不同" in cs_txt)
    ok(f"[{T}] ⑨ 案例都寫了日期、族群、之後 5／20／60 日、當時與教訓", J(pg, "() => [...document.querySelectorAll('#fcCases .fc3-case')].every(c => /20\\d\\d-\\d\\d-\\d\\d/.test(c.textContent) && /60 日/.test(c.textContent) && /教訓/.test(c.textContent))"))
    for key, probe in [("heat", "#fcHeat canvas, #fcHeat svg"), ("trend", "#fcTrend canvas, #fcTrend svg"), ("div", "#fcDivPane .fc-dr, #fcDivPane .muted"),
                       ("strength", "#fcWheel canvas, #fcWheel svg"), ("daily", "#fcDay *"), ("sig", "#fcSigL *"), ("news", "#fcNews *, #fcInst canvas, #fcInst svg")]:
        pg.click(f"#fcAdvSeg [data-v='{key}']"); pg.wait_for_timeout(900)
        vis = J(pg, "(k) => [...document.querySelectorAll('#fcAdv .fc-pane')].filter(p => !p.hidden).map(p => p.id)", key)
        has = J(pg, "(q) => document.querySelectorAll(q).length > 0", probe)
        ok(f"[{T}] ⑨ 進階「{key}」：一次只顯示這一段、而且真的有畫（或說清楚沒資料）", vis == [f"fcAP_{key}"] and has, (vis, probe))
    pg.click("#fcAdvSeg [data-v='mem']"); pg.wait_for_timeout(700)
    ok(f"[{T}] ⑨ 進階「成分股」：只顯示這一段、說得出為什麼沒有", J(pg, "() => !document.getElementById('fcAP_mem').hidden && document.getElementById('fcAP_mem').innerText.length > 10"))
    pg.click("#fcAdvSeg [data-v='trend']"); pg.wait_for_timeout(500)
    nm0 = J(pg, "() => document.getElementById('fcTrendName').textContent")
    pg.evaluate("() => { window.scrollTo(0, 0); }");
    chips = pg.locator("#fc3Ans .fc3-chip"); chips.nth(0).click(); pg.wait_for_timeout(600)
    nm1 = J(pg, "() => document.getElementById('fcTrendName').textContent")
    ok(f"[{T}] ⑨ 進階與首屏同步：在上面點一張卡，進階走勢大圖換成同一個族群（{nm0}→{nm1}）", nm1 == J(pg, "() => document.querySelector('#fc3Ans .fc3-chip.on .n').textContent") and nm1 != "—", (nm0, nm1))
    ctx.close()

    # ---------------------------------------------------------------- 淺色主題：對比
    ctx, pg = open_page(1440, 900, theme="light")
    CON = """() => { const parse = c => c.match(/[\\d.]+/g).map(Number); const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
      const cr = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
      const bg = parse(getComputedStyle(document.getElementById('fc3Card')).backgroundColor).slice(0, 3);
      const probe = v => { const e = document.createElement('i'); e.style.color = 'var(' + v + ')'; document.body.appendChild(e); const c = parse(getComputedStyle(e).color).slice(0, 3); e.remove(); return c; };
      const blend = (c, a) => c.map((v, i) => v * a + bg[i] * (1 - a));
      const o = { 次要字: cr(probe('--ink-3'), bg), 一般字: cr(probe('--ink-2'), bg), 琥珀: cr(probe('--amber'), bg), 紅: cr(probe('--rise'), bg), 綠: cr(probe('--fall'), bg) };
      ['semiconductor', 'ai_server', 'siph_cpo', 'electronics', 'software', 'financial', 'traditional', 'infrastructure'].forEach(k => { o['色帶_' + k] = cr(blend(probe('--cat-' + k), .8), bg); });
      return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, +v.toFixed(2)])); }"""
    cv = J(pg, CON)
    low_txt = {k: v for k, v in cv.items() if not k.startswith("色帶") and v < 4.5}
    low_band = {k: v for k, v in cv.items() if k.startswith("色帶") and v < 3}
    ok(f"[{T}] ⑩ 淺色主題對比：文字 ≥ 4.5、色帶 ≥ 3（量值：{_json.dumps(cv, ensure_ascii=False)}）", not low_txt and not low_band, (low_txt, low_band))
    ok(f"[{T}] ⑩ 淺色主題：河流與輪盤文字框不重疊、紅綠只在漲跌", not J(pg, OVERLAP) and not J(pg, RGSCAN))
    ctx.close()

    # ---------------------------------------------------------------- 手機 390×844
    ctx, pg = open_page(390, 844)
    ok(f"[{T}] ⑪ 手機：沒有橫向捲軸", J(pg, "() => document.documentElement.scrollWidth <= innerWidth + 1"))
    top = J(pg, "() => document.getElementById('v-flowcheck').getBoundingClientRect().top + scrollY")
    bot = J(pg, "() => document.getElementById('fcAdv').getBoundingClientRect().bottom + scrollY")
    ok(f"[{T}] ⑪ 手機整頁 ≤ 3 屏（內容高 {round(bot - top)}px ≤ {844 * 3}；v4 加了驗證三步驟，上限從 1.3 屏放寬到手機準則的 3 屏）", bot - top <= 844 * 3, bot - top)
    rg = J(pg, """() => { const r = document.getElementById('fc3Range'), b = r.getBoundingClientRect(); let th = 0;
      const walk = rules => [...rules].forEach(x => { if (x.selectorText) { if (/fc3-ctl input\\[type=.?range.?\\]::-webkit-slider-thumb/.test(x.selectorText)) th = Math.max(th, parseFloat(x.style.width) || 0); } else if (x.cssRules) walk(x.cssRules); });
      [...document.styleSheets].forEach(sh => { try { walk(sh.cssRules); } catch (e) {} });
      return [Math.round(b.width), Math.round(b.height), th, Math.round(document.getElementById('fc3Stage').getBoundingClientRect().right)]; }""")
    ok(f"[{T}] ⑪ 手機滑桿：寬 ≥ 280、高 ≥ 40、把手 ≥ 32px、主圖右側留 32px 安全區（{rg}）", rg[0] >= 279 and rg[1] >= 40 and rg[2] >= 31.5 and rg[3] <= 390 - 32 + 1, rg)
    pg.evaluate("() => { const r = document.getElementById('fc3Range'); r.value = +r.min; r.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(200)
    pg.tap("#fc3Latest"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑪ 手機拖滑桿到最早後，手指點一下「回最新」就回到最新日", st(pg)["t"] == st(pg)["T"] - 1, st(pg))
    pg.evaluate("() => document.getElementById('fc3Detail').scrollIntoView()"); pg.wait_for_timeout(300)
    first4 = J(pg, "() => [...document.querySelectorAll('#fc3Stage g.fc3-row')].slice(0, 4).every(r => r.getBoundingClientRect().bottom <= innerHeight)")
    ok(f"[{T}] ⑪ 手機首屏看得到：切換鈕、結論句、6 張卡、主圖前 4 列", first4 and J(pg, "() => ['#fc3View', '#fc3Sent', '#fc3Ans'].every(s => document.querySelector(s).getBoundingClientRect().bottom <= innerHeight)"))
    ok(f"[{T}] ⑪ 手機最小字 ≥ 12px、文字框不重疊（河流）", not J(pg, MINFONT) and not J(pg, OVERLAP), (J(pg, MINFONT), J(pg, OVERLAP)))
    small = J(pg, "() => [...document.querySelectorAll('#fc3View button, #fc3Win button, #fc3Play, #fc3Latest')].filter(e => e.getBoundingClientRect().width && e.getBoundingClientRect().height < 39.5).map(e => e.textContent.trim() + ':' + Math.round(e.getBoundingClientRect().height))")
    ok(f"[{T}] ⑪ 手機觸控：期間／切換鈕高 ≥ 40、播放 ≥ 44", not small and J(pg, "() => document.getElementById('fc3Play').getBoundingClientRect().height >= 43.5"), small)
    pg.locator("#fc3Stage g.fc3-row").nth(2).click(); pg.wait_for_timeout(300)
    inf = J(pg, "() => document.getElementById('fc3Info').textContent")
    ok(f"[{T}] ⑪ 手機點一列：上方細節列寫出該族群的占比與今日漲跌、列高亮", "占比" in inf and "今日" in inf and J(pg, "() => !!document.querySelector('#fc3Stage g.fc3-row.on')") and J(pg, "() => document.getElementById('fc3Tip').style.display !== 'block'"), inf)
    mh = [card_h(pg)]
    pg.click("#fc3View [data-v='wheel']"); pg.wait_for_timeout(300); mh.append(card_h(pg))
    ok(f"[{T}] ⑪ 手機輪盤：文字框不重疊、選取不丟、主圖卡高度不變（{sorted(set(mh))}）", not J(pg, OVERLAP) and st(pg)["sel"] is not None and len(set(mh)) == 1, (J(pg, OVERLAP), mh))
    ok(f"[{T}] ⑪ 手機輪盤標籤兩兩不相碰、不壓在點中心上", not J(pg, LABELS), J(pg, LABELS))
    ok(f"[{T}] ⑪ 手機輪盤下方有被選族群的累計走勢小圖（含起訖日）", J(pg, "() => !!document.querySelector('#fc3Stage .fc3-minibox svg.fc3-mini') && document.querySelectorAll('#fc3Stage .fc3-minibox text').length >= 4"))
    pg.click("#fc3View [data-v='river']"); pg.wait_for_timeout(200)
    pg.click("#fc3Win [data-w='10']"); pg.wait_for_timeout(300); mh.append(card_h(pg))
    ok(f"[{T}] ⑪ 手機切 10 日：主圖卡高度不變", len(set(mh)) == 1, mh)
    pg.click("[data-sig='toggle']"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑪ 手機證據表下方有「← 左右滑 →」提示、表可橫向捲", J(pg, "() => { const s = document.querySelector('#fc3Sig .fc3-swipe'); return !!s && s.offsetParent !== null && /左右滑/.test(s.textContent) && getComputedStyle(document.querySelector('#fc3Sig .fc3-tw')).overflowX !== 'visible'; }"))
    pg.click("[data-sig='toggle']"); pg.wait_for_timeout(200)
    pg.click("#fcAdvTog"); pg.wait_for_timeout(500)
    ok(f"[{T}] ⑪ 手機進階：分段列可橫向滑（不撐破版面）、整頁沒有橫捲", J(pg, "() => document.documentElement.scrollWidth <= innerWidth + 1"))
    ctx.close()

    # ---------------------------------------------------------------- 網址還原
    ctx, pg = open_page(1440, 900, h="#flowcheck?v=wheel&w=20&a=cases")
    s4 = st(pg)
    ok(f"[{T}] ⑫ 網址 ?v=wheel&w=20&a=cases 開頁：輪盤、20 日、進階展開在「驗證與案例」", s4["view"] == "wheel" and s4["win"] == 20 and J(pg, "() => document.getElementById('fcAdv').classList.contains('open') && !document.getElementById('fcAP_cases').hidden"), s4)
    ctx.close()


register("流向驗證v3", lambda pg, b, base, code: t_flowcheck_v3(b, base))
