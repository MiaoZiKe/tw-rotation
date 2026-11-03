# 驗收段落「診斷圖修正1103」：機構審查 W1～W4（switch_wireless 金色接點被拉寬、氣冷反轉雙轉子前後各有馬達、
# 晶圓代工 GAA 那格箭頭、交換器板層數口徑）。每一項都驗「畫面真的因此改變了」，不是只驗元素存在。
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def t_dg_fix_1103(b, base, code):
    T = "診斷圖修正1103"
    errs = []
    for w in (1440, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            # ---- W1／W4 switch_wireless
            pg.goto(base + "#industry/ai_server/dg/switch_wireless", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('svg.dgsw rect.cage').length > 0", 20000)
            r = pg.evaluate("""() => { const s = document.querySelector('svg.dgsw'), sw = s.getBoundingClientRect().width;
              const t = [...s.querySelectorAll('rect.ftab')].map(e => e.getBoundingClientRect().width);
              return { n: t.length, max: Math.max(...t), sw, oldTab: s.querySelectorAll('rect.tab').length,
                       head: document.querySelector('.dghead') ? document.querySelector('.dghead').textContent : document.body.innerText.slice(0, 400) }; }""")
            ok(f"【{T}】{w} 籠架金色接點 class 改名 ftab、舊 .tab 一個都不剩（不再被 layout4 的 .tab{{width:100%}} 命中）", r["n"] >= 16 and r["oldTab"] == 0, r)
            ok(f"【{T}】{w} 金色接點畫出來的寬度＜圖寬 5%（以前被拉到整張圖寬）", r["max"] < r["sw"] * 0.05, r)
            ok(f"【{T}】{w} 標題改「近 40 層以上」並有口徑（約 38～48 層）", "近 40 層以上" in r["head"] and "38～48" in r["head"], r["head"][:120])
            # ---- W2 air_cooling
            pg.goto(base + "#industry/ai_server/dg/air_cooling", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('svg.dgair [data-part=\"motor\"]').length > 0", 20000)
            a = pg.evaluate("""() => { const s = document.querySelector('svg.dgair');
              const by = (p) => [...s.querySelectorAll(`g[data-part="${p}"]`)].map(e => e.getBoundingClientRect().top).sort((x, y) => x - y);
              const txt = [...s.querySelectorAll('text')].map(e => e.textContent);
              return { motor: by('motor'), frame: by('fan_frame'), blade: by('blade'), rot2: by('counter_rot'),
                       lab: ['前扇框', '前組馬達', '後組馬達', '後扇框'].map(k => txt.includes(k)) }; }""")
            order = (len(a["frame"]) == 2 and len(a["motor"]) == 2 and len(a["blade"]) == 1 and len(a["rot2"]) == 1
                     and a["frame"][0] < a["blade"][0] < a["motor"][0] < a["rot2"][0] < a["motor"][1] < a["frame"][1])
            ok(f"【{T}】{w} 氣冷爆炸圖由上到下＝前扇框、前轉子、前馬達、後轉子、後馬達、後扇框（兩顆馬達、兩個扇框）", order, a)
            ok(f"【{T}】{w} 前扇框／前組馬達／後組馬達／後扇框四個標字都在", all(a["lab"]), a["lab"])
            if not mob:
                before = pg.evaluate("() => document.querySelectorAll('svg.dgair g[data-part=\"motor\"].sel-part').length")
                pg.evaluate("() => document.querySelector('svg.dgair g[data-part=\"motor\"]').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
                pg.wait_for_timeout(500)
                after = pg.evaluate("() => document.querySelectorAll('svg.dgair g[data-part=\"motor\"].sel-part').length")
                ok(f"【{T}】{w} 點馬達 → 前後兩組馬達一起亮（選取狀態真的變了）", before == 0 and after == 2, (before, after))
            # ---- W3 foundry
            pg.goto(base + "#industry/semiconductor/dg/foundry", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('[data-part=\"fd_face4\"] path.arw').length > 0", 20000)
            f = pg.evaluate("""() => { const q = (s) => [...document.querySelectorAll(s)];
              const d = q('[data-part="fd_face4"] path.arw').map(e => e.getAttribute('d').match(/-?[\\d.]+/g).map(Number));
              return { f4: d.length, f4oop: q('[data-part="fd_face4"] circle.arwx').length, horiz: d.filter(a => Math.abs(a[1] - a[3]) < 0.5).length,
                       f3: q('[data-part="fd_face3"] path.arw').length, f1: q('[data-part="fd_face1"] path.arw').length }; }""")
            ok(f"【{T}】{w} GAA 格：沿通道剖面只畫上下兩支箭頭、左右（源汲方向）一支都不畫，前後兩面用 ⊙⊗，合計 4 面", f["f4"] == 2 and f["horiz"] == 0 and f["f4oop"] == 2, f)
            ok(f"【{T}】{w} 平面 1 面、FinFET 3 面不受影響", f["f1"] == 1 and f["f3"] == 3, f)
        except Exception as e:
            ok(f"【{T}】{w} 操作中途爆掉", False, repr(e)[:200])
        finally:
            c.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])


register("診斷圖修正1103", lambda pg, b, base, code: t_dg_fix_1103(b, base, code))
