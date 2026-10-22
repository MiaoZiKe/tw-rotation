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
