/* ============================================================================
   體驗額度（site/grants.js）—— 2026-10-09，docs/launch_gap_payment_1009.md 第 3 節、docs/launch_gap_legal_1009.md 第 2 節
   ----------------------------------------------------------------------------
   Andy 10-09：「我部分付費功能他們看不到，兩個方式開放給他們用，但是有期限且限制次數，好比說主促 1-2 個禮拜可以看幾次，重點是得要有曝光」。
   ★ 叫「體驗額度」，畫面不准出現「免費試用」：不改方案、免綁卡、到期不扣款、自動回原等級；次數只在伺服器（account-api grant 區塊）計。

   做什麼：
     · 被鎖的功能（perm.js 的需開通卡、quota.js 的「今天次數用完」卡、熱力圖跳頁卡）如果這個人還有體驗額度：
       卡片多一個「體驗剩 N 次」小標籤＋「繼續看（用掉 1 次）」鈕 —— **按了才扣**（POST /v1/grants/hit），不會一進頁就扣。
       扣成功 → 這個單位今天打開（perm.js can()、quota.js 都問 TwGrants.open），內容出現；同一天同一單位再看不重扣。
     · 用完 → 回到原本的升級卡，卡上多一句「體驗額度已用完」。到期（伺服器說 end 已過）→ 一律當沒有，回原狀。
     · 訪客：活動中的功能在卡上寫「登入即可體驗 M 次」，按鈕換成「登入領取體驗」。
     · 總覽（#overview）活動期間顯示一條可關閉的細橫幅「上市體驗週：XX 功能每項可看 M 次，剩 N 天」，點了開「活動辦法」（7 點，公平法 §21 要的條件）。
       關閉記 localStorage（tw.grantBar.off.<活動代號>，只是這台瀏覽器不再顯示）。
   「單位」：個股功能＝代號；產業鏈功能（ind.*）＝c.<鏈>／g.<族群>；動作計次（篩選）＝quota.js 的 actUnit；其他＝d（整天一次）。

   對外：window.TwGrants
     open(k)            這個功能「目前這個單位」今天已經用體驗打開了嗎（perm.js／quota.js 問）
     has(k, key)        指定單位
     extra(k)           卡片要加的東西：{ gk, left, max, name, end } ／ { out:true } ／ { guest:{m,name} } ／ null
     use(k, key, el)    扣一次（el＝扣完要再幫他點一次的按鈕，例如畫線工具）
     state() / refresh() / rules(gid) / banner()
   事件：window 'tw:grants'（剩餘次數或打開的單位變了）
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } } };
  const A = () => window.TwAccount || null;
  const F = () => window.TwFeatures || null;
  const G = { pub: null, me: null, open: {}, seq: 0, busy: false, pend: null, who: '' };
  const DAY = 86400000;
  const tpeDate = (ms) => { const d = new Date(ms + 8 * 3600000); return { y: d.getUTCFullYear(), m: d.getUTCMonth() + 1, d: d.getUTCDate(), hh: d.getUTCHours(), mm: d.getUTCMinutes() }; };
  const md = (ms) => { const t = tpeDate(ms); return `${t.m}/${t.d}`; };
  const logged = () => { const a = A(); return !!(a && a.on && a.on() && a.user && a.user()); };
  function safeKey(s) {
    if (/^[0-9A-Za-z_.-]{1,24}$/.test(s)) return s;
    let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return 'x' + h.toString(16);
  }
  function unitOf(k) {
    const h = location.hash || '', f = F() && F().byId(k);
    let m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h);
    if (m && f && (f.cat === 'stockk' || f.cat === 'stocktab')) return m[1].toUpperCase();
    if (/^ind\./.test(k)) {
      m = /^#industry\/group\/([^/?]+)/.exec(h); if (m) return safeKey('g.' + decodeURIComponent(m[1]));
      m = /^#industry\/([^/?]+)/.exec(h); if (m) return safeKey('c.' + decodeURIComponent(m[1]));
    }
    m = /^#heatmap\/theme\/([^/?]+)/.exec(h); if (m && k === 'heat.detail') return safeKey('t.' + decodeURIComponent(m[1]));
    return 'd';
  }
  /* 有效（還沒到期）的體驗 */
  const live = () => ((G.me && G.me.grants) || []).filter((g) => g.end > Date.now() && g.start <= Date.now() + 60000);
  const covers = (k) => live().filter((g) => g.feats && g.feats[k]);
  const leftOf = (k) => covers(k).reduce((s, g) => s + (g.feats[k].left || 0), 0);
  function has(k, key) { return !!(covers(k).length && G.open[k] && G.open[k].has(key)); }
  function open(k) { return has(k, unitOf(k)); }
  /* 活動中的公開設定（訪客用）：這個功能有沒有在 promo／welcome 裡 */
  function pubFor(k) {
    const p = G.pub; if (!p) return null;
    const now = Date.now();
    const pr = (p.promo || []).find((d) => d.feats && d.feats[k] && d.t0 <= now && d.t1 > now);
    if (pr) return { m: pr.feats[k], name: pr.name, end: pr.t1, kind: 'promo' };
    const w = (p.welcome || []).find((d) => d.feats && d.feats[k]);
    return w ? { m: w.feats[k], name: w.name, days: w.days, kind: 'welcome' } : null;
  }
  function extra(k) {
    if (!k) return null;
    const P = window.TwPerm;
    if (P && P.owner && P.owner()) return null;
    if (logged()) {
      const c = covers(k);
      if (!c.length) return null;
      const left = leftOf(k);
      if (left > 0) { const g = c.find((x) => x.feats[k].left > 0) || c[0]; return { gk: k, left, max: c.reduce((s, x) => s + x.feats[k].max, 0), name: g.name, end: g.end }; }
      return { gk: k, out: true, name: c[0].name };
    }
    const pf = pubFor(k);
    return pf ? { gk: k, guest: pf } : null;
  }

  // ------------------------------------------------------------------ 讀取
  async function refresh(force) {
    const a = A(); if (!a || !a.on || !a.on()) { G.pub = null; G.me = null; paint(); return; }
    const seq = ++G.seq;
    /* 公開的活動設定：同一個分頁 1 分鐘內重用（每換一頁都打一次 Worker 沒有意義；管理區改了會叫 refresh(true)）*/
    let pubC = null;
    if (!force) { try { const c = JSON.parse(sessionStorage.getItem('tw.grantPub') || 'null'); if (c && Date.now() - c.at < 60000 && c.d) pubC = c.d; } catch (e) { pubC = null; } }
    const [pub, me] = await Promise.all([pubC ? Promise.resolve(pubC) : a.call('/v1/grants/public', {}), logged() ? a.call('/v1/grants/me', {}) : Promise.resolve(null)]);
    if (seq !== G.seq) return;
    G.pub = pub && pub._s === 200 ? pub : null;
    if (G.pub && !pubC) { try { sessionStorage.setItem('tw.grantPub', JSON.stringify({ at: Date.now(), d: G.pub })); } catch (e) { /* 私密視窗 */ } }
    G.me = me && me._s === 200 ? me : null;
    G.open = {};
    if (G.me && G.me.today) for (const [k, arr] of Object.entries(G.me.today)) G.open[k] = new Set(arr);
    paint();
  }
  function paint() {
    try { if (window.TwPerm) window.TwPerm.apply(); } catch (e) { /* 略 */ }
    try { if (window.TwQuota && window.TwQuota.evaluate) window.TwQuota.evaluate(); } catch (e) { /* 略 */ }
    banner();
    window.dispatchEvent(new CustomEvent('tw:grants', { detail: state() }));
  }
  function state() { return { pub: G.pub, me: G.me, open: Object.fromEntries(Object.entries(G.open).map(([k, s]) => [k, [...s]])) }; }

  // ------------------------------------------------------------------ 扣一次
  function toast(msg) { const T = window.TwSub; if (T && T.toast) T.toast(msg); }
  async function use(k, key, el) {
    if (G.busy) return false;
    const a = A(); if (!a || !logged()) { if (a && a.login) a.login(); return false; }
    key = key || unitOf(k);
    G.busy = true;
    let j = null;
    try { j = await a.call('/v1/grants/hit', { k, key }); } finally { G.busy = false; }
    if (j && j._s === 200 && j.ok) {
      (G.open[k] = G.open[k] || new Set()).add(key);
      /* 剩餘次數照伺服器回的（合併後）改；扣在哪一份不重要，畫面只顯示合計 */
      if (Number.isInteger(j.left) && G.me) {
        let rest = j.left;
        for (const g of covers(k)) { const x = g.feats[k]; x.left = Math.min(x.max, Math.max(0, rest)); rest -= x.left; x.used = x.max - x.left; }
      }
      const qm = document.getElementById('qcModal'); if (qm) qm.hidden = true;
      paint();
      if (!j.plan && !j.free) toast(j.again ? '今天看過的，不另外扣次' : `已使用 1 次體驗，還剩 ${Number.isInteger(j.left) ? j.left : leftOf(k)} 次`);
      if (el && el.isConnected) setTimeout(() => { try { el.click(); } catch (e) { /* 略 */ } }, 60);
      return true;
    }
    if (j && j._s === 200 && j.over) { toast('體驗額度已用完'); await refresh(); return false; }
    toast('連不到會員伺服器，稍後再試');
    return false;
  }

  // ------------------------------------------------------------------ 樣式
  function css() {
    if (document.getElementById('grantCss')) return;
    const s = document.createElement('style'); s.id = 'grantCss';
    s.textContent = `
.qcard .qc-gtag{display:inline-flex;align-items:center;gap:4px;margin-left:auto;height:22px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap;
  color:var(--cyan,#22d3ee);background:color-mix(in srgb,var(--cyan,#22d3ee) 14%,transparent);border:1px solid color-mix(in srgb,var(--cyan,#22d3ee) 45%,transparent)}
.qcard .qc-kick{flex-wrap:wrap}
.qcmodal .qcard .qc-kick{padding-right:30px}
.qcard .qc-try{display:flex;align-items:center;justify-content:center;gap:6px;width:100%;height:44px;margin-top:16px;border-radius:999px;box-sizing:border-box;cursor:pointer;
  background:transparent;color:var(--cyan,#22d3ee);border:1.5px solid var(--cyan,#22d3ee);font:inherit;font-size:var(--fs-body,14px);font-weight:700;white-space:nowrap}
.qcard .qc-try:hover{background:color-mix(in srgb,var(--cyan,#22d3ee) 12%,transparent)}
.qcard .qc-try:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
.qcard .qc-try[disabled]{opacity:.6;cursor:wait}
.qcard .qc-try+.qc-go{margin-top:10px}
.qcard .qc-gnote{margin:8px 0 0;font-size:var(--fs-sm,13px);color:var(--ink-3);line-height:1.5}
.qcard .qc-gnote a{color:var(--cyan,#22d3ee)}
.qcard .qc-gout{margin:8px 0 0;font-size:var(--fs-sm,13px);font-weight:600;color:var(--amber)}
.qcard.compact .qc-try{height:38px;margin-top:12px}
#grantBar{display:flex;align-items:center;gap:10px;margin:10px 0 0;padding:0 6px 0 14px;min-height:36px;border-radius:10px;font-size:13.5px;line-height:1.4;cursor:pointer;
  color:var(--ink);background:color-mix(in srgb,var(--cyan,#22d3ee) 10%,var(--panel));border:1px solid color-mix(in srgb,var(--cyan,#22d3ee) 40%,transparent)}
#grantBar[hidden]{display:none}
#grantBar .gb-ic{flex:none;color:var(--cyan,#22d3ee);font-weight:700}
#grantBar .gb-t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#grantBar .gb-t b{color:var(--cyan,#22d3ee)}
#grantBar .gb-r{flex:none;color:var(--ink-2);text-decoration:underline;font-size:12.5px}
#grantBar .gb-x{flex:none;width:32px;height:32px;border:0;border-radius:8px;background:transparent;color:var(--ink-3);font-size:18px;cursor:pointer}
#grantBar .gb-x:hover{color:var(--ink);background:var(--panel-3)}
.grules ol{margin:8px 0 0;padding-left:1.4em;font-size:14px;line-height:1.7;color:var(--ink-2)}
.grules ol li{margin:4px 0}
.grules .gr-f{color:var(--ink)}
@media (max-width:640px){
  #grantBar{margin:8px 0 0;padding:4px 2px 4px 10px;font-size:12.5px;align-items:flex-start}
  #grantBar .gb-t{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
  #grantBar .gb-r{display:none}
  .qcard .qc-gtag{margin-left:0}
  :root.m4 #grantBar{align-items:center;margin:8px 0}
  :root.m4 #grantBar .gb-t.gb-m{display:block;-webkit-line-clamp:unset;overflow:visible;line-height:1.45}
  :root.m4 #grantBar .gb-free{font-style:normal;white-space:nowrap;color:var(--ink)}
  :root.m4 #grantBar .gb-r.gb-rm{display:inline-flex;align-items:center;align-self:stretch;flex:none;padding:0 4px;min-height:36px;font-size:12.5px;font-weight:700;
    color:var(--cyan,#22d3ee);text-decoration:none;white-space:nowrap}
}`;
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------------ 卡片（qcard.js html() 會問 TwGrants.cardHtml）
  /* 回 { tag, sub, btn }：tag＝小標右邊的「體驗剩 N 次」、sub＝說明下面一行、btn＝升級鈕上方的「繼續看」 */
  function cardHtml(o) {
    const x = extra(o.gk);
    if (!x) return null;
    css();
    if (x.guest) {
      const g = x.guest;
      return { tag: `<span class="qc-gtag">🎁 登入可體驗 ${esc(g.m)} 次</span>`,
        sub: `<p class="qc-gnote">${esc(g.name)}：登入後此功能可體驗 ${esc(g.m)} 次${g.kind === 'promo' ? `，到 ${esc(md(g.end - 1))}` : `（註冊後 ${esc(g.days)} 天內）`}；免綁卡、到期不扣款。${g.kind === 'promo' ? '<a href="#" data-grules>活動辦法</a>' : ''}</p>`,
        btn: `<button type="button" class="qc-try" data-glogin>登入領取體驗</button>` };
    }
    if (x.out) return { tag: '', sub: `<p class="qc-gout" data-gout>體驗額度已用完</p>`, btn: '' };
    const key = o.gkey || unitOf(o.gk);
    return { tag: `<span class="qc-gtag" data-gleft="${esc(x.left)}">🎁 體驗剩 ${esc(x.left)} 次</span>`,
      sub: `<p class="qc-gnote">${esc(x.name)}：按「繼續看」才扣 1 次，今天重看同一個不另外扣；到 ${esc(md(x.end - 1))} 為止，免綁卡、到期不扣款。${(G.pub && (G.pub.promo || []).length) ? '<a href="#" data-grules>活動辦法</a>' : ''}</p>`,
      btn: `<button type="button" class="qc-try" data-gk="${esc(o.gk)}" data-gkey="${esc(key)}">繼續看（用掉 1 次體驗）</button>` };
  }
  document.addEventListener('click', (e) => {
    const t = e.target && e.target.closest && e.target.closest('.qc-try, [data-grules]');
    if (!t) return;
    e.preventDefault(); e.stopPropagation();
    if (t.hasAttribute('data-grules')) { rules(); return; }
    if (t.hasAttribute('data-glogin')) { const qm = document.getElementById('qcModal'); if (qm) qm.hidden = true; const a = A(); if (a && a.login) a.login(); return; }
    const k = t.dataset.gk; if (!k) return;
    t.disabled = true;
    const el = G.pend && G.pend.k === k ? G.pend.el : null;
    G.pend = null;
    use(k, t.dataset.gkey, el).finally(() => { if (t.isConnected) t.disabled = false; });
  }, true);
  /* 被鎖的按鈕（畫線、指標設定、3D 鈕）：perm.js 擋下時記住是哪一顆，扣完再幫他點一次 */
  function pending(k, el) { G.pend = { k, el }; }

  // ------------------------------------------------------------------ 總覽橫幅＋活動辦法
  const names = (feats) => Object.keys(feats || {}).map((k) => { const f = F() && F().byId(k); return f ? f.name : k; });
  function activePromo() { const now = Date.now(); return ((G.pub && G.pub.promo) || []).find((d) => d.t0 <= now && d.t1 > now) || null; }
  function banner() {
    const v = document.getElementById('v-overview');
    let el = document.getElementById('grantBar');
    const p = activePromo();
    /* 橫幅放在總覽那一頁（#v-overview）的最上面：換到別頁時整個 view 藏起來，不必另外判斷網址 */
    const off = p && ls.get('tw.grantBar.off.' + p.gid) === '1';
    if (!p || off || !v) { if (el) el.hidden = true; return; }
    css();
    if (!el) {
      el = document.createElement('div'); el.id = 'grantBar'; el.setAttribute('role', 'note');
      el.addEventListener('click', (e) => {
        if (e.target.closest('.gb-x')) { e.stopPropagation(); const q = activePromo(); if (q) ls.set('tw.grantBar.off.' + q.gid, '1'); el.hidden = true; return; }
        rules();
      });
    }
    /* ★ 2026-10-10（網頁手機同步稽核第 3 條）手機（html.m4 且 ≤640）另走一條：
       ① 位置固定在摘要卡列（#hero）正下方、分段鈕上面 —— 以前插在 #v-overview 最前面，再被 mobile3.js 把指數列／摘要卡搬回前面，
          結果有時在分段鈕上、有時在分段鈕下（看誰先跑），切分段就跳；mobile3.js hmSum 也會把它放回 #hero 後面。
       ② 字不截斷：「免綁卡、不扣款」與活動名、剩幾天一定看得到（原本兩行 line-clamp 會吃掉句尾）；功能名單收成「N 項功能」（完整清單在辦法裡）。
       ③ 露出「辦法 ›」短連結（法遵：辦法要易取得；原本手機把「活動辦法」字藏起來、只能整條點）。
       桌機那條字串與位置一字未改。*/
    const mob = document.documentElement.classList.contains('m4') && window.innerWidth <= 640;
    const hero = mob ? document.getElementById('hero') : null;
    if (hero && hero.parentNode === v) { if (hero.nextElementSibling !== el) hero.after(el); }
    else if (el.parentNode !== v || (!mob && v.firstElementChild !== el)) v.insertBefore(el, v.firstChild);
    const ns = names(p.feats), ms = [...new Set(Object.values(p.feats || {}))];
    const left = Math.max(1, Math.ceil((p.t1 - Date.now()) / DAY));
    const what = ns.length > 2 ? `${ns.slice(0, 2).join('、')}等 ${ns.length} 項功能` : ns.join('、');
    const per = p.per === 'day' ? '每天每項' : '每項';
    const mCnt = esc(ms.length === 1 ? ms[0] : Math.min(...ms) + '～' + Math.max(...ms));
    const t = mob ? `<span class="gb-ic" aria-hidden="true">🎁</span><span class="gb-t gb-m"><b>${esc(p.name)}</b>・剩 ${left} 天<br>${ns.length > 2 ? `${ns.length} 項付費功能` : esc(ns.join('、'))}${per}可看 ${mCnt} 次${logged() ? '' : '，登入即可使用'}；<em class="gb-free">免綁卡、不扣款</em></span><span class="gb-r gb-rm" role="link">辦法 ›</span><button type="button" class="gb-x" aria-label="關閉體驗活動橫幅">×</button>`
      : `<span class="gb-ic" aria-hidden="true">🎁</span><span class="gb-t"><b>${esc(p.name)}</b>：${esc(what)}${per}可看 ${esc(ms.length === 1 ? ms[0] : Math.min(...ms) + '～' + Math.max(...ms))} 次，剩 ${left} 天（${logged() ? '' : '登入即可使用，'}免綁卡、不扣款）</span><span class="gb-r">活動辦法</span><button type="button" class="gb-x" aria-label="關閉體驗活動橫幅">×</button>`;
    if (el.dataset.h !== t) { el.innerHTML = t; el.dataset.h = t; }
    el.dataset.gid = p.gid;
    el.title = '點一下看活動辦法';
    el.hidden = false;
  }
  function fmtFull(ms) { const t = tpeDate(ms); return `${t.y} 年 ${t.m} 月 ${t.d} 日 ${String(t.hh).padStart(2, '0')}:${String(t.mm).padStart(2, '0')}`; }
  function rules(gid) {
    const p = (gid && ((G.pub && G.pub.promo) || []).find((d) => d.gid === gid)) || activePromo();
    const T = window.TwSub;
    if (!p || !T || !T.dialog) return;
    css();
    const ms = [...new Set(Object.values(p.feats || {}))];
    const fl = Object.entries(p.feats || {}).map(([k, m]) => { const f = F() && F().byId(k); return `${f ? f.name : k}${ms.length > 1 ? ` ${m} 次` : ''}`; }).join('、');
    const m = ms.length === 1 ? ms[0] : '〔如各項所列〕';
    const dlg = T.dialog(`<div class="grules" id="grantRules"><h3>哩股哩股${esc(p.name)}活動辦法</h3><ol>
      <li>活動期間：${esc(fmtFull(p.t0))} 至 ${esc(fmtFull(p.t1 - 1))}（臺北時間）。</li>
      <li>對象：活動期間內已登入之註冊會員（含活動期間新註冊者）${p.audience === 'member' ? '' : '；付費方案會員本來就能使用下列功能，不另外發放'}。</li>
      <li>內容：下列付費功能，每位會員於活動期間內${p.per === 'day' ? '每天' : ''}各可使用 ${esc(m)} 次：<span class="gr-f">${esc(fl)}</span>。次數於每次按下「繼續看」時扣除（同一天看同一個不重複扣），剩餘次數顯示於功能旁。</li>
      <li>無須提供付款資訊；活動結束後自動回到原方案，不會產生任何費用。</li>
      <li>體驗額度不屬於免費試用，不影響日後購買付費方案之 7 天退款保證。</li>
      <li>本網站提供之內容為公開資料之整理與統計，不構成任何投資建議。</li>
      <li>本網站得因系統異常或不正當使用，調整或取消個別帳號之體驗額度；活動如有變更，將於本頁公告。</li>
    </ol><p>詳細條款見<a href="#terms" data-close>使用條款</a>第三節。</p><div class="row2"><button type="button" class="pri" data-close>知道了</button></div></div>`);
    return dlg;
  }

  // ------------------------------------------------------------------ 啟動
  let tmr = 0;
  const later = () => { clearTimeout(tmr); tmr = setTimeout(refresh, 150); };
  window.addEventListener('tw:account', () => { const a = A(); const w = a && a.user && a.user() ? a.user().email : ''; if (w !== G.who || !G.pub) { G.who = w; later(); } });
  window.addEventListener('tw:account-config', later);
  window.addEventListener('hashchange', () => banner());
  /* 手機／桌機兩種字串：拉寬拉窄跨過 640 才換（banner 內有 dataset.h 比對，沒變就不重畫） */
  { let rt = 0; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { if (document.getElementById('grantBar')) banner(); }, 250); }); }
  /* 到期：每分鐘看一次（過期的那一份從畫面拿掉、鎖頭蓋回來）*/
  setInterval(() => { if (G.me && (G.me.grants || []).some((g) => g.end <= Date.now() && !g._gone)) { G.me.grants.forEach((g) => { if (g.end <= Date.now()) g._gone = true; }); paint(); } }, 60000);
  window.TwGrants = { open, has, extra, use, cardHtml, pending, unitOf, refresh, rules, banner, state, left: leftOf };
  if (window.TW_ACCOUNT_ON) later();
})();
