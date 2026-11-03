/* 科技透明圈：公開版（官方薪資）——對所有人開放，只用官方合法資料。
   2026-11-03 Andy：「照建議做，先從官方薪資版預覽開始」。法遵依據 docs/tc/legal.md ③ 與 docs/marketing/diagnosis_1102/legal_tech_transparency.md：
   第一版只用證交所／櫃買中心公告的「非擔任主管職務之全時員工薪資」，GoodJob／Dcard／PTT 的數字不進這一頁（那些只在 tc.js 的管理者分頁）。

   資料兩層：
     1. data/tc_salary.json —— pipeline 從資料湖 salary_official 產出（官方開放資料，每年 6/30 後自動更新）；有就以它為準。
     2. tc/official_seed.json —— 人工整理的種子（媒體轉述官方公告，每筆標來源），pipeline 還沒跑出資料前先頂著，
        同時提供「全部科技公司名單」（代號、名稱、產業）——沒有官方數字的公司才查得到「尚未取得」。
   路由：#tc 排行｜#tc/co/<代號> 公司卡。不連個股頁（#stock/，法遵：科技帳號不導流到個股頁）。 */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const IND = { foundry: '晶圓代工', memory: '記憶體', osat: '封測', material: '半導體材料／PCB', equipment: '半導體設備', icdesign: 'IC 設計', odm: '電子代工 ODM', panel: '面板／光學', foreign: '外商', other: '其他科技' };
  const IND_ORDER = Object.keys(IND);
  const mob = () => window.matchMedia && window.matchMedia('(max-width:640px)').matches;

  /* 開口圈 LOGO（Andy 11-02 定稿原色：藍環 #1F6FEB＋橘點 #FF9F1C，僅去掉圓角底色，不改環與點的顏色；原稿 docs/brand/tc_logo_1102/c1_開口圈） */
  const LOGO = '<svg class="tcp-logo" viewBox="0 0 100 100" width="28" height="28" aria-hidden="true" focusable="false"><path d="M74.69 46.09 A25 25 0 1 1 53.91 25.31" fill="none" stroke="#1F6FEB" stroke-width="9" stroke-linecap="round"/><circle cx="67.68" cy="32.32" r="6.6" fill="#FF9F1C"/></svg>';

  /* 頁底固定文字：取自 docs/tc/legal.md ③，一字不改（改法遵文字要回去改那份文件） */
  const LEGAL = '<b>資料來源與免責聲明</b>' +
    '<p>本頁薪資數字取自：公開資訊觀測站「非擔任主管職務之全時員工薪資資訊」（金管會規定之上市櫃公司揭露，年度資料）、各公司永續報告書。網友分享平台（GoodJob、Dcard、PTT）的資訊僅作為參考連結，本站未轉載其內容，數字以原平台為準。</p>' +
    '<p>官方數字為公司整體平均數／中位數，含獎金與員工酬勞，<b>不代表任何單一職位或個人的實際薪資</b>。本站整理可能有誤或過時，請以原始公告為準。本頁不構成求職、勞動條件或投資建議。</p>' +
    '<p>若您認為內容有誤或涉及個人資料，請透過右下角客服聯絡，我們會儘快更正或移除。</p>' +
    '<p class="tcp-lic">資料來源：臺灣證券交易所、證券櫃檯買賣中心，政府資料開放授權條款第 1 版。</p>';

  const S = { loaded: false, rows: [], cos: [], year: null, ind: '', only: true, sort: { k: 'median', d: -1 }, all: false, mode: '' };

  async function jget(u) { try { const r = await fetch(u, { cache: 'no-cache' }); return r.ok ? await r.json() : null; } catch (e) { return null; } }
  /* 湖有官方資料（pipeline 產出）就蓋過種子：以代號合併，湖的列優先 */
  async function load() {
    if (S.loaded) return;
    const [seed, lake] = await Promise.all([jget('tc/official_seed.json'), jget('data/tc_salary.json')]);
    S.cos = (seed && seed.cos) || [];
    const by = new Map();
    ((seed && seed.rows) || []).forEach((r) => by.set(r.code, Object.assign({ src: 'seed' }, r)));
    ((lake && lake.rows) || []).forEach((r) => {
      if (r.avg_wan == null && r.median_wan == null) return;
      const old = by.get(r.code) || {};
      by.set(r.code, Object.assign({}, old, r, { year: lake.year, ind: old.ind, url: 'https://data.gov.tw/dataset/155869', note: null, src: 'official' }));
    });
    const info = new Map(S.cos.map((c) => [c.code, c]));
    S.rows = [...by.values()].map((r) => Object.assign({ ind: (info.get(r.code) || {}).ind || 'other', name: (info.get(r.code) || {}).name || r.name || r.code }, r, { ind: r.ind || (info.get(r.code) || {}).ind || 'other' }));
    S.year = Math.max(0, ...S.rows.map((r) => +r.year || 0)) || null;
    S.asof = (seed && seed.asof) || '';
    S.loaded = true;
  }

  const wan = (v) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 1 }));
  const yoy = (v) => (v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1) + '%');
  /* 台股慣例紅漲綠跌；這頁是瑞士極簡，年增用文字符號＋紅（增）／黑（減）以外不再引入綠色，避免和全站色義衝突 */
  const sorter = { avg: (r) => r.avg_wan, median: (r) => r.median_wan, yoy: (r) => r.yoy_pct, n: (r) => r.n, name: (r) => r.name };
  const visible = () => S.rows.filter((r) => !S.ind || r.ind === S.ind);

  function listHtml() {
    const rows = visible().slice();
    const f = sorter[S.sort.k] || sorter.median, d = S.sort.d;
    rows.sort((a, b) => { const x = f(a), y = f(b); if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1; return typeof x === 'string' ? d * -1 * x.localeCompare(y, 'zh-Hant') : d * (x - y); });
    const th = (k, t, cls) => '<th class="srt ' + (cls || '') + (S.sort.k === k ? ' on' : '') + '" data-sk="' + k + '" aria-sort="' + (S.sort.k === k ? (S.sort.d > 0 ? 'ascending' : 'descending') : 'none') + '"><button type="button">' + t + '<i>' + (S.sort.k === k ? (S.sort.d > 0 ? '▲' : '▼') : '') + '</i></button></th>';
    const cut = mob() && !S.all && rows.length > 10;
    const shown = cut ? rows.slice(0, 10) : rows;
    let h = '<div class="tcp-tw"><table class="tcp-tbl"><thead><tr>' + th('name', '公司', 'l') + '<th class="l tcp-hm">產業</th>' + th('median', '中位數(萬)') + th('avg', '平均(萬)') + th('yoy', '年增') + th('n', '員工數', 'tcp-hm') + '<th class="tcp-hm">年度・來源</th></tr></thead><tbody>';
    shown.forEach((r) => {
      h += '<tr class="tcp-row" data-code="' + esc(r.code) + '"><td class="l"><a class="tcp-go" href="#tc/co/' + esc(r.code) + '">' + esc(r.name) + '</a><small>' + esc(r.code) + '</small></td><td class="l tcp-hm">' + esc(IND[r.ind] || '') + '</td>' +
        '<td class="num strong">' + wan(r.median_wan) + '</td><td class="num">' + wan(r.avg_wan) + '</td><td class="num ' + (r.yoy_pct > 0 ? 'up' : '') + '">' + yoy(r.yoy_pct) + '</td><td class="num tcp-hm">' + (r.n == null ? '—' : r.n.toLocaleString('en-US')) + '</td>' +
        '<td class="tcp-hm">' + esc(r.year || '') + (r.url ? '・<a href="' + esc(r.url) + '" target="_blank" rel="noopener noreferrer">來源</a>' : '') + '</td></tr>';
    });
    h += '</tbody></table></div>';
    if (cut) h += '<button type="button" class="tcp-more" id="tcpMore">看全部 ' + rows.length + ' 家</button>';
    if (!rows.length) h = '<div class="empty isempty">這個產業目前沒有官方數字</div>';
    return h;
  }

  function missingHtml() {
    const have = new Set(S.rows.map((r) => r.code));
    const miss = S.cos.filter((c) => !have.has(c.code) && (!S.ind || c.ind === S.ind));
    if (!miss.length) return '';
    return '<details class="tcp-miss"><summary>尚未取得官方數字的 ' + miss.length + ' 家</summary><p>官方資料每年 6 月底公布，系統會在公布後自動補上；以下先列名單，不提供網友自述數字。</p><div class="tcp-chips">' + miss.map((c) => '<span>' + esc(c.name) + '</span>').join('') + '</div></details>';
  }

  function howHtml() {
    return '<span class="tcp-how"><button class="tcp-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button><div class="tcp-pop" hidden role="note">' +
      '<b>怎麼用</b><br>想知道某個產業的薪資落在哪：先挑產業，再點「中位數」排序——中位數是正中間那一位員工的年薪，不被少數高薪拉高；平均數比中位數高很多，代表分紅集中在少數人。' +
      '「年增」看這家近一年有沒有在加薪。點公司名看它在同產業的位置。<br>' +
      '口徑是「非擔任主管的全時員工」，含獎金與員工酬勞，不能拿來當某個職位的起薪；不同公司的分紅制度不同，比較時請看年度與來源。</div></span>';
  }

  function indBar() {
    const have = IND_ORDER.filter((id) => S.rows.some((r) => r.ind === id));
    return '<div class="tcp-inds" role="tablist" aria-label="產業"><button type="button" role="tab" data-ind="" class="' + (!S.ind ? 'on' : '') + '">全部<small>' + S.rows.length + '</small></button>' +
      have.map((id) => '<button type="button" role="tab" data-ind="' + id + '" class="' + (S.ind === id ? 'on' : '') + '">' + IND[id] + '<small>' + S.rows.filter((r) => r.ind === id).length + '</small></button>').join('') + '</div>';
  }

  function adminBar() {
    const T = window.TwTc;
    if (!(T && T.isAdm && T.isAdm())) return '';
    return '<div class="tcp-adm">管理者專用：<a href="#tc/foundry">網友樣本分頁（GoodJob／Dcard）</a>　一般訪客看不到這個連結</div>';
  }

  function paintList(root) {
    const n = visible().length;
    let h = adminBar() + '<div class="tcp-hd"><div class="tcp-ttl">' + LOGO + '<h2>官方薪資</h2>' + howHtml() + '</div>' +
      '<div class="tcp-sub">非主管全時員工' + (S.year ? '・' + (S.year - 1911) + ' 年度' : '') + '</div></div>' +
      indBar() + '<div class="tcp-cnt" id="tcpCount">顯示 <b>' + n + '</b> 家（單位：萬元／年）</div>' + listHtml() + missingHtml() + '<div class="tcp-legal" id="tcpLegal">' + LEGAL + '</div>';
    root.innerHTML = '<div class="tcp">' + h + '</div>';
    const b = $('.tcp-q', root), p = $('.tcp-pop', root);
    b.onclick = (e) => { e.stopPropagation(); p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); };
    if (!window.__tcpDoc) { window.__tcpDoc = true; document.addEventListener('click', (e) => { $$('.tcp-pop').forEach((x) => { if (!x.hidden && !x.contains(e.target)) { x.hidden = true; const q = x.previousElementSibling; if (q) q.setAttribute('aria-expanded', 'false'); } }); }); }
    $$('.tcp-inds button', root).forEach((x) => { x.onclick = () => { S.ind = x.dataset.ind; S.all = false; paintList(root); }; });
    $$('th.srt button', root).forEach((x) => { x.onclick = () => { const k = x.parentNode.dataset.sk; S.sort = S.sort.k === k ? { k, d: -S.sort.d } : { k, d: k === 'name' ? 1 : -1 }; paintList(root); }; });
    const mo = $('#tcpMore', root); if (mo) mo.onclick = () => { S.all = true; paintList(root); };
  }

  function paintCard(root, code) {
    const r = S.rows.find((x) => x.code === code), info = S.cos.find((x) => x.code === code);
    const back = '<div class="tcp-crumb"><a href="#tc" id="tcpBack">← 回官方薪資排行</a></div>';
    if (!r && !info) { root.innerHTML = '<div class="tcp">' + adminBar() + back + '<div class="empty isempty">找不到這家公司</div><div class="tcp-legal">' + LEGAL + '</div></div>'; return; }
    const name = (r || info).name, ind = (r || info).ind;
    let h = adminBar() + back + '<div class="tcp-hd"><div class="tcp-ttl">' + LOGO + '<h2>' + esc(name) + '</h2><span class="tcp-code">' + esc(code) + '</span></div><div class="tcp-sub">' + esc(IND[ind] || '') + '</div></div>';
    if (!r) {
      h += '<div class="tcp-nodata">這家公司的官方數字尚未取得。官方資料每年 6 月底公布，公布後系統會自動補上。</div>';
    } else {
      /* 同產業不到 3 家有官方數字就沒有比較的意義（只有自己一條），改拿全部有數字的公司比；兩種都在標題寫清楚比的是誰 */
      let peers = S.rows.filter((x) => x.ind === ind && x.median_wan != null), scope = '同產業（' + (IND[ind] || '') + '）';
      if (peers.length < 3) { peers = S.rows.filter((x) => x.median_wan != null); scope = '全部公司'; }
      peers.sort((a, b) => b.median_wan - a.median_wan);
      const rk = peers.findIndex((x) => x.code === code) + 1, mx = Math.max(...peers.map((x) => x.median_wan), 1);
      h += '<div class="tcp-kpis"><div><span>中位數</span><b>' + wan(r.median_wan) + '<i>萬</i></b></div><div><span>平均數</span><b>' + wan(r.avg_wan) + '<i>萬</i></b></div><div><span>年增（中位數）</span><b class="' + (r.yoy_pct > 0 ? 'up' : '') + '">' + yoy(r.yoy_pct) + '</b></div><div><span>員工數</span><b>' + (r.n == null ? '—' : r.n.toLocaleString('en-US')) + '</b></div></div>';
      if (rk) {
        h += '<div class="tcp-peer"><div class="tcp-peerh">' + esc(scope) + '中有官方中位數的 ' + peers.length + ' 家裡，這家排第 <b>' + rk + '</b>（中位數，萬元／年）</div>' +
          peers.map((x) => '<div class="tcp-bar' + (x.code === code ? ' me' : '') + '"><span class="nm">' + esc(x.name) + '</span><span class="bar"><i style="width:' + Math.max(2, x.median_wan / mx * 100).toFixed(1) + '%"></i></span><span class="v">' + wan(x.median_wan) + '</span></div>').join('') + '</div>';
      }
      h += '<div class="tcp-src">資料來源：公開資訊觀測站／證交所、櫃買中心公告，' + esc(r.year || '') + ' 年度（民國 ' + ((+r.year || 0) - 1911) + ' 年）' + (S.asof ? '，整理日 ' + esc(S.asof) : '') + '。' + (r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener noreferrer">原始來源</a>' : '') + (r.note ? '<br>' + esc(r.note) : '') + '</div>';
    }
    root.innerHTML = '<div class="tcp">' + h + '<div class="tcp-legal">' + LEGAL + '</div></div>';
  }

  async function show(rest) {
    const root = document.getElementById('v-tc'); if (!root) return;
    root.innerHTML = '<div class="tcp"><div class="empty">載入中…</div></div>';
    await load();
    if (rest[0] === 'co' && rest[1]) paintCard(root, decodeURIComponent(rest[1])); else paintList(root);
    window.scrollTo(0, 0);
  }

  window.TcPub = { show, state: () => S };
})();
