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
  rows: [...document.querySelectorAll('#incChips button.snk[data-n]')].map(r => ({ code: r.dataset.n.split(' ').pop(), txt: r.textContent })),
  lots: (document.getElementById('incBar').dataset.lots || '').split(','),
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
        # ① 已選色塊
        s0 = J(_SEL_JS)
        ok(f"{T}（{W}）①a：已選色塊列數＝圖上檔數（{s0['n']}），每顆色塊有「張」與金額（萬）", len(s0["rows"]) == s0["n"] >= 3 and all("張" in r["txt"] and "萬" in r["txt"] for r in s0["rows"]), s0["rows"][:2])
        ok(f"{T}（{W}）①b：色塊代號順序＝圖上順序；張數＝圖上資料", [r["code"] for r in s0["rows"]] == s0["codes"] and all((l + " 張") in r["txt"].replace(",", "") or (l in r["txt"].replace(",", "")) for l, r in zip(s0["lots"], s0["rows"])), s0)
        ok(f"{T}（{W}）①c：卡片標題下那句長說明不再只講一檔（沒有「投入最少的是」）", "投入最少的是" not in s0["sq"], s0["sq"])
        # 取消最後兩檔 → 表只剩 n-2 列；再勾回一檔 → +1 列
        rows = pg.locator("#incList .ilr input[type=checkbox]:checked")
        n0 = rows.count()
        rows.nth(n0 - 1).click(); pg.wait_for_timeout(300); rows = pg.locator("#incList .ilr input[type=checkbox]:checked"); rows.nth(rows.count() - 1).click(); pg.wait_for_timeout(500)
        s1 = J(_SEL_JS)
        ok(f"{T}（{W}）①d：取消 2 檔 → 已選色塊剩 {n0 - 2} 列、跟圖上一致", len(s1["rows"]) == n0 - 2 == s1["n"] and [r["code"] for r in s1["rows"]] == s1["codes"], s1["codes"])
        pg.locator("#incList .ilr input[type=checkbox]:not(:checked)").first.click(); pg.wait_for_timeout(500)
        s2 = J(_SEL_JS)
        ok(f"{T}（{W}）①e：再勾 1 檔 → 色塊 {n0 - 1} 列且多出的那檔內容對得上", len(s2["rows"]) == n0 - 1 and s2["codes"][-1] in [r["code"] for r in s2["rows"]], s2["codes"])
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
            ok(f"{T}（390）：沒有橫向捲軸、色塊在畫面內", sw)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF現金流1031", lambda pg, b, base, code: t_etf_cashflow_1031(b, base, code))


# ===================================================================== ETF自訂組合1031
# Andy 10-31 18:36：「需要新增自己客製化的組合分頁，目的是我想客製化 ETF 但不一定固定 3 檔」。
#  ① 自訂組合分頁出現在「單檔 ETF｜組合 A～E」那一排最後 ② 從清單勾 4 檔（月配頻率）→ 依目標自動配張數 → 每月入帳都 ≥ 目標
#  ③ 切「自己填張數」改第 1 檔張數 ×2 → 圖上資料（年領、直條）真的變 ④ 重新整理 → 組合還在（4 檔、自己填模式、張數）
#  ⑤ 新增第 2 組再刪除 → 清單少一組、刪掉那組不在 localStorage ⑥ 搜尋 ×、390 無橫向捲軸
_CU_JS = """() => { const c = document.querySelector('#incCombos .combo'); const S = window.TwEtfPage.state;
  return { tab: S.inc.tab, shown: !document.getElementById('incCuBox').hidden, rows: document.querySelectorAll('#cuList .ilr').length,
    sel: [...document.querySelectorAll('#incCuBox .cut tbody tr[data-code]')].map(r => r.dataset.code),
    codes: c ? c.dataset.codes.split(',') : [], lots: c ? c.dataset.lots.split(',').map(Number) : [], vals: c ? c.dataset.vals.split(',').map(Number) : [],
    note: (document.getElementById('cuNote') || {}).textContent || '', mode: (document.getElementById('incCuBox').dataset.mode || ''),
    target: Math.ceil((S.inc.mode === 'm' ? S.inc.mon * 12 : S.inc.year) / 12),
    opts: [...document.querySelectorAll('#cuSel option')].map(o => o.value), ls: localStorage.getItem('tw.etf.inc.custom') || '' }; }"""


def t_etf_custom_1031(b, base, code):
    T = "ETF自訂組合1031"
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
        ready = wait_until(pg, """() => { const el = document.getElementById('incBar'); return !!el && +el.dataset.n >= 3 && !!document.getElementById('incTabU') && window.TwEtfPage && window.TwEtfPage.state.series; }""", 30000)
        ok(f"{T}（{W}）：「自訂組合」分頁在分頁列最後（前置）", bool(ready) and J("() => { const b = [...document.querySelectorAll('#incTabs button')]; return b[b.length - 1].id === 'incTabU'; }"))
        if not ready:
            c.close(); continue
        J("() => document.getElementById('incTabU').click()"); pg.wait_for_timeout(1200)
        s0 = J(_CU_JS)
        ok(f"{T}（{W}）①：點分頁 → 自訂區出現、清單有 ETF、tab＝u、尚未挑（結果卡先是提示）", s0["tab"] == "u" and s0["shown"] and s0["rows"] >= 20 and not s0["sel"], s0["rows"])
        if W == 1440:
            # 搜尋 × 與頻率標籤：先搜再按 ×，清單回全部
            tot = s0["rows"]
            pg.fill("#cuSearch", "00919"); pg.wait_for_timeout(500)
            n1 = J("() => document.querySelectorAll('#cuList .ilr').length")
            pg.click("#cuSearchX"); pg.wait_for_timeout(500)
            n2 = J("() => document.querySelectorAll('#cuList .ilr').length")
            ok(f"{T}（{W}）⑥a：搜尋 00919 → 少數檔；按 × → 回全部 {tot} 檔、搜尋框清空", 0 < n1 < tot and n2 == tot and J("() => document.getElementById('cuSearch').value") == "", (tot, n1, n2))
            pg.locator("#cuFq button[data-v='月配']").click(); pg.wait_for_timeout(500)
            for _ in range(4):
                pg.locator("#cuList .ilr input:not(:checked)").first.click(); pg.wait_for_timeout(500)
            s1 = J(_CU_JS)
            ok(f"{T}（{W}）②a：勾 4 檔 → 已選表 4 列、結果卡 4 檔（甜甜圈／明細同一批）", len(s1["sel"]) == 4 and s1["codes"] == s1["sel"] and len(s1["vals"]) == 12, s1)
            ok(f"{T}（{W}）②b：依目標自動配 → 每個月入帳都 ≥ 每月目標（{s1['target']}）", len(s1["vals"]) == 12 and min(s1["vals"]) >= s1["target"] - 1 and "每個月入帳都" in s1["note"], (s1["vals"], s1["note"]))
            # ③ 自己填張數
            pg.click("#cuMode button[data-v='manual']"); pg.wait_for_timeout(700)
            m0 = J(_CU_JS)
            ok(f"{T}（{W}）③a：切自己填張數 → 每檔出現張數輸入框、張數沿用自動配的結果", m0["mode"] == "manual" and J("() => document.querySelectorAll('#incCuBox .culot').length") == 4 and m0["lots"] == s1["lots"], (m0["lots"], s1["lots"]))
            pg.fill("#incCuBox .culot >> nth=0", str(s1["lots"][0] * 2)); pg.dispatch_event("#incCuBox .culot >> nth=0", "change"); pg.wait_for_timeout(900)
            m1 = J(_CU_JS)
            ok(f"{T}（{W}）③b：第 1 檔張數 ×2 → 結果卡張數、每月入帳資料真的變（年領變大）", m1["lots"][0] == s1["lots"][0] * 2 and sum(m1["vals"]) > sum(m0["vals"]), (m0["lots"], m1["lots"], sum(m0["vals"]), sum(m1["vals"])))
            if shot_dir:
                os.makedirs(shot_dir, exist_ok=True); pg.screenshot(path=f"{shot_dir}/custom-1440.png", full_page=False)
            # ④ 重新整理
            pg.reload(wait_until="networkidle"); wait_until(pg, "() => !!document.querySelector('#incCombos .combo') && !!document.getElementById('cuList')", 30000); pg.wait_for_timeout(800)
            r1 = J(_CU_JS)
            ok(f"{T}（{W}）④：重新整理後組合還在（tab＝u、4 檔、自己填模式、第 1 檔張數同）", r1["tab"] == "u" and r1["sel"] == m1["sel"] and r1["mode"] == "manual" and r1["lots"] == m1["lots"], (r1["sel"], r1["mode"], r1["lots"]))
            # ⑤ 新增再刪除
            pg.click("#cuNew"); pg.wait_for_timeout(700)
            a2 = J(_CU_JS)
            ok(f"{T}（{W}）⑤a：新增第 2 組 → 下拉 2 組、已選清空", len(a2["opts"]) == 2 and not a2["sel"], a2["opts"])
            gone = a2["opts"][-1]
            pg.click("#cuDel"); pg.wait_for_timeout(700)
            a3 = J(_CU_JS)
            ok(f"{T}（{W}）⑤b：刪除目前這組 → 剩 1 組（回到有 4 檔那組）、刪掉的 id 不在 localStorage", len(a3["opts"]) == 1 and gone not in a3["ls"] and len(a3["sel"]) == 4, (a3["opts"], a3["sel"]))
            # 複利試算帶得到自訂組合
            pg.click("#incToCx"); pg.wait_for_timeout(1500)
            ok(f"{T}（{W}）⑦：結果卡「看複利試算」→ 複利對象下拉有這組自訂組合並選中", J("() => { const s = document.getElementById('cxObj'); return !!s && /自訂/.test(s.options[s.selectedIndex].textContent); }"))
        else:
            n = J("() => document.querySelectorAll('#cuList .ilr').length")
            pg.locator("#cuList .ilr input:not(:checked)").first.click(); pg.wait_for_timeout(700)
            s2 = J(_CU_JS)
            ok(f"{T}（{W}）：手機勾 1 檔 → 已選表 1 列、結果卡畫出", len(s2["sel"]) == 1 and len(s2["codes"]) == 1, s2["sel"])
            ok(f"{T}（390）：沒有橫向捲軸", J("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
            if shot_dir:
                os.makedirs(shot_dir, exist_ok=True); pg.screenshot(path=f"{shot_dir}/custom-390.png", full_page=False)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF自訂組合1031", lambda pg, b, base, code: t_etf_custom_1031(b, base, code))
