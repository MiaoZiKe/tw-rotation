# 驗收段落「個股獲利一屏1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 個股獲利一屏1019（Andy 10-19：「個股-獲利這分頁內容需要如圖那範圍內，幫我上下調整一下」）
# 1710×915 與 1440×820：真的點個股頁的「獲利」分頁，把 KPI 列捲到頁首正下方（跟 Andy 截圖同一個看法），
#   ① 最後一張卡（第二排兩張卡）的底部 ≤ 視窗底部 —— 整個分頁一個畫面看完、不用捲
#   ② 四張卡都還在、寬度配置沒變（第一排河流 8｜每季 4、第二排 EPS 7｜明細 5，同排等高）
#   ③ 三張圖的 Y 軸刻度間距 ≥ 14px（刻度字 11～12px，間距再小就疊在一起）、圖高 ≥ 150px
#   ④ KPI 列、河流圖讀數塊、本益比位置框裡的文字兩兩不重疊，字 ≥ 11px
#   ⑤ 切到「年」再切回「季」，EPS 圖照樣在卡內、卡底仍 ≤ 視窗底（切換不會把版面撐高）


def t_stock_profit_fit_1019(b, base, code):
    T = "個股獲利一屏1019"
    errs: list[str] = []
    shots = os.environ.get("TW_PROFIT_FIT_SHOT")
    stock = "4939"
    for (w, h) in ((1710, 915), (1440, 820)):
        c = b.new_context(viewport={"width": w, "height": h})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + f"#stock/{stock}", wait_until="domcontentloaded")
        if not wait_until(pg, "() => document.querySelectorAll('#stockTabs button').length > 0", 15000):
            ok(f"{T}（{w}×{h}）：個股頁有分頁鈕", False); c.close(); continue
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        btn = pg.locator("#stockTabs button", has_text="獲利").first
        if not btn.count():
            ok(f"{T}（{w}×{h}）：有「獲利」分頁", False); c.close(); continue
        btn.click()
        wait_until(pg, "() => { const e = document.getElementById('profitChart'); return !!e && !!window.echarts && !!echarts.getInstanceByDom(e); }", 10000)
        pg.wait_for_timeout(1500)
        # 把 KPI 列捲到頁首正下方（Andy 截圖的看法），再量
        # 上方 K 線區還在載入時頁面會長高、把 KPI 列推下去，所以捲完要等它「停在頁首下方」才量（4 組平行跑時實際踩到）
        SCROLL = """() => { const k = document.querySelector('#profGrid').previousElementSibling;
            const hd = document.getElementById('l4Head'); const hh = hd ? hd.getBoundingClientRect().height : 0;
            window.scrollTo(0, k.getBoundingClientRect().top + scrollY - hh - 8);
            return Math.abs(k.getBoundingClientRect().top - hh - 8) < 2 ? 1 : 0; }"""
        for _ in range(20):
            if pg.evaluate(SCROLL):
                pg.wait_for_timeout(400)
                if pg.evaluate(SCROLL):
                    break
            pg.wait_for_timeout(400)
        m = pg.evaluate("""() => { const r = id => document.getElementById(id).getBoundingClientRect();
            const hd = document.getElementById('l4Head');
            const kv = document.querySelector('#profGrid').previousElementSibling.getBoundingClientRect();
            const ids = ['peRiverCard','peQCard','profitCard','profitTblCard'];
            const o = { ih: innerHeight, hh: hd ? hd.getBoundingClientRect().height : 0, kvTop: kv.top, cards: {} };
            ids.forEach(i => { const b = r(i); o.cards[i] = [b.left, b.top, b.width, b.height, b.bottom]; });
            o.need = Math.max(...ids.map(i => r(i).bottom)) - kv.top + o.hh + 8;   // 不靠目前捲到哪：KPI 頂到最後一張卡底＋頁首
            return o; }""")
        cd = m["cards"]
        last = max(v[4] for v in cd.values())
        ok(f"{T}（{w}×{h}）：KPI 列捲到頁首下方時，最後一張卡底部 ≤ 視窗底（{round(last)} ≤ {m['ih']}）",
           last <= m["ih"] and m["need"] <= m["ih"], m)
        rv, pq, pc, pt = cd["peRiverCard"], cd["peQCard"], cd["profitCard"], cd["profitTblCard"]
        ok(f"{T}（{w}×{h}）：寬度配置不變（第一排河流｜每季、第二排 EPS｜明細，同排等高、左寬右窄）",
           abs(rv[1] - pq[1]) < 2 and abs(rv[3] - pq[3]) < 2 and abs(pc[1] - pt[1]) < 2 and abs(pc[3] - pt[3]) < 2
           and pq[0] > rv[0] and pt[0] > pc[0] and rv[2] > pq[2] * 1.6 and pc[2] > pt[2] * 1.2 and pc[1] > rv[1] + rv[3] - 2, cd)
        ax = pg.evaluate("""() => ['peChart','peQ','profitChart'].map(id => {
            const d = document.getElementById(id); const ins = d && window.echarts && echarts.getInstanceByDom(d);
            if (!ins) return [id, 0, 0];
            let minGap = 999; const md = ins.getModel(); let i = 0;
            while (true) { const ya = md.getComponent('yAxis', i); if (!ya) break;
              const cs = ya.axis.getTicksCoords().map(t => t.coord).sort((a, b) => a - b);
              for (let k = 1; k < cs.length; k++) minGap = Math.min(minGap, cs[k] - cs[k - 1]); i++; }
            return [id, Math.round(d.getBoundingClientRect().height), Math.round(minGap)]; })""")
        ok(f"{T}（{w}×{h}）：三張圖高 ≥ 150px、Y 軸刻度間距 ≥ 14px（刻度字不疊）",
           all(a[1] >= 150 and a[2] >= 14 for a in ax), ax)
        tx = pg.evaluate("""() => { const roots = [document.querySelector('#profGrid').previousElementSibling,
              document.getElementById('peNote'), document.querySelector('#peQCard .psprof')].filter(Boolean);
            const leaves = []; roots.forEach(rt => rt.querySelectorAll('*').forEach(e => {
              if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
              const rg = document.createRange(); rg.selectNodeContents(e);
              [...rg.getClientRects()].forEach(b => { if (b.width > 1 && b.height > 1) leaves.push([e, b]); }); }));
            const bad = []; let small = [];
            leaves.forEach(([e]) => { const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 11) small.push(e.textContent.trim().slice(0, 12) + ':' + fs); });
            for (let i = 0; i < leaves.length; i++) for (let j = i + 1; j < leaves.length; j++) {
              const [ea, a] = leaves[i], [eb, c] = leaves[j];
              if (ea.contains(eb) || eb.contains(ea)) continue;
              const ox = Math.min(a.right, c.right) - Math.max(a.left, c.left), oy = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
              if (ox > 2 && oy > 2) bad.push(ea.textContent.trim().slice(0, 10) + '／' + eb.textContent.trim().slice(0, 10)); }
            return { n: leaves.length, bad: bad.slice(0, 5), small: small.slice(0, 5) }; }""")
        ok(f"{T}（{w}×{h}）：KPI 列、讀數塊、本益比位置框文字不重疊且 ≥ 11px（{tx['n']} 段字）",
           tx["n"] > 10 and not tx["bad"] and not tx["small"], tx)
        if shots:
            pg.screenshot(path=f"{shots}/profit_fit_{w}x{h}.png")
        # ⑤ 切到「年」再回「季」：圖要真的換（X 軸類別數變了），版面仍在一屏內
        n0 = pg.evaluate("() => (echarts.getInstanceByDom(document.getElementById('profitChart')).getOption().xAxis[0].data || []).length")
        pg.click("#profitMode button[data-v='y']"); pg.wait_for_timeout(600)
        n1 = pg.evaluate("() => (echarts.getInstanceByDom(document.getElementById('profitChart')).getOption().xAxis[0].data || []).length")
        last_y = pg.evaluate("""() => { const hd = document.getElementById('l4Head'); const hh = hd ? hd.getBoundingClientRect().height : 0;
            const kt = document.querySelector('#profGrid').previousElementSibling.getBoundingClientRect().top;
            return Math.max(...['profitCard','profitTblCard'].map(i => document.getElementById(i).getBoundingClientRect().bottom)) - kt + hh + 8; }""")
        pg.click("#profitMode button[data-v='q']"); pg.wait_for_timeout(600)
        n2 = pg.evaluate("() => (echarts.getInstanceByDom(document.getElementById('profitChart')).getOption().xAxis[0].data || []).length")
        ok(f"{T}（{w}×{h}）：切「年」圖真的換成年度（{n0}→{n1}→{n2}）、卡底仍 ≤ 視窗底",
           n0 > 0 and n1 > 0 and n1 != n0 and n2 == n0 and last_y <= m["ih"], [n0, n1, n2, last_y])
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("個股獲利一屏1019", lambda pg, b, base, code: t_stock_profit_fit_1019(b, base, code))
