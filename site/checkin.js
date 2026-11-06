/* ============================================================================
   每日簽到＋比比寶箱（site/checkin.js）—— 預覽版（階段 1：本機模擬，不碰後端）
   規格：docs/feature_proposals/checkin_spec_1107.md（附錄「CEO 11-07 拍板」優先）；Andy 11-07 原話：
   「簽到型式是日曆方式，當天沒簽到就繼續簽到今天，沒簽到就空白，有簽到會有註記。累積機制分 3～4 次，
    提供教學文章、產業詳細分析、功能許願（做不到就送 Plus 3 天）……做好的內容在精選文章內開分頁……
    沒有簽到可以透過跟比比互動 5～10 次換簽到，最多 3 次補簽……需要新增我可以自行簽到完成功能」。
   做法：
   · 儲存層轉接器：UI 只認 S（本機狀態），日後正式版換成 Worker 端點只換 load()/save()，畫面不動。
   · 狀態存 localStorage（預覽版由殼自動加前綴，跟正式站完全隔離），鍵 tw.ci.v1:<email 或 guest>。
   · 願望每一項各打一次現有 POST /v1/feedback（type='wish'），內文帶【簽到願望】【預覽】標記，站主在
     #admin/feedback 的「願望清單」看得到；Plus 3 天只在畫面模擬，不呼叫任何開通端點。
   · ★ 法遵：寶箱文章只能靠簽到解鎖，付費方案、站主身分都不能直接打開 —— unlocked() 只看簽到兌換紀錄，完全不看方案。
   · 站主測試工具只給 admin／owner（DOM 不輸出給一般會員）。
   · 手機（≤640）用底部面板；樣式全在 @media (max-width:640px) 內，不影響桌機（CLAUDE.md 10-08）。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  /* ------------------------------------------------------------------ 設定（manifest 沒到時的備用值） */
  const CFG0 = { nodes: [3, 7, 14, 20], makeup_cost: [5, 7, 10], makeup_max: 3, makeup_days: 7, wish_max: 5, wish_ticket_days: 60, teach_rotation: ['tech', 'chip', 'macro'] };
  const DAY_CAP = 4, GAP_MS = 20000, CLICK_MS = 3000;     // 每天最多計 4 次、兩次計分間隔 ≥20 秒、3 秒內連點不算
  const NODE_NAMES = ['教學包', '教學包', '產業深度包', '許願券'];
  const T = { off: 0, today: '', on: false };            // 驗收注入：假時間、假「今天」
  const WK = ['日', '一', '二', '三', '四', '五', '六'];

  let M = null, MP = null;                               // manifest 與載入中的 promise
  const cfg = () => Object.assign({}, CFG0, (M && M.config) || {});
  function ready() {
    if (M) return Promise.resolve(M);
    if (!MP) MP = fetch('articles/vault/manifest.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).then((j) => { M = j && Array.isArray(j.packs) ? j : { packs: [], articles: [], lines: [], config: {} }; return M; }).catch(() => { M = { packs: [], articles: [], lines: [], config: {} }; return M; });
    return MP;
  }
  const artMeta = (id) => ((M && M.articles) || []).find((a) => a.id === id) || null;
  const packOf = (aid) => ((M && M.packs) || []).find((p) => p.articles.indexOf(aid) >= 0) || null;
  const lineName = (id) => { const l = ((M && M.lines) || []).find((x) => x.id === id); return l ? l.name : id; };

  /* ------------------------------------------------------------------ 時間（台北） */
  const nowMs = () => Date.now() + T.off;
  const tpe = (ms) => new Date(ms + 8 * 3600e3).toISOString().slice(0, 10);
  const today = () => T.today || tpe(nowMs());
  const ymOf = (d) => d.slice(0, 7);
  const dim = (ym) => new Date(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7), 0)).getUTCDate();
  const dstr = (ym, i) => ym + '-' + String(i).padStart(2, '0');
  const addDays = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
  const shiftYm = (ym, n) => { const d = new Date(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7) - 1 + n, 1)); return d.toISOString().slice(0, 7); };
  const md = (d) => `${+d.slice(5, 7)} 月 ${+d.slice(8, 10)} 日`;

  /* ------------------------------------------------------------------ 身分與權限 */
  const A = () => window.TwAccount || null;
  const acctOn = () => { const a = A(); return !!(a && a.on && a.on()); };
  const user = () => { const a = A(); return a && a.on && a.on() && a.user ? a.user() : null; };
  const uid = () => { const u = user(); return u && u.email ? String(u.email).toLowerCase() : acctOn() ? 'guest' : 'local'; };
  const loggedIn = () => !!user() || !acctOn();           // 會員系統沒開（本機）視同可用
  const isAdm = () => { const u = user(); return !!(u && (u.admin || u.owner)); };
  const perm = (id) => { const P = window.TwPerm; try { return P && P.can ? P.can(id) : true; } catch (e) { return true; } };
  const permVal = (id, fb) => { const P = window.TwPerm; try { const v = P && P.value ? P.value(id) : fb; return typeof v === 'number' ? v : fb; } catch (e) { return fb; } };

  /* ------------------------------------------------------------------ 儲存層（本機） */
  const KEY = 'tw.ci.v1';
  const blank = () => ({ v: 1, signs: {}, claims: {}, unlock: {}, fresh: [], pts: {}, mk: {}, dayPts: {}, lastAt: 0, lastClick: 0, seen: { say: [], quiz: [] }, wishes: [], badges: [], ticket: {}, seq: 0 });
  let S = null, SU = '';
  function load() {
    const id = uid();
    if (S && SU === id) return S;
    SU = id; S = blank();
    try { const j = JSON.parse(localStorage.getItem(KEY + ':' + id) || 'null'); if (j && j.v === 1) S = Object.assign(blank(), j); } catch (e) { /* 私密視窗：只留在記憶體 */ }
    return S;
  }
  function save() { try { localStorage.setItem(KEY + ':' + SU, JSON.stringify(S)); } catch (e) { /* 存不了就只留記憶體 */ } window.dispatchEvent(new CustomEvent('tw:ci')); }

  const signsIn = (ym) => Object.keys(load().signs).filter((d) => d.slice(0, 7) === ym).sort();
  const total = (ym) => signsIn(ym).length;
  const nodes = () => cfg().nodes;
  const claimed = (ym, i) => !!load().claims[ym + ':' + i];
  const unlockedIds = () => Object.keys(load().unlock);
  /* ★ 法遵：解鎖只看簽到兌換紀錄；不看方案、不看站主身分 */
  const unlocked = (aid) => !!load().unlock[aid];
  const allVault = () => (M && M.articles) || [];

  /* 補簽 */
  const mkUsed = (ym) => load().mk[ym] || 0;
  const mkCap = () => Math.max(0, Math.min(cfg().makeup_max, perm('ci.makeup') ? permVal('ci.makeup', cfg().makeup_max) : 0));
  const mkCost = (ym) => cfg().makeup_cost[Math.min(mkUsed(ym), cfg().makeup_cost.length - 1)];
  const pts = (ym) => load().pts[ym] || 0;
  function mkDays() {   // 可補的日子：本月、今天以前、最近 N 天、沒簽
    const t = today(), ym = ymOf(t), out = [];
    for (let k = 1; k <= cfg().makeup_days; k++) { const d = addDays(t, -k); if (ymOf(d) !== ym) break; if (!load().signs[d]) out.push(d); }
    return out;
  }
  const mkReady = () => mkUsed(ymOf(today())) < mkCap() && pts(ymOf(today())) >= mkCost(ymOf(today())) && mkDays().length > 0;

  /* ------------------------------------------------------------------ 動作 */
  function doSign(d, kind) {
    const s = load(), t = d || today();
    if (s.signs[t]) return { ok: false, error: 'already' };
    s.signs[t] = { k: kind || 'live', at: nowMs() }; save();
    return { ok: true, day: t, total: total(ymOf(t)) };
  }
  function doMakeup(d) {
    const s = load(), t = today(), ym = ymOf(t);
    if (!mkDays().includes(d)) return { ok: false, error: 'range' };
    if (!mkReady()) return { ok: false, error: 'notready' };
    s.pts[ym] = pts(ym) - mkCost(ym); s.mk[ym] = mkUsed(ym) + 1;
    s.signs[d] = { k: 'makeup', at: nowMs() }; save();
    return { ok: true, day: d };
  }
  /* 下一包：教學節點（前兩個）照 技術→籌碼→總經 輪流；產業節點取產業線下一包；已被這個人解鎖過的篇不會再給 */
  function nextPack(idx) {
    const packs = (M && M.packs) || [], c = cfg();
    const free = (p) => p.articles.every((a) => !load().unlock[a]);
    const lines = idx <= 1 ? c.teach_rotation : ['ind'];
    const prior = Object.keys(load().claims).filter((k) => +k.split(':')[1] <= 1 && load().claims[k].packs.length).length;
    for (let r = 0; r < lines.length; r++) {
      const ln = lines[(prior + r) % lines.length];
      const p = packs.filter((x) => x.line === ln && free(x)).sort((a, b) => a.order - b.order)[0];
      if (p) return p;
    }
    return null;
  }
  function doClaim(idx, force) {
    const s = load(), ym = ymOf(today()), n = nodes()[idx];
    if (claimed(ym, idx)) return { ok: false, error: 'claimed' };
    if (!force && total(ym) < n) return { ok: false, error: 'short' };
    const rec = { at: nowMs(), packs: [], articles: [] };
    if (idx === 3) {
      if (!force && (!perm('ci.wish') || wishesIn(ym) >= Math.max(1, permVal('ci.wish', 1)))) return { ok: false, error: 'locked' };
      s.ticket = { ym, at: nowMs(), left: true }; s.badges.push(ym);
    } else {
      const p = nextPack(idx);
      if (!p) return { ok: false, error: 'soldout' };
      rec.packs.push(p.id);
      p.articles.forEach((a) => { s.unlock[a] = { pack: p.id, node: n, ym, at: nowMs() }; rec.articles.push(a); if (s.fresh.indexOf(a) < 0) s.fresh.push(a); });
    }
    s.claims[ym + ':' + idx] = rec; save();
    return { ok: true, rec, idx };
  }
  const wishesIn = (ym) => load().wishes.filter((w) => w.ym === ym).length;

  /* 願望 */
  function evalBatch(w) {
    const st = w.items.map((i) => i.st);
    let r;
    if (st.some((x) => x === 'new')) r = 'pending';
    else if (st.some((x) => x === 'eval' || x === 'done')) r = 'eval';
    else if (st.every((x) => x === 'void')) r = 'void';
    else r = 'granted';
    w.result = r;
    if (r === 'granted') w.granted = true;     // 預覽只模擬：不呼叫任何開通端點
    return r;
  }
  async function sendWish(items, why) {
    const s = load(), ym = ymOf(today());
    s.seq += 1;
    const code = 'W' + today().replace(/-/g, '').slice(2) + String(s.seq).padStart(2, '0') + Math.random().toString(36).slice(2, 5);
    const w = { id: code, ym, at: nowMs(), why: why || '', items: items.map((t, i) => ({ n: i + 1, text: t, st: 'new', reply: '', sent: false })), result: 'pending', granted: false };
    s.wishes.unshift(w); s.ticket = {}; save();
    const a = A();
    for (const it of w.items) {
      if (!a || !a.call || !acctOn()) continue;
      const body = { type: 'wish', cat: 'idea', body: `【願望清單】【簽到願望】【預覽】【簽到願望#${code}-${it.n}】${it.text}${why ? '\n為什麼需要：' + why : ''}`.slice(0, 2000), url: location.href.slice(0, 300) };
      try { const j = await a.call('/v1/feedback', body); it.sent = !!(j && j._s === 200 && j.ok); } catch (e) { it.sent = false; }
    }
    save();
    return w;
  }
  /* 站主在管理區標狀態 → 回流到使用者畫面（站主身分才讀得到清單；其他人用「模擬願望回覆」工具） */
  async function syncWishes() {
    const a = A(); if (!isAdm() || !a || !a.call) return 0;
    const j = await a.call('/v1/admin/feedback/list', {}); if (!j || j._s !== 200) return 0;
    let n = 0;
    (j.feedback || []).forEach((r) => {
      const m = /【簽到願望#(W[\w]+)-(\d+)】/.exec(String(r.body || '')); if (!m) return;
      const w = load().wishes.find((x) => x.id === m[1]); const it = w && w.items.find((x) => x.n === +m[2]);
      const map = { eval: 'eval', no: 'no', done: 'done', void: 'void' };
      if (it && map[r.status] && it.st !== map[r.status]) { it.st = map[r.status]; n++; }
    });
    load().wishes.forEach(evalBatch); save(); return n;
  }

  /* ------------------------------------------------------------------ 比比互動（補簽點數） */
  let FACTS = null, FP = null;
  function loadFacts() { if (FACTS) return Promise.resolve(FACTS); if (!FP) FP = fetch('bibi_facts.json').then((r) => r.json()).then((j) => { FACTS = j; return j; }).catch(() => { FACTS = { facts: ['每天簽到只要十秒，比比會替你記著。'], quiz: [] }; return FACTS; }); return FP; }
  function countPoint() {
    const s = load(), t = today(), ym = ymOf(t), now = nowMs();
    if (now - s.lastClick < CLICK_MS) { s.lastClick = now; return { counted: false, why: 'fast' }; }
    s.lastClick = now;
    if (!loggedIn() || !user() && acctOn()) return { counted: false, why: 'login' };
    if (!perm('ci.makeup') || mkCap() <= 0) return { counted: false, why: 'locked' };
    if (mkUsed(ym) >= mkCap()) return { counted: false, why: 'max' };
    if (!mkDays().length) return { counted: false, why: 'noblank' };
    if ((s.dayPts[t] || 0) >= DAY_CAP) return { counted: false, why: 'day' };
    if (s.lastAt && now - s.lastAt < GAP_MS) return { counted: false, why: 'gap' };
    s.pts[ym] = pts(ym) + 1; s.dayPts[t] = (s.dayPts[t] || 0) + 1; s.lastAt = now; save();
    return { counted: true, pts: pts(ym), need: mkCost(ym) };
  }
  const WHY = { fast: '點太快了，慢慢來～', login: '登入後互動才會累積補簽進度', locked: '補簽功能目前未開通', max: '這個月的補簽次數用完了', noblank: '最近 7 天沒有漏簽的日子，不用補簽喔', day: '今天玩夠啦，明天再來～', gap: '比比需要休息一下，隔 20 秒再來～' };

  function bibiCard(kind) {
    close(true);
    ready().then(() => loadFacts()).then((F) => {
      const s = load(), ym = ymOf(today());
      let box = $('#ciBibi'); if (box) box.remove();
      box = document.createElement('div'); box.id = 'ciBibi'; box.className = 'ci-bibi'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', kind === 'say' ? '聽比比說' : '比比考考你');
      document.body.appendChild(box);
      const prog = () => { const need = mkCost(ym); return `補簽進度 <b>${Math.min(pts(ym), need)}／${need}</b>・本月已補 ${mkUsed(ym)}／${mkCap()} 次`; };
      let at = 0, done = false;
      if (kind === 'say') {
        const pool = F.facts.map((_, i) => i).filter((i) => s.seen.say.indexOf(i) < 0);
        const i = (pool.length ? pool : F.facts.map((_, k) => k))[Math.floor(Math.random() * (pool.length || F.facts.length))];
        if (!pool.length) s.seen.say = [];
        s.seen.say.push(i); save();
        box.innerHTML = `<h4>聽比比說</h4><p class="ci-bq">${esc(F.facts[i])}</p><div class="ci-bp" id="ciBP"></div><div class="ci-ba"><button type="button" class="ci-btn" id="ciBOk" disabled>知道了</button><button type="button" class="ci-btn ghost" id="ciBX">關閉</button></div>`;
        setTimeout(() => { const b = $('#ciBOk'); if (b) b.disabled = false; }, 2000);   // 看卡片至少 2 秒才可按，避免秒按
        $('#ciBOk').onclick = () => { if (done) return; done = true; const r = countPoint(); $('#ciBOk').disabled = true; $('#ciBP').innerHTML = r.counted ? '+1 互動！' + prog() + (mkReady() ? '<br><b>可以補簽了</b>，到簽到月曆按「開始補簽」' : '') : esc(WHY[r.why] || ''); at = 1; };
      } else {
        const qs = F.quiz.length ? F.quiz : [{ q: '一張股票通常是幾股？', opts: ['1000', '100', '10000'], a: 0, say: '一張 1000 股' }];
        const pool = qs.map((_, k) => k).filter((k) => s.seen.quiz.indexOf(k) < 0);
        const qi = (pool.length ? pool : qs.map((_, k) => k))[Math.floor(Math.random() * (pool.length || qs.length))];
        if (!pool.length) s.seen.quiz = []; s.seen.quiz.push(qi); save();
        const q = qs[qi], order = q.opts.map((o, k) => ({ o, k })).sort(() => Math.random() - 0.5);   // 選項順序隨機
        box.innerHTML = `<h4>比比考考你</h4><p class="ci-bq">${esc(q.q)}</p><div class="ci-bo">${order.map((x) => `<button type="button" class="ci-opt" data-k="${x.k}" disabled>${esc(x.o)}</button>`).join('')}</div><div class="ci-bp" id="ciBP"></div><div class="ci-ba"><button type="button" class="ci-btn ghost" id="ciBX">關閉</button></div>`;
        setTimeout(() => $$('.ci-opt', box).forEach((b) => { b.disabled = false; }), 3000);   // 出題 3 秒後才能作答
        $$('.ci-opt', box).forEach((b) => { b.onclick = () => {
          if (done) return; done = true;
          const right = +b.dataset.k === q.a; $$('.ci-opt', box).forEach((x) => { x.disabled = true; x.classList.toggle('right', +x.dataset.k === q.a); });
          b.classList.add(right ? 'okk' : 'bad');
          const r = countPoint();
          $('#ciBP').innerHTML = `${right ? '答對了！' : '沒關係，我們一起看：'}${esc(q.say)}<br>` + (r.counted ? '+1 互動！' + prog() + (mkReady() ? '<br><b>可以補簽了</b>，到簽到月曆按「開始補簽」' : '') : esc(WHY[r.why] || ''));
        }; });
      }
      $('#ciBX').onclick = () => { box.remove(); paintCard(); };
      void at;
      window.dispatchEvent(new CustomEvent('tw:ci'));
    });
  }

  /* ------------------------------------------------------------------ 樣式 */
  function css() {
    if (document.getElementById('ciCss')) return;
    const s = document.createElement('style'); s.id = 'ciCss';
    s.textContent = `
.evbtn#ciBtn{position:relative;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;padding:0}
.evbtn#ciBtn svg{width:18px;height:18px}
.evbtn#ciBtn i{position:absolute;right:3px;top:3px;width:8px;height:8px;border-radius:50%;background:var(--amber,#e0a21b)}
.evbtn#ciBtn i[hidden]{display:none}
@media (max-width:820px){.evbtn#ciBtn{display:none}}
.ciov{position:fixed;inset:0;z-index:1400;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:12px}
.ciov[hidden]{display:none}
.cidlg{width:min(720px,100%);max-height:min(640px,90vh);overflow:auto;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:12px;box-shadow:0 24px 60px -20px rgba(0,0,0,.6);padding:14px 16px 12px;box-sizing:border-box;font-size:14px}
.ci-h{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.ci-h h2{margin:0;font-size:17px}
.ci-q{width:22px;height:22px;border-radius:50%;border:1px solid var(--line);background:var(--panel-2);color:var(--ink-2);font-size:12px;cursor:pointer;padding:0}
.ci-x{margin-left:auto;width:32px;height:32px;border-radius:8px;border:1px solid var(--line);background:var(--panel-2);color:var(--ink);cursor:pointer;font-size:16px}
.ci-help{background:var(--panel-2);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:0 0 8px;font-size:13px;line-height:1.6;color:var(--ink-2)}
.ci-help ul{margin:4px 0 0;padding-left:18px}
.ci-body{display:grid;grid-template-columns:1fr 1fr;grid-template-areas:"cal top" "cal rest";grid-template-rows:auto 1fr;gap:10px 16px;align-items:start}
.ci-calw{grid-area:cal}.ci-top{grid-area:top}.ci-rest{grid-area:rest}
.ci-mnav{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:6px;font-weight:700}
.ci-mnav button{width:32px;height:32px;border-radius:8px;border:1px solid var(--line);background:var(--panel-2);color:var(--ink);cursor:pointer;font-size:16px}
.ci-mnav button:disabled{opacity:.35;cursor:default}
.ci-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
.ci-wk{text-align:center;font-size:12px;color:var(--ink-3);padding:2px 0}
.ci-c{position:relative;height:40px;border-radius:8px;border:1px solid transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:13px;color:var(--ink-3);background:transparent;padding:0;font-family:inherit}
.ci-c.out{visibility:hidden}
.ci-c.fu{opacity:.4}
.ci-c.bl{color:var(--ink-2)}
.ci-c.sg{background:color-mix(in srgb,var(--accent,var(--cyan)) 22%,var(--panel));color:var(--ink);border-color:color-mix(in srgb,var(--accent,var(--cyan)) 40%,transparent)}
.ci-c.mk{border:1.5px dashed var(--accent,var(--cyan))}
.ci-c.mk b.tg{position:absolute;left:2px;top:1px;font-size:11px;line-height:12px;padding:0 3px;border-radius:3px;background:var(--accent,var(--cyan));color:var(--ontop,#04121a);font-weight:700}
.ci-c.td{border:2px solid var(--accent,var(--cyan));color:var(--ink)}
.ci-c.td.go{cursor:pointer}
.ci-c.mkok{cursor:pointer;border:1.5px dashed var(--amber,#e0a21b);color:var(--ink)}
.ci-c svg.ck{position:absolute;right:2px;bottom:2px;width:13px;height:13px;color:var(--accent,var(--cyan))}
.ci-c small{font-size:11px;line-height:12px;color:var(--accent,var(--cyan))}
.ci-c .nb{position:absolute;right:2px;top:1px;font-size:11px;line-height:13px;min-width:13px;text-align:center;border-radius:7px;background:var(--amber,#e0a21b);color:#1a1200;font-weight:700;padding:0 2px}
.ci-c.cg-we:not(.sg):not(.td){background:color-mix(in srgb,var(--ink) 10%,var(--panel))}
.ci-c .cg-hl{font-size:11px;line-height:11px;position:absolute;bottom:1px;left:1px;right:1px;text-align:center}
.ci-sum{display:flex;align-items:center;gap:10px;justify-content:space-between;margin-bottom:8px}
.ci-sum b.n{font-size:20px}
.ci-btn{height:36px;padding:0 14px;border-radius:8px;border:1px solid var(--accent,var(--cyan));background:var(--accent,var(--cyan));color:var(--ontop,#04121a);font-weight:700;font-size:14px;cursor:pointer;font-family:inherit}
.ci-btn.ghost{background:var(--panel-2);color:var(--ink);border-color:var(--line);font-weight:500}
.ci-btn:disabled{opacity:.45;cursor:default}
.ci-btn.sm{height:30px;padding:0 10px;font-size:13px}
.ci-btn.lock{background:var(--panel-2);color:var(--ink-2);border-color:var(--line)}
.ci-pg{position:relative;display:flex;justify-content:space-between;margin:8px 4px 4px;padding-top:2px}
.ci-pg:before{content:"";position:absolute;left:8px;right:8px;top:9px;height:3px;background:var(--line);border-radius:2px}
.ci-pg .fill{position:absolute;left:8px;top:9px;height:3px;background:var(--accent,var(--cyan));border-radius:2px}
.ci-pg .nd{position:relative;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:12px;color:var(--ink-3);width:40px}
.ci-pg .nd i{width:16px;height:16px;border-radius:50%;background:var(--panel);border:2px solid var(--line);box-sizing:border-box}
.ci-pg .nd.on i{background:var(--accent,var(--cyan));border-color:var(--accent,var(--cyan))}
.ci-pg .nd.on{color:var(--ink)}
.ci-nl{list-style:none;margin:6px 0 0;padding:0;border:1px solid var(--line);border-radius:8px}
.ci-nl li{display:flex;align-items:center;gap:8px;padding:6px 10px;border-top:1px solid var(--line);min-height:40px;box-sizing:border-box}
.ci-nl li:first-child{border-top:0}
.ci-nl li .t{flex:1;min-width:0}
.ci-nl li .t small{display:block;color:var(--ink-3);font-size:12px}
.ci-nl .st{font-size:12px;color:var(--ink-3)}
.ci-mkr{display:flex;align-items:center;gap:8px;margin-top:8px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;justify-content:space-between}
.ci-mkr .ring{display:inline-block;width:14px;height:14px;border-radius:50%;vertical-align:-2px;margin-right:4px;background:conic-gradient(var(--accent,var(--cyan)) calc(var(--p,0)*1%),var(--line) 0)}
.ci-foot{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-top:10px;padding-top:8px;border-top:1px solid var(--line);font-size:13px}
.ci-foot a,.ci-foot button.lk{color:var(--cyan);background:none;border:0;cursor:pointer;font-size:13px;padding:6px 0;font-family:inherit}
.ci-adm{margin-top:8px;border:1px dashed var(--amber,#e0a21b);border-radius:8px;padding:6px 10px;font-size:13px}
.ci-adm summary{cursor:pointer;font-weight:700;color:var(--amber,#e0a21b)}
.ci-adm .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0}
.ci-adm input,.ci-adm select{height:32px;border-radius:6px;border:1px solid var(--line);background:var(--panel-2);color:var(--ink);padding:0 6px;font-size:13px;font-family:inherit;max-width:100%}
.ci-adm input[type=number]{width:70px}
.ci-adm .note{font-size:12px;color:var(--ink-3)}
.ci-pane h3{margin:2px 0 6px;font-size:15px}
.ci-pane p{margin:4px 0;line-height:1.6}
.ci-warn{padding:8px 10px;border-radius:8px;background:color-mix(in srgb,var(--amber,#e0a21b) 16%,var(--panel));border:1px solid color-mix(in srgb,var(--amber,#e0a21b) 50%,transparent);margin:6px 0;font-weight:600}
.ci-list{margin:6px 0;padding:0;list-style:none}
.ci-list li{padding:6px 10px;border:1px solid var(--line);border-radius:8px;margin:4px 0}
.ci-wr{display:flex;gap:6px;margin:4px 0}
.ci-wr input,.ci-wf textarea{flex:1;min-width:0;height:36px;border-radius:8px;border:1px solid var(--line);background:var(--panel-2);color:var(--ink);padding:0 8px;font-size:14px;font-family:inherit;box-sizing:border-box}
.ci-wf textarea{width:100%;height:60px;padding:6px 8px;resize:vertical}
.ci-msg{min-height:20px;font-size:13px;color:var(--ink-2);margin-top:4px}
.ci-msg.bad{color:var(--amber,#e0a21b)}
.ci-badge{display:inline-block;padding:0 6px;border-radius:8px;font-size:12px;background:var(--panel-2);border:1px solid var(--line)}
.ci-badge.eval{border-color:var(--cyan);color:var(--cyan)}
.ci-badge.grant{border-color:var(--amber,#e0a21b);color:var(--amber,#e0a21b)}
.ci-toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);z-index:1500;background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:8px 14px;box-shadow:0 10px 30px -10px rgba(0,0,0,.5);font-size:14px;max-width:90vw}
.ci-bibi{position:fixed;right:20px;bottom:84px;z-index:1450;width:min(320px,calc(100vw - 24px));background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:12px 14px;box-shadow:0 16px 40px -14px rgba(0,0,0,.6);box-sizing:border-box}
.ci-bibi h4{margin:0 0 6px;font-size:14px;color:var(--cyan)}
.ci-bq{margin:4px 0 8px;line-height:1.6;font-size:14px}
.ci-bo{display:grid;gap:6px}
.ci-opt{min-height:40px;border-radius:8px;border:1px solid var(--line);background:var(--panel-2);color:var(--ink);cursor:pointer;font-size:14px;text-align:left;padding:4px 10px;font-family:inherit}
.ci-opt:disabled{opacity:.6;cursor:default}
.ci-opt.right{border-color:var(--accent,var(--cyan));background:color-mix(in srgb,var(--accent,var(--cyan)) 18%,var(--panel))}
.ci-opt.bad{border-color:var(--amber,#e0a21b)}
.ci-bp{min-height:20px;font-size:13px;color:var(--ink-2);margin:6px 0}
.ci-ba{display:flex;gap:8px;justify-content:flex-end}
/* 概覽卡 */
.osc.ci .ci-n{display:flex;flex-direction:column;gap:4px;flex:1 1 auto;min-width:0}
.osc.ci .ci-big{font-size:20px;font-weight:700;line-height:1.1}
.osc.ci .ci-big small{font-size:12px;font-weight:400;color:var(--ink-3);margin-left:4px}
.osc.ci .ci-bar{height:5px;border-radius:3px;background:var(--line);overflow:hidden}
.osc.ci .ci-bar i{display:block;height:100%;background:var(--accent,var(--cyan))}
.osc.ci .ci-sub{font-size:12px;color:var(--ink-2)}
/* 寶箱分頁 */
.ci-vh{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:2px 0 10px}
.ci-vh .sum{font-weight:700}
.ci-vseg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.ci-vseg button{height:32px;padding:0 12px;border:0;background:var(--panel-2);color:var(--ink-2);cursor:pointer;font-family:inherit;font-size:13px}
.ci-vseg button.on{background:var(--accent,var(--cyan));color:var(--ontop,#04121a);font-weight:700}
.ci-vl{border:1px solid var(--line);border-radius:10px;margin:8px 0;padding:0 10px}
.ci-vl>summary{cursor:pointer;min-height:40px;display:flex;align-items:center;gap:8px;font-weight:700}
.ci-vl>summary small{color:var(--ink-3);font-weight:400}
.ci-vl .artgrid{padding-bottom:10px}
.artc.lkd.vlk{cursor:default}
.artc .newb{position:absolute;right:12px;top:-9px;z-index:2;font-size:11px;padding:0 6px;border-radius:8px;background:var(--amber,#e0a21b);color:#1a1200;font-weight:700}
.artc.vnew{box-shadow:0 0 0 2px var(--amber,#e0a21b)}
.artlocked.cilk .ci-lkbox{padding:16px;border:1px dashed var(--line);border-radius:10px;margin:10px 0;line-height:1.7}
@media (prefers-reduced-motion: reduce){.ci-c,.ciov{transition:none}}
@media (max-width:640px){
  .ciov{align-items:flex-end;padding:0}
  .cidlg{width:100%;max-height:92vh;border-radius:14px 14px 0 0;padding:6px 12px 10px}
  .cidlg:before{content:"";display:block;width:40px;height:4px;border-radius:2px;background:var(--line);margin:0 auto 6px}
  .ci-body{grid-template-columns:1fr;grid-template-areas:"top" "cal" "rest";gap:6px}
  .ci-c{height:36px}
  .ci-c .cg-hl{display:none}
  .ci-sum{margin-bottom:2px}.ci-sum b.n{font-size:17px}
  .ci-btn{height:40px}
  .ci-pg{margin:2px 4px}
  .ci-nl-d>summary{cursor:pointer;min-height:36px;display:flex;align-items:center;font-size:13px}
  .ci-foot{margin-top:6px;padding-top:4px}
  .ci-bibi{right:8px;bottom:78px}
  .ci-adm input[type=date]{max-width:150px}
}
@media (min-width:641px){.ci-nl-d>summary{display:none}}`;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 面板 */
  const V = { open: false, ym: '', pane: 'main', mkMode: false, help: false, adm: false, claim: null, msg: '', mkPick: '', nlOpen: false };
  const ICON_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M9 15l2 2 4-4"/></svg>';
  const CK = '<svg class="ck" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.4l3.1 3.1L13 4.6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  let ov = null;

  function toast(t) {
    let e = $('#ciToast'); if (e) e.remove();
    e = document.createElement('div'); e.id = 'ciToast'; e.className = 'ci-toast'; e.setAttribute('role', 'status'); e.textContent = t; document.body.appendChild(e);
    setTimeout(() => { if (e.parentNode) e.remove(); }, 3500);
  }
  const WIDE = () => { try { return window.matchMedia('(min-width:641px)').matches; } catch (e) { return true; } };   // 桌機：節點清單一律攤開（沒有可收的摺疊）；手機預設收起
  const vaultTotal = () => allVault().length;
  const vaultGot = () => allVault().filter((a) => unlocked(a.id)).length;
  function nextNode(ym) { const n = nodes().find((x, i) => !claimed(ym, i) && x > total(ym)); return n || null; }

  function calHTML() {
    const t = today(), ym = V.ym, n = dim(ym), first = new Date(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7) - 1, 1)).getUTCDay();
    const signed = signsIn(ym), cg = window.CalGrid;
    const okMk = V.mkMode ? mkDays() : [];
    let h = WK.map((w) => `<div class="ci-wk" aria-hidden="true">${w}</div>`).join('');
    for (let i = 0; i < first; i++) h += '<div class="ci-c out"></div>';
    for (let d = 1; d <= n; d++) {
      const k = dstr(ym, d), sg = load().signs[k], isT = k === t, fu = k > t;
      const idx = signed.indexOf(k) + 1, nb = sg && nodes().indexOf(idx) >= 0 ? idx : 0;
      const cl = ['ci-c'];
      if (cg && cg.cls) cl.push(cg.cls(k).trim());
      let aria = `${md(k)}`, tag = 'div', go = '';
      if (sg) { cl.push('sg'); if (sg.k === 'makeup') { cl.push('mk'); aria += ' 已簽到（補簽）'; } else aria += ' 已簽到'; if (nb) aria += `，達成累積 ${nb} 天`; }
      else if (isT) { aria += '，今天，尚未簽到，按下簽到'; }
      else if (fu) { cl.push('fu'); aria += ' 尚未到'; }
      else { cl.push('bl'); aria += ' 未簽到'; }
      if (isT) { cl.push('td'); if (!sg) { cl.push('go'); tag = 'button'; go = ' data-sign="1"'; } }
      if (okMk.indexOf(k) >= 0) { cl.push('mkok'); tag = 'button'; go = ` data-mk="${k}"`; aria += '，可補簽'; }
      const tagTxt = cg && cg.tag && !sg ? '' : '';
      h += `<${tag} class="${cl.join(' ')}" data-d="${k}"${go} aria-label="${esc(aria)}"${tag === 'button' ? ' type="button"' : ''}>${sg && sg.k === 'makeup' ? '<b class="tg">補</b>' : ''}<span>${d}</span>${isT && !sg ? '<small>簽</small>' : ''}${nb ? `<span class="nb" title="達成累積 ${nb} 天">${nb}</span>` : ''}${sg ? CK : ''}${tagTxt}</${tag}>`;
    }
    return `<div class="ci-grid" role="grid" aria-label="${ym} 簽到月曆">${h}</div>`;
  }

  function mainHTML() {
    load();
    const t = today(), tm = ymOf(t), ym = V.ym, cur = ym === tm, tot = total(ym), ns = nodes();
    const signedToday = !!load().signs[t];
    const canS = perm('ci.sign');
    const pct = Math.min(100, Math.round(100 * tot / ns[ns.length - 1]));
    const u = user();
    const pg = `<div class="ci-pg" aria-label="累積進度"><span class="fill" style="width:calc((100% - 16px)*${pct / 100})"></span>${ns.map((n, i) => `<span class="nd${tot >= n ? ' on' : ''}"><i></i>${n} 天</span>`).join('')}</div>`;
    const rows = ns.map((n, i) => {
      const cl = cur && claimed(ym, i), reach = tot >= n;
      let act;
      if (!cur) act = cl ? '<span class="st">已兌換</span>' : '<span class="st">未兌換</span>';
      else if (cl) act = '<span class="st">已兌換</span>';
      else if (!reach) act = `<span class="st">還差 ${n - tot} 天</span>`;
      else if (i === 3 && (!perm('ci.wish') || wishesIn(tm) >= Math.max(1, permVal('ci.wish', 1)))) act = '<button type="button" class="ci-btn sm lock" data-lockwish="1" disabled title="此功能需開通">🔒 需開通</button>';
      else act = `<button type="button" class="ci-btn sm" data-claim="${i}">兌換</button>`;
      const desc = i === 3 ? '許願券（1～5 個願望）＋月度徽章' : i === 2 ? '產業深度包・2 篇' : '教學包・2 篇';
      return `<li data-node="${i}"><span class="t"><b>${n} 天</b> ${esc(NODE_NAMES[i])}<small>${esc(desc)}</small></span>${act}</li>`;
    }).join('');
    const used = mkUsed(tm), cap = mkCap(), need = mkCost(tm), pp = pts(tm);
    const mk = !cur ? '' : `<div class="ci-mkr" id="ciMk"><span><i class="ring" style="--p:${Math.min(100, Math.round(100 * pp / need))}"></i>補簽：互動 <b>${Math.min(pp, need)}／${need}</b>・本月已補 ${used}／${cap} 次</span>`
      + (V.mkMode ? '<button type="button" class="ci-btn sm ghost" data-mkx="1">取消補簽</button>' : mkReady() ? '<button type="button" class="ci-btn sm" data-mkgo="1">開始補簽</button>' : '<button type="button" class="ci-btn sm ghost" data-findbibi="1">找比比</button>') + '</div>';
    const mkNote = V.mkMode ? `<div class="ci-warn" role="status">點一個虛線的空白日補簽（最近 ${cfg().makeup_days} 天內）</div>` : '';
    const adm = isAdm() ? admHTML() : '';
    const sg = cur ? (signedToday ? '<button type="button" class="ci-btn" disabled>今天已簽到</button>' : `<button type="button" class="ci-btn" id="ciSign" data-sign="1"${canS ? '' : ' disabled'}>${canS ? '簽到今天' : '🔒 需開通'}</button>`) : '';
    const help = V.help ? `<div class="ci-help" id="ciHelp"><b>怎麼用</b><ul><li>每天按一次「簽到今天」，月曆會留下勾；沒簽的日子保持空白。每月 1 日累積歸零，已拿到的文章永久保留。</li><li>累積滿 ${ns.join('／')} 天各可兌換一次：前兩個是教學包、第三個是產業深度包、最後是許願券。兌換後到精選文章的「比比寶箱」分頁閱讀。</li><li>漏簽可以跟比比互動換補簽（見下方補簽列），每月最多 ${cfg().makeup_max} 次，只能補最近 ${cfg().makeup_days} 天。</li><li>寶箱文章只能靠簽到解鎖，付費方案不能直接打開。</li><li>預覽版：資料只存在這個瀏覽器；許願會真的送給站主，Plus 3 天只是畫面模擬。</li></ul></div>` : '';
    return `<div class="ci-h"><h2 id="ciTtl">每日簽到</h2><button type="button" class="ci-q" id="ciQ" aria-label="每日簽到怎麼用" aria-expanded="${V.help}">?</button><button type="button" class="ci-x" id="ciX" aria-label="關閉">✕</button></div>${help}
<div class="ci-body">
 <div class="ci-top"><div class="ci-sum"><span>${cur ? '本月' : ym.replace('-', ' 年 ') + ' 月'}累積 <b class="n" id="ciTot">${tot}</b> 天${u || !acctOn() ? '' : '<small class="st"> （登入後才能簽到）</small>'}</span>${sg}</div>${pg}${mkNote}</div>
 <div class="ci-calw"><div class="ci-mnav"><button type="button" id="ciPrev" aria-label="上個月">‹</button><span id="ciMon">${ym.slice(0, 4)} 年 ${+ym.slice(5, 7)} 月</span><button type="button" id="ciNext" aria-label="下個月"${cur ? ' disabled' : ''}>›</button></div>${calHTML()}</div>
 <div class="ci-rest"><details class="ci-nl-d"${V.nlOpen || WIDE() ? ' open' : ''} id="ciNlD"><summary>節點與獎勵</summary><ul class="ci-nl" id="ciNodes">${rows}</ul></details>${mk}</div>
</div>
<div class="ci-foot"><a href="#articles/vault" id="ciVault">我的寶箱 ${vaultGot()}／${vaultTotal()} 篇 ›</a><button type="button" class="lk" id="ciWishes">我的願望 ${load().wishes.length} ›</button>${nextNode(tm) && cur ? `<span class="st">下一個節點：滿 ${nextNode(tm)} 天</span>` : ''}</div>${adm}`;
  }

  /* 站主測試工具：只給 admin／owner；一般會員的 DOM 裡完全不輸出 */
  function admHTML() {
    const ws = load().wishes;
    return `<details class="ci-adm" id="ciAdm"${V.adm ? ' open' : ''}><summary>站主測試（只有站主看得到）</summary>
<div class="row"><button type="button" class="ci-btn sm" data-t="signtoday">一鍵簽到今天</button><button type="button" class="ci-btn sm ghost" data-t="clear">清空本月</button><button type="button" class="ci-btn sm ghost" data-t="resetunlock">清空解鎖紀錄</button></div>
<div class="row"><input type="date" id="admDay" aria-label="補簽日期" value="${today()}"><button type="button" class="ci-btn sm ghost" data-t="signday">指定日期補簽</button></div>
<div class="row"><input type="number" id="admN" min="0" max="31" value="3" aria-label="填到第 N 天"><button type="button" class="ci-btn sm ghost" data-t="fill">填到第 N 天</button></div>
<div class="row"><select id="admNode" aria-label="節點">${nodes().map((n, i) => `<option value="${i}">${n} 天 ${esc(NODE_NAMES[i])}</option>`).join('')}</select><button type="button" class="ci-btn sm ghost" data-t="claim">直接兌換</button></div>
<div class="row"><input type="date" id="admToday" aria-label="模擬今天" value="${today()}"><button type="button" class="ci-btn sm ghost" data-t="settoday">模擬今天日期</button><button type="button" class="ci-btn sm ghost" data-t="realtoday">恢復真實日期</button></div>
<div class="row"><button type="button" class="ci-btn sm ghost" data-t="ptsfull">補簽互動加滿</button><button type="button" class="ci-btn sm ghost" data-t="ptsplus">互動 +1</button><button type="button" class="ci-btn sm ghost" data-t="ptsclear">互動歸零</button></div>
<div class="row"><select id="admBatch" aria-label="願望批次">${ws.length ? ws.map((w) => `<option value="${esc(w.id)}">${esc(w.id)}（${w.items.length} 項）</option>`).join('') : '<option value="">（還沒有願望）</option>'}</select>
<select id="admSt" aria-label="願望結果"><option value="no">做不到</option><option value="eval">會做</option><option value="void">不算</option></select><button type="button" class="ci-btn sm ghost" data-t="wishreply">模擬願望被回覆</button><button type="button" class="ci-btn sm ghost" data-t="wishsync">從意見回饋同步（真實）</button></div>
<div class="note" id="admMsg" role="status">測試寫入只在這個瀏覽器；Plus 3 天只在畫面模擬。</div></details>`;
  }

  function wishFormHTML() {
    const mx = cfg().wish_max;
    return `<div class="ci-h"><h2>許願</h2><button type="button" class="ci-x" id="ciX" aria-label="關閉">✕</button></div>
<div class="ci-pane ci-wf"><div class="ci-warn">願望不一定做得到。若這批願望站主評估後全部做不到，會送你 Plus 3 天（預覽版只在畫面模擬）。</div>
<p>可以寫 1～${mx} 個想要的功能，每個至少 6 個字：</p><div id="ciWrows">${[1, 2, 3].map((i) => `<div class="ci-wr"><input type="text" maxlength="200" data-w="${i}" aria-label="願望 ${i}" placeholder="願望 ${i}"></div>`).join('')}</div>
<button type="button" class="ci-btn sm ghost" id="ciWadd">＋再加一個</button>
<p><label for="ciWhy">為什麼需要（選填，整批共用）</label></p><textarea id="ciWhy" maxlength="500"></textarea>
<div class="ci-msg" id="ciWmsg" role="status"></div><div class="ci-ba" style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px"><button type="button" class="ci-btn ghost" id="ciWback">先不許願</button><button type="button" class="ci-btn" id="ciWsend">送出願望</button></div></div>`;
  }
  const ST = { new: '等待評估', eval: '會做', done: '已做', no: '做不到', void: '不算' };
  function wishListHTML() {
    const ws = load().wishes;
    const res = (w) => w.result === 'granted' ? '<span class="ci-badge grant">這批願望站主評估後都無法實作，已送你 Plus 3 天（預覽模擬，未真的開通）</span>'
      : w.result === 'eval' ? `<span class="ci-badge eval">站主打算做：${esc(w.items.filter((i) => i.st === 'eval' || i.st === 'done').map((i) => i.text).join('、'))}</span>`
      : w.result === 'void' ? '<span class="ci-badge">這批願望不在受理範圍</span>' : '<span class="ci-badge">評估中</span>';
    return `<div class="ci-h"><h2>我的願望</h2><button type="button" class="ci-x" id="ciX" aria-label="關閉">✕</button></div><div class="ci-pane">
${ws.length ? ws.map((w) => `<div class="ci-list" data-batch="${esc(w.id)}" data-result="${w.result}"><li style="list-style:none"><b>${esc(w.id)}</b>・${w.items.length} 個願望 <span class="st">${md(tpe(w.at))}</span><div class="ci-res">${res(w)}</div><ul style="margin:6px 0 0;padding-left:18px">${w.items.map((i) => `<li>${esc(i.text)} <span class="ci-badge" data-st="${i.st}">${ST[i.st]}</span>${i.reply ? `<small>（站主：${esc(i.reply)}）</small>` : ''}${i.sent ? '' : ' <small class="st">（未送達站主：本機測試或未登入）</small>'}</li>`).join('')}</ul></li></div>`).join('') : '<p>還沒有許過願。簽到滿 20 天可以兌換許願券。</p>'}
<button type="button" class="ci-btn ghost" id="ciBack">回月曆</button></div>`;
  }
  function claimDoneHTML() {
    const r = V.claim; if (!r) return '';
    const arts = r.rec.articles.map((a) => artMeta(a)).filter(Boolean);
    return `<div class="ci-h"><h2>兌換完成</h2><button type="button" class="ci-x" id="ciX" aria-label="關閉">✕</button></div><div class="ci-pane" id="ciDone">
<p>已解鎖 ${arts.length} 篇：${arts.map((a) => `〈${esc(a.title)}〉`).join('')}</p>
<p>到 <b>精選文章 →『比比寶箱』</b>分頁看。</p>
<div style="display:flex;gap:8px;margin-top:10px"><a class="ci-btn" id="ciGo" href="#articles/vault" style="text-decoration:none;display:inline-flex;align-items:center">去讀（比比寶箱）</a><button type="button" class="ci-btn ghost" id="ciStay">留在這裡</button></div></div>`;
  }

  function paint() {
    if (!ov) return;
    const box = $('.cidlg', ov);
    const st = { y: box.scrollTop };
    box.innerHTML = V.pane === 'wish' ? wishFormHTML() : V.pane === 'list' ? wishListHTML() : V.pane === 'done' ? claimDoneHTML() : mainHTML();
    box.scrollTop = st.y;
    bind(box);
    paintCard(); paintDot();
  }
  function admMsg(t) { const e = $('#admMsg'); if (e) e.textContent = t; }

  function bind(box) {
    const on = (sel, fn) => $$(sel, box).forEach((e) => { e.onclick = fn; });
    on('#ciX', () => close());
    on('#ciQ', () => { V.help = !V.help; paint(); });
    on('#ciPrev', () => { V.ym = shiftYm(V.ym, -1); V.mkMode = false; paint(); });
    on('#ciNext', () => { if (V.ym < ymOf(today())) { V.ym = shiftYm(V.ym, 1); V.mkMode = false; paint(); } });
    on('[data-sign]', () => sign());
    on('[data-claim]', (e) => claim(+e.currentTarget.dataset.claim));
    on('[data-mkgo]', () => { V.mkMode = true; paint(); });
    on('[data-mkx]', () => { V.mkMode = false; paint(); });
    on('[data-mk]', (e) => {
      const d = e.currentTarget.dataset.mk;
      if (V.mkPick !== d) { V.mkPick = d; toast(`再點一次確認補簽 ${md(d)}`); return; }
      const r = doMakeup(d); V.mkPick = '';
      if (r.ok) { V.mkMode = false; toast(`已補簽 ${md(d)}`); paint(); } else toast('補簽失敗：' + (r.error === 'notready' ? '互動次數還不夠' : '這天不能補簽'));
    });
    on('[data-findbibi]', () => { close(); toast('點右下角的比比，選「聽比比說」或「比比考考你」，每次互動都會累積補簽進度'); });
    on('#ciVault', () => close(true));
    on('#ciWishes', () => { V.pane = 'list'; paint(); });
    on('#ciBack', () => { V.pane = 'main'; paint(); });
    on('#ciStay', () => { V.pane = 'main'; paint(); });
    on('#ciGo', () => close(true));
    const nd = $('#ciNlD', box); if (nd) nd.ontoggle = () => { V.nlOpen = nd.open; };
    const ad = $('#ciAdm', box); if (ad) ad.ontoggle = () => { V.adm = ad.open; };
    on('[data-t]', (e) => admTool(e.currentTarget.dataset.t));
    // 許願表單
    on('#ciWadd', () => { const rows = $('#ciWrows', box); const n = $$('.ci-wr', rows).length; if (n >= cfg().wish_max) return; const d = document.createElement('div'); d.className = 'ci-wr'; d.innerHTML = `<input type="text" maxlength="200" data-w="${n + 1}" aria-label="願望 ${n + 1}" placeholder="願望 ${n + 1}">`; rows.appendChild(d); if (n + 1 >= cfg().wish_max) $('#ciWadd', box).disabled = true; });
    on('#ciWback', () => { V.pane = 'main'; paint(); });
    on('#ciWsend', async () => {
      const m = $('#ciWmsg', box), vals = $$('#ciWrows input', box).map((i) => i.value.trim()).filter(Boolean);
      m.className = 'ci-msg bad';
      if (!vals.length) { m.textContent = '至少寫一個願望'; return; }
      if (vals.some((v) => v.length < 6)) { m.textContent = '每個願望至少 6 個字'; return; }
      if (new Set(vals).size !== vals.length) { m.textContent = '同一批不能有重複的願望'; return; }
      if (load().wishes.some((w) => w.items.some((i) => vals.indexOf(i.text) >= 0))) { m.textContent = '有願望跟你之前送過的一模一樣'; return; }
      $('#ciWsend', box).disabled = true; m.className = 'ci-msg'; m.textContent = '送出中…';
      const w = await sendWish(vals, ($('#ciWhy', box) || {}).value);
      V.pane = 'list'; paint(); toast(`已送出 ${w.items.length} 個願望，站主看過後會在這裡告訴你結果`);
    });
  }

  function sign() {
    if (!perm('ci.sign')) { toast('此功能需開通'); return; }
    if (!loggedIn()) { toast('請先登入再簽到'); try { A().login(); } catch (e) { /* 略 */ } return; }
    const b = $('#ciSign'); if (b) { b.disabled = true; b.textContent = '簽到中…'; }
    const r = doSign();
    V.ym = ymOf(today());
    if (r.ok) { toast(`今天簽到完成，本月累積 ${r.total} 天`); } else toast('今天已經簽到過了');
    paint();
  }
  function claim(i) {
    const r = doClaim(i);
    if (!r.ok) { toast(r.error === 'soldout' ? '寶箱補貨中，進度會保留' : r.error === 'locked' ? '此功能需開通' : r.error === 'short' ? '累積天數還不夠' : '已經兌換過了'); paint(); return; }
    if (i === 3) { V.pane = 'wish'; paint(); return; }
    V.claim = r; V.pane = 'done'; paint();
  }
  function admTool(t) {
    if (!isAdm()) return;                         // 第二道防線：就算 DOM 被偷塞按鈕，不是站主也不動
    const s = load(), tm = ymOf(today());
    let m = '';
    if (t === 'signtoday') { const r = doSign(today(), 'test'); m = r.ok ? '已簽今天（測試）' : '今天已經簽過了'; }
    else if (t === 'signday') { const d = ($('#admDay') || {}).value; if (d && ymOf(d) === tm) { const r = doSign(d, 'makeup'); m = r.ok ? `已補簽 ${d}（不扣互動點數）` : '那天已簽過'; } else m = '請選本月的日期'; }
    else if (t === 'fill') {
      const nn = Math.max(0, Math.min(31, +($('#admN') || {}).value || 0)), t0 = today(); let k = 0, back = 0;
      Object.keys(s.signs).filter((d) => ymOf(d) === tm).forEach((d) => delete s.signs[d]);
      while (k < nn && back < 31) { const d = addDays(t0, -back); back++; if (ymOf(d) === tm) { s.signs[d] = { k: 'test', at: nowMs() }; k++; } }
      for (let f = 1; k < nn && f < 40; f++) { const d = addDays(t0, f); if (ymOf(d) === tm) { s.signs[d] = { k: 'test', at: nowMs() }; k++; } }
      save(); m = `本月已填到 ${total(tm)} 天`;
    }
    else if (t === 'clear') { Object.keys(s.signs).filter((d) => ymOf(d) === tm).forEach((d) => delete s.signs[d]); Object.keys(s.claims).filter((k) => k.indexOf(tm) === 0).forEach((k) => delete s.claims[k]); s.pts[tm] = 0; s.mk[tm] = 0; s.ticket = {}; save(); m = '本月已清空（簽到、兌換紀錄、補簽進度）'; }
    else if (t === 'resetunlock') { s.unlock = {}; s.fresh = []; Object.keys(s.claims).forEach((k) => { s.claims[k].articles = []; s.claims[k].packs = []; }); save(); m = '解鎖紀錄已清空'; }
    else if (t === 'claim') { const i = +($('#admNode') || {}).value; if (claimed(tm, i)) delete s.claims[tm + ':' + i]; const r = doClaim(i, true); if (r.ok) { if (i === 3) { V.pane = 'wish'; } else { V.claim = r; V.pane = 'done'; } paint(); return; } m = r.error === 'soldout' ? '寶箱已全部打開（補貨中）' : '兌換失敗：' + r.error; }
    else if (t === 'settoday') { const d = ($('#admToday') || {}).value; if (d) { T.today = d; V.ym = ymOf(d); m = '「今天」改成 ' + d; } }
    else if (t === 'realtoday') { T.today = ''; V.ym = ymOf(today()); m = '已恢復真實日期'; }
    else if (t === 'ptsfull') { s.pts[tm] = Math.max(pts(tm), mkCost(tm)); save(); m = '互動已加滿：' + pts(tm); }
    else if (t === 'ptsplus') { s.pts[tm] = pts(tm) + 1; save(); m = '互動 ' + pts(tm); }
    else if (t === 'ptsclear') { s.pts[tm] = 0; s.dayPts = {}; s.lastAt = 0; save(); m = '互動已歸零'; }
    else if (t === 'wishreply') {
      const id = ($('#admBatch') || {}).value, st = ($('#admSt') || {}).value, w = s.wishes.find((x) => x.id === id);
      if (!w) m = '沒有可以回覆的願望'; else { w.items.forEach((i) => { i.st = st; i.reply = st === 'eval' ? '排進開發清單' : st === 'no' ? '目前做不到' : ''; }); evalBatch(w); save(); m = `已把 ${id} 全部標成「${ST[st]}」→ ${w.result}`; }
    }
    else if (t === 'wishsync') { syncWishes().then((n) => { admMsg(`從意見回饋同步了 ${n} 項狀態`); paint(); admMsg(`從意見回饋同步了 ${n} 項狀態`); }); return; }
    paint(); admMsg(m);
  }

  /* ------------------------------------------------------------------ 開關 */
  function open(pane) {
    css(); load();
    ready().then(() => {
      if (!ov) {
        ov = document.createElement('div'); ov.className = 'ciov'; ov.id = 'ciOv'; ov.hidden = true;
        ov.innerHTML = '<div class="cidlg" id="ciDlg" role="dialog" aria-modal="true" aria-labelledby="ciTtl"></div>';
        document.body.appendChild(ov);
        ov.addEventListener('mousedown', (e) => { if (e.target === ov) close(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && V.open) close(); });
      }
      V.open = true; V.ym = ymOf(today()); V.pane = pane || 'main'; V.mkMode = false; V.claim = null; V.mkPick = '';
      ov.hidden = false; paint();
      if (window.CalGrid && window.CalGrid.load) window.CalGrid.load().then(() => { if (V.open && V.pane === 'main') paint(); });
      try { const b = $('#ciSign') || $('#ciX', ov); if (b && b.focus) b.focus({ preventScroll: true }); } catch (e) { /* 略 */ }
    });
  }
  function close(keep) { if (ov) ov.hidden = true; V.open = false; V.mkMode = false; const b = $('#ciBibi'); if (b && !keep) b.remove(); paintCard(); paintDot(); }

  /* ------------------------------------------------------------------ 入口：頂欄小圖示、總覽卡 */
  function paintDot() {
    const b = document.getElementById('ciBtn'); if (!b) return;
    const d = $('i', b); const un = loggedIn() && !load().signs[today()];
    if (d) d.hidden = !un;
    b.title = un ? '每日簽到（今天還沒簽）' : '每日簽到';
  }
  function mountTop() {
    const b = document.getElementById('ciBtn'); if (!b || b._ci) return; b._ci = 1;
    css(); b.innerHTML = ICON_CAL + '<i hidden></i>';
    b.onclick = () => open();
    paintDot();
  }
  function cardInner() {
    const tm = ymOf(today()), tot = total(tm), ns = nodes(), nx = nextNode(tm);
    const ready_ = ns.map((n, i) => (tot >= n && !claimed(tm, i) ? i : -1)).filter((i) => i >= 0);
    const sub = ready_.length ? `有 ${ready_.length} 個節點可以兌換` : nx ? `再 ${nx - tot} 天可兌換` : '本月節點都兌換了';
    return `<div class="ci-n"><div class="ci-big" data-v="tot">${tot}<small>天・本月</small></div><div class="ci-bar" aria-hidden="true"><i style="width:${Math.min(100, Math.round(100 * tot / ns[ns.length - 1]))}%"></i></div><div class="ci-sub" data-v="sub">${esc(load().signs[today()] ? '今天已簽到・' + sub : '今天還沒簽・' + sub)}</div></div>`;
  }
  function card() {
    css(); load();
    return `<div class="osc ci" data-k="ci" role="button" tabindex="0" aria-label="每日簽到，點一下開啟月曆" title="點一下開啟簽到月曆">`
      + `<div class="osc-h"><span class="osc-ic" aria-hidden="true" style="--ic:var(--cyan)">${ICON_CAL}</span><b class="osc-t">簽到</b><button class="howbtn pop" data-how="ovs-ci" data-ttl="每日簽到" type="button" aria-label="每日簽到怎麼用">?</button></div>`
      + `<div class="osc-n" id="ciCardBody">${cardInner()}</div></div>`;
  }
  function paintCard() { const b = document.getElementById('ciCardBody'); if (b) { load(); b.innerHTML = cardInner(); } }
  function mounted(host) {
    if (!host) return;
    if (!document.getElementById('how-ovs-ci')) { const b = document.createElement('div'); b.className = 'howtxt'; b.id = 'how-ovs-ci'; b.hidden = true; host.appendChild(b); }
    const hx = document.getElementById('how-ovs-ci');
    hx.innerHTML = '<b class="howq">每天按一下簽到，月曆會留下勾。</b><ul><li>每月累積滿 3／7／14／20 天各可兌換一次：教學文章、產業深度分析、許願券。</li><li>每月 1 日歸零，已解鎖的文章永久保留，到精選文章的「比比寶箱」分頁閱讀。</li><li>漏簽可跟比比互動換補簽。</li><li>預覽版，資料只存在這個瀏覽器。</li></ul>';
    ready().then(() => paintCard());
  }

  /* ------------------------------------------------------------------ 寶箱分頁（給 articles.js） */
  const VF = { f: 'unl' };
  const CHEST = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 10h18v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M4 10V8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2"/><path d="M12 10v4"/><rect x="10" y="13" width="4" height="3" rx=".5"/></svg>';
  const LOCKI = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M5 7V5a3 3 0 1 1 6 0v2h.5A1.5 1.5 0 0 1 13 8.5v5a1.5 1.5 0 0 1-1.5 1.5h-7A1.5 1.5 0 0 1 3 13.5v-5A1.5 1.5 0 0 1 4.5 7H5zm1.5 0h3V5a1.5 1.5 0 0 0-3 0v2z"/></svg>';
  function unlockHint(a) {
    const p = packOf(a.id); const c = cfg().nodes;
    return p && p.line === 'ind' ? `簽到 ${c[2]} 天解鎖` : `簽到 ${c[0]}／${c[1]} 天解鎖`;
  }
  function vcard(a) {
    const un = unlocked(a.id), fresh = load().fresh.indexOf(a.id) >= 0, p = packOf(a.id);
    const badge = `<span class="artbadge k-vault">${CHEST.replace('<svg', '<svg width="13" height="13"')}${esc(lineName(a.line))}</span>`;
    const pend = p && p.pending ? `<span class="rm" title="${esc(p.pending)}">待補</span>` : '';
    if (!un) return `<div class="artc lkd vlk k-vault" data-id="${esc(a.id)}" data-lock="1" data-line="${esc(a.line)}"><span class="wm">${CHEST.replace('<svg', '<svg width="96" height="96"')}</span><div class="r1">${badge}<span class="rm">約 ${esc(a.reading_min)} 分鐘</span></div><div class="tt">${esc(a.title)}</div><div class="lk">${LOCKI}<span>${esc(unlockHint(a))}</span></div></div>`;
    return `<a class="artc k-vault${fresh ? ' vnew' : ''}" href="#article/${encodeURIComponent(a.id)}" data-id="${esc(a.id)}" data-lock="0" data-line="${esc(a.line)}"><span class="wm">${CHEST.replace('<svg', '<svg width="96" height="96"')}</span>${fresh ? '<span class="newb">新</span>' : ''}<div class="r1">${badge}<span class="rm">約 ${esc(a.reading_min)} 分鐘</span>${pend}</div><div class="tt">${esc(a.title)}</div>${a.subtitle ? `<div class="st">${esc(a.subtitle)}</div>` : ''}</a>`;
  }
  function paintVault(box) {
    css(); load();
    if (!M) { box.innerHTML = '<div class="artempty">載入中…</div>'; ready().then(() => { if (box.isConnected) paintVault(box); }); return; }
    const got = vaultGot(), tot = vaultTotal(), tm = ymOf(today()), nx = nextNode(tm);
    if (!got && VF.f === 'unl' && !VF._u) VF.f = 'all';
    const lines = ((M && M.lines) || []).map((l) => ({ l, list: allVault().filter((a) => a.line === l.id) }));
    box.innerHTML = `<div class="ci-vh"><span class="sum" id="vaultSum">已解鎖 ${got}／${tot} 篇${nx ? `・下一個節點：滿 ${nx} 天` : ''}</span><div class="ci-vseg" role="tablist" aria-label="篩選"><button type="button" data-f="unl" class="${VF.f === 'unl' ? 'on' : ''}" role="tab">已解鎖</button><button type="button" data-f="all" class="${VF.f === 'all' ? 'on' : ''}" role="tab">全部</button></div><button type="button" class="ci-btn sm" id="vaultGo">去簽到</button></div>`
      + lines.map(({ l, list }) => { const n = list.filter((a) => unlocked(a.id)).length, shown = VF.f === 'unl' ? list.filter((a) => unlocked(a.id)) : list; const hasNew = list.some((a) => load().fresh.indexOf(a.id) >= 0);
        return `<details class="ci-vl" data-line="${esc(l.id)}"${hasNew || V['vo' + l.id] ? ' open' : ''}><summary>${esc(l.name)}<small>已解鎖 ${n}／${list.length}</small></summary><div class="artgrid">${shown.length ? shown.map(vcard).join('') : '<div class="artempty">這個系列還沒有解鎖的文章，簽到滿天數就能兌換。</div>'}</div></details>`; }).join('');
    $$('.ci-vseg button', box).forEach((b) => { b.onclick = () => { VF.f = b.dataset.f; VF._u = 1; paintVault(box); }; });
    $$('.ci-vl', box).forEach((d) => { d.ontoggle = () => { V['vo' + d.dataset.line] = d.open; }; });
    $('#vaultGo', box).onclick = () => open();
    // 看過就把「新」記號清掉（下次打開不再亮邊）
    if (load().fresh.length) setTimeout(() => { load().fresh = []; try { localStorage.setItem(KEY + ':' + SU, JSON.stringify(load())); } catch (e) { /* 略 */ } }, 4000);
  }
  function vaultMeta(id) { const a = artMeta(id); return a ? Object.assign({}, a, { pack: packOf(id) }) : null; }
  function lockedPageHTML(id) {
    const a = artMeta(id); if (!a) return '';
    return `<div class="artpage k-all"><article class="card artpost artlocked cilk" id="artPost" data-id="${esc(id)}" data-lock="1" data-cat="vault">
<button type="button" class="artback" id="artBack" data-to="#articles/vault">← 返回</button>
<nav class="artcrumb" aria-label="麵包屑"><a href="#articles">精選文章</a><span aria-hidden="true">›</span><a class="kc" href="#articles/vault">比比寶箱</a><span aria-hidden="true">›</span><span class="cur">${esc(a.title)}</span></nav>
<h2 class="artttl">${esc(a.title)}</h2>
<div class="ci-lkbox" id="ciLkBox"><b>${LOCKI} 這篇還沒解鎖</b><br>寶箱文章只能靠每日簽到解鎖（${esc(unlockHint(a))}），付費方案不能直接打開。<br><button type="button" class="ci-btn" id="ciLkGo" style="margin-top:8px">去簽到</button></div>
</article></div>`;
  }

  /* ------------------------------------------------------------------ 對外 */
  window.TwCheckin = {
    open, close, card, mounted, paintCard, ready, bibi: bibiCard,
    unlocked, vaultMeta, paintVault, lockedPageHTML, vaultIcon: CHEST,
    state: () => ({ ym: ymOf(today()), today: today(), total: total(ymOf(today())), signs: Object.assign({}, load().signs), unlock: Object.keys(load().unlock), pts: pts(ymOf(today())), mk: mkUsed(ymOf(today())), wishes: load().wishes.length, uid: uid(), admin: isAdm() }),
    test: { enable() { T.on = true; }, skip(ms) { T.off += ms; }, today(d) { T.today = d || ''; }, reset() { S = blank(); SU = uid(); save(); } },
  };
  document.addEventListener('click', (e) => {
    const t = e.target.closest && e.target.closest('#ciLkGo'); if (t) { e.preventDefault(); open(); }
    const c = e.target.closest && e.target.closest('.osc.ci'); if (c && !e.target.closest('.howbtn')) { /* 總覽卡的點擊由 app.js go() 轉進來 */ }
  });
  function boot() {
    css(); ready(); mountTop();
    window.addEventListener('tw:account', () => { S = null; paintDot(); paintCard(); if (V.open) paint(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
