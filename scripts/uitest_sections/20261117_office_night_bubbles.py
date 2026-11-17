# 驗收段落「辦公室夜晚不全黑＋泡泡不疊柱」（2026-11-17 擁有者截圖：凌晨整個場景近乎全黑、火災泡泡疊成一長條）
#   根因：夜晚（屋外 ×0.16）＋額度睡覺調暗（半球光下限 0.5）＋預算超額（畫布 brightness .6 再蓋 46% 深色遮罩）三層疊加。
#   ① 夜晚：場景（排除頂列與底部對話框）平均亮度 ≥ 門檻；夜晚＋睡覺調暗＋預算超額最壞疊加時仍 ≥ 較低門檻、而且不是接近全黑
#   ② 預算超額的遮罩規則（讀真正的樣式表）：brightness ≥ .8、遮罩不透明度 ≤ .2
#   ③ 火災：10 個同事同時著火求救／救火，逐幀檢查泡泡兩兩不重疊、每個角色最多一則、沒有一串垂直疊柱（任何垂直重疊鏈最多 3 則）、
#      每則泡泡實際停留 ≤ 3.2 秒（牆鐘；低幀率下遊戲時間變慢，原本會殘留數秒）
# 環境變數 NIGHT_SHOTS 指到資料夾時存截圖。
# flake8: noqa

import os as _os
import time as _time
from urllib.parse import urlparse as _up


def _nb_root(base):
    return base.rsplit("/", 1)[0]


def _nb_open(b, base, w=1280, h=800):
    c = b.new_context(viewport={"width": w, "height": h})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','night')}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.goto(_nb_root(base) + "/office/world.html?demo=1&q=low&pr=0.6", wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready", 150000)
    pg.wait_for_timeout(2500)
    return c, pg


def _nb_shot(pg, name):
    d = _os.environ.get("NIGHT_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


_NB_MEAN = """() => { const cv = document.getElementById('cv'); return null; }"""


def _nb_mean(pg, name):
    """螢幕截圖中間場景區（避開頂列與底部對話框）的平均亮度 0～255。"""
    from PIL import Image, ImageStat
    import io
    png = pg.screenshot(clip={"x": 170, "y": 190, "width": 940, "height": 400})
    im = Image.open(io.BytesIO(png)).convert("L")
    _nb_shot(pg, name)
    return ImageStat.Stat(im).mean[0]


def _nb_night(b, base):
    c, pg = _nb_open(b, base)
    try:
        st = pg.evaluate("() => ({ mode: __world.daytime.mode0(), t: __world.daytime.t })")
        ok("夜晚：時段是夜晚", st["mode"] == "night" or st["t"] >= 19 or st["t"] < 5, st)
        m1 = _nb_mean(pg, "night_plain.png")
        ok("夜晚：場景平均亮度 ≥ 120（看得清房間地板角色）", m1 >= 120, round(m1, 1))
        # 睡覺調暗（額度用完）
        pg.evaluate("() => { __world.power.dimTo(0.35, 0.01); __world.dim = 0.35; __world.daytime.applyDim(); }")
        pg.wait_for_timeout(800)
        inten = pg.evaluate("() => ({ h: __world.hemi.intensity, s: __world.sun.intensity })")
        ok("夜晚＋額度睡覺：半球光不低於 0.8", inten["h"] >= 0.8, inten)
        m2 = _nb_mean(pg, "night_sleep.png")
        ok("夜晚＋額度睡覺：場景平均亮度 ≥ 100", m2 >= 100, round(m2, 1))
        # 預算超額：套用「真正樣式表裡」的規則（讀 CSS，不是自己寫死的數字）
        rule = pg.evaluate("""() => {
          let f = null, bg = null;
          for (const ss of document.styleSheets) { let rs; try { rs = ss.cssRules; } catch (e) { continue; } for (const r of rs) { if (r.selectorText === 'body.budget-over #cv') f = r.style.filter; if (r.selectorText === '#budgetDim') bg = r.style.background || r.style.backgroundColor; } }
          return { f, bg };
        }""")
        ok("預算超額：樣式表有找到變暗規則", bool(rule["f"]) and bool(rule["bg"]), rule)
        import re as _re
        bm = _re.search(r"brightness\(([\d.]+)\)", rule["f"] or "")
        am = _re.search(r"rgba\([^)]*,\s*([\d.]+)\)", rule["bg"] or "")
        ok("預算超額：畫布亮度係數 ≥ 0.8", bm and float(bm.group(1)) >= 0.8, rule["f"])
        ok("預算超額：深色遮罩不透明度 ≤ 0.2", am and float(am.group(1)) <= 0.2, rule["bg"])
        pg.evaluate("(r) => { const s = document.createElement('style'); s.textContent = '#cv{filter:' + r.f + '!important}#budgetDim{opacity:1!important}'; document.head.append(s); }", rule)
        pg.wait_for_timeout(1000)
        m3 = _nb_mean(pg, "night_sleep_over.png")
        ok("夜晚＋睡覺＋預算超額（最壞疊加）：場景平均亮度 ≥ 85、不是接近全黑", m3 >= 85, round(m3, 1))
        ok("夜晚沒有頁面錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


_NB_FIRE = """() => {
  const W = __world; const cs = [...W.chars.values()].filter(c => !c.spec.pet).slice(0, 10);
  cs.forEach((c, i) => setTimeout(() => W.fire.ignite(c, 'campfire'), i * 400));
  window.__nb = { seen: new Map(), maxOver: 0, maxChain: 0, dup: 0, frames: 0 };
  const S = window.__nb, rect = e => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, e }; };
  const step = () => {
    const now = performance.now(); S.frames++;
    const vis = [...document.querySelectorAll('.bub')].filter(e => e.style.transform && !e.style.transform.includes('-999') && e.offsetWidth > 0).map(rect);
    for (let i = 0; i < vis.length; i++) for (let j = i + 1; j < vis.length; j++) { const a = vis[i], b = vis[j]; if (a.l < b.r - 0.5 && b.l < a.r - 0.5 && a.t < b.b - 0.5 && b.t < a.b - 0.5) S.maxOver++; }
    // 垂直疊柱：由下往上，彼此水平有重疊且上下相接的鏈
    const sorted = vis.slice().sort((p, q) => q.b - p.b); let chain = 0;
    for (const a of sorted) { let n = 1; for (const b of sorted) if (b !== a && b.b <= a.t + 12 && Math.abs((b.l + b.r) / 2 - (a.l + a.r) / 2) < (a.r - a.l + b.r - b.l) / 2 && a.t - b.b < 14) n++; chain = Math.max(chain, n); }
    S.maxChain = Math.max(S.maxChain, Math.min(chain, 99));
    for (const c of W.chars.values()) { const sp = c.speech; if (sp) { let r = S.seen.get(sp); if (!r) { r = { id: c.spec.id, t: sp.text, a: now, b: now }; S.seen.set(sp, r); } r.b = now; } }
    S.vis = vis.length; S.peak = Math.max(S.peak || 0, vis.length);
    if (!S.stop) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}"""


def _nb_bubbles(b, base):
    c, pg = _nb_open(b, base)
    try:
        pg.evaluate(_NB_FIRE)
        pg.wait_for_timeout(9000)
        _nb_shot(pg, "fire_bubbles.png")
        pg.wait_for_timeout(9000)
        r = pg.evaluate("() => { const S = window.__nb; S.stop = true; const life = [...S.seen.values()].map(x => [x.id, x.t, (x.b - x.a) / 1000]); life.sort((p, q) => q[2] - p[2]); return { over: S.maxOver, chain: S.maxChain, peak: S.peak, frames: S.frames, life: life.slice(0, 5), n: life.length }; }")
        ok("火災：有多人同時開口（泡泡尖峰 ≥ 5 則，驗得到擁擠情境）", r["peak"] >= 5, r)
        ok("火災：逐幀檢查泡泡兩兩不重疊（%d 幀 0 筆）" % r["frames"], r["over"] == 0, r["over"])
        ok("火災：沒有垂直疊成柱子（上下相接的連鎖最多 3 則）", r["chain"] <= 3, r["chain"])
        ok("火災：每則泡泡停留 ≤ 3.2 秒（%d 則）" % r["n"], all(x[2] <= 3.2 for x in r["life"]), r["life"])
        owners = pg.evaluate("() => { const m = new Map(); for (const c of __world.chars.values()) if (c.speech) m.set(c.spec.id, 1); const bs = [...document.querySelectorAll('.bub')].filter(e => e.style.transform && !e.style.transform.includes('-999') && e.offsetWidth > 0); return { speakers: m.size, shown: bs.length }; }")
        ok("同一角色同時最多一則（顯示的泡泡數 ≤ 正在說話的角色數）", owners["shown"] <= max(owners["speakers"], 0) + 0, owners)
        ok("泡泡沒有頁面錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _nb_all(pg, b, base, code):
    _nb_night(b, base)
    _nb_bubbles(b, base)


register("辦公室夜晚亮度與泡泡", _nb_all)
