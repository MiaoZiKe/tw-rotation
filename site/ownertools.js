/* 站主工具：錄影模式（隱藏名稱）（2026-11-01 Andy：「因為我是站主需要常常錄製影片，幫我新增隱藏名稱功能」）。
   只有站主（TwAccount.user().admin）看得到開關、只影響站主自己這台瀏覽器（localStorage）：
   把站主自己的名字／email／大頭貼換成「站主」，其他會員的 email 與名字也遮起來（錄影會拍到管理區會員清單與線上名單）。
   做法是「畫面後處理」：MutationObserver 盯著 DOM，把文字節點與 title／aria-label／src 改掉並記下原文，關掉就逐一還原。
   這樣不用動 admin.js／admin_grants.js／account.js 的畫面程式（同事正在改），畫面怎麼重畫都會被再遮一次。
   載入順序：account.js 之前即可（執行時才問 TwAccount）。 */
(function () {
  'use strict';
  const K_REC = 'tw.owner.rec';
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* 無痕或被擋：本次有效即可 */ } };
  const me = () => { try { return (window.TwAccount && window.TwAccount.user()) || null; } catch (e) { return null; } };
  const isAdmin = () => { const u = me(); return !!(u && u.admin); };

  /* ------------------------------------------------ 2) 錄影模式 */
  let rec = lsGet(K_REC) === '1';
  const recOn = () => rec && isAdmin();
  const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/g;
  const NAME_SEL = '#acctOnPop .opn, .memtbl .who1 small, .pmrow .who > b';
  const AV_OWN_SEL = '#acctBtn .ini, .acctbar .ini, .acctmenu .av, .m4am .av';
  const AV_OTHER_SEL = '.pmrow .av';
  const AV_IMG = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="16" fill="#3b82f6"/><text x="16" y="21.5" font-size="15" text-anchor="middle" fill="#fff" font-family="sans-serif">站</text></svg>');
  const maskMail = (m) => { const i = m.indexOf('@'); return m.charAt(0) + '***' + m.slice(i); };
  const maskName = (s, owner) => {
    const t = s.trim(); if (!t) return s;
    const o = owner || {};
    if (t === o.name || t === o.email || t.toLowerCase() === String(o.email || '').split('@')[0].toLowerCase()) return '站主';
    return t.charAt(0) + '＊＊';
  };
  function maskText(v, owner) {
    let s = v;
    if (owner.email && s.toLowerCase().includes(owner.email.toLowerCase())) s = s.replace(new RegExp(owner.email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '站主');
    if (owner.name && owner.name.length >= 2 && s.includes(owner.name)) s = s.split(owner.name).join('站主');
    if (s.includes('@')) s = s.replace(EMAIL_RE, maskMail);
    return s;
  }
  const origT = new Map();     // 文字節點 → { o: 原文, m: 遮後 }
  const origA = new Map();     // 元素 → { 屬性: {o, m} }
  let obs = null, ownerSnap = null;
  const SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, OPTION: 1, NOSCRIPT: 1 };

  function doText(node) {
    const p = node.parentElement; if (!p || SKIP[p.tagName]) return;
    const v = node.nodeValue; if (!v || !v.trim()) return;
    const e = origT.get(node); if (e && v === e.m) return;          // 已經是遮過的樣子
    let m = v;
    if (p.matches(AV_OWN_SEL) && v.trim().length <= 2) m = '站';
    else if (p.matches(AV_OTHER_SEL) && v.trim().length <= 2) m = '＊';
    else if (v.length < 120 && p.matches(NAME_SEL)) m = maskName(v, ownerSnap);
    else if (v.includes('@') || (ownerSnap.email && v.toLowerCase().includes(ownerSnap.email.toLowerCase())) || (ownerSnap.name && ownerSnap.name.length >= 2 && v.includes(ownerSnap.name))) m = maskText(v, ownerSnap);
    if (m !== v) { origT.set(node, { o: v, m }); node.nodeValue = m; }
  }
  function doAttr(el, a) {
    const v = el.getAttribute(a); if (!v) return;
    const rec0 = origA.get(el) || {}, e = rec0[a]; if (e && v === e.m) return;
    let m;
    if (a === 'src') { if (!el.matches('.acctbar img, .acctmenu .av img, .m4am .av img, .mmrow img, #mmAcct img')) return; m = AV_IMG; }
    else m = maskText(v, ownerSnap);
    if (m !== v) { rec0[a] = { o: v, m }; origA.set(el, rec0); el.setAttribute(a, m); }
  }
  function doEl(el) {
    ['title', 'aria-label'].forEach((a) => { if (el.hasAttribute(a)) doAttr(el, a); });
    if (el.tagName === 'IMG') doAttr(el, 'src');
  }
  function scan(root) {
    if (!root) return;
    if (root.nodeType === 3) { doText(root); return; }
    if (root.nodeType !== 1) return;
    doEl(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    let n; while ((n = w.nextNode())) { if (n.nodeType === 3) doText(n); else doEl(n); }
  }
  /* 觀察器回呼本身就是微任務，在畫面繪製之前跑：直接同步遮，不排 rAF／計時器 —— 這樣畫面不會閃一下原文、驗收讀到的也一定是遮過的 */
  function flushNodes(L) { if (!recOn()) return; L.forEach((n) => { if (n.isConnected) scan(n); }); }
  function startMask() {
    const u = me() || {}; ownerSnap = { name: u.name || '', email: u.email || '' };
    if (!obs) {
      obs = new MutationObserver((rs) => {
        const L = [];
        rs.forEach((r) => {
          if (r.type === 'characterData' || r.type === 'attributes') L.push(r.target);
          else r.addedNodes.forEach((n) => L.push(n));
        });
        flushNodes(L);
      });
    }
    obs.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['title', 'aria-label', 'src'] });
    scan(document.body);
  }
  function stopMask() {
    if (obs) obs.disconnect();
    origT.forEach((e, n) => { if (n.nodeValue === e.m) n.nodeValue = e.o; }); origT.clear();
    origA.forEach((rs, el) => { Object.keys(rs).forEach((a) => { if (el.getAttribute(a) === rs[a].m) el.setAttribute(a, rs[a].o); }); }); origA.clear();
  }

  function badge() {
    let b = document.getElementById('recBadge');
    if (!recOn()) { if (b) b.remove(); return; }
    if (b) return;
    b = document.createElement('span'); b.id = 'recBadge'; b.className = 'recbadge'; b.setAttribute('role', 'status');
    b.title = '錄影模式開著：名稱與 email 已隱藏（Alt+H 關閉）'; b.innerHTML = '<i></i>錄影中';
    const bar = window.TwAcctBar ? window.TwAcctBar() : null;
    if (bar && bar.offsetParent) bar.insertBefore(b, bar.firstChild); else { b.classList.add('fx'); document.body.appendChild(b); }
  }
  let applied = false;
  function applyRec() {
    const on = recOn();
    document.documentElement.classList.toggle('rec-on', on);
    if (on && !applied) { applied = true; startMask(); }
    else if (!on && applied) { applied = false; stopMask(); }
    badge(); eye(); syncUi();
  }
  /* 頂欄眼睛鈕（Andy 11-02：「改成我可以有眼睛符號隱藏」）：站主帳號鈕左邊，桌機與手機都有；睜眼＝顯示中，斜線眼＝隱藏中 */
  const EYE_ON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  const EYE_OFF = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 19C5 19 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24"/><path d="M1 1l22 22"/></svg>';
  function eye() {
    let b = document.getElementById('recEye');
    if (!isAdmin()) { if (b) b.remove(); return; }
    const ref = document.getElementById('acctBtn'); if (!ref || !ref.parentNode) return;   // 登入鈕在哪個容器就跟著放哪（桌機 #l4Tools、手機 .m4tools、舊版 .acctbar 各不同）
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = 'recEye'; b.className = 'receye'; b.setAttribute('data-own', 'rec');
      b.title = '錄影時隱藏名稱（Alt＋H）';
    }
    /* 桌機（layout4.js）：#l4Tools 裡的孩子數量／順序由 layout4.js 的 syncTools 固定，多一個陌生節點它會一直重排 → 眼睛鈕改放在 #l4Tools 前面（它的兄弟），
       不放進去，免得兩邊互相觸發。其他版面（手機 .m4tools、舊版 .acctbar）直接放在登入鈕前面。 */
    const tgt = ref.parentNode.id === 'l4Tools' ? ref.parentNode : ref;
    if (b.nextSibling !== tgt || b.parentNode !== tgt.parentNode) tgt.parentNode.insertBefore(b, tgt);
    const on = recOn();
    b.setAttribute('aria-pressed', String(on)); b.setAttribute('aria-label', on ? '錄影模式：隱藏中，點一下顯示名稱' : '錄影時隱藏名稱');
    const want = on ? 'off' : 'on'; if (b.dataset.ic !== want) { b.dataset.ic = want; b.innerHTML = on ? EYE_OFF : EYE_ON; }
    b.classList.toggle('on', on);
  }
  function setRec(v) { rec = !!v; lsSet(K_REC, rec ? '1' : '0'); applyRec(); }


  /* ------------------------------------------------ 帳號選單裡的開關（只有站主才會被畫出來） */
  function recRow(kind) {
    const on = recOn();
    if (kind === 'm4') return `<button type="button" class="m4i" role="menuitemcheckbox" aria-checked="${on}" data-own="rec"><span class="t">錄影模式（隱藏名稱）<small class="otsub">隱藏你的名字與 email、會員清單的 email。快捷鍵 Alt+H</small></span><span class="sw" aria-hidden="true"></span></button>`;
    return `<button type="button" class="dk" role="menuitemcheckbox" aria-checked="${on}" data-own="rec" title="錄影時把你的名字、email、大頭貼換成「站主」，會員清單與線上名單的 email 也遮起來。快捷鍵 Alt+H"><span class="t">錄影模式（隱藏名稱）<small class="otsub">快捷鍵 Alt+H</small></span><span class="sw" aria-hidden="true"></span></button>`;
  }
  const menuHTML = (kind) => (isAdmin() ? recRow(kind) : '');
  function syncUi() {
    const on = recOn();
    document.querySelectorAll('[data-own="rec"]:not(.receye)').forEach((b) => b.setAttribute('aria-checked', String(on)));
    eye();
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('[data-own="rec"]'); if (!b || !isAdmin()) return;
    e.stopPropagation(); setRec(!rec);      // 選單不收，讓人看到開關換了
  }, true);
  document.addEventListener('keydown', (e) => {
    if (e.altKey && !e.ctrlKey && !e.metaKey && (e.code === 'KeyH' || e.key === 'h' || e.key === 'H')) { if (isAdmin()) { e.preventDefault(); setRec(!rec); } }
  });
  window.addEventListener('tw:account', applyRec);
  /* layout4.js／mobile4.js 會把登入鈕搬來搬去：眼睛鈕要一直貼在它左邊（eye() 只在位置不對時才動 DOM，不會互相觸發無限循環）*/
  const watchBar = () => { const t = document.querySelector('.topbar') || document.body; new MutationObserver(() => { if (isAdmin()) eye(); }).observe(t, { childList: true, subtree: true }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchBar); else watchBar();

  const css = document.createElement('style');
  css.textContent = `
.recbadge{display:inline-flex;align-items:center;gap:5px;height:24px;padding:0 9px;border-radius:999px;font-size:12.5px;font-weight:700;color:#fff;background:#d92d3f;white-space:nowrap}
.recbadge i{width:8px;height:8px;border-radius:50%;background:#fff;animation:recblink 1.2s ease-in-out infinite}
.recbadge.fx{position:fixed;bottom:10px;left:10px;z-index:1400;box-shadow:0 2px 10px rgba(0,0,0,.35)}
@keyframes recblink{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.recbadge i{animation:none}}
#recEye{display:inline-grid;place-items:center;flex:none;width:34px;height:34px;margin:0 2px 0 0;padding:0;box-sizing:border-box;border:1px solid var(--line-2);border-radius:9px;background:var(--panel);color:var(--ink-2);cursor:pointer;line-height:1}
#recEye:hover{color:var(--ink);border-color:var(--cyan)}
#recEye.on{color:#fff;background:#d92d3f;border-color:#d92d3f}
#recEye svg{display:block}
.otsub{display:block;font-size:11.5px;font-weight:400;color:var(--ink-2);margin-top:1px}
/* 頂欄頭像字母：圖片載入失敗時由 account.js 的 onerror 換成字母節點，時序上可能晚於後處理 → 用 CSS 保底直接蓋成「站」 */
html.rec-on #acctBtn .ini,html.rec-on #mmAcct .ini{font-size:0!important}
html.rec-on #acctBtn .ini::after{content:'站';font-size:13px}
html.rec-on #v-admin input[type=email]{filter:blur(6px)}
html.rec-on #v-admin input[type=email]:focus{filter:none}`;
  document.head.appendChild(css);

  window.TwOwner = { recOn, setRec, menuHTML, syncUi };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyRec); else applyRec();
})();
