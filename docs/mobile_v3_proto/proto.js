/* ============================================================================
   手機版 v3 原型（docs/mobile_v3_spec.md 的可操作版本）
   資料一律讀 ../site/data/*.json（真資料），剖析圖直接用站上的 diagrams.js ＋ dg/*.js ＋ three3d.js，
   所以「只留編號」這一層是疊在站上真的圖上面，實作時可以原樣搬進 industry.js。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const cache = {};
  const load = (n) => cache[n] || (cache[n] = fetch('../site/data/' + n + '.json').then(r => r.json()).catch(() => null));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const sgn = (v, d) => (v > 0 ? '+' : '') + (+v).toFixed(d == null ? 1 : d);
  const cls = (v) => v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
  const yi = (v) => (v / 1e8).toFixed(v >= 1e11 ? 0 : 1);           // 元 → 億
  const LS = { get(k, d) { try { const v = localStorage.getItem('p3.' + k); return v == null ? d : v; } catch (e) { return d; } },
               set(k, v) { try { localStorage.setItem('p3.' + k, v); } catch (e) { /* 私密視窗 */ } } };
  const charts = [];
  const mkChart = (el) => { const c = echarts.init(el, null, { renderer: 'canvas' }); charts.push(c); return c; };
  const killCharts = () => { while (charts.length) { const c = charts.pop(); try { c.dispose(); } catch (e) { /* 已經掛掉 */ } } };

  /* 階段：配色沿用站上的 STAGE（改善 cyan／領先 紅／轉弱 琥珀／落後 綠）*/
  const ST = {
    improving: { n: '改善', v: '--st-imp' }, leading: { n: '領先', v: '--st-lead' },
    weakening: { n: '轉弱', v: '--st-weak' }, lagging: { n: '落後', v: '--st-lag' },
  };
  const stc = (q) => css(({ improving: '--cyan', leading: '--rise', weakening: '--amber', lagging: '--fall' })[q] || '--flat');

  /* ====================================================================== 說明氣泡「?」
     規則（Andy 2026-09-24）：補充文字一律收進「?」；點背景（或再點一次、Esc）關閉，沒有「收起」鈕。*/
  const scrim = $('#pScrim'), pop = $('#pPop'), sheet = $('#pSheet');
  let closeFn = null;
  function closeAll() {
    pop.hidden = true; sheet.hidden = true; scrim.hidden = true; scrim.classList.remove('clear');
    $$('.p-q.on').forEach(b => b.classList.remove('on'));
    const f = closeFn; closeFn = null; if (f) f();
  }
  scrim.addEventListener('click', closeAll);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAll(); });
  function showPop(btn, html) {
    const wasOn = btn.classList.contains('on');
    closeAll(); if (wasOn) return;
    pop.innerHTML = html; pop.hidden = false; scrim.hidden = false; scrim.classList.add('clear');
    btn.classList.add('on');
    const r = btn.getBoundingClientRect(), vh = innerHeight;
    const h = Math.min(pop.scrollHeight, vh * 0.52);
    /* 氣泡預設開在「?」的正下方；下面放不下（會壓到底部導覽）才翻到上面 */
    const below = r.bottom + 8, navH = 58;
    pop.style.top = (below + h < vh - navH - 8 ? below : Math.max(60, r.top - 8 - h)) + 'px';
  }
  function qbtn(key) { return `<button type="button" class="p-q" data-q="${key}" aria-label="說明">?</button>`; }
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('.p-q[data-q]'); if (!b) return;
    const src = HOW[b.dataset.q]; showPop(b, typeof src === 'function' ? src() : (src || '（說明還沒寫）'));
  });
  function showSheet(html, onClose) {
    closeAll();
    $('.p-sheetbody', sheet).innerHTML = html; sheet.hidden = false; scrim.hidden = false; scrim.classList.add('clear');
    closeFn = onClose || null;
    return sheet;
  }

  /* 說明文字（實作時對應 app.js 的 HOW；這裡只放原型用到的，而且照 Andy「簡短方便閱讀」寫短）*/
  const HOW = {
    rot: `<b>錢往哪個族群跑，跑到循環的哪一段。</b><ul>
      <li>順時針四段：<b style="color:var(--fall)">落後</b> → <b style="color:var(--cyan)">改善</b> → <b style="color:var(--rise)">領先</b> → <b style="color:var(--amber)">轉弱</b>。</li>
      <li>一顆點＝一個族群；越大＝成交值佔比越高，離圓心越遠＝跟大盤差越多。</li>
      <li>兩圈虛線＝今天最大偏離的一半／今天偏離最大的那個族群。</li>
      <li>小腳印＝最近走過的路，越新越清楚。</li>
      <li>四角的數字＝各段有幾個族群，點了只看那一段。</li></ul>
      <div class="p-popfoot">點一顆點看它的數字；點背景關閉。</div>`,
    rank: `<b>這段期間誰把錢吸走了。</b><ul><li>長條＝成交值佔比；右邊小字＝和上一段比多了／少了幾個百分點（紅＝變多、綠＝變少）。</li>
      <li>點一列＝在上面的輪盤只亮它。</li></ul>`,
    idx: `<b>大盤三張圖合成一張。</b><ul><li>上面三顆切換加權／櫃買／台指期，也可以在圖上左右滑。</li>
      <li>紅＝收盤比開盤高，綠＝比開盤低（台股慣例）。細線是 5 日與 20 日均線。</li>
      <li>台指期可以切日盤／夜盤。</li></ul><div class="p-popfoot">原型用資料湖日線；上線版的盤中走勢沿用現行。</div>`,
    breadth: `<b>漲的是少數權值股，還是大多數股票都在漲。</b><ul><li>上面：今天上漲／下跌家數。</li><li>下面：站上 20 日均線的股票比例；高於 50% 表示多數股票在上升趨勢。</li></ul>`,
    drill: `<b>錢從大盤分到哪幾條產業鏈，鏈裡又分給誰。</b><div>台股 → 產業鏈 → 族群 → 個股</div><ul><li>先看產業鏈；點一條往下看族群，再點看個股。</li>
      <li>桌機的分流圖（桑基）在手機改成可以點開的長條，數字是同一份。</li></ul>`,
    inst: `<b>三大法人的錢進了哪些族群。</b><ul><li>紅＝淨買超、綠＝淨賣超，單位萬張，最近一個交易日。</li></ul>`,
    conc: `<b>錢集中在少數族群，還是散開了。</b><ul><li>前 5 名族群吃掉的成交值比例；升高＝更集中在主流。</li></ul>`,
    heat: `<b>哪些族群佔最多成交值、是漲是跌。</b><ul><li>方塊越大＝成交值越大；紅漲綠跌，越深漲跌越大。</li></ul>`,
    theme: `<b>哪些題材在吸金。</b><ul><li>熱度＝資金佔比變化＋法人＋新聞，0～100。</li></ul>`,
    cand: `<b>今天技術面值得看的個股。</b><ul><li>A＝回檔承接、B＝突破追進；分數是技術分。</li><li>這不是買賣建議。</li></ul>`,
    ev: `<b>有沒有理由不進場。</b><ul><li>新聞、法說會、券商目標價。點標題看原文。</li></ul>`,
    dg: () => {
      const d = DGS.cur && DGS.cur.info;
      /* 先講怎麼用（三行），圖本身的長說明、公式與警語卡放在後面（收起來不是刪掉）*/
      return `<b>${esc(d ? d.title : '剖析圖')}</b>`
        + `<ul><li>圖上每個編號＝一個零件或環節，<b>點編號看說明與台股</b>。</li>
           <li>抽屜裡的 ‹ › 依序走完所有編號，不必關掉。</li>
           <li>「放大」看細節，圖可以上下左右滑。</li></ul>`
        + (d && d.sub ? `<div class="p-popfoot" style="color:var(--ink-2)">${esc(d.sub)}</div>` : '')
        + (d && d.notes.length ? `<div class="p-popfoot">${d.notes.map(esc).join('<br>')}</div>` : '');
    },
  };

  /* ====================================================================== 足跡輪盤（新雷達長相）
     長相照 app.js ROT_GRAD_V2 那一版（桌機 2026-09-24 晚上線）：象限底色離圓心越遠越濃（.12→.27）、
     三圈虛線、十字軸、盤緣 72 刻、四角膠囊徽章、淡淡的旋轉掃描、前掌＋腳跟的小腳印、
     點＝發光核心＋1px 白外圈、名字寫成點右側的小膠囊。
     座標換算照 app.js renderRotation 的 pos()：兩軸各除以今天的最大偏離，外圈虛線＝今天偏離最大的族群。*/
  const MAXR = 1.25, TAIL = 0.18;
  function radarPos(points) {
    let sx = 1e-6, sy = 1e-6;
    points.forEach(r => { sx = Math.max(sx, Math.abs(r.x - 100)); sy = Math.max(sy, Math.abs(r.y - 100)); });
    const raw = (x, y) => Math.hypot((x - 100) / sx, (y - 100) / sy);
    let sr = 1e-9, srAll = 1e-9;
    points.forEach(r => { sr = Math.max(sr, raw(r.x, r.y)); (r.trail || []).forEach(w => { srAll = Math.max(srAll, raw(w[1], w[2])); }); });
    srAll = Math.max(srAll, sr);
    const span = Math.max(1e-6, srAll / sr - 1), RIM = MAXR * (1 + TAIL);
    return (x, y) => {
      const dx = (x - 100) / sx, dy = (y - 100) / sy;
      const u = Math.hypot(dx, dy) / sr;
      const k = u <= 1 ? u : 1 + TAIL * (u - 1) / span;
      return [Math.min(RIM, k * MAXR) / RIM, Math.atan2(dy, dx)];   // [0～1 的半徑, 弧度]
    };
  }
  function radar(host, all, opts) {
    opts = opts || {};
    const W = Math.round(host.clientWidth || 340);
    let S = Math.min(W, opts.max || 360);
    /* fitBelow：輪盤下面還要放多少東西（px）。依「可視高度 − 輪盤頂端 − 底部導覽 − 這個數」決定輪盤多大，
       下限 260（再小四角的膠囊會壓到盤面）。這就是「圖與數字同一屏」的做法：先保數字，再給圖。*/
    if (opts.fitBelow) {
      const top = host.getBoundingClientRect().top + scrollY;
      S = Math.max(260, Math.min(S, Math.floor(innerHeight - 58 - top - opts.fitBelow)));
    }
    const c = S / 2, R = c - 30;                               // 四角留給膠囊徽章
    const pos = radarPos(all);
    const shown = all.slice().sort((a, b) => b.share - a.share).slice(0, opts.top || 16)
      .filter(p => !opts.quad || p.quadrant === opts.quad);
    const xy = (x, y) => { const [r, a] = pos(x, y); return [c + Math.cos(a) * r * R, c - Math.sin(a) * r * R]; };
    const ringR = R * (MAXR / (MAXR * (1 + TAIL)));           // u＝1（外圈虛線）
    const Q = [['leading', 0], ['improving', 90], ['lagging', 180], ['weakening', 270]];
    const A = [[.12, .17, .22, .27]][0];
    let g = `<defs>`;
    Q.forEach(([q]) => {
      const col = stc(q);
      g += `<radialGradient id="rg-${q}" cx="${c}" cy="${c}" r="${R}" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="${col}" stop-opacity="${A[0]}"/><stop offset=".42" stop-color="${col}" stop-opacity="${A[1]}"/>
        <stop offset=".85" stop-color="${col}" stop-opacity="${A[2]}"/><stop offset="1" stop-color="${col}" stop-opacity="${A[3]}"/></radialGradient>`;
    });
    g += `<linearGradient id="rscanG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${css('--cyan')}" stop-opacity="0"/><stop offset="1" stop-color="${css('--cyan')}" stop-opacity=".12"/></linearGradient>
      <filter id="rglow" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="2.4"/></filter></defs>`;
    // 象限扇形（SVG 角度：0°＝右，逆時針為正 → 螢幕上 y 反向）
    const arc = (a0, a1, r) => {
      const p = (a) => [c + Math.cos(a * Math.PI / 180) * r, c - Math.sin(a * Math.PI / 180) * r];
      const [x0, y0] = p(a0), [x1, y1] = p(a1);
      return `M${c},${c} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 0 ${x1.toFixed(1)},${y1.toFixed(1)} Z`;
    };
    Q.forEach(([q, a]) => { g += `<path d="${arc(a, a + 90, R)}" fill="url(#rg-${q})" opacity="${opts.quad && opts.quad !== q ? .35 : 1}"/>`; });
    const line = css('--line-2');
    [.25, .5, .75].forEach(f => { g += `<circle cx="${c}" cy="${c}" r="${(R * f).toFixed(1)}" fill="none" stroke="${line}" stroke-opacity=".35" stroke-width=".6"/>`; });
    g += `<circle cx="${c}" cy="${c}" r="${(ringR / 2).toFixed(1)}" fill="none" stroke="${css('--ink-3')}" stroke-opacity=".55" stroke-dasharray="3 4"/>`;
    g += `<circle cx="${c}" cy="${c}" r="${ringR.toFixed(1)}" fill="none" stroke="${css('--ink-3')}" stroke-opacity=".7" stroke-dasharray="5 4"/>`;
    g += `<circle cx="${c}" cy="${c}" r="${R}" fill="none" stroke="${line}" stroke-width="1.2"/>`;
    g += `<path d="M${c - R},${c}H${c + R}M${c},${c - R}V${c + R}" stroke="${line}" stroke-width=".8"/>`;
    for (let i = 0; i < 72; i++) {                            // 羅盤刻度：每 5° 一刻、每 45° 長刻
      const a = i * 5 * Math.PI / 180, L = i % 9 === 0 ? 8 : 3.5;
      g += `<path d="M${(c + Math.cos(a) * R).toFixed(1)},${(c - Math.sin(a) * R).toFixed(1)}L${(c + Math.cos(a) * (R - L)).toFixed(1)},${(c - Math.sin(a) * (R - L)).toFixed(1)}" stroke="${css('--ink-3')}" stroke-opacity="${L > 4 ? .8 : .4}" stroke-width=".8"/>`;
    }
    // 掃描：45° 扇形拖尾＋一條射線，6 秒一圈（系統開了「減少動態效果」就不畫）
    g += `<g class="rscan" style="transform-origin:${c}px ${c}px"><path d="${arc(0, 45, R)}" fill="url(#rscanG)"/><path d="M${c},${c}L${c + R},${c}" stroke="${css('--cyan')}" stroke-opacity=".35" stroke-width="1"/></g>`;
    // 腳印：佔比前 3 的最近 8 天
    shown.slice(0, 3).forEach(p => {
      const tr = (p.trail || []).slice(-9);
      const col = stc(p.quadrant);
      for (let i = 1; i < tr.length; i++) {
        const [x0, y0] = xy(tr[i - 1][1], tr[i - 1][2]), [x1, y1] = xy(tr[i][1], tr[i][2]);
        if (Math.hypot(x1 - x0, y1 - y0) < 3) continue;
        const ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI + 90, op = (.18 + .6 * i / tr.length).toFixed(2);
        g += `<g transform="translate(${x1.toFixed(1)},${y1.toFixed(1)}) rotate(${ang.toFixed(0)})" fill="${col}" opacity="${op}">
          <ellipse cx="0" cy="-1.6" rx="1.9" ry="2.6"/><ellipse cx="0" cy="2.6" rx="1.3" ry="1.4"/></g>`;
      }
    });
    // 點
    const pts = [];
    shown.forEach(p => {
      const [x, y] = xy(p.x, p.y), col = stc(p.quadrant), r = Math.max(4, Math.min(11, 3 + Math.sqrt(p.share) * 2.2));
      pts.push({ p, x, y, r });
      const sel = opts.sel === p.group_id;
      g += `<g data-g="${p.group_id}"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 3).toFixed(1)}" fill="${col}" opacity=".45" filter="url(#rglow)"/>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${col}" stroke="#fff" stroke-width="${sel ? 2.4 : 1}"/>
        ${sel ? `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 6).toFixed(1)}" fill="none" stroke="${col}" stroke-width="2"/>` : ''}</g>`;
    });
    // 名字膠囊：佔比前 5 ＋ 選到的那顆；互相擋到就往下推一格（最多三次），還擋就不寫
    const boxes = [];
    const lbl = shown.slice(0, 5).map(p => p.group_id); if (opts.sel && !lbl.includes(opts.sel)) lbl.push(opts.sel);
    pts.filter(q => lbl.includes(q.p.group_id)).forEach(q => {
      const t = q.p.group_name.length > 6 ? q.p.group_name.slice(0, 6) + '…' : q.p.group_name;
      const w = t.length * 12 + 12, h = 18;
      let x = q.x + q.r + 4, y = q.y - h / 2;
      if (x + w > S - 2) x = q.x - q.r - 4 - w;
      for (let k = 0; k < 3 && boxes.some(b => x < b[0] + b[2] && x + w > b[0] && y < b[1] + b[3] && y + h > b[1]); k++) y += h + 2;
      if (boxes.some(b => x < b[0] + b[2] && x + w > b[0] && y < b[1] + b[3] && y + h > b[1])) return;
      boxes.push([x, y, w, h]);
      g += `<g pointer-events="none"><rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w}" height="${h}" rx="9" fill="${css('--bg')}" fill-opacity=".82" stroke="${stc(q.p.quadrant)}" stroke-opacity=".8"/>
        <text x="${(x + 6).toFixed(1)}" y="${(y + 13.2).toFixed(1)}" font-size="12" fill="${css('--ink')}">${esc(t)}</text></g>`;
    });
    const cnt = {}; all.forEach(p => { cnt[p.quadrant] = (cnt[p.quadrant] || 0) + 1; });
    const corner = { improving: 'left:0;top:0', leading: 'right:0;top:0', lagging: 'left:0;bottom:0', weakening: 'right:0;bottom:0' };
    host.innerHTML = `<div class="p-radar" style="width:${S}px;height:${S}px"><svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}" role="img" aria-label="足跡輪盤">${g}</svg>`
      + Object.keys(ST).map(q => `<button type="button" class="qb${opts.quad === q ? ' on' : ''}" data-quad="${q}" style="${corner[q]};--c:${stc(q)}">${ST[q].n}<b>${cnt[q] || 0}</b></button>`).join('')
      + `</div>`;
    const svg = $('svg', host);
    /* 點選：找最近的一顆（24px 內）。點太小、又常常疊在一起，逐顆掛 hit 區會互相搶 */
    svg.addEventListener('click', (e) => {
      const b = svg.getBoundingClientRect(), k = S / b.width;
      const mx = (e.clientX - b.left) * k, my = (e.clientY - b.top) * k;
      let best = null, bd = 24 * k;
      pts.forEach(q => { const d = Math.hypot(q.x - mx, q.y - my) - q.r; if (d < bd) { bd = d; best = q; } });
      if (best && opts.onPick) opts.onPick(best.p);
    });
    $$('.qb', host).forEach(b => b.addEventListener('click', () => opts.onQuad && opts.onQuad(b.dataset.quad)));
    return { shown, pts, S };
  }
  function focusHtml(p, note) {
    if (!p) return '';
    const col = stc(p.quadrant);
    return `<div class="p-focus" style="--c:${col}" data-focus="${p.group_id}"><span class="nm"><i></i>${esc(p.group_name)}</span>
      <span><span class="st">${ST[p.quadrant] ? ST[p.quadrant].n : ''}</span></span><a href="#grp/${p.group_id}" data-soon="族群頁">族群 ›</a>
      <span class="nums"><span><em>強弱</em><span class="${cls(p.x - 100)}">${sgn(p.x - 100)}</span></span>
      <span><em>動能</em><span class="${cls(p.y - 100)}">${sgn(p.y - 100)}</span></span>
      <span><em>佔比</em>${(+p.share).toFixed(1)}%</span></span>${note ? `<span class="nums" style="font-family:inherit;font-weight:400;font-size:12px;color:var(--ink-3)">${esc(note)}</span>` : ''}</div>`;
  }

  /* ====================================================================== 共用：兩層導覽
     總覽＝四步動線（上層）＋ 那一步的分段（下層）；其他頁只有一層分段。選到哪裡記在 localStorage。*/
  function pager(host, key, segs, draw) {
    let cur = LS.get('seg.' + key, segs[0]); if (!segs.includes(cur)) cur = segs[0];
    const bar = document.createElement('div'); bar.className = 'p-segs'; bar.setAttribute('role', 'tablist');
    bar.innerHTML = segs.map(s => `<button type="button" role="tab" data-seg="${s}">${s}</button>`).join('');
    const body = document.createElement('div');
    host.appendChild(bar); host.appendChild(body);
    const go = (s) => {
      cur = s; LS.set('seg.' + key, s);
      $$('button', bar).forEach(b => { const on = b.dataset.seg === s; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); });
      killCharts(); body.innerHTML = ''; closeAll(); draw(s, body);
    };
    bar.addEventListener('click', (e) => { const b = e.target.closest('button[data-seg]'); if (b) go(b.dataset.seg); });
    go(cur);
    return { go };
  }

  /* ====================================================================== 總覽 */
  const STEPS = [
    { k: '①', n: '錢往哪跑', segs: ['足跡輪盤', '資金去向', '熱力圖', '熱門題材'] },
    { k: '②', n: '貴不貴', segs: ['大盤', '市場寬度', '法人買超'] },
    { k: '③', n: '何時進場', segs: ['今日候選'] },
    { k: '④', n: '別進的理由', segs: ['今日事件'] },
  ];
  function pageOv(main) {
    let st = +LS.get('step', 0) || 0;
    const steps = document.createElement('div'); steps.className = 'p-steps';
    steps.innerHTML = STEPS.map((s, i) => `<button type="button" data-step="${i}"><em>${s.k}</em><b>${s.n}</b></button>`).join('');
    const host = document.createElement('div');
    main.appendChild(steps); main.appendChild(host);
    const go = (i) => {
      st = i; LS.set('step', i);
      $$('button', steps).forEach(b => b.classList.toggle('on', +b.dataset.step === i));
      host.innerHTML = '';
      pager(host, 'ov' + i, STEPS[i].segs, (seg, body) => {
        const done = OV[seg] ? OV[seg](body) : (body.innerHTML = `<div class="p-todo">「${seg}」原型沒有做，版面規格見 docs/mobile_v3_spec.md §3-1</div>`);
        Promise.resolve(done).then(() => {
          const nx = (i + 1) % 4;
          const nb = document.createElement('button'); nb.type = 'button'; nb.className = 'p-next';
          nb.textContent = (nx === 0 ? '回到 ' : '下一步：') + STEPS[nx].k + ' ' + STEPS[nx].n + ' ›';
          nb.onclick = () => { go(nx); scrollTo(0, 0); };
          body.appendChild(nb);
        });
      });
    };
    steps.addEventListener('click', (e) => { const b = e.target.closest('button[data-step]'); if (b) go(+b.dataset.step); });
    go(st);
  }

  const OV = {
    '足跡輪盤': async (body) => {
      const f = await load('flow_v3'); if (!f) return;
      const all = f.rrg.points;
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><h3>足跡輪盤</h3><small>${f.rrg.date.slice(5)}</small><span class="p-sp"></span>${qbtn('rot')}</div><div class="p-rhost"></div><div class="p-fhost"></div>`;
      body.appendChild(card);
      let sel = null, quad = null;
      const draw = () => {
        const r = radar($('.p-rhost', card), all, { sel, quad, max: 360,
          onPick: (p) => { sel = p.group_id; draw(); },
          onQuad: (q) => { quad = quad === q ? null : q; draw(); } });
        if (!sel && r.shown.length) sel = r.shown[0].group_id;
        const p = all.find(x => x.group_id === sel);
        $('.p-fhost', card).innerHTML = focusHtml(p, quad ? `只看「${ST[quad].n}」：${r.shown.length} 個（佔比前 16 名內）· 再點一次角落的數字還原` : '');
        $('.p-rhost', card).dataset.sel = sel || '';
        $('.p-rhost', card).dataset.shown = r.shown.length;
      };
      draw();
    },
    '資金去向': (body) => drillCard(body),
    '熱力圖': async (body) => {
      const g = await load('groups_today'); if (!g) return;
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><h3>資金熱力圖</h3><small>${g[0].date.slice(5)}　成交值前 20</small><span class="p-sp"></span>${qbtn('heat')}</div><div class="p-chart" style="height:440px"></div>`;
      body.appendChild(card);
      const hm = (v) => css(v >= 3 ? '--hm-p3' : v >= 1.5 ? '--hm-p2' : v > .2 ? '--hm-p1' : v <= -3 ? '--hm-n3' : v <= -1.5 ? '--hm-n2' : v < -.2 ? '--hm-n1' : '--hm-0');
      const data = g.slice().sort((a, b) => b.turnover - a.turnover).slice(0, 20)
        .map(x => ({ name: x.group_name, value: x.turnover, chg: x.chg_pct, itemStyle: { color: hm(x.chg_pct) } }));
      const c = mkChart($('.p-chart', card));
      c.setOption({ series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, left: 0, right: 0, top: 0, bottom: 0,
        label: { show: true, formatter: (p) => `${p.name}\n${sgn(p.data.chg, 2)}%`, color: '#fff', fontSize: 12, lineHeight: 16, fontWeight: 600 },
        itemStyle: { borderColor: css('--bg'), borderWidth: 2, gapWidth: 2 }, data }] });
    },
    '熱門題材': async (body) => {
      const t = await load('themes'); if (!t) return;
      const card = document.createElement('div'); card.className = 'p-card';
      const top = t.themes.slice().sort((a, b) => b.heat - a.heat).slice(0, 8);
      card.innerHTML = `<div class="p-head"><h3>熱門題材</h3><small>熱度前 8</small><span class="p-sp"></span>${qbtn('theme')}</div>
        <ul class="p-rank">${top.map((x, i) => `<li style="--c:var(--amber)"><span class="r">${i + 1}</span><span class="bar" style="width:calc((100% - 110px) * ${(x.heat / 100).toFixed(2)})"></span><span class="n">${esc(x.name)}</span><span class="v">${x.heat}<small class="${cls(x.chg_pct)}">${sgn(x.chg_pct)}%</small></span></li>`).join('')}</ul>`;
      body.appendChild(card);
    },
    '大盤': (body) => indexCard(body),
    '市場寬度': async (body) => {
      const [mh, br] = await Promise.all([load('market_heat'), load('ma_breadth')]); if (!mh || !br) return;
      const s = br.series['全市場']['20'], d = br.dates;
      const card = document.createElement('div'); card.className = 'p-card';
      const tot = mh.advancers + mh.decliners + mh.unchanged;
      card.innerHTML = `<div class="p-head"><h3>市場寬度</h3><small>${mh.date.slice(5)}</small><span class="p-sp"></span>${qbtn('breadth')}</div>
        <div class="p-idxnum"><span class="px up">${mh.advancers}</span><span class="chg">漲</span><span class="px dn">${mh.decliners}</span><span class="chg">跌</span><span class="dt">平 ${mh.unchanged}</span></div>
        <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;margin:6px 0 10px"><i style="flex:${mh.advancers};background:var(--rise)"></i><i style="flex:${mh.unchanged};background:var(--flat)"></i><i style="flex:${mh.decliners};background:var(--fall)"></i></div>
        <div class="p-idxnum"><span class="px">${s[s.length - 1].toFixed(1)}%</span><span class="chg ${cls(s[s.length - 1] - s[s.length - 6])}">${sgn(s[s.length - 1] - s[s.length - 6])} <small style="font-size:12px;color:var(--ink-3)">比 5 日前</small></span><span class="dt">站上 20 日均線</span></div>
        <div class="p-chart" style="height:260px"></div>`;
      body.appendChild(card);
      const n = 120, c = mkChart($('.p-chart', card));
      c.setOption({ grid: { left: 34, right: 8, top: 10, bottom: 22 }, xAxis: { type: 'category', data: d.slice(-n).map(x => x.slice(5)), axisLabel: { color: css('--ink-3'), fontSize: 12 }, axisLine: { lineStyle: { color: css('--line-2') } } },
        yAxis: { min: 0, max: 100, splitNumber: 2, axisLabel: { color: css('--ink-3'), fontSize: 12 }, splitLine: { lineStyle: { color: css('--line') } } },
        series: [{ type: 'line', data: s.slice(-n), showSymbol: false, lineStyle: { color: css('--cyan'), width: 1.6 }, areaStyle: { color: css('--cyan'), opacity: .08 },
          markLine: { silent: true, symbol: 'none', data: [{ yAxis: 50 }], lineStyle: { color: css('--ink-3'), type: 'dashed' }, label: { show: false } } }] });
      void tot;
    },
    '今日候選': async (body) => {
      const c = await load('candidates'); if (!c) return;
      const card = document.createElement('div'); card.className = 'p-card';
      const row = (x) => `<li style="--c:${x.grade === 'A' ? 'var(--cyan)' : 'var(--violet)'}"><span class="r">${x.grade || ''}</span><span class="bar" style="width:calc((100% - 150px) * ${(x.tech_score / 100).toFixed(2)})"></span>
        <span class="n">${esc(x.name)} <small style="color:var(--ink-3);font-size:12px">${x.code}</small></span><span class="v">${x.close}<small class="${cls(x.chg_pct)}">${sgn(x.chg_pct, 2)}%</small></span></li>`;
      card.innerHTML = `<div class="p-head"><h3>今日候選</h3><small>${c.length} 檔</small><span class="p-sp"></span>${qbtn('cand')}</div><ul class="p-rank" id="pCand">${c.slice(0, 6).map(row).join('')}</ul>
        <button type="button" class="p-more" id="pCandAll">還有 ${c.length - 6} 檔 · 看全部 ›</button>`;
      body.appendChild(card);
      $('#pCandAll', card).onclick = (e) => { $('#pCand', card).innerHTML = c.slice(0, 40).map(row).join(''); e.target.remove(); };
    },
    '今日事件': async (body) => {
      const n = await load('news'); if (!n) return;
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><h3>今日事件</h3><small>${n.length} 則</small><span class="p-sp"></span>${qbtn('ev')}</div>
        <ul class="p-rank">${n.slice(0, 8).map(x => `<li style="grid-template-columns:44px 1fr;min-height:44px"><span class="r" style="text-align:left">${esc(x.category)}</span><span class="n" style="white-space:normal;font-size:13px;line-height:1.45">${esc(x.title)}</span></li>`).join('')}</ul>
        <button type="button" class="p-more" data-soon="事件抽屜">看全部 ${n.length} 則 ›</button>`;
      body.appendChild(card);
    },
  };

  /* ---- 大盤：加權／櫃買／台指期合成一張，可點可滑 ---- */
  async function indexCard(body) {
    const d = await load('index_ohlc'); if (!d) return;
    const KEYS = [['TSE', '加權'], ['OTC', '櫃買'], ['FUT', '台指期']];
    let i = Math.max(0, KEYS.findIndex(k => k[0] === LS.get('idx', 'TSE'))), night = false;
    const card = document.createElement('div'); card.className = 'p-card'; card.id = 'pIdx';
    card.innerHTML = `<div class="p-head"><span class="p-seg2" id="pIdxSw">${KEYS.map((k, j) => `<button type="button" data-i="${j}">${k[1]}</button>`).join('')}</span><span class="p-sp"></span>
      <button type="button" class="p-btn" id="pNight" hidden>日盤</button>${qbtn('idx')}</div>
      <div class="p-idxnum" id="pIdxNum"></div><div class="p-ohlc" id="pIdxOhlc"></div>
      <div class="p-chart" id="pIdxChart" style="height:320px"></div><div class="p-pos" id="pIdxPos"></div>`;
    body.appendChild(card);
    const c = mkChart($('#pIdxChart', card));
    const ma = (arr, n) => arr.map((_, k) => k < n - 1 ? null : +(arr.slice(k - n + 1, k + 1).reduce((s, v) => s + v, 0) / n).toFixed(2));
    const draw = () => {
      const key = KEYS[i][0] === 'FUT' && night ? 'FUT_N' : KEYS[i][0];
      const rows = d[key].slice(-80), last = rows[rows.length - 1], prev = rows[rows.length - 2];
      const chg = last[4] - prev[4], pct = chg / prev[4] * 100, dp = key === 'OTC' ? 2 : key.startsWith('FUT') ? 0 : 2;
      $$('#pIdxSw button', card).forEach(b => b.classList.toggle('on', +b.dataset.i === i));
      const nb = $('#pNight', card); nb.hidden = KEYS[i][0] !== 'FUT'; nb.textContent = night ? '夜盤' : '日盤'; nb.classList.toggle('on', night);
      const f = (v) => (+v).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });
      $('#pIdxNum', card).innerHTML = `<span class="px ${cls(chg)}">${f(last[4])}</span><span class="chg ${cls(chg)}">${sgn(chg, dp)}　${sgn(pct, 2)}%</span>`;

      $('#pIdxOhlc', card).innerHTML = `<span>開<b>${f(last[1])}</b></span><span>高<b class="up">${f(last[2])}</b></span><span>低<b class="dn">${f(last[3])}</b></span><span>昨收<b>${f(prev[4])}</b></span>`;
      $('#pIdxPos', card).innerHTML = KEYS.map((_, j) => `<i class="${j === i ? 'on' : ''}"></i>`).join('') + `<span>${i + 1} / ${KEYS.length}　左右滑切換</span>`;
      const cl = rows.map(r => r[4]);
      c.setOption({ animation: false,
        title: { text: last[0].slice(5) + (key === 'FUT_N' ? ' 夜盤' : ' 收盤'), left: 6, top: 2, textStyle: { fontSize: 12, fontWeight: 400, color: css('--ink-3'), fontFamily: css('--mono') } },
        grid: [{ left: 4, right: 52, top: 8, height: '70%' }, { left: 4, right: 52, top: '80%', bottom: 18 }],
        xAxis: [{ type: 'category', data: rows.map(r => r[0].slice(5)), axisLabel: { color: css('--ink-3'), fontSize: 12, showMinLabel: false, hideOverlap: true }, axisLine: { lineStyle: { color: css('--line-2') } }, axisTick: { show: false } },
                { type: 'category', gridIndex: 1, data: rows.map(r => r[0]), axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false } }],
        yAxis: [{ scale: true, position: 'right', splitNumber: 3, axisLabel: { color: css('--ink-3'), fontSize: 12 }, splitLine: { lineStyle: { color: css('--line') } } },
                { gridIndex: 1, scale: true, show: false }],
        series: [{ type: 'candlestick', data: rows.map(r => [r[1], r[4], r[3], r[2]]),
                   itemStyle: { color: css('--rise'), color0: css('--fall'), borderColor: css('--rise'), borderColor0: css('--fall') } },
                 { type: 'line', data: ma(cl, 5), showSymbol: false, lineStyle: { width: 1, color: css('--amber') } },
                 { type: 'line', data: ma(cl, 20), showSymbol: false, lineStyle: { width: 1, color: css('--violet') } },
                 { type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: rows.map(r => ({ value: r[5], itemStyle: { color: r[4] >= r[1] ? css('--rise') : css('--fall'), opacity: .55 } })) }] }, true);
      card.dataset.cur = key;
    };
    $('#pIdxSw', card).addEventListener('click', (e) => { const b = e.target.closest('button[data-i]'); if (!b) return; i = +b.dataset.i; LS.set('idx', KEYS[i][0]); draw(); });
    $('#pNight', card).onclick = () => { night = !night; draw(); };
    // 左右滑：水平位移 > 50px 而且比垂直大，才算切換（不然會搶掉整頁的上下捲動）
    let t0 = null; const el = $('#pIdxChart', card);
    el.addEventListener('touchstart', (e) => { const t = e.touches[0]; t0 = [t.clientX, t.clientY]; }, { passive: true });
    el.addEventListener('touchend', (e) => {
      if (!t0) return; const t = e.changedTouches[0], dx = t.clientX - t0[0], dy = t.clientY - t0[1]; t0 = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) { i = (i + (dx < 0 ? 1 : KEYS.length - 1)) % KEYS.length; LS.set('idx', KEYS[i][0]); draw(); }
    }, { passive: true });
    draw();
  }

  /* ---- 資金去向：桑基 → 可點開的長條（台股 → 產業鏈 → 族群 → 個股）---- */
  async function drillCard(body) {
    const f = await load('flow_v3'); if (!f) return;
    const L = f.sankey.links, N = f.sankey.nodes;
    /* 「其他族群／其他產業」是沒有歸類的剩餘，永遠排最後、灰色 —— 不然它會以 46% 佔掉第一名，看起來像主流 */
    const isOther = (n) => /^其他/.test(n);
    const kids = (name) => L.filter(l => l.source === name).sort((a, b) => (isOther(a.target) - isOther(b.target)) || (b.value - a.value));
    const total = kids('台股成交值').reduce((s, l) => s + l.value, 0);
    const node = (n) => N.find(x => x.name === n) || {};
    const card = document.createElement('div'); card.className = 'p-card p-drill';
    card.innerHTML = `<div class="p-head"><h3>資金去向</h3><small>${f.date.slice(5)}</small><span class="p-sp"></span>${qbtn('drill')}</div><div class="p-dh"></div>`;
    body.appendChild(card);
    const open = new Set();
    /* 長條以「同一層、不含『其他』的最大值」為滿格：不然「其他族群」46% 會把其他長條壓成一條線 */
    const baseOf = (ls) => Math.max(1, ...ls.filter(l => !isOther(l.target)).map(l => l.value));
    const rows = (src, lv) => { const ks = kids(src), base = baseOf(ks); return ks.map((l, i) => {
      const k = lv + ':' + l.target, isOpen = open.has(k), has = lv < 3 && kids(l.target).length;
      const col = isOther(l.target) ? 'var(--flat)' : lv === 1 ? 'var(--cyan)' : lv === 2 ? 'var(--violet)' : 'var(--amber)';
      return `<li data-k="${esc(k)}" style="--c:${col}"><span class="r">${has ? (isOpen ? '▾' : '▸') : (i + 1)}</span><span class="bar" style="width:calc((100% - 120px) * ${Math.min(1, l.value / base).toFixed(3)})"></span>
        <span class="n">${esc(l.target)}</span><span class="v">${yi(l.value)} 億<small style="color:var(--ink-3)">${(l.value / total * 100).toFixed(1)}%</small></span></li>`
        + (isOpen && has ? `<li style="display:block;padding:0;min-height:0;cursor:default"><ul class="p-rank lv">${rows(l.target, lv + 1)}</ul></li>` : '');
    }).join(''); };
    const draw = () => { $('.p-dh', card).innerHTML = `<ul class="p-rank">${rows('台股成交值', 1)}</ul>`; };
    card.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-k]'); if (!li) return;
      const k = li.dataset.k; open.has(k) ? open.delete(k) : open.add(k); draw();
      card.dataset.open = open.size;
    });
    draw(); void node;
  }

  /* ====================================================================== 資金流向 */
  function pageFlow(main) {
    pager(main, 'flow', ['輪動', '資金去向', '法人', '集中度'], (seg, body) => FLOW[seg](body));
  }
  const FLOW = {
    '輪動': async (body) => {
      const [f, sd] = await Promise.all([load('flow_v3'), load('sankey_daily')]); if (!f) return;
      /* 產業鏈中文名：先拿 sankey_daily 的 chain_name，沒有的（傳產、金融）用站上 industry_map 的名字補 */
      const chainName = { traditional: '傳產', financial: '金融', industry: '其他產業別' };
      ((sd && sd.groups) || []).forEach(g => { if (g.chain_name) chainName[g.chain] = g.chain_name; });
      const periods = f.periods;
      let chain = LS.get('flow.chain', ''), pk = LS.get('flow.period', periods[0].key), sel = null;
      if (!periods.some(p => p.key === pk)) pk = periods[0].key;
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><h3>資金輪動</h3><span class="p-sp"></span><button type="button" class="p-btn" id="pFilt"></button>${qbtn('rot')}</div>
        <div class="p-rhost"></div><div class="p-fhost"></div>
        <div class="p-head" style="margin-top:2px"><h3 style="font-size:14px">資金排行</h3><small id="pRankSub"></small><span class="p-sp"></span>${qbtn('rank')}</div><ul class="p-rank" id="pRank"></ul>`;
      body.appendChild(card);
      const draw = () => {
        const pts = f.rrg.points.filter(p => !chain || p.chain === chain);
        const per = periods.find(p => p.key === pk);
        const gs = per.groups.filter(g => !chain || g.chain === chain).sort((a, b) => b.share - a.share).slice(0, 8);
        $('#pFilt', card).textContent = '篩選 · ' + (chain ? (chainName[chain] || chain) : '全部') + ' · ' + per.label;
        $('#pFilt', card).classList.toggle('on', !!chain || pk !== periods[0].key);
        const r = radar($('.p-rhost', card), pts, { sel, max: 340, fitBelow: 81 + 42 + 5 * 36 + 18, onPick: (p) => { sel = p.group_id; draw(); }, onQuad: () => {} });
        if (!sel && r.shown.length) sel = r.shown[0].group_id;
        const p = pts.find(x => x.group_id === sel);
        const onClock = r.shown.some(x => x.group_id === sel);
        $('.p-fhost', card).innerHTML = p ? focusHtml(p) : `<div class="p-focus"><span class="nm">${esc((gs.find(g => g.group_id === sel) || {}).group_name || '')}</span><span></span><span></span><span class="nums" style="font-family:inherit;font-weight:400;font-size:12px">不在輪盤佔比前 16 名內，所以輪盤沒有變化</span></div>`;
        const mx = gs.length ? gs[0].share : 1;
        $('#pRankSub', card).textContent = `${per.label}　${per.from.slice(5)}～${per.to.slice(5)}`;
        $('#pRank', card).innerHTML = gs.map((g, i) => `<li data-g="${g.group_id}" class="${g.group_id === sel ? 'on' : ''}" style="--c:${stc((f.rrg.points.find(x => x.group_id === g.group_id) || {}).quadrant)}">
          <span class="r">${i + 1}</span><span class="bar" style="width:calc((100% - 140px) * ${(g.share / mx).toFixed(3)})"></span>
          <span class="n">${esc(g.group_name)}</span><span class="v">${g.share.toFixed(1)}%<small class="${cls(g.share_chg)}">${sgn(g.share_chg)}</small></span></li>`).join('');
        card.dataset.n = pts.length; card.dataset.chain = chain; card.dataset.sel = sel || ''; card.dataset.onclock = onClock ? '1' : '0';
      };
      $('#pRank', card).addEventListener('click', (e) => { const li = e.target.closest('li[data-g]'); if (!li) return; sel = li.dataset.g; draw(); });
      $('#pFilt', card).onclick = () => {
        const chains = [...new Set(f.rrg.points.map(p => p.chain))];
        const sh = showSheet(`<div class="p-shhead"><b>篩選與期間</b></div>
          <div class="p-shbody"><div style="font-size:12px;color:var(--ink-3)">產業鏈</div><div class="p-chips" id="pShChain">
          <a href="javascript:void 0" data-c="" style="${!chain ? 'border-color:var(--cyan);color:var(--cyan)' : ''}">全部</a>${chains.map(c => `<a href="javascript:void 0" data-c="${c}" style="${chain === c ? 'border-color:var(--cyan);color:var(--cyan)' : ''}">${esc(chainName[c] || c)}</a>`).join('')}</div>
          <div style="font-size:12px;color:var(--ink-3);margin-top:12px">排行期間</div><div class="p-chips" id="pShPer">${periods.map(p => `<a href="javascript:void 0" data-p="${p.key}" style="${pk === p.key ? 'border-color:var(--cyan);color:var(--cyan)' : ''}">${esc(p.label)}</a>`).join('')}</div></div>`);
        sh.onclick = (e) => {
          const a = e.target.closest('a[data-c],a[data-p]'); if (!a) return;
          if (a.dataset.c != null) { chain = a.dataset.c; LS.set('flow.chain', chain); sel = null; }
          if (a.dataset.p) { pk = a.dataset.p; LS.set('flow.period', pk); }
          closeAll(); draw();
        };
      };
      draw();
    },
    '資金去向': (body) => drillCard(body),
    '法人': async (body) => {
      const f = await load('flow_v3'); if (!f) return;
      /* 法人資料比價量晚一天（meta.inst_date）：最後一天常常全是 null，往回找第一個有值的日子 */
      const src = f.inst_daily;
      let last = src.dates.length - 1;
      while (last > 0 && !src.groups.some(g => g.foreign[last] != null || g.trust[last] != null || g.dealer[last] != null)) last--;
      const KS = [['foreign', '外資'], ['trust', '投信'], ['dealer', '自營'], ['total', '合計']];
      let k = LS.get('inst', 'total');
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><span class="p-seg2" id="pInstSw">${KS.map(x => `<button type="button" data-k="${x[0]}">${x[1]}</button>`).join('')}</span><span class="p-sp"></span>${qbtn('inst')}</div>
        <div class="p-head"><small>${src.dates[last]}　淨買超（萬張）</small></div><div class="p-chart" style="height:470px"></div>`;
      body.appendChild(card);
      const c = mkChart($('.p-chart', card));
      const draw = () => {
        $$('#pInstSw button', card).forEach(b => b.classList.toggle('on', b.dataset.k === k));
        const gs = src.groups.map(g => { const fo = g.foreign[last] || 0, tr = g.trust[last] || 0, de = g.dealer[last] || 0;
          return { n: g.group_name, v: (k === 'total' ? fo + tr + de : k === 'foreign' ? fo : k === 'trust' ? tr : de) / 1e4 }; })
          .filter(g => g.v).sort((a, b) => b.v - a.v);
        const rows = gs.slice(0, 8).concat(gs.slice(-8)).reverse();
        c.setOption({ animation: false, grid: { left: 96, right: 44, top: 4, bottom: 4 },
          xAxis: { type: 'value', show: false }, yAxis: { type: 'category', data: rows.map(r => r.n), axisLabel: { color: css('--ink-2'), fontSize: 12, width: 90, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { lineStyle: { color: css('--line-2') } } },
          series: [{ type: 'bar', barWidth: 14, data: rows.map(r => ({ value: +r.v.toFixed(1), itemStyle: { color: r.v > 0 ? css('--rise') : css('--fall'), borderRadius: 3 } })),
            label: { show: true, position: 'right', color: css('--ink-2'), fontSize: 12, formatter: (p) => sgn(p.value) } }] }, true);
        card.dataset.k = k;
      };
      $('#pInstSw', card).addEventListener('click', (e) => { const b = e.target.closest('button[data-k]'); if (!b) return; k = b.dataset.k; LS.set('inst', k); draw(); });
      draw();
    },
    '集中度': async (body) => {
      const d = await load('concentration'); if (!d) return;
      const rows = d.slice(-120), last = rows[rows.length - 1], ago = rows[rows.length - 21];
      const card = document.createElement('div'); card.className = 'p-card';
      card.innerHTML = `<div class="p-head"><h3>資金集中度</h3><small>${last.date.slice(5)}</small><span class="p-sp"></span>${qbtn('conc')}</div>
        <div class="p-idxnum"><span class="px">${last.top_share.toFixed(1)}%</span><span class="chg ${cls(last.top_share - ago.top_share)}">${sgn(last.top_share - ago.top_share)} <small style="font-size:12px;color:var(--ink-3)">比 20 日前</small></span><span class="dt">前 5 族群</span></div>
        <div class="p-ohlc">前 10 族群 <b>${last.top10_share.toFixed(1)}%</b>　第 1 名 <b>${esc(last.top[0].n)} ${last.top[0].share.toFixed(1)}%</b></div>
        <div class="p-chart" style="height:300px"></div>`;
      body.appendChild(card);
      const c = mkChart($('.p-chart', card));
      c.setOption({ grid: { left: 34, right: 8, top: 14, bottom: 22 }, legend: { show: false },
        xAxis: { type: 'category', data: rows.map(r => r.date.slice(5)), axisLabel: { color: css('--ink-3'), fontSize: 12 }, axisLine: { lineStyle: { color: css('--line-2') } } },
        yAxis: { scale: true, splitNumber: 3, axisLabel: { color: css('--ink-3'), fontSize: 12 }, splitLine: { lineStyle: { color: css('--line') } } },
        series: [{ type: 'line', data: rows.map(r => r.top_share), showSymbol: false, lineStyle: { color: css('--cyan'), width: 1.6 } },
                 { type: 'line', data: rows.map(r => r.top10_share), showSymbol: false, lineStyle: { color: css('--violet'), width: 1.2, type: 'dashed' } }] });
    },
  };

  /* ====================================================================== 剖析圖（手機只留編號）*/
  const DG_LIST = ['foundry', 'hbm', 'silicon_wafer', 'ai_adv_packaging', 'ic_substrate', 'pcb_rigid', 'liquid_cooling', 'server_psu'];
  const DGS = { cur: null, three: null };
  let stockName = {};
  async function pageDg(main) {
    const st = await load('stocks'); stockName = {}; (st || []).forEach(s => { stockName[s.code] = s.name; });
    const slots = window.DiagramSlots;
    const list = DG_LIST.filter(id => slots && slots.name(id));
    let id = LS.get('dg', list[0]); if (!list.includes(id)) id = list[0];
    let mode = LS.get('dgmode', '2d'), zoom = LS.get('dgzoom', 'fit');
    /* 圖名很長（「HBM：堆疊起來的記憶體與底下那顆邏輯晶粒」）：手機的晶片與標題只用冒號前那一段，全名收進「?」*/
    const fullOf = (x) => (slots && slots.name(x)) || x;
    const nameOf = (x) => fullOf(x).split(/[：:]/)[0].trim();
    main.innerHTML = `<div class="p-card" style="padding:8px 10px 10px">
      <div class="p-head"><h3 id="pDgTitle"></h3><span class="p-sp"></span>${qbtn('dg')}</div>
      <div class="p-dgpick p-hsc" id="pDgPick">${list.map(x => `<button type="button" data-id="${x}">${esc(nameOf(x))}</button>`).join('')}</div>
      <div class="p-dgbar"><span class="p-seg2" id="pDgMode"><button type="button" data-m="2d">平面</button><button type="button" data-m="3d">3D</button></span>
        <span class="p-sp" style="flex:1"></span><span class="p-seg2" id="pDgZoom"><button type="button" data-z="fit">整張</button><button type="button" data-z="big">放大</button></span></div>
      <div class="p-dgstage"><div class="p-dgscroll" id="pDgScroll"><div class="dgwrap" id="pDgHost"></div><div class="p-numlayer" id="pNums"></div></div><div class="p-3d" id="p3d" hidden></div></div>
      <div class="p-dghint"><span id="pDgCount"></span><span id="pDgTip">點編號看說明</span></div></div>`;
    const pick = $('#pDgPick');
    pick.addEventListener('scroll', () => pick.classList.toggle('end', pick.scrollLeft + pick.clientWidth >= pick.scrollWidth - 4));
    const paint = () => {
      $$('button', pick).forEach(b => b.classList.toggle('on', b.dataset.id === id));
      $$('#pDgMode button').forEach(b => b.classList.toggle('on', b.dataset.m === mode));
      $$('#pDgZoom button').forEach(b => b.classList.toggle('on', b.dataset.z === zoom));
      $('#pDgZoom').style.visibility = mode === '3d' ? 'hidden' : '';
      $('#pDgTitle').textContent = nameOf(id);
      $('#pDgTip').textContent = mode === '2d' && zoom === 'big' ? '← 左右上下滑看整張 →' : '點編號看說明';
    };
    const draw = async () => {
      closeAll(); paint();
      const scene = slots.scene(id);
      const has3d = !!(scene && window.Rack3D && window.Rack3D.hasScene(scene) && window.Rack3D.supported());
      $('#pDgMode button[data-m="3d"]').disabled = !has3d;
      $('#pDgMode button[data-m="3d"]').style.opacity = has3d ? '' : '.4';
      if (mode === '3d' && !has3d) mode = '2d';
      paint();
      if (DGS.three && DGS.three.dispose) { try { DGS.three.dispose(); } catch (e) { /* 已釋放 */ } }
      DGS.three = null;
      const host = $('#pDgHost'), sc = $('#pDgScroll'), h3 = $('#p3d');
      if (mode === '2d') {
        h3.hidden = true; h3.innerHTML = ''; sc.hidden = false;
        sc.classList.toggle('fit', zoom === 'fit');
        host.innerHTML = slots.draw(id);
        if (window.DG && window.DG.stampParts) window.DG.stampParts(host);
        DGS.cur = { id, info: dgInfo(host, fullOf(id)), items: dgItems(host) };
        requestAnimationFrame(() => requestAnimationFrame(layoutNums));
      } else {
        sc.hidden = true; h3.hidden = false; h3.innerHTML = '';
        DGS.cur = { id, info: { title: fullOf(id), sub: '', notes: [] }, items: [] };
        try {
          DGS.three = await window.Rack3D.mount(h3, scene, { anim: false, color: () => css('--cyan'), members: () => ({ list: [], total: 0 }) });
        } catch (e) { h3.innerHTML = `<div class="p-todo">3D 掛不起來：${esc(e.message)}</div>`; }
        setTimeout(() => { DGS.cur.items = items3d(h3); $('#pDgCount').textContent = `${DGS.cur.items.length} 個編號`; h3.dataset.n = DGS.cur.items.length; if (DGS.three) { DGS.cur.info.sub = DGS.three.sub || ''; loop3d(h3, DGS.three); } }, 900);
      }
    };
    pick.addEventListener('click', (e) => { const b = e.target.closest('button[data-id]'); if (!b) return; id = b.dataset.id; LS.set('dg', id); draw(); });
    $('#pDgMode').addEventListener('click', (e) => { const b = e.target.closest('button[data-m]'); if (!b || b.disabled) return; mode = b.dataset.m; LS.set('dgmode', mode); draw(); });
    $('#pDgZoom').addEventListener('click', (e) => { const b = e.target.closest('button[data-z]'); if (!b) return; zoom = b.dataset.z; LS.set('dgzoom', zoom); $('#pDgScroll').classList.toggle('fit', zoom === 'fit'); paint(); requestAnimationFrame(layoutNums); });
    $('#pNums').addEventListener('click', (e) => { const b = e.target.closest('.p-num'); if (b) openNo(+b.dataset.i); });
    $('#p3d').addEventListener('click', (e) => { const b = e.target.closest && e.target.closest('.p-num'); if (b) openNo(+b.dataset.i); });
    addEventListener('resize', () => requestAnimationFrame(layoutNums));
    draw();
  }
  /* 圖的標題／副標／公式與警語卡：手機不留在畫面上，收進「?」*/
  function dgInfo(host, full) {
    const hd = $('.dghead', host);
    const t = hd ? $$('b,span', hd).map(x => x.textContent.trim()) : [];
    const notes = $$('.dgcards .dgc.note, .dgcards .dgc.warn', host).map(x => x.innerText.replace(/\s+/g, ' ').trim());
    return { title: full || t[0] || '', sub: t.slice(1).join('　'), notes };
  }
  /* 有編號、而且圖上有錨點的卡片 → 一個編號鈕 */
  function dgItems(host) {
    return $$('.dgcards .dgc', host).filter(c => $('.no', c) && c.dataset.anc).map(c => ({
      no: $('.no', c).textContent.trim(), anc: c.dataset.anc,
      title: ($('.bd b', c) || {}).textContent || '', lines: $$('.bd i', c).map(x => x.textContent),
      codes: (c.dataset.codes || '').split(/[,\s]+/).filter(Boolean),
      color: c.style.getPropertyValue('--c') || c.dataset.dgcolor || css('--cyan'),
    })).sort((a, b) => a.no.localeCompare(b.no));
  }
  function items3d(h3) {
    return $$('.lbl3d', h3).map(d => ({ no: d.dataset.dgno, anc: null, title: ($('b', d) || {}).firstChild ? $('b', d).firstChild.textContent : '',
      lines: [($('i', d) || {}).textContent || ''], codes: [], color: d.dataset.dgcolor || css('--cyan'), part: d.dataset.dgpart, el: d })).sort((a, b) => a.no.localeCompare(b.no));
  }
  /* 互相擋到的編號往外推（最多 8 輪），推開的拉一條細引線回原點 —— 2D、3D 共用 */
  function spread(P, MIN) {
    for (let k = 0; k < 8; k++) {
      let moved = false;
      for (let a = 0; a < P.length; a++) for (let b = a + 1; b < P.length; b++) {
        const dx = P[b].x - P[a].x, dy = P[b].y - P[a].y, d = Math.hypot(dx, dy);
        if (d < MIN) { const push = (MIN - d) / 2 + .5, ux = d ? dx / d : (b % 2 ? 1 : -1), uy = d ? dy / d : 0;
          P[a].x -= ux * push; P[a].y -= uy * push; P[b].x += ux * push; P[b].y += uy * push; moved = true; }
      }
      if (!moved) break;
    }
    let ov = 0; for (let a = 0; a < P.length; a++) for (let b = a + 1; b < P.length; b++) if (Math.hypot(P[b].x - P[a].x, P[b].y - P[a].y) < MIN - 2) ov++;
    return ov;
  }
  const leaders = (P) => P.filter(p => Math.hypot(p.x - p.x0, p.y - p.y0) > 8)
    .map(p => `<path d="M${p.x0.toFixed(1)},${p.y0.toFixed(1)}L${p.x.toFixed(1)},${p.y.toFixed(1)}" stroke="${p.c}" stroke-width="1.2" fill="none" opacity=".8"/><circle cx="${p.x0.toFixed(1)}" cy="${p.y0.toFixed(1)}" r="2.5" fill="${p.c}"/>`).join('');
  /* 3D：編號跟著相機轉，所以每一格畫面重排一次（只在 3D 開著、頁面看得到時跑）。
     站上 three3d.js 的 .ld-no 編號圓點會互相疊住（HBM 那張 8 個疊成 4 堆），手機改由這一層接手。*/
  function loop3d(h3, view) {
    let layer = $('.p-num3', h3);
    if (!layer) { layer = document.createElement('div'); layer.className = 'p-numlayer p-num3'; layer.style.inset = '0'; h3.appendChild(layer); }
    const tick = () => {
      if (DGS.three !== view || !h3.isConnected || h3.hidden) return;
      const base = h3.getBoundingClientRect();
      const P = DGS.cur.items.map((it, i) => { const q = view.pointOf && view.pointOf(it.part); if (!q) return null;
        const x = q.x - base.left, y = q.y - base.top; return { i, x, y, x0: x, y0: y, c: it.color, back: !q.front }; }).filter(Boolean);
      const ov = spread(P, 30);
      P.forEach(q => { q.x = Math.max(15, Math.min(base.width - 15, q.x)); q.y = Math.max(15, Math.min(base.height - 15, q.y)); });
      layer.innerHTML = `<svg width="${base.width}" height="${base.height}" style="position:absolute;left:0;top:0;overflow:visible">${leaders(P)}</svg>`
        + P.map(p => { const it = DGS.cur.items[p.i]; return `<button type="button" class="p-num${DGS.selNo === it.no ? ' on' : ''}" data-i="${p.i}" style="left:${p.x.toFixed(1)}px;top:${p.y.toFixed(1)}px;--c:${it.color}${p.back ? ';opacity:.55' : ''}" aria-label="編號 ${it.no}：${esc(it.title)}">${it.no}</button>`; }).join('');
      layer.dataset.overlap = ov; layer.dataset.n = P.length;
      setTimeout(() => requestAnimationFrame(tick), 60);
    };
    requestAnimationFrame(tick);
  }
  /* 編號鈕的位置：量錨點的螢幕座標 → 換成捲動容器內的座標。互相擋到就往外推（最多 6 輪）*/
  function layoutNums() {
    const cur = DGS.cur; const layer = $('#pNums'), sc = $('#pDgScroll'); if (!cur || !layer || !sc || sc.hidden) return;
    const base = sc.getBoundingClientRect();
    const pos = cur.items.map((it, i) => {
      const a = $(`g.anc[data-for="${CSS.escape(it.anc)}"] .anchor`, sc) || $(`g.anc[data-for="${CSS.escape(it.anc)}"]`, sc);
      if (!a) return null;
      const r = a.getBoundingClientRect();
      const x = r.left + r.width / 2 - base.left + sc.scrollLeft, y = r.top + r.height / 2 - base.top + sc.scrollTop;
      return { i, x, y, x0: x, y0: y, c: it.color };
    });
    const P = pos.filter(Boolean);
    const ovAfter = spread(P, 30);
    /* 推開之後可能被推出畫面邊緣：夾回容器內（留 15px，編號鈕半徑 14）*/
    P.forEach(q => { q.x = Math.max(15, Math.min(sc.scrollWidth - 15, q.x)); q.y = Math.max(15, Math.min(sc.scrollHeight - 15, q.y)); });
    layer.style.width = sc.scrollWidth + 'px'; layer.style.height = sc.scrollHeight + 'px';
    layer.innerHTML = `<svg width="${sc.scrollWidth}" height="${sc.scrollHeight}" style="position:absolute;left:0;top:0">${leaders(P)}</svg>` + P.map(p => { const it = cur.items[p.i];
      return `<button type="button" class="p-num" data-i="${p.i}" style="left:${p.x.toFixed(1)}px;top:${p.y.toFixed(1)}px;--c:${it.color}" aria-label="編號 ${it.no}：${esc(it.title)}">${it.no}</button>`; }).join('');
    $('#pDgCount').textContent = `${P.length} 個編號`;
    layer.dataset.overlap = ovAfter; layer.dataset.n = P.length;
  }
  function openNo(k) {
    const cur = DGS.cur; if (!cur || !cur.items[k]) return;
    const it = cur.items[k], n = cur.items.length;
    const chips = it.codes.length ? it.codes.slice(0, 8).map(c => `<a href="#stock/${c}" data-soon="個股頁">${esc(stockName[c] || c)} ${c}</a>`).join('')
      : (cur.id && DGS.three ? '' : '<span class="none">台股無直接對應</span>');
    const sh = showSheet(`<div class="p-shhead" style="--c:${it.color}"><span class="no">${it.no}</span><b>${esc(it.title)}</b></div>
      <div class="p-shbody">${it.lines.map(l => `<i>${esc(l)}</i>`).join('')}</div>${chips ? `<div class="p-chips">${chips}</div>` : ''}
      <div class="p-shnav"><button type="button" data-d="-1" aria-label="上一個編號">‹</button><span>${it.no} / ${String(n).padStart(2, '0')}</span><button type="button" data-d="1" aria-label="下一個編號">›</button></div>`,
      () => { DGS.selNo = null; $$('.p-num.on').forEach(b => b.classList.remove('on')); });
    sh.dataset.no = it.no; DGS.selNo = it.no;
    $$('.p-num').forEach(b => b.classList.toggle('on', +b.dataset.i === k));
    $$('.p-shnav button', sh).forEach(b => b.onclick = (e) => { e.stopPropagation(); openNo((k + (+b.dataset.d) + n) % n); });
    /* 抽屜會蓋住下半部：被選的編號如果落在抽屜底下，把整頁捲上來讓它露出來 */
    const btn = $(`#pNums .p-num[data-i="${k}"]`) || $(`#p3d .p-num[data-i="${k}"]`);
    if (btn) {
      const r = btn.getBoundingClientRect(), top = innerHeight - sh.offsetHeight - 16;
      if (r.bottom > top) scrollBy({ top: r.bottom - top + 8, behavior: 'instant' });
      else if (r.top < 60) scrollBy({ top: r.top - 70, behavior: 'instant' });
      const sc = $('#pDgScroll');
      if (sc && !sc.classList.contains('fit')) { const b0 = sc.getBoundingClientRect(); if (r.left < b0.left + 20 || r.right > b0.right - 20) sc.scrollLeft += r.left - (b0.left + b0.width / 2); }
    }
  }

  /* ====================================================================== 路由 */
  const PAGES = { ov: pageOv, flow: pageFlow, dg: pageDg };
  function route() {
    const h = (location.hash || '#ov').slice(1).split('/')[0];
    const k = PAGES[h] ? h : 'ov';
    $$('#pNav button').forEach(b => b.classList.toggle('on', b.dataset.go === k));
    killCharts(); closeAll();
    if (DGS.three && DGS.three.dispose) { try { DGS.three.dispose(); } catch (e) { /* 已釋放 */ } DGS.three = null; }
    const main = $('#pMain'); main.innerHTML = ''; scrollTo(0, 0);
    PAGES[k](main);
  }
  $('#pNav').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-go]'); if (!b) return;
    if (PAGES[b.dataset.go]) location.hash = '#' + b.dataset.go;
    else showSheet(`<div class="p-shhead"><b>${b.textContent.trim()}</b></div><div class="p-shbody">原型只做總覽、資金流向、產業（剖析圖）三頁。${b.dataset.go === 'more' ? '「更多」裡放市場明細、週期統計、交付清單、今日事件、主題與設定（見規格 §2）。' : '熱力圖頁的版面見規格 §3-5。'}</div>`);
  });
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('[data-soon]'); if (!a || a.closest('#pNav')) return;
    e.preventDefault();
    showSheet(`<div class="p-shhead"><b>${esc(a.dataset.soon)}</b></div><div class="p-shbody">原型不含這一頁；上線版沿用站上現有的「${esc(a.dataset.soon)}」。</div>`);
  });
  addEventListener('hashchange', route);
  addEventListener('resize', () => charts.forEach(c => c.resize()));
  route();
  window.__proto = { DGS, layoutNums };
})();
