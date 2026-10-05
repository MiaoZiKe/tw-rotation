/* ============================================================================
   共用月曆格小模組（2026-10-06，Andy：「週末就反灰色、國定假日標上日曆」「ETF 日曆也優化」）
   財報日曆（earnings.js）與 ETF 配息行事曆（etfpage.js）共用，不各寫一套：
     · 週六日格反灰（.cg-we）、台股休市日格底色＋小字「國慶日・休市」（.cg-hol／.cg-hl）
     · 一屏的格高自適應 fit()
   休市日資料：site/tw_holidays.json（由 scripts/gen_holidays.py 從 pipeline/calendar/tw_holidays.yaml 產生，來源與查證日寫在 YAML）。
   ========================================================================== */
(function () {
  'use strict';
  const S = { days: {}, p: null, verified: '' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  function injectCSS() {
    if (document.getElementById('calgridCss')) return;
    const s = document.createElement('style'); s.id = 'calgridCss';
    s.textContent = `
.cg-we:not(.today):not(.out):not(.sel){background:color-mix(in srgb,var(--ink) 14%,var(--panel))!important;color:var(--ink-3)!important}
.cg-we:not(.out) .dn b{color:var(--ink-3)!important}
.cg-hol:not(.today):not(.out):not(.sel){background:color-mix(in srgb,var(--amber) 13%,var(--panel-2))!important}
.cg-hl{display:block;font-size:12px;line-height:16px;color:var(--amber);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}`;
    document.head.appendChild(s);
  }
  function load() {
    injectCSS();
    if (S.p) return S.p;
    S.p = fetch('tw_holidays.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).then((j) => {
      S.days = (j && j.days) || {}; S.verified = (j && j.verified) || ''; return S.days;
    }).catch(() => S.days);
    return S.p;
  }
  const isWeekend = (k) => { const g = new Date(k + 'T00:00:00Z').getUTCDay(); return g === 0 || g === 6; };
  const holiday = (k) => S.days[k] || null;
  /* 加在格子 class 上的字串（含前導空白） */
  const cls = (k) => (isWeekend(k) ? ' cg-we' : '') + (holiday(k) ? ' cg-hol' : '');
  /* 格內小字「國慶日・休市」；非休市日回空字串 */
  const tag = (k) => { const h = holiday(k); return h ? `<span class="cg-hl" title="${esc(h)}・台股休市（證交所公告；${esc(S.verified)}）">${esc(h)}・休市</span>` : ''; };
  /* 一屏格高：格高＝（視窗剩下的高度 − 星期列 − 間距）÷ 列數，夾在 min～max；回傳格高 */
  function fit(grid, rows, min, max, gap, extra) {
    const top = grid.getBoundingClientRect().top + window.scrollY;
    const avail = window.innerHeight - top - 26 - (extra || 0);
    return Math.max(min, Math.min(max, Math.floor((avail - 20 - rows * gap) / rows)));
  }
  /* 小圖（純 SVG、不放文字）：直條＋折線，淡格線；兩頁面板共用 */
  const W = 250, H = 84, nz = (v) => v != null && isFinite(v);
  function bars(vals, o) {
    o = o || {}; const v = vals.filter(nz); if (!v.length) return '';
    const lo = o.base0 ? Math.min(0, ...v) : 0, hi = Math.max(0, ...v), span = (hi - lo) || 1, n = vals.length, bw = W / n;
    const y = (x) => H - 4 - ((x - lo) / span) * (H - 8), y0 = y(0);
    return vals.map((x, i) => (!nz(x) ? '' : `<rect x="${(i * bw + bw * .18).toFixed(1)}" y="${Math.min(y(x), y0).toFixed(1)}" width="${(bw * .64).toFixed(1)}" height="${Math.max(1, Math.abs(y(x) - y0)).toFixed(1)}" rx="1.5" fill="${o.color ? o.color(x, i) : 'var(--cat-1)'}"><title>${esc(o.tip ? o.tip(i) : x)}</title></rect>`)).join('');
  }
  function line(vals, o) {
    const v = vals.filter(nz); if (v.length < 2) return '';
    const lo = Math.min(...v), hi = Math.max(...v), span = (hi - lo) || 1, n = vals.length, bw = W / n;
    const pts = vals.map((x, i) => (nz(x) ? [i * bw + bw / 2, 6 + (1 - (x - lo) / span) * (H - 16), i] : null)).filter(Boolean);
    return `<polyline points="${pts.map((q) => q[0].toFixed(1) + ',' + q[1].toFixed(1)).join(' ')}" fill="none" stroke="${o.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`
      + pts.map((q) => `<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="2.4" fill="${o.color}"><title>${esc(o.tip ? o.tip(q[2]) : vals[q[2]])}</title></circle>`).join('');
  }
  const wrap = (inner) => `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-hidden="true">${[.25, .5, .75].map((f) => `<line x1="0" x2="${W}" y1="${(H * f).toFixed(1)}" y2="${(H * f).toFixed(1)}" stroke="var(--grid)" stroke-width="1" opacity=".6"/>`).join('')}${inner}</svg>`;
  window.CalGrid = { svg: { bars, line, wrap }, load, cls, tag, holiday, isWeekend, fit, days: () => S.days };
})();
