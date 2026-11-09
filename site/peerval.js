/* ============================================================================
   族群同業估值位階（site/peerval.js）—— P-1107-04，Andy 2026-11-09 點頭（「02 05 03 04 06」）
   ----------------------------------------------------------------------------
   產品第二問「那個族群現在貴不貴」：同一族群裡，這一檔的估值落在同業的哪個位置。資料 data/peer_val.json
   （pipeline/compute/peerval.py；口徑寫在那支的檔頭，這裡只畫、不重算）。兩個地方：
     ① 族群頁（#industry/group/<gid>）：族群卡內容區（.nbbody，族群總覽或剖析圖下面）最後一張位階表 #pvCard
        欄位：個股（代號＋名稱）｜本益比｜淨值比｜殖利率｜營收 YoY｜自身歷史本益比；每格右邊一條分位條。
        點欄名排序（再點反向），預設依代號 —— 提案法遵段：不預設依估值排序，避免看起來像推薦清單。
     ② 個股頁總覽：三欄卡片下面一張小卡 #pvStock「在○○族群同業中：本益比位於第 N 百分位」＋淨值比、殖利率、營收 YoY 三格。
        一檔屬多個族群時上方一排族群鈕可切換。
   規矩：
     · 只陳述位置（第 N 百分位、族群中位數），不寫「便宜可買」「高估」。分位條的兩端標「低」「高」，不用紅綠（紅綠是漲跌），
       估值三欄用青色、營收 YoY 用中性灰紫（它不是估值）。
     · 殖利率的分位條方向跟本益比一致（0＝同業估值最低端）：資料端存的就是「殖利率由高到低」的位置，條寬＝那個數。
     · 虧損寫「不適用（虧損）」、沒資料寫「—」、有效樣本 < 5 檔寫「同業樣本不足」，都不畫條。
   功能鍵：group.peerval（位階表）、stock.peerval（個股小卡），features.js；被鎖由 perm.js／quota.js 蓋在 #pvCard／#pvStock 上。
   不改 industry.js／mobile3.js：MutationObserver 在它們畫完之後補上（同 riskflag.js 的做法）；已經畫好、內容沒變就不重畫
   （不然 quota.js 插進來的鎖頭會被自己拔掉、又觸發一次 —— 迴圈）。
   ============================================================================ */
(function () {
  'use strict';
  let D = null, loading = null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (v, nd) => (v == null ? '—' : (window.App && App.fmt && App.fmt.n ? App.fmt.n(v, nd) : Number(v).toFixed(nd)));
  /* 欄位：k＝資料欄、p＝百分位欄、u＝單位、nd＝小數位、hd＝表頭、cls＝條的顏色組 */
  const MET = [
    { k: 'pe', p: 'p_pe', hd: '本益比', u: '倍', nd: 1, cls: 'val' },
    { k: 'pb', p: 'p_pb', hd: '淨值比', u: '倍', nd: 2, cls: 'val' },
    { k: 'dy', p: 'p_dy', hd: '殖利率', u: '%', nd: 2, cls: 'val' },
    { k: 'yoy', p: 'p_yoy', hd: '營收 YoY', u: '%', nd: 1, cls: 'neu' },
  ];
  const sort = { k: 'code', dir: 1 };          // 位階表目前的排序（切族群、重畫都沿用）
  let stockPick = {};                          // 個股小卡：每檔選了哪個族群 { code: gid }

  function load() {
    if (D) return Promise.resolve(D);
    if (!loading) {
      const waitApp = new Promise((res) => { let n = 0; const t = () => (window.App && window.App.load) || ++n > 20 ? res(window.App) : setTimeout(t, 300); t(); });
      loading = waitApp.then((A) => (A && A.load ? A.load('peer_val', { fallback: null, low: true })
        : fetch('data/peer_val.json').then((r) => (r.ok ? r.json() : null))))
        .then((d) => { D = d && d.groups ? d : { groups: {}, stocks: {}, cols: [] }; return D; }, () => { D = { groups: {}, stocks: {}, cols: [] }; return D; });
    }
    return loading;
  }
  const minN = () => (D && D.min_n) || 5;
  function rowsOf(g) {
    const cols = D.cols || [];
    return (g.rows || []).map((r) => { const o = {}; cols.forEach((c, i) => { o[c] = r[i]; }); return o; });
  }

  /* 一格：數字＋分位條。p 為 null 時寫原因，不畫條 */
  function cellHTML(m, r, g) {
    const v = r[m.k], p = r[m.p];
    let val;
    if (m.k === 'pe' && r.st === 'loss') return '<span class="pvna" data-why="loss">不適用（虧損）</span>';
    if (v == null) return '<span class="pvna" data-why="na">—</span>';
    val = `<span class="pvv">${fmt(v, m.nd)}${m.u === '%' ? '%' : ''}</span>`;
    if (m.k === 'pe' && r.st === 'dist') return `${val}<span class="pvthin" data-why="dist" title="本益比低於 3 倍或高於 200 倍視為失真（多半是 EPS 很接近 0），照印數字但不排進同業">失真不排名</span>`;
    if (p == null) return `${val}<span class="pvthin" title="這一欄同業有效樣本 ${g.nv[m.k]} 檔，少於 ${minN()} 檔不算百分位">樣本不足</span>`;
    return `${val}<span class="pvbar ${m.cls}" data-p="${p}" title="${esc(m.hd)}：同業第 ${p} 百分位${m.k === 'dy' ? '（殖利率越高越靠左）' : ''}"><i style="width:${p}%"></i></span><span class="pvp">${p}</span>`;
  }
  function ownHTML(r) {
    if (r.own == null) return `<span class="pvna" data-why="${r.st === 'loss' ? 'loss' : 'na'}" title="${r.st === 'loss' ? '虧損沒有本益比' : `自己的本益比歷史只有 ${r.own_n || 0} 季，少於 12 季（3 年）不算`}">—</span>`;
    return `<span class="pvbar own" data-p="${r.own}" title="目前本益比在自己近 ${Math.min(20, r.own_n)} 季本益比的第 ${r.own} 百分位"><i style="width:${r.own}%"></i></span><span class="pvp">${r.own}</span>`;
  }
  const HOW = () => (window.App && App.howHTML ? App.howHTML('同一個族群裡，每一檔的估值在同業的位置。', [
    '同業百分位＝同族群裡比它低的檔數占比（最低的那檔是 0）；殖利率反過來排（殖利率越高越靠左），四條同一個方向',
    '本益比＝收盤 ÷ 近四季 EPS；虧損寫「不適用」，低於 3 倍或高於 200 倍寫「失真不排名」，都不排進同業',
    '殖利率＝近四次現金股利 ÷ 收盤；營收 YoY＝最新月營收年增',
    '同業有效樣本少於 5 檔不算百分位（寫「樣本不足」）',
    '自身歷史：目前本益比在自己近 3～5 年各季本益比的位置（少於 12 季不算）',
    '只陳述位置，不代表便宜或貴、也不是買賣建議',
  ]) : '');

  /* ---------------------------------------------------------------- ① 族群頁位階表 */
  function sortRows(rows) {
    const k = sort.k, dir = sort.dir;
    const key = (r) => (k === 'code' ? r.code : k === 'own' ? r.own : r[k]);
    return rows.slice().sort((a, b) => {
      const x = key(a), y = key(b);
      if (k === 'code') return String(x).localeCompare(String(y)) * dir;
      if (x == null && y == null) return String(a.code).localeCompare(String(b.code));
      if (x == null) return 1;                 // 沒值（虧損、缺資料）永遠排最後
      if (y == null) return -1;
      return (x - y) * dir || String(a.code).localeCompare(String(b.code));
    });
  }
  function th(k, label, sub) {
    const on = sort.k === k;
    const aria = on ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none';
    return `<th class="pvth${on ? ' on' : ''}" data-sk="${k}" aria-sort="${aria}" tabindex="0" role="columnheader">${label}${sub ? `<small>${sub}</small>` : ''}<b class="pvsi" aria-hidden="true">${on ? (sort.dir > 0 ? '▲' : '▼') : '↕'}</b></th>`;
  }
  function tableHTML(gid, g) {
    const rows = sortRows(rowsOf(g));
    const thin = g.n < minN();
    const body = rows.map((r) => `<tr data-code="${esc(r.code)}"><td class="pvnm"><a class="pvlk" href="#stock/${encodeURIComponent(r.code)}"><b>${esc(r.name || r.code)}</b><small class="num">${esc(r.code)}</small></a></td>`
      + MET.map((m) => `<td class="pvc" data-k="${m.k}">${cellHTML(m, r, g)}</td>`).join('')
      + `<td class="pvc" data-k="own">${ownHTML(r)}</td></tr>`).join('');
    const med = `<tr class="pvmed"><td class="pvnm">族群中位數</td>${MET.map((m) => `<td class="pvc" data-k="${m.k}">${g.med && g.med[m.k] != null ? `<span class="pvv">${fmt(g.med[m.k], m.nd)}${m.u === '%' ? '%' : ''}</span>` : `<span class="pvna">${g.nv && g.nv[m.k] < minN() ? '樣本不足' : '—'}</span>`}</td>`).join('')}<td class="pvc"></td></tr>`;
    return `<div class="pvhead row spread"><h5>同業估值位階<button class="howbtn pop" data-how="pv" data-ttl="同業估值位階" type="button" aria-label="同業估值位階怎麼看">?</button></h5>`
      + `<small class="muted pvmeta"><span class="pvlegend" aria-hidden="true">分位條：同業低<i></i>高</span>${esc(D.asof || '')}・${g.n} 檔${g.loss ? `・${g.loss} 檔虧損` : ''}${thin ? '・<b class="pvthinall">同業樣本不足</b>' : ''}</small></div>`
      + `<div class="howtxt" id="how-pv" hidden>${HOW()}</div>`
      + `<div class="pvscroll"><table class="pvtbl" data-gid="${esc(gid)}"><thead><tr>${th('code', '個股')}${MET.map((m) => th(m.k, m.hd, m.u === '倍' ? '倍' : '')).join('')}${th('own', '自身歷史', '本益比')}</tr>`
      + `</thead>`
      + `<tbody>${body}</tbody><tfoot>${med}</tfoot></table></div>`
      + `<button class="pvmore btn small" type="button" hidden></button>`;
  }
  function wireTable(card, gid, g) {
    card.querySelectorAll('th[data-sk]').forEach((h) => {
      const go = () => {
        const k = h.dataset.sk;
        if (sort.k === k) sort.dir = -sort.dir; else { sort.k = k; sort.dir = 1; }
        paintGroup(true);
      };
      h.onclick = go;
      h.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } };
    });
    /* 手機：前 10 檔＋「看全部 N 檔」（手機準則 1：一頁看到大部分資訊）；桌機框內捲 */
    const more = card.querySelector('.pvmore');
    const trs = card.querySelectorAll('tbody tr');
    const mob = document.documentElement.classList.contains('m4') || matchMedia('(max-width:640px)').matches;
    if (mob && trs.length > 10 && !card.dataset.all) {
      trs.forEach((tr, i) => { if (i >= 10) tr.hidden = true; });
      more.hidden = false; more.textContent = `看全部 ${trs.length} 檔`;
      more.onclick = () => { card.dataset.all = '1'; trs.forEach((tr) => { tr.hidden = false; }); more.hidden = true; };
    }
  }
  function paintGroup(force) {
    const m = /^#industry\/group\/([^/?]+)/.exec(location.hash || '');
    const old = document.getElementById('pvCard');
    /* 放在族群卡的 .nbbody 最後面（#gpSec／#dgSec 之後）：有剖析圖的族群（例如晶圓代工、面板）族群頁顯示的是剖析圖，
       #gpSec 是藏著的 —— 放進 #gpSec 的話那些族群根本看不到這張表（驗收段落 11-09 抓到）。*/
    const gs = document.getElementById('gpSec');
    const host = gs && gs.closest('.nbbody');
    if (!m || !host || !D) { if (old) old.remove(); return; }
    const gid = decodeURIComponent(m[1]);
    const g = D.groups && D.groups[gid];
    if (!g || g.kind !== 'grp' || !(g.rows || []).length) { if (old) old.remove(); return; }
    const key = `${gid}|${sort.k}|${sort.dir}|${D.asof}`;
    if (!force && old && old.dataset.key === key && host.contains(old) && host.lastElementChild === old) return;
    const all = old && old.dataset.gid === gid ? old.dataset.all : '';
    const card = old && host.contains(old) ? old : document.createElement('div');
    card.id = 'pvCard'; card.className = 'pvcard'; card.dataset.key = key; card.dataset.gid = gid;
    if (all) card.dataset.all = all; else delete card.dataset.all;
    card.querySelectorAll(':scope > :not(.qcov)').forEach((n) => n.remove());
    card.insertAdjacentHTML('afterbegin', tableHTML(gid, g));
    if (card.parentNode !== host || host.lastElementChild !== card) host.appendChild(card);
    wireTable(card, gid, g);
  }

  /* ---------------------------------------------------------------- ② 個股頁小卡 */
  function groupsOf(code) {
    const ids = ((D && D.stocks && D.stocks[code]) || []).filter((id) => D.groups[id]);
    /* 預設選哪個族群：本益比能算百分位的優先，其次同業多的；不能只照代號字母序（晶圓代工會排在矽光子代工後面也說不定）*/
    const score = (id) => { const g = D.groups[id]; return (g.nv && g.nv.pe >= minN() ? 1e4 : 0) + (g.kind === 'grp' ? 1e3 : 0) + (g.n || 0); };
    return ids.slice().sort((a, b) => score(b) - score(a));
  }
  function stockHTML(code, gid, ids) {
    const g = D.groups[gid];
    const r = rowsOf(g).find((x) => x.code === code);
    if (!r) return '';
    const pe = r.st === 'loss' ? '本益比不適用（虧損）'
      : r.pe == null ? '本益比無資料'
        : r.st === 'dist' ? `本益比 ${fmt(r.pe, 1)} 倍・失真不排名（低於 3 倍或高於 200 倍）`
        : r.p_pe == null ? `本益比 ${fmt(r.pe, 1)} 倍・同業樣本不足（有效 ${g.nv.pe} 檔）`
          : `本益比位於第 <b class="pvN">${r.p_pe}</b> 百分位`;
    const chips = ids.length > 1 ? `<span class="pvchips" role="group" aria-label="切換比較的族群">${ids.slice(0, 4).map((id) => `<button type="button" class="pvchip${id === gid ? ' on' : ''}" data-g="${esc(id)}" aria-pressed="${id === gid}">${esc(D.groups[id].name)}</button>`).join('')}</span>` : '';
    const link = g.kind === 'grp' ? `<a class="pvgo" href="#industry/group/${encodeURIComponent(gid)}">看族群位階表 ›</a>` : '';
    const mini = (lab, inner) => `<div class="pvmini"><span class="pvml">${lab}</span>${inner}</div>`;
    return `<div class="pvshead"><h4>同業估值位階<button class="howbtn pop" data-how="pvs" data-ttl="同業估值位階" type="button" aria-label="同業估值位階怎麼看">?</button></h4>${chips}${link}</div>`
      + `<div class="howtxt" id="how-pvs" hidden>${HOW()}</div>`
      + `<p class="pvsline" data-p="${r.p_pe == null ? '' : r.p_pe}">在「<b>${esc(g.name)}</b>」${g.kind === 'ind' ? '產業' : '族群'}同業中（${g.n} 檔）：${pe}</p>`
      /* 自己的歷史本益比位置不放小卡：正上方基本面卡的「本益比」條已經寫了（每日口徑），同一頁兩個數字會打架 */
      + `<div class="pvminis">${MET.map((m) => mini(m.hd, `<span class="pvc" data-k="${m.k}">${cellHTML(m, r, g)}</span>`)).join('')}</div>`;
  }
  function paintStock() {
    const m = /^#stock\/([^/?]+)/.exec(location.hash || '');
    const old = document.getElementById('pvStock');
    if (!m || !D) { if (old) old.remove(); return; }
    const code = decodeURIComponent(m[1]).toUpperCase();
    /* 桌機：總覽分頁的 #skOv（三欄卡片下面）；手機：#mbBody 的總覽分頁 */
    let host = document.getElementById('skOv');
    if (!host || !host.getClientRects().length) {
      const mb = document.getElementById('mbBody');
      host = mb && mb.dataset.tab === 'ov' && mb.getClientRects().length ? mb : (host && host.isConnected ? host : null);
    }
    /* 換股時舊的總覽還在畫面上：#skOv 裡的基本面卡不是這一檔就先不畫（MutationObserver 會再叫）*/
    const ids = groupsOf(code);
    if (!host || !ids.length) { if (old) old.remove(); return; }
    const gid = ids.includes(stockPick[code]) ? stockPick[code] : ids[0];
    const key = `${code}|${gid}|${D.asof}`;
    if (old && old.dataset.key === key && host.contains(old) && host.lastElementChild === old) return;
    const html = stockHTML(code, gid, ids);
    if (!html) { if (old) old.remove(); return; }
    const card = old && host.contains(old) ? old : document.createElement('div');
    card.id = 'pvStock'; card.className = 'card pvstock'; card.dataset.key = key; card.dataset.code = code; card.dataset.gid = gid;
    card.querySelectorAll(':scope > :not(.qcov)').forEach((n) => n.remove());
    card.insertAdjacentHTML('afterbegin', html);
    if (card.parentNode !== host || host.lastElementChild !== card) host.appendChild(card);
    card.querySelectorAll('.pvchip').forEach((b) => { b.onclick = () => { stockPick[code] = b.dataset.g; paintStock(); }; });
  }

  function paint() {
    if (!D) return;
    paintGroup(false);
    paintStock();
  }
  let qd = 0;
  function queue() { if (qd) return; qd = setTimeout(() => { qd = 0; try { paint(); } catch (e) { window.__pvErr = String(e && e.stack || e).slice(0, 300); } }, 50); }
  const RELEVANT = /^#(stock\/|industry\/group\/)/;
  function boot() {
    window.addEventListener('hashchange', queue);
    window.addEventListener('tw:perm', queue);
    new MutationObserver(() => { if (RELEVANT.test(location.hash || '')) { if (D) queue(); else load().then(queue); } })
      .observe(document.body, { childList: true, subtree: true });
    if (RELEVANT.test(location.hash || '')) load().then(queue);
  }
  window.TwPeerVal = { load, paint: queue, _d: () => D, _sort: () => Object.assign({}, sort), _reset: () => { D = null; loading = null; } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
