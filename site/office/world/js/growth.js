// 成長系統（2026-11-16，擁有者：「參考 3D 經營遊戲，補角色基礎設定：專長、體力壓力、個性、等級、自動派工、每日結算與短期目標」）。
// 這支只管「資料與規則」，畫面全部在 growth_ui.js。掛法：world.html 載入 growth.js（跟 connect_link.js 一樣獨立，不碰 main.js），
// 它等 window.__world.ready 之後才啟動，把自己放在 W.growth。
//
// 六件事：
//   ① 專長（工作適性）：每位 2～3 項，每項 1～5 星。由「職稱／類型文字」＋部門預設推出（用代號雜湊決定星數，固定不變）；
//      之後每完成一件「派工說明」對得上的任務就累積練習，每 3 次多 1 星（上限 5），所以專長會被工作練出來。
//   ② 體力／壓力：工作（領任務、進行中、交件）降體力、升壓力；休息區、茶水間、運動、睡覺、飲水機恢復。
//      低體力或高壓力時工作動畫變慢（包住 c.update 的時間步）、頭上週期性冒汗滴；體力太低、手上沒事時自己去休息，直到恢復。
//      數值同步寫回 mind.js 的精力／壓力，心情列與這裡的數字不會互相矛盾。
//   ③ 個性特質：每位固定 1～2 個（用代號雜湊決定，換裝改名不變），影響消耗／恢復速度與台詞。
//   ④ 等級與經驗值：完成派工得經驗（對得上專長多一點、完美主義者多一點），升級（畫面上一律稱「晉級」）有小慶祝。
//   ⑤ 依專長自動派工：示範／模擬模式下，CEO 依專長挑人並說出理由，真的派出一件任務；真實專案只做「建議人選」標示，不動 Claude 真實派工。
//   ⑥ 每日結算卡＋短期目標：台北時間 18:00 下班（或按鈕）跳出今日結算；今天 3 個短期目標，達成有提示。
// 狀態存 localStorage，鍵名統一 aiOffice.game.<範圍>（範圍＝專案 id／辦公室 id／示範）；之後雲端存檔接這個鍵。
// 去重靠「完成時間＋標題」做鍵（每位留最近 80 筆），重新整理後即時資料重送也不會重複給經驗。
// 畫面禁用字：價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵（一律用「晉級」「等級提升」）。
import { mountGrowthUI } from './growth_ui.js';
import { taipeiNow } from './daytime.js';

export const SKILLS = ['寫程式', '設計', '研究', '測試', '文案', '資料', '部署', '稽核', '影音'];
// 文字 → 專長：用在「職稱」與「派工說明」。命中次數最多者勝，同分取 SKILLS 順序。
const KW = {
  '寫程式': /程式|前端|後端|動效|工程|開發|實作|重構|函式|介面|頁面|延後載入|縮放|修一個|bug|code|frontend|mobile|engineer|coder|\bui\b|\bcss\b|\bapi\b/i,
  '設計': /設計|版型|美編|配色|圖表庫|插圖|繪圖|封面|視覺|排版|海報|貼文版|illustr|design|visual/i,
  '研究': /研究|分析|成分|口徑|供應鏈|族群|估值|法人|策略|產業|調研|查證|回測|輪動|財報|半導體|載板|伺服器|analyst|research|quant/i,
  '測試': /測試|驗收|品質|校驗|核對|檢查|驗證|比對|test|qa\b|review/i,
  '文案': /文案|貼文|發文|文章|週報|企劃|行銷|公告|編輯|標題|提案|說明|頻道|content|copy|write/i,
  '資料': /資料|抓取|補齊|盤後|資料湖|匯入|欄位|治理|data|scrap|etl/i,
  '部署': /部署|上線|推送|發布|排程|交付|效率|deploy|release|workflow|ops/i,
  '稽核': /稽核|審核|合規|法遵|資安|隱私|條款|監察|風險|審查|audit|legal|security|inspector|compliance/i,
  '影音': /影片|動畫|分鏡|剪輯|比比|配音|補幀|動態|音效|video|motion|animat|bibi/i,
};
// 部門預設專長（主、次）；對不上的部門（專案區塊、其他專案）改用文字推，再不行就「研究、文案」
const DEPT = { data: ['資料', '部署'], quant: ['研究', '資料'], industry: ['研究', '文案'], frontend: ['寫程式', '設計'], design: ['設計', '影音'], social: ['文案', '研究'], video: ['影音', '設計'], biz: ['文案', '研究'], legal: ['稽核', '研究'], ops: ['部署', '測試'], audit: ['稽核', '測試'], ceo: ['研究', '文案'] };
export function skillOfText(t) {
  t = String(t || ''); let best = null, bn = 0;
  for (const k of SKILLS) { const m = t.match(new RegExp(KW[k].source, 'gi')); const n = m ? m.length : 0; if (n > bn) { bn = n; best = k; } }
  return best;
}
// 示範用的任務池（每項都要能被 skillOfText 對回自己的專長；驗收會逐條檢查）
export const TASKS = {
  '寫程式': ['修一個畫面對不齊的問題', '把圖表改成延後載入'], '設計': ['做一張貼文封面', '圖表庫新增一款配色'],
  '研究': ['整理這週族群輪動重點', '核對估值口徑'], '測試': ['跑一輪真人操作驗收', '檢查手機版面有沒有跑掉'],
  '文案': ['寫盤後主貼文', '整理功能公告'], '資料': ['補齊今天的盤後資料', '核對資料欄位'],
  '部署': ['部署兩站並確認上線', '整理批次排程'], '稽核': ['檢查條款與隱私說明', '稽核本批回報'], '影音': ['做一支短影片分鏡', '剪輯今天的動畫'],
};

// 個性特質：drain 體力消耗倍率、stress 壓力累積倍率、xp 經驗倍率、rec 各種休息的恢復倍率（沒寫＝1）、night 18～6 點的消耗倍率
export const TRAITS = {
  hasty: { zh: '急性子', desc: '做事俐落、壓力累積得比較快', drain: 1.1, stress: 1.35, say: { go: '馬上開始！', up: '晉級了，下一件！', tired: '好累…但還要趕', rest: '快，我去充個電' } },
  perfect: { zh: '完美主義', desc: '任務做得細，經驗多 15%，但壓力累積比較快', stress: 1.25, xp: 1.15, say: { go: '我會做到沒有挑剔的地方', up: '還能更好', tired: '再檢查一遍就好…', rest: '休息一下，等等再校一次' } },
  night: { zh: '夜貓子', desc: '晚上 18 點後體力消耗慢，白天比較容易累', night: 0.7, drain: 1.1, say: { go: '這個時間剛好', up: '晚上狀態好！', tired: '白天真的太睏…', rest: '我先趴一下' } },
  social: { zh: '社交咖', desc: '在休息區、茶水間跟人聊聊，恢復得更多', rec: { lounge: 1.4, pantry: 1.5, water: 1.3 }, say: { go: '交給我，有事大家一起想', up: '大家一起升起來！', tired: '好想找人聊聊…', rest: '去茶水間找人聊天' } },
  chill: { zh: '悠哉派', desc: '壓力累積慢，但恢復也比較慢', stress: 0.7, recAll: 0.9, say: { go: '好喔，慢慢來', up: '喔，晉級了', tired: '嗯…有點累', rest: '休息一下下' } },
  sporty: { zh: '運動魂', desc: '運動、游泳時恢復加倍', rec: { sport: 1.7 }, say: { go: '活動筋骨前先把這個做完', up: '漂亮，再來一局！', tired: '該去動一動了', rest: '去運動一下' } },
  foodie: { zh: '貪吃鬼', desc: '茶水間的點心與咖啡恢復加倍', rec: { pantry: 1.7, water: 1.3 }, say: { go: '做完就能吃點心了', up: '今天要加菜', tired: '肚子也餓了…', rest: '我去找點心' } },
  grind: { zh: '工作狂', desc: '體力消耗慢，但不太會休息、恢復比較慢', drain: 0.8, recAll: 0.85, say: { go: '再多給我一件也行', up: '繼續衝', tired: '還撐得住…吧', rest: '好吧，休息五分鐘' } },
};
const TRAIT_IDS = Object.keys(TRAITS);

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hash = s => { let h = 2166136261; for (const ch of String(s)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; } h ^= h >>> 15; h = Math.imul(h, 2246822519) >>> 0; h ^= h >>> 13; h = Math.imul(h, 3266489917) >>> 0; h ^= h >>> 16; return h >>> 0; };   // 結尾的混合讓相近的代號也分得開
const tpeDay = (ms = Date.now()) => new Date(ms + 8 * 3600e3).toISOString().slice(0, 10);
export const needFor = lv => 40 + 20 * (lv - 1);                 // 從 lv 升到 lv+1 要多少經驗
export const MAXLV = 20;
const RATE = { sleep: 1.5, sport: 2.0, lounge: 3.0, pantry: 3.0, water: 2.0, outside: 0.8 };   // 每模擬秒恢復的體力（壓力同時降 0.7 倍）；休息的路程只有幾秒到幾十秒，所以數字比工作消耗大得多
const REST_ZH = { sleep: '睡覺', sport: '運動', lounge: '休息區', pantry: '茶水間', water: '飲水機', outside: '無業遊民區' };
export const DRAIN = 0.12, STRESS_UP = 0.10;                     // 每模擬秒的工作消耗

export function createGrowth(W) {
  const qs = new URLSearchParams(location.search), S = W.state;
  const scope = (/^[0-9a-f]{16}$/.test(qs.get('project') || '') ? qs.get('project') : null) || (/^[A-Za-z0-9_-]{1,40}$/.test(qs.get('office') || '') ? qs.get('office') : null) || 'demo';
  const KEY = 'aiOffice.game.' + scope;
  const G = { scope, key: KEY, dirty: false, ready: false, cfg: { restBelow: 25, restUntil: 60, stressRest: 85, noAutoRest: false, settleHour: 18 } };
  W.growth = G; G.SKILLS = SKILLS; G.TRAITS = TRAITS; G.TASKS = TASKS; G.skillOfText = skillOfText; G.needFor = needFor;
  const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  let save = null; try { save = JSON.parse(lsGet(KEY) || 'null'); } catch (e) { save = null; }
  if (!save || save.v !== 1 || typeof save.chars !== 'object') save = { v: 1, chars: {}, day: null };
  G.save = save;
  const persist = () => { if (!G.dirty) return; G.dirty = false; try { localStorage.setItem(KEY, JSON.stringify(save)); } catch (e) { /* 私密視窗：只在這次載入有效 */ } };
  setInterval(persist, 4000); addEventListener('pagehide', persist); addEventListener('beforeunload', persist);
  G.flush = persist;

  // ───────── 今天（台北時間） ─────────
  const memberCount = () => members().length;
  function newDay(d) { return { d, done: 0, failed: 0, xp: 0, byId: {}, lvUps: [], rested: [], goals: { done: false, lvup: false, rest: false }, settled: false }; }
  function ensureDay() { const d = tpeDay(); if (!save.day || save.day.d !== d) { save.day = newDay(d); G.dirty = true; } return save.day; }
  G.day = () => ensureDay();
  G.goals = () => {
    const D = ensureDay(), n = Math.max(1, memberCount()), restT = Math.min(3, n);
    return [
      { id: 'done', text: '今天完成 5 件任務', cur: Math.min(D.done, 5), target: 5, ok: D.done >= 5 },
      { id: 'lvup', text: '有 1 位同事晉級', cur: Math.min(D.lvUps.length, 1), target: 1, ok: D.lvUps.length >= 1 },
      { id: 'rest', text: restT > 1 ? `${restT} 位同事休息恢復體力` : '有 1 位同事休息恢復體力', cur: Math.min(D.rested.length, restT), target: restT, ok: D.rested.length >= restT },
    ];
  };
  function checkGoals() {
    const D = ensureDay();
    for (const g of G.goals()) if (g.ok && !D.goals[g.id]) { D.goals[g.id] = true; G.dirty = true; G.ui && G.ui.goalHit(g); W.emit && W.emit('growth_goal', 'ceo', { goal: g.id }); }
  }

  // ───────── 成員 ─────────
  const okChar = c => c && !c.spec.pet && !c.spec.isCeo && !c.jobless && !c.away;
  function members() { return [...W.chars.values()].filter(okChar); }
  G.members = members;
  const mindOf = c => (W.mind && W.mind.mindOf ? W.mind.mindOf(c) : null);

  // ───────── 每位的紀錄 ─────────
  function baseSkills(spec) {
    const mem = W.members && W.members.get(spec.id), text = [spec.id, spec.zh, mem && mem.deptName, spec.dept].join(' ');
    const picked = [];
    for (const k of SKILLS) if (KW[k].test(String(spec.zh))) picked.push(k);                          // 職稱的中文最準
    for (const k of SKILLS) if (!picked.includes(k) && KW[k].test(String(spec.id))) picked.push(k);   // 再看代號（英文）
    for (const k of SKILLS) if (!picked.includes(k) && KW[k].test(text)) picked.push(k);
    for (const k of DEPT[spec.dept] || (W.blocks ? ['研究', '文案'] : [])) if (!picked.includes(k)) picked.push(k);
    if (!picked.length) picked.push('研究', '文案');
    const n = 2 + (hash(spec.id + 'n') % 2), out = [];                                              // 2 或 3 項
    for (let i = 0; i < Math.min(n, picked.length); i++) { const k = picked[i], h = hash(spec.id + k); out.push({ k, n: i === 0 ? 4 + (h % 2) : i === 1 ? 2 + (h % 2) : 1 + (h % 2) }); }
    return out;
  }
  function pickTraits(id) {
    const a = hash(id + 'trait') % TRAIT_IDS.length, out = [TRAIT_IDS[a]];
    if (hash(id + 'two') % 2) { const b = (a + 1 + (hash(id + 'trait2') % (TRAIT_IDS.length - 1))) % TRAIT_IDS.length; out.push(TRAIT_IDS[b]); }
    return out;
  }
  function rec(c) {
    const id = c.spec.id; let r = save.chars[id];
    if (!r) {
      const m = mindOf(c);
      r = save.chars[id] = { xp: 0, lv: 1, sta: Math.round(clamp(m ? m.energy * 100 : 85, 30, 100)), str: Math.round(clamp(m ? m.stress * 100 : 10, 0, 90)), prac: {}, done: 0, failed: 0, keys: [], fresh: true };
      G.dirty = true;
    }
    if (!r._sk || r._skId !== c.spec.id) { r._sk = baseSkills(c.spec); r._skId = c.spec.id; }
    if (!r._tr) r._tr = pickTraits(id);
    return r;
  }
  const stars = (r, k) => { const b = (r._sk.find(x => x.k === k) || { n: 0 }).n, p = Math.floor(((r.prac || {})[k] || 0) / 3); return clamp(b + p, b || p ? 1 : 0, 5); };
  const skillList = r => { const ks = new Set(r._sk.map(x => x.k)); for (const k of Object.keys(r.prac || {})) if (r.prac[k] >= 1) ks.add(k); return [...ks].map(k => ({ k, n: stars(r, k), base: r._sk.some(x => x.k === k) })).filter(x => x.n > 0).sort((a, b) => b.n - a.n); };
  const traitMods = r => {
    const T = r._tr.map(k => TRAITS[k]); const f = (key, d = 1) => T.reduce((p, t) => p * (t[key] == null ? 1 : t[key]), d);
    return { drain: f('drain'), stress: f('stress'), xp: f('xp'), night: f('night'), recAll: f('recAll'), rec: k => T.reduce((p, t) => p * ((t.rec && t.rec[k]) || 1), 1) };
  };
  G.get = id => {
    const c = W.chars.get(id); if (!c || c.spec.pet || c.spec.isCeo) return null; const r = rec(c);
    const w = working(c), rk = restKind(c);
    return { id, lv: r.lv, xp: r.xp, need: r.lv >= MAXLV ? 0 : needFor(r.lv), sta: Math.round(r.sta), str: Math.round(r.str), skills: skillList(r), traits: r._tr.map(k => ({ id: k, zh: TRAITS[k].zh, desc: TRAITS[k].desc })), done: r.done, failed: r.failed, working: w, resting: rk, restZh: rk ? REST_ZH[rk] : '', tired: tired(r), speed: speedOf(c, r, w) };
  };
  G.set = (id, p = {}) => { const c = W.chars.get(id); if (!c) return null; const r = rec(c); for (const k of ['sta', 'str', 'xp', 'lv']) if (p[k] != null) r[k] = +p[k]; r.sta = clamp(r.sta, 0, 100); r.str = clamp(r.str, 0, 100); G.dirty = true; return G.get(id); };   // 驗收與除錯用

  // ───────── 工作／休息判斷 ─────────
  const working = c => { const a = S && S.agents.get(c.spec.id); return !!a && a.phase !== 'idle'; };
  const sports = new Map();      // id → 最後一次運動事件的模擬時間（沒收到結束事件也會在 120 秒後自動失效）
  const restKind = c => {
    if (c.sleeping || c.action === 'sleep') return 'sleep';
    if (sports.has(c.spec.id) && W.time - sports.get(c.spec.id) < 120) return 'sport';
    if (c.state === 'walk' || c.state === 'held') return null;
    const p = c.object3D.position;
    if (W.outside && W.outside.inZone && W.outside.inZone(p.x, p.z)) return 'outside';
    const rm = W.roomAt && W.roomAt(p.x, p.z);
    if (rm && !c.atDesk) { if (rm.id === 'lounge' || rm.id === 'play') return 'lounge'; if (rm.id === 'pantry' || rm.id === 'food') return 'pantry'; }
    if (!c.atDesk && c.action === 'drink') return 'water';
    return null;
  };
  const tired = r => r.sta < 30 || r.str > 75;
  function speedOf(c, r, w) { if (!w) return 1; const s = r.sta < 20 ? 0.55 : r.sta < 40 ? 0.75 : 1, t = r.str > 85 ? 0.7 : r.str > 70 ? 0.85 : 1; return Math.min(s, t); }
  G.speedOf = id => { const c = W.chars.get(id); return c && !c.spec.pet && !c.spec.isCeo ? speedOf(c, rec(c), working(c)) : 1; };
  const wrapUpdate = c => {          // 疲累時工作（坐著）動畫變慢：打字等姿勢是用「時間」算的（不是時間步），所以時間步與時間都縮：
    // 角色拿到的時間＝真實時間減掉「累積少走的那一段」，單調遞增、不影響別的程式用 W.time 排的計時；走路與其他動作 k＝1，原樣
    if (c.__gw) return; c.__gw = true; c.__goff = 0; const o = c.update.bind(c);
    c.update = (h, t) => { let k = 1; if (c.state === 'sit' && okChar(c) && !c.piloted) { const r = save.chars[c.spec.id]; if (r && working(c)) k = speedOf(c, r, true); } if (k < 1) c.__goff += h * (1 - k); return o(h * k, t - c.__goff); };
  };

  // ───────── 經驗與等級 ─────────
  function award(c, entry, failed) {
    const r = rec(c), id = c.spec.id, D = ensureDay(), mod = traitMods(r), title = entry && entry.title || '';
    const sk = skillOfText(title), matched = sk ? stars(r, sk) : 0;
    let xp = failed ? 5 : Math.round(20 * mod.xp * (1 + 0.08 * matched));
    if (failed) r.failed++; else { r.done++; if (sk) { r.prac[sk] = (r.prac[sk] || 0) + 1; } }
    const doneToday = entry && entry.t ? tpeDay(entry.t) === D.d : true;
    if (doneToday) { const b = D.byId[id] || (D.byId[id] = { done: 0, xp: 0, failed: 0 }); if (failed) { D.failed++; b.failed++; } else { D.done++; b.done++; } D.xp += xp; b.xp += xp; }
    r.xp += xp; G.dirty = true;
    let ups = 0; while (r.lv < MAXLV && r.xp >= needFor(r.lv)) { r.xp -= needFor(r.lv); r.lv++; ups++; if (doneToday) D.lvUps.push({ id, lv: r.lv, nick: c.spec.nick, t: Date.now() }); G.ui && G.ui.levelUp(c, r.lv); }
    if (r.lv >= MAXLV) r.xp = 0;
    if (!ups) G.ui && G.ui.gain(c, xp, sk, failed);
    const tr = TRAITS[r._tr[0]]; if (ups && tr) c.say && c.say(tr.say.up, 2.4);
    checkGoals(); W.emit && W.emit('growth_xp', id, { xp, lv: r.lv, up: ups, skill: sk, failed: !!failed });
    return { xp, ups, skill: sk };
  }
  G.award = (id, entry, failed) => { const c = W.chars.get(id); return c && okChar(c) ? award(c, entry || {}, !!failed) : null; };
  function scanDone(c, r) {
    const a = S && S.agents.get(c.spec.id); if (!a) return;
    if (r.fresh) { r.fresh = false; }
    for (let i = a.done.length - 1; i >= 0; i--) {      // 舊的先算
      const e = a.done[i], k = (e.t || 0) + '|' + (e.title || '');
      if (r.keys.includes(k)) continue; r.keys.push(k); if (r.keys.length > 80) r.keys.shift(); award(c, e, false);
    }
    const f = a.failed || 0; if (f > (r.seenFail || 0)) { const n = f - (r.seenFail || 0); r.seenFail = f; for (let i = 0; i < n; i++) award(c, { title: a.task || '', t: Date.now() }, true); }
    else if (r.seenFail == null) r.seenFail = f;
  }

  // ───────── 每個模擬步 ─────────
  let acc = 0, wrapN = 0;
  const restState = new Map();    // id → { gain, day }：今天靠休息累積恢復了多少體力，滿 6 才算「休息恢復過一次」（短短一趟睡一下也要能累積，所以不看單趟）
  G.tick = h => {
    acc += h; if (acc < 0.25) return; const d = acc; acc = 0; if (!W.ready) return;
    const hr = taipeiNow().h, night = hr >= 18 || hr < 6;
    for (const c of members()) {
      if (!c.__gw) wrapUpdate(c);
      const r = rec(c), id = c.spec.id, mod = traitMods(r), w = working(c), rk = w ? null : restKind(c);
      scanDone(c, r);
      if (w) {
        r.sta -= d * DRAIN * mod.drain * (night && mod.night !== 1 ? mod.night : 1) * (1 + r.str / 150);
        r.str += d * STRESS_UP * mod.stress * (r.sta < 25 ? 1.6 : 1);
        if (r.sta <= 30 || r.str >= 75) {
          c._gT = (c._gT || 0) + d;
          if (c._gT > 5) { c._gT = 0; c.emote && c.emote('sweat', 2.2); if (Math.random() < 0.35 && !c.speech) { const t = TRAITS[r._tr[0]]; c.say && c.say(t.say.tired, 2.4); } }
        }
      } else if (rk) {
        const rate = RATE[rk] * mod.rec(rk) * mod.recAll, before = r.sta;
        r.sta += d * rate; r.str -= d * rate * 0.7;
        const s = restState.get(id) || { gain: 0, day: '' }; if (s.day !== ensureDay().d) { s.day = ensureDay().d; s.gain = 0; } s.gain += Math.max(0, Math.min(100, r.sta) - before); restState.set(id, s);   // 今天靠休息一共回了多少體力（睡一下、喝一杯、逛休息區都累積）
        if (s.gain >= 6) { const D = ensureDay(); if (!D.rested.includes(id)) { D.rested.push(id); G.dirty = true; checkGoals(); } }
      } else { r.sta += d * 0.03; r.str -= d * 0.05; }
      r.sta = clamp(r.sta, 0, 100); r.str = clamp(r.str, 0, 100); G.dirty = true;
      const m = mindOf(c); if (m) { m.energy = r.sta / 100; m.stress = r.str / 100; }       // 同步給心情層：心情列的「有點睏／壓力大」跟這裡的數字同一個來源
      // 手上沒事又很累：自己去休息，直到恢復（工作中不能休息，只會慢下來）
      if (r.sta < G.cfg.restBelow || r.str > G.cfg.stressRest) r.needRest = true; else if (r.sta >= G.cfg.restUntil && r.str < 50) r.needRest = false;
      if (r.needRest && !w && !G.cfg.noAutoRest && !c.busy && c.state === 'sit' && c.atDesk && !c.sleeping && !c.piloted && W.time >= (c._gNext || 0) && W.director && W.director.routine) {
        c._gNext = W.time + 6; const t = TRAITS[r._tr[0]], kind = W.blocks ? 'water' : r._tr.includes('foodie') || r._tr.includes('social') ? 'snack' : r._tr.includes('sporty') ? 'play' : 'rest';
        c.say && c.say(t.say.rest, 2.2); W.director.routine(id, kind);
      }
      if (c._gUp && W.time > c._gUp) c._gUp = 0;
    }
    G.ui && G.ui.tick();
    void wrapN;
  };
  const prevTick = W.mind && W.mind.tick; if (prevTick) { W.mind.tick = h => { prevTick(h); try { G.tick(h); } catch (e) { if (!G.err) { G.err = e; console.error('成長系統例外', e); } } }; }   // simStep 每步都會呼叫 W.mind.tick：掛在它後面，不用改 main.js

  // ───────── 事件：運動、被照顧、被誇獎／退件 ─────────
  // phys.js 的事件匯流排把「事件物件」當第一個參數傳進來（{id,…}），mind.js 的則是（代號, 資料）：兩種長相都吃
  const on = (n, fn) => { if (W.on) W.on(n, (a, b) => { try { if (a && typeof a === 'object') fn(a.id, a); else fn(a, b || {}); } catch (e) { console.warn('成長系統事件例外', e); } }); };
  on('sport_start', id => { sports.set(id, W.time); });
  on('sport_score', id => { if (sports.has(id)) sports.set(id, W.time); });
  on('sport_end', id => { sports.delete(id); });
  on('left_pool', id => { sports.delete(id); });
  const bump = (id, ds, dt) => { const c = W.chars.get(id); if (!c || !okChar(c)) return; const r = rec(c); r.sta = clamp(r.sta + (ds || 0), 0, 100); r.str = clamp(r.str + (dt || 0), 0, 100); G.dirty = true; };
  G.bump = bump;
  on('praised', id => bump(id, 0, -6)); on('rewarded', id => bump(id, 0, -10)); on('comforted', id => bump(id, 0, -8));
  on('rejected', id => bump(id, 0, 10)); on('knocked', id => bump(id, 0, 6)); on('burned', id => bump(id, 0, 12));

  // ───────── 依專長挑人 ─────────
  G.rank = (skill, opt = {}) => {
    const out = [];
    for (const c of members()) {
      if (opt.exclude && opt.exclude.includes(c.spec.id)) continue;
      const r = rec(c), n = stars(r, skill), w = working(c), idle = !w && !c.busy && !c.sleeping, rk = restKind(c);
      let score = n * 20 + r.sta * 0.3 - r.str * 0.2 + (idle ? 15 : w ? -30 : -12) + (c.sleeping ? -40 : 0) + (r.needRest ? -25 : 0);
      score += (hash(c.spec.id + skill) % 100) / 1000;                                     // 同分時固定順序（不隨機）
      const why = `${c.spec.nick}：${skill}${n ? ' ' + '★'.repeat(n) + '☆'.repeat(5 - n) : '（沒有這項專長）'}，體力 ${Math.round(r.sta)}，壓力 ${Math.round(r.str)}，${w ? '手上有事' : c.sleeping ? '睡覺中' : rk ? '休息中' : idle ? '目前閒置' : '正在忙'}`;
      out.push({ id: c.spec.id, nick: c.spec.nick, stars: n, sta: Math.round(r.sta), str: Math.round(r.str), idle, working: w, score, why });
    }
    return out.sort((a, b) => b.score - a.score);
  };
  G.real = () => !!(W.live && W.live.mode === 'live');
  // 自動派工：示範／模擬模式才真的派（走模擬器 → 狀態層 → 跟手動派一模一樣的演出）；真實專案只回建議人選
  G.assign = async skill => {
    if (!SKILLS.includes(skill)) return null;
    const list = G.rank(skill), top = list[0]; if (!top) return { error: '目前沒有可以派的人' };
    const task = (TASKS[skill] || ['一件新任務'])[(G.n = (G.n || 0) + 1) % 2];
    const res = { skill, task, who: top.id, nick: top.nick, why: top.why, others: list.slice(1, 3).map(x => x.why), real: G.real() };
    if (res.real) { G.ui && G.ui.suggest(res); return res; }
    const gt = W.gate ? await W.gate.begin('office.autoassign') : null;
    if (gt && !gt.pass) { G.ui && G.ui.blocked(gt.note); return { error: gt.note, blocked: true }; }
    let okk = false; try {
      const ceo = W.chars.get('ceo'); if (ceo && ceo.say) { ceo.say(`這件交給${top.nick}：${skill}${top.stars ? '★'.repeat(top.stars) : ''}`, 3.2); }
      W.sim.start(top.id, task); okk = true; G.ui && G.ui.why(res);
      const aid = W.sim.last.get(top.id); (async () => { await W.sleep(16 + Math.random() * 6); if (W.sim.last.get(top.id) === aid) W.sim.stop(top.id, true); })();   // 做一陣子就交件（模擬器沒有自動收件）
    } finally { if (gt) { if (okk) gt.done(); else gt.cancel(); } }
    return res;
  };

  // ───────── 結算 ─────────
  G.summary = () => {
    const D = ensureDay(), rows = Object.entries(D.byId).map(([id, b]) => ({ id, ...b, nick: (W.chars.get(id) || { spec: { nick: id } }).spec.nick }));
    const top = rows.filter(x => x.done > 0).sort((a, b) => b.done - a.done || b.xp - a.xp)[0] || null;
    const ms = members().map(c => ({ id: c.spec.id, nick: c.spec.nick, sta: Math.round(rec(c).sta), str: Math.round(rec(c).str) })).sort((a, b) => a.sta - b.sta || b.str - a.str);
    return { day: D.d, done: D.done, failed: D.failed, xp: D.xp, top, tiredest: ms[0] || null, lvUps: D.lvUps.slice(), goals: G.goals(), rested: D.rested.length };
  };
  G.settle = (auto = false) => { const D = ensureDay(); if (auto) D.settled = true; G.dirty = true; const sm = G.lastSummary = G.summary(); G.ui && G.ui.settle(sm, auto); };
  setInterval(() => {
    if (document.visibilityState === 'hidden' || !W.ready) return; const D = ensureDay(), t = taipeiNow();
    if (t.h >= G.cfg.settleHour && !D.settled && (D.done > 0 || D.failed > 0)) G.settle(true);
  }, 2000);

  G.ui = mountGrowthUI(G, W);
  G.ready = true; checkGoals();
  return G;
}

// ───────── 啟動：等辦公室準備好 ─────────
(function boot() {
  let n = 0; const t = setInterval(() => {
    const W = window.__world;
    if (W && W.ready && W.state && W.chars && W.mind && W.ui && !W.growth) { clearInterval(t); try { createGrowth(W); } catch (e) { console.error('成長系統啟動失敗', e); } }
    else if (++n > 600) clearInterval(t);
  }, 100);
})();
