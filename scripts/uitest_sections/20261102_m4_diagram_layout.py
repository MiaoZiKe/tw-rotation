# 驗收段落「手機剖析圖上下編號1102」—— 2026-11-02（Andy：「編號不能點擊 無法看圖片…你需將 2D 3D 圖片放大，
# 而他們的編號需要改到一條線引導到上下兩邊 這樣才有足夠空間看圖」）。
# 由 _uitest.py 用 exec 載入（ok()、wait_until()、fails、os 直接可用）。不要在這裡寫三引號模組說明。
# flake8: noqa
#
# 逐張量（全部 2D 與 3D）：
#   · 圖寬 ≥ 圖框內寬 95%（2D 量 .dgcanvas svg；3D 量 canvas）
#   · 編號泡泡全部在圖的上方或下方（泡泡中心不在圖的左右、也不在圖的範圍內）
#   · 泡泡兩兩不重疊（中心距 ≥ 30）
#   · 引線端點（零件上的圓點）落在圖框內
#   · touchscreen.tap 每一顆泡泡：抽屜開、標題的編號＝該泡泡；點圖框外背景關
#   · 點零件本身（2D）同樣開抽屜
#   · 3D：自轉時泡泡位置穩定（兩次取樣泡泡中心差 ≤ 2px），引線端點隨零件投影移動
#   · 大圖：⤢ 鈕開全螢幕、＋ 倍率變大、點背景關、✕ 關
#   360／390／430 三種寬度。環境變數 TW_DGL_ALL=1 跑全部圖，預設每寬度挑 4 張（含 AI 伺服器機櫃）。
HOST = {'2d': '#prodDiagram', '3d': '#prod3d'}
DGL_ST = r"""() => { const s = document.getElementById('mSheet'), k = document.getElementById('mSheetBack');
  const vis = e => !!(e && !e.hidden && e.getClientRects().length && getComputedStyle(e).display !== 'none');
  const h = s && s.querySelector('.mshhead .no, .mshhead b');
  return { sheet: vis(s), scrim: vis(k), no: s && s.dataset ? (s.dataset.no || '') : '', title: s ? (s.querySelector('.mshhead') || {}).textContent || '' : '' }; }"""
DGL_MEASURE = r"""(mode) => {
  const host = document.querySelector(mode === '3d' ? '#prod3d' : '#prodDiagram');
  if (!host) return { err: 'nohost' };
  const fr = host.getBoundingClientRect();
  const fig = mode === '3d' ? host.querySelector('canvas') : (host.querySelector('.dgcanvas svg') || host.querySelector('svg.dg'));
  if (!fig) return { err: 'nofig' };
  const f = fig.getBoundingClientRect();
  const cs = getComputedStyle(host);
  const innerW = fr.width - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const nums = [...host.querySelectorAll('.mnumlayer .mnum')].filter(b => b.style.display !== 'none').map(b => { const r = b.getBoundingClientRect();
    return { i: +b.dataset.i, no: b.dataset.no, cx: r.left + r.width / 2, cy: r.top + r.height / 2, w: r.width, h: r.height, side: b.dataset.side || '' }; });
  const leads = [...host.querySelectorAll('.mnumlayer svg circle')].map(c => { const r = c.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
  const ly = host.querySelector('.mnumlayer');
  return { fr: [fr.left, fr.top, fr.right, fr.bottom], fig: [f.left, f.top, f.right, f.bottom], figW: f.width, innerW, nums, leads, overlap: ly ? ly.dataset.overlap : null, gen: ly ? (ly.dataset.gen || '0') : null, rows: ly ? ly.dataset.rows : null,
    sx: document.documentElement.scrollWidth, vw: innerWidth }; }"""


def t_m4_dglayout_1102(b, base):
    T = "手機剖析圖上下編號1102"
    SHOT = os.environ.get("TW_DGL_SHOT")
    ALL = os.environ.get("TW_DGL_ALL")
    WS = [int(x) for x in os.environ.get("TW_DGL_W", "360,390,430").split(",")]
    RNG = os.environ.get("TW_DGL_RANGE")
    ONLY = [x for x in os.environ.get("TW_DGL_ONLY", "").split(",") if x]
    for W, H in [x for x in ((360, 780), (390, 844), (430, 932)) if x[0] in WS]:
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2 if SHOT else 1, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('dgl')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1');"
                            " localStorage.setItem('tw.m4.3danim','1'); sessionStorage.setItem('dgl','1'); } }catch(e){}")
        if os.environ.get("TW_DGL_TRACE"):
            ctx.add_init_script("""(() => { window.__tr = []; const L = (t) => document.addEventListener(t, e => { const el = e.target; const b = el && el.closest ? el.closest('.mnum') : null;
              window.__tr.push([Math.round(performance.now()), t, b ? 'mnum' + b.dataset.no : (el && (el.tagName + '.' + (el.className && el.className.baseVal === undefined ? el.className : '')).slice(0, 30)), Math.round(e.clientX || (e.changedTouches && e.changedTouches[0].clientX) || 0), Math.round(e.clientY || (e.changedTouches && e.changedTouches[0].clientY) || 0)]); if (window.__tr.length > 80) window.__tr.shift(); }, true);
              ['pointerdown', 'pointerup', 'click'].forEach(L); })();""")
        m = ctx.new_page()
        m.on("pageerror", lambda e, W=W: fails.append(f"{T} {W} pageerror: {e}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = m.evaluate

        def xy(sel):
            return J("(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }", sel)

        def goto(chain, dg):
            m.goto(base + f"#industry/{chain}/dg/{dg}", wait_until="domcontentloaded")
            wait_until(m, "() => { const g = document.querySelector('#dg3d'); return !!(g && g.getClientRects().length); }", 40000, 300)
            m.wait_for_timeout(600)
            if J("() => { const h = document.querySelector('#prodDiagram'); return !!(h && h.hidden); }"):
                J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })"); m.wait_for_timeout(300)
                p = xy("#dg3d button[data-dm='2d']")
                if p: m.touchscreen.tap(*p); m.wait_for_timeout(800)
            wait_until(m, "() => !!document.querySelector('#prodDiagram .mnumlayer .mnum')", 40000, 300)
            m.wait_for_timeout(1600)

        def to3d():
            J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })"); m.wait_for_timeout(300)
            if J("() => document.querySelector('#prod3d').hidden"):
                p = xy("#dg3d button[data-dm='3d']")
                if p: m.touchscreen.tap(*p)
            got = wait_until(m, "() => { const h = document.querySelector('#prod3d'); return !!(h && !h.hidden && h.querySelector('.mnumlayer .mnum')); }", 40000, 300)
            m.wait_for_timeout(1800)
            return got

        def tap_center(sel_fn_js):
            p = J(sel_fn_js)
            if p: m.touchscreen.tap(*p); m.wait_for_timeout(700)
            return p

        def check_layout(mode, tag):
            wait_until(m, "() => !!document.querySelector('" + HOST[mode] + " .mnumlayer .mnum')", 15000, 300)
            m.wait_for_timeout(500)
            r = J(DGL_MEASURE, mode)
            for _ in range(20):                 # 第一次載入（冷快取）編號層可能還在排：最多再等 6 秒，真的沒有才算壞
                if r.get("err") or r["nums"]: break
                m.wait_for_timeout(300); r = J(DGL_MEASURE, mode)
            if r.get("err"):
                ok(f"【{T}】{W} {tag} {mode} 量得到圖（{r['err']}）", False, r); return None
            n = len(r["nums"])
            dbg = J("(h) => { const e = document.querySelector(h); const L = e && e.querySelector('.mnumlayer'); return { cls: e && e.className, layer: !!L, btn: L ? L.querySelectorAll('.mnum').length : -1, html: L ? L.innerHTML.length : -1, ds: L ? Object.assign({}, L.dataset) : null, hidden: e && e.hidden, hash: location.hash }; }", HOST[mode]) if n == 0 else None
            ok(f"【{T}】{W} {tag} {mode} 圖寬 {r['figW']:.0f} ≥ 框內寬 {r['innerW']:.0f} 的 95%", n > 0 and r["figW"] >= r["innerW"] * 0.95 - 0.5, [r["figW"], dbg])
            fy0, fy1 = r["fig"][1], r["fig"][3]
            side = [q for q in r["nums"] if not (q["cy"] < fy0 - 4 or q["cy"] > fy1 + 4)]
            ok(f"【{T}】{W} {tag} {mode} {n} 顆編號全在圖的上方或下方（{len(side)} 顆落在圖範圍內）", n > 0 and not side, [q["no"] for q in side])
            ok(f"【{T}】{W} {tag} {mode} 編號全在畫面左右邊界內（不被切）", all(q["cx"] - q["w"] / 2 >= -0.5 and q["cx"] + q["w"] / 2 <= r["vw"] + 0.5 for q in r["nums"]), r["vw"])
            def pairs(r):
                out = []
                for a in range(len(r["nums"])):
                    for c in range(a + 1, len(r["nums"])):
                        d = ((r["nums"][a]["cx"] - r["nums"][c]["cx"]) ** 2 + (r["nums"][a]["cy"] - r["nums"][c]["cy"]) ** 2) ** 0.5
                        if d < 30: out.append((r["nums"][a]["no"], r["nums"][c]["no"], round(d, 1)))
                return out
            if pairs(r):                       # 重排時泡泡用 .35 秒滑位，滑完再量一次
                m.wait_for_timeout(800); r = J(DGL_MEASURE, mode)
            bad = pairs(r)
            for a in range(0):
                for c in range(a + 1, n):
                    d = ((r["nums"][a]["cx"] - r["nums"][c]["cx"]) ** 2 + (r["nums"][a]["cy"] - r["nums"][c]["cy"]) ** 2) ** 0.5
                    if d < 30: bad.append((r["nums"][a]["no"], r["nums"][c]["no"], round(d, 1)))
            ok(f"【{T}】{W} {tag} {mode} 泡泡兩兩不重疊（{bad[:3]}）", not bad, bad)
            ok(f"【{T}】{W} {tag} {mode} 泡泡 ≥ 30px 見方（觸控範圍）", all(q["w"] >= 29.5 and q["h"] >= 29.5 for q in r["nums"]), r["nums"][:1])
            lead_out = [l for l in r["leads"] if not (r["fr"][0] - 2 <= l[0] <= r["fr"][2] + 2 and r["fig"][1] - 2 <= l[1] <= r["fig"][3] + 2)]
            ok(f"【{T}】{W} {tag} {mode} 引線端點（{len(r['leads'])} 個）都落在圖範圍內（{len(lead_out)} 個在外）", len(lead_out) <= (0 if mode == '2d' else max(1, n // 6)), lead_out[:3])
            ok(f"【{T}】{W} {tag} {mode} 頁面不橫捲（{r['sx']} / {r['vw']}）", r["sx"] <= r["vw"] + 1, r)
            return r

        def tap_all(r, mode, tag, limit=99):
            k = 0
            for q in sorted(r["nums"], key=lambda q: q["no"])[:limit]:
                # 泡泡可能在可視範圍外：捲到中間再點，之後重新量位置
                J("([h, i]) => { const b = document.querySelector(h + ' .mnumlayer .mnum[data-i=\"' + i + '\"]'); if (b) b.scrollIntoView({ block: 'center', behavior: 'instant' }); }", [HOST[mode], q["i"]])
                m.wait_for_timeout(250)
                for attempt in range(3):
                    # 量位置、確認「這個點上最上面的就是這顆」、記下重排世代：同一次 evaluate 做完（中間不會有別的事插進來）
                    pr = J("""([h, i]) => { const L = document.querySelector(h + ' .mnumlayer'); const b = L && L.querySelector('.mnum[data-i="' + i + '"]'); if (!b) return null;
                      const r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, t = document.elementFromPoint(x, y);
                      return { p: [x, y], top: t && t.closest('.mnum') ? t.closest('.mnum').dataset.no : (t ? t.tagName : null), gen: L.dataset.gen || '0' }; }""", [HOST[mode], q["i"]])
                    if not pr: break
                    p, topno, gen0 = pr["p"], pr["top"], pr["gen"]
                    m.touchscreen.tap(*p); m.wait_for_timeout(500)
                    s = J(DGL_ST); s['top'] = topno; s['p'] = [round(p[0]), round(p[1])]
                    gen1 = J("(h) => { const L = document.querySelector(h + ' .mnumlayer'); return L ? (L.dataset.gen || '0') : null; }", HOST[mode])
                    good = s["sheet"] and s["no"] == q["no"] and q["no"] in s["title"]
                    if good or gen1 == gen0: break
                    # 失敗且「量位置到放開」之間剛好發生一次重排（世代變了）→ 這一下點的是別顆，重量再點；其餘失敗一律算失敗
                    globals().get('notes', []).append(f"{T} {W} {tag} {mode} 編號 {q['no']}：量位置後剛好重排（世代 {gen0}→{gen1}），重點第 {attempt + 2} 次")
                    J("() => { const k = document.getElementById('mSheetBack'); if (k && !k.hidden) k.click(); }"); m.wait_for_timeout(450)
                if not pr: ok(f"【{T}】{W} {tag} {mode} 編號 {q['no']} 找得到", False); continue
                if not good: ok(f"【{T}】{W} {tag} {mode} 點編號 {q['no']} 開抽屜且標題對應（{s}）", False, s)
                else: k += 1
                # 關掉：點抽屜上方背景
                J("() => { const k = document.getElementById('mSheetBack'); if (k && !k.hidden) k.click(); }"); m.wait_for_timeout(450)   # 抽屜背景在頂欄／子分頁上方時，用手指點會點到分頁而換頁，所以關抽屜走背景的 click
            ok(f"【{T}】{W} {tag} {mode} 用手指點每一顆編號：{k}/{min(limit, len(r['nums']))} 顆都開了對應抽屜", k == min(limit, len(r['nums'])), k)

        try:
            m.goto(base + "#industry/semiconductor/dg/foundry", wait_until="domcontentloaded"); wait_until(m, "() => !!(window.DiagramSlots && window.Diagrams && Object.keys(window.Diagrams).length > 5)", 40000, 300)
            # 剖析圖分檔晚到：清單要等「連續 4 次取樣張數不變」才算齊（冷快取只量到 7 張就開跑，會漏驗 25 張）
            _last, _same = -1, 0
            for _ in range(60):
                _c = J("() => Object.keys(window.Diagrams || {}).length")
                _same = _same + 1 if _c == _last else 0
                _last = _c
                if _same >= 4: break
                m.wait_for_timeout(500)
            ids = J("() => Object.keys(window.Diagrams || {}).map(id => [window.DiagramSlots.chainOf(id), id, window.DiagramSlots.level(id)]).filter(x => x[0])")
            PART = os.environ.get("TW_DGL_PART")
            if PART: k0, kn = [int(x) for x in PART.split("/")]; ids = [x for i, x in enumerate(ids) if i % kn == k0]
            if RNG: a0, a1 = [int(x) for x in RNG.split(":")]; ids = ids[a0:a1]
            pick = ids if ALL else [x for x in ids if x[1] in (ONLY or ("foundry", "adv_pkg", "ai_server", "hbm"))][:4]
            ok(f"【{T}】{W} 找得到剖析圖清單（{len(ids)} 張，驗 {len(pick)} 張）", (len(ids) >= 10 or PART or RNG) and len(pick) >= (1 if RNG else 3), [x[1] for x in pick])
            for chain, dg, lv in pick:
                tag = dg
                J("() => window.DG && DG.closeView && DG.closeView()")
                goto(chain, dg)
                r2 = check_layout("2d", tag)
                if r2 is None: continue
                if SHOT: J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start' })"); m.wait_for_timeout(300); m.screenshot(path=os.path.join(SHOT, f"dglayout_{dg}_2d_{W}.png"))
                tap_all(r2, "2d", tag, limit=(99 if W == 390 else 4))
                # 點零件本身（2D）→ 抽屜
                # 零件是 <g>：它的外接盒中心常落在「空的地方」（例如 psu_ups 的細長虛線框、中間是空白），點那裡本來就不會點到零件。
                # 所以點「外接盒內真的命中該零件的點」（取離中心最近的一個）；整個盒子都找不到命中點的零件才算驗不到。
                HIT = """(k) => { const h = document.querySelector('#prodDiagram'); const e = h.querySelector('[data-part="' + k + '"]'); if (!e) return null;
                  e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2; let best = null;
                  for (let i = 0; i <= 8; i++) for (let j = 0; j <= 8; j++) { const x = r.left + r.width * (i + .5) / 9, y = r.top + r.height * (j + .5) / 9;
                    if (x < 2 || x > innerWidth - 2 || y < 70 || y > innerHeight - 90) continue;
                    const t = document.elementFromPoint(x, y); const g = t && t.closest && t.closest('[data-part]'); if (!g || g.dataset.part !== k) continue;
                    const d = Math.hypot(x - cx, y - cy); if (!best || d < best[2]) best = [x, y, d]; }
                  return best ? [best[0], best[1]] : null; }"""
                keys = J("""() => { const h = document.querySelector('#prodDiagram'); const keys = new Set(((h._mctx && h._mctx.items) || []).map(i => i.part).filter(Boolean));
                  return [...h.querySelectorAll('[data-part]')].filter(e => keys.has(e.dataset.part) && getComputedStyle(e).pointerEvents !== 'none' && !/^card:/.test(e.dataset.part) && e.getClientRects().length && e.getBoundingClientRect().width > 8).map(e => e.dataset.part); }""")
                p = None
                for k in dict.fromkeys(keys):
                    xy_ = J(HIT, k)
                    if xy_: m.wait_for_timeout(250); xy_ = J(HIT, k)
                    if xy_: p = [xy_[0], xy_[1], k]; break
                ok(f"【{T}】{W} {tag} 2d 找得到一個點得到的零件（候選 {len(keys)} 個）", bool(p) or not keys, keys[:5])
                if p:
                    m.wait_for_timeout(100)
                    h0 = J("() => location.hash"); m.touchscreen.tap(p[0], p[1]); m.wait_for_timeout(600)
                    if J("() => location.hash") != h0:          # 這個零件是「連到別頁」的連結（環節連結）：換頁不是抽屜，回來繼續
                        goto(chain, dg)
                    s = J(DGL_ST)
                    ok(f"【{T}】{W} {tag} 2d 點零件本身也開抽屜（{s['no']} {s['title'][:12]}）", s["sheet"], s)
                    J("() => { const k = document.getElementById('mSheetBack'); if (k && !k.hidden) k.click(); }"); m.wait_for_timeout(450)
                # 大圖：⤢ → 開、＋ 變大、點背景關
                J("() => document.querySelector('#dgSec').scrollIntoView({ block: 'start', behavior: 'instant' })"); m.wait_for_timeout(300)
                p = xy("#dgTools .mdvbtn")
                if ok(f"【{T}】{W} {tag} 2d 有 ⤢ 看大圖鈕", bool(p)):
                    m.touchscreen.tap(*p); m.wait_for_timeout(500)
                    v = J("() => { const o = document.getElementById('mDgView'); if (!o) return null; const s = o.querySelector('svg'); return { w: s.getBoundingClientRect().width, z: o.dataset.zoom }; }")
                    ok(f"【{T}】{W} {tag} 2d 點 ⤢ 開全螢幕大圖（{v}）", bool(v) and v["w"] > 100, v)
                    if v:
                        m.touchscreen.tap(*xy("#mDgView [data-z='1']")); m.wait_for_timeout(300)
                        v2 = J("() => ({ w: document.querySelector('#mDgView svg').getBoundingClientRect().width, z: document.getElementById('mDgView').dataset.zoom })")
                        ok(f"【{T}】{W} {tag} 2d 按 ＋ 圖變寬（{v['w']:.0f} → {v2['w']:.0f}）", v2["w"] > v["w"] * 1.3, [v, v2])
                        m.touchscreen.tap(*xy("#mDgView .mdv-x")); m.wait_for_timeout(300)
                        ok(f"【{T}】{W} {tag} 2d 按 ✕ 關大圖", J("() => !document.getElementById('mDgView')"))
                        m.touchscreen.tap(*xy("#dgTools .mdvbtn")); m.wait_for_timeout(400)
                        # 點圖外暗處（標題列下方、圖左緣外面不一定有空；縮回 100% 後圖下方有暗處）
                        bg = J("() => { const body = document.querySelector('#mDgView .mdv-body').getBoundingClientRect(); return [body.left + 4, body.top + body.height / 2]; }")
                        m.touchscreen.tap(*bg); m.wait_for_timeout(300)
                        ok(f"【{T}】{W} {tag} 2d 點背景關大圖", J("() => !document.getElementById('mDgView')"))
                # 3D（沒有 3D 場景的圖跳過）
                if not J("(k) => !!window.DiagramSlots.scene(k)", dg): continue
                if not ok(f"【{T}】{W} {tag} 切到 3D 有編號", to3d()): continue
                r3 = check_layout("3d", tag)
                if r3 is None: continue
                if SHOT: m.screenshot(path=os.path.join(SHOT, f"dglayout_{dg}_3d_{W}.png"))
                tap_all(r3, "3d", tag, limit=(99 if W == 390 else 4))
                # 按住一顆泡泡 4.5 秒（自轉一直在動、超過重排間隔）：泡泡不准被重排或滑走，放開後開的是按下的那一顆
                hq = sorted(r3["nums"], key=lambda q: q["no"])[len(r3["nums"]) // 2]
                J('''([h, i]) => { const b = document.querySelector(h + ' .mnumlayer .mnum[data-i="' + i + '"]'); if (b) b.scrollIntoView({ block: 'center', behavior: 'instant' }); }''', [HOST['3d'], hq["i"]]); m.wait_for_timeout(300)
                HP = '''([h, i]) => { const L = document.querySelector(h + ' .mnumlayer'); const b = L.querySelector('.mnum[data-i="' + i + '"]'); const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, gen: L.dataset.gen || '0', top: (document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2).closest('.mnum') || {dataset: {}}).dataset.no }; }'''
                h00 = J(HP, [HOST['3d'], hq["i"]])
                m.mouse.move(h00["x"], h00["y"]); m.mouse.down(); m.wait_for_timeout(150)
                h0 = J(HP, [HOST['3d'], hq["i"]])        # 按下之後才記基準（按下前到按下瞬間之間發生的重排不算「按著時重排」）
                m.wait_for_timeout(4350)
                h1 = J(HP, [HOST['3d'], hq["i"]])
                m.mouse.up(); m.wait_for_timeout(600)
                sh = J(DGL_ST)
                ok(f"【{T}】{W} {tag} 3d 按住編號 {hq['no']} 4.5 秒：位置不動（{abs(h1['x']-h0['x'])+abs(h1['y']-h0['y']):.1f}px）、沒重排（世代 {h0['gen']}→{h1['gen']}）、放開後開的是它（{sh['no']}）",
                   abs(h1["x"] - h0["x"]) + abs(h1["y"] - h0["y"]) < 1 and h0["gen"] == h1["gen"] and h0["top"] == hq["no"] and sh["sheet"] and sh["no"] == hq["no"], [h0, h1, sh])
                J("() => { const k = document.getElementById('mSheetBack'); if (k && !k.hidden) k.click(); }"); m.wait_for_timeout(450)
                # 自轉中泡泡位置穩定、引線端點跟著零件走
                a = J(DGL_MEASURE, "3d"); m.wait_for_timeout(1400); c = J(DGL_MEASURE, "3d")
                if a.get("gen") != c.get("gen"):        # 這 1.4 秒剛好整排重排過一次（泡泡本來就會整批換位）→ 換一段沒重排的來比
                    a = c; m.wait_for_timeout(1400); c = J(DGL_MEASURE, "3d")
                if "nums" not in a or "nums" not in c: ok(f"【{T}】{W} {tag} 3d 自轉取樣量得到", False, [a, c]); continue
                by = {q["no"]: q for q in c["nums"]}
                drift = max([abs((q["cx"] - a["fr"][0]) - (by[q["no"]]["cx"] - c["fr"][0])) + abs((q["cy"] - a["fr"][1]) - (by[q["no"]]["cy"] - c["fr"][1])) for q in a["nums"] if q["no"] in by] or [0])   # 相對畫布量，頁面自己捲動不算
                moved = sum(1 for p0, p1 in zip(a["leads"], c["leads"]) if abs(p0[0] - p1[0]) + abs(p0[1] - p1[1]) > 0.5)
                ok(f"【{T}】{W} {tag} 3d 自轉 1.4 秒：泡泡最大位移 {drift:.1f}px（沒重排時必須 ≤ 2，泡泡不准自己飄）、引線端點有 {moved} 個跟著零件動", (drift <= 2 if a.get("gen") == c.get("gen") else drift <= 40), [drift, moved])
                # 切回 2D，下一張
                p = xy("#dg3d button[data-dm='2d']")
                if p: m.touchscreen.tap(*p); m.wait_for_timeout(500)
            # 延伸閱讀抽屜裡的圖：點圖開大圖
            goto(*[(x[0], x[1]) for x in pick][0])
            p = J("() => { const b = document.querySelector('.mdgfolds .mdgfold, .mdgfolds button, .mdgfolds summary'); if (!b) return null; b.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
            if p:
                m.wait_for_timeout(250); p = J("() => { const b = document.querySelector('.mdgfolds .mdgfold, .mdgfolds button, .mdgfolds summary'); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                m.touchscreen.tap(*p); m.wait_for_timeout(900)
                q = J("() => { const e = document.querySelector('#mSheet .mdvtap'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, Math.max(r.top, 0) + 60]; }")
                if ok(f"【{T}】{W} 延伸閱讀抽屜裡的圖可點", bool(q)):
                    m.touchscreen.tap(*q); m.wait_for_timeout(500)
                    ok(f"【{T}】{W} 點延伸閱讀的圖開全螢幕大圖", J("() => !!document.getElementById('mDgView')"))
                    bg = J("() => { const body = document.querySelector('#mDgView .mdv-body').getBoundingClientRect(); return [body.left + 4, body.top + body.height / 2]; }")
                    m.touchscreen.tap(*bg); m.wait_for_timeout(300)
                    ok(f"【{T}】{W} 點背景關延伸閱讀大圖", J("() => !document.getElementById('mDgView')"))
        finally:
            ctx.close()
    # 桌機守：1440 沒有上下排、沒有 ⤢、圖框沒有 --mnTop
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    try:
        pg.goto(base + "#industry/semiconductor/dg/foundry", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.querySelector('#prodDiagram svg')", 40000, 300)
        pg.wait_for_timeout(1200)
        u = pg.evaluate("() => ({ rows: !!document.querySelector('.mrows'), btn: !!document.querySelector('.mdvbtn'), view: !!document.getElementById('mDgView'), pad: getComputedStyle(document.querySelector('#prodDiagram')).paddingTop })")
        ok(f"【{T}】1440 桌機沒有上下排編號、沒有 ⤢ 鈕（{u}）", not u["rows"] and not u["btn"] and not u["view"], u)
    finally:
        pg.close()


register("手機剖析圖上下編號1102", lambda pg, b, base, code: t_m4_dglayout_1102(b, base), after="手機3D分頁1016")
