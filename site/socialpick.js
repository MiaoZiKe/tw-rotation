/* ============================================================================
   社群選題（管理區 #admin/social）—— 2026-10-16 建（僅管理者可見）
   ----------------------------------------------------------------------------
   Andy 2026-10-16：每天從清單挑要做的題目；「該頁面需要新增產主題功能，我可以挑類型產，因為不一定都是 21:50 才需要，
   所以生產的時間、日期、頻率、類型我可以上面直接設定」。
   這一頁回答的問題：「今天社群部整理了哪些題目？我要做哪幾個？以後想在什麼時間、哪幾天、產幾個什麼類型？」
   所以該怎麼用：左邊分頁「今日選題」勾想做的 → 按「送出選擇」；要改定時或立刻多產，切「產主題設定」。

   v1 零後端：「送出」＝開一個預先填好內容的 GitHub 新 Issue（repo MiaoZiKe/tw-rotation），Andy 在 GitHub 按 Submit new issue 才算送出。
     · 勾選 → label social-pick；產主題設定 → label social-schedule（body 含 JSON 區塊）。格式見 docs/marketing/social_unit/menu_json_spec.md。
     · 資料來源：site/social/menu_latest.json（社群媒體部每日 commit，不是 build 產物）。檔案缺失／壞掉／空 → 空狀態寫原因。
   權限：只有管理者（TwAccount user.admin）看得到內容；入口在 layout4.js 的 ADM_SUBS（只有管理者才會建立那一格），
     一般會員與訪客的 DOM 裡沒有入口，自己打網址只會看到「只有管理者看得到」。預覽版（window.TW_PREVIEW）比照其他管理頁可瀏覽。
     ⚠ menu_latest.json 在公開的 site/ 底下，任何人打網址讀得到 —— 只放可公開的題目與重點（見 spec）。
   存放：勾選與設定存 localStorage（鍵 tw.social.pick / tw.social.sched），每次讀寫都包 try/catch。
   安全：JSON 內所有字串一律 esc() 後才放進畫面，不收 HTML。
   驗收：scripts/_uitest.py「社群選題1016」。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const REPO = 'MiaoZiKe/tw-rotation';
  const KINDS = ['最新消息', '產業延伸', '精選文章', '總經名詞'];
  const KCOL = { 最新消息: 'var(--cat-1)', 產業延伸: 'var(--cat-2)', 精選文章: 'var(--cat-3)', 總經名詞: 'var(--cat-4)' };
  const LS_PICK = 'tw.social.pick', LS_SCHED = 'tw.social.sched';
  const WD = ['一', '二', '三', '四', '五', '六', '日'];
  const FREQ = [['daily', '每天'], ['workdays', '僅工作日'], ['weekly', '自訂星期'], ['once', '只跑一次']];
  const NOTE_LAG = '設定會在下一個處理週期（最多數小時）生效，要立刻生效請在對話告訴 CEO。';

  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } };
  const tpeNow = () => new Date(Date.now() + 8 * 3600000);
  const tpeDay = () => tpeNow().toISOString().slice(0, 10);
  const tpeIso = () => tpeNow().toISOString().slice(0, 19) + '+08:00';
  const tpeHm = () => tpeNow().toISOString().slice(11, 16);

  const S = { menu: null, err: '', loading: false, picked: new Set(), open: new Set(), kind: '', tab: 'pick', admin: null,
    sched: { kinds: { 最新消息: 2, 產業延伸: 2, 精選文章: 0, 總經名詞: 1 }, times: ['21:50'], freq: 'daily', days: [1, 2, 3, 4, 5], date: '' } };

  /* ---------------------------------------------------------------- 樣式（全部掛在 #v-subadm .spk 底下；手機規則只在 ≤640） */
  function css() {
    if (document.getElementById('spkCss')) return;
    const s = document.createElement('style'); s.id = 'spkCss';
    s.textContent = `
#v-subadm .spk{max-width:1100px;margin:0 auto}
#v-subadm .spk [hidden]{display:none!important}
#v-subadm .spk .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 6px}
#v-subadm .spk .hd h3{margin:0;font-size:var(--fs-h3,16px);font-weight:600}
#v-subadm .spk .hd h3::before{content:"";display:inline-block;width:4px;height:14px;border-radius:2px;background:var(--accent,var(--cyan));margin-right:8px;vertical-align:-2px}
#v-subadm .spk .hd .sp{flex:1}
#v-subadm .spk .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:0 0 8px}
#v-subadm .spk .ex{display:inline-block;padding:1px 9px;border-radius:999px;border:1px solid var(--amber);color:var(--amber);font-size:12px;font-weight:700}
#v-subadm .spk .warn{border:1px solid var(--amber);border-radius:8px;padding:6px 10px;color:var(--amber);font-size:13px;margin:0 0 8px}
#v-subadm .spk .lag{border-left:3px solid var(--accent,var(--cyan));background:var(--panel-3);border-radius:0 8px 8px 0;padding:8px 12px;color:var(--ink);font-size:13.5px;line-height:1.6;margin:0 0 10px}
#v-subadm .spk button,#v-subadm .spk .btn{box-sizing:border-box;min-height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center;text-decoration:none}
#v-subadm .spk button:hover,#v-subadm .spk .btn:hover{border-color:var(--cyan)}
#v-subadm .spk .btn.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .spk .btn[aria-disabled="true"]{opacity:.45;cursor:not-allowed;pointer-events:none}
#v-subadm .spk .tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 8px}
#v-subadm .spk .seg{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch;max-width:100%;flex:0 1 auto}
#v-subadm .spk .seg::-webkit-scrollbar{display:none}
#v-subadm .spk .seg button{flex:0 0 auto}
#v-subadm .spk .seg button.on{background:var(--panel);border-color:var(--cyan);color:var(--cyan);font-weight:700}
#v-subadm .spk .seg em{font-style:normal;font-family:var(--mono);font-size:12px;color:var(--ink-3);margin-left:6px}
#v-subadm .spk .cnt{margin-left:auto;font-size:13px;color:var(--ink-2);font-family:var(--mono)}
#v-subadm .spk .list{display:flex;flex-direction:column;gap:6px}
#v-subadm .spk .it{border:1px solid var(--line);border-radius:10px;background:var(--panel)}
#v-subadm .spk .it.on{border-color:var(--cyan);background:var(--panel-3)}
#v-subadm .spk .it:hover{border-color:var(--line-2)}
#v-subadm .spk .it.on:hover{border-color:var(--cyan)}
#v-subadm .spk .row{display:grid;grid-template-columns:40px minmax(0,1fr) auto 28px;align-items:center;gap:6px;padding:4px 8px 4px 0;min-height:56px}
#v-subadm .spk .cb{display:flex;align-items:center;justify-content:center;width:40px;height:40px;cursor:pointer}
#v-subadm .spk .cb input{width:20px;height:20px;margin:0;accent-color:var(--cyan);cursor:pointer}
#v-subadm .spk .mn{min-width:0;display:block;text-align:left;background:none;border:0;padding:4px 0;color:inherit;font:inherit;cursor:pointer;min-height:40px;display:block;white-space:normal}
#v-subadm .spk .mn1{display:flex;align-items:center;gap:8px;min-width:0}
#v-subadm .spk .id{font-family:var(--mono);font-size:12px;color:var(--ink-3);flex:none}
#v-subadm .spk .kd{display:inline-flex;align-items:center;gap:5px;flex:none;font-size:12px;color:var(--ink-2);border:1px solid var(--line-2);border-radius:999px;padding:0 8px;height:20px}
#v-subadm .spk .kd::before{content:"";width:8px;height:8px;border-radius:2px;background:var(--c,var(--cat-6))}
#v-subadm .spk .tt{font-size:14px;font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink)}
#v-subadm .spk .wc{display:block;font-size:12.5px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
#v-subadm .spk .mt{display:flex;align-items:center;gap:6px;flex:none}
#v-subadm .spk .ch{display:inline-flex;align-items:center;gap:4px;height:22px;padding:0 8px;border-radius:999px;border:1px solid var(--line-2);font-size:12px;color:var(--ink-2);white-space:nowrap}
#v-subadm .spk .ch.no{color:var(--ink-3)}
#v-subadm .spk .ch.wait{color:var(--amber);border-color:var(--amber)}
#v-subadm .spk .ch.flag{color:var(--amber);border-color:var(--amber);font-weight:700}
#v-subadm .spk .ch.out{max-width:170px;overflow:hidden;text-overflow:ellipsis;display:inline-block;line-height:20px}
#v-subadm .spk .kd2,#v-subadm .spk .id2{display:none}
#v-subadm .spk .how-m{display:none}
#v-subadm .spk .fm,#v-subadm .spk .sh{display:none}
#v-subadm .spk .chev{width:28px;min-height:28px!important;padding:0!important;border:0!important;background:none!important;color:var(--ink-3);transition:transform .15s}
#v-subadm .spk .it.open .chev{transform:rotate(180deg)}
#v-subadm .spk .det{border-top:1px solid var(--line);padding:10px 14px 12px 48px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 24px;font-size:13px;line-height:1.6;color:var(--ink-2)}
#v-subadm .spk .det h4{margin:0 0 2px;font-size:12px;font-weight:600;color:var(--ink-3);letter-spacing:.04em}
#v-subadm .spk .det ol,#v-subadm .spk .det ul{margin:0;padding-left:18px;color:var(--ink)}
#v-subadm .spk .det .fl{color:var(--amber)}
#v-subadm .spk .det .full{grid-column:1/-1}
#v-subadm .spk .bar{position:sticky;bottom:0;z-index:5;margin-top:10px;background:var(--panel-2);border:1px solid var(--line-2);border-radius:10px;padding:8px 12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#v-subadm .spk .bar .n{font-size:13px;color:var(--ink-2)}
#v-subadm .spk .bar .n b{color:var(--ink);font-family:var(--mono);font-size:16px}
#v-subadm .spk .bar .sp{flex:1}
#v-subadm .spk details{margin-top:8px}
#v-subadm .spk summary{cursor:pointer;color:var(--ink-2);font-size:13px;min-height:32px;display:flex;align-items:center}
#v-subadm .spk pre{margin:6px 0 0;padding:10px 12px;background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--ink);font-family:var(--mono);font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-all;max-height:260px;overflow:auto}
#v-subadm .spk .empty{padding:28px 12px;text-align:center;color:var(--ink-2);font-size:14px;line-height:1.7;border:1px dashed var(--line-2);border-radius:10px}
#v-subadm .spk .nbbody{margin-bottom:0}
/* 產主題設定 */
#v-subadm .spk .fm{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
#v-subadm .spk .fs{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:10px 14px 12px;min-width:0}
#v-subadm .spk .fs.w2{grid-column:1/-1}
#v-subadm .spk .fs h4{margin:0 0 8px;font-size:13.5px;font-weight:700;color:var(--ink)}
#v-subadm .spk .kr{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;min-height:40px;border-bottom:1px solid var(--line)}
#v-subadm .spk .kr:last-child{border-bottom:0}
#v-subadm .spk .kr label{display:flex;align-items:center;gap:10px;cursor:pointer;min-height:40px;min-width:0}
#v-subadm .spk .kr input[type=checkbox]{width:20px;height:20px;margin:0;accent-color:var(--cyan)}
#v-subadm .spk .stp{display:inline-flex;align-items:center;gap:4px}
#v-subadm .spk .stp button{width:32px;padding:0;font-size:16px}
#v-subadm .spk .stp input,#v-subadm .spk input[type=time],#v-subadm .spk input[type=date]{box-sizing:border-box;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-family:var(--mono);font-size:13px;text-align:center;padding:0 6px}
#v-subadm .spk .stp input{width:44px}
#v-subadm .spk .stp input::-webkit-outer-spin-button,#v-subadm .spk .stp input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
#v-subadm .spk .stp input[type=number]{-moz-appearance:textfield;appearance:textfield}
#v-subadm .spk .kr.off .stp{opacity:.45}
#v-subadm .spk .tm{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#v-subadm .spk .tm .t{display:inline-flex;align-items:center;gap:2px}
#v-subadm .spk .tm .t input{width:104px}
#v-subadm .spk .tm .t button{width:32px;padding:0;border-color:transparent;background:none;color:var(--ink-3)}
#v-subadm .spk .wk{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
#v-subadm .spk .wk button{width:40px;padding:0}
#v-subadm .spk .wk button.on{background:var(--panel);border-color:var(--cyan);color:var(--cyan);font-weight:700}
#v-subadm .spk .sum{font-size:13.5px;line-height:1.7;color:var(--ink)}
#v-subadm .spk .why{font-size:12.5px;color:var(--amber);min-height:20px;margin-top:4px}
#v-subadm .spk .acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
@media (max-width:820px){#v-subadm .spk .fm{grid-template-columns:minmax(0,1fr)}#v-subadm .spk .det{grid-template-columns:minmax(0,1fr)}}
@media (max-width:640px){
  /* 手機（Andy 準則 1、3）：390 一屏要看得到 6 題＋送出列 → 只留「勾選、題目（最多 2 行）、類型／編號／圖表／查證／⚠」，
     內文三點、預估產出、怎麼用長說明都收到點開的細節裡；題目允許 2 行（手機沒有滑過提示，一行截斷會看不出是哪題） */
  #v-subadm .spk .row{grid-template-columns:40px minmax(0,1fr) 40px;align-items:start;min-height:0;padding:4px 4px 4px 0;gap:0 4px}
  #v-subadm .spk .cb{grid-row:1/3;margin-top:-2px}
  #v-subadm .spk .mn{grid-column:2;grid-row:1;min-height:0;padding:0}
  #v-subadm .spk .mn1 .id,#v-subadm .spk .mn1 .kd{display:none}
  #v-subadm .spk .tt{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:1.3;font-size:14px}
  #v-subadm .spk .mt{grid-column:2;grid-row:2;flex-wrap:wrap;gap:4px;margin-top:4px}
  #v-subadm .spk .kd2{display:inline-flex;padding:0 6px}
  #v-subadm .spk .fd,#v-subadm .spk .lg{display:none}
  #v-subadm .spk .fm,#v-subadm .spk .sh{display:inline}
  #v-subadm .spk .ch{padding:0 6px}
  #v-subadm .spk .tools{flex-wrap:nowrap}
  #v-subadm .spk .tools .seg{flex:1 1 0;min-width:0}
  #v-subadm .spk .tools>button{padding:0 8px;flex:none}
  #v-subadm .spk .row .chev{grid-column:3;grid-row:1;align-self:start}
  #v-subadm .spk .wc,#v-subadm .spk .ch.out,#v-subadm .spk .how-d,#v-subadm .spk .cnt,#v-subadm .spk #spkEx,#v-subadm .spk #spkDt{display:none}
  #v-subadm .spk .how-m{display:block;margin:8px 0 0}
  #v-subadm .spk .det{padding:10px 12px 12px}
  #v-subadm .spk .bar{padding:8px 10px;margin-top:8px}
  #v-subadm .spk .tools{margin-bottom:6px}
  #v-subadm .spk .list{gap:5px}
}
`;
    document.head.appendChild(s);
  }

  /* ---------------------------------------------------------------- 權限 */
  function isAdmin() {
    if (window.TW_PREVIEW) return true;   // 預覽版全開（DECISIONS #343）；寫入本來就只經 GitHub 連結，沒有後端
    const A = window.TwAccount; const u = A && A.on && A.on() && A.user && A.user();
    return !!(u && u.admin);
  }

  /* ---------------------------------------------------------------- 資料 */
  function normItem(x) {
    if (!x || typeof x !== 'object') return null;
    const id = String(x.id == null ? '' : x.id);
    if (!/^[A-Za-z0-9_-]{1,16}$/.test(id)) return null;
    const arr = (a) => (Array.isArray(a) ? a.map((v) => String(v == null ? '' : v)).filter(Boolean) : []);
    const ch = x.chart && typeof x.chart === 'object' ? x.chart : {}, vf = x.verified && typeof x.verified === 'object' ? x.verified : {};
    return { id, kind: String(x.kind || ''), title: String(x.title || '（未命名）').slice(0, 80), will_cover: arr(x.will_cover).slice(0, 3),
      chart: { has: !!ch.has, note: String(ch.note || '') }, images: arr(x.images_needed),
      verified: { ok: vf.status === '已查證', status: String(vf.status || '待查證'), who: String(vf.who || '') }, output: String(x.output || ''), flags: arr(x.flags) };
  }
  async function loadMenu(force) {
    if (S.loading || (S.menu && !force)) return;
    S.loading = true; S.err = '';
    try {
      const r = await fetch('social/menu_latest.json?_=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status === 404 ? '本部今天還沒有產出選題清單（找不到 social/menu_latest.json）' : '讀取失敗（HTTP ' + r.status + '）');
      const j = await r.json();
      if (!j || typeof j !== 'object' || !Array.isArray(j.items)) throw new Error('清單格式不對（少了 items）');
      if (j.version !== 1) throw new Error('清單版本 ' + esc(j.version) + ' 這一頁還不認得（只認 version 1）');
      const items = j.items.map(normItem).filter(Boolean).slice(0, 30);
      S.menu = { date: /^\d{4}-\d\d-\d\d$/.test(j.date) ? j.date : '', example: j.example === true, updated: String(j.updated || ''), items };
      // 只還原「同一天」的勾選，而且只留清單裡真的有的編號（清單換了，舊勾選不會變成幽靈）
      let sv = null; try { sv = JSON.parse(lsGet(LS_PICK) || 'null'); } catch (e) { sv = null; }
      S.picked = new Set(sv && sv.date === S.menu.date && Array.isArray(sv.ids) ? sv.ids.filter((id) => items.some((i) => i.id === id)) : []);
    } catch (e) {
      S.menu = null; S.err = e && e.message ? String(e.message) : '讀取失敗';
    }
    S.loading = false;
  }
  function loadSched() {
    let sv = null; try { sv = JSON.parse(lsGet(LS_SCHED) || 'null'); } catch (e) { sv = null; }
    if (!sv || typeof sv !== 'object') return;
    const c = S.sched;
    if (sv.kinds && typeof sv.kinds === 'object') KINDS.forEach((k) => { const n = Math.round(Number(sv.kinds[k])); if (n >= 0 && n <= 9) c.kinds[k] = n; });
    if (Array.isArray(sv.times)) { const t = sv.times.filter((v) => /^\d\d:\d\d$/.test(v)).slice(0, 6); if (t.length) c.times = t; }
    if (FREQ.some((f) => f[0] === sv.freq)) c.freq = sv.freq;
    if (Array.isArray(sv.days)) c.days = sv.days.map(Number).filter((n) => n >= 1 && n <= 7);
    if (/^\d{4}-\d\d-\d\d$/.test(sv.date || '')) c.date = sv.date;
  }
  const savePick = () => lsSet(LS_PICK, JSON.stringify({ date: S.menu ? S.menu.date : '', ids: Array.from(S.picked) }));
  const saveSched = () => lsSet(LS_SCHED, JSON.stringify(S.sched));

  /* ---------------------------------------------------------------- Issue 連結內容 */
  const issueUrl = (title, body, label) => 'https://github.com/' + REPO + '/issues/new?title=' + encodeURIComponent(title) + '&body=' + encodeURIComponent(body) + '&labels=' + encodeURIComponent(label);
  const shq = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'";
  const ghCmd = (title, body, label) => 'gh issue create -R ' + REPO + ' -t ' + shq(title) + ' -l ' + label + ' -b ' + shq(body);
  function pickIssue() {
    const m = S.menu; if (!m) return null;
    const ps = m.items.filter((i) => S.picked.has(i.id));
    const body = '日期：' + m.date + '\n被勾 ' + ps.length + ' 項（共 ' + m.items.length + ' 項）：\n' + ps.map((i) => '- [x] ' + i.id + '｜' + i.kind + '｜' + i.title).join('\n') +
      '\n沒勾的不做。\n<!-- social-pick ' + JSON.stringify({ date: m.date, picked: ps.map((i) => i.id) }) + ' -->';
    return { title: '每日選題勾選 ' + m.date, body, label: 'social-pick', n: ps.length };
  }
  const fmtDays = (d) => d.length === 5 && d.join() === '1,2,3,4,5' ? '週一至週五' : d.map((n) => '週' + WD[n - 1]).join('、');
  function schedErr(action) {
    const c = S.sched, tot = KINDS.reduce((a, k) => a + (c.kinds[k] || 0), 0);
    if (!tot) return '至少要有一種類型、項數大於 0';
    if (action === 'run_now') return '';
    if (!c.times.length) return '至少要一個執行時間';
    if (c.freq === 'weekly' && !c.days.length) return '自訂星期至少選一天';
    if (c.freq === 'once') { if (!c.date) return '只跑一次要指定哪一天'; if (c.date < tpeDay()) return '指定日期不能早於今天（台北）'; }
    return '';
  }
  function schedJson(action) {
    const c = S.sched, kinds = {}; KINDS.forEach((k) => { kinds[k] = c.kinds[k] || 0; });
    const o = { version: 1, action, tz: 'Asia/Taipei', kinds };
    if (action === 'set_schedule') {
      o.times = Array.from(new Set(c.times)).sort(); o.frequency = c.freq;
      o.days = c.freq === 'weekly' ? Array.from(new Set(c.days)).sort((a, b) => a - b) : [];
      o.date = c.freq === 'once' ? c.date : null;
    }
    o.created = tpeIso();
    return o;
  }
  function kindsText() { const p = KINDS.filter((k) => S.sched.kinds[k] > 0).map((k) => k + ' ' + S.sched.kinds[k]); const t = KINDS.reduce((a, k) => a + (S.sched.kinds[k] || 0), 0); return p.join('、') + '（共 ' + t + ' 項）'; }
  function schedSummary(action) {
    const c = S.sched;
    if (action === 'run_now') return '立刻產一份：' + kindsText() + '。';
    const when = c.freq === 'daily' ? '每天' : c.freq === 'workdays' ? '每個工作日（週一至週五）' : c.freq === 'weekly' ? '每週 ' + fmtDays(c.days.slice().sort((a, b) => a - b)) : '只跑一次，' + (c.date || '（未指定日期）');
    return when + ' ' + Array.from(new Set(c.times)).sort().join('、') + '（台北時間）產：' + kindsText() + '。';
  }
  function schedIssue(action) {
    const j = schedJson(action), sum = schedSummary(action);
    const body = sum + '\n' + NOTE_LAG + '\n\n```json social-schedule\n' + JSON.stringify(j, null, 2) + '\n```';
    const title = action === 'run_now' ? '立刻產主題 ' + tpeDay() + ' ' + tpeHm() : '每日產主題設定 ' + tpeDay();
    return { title, body, label: 'social-schedule', json: j };
  }

  /* ---------------------------------------------------------------- 畫面：今日選題 */
  function chips(i) {
    const f = i.flags.length;
    return `<span class="ch ${i.chart.has ? '' : 'no'}" title="${esc(i.chart.note)}">圖表：${i.chart.has ? '有' : '無'}</span>`
      + `<span class="ch ${i.verified.ok ? '' : 'wait'}" title="${esc(i.verified.who)}">${esc(i.verified.status)}</span>`
      + (f ? `<span class="ch flag" title="${esc(i.flags.join('、'))}">⚠ <span class="fd">${esc(i.flags.length > 1 ? i.flags.length + ' 項' : i.flags[0])}</span><span class="fm">${f}</span></span>` : '')
      + `<span class="ch out" title="${esc(i.output)}">${esc(i.output)}</span>`;
  }
  function itemHtml(i) {
    const on = S.picked.has(i.id), op = S.open.has(i.id);
    return `<div class="it${on ? ' on' : ''}${op ? ' open' : ''}" data-id="${esc(i.id)}" data-kind="${esc(i.kind)}">
  <div class="row">
    <label class="cb" title="勾選這一項"><input type="checkbox" data-pick="${esc(i.id)}" aria-label="勾選 ${esc(i.id)} ${esc(i.title)}"${on ? ' checked' : ''}></label>
    <button type="button" class="mn" data-open="${esc(i.id)}" aria-expanded="${op}" title="${esc(i.title)}">
      <span class="mn1"><span class="id">${esc(i.id)}</span><span class="kd" style="--c:${KCOL[i.kind] || 'var(--cat-6)'}">${esc(i.kind || '其他')}</span><span class="tt">${esc(i.title)}</span></span>
      <span class="wc">${i.will_cover.map((w, n) => '①②③'[n] + ' ' + esc(w)).join('　')}</span>
    </button>
    <span class="mt"><span class="kd kd2" style="--c:${KCOL[i.kind] || 'var(--cat-6)'}">${esc(i.kind || '其他')}</span><span class="id id2">${esc(i.id)}</span>${chips(i)}</span>
    <button type="button" class="chev" data-open="${esc(i.id)}" aria-label="${op ? '收起' : '展開'}細節">▾</button>
  </div>
  <div class="det" ${op ? '' : 'hidden'}>
    <div class="full"><h4>這次內文會講</h4><ol>${i.will_cover.map((w) => `<li>${esc(w)}</li>`).join('') || '<li>（清單沒有寫）</li>'}</ol></div>
    <div><h4>圖表</h4>${i.chart.has ? '有：' : '無：'}${esc(i.chart.note.replace(/^[有無][:：]\s*/, '') || '（未說明）')}</div>
    <div><h4>圖片需補充</h4>${i.images.length ? `<ul>${i.images.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>` : '不需要，素材都現成'}</div>
    <div><h4>查證</h4>${esc(i.verified.status)}${i.verified.who ? '：' + esc(i.verified.who) : ''}</div>
    <div><h4>預估產出</h4>${esc(i.output || '（未寫）')}</div>
    <div class="full"><h4>法遵紅旗</h4>${i.flags.length ? `<span class="fl">⚠ ${i.flags.map(esc).join('、')}</span>` : '沒有'}</div>
  </div>
</div>`;
  }
  function listHtml() {
    const m = S.menu;
    const items = m.items.filter((i) => !S.kind || i.kind === S.kind);
    return items.length ? items.map(itemHtml).join('') : `<div class="empty">這個類型今天沒有題目。</div>`;
  }
  function pickHtml() {
    if (S.loading && !S.menu) return '<div class="empty">載入今日選題…</div>';
    if (!S.menu) return `<div class="empty" id="spkEmpty">${esc(S.err || '沒有選題清單')}<br>清單由社群媒體部每天產出，沒有清單時這一頁沒有東西可勾。<br><button type="button" id="spkRetry" style="margin-top:10px">重新讀取</button></div>`;
    const m = S.menu;
    if (!m.items.length) return '<div class="empty" id="spkEmpty">今天的清單是空的（items 沒有題目）。</div>';
    const cnt = (k) => m.items.filter((i) => !k || i.kind === k).length;
    const tabs = [['', '全部']].concat(KINDS.map((k) => [k, k])).filter((t) => !t[0] || cnt(t[0]));
    return `${m.example ? '<div class="warn" id="spkEx">這是範例資料（menu_latest.json 標了 example），不是本部今天的真實清單。</div>' : ''}${m.date && m.date !== tpeDay() ? `<div class="warn" id="spkStale">清單日期是 ${esc(m.date)}，不是今天（${tpeDay()}）：本部還沒更新今天的清單。</div>` : ''}
<div class="tools"><div class="seg" id="spkKinds" role="tablist" aria-label="題目類型">${tabs.map(([k, n]) => `<button type="button" role="tab" data-k="${esc(k)}" class="${S.kind === k ? 'on' : ''}" aria-selected="${S.kind === k}">${esc(n)}<em>${cnt(k)}</em></button>`).join('')}</div>
  <button type="button" id="spkAll"><span class="lg">全選這一頁</span><span class="sh">全選</span></button><button type="button" id="spkNone"><span class="lg">全部取消</span><span class="sh">取消</span></button>
  <span class="cnt" id="spkCnt"></span></div>
<div class="list" id="spkList">${listHtml()}</div>
<p class="muted how-m"><b>怎麼用：</b>勾題目 → 按「送出選擇」；沒勾的不做。想改時間／類型／項數，切「產主題設定」。</p>
<div class="bar" id="spkBar"><span class="n">已勾 <b id="spkN">0</b> 項</span><span class="sp"></span>
  <a class="btn pri" id="spkSend" target="_blank" rel="noopener noreferrer" role="button">送出選擇（開 GitHub）</a>
  <button type="button" id="spkCopy" title="複製成命令列（gh issue create）；沒有 gh 時也可以直接對 CEO 說「勾 編號」">複製指令</button></div>
<p class="muted" style="margin-top:8px">送出＝開一個填好內容的 GitHub 新 Issue，請在那一頁按綠色的 <b>Submit new issue</b>（送出新問題）才算數。Issue 是公開的，內容只有編號與題目。備援：直接對 CEO 說「勾 ${esc(m.items[0].id)}」也可以。</p>
<details id="spkPrevD"><summary>送出內容預覽</summary><pre id="spkPrev"></pre></details>`;
  }
  function syncPick(v) {
    const m = S.menu; if (!m) return;
    const q = pickIssue(), a = $('#spkSend', v);
    $$('#spkList .it', v).forEach((it) => { const on = S.picked.has(it.dataset.id); it.classList.toggle('on', on); const cb = $('input[data-pick]', it); if (cb) cb.checked = on; });
    $('#spkN', v).textContent = String(q.n);
    $('#spkCnt', v).textContent = '共 ' + m.items.length + ' 項・此頁 ' + $$('#spkList .it', v).length + ' 項';
    if (q.n) { a.href = issueUrl(q.title, q.body, q.label); a.removeAttribute('aria-disabled'); a.title = '開新分頁：GitHub 新 Issue（' + q.title + '）'; }
    else { a.removeAttribute('href'); a.setAttribute('aria-disabled', 'true'); a.title = '先勾至少一項'; }
    $('#spkPrev', v).textContent = q.n ? '標題：' + q.title + '\n標籤：' + q.label + '\n\n' + q.body : '（還沒勾任何一項）';
    const cp = $('#spkCopy', v); cp.disabled = !q.n; cp.style.opacity = q.n ? '' : '.45';
  }
  async function copyText(t) {
    try { await navigator.clipboard.writeText(t); return true; } catch (e) { /* 退回舊法 */ }
    try { const ta = document.createElement('textarea'); ta.value = t; ta.style.cssText = 'position:fixed;left:-999px;top:0'; document.body.appendChild(ta); ta.select(); const r = document.execCommand('copy'); ta.remove(); return !!r; } catch (e) { return false; }
  }
  const toast = (m) => { const T = window.TwSub; if (T && T.toast) T.toast(m); };
  function bindPick(v) {
    const R = $('#spkRetry', v); if (R) R.onclick = async () => { S.menu = null; await loadMenu(true); paint(v); };
    if (!S.menu || !S.menu.items.length) return;
    v.onclick = null;
    $('#spkKinds', v).onclick = (e) => { const b = e.target.closest('button[data-k]'); if (!b) return; S.kind = b.dataset.k; paint(v); };
    $('#spkList', v).onclick = (e) => {
      const o = e.target.closest('[data-open]');
      if (o) { const id = o.dataset.open; if (S.open.has(id)) S.open.delete(id); else S.open.add(id);
        const it = o.closest('.it'), op = S.open.has(id); it.classList.toggle('open', op); $('.det', it).hidden = !op; $$('[data-open]', it).forEach((x) => x.setAttribute('aria-expanded', String(op))); return; }
    };
    $('#spkList', v).onchange = (e) => {
      const c = e.target.closest('input[data-pick]'); if (!c) return;
      if (c.checked) S.picked.add(c.dataset.pick); else S.picked.delete(c.dataset.pick);
      savePick(); syncPick(v);
    };
    const vis = () => $$('#spkList .it', v).map((x) => x.dataset.id);
    $('#spkAll', v).onclick = () => { vis().forEach((id) => S.picked.add(id)); savePick(); syncPick(v); };
    $('#spkNone', v).onclick = () => { S.picked.clear(); savePick(); syncPick(v); };
    $('#spkCopy', v).onclick = async () => { const q = pickIssue(); if (!q.n) return; toast((await copyText(ghCmd(q.title, q.body, q.label))) ? '已複製指令' : '複製失敗，請改用「送出內容預覽」手動複製'); };
    syncPick(v);
  }

  /* ---------------------------------------------------------------- 畫面：產主題設定 */
  function schedHtml() {
    const c = S.sched;
    return `<div class="lag" id="spkLag">${NOTE_LAG}</div>
<div class="fm">
  <div class="fs"><h4>① 要產哪些類型、各幾項</h4>
    ${KINDS.map((k) => `<div class="kr${c.kinds[k] > 0 ? '' : ' off'}" data-kind="${esc(k)}"><label><input type="checkbox" data-kc="${esc(k)}"${c.kinds[k] > 0 ? ' checked' : ''}><span class="kd" style="--c:${KCOL[k]}">${esc(k)}</span></label>
      <span class="stp"><button type="button" data-st="-1" aria-label="${esc(k)}減一項">−</button><input type="number" min="0" max="9" step="1" inputmode="numeric" data-kn="${esc(k)}" value="${c.kinds[k]}" aria-label="${esc(k)}項數"><button type="button" data-st="1" aria-label="${esc(k)}加一項">＋</button></span></div>`).join('')}
  </div>
  <div class="fs"><h4>② 執行時間（台北時間，可多個時段）</h4>
    <div class="tm" id="spkTimes"></div>
    <p class="muted" style="margin:8px 0 0">不一定要 21:50，想幾點就幾點；最多 6 個時段。</p>
  </div>
  <div class="fs w2"><h4>③ 哪幾天、多久一次</h4>
    <div class="seg" id="spkFreq" role="tablist" aria-label="頻率">${FREQ.map(([k, n]) => `<button type="button" role="tab" data-f="${k}" class="${c.freq === k ? 'on' : ''}" aria-selected="${c.freq === k}">${n}</button>`).join('')}</div>
    <div class="wk" id="spkWk" ${c.freq === 'weekly' ? '' : 'hidden'}>${WD.map((n, i) => `<button type="button" data-d="${i + 1}" class="${c.days.includes(i + 1) ? 'on' : ''}" aria-pressed="${c.days.includes(i + 1)}">${n}</button>`).join('')}</div>
    <div class="tm" id="spkOnce" style="margin-top:8px" ${c.freq === 'once' ? '' : 'hidden'}><label for="spkDate" class="muted" style="margin:0">指定日期</label><input type="date" id="spkDate" value="${esc(c.date)}" min="${tpeDay()}" style="width:150px"></div>
  </div>
  <div class="fs w2"><h4>④ 確認並送出</h4>
    <div class="sum" id="spkSum"></div><div class="why" id="spkWhy" role="status"></div>
    <div class="acts"><a class="btn pri" id="spkSave" target="_blank" rel="noopener noreferrer" role="button">送出排程設定（開 GitHub）</a>
      <a class="btn" id="spkNow" target="_blank" rel="noopener noreferrer" role="button" title="只依①的類型與項數、現在就產一份，不改排程">立刻產一份（開 GitHub）</a>
      <button type="button" id="spkCopyJ">複製設定 JSON</button></div>
    <details id="spkJd"><summary>設定 JSON（本部讀的格式）</summary><pre id="spkJson"></pre></details>
  </div>
</div>`;
  }
  function timesHtml() {
    const c = S.sched;
    return c.times.map((t, i) => `<span class="t"><input type="time" data-ti="${i}" value="${esc(t)}" aria-label="執行時間 ${i + 1}"><button type="button" data-tdel="${i}" aria-label="刪除這個時段" title="刪除這個時段"${c.times.length < 2 ? ' disabled style="opacity:.3"' : ''}>×</button></span>`).join('')
      + (c.times.length < 6 ? '<button type="button" id="spkTAdd">＋ 加一個時段</button>' : '');
  }
  function syncSched(v) {
    const c = S.sched;
    $$('.kr', v).forEach((r) => { const k = r.dataset.kind, n = c.kinds[k] || 0; r.classList.toggle('off', n <= 0); $('input[data-kc]', r).checked = n > 0; const i = $('input[data-kn]', r); if (document.activeElement !== i) i.value = String(n); });
    $$('#spkFreq button', v).forEach((b) => { const on = b.dataset.f === c.freq; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
    $('#spkWk', v).hidden = c.freq !== 'weekly'; $('#spkOnce', v).hidden = c.freq !== 'once';
    $$('#spkWk button', v).forEach((b) => { const on = c.days.includes(+b.dataset.d); b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    const e1 = schedErr('set_schedule'), e2 = schedErr('run_now');
    $('#spkSum', v).textContent = e1 && e2 ? '' : e1 ? schedSummary('run_now') : schedSummary('set_schedule');
    $('#spkWhy', v).textContent = e1 ? '無法送出排程：' + e1 : '';
    const set = (a, err, act) => { if (err) { a.removeAttribute('href'); a.setAttribute('aria-disabled', 'true'); a.title = err; } else { const q = schedIssue(act); a.href = issueUrl(q.title, q.body, q.label); a.removeAttribute('aria-disabled'); a.title = '開新分頁：GitHub 新 Issue（' + q.title + '）'; } };
    set($('#spkSave', v), e1, 'set_schedule'); set($('#spkNow', v), e2, 'run_now');
    $('#spkJson', v).textContent = e1 ? '（設定還不完整：' + e1 + '）' : JSON.stringify(schedJson('set_schedule'), null, 2);
    const cj = $('#spkCopyJ', v); cj.disabled = !!e1; cj.style.opacity = e1 ? '.45' : '';
    saveSched();
  }
  function bindSched(v) {
    const c = S.sched, tm = $('#spkTimes', v);
    const paintT = () => { tm.innerHTML = timesHtml(); };
    paintT();
    tm.oninput = (e) => { const t = e.target.closest('input[data-ti]'); if (!t) return; if (/^\d\d:\d\d$/.test(t.value)) c.times[+t.dataset.ti] = t.value; syncSched(v); };
    tm.onclick = (e) => {
      if (e.target.closest('#spkTAdd')) { c.times.push(c.times[c.times.length - 1] || '21:50'); paintT(); syncSched(v); const l = $$('input[data-ti]', tm); if (l.length) l[l.length - 1].focus(); return; }
      const d = e.target.closest('button[data-tdel]'); if (d && c.times.length > 1) { c.times.splice(+d.dataset.tdel, 1); paintT(); syncSched(v); }
    };
    v.querySelector('.fm').addEventListener('click', (e) => {
      const st = e.target.closest('button[data-st]');
      if (st) { const k = st.closest('.kr').dataset.kind; c.kinds[k] = Math.max(0, Math.min(9, (c.kinds[k] || 0) + (+st.dataset.st))); syncSched(v); return; }
      const f = e.target.closest('#spkFreq button'); if (f) { c.freq = f.dataset.f; syncSched(v); return; }
      const d = e.target.closest('#spkWk button'); if (d) { const n = +d.dataset.d; c.days = c.days.includes(n) ? c.days.filter((x) => x !== n) : c.days.concat(n); syncSched(v); }
    });
    v.querySelector('.fm').addEventListener('change', (e) => {
      const kc = e.target.closest('input[data-kc]'); if (kc) { c.kinds[kc.dataset.kc] = kc.checked ? Math.max(1, c.kinds[kc.dataset.kc] || 1) : 0; syncSched(v); return; }
      const kn = e.target.closest('input[data-kn]'); if (kn) { const n = Math.round(Number(kn.value)); c.kinds[kn.dataset.kn] = n >= 0 && n <= 9 ? n : Math.max(0, Math.min(9, n || 0)); syncSched(v); return; }
      const dt = e.target.closest('#spkDate'); if (dt) { c.date = dt.value; syncSched(v); }
    });
    $('#spkCopyJ', v).onclick = async () => { if (schedErr('set_schedule')) return; toast((await copyText(JSON.stringify(schedJson('set_schedule'), null, 2))) ? '已複製設定 JSON' : '複製失敗'); };
    syncSched(v);
  }

  /* ---------------------------------------------------------------- 外殼 */
  function paint(v) {
    css();
    if (!isAdmin()) {
      S.admin = false;
      v.innerHTML = '<div class="card spk" id="spkDenied"><div class="hd"><h3>社群選題</h3></div><p class="muted">這一頁只有管理者看得到' + (window.TwAccount && window.TwAccount.user && window.TwAccount.user() ? '' : '，請先登入') + '。</p></div>';
      return;
    }
    S.admin = true;
    const m = S.menu;
    v.innerHTML = `<div class="card spk" id="spkRoot">
  <div class="hd"><h3>社群選題</h3>${m && m.example ? '<span class="ex" id="spkExB">範例</span>' : ''}<span class="sp"></span><span class="muted" style="margin:0" id="spkDt">${m ? '清單日期 ' + esc(m.date) + (m.updated ? '・更新 ' + esc(m.updated.replace('T', ' ').slice(0, 16)) : '') : ''}</span></div>
  <p class="muted how-d"><b>怎麼用：</b>在「今日選題」勾想做的題目，按「送出選擇」；沒勾的不做。想改成別的時間、別的類型或項數，切到「產主題設定」。送出＝開 GitHub 新 Issue，按那頁的 Submit new issue 才算數。</p>
  <div class="nbsw lv2" id="spkTabs" role="tablist" aria-label="社群選題分頁"><button type="button" role="tab" data-t="pick" class="${S.tab === 'pick' ? 'on' : ''}" aria-selected="${S.tab === 'pick'}">今日選題</button><button type="button" role="tab" data-t="sched" class="${S.tab === 'sched' ? 'on' : ''}" aria-selected="${S.tab === 'sched'}">產主題設定</button></div>
  <div class="nbbody" id="spkBody">${S.tab === 'pick' ? pickHtml() : schedHtml()}</div>
</div>`;
    $('#spkTabs', v).onclick = (e) => { const b = e.target.closest('button[data-t]'); if (!b || b.dataset.t === S.tab) return; S.tab = b.dataset.t; paint(v); };
    if (S.tab === 'pick') bindPick(v); else bindSched(v);
  }
  let seq = 0;
  async function render(v) {
    css(); S.admin = isAdmin(); loadSched();
    if (!S.admin) { paint(v); return; }
    const my = ++seq;
    if (!S.menu) { S.loading = true; paint(v); S.loading = false; await loadMenu(true); }
    if (my !== seq || location.hash !== '#admin/social') return;
    paint(v);
  }

  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'social') return null;
    const T = window.TwSub; const v = T && T.view ? T.view('v-subadm') : document.getElementById('v-subadm'); if (!v) return null;
    S.tab = 'pick'; S.kind = '';   // 換頁回來一律是預設（今日選題、全部類型）；勾選與設定另存 localStorage
    render(v);
    return 'v-subadm';
  });
  // 管理者身分是非同步回來的（登入、/v1/me）：身分真的變了才重畫，避免心跳刷新時把還沒送出的操作重畫掉
  window.addEventListener('tw:account', () => {
    if (location.hash !== '#admin/social') return;
    const v = document.getElementById('v-subadm'); if (!v) return;
    if (isAdmin() !== S.admin) render(v);
  });
  window.TwSocialPick = { state: () => S, issueUrl, schedJson, pickIssue, schedIssue };
})();
