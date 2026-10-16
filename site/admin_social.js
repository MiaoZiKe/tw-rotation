/* 管理區：社群選題（#admin/social）—— 2026-10-19，Andy：「告訴網頁 team 需要新增一種方式讓我可以選擇主題」
   ----------------------------------------------------------------------------
   社群媒體部每天產出「每日選題清單」，Andy 只重新整理網頁、不下本機指令，所以改成在網站上點選今天要做哪幾題。
   流程（v1，零後端）：
     ① 讀 social/menu_latest.json（本部每天 commit，不是 build 產物；格式 docs/marketing/social_unit/menu_json_spec.md）
     ② 每題一張卡：勾選框＋題目＋類型＋三個狀態晶片（圖表／查證／產出）＋⚠ 法遵紅旗；點卡展開「這次內文會講」等細節（預設收起）
     ③ 「送出選擇」＝一個預填好的 GitHub 新 Issue 連結（新分頁），Andy 在手機按「Submit new issue」即完成；
        備援「複製指令」。勾選狀態存 localStorage（依清單日期），重新整理不掉。
   ★ 只有管理者看得到：導覽（側欄、手機帳號選單）只對 u.admin 長出入口；網址直接打進來，非管理者只看到一句說明，
     連 menu_latest.json 都不去抓（檔案本身是 public 的，頁面只是不展示）。
   ★ 不碰後端：沒有新的 Worker 端點。v2 評估見 docs/marketing/social_unit/menu_json_spec.md 之外的回報。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const REPO = 'MiaoZiKe/tw-rotation';
  const LABEL = 'social-pick';
  const LS_KEY = 'tw.social.pick';
  const KINDS = ['最新消息', '產業延伸', '精選文章', '總經名詞'];
  const lsGet = () => { try { return JSON.parse(localStorage.getItem(LS_KEY) || 'null'); } catch (e) { return null; } };
  const lsSet = (o) => { try { localStorage.setItem(LS_KEY, JSON.stringify(o)); } catch (e) { /* 私密視窗：只在這次有效 */ } };
  const tpeToday = () => new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10);
  const SCH_KEY = 'tw.social.sched';
  const LABEL2 = 'social-schedule';
  const DAYN = ['日', '一', '二', '三', '四', '五', '六'];
  const TIMES = ['07:30', '12:00', '18:00', '21:50'];
  const FREQ = { daily: '每天', weekday: '僅工作日（週一到五）', days: '指定星期幾', date: '指定某一天（只跑那天）', now: '只跑一次，現在就產' };
  const schDef = () => ({ types: { 最新消息: 2, 產業延伸: 2, 精選文章: 1, 總經名詞: 1 }, freq: 'daily', days: [1, 2, 3, 4, 5], date: '', times: ['21:50'] });
  const schLoad = () => { try { const o = JSON.parse(localStorage.getItem(SCH_KEY) || 'null'); if (o && o.types && o.freq) return Object.assign(schDef(), o); } catch (e) { /* 私密視窗 */ } return schDef(); };
  const schSave = () => { try { localStorage.setItem(SCH_KEY, JSON.stringify(SCH)); } catch (e) { /* 私密視窗 */ } };
  let SCH = schDef();
  const schTypes = () => KINDS.filter((k) => SCH.types[k] > 0).map((k) => ({ kind: k, n: SCH.types[k] }));
  /* 設定 JSON（格式見 menu_json_spec.md「schedule」）＋人看得懂的摘要；now=true 時是「立刻產一份」 */
  function schPayload(now) {
    const cfg = { v: 1, tz: 'Asia/Taipei', types: schTypes(), freq: now ? 'now' : SCH.freq, times: now ? [] : SCH.times.slice().sort() };
    if (!now && SCH.freq === 'days') cfg.days = SCH.days.slice().sort();
    if (!now && SCH.freq === 'date') cfg.date = SCH.date;
    const when = now ? '現在立刻產一份' : `${FREQ[cfg.freq]}${cfg.days ? '（週' + cfg.days.map((d) => DAYN[d]).join('、') + '）' : ''}${cfg.date ? '（' + cfg.date + '）' : ''}，台北時間 ${cfg.times.join('、') || '（未選）'}`;
    const sum = cfg.types.map((t) => `${t.kind} ${t.n} 項`).join('、') || '（未選類型）';
    const title = now ? `立刻產選題清單 ${tpeToday()}` : `選題排程設定 ${tpeToday()}`;
    const body = [`## 摘要`, `- 類型與數量：${sum}`, `- 時間：${when}`, '', '## 設定 JSON（本部讀這段）', '```json', JSON.stringify(cfg, null, 2), '```'].join('\n');
    const url = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=${LABEL2}`;
    return { cfg, title, body, url, sum, when };
  }
  function schErr(now) {
    if (!schTypes().length) return '至少要選一種類型、數量大於 0';
    if (now) return '';
    if (SCH.freq === 'days' && !SCH.days.length) return '請選至少一個星期幾';
    if (SCH.freq === 'date' && !/^\d{4}-\d\d-\d\d$/.test(SCH.date)) return '請選哪一天';
    if (SCH.freq !== 'now' && !SCH.times.length) return '至少選一個執行時間';
    return '';
  }
  const S = { menu: null, sel: new Set(), open: new Set(), err: '', loading: false };

  /* 只留清單裡真的存在的欄位型別，壞資料不讓整頁掛掉 */
  function clean(j) {
    if (!j || !Array.isArray(j.items)) return null;
    const items = j.items.filter((x) => x && x.id && x.title).map((x) => ({
      id: String(x.id), kind: KINDS.includes(x.kind) ? x.kind : String(x.kind || '其他'), title: String(x.title),
      will_cover: Array.isArray(x.will_cover) ? x.will_cover.map(String) : [],
      chart: { has: !!(x.chart && x.chart.has), note: String((x.chart && x.chart.note) || '') },
      images_needed: Array.isArray(x.images_needed) ? x.images_needed.map(String) : [],
      verified: { status: x.verified && x.verified.status === '已查證' ? '已查證' : '待查證', who: String((x.verified && x.verified.who) || '') },
      output: String(x.output || ''), flags: Array.isArray(x.flags) ? x.flags.map(String) : [],
    }));
    return { date: String(j.date || ''), sample: !!j.sample, note: String(j.note || ''), items };
  }
  const picked = () => (S.menu ? S.menu.items.filter((x) => S.sel.has(x.id)) : []);
  /* 送出內容：標題、內文、指令都由同一處組出來，連結與預覽不會各算各的 */
  function payload() {
    const m = S.menu, ps = picked();
    const title = `每日選題勾選 ${m.date}${m.sample ? '（範例）' : ''}`;
    const cmd = `產出 ${ps.map((x) => x.id).join('、')}，交 GPT 交接包`;
    const body = [`清單日期：${m.date}${m.sample ? '（範例資料）' : ''}`, ''].concat(ps.map((x) => `- [x] ${x.id} ${x.title}`), ['', `指令：${cmd}`]).join('\n');
    const url = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=${LABEL}`;
    return { title, body, cmd, url };
  }
  function css() {
    T().css('socCss', `
#v-subadm .soc [hidden]{display:none!important}
#v-subadm .soc h3{margin:0;font-size:16px}
#v-subadm .soc .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:0}
#v-subadm .soc .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
#v-subadm .soc .hd .sp{flex:1}
#v-subadm .soc .samp{margin:10px 0 0;padding:8px 12px;border-radius:8px;font-size:13px;line-height:1.55;color:var(--amber);background:color-mix(in srgb,var(--amber) 12%,transparent);border:1px solid color-mix(in srgb,var(--amber) 45%,transparent)}
#v-subadm .soc .bar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px}
#v-subadm .soc .bar .cnt{font-size:14px;color:var(--ink-2);margin-right:auto}
#v-subadm .soc .bar .cnt b{color:var(--ink);font-size:16px}
#v-subadm .soc .btn,#v-subadm .soc a.btn{display:inline-flex;align-items:center;justify-content:center;height:36px;min-width:32px;padding:0 14px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:14px;cursor:pointer;white-space:nowrap;text-decoration:none;box-sizing:border-box}
#v-subadm .soc .btn.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .soc .btn[aria-disabled="true"]{opacity:.45;cursor:not-allowed;pointer-events:none}
#v-subadm .soc .btn:hover{border-color:var(--cyan)}
#v-subadm .soc .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px;margin-top:14px}
#v-subadm .soc .cd{display:grid;grid-template-columns:44px minmax(0,1fr);align-items:start;border:1px solid var(--line);border-radius:12px;background:var(--panel);transition:border-color .12s,background .12s,box-shadow .12s}
#v-subadm .soc .cd:hover{border-color:var(--line-2);box-shadow:0 6px 18px -10px rgba(0,0,0,.5)}
#v-subadm .soc .cd.on{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 7%,var(--panel))}
#v-subadm .soc .ck{display:flex;align-items:flex-start;justify-content:center;padding-top:14px;cursor:pointer;height:100%}
#v-subadm .soc .ck input{width:22px;height:22px;margin:0;accent-color:var(--cyan);cursor:pointer}
#v-subadm .soc .hdb{all:unset;box-sizing:border-box;display:block;cursor:pointer;padding:12px 14px 12px 0;min-width:0;color:var(--ink)}
#v-subadm .soc .hdb:focus-visible{outline:2px solid var(--cyan);outline-offset:2px;border-radius:8px}
#v-subadm .soc .r1{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--ink-3)}
#v-subadm .soc .kd{display:inline-block;padding:1px 8px;border-radius:999px;border:1px solid var(--line-2);font-size:12px;color:var(--ink-2);white-space:nowrap}
#v-subadm .soc .kd.k0{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 45%,transparent)}
#v-subadm .soc .kd.k1{color:var(--violet);border-color:color-mix(in srgb,var(--violet) 45%,transparent)}
#v-subadm .soc .kd.k2{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 45%,transparent)}
#v-subadm .soc .kd.k3{color:var(--lime);border-color:color-mix(in srgb,var(--lime) 45%,transparent)}
#v-subadm .soc .warn{color:var(--amber);font-weight:700;font-size:12.5px;white-space:nowrap}
#v-subadm .soc .tt{margin:6px 0 0;font-size:15.5px;line-height:1.5;font-weight:700;color:var(--ink)}
#v-subadm .soc .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
#v-subadm .soc .chip{font-size:12px;padding:2px 8px;border-radius:6px;background:var(--panel-3);color:var(--ink-2);white-space:nowrap}
#v-subadm .soc .chip.bad{color:var(--amber)}
#v-subadm .soc .more{font-size:12px;color:var(--cyan);margin-top:8px}
#v-subadm .soc .det{grid-column:2;padding:0 14px 14px 0;font-size:13.5px;line-height:1.65;color:var(--ink-2);border-top:1px dashed var(--line);margin-top:0}
#v-subadm .soc .det h4{margin:10px 0 2px;font-size:12.5px;color:var(--ink-3);font-weight:700}
#v-subadm .soc .det ol,#v-subadm .soc .det ul{margin:0;padding-left:20px}
#v-subadm .soc .det p{margin:0}
#v-subadm .soc .pv{margin-top:14px;border:1px solid var(--line);border-radius:10px;padding:8px 12px}
#v-subadm .soc .pv summary{cursor:pointer;font-size:13.5px;color:var(--ink-2);min-height:32px;display:flex;align-items:center}
#v-subadm .soc .pv pre{margin:8px 0 0;white-space:pre-wrap;word-break:break-all;font-size:12.5px;line-height:1.6;color:var(--ink);background:var(--panel-3);border-radius:8px;padding:10px;max-height:260px;overflow:auto}
#v-subadm .soc .st{font-size:13px;min-height:18px;margin-top:8px}
#v-subadm .soc .st.ok{color:var(--fall,#2fbf71)}
#v-subadm .soc .sch{margin-top:14px;border:1px solid var(--line);border-radius:10px;padding:8px 12px}
#v-subadm .soc .sch>summary{cursor:pointer;font-size:14.5px;font-weight:700;min-height:32px;display:flex;align-items:center}
#v-subadm .soc .sch .sr{display:grid;grid-template-columns:128px minmax(0,1fr);gap:8px 12px;align-items:start;margin-top:10px}
#v-subadm .soc .sch .sr>b{font-size:13px;color:var(--ink-2);padding-top:6px;font-weight:600}
#v-subadm .soc .sch .wrap{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#v-subadm .soc .sch label.pk{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 10px;border:1px solid var(--line-2);border-radius:8px;font-size:13.5px;cursor:pointer;background:var(--panel-3)}
#v-subadm .soc .sch label.pk:has(input:checked){border-color:var(--cyan);color:var(--cyan)}
#v-subadm .soc .sch label.pk input[type=checkbox]{margin:0;accent-color:var(--cyan);width:16px;height:16px}
#v-subadm .soc .sch input[type=number],#v-subadm .soc .sch input[type=time],#v-subadm .soc .sch input[type=date],#v-subadm .soc .sch select{height:32px;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px;font:inherit;font-size:14px}
#v-subadm .soc .sch input[type=number]{width:60px}
#v-subadm .soc .sch .note{margin-top:12px;padding:8px 12px;border-radius:8px;font-size:13px;line-height:1.55;color:var(--amber);background:color-mix(in srgb,var(--amber) 12%,transparent);border:1px solid color-mix(in srgb,var(--amber) 45%,transparent)}
#v-subadm .soc .sch .sum{margin-top:10px;font-size:13px;color:var(--ink-2);line-height:1.6}
@media (max-width:640px){
  #v-subadm .soc .sch .sr{grid-template-columns:minmax(0,1fr);gap:4px}
  #v-subadm .soc .sch .sr>b{padding-top:6px}
  #v-subadm .soc .grid{grid-template-columns:minmax(0,1fr);gap:8px;margin-top:10px}
  #v-subadm .soc #socAll,#v-subadm .soc .socnote,#v-subadm .soc .more,#v-subadm .soc .chips .chip:nth-child(3){display:none!important}
  #v-subadm .soc .samp{margin-top:8px;padding:5px 10px;font-size:12px}
  #v-subadm .soc .bar{margin-top:8px}
  #v-subadm .soc .st{min-height:0;margin-top:4px}
  #v-subadm .soc .st:empty{display:none}
  #v-subadm .soc .hdb{padding:10px 12px 10px 0}
  #v-subadm .soc .ck{padding-top:12px}
  #v-subadm .soc .chips{margin-top:6px}
  #v-subadm .soc .cd{grid-template-columns:44px minmax(0,1fr)}
  #v-subadm .soc .tt{font-size:15px;margin-top:4px}
  #v-subadm .soc .bar .btn{flex:1 1 auto}
  #v-subadm .soc .bar .cnt{flex:1 1 100%}
}`);
  }
  function card(x, i) {
    const on = S.sel.has(x.id), op = S.open.has(x.id), k = Math.max(0, KINDS.indexOf(x.kind));
    const warn = x.flags.length;
    return `<article class="cd${on ? ' on' : ''}" data-id="${esc(x.id)}">
      <label class="ck" title="勾選這一題"><input type="checkbox" class="socck" data-id="${esc(x.id)}"${on ? ' checked' : ''} aria-label="勾選 ${esc(x.id)} ${esc(x.title)}"></label>
      <button type="button" class="hdb socopen" data-id="${esc(x.id)}" aria-expanded="${op}">
        <span class="r1"><span class="kd k${k}">${esc(x.kind)}</span><span>${esc(x.id)}</span>${warn ? `<span class="warn" title="${esc(x.flags.join('、'))}">⚠ ${esc(x.flags.join('、'))}</span>` : ''}</span>
        <span class="tt" style="display:block">${esc(x.title)}</span>
        <span class="chips" style="display:flex"><span class="chip">${x.chart.has ? '圖表：有' : '圖表：無'}</span><span class="chip${x.verified.status === '已查證' ? '' : ' bad'}">${esc(x.verified.status)}</span><span class="chip">${esc(x.output || '產出未定')}</span></span>
        <span class="more" style="display:block">${op ? '收起細節 ▴' : '看細節 ▾'}</span>
      </button>
      <div class="det" ${op ? '' : 'hidden'}>
        <h4>這次內文會講</h4><ol>${x.will_cover.map((w) => `<li>${esc(w)}</li>`).join('') || '<li>（尚未填）</li>'}</ol>
        <h4>圖表</h4><p>${x.chart.has ? '有：' + esc(x.chart.note || '（未說明）') : '無'}</p>
        <h4>圖片需補充</h4>${x.images_needed.length ? `<ul>${x.images_needed.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>` : '<p>不需要</p>'}
        <h4>查證</h4><p>${esc(x.verified.status)}${x.verified.who ? '・' + esc(x.verified.who) : ''}${x.verified.status === '待查證' ? '（查完才算可立即發）' : ''}</p>
        <h4>預估產出</h4><p>${esc(x.output || '未定')}</p>
        ${warn ? `<h4>法遵紅旗</h4><p>⚠ ${esc(x.flags.join('、'))}（發佈前法遵要過一次）</p>` : ''}
      </div></article>`;
  }
  function paint(v) {
    const m = S.menu;
    const stale = m.date && m.date !== tpeToday();
    v.innerHTML = `<div class="card soc" id="soc">
      <div class="hd"><h3>社群選題</h3><span class="muted">清單日期 <b id="socDate">${esc(m.date)}</b>・共 ${m.items.length} 題</span><span class="sp"></span>
        <button type="button" class="btn" id="socAll">全部展開</button></div>
      ${m.sample ? '<div class="samp" id="socSample" role="note">範例資料：虛構題目，非真實清單</div>' : ''}
      ${stale ? `<div class="samp" id="socStale" role="note">清單是 ${esc(m.date)} 的，不是今天（${tpeToday().slice(5)}）</div>` : ''}
      ${m.note ? `<p class="muted socnote" style="margin-top:8px">${esc(m.note)}</p>` : ''}
      <div class="bar"><span class="cnt">已選 <b id="socCount">0</b> / ${m.items.length} 題</span>
        <button type="button" class="btn" id="socClear">清除勾選</button>
        <button type="button" class="btn" id="socCopy">複製指令</button>
        <a class="btn pri" id="socSubmit" target="_blank" rel="noopener noreferrer" aria-disabled="true">送出選擇</a></div>
      <div class="st" id="socSt" role="status"></div>
      <div class="grid" id="socGrid">${m.items.map(card).join('')}</div>
      <details class="sch" id="socSch"><summary>產主題設定（類型、時間、頻率）</summary><div id="socSchBody"></div></details>
      <details class="pv" id="socPv"><summary>送出內容預覽（會建立的 GitHub Issue）</summary><pre id="socPre"></pre></details>
      <p class="muted" style="margin-top:12px">用法：勾好題目 → 按「送出選擇」，新分頁會開 GitHub 的新 Issue（已填好標題與內容）→ 在手機或電腦按「Submit new issue」。本部讀到 Issue 就開始產出，並交接給 GPT 做圖文。按不開時改用「複製指令」貼到對話。</p>
    </div>`;
    sync(v);
    bind(v);
    paintSch(v);
  }
  /* 勾選變了只更新數字、連結、卡片外框，不整頁重畫（不然展開狀態與捲動位置會被洗掉）*/
  function sync(v) {
    const n = S.sel.size, sub = v.querySelector('#socSubmit'), cp = v.querySelector('#socCopy'), clr = v.querySelector('#socClear');
    v.querySelector('#socCount').textContent = String(n);
    v.querySelectorAll('.cd').forEach((c) => c.classList.toggle('on', S.sel.has(c.dataset.id)));
    v.querySelectorAll('.socck').forEach((c) => { c.checked = S.sel.has(c.dataset.id); });
    if (n) {
      const p = payload();
      sub.href = p.url; sub.setAttribute('aria-disabled', 'false'); sub.removeAttribute('tabindex');
      v.querySelector('#socPre').textContent = `標題：${p.title}\n標籤：${LABEL}\n\n${p.body}\n\n連結：\n${p.url}`;
    } else {
      sub.removeAttribute('href'); sub.setAttribute('aria-disabled', 'true'); sub.setAttribute('tabindex', '-1');
      v.querySelector('#socPre').textContent = '還沒勾任何題目。';
    }
    cp.setAttribute('aria-disabled', n ? 'false' : 'true'); clr.setAttribute('aria-disabled', n ? 'false' : 'true');
    lsSet({ date: S.menu.date, ids: [...S.sel] });
  }
  function paintSch(v) {
    const box = v.querySelector('#socSchBody'); if (!box) return;
    const ch = (a, x) => (a.includes(x) ? ' checked' : '');
    box.innerHTML = `
      <div class="sr"><b>類型與數量</b><div class="wrap">${KINDS.map((k) => `<label class="pk"><input type="checkbox" data-sk="${k}"${SCH.types[k] > 0 ? ' checked' : ''} aria-label="${k}">${k}<input type="number" min="1" max="5" data-sn="${k}" value="${SCH.types[k] > 0 ? SCH.types[k] : 1}" ${SCH.types[k] > 0 ? '' : 'disabled '}aria-label="${k} 項數"> 項</label>`).join('')}</div>
      <b>頻率</b><div class="wrap"><select id="schFreq" aria-label="頻率">${Object.keys(FREQ).map((k) => `<option value="${k}"${SCH.freq === k ? ' selected' : ''}>${FREQ[k]}</option>`).join('')}</select></div>
      <b class="sc-days"${SCH.freq === 'days' ? '' : ' hidden'}>星期幾</b><div class="wrap sc-days"${SCH.freq === 'days' ? '' : ' hidden'}>${[1, 2, 3, 4, 5, 6, 0].map((d) => `<label class="pk"><input type="checkbox" data-sd="${d}"${ch(SCH.days, d)}>週${DAYN[d]}</label>`).join('')}</div>
      <b class="sc-date"${SCH.freq === 'date' ? '' : ' hidden'}>哪一天</b><div class="wrap sc-date"${SCH.freq === 'date' ? '' : ' hidden'}><input type="date" id="schDate" value="${esc(SCH.date)}" aria-label="指定日期"></div>
      <b class="sc-time"${SCH.freq === 'now' ? ' hidden' : ''}>執行時間（台北）</b><div class="wrap sc-time"${SCH.freq === 'now' ? ' hidden' : ''}>${TIMES.map((t) => `<label class="pk"><input type="checkbox" data-st="${t}"${ch(SCH.times, t)}>${t}</label>`).join('')}
        ${SCH.times.filter((t) => !TIMES.includes(t)).map((t) => `<label class="pk"><input type="checkbox" data-st="${t}" checked>${t}</label>`).join('')}
        <input type="time" id="schCustom" aria-label="自訂時間"><button type="button" class="btn" id="schAddT">加入時段</button></div></div>
      <div class="sum" id="schSum"></div>
      <div class="note" role="note">設定會在下一個處理週期（最多數小時）生效。要立刻生效，請在對話裡告訴 CEO。</div>
      <div class="bar"><span class="cnt" id="schErr" style="color:var(--amber)"></span>
        <a class="btn" id="schNow" target="_blank" rel="noopener noreferrer">立刻產一份</a>
        <a class="btn pri" id="schGo" target="_blank" rel="noopener noreferrer">送出排程設定</a></div>`;
    const up = () => {
      schSave();
      const p = schPayload(false), e = schErr(false), e2 = schErr(true), g = box.querySelector('#schGo'), n = box.querySelector('#schNow');
      box.querySelector('#schSum').textContent = `將設定為：${p.sum}；${p.when}`;
      box.querySelector('#schErr').textContent = e || '';
      if (e) { g.removeAttribute('href'); g.setAttribute('aria-disabled', 'true'); } else { g.href = p.url; g.setAttribute('aria-disabled', 'false'); }
      if (e2) { n.removeAttribute('href'); n.setAttribute('aria-disabled', 'true'); } else { n.href = schPayload(true).url; n.setAttribute('aria-disabled', 'false'); }
    };
    box.querySelectorAll('[data-sk]').forEach((c) => { c.onchange = () => { const n = box.querySelector(`[data-sn="${c.dataset.sk}"]`); n.disabled = !c.checked; SCH.types[c.dataset.sk] = c.checked ? Math.max(1, +n.value || 1) : 0; up(); }; });
    box.querySelectorAll('[data-sn]').forEach((n) => { n.onchange = () => { n.value = Math.min(5, Math.max(1, +n.value || 1)); SCH.types[n.dataset.sn] = +n.value; up(); }; });
    box.querySelector('#schFreq').onchange = (e) => { SCH.freq = e.target.value; schSave(); paintSch(v); };
    box.querySelectorAll('[data-sd]').forEach((c) => { c.onchange = () => { const d = +c.dataset.sd; SCH.days = SCH.days.filter((x) => x !== d).concat(c.checked ? [d] : []); up(); }; });
    const dt = box.querySelector('#schDate'); if (dt) dt.onchange = () => { SCH.date = dt.value; up(); };
    box.querySelectorAll('[data-st]').forEach((c) => { c.onchange = () => { SCH.times = SCH.times.filter((x) => x !== c.dataset.st).concat(c.checked ? [c.dataset.st] : []); up(); }; });
    box.querySelector('#schAddT').onclick = () => { const t = box.querySelector('#schCustom').value; if (/^\d\d:\d\d$/.test(t) && !SCH.times.includes(t)) { SCH.times.push(t); schSave(); paintSch(v); } };
    [['#schGo', false], ['#schNow', true]].forEach(([sel, now]) => box.querySelector(sel).addEventListener('click', (e) => {
      if (schErr(now)) { e.preventDefault(); return; }
      const st = v.querySelector('#socSt'); if (st) { st.textContent = '已在新分頁打開 GitHub 新 Issue：按「Submit new issue」才算送出；設定會在下一個處理週期（最多數小時）生效'; st.className = 'st ok'; }
    }));
    up();
  }
  async function copy(t) {
    try { await navigator.clipboard.writeText(t); return true; } catch (e) { /* 沒權限：退回選取複製 */ }
    try {
      const ta = document.createElement('textarea'); ta.value = t; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0';
      document.body.appendChild(ta); ta.select(); const ok = document.execCommand('copy'); ta.remove(); return !!ok;
    } catch (e) { return false; }
  }
  function bind(v) {
    const st = (m, ok) => { const e = v.querySelector('#socSt'); if (e) { e.textContent = m; e.className = 'st' + (ok ? ' ok' : ''); } };
    v.querySelector('#socGrid').addEventListener('change', (e) => {
      const c = e.target.closest('.socck'); if (!c) return;
      if (c.checked) S.sel.add(c.dataset.id); else S.sel.delete(c.dataset.id);
      sync(v); st('');
    });
    v.querySelector('#socGrid').addEventListener('click', (e) => {
      const b = e.target.closest('.socopen'); if (!b) return;
      const id = b.dataset.id, card = b.closest('.cd'), d = card.querySelector('.det');
      if (S.open.has(id)) S.open.delete(id); else S.open.add(id);
      const op = S.open.has(id);
      d.hidden = !op; b.setAttribute('aria-expanded', String(op)); b.querySelector('.more').textContent = op ? '收起細節 ▴' : '看細節 ▾';
    });
    v.querySelector('#socAll').onclick = (e) => {
      const all = S.open.size < S.menu.items.length;
      S.open = new Set(all ? S.menu.items.map((x) => x.id) : []);
      v.querySelectorAll('.cd').forEach((c) => { const op = S.open.has(c.dataset.id); c.querySelector('.det').hidden = !op; c.querySelector('.socopen').setAttribute('aria-expanded', String(op)); c.querySelector('.more').textContent = op ? '收起細節 ▴' : '看細節 ▾'; });
      e.currentTarget.textContent = all ? '全部收起' : '全部展開';
    };
    v.querySelector('#socClear').onclick = () => { S.sel.clear(); sync(v); st('已清除勾選'); };
    v.querySelector('#socCopy').onclick = async () => {
      if (!S.sel.size) { st('先勾至少一題'); return; }
      const p = payload(), ok = await copy(p.cmd);
      st(ok ? '已複製：' + p.cmd : '這個瀏覽器不讓程式複製，請改按「送出內容預覽」自己選取：' + p.cmd, ok);
    };
    v.querySelector('#socSubmit').addEventListener('click', (e) => {
      if (!S.sel.size) { e.preventDefault(); st('先勾至少一題'); return; }
      st('已在新分頁打開 GitHub 新 Issue：到那邊按「Submit new issue」才算送出', true);
    });
  }
  async function render(v) {
    css();
    const A = T().A(), u = A && A.on() ? A.user() : null;
    if (!u || !u.admin) {
      v.innerHTML = `<div class="card soc"><h3>社群選題</h3><p class="muted" style="margin-top:6px">這一頁只有管理者看得到${u ? '' : '，請先登入'}。</p></div>`;
      return;
    }
    v.innerHTML = '<div class="card soc"><p class="muted">載入今日選題清單…</p></div>';
    let j = null;
    try { const r = await fetch('social/menu_latest.json', { cache: 'no-store' }); if (r.ok) j = await r.json(); } catch (e) { j = null; }
    if (!(location.hash || '').startsWith('#admin/social')) return;
    const m = clean(j);
    if (!m || !m.items.length) { v.innerHTML = '<div class="card soc"><h3>社群選題</h3><p class="muted" style="margin-top:6px">今天的選題清單還沒上線（<code>social/menu_latest.json</code> 讀不到或是空的）。社群媒體部每天整理好會自動放上來，晚點再重新整理。</p></div>'; return; }
    S.menu = m;
    const old = lsGet();
    S.sel = new Set(old && old.date === m.date && Array.isArray(old.ids) ? old.ids.filter((id) => m.items.some((x) => x.id === id)) : []);
    S.open = new Set();
    SCH = schLoad();
    paint(v);
  }
  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'social' || !T()) return null;
    const v = T().view('v-subadm'); if (!v) return null;
    render(v);
    return 'v-subadm';
  });
  /* 登入狀態晚到（重新整理直接開這頁時 /v1/me 還沒回來）→ 回來之後重畫一次 */
  window.addEventListener('tw:account', () => {
    if ((location.hash || '').startsWith('#admin/social') && T()) { const v = document.getElementById('v-subadm'); if (v) render(v); }
  });
  window.TwAdminSocial = { render, payload, schPayload, picked: () => picked().map((x) => x.id) };
})();
