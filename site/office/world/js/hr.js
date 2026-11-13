// 人事：開除與重新聘用（擁有者原話：「開除後他們並不會完全消失，而是跑到公司外面的無業遊民區」）。
// 規則：
//   · CEO 不可被開除；可開除單一同事或整個部門；一定先跳確認框（列出對象、任務數、選「任務交給誰」，要按兩次才會執行）。
//   · 演出：收紙箱 → 向大家揮手 → 走出大門 → 到無業遊民區；那裡閒晃、坐長椅、烤火、睡毯子。沒有任何負面特效。
//   · 他們仍是辦公室的人：點得到、看得到資訊卡（開除日期、原因、在職期間完成的任務），可以「重新聘用」走回座位。
//   · 任務轉交：他手上未完成與進行中的任務交給指定的人（預設 CEO）；轉交後接手者的資訊卡與部門佈告欄的數字跟著變，重新聘用就還回去。
//   · 開除狀態存在 localStorage（鍵 aiOffice.hr.v1，包 try/catch）；之後要存後端，只要換掉 store（load／save，save 可回傳 Promise）。
import { mmdd } from './state.js';

const LS = 'aiOffice.hr.v1';
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const R = (a, b) => a + Math.random() * (b - a), rnd = a => a[Math.floor(Math.random() * a.length)];
const localStore = {
  load() { try { return JSON.parse(localStorage.getItem(LS) || 'null'); } catch (e) { return null; } },
  save(o) { try { localStorage.setItem(LS, JSON.stringify(o)); return true; } catch (e) { return false; } },
};

export function createHR(W, X) {
  const { ui, director: D, state: S } = X, C = id => W.chars.get(id), pos = c => ({ x: c.object3D.position.x, z: c.object3D.position.z });
  const H = { fired: new Map(), store: X.store || localStore, outside: W.outside };
  const O = () => W.outside, stamp = ms => `${mmdd(ms)} ${new Date(ms + 8 * 3600000).toISOString().slice(11, 16)}`;
  W.hrStore = H.store;

  // ───────── 存取 ─────────
  function persist() {
    const o = { v: 1, fired: Object.fromEntries([...H.fired].map(([k, r]) => [k, r])) };
    try { const r = H.store.save(o); if (r && r.catch) r.catch(e => console.warn('開除狀態存後端失敗', e)); } catch (e) { console.warn('開除狀態存不進去', e); }
  }
  const saved = H.store.load();
  if (saved && saved.fired) for (const [id, r] of Object.entries(saved.fired)) if (id !== 'ceo' && W.members.has(id)) H.fired.set(id, r);

  H.isFired = id => H.fired.has(id);
  H.recordOf = id => H.fired.get(id) || null;
  H.statusOf = c => { const r = H.fired.get(c.spec.id); return r ? `待業中・${mmdd(r.at)}` : ''; };
  H.activeCount = deptId => { const d = W.org.departments.find(q => q.id === deptId); return d ? d.members.filter(m => !H.fired.has(m.id)).length : 0; };
  H.nameOf = id => (id === 'ceo' ? 'CEO' : (W.members.get(id) || {}).nick || id);

  // ───────── 任務帳：資訊卡與佈告欄的數字（ui.progress 會經過這裡） ─────────
  // base 是示範資料產生的固定清單；這裡疊上：① 被開除的人只留已完成 ② 接手別人轉來的任務 ③ 狀態層裡即時派出／交件的任務
  H.adjust = (spec, base) => {
    const id = spec.id, rec = H.fired.get(id); let list = base.list.slice();
    if (rec) list = list.filter(x => x.s === 3);
    else for (const r of H.fired.values()) if (r.to === id) for (const t of r.moved) list.push({ s: t.s, title: `${t.title}（接手自${r.nick}）`, t: t.t, from: r.nick });
    const live = W.jobs ? W.jobs.live(id) : { doing: null, done: [] };
    if (!rec && live.doing) list.unshift({ s: 2, title: live.doing, t: stamp(S.now()) });
    for (const d of live.done) list.push({ s: 3, title: d.title, t: stamp(d.t) });
    const ord = { 2: 0, 1: 1, 3: 2 }; list = list.map((x, i) => ({ x, i })).sort((a, b) => ord[a.x.s] - ord[b.x.s] || a.i - b.i).map(o => o.x);
    const n = k => list.filter(x => x.s === k).length, f = k => (list.find(x => x.s === k) || {}).t || '';
    return { ...base, list, nDone: n(3), nDoing: n(2), nTodo: n(1), lastDone: f(3) || '—', lastDoing: f(2) || '—', nextTodo: f(1) };
  };
  H.unfinishedOf = id => { const p = ui.baseProgress(W.members.get(id) || { id }); const out = p.list.filter(x => x.s !== 3).map(x => ({ s: x.s, title: x.title, t: x.t })); const lv = W.jobs ? W.jobs.live(id) : null; if (lv && lv.doing) out.unshift({ s: 2, title: lv.doing, t: stamp(S.now()) }); return out; };

  // ───────── 遊民區：挑位子、走路 ─────────
  const pickStand = id => { const o = O(), free = o.stands.filter(s => !s.taken || s.taken === id); const s = rnd(free.length ? free : o.stands); s.taken = id; return s; };
  const freeAll = id => { const o = O(); [...o.stands, ...o.seats, ...o.mats].forEach(s => { if (s.taken === id) s.taken = null; }); };
  const pathTo = (c, x, z) => { const p = pos(c), path = W.nav.findPath(p, { x, z }); return path && path.length > 1 ? path : [p, { x, z }]; };
  async function walkTo(c, x, z, speed = 1.7) { const tok = c.lifeTok; const ok = await c.walkTo(pathTo(c, x, z), { speed }); return ok && c.lifeTok === tok; }

  // ───────── 演出：收拾 → 揮手 → 走出大門 → 無業遊民區 ─────────
  function markFired(c) { c.jobless = true; c.busy = true; c.sleeping = false; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.jtok = (c.jtok || 0) + 1; c.lifeTok = (c.lifeTok || 0) + 1; X.pilot.releaseIf(c); }
  function seatClear(c) { D.release(c); const s = W.spots.find(q => q.name === 'seat:' + c.spec.id); if (s && s.taken === c.spec.id) s.taken = null; if (c.homeSpot && c.homeSpot.taken === c.spec.id) c.homeSpot.taken = null; c.homeSpot = null; c.atDesk = false; }
  async function walkOut(c, idx) {
    const reduce = W.reduceMotion || matchMedia('(prefers-reduced-motion: reduce)').matches, tok = c.lifeTok; c.hrBusy = true;
    const gone = () => c.lifeTok !== tok;
    await W.sleep(idx * 0.45); if (gone()) return;
    if (!reduce) {
      c.setAction('box'); c.say('我先收拾一下…', 1.8); c.emote('dots', 1.6); await W.sleep(1.9); if (gone()) return;
      seatClear(c); c.setAction('box');
      const door = W.findSpots('door_out')[0]; const ok = await D.goTo(c, door, { speed: 1.9 }); door.taken = null; if (gone() || !ok) { if (!gone()) c.hrBusy = false; return; }
      c.setAction('wave'); c.say('謝謝大家，再見～', 2); await W.sleep(1.5); if (gone()) return; c.setAction('box');
      const t = pickStand(c.spec.id); const ok2 = await walkTo(c, t.x, t.z, 1.8); if (gone()) return;
      if (!ok2) c.standAt(t.x, t.z, t.face);
      c.standAt(c.object3D.position.x, c.object3D.position.z, t.face); c.setAction('idle'); c.setExpression('neutral', 0.1);
    } else { seatClear(c); const t = pickStand(c.spec.id); c.standAt(t.x, t.z, t.face); c.setAction('idle'); }
    c.hrBusy = false; c.lifeAt = W.time + R(1.5, 4);
  }
  H.placeInstant = c => { markFired(c); seatClear(c); const t = pickStand(c.spec.id); c.stop(false); c.standAt(t.x, t.z, t.face); c.setAction('idle'); c.hrBusy = false; c.lifeAt = W.time + R(1, 5); };

  // ───────── 開除 ─────────
  H.fire = async (ids, o = {}) => {
    ids = [...new Set(ids)].filter(id => id !== 'ceo' && W.chars.has(id) && !H.fired.has(id));
    if (!ids.length) return [];
    let to = o.to || 'ceo'; if (to !== 'ceo' && (!W.chars.has(to) || ids.includes(to) || H.fired.has(to))) to = 'ceo';
    const at = Date.now(); let moved = 0;
    for (const id of ids) {
      const c = C(id), spec = c.spec, list = H.unfinishedOf(id);
      for (const r of H.fired.values()) if (r.to === id) r.to = to;            // 他之前接手的任務，改轉給新的接手者
      H.fired.set(id, { id, at, reason: String(o.reason || '').slice(0, 40), to, moved: list, nick: spec.nick, dept: spec.dept || '', zh: spec.zh || '' }); moved += list.length;
      const a = S.agents.get(id); if (a) { a.phase = 'idle'; a.task = ''; a.tool = null; }
    }
    persist();
    ids.forEach((id, i) => { const c = C(id); markFired(c); if (c.spot && c.spot.taken === id) { /* 座位在 walkOut 清掉 */ } walkOut(c, i); });
    ui.toast(`${ids.length > 1 ? ids.length + ' 位同事' : H.nameOf(ids[0])}離開了公司，${moved} 項任務交給${H.nameOf(to)}`);
    ui.afterHr && ui.afterHr(); S.say(`${ids.map(H.nameOf).join('、')}離開了公司`);
    return ids;
  };

  // ───────── 重新聘用 ─────────
  H.rehire = async id => {
    const rec = H.fired.get(id), c = C(id); if (!rec || !c) return false;
    H.fired.delete(id); persist(); freeAll(id);
    const tok = c.lifeTok = (c.lifeTok || 0) + 1; c.hrBusy = true; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.stop(false); c.setAction('idle');
    const seat = W.spots.find(q => q.name === 'seat:' + id); c.homeSpot = null;
    if (seat && seat.taken && seat.taken !== id) c.homeSpot = W.spots.find(q => q.name === 'spare' && !q.taken) || W.spots.find(q => q.name === 'reserve' && !q.taken) || null;   // 原座位被占了：換新座位
    ui.toast(`${c.spec.nick}重新回到公司`); S.say(`${c.spec.nick}回到公司`); ui.afterHr && ui.afterHr();
    const reduce = W.reduceMotion || matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduce) {
      c.say('我回來了！', 2); const door = W.findSpots('door_in')[0], ok = await c.walkTo(pathTo(c, door.x, door.z), { speed: 2 });
      if (c.lifeTok !== tok) return true; if (!ok) c.standAt(door.x, door.z, 0);
      c.jobless = false; c.setAction('wave'); c.setExpression('happy', 1.6); await W.sleep(1.4); if (c.lifeTok !== tok) return true;
      const fans = [...W.chars.values()].filter(q => q !== c && q.state === 'sit' && !q.busy && !q.jobless && !q.sleeping).slice(0, 5); fans.forEach(q => { q.setAction('clap', { duration: 2.4 }); q.setExpression('happy', 2); });   // 大家鼓掌
    }
    c.jobless = false; c.busy = true;
    if (reduce) { const s = c.homeSpot || seat; if (s && s.seat) { D.release(c); s.taken = id; c.spot = s; c.sitAt(s.seat, { instant: true }); c.atDesk = true; c.setAction('type'); } }
    else await D.goHome(c, { speed: 2.2 });
    c.busy = !!(W.jobs && W.jobs.holds(c)); c.hrBusy = false; c.workAt = W.time + 3; ui.afterHr && ui.afterHr(); return true;
  };

  // ───────── 待業中的日子：閒晃、坐長椅、烤火、睡毯子 ─────────
  async function life(c) {
    const o = O(), id = c.spec.id, tok = c.lifeTok = (c.lifeTok || 0) + 1, gone = () => c.lifeTok !== tok; c.hrBusy = true;
    try {
      freeAll(id); const r = Math.random(), p = pos(c);
      if (!o.inZone(p.x, p.z)) { const t = pickStand(id); await walkTo(c, t.x, t.z); return; }
      const seat = r < 0.34 ? o.seats.find(s => !s.taken) : null, mat = !seat && r < 0.5 ? o.mats.find(s => !s.taken) : null;
      if (seat) {
        seat.taken = id; if (!await walkTo(c, seat.ap.x, seat.ap.z)) return; c.faceTo(seat.seat.x, seat.seat.z); c.sitAt(seat.seat); await W.sleep(0.9); if (gone()) return;
        c.setAction(rnd(['idle', 'idle', 'phone', 'drink'])); await W.sleep(R(8, 14)); if (gone()) return;
        c.setAction('idle'); await c.walkTo([pos(c), { x: seat.ap.x, z: seat.ap.z }], { speed: 1.5 });
      } else if (mat) {
        mat.taken = id; if (!await walkTo(c, mat.x, mat.z)) return; c.standAt(mat.x, mat.z, mat.face); c.setAction('sleep'); c.emote('zzz', 3); await W.sleep(R(9, 15)); if (gone()) return; c.setAction('idle');
      } else {
        const t = pickStand(id); if (!await walkTo(c, t.x, t.z)) return; c.faceTo(c.object3D.position.x + Math.sin(t.face), c.object3D.position.z + Math.cos(t.face)); c.setAction('idle');
        if (Math.random() < 0.25) c.emote(rnd(['dots', 'note', 'heart']), 1.6);
        await W.sleep(R(5, 9));
      }
    } finally { if (!gone()) { c.hrBusy = false; c.lifeAt = W.time + R(1.5, 5); } }
  }
  let nextLife = 0;
  H.tick = () => {
    if (!H.fired.size || W.time < nextLife) return; nextLife = W.time + 0.5;
    for (const id of H.fired.keys()) {
      const c = C(id); if (!c || !c.jobless || c.hrBusy || c.state === 'held' || c._path || c.piloted) continue;
      if (W.time >= (c.lifeAt || 0)) life(c);
    }
  };

  // ───────── 確認框 ─────────
  let dlg = null;
  const closeDlg = () => { if (dlg) { dlg.remove(); dlg = null; document.body.classList.remove('dlg-open'); } };
  H.closeDlg = closeDlg;
  H.ask = (ids, label) => {
    ids = ids.filter(id => id !== 'ceo' && W.chars.has(id) && !H.fired.has(id)); closeDlg();
    if (!ids.length) { ui.toast('沒有可以開除的對象'); return null; }
    const rows = ids.map(id => { const c = C(id), s = c.spec, l = H.unfinishedOf(id), td = l.filter(x => x.s === 1).length, dg = l.filter(x => x.s === 2).length; return { id, s, td, dg }; });
    const total = rows.reduce((n, r) => n + r.td + r.dg, 0), cands = [...W.chars.values()].filter(c => !c.spec.pet && !c.spec.isCeo && !ids.includes(c.spec.id) && !H.fired.has(c.spec.id));
    const title = label ? `開除「${esc(label)}」全部 ${ids.length} 位？` : `開除 ${esc(rows[0].s.nick)}？`;
    dlg = document.createElement('div'); dlg.className = 'dlg-back'; dlg.id = 'fireDlg'; dlg.setAttribute('role', 'dialog'); dlg.setAttribute('aria-modal', 'true'); dlg.setAttribute('aria-labelledby', 'fdT');
    dlg.innerHTML = `<div class="dlg"><h3 id="fdT">${title}</h3>
      <ul class="fd-list">${rows.map(r => `<li><b>${esc(r.s.nick)}</b><span>${esc(r.s.id)}・${esc(r.s.zh)}</span><em>未完成 ${r.td}・進行中 ${r.dg}</em></li>`).join('')}</ul>
      <p class="fd-sum" id="fdSum">共 ${total} 項未完成或進行中的任務</p>
      <label class="fd-f">這些任務交給誰<select id="fireTo"><option value="ceo" selected>CEO</option>${cands.map(c => `<option value="${esc(c.spec.id)}">${esc(c.spec.nick)}・${esc(c.spec.zh)}</option>`).join('')}</select></label>
      <label class="fd-f">原因（選填）<input id="fireReason" maxlength="40" autocomplete="off"></label>
      <p class="fd-warn" id="fdWarn" hidden>再按一次「確定開除」才會執行。他們會搬到公司外面的無業遊民區，隨時可以重新聘用。</p>
      <div class="dlg-acts"><button class="btn" id="fireCancel">取消</button><button class="btn on" id="fireGo">開除</button></div></div>`;
    $('app').append(dlg); document.body.classList.add('dlg-open'); let armed = false;
    const go = $('fireGo'); $('fireCancel').focus();
    dlg.addEventListener('click', e => {
      if (e.target === dlg || e.target.closest('#fireCancel')) { closeDlg(); return; }
      if (e.target.closest('#fireGo')) {
        if (!armed) { armed = true; $('fdWarn').hidden = false; go.textContent = '確定開除'; go.classList.add('danger'); return; }
        const to = $('fireTo').value, reason = $('fireReason').value; closeDlg(); H.fire(ids, { to, reason });
      }
    });
    dlg.addEventListener('change', e => { if (e.target.id === 'fireTo' && armed) { armed = false; $('fdWarn').hidden = true; go.textContent = '開除'; go.classList.remove('danger'); } });
    return dlg;
  };
  H.askDept = deptId => { const d = W.org.departments.find(q => q.id === deptId); if (!d) return null; return H.ask(d.members.map(m => m.id), d.name); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && dlg) { e.preventDefault(); closeDlg(); } });

  // ───────── 開機：套用上次的開除狀態（人直接在遊民區，不重演走出去） ─────────
  H.boot = () => { for (const id of H.fired.keys()) { const c = C(id); if (c) H.placeInstant(c); } };
  return H;
}
