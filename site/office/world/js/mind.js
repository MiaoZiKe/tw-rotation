// 角色的「心」（2026-11-14，擁有者：「他們被獎勵、懲罰等表情、情緒也要更貼近一般人，他們是獨立個體」）。
// 每位同事一個「心」：
//   ① 個性（0～1 的五個特質：ext 外向、sens 敏感、comp 好勝、opt 樂觀、pat 耐心）
//      ＝物種的預設 ＋ 職稱修正 ＋ 用代號雜湊產生的固定小隨機（同物種兩位也不一樣；存在 localStorage，重新整理保持一致）
//   ② 心情（val 愉快度 -1～1、energy 精力 0～1、stress 壓力 0～1）：事件把它推開，時間把它慢慢拉回基準
//      （敏感的人拉得慢、樂觀的人拉得快）
//   ③ 短期記憶（最近 8 件事與對誰：被你丟過、被誰稱讚、跟誰聊過…），被點選時的戒心、摸頭要不要原諒都看它
// 事件 → 反應：全部走事件匯流排 W.emit(name, id, data)／W.on(name, fn)（「物理互動」那邊也用同一個）。
//   本層聽：rewarded／promoted／awarded／item／praised（獎勵）｜rejected／demoted／bonked（懲罰）｜comforted｜
//           fired／fired_door／jobless_arrived／rehired（人事）｜knocked／burned／recovered（物理）
//   本層送：petted／fed／bonked（包住角色的 pet／feed／bonk）、knocked（拎起來用力丟出去，且物理那邊沒送時補送）
// 不羞辱原則：懲罰類只會難過、委屈、生氣跺腳，不會被嘲笑；旁人只會關心，或「小小偷笑一下」（只在無傷的碰撞），不指人、不圍觀。
// 做法：不改角色與導演的內部，只用角色的公開介面（setExpression／setAction／emote／say／lookAt／faceTo／pause／walkTo）；
//   表情用「保持」機制：心在演的期間，其他系統對表情的設定會被擋掉，演完才還給基準表情（依心情）。
import { hhmm } from './state.js';

const LS = 'aiOffice.mind.v1';
const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t;
const rnd = a => a[Math.floor(Math.random() * a.length)], R = (a, b) => a + Math.random() * (b - a);
const hash = s => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0; return h; };
const mulberry = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };

// ── ① 個性：物種預設 [外向, 敏感, 好勝, 樂觀, 耐心]
export const TRAIT_KEYS = ['ext', 'sens', 'comp', 'opt', 'pat'];
export const TRAIT_ZH = { ext: '外向', sens: '敏感', comp: '好勝', opt: '樂觀', pat: '耐心' };
const SP = {
  mochi: [.55, .50, .35, .65, .50], bunny: [.45, .70, .30, .55, .40], pudding: [.50, .65, .25, .70, .45], bean: [.60, .40, .45, .60, .50], robo: [.30, .25, .60, .50, .70],
  cloud: [.35, .70, .20, .45, .55], flame: [.75, .45, .80, .65, .25], cactus: [.25, .35, .55, .40, .75], mug: [.55, .40, .35, .60, .55], ghost: [.30, .80, .20, .40, .45],
  bird: [.80, .45, .50, .70, .30], octo: [.50, .50, .55, .55, .50], star: [.85, .40, .70, .80, .30], calc: [.25, .30, .60, .45, .75], seal: [.65, .35, .30, .75, .55],
  bulb: [.55, .55, .55, .70, .35], note: [.50, .50, .40, .55, .50], folder: [.30, .45, .45, .50, .70], pencil: [.45, .50, .60, .55, .50], stamp: [.35, .35, .65, .45, .65],
  lamp: [.50, .50, .35, .60, .55], snail: [.20, .60, .15, .50, .90], dino: [.65, .35, .70, .60, .35], donut: [.70, .55, .30, .80, .40], worm: [.40, .60, .30, .60, .50],
};
function makeTraits(c) {
  const sp = c.look && c.look.species || c.spec.species, base = (SP[sp] || [.5, .5, .45, .6, .5]).slice(), z = c.spec.zh || '', id = c.spec.id;
  if (/設計|創意|社群|行銷|業務|公關|影片|客服|品牌/.test(z)) base[0] += .12;
  if (/稽核|法務|合規|量化|資料|風控|研究|分析|後端|架構/.test(z)) { base[0] -= .1; base[4] += .1; }
  if (c.spec.lead || /主管|總監|經理|長$/.test(z)) { base[2] += .1; base[4] += .05; }
  if (c.spec.isCeo) { base[2] += .12; base[4] += .15; base[0] += .05; base[3] += .05; }
  const r = mulberry(hash(id + '|mind')), t = {};
  TRAIT_KEYS.forEach((k, i) => { t[k] = Math.round(clamp(base[i] + (r() - .5) * .44, .05, .95) * 100) / 100; });
  return t;
}
let SAVED = {}; try { SAVED = (JSON.parse(localStorage.getItem(LS) || '{}') || {}).t || {}; } catch (e) { SAVED = {}; }
let saveT = 0; const saveNow = () => { try { localStorage.setItem(LS, JSON.stringify({ v: 1, t: SAVED })); } catch (e) { /* 存不進去就算了：下次用同一個雜湊算出同樣的值 */ } };

// ── 表情分類（驗收與資訊卡用）
export const HAPPY_FACES = new Set(['happy', 'laugh', 'whee', 'smile', 'bliss', 'shy', 'fistpump', 'giggle', 'grateful', 'relieved', 'smug', 'proud', 'chew', 'eatOpen']);
export const SAD_FACES = new Set(['sad', 'pout', 'cry', 'worried', 'sulkf', 'ouch']);
export const WARY_FACES = new Set(['wary', 'sulkf', 'angry']);
const OLD_ALIAS = { shy: 'sulk', fist: 'raise', sob: 'sulk', flail: 'raise', cough: 'idle', yawn: 'stretch', rub: 'think', dizzy: 'sulk', fidget: 'idle' };   // 舊做法角色沒有的姿勢：用最像的現成動作
const CAUSE = { praise: '剛被稱讚', award: '剛得獎', promote: '剛升等', item: '剛拿到新配件', rejected: '交件被退回', demote: '等第降了，想再加油', bonk: '被敲了頭', fired: '剛離開公司', rehired: '剛被重新聘用',
  petted: '被摸了頭', fed: '剛吃了點心', knocked: '被丟出去', knockedObj: '被撞了一下', burned: '被火燒到', recovered: '剛恢復', relieved: '剛交完件', comforted: '被安慰了', sleepy: '工作很久了', saw: '看到同事出事', wary: '對你有點戒心', jobless: '待業中' };

export function createMind(W, X = {}) {
  const S = X.state || W.state, D = () => W.director, A = () => W.attn, C = id => W.chars.get(id);
  const M = { minds: new Map(), log: [], count: 0 };
  W.mind = M;

  // ───────── 事件匯流排（物理互動那邊也會用；誰先建都行，這裡不蓋掉別人的） ─────────
  const handlers = {};
  const sub = (name, fn) => (handlers[name] ||= []).push(fn);
  let lastD = null;
  const dispatch = (name, a, b) => { const nowR = performance.now(); if (lastD && lastD.n === name && lastD.a === a && lastD.b === b && nowR - lastD.t < 30) return; lastD = { n: name, a, b, t: nowR }; const id = a && typeof a === 'object' ? (a.id || a.who) : a, d = a && typeof a === 'object' ? a : (b || {}); for (const f of handlers[name] || []) { try { f(id, d, name); } catch (e) { console.error('心情事件例外', name, e); } } };
  let myEmit = null;
  function bus() {
    if (!W.emit) {
      const L = {}; myEmit = (name, id, data) => { for (const f of L[name] || []) { try { f(id, data, name); } catch (e) { console.error(e); } } dispatch(name, id, data); };
      W.emit = myEmit; W.on = (name, fn) => { (L[name] ||= []).push(fn); return () => { L[name] = (L[name] || []).filter(q => q !== fn); }; };
    } else if (W.emit !== myEmit && !W.emit.__mind) {   // 別人先建了匯流排，或後來蓋掉我的：包一層，讓我的處理函式一定收得到
      const theirs = W.emit; const w = (name, id, data) => { const r = theirs.call(W, name, id, data); dispatch(name, id, data); return r; }; w.__mind = 1; W.emit = w; myEmit = w;
    }
  }
  bus();
  const EV = ['rewarded', 'promoted', 'awarded', 'item', 'praised', 'rejected', 'demoted', 'bonked', 'comforted', 'fired', 'fired_door', 'jobless_arrived', 'rehired', 'knocked', 'burned', 'recovered'];
  M.names = EV;
  const emit = (name, id, data) => { bus(); W.emit(name, id, data); };

  // ───────── 個體 ─────────
  const people = () => [...W.chars.values()].filter(c => !c.spec.pet);
  function mindOf(c) {
    if (!c || c.spec.pet) return null; const id = c.spec.id; let m = M.minds.get(id);
    if (!m) {
      let t = SAVED[id]; if (!Array.isArray(t) || t.length !== 5) { const tt = makeTraits(c); t = TRAIT_KEYS.map(k => tt[k]); SAVED[id] = t; if (!saveT) saveT = setTimeout(() => { saveT = 0; saveNow(); }, 800); }
      const tr = Object.fromEntries(TRAIT_KEYS.map((k, i) => [k, t[i]]));
      const base = { val: clamp((tr.opt - .5) * .5 + .05, -.2, .35), energy: .8, stress: .1 + (1 - tr.pat) * .1 };
      m = { id, t: tr, base, val: base.val, energy: base.energy, stress: base.stress, bias: 0, mem: [], cause: null, flag: null, wary: 0, resent: 0, petTry: 0, petAt: -99, feedTry: 0, sc: null, holdUntil: 0, faceName: null, faceUntil: 0, baseName: 'neutral',
        nextHabit: W.time + R(6, 30), habit: null, last: null, acc: 0, inner: 0, burned: false, jobT: 0, lookDown: false, spin: null, calmAt: 0, lastFace: 'neutral' };
      M.minds.set(id, m);
    }
    return m;
  }
  const speedMul = m => clamp(1 + .16 * Math.max(0, m.val) - .24 * Math.max(0, -m.val) - .14 * Math.max(0, .45 - m.energy), .7, 1.16);
  const awake = c => !c.sleeping && c.action !== 'sleep' && c.object3D.visible && !c.away;
  const meeting = c => { const d = D(), mt = d && d.meeting; return !!(mt && mt.people.includes(c)); };
  const canAct = c => !c.busy && !c.piloted && !c.sleeping && !c.jobless && !c.hrBusy && c.state !== 'held' && !meeting(c) && c.action !== 'sleep';
  const pos = c => c.object3D.position;
  const cam = () => W.camera.position;
  const dist = (a, b) => Math.hypot(pos(a).x - pos(b).x, pos(a).z - pos(b).z);
  const record = (m, o) => { m.last = { ...o, at: W.time }; M.log.unshift({ id: m.id, ...o, at: W.time }); if (M.log.length > 80) M.log.length = 80; M.count++; };
  const remember = (m, type, who, text) => { m.mem.unshift({ t: W.time, type, who: who || '', text: text || CAUSE[type] || type }); if (m.mem.length > 8) m.mem.length = 8; };
  const recent = (m, type, sec, who) => m.mem.some(x => x.type === type && W.time - x.t < sec && (!who || x.who === who));

  // 心情被事件推開：d={val,energy,stress}（正負都行），cause=資訊卡上的原因字
  function affect(m, d, cause, dur = 150) {
    m.val = clamp(m.val + (d.val || 0), -1, 1); m.energy = clamp(m.energy + (d.energy || 0), 0, 1); m.stress = clamp(m.stress + (d.stress || 0), 0, 1);
    if (cause) m.cause = { text: cause, until: W.time + dur };
  }

  // ───────── 表情保持機制 ─────────
  function wrap(c, m) {
    if (c._mindW === m) return; c._mindW = m;
    const set0 = c._mindSet0 || (c._mindSet0 = c.setExpression.bind(c));
    c.setExpression = (name, sec) => { if (m.inner || !(m.holdUntil > W.time) || c.sleeping) { if (!m.inner) m.baseName = ''; return set0(name, sec); } };   // 保持期間，其他系統的表情先擋掉
    c._mindFace = name => { m.inner = 1; try { set0(name); } finally { m.inner = 0; } };
    const walk0 = c._mindWalk0 || (c._mindWalk0 = c.walkTo.bind(c)); c.walkTo = (path, opts = {}) => walk0(path, { ...opts, speed: (opts.speed || 1.6) * speedMul(m) });
    // 被點選時角色會「精神一振」（perk，開心的眼神）：心在演的期間不要蓋掉我的表情（舊做法的臉用同一個口子，後呼叫的會贏）
    const perk0 = c.perk && (c._mindPerk0 || (c._mindPerk0 = c.perk.bind(c))); if (perk0) c.perk = (sec) => { if (m.holdUntil > W.time) return; return perk0(sec); };
    // 摸頭、餵點心、敲頭：心情不好或剛被你欺負過時不吃這套
    const pet0 = c.pet.bind(c); c.pet = (sec) => { if (onPetAttempt(c, m, 'pet') === 'dodge') return; pet0(sec); afterPet(c, m, sec || 2.2); };
    const feed0 = c.feed.bind(c); c.feed = () => { if (onPetAttempt(c, m, 'feed') === 'dodge') return; feed0(); afterFeed(c, m); };
    const bonk0 = c.bonk.bind(c); c.bonk = () => { bonk0(); emit('bonked', c.spec.id, { by: 'you' }); };
    // 拎起來快速甩出去：沒人先送 knocked 就由這裡補送
    const grab0 = c.grab.bind(c), drag0 = c.dragTo.bind(c), rel0 = c.release.bind(c); c._dh = [];
    c.grab = () => { c._dh.length = 0; m.grabbedAt = W.time; return grab0(); };
    c.dragTo = (x, y, z) => { c._dh.push([performance.now(), x, y, z]); if (c._dh.length > 8) c._dh.shift(); return drag0(x, y, z); };
    c.release = () => {
      const h = c._dh, n = h.length; let sp = 0; if (n >= 2) { const a = h[Math.max(0, n - 4)], b = h[n - 1], dt = Math.max(0.03, (b[0] - a[0]) / 1000); sp = Math.hypot(b[1] - a[1], b[2] - a[2], b[3] - a[3]) / dt; }
      const was = c._held; const r = rel0(); if (was && sp > 3.2) { m.thrownAt = W.time; setTimeout(() => emit('knocked', c.spec.id, { by: 'you', speed: sp }), 0); } return r;
    };
  }

  function face(c, m, name, sec) {
    m.faceName = name; m.faceUntil = W.time + sec; m.holdUntil = m.faceUntil; if (c._mindFace) c._mindFace(name); else c.setExpression(name);
  }
  const HAPPY_BASE = .5, SAD_BASE = -.28;
  function baseFace(m, c) {
    if (c.sleeping || c.action === 'sleep') return null;
    if (m.burned) return 'blank';
    if (m.val < -.55) return 'pout'; if (m.val < SAD_BASE) return 'worried'; if (m.stress > .8 && m.energy < .4) return 'sleepy'; if (m.val > HAPPY_BASE) return 'smile'; return 'neutral';
  }
  function applyBase(c, m, force) {
    const n = baseFace(m, c); if (n == null) return;
    if (force || c.expression === 'neutral' || (m.baseName && c.expression === m.baseName)) { if (n !== c.expression || force) { c._mindFace && c._mindFace(n); } m.baseName = n; }
    m.lastFace = n;
  }
  const say = (c, text, sec = 1.8, force) => { if (force || canAct(c) || c.jobless || c.hrBusy) c.say(text, sec); };
  const act = (c, name, opt = {}, force) => { if (!(force || canAct(c))) return false; c.setAction(c.newModel ? name : (OLD_ALIAS[name] || name), opt); return true; };

  // ───────── 場景（一段演出：依時間排好的步驟，高優先的蓋掉低優先的） ─────────
  function scene(c, m, prio, name, build) {
    if (m.sc && m.sc.prio > prio && !m.sc.done) return null; endScene(c, m);
    const sc = { prio, name, t0: W.time, steps: [], i: 0, undo: [], len: 0, poll: null, done: false, c };
    sc.at = (t, fn) => { let k = sc.steps.length; while (k > sc.i && sc.steps[k - 1].t > t) k--; sc.steps.splice(k, 0, { t, fn }); sc.len = Math.max(sc.len, t); return sc; };   // 依時間插入（演出途中也能再排後面的步驟）
    sc.on_end = fn => { sc.undo.push(fn); return sc; };
    m.sc = sc; build(sc); return sc;
  }
  function endScene(c, m) {
    const sc = m.sc; if (!sc) return; m.sc = null; sc.done = true;
    for (const f of sc.undo) { try { f(); } catch (e) { console.error(e); } }
  }
  const pauseFor = (sc, c) => { c.pause(true); sc.on_end(() => c.pause(false)); };
  const lookAtPt = (sc, c, v, sec) => { c.lookAt(v); sc.at(sec, () => { if (!(A() && A().current() === c)) c.lookAt(null); }); sc.on_end(() => { if (!(A() && A().current() === c)) c.lookAt(null); }); };
  const downPt = c => ({ x: pos(c).x + Math.sin(c.heading || 0) * 1.1, y: .2, z: pos(c).z + Math.cos(c.heading || 0) * 1.1 });
  const holdCap = (c, m, sc) => sc.on_end(() => { if (W.time >= m.faceUntil) { m.faceName = null; m.holdUntil = 0; applyBase(c, m, true); } });
  const nearest = (c, r = 6) => { let best = null, bd = r; for (const o of people()) { if (o === c || !awake(o) || o.jobless) continue; const d = dist(c, o); if (d < bd) { bd = d; best = o; } } return best; };

  // ───────── 獎勵 ─────────
  function reward(id, d = {}, kindIn) {
    const c = C(id), m = mindOf(c); if (!c || !m || c.jobless && kindIn !== 'rehire') return;
    const kind = kindIn || d.kind || 'praise', I = { promote: 1, award: 1, item: .8, praise: .6 }[kind] || .6, t = m.t;
    affect(m, { val: .34 * I * (1 + .3 * t.opt), energy: .06, stress: -.15 * I }, CAUSE[kind], 160);
    remember(m, kind, d.by === 'ceo' ? 'CEO' : '', CAUSE[kind]); m.flag = null; m.calmAt = 0;
    const style = t.comp >= .65 && t.ext < .7 ? 'fist' : t.ext >= .62 ? 'burst' : t.ext <= .4 ? 'shy' : 'warm';
    const tgt = nearest(c, 6);
    scene(c, m, 6, 'reward-' + style, sc => {
      if (style === 'burst') {                       // 外向：跳起來、轉圈、跟旁邊的人炫耀
        sc.at(0, () => { face(c, m, 'laugh', 1.9); c.emote('star', 1.8); say(c, rnd(['太棒了！！', '耶～！', '我做到了！']), 1.8); const ok = act(c, 'cheer', { duration: 1.8 }); if (ok && c.state === 'stand' && c.newModel && c.inner && 'extFall' in c.inner) c.inner.extFall = true; if (c.state === 'stand') m.spin = { t0: W.time, h0: c.heading || 0, dur: 1.1 }; });
        sc.at(2.0, () => { face(c, m, 'whee', 1.6); if (tgt && awake(tgt)) { c.faceTo(pos(tgt).x, pos(tgt).z); say(c, rnd(['你看你看！', '快看我的！']), 1.8); act(c, 'point', { duration: 1.5 }); } });
        sc.at(3.8, () => face(c, m, 'happy', 2.2)).at(6, () => { });
      } else if (style === 'shy') {                  // 內向：害羞微笑、低頭、臉紅
        sc.at(0, () => { face(c, m, 'shy', 2.6); act(c, 'shy', { duration: 2.4 }); c.lookAt(downPt(c)); say(c, rnd(['（小聲）謝謝…', '欸、欸嘿…']), 1.9); });
        sc.at(2.6, () => { face(c, m, 'smile', 2.4); if (!(A() && A().current() === c)) c.lookAt(null); c.emote('heart', 1.2); }).at(5, () => { });
      } else if (style === 'fist') {                 // 好勝：握拳
        sc.at(0, () => { face(c, m, 'fistpump', 1.9); act(c, 'fist', { duration: 1.5 }); say(c, rnd(['好！繼續拿下！', '下一個目標！']), 1.7); c.emote('star', 1.4); });
        sc.at(1.9, () => face(c, m, 'smug', 1.8)).at(3.8, () => { });
      } else {                                       // 溫和：點頭微笑
        sc.at(0, () => { face(c, m, 'happy', 2.2); act(c, 'nod', { duration: 1.2 }); c.emote('note', 1.6); say(c, rnd(['謝謝～', '收到，我會繼續努力']), 1.7); });
        sc.at(2.2, () => face(c, m, 'smile', 2.2)).at(4.4, () => { });
      }
      holdCap(c, m, sc);
    });
    record(m, { event: 'reward', kind, style, action: { burst: 'cheer+jump+spin', shy: 'shy', fist: 'fist', warm: 'nod' }[style], face: { burst: 'laugh', shy: 'shy', fist: 'fistpump', warm: 'happy' }[style] });
    witness(id, 'rewarded', d);
  }

  // ───────── 懲罰 ─────────
  function punish(id, d = {}, kindIn) {
    const c = C(id), m = mindOf(c); if (!c || !m || c.jobless) return;
    const kind = kindIn || d.kind || 'rejected', t = m.t, I = { rejected: .38, bonk: .3, demote: .42 }[kind] || .35;
    affect(m, { val: -I * (.7 + .6 * t.sens) * (1.1 - .4 * t.opt), stress: .1, energy: -.04 }, CAUSE[kind], 200);
    remember(m, kind, kind === 'bonk' ? '你' : '', CAUSE[kind]);
    const emo = (sym, sec) => { if (kind !== 'rejected') c.emote(sym, sec); };   // 交件失敗時派工那邊已經放了小烏雲，不蓋掉
    const style = t.comp >= .62 && t.sens < .6 ? 'angry' : t.sens >= .55 ? 'sad' : 'stoic', body = canAct(c);
    const dur = 2.6 + 3.6 * t.sens;
    scene(c, m, 6, 'punish-' + style, sc => {
      if (style === 'angry') {                       // 好勝：生氣、跺腳
        sc.at(0, () => { face(c, m, 'angry', 2.4); emo('anger', 2.2); say(c, rnd(['可惡…', '下次不會了！', '氣死我了！']), 1.8); act(c, 'slam', { duration: 1.8 }); });
        sc.at(2.6, () => face(c, m, 'sulkf', 2)).at(4.6, () => { });
      } else if (style === 'sad') {                  // 敏感：難過、輕微流淚、垂頭
        sc.at(0, () => { face(c, m, 'sad', dur); emo('cloud', Math.min(2.6, dur)); act(c, 'sob', { duration: dur }); say(c, rnd(['…', '嗚…', '我知道了…']), 1.6); if (body) c.lookAt(downPt(c)); });
        sc.on_end(() => { if (!(A() && A().current() === c)) c.lookAt(null); });
        if (t.opt >= .6) sc.at(dur, () => { face(c, m, 'effort', 1.4); say(c, '我再試一次！', 1.6); m.val = Math.max(m.val, -.1); }).at(dur + 1.5, () => { }); else sc.at(dur, () => face(c, m, 'worried', 2)).at(dur + 2, () => { });
      } else {                                       // 悶著的人：嘟嘴
        sc.at(0, () => { face(c, m, 'pout', 2.4); act(c, 'sulk', { duration: 2.2 }); emo('dots', 1.8); say(c, '好吧…', 1.5); });
        sc.at(2.4, () => { }).at(2.6, () => { });
      }
      holdCap(c, m, sc);
    });
    record(m, { event: 'punish', kind, style, action: { angry: 'slam', sad: 'sob', stoic: 'sulk' }[style], face: { angry: 'angry', sad: 'sad', stoic: 'pout' }[style] });
    witness(id, kind === 'rejected' ? 'rejected' : 'punish', d);
  }

  // ───────── 人事：被開除、重新聘用 ─────────
  function fired(id, d) {
    const c = C(id), m = mindOf(c); if (!c || !m) return;
    affect(m, { val: -.55 * (.7 + .6 * m.t.sens), stress: .15, energy: -.08 }, CAUSE.fired, 400); remember(m, 'fired', '', CAUSE.fired); m.jobT = W.time; m.flag = { name: 'jobless', until: 1e12 };
    scene(c, m, 7, 'fired', sc => {
      sc.at(0, () => face(c, m, m.t.sens >= .5 ? 'sad' : 'pout', 9)).at(9, () => { });
      holdCap(c, m, sc);
    });
    record(m, { event: 'fired', style: m.t.sens >= .5 ? 'sad' : 'pout', face: m.t.sens >= .5 ? 'sad' : 'pout', action: 'walk-out' });
    witness(id, 'fired', d);
  }
  function firedDoor(id) {
    const c = C(id), m = mindOf(c); if (!c || !m) return;
    scene(c, m, 8, 'fired-door', sc => {                    // 回頭看一眼
      pauseFor(sc, c); sc.at(0, () => { face(c, m, 'sad', 2.6); c.emote('dots', 2); const p = pos(c); lookAtPt(sc, c, { x: p.x, y: 1.1, z: p.z - 5 }, 2.4); });
      sc.at(2.5, () => { }); holdCap(c, m, sc);
    });
    record(m, { event: 'fired_door', face: 'sad', action: 'look-back' });
  }
  function jobless(id) { const c = C(id), m = mindOf(c); if (!c || !m) return; m.jobT = W.time; m.flag = { name: 'jobless', until: 1e12 }; }
  function rehired(id) {
    const c = C(id), m = mindOf(c); if (!c || !m) return; m.flag = null; m.jobT = 0; m.rehiring = true;   // 回來的路上 c.jobless 還沒放掉，別又當成待業
    affect(m, { val: .6, stress: -.2, energy: .1 }, CAUSE.rehired, 240); remember(m, 'rehired', '', CAUSE.rehired);
    scene(c, m, 7, 'rehired', sc => {
      sc.at(0, () => { face(c, m, 'surprised', 1); c.emote('exclaim', 1); }).at(1, () => { face(c, m, 'grateful', 3.4); c.emote('heart', 2.6); if (m.t.ext >= .55) m.spin = { t0: W.time, h0: c.heading || 0, dur: 1.1 }; });
      sc.at(4.4, () => face(c, m, m.t.ext <= .4 ? 'shy' : 'happy', 2.4)).at(7, () => { }); holdCap(c, m, sc);
    });
    record(m, { event: 'rehired', style: m.t.ext >= .55 ? 'joy' : 'tearful', face: 'grateful', action: 'surprise-then-thanks' });
    witness(id, 'rewarded', {});
  }

  // ───────── 物理：被丟出去、被燒到、恢復 ─────────
  function knocked(id, d = {}) {
    const c = C(id), m = mindOf(c); if (!c || !m) return; if (m.sc && m.sc.name === 'knocked' && W.time - m.sc.t0 < 1.2) return;   // 兩邊都送也只演一次
    const by = d.by || (m.thrownAt && W.time - m.thrownAt < 2 ? 'you' : m.grabbedAt && W.time - m.grabbedAt < 5 ? 'you' : 'obj'), you = by === 'you', t = m.t;
    affect(m, { val: -(you ? .36 : .2) * (.7 + .6 * t.sens), stress: .12 }, you ? CAUSE.knocked : CAUSE.knockedObj, 220); remember(m, 'knocked', you ? '你' : '', you ? CAUSE.knocked : CAUSE.knockedObj);
    const angry = t.comp >= .55 && t.sens < .75, dz = 2.2 + 1.4 * t.sens, light = !you && d.speed != null && d.speed < 2.5;   // 輕輕撞到：不暈
    scene(c, m, 8, 'knocked', sc => {
      let ph = 0, ts = 0, glare = null;
      face(c, m, 'scared', 6); c.emote('exclaim', 1); say(c, '哇啊！', 1, true); act(c, 'flail', { duration: 1.4 }, true);
      sc.poll = () => {
        const age = W.time - sc.t0, grounded = c.state !== 'held' && !(c.inner && c.inner.extFall) && age > .5;
        if (ph === 0 && light && age > .6) { ph = 1; ts = W.time - dz; }
        else if (ph === 0 && (grounded || age > 5)) {                // 落地：暈眩，頭上轉圈
          ph = 1; ts = W.time; face(c, m, 'dizzy', dz + .2); c.emote('swirl', dz); act(c, 'dizzy', { duration: dz }, true); c.pause(true); sc.on_end(() => c.pause(false)); m.flag = { name: 'dizzy', until: W.time + dz };
        } else if (ph === 1 && W.time - ts >= dz) {              // 看向你（記住是你）
          ph = 2; ts = W.time; m.flag = you ? { name: 'upset', until: W.time + 3.4 } : null;
          if (you) {
            const p = pos(c), q = cam(); c.faceTo(q.x, q.z); c.lookAt(q); sc.on_end(() => { if (!(A() && A().current() === c)) c.lookAt(null); });
            if (angry) { face(c, m, 'angry', 3); c.emote('anger', 2.4); say(c, rnd(['喂！很危險耶！', '不要這樣啦！']), 2, true); } else if (t.sens >= .6) { face(c, m, 'sad', 3.2); c.emote('cloud', 2.4); say(c, rnd(['嗚…', '好可怕…']), 2, true); } else { face(c, m, 'pout', 3); c.emote('dots', 2); say(c, '…哼', 1.6, true); }
            void p;
          } else { face(c, m, 'confused', 2.2); c.emote('question', 2); }
        } else if (ph === 2 && W.time - ts >= (you ? 3.2 : 2.2)) { if (you) m.wary = W.time + 150 * (1.25 - .6 * t.opt); return true; }
        return false;
      };
      holdCap(c, m, sc);
    });
    record(m, { event: 'knocked', by, style: angry ? 'angry' : t.sens >= .6 ? 'sad' : 'pout', face: 'scared>dizzy>' + (you ? (angry ? 'angry' : t.sens >= .6 ? 'sad' : 'pout') : 'confused'), action: 'flail>dizzy' });
    witness(id, 'knocked', { by });
  }
  function burned(id, d = {}) {
    const c = C(id), m = mindOf(c); if (!c || !m) return; m.burned = true; m.burnedAt = W.time;
    affect(m, { val: -.3 * (.7 + .6 * m.t.sens), stress: .25 }, CAUSE.burned, 300); remember(m, 'burned', '', CAUSE.burned);
    scene(c, m, 9, 'burned', sc => {
      let ph = 0, ts = W.time, nextCough = 0, coughEnd = 0;
      face(c, m, 'scared', 60); c.emote('exclaim', 1.2); say(c, rnd(['燙燙燙！', '哇！好燙！']), 1.4, true); act(c, 'flail', { duration: 1.6 }, true);
      if (c.state === 'stand' && c.newModel && c.inner && 'extFall' in c.inner) c.inner.extFall = true;   // 跳腳（舊做法的角色不跳，只亂揮手）
      sc.poll = () => {
        const age = W.time - ts;
        if (ph === 0 && age > 1.5) {                          // 跑開
          ph = 1; ts = W.time;
          if (c.state === 'stand' || c.state === 'walk') { const p = pos(c), a = R(0, 6.283), f = W.nav.nearestFree(p.x + Math.cos(a) * 3.4, p.z + Math.sin(a) * 3.4, 6); const path = f && W.nav.findPath(p, f); if (path) c.walkTo(path, { speed: 3.8 }); }
        } else if (ph === 1 && age > 1.8) { ph = 2; ts = W.time; face(c, m, 'blank', 60); nextCough = 0.6; }   // 焦黑呆滯
        else if (ph === 2) {
          if (coughEnd && age >= coughEnd) { coughEnd = 0; face(c, m, 'blank', 60); }
          if (age >= nextCough && c.state !== 'walk') { nextCough = age + 3.2; coughEnd = age + 1.2; face(c, m, 'cough', 60); c.emote('smoke', 1.3); act(c, 'cough', { duration: 1.4 }, true); }
          if (c.inner && c.inner.ch && c.inner.ch.face && Math.random() < .02) c.inner.ch.face.blinkNow && c.inner.ch.face.blinkNow();    // 眨眨眼
          if (!m.burned || age > 40) { m.burned = false; return true; }
        }
        return false;
      };
      holdCap(c, m, sc);
    });
    record(m, { event: 'burned', face: 'scared>blank>cough', action: 'flail>run>cough' });
    witness(id, 'burned', d);
  }
  function recovered(id, d = {}) {
    const c = C(id), m = mindOf(c); if (!c || !m) return; m.burned = false;
    affect(m, { val: .22, stress: -.12 }, CAUSE.recovered, 140); remember(m, 'recovered', '', CAUSE.recovered);
    scene(c, m, 9, 'recovered', sc => {
      sc.at(0, () => { face(c, m, 'relieved', 2.8); say(c, rnd(['呼…', '好險…']), 1.8, true); c.emote('note', 1.6); }).at(2.8, () => face(c, m, 'smile', 2)).at(5, () => { }); holdCap(c, m, sc);
    });
    record(m, { event: 'recovered', face: 'relieved', action: 'sigh' });
    witness(id, 'recovered', d);
  }

  // ───────── 旁觀者：轉頭看、驚訝、關心地走過去，或小小偷笑一下（不羞辱） ─────────
  function witness(srcId, kind, d = {}) {
    const A0 = C(srcId); if (!A0) return; const list = [];
    for (const B of people()) { if (B === A0 || !awake(B) || (B.jobless && kind !== 'rewarded') || B.piloted) continue; const dd = dist(A0, B); if (dd <= 7.5) list.push([dd, B]); }
    list.sort((a, b) => a[0] - b[0]); let careGiven = false;
    list.slice(0, 4).forEach(([dd, B], i) => {
      const mb = mindOf(B); if (!mb) return; const t = mb.t, rel = clamp(.18 + (B.spec.dept && B.spec.dept === A0.spec.dept ? .32 : 0) + (hash(B.spec.id + A0.spec.id) % 100) / 330, 0, 1);
      const delay = .3 + i * .3 + Math.random() * .3, bad = kind !== 'rewarded';
      scene(B, mb, 2, 'witness-' + kind, sc => {
        sc.at(delay, () => {
          const a = pos(A0), glance = { x: a.x, y: 1, z: a.z }; B.lookAt(glance); B.faceTo(a.x, a.z); sc.on_end(() => { if (!(A() && A().current() === B)) B.lookAt(null); if (B.state === 'sit') B.swivel(null); });
          remember(mb, 'saw', A0.spec.nick, '看到' + A0.spec.nick + (kind === 'rewarded' ? '被獎勵' : kind === 'fired' ? '離開公司' : '出狀況'));
          if (bad) affect(mb, { val: -.07 * t.sens * (1 + rel) }, CAUSE.saw, 90); else affect(mb, { val: .09 * (.5 + t.ext * .5) }, '看到同事被獎勵', 90);
          face(B, mb, 'surprised', .8);
        });
        sc.at(delay + .85, () => {
          if (kind === 'rewarded') {
            if (t.ext >= .5 || rel >= .45) { face(B, mb, 'happy', 2.2); act(B, 'clap', { duration: 1.6 }); if (t.ext >= .6 && Math.random() < .6) say(B, rnd(['恭喜！', '太好了！']), 1.4); }
            else if (t.comp >= .7) { face(B, mb, 'fistpump', 1.6); act(B, 'fist', { duration: 1.4 }); } else { face(B, mb, 'smile', 2); act(B, 'nod', { duration: 1 }); }
          } else if (kind === 'fired') { face(B, mb, t.sens >= .4 ? 'worried' : 'blank', 2.4); B.emote('dots', 1.8); if (t.ext >= .65 && rel >= .45 && t.sens >= .4) say(B, '保重…', 1.6); }
          else if (kind === 'rejected' || kind === 'punish') { face(B, mb, 'worried', 2); if (rel >= .45 && t.ext >= .5) say(B, '加油，沒事的', 1.6); }
          else {                                                  // 被丟、被燒
            const care = t.sens * .6 + rel * .5 >= .45;
            if (kind === 'knocked' && !care && t.ext >= .6 && t.sens < .5 && d.by !== 'you') { face(B, mb, 'giggle', 1.3); B.emote('dots', 1.2); }   // 只有無傷的碰撞才偷笑一下，笑完就關心
            else { face(B, mb, 'worried', 2.4); B.emote(kind === 'burned' ? 'exclaim' : 'question', 1.6); if (care || t.ext >= .6) say(B, kind === 'burned' ? '好燙！你還好嗎？' : '沒事吧？', 1.8); }
            if (care && !careGiven && canAct(B) && B.state !== 'held' && dd > 1.4 && !B.jobless) { careGiven = true; careWalk(B, A0); }
          }
        });
        sc.at(delay + 3.2, () => { }); holdCap(B, mb, sc);
      });
      record(mb, { event: 'witness', kind, of: A0.spec.nick, rel: Math.round(rel * 100) / 100 });
    });
  }
  async function careWalk(B, A0) {
    const D0 = D(); if (!D0) return; const tok = B.script = (B.script || 0) + 1; B.busy = true; record(mindOf(B), { event: 'care-walk', to: A0.spec.nick });
    try {
      const a = pos(A0), b = pos(B), L = Math.hypot(b.x - a.x, b.z - a.z) || 1, f = W.nav.nearestFree(a.x + (b.x - a.x) / L * 1.1, a.z + (b.z - a.z) / L * 1.1, 4); if (!f) return;
      const ok = await D0.goTo(B, { x: f.x, z: f.z, face: 0 }, { speed: 2.6 }); if (B.script !== tok || !ok) return;
      B.faceTo(a.x, a.z); B.setAction('listen'); await W.sleep(2); if (B.script !== tok) return;
      B.setAction('idle'); await D0.goHome(B, { speed: 2.2 });
    } finally { if (B.script === tok) B.busy = false; }
  }

  // ───────── 摸頭、餵點心：心情很差或剛被你欺負過時，一開始會閃躲或嘟嘴，多摸幾次才原諒 ─────────
  function resenting(m) { return W.time < m.wary || m.val < -.3 || recent(m, 'knocked', 100 * (1.3 - .6 * m.t.opt), '你') || recent(m, 'bonk', 100 * (1.3 - .6 * m.t.opt), '你'); }
  function onPetAttempt(c, m, kind) {
    if (c.sleeping || c.jobless && false) return null;
    if (W.time - m.petAt > 25) { m.petTry = 0; m.feedTry = 0; } m.petAt = W.time;
    if (!resenting(m)) { m.petTry = m.feedTry = 0; return null; }
    const need = kind === 'feed' ? 2 : 2 + (m.t.opt < .5 ? 1 : 0) + (m.t.comp > .6 ? 1 : 0), key = kind === 'feed' ? 'feedTry' : 'petTry'; m[key]++;
    if (m[key] >= need) { m[key] = 0; m.wary = 0; m.val = Math.max(m.val, -.05) + .15; m.cause = { text: '原諒你了', until: W.time + 120 }; face(c, m, 'shy', 1.4); record(m, { event: 'forgive', kind, face: 'shy', action: 'accept' }); return null; }
    // 閃躲
    const q = cam(), ty = Math.atan2(q.x - pos(c).x, q.z - pos(c).z);
    scene(c, m, 5, 'dodge', sc => {
      sc.at(0, () => { face(c, m, m.t.comp >= .6 ? 'sulkf' : 'pout', 2.2); c.emote(m.t.comp >= .6 ? 'anger' : 'dots', 1.6); if (c.state === 'stand') { c.heading = ty + Math.PI * .8; } else if (c.state === 'sit') c.swivel((c._seat ? c._seat.face : 0) + Math.PI * .5); say(c, rnd(['…', '哼，不要。', '不要啦…']), 1.4, true); });
      sc.at(2.2, () => { if (c.state === 'sit') c.swivel(null); }); sc.on_end(() => { if (c.state === 'sit') c.swivel(null); }); holdCap(c, m, sc);
    });
    record(m, { event: 'dodge', kind, face: m.t.comp >= .6 ? 'sulkf' : 'pout', action: 'turn-away', tries: m[key], need });
    return 'dodge';
  }
  function afterPet(c, m, sec) {
    affect(m, { val: .1 * (1 + m.t.ext * .3) }, CAUSE.petted, 90); remember(m, 'petted', '你', CAUSE.petted);
    scene(c, m, 4, 'petted', sc => {
      if (m.t.ext >= .65) sc.at(sec + .3, () => { face(c, m, 'laugh', 1.2); c.emote('note', 1.2); }).at(sec + 1.6, () => { });
      else if (m.t.ext <= .4) sc.at(sec + .3, () => { face(c, m, 'shy', 1.8); }).at(sec + 2.2, () => { });
      else sc.at(sec + .3, () => { face(c, m, 'smile', 1.6); }).at(sec + 2, () => { });
      holdCap(c, m, sc);
    });
    record(m, { event: 'petted', face: m.t.ext >= .65 ? 'laugh' : m.t.ext <= .4 ? 'shy' : 'smile' });
  }
  function afterFeed(c, m) { affect(m, { val: .16, energy: .08, stress: -.06 }, CAUSE.fed, 120); remember(m, 'fed', '你', CAUSE.fed); record(m, { event: 'fed', face: 'eatOpen>happy' }); }

  // ───────── 被點選：剛被你欺負過就有戒心 ─────────
  let lastSel = null;
  function onSelect(c) {
    const m = mindOf(c); if (!m || c.sleeping) return;
    if (W.time < m.wary) {
      scene(c, m, 5, 'wary', sc => { sc.at(0, () => { face(c, m, 'wary', 2.8); c.emote('dots', 2); if (m.t.sens >= .55) say(c, '…', 1.2, true); }).at(2.8, () => { }); holdCap(c, m, sc); });
      record(m, { event: 'select-wary', face: 'wary', action: 'guard' });
    }
  }

  // ───────── 額度：用完全員要睡了（打哈欠），恢復（伸懶腰、鬆一口氣） ─────────
  function onQuota(wasExhausted) {
    const ex = S.q.exhausted;
    if (ex && !wasExhausted) people().filter(c => awake(c) && !c.jobless && !c.piloted).forEach((c, i) => {
      const m = mindOf(c); scene(c, m, 3, 'yawn-all', sc => { sc.at(.15 + i * .12 + Math.random() * .8, () => { face(c, m, 'yawn', 1.7); if (canAct(c) && c.state === 'sit' && !meeting(c)) act(c, 'rub', { duration: 1.4 }); }); sc.at(2.6, () => { }); holdCap(c, m, sc); }); affect(m, { energy: -.2 }, CAUSE.sleepy, 120);
    });
    if (!ex && wasExhausted) people().filter(c => !c.jobless && !c.away && !c.piloted).forEach((c, i) => {
      const m = mindOf(c); scene(c, m, 3, 'wake-all', sc => { sc.at(.4 + i * .2 + Math.random() * .5, () => { face(c, m, 'yawn', 1.4); }); sc.at(1.9 + i * .2, () => face(c, m, 'smile', 2.2)); sc.at(4.6 + i * .2, () => { }); holdCap(c, m, sc); }); affect(m, { energy: .3, val: .08 }, '睡飽了', 100);
    });
  }

  // ───────── 閒置的小習慣（依個性挑，不是每個人同一套） ─────────
  const HAB = {
    chat: m => .15 + 1.5 * m.t.ext, phone: m => .3 + m.t.ext, stare: m => .2 + (1 - m.t.ext) * .9 + m.t.sens * .3, stretch: m => .2 + m.stress * 1.6 + (1 - m.energy) * .8,
    yawn: m => (1 - m.energy) * 2 + m.stress * .6, rub: m => m.stress * 1.2 + (1 - m.energy) * .8, sip: () => .5, doodle: m => .2 + (1 - m.t.ext) * .5 + (m.t.comp < .4 ? .3 : 0),
    fidget: m => m.t.sens * .9 + m.stress * .8, glance: m => .3 + m.t.ext * .4,
  };
  const HAB_ZH = { chat: '跟鄰座聊天', phone: '滑手機', stare: '發呆', stretch: '伸懶腰', yawn: '打哈欠', rub: '揉眼睛', sip: '喝水', doodle: '塗鴉', fidget: '坐立不安', glance: '東張西望' };
  M.HAB_ZH = HAB_ZH;
  const LINES = ['今天好忙', '午餐吃什麼？', '這個你看過嗎？', '等等去倒咖啡？', '好想睡…', '剛剛那個推上去了嗎', '你這週還順利嗎'];
  function habitOk(c, m) { return c.state === 'sit' && c.atDesk && canAct(c) && !c.sleeping && !m.sc && W.time >= m.holdUntil && !(D() && D().hold) && !(A() && A().current() === c) && !(W.pilot && W.pilot.sel === c); }
  function neighbor(c) { let best = null, bd = 4.2; for (const o of people()) { if (o === c || o.state !== 'sit' || !o.atDesk || !canAct(o) || o.sleeping) continue; const d = dist(c, o); if (d < bd) { bd = d; best = o; } } return best; }
  function doHabit(c, m, forced) {
    const w = Object.entries(HAB).map(([k, f]) => [k, Math.max(0.02, f(m))]); let sum = 0; w.forEach(x => { sum += x[1]; }); let r = Math.random() * sum, name = 'glance'; for (const [k, v] of w) { r -= v; if (r <= 0) { name = k; break; } }
    const nb = name === 'chat' ? neighbor(c) : null; if (name === 'chat' && !nb) name = 'phone';
    const dur = { chat: 5.4, phone: 5, stare: 5, stretch: 2.8, yawn: 2.8, rub: 2.1, sip: 4.5, doodle: 5, fidget: 3.2, glance: 1.6 }[name];
    m.habit = { name, zh: HAB_ZH[name], until: W.time + dur }; c.workAt = Math.max(c.workAt || 0, W.time + dur + .6);
    scene(c, m, 1, 'habit-' + name, sc => {
      if (nb) sc.at(2.4, () => { act(nb, 'talk', { duration: 2 }, true); say(nb, rnd(LINES), 2, true); face(nb, mindOf(nb), 'happy', 2.4); });
      sc.at(0, () => {
        switch (name) {
          case 'chat': c.faceTo(pos(nb).x, pos(nb).z); nb.faceTo(pos(c).x, pos(c).z); nb.workAt = Math.max(nb.workAt || 0, W.time + dur + .6); act(c, 'talk', { duration: 2.2 }); say(c, rnd(LINES), 2.2); face(c, m, 'smile', 3); remember(m, 'chat', nb.spec.nick, '跟' + nb.spec.nick + '聊了幾句'); remember(mindOf(nb), 'chat', c.spec.nick, '跟' + c.spec.nick + '聊了幾句');
            sc.on_end(() => { c.swivel(null); nb.swivel(null); }); break;
          case 'phone': act(c, 'phone', { duration: dur }); break;
          case 'stare': act(c, 'think', { duration: dur }); c.emote('dots', 2.2); face(c, m, 'blank', 2.6); { const p = pos(c); lookAtPt(sc, c, { x: p.x + R(-2, 2), y: 1.6, z: p.z + R(-2, 2) }, dur - .4); } break;
          case 'stretch': act(c, 'stretch', { duration: dur }); face(c, m, 'relieved', 2.4); break;
          case 'yawn': act(c, 'yawn', { duration: dur }); face(c, m, 'yawn', 2.4); break;
          case 'rub': act(c, 'rub', { duration: dur }); face(c, m, 'sleepy', 2.2); break;
          case 'sip': act(c, 'drink', { duration: dur }); break;
          case 'doodle': act(c, 'note', { duration: dur }); face(c, m, 'smile', 3); break;
          case 'fidget': act(c, 'fidget', { duration: dur }); face(c, m, 'worried', 2.6); if (m.stress > .5) c.emote('sweat', 1.6); break;
          case 'glance': { const p = pos(c); lookAtPt(sc, c, { x: p.x + R(-3, 3), y: 1.2, z: p.z + R(-3, 3) }, 1.4); break; }
        }
      }); sc.at(dur, () => { }); holdCap(c, m, sc);
    });
    m.nextHabit = W.time + (22 + 60 * Math.random()) * (1.35 - m.t.ext * .6);
    record(m, { event: 'habit', habit: name, forced: !!forced });
    return name;
  }
  M.forceHabit = id => { const c = C(id), m = mindOf(c); if (!c || !m) return null; if (m.sc) endScene(c, m); return doHabit(c, m, true); };
  // 導演挑桌上工作時，依個性調整權重（外向多講電話、內向多讀文件、壓力大多伸懶腰、沒精神多喝咖啡打瞌睡）
  M.bias = (c, w) => {
    const m = mindOf(c); if (!m) return w; const t = m.t;
    if ('phone' in w) w.phone *= .4 + 1.6 * t.ext; if ('tablet' in w) w.tablet *= .6 + .8 * t.ext; if ('doc' in w) w.doc *= 1.5 - t.ext; if ('think' in w) w.think *= .7 + .8 * t.sens; if ('note' in w) w.note *= 1.4 - t.ext * .6;
    if ('stretch' in w) w.stretch *= 1 + m.stress * 3; if ('doze' in w) w.doze *= 1 + (1 - m.energy) * 3; if ('cup' in w) w.cup *= 1 + (1 - m.energy) * 2.2; if ('magnify' in w) w.magnify *= .5 + t.comp;
    return w;
  };

  // ───────── 資訊卡的心情列 ─────────
  const ICONS = { excited: '😆', happy: '😊', calm: '😌', tired: '😪', stress: '😣', low: '😔', sad: '😢', angry: '😠', wary: '😒', shy: '😳', dizzy: '😵', burned: '😵', sleep: '😴', upset: '😤', jobless: '😌' };
  M.moodLine = c => {
    const m = mindOf(c); if (!m) return null; let k, label, cause = '';
    const cz = m.cause && W.time < m.cause.until ? m.cause.text : '';
    if (c.sleeping || c.action === 'sleep') { k = 'sleep'; label = '睡覺中'; cause = c.jobless ? '待業中，在毯子上休息' : (S && S.q.exhausted ? '電力用完了' : '正在休息'); }
    else if (m.burned) { k = 'burned'; label = '驚魂未定'; cause = CAUSE.burned; }
    else if (m.flag && m.flag.name === 'dizzy' && W.time < m.flag.until) { k = 'dizzy'; label = '頭暈'; cause = cz || CAUSE.knocked; }
    else if (m.flag && m.flag.name === 'upset' && W.time < m.flag.until) { k = 'upset'; label = '有點生氣'; cause = cz || CAUSE.knocked; }
    else if (c.jobless) { const calm = W.time - m.jobT > 90 || m.val > -.2; k = calm ? 'jobless' : 'low'; label = calm ? '慢慢平靜' : '失落'; cause = calm ? '待業中' : cz || CAUSE.fired; }
    else if (W.time < m.wary && m.faceName === 'wary') { k = 'wary'; label = '戒備'; cause = CAUSE.wary; }
    else if (m.val >= .6) { k = 'excited'; label = '興奮'; cause = cz; }
    else if (m.val >= .3) { k = 'happy'; label = '開心'; cause = cz || (m.bias > .05 ? '上週表現不錯' : ''); }
    else if (m.val > -.15) { if (m.stress > .7) { k = 'stress'; label = '壓力大'; cause = '工作很久了'; } else if (m.energy < .35) { k = 'tired'; label = '有點睏'; cause = cz; } else { k = 'calm'; label = '平靜'; cause = cz; } }
    else if (m.val > -.5) { k = 'low'; label = '低落'; cause = cz; }
    else { k = 'sad'; label = '難過'; cause = cz; }
    if (k === 'calm' && m.faceName === 'shy') { k = 'shy'; label = '害羞'; }
    return { key: k, icon: ICONS[k], label, cause, text: `心情：${ICONS[k]} ${label}${cause ? '（' + cause + '）' : ''}`, val: Math.round(m.val * 100) / 100 };
  };

  // ───────── 對外查詢（資訊卡、驗收用） ─────────
  M.get = id => { const c = C(id), m = mindOf(c); if (!m) return null; return { id, traits: { ...m.t }, mood: { val: m.val, energy: m.energy, stress: m.stress }, face: m.faceName || c.expression, faceHeld: !!m.faceName, flag: m.flag && m.flag.name, last: m.last, mem: m.mem.slice(), habit: m.habit && W.time < m.habit.until ? { ...m.habit } : null, wary: W.time < m.wary, scene: m.sc && m.sc.name, burned: m.burned, expression: c.expression }; };
  M.mindOf = id => mindOf(C(id));
  M.faceClass = name => HAPPY_FACES.has(name) ? 'happy' : SAD_FACES.has(name) ? 'sad' : WARY_FACES.has(name) ? 'wary' : 'other';
  M.reward = (id, kind = 'award', d = {}) => reward(id, d, kind);
  M.punish = (id, kind = 'rejected', d = {}) => punish(id, d, kind);

  // ───────── 事件接線 ─────────
  const KIND = { promoted: 'promote', awarded: 'award', item: 'item', praised: 'praise' };
  sub('rewarded', (id, d) => reward(id, d)); for (const n of ['promoted', 'awarded', 'item', 'praised']) sub(n, (id, d) => reward(id, d, KIND[n]));
  sub('rejected', (id, d) => punish(id, d, 'rejected')); sub('demoted', (id, d) => punish(id, d, 'demote')); sub('bonked', (id, d) => punish(id, d, 'bonk'));
  sub('comforted', id => { const c = C(id), m = mindOf(c); if (!m) return; affect(m, { val: .12 }, CAUSE.comforted, 90); if (!m.sc) { scene(c, m, 3, 'comforted', sc => { sc.at(0, () => { face(c, m, 'relieved', 1.8); }).at(1.8, () => { }); holdCap(c, m, sc); }); } });
  sub('fired', fired); sub('fired_door', firedDoor); sub('jobless_arrived', jobless); sub('rehired', rehired);
  sub('knocked', knocked); sub('burned', burned); sub('recovered', recovered);
  for (const n of EV) handlers[n] || (handlers[n] = []);
  // 想用 W.on 接線（別人建的匯流排）時：把我的處理函式也掛上去，避免只靠包過的 emit
  if (S) S.on((e, s, x) => { if (e.name === 'rate_limit_event' || e.name === 'rate_limits' || e.name === 'QuotaRecovered') onQuota(!!(x && x.wasExhausted)); });

  // 每週績效：上週升等的人有點得意，降等的人想再加油（只推一點心情基準，不演戲）
  function weekBias() {
    const R0 = W.rewards; if (!R0 || !R0.on) return;
    for (const c of people()) { const m = mindOf(c), u = R0.unit(c.spec.id); if (!m || !u || !u.row || !u.row.grade) continue; const r = u.row; if (!r.prevGrade) continue;
      const gi = g => R0.GRADES ? R0.GRADES.indexOf(g) : 'SABCDEF'.indexOf(g), d = gi(r.prevGrade) - gi(r.grade);
      if (d > 0) { m.bias = .14; m.base.val = clamp(m.base.val + .14, -.3, .5); m.val = Math.max(m.val, m.base.val); m.cause = { text: '上週升到 ' + r.grade, until: 1e12 }; }
      else if (d < 0) { m.bias = -.08; m.base.val = clamp(m.base.val - .08, -.3, .5); m.val = Math.min(m.val, m.base.val + .02); m.cause = { text: '上週降到 ' + r.grade + '，想再加油', until: 1e12 }; } }
  }

  // ───────── 每一步：場景推進、心情隨時間變化、基準表情、習慣 ─────────
  let t1 = 0, lastSelSeen = null, nextWrap = 0;
  M.tick = dt => {
    const now = W.time;
    if (now >= nextWrap) { nextWrap = now + 1; bus(); for (const c of people()) { const m = mindOf(c); wrap(c, m); } }
    const sel = W.pilot && W.pilot.sel; if (sel !== lastSelSeen) { lastSelSeen = sel; if (sel && !sel.spec.pet) onSelect(sel); }
    for (const c of W.chars.values()) {
      const m = M.minds.get(c.spec.id); if (!m || !c._mindW) continue;
      const sc = m.sc;
      if (sc) {
        if (sc.poll && sc.poll()) endScene(c, m);
        else { while (sc.i < sc.steps.length && now - sc.t0 >= sc.steps[sc.i].t) { const s = sc.steps[sc.i++]; try { s.fn(); } catch (e) { console.error(e); } } if (!sc.poll && sc.i >= sc.steps.length && now - sc.t0 >= sc.len + .05) endScene(c, m); }
      }
      if (m.spin) { const u = (now - m.spin.t0) / m.spin.dur; if (u >= 1 || c.state !== 'stand') m.spin = null; else c.heading = m.spin.h0 + Math.PI * 2 * u; }
      if (!c.jobless) m.rehiring = false;
      if (c.jobless && !m.jobT && !m.rehiring) { m.jobT = now - 60; m.val = Math.min(m.val, -.15); m.flag = { name: 'jobless', until: 1e12 }; }
      if (!c.jobless && m.jobT && !(m.flag && m.flag.name !== 'jobless')) { m.jobT = 0; if (m.flag && m.flag.name === 'jobless') m.flag = null; }
      if (m.faceName && now >= m.faceUntil && !m.sc) { m.faceName = null; m.holdUntil = 0; applyBase(c, m, true); }
      if (m.flag && m.flag.until < 1e11 && now > m.flag.until) m.flag = null;
      m.acc += dt; if (m.acc < .25) continue; const d = m.acc; m.acc = 0;
      // 心情隨時間回到基準：負面的拉回要看敏感與樂觀；工作中壓力慢慢上升、精力下降
      let base = m.base.val; if (c.jobless && m.jobT) base = lerp(Math.min(m.base.val, -.3), .05, clamp((now - m.jobT) / 120, 0, 1));
      const neg = m.val < base, tau = neg ? (18 + 70 * m.t.sens) * (1.25 - .8 * m.t.opt) : 35; m.val += (base - m.val) * (1 - Math.exp(-d / tau));
      const ag = S && S.agents.get(c.spec.id), working = !!(ag && ag.phase === 'doing') || c.action === 'type';
      if (c.sleeping || c.action === 'sleep') { m.energy = clamp(m.energy + d / 120, 0, 1); m.stress = clamp(m.stress - d / 60, 0, 1); }
      else { m.energy = clamp(m.energy + (working ? -d / 900 : (m.base.energy - m.energy) * d / 500), 0, 1); m.stress = clamp(m.stress + (working && ag && ag.phase === 'doing' ? d / (150 * (.6 + m.t.pat)) : -d / 100), 0, 1); }
      if (m.cause && now > m.cause.until) m.cause = null;
      // 走路：心情差垂頭走、心情好輕快（偶爾哼歌）
      const walking = c.state === 'walk' && !c.piloted && !(A() && A().current() === c) && !m.sc;
      if (walking && m.val < -.3 && c.state === 'walk') { c.lookAt(downPt(c)); m.lookDown = true; } else if (m.lookDown) { m.lookDown = false; if (!(A() && A().current() === c)) c.lookAt(null); }
      if (walking && m.val > .4 && Math.random() < .03 && !c.emoteSym) c.emote('note', 1.2);
      if (!m.sc && !c.sleeping && now >= m.holdUntil) applyBase(c, m, false);
      if (now >= m.nextHabit && habitOk(c, m)) doHabit(c, m); else if (now >= m.nextHabit + 30) m.nextHabit = now + 6;
    }
    if (saveT === 0 && false) saveNow();
  };

  // 初始：套每週績效的心情基準，並讓每個人都有「心」
  for (const c of people()) mindOf(c);
  weekBias();
  M.weekBias = weekBias;
  void hhmm; void lastSel;
  return M;
}
