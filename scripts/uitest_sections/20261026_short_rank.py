# 驗收段落「融券排行1026」（site/marketfut.js，#market/credit → 個股排行）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-26：「需要新增一個融券的」。用假的 market_fut.json（page.route 攔截）真的操作：
# 進「個股排行」→ 分段開關「融資／融券」預設融資 → 按「融券」：標題換成「融券增減排行」、列換成融券那批代號、
# 增加 8 列紅（up）／減少 8 列綠（down）、數字是千張、每列有長條 → 按回「融資」列換回來；
# 「?」說明有寫融券；族群篩選在融券也有效；1440 一頁看完（16 列在第一屏內）；390 沒有橫向捲軸；
# 沒有 short_rank 的舊資料 → 「融券」鈕反灰＋title。

def _sr_fake(with_short=True):
    import datetime as _dt
    days, d = [], _dt.date(2026, 6, 1)
    while len(days) < 120:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += _dt.timedelta(days=1)
    rows = [{"d": x, "ratio": 165 + (i % 30) * .5, "margin_lots": 7.5e6, "margin_chg": 1000.0, "margin_yi": 2400.0, "cap_yi": 4000.0,
             "short_lots": 3e5, "short_chg": 200.0, "taiex": 19000 + i * 20.0} for i, x in enumerate(days)]
    rk = {"d": days[-1], "rows": [{"code": f"1{i:03d}", "name": f"資甲{i}", "chg": 9000.0 - i * 500, "g": ["族群A"]} for i in range(10)]
          + [{"code": f"2{i:03d}", "name": f"資乙{i}", "chg": -9000.0 + i * 500, "g": ["族群B"]} for i in range(10)]}
    sr = {"d": days[-1], "rows": [{"code": f"3{i:03d}", "name": f"券甲{i}", "chg": 4200.0 - i * 300, "bal": 9000.0, "g": ["族群A" if i % 2 else "族群C"]} for i in range(10)]
          + [{"code": f"4{i:03d}", "name": f"券乙{i}", "chg": -3900.0 + i * 300, "bal": 5000.0, "g": ["族群C"]} for i in range(10)]}
    m = {"rows": rows, "asof": days[-1], "rank": rk}
    if with_short:
        m["short_rank"] = sr
    return {"margin": m}


_SR_READ = """() => [...document.querySelectorAll('#mfRankBody .mf-rank')].map(col => [...col.querySelectorAll('a.mf-rk')].map(a => ({
  code: (a.getAttribute('href') || '').split('/').pop(), val: (a.querySelector('.mf-val') || {}).textContent || '',
  cls: ((a.querySelector('.mf-sb i') || {}).className || ''), bottom: a.getBoundingClientRect().bottom })))"""


def t_short_rank_1026(b, base, code):
    T = "融券排行1026"
    errs = []
    for w, with_short in ((1440, True), (390, True), (1440, False)):
        mob = w <= 640
        tag = f"{T}（{w}{'' if with_short else '，舊資料沒有融券'}）"
        fake = json.dumps(_sr_fake(with_short))
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/data/market_fut.json*", (lambda f: (lambda r: r.fulfill(status=200, content_type="application/json", body=f)))(fake))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#market/credit", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            pg.click("#mfTab button[data-k='rank']"); pg.wait_for_timeout(400)
            seg = pg.locator("#mfRkSeg button")
            ok(f"[{tag}] 個股排行有「融資／融券」分段開關", seg.count() == 2 and seg.nth(0).inner_text().strip() == "融資" and seg.nth(1).inner_text().strip() == "融券", seg.count())
            ok(f"[{tag}] 預設是融資、標題「融資增減排行」", "on" in (seg.nth(0).get_attribute("class") or "") and "融資增減排行" in pg.inner_text(".mf-rkhead"))
            before = pg.evaluate(_SR_READ)
            if not with_short:
                btn = pg.locator("#mfRkSeg button[data-k='short']")
                ok(f"★ {tag}：沒有融券資料 → 「融券」鈕反灰＋title 寫原因", btn.is_disabled() and bool(btn.get_attribute("title")), btn.get_attribute("title"))
                btn.click(force=True); pg.wait_for_timeout(300)
                ok(f"[{tag}] 按反灰的鈕不換內容", pg.evaluate(_SR_READ) == before)
                continue
            pg.click("#mfRkSeg button[data-k='short']"); pg.wait_for_timeout(400)
            after = pg.evaluate(_SR_READ)
            ok(f"★ {tag}：按「融券」→ 標題換成「融券增減排行」", "融券增減排行" in pg.inner_text(".mf-rkhead") and "融資增減排行" not in pg.inner_text(".mf-rkhead"))
            ok(f"★ {tag}：列真的換成融券那批（增加 3xxx、減少 4xxx，各 8 列）",
               len(after) == 2 and len(after[0]) == 8 and len(after[1]) == 8 and all(x["code"].startswith("3") for x in after[0]) and all(x["code"].startswith("4") for x in after[1]),
               [[x["code"] for x in col[:3]] for col in after])
            ok(f"★ {tag}：增加紅（up）、減少綠（down），單位千張、由大到小", all(x["cls"] == "up" for x in after[0]) and all(x["cls"] == "down" for x in after[1])
               and after[0][0]["val"].startswith("+4.20") and "千張" in after[0][0]["val"] and after[1][0]["val"].startswith("-3.90"), [after[0][0]["val"], after[1][0]["val"]])
            ok(f"[{tag}] 只有一個「融券增減排行」標題（不重複）", pg.evaluate("() => (document.querySelector('#mf-credit').innerText.match(/融券增減排行/g) || []).length") == 1)
            if not mob:
                ok(f"★ {tag}：1440×900 一頁看完（16 列都在第一屏內）", max(x["bottom"] for col in after for x in col) <= 900, max(x["bottom"] for col in after for x in col))
            # 族群篩選在融券也有效：只選族群C → 增加那欄只剩偶數號（族群C）
            pg.click("#mfGroupDD .ddbtn"); pg.wait_for_timeout(250)
            cb = pg.locator("#mfGroupDD .ddlist input[data-n='族群C']")
            if cb.count():
                cb.first.check(); pg.wait_for_timeout(400)
                f2 = pg.evaluate(_SR_READ)
                ok(f"★ {tag}：族群篩選（族群C）在融券排行有效", f2 and f2[0] and all(int(x["code"][1:]) % 2 == 0 for x in f2[0]) and len(f2[0]) < 8, [x["code"] for x in f2[0]] if f2 else f2)
                cb.first.uncheck(); pg.wait_for_timeout(300)
            else:
                ok(f"[{tag}] 族群清單有族群C", False, pg.evaluate("() => (document.querySelector('#mfGroupDD .ddlist') || {}).innerHTML || ''")[:200])
            pg.keyboard.press("Escape"); pg.mouse.click(5, 5); pg.wait_for_timeout(200)
            pg.click("#mfRkSeg button[data-k='margin']"); pg.wait_for_timeout(400)
            back = pg.evaluate(_SR_READ)
            ok(f"★ {tag}：按回「融資」→ 列換回融資那批", [x["code"] for col in back for x in col] == [x["code"] for col in before for x in col])
            # 「?」說明有寫融券
            pg.click("#mf-credit .howbtn"); pg.wait_for_timeout(400)
            ok(f"[{tag}] 「?」說明有寫融券排行怎麼看", "融券增減排行" in pg.evaluate("() => (document.querySelector('#how-mf-credit') || {}).textContent || ''"))
            ok(f"[{tag}] 沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        finally:
            c.close()
    ok(f"{T}：沒有頁面例外", not errs, errs[:3])


register("融券排行1026", lambda pg, b, base, code: t_short_rank_1026(b, base, code))
