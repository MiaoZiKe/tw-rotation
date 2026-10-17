# 驗收段落「管理區重疊普查1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_adm2_ctx… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 管理區重疊普查1017（Andy 10-17：「發現重疊 修正」「不只一處 其他地方也有，請檢查後修正」）
# 流量觀測（#admin/traffic，/preview/ 路徑走示範資料）在 1440／1100／800 三種寬，逐一點每個頂層分頁與子分頁：
#   ① 任兩段文字（不同元素、彼此不是父子）的字框交疊面積 > 4px² → 算一筆重疊
#   ② 文字超出它所在卡片（.card）的左右邊 → 算一筆溢出
#   ③ 把每個甜甜圈圖例的名稱換成 30 字長標題（真實文章、常見問題就有這麼長）再量一次 —— 長名稱必須換行，不准壓到數字或跑出卡片
ADM_OV_JS = r"""(long) => {
  const root = document.getElementById('admBody'); if (!root) return { err: 'no admBody' };
  if (long) root.querySelectorAll('ul.lg li span').forEach((s, i) => { if (!s.dataset.orig) s.dataset.orig = s.textContent; s.textContent = '要登入嗎？登入會拿到我的什麼資料？台積電9月營收5,119億元第三季創新高' + i; });
  const vis = (e) => { const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };
  const segs = [];
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: (n) => n.textContent.trim() ? 1 : 2 });
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    const el = n.parentElement; if (!el || !vis(el) || el.closest('svg,canvas,.dnc,[aria-hidden=true],.tip,[hidden]')) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    const cs = getComputedStyle(el), clip = /hidden|clip/.test(cs.overflowX) ? el.getBoundingClientRect() : null;   // 「…」截斷的字：被藏起來的部分不算
    for (const r0 of rg.getClientRects()) { const r = clip ? { left: Math.max(r0.left, clip.left), right: Math.min(r0.right, clip.right), top: Math.max(r0.top, clip.top), bottom: Math.min(r0.bottom, clip.bottom) } : r0; r.width = r.right - r.left; r.height = r.bottom - r.top;
      if (r.width > 1 && r.height > 1) segs.push({ el, r, t: n.textContent.trim().slice(0, 14) + '@' + (el.closest('[id]') || {}).id + '.' + String(el.className || el.tagName).slice(0, 12) }); }
  }
  const out = [], over = [];
  for (let i = 0; i < segs.length; i++) for (let j = i + 1; j < segs.length; j++) {
    const a = segs[i], b = segs[j]; if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (w > 2 && h > 2 && w * h > 4) out.push([a.t, b.t, Math.round(w * h)]);
  }
  for (const s of segs) { const c = s.el.closest('.card'); if (!c) continue; const cr = c.getBoundingClientRect();
    const sc = s.el.closest('.nbsw,[style*=overflow],.tbw'); if (sc && c.contains(sc) && getComputedStyle(sc).overflowX !== 'visible') continue;   // 橫向捲動列裡本來就會超出
    if (s.r.right > cr.right + 1 || s.r.left < cr.left - 1) over.push([s.t, Math.round(s.r.right - cr.right)]); }
  if (long) root.querySelectorAll('ul.lg li span[data-orig]').forEach((s) => { s.textContent = s.dataset.orig; delete s.dataset.orig; });
  return { n: segs.length, ov: out.slice(0, 12), nov: out.length, ex: over.slice(0, 12), nex: over.length };
}"""


def t_admin_overlap_1017(b, base, code):
    T = "管理區重疊普查1017"
    errs: list[str] = []
    pbase = base.replace("/index.html", "/preview/style-guide/index.html")
    for w in (1440, 1100, 800):
        c, sent = _adm2_ctx(b, width=w)
        c.route(re.compile(r".*/preview/style-guide/.*"), lambda r: r.continue_(url=r.request.url.replace("/preview/style-guide/", "/")))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(pbase + "#admin/traffic", wait_until="domcontentloaded")
        if not ok(f"{T}（{w}）：流量觀測打得開", bool(wait_until(pg, "() => !!document.getElementById('trTabs')", 15000))):
            c.close(); continue
        pg.wait_for_timeout(800)
        bad: list = []
        tabs = pg.evaluate("() => [...document.querySelectorAll('#trTabs button[data-t]')].map(b => b.dataset.t)")
        for t in tabs:
            pg.click(f"#trTabs button[data-t='{t}']"); pg.wait_for_timeout(500)
            subs = pg.evaluate("() => [...document.querySelectorAll('#trSubs button[data-sub]')].map(b => b.dataset.sub)") or ["-"]
            for s in subs:
                if s != "-":
                    pg.click(f"#trSubs button[data-sub='{s}']"); pg.wait_for_timeout(450)
                for lng in (False, True):
                    r = pg.evaluate(ADM_OV_JS, lng)
                    if r.get("nov") or r.get("nex"):
                        bad.append({"tab": t, "sub": s, "long": lng, "ov": r["ov"][:4], "ex": r["ex"][:4], "n": [r["nov"], r["nex"]]})
        ok(f"{T}（{w}）：{len(tabs)} 個分頁（含子分頁、長名稱）文字 0 重疊、0 超出卡片", not bad, bad[:6])
        if w == 1440:
            # Andy：「字不要全部塞下，顯示前面幾個字就好，不夠的游標移動過去再顯示」→ 長名稱一行「…」截斷；滑過那一列，提示裡是完整名稱
            pg.click("#trTabs button[data-t='all']"); pg.wait_for_timeout(500)
            LONG = "要登入嗎？登入會拿到我的什麼資料？台積電9月營收5,119億元第三季創新高"
            st = pg.evaluate("""(L) => { const s = document.querySelector('#trDonut ul.lg li span'); if (!s) return null; const li = s.closest('li');
                s.textContent = L; li.dataset.tip = '<b>' + L + '</b><br>測試'; const lh = parseFloat(getComputedStyle(s).lineHeight) || 18;
                return { cut: s.scrollWidth > s.clientWidth + 2, one: s.getBoundingClientRect().height < lh * 1.6, ell: getComputedStyle(s).textOverflow }; }""", LONG)
            ok(f"{T}：長名稱只顯示一行、尾巴「…」", bool(st) and st["cut"] and st["one"] and st["ell"] == "ellipsis", st)
            pg.hover("#trDonut ul.lg li >> nth=0"); pg.wait_for_timeout(500)
            tip = pg.evaluate("() => { const t = [...document.querySelectorAll('.tip, #tip, [role=tooltip]')].find(e => !e.hidden && /台積電9月營收/.test(e.textContent)); return t ? t.textContent : ''; }")
            ok(f"{T}：滑過那一列 → 提示顯示完整名稱", LONG in tip, tip[:80])
        shot = os.environ.get("TW_ADMOV_SHOT")
        if shot and w == 1440:
            pg.click("#trTabs button[data-t='support']") if pg.locator("#trTabs button[data-t='support']").count() else None
            pg.wait_for_timeout(500)
            pg.evaluate(ADM_OV_JS.replace("if (long) root.querySelectorAll('ul.lg li span[data-orig]')", "if (false) root.querySelectorAll('ul.lg li span[data-orig]')"), True)
            el = pg.locator("#trPageBody")
            el.screenshot(path=shot)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("管理區重疊普查1017", lambda pg, b, base, code: t_admin_overlap_1017(b, base, code))
