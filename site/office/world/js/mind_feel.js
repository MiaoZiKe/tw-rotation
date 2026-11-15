// 情緒加深層（2026-11-15，擁有者：「被燒之後的情緒要更多，被打、被照顧都是。」）。
// 接在 mind.js 之下（由 mind.js 建立並傳入它的工具函式），負責「跨時間、因人而異」的那一半：
//   ① 對你的態度 rel（-1～1）：被你丟、被你敲就下降（敏感的人降得多、也久），摸頭、餵點心、救他、獎勵就慢慢回升；
//      rel 很低 → 你靠近時後退、被點到會戒備；rel 很高 → 你靠近時揮手、主動走過來。
//   ② 怕火 fear（0～1）：被燒之後的餘悸。怕火的人經過營火會繞遠、在火邊發抖；夜晚靠近路燈火光會緊張；
//      存進 localStorage（隔天還記得「昨天被燒」），敏感的人記得久、樂觀的人很快忘。
//   ③ 被欺負的分級（最近 5 分鐘內被丟／被敲／撞到的加權次數）：1 小委屈 → 2 生氣跺腳或難過 → 3 害怕躲你，並跑去找 CEO 告狀（外向、好勝）或躲到角落（內向）。
//   ④ 被燒的分階段（驚嚇→疼痛狼狽→餘悸→怪不怪你→找朋友訴苦／同事安慰）、被泳池救火（鬆一口氣＋濕答答）。
//   ⑤ 運動事件（sport_start／sport_score／sport_end）：贏了開心、輸了不甘心想再來一場、和對手的關係變好。
// 不羞辱原則：旁人只關心、安慰、陪著，不嘲笑、不圍觀；欺負別人的永遠只有「你」，其他同事不會。
// 只用角色的公開介面（setExpression／setAction／emote／say／walkTo／faceTo）與 mind.js 傳進來的 scene／face／act／say。
const LS = 'aiOffice.mind.feel.v1';
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const rnd = a => a[Math.floor(Math.random() * a.length)], R = (a, b) => a + Math.random() * (b - a);

export function createFeel(W, K) {
  const { people, C, scene, endScene, face, say, act, affect, remember, record, canAct, awake, pos, dist, hash, D, A, emit, mindOf, downPt } = K;
  const F = { youOverride: null, stats: { detours: 0, retreats: 0, waves: 0, approaches: 0 } };
  let SAVED = {}; try { SAVED = (JSON.parse(localStorage.getItem(LS) || '{}') || {}).m || {}; } catch (e) { SAVED = {}; }
  let saveT = 0;
  const dirty = m => {
    const f = m.f; SAVED[m.id] = { rel: Math.round(f.rel * 100) / 100, fear: Math.round(f.fear * 100) / 100, burnAt: f.burnAt, rap: f.rap, at: Date.now() };
    if (!saveT) saveT = setTimeout(() => { saveT = 0; try { localStorage.setItem(LS, JSON.stringify({ v: 1, m: SAVED })); } catch (e) { /* 存不進去就算了 */ } }, 1500);
  };

  // ───────── 每個人的「感受」狀態 ─────────
  function of(m) {
    if (m.f) return m.f;
    const s = SAVED[m.id] || {}, hrs = s.at ? Math.max(0, (Date.now() - s.at) / 3600e3) : 0, t = m.t;   // 隔了幾小時：敏感的人記得久、樂觀的人忘得快
    m.f = { rel: (s.rel || 0) * Math.exp(-hrs / (40 * (.4 + t.sens))), fear: (s.fear || 0) * Math.exp(-hrs / (40 * (.4 + t.sens) * (1.3 - t.opt))), burnAt: s.burnAt || 0, rap: s.rap || {},
      hits: [], q: [], cd: {}, mode: null, wetUntil: 0, stage: null, blame: false, fearYou: 0, rematch: null, wonAt: 0, thanksAt: 0, fearT: 0, detKey: null, detPi: -1, comfortAt: -99, ventDone: false };
    return m.f;
  }
  F.of = of;
  const you = () => F.youOverride || (W.camera && W.camera.position);
  const nearYou = (c, r) => { const y = you(); if (!y) return false; const p = pos(c); return Math.hypot(y.x - p.x, (y.y || 0) - 0.7, y.z - p.z) < r; };
  const youXZ = () => { const y = you(); return y ? { x: y.x, z: y.z } : null; };

  // ───────── 稍後再做：等心的場景結束、角色有空才做（演出被別的事佔住就等一下） ─────────
  function later(m, delay, fn, o = {}) { of(m).q.push({ at: W.time + delay, until: W.time + delay + (o.wait || 25), fn, cond: o.cond || (() => !m.sc) }); }
  function runQ(c, m) {
    const q = m.f.q; if (!q.length) return;
    for (let i = 0; i < q.length; i++) { const e = q[i]; if (W.time < e.at) continue; if (e.cond(c, m)) { q.splice(i--, 1); try { e.fn(c, m); } catch (er) { console.error('情緒排程例外', er); } } else if (W.time > e.until) q.splice(i--, 1); }
  }

  // ───────── 對你的態度 ─────────
  const relTxt = m => {
    const r = of(m).rel, comp = m.t.comp >= .55;
    if (r <= -.6) return comp ? '還在生你的氣' : '很怕你'; if (r <= -.35) return '有點防備'; if (r <= -.18) return '稍微保持距離';
    if (r >= .6) return '很信任你'; if (r >= .35) return '親近'; if (r >= .18) return '有好感'; return '';
  };
  F.attitude = m => relTxt(m);
  const addRel = (m, d, why) => { const f = of(m); f.rel = clamp(f.rel + d, -1, 1); dirty(m); if (why) f.relWhy = why; };
  F.addRel = addRel;
  const relDecay = (m, d) => {
    const f = m.f, t = m.t;
    if (f.rel < 0) { const tau = (180 + 900 * t.sens) * (1.35 - .9 * t.opt); f.rel += (0 - f.rel) * (1 - Math.exp(-d / tau)); }
    else if (f.rel > 0) f.rel -= f.rel * (1 - Math.exp(-d / 2400));
  };

  // ───────── 被打、被丟、撞到：分級 ─────────
  const wsum = (m, sec) => of(m).hits.filter(h => W.time - h.t < sec).reduce((s, h) => s + h.w, 0);
  F.onHit = (c, m, kind, d = {}) => {
    const f = of(m), t = m.t, w = { throw: 1, bonk: .8, obj: .5 }[kind] || .5;
    // 同一次丟出去只算一次（飛行途中撞牆、彈跳會再送好幾次 knocked）；碰撞類 2 秒內只算一次
    if (!d.upgrade && kind === 'throw' && m.releasedAt != null && f.lastRel === m.releasedAt) return f.tier || 1;
    if (!d.upgrade && kind === 'obj' && f.hits.length && W.time - f.hits[f.hits.length - 1].t < 2) return f.tier || 1;
    if (kind === 'throw' && m.releasedAt != null) f.lastRel = m.releasedAt;
    if (d.upgrade) { const h = f.hits[f.hits.length - 1]; if (h) h.w = Math.max(h.w, 1); } else f.hits.push({ t: W.time, w, kind });
    if (f.hits.length > 8) f.hits.shift();
    if (kind !== 'obj' || d.upgrade) { addRel(m, -.28 * (d.upgrade ? .65 : w) * (.75 + .5 * t.sens) * (1.2 - .5 * t.opt), '被欺負'); f.bullyAt = W.time; }
    const n = wsum(m, 300), tier = n >= 2.4 ? 3 : n >= 1.4 ? 2 : 1; f.tier = tier;
    if (d.upgrade) return tier;
    if (tier === 3 && kind !== 'obj') f.fearYou = W.time + 260 * (1.3 - .6 * t.opt);
    if (tier >= 2 && kind !== 'obj') later(m, kind === 'bonk' ? 2.4 : 6, () => tierScene(c, m, tier));
    record(m, { event: 'hit-tier', kind, tier, n: Math.round(n * 10) / 10 });
    return tier;
  };
  function tierScene(c, m, tier) {
    if (!awake(c) || c.jobless) return; const t = m.t, f = of(m);
    if (tier === 2) {
      const angry = t.comp >= .55 && t.sens < .75;
      scene(c, m, 5, 'feel-tier2', sc => {
        if (angry) sc.at(0, () => { face(c, m, 'angry', 2.6); c.emote('anger', 2.2); say(c, rnd(['又來了！很痛耶！', '不要一直這樣！', '你很過分欸！']), 2, true); act(c, 'slam', { duration: 1.8 }); });
        else if (t.sens >= .5) sc.at(0, () => { face(c, m, 'cry', 3); c.emote('cloud', 2.4); say(c, rnd(['嗚…又…', '為什麼一直這樣…']), 2, true); act(c, 'sob', { duration: 3 }); if (canAct(c)) c.lookAt(downPt(c)); });
        else sc.at(0, () => { face(c, m, 'pout', 2.6); c.emote('dots', 2); say(c, '…夠了喔', 1.8, true); act(c, 'sulk', { duration: 2.4 }); });
        sc.at(3.2, () => { }); sc.on_end(() => { if (!(A() && A().current() === c)) c.lookAt(null); }); K.holdCap(c, m, sc);
      });
      record(m, { event: 'bully-reaction', tier: 2, style: angry ? 'stomp' : t.sens >= .5 ? 'cry' : 'pout', face: angry ? 'angry' : t.sens >= .5 ? 'cry' : 'pout', action: angry ? 'slam' : t.sens >= .5 ? 'sob' : 'sulk' });
    } else if (tier >= 3) {
      f.mode = null; const tell = t.ext >= .45 || t.comp >= .6, ceo = C('ceo');
      scene(c, m, 5, 'feel-tier3', sc => { sc.at(0, () => { face(c, m, 'scared', 2.2); c.emote('sweat', 1.8); say(c, rnd(['不、不要再來了…', '我好怕…']), 1.8, true); }); sc.at(2.4, () => { }); K.holdCap(c, m, sc); });
      record(m, { event: 'bully-reaction', tier: 3, style: tell && ceo && ceo !== c ? 'complain' : 'hide', face: 'scared' });
      later(m, 3, () => { if (tell && ceo && ceo !== c && !ceo.away && !ceo.jobless) complain(c, m, ceo); else hideAway(c, m); }, { cond: (cc, mm) => !mm.sc && canAct(cc), wait: 40 });
    }
  }
  // 小工具：走到某人旁邊做一件事，再走回座位（演出中被打斷就放棄）
  async function visit(c, tgt, o) {
    const D0 = D(); if (!D0 || !canAct(c)) return false; const tok = c.script = (c.script || 0) + 1; c.busy = true;
    try {
      const a = pos(tgt), b = pos(c), L = Math.hypot(b.x - a.x, b.z - a.z) || 1, g = o.gap || 1.3, f = W.nav.nearestFree(a.x + (b.x - a.x) / L * g, a.z + (b.z - a.z) / L * g, 4); if (!f) return false;
      c.setAction('idle'); const ok = await D0.goTo(c, { x: f.x, z: f.z, face: 0 }, { speed: o.speed || 2.4 }); if (c.script !== tok || !ok) return false;
      c.faceTo(a.x, a.z); if (o.at) await o.at(tok, () => c.script === tok); if (c.script !== tok) return false;
      c.setAction('idle'); await D0.goHome(c, { speed: 2.1 }); return true;
    } finally { if (c.script === tok) c.busy = false; }
  }
  async function complain(c, m, ceo) {
    const f = of(m); f.mode = 'complain'; record(m, { event: 'complain-start', to: ceo.spec.nick });
    const ok = await visit(c, ceo, { gap: 1.2, speed: 2.6, at: async (tok, alive) => {
      face(c, m, m.t.sens >= .55 ? 'sad' : 'worried', 4); act(c, 'talk', { duration: 2.2 }, true); say(c, rnd(['報告…一直有人欺負我', '我可以講一件事嗎…我一直被丟']), 2.6, true);
      await W.sleep(2.2); if (!alive()) return;
      ceo.faceTo(pos(c).x, pos(c).z); face(ceo, mindOf(ceo), 'worried', 2.6); say(ceo, rnd(['辛苦了，我知道了', '好，我會處理，先休息一下']), 2.4, true); act(ceo, 'nod', { duration: 1.2 }, true); ceo.emote('heart', 1.6);
      await W.sleep(2); if (!alive()) return; emit('comforted', c.spec.id, { by: ceo.spec.id }); f.relief = W.time;
    } });
    f.mode = null; record(m, { event: 'complain', to: ceo.spec.nick, done: !!ok }); remember(m, 'complained', ceo.spec.nick, '跟' + ceo.spec.nick + '說了被欺負的事');
  }
  async function hideAway(c, m) {
    const f = of(m), D0 = D(); if (!D0 || !canAct(c)) return; const B = W.layout && W.layout.size || { w: 40, d: 34 }, y = youXZ() || { x: 20, z: 17 };
    const cands = [[2, 2], [B.w - 2, 2], [2, B.d - 2], [B.w - 2, B.d - 2]].map(([x, z]) => W.nav.nearestFree(x, z, 5)).filter(Boolean).sort((a, b) => Math.hypot(b.x - y.x, b.z - y.z) - Math.hypot(a.x - y.x, a.z - y.z));
    const tok = c.script = (c.script || 0) + 1; c.busy = true; f.mode = 'hide'; record(m, { event: 'hide-start' });
    try {
      const spot = cands[0]; if (spot) { const ok = await D0.goTo(c, { x: spot.x, z: spot.z, face: 0 }, { speed: 2.6 }); if (c.script !== tok || !ok) return; }
      face(c, m, 'worried', 14); act(c, 'sulk', { duration: 12 }, true); c.emote('dots', 2); say(c, '…（躲一下）', 1.6, true); record(m, { event: 'hide' });
      await W.sleep(14); if (c.script !== tok) return; c.setAction('idle'); await D0.goHome(c, { speed: 2 });
    } finally { f.mode = null; if (c.script === tok) c.busy = false; }
  }

  // ───────── 被燒：分階段 ─────────
  const burnWho = m => m.thrownAt != null && W.time - m.thrownAt < 20;
  F.onBurn = (c, m, d = {}) => {
    const f = of(m); f.stage = 'shock'; f.burnAt = Date.now(); f.ventDone = false; f.thankedC = false; f.blame = burnWho(m) || d.by === 'you' || !!(c._held || c.state === 'held' || (m.grabbedAt != null && W.time - m.grabbedAt < 25));   // 被你拎著放到火上、或剛被你甩出去
    if (f.blame) { f.hits.push({ t: W.time, w: 1.2, kind: 'fire' }); f.bullyAt = W.time; }
    if (f.blame) addRel(m, -.34 * (.75 + .5 * m.t.sens) * (1.2 - .5 * m.t.opt), '被丟進火裡'); dirty(m);
  };
  F.onPain = (c, m) => { of(m).stage = 'pain'; };
  // 疼痛與狼狽：拍身上的灰、喘氣；不同個性的臉不一樣
  F.patDown = (c, m) => {
    const t = m.t, f = of(m); if (c.state === 'walk') return false;
    const fc = t.sens >= .6 ? 'cry' : t.comp >= .6 ? 'angry' : 'ouch';
    face(c, m, fc, 1.5); act(c, 'clap', { duration: 1.4 }, true); c.emote(t.comp >= .6 && t.sens < .6 ? 'anger' : 'sweat', 1.4); say(c, rnd(t.sens >= .6 ? ['痛痛痛…', '好狼狽…'] : t.comp >= .6 ? ['可惡…', '拍掉拍掉…'] : ['拍拍…灰好多', '呼，頭髮都焦了']), 1.6, true);
    record(m, { event: 'pat-down', face: fc, action: 'clap' }); f.pats = (f.pats || 0) + 1; return true;
  };
  F.onRecovered = (c, m) => {
    const f = of(m), t = m.t; f.stage = 'after'; f.fear = clamp(Math.max(f.fear, .45 + .45 * t.sens - .25 * t.opt), .15, 1); f.fearT = W.time; dirty(m);
    // 餘悸之後：怪不怪你
    if (f.blame) later(m, 3.2, () => resent(c, m));
    // 找好朋友訴苦（外向或敏感的人才會；悶著的人自己消化）
    if (t.ext >= .45 || t.sens >= .55) later(m, 6, () => vent(c, m), { cond: (cc, mm) => !mm.sc && canAct(cc) && !cc.away, wait: 50 });
    else record(m, { event: 'bottle-up', face: 'blank' });
  };
  function resent(c, m) {
    if (!awake(c) || c.jobless) return; const t = m.t, q = W.camera && W.camera.position, style = t.comp >= .55 ? 'angry' : t.sens >= .55 ? 'cry' : t.opt >= .6 ? 'shrug' : 'pout';
    scene(c, m, 5, 'feel-resent', sc => {
      sc.at(0, () => {
        if (q && canAct(c)) { c.faceTo(q.x, q.z); }
        if (style === 'angry') { face(c, m, 'angry', 2.8); c.emote('anger', 2); say(c, '剛剛是你把我丟進去的吧！', 2.4, true); act(c, 'slam', { duration: 1.8 }); }
        else if (style === 'cry') { face(c, m, 'cry', 3.2); c.emote('cloud', 2.4); say(c, '…好可怕，你為什麼要這樣', 2.6, true); act(c, 'sob', { duration: 3 }); }
        else if (style === 'shrug') { face(c, m, 'effort', 2.4); say(c, '算了…下次別這樣喔', 2.4, true); act(c, 'shake', { duration: 1.2 }); }
        else { face(c, m, 'pout', 2.8); c.emote('dots', 2); say(c, '…哼', 1.6, true); act(c, 'sulk', { duration: 2.4 }); }
      }); sc.at(3.4, () => { }); K.holdCap(c, m, sc);
    });
    record(m, { event: 'resent', style, face: { angry: 'angry', cry: 'cry', shrug: 'effort', pout: 'pout' }[style] });
  }
  function friendOf(c) {
    let best = null, bs = -9; const f = of(mindOf(c));
    for (const o of people()) {
      if (o === c || !awake(o) || o.jobless || o.piloted || !canAct(o) || o.state === 'held') continue; const d = dist(c, o); if (d > 16) continue;
      const s = (o.spec.dept && o.spec.dept === c.spec.dept ? .35 : 0) + (hash(o.spec.id + c.spec.id) % 100) / 250 + (f.rap[o.spec.id] || 0) - d * .012; if (s > bs) { bs = s; best = o; }
    }
    return best;
  }
  async function vent(c, m) {
    const f = of(m), fr = friendOf(c); if (!fr) { record(m, { event: 'no-friend' }); return; } f.mode = 'vent';
    record(m, { event: 'vent-start', to: fr.spec.nick });
    const ok = await visit(c, fr, { gap: 1.2, speed: 2.5, at: async (tok, alive) => {
      const mf = mindOf(fr); fr.faceTo(pos(c).x, pos(c).z); fr.workAt = Math.max(fr.workAt || 0, W.time + 9);
      face(c, m, m.t.sens >= .55 ? 'sad' : 'worried', 4); act(c, 'talk', { duration: 2.4 }, true); say(c, rnd(['我跟你說…剛剛被火燒到了…', '你知道嗎，我剛剛差點變成烤的…']), 2.6, true);
      await W.sleep(2.4); if (!alive()) return;
      face(fr, mf, 'worried', 3); act(fr, 'listen', { duration: 2.4 }, true); fr.emote('heart', 1.8); say(fr, rnd(['好可怕…沒事了，辛苦你了', '你還好嗎？我陪你一下']), 2.4, true);
      await W.sleep(2.2); if (!alive()) return; face(fr, mf, 'smile', 2); act(fr, 'nod', { duration: 1.2 }, true);
      emit('comforted', c.spec.id, { by: fr.spec.id }); f.rap[fr.spec.id] = clamp((f.rap[fr.spec.id] || 0) + .15, 0, .6); mf && (of(mf).rap[c.spec.id] = clamp((of(mf).rap[c.spec.id] || 0) + .1, 0, .6)); f.ventDone = true; dirty(m);
      remember(mf, 'comforted', c.spec.nick, '安慰了' + c.spec.nick); await W.sleep(1.4);
    } });
    f.mode = null; record(m, { event: 'vent', to: fr.spec.nick, done: !!ok });
  }
  F.onComforted = (c, m, d = {}) => {
    const f = of(m); f.comfortAt = W.time; const by = d.by && C(d.by); remember(m, 'comforted', by ? by.spec.nick : '', by ? by.spec.nick + '來安慰我' : '被安慰了');
    affect(m, { val: .1 + .06 * m.t.sens, stress: -.06 }, '同事來安慰了', 120);
    if (!m.sc) scene(c, m, 3, 'comforted', sc => { sc.at(0, () => { face(c, m, m.t.ext <= .4 ? 'shy' : 'grateful', 2.2); if (by) say(c, '謝謝你…', 1.6, true); c.emote('heart', 1.4); }).at(2.2, () => { }); K.holdCap(c, m, sc); });
  };
  // 被泳池救火（extinguished cause:'pool'／splashed）：鬆一口氣、濕答答
  F.onPool = (c, m, d = {}) => {
    const f = of(m), t = m.t, was = m.burned || f.stage === 'shock' || f.stage === 'pain'; f.wetUntil = W.time + 70 + 40 * t.sens; f.stage = 'wet'; m.burned = false;
    const rescue = was && (d.by === 'you' || d.rescue); if (rescue) { addRel(m, .3 * (1 + t.ext * .3), '被你救了'); f.blame = false; }
    affect(m, { val: was ? .16 : -.04, stress: was ? -.1 : .03 }, rescue ? '被你救了，濕答答的' : was ? '被水澆熄了，濕答答的' : '被水潑到，濕答答的', 160); remember(m, 'splashed', rescue ? '你' : '', '被水救了');
    scene(c, m, 9, 'feel-wet', sc => {
      sc.at(0, () => { face(c, m, 'surprised', .9); c.emote('exclaim', 1); act(c, 'flail', { duration: .9 }, true); });
      sc.at(.9, () => { if (was) { face(c, m, 'relieved', 2.6); say(c, rnd(['呼～得救了…', '好險…火滅了']), 2, true); c.emote('note', 1.4); } else { face(c, m, 'worried', 2.6); say(c, '哇！冷冷冷', 1.8, true); } });
      sc.at(3.5, () => {
        if (t.comp >= .55 && t.sens < .6) { face(c, m, 'sulkf', 2.8); say(c, '全身都濕了…', 2, true); act(c, 'slam', { duration: 1.5 }); }
        else if (t.opt >= .6) { face(c, m, 'smile', 2.8); say(c, '至少涼快了！', 2, true); act(c, 'shake', { duration: 1.2 }); }
        else { face(c, m, 'worried', 2.8); c.emote('sweat', 1.8); say(c, '好冷…', 1.6, true); act(c, 'fidget', { duration: 2.4 }); }
      });
      if (rescue) sc.at(6.5, () => { face(c, m, t.ext <= .4 ? 'shy' : 'grateful', 2.4); c.emote('heart', 1.6); say(c, '謝謝你救了我…', 2, true); });
      sc.at(9.5, () => { }); K.holdCap(c, m, sc);
    });
    record(m, { event: 'pool', rescue: !!rescue, face: 'surprised>relieved', action: 'flail>shiver' });
    F.witnessCare && F.witnessCare(c);
  };
  F.onRescue = (c, m) => { addRel(m, .3, '被你救了'); };

  // ───────── 被照顧 ─────────
  F.onCare = (c, m, kind) => {
    const f = of(m), before = f.rel, w = { pet: .06, feed: .1, reward: .05 }[kind] || .05;
    addRel(m, w * (1 + m.t.ext * .3)); f.thanksAt = W.time;
    if (before < .3 && f.rel >= .3) { record(m, { event: 'warm-up', rel: Math.round(f.rel * 100) / 100 }); }
  };
  F.onDodge = (c, m) => { addRel(m, .04); };   // 嘗試靠近就算有一點點誠意
  F.onForgive = (c, m) => {
    const f = of(m); f.rel = Math.max(f.rel + .2, -.24); dirty(m); f.blame = false; later(m, 1.8, () => {
      if (!awake(c) || c.jobless || m.sc) return;
      scene(c, m, 4, 'feel-forgive', sc => { sc.at(0, () => { say(c, m.t.comp >= .55 ? '…下次輕一點喔' : '嗯…我不氣了', 2, true); c.emote('heart', 1.4); face(c, m, m.t.ext <= .4 ? 'shy' : 'smile', 2.2); }).at(2.3, () => { }); K.holdCap(c, m, sc); });
    });
  };

  // ───────── 運動事件 ─────────
  const norm = (id, d = {}) => {
    const opp = d.opponent || d.vs || d.against || d.rival || (d.opponents && d.opponents[0]) || (d.opp) || null, oid = opp && typeof opp === 'object' ? (opp.id || opp.spec && opp.spec.id) : opp;
    const r = String(d.result || d.outcome || '').toLowerCase(), win = d.win === true || d.won === true || r === 'win' || r === 'won' || r === '贏', lose = d.win === false || d.won === false || d.lose === true || r === 'lose' || r === 'lost' || r === '輸', draw = d.draw === true || r === 'draw' || r === 'tie' || r === '平';
    return { oid, oc: oid && C(oid), win, lose: lose && !win, draw: draw && !win && !lose, sport: d.sport || d.kind || d.game || '', scorer: d.scorer || d.by || (d.scored === false ? oid : id), score: d.score };
  };
  const rapUp = (m, oid, v) => { if (!oid) return; const f = of(m); f.rap[oid] = clamp((f.rap[oid] || 0) + v, 0, .6); dirty(m); };
  F.onSport = (kind, id, d) => {
    const c = C(id), m = mindOf(c); if (!c || !m || c.jobless || c.sleeping) return; const n = norm(id, d), t = m.t, f = of(m), on = n.oc && n.oc.spec.nick || '對手';
    if (kind === 'start') {
      const style = t.comp >= .6 ? 'fierce' : t.ext >= .62 ? 'fun' : 'calm';
      scene(c, m, 4, 'sport-start', sc => { sc.at(0, () => { face(c, m, style === 'fierce' ? 'smug' : style === 'fun' ? 'happy' : 'effort', 2.4); say(c, style === 'fierce' ? '來吧，我不會輸的！' : style === 'fun' ? '開始囉～衝啊！' : '請多指教', 1.8, true); c.emote(style === 'fierce' ? 'star' : 'note', 1.4); if (n.oc) c.faceTo(pos(n.oc).x, pos(n.oc).z); }).at(2.5, () => { }); K.holdCap(c, m, sc); });
      affect(m, { val: .08, energy: .05 }, '要比賽了' + (n.oc ? '，對手是' + on : ''), 120); record(m, { event: 'sport', phase: 'start', style, face: style === 'fierce' ? 'smug' : style === 'fun' ? 'happy' : 'effort', opp: on });
    } else if (kind === 'score') {
      const mine = n.scorer === id || n.scorer == null;
      if (mine) { const fc = t.ext >= .62 ? 'laugh' : t.comp >= .6 ? 'fistpump' : 'happy'; face(c, m, fc, 1.8); c.emote('star', 1.4); act(c, t.comp >= .6 ? 'fist' : 'cheer', { duration: 1.4 }); affect(m, { val: .1 }, '得分了', 90); record(m, { event: 'sport', phase: 'score', mine: true, face: fc }); }
      else { const fc = t.comp >= .6 ? 'sulkf' : t.sens >= .6 ? 'worried' : 'surprised'; face(c, m, fc, 1.6); if (t.comp >= .6) { c.emote('anger', 1.2); say(c, '可惡！', 1.2, true); } else say(c, rnd(['好球！', '厲害…']), 1.2, true); affect(m, { val: -.05 * (.6 + t.comp) }, on + '得分了', 90); record(m, { event: 'sport', phase: 'score', mine: false, face: fc }); }
    } else if (kind === 'end') {
      rapUp(m, n.oid, .2); if (n.oc) rapUp(mindOf(n.oc), id, .2);
      if (n.win) {
        const st = t.ext >= .62 ? 'burst' : t.comp >= .6 ? 'fist' : t.ext <= .4 ? 'shy' : 'warm'; f.wonAt = W.time;
        affect(m, { val: .3 * (1 + .3 * t.opt), energy: -.04, stress: -.12 }, '贏了' + (n.oc ? '和' + on + '的比賽' : '比賽'), 200); remember(m, 'sport-win', on, '贏了和' + on + '的比賽');
        scene(c, m, 6, 'sport-win-' + st, sc => {
          sc.at(0, () => { const fc = { burst: 'laugh', fist: 'fistpump', shy: 'smile', warm: 'happy' }[st]; face(c, m, fc, 2.2); c.emote('star', 1.6); say(c, { burst: '耶～我贏啦！', fist: '漂亮！', shy: '欸嘿…贏了', warm: '打得很開心～' }[st], 1.8, true); act(c, { burst: 'cheer', fist: 'fist', shy: 'shy', warm: 'nod' }[st], { duration: 1.6 }); });
          if (n.oc) sc.at(2.4, () => { c.faceTo(pos(n.oc).x, pos(n.oc).z); face(c, m, 'smile', 2); say(c, '打得好！謝謝你陪我打', 2, true); act(c, 'clap', { duration: 1.4 }); });
          sc.at(5, () => { }); K.holdCap(c, m, sc);
        });
        record(m, { event: 'sport', phase: 'end', result: 'win', style: st, face: { burst: 'laugh', fist: 'fistpump', shy: 'smile', warm: 'happy' }[st], opp: on });
      } else if (n.lose) {
        const st = t.comp >= .55 ? 'fierce' : t.sens >= .6 ? 'sad' : 'calm';
        affect(m, { val: -.26 * (.7 + .5 * t.sens + .3 * t.comp) * (1.15 - .4 * t.opt), stress: .06 }, '輸了不甘心，想再來一場' + (n.oc ? '（對手：' + on + '）' : ''), 220); remember(m, 'sport-lose', on, '輸給' + on);
        f.rematch = { opp: n.oid, nick: on, until: W.time + 300 };
        scene(c, m, 6, 'sport-lose-' + st, sc => {
          sc.at(0, () => {
            if (st === 'fierce') { face(c, m, 'sulkf', 2.2); c.emote('anger', 1.6); say(c, '不甘心！再來一場！', 2.2, true); act(c, 'slam', { duration: 1.6 }); }
            else if (st === 'sad') { face(c, m, 'sad', 2.6); c.emote('cloud', 1.8); say(c, '…輸了。', 1.6, true); act(c, 'sob', { duration: 2.4 }); }
            else { face(c, m, 'pout', 2.2); say(c, '輸了…下次再戰', 2, true); }
          });
          sc.at(2.8, () => { if (n.oc) c.faceTo(pos(n.oc).x, pos(n.oc).z); face(c, m, 'effort', 2.4); say(c, n.oc ? '再來一場好不好？' : '我要再練一下', 2, true); act(c, 'raise', { duration: 1.6 }); });
          sc.at(5.5, () => { }); K.holdCap(c, m, sc);
        });
        record(m, { event: 'sport', phase: 'end', result: 'lose', style: st, face: st === 'fierce' ? 'sulkf' : st === 'sad' ? 'sad' : 'pout', want: 'rematch', opp: on });
      } else {
        affect(m, { val: .1 }, '和' + on + '打成平手', 120); scene(c, m, 6, 'sport-draw', sc => { sc.at(0, () => { face(c, m, 'smile', 2.4); say(c, '平手！下次再分勝負', 2, true); }).at(2.5, () => { }); K.holdCap(c, m, sc); });
        record(m, { event: 'sport', phase: 'end', result: 'draw', face: 'smile', opp: on });
      }
    }
  };

  // ───────── 每個人每 0.25 秒：怕火、你靠近時的反應、排程 ─────────
  const fireInfo = () => { const fr = W.fire; return fr && fr.on !== false && fr.center ? fr.center : null; };
  const nightK = () => (W.daytime && W.daytime.outL ? W.daytime.outL.k : 0) || 0;
  const flat = (c, x, z) => Math.hypot(pos(c).x - x, pos(c).z - z);
  F.tickChar = (c, m, now, d) => {
    const f = of(m); if (!awake(c) || c.jobless) { runQ(c, m); return; }
    relDecay(m, d); runQ(c, m);
    if (f.fear > 0) { const tau = (500 + 1500 * m.t.sens) * (1.3 - m.t.opt); f.fear -= f.fear * (1 - Math.exp(-d / tau)); if (f.fear < .02) f.fear = 0; }
    if (now < f.wetUntil && now >= (f.cd.shiver || 0) && !m.sc && canAct(c) && c.state !== 'walk') { f.cd.shiver = now + R(6, 10); act(c, 'fidget', { duration: 2 }); face(c, m, 'worried', 2); c.emote('sweat', 1.4); }
    // 怕火
    const fc = fireInfo(), moving = c.state === 'walk', fearNow = f.fear;
    if (fc && fearNow >= .25) {
      const fd = flat(c, fc.x, fc.z);
      if (moving && c._path && c._pi < c._path.length && (f.detKey !== c._path || f.detPi !== c._pi)) {          // 繞遠：下一段路若會經過火堆附近，就插一個繞開的點
        f.detKey = c._path; f.detPi = c._pi; const p = pos(c), tg = c._path[c._pi], rad = 3 + 2.6 * fearNow;
        const sx = tg.x - p.x, sz = tg.z - p.z, sl = sx * sx + sz * sz, u = sl > 1e-9 ? clamp(((fc.x - p.x) * sx + (fc.z - p.z) * sz) / sl, 0, 1) : 0, qx = p.x + sx * u, qz = p.z + sz * u, dd = Math.hypot(qx - fc.x, qz - fc.z);
        if (dd < rad && Math.hypot(p.x - fc.x, p.z - fc.z) > 1.2) {
          let ox = qx - fc.x, oz = qz - fc.z, L = Math.hypot(ox, oz); if (L < .05) { ox = -sz; oz = sx; L = Math.hypot(ox, oz) || 1; }
          const w = W.nav.nearestFree(fc.x + ox / L * (rad + 1.1), fc.z + oz / L * (rad + 1.1), 3);
          if (w) { c._path.splice(c._pi, 0, { x: w.x, z: w.z }); F.stats.detours++; f.detours = (f.detours || 0) + 1; if (now >= (f.cd.detSay || 0)) { f.cd.detSay = now + 20; c.emote('sweat', 1.4); if (!m.sc) face(c, m, 'worried', 1.8); record(m, { event: 'fire-detour', fear: Math.round(fearNow * 100) / 100, face: 'worried' }); } }
        }
      }
      if (fd < 5.5 && now >= (f.cd.shake || 0) && !m.sc && c.state !== 'sit' && !moving && canAct(c)) {   // 站在火邊：發抖
        f.cd.shake = now + R(7, 11); face(c, m, 'scared', 2.2); act(c, 'fidget', { duration: 2.2 }); c.emote('sweat', 1.6); say(c, rnd(['…好怕火', '離火遠一點…']), 1.6); record(m, { event: 'fire-shiver', face: 'scared', action: 'fidget' });
      }
      // 夜晚的路燈火光：緊張
      if (nightK() > .3 && now >= (f.cd.lamp || 0) && W.phys && W.phys.lampSpots) {
        const ls = W.phys.lampSpots(), p = pos(c); let near = null; for (const l of ls) if (l && Math.hypot(l.x - p.x, l.z - p.z) < 3) { near = l; break; }
        if (near && !m.sc) { f.cd.lamp = now + 25; face(c, m, 'worried', 2); c.emote('sweat', 1.4); say(c, '…那個光…', 1.4); record(m, { event: 'lamp-nervous', face: 'worried' }); }
      }
    }
    // 你靠近
    const bad = f.rel <= -.35 || now < f.fearYou, good = f.rel >= .4;
    if ((bad || good) && !m.sc && canAct(c) && !c.sleeping) {
      if (bad && nearYou(c, 2.6) && now >= (f.cd.retreat || 0)) {
        f.cd.retreat = now + 7; const y = youXZ(), p = pos(c);
        if (c.state === 'stand' && y) {
          const a = Math.atan2(p.x - y.x, p.z - y.z), tgt = W.nav.nearestFree(p.x + Math.sin(a) * 2, p.z + Math.cos(a) * 2, 3), path = tgt && W.nav.findPath(p, tgt);
          face(c, m, f.rel <= -.55 && m.t.sens >= .5 ? 'scared' : 'wary', 2.4); c.emote('dots', 1.4); if (path) c.walkTo(path, { speed: 2.4 }); F.stats.retreats++; record(m, { event: 'back-off', face: 'wary', rel: Math.round(f.rel * 100) / 100 });
        } else if (c.state === 'sit') { face(c, m, 'wary', 2.4); c.emote('dots', 1.4); c.swivel((c._seat ? c._seat.face : 0) + Math.PI * .5); setTimeout(() => { if (c.state === 'sit') c.swivel(null); }, 2600); F.stats.retreats++; record(m, { event: 'turn-away', face: 'wary' }); }
      } else if (good && now >= (f.cd.wave || 0) && nearYou(c, 4.5) && (c.state === 'stand' || c.state === 'sit')) {
        f.cd.wave = now + 40; const y = youXZ(); if (y && c.state === 'stand') c.faceTo(y.x, y.z);
        face(c, m, f.rel >= .6 ? 'happy' : 'smile', 2.2); act(c, 'wave', { duration: 1.4 }); c.emote(f.rel >= .6 ? 'heart' : 'note', 1.5); say(c, rnd(['嗨～', '你來啦～']), 1.5); F.stats.waves++; record(m, { event: 'wave-to-you', face: f.rel >= .6 ? 'happy' : 'smile', action: 'wave', rel: Math.round(f.rel * 100) / 100 });
      } else if (f.rel >= .62 && now >= (f.cd.come || 0) && !nearYou(c, 2.2) && nearYou(c, 9) && !(S0() && S0().agents.get(c.spec.id) && S0().agents.get(c.spec.id).phase === 'doing')) {
        f.cd.come = now + 90; const y = youXZ(); if (y) { F.stats.approaches++; record(m, { event: 'come-to-you', rel: Math.round(f.rel * 100) / 100 });
          visit(c, { object3D: { position: { x: y.x, y: 0, z: y.z } } }, { gap: 1.6, speed: 2.4, at: async (tok, alive) => { face(c, m, 'happy', 2.4); act(c, 'wave', { duration: 1.4 }, true); c.emote('heart', 1.6); say(c, '嗨～我來找你了', 1.8, true); await W.sleep(2.4); } }); }
      }
    }
  };
  const S0 = () => K.S;

  // ───────── 心情列：補上階段、怕火、躲起來等 ─────────
  const when = f => { if (!f.burnAt) return '被燒到'; const h = (Date.now() - f.burnAt) / 3600e3; return h < .17 ? '剛被燒到' : h < 18 ? '今天被燒到' : h < 48 ? '昨天被燒到' : '前幾天被燒到'; };
  F.mood = (c, m, cur) => {
    const f = of(m); if (['sleep', 'dizzy'].includes(cur.k)) return null;
    if (cur.k === 'burned') return f.stage === 'pain' ? { k: 'burned', label: '又痛又狼狽', cause: cur.cause } : null;
    if (f.mode === 'complain') return { k: 'complain', label: '想告狀', cause: '一直被欺負' };
    if (f.mode === 'hide') return { k: 'hide', label: '想躲起來', cause: '一直被欺負' };
    if (f.mode === 'vent') return { k: 'vent', label: '想找人訴苦', cause: '剛被火燒到' };
    if (W.time < f.wetUntil) return { k: 'wet', label: '濕答答的', cause: cur.cause && /救|水/.test(cur.cause) ? cur.cause : '剛被水救了' };
    if (c.jobless) return null;
    if (f.rematch && W.time < f.rematch.until && ['calm', 'low', 'sad', 'stress', 'tired'].includes(cur.k)) return { k: 'rematch', label: '不甘心', cause: '輸給' + f.rematch.nick + '，想再來一場' };
    const plain = !cur.cause || /燒|恢復|火|欺負|被你丟|被丟|撞|敲/.test(cur.cause);
    if (f.fear >= .25 && (['calm', 'tired', 'stress', 'low', 'sad'].includes(cur.k) || (f.fear >= .4 && cur.k === 'happy')) && plain) return { k: 'afraid', label: '還在怕火', cause: when(f) };
    if (f.rel <= -.45 && cur.k === 'calm' && W.time >= m.wary) return { k: 'wary', label: m.t.comp >= .55 ? '還在生氣' : '有點怕你', cause: W.time - (f.bullyAt || -999) < 900 ? '被欺負過' : '被你丟過' };
    return null;
  };
  F.snapshot = m => { const f = of(m); return { rel: Math.round(f.rel * 100) / 100, att: relTxt(m), fear: Math.round(f.fear * 100) / 100, mode: f.mode, tier: f.tier || 0, stage: f.stage, wet: W.time < f.wetUntil, rematch: f.rematch && W.time < f.rematch.until ? f.rematch.nick : null, rap: { ...f.rap }, detours: f.detours || 0, pats: f.pats || 0, blame: f.blame, hits: f.hits.length, ventDone: f.ventDone }; };
  F.scene = scene; void endScene;
  return F;
}
