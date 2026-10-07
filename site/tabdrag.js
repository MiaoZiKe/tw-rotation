/* ============================================================================
   分頁拖曳排序（site/tabdrag.js）—— 全站共用、自動掛載
   ----------------------------------------------------------------------------
   Andy 2026-10-06：「分頁具備拖曳移動位置功能，但不具備刪除功能」
                    「所有分頁都具備拖曳移動調整位置功能」。

   做什麼：
     · 頁面裡的分頁列（SEL）自動可以用滑鼠拖曳換位置；鍵盤焦點在分頁上時 Alt+← ／ Alt+→ 左右移一格。
     · 順序存 localStorage（tw.tabs.<路由>.<分頁列 id>），屬於「使用者設定」：重新整理保留。
     · 分頁列重新渲染（innerHTML 換掉）時自動套回順序。
     · 只能排序，不能刪除。改過順序的分頁列，在分頁上按右鍵 →「還原預設順序」。

   為什麼用 CSS `order` 而不是搬 DOM：
     各頁的分頁程式有用「第幾個子元素」判斷目前分頁的（例如 `[...bar.children].forEach((b, k) => …)`），
     perm.js 也靠 data-t 掛鎖頭。只改視覺順序、DOM 一個節點都不動，既有的點擊、鎖頭、索引邏輯全部照舊。
     代價：Tab 鍵的焦點順序仍是原始順序（Alt+←→ 移動後焦點仍留在被移動的那一顆上）。

   為什麼用 MutationObserver 而不是讓每一頁自己呼叫：
     分頁列散在十幾支檔案、各自 innerHTML 重畫；逐頁加呼叫一定會漏。觀察者的回呼是微任務，
     在瀏覽器畫下一格之前就把順序套回去，所以重畫時不會先閃一下原始順序。

   拖曳中不觸發切換：滑鼠移動超過 6px 才算拖曳；放開後吞掉緊接的那一次 click（含 <a> 的預設跳頁）。
   只接受滑鼠／觸控筆；手指觸控保留原本的橫向捲動（手機上改順序用不到，也最不干擾）。

   排除：側欄與頂部導覽（.tabs）、管理區（#v-admin，它的範本頁籤有自己的伺服器排序）、
         自選清單頁籤（#wlTabs／#wpTabs：那是使用者自己的清單，順序是清單資料，不是分頁設定）。

   用法（別的頁要加分頁列時）：
     1. 分頁列用 `.nbsw`、`.subtabs` 或 `role="tablist"` 其中之一，就會自動掛上；給它一個穩定的 id。
     2. 每顆分頁帶一個穩定的 data-*（data-t／data-v／data-c／data-cat／data-k／data-i…），沒有就用文字（去掉數字）。
     3. 不需要寫任何 JS。要程式操作：window.TabDrag.order(bar) 取目前順序、TabDrag.reset(bar) 還原、
        TabDrag.scan() 手動掃一次；順序改變時分頁列會發出 `tabdrag:change` 事件（detail.order）。
   ============================================================================ */
(function () {
  'use strict';
  const SEL = '.nbsw, .subtabs, #stockTabs, #mktSeg2, #mktTabs, [role="tablist"]';
  const EXCL = '#v-admin, .tabs, #tabsWrap, #wlTabs, #wpTabs, .wltabs, .wptabs, .admnav';
  const IDK = ['t', 'c', 'cat', 'v', 'dgid', 'dgtab', 'k', 'i', 's', 'p', 'tab', 'sub', 'view', 'id'];
  const LS = {
    get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 私密視窗：只在這次有效 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 同上 */ } },
  };

  /* ★ 2026-10-07（Andy 14:50）：「拖曳功能，只有帳號可以使用，任何可更改功能都只有我這帳號可以，其他帳號我沒有新增管理者情況下不行」。
     只有管理者（擁有者＋擁有者在 #admin/admins 加的人；判定在 Worker，前端只讀 /v1/me 回的 admin 旗標）可以拖。
     非管理者：不掛 data-tdrag（沒有拖曳游標、沒有提示、拖不動、Alt+←→／右鍵還原都不作用），已存的 tw.tabs.* 一律清掉回預設。
     判斷用 TwAccount.user()；account.js 還沒載入時退回同一份登入快取（tw.acct.user），免得管理者自己的順序在開頁瞬間被清掉。
     ⚠ 這是「每人自己瀏覽器的排列」，不會改到全站；但 Andy 明講仍只限管理者，照做（docs/admin_only_audit.md）。*/
  function isAdm() {
    try {
      const A = window.TwAccount;
      if (A && A.on && !A.on()) return false;                 // 會員功能沒設定＝沒有管理者
      const u = A && A.user ? A.user() : JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && u.admin);
    } catch (e) { return false; }
  }
  /* 只在「確定不是管理者」時清：會員功能沒設定、沒登入（沒權杖）、或身分已確認但不是管理者。
     有權杖但 /v1/me 還沒回來（身分未知）時先不清，免得管理者自己的順序在開頁瞬間被洗掉；回來後 tw:account 會再判一次。*/
  function notAdmKnown() {
    let tok = null; try { tok = localStorage.getItem('tw.acct.tok'); } catch (e) { return false; }
    if (!tok) return true;                                   // 沒登入
    const A = window.TwAccount, u = A && A.on && A.on() && A.user && A.user();
    return !!u && !u.admin;                                  // 已確認身分且不是管理者
  }
  function purge() { if (!notAdmKnown()) return; try { Object.keys(localStorage).filter((k) => k.startsWith('tw.tabs.')).forEach((k) => localStorage.removeItem(k)); } catch (e) { /* 私密視窗 */ } }
  function strip(bar) {
    if (!bar.hasAttribute('data-tdrag')) return;
    bar.removeAttribute('data-tdrag'); bar.removeAttribute('data-tdcustom');
    if (bar.title === TITLE) bar.removeAttribute('title');
    items(bar).forEach((el) => { if (el.style.order) el.style.order = ''; el.classList.remove('td-src'); });
  }
  const TITLE = '拖曳分頁可調整順序（或 Alt+←／→）；改過後按右鍵可還原';
  const isBar = (el) => !!(el && el.nodeType === 1 && el.matches(SEL) && !el.closest(EXCL));
  const items = (bar) => [...bar.children].filter((c) => c.nodeType === 1 && !c.hidden && c.tagName !== 'TEMPLATE');
  function itemId(el) {
    for (const k of IDK) if (el.dataset && el.dataset[k] != null && el.dataset[k] !== '') return k + ':' + el.dataset[k];
    return 'x:' + (el.textContent || '').replace(/[\d,.\s%+\-]+/g, '').slice(0, 24);
  }
  function key(bar) {
    const inMain = !!bar.closest('main');
    const route = inMain ? ((location.hash || '#overview').slice(1).split(/[/?]/)[0] || 'overview') : 'global';
    const id = bar.id || (bar.getAttribute('aria-label') || [...bar.classList].filter((c) => c !== 'on').join('.') || 'bar');
    return 'tw.tabs.' + route + '.' + id;
  }
  // 預設順序＝DOM 順序；存下來的順序只排它認得的那幾顆，新出現的分頁跟在它在 DOM 裡前一顆的後面
  function merged(bar) {
    const els = items(bar), ids = els.map(itemId), saved = LS.get(key(bar));
    if (!Array.isArray(saved) || !saved.length) return els;
    const out = saved.map((s) => els[ids.indexOf(s)]).filter(Boolean);
    els.forEach((el, i) => {
      if (out.includes(el)) return;
      let j = i - 1; while (j >= 0 && !out.includes(els[j])) j--;
      out.splice(j < 0 ? 0 : out.indexOf(els[j]) + 1, 0, el);
    });
    return out;
  }
  function paint(bar, seq) {
    const els = items(bar), custom = seq.some((el, i) => el !== els[i]);
    seq.forEach((el, i) => { const v = custom ? String(i) : ''; if (el.style.order !== v) el.style.order = v; });
    bar.toggleAttribute('data-tdcustom', custom);
  }
  function apply(bar) {
    if (!isBar(bar)) return;
    if (!isAdm()) { strip(bar); return; }
    if (!bar.hasAttribute('data-tdrag')) {
      bar.setAttribute('data-tdrag', '');
      if (!bar.title) bar.title = TITLE;
    }
    paint(bar, merged(bar));
  }
  // 目前看到的順序：改過就照 style.order，沒改過就是 DOM 順序（不量版面，隱藏的分頁也排得進去）
  const visual = (bar) => { const els = items(bar);
    return bar.hasAttribute('data-tdcustom') ? els.slice().sort((x, y) => (+x.style.order || 0) - (+y.style.order || 0)) : els; };
  function save(bar, seq) {
    const els = items(bar);
    if (seq.every((el, i) => el === els[i])) LS.del(key(bar)); else LS.set(key(bar), seq.map(itemId));
    paint(bar, seq);
    bar.dispatchEvent(new CustomEvent('tabdrag:change', { bubbles: true, detail: { key: key(bar), order: seq.map(itemId) } }));
  }
  function scan(root) {
    const r = root && root.nodeType === 1 ? root : document;
    if (r !== document && isBar(r)) apply(r);
    r.querySelectorAll(SEL).forEach(apply);
  }

  /* ---------- 樣式（自帶，不依賴任何一頁的 CSS） ---------- */
  const css = document.createElement('style');
  css.textContent = `[data-tdrag] > *{-webkit-user-drag:none}
[data-tdrag] > .td-src{opacity:.5;outline:1px dashed var(--line-2,#888);outline-offset:-1px}
html.td-dragging, html.td-dragging *{cursor:grabbing!important;user-select:none!important}
.td-menu{position:fixed;z-index:10050;background:var(--panel,#fff);border:1px solid var(--line-2,#ccc);border-radius:8px;
  box-shadow:0 6px 20px rgba(0,0,0,.25);padding:4px;font-size:13px;color:var(--ink,#111)}
.td-menu button{display:block;width:100%;text-align:left;background:none;border:0;color:inherit;font:inherit;padding:6px 12px;border-radius:6px;cursor:pointer;white-space:nowrap}
.td-menu button:hover,.td-menu button:focus{background:var(--panel-3,rgba(127,127,127,.15));outline:none}`;
  (document.head || document.documentElement).appendChild(css);

  /* ---------- 滑鼠拖曳 ---------- */
  let D = null, eatClick = false;
  const itemOf = (t) => { const bar = t && t.closest && t.closest('[data-tdrag]'); if (!bar || !isBar(bar)) return null;
    const it = items(bar).find((c) => c.contains(t)); return it ? { bar, it } : null; };
  document.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 || e.pointerType === 'touch') return;
    const h = itemOf(e.target); if (!h || items(h.bar).length < 2) return;
    D = { ...h, x: e.clientX, y: e.clientY, on: false };
  });
  document.addEventListener('pointermove', (e) => {
    if (!D) return;
    if (!D.on) {
      if (Math.hypot(e.clientX - D.x, e.clientY - D.y) < 6) return;
      D.on = true; D.it.classList.add('td-src'); document.documentElement.classList.add('td-dragging');
    }
    e.preventDefault();
    const seq = visual(D.bar), over = seq.find((c) => { const r = c.getBoundingClientRect();
      return e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top - 6 && e.clientY <= r.bottom + 6; });
    if (!over || over === D.it) return;
    const from = seq.indexOf(D.it), to = seq.indexOf(over);
    seq.splice(from, 1); seq.splice(to, 0, D.it);
    paint(D.bar, seq);          // 拖曳中只換視覺位置，放開才存
  });
  const end = () => {
    if (!D) return;
    if (D.on) {
      D.it.classList.remove('td-src'); document.documentElement.classList.remove('td-dragging');
      save(D.bar, visual(D.bar));
      eatClick = true; setTimeout(() => { eatClick = false; }, 0);
    }
    D = null;
  };
  document.addEventListener('pointerup', end);
  document.addEventListener('pointercancel', end);
  window.addEventListener('click', (e) => { if (eatClick) { eatClick = false; e.stopPropagation(); e.preventDefault(); } }, true);
  document.addEventListener('dragstart', (e) => { if (itemOf(e.target)) e.preventDefault(); });

  /* ---------- 鍵盤：Alt+←／→ ---------- */
  document.addEventListener('keydown', (e) => {
    if (!e.altKey || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    const h = itemOf(document.activeElement); if (!h) return;
    e.preventDefault(); e.stopPropagation();       // 也擋掉瀏覽器的 Alt+← 上一頁
    const seq = visual(h.bar), i = seq.indexOf(h.it), j = i + (e.key === 'ArrowLeft' ? -1 : 1);
    if (j < 0 || j >= seq.length) return;
    seq.splice(i, 1); seq.splice(j, 0, h.it);
    save(h.bar, seq); h.it.focus();
  }, true);

  /* ---------- 右鍵：還原預設順序（只在改過的分頁列出現，沒改過就是瀏覽器原本的右鍵） ---------- */
  let menu = null;
  const closeMenu = () => { if (menu) { menu.remove(); menu = null; } };
  function reset(bar) { LS.del(key(bar)); paint(bar, items(bar));
    bar.dispatchEvent(new CustomEvent('tabdrag:change', { bubbles: true, detail: { key: key(bar), order: items(bar).map(itemId) } })); }
  document.addEventListener('contextmenu', (e) => {
    const h = itemOf(e.target); if (!h || !h.bar.hasAttribute('data-tdcustom')) return;
    e.preventDefault(); closeMenu();
    menu = document.createElement('div'); menu.className = 'td-menu'; menu.setAttribute('role', 'menu');
    menu.innerHTML = '<button type="button" role="menuitem" data-tdreset>↺ 還原預設順序</button>';
    menu.style.left = Math.min(e.clientX, innerWidth - 180) + 'px'; menu.style.top = Math.min(e.clientY, innerHeight - 50) + 'px';
    menu.querySelector('button').onclick = () => { reset(h.bar); closeMenu(); };
    document.body.appendChild(menu); menu.querySelector('button').focus();
  });
  document.addEventListener('pointerdown', (e) => { if (menu && !menu.contains(e.target)) closeMenu(); }, true);
  document.addEventListener('keydown', (e) => { if (menu && e.key === 'Escape') closeMenu(); });
  window.addEventListener('hashchange', closeMenu);

  /* ---------- 自動掛載 ---------- */
  const mo = new MutationObserver((recs) => {
    const bars = new Set();
    for (const r of recs) {
      const t = r.target.nodeType === 1 ? r.target : r.target.parentElement;
      const b = t && t.closest(SEL); if (b) bars.add(b);
      r.addedNodes.forEach((n) => { if (n.nodeType !== 1) return; if (n.matches(SEL)) bars.add(n); n.querySelectorAll(SEL).forEach((x) => bars.add(x)); });
    }
    bars.forEach(apply);
  });
  /* 身分換了（登入／登出／被加為或移除管理者）→ 整頁重掃：非管理者拔掉拖曳、清掉已存順序 */
  function recheck() { if (!isAdm()) { purge(); D = null; document.documentElement.classList.remove('td-dragging'); document.querySelectorAll('[data-tdrag]').forEach(strip); } scan(document); }
  window.addEventListener('tw:account', recheck);
  function start() { if (!isAdm()) purge(); scan(document); mo.observe(document.body, { childList: true, subtree: true }); }
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);

  window.TabDrag = { scan, reset, key, enabled: isAdm, order: (bar) => visual(bar).map(itemId) };
})();
