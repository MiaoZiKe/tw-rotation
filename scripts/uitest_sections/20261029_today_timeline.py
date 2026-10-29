# 驗收段落「今日時間軸1029」—— Andy 10-29：「即時…新增時間軸，開盤到最新時間，可以播放當日狀況，資金流水也是」「熱力圖也是」。
# 假時鐘（台北 10:30）＋假 Worker（/quote 漂移報價、/tape 回 09:00～10:25 共 18 格 NDJSON），真的拖拉、真的播放，驗畫面真的因此改變。
# 由 _uitest.py 用 exec 載入，ok()／wait_until()／count()／text()／fails／SITE 直接可用。
# flake8: noqa

def t_today_timeline_1029(b, base):
    import json as _json
    import datetime as _dt
    import time as _time
    from urllib.parse import urlparse, parse_qs
    T = "今日時間軸1029"
    S = {"k": 0}
    day = _dt.date(2026, 10, 29)
    DAY = day.isoformat(); DAY8 = DAY.replace("-", "")
    CLK = f"{DAY}T02:30:00Z"            # 台北 10:30
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
        pg.evaluate("([id, p]) => { const i = document.querySelector('#' + id + ' input'); i.value = p; i.dispatchEvent(new Event('input', {bubbles: true})); }", [bar_id, pos])
        pg.wait_for_timeout(700)

    def val(pg, bar_id):
        return pg.evaluate("(id) => (document.querySelector('#' + id + ' .val') || {}).textContent", bar_id)

    ROT = "() => JSON.stringify(App.rlvState().pts)"
    # ------------------------------------------------------------------ ① 資金輪盤
    ctx, pg = open_page("#flow/rotation")
    wait_until(pg, "() => !!document.querySelector('#rotClock canvas') && !!document.getElementById('rotLiveBtn')", 25000)
    ok(f"[{T}] ① 沒開即時：沒有今日時間軸、日線拉桿在", count(pg, "#rotTl") == 0 and pg.evaluate("() => !!document.querySelector('#rotBack input[type=range]') && !document.getElementById('rotBack').classList.contains('tlon')"))
    pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0 && Object.keys(s.pts).length > 0; }", 60000, 400)
    wait_until(pg, "() => !!document.getElementById('rotTl')", 15000)
    ok(f"[{T}] ① 開即時後出現「今日時間軸」，且日線拉桿藏起來（兩條不重複）、只剩「即時」鈕",
       count(pg, "#rotTl") == 1 and pg.evaluate("() => { const b = document.getElementById('rotBack'); return b.classList.contains('tlon') && ![...b.children].some(e => !e.classList.contains('livebtn') && e.getClientRects().length > 0); }"))
    ok(f"[{T}] ① 時間軸左端 09:00、共 {NSLOT} 格、目前在「最新」",
       pg.evaluate("() => document.querySelector('#rotTl .tl0').textContent") == "09:00" and pg.evaluate("() => +document.querySelector('#rotTl input').max") == NSLOT and val(pg, "rotTl") == "最新")
    live_sig = pg.evaluate(ROT)
    drag(pg, "rotTl", 12)       # 10:00
    s10 = pg.evaluate(ROT)
    ok(f"[{T}] ① ★ 拖到 10:00：標籤寫 10:00、狀態字「回放 10:00」、輪盤座標跟最新不同", val(pg, "rotTl") == "10:00" and "回放 10:00" in text(pg, "#rotLiveTag") and s10 != live_sig)
    drag(pg, "rotTl", 3)        # 09:15
    s0915 = pg.evaluate(ROT)
    ok(f"[{T}] ① ★ 再拖到 09:15：座標又不一樣（不是只換了標籤）", val(pg, "rotTl") == "09:15" and s0915 != s10)
    pg.click("#rotTl .pb.play")
    pg.wait_for_timeout(2500)
    mid = val(pg, "rotTl")
    ok(f"[{T}] ① ★ 按 ▶ 重播：2.5 秒後時間往後走了、鈕變 ⏸、拉桿反灰", mid not in ("09:15", "最新") and text(pg, "#rotTl .pb.play") == "⏸" and pg.evaluate("() => document.getElementById('rotTl').classList.contains('playdim')"), mid)
    ok(f"[{T}] ① 播放中輪盤座標隨之改變", pg.evaluate(ROT) not in (s0915, live_sig))
    wait_until(pg, "() => !Tape.playing", 30000, 300)
    ok(f"[{T}] ① ★ 播到最後自動回到「最新」並停止，輪盤回到即時的座標", val(pg, "rotTl") == "最新" and text(pg, "#rotTl .pb.play") == "▶" and not pg.evaluate("() => Tape.pinned()"))
    pg.wait_for_timeout(6500)
    ok(f"[{T}] ① 回到最新後繼續跟新資料（狀態字回「即時」）", "即時" in text(pg, "#rotLiveTag") and "回放" not in text(pg, "#rotLiveTag"))
    drag(pg, "rotTl", 6)
    pg.click("#rotTl .pb.latest"); pg.wait_for_timeout(700)
    ok(f"[{T}] ① 「最新」鈕：回到最新", val(pg, "rotTl") == "最新")
    # ② 資金分流樹（同頁）
    pg.evaluate("() => { location.hash = '#flow/sankey'; }")
    wait_until(pg, "() => !!document.getElementById('sankeyLiveBtn')", 20000)
    pg.click("#sankeyLiveBtn")
    wait_until(pg, "() => { const s = App.sklSig(); return s.on && !s.err && s.sig.length > 0; }", 60000, 400)
    wait_until(pg, "() => !!document.getElementById('sankeyTl')", 15000)
    ok(f"[{T}] ② 分流樹開即時：出現今日時間軸、日線拉桿藏起來", count(pg, "#sankeyTl") == 1 and pg.evaluate("() => document.getElementById('sankeyDays').classList.contains('tlon')"))
    k0 = pg.evaluate("() => App.sklSig().sig")
    drag(pg, "sankeyTl", 4)
    k1 = pg.evaluate("() => App.sklSig().sig")
    ok(f"[{T}] ② ★ 拖到 09:20：各板塊成交值跟最新不同、標籤 09:20", val(pg, "sankeyTl") == "09:20" and k1 != k0)
    drag(pg, "sankeyTl", 9)
    ok(f"[{T}] ② ★ 再拖到 09:45：又不一樣", val(pg, "sankeyTl") == "09:45" and pg.evaluate("() => App.sklSig().sig") != k1)
    pg.click("#sankeyLiveBtn"); pg.wait_for_timeout(600)
    ok(f"[{T}] ② 關掉即時：分流樹的時間軸消失、日線拉桿回來", count(pg, "#sankeyTl") == 0 and pg.evaluate("() => !document.getElementById('sankeyDays').classList.contains('tlon')"))
    pg.evaluate("() => { const b = document.getElementById('rotLiveBtn'); if (b && App.rlvState().on) b.click(); }")
    pg.wait_for_timeout(800)
    ok(f"[{T}] ② 所有圖的即時都關了：游標回到最新", not pg.evaluate("() => Tape.pinned()"))
    ctx.close()

    # ------------------------------------------------------------------ ③ 熱力圖：產業、題材
    for route, card, tid, sig_id in (("#heatmap/industry", "[data-hlcard=ind]", "indTl", "indTree"), ("#heatmap/theme", "#themeMapCard", "themeTl", "themeMap")):
        ctx, pg = open_page(route)
        wait_until(pg, f"() => !!document.querySelector('#{sig_id} canvas, #{sig_id} svg')", 20000)
        wait_until(pg, f"() => !!document.querySelector('{card}') && document.querySelector('{card}').dataset.snapLive === 'live'", 90000, 400)
        if sig_id == "themeMap":
            pg.select_option("#themeColorSel", "chg")
        wait_until(pg, f"() => !!document.getElementById('{tid}')", 15000)
        ok(f"[{T}] ③ {route}：即時開著時卡片有今日時間軸", count(pg, f"#{tid}") == 1 and val(pg, tid) == "最新")
        h0 = pg.evaluate(HL_SIG, sig_id)
        drag(pg, tid, 5)
        h1 = pg.evaluate(HL_SIG, sig_id)
        ok(f"[{T}] ③ ★ {route}：拖到 09:25，格子顏色／面積跟最新不同", val(pg, tid) == "09:25" and bool(h1) and h1 != h0)
        drag(pg, tid, 14)
        ok(f"[{T}] ③ ★ {route}：再拖到 10:10 又不同", pg.evaluate(HL_SIG, sig_id) not in (h1, h0))
        pg.click(f"#{tid} .pb.play"); pg.wait_for_timeout(1800)
        ok(f"[{T}] ③ {route}：▶ 重播中時間在走", val(pg, tid) not in ("10:10", "最新"))
        wait_until(pg, "() => !Tape.playing", 30000, 300)
        pg.wait_for_timeout(800)
        ok(f"[{T}] ③ {route}：播完回到最新", val(pg, tid) == "最新" and not pg.evaluate("() => Tape.pinned()"))
        pg.click(f"{card} .livetg-b"); pg.wait_for_timeout(800)
        ok(f"[{T}] ③ {route}：關掉熱力圖即時後時間軸消失", count(pg, f"#{tid}") == 0)
        ctx.close()

    # ------------------------------------------------------------------ ④ 手機 390
    ctx, pg = open_page("#flow/rotation", vp={"width": 390, "height": 844}, mobile=True)
    wait_until(pg, "() => !!document.getElementById('rotLiveBtn')", 25000)
    pg.click("#rotLiveBtn")
    wait_until(pg, "() => !!document.getElementById('rotTl')", 60000, 400)
    m = pg.evaluate("""() => { const bar = document.getElementById('rotTl').getBoundingClientRect(), i = document.querySelector('#rotTl input').getBoundingClientRect();
      return { bw: bar.width, ih: i.height, sw: document.documentElement.scrollWidth, iw: window.innerWidth, right: bar.right,
        btn: Math.min(...[...document.querySelectorAll('#rotTl .pb')].map(e => e.getBoundingClientRect().height)) }; }""")
    ok(f"[{T}] ④ 手機 390：時間軸不超出畫面、無橫向捲軸、拉桿高度與按鈕 ≥32px", m["right"] <= m["iw"] + 1 and m["sw"] <= m["iw"] + 1 and m["ih"] >= 32 and m["btn"] >= 32, m)
    drag(pg, "rotTl", 8)
    ok(f"[{T}] ④ 手機拖到 09:40 圖跟著變", val(pg, "rotTl") == "09:40" and "回放" in text(pg, "#rotLiveTag"))
    ctx.close()

    # ------------------------------------------------------------------ ⑤ 伺服器快照沒有時：退回頁面自己累積，不壞
    ctx = b.new_context(viewport={"width": 1440, "height": 1000}, timezone_id="Asia/Taipei")
    ctx.add_init_script("window.TW_LIVE_OVERRIDE = true;")
    pg = ctx.new_page(); pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
    pg.clock.install(time=CLK)
    pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg.route("https://fake-worker.test/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
    pg.route("https://fake-worker.test/quote?*", fake_quote)
    pg.goto(base + "#flow/rotation", wait_until="domcontentloaded")
    pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); localStorage.setItem('tw.tour','done'); } catch (e) {} }")
    pg.goto("about:blank"); pg.goto(base + "#flow/rotation", wait_until="load")
    wait_until(pg, "() => !!document.getElementById('rotLiveBtn')", 25000)
    pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && s.at > 0; }", 60000, 400)
    pg.wait_for_timeout(8000)
    ok(f"[{T}] ⑤ 沒有伺服器快照（/tape 404）：頁面不報錯、輪盤照常即時（時間軸等本機累積夠一格才出現）", pg.evaluate("() => App.rlvState().err") == "" and pg.evaluate("() => Tape.source") in ("none", "local"))
    ctx.close()


HL_SIG = globals().get("HL_SIG") or """(id) => { const el = document.getElementById(id); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return null;
  const out = []; const walk = (a) => (a || []).forEach(d => { if (d.children && d.children.length) walk(d.children);
    else out.push([d.name, Math.round(d.value || 0), (d.itemStyle && d.itemStyle.color) || '']); });
  walk(((i.getOption().series || [])[0] || {}).data); return JSON.stringify(out); }"""
register("今日時間軸1029", lambda pg, b, base, code: t_today_timeline_1029(b, base))
