# 驗收段落「精選文章插圖1016」—— 2026-10-16 新增（拆檔防合併衝突：新段落一律放 scripts/uitest_sections/）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章插圖1016（site/artillus.js＋articles.js 的 illus 區塊）
# Andy 10-16 看著 CoWoS 文章的色塊長條剖面：「像是這種有提到特定元件，需要繪圖出來，更具像化，我指的就是這種圖要穿差一點」
#   ① CoWoS 文章：舊的 stack 長條不見了，換成 illus（kind=cowos）；8 個零件（GPU、HBM、微凸塊、矽中介層、C4、ABF 載板、錫球、主機板）都畫出來
#      ＋層別順序由上而下正確、凸塊大小「微凸塊 < C4 < 錫球」、HBM 看得到 8 層 DRAM＋TSV、中介層有 TSV 與重佈線
#   ② AI 伺服器文章：illus（kind=rack）7 個零件都畫出來（含拉出來的托盤、冷板、分歧管、電池極柱）
#   ③ 引線：每個零件一條，起點落在那個零件的實際範圍裡、終點接到對應編號；說明兩兩不重疊、不壓在圖上、編號由上而下
#   ④ 真的操作：滑過（電腦）／點（手機）說明 → 那個零件保持原樣、其他零件變淡、那條引線變色；離開／再點一次 → 恢復
#   ⑤ 390 手機：圖右邊一排編號＋圖下方編號清單、不超出畫面、沒有橫向捲軸、字 ≥ 12px
#   ⑥ 深色、淺色兩種主題都量（零件顏色真的換成另一組、說明字跟底色對比夠）；文章卡浮水印照舊
#   ⑦ 安全：parts 文字塞 HTML 不會執行；不認得的 kind 不畫
def t_art_illus_1016(b, base):
    T = "精選文章插圖1016"
    API = "https://uitest-art-illus.invalid"
    COWOS, RACK = "2026-10-14-know-cowos", "2026-10-14-intro-ai-server"
    C_PARTS = ["gpu", "hbm", "ubump", "interposer", "c4", "abf", "bga", "board"]
    R_PARTS = ["frame", "psu", "compute", "switch", "coldplate", "manifold", "bbu"]
    xss = {"id": "uitest-illus-xss", "cat": "know", "title": "插圖安全測試", "date": "2026-10-16", "tags": [], "summary": "", "reading_min": 1, "groups": [],
           "blocks": [{"t": "illus", "kind": "cowos", "title": "<img src=x onerror=window.__ilXss=1>", "parts": [{"id": "gpu", "label": "<img src=x onerror=window.__ilXss=1>晶片", "sub": "<b>粗</b>"},
                                                                                                         {"id": "\"><img src=x onerror=window.__ilXss=1>", "label": "壞 id"}]},
                      {"t": "illus", "kind": "<script>window.__ilXss=1</script>", "parts": []},
                      {"t": "illus", "kind": "toString", "parts": []}]}

    # 通用 custom（Andy 10-16 追加：「不只這些 是只要設備 都要繪製他的大致剖析圖」）：用資料描述一顆氣冷散熱模組＋一顆電池，
    # 驗「不用改程式、只寫 JSON 就畫得出來」；另外塞壞材質、壞 id、HTML 字串，確認被白名單擋掉
    CU_PARTS = ["fan", "fins", "pipe", "base", "chip", "board", "cell"]
    cust = {"id": "uitest-illus-custom", "cat": "know", "title": "通用剖析圖測試", "date": "2026-10-16", "tags": [], "summary": "", "reading_min": 1, "groups": [],
            "blocks": [{"t": "illus", "kind": "custom", "title": "氣冷散熱模組（測試）", "note": "示意", "view": [560, 330], "depth": [44, -26],
                        "shapes": [
                            {"part": "board", "type": "box", "x": 20, "y": 270, "w": 420, "h": 26, "mat": "pcb", "detail": "lines", "n": 2},
                            {"part": "chip", "type": "box", "x": 170, "y": 252, "w": 110, "h": 18, "mat": "chip", "detail": "grid"},
                            {"part": "base", "type": "box", "x": 150, "y": 234, "w": 150, "h": 18, "mat": "cu"},
                            {"part": "pipe", "type": "pipe", "mat": "cu", "r": 5, "points": [[180, 238], [180, 120], [200, 100]]},
                            {"part": "pipe", "type": "pipe", "mat": "cu", "r": 5, "points": [[270, 238], [270, 120], [290, 100]]},
                            {"part": "fins", "type": "box", "x": 140, "y": 90, "w": 180, "h": 120, "mat": "steel", "detail": "fins", "n": 18},
                            {"part": "fan", "type": "box", "x": 330, "y": 96, "w": 100, "h": 110, "mat": "plastic", "detail": "fan", "d": 0.5},
                            {"part": "cell", "type": "cyl", "x": 470, "y": 180, "w": 50, "h": 100, "mat": "battery", "detail": "terminals"},
                            {"part": "\"><img src=x onerror=window.__ilXss=1>", "type": "box", "x": 0, "y": 0, "w": 10, "h": 10},
                            {"part": "evil", "type": "<script>", "x": 0, "y": 0},
                            {"part": "fan", "type": "box", "x": 5, "y": 5, "w": 4, "h": 4, "mat": "\"><img src=x onerror=window.__ilXss=1>"}],
                        "parts": [{"id": "fan", "label": "風扇", "sub": "扇框＋扇葉＋輪轂，把風吹過鰭片"}, {"id": "fins", "label": "散熱鰭片", "sub": "一片片薄鋁片，加大散熱面積"},
                                  {"id": "pipe", "label": "熱管", "sub": "把熱從底座帶到鰭片"}, {"id": "base", "label": "銅底座", "sub": "貼在晶片上吸熱"},
                                  {"id": "chip", "label": "晶片", "sub": "熱的來源"}, {"id": "board", "label": "主機板", "sub": "承載晶片"},
                                  {"id": "cell", "label": "電池", "sub": "上面有極柱"}, {"id": "ghost", "label": "圖上沒有的部件", "sub": "要被略過"}]}]}

    def prep(ctx, theme):
        ctx.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": API}) + ";"
                            "try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme'," + json.dumps(theme) + ")}catch(e){}")
        ctx.route(API + "/**", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"views":{}}'))
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctx.route("**/articles/posts/uitest-illus-custom.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(cust, ensure_ascii=False)))
        ctx.route("**/articles/posts/uitest-illus-xss.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(xss, ensure_ascii=False)))

    MEAS = """() => { const F = document.querySelector('#artBody .artillus'); if (!F) return null;
      const R = (e) => e.getBoundingClientRect(), W = F.querySelector('.ilw'), svg = F.querySelector('svg.ilsvg'), WR = R(W);
      const hit = (a, b) => !(a.right <= b.left + 0.5 || b.right <= a.left + 0.5 || a.bottom <= b.top + 0.5 || b.bottom <= a.top + 0.5);
      const cmp = W.classList.contains('cmp');
      const tags = cmp ? [...F.querySelectorAll('.ilbs em')] : [...F.querySelectorAll('.ill li')];
      const ids = [...new Set([...svg.querySelectorAll('[data-part]')].map(g => g.dataset.part))];
      const box = (id) => { const gs = [...svg.querySelectorAll('[data-part="' + id + '"]')].map(R).filter(r => r.width > 0 && r.height > 0); if (!gs.length) return null;
        return { left: Math.min(...gs.map(r => r.left)), right: Math.max(...gs.map(r => r.right)), top: Math.min(...gs.map(r => r.top)), bottom: Math.max(...gs.map(r => r.bottom)) }; };
      const parts = {}; ids.forEach(id => { const b = box(id); if (b) parts[id] = { ...b, cy: (b.top + b.bottom) / 2 }; });
      const rad = (id) => { const cs = [...svg.querySelectorAll('[data-part="' + id + '"] circle')].map(c => R(c).width); return cs.length ? cs.reduce((s, x) => s + x, 0) / cs.length : 0; };
      const lines = [...F.querySelectorAll('svg.illn g')].map(g => { const p = g.querySelector('path'), c = g.querySelector('circle'), d = p.getAttribute('d');
        const nums = d.match(/-?[0-9.]+/g).map(Number); const ex = nums[nums.length - 2] + WR.left, ey = nums[nums.length - 1] + WR.top;
        const ax = +c.getAttribute('cx') + WR.left, ay = +c.getAttribute('cy') + WR.top;
        const tag = tags.find(t => t.dataset.part === g.dataset.part); const em = tag ? R(tag.matches('em') ? tag : tag.querySelector('em')) : null;
        const pb = parts[g.dataset.part];
        // 起點落在零件範圍裡：同時確認那一點真的打在該零件上（elementFromPoint 往下找第一個 data-part）
        let onPart = false; if (pb) { const els = document.elementsFromPoint(ax, ay); const hitPart = els.map(e => e.closest && e.closest('svg.ilsvg [data-part]')).find(Boolean); onPart = !!hitPart && hitPart.dataset.part === g.dataset.part; }
        return { id: g.dataset.part, ax, ay, ex, ey, inBox: !!pb && ax >= pb.left - 1 && ax <= pb.right + 1 && ay >= pb.top - 1 && ay <= pb.bottom + 1, onPart,
          toTag: !!em && Math.abs(ex - (em.left - 3)) <= 2 && ey >= em.top - 1 && ey <= em.bottom + 1 }; });
      const lis = [...F.querySelectorAll('.ill li')], SR = R(svg);
      const labHit = (els) => { let n = 0; for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) if (hit(R(els[i]), R(els[j]))) n++; return n; };
      const txt = [...F.querySelectorAll('.ill li b, .ill li span, .ilbs em, .ill li em')].filter(e => R(e).width > 0);
      const fs = txt.map(e => parseFloat(getComputedStyle(e).fontSize));
      const fr = R(F);
      const s0 = svg.querySelector('[data-part] .f, [data-part] .bezel');
      return { kind: F.dataset.kind, cmp, ids, parts, n: tags.length, tagIds: tags.map(t => t.dataset.part), lines, nLines: +F.dataset.lines,
        labHit: labHit(lis), tagHit: labHit(tags), labOnSvg: cmp ? lis.filter(l => hit(R(l), SR)).length : lis.filter(l => R(l).left < SR.right - 1).length,
        tagOrder: tags.map(t => R(t).top), minFs: Math.min(...fs), rad: { ub: rad('ubump'), c4: rad('c4'), bga: rad('bga') },
        dram: svg.querySelectorAll('[data-part="hbm"] .dram1, [data-part="hbm"] .dram2').length, tsv: svg.querySelectorAll('[data-part="interposer"] rect.cu').length,
        figR: fr.right, figL: fr.left, vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, oldStack: document.querySelectorAll('#artBody .artstack').length,
        fill: s0 ? getComputedStyle(s0).fill : '', labC: lis.length ? getComputedStyle(lis[0].querySelector('b')).color : '', figBg: getComputedStyle(F).backgroundColor,
        theme: document.documentElement.getAttribute('data-theme') || 'dark',
        wm: getComputedStyle(document.getElementById('artPost'), '::after').backgroundImage !== 'none' };
    }"""

    def lum(c):
        import re as _re
        v = [float(x) / 255 for x in _re.findall(r"[\d.]+", c)[:3]]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

    def contrast(a, b2):
        la, lb = lum(a), lum(b2)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    fills = {}
    for theme in ("dark", "light"):
        for w in (1440, 390):
            mob = w < 640
            ctx = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, device_scale_factor=1 if not mob else 2, is_mobile=mob, has_touch=mob)
            prep(ctx, theme)
            pg = ctx.new_page()
            for aid, kind, want in ((COWOS, "cowos", C_PARTS), (RACK, "rack", R_PARTS), ("uitest-illus-custom", "custom", CU_PARTS)):
                tag = f"{theme}/{w}/{kind}"
                pg.goto(base + "#article/" + aid, wait_until="domcontentloaded")
                ok_ = wait_until(pg, "() => { const f = document.querySelector('#artBody .artillus'); return f && +f.dataset.lines > 0; }", 20000)
                pg.wait_for_timeout(500)
                pg.evaluate("() => document.querySelector('#artBody .artillus').scrollIntoView({block: 'center', behavior: 'instant'})"); pg.wait_for_timeout(400)
                m = pg.evaluate(MEAS)
                if not ok_ or not m:
                    ok(f"{T}[{tag}]：插圖有畫出來", False, m); continue
                ok(f"{T}[{tag}]：插圖畫出來（kind={kind}）、{len(want)} 個零件都在圖上且有大小、說明 {len(want)} 條、引線 {len(want)} 條",
                   m["kind"] == kind and all(p in m["parts"] for p in want) and m["n"] == len(want) and m["nLines"] == len(want) and len(m["lines"]) == len(want), {k: m[k] for k in ("kind", "ids", "n", "nLines")})
                if kind == "cowos":
                    ok(f"{T}[{tag}]：舊的色塊長條（stack）不見了", m["oldStack"] == 0, m["oldStack"])
                    P = m["parts"]
                    order = ["ubump", "interposer", "c4", "abf", "bga", "board"]
                    ok(f"{T}[{tag}]：層別由上而下：晶片／HBM → 微凸塊 → 矽中介層 → C4 → ABF 載板 → 錫球 → 主機板（各層中心 y 遞增）",
                       max(P["gpu"]["cy"], P["hbm"]["cy"]) < P["ubump"]["cy"] and all(P[order[i]]["cy"] < P[order[i + 1]]["cy"] for i in range(len(order) - 1)), {k: round(P[k]["cy"]) for k in C_PARTS})
                    ok(f"{T}[{tag}]：凸塊大小 微凸塊 {m['rad']['ub']:.1f} < C4 {m['rad']['c4']:.1f} < 錫球 {m['rad']['bga']:.1f}（px 直徑）",
                       0 < m["rad"]["ub"] < m["rad"]["c4"] < m["rad"]["bga"], m["rad"])
                    ok(f"{T}[{tag}]：HBM 看得到多層 DRAM（4 疊 × 8 層＝{m['dram']}）、中介層有 TSV／重佈線銅線（{m['tsv']} 條）",
                       m["dram"] == 32 and m["tsv"] >= 30, [m["dram"], m["tsv"]])
                bad = [l for l in m["lines"] if not (l["inBox"] and l["onPart"] and l["toTag"])]
                ok(f"{T}[{tag}]：每條引線起點打在自己那個零件上（elementFromPoint 確認）、終點接到同一個零件的編號", not bad, bad)
                ok(f"{T}[{tag}]：說明編號由上而下排（跟圖上層的順序一致）、編號兩兩不重疊、說明兩兩不重疊、說明不壓在圖上",
                   m["tagOrder"] == sorted(m["tagOrder"]) and m["tagHit"] == 0 and m["labHit"] == 0 and m["labOnSvg"] == 0, {k: m[k] for k in ("tagOrder", "tagHit", "labHit", "labOnSvg")})
                ok(f"{T}[{tag}]：字 ≥ 12px（最小 {m['minFs']}）、插圖卡不超出畫面（{m['figL']:.0f}～{m['figR']:.0f} / {m['vw']}）、沒有橫向捲軸",
                   m["minFs"] >= 12 and m["figL"] >= 0 and m["figR"] <= m["vw"] + 0.5 and m["sw"] <= 0, m)
                ok(f"{T}[{tag}]：{'手機改成圖右側編號＋圖下清單' if mob else '電腦版說明在圖右側'}（cmp={m['cmp']}）", m["cmp"] == mob, m["cmp"])
                ok(f"{T}[{tag}]：說明字跟卡片底色對比 ≥ 4.5（{contrast(m['labC'], m['figBg']):.1f}）、主題＝{theme}、文章卡浮水印還在",
                   contrast(m["labC"], m["figBg"]) >= 4.5 and m["theme"] == theme and m["wm"], [m["labC"], m["figBg"], m["theme"], m["wm"]])
                fills[(theme, kind)] = m["fill"]
                # 真的操作：滑過／點第 3 條說明 → 該零件不透明、其他零件變淡、該引線換色；再操作一次 → 恢復
                pid = m["tagIds"][2]
                sel = f"#artBody .artillus {'.ilbs em' if mob else '.ill li'}[data-part='{pid}']"
                ST = """(pid) => { const F = document.querySelector('#artBody .artillus'); const op = (e) => +getComputedStyle(e).opacity;
                    const gs = [...F.querySelectorAll('svg.ilsvg [data-part]')]; const me = gs.filter(g => g.dataset.part === pid), ot = gs.filter(g => g.dataset.part !== pid);
                    const ln = F.querySelector('svg.illn g[data-part="' + pid + '"] path');
                    return { me: Math.min(...me.map(op)), ot: Math.max(...ot.map(op)), stroke: getComputedStyle(ln).stroke, hi: F.dataset.hi || '' }; }"""
                s0 = pg.evaluate(ST, pid)
                if mob:
                    pg.locator(sel).tap()
                else:
                    pg.locator(sel).hover()
                pg.wait_for_timeout(350)
                s1 = pg.evaluate(ST, pid)
                ok(f"{T}[{tag}]：{'點' if mob else '滑過'}「{pid}」→ 那個零件不透明、其他零件變淡（{s0['ot']} → {s1['ot']}）、那條引線換色",
                   s0["ot"] == 1 and s1["me"] == 1 and s1["ot"] <= 0.5 and s1["stroke"] != s0["stroke"] and s1["hi"] == pid, [s0, s1])
                if mob:
                    pg.locator(sel).tap()
                else:
                    pg.mouse.move(2, 2)
                pg.wait_for_timeout(350)
                s2 = pg.evaluate(ST, pid)
                ok(f"{T}[{tag}]：{'再點一次' if mob else '滑開'} → 恢復原樣", s2["ot"] == 1 and s2["me"] == 1 and s2["hi"] == "", s2)
                # 改寬度 → 引線跟著重畫、仍然對到（ResizeObserver）
                if not mob:
                    pg.set_viewport_size({"width": 1100, "height": 900}); pg.wait_for_timeout(600)
                    m2 = pg.evaluate(MEAS)
                    bad2 = [l for l in m2["lines"] if not (l["inBox"] and l["toTag"])]
                    ok(f"{T}[{tag}]：視窗 1440 → 1100，引線跟著重畫、仍然每條對到零件與編號、說明不重疊", not bad2 and m2["labHit"] == 0 and m2["nLines"] == len(want), [bad2, m2["labHit"]])
                    pg.set_viewport_size({"width": 1440, "height": 900}); pg.wait_for_timeout(400)
                shots = os.environ.get("TW_ART_ILLUS_SHOTS")
                if shots:
                    Path(shots).mkdir(parents=True, exist_ok=True)
                    pg.locator("#artBody .artillus").screenshot(path=str(Path(shots) / f"{kind}-{theme}-{w}.png"))
                if kind == "custom":
                    cx = pg.evaluate("""() => ({ xss: !!window.__ilXss, imgs: document.querySelectorAll('#artBody img').length,
                        fins: document.querySelectorAll('#artBody svg.ilsvg [data-part="fins"] .fin').length, blades: document.querySelectorAll('#artBody svg.ilsvg [data-part="fan"] .blade').length,
                        hub: document.querySelectorAll('#artBody svg.ilsvg [data-part="fan"] .hub').length, term: document.querySelectorAll('#artBody svg.ilsvg [data-part="cell"] .term').length,
                        pipes: document.querySelectorAll('#artBody svg.ilsvg [data-part="pipe"] path.tube').length, ghost: document.querySelectorAll('#artBody .ill li[data-part="ghost"]').length,
                        badMat: document.querySelectorAll('#artBody svg.ilsvg [class*="img"]').length })""")
                    ok(f"{T}[{tag}]：通用 custom 只靠 JSON 就畫出散熱模組（鰭片 {cx['fins']} 條線、扇葉 {cx['blades']} 片＋輪轂、2 根熱管、電池極柱）；圖上沒有的部件不列、壞 id／壞材質／壞形狀被擋、HTML 不執行",
                       cx["fins"] >= 30 and cx["blades"] == 5 and cx["hub"] == 1 and cx["term"] == 1 and cx["pipes"] == 2 and cx["ghost"] == 0 and cx["badMat"] == 0 and not cx["xss"] and cx["imgs"] == 0, cx)
            if theme == "dark" and w == 1440:
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(base + "#article/uitest-illus-xss", wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.querySelector('#artPost .artttl')", 15000); pg.wait_for_timeout(800)
                x = pg.evaluate("""() => ({ xss: !!window.__ilXss, figs: document.querySelectorAll('#artBody .artillus').length, imgs: document.querySelectorAll('#artBody img').length,
                    lbl: [...document.querySelectorAll('#artBody .ill li b')].map(b => b.textContent), n: document.querySelectorAll('#artBody .ill li').length })""")
                ok(f"{T}：parts 文字塞 HTML 不執行、不認得的 kind（含 toString 這種原型名）不畫、壞 id 被略過、沒有頁面錯誤",
                   not x["xss"] and x["figs"] == 1 and x["imgs"] == 0 and x["n"] == 1 and x["lbl"][0].startswith("<img") and not errs, [x, errs])
            ctx.close()
    ok(f"{T}：深色與淺色的零件顏色真的換了一組（cowos {fills.get(('dark', 'cowos'))} → {fills.get(('light', 'cowos'))}）",
       fills.get(("dark", "cowos")) and fills.get(("dark", "cowos")) != fills.get(("light", "cowos")) and fills.get(("dark", "rack")) != fills.get(("light", "rack")), fills)


register("精選文章插圖1016", lambda pg, b, base, code: t_art_illus_1016(b, base), after="精選文章1014")
