# 驗收段落「精選文章圖表擴充1017」—— 2026-10-17 新增（拆檔防合併衝突：新段落一律放 scripts/uitest_sections/）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、ROOT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章圖表擴充1017（site/articles.js 的 chart 區塊：signed／refs／bands）
# 依 docs/articles/visual_playbook.md 第 7 節高優先 #1、#2；Andy：「觀眾大多為視覺系生物，對圖片圖表敏感度高於文字」
# 做法：攔截一篇公開舊文章（台積電 9 月營收）的全文 JSON，原樣保留它的兩張舊圖，尾巴再塞三張新圖：
#   A：bar  signed＋refs（含壞值）＋highlight         —— 個股漲跌幅
#   B：hbar signed＋refs（x）                          —— 外資買賣超
#   C：barline signed 長條＋折線＋bands（含不精確日期與壞值）＋refs —— 月營收年增率＋升息期間
# 驗：
#   ① 正的長條＝--rise、負的＝--fall（讀 ECharts option 的漸層色，跟頁面的 CSS 變數比），而且兩者真的不同、紅色系（R 最大）＝漲
#   ② 畫面上的標籤（?svg=1 讀 SVG 文字）正數帶 +、負數帶 -
#   ③ 參考線（markLine）與陰影（markArea）真的在 option 裡、文字真的畫在 SVG 上；陰影的矩形真的有面積
#   ④ 壞值被忽略：非數字、空字串、離資料太遠的參考線不畫；找不到的區間不畫；大括號／HTML 只當純文字（不執行、不變成元素、不走 ECharts 富文字）
#   ⑤ 舊圖 option 不變：同一篇舊文章的兩張圖，用 origin/main 的 articles.js 與這一版各畫一次，JSON 逐字一樣
#   ⑥ 1440 淺色、390 深色：圖內文字兩兩不重疊、字 ≥ 11px（SVG 乘 getScreenCTM）、沒有橫向捲軸
#   ⑦ 真的操作：滑過正負長條 → 提示框的數字帶正負號、不會出現輔助系列（__artaux）
def t_art_chart_ext_1017(b, base):
    import subprocess as _sp
    T = "精選文章圖表擴充1017"
    API = "https://uitest-art-chart.invalid"
    AID = "2026-10-14-news-tsmc-sep-revenue"
    src = json.loads((SITE / "articles" / "posts" / (AID + ".json")).read_text(encoding="utf-8"))
    old_idx = [i for i, bl in enumerate(src["blocks"]) if bl.get("t") == "chart"]
    XSS = "<img onerror=x>{a|富}"   # 24 字以內（參考線文字上限 24 字，超過會被截）
    A = {"t": "chart", "kind": "bar", "signed": True, "title": "驗收：個股今日漲跌幅", "unit": "%", "x": ["台積電", "聯發科", "鴻海", "日月光", "廣達", "聯電"],
         "series": [{"name": "漲跌幅", "data": [3.2, -1.5, 0.8, -2.4, 0, 1.1]}], "highlight": [0],
         "refs": [{"y": 2, "label": "大盤 +2"}, {"y": "abc", "label": "壞值字串"}, {"y": "", "label": "空字串"}, {"y": None, "label": "空值"},
                  {"y": 1e9, "label": "太遠"}, {"y": True, "label": "布林"}, "不是物件", [1, 2]]}
    B = {"t": "chart", "kind": "hbar", "sign": True, "title": "驗收：外資買賣超", "unit": "億", "x": ["台積電", "鴻海", "聯發科", "廣達", "緯創", "台達電"],
         "series": [{"name": "買賣超", "data": [120, -80, 45, -230, 15, -10]}], "refs": [{"x": 50, "label": "近 20 日均"}, {"y": "x"}]}
    months = [f"{y}-{m:02d}" for y in (2022, 2023) for m in range(1, 13)]
    yoy = [12, 8, 5, -3, -6, -9, -12, -8, -4, 2, 6, 9, 11, 7, 3, -2, -5, -1, 4, 8, 10, 12, 9, 6]
    C = {"t": "chart", "kind": "barline", "signed": True, "title": "驗收：營收年增率與升息期間", "unit": "%", "y2unit": "億元", "x": months,
         "series": [{"name": "年增率", "type": "bar", "data": yoy, "axis": 0}, {"name": "營收", "type": "line", "data": [3000 + i * 40 for i in range(24)], "axis": 1}],
         "refs": [{"y": 0, "label": "零成長"}, {"y": 10, "text": XSS}],
         "bands": [{"from": "2022-03", "to": "2022-12", "label": "升息期間"}, {"from": "2023-06-15", "to": "2023-09-30", "label": "去庫存"},
                   {"from": "沒有這個月", "to": "2023-01", "label": "壞值"}, {"from": {"x": 1}, "to": "2023-01"}, {"from": "2023-01", "label": "缺 to"}]}
    post = dict(src)
    post["blocks"] = list(src["blocks"]) + [{"t": "h", "text": "驗收用新圖"}, A, B, C]
    NEW = [len(src["blocks"]) + 1, len(src["blocks"]) + 2, len(src["blocks"]) + 3]
    try:
        old_js = _sp.run(["git", "show", "origin/main:site/articles.js"], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8").stdout
    except Exception:
        old_js = ""

    def prep(ctx, theme, use_old=False, inject=True):
        ctx.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme'," + json.dumps(theme) + ")}catch(e){}")
        ctx.route(API + "/**", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"views":{}}'))
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        if inject:
            ctx.route("**/articles/posts/" + AID + ".json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(post, ensure_ascii=False)))
        if use_old and old_js:
            import re as _re
            ctx.route(_re.compile(r".*/articles\.js(\?.*)?$"), lambda r: r.fulfill(status=200, content_type="application/javascript", body=old_js))

    OPT = """(bis) => bis.map(bi => { const el = document.querySelector('#artBody .artchart[data-bi="' + bi + '"] .cv'); const c = el && echarts.getInstanceByDom(el);
        return c ? JSON.stringify(c.getOption()) : null; })"""

    def load(pg, want):
        pg.goto(base + "?svg=1#article/" + AID, wait_until="domcontentloaded")
        okk = wait_until(pg, "() => { const cs = [...document.querySelectorAll('#artBody .artchart .cv')]; return cs.length >= " + str(int(want)) + " && cs.every(e => window.echarts && echarts.getInstanceByDom(e)); }", 20000)
        pg.wait_for_timeout(700)
        return okk

    # ⑤ 舊圖 option 不變（origin/main 的 articles.js vs 這一版；同一篇沒加料的文章）
    if old_js:
        res = {}
        for tag, use_old in (("old", True), ("new", False)):
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            prep(ctx, "dark", use_old=use_old, inject=False)
            pg = ctx.new_page()
            load(pg, len(old_idx))
            res[tag] = pg.evaluate(OPT, old_idx)
            ctx.close()
        ok(f"{T}：沒帶 signed／refs／bands 的舊圖（{AID} 的 {len(old_idx)} 張）—— main 版與這一版畫出的 option 逐字一樣",
           all(res["old"]) and res["old"] == res["new"], [len(x or "") for x in res["old"]] + [len(x or "") for x in res["new"]])
    else:
        ok(f"{T}：取得 origin/main 的 articles.js（比對舊圖用）", False, "git show 失敗")

    MEAS = """(bi) => { const F = document.querySelector('#artBody .artchart[data-bi="' + bi + '"]'); if (!F) return null;
      const el = F.querySelector('.cv'), c = echarts.getInstanceByDom(el), o = c.getOption();
      const catAx = [].concat(o.xAxis || [], o.yAxis || []).find(z => z && z.type === 'category'); const cats = catAx ? catAx.data : [];
      const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      const ser = o.series.map(s => ({ id: s.id, name: s.name, type: s.type,
        cols: (s.data || []).map(d => d && d.itemStyle && d.itemStyle.color && d.itemStyle.color.colorStops ? d.itemStyle.color.colorStops.map(z => z.color) : null),
        vals: (s.data || []).map(d => d && typeof d === 'object' && !Array.isArray(d) ? d.value : d),
        ml: s.markLine && s.markLine.data ? s.markLine.data.map(m => m.yAxis != null ? m.yAxis : m.xAxis) : [],
        ma: s.id === '__artband' ? (s.data || []).map(d => [cats[d[0]], cats[d[1]]]) : [] }));
      const svg = el.querySelector('svg');
      const vis = (t) => { let e = t; while (e && e !== svg) { const op = e.getAttribute && (e.getAttribute('opacity') || e.getAttribute('fill-opacity')); if (op != null && +op === 0) return false; e = e.parentNode; } return true; };
      const clipped = (t) => { let e = t.parentNode; while (e && e !== svg) { if (e.getAttribute && e.getAttribute('clip-path')) return true; e = e.parentNode; } return !!(t.getAttribute && t.getAttribute('clip-path')); };
      const texts = svg ? [...svg.querySelectorAll('text')].filter(t => t.textContent.trim() && t.textContent.trim() !== '哩股哩股' && vis(t)) : [];   // 哩股哩股＝全站圖表浮水印（淡底字，本來就壓在圖上）
      const R = (e) => e.getBoundingClientRect();
      const boxes = texts.map(t => { const r = R(t); const m = t.getScreenCTM(); const fs = parseFloat(t.getAttribute('font-size') || getComputedStyle(t).fontSize) * (m ? Math.hypot(m.a, m.b) : 1);
        return { s: t.textContent, clip: clipped(t), l: r.left, r: r.right, t: r.top, b: r.bottom, fs }; }).filter(x => x.r - x.l > 0);
      const hits = []; for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) { const a = boxes[i], z = boxes[j];
        const ox = Math.min(a.r, z.r) - Math.max(a.l, z.l), oy = Math.min(a.b, z.b) - Math.max(a.t, z.t); if (ox > 1 && oy > 1) hits.push([a.s, z.s]); }
      // 陰影矩形：fill 帶 0.16 透明度的 path／rect（markArea），量它在螢幕上的寬度
      const areas = svg ? [...svg.querySelectorAll('path, rect')].filter(p => /0\\.16\\)/.test(p.getAttribute('fill') || '') || (+(p.getAttribute('fill-opacity') || 1) > 0.1 && +(p.getAttribute('fill-opacity') || 1) < 0.2)).map(p => R(p).width) : [];
      const dash = svg ? [...svg.querySelectorAll('path')].filter(p => (p.getAttribute('stroke-dasharray') || '') !== '' && (p.getAttribute('stroke-dasharray') || '') !== 'none').length : 0;
      const fr = R(F);
      return { ser, clippedTexts: boxes.filter(x => x.clip).map(x => x.s), rise: css('--rise'), fall: css('--fall'), texts: boxes.map(x => x.s), hits, minFs: Math.min(...boxes.map(x => x.fs)), areas, dash,
        figL: fr.left, figR: fr.right, vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth,
        xss: !!window.__acXss, imgs: document.querySelectorAll('#artBody img').length };
    }"""

    def rgb(c):
        import re as _re
        c = c.strip()
        m = _re.match(r"#([0-9a-f]{6})$", c, _re.I)
        if m:
            h = m.group(1); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        v = _re.findall(r"[\d.]+", c)
        return tuple(int(float(z)) for z in v[:3]) if len(v) >= 3 else None

    shots = Path(os.environ.get("TW_ART_CHART_SHOTS") or "")
    for theme, w in (("light", 1440), ("dark", 390), ("dark", 1440), ("light", 390)):
        mob = w < 640
        tag = f"{theme}/{w}"
        ctx = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, device_scale_factor=1 if not mob else 2, is_mobile=mob, has_touch=mob)
        prep(ctx, theme)
        errs = []
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if not load(pg, len(old_idx) + 3):
            ok(f"{T}[{tag}]：三張新圖畫出來", False, pg.evaluate("() => document.querySelectorAll('#artBody .artchart').length")); ctx.close(); continue
        ms = {}
        for k, bi in zip("ABC", NEW):
            pg.evaluate("(bi) => document.querySelector('#artBody .artchart[data-bi=\"' + bi + '\"]').scrollIntoView({block: 'center', behavior: 'instant'})", bi)
            pg.wait_for_timeout(250)
            ms[k] = pg.evaluate(MEAS, bi)
        rise, fall = rgb(ms["A"]["rise"]), rgb(ms["A"]["fall"])
        ok(f"{T}[{tag}]：站上漲跌色紅漲綠跌（--rise {ms['A']['rise']} 紅色系、--fall {ms['A']['fall']} 綠色系）",
           rise and fall and rise[0] > rise[1] and fall[1] > fall[0], [rise, fall])

        def sign_ok(m, si, vals):
            s = m["ser"][si]; bad = []
            for i, v in enumerate(vals):
                col = s["cols"][i]
                if not col: bad.append((i, "沒漸層")); continue
                c1 = rgb(col[-1] if col[-1].startswith("rgba") else col[0])
                tgt = rise if v > 0 else fall if v < 0 else None
                if tgt and (not c1 or c1[:3] != tgt[:3]): bad.append((i, v, col))
            return bad
        A_vals, B_vals = A["series"][0]["data"], B["series"][0]["data"]
        bA, bB, bC = sign_ok(ms["A"], 0, A_vals), sign_ok(ms["B"], 0, B_vals), sign_ok(ms["C"], 0, yoy)
        ok(f"{T}[{tag}]：正負上色 —— 直條／橫條／直條＋折線，正的長條＝--rise、負的＝--fall（逐根比對漸層色）", not bA and not bB and not bC, [bA, bB, bC])
        pc = ms["A"]["ser"][0]["cols"]
        ok(f"{T}[{tag}]：正負兩根顏色真的不同（台積電 {pc[0][0] if pc[0] else ''} vs 聯發科 {pc[1][0] if pc[1] else ''}）", pc[0] and pc[1] and pc[0] != pc[1], [pc[0], pc[1]])
        ok(f"{T}[{tag}]：直條＋折線那張的折線不吃正負色（還是原本的單一色）", ms["C"]["ser"][1]["type"] == "line" and not any(ms["C"]["ser"][1]["cols"]), ms["C"]["ser"][1]["cols"][:3])
        tA, tB = ms["A"]["texts"], ms["B"]["texts"]
        ok(f"{T}[{tag}]：畫面上的數字標籤帶正負號（直條 +3.2／-1.5／-2.4；橫條 +120／-230）",
           "+3.2" in tA and "-1.5" in tA and "-2.4" in tA and "+120" in tB and "-230" in tB and "+1.1" in tA, [tA, tB])
        # ③ 參考線與陰影
        auxA = [s for s in ms["A"]["ser"] if s["id"] == "__artaux"]
        auxB = [s for s in ms["B"]["ser"] if s["id"] == "__artaux"]
        auxC = [s for s in ms["C"]["ser"] if s["id"] == "__artaux"]
        bandC = [s for s in ms["C"]["ser"] if s["id"] == "__artband"]
        ok(f"{T}[{tag}]：參考線 —— 直條只留 1 條合法的（y=2；壞字串、空字串、null、布林、1e9 都被丟掉）、文字畫出來；畫面有虛線",
           len(auxA) == 1 and auxA[0]["ml"] == [2] and any(t.startswith("大盤 +2") for t in tA) and ms["A"]["dash"] >= 1 and not any("壞值" in t or "太遠" in t or "空" in t or "布林" in t for t in tA),
           [auxA and auxA[0]["ml"], tA, ms["A"]["dash"]])
        ok(f"{T}[{tag}]：橫條的參考線用 x（50）、文字畫出來；壞的 {{y:'x'}} 被丟掉", len(auxB) == 1 and auxB[0]["ml"] == [50] and any("近 20 日均" in t for t in tB), [auxB and auxB[0]["ml"], tB])
        tC = ms["C"]["texts"]
        ok(f"{T}[{tag}]：區間陰影 —— 升息期間 2022-03～2022-12、去庫存（不精確日期 2023-06-15～2023-09-30 → 2023-07～2023-09）；壞的 3 段不畫；標籤畫出來、陰影矩形有面積",
           len(bandC) == 1 and bandC[0]["ma"] == [["2022-03", "2022-12"], ["2023-07", "2023-09"]] and "升息期間" in tC and "去庫存" in tC and "壞值" not in tC
           and len([a for a in ms["C"]["areas"] if a > 10]) >= 2, [bandC and bandC[0]["ma"], tC, ms["C"]["areas"]])
        ok(f"{T}[{tag}]：區間與參考線的文字沒有被繪圖區裁掉（SVG 文字的祖先沒有 clip-path）",
           not any(t in ("升息期間", "去庫存") or "零成長" in t or "大盤" in t for t in ms["C"]["clippedTexts"] + ms["A"]["clippedTexts"] + ms["B"]["clippedTexts"]),
           [ms[k]["clippedTexts"] for k in "ABC"])
        ok(f"{T}[{tag}]：參考線文字裡的 HTML 與 ECharts 富文字大括號只當純文字（全形括號、不執行、不變成 img）；沒有頁面錯誤",
           any("<img onerror=x>｛a｜富｝" in t for t in tC) and not ms["C"]["xss"] and ms["C"]["imgs"] == 0 and not errs, [[t for t in tC if "img" in t], errs])
        # ⑥ 版面
        for k in "ABC":
            m = ms[k]
            ok(f"{T}[{tag}]：圖 {k} 圖內文字兩兩不重疊（{len(m['texts'])} 段）、字 ≥ 11px（最小 {m['minFs']:.1f}）、圖不超出畫面、沒有橫向捲軸",
               not m["hits"] and m["minFs"] >= 11 and m["figL"] >= 0 and m["figR"] <= m["vw"] + 0.5 and m["sw"] <= 0, {"hits": m["hits"], "minFs": m["minFs"], "sw": m["sw"], "fig": [m["figL"], m["figR"], m["vw"]]})
        # ⑦ 真的操作：滑過正、負長條 → 提示框帶正負號、不會有輔助系列
        if not mob:
            tips = []
            for i in (0, 1):
                pg.evaluate("(bi) => document.querySelector('#artBody .artchart[data-bi=\"' + bi + '\"]').scrollIntoView({block: 'center', behavior: 'instant'})", NEW[0])
                pg.wait_for_timeout(200)
                pt = pg.evaluate("""([bi, i]) => { const el = document.querySelector('#artBody .artchart[data-bi="' + bi + '"] .cv'); const c = echarts.getInstanceByDom(el);
                    const p = c.convertToPixel({ seriesIndex: 0 }, [i, 0]); const r = el.getBoundingClientRect(); return [r.left + p[0], r.top + p[1] - 6]; }""", [NEW[0], i])
                pg.mouse.move(pt[0], pt[1]); pg.wait_for_timeout(350)
                tips.append(pg.evaluate("() => { const t = [...document.querySelectorAll('body > div')].filter(d => /漲跌幅/.test(d.textContent) && getComputedStyle(d).display !== 'none' && getComputedStyle(d).visibility !== 'hidden' && +getComputedStyle(d).opacity > 0); return t.length ? t[t.length - 1].textContent : ''; }"))
            pg.mouse.move(2, 2)
            ok(f"{T}[{tag}]：滑過正的長條 → 提示框「+3.2」、滑過負的 → 「-1.5」，提示框裡沒有輔助系列 __artaux",
               "+3.2" in tips[0] and "-1.5" in tips[1] and not any("__artaux" in t for t in tips), tips)
        if str(shots) not in ("", "."):
            shots.mkdir(parents=True, exist_ok=True)
            for k, bi in zip("ABC", NEW):
                loc = pg.locator(f"#artBody .artchart[data-bi='{bi}']")
                loc.scroll_into_view_if_needed(); pg.wait_for_timeout(150)
                loc.screenshot(path=str(shots / f"chart{k}-{theme}-{w}.png"))
        ctx.close()


register("精選文章圖表擴充1017", lambda pg, b, base, code: t_art_chart_ext_1017(b, base), after="精選文章1014")
