/* ============================================================================
   產貼文頻率設定（管理區 #admin/articles「文章主題」分頁最下面那張卡）—— 2026-10-16 建，同日晚改第 2 版
   ----------------------------------------------------------------------------
   Andy 2026-10-16 第 2 版：「這邊設計好糟糕 應該是可以選擇 日期 後面是時段以小時為單位， 10:00 AM/PM 這樣
   然後接者是產的類型選擇，啟用應該是這邊都選完才會輪到，不應該是這樣順序 … 這裡好亂」。
   第 1 版的毛病：啟用開關排第一步（還沒設定就叫你開）、時段只有三輪固定時間 × 星期格子、類別篇數跟時段分兩塊看不出哪個時段產什麼。

   這一塊回答的問題：「哪幾天的幾點，Claude 要自動幫我產哪幾類精選文章、各幾篇？」
   所以怎麼用（畫面由上而下就是操作順序）：
     ① 日期：每週重複（星期多選＋「每天」「週一至五」快捷）或 指定日期（挑日曆日、變成可刪的小標籤；過去的日期不能選）
     ② 時段：整點、12 小時制「10:00 AM」，上午一排、下午一排，可多選（台北時間）
     ③ 產出類型與篇數：比比快訊／產業鏈／知識 各 0～3 篇
     ④ 加入排程：①＋②＋③ 組成一條「規則」放進下方清單（缺什麼按鈕旁邊寫明）；清單每列可「編輯」帶回上面、可「刪除」；最多 20 條
     ⑤ 啟用：清單至少一條才能開
   儲存：規則增刪改、切開關都**當下自動存**（不再有「儲存」鈕 —— 第 1 版「有的要按儲存、有的切了就存」讓人搞不清楚），
   ⑤ 旁邊永遠寫目前狀態：「已儲存 21:40」／「儲存中…」／「沒存成功＋原因＋重試」。
   資料流：會員 Worker /v1/articles/schedule/add（只有管理者；格式 {ver:2, enabled, rules}）→ article-jobs.yml 每小時 :41 讀它，
     到點的規則排進「產出進度」→ Claude 排程（台北每小時 :05）處理。細節 docs/articles/production_guide.md。
   Worker 讀到第 1 版設定會自己轉成第 2 版回來，這裡只認第 2 版。
   權限：只有 articles.js 的管理者畫面會呼叫 mount；Worker 端另外驗證管理者。
   預覽版：寫入被 preview_boot.js 擋（preview_readonly）→ 畫面寫「預覽版不會真的儲存」。
   後端還沒部署新版（404）→ 寫「後端還沒更新」，規則留在畫面與瀏覽器草稿（tw.art.sched.draft2），不丟。
   安全：所有字串 esc() 後才放進畫面。
   驗收：scripts/uitest_sections/20261016_artsched_v2.py（真人照順序操作）＋ _uitest「文章主題兩分頁1016」。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const WD = ['一', '二', '三', '四', '五', '六', '日'];
  const LS = 'tw.art.sched.draft2';
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } };

  /* 台北時間工具（容器／使用者電腦時區不一定是台北，一律用 UTC+8 算） */
  const tpeNow = () => new Date(Date.now() + 8 * 3600e3);
  const todayTpe = () => tpeNow().toISOString().slice(0, 10);
  const wdOf = (ymd) => { const d = new Date(ymd + 'T00:00:00Z').getUTCDay(); return d === 0 ? 7 : d; };
  const hourLabel = (h) => `${h % 12 === 0 ? 12 : h % 12}:00 ${h < 12 ? 'AM' : 'PM'}`;
  const md = (ymd) => `${+ymd.slice(5, 7)}/${+ymd.slice(8, 10)}（${WD[wdOf(ymd) - 1]}）`;
  const stamp = (ms) => { const d = new Date(Number(ms) + 8 * 3600e3).toISOString(); const t = d.slice(11, 16); return d.slice(0, 10) === todayTpe() ? t : d.slice(5, 10) + ' ' + t; };

  /* 狀態
     draft：①②③ 正在組的那一條（mode 'days'｜'dates'）；edit：正在編輯第幾條（-1＝新增）
     rules／enabled：清單與開關（＝要存到伺服器的那一份）；saved：伺服器上那一份的指紋（判斷「畫面跟已儲存的一不一致」） */
  const blank = () => ({ mode: 'days', days: [], dates: [], hours: [], cats: { news: 0, intro: 0, know: 0 } });
  const S = { draft: blank(), edit: -1, rules: [], enabled: false, hours: Array.from({ length: 24 }, (_, i) => i), max: 3, maxRules: 20, maxDates: 31,
    saved: null, savedAt: null, backend: 'loading', note: '', noteErr: false, busy: false, again: false };
  let O = { call: () => Promise.resolve(null), cats: [['news', '比比快訊'], ['intro', '比比產業鏈'], ['know', '比比知識']] };
  const short = (n) => String(n).replace(/^比比/, '');

  const fp = () => JSON.stringify({ e: !!S.enabled, r: S.rules });
  const sortN = (a) => Array.from(new Set(a)).sort((x, y) => x - y);
  const sortS = (a) => Array.from(new Set(a)).sort();
  /* 把畫面上那一條整理成要送出的形狀（跟 Worker 的 cleanRule 一樣：排序、去重、三類都帶） */
  function ruleOf(d) {
    const r = d.mode === 'dates' ? { dates: sortS(d.dates) } : { days: sortN(d.days) };
    r.hours = sortN(d.hours);
    r.cats = {}; O.cats.forEach(([k]) => { r.cats[k] = d.cats[k] || 0; });
    return r;
  }
  const sameRule = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  /* 還缺什麼（空陣列＝可以加入） */
  function lack() {
    const d = S.draft, a = [];
    if (!(d.mode === 'dates' ? d.dates.length : d.days.length)) a.push(d.mode === 'dates' ? '① 至少挑一個日期' : '① 至少選一個星期');
    if (!d.hours.length) a.push('② 至少選一個時段');
    if (!O.cats.some(([k]) => d.cats[k] > 0)) a.push('③ 至少一類 1 篇以上');
    if (S.edit < 0 && S.rules.length >= S.maxRules) a.push(`清單已滿 ${S.maxRules} 條，先刪掉一條`);
    return a;
  }
  /* 一條規則的白話：日期｜時段｜產什麼 */
  function dayText(r) {
    if (r.dates) return r.dates.map(md).join('、');
    const d = r.days.join(',');
    if (d === '1,2,3,4,5,6,7') return '每天';
    if (d === '1,2,3,4,5') return '每週一至五';
    if (d === '6,7') return '每週六、日';
    return '每週' + r.days.map((n) => WD[n - 1]).join('、');
  }
  const hourText = (r) => r.hours.map(hourLabel).join('、');
  const catText = (r) => O.cats.filter(([k]) => r.cats[k] > 0).map(([k, n]) => short(n) + ' ' + r.cats[k]).join('、');
  const expired = (r) => !!r.dates && r.dates.every((x) => x < todayTpe());

  const BACK = {
    old: '後端還沒更新到新版（會員 Worker 尚未部署），現在存不進去；清單先留在這個畫面與瀏覽器草稿。',
    off: '連不到會員伺服器，清單先留在這個畫面與瀏覽器草稿。', denied: '登入身分不是管理者（請重新登入）。',
    preview: '預覽版不會真的儲存（寫入被擋下），只用來看畫面。',
  };

  function html() {
    const tday = todayTpe();
    const hb = (h) => `<button type="button" class="hb" data-h="${h}" aria-pressed="false">${hourLabel(h)}</button>`;
    const am = S.hours.filter((h) => h < 12), pm = S.hours.filter((h) => h >= 12);
    return `<div class="card artadm asd" id="artSchedCard">
  <div class="hd"><h3>產貼文頻率設定</h3><span class="muted" id="asdLead">到點後最多約 1 小時內，Claude 會自動把文章排進上面的產出進度</span></div>
  <ol class="asd-steps">
    <li class="asd-st" id="asdStep1"><div class="asd-lb"><b class="asd-n">1</b><span>選日期</span></div><div class="asd-bd">
      <div class="asd-seg" role="tablist" aria-label="日期方式"><button type="button" role="tab" data-mode="days" id="asdModeDays">每週重複</button><button type="button" role="tab" data-mode="dates" id="asdModeDates">指定日期</button></div>
      <div class="asd-pane" data-pane="days"><div class="asd-days" id="asdDays">${[1, 2, 3, 4, 5, 6, 7].map((d) => `<button type="button" class="dd" data-d="${d}" aria-pressed="false" aria-label="週${WD[d - 1]}">${WD[d - 1]}</button>`).join('')}</div>
        <div class="asd-quick"><button type="button" data-q="all">每天</button><button type="button" data-q="work">週一至五</button><button type="button" data-q="none">清除</button></div></div>
      <div class="asd-pane" data-pane="dates" hidden><div class="asd-dpick"><input type="date" id="asdDate" min="${tday}" value="${tday}" aria-label="挑日期"><button type="button" id="asdDateAdd">加入這天</button><span class="asd-tip" id="asdDateTip" role="status"></span></div>
        <div class="asd-chips" id="asdChips"></div></div>
    </div></li>
    <li class="asd-st" id="asdStep2"><div class="asd-lb"><b class="asd-n">2</b><span>選時段</span><small>台北時間・可多選</small></div><div class="asd-bd">
      <div class="asd-hrow"><span class="asd-hl">上午</span><div class="asd-hours" id="asdHoursAm">${am.map(hb).join('')}</div></div>
      <div class="asd-hrow"><span class="asd-hl">下午</span><div class="asd-hours" id="asdHoursPm">${pm.map(hb).join('')}</div></div>
    </div></li>
    <li class="asd-st" id="asdStep3"><div class="asd-lb"><b class="asd-n">3</b><span>產什麼、幾篇</span><small>每個時段各產幾篇</small></div><div class="asd-bd"><div class="asd-cats">
      ${O.cats.map(([k, n]) => `<div class="asd-kr" data-cat="${esc(k)}"><span class="asd-kn">${esc(n)}</span><span class="asd-stp"><button type="button" data-st="-1" aria-label="${esc(n)}減一篇">−</button><input type="number" min="0" max="${S.max}" step="1" inputmode="numeric" data-kn="${esc(k)}" value="0" aria-label="${esc(n)}篇數"><button type="button" data-st="1" aria-label="${esc(n)}加一篇">＋</button></span></div>`).join('')}
    </div></div></li>
    <li class="asd-st" id="asdStep4"><div class="asd-lb"><b class="asd-n">4</b><span>加入排程</span></div><div class="asd-bd">
      <div class="asd-prev" id="asdPrev"></div>
      <div class="asd-act"><button type="button" class="asd-pri" id="asdAdd">加入排程</button><button type="button" id="asdCancelEdit" hidden>取消編輯</button><span class="asd-lack" id="asdLack" role="status"></span></div>
      <div class="asd-list"><div class="asd-lh"><span>排程清單</span><span class="asd-cnt" id="asdCnt"></span></div><ul id="asdRules"></ul></div>
    </div></li>
    <li class="asd-st" id="asdStep5"><div class="asd-lb"><b class="asd-n">5</b><span>啟用</span></div><div class="asd-bd">
      <label class="asd-sw"><input type="checkbox" id="asdOn"><span id="asdOnLbl">啟用自動產精選文章</span></label>
      <div class="asd-save"><span class="asd-st-txt" id="asdState" role="status"></span><button type="button" id="asdRetry" hidden>重試儲存</button></div>
      <p class="asd-note" id="asdNote" role="status"></p>
    </div></li>
  </ol>
</div>`;
  }

  function css() {
    if (document.getElementById('asdCss')) return;
    const s = document.createElement('style'); s.id = 'asdCss';
    /* 桌機與 ≤820 的版面寫在這裡（元件自己的）；≤640 手機的調整在 site/m4/20261016f-artsched-v2.css（CLAUDE.md 拆檔規則） */
    s.textContent = `
#v-subadm .asd .asd-steps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0}
#v-subadm .asd .asd-st{display:grid;grid-template-columns:150px minmax(0,1fr);gap:var(--sp-3,12px);padding:var(--sp-3,12px) 0;border-top:1px solid var(--line)}
#v-subadm .asd .asd-st:first-child{border-top:0;padding-top:4px}
#v-subadm .asd .asd-lb{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;align-content:flex-start;padding-top:4px;font-size:13.5px;font-weight:700;color:var(--ink)}
#v-subadm .asd .asd-lb small{flex-basis:100%;padding-left:32px;font-size:12px;font-weight:400;color:var(--ink-2)}
#v-subadm .asd .asd-n{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--panel-3);color:var(--accent,var(--cyan));box-shadow:inset 0 0 0 1.5px var(--accent,var(--cyan));font-family:var(--mono);font-size:13px;font-weight:700}
/* 這一步填好了 → 實心（一眼看出還差哪幾步） */
#v-subadm .asd .asd-st.done .asd-n{background:var(--accent,var(--cyan));color:var(--bg);box-shadow:none}
#v-subadm .asd .asd-bd{min-width:0;display:flex;flex-direction:column;gap:8px}
#v-subadm .asd button{box-sizing:border-box;min-height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
#v-subadm .asd button:hover:not(:disabled){border-color:var(--accent,var(--cyan))}
#v-subadm .asd button:disabled{opacity:.45;cursor:not-allowed}
#v-subadm .asd button[aria-pressed=true],#v-subadm .asd .asd-seg button.on{background:color-mix(in srgb,var(--accent,var(--cyan)) 16%,var(--panel));border-color:var(--accent,var(--cyan));color:var(--accent,var(--cyan));font-weight:700}
#v-subadm .asd .asd-seg{display:inline-flex;align-self:flex-start;border:1px solid var(--line-2);border-radius:8px;overflow:hidden}
#v-subadm .asd .asd-seg button{border:0;border-radius:0;min-width:96px}
#v-subadm .asd .asd-seg button+button{border-left:1px solid var(--line-2)}
#v-subadm .asd .asd-pane[hidden]{display:none}
#v-subadm .asd .asd-pane{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px}
#v-subadm .asd .asd-days{display:grid;grid-template-columns:repeat(7,40px);gap:6px}
#v-subadm .asd .asd-days .dd{width:40px;padding:0;font-weight:600}
#v-subadm .asd .asd-quick{display:flex;gap:6px;flex-wrap:wrap}
#v-subadm .asd .asd-dpick{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#v-subadm .asd input[type=date]{box-sizing:border-box;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-family:var(--mono);font-size:13px;padding:0 8px;color-scheme:light dark}
#v-subadm .asd .asd-tip{font-size:12.5px;color:var(--amber)}
#v-subadm .asd .asd-chips{display:flex;flex-wrap:wrap;gap:6px;flex-basis:100%}
#v-subadm .asd .asd-chips:empty::before{content:'還沒挑日期';font-size:12.5px;color:var(--ink-3)}
#v-subadm .asd .asd-chip{display:inline-flex;align-items:center;gap:2px;height:30px;padding:0 2px 0 10px;border-radius:999px;border:1px solid var(--accent,var(--cyan));color:var(--ink);font-family:var(--mono);font-size:13px}
#v-subadm .asd .asd-chip button{min-height:26px;height:26px;width:26px;padding:0;border:0;border-radius:50%;background:transparent;color:var(--ink-2);font-size:15px}
#v-subadm .asd .asd-hrow{display:grid;grid-template-columns:40px minmax(0,1fr);align-items:center;gap:8px}
#v-subadm .asd .asd-hl{font-size:13px;color:var(--ink-2);text-align:center}
#v-subadm .asd .asd-hours{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:6px}
#v-subadm .asd .hb{padding:0 2px;font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
#v-subadm .asd .asd-cats{display:flex;flex-wrap:wrap;gap:8px 24px}
#v-subadm .asd .asd-kr{display:flex;align-items:center;gap:10px;min-height:36px;font-size:14px}
#v-subadm .asd .asd-kn{min-width:6em}
#v-subadm .asd .asd-stp{display:inline-flex;align-items:center;gap:4px}
#v-subadm .asd .asd-stp button{width:32px;padding:0;font-size:16px}
#v-subadm .asd .asd-stp input{box-sizing:border-box;width:44px;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-family:var(--mono);font-size:13px;text-align:center;padding:0 6px;-moz-appearance:textfield;appearance:textfield}
#v-subadm .asd .asd-stp input::-webkit-outer-spin-button,#v-subadm .asd .asd-stp input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
#v-subadm .asd .asd-kr.on .asd-kn{color:var(--accent,var(--cyan));font-weight:700}
#v-subadm .asd .asd-prev{border-left:3px solid var(--accent,var(--cyan));background:var(--panel-3);border-radius:0 8px 8px 0;padding:6px 12px;font-size:13.5px;line-height:1.6;color:var(--ink)}
#v-subadm .asd .asd-prev.asd-emp{color:var(--ink-3);border-left-color:var(--line-2)}
#v-subadm .asd .asd-act{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
#v-subadm .asd .asd-pri{background:var(--accent,var(--cyan));color:var(--bg);border-color:transparent;font-weight:700;min-width:112px}
#v-subadm .asd .asd-lack{font-size:12.5px;color:var(--amber)}
#v-subadm .asd .asd-list{border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden}
#v-subadm .asd .asd-lh{display:flex;justify-content:space-between;align-items:center;padding:6px 12px;background:var(--panel-3);font-size:12px;font-weight:600;color:var(--ink-2)}
#v-subadm .asd .asd-cnt{font-family:var(--mono)}
#v-subadm .asd #asdRules{list-style:none;margin:0;padding:0}
#v-subadm .asd #asdRules:empty::before{content:'還沒有任何規則：在上面選好 ①②③ 再按「加入排程」';display:block;padding:10px 12px;font-size:13px;color:var(--ink-3)}
#v-subadm .asd .asd-rule{display:grid;grid-template-columns:28px minmax(0,1.3fr) minmax(0,1.4fr) minmax(0,1fr) auto;align-items:center;gap:10px;padding:6px 12px;border-top:1px solid var(--line);font-size:13.5px}
#v-subadm .asd .asd-rule:first-child{border-top:0}
#v-subadm .asd .asd-rule.ed{background:color-mix(in srgb,var(--accent,var(--cyan)) 10%,var(--panel))}
#v-subadm .asd .asd-rule.exp{opacity:.6}
#v-subadm .asd .asd-ri{font-family:var(--mono);color:var(--ink-3);text-align:center}
#v-subadm .asd .asd-rd,#v-subadm .asd .asd-rh{font-variant-numeric:tabular-nums}
#v-subadm .asd .asd-rh{font-family:var(--mono);font-size:13px}
#v-subadm .asd .asd-rb{display:flex;gap:6px}
#v-subadm .asd .asd-rb button{min-width:56px}
#v-subadm .asd .asd-rb button[data-del]:hover{border-color:var(--rise);color:var(--rise)}
#v-subadm .asd .asd-xp{display:inline-block;margin-left:6px;padding:0 6px;border-radius:999px;border:1px solid var(--line-2);font-size:12px;color:var(--ink-3)}
#v-subadm .asd .asd-sw{display:flex;align-items:center;gap:10px;min-height:36px;cursor:pointer;font-size:14px;font-weight:600}
#v-subadm .asd .asd-sw input{width:20px;height:20px;margin:0;accent-color:var(--accent,var(--cyan))}
#v-subadm .asd .asd-sw.dis{opacity:.55;cursor:not-allowed}
#v-subadm .asd .asd-save{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-height:32px}
#v-subadm .asd .asd-st-txt{font-size:13px;color:var(--ink-2)}
#v-subadm .asd .asd-st-txt.ok{color:var(--accent,var(--cyan))}
#v-subadm .asd .asd-st-txt.err{color:var(--amber)}
#v-subadm .asd .asd-note{margin:0;font-size:12.5px;color:var(--ink-2);min-height:18px}
#v-subadm .asd .asd-note.err{color:var(--amber)}
@media (max-width:1180px){#v-subadm .asd .asd-hours{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media (max-width:820px){
  #v-subadm .asd .asd-st{grid-template-columns:minmax(0,1fr);gap:8px}
  #v-subadm .asd .asd-lb{padding-top:0}
  #v-subadm .asd .asd-rule{grid-template-columns:24px minmax(0,1fr) auto;grid-template-areas:"i d b" "i h b" "i c b";row-gap:2px}
  #v-subadm .asd .asd-ri{grid-area:i;align-self:start}#v-subadm .asd .asd-rd{grid-area:d}#v-subadm .asd .asd-rh{grid-area:h}#v-subadm .asd .asd-rc{grid-area:c}#v-subadm .asd .asd-rb{grid-area:b}
}
`;
    document.head.appendChild(s);
  }

  /* 依狀態重畫（不重建 DOM，只改 class／文字；清單整塊重畫） */
  function sync(host) {
    const c = $('#artSchedCard', host); if (!c) return;
    const d = S.draft;
    // ① 日期
    $$('.asd-seg button', c).forEach((b) => { const on = b.dataset.mode === d.mode; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
    $$('.asd-pane', c).forEach((p) => { p.hidden = p.dataset.pane !== d.mode; });
    $$('#asdDays .dd', c).forEach((b) => b.setAttribute('aria-pressed', String(d.days.includes(+b.dataset.d))));
    $('#asdChips', c).innerHTML = sortS(d.dates).map((x) => `<span class="asd-chip" data-date="${esc(x)}">${esc(md(x))}<button type="button" data-undate="${esc(x)}" aria-label="移除 ${esc(x)}" title="移除">×</button></span>`).join('');
    $('#asdDate', c).min = todayTpe();
    // ② 時段
    $$('.hb', c).forEach((b) => b.setAttribute('aria-pressed', String(d.hours.includes(+b.dataset.h))));
    // ③ 篇數
    $$('.asd-kr', c).forEach((r) => { const i = $('input', r), n = d.cats[r.dataset.cat] || 0; if (document.activeElement !== i) i.value = String(n); r.classList.toggle('on', n > 0); });
    // ④ 預覽、按鈕、清單
    const lk = lack(), r = ruleOf(d), dupAt = S.rules.findIndex((x, i) => i !== S.edit && sameRule(x, r));
    const pv = $('#asdPrev', c);
    const has1 = d.mode === 'dates' ? d.dates.length : d.days.length;
    pv.classList.toggle('asd-emp', !(has1 || d.hours.length || catText(r)));
    pv.textContent = (S.edit >= 0 ? `正在編輯第 ${S.edit + 1} 條：` : '這一條：') + (has1 ? dayText(r) : '（日期）') + '｜' + (d.hours.length ? hourText(r) : '（時段）') + '｜' + (catText(r) || '（產什麼）');
    const add = $('#asdAdd', c);
    add.textContent = S.edit >= 0 ? `更新第 ${S.edit + 1} 條` : '加入排程';
    add.disabled = lk.length > 0 || dupAt >= 0 || S.busy;
    $('#asdCancelEdit', c).hidden = S.edit < 0;
    $('#asdLack', c).textContent = lk.length ? '還缺：' + lk.join('、') : dupAt >= 0 ? `跟第 ${dupAt + 1} 條一模一樣，不用再加` : '';
    ['asdStep1', 'asdStep2', 'asdStep3'].forEach((id, i) => $('#' + id, c).classList.toggle('done', [!!has1, d.hours.length > 0, O.cats.some(([k]) => d.cats[k] > 0)][i]));
    $('#asdStep4', c).classList.toggle('done', S.rules.length > 0);
    $('#asdCnt', c).textContent = `${S.rules.length}／${S.maxRules} 條`;
    $('#asdRules', c).innerHTML = S.rules.map((x, i) => `<li class="asd-rule${i === S.edit ? ' ed' : ''}${expired(x) ? ' exp' : ''}" data-i="${i}">
      <span class="asd-ri">${i + 1}</span><span class="asd-rd">${esc(dayText(x))}${expired(x) ? '<span class="asd-xp">已過期</span>' : ''}</span><span class="asd-rh">${esc(hourText(x))}</span><span class="asd-rc">${esc(catText(x))}</span>
      <span class="asd-rb"><button type="button" data-ed="${i}">編輯</button><button type="button" data-del="${i}">刪除</button></span></li>`).join('');
    // ⑤ 啟用＋儲存狀態
    const on = $('#asdOn', c), none = !S.rules.length;
    on.checked = !!S.enabled; on.disabled = (none && !S.enabled) || S.busy;
    on.closest('.asd-sw').classList.toggle('dis', on.disabled);
    $('#asdOnLbl', c).textContent = none ? '啟用自動產精選文章（清單至少要有一條規則才可以開）' : S.enabled ? '已啟用：到點就自動排進產出進度' : '啟用自動產精選文章';
    $('#asdStep5', c).classList.toggle('done', !!S.enabled);
    const st = $('#asdState', c), dirty = S.saved !== null && fp() !== S.saved;
    let txt = '', cls = '';
    if (S.busy) txt = '儲存中…';
    else if (S.backend === 'loading') txt = '讀取已儲存的設定中…';
    else if (S.backend === 'ok' && !dirty) { txt = S.savedAt ? '已儲存 ' + stamp(S.savedAt) : '還沒儲存過任何設定（目前＝關閉）'; cls = S.savedAt ? 'ok' : ''; }
    else if (S.backend === 'ok' && dirty) { txt = '尚未儲存成功'; cls = 'err'; }
    else { txt = BACK[S.backend] || ''; cls = 'err'; }
    st.textContent = txt; st.className = 'asd-st-txt' + (cls ? ' ' + cls : '');
    $('#asdRetry', c).hidden = !(S.backend === 'ok' && dirty && !S.busy);
    const nt = $('#asdNote', c); nt.textContent = S.note; nt.classList.toggle('err', S.noteErr);
    lsSet(LS, JSON.stringify({ enabled: S.enabled, rules: S.rules }));
  }

  /* 讀進來的規則再驗一次形狀（Worker 已經驗過；這裡只防壞資料讓畫面壞掉） */
  function cleanIn(sc) {
    const out = [];
    (Array.isArray(sc && sc.rules) ? sc.rules : []).forEach((r) => {
      if (!r || typeof r !== 'object') return;
      const hours = sortN((r.hours || []).filter((h) => Number.isInteger(h) && h >= 0 && h <= 23));
      const days = Array.isArray(r.days) ? sortN(r.days.filter((x) => Number.isInteger(x) && x >= 1 && x <= 7)) : null;
      const dates = Array.isArray(r.dates) ? sortS(r.dates.filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(String(x)))) : null;
      const cats = {}; O.cats.forEach(([k]) => { cats[k] = Math.max(0, Math.min(S.max, Math.round(Number(r.cats && r.cats[k]) || 0))); });
      if (!hours.length || !O.cats.some(([k]) => cats[k] > 0) || !((days && days.length) || (dates && dates.length))) return;
      out.push(Object.assign(dates && dates.length ? { dates } : { days }, { hours, cats }));
    });
    return out.slice(0, S.maxRules);
  }
  async function load(host) {
    S.backend = 'loading'; sync(host);
    const r = await O.call('/v1/articles/schedule/get', {});
    if (!host.isConnected) return;
    if (!r) S.backend = 'off';
    else if (r._s === 403) S.backend = 'denied';
    else if (r._s === 404 || r.error === 'not_found' || (r._s >= 400 && !r.allowed)) S.backend = 'old';
    else {
      S.backend = 'ok';
      const al = r.allowed || {};
      if (Array.isArray(al.hours) && al.hours.length) S.hours = sortN(al.hours.filter((h) => Number.isInteger(h) && h >= 0 && h <= 23));
      if (al.max) S.max = al.max;
      if (al.maxRules) S.maxRules = al.maxRules;
      if (al.maxDates) S.maxDates = al.maxDates;
      if (r.schedule) { S.rules = cleanIn(r.schedule); S.enabled = !!r.schedule.enabled && S.rules.length > 0; S.savedAt = r.schedule.updated || null; }
      else { S.rules = []; S.enabled = false; S.savedAt = null; }
      S.saved = fp();
    }
    host.innerHTML = html(); bind(host); sync(host);
  }
  /* 存：每次增刪改／切開關都呼叫；同時只送一筆，送的途中又有變動就等這筆回來再送最新一份 */
  async function save(host, why) {
    if (S.busy) { S.again = true; return; }
    if (S.backend !== 'ok' && S.backend !== 'preview') {   // 後端沒更新／連不到／非管理者：不送，畫面講清楚
      if (why === 'toggle') { S.enabled = !S.enabled; S.note = '開關沒切成功：' + (BACK[S.backend] || '後端無法使用'); S.noteErr = true; }
      sync(host); return;
    }
    const was = S.enabled;
    S.busy = true; sync(host);
    const body = { ver: 2, enabled: !!S.enabled, rules: S.rules };
    const r = await O.call('/v1/articles/schedule/add', body);
    S.busy = false;
    if (r && r.ok) {
      S.backend = 'ok'; S.savedAt = (r.schedule && r.schedule.updated) || Date.now(); S.saved = JSON.stringify({ e: body.enabled, r: body.rules });
      if (why === 'toggle') { S.note = S.enabled ? '已啟用。到點後最多約 1 小時內，文章會出現在上面的產出進度。' : '已關閉，之後不會再自動排；已經排進產出進度的照常處理。'; S.noteErr = false; }
    } else {
      if (why === 'toggle') S.enabled = !was;   // 開關切了但沒存成 → 退回去，不假裝已經開了
      if (r && r.error === 'preview_readonly') { S.backend = 'preview'; S.note = '預覽版不會真的儲存（寫入被擋下）。'; }
      else if (!r) S.note = '儲存失敗：連不到會員伺服器。';
      else if (r._s === 403) { S.backend = 'denied'; S.note = '儲存失敗：登入身分不是管理者。'; }
      else if (r._s === 404) { S.backend = 'old'; S.note = '儲存失敗：後端還沒更新到新版。'; }
      else S.note = '儲存失敗：' + (r.error || ('HTTP ' + r._s));
      S.noteErr = true;
    }
    sync(host);
    if (S.again) { S.again = false; save(host); }
  }
  function commitRules(host, msg) {
    if (S.enabled && !S.rules.length) { S.enabled = false; msg = '規則都刪光了，已自動關閉（不能開著卻什麼都不做）。'; }
    S.note = msg || ''; S.noteErr = false;
    sync(host); save(host, 'rules');
  }
  function addDate(host) {
    const c = $('#artSchedCard', host), v = $('#asdDate', c).value, tip = $('#asdDateTip', c);
    tip.textContent = '';
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) { tip.textContent = '請先挑一個日期'; return; }
    if (v < todayTpe()) { tip.textContent = '過去的日期不能選'; return; }
    if (S.draft.dates.includes(v)) { tip.textContent = '這天已經挑過了'; return; }
    if (S.draft.dates.length >= S.maxDates) { tip.textContent = `一條規則最多 ${S.maxDates} 天`; return; }
    S.draft.dates.push(v); sync(host);
  }
  function bind(host) {
    const c = $('#artSchedCard', host);
    $$('.asd-seg button', c).forEach((b) => { b.onclick = () => { S.draft.mode = b.dataset.mode; sync(host); }; });
    $('#asdDays', c).onclick = (e) => { const b = e.target.closest('button[data-d]'); if (!b) return; const d = +b.dataset.d, a = S.draft.days, i = a.indexOf(d); if (i >= 0) a.splice(i, 1); else a.push(d); S.draft.days = sortN(a); sync(host); };
    $$('.asd-quick button', c).forEach((b) => { b.onclick = () => { S.draft.days = b.dataset.q === 'all' ? [1, 2, 3, 4, 5, 6, 7] : b.dataset.q === 'work' ? [1, 2, 3, 4, 5] : []; sync(host); }; });
    $('#asdDateAdd', c).onclick = () => addDate(host);
    $('#asdDate', c).addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addDate(host); } });
    $('#asdChips', c).onclick = (e) => { const b = e.target.closest('button[data-undate]'); if (!b) return; S.draft.dates = S.draft.dates.filter((x) => x !== b.dataset.undate); sync(host); };
    c.addEventListener('click', (e) => {
      const h = e.target.closest('button.hb'); if (h) { const v = +h.dataset.h, a = S.draft.hours, i = a.indexOf(v); if (i >= 0) a.splice(i, 1); else a.push(v); S.draft.hours = sortN(a); sync(host); return; }
      const st = e.target.closest('button[data-st]'); if (st) { const k = st.closest('.asd-kr').dataset.cat; S.draft.cats[k] = Math.max(0, Math.min(S.max, (S.draft.cats[k] || 0) + (+st.dataset.st))); sync(host); return; }
      const ed = e.target.closest('button[data-ed]'); if (ed) {
        const i = +ed.dataset.ed, r = S.rules[i]; if (!r) return;
        S.edit = i; S.draft = { mode: r.dates ? 'dates' : 'days', days: (r.days || []).slice(), dates: (r.dates || []).slice(), hours: r.hours.slice(), cats: Object.assign({}, r.cats) };
        S.note = `第 ${i + 1} 條已帶回上面 ①②③，改好按「更新第 ${i + 1} 條」。`; S.noteErr = false; sync(host);
        $('#asdStep1', c).scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        return;
      }
      const del = e.target.closest('button[data-del]'); if (del) {
        const i = +del.dataset.del; if (!S.rules[i]) return;
        S.rules.splice(i, 1);
        if (S.edit === i) { S.edit = -1; S.draft = blank(); } else if (S.edit > i) S.edit -= 1;
        commitRules(host, `已刪除第 ${i + 1} 條。`);
      }
    });
    c.addEventListener('change', (e) => { const i = e.target.closest('input[data-kn]'); if (!i) return; const n = Math.round(Number(i.value)); S.draft.cats[i.dataset.kn] = Math.max(0, Math.min(S.max, Number.isFinite(n) ? n : 0)); i.value = String(S.draft.cats[i.dataset.kn]); sync(host); });   // 輸入框還有焦點時 sync 不會改它，所以這裡直接把修正後的數字寫回去
    $('#asdAdd', c).onclick = () => {
      if (lack().length) return;
      const r = ruleOf(S.draft);
      if (S.rules.some((x, i) => i !== S.edit && sameRule(x, r))) return;
      let msg;
      if (S.edit >= 0) { S.rules[S.edit] = r; msg = `已更新第 ${S.edit + 1} 條。`; S.edit = -1; }
      else { S.rules.push(r); msg = `已加入第 ${S.rules.length} 條。`; }
      S.draft = blank();
      commitRules(host, msg + (S.enabled ? '' : '全部設好後到 ⑤ 開啟用。'));
    };
    $('#asdCancelEdit', c).onclick = () => { S.edit = -1; S.draft = blank(); S.note = ''; sync(host); };
    /* 開關＝即時生效：切換就送出（關掉就立刻停止自動排隊） */
    $('#asdOn', c).onchange = (e) => { if (!S.rules.length && e.target.checked) { e.target.checked = false; return; } S.enabled = e.target.checked; S.note = ''; sync(host); save(host, 'toggle'); };
    $('#asdRetry', c).onclick = () => { S.note = ''; save(host); };
  }
  function mount(host, opts) {
    css(); if (opts) O = Object.assign(O, opts);
    S.draft = blank(); S.edit = -1; S.note = ''; S.saved = null;
    try { const d = JSON.parse(lsGet(LS) || 'null'); if (d && typeof d === 'object') { S.rules = cleanIn(d); S.enabled = !!d.enabled && S.rules.length > 0; } } catch (e) { /* 壞草稿就不理它 */ }
    host.innerHTML = html(); bind(host); sync(host);
    load(host);
  }
  window.TwArtSched = { mount, state: () => S, hourLabel };
})();
