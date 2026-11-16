// 任務重播（2026-11-16，第二輪參考研究 docs/ai_office/game_basics_gap_round2.md 第 9 項：ChatDev 的「重播模式」）
//
// 做什麼：成績單（scorecard.js）裡「▶ 重播這件」，把那一件工作從派工到交件的過程，在辦公室裡倒帶重演一次：
//   座位 → 走去 CEO 桌前領任務 → 回座位開工（依當時的工具類別換動作：讀、寫、查、測試…）→ 拿著成果走去交件 → 回座位。
//   · 時間軸拉桿可以拖（拖到哪、角色就在哪個位置做哪個動作）、播放／暫停、1×／4×；角落標「重播中」；結束（或按「結束重播」）回到即時。
//   · 時間被壓縮：真實可能做了 20 分鐘，重播最長約一分鐘；工具呼叫依它在原本過程裡的相對位置排進去。
//
// 為什麼重播是「用姿勢函式算位置」而不是把事件再餵一次狀態層：
//   拉桿要能跳到任何一刻，所以「某一秒時角色在哪、做什麼」必須是時間的純函式（timelineAt）；每一幀只是把這個答案套到角色身上。
//   事件重餵做不到倒帶，而且會污染真實的派工狀態（成績單、通知、經驗值）。重播期間完全不碰狀態層、不寫存檔。
// 重播期間怎麼不跟即時演出打架：被重播的那位同事標成 piloted（跟玩家操控時一樣，jobs.js／mind.js／growth.js 都會略過 piloted 的人），
//   結束時還原並叫他走回座位；其他同事照常工作，期間收到的即時事件照樣記錄（只是這位同事不會演出）。
// 用到的角色介面（character.js 檔頭）：sitAt／standAt／setAction／say／emote／faceTo；走路用 state='walk' 與 _speed 播走路姿勢，位置自己設。
// 功能閘門：features.js 的 office.replay（開關）。

const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const TOOL_ACT = { read: 'doc', write: 'note', search: 'magnify', test: 'type', deploy: 'phone', wait: 'drink', other: 'tablet' };
const CAT_ZH = { read: '讀資料', write: '寫程式', search: '查資料', test: '跑測試', deploy: '部署', wait: '等部署', other: '處理中' };
const mmss = s => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

function boot(W) {
  const R = { on: false, t: 0, total: 0, speed: 1, playing: false, cardId: null, segs: [], c: null, endT: 0, played: 0, last: '' };
  W.replay = R;
  const gateOk = () => { try { return !W.gate || W.gate.peek('office.replay').pass; } catch (e) { return true; } };
  R.gateOk = gateOk;
  const toast = t => { if (W.ui && W.ui.toast) W.ui.toast(t); };

  // ───────── 樣式與畫面 ─────────
  const css = document.createElement('style'); css.id = 'rpCss';
  css.textContent = `#rpTag{position:absolute;left:12px;top:64px;z-index:33;background:#e5484d;color:#fff;border-radius:999px;padding:4px 12px;font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;pointer-events:none;box-shadow:0 2px 10px rgba(0,0,0,.25)}
#rpTag i{width:8px;height:8px;border-radius:50%;background:#fff;animation:rpb 1s infinite}@keyframes rpb{50%{opacity:.25}}
#rpBar{position:absolute;left:50%;transform:translateX(-50%);bottom:14px;z-index:33;width:min(560px,calc(100vw - 24px));background:var(--card,#fff);border-radius:var(--r,16px);box-shadow:var(--sh,0 8px 30px rgba(0,0,0,.2));padding:10px 12px;font-size:13px;color:var(--ink,#3b302a)}
#rpBar .rp-cap{font-size:13px;margin:0 2px 6px;line-height:1.45;min-height:1.45em;word-break:break-all}#rpBar .rp-cap b{font-weight:700}
#rpBar .rp-row{display:flex;gap:8px;align-items:center}
#rpBar .btn{box-shadow:none;border:1px solid var(--line,#e3d9cf);height:36px;min-width:40px;padding:0 10px;justify-content:center;font-size:13px;flex:none}#rpBar .btn.on{background:var(--on,#f08a24);border-color:var(--on,#f08a24);color:#fff}
#rpBar input[type=range]{flex:1;min-width:0;height:32px;accent-color:var(--on,#f08a24)}#rpBar .rp-time{flex:none;font-variant-numeric:tabular-nums;font-size:12px;color:var(--sub,#7a6f66);min-width:5.6em;text-align:center}
@media (max-width:640px){#rpBar{bottom:8px;padding:8px 10px}#rpBar .rp-row{flex-wrap:wrap}#rpBar input[type=range]{flex:1 1 100%;order:5}#rpBar .rp-time{order:2;flex:1}#rpTag{top:56px}}`;
  document.head.append(css);
  const app = $('app') || document.body;
  const tag = document.createElement('div'); tag.id = 'rpTag'; tag.hidden = true; tag.setAttribute('role', 'status'); tag.innerHTML = '<i></i>重播中';
  const bar = document.createElement('div'); bar.id = 'rpBar'; bar.hidden = true; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', '任務重播控制');
  bar.innerHTML = `<div class="rp-cap" id="rpCap" aria-live="polite"></div><div class="rp-row"><button class="btn" id="rpPlay" type="button" aria-label="暫停">⏸</button>
    <input id="rpSeek" type="range" min="0" max="1000" step="1" value="0" aria-label="時間軸，拖動可跳到任何一刻"><span class="rp-time" id="rpTime">0:00 / 0:00</span>
    <button class="btn on" data-rs="1" type="button" aria-pressed="true">1×</button><button class="btn" data-rs="4" type="button" aria-pressed="false">4×</button><button class="btn" id="rpExit" type="button">結束重播</button></div>`;
  app.append(tag, bar);

  // ───────── 路徑工具 ─────────
  const plen = p => { let L = 0; for (let i = 1; i < p.length; i++) L += Math.hypot(p[i].x - p[i - 1].x, p[i].z - p[i - 1].z); return L; };
  function pointAt(p, f) {
    const L = plen(p) || 1e-6; let d = clamp(f, 0, 1) * L;
    for (let i = 1; i < p.length; i++) { const s = Math.hypot(p[i].x - p[i - 1].x, p[i].z - p[i - 1].z); if (d <= s || i === p.length - 1) { const k = s ? clamp(d / s, 0, 1) : 1; return { x: p[i - 1].x + (p[i].x - p[i - 1].x) * k, z: p[i - 1].z + (p[i].z - p[i - 1].z) * k, h: Math.atan2(p[i].x - p[i - 1].x, p[i].z - p[i - 1].z) }; } d -= s; }
    const q = p[p.length - 1]; return { x: q.x, z: q.z, h: 0 };
  }

  // ───────── 時間軸：成績單 → 一串片段 ─────────
  function build(card, c) {
    const id = c.spec.id, hs = c.homeSpot || W.spots.find(q => q.name === 'seat:' + id), ds = W.findSpots('ceo_front')[0];
    if (!hs || !hs.seat || !ds) return null;
    const route = (a, b) => { let p = null; try { p = W.nav.findPath({ x: a.x, z: a.z }, { x: b.x, z: b.z }); } catch (e) { p = null; } return p && p.length > 1 ? p : [{ x: a.x, z: a.z }, { x: b.x, z: b.z }]; };
    const go = route(hs.seat, ds), back = go.slice().reverse(), wd = clamp(plen(go) / 2.6, 1.2, 6);
    const evs = (card.evs || []).map(x => ({ d: +x[0] || 0, c: x[1] })), workD = clamp(evs.length * 1.2 + 4, 6, 40), dur = Math.max(1, card.dur || 1);
    const fail = !!card.failed, sum = short(card.summary || card.title, 16);
    const segs = [
      { k: 'sit', d: 1.2, act: 'type', cap: `${card.nick} 在座位上，等著被派工` },
      { k: 'walk', d: wd, path: go, cap: `${card.nick} 走去 CEO 桌前領任務` },
      { k: 'stand', d: 2.6, act: 'listen', say: '收到：' + short(card.title, 14), cap: `領任務：<b>${esc(short(card.title, 24))}</b>` },
      { k: 'walk', d: wd, path: back, cap: '回座位開工' },
      { k: 'work', d: workD, evs: evs.map((x, i) => ({ at: clamp(x.d / dur, 0, 1) * workD, c: x.c, i: i + 1 })), cap: '開工' },
      { k: 'walk', d: wd, path: go, cap: fail ? '拿著遇到的問題去回報' : '拿著成果去交件' },
      { k: 'stand', d: 3.2, act: fail ? 'sulk' : 'present', say: fail ? '這邊卡住了：' + sum : sum, cap: fail ? `遇到問題：<b>${esc(sum)}</b>` : `交件：<b>${esc(sum)}</b>` },
      { k: 'walk', d: wd, path: back, cap: '回座位' },
      { k: 'sit', d: 1.5, act: 'type', cap: fail ? '回座位，這件沒做成' : '回座位，這件完成' },
    ];
    let t = 0; for (const s of segs) { s.t0 = t; t += s.d; s.t1 = t; }
    return { segs, total: t, hs, ds, id };
  }
  // 某一秒時：第幾段、這一段走了多少（0..1）、工作段裡已經做到第幾次工具呼叫
  function timelineAt(t) {
    const segs = R.segs; let i = segs.findIndex(s => t < s.t1); if (i < 0) i = segs.length - 1;
    const s = segs[i], f = s.d ? clamp((t - s.t0) / s.d, 0, 1) : 1; let ev = null;
    if (s.k === 'work') for (const e of s.evs) if (t - s.t0 >= e.at) ev = e;
    return { i, s, f, ev };
  }

  // ───────── 套到角色身上 ─────────
  // 角色是 newchar.js 的物理控制器：位置由控制器決定（直接改 object3D.position 會被它拉回去），state 是唯讀的。
  // 所以：定點的片段（坐、站）用 sitAt／standAt 放好；走路片段「播放中」用真的 walkTo（有走路姿勢），算好速度剛好在片段結束時到；
  //       「暫停或拖拉桿」時用 standAt 把人放在路徑上的對應點（人站著，但位置跟著拉桿走）。
  function startWalk(s, f) {
    const c = R.c, path = s.path; let L = plen(path) || 1e-6, d = f * L, rem = [pointAt(path, f)];
    for (let i = 1; i < path.length; i++) { const sl = Math.hypot(path[i].x - path[i - 1].x, path[i].z - path[i - 1].z); if (d < sl - 1e-6) rem.push(path[i]); d -= sl; if (d < 0) d = -1; }
    if (rem.length < 2) return;
    const remLen = plen(rem), left = Math.max(0.2, (1 - f) * s.d / R.speed);
    c.walkTo(rem, { speed: clamp(remLen / left, 0.6, 14) }); R.walking = true;
  }
  function apply(force) {
    const c = R.c; if (!c) return; const tl = timelineAt(R.t), s = tl.s, T = R.timeline, mode = s.k === 'work' ? 'sit' : s.k;
    const sig = s.k + ':' + tl.i + ':' + (tl.ev ? tl.ev.i : 0);
    const enter = force || R.dirty || sig !== R.last || R.mode !== mode; R.last = sig; R.dirty = false;
    if (mode === 'walk') {
      if (enter) { const p = pointAt(s.path, tl.f); c.standAt(p.x, p.z, p.h); c.atDesk = false; c.setAction('idle'); R.walking = false; if (R.playing) startWalk(s, tl.f); }
      else if (R.playing && !R.walking) startWalk(s, tl.f);
      else if (!R.playing && R.walking) { c.stop(false); R.walking = false; }
    } else if (mode === 'sit') {
      if (R.mode !== 'sit') { R.walking = false; c.sitAt(T.hs.seat); c.atDesk = true; }
      if (enter) { const act = s.k === 'work' ? (tl.ev ? TOOL_ACT[tl.ev.c] || 'type' : 'type') : s.act; c.setAction(act); c.workAt = W.time + 600; if (tl.ev && tl.ev.c === 'test') c.emote('dots', 1.4); }
    } else {
      if (enter) {
        R.walking = false; c.standAt(T.ds.x, T.ds.z, T.ds.face); const ceo = W.chars.get('ceo'); if (ceo) c.faceTo(ceo.object3D.position.x, ceo.object3D.position.z);
        c.setAction(s.act); if (s.say) c.say(s.say, 2.8); if (s.act === 'sulk') c.setExpression('sad', 3); else c.setExpression('neutral', 0.1);
      }
    }
    R.mode = mode;
    const cap = s.k === 'work' ? (tl.ev ? `${CAT_ZH[tl.ev.c] || '處理中'}（第 ${tl.ev.i} 次工具呼叫，共 ${s.evs.length} 次）` : s.evs.length ? '開工' : '開工（這件沒有記到工具呼叫）') : s.cap;
    $('rpCap').innerHTML = `<b>${esc(R.card.nick)}</b>・` + cap;
    $('rpTime').textContent = mmss(R.t) + ' / ' + mmss(R.total);
    const sk = $('rpSeek'); if (document.activeElement !== sk) sk.value = String(Math.round(R.t / R.total * 1000));
  }

  // ───────── 播放迴圈 ─────────
  let raf = 0, lastTs = 0, exitT = 0;
  function loop(ts) {
    raf = requestAnimationFrame(loop); if (!R.on) return;
    const dt = lastTs ? Math.min(0.25, (ts - lastTs) / 1000) : 0; lastTs = ts;
    if (R.playing && !document.hidden) {
      R.t = Math.min(R.total, R.t + dt * R.speed);
      if (R.t >= R.total) { R.playing = false; paintPlay(); clearTimeout(exitT); exitT = setTimeout(() => { if (R.on && R.t >= R.total) R.stop(); }, 1800); }
    }
    apply(false);
  }
  function paintPlay() { R.dirty = true; const b = $('rpPlay'); b.textContent = R.playing ? '⏸' : '▶'; b.setAttribute('aria-label', R.playing ? '暫停' : '播放'); }

  // ───────── 對外 ─────────
  R.play = id => {
    if (!gateOk()) { toast('這個功能目前沒有開放'); return false; }
    const SC = W.scorecard; const card = SC && SC.cards.find(x => x.id === id); if (!card) return false;
    const c = W.chars.get(card.who);
    if (!c || c.absent || c.jobless || c.away || (c.object3D && c.object3D.visible === false)) { toast('這位同事現在不在辦公室，沒辦法重播'); return false; }
    if (c.piloted) { toast('這位同事正被你操控，放開他再重播'); return false; }
    { const a = W.state.agents.get(card.who); if (a && a.phase !== 'idle') { toast('他現在有工作在進行，做完再重播'); return false; } }   // 不打斷 jobs.js 的派工演出（會讓他的狀態卡在「領任務中」）
    if (R.on) R.stop(true);
    const T = build(card, c); if (!T) { toast('找不到他的座位，沒辦法重播'); return false; }
    R.timeline = T; R.segs = T.segs; R.total = T.total; R.card = card; R.cardId = id; R.c = c; R.t = 0; R.speed = 1; R.dirty = true; R.walking = false; R.mode = ''; R.last = ''; R.on = true; R.playing = true; R.played++;
    // 接管：跟玩家操控同一套旗標，讓即時演出略過他；中斷他手上正在走的路與腳本
    R.was = { busy: c.busy, view: (document.querySelector('#viewSeg .on') || {}).dataset ? document.querySelector('#viewSeg .on').dataset.v : 'ceo' };
    c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.stop(false); c.sleeping = false; c.piloted = true; c.busy = true; c.keep = null;
    try { if (W.director && W.director.release) W.director.release(c); } catch (e) { /* 沒有就算了 */ }
    tag.hidden = false; bar.hidden = false; document.body.classList.add('rp-on');
    bar.querySelectorAll('[data-rs]').forEach(b => { const on = +b.dataset.rs === 1; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    paintPlay(); try { if (W.setView) W.setView('char', c); } catch (e) { /* 略 */ }
    apply(true); lastTs = 0; cancelAnimationFrame(raf); raf = requestAnimationFrame(loop);
    return true;
  };
  R.seek = t => { if (!R.on) return; R.t = clamp(+t || 0, 0, R.total); clearTimeout(exitT); R.dirty = true; apply(false); };
  R.pause = () => { R.playing = false; paintPlay(); };
  R.resume = () => { if (!R.on) return; if (R.t >= R.total) R.t = 0; R.playing = true; clearTimeout(exitT); paintPlay(); };
  R.setSpeed = v => { R.speed = v; R.dirty = true; bar.querySelectorAll('[data-rs]').forEach(b => { const on = +b.dataset.rs === v; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); }); };
  R.stop = quiet => {
    if (!R.on) return; R.on = false; R.playing = false; clearTimeout(exitT); cancelAnimationFrame(raf); raf = 0;
    const c = R.c, T = R.timeline; tag.hidden = true; bar.hidden = true; document.body.classList.remove('rp-on');
    if (c) {
      c.piloted = false; c.busy = !!(R.was && R.was.busy);
      // 還原：在座位上就坐好繼續工作，否則把他現在的位置固定下來再走回座位
      if (R.mode === 'sit') { c.sitAt(T.hs.seat); c.atDesk = true; c.setAction('type'); c.workAt = W.time + 5; }
      else { const p = c.object3D.position; c.standAt(p.x, p.z); c.setAction('idle'); try { W.director.goHome(c, { speed: 2.4 }); } catch (e) { /* 略 */ } }
      c.setExpression('neutral', 0.1);
    }
    if (!quiet) { try { const v = R.was && R.was.view; if (W.setView && (v === 'ceo' || v === 'god')) W.setView(v); } catch (e) { /* 略 */ } }
    R.c = null;
  };
  bar.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.id === 'rpPlay') { if (R.playing) R.pause(); else R.resume(); }
    else if (b.id === 'rpExit') R.stop();
    else if (b.dataset.rs) R.setSpeed(+b.dataset.rs);
  });
  $('rpSeek').addEventListener('input', e => R.seek(+e.target.value / 1000 * R.total));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && R.on) R.stop(); });
  if (W.scorecard) W.scorecard.paint && W.scorecard.paint();
}

{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.ready && W.state && W.chars && W.ui && W.scorecard) { clearInterval(t); try { boot(W); } catch (e) { console.error('任務重播載入失敗', e); } } else if (++n > 600) clearInterval(t); }, 100); }
