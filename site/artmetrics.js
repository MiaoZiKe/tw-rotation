/* 2026-11-17 文章觀測（Andy：「記錄是訪客還是會員；哪一篇次數多；有沒有被收藏、轉發；目前只先記錄」）。主站文章頁與獨立站（site/c/）共用。
   沿用 account.js 的「細項事件 ev2」管道（window.TwT → /v1/track/batch，Worker 不用改、不用重新部署）：
     頁面固定 articles；元件＝ch.<動作>.<身分>[.<來源>]；細項＝<頻道代號>:<id 去掉年份>（≤24 字，account.js 會截）。
       ch.view.<guest|member|admin>.<dm|site>   文章被打開（dm＝從私訊解鎖連結進來，site＝站內／其他）
       ch.save.<身分>／ch.unsave.member／ch.savetry.guest（訪客點收藏）   收藏
       ch.share.sys.<身分>（手機系統分享）／ch.share.copy.<身分>（複製連結）   轉發
       ch.play.<身分>／ch.dl.<身分>   影片播放（每次打開文章第一次播放）、下載
   不記 IP、不記裝置指紋、不帶識別碼；DNT／GPC 開著就不送（account.js 的 noTrack）。
   收藏「記在帳號」需要會員 Worker 端點；Worker 未改前先存本機（tw.art.fav.<uid>）並送事件，見 docs/marketing/channels/follow_unlock_design.md 第 8 節。 */
(function () {
  'use strict';
  const CHK = { caffaine: 'c', healing: 'h', tech: 't', ligu: 'l' };
  const S = { id: '', ch: '' };
  const user = () => { try { return window.TwAccount && TwAccount.user && TwAccount.user(); } catch (e) { return null; } };
  const aud = () => { const u = user(); return u ? (u.admin ? 'admin' : 'member') : 'guest'; };
  const uid = () => { const u = user(); return u ? (u.uid || u.email || '') : ''; };
  const det = () => (CHK[S.ch] || 'x') + ':' + S.id.replace(/^\d{4}-/, '');
  const ev = (comp) => { try { if (window.TwT) window.TwT(comp, det(), 'articles'); } catch (e) { /* 統計失敗不影響閱讀 */ } };
  const favKey = () => 'tw.art.fav.' + uid();
  const favs = () => { try { return JSON.parse(localStorage.getItem(favKey()) || '[]') || []; } catch (e) { return []; } };
  const isFav = () => !!uid() && favs().includes(S.id);
  const toast = (m) => {
    try { let t = document.getElementById('amToast'); if (!t) { t = document.createElement('div'); t.id = 'amToast'; t.className = 'accttoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); } t.textContent = m; t.style.display = 'block'; clearTimeout(t._h); t._h = setTimeout(() => { t.style.display = 'none'; }, 3000); } catch (e) { /* 忽略 */ }
  };
  const src = () => { let d = ''; try { d = sessionStorage.getItem('tw.src.dm') || ''; } catch (e) { /* 忽略 */ } return d ? 'dm' : 'site'; };
  const CSS = '.artm{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}.artm button{display:inline-flex;align-items:center;gap:6px;min-height:36px;padding:6px 14px;border:1px solid currentColor;border-radius:999px;background:transparent;color:inherit;font:inherit;font-size:14px;cursor:pointer;opacity:.85}.artm button.on{font-weight:700;opacity:1}';
  function paint() {
    const b = document.querySelector('#artM [data-am=save]'); if (!b) return;
    b.classList.toggle('on', isFav()); b.textContent = isFav() ? '★ 已收藏' : '☆ 收藏';
  }
  /* 打開一篇文章時呼叫：記瀏覽、把收藏／分享鈕放進 host（沒給 host 就放在 .artttl／h1 後面）*/
  function open(id, ch, host) {
    S.id = String(id || ''); S.ch = ch || ''; S.played = false;
    if (!S.id) return;
    ev('ch.view.' + aud() + '.' + src());
    if (!document.getElementById('amCss')) { const st = document.createElement('style'); st.id = 'amCss'; st.textContent = CSS; document.head.appendChild(st); }
    const old = document.getElementById('artM'); if (old) old.remove();
    const el = document.createElement('div'); el.className = 'artm'; el.id = 'artM';
    el.innerHTML = '<button type="button" data-am="save"></button><button type="button" data-am="share">↗ 分享</button>';
    const h = host || document.querySelector('.artttl, .art h1'); if (!h) return;
    h.insertAdjacentElement('afterend', el); paint();
  }
  document.addEventListener('click', (e) => {
    const t = e.target && e.target.closest && e.target.closest('#artM [data-am], a[download], a.avdl'); if (!t || !S.id) return;
    if (t.matches('a[download], a.avdl')) { ev('ch.dl.' + aud()); return; }
    if (t.dataset.am === 'save') {
      if (!uid()) { ev('ch.savetry.guest'); toast('登入後才能收藏'); try { TwAccount.login(); } catch (er) { /* 帳號功能沒開 */ } return; }
      const k = favKey(), cur = favs(), on = cur.includes(S.id);
      const nx = on ? cur.filter((x) => x !== S.id) : cur.concat(S.id).slice(-300);
      try { localStorage.setItem(k, JSON.stringify(nx)); } catch (er) { /* 私密視窗 */ }
      ev(on ? 'ch.unsave.member' : 'ch.save.' + aud()); paint(); toast(on ? '已取消收藏' : '已收藏'); return;
    }
    if (t.dataset.am === 'share') {
      const url = location.href.split('#unlock')[0], title = document.title;
      const phone = matchMedia && matchMedia('(pointer:coarse)').matches;
      if (phone && navigator.share) { ev('ch.share.sys.' + aud()); navigator.share({ title, url }).catch(() => {}); return; }
      ev('ch.share.copy.' + aud());
      try { navigator.clipboard.writeText(url).then(() => toast('已複製連結'), () => toast('請手動複製網址列')); } catch (er) { toast('請手動複製網址列'); }
    }
  });
  document.addEventListener('play', (e) => {
    if (!e.target || e.target.tagName !== 'VIDEO' || !S.id || S.played) return;
    S.played = true; ev('ch.play.' + aud());
  }, true);
  window.addEventListener('tw:account', paint);
  window.TwArtM = { open, aud, src, isFav, _det: () => det() };
})();
