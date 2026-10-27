/* ============================================================================
   自選日報＋自設提醒（2026-10-27，Andy 拍板 T-4；規格 docs/marketing/tier_plan_1027.md W7、法遵 L-13）
   ----------------------------------------------------------------------------
   回答的問題：「我自選的股票今天發生了什麼事？」「我設的條件有沒有成立？」
   · 資料：data/digest.json（盤後 build_payload 產出，pipeline/compute/digest.py）＝全市場事實表。
     自選清單與提醒條件都留在使用者這邊（清單在 TwWatch、條件在 Worker /v1/alerts/*），日報與提醒在瀏覽器裡組，
     所以不需要寄信、不需要 Worker 碰資料湖。
   · ★ 欄位白名單（法遵 L-13）：只列收盤價與成交量、三大法人買賣超、最新月營收、公告事件（除息／法說會／財報公布）。
     沒有評分、排名、技術燈號、AI 分析、進出場時機或買賣建議；提醒條件一律使用者自己設，站方不提供預設條件。
     文案也不暗示時機：條件成立只寫「你設定的條件成立：…」。
   · 通知出口＝既有的通知鈴鐺（notices.js 的 L() 會併入 TwDigest.notes()）。這些通知存在本機（localStorage），
     已讀也只記本機，不經 Worker。
   · 權限：watch.digest（日報，Pro）、watch.alert（提醒條數：註冊會員 1、Plus 5、Pro 不限）。條數上限伺服器那關也守。
   · 提醒觸發＝邊緣觸發：條件由不成立變成立才響一次（價格／連買連賣）；除息每個除息日響一次；營收每公布新的一期響一次。
     新建的條件若當下已成立，下一次載入資料時響一次（讓人知道有效）；營收新建時先記下現有那一期，不補響。
   驗收：scripts/uitest_sections/20261027_digest.py
   ========================================================================== */
(function () {
  'use strict';
  const T = () => window.TwSub;
  if (!T()) return;
  const { esc, css, call, ls } = T();
  const A = () => window.TwAccount;
  const K = () => { const a = A(), u = a && a.on && a.on() && a.user && a.user(); return u && u.email ? 'tw.digest.v1.' + String(u.email).toLowerCase() : ''; };
  const S = { d: null, rules: null, rev: 0, cap: null, view: 'digest', msg: '', form: { type: 'above' }, busy: false };
  const num = (v, d) => (v == null || !isFinite(v) ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: d || 0 }));
  const sgn = (v, d) => (v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + num(v, d));
  const md = (iso) => String(iso || '').slice(5).replace('-', '/');
  const P = () => window.TwPerm;
  const can = (id) => { const p = P(); return !!(p && p.can(id)); };
  const capNow = () => { const p = P(); const c = p ? p.limit('watch.alert', 1) : 1; return Number.isInteger(c) ? c : (S.cap == null ? 1 : S.cap); };

  // ------------------------------------------------------------------ 本機狀態（通知＋每條提醒的觸發紀錄）
  function load() { const k = K(); if (!k) return { notes: [], st: {}, last: '' }; try { const j = JSON.parse(ls.get(k) || 'null'); if (j && typeof j === 'object') return { notes: j.notes || [], st: j.st || {}, last: j.last || '' }; } catch (e) { /* 壞資料當沒有 */ } return { notes: [], st: {}, last: '' }; }
  function save(m) { const k = K(); if (k) ls.set(k, JSON.stringify({ notes: m.notes.slice(0, 40), st: m.st, last: m.last })); }
  const notes = () => { if (!K()) return []; const cut = Date.now() - 30 * 86400e3; return load().notes.filter((n) => n.start > cut); };

  // ------------------------------------------------------------------ 事實 → 文字（只寫事實）
  const nameOf = (c) => { const s = S.d && S.d.s[c]; return s ? s.n : c; };
  function factLine(c, s) {
    const p = [`${c} ${s.n}　收盤 ${num(s.c, 2)}`];
    if (s.pc) p[0] += `（${sgn((s.c / s.pc - 1) * 100, 2)}%）`;
    p.push(`成交 ${num(s.v)} 張`);
    if (s.i) p.push(`外資 ${sgn(s.i[0])}／投信 ${sgn(s.i[1])}／三大法人 ${sgn(s.i[3])} 張`);
    if (s.r) p.push(`${s.r.ym} 月營收 ${num(s.r.rev, 1)} 億元${s.r.yoy != null ? `（年增 ${sgn(s.r.yoy, 1)}%` + (s.r.mom != null ? `、月增 ${sgn(s.r.mom, 1)}%）` : '）') : ''}${s.r.ann ? `，${md(s.r.ann)} 公布` : ''}`);
    if (s.x) p.push(`除息日 ${md(s.x.d)}${s.x.a != null ? `（現金股利 ${num(s.x.a, 2)} 元）` : ''}`);
    (s.e || []).forEach((e) => p.push(`${e[0]} ${md(e[1])}`));
    return p.join('　');
  }
  function ruleText(r) {
    if (r.type === 'rev') return '月營收公布時';
    if (r.type === 'streak') return `${{ total: '三大法人合計', foreign: '外資', trust: '投信' }[r.who]}連續${r.side === 'buy' ? '買超' : '賣超'} ${r.n} 天以上`;
    if (r.type === 'above') return `收盤價高於 ${num(r.x, 2)} 元`;
    if (r.type === 'below') return `收盤價低於 ${num(r.x, 2)} 元`;
    return `距離除息日 ${r.n} 天內`;
  }
  const dayStart = (iso) => { const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(iso || ''); return m ? Date.UTC(+m[1], m[2] - 1, +m[3]) - 8 * 3600e3 : Date.now(); };
  const daysTo = (a, b) => Math.round((dayStart(b) - dayStart(a)) / 86400e3);

  /* 一條提醒對一檔的判斷：回 {met, key, text}；met 不成立 text 為空。key 用來避免同一件事響兩次（營收的期別、除息日）*/
  function evalRule(r, s) {
    if (!s) return { met: false };
    if (r.type === 'rev') return s.r ? { met: true, key: s.r.ym, text: `${s.n}（${r.code}）公布 ${s.r.ym} 月營收 ${num(s.r.rev, 1)} 億元${s.r.yoy != null ? `，年增 ${sgn(s.r.yoy, 1)}%` : ''}${s.r.mom != null ? `、月增 ${sgn(s.r.mom, 1)}%` : ''}` } : { met: false };
    if (r.type === 'above' || r.type === 'below') {
      const hit = r.type === 'above' ? s.c > r.x : s.c < r.x;
      return { met: hit, text: `${s.n}（${r.code}）收盤價 ${num(s.c, 2)} 元，${r.type === 'above' ? '高於' : '低於'}你設定的 ${num(r.x, 2)} 元` };
    }
    if (r.type === 'streak') {
      if (!s.k) return { met: false };
      const k = s.k[{ foreign: 0, trust: 1, total: 2 }[r.who]], hit = r.side === 'buy' ? k >= r.n : k <= -r.n;
      const lot = s.i ? s.i[{ foreign: 0, trust: 1, total: 3 }[r.who]] : null;
      return { met: hit, text: `${s.n}（${r.code}）${{ total: '三大法人合計', foreign: '外資', trust: '投信' }[r.who]}已連續${r.side === 'buy' ? '買超' : '賣超'} ${Math.abs(k)} 天（最近一日 ${sgn(lot)} 張）` };
    }
    if (r.type === 'exdiv' && s.x) {
      const dd = daysTo(S.d.asof, s.x.d);
      return { met: dd >= 0 && dd <= r.n, key: s.x.d, text: `${s.n}（${r.code}）除息日 ${md(s.x.d)}，還有 ${dd} 天${s.x.a != null ? `（現金股利 ${num(s.x.a, 2)} 元）` : ''}` };
    }
    return { met: false };
  }

  /* 載入資料與條件後跑一次：組日報通知、判斷每條提醒。同一個資料日只做一次（lastDigest／每條 st.asof）*/
  function run() {
    if (!S.d || !K()) return;
    const m = load(), asof = S.d.asof, ymd = asof.replace(/-/g, '');
    let changed = false;
    const push = (n) => { if (!m.notes.some((x) => x.id === n.id)) { m.notes.unshift(n); changed = true; } };
    // 1) 日報（Pro）：自選清單全部頁籤的股票，一天一則
    const W = window.TwWatch;
    if (can('watch.digest') && W && m.last !== asof) {
      const codes = [...new Set(W.tabs().flatMap((t) => t.codes))].filter((c) => S.d.s[c]);
      if (codes.length) {
        const lines = codes.slice(0, 30).map((c) => factLine(c, S.d.s[c]));
        const more = codes.length > 30 ? `\n…另外 ${codes.length - 30} 檔請到自選頁看` : '';
        push({ id: `d-${ymd}-digest`, kind: 'digest', title: `自選日報 ${md(asof)}：${codes.length} 檔自選`, aud: 'member', start: dayStart(asof) + 18 * 3600e3, end: 0, pinned: false, stat: true,
          body: lines.join('\n') + more + '\n公開資料整理，非投資建議。\n[看完整日報](#watch)' });
      }
      m.last = asof; changed = true;
    }
    // 2) 提醒
    (S.rules || []).filter((r) => r.on !== false).forEach((r) => {
      const st = m.st[r.id] || (m.st[r.id] = {});
      if (st.asof === asof) return;
      const e = evalRule(r, S.d.s[r.code]);
      if (r.type === 'rev') {
        if (st.key === undefined) st.key = e.key || '';                 // 新建：記下現有那一期，不補響
        else if (e.met && e.key !== st.key) { st.key = e.key; push(mkAlert(r, ymd, e.text, asof)); }
      } else if (r.type === 'exdiv') {
        if (e.met && e.key !== st.key) { st.key = e.key; push(mkAlert(r, ymd, e.text, asof)); }
      } else if (e.met && !st.met) push(mkAlert(r, ymd, e.text, asof));
      st.met = !!e.met; st.asof = asof; changed = true;
    });
    // 已刪的條件的紀錄順手清掉
    const live = new Set((S.rules || []).map((r) => r.id)); Object.keys(m.st).forEach((id) => { if (!live.has(id)) { delete m.st[id]; changed = true; } });
    if (changed) { save(m); window.dispatchEvent(new Event('tw:digest')); }
  }
  const mkAlert = (r, ymd, text, asof) => ({ id: `d-${ymd}-${r.id}`, kind: 'alert', title: `提醒：${nameOf(r.code)} ${ruleText(r)}`, body: `你設定的條件成立：${text}\n條件由你自設，成立不代表買賣時機；公開資料整理，非投資建議。\n[到自選頁](#watch)`, aud: 'member', start: dayStart(asof) + 18 * 3600e3, end: 0, pinned: false, stat: true });

  // ------------------------------------------------------------------ 取資料
  let dFly = null;
  function loadDigest() {
    if (S.d) return Promise.resolve(S.d);
    if (dFly) return dFly;
    dFly = fetch('data/digest.json', { cache: 'no-cache' }).then((r) => (r.ok ? r.json() : null)).catch(() => null).then((j) => { dFly = null; if (j && j.s && j.asof) S.d = j; return S.d; });
    return dFly;
  }
  function loadRules() {
    const a = A(); if (!a || !a.on() || !a.user()) { S.rules = null; return Promise.resolve(); }
    return call('/v1/alerts/get', {}).then((j) => { if (j && j._s === 200) { S.rules = j.alerts || []; S.rev = j.rev || 0; S.cap = j.cap; } });
  }
  function boot() {
    const a = A(); if (!a || !a.on() || !a.user()) return;
    Promise.all([loadDigest(), loadRules()]).then(() => { run(); repaint(); });
  }
  async function saveRules(next, okMsg) {
    S.busy = true;
    const j = await call('/v1/alerts/put', { alerts: next, rev: S.rev });
    S.busy = false;
    if (j && j._s === 200) { S.rules = j.alerts; S.rev = j.rev; S.cap = j.cap; S.msg = okMsg || ''; run(); }
    else if (j && j._s === 403 && j.error === 'alert_limit') { S.rules = j.alerts; S.rev = j.rev; S.cap = j.limit; S.msg = `目前方案最多 ${j.limit} 條提醒`; }
    else if (j && j._s === 409) { S.rules = j.alerts; S.rev = j.rev; S.msg = '另一台裝置剛改過，已更新，請再操作一次'; }
    else S.msg = '儲存失敗，稍後再試';
    repaint();
    // 成功提示只閃一下就收掉：原本「已刪除」一直留在清單標題的位置，390 寬時看起來像下面那條仍啟用的提醒被刪了
    if (okMsg && S.msg === okMsg) { const m = okMsg; clearTimeout(saveRules._t); saveRules._t = setTimeout(() => { if (S.msg === m) { S.msg = ''; repaint(); } }, 2500); }
  }

  // ------------------------------------------------------------------ 畫面（掛在自選頁 #v-watch 底下）
  css('digestCss', `
#wdCard{margin-top:12px}
#wdCard .wphd{margin-bottom:8px}
#wdCard .wdseg{margin:0 0 8px}
#wdCard .wdscroll{overflow:auto;max-height:340px;border:1px solid var(--line);border-radius:9px;-webkit-overflow-scrolling:touch}
#wdCard table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:760px}
#wdCard th{position:sticky;top:0;background:var(--panel-2);color:var(--ink-2);font-weight:600;text-align:right;padding:6px 8px;white-space:nowrap;z-index:1}
#wdCard td{padding:6px 8px;border-top:1px solid var(--line);text-align:right;white-space:nowrap}
#wdCard th:first-child,#wdCard td:first-child{text-align:left;position:sticky;left:0;background:var(--panel);z-index:1}
#wdCard th:first-child{background:var(--panel-2);z-index:2}
#wdCard td:first-child small{color:var(--ink-3);margin-left:6px}
#wdCard td.up{color:var(--rise)}
#wdCard td.down{color:var(--fall)}   /* 台股慣例：紅漲綠跌（買超紅、賣超綠）*/
#wdCard td.ev{text-align:left;white-space:normal;min-width:130px}
#wdCard .wdlock{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px;border:1px dashed var(--line-2);border-radius:9px;color:var(--ink-2);font-size:14px}
#wdCard .wdlock a{color:var(--cyan)}
#wdCard .wdform{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:2px 0 8px}
#wdCard .wdform select,#wdCard .wdform input{height:34px;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px;font:inherit;font-size:14px}
#wdCard .wdform input{width:92px}
#wdCard .wdform button{height:34px;padding:0 14px;border-radius:8px;border:1px solid transparent;background:var(--cyan);color:var(--ontop);font-weight:700;font-size:14px;cursor:pointer}
#wdCard .wdform button:disabled{opacity:.45;cursor:not-allowed}
#wdCard .wdmsg{font-size:13px;color:var(--ink-2);min-height:18px}
#wdCard .wdrule{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:14px}
#wdCard .wdrule .tx{flex:1;min-width:0;overflow-wrap:anywhere}
#wdCard .wdrule label{display:inline-flex;align-items:center;gap:4px;font-size:13px;color:var(--ink-2);white-space:nowrap}
#wdCard .wdrule .del{border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink-2);border-radius:8px;width:32px;height:32px;cursor:pointer}
@media (max-width:640px){#wdCard .wdform input{width:84px}#wdCard .wdform select{max-width:46vw}#wdCard .wdscroll{max-height:300px}}`);

  const HOWTXT = `<b class="howq">自選日報整理你自選股票今天的公開資料；提醒只在你自己設的條件成立時通知。</b><ul>
    <li>日報只列事實：收盤價與成交量、三大法人買賣超、最新月營收、公告的除息與法說日期</li>
    <li>資料每個交易日盤後更新一次，不是盤中即時</li>
    <li>提醒條件由你自己設定，成立時通知鈴鐺響一次</li>
    <li>本功能為公開資料整理，不構成投資建議或買賣推介；提醒成立只代表你設的條件發生，不代表買進或賣出時機，投資盈虧自行負責</li>
    <li>日報為 Pro 功能；提醒條數：註冊會員 1 條、Plus 5 條、Pro 不限</li></ul>`;

  function digestHTML() {
    if (!can('watch.digest')) return `<div class="wdlock"><span>自選日報為 Pro 方案功能（每天盤後整理自選股票的公開資料）</span><a href="#pricing">看方案</a></div>`;
    const W = window.TwWatch, d = S.d;
    if (!d) return '<div class="wdlock"><span>日報資料載入中…</span></div>';
    const t = W.curTab(), rows = t.codes.filter((c) => d.s[c]);
    if (!t.codes.length) return `<div class="wdlock"><span>「${esc(t.name)}」還沒有股票</span></div>`;
    const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');   // 紅漲綠跌的 class（.up／.down），不依賴 App.fmt
    const body = rows.map((c) => {
      const s = d.s[c], chg = s.pc ? (s.c / s.pc - 1) * 100 : null;
      const evs = [s.x ? `除息 ${md(s.x.d)}` : '', ...(s.e || []).map((e) => `${e[0]} ${md(e[1])}`)].filter(Boolean).join('、') || '—';
      const ic = (v) => `<td class="num ${cls(v)}">${sgn(v)}</td>`;
      return `<tr data-wd="${esc(c)}"><td><b>${esc(s.n)}</b><small class="num">${esc(c)}</small></td><td class="num">${num(s.c, 2)}</td><td class="num ${cls(chg)}">${chg == null ? '—' : sgn(chg, 2) + '%'}</td><td class="num">${num(s.v)}</td>`
        + (s.i ? ic(s.i[0]) + ic(s.i[1]) + ic(s.i[3]) : '<td>—</td><td>—</td><td>—</td>')
        + `<td class="num">${s.r ? `${esc(s.r.ym)}　${num(s.r.rev, 1)} 億${s.r.yoy != null ? `（${sgn(s.r.yoy, 1)}%）` : ''}` : '—'}</td><td class="ev">${esc(evs)}</td></tr>`;
    }).join('');
    const miss = t.codes.length - rows.length;
    return `<div class="wdscroll"><table id="wdTbl"><thead><tr><th>股票</th><th>收盤</th><th>漲跌幅</th><th>成交量(張)</th><th>外資(張)</th><th>投信(張)</th><th>三大法人(張)</th><th>最新月營收（年增）</th><th>公告事件</th></tr></thead><tbody>${body}</tbody></table></div>`
      + (miss ? `<div class="wdmsg">另有 ${miss} 檔當日沒有行情資料</div>` : '');
  }

  function formHTML() {
    const W = window.TwWatch, codes = W.curTab().codes, f = S.form;
    const opts = codes.map((c) => `<option value="${esc(c)}"${f.code === c ? ' selected' : ''}>${esc(c)} ${esc(nameOf(c))}</option>`).join('');
    const ty = [['above', '收盤價高於'], ['below', '收盤價低於'], ['streak', '法人連買／連賣'], ['rev', '月營收公布'], ['exdiv', '除息前 N 天']];
    const sel = (id, list, cur) => `<select id="${id}" aria-label="${id}">${list.map(([v, l]) => `<option value="${v}"${cur === v ? ' selected' : ''}>${l}</option>`).join('')}</select>`;
    let ex = '';
    if (f.type === 'above' || f.type === 'below') ex = `<input id="wdX" type="number" inputmode="decimal" min="0" step="0.01" placeholder="價格" value="${esc(f.x || '')}" aria-label="價格">`;
    if (f.type === 'streak') ex = sel('wdWho', [['total', '三大法人合計'], ['foreign', '外資'], ['trust', '投信']], f.who || 'total') + sel('wdSide', [['buy', '買超'], ['sell', '賣超']], f.side || 'buy')
      + `<input id="wdN" type="number" inputmode="numeric" min="2" max="30" placeholder="連續天數" value="${esc(f.n || '')}" aria-label="連續天數">`;
    if (f.type === 'exdiv') ex = `<input id="wdN" type="number" inputmode="numeric" min="1" max="30" placeholder="天數" value="${esc(f.n || '')}" aria-label="天數">`;
    const full = (S.rules || []).length >= capNow();
    return `<div class="wdform"><select id="wdCode" aria-label="股票">${opts}</select>${sel('wdType', ty, f.type)}${ex}<button type="button" id="wdAdd"${full || !codes.length ? ' disabled' : ''}>加入提醒</button></div>`;
  }
  function rulesHTML() {
    const W = window.TwWatch;
    if (S.rules == null) return '<div class="wdmsg">載入中…</div>';
    const full = S.rules.length >= capNow();
    const list = S.rules.map((r) => `<div class="wdrule" data-rid="${esc(r.id)}"><span class="tx">${esc(r.code)} ${esc(nameOf(r.code))}：${esc(ruleText(r))}</span>
      <label><input type="checkbox" data-wdon="${esc(r.id)}"${r.on !== false ? ' checked' : ''}>啟用</label><button type="button" class="del" data-wddel="${esc(r.id)}" aria-label="刪除這條提醒">✕</button></div>`).join('');
    return (W.curTab().codes.length ? formHTML() : '<div class="wdmsg">先把股票加進這一頁自選，才能設提醒</div>')
      + `<div class="wdmsg" id="wdMsg">${esc(S.msg || (full ? `已達目前方案的 ${capNow()} 條上限，升級可設更多` : ''))}${full ? ' <a href="#pricing">看方案</a>' : ''}</div>` + list;
  }
  function paint() {
    const el = document.getElementById('wdCard'); if (!el) return;
    const n = (S.rules || []).length, cap = capNow();
    el.innerHTML = `<div class="wphd"><h2>自選日報與提醒 <button class="howbtn pop" data-how="wdg" data-ttl="自選日報與提醒" type="button" aria-label="自選日報與提醒怎麼看">?</button></h2>${S.d ? `<span class="wpmode">資料日 ${md(S.d.asof)}</span>` : ''}</div>
      <div class="seg wdseg" role="tablist"><button type="button" role="tab" data-wdv="digest" class="${S.view === 'digest' ? 'on' : ''}" aria-selected="${S.view === 'digest'}">今日日報</button><button type="button" role="tab" data-wdv="rules" class="${S.view === 'rules' ? 'on' : ''}" aria-selected="${S.view === 'rules'}">我的提醒 ${n}／${cap >= 200 ? '不限' : cap}</button></div>
      <div id="wdBody">${S.view === 'digest' ? digestHTML() : rulesHTML()}</div><div class="howtxt" id="how-wdg" hidden>${HOWTXT}</div>`;
  }
  const repaint = () => { if (document.getElementById('wdCard')) paint(); };

  function onClick(e) {
    const v = e.target.closest('[data-wdv]');
    if (v) { S.view = v.dataset.wdv; S.msg = ''; paint(); return; }
    const del = e.target.closest('[data-wddel]');
    if (del) { saveRules(S.rules.filter((r) => r.id !== del.dataset.wddel), '已刪除該條提醒'); return; }
    if (e.target.closest('#wdAdd')) addRule();
  }
  function addRule() {
    const g = (id) => { const x = document.getElementById(id); return x ? x.value : ''; };
    const f = S.form = { type: g('wdType'), code: g('wdCode'), who: g('wdWho') || undefined, side: g('wdSide') || undefined, x: g('wdX'), n: g('wdN') };
    const r = { id: Math.random().toString(36).slice(2, 10), code: f.code, type: f.type, on: true };
    if (f.type === 'above' || f.type === 'below') { r.x = parseFloat(f.x); if (!(r.x > 0)) { S.msg = '請填價格（大於 0）'; paint(); return; } }
    if (f.type === 'streak') { r.n = parseInt(f.n, 10); r.who = f.who || 'total'; r.side = f.side || 'buy'; if (!(r.n >= 2 && r.n <= 30)) { S.msg = '連續天數請填 2～30'; paint(); return; } }
    if (f.type === 'exdiv') { r.n = parseInt(f.n, 10); if (!(r.n >= 1 && r.n <= 30)) { S.msg = '天數請填 1～30'; paint(); return; } }
    if (!r.code) { S.msg = '請先選股票'; paint(); return; }
    S.form = { type: f.type, code: f.code, who: f.who, side: f.side };
    saveRules((S.rules || []).concat([r]), '已加入提醒');
  }
  function onChange(e) {
    const t = e.target;
    if (t.id === 'wdType') { S.form = { type: t.value, code: (document.getElementById('wdCode') || {}).value }; paint(); return; }
    if (t.dataset && t.dataset.wdon) saveRules(S.rules.map((r) => (r.id === t.dataset.wdon ? { ...r, on: t.checked } : r)), '');
  }
  function mount(host) {
    const a = A(); if (!host || !a || !a.on() || !a.user()) return;
    let el = document.getElementById('wdCard');
    if (!el) { el = document.createElement('div'); el.id = 'wdCard'; el.className = 'card'; host.appendChild(el); el.addEventListener('click', onClick); el.addEventListener('change', onChange); }
    else if (el.parentNode !== host) host.appendChild(el);
    paint();
    if (!S.d || S.rules == null) boot();
  }

  window.addEventListener('tw:account', () => { S.rules = null; S.msg = ''; boot(); });
  window.addEventListener('tw:watch', () => { run(); repaint(); });
  window.addEventListener('tw:perm', () => { run(); repaint(); });
  window.TwDigest = { notes, mount, run, rules: () => (S.rules || []).slice(), data: () => S.d, ruleText, factLine };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
