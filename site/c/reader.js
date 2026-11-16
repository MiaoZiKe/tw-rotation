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
      case 'callout': return `<div class="callout">${esc(b.text)}</div>`;
      case 'ul': return `<ul>${(b.items || []).map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
      case 'steps': return `${b.title ? `<h2>${esc(b.title)}</h2>` : ''}<ol class="st">${(b.items || []).map((x) => `<li><b>${esc(x.label)}</b>${x.text ? '：' + esc(x.text) : ''}</li>`).join('')}</ol>${b.note ? `<p class="n">${esc(b.note)}</p>` : ''}`;
      case 'table': return `<div class="tw"><table><thead><tr>${(b.head || []).map((x) => `<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${(b.rows || []).map((r) => `<tr>${r.map((x) => `<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      case 'img': return `<div class="imgs">${(b.items || []).map((x) => okUrl(x.src) ? `<figure><img src="${esc(rel(x.src))}" alt="${esc(x.alt)}" loading="lazy">${x.cap ? `<figcaption>${esc(x.cap)}</figcaption>` : ''}</figure>` : '').join('')}</div>`;
      case 'links': return `${b.title ? `<h2>${esc(b.title)}</h2>` : ''}<ul>${(b.items || []).map((x) => (/^https:\/\//.test(x.url || '') ? `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label)}</a></li>` : '')).join('')}</ul>`;
      case 'mp4': {
        const s = okUrl(b.src); if (!s) return '';
        const p = okUrl(b.poster);
        return `<div class="vid"><video controls playsinline preload="metadata" src="${esc(rel(s))}"${p ? ` poster="${esc(rel(p))}"` : ''}></video>${b.note ? `<div class="n">${esc(b.note)}</div>` : ''}<a class="btn" href="${esc(rel(s))}" download>下載影片 ⬇</a></div>`;
      }
      default: return '';
    }
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
    app.innerHTML = `<article class="art"><a class="back" href="#/" id="bk">← ${canList() ? '全部文章' : esc(CH.name)}</a><h1>${esc(d.title)}</h1><div class="meta">${esc(d.date)}　閱讀約 ${esc(d.reading_min || 1)} 分鐘</div><div class="tags">${(d.tags || []).map((t) => `<span>${esc(t)}</span>`).join('')}</div>${banner()}${(d.blocks || []).map(block).join('')}</article>`;
    window.scrollTo(0, 0);
    mountKit(id);
    try { window.TwArtM && TwArtM.open(id, CH.id, app.querySelector('.art .meta')); } catch (e) { /* 觀測失敗不影響閱讀 */ }
  }
  function route() {
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
