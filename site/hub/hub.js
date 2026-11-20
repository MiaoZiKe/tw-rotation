/* ============================================================================
   頻道作品專區（#hub、#hub/<頻道>）—— 2026-11-20 Andy：「哩股哩股上方都需要各頻道影片 文案 資訊可以下載，及觀看」
   這一頁回答的問題：「四個頻道各做過哪些影片？我要看、要下載、要拿文案去貼，一個地方做完。」
   怎麼用：上方四個頻道分頁切換；每則作品可「播放」（卡片原地展開影片，不跳頁）、「下載影片」、「複製文案」、「看文章」。
   資料：site/hub/works.json，由 scripts/build_channel_hub.py 從 site/articles/<頻道>/*.json 的 mp4 區塊與 queue 的 caption.txt 產生，不手寫。
   權限：下載＝功能鍵 hub.dl（訪客顯示「登入後可下載」，點了開登入視窗）；複製文案＝hub.copy。影片播放與看文案不受限。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const can = (k) => { try { const P = window.TwPerm; return !(P && P.can) || P.can(k); } catch (e) { return true; } };
  const DEF = 'ligu';
  let DATA = null, cur = DEF, openId = '';

  async function load() {
    if (DATA) return DATA;
    try { const r = await fetch('hub/works.json', { cache: 'no-cache' }); DATA = await r.json(); }
    catch (e) { DATA = { channels: [], works: [] }; }
    return DATA;
  }
  const today = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  const md = (s) => String(s || '').slice(5).replace('-', '/');
  const dlName = (w) => (String(w.title).replace(/[\\/:*?"<>|\r\n]+/g, ' ').trim().slice(0, 60) || w.id) + '.mp4';

  function card(w) {
    const pre = w.date > today();
    const open = openId === w.id;
    const dlOn = can('hub.dl'), cpOn = can('hub.copy');
    return `<article class="hbc${open ? ' open' : ''}" data-id="${esc(w.id)}">
      <div class="hbt">
        <button type="button" class="hbp" data-act="play" aria-label="播放：${esc(w.title)}"><img src="${esc(w.poster)}" alt="" loading="lazy" decoding="async"><i aria-hidden="true">▶</i></button>
        <div class="hbi"><h3>${esc(w.title)}</h3>
          <p class="hbm"><span class="hbd${pre ? ' pre' : ''}">${pre ? '預排 ' : ''}${esc(md(w.date))}</span><span>${esc(w.mb)} MB</span>${w.ig ? `<a href="${esc(w.ig)}" target="_blank" rel="noopener">IG</a>` : ''}${w.threads ? `<a href="${esc(w.threads)}" target="_blank" rel="noopener">Threads</a>` : ''}</p>
          <p class="hbs">${esc(w.summary)}</p></div>
      </div>
      <div class="hba">
        <button type="button" class="hbb pri" data-act="play">${open ? '收起' : '▶ 播放'}</button>
        <a class="hbb dl${dlOn ? '' : ' lock'}" data-act="dl" data-src="${esc(w.video)}" data-dl="${esc(dlName(w))}" ${dlOn ? `href="${esc(w.video)}" download="${esc(dlName(w))}"` : 'href="#" aria-disabled="true"'}>${dlOn ? '下載影片' : '登入後可下載'}</a>
        <button type="button" class="hbb cp" data-act="copy"${cpOn ? '' : ' disabled'}>複製文案</button>
        <a class="hbb" href="#article/${esc(w.id)}">看文章</a>
      </div>
      ${open ? `<div class="hbx"><div class="hbv"><video controls playsinline autoplay preload="metadata" src="${esc(w.video)}" poster="${esc(w.poster)}" aria-label="${esc(w.title)}"></video></div>
        <div class="hbcap"><h4>貼文文案${w.caption_src === 'summary' ? '<small>（由文章摘要整理，非貼出的原文）</small>' : ''}</h4><pre>${esc(w.caption)}</pre></div></div>` : ''}
    </article>`;
  }

  function paint() {
    const root = $('#v-hub'); if (!root || !DATA) return;
    const ws = DATA.works.filter((w) => w.ch === cur);
    root.innerHTML = `<div class="hubbar"><div class="seg hubtabs" role="tablist" aria-label="頻道">${DATA.channels.map((c) =>
      `<button type="button" role="tab" data-ch="${esc(c.id)}" class="${c.id === cur ? 'on' : ''}" aria-selected="${c.id === cur}"><span class="hn">${esc(c.name)}</span><span class="hs2">${esc(c.short)}</span><b>${c.n}</b></button>`).join('')}</div>
      <button type="button" class="hubq" aria-label="這一頁怎麼用" aria-expanded="false">?</button></div>
      <p class="hubhelp" hidden>每個頻道已做好的短影片都放在這裡：點「播放」在原地看、「下載影片」存 mp4（登入後可下載）、「複製文案」拿去貼 IG／Threads，「看文章」到站上對應的完整文章。標「預排」的是已做好、尚未到發布日的作品。</p>
      <div class="hubgrid">${ws.length ? ws.map(card).join('') : '<p class="hubempty">這個頻道目前沒有影片作品。</p>'}</div>`;
  }

  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t);
    return new Promise((res, rej) => { try { const a = document.createElement('textarea'); a.value = t; a.style.cssText = 'position:fixed;opacity:0'; document.body.appendChild(a); a.select(); document.execCommand('copy') ? res() : rej(); a.remove(); } catch (e) { rej(e); } });
  }

  function bind() {
    const root = $('#v-hub'); if (!root || root._hub) return; root._hub = 1;
    root.addEventListener('click', (e) => {
      const t = e.target.closest('button,a'); if (!t) return;
      if (t.matches('.hubtabs button')) { location.hash = '#hub/' + t.dataset.ch; return; }
      if (t.matches('.hubq')) { const h = $('.hubhelp', root); h.hidden = !h.hidden; t.setAttribute('aria-expanded', String(!h.hidden)); return; }
      const c = t.closest('.hbc'); if (!c) return;
      const w = DATA.works.find((x) => x.id === c.dataset.id); if (!w) return;
      const act = t.dataset.act;
      if (act === 'play') { openId = openId === w.id ? '' : w.id; paint(); const n = $('.hbc[data-id="' + w.id + '"]', root); if (n && openId) n.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
      else if (act === 'dl' && t.classList.contains('lock')) { e.preventDefault(); try { window.TwAccount && TwAccount.login && TwAccount.login(); } catch (er) { /* 登入視窗開不起來就維持原狀 */ } }
      else if (act === 'copy') {
        copyText(w.caption).then(() => { t.textContent = '已複製 ✓'; t.classList.add('ok'); setTimeout(() => { t.textContent = '複製文案'; t.classList.remove('ok'); }, 1600); })
          .catch(() => { t.textContent = '複製失敗，請展開手動選取'; setTimeout(() => { t.textContent = '複製文案'; }, 2200); });
      }
    });
    const re = () => { if (DATA && /^#hub(\/|$)/.test(location.hash)) { const keep = openId; paint(); openId = keep; } };
    window.addEventListener('tw:perm', re); window.addEventListener('tw:account', re);
  }

  async function show(head, rest) {
    const root = $('#v-hub'); if (!root) return;
    await load();
    const want = (rest && rest[0]) || DEF;
    const ch = DATA.channels.some((c) => c.id === want) ? want : DEF;
    if (ch !== cur) openId = '';
    cur = ch; bind(); paint();
  }
  window.TwHub = { show };
})();
