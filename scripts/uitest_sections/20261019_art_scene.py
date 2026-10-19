# 驗收段落「文章3D區塊1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 文章3D區塊1019
# 10-19 稽核（docs/articles/quality_audit_1019.md）兩件網頁需求：
#   #10 390 手機 8 篇第一屏都看不到圖 → 手機把副標／族群／標籤／摘要收成一顆「導讀・相關族群」，第一屏（844 高）要看得到第一個視覺區塊
#   #11 新區塊 {t:'scene', kind:'3d'|'25d', id, title, caption}：文章內直接嵌站內 3D／2.5D 剖析圖
# 做法照 20261017_article_video.py：拿一篇公開舊文章，在這個 context 裡把全文換成「原文＋scene 區塊」（repo 不動），1440 與 390 真的操作：
#   ① 進文章時 scene 區塊只是骨架（data-st=idle、沒有 canvas、three3d.js 還沒載）＝捲到才初始化
#   ② 捲到 3D 區塊 → three3d.js 才載入、畫布真的有畫出東西（截畫布那一塊、數不同顏色）
#   ③ 手機：3D 與 2.5D 都先是預覽（.pv、高度 ≤ 300、蓋一顆「點開互動」）；點了 → 預覽拿掉、高度放開、可以操作
#   ④ 2.5D：點一個環節 → 它亮起（.sel）、其他變淡（.dim）
#   ⑤ 壞 id：站內沒有的圖 → 一行說明＋「到站內頁面看」連結；格式不對（帶引號）整塊不畫、不執行；文章其他部分照常、沒有網頁錯誤
#   ⑥ 沒有橫向捲軸
SCENE_BLOCKS = [
    {"t": "scene", "kind": "3d", "id": "semiconductor", "title": "CoWoS-L 立體剖面（測試）", "caption": "拖曳旋轉、點零件看名稱（測試）"},
    {"t": "scene", "kind": "25d", "id": "cowos", "title": "CoWoS 供應鏈 2.5D（測試）", "caption": "點環節亮起（測試）"},
    {"t": "scene", "kind": "3d", "id": "no_such_scene", "title": "壞 id（測試）"},
    {"t": "scene", "kind": "25d", "id": "nope_theme", "title": "壞 2.5D id（測試）"},
    {"t": "scene", "kind": "3d", "id": "\"><img src=x onerror=window.__sceneXss=1>"},
    {"t": "scene", "kind": "4d", "id": "hbm"},
]
VISUAL_SEL = ".artkpi, .artchart, .artflow, .artstack, .artillus, .artsteps, .artcompare, .artvid, .artscene, .tbw, .artstk"


def _px_rich(png: bytes) -> dict:
    """截圖裡有幾種顏色、亮度標準差：空白畫布＝1～2 種顏色、標準差 0。"""
    try:
        from PIL import Image, ImageStat
        import io
        im = Image.open(io.BytesIO(png)).convert("RGB")
        small = im.resize((max(1, im.width // 4), max(1, im.height // 4)))
        raw = small.tobytes(); cols = len({raw[i:i + 3] for i in range(0, len(raw), 3)})
        sd = ImageStat.Stat(im.convert("L")).stddev[0]
        return {"cols": cols, "sd": round(sd, 1)}
    except Exception as e:   # 沒有 PIL：退回只看檔案大小（純色 PNG 很小）
        return {"cols": 999 if len(png) > 20000 else 0, "sd": -1, "err": str(e)}


def t_art_scene_1019(b, base, code):
    T = "文章3D區塊1019"
    errs: list[str] = []
    idx = json.loads((SITE / "articles" / "index.json").read_text(encoding="utf-8"))["articles"]
    pub = [a for a in idx if a.get("src") != "api" and (SITE / "articles" / "posts" / f"{a['id']}.json").exists()]
    if not ok(f"{T}：有公開的舊文章可以拿來測", bool(pub)):
        return
    aid = pub[0]["id"]
    post = json.loads((SITE / "articles" / "posts" / f"{aid}.json").read_text(encoding="utf-8"))
    post["blocks"] = post["blocks"] + SCENE_BLOCKS   # 放在文末：一進文章一定不在畫面附近，才驗得到「捲到才初始化」
    shots = os.environ.get("TW_SCENE_SHOT")
    for w in (1440, 390):
        c = b.new_context(viewport={"width": w, "height": 900 if w > 640 else 844})
        c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.tour','done');localStorage.removeItem('tw.art.hd')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(f"**/articles/posts/{aid}.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(post, ensure_ascii=False)))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + f"#article/{aid}", wait_until="domcontentloaded")
        got = wait_until(pg, "() => document.querySelectorAll('.artscene').length >= 1 ? 1 : 0", 15000)
        if not ok(f"{T}（{w}）：文章頁畫出 scene 區塊", bool(got)):
            c.close(); continue
        pg.wait_for_timeout(1200)
        st0 = pg.evaluate("""() => { const f = [...document.querySelectorAll('.artscene')];
            return { n: f.length, st: f.map(x => x.dataset.st), cv: document.querySelectorAll('.artscene canvas').length, r3d: !!window.Rack3D,
              kinds: f.map(x => x.dataset.kind + ':' + x.dataset.sid), xss: !!window.__sceneXss }; }""")
        ok(f"{T}（{w}）：還沒捲到 → 4 塊都是骨架（idle）、沒有 canvas、three3d.js 還沒載；格式不對的 id 與不支援的 kind 整塊不畫",
           st0["n"] == 4 and all(s == "idle" for s in st0["st"]) and st0["cv"] == 0 and not st0["r3d"] and not st0["xss"], st0)
        # ② 捲到 3D 區塊
        pg.locator(".artscene.k3d >> nth=0").scroll_into_view_if_needed()
        ready = wait_until(pg, "() => { const f = document.querySelector('.artscene.k3d'); return f && f.dataset.st !== 'idle' && f.dataset.st !== 'loading' ? 1 : 0; }", 40000, 300)
        pg.wait_for_timeout(1500)
        s3 = pg.evaluate("""() => { const f = document.querySelector('.artscene.k3d'), cv = f && f.querySelector('canvas'), r = cv && cv.getBoundingClientRect();
            return { st: f && f.dataset.st, cv: !!cv, w: r ? Math.round(r.width) : 0, h: r ? Math.round(r.height) : 0, r3d: !!window.Rack3D,
              pv: f.classList.contains('pv'), ov: !!f.querySelector('.asov'), wh: Math.round(f.querySelector('.asw').getBoundingClientRect().height),
              link: (f.querySelector('.asf a') || {}).getAttribute && f.querySelector('.asf a').getAttribute('href') }; }""")
        px = {}
        if s3["cv"]:
            # 截畫布那一塊（截圖＝螢幕上真的看到的；WebGL 的 toDataURL 在這個容器不可靠，DECISIONS #199）
            if s3["pv"]:
                pg.evaluate("() => { const o = document.querySelector('.artscene.k3d .asov'); if (o) o.style.visibility = 'hidden'; }")
            px = _px_rich(pg.locator(".artscene.k3d canvas >> nth=0").screenshot())
            if s3["pv"]:
                pg.evaluate("() => { const o = document.querySelector('.artscene.k3d .asov'); if (o) o.style.visibility = ''; }")
        ok(f"{T}（{w}）：捲到 3D 區塊 → three3d.js 才載入、畫布 {s3['w']}×{s3['h']} 真的畫出東西（{px.get('cols')} 種顏色、亮度標準差 {px.get('sd')}）、下方有「在站內完整頁面看」連到 #industry/group/ai_adv_packaging",
           bool(ready) and s3["st"] == "ready" and s3["cv"] and s3["w"] >= 280 and s3["h"] >= 200 and s3["r3d"] and px.get("cols", 0) >= 20 and px.get("sd", 0) != 0
           and s3["link"] == "#industry/group/ai_adv_packaging", [s3, px])
        if w <= 640:
            ok(f"{T}（{w}）：手機 3D 先是預覽（高度 {s3['wh']} ≤ 300、蓋一顆「點開互動」，手指照常捲頁面）", s3["pv"] and s3["ov"] and s3["wh"] <= 302, s3)
            if shots:
                pg.locator(".artscene.k3d >> nth=0").scroll_into_view_if_needed(); pg.wait_for_timeout(300)
                pg.screenshot(path=shots.replace(".png", f"_{w}_3dpv.png"))
            pg.locator(".artscene.k3d .asov").click(); pg.wait_for_timeout(1500)
            s3b = pg.evaluate("""() => { const f = document.querySelector('.artscene.k3d'), cv = f.querySelector('canvas');
                return { pv: f.classList.contains('pv'), ov: !!f.querySelector('.asov'), open: f.dataset.open, wh: Math.round(f.querySelector('.asw').getBoundingClientRect().height),
                  pe: cv ? getComputedStyle(cv).pointerEvents : null }; }""")
            ok(f"{T}（{w}）：點「點開互動」→ 預覽拿掉、在原地展開（高度 {s3['wh']} → {s3b['wh']}）、畫布可以操作", not s3b["pv"] and not s3b["ov"] and s3b["open"] == "1" and s3b["wh"] > s3["wh"] and s3b["pe"] != "none", s3b)
        elif shots:
            pg.locator(".artscene.k3d >> nth=0").scroll_into_view_if_needed(); pg.wait_for_timeout(500)
            pg.screenshot(path=shots.replace(".png", f"_{w}_3d.png"))
        # ③ 2.5D
        pg.locator(".artscene.k25d >> nth=0").scroll_into_view_if_needed()
        wait_until(pg, "() => { const f = document.querySelector('.artscene.k25d'); return f && (f.dataset.st === 'ready' || f.dataset.st === 'fail') ? 1 : 0; }", 20000, 300)
        pg.wait_for_timeout(800)
        s25 = pg.evaluate("""() => { const f = document.querySelector('.artscene.k25d');
            return { st: f.dataset.st, svg: !!f.querySelector('svg.dg3'), parts: f.querySelectorAll('[data-part], .vstep[data-p]').length, pv: f.classList.contains('pv'),
              wh: Math.round(f.querySelector('.asw').getBoundingClientRect().height), link: f.querySelector('.asf a').getAttribute('href') }; }""")
        ok(f"{T}（{w}）：捲到 2.5D 區塊 → 題材剖析圖畫出來（{s25['parts']} 個環節）、連結到 #heatmap/theme/cowos",
           s25["st"] == "ready" and s25["svg"] and s25["parts"] >= 3 and s25["link"] == "#heatmap/theme/cowos", s25)
        if w <= 640:
            ok(f"{T}（{w}）：手機 2.5D 也先是預覽（高度 {s25['wh']} ≤ 300）", s25["pv"] and s25["wh"] <= 302, s25)
        if w > 640:
            # 桌機：點一個環節 → 它亮起、其他變淡（文章這邊 wireScene25 接的，跟題材頁同一套規則）
            part = pg.evaluate("() => { const n = document.querySelector('.artscene.k25d .p3.stn[data-part]') || document.querySelector('.artscene.k25d [data-part]'); return n.dataset.part; }")
            pg.locator(f".artscene.k25d [data-part='{part}'] >> nth=0").click(force=True)
            pg.wait_for_timeout(300)
            s25b = pg.evaluate("() => { const f = document.querySelector('.artscene.k25d'); return { sel: f.querySelectorAll('[data-part].sel').length, dim: f.querySelectorAll('[data-part].dim').length, h: location.hash }; }")
            ok(f"{T}（{w}）：點 2.5D 的環節「{part}」→ 它亮起、其他變淡（就地，不跳頁）", s25b["sel"] >= 1 and s25b["dim"] >= 1 and s25b["h"] == f"#article/{aid}", s25b)
        else:
            # 手機：2.5D 是直排步驟版（themes3d.js .vstep），點「點開互動」後點第 2 步 → 那一步展開（aria-expanded）
            pg.locator(".artscene.k25d .asov").click(); pg.wait_for_timeout(500)
            pg.locator(".artscene.k25d .vstep[data-i='1'] >> nth=0").click(force=True); pg.wait_for_timeout(400)
            s25b = pg.evaluate("() => { const f = document.querySelector('.artscene.k25d'), v = f.querySelector(\".vstep[data-i='1']\"); return { pv: f.classList.contains('pv'), ex: v && v.getAttribute('aria-expanded'), wh: Math.round(f.querySelector('.asw').getBoundingClientRect().height), h: location.hash }; }")
            ok(f"{T}（{w}）：點「點開互動」→ 2.5D 在原地展開（高度 {s25['wh']} → {s25b['wh']}）；點第 2 步 → 那一步展開、不跳頁", not s25b["pv"] and s25b["ex"] == "true" and s25b["wh"] > s25["wh"] and s25b["h"] == f"#article/{aid}", s25b)
        # ⑤ 壞 id
        pg.locator(".artscene >> nth=3").scroll_into_view_if_needed()
        wait_until(pg, "() => [...document.querySelectorAll('.artscene')].slice(2).every(f => f.dataset.st === 'fail') ? 1 : 0", 20000, 300)
        sb = pg.evaluate("""() => [...document.querySelectorAll('.artscene')].slice(2).map(f => ({ st: f.dataset.st, txt: (f.querySelector('.asx') || {}).textContent || '',
            a: (f.querySelector('.asx a') || {}).getAttribute ? f.querySelector('.asx a').getAttribute('href') : null }))""")
        ok(f"{T}（{w}）：站內沒有的圖 → 一行「暫時載不出來」＋到站內頁面的連結（不是空白、不是黑方塊）",
           len(sb) == 2 and all(x["st"] == "fail" and "載不出來" in x["txt"] and x["a"] for x in sb) and sb[0]["a"] == "#industry/group/no_such_scene" and sb[1]["a"] == "#heatmap/theme/nope_theme", sb)
        fin = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth - innerWidth, end: !!document.getElementById('artEnd'), xss: !!window.__sceneXss })")
        ok(f"{T}（{w}）：壞 id 不壞頁（文末照常畫出、沒有執行注入）、沒有橫向捲軸", fin["end"] and not fin["xss"] and fin["sw"] <= 1, fin)
        # 換頁 → 3D 收掉（不留著吃 CPU）
        pg.evaluate("() => { location.hash = '#articles'; }")
        wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0 ? 1 : 0", 8000)
        ok(f"{T}（{w}）：離開文章 → 3D 檢視收掉（Rack3D.current 清空）", pg.evaluate("() => !window.Rack3D || !window.Rack3D.current"))
        c.close()

    # ⑦ 手機第一屏（#10）：公開舊文章逐篇開 390×844，第一個視覺區塊要在第一屏看得到；導讀收起、點了展開、記住
    for a in pub:
        c = b.new_context(viewport={"width": 390, "height": 844})
        c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.tour','done');if(!sessionStorage.getItem('x')){localStorage.removeItem('tw.art.hd');sessionStorage.setItem('x','1')}}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + f"#article/{a['id']}", wait_until="domcontentloaded")
        wait_until(pg, "() => document.querySelectorAll('#artBody > *').length > 2 ? 1 : 0", 15000)
        pg.wait_for_timeout(900)
        fs = pg.evaluate("""(sel) => { const B = document.getElementById('artBody'), ul = B.querySelector(':scope > ul');
            const all = [...B.querySelectorAll(':scope > *')], i0 = ul ? all.indexOf(ul) : -1;
            const v = all.slice(i0 + 1).find(e => e.matches(sel)) || all.find(e => e.matches(sel));
            const r = v && v.getBoundingClientRect(), hd = document.getElementById('artHd'), t = document.getElementById('artHdT');
            return { y: scrollY, top: r ? Math.round(r.top) : null, h: r ? Math.round(r.height) : 0, cls: v ? v.className : null, ih: innerHeight,
              hdOn: hd ? hd.classList.contains('on') : null, tVis: t ? t.getBoundingClientRect().height > 0 : false,
              bodyHidden: hd ? getComputedStyle(document.getElementById('artHdB')).display === 'none' : null,
              crumb: getComputedStyle(document.querySelector('.artcrumb')).display, sw: document.documentElement.scrollWidth - innerWidth }; }""", VISUAL_SEL)
        vis = fs["top"] is not None and fs["top"] < fs["ih"] and (fs["ih"] - fs["top"]) >= min(fs["h"], 90)
        ok(f"{T}（390 第一屏）：{a['id']} 第一個視覺區塊（{fs['cls']}）上緣在 {fs['top']}px，844 高的第一屏內看得到至少 90px；導讀預設收起、麵包屑收掉、沒有橫向捲軸",
           fs["y"] == 0 and vis and fs["hdOn"] is False and fs["tVis"] and fs["bodyHidden"] and fs["crumb"] == "none" and fs["sw"] <= 1, fs)
        if a is pub[0]:
            if shots:
                pg.screenshot(path=shots.replace(".png", "_390_first.png"))
            pg.click("#artHdT"); pg.wait_for_timeout(200)
            o = pg.evaluate("() => ({ on: document.getElementById('artHd').classList.contains('on'), ex: document.getElementById('artHdT').getAttribute('aria-expanded'), sub: (document.querySelector('#artHdB .artsub, #artHdB .artlead') || {getBoundingClientRect: () => ({height: 0})}).getBoundingClientRect().height, ls: localStorage.getItem('tw.art.hd') })")
            ok(f"{T}（390）：點「導讀・相關族群」→ 在原地展開副標／摘要，記住（tw.art.hd=1）", o["on"] and o["ex"] == "true" and o["sub"] > 0 and o["ls"] == "1", o)
            pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.getElementById('artHd') ? 1 : 0", 10000)
            ok(f"{T}（390）：重新整理 → 還是展開（使用者展開過的才記住）", pg.evaluate("() => document.getElementById('artHd').classList.contains('on')"))
        c.close()
    # 桌機不變：切換鈕不顯示、副標與摘要照舊攤開、麵包屑在
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.tour','done');localStorage.removeItem('tw.art.hd')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + f"#article/{pub[0]['id']}", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('artHd') ? 1 : 0", 15000); pg.wait_for_timeout(500)
    dk = pg.evaluate("() => ({ t: getComputedStyle(document.getElementById('artHdT')).display, b: getComputedStyle(document.getElementById('artHdB')).display, crumb: getComputedStyle(document.querySelector('.artcrumb')).display, lead: !!document.querySelector('#artHdB .artlead, #artHdB .artsub') })")
    ok(f"{T}（1440）：桌機不受影響 —— 導讀切換鈕不顯示、副標／族群／摘要照舊攤開、麵包屑在", dk["t"] == "none" and dk["b"] != "none" and dk["crumb"] != "none" and dk["lead"], dk)
    c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("文章3D區塊1019", lambda pg, b, base, code: t_art_scene_1019(b, base, code))
