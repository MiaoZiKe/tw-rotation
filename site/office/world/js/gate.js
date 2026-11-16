// 功能閘門（2026-11-15）：AI 辦公室頁的「功能鍵＋各方案每日次數」判斷，跟主站同一套規則、同一份宣告。
//
// 為什麼是一支薄的相容層，不直接載入主站的 perm.js／quota.js／account.js：
//   那三支綁著主站的版面（鎖頭蓋在主站的 DOM 選擇器上、用完時跳主站的卡片、登入視窗…），搬進 3D 辦公室只會多一堆用不到的程式碼與副作用。
//   這裡只做辦公室需要的四件事，而且「資料來源」與主站完全一致，不另造規則：
//     ① 功能鍵與預設值：讀 ../features.js（window.TwFeatures；鍵 office.cmd／office.connect／office.hr 在那裡宣告，plan_presets.js 寫四個方案的數字）
//     ② 這個人的方案、開關、每日次數：Worker 的 /v1/perm/me（跟主站 perm.js 同一支）；站主旗標：/v1/me 的 user.owner
//     ③ 體驗額度：/v1/grants/me、/v1/grants/hit（跟主站 grants.js 同一支；Worker 只驗鍵的格式，新鍵不必重新部署）
//     ④ 今天用了幾次：沿用主站的 localStorage 鍵 tw.quota（同源，所以主站「我的額度」看得到辦公室用掉幾次）＋登入者送 /v1/quota/hit 跟伺服器對帳
//
// 規則（跟主站一致，不要在這裡另外發明）：
//   · 站長（owner）永遠不受限；預覽網址（/preview/）比照主站 DECISIONS #343 一律全開，除非網址帶 ?demo_tier=guest|free|plus|pro 才照那個身分算（給 Andy 看被鎖的樣子）。
//   · 會員系統沒開（account_config.js 沒網址）、連不到 Worker：一律放行（主站「寧可多給、不要誤鎖」的慣例）。
//   · 訪客（沒登入）：limBy.guest 0＝不開放。0 與「開關關閉」都顯示「沒有開放」，用完（N＞0）顯示「今天的次數用完了，明天會恢復」。
//   · 用完時如果有體驗額度：這一次改扣體驗（begin() 先向 /v1/grants/hit 扣一次，成功才放行）。
//   · 後端收件服務仍只認站長；這裡只是前端閘門，擋的是畫面上的操作。
//
// 用法：const t = await W.gate.begin('office.cmd'); if (!t.pass) { 顯示 t.note; return; } …做事…; 成功 t.done()／失敗 t.cancel()。
//   · 每日次數是「做成功才扣」（送出失敗、連不上收件服務不吃次數）；體驗次數是放行前就向伺服器扣（沒辦法反悔，Worker 沒有退還的路）。
//   · peek(id) 不扣次、不發請求（用目前已載入的狀態），給畫面決定要不要把鈕灰掉。
// 文案禁用字（辦公室頁一律不出現）：價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵。

const ACCT_TOK = 'tw.acct.tok', TQ = 'tw.quota', DEMO_K = 'tw.demo.tier';
export const GATE_IDS = ['office.cmd', 'office.connect', 'office.hr', 'office.overview', 'office.save', 'office.budget', 'office.autoassign', 'office.scorecard', 'office.awaypack', 'office.replay', 'office.blueprint', 'office.priority'];   // 2026-11-16 加 office.save（雲端存檔，save.js）、office.budget（今日預算，budget.js）
const NAME = { 'office.cmd': '下指令', 'office.connect': '連接', 'office.hr': '人事異動', 'office.overview': '總覽', 'office.save': '雲端存檔', 'office.budget': '今日預算', 'office.autoassign': '自動派工', 'office.scorecard': '單件成績單', 'office.awaypack': '離開成果包與提醒', 'office.replay': '任務重播', 'office.blueprint': '任務藍圖', 'office.priority': '優先度表' };
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const tpeDay = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
const unitKey = () => 'n' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);   // 跟主站 quota.js use() 同一個格式（Worker 驗 ^[0-9A-Za-z_.-]{1,24}$）
const F = () => window.TwFeatures || null;

function qload() {
  let d = null; try { d = JSON.parse(lsGet(TQ) || 'null'); } catch (e) { d = null; }
  if (!d || d.day !== tpeDay() || typeof d.k !== 'object' || !d.k) d = { day: tpeDay(), k: {} };
  return d;
}
function qsave(d) { try { localStorage.setItem(TQ, JSON.stringify(d)); } catch (e) { /* 私密視窗：只在這次載入有效（下面 mem 備援） */ } }

export function createGate(W) {
  const G = { state: { src: 'default', who: 'guest', plan: '', owner: false, exempt: false, feats: {}, lims: {}, grants: null, demo: '' }, p: null, at: 0 };
  W.gate = G;

  const api = () => { const c = window.TW_ACCOUNT; return c && typeof c.api === 'string' ? c.api.replace(/\/+$/, '') : ''; };
  const tok = () => lsGet(ACCT_TOK) || '';
  async function post(path, body) {
    const u = api(); if (!u) return null;
    try {
      const r = await fetch(u + path, { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify(body || {}), credentials: 'omit' });
      let j = {}; try { j = await r.json(); } catch (e) { j = {}; }
      j._s = r.status; return j;
    } catch (e) { return null; }
  }
  const loadScript = src => new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); setTimeout(res, 4000); document.head.append(s); });

  // ───────── 今天用了幾次（tw.quota 同一份） ─────────
  const used = id => (qload().k[id] || []).length;
  function addUse(id, key) { const d = qload(); const s = new Set(d.k[id] || []); s.add(key); d.k[id] = [...s]; qsave(d); }
  function dropUse(id, key) { const d = qload(); d.k[id] = (d.k[id] || []).filter(x => x !== key); qsave(d); }

  // ───────── 載入：這個人的方案、開關、次數、體驗 ─────────
  const planKey = () => { const s = G.state; return s.who === 'guest' ? 'guest' : !s.plan || s.plan === 'free' ? 'free' : s.plan; };
  function demoTier() {
    // 預覽網址或本機驗收：?demo_tier= 指定身分（寫進 sessionStorage，換頁還在；跟主站 quota.js 同一個鍵）
    if (!(/\/preview\//.test(location.pathname) || /^(localhost|127\.0\.0\.1)$/.test(location.hostname))) return '';
    let t = (/[?&]demo_tier=([a-z]+)/.exec(location.search) || [])[1] || '';
    try { if (t) sessionStorage.setItem(DEMO_K, t); else t = sessionStorage.getItem(DEMO_K) || ''; } catch (e) { /* 略 */ }
    return /^(guest|free|plus|pro)$/.test(t) ? t : '';
  }
  async function doLoad() {
    const S = G.state; S.demo = demoTier();
    if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
    if (!window.TwFeatures) await loadScript('../features.js');
    if (S.demo) {
      // 示範身分：直接讀 plan_presets.js 的範本，不碰會員伺服器
      if (!window.TW_PLAN_PRESETS) await loadScript('../plan_presets.js');
      const t = ((window.TW_PLAN_PRESETS || {}).tiers || []).find(x => x.key === S.demo) || {};
      Object.assign(S, { src: 'demo', who: S.demo === 'guest' ? 'guest' : 'member', plan: S.demo === 'guest' || S.demo === 'free' ? '' : S.demo, owner: false, exempt: false, feats: t.feats || {}, lims: t.lims || {}, grants: null });
      fill(); return S;
    }
    if (/\/preview\//.test(location.pathname)) { Object.assign(S, { src: 'preview', exempt: true }); return S; }   // 預覽版一律全開（主站 DECISIONS #343）
    if (!api()) { Object.assign(S, { src: 'default' }); return S; }                                              // 會員系統沒開：全開
    const t = tok();
    let [pm, me, gr] = await Promise.all([post('/v1/perm/me', t ? { t } : {}), t ? post('/v1/me', { t }) : null, t ? post('/v1/grants/me', { t }) : null]);
    if (t && pm && pm._s === 401) { pm = await post('/v1/perm/me', {}); me = null; gr = null; }                  // 權杖失效：當訪客算（chat.js 自己會顯示「請重新登入」）
    if (!pm || pm._s !== 200 || !pm.feats) { Object.assign(S, { src: 'default', owner: false }); return S; }       // 連不到：放行
    Object.assign(S, { src: 'server', who: pm.who || 'guest', plan: pm.plan || '', feats: pm.feats || {}, lims: pm.lims && typeof pm.lims === 'object' ? pm.lims : {},
      owner: !!(me && me._s === 200 && me.user && me.user.owner), grants: gr && gr._s === 200 ? gr : null });
    fill();
    // 登入者：跟伺服器對帳今天已用的（別台裝置用過的也算進來）
    if (t && !S.owner) {
      await Promise.all(GATE_IDS.filter(id => { const n = lim(id); return Number.isFinite(n) && n > 0; }).map(async id => {
        const j = await post('/v1/quota/hit', { t, k: id });
        if (j && j._s === 200 && Array.isArray(j.keys)) { const d = qload(); const s = new Set(d.k[id] || []); j.keys.forEach(x => s.add(x)); d.k[id] = [...s]; qsave(d); }
      }));
    }
    return S;
  }
  // 範本沒寫的項目補上 features.js 的預設（開關 defBy、次數 limBy）——跟主站 perm.js 同一個做法
  function fill() {
    const Ft = F(), S = G.state; if (!Ft) return;
    const pk = planKey(), dl = Ft.limDefaults ? Ft.limDefaults(pk) : {};
    GATE_IDS.forEach(id => {
      if (!Object.prototype.hasOwnProperty.call(S.lims, id) && S.feats[id] !== false && Object.prototype.hasOwnProperty.call(dl, id)) S.lims = Object.assign({}, S.lims, { [id]: dl[id] });
    });
  }
  G.load = function (force) {
    if (!force && G.p && Date.now() - G.at < 30000) return G.p;
    G.at = Date.now(); G.p = doLoad().catch(() => { G.state.src = 'default'; return G.state; });
    return G.p;
  };

  // ───────── 判斷（不扣次） ─────────
  function lim(id) { const v = G.state.lims[id]; return Number.isInteger(v) && v >= 0 ? v : Infinity; }
  function enabled(id) {
    const f = F(), v = G.state.feats[id]; if (typeof v === 'boolean') return v;
    return f && f.byId(id) ? f.defOf(f.byId(id), planKey()) !== false : true;
  }
  const grantLeft = id => { const gr = G.state.grants; if (!gr || !gr.grants) return 0; const now = Date.now(); return gr.grants.filter(g => g.end > now && g.start <= now + 60000 && g.feats && g.feats[id]).reduce((s, g) => s + (g.feats[id].left || 0), 0); };
  function peek(id) {
    const S = G.state, n = lim(id), u = used(id), name = NAME[id] || '這個功能';
    const open = { id, pass: true, via: 'daily', kind: 'open', limit: n, used: u, left: n === Infinity ? Infinity : Math.max(0, n - u), grant: 0, note: '' };
    if (S.owner || S.exempt || S.src === 'default' || S.src === 'preview') return { ...open, limit: Infinity, left: Infinity };   // 不受限的身分：不管範本寫幾次，都不計次
    const gl = grantLeft(id);
    const login = S.who === 'guest';
    if (!enabled(id) || n === 0) {
      if (gl > 0) return { ...open, via: 'grant', kind: 'grant', grant: gl, note: `你有體驗次數 ${gl} 次，這一次會用掉 1 次。` };
      return { ...open, pass: false, kind: login ? 'login' : 'off', note: login ? `${name}要先登入才能使用。登入之後，每天都有可以用的次數。` : `${name}目前沒有開放給你的帳號。` };
    }
    if (u >= n) {
      if (gl > 0) return { ...open, via: 'grant', kind: 'grant', grant: gl, note: `今天的${name}次數用完了（今天 ${u}／${n}）。你還有體驗次數 ${gl} 次，這一次會用掉 1 次。` };
      return { ...open, pass: false, kind: 'out', note: `今天的${name}次數用完了（今天 ${u}／${n}），明天會恢復。` };
    }
    return open;
  }
  G.peek = peek;
  G.used = used;

  // ───────── 開始一個動作：放行就回 { pass:true, done(), cancel() } ─────────
  G.begin = async function (id) {
    await G.load();
    const g = peek(id);
    if (!g.pass) return { ...g, done() { }, cancel() { } };
    if (g.via === 'grant') {
      const t = tok(), key = unitKey();
      const j = t ? await post('/v1/grants/hit', { t, k: id, key }) : null;
      if (j && j._s === 200 && j.ok) { if (G.state.grants) G.state.grants = null; G.load(true); return { ...g, done() { }, cancel() { } }; }
      return { ...g, pass: false, kind: 'out', note: j && j._s === 200 && j.over ? `今天的${NAME[id] || '這個功能'}次數用完了，體驗次數也用完了，明天會恢復。` : '連不上會員伺服器，這一次先不執行，請稍後再試。', done() { }, cancel() { } };
    }
    if (g.limit === Infinity) return { ...g, done() { }, cancel() { } };         // 不限次數：不記
    const key = unitKey(); let fin = false;
    return { ...g, done() {
      if (fin) return; fin = true; addUse(id, key);
      const t = tok(); if (t && G.state.src === 'server') post('/v1/quota/hit', { t, k: id, key }).then(j => { if (j && j._s === 200 && j.over) dropUse(id, key); });
    }, cancel() { fin = true; } };
  };

  // ───────── 被鎖的白話說明（浮在畫面下方，6 秒或點一下收掉）：給沒有自己位置放說明的操作（例如資訊卡上的「重新聘用」） ─────────
  G.say = function (text) {
    let el = document.getElementById('gateSay');
    if (!el) { el = document.createElement('div'); el.id = 'gateSay'; el.className = 'gate-say'; el.setAttribute('role', 'status'); el.onclick = () => { el.hidden = true; }; (document.getElementById('app') || document.body).append(el); }
    el.textContent = text; el.hidden = false; clearTimeout(el._t); el._t = setTimeout(() => { el.hidden = true; }, 6000);
  };
  return G;
}
