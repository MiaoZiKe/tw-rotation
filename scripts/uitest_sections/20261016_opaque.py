# 驗收段落「手機點擊面板不透明1016」（scripts/uitest_sections 外掛段落）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 手機點擊面板不透明1016（Andy iPhone 淺色、資金流向「族群資金排行」點封測代工：
#   「這邊出現重疊現況，幫我確認是否其他點擊後的圖片也會這樣背景透明，幫我修正這問題」）
#   根因：mobile4.css 第 14 節把 .hpanel 一律 background:transparent!important；蓋在排行圖上的 #rankPanel（absolute inset:0）也是 .hpanel，
#   長條、族群名、軸名全部透上來。另外清單是格線、列高被算成 32px，每一檔的第二行（成交值・占比・漲跌）被下一檔蓋住。
#   這一段用手指真的點：排行長條、輪動時鐘的點 → #rankPanel；熱力圖方塊、剖析圖編號 → 底部抽屜；資金分流樹節點 → #sankeyPanel；
#   週期統計熱力格 → 圖表提示框。每一塊都量：
#     ① 面板（連同它到「跟圖共同祖先」之間每一層）合成的底色不透明度 ≥ 0.95
#     ② 圖上每一個文字（zrender 的 text）只要落在面板範圍內，那一點最上層一定是面板（＝圖的字不會跟面板的字疊在一起）
#     ③ 面板清單每一列的第二行不被下一列蓋住（列底 ≤ 下一列頂）
#   360／390／430 × 淺色／深色；⚠ --workers 1。
OP1016_JS = r"""() => {
  const X = window.__op1016 = {};
  const vis = e => { if (!e || !e.isConnected || !e.getClientRects().length) return false; const c = getComputedStyle(e); return c.visibility !== 'hidden' && c.display !== 'none' && +c.opacity > 0.05; };
  const al = c => { const m = /rgba?\(([^)]+)\)/.exec(c || ''); if (!m) return 0; const p = m[1].split(/[ ,\/]+/).filter(Boolean); return p.length >= 4 ? +p[3] : 1; };
  const own = e => { const c = getComputedStyle(e); let a = al(c.backgroundColor);
    const cols = (c.backgroundImage && c.backgroundImage !== 'none') ? (c.backgroundImage.match(/rgba?\([^)]+\)/g) || []) : [];
    if (cols.length) a = 1 - (1 - a) * cols.reduce((s, x) => s * (1 - al(x)), 1);
    return a * (+c.opacity); };
  X.alpha = (p, ch) => { let a = 0, e = p; while (e && e !== document.body && !(ch && e.contains(ch))) { a = 1 - (1 - a) * (1 - own(e)); e = e.parentElement; } return +a.toFixed(3); };
  /* 圖上所有文字（zrender text）在畫面上的矩形 */
  X.zrText = (ch) => { const c = window.echarts && echarts.getInstanceByDom(ch); if (!c) return []; const r = ch.getBoundingClientRect(); const L = [];
    c.getZr().storage.getDisplayList(true).forEach(el => { if (el.type !== 'text' && el.type !== 'tspan') return; if (el.invisible || el.ignore) return;
      const s = el.style || {}; if (!s.text || !String(s.text).trim()) return; let b; try { b = el.getBoundingRect().clone(); const t = el.getComputedTransform && el.getComputedTransform(); if (t) b.applyTransform(t); } catch (e) { return; }
      L.push({ t: String(s.text).slice(0, 14), l: r.left + b.x, t0: r.top + b.y, r: r.left + b.x + b.width, b: r.top + b.y + b.height }); });
    return L; };
  /* 面板蓋到圖的那一塊：面板範圍內的圖文字，中心點最上層是不是面板 */
  X.cover = (psel, chsel) => { const p = document.querySelector(psel), ch = document.querySelector(chsel); if (!vis(p)) return { open: false };
    const out = { open: true, alpha: X.alpha(p, ch), hidden: !vis(ch), leak: [], n: 0 };
    if (out.hidden) return out;
    const pr = p.getBoundingClientRect();
    p.scrollIntoView({ block: 'nearest', behavior: 'instant' });
    const pr2 = p.getBoundingClientRect();
    for (const z of X.zrText(ch)) { const cx = (z.l + z.r) / 2, cy = (z.t0 + z.b) / 2;
      if (cx < pr2.left || cx > pr2.right || cy < pr2.top || cy > pr2.bottom) continue;
      if (cy < 60 || cy > innerHeight - 4) continue;
      out.n++; const h = document.elementFromPoint(cx, cy); if (!(h && (h === p || p.contains(h)))) out.leak.push(z.t); }
    return out; };
  /* 面板清單每一列（含第二行）不被下一列蓋住 */
  X.rows = (psel) => { const rows = [...document.querySelectorAll(psel + ' div.ms > a')].filter(vis); const bad = [];
    rows.forEach((a, i) => { const nx = rows[i + 1]; const g = a.querySelector('.g'); if (!g) return; const gb = g.getBoundingClientRect(), ab = a.getBoundingClientRect();
      if (gb.bottom > ab.bottom + 1) bad.push([a.dataset.code, '第二行超出列', Math.round(gb.bottom - ab.bottom)]);
      if (nx && nx.getBoundingClientRect().top < gb.bottom - 1) bad.push([a.dataset.code, '被下一列蓋住']); });
    return { n: rows.length, bad: bad.slice(0, 5), h: rows.length ? Math.round(rows[0].getBoundingClientRect().height) : 0 }; };
  /* 排行長條／輪動時鐘點的中心（給手指點） */
  X.bar = (id, k) => { const el = document.getElementById(id); const c = echarts.getInstanceByDom(el); const d = c.getModel().getSeriesByIndex(0).getData();
    /* 從第 k 項往後找第一個「中心點在畫面內、而且手指點下去落在這張圖上」的（窄螢幕的熱力圖會左右滑，前幾格可能在畫面外） */
    const r = el.getBoundingClientRect();
    for (let j = Math.min(k, d.count() - 1); j < d.count(); j++) { const g = d.getItemGraphicEl(j); if (!g) continue; const b = g.getBoundingRect().clone(); const t = g.getComputedTransform && g.getComputedTransform(); if (t) b.applyTransform(t);
      if (!(b.width > 2 && b.height > 2)) continue; const x = r.left + b.x + b.width / 2, y = r.top + b.y + b.height / 2;
      if (x < 8 || x > innerWidth - 8 || y < 70 || y > innerHeight - 8) continue; const h = document.elementFromPoint(x, y); if (h && el.contains(h)) return [x, y]; }
    return null; };
  X.clockPt = () => { const el = document.getElementById('rotClock'); const c = echarts.getInstanceByDom(el); const r = el.getBoundingClientRect(); let best = null;
    c.getModel().eachSeries(s => { if (best) return; const d = s.getData(); for (let j = 0; j < d.count(); j++) { const row = (d.getRawDataItem(j) || {}).row; if (!row || row.isStock) continue;
      const g = d.getItemGraphicEl(j); if (!g) continue; const b = g.getBoundingRect().clone(); const t = g.getComputedTransform && g.getComputedTransform(); if (t) b.applyTransform(t);
      const x = r.left + b.x + b.width / 2, y = r.top + b.y + b.height / 2; if (x < r.left + 10 || x > r.right - 10 || y < 70 || y > innerHeight - 10) continue;
      const h = document.elementFromPoint(x, y); if (h && el.contains(h)) { best = [x, y, row.name]; return; } } });
    return best; };
  X.ft = (host) => { const h = document.getElementById(host); const P = h && window.FlowTopo && FlowTopo.probe(h); if (!P) return null; const cv = h._ft.cvLab; const r = cv.getBoundingClientRect();
    const n = P.nodes.filter(n => n.lv === 2).find(n => r.top + n.y > 130 && r.top + n.y < innerHeight - 130 && r.left + n.x > 20); return n ? [r.left + n.x + 3, r.top + n.y, n.name] : null; };
  X.tipAlpha = (chsel) => { /* 手機的提示框掛在 body 底下（appendToBody），不在圖的 DOM 裡 → 全頁找 */ const t = [...document.querySelectorAll('div')].find(d => /z-index: 9999999/.test(d.getAttribute('style') || '') && vis(d)); return t ? X.alpha(t, null) : null; };
  return true;
}"""


def t_m4_opaque_panel_1016(b, base):
    T = "手機點擊面板不透明1016"
    shots = os.environ.get("TW_OPAQUE1016_SHOTS")
    for theme in ("light", "dark"):
        for W, Hh in ((360, 780), (390, 844), (430, 932)):
            tag = f"【{T}】{theme} {W}"
            ctx = b.new_context(viewport={"width": W, "height": Hh}, is_mobile=True, has_touch=True, device_scale_factor=2, service_workers="block")
            ctx.add_init_script(f"try{{ localStorage.setItem('tw.theme','{theme}'); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.m4.3danim','0'); }}catch(e){{}}")
            m = ctx.new_page()
            m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
            m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            J = m.evaluate
            try:
                def go(h, ready):
                    m.goto(base + h, wait_until="domcontentloaded"); wait_until(m, ready, 20000, 200); m.wait_for_timeout(900); J(OP1016_JS)

                # ---- ① 族群資金排行：手指點長條 → #rankPanel 蓋住排行圖 ----
                go("#flow/rotation", "(() => { const e = document.getElementById('rankFlow'); return !!(e && window.echarts && echarts.getInstanceByDom(e) && e.getClientRects().length); })()")
                J("() => document.getElementById('rankFlow').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(500)
                xy = J("() => __op1016.bar('rankFlow', 3)")
                if ok(f"{tag} 排行圖有長條可以點", bool(xy), xy):
                    m.touchscreen.tap(xy[0], xy[1]); m.wait_for_timeout(1100)
                    cv = J("() => __op1016.cover('#rankPanel', '#rankFlow')")
                    ok(f"{tag} ① 點排行長條 → 成分股面板打開、底色不透明（{cv.get('alpha')} ≥ 0.95）", cv.get("open") and cv.get("alpha", 0) >= 0.95, cv)
                    ok(f"{tag} ① 面板範圍內的 {cv.get('n')} 個圖上文字（族群名／數字／軸名）一個都透不上來", cv.get("open") and (cv.get("hidden") or (cv.get("n", 0) >= 3 and not cv.get("leak"))), cv)
                    rw = J("() => __op1016.rows('#rankPanel')")
                    ok(f"{tag} ① 成分股 {rw['n']} 列、每列高 {rw['h']}px：第二行（成交值・占比・漲跌）不被下一列蓋住、可點高度 ≥ 44", rw["n"] >= 2 and not rw["bad"] and rw["h"] >= 44, rw)
                    if shots and W == 390:
                        m.screenshot(path=os.path.join(shots, f"opaque_rank_{theme}_{W}.png"))
                    # 返回鍵 → 面板收起、排行圖回來（面板不透明以後，返回要真的看得到圖）
                    J("() => document.querySelector('#rankPanel [data-all]').scrollIntoView({ block: 'center', behavior: 'instant' })")
                    bx = J("() => { const r = document.querySelector('#rankPanel [data-all]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                    m.touchscreen.tap(bx[0], bx[1]); m.wait_for_timeout(700)
                    ok(f"{tag} ① 按「‹ 全部族群」→ 面板收起", J("() => document.getElementById('rankPanel').hidden"))
                # ---- ② 輪動時鐘：手指點族群圓點 → 同一塊 #rankPanel ----
                J("() => document.getElementById('rotClock').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(500)
                pt = J("() => __op1016.clockPt()")
                if ok(f"{tag} 輪動時鐘上有族群圓點點得到", bool(pt), pt):
                    m.touchscreen.tap(pt[0], pt[1]); m.wait_for_timeout(1100)
                    cv = J("() => __op1016.cover('#rankPanel', '#rankFlow')")
                    ok(f"{tag} ② 點時鐘「{pt[2]}」→ 成分股面板打開、底色不透明（{cv.get('alpha')}）、圖上文字不透上來（{cv.get('n')} 個）",
                       cv.get("open") and cv.get("alpha", 0) >= 0.95 and not cv.get("leak"), cv)
                    m.keyboard.press("Escape"); m.wait_for_timeout(400)

                # ---- ②b 輪盤四角的象限鈕（改善／領先…）→ #stagePanel（同一格側欄，同樣蓋住排行圖） ----
                J("() => { const q = document.querySelector('.rotquads .rq'); if (q) q.scrollIntoView({ block: 'center', behavior: 'instant' }); }"); m.wait_for_timeout(400)
                qx = J("() => { const q = [...document.querySelectorAll('.rotquads .rq')].find(e => e.getClientRects().length); if (!q) return null; const r = q.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, q.textContent.trim()]; }")
                if ok(f"{tag} 輪盤有象限鈕", bool(qx), qx):
                    m.touchscreen.tap(qx[0], qx[1]); m.wait_for_timeout(1000)
                    cv = J("() => __op1016.cover('#stagePanel', '#rankFlow')")
                    ok(f"{tag} ②b 點象限鈕「{qx[2]}」→ 象限面板打開、底色不透明（{cv.get('alpha')}）、排行圖的字不透上來（{cv.get('n')} 個）",
                       cv.get("open") and cv.get("alpha", 0) >= 0.95 and not cv.get("leak"), cv)
                    m.keyboard.press("Escape"); m.wait_for_timeout(400)

                # ---- ③ 資金分流樹：手指點族群節點 → #sankeyPanel（排在樹下面；就算蓋到也要不透明） ----
                go("#flow/sankey", "(() => { const h = document.getElementById('sankey'); return !!(h && h._ft && window.FlowTopo && FlowTopo.probe(h)); })()")
                J("() => document.getElementById('sankey').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(500)
                n = J("() => __op1016.ft('sankey')")
                if ok(f"{tag} 資金分流樹有族群節點", bool(n), n):
                    m.touchscreen.tap(n[0], n[1]); m.wait_for_timeout(1100)
                    d = J("""() => { const p = document.getElementById('sankeyPanel'), s = document.querySelector('#sankey .ftstage') || document.getElementById('sankey');
                        if (!p || p.hidden || !p.getClientRects().length) return { open: false };
                        const a = p.getBoundingClientRect(), c = s.getBoundingClientRect(); const ov = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 2 && Math.min(a.right, c.right) - Math.max(a.left, c.left) > 2;
                        return { open: true, overlap: ov, alpha: __op1016.alpha(p, s) }; }""")
                    ok(f"{tag} ③ 點分流樹「{n[2]}」→ 成分股面板打開，不跟樹重疊（或重疊處底色 ≥ 0.95）", d.get("open") and (not d.get("overlap") or d.get("alpha", 0) >= 0.95), d)

                # ---- ④ 熱力圖方塊 → 底部抽屜 ----
                go("#heatmap/industry", "(() => { const e = document.getElementById('indTree'); return !!(e && window.echarts && echarts.getInstanceByDom(e)); })()")
                J("() => document.getElementById('indTree').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(500)
                xy = J("() => __op1016.bar('indTree', 1)")
                if ok(f"{tag} 熱力圖有方塊", bool(xy), xy):
                    m.touchscreen.tap(xy[0], xy[1]); m.wait_for_timeout(1100)
                    cv = J("() => __op1016.cover('#mSheet', '#indTree')")
                    ok(f"{tag} ④ 點熱力圖方塊 → 抽屜打開、底色不透明（{cv.get('alpha')}）、方塊上的字不透上來", cv.get("open") and cv.get("alpha", 0) >= 0.95 and not cv.get("leak"), cv)
                    m.keyboard.press("Escape"); m.wait_for_timeout(400)

                # ---- ⑤ 週期統計熱力格 → 圖表提示框（ECharts tooltip）底色 ----
                go("#season", "(() => { const e = document.getElementById('seasonHeat'); return !!(e && window.echarts && echarts.getInstanceByDom(e)); })()")
                J("() => document.getElementById('seasonHeat').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(500)
                xy = J("() => __op1016.bar('seasonHeat', 1)")
                if ok(f"{tag} 週期統計熱力圖有格子", bool(xy), xy):
                    m.touchscreen.tap(xy[0], xy[1]); m.wait_for_timeout(900)
                    ta = J("() => __op1016.tipAlpha('#seasonHeat')")
                    if ta is None:          # 有些寬度第一下只是「選中」、不出提示框 → 換一格再點一次
                        xy2 = J("() => __op1016.bar('seasonHeat', 25)")
                        if xy2:
                            m.touchscreen.tap(xy2[0], xy2[1]); m.wait_for_timeout(900); ta = J("() => __op1016.tipAlpha('#seasonHeat')")
                    # 沒有提示框＝沒有東西蓋在圖上（不算失敗）；有的話底色一定要 ≥ 0.95
                    ok(f"{tag} ⑤ 點週期統計格子 → 提示框底色 {ta}（沒有提示框＝沒東西蓋圖；有就要 ≥ 0.95）", ta is None or ta >= 0.95, ta)
            finally:
                ctx.close()


# ★ 2026-10-16 Andy iPhone：「這邊出現重疊現況…其他點擊後的圖片也會這樣背景透明」—— 點了才出現、蓋在圖上的面板一律不透明（樣式：site/m4/20261016e-opaque.css；360／390／430 × 淺／深；⚠ --workers 1）
register("手機點擊面板不透明1016", lambda pg, b, base, code: t_m4_opaque_panel_1016(b, base), after="手機彈窗點背景1016")
