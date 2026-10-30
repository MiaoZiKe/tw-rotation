# 驗收段落「今日走勢驗證1030」—— Andy 10-30：「即時模式將移動變化幅度大一點，並且是否有方法讓他驗證（例：PCB 今日轉弱，看相關族群全部走勢是否開高走低）」。
# 假時鐘（台北 10:30）＋假 Worker（/quote、/tape 18 格），真的點排行長條開「今日走勢驗證」面板、拖時間軸、切相關族群、看全部、關閉；
# 另驗：型態判斷函式、即時位移放大倍率與圖腳字、播放中排行不做更新動畫（兩組數字疊在一起那個 bug）、手機底部抽屜。
# flake8: noqa

def t_today_verify_1030(b, base):
    import json as _json
    import datetime as _dt
    import time as _time
    from urllib.parse import urlparse, parse_qs
    T = "今日走勢驗證1030"
    S = {"k": 0}
    DAY = "2026-10-29"; DAY8 = DAY.replace("-", "")
    CLK = f"{DAY}T02:30:00Z"
    codes = _json.loads((SITE / "data" / "tape_codes.json").read_text(encoding="utf-8"))["codes"]
    NSLOT = 18

    def chg_of(c, i):
        h = sum(ord(ch) * (k + 3) for k, ch in enumerate(c))
        return (((h * 7) % 21) - 10) * 0.2 * (1 + i / 6.0) + ((i % 7) - 3) * 0.9 * (1 if h % 2 else -1)

    def tape_body():
        lines = [_json.dumps({"date": DAY, "codes": [c[0] for c in codes], "y": [100.0] * len(codes)})]
        for i in range(NSLOT):
            m = 9 * 60 + i * 5
            lines.append(_json.dumps({"t": "%02d:%02d" % (m // 60, m % 60),
                                      "p": [round(100 * (1 + chg_of(c[0], i) / 100), 2) for c in codes],
                                      "v": [1000 + (sum(map(ord, c[0])) % 50) * 100 + i * 400 for c in codes]}))
        return "\n".join(lines) + "\n"
    TAPE = tape_body()

    def fake_quote(route):
        ex = (parse_qs(urlparse(route.request.url).query).get("ex_ch") or [""])[0]
        S["k"] += 1
        arr = []
        for tok in [t for t in ex.split("|") if t]:
            try:
                c = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            if c in ("t00", "o00"):
                z, y = 20100, 20000
            else:
                y = 100.0
                z = round(y * (1 + chg_of(c, NSLOT + 2) / 100), 2)
            arr.append({"c": c, "n": "測試" + c, "ex": tok[:3], "z": f"{z:.2f}", "y": f"{y:.2f}", "o": f"{y:.2f}", "h": f"{max(z, y) + 1:.2f}",
                        "l": f"{min(z, y) - 1:.2f}", "v": str(1000 + (sum(map(ord, c)) % 50) * 100 + NSLOT * 400), "t": "10:29:50", "d": DAY8,
                        "tlong": str(int(_time.time() * 1000))})
        route.fulfill(status=200, content_type="application/json; charset=utf-8", body=_json.dumps({"rtcode": "0000", "msgArray": arr}))

    def open_page(route_hash, vp=None, mobile=False):
        kw = {"viewport": vp or {"width": 1440, "height": 1000}, "timezone_id": "Asia/Taipei"}
        if mobile:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script("window.TW_LIVE_OVERRIDE = true;")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.clock.install(time=CLK)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("https://fake-worker.test/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
        pg.route("https://fake-worker.test/quote?*", fake_quote)
        pg.route("https://fake-worker.test/tape*", lambda r: r.fulfill(status=200, content_type="application/x-ndjson", body=TAPE))
        pg.goto(base + route_hash, wait_until="domcontentloaded")
        pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); localStorage.setItem('tw.tour','done'); } catch (e) {} }")
        pg.goto("about:blank")
        pg.goto(base + route_hash, wait_until="load")
        return ctx, pg

    def drag(pg, bar_id, pos):
        pg.evaluate("([id, p]) => { const i = document.querySelector('#' + id + ' input.tlr'); i.value = p; i.dispatchEvent(new Event('input', {bubbles: true})); }", [bar_id, pos])
        pg.wait_for_timeout(700)

    def val(pg, bar_id):
        return pg.evaluate("(id) => (document.querySelector('#' + id + ' .val') || {}).textContent", bar_id)

    def Tape_step(pg):
        return pg.evaluate("() => Tape.stepMs")


    # ------------------------------------------------------------------ 型態判斷函式
    ctx, pg = open_page("#flow/rotation")
    wait_until(pg, "() => !!window.App && !!App.tvPattern", 20000)
    cases = {"開高走低": [1.0, 1.2, 0.9, 0.4, -0.2, -0.6], "開低走高": [-1.0, -0.8, -0.2, 0.4, 0.9], "盤整": [0.1, 0.2, 0.0, 0.15, 0.1],
             "一路走高": [0.1, 0.4, 0.8, 1.2, 1.6], "一路走低": [-0.1, -0.5, -0.9, -1.4], "盤整2": [0.5, 1.4, 1.0, 0.2, 0.55]}
    got = {k: pg.evaluate("(a) => (App.tvPattern(a) || {}).name", v) for k, v in cases.items()}
    ok(f"[{T}] 型態判斷：開高走低／開低走高／盤整／一路走高／一路走低 都判得對（衝高回到原點算盤整）",
       got == {"開高走低": "開高走低", "開低走高": "開低走高", "盤整": "盤整", "一路走高": "一路走高", "一路走低": "一路走低", "盤整2": "盤整"}, got)
    # ------------------------------------------------------------------ 即時：位移放大、開面板
    wait_until(pg, "() => !!document.getElementById('rotLiveBtn')", 25000); pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0 && Object.keys(s.pts).length > 0; }", 60000, 400)
    wait_until(pg, "() => !!document.getElementById('rotTl')", 15000)
    pg.wait_for_timeout(1500)
    k = pg.evaluate("() => App.rlvState().k")
    ok(f"[{T}] ★ 即時：點的位移已放大（倍率 ×{k} ≥ 1.5、上限 12），圖腳寫「位移已放大 ×N」", 1.5 <= k <= 12 and
       pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock')); return JSON.stringify(c.getOption().graphic || []).indexOf('位移已放大') >= 0; }"), k)
    ok(f"[{T}] 沒點族群之前沒有驗證面板", count(pg, "#todayVerify:not([hidden])") == 0)
    pos = pg.evaluate("""() => { const el = document.getElementById('rankFlow'), c = echarts.getInstanceByDom(el); const rows = el._rfRows || [];
      const i = rows.length - 1; const g = rows[i]; const px = c.convertToPixel({ seriesIndex: 0 }, [g.share_chg * 0.5, i]); const r = el.getBoundingClientRect();
      return { x: r.left + px[0], y: r.top + px[1], gid: g.group_id, n: rows.length }; }""")
    pg.mouse.click(pos["x"], pos["y"])
    wait_until(pg, "() => { const e = document.getElementById('todayVerify'); return !!e && !e.hidden && !!e.querySelector('.tvrow'); }", 15000)
    st = pg.evaluate("() => ({ gid: document.getElementById('todayVerify').dataset.gid, pat: (document.getElementById('tvPat') || {}).textContent, rows: document.querySelectorAll('#tvList .tvrow').length, sp: document.querySelectorAll('#tvList .tvrow svg.tvspark polyline').length, canvas: document.querySelectorAll('#tvChart canvas, #tvChart svg').length, tv: App._tv, conc: (document.getElementById('tvConc') || {}).textContent })")
    ok(f"[{T}] ★ 點排行長條 → 開「今日走勢驗證」面板（族群正確、有分時圖、有結論）", st["gid"] == pos["gid"] and st["canvas"] > 0 and len(st["conc"] or "") > 20, [st, pos])
    calc = pg.evaluate("(g) => { const r = App.tvCalc(g); return { pat: r.pat && r.pat.name, n: r.stocks.length, times: r.times.length }; }", pos["gid"])
    ok(f"[{T}] ★ 型態判斷：面板寫的型態（{st['pat']}）＝ 用同一份分時資料重算的結果，且是五種之一", st["pat"] == calc["pat"] and st["pat"] in ("開高走低", "開低走高", "盤整", "一路走高", "一路走低"), [st["pat"], calc])
    ok(f"[{T}] ★ 成分股每檔一條小分時線：列數 {st['rows']}＝min(10, {calc['n']})，每列都有 sparkline（{st['sp']} 條）", st["rows"] == min(10, calc["n"]) and st["sp"] == st["rows"] and st["rows"] > 0)
    if calc["n"] > 10:
        pg.click("#todayVerify .tvmore"); pg.wait_for_timeout(500)
        ok(f"[{T}] 「看全部」展開到全部 {calc['n']} 檔", pg.evaluate("() => document.querySelectorAll('#tvList .tvrow').length") == calc["n"])
        pg.click("#todayVerify .tvmore"); pg.wait_for_timeout(300)
    # 拖時間軸到 09:30：面板只算到那一格
    pg.evaluate("() => { const i = document.querySelector('#rotTl input.tlr'); i.value = 6; i.dispatchEvent(new Event('input', {bubbles: true})); }")
    pg.wait_for_timeout(1200)
    t6 = pg.evaluate("() => App._tv")
    ok(f"[{T}] ★ 時間軸拖到 09:30：驗證面板只算到那一格（共 7 格、最後是 09:30）", t6["times"] == 7 and t6["cur"] == "09:30", t6)
    pg.evaluate("() => { const i = document.querySelector('#rotTl input.tlr'); i.value = 18; i.dispatchEvent(new Event('input', {bubbles: true})); }")
    pg.wait_for_timeout(1200)
    # 相關族群一鍵切換
    nrel = count(pg, "#todayVerify .tvrel button")
    if nrel:
        g0 = pg.evaluate("() => document.getElementById('todayVerify').dataset.gid")
        pg.click("#todayVerify .tvrel button"); pg.wait_for_timeout(1500)
        g1 = pg.evaluate("() => document.getElementById('todayVerify').dataset.gid")
        ok(f"[{T}] ★ 相關族群（同產業鏈 {nrel} 個）一鍵切換：面板換成另一個族群、仍有 sparkline", g1 != g0 and count(pg, "#tvList .tvrow svg.tvspark") > 0, [g0, g1])
    else:
        ok(f"[{T}] 這個族群沒有同產業鏈的相關族群（略過切換）", True)
    pg.click("#todayVerify .tvx"); pg.wait_for_timeout(400)
    ok(f"[{T}] 按 ✕ 關閉面板", pg.evaluate("() => document.getElementById('todayVerify').hidden") is True)
    # 重開、關即時一起收
    pg.mouse.click(pos["x"], pos["y"]); wait_until(pg, "() => { const e = document.getElementById('todayVerify'); return !!e && !e.hidden; }", 15000)
    pg.click("#rotLiveBtn"); pg.wait_for_timeout(1500)
    ok(f"[{T}] 關掉即時：驗證面板一起收起", pg.evaluate("() => document.getElementById('todayVerify').hidden") is True)
    # ------------------------------------------------------------------ 排行：播放中不做更新動畫
    pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0; }", 60000, 400); wait_until(pg, "() => !!document.getElementById('rotTl')", 15000)
    pg.evaluate("() => Tape.setSpeed(3)")
    pg.evaluate("() => { const i = document.querySelector('#rotTl input.tlr'); i.value = 1; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(800)
    pg.click("#rotTl .pb.play"); pg.wait_for_timeout(700)
    an = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow')); return { playing: Tape.playing, d: c.getOption().animationDurationUpdate }; }")
    ok(f"[{T}] ★ 播放中族群資金排行不做更新動畫（兩根長條換位途中不會讓標籤疊在一起）", an["playing"] and an["d"] == 0, an)
    pg.click("#rotTl .pb.play"); pg.evaluate("() => Tape.setSpeed(1)")
    ctx.close()
    # ------------------------------------------------------------------ 手機 390：底部抽屜
    ctx, pg = open_page("#flow/rotation", vp={"width": 390, "height": 844}, mobile=True)
    wait_until(pg, "() => !!document.getElementById('rotLiveBtn')", 25000); pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0; }", 60000, 400); wait_until(pg, "() => !!document.getElementById('rotTl')", 15000)
    pg.evaluate("() => App.tvOpen(Object.keys(App.rlvState().pts)[0])")
    wait_until(pg, "() => { const e = document.getElementById('todayVerify'); return !!e && !e.hidden && !!e.querySelector('.tvrow'); }", 15000)
    pg.wait_for_timeout(800)
    mb = pg.evaluate("""() => { const e = document.getElementById('todayVerify'), r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      return { pos: cs.position, bottom: Math.round(r.bottom), h: innerHeight, left: Math.round(r.left), right: Math.round(r.right), w: innerWidth, sw: document.documentElement.scrollWidth,
        x: Math.round(e.querySelector('.tvx').getBoundingClientRect().height) }; }""")
    ok(f"[{T}] ★ 手機：驗證面板是底部抽屜（fixed、貼底、不超出寬度、無橫向捲軸、關閉鈕 ≥40px）", mb["pos"] == "fixed" and abs(mb["bottom"] - mb["h"]) <= 14 and mb["left"] >= 0 and mb["right"] <= mb["w"] and mb["sw"] <= mb["w"] + 1 and mb["x"] >= 40, mb)
    ctx.close()


register("今日走勢驗證1030", lambda pg, b, base, code: t_today_verify_1030(b, base))
