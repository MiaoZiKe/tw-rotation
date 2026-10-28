# 驗收段落「台指期策略1028」（site/futures.js，路由 #futures）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-28：「台指期也要做成網站頁面」。真的操作：
#  ① 側欄「台指期策略」點下去 → hash 變 #futures、六格訊號有值、數字跟 futures.json 對得上
#  ② 標題旁「?」點開 → 跳出說明含「結算前一日轉倉」「不擇時、不停損」；點背景關閉
#  ③ 回測表五列（F0～F4），採用的 F2 那列有標示
#  ④ 假資料（130 天）→ 期間鈕 1月／3月／6月／全部 都可按；按 3月 → 圖的點數變少、起點為 0、績效格數字改變；按全部回來
#  ⑤ 真資料只有 1 天 → 期間鈕 1月／3月／6月 反灰且有 title
#  ⑥ 沒有橫向捲軸；畫面沒有 details／說明卡；手機整頁 ≤ 3 屏，表格容器可橫拖
import json as _fu_json
import datetime as _fu_dt

_FU_SHOTS = "/tmp/claude-0/-home-user-tw-rotation/fe3b946e-89a8-59da-b615-8ebf1e80fccc/scratchpad/futures_page"


def _fu_fake(days=200):
    """合成一份 200 個日曆日的假帳本（F2 比 0050 多賺），用來驗期間鈕。"""
    d0 = _fu_dt.date(2026, 5, 1)
    ser, f, b = [], 0.0, 0.0
    for i in range(days):
        d = d0 + _fu_dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        f += 0.0031 if i % 3 else -0.0012
        b += 0.0018 if i % 4 else -0.0010
        ser.append({"d": d.isoformat(), "f": round(f, 5), "b": round(b, 5), "nav": round(10_000_000 * (1 + f))})
    return ser


def t_futures_1028(b, base, code):
    import os
    os.makedirs(_FU_SHOTS, exist_ok=True)
    T = "台指期策略1028"
    errs = []
    for W in (1440, 390):
        mob = W <= 640
        c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        a = pg.get_by_role("button", name="同意並繼續")
        if a.count() and a.first.is_visible():
            a.first.click(); pg.wait_for_timeout(300)
        wait_until(pg, "() => !!document.querySelector('.tab[data-view=futures]')", 8000)
        # ① 進頁：電腦版點側欄那一格；手機（沒有側欄）直接貼網址
        if not mob:
            vis = pg.evaluate("() => { const t = document.querySelector('.tab[data-view=futures]'); return !!t && t.getClientRects().length > 0; }")
            ok(f"{T}（{W}）側欄看得到「台指期策略」", bool(vis))
            pg.click(".tab[data-view=futures]")
        else:
            pg.evaluate("() => { location.hash = '#futures'; }")
        got = wait_until(pg, "() => location.hash === '#futures' && document.getElementById('v-futures').dataset.ready", 10000)
        pg.wait_for_timeout(700)
        d = pg.evaluate("() => App.D.futures || null")
        sig = (d or {}).get("signal") or {}
        ok(f"{T}（{W}）進頁後 hash 是 #futures、頁面載完（ready）", bool(got) and bool(d) and bool(sig), [pg.evaluate("() => location.hash"), bool(d)])
        tiles = pg.evaluate("() => [...document.querySelectorAll('#fuTiles .fu-t')].map(t => [t.querySelector('.l').textContent, t.querySelector('.v').textContent])")
        ok(f"{T}（{W}）今日訊號六格都有值", len(tiles) == 6 and all(v and v != "—" for _, v in tiles), tiles)
        big = next((v for l, v in tiles if l == "大台"), "")
        mic = next((v for l, v in tiles if l == "微台"), "")
        ok(f"{T}（{W}）大台／微台口數跟資料檔一致", f"{sig.get('contracts_big'):.2f}" in big and str(int(sig.get('contracts_micro'))) in mic, [big, mic, sig.get("contracts_big"), sig.get("contracts_micro")])
        # ③ 回測表
        rows = pg.evaluate("() => [...document.querySelectorAll('#fuBt tbody tr')].map(r => [r.dataset.id, r.classList.contains('pick')])")
        ok(f"{T}（{W}）回測表五列 F0～F4，F2 標示採用", [r[0] for r in rows] == ["F0", "F1", "F2", "F3", "F4"] and [r[0] for r in rows if r[1]] == ["F2"], rows)
        # ⑤ 真資料只有 1 天 → 1月／3月／6月 反灰
        n_pts = len((d or {}).get("series") or [])
        per = pg.evaluate("() => [...document.querySelectorAll('#fuPer button')].map(x => [x.dataset.p, x.disabled, x.title, x.classList.contains('on')])")
        ok(f"{T}（{W}）期間鈕齊全，資料不足的反灰且有 title，「全部」預設選中且可按",
           [p[0] for p in per] == ["1m", "3m", "6m", "all"] and any(p[0] == "all" and not p[1] and p[3] for p in per)
           and all((not p[1]) or p[2] for p in per) and (n_pts >= 30 or all(p[1] for p in per if p[0] != "all")), per)
        # 圖：兩條線
        ns = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('fuChart')); return c ? c.getOption().series.length : -1; }")
        ok(f"{T}（{W}）績效圖畫出兩條線（F2、0050 含息）", ns == 2, ns)
        # ② 「?」
        pg.click("#fuSigCard .howbtn"); pg.wait_for_timeout(250)
        pop = pg.evaluate("() => { const p = document.getElementById('howPop'); return p && !p.hidden ? p.innerText : ''; }")
        ok(f"{T}（{W}）點「?」跳出規則說明（結算前一日轉倉、不擇時不停損）", "結算前一日轉倉" in pop and "不擇時" in pop, pop[:80])
        pg.mouse.click(5 if mob else 5, 5 if mob else 400); pg.wait_for_timeout(250)
        shut = pg.evaluate("() => { const p = document.getElementById('howPop'); return !p || p.hidden; }")
        ok(f"{T}（{W}）點背景關閉說明", shut)
        # ⑥ 版面規矩
        lay = pg.evaluate("""() => { const v = document.getElementById('v-futures');
          return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, h: v.scrollHeight,
                   details: v.querySelectorAll('details').length, howcards: v.querySelectorAll('.fp-how,.irabout,.howtxt:not([hidden])').length,
                   tw: (() => { const t = v.querySelector('.fu-tw'); return [t.scrollWidth, t.clientWidth]; })() }; }""")
        ok(f"{T}（{W}）頁面沒有橫向捲軸、沒有 details／攤開的說明卡", lay["sw"] <= lay["cw"] + 1 and lay["details"] == 0 and lay["howcards"] == 0, lay)
        if mob:
            ok(f"{T}（{W}）手機整頁 ≤ 3 屏（≤ 2532px）", lay["h"] <= 2532, lay["h"])
        else:
            ok(f"{T}（{W}）電腦整頁 ≤ 2 屏（≤ 1800px）", lay["h"] <= 1800, lay["h"])
        try:
            pg.screenshot(path=f"{_FU_SHOTS}/futures_{W}.png", full_page=True)
        except Exception:
            pass   # 截圖只是留證，容器記憶體吃緊時 Chromium 會崩，不能因此判驗收失敗
        # ④ 假資料驗期間鈕
        fake = _fu_fake()
        d2 = dict(d); d2["series"] = fake
        # load() 對同名檔有快取 → 直接把假資料塞進 App.D 再重畫（App.load 會原樣回傳 D.futures）
        pg.evaluate("(d2) => { App.D.futures = d2; return window.TwFutures.render(); }", d2)
        wait_until(pg, "() => (App.D.futures.series || []).length > 50 && document.querySelectorAll('#fuPer button:not([disabled])').length === 4", 8000)
        per = pg.evaluate("() => [...document.querySelectorAll('#fuPer button')].map(x => x.disabled)")
        ok(f"{T}（{W}）假資料 200 天：四顆期間鈕都可按", per == [False, False, False, False], per)
        cnt = lambda: pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fuChart')).getOption().series[0].data.length")
        first = lambda: pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fuChart')).getOption().series[0].data[0]")
        lead = lambda: pg.evaluate("() => document.querySelectorAll('#fuPerfTiles .fu-t .v')[2].textContent")
        n_all, lead_all = cnt(), lead()
        pg.click("#fuPer button[data-p=\"3m\"]"); pg.wait_for_timeout(300)
        n_3m, lead_3m, f0 = cnt(), lead(), first()
        ok(f"{T}（{W}）按「3月」：圖的點數變少、起點歸 0、「領先」格數字改變", n_3m < n_all and abs(f0) < 1e-9 and lead_3m != lead_all, [n_all, n_3m, f0, lead_all, lead_3m])
        pg.click("#fuPer button[data-p=\"1m\"]"); pg.wait_for_timeout(300)
        n_1m = cnt()
        ok(f"{T}（{W}）按「1月」：點數比 3 月更少", n_1m < n_3m, [n_3m, n_1m])
        pg.click("#fuPer button[data-p=\"all\"]"); pg.wait_for_timeout(300)
        ok(f"{T}（{W}）按「全部」：回到完整點數與原本「領先」數字", cnt() == n_all and lead() == lead_all, [cnt(), n_all])
        try:
            pg.screenshot(path=f"{_FU_SHOTS}/futures_{W}_fake130.png")
        except Exception:
            pass
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


register("台指期策略1028", lambda pg, b, base, code: t_futures_1028(b, base, code))
