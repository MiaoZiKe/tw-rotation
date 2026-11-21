# 驗收段落「個股工具列761」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 個股工具列761
# 2026-11-07 週健康檢查：641～820 寬的 #stock 頁，761～769 寬時 #skTools（週期鈕列）內容比卡片寬 8px，
# 「?」伸出卡片、整頁多出橫向捲動。原本 overflow-x:auto 只到 760，抬到 780。
# 驗：641～820 每 10 寬＋761、769、770、780、781 邊界，整頁 scrollWidth ≤ 視窗寬，且沒有任何元素伸出卡片右緣。

def t_sktools_761(b, base):
    T = "個股工具列761"
    bad = []
    widths = sorted(set(list(range(641, 821, 10)) + [761, 765, 769, 770, 780, 781]))
    c = b.new_context(viewport={"width": 800, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page()
    try:
        pg.goto(base + "#stock/2330", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('skTools')", 12000)
        for w in widths:
            pg.set_viewport_size({"width": w, "height": 900}); pg.wait_for_timeout(350)
            m = pg.evaluate("""() => { const t = document.getElementById('skTools'), card = document.getElementById('skChartCard');
                if (!t || !card) return null;
                const cr = card.getBoundingClientRect(); let out = [];
                for (const e of t.children) { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
                    if (r.width > 0 && cs.display !== 'none' && r.right > cr.right + 1 && !(t.scrollWidth > t.clientWidth && /(auto|scroll)/.test(getComputedStyle(t).overflowX))) out.push((e.id || e.className) + ':' + Math.round(r.right)); }
                return { sw: document.documentElement.scrollWidth, vw: innerWidth, out }; }""")
            if m is None or m["sw"] > m["vw"] or m["out"]:
                bad.append((w, m))
    finally:
        c.close()
    ok(f"{T}：641～820 共 {len(widths)} 個寬度，個股工具列不撐破卡片、整頁沒有橫向捲動", not bad, bad[:5])


register("個股工具列761", lambda pg, b, base, code: t_sktools_761(b, base))
