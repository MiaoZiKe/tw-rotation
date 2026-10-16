# 驗收段落「手機彈窗點背景1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 手機彈窗點背景1016（Andy iPhone：「確實檢查所有開啟的小說明，點擊背景就會消失，確實明察功能是否正常」）
#   普查：13 頁 × 每一顆「?」、會開抽屜／下拉／選單的鈕、每頁前 3 張 ECharts 圖（點出提示框），用手指點開 → 手指點背景 → 量三件事：
#     ① 開出來的東西真的消失（含 ECharts 提示框）② 頁面捲得動、沒有全頁遮罩殘留 ③ 原本那顆鈕點得到（elementFromPoint 是它自己）。
#   「背景點」怎麼挑：畫面上一個非互動的點，而且它上下左右 22px 內也都沒有鈕／連結／圖表（摘要鈕的觸控區比外框大，貼著點會被當成按到它）；
#   刻意排除的不算背景：資金輪動的時間列／篩選列（DECISIONS：拖時間軸、按 ▶ 是「畫上去之後要做的事」，dismissable 的 ignore 名單裡就有）。
#   不算「開出來的東西」：輪動時鐘的掃描光束（div.ray）、象限鈕（.rq／.rg）、客服鈕（#supFab）—— 那是圖本身的動畫與常駐元件。
#   360／390／430 三種寬度；⚠ --workers 1（每頁都 reload，不共用狀態）。
#   ⚠ 網站開了 scroll-behavior:smooth：量測用的捲動一律 behavior:'instant'，不然 scrollBy 之後馬上讀到的是捲到一半的位置（第一版就這樣假紅）。
M4POP_PAGES = ["#overview", "#earnings", "#flow/rotation", "#heatmap/industry", "#industry", "#industry/semiconductor/dg/foundry",
               "#market", "#explore", "#etf/cal", "#season", "#watch", "#delivery", "#stock/2330"]
M4POP_JS = r"""() => {
  const vis = e => { if (!e || !e.isConnected || !e.getClientRects().length) return false; const c = getComputedStyle(e); return c.visibility !== 'hidden' && c.display !== 'none' && +c.opacity > 0.05; };
  const POP = '.howtxt, [role=dialog], [role=menu], [role=listbox], [role=tooltip], .msddpanel, .ddpanel, .pop, .menu, .tip, .panel, .segddp, [aria-modal]';
  const NOISE = '.ray, .rq, .rg, #supFab';
  const X = window.__m4pop = window.__m4pop || {};
  X.cand = () => {
    document.querySelectorAll('[data-m4pop]').forEach(e => e.removeAttribute('data-m4pop'));
    const S = '.howbtn[data-how], [aria-haspopup], .mfilt, .m4ctlrow button, .msdd > button, .segdd > button, #segDDBtn, .ddbtn, details > summary';
    const out = [], seen = new Set();
    document.querySelectorAll(S).forEach(e => { if (!vis(e) || e.closest('.msheet, #howPop, #m4Drawer, .topbar, header')) return;
      const k = (e.id || '') + '|' + (e.dataset.how || '') + '|' + e.className + '|' + e.textContent.trim().slice(0, 12); if (seen.has(k)) return; seen.add(k);
      X.keys = X.keys || {}; X.keys['b' + out.length] = k;
      e.dataset.m4pop = 'b' + out.length; out.push({ id: 'b' + out.length, txt: (e.textContent.trim().slice(0, 16) || e.getAttribute('aria-label') || e.id) }); });
    [...document.querySelectorAll('div[_echarts_instance_]')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 120 && r.height > 100 && e.offsetParent; }).slice(0, 3)
      .forEach((e, i) => { e.dataset.m4pop = 'c' + i; out.push({ id: 'c' + i, txt: '圖表 ' + (e.id || 'echarts'), chart: true }); });
    return out;
  };
  /* 「?」關掉時 howPop 會把說明盒搬回卡片、標題列可能整段重畫 → 原本那顆鈕被換成一顆新的（同一個樣子），用同一個簽名找回來 */
  X.find = (id) => { const b = document.querySelector('[data-m4pop="' + id + '"]'); if (b && b.isConnected && b.getClientRects().length) return b;
    const k = (X.keys || {})[id]; if (!k) return b;
    return [...document.querySelectorAll('.howbtn[data-how], [aria-haspopup], .mfilt, .m4ctlrow button, .msdd > button, .segdd > button, #segDDBtn, .ddbtn, details > summary')]
      .find(e => vis(e) && ((e.id || '') + '|' + (e.dataset.how || '') + '|' + e.className + '|' + e.textContent.trim().slice(0, 12)) === k) || b; };
  X.xy = (id) => { const b = X.find(id); if (!b) return null;
    const at = () => { const r = b.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2, h = document.elementFromPoint(x, y); return { x, y, ok: !!(h && (h === b || b.contains(h))) }; };
    b.scrollIntoView({ block: 'center', behavior: 'instant' }); let q = at();
    for (const dy of [-200, -200, 400]) { if (q.ok) break; scrollBy({ top: dy, behavior: 'instant' }); q = at(); }
    return q; };
  X.snap = () => { const L = []; document.querySelectorAll('body *').forEach(e => { const c = getComputedStyle(e);
    if ((c.position === 'fixed' || c.position === 'absolute' || e.matches(POP)) && vis(e)) L.push(e); }); X.old = new Set(L); };
  X.tips = () => [...document.querySelectorAll('div')].filter(d => /z-index: 9999999/.test(d.getAttribute('style') || '') && vis(d)).length;
  X.diff = () => { const N = []; document.querySelectorAll('body *').forEach(e => { const c = getComputedStyle(e);
      if ((c.position === 'fixed' || c.position === 'absolute' || e.matches(POP)) && vis(e) && !X.old.has(e) && !e.closest(NOISE)) { const r = e.getBoundingClientRect(); if (r.width > 40 && r.height > 30) N.push(e); } });
    ['howPop', 'mSheet'].forEach(id => { const e = document.getElementById(id); if (e && vis(e) && !N.includes(e) && !X.old.has(e)) N.push(e); });
    X.open = N.filter(e => !N.some(o => o !== e && o.contains(e)));
    return X.open.map(e => e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0]); };
  X.bg = () => { const H = innerHeight, W = innerWidth, open = X.open || [];
    const INT = 'a,button,input,select,textarea,label,summary,[role=tab],[role=button],canvas,svg,[_echarts_instance_],.howbtn,[onclick],.msheet,#howPop,#supFab,.topbar,nav,.m4ctlrow,#flowRotTime,#flowRotFilter,#rotLive,.rotquads,#stagePanel,.chip,.co,.segchip,#dgSec,#relSec,.chainmap';
    /* 背景點不准落在任何一顆會開東西的鈕附近（±24px）：
       ① 隔著「?」的半透明背景點在「?」本人正上方 → 背景關掉、緊接的 click 落到「?」又打開一次（那是使用者點了「?」，不是點背景）；
       ② 摘要鈕（.mfilt）的觸控區比外框大，貼著點會被當成按到它。 */
    /* ③ Chromium 手機模擬（跟 iOS 一樣）有「觸控校正」：手指落在鈕旁邊幾 px 的空白，會被吸到那顆鈕上（實測：輪動卡左邊 12px 的留白被吸到時間列的「−」）。
          所以任何可以按的東西（鈕、連結、tab、表單）±24px 內都不算背景。 */
    const AV = [...document.querySelectorAll('.howbtn, [aria-haspopup], .mfilt, .m4ctlrow, [data-m4pop], button, a[href], [role=button], [role=tab], input, select, label, summary')]
      .filter(e => vis(e) && !e.closest('#howBack, #mSheetBack') && !open.some(o => o.contains(e) && /back/i.test(o.id + o.className))).map(e => e.getBoundingClientRect())
      .filter(r => r.bottom > 0 && r.top < H && r.width < W * 0.95);
    const near = (x, y) => AV.some(r => x > r.left - 24 && x < r.right + 24 && y > r.top - 24 && y < r.bottom + 24);
    const hard = (x, y) => { const e = document.elementFromPoint(x, y); return !e || !!e.closest(INT) || open.some(o => o.contains(e) && !/back/i.test(o.id + o.className)); };
    const bad = (x, y) => near(x, y) || hard(x, y);
    for (let y = H * 0.18; y < H * 0.88; y += 19) for (let x = 14; x < W - 14; x += 23)
      if (!bad(x, y) && !bad(x - 22, y) && !bad(x + 22, y) && !bad(x, y - 22) && !bad(x, y + 22)) { const e = document.elementFromPoint(x, y); return [x, y, e.id || String(e.className).slice(0, 24)]; }
    // 整片都是圖／清單（例：430 輪動時鐘開著成分股清單）→ 鄰近範圍放寬到 10px 再找一次
    for (let y = H * 0.12; y < H * 0.92; y += 13) for (let x = 12; x < W - 12; x += 17)
      if (!bad(x, y) && !bad(x - 10, y) && !bad(x + 10, y) && !bad(x, y - 10) && !bad(x, y + 10)) { const e = document.elementFromPoint(x, y); return [x, y, e.id || String(e.className).slice(0, 24)]; }
    /* 還是沒有（整個畫面都是圖：輪動時鐘＋展開的成分股清單）→ 卡片標題列右端的空白（標題字右邊、「?」之外） */
    for (const h of document.querySelectorAll('.card > .row.spread, .card .rotchead, .card > h3, .card > h2')) {
      if (!vis(h)) continue; const r = h.getBoundingClientRect(); if (r.top < 60 || r.bottom > H - 20) continue;
      const x = r.right - 12, y = (r.top + r.bottom) / 2; /* 標題列本身就貼著圖，不套 ±24px（點的是標題列本人，不是圖）*/ if (!hard(x, y)) { const e = document.elementFromPoint(x, y); return [x, y, e.id || String(e.className).slice(0, 24)]; } }
    return null; };
  X.after = (id) => { const still = (X.open || []).filter(vis).map(e => e.id || String(e.className).split(' ')[0]);
    const cover = [...document.querySelectorAll('body *')].filter(e => { const c = getComputedStyle(e); if (c.position !== 'fixed' || !vis(e) || c.pointerEvents === 'none') return false;
      const r = e.getBoundingClientRect(); return r.width >= innerWidth * 0.9 && r.height >= innerHeight * 0.5; }).map(e => e.id || e.className);
    const q = id[0] === 'b' ? X.xy(id) : { ok: true };
    const sh = document.getElementById('mSheet');
    return { still, cover, hit: !!(q && q.ok), tips: X.tips(), sheetKind: sh && !sh.hidden ? sh.dataset.kind : null }; };
  return true;
}"""


def t_m4_pop_bg_1016(b, base):
    T = "手機彈窗點背景1016"
    table = []
    for W, H in ((360, 780), (390, 844), (430, 932)):
        ctx = b.new_context(viewport={"width": W, "height": H}, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('m4pop')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1');"
                            " localStorage.setItem('tw.m4.3danim','0'); sessionStorage.setItem('m4pop','1'); } }catch(e){}")
        m = ctx.new_page()
        m.on("pageerror", lambda e, W=W: fails.append(f"{T} {W} pageerror: {e}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = m.evaluate
        n_open = 0
        try:
            for pg in M4POP_PAGES:
                def load():
                    m.goto(base + pg, wait_until="domcontentloaded"); m.reload(wait_until="domcontentloaded")
                    m.wait_for_timeout(3000); J(M4POP_JS)
                load()
                cands = J("() => __m4pop.cand()")
                for c in cands[:18]:
                    if not J("() => location.hash").startswith(pg):
                        load(); J("() => __m4pop.cand()")
                    q = J("(i) => __m4pop.xy(i)", c["id"])
                    if not q or not q["ok"]:
                        continue
                    m.wait_for_timeout(300); q = J("(i) => __m4pop.xy(i)", c["id"])
                    if not q or not q["ok"]:
                        continue
                    J("() => __m4pop.snap()")
                    m.touchscreen.tap(q["x"], q["y"]); m.wait_for_timeout(800)
                    opened = J("() => __m4pop.diff()")
                    tip = J("() => __m4pop.tips()") if c.get("chart") else 0
                    if not opened and not tip:
                        continue
                    if not J("() => location.hash").startswith(pg):
                        continue                                  # 點圖＝換頁（例如點個股），不是彈窗
                    n_open += 1
                    pt = J("() => __m4pop.bg()")
                    if not pt:                                    # 這一屏全是圖與清單（產業鏈頁開著環節下拉）→ 捲回頁首，點頁首標題列的空白
                        J("() => scrollTo({ top: 0, behavior: 'instant' })"); m.wait_for_timeout(300); pt = J("() => __m4pop.bg()")
                    if not ok(f"【{T}】{W} {pg}「{c['txt']}」開出 {opened or ['提示框']}：畫面上找得到可以點的背景", bool(pt), opened):
                        J("() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"); continue
                    m.touchscreen.tap(pt[0], pt[1]); m.wait_for_timeout(800)
                    # 捲得動：往下捲；已經在頁底（往下不動）就改往上捲
                    y0 = J("scrollY"); J("scrollBy({ top: 120, behavior: 'instant' })"); m.wait_for_timeout(200); y1 = J("scrollY")
                    if y1 == y0:
                        J("scrollBy({ top: -120, behavior: 'instant' })"); m.wait_for_timeout(200); y1 = J("scrollY")
                    else:
                        J("scrollBy({ top: -120, behavior: 'instant' })")
                    short = J("document.documentElement.scrollHeight <= innerHeight + 2")
                    a = J("(i) => __m4pop.after(i)", c["id"])
                    good = not a["still"] and a["tips"] == 0 and not a["cover"] and a["hit"] and (y1 != y0 or short)
                    table.append((W, pg, c["txt"], "、".join(opened) or "提示框", "✓" if not a["still"] and a["tips"] == 0 else "✗",
                                  "✓" if (y1 != y0 or short) and not a["cover"] else "✗", "✓" if a["hit"] else "✗"))
                    ok(f"【{T}】{W} {pg}「{c['txt']}」開出 {opened or ['提示框']} → 手指點背景（{pt[2]}）：消失（殘留 {a['still']}、提示框 {a['tips']}）、"
                       f"捲得動（{y0}→{y1}）、沒有遮罩（{a['cover']}）、鈕點得到（{a['hit']}）", good, a)
                    if a["still"] or a["tips"]:
                        J("() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"); m.wait_for_timeout(300)
            ok(f"【{T}】{W} 普查真的點開過夠多個彈窗（{n_open} 個 ≥ 30）", n_open >= 30, n_open)
        finally:
            ctx.close()
    if os.environ.get("TW_M4POP_TABLE"):
        with open(os.environ["TW_M4POP_TABLE"], "w", encoding="utf-8") as f:
            f.write("| 寬 | 頁 | 鈕 | 開出 | 消失 | 捲得動無遮罩 | 鈕點得到 |\n|---|---|---|---|---|---|---|\n")
            for r in table:
                f.write("| " + " | ".join(str(x) for x in r) + " |\n")


# ★ 2026-10-16 Andy：「確實檢查所有開啟的小說明，點擊背景就會消失」—— 13 頁 × 每顆 ?／抽屜／下拉／圖表提示框（360／390／430 觸控；⚠ --workers 1）
register("手機彈窗點背景1016", lambda pg, b, base, code: t_m4_pop_bg_1016(b, base), after="手機3D分頁1016")
