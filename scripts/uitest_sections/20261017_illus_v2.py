# 驗收段落「精選文章插圖v2」—— 2026-10-17 新增（拆檔防合併衝突：新段落一律放 scripts/uitest_sections/）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章插圖v2（site/artillus.js 的 "style": 2；規格 docs/articles/illus_style.md）
# Andy 10-17：「自動產精選文章，之後的圖需要再更細緻，顏色不要太單一……這次先不改（指已上架的 HBM 那張），我等你們串接好後，我去點選生產文章」
#   ① 舊圖不變：沒帶 style 的 cowos／rack／custom，SVG 標記跟改版前逐字相同（雜湊比對；改版前後在本機逐像素比過，見 HANDOFF）、
#      沒有 ilv2；同一張帶 "style": 1 畫出來跟沒帶一模一樣
#   ② 第 2 版真的換了畫法：每個方塊有頂面高光帶、正面漸層、側面加暗漸層、稜線高光、倒角亮線；球有高光點與接觸陰影；
#      分層、凸塊陣列、走線、刻字、填充膠斜邊、銅墊、通孔、導引虛線都畫得出來；tone 換得出不同色；沒有任何濾鏡、模糊、動畫
#   ③ 規格 4.2 節機器量測（scripts/illus_audit.py 的 measure／judge）：深淺 × 1440／390 全部門檻過
#      （色相 ≥ 4 組、最大一組 ≤ 35%、前兩組 ≤ 60%、冷暖各 ≥ 10%、灰 ≤ 35%、mat 數、同 mat、相鄰色差、不可相鄰、最大彩度 ≤ 0.15、
#        構圖填滿、390 球半徑 ≥ 2.5px、390 每層 ≥ 2px、無空白方塊、引線／說明／編號 0 重疊、0 濾鏡）
#   ④ 真的操作：深色 → 切淺色（不重畫，只改 data-theme）零件頂面顏色真的換一組；滑過／點說明 → 該零件不變、其他變淡、再離開恢復
#   ⑤ 內建 kind 帶 "style": 2（cowos、rack）也換新色票與光影、拿掉模糊影子；舊的照舊
#   ⑥ 安全：mat／detail／bmat／type／tone 塞 HTML 或怪值 → 被白名單擋掉、不執行、不出現在 SVG
#   截圖：TW_ILLUS_V2_SHOTS=<資料夾> 才存。

# 舊圖（沒帶 style）SVG 標記的雜湊：2026-10-17 在改版前的 main（9645bac5）量到的值，改版後逐字相同 —— 這三個數字變了就代表舊圖被動到了
_IL1_HASH = {"cowos": "3680361071461a67", "rack": "6c0e6888d4772b85", "custom": "7ccafcf711961ac8"}
_IL1_CUSTOM = {"t": "illus", "kind": "custom", "title": "氣冷散熱模組（舊版測試）", "note": "示意", "view": [560, 330], "depth": [44, -26],
               "shapes": [{"part": "board", "type": "box", "x": 20, "y": 270, "w": 420, "h": 26, "mat": "pcb", "detail": "lines", "n": 2},
                          {"part": "chip", "type": "box", "x": 170, "y": 252, "w": 110, "h": 18, "mat": "chip", "detail": "grid"},
                          {"part": "base", "type": "box", "x": 150, "y": 234, "w": 150, "h": 18, "mat": "cu"},
                          {"part": "pipe", "type": "pipe", "mat": "cu", "r": 5, "points": [[180, 238], [180, 120], [200, 100]]},
                          {"part": "fins", "type": "box", "x": 140, "y": 90, "w": 180, "h": 120, "mat": "steel", "detail": "fins", "n": 18},
                          {"part": "fan", "type": "box", "x": 330, "y": 96, "w": 100, "h": 110, "mat": "plastic", "detail": "fan", "d": 0.5},
                          {"part": "cell", "type": "cyl", "x": 470, "y": 180, "w": 50, "h": 100, "mat": "battery", "detail": "terminals"},
                          {"part": "die", "type": "box", "x": 30, "y": 200, "w": 90, "h": 40, "mat": "mem", "detail": "layers", "n": 6},
                          {"part": "bump", "type": "balls", "x": 40, "x2": 110, "y": 246, "n": 6, "r": 3, "mat": "solder"}],
               "parts": [{"id": "fan", "label": "風扇", "sub": "扇框＋扇葉＋輪轂"}, {"id": "fins", "label": "散熱鰭片", "sub": "加大散熱面積"},
                         {"id": "pipe", "label": "熱管", "sub": "把熱帶到鰭片"}, {"id": "base", "label": "銅底座", "sub": "貼在晶片上"},
                         {"id": "chip", "label": "晶片", "sub": "熱的來源"}, {"id": "board", "label": "主機板", "sub": "承載晶片"},
                         {"id": "cell", "label": "電池", "sub": "有極柱"}, {"id": "die", "label": "疊層晶粒", "sub": "分層"}, {"id": "bump", "label": "凸塊", "sub": "一排球"}]}


def _il2_fixture():
    """第 2 版測試圖：一顆「疊層記憶體＋運算晶片」封裝，上方拆開看（構圖照 HBM 試作，文字是測試用、不是文章內容）。"""
    R = 5.6
    S = [{"part": "sub", "type": "balls", "x": 40, "x2": 340, "y": 453, "n": 10, "r": R, "mat": "solder", "d": 1.3},
         {"part": "sub", "type": "box", "x": 20, "y": 420, "w": 340, "h": 26, "mat": "abf", "detail": ["lines", "hatch"], "n": 3, "d": 1.3},
         {"part": "ip", "type": "balls", "x": 52, "x2": 328, "y": 413, "n": 12, "r": R, "mat": "solder", "d": 1.15},
         {"part": "ip", "type": "box", "x": 40, "y": 390, "w": 300, "h": 16, "mat": "si", "detail": ["vias", "traces"], "n": 14, "d": 1.15},
         {"part": "stack", "type": "balls", "x": 64, "x2": 136, "y": 385, "n": 5, "r": R, "mat": "cu", "d": 0.9},
         {"part": "proc", "type": "balls", "x": 180, "x2": 308, "y": 385, "n": 8, "r": R, "mat": "cu", "d": 1.0},
         {"part": "stack", "type": "box", "x": 54, "y": 368, "w": 92, "h": 12, "mat": "logic", "detail": ["pads"], "d": 0.9},
         {"part": "stack", "type": "box", "x": 54, "y": 318, "w": 92, "h": 50, "mat": "mem", "tone": -1, "detail": ["layers", "label", "seal"], "n": 8, "d": 0.9},
         {"part": "proc", "type": "box", "x": 170, "y": 326, "w": 148, "h": 54, "mat": "chip", "detail": ["grid", "label", "seal"], "d": 1.0},
         {"type": "guide", "points": [[46, 316], [46, 268]]},
         {"part": "ctl", "type": "box", "x": 40, "y": 246, "w": 124, "h": 16, "mat": "logic", "tone": 2, "detail": ["bumps", "pads"], "nu": 8, "nv": 3, "bmat": "cu", "d": 1.0}]
    for k, y in enumerate([206, 166, 126, 86]):
        S.append({"part": "mb", "type": "balls", "x": 50, "x2": 154, "y": y + 26, "n": 7, "r": R, "mat": "solder", "d": 1.0})
        S.append({"part": "die", "type": "box", "x": 40, "y": y, "w": 124, "h": 12, "mat": "mem", "tone": 1, "detail": ["vias", "label"] if k == 3 else ["vias", "pads"], "n": 6, "d": 0.85})
    for x in (62, 101, 140):
        S.append({"part": "via", "type": "pipe", "mat": "cu", "r": 2.6, "points": [[x, 270], [x, 88]]})
    P = [{"id": "mb", "label": "層間凸塊", "sub": "測試：層與層之間", "anchor": [166, 101]}, {"id": "die", "label": "晶粒（拆開）", "sub": "測試", "anchor": [178, 164]},
         {"id": "ctl", "label": "底層控制晶粒", "sub": "測試", "anchor": [184, 244]}, {"id": "via", "label": "垂直導通", "sub": "測試", "anchor": [140, 266]},
         {"id": "stack", "label": "疊層記憶體", "sub": "測試", "anchor": [150, 306], "out": 284}, {"id": "proc", "label": "運算晶片", "sub": "測試", "anchor": [338, 345]},
         {"id": "ip", "label": "中介層", "sub": "測試", "anchor": [380, 371]}, {"id": "sub", "label": "載板", "sub": "測試", "anchor": [392, 424]}]
    return {"t": "illus", "kind": "custom", "style": 2, "title": "第 2 版測試圖", "note": "示意", "view": [600, 480], "depth": [40, -24], "shapes": S, "parts": P}


def t_illus_v2_1017(b, base):
    T = "精選文章插圖v2"
    import hashlib, importlib.util
    spec = importlib.util.spec_from_file_location("illus_audit", str(ROOT / "scripts" / "illus_audit.py"))
    AU = importlib.util.module_from_spec(spec); spec.loader.exec_module(AU)
    shots = os.environ.get("TW_ILLUS_V2_SHOTS")
    fx = _il2_fixture()
    evil = json.loads(json.dumps(fx))
    evil["shapes"][1] = dict(evil["shapes"][1], mat="\"><img src=x onerror=window.__ilXss=1>", detail=["<script>window.__ilXss=1</script>", "hatch", "toString"], bmat="<b>", tone="NaN")
    evil["shapes"].append({"part": "proc", "type": "<script>", "x": 0, "y": 0})
    evil["shapes"].append({"part": "proc", "type": "box", "x": 5, "y": 5, "w": 4, "h": 4, "tone": 99, "mat": "toString", "detail": "constructor"})
    arts = {
        "uitest-il1-legacy": {"blocks": [{"t": "illus", "kind": "cowos"}, {"t": "illus", "kind": "rack"}, _IL1_CUSTOM]},
        "uitest-il1-style1": {"blocks": [{"t": "illus", "kind": "cowos", "style": 1}, {"t": "illus", "kind": "rack", "style": "1"}, dict(_IL1_CUSTOM, style=1)]},
        "uitest-il2": {"blocks": [fx]},
        "uitest-il2-builtin": {"blocks": [{"t": "illus", "kind": "cowos", "style": 2, "title": "CoWoS（第 2 版）"}, {"t": "illus", "kind": "rack", "style": 2, "title": "機櫃（第 2 版）"}]},
        "uitest-il2-evil": {"blocks": [evil]},
    }

    def post(aid):
        return json.dumps(dict({"id": aid, "cat": "know", "title": "插圖第 2 版測試", "date": "2026-10-17", "tags": [], "summary": "", "reading_min": 1, "groups": []}, **arts[aid]), ensure_ascii=False)

    def ctx_for(theme, w):
        mob = w < 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme'," + json.dumps(theme) + ")}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        for aid in arts:
            c.route(f"**/articles/posts/{aid}.json", (lambda body: (lambda r: r.fulfill(status=200, content_type="application/json", body=body)))(post(aid)))
        return c

    def open_art(pg, aid, n):
        pg.goto(base + "#article/" + aid, wait_until="domcontentloaded")
        okk = wait_until(pg, f"() => document.querySelectorAll('#artBody .artillus').length >= {n} && [...document.querySelectorAll('#artBody .artillus')].every(f => +f.dataset.lines > 0)", 20000)
        pg.wait_for_timeout(500)
        return okk

    SVGS = "() => [...document.querySelectorAll('#artBody .artillus svg.ilsvg')].map(s => ({ cls: s.getAttribute('class'), vb: s.getAttribute('viewBox'), html: s.innerHTML.replace(/il[0-9]+_/g, 'il_'), filt: s.querySelectorAll('filter, feGaussianBlur').length }))"
    h = lambda x: hashlib.sha256((x["vb"] + "|" + x["html"]).encode("utf-8")).hexdigest()[:16]

    # ---------------------------------------------------------------- ① 舊圖不變
    c = ctx_for("dark", 1440); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    ok(f"{T}：舊圖測試頁畫出 3 張（cowos、rack、custom）", open_art(pg, "uitest-il1-legacy", 3))
    L = pg.evaluate(SVGS)
    got = {k: h(x) for k, x in zip(("cowos", "rack", "custom"), L)}
    if os.environ.get("TW_ILLUS_V2_PRINT_HASH"):
        print("[精選文章插圖v2] 舊圖雜湊：", got)
    ok(f"{T}：舊圖（沒帶 style）SVG 標記跟改版前逐字相同（雜湊 {got}）、沒有 ilv2", got == _IL1_HASH and all(x["cls"] == "ilsvg" for x in L), [got, _IL1_HASH, [x["cls"] for x in L]])
    ok(f"{T}：舊圖照舊保留原本的模糊影子（證明舊路徑沒被改成新畫法）", L[0]["filt"] >= 1 and L[1]["filt"] >= 1, [x["filt"] for x in L])
    open_art(pg, "uitest-il1-style1", 3)
    L1 = pg.evaluate(SVGS)
    ok(f"{T}：同一張帶 \"style\": 1（或字串 \"1\"）畫出來跟沒帶一模一樣", [h(x) for x in L1] == [h(x) for x in L], [h(x) for x in L1])
    c.close()

    # ---------------------------------------------------------------- ②③④ 第 2 版：深淺 × 1440／390
    res = {}
    top_fill = {}
    for theme in ("dark", "light"):
        r = {}
        for w in (1440, 390):
            mob = w < 640
            tag = f"{theme}/{w}"
            c = ctx_for(theme, w); pg = c.new_page()
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            if not open_art(pg, "uitest-il2", 1):
                ok(f"{T}[{tag}]：第 2 版測試圖畫出來", False); c.close(); continue
            F = pg.evaluate("""() => { const s = document.querySelector('#artBody svg.ilsvg'); const q = (x) => s.querySelectorAll(x).length;
                const boxes = q('g.qk:has(> rect.qf)');
                return { cls: s.getAttribute('class'), boxes, band: q('g.qk > polygon.qb'), side: [...s.querySelectorAll('g.qk > polygon.qr')].filter(p => /url\\(/.test(p.style.fill)).length,
                  front: [...s.querySelectorAll('g.qk > rect.qf')].filter(p => /url\\(/.test(p.style.fill)).length, hl: q('g.qk > path.qhl'), bv: q('g.qk > path.qbv'),
                  balls: q('circle.qball'), ballHi: q('circle.qbh'), ballSh: q('ellipse.qbs'), layers: q('rect.ql1, rect.ql2'), glue: q('path.qglue'), bumps: q('ellipse.qbump'),
                  traces: q('path.qtr'), marks: q('line.qmark'), pin: q('circle.qpin'), seal: q('polygon.qfill'), hatch: q('path.qhatch'), guide: q('g.qguide'),
                  grid: q('line.qgrid'), sealring: q('polygon.qseal'), lines: q('line.qln'), ends: q('rect.qend'),
                  filt: q('filter, feGaussianBlur, feDropShadow, animate, animateTransform'), stops: q('stop'),
                  t1: getComputedStyle(s.querySelector('[data-part="stack"] g.qk.k-mem_m1 > polygon.qt')).fill,
                  t2: getComputedStyle(s.querySelector('[data-part="die"] g.qk.k-mem_p1 > polygon.qt')).fill,
                  topProc: getComputedStyle(s.querySelector('[data-part="proc"] g.qk > polygon.qt')).fill }; }""")
            if not mob:
                ok(f"{T}[{tag}]：svg 掛 ilv2；{F['boxes']} 個方塊每個都有頂面高光帶（{F['band']}）、正面漸層（{F['front']}）、側面加暗漸層（{F['side']}）、稜線高光（{F['hl']}）、倒角亮線（{F['bv']}）",
                   "ilv2" in F["cls"] and F["boxes"] >= 9 and F["band"] >= F["boxes"] and F["front"] >= F["boxes"] and F["side"] >= F["boxes"] and F["hl"] >= F["boxes"] and F["bv"] >= F["boxes"], F)
                ok(f"{T}[{tag}]：球 {F['balls']} 顆每顆都有高光點與接觸陰影；分層 {F['layers']}＋黏著線 {F['glue']}、凸塊陣列 {F['bumps']}、走線 {F['traces']}、刻字 {F['marks']}＋pin-1、"
                   f"填充膠斜邊 {F['seal']}、剖面斜線、晶片格線＋密封環、內層線路 {F['lines']}、管線接頭 {F['ends']}、拆開導引虛線",
                   F["balls"] > 50 and F["ballHi"] >= F["balls"] + F["bumps"] and F["ballSh"] == F["balls"] and F["layers"] >= 8 and F["glue"] >= 7 and F["bumps"] >= 18 and F["traces"] >= 6
                   and F["marks"] >= 6 and F["pin"] >= 2 and F["seal"] >= 4 and F["hatch"] >= 1 and F["grid"] >= 5 and F["sealring"] >= 1 and F["lines"] >= 3 and F["ends"] >= 6 and F["guide"] == 1, F)
                ok(f"{T}[{tag}]：同一種材料不同 tone 真的是兩個色（組好的 {F['t1']} ≠ 拆開的 {F['t2']}）；沒有任何濾鏡、模糊、動畫（{F['filt']}）",
                   F["t1"] != F["t2"] and F["filt"] == 0, F)
                top_fill[theme] = F["topProc"]
            m = AU.measure(pg, fx, 0, theme, w, Path(shots) if shots else None, f"il2-{theme}{w}")
            r["wide" if not mob else "narrow"] = m
            if not mob:
                r["struct"] = AU.structure(pg, fx, theme)
                # ④ 真的操作：滑過說明 → 該零件不變、其他零件變淡；離開恢復
                pid = "proc"
                ST = """(pid) => { const F = document.querySelector('#artBody .artillus'); const op = (e) => +getComputedStyle(e).opacity;
                    const gs = [...F.querySelectorAll('svg.ilsvg [data-part]')]; return { me: Math.min(...gs.filter(g => g.dataset.part === pid).map(op)), ot: Math.max(...gs.filter(g => g.dataset.part !== pid).map(op)) }; }"""
                pg.locator(f"#artBody .artillus .ill li[data-part='{pid}']").hover(); pg.wait_for_timeout(350)
                s1 = pg.evaluate(ST, pid)
                pg.mouse.move(2, 2); pg.wait_for_timeout(350)
                s2 = pg.evaluate(ST, pid)
                ok(f"{T}[{tag}]：滑過「運算晶片」說明 → 它不透明、其他零件變淡（{s1['ot']}）；滑開 → 恢復", s1["me"] == 1 and s1["ot"] <= 0.5 and s2["ot"] == 1, [s1, s2])
                if theme == "dark":
                    pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')"); pg.wait_for_timeout(300)
                    after = pg.evaluate("() => getComputedStyle(document.querySelector('#artBody svg.ilsvg [data-part=\"proc\"] g.qk > polygon.qt')).fill")
                    ok(f"{T}[{tag}]：不重畫、只把主題切到淺色 → 運算晶片頂面顏色真的換一組（{F['topProc']} → {after}）", after != F["topProc"], [F["topProc"], after])
                if shots:
                    Path(shots).mkdir(parents=True, exist_ok=True)
                    pg.evaluate("() => document.documentElement.setAttribute('data-theme', " + json.dumps(theme) + ")"); pg.wait_for_timeout(200)
                    pg.locator("#artBody .artillus").first.screenshot(path=str(Path(shots) / f"il2-{theme}-{w}.png"))
            elif shots:
                Path(shots).mkdir(parents=True, exist_ok=True)
                pg.locator("#artBody .artillus").first.screenshot(path=str(Path(shots) / f"il2-{theme}-{w}.png"))
            ok(f"{T}[{tag}]：沒有頁面錯誤、沒有橫向捲軸", not errs and not m.get("hscroll"), [errs, m.get("hscroll")])
            c.close()
        res[theme] = r
    if all(len(v) == 3 for v in res.values()):
        fails = AU.judge(fx, res)
        S = AU.summary(res)
        for th in ("dark", "light"):
            s = S[th]
            ok(f"{T}[{th}]：規格 4.2 量測 —— 色相 ≥5% 的組 {s['hue_groups_ge5']}（≥4）、最大一組 {s['hue_top1']:.0%}（≤35%）、前兩組 {s['hue_top2_sum']:.0%}（≤60%）、"
               f"暖 {s['warm_pct']:.0%}／冷 {s['cool_pct']:.0%}（各 ≥10%）、灰 {s['neutral_pct']:.0%}（≤35%）",
               not [f for f in fails if f.startswith(th + ":") and f.split(":")[1] in ("hue_groups_ge5", "hue_top1", "hue_top2_sum", "warm_pct", "cool_pct", "neutral_pct")], s)
            ok(f"{T}[{th}]：mat {s['mat_count']} 種／零件 {s['parts_count']}、同 mat 當不同零件 {s['same_mat_parts']}、相鄰最小 ΔE00 {s['adjacent_min_de00']}（≥15）、同疊 {s['same_stack_min_de00']}（≥8）、"
               f"不可相鄰 {s['forbidden_pairs']}、最大彩度 {s['max_chroma']}（≤0.15）、空白方塊 {s['empty_boxes']}",
               not [f for f in fails if f.startswith(th + ":") and f.split(":")[1] in ("mat_count", "same_mat_parts", "adjacent_min_de00", "same_stack_min_de00", "forbidden_pairs", "max_chroma", "empty_boxes", "dark_fill_L")], s)
            ok(f"{T}[{th}]：構圖 寬 {s['bbox_fill_w']:.0%}／高 {s['bbox_fill_h']:.0%}（≥85%／70%）、390 球半徑最小 {s['min_ball_px_390']}px（≥2.5）、390 每層最小 {s['min_layer_px_390']}px（≥2）、"
               f"引線／說明／編號重疊 {s['overlap']}、濾鏡 {s['filters']}",
               not [f for f in fails if f.startswith(th + ":") and f.split(":")[1] in ("bbox_fill_w", "bbox_fill_h", "min_ball_px_390", "min_layer_px_390", "overlap", "filters")], s)
        if shots:
            Path(shots, "illus_audit.json").write_text(json.dumps({"pass": not fails, "fails": fails, "thresholds": AU.TH, "per_theme": S}, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        ok(f"{T}：深淺 × 1440／390 都量到", False, {k: list(v) for k, v in res.items()})

    # ---------------------------------------------------------------- ⑤ 內建 kind 的第 2 版
    for theme in ("dark", "light"):
        c = ctx_for(theme, 1440); pg = c.new_page()
        ok(f"{T}[{theme}]：cowos／rack 帶 style 2 畫得出來（各自 8／7 條引線）", open_art(pg, "uitest-il2-builtin", 2))
        B = pg.evaluate(SVGS)
        ok(f"{T}[{theme}]：cowos／rack 第 2 版掛 ilv2、拿掉模糊影子（0 濾鏡）、方塊換成新畫法（有頂面高光帶與正面漸層）",
           len(B) == 2 and all("ilv2" in x["cls"] and x["filt"] == 0 and 'class="qb"' in x["html"] and "f-chip_p0" in x["html"] + B[1]["html"] for x in B) and "f-tray_p0" in B[1]["html"], [(x["cls"], x["filt"]) for x in B])
        if shots:
            for i, k in enumerate(("cowos", "rack")):
                pg.locator("#artBody .artillus").nth(i).screenshot(path=str(Path(shots) / f"builtin2-{k}-{theme}.png"))
        c.close()

    # ---------------------------------------------------------------- ⑥ 安全
    c = ctx_for("dark", 1440); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    open_art(pg, "uitest-il2-evil", 1)
    X = pg.evaluate("""() => { const s = document.querySelector('#artBody svg.ilsvg'); const css = (document.getElementById('artIlCss2') || {}).textContent || '';
        return { xss: !!window.__ilXss, imgs: document.querySelectorAll('#artBody img').length, html: s ? s.innerHTML : '', css }; }""")
    bad = [k for k in ("<img", "onerror", "<script", "toString", "constructor", "<b>", "NaN") if k in X["html"] or k in X["css"]]
    ok(f"{T}：mat／detail／bmat／type／tone 塞 HTML 或怪值 → 不執行、不出現在 SVG 與樣式裡、壞的積木被擋（命中 {bad}）、沒有頁面錯誤",
       not X["xss"] and X["imgs"] == 0 and not bad and "k-steel_p0" in X["html"] and "k-steel_p2" in X["html"] and not errs, [bad, errs, X["xss"]])
    c.close()


register("精選文章插圖v2", lambda pg, b, base, code: t_illus_v2_1017(b, base), after="精選文章插圖1016")
