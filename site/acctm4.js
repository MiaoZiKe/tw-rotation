/* ============================================================================
   手機（html.m4，≤640）右上角頭像的帳號選單 —— Andy 2026-10-09 06:5x
   ----------------------------------------------------------------------------
   原話：「使用者上方需要有…拿掉自選清單，頭貼旁需要有 訪客／註冊會員／plus／pro 符號，新增 訂閱方案、通知、
         額度上限（裡面可以知道他所有功能額度還剩多少）、意見回饋、刪除帳號功能（標紅色）、登出。
         以上功能皆需要連動到需要的功能上」；07:0x 追加「新增一個 客服 關／開 功能」。

   ★ 只管手機：account.js 的 openMenu() 在 html.m4 時把同一個 #acctMenu 交給這支畫；桌機（沒有 m4）完全走原本的選單，
     這支一個節點都不插（CLAUDE.md 2026-10-08「手機改動不准影響桌機」）。網頁版要不要同步，等 Andy 決定。
   ★ 為什麼沿用 #acctMenu 而不是另做一個：account.js 已經處理「點外面收起」「管理區各項 data-a 的導頁」「點徽章到 #pricing」，
     沿用就不必再抄一份；新加的項目用 data-m（account.js 只認 data-a，所以不會被它攔走、開關切了選單也不會收）。

   每一項接到哪裡（「以上功能皆需要連動到需要的功能上」）：
     訂閱方案 → #pricing（右邊標目前方案）
     通知     → #notices（notices.js 的公告頁；有未讀公告就顯示紅色數字＝TwNotices.unread()）
     額度上限 → 底部抽屜 #m4Quota：全站每日額度＋這個身分每一項有上限的功能「已用／上限・剩幾次」
                （資料只讀 TwPerm.lim／TwPerm.limit／TwQuota.used —— 頁首那顆額度圓環是另一位同事在改，這裡不碰）
     意見回饋 → support.js 的客服面板（TwSupport.open()；客服浮動鈕關掉時照樣打得開）
     客服功能 → 開關（10-09 09:2x Andy：「客服按鈕改成『客服功能』」，只改名、開關行為不變）：關＝右下角客服浮動鈕藏起來（localStorage tw.fab.off＝'1'；<html class="fab-off">，index.html 開頭就先套用，不會先閃一下）
     版面風格 → 收合群組（預設收起）：三套版面風格（親和休閒／科技 HUD／專業有力），點了就是 window.T4.set()，跟原本外觀面板同一支
                （10-09 08:4x Andy 圖一＋圖二：「將紅框改成這功能（明暗切換）／風格在圖二改」——明暗改由頂欄那顆 ☀／🌙 直接切，
                 原本「深色模式」開關這一列改成「風格」；頂欄的外觀調色盤鈕 #t4Btn 在手機藏起來，不留兩顆重複的入口）
     管理區 › → 只有管理員／站主看得到；收合群組（預設收起），裡面是原本的四～五項
     （使用條款／隱私權政策／免責聲明那一列 10-09 08:4x 拿掉：Andy 圖三「拿掉」，頁尾已經有這三個連結）
     刪除帳號 → 紅字；二次確認要輸入「刪除」才按得下去；呼叫 account-api 既有的 POST /v1/delete；站主帳號停用並說明原因
     登出     → 原本的登出
   ============================================================================ */
(function () {
  'use strict';
  const K_FAB = 'tw.fab.off';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：這次有效 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const A = () => window.TwAccount || null;
  const P = () => window.TwPerm || null;
  const Q = () => window.TwQuota || null;
  const F = () => window.TwFeatures || null;

  /* ---------------- 客服浮動鈕開關（全站生效；入口只在手機選單） ---------------- */
  const fabOff = () => ls.get(K_FAB) === '1';
  function setFab(off) {
    if (off) ls.set(K_FAB, '1'); else ls.del(K_FAB);
    document.documentElement.classList.toggle('fab-off', !!off);
  }
  document.documentElement.classList.toggle('fab-off', fabOff());

  /* ---------------- 身分 ---------------- */
  /* 方案徽章四種顏色：訪客灰、註冊會員青、付費依 pricing.js 的方案色（Plus 藍、Pro 紫，方案多了自動換色）；站主琥珀、管理紅 */
  function who() {
    const a = A(), u = a && a.on && a.on() ? a.user() : null;
    const st = P() ? P().state() : { who: 'guest', plan: '', planName: '' };
    if (!u) return { u: null, tier: 'guest', label: '訪客', plan: 'guest' };
    if (u.owner) return { u, tier: 'owner', label: '站主', plan: 'owner' };
    if (!st.plan || st.plan === 'free' || st.who === 'guest') return { u, tier: 'free', label: '註冊會員', plan: 'free' };
    const pb = window.TwPlanBadge ? window.TwPlanBadge() : '';
    const pc = (/\bpc-([a-z]+)/.exec(pb) || [])[1] || (/pro/i.test(st.plan) ? 'violet' : 'blue');
    return { u, tier: 'paid', label: st.planName || st.plan, plan: st.plan, pc };
  }
  function badges(w) {
    const c = w.tier === 'paid' ? ' pc-' + w.pc : '';
    let h = `<a href="#pricing" class="planbadge m4pb t-${w.tier}${c}" data-plan="${esc(w.plan)}" title="查看方案">${esc(w.label)}</a>`;
    if (w.u && w.u.admin && !w.u.owner) h += '<span class="m4role" data-role="admin">管理</span>';
    return h;
  }

  /* ---------------- 額度清單（額度上限頁與選單右側的「今日剩」共用） ---------------- */
  const UNIT_TXT = { tab: '切分頁', filter: '篩選', drill: '下鑽', obj: '看' };
  /* 這個身分所有「有上限」的功能：
       daily：每日次數（範本 lims 有寫、而且不是不限；0＝不開放）＋最上面的全站每日額度（quota.all＝範本 dq）
       count：同時數量上限（features.js kind:'limit'，例如自選分頁數、每頁檔數、同時選幾個族群）—— 比該項最大值小才算「有上限」
     站主／預覽版：TwPerm.lim 一律 Infinity、limit 一律最大值 → 兩份都空。*/
  function quotaItems() {
    const p = P(), q = Q(), Ft = F(); const out = { all: null, daily: [], count: [] };
    if (!p || !Ft) return out;
    const used = (id) => (q && q.used ? q.used(id).length : 0);
    const n0 = p.lim('quota.all');
    if (n0 !== Infinity) { const u = Math.min(n0, used('quota.all')); out.all = { id: 'quota.all', name: '研究瀏覽（全站共用）', unit: '看', used: u, lim: n0, rem: Math.max(0, n0 - u) }; }
    const st = p.state();
    Object.keys(st.lims || {}).forEach((id) => {
      /* 族群觀測（cat 'grp'）不列：跟桌機頁首「本頁限制」（quota.js pageItems）同一個口徑 —— 族群項目是每個族群一個鍵（上百個），
         而且要等 groups_today.json 載入（addGroups）才查得到名字，列進來筆數會忽多忽少；族群的開關由族群頁與下拉的鎖頭負責。 */
      const f = Ft.byId(id); if (!f || f.kind === 'limit' || f.cat === 'grp') return;
      const n = p.lim(id); if (n === Infinity) return;
      const u = Math.min(n, used(id));
      out.daily.push({ id, cat: f.cat, name: f.name, unit: UNIT_TXT[f.act] || '看', used: u, lim: n, rem: Math.max(0, n - u) });
    });
    Ft.list.forEach((f) => {
      if (f.kind !== 'limit') return;
      const v = p.limit(f.id, f.max);
      if (typeof v === 'number' && v < f.max) out.count.push({ id: f.id, cat: f.cat, name: f.name, unit: f.unit || '', lim: v, cnt: true });
    });
    return out;
  }
  const quotaCount = () => { const o = quotaItems(); return (o.all ? 1 : 0) + o.daily.length + o.count.length; };

  /* ---------------- 樣式（只掛在 html.m4 底下：桌機就算載入這支也不受影響） ---------------- */
  function css() {
    if (document.getElementById('acctM4Css')) return;
    const s = document.createElement('style'); s.id = 'acctM4Css';
    s.textContent = `
html.m4 .acctmenu.m4am{left:8px!important;right:8px;width:auto;min-width:0;max-width:none;max-height:calc(100dvh - var(--m4am-top,60px) - 12px);overflow:auto;overscroll-behavior:contain;padding:6px 6px 8px;font-size:15px}
/* 頂欄頭像鈕：mobile4.css 把字級設 0（藏名字與 ▾），但它是 inline-grid —— 「▾」文字節點自成一列，把頭像擠到上半部；
   訪客那顆的「登入」也被字級 0 藏掉，只剩一個空框。這裡改成置中的 flex，訪客畫一個人形圖示。只在 html.m4 生效。*/
html.m4 .m4tools button#acctBtn:is(.abtn){display:inline-flex!important;align-items:center;justify-content:center}
html.m4 .m4tools #acctBtn .ini{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--violet);color:#fff;font-weight:700}
html.m4 .m4tools #acctBtn:not(.ame)::before{content:'';width:22px;height:22px;background:currentColor;
  -webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'%3E%3Ccircle cx='12' cy='8' r='4'/%3E%3Cpath d='M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7'/%3E%3C/svg%3E") center/contain no-repeat;
  mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'%3E%3Ccircle cx='12' cy='8' r='4'/%3E%3Cpath d='M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7'/%3E%3C/svg%3E") center/contain no-repeat}
html.m4 .m4am .mh{display:grid;grid-template-columns:44px 1fr;column-gap:10px;row-gap:2px;align-items:center;padding:10px 8px 12px}
html.m4 .m4am .mh .av{grid-row:span 2;width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:var(--violet);color:#fff;font-weight:700;font-size:18px;overflow:hidden}
html.m4 .m4am .mh .av img{width:100%;height:100%;object-fit:cover}
html.m4 .m4am .mh .av.gst{background:var(--panel-3,#2a3245);color:var(--ink-2)}
html.m4 .m4am .mh .nm{display:flex;align-items:center;gap:6px;min-width:0;flex-wrap:wrap}
html.m4 .m4am .mh .nm b{display:inline;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:16px}
html.m4 .m4am .mh small{font-size:12.5px;color:var(--ink-2);word-break:break-all}
html.m4 .m4am .mh .m4login{grid-column:2;justify-self:start;margin-top:6px;height:36px;padding:0 16px;border-radius:9px;border:0;background:var(--cyan);color:#04121a;font-weight:700;font-size:14px;width:auto;text-align:center}
html.m4 .m4am .planbadge.t-guest{color:var(--ink-2);border:1px solid var(--line-2);background:transparent}
html.m4 .m4am .planbadge.t-free{color:var(--cyan);border:1px solid color-mix(in srgb,var(--cyan) 45%,transparent);background:color-mix(in srgb,var(--cyan) 10%,transparent)}
html.m4 .m4am .m4role{display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:700;color:#ff6b7a;border:1px solid color-mix(in srgb,#ff6b7a 55%,transparent);background:color-mix(in srgb,#ff6b7a 14%,transparent)}
html.m4 .m4am .m4i{display:flex!important;align-items:center;gap:10px;min-height:46px;padding:0 10px!important;font-size:15px!important}
html.m4 .m4am .m4i .t{flex:1;min-width:0}
html.m4 .m4am .m4i .r{color:var(--ink-2);font-size:12.5px;white-space:nowrap}
html.m4 .m4am .m4i .num{min-width:20px;height:20px;padding:0 6px;box-sizing:border-box;border-radius:999px;background:var(--rise);color:#fff;font-size:12px;font-weight:700;line-height:20px;text-align:center}
html.m4 .m4am .m4i .num[hidden]{display:none}
html.m4 .m4am .sw{position:relative;width:42px;height:24px;border-radius:999px;background:var(--line-2);flex:none;transition:background .15s}
html.m4 .m4am .sw::after{content:'';position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:transform .15s}
html.m4 .m4am [aria-checked="true"] .sw{background:var(--cyan)}
html.m4 .m4am [aria-checked="true"] .sw::after{transform:translateX(18px)}
html.m4 .m4am .hr{height:1px;background:var(--line);margin:6px 4px}
html.m4 .m4am .m4grp .chev{transition:transform .15s;color:var(--ink-2)}
html.m4 .m4am .m4grp[aria-expanded="true"] .chev{transform:rotate(90deg)}
html.m4 .m4am .m4sub{padding-left:14px}
html.m4 .m4am .m4sub[hidden]{display:none}
html.m4 .m4am .m4sub button{min-height:42px;font-size:14px}
/* 頂欄：明暗直接由 ☀／🌙（#themeBtn）切；外觀調色盤（#t4Btn）在手機藏起來 —— 風格改從帳號選單的「風格」換（10-09 Andy 圖一＋圖二）*/
html.m4 #m4Tools #t4Btn{display:none!important}
/* 版面風格：同一排分段控制器（10-09 18:1x Andy 帳本 76：「版面改成 同一排分段式開關」）。
   外觀照 style_guide「分段控制器」：一個外框（控制項底＋1px --t4-ctl-edge、圓角 9、內距 3、間距 2）包三格等寬、選中＝ --t4-accent 實心＋ --on-accent 字。
   標題與分段放不下同一排時（分段的最小寬度＝三格中最寬那格的內容 ×3）整組分段自動掉到下一行、撐滿；分段本身永遠單排三格、不截字 */
html.m4 .m4am .m4styrow{display:flex;flex-wrap:wrap;align-items:center;column-gap:10px;row-gap:6px;padding:6px 10px;min-height:46px;box-sizing:border-box}
html.m4 .m4am .m4styrow>.t{flex:1 0 auto;font-size:15px;white-space:nowrap}
html.m4 .m4am .m4seg4{flex:1 0 auto;min-width:max-content;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:2px;padding:3px;box-sizing:border-box;
  border:1px solid var(--t4-ctl-edge,var(--line-2));border-radius:9px;background:var(--t4-ctl,var(--panel-3))}
html.m4 .m4am .m4seg4 button{display:flex!important;align-items:center;justify-content:center;width:auto;min-height:40px;padding:0 9px;border:0;border-radius:7px;
  background:transparent;color:var(--ink-2);font-size:13px;line-height:1.2;white-space:nowrap;text-align:center}
html.m4 .m4am .m4seg4 button:hover{background:transparent}
html.m4 .m4am .m4seg4 button[data-plkb]{opacity:.45}
html.m4 .m4am .m4seg4 button[data-plkb]::after{content:none!important}
html.m4 .m4am .m4seg4 button[aria-checked="true"]{background:var(--t4-accent,var(--cyan));color:var(--on-accent,#04121a);font-weight:700}
html.m4 .m4am .m4del{color:#ff6b7a!important}
html.m4 .m4am .m4del[aria-disabled="true"],html.m4 .m4am .m4off[aria-disabled="true"]{opacity:.55;cursor:not-allowed}
html.m4 .m4am .m4del small{display:block;color:var(--ink-2);font-size:12px;line-height:1.4}
html.m4 .m4am .m4ver{padding:6px 10px 2px;font-size:12px;color:var(--ink-2)}
html.m4 .m4sheet{position:fixed;inset:0;z-index:1450;background:rgba(3,6,14,.55);display:flex;align-items:flex-end}
html.m4 .m4sheet[hidden]{display:none}
html.m4 .m4sheet .bx{width:100%;max-height:86dvh;overflow:auto;overscroll-behavior:contain;background:var(--panel);color:var(--ink);border-radius:16px 16px 0 0;border-top:1px solid var(--line-2);padding:14px 16px calc(16px + env(safe-area-inset-bottom));box-sizing:border-box;font-size:14px}
html.m4 .m4sheet .hd{display:flex;align-items:center;gap:8px;margin-bottom:8px}
html.m4 .m4sheet .hd h3{margin:0;font-size:17px;flex:1}
html.m4 .m4sheet .x{width:40px;height:40px;border-radius:10px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:18px}
html.m4 .m4sheet .lead{margin:0 0 10px;color:var(--ink-2);font-size:13px;line-height:1.55}
html.m4 .m4sheet .qh{margin:14px 0 6px;font-size:13px;color:var(--ink-2);font-weight:700}
html.m4 .m4sheet .qi{padding:10px 0;border-bottom:1px solid var(--line)}
html.m4 .m4sheet .qi .r1{display:flex;gap:8px;align-items:baseline}
html.m4 .m4sheet .qi .r1 b{flex:1;min-width:0;font-weight:600}
html.m4 .m4sheet .qi .r1 span{white-space:nowrap;font-size:13px;color:var(--ink-2)}
html.m4 .m4sheet .qi .r1 em{font-style:normal;font-weight:700;white-space:nowrap}
html.m4 .m4sheet .qi.all{border:1px solid var(--line-2);border-radius:12px;padding:12px;background:var(--panel-2)}
html.m4 .m4sheet .qi.all .r1 b{font-size:15px}
html.m4 .m4sheet .bar{height:6px;border-radius:999px;background:var(--line);margin-top:7px;overflow:hidden}
html.m4 .m4sheet .bar i{display:block;height:100%;background:var(--cyan);border-radius:999px}
html.m4 .m4sheet .qi[data-lvl="low"] em,html.m4 .m4sheet .qi[data-lvl="low"] .bar i{color:var(--amber);background-color:var(--amber)}
html.m4 .m4sheet .qi[data-lvl="out"] em,html.m4 .m4sheet .qi[data-lvl="off"] em{color:#ff6b7a}
html.m4 .m4sheet .qi[data-lvl="out"] .bar i{background:#ff6b7a}
html.m4 .m4sheet .qi[data-lvl="low"] em{background:none}
html.m4 .m4sheet .none{padding:18px 0;color:var(--ink-2)}
html.m4 .m4sheet .ft{display:flex;gap:8px;align-items:center;margin-top:14px;flex-wrap:wrap}
/* 額度上限：標題與底部固定、中間 .sc 自己捲（2026-10-10「太長就用拉Bar」）；只准垂直捲，橫向一律藏 */
html.m4 #m4Quota .bx{display:flex;flex-direction:column;overflow:hidden;padding-bottom:calc(12px + env(safe-area-inset-bottom))}
html.m4 #m4Quota .hd{flex:none}
html.m4 #m4Quota .sc{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;margin-right:-10px;padding-right:10px;
  scrollbar-width:thin;scrollbar-color:color-mix(in srgb,var(--ink-2) 55%,transparent) transparent;
  -webkit-mask-image:none;mask-image:none}
html.m4 #m4Quota .sc::-webkit-scrollbar{width:5px}
html.m4 #m4Quota .sc::-webkit-scrollbar-thumb{background:color-mix(in srgb,var(--ink-2) 55%,transparent);border-radius:999px}
html.m4 #m4Quota .bx.more .sc{-webkit-mask-image:linear-gradient(#000 calc(100% - 36px),transparent);mask-image:linear-gradient(#000 calc(100% - 36px),transparent)}
html.m4 #m4Quota .ft{flex:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
html.m4 #m4Quota .bx.more .ft small::before{content:'往下滑看更多 ↓・';color:var(--ink)}
html.m4 #m4Quota .qh{display:flex;align-items:baseline;gap:8px}
html.m4 #m4Quota .qh small{margin-left:auto;font-weight:400;font-size:12px}
html.m4 #m4Quota .qg{border:1px solid var(--line);border-radius:12px;margin:0 0 8px;background:var(--panel-2);overflow:hidden}
html.m4 #m4Quota .qgh{display:flex;align-items:center;gap:8px;width:100%;min-height:48px;padding:8px 12px;border:0;background:none;color:var(--ink);font:inherit;text-align:left;cursor:pointer}
html.m4 #m4Quota .qgh .t{font-weight:700;font-size:15px;white-space:nowrap}
html.m4 #m4Quota .qgh small{color:var(--ink-2);font-size:12px;white-space:nowrap}
html.m4 #m4Quota .qgh .s{flex:1;min-width:0;display:flex;flex-wrap:wrap;justify-content:flex-end;gap:4px 8px}
html.m4 #m4Quota .qgh .s em{font-style:normal;font-size:12px;color:var(--ink-2);white-space:nowrap}
html.m4 #m4Quota .qgh .s em.low{color:var(--amber)}
html.m4 #m4Quota .qgh .s em.out{color:#ff6b7a}
html.m4 #m4Quota .qgh .s em.pl{color:var(--amber)}
html.m4 #m4Quota .qgh i{font-style:normal;color:var(--ink-2);font-size:18px;line-height:1;transition:transform .15s}
html.m4 #m4Quota .qgh[aria-expanded="true"] i{transform:rotate(90deg)}
html.m4 #m4Quota .qgb{padding:0 12px 4px;border-top:1px solid var(--line)}
html.m4 #m4Quota .qgb .qi:last-child{border-bottom:0}
html.m4 #m4Quota .qi .r1{align-items:center}
html.m4 #m4Quota .qplan{flex:none;display:inline-flex;align-items:center;height:24px;padding:0 10px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap;
  color:var(--amber);background:color-mix(in srgb,var(--amber) 14%,transparent);border:1px solid color-mix(in srgb,var(--amber) 45%,transparent)}
html.m4 #m4Quota .qplan::before{content:'★';margin-right:4px;font-size:11px}
html.m4 .m4sheet .ft small{flex:1;color:var(--ink-2);font-size:12.5px;min-width:10em}
html.m4 .m4sheet .go{height:40px;padding:0 16px;border-radius:10px;border:0;background:var(--cyan);color:#04121a;font-weight:700;font-size:14px;text-decoration:none;display:inline-flex;align-items:center}
html.m4 .m4deldlg .box{font-size:14px}
html.m4 .m4deldlg input{width:100%;height:42px;box-sizing:border-box;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:16px;padding:0 12px;margin:6px 0 2px}
html.m4 .m4deldlg .danger:disabled{opacity:.45;cursor:not-allowed}
html.m4 .m4deldlg .msg{min-height:1.4em;font-size:13px;color:#ff6b7a;margin:4px 0 0}`;
    document.head.appendChild(s);
  }

  css();   // 一開始就掛：頂欄頭像鈕的修正要在選單打開之前生效（規則全部限定 html.m4，桌機不受影響）

  /* ---------------- 選單內容 ---------------- */
  const ver = () => { const b = document.getElementById('buildver'); const t = b && b.textContent.trim(); if (t) return t; const m = document.querySelector('meta[name="tw:build"]'); return 'v ' + (((m && m.content) || 'dev').split('|')[0] || 'dev'); };
  /* 版面風格：清單讀 theme4.js 的 T4.THEMES（只有 id），名稱照外觀面板的寫法 */
  const STY = { casual: ['親和休閒', 'linear-gradient(135deg,#FFE8DA,#6A55E6)'], hud: ['科技 HUD', 'linear-gradient(135deg,#050A13,#37E2FF)'], pro: ['專業有力', 'linear-gradient(135deg,#0A0C10,#2E5BDB)'] };
  const styIds = () => ((window.T4 && window.T4.THEMES) || Object.keys(STY)).filter((k) => STY[k]);
  const styCur = () => (window.T4 && window.T4.get ? window.T4.get() : (document.documentElement.getAttribute('data-theme4') || 'hud'));
  const styName = (k) => (STY[k] || [k])[0];
  const unread = () => { try { return window.TwNotices && window.TwNotices.unread ? window.TwNotices.unread() : 0; } catch (e) { return 0; } };
  function remText() {
    const o = quotaItems();
    if (o.all) return `今日剩 ${o.all.rem}／${o.all.lim}`;
    const n = o.daily.length + o.count.length;
    return n ? `${n} 項` : '不限';
  }
  function html() {
    const w = who(), u = w.u, a = A();
    const ini = esc(((u && (u.name || u.email)) || '?').trim().charAt(0).toUpperCase());
    const av = u ? (u.pic ? `<span class="av" aria-hidden="true"><img src="${esc(u.pic)}" alt="" referrerpolicy="no-referrer"></span>` : `<span class="av" aria-hidden="true">${ini}</span>`)
      : '<span class="av gst" aria-hidden="true">訪</span>';
    const head = u
      ? `<div class="mh mhx">${av}<span class="nm"><b>${esc(u.name || u.email || '')}</b>${badges(w)}</span><small>${esc(u.email || '')}</small></div>`
      : `<div class="mh mhx">${av}<span class="nm"><b>訪客</b>${badges(w)}</span><small>登入後自選清單可跨裝置同步、每日次數更多</small>`
        + (a && a.on && a.on() ? '<button type="button" class="m4login" data-m="login">登入／註冊</button>' : '') + '</div>';
    const n = unread();
    const sw = (k, on, t) => `<button type="button" class="m4i" role="menuitemcheckbox" aria-checked="${on}" data-m="${k}"><span class="t">${t}</span><span class="sw" aria-hidden="true"></span></button>`;
    let h = head
      + `<button type="button" class="m4i" role="menuitem" data-m="pricing"><span class="t">訂閱方案</span><span class="r">目前：${esc(w.label)}</span></button>`
      + (window.TwBilling ? window.TwBilling.menuHTML('m4') : '')   // 取消訂閱／申請退款（帳本 48；付費方案才有、站主停用）
      + `<button type="button" class="m4i" role="menuitem" data-m="notify"><span class="t">通知</span><span class="num" ${n ? '' : 'hidden'} aria-label="${n} 則未讀">${n > 99 ? '99+' : n}</span></button>`
      + `<button type="button" class="m4i" role="menuitem" data-m="quota"><span class="t">額度上限</span><span class="r">${esc(remText())}</span></button>`
      + `<button type="button" class="m4i" role="menuitem" data-m="feedback"><span class="t">意見回饋</span></button>`
      + sw('fab', !fabOff(), '客服功能')
      + '<div class="m4styrow" data-m="style"><span class="t" id="m4StyLbl">版面風格</span>'
      + '<div class="m4seg4" role="radiogroup" aria-labelledby="m4StyLbl">' + styIds().map((k) => `<button type="button" role="radio" aria-checked="${k === styCur()}" data-m="sty" data-sty="${k}">${esc(styName(k))}</button>`).join('') + '</div></div>';
    if (u && u.admin) {
      h += '<div class="hr"></div><button type="button" class="m4i m4grp" role="menuitem" aria-expanded="false" data-m="admgrp"><span class="t">管理區</span><span class="chev" aria-hidden="true">›</span></button>'
        + '<div class="m4sub" hidden>'
        + '<button type="button" role="menuitem" data-a="feedback">意見反饋與訂閱申請</button><button type="button" role="menuitem" data-a="notices">公告</button>'
        + '<button type="button" role="menuitem" data-a="admin">流量觀測與線上名單</button><button type="button" role="menuitem" data-a="perm">會員功能權限</button>'
        + (window.TwGw && window.TwGw.on && window.TwGw.on() ? '<button type="button" role="menuitem" data-a="gw">付費資料異常</button>' : '')
        + '</div>';
    }
    /* 選單最下方一律有「刪除帳號」（紅字）與「登出」兩列（10-09 09:2x Andy：「下方需要多出刪除功能以及登出功能」）：
       訪客＝兩列都顯示但停用、寫「登入後可用」；站主＝刪除帳號停用並說明原因；其他登入會員照常可按 */
    h += '<div class="hr"></div>';
    if (u) {
      const own = !!u.owner;
      h += `<button type="button" class="m4i m4del" role="menuitem" data-m="del"${own ? ' aria-disabled="true"' : ''}><span class="t">刪除帳號${own ? '<small>站主帳號不可刪除：網站的最高管理權限綁在這個帳號上，刪了管理區就沒有擁有者</small>' : ''}</span></button>`
        + '<button type="button" class="m4i" role="menuitem" data-a="logout"><span class="t">登出</span></button>';
    } else {
      h += '<button type="button" class="m4i m4del" role="menuitem" data-m="del" aria-disabled="true"><span class="t">刪除帳號</span><span class="r">登入後可用</span></button>'
        + '<button type="button" class="m4i m4off" role="menuitem" data-m="logout" aria-disabled="true"><span class="t">登出</span><span class="r">登入後可用</span></button>';
    }
    h += `<div class="m4ver">${esc(ver())}</div>`;
    return h;
  }

  /* account.js openMenu() 在 html.m4 時呼叫：畫內容＋定位（貼頂欄下緣、左右各留 8px）*/
  function paint(m, anchor) {
    css();
    m.classList.add('m4am');
    m.innerHTML = html();
    const img = m.querySelector('.mh .av img');
    if (img) img.onerror = () => { const p = img.parentNode; const u = who().u; p.textContent = ((u && (u.name || u.email)) || '?').trim().charAt(0).toUpperCase(); };
    if (!m._m4) {
      m._m4 = true;
      m.addEventListener('click', onClick);
    }
    const bar = document.querySelector('.topbar');
    const top = Math.round(Math.max(anchor ? anchor.getBoundingClientRect().bottom : 0, bar ? bar.getBoundingClientRect().bottom : 0) + 6);
    m.style.top = top + 'px'; m.style.left = '8px';
    m.style.setProperty('--m4am-top', top + 'px');
    m.hidden = false;
  }
  function close() { const m = document.getElementById('acctMenu'); if (m) m.hidden = true; }
  function onClick(e) {
    const m = e.currentTarget; if (!m.classList.contains('m4am')) return;
    const b = e.target.closest('[data-m]'); if (!b) return;
    const k = b.dataset.m;
    if (k === 'fab') { const off = !fabOff(); setFab(off); b.setAttribute('aria-checked', String(!off)); return; }
    if (k === 'style') return;   // 版面風格那一列的空白處：不做事（只有三格分段可點）
    if (k === 'sty' && (b.dataset.plkb === 'block' || (P() && P().can && !P().can('theme')))) return;   // 「主題外觀」被方案關掉：perm.js 捕獲階段已經擋下並提示；這裡再保險一次
    if (k === 'sty') {   // 選了就套用（T4.set 會存 tw.theme4、重畫圖表），選單留著讓人看到選中格換了
      if (window.T4 && window.T4.set) window.T4.set(b.dataset.sty);
      const cur = styCur();
      m.querySelectorAll('[data-m=sty]').forEach((x) => x.setAttribute('aria-checked', String(x.dataset.sty === cur)));
      return;
    }
    if (k === 'admgrp') { const sub = b.nextElementSibling; const open = b.getAttribute('aria-expanded') !== 'true'; b.setAttribute('aria-expanded', String(open)); if (sub) sub.hidden = !open; return; }
    if (b.getAttribute('aria-disabled') === 'true') return;   // 停用的列（站主的刪除帳號、訪客的刪除帳號與登出）：點了不做事
    close();
    if (k === 'login') { const a = A(); if (a && a.login) a.login(); }
    else if (k === 'pricing') location.hash = '#pricing';
    else if (k === 'notify') location.hash = '#notices';
    else if (k === 'quota') openQuota();
    else if (k === 'feedback') { if (window.TwSupport && window.TwSupport.open) window.TwSupport.open(); }
    else if (k === 'del') openDel();
  }

  /* ---------------- 額度上限（底部抽屜） ----------------
     ★ 2026-10-10 Andy：「額度上限使用收合功能將每個母分頁內所有有限制的功能標示出來，太長就用拉Bar。
       不要寫"不開放" 幫我改成plus 會員 這樣比較親切」
     · 全站每日額度維持在最上面（不收合）；下面依「母分頁」（側欄那一層：總覽、資金流向、熱力圖、產業地圖、個股、ETF…）一組一個收合區塊，
       標題＝分頁名＋項目數＋一句狀態（最少剩幾次／幾項要升級）；組內列出每日次數、同時數量上限、上限 0 的項目。
     · 功能歸哪一頁：沿用 quota.js 的 onPage()（PAGE_OF 精確對子分頁、其餘依分類對頁名），拿每一頁的代表網址去問，不另寫一套對照。
       對不到任何一頁的（全站工具、族群觀測）依 features.js 的分類名自成一組，排最後。
     · 收合預設收起（全站準則五）；只有一組時直接展開；使用者手動展開過的記在 localStorage tw.m4quota.open（關掉就刪）。
     · 上限 0 不再寫紅字「不開放」，改成琥珀色小膠囊「<最低有開的方案> 會員」：
       先問 TwPricing.unlockers()（後端方案範本，順序＝方案卡順序：註冊會員 → Plus → Pro）挑第一個；
       方案清單還沒到或只有預設值時，退回 plan_presets.js 的建議方案。都查不到才寫「升級會員」。
     · 面板內容太長：只有中間那段捲（.sc，細捲軸＋底部淡出），標題列與底部「看方案」固定；不准橫向捲動。 */
  const K_QOPEN = 'tw.m4quota.open';
  const QPAGES = [
    ['overview', '總覽', ['#overview']], ['earnings', '財經日曆', ['#earnings']],
    ['flow', '資金流向', ['#flow/rotation', '#flow/sankey', '#flow/inst']], ['heatmap', '熱力圖', ['#heatmap/industry', '#heatmap/theme']],
    ['industry', '產業地圖', ['#industry']], ['stock', '個股', ['#stock/2330']], ['market', '市場明細', ['#market']],
    ['explore', '選股策略', ['#explore']], ['season', '週期統計', ['#season']], ['etf', 'ETF', ['#etf', '#etf/list', '#etf/cal', '#etf/inc']],
    ['watch', '自選', ['#watch']],
  ];
  function pageOf(x) {
    const Qt = Q(), f = F() && F().byId(x.id);
    if (Qt && Qt.onPage && f) { for (const [k, t, hs] of QPAGES) if (hs.some((h) => Qt.onPage(f, h))) return [k, t]; }
    const c = F() && (F().cats || []).find((z) => z.id === x.cat);
    return ['cat-' + (x.cat || 'other'), c ? c.name : '其他'];
  }
  /* 上限 0 的項目：最低哪個方案有開。回「Plus 會員」這種字；查不到回「升級會員」 */
  function presetOff(t, id) { if (t.lims && t.lims[id] === 0) return true; const v = (t.feats || {})[id]; return v === false || v === 0; }
  function needPlan(id) {
    const Pr = window.TwPricing, st = Pr && Pr.state ? Pr.state() : null;
    const lab = (p) => (p.id === 'free' ? '註冊會員' : String(p.name || p.id).replace(/\s*會員$/, '') + ' 會員');
    if (st && (st.src === 'server' || st.src === 'demo') && Pr.unlockers) {
      const cur = P() ? P().state().plan : '';
      const u = (Pr.unlockers(id) || []).filter((p) => p.id !== cur);
      if (u.length) return lab(u[0]);
    }
    const pr = window.TW_PLAN_PRESETS, tiers = pr && Array.isArray(pr.tiers) ? pr.tiers : [];
    const t = tiers.find((z) => z.key !== 'guest' && !presetOff(z, id));
    return t ? lab({ id: t.key, name: t.name }) : '升級會員';
  }
  const qOpen = () => { try { const v = JSON.parse(ls.get(K_QOPEN) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
  function openQuota() {
    css();
    let d = document.getElementById('m4Quota');
    if (!d) {
      d = document.createElement('div'); d.id = 'm4Quota'; d.className = 'm4sheet'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '額度上限');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => {
        const g = e.target.closest('[data-qg]');
        if (g) {   // 分組標題：展開／收起；記住使用者手動展開的那幾組
          const open = g.getAttribute('aria-expanded') !== 'true', b = g.nextElementSibling;
          g.setAttribute('aria-expanded', String(open)); if (b) b.hidden = !open;
          const s = new Set(qOpen()); if (open) s.add(g.dataset.qg); else s.delete(g.dataset.qg);
          if (s.size) ls.set(K_QOPEN, JSON.stringify([...s])); else ls.del(K_QOPEN);
          qFade(d);
          return;
        }
        if (e.target === d || e.target.closest('[data-x]') || e.target.closest('a[href]')) d.hidden = true;
      });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !d.hidden) d.hidden = true; });
      window.addEventListener('hashchange', () => { d.hidden = true; });
      /* 方案清單晚到（第一次開面板才去抓）→ 膠囊上的方案名重畫一次；展開狀態照 DOM 保留 */
      window.addEventListener('tw:plans', () => { if (!d.hidden) d.querySelectorAll('.qplan[data-need]').forEach((e) => { e.textContent = needPlan(e.dataset.need); }); });
    }
    if (window.TwPricing && window.TwPricing.ensure) window.TwPricing.ensure();
    const w = who(), o = quotaItems();
    const lvl = (x) => (x.lim === 0 ? 'off' : x.cnt ? 'ok' : x.rem === 0 ? 'out' : x.rem === 1 ? 'low' : 'ok');
    const plan = (x) => `<span class="qplan" data-need="${esc(x.id)}">${esc(needPlan(x.id))}</span>`;
    const row = (x, cls) => `<div class="qi${cls || ''}" data-id="${esc(x.id)}" data-lvl="${lvl(x)}"><div class="r1"><b>${esc(x.name)}</b>`
      + (x.lim === 0 ? plan(x) : x.cnt ? `<span>同時最多 ${x.lim} ${esc(x.unit)}</span>` : `<span>${esc(x.unit)}・已用 ${x.used}／${x.lim}</span><em>剩 ${x.rem} 次</em>`)
      + `</div>${x.lim === 0 || x.cnt ? '' : `<div class="bar"><i style="width:${Math.round((x.used / Math.max(1, x.lim)) * 100)}%"></i></div>`}</div>`;
    /* 分組：照 QPAGES 的順序，對不到頁的接在後面 */
    const groups = new Map();
    QPAGES.forEach(([k, t]) => groups.set(k, { k, t, xs: [] }));
    o.daily.concat(o.count).forEach((x) => { const [k, t] = pageOf(x); if (!groups.has(k)) groups.set(k, { k, t, xs: [] }); groups.get(k).xs.push(x); });
    const gs = [...groups.values()].filter((g) => g.xs.length);
    const remembered = new Set(qOpen());
    const gsum = (g) => {
      const dl = g.xs.filter((x) => !x.cnt && x.lim > 0), off = g.xs.filter((x) => x.lim === 0).length;
      const parts = [];
      if (dl.length) { const m = Math.min(...dl.map((x) => x.rem)); parts.push(`<em class="${m === 0 ? 'out' : m === 1 ? 'low' : ''}">${m === 0 ? '有項目用完' : `最少剩 ${m} 次`}</em>`); }
      if (off) parts.push(`<em class="pl">${off} 項升級可用</em>`);
      if (!parts.length) parts.push(`<em>${g.xs.length} 項數量上限</em>`);   // 只有「同時最多 N 個」的組：不收合也看得出是哪一種限制
      return parts.join('');
    };
    const grp = (g) => { const open = gs.length === 1 || remembered.has(g.k);
      return `<section class="qg" data-pg="${esc(g.k)}"><button type="button" class="qgh" data-qg="${esc(g.k)}" aria-expanded="${open}">`
        + `<span class="t">${esc(g.t)}</span><small>${g.xs.length} 項</small><span class="s">${gsum(g)}</span><i aria-hidden="true">›</i></button>`
        + `<div class="qgb"${open ? '' : ' hidden'}>${g.xs.map((x) => row(x)).join('')}</div></section>`; };
    const any = o.all || gs.length;
    d.innerHTML = '<div class="bx"><div class="hd"><h3>額度上限</h3><button type="button" class="x" data-x aria-label="關閉">✕</button></div>'
      + '<div class="sc">'
      + `<p class="lead">目前身分：<b>${esc(w.label)}</b>。依分頁列出每一項有上限的功能；同一個對象同一天重複看不重算。</p>`
      + (!any ? '<p class="none">你的方案沒有任何次數或數量上限。</p>' : '')
      + (o.all ? '<div class="qh">全站每日額度</div>' + row(o.all, ' all') : '')
      + (gs.length ? `<div class="qh">各分頁的限制（${o.daily.length + o.count.length} 項）<small>點分頁展開</small></div>` + gs.map(grp).join('') : '')
      + '</div>'
      + `<div class="ft"><small>每天台北時間 00:00 重置</small>${w.tier === 'owner' ? '' : '<a class="go" href="#pricing">看方案</a>'}</div></div>`;
    d.hidden = false;
    const sc = d.querySelector('.sc');
    if (sc && !sc._m4) { sc._m4 = true; sc.addEventListener('scroll', () => qFade(d), { passive: true }); }
    qFade(d);
  }
  /* 中間那段還有內容在下面 → 底部淡出＋「往下滑看更多」；捲到底就拿掉 */
  function qFade(d) {
    const sc = d.querySelector('.sc'); if (!sc) return;
    d.querySelector('.bx').classList.toggle('more', sc.scrollHeight - sc.clientHeight - sc.scrollTop > 4);
  }

  /* ---------------- 刪除帳號（二次確認） ---------------- */
  function openDel() {
    css();
    const w = who(); if (!w.u || w.u.owner) return;
    let d = document.getElementById('m4Del');
    if (!d) {
      d = document.createElement('div'); d.id = 'm4Del'; d.className = 'acctdlg m4deldlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '刪除帳號');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => { if (e.target === d || e.target.closest('[data-close]')) d.hidden = true; if (e.target.closest('#m4DelYes')) doDel(d); });
      d.addEventListener('input', () => { const y = d.querySelector('#m4DelYes'); if (y) y.disabled = d.querySelector('#m4DelTxt').value.trim() !== '刪除'; });
      d.addEventListener('keydown', (e) => { if (e.key === 'Escape') d.hidden = true; });
    }
    const paid = w.tier === 'paid';
    d.innerHTML = `<div class="box"><h3>刪除帳號</h3>
      <p>會<b>立即、永久</b>刪除這個帳號（${esc(w.u.email || '')}）在本站的資料，<b>無法復原</b>：</p>
      <ul>
        <li>會員資料：名稱、email、大頭貼網址</li>
        <li>雲端自選清單（所有分頁）</li>
        <li>線上狀態、個人使用明細、今日次數紀錄</li>
        <li>意見反饋、訂閱申請、公告已讀紀錄</li>
        <li>方案與功能權限${paid ? `（你目前是 <b>${esc(w.label)}</b>：刪除後方案立即失效；已付的費用不會自動退款，有需要請先用「意見回饋」聯絡我們）` : ''}</li>
      </ul>
      <p class="muted">不受影響：這台裝置上的本機設定與本機自選（要清除請用瀏覽器的「清除網站資料」）；不記名的全站使用次數統計。若你用過退款保證（目前不提供免費試用），會另存一組無法還原成信箱的比對碼 365 天，防止重新註冊後重複使用。之後再用同一個 Google 帳號登入，會是一個全新的註冊會員。</p>
      <label for="m4DelTxt">請輸入「刪除」兩個字確認</label>
      <input id="m4DelTxt" type="text" autocomplete="off" inputmode="text" placeholder="刪除">
      <p class="msg" id="m4DelMsg" role="status"></p>
      <div class="row2"><button type="button" data-close>取消</button><button type="button" class="danger" id="m4DelYes" disabled>永久刪除帳號</button></div></div>`;
    d.hidden = false;
  }
  async function doDel(d) {
    const y = d.querySelector('#m4DelYes'), msg = d.querySelector('#m4DelMsg');
    if (!y || y.disabled) return;
    y.disabled = true; msg.textContent = '刪除中…';
    const a = A();
    const j = a && a.call ? await a.call('/v1/delete', {}) : null;
    if (j && j.deleted) {
      d.hidden = true;
      if (a.signedOut) a.signedOut('你的帳號與雲端資料已經刪除');
      location.hash = '#overview';
      return;
    }
    /* 失敗一律白話講原因，不要只丟狀態碼：Worker 還沒更新（404）、站主（403 owner）、權杖過期（401，call() 已經當作登出）、連不到 */
    msg.textContent = !j ? '連不到會員系統，請確認網路後再試一次。'
      : j._s === 404 ? '刪除帳號功能還沒在伺服器上開放，請稍後再試，或用「意見回饋」請我們代為刪除。'
      : j._s === 403 && j.error === 'owner' ? '站主帳號不可刪除。'
      : j._s === 401 ? '登入已過期，請重新登入後再刪除。'
      : `刪除沒有成功（${j._s}），請稍後再試。`;
    y.disabled = j && j._s === 401 ? true : false;
  }

  /* 選單開著時身分／權限／公告換了：重畫（徽章與額度常常比選單晚一步到） */
  const repaint = () => { const m = document.getElementById('acctMenu'); if (m && !m.hidden && m.classList.contains('m4am') && document.documentElement.classList.contains('m4')) { const was = ['admgrp'].filter((k) => { const g = m.querySelector(`[data-m=${k}]`); return g && g.getAttribute('aria-expanded') === 'true'; }); paint(m, null); was.forEach((k) => { const g = m.querySelector(`[data-m=${k}]`); if (g) g.click(); }); } };
  ['tw:perm', 'tw:account', 'tw:plans'].forEach((ev) => window.addEventListener(ev, repaint));

  window.TwAcctM4 = { paint, openQuota, openDel, quotaItems, quotaCount, who, setFab, fabOff };
})();
