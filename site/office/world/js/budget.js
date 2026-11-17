// 今日預算（2026-11-16，研究報告 docs/ai_office/game_basics_gap.md 第 10 項：用量額度當遊戲幣）
//
// 做什麼：頂列一條「今日預算」：今天這個專案用掉多少 Token（收件服務 /v1/office/<id>/usage 彙總，外掛 bridge.py 送的 usage_main／usage_subagents；
//   取不到時收件服務以工具呼叫次數推估，畫面標「估算」）÷ 使用者自己在設定填的每日上限。
//   · 用到 80%：跳一次提醒（同一天同一專案只提醒一次）
//   · 超過上限：辦公室整片變暗，並寫明「不會擋你的 Claude」
// ★ 絕不擋使用者的 Claude：這支只讀用量、只改畫面；網站本身不呼叫 Claude、不送任何指令。
// 每日上限存在 localStorage 的 aiOffice.game.budget（{ daily: <Token 數> }），所以會跟著雲端存檔（save.js）一起同步到別台裝置。
// 功能閘門：features.js 的 office.budget（開關；訪客不開放）。
// 網址參數（驗收用）：budget_poll=<毫秒> 改讀用量的間隔（預設 60 秒）。
// 接法：world.html 在 main.js 之後加 <script type="module" src="world/js/budget.js"></script>。

const KEY = 'aiOffice.game.budget', WARN = 'aiOffice.budget.warned', ACCT_TOK = 'tw.acct.tok';
const qs = new URLSearchParams(location.search);
const POLL = Math.max(300, +qs.get('budget_poll') || 60000);
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); return true; } catch (e) { return false; } };
export const fmtTok = n => { n = Math.max(0, n || 0); if (n >= 1e8) return (n / 1e8).toFixed(n >= 1e9 ? 0 : 1) + ' 億'; if (n >= 1e4) return (n / 1e4).toFixed(n >= 1e6 ? 0 : 1).replace(/\.0$/, '') + ' 萬'; return String(Math.round(n)); };

function boot(W) {
  const L = W.live || {};
  const B = { used: 0, est: false, tools: 0, day: '', daily: 0, pct: 0, level: 'none', ok: false, polls: 0, err: '' };
  W.budget = B;
  const readLimit = () => { try { const o = JSON.parse(lsGet(KEY) || 'null'); return o && Number.isFinite(o.daily) && o.daily > 0 ? o.daily : 0; } catch (e) { return 0; } };
  B.daily = readLimit();

  const css = document.createElement('style'); css.id = 'budgetCss';
  css.textContent = `#budgetBtn{gap:8px;padding:0 10px;font-size:12.5px}
#budgetBtn .tr{position:relative;width:74px;height:8px;border-radius:5px;background:rgba(0,0,0,.09);overflow:hidden;flex:none}
#budgetBtn .tr .fl{position:absolute;left:0;top:0;bottom:0;width:0;border-radius:5px;background:#35b36b;transition:width .4s}
#budgetBtn.warn .tr .fl{background:#f2a93b}#budgetBtn.over .tr .fl{background:#c2590c}
#budgetBtn .tx{white-space:nowrap;color:var(--sub,#7a6f66)}#budgetBtn .tx b{color:var(--ink,#3b302a);font-weight:700}
#budgetPop{width:300px;font-size:13.5px;line-height:1.55}#budgetPop h4{margin:2px 4px 6px;font-size:15px}
#budgetPop p{margin:4px 4px 8px;color:var(--sub,#7a6f66);font-size:12.5px}
#budgetPop .row{display:flex;gap:6px;align-items:center;margin:6px 4px}#budgetPop input{font:inherit;width:100px;border:1px solid var(--line,#e3d9cf);border-radius:10px;padding:5px 8px}
#budgetPop .row .btn{box-shadow:none;border:1px solid var(--line,#e3d9cf);height:32px;padding:0 12px}
#budgetDim{position:absolute;inset:0;background:rgba(18,20,42,.14);pointer-events:none;z-index:5;opacity:0;transition:opacity .8s}
#budgetDim.on{opacity:1}
body.budget-over #cv{filter:brightness(.86) saturate(.8);transition:filter .8s}
#budgetNote{position:absolute;left:50%;top:132px;transform:translateX(-50%);z-index:11;background:rgba(30,30,52,.9);color:#fff;border-radius:14px;padding:8px 14px;font-size:13px;max-width:calc(100vw - 32px);text-align:center;line-height:1.5}
@media (max-width:640px){#budgetBtn .tr{width:44px}#budgetBtn{order:21;font-size:11.5px;padding:0 8px;gap:5px}#budgetBtn .lb{display:none}#budgetPop{width:calc(100vw - 32px)}#budgetNote{font-size:12px;top:140px}}`;
  document.head.append(css);
  const app = document.getElementById('app') || document.body, bar = document.getElementById('bar');
  const btn = document.createElement('button'); btn.className = 'btn'; btn.id = 'budgetBtn'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-label', '今日預算（點開可設定每日上限）');
  btn.innerHTML = '<span class="lb">今日預算</span><span class="tr"><b class="fl"></b></span><span class="tx"></span>';
  const pop = document.createElement('div'); pop.className = 'pop'; pop.id = 'budgetPop'; pop.hidden = true;
  const dim = document.createElement('div'); dim.id = 'budgetDim';
  const note = document.createElement('div'); note.id = 'budgetNote'; note.hidden = true; note.setAttribute('role', 'status');
  const cv = document.getElementById('cv'); if (cv && cv.parentNode === app) cv.after(dim); else app.prepend(dim);
  app.append(note, pop); if (bar) bar.append(btn);

  const gateOff = () => { const g = W.gate ? W.gate.peek('office.budget') : { pass: true }; return !g.pass; };
  function render() {
    btn.hidden = gateOff(); if (btn.hidden) { dim.classList.remove('on'); note.hidden = true; return; }
    const lim = B.daily; B.pct = lim ? B.used / lim : 0;
    B.level = !lim ? 'none' : B.pct > 1 ? 'over' : B.pct >= 0.8 ? 'warn' : 'ok';
    btn.classList.toggle('warn', B.level === 'warn'); btn.classList.toggle('over', B.level === 'over');
    btn.querySelector('.tr .fl').style.width = (lim ? Math.min(100, B.pct * 100) : 0).toFixed(1) + '%';
    const est = B.est ? '（估算）' : '';
    btn.querySelector('.tx').innerHTML = !B.ok && !B.used ? '尚未連上' : lim ? `<b>${fmtTok(B.used)}</b>／${fmtTok(lim)}${est}` : `<b>${fmtTok(B.used)}</b> Token${est}・設定上限`;
    btn.title = `今天用掉 ${Math.round(B.used).toLocaleString('zh-TW')} Token${B.est ? '（含估算：取不到 Token 的工作階段以工具呼叫次數推估）' : ''}${lim ? `，每日上限 ${Math.round(lim).toLocaleString('zh-TW')}` : ''}`;
    dim.classList.toggle('on', B.level === 'over'); document.body.classList.toggle('budget-over', B.level === 'over');
    if (B.level === 'over') { note.hidden = false; note.textContent = `今日預算用完了（${fmtTok(B.used)}／${fmtTok(lim)}），辦公室先暗下來提醒你。這不會擋你的 Claude，它照常工作。`; }
    else note.hidden = true;
    // 80% 提醒：同一天、同一專案只跳一次
    if (B.level === 'warn' || B.level === 'over') {
      const k = (B.day || '') + ':' + (L.qProject || 'main') + ':' + B.level;
      let seen = ''; try { seen = sessionStorage.getItem(WARN) || lsGet(WARN) || ''; } catch (e) { seen = lsGet(WARN) || ''; }
      if (!seen.split('|').includes(k)) {
        const v = [k, ...seen.split('|').filter(Boolean)].slice(0, 6).join('|'); lsSet(WARN, v); try { sessionStorage.setItem(WARN, v); } catch (e) { /* 略 */ }
        if (W.ui && W.ui.toast) W.ui.toast(B.level === 'warn' ? `今日預算已用到 ${Math.floor(B.pct * 100)}%，留意一下用量` : '今日預算用完了，辦公室先暗下來（不影響你的 Claude）');
        B.warned = (B.warned || 0) + 1;
      }
    }
  }
  function openPop() {
    const lim = B.daily;
    pop.innerHTML = `<h4>今日預算</h4><p>今天這個專案用掉 <b>${fmtTok(B.used)}</b> Token${B.est ? '（含估算）' : ''}${B.tools ? `，工具呼叫 ${B.tools} 次` : ''}。</p>
<label class="row">每日上限 <input id="budgetIn" type="number" min="0" step="1" inputmode="numeric" value="${lim ? Math.round(lim / 1e4) : ''}" placeholder="例如 50"> 萬 Token</label>
<p>用到 80% 會提醒；超過時辦公室變暗。只是提醒，不會擋你的 Claude。</p>
<div class="row"><button class="btn" id="budgetSave">儲存</button><button class="btn" id="budgetClear">不設上限</button></div>`;
    pop.hidden = false; btn.setAttribute('aria-expanded', 'true');
    const r = btn.getBoundingClientRect(); pop.style.position = 'absolute'; pop.style.top = (r.bottom + 6) + 'px'; pop.style.left = Math.max(16, Math.min(innerWidth - pop.offsetWidth - 16, r.left)) + 'px';
    pop.querySelector('#budgetSave').onclick = () => { const v = +pop.querySelector('#budgetIn').value; setLimit(v > 0 ? v * 1e4 : 0); closePop(); };
    pop.querySelector('#budgetClear').onclick = () => { setLimit(0); closePop(); };
  }
  function closePop() { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
  function setLimit(t) { B.daily = t; lsSet(KEY, t ? JSON.stringify({ daily: t }) : null); render(); if (W.ui && W.ui.toast) W.ui.toast(t ? `每日上限設為 ${fmtTok(t)} Token` : '已取消每日上限'); }
  B.setLimit = setLimit;
  btn.onclick = e => { e.stopPropagation(); if (pop.hidden) openPop(); else closePop(); };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !pop.contains(e.target) && e.target !== btn && !btn.contains(e.target)) closePop(); });

  async function poll() {
    B.daily = readLimit();
    let u = ''; try { u = L.resolveUrl ? await L.resolveUrl() : ''; } catch (e) { u = ''; }
    const h = L.code ? { Authorization: 'Bearer ' + L.code } : lsGet(ACCT_TOK) ? { 'X-AIO-Session': lsGet(ACCT_TOK) } : null;
    if (u && h) {
      try {
        const office = (L.cfg && /^[A-Za-z0-9_-]{1,40}$/.test(L.cfg.office || '') && !/^o_/.test(L.cfg.office)) ? L.cfg.office : 'main';
        const r = await fetch(u + '/v1/office/' + office + '/usage' + (L.qProject ? '?project=' + L.qProject : ''), { headers: h, credentials: 'omit', cache: 'no-store' });
        const j = r.ok ? await r.json() : null;
        if (j && j.ok && j.today_usage) { B.ok = true; B.err = ''; B.day = j.today; B.used = j.today_usage.tokens || 0; B.est = !!j.today_usage.estimated; B.tools = j.today_usage.tools || 0; }
        else B.err = 'http' + r.status;
      } catch (e) { B.err = 'net'; }
    }
    B.polls++; render();
  }
  B.poll = poll;
  addEventListener('storage', e => { if (e.key === KEY) { B.daily = readLimit(); render(); } });
  render(); poll(); setInterval(poll, POLL);
}

{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.live) { clearInterval(t); boot(W); } else if (++n > 300) clearInterval(t); }, 100); }
