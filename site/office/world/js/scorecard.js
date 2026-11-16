// 單件成績單（2026-11-16，第二輪參考研究 docs/ai_office/game_basics_gap_round2.md 第 4 項：Game Dev Tycoon 類「成品評分卡」）
//
// 做什麼：每一件派工完成（SubagentStop）時產生一張成績單：誰做的、做了什麼、耗時、用量、被退幾次、測試有沒有跑、結果。
//   · 入口：頂列「成績單」鈕（有新卡會有小紅點）、員工資訊卡裡「最近成績單」那一行、總覽通知「完成」那一則（點下去會開對應的那一張）。
//   · 歷史清單：面板裡可翻上一件／下一件，或切到清單挑一張；存在 localStorage 的 aiOffice.game.scorecards（最多 50 張，雲端存檔會跟著帶）。
//
// 為什麼只靠 state.on 聽事件、不改 jobs.js：
//   派工演出（jobs.js）與資訊卡、通知（ui.js、overview.js）都有別的同事在改；這裡只「看事件」，事件格式見 state.js 檔頭，對方怎麼改都不會壞。
//   資訊卡用包住 ui.showCard 的方式插一行（跟 growth_ui.js 同一種做法）；存在才接、找不到就略過。
//
// 數字怎麼來（鐵則：沒有的資料就寫「沒有提供」，不補假數字）：
//   · 耗時＝SubagentStop 的 ts − SubagentStart 的 ts（事件自帶的時間，所以離線後補收的歷史事件也算得對）。
//   · 用量＝這一件期間該 Agent 的工具呼叫次數（PreToolUse 帶 agent_id 的）。這是「估算」：收件端沒有逐件的 Token 數；
//     事件若自帶 tokens／usage_tokens 才顯示實際 Token。
//   · 被退次數＝同一位同事、同一個任務標題，在這次做好之前連續「沒做成」了幾次（失敗的那張卡也標第幾次沒過）。
//   · 測試＝這一件期間有沒有跑測試類工具、跑了幾次；結果以交件成功／失敗為準，事件本身不帶測試通過與否，所以不寫「測試全過」。
// 重播用的事件序列（每個工具呼叫距開工幾毫秒）也存在卡裡，replay.js 讀它。
// 功能閘門：features.js 的 office.scorecard（開關）。文案禁用字見 gate.js 檔頭。

const LSK = 'aiOffice.game.scorecards', MAXC = 50, MAXEV = 60;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };
const CAT_ZH = { read: '讀資料', write: '寫程式', search: '查資料', test: '跑測試', deploy: '部署', wait: '等部署', other: '其他' };
const f2 = new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', hourCycle: 'h23', hour: '2-digit', minute: '2-digit' });
const hhmm = ms => f2.format(new Date(ms));
export const durText = ms => { const s = Math.max(0, Math.round(ms / 1000)); if (s < 60) return s + ' 秒'; const m = Math.floor(s / 60), r = s % 60; if (m < 60) return m + ' 分' + (r ? ' ' + r + ' 秒' : ''); const h = Math.floor(m / 60); return h + ' 小時' + (m % 60 ? ' ' + (m % 60) + ' 分' : ''); };

function boot(W) {
  const S = W.state, SC = { cards: [], running: new Map(), idx: 0, open: false, mode: 'card', toasted: 0 };
  W.scorecard = SC;
  const gateOk = () => { try { return !W.gate || W.gate.peek('office.scorecard').pass; } catch (e) { return true; } };
  SC.gateOk = gateOk;
  const nameOf = id => { const c = W.chars.get(id); return c ? { nick: c.spec.nick || id, zh: c.spec.zh || '' } : { nick: id || '同事', zh: '' }; };

  // ───────── 存取 ─────────
  try { const o = JSON.parse(lsGet(LSK) || 'null'); if (o && Array.isArray(o.cards)) SC.cards = o.cards.filter(x => x && x.id && x.t1).slice(0, MAXC); } catch (e) { /* 壞掉就從頭 */ }
  const save = () => lsSet(LSK, JSON.stringify({ v: 1, cards: SC.cards.slice(0, MAXC) }));
  addEventListener('storage', e => { if (e.key === LSK) { try { const o = JSON.parse(e.newValue || 'null'); if (o && Array.isArray(o.cards)) { SC.cards = o.cards.slice(0, MAXC); paintBtn(); if (SC.open) paint(); } } catch (x) { /* 略 */ } } });

  // ───────── 聽事件：開工、工具、交件 ─────────
  const keyOf = e => e.agent_id || ('t:' + (e.agent_type || ''));
  const normTitle = t => String(t || '').replace(/\s+/g, ' ').trim();
  S.on(e => {
    if (e.name === 'SubagentStart') {
      SC.running.set(keyOf(e), { key: keyOf(e), t0: e.ts, title: normTitle(e.description) || '新任務', type: e.agent_type || '', tools: [], cats: {}, aid: e.agent_id || null });
    } else if (e.name === 'PreToolUse' && e.agent_id) {
      const j = SC.running.get(e.agent_id); if (!j) return;
      const cat = S.CATS.includes(e.tool_category) ? e.tool_category : 'other';
      j.cats[cat] = (j.cats[cat] || 0) + 1; j.tools.push({ d: Math.max(0, e.ts - j.t0), c: cat });
    } else if (e.name === 'SubagentStop') {
      const j = SC.running.get(keyOf(e)); if (!j) return;
      SC.running.delete(j.key);
      // jobs.js 在同一個事件裡才把 agent_id 對到同事，所以挑同事要等它跑完：這裡用微任務延後一拍
      Promise.resolve().then(() => finish(j, e));
    }
  });

  function whoOf(j, e) {
    const mid = (j.aid && S.byAgentId.get(j.aid)) || (e.agent_type && W.chars.get(e.agent_type) ? e.agent_type : null) || (j.type && W.chars.get(j.type) ? j.type : null);
    return mid || j.type || 'ceo';
  }
  function finish(j, e) {
    const failed = e.status === 'failed', who = whoOf(j, e), n = nameOf(who), t1 = e.ts || S.now();
    // 被退次數：同一位同事、同一個標題，在這之前連續失敗幾張（遇到一張成功的就斷）
    let retries = 0; for (const c of SC.cards) { if (c.who !== who || c.title !== j.title) continue; if (c.failed) retries++; else break; }
    const toolN = j.tools.length, tests = j.cats.test || 0;
    let evs = j.tools; if (evs.length > MAXEV) { const step = evs.length / MAXEV; evs = Array.from({ length: MAXEV }, (_, i) => evs[Math.floor(i * step)]); }
    const tok = [e.tokens, e.usage_tokens, e.total_tokens].find(v => Number.isFinite(+v) && +v > 0);
    const card = { id: 'c' + t1.toString(36) + Math.random().toString(36).slice(2, 5), who, nick: n.nick, role: n.zh, title: j.title, t0: j.t0, t1, dur: Math.max(0, t1 - j.t0),
      failed, retries, toolN, cats: j.cats, tests, tokens: tok ? Math.round(+tok) : null, summary: short(e.last_assistant_message || '', 60), evs: evs.map(x => [Math.round(x.d), x.c]), seen: false };
    SC.cards.unshift(card); if (SC.cards.length > MAXC) SC.cards.length = MAXC;
    save(); paintBtn(); if (SC.open && SC.mode === 'card' && SC.cards.length > 1) SC.idx++;   // 新卡插到最前面，正在看的那張往後一格，畫面不亂跳
    if (SC.open) paint();
    if (gateOk() && Math.abs(S.now() - t1) < 120000 && !(W.replay && W.replay.on)) toast(card);
    refreshCardBlock();
    if (SC.onCard) SC.onCard(card);
  }

  // ───────── 樣式 ─────────
  const css = document.createElement('style'); css.id = 'scCss';
  css.textContent = `#scBtn{position:relative}#scBtn b.sc-dot{position:absolute;right:-4px;top:-5px;min-width:16px;height:16px;border-radius:8px;background:#e5484d;color:#fff;font-size:11px;line-height:16px;text-align:center;padding:0 4px}
#scPanel{position:absolute;z-index:31;left:50%;top:76px;transform:translateX(-50%);width:min(420px,calc(100vw - 24px));max-height:calc(100dvh - 100px);overflow:auto;background:var(--card,#fff);border-radius:var(--r,16px);box-shadow:var(--sh,0 8px 30px rgba(0,0,0,.2));padding:14px 16px;font-size:14px;line-height:1.55;color:var(--ink,#3b302a)}
#scPanel h3{margin:0 0 2px;font-size:16px;display:flex;align-items:center;gap:8px;padding-right:30px}#scPanel h3 small{font-size:12px;color:var(--sub,#7a6f66);font-weight:600}
#scPanel .x{position:absolute;right:10px;top:8px;width:30px;height:30px;border:0;background:transparent;font-size:22px;cursor:pointer;color:var(--sub,#7a6f66)}
#scPanel .sc-t{font-size:14px;margin:2px 0 8px;color:var(--ink,#3b302a);font-weight:600;word-break:break-all}
#scPanel .sc-res{display:inline-block;border-radius:999px;padding:2px 10px;font-size:13px;font-weight:700;margin-bottom:6px}#scPanel .sc-res.ok{background:#e4f6ea;color:#1c7a43}#scPanel .sc-res.bad{background:#fdeadf;color:#b4500a}
#scPanel dl{margin:0;display:grid;grid-template-columns:5.2em 1fr;gap:5px 8px;font-size:13.5px}#scPanel dt{color:var(--sub,#7a6f66)}#scPanel dd{margin:0;word-break:break-all}#scPanel dd small{color:var(--sub,#7a6f66);font-size:12px}
#scPanel .sc-note{font-size:12.5px;color:var(--sub,#7a6f66);margin:8px 0 0;background:var(--on2,#f6efe8);border-radius:10px;padding:6px 10px}
#scPanel .sc-act{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}#scPanel .sc-act .btn{box-shadow:none;border:1px solid var(--line,#e3d9cf);height:34px;padding:0 11px;font-size:13px}#scPanel .sc-act .btn[disabled]{opacity:.45}
#scPanel .sc-list{list-style:none;margin:6px 0 0;padding:0}#scPanel .sc-list button{width:100%;display:flex;gap:8px;align-items:baseline;text-align:left;border:0;border-bottom:1px solid var(--line,#e3d9cf);background:transparent;padding:8px 2px;font:inherit;font-size:13px;cursor:pointer;color:inherit;min-height:40px}
#scPanel .sc-list b{flex:none}#scPanel .sc-list span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--sub,#7a6f66)}#scPanel .sc-list time{flex:none;font-size:12px;color:var(--sub,#7a6f66)}#scPanel .sc-list i{font-style:normal;flex:none;font-weight:700}
#scPanel .sc-list i.ok{color:#1c7a43}#scPanel .sc-list i.bad{color:#b4500a}
#scPanel .sc-help{font-size:12.5px;color:var(--sub,#7a6f66);margin:8px 0 0;line-height:1.6}
#scPanel .sc-q{width:22px;height:22px;border-radius:50%;border:1px solid var(--line,#e3d9cf);background:transparent;font-size:12px;cursor:pointer;color:var(--sub,#7a6f66);padding:0}
#scToast{position:absolute;left:12px;bottom:76px;z-index:12;max-width:min(340px,calc(100vw - 24px));background:rgba(30,30,52,.92);color:#fff;border-radius:14px;padding:9px 12px;font-size:13px;display:flex;gap:10px;align-items:center}
#scToast button{border:1px solid rgba(255,255,255,.5);background:transparent;color:#fff;border-radius:10px;height:30px;padding:0 10px;font-size:13px;cursor:pointer;flex:none}
#scCardB{margin:6px 0;font-size:13px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:var(--on2,#f6efe8);border-radius:10px;padding:6px 10px}#scCardB span{flex:1 1 9em;min-width:0}#scCardB .btn{box-shadow:none;border:1px solid var(--line,#e3d9cf);height:30px;padding:0 10px;font-size:13px}
@media (max-width:640px){#scPanel{top:64px;padding:12px}#scBtn{padding:0 8px;font-size:12.5px}#scToast{bottom:64px;font-size:12px}}`;
  document.head.append(css);

  // ───────── 頂列鈕＋面板＋提示 ─────────
  const app = $('app') || document.body, bar = $('bar');
  const btn = document.createElement('button'); btn.className = 'btn'; btn.id = 'scBtn'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-label', '成績單（每件派工做完的成績，可翻歷史）');
  btn.innerHTML = '成績單<b class="sc-dot" id="scDot" hidden>0</b>';
  const ovBtn = $('ovBtn'); if (bar) { if (ovBtn) bar.insertBefore(btn, ovBtn); else bar.append(btn); }
  const panel = document.createElement('aside'); panel.id = 'scPanel'; panel.hidden = true; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', '單件成績單');
  const tst = document.createElement('div'); tst.id = 'scToast'; tst.hidden = true; tst.setAttribute('role', 'status');
  app.append(panel, tst);

  function paintBtn() {
    btn.hidden = !gateOk(); const n = SC.cards.filter(c => !c.seen).length, d = $('scDot'); d.hidden = !n; d.textContent = n > 99 ? '99+' : String(n);
    btn.setAttribute('aria-label', n ? `成績單，${n} 張沒看過` : '成績單（每件派工做完的成績，可翻歷史）');
  }
  SC.paintBtn = paintBtn;
  let tT = 0;
  function toast(card) {
    tst.innerHTML = `<span>${esc(card.nick)}${card.failed ? ' 這件沒做成' : ' 交件了'}：${esc(short(card.title, 18))}</span><button type="button" data-sc-open="${esc(card.id)}">看成績單</button>`;
    tst.hidden = false; clearTimeout(tT); tT = setTimeout(() => { tst.hidden = true; }, 9000);
  }
  tst.addEventListener('click', e => { const b = e.target.closest('[data-sc-open]'); if (b) { tst.hidden = true; SC.show(b.dataset.scOpen); } });

  // ───────── 面板 ─────────
  const catLine = c => Object.keys(c.cats || {}).map(k => `${CAT_ZH[k] || k} ${c.cats[k]}`).join('・');
  function cardHtml(c, i) {
    const total = SC.cards.length;
    const res = c.failed ? `<span class="sc-res bad">沒做成${c.retries ? `（這是第 ${c.retries + 1} 次沒過）` : ''}</span>` : `<span class="sc-res ok">順利交件</span>`;
    const use = c.tokens ? `約 ${c.tokens.toLocaleString('zh-TW')} Token` : `${c.toolN} 次工具呼叫${c.toolN ? `<br><small>${esc(catLine(c))}・估算，沒有逐件 Token 數</small>` : '<br><small>估算，沒有逐件 Token 數</small>'}`;
    const retry = c.failed ? `前面已經有 ${c.retries} 次沒過` : c.retries ? `<b>${c.retries}</b> 次（做好之前沒過 ${c.retries} 次）` : '<b>0</b> 次（一次就過）';
    const test = c.tests ? (c.failed ? `有跑 ${c.tests} 次，最後沒做成` : `有跑 ${c.tests} 次，交件成功`) : '這件沒有跑測試';
    return `<h3>${esc(c.nick)} 的成績單<small>第 ${i + 1}／${total} 件</small></h3>
      <div class="sc-t">${esc(c.title)}</div>${res}
      <dl><dt>誰做的</dt><dd>${esc(c.nick)}${c.role ? '・' + esc(c.role) : ''}</dd>
        <dt>耗時</dt><dd><b>${esc(durText(c.dur))}</b><br><small>${hhmm(c.t0)} 開工 → ${hhmm(c.t1)} 交件</small></dd>
        <dt>用量</dt><dd>${use}</dd>
        <dt>被退次數</dt><dd>${retry}</dd>
        <dt>測試</dt><dd>${esc(test)}</dd></dl>
      ${c.summary ? `<p class="sc-note">交件說明：${esc(c.summary)}</p>` : ''}`;
  }
  function paint() {
    if (!SC.open) return;
    const cs = SC.cards;
    const head = '<button class="x" data-sc="close" aria-label="關閉成績單">×</button>';
    const help = `<p class="sc-help" id="scHelp" hidden>耗時用事件自己的時間算；用量是這一件期間的工具呼叫次數（估算）；被退次數＝同一位同事做同一個任務，成功之前連續沒做成幾次；測試只看有沒有跑，事件不帶測試通過與否，所以以交件成功或失敗為準。</p>`;
    if (!cs.length) { panel.innerHTML = head + `<h3>成績單</h3><p class="sc-note">還沒有成績單。每件派工做完，這裡就會多一張。</p>`; return; }
    if (SC.idx >= cs.length) SC.idx = cs.length - 1; if (SC.idx < 0) SC.idx = 0;
    if (SC.mode === 'list') {
      panel.innerHTML = head + `<h3>歷史清單<small>${cs.length} 張</small></h3><ul class="sc-list">${cs.map((c, i) => `<li><button type="button" data-sc-i="${i}"><i class="${c.failed ? 'bad' : 'ok'}">${c.failed ? '✗' : '✓'}</i><b>${esc(c.nick)}</b><span>${esc(c.title)}</span><time>${hhmm(c.t1)}</time></button></li>`).join('')}</ul>
        <div class="sc-act"><button class="btn" data-sc="card">回到成績單</button></div>`;
      return;
    }
    const c = cs[SC.idx]; c.seen = true; save(); paintBtn();
    const rp = W.replay;
    panel.innerHTML = head + cardHtml(c, SC.idx) + help + `<div class="sc-act"><button class="btn" data-sc="prev"${SC.idx >= cs.length - 1 ? ' disabled' : ''}>◀ 上一件</button><button class="btn" data-sc="next"${SC.idx <= 0 ? ' disabled' : ''}>下一件 ▶</button>
      <button class="btn" data-sc="list">歷史清單</button>${rp && rp.gateOk() ? '<button class="btn" data-sc="replay">▶ 重播這件</button>' : ''}${W.away && W.away.gateOk() ? '<button class="btn" data-sc="away">提醒設定</button>' : ''}<button class="sc-q" data-sc="help" aria-expanded="false" aria-label="怎麼算的">?</button></div>`;
  }
  SC.paint = paint;
  SC.show = id => {
    if (!gateOk()) return false;
    const i = id == null ? 0 : typeof id === 'number' ? id : SC.cards.findIndex(c => c.id === id);
    SC.idx = Math.max(0, i); SC.mode = 'card'; SC.open = true; panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); paint(); return true;
  };
  SC.showList = () => { if (!gateOk()) return false; SC.mode = 'list'; SC.open = true; panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); paint(); return true; };
  SC.close = () => { SC.open = false; panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); };
  btn.onclick = () => { if (SC.open) SC.close(); else SC.show(0); };
  panel.addEventListener('click', e => {
    const b = e.target.closest('[data-sc],[data-sc-i]'); if (!b) return;
    if (b.dataset.scI != null) { SC.idx = +b.dataset.scI; SC.mode = 'card'; paint(); return; }
    const a = b.dataset.sc;
    if (a === 'close') SC.close();
    else if (a === 'prev') { SC.idx++; paint(); } else if (a === 'next') { SC.idx--; paint(); }
    else if (a === 'list') { SC.mode = 'list'; paint(); } else if (a === 'card') { SC.mode = 'card'; paint(); }
    else if (a === 'help') { const h = $('scHelp'); h.hidden = !h.hidden; b.setAttribute('aria-expanded', String(!h.hidden)); }
    else if (a === 'away') { SC.close(); if (W.away) W.away.settings(); }
    else if (a === 'replay') { const c = SC.cards[SC.idx]; if (c && W.replay) { SC.close(); W.replay.play(c.id); } }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && SC.open) SC.close(); });

  // ───────── 資訊卡：最近成績單 ─────────
  let cardId = null;
  function cardBlock(id) {
    const i = SC.cards.findIndex(c => c.who === id); if (i < 0) return '';
    const c = SC.cards[i];
    return `<div id="scCardB"><span>最近成績單：${esc(short(c.title, 14))}・${c.failed ? '沒做成' : '耗時 ' + esc(durText(c.dur))}</span><button class="btn" type="button" data-sc-card="${esc(c.id)}">看成績單</button></div>`;
  }
  function decorate(c) {
    cardId = c.spec.id; const card = $('card'); if (!card) return; const old = card.querySelector('#scCardB'); if (old) old.remove();
    const html = cardBlock(cardId); if (!html || !gateOk()) return;
    const anchor = card.querySelector('#gmCard') || card.querySelector('#cardMood') || card.querySelector('#cardNow'); if (!anchor) return;
    anchor.insertAdjacentHTML('afterend', html);
  }
  function refreshCardBlock() { const card = $('card'); if (card && !card.hidden && cardId) { const c = W.chars.get(cardId); if (c) decorate(c); } }
  if (W.ui && W.ui.showCard) { const orig = W.ui.showCard; W.ui.showCard = c => { const r = orig.call(W.ui, c); try { decorate(c); } catch (e) { console.error('成績單區塊失敗', e); } return r; }; }
  $('card') && $('card').addEventListener('click', e => { const b = e.target.closest('[data-sc-card]'); if (b) SC.show(b.dataset.scCard); });

  // ───────── 總覽通知「完成」→ 開那一張（先於總覽自己的處理，總覽照樣把鏡頭飛過去） ─────────
  const ovp = $('ovPanel');
  if (ovp) ovp.addEventListener('click', e => {
    const b = e.target.closest('.ov-nt[data-k="done"]'); if (!b || !W.overview) return;
    const n = W.overview.notes.find(x => x.id === +b.dataset.nid); if (!n) return;
    // 通知的時間是「偵測到的時候」，成績單的時間是事件時間：找同一位、最接近的一張
    let best = -1, bd = 1e15; SC.cards.forEach((c, i) => { if (c.who !== n.who) return; const d = Math.abs(c.t1 - n.t); if (d < bd) { bd = d; best = i; } });
    if (best >= 0) setTimeout(() => SC.show(best), 0);
  }, true);

  paintBtn();
  if (W.gate && W.gate.load) W.gate.load().then(() => { paintBtn(); if (!gateOk()) SC.close(); }).catch(() => { /* 連不到：維持顯示 */ });
}

{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.ready && W.state && W.chars && W.ui) { clearInterval(t); try { boot(W); } catch (e) { console.error('成績單載入失敗', e); } } else if (++n > 600) clearInterval(t); }, 100); }
