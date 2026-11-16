// 離開期間成果包＋到點提醒（2026-11-16，第二輪參考研究 docs/ai_office/game_basics_gap_round2.md 第 5 項：Neko Atsume「離線也有進展、回來看禮物」＋ Tamagotchi「約定時間回來」）
//
// ① 「你不在的時候」摘要：離開頁面（切分頁、縮小）或整個關掉之後，隔超過 N 分鐘（預設 10 分鐘，可選 5／10／30／關閉）再回來，
//    跳出一張卡：完成幾件（附前幾件標題、可一鍵看成績單）、誰卡住、誰晉級、其他重要事件（著火、額度用完、CEO 在等你）。可關，也可選「之後不再顯示」。
//    · 設計原則（研究報告）：輕懲罰、不靠罪惡感——離開太久不會有任何壞事，這張卡只是「回來看看成果」，沒有成果就不打擾。
//    · 離開時間點：visibilitychange hidden（記在 aiOffice.game.away.leftAt）；整頁關掉再開則用最後一次心跳 seen（每 20 秒寫一次）。
//      回來 4 秒後才算（給即時模式補收離線期間的事件）。成績單的時間是事件自己的時間，所以補收的歷史事件也算得進去。
// ② 到點提醒：某一件正在做的工作，過了「同一位同事過去的平均耗時」還沒交件，就提醒一次：「預估這時候該做完了」。
//    · 估算只用成績單歷史：同一位同事做過 2 件以上用他的平均，否則全部平均要 3 件以上；樣本不足就不提醒，不編數字。
//    · 瀏覽器通知需要使用者按「開啟瀏覽器通知」並同意；不同意、不支援、分頁在前景時，一律改成畫面上的提示（跟離開期間的提醒一起進成果包）。
// 存檔：localStorage aiOffice.game.away（{ leftAt, seen }）與 aiOffice.game.awaycfg（{ min, off, remind, notif }）；雲端存檔會帶走設定。
// 網址參數（驗收用）：away_min=<分鐘，可小數> 覆蓋門檻。功能閘門：features.js 的 office.awaypack（開關）。文案禁用字見 gate.js 檔頭。

const KS = 'aiOffice.game.away', KC = 'aiOffice.game.awaycfg';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };
const jget = (k, d) => { try { const o = JSON.parse(lsGet(k) || 'null'); return o && typeof o === 'object' ? o : d; } catch (e) { return d; } };
const spanText = ms => { const m = Math.max(1, Math.round(ms / 60000)); if (m < 60) return m + ' 分鐘'; const h = Math.floor(m / 60); return h + ' 小時' + (m % 60 ? ' ' + (m % 60) + ' 分' : ''); };

function boot(W) {
  const S = W.state, qs = new URLSearchParams(location.search);
  const AW = { cfg: Object.assign({ min: 10, off: false, remind: true, notif: false }, jget(KC, {})), open: false, mode: 'pack', pack: null, missed: [], fired: new Set(), notified: [], lastShown: 0 };
  W.away = AW;
  const gateOk = () => { try { return !W.gate || W.gate.peek('office.awaypack').pass; } catch (e) { return true; } };
  AW.gateOk = gateOk;
  const thresholdMs = () => { const q = parseFloat(qs.get('away_min')); return (Number.isFinite(q) && q > 0 ? q : AW.cfg.min) * 60000; };
  const saveCfg = () => lsSet(KC, JSON.stringify(AW.cfg));
  const nameOf = id => { const c = W.chars.get(id); return c ? c.spec.nick || id : id || '同事'; };

  // ───────── 樣式與畫面 ─────────
  const css = document.createElement('style'); css.id = 'awCss';
  css.textContent = `#awPanel{position:absolute;z-index:34;left:50%;top:84px;transform:translateX(-50%);width:min(440px,calc(100vw - 24px));max-height:calc(100dvh - 110px);overflow:auto;background:var(--card,#fff);border-radius:var(--r,16px);box-shadow:var(--sh,0 8px 30px rgba(0,0,0,.25));padding:16px;font-size:14px;line-height:1.55;color:var(--ink,#3b302a)}
#awPanel h3{margin:0 0 4px;font-size:17px;padding-right:30px}#awPanel .aw-sub{font-size:12.5px;color:var(--sub,#7a6f66);margin:0 0 10px}
#awPanel .x{position:absolute;right:10px;top:8px;width:32px;height:32px;border:0;background:transparent;font-size:22px;cursor:pointer;color:var(--sub,#7a6f66)}
#awPanel .aw-sec{margin:8px 0;padding:8px 10px;border-radius:12px;background:var(--on2,#f6efe8)}#awPanel .aw-sec h5{margin:0 0 3px;font-size:13.5px}#awPanel .aw-sec h5 b{font-size:15px}
#awPanel .aw-sec.warn{background:#fdf1e3}#awPanel .aw-sec ul{margin:2px 0 0;padding-left:18px;font-size:13px}#awPanel .aw-sec li{margin:1px 0}
#awPanel .aw-calm{font-size:13.5px;color:var(--sub,#7a6f66);margin:8px 0}
#awPanel .aw-act{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}#awPanel .aw-act .btn,#awPanel .aw-chips .btn{box-shadow:none;border:1px solid var(--line,#e3d9cf);height:36px;padding:0 12px;font-size:13px}
#awPanel .aw-chips{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px}#awPanel .btn.on{background:var(--on,#f08a24);border-color:var(--on,#f08a24);color:#fff}
#awPanel .aw-row{margin:10px 0 4px;font-size:13px}#awPanel .aw-row b{display:block;margin-bottom:3px}#awPanel .aw-msg{font-size:12.5px;color:var(--sub,#7a6f66);margin:4px 0 0}
#awToast{position:absolute;right:12px;bottom:76px;z-index:35;max-width:min(360px,calc(100vw - 24px));background:rgba(30,30,52,.94);color:#fff;border-radius:14px;padding:10px 12px;font-size:13px;display:flex;gap:10px;align-items:center;line-height:1.45}
#awToast button{border:1px solid rgba(255,255,255,.5);background:transparent;color:#fff;border-radius:10px;height:32px;min-width:44px;padding:0 10px;font-size:13px;cursor:pointer;flex:none}
@media (max-width:640px){#awPanel{top:64px;padding:12px}#awToast{bottom:64px;right:8px;font-size:12px}}`;
  document.head.append(css);
  const app = $('app') || document.body;
  const panel = document.createElement('aside'); panel.id = 'awPanel'; panel.hidden = true; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', '你不在的時候');
  const toastEl = document.createElement('div'); toastEl.id = 'awToast'; toastEl.hidden = true; toastEl.setAttribute('role', 'status');
  app.append(panel, toastEl);

  // ───────── 成果包內容：離開之後發生了什麼 ─────────
  function buildPack(since) {
    const SC = W.scorecard, cards = SC ? SC.cards.filter(c => c.t1 >= since) : [], now = S.now();
    const done = cards.filter(c => !c.failed), failed = cards.filter(c => c.failed);
    const stuck = [], stuckMs = (S.cfg && S.cfg.stuckMs && S.cfg.stuckMs[0]) || 180000;
    for (const [id, a] of S.agents) { if (a.phase === 'doing' && now - a.lastToolAt >= stuckMs) stuck.push(`${nameOf(id)}：「${short(a.task, 18)}」已 ${spanText(now - a.lastToolAt)}沒有新動靜`); }
    const waits = []; if (S.flags.permission) waits.push('CEO 在等你核准'); if (S.flags.question) waits.push('CEO 在等你回答');
    const notes = (W.overview && W.overview.notes ? W.overview.notes : []).filter(n => n.t >= since);
    const lv = notes.filter(n => n.kind === 'level').map(n => n.text), fire = notes.filter(n => n.kind === 'fire').map(n => n.text);
    const other = []; if (S.q && S.q.exhausted) other.push('額度用完了，恢復前大家先休息'); fire.slice(0, 3).forEach(t => other.push(t)); AW.missed.filter(m => m.t >= since).forEach(m => other.push(m.text));
    return { since, until: now, away: now - since, done, failed, stuck, waits, lv, other };
  }
  const packEmpty = p => !p.done.length && !p.failed.length && !p.stuck.length && !p.waits.length && !p.lv.length && !p.other.length;

  function paint() {
    if (!AW.open) return;
    const x = '<button class="x" data-aw="close" aria-label="關閉">×</button>';
    if (AW.mode === 'set') {
      const N = typeof Notification !== 'undefined' ? Notification.permission : 'unsupported';
      const st = N === 'unsupported' ? '這個瀏覽器不支援通知，到點時改用畫面上的提示。' : AW.cfg.notif && N === 'granted' ? '已開啟：到點時，就算你在別的分頁也會跳瀏覽器通知。' : N === 'denied' ? '瀏覽器已拒絕通知，到點時改用畫面上的提示（要改請到瀏覽器的網站設定）。' : '還沒開啟：到點時用畫面上的提示。';
      panel.innerHTML = x + `<h3>提醒設定</h3><p class="aw-sub">離開一陣子回來的摘要，和「預估該做完了」的到點提醒。</p>
        <div class="aw-row"><b>離開多久回來，要看摘要？</b><div class="aw-chips" id="awChips">${[[0, '不顯示'], [5, '5 分鐘'], [10, '10 分鐘'], [30, '30 分鐘']].map(([m, t]) => `<button class="btn${(m === 0 ? AW.cfg.off : !AW.cfg.off && AW.cfg.min === m) ? ' on' : ''}" data-aw-min="${m}" aria-pressed="${m === 0 ? AW.cfg.off : !AW.cfg.off && AW.cfg.min === m}">${t}</button>`).join('')}</div></div>
        <div class="aw-row"><b>到點提醒</b><div class="aw-chips"><button class="btn${AW.cfg.remind ? ' on' : ''}" data-aw="remind" aria-pressed="${AW.cfg.remind}">${AW.cfg.remind ? '已開啟' : '已關閉'}</button><button class="btn" data-aw="notif">開啟瀏覽器通知</button></div>
          <p class="aw-msg" id="awMsg">${esc(st)}</p></div>
        <div class="aw-act"><button class="btn" data-aw="back">${AW.pack ? '回到摘要' : '關閉'}</button></div>`;
      return;
    }
    const p = AW.pack; if (!p) { AW.mode = 'set'; paint(); return; }
    const sec = (cls, h, n, items) => `<div class="aw-sec ${cls}"><h5>${h}${n != null ? ` <b>${n}</b>` : ''}</h5>${items && items.length ? `<ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>` : ''}</div>`;
    panel.innerHTML = x + `<h3>你不在的時候</h3><p class="aw-sub">你離開了約 ${spanText(p.away)}（${new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', hourCycle: 'h23', hour: '2-digit', minute: '2-digit' }).format(new Date(p.since))} 起）。沒有壓力，這只是回來看看成果。</p>
      ${p.done.length ? sec('ok', '完成了（件）', p.done.length, p.done.slice(0, 4).map(c => `${c.nick}：${short(c.title, 22)}` + (p.done.length > 4 && c === p.done[3] ? '…還有更多' : ''))) : ''}
      ${p.failed.length ? sec('warn', '遇到問題沒做成（件）', p.failed.length, p.failed.slice(0, 3).map(c => `${c.nick}：${short(c.title, 22)}`)) : ''}
      ${p.waits.length ? sec('warn', '現在在等你', null, p.waits) : ''}
      ${p.stuck.length ? sec('warn', '卡住的（人）', p.stuck.length, p.stuck.slice(0, 4)) : ''}
      ${p.lv.length ? sec('ok', '晉級了（人）', p.lv.length, p.lv.slice(0, 4)) : ''}
      ${p.other.length ? sec('', '其他重要事件', null, p.other.slice(0, 4)) : ''}
      ${packEmpty(p) ? '<p class="aw-calm">這段時間很平靜，沒有新的成果或狀況。</p>' : ''}
      <div class="aw-act">${p.done.length || p.failed.length ? '<button class="btn" data-aw="cards">看成績單</button>' : ''}<button class="btn" data-aw="settings">提醒設定</button><button class="btn" data-aw="never">之後不再顯示</button><button class="btn on" data-aw="close">知道了</button></div>`;
  }
  AW.paint = paint;
  AW.show = (since, auto) => {
    if (!gateOk()) return false;
    const pk = buildPack(since == null ? Date.now() - thresholdMs() : since);
    if (auto && packEmpty(pk)) return false;          // 自動跳出時沒有成果就不打擾（輕懲罰原則）；手動開一定顯示
    AW.pack = pk; AW.mode = 'pack'; AW.open = true; panel.hidden = false; AW.lastShown = Date.now(); paint(); return true;
  };
  AW.settings = () => { if (!gateOk()) return false; AW.mode = 'set'; AW.open = true; panel.hidden = false; paint(); return true; };
  AW.close = () => { AW.open = false; panel.hidden = true; AW.pack = null; };
  panel.addEventListener('click', async e => {
    const b = e.target.closest('[data-aw],[data-aw-min]'); if (!b) return;
    if (b.dataset.awMin != null) { const m = +b.dataset.awMin; if (m === 0) AW.cfg.off = true; else { AW.cfg.off = false; AW.cfg.min = m; } saveCfg(); paint(); return; }
    const a = b.dataset.aw;
    if (a === 'close') AW.close();
    else if (a === 'never') { AW.cfg.off = true; saveCfg(); AW.close(); if (W.ui && W.ui.toast) W.ui.toast('之後不再顯示離開摘要，要重開到成績單的「提醒設定」'); }
    else if (a === 'cards') { AW.close(); if (W.scorecard) W.scorecard.showList(); }
    else if (a === 'settings') { AW.mode = 'set'; paint(); }
    else if (a === 'back') { if (AW.pack) { AW.mode = 'pack'; paint(); } else AW.close(); }
    else if (a === 'remind') { AW.cfg.remind = !AW.cfg.remind; saveCfg(); paint(); }
    else if (a === 'notif') await askNotif();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && AW.open) AW.close(); });

  // ───────── 瀏覽器通知（要使用者按鈕同意；不同意就用畫面提示） ─────────
  async function askNotif() {
    const msg = t => { const m = $('awMsg'); if (m) m.textContent = t; };
    if (typeof Notification === 'undefined') { AW.cfg.notif = false; saveCfg(); msg('這個瀏覽器不支援通知，到點時改用畫面上的提示。'); return; }
    let r = Notification.permission;
    if (r === 'default') { try { r = await Notification.requestPermission(); } catch (e) { r = 'denied'; } }
    AW.cfg.notif = r === 'granted'; saveCfg(); AW.permResult = r;
    if (AW.open && AW.mode === 'set') paint();
    const m = $('awMsg'); if (m && r !== 'granted') m.textContent = '你沒有同意通知，到點時改用畫面上的提示。';
  }
  let tT = 0;
  function inSite(text, act) {
    toastEl.innerHTML = `<span>${esc(text)}</span>${act ? `<button type="button" data-aw-t="${act}">${act === 'cards' ? '看成績單' : '知道了'}</button>` : '<button type="button" data-aw-t="ok">知道了</button>'}`;
    toastEl.hidden = false; clearTimeout(tT); tT = setTimeout(() => { toastEl.hidden = true; }, 12000);
  }
  toastEl.addEventListener('click', e => { const b = e.target.closest('[data-aw-t]'); if (!b) return; toastEl.hidden = true; if (b.dataset.awT === 'cards' && W.scorecard) W.scorecard.showList(); });
  function notify(text) {
    AW.missed.push({ t: Date.now(), text }); if (AW.missed.length > 20) AW.missed.shift();
    let sent = false;
    if (AW.cfg.notif && typeof Notification !== 'undefined' && Notification.permission === 'granted' && document.hidden) {
      try { const n = new Notification('AI 辦公室', { body: text, tag: 'ai-office-eta' }); AW.notified.push(text); sent = true; n.onclick = () => { try { window.focus(); n.close(); } catch (e) { /* 略 */ } }; } catch (e) { sent = false; }
    }
    if (!sent) inSite(text);
    return sent;
  }
  AW.notify = notify;

  // ───────── 到點提醒：正在做的工作過了預估時間 ─────────
  function etaMs(who) {
    const cs = W.scorecard ? W.scorecard.cards.filter(c => !c.failed && c.dur >= 20000) : [];
    const mine = cs.filter(c => c.who === who); const use = mine.length >= 2 ? mine : cs.length >= 3 ? cs : null;
    return use ? use.reduce((s, c) => s + c.dur, 0) / use.length : null;
  }
  AW.etaMs = etaMs;
  function checkEta() {
    if (!AW.cfg.remind || !gateOk() || !W.scorecard) return;
    const now = S.now();
    for (const j of W.scorecard.running.values()) {
      if (AW.fired.has(j.key + j.t0)) continue;
      const who = (j.aid && S.byAgentId.get(j.aid)) || j.type, est = etaMs(who); if (!est) continue;
      if (now >= j.t0 + est) { AW.fired.add(j.key + j.t0); notify(`「${short(j.title, 18)}」預估這時候該做完了（${nameOf(who)} 通常約 ${spanText(est)}），還沒交件，去看看？`); }
    }
  }
  AW.checkEta = checkEta;
  setInterval(() => { try { checkEta(); } catch (e) { console.warn('到點提醒例外', e); } }, 3000);

  // ───────── 離開／回來 ─────────
  const rec = () => jget(KS, {});
  const put = o => lsSet(KS, JSON.stringify(Object.assign(rec(), o)));
  function onHide() { put({ leftAt: Date.now(), seen: Date.now() }); }
  function onShow() {
    const r = rec(), left = r.leftAt; put({ leftAt: 0, seen: Date.now() });
    if (!left || AW.cfg.off || !gateOk()) return;
    if (Date.now() - left >= thresholdMs()) setTimeout(() => { AW.show(left, true); }, 600);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) onHide(); else onShow(); });
  addEventListener('pagehide', onHide);
  setInterval(() => { if (!document.hidden) put({ seen: Date.now() }); }, 20000);
  // 整頁關掉再開：用上次最後的心跳或離開時間；等 4 秒讓即時模式補收離線期間的事件再算
  { const r = rec(), from = r.leftAt || r.seen || 0;
    put({ leftAt: 0, seen: Date.now() });
    if (from && !AW.cfg.off && Date.now() - from >= thresholdMs()) setTimeout(() => { if (gateOk() && !AW.open) AW.show(from, true); }, 4000); }

  if (W.scorecard && W.scorecard.paint) W.scorecard.paint();
}

{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.ready && W.state && W.chars && W.ui && W.scorecard) { clearInterval(t); try { boot(W); } catch (e) { console.error('離開成果包載入失敗', e); } } else if (++n > 600) clearInterval(t); }, 100); }
