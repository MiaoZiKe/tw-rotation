/* ==================================================================================
   設計 v4：三主題切換＋外觀設定面板＋圖表共用規格＋每張卡的「一句結論」
   規格：docs/design_v4/01_設計系統.md（§3 主題、§4 圖表、§6 卡片排法）；套用紀錄：docs/design_v4/02_套用第一批.md
   ★ 2026-09-28 正式套用（Andy「V4執行」）：預設科技 HUD 深色；原型的「現行（不套 v4）」選項拿掉 ——
     「多主題是同一套骨架換皮」，保留舊骨架等於維護兩套網站。

   做四件事，**不改任何功能邏輯、不改資料**：
   1. 外觀設定面板：頂欄「外觀」鈕（桌機）打開 → 只有風格三選一；手機在「⋯ 更多工具」清單加一段風格
      （明暗那列本來就在清單裡）。風格存 localStorage `tw.theme4`（casual／hud／pro）。
      ★ 2026-10-03（Andy 看著外觀面板與旁邊的 🌙 鈕：「這邊重複到了，改進」）：面板裡原本的「明暗：深色｜淺色」二段式拿掉，
        明暗只剩右上角 ☀／🌙（#themeBtn，app.js applyTheme，存 `tw.theme`）一個入口 —— 同一件事兩個開關，
        使用者會懷疑兩個是不是管不同東西；而且 Andy 先前已經指定「明暗用原來的圖示，放右上」。面板說明改成指向那顆鈕。
   2. 切風格後呼叫 App.applyTheme(目前明暗, true)：圖表顏色本來就是 refreshPalette() 從 CSS 變數讀的，重畫一次就全部換色。
   3. 圖表共用規格（§4）：app.js 的 chart() 在 setOption 前呼叫 window.T4.normalize(option)——
      只留水平格線（x 軸是類別／時間軸、或 y 軸全是數值軸的圖，x 軸的直向格線關掉）、
      圖例字 12px，以及「圖例在上方時繪圖區頂端至少讓出 28px」，圖例不壓到繪圖區。
      軸字 12／提示框 13 與 HUD 虛線格線寫在 app.js 的 axisStyle／tip／refreshPalette（讀 --t4-grid-type）。
   4. 一句結論（.t4-lede）：插在卡片標題列正下方。**每一句都從那張圖自己畫出來的資料讀**
      （ECharts 的 getOption()、或卡片上已經顯示的讀數），不另外算、不另外抓 ——
      所以句子裡的每一個數字都指得到圖上真的有的值。讀不到就不插（不留空白、不寫猜的）。
   ================================================================================== */
(function () {
  'use strict';
  const KEY = 'tw.theme4';
  const DEF = 'hud';
  const THEMES = [
    { id: 'casual', name: '親和休閒', sub: '柔和漸層、圓角、暖白與夜紫', sw: 'linear-gradient(135deg,#FFE8DA,#6A55E6)' },
    { id: 'hud', name: '科技 HUD', sub: '透明玻璃、定位框、青色光（預設）', sw: 'linear-gradient(135deg,#050A13,#37E2FF)' },
    { id: 'pro', name: '專業有力', sub: '高對比、方角、粗標題', sw: 'linear-gradient(135deg,#0A0C10,#2E5BDB)' },
  ];
  const $ = (s, r) => (r || document).querySelector(s);
  const valid = (v) => THEMES.some(t => t.id === v);
  /* 目前生效的風格＝<html data-theme4>（<head> 已經掛好）；localStorage 只是下次開站的記憶 */
  const get = () => { const v = document.documentElement.getAttribute('data-theme4'); return valid(v) ? v : DEF; };
  const mode = () => (document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');

  function syncMeta() {
    /* 手機瀏覽器網址列顏色跟頁底一致（applyTheme 寫的是舊主題的兩個固定色，這裡改成讀目前的 --bg） */
    const meta = document.querySelector('meta[name="theme-color"]');
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
    if (meta && bg) meta.setAttribute('content', bg);
  }
  function set(v) {
    if (!valid(v)) v = DEF;
    document.documentElement.setAttribute('data-theme4', v);
    try { localStorage.setItem(KEY, v); } catch (e) { /* 私密視窗：這次有效，下次開站回預設 */ }
    syncButtons();
    // 圖表顏色重新讀 CSS 變數並重畫（既有流程，跟按 ☀ 一樣）
    if (window.App && window.App.applyTheme) window.App.applyTheme(window.App.theme(), true);
    syncMeta();
    window.dispatchEvent(new CustomEvent('tw:theme4', { detail: { theme4: v } }));
    schedule();
  }

  /* 圖表共用規格（01 §4）：chart() 每次 setOption 前過一次。只調「版面」相關的欄位，不動資料與顏色。 */
  const arr = (x) => (Array.isArray(x) ? x : x ? [x] : []);
  function normalize(o) {
    if (!o || typeof o !== 'object') return o;
    try {
      const xs = arr(o.xAxis), ys = arr(o.yAxis);
      if (xs.length && ys.length) {
        const yAllValue = ys.every(y => y && (y.type == null || y.type === 'value' || y.type === 'log'));
        const nx = xs.map(x => {
          if (!x || typeof x !== 'object') return x;
          const cat = x.type === 'category' || x.type === 'time';
          // 已經明確要格線（splitLine.show === true）而且是數值軸的，尊重原圖（例如散佈圖的中線刻意要畫）
          if (x.splitLine && x.splitLine.show === true && !cat) return x;
          if (cat || yAllValue) return { ...x, splitLine: { ...(x.splitLine || {}), show: false } };
          return x;
        });
        o = { ...o, xAxis: Array.isArray(o.xAxis) ? nx : nx[0] };
      }
      const lg = o.legend;
      if (lg && !Array.isArray(lg) && lg.show !== false) {
        const top = lg.bottom == null && lg.orient !== 'vertical' && (lg.top == null || lg.top === 0 || lg.top === 'top');
        o = { ...o, legend: { ...lg, textStyle: { fontSize: 12, ...(lg.textStyle || {}) } } };
        // 圖例在上方：繪圖區頂端至少讓出 28px（圖例一行 ≈ 20px ＋ 8px 間距），不讓圖例壓在繪圖區裡
        if (top && o.grid && !Array.isArray(o.grid) && typeof o.grid.top === 'number' && o.grid.top < 28) {
          o = { ...o, grid: { ...o.grid, top: 28 } };
        }
      }
    } catch (e) { /* 規格化失敗就原樣畫，不能因為外觀讓圖畫不出來 */ }
    return o;
  }

  // ---------------------------------------------------------------- 外觀設定面板
  function buildPop() {
    const pop = document.createElement('div');
    pop.className = 't4pop'; pop.id = 't4Pop'; pop.hidden = true; pop.setAttribute('role', 'dialog');
    pop.setAttribute('aria-label', '外觀設定');
    pop.innerHTML = `<h4>版面風格</h4><div class="t4opts">${THEMES.map(t =>
      `<button type="button" class="t4o" data-t4="${t.id}" aria-pressed="false"><span class="sw" style="background:${t.sw}"></span><b>${t.name}</b><small>${t.sub}</small></button>`).join('')}</div>
      <div class="t4hint">每個風格都有深淺兩套，用右上角 ☀／🌙 切換；選擇會記在這台瀏覽器。</div>`;
    document.body.appendChild(pop);
    pop.addEventListener('click', (e) => {
      const b = e.target.closest('.t4o'); if (b) set(b.dataset.t4);
    });
    return pop;
  }
  function place(pop, btn) {
    const r = btn.getBoundingClientRect();
    pop.style.top = Math.round(r.bottom + 8) + 'px';
    pop.style.left = Math.max(8, Math.round(Math.min(r.right - 260, window.innerWidth - 268))) + 'px';
  }
  function syncButtons() {
    const v = get(), m = mode();
    document.querySelectorAll('[data-t4]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t4 === v)));
    const btn = $('#t4Btn');
    if (btn) { const t = THEMES.find(x => x.id === v); btn.title = `外觀設定（目前：${t.name}・${m === 'light' ? '淺色' : '深色'}）`; }
  }
  function initMenu() {
    const tb = $('#themeBtn');
    if (!tb || $('#t4Btn')) return;
    const btn = document.createElement('button');
    btn.className = 'evbtn t4btn'; btn.id = 't4Btn'; btn.type = 'button';
    btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false'); btn.textContent = '外觀';
    tb.parentNode.insertBefore(btn, tb);
    const pop = buildPop();
    const show = (on) => { pop.hidden = !on; btn.setAttribute('aria-expanded', String(on)); if (on) { syncButtons(); place(pop, btn); } };
    btn.addEventListener('click', (e) => { e.stopPropagation(); show(pop.hidden); });
    document.addEventListener('mousedown', (e) => { if (!pop.hidden && !pop.contains(e.target) && e.target !== btn) show(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !pop.hidden) show(false); });
    window.addEventListener('hashchange', () => show(false));
    window.addEventListener('resize', () => { if (!pop.hidden) place(pop, btn); });
    // ☀ 鈕切明暗之後，「外觀」鈕的提示字（目前：風格・深／淺）與網址列顏色跟著更新
    window.addEventListener('tw:theme', () => { syncButtons(); syncMeta(); });
    // 手機：「⋯ 更多工具」清單加一段（三顆鈕，直接切；明暗那列清單裡原本就有）
    const mp = $('#morePop');
    if (mp && !$('#mmT4', mp)) {
      const box = document.createElement('div');
      box.id = 'mmT4'; box.className = 't4mm';
      box.innerHTML = `<div class="hint" style="margin:6px 0 0;border-top:1px solid var(--line);padding-top:8px">版面風格（電腦版在頂欄「外觀」鈕）</div>` + THEMES.map(t =>
        `<button type="button" data-t4="${t.id}" aria-pressed="false"><span class="ic" style="display:inline-block;width:14px;height:14px;border-radius:4px;background:${t.sw}"></span>${t.name}</button>`).join('');
      // 接在原本那句「這兩項在電腦版是…」的後面，不插在它和那兩列中間（那句說明指的是上面兩列）
      mp.appendChild(box);
      box.addEventListener('click', (e) => { const b = e.target.closest('[data-t4]'); if (b) set(b.dataset.t4); });
    }
    syncButtons();
  }

  // ---------------------------------------------------------------- 一句結論
  const fmtN = (v, d) => Number(v).toLocaleString('zh-TW', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  const sgn = (v, d, u) => { const s = Number(v).toFixed(d); const z = Number(s) === 0; return `${z ? '' : (v > 0 ? '+' : '')}${s}${u || ''}`; };
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');
  function ec(id) {
    const el = document.getElementById(id);
    if (!el || !window.echarts) return null;
    const inst = echarts.getInstanceByDom(el);
    if (!inst) return null;
    try { return inst.getOption(); } catch (e) { return null; }
  }
  const txt = (sel) => { const e = $(sel); return e ? e.textContent.replace(/\s+/g, ' ').trim() : ''; };

  /* 橫條／直條圖：回傳 [{name, v}]（類別軸＋第一個數值序列） */
  function bars(opt, si) {
    if (!opt || !opt.series || !opt.series.length) return [];
    const ax = [].concat(opt.yAxis || [], opt.xAxis || []).find(a => a && a.type === 'category' && a.data);
    if (!ax) return [];
    const s = opt.series[si || 0];
    if (!s || !s.data) return [];
    return ax.data.map((c, i) => {
      const d = s.data[i];
      const v = d == null ? NaN : (typeof d === 'object' ? (Array.isArray(d) ? d[d.length - 1] : d.value) : d);
      return { name: typeof c === 'object' ? (c.value || c.name) : c, v: Number(Array.isArray(v) ? v[v.length - 1] : v) };
    }).filter(x => Number.isFinite(x.v));
  }

  /* 樹圖（treemap）的葉子：遞迴攤平，只留有 value 的節點 */
  function leaves(opt) {
    const out = [];
    const walk = (arr) => (arr || []).forEach(n => { if (n.children && n.children.length) walk(n.children); else if (n.value != null) out.push(n); });
    if (opt && opt.series && opt.series[0]) walk(opt.series[0].data);
    return out;
  }
  const LEDES = {
    /* 資金熱力圖：方塊上寫的就是「資金 ±pp」（rot）或「漲跌 ±%」（chg），方塊大小＝成交值佔比（share）。
       句子只挑兩個極端：佔比最大的那塊、資金 pp 增加最多的那塊 —— 兩個數字都是方塊自己帶的欄位。 */
    ovHeatCard() {
      const L = leaves(ec('heat')).filter(n => Number.isFinite(+n.share));
      if (!L.length) return '';
      const big = L.reduce((a, c) => (+c.share > +a.share ? c : a), L[0]);
      const R = L.filter(n => Number.isFinite(+n.rot));
      const hot = R.length ? R.reduce((a, c) => (+c.rot > +a.rot ? c : a), R[0]) : null;
      const chg = Number.isFinite(+big.chg) ? `，<span class="${cls(+big.chg)}">${sgn(+big.chg, 2, '%')}</span>` : '';
      return `成交值<b>最大</b>：${big.name}（佔 ${(+big.share).toFixed(1)}%${chg}）` +
        (hot && +hot.rot > 0 ? `；資金<b>增加最多</b>：${hot.name} <span class="up">${sgn(+hot.rot, 1, 'pp')}</span>` : '');
    },
    /* 熱門題材：方塊上寫「熱度 N」（heat），大小＝成交值佔比（share） */
    ovThemeCard() {
      const L = leaves(ec('ovTheme')).filter(n => Number.isFinite(+n.heat));
      if (!L.length) return '';
      const hot = L.reduce((a, c) => (+c.heat > +a.heat ? c : a), L[0]);
      const S = L.filter(n => Number.isFinite(+n.share));
      const big = S.length ? S.reduce((a, c) => (+c.share > +a.share ? c : a), S[0]) : null;
      return `<b>最熱</b>：${hot.name}（熱度 ${hot.heat}）` + (big && big !== hot ? `；成交值<b>最大</b>：${big.name}（佔 ${(+big.share).toFixed(1)}%）` : '');
    },
    /* 漲跌家數：直條圖每一格的家數加總（跟圖上數字同一份）。級距名稱第一個字元判斷漲跌。 */
    ovBreadthCard() {
      const b = bars(ec('breadth'));
      if (!b.length) return '';
      let up = 0, dn = 0, fl = 0;
      b.forEach(x => { const n = String(x.name);
        if (n === '平' || n === '0') fl += x.v;
        else if (/^(跌停|<|-)/.test(n)) dn += x.v; else up += x.v; });
      if (!(up + dn)) return '';
      const lead = up > dn ? `漲多於跌` : up < dn ? `跌多於漲` : '漲跌家數相當';
      return `<b>${lead}</b>：上漲 <span class="up">${fmtN(up)}</span> 家、下跌 <span class="down">${fmtN(dn)}</span> 家、平盤 ${fmtN(fl)} 家`;
    },
    /* 法人連續買賣超：卡片右上已經寫著「投信 ≥3 天・買 40 / 賣 40」，照抄成一句，不另外算 */
    ovTrustCard() {
      const s = txt('#streakSub');
      const m = s.match(/(\S+)\s*≥\s*(\d+)\s*天.*?買\s*(\d+).*?賣\s*(\d+)/);
      if (!m) return '';
      const [, who, d, buy, sell] = m;
      const lead = +buy > +sell ? '連買的檔數多於連賣' : +buy < +sell ? '連賣的檔數多於連買' : '連買與連賣檔數相當';
      return `<b>${who}${lead}</b>：連買 ≥${d} 天 <span class="up">${buy}</span> 檔、連賣 <span class="down">${sell}</span> 檔`;
    },
    /* 資金流向排行：橫條圖最上與最下那一根（佔比變化 pp） */
    flowRotCard() {
      const b = bars(ec('rankFlow'));
      if (b.length < 2) return '';
      const s = b.slice().sort((a, c) => c.v - a.v);
      const hi = s[0], lo = s[s.length - 1];
      const nm = (x) => String(x.name).replace(/\s*\d+[↑↓]?$/, '').trim();
      return `資金佔比<b>增加最多</b>：${nm(hi)} <span class="${cls(hi.v)}">${sgn(hi.v, 2, 'pp')}</span>；<b>減少最多</b>：${nm(lo)} <span class="${cls(lo.v)}">${sgn(lo.v, 2, 'pp')}</span>`;
    },
    /* 族群 × 法人：橫條圖第一名（圖上已經排好序） */
    flowInstCard() {
      const o = ec('instGroups');
      const b = bars(o);
      if (!b.length) return '';
      const top = b.reduce((a, c) => (Math.abs(c.v) > Math.abs(a.v) ? c : a), b[0]);
      const nm = String(top.name).replace(/\s+[\d.]+%$/, '');
      const pc = String(top.name).match(/([\d.]+%)$/);
      return `法人淨買超<b>最集中</b>：${nm}${pc ? `（佔 ${pc[1]}）` : ''}`;
    },
  };

  function lede(card, html) {
    /* 找既有的那一句要找「卡片裡任何一層」：資金輪動卡的那一句插在左欄（.rothead 後面），不是卡片的直接子元素。
       原型第一版只找直接子元素 → 每次重畫都再插一句，800px 截圖疊了 14 行（踩過，留作記錄）。*/
    let p = card.querySelector('.t4-lede');
    if (!html) { if (p) p.remove(); return; }
    if (!p) {
      p = document.createElement('p'); p.className = 't4-lede'; p.setAttribute('aria-live', 'polite');
      /* 位置：緊接在標題列下面（說明盒 .howtxt 平常是 hidden、按「?」時搬到浮層，不佔位置，所以不必跳過它）。
         資金輪動卡是兩欄，標題列在左欄裡（.rothead）；其他卡是卡片的第一個 .row.spread。*/
      const head = card.querySelector('.rothead') || card.querySelector(':scope > .row.spread') || card.querySelector(':scope > .row');
      if (head) head.after(p); else card.prepend(p);
    }
    if (p.innerHTML !== html) p.innerHTML = html;
  }
  function decorate() {
    const on = document.documentElement.hasAttribute('data-theme4');
    Object.keys(LEDES).forEach(id => {
      const card = document.getElementById(id);
      if (!card) return;
      let html = '';
      if (on) { try { html = LEDES[id](); } catch (e) { html = ''; } }
      lede(card, html);
    });
  }
  let timer = 0;
  function schedule() { clearTimeout(timer); timer = setTimeout(decorate, 250); }

  function boot() {
    initMenu();
    syncMeta();
    // 圖表是非同步畫的：換頁、改篩選、重畫都會動到 main，量到變化就重寫一次結論（250ms 去抖）
    const main = document.querySelector('main');
    /* ★ 2026-10-02 卡頓（DECISIONS #284）：輪動時鐘的聲納圓圈（.rotping）加一次拿一次都會進來，但它不改任何數字 ——
       整批都是它就不重寫結論（以前資金流向頁停著不動，每 250ms 就把七張卡的結論重算一次）。*/
    const pingOnly = (recs) => recs.every(r => { const ns = [...r.addedNodes, ...r.removedNodes];
      return ns.length > 0 && ns.every(n => n.classList && n.classList.contains('rotping')); });
    if (main && window.MutationObserver) new MutationObserver((recs) => { if (!pingOnly(recs)) schedule(); }).observe(main, { childList: true, subtree: true });
    window.addEventListener('hashchange', schedule);
    window.addEventListener('tw:theme', schedule);
    schedule();
  }
  window.T4 = { set, get, normalize, decorate, THEMES: THEMES.map(t => t.id) };
  window.Theme4 = window.T4;   // 原型時期的名字，留著給還在用的驗收腳本
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
