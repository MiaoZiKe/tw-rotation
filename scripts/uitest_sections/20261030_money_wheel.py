# 驗收段落「資金輪盤1030」—— Andy 10-30 拍板「改名＋再做真正資金輪盤」：資金流向頁那張輪盤從「資金輪盤」改名「強弱輪動」，
# 並在同一張卡加「強弱輪動｜資金輪盤」切換（資金輪盤＝成交值占比版，後端 compute/money_wheel.py）。
# 假時鐘（台北 10:30）＋假 Worker 的 /quote（漂移報價）與 /tape，真的切換、真的按象限、真的播放、真的開即時、真的拖今日時間軸，驗畫面真的因此改變。
# 由 _uitest.py 用 exec 載入，ok()／wait_until()／count()／text()／fails／SITE 直接可用。
# flake8: noqa

def t_money_wheel_1030(b, base):
    import json as _json
    import datetime as _dt
    import time as _time
    from urllib.parse import urlparse, parse_qs
    T = "資金輪盤1030"
    S = {"k": 0}
    DAY = "2026-10-29"; DAY8 = DAY.replace("-", "")
    CLK = f"{DAY}T02:30:00Z"            # 台北 10:30
    codes = _json.loads((SITE / "data" / "tape_codes.json").read_text(encoding="utf-8"))["codes"]
    NSLOT = 18

    def chg_of(c, i):
        h = sum(ord(ch) * (k + 3) for k, ch in enumerate(c))
        return (((h * 7) % 21) - 10) * 0.2 * (1 + i / 6.0) + ((i % 7) - 3) * 0.9 * (1 if h % 2 else -1)

    def vol_of(c, i):
        h = sum(map(ord, c))
        return 1000 + (h % 50) * 100 + (i * 400 if h % 3 else i * 40)      # 三分之二的股票量越來越大、其餘幾乎不動 → 各族群占比會隨時間改變

    lines = [_json.dumps({"date": DAY, "codes": [c[0] for c in codes], "y": [100.0] * len(codes)})]
    for i in range(NSLOT):
        m = 9 * 60 + i * 5
        lines.append(_json.dumps({"t": "%02d:%02d" % (m // 60, m % 60),
                                  "p": [round(100 * (1 + chg_of(c[0], i) / 100), 2) for c in codes],
                                  "v": [vol_of(c[0], i) for c in codes]}))
    TAPE = "\n".join(lines) + "\n"

    def fake_quote(route):
        ex = (parse_qs(urlparse(route.request.url).query).get("ex_ch") or [""])[0]
        S["k"] += 1
        arr = []
        for tok in [t for t in ex.split("|") if t]:
            try:
                c = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            y = 20000 if c in ("t00", "o00") else 100.0
            z = 20100 if c in ("t00", "o00") else round(y * (1 + chg_of(c, NSLOT + 2) / 100), 2)
            arr.append({"c": c, "n": "測試" + c, "ex": tok[:3], "z": f"{z:.2f}", "y": f"{y:.2f}", "o": f"{y:.2f}", "h": f"{max(z, y) + 1:.2f}",
                        "l": f"{min(z, y) - 1:.2f}", "v": str(vol_of(c, NSLOT)), "t": "10:29:50", "d": DAY8, "tlong": str(int(_time.time() * 1000))})
        route.fulfill(status=200, content_type="application/json; charset=utf-8", body=_json.dumps({"rtcode": "0000", "msgArray": arr}))

    def open_page(route_hash, vp=None, mobile=False, live=False):
        kw = {"viewport": vp or {"width": 1440, "height": 1000}, "timezone_id": "Asia/Taipei"}
        if mobile:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        if live:
            ctx.add_init_script("window.TW_LIVE_OVERRIDE = true;")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        if live:
            pg.clock.install(time=CLK)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        if live:
            pg.route("https://fake-worker.test/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
            pg.route("https://fake-worker.test/quote?*", fake_quote)
            pg.route("https://fake-worker.test/tape*", lambda r: r.fulfill(status=200, content_type="application/x-ndjson", body=TAPE))
            pg.goto(base + route_hash, wait_until="domcontentloaded")
            pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); localStorage.setItem('tw.tour','done'); } catch (e) {} }")
            pg.goto("about:blank")
        pg.goto(base + route_hash, wait_until="load")
        return ctx, pg

    # 時鐘上每個族群點的座標（echarts series 的 data）→ 一個簽章字串，用來驗「畫面真的變了」
    SIG = """() => { const el = document.getElementById('rotClock'); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return '';
      return JSON.stringify((i.getOption().series || []).map(s => (s.data || []).slice(0, 80).map(d => (d && (d.value || d)) || null))); }"""
    HEAD = "() => ({ title: (document.getElementById('rotModeTitle') || {}).textContent, note: (() => { const n = document.getElementById('rotModeNote'); return n && !n.hidden ? n.textContent : ''; })(), "\
           "quads: [...document.querySelectorAll('#rotClockWrap .rquad, #rotClockWrap [data-stage]')].map(e => e.textContent.replace(/\\s+/g, ' ').trim()) })"

    # ------------------------------------------------------------------ ① 桌機：切換、象限、回放
    ctx, pg = open_page("#flow/rotation")
    wait_until(pg, "() => !!document.querySelector('#rotClock canvas') && document.querySelectorAll('#rotModeSeg button').length === 2", 30000)
    h0 = pg.evaluate(HEAD)
    ok(f"[{T}] ① 輪盤標題旁有「強弱輪動｜資金輪盤」切換，預設選強弱輪動、標題＝強弱輪動、沒有「與價格同步」提示",
       pg.evaluate("() => [...document.querySelectorAll('#rotModeSeg button')].map(b => b.textContent).join('|')") == "強弱輪動|資金輪盤"
       and "強弱輪動" in text(pg, "#rotModeSeg button.on") and h0["title"] == "強弱輪動" and not h0["note"], h0)
    quad0 = text(pg, "#rotClockWrap")
    sig0 = pg.evaluate(SIG)
    ok(f"[{T}] ① 強弱輪動模式四段名＝領先／改善／轉弱／落後", all(w in quad0 for w in ("領先", "改善", "轉弱", "落後")), quad0[:120])
    pg.click("#rotModeSeg button[data-rm=money]"); pg.wait_for_timeout(1800)
    h1 = pg.evaluate(HEAD); quad1 = text(pg, "#rotClockWrap"); sig1 = pg.evaluate(SIG)
    ok(f"[{T}] ① ★ 切到資金輪盤：標題換成「資金輪盤」、出現「與價格同步，不是提前訊號」", h1["title"] == "資金輪盤" and "與價格同步，不是提前訊號" in h1["note"], h1)
    ok(f"[{T}] ① ★ 切到資金輪盤：四段名換成 集中／升溫／退燒／冷落（不再出現領先／改善）", all(w in quad1 for w in ("集中", "升溫", "退燒", "冷落")) and "領先" not in quad1 and "改善" not in quad1, quad1[:120])
    ok(f"[{T}] ① ★ 切到資金輪盤：輪盤上點的座標真的不一樣（不是只換標題）", bool(sig0) and bool(sig1) and sig0 != sig1)
    nums = pg.evaluate("() => [...document.querySelectorAll('#rotClock .rotquads .rq')].map(e => (e.textContent.match(/\\d+/) || [0])[0] * 1)")
    ok(f"[{T}] ① 資金輪盤四段家數加總 > 0（有族群上盤）", len(nums) == 4 and sum(nums) > 0, nums)
    # 點「集中」那一段 → 在原地展開該段族群
    pg.click("#rotClock .rotquads .rq[data-k=leading]"); pg.wait_for_timeout(800)
    n_open = pg.evaluate("() => document.querySelectorAll('#stagePanel li[data-gid]').length")
    cols = pg.evaluate("() => [...document.querySelectorAll('#stagePanel li.cols span')].map(s => s.title + s.textContent).join('|')")
    ok(f"[{T}] ① 點「集中」展開該段族群清單（{n_open} 列），欄名換成「占比水準」", n_open > 0 and "占比水準" in cols, [n_open, cols])
    # 回放：▶ 按下去，時間往前走、輪盤跟著變
    pg.evaluate("() => document.querySelector('#rotBack').scrollIntoView({block: 'center'})")
    s_a = pg.evaluate(SIG); v_a = text(pg, "#rotBack .val")
    pg.click("#rotBack .pb.play"); pg.wait_for_timeout(1600)
    v_b = text(pg, "#rotBack .val"); s_b = pg.evaluate(SIG)
    ok(f"[{T}] ① ★ 資金輪盤按 ▶ 回放：讀數改變（{v_a} → {v_b}）、鈕變 ⏸、輪盤座標跟著變", v_a != v_b and text(pg, "#rotBack .pb.play") == "⏸" and s_a != s_b)
    pg.click("#rotBack .pb.play"); pg.wait_for_timeout(300)
    # 拖「N 天前」拉桿 → 軌跡變、座標變
    pg.evaluate("() => { const i = document.querySelector('#rotBack input[type=range]'); i.value = 5; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    s_c = pg.evaluate(SIG)
    ok(f"[{T}] ① 資金輪盤拉「N 天前」拉桿：輪盤變了", s_c != s_b)
    # 切回強弱輪動 → 還原
    pg.click("#rotModeSeg button[data-rm=price]"); pg.wait_for_timeout(1500)
    h2 = pg.evaluate(HEAD); quad2 = text(pg, "#rotClockWrap")
    ok(f"[{T}] ① ★ 切回強弱輪動：標題、提示、四段名全部還原（領先／改善回來、集中／升溫消失）",
       h2["title"] == "強弱輪動" and not h2["note"] and "領先" in quad2 and "集中" not in quad2, [h2, quad2[:80]])
    # 「?」說明：資金輪盤那份也要寫到「所以我該怎麼用」
    pg.click("#rotModeSeg button[data-rm=money]"); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#flowRotCard .howbtn, .rothead .howbtn').click()"); pg.wait_for_timeout(600)
    how = pg.evaluate("() => (document.querySelector('#howPop') || {innerText: ''}).innerText")
    ok(f"[{T}] ① 資金輪盤的「?」說明：講清楚成交值占比、寫「不是提前訊號」、有「用法」", "成交值占比" in how and "不是提前訊號" in how and "用法" in how and len(how) <= 700, len(how))
    ctx.close()

    # ------------------------------------------------------------------ ② 手機 390：切換鈕在、不橫向溢出、切過去輪盤變
    ctx, pg = open_page("#flow/rotation", vp={"width": 390, "height": 844}, mobile=True)
    wait_until(pg, "() => !!document.querySelector('#rotClock canvas') && document.querySelectorAll('#rotModeSeg button').length === 2", 30000)
    sg0 = pg.evaluate(SIG)
    pg.tap("#rotModeSeg button[data-rm=money]"); pg.wait_for_timeout(1800)
    sg1 = pg.evaluate(SIG)
    m = pg.evaluate("() => { const r = document.getElementById('rotModeSeg').getBoundingClientRect(); return { l: r.left, r: r.right, w: innerWidth, sw: document.documentElement.scrollWidth, fs: Math.min(...[...document.querySelectorAll('#rotModeSeg button')].map(b => parseFloat(getComputedStyle(b).fontSize))) }; }")
    ok(f"[{T}] ② [390] 手機點「資金輪盤」：輪盤變了、提示出現、切換鈕沒超出畫面、字 ≥ 11px、頁面沒有橫向捲軸",
       sg0 != sg1 and "與價格同步" in text(pg, "#rotModeNote") and m["l"] >= 0 and m["r"] <= m["w"] + 1 and m["fs"] >= 11 and m["sw"] <= m["w"] + 1, m)
    ctx.close()

    # ------------------------------------------------------------------ ③ 盤中即時＋今日時間軸（資金輪盤）
    ctx, pg = open_page("#flow/rotation", live=True)
    wait_until(pg, "() => !!document.querySelector('#rotClock canvas') && !!document.getElementById('rotLiveBtn') && document.querySelectorAll('#rotModeSeg button').length === 2", 30000)
    pg.click("#rotModeSeg button[data-rm=money]"); pg.wait_for_timeout(1200)
    base_sig = pg.evaluate(SIG)
    pg.click("#rotLiveBtn")
    wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0 && Object.keys(s.pts).length > 0; }", 60000, 400)
    pg.wait_for_timeout(1200)
    pts = pg.evaluate("() => App.rlvState().pts")
    first = next(iter(pts.values())) if pts else {}
    ok(f"[{T}] ③ ★ 資金輪盤開即時：有 {len(pts)} 個族群的即時座標、帶「估算占比 sh」（不是強弱輪動的報酬續算）、輪盤跟盤後不一樣",
       len(pts) > 3 and first.get("mode") == "money" and pg.evaluate(SIG) != base_sig, first)
    ok(f"[{T}] ③ 資金輪盤即時：占比總和校準成昨天同批族群的占比（0 < 總和 < 100）", 0 < sum((v.get("sh") or 0) for v in pts.values()) < 100, sum((v.get("sh") or 0) for v in pts.values()))
    wait_until(pg, "() => !!document.getElementById('rotTl')", 15000)
    live_sig = pg.evaluate("() => JSON.stringify(App.rlvState().pts)")
    pg.evaluate("() => { const i = document.querySelector('#rotTl input.tlr'); i.value = 4; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    t1 = pg.evaluate("() => JSON.stringify(App.rlvState().pts)")
    ok(f"[{T}] ③ ★ 資金輪盤＋今日時間軸：拖到 09:20，座標跟最新不同（同一個占比公式回放）", t1 != live_sig)
    pg.click("#rotTl .pb.play"); pg.wait_for_timeout(2200)
    t2 = pg.evaluate("() => JSON.stringify(App.rlvState().pts)")
    ok(f"[{T}] ③ ★ 資金輪盤＋今日時間軸按 ▶：播放中座標隨之改變", t2 != t1 and text(pg, "#rotTl .pb.play") == "⏸")
    pg.click("#rotTl .pb.play"); pg.wait_for_timeout(300)
    # 即時開著時切回強弱輪動：座標改回價格續算（有 ret 欄但沒有 sh）
    pg.click("#rotModeSeg button[data-rm=price]")
    wait_until(pg, "() => { const s = App.rlvState(); const v = Object.values(s.pts)[0]; return !!v && v.mode === 'price'; }", 30000, 400)
    ok(f"[{T}] ③ 即時開著切回強弱輪動：即時座標改回價格續算（mode 回到 price）、不報錯", pg.evaluate("() => { const v = Object.values(App.rlvState().pts)[0]; return !!v && v.mode === 'price'; }"))
    ctx.close()


register("資金輪盤1030", lambda pg, b, base, code: t_money_wheel_1030(b, base))
