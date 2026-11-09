/* ============================================================================
   風險警示牌（site/riskflag.js）—— P-1107-02，Andy 2026-11-09 點頭（「02 05 03 04 06」）
   ----------------------------------------------------------------------------
   交易所公布的注意股／處置股（上市＋上櫃），資料 data/risk_flags.json（pipeline/compute/risk.py）。
   三個地方：
     ① 個股頁：K 線卡名稱區下方一條琥珀色警示條 #riskBar（手機：#skHead 被藏時改插在 K 線卡最上面）
        「處置中：11/09～11/13・約每二分鐘撮合一次・預收款券」／「即將處置：…」
        「注意股：11/06 公布・<交易所寫的原因>・近 10 個交易日被列注意 N 次」
     ② 自選清單（#watch 頁、右側自選面板、手機首頁觀察清單）：名稱旁小角標「處置」「注意」
     ③ 族群頁（#industry/group/<gid>）：族群分頁列最右邊一顆「本族群 N 檔處置中・M 檔注意」
   規矩（提案法遵段）：
     · 只轉述公告原文（日期、期間、撮合方式、原因），不寫買賣意見，不寫「避開」「危險」；顏色只用琥珀（--amber），不用紅綠。
     · 「近 10 個交易日被列注意 N 次」由公告直接數（build 端），不推算處置門檻；湖從 since 才開始存，晚於視窗起點就寫「本站自 M/D 起記錄」。
     · 處置中／即將處置用讀者當下的台北日期比 start／end（JSON 隔週末也不會把已結束的當成處置中）。
     · 交易所「公布注意暨處置專區」只寫名稱給讀者自己去查，不連、不爬。
   功能鍵 risk.flag（features.js）：四個方案全開、不計次；被管理者在 #admin/perm 關掉時警示條、角標、族群計數三樣都不畫。
   不改 industry.js／watchpage.js／watchlists.js／mobile3.js：用一個 MutationObserver 在它們畫完之後補上（換股、重畫都會再補）。
   ⚠ 測試可設 window.TW_RISK_TODAY='YYYY-MM-DD' 固定「今天」。
   ============================================================================ */
(function () {
  'use strict';
  const EMPTY = { stocks: {}, groups: {}, window: [] };
  let D = null, loading = null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const today = () => window.TW_RISK_TODAY || new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);
  const md = (d) => (d ? `${+d.slice(5, 7)}/${+d.slice(8, 10)}` : '—');
  const allowed = () => { const P = window.TwPerm; try { return !P || P.can('risk.flag'); } catch (e) { return true; } };

  function load() {
    if (D) return Promise.resolve(D);
    if (!loading) {
      /* 走 App.load（跟全站同一個版本鍵與離線存檔）；App 還沒掛好就等一下，最多 6 秒後改直接抓 */
      const waitApp = new Promise((res) => { let n = 0; const t = () => (window.App && window.App.load) || ++n > 20 ? res(window.App) : setTimeout(t, 300); t(); });
      loading = waitApp.then((A) => (A && A.load ? A.load('risk_flags', { fallback: null, low: true })
        : fetch('data/risk_flags.json').then((r) => (r.ok ? r.json() : null))))
        .then((d) => { D = d && d.stocks ? d : EMPTY; return D; }, () => { D = EMPTY; return D; });
    }
    return loading;
  }

  /* 這一檔現在要顯示什麼：處置（進行中優先，其次即將開始）＋注意（近 10 個交易日內）*/
  function info(code) {
    const e = D && D.stocks && D.stocks[code]; if (!e) return null;
    const t = today();
    const ps = (e.punish || []).filter((x) => x.end && x.end >= t)
      .sort((a, b) => String(a.start || '').localeCompare(String(b.start || '')));
    const on = ps.find((x) => !x.start || x.start <= t), soon = ps.find((x) => x.start && x.start > t);
    const p = on || soon || null;
    const n = e.notice && e.notice.last ? e.notice : null;
    if (!p && !n) return null;
    return { name: e.name, market: e.market, punish: p, pState: p ? (on ? 'on' : 'soon') : null, notice: n };
  }

  /* ---------------------------------------------------------------- ① 個股頁警示條 */
  function barHTML(code, it) {
    const rows = [];
    if (it.punish) {
      const p = it.punish;
      const bits = [`期間 ${md(p.start)}～${md(p.end)}`];
      if (p.match) bits.push(esc(p.match));
      if (p.prepay) bits.push('預收款券');
      if (p.measure) bits.push(esc(p.measure));
      rows.push(`<div class="rk-row" data-rk="punish"><b class="rk-tag">${it.pState === 'on' ? '處置中' : '即將處置'}</b><span class="rk-t">${bits.join('・')}<span class="rk-sub">（${md(p.date)} 公布）</span></span></div>`);
    }
    if (it.notice) {
      const n = it.notice, since = D.since, w = D.window || [];
      const partial = since && w.length && since > w[0];
      const cnt = `近 10 個交易日被列注意 ${n.n10} 次${partial ? `（本站自 ${md(since)} 起記錄）` : ''}`;
      rows.push(`<div class="rk-row" data-rk="notice"><b class="rk-tag">注意股</b><span class="rk-t">${md(n.last)} 公布・<span class="rk-n">${cnt}</span>${n.reason ? `・<span class="rk-why" title="${esc(n.reason)}">${esc(n.reason)}</span>` : ''}</span></div>`);
    }
    return `<div class="rk-rows">${rows.join('')}</div>
      <button class="howbtn pop" data-how="risk" data-ttl="注意股／處置股" type="button" aria-label="注意股／處置股說明">?</button>
      <div class="howtxt" id="how-risk" hidden>${window.App && window.App.howHTML ? window.App.howHTML('交易所公布的注意股、處置股', [
        '資料：證交所與櫃買中心每日公告（上市＋上櫃）',
        '處置期間、撮合方式照公告原文',
        '注意次數只數公告，不推算處置門檻',
        '完整公告：交易所「公布注意暨處置專區」',
      ]) : ''}</div>`;
  }
  function paintStock(on) {
    const m = /^#stock\/([^/?]+)/.exec(location.hash || '');
    const old = document.getElementById('riskBar');
    if (!m || !on) { if (old) old.remove(); return; }
    const code = decodeURIComponent(m[1]);
    const card = document.getElementById('skChartCard');
    if (!card) return;
    /* 換股時舊的 K 線卡還留在畫面上、新的還在載：卡上的報價格（data-lc）還是上一檔就先不畫，等新卡畫好（MutationObserver 會再叫）*/
    const own = card.querySelector('[data-lc]');
    if (own && own.dataset.lc !== code) { if (old) old.remove(); return; }
    const it = info(code);
    if (!it) { if (old) old.remove(); return; }
    if (old && old.dataset.code === code && card.contains(old)) return;
    if (old) old.remove();
    const bar = document.createElement('div');
    bar.id = 'riskBar'; bar.className = 'riskbar'; bar.dataset.code = code; bar.setAttribute('role', 'note');
    bar.innerHTML = barHTML(code, it);
    /* 放不下時文字截斷（手機兩行）：點文字展開全文、再點收起 */
    bar.querySelectorAll('.rk-t').forEach((t) => { t.onclick = () => t.classList.toggle('open'); });
    const head = document.getElementById('skHead');
    if (head && card.contains(head) && head.getClientRects().length) head.after(bar);
    else card.prepend(bar);
  }

  /* ---------------------------------------------------------------- ② 自選清單角標 */
  function badge(code) {
    const it = info(code); if (!it) return '';
    const k = it.punish ? 'punish' : 'notice';
    const txt = it.punish ? (it.pState === 'on' ? '處置' : '將處置') : '注意';
    const tip = it.punish ? `${it.pState === 'on' ? '處置中' : '即將處置'}：${md(it.punish.start)}～${md(it.punish.end)}` : `注意股：${md(it.notice.last)} 公布`;
    return `<span class="rkb" data-rk="${k}" title="${esc(tip)}">${txt}</span>`;
  }
  function paintWatch(on) {
    const spots = [['#wpTbl tr[data-go]', '.t small.num'], ['#wlList li[data-go]', '.nm small.num'], ['#mbWatch .mbw[data-go]', '.mbwn']];
    for (const [rowSel, at] of spots) {
      document.querySelectorAll(rowSel).forEach((row) => {
        const code = row.dataset.go, cur = row.querySelector('.rkb');
        const want = on ? badge(code) : '';
        if (cur && cur.outerHTML === want) return;
        if (cur) cur.remove();
        if (!want) return;
        const anchor = row.querySelector(at);
        if (anchor) anchor.insertAdjacentHTML('afterend', want);
      });
    }
  }

  /* ---------------------------------------------------------------- ③ 族群頁計數 */
  function paintGroup(on) {
    const m = /^#industry\/group\/([^/?]+)/.exec(location.hash || '');
    const pick = document.getElementById('dgPick');
    const old = document.getElementById('riskGrp');
    if (!m || !pick || !on) { if (old) old.remove(); return; }
    const gid = decodeURIComponent(m[1]);
    const codes = (D.groups && D.groups[gid]) || [];
    /* 一檔只算一類：處置中 ＞ 即將處置 ＞ 注意（處置股多半也被列過注意，不重複算）*/
    let np = 0, ns = 0, nn = 0;
    codes.forEach((c) => { const it = info(c); if (!it) return; if (it.pState === 'on') np += 1; else if (it.pState === 'soon') ns += 1; else nn += 1; });
    if (!np && !ns && !nn) { if (old) old.remove(); return; }
    const txt = [np ? `${np} 檔處置中` : '', ns ? `${ns} 檔即將處置` : '', nn ? `${nn} 檔注意` : ''].filter(Boolean).join('・');
    const tip = codes.map((c) => { const it = info(c); if (!it) return ''; const s = (D.stocks[c] || {}).name || c;
      return `${s} ${c}：${it.punish ? (it.pState === 'on' ? '處置中' : '即將處置') : '注意股'}`; }).filter(Boolean).join('\n');
    const html = `<span class="rkgrp" id="riskGrp" data-gid="${esc(gid)}" data-np="${np}" data-ns="${ns}" data-nn="${nn}" title="${esc(tip)}">本族群 ${txt}</span>`;
    if (old && old.outerHTML === html && pick.contains(old)) return;
    if (old) old.remove();
    pick.insertAdjacentHTML('beforeend', html);
  }

  let dbg = { n: 0 };
  function paint() {
    if (!D) return;
    const on = allowed();
    dbg = { n: dbg.n + 1, on, h: location.hash, card: !!document.getElementById('skChartCard'), at: Date.now() };
    paintStock(on);
    paintWatch(on);
    paintGroup(on);
  }

  let qd = 0;
  /* 用 setTimeout 不用 requestAnimationFrame：分頁在背景或主執行緒忙（換股時圖表一直在畫）時 rAF 會被延後好幾秒，
     實測警示條晚 8 秒才出現（11-09 驗收段落抓到）。50ms 內的多次變動合併成一次。*/
  function queue() { if (qd) return; qd = setTimeout(() => { qd = 0; try { paint(); } catch (e) { dbg.err = String(e && e.stack || e).slice(0, 300); /* 標示失敗不影響頁面 */ } }, 50); }
  const RELEVANT = /^#(stock\/|watch|industry\/group\/)/;
  function boot() {
    load().then(queue);
    window.addEventListener('hashchange', queue);
    window.addEventListener('tw:watch', queue);
    window.addEventListener('tw:perm', queue);
    /* 個股頁換股、自選清單重畫、族群分頁重畫都是整塊 innerHTML 換掉：畫完之後補上。
       只在三種相關路由或右側自選面板開著時才做事（其他頁幾乎零成本）。 */
    new MutationObserver(() => {
      if (RELEVANT.test(location.hash || '') || document.getElementById('wlList') || document.getElementById('mbWatch')) queue();
    }).observe(document.body, { childList: true, subtree: true });
  }
  window.TwRisk = { load, info, paint: queue, _d: () => D, _reset: () => { D = null; loading = null; }, _dbg: () => dbg };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
