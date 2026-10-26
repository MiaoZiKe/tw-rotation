/* ============================================================================
   科技透明圈（#tc → #tc/<產業id> → #tc/<產業id>/<公司>）—— 2026-10-25 建
   這一頁回答的問題：「科技業各產業、各公司、各單位的職位，實際工時／底薪／分紅／年薪／加班長怎樣？」
   怎麼用：先挑產業，用上面五組篩選縮小（篩選對公司卡與職位表同時生效），點公司卡看單位→職位表。
   資料：site/tc/json/<產業id>.json（格式見 docs/tc/schema.md，由他人產出、前端只讀）。檔案還不存在的產業照樣有分頁，內容顯示「尚無資料」。
   數字全是區間，篩選一律拿區間中點比；工時、加班是單一值／分類。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const INDS = [['foundry', '晶圓代工'], ['memory', '記憶體'], ['osat', '封測'], ['material', '半導體材料'], ['equipment', '半導體設備'], ['icdesign', 'IC 設計'], ['odm', '電子代工 ODM'], ['panel', '面板／光學'], ['foreign', '外商'], ['other', '其他科技']];
  /* ★ 2026-10-25（Andy：「這內容就算上線了也只有我可以看，其他 Plus Pro 都先隱藏」）：只有管理者（站主＋站主加的人）看得到。
     判定沿用 livegate.js 同一條：/v1/me 的 admin／owner 旗標（TwAccount.user()，還沒載入退回登入快取）。
     非管理者：html 不掛 .tc-adm → m4/20261025-tc.css 把側欄與手機導覽的入口藏掉，直接打 #tc 導回總覽。
     本機驗收用 window.TW_TC_OVERRIDE（只在 localhost／127.0.0.1 生效）。 */
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;   // 預覽版全開（DECISIONS #343），正式站沒有這個旗標
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_TC_OVERRIDE === true || window.TW_TC_OVERRIDE === false)) return window.TW_TC_OVERRIDE;
      const A = window.TwAccount; let u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  /* 10-25 修（Andy：預覽版登入後「點擊後沒東西」）：開頁時 /v1/me 還沒回來，isAdm() 一定是 false，
     以前就當場導回總覽、內容也不畫。現在等身分確定（第一次 tw:account 或 6 秒逾時）才判定要不要導走；
     確定是管理者而且停在 #tc，就重跑一次路由把內容畫出來。 */
  let known = false;
  function gate() {
    const on = isAdm();
    document.documentElement.classList.toggle('tc-adm', on);
    if (!on && known && /^#tc(\/|$)/.test(location.hash || '')) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', () => {
    known = true;
    if (gate() && /^#tc(\/|$)/.test(location.hash || '')) window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
  setTimeout(() => { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  const FOOT = '資料整理自 GoodJob、Dcard、PTT 等公開分享，僅供參考';

  /* 篩選：k＝角色欄位、opts＝[顯示字, 判斷函式]；第一個永遠是「全部」 */
  const mid = (a) => (typeof a === 'number' ? a : Array.isArray(a) && a.length ? (a[0] + a[a.length - 1]) / 2 : null);
  /* 真資料的工時可能是區間或空、加班是自由文字（例「偶爾～經常（依部門）」）：缺值一律不通過數值篩選；加班依字面歸類，同時含兩類的兩邊都算 */
  const has = (v) => v != null;
  const otIs = (r, w) => { const t = String(r.overtime || ''); return w === '幾乎不' ? /幾乎不|很少|不加班/.test(t) : t.includes(w); };
  const FILTERS = [
    { k: 'hours', t: '工時', opts: [['全部'], ['≤45', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) <= 45], ['46–50', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 45 && mid(r.weekly_hours) <= 50], ['51–55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 50 && mid(r.weekly_hours) <= 55], ['>55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 55]], tip: '每週工時（小時）' },
    { k: 'base', t: '底薪', opts: [['全部'], ['≥50K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 50], ['≥60K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 60], ['≥70K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 70], ['≥80K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 80]], tip: '月底薪區間的中點' },
    { k: 'bonus', t: '分紅月數', opts: [['全部'], ['≥4', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 4], ['≥8', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 8], ['≥12', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 12]], tip: '年終＋分紅合計月數區間的中點' },
    { k: 'annual', t: '年薪', opts: [['全部'], ['≥100萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 100], ['≥150萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 150], ['≥200萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 200], ['≥300萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 300]], tip: '年薪總額（萬）區間的中點' },
    { k: 'ot', t: '加班', opts: [['全部'], ['幾乎不', (r) => otIs(r, '幾乎不')], ['偶爾', (r) => otIs(r, '偶爾')], ['經常', (r) => otIs(r, '經常')]], tip: '加班狀況' },
  ];
  const S = { ind: '', co: '', f: {}, sort: { k: '', d: -1 }, fopen: false, data: {}, loaded: false, chm: 'share', chv: 'ring', payI: null, rk: { m: 'ann', ind: 'all', all: false }, agg: null };

  /* 分紅發放欄只放「幾月」：從公司層 bonus_timing 抓出所有「N 月」，抓不到顯示「—」（完整說明留在公司頁頂端） */
  /* 展開「2、5、8、11 月」「2／5／8 月」這種列表＋單獨的「7 月」，去重後依數字排序輸出「2月、5月、…」；(?<!\d) 避免把 114 年的「14」當月份 */
  const btMonths = (t) => { const set = new Set(); String(t || '').replace(/(?<!\d)(\d{1,2}(?:\s*[、／\/,，]\s*\d{1,2})*)\s*月/g, (_, g) => { g.split(/[、／\/,，]/).forEach((x) => { const n = +x.trim(); if (n >= 1 && n <= 12) set.add(n); }); return _; }); return set.size ? Array.from(set).sort((x, y) => x - y).map((n) => n + '月').join('、') : '—'; };
  /* 沒有任何數字的職位（底薪、分紅月數、年薪總月數、年薪、週工時全空）→ 反灰並排在同單位有數據的列後面 */
  /* 分紅發放欄單行精簡：「2月、5月、7月」→「2/5/7 月」（不折行）；完整說明放 tooltip（title） */
  const btShort = (t) => (/^\d{1,2}月(、\d{1,2}月)*$/.test(t) ? t.replace(/月/g, '').replace(/、/g, '/') + ' 月' : t);
  const btTitle = (r, bt) => { const full = r.bonus_timing_month || bt; return full ? ' title="' + esc(String(full).slice(0, 300)) + '"' : ''; };
  const hasNum = (v) => fl(v).length > 0;
  const roleHasData = (r) => hasNum(r.base_month_k) || hasNum(r.bonus_months) || hasNum(r.annual_months) || hasNum(r.annual_total_wan) || hasNum(r.weekly_hours);
  /* 分紅結構：公司層 bonus_structure（每種獎金一筆）。摘要與頂端區塊都從它組；沒有就退回 bonus_timing */
  const bsum = (c) => {
    const bs = Array.isArray(c.bonus_structure) ? c.bonus_structure : [];
    const parts = bs.map((x) => {
      const r = String(x.rule || ''), pk = r.match(/(\d+)\s*包/), mm = r.match(/\d{1,2}(?:[／\/、]\d{1,2})+\s*月/), nx = r.match(/隔年\s*(\d{1,2})\s*月/);
      if (pk && mm) return pk[1] + ' 包（' + mm[0].replace(/\s*月/, '').replace(/[／、]/g, '/') + (nx ? '＋隔年' + nx[1] + '月' : '') + '）';
      if (x.months != null) return String(x.type || '').replace(/獎金$/, '') + x.months + '個月';
      return '';
    }).filter(Boolean);
    return parts.length ? parts.join('＋') : (c.bonus_timing ? clip(c.bonus_timing, 14) : '—');
  };
  /* ---- 一眼看懂區的零件（2026-10-26）：長文改短標籤，完整文字收進「?」 ---- */
  const qpop = (html) => '<span class="tc-how tc-qp"><button class="howbtn tc-q" type="button" aria-label="看完整說明" aria-expanded="false">?</button><div class="tc-pop" hidden>' + html + '</div></span>';
  const monthsIn = (t) => { const set = new Set(); String(t || '').replace(/(?<!\d)(\d{1,2}(?:\s*[、／\/,，]\s*\d{1,2})*)\s*月/g, (_, g) => { g.split(/[、／\/,，]/).forEach((x) => { const n = +x.trim(); if (n >= 1 && n <= 12) set.add(n); }); return _; }); return Array.from(set).sort((x, y) => x - y); };
  const catOf = (ty) => (/年終/.test(ty) ? '年終' : /三節|端午|中秋|春節|節/.test(ty) ? '三節' : /季|分紅|酬勞|績效|業績|獎金/.test(ty) ? '分紅／季獎' : '其他');
  const CAT_C = { '年終': '#ffb454', '三節': '#2ec4b6', '分紅／季獎': '#8b7bff', '其他': '#9aa7b8' };
  const chipsOf = (t, n, len) => { const seen = new Set(), out = []; String(t || '').split(/[；;。→＋:：、，,（）()／\/]/).forEach((x) => { x = x.trim(); if (x.length >= 2 && x.length <= len && !seen.has(x)) { seen.add(x); out.push(x); } }); return out.slice(0, n); };
  const chipRow = (label, text, chips) => (text ? '<div class="tc-cg"><span class="tc-cgl">' + label + '</span><span class="tc-chips">' + (chips.length ? chips : [clip(text, 10)]).map((x) => '<em class="tc-chip">' + esc(x) + '</em>').join('') + '</span>' + qpop(esc(text)) + '</div>' : '');
  const lvl3 = (v, map) => { const t = String(v || ''); for (const [re, n] of map) if (re.test(t)) return n; return 0; };
  const gauge = (label, v, map, names) => { const n = lvl3(v, map); return '<div class="tc-gg"><span class="tc-cgl">' + label + '</span><span class="tc-g3" title="' + esc(v || '無資料') + '">' + [1, 2, 3].map((i) => '<i class="' + (i <= n ? 'on l' + n : '') + '"></i>').join('') + '</span><em>' + esc(n ? names[n - 1] : '—') + '</em></div>'; };
  function kpiOf(co) {
    const rs = co.roles || [], col = (f) => rs.map((r) => mdp(r[f])).filter((x) => x != null), r1 = (a) => (a.length ? Math.round(med(a) * 10) / 10 : null), cf = {};
    rs.forEach((r) => { if (r.confidence) cf[r.confidence] = (cf[r.confidence] || 0) + 1; });
    return { ann: r1(col('annual_total_wan')), base: r1(col('base_month_k')), am: r1(col('annual_months')), n: rs.reduce((x, r) => x + (r.n || 0), 0), conf: '—' };
  }
  function topHtml(co) {
    const K = kpiOf(co); K.conf = K.n >= 30 ? '高' : K.n >= 10 ? '中' : K.n > 0 ? '低' : '—';   // 依全公司樣本數：≥30 高、10～29 中、<10 低
    const mo = co.mops && co.mops.avg_wan != null ? co.mops : null;
    const kp = (l, v, u) => '<div class="tc-kpi' + (v == null ? ' na' : '') + '"><span>' + l + '</span><b>' + (v == null ? '—' : esc(v)) + (v != null && u ? '<small>' + u + '</small>' : '') + '</b></div>';
    return '<div class="tc-kpis">' + kp('年薪中位數', K.ann, '萬') + kp('底薪中位數', K.base, 'K/月') + kp('年薪總月數', K.am, '月') + kp('樣本數', K.n, '筆') + kp('信心（依樣本數）', K.conf === '—' ? null : K.conf) + (mo ? kp('全體員工平均年薪（' + mo.year + '）', mo.avg_wan, '萬') : '') + '</div>';
  }
  function calHtml(co) {
    const bs = Array.isArray(co.bonus_structure) ? co.bonus_structure : [], by = {};
    bs.forEach((x) => monthsIn(String(x.type || '') + ' ' + String(x.rule || '')).forEach((m) => { (by[m] = by[m] || []).push(catOf(String(x.type || ''))); }));
    if (!bs.length) monthsIn(co.bonus_timing).forEach((m) => { by[m] = ['分紅／季獎']; });
    const has = Object.keys(by).length, cats = Array.from(new Set([].concat(...Object.values(by))));
    return '<div class="tc-cal"><div class="tc-payh"><h5>獎金發放月曆</h5>' + (has ? '<span class="tc-cl">' + cats.map((c) => '<em><i style="background:' + CAT_C[c] + '"></i>' + c + '</em>').join('') + '</span>' : '') + '</div>' +
      '<div class="tc-cm12">' + [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => { const c = Array.from(new Set(by[m] || [])); return '<div class="tc-cm' + (c.length ? ' lit' : '') + '" title="' + (c.length ? m + ' 月：' + esc(c.join('、')) : m + ' 月：無已知發放') + '"><b>' + m + '</b><span>' + c.map((x) => '<i style="background:' + CAT_C[x] + '"></i>').join('') + '</span></div>'; }).join('') + '</div>' +
      (has ? '' : '<div class="tc-paynote">發放月份查無資料</div>') +
      '<div class="tc-gauges">' + gauge('加班', top((co.roles || []).map((r) => r.overtime)), [[/幾乎不/, 1], [/偶/, 2], [/經常|常/, 3]], ['幾乎不', '偶爾', '經常']) + gauge('出差', top((co.roles || []).map((r) => r.travel)), [[/不用|無|幾乎不/, 1], [/偶/, 2], [/經常|常/, 3]], ['不用', '偶爾', '經常']) + '</div></div>';
  }
  function chipsHtml(co) {
    const sp = co.stock_plan, st = [['RSU', /RSU/i], ['PSU', /PSU/i], ['員工認股', /認股/], ['員工購股', /購股/], ['庫藏股', /庫藏/], ['配股', /配股/]].filter(([, re]) => re.test(sp || '')).map((x) => x[0]);
    const cu = co.culture || '', gj = cu.match(/工時[^；，。]*?(\d(?:\.\d)?)\s*[／\/]\s*5/), cc = (gj ? ['工時 ' + gj[1] + '/5'] : []).concat(/高工時/.test(cu) ? ['高工時'] : [], /輪班/.test(cu) ? ['輪班'] : [], chipsOf(cu, 3, 9));
    const bm = monthsIn(co.bonus_timing);
    const chg = '<div class="tc-chg">' + chipRow('福利', co.benefits, chipsOf(co.benefits, 4, 9)) + chipRow('持股', sp, st.length ? st : chipsOf(sp, 3, 10)) + chipRow('風氣', cu, Array.from(new Set(cc)).slice(0, 4)) + chipRow('面試', co.interview, chipsOf(co.interview, 4, 10)) + chipRow('分紅時間', co.bonus_timing, bm.length ? [bm.join('/') + ' 月'] : []) + '</div>';
    return mob() ? '<details class="tc-chd"><summary>福利・持股・風氣・面試（點開）</summary>' + chg + '</details>' : chg;
  }
  const bonusBlock = (co) => {
    const bs = Array.isArray(co.bonus_structure) ? co.bonus_structure : [];
    const src = (x) => (x.sources || []).filter((s) => s && s.url).map((s) => '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.site || '來源') + (s.date ? ' ' + esc(s.date) : '') + '</a>').join('・');
    let body;
    if (bs.length) body = '<div class="tc-bcards">' + bs.map((x) => { const ty = String(x.type || '—'), c = CAT_C[catOf(ty)], mm = monthsIn(x.rule); return '<div class="tc-bsr" style="--bc:' + c + '"><i class="tc-bic">' + esc(ty.charAt(0)) + '</i><b>' + esc(ty) + '</b><em>' + (x.months != null ? esc(x.months) + '<small>個月</small>' : '<small>不固定</small>') + '</em><span>' + (mm.length ? mm.join('/') + ' 月' : '月份未載') + '</span>' + qpop(esc(x.rule || '—') + (src(x) ? '<br><span class="muted">' + src(x) + '</span>' : '')) + '</div>'; }).join('') + '</div>';
    else if (co.bonus_timing) body = '<div class="tc-bcards"><div class="tc-bsr"><b>發放時間</b><span>' + esc(clip(co.bonus_timing, 16)) + '</span>' + qpop(esc(co.bonus_timing)) + '</div></div>';
    else return '';
    const n = bs.length;
    const ttl = '分紅結構' + (n ? '（' + n + ' 種獎金）' : '（發放時間）');
    return matchMedia('(max-width:640px)').matches ? '<details class="tc-bs"><summary>' + ttl + '</summary>' + body + '</details>' : '<div class="tc-bs"><h5>' + ttl + '</h5>' + body + '</div>';
  };
  const dash = (x) => (x === '–' ? '—' : x);
  const rng = (a, u) => (Array.isArray(a) && a.length ? (a[0] === a[a.length - 1] ? a[0] : a[0] + '–' + a[a.length - 1]) + (u || '') : '—');
  const roleOk = (r) => FILTERS.every((F) => { const i = S.f[F.k] || 0; return i === 0 || F.opts[i][1](r); });
  const nActive = () => FILTERS.filter((F) => (S.f[F.k] || 0) > 0).length;
  const sortVal = { base: (r) => mid(r.base_month_k), bonus: (r) => mid(r.bonus_months), annual: (r) => mid(r.annual_total_wan), hours: (r) => mid(r.weekly_hours), n: (r) => r.n };

  async function loadAll() {
    if (S.loaded) return;
    await Promise.all(INDS.map(async ([id]) => {
      try { const r = await fetch('tc/json/' + id + '.json', { cache: 'no-cache' }); S.data[id] = r.ok ? await r.json() : null; }
      catch (e) { S.data[id] = null; }
    }));
    /* 職位區間若有 samples 就由 samples 算（最小～最大），沒有才用手填值 */
    const mm = (a) => { a = [].concat(...a.map(fl)); return a.length ? [Math.min(...a), Math.max(...a)] : null; };
    Object.values(S.data).forEach((d) => d && (d.companies || []).forEach((c) => (c.roles || []).forEach((r) => {
      const sm = (Array.isArray(r.samples) ? r.samples : []).filter(inWin); if (!sm.length) return;
      r.n = sm.length;
      [['base_month_k', 'base_k'], ['bonus_months', 'bonus_months'], ['annual_months', 'annual_months'], ['annual_total_wan', 'annual_wan'], ['weekly_hours', 'weekly_hours']].forEach(([a, b]) => { const v = mm(sm.map((x) => x[b])); if (v) r[a] = v; });
    })));
    S.loaded = true;
  }

  /* 「?」小說明：點開浮出、點背景關閉（Andy 規矩 B2：說明收進 ?） */
  function howHtml() {
    return '<span class="tc-how"><button class="howbtn tc-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button>' +
      '<div class="tc-pop" hidden><b>怎麼用</b><br>上方挑產業，五組篩選（工時、底薪、分紅月數、年薪、加班）同時作用在公司卡與職位表；點公司卡看各單位的職位。' +
      '數字都是整理後的區間，篩選拿區間中點比；信心度低代表來源少或彼此對不起來。' + '<br>「樣本統計」分頁：橫條是中位數、細線是最低到最高；越長代表該產業（公司）給得越高，線越長代表落差越大、談薪空間越大；公司排行可切底薪／年薪並按產業篩選，點一列進公司頁。' + '<br><span class="muted">' + esc(FOOT) + '</span></div></span>';
  }
  function bindHow(root) {
    const b = $('.tc-q', root), p = $('.tc-pop', root); if (!b || !p) return;
    const close = () => { p.hidden = true; b.setAttribute('aria-expanded', 'false'); };
    b.onclick = (e) => { e.stopPropagation(); p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); };
    document.addEventListener('click', (e) => { if (!p.hidden && !p.contains(e.target)) close(); });
  }

  function filterBar() {
    const n = nActive();
    return '<div class="tc-fbar"><button class="tc-ftog" type="button" aria-expanded="' + S.fopen + '">篩選' + (n ? '（' + n + '）' : '') + '</button>' +
      '<div class="tc-fgrp' + (S.fopen ? ' open' : '') + '">' + FILTERS.map((F) =>
        '<div class="tc-f" title="' + esc(F.tip) + '"><span class="tc-fl">' + F.t + '</span><div class="seg" data-fk="' + F.k + '">' +
        F.opts.map((o, i) => '<button type="button" data-i="' + i + '" class="' + ((S.f[F.k] || 0) === i ? 'on' : '') + '">' + esc(o[0]) + '</button>').join('') + '</div></div>').join('') +
      '<button class="tc-clear" type="button"' + (n ? '' : ' hidden') + '>清除篩選</button></div></div>';
  }

  /* 來源欄只放統計「N 筆（Dcard x／GoodJob y／PTT z）」，明細看 ▸ 展開的逐筆樣本 */
  function srcHtml(r) {
    const ss = r.sources || []; if (!ss.length) return '–';
    const m = {}; ss.forEach((x) => { m[x.site] = (m[x.site] || 0) + 1; });
    return '<span title="' + esc(Object.keys(m).map((k) => k + ' ' + m[k]).join('／')) + '">' + ss.length + ' 筆</span>';
  }
  const confCls = (c) => (c === '高' ? 'hi' : c === '中' ? 'mid' : 'lo');

  /* 只有 date_confirmed:true 且 date ≥ 2025-08 的樣本進統計；日期未確認標「日期未確認」、範圍外標「範圍外參考」，都照列但標灰 */
  const smSt = (x) => (x.date_confirmed !== true ? 'unc' : (x.in_window === false || !x.date || String(x.date) < '2025-08' ? 'out' : 'in'));
  const inWin = (x) => smSt(x) === 'in';
  const fl = (v) => (typeof v === 'number' ? [v] : Array.isArray(v) ? v.filter((x) => typeof x === 'number') : []);   // 樣本值可能是區間陣列：展開成數值
  const mdp = (v) => { const a = fl(v); return a.length ? (Math.min(...a) + Math.max(...a)) / 2 : null; };   // 區間取中點
  const nv = (v) => { if (v == null) return '—'; if (Array.isArray(v)) { const a = fl(v); if (!a.length) return '—'; const lo = Math.min(...a), hi = Math.max(...a); return lo === hi ? lo : lo + '–' + hi; } return v; };
  function smRow(r) {
    const sm = r.samples || []; if (!sm.length) return '';
    return '<tr class="tc-smrow" hidden><td colspan="14"><div class="tc-smw"><table class="tc-smt"><thead><tr>' + ['來源・日期', '單位細項', '年資', '學歷', '底薪(K)', '年薪(萬)', '分紅月數', '工時', '加班', '摘要'].map((x) => '<th>' + x + '</th>').join('') + '</tr></thead><tbody>' +
      sm.map((x) => '<tr' + (inWin(x) ? '' : ' class="tc-out" title="不進統計"') + '><td data-l="來源・日期">' + (smSt(x) === 'unc' ? '<em>日期未確認</em> ' : smSt(x) === 'out' ? '<em>範圍外參考</em> ' : '') + (/^https?:\/\//.test(x.url || '') ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer">' + esc(x.site || '連結') + '</a>' : esc(x.site || '—')) + ' ' + esc(x.date || '') + '</td><td data-l="單位細項">' + esc(nv(x.unit_detail)) + '</td><td data-l="年資">' + esc(nv(x.years)) + '</td><td data-l="學歷">' + esc(nv(x.degree)) + '</td><td data-l="底薪(K)">' + nv(x.base_k) + '</td><td data-l="年薪(萬)">' + nv(x.annual_wan) + '</td><td data-l="分紅月數">' + nv(x.bonus_months) + '</td><td data-l="工時">' + nv(x.weekly_hours) + '</td><td data-l="加班">' + esc(nv(x.overtime)) + '</td><td data-l="摘要" class="tc-clip" title="點一下展開／收合">' + esc(nv(x.quote_free_note)) + '</td></tr>').join('') + '</tbody></table></div></td></tr>';
  }
  const med = (a) => { a = a.filter((v) => typeof v === 'number').sort((x, y) => x - y); if (!a.length) return null; const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  const stat = (a) => { const v = [].concat(...a.map(fl)), m = a.map(mdp).filter((x) => x != null); return v.length ? med(m) + '（' + Math.min(...v) + '–' + Math.max(...v) + '）' : '—'; };

  /* ---------- 圖表化（2026-10-26）：各產業中位數＋區間、樣本筆數、公司排行（含 LOGO） ---------- */
  function aggStats() {
    const mk = (sm) => { const f = (k) => { const raw = sm.map((x) => x[k]), v = [].concat(...raw.map(fl)), m = raw.map(mdp).filter((x) => x != null); return v.length ? { med: Math.round(med(m) * 10) / 10, min: Math.min(...v), max: Math.max(...v), n: m.length } : null; }; return { n: sm.length, base: f('base_k'), ann: f('annual_wan') }; };
    const inds = [], cos = [];
    INDS.forEach(([id, n]) => {
      const d = S.data[id]; if (!d) return; let all = [];
      (d.companies || []).forEach((c) => {
        const sm = [].concat(...(c.roles || []).map((r) => (r.samples || []).filter(inWin))); if (!sm.length) return;
        all = all.concat(sm); cos.push(Object.assign({ ind: id, indName: n, name: c.name }, mk(sm)));
      });
      if (all.length) inds.push(Object.assign({ id, name: n }, mk(all)));
    });
    return { inds, cos };
  }
  const RK_SHOW_D = 15, RK_SHOW_M = 10, mob = () => matchMedia('(max-width:640px)').matches;
  function rankHtml(A) {
    const m = S.rk.m, key = m === 'base' ? 'base' : 'ann', unit = m === 'base' ? 'K/月' : '萬/年';
    const list = A.cos.filter((c) => c[key] && (S.rk.ind === 'all' || c.ind === S.rk.ind)).sort((a, b) => b[key].med - a[key].med);
    const top = S.rk.all ? list : list.slice(0, (mob() ? RK_SHOW_M : RK_SHOW_D)), mx = Math.max(1, ...list.map((c) => c[key].max));
    const seg = (k, arr) => '<div class="seg" data-rk="' + k + '">' + arr.map(([v, t]) => '<button type="button" data-v="' + v + '" class="' + (String(S.rk[k]) === v ? 'on' : '') + '">' + esc(t) + '</button>').join('') + '</div>';
    const indOpts = [['all', '全部產業']].concat(A.inds.map((x) => [x.id, x.name]));
    return '<div class="tc-rkbar"><span class="tc-fl">排行依</span>' + seg('m', [['ann', '年薪'], ['base', '底薪']]) + '<span class="tc-fl">產業</span>' + seg('ind', indOpts) + '</div>' +
      '<div class="tc-cnt">共 <b>' + list.length + '</b> 家有樣本（中位數由高到低；細線＝最低到最高；單位 ' + unit + '）</div>' +
      (list.length ? '<div class="tc-rk">' + top.map((c, i) => { const v = c[key], w = Math.max(2, v.med / mx * 100), l = v.min / mx * 100, r = v.max / mx * 100;
        return '<a class="tc-rkr" href="#tc/' + c.ind + '/' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '"><span class="tc-rkn">' + (i + 1) + '</span>' + TL(c.name, c.ind, 24) + '<span class="tc-rkt">' + esc(c.name) + '<small>' + esc(c.indName) + '・' + c.n + ' 筆</small></span>' +
          '<span class="tc-rkb"><i class="tc-rkbar" style="width:' + w.toFixed(1) + '%"></i><i class="tc-rkrg" style="left:' + l.toFixed(1) + '%;width:' + Math.max(0.5, r - l).toFixed(1) + '%"></i></span>' +
          '<span class="tc-rkv"><b>' + v.med + '</b><small>' + v.min + '–' + v.max + '</small></span></a>'; }).join('') + '</div>' +
        (list.length > (mob() ? RK_SHOW_M : RK_SHOW_D) ? '<button type="button" class="tc-rkmore">' + (S.rk.all ? '只看前 ' + RK_SHOW : '看全部 ' + list.length + ' 家') + '</button>' : '') : '<div class="empty isempty tc-empty">這個產業沒有樣本</div>');
  }
  const TL = (name, ind, sz) => (window.TcLogo ? window.TcLogo.html(name, ind, sz) : '');
  function bindRank(root) {
    $$('.seg[data-chm] button', root).forEach((b) => b.onclick = () => { S.chm = b.dataset.v; $$('.seg[data-chm] button', root).forEach((x) => x.classList.toggle('on', x === b)); const g = $('.tc-gr', root); if (g) g.dataset.m = S.chm; drawStats(); });
    $$('.seg[data-chv] button', root).forEach((b) => b.onclick = () => { S.chv = b.dataset.v; $$('.seg[data-chv] button', root).forEach((x) => x.classList.toggle('on', x === b)); drawStats(); });
    const A = S.agg, box = $('#tcRank', root); if (!box) return;
    $$('.seg[data-rk] button', box).forEach((b) => b.onclick = () => { const k = b.parentNode.dataset.rk; S.rk[k] = b.dataset.v; S.rk.all = false; box.innerHTML = rankHtml(A); bindRank(root); });
    const mo = $('.tc-rkmore', box); if (mo) mo.onclick = () => { S.rk.all = !S.rk.all; box.innerHTML = rankHtml(A); bindRank(root); };
  }
  const cv = (n, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d; } catch (e) { return d; } };
  const INK2 = () => cv('--ink-2', '#5b6b80'), INK3 = () => cv('--ink-3', '#8a97ab');
  function indBarOpt(A, key, unit, color) {
    const rows = A.inds.filter((x) => x[key]).sort((a, b) => a[key].med - b[key].med);   // 升冪＋橫條由下往上畫＝最高在最上
    const rng = rows.map((x, i) => [x[key].min, x[key].max, i]);
    return { grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, formatter: (p) => { const x = rows[p[0].dataIndex]; return esc(x.name) + '<br>中位數 <b>' + x[key].med + '</b> ' + unit + '<br>區間 ' + x[key].min + '–' + x[key].max + '<br>樣本 ' + x[key].n + ' 筆'; } },
      xAxis: { type: 'value', axisLabel: { color: INK3(), fontSize: 12 }, splitLine: { lineStyle: { opacity: .15 } } },
      yAxis: { type: 'category', data: rows.map((x) => x.name), axisLabel: { color: INK2(), fontSize: 12 }, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { type: 'bar', data: rows.map((x) => x[key].med), barWidth: 12, itemStyle: { borderRadius: [0, 3, 3, 0], color: color }, showBackground: true, backgroundStyle: { color: 'rgba(120,140,170,.12)', borderRadius: 3 }, z: 2,
          label: { show: false } },
        { type: 'custom', data: rng, z: 3, silent: true, tooltip: { show: false },
          renderItem: (params, api) => { const a = api.coord([api.value(0), api.value(2)]), b = api.coord([api.value(1), api.value(2)]), st = { stroke: '#ffb454', lineWidth: 2 };
            return { type: 'group', children: [{ type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: st }, { type: 'line', shape: { x1: a[0], y1: a[1] - 5, x2: a[0], y2: a[1] + 5 }, style: st }, { type: 'line', shape: { x1: b[0], y1: b[1] - 5, x2: b[0], y2: b[1] + 5 }, style: st }] }; } }
      ] };
  }
  /* ---------- 甜甜圈（圖表庫 A 款）：產業樣本占比、各產業底薪／年薪環組、公司薪資組成 ---------- */
  const PAL = { base: '#3ee0ff', year: '#ffb454', bonus: '#8b7bff', other: '#2ec4b6', rest: '#9aa7b8' };
  const TRACK = () => cv('--panel-3', '#e4ebf3');
  const INK1 = () => cv('--ink', '#10202f');
  const IND_PAL = ['#3ee0ff', '#8b7bff', '#ffb454', '#2ec4b6', '#ff7a45'];
  function shareOpt(A, el) {
    const rows = A.inds.slice().sort((a, b) => b.n - a.n), top = rows.slice(0, 5), rest = rows.slice(5), tot = rows.reduce((s, x) => s + x.n, 0);
    const data = top.map((x, i) => ({ name: x.name, value: x.n, id: x.id, itemStyle: { color: IND_PAL[i] } }));
    if (rest.length) data.push({ name: '其他', value: rest.reduce((s, x) => s + x.n, 0), items: rest.map((x) => x.name + ' ' + x.n), itemStyle: { color: '#9aa7b8' } });
    const narrow = true;   // 卡片窄，圖例一律放下方（放右側會壓到環）
    return { _tot: tot, tooltip: { trigger: 'item', confine: true, formatter: (p) => esc(p.name) + '：<b>' + p.value + '</b> 筆（' + (p.value / tot * 100).toFixed(1) + '%）' + (p.data.items ? '<br>' + p.data.items.map(esc).join('<br>') : '') },
      legend: { orient: narrow ? 'horizontal' : 'vertical', right: narrow ? 'center' : 4, bottom: narrow ? 0 : 'middle', top: narrow ? undefined : 'middle', itemWidth: 10, itemHeight: 10, textStyle: { color: INK2(), fontSize: 12 },
        formatter: (n) => { const d = data.find((x) => x.name === n); return n + '  ' + (d ? d.value : '') + ' 筆・' + (d ? Math.round(d.value / tot * 100) : 0) + '%'; } },
      graphic: [{ id: 'c1', type: 'text', silent: true, style: { text: '樣本', fill: INK3(), fontSize: 12, textAlign: 'center' } }, { id: 'c2', type: 'text', silent: true, style: { text: String(tot), fill: INK1(), fontSize: 28, fontWeight: 700, textAlign: 'center' } }],
      series: [{ type: 'pie', radius: ['38%', '54%'], center: ['50%', '32%'], avoidLabelOverlap: true, label: { show: false }, labelLine: { show: false }, padAngle: 1, itemStyle: { borderRadius: 6, borderColor: cv('--panel-2', '#fff'), borderWidth: 1 }, emphasis: { scale: true, scaleSize: 4, itemStyle: { borderColor: cv('--cyan', '#3ee0ff'), borderWidth: 3 } }, data }] };
  }
  /* 中心字位置依實際容器算（graphic 要 px）；hover 時換成該塊名稱與占比 */
  function centerText(c, el, cx, cy, t1, t2) { c.setOption({ graphic: [{ id: 'c1', style: { text: t1 }, x: cx, y: cy - 22 }, { id: 'c2', style: { text: t2 }, x: cx, y: cy - 8 }] }); }
  function drawShare(ch) {
    const A = S.agg, el = document.getElementById('tcChN'); if (!el || !el.clientWidth) return;
    el.style.height = '330px';
    const o = shareOpt(A, el), c = ch(el, o); if (!c) return;
    const W = el.clientWidth, H = el.clientHeight, cx = W * .5, cy = H * .32, tot = o._tot;
    centerText(c, el, cx, cy, '樣本', String(tot));
    c.off('mouseover'); c.off('globalout');
    c.on('mouseover', (p) => { if (p.seriesType === 'pie') centerText(c, el, cx, cy, p.name, (p.value / tot * 100).toFixed(1) + '%'); });
    c.on('globalout', () => centerText(c, el, cx, cy, '樣本', String(tot)));
  }
  function ringsOpt(A, key, unit, color, el) {
    const rows = A.inds.filter((x) => x[key]).sort((a, b) => b[key].med - a[key].med), mx = Math.max(1, ...rows.map((x) => x[key].med));
    const W = el.clientWidth, cols = W >= 300 && !mob() ? 3 : 2, cellH = 112, R = 32, pos = rows.map((x, i) => [(i % cols + .5) * W / cols, Math.floor(i / cols) * cellH + 44]);
    el.style.height = Math.ceil(rows.length / cols) * cellH + 'px';
    return { tooltip: { trigger: 'item', confine: true, formatter: (p) => { const x = rows[p.seriesIndex]; return x ? esc(x.name) + '<br>中位數 <b>' + x[key].med + '</b> ' + unit + '<br>區間 ' + x[key].min + '–' + x[key].max + '<br>樣本 ' + x[key].n + ' 筆' : ''; } },
      graphic: rows.map((x, i) => ({ type: 'text', silent: true, x: pos[i][0], y: pos[i][1] + R + 8, style: { text: x.name, fill: INK2(), fontSize: 12, textAlign: 'center' } })),
      series: rows.map((x, i) => ({ type: 'pie', radius: [R * .72, R], center: pos[i], silent: false, startAngle: 90, label: { show: true, position: 'center', formatter: () => String(x[key].med), color: INK1(), fontSize: 12, fontWeight: 700 }, labelLine: { show: false }, emphasis: { scale: true, scaleSize: 3, label: { show: true } },
        data: [{ value: x[key].med, name: x.name, itemStyle: { color } }, { value: Math.max(mx - x[key].med, mx * .02), name: '', tooltip: { show: false }, itemStyle: { color: TRACK() }, emphasis: { disabled: true } }] })) };
  }
  function drawStats() {
    const A = S.agg, ch = window.App && window.App.chart; if (!A || !ch) return;
    const mkH = (n) => Math.max(120, n * 30 + 24);
    const draw = (id, key, unit, color) => { const el = document.getElementById(id); if (!el || !el.clientWidth) return; const n = A.inds.filter((x) => x[key]).length;
      if (S.chv === 'bar') { el.style.height = mkH(n) + 'px'; ch(el, indBarOpt(A, key, unit, color)); } else ch(el, ringsOpt(A, key, unit, color, el)); };
    draw('tcChBase', 'base', 'K/月', '#3ee0ff'); draw('tcChAnn', 'ann', '萬/年', '#8b7bff');
    drawShare(ch);
    $$('#tcChBase,#tcChAnn', document).forEach((e) => { const c = window.echarts && window.echarts.getInstanceByDom(e); if (!c) return; c.off('click'); c.on('click', (q) => { const key = e.id === 'tcChBase' ? 'base' : 'ann'; const rows = S.chv === 'bar' ? A.inds.filter((x) => x[key]).sort((a, b) => a[key].med - b[key].med) : A.inds.filter((x) => x[key]).sort((a, b) => b[key].med - a[key].med); const k = S.chv === 'bar' ? q.dataIndex : q.seriesIndex; if (rows[k]) location.hash = '#tc/' + rows[k].id; }); });
  }
  function chartsHtml(A) {
    if (!A.inds.length) return '';
    const sg = (k, arr, cur) => '<div class="seg" data-' + k + '="1">' + arr.map(([v, t]) => '<button type="button" data-v="' + v + '" class="' + (cur === v ? 'on' : '') + '">' + t + '</button>').join('') + '</div>';
    return '<div class="tc-chm">' + sg('chm', [['share', '占比'], ['base', '底薪'], ['ann', '年薪']], S.chm) + sg('chv', [['ring', '甜甜圈'], ['bar', '橫條']], S.chv) + '</div>' +
      '<div class="tc-gr" data-m="' + S.chm + '"><div class="tc-gc" data-c="share"><h5>各產業樣本占比</h5><div id="tcChN" class="tc-ch"></div></div><div class="tc-gc" data-c="base"><h5>各產業底薪中位數（K/月）</h5><div id="tcChBase" class="tc-ch"></div></div><div class="tc-gc" data-c="ann"><h5>各產業年薪中位數（萬/年）</h5><div id="tcChAnn" class="tc-ch"></div></div></div>' +
      '<div class="tc-rkw"><h5>公司排行</h5><div id="tcRank">' + rankHtml(A) + '</div></div>';
  }
  /* ---------- 公司薪資組成：以「月數」為單位，缺的不捏造 ---------- */
  function payOf(co, r) {
    const bs = Array.isArray(co.bonus_structure) ? co.bonus_structure : [], num = (x) => (typeof x.months === 'number' ? x.months : null);
    const sumOf = (f) => { let t = 0, ok = false; bs.forEach((x) => { const m = num(x), ty = String(x.type || ''); if (m != null && f(ty)) { t += m; ok = true; } }); return ok ? t : null; };
    const baseK = mdp(r.base_month_k), annM = mdp(r.annual_months), annW = mdp(r.annual_total_wan), bonus = mdp(r.bonus_months);
    const year = sumOf((t) => /年終/.test(t) && !/分紅|保障/.test(t)), other = sumOf((t) => !/年終|分紅|酬勞|保障|RSU/.test(t));
    const parts = [], miss = [];
    if (baseK != null) parts.push({ k: 'base', name: '底薪', m: 12, c: PAL.base }); else miss.push('底薪查無資料');
    if (year != null) parts.push({ k: 'year', name: '年終', m: year, c: PAL.year }); else miss.push('年終月數查無資料');
    if (bonus != null) parts.push({ k: 'bonus', name: '分紅', m: bonus, c: PAL.bonus }); else miss.push('分紅月數查無資料');
    if (other != null) parts.push({ k: 'other', name: '三節／其他獎金', m: other, c: PAL.other }); else miss.push('三節／其他獎金月數查無資料');
    const known = parts.reduce((s, p) => s + p.m, 0);
    if (annM != null && annM > 0) { const rest = annM - known; if (rest > 0.4 && parts.length) parts.push({ k: 'rest', name: '其餘獎金（分紅／季獎金等，未細分）', m: Math.round(rest * 10) / 10, c: PAL.rest }); if (annM > 0 && !parts.length) miss.push('只有年薪總月數'); } else miss.push('年薪總月數查無資料');
    return { parts, miss, baseK, annM, annW, known };
  }
  const payRoles = (co) => (co.roles || []).filter((r) => hasNum(r.base_month_k) || hasNum(r.annual_months) || hasNum(r.annual_total_wan) || hasNum(r.bonus_months));
  function payHtml(co) {
    const rs = payRoles(co);
    if (!rs.length) return '<div class="tc-pay"><h5>薪資組成</h5><div id="tcPay" class="tc-paych"></div><div class="tc-paynote">資料不足：這家公司還沒有可用的底薪／年薪數字</div></div>';
    const fullness = (r) => ['base_month_k', 'bonus_months', 'annual_months', 'annual_total_wan'].filter((k) => hasNum(r[k])).length;
    let bi = 0; rs.forEach((r, i) => { const b = rs[bi]; if (fullness(r) > fullness(b) || (fullness(r) === fullness(b) && (r.n || 0) > (b.n || 0))) bi = i; });   // 預設：資料最完整的職位，同分取樣本多的
    S.payI = S.payI != null && S.payI < rs.length ? S.payI : bi;
    return '<div class="tc-pay"><div class="tc-payh"><h5>薪資組成（以月數計）</h5><select id="tcPaySel" aria-label="選職位">' + rs.map((r, i) => '<option value="' + i + '"' + (i === S.payI ? ' selected' : '') + '>' + esc((r.unit || '') + '・' + (r.role || '') + '（' + (r.n || 0) + ' 筆）') + '</option>').join('') + '</select></div>' +
      '<div class="tc-paybody"><div id="tcPay" class="tc-paych"></div><div id="tcPayLg" class="tc-paylg"></div></div><div id="tcPayNote" class="tc-paynote"></div></div>';
  }
  function drawPay(co) {
    const ch = window.App && window.App.chart, el = document.getElementById('tcPay'); if (!el || !ch) return;
    const rs = payRoles(co), lg = document.getElementById('tcPayLg'), nt = document.getElementById('tcPayNote');
    el.style.height = (mob() ? 190 : 200) + 'px';
    const r = rs[S.payI || 0], P = r ? payOf(co, r) : { parts: [], miss: [], baseK: null, annM: null, annW: null };
    const W = el.clientWidth || 200, H = el.clientHeight, cx = W / 2, cy = H / 2;
    const amt = (m) => (P.baseK != null ? '約 ' + (m * P.baseK / 10).toFixed(1) + ' 萬' : '');
    const empty = !P.parts.length, tot = P.annM != null ? P.annM : P.known;
    const t1 = empty ? '資料不足' : (P.annM != null ? '年薪總月數' : '已知月數'), t2 = empty ? '' : String(Math.round(tot * 10) / 10), t3 = P.annW != null && H >= 190 ? '年薪中位 ' + P.annW + ' 萬' : '';
    const c = ch(el, { tooltip: { trigger: 'item', confine: true, formatter: (p) => (p.data && p.data.k ? esc(p.name) + '：<b>' + p.value + '</b> 個月' + (amt(p.value) ? '（' + amt(p.value) + '）' : '') : '') },
      graphic: [{ id: 'c1', type: 'text', silent: true, x: cx, y: cy - 24, style: { text: t1, fill: INK3(), fontSize: 12, textAlign: 'center' } }, { id: 'c2', type: 'text', silent: true, x: cx, y: cy - 10, style: { text: t2, fill: INK1(), fontSize: 26, fontWeight: 700, textAlign: 'center' } }, { id: 'c3', type: 'text', silent: true, x: cx, y: cy + 26, style: { text: t3, fill: INK3(), fontSize: 12, textAlign: 'center' } }],
      series: [{ type: 'pie', radius: ['62%', '90%'], center: ['50%', '50%'], label: { show: false }, labelLine: { show: false }, padAngle: 1, itemStyle: { borderRadius: 5 }, emphasis: { scale: true, scaleSize: 4, itemStyle: { borderColor: cv('--cyan', '#3ee0ff'), borderWidth: 3 } },
        data: empty ? [{ value: 1, name: '', itemStyle: { color: TRACK() }, emphasis: { disabled: true } }] : P.parts.map((p) => ({ value: p.m, name: p.name, k: p.k, itemStyle: { color: p.c } })) }] });
    if (c) { c.off('mouseover'); c.off('globalout'); c.on('mouseover', (q) => { if (q.data && q.data.k) { c.setOption({ graphic: [{ id: 'c1', style: { text: q.name } }, { id: 'c2', style: { text: String(q.value) + ' 月' } }, { id: 'c3', style: { text: amt(q.value) } }] }); } }); c.on('globalout', () => c.setOption({ graphic: [{ id: 'c1', style: { text: t1 } }, { id: 'c2', style: { text: t2 } }, { id: 'c3', style: { text: t3 } }] })); }
    if (lg) lg.innerHTML = P.parts.map((p) => '<div class="tc-pl"><i style="background:' + p.c + '"></i><span>' + esc(p.name) + '</span><b>' + p.m + ' 月</b><small>' + esc(amt(p.m)) + '</small></div>').join('');
    if (nt) nt.textContent = empty ? '資料不足：' + (P.miss.join('、') || '') : (P.miss.length ? P.miss.join('、') + '（該塊未畫，不推算）' : '底薪以 12 個月計；其餘依公司層獎金結構與職位樣本');
  }
  /* 樣本統計：產業→公司→單位→職位，每層 <details> 預設收起，只有一組時展開 */
  function statsHtml() {
    const row = (name, sm, lvl) => '<span class="tc-sn">' + esc(name) + '</span><span data-l="樣本">' + sm.length + ' 筆</span><span data-l="底薪中位數(區間)">' + stat(sm.map((x) => x.base_k)) + '</span><span data-l="年薪中位數(區間)">' + stat(sm.map((x) => x.annual_wan)) + '</span>';
    const node = (name, sm, kids, lvl, only) => kids ? '<details class="tc-st l' + lvl + '"' + (only ? ' open' : '') + '><summary>' + row(name, sm, lvl) + '</summary>' + kids + '</details>' : '<div class="tc-st leaf l' + lvl + '">' + row(name, sm, lvl) + '</div>';
    let all = 0, unc = 0, outc = 0;
    Object.values(S.data).forEach((d) => d && (d.companies || []).forEach((c) => (c.roles || []).forEach((r) => (r.samples || []).forEach((x) => { if (smSt(x) === 'unc') unc++; else if (smSt(x) === 'out') outc++; }))));
    const inds = INDS.map(([id, n]) => {
      const d = S.data[id]; if (!d) return null;
      const cs = (d.companies || []).map((c) => {
        const us = {}; (c.roles || []).forEach((r) => { (r.samples || []).filter(inWin).forEach((x) => { (us[r.unit] = us[r.unit] || {})[r.role] = (us[r.unit][r.role] || []).concat(x); }); });
        const ul = Object.keys(us); const csm = [];
        const uh = ul.map((u) => { const rl = Object.keys(us[u]); const usm = [].concat(...rl.map((k) => us[u][k])); csm.push(...usm); return node(u, usm, rl.map((k) => node(k, us[u][k], '', 4)).join(''), 3, ul.length === 1); }).join('');
        return csm.length ? [c.name, csm, uh] : null;
      }).filter(Boolean);
      if (!cs.length) return null;
      const isan = [].concat(...cs.map((c) => c[1])); all += isan.length;
      return node(n, isan, cs.map((c) => node(c[0], c[1], c[2], 2, cs.length === 1)).join(''), 1, false);
    }).filter(Boolean);
    S.agg = aggStats();
    return chartsHtml(S.agg) + (S.agg.inds.length ? '<details class="tc-raw"><summary>看數字明細（產業→公司→單位→職位）</summary>' : '<div>') + '<div class="tc-cnt">進統計 <b id="tcAll">' + all + '</b> 筆・未確認 ' + unc + '・範圍外 ' + outc + qpop('統計只算日期確認且 2025-08 起的樣本；明細依 產業→公司→單位→職位 逐層展開；底薪／年薪為中位數，括號內是最低到最高區間。') + '</div>' + (inds.length ? '<div class="tc-stats">' + inds.join('') + '</div>' : '<div class="empty isempty tc-empty">尚無逐筆樣本</div>') + '</' + (S.agg.inds.length ? 'details' : 'div') + '>';
  }

  function rolesTable(roles, bt, tsmc) {
    const cols = [['role', '職位'], ['grade', '職等'], tsmc ? ['busy', '單位繁忙度'] : ['deg', '學歷'], ['base', '底薪(K/月)'], ['bonus', '分紅月數'], ['am', '年薪總月數'], ['bt', '分紅發放'], ['annual', '年薪(萬)'], ['hours', '週工時'], ['ot', '加班'], ['trv', '出差'], ['n', '樣本'], ['conf', '信心'], ['src', '來源・日期']];
    const sk = S.sort.k, sd = S.sort.d;
    /* 同產業全部職位的最大值＝小橫條 100%：看這個職位在產業裡落在哪（只畫條，不加字） */
    const IM = { a: 0, b: 0 }; ((S.data[S.ind] || {}).companies || []).forEach((c) => (c.roles || []).forEach((r) => { IM.a = Math.max(IM.a, mdp(r.annual_total_wan) || 0); IM.b = Math.max(IM.b, mdp(r.base_month_k) || 0); }));
    const mb = (v, mx) => (v == null || !mx ? '' : '<i class="tc-mb" title="同產業最高 ' + mx + '"><b style="width:' + Math.max(3, Math.min(100, v / mx * 100)).toFixed(0) + '%"></b></i>');
    const units = [];
    roles.forEach((r) => { let u = units.find((x) => x.u === r.unit); if (!u) { u = { u: r.unit, rows: [] }; units.push(u); } u.rows.push(r); });
    if (sk && sortVal[sk]) units.forEach((u) => u.rows.sort((a, b) => ((sortVal[sk](a) || 0) - (sortVal[sk](b) || 0)) * sd));
    units.forEach((u) => { const y = u.rows.filter(roleHasData), n = u.rows.filter((r) => !roleHasData(r)); u.rows = y.concat(n); });
    const head = '<tr>' + cols.map(([k, n]) => '<th data-sk="' + (sortVal[k] ? k : '') + '" class="' + (sortVal[k] ? 'srt' : '') + (sk === k ? ' on' : '') + '">' + n + (sk === k ? (sd < 0 ? ' ▼' : ' ▲') : '') + '</th>').join('') + '</tr>';
    const body = units.map((u) => '<tr class="tc-unit"><td colspan="14"><i></i>' + esc(u.u) + '<small>' + u.rows.length + ' 個職位</small></td></tr>' + u.rows.map((r) =>
      '<tr class="tc-row' + (roleHasData(r) ? '' : ' tc-nod') + '"><td data-l="職位" class="tc-role">' + ((r.samples || []).length ? '<button type="button" class="tc-exp" aria-expanded="false" title="展開逐筆樣本">▸</button>' : '') + '<b>' + esc(r.role) + '</b><small>' + esc(r.years ? r.years + ' 年經驗' : '') + '</small></td>' +
      '<td data-l="職等" class="tc-grade">' + esc(r.grade || '—') + '</td>' +
      (tsmc ? '<td data-l="單位繁忙度" class="tc-busy">' + (r.busyness ? '<span class="tc-conf ' + (String(r.busyness).charAt(0) === '高' ? 'lo' : String(r.busyness).charAt(0) === '中' ? 'mid' : 'hi') + '" title="' + esc(r.busyness) + '">' + esc(String(r.busyness).charAt(0)) + '</span>' : '—') + '</td>'
        : '<td data-l="學歷" class="tc-deg">' + esc(r.degree || '—') + (r.degree_diff ? '<small>學士：' + esc(r.degree_diff) + '</small>' : '') + '</td>') +
      '<td data-l="底薪(K/月)">' + '<span class="tc-nv">' + rng(r.base_month_k) + '</span>' + mb(mdp(r.base_month_k), IM.b) + '</td><td data-l="分紅月數">' + rng(r.bonus_months) + '</td><td data-l="年薪總月數">' + dash(rng(r.annual_months)) + '</td><td data-l="分紅發放" class="tc-btm"' + btTitle(r, bt) + '>' + esc(btShort(r.bonus_timing_month ? (btMonths(r.bonus_timing_month) !== '—' ? btMonths(r.bonus_timing_month) : r.bonus_timing_month) : btMonths(bt))) + '</td><td data-l="年薪(萬)" class="tc-big">' + '<span class="tc-nv">' + rng(r.annual_total_wan) + '</span>' + mb(mdp(r.annual_total_wan), IM.a) + '</td>' +
      '<td data-l="週工時">' + rng(r.weekly_hours) + '</td><td data-l="加班"><span class="tc-ot ot-' + esc(r.overtime) + '">' + esc(r.overtime || '—') + '</span></td><td data-l="出差">' + esc(r.travel || '—') + '</td>' +
      '<td data-l="樣本">' + (r.n != null ? r.n : '–') + '</td><td data-l="信心"><span class="tc-conf ' + confCls(r.confidence) + '" title="' + esc(r.note || '') + '">' + esc(r.confidence || '–') + '</span></td>' +
      '<td data-l="來源・日期" class="tc-src">' + srcHtml(r) + '</td></tr>' + smRow(r)).join('')).join('');
    return '<div class="tc-tw"><table class="tc-tbl"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>';
  }

  /* 公司卡：把符合篩選的職位合併成「範圍」；全部缺值就顯示「—」。加班／出差取出現最多的字面值 */
  function span(arr, u) { const v = []; arr.forEach((a) => { if (Array.isArray(a) && a.length) v.push(a[0], a[a.length - 1]); else if (typeof a === 'number') v.push(a); }); return v.length ? (Math.min(...v) === Math.max(...v) ? Math.min(...v) : Math.min(...v) + '–' + Math.max(...v)) + (u || '') : '—'; }
  function top(arr) { const m = {}; arr.filter(Boolean).forEach((x) => { m[x] = (m[x] || 0) + 1; }); const k = Object.keys(m).sort((a, b) => m[b] - m[a])[0]; return k || '—'; }
  const clip = (t, n) => { t = String(t || ''); return t.length > n ? t.slice(0, n) + '…' : t; };
  /* 卡片迷你甜甜圈（純 SVG，不佔 echarts 實例）：取樣本最多的職位組成；沒有可畫的就不放 */
  function miniDonut(c) {
    const rs = payRoles(c); if (!rs.length) return '';
    let b = rs[0]; rs.forEach((r) => { if ((r.n || 0) > (b.n || 0)) b = r; });
    const P = payOf(c, b); if (!P.parts.length) return '';
    const tot = P.parts.reduce((x, p) => x + p.m, 0), R = 15, C = 2 * Math.PI * R; let off = 0;
    return '<div class="tc-mini" title="' + esc('薪資組成（月數）：' + P.parts.map((p) => p.name + p.m).join('／')) + '"><svg viewBox="0 0 40 40" width="44" height="44" aria-hidden="true">' + P.parts.map((p) => { const l = p.m / tot * C, e = '<circle cx="20" cy="20" r="' + R + '" fill="none" stroke="' + p.c + '" stroke-width="6" stroke-dasharray="' + l.toFixed(2) + ' ' + (C - l).toFixed(2) + '" stroke-dashoffset="' + (-off).toFixed(2) + '" transform="rotate(-90 20 20)"/>'; off += l; return e; }).join('') + '</svg></div>';
  }
  function coCard(ind, c, matched) {
    const mini = miniDonut(c), col = (f) => matched.map((r) => mdp(r[f])).filter((v) => v != null);
    const mA = col('annual_total_wan'), mB = col('base_month_k'), hr = col('weekly_hours'), nn = matched.reduce((x, r) => x + (r.n || 0), 0);
    const ann = mA.length ? Math.round(med(mA) * 10) / 10 : null, bs = mB.length ? Math.round(med(mB) * 10) / 10 : null, hh = hr.length ? Math.round(hr.reduce((x, y) => x + y, 0) / hr.length) : null;
    const none = ann == null && bs == null;
    return '<a class="tc-co' + (matched.some(roleHasData) ? '' : ' tc-nod') + '" href="#tc/' + ind + '/' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '">' +
      '<div class="tc-coh">' + TL(c.name, ind, 36) + '<span class="tc-con"><b>' + esc(c.name) + '</b>' + (c.code ? '<small>' + esc(c.code) + '</small>' : '') + '</span>' + (c.heat ? '<span class="tc-heat">' + esc(String(c.heat).replace(/^.*熱度：?/, '熱度 ')) + '</span>' : '') + '</div>' +
      '<div class="tc-cok' + (mini ? ' has-pay' : '') + '"><div class="tc-bigv"><em>' + (ann == null ? '—' : ann) + '</em><span>年薪中位數（萬）</span></div>' + mini + '</div>' +
      '<div class="tc-cof"><span>底薪 <b>' + (bs == null ? '—' : bs + 'K') + '</b></span><span>週工時 <b>' + (hh == null ? '—' : hh) + '</b></span><span>樣本 <b>' + nn + '</b></span><span>符合職位 <b>' + matched.length + '</b></span></div></a>';
  }

  function paint() {
    const root = $('#v-tc'); if (!root) return;
    const d = S.data[S.ind];
    const tabs = '<div class="nbsw tc-tabs" role="tablist" aria-label="產業"><a href="#tc/stats" role="tab" data-ind="stats" class="' + (S.ind === 'stats' ? 'on' : '') + '">樣本統計</a>' + INDS.map(([id, n]) => '<a href="#tc/' + id + '" role="tab" data-ind="' + id + '" class="' + (id === S.ind ? 'on' : '') + '">' + n + (S.data[id] ? '<small>' + (S.data[id].companies || []).length + '</small>' : '') + '</a>').join('') + '</div>';
    let h = '<div class="card tc-card"><div class="row spread tc-hd"><h3>' + esc(S.ind === 'stats' ? '樣本統計' : (INDS.find((x) => x[0] === S.ind) || [])[1] || '') + howHtml() + '</h3><span class="tc-upd">' +
      (d ? '資料 ' + esc(d.updated || '') + '・近一年' : '') + '</span></div>' + tabs + '<div class="tc-body">';
    if (S.ind === 'stats') {
      h += statsHtml();
    } else if (!d || !(d.companies || []).length) {
      h += '<div class="empty isempty tc-empty">尚無資料</div>';
    } else {
      h += filterBar();
      const co = S.co ? d.companies.find((x) => x.name === S.co) : null;
      if (S.co && !co) { h += '<div class="empty isempty tc-empty">找不到這家公司</div>'; }
      else if (co) {
        const m = (co.roles || []).filter(roleOk), tsmc = String(co.code) === '2330';
        h += '<div class="tc-crumb"><a href="#tc/' + S.ind + '" id="tcBack">← 返回公司列表</a></div>' +
          '<div class="tc-cinfo"><h4>' + TL(co.name, S.ind, 40) + ' <span>' + esc(co.name) + '</span>' + (co.code && /^\d{4,6}$/.test(co.code) ? ' <a class="tc-code" href="#stock/' + esc(co.code) + '">' + esc(co.code) + '</a>' : '') + (co.heat ? '<small class="tc-heat">' + esc(co.heat) + '</small>' : '') + '</h4>' + topHtml(co) + '</div>' +
          '<div class="tc-two">' + payHtml(co) + calHtml(co) + '</div>' + chipsHtml(co) +
          bonusBlock(co) +
          (co.grade_system ? '<div class="tc-gs"><b>職等制度</b><span class="tc-chips">' + chipsOf(co.grade_system, 3, 14).map((x) => '<em class="tc-chip">' + esc(x) + '</em>').join('') + '</span>' + qpop(esc(co.grade_system)) + '</div>' : '') +
          (tsmc ? '<div class="tc-gs tc-tsmcnote">台積電不分學歷，薪資差異主要來自單位繁忙度</div>' : '') +
          '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + m.length + '</b> / ' + (co.roles || []).length + ' 個職位</div>' +
          (m.length ? rolesTable(m, co.bonus_timing, tsmc) : '<div class="empty isempty tc-empty">沒有符合篩選的職位</div>');
      } else {
        const list = d.companies.map((c) => [c, (c.roles || []).filter(roleOk)]).filter((x) => x[1].length);
        h += '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + list.length + '</b> / ' + d.companies.length + ' 家公司</div>' +
          (list.length ? '<div class="tc-grid">' + list.map((x) => coCard(S.ind, x[0], x[1])).join('') + '</div>' : '<div class="empty isempty tc-empty">沒有符合篩選的公司</div>');
      }
    }
    h += '</div></div><div class="tc-foot">' + esc(FOOT) + '</div>';
    root.innerHTML = h;
    bindHow(root);
    $$('.tc-smt td.tc-clip', root).forEach((td) => td.onclick = () => td.classList.toggle('open'));
    $$('.tc-qp > .tc-q', root).forEach((b) => b.onclick = (e) => { e.stopPropagation(); const p = b.nextElementSibling, open = p.hidden; $$('.tc-qp > .tc-pop', root).forEach((x) => { x.hidden = true; }); p.hidden = !open; b.setAttribute('aria-expanded', String(open)); });
    if (!window.__tcQpDoc) { window.__tcQpDoc = true; document.addEventListener('click', (e) => { if (!e.target.closest('.tc-qp')) $$('.tc-qp > .tc-pop').forEach((x) => { x.hidden = true; }); }); }
    $$('.tc-tbl td', root).forEach((td) => { if (td.textContent.trim() === '—') td.classList.add('tc-dash'); });
    if (S.ind === 'stats') { drawStats(); bindRank(root); }
    else if (S.co && S.data[S.ind]) { const co2 = (S.data[S.ind].companies || []).find((x) => x.name === S.co); if (co2) { drawPay(co2); const sel = $('#tcPaySel', root); if (sel) sel.onchange = () => { S.payI = +sel.value; drawPay(co2); }; } }
    $$('.tc-fbar .seg', root).forEach((sg) => $$('button', sg).forEach((b) => b.onclick = () => { S.f[sg.dataset.fk] = +b.dataset.i; paint(); }));
    /* 手機：職位列超過 10 列先收起，按「看全部」才展開（整頁 ≤4 屏準則）；桌機不動 */
    const tw = $('.tc-tw', root);
    if (tw && mob() && !S.rowsAll) {
      const trs = $$('tbody > tr', tw); let n = 0, cut = -1;
      trs.forEach((tr, i) => { if (tr.classList.contains('tc-row')) { n++; if (n === 11 && cut < 0) cut = i; } });
      if (cut >= 0) {
        trs.slice(cut).forEach((tr) => tr.classList.add('tc-hmore'));
        const all = trs.filter((t) => t.classList.contains('tc-row')).length;
        const bt = document.createElement('button'); bt.type = 'button'; bt.className = 'tc-rkmore tc-rowmore'; bt.textContent = '看全部 ' + all + ' 個職位';
        bt.onclick = () => { S.rowsAll = true; $$('.tc-hmore', tw).forEach((t) => t.classList.remove('tc-hmore')); bt.remove(); };
        tw.parentNode.insertBefore(bt, tw.nextSibling);
      }
    }
    const cl = $('.tc-clear', root); if (cl) cl.onclick = () => { S.f = {}; paint(); };
    const tg = $('.tc-ftog', root); if (tg) tg.onclick = () => { S.fopen = !S.fopen; paint(); };
    /* 點整列任何地方（連結／按鈕除外）展開／收合逐筆樣本；手機同時切「顯示更多欄位」；鍵盤 Enter／空白鍵也可 */
    const togRow = (tr) => {
      if (mob()) tr.classList.toggle('mo');
      const sm = tr.nextElementSibling; if (!sm || !sm.classList.contains('tc-smrow')) return;
      const o = sm.hidden; sm.hidden = !o; tr.classList.toggle('tc-open', o); tr.setAttribute('aria-expanded', String(o));
      const b = $('.tc-exp', tr); if (b) { b.textContent = o ? '▾' : '▸'; b.setAttribute('aria-expanded', String(o)); }
    };
    $$('.tc-row', root).forEach((tr) => {
      tr.tabIndex = 0; tr.setAttribute('role', 'button'); tr.setAttribute('aria-expanded', 'false');
      tr.addEventListener('click', (e) => { if (e.target.closest('a') || (e.target.closest('button') && !e.target.closest('.tc-exp'))) return; togRow(tr); });
      tr.addEventListener('keydown', (e) => { if (e.target !== tr) return; if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); togRow(tr); } });
    });
    $$('th.srt', root).forEach((th) => th.onclick = () => { const k = th.dataset.sk; S.sort = S.sort.k === k ? { k, d: -S.sort.d } : { k, d: -1 }; paint(); });
  }

  async function show(head, rest) {
    const root = $('#v-tc'); if (!root) return;
    if (!gate()) { if (!known) { const v = document.getElementById('v-tc'); if (v) v.innerHTML = '<div class="empty">確認登入身分中…</div>'; } return; }   // 非管理者：gate() 已導回總覽；身分還沒確定先顯示確認中
    const ids = INDS.map((x) => x[0]);
    const ind = rest[0] === 'stats' ? 'stats' : ids.includes(rest[0]) ? rest[0] : ids[0];
    const co = rest[1] ? decodeURIComponent(rest[1]) : '';
    if (ind !== S.ind || co !== S.co) { S.rowsAll = false; S.payI = null; }
    if (ind !== S.ind) { S.f = {}; S.sort = { k: '', d: -1 }; S.fopen = false; }   // 換產業回 Default（Andy 規矩 C7）
    S.ind = ind; S.co = co;
    await loadAll();
    paint();
  }

  window.TwTc = { show, state: () => S, INDS };
})();
