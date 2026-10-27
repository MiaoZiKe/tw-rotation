# 驗收段落「輪動時鐘環標1027」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# Andy 2026-10-27：#flow 800px 輪動時鐘「100%」環標偶發壓到點標（例如「玻璃陶瓷」）。
# 修法：layoutRotNear 把環標當障礙物。這裡 800 寬連開 3 次、讀 zrender 顯示清單，環標矩形與任何點標矩形都不准相交。
RING_JS = """() => { const el = document.getElementById('rotClock'); const c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const rs = [];
  c.getZr().storage.getDisplayList().forEach(e => { const t = (e.style && e.style.text) || ''; if (!t || e.invisible || e.ignore) return;
    const r = e.getBoundingRect().clone(); if (e.transform) r.applyTransform(e.transform);
    rs.push({ t: String(t), x: r.x, y: r.y, w: r.width, h: r.height, ring: /^(25|100)%$/.test(String(t)) }); });
  const rings = rs.filter(x => x.ring), labs = rs.filter(x => !x.ring && x.w > 8);
  const hit = []; rings.forEach(a => labs.forEach(l => { if (a.x < l.x + l.w && l.x < a.x + a.w && a.y < l.y + l.h && l.y < a.y + a.h) hit.push([a.t, l.t]); }));
  return { rings: rings.length, labs: labs.length, hit }; }"""


def t_rot_ringlbl_1027(b, base, code):
    T = "輪動時鐘環標1027"
    for rep in range(3):
        c = b.new_context(viewport={"width": 800, "height": 1000})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'t'}))}catch(e){}")
        pg = c.new_page()
        pg.goto(base + "#flow", wait_until="domcontentloaded")
        wait_until(pg, "() => { const e = document.getElementById('rotClock'); const c = e && window.echarts && echarts.getInstanceByDom(e); return c && c.getZr().storage.getDisplayList().length > 20 ? 1 : 0; }", 20000)
        pg.wait_for_timeout(2500)
        r = pg.evaluate(RING_JS)
        ok(f"{T}（第 {rep + 1} 次，800px）：環標「25%」「100%」都畫出來、點標沒有壓到環標",
           bool(r) and r["rings"] == 2 and r["labs"] >= 3 and not r["hit"], r)
        c.close()


register("輪動時鐘環標1027", lambda pg, b, base, code: t_rot_ringlbl_1027(b, base, code))
