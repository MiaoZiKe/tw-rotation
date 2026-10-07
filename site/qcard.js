/* ============================================================================
   額度／開通卡片（site/qcard.js）—— 2026-10-07，docs/quota_plan.md
   ----------------------------------------------------------------------------
   Andy（10-07 01:30）：「圖二的內容當達到上限，出現的畫面參考圖三，並且可以置中，之後會分成 Plus 和更上去的 Pro。
                        plus 目前先暫定皆可以觀看50次，pro 則是都不限次數」。

   一個元件、兩種卡（共用同一個殼，字級層次一樣）：
     · quota（額度用完）：小標「🔒 Plus 每日額度」→ 大標「今天的研究額度用完了」→ 一行說明 → 分段進度條
                         → 左「今日已使用 50 / 50 次」右「🕘 X 小時 Y 分後重置」→ 分隔線 → 「升級 Pro 還能使用」＋打勾清單 → 全寬大按鈕
     · lock（需開通）：小標「🔒 需要開通」→ 大標「此功能需開通」→ 功能名＋一句 → 分隔線 → 「這些方案可以使用」＋打勾清單 → 全寬大按鈕
   放在被擋住的那個區塊裡，**水平垂直置中**；區塊比視窗高時改成黏在視窗中間（sticky），捲到哪都看得到。
   寬約 520px，窄畫面＝區塊寬減左右各 16px。顏色全用主題變數（深淺主題都對）；按鈕是本站琥珀色。

   「一次」的定義（CEO 拍板，寫在 docs/quota_plan.md）：同一天（台北日期）、同一個單位只算一次。
     單位＝一檔個股頁、一張產業鏈剖析圖、一個付費分頁。個股頁裡切總覽／營收／籌碼分頁不算（同一支 stock/<代號>.json）。
   ★ 真正扣次在付費資料閘道（workers/data-gw）：前端計數按 F12 就能改，所以這支**只負責畫**，不自己數。
     data-gw 回 429 {error:'quota'} → site/datagw.js 發 'tw:quota' 事件 → 這裡把卡片蓋在那個區塊上。
     data-gw 沒開（正式站現況）就永遠不會有這個事件 → 畫面完全照舊。

   示範開關（給 Andy 在預覽站看，只在網址帶參數時生效，不寫任何資料）：
     ?demo=quota       Plus 已用 50/50
     ?demo=quota-free  免費會員已用 5/5（免費範本目前沒設額度，5 是示意值）
     ?demo=lock        產業鏈剖析圖（2D）需開通（走 perm.js 真的鎖頭流程，見 perm.js 的 DEMO_LOCK）

   對外：window.TwQCard
     html(o)            卡片 HTML（o.kind＝'quota'|'lock'）
     mount(host, o, cls)  蓋到區塊上（冪等：內容沒變不重寫）；cls＝外層多掛的 class（perm.js 用 plkov、quota.js 用 qlkov）
     unmount(host)      拿掉
     resetText(ms?)     「X 小時 Y 分後重置」（台北 00:00）
     show(o) / clear()  額度用完卡（data-gw 事件與示範開關用；換頁自動清掉）
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const DAY = 86400000, TPE = 8 * 3600000;
  /* 下一個台北 00:00（跟 data-gw 的 tpeReset 同一個算法）*/
  const nextReset = (now) => (Math.floor((now + TPE) / DAY) + 1) * DAY - TPE;
  function resetText(reset) {
    const now = Date.now(), r = Number.isFinite(reset) && reset > now ? reset : nextReset(now);
    const m = Math.max(1, Math.ceil((r - now) / 60000));
    return `${Math.floor(m / 60)} 小時 ${m % 60} 分後重置`;
  }
  const ICON = {
    lock: '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M5 7V5a3 3 0 1 1 6 0v2h.5A1.5 1.5 0 0 1 13 8.5v5a1.5 1.5 0 0 1-1.5 1.5h-7A1.5 1.5 0 0 1 3 13.5v-5A1.5 1.5 0 0 1 4.5 7H5zm1.5 0h3V5a1.5 1.5 0 1 0-3 0v2z"/></svg>',
    clock: '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 4.6V8l2.4 1.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    check: '<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M3 8.4l3.1 3.1L13 4.6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  // ------------------------------------------------------------------ 樣式
  function css() {
    if (document.getElementById('qcardCss')) return;
    const s = document.createElement('style'); s.id = 'qcardCss';
    /* 顏色只用主題變數：卡＝--panel、線＝--line／--line-2、字＝--ink／--ink-2／--ink-3、強調＝--amber（深淺主題各自的值）。
       按鈕字色：深色主題用 --bg（近黑，壓在亮琥珀上）；淺色主題的 --amber 是深琥珀，字改 --panel（白）。*/
    s.textContent = `
[data-qcard]{isolation:isolate}
[data-qcard][data-qcard-rel]{position:relative}
[data-qcard]>*:not(.qcov){filter:blur(6px)!important;opacity:.25!important;pointer-events:none!important;user-select:none!important}
.qcov{position:absolute!important;inset:0!important;z-index:40!important;display:flex!important;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;
  background:color-mix(in srgb,var(--panel) 50%,transparent);border-radius:inherit;filter:none!important;opacity:1!important;pointer-events:auto!important}
.qcov.tall{align-items:flex-start}
/* 手機版（mobile3.js）把桌機卡片變成 .m3host，會用 !important 藏掉「不是 .m3keep 的子節點」—— 卡片也會被藏，只剩模糊的內容、沒有卡（覆蓋稽核抓到的漏洞）。
   這條的權重比 index.html 那條高，卡片一律顯示 */
body.m3on .m3host:not(.mfull)>.qcov:not(.m3keep):not(.m3keep-h),body.m3on .m3host.mfull>.qcov:not(.m3keep):not(.m3keep-h){display:flex!important}
.qcard{--qc-on:var(--bg);width:min(520px,100%);box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:16px;
  padding:24px 28px;box-shadow:0 24px 60px -28px rgba(0,0,0,.55);text-align:left;font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}
:root[data-theme="light"] .qcard{--qc-on:var(--panel);box-shadow:0 18px 48px -26px rgba(40,30,10,.35)}
.qcov.tall .qcard{position:sticky}
.qcard .qc-kick{display:flex;align-items:center;gap:6px;font-size:var(--fs-sm,13px);font-weight:700;color:var(--amber);line-height:20px;margin:0 0 8px}
.qcard .qc-h{margin:0;font-size:var(--fs-h2,20px);font-weight:700;line-height:1.3;color:var(--ink)}
.qcard .qc-sub{margin:8px 0 0;font-size:var(--fs-body,14px);line-height:1.55;color:var(--ink-2)}
.qcard .qc-bar{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:4px;margin:20px 0 10px}
.qcard .qc-bar i{display:block;height:6px;border-radius:3px;background:var(--line-2)}
.qcard .qc-bar i.on{background:var(--amber)}
.qcard .qc-meta{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:var(--fs-sm,13px);color:var(--ink-2);white-space:nowrap}
.qcard .qc-meta b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:600;color:var(--ink)}
.qcard .qc-meta .qc-reset{display:inline-flex;align-items:center;gap:5px;font-variant-numeric:tabular-nums}
.qcard .qc-meta .qc-reset svg{color:var(--amber)}
.qcard hr{border:0;border-top:1px solid var(--line);margin:18px 0 14px}
.qcard .qc-lh{font-size:var(--fs-sm,13px);font-weight:600;color:var(--ink-2);margin:0 0 8px}
.qcard .qc-list{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.qcard .qc-list li{display:flex;align-items:center;gap:10px;font-size:var(--fs-body,14px);line-height:1.45;color:var(--ink);min-width:0}
.qcard .qc-list li svg{flex:none;color:var(--amber)}
.qcard .qc-list li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qcard .qc-list li small{margin-left:auto;font-size:var(--fs-sm,13px);color:var(--ink-3);white-space:nowrap;font-variant-numeric:tabular-nums}
.qcard .qc-go{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;height:48px;margin-top:20px;border-radius:999px;box-sizing:border-box;
  background:linear-gradient(90deg,var(--amber),color-mix(in srgb,var(--amber) 70%,var(--rise)));color:var(--qc-on)!important;
  font-size:var(--fs-h3,16px);font-weight:700;text-decoration:none;white-space:nowrap;box-shadow:0 10px 24px -14px var(--amber);transition:filter .15s}
.qcard .qc-go:hover{filter:brightness(1.07)}
.qcard .qc-go:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
.qcard.compact{padding:16px 18px}
.qcard.compact .qc-go{height:40px;margin-top:14px;font-size:var(--fs-body,14px)}
/* 手機：卡片吃滿區塊寬（外層左右不再留邊，區塊本身已經離螢幕邊 16px 以上）；用量與倒數放不下就換行，不准撐出卡片 */
@media (max-width:640px){.qcov{padding:16px 0}.qcard{padding:18px 16px;border-radius:14px}.qcard .qc-h{font-size:var(--fs-h3,16px)}
  .qcard .qc-meta{flex-wrap:wrap;row-gap:4px}.qcard .qc-go{height:44px}}
.qcmodal{position:fixed;inset:0;z-index:1450;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;background:color-mix(in srgb,var(--bg) 62%,transparent);backdrop-filter:blur(2px)}
.qcmodal[hidden]{display:none}
.qcmodal .qcard{position:relative;max-height:calc(100vh - 32px);overflow:auto}
.qcmodal .qc-x{position:absolute;top:10px;right:10px;width:32px;height:32px;border-radius:8px;border:0;background:transparent;color:var(--ink-3);font-size:18px;cursor:pointer}
.qcmodal .qc-x:hover{color:var(--ink);background:var(--panel-3)}
@media (prefers-reduced-motion:reduce){.qcard .qc-go{transition:none}}`;
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------------ 卡片內容
  /* 分段進度條：上限 ≤ 10 一段一次；> 10 固定 10 段（Plus 50 → 每段 5 次），已用到哪一段就亮到哪一段 */
  function bar(used, limit) {
    if (!(limit > 0)) return '';
    const segs = Math.min(10, limit), per = limit / segs;
    const lit = Math.min(segs, Math.ceil(Math.min(used, limit) / per - 1e-9));
    return `<div class="qc-bar" role="progressbar" aria-label="今日已使用" aria-valuemin="0" aria-valuemax="${limit}" aria-valuenow="${Math.min(used, limit)}">${Array.from({ length: segs }, (_, i) => `<i class="${i < lit ? 'on' : ''}"></i>`).join('')}</div>`;
  }
  function list(items) {
    return `<ul class="qc-list">${items.map((x) => {
      const t = typeof x === 'string' ? { t: x } : x;
      return `<li>${ICON.check}<span title="${esc(t.t)}">${esc(t.t)}</span>${t.s ? `<small>${esc(t.s)}</small>` : ''}</li>`;
    }).join('')}</ul>`;
  }
  /* o：{ kind, kick, title, sub, used, limit, reset, lh, items, btn, href, compact, btnCls } */
  function html(o) {
    const quota = o.kind === 'quota';
    const body = quota ? `${bar(o.used, o.limit)}<div class="qc-meta"><span>今日已使用 <b>${esc(o.used)} / ${esc(o.limit)}</b> 次</span><span class="qc-reset">${ICON.clock}<span class="qc-rt">${esc(resetText(o.reset))}</span></span></div>` : '';
    const lst = !o.compact && o.items && o.items.length ? `<hr><div class="qc-lh">${esc(o.lh || '')}</div>${list(o.items)}` : '';
    return `<div class="qcard${o.compact ? ' compact' : ''}" data-kind="${quota ? 'quota' : 'lock'}" role="alert">
      <div class="qc-kick">${ICON.lock}<span>${esc(o.kick || '')}</span></div>
      <div class="qc-h" role="heading" aria-level="3">${esc(o.title || '')}</div>${o.sub ? `<p class="qc-sub">${esc(o.sub)}</p>` : ''}
      ${o.compact ? '' : body}${lst}
      <a class="qc-go${o.btnCls ? ' ' + o.btnCls : ''}" href="${esc(o.href || '#pricing')}">${esc(o.btn || '查看方案')} <span aria-hidden="true">→</span></a></div>`;
  }

  // ------------------------------------------------------------------ 掛上／拿掉
  const ro = window.ResizeObserver ? new ResizeObserver((es) => es.forEach((e) => place(e.target))) : null;
  /* 置中：區塊比視窗矮 → flex 置中；比視窗高 → 卡片黏在視窗中間（sticky top＝(視窗高 − 卡高)/2）。
     區塊太矮放不下卡片 → 撐高到「卡高＋上下 16px」（只撐 min-height，拿掉時還原）。*/
  function place(host) {
    const ov = host && host.querySelector(':scope > .qcov'), card = ov && ov.querySelector('.qcard');
    if (!card) return;
    const ch = card.offsetHeight, vh = window.innerHeight || 800;
    const need = ch + 32;
    if (host.dataset.qcMin == null) host.dataset.qcMin = host.style.minHeight || '';
    if (host.offsetHeight < need - 1) host.style.minHeight = need + 'px';
    const tall = host.offsetHeight > vh;
    if (ov.classList.contains('tall') !== tall) ov.classList.toggle('tall', tall);
    const top = tall ? Math.max(16, Math.round((vh - ch) / 2)) + 'px' : '';
    if (card.style.top !== top) card.style.top = top;
  }
  function mount(host, o, cls) {
    if (!host) return null;
    css();
    let ov = host.querySelector(':scope > .qcov');
    if (!host.hasAttribute('data-qcard')) {
      host.setAttribute('data-qcard', o.kind || 'lock');
      if (getComputedStyle(host).position === 'static') host.setAttribute('data-qcard-rel', '');
    }
    /* 小區塊（一行重點、單顆小卡）用精簡版：只留小標、大標、說明、按鈕，免得把版面撐成一大塊 */
    if (o.compact == null && !ov) o.compact = host.offsetHeight > 0 && host.offsetHeight < 200 && host.offsetWidth < 360;
    const h = html(o);
    if (!ov) { ov = document.createElement('div'); ov.className = 'qcov'; host.appendChild(ov); if (ro) ro.observe(host); }
    /* 只在缺的時候才加：classList.add 就算 class 已經在也會觸發一次屬性變動，perm.js 的 MutationObserver 會因此無限重算 */
    if (cls) cls.split(/\s+/).forEach((c) => { if (c && !ov.classList.contains(c)) ov.classList.add(c); });
    if (ov.dataset.h !== h) { ov.innerHTML = h; ov.dataset.h = h; }
    if (host.lastElementChild !== ov) host.appendChild(ov);
    place(host);
    tick();
    return ov;
  }
  function unmount(host) {
    if (!host) return;
    const ov = host.querySelector(':scope > .qcov'); if (ov) ov.remove();
    if (ro) ro.unobserve(host);
    if (host.dataset.qcMin != null) { host.style.minHeight = host.dataset.qcMin; delete host.dataset.qcMin; }
    host.removeAttribute('data-qcard'); host.removeAttribute('data-qcard-rel');
  }
  /* 倒數每 30 秒更新一次（只改文字，不重畫卡片）；畫面上沒有額度卡就停 */
  let timer = 0;
  function tick() {
    if (timer) return;
    timer = setInterval(() => {
      const els = document.querySelectorAll('.qcard[data-kind="quota"] .qc-rt');
      if (!els.length) { clearInterval(timer); timer = 0; return; }
      const r = Q.cur && Q.cur.reset;
      els.forEach((el) => { const t = resetText(r); if (el.textContent !== t) el.textContent = t; });
    }, 30000);
  }
  window.addEventListener('resize', () => document.querySelectorAll('[data-qcard]').forEach(place));

  // ------------------------------------------------------------------ 方案資料（清單與按鈕要寫「升級哪一個」）
  const PLUS = { id: 'plus', name: 'Plus', dq: 50 }, PRO = { id: 'pro', name: 'Pro', dq: null };
  function plans() {
    const P = window.TwPricing;
    const list = P && P.plans ? P.plans() : null;
    const paid = (list || []).filter((p) => p && p.id !== 'guest' && p.id !== 'free');
    if (!paid.some((p) => p.id === 'plus')) paid.push(PLUS);
    if (!paid.some((p) => p.id === 'pro')) paid.push(PRO);
    return { all: list || [], paid };
  }
  const dqTxt = (dq) => (Number.isInteger(dq) ? `每日 ${dq} 次` : '不限次數');
  /* 現在的方案用完了 → 該升級哪一個：免費／訪客 → 有額度而且比較多的（Plus）；已經是有額度的付費 → 不限的（Pro）*/
  function upgradeFor(planId, limit) {
    const { paid } = plans();
    const up = paid.filter((p) => p.id !== planId && (p.dq == null || p.dq > limit));
    if (planId === 'free' || planId === 'guest' || !planId) return up.find((p) => p.id === 'plus') || up.find((p) => p.dq != null) || up[0] || PLUS;
    return up.find((p) => p.id === 'pro') || up.find((p) => p.dq == null) || up[0] || PRO;
  }
  /* 額度卡的選項（data-gw 回的 used／limit／reset／plan）*/
  function quotaOpts(q) {
    const plan = q.plan || 'free';
    /* data-gw 擋的是「某個功能自己的每日次數」（範本 lims）→ 標題寫那個功能，清單寫哪些方案次數更多 */
    const Ft = window.TwFeatures, ff = q.feat && Ft ? Ft.byId(q.feat) : null;
    if (ff) {
      const lk = lockOpts(ff, plan === 'guest' ? 'guest' : 'member');
      return { kind: 'quota', kick: '每日瀏覽次數', title: `今天的「${ff.name}」次數用完了`, sub: `今日已用完 ${q.used}/${q.limit} 次，升級方案可增加每日次數。`,
        used: q.used, limit: q.limit, reset: q.reset, lh: lk.items.length ? '這些方案可以看更多次' : '', items: lk.items, btn: lk.btn, href: '#pricing/need/' + encodeURIComponent(ff.id) };
    }
    const { all } = plans();
    const me = all.find((p) => p.id === plan);
    const planName = plan === 'free' ? '免費' : plan === 'guest' ? '訪客' : (me && me.name) || (plan === 'plus' ? 'Plus' : plan);
    /* 訪客用完：下一步是「免費註冊」（註冊會員每日 10 次），不是直接叫他付錢 */
    if (plan === 'guest') {
      const fr = all.find((p) => p.id === 'free');
      const n = fr && Number.isInteger(fr.dq) ? fr.dq : 10;
      return { kind: 'quota', kick: '訪客 每日額度', title: '今天的研究額度用完了', sub: `免費註冊就能每天看 ${n} 次，繼續查看完整研究內容。`,
        used: q.used, limit: q.limit, reset: q.reset, lh: '免費註冊還能使用', items: [`每日 ${n} 次研究瀏覽`, '自選清單（登入後跨裝置同步）', '同一檔、同一張圖當天重看不另外扣次'],
        btn: '免費註冊', href: '#pricing/plan/free' };
    }
    const up = upgradeFor(plan, q.limit);
    const unlimited = up.dq == null;
    const items = unlimited
      ? ['不限次數瀏覽個股頁', '不限次數瀏覽產業鏈剖析圖', '所有付費分頁不限次數', '不必等每日額度重置']
      : [`每日 ${up.dq} 次研究瀏覽`, '個股頁、產業鏈剖析圖、付費分頁共用額度', '同一檔、同一張圖當天重看不另外扣次', ...extraFeats(plan, up)].slice(0, 5);
    return { kind: 'quota', kick: `${planName} 每日額度`, title: '今天的研究額度用完了',
      sub: unlimited ? `升級 ${up.name} 不限次數，繼續查看完整研究內容。` : `升級 ${up.name} 提高每日額度，繼續查看完整研究內容。`,
      used: q.used, limit: q.limit, reset: q.reset, lh: `升級 ${up.name} 還能使用`, items, btn: `升級 ${up.name}`, href: '#pricing/plan/' + encodeURIComponent(up.id) };
  }
  /* 目標方案有、目前方案沒有的功能（最多 2 項；方案資料讀不到就不列）*/
  function extraFeats(cur, up) {
    const F = window.TwFeatures, { all } = plans();
    const a = all.find((p) => p.id === cur), b = all.find((p) => p.id === up.id);
    if (!F || !a || !b) return [];
    return F.list.filter((f) => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && (a.feats || {})[f.id] === false && (b.feats || {})[f.id] !== false).slice(0, 2).map((f) => f.name);
  }
  /* 需開通卡的選項（perm.js 的鎖頭）：哪些方案有這個功能、按鈕寫最便宜能解鎖的那個 */
  function lockOpts(f, who) {
    const P = window.TwPricing;
    let ok = P && P.unlockers ? P.unlockers(f.id) : null;
    if (DEMO === 'lock' || !ok) ok = null;
    const { paid } = plans();
    const rows = ok ? ok : paid.filter((p) => p.id === 'plus' || p.id === 'pro');
    const guest = who === 'guest';
    const first = rows[0] || PLUS;
    const items = rows.slice(0, 5).map((p) => ({ t: p.id === 'free' ? '註冊會員（免費）' : p.name, s: p.id === 'free' ? '登入即可' : dqTxt(p.dq) }));
    return { kind: 'lock', kick: '需要開通', title: f.cat === 'grp' ? '此族群需開通' : '此功能需開通',
      sub: `${f.name}・${guest ? '登入或升級方案即可使用' : '升級方案即可使用'}`, lh: items.length ? '這些方案可以使用' : '', items,
      btn: first.id === 'free' ? (guest ? '免費註冊／登入' : '查看方案') : `升級 ${first.name}`, href: '#pricing/need/' + encodeURIComponent(f.id), btnCls: 'plkgo' };
  }

  // ------------------------------------------------------------------ 額度用完（data-gw 事件／示範）
  const DEMO = (/[?&]demo=([a-z-]+)/.exec(location.search) || [])[1] || '';
  const Q = { cur: null, host: null, obs: null, raf: 0 };
  /* 卡片蓋在哪：產業鏈頁＝剖析圖那一塊（#dgSec）；個股頁＝整個個股頁；其他＝目前這一頁 */
  function hostFor(name) {
    const h = location.hash || '';
    const vis = (el) => !!el && el.getClientRects().length > 0;
    if (/^#industry\/[^/]+/.test(h) && !/^#industry\/group\//.test(h) && (!name || /^(supply_chain|chain\/)/.test(name) || name === '__demo')) { const d = document.getElementById('dgSec'); if (vis(d)) return d; }
    if (/^#stock\//.test(h)) { const s = document.getElementById('v-industry'); if (vis(s)) return s; }
    const v = document.querySelector('main .view.on');
    return vis(v) ? v : null;
  }
  function paint() {
    Q.raf = 0;
    if (!Q.cur) return;
    const host = hostFor(Q.cur.name);
    if (Q.host && Q.host !== host) unmount(Q.host);
    Q.host = host;
    if (host) mount(host, quotaOpts(Q.cur), 'qgate');
  }
  const schedule = () => { if (!Q.raf) Q.raf = requestAnimationFrame(paint); };
  function show(q) {
    Q.cur = Object.assign({ used: 0, limit: 0, reset: nextReset(Date.now()), plan: 'free' }, q);
    if (!Q.obs && window.MutationObserver) { Q.obs = new MutationObserver(schedule); Q.obs.observe(document.body, { childList: true, subtree: true }); }
    schedule();
  }
  function clear() {
    Q.cur = null;
    if (Q.host) unmount(Q.host);
    Q.host = null;
    document.querySelectorAll('.qcov.qgate').forEach((ov) => unmount(ov.parentElement));
    if (Q.obs) { Q.obs.disconnect(); Q.obs = null; }
  }
  /* data-gw 回 429 quota → datagw.js 發這個事件。換頁先清掉：下一頁要的檔如果也超過，data-gw 會再回一次 429 */
  window.addEventListener('tw:quota', (e) => show(e.detail || {}));
  window.addEventListener('hashchange', () => { if (!DEMO.startsWith('quota')) clear(); else schedule(); });
  /* 方案資料晚到（訂閱頁的方案清單）→ 重畫一次，按鈕與清單才會用後端的方案名稱 */
  window.addEventListener('tw:plans', () => { if (Q.cur) { const ov = Q.host && Q.host.querySelector(':scope > .qcov'); if (ov) ov.dataset.h = ''; schedule(); } });

  if (DEMO === 'quota' || DEMO === 'quota-free') {
    const go = () => show(DEMO === 'quota' ? { name: '__demo', used: 50, limit: 50, plan: 'plus' } : { name: '__demo', used: 5, limit: 5, plan: 'free' });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
  }

  /* 浮在畫面中間的版本（自選清單超過上限這種「按了沒反應」的情況用）：點遮罩、×、Esc 關閉；按鈕照樣連訂閱頁 */
  function modal(o) {
    css();
    let m = document.getElementById('qcModal');
    if (!m) {
      m = document.createElement('div'); m.id = 'qcModal'; m.className = 'qcmodal'; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
      document.body.appendChild(m);
      m.addEventListener('click', (e) => { if (e.target === m || e.target.closest('.qc-x') || e.target.closest('.qc-go')) m.hidden = true; });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !m.hidden) m.hidden = true; });
    }
    m.innerHTML = html(Object.assign({ compact: false }, o)).replace('<div class="qc-kick">', '<button type="button" class="qc-x" aria-label="關閉">×</button><div class="qc-kick">');
    m.hidden = false;
    const g = m.querySelector('.qc-go'); if (g) setTimeout(() => g.focus(), 30);
    return m;
  }

  window.TwQCard = { html, mount, modal, unmount, place, resetText, nextReset, show, clear, quotaOpts, lockOpts, demo: DEMO, state: () => (Q.cur ? Object.assign({}, Q.cur) : null) };
})();
