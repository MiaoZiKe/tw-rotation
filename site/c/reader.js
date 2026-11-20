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
  const app = $('#app'), SC = $('#scr');   // 捲動容器：版面固定成「頁首／可捲內容／底部工具列」三段，工具列不蓋內文

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
      case 'steps': return `${b.title ? `<h2 class="stt">${esc(b.title)}</h2>` : ''}<ol class="st">${(b.items || []).map((x) => `<li><span><b>${esc(x.label)}</b>${x.text ? '：' + esc(x.text) : ''}</span></li>`).join('')}</ol>${b.note ? `<p class="n">${esc(b.note)}</p>` : ''}`;
      case 'table': return `<div class="tw"><table><thead><tr>${(b.head || []).map((x) => `<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${(b.rows || []).map((r) => `<tr>${r.map((x, i) => `<td data-l="${esc((b.head || [])[i] || '')}"${i && /^[\d,.\-+−%\s]+[^\d\s]{0,3}$/.test(String(x)) ? ' class="nu"' : ''}>${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      case 'img': return `<div class="imgs c${Math.min((b.items || []).length, 3)}${b.wide ? ' wide' : ''}">${(b.items || []).map((x) => { if (!okUrl(x.src)) return ''; const sv = /\.svg(\?|$)/.test(x.src);
        return `<figure class="${sv ? 'fs' : 'fj'}"><div class="fz"><img src="${esc(rel(x.src))}" alt="${esc(x.alt)}" loading="lazy" data-zoom="1" tabindex="0" role="button" aria-label="${esc((x.alt || '圖') + '，點一下放大')}">${sv ? '' : '<span class="zm" aria-hidden="true">點開放大</span>'}</div>${sv ? '<span class="zh">點圖可放大</span>' : ''}${x.cap ? `<figcaption>${esc(x.cap)}</figcaption>` : ''}</figure>`; }).join('')}</div>`;
      case 'links': return `${b.title ? `<h2>${esc(b.title)}</h2>` : ''}<ul>${(b.items || []).map((x) => (/^https:\/\//.test(x.url || '') ? `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label)}</a></li>` : '')).join('')}</ul>`;
      case 'mp4': {
        const s = okUrl(b.src); if (!s) return '';
        const p = okUrl(b.poster);
        return `<div class="vid"><div class="pv"><video controls playsinline preload="metadata" src="${esc(rel(s))}"${p ? ` poster="${esc(rel(p))}"` : ''}></video></div><div class="bar"><div class="acts"><button class="btn fill" type="button" data-vplay>▶ 播放</button><a class="btn" href="${esc(rel(s))}" download>下載 MP4</a></div>${b.note ? `<div class="nt">${esc(b.note)}</div>` : ''}</div></div>`;
      }
      default: return '';
    }
  };
  const tail = (d) => {
    const rel2 = (d.related || []).filter((x) => okId(x.id));
    const src = d.sources || [];
    return (rel2.length ? `<section class="more"><h2>延伸閱讀</h2><div class="rel">${rel2.map((x) => `<a href="#/${encodeURIComponent(x.id)}"><b>${esc(x.title)}</b>${x.why ? `<span>${esc(x.why)}</span>` : ''}</a>`).join('')}</div></section>` : '')
      + (src.length ? `<details class="srcs"><summary>出處與資料說明（${src.length}）</summary><ol>${src.map((x) => `<li>${esc(x.title)}<span>${esc([x.publisher, x.date].filter(Boolean).join('，'))}</span></li>`).join('')}</ol>${d.confidence ? `<p class="n">可信度：${esc(d.confidence)}</p>` : ''}</details>` : '');
  };
  const banner = () => {
    if (admin()) return '';
    if (unlocked() && member()) return '';   // 已解鎖：頁首「已追蹤」已經說明，不再佔文章第一屏
    if (!member()) return `<div class="bn" id="bn" data-st="guest"><span>這是「${esc(CH.name)}」的單篇分享，只能看這一篇。<b>註冊並追蹤頻道，即可看全部文章。</b></span><button class="btn fill" id="lg" type="button">登入／註冊</button></div>`;
    return `<div class="bn" id="bn" data-st="nogate"><span>已登入，但這個帳號還沒解鎖「${esc(CH.name)}」全部文章。追蹤頻道、留言關鍵字後，用私訊裡的解鎖連結打開一次，就會記在你的帳號。</span></div>`;
  };
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
  /* 列表封面：談晴說礙＝「大數字磚」，數字取自文章標題（% > 成 > 元 > 年 > 第一個數字），小字取第二個標籤；
     標題裡沒有數字就退回漸層＋LOGO，不自己編。CaffAIne＝品牌漸層＋杯子線稿，不放貼文圖當封面（Andy 11-20 決定）。 */
  const bigNum = (t) => { for (const re of [/\d[\d,]*(?:\.\d+)?\s?%/, /\d[\d,]*(?:\.\d+)?\s?成/, /\d[\d,]*(?:\.\d+)?\s?元/, /\d[\d,]*(?:\.\d+)?\s?年/, /\d[\d,]*(?:\.\d+)?/]) { const m = String(t || '').match(re); if (m) return m[0].replace(/\s/g, ''); } return ''; };
  const CUP = '<svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 14h20v9a9 9 0 0 1-9 9h-2a9 9 0 0 1-9-9z"/><path d="M27 17h3a4 4 0 0 1 0 8h-3"/><path d="M13 6c-1 2 1 3 0 5M19 6c-1 2 1 3 0 5"/></svg>';
  const topic = (x) => (x.tags || []).filter((t) => t !== CH.name)[0] || '';
  const tile = (x) => {
    if (CH.id === 'healing') { const n = bigNum(x.title); if (n) return `<div class="th"><div class="num${n.length > 5 ? ' s' : ''}">${esc(n)}${topic(x) ? `<small>${esc(topic(x))}</small>` : ''}</div></div>`; }
    return `<div class="th g">${CUP}</div>`;
  };
  const cover = (x) => {
    const n = CH.id === 'healing' ? bigNum(x.title) : '';
    return `<div class="cv">${n ? `<div><span class="pill">${esc(topic(x) || '最新一篇')}</span><div class="bg">${esc(n)}</div></div>` : `<span class="pill">${esc(topic(x) || '最新一篇')}</span>`}${n ? '' : `<span class="ic">${CUP}</span>`}</div>`;
  };
  async function list() {
    document.title = CH.name;
    app.innerHTML = '<p class="sub">載入中…</p>';
    let j; try { j = await getJ(DIR + 'index.json'); } catch (e) { app.innerHTML = '<p class="sub">文章清單暫時讀不到，請稍後再試。</p>'; return; }
    const a = (j.articles || []).filter((x) => okId(x.id)).sort((x, y) => String(y.date).localeCompare(String(x.date)));
    const open = canList();
    const mins = a.map((x) => x.reading_min).filter(Boolean);
    const span = mins.length ? `；每篇約 ${Math.min(...mins)}${Math.min(...mins) === Math.max(...mins) ? '' : '～' + Math.max(...mins)} 分鐘` : '';
    const gate = open ? '' : `<div class="gate" id="gate"><span>追蹤頻道，用私訊裡的解鎖連結打開一次，就能看全部文章</span>${member() ? '' : '<button class="btn fill" id="lg" type="button">登入</button>'}</div>`;
    /* 分類 chip：用文章自己的標籤，同一個標籤出現在 2 篇以上才列（最多 5 個），數字是實際篇數 */
    const cnt = {}; a.forEach((x) => (x.tags || []).forEach((t) => { if (t !== CH.name) cnt[t] = (cnt[t] || 0) + 1; }));
    const tags = Object.keys(cnt).filter((t) => cnt[t] >= 2).sort((p, q) => cnt[q] - cnt[p]).slice(0, 5);
    const lk = open ? '' : ' lk';
    const href = (x) => (open ? '#/' + encodeURIComponent(x.id) : '#/');
    const dat = (x) => `data-id="${esc(x.id)}" data-tags="${esc((x.tags || []).join('|'))}"${open ? '' : ' data-lock="1"'}`;
    const f = a[0], rest = a.slice(1);
    app.innerHTML = `<section class="hero"><div class="hi"><h1>${esc(CH.tag)}</h1><p>共 ${a.length} 篇${span}</p>${gate}</div></section><div class="lw">`
      + `<nav class="chips" aria-label="文章分類"><button class="chip" type="button" data-chip="" aria-pressed="true">全部 ${a.length}</button>${tags.map((t) => `<button class="chip" type="button" data-chip="${esc(t)}" aria-pressed="false">${esc(t)} ${cnt[t]}</button>`).join('')}</nav>`
      + (f ? `<a class="feat${lk}" href="${href(f)}" ${dat(f)}>${cover(f)}<div class="tx"><h2>${esc(f.title)}</h2><div class="m">${esc(f.date)}・閱讀約 ${esc(f.reading_min || 1)} 分鐘</div></div>${open ? '' : '<span class="lkc" aria-label="未解鎖">🔒</span>'}</a>` : '')
      + (rest.length ? `<div class="lst" id="list"><h2 class="sec">更多文章</h2>${rest.map((x) => `<a class="it${lk}" href="${href(x)}" ${dat(x)}>${tile(x)}<div class="tx"><h3>${esc(x.title)}</h3>${x.summary ? `<p>${esc(x.summary)}</p>` : ''}<div class="m">${esc(x.date)}・${esc(x.reading_min || 1)} 分鐘</div></div>${open ? '' : '<span class="lkc" aria-label="未解鎖">🔒</span>'}</a>`).join('')}</div>` : '')
      + '</div>';
    mountKitAll();
  }
  async function post(id) {
    app.innerHTML = '<p class="sub">載入中…</p>';
    let d; try { d = await getJ(DIR + encodeURIComponent(id) + '.json'); } catch (e) { app.innerHTML = '<p class="sub">找不到這篇文章。</p><p style="padding:0 18px"><a class="btn" href="#/">回文章列表</a></p>'; return; }
    document.title = d.title + '｜' + CH.name;
    const bl = d.blocks || [];
    const pub0 = ((d.sources || [])[0] || {}).publisher, pub = pub0 && pub0.length <= 12 ? pub0 : '';   // 太長的出處名（例如整串工具版本）不放進 meta 一行
    const jumps = (bl.some((b) => b.t === 'mp4' && okUrl(b.src)) ? '<a href="#" data-jump=".vid">▶ 先看影片</a>' : '') + (bl.some((b) => b.t === 'steps' || b.t === 'prompt') ? '<a href="#" data-jump="ol.st,.pr">🔎 直接看做法</a>' : '');
    app.innerHTML = `<div class="aw"><nav class="rail" id="rail" aria-label="文章目錄"></nav><article class="art"><a class="back" href="#/" id="bk">← ${canList() ? '全部文章' : esc(CH.name)}</a><div class="tags">${(d.tags || []).filter((t) => t !== CH.name).map((t) => `<span class="pill">${esc(t)}</span>`).join('')}</div><h1>${esc(d.title)}</h1><div class="meta">${esc(d.date)}・閱讀約 ${esc(d.reading_min || 1)} 分鐘${pub ? '・資料：' + esc(pub) : ''}</div>${jumps ? `<div class="jump">${jumps}</div>` : ''}${banner()}${bl.map(block).join('')}${tail(d)}</article></div>`;
    SC.scrollTo(0, 0);
    mountKit(id);
    mountToc(); fitSvgs();
    try { window.TwArtM && TwArtM.open(id, CH.id, app.querySelector('.art .meta')); } catch (e) { /* 觀測失敗不影響閱讀 */ }
  }
  /* ---- 手機閱讀工具：目錄抽屜／桌機左側欄、進度條、回頂端（蓋到圖表就讓位）、圖片全螢幕放大 ---- */
  let fabs = null, secs = [];
  const unmountFabs = () => { if (fabs) { fabs.remove(); fabs = null; } const s = document.getElementById('tocSheet'); if (s) s.remove(); secs = []; };
  function mountToc() {
    unmountFabs();
    const hh = [...app.querySelectorAll('.art > h2')];
    hh.forEach((h, i) => { h.id = 'sec' + i; });
    secs = hh;
    fabs = document.createElement('div'); fabs.className = 'fabs';
    fabs.innerHTML = (hh.length ? '<button type="button" class="fab" id="tocBtn" aria-expanded="false" aria-controls="tocSheet">☰ 目錄</button>' : '') + '<button type="button" class="fab top" id="topBtn" aria-label="回到頂端" hidden>↑</button>';
    document.body.appendChild(fabs);
    const li = (h, i) => `<li data-i="${i}"><a href="#sec${i}" data-sec="sec${i}">${esc(h.textContent)}</a></li>`;
    if (hh.length) {
      const sh = document.createElement('div'); sh.id = 'tocSheet'; sh.className = 'tocs'; sh.hidden = true;
      sh.innerHTML = '<div class="tocb"><div class="gr"></div><div class="toch"><b>目錄</b><button type="button" class="btn" id="tocX">關閉</button></div><ol>' + hh.map(li).join('') + '</ol></div>';
      document.body.appendChild(sh);
      const rl = document.getElementById('rail'); if (rl) rl.innerHTML = '<b>本文目錄</b><ol>' + hh.map(li).join('') + '</ol>';
    }
    /* 影片與步驟的捷徑要有錨點 */
    onScroll();
  }
  let tick = false;
  const onScroll = () => {
    if (tick) return; tick = true;
    requestAnimationFrame(() => {
      tick = false;
      const t = document.getElementById('topBtn'); if (t) t.hidden = SC.scrollTop < 500;
      const pg = document.querySelector('.prog b'), art = app.querySelector('.art');
      if (pg && art) { const r = art.getBoundingClientRect(), tot = r.height - SC.clientHeight; pg.style.width = (tot > 0 ? Math.max(0, Math.min(1, -r.top / tot)) * 100 : 100) + '%'; }
      if (secs.length) { let cur = -1; const top0 = SC.getBoundingClientRect().top; secs.forEach((h, i) => { if (h.getBoundingClientRect().top - top0 < 120) cur = i; }); document.querySelectorAll('.tocb li,.rail li').forEach((el) => el.classList.toggle('on', +el.dataset.i === cur)); }
    });
  };
  SC.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  /* SVG 圖表：依圖內最小字級算出「手機上字不小於 13px」所需的寬度，窄螢幕就橫向滑動，不縮到看不見 */
  const svgW = {};
  function fitSvgs() {
    app.querySelectorAll('.fz img[src$=".svg"]').forEach((im) => {
      const u = im.getAttribute('src');
      (svgW[u] = svgW[u] || fetch(u).then((r) => r.text()).then((t) => {
        const vb = (t.match(/viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"/) || []);
        const fs = (t.match(/font-size="([\d.]+)"/g) || []).map((x) => parseFloat(x.replace(/[^\d.]/g, ''))).filter((x) => x > 0);
        const w = parseFloat(vb[1]) || 800, mn = fs.length ? Math.min(...fs) : 18;
        return Math.min(Math.round(w * 12 / mn), 1100);
      }).catch(() => 780)).then((w) => { im.style.setProperty('--mw', w + 'px'); const fz = im.closest('.fz'); if (matchMedia('(max-width:640px)').matches && w > fz.clientWidth - 2) { fz.dataset.svg = '1'; const zh = fz.parentNode.querySelector('.zh'); if (zh) zh.textContent = '← 左右滑動看全圖　點圖可放大'; } });
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
    const ch = t.closest('[data-chip]'); if (ch) { filt(ch.dataset.chip); return; }
    const jp = t.closest('a[data-jump]'); if (jp) { e.preventDefault(); const el = app.querySelector(jp.dataset.jump); if (el) { const h = el.previousElementSibling; const tg = el.matches('ol.st') && h && h.classList.contains('stt') ? h : el; tg.style.scrollMarginTop = '68px'; tg.scrollIntoView({ behavior: 'smooth', block: 'start' }); } return; }
    const vp = t.closest('[data-vplay]'); if (vp) { const v = vp.closest('.vid').querySelector('video'); try { v.play(); const fs = v.requestFullscreen || v.webkitRequestFullscreen; if (fs && matchMedia('(max-width:640px)').matches) fs.call(v); else if (v.webkitEnterFullscreen && matchMedia('(max-width:640px)').matches) v.webkitEnterFullscreen(); } catch (er) { /* 略 */ } return; }
    if (t.closest('#fl')) { follow(); return; }
    if (t.closest('#tocBtn')) { const s = document.getElementById('tocSheet'); s.hidden = !s.hidden; t.closest('#tocBtn').setAttribute('aria-expanded', String(!s.hidden)); return; }
    if (t.closest('#tocX')) { document.getElementById('tocSheet').hidden = true; return; }
    const a = t.closest('a[data-sec]'); if (a) { e.preventDefault(); document.getElementById('tocSheet').hidden = true; const h = document.getElementById(a.dataset.sec); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    if (t.closest('#topBtn')) { SC.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    if (t.id === 'tocSheet') t.hidden = true;
  });
  /* 分類 chip：只切顯示，不重畫；同時按下的 chip 標 aria-pressed */
  function filt(tag) {
    app.querySelectorAll('[data-chip]').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.chip === tag)));
    app.querySelectorAll('a[data-tags]').forEach((a) => { a.hidden = !!tag && !a.dataset.tags.split('|').includes(tag); });
    const l = app.querySelector('#list'); if (l) l.hidden = !l.querySelector('a:not([hidden])');
  }
  /* 頁首「追蹤」鈕（常駐右側，Andy 11-20 決定）：沒登入→登入視窗；已登入沒解鎖→帶到說明；已解鎖→顯示「已追蹤」 */
  function renderFollow() {
    const b = document.getElementById('fl'); if (!b) return;
    if (admin()) { b.hidden = true; return; }
    b.hidden = false;
    const on = member() && unlocked();
    b.textContent = on ? '已追蹤 ✓' : '追蹤';
    b.classList.toggle('fill', !on);
    b.setAttribute('aria-label', on ? '已追蹤 ' + CH.name : '追蹤 ' + CH.name);
  }
  function follow() {
    if (!member()) { login(); return; }
    if (unlocked()) { location.hash = '#/'; return; }
    const g = document.getElementById('gate') || document.getElementById('bn');
    if (g) g.scrollIntoView({ block: 'center', behavior: 'smooth' });
    else location.hash = '#/';
  }
  function route() {
    closeLb(); unmountFabs(); renderFollow();
    const h = (location.hash || '').replace(/^#\/?/, '');
    document.body.classList.toggle('ispost', !!(h && okId(decodeURIComponent(h))));
    if (h && okId(decodeURIComponent(h))) post(decodeURIComponent(h)); else list();
  }
  document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'lg') login();
    const k = e.target && e.target.closest && e.target.closest('a[data-lock]');
    if (k) { e.preventDefault(); if (!member()) login(); else { const g = document.getElementById('gate'); if (g) g.scrollIntoView({ block: 'center', behavior: 'smooth' }); } }   // 沒解鎖：未登入→登入視窗；已登入→捲到說明
  });
  window.addEventListener('hashchange', route);
  /* 登入／解鎖狀態變了才重畫（兌換是非同步，會晚到）*/
  let t; const again = () => { clearTimeout(t); t = setTimeout(route, 80); };
  window.addEventListener('tw:account', again);
  window.addEventListener('tw:chunl', again);
  route();
})();
