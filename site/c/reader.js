/* 頻道獨立閱讀站（site/c/<頻道>/index.html 共用）：讀 site/articles/<頻道>/ 同一份資料，不複製文章。
   路由：#/ 清單、#/<文章 id> 內文。登入共用主站（同網域 localStorage，account.js）；追蹤解鎖規則同主站：
   單篇連結任何人可讀；頻道清單＝站主或帳號已解鎖該頻道（unlock.js 的 TwUnlock）。 */
(function () {
  'use strict';
  const CH = window.CH, ROOT = '../../', DIR = ROOT + 'articles/' + CH.id + '/';
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const okId = (s) => /^[\w-]{3,80}$/.test(s);
  const okUrl = (u) => /^(https:\/\/|media\/|articles\/)/.test(String(u || '')) ? String(u) : '';
  const rel = (u) => (/^https:/.test(u) ? u : ROOT + u);
  const user = () => { try { return window.TwAccount && TwAccount.user && TwAccount.user(); } catch (e) { return null; } };
  const member = () => { const u = user(); return !!(u && (u.email || u.name || u.admin)); };
  const admin = () => { const u = user(); return !!(u && u.admin); };
  const unlocked = () => { try { return !!(window.TwUnlock && TwUnlock.has(CH.id)); } catch (e) { return false; } };
  const canList = () => admin() || (member() && unlocked());
  const getJ = (u) => fetch(u, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
  const login = () => { try { window.TwAccount && TwAccount.login && TwAccount.login(); } catch (e) { /* 帳號功能沒開 */ } };
  const app = $('#app');

  const block = (b) => {
    if (!b) return '';
    switch (b.t) {
      case 'h': return `<h2>${esc(b.text)}</h2>`;
      case 'p': return `<p>${esc(b.text)}</p>`;
      case 'lead': return `<p class="lead">${esc(b.text)}</p>${b.more ? `<p>${esc(b.more)}</p>` : ''}`;
      case 'sum': return `<aside class="sum"><h2>${esc(b.title || '3 個重點')}</h2><ol>${(b.items || []).map((x) => `<li>${esc(x)}</li>`).join('')}</ol></aside>`;
      case 'term': return `<aside class="term"><h3>${esc(b.title || '名詞解釋')}</h3><dl>${(b.items || []).map((x) => `<dt>${esc(x.k)}</dt><dd>${esc(x.v)}</dd>`).join('')}</dl></aside>`;
      case 'prompt': return `<div class="pr"><div class="prh"><b>${esc(b.title || '提示詞')}</b><button class="btn" type="button" data-pcopy>複製這段</button></div><pre class="prt">${esc(b.text)}</pre>${b.note ? `<div class="prn">${esc(b.note)}</div>` : ''}</div>`;
      case 'callout': return `<div class="callout">${esc(b.text)}</div>`;
      case 'ul': return `<ul>${(b.items || []).map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
      case 'steps': return `${b.title ? `<h2>${esc(b.title)}</h2>` : ''}<ol class="st">${(b.items || []).map((x) => `<li><b>${esc(x.label)}</b>${x.text ? '：' + esc(x.text) : ''}</li>`).join('')}</ol>${b.note ? `<p class="n">${esc(b.note)}</p>` : ''}`;
      case 'table': return `<div class="tw"><table><thead><tr>${(b.head || []).map((x) => `<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${(b.rows || []).map((r) => `<tr>${r.map((x, i) => `<td data-l="${esc((b.head || [])[i] || '')}">${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      case 'img': return `<div class="imgs c${Math.min((b.items || []).length, 3)}${b.wide ? ' wide' : ''}">${(b.items || []).map((x) => okUrl(x.src) ? `<figure><div class="fz"><img src="${esc(rel(x.src))}" alt="${esc(x.alt)}" loading="lazy" data-zoom="1" tabindex="0" role="button" aria-label="${esc((x.alt || '圖') + '，點一下放大')}"></div><span class="zh">點圖可放大</span>${x.cap ? `<figcaption>${esc(x.cap)}</figcaption>` : ''}</figure>` : '').join('')}</div>`;
      case 'links': return `${b.title ? `<h2>${esc(b.title)}</h2>` : ''}<ul>${(b.items || []).map((x) => (/^https:\/\//.test(x.url || '') ? `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label)}</a></li>` : '')).join('')}</ul>`;
      case 'mp4': {
        const s = okUrl(b.src); if (!s) return '';
        const p = okUrl(b.poster);
        return `<div class="vid"><video controls playsinline preload="metadata" src="${esc(rel(s))}"${p ? ` poster="${esc(rel(p))}"` : ''}></video>${b.note ? `<div class="n">${esc(b.note)}</div>` : ''}<a class="btn" href="${esc(rel(s))}" download>下載影片 ⬇</a></div>`;
      }
      default: return '';
    }
  };
  const tail = (d) => {
    const rel2 = (d.related || []).filter((x) => okId(x.id));
    const src = d.sources || [];
    return (rel2.length ? `<section class="more"><h2>延伸閱讀</h2>${rel2.map((x) => `<a class="card" href="#/${encodeURIComponent(x.id)}"><span class="tx"><h3>${esc(x.title)}</h3><p>${esc(x.why || '')}</p></span></a>`).join('')}</section>` : '')
      + (src.length ? `<section class="srcs"><h2>出處與查證</h2><ol>${src.map((x) => `<li>${esc(x.title)}<span>${esc([x.publisher, x.date].filter(Boolean).join('，'))}</span></li>`).join('')}</ol>${d.confidence ? `<p class="n">可信度：${esc(d.confidence)}</p>` : ''}</section>` : '');
  };
  const banner = () => {
    if (admin()) return '';
    if (unlocked() && member()) return `<div class="bn ok" id="bn" data-st="ok"><span>已解鎖「${esc(CH.name)}」全部文章</span><a class="btn" href="#/">看全部文章</a></div>`;
    if (!member()) return `<div class="bn" id="bn" data-st="guest"><span>這是「${esc(CH.name)}」的單篇分享，只能看這一篇。<b>註冊並追蹤頻道，即可看全部文章。</b></span><button class="btn fill" id="lg" type="button">登入／註冊</button></div>`;
    return `<div class="bn" id="bn" data-st="nogate"><span>已登入，但這個帳號還沒解鎖「${esc(CH.name)}」全部文章。追蹤頻道、留言關鍵字後，用私訊裡的解鎖連結打開一次，就會記在你的帳號。</span></div>`;
  };
  const thumbOf = (d) => { for (const b of d.blocks || []) { if (b.t === 'mp4' && okUrl(b.poster)) return rel(b.poster); if (b.t === 'img' && b.items && b.items[0] && okUrl(b.items[0].src)) return rel(b.items[0].src); } return ''; };
  /* 發文包（只有站主看得到）：資料 postkit.json 由 scripts/postkit_build.py 產生；非站主連請求都不送 */
  let kitP = null;
  const kits = () => (kitP = kitP || getJ(DIR + 'postkit.json').then((j) => j.kits || []).catch(() => []));
  const ST_C = { '已發': '✅', '已排程': '🕒', '存貨': '📦' };
  const kitHtml = (k, withTitle) => `<div class="kit1" data-key="${esc(k.key)}">${withTitle ? `<div class="kt"><b>${esc(k.title)}</b><span class="kst" data-st="${esc(k.status)}">${ST_C[k.status] || ''} ${esc(k.status)}${k.publish_at ? '　' + esc(k.publish_at.replace('T', ' ').slice(0, 16)) : ''}</span></div>` : ''}<div class="kb">${(k.files || []).map((f) => `<a class="btn" href="${esc(rel(f.url))}" download>${esc(f.label)} ⬇</a>`).join('')}<button class="btn" type="button" data-copy="ig">複製 IG 文案</button><button class="btn" type="button" data-copy="th">複製 Threads 文案</button></div><textarea class="kc" readonly rows="6" aria-label="貼文文案">${esc(k.caption)}</textarea></div>`;
  async function mountKit(id) {
    if (!admin()) return;
    const ks = (await kits()).filter((k) => k.article === id); if (!ks.length) return;
    const art = app.querySelector('.art'); if (!art || document.getElementById('kit')) return;
    const el = document.createElement('section'); el.className = 'kit'; el.id = 'kit';
    el.innerHTML = '<h2>發文包（只有站主看得到）</h2>' + ks.map((k) => kitHtml(k, true)).join('');
    art.appendChild(el);
  }
  async function mountKitAll() {
    if (!admin()) return;
    const ks = await kits(); if (!ks.length || document.getElementById('kitAll')) return;
    const el = document.createElement('section'); el.className = 'kit'; el.id = 'kitAll';
    el.innerHTML = `<h2>發文包總覽（只有站主看得到）</h2><p class="sub">共 ${ks.length} 組；狀態：✅ 已發、🕒 已排程、📦 存貨（未排程）。</p>` + ks.slice().sort((a, b) => String(b.publish_at).localeCompare(String(a.publish_at))).map((k) => kitHtml(k, true)).join('');
    app.appendChild(el);
  }
  document.addEventListener('click', (e) => {
    const pb = e.target && e.target.closest && e.target.closest('[data-pcopy]');
    if (pb) {
      const t = pb.closest('.pr').querySelector('.prt').textContent;
      const ok = () => { pb.textContent = '已複製 ✓'; setTimeout(() => { pb.textContent = '複製這段'; }, 2000); };
      const fb = () => { try { const r = document.createRange(); r.selectNodeContents(pb.closest('.pr').querySelector('.prt')); const sl = getSelection(); sl.removeAllRanges(); sl.addRange(r); pb.textContent = '請按 Ctrl+C'; } catch (er) { /* 略 */ } };
      try { navigator.clipboard.writeText(t).then(ok, fb); } catch (er) { fb(); }
      return;
    }
    const b = e.target && e.target.closest && e.target.closest('[data-copy]'); if (!b) return;
    const ta = b.closest('.kit1').querySelector('textarea'); const t = ta.value;
    try { navigator.clipboard.writeText(t).then(() => { b.dataset.done = '1'; b.textContent = '已複製 ✓'; }, () => { ta.select(); b.textContent = '請按 Ctrl+C'; }); } catch (er) { ta.select(); b.textContent = '請按 Ctrl+C'; }
  });
  async function list() {
    document.title = CH.name;
    app.innerHTML = '<p class="sub">載入中…</p>';
    let j; try { j = await getJ(DIR + 'index.json'); } catch (e) { app.innerHTML = '<p class="sub">文章清單暫時讀不到，請稍後再試。</p>'; return; }
    const a = (j.articles || []).filter((x) => okId(x.id)).sort((x, y) => String(y.date).localeCompare(String(x.date)));
    const open = canList();
    const gate = open ? '' : `<div class="gate" id="gate"><span>下面是「${esc(CH.name)}」的文章。<b>註冊並追蹤頻道</b>，用私訊裡的解鎖連結打開一次，就能看全部；沒解鎖的只能看私訊連結給你的那一篇。</span>${member() ? '' : '<button class="btn fill" id="lg" type="button">登入／註冊</button>'}</div>`;
    app.innerHTML = `<h1>${esc(CH.name)}</h1><p class="sub">${esc(CH.tag)}　共 ${a.length} 篇</p>${gate}<div class="cards" id="list">${a.map((x) => `<a class="card${open ? '' : ' lk'}" href="${open ? '#/' + encodeURIComponent(x.id) : '#/'}" data-id="${esc(x.id)}"${open ? '' : ' data-lock="1"'}><span class="th" data-th="${esc(x.id)}"></span><span class="tx"><h3>${esc(x.title)}</h3><div class="m">${esc(x.date)}　閱讀約 ${esc(x.reading_min || 1)} 分鐘</div></span>${open ? '' : '<span class="lkc" aria-label="未解鎖">🔒</span>'}</a>`).join('')}</div>`;
    /* 封面縮圖：每篇內文 JSON 的 mp4 封面或第一張圖；晚到就補上，不擋清單 */
    mountKitAll();
    a.forEach((x) => getJ(DIR + encodeURIComponent(x.id) + '.json').then((d) => { const u = thumbOf(d), el = app.querySelector(`.th[data-th="${CSS.escape(x.id)}"]`); if (u && el) el.style.backgroundImage = `url("${u}")`; }).catch(() => {}));
  }
  async function post(id) {
    app.innerHTML = '<p class="sub">載入中…</p>';
    let d; try { d = await getJ(DIR + encodeURIComponent(id) + '.json'); } catch (e) { app.innerHTML = '<p class="sub">找不到這篇文章。</p><a class="btn" href="#/">回文章列表</a>'; return; }
    document.title = d.title + '｜' + CH.name;
    app.innerHTML = `<article class="art"><a class="back" href="#/" id="bk">← ${canList() ? '全部文章' : esc(CH.name)}</a><h1>${esc(d.title)}</h1><div class="meta">${esc(d.date)}　閱讀約 ${esc(d.reading_min || 1)} 分鐘</div><div class="tags">${(d.tags || []).map((t) => `<span>${esc(t)}</span>`).join('')}</div>${banner()}${(d.blocks || []).map(block).join('')}${tail(d)}</article>`;
    window.scrollTo(0, 0);
    mountKit(id);
    mountToc(); fitSvgs();
    try { window.TwArtM && TwArtM.open(id, CH.id, app.querySelector('.art .meta')); } catch (e) { /* 觀測失敗不影響閱讀 */ }
  }
  /* ---- 手機閱讀工具：目錄抽屜、回頂端、圖片全螢幕放大（可縮放）---- */
  let fabs = null;
  const unmountFabs = () => { if (fabs) { fabs.remove(); fabs = null; } const s = document.getElementById('tocSheet'); if (s) s.remove(); };
  function mountToc() {
    unmountFabs();
    const hh = [...app.querySelectorAll('.art > h2')];
    hh.forEach((h, i) => { h.id = 'sec' + i; });
    fabs = document.createElement('div'); fabs.className = 'fabs';
    fabs.innerHTML = (hh.length ? '<button type="button" class="fab" id="tocBtn" aria-expanded="false" aria-controls="tocSheet">☰ 目錄</button>' : '') + '<button type="button" class="fab top" id="topBtn" aria-label="回到頂端" hidden>↑</button>';
    document.body.appendChild(fabs);
    if (hh.length) {
      const sh = document.createElement('div'); sh.id = 'tocSheet'; sh.className = 'tocs'; sh.hidden = true;
      sh.innerHTML = '<div class="tocb"><div class="toch"><b>目錄</b><button type="button" class="btn" id="tocX">關閉</button></div><ol>' + hh.map((h, i) => `<li><a href="#sec${i}" data-sec="sec${i}">${esc(h.textContent)}</a></li>`).join('') + '</ol></div>';
      document.body.appendChild(sh);
    }
    onScroll();
  }
  const onScroll = () => { const t = document.getElementById('topBtn'); if (t) t.hidden = window.scrollY < 500; };
  window.addEventListener('scroll', onScroll, { passive: true });
  /* SVG 圖表：依圖內最小字級算出「手機上字不小於 13px」所需的寬度，窄螢幕就橫向滑動，不縮到看不見 */
  const svgW = {};
  function fitSvgs() {
    app.querySelectorAll('.fz img[src$=".svg"]').forEach((im) => {
      const u = im.getAttribute('src');
      (svgW[u] = svgW[u] || fetch(u).then((r) => r.text()).then((t) => {
        const vb = (t.match(/viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"/) || []);
        const fs = (t.match(/font-size="([\d.]+)"/g) || []).map((x) => parseFloat(x.replace(/[^\d.]/g, ''))).filter((x) => x > 0);
        const w = parseFloat(vb[1]) || 800, mn = fs.length ? Math.min(...fs) : 18;
        return Math.min(Math.round(w * 13.5 / mn), 1100);
      }).catch(() => 780)).then((w) => { im.style.setProperty('--mw', w + 'px'); const fz = im.closest('.fz'); if (w > fz.clientWidth + 4) fz.dataset.svg = '1'; });
    });
  }
  let lb = null;
  function closeLb() { if (lb) { lb.remove(); lb = null; document.documentElement.classList.remove('lbo'); } }
  function openLb(im) {
    closeLb();
    lb = document.createElement('div'); lb.className = 'lb'; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-label', '圖片放大檢視');
    const cap = im.closest('figure') && im.closest('figure').querySelector('figcaption');
    lb.innerHTML = '<div class="lbt"><button type="button" class="btn" data-z="-">－</button><button type="button" class="btn" data-z="0">符合寬度</button><button type="button" class="btn" data-z="+">＋</button><span class="sp"></span><button type="button" class="btn fill" data-z="x">關閉</button></div><div class="lbs"><img alt=""></div><div class="lbc"></div>';
    const g = lb.querySelector('img'); g.src = im.currentSrc || im.src; g.alt = im.alt;
    lb.querySelector('.lbc').textContent = (cap ? cap.textContent : im.alt) + '　（兩指可縮放、單指拖曳）';
    document.body.appendChild(lb); document.documentElement.classList.add('lbo');
    const sc = lb.querySelector('.lbs'); let w = 0, base = 0;
    const fit = () => { base = sc.clientWidth; return base; };
    const setW = (nw, cx, cy) => {
      nw = Math.max(base, Math.min(base * 5, nw)); const r = nw / (w || nw);
      const ox = sc.scrollLeft + cx, oy = sc.scrollTop + cy; w = nw; g.style.width = w + 'px';
      sc.scrollLeft = ox * r - cx; sc.scrollTop = oy * r - cy;
    };
    fit(); w = base; g.style.width = base + 'px';
    lb.addEventListener('click', (e) => { const z = e.target.dataset && e.target.dataset.z; if (!z) return; const cx = sc.clientWidth / 2, cy = sc.clientHeight / 2;
      if (z === 'x') closeLb(); else if (z === '0') setW(base, cx, cy); else setW(w * (z === '+' ? 1.5 : 1 / 1.5), cx, cy); });
    sc.addEventListener('dblclick', (e) => { const r = sc.getBoundingClientRect(); setW(w > base * 1.2 ? base : base * 2.5, e.clientX - r.left, e.clientY - r.top); });
    sc.addEventListener('wheel', (e) => { if (!e.ctrlKey && !e.metaKey) return; e.preventDefault(); const r = sc.getBoundingClientRect(); setW(w * (e.deltaY < 0 ? 1.15 : 1 / 1.15), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
    let d0 = 0, w0 = 0;   // 兩指縮放
    const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    sc.addEventListener('touchstart', (e) => { if (e.touches.length === 2) { d0 = dist(e.touches); w0 = w; } }, { passive: true });
    sc.addEventListener('touchmove', (e) => { if (e.touches.length === 2 && d0) { e.preventDefault(); const r = sc.getBoundingClientRect(); setW(w0 * dist(e.touches) / d0, (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left, (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top); } }, { passive: false });
    sc.addEventListener('touchend', () => { d0 = 0; });
    lb.querySelector('[data-z="x"]').focus();
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeLb(); const s = document.getElementById('tocSheet'); if (s) s.hidden = true; }
    if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.dataset && e.target.dataset.zoom) { e.preventDefault(); openLb(e.target); }
  });
  document.addEventListener('click', (e) => {
    const t = e.target; if (!t || !t.closest) return;
    const im = t.closest('img[data-zoom]'); if (im) { openLb(im); return; }
    if (t.closest('#tocBtn')) { const s = document.getElementById('tocSheet'); s.hidden = !s.hidden; t.closest('#tocBtn').setAttribute('aria-expanded', String(!s.hidden)); return; }
    if (t.closest('#tocX')) { document.getElementById('tocSheet').hidden = true; return; }
    const a = t.closest('a[data-sec]'); if (a) { e.preventDefault(); document.getElementById('tocSheet').hidden = true; const h = document.getElementById(a.dataset.sec); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    if (t.closest('#topBtn')) { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    if (t.id === 'tocSheet') t.hidden = true;
  });
  function route() {
    closeLb(); unmountFabs();
    const h = (location.hash || '').replace(/^#\/?/, '');
    if (h && okId(decodeURIComponent(h))) post(decodeURIComponent(h)); else list();
  }
  document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'lg') login();
    const k = e.target && e.target.closest && e.target.closest('a.card[data-lock]');
    if (k) { e.preventDefault(); if (!member()) login(); else { const g = document.getElementById('gate'); if (g) g.scrollIntoView({ block: 'center', behavior: 'smooth' }); } }   // 沒解鎖：未登入→登入視窗；已登入→捲到說明
  });
  window.addEventListener('hashchange', route);
  /* 登入／解鎖狀態變了才重畫（兌換是非同步，會晚到）*/
  let t; const again = () => { clearTimeout(t); t = setTimeout(route, 80); };
  window.addEventListener('tw:account', again);
  window.addEventListener('tw:chunl', again);
  route();
})();
