# 驗收段落「交易練習室箭頭1029」：進出場箭頭不撐爆價格軸（台指期／歷史回測 全部期間），手機台指期量軸寫「口」。 flake8: noqa


def t_lab_arrows(b, base, code):
    T = "交易練習室箭頭1029"
    _ok = globals()["ok"]
    js = """() => { const CH = window.TwLab.charts, S = window.TwLab.state(); const k = CH.k, cs = CH.cs; if (!k || !cs) return null;
      const h = k.paneSize(0).height, lo = cs.coordinateToPrice(h - 1);
      const rg = k.timeScale().getVisibleLogicalRange(), B = (S.bt && S.bt.B) || (S.fut && S.fut.B);
      let m = Infinity, M = -Infinity; for (let i = Math.max(0, Math.floor(rg.from)); i <= Math.min(B.n - 1, Math.ceil(rg.to)); i++) { m = Math.min(m, B.l[i]); M = Math.max(M, B.h[i]); }
      return [lo, m, M]; }"""
    for w, h, mob in [(1440, 900, False), (390, 844, True)]:
        kw = dict(viewport={"width": w, "height": h})
        if mob:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        c = b.new_context(**kw)
        c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
        pg = c.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#lab/fut", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
        pg.click("#labFSub button[data-f='bt']"); pg.wait_for_timeout(3500)
        pg.evaluate("() => document.querySelector(\"#labRng button[data-r='All']\").click()"); pg.wait_for_timeout(2500)
        r = pg.evaluate(js)
        _ok(f"{T}（{w}）：台指期全部，價格軸最小值不低於可視最低價－15% 價幅（箭頭不撐軸）", bool(r) and r[0] >= r[1] - 0.15 * (r[2] - r[1]), r)
        if mob:
            txt = pg.evaluate("() => { const ss = window.TwLab.charts.k.panes()[1].getSeries(); return ss.map((x) => { const f = x.options().priceFormat; return f.tickmarksFormatter ? f.tickmarksFormatter([400, 400000, 30000000]).join(',') : (f.formatter ? f.formatter(400) : ''); }).join('|'); }")
            _ok(f"{T}（{w}）：手機台指期量軸單位是「口」不是「張」", "口" in txt and "張" not in txt, txt)
        pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
        r = pg.evaluate(js)
        _ok(f"{T}（{w}）：歷史回測價格軸最小值不低於可視最低價－15% 價幅（箭頭不撐軸）", bool(r) and r[0] >= r[1] - 0.15 * (r[2] - r[1]), r)
        _ok(f"{T}（{w}）：無 JS 錯誤", not errs, errs[:3])
        c.close()


register("交易練習室箭頭1029", lambda pg, b, base, code: t_lab_arrows(b, base, code))
