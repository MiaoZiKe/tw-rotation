// 成長系統的畫面（2026-11-16）：資訊卡的「成長」區塊、名牌旁等級、頂列「今日目標」鈕與面板、晉級慶祝、派工理由、每日結算卡。
// 資料與規則在 growth.js；這支只負責畫面，不改任何既有檔案的內容，全部用「掛上去」的方式：
//   · 資訊卡：包住 ui.showCard，卡畫好之後在心情列後面插一塊（ui.refreshCard 重畫時也會再插一次）
//   · 名牌：在 c._lab.tag 裡多放一個 <i class="glv">Lv.3</i>（右上角的績效等第章在右邊，等級在左邊，不重疊）
//   · 頂列：在「績效總表」後面多一顆「今日目標 1/3」，點開面板；手機收在「更多」裡
// 說明文字一律收進「?」，預設收起（擁有者介面規矩）。畫面禁用字：價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵。

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const star = n => '★'.repeat(n) + '☆'.repeat(5 - n);

export function mountGrowthUI(G, W) {
  const U = {}, ui = W.ui;
  const toast = t => { try { ui.toast(t); } catch (e) { /* 略 */ } };

  // ───────── 浮動訊息（晉級、目標、派工理由）：同一個堆疊，不互相蓋住 ─────────
  const stack = document.createElement('div'); stack.id = 'gmStack'; stack.setAttribute('aria-live', 'polite'); ($('app') || document.body).append(stack);
  function pushMsg(html, cls, ms = 4200) {
    const el = document.createElement('div'); el.className = 'gm-msg ' + (cls || ''); el.innerHTML = html; stack.append(el);
    (G.msgLog || (G.msgLog = [])).push({ cls: cls || '', text: el.textContent }); if (G.msgLog.length > 40) G.msgLog.shift();   // 訊息會自己消失，留一份紀錄給驗收與除錯看
    while (stack.children.length > 4) stack.firstChild.remove();
    el.addEventListener('click', () => el.remove()); setTimeout(() => el.remove(), ms); return el;
  }
  U.msg = pushMsg;

  // ───────── 名牌旁的等級 ─────────
  function badge(c) {
    const L = c._lab; if (!L || !L.tag) return null; let b = L.tag.querySelector('.glv');
    if (!b) { b = document.createElement('i'); b.className = 'glv'; b.setAttribute('aria-label', '等級'); L.tag.append(b); L.tag.classList.add('haslv'); }
    return b;
  }
  function syncBadges() {
    for (const c of G.members()) { const b = badge(c); if (!b) continue; const g = G.get(c.spec.id), t = 'Lv.' + g.lv; if (b.textContent !== t) b.textContent = t; b.classList.toggle('tired', g.tired); b.title = `${c.spec.nick}：等級 ${g.lv}`; }
  }
  U.levelUp = (c, lv) => {
    const b = badge(c); if (b) { b.classList.remove('up'); void b.offsetWidth; b.classList.add('up'); setTimeout(() => b.classList.remove('up'), 3000); }
    try { c.emote && c.emote('star', 2.6); c.setExpression && c.setExpression('happy', 2.2); if (c.state === 'sit' && !c.busy && c.setAction) c.setAction('cheer', { duration: 1.6, then: 'idle' }); } catch (e) { /* 慶祝動作失敗不影響成長 */ }
    pushMsg(`<b>★ ${esc(c.spec.nick)} 晉級到 Lv.${lv}</b><span>等級提升了，繼續加油</span>`, 'up', 4800);
    G.last = { kind: 'levelUp', id: c.spec.id, lv };
  };
  U.gain = (c, xp, sk, failed) => { const b = badge(c); if (!b) return; b.dataset.gain = (failed ? '+' : '+') + xp + ' 經驗'; b.classList.remove('gain'); void b.offsetWidth; b.classList.add('gain'); setTimeout(() => b.classList.remove('gain'), 2200); };
  U.goalHit = g => { pushMsg(`<b>✓ 今日目標達成</b><span>${esc(g.text)}</span>`, 'goal', 4800); G.last = { kind: 'goal', id: g.id }; };

  // ───────── 資訊卡的成長區塊 ─────────
  let cardId = null;
  const SK_HELP = '專長：這位同事擅長的工作，星星越多越拿手。完成對得上的任務會累積練習，每 3 次多 1 星。\n體力與壓力：工作會讓體力下降、壓力上升；體力太低或壓力太高時，工作動作會變慢、頭上冒汗。去休息區、茶水間、運動場、泳池、飲水機或睡覺都能恢復。\n個性：固定不變，影響消耗與恢復的速度，也影響他說的話。\n經驗：完成派工得經驗，滿了就晉級；任務跟專長對得上、或是完美主義者，經驗更多。';
  const bar = (k, cls) => `<div class="gm-bar ${cls}" role="img" aria-label="${k}"><i data-k="${k}bar"></i></div>`;
  function cardHTML(c, g) {
    return `<div class="gm" id="gmCard" data-id="${esc(c.spec.id)}">
      <div class="gm-lv"><b data-k="lv">Lv.${g.lv}</b>${bar('xp', 'xp')}<span data-k="xp"></span><button class="gm-q" data-gmq aria-expanded="false" aria-label="成長說明">?</button></div>
      <div class="gm-st"><label>體力</label>${bar('sta', 'sta')}<b data-k="sta"></b><label>壓力</label>${bar('str', 'str')}<b data-k="str"></b></div>
      <div class="gm-state" data-k="state"></div>
      <div class="gm-row"><span class="gm-h">專長</span><span data-k="skills"></span></div>
      <div class="gm-row"><span class="gm-h">個性</span><span data-k="traits"></span></div>
      <div class="gm-help" hidden>${esc(SK_HELP).replace(/\n/g, '<br>')}</div></div>`;
  }
  function fillCard() {
    const root = $('gmCard'); if (!root) return; const g = G.get(root.dataset.id); if (!g) return;
    const set = (k, t) => { const e = root.querySelector(`[data-k="${k}"]`); if (e && e.textContent !== t) e.textContent = t; };
    const w = (k, v, col) => { const e = root.querySelector(`[data-k="${k}bar"]`); if (e) { e.style.width = clamp(v) + '%'; if (col) e.dataset.lvl = col; } };
    set('lv', 'Lv.' + g.lv); set('xp', g.need ? `${g.xp}／${g.need} 經驗` : '已到最高等級'); w('xp', g.need ? g.xp / g.need * 100 : 100);
    set('sta', String(g.sta)); set('str', String(g.str)); w('sta', g.sta, g.sta < 20 ? 'bad' : g.sta < 40 ? 'warn' : 'ok'); w('str', g.str, g.str > 85 ? 'bad' : g.str > 70 ? 'warn' : 'ok');
    const st = g.working ? (g.tired ? `工作中・已經很累，動作變慢了（速度 ${Math.round(g.speed * 100)}%）` : '工作中・體力慢慢下降') : g.resting ? `休息中（${g.restZh}）・體力恢復中` : g.tired ? '很累，手上沒事就會去休息' : '狀態不錯';
    set('state', st); root.classList.toggle('tired', g.tired);
    const sk = root.querySelector('[data-k="skills"]'), sh = g.skills.map(s => `${s.k}${star(s.n)}`).join('|');
    if (sk && sk.dataset.sig !== sh) { sk.dataset.sig = sh; sk.innerHTML = g.skills.map(s => `<span class="gm-chip sk" data-skill="${esc(s.k)}" aria-label="${esc(s.k)} ${s.n} 星">${esc(s.k)} <em>${star(s.n)}</em></span>`).join(''); }
    const tr = root.querySelector('[data-k="traits"]'), th = g.traits.map(t => t.id).join('|');
    if (tr && tr.dataset.sig !== th) { tr.dataset.sig = th; tr.innerHTML = g.traits.map(t => `<span class="gm-chip tr" data-trait="${t.id}">${esc(t.zh)}</span>`).join(''); }
  }
  const clamp = v => Math.max(0, Math.min(100, v));
  function decorate(c) {
    if (!c || c.spec.pet || c.spec.isCeo || c.jobless) return; const g = G.get(c.spec.id); if (!g) return;
    cardId = c.spec.id; const card = $('card'); if (!card || card.querySelector('#gmCard')) { fillCard(); return; }
    const anchor = card.querySelector('#cardMood') || card.querySelector('#cardNow'); if (!anchor) return;
    anchor.insertAdjacentHTML('afterend', cardHTML(c, g));
    const hp = card.querySelector('#gmCard .gm-help'); if (hp) hp.insertAdjacentHTML('beforeend', '<br><b>目前的個性：</b>' + g.traits.map(t => esc(t.zh) + '：' + esc(t.desc)).join('；'));
    fillCard();
  }
  const origShow = ui.showCard; ui.showCard = c => { const r = origShow.call(ui, c); try { decorate(c); } catch (e) { console.error('成長區塊失敗', e); } return r; };
  $('card').addEventListener('click', e => {
    const q = e.target.closest('[data-gmq]'); if (q) { const h = $('card').querySelector('#gmCard .gm-help'); if (h) { h.hidden = !h.hidden; q.setAttribute('aria-expanded', !h.hidden); } return; }
    const f = e.target.closest('[data-i="feed"]'); if (f && cardId) setTimeout(() => G.bump(cardId, 12, -4), 300);          // 餵點心：恢復一點體力
  });

  // ───────── 頂列「今日目標」＋面板 ─────────
  const btn = document.createElement('button'); btn.className = 'btn'; btn.id = 'gmBtn'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'gmPop');
  const rw = $('rwBtn'); if (rw && rw.parentNode) rw.after(btn); else $('bar').append(btn);
  const pop = document.createElement('div'); pop.className = 'pop'; pop.id = 'gmPop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '今日目標與派工'); ($('app') || document.body).append(pop);
  const goalsLine = () => { const gs = G.goals(), n = gs.filter(x => x.ok).length; return { gs, n }; };
  function renderBtn() { const { gs, n } = goalsLine(); const t = `今日目標 ${n}/${gs.length}`; if (btn.firstChild == null || btn.dataset.t !== t) { btn.dataset.t = t; btn.innerHTML = `${t}<i></i>`; } btn.classList.toggle('done', n === gs.length); }
  function renderPop() {
    const { gs } = goalsLine(), real = G.real(); pop.dataset.sig = JSON.stringify([gs.map(g => g.cur), real]);
    pop.innerHTML = `<h4>今日目標（台北時間，每天重新開始）</h4>
      <ul class="gm-goals">${gs.map(g => `<li class="${g.ok ? 'ok' : ''}" data-goal="${g.id}"><span class="mk" aria-hidden="true">${g.ok ? '✓' : '○'}</span><span class="tx">${esc(g.text)}</span><em>${g.cur}／${g.target}</em></li>`).join('')}</ul>
      <h4>${real ? '建議人選（依專長與體力）' : 'CEO 依專長自動派工'}</h4>
      <div class="grid c3 gm-skgrid">${G.SKILLS.map(k => `<button class="it" data-skill="${esc(k)}">${esc(k)}</button>`).join('')}</div>
      <p class="gm-note">${real ? '這是真實專案：Claude 的真實派工不會被改變，這裡只幫你看這類工作適合誰。' : '示範模式：按一下，CEO 會挑最適合的人並說出理由，真的派出一件任務。'}</p>
      <div class="acts"><button class="btn" data-gm="settle">今日結算</button></div>`;
  }
  function placePop() { const r = btn.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; }
  const closePop = () => { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.classList.remove('on'); };
  btn.onclick = () => { const was = pop.hidden; ui.closePops(); if (was) { renderPop(); pop.hidden = false; placePop(); btn.setAttribute('aria-expanded', 'true'); btn.classList.add('on'); } else closePop(); };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#gmPop') && !e.target.closest('#gmBtn')) closePop(); });
  pop.addEventListener('click', async e => {
    const s = e.target.closest('[data-skill]'); if (s) { s.disabled = true; try { await G.assign(s.dataset.skill); } finally { s.disabled = false; } return; }
    if (e.target.closest('[data-gm="settle"]')) { closePop(); G.settle(false); }
  });

  // ───────── 派工理由／建議人選 ─────────
  U.why = res => {
    const el = pushMsg(`<b>CEO 挑了 ${esc(res.nick)}・${esc(res.skill)}</b><span>${esc(res.why)}</span>${res.others.length ? `<span class="o">其他候選：${res.others.map(esc).join('；')}</span>` : ''}<span class="o">任務：${esc(res.task)}</span>`, 'why', 9000);
    el.dataset.who = res.who; G.last = { kind: 'why', who: res.who, skill: res.skill };
    if (!pop.hidden) renderPop();
  };
  U.suggest = res => {
    const c = W.chars.get(res.who), L = c && c._lab;
    if (L && L.tag) { let s = L.tag.querySelector('.gsg'); if (!s) { s = document.createElement('i'); s.className = 'gsg'; L.tag.append(s); } s.textContent = '建議人選：' + res.skill; clearTimeout(s._t); s._t = setTimeout(() => s.remove(), 20000); }
    const el = pushMsg(`<b>建議人選：${esc(res.nick)}（${esc(res.skill)}）</b><span>${esc(res.why)}</span>${res.others.length ? `<span class="o">其他候選：${res.others.map(esc).join('；')}</span>` : ''}<span class="o">這是真實專案，只標示建議，不會改變 Claude 的真實派工。</span>`, 'why', 9000);
    el.dataset.who = res.who; G.last = { kind: 'suggest', who: res.who, skill: res.skill };
    try { c && c.emote && c.emote('star', 2); } catch (e) { /* 略 */ }
  };
  U.blocked = note => { toast(note || '這個功能目前沒有開放'); try { W.gate && W.gate.say(note); } catch (e) { /* 略 */ } };

  // ───────── 每日結算卡 ─────────
  let dlg = null;
  U.settle = (s, auto) => {
    if (dlg) dlg.remove(); dlg = document.createElement('div'); dlg.id = 'gmDay'; dlg.className = 'gm-ov'; dlg.setAttribute('role', 'dialog'); dlg.setAttribute('aria-modal', 'true'); dlg.setAttribute('aria-label', '今日結算');
    const none = s.done === 0 && s.failed === 0;
    dlg.innerHTML = `<div class="gm-day"><button class="x" data-gmx aria-label="關閉">×</button>
      <h3>今日結算<small>${esc(s.day)}${auto ? '・下班了' : ''}</small></h3>
      <div class="gd-big"><div><b data-k="done">${s.done}</b><span>完成件數</span></div><div><b data-k="xp">${s.xp}</b><span>共得經驗</span></div><div><b data-k="failed">${s.failed}</b><span>遇到問題</span></div></div>
      <dl class="gd-list">
        <dt>最拚</dt><dd data-k="top">${s.top ? `${esc(s.top.nick)}（完成 ${s.top.done} 件，經驗 +${s.top.xp}）` : none ? '今天還沒有人完成任務' : '今天沒有人完成任務'}</dd>
        <dt>最累</dt><dd data-k="tired">${s.tiredest ? `${esc(s.tiredest.nick)}（體力 ${s.tiredest.sta}、壓力 ${s.tiredest.str}）` : '目前沒有同事'}</dd>
        <dt>晉級</dt><dd data-k="lvup">${s.lvUps.length ? s.lvUps.map(x => `${esc(x.nick)} 到 Lv.${x.lv}`).join('、') : '今天沒有人晉級'}</dd>
        <dt>休息</dt><dd data-k="rest">${s.rested} 位同事休息恢復過體力</dd></dl>
      <h4>今日目標</h4><ul class="gm-goals">${s.goals.map(g => `<li class="${g.ok ? 'ok' : ''}" data-goal="${g.id}"><span class="mk" aria-hidden="true">${g.ok ? '✓' : '○'}</span><span class="tx">${esc(g.text)}</span><em>${g.cur}／${g.target}</em></li>`).join('')}</ul>
      <div class="acts"><button class="btn on" data-gmx>收工，明天見</button></div></div>`;
    ($('app') || document.body).append(dlg); const closeB = dlg.querySelector('.acts .btn'); closeB && closeB.focus();
    dlg.addEventListener('click', e => { if (e.target === dlg || e.target.closest('[data-gmx]')) { dlg.remove(); dlg = null; } });
    G.last = { kind: 'settle' };
  };
  addEventListener('keydown', e => { if (e.key !== 'Escape') return; if (dlg) { dlg.remove(); dlg = null; } else if (!pop.hidden) closePop(); });
  { const dp = $('demoPop'); if (dp) dp.addEventListener('click', e => { const b = e.target.closest('[data-demo="clockout"]'); if (b) setTimeout(() => { const d = G.day(); if (d.done > 0 || d.xp > 0) G.settle(false); }, 6000); }); }   // 示範的「下班」：幾位同事離開之後跳出今日結算

  // ───────── 每 0.4 秒（真實時間）更新一次 ─────────
  let last = 0;
  U.tick = () => { const n = performance.now(); if (n - last < 400) return; last = n; syncBadges(); renderBtn(); fillCard(); if (!pop.hidden) { const sig = JSON.stringify([goalsLine().gs.map(g => g.cur), G.real()]); if (sig !== pop.dataset.sig) { pop.dataset.sig = sig; const keep = pop.scrollTop; renderPop(); pop.scrollTop = keep; } } };
  renderBtn();
  return U;
}
