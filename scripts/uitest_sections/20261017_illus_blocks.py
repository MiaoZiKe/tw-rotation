# 驗收段落「精選文章插圖積木1017」—— 2026-10-17 晚新增（拆檔防合併衝突：新段落一律放 scripts/uitest_sections/）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章插圖積木1017（site/artillus.js 第 2 版的 wheel／hcyl／shell）
# CEO 退件第二代 Roadster 剖析圖第一版：「車身只是一條細折線、零件浮在車身外、輪子是兩顆球、馬達是直立圓柱」
# → style:2 多三個積木：wheel（側視車輪）、hcyl（橫躺圓柱）、shell（車殼／外殼剖面，可擠出厚度、開窗、開口、兩端收窄）。
#   ① 只在 style:2 生效：同一份積木不帶 style → 三個新積木一個都不畫（舊畫法的白名單沒有它們）、其他積木照畫、沒有頁面錯誤
#   ② 真的畫出識別特徵：車輪＝輪胎（深色厚環）＋胎紋＋5 輻＋輪轂＋5 螺帽＋接地陰影；橫躺圓柱＝筒身由上往下受光漸層＋看得到的端面＋散熱環／色帶／端面螺栓；
#      外殼＝遠側殼＋看得到的擠出面（頂面）＋近側殼（開窗用 evenodd 裁掉）＋開窗切口＋上緣高光
#   ③ 參數真的有作用（畫面因此改變）：open 指定的邊不畫頂面（擠出面數變少）、layer 1／2 只畫後半／前半、taper 讓兩端收窄（遠側輪廓變了）、
#      cut 拿掉 → 近側殼不再裁切
#   ④ 構圖：viewBox 包得住車輪接地陰影與外殼的遠側；引線／說明／編號 0 重疊、0 濾鏡（1440／390 都量）
#   ⑤ 真的操作：切主題 → 輪胎、圓柱端面顏色真的換；滑過「車輪」說明 → 車輪不變、其他零件變淡
#   ⑥ 安全：mat／type／points／cut／open／layer／op 塞 HTML 或怪值 → 白名單擋掉、夾值、不執行、不出現在 SVG

def _ilb_fixture(**over):
    """測試圖：一台通用小車（側視剖面）＋一顆橫躺圓柱。文字是測試用、不是文章內容。"""
    G, R = 300, 30
    body = [[20, G - 14], [12, G - 30], [26, G - 50], [90, G - 62], [140, G - 70], [300, G - 72], [340, G - 64], [352, G - 40], [344, G - 14],
            [318, G - 14], [312, G - 46], [280, G - 64], [248, G - 46], [242, G - 14], [110, G - 14], [104, G - 46], [72, G - 64], [40, G - 46], [34, G - 14]]
    sh = [
        {"part": "shell", "type": "shell", "points": body, "mat": "pcb", "d": 3, "op": 0.4, "layer": 1, "open": over.get("open", [4]), "taper": over.get("taper", 0.5)},
        {"part": "motor", "type": "hcyl", "x": 60, "y": 236, "w": 50, "h": 26, "mat": "magnet", "detail": ["fins", "screws"], "n": 5},
        {"part": "tank", "type": "hcyl", "x": 220, "y": 212, "w": 56, "h": 20, "mat": "cold", "detail": ["layers", "terminals"], "n": 3},
        {"part": "pack", "type": "box", "x": 120, "y": 256, "w": 110, "h": 14, "mat": "battery", "detail": ["grid"], "d": 2},
        {"part": "shell", "type": "shell", "points": body, "mat": "cu", "d": 3, "op": 0.4, "layer": 2, "taper": over.get("taper", 0.5),
         "cut": over.get("cut", [[[40, G - 44], [330, G - 60], [340, G - 22], [40, G - 22]]])},
        {"part": "wheel", "type": "wheel", "x": 72, "y": G - R, "r": R, "mat": "ceramic"},
        {"part": "wheel", "type": "wheel", "x": 280, "y": G - R, "r": R, "mat": "ceramic"},
    ]
    P = [{"id": "tank", "label": "橫躺圓柱（色帶）", "sub": "測試"}, {"id": "motor", "label": "橫躺圓柱（散熱環）", "sub": "測試"},
         {"id": "shell", "label": "外殼", "sub": "測試", "anchor": [352, 250]}, {"id": "pack", "label": "方塊", "sub": "測試"},
         {"id": "wheel", "label": "車輪", "sub": "測試", "anchor": [310, 276]}]
    b = {"t": "illus", "kind": "custom", "style": 2, "title": "第 2 版新積木測試圖", "note": "示意", "view": [400, 320], "depth": [18, -30], "shapes": sh, "parts": P}
    if over.get("nostyle"):
        b.pop("style")
    return b


def t_illus_blocks_1017(b, base):
    T = "精選文章插圖積木1017"
    import importlib.util
    spec = importlib.util.spec_from_file_location("illus_audit", str(ROOT / "scripts" / "illus_audit.py"))
    AU = importlib.util.module_from_spec(spec); spec.loader.exec_module(AU)
    shots = os.environ.get("TW_ILLUS_V2_SHOTS")
    fx = _ilb_fixture()
    evil = _ilb_fixture()
    evil["shapes"][0] = dict(evil["shapes"][0], mat="\"><img src=x onerror=window.__ilbXss=1>", open=["<b>", 99, "constructor", -5], layer="<script>", op="NaN", d=1e9, taper="x",
                             points=evil["shapes"][0]["points"] + [["<i>", 3], [1e12, -1e12]] * 30)
    evil["shapes"][4] = dict(evil["shapes"][4], cut=[[["<svg onload=window.__ilbXss=1>", 1], [2, 2]], "toString", [[1, 1], [2, 2], [3, 3]] * 40] * 5)
    evil["shapes"][5] = dict(evil["shapes"][5], mat="toString", r="1e9", x="<b>")
    evil["shapes"].append({"part": "evil", "type": "wheel\"><script>window.__ilbXss=1</script>", "x": 1, "y": 1, "r": 5})
    arts = {
        "uitest-ilb": {"blocks": [fx]},
        "uitest-ilb-nostyle": {"blocks": [_ilb_fixture(nostyle=True)]},
        "uitest-ilb-noopen": {"blocks": [_ilb_fixture(open=[], taper=0, cut=[])]},
        "uitest-ilb-evil": {"blocks": [evil]},
    }

    def post(aid):
        return json.dumps(dict({"id": aid, "cat": "know", "title": "插圖新積木測試", "date": "2026-10-17", "tags": [], "summary": "", "reading_min": 1, "groups": []}, **arts[aid]), ensure_ascii=False)

    def ctx_for(theme, w):
        mob = w < 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme'," + json.dumps(theme) + ")}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        for aid in arts:
            c.route(f"**/articles/posts/{aid}.json", (lambda body: (lambda r: r.fulfill(status=200, content_type="application/json", body=body)))(post(aid)))
        return c

    def open_art(pg, aid):
        pg.goto(base + "#article/" + aid, wait_until="domcontentloaded")
        okk = wait_until(pg, "() => { const f = document.querySelector('#artBody .artillus'); return f && +f.dataset.lines > 0; }", 20000)
        pg.wait_for_timeout(400)
        return okk

    CNT = """() => { const s = document.querySelector('#artBody svg.ilsvg'); const q = (x) => s.querySelectorAll(x).length;
        const sk = s.querySelector('polygon.qsk'); const cp = sk && sk.getAttribute('clip-path'); const cpid = cp && cp.slice(5, -1);
        const cpath = cpid ? document.getElementById(cpid) : null;
        const far = s.querySelector('polygon.qsb');
        return { cls: s.getAttribute('class'), vb: s.getAttribute('viewBox'), tire: q('circle.qtire'), tread: q('circle.qtread'), spoke: q('polygon.qspoke'), hub: q('circle.qhubw'), nut: q('circle.qnut'),
          ws: q('ellipse.qws'), rim: q('circle.qrimo'), disc: q('circle.qdisc'),
          hbody: [...s.querySelectorAll('[data-part="motor"] path.qf, [data-part="tank"] path.qf')].filter(p => /url\\("?#il[0-9]+_v-/.test(p.style.fill)).length,
          hend: q('[data-part="motor"] ellipse.qt, [data-part="tank"] ellipse.qt'), fins: q('path.qfinr'), bands: q('path.qband'), bolts: q('[data-part="motor"] circle.qscrew'),
          term: q('[data-part="tank"] g.qk g.qk'), sb: q('polygon.qsb'), sf: q('polygon.qsf'), sk: q('polygon.qsk'), skClip: !!cp, cpSub: cpath ? (cpath.querySelector('path').getAttribute('d').match(/M/g) || []).length : 0,
          cpRule: cpath ? cpath.querySelector('path').getAttribute('clip-rule') : '', cut: q('polygon.qcut'), shl: q('path.qshl'), so: q('polygon.qso'),
          far: far ? far.getAttribute('points') : '', parts: [...new Set([...s.querySelectorAll('[data-part]')].map(g => g.dataset.part))].sort(),
          filt: q('filter, feGaussianBlur, feDropShadow, animate, animateTransform'),
          tireFill: getComputedStyle(s.querySelector('circle.qtire') || s).fill, endFill: getComputedStyle(s.querySelector('[data-part="tank"] ellipse.qt') || s).fill }; }"""

    # ---------------------------------------------------------------- ① 只在 style:2 生效
    c = ctx_for("dark", 1440); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    ok(f"{T}：不帶 style 的同一份積木畫得出來（只剩舊積木）", open_art(pg, "uitest-ilb-nostyle"))
    N = pg.evaluate(CNT)
    ok(f"{T}：不帶 style → wheel／hcyl／shell 一個都不畫（車輪 {N['tire']}、外殼 {N['sk']}、只剩 {N['parts']}）、沒有 ilv2、沒有頁面錯誤",
       N["tire"] == 0 and N["sk"] == 0 and N["sb"] == 0 and N["parts"] == ["pack"] and "ilv2" not in N["cls"] and not errs, [N, errs])

    # ---------------------------------------------------------------- ② 識別特徵
    ok(f"{T}：style 2 的新積木測試圖畫得出來", open_art(pg, "uitest-ilb"))
    F = pg.evaluate(CNT)
    ok(f"{T}：車輪 2 個 —— 輪胎 {F['tire']}、胎紋 {F['tread']}、輪框 {F['rim']}、碟盤 {F['disc']}、輻 {F['spoke']}（每輪 5）、輪轂 {F['hub']}、螺帽 {F['nut']}、接地陰影 {F['ws']}",
       F["tire"] == 2 and F["tread"] == 2 and F["rim"] == 2 and F["disc"] == 2 and F["spoke"] == 10 and F["hub"] == 2 and F["nut"] == 10 and F["ws"] == 2, F)
    ok(f"{T}：橫躺圓柱 2 個 —— 筒身受光漸層 {F['hbody']}、端面 {F['hend']}、散熱環 {F['fins']}（n=5）、色帶 {F['bands']}（n=3）、端面螺栓 {F['bolts']}、頂上接頭 {F['term']}",
       F["hbody"] == 2 and F["hend"] == 2 and F["fins"] == 5 and F["bands"] == 3 and F["bolts"] == 6 and F["term"] >= 1, F)
    ok(f"{T}：外殼 —— 遠側殼 {F['sb']}、擠出面 {F['sf']}、近側殼 {F['sk']}（evenodd 裁切 {F['cpRule']}、{F['cpSub']} 段＝殼＋1 個窗）、開窗切口 {F['cut']}、上緣高光 {F['shl']}、外框 {F['so']}；沒有濾鏡動畫",
       F["sb"] == 1 and F["sf"] >= 5 and F["sk"] == 1 and F["skClip"] and F["cpRule"] == "evenodd" and F["cpSub"] == 2 and F["cut"] == 1 and F["shl"] == 1 and F["so"] == 1 and F["filt"] == 0, F)
    vb = [float(x) for x in F["vb"].split()]
    ok(f"{T}：viewBox {F['vb']} 包得住車輪接地陰影（y ≥ 302）與外殼遠側（往右上擠出 3 格、兩端收窄：x ≥ 392、y ≤ 162）",
       vb[1] + vb[3] >= 302 and vb[0] + vb[2] >= 392 and vb[1] <= 162, vb)

    # ---------------------------------------------------------------- ③ 參數真的有作用
    open_art(pg, "uitest-ilb-noopen")
    G2 = pg.evaluate(CNT)
    ok(f"{T}：open 指定的邊不畫頂面（有 open {F['sf']} 面 < 沒有 open {G2['sf']} 面）；taper 讓遠側輪廓不一樣；cut 拿掉 → 近側殼不裁切、沒有切口",
       F["sf"] < G2["sf"] and F["far"] != G2["far"] and not G2["skClip"] and G2["cut"] == 0, [F["sf"], G2["sf"], G2["skClip"], G2["cut"]])
    c.close()

    # ---------------------------------------------------------------- ④⑤ 深淺 × 1440／390：重疊、濾鏡、主題切換、滑過
    fills = {}
    for theme in ("dark", "light"):
        for w in (1440, 390):
            tag = f"{theme}/{w}"
            c = ctx_for(theme, w); pg = c.new_page()
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            if not open_art(pg, "uitest-ilb"):
                ok(f"{T}[{tag}]：畫得出來", False); c.close(); continue
            m = AU.measure(pg, fx, 0, theme, w, None)
            ok(f"{T}[{tag}]：引線／說明／編號重疊 {m['overlap']}（{ {k: v for k, v in m['overlap_detail'].items() if k != 'where' and v} }）、濾鏡 {m['filters']}、沒有橫向捲軸、沒有頁面錯誤",
               m["overlap"] == 0 and m["filters"] == 0 and not m.get("hscroll") and not errs, [m["overlap_detail"], errs])
            if w == 1440:
                X = pg.evaluate(CNT)
                fills[theme] = (X["tireFill"], X["endFill"])
                ST = """(pid) => { const F = document.querySelector('#artBody .artillus'); const op = (e) => +getComputedStyle(e).opacity;
                    const gs = [...F.querySelectorAll('svg.ilsvg [data-part]')]; return { me: Math.min(...gs.filter(g => g.dataset.part === pid).map(op)), ot: Math.max(...gs.filter(g => g.dataset.part !== pid).map(op)) }; }"""
                pg.locator("#artBody .artillus .ill li[data-part='wheel']").hover(); pg.wait_for_timeout(350)
                s1 = pg.evaluate(ST, "wheel")
                pg.mouse.move(2, 2); pg.wait_for_timeout(350)
                s2 = pg.evaluate(ST, "wheel")
                ok(f"{T}[{tag}]：滑過「車輪」說明 → 兩個車輪不透明、其他零件變淡（{s1['ot']}）；滑開 → 恢復", s1["me"] == 1 and s1["ot"] <= 0.5 and s2["ot"] == 1, [s1, s2])
                if theme == "dark":
                    pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')"); pg.wait_for_timeout(300)
                    Y = pg.evaluate(CNT)
                    ok(f"{T}[{tag}]：不重畫、只切淺色 → 輪胎（{X['tireFill']} → {Y['tireFill']}）與圓柱端面（{X['endFill']} → {Y['endFill']}）顏色真的換",
                       X["tireFill"] != Y["tireFill"] and X["endFill"] != Y["endFill"], [X["tireFill"], Y["tireFill"], X["endFill"], Y["endFill"]])
                    pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'dark')"); pg.wait_for_timeout(200)
            if shots:
                Path(shots).mkdir(parents=True, exist_ok=True)
                pg.locator("#artBody .artillus").first.screenshot(path=str(Path(shots) / f"ilb-{theme}-{w}.png"))
            c.close()

    # ---------------------------------------------------------------- ⑥ 安全
    c = ctx_for("dark", 1440); pg = c.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    open_art(pg, "uitest-ilb-evil")
    X = pg.evaluate("""() => { const s = document.querySelector('#artBody svg.ilsvg'); const css = (document.getElementById('artIlCss2') || {}).textContent || '';
        const nums = (s ? s.innerHTML : '').match(/-?[0-9]+(\\.[0-9]+)?(e[+-]?[0-9]+)?/g) || [];
        return { xss: !!window.__ilbXss, imgs: document.querySelectorAll('#artBody img, #artBody script').length, html: s ? s.innerHTML : '', css,
                 big: nums.filter(n => Math.abs(+n) > 5000).length, sk: s ? s.querySelectorAll('polygon.qsk').length : -1, cut: s ? s.querySelectorAll('polygon.qcut').length : -1 }; }""")
    bad = [k for k in ("<img", "onerror", "onload", "<script", "<svg", "<b>", "<i>", "toString", "constructor", "NaN", "Infinity") if k in X["html"] or k in X["css"]]
    ok(f"{T}：外殼／車輪塞 HTML 或怪值 → 不執行、不出現在 SVG 與樣式（命中 {bad}）、座標全部夾值（超過 5000 的數字 {X['big']} 個）、壞的窗被擋掉、壞的 type 不畫、沒有頁面錯誤",
       not X["xss"] and X["imgs"] == 0 and not bad and X["big"] == 0 and X["sk"] in (1, 2) and X["cut"] <= 3 and not errs, [bad, X["big"], X["sk"], X["cut"], errs])
    c.close()


register("精選文章插圖積木1017", lambda pg, b, base, code: t_illus_blocks_1017(b, base), after="精選文章插圖v2")
