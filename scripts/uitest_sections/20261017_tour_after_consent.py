# 驗收段落「同意後平台導覽1017」—— 2026-10-17 同意條款之後直接開頁首「平台導覽」那一套（tour.js），不再跳舊的置中大視窗。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_lg_page()、_lg_ls()、_tour_wait()、_tour_inview()、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# Andy 10-17 原話：「平台導覽還停留在之前的版本，CEO 幫我更新，並且在同意之後，不用額外跳視窗，直接開啟上方平台導覽功能，客戶不需要看就會自動跳過」。
# 真人操作（1440 桌機、390 手機各一次；都用乾淨的瀏覽器＝localStorage 什麼都沒有、也不注入任何法律設定）：
#   1. 看到同意橫幅 → 按「同意並繼續」
#   2. 舊的置中大視窗（#lgTour／.lgmask）沒有出現；平台導覽（#twTour，全站導覽 site）自動開始、第一步框得到東西
#   3. 按「跳過導覽」→ 導覽整個關掉；tw.tour 已寫入
#   4. 重新整理 → 橫幅不再出現、導覽不再自動跑
#   5. 按頁首「平台導覽」（桌機 #twTourBtn；手機頂欄 🧭 → 小選單「平台導覽」）→ 再跑一次；Esc 能關、點變暗的遮罩也能關
#   6. 再按一次，逐步按「下一步」走到最後一步（「想再看一次，按這裡」）→ 按「完成」結束：
#      每一步框住的元素存在、在畫面內，說明卡不出畫面、不蓋住被框的元素，卡片字 ≥ 11px，一步都沒被跳過
#   7. （1440）在法律頁（#terms）上按同意 → 不把正在讀條文的人拉走；離開法律頁回總覽時才自動開
# 設 TW_TOUR1017_SHOTS=<資料夾> 時存截圖：同意後第一步、中間（個股頁那步）、最後一步。

T1017 = "同意後平台導覽1017"

T1017_CARD = """() => { const c = document.getElementById('twTourCard'); if (!c) return null;
  const fs = [...c.querySelectorAll('*')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
    .map(e => parseFloat(getComputedStyle(e).fontSize));
  const sk = document.getElementById('twTourSkip'), r = sk ? sk.getBoundingClientRect() : null;
  return { minFs: fs.length ? Math.min(...fs) : 0, skip: sk ? sk.textContent.trim() : '', skipVis: !!r && r.width > 40 && r.height >= 30,
           skipBorder: sk ? parseFloat(getComputedStyle(sk).borderTopWidth) : 0, sw: document.documentElement.scrollWidth - innerWidth }; }"""

T1017_OLD = "() => !!document.querySelector('#lgTour, #lgTourMask, .lgmask')"


def _t1017_hit(st):
    """說明卡跟被框住的元素有沒有疊在一起（place＝over 是目標比半個畫面還大、刻意疊在角落，不算）。"""
    t, c = st.get("target"), st["card"]
    if not t or st.get("place") == "over":
        return False
    return min(t["r"], c["r"]) - max(t["l"], c["l"]) > 2 and min(t["b"], c["b"]) - max(t["t"], c["t"]) > 2


def _t1017_open_site(pg, mob):
    """按頁首的平台導覽入口：桌機右上角「平台導覽」；手機頂欄 🧭（這一頁有本頁導覽時先跳兩列小選單，選「平台導覽」）。"""
    if not mob:
        pg.click("#twTourBtn")
    else:
        pg.click("#twPageTourBtn"); pg.wait_for_timeout(400)
        if pg.locator("#twPickSite").count() and pg.locator("#twPickSite").is_visible():
            pg.click("#twPickSite")
    return wait_until(pg, "() => { const s = window.TwTour && TwTour.state(); return !!s && s.active && s.tour === 'site' && !s.busy && s.i >= 0; }", 12000)


def t_tour_after_consent_1017(b, base):
    shots = os.environ.get("TW_TOUR1017_SHOTS", "")
    if shots:
        os.makedirs(shots, exist_ok=True)
    n0 = len(fails)
    for w, h, mob in ((1440, 950, False), (390, 844, True)):
        tag = f"【{T1017}】{w}"
        ctx, pg = _lg_page(b, w, h, mobile=mob)
        pg.goto(base + "#overview", wait_until="networkidle"); pg.wait_for_timeout(2500)
        ok(f"{tag}：乾淨的瀏覽器 → localStorage 沒有 tw.consent／tw.tour、同意橫幅出現",
           _lg_ls(pg, "tw.consent") is None and _lg_ls(pg, "tw.tour") is None and pg.locator("#lgBanner").count() == 1,
           [_lg_ls(pg, "tw.consent"), _lg_ls(pg, "tw.tour"), pg.locator("#lgBanner").count()])
        ok(f"{tag}：還沒同意之前，導覽沒有自己跑", not pg.evaluate("() => !!(window.TwTour && TwTour.state().active)"))

        # ---- 1～2. 按同意 → 舊的置中大視窗不出現、平台導覽自動開始
        pg.click("#lgAccept")
        started = wait_until(pg, "() => { const s = window.TwTour && TwTour.state(); return !!s && s.active && !s.busy && s.i >= 0; }", 12000)
        st = _tour_wait(pg) if started else pg.evaluate(TOUR_ST)
        ok(f"{tag}：按「同意並繼續」→ 舊的置中大視窗（平台導覽／四步看懂今天的資金）沒有出現",
           not pg.evaluate(T1017_OLD) and "四步看懂今天的資金" not in pg.inner_text("body"), pg.evaluate(T1017_OLD))
        ok(f"{tag}：按「同意並繼續」→ 頁首那套平台導覽（全站導覽）自動開始、橫幅收掉",
           bool(started) and st and st.get("active") and st.get("tour") == "site" and pg.locator("#lgBanner").count() == 0,
           st and {k: st.get(k) for k in ("active", "tour", "i", "title", "sel")})
        if st and st.get("active"):
            c_ok, h_ok = _tour_inview(st)
            ok(f"{tag}：自動開始的第一步「{st['title']}」框住的元素在畫面內、說明卡不出畫面也不蓋住它",
               st["i"] == 0 and c_ok and h_ok and not _t1017_hit(st), (st["sel"], st["target"], st["card"], st["place"]))
            cd = pg.evaluate(T1017_CARD)
            ok(f"{tag}：說明卡上有明顯的「跳過導覽」鈕（有框、夠大）、卡片字 ≥ 11px、沒有橫向捲軸",
               cd and cd["skip"] == "跳過導覽" and cd["skipVis"] and cd["skipBorder"] >= 1 and cd["minFs"] >= 11 and cd["sw"] <= 1, cd)
            ok(f"{tag}：自動開始的同時 tw.tour 已寫入（導覽跑到一半重新整理也不會再自動跑）", (_lg_ls(pg, "tw.tour") or "") not in ("", "ERR"), _lg_ls(pg, "tw.tour"))
            if shots:
                pg.screenshot(path=os.path.join(shots, f"{w}_1_同意後第一步.png"))

        # ---- 3. 按「跳過導覽」→ 整個關掉
        if pg.locator("#twTourSkip").count():
            pg.click("#twTourSkip"); pg.wait_for_timeout(400)
        ok(f"{tag}：按「跳過導覽」→ 遮罩與說明卡整個消失",
           pg.locator("#twTour").count() == 0 and not pg.evaluate("() => TwTour.state().active"), pg.locator("#twTour").count())
        ok(f"{tag}：跳過之後畫面上沒有任何導覽或彈窗殘留", not pg.evaluate(T1017_OLD) and pg.locator("#lgBanner").count() == 0)

        # ---- 4. 重新整理 → 不再自動跑
        pg.reload(wait_until="networkidle"); pg.wait_for_timeout(3000)
        ok(f"{tag}：重新整理 → 橫幅不再出現、導覽不再自動跑、舊視窗也沒有",
           pg.locator("#lgBanner").count() == 0 and not pg.evaluate("() => TwTour.state().active") and not pg.evaluate(T1017_OLD))

        # ---- 5. 按頁首「平台導覽」→ 再跑；Esc 關、點遮罩關
        got = _t1017_open_site(pg, mob)
        ok(f"{tag}：按頁首「平台導覽」{'（頂欄 🧭 → 平台導覽）' if mob else ''}→ 全站導覽又開始", bool(got), pg.evaluate(TOUR_ST))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
        ok(f"{tag}：導覽中按 Esc → 結束", pg.locator("#twTour").count() == 0 and not pg.evaluate("() => TwTour.state().active"))
        got = _t1017_open_site(pg, mob)
        if got:
            st = _tour_wait(pg)
            # 點變暗的遮罩：挑一個不在說明卡、也不在聚光燈框裡的點
            pt = pg.evaluate("""() => { const s = TwTour.state(), c = s.card, h = s.hole; const W = innerWidth, H = innerHeight;
                const cand = [[W / 2, H / 2], [W - 20, H / 2], [20, H - 20], [W / 2, 20], [W - 20, H - 20], [W / 2, H * 0.3]];
                const inR = (p, r) => p[0] >= r.l - 4 && p[0] <= r.r + 4 && p[1] >= r.t - 4 && p[1] <= r.b + 4;
                const p = cand.find(p => !inR(p, c) && !inR(p, h)); return p || null; }""")
            if pt:
                pg.mouse.click(pt[0], pt[1]); pg.wait_for_timeout(400)
            ok(f"{tag}：點變暗的遮罩（說明卡以外）→ 導覽結束（客戶不想看，點哪裡都能離開）",
               bool(pt) and pg.locator("#twTour").count() == 0 and not pg.evaluate("() => TwTour.state().active"),
               {"點": pt, "還在": pg.evaluate("() => TwTour.state().active")})
            ok(f"{tag}：點遮罩那一下沒有穿透到底下的頁面（網址沒變）", pg.evaluate("() => location.hash") == st.get("hash"),
               [st.get("hash"), pg.evaluate("() => location.hash")])
        else:
            ok(f"{tag}：第二次按「平台導覽」開得起來", False, pg.evaluate(TOUR_ST))

        # ---- 6. 再開一次，逐步走到最後一步
        pg.goto(base + "#overview", wait_until="networkidle"); pg.wait_for_timeout(1500)
        got = _t1017_open_site(pg, mob)
        rows, seen = [], []
        for _ in range(26):
            st = _tour_wait(pg)
            if not st or not st.get("active"):
                break
            if st["i"] in seen:
                ok(f"{tag}：按「下一步」不會停在原地（第 {st['i'] + 1} 步重複）", False, st)
                break
            seen.append(st["i"]); rows.append(st)
            if shots and st["title"].startswith("個股頁"):
                pg.screenshot(path=os.path.join(shots, f"{w}_2_中間_個股頁.png"))
            if pg.evaluate("() => document.getElementById('twTourNext').textContent.trim()") == "完成":
                if shots:
                    pg.screenshot(path=os.path.join(shots, f"{w}_3_最後一步.png"))
                pg.click("#twTourNext"); pg.wait_for_timeout(500)
                break
            pg.click("#twTourNext")
        titles = [r["title"] for r in rows]
        li = pg.evaluate("() => TwTour.last()") or {}
        need = 17 if mob else 16
        ok(f"{tag}：全站導覽一路按到最後一步「想再看一次，按這裡」、按「完成」關閉（走了 {len(rows)} 步，一步都沒被跳過）",
           bool(got) and len(rows) >= need and titles and titles[-1] == "想再看一次，按這裡" and li.get("why") == "done" and not li.get("skipped")
           and pg.locator("#twTour").count() == 0, {"titles": titles, "last": li})
        for k in ("總覽", "精選文章", "財經日曆", "資金流向", "熱力圖", "產業地圖", "個股頁", "市場明細", "選股策略", "ETF", "週期統計", "自選", "搜尋", "會員與訂閱", "客服"):
            if not any(t.startswith(k) or k in t for t in titles):
                ok(f"{tag}：導覽內容有講到「{k}」", False, titles)
        bad_in, bad_hit = [], []
        for r in rows:
            c_ok, h_ok = _tour_inview(r)
            if not (c_ok and h_ok):
                bad_in.append((r["title"], r["sel"], r["target"], r["hole"], r["card"]))
            if _t1017_hit(r):
                bad_hit.append((r["title"], r["target"], r["card"], r["place"]))
        ok(f"{tag}：每一步框住的元素存在、在畫面內，說明卡不出畫面", not bad_in, bad_in[:3])
        ok(f"{tag}：每一步說明卡都不蓋住被框住的元素（文字不重疊）", not bad_hit, bad_hit[:3])
        stock = [r for r in rows if r["title"].startswith("個股頁")]
        ok(f"{tag}：「個股頁」那一步真的換到個股頁（#stock/…）、框住股票名稱與現價",
           bool(stock) and stock[0]["hash"].startswith("#stock/") and stock[0]["sel"] in ("#skIdent", "#mbQuote"), stock and stock[0]["sel"])
        ok(f"{tag}：最後一步框住的是頁首的平台導覽入口（{'🧭' if mob else '右上角「平台導覽」'}）",
           bool(rows) and rows[-1]["sel"] == ("#twPageTourBtn" if mob else "#twTourBtn"), rows and rows[-1]["sel"])
        ctx.close()

    # ---- 7. 在法律頁上按同意 → 不把人拉走；回到一般頁面才自動開
    ctx, pg = _lg_page(b, 1440, 950)
    pg.goto(base + "#terms", wait_until="networkidle"); pg.wait_for_timeout(1800)
    pg.click("#lgAccept"); pg.wait_for_timeout(1500)
    ok(f"【{T1017}】1440 在使用條款頁上按同意 → 還留在 #terms、導覽先不開（正在讀條文的人不被拉走）",
       pg.evaluate("() => location.hash") == "#terms" and not pg.evaluate("() => TwTour.state().active") and not pg.evaluate(T1017_OLD),
       [pg.evaluate("() => location.hash"), pg.evaluate("() => TwTour.state().active")])
    pg.click(".tab[data-view='overview']")
    got = wait_until(pg, "() => { const s = TwTour.state(); return s.active && s.tour === 'site'; }", 8000)
    ok(f"【{T1017}】1440 離開法律頁回總覽 → 這時才自動開平台導覽（只開這一次）", bool(got), pg.evaluate(TOUR_ST))
    if got:
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pg.click(".tab[data-view='flow']"); pg.wait_for_timeout(1500)
    ok(f"【{T1017}】1440 之後再換頁不會又自動開", not pg.evaluate("() => TwTour.state().active"))
    ctx.close()

    ok(f"【{T1017}】整段沒有 pageerror", not [f for f in fails[n0:] if "pageerror" in f], fails[n0:])


register(T1017, lambda pg, b, base, code: t_tour_after_consent_1017(b, base), after="法律上架1016")
