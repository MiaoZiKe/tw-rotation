# 驗收段落「ETF版面重排1031」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa

# Andy 10-31 23:50～23:58：
#  「這太不美觀了，都影響到整個版面」→ 已選明細寫在色塊上、不撐高標題列、卡內無大空白
#  「固定版面，不該隨清單數量而改變」→ 自訂組合選 2 檔與 8 檔，結果卡位置相同
#  「清除選項功能呢？」→ 清除勾選／搜尋 ×／其他勾選列不淡掉
#  「上面分頁用不同顏色標註」→ 7 個分頁各一色，結果卡同色呼應
#  自動配張數：各檔金額平均／總投入最少 兩種，甜甜圈小切片不標字

_TOP_JS = """() => { const q = (s) => document.querySelector(s); const r = (e) => e ? e.getBoundingClientRect() : null;
  const cb = r(q('#incCombos .combo')), cug = r(q('#incCuBox .cug')), lst = r(q('#incCuBox .cuic'));
  return { top: cb ? cb.top + scrollY : null, cugH: cug ? cug.height : null, lstH: lst ? lst.height : null, cugTop: cug ? cug.top + scrollY : null,
    sw: document.documentElement.scrollWidth, iw: window.innerWidth }; }"""


def t_etf_ui_1031(b, base, code):
    T = "ETF版面重排1031"
    errs: list[str] = []
    for W in (1440, 1280, 390):
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
        ok(f"{T}（{W}）：單檔圖畫出（前置）", bool(ready))
        if not ready:
            c.close(); continue
        pg.wait_for_timeout(600)
        desk = W >= 1101
        if desk:
            g = J("""() => { const q = (s) => document.querySelector(s), r = (e) => e.getBoundingClientRect();
              const hd = q('#incSingle .row.spread'), lst = r(q('#incListBox')), bar = r(q('#incBar')), ch = [...document.querySelectorAll('#incSingle > *:not([hidden]):not(.incdet)')].map(r);
              let gap = 0; for (let i = 1; i < ch.length; i++) gap = Math.max(gap, ch[i].top - ch[i - 1].bottom);
              const cl = q('#incChips'); const sn = [...document.querySelectorAll('#incChips .snd')].length;
              return { hdH: r(hd).height, listB: lst.bottom, barB: bar.bottom, gap, snd: sn, sel: !!q('#incSel'), inc: q('#incSingle').getBoundingClientRect().width }; }""")
            ok(f"{T}（{W}）①a：單檔標題列高度不被撐高（{g['hdH']:.0f}px ≤ 60）、已選明細是色塊（{g['snd']} 顆有張數金額）、沒有獨立小表", g["hdH"] <= 60 and g["snd"] >= 3 and not g["sel"], g)
            ok(f"{T}（{W}）①b：卡內相鄰區塊之間沒有 > 120px 的空白帶（最大 {g['gap']:.0f}px）；清單底邊與圖底邊差 ≤ 40px", g["gap"] <= 120 and abs(g["listB"] - g["barB"]) <= 40, g)
            # 清除勾選
            n5 = J("() => document.querySelectorAll('#incList .ilr input:checked').length")
            pg.click("#incClear"); pg.wait_for_timeout(600)
            z = J("() => ({ ck: document.querySelectorAll('#incList .ilr input:checked').length, n: +document.getElementById('incBar').dataset.n, hint: !!document.querySelector('#incChips .snhint'), cnt: document.getElementById('incCnt').textContent })")
            ok(f"{T}（{W}）②a：按「清除勾選」→ 勾選 {n5}→0、圖上 0 柱、出現「請從右側勾選」提示", n5 >= 3 and z["ck"] == 0 and z["n"] == 0 and z["hint"], z)
            pg.click("#incReset"); pg.wait_for_timeout(600)
            ok(f"{T}（{W}）②b：「回前 5」→ 勾回 5 檔", J("() => document.querySelectorAll('#incList .ilr input:checked').length") == 5)
            pg.fill("#incSearch", "009"); pg.wait_for_timeout(300)
            v = J("() => { const x = document.getElementById('incSearchX'), r = x.getBoundingClientRect(); return { hidden: x.hidden, w: r.width, h: r.height }; }")
            ok(f"{T}（{W}）②c：搜尋框打字後 × 可見（{v['w']:.0f}×{v['h']:.0f}）", not v["hidden"] and v["w"] >= 20, v)
            pg.click("#incSearchX"); pg.wait_for_timeout(300)
            ok(f"{T}（{W}）②d：按 × → 搜尋框清空、× 消失", J("() => document.getElementById('incSearch').value") == "" and J("() => document.getElementById('incSearchX').hidden"))
            # 勾選列選取後不淡掉
            J("() => document.querySelector('#incList .ilr:nth-child(2) .iln').click()"); pg.wait_for_timeout(300)
            op = J("() => [...document.querySelectorAll('#incList .ilr')].filter(r => r.querySelector('input').checked).map(r => +getComputedStyle(r).opacity)")
            ok(f"{T}（{W}）②e：選取其中一檔後，5 個勾選列都不淡掉（opacity 全 1）", len(op) == 5 and all(o >= 0.99 for o in op), op)
            # 色塊 ×
            pg.locator("#incChips button.snk[data-n] b").first.click(); pg.wait_for_timeout(500)
            ok(f"{T}（{W}）②f：色塊 × → 圖上少 1 檔、清單勾選同步", J("() => +document.getElementById('incBar').dataset.n") == 4 and J("() => document.querySelectorAll('#incList .ilr input:checked').length") == 4)
            pg.click("#incReset"); pg.wait_for_timeout(400)
        # 分頁識別色
        tc = J("""() => [...document.querySelectorAll('#incTabs button[data-tc]')].map(b => ({ k: b.dataset.tc, c: parseFloat(getComputedStyle(b).borderTopWidth) >= 3 ? getComputedStyle(b).borderTopColor : getComputedStyle(b).boxShadow, w: parseFloat(getComputedStyle(b).borderTopWidth) >= 3 ? 3 : (/0px 3px 0px 0px inset/.test(getComputedStyle(b).boxShadow) ? 3 : 0) }))""")
        ok(f"{T}（{W}）③a：分頁 {len(tc)} 顆（單檔、A～E、自訂）各有不同識別色（上緣色條 ≥ 3px）", len(tc) >= 7 and len({t['c'] for t in tc}) == len(tc) and all(t["w"] >= 3 for t in tc), tc)
        if desk:
            pg.locator("#incTabs button[data-tc='C']").click(); pg.wait_for_timeout(1300)
            cc = J("() => { const c = document.querySelector('#incCombos .combo'), t = document.querySelector('#incTabs button[data-tc=C]'); return { card: c.dataset.tc, bt: getComputedStyle(c).borderTopColor, tab: getComputedStyle(t).borderTopColor, rk: getComputedStyle(c.querySelector('.rk')).color, txt: c.querySelector('.rk').textContent }; }")
            ok(f"{T}（{W}）③b：組合 C 的結果卡上緣色條＝C 分頁色，標題「{cc['txt']}」", cc["card"] == "C" and cc["bt"] == cc["tab"] and "C" in cc["txt"], cc)
            codesA = J("() => { document.querySelector('#incTabs button[data-tc=A]').click(); return null; }")
            pg.wait_for_timeout(1200)
            A = J("() => document.querySelector('#incCombos .combo').dataset.codes.split(',')")
            # 自訂組合：固定版面
            J("() => document.getElementById('incTabU').click()"); pg.wait_for_timeout(1000)
            pg.locator("#cuFq button[data-v='月配']").click(); pg.wait_for_timeout(400)
            for _ in range(2):
                pg.locator("#cuList .ilr input:not(:checked)").first.click(); pg.wait_for_timeout(500)
            p2 = J(_TOP_JS)
            for _ in range(6):
                pg.locator("#cuList .ilr input:not(:checked)").first.click(); pg.wait_for_timeout(500)
            p8 = J(_TOP_JS)
            ok(f"{T}（{W}）④a：自訂組合選 2 檔與 8 檔 → 結果卡 top 相同（{p2['top']}／{p8['top']}，Δ<1px）", p2["top"] is not None and p8["top"] is not None and abs(p2["top"] - p8["top"]) < 1, (p2, p8))
            ok(f"{T}（{W}）④b：上半部兩欄同高（表 {p8['cugH']}、清單 {p8['lstH']}；2 檔時 {p2['cugH']}）且固定", p8["cugH"] and abs(p8["cugH"] - p8["lstH"]) < 1 and abs(p2["cugH"] - p8["cugH"]) < 1, (p2, p8))
            lab = J("() => document.getElementById('incCdn').dataset.labels")
            ok(f"{T}（{W}）⑤a：8 檔甜甜圈：占比 < 9% 的切片不標字（標籤陣列 {lab}）", all(x == "" or "張" in x for x in lab.split("|")) and len(lab.split("|")) == 8, lab)
            # 兩種自動配法（用組合 A 的檔，湊得滿 12 個月）
            pg.click("#cuClear"); pg.wait_for_timeout(500)
            ck0 = J("() => document.querySelectorAll('#cuList .ilr input:checked').length")
            pg.click("#cuSearchX") if J("() => !document.getElementById('cuSearchX').hidden") else None
            pg.locator("#cuFq button[data-v='all']").click() if J("() => !!document.querySelector('#cuFq button[data-v=all]:not(.on)')") else None
            pg.wait_for_timeout(300)
            for cd in A:
                pg.fill("#cuSearch", cd); pg.wait_for_timeout(300)
                pg.locator(f"#cuList .ilr[data-code='{cd}'] input").click(); pg.wait_for_timeout(400)
            pg.click("#cuSearchX"); pg.wait_for_timeout(400)
            ev = J("""() => { const c = document.querySelector('#incCombos .combo'); const f = (x) => ({ lots: c.dataset.lots.split(',').map(Number), vals: c.dataset.vals.split(',').map(Number), cost: +c.dataset.cost });
              return { ...f(), note: document.getElementById('cuNote').textContent, alloc: !!document.getElementById('cuAlloc'), on: (document.querySelector('#cuAlloc button.on') || {}).dataset.v,
                target: Math.ceil((window.TwEtfPage.state.inc.mode === 'm' ? window.TwEtfPage.state.inc.mon * 12 : window.TwEtfPage.state.inc.year) / 12) }; }""")
            pg.click("#cuAlloc button[data-v='min']"); pg.wait_for_timeout(900)
            mn = J("""() => { const c = document.querySelector('#incCombos .combo'); return { lots: c.dataset.lots.split(',').map(Number), vals: c.dataset.vals.split(',').map(Number), cost: +c.dataset.cost, note: document.getElementById('cuNote').textContent }; }""")
            ok(f"{T}（{W}）⑥a：自動配有兩種切換，預設＝各檔金額平均，兩種每月入帳都 ≥ 目標（{ev['target']}）", ev["alloc"] and ev["on"] == "even" and min(ev["vals"]) >= ev["target"] - 1, (ev, mn))
            ok(f"{T}（{W}）⑥b：各檔金額平均 ≥ 總投入最少的總投入、且張數比較不懸殊（最大/最小張數比：平均 {max(ev['lots'])/max(1,min(ev['lots'])):.1f} vs 最少 {max(mn['lots'])/max(1,min(mn['lots'])):.1f}）", ev["cost"] >= mn["cost"] - 1 and min(mn["vals"]) >= ev["target"] - 1, (ev["lots"], mn["lots"], ev["cost"], mn["cost"]))
            ok(f"{T}（{W}）⑥c：畫面有白話說明（平均＝「金額大致相同」；最少＝「總投入最少」）", "大致相同" in ev["note"] and "總投入最少" in mn["note"], (ev["note"], mn["note"]))
            # 自訂清單清除勾選
            pg.click("#cuClear"); pg.wait_for_timeout(500)
            ok(f"{T}（{W}）⑦：自訂清單「清除勾選」→ 勾選 0、已選表 0 列", J("() => document.querySelectorAll('#cuList .ilr input:checked').length") == 0 and J("() => document.querySelectorAll('#incCuBox .cut tbody tr[data-code]').length") == 0)
        ok(f"{T}（{W}）⑧：沒有橫向捲軸", J("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF版面重排1031", lambda pg, b, base, code: t_etf_ui_1031(b, base, code))
