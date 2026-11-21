# 驗收段落「盤前消息1026」（site/articles.js，#articles/premarket）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-26：精選文章要有「盤前消息」分頁。用假的 articles/premarket.json（page.route 攔截，3 天）真的操作：
# 點分頁 → hash 變 #articles/premarket、只看到最新一天展開 5 則（分類色塊、可點連結 target=_blank）→
# 按「複製整包」剪貼簿內容＝日期標題＋每則「分類｜標題」換行連結 → 點較早日期列在原地展開 → 「看更早」→
# 切回「全部文章」盤前面板收起、文章清單回來 → 沒資料（空 days / 404）顯示空狀態且沒有頁面例外 → 390 無橫向捲軸、字 ≥ 11px。

def _pm_fake(days_n=3):
    cats = ["總經", "事件", "科技", "科技", "新聞"]
    days = []
    for k in range(days_n):
        d = f"2026-10-{27 - k:02d}"
        days.append({"date": d, "items": [{"cat": cats[i], "title": f"{d} 測試標題{i}：台積電與美債殖利率", "url": f"https://example.com/{d}/{i}",
                                            "source": "鉅亨", "time": f"{d}T08:{10 + i}:00+08:00"} for i in range(5)]})
    return {"updated": "2026-10-26", "days": days}


def t_premarket_1026(b, base, code):
    T = "盤前消息1026"
    errs = []
    for w, mode in ((1440, "data"), (390, "data"), (1440, "empty"), (1440, "404")):
        mob = w <= 640
        tag = f"{T}（{w}{'' if mode == 'data' else '，' + mode}）"
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        try: c.grant_permissions(["clipboard-read", "clipboard-write"])
        except Exception: pass
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        if mode == "data":
            body = json.dumps(_pm_fake(9))
            c.route("**/articles/premarket.json*", (lambda f: (lambda r: r.fulfill(status=200, content_type="application/json", body=f)))(body))
        elif mode == "empty":
            c.route("**/articles/premarket.json*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"updated":"","days":[]}'))
        else:
            c.route("**/articles/premarket.json*", lambda r: r.fulfill(status=404, body="no"))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#articles", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=premarket]')", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            tab = pg.locator("#artCats>button[data-cat=premarket]")
            ok(f"[{tag}] 精選文章有「盤前消息」分頁", "盤前" in tab.inner_text() or w <= 640, tab.inner_text())
            tab.click(); pg.wait_for_timeout(500)
            ok(f"[{tag}] 點分頁 → #articles/premarket、分頁亮起、文章清單區收起", pg.evaluate("() => location.hash") == "#articles/premarket"
               and "on" in (tab.get_attribute("class") or "") and not pg.locator("#artList").is_visible())
            if mode != "data":
                wait_until(pg, "() => !!document.querySelector('#artPreEmpty')", 8000)
                ok(f"★ {tag}：沒資料 → 空狀態一句話、沒有卡片", "尚無盤前消息" in pg.inner_text("#artPre") and pg.locator("#artPre .pmday").count() == 0)
                continue
            wait_until(pg, "() => document.querySelectorAll('#artPre .pmday').length > 0", 8000)
            days = pg.locator("#artPre .pmday")
            ok(f"★ {tag}：先列 7 天（共 9 天）、只有最新一天展開、有『看更早』", days.count() == 7 and pg.locator("#artPre .pmday.open").count() == 1
               and "open" in (days.nth(0).get_attribute("class") or "") and pg.locator("#artPreMore").count() == 1, days.count())
            items = days.nth(0).locator(".pmi")
            ok(f"★ {tag}：最新一天看到 5 則、分類色塊依序 總經／事件／科技／科技／新聞", items.count() == 5
               and [items.nth(i).locator(".pmk").inner_text() for i in range(5)] == ["總經", "事件", "科技", "科技", "新聞"])
            lk = items.nth(0).locator("a.tt")
            ok(f"★ {tag}：標題是新分頁開的連結（_blank＋noopener）", lk.get_attribute("href") == "https://example.com/2026-10-27/0" and lk.get_attribute("target") == "_blank"
               and "noopener" in (lk.get_attribute("rel") or ""))
            colors = pg.evaluate("() => [...document.querySelectorAll('#artPre .pmday.open .pmk')].map(e => getComputedStyle(e).backgroundColor)")
            ok(f"[{tag}] 四種分類色塊顏色兩兩不同", len(set(colors)) == 4, colors)
            ok(f"[{tag}] 標題列沒有重複標題（卡內不再寫『盤前消息』）", "盤前消息" not in pg.inner_text("#artPre"))
            # 複製整包
            btn = days.nth(0).locator(".pmcp")
            btn.click(); pg.wait_for_timeout(500)
            clip = pg.evaluate("async () => { try { return await navigator.clipboard.readText(); } catch (e) { return 'ERR ' + e; } }")
            if clip.startswith("ERR"):
                clip = btn.get_attribute("data-copied") or ""
            want = "【台股盤前消息｜2026-10-27】\n" + "\n".join(f"{n + 1}. {c_}｜2026-10-27 測試標題{n}：台積電與美債殖利率\nhttps://example.com/2026-10-27/{n}" for n, c_ in enumerate(["總經", "事件", "科技", "科技", "新聞"]))
            ok(f"★ {tag}：按『複製整包』→ 剪貼簿＝日期標題＋每則『分類｜標題』與連結（共 {len(clip.splitlines())} 行）", clip == want, clip[:200])
            ok(f"[{tag}] 按鈕回饋『已複製』", "已複製" in btn.inner_text())
            # 較早日期在原地展開
            before_y = pg.evaluate("() => scrollY")
            days.nth(1).locator(".pmt").click(); pg.wait_for_timeout(300)
            ok(f"★ {tag}：點較早日期列 → 原地展開 5 則（hash 不變）", days.nth(1).locator(".pmi").first.is_visible() and pg.evaluate("() => location.hash") == "#articles/premarket")
            days.nth(1).locator(".pmt").click(); pg.wait_for_timeout(200)
            ok(f"[{tag}] 再點一次 → 收合", not days.nth(1).locator(".pmi").first.is_visible())
            pg.click("#artPreMore"); pg.wait_for_timeout(300)
            ok(f"★ {tag}：『看更早』→ 天數 9、按鈕消失", pg.locator("#artPre .pmday").count() == 9 and pg.locator("#artPreMore").count() == 0)
            # 「?」
            pg.click("#artCard .howbtn"); pg.wait_for_timeout(400)
            ok(f"[{tag}] 「?」說明是盤前消息那份（寫到所以怎麼用）", "複製整包" in pg.evaluate("() => (document.querySelector('#how-artpre') || {}).textContent || ''") and pg.evaluate("() => document.querySelector('#artCard .howbtn').dataset.how") == "artpre")
            pg.keyboard.press("Escape"); pg.mouse.click(5, 5); pg.wait_for_timeout(200)
            ok(f"[{tag}] 沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
            tiny = pg.evaluate("() => [...document.querySelectorAll('#artPre *')].filter(e => e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && parseFloat(getComputedStyle(e).fontSize) < 11).map(e => e.textContent.trim().slice(0, 12))")
            ok(f"[{tag}] 沒有 < 11px 的字", not tiny, tiny)
            # 10-28 Andy「這邊沒對齊 版面也不好」：標題欄右緣一致、標籤等寬、標題不再被 .tw 框、來源時間欄固定寬靠右、箭頭在日期左邊
            al = pg.evaluate("""() => {
              const q = (s) => [...document.querySelectorAll('#artPre .pmday.open ' + s)];
              const r = (e) => e.getBoundingClientRect();
              const w = q('.pmw'), k = q('.pmk'), m = q('.sm');
              const day = document.querySelector('#artPre .pmday.open');
              return {n: w.length, rights: new Set(w.map(e => Math.round(r(e).right))).size, kw: new Set(k.map(e => Math.round(r(e).width))).size,
                bord: w.some(e => parseFloat(getComputedStyle(e).borderTopWidth) > 0),
                smw: new Set(m.map(e => Math.round(r(e).width))).size, smr: new Set(m.map(e => Math.round(r(e).right))).size,
                topgap: Math.max(...w.map((e, i) => Math.abs(r(e.querySelector('.tt')).top - r(k[i]).top))),
                chev: r(day.querySelector('.pc')).left < r(day.querySelector('.pd')).left,
                cp: r(day.querySelector('.pmcp')).right - r(day.querySelector('.pmh')).right,
                below: m.length ? m.every((e, i) => r(e).top >= r(w[i]).bottom - 1) : false};
            }""")
            ok(f"★ {tag}：標題欄右緣一致、標籤等寬、標題無外框", al["n"] == 5 and al["rights"] == 1 and al["kw"] == 1 and not al["bord"], al)
            ok(f"★ {tag}：標題與標籤上緣對齊（≤ 3px）、箭頭在日期左邊、複製整包靠右", al["topgap"] <= 3 and al["chev"] and al["cp"] >= -12, al)
            if not mob:
                ok(f"★ {tag}：來源時間欄等寬且右緣對齊", al["smw"] == 1 and al["smr"] == 1, al)
            else:
                ok(f"★ {tag}：手機來源時間在標題下一行", al["below"], al)
            if not mob:
                r = pg.evaluate("() => { const e = document.querySelector('#artPre .pmday.open').getBoundingClientRect(); return e.bottom; }")
                ok(f"★ {tag}：1440×900 最新一天整張卡在第一屏內", r <= 900, r)
            else:
                ok(f"[{tag}] 手機五個分頁都在畫面內", pg.evaluate("() => [...document.querySelectorAll('#artCats>button')].every(b => { const r = b.getBoundingClientRect(); return r.left >= -1 && r.right <= 391; })"))
            # 切回全部文章
            pg.click("#artCats>button[data-cat=all]"); pg.wait_for_timeout(500)
            ok(f"★ {tag}：切回『全部文章』→ 盤前面板收起、文章清單回來", pg.locator("#artPre").is_hidden() and pg.locator("#artList").is_visible()
               and pg.evaluate("() => document.querySelector('#artCard .howbtn').dataset.how") == "artlist")
        finally:
            c.close()
    ok(f"{T}：沒有頁面例外", not errs, errs[:3])


register("盤前消息1026", lambda pg, b, base, code: t_premarket_1026(b, base, code))
