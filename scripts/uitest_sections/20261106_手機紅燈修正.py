# 驗收段落「手機紅燈1106」：手機按鈕普查 11-06 的兩個紅燈，各自用觸控真的操作一次、驗畫面真的變了。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok() 直接可用，不要 import _uitest。
#   ① HBM 剖析圖「全螢幕看大圖」浮層裡的章節摺疊列（g.dgfold）：浮層裡的圖是 cloneNode 複製的，事件監聽沒跟著複製，點了不會展開。
#      修在 diagrams.js openView：把點擊轉給原圖同一條章節列，再用原圖重新複製一份換進來。這裡驗：點一條 → 展開數 0→1、圖變高。
#   ② ETF 現金流試算「自訂組合自己挑」的「我的組合」下拉：兩組以上時切換真的換了組合（名稱欄、頁籤小字、已選列數都換）；
#      只有一組時沒有可切換的東西（普查改成註記、不算沒反應，見 _mobile_tap_audit.py single）。


def t_mobile_reds_1106(b, base, code):
    T = "手機紅燈1106"
    errs: list = []
    c = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))

    # ---- ① 大圖裡的章節摺疊列 ----
    pg.goto(base + "#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(2500)
    pg.evaluate("() => { const b = [...document.querySelectorAll('#dgPick button')].find(x => /HBM/.test(x.textContent)); if (b) b.click(); }")
    pg.wait_for_timeout(2500)
    pg.evaluate("() => { const b = document.querySelector('.mdvbtn'); if (b) b.scrollIntoView({ block: 'center' }); }"); pg.wait_for_timeout(300)
    r = pg.evaluate("() => { const b = document.querySelector('.mdvbtn'); if (!b) return null; const r = b.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
    ok(f"{T} HBM 剖析圖有「放大」鈕", bool(r), r)
    if r:
        pg.touchscreen.tap(*r); pg.wait_for_timeout(1200)
        S1 = """() => { const v = document.getElementById('mDgView'); if (!v) return null; const s = v.querySelector('svg'), fs = [...v.querySelectorAll('g.dgfold')];
            return { folds: fs.length, open: fs.filter(g => g.classList.contains('open')).length, h: Math.round(s.getBoundingClientRect().height) }; }"""
        a0 = pg.evaluate(S1)
        ok(f"{T} 全螢幕大圖打得開、裡面有章節摺疊列", bool(a0) and a0["folds"] > 0, a0)
        if a0 and a0["folds"]:
            pg.evaluate("() => { const g = document.querySelector('#mDgView g.dgfold'); g.scrollIntoView({ block: 'center' }); }"); pg.wait_for_timeout(300)
            pt = pg.evaluate("() => { const r = document.querySelector('#mDgView g.dgfold').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
            pg.touchscreen.tap(*pt); pg.wait_for_timeout(900)
            a1 = pg.evaluate(S1)
            ok(f"{T} 用觸控點大圖裡的章節摺疊列 → 真的展開（展開數 {a0['open']}→{a1 and a1['open']}、圖變高 {a0['h']}→{a1 and a1['h']}px）",
               bool(a1) and a1["open"] == a0["open"] + 1 and a1["h"] > a0["h"], (a0, a1))
            pt = pg.evaluate("() => { const g = document.querySelector('#mDgView g.dgfold.open'); if (!g) return null; const r = g.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
            if pt:
                pg.touchscreen.tap(*pt); pg.wait_for_timeout(900)
                a2 = pg.evaluate(S1)
                ok(f"{T} 再點同一條 → 收回去（展開數回到 {a0['open']}）", bool(a2) and a2["open"] == a0["open"], a2)
        pg.evaluate("() => { const x = document.querySelector('#mDgView .mdv-x'); if (x) x.click(); }"); pg.wait_for_timeout(300)

    # ---- ② 自訂組合下拉 ----
    pg.goto(base + "#etf/inc", wait_until="networkidle"); pg.wait_for_timeout(2500)
    pg.evaluate("() => { const b = document.querySelector('#incTabs button[data-v=\"u\"]'); if (b) b.click(); }"); pg.wait_for_timeout(1500)
    SN = """() => { const s = document.getElementById('cuSel'); return s ? { cur: s.value, opts: s.options.length, name: (document.getElementById('cuName') || {}).value,
        rows: document.querySelectorAll('#incCuBox .cut tbody tr[data-code]').length, tab: ((document.getElementById('incTabU') || {}).textContent || '') } : null; }"""
    n0 = pg.evaluate(SN)
    ok(f"{T} 自訂組合頁有「我的組合」下拉", bool(n0), n0)
    if n0:
        pg.evaluate("() => document.getElementById('cuNew').click()"); pg.wait_for_timeout(700)
        pg.evaluate("() => document.querySelector('#cuList .ilr input').click()"); pg.wait_for_timeout(700)
        n1 = pg.evaluate(SN)
        pg.evaluate("() => { const s = document.getElementById('cuSel'); s.selectedIndex = (s.selectedIndex + 1) % s.options.length; s.dispatchEvent(new Event('change', { bubbles: true })); }"); pg.wait_for_timeout(700)
        n2 = pg.evaluate(SN)
        ok(f"{T} 兩組以上時切換「我的組合」→ 真的換了組合（名稱欄、頁籤小字、已選列數都跟著換）",
           n1["opts"] >= 2 and n2["cur"] != n1["cur"] and n2["name"] != n1["name"] and n2["tab"] != n1["tab"] and n2["rows"] != n1["rows"], (n1, n2))
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("手機紅燈1106", lambda pg, b, base, code: t_mobile_reds_1106(b, base, code))
