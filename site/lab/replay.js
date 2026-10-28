/* ============================================================================
   交易練習室 › K 線重播（#lab/replay）—— 2026-10-28 建（規格 docs/tradingview_spec.md 第四、七節）
   這一頁回答的問題：「把圖倒回過去某一天，一根一根往前看，當時我會怎麼下單？這一輪練習的成績如何？」
   · 未來的 K 棒完全不畫（資料只送到目前這一根），指標也只算到目前這一根。
   · 模擬下單：市價（下一根開盤成交，避免偷看）、限價、停損，可附停利停損（OCO）。成本、滑價、成交規則與回測引擎同一套。
   · 帳戶（持倉、委託、成交紀錄、帳戶、成績單）只存在這個分頁的記憶體裡，離開就清掉，不進 repo、不上傳。
   ============================================================================ */
(function () {
  'use strict';
  const L = window.TwLab; if (!L) return;
  let U = null, E = null;
  const SPEEDS = [1, 2, 5, 10, 20];
  const MAS = [[5, '#ffb703'], [20, '#4cc9f0'], [60, '#b388ff']];

  function fresh() {
    return { sym: '2330', tf: 'D', B: null, run: false, i: -1, start: -1, playing: false, speed: 2, timer: null, blind: false, pick: false, tab: 'pos',
      kind: 'mkt', unit: 'lot', msg: '', cap: 1000000, acct: null, snaps: [], eq: [], bars: [], series: {}, lines: [], marks: [], times: [], tmap: {} };
  }
  let R = fresh();

  /* ---------------------------------------------------------------- 模擬帳戶 */
  const newAcct = (cap) => ({ cap, cash: cap, lots: [], orders: [], trades: [], fills: [], nid: 1, comm: 0, maxQ: 0 });
  const inst = () => { const k = U.kindOf(R.sym); R.inst = R.inst && R.inst.kind === k ? R.inst : E.instDefaults(k); return R.inst; };
  const A = () => R.acct;
  const pos = () => { const a = A(); return a.lots.length ? a.lots[0].dir : 0; };
  const qtyOf = () => A().lots.reduce((s, x) => s + x.q, 0);
  function equity(c) { const a = A(), it = inst(), fut = it.kind === 'fut'; let e = a.cash; for (const x of a.lots) e += fut ? x.dir * x.q * it.mult * (c - x.p) : x.dir * x.q * c; return e; }
  const feeOf = (it, p, q) => (it.kind === 'fut' ? it.futFee * q : Math.max(it.feeMin, p * q * it.mult * it.feeRate / 100 * it.feeDisc));
  const taxOf = (it, p, q, sell) => (it.kind === 'fut' ? p * q * it.mult * it.futTax / 100 : (sell ? p * q * it.taxRate / 100 : 0));
  const slip = (it, p) => (it.kind === 'fut' ? it.slip : p * it.slip / 100);

  /** 成交一筆（dir＋1 買／－1 賣）：先反向沖掉既有部位（FIFO，每口一筆交易紀錄），剩下的開新倉。回傳訊息或 ''。 */
  function applyFill(dir, q, raw, i, note, why) {
    const a = A(), it = inst(), fut = it.kind === 'fut', B = R.B;
    const p = dir === 1 ? raw + slip(it, raw) : raw - slip(it, raw);
    let left = q;
    if (a.lots.length && a.lots[0].dir === -dir) {
      while (left > 0 && a.lots.length) {
        const x = a.lots[0], u = Math.min(left, x.q), frac = u / x.q;
        const exFee = feeOf(it, p, u), exTax = taxOf(it, p, u, x.dir === 1);
        const gross = x.dir * (p - x.p) * u * it.mult;
        if (fut) a.cash += gross - exFee - exTax; else if (x.dir === 1) a.cash += p * u - exFee - exTax; else a.cash -= p * u + exFee;
        const eFee = x.fee * frac, eTax = x.tax * frac, costs = eFee + eTax + exFee + exTax, notional = x.p * u * it.mult;
        a.comm += exFee + exTax;
        a.trades.push({ dir: x.dir, i0: x.i0, i1: i, p0: x.p, p1: p, qty: u, gross, costs, pnl: gross - costs, pnlP: (gross - costs) / notional * 100, bars: i - x.i0, mfe: x.mfe * u * it.mult, mae: x.mae * u * it.mult, mfeP: x.mfe / x.p * 100, maeP: x.mae / x.p * 100, why: why || '平倉', entryWhy: x.why || '手動', open: false, notional, note: x.note || note || '' });
        a.fills.push({ i, dir, q: u, p, fee: exFee + exTax, pnl: gross - costs, note: note || '', kind: '平倉' });
        x.q -= u; x.fee -= eFee; x.tax -= eTax; left -= u;
        if (x.q <= 0) a.lots.shift();
      }
    }
    if (left > 0) {
      const f = feeOf(it, p, left), t = taxOf(it, p, left, dir === -1);
      if (dir === 1 && !fut && a.cash < p * left + f) return '現金不足，這筆沒有成交';
      if (fut ? a.cash < f + t : false) return '資金不足，這筆沒有成交';
      if (fut) a.cash -= f + t; else if (dir === 1) a.cash -= p * left + f; else a.cash += p * left - f - t;
      a.comm += f + t;
      a.lots.push({ dir, q: left, p, i0: i, fee: f, tax: t, mfe: 0, mae: 0, why: why || '手動', note });
      a.fills.push({ i, dir, q: left, p, fee: f + t, pnl: null, note: note || '', kind: '開倉' });
      a.maxQ = Math.max(a.maxQ, qtyOf());
    }
    return '';
  }

  /** 新的一根開出來：依序處理委託（市價先、價格單依下單順序），再更新持倉的最大有利／不利幅度。 */
  function processBar(i) {
    const a = A(), B = R.B, o = B.o[i], h = B.h[i], l = B.l[i];
    const list = a.orders.filter((x) => x.kind === 'mkt').concat(a.orders.filter((x) => x.kind !== 'mkt'));
    const done = new Set();
    for (const od of list) {
      if (done.has(od.id)) continue;
      if (od.reduce && !(a.lots.length && a.lots[0].dir === -od.dir)) { done.add(od.id); continue; }
      let fill = NaN;
      if (od.kind === 'mkt') fill = o;
      else if (od.kind === 'stop') { if (od.dir === 1 ? h >= od.price : l <= od.price) fill = od.dir === 1 ? Math.max(o, od.price) : Math.min(o, od.price); }
      else if (od.dir === 1 ? l <= od.price : h >= od.price) fill = od.dir === 1 ? Math.min(o, od.price) : Math.max(o, od.price);
      if (Number.isNaN(fill)) continue;
      const q = od.reduce ? Math.min(od.q, qtyOf()) : od.q;
      const m = applyFill(od.dir, q, fill, i, od.note, od.why);
      done.add(od.id);
      if (m) { R.msg = m; continue; }
      R.msg = '成交：' + (od.dir === 1 ? '買 ' : '賣 ') + U.fmt(q, 0) + ' @ ' + U.fmt(fill, 2);
      if (od.oca) a.orders.forEach((x) => { if (x.oca === od.oca && x.id !== od.id) done.add(x.id); });
      if (od.tp || od.sl) {      // 附停利停損：成交後掛 OCO 出場單（均價另算，用這次成交價）
        const oca = 'o' + od.id, opp = -od.dir;
        if (od.tp) a.orders.push({ id: a.nid++, dir: opp, kind: 'limit', price: fill * (1 + od.dir * od.tp / 100), q: od.q, reduce: true, oca, why: '停利', note: '' });
        if (od.sl) a.orders.push({ id: a.nid++, dir: opp, kind: 'stop', price: fill * (1 - od.dir * od.sl / 100), q: od.q, reduce: true, oca, why: '停損', note: '' });
      }
    }
    a.orders = a.orders.filter((x) => !done.has(x.id));
    for (const x of a.lots) { x.mfe = Math.max(x.mfe, x.dir === 1 ? h - x.p : x.p - l); x.mae = Math.max(x.mae, x.dir === 1 ? x.p - l : h - x.p); }
  }

  /* ---------------------------------------------------------------- 圖 */
  const bar = (i) => ({ time: U.ltime(R.B, i), open: R.B.o[i], high: R.B.h[i], low: R.B.l[i], close: R.B.c[i] });
  function buildChart(upto) {
    const el = U.$('#rpK'); if (!el) return;
    U.killChart('k');
    const B = R.B;
    // 全站 KChart：指標只用到目前這一根（kv.set(upto) 之後的資料根本沒送進圖裡，所以不可能洩漏未來）；繪圖工具照常可用
    const items = [{ id: 'ma', n: 5 }, { id: 'ma', n: 20 }, { id: 'ma', n: 60 }, { id: 'vol' }];
    const kv = new U.LabK.KView(el, B, { items, drawKey: 'tw.draw.lab.replay.' + R.sym + '.' + R.tf });
    U.CH.kv = kv; U.CH.k = kv.chart; U.CH.cs = kv.candle; R.kv = kv; R.series = { cs: kv.candle }; R.lines = [];
    R.times = []; R.tmap = {};
    for (let i = 0; i < B.n; i++) { const t = U.ltime(B, i); R.tmap[t] = i; if (i <= upto) R.times.push(t); }
    kv.set(upto, false); kv.enableDraw(U.$('#rpDraw'));
    kv.chart.applyOptions({ timeScale: { visible: !R.blind } });
    if (R.run) kv.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, upto - 100), to: upto + 8 }); else kv.chart.timeScale().fitContent();
    if (R.pick) kv.chart.subscribeClick((p) => { if (!R.pick || !p.time) return; const i = R.tmap[p.time]; if (i != null && i >= 30 && i < R.B.n - 1) startAt(i); });
    drawMarks(); drawLines();
  }
  function pushBar(i) {
    R.times.push(U.ltime(R.B, i));
    R.kv.set(i, true);        // 保留目前取景；KChart 只比對尾巴、單點更新
  }
  function drawMarks() {
    if (!R.kv) return; const c = U.pal(), a = A(); if (!a) return;
    const m = a.fills.map((f) => ({ time: U.ltime(R.B, f.i), position: f.dir === 1 ? 'belowBar' : 'aboveBar', shape: f.dir === 1 ? 'arrowUp' : 'arrowDown', color: f.dir === 1 ? c.rise : c.fall, text: (f.dir === 1 ? '買 ' : '賣 ') + (f.pnl != null ? U.compact(f.pnl) : ''), size: 1 }));
    m.sort((x, y) => (x.time < y.time ? -1 : x.time > y.time ? 1 : 0));
    R.kv.setMarkers(m);
  }
  function drawLines() {
    const cs = R.series.cs; if (!cs || !A()) return; const c = U.pal();
    R.lines.forEach((l) => { try { cs.removePriceLine(l); } catch (e) { /* 忽略 */ } }); R.lines = [];
    const a = A();
    if (a.lots.length) { const q = qtyOf(), avg = a.lots.reduce((s, x) => s + x.p * x.q, 0) / q; R.lines.push(cs.createPriceLine({ price: avg, color: a.lots[0].dir === 1 ? c.rise : c.fall, lineWidth: 1, lineStyle: 0, axisLabelVisible: false, title: (a.lots[0].dir === 1 ? '多 ' : '空 ') + q })); }
    a.orders.forEach((o) => { if (o.price) R.lines.push(cs.createPriceLine({ price: o.price, color: c.amber, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: (o.dir === 1 ? '買' : '賣') + (o.kind === 'limit' ? '限' : '停') })); });
  }

  /* ---------------------------------------------------------------- 流程 */
  function stop() { R.playing = false; if (R.timer) { clearInterval(R.timer); R.timer = null; } }
  function startAt(idx) {
    stop(); R.run = true; R.pick = false; R.start = idx; R.i = idx; R.snaps = []; R.msg = '';
    R.unit = R.B.c[idx] * 1000 > R.cap * 0.3 ? 'sh' : 'lot';      // 一張買不起的標的預設改用股數
    R.acct = newAcct(R.cap); R.eq = [equity(R.B.c[idx])];
    buildChart(idx); paint();
  }
  function step(render) {
    if (!R.run || R.i >= R.B.n - 1) { stop(); paint(); return false; }
    R.snaps.push(JSON.stringify({ a: R.acct, eq: R.eq.length, msg: R.msg }));
    R.i++;
    processBar(R.i);        // 成交或被拒的訊息會留在畫面上，直到下一次下單才清掉
    R.eq.push(equity(R.B.c[R.i]));
    if (render !== false) { pushBar(R.i); drawMarks(); drawLines(); try { U.CH.k.timeScale().scrollToRealTime(); } catch (e) { /* 忽略 */ } paint(); }
    if (R.i >= R.B.n - 1) { stop(); paint(); }
    return true;
  }
  function back() {
    if (!R.run || !R.snaps.length) return; stop();
    const s = JSON.parse(R.snaps.pop()); R.acct = s.a; R.eq.length = s.eq; R.i--; R.msg = s.msg || '';
    buildChart(R.i); paint();
  }
  function play() {
    if (!R.run) return;
    if (R.playing) { stop(); paint(); return; }
    if (R.i >= R.B.n - 1) return;
    R.playing = true; R.timer = setInterval(() => step(true), 1000 / SPEEDS[R.speed]); paint();
  }
  function toEnd() { if (!R.run) return; stop(); while (R.i < R.B.n - 1) step(false); buildChart(R.i); paint(); }
  function exitRun() { stop(); R.run = false; R.i = -1; R.acct = null; R.snaps = []; R.eq = []; R.msg = ''; buildChart(R.B.n - 1); paint(); }

  /* ---------------------------------------------------------------- 下單 */
  function order(dir) {
    if (!R.run) return;
    const a = A(), it = inst(), fut = it.kind === 'fut';
    const v = parseFloat(U.$('#rpQty').value), px = parseFloat(U.$('#rpPx').value);
    if (!(v > 0)) { R.msg = '請輸入數量'; return paint(); }
    const q = fut ? Math.floor(v) : (R.unit === 'lot' ? Math.floor(v * 1000) : Math.floor(v));
    if (q < 1) { R.msg = '數量太小'; return paint(); }
    if (R.kind !== 'mkt' && !(px > 0)) { R.msg = '請輸入價格'; return paint(); }
    const tp = parseFloat(U.$('#rpTp').value) || 0, sl = parseFloat(U.$('#rpSl').value) || 0;
    a.orders.push({ id: a.nid++, dir, kind: R.kind, price: R.kind === 'mkt' ? 0 : px, q, tp, sl, note: (U.$('#rpNote').value || '').slice(0, 60), why: '手動', reduce: false });
    R.msg = R.kind === 'mkt' ? '已送出，下一根開盤成交' : '委託已掛出，之後哪一根碰到價位就成交';
    drawLines(); paint();
  }
  function flatten() {
    if (!R.run || !A().lots.length) return;
    const a = A(); a.orders.push({ id: a.nid++, dir: -pos(), kind: 'mkt', price: 0, q: qtyOf(), note: '手動全部平倉', why: '手動平倉', reduce: true });
    R.msg = '已送出平倉，下一根開盤成交'; paint();
  }

  /* ---------------------------------------------------------------- 畫面 */
  const TABS = [['pos', '持倉'], ['ord', '委託'], ['his', '成交紀錄'], ['acc', '帳戶'], ['sc', '成績單']];
  function html() {
    return '<div class="lab-bar"><div class="lab-f lab-symw"><span>標的</span><input id="labSym" class="lab-in" type="text" autocomplete="off" spellcheck="false" aria-label="搜尋標的" placeholder="代號或名稱"><div class="lab-dd" id="labSymDD" hidden></div></div>' +
      '<div class="seg" id="rpTf" role="tablist" aria-label="時間週期">' + [['60', '60分'], ['D', '日'], ['W', '週']].map(([k, n]) => '<button type="button" role="tab" data-tf="' + k + '">' + n + '</button>').join('') + '</div>' +
      '<div class="rp-start" id="rpStart"><label class="lab-f"><span>起點</span><input class="lab-in" type="date" id="rpDate" aria-label="起點日期"></label><button type="button" class="lab-clear" id="rpGo">從這天開始</button><button type="button" class="lab-clear" id="rpRand">隨機</button><button type="button" class="lab-clear" id="rpPick">點圖選起點</button></div>' +
      '<button type="button" class="lab-gear lab-mxbtn" id="labMx" aria-expanded="false">設定</button><label class="lab-chk rp-blind lab-mx"><input type="checkbox" id="rpBlind"> 盲測（隱藏標的與日期）</label></div>' +
      '<div class="rp-ctl" id="rpCtl"><button type="button" class="lab-clear" id="rpBack" title="上一根（←）">◀ 上一根</button><button type="button" class="lab-gear on" id="rpPlay" title="播放／暫停（空白鍵）">▶ 播放</button><button type="button" class="lab-clear" id="rpNext" title="下一根（→）">下一根 ▶</button>' +
      '<div class="seg lab-mx" id="rpSpd" role="tablist" aria-label="播放速度">' + SPEEDS.map((v, k) => '<button type="button" role="tab" data-s="' + k + '">' + v + ' 根/秒</button>').join('') + '</div>' +
      '<button type="button" class="lab-clear lab-mx" id="rpEnd">跳到最新</button><button type="button" class="lab-clear lab-mx" id="rpExit">離開重播</button><span class="rp-now lab-mx" id="rpNow"></span></div>' +
      '<div class="rp-main"><div class="lab-kwrap"><div class="lab-draw lab-mx" id="rpDraw" aria-label="繪圖工具"></div><div class="lab-kc rp-kc"><div class="lab-ch" id="rpK"></div></div></div>' +
      '<div class="rp-ticket" id="rpTicket"></div></div>' +
      '<div class="rp-tabs"><div class="seg" id="rpTabs" role="tablist" aria-label="交易面板">' + TABS.map(([k, n]) => '<button type="button" role="tab" data-t="' + k + '">' + n + '</button>').join('') + '</div></div>' +
      '<div class="lab-tbody rp-panel" id="rpPanel"></div>';
  }
  function ticketHTML() {
    const it = inst(), fut = it.kind === 'fut', last = R.run ? R.B.c[R.i] : 0;
    return '<div class="rp-tk-h">模擬下單</div>' +
      '<label class="lab-fld"><span>數量</span><span class="rp-qr"><input class="lab-in" id="rpQty" type="number" min="1" step="1" value="' + (fut || R.unit === 'lot' ? 1 : Math.max(1, Math.floor(R.cap * 0.2 / (last || 1) / 10) * 10)) + '">' + (fut ? '<em>口</em>' : '<span class="seg" id="rpUnit" role="tablist" aria-label="單位"><button type="button" data-u="lot" class="' + (R.unit === 'lot' ? 'on' : '') + '">張</button><button type="button" data-u="sh" class="' + (R.unit === 'sh' ? 'on' : '') + '">股</button></span>') + '</span></label>' +
      '<div class="seg" id="rpKind" role="tablist" aria-label="委託類型">' + [['mkt', '市價'], ['limit', '限價'], ['stop', '停損']].map(([k, n]) => '<button type="button" role="tab" data-k="' + k + '" class="' + (R.kind === k ? 'on' : '') + '">' + n + '</button>').join('') + '</div>' +
      '<label class="lab-fld"><span>價格</span><input class="lab-in" id="rpPx" type="number" step="any" value="' + (last ? last : '') + '"' + (R.kind === 'mkt' ? ' disabled' : '') + '></label>' +
      '<div class="rp-two"><label class="lab-fld"><span>停利 %</span><input class="lab-in" id="rpTp" type="number" min="0" step="0.5" placeholder="不設"></label><label class="lab-fld"><span>停損 %</span><input class="lab-in" id="rpSl" type="number" min="0" step="0.5" placeholder="不設"></label></div>' +
      '<label class="lab-fld"><span>想法</span><input class="lab-in" id="rpNote" type="text" maxlength="60" placeholder="記下為什麼下這一單（選填）"></label>' +
      '<div class="rp-two"><button type="button" class="rp-buy" id="rpBuy">買進</button><button type="button" class="rp-sell" id="rpSell">' + (fut ? '賣出' : '賣出／放空') + '</button></div>' +
      '<button type="button" class="lab-clear" id="rpFlat">全部平倉</button><div class="rp-msg" id="rpMsg" role="status"></div>';
  }
  function paint() {
    const run = R.run, a = A();
    U.$('#rpStart').style.display = run ? 'none' : '';
    U.$('#rpCtl').style.display = run ? '' : 'none';
    U.$$('#rpTf button').forEach((b) => { b.classList.toggle('on', b.dataset.tf === R.tf); const it = (U.DATA.idx.items || []).find((x) => x.c === R.sym); b.disabled = b.dataset.tf === '60' && !(it && it.h60); b.title = b.disabled ? '此標的沒有 60 分 K（60 分資料只有 2023-09 之後、近期成交值前 500 名的個股）' : ''; });
    U.$$('#rpSpd button').forEach((b) => b.classList.toggle('on', +b.dataset.s === R.speed));
    const pl = U.$('#rpPlay'); pl.textContent = R.playing ? '⏸ 暫停' : '▶ 播放'; pl.disabled = !run || R.i >= R.B.n - 1;
    U.$('#rpBack').disabled = !run || !R.snaps.length; U.$('#rpNext').disabled = !run || R.i >= R.B.n - 1;
    const sym = U.$('#labSym'); if (sym && document.activeElement !== sym) { const it = (U.DATA.idx.items || []).find((x) => x.c === R.sym); sym.value = R.blind ? '？？？' : (it ? it.c + ' ' + it.n : R.sym); }
    const now = U.$('#rpNow');
    if (run) { const i = R.i, B = R.B; now.innerHTML = R.blind ? '第 ' + (i - R.start) + ' 根' : '<b>' + U.tstr(B, i) + '</b> 開 ' + U.fmt(B.o[i], 2) + ' 高 ' + U.fmt(B.h[i], 2) + ' 低 ' + U.fmt(B.l[i], 2) + ' 收 <b class="' + U.cls(B.c[i] - (i ? B.c[i - 1] : B.c[i])) + '">' + U.fmt(B.c[i], 2) + '</b>'; } else now.textContent = '';
    const tk = U.$('#rpTicket'); if (!tk.dataset.k || tk.dataset.k !== R.sym + R.kind + R.unit + (run ? 1 : 0)) { tk.innerHTML = ticketHTML(); tk.dataset.k = R.sym + R.kind + R.unit + (run ? 1 : 0); }
    tk.classList.toggle('off', !run);
    U.$$('#rpTicket input,#rpTicket button').forEach((e) => { if (e.id !== 'rpPx') e.disabled = !run; });
    const px = U.$('#rpPx'); if (px) px.disabled = !run || R.kind === 'mkt';
    const mg = U.$('#rpMsg'); if (mg) mg.textContent = run ? R.msg : '先選起點';
    U.$$('#rpTabs button').forEach((b) => b.classList.toggle('on', b.dataset.t === R.tab));
    panel();
  }
  function stats() {
    const a = A(), B = R.B, it = inst(), n = R.eq.length;
    const opens = a.lots.map((x) => { const c = B.c[R.i], gross = x.dir * (c - x.p) * x.q * it.mult; return { dir: x.dir, i0: x.i0, i1: R.i, p0: x.p, p1: c, qty: x.q, gross, costs: x.fee + x.tax, pnl: gross - x.fee - x.tax, pnlP: (gross - x.fee - x.tax) / (x.p * x.q * it.mult) * 100, bars: R.i - x.i0, mfe: 0, mae: 0, open: true, why: '未平倉', entryWhy: x.why }; });
    return { st: E.computeStats(B, a.trades.slice(), Float64Array.from(R.eq), { capital: a.cap, inst: it, sizeMode: 'units', sizeVal: 1 }, R.start, R.i, opens, a.maxQ), opens };
  }
  function panel() {
    const el = U.$('#rpPanel'); if (!el) return;
    const run = R.run, a = A(), B = R.B, it = inst(), u = it.kind === 'fut' ? '口' : '股';
    if (!run) { el.innerHTML = '<div class="lab-note">選好起點後，這裡會出現持倉、委託、成交紀錄、帳戶與這一輪的成績單。</div>'; return; }
    const c = B.c[R.i];
    if (R.tab === 'pos') {
      if (!a.lots.length) { el.innerHTML = '<div class="lab-note">目前空手</div>'; return; }
      const q = qtyOf(), avg = a.lots.reduce((s, x) => s + x.p * x.q, 0) / q, d = a.lots[0].dir, pnl = d * (c - avg) * q * it.mult;
      el.innerHTML = '<div class="lab-twrap"><table class="lab-tbl"><thead><tr><th>商品</th><th>方向</th><th>數量</th><th>均價</th><th>現價</th><th>未實現損益</th><th>報酬</th></tr></thead><tbody><tr><td>' + U.esc(R.blind ? '？？？' : R.sym) + '</td><td class="' + (d === 1 ? 'up' : 'dn') + '">' + (d === 1 ? '多' : '空') + '</td><td>' + U.fmt(q, 0) + ' ' + u + '</td><td>' + U.fmt(avg, 2) + '</td><td>' + U.fmt(c, 2) + '</td><td class="' + U.cls(pnl) + '">' + U.sgn(pnl, 0) + '</td><td class="' + U.cls(pnl) + '">' + U.sgn(d * (c / avg - 1) * 100, 2) + '%</td></tr></tbody></table></div>';
    } else if (R.tab === 'ord') {
      el.innerHTML = a.orders.length ? '<div class="lab-twrap"><table class="lab-tbl"><thead><tr><th>方向</th><th>類型</th><th>價格</th><th>數量</th><th>說明</th><th></th></tr></thead><tbody>' + a.orders.map((o) => '<tr><td class="' + (o.dir === 1 ? 'up' : 'dn') + '">' + (o.dir === 1 ? '買' : '賣') + '</td><td>' + ({ mkt: '市價', limit: '限價', stop: '停損' }[o.kind]) + '</td><td>' + (o.price ? U.fmt(o.price, 2) : '下一根開盤') + '</td><td>' + U.fmt(o.q, 0) + '</td><td>' + U.esc(o.why + (o.tp ? ' 停利' + o.tp + '%' : '') + (o.sl ? ' 停損' + o.sl + '%' : '')) + '</td><td><button type="button" class="lab-clear rp-cx" data-id="' + o.id + '">取消</button></td></tr>').join('') + '</tbody></table></div>' : '<div class="lab-note">沒有未成交的委託</div>';
    } else if (R.tab === 'his') {
      el.innerHTML = a.fills.length ? '<div class="lab-twrap"><table class="lab-tbl"><thead><tr><th>時間</th><th>動作</th><th>方向</th><th>價格</th><th>數量</th><th>費用</th><th>損益</th><th>想法</th></tr></thead><tbody>' + a.fills.slice().reverse().map((f) => '<tr><td>' + (R.blind ? '—' : U.tstr(B, f.i)) + '</td><td>' + f.kind + '</td><td class="' + (f.dir === 1 ? 'up' : 'dn') + '">' + (f.dir === 1 ? '買' : '賣') + '</td><td>' + U.fmt(f.p, 2) + '</td><td>' + U.fmt(f.q, 0) + '</td><td>' + U.fmt(f.fee, 0) + '</td><td class="' + U.cls(f.pnl) + '">' + (f.pnl == null ? '—' : U.sgn(f.pnl, 0)) + '</td><td title="' + U.esc(f.note) + '">' + U.esc(f.note.slice(0, 14)) + '</td></tr>').join('') + '</tbody></table></div>' : '<div class="lab-note">還沒有成交</div>';
    } else if (R.tab === 'acc') {
      const { st } = stats(), eq = R.eq[R.eq.length - 1], real = a.trades.reduce((s, t) => s + t.pnl, 0), T = (l, v, c2) => '<div class="lab-st"><span>' + l + '</span><b class="' + (c2 || '') + '">' + v + '</b></div>';
      el.innerHTML = '<div class="rp-acc">' + T('初始資金', U.fmt(a.cap, 0)) + T('權益', U.fmt(eq, 0), U.cls(eq - a.cap)) + T('帳上現金', U.fmt(a.cash, 0)) + T('已實現損益', U.sgn(real, 0), U.cls(real)) + T('未實現損益', U.sgn(eq - a.cap - real, 0), U.cls(eq - a.cap - real)) + T('費用合計', U.fmt(a.comm, 0)) + T('報酬率', U.sgn((eq / a.cap - 1) * 100, 2) + '%', U.cls(eq - a.cap)) + T('最大回撤', '−' + st.mddP.toFixed(2) + '%', st.mdd > 0 ? 'dn' : '') + '</div><div class="rp-reset"><label class="lab-fld"><span>初始資金</span><input class="lab-in" id="rpCap" type="number" step="10000" value="' + R.cap + '"></label><button type="button" class="lab-clear" id="rpReset">重設帳戶（回到起點重新開始）</button></div>';
    } else {
      const { st, opens } = stats();
      el.innerHTML = U.summaryHTML({ res: { stats: st }, cfg: { capital: a.cap }, sym: R.sym });
      void opens;
    }
  }

  /* ---------------------------------------------------------------- 載入與綁定 */
  async function setSym(code, tf) {
    stop(); R.run = false; R.i = -1; R.acct = null; R.snaps = []; R.eq = []; R.pick = false; R.inst = null;
    const items = (U.DATA.idx || {}).items || [], it = items.find((x) => x.c === code); if (!it) return;
    R.sym = code; R.tf = tf || (R.tf === '60' && !it.h60 ? 'D' : R.tf);
    R.B = await U.loadSeries(code, R.tf);
    if (!R.B && R.tf !== 'D') { R.tf = 'D'; R.B = await U.loadSeries(code, 'D'); }
    if (!R.B) return;
    const last = R.B.n - 1; const d = U.$('#rpDate'); if (d) { d.min = U.E.dayToStr(R.B.day[30]); d.max = U.E.dayToStr(R.B.day[last - 1]); d.value = U.E.dayToStr(R.B.day[Math.max(30, last - 250)]); }
    buildChart(last); paint();
  }
  function startFromDate() {
    const v = U.$('#rpDate').value; if (!v) return;
    const d = E.strToDay(v); let k = R.B.n - 2;
    for (let i = 30; i < R.B.n - 1; i++) if (R.B.day[i] >= d) { k = i; break; }
    startAt(k);
  }
  function key(e) {
    if (!R.run || e.target.closest('input,select,textarea')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); step(true); } else if (e.key === 'ArrowLeft') { e.preventDefault(); back(); } else if (e.key === ' ') { e.preventDefault(); play(); }
  }
  async function mount(body, util) {
    U = util; E = U.E; R = fresh();
    body.innerHTML = html();
    body.onclick = async (e) => {
      const t = e.target;
      const tf = t.closest('#rpTf button'); if (tf && !tf.disabled) { await setSym(R.sym, tf.dataset.tf); return; }
      const di = t.closest('.lab-di'); if (di) { U.$('#labSymDD').hidden = true; await setSym(di.dataset.c); return; }
      const mxb = t.closest('#labMx'); if (mxb) { U.toggleMx(body, mxb); return; }
      if (t.closest('#rpGo')) return startFromDate();
      if (t.closest('#rpRand')) { startAt(30 + Math.floor(Math.random() * Math.max(1, R.B.n - 90))); return; }
      if (t.closest('#rpPick')) { R.pick = !R.pick; buildChart(R.B.n - 1); U.$('#rpPick').classList.toggle('on', R.pick); R.msg = ''; return; }
      if (t.closest('#rpPlay')) return play();
      if (t.closest('#rpNext')) { stop(); step(true); return; }
      if (t.closest('#rpBack')) return back();
      if (t.closest('#rpEnd')) return toEnd();
      if (t.closest('#rpExit')) return exitRun();
      const sp = t.closest('#rpSpd button'); if (sp) { R.speed = +sp.dataset.s; if (R.playing) { stop(); play(); } else paint(); return; }
      const k = t.closest('#rpKind button'); if (k) { R.kind = k.dataset.k; U.$('#rpTicket').dataset.k = ''; paint(); return; }
      const un = t.closest('#rpUnit button'); if (un) { R.unit = un.dataset.u; U.$('#rpTicket').dataset.k = ''; paint(); return; }
      if (t.closest('#rpBuy')) return order(1);
      if (t.closest('#rpSell')) return order(-1);
      if (t.closest('#rpFlat')) return flatten();
      const tb = t.closest('#rpTabs button'); if (tb) { R.tab = tb.dataset.t; paint(); return; }
      const cx = t.closest('.rp-cx'); if (cx) { const a = A(); a.orders = a.orders.filter((o) => o.id !== +cx.dataset.id); drawLines(); paint(); return; }
      if (t.closest('#rpReset')) { startAt(R.start); return; }
    };
    body.oninput = (e) => {
      const t = e.target;
      if (t.id === 'labSym') { const dd = U.$('#labSymDD'), list = U.searchItems(t.value.replace(/^\S+\s/, '')); dd.innerHTML = list.map((x) => '<button type="button" class="lab-di" data-c="' + U.esc(x.c) + '"><b>' + U.esc(x.c) + '</b> ' + U.esc(x.n) + (U.KIND_N[x.k] ? ' <small>' + U.KIND_N[x.k] + '</small>' : '') + '</button>').join('') || '<div class="lab-note">找不到符合的標的</div>'; dd.hidden = false; return; }
      if (t.id === 'rpBlind') { R.blind = t.checked; const wr = U.$('#rpK'); if (wr) wr.classList.toggle('rp-blindon', R.blind); if (R.B) { buildChart(R.run ? R.i : R.B.n - 1); paint(); } return; }
      if (t.id === 'rpCap') { const v = parseFloat(t.value); if (v > 0) R.cap = v; }
    };
    body.onfocusin = (e) => { if (e.target.id === 'labSym') { e.target.select(); e.target.dispatchEvent(new Event('input', { bubbles: true })); } };
    document.addEventListener('keydown', key); R.keyBound = true;
    await setSym(R.sym, 'D');
  }
  function unmount() { stop(); document.removeEventListener('keydown', key); }
  L.register({ id: 'replay', name: 'K 線重播', ord: 30, mount, unmount, reset() { R = fresh(); },
    state: () => R, api: { startAt, step, back, order, processBar, applyFill, newAcct, fresh: () => { R = fresh(); return R; }, get R() { return R; } } });
}());
