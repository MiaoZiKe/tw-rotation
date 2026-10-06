/* ============================================================================
   通知中心（sub-v1，2026-10-05）—— 鈴鐺、公告頁 #notices、置頂橫幅、管理端 #admin/notices
   ----------------------------------------------------------------------------
   Andy：「之後有活動或是變更會需要通知大家」。回答的問題：「網站最近有什麼我該知道的變動？」
     · 右上角鈴鐺（未讀數紅點）→ 下拉列出公告（類型、標題、日期、內容）。點一則＝展開內容＋標已讀；「全部標為已讀」；「查看全部」到 #notices。
     · 已讀存哪：訪客 localStorage（tw.notice.read）；登入者存 Worker（notice_reads，跨裝置），本機也記一份當快取。
     · 新的「置頂」公告：開站時若未讀，頁首顯示一條可關閉的橫幅（關掉＝標已讀）。
     · 內文是純文字：一律先跳脫，再把 http(s) 網址轉成連結 —— 不收 HTML，管理者也塞不進 <script>。
     · 對象過濾在 Worker 做（/v1/notices 只回「這個人該看到、而且上架中」的），前端不自己判斷。
   管理端 #admin/notices（只有管理者）：發佈／編輯／下架／刪除；欄位：標題、內容、類型、對象、上架與下架時間、置頂。
     不掛進 admin.js（另一條分支正在改），這一頁由這支自己畫，跟 support.js 的 #admin/feedback 共用 #v-subadm。
   會員功能沒設定（沒有 Worker）→ 沒有公告來源，鈴鐺不出現。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  if (!T()) return;
  const { esc, css, call, view, toast, ls } = T();
  const K_READ = 'tw.notice.read', K_BAN = 'tw.notice.banner';
  const KINDS = { event: '活動', feature: '功能更新', maint: '維護', plan: '方案異動' };
  const AUD = [['all', '全部'], ['guest', '訪客'], ['member', '註冊會員（含付費）'], ['paid', '付費會員']];
  const S = { list: [], loaded: false, open: false, expand: null, at: 0 };
  const A = () => window.TwAccount;
  const logged = () => { const a = A(); return !!(a && a.on() && a.user()); };
  const localRead = () => { try { const a = JSON.parse(ls.get(K_READ) || '[]'); return new Set(Array.isArray(a) ? a : []); } catch (e) { return new Set(); } };
  const saveLocal = (set) => ls.set(K_READ, JSON.stringify([...set].slice(-300)));
  const isRead = (n) => n.read === true || localRead().has(n.id);
  const unread = () => S.list.filter((n) => !isRead(n));
  const dstr = (ms) => new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, '/');
  /* 純文字 → 安全 HTML：先跳脫、換行變 <br>、網址變連結 */
  const rich = (s) => esc(s).replace(/https?:\/\/[^\s<>"']+/g, (u) => `<a href="${u}" target="_blank" rel="noopener noreferrer">${u}</a>`).replace(/\n/g, '<br>');

  css('noticesCss', `
.ntbell{position:relative;display:inline-grid;place-items:center;width:34px;height:34px;box-sizing:border-box;padding:0;border:1px solid var(--line-2);border-radius:var(--r-sm,9px);background:var(--panel-2);color:var(--ink);cursor:pointer;flex:none}
.ntbell svg{display:block;width:17px;height:17px}
.ntbell .dot{position:absolute;top:-6px;right:-6px;min-width:18px;height:18px;padding:0 5px;box-sizing:border-box;border-radius:999px;background:var(--rise);color:#fff;font-size:11.5px;font-weight:700;line-height:18px;text-align:center}
.ntbell .dot[hidden]{display:none}
.ntdrop{position:fixed;z-index:1300;width:min(380px,calc(100vw - 24px));max-height:min(560px,calc(100vh - 90px));display:flex;flex-direction:column;background:var(--panel-2);color:var(--ink);
  border:1px solid var(--line-2);border-radius:14px;box-shadow:0 20px 50px -18px rgba(0,0,0,.75);overflow:hidden}
.ntdrop[hidden]{display:none}
.ntdrop .nth{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--line)}
.ntdrop .nth b{flex:1;font-size:15px}
.ntdrop .nth button{background:none;border:0;color:var(--cyan);font-size:13px;cursor:pointer;padding:4px}
.ntdrop .ntl{overflow:auto}
.ntdrop .ntf{display:flex;justify-content:center;border-top:1px solid var(--line)}
.ntdrop .ntf a{display:block;padding:10px;color:var(--cyan);font-size:13.5px;text-decoration:none}
.ntitem{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);padding:11px 14px;color:var(--ink);cursor:pointer;font:inherit}
.ntitem.unread{background:color-mix(in srgb,var(--cyan) 7%,transparent)}
.ntitem .r1{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--ink-2)}
.ntitem .r1 .u{width:8px;height:8px;border-radius:50%;background:var(--rise);flex:none}
.ntitem .ttl{display:block;font-size:14.5px;font-weight:600;margin:3px 0 2px;line-height:1.45}
.ntitem .bd{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13px;color:var(--ink-2);line-height:1.6}
.ntitem.ex .bd{display:block;-webkit-line-clamp:unset}
.ntkind{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink)}
.ntkind.k-event{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 50%,transparent)}
.ntkind.k-feature{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 50%,transparent)}
.ntkind.k-maint{color:var(--rise);border-color:color-mix(in srgb,var(--rise) 50%,transparent)}
.ntkind.k-plan{color:var(--violet);border-color:color-mix(in srgb,var(--violet) 50%,transparent)}
.ntpin{font-size:11.5px;color:var(--amber)}
.ntempty{padding:22px 14px;text-align:center;color:var(--ink-2);font-size:13.5px}
.ntban{position:relative;z-index:30;display:flex;align-items:center;gap:12px;margin:8px auto 0;max-width:1280px;padding:10px 14px;border-radius:12px;
  background:color-mix(in srgb,var(--amber) 16%,var(--panel));border:1px solid color-mix(in srgb,var(--amber) 45%,transparent);color:var(--ink);font-size:14px}
.ntban b{white-space:nowrap}
.ntban .tx{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ntban a.more{color:var(--cyan);white-space:nowrap}
.ntban button{background:none;border:0;color:var(--ink-2);font-size:20px;cursor:pointer;width:30px;height:30px;border-radius:8px;flex:none}
#v-notices{max-width:880px;margin:0 auto;padding-top:14px}
#v-notices .nphead{display:flex;align-items:center;gap:10px;margin:8px 0 10px}
#v-notices .nphead h2{margin:0;font-size:20px;flex:1}
#v-notices .nphead button{height:32px;padding:0 12px;border:1px solid var(--line-2);border-radius:8px;background:var(--panel-2);color:var(--ink);font-size:13.5px;cursor:pointer}
#v-notices .npi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
#v-notices .npi.unread{border-color:color-mix(in srgb,var(--cyan) 55%,transparent)}
#v-notices .npi h3{margin:6px 0 6px;font-size:16.5px}
#v-notices .npi .bd{font-size:14px;line-height:1.75;color:var(--ink-2)}
#v-notices .npi .r1{display:flex;gap:8px;align-items:center;font-size:12.5px;color:var(--ink-2)}
#v-subadm .ntform{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 16px}
#v-subadm .ntform .w2{grid-column:span 2}
#v-subadm .ntform label{display:block;font-size:13px;color:var(--ink-2);margin-bottom:4px}
#v-subadm .ntform input,#v-subadm .ntform select,#v-subadm .ntform textarea{width:100%;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:8px 10px;font:inherit;font-size:14px}
#v-subadm .ntform textarea{min-height:120px;resize:vertical}
#v-subadm .ntform .chk{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--ink)}
#v-subadm .ntform .chk input{width:auto}
#v-subadm .ntact{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
#v-subadm .ntact button{height:36px;padding:0 16px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:14px;cursor:pointer}
#v-subadm .ntact button.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .ntact .msg{font-size:13.5px}
#v-subadm .ntact .msg.bad{color:var(--rise)}#v-subadm .ntact .msg.ok{color:var(--fall)}`);

  // ------------------------------------------------------------------ 資料
  /* 2026-10-06（流量批次）：開一頁原本會打 2～3 次 /v1/notices（boot、tw:account-config、tw:account 各一次）。
     改成：同一個人 10 分鐘內只打一次，結果放 sessionStorage（tw.nt.c）；進行中的那一次大家共用。
     換人（登入／登出）快取鍵不同 → 重抓；TwNotices.refresh() 是明確要最新 → force 不看快取。*/
  const NT_TTL = 10 * 60 * 1000, NT_KEY = 'tw.nt.c';
  let ntFly = null;
  function ntWho() { const a = A(), u = a && a.user ? a.user() : null; return u && u.email ? String(u.email) : '-'; }
  function fetchList(force) {
    const a = A(); if (!a || !a.on()) { S.list = []; S.loaded = false; paintBell(); return Promise.resolve(); }
    if (!force) {
      if (ntFly) return ntFly;
      try {
        const c = JSON.parse(sessionStorage.getItem(NT_KEY) || 'null');
        if (c && c.who === ntWho() && Date.now() - c.at < NT_TTL && Array.isArray(c.notices)) return Promise.resolve(fetchDone({ _s: 200, notices: c.notices }));
      } catch (e) { /* 沒快取就照抓 */ }
    }
    const who = ntWho();
    ntFly = call('/v1/notices', {}).then((j) => {
      ntFly = null;
      if (j && j._s === 200 && Array.isArray(j.notices)) { try { sessionStorage.setItem(NT_KEY, JSON.stringify({ who, at: Date.now(), notices: j.notices })); } catch (e) { /* 略 */ } }
      return fetchDone(j);
    });
    return ntFly;
  }
  function fetchDone(j) {
    if (j && j._s === 200 && Array.isArray(j.notices)) {
      S.list = j.notices; S.loaded = true; S.at = Date.now();
      /* 伺服器說讀過的，本機也記起來（下次離線時紅點不會又冒出來）*/
      const set = localRead(); let g = false; S.list.forEach((n) => { if (n.read === true && !set.has(n.id)) { set.add(n.id); g = true; } }); if (g) saveLocal(set);
    }
    paintBell(); paintBanner();
    if (S.open) paintDrop();
    if ((location.hash || '').startsWith('#notices')) paintPage();
  }
  async function markRead(ids) {
    ids = ids.filter(Boolean); if (!ids.length) return;
    const set = localRead(); ids.forEach((id) => set.add(id)); saveLocal(set);
    S.list.forEach((n) => { if (ids.includes(n.id)) n.read = logged() ? true : n.read; });
    paintBell(); paintBanner();
    if (logged()) await call('/v1/notices/read', { ids });
  }

  // ------------------------------------------------------------------ 鈴鐺＋下拉
  const BELL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>';
  function paintBell() {
    const a = A();
    let b = document.getElementById('ntBell');
    if (!a || !a.on()) { if (b) b.remove(); return; }
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = 'ntBell'; b.className = 'ntbell'; b.setAttribute('aria-haspopup', 'dialog');
      b.innerHTML = BELL + '<span class="dot" id="ntDot" hidden></span>';
      b.onclick = (e) => { e.stopPropagation(); toggleDrop(); };
    }
    place(b);
    const n = unread().length;
    const dot = b.querySelector('.dot');
    dot.hidden = n === 0; dot.textContent = n > 99 ? '99+' : String(n);
    b.setAttribute('aria-label', n ? `通知：${n} 則未讀` : '通知');
    b.title = b.getAttribute('aria-label');
  }
  /* 放哪：電腦版（layout4 掛 l4）右上角工具列是 #l4Tools —— 放在它「前面」當兄弟節點，不放進去：
     layout4 的 syncTools 會依固定清單重排 #l4Tools 的子節點，放進去會被當成多出來的節點、每次都重排（而它又被觀察器叫醒）。
     沒有 l4（窄畫面）→ 放進 account.js 的 .acctbar 最前面。 */
  function place(b) {
    const tools = document.getElementById('l4Tools');
    const vis = (el) => !!el && el.getClientRects().length > 0;
    if (tools && vis(tools)) { if (b.nextElementSibling !== tools) tools.parentNode.insertBefore(b, tools); return; }
    const bar = window.TwAcctBar ? window.TwAcctBar() : null; if (!bar) return;
    if (bar.firstChild !== b) bar.insertBefore(b, bar.firstChild);
  }
  /* 換頁時通知下拉一律收起（2026-10-06 預設狀態普查：從下拉點「查看全部」以外的連結換頁也不該留著）*/
  window.addEventListener('hashchange', () => { if (S.open) toggleDrop(false); setTimeout(paintBell, 50); });
  let rzT = 0; window.addEventListener('resize', () => { clearTimeout(rzT); rzT = setTimeout(paintBell, 250); });
  function toggleDrop(want) {
    const open = want == null ? !S.open : want;
    S.open = open;
    let d = document.getElementById('ntDrop');
    if (!open) { if (d) d.hidden = true; return; }
    if (!d) {
      d = document.createElement('div'); d.id = 'ntDrop'; d.className = 'ntdrop'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', '通知');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => {
        const it = e.target.closest('.ntitem');
        if (e.target.closest('a')) { if (e.target.closest('#ntAll')) toggleDrop(false); return; }
        if (e.target.closest('#ntReadAll')) { markRead(unread().map((n) => n.id)).then(paintDrop); paintDrop(); return; }
        if (it) { S.expand = S.expand === it.dataset.id ? null : it.dataset.id; markRead([it.dataset.id]); paintDrop(); }
      });
    }
    d.hidden = false;
    paintDrop();
    if (Date.now() - S.at > 60000) fetchList();
  }
  function itemHTML(n) {
    const u = !isRead(n);
    return `<button type="button" class="ntitem${u ? ' unread' : ''}${S.expand === n.id ? ' ex' : ''}" data-id="${esc(n.id)}" aria-expanded="${S.expand === n.id}">
      <span class="r1">${u ? '<i class="u" aria-label="未讀"></i>' : ''}<span class="ntkind k-${esc(n.kind)}">${esc(KINDS[n.kind] || n.kind)}</span>${n.pinned ? '<span class="ntpin">置頂</span>' : ''}<span>${dstr(n.start)}</span></span>
      <span class="ttl">${esc(n.title)}</span><span class="bd">${rich(n.body)}</span></button>`;
  }
  function paintDrop() {
    const d = document.getElementById('ntDrop'); if (!d || d.hidden) return;
    const n = unread().length;
    d.innerHTML = `<div class="nth"><b>通知${n ? `（${n} 則未讀）` : ''}</b>${n ? '<button type="button" id="ntReadAll">全部標為已讀</button>' : ''}</div>
      <div class="ntl">${S.list.length ? S.list.slice(0, 20).map(itemHTML).join('') : '<div class="ntempty">目前沒有公告</div>'}</div>
      <div class="ntf"><a href="#notices" id="ntAll">查看全部</a></div>`;
    const b = document.getElementById('ntBell'); if (!b) return;
    const r = b.getBoundingClientRect();
    d.style.top = (r.bottom + 8) + 'px';
    d.style.left = Math.max(12, Math.min(innerWidth - d.offsetWidth - 12, r.right - d.offsetWidth)) + 'px';
  }
  document.addEventListener('pointerdown', (e) => {
    if (!S.open) return;
    if (e.target.closest('#ntDrop') || e.target.closest('#ntBell')) return;
    toggleDrop(false);
  }, true);

  // ------------------------------------------------------------------ 置頂橫幅
  function paintBanner() {
    const top = S.list.find((n) => n.pinned && !isRead(n));
    let b = document.getElementById('ntBanner');
    if (!top) { if (b) b.remove(); return; }
    const main = document.querySelector('main'); if (!main) return;
    if (!b) { b = document.createElement('div'); b.id = 'ntBanner'; b.className = 'ntban'; b.setAttribute('role', 'status'); main.insertBefore(b, main.firstChild); }
    if (b.dataset.id === top.id) return;
    b.dataset.id = top.id;
    b.innerHTML = `<span class="ntkind k-${esc(top.kind)}">${esc(KINDS[top.kind] || top.kind)}</span><b>${esc(top.title)}</b><span class="tx">${esc(top.body.replace(/\s+/g, ' '))}</span><a class="more" href="#notices">看全文</a><button type="button" aria-label="關閉這則公告">×</button>`;
    b.querySelector('button').onclick = () => markRead([top.id]);
    b.querySelector('a.more').onclick = () => markRead([top.id]);
  }

  // ------------------------------------------------------------------ 公告頁 #notices
  function paintPage() {
    const v = view('v-notices'); if (!v) return;
    const a = A();
    if (!a || !a.on()) { v.innerHTML = '<div class="nphead"><h2>公告</h2></div><div class="npi"><p class="bd">目前沒有公告。</p></div>'; return; }
    const n = unread().length;
    v.innerHTML = `<div class="nphead"><h2>公告</h2>${n ? `<button type="button" id="npReadAll">全部標為已讀（${n}）</button>` : ''}</div>
      ${S.list.length ? S.list.map((x) => `<article class="npi${isRead(x) ? '' : ' unread'}" data-id="${esc(x.id)}"><div class="r1"><span class="ntkind k-${esc(x.kind)}">${esc(KINDS[x.kind] || x.kind)}</span>${x.pinned ? '<span class="ntpin">置頂</span>' : ''}<span>${dstr(x.start)}</span>${isRead(x) ? '' : '<span style="color:var(--rise)">未讀</span>'}</div>
        <h3>${esc(x.title)}</h3><div class="bd">${rich(x.body)}</div></article>`).join('') : '<div class="npi"><p class="bd">目前沒有公告。</p></div>'}`;
    const ra = v.querySelector('#npReadAll'); if (ra) ra.onclick = () => markRead(unread().map((x) => x.id)).then(paintPage);
  }

  // ------------------------------------------------------------------ 管理端 #admin/notices
  /* datetime-local 的值一律當台北時間（使用者電腦不一定在台北）*/
  const toLocal = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 16) : '');
  const fromLocal = (s) => { const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)$/.exec(s || ''); return m ? Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5]) - 8 * 3600 * 1000 : 0; };
  const AS = { list: [], edit: null, plans: [] };
  async function renderNoticesAdmin(el) {
    const a = A(), u = a && a.on() ? a.user() : null;
    if (!u || !u.admin) { el.innerHTML = '<div class="card"><h2>管理頁</h2><p class="muted">這一頁只有管理者看得到' + (u ? '' : '，請先登入') + '。</p></div>'; return; }
    const [j, pj] = await Promise.all([call('/v1/admin/notices/list', {}), call('/v1/admin/plans/get', {})]);
    if (!j || j._s !== 200) { el.innerHTML = '<div class="card"><p class="muted">讀取失敗（' + esc(j ? j._s : '連不到') + '）</p></div>'; return; }
    AS.list = j.notices || []; AS.plans = (pj && pj.plans) || [];
    paintAdmin(el, j.now || Date.now());
  }
  function paintAdmin(el, now) {
    const e = AS.edit || { title: '', body: '', kind: 'feature', audience: 'all', start: 0, end: 0, pinned: false };
    const audOpts = AUD.concat(AS.plans.filter((p) => !p.builtin).map((p) => ['plan:' + p.id, '指定範本：' + p.name]));
    const state = (n) => (n.start > now ? '未上架' : n.end && n.end <= now ? '已下架' : '上架中');
    el.innerHTML = `<div class="sat"><h2>公告管理</h2><a href="#admin/feedback">意見反饋</a><a href="#notices">看使用者畫面</a><a href="#admin/traffic">回管理區</a></div>
      <div class="card"><h3>${AS.edit ? '編輯公告' : '發佈新公告'}</h3><p class="muted">內容是純文字（網址會自動變成連結，不收 HTML）。上架時間空白＝立刻；下架時間空白＝不下架。時間一律台北時間。</p>
      <div class="ntform">
        <div class="w2"><label for="ntTitle">標題</label><input id="ntTitle" maxlength="80" value="${esc(e.title)}"></div>
        <div class="w2"><label for="ntBody">內容</label><textarea id="ntBody" maxlength="2000">${esc(e.body)}</textarea></div>
        <div><label for="ntKind">類型</label><select id="ntKind">${Object.entries(KINDS).map(([k, n]) => `<option value="${k}" ${e.kind === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
        <div><label for="ntAud">對象</label><select id="ntAud">${audOpts.map(([k, n]) => `<option value="${esc(k)}" ${e.audience === k ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></div>
        <div><label for="ntStart">上架時間</label><input type="datetime-local" id="ntStart" value="${toLocal(e.start)}"></div>
        <div><label for="ntEnd">下架時間</label><input type="datetime-local" id="ntEnd" value="${toLocal(e.end)}"></div>
        <div class="w2"><label class="chk"><input type="checkbox" id="ntPin" ${e.pinned ? 'checked' : ''}> 置頂（未讀的人開站時頁首會出現橫幅）</label></div>
      </div>
      <div class="ntact"><button type="button" class="pri" id="ntSave">${AS.edit ? '儲存修改' : '發佈'}</button>${AS.edit ? '<button type="button" id="ntCancel">取消編輯</button>' : ''}<span class="msg" id="ntMsg" role="status"></span></div></div>
      <div class="card"><h3>所有公告（${AS.list.length}）</h3>
        ${AS.list.length ? `<table id="ntTable"><thead><tr><th>狀態</th><th>類型</th><th>標題</th><th>對象</th><th>上架</th><th>下架</th><th>已讀（會員）</th><th></th></tr></thead><tbody>${AS.list.map((n) => `<tr data-id="${esc(n.id)}">
          <td>${state(n)}${n.pinned ? '<br><span class="ntpin">置頂</span>' : ''}</td><td><span class="ntkind k-${esc(n.kind)}">${esc(KINDS[n.kind] || n.kind)}</span></td><td>${esc(n.title)}</td>
          <td>${esc((audOpts.find((x) => x[0] === n.audience) || [0, n.audience])[1])}</td><td>${toLocal(n.start).replace('T', ' ')}</td><td>${n.end ? toLocal(n.end).replace('T', ' ') : '—'}</td><td>${n.reads || 0}</td>
          <td><button type="button" data-a="edit">編輯</button> ${state(n) === '上架中' ? '<button type="button" data-a="off">下架</button>' : ''} <button type="button" data-a="del">刪除</button></td></tr>`).join('')}</tbody></table>` : '<p class="muted">還沒有公告。</p>'}</div>`;
    const msg = el.querySelector('#ntMsg');
    el.querySelector('#ntSave').onclick = async () => {
      const body = { title: el.querySelector('#ntTitle').value.trim(), body: el.querySelector('#ntBody').value.trim(), kind: el.querySelector('#ntKind').value,
        audience: el.querySelector('#ntAud').value, start: fromLocal(el.querySelector('#ntStart').value), end: fromLocal(el.querySelector('#ntEnd').value), pinned: el.querySelector('#ntPin').checked };
      if (!body.title || !body.body) { msg.className = 'msg bad'; msg.textContent = '標題與內容都要填'; return; }
      if (AS.edit) body.id = AS.edit.id;
      const j = await call('/v1/admin/notices/put', body);
      if (j && j._s === 200) { AS.edit = null; toast(body.id ? '已儲存' : '已發佈'); await renderNoticesAdmin(el); fetchList(true); }
      else { msg.className = 'msg bad'; msg.textContent = j && j.error === 'bad_range' ? '下架時間要晚於上架時間' : '儲存失敗（' + esc(j ? j.error || j._s : '連不到') + '）'; }
    };
    const c = el.querySelector('#ntCancel'); if (c) c.onclick = () => { AS.edit = null; paintAdmin(el, now); };
    el.querySelectorAll('#ntTable button[data-a]').forEach((b) => {
      b.onclick = async () => {
        const n = AS.list.find((x) => x.id === b.closest('tr').dataset.id); if (!n) return;
        if (b.dataset.a === 'edit') { AS.edit = n; paintAdmin(el, now); el.querySelector('#ntTitle').focus(); return; }
        if (b.dataset.a === 'del' && !confirm(`刪除「${n.title}」？已讀紀錄會一起刪除，無法復原。`)) return;
        const j = b.dataset.a === 'del' ? await call('/v1/admin/notices/del', { id: n.id })
          : await call('/v1/admin/notices/put', { id: n.id, title: n.title, body: n.body, kind: n.kind, audience: n.audience, start: Math.min(n.start, Date.now() - 1000), end: Date.now(), pinned: n.pinned });
        if (j && j._s === 200) { toast(b.dataset.a === 'del' ? '已刪除' : '已下架'); await renderNoticesAdmin(el); fetchList(true); } else toast('操作失敗');
      };
    });
  }

  window.TwSubRoutes.push((head, rest) => {
    if (head === 'notices') { paintPage(); if (!S.loaded) fetchList(); return 'v-notices'; }
    if (head === 'admin' && rest[0] === 'notices') { const v = view('v-subadm'); if (!v) return null; v.innerHTML = '<div class="card"><p class="muted">載入中…</p></div>'; renderNoticesAdmin(v); return 'v-subadm'; }
    return null;
  });
  window.addEventListener('tw:account', () => {
    fetchList();
    if ((location.hash || '') === '#admin/notices') { const v = view('v-subadm'); if (v) renderNoticesAdmin(v); }
  });
  window.addEventListener('tw:account-config', () => { paintBell(); fetchList(); });
  setInterval(() => { if (!document.hidden) fetchList(); }, 10 * 60 * 1000);
  window.TwNotices = { refresh: () => fetchList(true), open: () => toggleDrop(true), unread: () => unread().length, list: () => S.list.slice(), renderNoticesAdmin };
  function boot() { const a = A(); if (a && a.on()) { paintBell(); fetchList(); } }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
