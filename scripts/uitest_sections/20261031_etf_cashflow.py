# 驗收段落「ETF現金流1031」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== ETF現金流1031
# Andy 10-31 18:30（月配試算表單檔 ETF）：
#  ① 圖上選中的每一檔，右上要直接看到「現價・需要張數・需要金額」（原本只有一句話講一檔）
#  ② 「所有的清單都要有移除篩選功能」→ 搜尋框 ×、頻率標籤再點一次回「全部」
#  ③ 「報酬期間改成近 3 年，圖表沒有任何變化」→ 直條要隨期間重算、圖上標出目前期間；自訂日期也要生效
# 全部用真的點擊／輸入，每一步量畫面真的變了（右上表列數與內容、清單列數、直條資料 series）。

_SEL_JS = """() => ({
  n: +(document.getElementById('incBar').dataset.n || 0),
  codes: (document.getElementById('incBar').dataset.codes || '').split(',').filter(Boolean),
  rows: [...document.querySelectorAll('#incSel tbody tr')].map(r => ({ code: r.dataset.code, txt: r.textContent })),
  lots: (document.getElementById('incBar').dataset.lots || '').split(','),
  head: (document.querySelector('#incSel thead th') || {}).textContent || '',
  sq: (document.getElementById('incSQ') || {}).textContent || '',
})"""
_PER_JS = """() => ({ g: document.getElementById('incBar').dataset.groups || '', lab: (document.getElementById('incPerLab') || {}).textContent || '',
  per: (document.getElementById('incPerLab') || {}).dataset.per || '',
  ser: (() => { try { return JSON.stringify(echarts.getInstanceByDom(document.getElementById('incBar')).getOption().series.map(s => s.data)); } catch (e) { return ''; } })() })"""


def t_etf_cashflow_1031(b, base, code):
    T = "ETF現金流1031"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_ETFCF_SHOT")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#etf/inc", wait_until="networkidle")
        J("() => { try { Object.keys(localStorage).filter(k => k.startsWith('tw.etf.')).forEach(k => localStorage.removeItem(k)); } catch (e) {} }")
        pg.reload(wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, """() => { const el = document.getElementById('incBar'); return !!el && +el.dataset.n >= 3 && !!echarts.getInstanceByDom(el)
            && document.querySelectorAll('#incList .ilr').length >= 5 && window.TwEtfPage && window.TwEtfPage.state.series; }""", 30000)
        ok(f"{T}（{W}）：單檔圖畫出、清單 ≥ 5 列、週線載入（前置）", bool(ready))
        if not ready:
            c.close(); continue
        pg.wait_for_timeout(500)
        # ① 右上小表
        s0 = J(_SEL_JS)
        ok(f"{T}（{W}）①a：右上小表列數＝圖上檔數（{s0['n']}），每列有「張」與「NT$」", len(s0["rows"]) == s0["n"] >= 3 and all("張" in r["txt"] and "NT$" in r["txt"] for r in s0["rows"]), s0["rows"][:2])
        ok(f"{T}（{W}）①b：小表代號順序＝圖上順序；張數＝圖上資料", [r["code"] for r in s0["rows"]] == s0["codes"] and all((l + " 張") in r["txt"].replace(",", "") or (l in r["txt"].replace(",", "")) for l, r in zip(s0["lots"], s0["rows"])), s0)
        ok(f"{T}（{W}）①c：卡片標題下那句長說明不再只講一檔（沒有「投入最少的是」）", "投入最少的是" not in s0["sq"], s0["sq"])
        # 取消最後兩檔 → 表只剩 n-2 列；再勾回一檔 → +1 列
        rows = pg.locator("#incList .ilr input[type=checkbox]:checked")
        n0 = rows.count()
        rows.nth(n0 - 1).click(); pg.wait_for_timeout(300); rows = pg.locator("#incList .ilr input[type=checkbox]:checked"); rows.nth(rows.count() - 1).click(); pg.wait_for_timeout(500)
        s1 = J(_SEL_JS)
        ok(f"{T}（{W}）①d：取消 2 檔 → 右上小表剩 {n0 - 2} 列、跟圖上一致", len(s1["rows"]) == n0 - 2 == s1["n"] and [r["code"] for r in s1["rows"]] == s1["codes"], s1["codes"])
        pg.locator("#incList .ilr input[type=checkbox]:not(:checked)").first.click(); pg.wait_for_timeout(500)
        s2 = J(_SEL_JS)
        ok(f"{T}（{W}）①e：再勾 1 檔 → 小表 {n0 - 1} 列且多出的那檔內容對得上", len(s2["rows"]) == n0 - 1 and s2["codes"][-1] in [r["code"] for r in s2["rows"]], s2["codes"])
        # ② 搜尋 ×
        tot = int(J("() => document.getElementById('incList').dataset.n"))
        pg.fill("#incSearch", "00919"); pg.wait_for_timeout(400)
        n1 = int(J("() => document.getElementById('incList').dataset.n")); vis = J("() => !document.getElementById('incSearchX').hidden")
        ok(f"{T}（{W}）②a：搜尋 00919 → 清單剩少數檔、× 出現", 0 < n1 < tot and vis, (tot, n1, vis))
        pg.click("#incSearchX"); pg.wait_for_timeout(400)
        n2 = int(J("() => document.getElementById('incList').dataset.n")); v2 = J("() => document.getElementById('incSearch').value")
        ok(f"{T}（{W}）②b：按 × → 搜尋框清空、清單回到全部 {tot} 檔、× 消失", n2 == tot and v2 == "" and J("() => document.getElementById('incSearchX').hidden"), (n2, v2))
        # 頻率標籤再點一次＝取消回全部
        chip = pg.locator("#incFq button[data-v='月配']")
        if chip.count():
            chip.click(); pg.wait_for_timeout(300)
            nf = int(J("() => document.getElementById('incList').dataset.n"))
            pg.locator("#incFq button[data-v='月配']").click(); pg.wait_for_timeout(300)
            nb = int(J("() => document.getElementById('incList').dataset.n")); on = J("() => document.querySelector('#incFq button.on').dataset.v")
            ok(f"{T}（{W}）②c：點「月配」只剩月配、再點一次 → 回「全部」{tot} 檔", nf < tot and nb == tot and on == "all", (nf, nb, on))
        if W == 1440:   # 手機的期間鈕收在條件抽屜裡（每個分頁各一份），這段只在桌機驗；手機只驗 ①②
            # ③ 期間
            pg.select_option("#etfIncRng .rpsel", "1y"); pg.wait_for_timeout(900)
            p1 = J(_PER_JS)
            pg.select_option("#etfIncRng .rpsel", "3y"); pg.wait_for_timeout(1200)
            p3 = J(_PER_JS)
            ok(f"{T}（{W}）③a：近 1 年 → 近 3 年，直條資料真的改變、圖上標「近 3 年」與起訖日", p1["ser"] != p3["ser"] and "近 3 年" in p3["lab"] and "近 1 年" in p1["lab"] and "～" in p3["lab"], {"1y": p1["lab"], "3y": p3["lab"]})
            ok(f"{T}（{W}）③b：近 3 年是「期間內平均」（不是近 12 個月的退回）", "期間內平均" in p3["lab"] and "退回" not in p3["lab"], p3["lab"])
            # 自訂日期
            pg.fill("#etfIncRng .rpfrom", "2025-06-01"); pg.dispatch_event("#etfIncRng .rpfrom", "change"); pg.wait_for_timeout(1200)
            pc = J(_PER_JS)
            ok(f"{T}（{W}）③c：自訂起始日 2025/06/01 → 直條與標示都跟著改（下拉＝起始日期～至今）", pc["ser"] != p3["ser"] and "2025/06/01" in pc["lab"] and pc["per"].startswith("C"), pc["lab"])
            if shot_dir:
                os.makedirs(shot_dir, exist_ok=True)
                pg.select_option("#etfIncRng .rpsel", "1y"); pg.wait_for_timeout(900); pg.screenshot(path=f"{shot_dir}/per1y-{W}.png")
                pg.select_option("#etfIncRng .rpsel", "3y"); pg.wait_for_timeout(900); pg.screenshot(path=f"{shot_dir}/per3y-{W}.png")
        if W == 390:
            sw = J("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
            ok(f"{T}（390）：沒有橫向捲軸、小表在畫面內", sw)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF現金流1031", lambda pg, b, base, code: t_etf_cashflow_1031(b, base, code))
