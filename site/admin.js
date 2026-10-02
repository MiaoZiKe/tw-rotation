/* ============================================================================
   管理頁 #admin：使用統計、目前誰在線上、會員名單（只有管理者看得到）
   · 這支只在「已登入的管理者打開 #admin」時才由 account.js 載入，一般訪客完全不下載它。
   · 真正的權限檢查在 Worker（ADMIN_EMAILS）：就算有人把這支檔案叫出來，沒有管理者權杖一樣拿不到任何資料。
   · 圖用純 HTML 長條（不用 ECharts）：資料只有十幾列，HTML 在任何寬度都不會被裁、手機也不用另外調。
   每張卡片標題就是它回答的問題，下面一行寫「所以我該怎麼用」。
   ========================================================================== */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const VIEW_NAME = { overview: '總覽', flow: '資金流向', industry: '產業地圖', heatmap: '熱力圖', market: '市場明細', season: '週期統計',
    delivery: '交付清單', stock: '個股頁', legal: '法律頁', watch: '自選清單', other: '其他' };
  const EV_NAME = { session: '開啟網站（每個分頁一次）', session_login: '登入狀態下開啟網站', login: '登入', logout: '登出',
    search: '搜尋股票', watch_add: '加入自選', watch_remove: '移出自選', watch_tab_new: '新增自選分頁', watch_panel: '打開自選清單',
    stock_tab: '切個股分頁（營收／籌碼…）', k_period: '切 K 線週期', ai_tab: '切 AI 分析面向', open_3d: '打開 3D 剖析圖', zoom: '放大圖表',
    how: '打開「?」說明', theme_toggle: '切深淺色', events_drawer: '打開今日事件', mtf: '四週期同看', indicators: '打開指標設定', draw: '畫線工具', m_seg: '手機切分段' };
  const S = { days: 30, timer: 0, v: null, A: null };

  function css() {
    if (document.getElementById('admCss')) return;
    const s = document.createElement('style'); s.id = 'admCss';
    s.textContent = `
#v-admin .admgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .card{min-width:0}
#v-admin h2{margin:0;font-size:18px}#v-admin h3{margin:0 0 2px;font-size:16px}
#v-admin .use{font-size:13px;color:var(--ink-2);margin:0 0 10px}
#v-admin .admtop{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
#v-admin .admtop .sp{flex:1}
#v-admin .admtop select,#v-admin .admtop button{height:32px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin .kpis{display:flex;gap:18px;flex-wrap:wrap;margin:4px 0 10px}
#v-admin .kpis div{font-size:13px;color:var(--ink-2)}#v-admin .kpis b{display:block;font-size:26px;color:var(--ink);font-family:var(--mono)}
#v-admin .bars{display:grid;grid-template-columns:minmax(0,11em) minmax(0,1fr) auto;gap:6px 10px;align-items:center;font-size:13.5px}
#v-admin .bars .bl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-admin .bars .bt{height:14px;background:var(--panel-3);border-radius:4px;overflow:hidden}
#v-admin .bars .bt i{display:block;height:100%;background:var(--cyan);border-radius:4px}
#v-admin .bars .bn{font-family:var(--mono);text-align:right;min-width:3em}
#v-admin .days{display:flex;align-items:flex-end;gap:2px;height:120px;border-bottom:1px solid var(--line);padding-top:6px}
#v-admin .days i{flex:1;min-width:2px;background:var(--violet);border-radius:3px 3px 0 0}
#v-admin .dayx{display:flex;justify-content:space-between;font-size:12px;color:var(--ink-2);margin-top:4px}
#v-admin table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-admin th,#v-admin td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
#v-admin th{color:var(--ink-2);font-weight:500;font-size:12.5px}
#v-admin .empty{color:var(--ink-2);font-size:13px;padding:10px 0}
#v-admin label.tg{display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer}
#v-admin label.tg input{width:18px;height:18px}
#v-admin .err{color:#ff6b7a}
#v-admin .admnav{display:flex;gap:6px;flex-wrap:wrap}
#v-admin .admnav a{display:inline-flex;align-items:center;height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);color:var(--ink-2);text-decoration:none;font-size:13.5px}
#v-admin .admnav a.on{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .pmbar{display:flex;align-items:center;gap:8px 10px;flex-wrap:wrap;margin-top:8px}
#v-admin .pmbar input,#v-admin .pmbar select{height:34px;font-size:14px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;min-width:0}
#v-admin .pmbar input[type=email]{flex:1 1 240px;max-width:360px}
#v-admin .pmbar button{height:34px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 12px;cursor:pointer}
#v-admin .pmbar button.pri{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .pmbar button.danger{color:#ff6b7a}
#v-admin .pmbar button:disabled,#v-admin .pmcat button:disabled{opacity:.45;cursor:not-allowed}
#v-admin .pmwho{font-size:13.5px;color:var(--ink-2);margin-top:8px;min-height:1.4em}
#v-admin .pmwho b{color:var(--ink)}
#v-admin .pmstat{font-size:13px;margin-top:6px;min-height:1.3em;color:var(--ink-2)}
#v-admin .pmstat.ok{color:#35d07f}#v-admin .pmstat.bad{color:#ff6b7a}
#v-admin .pmcats{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .pmcats.off{opacity:.5;pointer-events:none}
#v-admin .pmcathd{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px}
#v-admin .pmcathd h3{margin:0;flex:1;min-width:0}
#v-admin .pmcathd h3 small{font-size:12.5px;color:var(--ink-2);font-weight:400;margin-left:6px}
#v-admin .pmcathd button{height:30px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin .pmrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
#v-admin .pmrow .pmtx b{display:block;font-size:14px;font-weight:600}
#v-admin .pmrow .pmtx small{display:block;font-size:12.5px;color:var(--ink-2);line-height:1.45}
#v-admin .pmrow .pmside{display:flex;align-items:center;gap:6px}
#v-admin .pmtag{font-size:12px;padding:1px 6px;border-radius:6px;background:color-mix(in srgb,var(--amber,#f5b942) 22%,transparent);color:var(--ink);white-space:nowrap}
#v-admin .pmrev{font-size:12px;background:none;border:0;color:var(--cyan);cursor:pointer;padding:2px 4px}
#v-admin label.psw{position:relative;display:inline-block;width:44px;height:24px;flex:none}
#v-admin label.psw input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer;z-index:1}
#v-admin label.psw span{position:absolute;inset:0;border-radius:12px;background:var(--panel-3);border:1px solid var(--line-2);transition:background .15s}
#v-admin label.psw span::before{content:'';position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;background:var(--ink-2);transition:transform .15s,background .15s}
#v-admin label.psw input:checked+span{background:var(--cyan);border-color:var(--cyan)}
#v-admin label.psw input:checked+span::before{transform:translateX(20px);background:#fff}
#v-admin label.psw input:focus-visible+span{outline:2px solid var(--cyan);outline-offset:2px}
#v-admin label.psw input:disabled{cursor:not-allowed}
#v-admin .pmrow select{height:30px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px}
#v-admin table.pmlist{table-layout:fixed}#v-admin .pmlist th,#v-admin .pmlist td{white-space:normal!important;overflow-wrap:anywhere}#v-admin .pmlist th:nth-child(1){width:42%}#v-admin .pmlist th:nth-child(3){width:3.5em}#v-admin .pmlist tr{cursor:pointer}#v-admin .pmlist tr:hover td{background:var(--row-hover)}
#v-admin .pmwarn{font-size:13px;color:var(--ink-2);line-height:1.6;margin:0}
@media (max-width:820px){ #v-admin .admgrid{grid-template-columns:minmax(0,1fr)} #v-admin .bars{grid-template-columns:minmax(0,8em) minmax(0,1fr) auto} }`;
    document.head.appendChild(s);
  }
  const ago = (ms) => { const s = Math.max(0, Math.round((Date.now() - ms) / 1000)); return s < 60 ? s + ' 秒前' : Math.round(s / 60) + ' 分前'; };
  const dstr = (ms) => { if (!ms) return '—'; const d = new Date(ms + 8 * 3600 * 1000); return d.toISOString().slice(0, 16).replace('T', ' '); };

  function bars(list, names, total) {
    if (!list.length) return '<div class="empty">這段期間還沒有紀錄。</div>';
    const max = Math.max(...list.map((x) => x[1]), 1);
    return '<div class="bars">' + list.map(([k, n]) => `<span class="bl" title="${esc(k)}">${esc(names[k] || k)}</span><span class="bt"><i style="width:${(n / max * 100).toFixed(1)}%"></i></span>`
      + `<span class="bn">${n.toLocaleString('en-US')}${total ? `<small style="color:var(--ink-2)"> ${(n / total * 100).toFixed(0)}%</small>` : ''}</span>`).join('') + '</div>';
  }

  async function paint() {
    const v = S.v, A = S.A; if (!v || !A) return;
    const [st, on] = await Promise.all([A.call('/v1/admin/stats', { days: S.days }), A.call('/v1/admin/online', {})]);
    if (!(location.hash || '').startsWith('#admin') || /^#admin\/perm/.test(location.hash) || !v.querySelector('#admBody')) return;
    if (!st || st._s !== 200 || !on || on._s !== 200) {
      v.querySelector('#admBody').innerHTML = `<div class="card"><p class="err">讀不到報表（${st ? st._s : '連不到伺服器'}）。只有管理者帳號看得到；若你是管理者，確認 Worker 的 ADMIN_EMAILS 有你的 email（docs/login_setup.md 第 6 步）。</p></div>`;
      return;
    }
    const pv = {}, ev = {}, perDay = {};
    st.rows.forEach((r) => {
      const [kind, name] = r.k.split(':');
      if (kind === 'pv') { pv[name] = (pv[name] || 0) + r.n; perDay[r.day] = (perDay[r.day] || 0) + r.n; } else ev[name] = (ev[name] || 0) + r.n;
    });
    const pvList = Object.entries(pv).sort((a, b) => b[1] - a[1]);
    const evList = Object.entries(ev).filter(([k]) => !['session', 'session_login', 'login', 'logout'].includes(k)).sort((a, b) => b[1] - a[1]);
    const pvTotal = pvList.reduce((s, x) => s + x[1], 0);
    // 每一天都要有一格（沒有紀錄的日子是 0，不是跳過）
    const days = [];
    for (let t = Date.parse(st.from + 'T00:00:00Z'); t <= Date.parse(st.to + 'T00:00:00Z'); t += 86400000) days.push(new Date(t).toISOString().slice(0, 10));
    const dmax = Math.max(1, ...days.map((d) => perDay[d] || 0));
    const sessions = ev.session || 0, loginSess = ev.session_login || 0;
    v.querySelector('#admBody').innerHTML = `
      <div class="admgrid">
        <div class="card" id="admOnline"><h3>現在誰在線上？</h3><p class="use">最近 2 分半有動作的分頁。登入者列出名稱與所在頁面；訪客只算人數。每 30 秒自動更新。</p>
          <div class="kpis"><div><b id="admOnN">${on.total}</b>在線（分頁數）</div><div><b>${on.users.length}</b>登入者</div><div><b>${on.guests}</b>訪客</div></div>
          ${on.users.length ? `<table><thead><tr><th>名稱</th><th>email</th><th>在看</th><th>最後動作</th></tr></thead><tbody>${on.users.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${esc(VIEW_NAME[u.route] || u.route)}</td><td>${ago(u.seen)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">目前沒有登入者在線上。</div>'}
          <label class="tg" style="margin-top:12px"><input type="checkbox" id="admPub" ${on.public_online ? 'checked' : ''}>一般訪客看得到「目前 N 人在線」（只有總數，看不到名字）</label></div>
        <div class="card" id="admDays"><h3>每天有多少瀏覽？</h3><p class="use">每天的頁面瀏覽總次數（換頁一次算一次）。突然掉下來先查網站是不是壞了，突然衝高看當天發生了什麼。</p>
          <div class="kpis"><div><b>${pvTotal.toLocaleString('en-US')}</b>頁面瀏覽（${S.days} 天）</div><div><b>${sessions.toLocaleString('en-US')}</b>開啟次數</div><div><b>${loginSess.toLocaleString('en-US')}</b>其中登入狀態</div></div>
          <div class="days" id="admDayBars">${days.map((d) => `<i style="height:${((perDay[d] || 0) / dmax * 100).toFixed(1)}%" title="${d}：${perDay[d] || 0} 次"></i>`).join('')}</div>
          <div class="dayx"><span>${esc(st.from)}</span><span>${esc(st.to)}</span></div></div>
        <div class="card" id="admPv"><h3>哪一頁最多人看？</h3><p class="use">${S.days} 天內每一頁被打開的次數與佔比。排在後面的頁面，要嘛入口太深、要嘛內容不被需要 —— 改版優先順序就從這裡排。</p>${bars(pvList, VIEW_NAME, pvTotal)}</div>
        <div class="card" id="admEv"><h3>哪個功能最常被用？</h3><p class="use">${S.days} 天內每個功能被按的次數（完整定義見 docs/account_analytics.md）。常用的功能值得放到更顯眼的位置；幾乎沒人按的，考慮收起來或拿掉。</p>${bars(evList, EV_NAME, 0)}</div>
        <div class="card" id="admUsers" style="grid-column:1 / -1"><h3>有哪些會員？</h3><p class="use">共 ${st.users.total} 位；依最後使用時間排序（最多列 50 位）。24 個月沒有使用的會員會被系統自動刪除。</p>
          ${st.users.recent.length ? `<table><thead><tr><th>名稱</th><th>email</th><th>加入</th><th>最後使用（台北）</th></tr></thead><tbody>${st.users.recent.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${dstr(u.created)}</td><td>${dstr(u.seen)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">還沒有會員。</div>'}</div>
      </div>`;
    const pub = v.querySelector('#admPub');
    pub.onchange = async () => { const r = await A.call('/v1/admin/settings', { public_online: pub.checked }); if (!r || r._s !== 200) pub.checked = !pub.checked; };
  }

  /* 管理頁兩個分頁：#admin（使用統計與線上）、#admin/perm（功能權限，DECISIONS #288）。用網址分，上一頁回得來、可以直接貼網址。*/
  const nav = (cur) => `<nav class="admnav" aria-label="管理頁分頁"><a href="#admin" class="${cur === 'stats' ? 'on' : ''}" id="admNavStats">使用統計與線上</a>`
    + `<a href="#admin/perm" class="${cur === 'perm' ? 'on' : ''}" id="admNavPerm">功能權限</a></nav>`;
  function render(v, A) {
    css();
    S.v = v; S.A = A;
    if (/^#admin\/perm\b/.test(location.hash || '')) { clearInterval(S.timer); renderPerm(v, A); return; }
    const u = A.user() || {};
    v.innerHTML = `<div class="card" style="margin-top:16px"><div class="admtop"><h2>管理頁</h2><small style="color:var(--ink-2)">${esc(u.email || '')}</small>${nav('stats')}<span class="sp"></span>
        <label style="font-size:13.5px;color:var(--ink-2)">期間 <select id="admDaysSel">${[7, 30, 90, 365].map((d) => `<option value="${d}" ${d === S.days ? 'selected' : ''}>近 ${d} 天</option>`).join('')}</select></label>
        <button type="button" id="admRefresh">重新整理</button></div>
        <p class="use" style="margin:8px 0 0">使用統計只記「每天每一項的次數」（不記是誰、不存 IP），保留 13 個月；線上狀態離線即刪。這一頁只有管理者看得到。</p></div>
      <div id="admBody"><div class="card" style="margin-top:14px"><p class="use">載入中…</p></div></div>`;
    v.querySelector('#admDaysSel').onchange = (e) => { S.days = +e.target.value; paint(); };
    v.querySelector('#admRefresh').onclick = () => paint();
    paint();
    clearInterval(S.timer);
    S.timer = setInterval(() => { if ((location.hash || '').startsWith('#admin') && document.visibilityState !== 'hidden') paint(); else if (!(location.hash || '').startsWith('#admin')) clearInterval(S.timer); }, 30000);
  }
  /* ==========================================================================
     #admin/perm 功能權限（Andy 2026-10-02，DECISIONS #288）
     這頁回答一個問題：「這個會員（或這個方案）現在能用哪些功能？」所以我該怎麼用：
       ① 選「會員 email」→ 輸入或從清單挑一個 email → 先選方案範本（免費／付費…）→ 再逐項微調。
       ② 選「方案範本」→ 改一整組預設；沒有被個別指定的會員（與訪客）全部跟著變。
     每撥一個開關就立刻存（不必另外按儲存），存好會寫「已儲存（台北時間）」。
     資料怎麼合：features.js 的預設值 ← 方案範本 ← 個別微調（後面蓋前面）。
     範本只存「跟預設不同」的項目、微調只存「跟範本不同」的項目 —— 之後新增功能時，沒人設過的一律照預設（開），不會突然鎖住誰。
     ========================================================================== */
  const PS = { mode: 'member', email: '', rec: null, plans: [], planSel: 'free', list: null, confirmDel: false, A: null, v: null, seq: 0 };
  const FT = () => window.TwFeatures;
  const tpeTime = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(11, 19);
  function loadFeatures() {
    if (window.TwFeatures) return Promise.resolve();
    return new Promise((res) => {
      const s = document.createElement('script'); s.src = 'features.js'; s.onload = () => res(); s.onerror = () => res(); document.head.appendChild(s);
    });
  }
  const planOf = (id) => PS.plans.find((p) => p.id === id) || null;
  /* 目前畫面上要顯示的「基準」（範本）與「實際值」 */
  function baseVals() {
    const o = FT().defaults();
    const p = planOf(PS.mode === 'member' ? (PS.rec ? PS.rec.plan : 'free') : PS.planSel);
    if (p) Object.assign(o, p.feats);
    return o;
  }
  function curVals() {
    const o = baseVals();
    if (PS.mode === 'member' && PS.rec) Object.assign(o, PS.rec.over || {});
    return o;
  }
  function setStat(msg, cls) { const s = PS.v && PS.v.querySelector('#pmStat'); if (s) { s.textContent = msg; s.className = 'pmstat' + (cls ? ' ' + cls : ''); } }
  const ERR = { forbidden: '沒有管理者權限', bad_email: 'email 格式不對', bad_plan: '方案不存在', bad_feats: '開關格式不對', bad_name: '範本名稱不能空白', too_many: '數量超過上限', builtin: '內建範本不能刪' };
  const errText = (r) => !r ? '連不到伺服器' : (ERR[r.error] || ('HTTP ' + r._s)) + (r._s === 404 && !r.error ? '' : '');

  async function renderPerm(v, A) {
    PS.v = v; PS.A = A;
    const u = A.user() || {};
    v.innerHTML = `<div class="card" style="margin-top:16px"><div class="admtop"><h2>管理頁</h2><small style="color:var(--ink-2)">${esc(u.email || '')}</small>${nav('perm')}</div>
        <p class="use" style="margin:8px 0 0">替每個會員 email 決定能用哪些功能。關掉的功能在對方畫面上會蓋一個鎖頭與「此功能需開通」（不會整頁消失）。這一頁只有管理者看得到。</p></div>
      <div class="card" id="pmHead" style="margin-top:14px"><h3>要設定誰？</h3>
        <p class="use">「會員 email」＝替某一個人設定：先選方案範本，再個別微調。「方案範本」＝改一整組預設：「訪客」給沒登入的人、「免費會員」給登入後沒被指定方案的人。</p>
        <div class="seg" id="pmMode" role="tablist"><button type="button" data-m="member" class="${PS.mode === 'member' ? 'on' : ''}">會員 email</button><button type="button" data-m="plan" class="${PS.mode === 'plan' ? 'on' : ''}">方案範本</button></div>
        <div id="pmTarget"></div>
        <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div></div>
      <div class="pmcats" id="pmCats"></div>
      <div class="card" id="pmList" style="margin-top:14px"><h3>已經個別設定過的會員</h3><p class="use">點一列就載入那個人。沒列在這裡的會員＝套「免費會員」範本。</p><div id="pmListBody"><div class="empty">載入中…</div></div></div>
      <div class="card" style="margin-top:14px"><h3>這個鎖頭擋得住什麼？</h3><p class="pmwarn">鎖頭只擋一般使用者的畫面。這個網站是 GitHub Pages 靜態站，資料檔（site/data/*.json）是公開的，懂技術的人仍然能直接讀到。
        真正保護付費內容，要讓付費資料改由會員 Worker 驗證身分後才提供 —— 設計與工作量寫在 DECISIONS #288，這一版還沒做。</p></div>`;
    v.querySelector('#pmMode').onclick = (e) => {
      const b = e.target.closest('button[data-m]'); if (!b || b.dataset.m === PS.mode) return;
      PS.mode = b.dataset.m; PS.confirmDel = false;
      v.querySelectorAll('#pmMode button').forEach((x) => x.classList.toggle('on', x === b));
      paintTarget(); paintCats(); setStat('');
    };
    await loadFeatures();
    if (!FT()) { v.querySelector('#pmCats').innerHTML = '<div class="card"><p class="err">功能清單（features.js）載入失敗。</p></div>'; return; }
    const [pl, li] = await Promise.all([A.call('/v1/admin/plans/get', {}), A.call('/v1/admin/perm/list', {})]);
    if (!/^#admin\/perm\b/.test(location.hash || '')) return;
    if (!pl || pl._s !== 200) {
      v.querySelector('#pmCats').innerHTML = `<div class="card" style="grid-column:1/-1"><p class="err">讀不到方案範本（${esc(errText(pl))}）。${pl && pl._s === 404 ? '會員 Worker 可能還沒更新成有功能權限的版本（deploy-account-worker.yml）。' : '只有管理者帳號看得到；確認 Worker 的 ADMIN_EMAILS 有你的 email。'}</p></div>`;
      return;
    }
    PS.plans = pl.plans || [];
    if (!planOf(PS.planSel)) PS.planSel = 'free';
    PS.list = li && li._s === 200 ? li : { rows: [], users: [] };
    paintTarget(); paintCats(); paintList();
    if (PS.mode === 'member' && PS.email) loadMember(PS.email);
  }

  function planOpts(sel, withGuest) {
    return PS.plans.filter((p) => withGuest || p.id !== 'guest')
      .map((p) => `<option value="${esc(p.id)}" ${p.id === sel ? 'selected' : ''}>${esc(p.name)}${p.builtin ? '' : ''}</option>`).join('');
  }
  function paintTarget() {
    const v = PS.v, box = v.querySelector('#pmTarget'); if (!box) return;
    if (PS.mode === 'member') {
      const emails = new Map();
      ((PS.list && PS.list.rows) || []).forEach((r) => emails.set(r.email, r.email));
      ((PS.list && PS.list.users) || []).forEach((u) => { if (u.email && !emails.has(u.email)) emails.set(u.email, u.name ? `${u.name}（${u.email}）` : u.email); });
      const r = PS.rec;
      box.innerHTML = `<div class="pmbar"><input type="email" id="pmEmail" list="pmEmails" placeholder="輸入或選擇會員 email" autocomplete="off" value="${esc(PS.email)}" aria-label="會員 email">
          <datalist id="pmEmails">${[...emails.entries()].map(([e, l]) => `<option value="${esc(e)}">${esc(l)}</option>`).join('')}</datalist>
          <button type="button" class="pri" id="pmLoad">讀取</button></div>
        <div class="pmwho" id="pmWho">${r ? whoLine(r) : '輸入 email 後按「讀取」（或按 Enter）。對方還沒登入過也可以先設好，登入後就生效。'}</div>
        ${r ? `<div class="pmbar"><label style="font-size:13.5px;color:var(--ink-2)">方案範本 <select id="pmPlan">${planOpts(r.plan, false)}</select></label>
          <button type="button" id="pmClearOver" ${Object.keys(r.over || {}).length ? '' : 'disabled'}>清除個別微調</button>
          <input type="text" id="pmNewName" maxlength="20" placeholder="新範本名稱" aria-label="新範本名稱" style="width:9em">
          <button type="button" id="pmSaveAs">把這組存成新範本</button>
          <button type="button" class="danger" id="pmReset" ${r.set ? '' : 'disabled'}>移除此會員設定</button></div>` : ''}`;
      const go = () => { const e = (v.querySelector('#pmEmail').value || '').trim(); if (e) loadMember(e); };
      v.querySelector('#pmLoad').onclick = go;
      v.querySelector('#pmEmail').onkeydown = (e) => { if (e.key === 'Enter') go(); };
      const ps = v.querySelector('#pmPlan');
      if (ps) ps.onchange = () => saveMember({ plan: ps.value }, `已套用「${(planOf(ps.value) || {}).name || ps.value}」範本`);
      const co = v.querySelector('#pmClearOver');
      if (co) co.onclick = () => saveMember({ over: {} }, '已清除個別微調，完全照範本');
      const rs = v.querySelector('#pmReset');
      if (rs) rs.onclick = async () => {
        if (!PS.confirmDel) { PS.confirmDel = true; rs.textContent = '確定移除？（回到免費會員預設）'; return; }
        PS.confirmDel = false;
        const j = await PS.A.call('/v1/admin/perm/put', { email: PS.rec.email, reset: true });
        if (j && j._s === 200) { PS.rec = j; afterSave(j.email, '已移除此會員的設定，回到「免費會員」預設'); } else setStat('移除失敗：' + errText(j), 'bad');
      };
      const sa = v.querySelector('#pmSaveAs');
      if (sa) sa.onclick = () => saveAsPlan(v.querySelector('#pmNewName').value);
    } else {
      const p = planOf(PS.planSel);
      box.innerHTML = `<div class="pmbar"><label style="font-size:13.5px;color:var(--ink-2)">範本 <select id="pmPlanSel">${planOpts(PS.planSel, true)}</select></label>
          <input type="text" id="pmNewName" maxlength="20" placeholder="新範本名稱" aria-label="新範本名稱" style="width:9em">
          <button type="button" id="pmSaveAs">另存為新範本</button>
          <button type="button" class="danger" id="pmPlanDel" ${p && !p.builtin ? '' : 'disabled'} title="${p && p.builtin ? '內建範本不能刪' : '用這個範本的會員會退回免費會員'}">刪除範本</button></div>
        <div class="pmwho" id="pmWho">${p ? planLine(p) : ''}</div>`;
      v.querySelector('#pmPlanSel').onchange = (e) => { PS.planSel = e.target.value; PS.confirmDel = false; paintTarget(); paintCats(); setStat(''); };
      v.querySelector('#pmSaveAs').onclick = () => saveAsPlan(v.querySelector('#pmNewName').value);
      const del = v.querySelector('#pmPlanDel');
      del.onclick = async () => {
        if (!PS.confirmDel) { PS.confirmDel = true; del.textContent = '確定刪除？'; return; }
        PS.confirmDel = false;
        const j = await PS.A.call('/v1/admin/plans/put', { id: PS.planSel, del: true });
        if (j && j._s === 200) { PS.plans = j.plans; const nm = p.name; PS.planSel = 'free'; paintTarget(); paintCats(); setStat(`已刪除「${nm}」；原本用它的會員退回「免費會員」（個別微調保留）`, 'ok'); refreshList(); }
        else setStat('刪除失敗：' + errText(j), 'bad');
      };
    }
  }
  function whoLine(r) {
    const n = Object.keys(r.over || {}).length;
    const who = r.known ? `已登入過：<b>${esc(r.known.name || '')}</b>` : '<b>尚未登入過</b>（先設好，對方登入後就生效）';
    return `<b>${esc(r.email)}</b>・${who}・目前方案「<b>${esc(r.planName || r.plan)}</b>」・個別微調 <b>${n}</b> 項${r.set ? '' : '（還沒個別設定過＝照免費會員）'}`;
  }
  function planLine(p) {
    const n = Object.keys(p.feats || {}).length;
    const who = p.id === 'guest' ? '套用對象：所有沒登入的訪客' : p.id === 'free' ? '套用對象：登入後沒被指定方案的會員' : `套用對象：被指定這個方案的會員（目前 ${p.members || 0} 位）`;
    return `${who}・跟預設不同的項目 <b>${n}</b> 項`;
  }

  function paintCats() {
    const v = PS.v, box = v.querySelector('#pmCats'); if (!box || !FT()) return;
    const ready = PS.mode === 'plan' ? !!planOf(PS.planSel) : !!PS.rec;
    const cur = curVals(), base = baseVals();
    box.classList.toggle('off', !ready);
    box.innerHTML = FT().cats.map((c) => {
      const fs = FT().inCat(c.id); if (!fs.length) return '';
      const nOn = fs.filter((f) => f.kind === 'limit' ? cur[f.id] > 0 : cur[f.id] !== false).length;
      return `<div class="card pmcat" data-cat="${esc(c.id)}"><div class="pmcathd"><h3>${esc(c.name)}<small>${fs.length} 項・開 ${nOn}</small></h3>
          <button type="button" data-all="1" data-cat="${esc(c.id)}" ${ready ? '' : 'disabled'}>全開</button><button type="button" data-all="0" data-cat="${esc(c.id)}" ${ready ? '' : 'disabled'}>全關</button></div>`
        + fs.map((f) => {
          const val = cur[f.id], diff = PS.mode === 'member' ? (PS.rec && Object.prototype.hasOwnProperty.call(PS.rec.over || {}, f.id)) : val !== f.def;
          const ctl = f.kind === 'limit'
            ? `<select data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${ready ? '' : 'disabled'}>${Array.from({ length: f.max + 1 }, (_, i) => `<option value="${i}" ${i === val ? 'selected' : ''}>${i === 0 ? '不能用' : i + ' 頁'}</option>`).join('')}</select>`
            : `<label class="psw"><input type="checkbox" role="switch" data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${val !== false ? 'checked' : ''} ${ready ? '' : 'disabled'}><span></span></label>`;
          const tag = diff ? (PS.mode === 'member' ? `<span class="pmtag" title="跟範本不同（範本是${base[f.id] === false ? '關' : base[f.id] === true ? '開' : base[f.id]}）">微調</span><button type="button" class="pmrev" data-rev="${esc(f.id)}">還原</button>`
            : `<span class="pmtag" title="跟預設不同">改過</span>`) : '';
          return `<div class="pmrow" data-f="${esc(f.id)}">${ctl}<div class="pmtx"><b>${esc(f.name)}</b><small>${esc(f.desc)}</small></div><div class="pmside">${tag}</div></div>`;
        }).join('') + '</div>';
    }).join('');
    box.onchange = (e) => {
      const el = e.target.closest('[data-f]'); if (!el) return;
      const f = FT().byId(el.dataset.f); if (!f) return;
      const val = f.kind === 'limit' ? parseInt(el.value, 10) : !!el.checked;
      setVals({ [f.id]: val }, `「${f.name}」${f.kind === 'limit' ? '改成 ' + val : val ? '開啟' : '關閉'}`);
    };
    box.onclick = (e) => {
      const a = e.target.closest('button[data-all]');
      if (a) {
        const on = a.dataset.all === '1', c = FT().cats.find((x) => x.id === a.dataset.cat);
        const ch = {}; FT().inCat(a.dataset.cat).forEach((f) => { ch[f.id] = f.kind === 'limit' ? (on ? f.max : 0) : on; });
        setVals(ch, `「${c ? c.name : ''}」全部${on ? '開啟' : '關閉'}`);
        return;
      }
      const r = e.target.closest('button[data-rev]');
      if (r && PS.rec) {
        const over = Object.assign({}, PS.rec.over); delete over[r.dataset.rev];
        const f = FT().byId(r.dataset.rev);
        saveMember({ over }, `「${f ? f.name : r.dataset.rev}」還原成範本的設定`);
      }
    };
  }
  /* 把一批「新的實際值」換算成要存的東西：會員存「跟範本不同」的、範本存「跟預設不同」的 */
  function setVals(ch, label) {
    if (PS.mode === 'member') {
      if (!PS.rec) return;
      const base = baseVals(), over = Object.assign({}, PS.rec.over || {});
      Object.entries(ch).forEach(([k, v2]) => { if (base[k] === v2) delete over[k]; else over[k] = v2; });
      saveMember({ over }, label);
    } else {
      const p = planOf(PS.planSel); if (!p) return;
      const feats = Object.assign({}, p.feats || {});
      Object.entries(ch).forEach(([k, v2]) => { const f = FT().byId(k); if (f && f.def === v2) delete feats[k]; else feats[k] = v2; });
      savePlan(p.id, p.name, feats, label);
    }
  }
  async function loadMember(email) {
    const seq = ++PS.seq;
    setStat('讀取中…');
    const j = await PS.A.call('/v1/admin/perm/get', { email });
    if (seq !== PS.seq) return;
    if (!j || j._s !== 200) { setStat('讀不到：' + errText(j), 'bad'); return; }
    PS.email = j.email; PS.rec = j; PS.confirmDel = false;
    paintTarget(); paintCats(); setStat('');
  }
  async function saveMember(patch, label) {
    const r = PS.rec; if (!r) return;
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/perm/put', { email: r.email, plan: patch.plan || r.plan, over: patch.over || r.over || {} });
    if (j && j._s === 200) { PS.rec = Object.assign({}, j, { known: r.known }); afterSave(j.email, label + `・已儲存（台北 ${tpeTime()}）`); }
    else { setStat('儲存失敗：' + errText(j) + '（畫面已還原）', 'bad'); paintTarget(); paintCats(); }
  }
  function afterSave(email, msg) {
    paintTarget(); paintCats(); setStat(msg, 'ok'); refreshList();
    /* 改的是自己：自己的鎖頭馬上跟著換，不必重新整理 */
    const me = (PS.A.user() || {}).email;
    if (me && String(me).toLowerCase() === email && window.TwPerm) window.TwPerm.refresh();
  }
  async function savePlan(id, name, feats, label) {
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats });
    if (j && j._s === 200) {
      PS.plans = j.plans; paintTarget(); paintCats(); setStat(label + `・已儲存到「${name}」範本（台北 ${tpeTime()}）`, 'ok');
      if (window.TwPerm) window.TwPerm.refresh();     // 改到訪客／免費範本時，自己若吃這份也跟著換
    } else { setStat('儲存失敗：' + errText(j) + '（畫面已還原）', 'bad'); paintCats(); }
  }
  async function saveAsPlan(name) {
    name = String(name || '').trim();
    if (!name) { setStat('先在旁邊輸入新範本的名稱', 'bad'); return; }
    /* 目前畫面上這一組（範本模式＝這個範本；會員模式＝這個人的實際值）只留「跟預設不同」的項目 */
    const cur = curVals(), feats = {};
    FT().list.forEach((f) => { if (cur[f.id] !== f.def) feats[f.id] = cur[f.id]; });
    const id = 'p' + Date.now().toString(36).slice(-7);
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats });
    if (!j || j._s !== 200) { setStat('另存失敗：' + errText(j), 'bad'); return; }
    PS.plans = j.plans;
    if (PS.mode === 'plan') { PS.planSel = id; paintTarget(); paintCats(); setStat(`已另存為新範本「${name}」`, 'ok'); }
    else { await saveMember({ plan: id, over: {} }, `已存成新範本「${name}」並套用到這位會員`); }
  }
  async function refreshList() {
    const li = await PS.A.call('/v1/admin/perm/list', {});
    if (li && li._s === 200) { PS.list = li; paintList(); }
  }
  function paintList() {
    const box = PS.v && PS.v.querySelector('#pmListBody'); if (!box) return;
    const rows = (PS.list && PS.list.rows) || [];
    const pn = (id) => (planOf(id) || {}).name || id;
    box.innerHTML = rows.length ? `<table class="pmlist"><thead><tr><th>email</th><th>方案</th><th>微調</th><th>最後修改（台北）</th></tr></thead><tbody>${rows.map((r) =>
      `<tr data-email="${esc(r.email)}"><td>${esc(r.email)}</td><td>${esc(pn(r.plan))}</td><td>${r.n}</td><td>${dstr(r.updated)}</td></tr>`).join('')}</tbody></table>`
      : '<div class="empty">還沒有個別設定過任何會員。</div>';
    box.onclick = (e) => {
      const tr = e.target.closest('tr[data-email]'); if (!tr) return;
      if (PS.mode !== 'member') { PS.mode = 'member'; PS.v.querySelectorAll('#pmMode button').forEach((x) => x.classList.toggle('on', x.dataset.m === 'member')); }
      PS.email = tr.dataset.email; loadMember(tr.dataset.email);
      PS.v.querySelector('#pmHead').scrollIntoView({ block: 'start', behavior: 'smooth' });
    };
  }

  window.TwAdmin = { render };
})();
