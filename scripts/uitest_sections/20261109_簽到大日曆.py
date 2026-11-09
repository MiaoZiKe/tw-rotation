# 驗收段落「簽到大日曆1109」：#checkin 直達、上方寬進度條、下方大日曆、簽到後今天格出現已簽標記且進度條天數 +1
# flake8: noqa


def t_checkin_big_1109(b, base, code):
    import os
    T = "簽到大日曆1109"
    errs: list[str] = []
    shot = os.environ.get("TW_CI_SHOT")
    for W in (1440, 390):
        for theme in ("dark", "light"):
            c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900})
            c.add_init_script("window.__TW_UITEST=1;try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme','%s')}catch(e){}" % theme)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            pg.goto(base + "#checkin", wait_until="load")
            opened = wait_until(pg, "() => { const o = document.getElementById('ciOv'); return !!o && !o.hidden && !!document.getElementById('ciSign'); }", 10000)
            ok(f"{T}（{theme}/{W}）網址 #checkin → 直接打開簽到月曆", bool(opened))
            ok(f"{T}（{theme}/{W}）打開後網址換回 #overview", pg.evaluate("() => location.hash") == "#overview")
            if not opened:
                c.close(); continue
            pg.evaluate("() => TwCheckin.test.reset()"); pg.wait_for_timeout(300)
            pg.evaluate("() => TwCheckin.close()"); pg.evaluate("() => TwCheckin.open()"); pg.wait_for_selector("#ciSign", timeout=5000)
            g = pg.evaluate("""() => { const d = document.getElementById('ciDlg'), cs = getComputedStyle(d), inner = d.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
              const pr = document.querySelector('.ci-prog').getBoundingClientRect(), cell = document.querySelector('.ci-c[data-d]').getBoundingClientRect();
              const cal = document.querySelector('.ci-calw').getBoundingClientRect(), sg = document.getElementById('ciSign').getBoundingClientRect();
              return { inner, prog: pr.width, cell: cell.width, cellh: cell.height, progBottom: pr.bottom, signTop: sg.top, signBottom: sg.bottom, calTop: cal.top, nodes: document.querySelectorAll('.ci-pn').length, hs: document.documentElement.scrollWidth, vw: innerWidth }; }""")
            ok(f"{T}（{theme}/{W}）進度條寬度 ≥ 彈窗內寬 90%（{g['prog']:.0f}／{g['inner']:.0f}）", g["prog"] >= g["inner"] * 0.9, g)
            ok(f"{T}（{theme}/{W}）進度條上有 4 個節點（3／7／14／20）", g["nodes"] == 4)
            want = 72 if W > 640 else 44
            ok(f"{T}（{theme}/{W}）日曆格子高度 ≥ {want}px（{g['cellh']:.0f}）、寬 ≥ {want if W > 640 else 40}", g["cellh"] >= want - 0.5 and g["cell"] >= (want if W > 640 else 40), g)
            ok(f"{T}（{theme}/{W}）順序：進度條在上、簽到鈕在中、日曆在下，沒有重疊", g["progBottom"] <= g["signTop"] + 1 and g["signBottom"] <= g["calTop"] + 1, g)
            ok(f"{T}（{theme}/{W}）沒有橫向捲軸", g["hs"] <= g["vw"])
            if W < 641:
                one = pg.evaluate("() => { const d = document.getElementById('ciDlg'); return { sh: d.scrollHeight, ch: d.clientHeight }; }")
                ok(f"{T}（{theme}/{W}）手機 390：整個月一屏看完（不內捲）", one["sh"] <= one["ch"] + 1, one)
            before = pg.evaluate("() => +document.getElementById('ciTot').textContent")
            has_mark_before = pg.evaluate("() => !!document.querySelector('.ci-c.td svg.ck')")
            pg.click("#ciSign"); pg.wait_for_timeout(400)
            after = pg.evaluate("() => +document.getElementById('ciTot').textContent")
            mark = pg.evaluate("() => { const e = document.querySelector('.ci-c.td.sg svg.ck'); if (!e) return null; const r = e.getBoundingClientRect(); return { w: r.width, bg: getComputedStyle(e).backgroundColor }; }")
            ok(f"{T}（{theme}/{W}）簽到後今天格出現已簽標記（實心圓章）、簽前沒有", (not has_mark_before) and bool(mark) and mark["w"] >= 20, mark)
            ok(f"{T}（{theme}/{W}）簽到後進度條天數 +1（{before}→{after}）", after == before + 1)
            ok(f"{T}（{theme}/{W}）進度條填色寬度隨天數變寬", pg.evaluate("() => document.querySelector('.ci-ptb i').getBoundingClientRect().width") > 0)
            if shot:
                pg.wait_for_timeout(3800)   # 等簽到提示氣泡自己消失，截圖才不被它蓋住
                os.makedirs(shot, exist_ok=True); pg.screenshot(path=f"{shot}/checkin_{theme}_{W}.png")
            c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("簽到大日曆1109", lambda pg, b, base, code: t_checkin_big_1109(b, base, code))
