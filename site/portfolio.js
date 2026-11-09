/* ============================================================================
   我的持股曝險（#portfolio）—— 2026-11-09，提案 P-1107-03（Andy 同日點頭：「02 05 03 04 06」）。
   一句話：你輸入的持股，集中在本站哪幾個族群，而那些族群的錢現在往哪走。

   · ★ 隱私（CLAUDE.md：repo 是 public，持股不准進 repo、不碰成本價）：
       持股只存在這台裝置的 localStorage（鍵 tw.portfolio），不送後端、不進任何請求、不跟會員帳號同步。
       只存「代號＋股數或金額」，不存成本價、不算損益。畫面明寫「資料只存在這台裝置」。
       所有讀寫包 try/catch（私密視窗會丟例外）；讀不到就當作空清單。
   · 計算：每檔只算進 stocks.json 的主要族群（group_id）；市值＝股數 × 最新收盤，或使用者直接填的金額；
       族群比重＝該族群各檔市值加總 ÷ 全部持股市值。
   · 資金欄位全用站上現成資料（flow_v3.json 的 share_daily／money_rrg），不另外抓：
       5 日占比／20 日占比＝該族群成交值占全市場比重的近 5／20 日平均；變化＝兩者相差幾個百分點；
       輪動狀態＝資金流向頁同一套（集中／升溫／退燒／冷落）。只陳述事實，不寫買賣建議。
   · 圖：A 款甜甜圈（App.donut，前 5 大＋其他），點扇區或點表格列＝在原地展開該族群的持股（不跳頁），名稱再點進個股頁。
   · 方案閘門：portfolio.exposure（整頁每日次數，quota.js 依 features.js 的 route／veil 自動蓋）、
       portfolio.size（持股檔數上限）、portfolio.import（匯入 CSV，Plus 以上）。
   驗收：scripts/uitest_sections/20261109_我的持股曝險.py。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const isM = () => window.matchMedia('(max-width: 640px)').matches;
  const KEY = 'tw.portfolio';
  const HARD = 100;               // 硬上限（features.js 的 max）：再多也只會拖慢畫面
  const DEF_SHARES = 1000;        // 從自選帶入時預設每檔 1 張，使用者再改成實際股數
  const QUAD = { leading: ['集中', 'rise'], improving: ['升溫', 'cyan'], weakening: ['退燒', 'amber'], lagging: ['冷落', 'fall'] };
  const S = { rows: [], mode: 'sh', sel: null, msg: '', all: false, clearArm: false };
  let stocks = [], byCode = new Map(), flow = new Map(), timer = null;

  /* ------------------------------------------------------------------ 儲存（只在這台裝置）*/
  function readRows() {
    try {
      const o = JSON.parse(localStorage.getItem(KEY) || 'null');
      const r = o && Array.isArray(o.rows) ? o.rows : [];
      const seen = new Set();
      return r.filter((x) => x && typeof x.c === 'string' && /^[0-9A-Za-z]{2,8}$/.test(x.c) && (x.m === 'sh' || x.m === 'amt') && Number.isFinite(+x.v) && +x.v > 0 && !seen.has(x.c) && seen.add(x.c))
        .slice(0, HARD).map((x) => ({ c: x.c.toUpperCase(), m: x.m, v: +x.v }));
    } catch (e) { return []; }
  }
  function saveRows() { try { localStorage.setItem(KEY, JSON.stringify({ v: 1, rows: S.rows })); } catch (e) { /* 私密視窗：這次開著仍可用，關掉就沒了 */ } }

  /* ------------------------------------------------------------------ 方案上限 */
  const permOn = () => { if (window.TW_PREVIEW) return true; const P = window.TwPerm; return !!P && P.state().src !== 'default'; };
  function cap() {
    const P = window.TwPerm;
    if (window.TW_PREVIEW) return HARD;
    if (!permOn()) return 10;     // 連不到會員伺服器：寧可多給，用註冊會員的 10 檔
    return Math.max(0, Math.min(HARD, P.limit('portfolio.size', 10)));
  }

  /* ------------------------------------------------------------------ 資料 */
  function buildFlow(f) {
    const m = new Map();
    const sd = f && f.share_daily;
    if (!sd || !Array.isArray(sd.groups)) return m;
    const quad = new Map((((f.money_rrg || {}).points) || []).map((p) => [p.group_id, p.quadrant]));
    const avg = (a, k) => { const x = a.slice(-k).filter((v) => v != null); return x.length === k ? x.reduce((s, v) => s + v, 0) / k : null; };
    const comp = (a, k) => { const x = a.slice(-k); return x.length === k ? (x.reduce((p, v) => p * (1 + (v || 0) / 100), 1) - 1) * 100 : null; };
    sd.groups.forEach((g) => {
      const sh = g.share || [], ch = g.chg || [];
      const s5 = avg(sh, 5), s20 = avg(sh, 20);
      m.set(g.group_id, { name: g.group_name, s5, s20, d: s5 != null && s20 != null ? s5 - s20 : null, chg1: ch.length ? ch[ch.length - 1] : null, chg5: comp(ch, 5), quad: quad.get(g.group_id) || null });
    });
    return m;
  }
  async function loadData() {
    const a = A();
    const [st, f] = await Promise.all([a.load('stocks', { fallback: [] }), a.load('flow_v3', { fallback: null })]);
    stocks = (st || []).filter((r) => r && r.code);
    byCode = new Map(stocks.map((r) => [r.code.toUpperCase(), r]));
    flow = buildFlow(f);
  }

  /* 持股 → 各族群曝險。回傳 { items, groups, total } */
  function calc() {
    const items = S.rows.map((r) => {
      const s = byCode.get(r.c) || null;
      const close = s && Number.isFinite(+s.close) ? +s.close : null;
      const val = r.m === 'amt' ? r.v : close != null ? r.v * close : 0;
      return { c: r.c, m: r.m, v: r.v, name: s ? s.name : r.c, gid: s && s.group_id ? s.group_id : '_none', gname: s && s.group ? s.group : '未分類', close, chg: s ? s.chg_pct : null, val, known: !!s };
    });
    const total = items.reduce((t, i) => t + i.val, 0);
    const gm = new Map();
    items.forEach((i) => {
      if (!(i.val > 0)) return;
      let g = gm.get(i.gid);
      if (!g) { const fl = flow.get(i.gid) || null; g = { gid: i.gid, name: i.gname, val: 0, items: [], fl }; gm.set(i.gid, g); }
      g.val += i.val; g.items.push(i);
    });
    const groups = Array.from(gm.values()).sort((a, b) => b.val - a.val);
    groups.forEach((g) => { g.pct = total > 0 ? g.val / total * 100 : 0; g.items.sort((a, b) => b.val - a.val); g.items.forEach((i) => { i.pct = total > 0 ? i.val / total * 100 : 0; }); });
    items.forEach((i) => { if (i.pct == null) i.pct = 0; });
    return { items, groups, total };
  }

  /* ------------------------------------------------------------------ 樣式 */
  function injectCSS() {
    if (document.getElementById('pfCss')) return;
    const s = document.createElement('style'); s.id = 'pfCss';
    s.textContent = `
#v-portfolio .pfwrap{display:grid;grid-template-columns:minmax(300px,380px) minmax(0,1fr);gap:var(--sp-3);align-items:stretch}
#v-portfolio .pfwrap>.card{margin:0;min-width:0}
#v-portfolio .pfpriv{margin-left:auto;font-size:var(--fs-sm,12.5px);color:var(--ink-3);white-space:nowrap}
#v-portfolio .pfform{display:grid;grid-template-columns:auto minmax(0,1fr);gap:var(--sp-2);align-items:center;margin-bottom:var(--sp-2)}
#v-portfolio .pfform input,#v-portfolio .pfrow2 input{height:32px;min-width:0;box-sizing:border-box;border:1px solid var(--line-2);border-radius:var(--r-sm,8px);background:var(--panel-3);color:var(--ink);padding:0 var(--sp-2);font-size:13.5px}
#v-portfolio .pfform input:focus,#v-portfolio .pfrow2 input:focus{outline:2px solid var(--cyan);outline-offset:-1px}
#v-portfolio .pfrow2{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:var(--sp-2);margin-bottom:var(--sp-2)}
#v-portfolio .pfbtns{display:flex;flex-wrap:wrap;gap:var(--sp-2);margin-bottom:var(--sp-2)}
#v-portfolio .pfbtns .btn,#v-portfolio .pfrow2 .btn{height:32px;white-space:nowrap}
#v-portfolio .pfbtns .btn.arm{border-color:var(--amber);color:var(--amber)}
#v-portfolio .pfmsg{min-height:20px;font-size:var(--fs-sm,12.5px);color:var(--ink-2);margin:0 0 var(--sp-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-portfolio .pfmsg.bad{color:var(--amber)}
#v-portfolio .pflist{max-height:320px;overflow:auto;border:1px solid var(--line);border-radius:var(--r-sm,8px)}
#v-portfolio table.pft{width:100%;border-collapse:collapse;font-size:13.5px}
#v-portfolio table.pft th{position:sticky;top:0;background:var(--panel-2);font-size:12px;font-weight:600;color:var(--ink-3);height:32px;text-align:center;z-index:1}
#v-portfolio table.pft td{height:32px;border-top:1px solid var(--line);text-align:center;padding:0 var(--sp-1);white-space:nowrap}
#v-portfolio table.pft td.nm,#v-portfolio table.pft th.nm{text-align:left;padding-left:var(--sp-2);max-width:150px;overflow:hidden;text-overflow:ellipsis}
#v-portfolio table.pft td.num{font-family:var(--mono,monospace)}
#v-portfolio .pflist input.q{width:92px;height:26px;box-sizing:border-box;text-align:right;border:1px solid var(--line-2);border-radius:6px;background:var(--panel-3);color:var(--ink);font:13px var(--mono,monospace);padding:0 6px}
#v-portfolio .pflist .x{border:0;background:transparent;color:var(--ink-3);cursor:pointer;font-size:16px;width:28px;height:28px;border-radius:6px}
#v-portfolio .pflist .x:hover{color:var(--rise);background:var(--panel-3)}
#v-portfolio .pflist a{color:var(--ink);text-decoration:none}#v-portfolio .pflist a:hover{color:var(--cyan)}
#v-portfolio .pflist tr.warn td.nm{color:var(--amber)}
#v-portfolio .pfempty{padding:var(--sp-4);text-align:center;color:var(--ink-3);font-size:13.5px}
#v-portfolio .pftop{display:flex;gap:var(--sp-4);align-items:center;margin-bottom:var(--sp-3)}
#v-portfolio .pfdn{flex:none;width:210px;height:210px}
#v-portfolio .pfside{flex:1;min-width:0;display:flex;flex-direction:column;gap:var(--sp-2)}
#v-portfolio .pflg{list-style:none;margin:0;padding:0;font-size:13.5px}
#v-portfolio .pflg li{display:flex;align-items:center;gap:var(--sp-2);min-height:28px;cursor:pointer;border-radius:6px;padding:0 var(--sp-1)}
#v-portfolio .pflg li:hover,#v-portfolio .pflg li.on{background:var(--panel-3)}
#v-portfolio .pflg i{flex:none;width:10px;height:10px;border-radius:3px}
#v-portfolio .pflg span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-2)}
#v-portfolio .pflg b{margin-left:auto;font-family:var(--mono,monospace);font-weight:600}
#v-portfolio .pffact{font-size:13.5px;line-height:1.55;color:var(--ink-2);margin:0}
#v-portfolio .pffact b{color:var(--ink);font-weight:600}
#v-portfolio .pfgt{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:var(--r-sm,8px)}
#v-portfolio .pfgt tr.g{cursor:pointer}
#v-portfolio .pfgt tr.g:hover td,#v-portfolio .pfgt tr.g.on td{background:var(--panel-3)}
#v-portfolio .pfgt td.nm i.sw{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px}
#v-portfolio .pfgt td.bar{position:relative;min-width:84px}
#v-portfolio .pfgt td.bar i.b{position:absolute;left:0;top:7px;bottom:7px;border-radius:3px;background:var(--cyan);opacity:.22}
#v-portfolio .pfgt td.bar span{position:relative}
#v-portfolio .pfgt tr.det td{background:var(--panel-2);text-align:left;padding:var(--sp-1) var(--sp-3);height:auto;white-space:normal}
#v-portfolio .pfgt .det a{display:inline-flex;gap:6px;align-items:baseline;margin:2px var(--sp-3) 2px 0;color:var(--ink);text-decoration:none;white-space:nowrap}
#v-portfolio .pfgt .det a:hover{color:var(--cyan)}
#v-portfolio .pfgt .det small{color:var(--ink-3)}
#v-portfolio .pfmore{display:none}
#v-portfolio .q-rise{color:var(--rise)}#v-portfolio .q-cyan{color:var(--cyan)}#v-portfolio .q-amber{color:var(--amber)}#v-portfolio .q-fall{color:var(--fall)}
`;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 畫面 */
  const num = (v, d) => A().fmt.n(v, d == null ? 1 : d);
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
  const sgn = (v, d) => (v == null || Number.isNaN(v) ? '—' : A().fmt.pct(v, d == null ? 2 : d));
  function pp(v) { if (v == null) return '—'; const r = Number(v.toFixed(1)); return (r > 0 ? '+' : '') + (r === 0 ? '0.0' : r.toFixed(1)); }

  function skeleton(root) {
    const how = `<div class="howtxt" id="how-pfx" hidden>${A().howHTML('你的持股集中在哪個族群，而那個族群的錢現在往哪走。', [
      '<b>比重</b>＝各檔市值加總到本站族群，除以全部持股市值；市值＝股數 × 最新收盤，或你直接填的金額。',
      '每一檔只算進本站分類的一個主要族群；查不到收盤價的不計入。',
      '<b>5 日占比／20 日占比</b>＝該族群成交值占全市場的近 5／20 日平均；<b>變化</b>＝兩者相差幾個百分點，紅＝占比在升、綠＝在降。',
      '<b>輪動</b>＝資金流向頁同一套狀態：集中、升溫、退燒、冷落。',
      '所以：先看最大那個族群占你幾成，再看它的占比是升是降；點表格那一列會在原地列出是哪幾檔。這裡只整理你輸入的數字與站上資料，不構成投資建議。',
      '你輸入的持股只存在這台裝置的瀏覽器，不上傳、不跟帳號同步；換裝置或清除瀏覽資料就沒有了。不存成本價、不算損益。'])}</div>`;
    root.innerHTML = `
<div class="pfwrap" id="pfWrap">
  <div class="card" id="pfIn">
    <div class="row spread"><h3>持股輸入 <button class="howbtn pop" data-how="pfx" data-ttl="我的持股曝險怎麼看" type="button" aria-label="我的持股曝險怎麼看">?</button></h3><span class="pfpriv" id="pfPriv">資料只存在這台裝置</span></div>
    ${how}
    <div class="pfform"><div class="seg tiny" id="pfMode" role="tablist" aria-label="輸入方式"><button type="button" data-m="sh" class="on">股數</button><button type="button" data-m="amt">金額</button></div>
      <input id="pfCode" type="text" inputmode="text" autocomplete="off" placeholder="代號或名稱，例如 2330" aria-label="代號或名稱"></div>
    <div class="pfrow2"><input id="pfQty" type="text" inputmode="numeric" autocomplete="off" placeholder="股數（1 張＝1000 股）" aria-label="股數或金額"><button class="btn small" id="pfAdd" type="button">加入</button></div>
    <div class="pfbtns"><button class="btn small" id="pfWatch" type="button">從自選帶入</button><button class="btn small" id="pfImp" type="button" title="匯入「代號,股數」每行一筆的 CSV">匯入 CSV</button><button class="btn small" id="pfClear" type="button">清除全部</button>
      <input id="pfFile" type="file" accept=".csv,.txt,text/csv,text/plain" hidden></div>
    <p class="pfmsg" id="pfMsg" role="status" aria-live="polite"></p>
    <div class="pflist" id="pfList"></div>
  </div>
  <div class="card" id="pfOut"></div>
</div>`;
  }

  function msg(t, bad) {
    S.msg = t || ''; const e = $('#pfMsg'); if (!e) return;
    e.textContent = S.msg; e.classList.toggle('bad', !!bad); e.title = S.msg;
  }

  function paintList(R) {
    const box = $('#pfList'); if (!box) return;
    if (!S.rows.length) { box.innerHTML = '<div class="pfempty">尚未輸入持股</div>'; return; }
    const f = A().fmt;
    box.innerHTML = `<table class="pft"><thead><tr><th class="nm">名稱</th><th>${S.rows.some((r) => r.m === 'amt') ? '股數／金額' : '股數'}</th><th>比重</th><th></th></tr></thead><tbody>${R.items.map((i) => `
<tr data-c="${esc(i.c)}"${i.val > 0 ? '' : ' class="warn"'}><td class="nm" title="${esc(i.c + ' ' + i.name)}${i.val > 0 ? '' : '（查不到最新收盤價，未計入比重）'}"><a href="#stock/${esc(i.c)}">${esc(i.name)}</a> <small>${esc(i.c)}</small></td>
<td><input class="q" type="text" inputmode="numeric" value="${f.i(i.v)}" data-c="${esc(i.c)}" aria-label="${esc(i.name)}${i.m === 'amt' ? '金額' : '股數'}" title="${i.m === 'amt' ? '金額（元）' : '股數'}"></td>
<td class="num">${i.val > 0 ? num(i.pct, 1) + '%' : '—'}</td><td><button class="x" type="button" data-x="${esc(i.c)}" aria-label="移除${esc(i.name)}" title="移除">✕</button></td></tr>`).join('')}</tbody></table>`;
  }

  function factLine(R) {
    const g = R.groups; if (!g.length) return '';
    const top = g[0], t3 = g.slice(0, 3).reduce((s, x) => s + x.pct, 0), fl = top.fl;
    let t = `最大族群<b>「${esc(top.name)}」</b>占持股 <b>${num(top.pct, 1)}%</b>`;
    if (g.length > 1) t += `，前三大合計 <b>${num(t3, 1)}%</b>（共 ${g.length} 個族群）`;
    t += '。';
    if (fl && fl.s5 != null && fl.s20 != null) {
      t += `它的成交值占全市場近 5 日平均 ${num(fl.s5, 2)}%、近 20 日平均 ${num(fl.s20, 2)}%（${pp(fl.d)} 個百分點）`;
      if (fl.quad && QUAD[fl.quad]) t += `，輪動狀態「${QUAD[fl.quad][0]}」`;
      t += '。';
    }
    return t;
  }

  function groupTable(R) {
    const f = A().fmt;
    const rows = R.groups.map((g, k) => {
      const fl = g.fl || {}, q = fl.quad && QUAD[fl.quad];
      const on = S.sel === g.gid;
      const head = `<tr class="g${on ? ' on' : ''}${k >= 3 ? ' pfx' : ''}" data-gid="${esc(g.gid)}" tabindex="0" role="button" aria-expanded="${on}" title="點一下展開持股">
<td class="nm"><i class="sw" style="background:${esc(colorOf(R, g))}"></i>${esc(g.name)}</td>
<td class="bar"><i class="b" style="width:${Math.min(100, g.pct).toFixed(1)}%"></i><span class="num" data-pct="${g.pct.toFixed(4)}">${num(g.pct, 1)}%</span></td>
<td class="num ${cls(fl.chg1)}">${sgn(fl.chg1)}</td><td class="num ${cls(fl.chg5)} mx">${sgn(fl.chg5)}</td>
<td class="num mx">${fl.s5 != null ? num(fl.s5, 2) + '%' : '—'}</td><td class="num mx">${fl.s20 != null ? num(fl.s20, 2) + '%' : '—'}</td>
<td class="num ${cls(fl.d)}">${pp(fl.d)}</td><td class="${q ? 'q-' + q[1] : ''}">${q ? q[0] : '—'}</td></tr>`;
      const det = on ? `<tr class="det${k >= 3 ? ' pfx' : ''}"><td colspan="8">${g.items.map((i) => `<a href="#stock/${esc(i.c)}" title="${esc(i.c + ' ' + i.name)}"><span>${esc(i.name)}</span><small>${esc(i.c)}</small><b class="num">${num(i.pct, 1)}%</b><span class="num ${cls(i.chg)}">${sgn(i.chg)}</span></a>`).join('')}</td></tr>` : '';
      return head + det;
    }).join('');
    return `<div class="pfgt${S.all ? ' all' : ''}" id="pfGT"><table class="pft"><thead><tr><th class="nm">族群</th><th>比重</th><th>今日</th><th class="mx">近 5 日</th><th class="mx">5 日占比</th><th class="mx">20 日占比</th><th>變化</th><th>輪動</th></tr></thead><tbody>${rows}</tbody></table></div>
<button class="btn small pfmore" id="pfMore" type="button">${S.all ? '只看前三大' : '看全部 ' + R.groups.length + ' 個族群'}</button>`;
  }

  /* 甜甜圈：前 5 大 + 其他（A 款），回傳 parts 供掛圖 */
  function partsOf(R) {
    const top = R.groups.slice(0, 5).map((g) => ({ name: g.name, value: g.val, gid: g.gid, chg: g.fl ? g.fl.chg1 : null, hint: '點一下展開持股' }));
    const rest = R.groups.slice(5);
    if (rest.length) top.push({ name: '其他', value: rest.reduce((s, g) => s + g.val, 0), isOther: true, gid: '_other', hint: rest.map((g) => g.name).slice(0, 6).join('、') + (rest.length > 6 ? '…' : '') });
    return top;
  }
  function colorOf(R, g) {
    const i = R.groups.indexOf(g), a = A(); if (!a || !a.donut) return 'var(--cyan)';
    return i >= 0 && i < 5 ? a.donut.color(i) : a.donut.other();
  }

  function paintOut(R) {
    const out = $('#pfOut'); if (!out) return;
    if (!R.groups.length) {
      out.innerHTML = `<div class="row spread"><h3>族群曝險</h3></div><div class="pfempty" id="pfEmpty">${S.rows.length ? '查不到這些代號的最新收盤價，請改用「金額」輸入' : '輸入持股後，這裡會算出你的錢集中在哪些族群'}</div>`;
      return;
    }
    const a = A(), parts = partsOf(R);
    out.innerHTML = `<div class="row spread"><h3>族群曝險</h3></div>
<div class="pftop"><div class="pfdn" id="pfDn" role="img" aria-label="族群曝險甜甜圈"></div>
  <div class="pfside"><ul class="pflg" id="pfLg">${parts.map((p, i) => `<li data-gid="${esc(p.gid)}"${S.sel === p.gid ? ' class="on"' : ''}><i style="background:${p.isOther ? 'var(--ink-3)' : esc(a.donut.color(i))}"></i><span title="${esc(p.hint && p.isOther ? p.name + '：' + p.hint : p.name)}">${esc(p.name)}</span><b>${num(p.value / R.total * 100, 1)}%</b></li>`).join('')}</ul>
  <p class="pffact" id="pfFact">${factLine(R)}</p></div></div><div id="pfGTW">${groupTable(R)}</div>`;
    const el = $('#pfDn');
    const op = { size: 210, fmtVal: (v) => a.fmt.i(v), valLabel: '市值', centerLabel: '持股', centerValue: S.rows.length + ' 檔', cursor: 'pointer' };
    const { option } = a.donut.option(parts, op);
    const inst = a.chart(el, option, { notMerge: true });
    if (inst) {
      a.donut.wireHover(inst, parts, op);
      inst.off('click');
      inst.on('click', (p) => { if (p.seriesIndex === 0 && p.data && p.data.gid && p.data.gid !== '_other') pick(p.data.gid); });
    }
  }

  function paint() {
    const R = calc();
    S.last = R;
    paintList(R); paintOut(R);
    const w = $('#pfWrap'); if (w) w.classList.toggle('has', R.groups.length > 0);
    const c = $('#pfClear'); if (c) { c.textContent = S.clearArm ? '再按一次確認清除' : '清除全部'; c.classList.toggle('arm', S.clearArm); c.disabled = !S.rows.length; }
    const cp = cap(), add = $('#pfAdd'); if (add) add.title = `目前方案最多 ${cp} 檔（已輸入 ${S.rows.length} 檔）`;
  }

  /* 點扇區／圖例／表格列＝在原地展開那個族群的持股；只換表格與圖例的選中狀態，不重畫甜甜圈（不閃、不重播動畫） */
  function pick(gid) {
    S.sel = S.sel === gid ? null : gid;
    const R = S.last || calc(), w = $('#pfGTW'); if (!w) return;
    w.innerHTML = groupTable(R);
    $$('#pfLg li').forEach((li) => li.classList.toggle('on', li.dataset.gid === S.sel));
  }

  /* ------------------------------------------------------------------ 動作 */
  function resolve(q) {
    q = String(q || '').trim().toUpperCase(); if (!q) return null;
    if (byCode.has(q)) return byCode.get(q);
    const nm = stocks.filter((s) => (s.name || '').toUpperCase() === q);
    if (nm.length) return nm[0];
    const part = stocks.filter((s) => (s.name || '').toUpperCase().includes(q)).sort((x, y) => (y.turnover || 0) - (x.turnover || 0));
    return part.length ? part[0] : null;
  }
  const parseNum = (t) => { const n = Number(String(t == null ? '' : t).replace(/[,，\s元股NT$]/gi, '')); return Number.isFinite(n) ? n : NaN; };

  /* 加一檔（或覆蓋同代號）。回傳 'ok'｜'full'｜'nf'｜'bad' */
  function addRow(code, mode, v) {
    const s = resolve(code); if (!s) return 'nf';
    if (!(v > 0)) return 'bad';
    const c = s.code.toUpperCase(), ex = S.rows.find((r) => r.c === c);
    if (ex) { ex.m = mode; ex.v = v; return 'ok'; }
    if (S.rows.length >= cap()) return 'full';
    S.rows.push({ c, m: mode, v }); return 'ok';
  }
  const fullMsg = () => `目前方案最多 ${cap()} 檔，要放更多需升級方案（已輸入的不會被刪）`;

  function onAdd() {
    const code = $('#pfCode').value, v = parseNum($('#pfQty').value);
    const r = addRow(code, S.mode, v);
    if (r === 'nf') return msg(`找不到「${code.trim()}」，請輸入股票代號或名稱`, true);
    if (r === 'bad') return msg(S.mode === 'sh' ? '請輸入大於 0 的股數' : '請輸入大於 0 的金額', true);
    if (r === 'full') return msg(fullMsg(), true);
    saveRows(); $('#pfCode').value = ''; $('#pfQty').value = ''; msg(`已加入 ${resolve(code).name}`); S.clearArm = false; paint(); $('#pfCode').focus();
  }
  function onWatch() {
    const W = window.TwWatch; if (!W) return msg('自選清單尚未載入', true);
    const t = W.curTab(), codes = (t && t.codes) || [];
    if (!codes.length) return msg(`自選「${t ? t.name : ''}」裡還沒有股票`, true);
    let n = 0, full = false;
    codes.forEach((c) => { if (S.rows.some((r) => r.c === String(c).toUpperCase())) return; const r = addRow(c, 'sh', DEF_SHARES); if (r === 'ok') n++; else if (r === 'full') full = true; });
    saveRows(); S.clearArm = false;
    msg(n ? `已從自選「${t.name}」帶入 ${n} 檔，預設每檔 1 張，請改成實際股數${full ? '；已達方案檔數上限' : ''}` : full ? fullMsg() : '自選裡的股票都已經在清單裡', full && !n);
    paint();
  }
  function importText(txt) {
    let n = 0, skip = 0, full = false;
    String(txt || '').split(/\r?\n/).forEach((ln) => {
      const p = ln.split(/[,\t，;]+/).map((x) => x.replace(/^["'\s]+|["'\s]+$/g, '')).filter(Boolean);
      if (p.length < 2) { if (ln.trim()) skip++; return; }
      const v = parseNum(p[1]); if (!(v > 0)) { skip++; return; }
      const r = addRow(p[0], 'sh', v); if (r === 'ok') n++; else { skip++; if (r === 'full') full = true; }
    });
    saveRows(); S.clearArm = false;
    msg(`匯入 ${n} 檔${skip ? `，略過 ${skip} 行（格式不符、查不到代號或超過上限）` : ''}${full ? '；已達方案檔數上限' : ''}`, !n);
    paint();
  }
  function onClear() {
    if (!S.rows.length) return;
    if (!S.clearArm) { S.clearArm = true; paint(); clearTimeout(timer); timer = setTimeout(() => { S.clearArm = false; const c = $('#pfClear'); if (c) { c.textContent = '清除全部'; c.classList.remove('arm'); } }, 4000); return; }
    clearTimeout(timer); S.rows = []; S.sel = null; S.clearArm = false; saveRows(); msg('已清除全部持股'); paint();
  }

  function wire(root) {
    root.addEventListener('click', (e) => {
      const t = e.target;
      const m = t.closest && t.closest('#pfMode button');
      if (m) { S.mode = m.dataset.m; $$('#pfMode button').forEach((b) => b.classList.toggle('on', b === m)); $('#pfQty').placeholder = S.mode === 'sh' ? '股數（1 張＝1000 股）' : '金額（元）'; return; }
      if (t.closest && t.closest('#pfAdd')) return onAdd();
      if (t.closest && t.closest('#pfWatch')) return onWatch();
      if (t.closest && t.closest('#pfImp')) { if (t.closest('#pfImp').dataset.plkb) return; $('#pfFile').click(); return; }
      if (t.closest && t.closest('#pfClear')) return onClear();
      const x = t.closest && t.closest('button.x[data-x]');
      if (x) { S.rows = S.rows.filter((r) => r.c !== x.dataset.x); saveRows(); S.clearArm = false; msg(''); paint(); return; }
      if (t.closest && t.closest('#pfMore')) { S.all = !S.all; const g = $('#pfGT'); if (g) g.classList.toggle('all', S.all); const b = $('#pfMore'); if (b) b.textContent = S.all ? '只看前三大' : '看全部 ' + (S.last ? S.last.groups.length : '') + ' 個族群'; return; }
      const lg = t.closest && t.closest('#pfLg li[data-gid]');
      if (lg) { if (lg.dataset.gid !== '_other') pick(lg.dataset.gid); return; }
      if (t.closest && t.closest('a')) return;
      const tr = t.closest && t.closest('#pfGT tr.g[data-gid]');
      if (tr) pick(tr.dataset.gid);
    });
    root.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target && (e.target.id === 'pfCode' || e.target.id === 'pfQty')) { e.preventDefault(); onAdd(); }
      if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.matches && e.target.matches('#pfGT tr.g')) { e.preventDefault(); pick(e.target.dataset.gid); }
    });
    root.addEventListener('change', (e) => {
      const q = e.target;
      if (q && q.id === 'pfFile') {
        const f = q.files && q.files[0]; if (!f) return;
        const rd = new FileReader(); rd.onload = () => { importText(String(rd.result || '')); q.value = ''; }; rd.readAsText(f); return;
      }
      if (q && q.matches && q.matches('input.q[data-c]')) {
        const v = parseNum(q.value), r = S.rows.find((x) => x.c === q.dataset.c);
        if (!r) return;
        if (!(v > 0)) { q.value = A().fmt.i(r.v); return msg('數量要大於 0；要移除請按 ✕', true); }
        r.v = v; saveRows(); msg(''); paint();
      }
    });
  }

  /* ------------------------------------------------------------------ 進入點 */
  async function render() {
    const root = document.getElementById('v-portfolio'); if (!root || !A()) return;
    injectCSS();
    S.rows = readRows(); S.clearArm = false;
    if (!$('#pfWrap', root)) { skeleton(root); wire(root); }
    else { const c = $('#pfCode'); if (c) c.value = ''; }
    msg('');
    await loadData();
    paint();
  }
  window.TwPortfolio = { render, _s: S, calc, KEY };
})();
