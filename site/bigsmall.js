/* ============================================================================
   個股「大戶／散戶買賣（推估）」面板（site/bigsmall.js）—— 2026-11-07
   ----------------------------------------------------------------------------
   Andy 11-07：「個股可以看到 大戶 散戶 當前買賣狀況，即時的資訊 以及 日K級別資訊 這功能記得也要顯在權限內 但暫不開放」。
   查證、口徑、誤差：docs/bigsmall_sources.md；DECISIONS #384。

   · 放在個股「大戶／散戶」分頁（桌機 #stockTab 的集保圖下面；手機 #mbBody[data-tab="big"] 的「買賣推估」分段）。
   · 功能鍵 stock.bigsmall（features.js）：四個方案範本都寫 false＝暫不開放；站主不受限（perm.js owner）。
     沒開＝整張卡不畫（手機也不列「買賣推估」分段），**不抓任何資料、不打任何報價**；Andy 在 #admin/perm 打開某個方案後，那個方案的人就看得到。
   · 即時（今日累計、每 5 秒）：另外要過即時閘門 livegate（TwLive.allowed()，只有站主／管理員，DECISIONS #326）；
     鈕標 data-live-ui，網址一律從 Live.proxy() 拿（非管理者回空字串＝網路層第三道保險）。
   · 日 K 級別：讀 data/bigsmall/<代號>.json（資料湖 bigsmall_daily，收盤後彙整，從開始收集那天起累積）＋個股 JSON 的日 K 對照。
   · 規則（大單／小單門檻、內外盤判斷、沒看到的量怎麼分）跟 pipeline/compute/bigsmall.py **逐行同一套**，
     tests/test_bigsmall.py 用同一組向量對兩邊（node 跑這支的 Acc）。改一邊一定要改另一邊。
   ============================================================================ */
(function (root) {
  'use strict';
  const BIG_FLOOR = 1e6, AVG_MULT = 4, AO = '09:00:00', AC = '13:30:00', STEP = 5;
  const num = (v) => { const x = parseFloat(v); return isFinite(x) ? x : null; };
  const first = (s) => (s ? num(String(s).split('_')[0]) : null);
  const r1 = (x) => Math.round(x * 10) / 10;
  const threshold = (avg) => { const a = num(avg) || 0; return Math.max(BIG_FLOOR, AVG_MULT * a); };

  function Acc(thr, o) {
    Object.assign(this, { thr: thr || BIG_FLOOR, v0: null, v: null, p: null, ask: null, bid: null, dir: 0,
      big_buy: 0, big_sell: 0, small_buy: 0, small_sell: 0, big_buy_amt: 0, big_sell_amt: 0, small_buy_amt: 0, small_sell_amt: 0,
      neutral: 0, auction: 0, seen: 0, seen_big: 0, polls: 0, first_t: '', last_t: '', series: [] }, o || {});
  }
  Acc.prototype.step = function (m) {
    const tr = m.trade || {};
    const v = num(m.v), t = String(m.t || tr.t || ''), ask = first(m.a), bid = first(m.b);
    this.polls += 1;
    if (v === null) return;
    let p = num(m.z); if (p === null) p = num(tr.z); if (p === null) p = this.p;
    if (this.v === null) { this.v0 = this.v = v; this.p = p; this.ask = ask || this.ask; this.bid = bid || this.bid; this.first_t = this.last_t = t; return; }
    const dv = v - this.v;
    if (dv <= 0 || p === null) { this.ask = ask || this.ask; this.bid = bid || this.bid; this.last_t = t || this.last_t; return; }
    let tv = num(m.tv); if (tv === null) tv = num(tr.v);
    if (tv === null || tv <= 0 || tv > dv) tv = 0;
    if (t === AO || t === AC) { this.neutral += dv; this.auction += dv; }
    else {
      let d;
      if (this.ask !== null && p >= this.ask) d = 1;
      else if (this.bid !== null && p <= this.bid) d = -1;
      else if (this.p !== null && p > this.p) d = 1;
      else if (this.p !== null && p < this.p) d = -1;
      else d = this.dir;
      let big = 0;
      if (tv > 0) { if (tv * 1000 * p >= this.thr) { big += tv; this.seen_big += tv; } this.seen += tv; }
      const r = dv - tv;
      if (r > 0) { if (this.seen > 0) big += r * (this.seen_big / this.seen); else if (r * 1000 * p >= this.thr) big += r; }
      const small = dv - big;
      if (d > 0) { this.big_buy += big; this.small_buy += small; this.big_buy_amt += big * 1000 * p; this.small_buy_amt += small * 1000 * p; }
      else if (d < 0) { this.big_sell += big; this.small_sell += small; this.big_sell_amt += big * 1000 * p; this.small_sell_amt += small * 1000 * p; }
      else this.neutral += dv;
      if (d) this.dir = d;
    }
    this.v = v; this.p = p; this.ask = ask || this.ask; this.bid = bid || this.bid; this.last_t = t || this.last_t;
    this.mark(t);
  };
  Acc.prototype.mark = function (t) {
    if (t.length < 5) return;
    const m = +t.slice(0, 2) * 60 + +t.slice(3, 5), s = m - m % STEP;
    const hm = String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
    const pt = [hm, r1(this.big_buy - this.big_sell), r1(this.small_buy - this.small_sell)];
    const L = this.series;
    if (L.length && L[L.length - 1][0] === hm) L[L.length - 1] = pt; else L.push(pt);
  };
  Acc.prototype.row = function (date, code) {
    const obs = this.v !== null && this.v0 !== null ? this.v - this.v0 : 0;
    return { date, code, big_buy: r1(this.big_buy), big_sell: r1(this.big_sell), small_buy: r1(this.small_buy), small_sell: r1(this.small_sell),
      big_net_amt: Math.round(this.big_buy_amt - this.big_sell_amt), small_net_amt: Math.round(this.small_buy_amt - this.small_sell_amt),
      neutral: r1(this.neutral), auction: r1(this.auction), observed: r1(obs), pre: r1(this.v0 || 0), sampled: r1(this.seen),
      coverage: obs > 0 ? Math.round(this.seen / obs * 10000) / 10000 : null, threshold: Math.round(this.thr), polls: this.polls, first_t: this.first_t, last_t: this.last_t };
  };
  const core = { Acc, threshold, BIG_FLOOR, AVG_MULT };
  if (typeof module !== 'undefined' && module.exports) { module.exports = core; return; }

  // ======================================================================== 畫面
  const KEY = 'stock.bigsmall';
  const A = () => root.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } } };
  const can = () => { try { return !!(root.TwPerm && root.TwPerm.can(KEY)); } catch (e) { return false; } };
  const liveOK = () => { try { return !!(root.TwLive && root.TwLive.allowed() && root.Live && root.Live.proxy()); } catch (e) { return false; } };
  const COL = () => { const C = root.TwChipColors || {}; return { big: C.foreign || '#3F6BC4', small: C.retail || '#2A9D8F' }; };
  const tpe = () => new Date(Date.now() + 8 * 3600000);
  const today = () => tpe().toISOString().slice(0, 10);
  const inSession = () => { if (root.TW_BS_FORCE_OPEN) return true; const d = tpe(), w = d.getUTCDay(), m = d.getUTCHours() * 60 + d.getUTCMinutes(); return w >= 1 && w <= 5 && m >= 8 * 60 + 59 && m <= 13 * 60 + 36; };
  const lots = (v) => (v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(Math.round(v)).toLocaleString('zh-TW'));
  const plain = (v) => (v == null ? '—' : Math.round(v).toLocaleString('zh-TW'));
  const amt = (v) => { if (v == null) return '—'; const a = Math.abs(v), s = v > 0 ? '+' : v < 0 ? '−' : '';
    return a >= 1e8 ? s + (a / 1e8).toFixed(2) + ' 億' : s + Math.round(a / 1e4).toLocaleString('zh-TW') + ' 萬'; };
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'muted');
  const S = { code: null, mode: null, win: +ls.get('tw.bs.win', '20') || 20, timer: 0, acc: null, pts: [], daily: null, thr: null, err: '' };

  function css() {
    if (document.getElementById('bsCss')) return;
    const st = document.createElement('style'); st.id = 'bsCss';
    st.textContent = `
#bsCard{margin-top:var(--gap-card,16px)}
#bsCard .bshd{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap}
#bsCard .bshd h3{margin:0}
#bsCard .bshd .sp{flex:1}
#bsCard .bstag{font-size:var(--fs-min);color:var(--ink-3);border:1px solid var(--line-2);border-radius:var(--r-pill);padding:0 var(--sp-2);line-height:20px}
#bsCard .bskpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--sp-2);margin:var(--sp-3) 0}
#bsCard .bskpi > div{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:var(--sp-2) var(--sp-3);min-width:0}
#bsCard .bskpi .k{font-size:var(--fs-min);color:var(--ink-2);display:flex;align-items:center;gap:6px;white-space:nowrap}
#bsCard .bskpi .k i{width:10px;height:10px;border-radius:2px;display:inline-block}
#bsCard .bskpi b{display:block;font-family:var(--mono);font-size:20px;line-height:1.3;white-space:nowrap}
#bsCard .bskpi small{display:block;font-family:var(--mono);font-size:var(--fs-min);color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#bsCard .bsduo{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);gap:var(--sp-3);align-items:stretch}
#bsCard .bschart{min-height:360px;height:360px}
#bsCard .bstbl{max-height:360px;overflow:auto;border:1px solid var(--line);border-radius:var(--r-sm)}
#bsCard .bstbl table{width:100%;border-collapse:collapse;font-size:var(--fs-sm)}
#bsCard .bstbl th,#bsCard .bstbl td{padding:6px var(--sp-2);text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
#bsCard .bstbl th:first-child,#bsCard .bstbl td:first-child{text-align:left}
#bsCard .bstbl th{position:sticky;top:0;background:var(--panel-2);color:var(--ink-2);font-weight:600}
#bsCard .bstbl td{font-family:var(--mono)}
#bsCard .bsnote{font-size:var(--fs-min);color:var(--ink-3);margin-top:var(--sp-2)}
#bsCard .bsempty{display:flex;align-items:center;justify-content:center;min-height:120px;color:var(--ink-3);font-size:var(--fs-sm);text-align:center;padding:var(--sp-3)}
#bsCard .seg button[disabled]{opacity:.42;cursor:not-allowed}
@media (max-width:1100px){#bsCard .bsduo{grid-template-columns:1fr}#bsCard .bstbl{max-height:240px}}
@media (max-width:640px){
  #bsCard .bskpi{grid-template-columns:repeat(2,minmax(0,1fr))}
  #bsCard .bskpi b{font-size:17px}
  #bsCard .bskpi small{white-space:normal;overflow:visible}
  #bsCard .bschart{min-height:300px;height:300px}
  #bsCard .seg button{min-height:32px}
}`;
    document.head.appendChild(st);
  }

  const HOW = ['推估，不是官方數字：從證交所盤中快照的增量推算，沒有逐筆成交',
    '大單（大戶）＝單筆成交金額 ≥ 門檻；其餘＝小單（散戶）',
    '門檻＝max(100 萬元, 4 × 近 20 日平均每筆成交金額)',
    '成交在委賣價以上＝外盤（主動買）、委買價以下＝內盤（主動賣）',
    '快照之間沒看到的成交，依當天已看到的大小單比例分攤；開盤、收盤集合競價不分方向'];
  const HOW_FINE = '這是推估：一次快照只看得到最後一筆，涵蓋率＝真的看到單筆大小的量占成交量的比例，越低誤差越大。日 K 從開始收集那天起逐日累積，補不了過去；集保千張大戶是每週公布的持股，放在下面當週級參考。口徑與已知誤差見 docs/bigsmall_sources.md。';

  function shell(body, tools) {
    return `<div class="card" id="bsCard" data-bs="${esc(S.mode || '')}"><div class="bshd"><h3>大戶／散戶買賣 <span class="bstag">推估</span> <button class="howbtn pop" data-how="skbs" data-ttl="大戶／散戶買賣（推估）" type="button" aria-label="大戶／散戶買賣怎麼看">?</button></h3>`
      + `<span class="sp"></span>${tools || ''}</div><div class="howtxt" id="how-skbs" hidden>${(A() && A().howHTML) ? A().howHTML('', HOW) : ''}<p class="muted">${HOW_FINE}</p></div>${body}</div>`;
  }

  /** 掛載點：桌機 industry.js renderTab 在「大戶／散戶」分頁畫完後呼叫；手機 mobile3.js 的「買賣推估」分段呼叫。 */
  function mount(pg, el) {
    if (!el || !pg || !pg.meta) return;
    css();
    stop();
    S.code = String(pg.meta.code); S.pg = pg; S.host = el; S.acc = null; S.pts = []; S.daily = null; S.err = '';
    const old = $('#bsCard', el); if (old) old.remove();
    if (!can()) {
      /* 暫不開放：整張卡不畫（不是蓋鎖頭 —— 鎖頭卡寫的是「升級 Plus」，但目前沒有任何方案有這個功能，那句話會騙人）；
         不抓資料、不打報價。權限晚一步回來（站主身分確認、Andy 之後在 #admin/perm 打開）→ tw:perm 時再掛一次。 */
      S.mode = null; S.wait = { pg, el };
      return;
    }
    S.wait = null;
    const live = liveOK();
    const saved = ls.get('tw.bs.mode', '');
    S.mode = live ? (saved === 'day' || saved === 'live' ? saved : (inSession() ? 'live' : 'day')) : 'day';
    draw();
    loadDaily();
    if (S.mode === 'live') startLive();
  }

  function tools() {
    const live = liveOK();
    const seg = `<div class="seg" id="bsMode" role="group" aria-label="即時或日 K">`
      + (live ? `<button type="button" data-v="live" data-live-ui class="${S.mode === 'live' ? 'on' : ''}">今日即時</button>` : '')
      + `<button type="button" data-v="day" class="${S.mode === 'day' ? 'on' : ''}">日 K</button></div>`;
    const n = S.daily ? S.daily.days.length : 0;
    const wins = S.mode === 'day' ? `<div class="seg" id="bsWin" role="group" aria-label="期間">${[20, 60, 120].map(w => {
      const dis = w > 20 && n < w / 2;
      return `<button type="button" data-v="${w}" class="${S.win === w ? 'on' : ''}"${dis ? ` disabled title="已收集 ${n} 天，滿 ${w / 2} 天才開"` : ''}>${w} 日</button>`; }).join('')}</div>` : '';
    return seg + wins;
  }

  function draw() {
    const el = S.host; if (!el) return;
    const card = $('#bsCard', el);
    const html = shell(S.mode === 'live' ? liveBody() : dayBody(), tools());
    if (card) card.outerHTML = html; else el.insertAdjacentHTML('beforeend', html);
    const c = $('#bsCard', el);
    c.querySelectorAll('#bsMode button').forEach(b => b.addEventListener('click', () => {
      if (b.dataset.v === S.mode) return;
      S.mode = b.dataset.v; ls.set('tw.bs.mode', S.mode);
      if (S.mode === 'live') startLive(); else stop();
      draw();
    }));
    c.querySelectorAll('#bsWin button').forEach(b => b.addEventListener('click', () => {
      if (b.disabled) return; S.win = +b.dataset.v; ls.set('tw.bs.win', String(S.win)); draw();
    }));
    if (S.mode === 'live') drawLiveChart(); else drawDayChart();
  }

  function kpis(o) {
    const C = COL();
    const cell = (name, color, net, buy, sell, a) => `<div><span class="k"><i style="background:${color}"></i>${name}淨額</span><b class="${cls(net)}">${lots(net)} 張</b><small>${a != null ? '淨 ' + amt(a) + '元' : ''}${buy != null ? `${a != null ? '・' : ''}買 ${plain(buy)}／賣 ${plain(sell)}` : ''}</small></div>`;
    return `<div class="bskpi" id="bsKpi">${cell('大單（大戶）', C.big, o.bn, o.bb, o.bs, o.ba)}${cell('小單（散戶）', C.small, o.sn, o.sb, o.ss, o.sa)}`
      + `<div><span class="k">${esc(o.k3)}</span><b>${o.v3}</b><small>${o.s3}</small></div><div><span class="k">${esc(o.k4)}</span><b class="${o.c4 || ''}">${o.v4}</b><small>${o.s4}</small></div></div>`;
  }
  function holderRef() {
    const ho = (S.pg && S.pg.holders || []).filter(r => r && r[1] != null);
    if (!ho.length) return { v: '—', s: '集保尚無資料', c: '' };
    const L = ho[ho.length - 1], P = ho.length > 1 ? ho[ho.length - 2] : null, d = P ? L[1] - P[1] : null;
    return { v: (+L[1]).toFixed(2) + '%', s: `${String(L[0]).slice(5)} 週${d == null ? '' : (d > 0 ? ' +' : d < 0 ? ' −' : ' ±') + Math.abs(d).toFixed(2) + 'pp'}`, c: d == null ? '' : cls(d) };
  }

  // ------------------------------------------------------------------ 日 K
  function dayBody() {
    const D = S.daily;
    if (S.err) return `<div class="bsempty">${esc(S.err)}</div>`;
    if (!D) return '<div class="bsempty">讀取中…</div>';
    const days = D.days.slice(-S.win);
    const L = days[days.length - 1];
    const h = holderRef();
    const cov = L && L[5] != null ? Math.round(L[5] * 100) + '%' : '—';
    const top = kpis(L ? { bn: L[1], sn: L[2], ba: L[3], sa: L[4], bb: null, bs: null, sb: null, ss: null,
      k3: '涵蓋率（最新一天）', v3: cov, s3: `${L[0].slice(5)}・門檻 ${amt(L[8]).replace('+', '')}元`,
      k4: '集保千張大戶（週）', v4: h.v, s4: h.s, c4: h.c }
      : { bn: null, sn: null, k3: '涵蓋率', v3: '—', s3: '尚未收集', k4: '集保千張大戶（週）', v4: h.v, s4: h.s, c4: h.c });
    const rows = days.slice().reverse().map(r => `<tr><td>${esc(r[0].slice(5))}</td><td class="${cls(r[1])}">${lots(r[1])}</td><td class="${cls(r[2])}">${lots(r[2])}</td><td>${r[5] == null ? '—' : Math.round(r[5] * 100) + '%'}</td></tr>`).join('');
    const tbl = `<div class="bstbl" id="bsTbl"><table><thead><tr><th>日期</th><th>大單淨(張)</th><th>小單淨(張)</th><th>涵蓋</th></tr></thead><tbody>${rows || '<tr><td colspan="4">尚無資料</td></tr>'}</tbody></table></div>`;
    const grow = `<div class="bsnote" id="bsGrow" data-days="${D.days.length}">${D.days.length ? `從 ${esc(D.days[0][0])} 起每個交易日收盤後累積，目前 ${D.days.length} 天` : '這一檔還沒有收集到日資料：從開始收集那天起每個交易日收盤後累積'}${D.sample ? '・<b>示意資料（非真實）</b>' : ''}</div>`;
    return top + `<div class="bsduo"><div id="bsChart" class="bschart chart"></div>${tbl}</div>` + grow;
  }
  function drawDayChart() {
    const D = S.daily, Ap = A(); if (!D || !Ap || !Ap.chart || !document.getElementById('bsChart')) return;
    const C = COL(), CH = Ap.CH;
    /* X 軸＝日 K 日期 ∪ 有收集的日期，取最後 N 天（同籌碼分頁 chipAxis 的做法）：資料湖的大小單比個股 JSON 新一天時也看得到 */
    const km = new Map((S.pg.daily || []).map(r => [String(r[0]).slice(0, 10), r]));
    const dm = new Map(D.days.map(r => [r[0], r]));
    const dates = [...new Set([...km.keys(), ...dm.keys()])].sort().slice(-S.win);
    const K = dates.map(d => km.get(d) || null);
    const kv = K.filter(Boolean), lo = kv.length ? Math.min(...kv.map(r => r[3])) : 0, hi = kv.length ? Math.max(...kv.map(r => r[2])) : 1, pad = (hi - lo) * 0.08 || hi * 0.02 || 1;
    const val = (i) => dates.map(d => { const r = dm.get(d); return r ? r[i] : null; });
    Ap.chart('bsChart', {
      animation: false,
      tooltip: { ...Ap.tip, trigger: 'axis', axisPointer: { type: 'line' }, formatter: (ps) => {
        const d = ps[0].axisValue, r = dm.get(d), k = km.get(d);
        return `<b>${d}</b>` + (k ? `<br>收盤 ${Ap.fmt.n(k[4], 2)}` : '') + (r ? `<br><span style="color:${C.big}">●</span> 大單淨 ${lots(r[1])} 張（${amt(r[3])}）`
          + `<br><span style="color:${C.small}">●</span> 小單淨 ${lots(r[2])} 張（${amt(r[4])}）<br>涵蓋率 ${r[5] == null ? '—' : Math.round(r[5] * 100) + '%'}` : '<br>這天沒有收集'); } },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [{ left: 56, right: 16, top: 12, height: '46%' }, { left: 56, right: 16, top: '62%', bottom: 28 }],
      xAxis: [0, 1].map(i => ({ type: 'category', data: dates, gridIndex: i, boundaryGap: true, axisLine: { lineStyle: { color: CH.line || '#3b4f7f' } },
        axisLabel: { show: i === 1, color: CH.ink3, fontFamily: Ap.NUM_FONT, formatter: (v) => v.slice(5), hideOverlap: true }, axisTick: { show: false } })),
      yAxis: [{ ...Ap.axisStyle, type: 'value', gridIndex: 0, scale: true, splitNumber: 3, min: +(lo - pad).toPrecision(4), max: +(hi + pad).toPrecision(4), axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT } },
        { ...Ap.axisStyle, type: 'value', gridIndex: 1, splitNumber: 2, axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT, formatter: (v) => Math.abs(v) >= 1e4 ? (v / 1e4).toFixed(1) + '萬' : v } }],
      series: [
        { name: '日 K', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0, data: K.map(r => (r ? [r[1], r[4], r[3], r[2]] : '-')),
          itemStyle: { color: CH.up, color0: CH.down, borderColor: CH.up, borderColor0: CH.down } },
        { name: '大單淨', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: val(1), itemStyle: { color: C.big }, barMaxWidth: 14, solid: true, silent: true },
        { name: '小單淨', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: val(2), itemStyle: { color: C.small }, barMaxWidth: 14, solid: true, silent: true },
      ],
    }, { notMerge: true });
  }
  // 先讀 _index.json（只抓一次、記在記憶體）：代號不在名單裡就不發 <代號>.json 請求（避免 404）；索引抓不到也安靜略過
  let _idx = null;
  function loadIndex() {
    if (!_idx) _idx = fetch('data/bigsmall/_index.json', { cache: 'no-cache' }).then(r => (r.ok ? r.json() : null)).then(j => (j && Array.isArray(j.codes) ? new Set(j.codes.map(String)) : null)).catch(() => null);
    return _idx;
  }
  async function loadDaily() {
    const code = S.code;
    try {
      const idx = await loadIndex();
      const has = !!(idx && idx.has(String(code)));
      const [d, t] = await Promise.all([
        has ? fetch('data/bigsmall/' + encodeURIComponent(code) + '.json', { cache: 'no-cache' }).then(r => (r.ok ? r.json() : null)).catch(() => null) : null,
        fetch('data/bigsmall/_thr.json', { cache: 'no-cache' }).then(r => (r.ok ? r.json() : null)).catch(() => null)]);
      if (code !== S.code) return;
      S.daily = d && Array.isArray(d.days) ? d : { days: [] };
      S.thr = (d && d.thr) || (t && t.thr && t.thr[code]) || BIG_FLOOR;
      if (S.acc) S.acc.thr = S.thr;
    } catch (e) { S.daily = { days: [] }; }
    if (S.mode === 'day') draw();
  }

  // ------------------------------------------------------------------ 今日即時（只有站主／管理員）
  const LSK = () => 'tw.bs.live.' + S.code;
  function restore() {
    try { const j = JSON.parse(ls.get(LSK(), 'null')); if (j && j.d === today() && j.acc) { S.acc = new Acc(j.acc.thr, j.acc); S.pts = j.pts || []; return; } } catch (e) { /* 壞檔重來 */ }
    S.acc = new Acc(S.thr || BIG_FLOOR); S.pts = [];
  }
  function save() { try { ls.set(LSK(), JSON.stringify({ d: today(), acc: S.acc, pts: S.pts.slice(-2000) })); } catch (e) { /* 滿了就算了 */ } }
  function exch() { const m = String((S.pg.meta || {}).market || '').toUpperCase(); return (m === 'TPEX' || m === 'OTC' ? 'otc_' : 'tse_') + S.code + '.tw'; }
  async function tick() {
    if (!S.host || !document.body.contains(S.host) || !$('#bsCard', S.host)) { stop(); return; }
    if (!liveOK()) { stop(); return; }
    if (document.hidden) return;
    const base = root.Live.proxy(); if (!base) return;
    try {
      const r = await fetch(base + '/quote?ex_ch=' + encodeURIComponent(exch()), { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json(); const m = (j.msgArray || [])[0];
      if (!m) throw new Error('沒有這一檔的報價');
      if (m.d && m.d.length === 8) { const d = m.d.slice(0, 4) + '-' + m.d.slice(4, 6) + '-' + m.d.slice(6); if (S.accDay && S.accDay !== d) restore(); S.accDay = d; }
      S.acc.step(m);
      if (S.acc.last_t) { const L = S.pts[S.pts.length - 1]; const pt = [S.acc.last_t, r1(S.acc.big_buy - S.acc.big_sell), r1(S.acc.small_buy - S.acc.small_sell)];
        if (L && L[0] === pt[0]) S.pts[S.pts.length - 1] = pt; else S.pts.push(pt); }
      S.err = ''; save();
    } catch (e) { S.err = '即時報價暫時取不到（' + (e && e.message || e) + '）'; }
    if (S.mode === 'live') draw();
    if (!inSession()) stop();
  }
  function startLive() { if (!liveOK()) return; restore(); stop(); tick(); if (inSession()) S.timer = setInterval(tick, 5000); }
  function stop() { if (S.timer) { clearInterval(S.timer); S.timer = 0; } }
  function liveBody() {
    const a = S.acc || new Acc(S.thr || BIG_FLOOR), R = a.row(today(), S.code);
    const cov = R.coverage == null ? '—' : Math.round(R.coverage * 100) + '%';
    const top = kpis({ bn: R.big_buy - R.big_sell, sn: R.small_buy - R.small_sell, bb: R.big_buy, bs: R.big_sell, sb: R.small_buy, ss: R.small_sell,
      ba: R.big_net_amt, sa: R.small_net_amt, k3: '涵蓋率', v3: cov, s3: `門檻 ${amt(a.thr).replace('+', '')}元・開盤前已成交 ${plain(R.pre)} 張`,
      k4: '開始收集', v4: esc(a.first_t || '—'), s4: `最新 ${esc(a.last_t || '—')}・${inSession() ? '每 5 秒更新' : '非盤中，停止更新'}` });
    const rows = a.series.slice().reverse().map(p => `<tr><td>${esc(p[0])}</td><td class="${cls(p[1])}">${lots(p[1])}</td><td class="${cls(p[2])}">${lots(p[2])}</td></tr>`).join('');
    const tbl = `<div class="bstbl" id="bsTbl"><table><thead><tr><th>時間（5 分）</th><th>大單淨(張)</th><th>小單淨(張)</th></tr></thead><tbody>${rows || '<tr><td colspan="3">等第一筆成交…</td></tr>'}</tbody></table></div>`;
    return top + `<div class="bsduo"><div id="bsChart" class="bschart chart"></div>${tbl}</div>`
      + `<div class="bsnote" id="bsLiveNote">${S.err ? esc(S.err) + '・' : ''}從你打開這一頁（${esc(a.first_t || '—')}）起累計；之前的 ${plain(R.pre)} 張沒看到，不算進大小單${root.TW_BS_SAMPLE ? '・<b>示意資料（非真實）</b>' : ''}</div>`;
  }
  function drawLiveChart() {
    const Ap = A(); if (!Ap || !Ap.chart || !document.getElementById('bsChart')) return;
    const C = COL(), CH = Ap.CH, P = S.pts;
    if (!P.length) { Ap.empty && Ap.empty('bsChart', '盤中開始成交後畫出走勢'); return; }
    Ap.chart('bsChart', {
      animation: false,
      tooltip: { ...Ap.tip, trigger: 'axis', formatter: (ps) => `<b>${ps[0].axisValue}</b>` + ps.map(p => `<br><span style="color:${p.color}">●</span> ${p.seriesName} ${lots(p.value)} 張`).join('') },
      grid: { left: 56, right: 16, top: 16, bottom: 28 },
      xAxis: { type: 'category', data: P.map(p => p[0]), boundaryGap: false, axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT, hideOverlap: true }, axisTick: { show: false } },
      yAxis: { ...Ap.axisStyle, type: 'value', splitNumber: 3, axisLabel: { color: CH.ink3, fontFamily: Ap.NUM_FONT } },
      series: [{ name: '大單淨', type: 'line', data: P.map(p => p[1]), showSymbol: false, lineStyle: { color: C.big, width: 2 }, itemStyle: { color: C.big } },
        { name: '小單淨', type: 'line', data: P.map(p => p[2]), showSymbol: false, lineStyle: { color: C.small, width: 2 }, itemStyle: { color: C.small } }],
    }, { notMerge: true });
  }

  root.addEventListener('tw:perm', () => { const w = S.wait; if (w && can() && document.body.contains(w.el)) mount(w.pg, w.el); });
  root.TwBigSmall = Object.assign({}, core, { mount, stop, can, state: () => ({ code: S.code, mode: S.mode, win: S.win, timer: !!S.timer, days: S.daily ? S.daily.days.length : null,
    row: S.acc ? S.acc.row(today(), S.code) : null, pts: S.pts.length, thr: S.thr, err: S.err }) });
})(typeof window !== 'undefined' ? window : this);
