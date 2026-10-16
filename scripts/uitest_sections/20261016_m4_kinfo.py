# 驗收段落「手機K線資訊1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

def _kinfo_fake_m60(pg, code):
    """本機資料湖只有 ETF 的 60 分 K：1時／4時 驗收時把 0050 的 60 分 K 依這檔收盤價等比例放大，掛成這檔的（只在驗收裡，線上不受影響）。"""
    sj = json.loads((SITE / "data" / "stock" / f"{code}.json").read_text(encoding="utf-8"))
    last = (sj.get("daily") or sj.get("ohlcv"))[-1][4]
    src = json.loads((SITE / "data" / "m60" / "0050.json").read_text(encoding="utf-8"))
    k = last / src["days"][-1][1][-1][4]
    src["code"] = code
    src["days"] = [[d, [[x[0]] + [round(v * k, 1) for v in x[1:5]] + [x[5] // 50] for x in bars]] for d, bars in src["days"]]
    body = json.dumps(src)

    def st(route):
        j = json.loads(route.fetch().text()); j.setdefault("meta", {})["m60"] = "ok"
        route.fulfill(body=json.dumps(j), content_type="application/json")
    pg.route(f"**/data/stock/{code}.json*", st)
    pg.route(f"**/data/m60/{code}.json*", lambda r: r.fulfill(body=body, content_type="application/json"))


def t_m4_kinfo_1016(b, base, code):
    """★ 2026-10-16 Andy（iPhone，南電 8046 4時）：「手機版本 個股K線圖那邊資的訊太多，可以看到 K線圖 被遮住一大部分，需要處理」。
    手機（html.m4）把圖頭（日期／開高低收／振幅／量／MA）從主圖上搬到圖上方的兩行資訊列 #m4kInfo（industry.js m4KInfo／paintM4KInfo、mobile4.css 1016k 節）。
    360／390／430 × 淺色／深色 × 分時／1時／4時／日／週／月：
      ① 任何圖頭／資訊元素（#legendOv、#ohlcBox、#m4kInfo、「還原」小標）跟主圖繪圖區（不含價格軸）的交集 = 0px
      ② 資訊列第 1 行有字（收／量）、字級 ≥ 12px、第 2 行有均線晶片；整頁不橫捲
      ③ 手指點一根 K 棒 → 第 1 行換成那一根、第 2 行最前面出現「開／高／低／振幅」；點另一根 → 再換；放開後主圖上沒有任何浮層
      ④ 主圖高度不比改前少（改前 390 寬主圖約 348px；這裡驗 ≥ 改前同寬的 #lwc 主圖：#lwc 高度沒動）"""
    T = "手機K線資訊1016"
    M = """() => { const lw = document.getElementById('lwc'); if (!lw) return null;
      const R = (e) => { if (!e) return null; const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || e.hidden) return null;
                         const r = e.getBoundingClientRect(); return r.width && r.height ? { l: r.left, t: r.top, r: r.right, b: r.bottom, h: r.height } : null; };
      const tbl = [...lw.querySelectorAll('table')].find(t => !t.closest('.ohlcbox,#ohlcBox,.legend-ov'));
      const pane = tbl && [...tbl.rows[0].cells].reduce((a, c) => (!a || c.getBoundingClientRect().width > a.getBoundingClientRect().width ? c : a), null); const st = document.getElementById('m4kInfo');
      const l1 = st && st.querySelector('.m4ki1'), l2 = st && st.querySelector('.m4ki2');
      let txt = null; if (l1 && l1.firstChild) { const rg = document.createRange(); rg.selectNodeContents(l1); const q = rg.getBoundingClientRect(); txt = { l: q.left, t: q.top, r: q.right, b: q.bottom }; }
      return { empty: !!lw.querySelector('.empty'), pane: R(pane), legend: R(document.getElementById('legendOv')), ohlc: R(document.getElementById('ohlcBox')),
        strip: R(st), tag: R(document.getElementById('adjTag')), txt, l1: l1 ? l1.textContent : '', chips: l2 ? [...l2.children].map(c => c.textContent) : [],
        picked: st ? st.dataset.picked : '', fs: l1 ? parseFloat(getComputedStyle(l1).fontSize) : 0, cfs: l2 && l2.firstElementChild ? parseFloat(getComputedStyle(l2.firstElementChild).fontSize) : 0,
        sw: document.documentElement.scrollWidth, vw: innerWidth, lwcH: lw.getBoundingClientRect().height, tf: (document.querySelector('#tfSeg button.on') || {}).dataset?.tf || '' }; }"""

    def inter(a, p):
        if not a or not p:
            return 0
        w = min(a["r"], p["r"]) - max(a["l"], p["l"]); h = min(a["b"], p["b"]) - max(a["t"], p["t"])
        return max(0, w) * max(0, h)
    for W in (360, 390, 430):
        for theme in ("light", "dark"):
            tag = f"【{T}】{W} {theme}"
            ctx = b.new_context(viewport={"width": W, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            try:
                ctx.add_init_script(f"try{{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.theme','{theme}'); }}catch(e){{}}")
                m = ctx.new_page()
                m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
                m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
                _kinfo_fake_m60(m, "8046")
                m.goto(base + "#stock/8046", wait_until="domcontentloaded")
                if not ok(f"{tag}：個股頁 K 線圖畫出來", wait_until(m, "!!document.querySelector('#lwc canvas') && !!document.querySelector('#tfSeg button')", 25000)):
                    continue
                ok(f"{tag}：手機是 html.m4", m.evaluate("document.documentElement.classList.contains('m4')"))
                seen = []
                for tf, nm in (("tick", "分時"), ("60m", "1時"), ("240m", "4時"), ("1d", "日"), ("1w", "週"), ("1M", "月")):
                    btn = m.locator(f"#tfSeg button[data-tf='{tf}']")
                    if not btn.count():
                        ok(f"{tag} {nm}：週期列有這顆鈕", False); continue
                    btn.first.scroll_into_view_if_needed(); btn.first.tap(); m.wait_for_timeout(1200)
                    m.evaluate("() => { const w = document.getElementById('chartWrap'); window.scrollTo(0, w.getBoundingClientRect().top + scrollY - 150); }"); m.wait_for_timeout(400)
                    s = m.evaluate(M)
                    if s is None or s["empty"] or not s["pane"]:
                        ok(f"{tag} {nm}：沒資料 → 資訊列收起、不留舊數字", s is None or not s["strip"], s); continue
                    seen.append(nm)
                    over = {k: inter(s[k], s["pane"]) for k in ("legend", "ohlc", "strip", "tag")}
                    ok(f"{tag} {nm}①：圖頭／提示框／資訊列／還原小標跟主圖繪圖區交集都是 0（{over}）", all(v == 0 for v in over.values()), s)
                    ok(f"{tag} {nm}②：資訊列第 1 行「{s['l1']}」有字、字級 {s['fs']}／{s['cfs']} ≥ 12、在圖上方、還原小標不壓字、整頁不橫捲",
                       bool(s["strip"]) and s["l1"].strip() != "" and ("收" in s["l1"] or "價" in s["l1"]) and "量" in s["l1"] and s["fs"] >= 12 and (s["cfs"] >= 12 or not s["chips"])
                       and s["strip"]["b"] <= s["pane"]["t"] and inter(s["tag"], s["txt"]) == 0 and s["sw"] <= s["vw"], s)
                    if tf != "tick":
                        ok(f"{tag} {nm}②：第 2 行均線晶片 {s['chips'][:4]}", any(c.startswith("MA") for c in s["chips"]), s["chips"])
                    p = s["pane"]; y = p["t"] + p["h"] * 0.55
                    m.touchscreen.tap(p["l"] + (p["r"] - p["l"]) * 0.30, y); m.wait_for_timeout(350)
                    a = m.evaluate(M)
                    m.touchscreen.tap(p["l"] + (p["r"] - p["l"]) * 0.75, y); m.wait_for_timeout(350)
                    c = m.evaluate(M)
                    if tf == "tick":
                        ok(f"{tag} {nm}③：點分時線兩處 → 第 1 行跟著換（{a['l1']} → {c['l1']}）", a["l1"] != c["l1"] and a["picked"] == "1", [a["l1"], c["l1"]])
                    else:
                        ok(f"{tag} {nm}③：點兩根不同的 K 棒 → 第 1 行換（{a['l1']} → {c['l1']}）、第 2 行最前面是開／高／低／振幅",
                           a["l1"] != c["l1"] and c["picked"] == "1" and len(c["chips"]) >= 4 and c["chips"][0].startswith("開") and c["chips"][3].startswith("振幅"), [a["l1"], c["l1"], c["chips"][:4]])
                    over2 = {k: inter(c[k], c["pane"]) for k in ("legend", "ohlc", "strip", "tag")}
                    ok(f"{tag} {nm}③：手指放開後主圖上沒有任何浮層（{over2}）", all(v == 0 for v in over2.values()), over2)
                ok(f"{tag}：六個週期裡至少 5 個有圖可驗（{seen}）", len(seen) >= 5, seen)
                # 第 2 行可以用手指左右滑（晶片多於一行寬時）：真的捲得動
                sc = m.evaluate("() => { const l2 = document.querySelector('#m4kInfo .m4ki2'); if (!l2) return null; const r = l2.getBoundingClientRect(); return { x: r.left + r.width * 0.8, y: r.top + r.height / 2, over: l2.scrollWidth - l2.clientWidth, more: l2.classList.contains('more') }; }")
                if sc and sc["over"] > 4:
                    cdp = ctx.new_cdp_session(m)
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": sc["x"], "y": sc["y"]}]})
                    for k in range(1, 9):
                        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": sc["x"] - 20 * k, "y": sc["y"]}]}); m.wait_for_timeout(16)
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); m.wait_for_timeout(500)
                    sl = m.evaluate("document.querySelector('#m4kInfo .m4ki2').scrollLeft")
                    ok(f"{tag}：第 2 行晶片多出 {sc['over']:.0f}px → 右緣淡出提示（{sc['more']}）、手指往左拖真的捲動（scrollLeft {sl}）", sc["more"] and sl > 8, sc)
            finally:
                ctx.close()


# ★ 2026-10-16 Andy（iPhone 南電 8046 4時）：「個股K線圖那邊資的訊太多，可以看到 K線圖 被遮住一大部分」—— 360／390／430 × 淺／深 × 六個週期：圖頭搬到圖上方資訊列、跟主圖繪圖區交集 0、點 K 棒資訊列換；1440 不變
register("手機K線資訊1016", lambda pg, b, base, code: t_m4_kinfo_1016(b, base, code), after="手機法人散布1016")
