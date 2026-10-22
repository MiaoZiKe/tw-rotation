"""全片不准有任何模糊（Andy 2026-10-22）：錄影瀏覽器裡的「去模糊」與「逐幀模糊檢查」。

做法（只在錄影的瀏覽器，不改 site/）：
  ① 不再注入公司名稱／代號／股價的模糊 CSS（舊 BLUR_CSS 全部拿掉）；
  ② 網站自己的毛玻璃（backdrop-filter: blur）：全域 `backdrop-filter:none`，並掃描樣式表把任何 filter／backdrop-filter 含 blur 的規則（含 ::before／::after）一律改成 none；
  ③ 每一幀：掃 DOM，任何元素的 computed filter 或 backdrop-filter 還含 blur 就先改成 none，並記一筆「處理過」；處理後再量一次，仍含 blur 的記一筆「模糊」（報告要 0）。
     處理過的筆數也一併回報（誠實揭露網站本身有哪些毛玻璃被關掉）。
"""
INIT_JS = r"""
(() => {
  const css = '*,*::before,*::after{-webkit-backdrop-filter:none!important;backdrop-filter:none!important}';
  const BLUR = /blur/i;
  const go = () => {
    const st = document.createElement('style'); st.id = '__noblur'; let extra = '';
    const sels = new Set();
    for (const sh of [...document.styleSheets]) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
      const walk = (rs) => { for (const r of rs) { if (r.cssRules && !r.selectorText) { walk(r.cssRules); continue; } const s = r.style; if (!s) continue;
        const f = (s.filter || '') + ' ' + (s.getPropertyValue('backdrop-filter') || '') + ' ' + (s.getPropertyValue('-webkit-backdrop-filter') || '');
        if (BLUR.test(f) && r.selectorText) sels.add(r.selectorText); } };
      walk(rules); }
    window.__blurRules = [...sels];
    if (sels.size) extra = [...sels].join(',') + '{filter:none!important}';
    st.textContent = css + extra; (document.head || document.documentElement).appendChild(st);
  };
  window.__bfSweep = () => { let fixed = 0, left = 0; const seen = [];
    const ids = [...document.querySelectorAll('filter')].filter(f => f.querySelector('feGaussianBlur') || f.querySelector('feDropShadow')).map(f => f.id).filter(Boolean);
    const isBlur = (cs) => { const f = cs.filter || '', b = cs.backdropFilter || cs.webkitBackdropFilter || ''; return BLUR.test(f) || BLUR.test(b) || ids.some(id => f.indexOf('#' + id) >= 0); };
    for (const e of document.querySelectorAll('*')) { const cs = getComputedStyle(e);
      if (isBlur(cs)) { fixed++; if (seen.length < 4) seen.push((e.id ? '#' + e.id : e.tagName.toLowerCase()) + '.' + String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className).split(' ')[0]);
        e.style.setProperty('filter', 'none', 'important'); e.style.setProperty('backdrop-filter', 'none', 'important'); e.style.setProperty('-webkit-backdrop-filter', 'none', 'important'); } }
    for (const e of document.querySelectorAll('*')) { if (isBlur(getComputedStyle(e))) left++; }
    return { fixed, left, fe: ids.length, seen }; };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
"""


import math  # noqa: E402


def safe_path(rects, p0, p1, cell=6, W=1280, H=680):
    """格點最短路徑：游標矩形 (x-3,y-2,26,30) 不與任何外框相交；起點、終點即使在字上也放行。回傳拐點（已簡化）。"""
    import heapq
    gx, gy = W // cell, H // cell

    def blocked(cx, cy):
        x, y = cx * cell, cy * cell
        for (rx, ry, rw, rh) in rects:
            if x - 3 < rx + rw + 1 and x + 23 > rx - 1 and y - 2 < ry + rh + 1 and y + 28 > ry - 1:
                return True
        return False
    s = (int(p0[0] // cell), int(p0[1] // cell))
    g = (int(p1[0] // cell), int(p1[1] // cell))
    s = (max(0, min(gx - 1, s[0])), max(0, min(gy - 1, s[1])))
    g = (max(0, min(gx - 1, g[0])), max(0, min(gy - 1, g[1])))
    dist = {s: 0.0}
    prev = {}
    pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == g:
            break
        if d > dist.get(u, 1e18):
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy:
                    continue
                v = (u[0] + dx, u[1] + dy)
                if not (0 <= v[0] < gx and 0 <= v[1] < gy):
                    continue
                if v != g and max(abs(v[0] - s[0]), abs(v[1] - s[1])) > 3 and blocked(*v):   # 起點附近 3 格放行（游標本來就壓在字邊上時要能離開）
                    continue
                nd = d + math.hypot(dx, dy) + (0.0 if u == s else 0.0)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
    if g not in prev and g != s:
        return None
    pts = [g]
    while pts[-1] != s:
        pts.append(prev[pts[-1]])
    pts.reverse()
    pts = [(c[0] * cell, c[1] * cell) for c in pts]
    # 簡化：去掉共線點
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a_, b_, c_ = out[-1], pts[i], pts[i + 1]
        if (b_[0] - a_[0]) * (c_[1] - b_[1]) != (b_[1] - a_[1]) * (c_[0] - b_[0]):
            out.append(b_)
    out.append(pts[-1])
    return out[1:] and out
