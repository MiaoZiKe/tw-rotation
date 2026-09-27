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
    if (!(location.hash || '').startsWith('#admin')) return;
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

  function render(v, A) {
    css();
    S.v = v; S.A = A;
    const u = A.user() || {};
    v.innerHTML = `<div class="card" style="margin-top:16px"><div class="admtop"><h2>管理頁</h2><small style="color:var(--ink-2)">${esc(u.email || '')}</small><span class="sp"></span>
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
  window.TwAdmin = { render };
})();
