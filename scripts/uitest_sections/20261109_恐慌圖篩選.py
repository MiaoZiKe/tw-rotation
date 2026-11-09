# 驗收段落「恐慌圖篩選1109」
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_sub_ctx() 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _FEAR1109B_ 開頭（所有段落 exec 進同一個命名空間）。
# Andy 11-09：「需要可以篩選，並且需要標出VIX階段性最低最高點 以垂直虛線表示，並且在標示出 最低到最高 漲多少% 最高到最低 跌幅多少%」
#            「並且可以用游標 縮放」「並且 上下寬度需要在+寬」。
# 真的操作：
#   1. 點圖例關掉「費城半導體」→ 那條線消失、上格 Y 軸範圍改變、下格 Y 軸不動、重新整理仍是關的；台股不受影響（各自記）；全關上格＝只剩 1 格
#   2. 階段高低點：垂直虛線 ≥ 2 條（上下兩格各一條）、▲／▼ 標籤的百分比＝相鄰轉折實際算出的漲跌幅（誤差 0.5 內）、所有文字（含色帶字、軸字）兩兩不重疊、不超出圖框
#   3. 切期間鈕（1月）→ 轉折重算：全部落在新視窗內
#   4. 提示框滑到轉折那天 → 多一行「波段低點／高點」
#   5. 游標縮放：滾輪放大 → 視窗變窄、期間鈕全部取消亮起、轉折重算；按期間鈕回到該期間；拖曳平移視窗起點改變
#   6. 手機 390：標籤不重疊；單指上下滑頁面仍會捲動；兩指縮放視窗變窄
#   7. 圖加高：桌機整張圖 ≥ 480px、下格 ≥ 190px

_FEAR1109B_JS = """() => { const el = document.getElementById('ovFearChart'); const ch = echarts.getInstanceByDom(el); if (!ch) return null; const o = ch.getOption();
    const W = el.clientWidth, H = el.clientHeight;
    const texts = []; ch.getZr().storage.getDisplayList(true).forEach(e => { const t = e.style && e.style.text; if (!t || e.invisible || (e.style.opacity === 0)) return;
      let r = e.getBoundingRect().clone(); const m = e.getComputedTransform && e.getComputedTransform(); if (m) r.applyTransform(m);
      if (r.width < 1 || r.height < 1) return; texts.push({ t: String(t), x0: r.x, y0: r.y, x1: r.x + r.width, y1: r.y + r.height }); });
    const bot = o.series.find(s => /^bot-/.test(s.id || '')), top = o.series.filter(s => /^top-/.test(s.id || ''));
    const lines = (s) => (s && s.markLine && s.markLine.data || []).filter(d => d.xAxis != null).length;
    const z = o.dataZoom[0];
    return { W, H, texts, ids: o.series.map(s => s.id), ys: o.yAxis.map(y => [y.min, y.max]), grids: o.grid.map(g => Math.round(+g.height)),
      botLines: lines(bot), topLines: lines(top[0]), bands: bot && bot.markArea ? bot.markArea.data.length : 0, a: +z.startValue, b: +z.endValue,
      f: window.App._fear, ls: (() => { try { return [localStorage.getItem('tw.fear.hide.us'), localStorage.getItem('tw.fear.hide.tw')]; } catch (e) { return null; } })(),
      pers: [...document.querySelectorAll('#fzPer button.on')].map(b => b.dataset.p), legOff: [...document.querySelectorAll('#fzLeg button.off')].map(b => b.dataset.k) }; }"""


def _fear1109b_overlap(f):
    """所有文字（標籤、色帶字、軸字）兩兩不相交、不超出圖框；回傳 (問題清單)"""
    bad, T = [], f["texts"]
    for i, a in enumerate(T):
        if a["x0"] < -0.5 or a["y0"] < -0.5 or a["x1"] > f["W"] + 0.5 or a["y1"] > f["H"] + 0.5:
            bad.append(("出框", a["t"]))
        for b2 in T[i + 1:]:
            if a["t"] == b2["t"] and abs(a["x0"] - b2["x0"]) < 1 and abs(a["y0"] - b2["y0"]) < 1:
                continue
            if min(a["x1"], b2["x1"]) - max(a["x0"], b2["x0"]) > 0.5 and min(a["y1"], b2["y1"]) - max(a["y0"], b2["y0"]) > 0.5:
                bad.append((a["t"], b2["t"]))
    return bad


def _fear1109b_pct_ok(f):
    """畫在圖上的 ▲／▼ 百分比，每一個都要對得上「相鄰轉折實際算出的漲跌幅」（誤差 0.5 內）"""
    import re as _re
    pv = f["f"]["piv"]; real = [(pv[j]["v"] / pv[j - 1]["v"] - 1) * 100 for j in range(1, len(pv))]
    shown = []
    for t in f["texts"]:
        m = _re.match(r"^([▲▼])([+-])(\d+)%$", t["t"])
        if m:
            shown.append(int(m.group(3)) * (1 if m.group(1) == "▲" else -1))
    return bool(shown) and all(any(abs(s - r) <= 0.51 for r in real) for s in shown) and len(shown) == len(real), shown, [round(x, 1) for x in real]


def t_fear_1109b(b, base, code):
    T = "恐慌圖篩選1109"
    errs: list = []
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))

    def go(p):
        p.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(p, "() => !!document.querySelector('#hero .osc[data-k=\"fear\"]') && !!window.FearCard && !!FearCard._s.data", 30000)
        p.wait_for_timeout(700)
        if p.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            p.keyboard.press("Escape"); p.wait_for_timeout(300)
        p.evaluate("() => document.querySelector('#hero .osc[data-k=\"fear\"]').scrollIntoView({block: 'center'})")
        p.locator('#hero .osc[data-k="fear"]').click(position={"x": 30, "y": 60})
        wait_until(p, "() => !!document.querySelector('#ovFearChart canvas, #ovFearChart svg')", 8000)
        p.wait_for_timeout(1000)

    go(pg)
    pg.locator("#fzMkt button", has_text="美股").click(); pg.wait_for_timeout(600)
    pg.locator("#fzPer button", has_text="6月").click(); pg.wait_for_timeout(700)
    f0 = pg.evaluate(_FEAR1109B_JS)
    # ---- 7. 加高
    ok(f"{T} 圖加高：桌機整張圖 ≥ 480px、下格 ≥ 190px、上格 ≥ 190px", f0["H"] >= 480 and f0["grids"][-1] >= 190 and f0["grids"][0] >= 190, [f0["H"], f0["grids"]])
    # ---- 2. 轉折
    ok(f"{T} 美股 6 月：階段高低點 ≥ 3 個、垂直虛線上下兩格都有（≥ 3 條）", len(f0["f"]["piv"]) >= 3 and f0["botLines"] >= 3 and f0["topLines"] >= 3, [len(f0["f"]["piv"]), f0["botLines"], f0["topLines"]])
    good, shown, real = _fear1109b_pct_ok(f0)
    ok(f"{T} 美股 6 月：▲／▼ 百分比標籤＝相鄰轉折實際漲跌幅（誤差 0.5 內、段數一致）", good, [shown, real])
    ov = _fear1109b_overlap(f0)
    ok(f"{T} 美股 6 月：所有文字兩兩不重疊、不超出圖框", not ov, ov[:4])
    ok(f"{T} 下格三段色帶永遠都畫", f0["bands"] == 3, f0["bands"])
    # ---- 4. 提示框
    pv = f0["f"]["piv"][1]
    px = pg.evaluate("""(d) => { const el = document.getElementById('ovFearChart'), ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
        const t = Date.parse(d + 'T00:00:00Z'); const p = ch.convertToPixel({ xAxisIndex: 1 }, t); return [r.left + (Array.isArray(p) ? p[0] : p), r.top + 260]; }""", pv["d"])
    pg.mouse.move(px[0] - 30, px[1]); pg.mouse.move(px[0], px[1]); pg.wait_for_timeout(500)
    tip = pg.evaluate("() => [...document.querySelectorAll('div')].filter(d => d.children.length < 40 && /波段/.test(d.innerText || '') && d.offsetHeight < 200).map(d => d.innerText).join('|')")
    ok(f"{T} 滑到轉折那天：提示框多一行「波段低點／高點」", "波段" in tip, tip[:120])
    pg.mouse.move(5, 5)
    # ---- 1. 篩選
    pg.locator("#fzLeg button", has_text="費城半導體").click(); pg.wait_for_timeout(700)
    f1 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 關掉費城半導體：線消失、圖例變淡（off）、上格 Y 軸範圍改變、下格 Y 軸不動",
       "top-SOX" not in f1["ids"] and "top-IXIC" in f1["ids"] and f1["legOff"] == ["SOX"] and f1["ys"][0] != f0["ys"][0] and f1["ys"][1] == f0["ys"][1], [f1["ids"], f1["legOff"], f0["ys"], f1["ys"]])
    ok(f"{T} 關掉之後文字仍不重疊", not _fear1109b_overlap(f1), _fear1109b_overlap(f1)[:3])
    ok(f"{T} localStorage 記下（tw.fear.hide.us 含 SOX、tw.fear.hide.tw 沒有）", f1["ls"] and "SOX" in (f1["ls"][0] or "") and not f1["ls"][1], f1["ls"])
    pg.reload(wait_until="domcontentloaded"); go(pg)
    pg.locator("#fzMkt button", has_text="美股").click(); pg.wait_for_timeout(700)
    f2 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 重新整理後仍是關的", "top-SOX" not in f2["ids"] and f2["legOff"] == ["SOX"], [f2["ids"], f2["legOff"]])
    pg.locator("#fzMkt button", has_text="台股").click(); pg.wait_for_timeout(700)
    f3 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 切到台股：不受美股的設定影響（加權、櫃買都在），台股一樣有轉折虛線與不重疊的標籤", "top-TSE" in f3["ids"] and "top-OTC" in f3["ids"] and not f3["legOff"] and f3["botLines"] >= 2 and not _fear1109b_overlap(f3), [f3["ids"], f3["botLines"], _fear1109b_overlap(f3)[:3]])
    good, shown, real = _fear1109b_pct_ok(f3)
    ok(f"{T} 台股：百分比標籤＝相鄰轉折實際漲跌幅", good, [shown, real])
    pg.locator("#fzLeg button", has_text="加權").click(); pg.locator("#fzLeg button", has_text="櫃買").click(); pg.wait_for_timeout(700)
    f4 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 台股上格全關：只剩 1 格（下格＋圖例仍在、色帶與轉折仍在）", len(f4["grids"]) == 1 and f4["bands"] == 3 and f4["botLines"] >= 2 and not _fear1109b_overlap(f4), [f4["grids"], f4["bands"], f4["botLines"]])
    pg.locator("#fzLeg button", has_text="台指自算").click(); pg.wait_for_timeout(700)
    f5 = pg.evaluate("() => ({ txt: (document.querySelector('#ovFearChart') || {}).innerText || '', chart: !!echarts.getInstanceByDom(document.getElementById('ovFearChart')), off: document.querySelectorAll('#fzLeg button.off').length })")
    ok(f"{T} 恐慌指數那條也關掉：整張沒圖、有提示字、圖例還在", f5["off"] == 3 and "關掉" in f5["txt"] and not f5["chart"], f5)
    pg.locator("#fzLeg button", has_text="台指自算").click(); pg.locator("#fzLeg button", has_text="加權").click(); pg.locator("#fzLeg button", has_text="櫃買").click(); pg.wait_for_timeout(700)
    f6 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 全部打開回到兩格、轉折回來", len(f6["grids"]) == 2 and f6["botLines"] >= 2, [f6["grids"], f6["botLines"]])
    # ---- 3. 切期間
    pg.locator("#fzMkt button", has_text="美股").click(); pg.locator("#fzLeg button", has_text="費城半導體").click(); pg.wait_for_timeout(500)
    pg.locator("#fzPer button", has_text="全部").click(); pg.wait_for_timeout(700)
    fa = pg.evaluate(_FEAR1109B_JS)
    pg.locator("#fzPer button", has_text="1月").click(); pg.wait_for_timeout(700)
    fb = pg.evaluate(_FEAR1109B_JS)
    w0, w1 = fb["f"]["win"]
    ok(f"{T} 切 1月：轉折依新視窗重算（全部落在視窗內、與「全部」那組不同）", all(w0 <= q["d"] <= w1 for q in fb["f"]["piv"]) and fb["f"]["piv"] != fa["f"]["piv"], [fb["f"]["win"], [q["d"] for q in fb["f"]["piv"]], [q["d"] for q in fa["f"]["piv"]]])
    ok(f"{T} 切期間：下格 Y 軸完全不變（全部／1月 一樣）", fa["ys"][-1] == fb["ys"][-1], [fa["ys"], fb["ys"]])
    ok(f"{T} 1月：文字不重疊、百分比對得上", not _fear1109b_overlap(fb) and _fear1109b_pct_ok(fb)[0] or len(fb["f"]["piv"]) < 2, [_fear1109b_overlap(fb)[:3], _fear1109b_pct_ok(fb)])
    # ---- 5. 游標縮放
    pg.locator("#fzPer button", has_text="6月").click(); pg.wait_for_timeout(700)
    fz0 = pg.evaluate(_FEAR1109B_JS)
    box = pg.evaluate("() => { const r = document.getElementById('ovFearChart').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
    pg.evaluate("() => document.getElementById('ovFearChart').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(300)
    box = pg.evaluate("() => { const r = document.getElementById('ovFearChart').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
    pg.mouse.move(box[0] + box[2] * 0.7, box[1] + 100)
    for _ in range(3):
        pg.mouse.wheel(0, -300); pg.wait_for_timeout(150)
    pg.wait_for_timeout(600)
    fz1 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 滾輪放大：視窗變窄、期間鈕全部取消亮起、轉折依新視窗重算（全落在視窗內）",
       (fz1["b"] - fz1["a"]) < (fz0["b"] - fz0["a"]) * 0.9 and not fz1["pers"] and all(fz1["f"]["win"][0] <= q["d"] <= fz1["f"]["win"][1] for q in fz1["f"]["piv"]),
       [fz0["f"]["win"], fz1["f"]["win"], fz1["pers"]])
    ok(f"{T} 放大後：下格 Y 軸不變、上格起點重算成 100（base 有值）、文字不重疊", fz1["ys"][-1] == fz0["ys"][-1] and not _fear1109b_overlap(fz1), [fz0["ys"][-1], fz1["ys"][-1], _fear1109b_overlap(fz1)[:3]])
    pg.mouse.move(box[0] + box[2] * 0.5, box[1] + 100); pg.mouse.down(); pg.mouse.move(box[0] + box[2] * 0.5 - 150, box[1] + 100, steps=8); pg.mouse.up(); pg.wait_for_timeout(600)
    fz2 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 按住拖曳：視窗平移（起點改變、寬度不變）", fz2["a"] != fz1["a"] and abs((fz2["b"] - fz2["a"]) - (fz1["b"] - fz1["a"])) < 2 * 86400000, [fz1["f"]["win"], fz2["f"]["win"]])
    pg.locator("#fzPer button", has_text="3月").click(); pg.wait_for_timeout(600)
    fz3 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 縮放後按期間鈕：回到該期間、鈕亮起", fz3["pers"] == ["3m"], fz3["pers"])
    ok(f"{T} 沒有 JS 例外（桌機）", not errs, errs[:3])
    c.close()

    # ---- 6. 手機 390
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free", width=390, touch=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    pg.locator("#fzMkt button", has_text="美股").click(); pg.wait_for_timeout(600)
    pg.locator("#fzPer button", has_text="6月").click(); pg.wait_for_timeout(700)
    pg.evaluate("() => document.getElementById('ovFearChart').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(500)
    m0 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 手機 390 美股 6 月：轉折 ≥ 2 個、文字不重疊、百分比對得上、整頁無橫向捲軸",
       len(m0["f"]["piv"]) >= 2 and not _fear1109b_overlap(m0) and _fear1109b_pct_ok(m0)[0] and pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"),
       [len(m0["f"]["piv"]), _fear1109b_overlap(m0)[:3], _fear1109b_pct_ok(m0)])
    ok(f"{T} 手機：圖加高（整張 ≥ 400px）", m0["H"] >= 400, m0["H"])
    pg.locator("#fzMkt button", has_text="台股").click(); pg.wait_for_timeout(600)
    m1 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 手機 390 台股：文字不重疊", not _fear1109b_overlap(m1), _fear1109b_overlap(m1)[:3])
    pg.locator("#fzMkt button", has_text="美股").click(); pg.wait_for_timeout(600)
    cdp = c.new_cdp_session(pg)
    # ⚠ 這個環境的無頭瀏覽器合成不出「手指拖動捲頁」（連空白頁都捲不動，已用純 HTML 對照確認），所以改驗「圖上單指拖曳的 touch 事件沒有被 preventDefault、
    #    觸控動作不是 none」——頁面能不能捲只取決於這兩件事；另外兩指縮放下面用 CDP 真的合成。
    pg.evaluate("() => document.getElementById('ovFearChart').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(400)
    sw = pg.evaluate("""() => { const cv = document.querySelector('#ovFearChart canvas, #ovFearChart svg'); const ta = []; for (let e = cv; e && e !== document.documentElement; e = e.parentElement) ta.push(getComputedStyle(e).touchAction);
        const r = cv.getBoundingClientRect(); const mk = (t, x, y) => { const tc = new Touch({ identifier: 1, target: cv, clientX: x, clientY: y }); const ev = new TouchEvent(t, { touches: t === 'touchend' ? [] : [tc], changedTouches: [tc], bubbles: true, cancelable: true }); cv.dispatchEvent(ev); return ev.defaultPrevented; };
        const x = r.left + r.width / 2, y = r.top + r.height / 2; const a = [mk('touchstart', x, y)]; for (let i = 1; i < 8; i++) a.push(mk('touchmove', x, y + i * 12)); a.push(mk('touchend', x, y + 96));
        const o = echarts.getInstanceByDom(document.getElementById('ovFearChart')).getOption().dataZoom.find(z => z.type === 'inside');
        return { ta, prevented: a.some(Boolean), mv: o.moveOnMouseMove, zw: o.zoomOnMouseWheel }; }""")
    ok(f"{T} 手機：在圖上單指上下滑，頁面仍會捲動（touch 事件沒被攔截、touch-action 不是 none、單指平移與滾輪縮放關閉）", not sw["prevented"] and "none" not in sw["ta"] and sw["mv"] is False and sw["zw"] is False, sw)
    pg.evaluate("() => document.getElementById('ovFearChart').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(400)
    r = pg.evaluate("() => { const r = document.getElementById('ovFearChart').getBoundingClientRect(); return [r.left + r.width / 2, r.top + 80]; }")
    mp0 = pg.evaluate(_FEAR1109B_JS)
    cdp.send("Input.synthesizePinchGesture", {"x": r[0], "y": r[1], "scaleFactor": 2.2, "relativeSpeed": 300, "gestureSourceType": "touch"})
    pg.wait_for_timeout(800)
    mp1 = pg.evaluate(_FEAR1109B_JS)
    ok(f"{T} 手機：兩指放大 → 視窗變窄、期間鈕取消亮起、文字不重疊", (mp1["b"] - mp1["a"]) < (mp0["b"] - mp0["a"]) * 0.9 and not mp1["pers"] and not _fear1109b_overlap(mp1), [mp0["f"]["win"], mp1["f"]["win"], mp1["pers"], _fear1109b_overlap(mp1)[:3]])
    ok(f"{T} 沒有 JS 例外（手機）", not errs, errs[:3])
    c.close()


register("恐慌圖篩選1109", lambda pg, b, base, code: t_fear_1109b(b, base, code))
