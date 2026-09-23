/* 台股資金輪動儀表板 v3 —— 前端只畫圖不運算（K 線指標除外，因為要能調參數）。
   路由：#overview / #flow / #industry / #industry/<chain> / #stock/<code> / #themes / #season
   台股慣例：紅漲綠跌。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const D = {};                       // 已載入的 JSON
  const charts = {};                  // ECharts 實例
  /* 圖表色票。深色是預設值；切到明亮主題時 refreshPalette() 會就地改寫這個物件
     （所有圖表都是在 render 當下才讀它，改完重畫就會換色）。 */
  const CH = { up: '#ff4d6d', down: '#2ee59d', cyan: '#3ee0ff', violet: '#8b7bff', amber: '#ffb454', lime: '#c3ff5b',
    ink: '#e8eeff', ink2: '#a9b6d6', ink3: '#6f7ea3', line: '#1e2a48', grid: 'rgba(255,255,255,.05)', panel: '#0a1020' };
  /* 分類色盤。深色主題那組是螢光色，畫在近白色的面板上（供應鏈環節的小標籤、
     族群卡片、折線）對比度只有 1.5 左右，等於看不見（Andy 2026-09-16
     「切換回白色 UI 後需要更改的顏色」）。淺色主題換成同色相壓深的一組。
     ★ 切換時是**就地改寫這個陣列**（length=0 再 push），不是換一個新陣列 ——
       外面已經拿走 PALETTE 參照的地方才會跟著變。
     ★★ 2026-09-21：族群換成 tide-tw.app 的板塊之後，卡片從 28 張變成 117 張
        （83 個手寫板塊 + 33 個法定產業別自動桶 + ETF），而色盤只有 14 色 ——
        `PALETTE[gidx % 14]` 於是產生 446 對「兩個不同板塊長得一模一樣」。
        熱力圖、桑基圖、輪動時鐘都是跨產業鏈顯示的，那裡一定看得到。
        **14 → 34 色。為什麼剛好是 34：**
        - 每條產業鏈的族群索引是「連續的一段」（半導體 0–23、AI 伺服器 24–42、
          一般電子 43–60 …、法定產業別自動桶 83–116）。最長的一段是自動桶的 **34** 張，
          所以色盤只要 ≥34，任何一條鏈內部就不會有兩張卡同色。
        - `supply_chain.yaml` 現在有 **34** 個環節（color_idx 0–33），34 色剛好讓
          剖析圖的每個環節各有一色，不再兩個環節共用一個顏色。
        - 再往上加沒有意義：新色與既有色的 CIEDE2000 下限訂在 **10**
          （對照組：Tableau 20 的下限 9.1、Kelly 22 色的 10.0 —— 這是公認做得到的極限附近），
          超過 34 色就一定得把某兩色壓到「看起來一樣」，那跟同色對使用者沒有差別。
        新增的 20 色**大多刻意壓低彩度**：既有 14 色配在「人工校訂的產業鏈」上，
        新色多半落在法定產業別自動桶，讓主線亮、雜項退後，畫面才有重點。
        另外三條硬性條件，改這一段之前先量過再改：
        ① 每個新色與 --rise／--fall 的 ΔE ≥18（鎖定區最差只有 5.7），
           不會被讀成「這個板塊在漲／在跌」；
        ② 深色對 --chartbg 的對比 ≥7.2、淺色對白底 ≥4.30
           —— 都不低於鎖定區自己最弱的那一個（深 5.75、淺 4.25）；
        ③ 索引相鄰的兩色 ΔE ≥34（卡片在格線裡是相鄰的，那裡最容易看錯）。
        量測腳本的作法：CIEDE2000 ＋ 依 L.init() 重現 gidx／color_idx 的配色順序。*/
  const PALETTE_DARK = [
    /* 0–13　★ 鎖定區：2026-09-12 起沿用的 14 色。loader.py 的 color_idx 靠它記住既有板塊的顏色，
       動一個值就等於把全站既有板塊的顏色洗牌一次（DECISIONS #48）。只准往後 append。*/
    '#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871',
    '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a',
    /* 14–33　2026-09-21 新增的 20 色（見下方說明）。*/
    '#56acc2', '#e4bcca', '#70ac99', '#e5beab', '#75b138', '#acb1d9', '#a6a366',
    '#c8a8d9', '#ccc98a', '#ded4ff', '#be9e16', '#cddbf5', '#e48c2f', '#ace3ec',
    '#d59078', '#bed04b', '#ffc9fc', '#c29967', '#da83c9', '#efd7b4'
  ];
  const PALETTE_LIGHT = [
    /* 0–13　★ 鎖定區：2026-09-12 起沿用的 14 色。loader.py 的 color_idx 靠它記住既有板塊的顏色，
       動一個值就等於把全站既有板塊的顏色洗牌一次（DECISIONS #48）。只准往後 append。*/
    '#0b7fa6', '#5f4ddb', '#b06a00', '#4a8a15', '#c2185b', '#0369a1', '#8a6d00',
    '#0f766e', '#c2410c', '#6d28d9', '#047857', '#b91c1c', '#1d4ed8', '#a16207',
    /* 14–33　2026-09-21 新增的 20 色（見下方說明）。*/
    '#285662', '#a75577', '#36564c', '#9c6140', '#305a00', '#515e94', '#53522e',
    '#77528e', '#737243', '#9d48f7', '#604e00', '#547abb', '#794200', '#5c8085',
    '#7a402c', '#667700', '#bf46c2', '#634c2e', '#842c77', '#927548'
  ];
  const PALETTE = PALETTE_DARK.slice();

  // ---------------------------------------------------------------- 工具
  const fmt = {
    n(v, d = 2) { if (v === null || v === undefined || Number.isNaN(v)) return '—'; return Number(v).toLocaleString('zh-TW', { minimumFractionDigits: d, maximumFractionDigits: d }); },
    i(v) { if (v === null || v === undefined) return '—'; return Math.round(v).toLocaleString('zh-TW'); },
    pct(v, d = 1) { if (v === null || v === undefined || Number.isNaN(v)) return '—'; const s = v > 0 ? '+' : ''; return s + Number(v).toFixed(d) + '%'; },
    yi(v) { if (v === null || v === undefined) return '—'; const a = Math.abs(v); if (a >= 1e8) return (v / 1e8).toFixed(a >= 1e10 ? 0 : 1) + ' 億'; if (a >= 1e4) return (v / 1e4).toFixed(0) + ' 萬'; return fmt.i(v); },
    lot(v) { if (v === null || v === undefined) return '—'; const a = Math.abs(v); if (a >= 1e4) return (v / 1e4).toFixed(1) + ' 萬張'; return fmt.i(v) + ' 張'; },
    cls(v) { return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'; },
    esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); },
  };
  const upDown = (v) => (v > 0 ? CH.up : v < 0 ? CH.down : CH.ink3);
  // #rrggbb + 透明度 → rgba()：色票只寫一份，要半透明時就地調
  const hexA = (hex, a) => {
    const h = String(hex || '').replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const v = parseInt(n || '888888', 16);
    return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
  };
  /* 兩個 #rrggbb 之間線性插值（t=0 回 a、t=1 回 b）。
     輪動時鐘的「越外圈顏色越深」用它：把族群色往面板底色調淡＝靠近圓心，
     整條混色只用色票、不寫死任何色碼，所以淺色主題切過去一樣成立。*/
  const mixHex = (a, b, t) => {
    const un = (h) => { const x = String(h || '').replace('#', '');
      const y = x.length === 3 ? x.split('').map(c => c + c).join('') : x;
      const v = parseInt(y || '888888', 16);
      return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
    const A = un(a), B = un(b), u = Math.max(0, Math.min(1, t));
    const c = A.map((x, i) => Math.round(x + (B[i] - x) * u));
    return '#' + c.map(x => x.toString(16).padStart(2, '0')).join('');
  };

  /* 紅漲綠跌的連續色。
     2026-09-18（Andy 圖13）：以前紅綠是寫死的深色主題霓虹值，而且透明度一路拉到 0.95，
     在淺色主題的白底上變成「很濃的紅塊配白字」，字幾乎讀不到。
     改成①顏色讀 CH.up/CH.down（切主題時 refreshPalette 會就地換掉）
     ②淺色主題的透明度上限壓到 0.62 —— 白底上是淡色塊，配深色字才讀得到（見 treeSkin）。*/
  const chgColor = (v, cap = 3) => {
    const lt = theme() === 'light';
    if (v === null || v === undefined) return lt ? hexA(CH.ink3, .18) : '#334155';
    const t = Math.max(-1, Math.min(1, v / cap));
    const lo = lt ? .15 : .25, hi = lt ? .62 : .95;
    return hexA(t >= 0 ? CH.up : CH.down, lo + (hi - lo) * Math.abs(t));
  };
  /* 熱力（0-100）→ 顏色。題材熱力圖用，同樣不准寫死色碼。*/
  const heatColor = (h) => {
    const lt = theme() === 'light';
    if (h >= 75) return hexA(CH.up, lt ? .62 : .85);
    if (h >= 60) return hexA(CH.up, lt ? .42 : .72);
    if (h >= 45) return hexA(CH.violet, lt ? .38 : .70);
    if (h >= 30) return hexA(CH.cyan, lt ? .34 : .55);
    return hexA(CH.ink3, lt ? .24 : .50);
  };
  /* 三張 treemap（產業板塊 #indTree、總覽熱力圖、題材熱力圖）共用的「殼」。
     ★ ECharts 的 treemap 是用 itemStyle.borderColor 當整片底色的（方塊間的縫就是它），
       以前三處都寫死 '#0b1224'，所以淺色主題切過去整張圖還是黑底 —— Andy 圖13 講的就是這個。
     標籤色也一起收在這裡：淺色主題底下方塊是淡色，白字會消失，要改用深色字。*/
  const treeSkin = () => {
    const lt = theme() === 'light';
    return {
      border: CH.panel,
      label: { color: lt ? CH.ink : '#fff', textShadowColor: lt ? 'rgba(255,255,255,.75)' : '#000', textShadowBlur: lt ? 3 : 4 },
      upper: { color: lt ? CH.ink2 : '#a9b6d6', backgroundColor: lt ? 'rgba(15,24,48,.06)' : 'rgba(0,0,0,.25)' },
    };
  };
  async function load(name, opt) {
    if (D[name] && !opt) return D[name];
    try { const r = await fetch(`data/${name}.json?v=${(D.meta && D.meta.generated_at) || ''}`, { cache: 'no-store' }); if (!r.ok) throw new Error(r.status); D[name] = await r.json(); }
    catch (e) { console.warn('載入失敗', name, e); D[name] = opt && opt.fallback !== undefined ? opt.fallback : null; }
    return D[name];
  }
  /* ★ 驗收用的 SVG renderer 開關（2026-09-20）。
     線上版一律 canvas（效能）—— 但 canvas 畫出來的字在 DOM 上完全不存在，
     所以 `_preview.py` 的文字重疊掃描對「圖裡的字」是物理性全盲的：
     它永遠報 0 筆，Andy 一換螢幕就看到壓字。SVG renderer 會產生真的 <text> 節點，
     量得出來。
     為什麼用網址參數（`?svg=1`）當主要開關，而不是只認一個全域變數：
       1. 它撐得過 `pg.goto()` 與重新整理，不用每開一頁就補一次 add_init_script；
       2. 人可以自己貼網址重現同一個畫面（`index.html?svg=1#overview`），
          回報裡的數字才驗得回來。
     `window.__TW_SVG_RENDER__` 保留成第二條路，給沒辦法改網址的呼叫端用。
     ⚠ SVG 與 canvas 的字寬量法略有差異，版面不保證 100% 相同 ——
     量到的重疊要人工看截圖確認，不要照單全收。 */
  function wantRenderer() {
    try {
      if (window.__TW_SVG_RENDER__) return 'svg';
      if (/[?&]svg=1(&|$)/.test(location.search)) return 'svg';
    } catch (e) { /* 取不到就當 canvas */ }
    return 'canvas';
  }
  function chart(id, option, opts) {
    const el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return null;
    if (typeof echarts === 'undefined') { el.innerHTML = '<div class="empty">圖表函式庫載入失敗</div>'; return null; }
    el.classList.remove('isempty');
    const want = wantRenderer();
    let c = echarts.getInstanceByDom(el);
    // renderer 是 init 當下決定的，中途要換只能整個 dispose 重建
    if (c && el._renderer && el._renderer !== want) { c.dispose(); c = null; }
    if (!c) { c = echarts.init(el, null, { renderer: want }); el._renderer = want; }
    c.setOption(Object.assign({ backgroundColor: 'transparent', textStyle: { fontFamily: 'Noto Sans TC, JetBrains Mono, sans-serif', color: CH.ink2 }, animationDuration: 500 }, option), opts && opts.notMerge !== false);
    // 容器在 display:none 或還沒排版時 init 出來會是 0×0，畫完就是一片空白而且不會自己好。
    // 盯著容器尺寸，一變就 resize，這樣切分頁、展開說明、視窗縮放都不會留下空白圖。
    if (!el._ro && typeof ResizeObserver !== 'undefined') {
      el._ro = new ResizeObserver(() => {
        const i = echarts.getInstanceByDom(el);
        if (!i || !(el.clientWidth > 0) || !(el.clientHeight > 0)) return;
        /* ★ 2026-09-21：尺寸沒有真的變就不要再 resize 一次。
           `resize()` 會**立刻**重排並且吃掉正在跑的補間動畫；
           資金去向展開族群時容器要長高，是「先自己 resize 到新高度、再 setOption 補間」，
           如果 ResizeObserver 隨後又補一次 resize，換位動畫就會在第一幀被切斷
           （實測：y 從 885 直接跳到 1007，中間一格都沒有）。
           ResizeObserver 本來就只在尺寸變動時才發，所以這道閘門平常是 no-op。*/
        const sig = el.clientWidth + 'x' + el.clientHeight;
        if (el._roSize === sig) return;
        el._roSize = sig;
        i.resize();
      });
      el._ro.observe(el);
    }
    charts[el.id || Math.random()] = c; return c;
  }
  const axisStyle = { axisLine: { lineStyle: { color: CH.line } }, axisLabel: { color: CH.ink3, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: CH.grid } } };
  const tip = { backgroundColor: '#141e36', borderColor: '#2a3860', textStyle: { color: '#e8eeff', fontSize: 12.5 }, confine: true };

  /* ---------------- 明亮／深色主題（Andy 2026-09-14）----------------
     版面本身全部吃 CSS 變數，換主題是一行 setAttribute 的事。
     麻煩的是圖表：ECharts 與 Lightweight Charts 的顏色是 JS 在畫的當下寫死進去的，
     不會跟著 CSS 變。所以切換時要做三件事：
       1. 把 CSS 變數的值讀回 CH / axisStyle / tip（下次畫圖就是新色）
       2. 把現有的 ECharts 實例全部 dispose（留著的話只會 resize，不會換色）
       3. 清掉 rendered 旗標再跑一次 route()，讓目前這一頁整個重畫
     不用 location.reload() 是因為那會把展開的列、勾選、K 線縮放全部弄掉。 */
  const THEME_KEY = 'tw.theme';
  const theme = () => (document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');
  function refreshPalette() {
    const s = getComputedStyle(document.documentElement);
    const v = (n, d) => (s.getPropertyValue(n) || '').trim() || d;
    CH.up = v('--rise', '#ff4d6d'); CH.down = v('--fall', '#2ee59d');
    CH.cyan = v('--cyan', '#3ee0ff'); CH.violet = v('--violet', '#8b7bff');
    CH.amber = v('--amber', '#ffb454'); CH.lime = v('--lime', '#c3ff5b');
    CH.ink = v('--ink', '#e8eeff'); CH.ink2 = v('--ink-2', '#a9b6d6'); CH.ink3 = v('--ink-3', '#6f7ea3');
    CH.line = v('--line', '#1e2a48'); CH.grid = v('--grid', 'rgba(255,255,255,.05)');
    CH.panel = v('--chartbg', '#0a1020');
    // 分類色盤就地換一組（不能換新陣列，L.scolor 之類的地方拿的是同一個參照）
    const src = theme() === 'light' ? PALETTE_LIGHT : PALETTE_DARK;
    PALETTE.length = 0; src.forEach(c => PALETTE.push(c));
    if (L.ready) L.recolor();                 // 族群／環節色要跟著新色盤重算
    axisStyle.axisLine.lineStyle.color = CH.line;
    axisStyle.axisLabel.color = CH.ink3;
    axisStyle.splitLine.lineStyle.color = CH.grid;
    tip.backgroundColor = v('--panel-2', '#141e36');
    tip.borderColor = v('--line-2', '#2a3860');
    tip.textStyle.color = CH.ink;
    if (window.KUtil && window.KUtil.refreshTheme) window.KUtil.refreshTheme();
  }
  function applyTheme(name, redraw) {
    document.documentElement.setAttribute('data-theme', name === 'light' ? 'light' : 'dark');
    try { localStorage.setItem(THEME_KEY, theme()); } catch (e) { /* 私密視窗，忽略 */ }
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme() === 'light' ? '#f2f5fb' : '#070b16');
    const btn = document.getElementById('themeBtn');
    if (btn) { btn.textContent = theme() === 'light' ? '🌙' : '☀'; btn.title = theme() === 'light' ? '切換成深色' : '切換成明亮'; }
    refreshPalette();
    if (!redraw) return;
    stopAllPlay(); _players.clear();    // 換主題會 dispose 全部圖表，播放中的計時器要先停
    Object.keys(charts).forEach(k => { try { charts[k].dispose(); } catch (e) { /* 忽略 */ } delete charts[k]; });
    Object.keys(rendered).forEach(k => delete rendered[k]);
    window.dispatchEvent(new CustomEvent('tw:theme', { detail: { theme: theme() } }));
    route();
  }
  // 沒東西可畫就把高度收掉，只留一行字 —— 不要留一個 420px 的黑方塊讓人以為壞了
  const empty = (id, msg) => {
    const el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return;
    const c = echarts.getInstanceByDom(el); if (c) c.dispose();
    el.classList.add('isempty');
    el.innerHTML = `<div class="empty">${msg || '尚無資料'}</div>`;
  };
  window.addEventListener('resize', () => { Object.values(charts).forEach(c => c && c.resize && c.resize()); });
  /* 瀏覽器縮放（Ctrl +/-）會改 devicePixelRatio，而 ECharts 是在 init 當下記住 DPR 的。
     只呼叫 resize() 的話畫布尺寸對了、內部座標還是舊 DPR，結果就是「圖縮到中間一小塊、周圍一片黑」
     （Andy 縮小視窗後熱力圖變一小塊就是這個）。DPR 一變就整個丟掉重建，沒有別的解法。 */
  let _dpr = window.devicePixelRatio || 1;
  (function watchDPR() {
    const onChange = () => {
      const d = window.devicePixelRatio || 1;
      if (d !== _dpr) {
        _dpr = d;
        Object.keys(charts).forEach(k => { try { charts[k].dispose(); } catch (e) { /* 已經沒了 */ } delete charts[k]; });
        Object.keys(rendered).forEach(k => delete rendered[k]);
        route();
      }
      try { matchMedia(`(resolution: ${d}dppx)`).addEventListener('change', onChange, { once: true }); }
      catch (e) { /* 舊瀏覽器沒有這個 media query，退回只靠 resize */ }
    };
    onChange();
  })();
  /* 滾輪放大：Andy 要「可以用滾輪放大，但縮小最多就是原始畫面」。
     三個關鍵：
     1. 不用 CSS transform 縮放 —— 那是把畫好的點陣圖拉大，字會糊。
        改成把內容的寬高乘上倍率，ECharts 用新尺寸重畫，放多大都清楚；SVG 本來就是向量。
     2. **外框高度在放大時鎖死**。不鎖的話卡片會被撐成 4 倍高，整頁版面都被推開
        （Andy：「放大部份會影響到整頁面」）。放大只在框內發生，框外的版面完全不動。
     3. 倍率下限是 1（原始畫面）；已經 1 倍還往下滾就不攔 wheel，讓頁面正常往下捲。 */
  function wheelZoom(box, opts) {
    if (!box || box._zoom) return box && box._zoom;
    const o = Object.assign({ max: 4, onZoom: null }, opts || {});
    // 捲動層自己包一層，徽章才不會跟著內容捲走
    let pane = box.querySelector(':scope > .zpane');
    if (!pane) {
      pane = document.createElement('div'); pane.className = 'zpane';
      while (box.firstChild) pane.appendChild(box.firstChild);
      box.appendChild(pane);
    }
    const inner = pane.firstElementChild; if (!inner) return null;
    let k = 1, baseH = 0, calm = 0;
    box.classList.add('zwrap');
    const badge = document.createElement('div');
    badge.className = 'zbadge'; badge.textContent = '滾輪放大';
    box.appendChild(badge);
    const setK = (nk) => {
      nk = Math.max(1, Math.min(o.max, nk));
      if (Math.abs(nk - k) < 0.001) return false;
      if (!baseH) baseH = inner.clientHeight || inner.offsetHeight || 320;
      k = nk;
      if (k <= 1.001) {
        inner.style.width = ''; inner.style.height = ''; pane.style.height = '';
        box.classList.remove('zoomed');
      } else {
        pane.style.height = baseH + 'px';           // ← 外框高度鎖住，卡片不會被撐高
        inner.style.width = (k * 100) + '%';
        inner.style.height = Math.round(baseH * k) + 'px';
        box.classList.add('zoomed');
      }
      badge.textContent = k <= 1.001 ? '滾輪放大　·　放大後可拖曳' : k.toFixed(1) + '×　拖曳移動　·　雙擊還原';
      if (o.onZoom) o.onZoom(k);
      return true;
    };
    pane.addEventListener('wheel', (e) => {
      const zin = e.deltaY < 0;
      /* 已經是原始大小又繼續往下滾 → 交還給頁面捲動。
         但「剛剛才還原成 1 倍」的那一瞬間不能馬上交還：使用者手還在滾，
         一放手整頁就被帶著往下衝（Andy：「還原成正常大小 他會導致整體頁面往下」）。
         所以還原後留 450ms 的緩衝，這段時間內的 wheel 一律吃掉，停手後才恢復正常捲動。 */
      if (!zin && k <= 1.001) {
        if (Date.now() < calm) { e.preventDefault(); e.stopPropagation(); calm = Date.now() + 450; }
        return;
      }
      e.preventDefault(); e.stopPropagation();
      const r = pane.getBoundingClientRect();
      const ox = e.clientX - r.left, oy = e.clientY - r.top;
      const px = (pane.scrollLeft + ox) / k, py = (pane.scrollTop + oy) / k;
      if (!setK(k * (zin ? 1.18 : 1 / 1.18))) return;
      if (k <= 1.001) { calm = Date.now() + 450; pane.scrollTo({ left: 0, top: 0 }); return; }
      pane.scrollLeft = px * k - ox; pane.scrollTop = py * k - oy;
    }, { passive: false });

    /* 放大後用游標直接抓著圖移動（Andy：「需要新增游標抓取可以移動功能」）。
       只在放大時生效，1 倍時不攔，才不會影響點方塊看成分股那些互動。 */
    let drag = null;
    pane.addEventListener('pointerdown', (e) => {
      if (k <= 1.001 || e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, l: pane.scrollLeft, t: pane.scrollTop, moved: false, id: e.pointerId };
      box.classList.add('grabbing');
    });
    pane.addEventListener('pointermove', (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;   // 小抖動還算點擊
      if (!drag.moved) { drag.moved = true; try { pane.setPointerCapture(drag.id); } catch (err) { /* 忽略 */ } }
      e.preventDefault();
      pane.scrollLeft = drag.l - dx; pane.scrollTop = drag.t - dy;
    });
    const endDrag = (e) => {
      if (!drag) return;
      // 真的拖過就把接下來那一次 click 吃掉，不然放開手會順便點到圖上的方塊
      if (drag.moved) { pane.addEventListener('click', (c) => { c.stopPropagation(); c.preventDefault(); }, { capture: true, once: true }); }
      try { pane.releasePointerCapture(drag.id); } catch (err) { /* 忽略 */ }
      drag = null; box.classList.remove('grabbing');
    };
    pane.addEventListener('pointerup', endDrag);
    pane.addEventListener('pointercancel', endDrag);
    pane.addEventListener('pointerleave', endDrag);

    box.addEventListener('dblclick', () => { setK(1); pane.scrollTo({ left: 0, top: 0 }); calm = Date.now() + 450; });
    box._zoom = { reset: () => setK(1), get scale() { return k; } };
    return box._zoom;
  }

  const goStock = (code) => { location.hash = '#stock/' + code; };
  window.goStock = goStock;

  // ---------------------------------------------------------------- 全站互通：任何股票／族群／產業鏈／題材名稱都可點
  // 資料載入後建索引；各頁用 L.stock()/L.group()/L.theme() 產生連結，永遠連到同一個地方。
  const L = {
    gname: {}, gid: {}, gchain: {}, gcolor: {}, gidx: {}, cname: {}, cgroup: {}, cmarket: {}, ctheme: {}, chains: {}, scolor: {}, sidx: {}, gsegs: {}, sgroups: {}, all: [], ready: false,
    // 環節色：讀的當下才從 PALETTE 取，這樣切主題就會跟著換
    segColor(id) { const i = this.sidx[id]; return i == null ? '#8ea0c4' : PALETTE[i % PALETTE.length]; },
    /* 族群色被十幾個地方直接讀 L.gcolor[gid]，一個個改成函式風險太大，
       所以改成「換主題時整包重算一次」。順序照舊：先照族群索引配色，
       有對應供應鏈環節的再用環節色蓋過去（剖析圖、環節標籤、族群卡片要同色）。*/
    recolor() {
      Object.keys(this.gidx).forEach(gid => { this.gcolor[gid] = PALETTE[this.gidx[gid] % PALETTE.length]; });
      Object.keys(this.sidx).forEach(sid => { this.scolor[sid] = this.segColor(sid); });
      Object.keys(this.gsegs).forEach(gid => { this.gcolor[gid] = this.segColor(this.gsegs[gid][0]) || this.gcolor[gid]; });
    },
    init(im, gt, cands, th, sc, all) {
      const gs = [];
      if (im) { (im.chains || []).forEach(c => { L.chains[c.id] = c.name; (c.groups || []).forEach(g => gs.push({ ...g, chain: c.id })); }); (im.industries || []).forEach(g => gs.push({ ...g, chain: 'industry' })); }
      (gt || []).forEach(g => gs.push({ id: g.group_id, name: g.group_name, chain: g.chain, members: [] }));
      gs.forEach((g, i) => { if (!L.gname[g.id]) { L.gname[g.id] = g.name; L.gid[g.name] = g.id; L.gchain[g.id] = g.chain; L.gidx[g.id] = i; L.gcolor[g.id] = PALETTE[i % PALETTE.length]; } (g.members || []).forEach(m => { if (!L.cname[m.code]) { L.cname[m.code] = m.name; L.cgroup[m.code] = g.id; } if (m.market) L.cmarket[m.code] = m.market; }); });
      (cands || []).forEach(c => { L.cname[c.code] = c.name; if (c.group_id) L.cgroup[c.code] = c.group_id; if (c.market) L.cmarket[c.code] = c.market; });
      // 全市場索引：每一檔上市櫃股票都有個股頁，搜尋與連結都以這份為準
      L.all = all || [];
      L.all.forEach(c => { if (c.name) L.cname[c.code] = c.name; if (c.group_id) L.cgroup[c.code] = c.group_id; if (c.market) L.cmarket[c.code] = c.market; });
      ((th && th.themes) || []).forEach(t => (t.members || []).forEach(m => { (L.ctheme[m.code] = L.ctheme[m.code] || []).push({ id: t.id, name: t.name }); if (!L.cname[m.code]) L.cname[m.code] = m.name; }));
      // 供應鏈環節的顏色是全站唯一：剖析圖零件、環節色標、關聯圖、族群卡片、族群連結的圓點都用它
      // 記索引而不是記色碼：色碼在載入當下就固定了，切主題不會跟著換（見 segColor）
      // ★ 索引一律吃 color_idx（YAML 的原始順序），不吃陣列位置。
      //   陣列是依 layer 排過序的，在前面的 layer 插一個新環節，後面每一個既有環節的
      //   位置都會 +1，全站環節顏色會一起被洗掉。color_idx 由 loader.py 在排序前記下。
      ((sc && sc.segments) || []).forEach((sg, i) => { const ci = (sg.color_idx == null ? i : sg.color_idx); L.sidx[sg.id] = ci; L.scolor[sg.id] = PALETTE[ci % PALETTE.length]; });
      ((sc && sc.companies) || []).forEach(c => (c.groups || []).forEach(gn => { const gid = L.gid[gn]; if (!gid || !c.segment) return; const a = (L.gsegs[gid] = L.gsegs[gid] || []); if (!a.includes(c.segment)) a.push(c.segment); const b = (L.sgroups[c.segment] = L.sgroups[c.segment] || []); if (!b.includes(gid)) b.push(gid); }));
      // 沒有台股直接對應的環節（HBM、雲端業者）也要點得到東西：接到最相近的族群
      /* ★ 2026-09-21：族群換成 tide-tw.app 的 110 個板塊，這張表的右邊全部要跟著換。
         舊的 8 個 id（memory / networking / ic_design / advanced_packaging / pcb_abf /
         server_thermal / optical_comm / silicon_ip / handset_chain）已經不存在 ——
         留著不會報錯，只會讓產業鏈剖析圖上那幾個環節**點下去列不出任何台股**，
         而且畫面看起來完全正常，沒有人會覺得它壞了。
         下面每一格的對映都用 `loader.load()` 驗過目標 id 真的存在。
         thermal 接兩格是因為 tide 把散熱拆成液冷與氣冷，環節沒拆，所以要聯集。
         ccl 目前借用 ic_substrate —— tide 的 110 個名字裡**沒有 CCL 銅箔基板**，
         這是已知缺口（見 docs/tide_110_boards.md），等 Andy 查到 tide 把台光電放哪一格再改。*/
      const FALLBACK = { hbm: ['hbm'], hyperscaler: ['ai_server_odm'], switch: ['switch_wireless', 'ai_server_odm'], ic_design: ['hpc_network_ic'], foundry: ['foundry'], adv_pkg: ['ai_adv_packaging'], osat_test: ['osat'], abf_pcb: ['ic_substrate'], ccl: ['ic_substrate'], thermal: ['liquid_cooling', 'air_cooling'], power: ['server_psu'], optical: ['optical_module'], assembly: ['ai_server_odm'], ip_eda: ['ip_asic'],
        // 一般電子鏈這兩格只有外商（康寧／Apple／SpaceX），沒有台股節點，
        // 不接 fallback 的話點下去列不出任何東西。
        display_material: ['panel'], brand_operator: ['smartphone'] };
      Object.entries(FALLBACK).forEach(([seg, gids]) => { if (!L.scolor[seg]) return; gids.filter(g => L.gname[g]).forEach(g => { const b = (L.sgroups[seg] = L.sgroups[seg] || []); if (!b.includes(g)) b.push(g); const a = (L.gsegs[g] = L.gsegs[g] || []); if (!a.includes(seg)) a.push(seg); }); });
      L.recolor();
      L.ready = true;
    },
    stock(code, name, o) { o = o || {}; const n = name || L.cname[code] || ''; return `<a class="lk lk-stock ${o.cls || ''}" href="#stock/${code}" title="看 ${fmt.esc(n)} 個股頁">${o.codeFirst ? `<span class="code">${code}</span>${fmt.esc(n)}` : `${fmt.esc(n)}<span class="code">${code}</span>`}</a>`; },
    group(gid, name, o) { o = o || {}; if (!gid) return fmt.esc(name || ''); const n = name || L.gname[gid] || gid; const col = L.gcolor[gid] || '#8ea0c4'; return `<a class="lk lk-group ${o.cls || ''}" href="#industry/group/${gid}" title="看「${fmt.esc(n)}」族群成分股" style="--c:${col}">${o.dot === false ? '' : '<i></i>'}${fmt.esc(n)}</a>`; },
    groupByName(name, o) { const gid = L.gid[name] || (L.gname['ind_' + name] ? 'ind_' + name : null); return gid ? L.group(gid, name, o) : fmt.esc(name || ''); },
    chain(cid, name, o) { o = o || {}; const n = name || L.chains[cid] || ({ industry: '法定產業別' })[cid] || cid; return `<a class="lk lk-chain ${o.cls || ''}" href="#industry/${cid}" title="看整條產業鏈">${fmt.esc(n)}</a>`; },
    theme(id, name, o) { o = o || {}; return `<a class="lk lk-theme ${o.cls || ''}" href="#themes/${id}" title="看題材">${fmt.esc(name)}</a>`; },
    themesOf(code) { return (L.ctheme[code] || []).map(t => L.theme(t.id, t.name)).join(''); },
    back() { return `<a class="lk lk-back" data-back="1" href="#" title="回上一頁">← 返回</a>`; },
  };
  window.Link = L;
  // 連結在表格列／卡片裡：點連結走連結，不要再觸發列的 onclick（Ctrl／中鍵仍可開新分頁）
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a.lk'); if (!a) return;
    e.stopPropagation();
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (a.dataset.back) { e.preventDefault(); if (history.length > 1) history.back(); else location.hash = '#industry'; return; }
    const h = a.getAttribute('href'); if (h && h.startsWith('#')) { e.preventDefault(); if (location.hash === h) route(); else location.hash = h; }
  }, true);


  /* ---------------------------------------------------------------- 排序 × 即時
     即時層（live.js 的 paint）每分鐘會把畫面上的收盤／漲跌**就地**改掉。
     表格如果正照著這兩欄排序，順序不會跟著換 —— 表頭還標著 ▲／▼，
     但那一欄已經不是排好的了。Andy 2026-09-15 的兩張截圖就是這個：
     同一張成分股表，標著「漲跌 ▲」，值卻是 -1.21 / -3.45 / -5.89 / -3.07 / -6.44。

     兩件事一起做才會對：
       1. liveMerge：排序**之前**先把即時值疊回列資料，排的就是使用者看到的數字
       2. onLive：即時層更新完之後再重排一次（只有正照著即時欄排序時才需要） */
  const LIVE_KEYS = ['close', 'chg_pct'];
  function liveMerge(rows) {
    const q = (window.Live && window.Live.quotes) || null;
    if (!q || !rows) return rows;
    rows.forEach(r => {
      const v = r && r.code ? q[r.code] : null;
      if (!v) return;
      if (v.price != null) r.close = v.price;
      if (v.chgPct != null) r.chg_pct = v.chgPct;
    });
    return rows;
  }
  /** 綁在某個元素上：即時層更新就呼叫 fn。
   *  兩個地雷都要避開：
   *   1. **同一個元素只能掛一次** —— 重排會再呼叫一次 onLive，每次都掛新的話
   *      監聽器會 1→2→4→8 指數成長，一次即時更新就重畫幾十遍，整頁卡住
   *      （2026-09-15 第一版就是這樣，把「更新」鈕卡成 disabled）。
   *   2. 但每次都要用**最新的 closure**（它抓著當下的排序狀態），所以放 WeakMap 覆蓋。
   *  元素離開畫面（換頁）時自己解除監聽。 */
  /* 拉 Bar（Andy 2026-09-18：RRG 的 5/10/20 天、族群佔比河流、族群×法人都要改成拖曳）。
     全站共用同一支，這樣四張圖的互動語彙一致 —— 而不是每張圖各長一個樣子。
     · 拖的當下就重畫（input），手感才連續；離手才寫 localStorage，免得拖一次寫幾十筆
     · 選過就記住，換頁回來還是同一個天數 */
  function rangeBar(box, o) {
    box = typeof box === 'string' ? document.getElementById(box) : box;
    if (!box) return null;
    const min = o.min, max = o.max, step = o.step || 1;
    let v = o.value != null ? o.value : max;
    /* ★ 2026-09-20 修掉一個一直沒人看到的 bug：以前寫
         `const s = +localStorage.getItem(o.key); if (s >= min && s <= max) v = s;`
       `localStorage.getItem` 沒存過會回 `null`，而 `+null === 0` ——
       所以只要這支拉Bar 的 min 是 0，第一次打開就會被當成「使用者上次選了 0」。
       資金去向的「看哪一天」min 就是 0，於是**第一次打開看到的是 60 天前那一天**，
       不是最新；而且因為畫面本身完全正常，沒有人會覺得它壞了。
       一定要先確認鍵真的存在、而且是個有限數字，才准覆蓋預設值。*/
    if (o.key) {
      try {
        const raw = localStorage.getItem(o.key);
        if (raw != null && raw !== '') { const s = +raw; if (isFinite(s) && s >= min && s <= max) v = s; }
      } catch (e) { /* 私密視窗 */ }
    }
    v = Math.max(min, Math.min(max, v));
    const label = (x) => (o.fmt ? o.fmt(x) : x + ' 天');
    box.classList.add('rbar');
    box.innerHTML = `${o.label ? `<span class="t">${fmt.esc(o.label)}</span>` : ''}`
      + `<input type="range" min="${min}" max="${max}" step="${step}" value="${v}">`
      + `<span class="val"></span>`;
    const inp = box.querySelector('input'), out = box.querySelector('.val');
    const paint = () => { out.textContent = label(+inp.value); };
    paint();
    inp.oninput = () => { paint(); if (o.onChange) o.onChange(+inp.value); };
    inp.onchange = () => { if (o.key) { try { localStorage.setItem(o.key, inp.value); } catch (e) { /* 忽略 */ } } };
    return { get value() { return +inp.value; }, set(x) { inp.value = x; paint(); } };
  }

  /* ---------------------------------------------------------------- 播放拉Bar
     Andy 2026-09-18（圖二/四/六/七/八）：「拉Bar 再多新增 + & - 符號可以調整」
     「具備播放功能，點擊後可以播放我拉Bar 選定的時間」。
     五張圖共用這一支，驗收也只寫一支 check_play()，不要各寫一套。

     做法：包住既有的 rangeBar（不動它），加三顆鈕；改值一律走
     input.value = x → dispatch input + change，這樣原本掛在 rangeBar 上的
     onChange 與 localStorage 寫入完全照舊，播放跟手動拉在行為上分不出來。

     ★ 會自己停的時機（不停的話會對已經 dispose 的 ECharts 實例 setOption 而拋錯）：
       分頁切到背景、換頁（route）、換主題（applyTheme 會 dispose 所有圖表）、
       使用者自己動手拉 Bar。*/
  /* ★ 2026-09-21（Andy：「輪動時鐘 暫停功能壞掉了，無法停止」）—— 量出來的根因在這裡。
     以前這是一個 `Set`，而且**只增不減**，於是有兩個坑：

     ① **同一個值被兩支拉Bar 控制，暫停只停得掉自己那一支。**
        「看哪一天」在卡片上是 `#rotBack`、在放大視窗裡是 `#rotZoomBack`，
        兩支改的是同一個 `rotFrame`。實測（計時器 id ＋ 間隔）：
          卡片按 ▶ → interval 36@420；開放大 → 36@420 還在；
          在放大裡按 ▶ → 36@420 + 48@420（**兩支同時在跑**）；
          在放大裡按 ⏸ → 只剩 36@420；ESC 關掉放大 → 36@420 **繼續跑**，
          「幾天前」3 秒內從 3 一路跑到 27。
        使用者的感受就是「我明明按了暫停，它還在自己跑」。
     ② 容器被重畫（`rangeBar` 每次都 `box.innerHTML = …`）之後，舊的 api 還留在集合裡，
        指著一個已經被拔掉的 `<input>`。今天還沒有人這樣用，但放大視窗每開一次就留一筆。

     改法：**以容器元素當 key**（同一個容器只會有一支活著），
     再加一個 `group`＝「這支在控制哪個值」。同一個 group 一次只准一支在播，
     而按 ⏸ 停的是**整個 group**，因為使用者按的是「停下這個時鐘」，
     不是「停下我手上這顆按鈕」。*/
  const _players = new Map();          // 容器元素 → api
  function stopAllPlay() { _players.forEach(p => { try { p.stop(); } catch (e) { /* 忽略 */ } }); }
  /** 停掉「控制同一個值」的其他播放器（except 傳自己，避免把剛要啟動的那支也停掉）。*/
  function stopPlayGroup(group, except) {
    if (!group) return;
    _players.forEach(p => {
      if (p.group === group && p !== except) { try { p.stop(); } catch (e) { /* 忽略 */ } }
    });
  }
  function playBar(box, o) {
    box = typeof box === 'string' ? document.getElementById(box) : box;
    if (!box) return null;
    // 這個容器上一支播放器先收乾淨（下面 rangeBar 會把它的 <input> 換掉，留著就是幽靈計時器）
    const prev = _players.get(box);
    if (prev) { try { prev.stop(); } catch (e) { /* 忽略 */ } _players.delete(box); }
    // 順手清掉已經離開 DOM 的（放大視窗每開一次就會換一個新容器）
    _players.forEach((p, el) => {
      if (!el.isConnected) { try { p.stop(); } catch (e) { /* 忽略 */ } _players.delete(el); }
    });
    const rb = rangeBar(box, o);
    if (!rb) return null;
    const inp = box.querySelector('input');
    const mk = (cls, txt, title) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'pb ' + cls; b.textContent = txt; b.title = title;
      b.setAttribute('aria-label', title);
      return b;
    };
    const bMinus = mk('step', '−', '往前一格');
    const bPlus = mk('step', '＋', '往後一格');
    const bPlay = mk('play', '▶', '播放');
    inp.parentNode.insertBefore(bMinus, inp);
    inp.parentNode.insertBefore(bPlus, inp.nextSibling);
    box.appendChild(bPlay);

    const lim = () => ({ min: +inp.min, max: +inp.max, st: +inp.step || 1 });
    // 改值走真的事件，才會觸發 rangeBar 既有的 onChange 與 localStorage
    const setV = (x) => {
      const { min, max } = lim();
      x = Math.max(min, Math.min(max, x));
      if (x === +inp.value) return false;
      inp.value = x;
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };
    let timer = null;
    let api = null;                    // start() 會先用到（stopPlayGroup 要排除自己），所以提前宣告
    const paintBtn = () => {
      const { min, max } = lim();
      bMinus.disabled = +inp.value <= min;
      bPlus.disabled = +inp.value >= max;
      bPlay.textContent = timer ? '⏸' : '▶';
      bPlay.title = timer ? '暫停' : '播放';
      bPlay.setAttribute('aria-label', bPlay.title);
      box.classList.toggle('playing', !!timer);
    };
    const stop = () => { if (timer) { clearInterval(timer); timer = null; } paintBtn(); };
    /* dir = -1：播放時值**由大往小**跑。
       2026-09-20（Andy A4 第 5 條「輪動時鐘新增播放功能」）加的：
       輪動時鐘那支拉Bar 的值是「幾天前」，所以「時間往前走」＝值往下掉。
       沒有這個方向旗標的話，按播放會從「前一天」跑到「前三十天」——
       等於時光倒流，和他要看的「資金怎麼一路輪過來」剛好相反。*/
    const dirOf = () => (o.dir === -1 ? -1 : 1);
    const tick = () => {
      const { min, max, st } = lim();
      const d = dirOf();
      let nx = +inp.value + st * d;
      if (d > 0 ? nx > max : nx < min) { if (o.loop === false) { stop(); return; } nx = d > 0 ? min : max; }
      setV(nx); paintBtn();
    };
    const start = () => {
      if (timer) return;
      stopPlayGroup(o.group, api);      // 同一個值一次只准一支在播（見 _players 那一段的量測）
      const { min, max } = lim();
      const d = dirOf();
      if (d > 0 ? +inp.value >= max : +inp.value <= min) setV(d > 0 ? min : max);   // 已經在尾端就從頭播
      timer = setInterval(tick, o.frame || 600);
      paintBtn();
    };
    /* 按 ⏸ 停的是**整個 group**：使用者按的是「停下這個時鐘」，
       而同一個時鐘可能同時被卡片與放大視窗兩支拉Bar 推著走。*/
    bPlay.onclick = () => { if (timer) { stop(); stopPlayGroup(o.group, null); } else start(); };
    bMinus.onclick = () => { stop(); setV(+inp.value - lim().st); paintBtn(); };
    bPlus.onclick = () => { stop(); setV(+inp.value + lim().st); paintBtn(); };
    inp.addEventListener('pointerdown', stop);  // 自己動手拉就停播放
    inp.addEventListener('input', paintBtn);
    paintBtn();
    api = { get value() { return +inp.value; }, set(x) { setV(x); paintBtn(); },
      stop, start, playing: () => !!timer, el: box, group: o.group || '' };
    _players.set(box, api);
    return api;
  }

  /* ---------------------------------------------------------------- 區間拉Bar（雙把手）
     ★ D1（Andy 2026-09-23：「資金輪動已經有一個時間拉 Bar 幫我合併」）。

     ── 合併前是哪兩條、為什麼該合併 ──
       · `#rotBack`　「看哪一天　− ▬▬ ＋　最新　▶　即時」＝時鐘大圈停在哪一天（＝排行的截止日）
       · `#rankDays`「最近 ▬▬ 20 天　☑ 顯示軌跡」＝排行往回看幾個交易日
       兩條講的是**同一段時間的兩個端點**：一個是結尾、一個是長度。
       分成兩條的代價是使用者得自己在腦袋裡把「截止 5 天前」加「最近 20 天」湊成
       「25 天前～5 天前」—— 那正是「逼使用者自己做兩步推論」。

     ── 合併後的做法 ──
       一條**雙把手的區間桿**，軸是「幾個交易日前」（左邊舊、右邊＝最新）：
         · 右把手（青色）＝**看哪一天**：時鐘大圈停的那一天，也是排行的截止日
         · 左把手（灰色）＝**這一段的起點**：兩個把手中間的距離就是「排行往回看幾天」
       所以一條桿同時把「哪一天」與「回溯幾天」寫在同一個刻度上，讀出來就是一段區間。
       `−` `＋` `▶` 三顆鈕改成**整段一起平移**（長度不變、窗口往前滑），
       那是「看時間怎麼走」最自然的動作，也是原本播放在做的事。

     ── 這四個控制項一個都沒掉（Andy 指定）──
       「最新」＝右把手拉到底時 `.val` 就寫「最新」；`▶ 播放`＝這支自己的播放鈕；
       `即時` 由 `rlvMountBtn()` 照舊掛在同一個容器（`#rotBack`）上；
       `☑ 顯示軌跡` 仍然在旁邊的 `#rotTools`（它是開關不是時間，硬併進來反而讀不懂）。

     ── 刻意付出的代價（寫出來，不要讓下一個人以為是 bug）──
       合併前「截止 30 天前 ＋ 最近 30 天」可以看到 60 天前；現在兩個把手在同一根 0～30 的軸上，
       所以最遠只到 30 個交易日前。取捨的理由：時鐘的軌跡（`rrg.points[].trail`）本來就只有 31 天，
       超過 30 天的那一段**只有排行看得到、時鐘看不到**，兩張並排的圖各講各的時間才是更糟的事。

     ── `ROT_BOARD_WIN` 與這條桿無關（Andy 特別交代）──
       象限卡的「和 5 個交易日前比」是固定窗長，不吃這裡的任何一個值。

     onChange(to, days)：to＝截止日是「幾天前」（0＝最新）、days＝這一段有幾個交易日。*/
  function spanBar(box, o) {
    box = typeof box === 'string' ? document.getElementById(box) : box;
    if (!box) return null;
    // 這個容器上一支播放器先收乾淨（下面會換掉整個 innerHTML，留著就是幽靈計時器）
    const prev = _players.get(box);
    if (prev) { try { prev.stop(); } catch (e) { /* 忽略 */ } _players.delete(box); }
    _players.forEach((pp, elx) => {
      if (!elx.isConnected) { try { pp.stop(); } catch (e) { /* 忽略 */ } _players.delete(elx); }
    });
    const PMAX = o.max != null ? o.max : 30;          // 軸長＝最多看到幾個交易日前
    const readLS = (key, lo, hi, dft) => {
      if (!key) return dft;
      try {
        const raw = localStorage.getItem(key);
        if (raw == null || raw === '') return dft;
        const v = +raw;
        return (isFinite(v) && v >= lo && v <= hi) ? v : dft;
      } catch (e) { return dft; }
    };
    // 內部一律用「位置」p：p = PMAX − 幾天前，所以右邊＝最新，和時間軸的直覺一致
    let days = readLS(o.keyDays, 1, PMAX, o.days != null ? o.days : 20);
    let pHi = PMAX - readLS(o.keyTo, 0, PMAX - 1, o.to != null ? o.to : 0);
    const clamp = () => {
      days = Math.max(1, Math.min(PMAX, Math.round(days)));
      pHi = Math.max(days, Math.min(PMAX, Math.round(pHi)));   // 起點不可以掉到軸的左邊外面
    };
    clamp();
    box.classList.add('rbar');
    box.innerHTML = `${o.label ? `<span class="t">${fmt.esc(o.label)}</span>` : ''}`
      // ★ 「看哪一天」那支**寫在前面**：外面有程式碼用 `box.querySelector('input')` 抓這支拉Bar
      //   的主值（例如驗收腳本），抓到的必須是主角，不是區間起點。視覺上下的疊法由 CSS 決定。
      + '<div class="dual"><span class="track"></span><span class="sel"></span>'
      + `<input class="hi" type="range" min="1" max="${PMAX}" step="1" value="${pHi}"`
      + ' aria-label="看哪一天（這一段的截止日）">'
      + `<input class="lo" type="range" min="0" max="${PMAX - 1}" step="1" value="${pHi - days}"`
      + ' aria-label="這一段的起點（往回幾個交易日）"></div>'
      + '<span class="val"></span>';
    const hi = box.querySelector('input.hi'), lo = box.querySelector('input.lo');
    const sel = box.querySelector('.sel'), out = box.querySelector('.val');
    const toDays = () => PMAX - pHi;                  // 截止日是「幾天前」
    const paint = () => {
      hi.value = pHi; lo.value = pHi - days;
      const a = (pHi - days) / PMAX * 100, b = pHi / PMAX * 100;
      sel.style.left = a + '%'; sel.style.width = Math.max(0, b - a) + '%';
      out.textContent = `最近 ${days} 天 · 截止 ${toDays() === 0 ? '最新' : toDays() + ' 天前'}`;
      bMinus.disabled = pHi <= days; bPlus.disabled = pHi >= PMAX;
      bPlay.textContent = timer ? '⏸' : '▶';
      bPlay.title = timer ? '暫停' : '播放（整段往「最新」滑）';
      bPlay.setAttribute('aria-label', bPlay.title);
      box.classList.toggle('playing', !!timer);
    };
    const save = () => {
      try {
        if (o.keyTo) localStorage.setItem(o.keyTo, String(toDays()));
        if (o.keyDays) localStorage.setItem(o.keyDays, String(days));
      } catch (e) { /* 私密視窗 */ }
    };
    const fire = () => { if (o.onChange) o.onChange(toDays(), days); };
    const mk = (cls, txt, title) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'pb ' + cls; b.textContent = txt; b.title = title;
      b.setAttribute('aria-label', title);
      return b;
    };
    const bMinus = mk('step', '−', '整段往回一個交易日');
    const bPlus = mk('step', '＋', '整段往後一個交易日');
    const bPlay = mk('play', '▶', '播放（整段往「最新」滑）');
    const dual = box.querySelector('.dual');
    box.insertBefore(bMinus, dual);
    box.insertBefore(bPlus, dual.nextSibling);
    box.appendChild(bPlay);
    let timer = null;
    let api = null;
    const stop = () => { if (timer) { clearInterval(timer); timer = null; } paint(); };
    /* ★ 順序不能反：**先把使用者拖到的值讀出來，再 `stop()`**。
       `stop()` 會呼叫 `paint()`，而 `paint()` 會把 `<input>` 的值寫回目前的 `pHi`／`days` ——
       先 stop 的話這一行就把使用者剛拖出來的值蓋掉了，讀回來永遠是舊值，
       於是「拖了完全沒反應」（實測：拖到 24，讀回來還是 30）。*/
    // 右把手：拖它＝換截止日，**長度不變**（除非撞到軸的左端，那時只好把長度縮短）
    hi.oninput = () => { const v = +hi.value; stop(); pHi = v; if (pHi < days) days = Math.max(1, pHi); paint(); fire(); };
    // 左把手：拖它＝換這一段有多長（截止日不動）
    lo.oninput = () => { const v = +lo.value; stop(); days = Math.max(1, pHi - v); paint(); fire(); };
    hi.onchange = lo.onchange = save;
    const slide = (d) => {
      const nx = Math.max(days, Math.min(PMAX, pHi + d));
      if (nx === pHi) return false;
      pHi = nx; paint(); fire(); save(); return true;
    };
    bMinus.onclick = () => { stop(); slide(-1); };
    bPlus.onclick = () => { stop(); slide(1); };
    const start = () => {
      if (timer) return;
      stopPlayGroup(o.group, api);                    // 同一個值一次只准一支在播
      if (pHi >= PMAX) { pHi = days; paint(); fire(); }   // 已經在最新了就從最舊重播
      timer = setInterval(() => { if (!slide(1)) { pHi = days; paint(); fire(); } }, o.frame || 600);
      paint();
    };
    bPlay.onclick = () => { if (timer) { stop(); stopPlayGroup(o.group, null); } else start(); };
    paint();
    api = {
      get value() { return toDays(); },               // 對外沿用舊語彙：值＝「幾天前」
      get days() { return days; },
      /* set(x)＝「把截止日設成 x 天前」。放大視窗那支拉Bar 的上限還是 30，
         而這裡的右把手最遠只到 `PMAX − 1` 天前（左把手至少要佔一格），
         所以撞到軸的左端時**優先保住他要的那一天**，把區間長度縮短，不要默默改掉截止日。*/
      set(x) {
        let np = PMAX - Math.max(0, Math.min(PMAX, +x || 0));
        if (np < 1) np = 1;
        if (np < days) days = Math.max(1, np);
        pHi = np; paint();
      },
      setDays(k) { days = Math.max(1, Math.min(PMAX, +k || 1)); if (pHi < days) pHi = days; paint(); },
      stop, start, playing: () => !!timer, el: box, group: o.group || '',
    };
    _players.set(box, api);
    return api;
  }

  const _liveFns = new WeakMap();
  function onLive(el, fn) {
    if (!el) return;
    _liveFns.set(el, fn);
    if (el.dataset.liveBound) return;
    el.dataset.liveBound = '1';
    const h = () => {
      if (!el.isConnected) { window.removeEventListener('tw:quotes', h); return; }
      const f = _liveFns.get(el);
      if (f) { try { f(); } catch (e) { /* 一張表壞掉不要拖垮整頁 */ } }
    };
    window.addEventListener('tw:quotes', h);
  }

  // ---------------------------------------------------------------- 路由
  /* ★ 2026-09-23：'heatmap'＝產業熱力圖，從 #industry 拆出來的頂層分頁（DECISIONS #252）。
     它跟 'industry' 共用 industry.js 的資料載入，所以路由也交給 window.Industry 處理。*/
  const VIEWS = ['overview', 'flow', 'market', 'industry', 'heatmap', 'themes', 'season', 'tasks'];
  const rendered = {};
  let _lastPageKey = null;          // 上一次停在哪一頁（見 route() 裡的捲動判斷）
  async function route() {
    stopAllPlay();                       // 換頁前先停，否則計時器會對已 dispose 的圖表 setOption
    _players.clear();
    /* ★ 這裡**不要**呼叫 stopSankeyFlow()。
       換頁時 `#sankey` 只是被 CSS 藏起來、還在 DOM 裡，而 route() 對已經畫過的
       view 不會再跑一次 renderFlow —— 在這裡收掉的話，離開資金流向頁再回來，
       小圓點就永遠不會回來了（2026-09-20 實測：`canvas.dotfx` 整個不見）。
       改成讓動畫迴圈自己判斷「我現在看得見嗎」，看不見就只空轉不畫（見 startSankeyFlow）。*/
    // 產業鏈的外商小面板不屬於任何 view，換頁一定要自己清（Andy 2026-09-18 圖12）
    { const cb = document.getElementById('coBox'); if (cb) cb.remove(); }
    /* 「成分股放寬、暫時蓋住事件面板」也是同一種東西：它掛在 <body> 上、不屬於任何 view。
       換頁不清的話，使用者在產業鏈頁按了放寬，跑去總覽會發現事件面板莫名其妙不見了。
       remember=false —— 那是暫時狀態，不該改掉他自己設定的偏好（DECISIONS #248）。*/
    if (document.body.classList.contains('memwide')) {
      document.body.classList.remove('memwide');
      let want = true; try { want = localStorage.getItem('tw.side') !== '0'; } catch (e) { /* 忽略 */ }
      if (typeof window.twSetSide === 'function') window.twSetSide(want, false);
    }
    const h = location.hash.replace('#', '') || 'overview';
    /* ★ 2026-09-19：一定要逐段 decodeURIComponent。
       法定產業別的族群 id 是中文（ind_半導體業），瀏覽器把 hash 存成百分比編碼，
       不解碼的話 industry.js 的 `g.id === state.group` 永遠比不中 ——
       35 個法定產業別裡有 34 個的族群頁是「0 檔 · 沒有符合的股票」，
       只有純 ASCII 的 ind_ETF 躲過。候選名單、市場明細、個股頁的族群連結全部通到這裡。
       decodeURIComponent 對沒編碼過的字串是 identity，所以其餘路由不受影響；
       使用者手打出壞的 % 序列會丟例外，包起來退回原字串。 */
    const _dec = (x) => { try { return decodeURIComponent(x); } catch (e) { return x; } };
    const [head, ...rest] = h.split('/').map(_dec);
    let view = VIEWS.includes(head) ? head : head === 'stock' ? 'industry' : 'overview';
    $$('.tab').forEach(t => t.classList.toggle('on', t.dataset.view === view));
    /* ★ 2026-09-23：頂層分頁多了「熱力圖」之後，1440 以下這一排就放不下了（本來就會左右捲）。
       放不下時**現在這一頁一定要捲進視野** —— 不然使用者會看到一排分頁，卻找不到自己在哪一頁。
       捲的是分頁列自己（設 scrollLeft），不是 scrollIntoView：後者會連整頁一起捲。*/
    { const strip = document.getElementById('tabs'), on = strip && strip.querySelector('.tab.on');
      if (strip && on && strip.scrollWidth > strip.clientWidth + 2) {
        strip.scrollLeft = Math.max(0, on.offsetLeft - (strip.clientWidth - on.offsetWidth) / 2);
      } }
    $$('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + view));
    /* K 線「寬版」只在個股頁生效：離開個股頁要把右側事件欄還回來，
       不然使用者會覺得事件欄莫名其妙消失了（設定本身留著，回個股頁自動復原）。 */
    // 預設就是寬版（Andy：「K 線圖 default 就大一點」）；只有自己按過關掉才會是窄的
    let wide = true;
    try { const v = localStorage.getItem('tw.kwide'); if (v !== null) wide = v === '1'; } catch (e) { /* 忽略 */ }
    document.body.classList.toggle('kwide', head === 'stock' && wide);
    /* ★ 2026-09-23（Andy：「每次切換族群不會一直跳到上面，還要再滑下來看」）。
       根因就是這一行：路由**每換一次**就捲頁首，而「切圖別／換族群／換關聯圖中心」
       都會改 hash → 觸發路由 → 整頁彈回最上面，使用者得再滑下來一次。
       改成有條件：**同一頁內的切換保留捲動位置，換頁或換一條鏈才捲頁首**。
       「同一頁」的定義＝hash 的頁面部分（第一段 ＋ 鏈 id／個股代號）一樣。
       ⚠ 不是把捲動關掉：`#industry/semiconductor` → `#industry/ai_server` 仍然會捲，
         `#flow` → `#overview` 也會 —— 驗收有一條就是反過來證明這件事。*/
    const pageKey = (hd, rs) => (hd === 'industry' || hd === 'stock') ? hd + '/' + (rs[0] || '') : hd;
    const key = pageKey(head, rest);
    if (key !== _lastPageKey) window.scrollTo({ top: 0 });
    _lastPageKey = key;
    if (view === 'heatmap') { await window.Industry.routeHeat(); return; }
    if (view === 'industry') { await window.Industry.route(head, rest); return; }
    if (view === 'themes' && rendered.themes && D.themes && D.themes.themes) { renderThemeDetail(D.themes, rest[0] || D.themes.themes[0].id); return; }
    if (view === 'market' && rendered.market) { drawMarket(rest[0] || 'updown'); return; }
    if (!rendered[view]) { rendered[view] = true; await ({ overview: renderOverview, flow: renderFlow, market: renderMarket, themes: renderThemes, season: renderSeason, tasks: renderTasks })[view](); }
    setTimeout(() => Object.values(charts).forEach(c => c && c.resize && c.resize()), 30);
  }
  window.addEventListener('hashchange', route);
  $$('.tab').forEach(t => t.addEventListener('click', () => { location.hash = '#' + t.dataset.view; }));


  /* 總覽上方那排數字只是摘要，點下去到「市場明細」分頁看完整名單。
     Andy：「上面是簡說，點擊後會出現所有資訊」——
     所以不在總覽塞一個小面板，而是給它一個真的分頁，資訊可以鋪得開。 */
  /* 2026-09-18（Andy 圖16）：「市場明細內資金集中這頁拿掉」——
     資金集中度在「資金流向」頁已經有完整的一張（含均線與逐日鑽取），這裡重複了。*/
  const MKT = [
    ['updown', '漲跌家數'], ['ma', '站上均線'], ['cand', '今日候選'],
  ];
  function wireKpiDrill() {
    /* drill 以 # 開頭就是完整 hash（例如集中度改導到資金流向頁），否則是市場明細的子頁。
       ★ 2026-09-19：完整 hash 的情況要再捲到那張圖。「前五族群佔比」導到 #flow，
       但集中度圖在頁面 2700px 處，使用者點完只會看到資金流向頁的頂端，
       得自己往下捲很久才找得到 —— 看起來像「點了沒反應」。
       #anchor 的形式寫成 `#flow>conc`：> 後面是要捲過去的元素 id。 */
    $$('#hero .kpi.clickable').forEach(k => k.onclick = () => {
      const d = k.dataset.drill || '';
      if (!d.startsWith('#')) { location.hash = '#market/' + d; return; }
      const [hash, anchor] = d.split('>');
      location.hash = hash;
      if (!anchor) return;
      /* 換頁是非同步的（route() 要等資料與圖表），輪詢到元素出現再捲。
         ★ 2026-09-20：原本捲一次就結束，而那一刻圖表往往還在長高
         （每張圖都有 min-height 佔位，畫完才變成真高度）——
         於是使用者被留在錯的位置，看起來就像「點了沒反應」。
         在慢一點的機器上一定會遇到，這跟 Andy 回報的「換一台電腦版面就跑掉」是同一類。
         改成：捲過去之後繼續盯著目標的位置，位置還在變就再捲一次，
         直到連續兩次量到同一個位置（或超過上限）為止。
         使用者只要自己動了滾輪／觸控／方向鍵就立刻放手，不跟人搶。 */
      let tries = 0, settles = 0, rescrolls = 0, lastTop = null, userMoved = false;
      const release = () => { userMoved = true; };
      ['wheel', 'touchstart', 'keydown'].forEach(ev =>
        window.addEventListener(ev, release, { passive: true, once: true }));
      const done = () => ['wheel', 'touchstart', 'keydown'].forEach(ev =>
        window.removeEventListener(ev, release));
      const go = (el) => (el.closest('.card') || el).scrollIntoView({ behavior: 'smooth', block: 'start' });
      const settle = () => {
        if (userMoved) { done(); return; }
        const el = document.getElementById(anchor);
        if (!el) { done(); return; }
        const top = Math.round(el.getBoundingClientRect().top);
        // 已經在視窗裡而且位置穩住了 → 收工
        if (lastTop !== null && Math.abs(top - lastTop) <= 2) {
          if (top >= 0 && top < window.innerHeight) { done(); return; }
          settles++;
        } else {
          settles = 0;
        }
        lastTop = top;
        // 位置變了（版面還在長）或還沒捲進視窗 → 再捲一次，但有上限，不要無限追
        if ((settles > 0 || top < 0 || top >= window.innerHeight) && rescrolls < 8) {
          rescrolls++; go(el);
        }
        if (rescrolls < 8) setTimeout(settle, 220);
        else done();
      };
      const tick = () => {
        const el = document.getElementById(anchor);
        if (el && el.offsetParent !== null) { go(el); setTimeout(settle, 220); return; }
        if (++tries < 40) setTimeout(tick, 100); else done();
      };
      setTimeout(tick, 100);
    });
  }

  function stockTable(rows, cols) {
    if (!rows || !rows.length) return '<div class="empty">沒有符合的股票</div>';
    return `<div class="tw cap-lg"><table><thead><tr><th class="l">股票</th><th class="l">族群</th>`
      + cols.map(c => `<th>${c[0]}</th>`).join('') + `</tr></thead><tbody>`
      + rows.map(r => `<tr data-code="${r.code}"><td class="l">${L.stock(r.code, r.name)}</td>`
        + `<td class="l">${r.group_id ? L.group(r.group_id, r.group_name) : '<span class="muted">—</span>'}</td>`
        + cols.map(c => `<td class="num">${c[1](r)}</td>`).join('') + '</tr>').join('')
      + '</tbody></table></div>';
  }

  let mktKind = 'updown', mktTab = 0;
  async function renderMarket() {
    wireHowto($('#v-market'));
    // stocks.json：圖15 的漲跌分佈長條圖要用（每一檔都有 market / group / chg_pct）
    await Promise.all([load('market_heat'), load('groups_today'), load('candidates'),
                       load('groups_detail'), load('stocks', { fallback: [] })]);
    $('#mktSeg2').innerHTML = MKT.map(([k, l]) => `<button data-k="${k}">${l}</button>`).join('');
    $$('#mktSeg2 button').forEach(b => b.onclick = () => { location.hash = '#market/' + b.dataset.k; });
    drawMarket((location.hash.split('/')[1]) || 'updown');
  }

  /* 圖15（Andy 2026-09-18）：「市場明細需要新增長條圖，去表現漲幅到跌幅 -10~+10%
     常態分佈每2%為一個區間，並且可以篩選上市上櫃 族群」。

     資料直接用 stocks.json（每一檔都有 market / group / chg_pct），不必改後端。
     ETF 預設排除（已拍板）—— ETF 的漲跌分佈跟個股不同，混在一起會把中央那根撐高。
     兩端各留一個「≤ -10%」「≥ +10%」的溢出格，不要把離群值丟掉。*/
  const DIST = { market: '', groups: null, etf: false };
  /* 圖15 的篩選：市場（全部／上市／上櫃）、含不含 ETF、族群複選。
     族群用「晶片」而不是下拉 —— 這頁本來就用晶片，語彙一致。*/
  function wireDistFilter() {
    const box = $('#distFilter'); if (!box) return;
    const all = D.stocks || [];
    const markets = [...new Set(all.map(r => r.market).filter(Boolean))];
    box.innerHTML = `<div class="seg tiny" id="distMkt">
        <button data-m="" class="${DIST.market ? '' : 'on'}">全部</button>
        ${markets.map(m => `<button data-m="${m}" class="${DIST.market === m ? 'on' : ''}">${m === 'TWSE' ? '上市' : m === 'TPEx' ? '上櫃' : m}</button>`).join('')}
      </div>
      <label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;font-size:12.5px;color:var(--ink-2)">
        <input type="checkbox" id="distEtf" ${DIST.etf ? 'checked' : ''}>含 ETF</label>
      <button class="btn small" id="distGroupBtn">族群篩選${DIST.groups ? `（${DIST.groups.size}）` : ''}</button>`;
    $$('#distMkt button', box).forEach(b => b.onclick = () => {
      DIST.market = b.dataset.m; wireDistFilter(); drawChgDist();
    });
    const etf = $('#distEtf', box);
    if (etf) etf.onchange = () => { DIST.etf = etf.checked; drawChgDist(); };
    const gb = $('#distGroupBtn', box);
    if (gb) gb.onclick = () => {
      const names = [...new Set(all.map(r => r.group || '（未分類）'))].sort();
      const wrap = $('#distGroups') || (() => {
        const d = document.createElement('div');
        d.id = 'distGroups'; d.className = 'chainchips';
        d.style.cssText = 'margin-top:8px;max-height:130px;overflow:auto';
        box.parentNode.parentNode.insertBefore(d, box.parentNode.nextSibling);
        return d;
      })();
      if (wrap.dataset.open === '1') { wrap.dataset.open = '0'; wrap.innerHTML = ''; return; }
      wrap.dataset.open = '1';
      wrap.innerHTML = `<button data-g="">全部</button>`
        + names.map(g => `<button data-g="${fmt.esc(g)}" class="${DIST.groups && DIST.groups.has(g) ? 'on' : ''}">${fmt.esc(g)}</button>`).join('');
      $$('button', wrap).forEach(b => b.onclick = () => {
        const g = b.dataset.g;
        if (!g) DIST.groups = null;
        else {
          DIST.groups = DIST.groups || new Set();
          if (DIST.groups.has(g)) DIST.groups.delete(g); else DIST.groups.add(g);
          if (!DIST.groups.size) DIST.groups = null;
        }
        $$('button', wrap).forEach(x => x.classList.toggle('on', !!DIST.groups && DIST.groups.has(x.dataset.g)));
        const btn = $('#distGroupBtn'); if (btn) btn.textContent = `族群篩選${DIST.groups ? `（${DIST.groups.size}）` : ''}`;
        drawChgDist();
      });
    };
  }

  /* 圖16（Andy 2026-09-18）：「站上均線這邊需要可篩選曲線走勢圖可以看，
     需要將所有圖疊加看變化 更直觀分析，並且均線可以分 5 10 20 30 60 120 240 含篩選功能」。
     資料走獨立檔 ma_breadth.json（250 天 × 七條均線 × 27 個族群，約 287KB），
     只有這一頁會載。均線單選（一次看一條，七條疊在一起會看不出族群差異），
     族群複選（預設前 8 個 ＋ 全市場）。*/
  const MAT = { ma: '20', groups: null };
  async function drawMaTrend() {
    const host = $('#maTrendBox'); if (!host) return;
    const mb = await load('ma_breadth', { fallback: { dates: [], mas: [], series: {} } });
    if (!mb || !mb.dates || !mb.dates.length) { return empty('maTrend', '站上均線的歷史還在產出（下一輪盤後管線就會有）'); }
    const names = Object.keys(mb.series).filter(n => n !== '全市場');
    if (!MAT.groups) MAT.groups = new Set(['全市場', ...names.slice(0, 7)]);
    // 均線單選
    const pick = $('#maPick');
    if (pick) {
      pick.innerHTML = '<span class="muted">均線</span>'
        + `<div class="seg tiny" id="maSeg">${(mb.mas || []).map(n =>
          `<button data-n="${n}" class="${String(n) === MAT.ma ? 'on' : ''}">${n} 日</button>`).join('')}</div>`;
      $$('#maSeg button', pick).forEach(b => b.onclick = () => { MAT.ma = b.dataset.n; drawMaTrend(); });
    }
    // 族群複選
    const gbox = $('#maGroups');
    if (gbox) {
      gbox.innerHTML = ['全市場', ...names].map(n =>
        `<button data-g="${fmt.esc(n)}" class="${MAT.groups.has(n) ? 'on' : ''}">${fmt.esc(n)}</button>`).join('');
      $$('button', gbox).forEach(b => b.onclick = () => {
        const g = b.dataset.g;
        if (MAT.groups.has(g)) MAT.groups.delete(g); else MAT.groups.add(g);
        if (!MAT.groups.size) MAT.groups.add('全市場');
        drawMaTrend();
      });
    }
    const shown = ['全市場', ...names].filter(n => MAT.groups.has(n));
    const sub = $('#maTrendSub');
    if (sub) sub.textContent = `MA${MAT.ma}：${shown.length} 條線　·　${mb.dates[0]} ～ ${mb.dates[mb.dates.length - 1]}`;
    chart('maTrend', {
      tooltip: { ...tip, trigger: 'axis',
        formatter: (ps) => `<b>${ps[0].axisValue}</b><br>`
          + ps.filter(q => q.value != null).sort((a, b) => b.value - a.value).slice(0, 12)
              .map(q => `${q.marker}${q.seriesName} ${fmt.n(q.value, 1)}%`).join('<br>') },
      legend: { type: 'scroll', top: 0, textStyle: { color: CH.ink2 }, pageTextStyle: { color: CH.ink3 } },
      grid: { left: 52, right: 24, top: 34, bottom: 30 },
      xAxis: { ...axisStyle, type: 'category', data: mb.dates, axisLabel: { color: CH.ink3, formatter: (v) => String(v).slice(5) } },
      yAxis: { ...axisStyle, min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
      series: shown.map((n, i) => ({
        name: n, type: 'line', smooth: .25, showSymbol: false, connectNulls: true,
        data: (mb.series[n] || {})[MAT.ma] || [],
        lineStyle: { width: n === '全市場' ? 2.6 : 1.5,
          color: n === '全市場' ? CH.ink : (L.gcolorByName ? L.gcolorByName(n) : PALETTE[i % PALETTE.length]) },
        itemStyle: { color: n === '全市場' ? CH.ink : PALETTE[i % PALETTE.length] },
        markLine: i === 0 ? { silent: true, symbol: 'none', label: { show: false },
          lineStyle: { color: hexA(CH.ink3, .5), type: 'dashed' }, data: [{ yAxis: 50 }] } : undefined,
      })),
    }, { notMerge: true });
  }

  function drawChgDist() {
    const host = $('#chgDistBox'); if (!host) return;
    /* ★ D4：即時模式下換成「這一輪抓到報價的那幾檔」的即時漲跌幅。
       欄位和 stocks.json 一模一樣（`mudRows()` 負責對齊），所以下面整段完全不用改。*/
    const live = mudLive();
    const all = live ? mudRows() : (D.stocks || []);
    if (!all.length) { host.innerHTML = ''; return; }
    const isEtf = (r) => /^00/.test(String(r.code || ''));
    const pool = all.filter(r => r.chg_pct != null
      && (!DIST.market || r.market === DIST.market)
      && (DIST.etf || !isEtf(r))
      && (!DIST.groups || DIST.groups.has(r.group || '（未分類）')));
    // -10 ~ +10 每 2% 一格，共 10 格，外加兩端溢出
    const edges = [-10, -8, -6, -4, -2, 0, 2, 4, 6, 8, 10];
    const labels = ['≤ -10'];
    for (let i = 0; i < edges.length - 1; i++) labels.push(`${edges[i]} ~ ${edges[i + 1]}`);
    labels.push('≥ +10');
    const bins = new Array(labels.length).fill(0);
    pool.forEach(r => {
      const v = +r.chg_pct;
      if (v <= -10) { bins[0]++; return; }
      if (v >= 10) { bins[bins.length - 1]++; return; }
      let k = 0; while (k < edges.length - 1 && v > edges[k + 1]) k++;
      bins[k + 1]++;
    });
    const n = pool.length || 1;
    // 常態曲線：用這批樣本自己的平均與標準差，疊上去看「今天偏左還偏右」
    const mu = pool.reduce((s2, r) => s2 + (+r.chg_pct), 0) / n;
    const sd = Math.sqrt(pool.reduce((s2, r) => s2 + Math.pow(+r.chg_pct - mu, 2), 0) / n) || 1;
    const mids = labels.map((_, i) => (i === 0 ? -11 : i === labels.length - 1 ? 11 : (edges[i - 1] + edges[i]) / 2));
    const norm = mids.map(x => n * 2 / (sd * Math.sqrt(2 * Math.PI)) * Math.exp(-Math.pow(x - mu, 2) / (2 * sd * sd)));
    const c = chart('chgDist', {
      tooltip: { ...tip, trigger: 'axis',
        formatter: (ps) => { const i = ps[0].dataIndex;
          return `<b>${labels[i]}%</b><br>${bins[i]} 檔（${fmt.n(bins[i] / n * 100, 1)}%）<br><small>點一下只看這一段</small>`; } },
      grid: { left: 50, right: 20, top: 26, bottom: 34 },
      xAxis: { ...axisStyle, type: 'category', data: labels, axisLabel: { color: CH.ink3, fontSize: 10.5, interval: 0, rotate: 30 } },
      yAxis: { ...axisStyle, name: '家數', nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3 } },
      series: [
        { type: 'bar', data: bins.map((v, i) => ({ value: v,
            itemStyle: { color: chgColor(mids[i], 6), borderRadius: [3, 3, 0, 0] } })),
          barWidth: '72%',
          label: { show: true, position: 'top', color: CH.ink3, fontSize: 10.5,
            formatter: (q) => (q.value ? `${q.value}` : '') } },
        { type: 'line', data: norm, smooth: true, symbol: 'none', silent: true,
          lineStyle: { color: hexA(CH.ink3, .8), width: 1.4, type: 'dashed' } },
      ],
    }, { notMerge: true });
    const sub = $('#distSub');
    /* ★ D4：副標一定要跟著模式換 —— 即時那一版的分母是「抓到報價的這幾檔」，
       寫成和盤後一樣的「N 檔」會被讀成全市場（完整的口徑說明在上面的 `#mktLive`）。*/
    if (sub) sub.textContent = (live ? `⚡ 即時 · 抓到的 ${n} 檔（不是全市場）　` : `${n} 檔　`)
      + `平均 ${fmt.pct(mu)}　標準差 ${fmt.n(sd, 2)}%　`
      + `（虛線＝用這批樣本自己的平均與標準差畫的常態曲線）`;
    // 點某一段 → 下面只列那一段
    if (c) c.off('click').on('click', (p) => {
      const i = p.dataIndex;
      const lo = i === 0 ? -Infinity : edges[i - 1];
      const hi = i === labels.length - 1 ? Infinity : edges[i];
      const rows = pool.filter(r => (i === 0 ? r.chg_pct <= -10
        : i === labels.length - 1 ? r.chg_pct >= 10
          : r.chg_pct > lo && r.chg_pct <= hi))
        .sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 80);
      const box = $('#distPick'); if (!box) return;
      box.hidden = false;
      box.innerHTML = `<div class="hh"><b>${labels[i]}%</b><span class="m">${rows.length} 檔（依成交值）</span>
          <span class="sp"></span><button class="btn small" data-x="1">收起 ✕</button></div>
        <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">
          ${rows.map(r => L.stock(r.code, r.name, { cls: 'sm' })).join('') || '<span class="muted">這一段沒有股票</span>'}</div>`;
      const x = box.querySelector('[data-x]'); if (x) x.onclick = () => { box.hidden = true; };
    });
  }

  /* ================================================================ 漲跌家數／漲跌分佈的「即時」模式（D4）
     Andy 2026-09-23：「漲跌幅需要多一個『即時』Mode」。比照資金去向與輪動時鐘那兩顆「即時」鈕：
     同一顆 `.pb.livebtn`／同一套 seg、按下去切換、每分鐘一輪、再按一次退回盤後，**盤後是預設**。

     ── 這個模式在回答什麼 ──
       盤後那一版回答「今天收盤，全市場 2000 多檔的漲跌長什麼樣」；
       即時這一版回答「**現在這一刻，我們抓得到的這一批**的漲跌長什麼樣」。
       這是兩個不同的問題，所以下面那條誠實界線不是客套話，是這張圖的定義本身。

     ── 誠實界線（`mudStamp()` 會把每一條都印在畫面上，不准省略）──
       ① **這不是全市場。** 即時報價是逐檔打的，一輪最多幾百檔；這裡抓的是
          **人工族群的成分股聯集**（`groups_detail` 去掉 `ind_*` 自動桶），約 440 檔，
          而 `stocks.json` 有 2300 多檔。所以畫面上一定要同時寫出
          「抓到幾檔 / 想抓幾檔 / 佔全市場幾 %」三個數字（＝比照 `rlvStamp()` 的涵蓋率寫法）。
       ② **樣本是偏的，不只是少。** 這一批是「有人工分族群的股票」，本來就偏中大型、偏電子，
          所以即時的分佈會比全市場窄、平均會比較貼近權值股。這句話要寫出來，
          不然使用者會把它讀成「全市場的縮影」。
       ③ **漲跌幅是真的，成交值是估的。** 漲跌幅＝(現價 − 昨收) ÷ 昨收，是真值；
          「成交值前段」那一格用的是「現價 × 累計張數 × 1000」的**估算值**
          （即時端點沒有每檔的累積成交金額），和盤後的真實成交值不是同一個東西。
       ④ **非盤中按下去畫的是最後一次報價的快照**，不是盤中變化。

     ── 為什麼不直接抓全市場 ──
       2300 檔要 24 個請求、而且每分鐘一輪；免費代理撐不住，也沒有必要 ——
       「現在誰在漲」看這 440 檔已經夠做判斷，把口徑寫清楚比硬湊一個假的全市場有用。*/
  const MUD = { on: false, q: {}, at: 0, busy: false, err: '', intraday: true,
    timer: null, reqs: 0, hit: 0, codes: 0, quoteAt: '' };
  const MUD_BATCH = 100;               // 一個請求塞幾檔（沿用 live.js 實測的批次大小）
  const MUD_MS = 60 * 1000;            // 每分鐘一輪（和另外兩個即時模式同節奏）

  /* 這一輪要抓哪些股票：所有**人工族群**的成分股（去重）。
     自動桶（`ind_*`）跳過 —— 光 ETF 一格就三百多檔，抓它不會讓分佈更準，只會把請求數翻倍。*/
  function mudCodes() {
    const det = D.groups_detail || {};
    const seen = new Set(), out = [];
    Object.keys(det).forEach(gid => {
      if (isAutoBucket(gid)) return;
      ((det[gid] || {}).members || []).forEach(m => {
        const c = String(m.code); if (c && !seen.has(c)) { seen.add(c); out.push(c); }
      });
    });
    return out;
  }

  /* 把報價換成「和 stocks.json 同樣欄位」的列，下游（分佈圖、五個分頁、表格）完全不用改。
     ★ 只回**真的抓到報價**的那幾檔 —— 沒抓到的不可以拿收盤值混進來充數，
       那會變成「一半即時一半盤後」的分佈圖，比不做還糟。*/
  function mudRows() {
    const all = D.stocks || [];
    const out = [];
    all.forEach(r => {
      const q = MUD.q[String(r.code)];
      if (!q || q.chgPct == null) return;
      out.push({ ...r, chg_pct: q.chgPct,
        close: q.price != null ? q.price : r.close,
        // 成交值是估的（端點沒有每檔的累積成交金額）；畫面上有寫，tooltip 也有寫
        turnover: (q.price != null && q.volume != null) ? q.price * q.volume * 1000 : null,
        est: true });
    });
    return out;
  }
  const mudLive = () => MUD.on && !MUD.err && Object.keys(MUD.q).length > 0;

  async function mudFetch() {
    if (!window.Live || !window.Live.fetchQuotes) throw new Error('即時報價層還沒載入（live.js）');
    const codes = mudCodes();
    if (!codes.length) throw new Error('成分股資料還沒載入，抓不了即時');
    const q = {};
    let reqs = 0;
    for (let i = 0; i < codes.length; i += MUD_BATCH) {
      Object.assign(q, await window.Live.fetchQuotes(codes.slice(i, i + MUD_BATCH)));
      reqs++;
    }
    const hit = Object.keys(q).filter(c => q[c] && q[c].chgPct != null);
    if (!hit.length) throw new Error('報價回來了，但沒有一檔算得出漲跌幅');
    MUD.q = q; MUD.reqs = reqs; MUD.codes = codes.length; MUD.hit = hit.length;
    MUD.quoteAt = (q[hit[0]] || {}).time || '';
    MUD.at = Date.now(); MUD.err = '';
  }

  /* 狀態列。★ 誠實標示全部寫在這裡、不散在圖上 —— 圖上塞不下，
     而這幾句話少一句整張圖就會被讀錯（和 `rlvStamp()` 同一條規矩）。*/
  function mudStamp() {
    const el = $('#mktLive'); if (!el) return;
    if (!MUD.on) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    /* ⚠ 順序：**錯誤要排在「抓取中」前面**。抓失敗時 `MUD.at` 永遠是 0，
       先判 `!MUD.at` 的話畫面會一直停在「抓取中…」，使用者完全看不到失敗原因，
       也按不到「一鍵退回盤後」。*/
    if (MUD.err) {
      el.innerHTML = `<b class="bad">即時抓不到報價</b>　${fmt.esc(MUD.err)}`
        + '　·　下面畫的仍然是<b>盤後</b>那一份（圖沒有變空白）'
        + '　<button type="button" class="btn small" id="mktLiveBack">一鍵退回盤後</button>';
      const b = $('#mktLiveBack'); if (b) b.onclick = () => mudOff();
      return;
    }
    /* 還沒有任何一輪成功過（`at` 是 0）＝第一輪還在路上。
       ★ 不可以用 `MUD.busy` 當條件：`mudToggle()` 會先畫一次狀態列、再去跑第一輪，
         那一瞬間 `busy` 還是 false，畫面就會先閃一格「涵蓋率 —%」的假資訊。*/
    if (!MUD.at) { el.innerHTML = '<b>即時</b>　抓取中…'; return; }
    const uni = (D.stocks || []).length || 0;
    el.innerHTML = (MUD.intraday
      ? `<b class="live">即時</b>　報價 ${fmt.esc(MUD.quoteAt || '—')}　每分鐘更新`
      : '<b class="warn">現在不是盤中</b>（現貨 09:00–13:30）　下面畫的是<b>最後一次報價的快照</b>，不是盤中變化')
      + `　·　<b>涵蓋率 ${uni ? fmt.n(MUD.hit / uni * 100, 1) : '—'}%</b>`
      + `（抓到 <b>${MUD.hit}</b> 檔 / 想抓 ${MUD.codes} 檔 / 全市場 ${uni} 檔　·　${MUD.reqs} 個請求）`
      + '<br>· <b>這不是全市場</b>：即時報價逐檔打，所以只抓「有人工分族群」的成分股聯集'
      + '（自動桶 <code>ind_*</code> 跳過）。這一批本來就<b>偏中大型、偏電子</b>，'
      + '分佈會比全市場<b>窄</b>、平均比較貼近權值股 —— 它是這一批的樣子，不是全市場的縮影。'
      + '<br>· <b>漲跌幅是真的，成交值是估的</b>：漲跌幅＝(現價 − 昨收) ÷ 昨收；'
      + '「成交值前段」那一格是「現價 × 累計張數 × 1000」的<b>估算值</b>'
      + '（即時端點沒有每檔的累積成交金額），和盤後的真實成交值不是同一個數字。';
  }

  async function mudTick() {
    if (!MUD.on || MUD.busy) return;
    /* 離開這一頁就把即時關掉 —— 每分鐘對一個看不到的畫面打 5 個請求，
       使用者沒有任何方式察覺，只會看到額度莫名其妙被吃掉。*/
    if (!/^#market/.test(location.hash || '')) { mudOff(false); return; }
    MUD.busy = true; MUD.intraday = !window.Live || window.Live.isIntraday();
    try { await mudFetch(); } catch (e) { MUD.err = (e && e.message) || String(e); }
    MUD.busy = false;
    if (!MUD.on) return;
    if (mktKind === 'updown') drawMarket('updown');
    mudStamp();
  }
  function mudOff(redraw) {
    MUD.on = false;
    if (MUD.timer) { clearInterval(MUD.timer); MUD.timer = null; }
    MUD.q = {}; MUD.err = ''; MUD.at = 0;
    if (redraw !== false && mktKind === 'updown') drawMarket('updown');
  }
  function mudToggle() {
    if (MUD.on) return mudOff();
    /* ⚠ 這裡**不可以**先把 `MUD.busy` 設成 true —— `mudTick()` 開頭就是
       `if (!MUD.on || MUD.busy) return;`，設了它第一輪會直接被自己擋掉，
       畫面永遠停在「抓取中…」（實測踩過）。*/
    MUD.on = true; MUD.err = '';
    MUD.intraday = !window.Live || window.Live.isIntraday();
    drawMarket('updown');                      // 先把「抓取中…」畫出來，不要讓人按了沒反應
    mudTick();
    if (!MUD.timer) MUD.timer = setInterval(mudTick, MUD_MS);
  }

  function drawMarket(kind) {
    // 舊書籤 #market/top5 進來時落回漲跌家數（那一頁 2026-09-18 拿掉了）
    if (!MKT.some(m => m[0] === kind)) kind = 'updown';
    if (kind !== mktKind) mktTab = 0;
    mktKind = kind;
    $$('#mktSeg2 button').forEach(b => b.classList.toggle('on', b.dataset.k === kind));
    const heat = D.market_heat || {}, b = heat.breadth || {}, mv = b.movers || {};
    const gt = D.groups_today || [], cands = D.candidates || [], gd = D.groups_detail || {};
    const body = $('#mktBody'); const title = $('#mktTitle');
    const PCT = ['漲跌', r => `<span class="${fmt.cls(r.chg_pct)}">${fmt.pct(r.chg_pct, 2)}</span>`];
    const CLOSE = ['收盤', r => fmt.n(r.close)];
    const TO = ['成交值', r => fmt.yi(r.turnover)];
    const bind = () => $$('#mktBody tr[data-code]').forEach(tr =>
      tr.onclick = (e) => { if (e.target.closest('a')) return; goStock(tr.dataset.code); });

    if (kind === 'updown') {
      /* ★ D4（Andy 2026-09-23「漲跌幅需要多一個『即時』Mode」）：
         同一塊版面兩種口徑。盤後＝後端算好的全市場統計（`market_heat.breadth.movers`）；
         即時＝這一輪抓到報價的那幾百檔自己重算一次。
         兩者**不可以混著用** —— 混一半會得到一張誰也不是的圖，所以下面是整段分岔，
         而且每一個數字旁邊都跟著同一份涵蓋率說明（`#mktLive`）。*/
      const live = mudLive();
      const lr = live ? mudRows() : [];
      const top = (arr, key, dir) => arr.slice()
        .sort((a, b) => dir * ((a[key] || 0) - (b[key] || 0))).slice(0, 30);
      const cnt = live ? {
        adv: lr.filter(r => r.chg_pct > 0).length,
        dec: lr.filter(r => r.chg_pct < 0).length,
        flat: lr.filter(r => r.chg_pct === 0).length,
        lu: lr.filter(r => r.chg_pct >= 9.5).length,
        ld: lr.filter(r => r.chg_pct <= -9.5).length,
      } : null;
      title.innerHTML = live
        ? `漲跌家數 <small>⚡ 即時：抓到的 ${lr.length} 檔裡 ${cnt.adv} 漲 / ${cnt.dec} 跌，`
          + `漲停 ${cnt.lu} 檔、跌停 ${cnt.ld} 檔　·　<b>這不是全市場</b>（口徑見下方）</small>`
        : `漲跌家數 <small>今天 ${heat.advancers || 0} 漲 / ${heat.decliners || 0} 跌，漲停 ${(mv.counts || {}).limit_up ?? '—'} 檔、跌停 ${(mv.counts || {}).limit_down ?? '—'} 檔</small>`;
      const sets = (live ? [
        ['漲停', lr.filter(r => r.chg_pct >= 9.5), '漲幅 ≥ 9.5%（現價 vs 昨收，是真值）'],
        ['跌停', lr.filter(r => r.chg_pct <= -9.5), '跌幅 ≤ -9.5%（現價 vs 昨收，是真值）'],
        ['漲幅前段', top(lr, 'chg_pct', -1), '現在漲最多的（只在抓到報價的這一批裡排）'],
        ['跌幅前段', top(lr, 'chg_pct', 1), '現在跌最多的（只在抓到報價的這一批裡排）'],
        ['成交值前段', top(lr.filter(r => r.turnover != null), 'turnover', -1),
          '量最大的。⚠ 這一欄是「現價 × 累計張數」的估算值，不是真實成交值'],
      ] : [
        ['漲停', mv.limit_up, '漲幅 ≥ 9.5%（成交價照檔位跳，實際常落在 9.7~10.0）'],
        ['跌停', mv.limit_down, '跌幅 ≤ -9.5%'],
        ['漲幅前段', mv.up, '今天漲最多的'],
        ['跌幅前段', mv.down, '今天跌最多的'],
        ['成交值前段', mv.turnover, '今天量最大的，這裡才是真正的戰場'],
      ]).filter(t => t[1] && t[1].length);
      if (!sets.length && !live) { body.innerHTML = '<div class="empty">今天沒有明細資料</div>'; return; }
      if (mktTab >= sets.length) mktTab = 0;
      const draw = () => {
        const t = sets[mktTab];
        // 即時模式剛按下去、報價還沒回來時 sets 會是空的 —— 給一句話，不要留一塊空白
        if (!t) { $('#mktInner').innerHTML = '<div class="empty">即時報價還沒回來（下一輪就會有）</div>'; return; }
        $('#mktInner').innerHTML = `<div class="kpinote">${t[2]}</div>` + stockTable(t[1], [PCT, CLOSE, TO]);
        bind();
      };
      /* ★ D4：模式切換列。盤後是預設（Andy 指定），即時那一顆亮起來的樣子沿用
         全站那顆 `.pb.livebtn`（資金去向、輪動時鐘都是同一顆），不另外發明一種。*/
      body.innerHTML = `<div class="row" style="gap:8px;align-items:center;margin:0 0 10px">
          <div class="seg tiny" id="mktMode">
            <button data-m="eod" class="${live || MUD.on ? '' : 'on'}">盤後</button>
            <button data-m="live" class="${MUD.on ? 'on' : ''}">⚡ 即時</button></div>
          <span class="muted" style="font-size:12.5px">盤後＝今天收盤的全市場統計；即時＝現在這一刻、我們抓得到的那一批</span>
        </div>
        <div id="mktLive" class="note livenote" ${MUD.on ? '' : 'hidden'}></div>
        <div class="card" style="margin:10px 0 14px;padding:12px 14px">
          <div class="row spread"><h3 style="margin:0">漲跌分佈 <small id="distSub"></small></h3>
            <div class="row" id="distFilter" style="gap:8px;flex-wrap:wrap"></div></div>
          <div id="chgDistBox"><div id="chgDist" class="chart" style="min-height:260px"></div></div>
          <div class="hpanel" id="distPick" hidden></div></div>`
        + `<div class="seg" id="mktTabs">${sets.map((t, i) =>
        `<button data-i="${i}" class="${i === mktTab ? 'on' : ''}">${t[0]} <em>${t[1].length}</em></button>`).join('')}</div>`
        + `<div id="mktInner" style="margin-top:10px"></div>`;
      $$('#mktMode button').forEach(b => b.onclick = () => {
        const want = b.dataset.m === 'live';
        if (want === MUD.on) return;              // 已經在這個模式就不要白重畫一次
        mudToggle();
      });
      mudStamp();
      wireDistFilter();
      drawChgDist();          // ★ 一定要在 body.innerHTML 之後 —— #chgDistBox 是那時才存在的
      $$('#mktTabs button').forEach(btn => btn.onclick = () => {
        mktTab = +btn.dataset.i;
        $$('#mktTabs button').forEach(x => x.classList.toggle('on', x === btn)); draw();
      });
      draw();
      return;
    }

    if (kind === 'ma') {
      const gs = (b.by_group || []);
      title.innerHTML = `站上均線 <small>全市場 ${b.pct_above_ma20 ?? '—'}% 站上 MA20（樣本 ${b.n ?? '—'} 檔）</small>`;
      body.innerHTML = `<div class="card" style="margin:0 0 14px;padding:12px 14px">
          <div class="row spread"><h3 style="margin:0">站上均線走勢 <small id="maTrendSub">七條均線疊起來看變化</small></h3></div>
          <div class="row" id="maPick" style="gap:10px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-2);margin:8px 0"></div>
          <div class="chainchips" id="maGroups" style="max-height:104px;overflow:auto"></div>
          <div id="maTrendBox"><div id="maTrend" class="chart" style="min-height:300px"></div></div></div>`
        + `<div class="kpinote">下面這一排是**今天的快照**：條越長＝這個族群越多成分股站在 20 日均線之上。點族群看成分股。</div>`
        + (gs.length ? `<div class="magrid">${gs.map(g => `<div class="ma" data-gid="${g.group_id}">
            <div class="n">${fmt.esc(g.group_name)}<em>${g.n} 檔</em></div>
            <div class="bar"><i style="width:${g.pct20}%;background:${g.pct20 >= 60 ? 'var(--rise)' : g.pct20 >= 40 ? 'var(--amber)' : 'var(--fall)'}"></i></div>
            <div class="v">MA20 ${g.pct20}%<span>MA60 ${g.pct60}%</span></div></div>`).join('')}</div>`
          : '<div class="empty">均線統計還在產生</div>');
      $$('#mktBody .ma[data-gid]').forEach(e => e.onclick = () => { location.hash = '#industry/group/' + e.dataset.gid; });
      drawMaTrend();
      return;
    }

    if (kind === 'top5') {
      const top = gt.slice().sort((a, c) => c.turnover - a.turnover).slice(0, 10);
      title.innerHTML = `資金集中 <small>前五大族群吃掉 ${heat.top5_share != null ? heat.top5_share.toFixed(1) + '%' : '—'} 的成交值</small>`;
      body.innerHTML = `<div class="kpinote">吃掉最多成交值的十個族群，以及每個族群裡量最大的成分股。
        越高＝行情越縮圈在主流，這時候買冷門股不容易動。</div>`
        + `<div class="top5grid">${top.map((g, i) => {
          const det = gd[g.group_id] || {};
          const ms = (det.members || []).slice().sort((a, c) => (c.turnover || 0) - (a.turnover || 0)).slice(0, 10);
          return `<div class="t5"><div class="h">${i + 1}. ${L.group(g.group_id, g.group_name)}<em>${fmt.n(g.turnover_share, 1)}%</em></div>
            <div class="m">${fmt.yi(g.turnover)}　<span class="${fmt.cls(g.chg_pct)}">${fmt.pct(g.chg_pct)}</span>　${g.constituents || 0} 檔</div>
            <div class="ls">${ms.map(m => L.stock(m.code, m.name)).join('') || '<span class="muted">成分股整理中</span>'}</div></div>`;
        }).join('')}</div>`;
      return;
    }

    // 今日候選
    const ab = cands.filter(c => c.grade === 'A' || c.grade === 'B');
    const use = ab.length ? ab : cands.slice().sort((a, c) => (c.score_all || 0) - (a.score_all || 0)).slice(0, 40);
    title.innerHTML = `今日候選 <small>${ab.length ? `A ${cands.filter(c => c.grade === 'A').length} 檔 / B ${cands.filter(c => c.grade === 'B').length} 檔` : '今天沒有 A / B'}</small>`;
    body.innerHTML = `<div class="kpinote">${ab.length
      ? 'A＝回檔承接、B＝突破追進。技術面永遠是最後一關，方向與估值要先過。'
      : '今天技術面沒有任何一檔達到 A / B（大盤走弱時很常見）。下面是綜合分最高的前 40 檔，當觀察名單就好，不是進場訊號。'}
      　完整的四面向理由在總覽的「今日候選」。</div>`
      + stockTable(use.map(c => ({ code: c.code, name: c.name, group_id: c.group_id, group_name: c.group,
          chg_pct: c.chg_pct, close: c.close, grade: c.grade, verdict: c.verdict, score: c.score_all })),
        [['判定', r => r.grade ? `<span class="grade ${r.grade}">${r.grade}</span>` : `<span class="muted">${fmt.esc(r.verdict || '—')}</span>`],
         ['綜合分', r => r.score != null ? fmt.n(r.score, 0) : '—'], PCT, CLOSE]);
    bind();
  }

  // ---------------------------------------------------------------- 總覽
  async function renderOverview() {
    wireHowto($('#v-overview'));
    // 最上面三張大盤圖（加權 / 櫃買 / 台指期）。它自己去抓 mis 的當日分時，不等下面的 JSON。
    if (window.Market3) window.Market3.mount();
    /* ★ 2026-09-23：多載一份 `sankey_daily` —— 右下角那塊換成「昨日資金去向分流圖」（D7）之後
       總覽也要用到它。它和資金流向頁吃的是**同一份檔案**（同一個口徑，不另外算一份）。 */
    // ★ 2026-09-23：`group_valuation` 不再載入 —— 總覽的「族群估值」散布圖已移除，它是全站最後一個讀者。
    const [heat, gt, rot, cands, f3, th, trust, , , sd] = await Promise.all([load('market_heat'), load('groups_today'), load('rotation'), load('candidates'), load('flow_v3'), load('themes'), load('trust_streak'), load('groups_detail'), load('inst_streak', { fallback: {} }), load('sankey_daily', { fallback: null })]);
    // hero
    const b = (heat && heat.breadth) || {};
    const mv = b.movers || {};
    // KPI 點得開：只看到「567 / 1545」沒辦法做任何事，要能往下看是哪些股票（Andy）
    const kp = (l, v, d, cls, drill) => `<div class="card tight kpi${drill ? ' clickable' : ''}"${drill ? ` data-drill="${drill}"` : ''}>`
      + `<div class="l">${l}${drill ? '<span class="more">看明細 ›</span>' : ''}</div><div class="v ${cls || ''}">${v}</div><div class="d">${d || ''}</div></div>`;
    $('#hero').innerHTML = [
      // 加權指數是 mis 的 tse_t00.tw；盤中每分鐘跳一次（live.js）
      kp('加權指數', `<span data-live="idx" data-lc="t00">${fmt.n(heat && heat.taiex, 0)}</span>`,
         heat ? `<span class="${fmt.cls(heat.change)}" data-live="chg" data-lc="t00">${fmt.pct(heat.change / (heat.taiex - heat.change) * 100)}</span>` : '', heat && fmt.cls(heat.change)),
      kp('成交值', heat ? fmt.yi(heat.turnover) : '—', heat && heat.turnover_ma20 ? `20 日均 ${fmt.yi(heat.turnover_ma20)}` : ''),
      kp('漲 / 跌家數', heat ? `<span class="up">${heat.advancers}</span> <span class="muted">/</span> <span class="down">${heat.decliners}</span>` : '—',
         mv.counts ? `漲停 ${mv.counts.limit_up}　跌停 ${mv.counts.limit_down}　平盤 ${heat.unchanged}` : (heat ? `平盤 ${heat.unchanged}` : ''), '', mv.counts ? 'updown' : ''),
      kp('站上 MA20', b.pct_above_ma20 != null ? b.pct_above_ma20 + '%' : '—', `MA60 ${b.pct_above_ma60 ?? '—'}%　樣本 ${b.n ?? '—'}`,
         '', (b.by_group || []).length ? 'ma' : ''),
      // 「資金集中」那一頁 2026-09-18 拿掉了，改導到資金流向頁的集中度圖（那裡功能更完整）
      kp('前五族群佔比', heat && heat.top5_share != null ? heat.top5_share.toFixed(1) + '%' : '—', '越高＝資金越集中', '', (gt || []).length ? '#flow>conc' : ''),
      kp('今日候選', `<span class="up">${b.grade_a ?? 0}</span> A <span class="muted">/</span> <span class="amber">${b.grade_b ?? 0}</span> B`, '回檔承接 / 突破追進', '', 'cand'),
    ].join('');
    wireKpiDrill();
    renderHeat(gt, rot);
    /* ★ 2026-09-23（Andy：「總覽 輪動階段 上方的『放大』移除，並且需要圓圈大一點」）。
       · `#rotMiniZoomBtn` 整顆移除（連同這裡的接線）——「放大」這個能力沒有消失：
         點卡片標題旁邊的分頁「資金流向」就是同一張時鐘的完整版（有拉Bar、篩選、播放）。
       · 圓圈放大的做法**不是**把卡片變高就好：`renderRotClock` 的 compact 半徑是
         66%（`polar.radius`），那是還有族群名標籤時留的餘裕；compact 本來就不畫標籤
         （`label.show: !compact`），只有四個象限名貼在盤外，所以 66% → 82% 純粹是把
         一直空著的那一圈還給盤面。容器高度同步 300 → 360（見 index.html），
         不然 82% 只是「在同樣小的框裡畫大一點」。
       · `board: 'rotMini'` 也不再傳 —— 那四格階段卡已經換成「昨日資金去向分流圖」（D7）。*/
    renderRotation(f3 && f3.rrg, 5, { clock: 'rotClockMini', compact: true });
    renderOvFlow(sd);
    renderThemeStrip(th);
    renderCandidates(cands);
    renderBreadth(heat);
    renderTrust(trust, cands);
    wireStreak(trust, cands);
    /* Andy（09-13）：「將這邊的縮放功能取消」—— 滾輪縮放**只留熱力圖類**
       （總覽資金熱力、產業地圖板塊、題材資金熱力）。其餘的圖一律原尺寸顯示：
       徽章會壓在圖上、滾輪又會搶走頁面捲動，代價大於收益。 */
  }

  // 圖表下方的可點連結列：圖上點得到的東西，這裡也一定點得到（手機沒有 hover）
  function linkRow(afterId, html, label) {
    const el = document.getElementById(afterId); if (!el) return;
    // 圖被包進放大層時，連結列要掛在放大層外面，否則放大時會跟著被裁掉
    const at = el.closest('.zwrap') || el;
    let row = at.nextElementSibling; if (!row || !row.classList.contains('linkrow')) { row = document.createElement('div'); row.className = 'linkrow'; at.parentNode.insertBefore(row, at.nextSibling); }
    row.innerHTML = (label ? `<span class="muted">${label}</span>` : '') + html;
  }
  // 資金熱力圖：不用 treemap 的 roam 縮放 —— 它會把整張圖平移縮放，而且狀態留在 instance 裡，
  // 換分頁再回來就是一片空白（Andy 遇到的就是這個），而且「只能放大縮小整張圖」也解決不了小方塊看不到。
  // 改成產業鏈下鑽：上面一排晶片點半導體就只看半導體，點「全部」回到原來的圖。
  /* 產業鏈的中文名。★ 2026-09-21（Andy 截圖上出現一格英文 `financial`）：
     這張表以前是**寫死的第二份對照表**，族群改版新增的 `software` / `financial`
     沒補進來，篩選列就直接把英文 id 印在畫面上（全站繁體中文是硬規則）。
     正解不是再補兩行，是**以 payload 為準**：`industry_map.json` 的 `chains[].name`
     已經帶著「金融」「軟體與資訊服務」進來了（`L.chains`，來源是 groups.yaml）。
     這裡只留兩種 fallback：
       · `industry`＝法定產業別那個**虛擬**分類鍵，它不是 groups.yaml 的一條鏈，payload 裡沒有；
       · `L` 還沒 init 完就被讀到時的暫時值（實務上不會發生，但不要讓畫面出現英文 id）。*/
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子',
    software: '軟體與資訊服務', financial: '金融',
    traditional: '傳產', infrastructure: '基礎建設', industry: '其他產業別' };
  const chainLabel = (cid) => L.chains[cid] || CHAIN_NAME[cid] || cid;
  let heatChain = null;

  /* 放大罩：熱力圖方塊太小看不清楚時，全螢幕看同一張圖。
     刻意不做「拖曳平移」—— treemap 一旦可以拖，整張圖就會被拖走而且回不來
     （Andy 遇到的空白畫面就是這樣來的）。要看細節就放大或下鑽，位置永遠固定。 */
  function openZoom(title, render, onClose) {
    const ov = $('#zoomOv'); if (!ov) return;
    $('#zoomTitle').textContent = title;
    ov.hidden = false;
    document.body.style.overflow = 'hidden';
    const close = () => {
      ov.hidden = true; document.body.style.overflow = '';
      const c = echarts.getInstanceByDom($('#zoomBody')); if (c) c.dispose();
      $('#zoomChips').innerHTML = '';
      /* ★ 2026-09-20（E2）：控制項列也要清掉。以前只清 #zoomChips，
         所以開過輪動時鐘的放大視窗之後，再去開熱力圖的放大，
         上面還掛著輪動時鐘的拉Bar 與篩選列（按了當然沒反應）。*/
      const tl = $('#zoomTools'); if (tl) tl.innerHTML = '';
      document.removeEventListener('keydown', esc);
      if (onClose) { try { onClose(); } catch (e) { /* 關閉流程不要因為同步失敗卡住 */ } }
    };
    const esc = (e) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', esc);
    $('#zoomClose').onclick = close;
    ov.onclick = (e) => { if (e.target === ov) close(); };
    setTimeout(() => { render($('#zoomBody'), $('#zoomChips'), close); }, 30);
  }

  // 點方塊後在原地列出成分股（不跳頁），每一檔都點得進個股頁
  /* opts.scroll === false 時不要自己捲動頁面。
     2026-09-18 圖四踩到：排行的成分股面板就貼在圖表正下方（同一張卡片裡），
     再 scrollIntoView 一次會把頁面往下推 895px —— **使用者剛點的那張圖直接被捲出畫面**。
     驗收量到的是「第二次點沒收起來」，追下去才發現長條的視窗座標變成 y = -491，
     也就是圖已經不在畫面上了，點當然點不到。面板本來就在旁邊的情況一律不要捲。*/
  function heatPanel(panelId, gid, gname, extra, opts) {
    const box = $('#' + panelId); if (!box) return;
    const det = (D.groups_detail || {})[gid] || {};
    const ms = (det.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 40);
    box.hidden = false;
    box.innerHTML = `<div class="hh"><b>${fmt.esc(gname || det.group_name || gid)}</b>
        <span class="m">${extra || ''}</span><span class="sp"></span>
        <a class="pill cyan" href="#industry/group/${gid}">進族群頁 →</a>
        <button class="btn small" data-x="1">收起 ✕</button></div>
      ${ms.length ? `<div class="ms">${ms.map(m => `<a href="#stock/${m.code}"><span>${fmt.esc(m.name)}</span>
          <span class="c">${m.code}</span><span class="g ${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct)}</span></a>`).join('')}</div>`
        : '<div class="empty">這個族群的成分股整理中</div>'}`;
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => { box.hidden = true; };
    if (!opts || opts.scroll !== false) box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // 熱力圖的 option 與資料（放大罩與原圖共用，才不會兩邊畫出不一樣的東西）
  function heatOption(gt, rot, chain, big) {
    const rotMap = {}; (rot || []).forEach(r => { rotMap[r.group_id] = r.rotation; });
    const chains = {}; gt.forEach(g => { const c = g.chain || 'industry'; (chains[c] = chains[c] || []).push(g); });
    const mk = (g) => ({ name: g.group_name, value: g.turnover, gid: g.group_id, chg: g.chg_pct,
      rot: rotMap[g.group_id], share: g.turnover_share,
      itemStyle: { color: chgColor(rotMap[g.group_id] != null ? rotMap[g.group_id] * 3 : g.chg_pct, 3) } });
    const inChain = chain && chains[chain] ? chains[chain] : null;
    const data = inChain ? inChain.map(mk)
      : Object.keys(chains).map(cid => ({ name: chainLabel(cid), cid, children: chains[cid].map(mk) }));
    const SK = treeSkin();
    return { chains, inChain, option: {
      tooltip: { ...tip, formatter: p => p.data.gid
        ? `<b>${p.name}</b><br>成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span><br>資金流向 <span style="color:${upDown(p.data.rot)}">${p.data.rot != null ? (p.data.rot > 0 ? '流入 +' : '流出 ') + p.data.rot.toFixed(2) + ' pp' : '—'}</span><br><small>點一下看成分股</small>`
        : `<b>${p.name}</b><br><small>點一下只看這條產業鏈</small>` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false },
        width: '100%', height: '100%', top: 0, left: 0, visibleMin: inChain ? (big ? 5 : 20) : (big ? 40 : 120),
        /* 顏色＝資金流向（5日vs20日佔比），文字以前只寫漲跌 —— 於是出現「紅底寫 -0.7%」，
           使用者只會當成 bug。現在方塊上兩個數字都寫，而且標明哪個是哪個。 */
        label: { show: true, formatter: p => `${p.name}\n${fmt.pct(p.data.chg)}\n${p.data.rot != null ? '資金 ' + (p.data.rot > 0 ? '+' : '') + p.data.rot.toFixed(1) + 'pp' : '資金 —'}`,
          lineHeight: big ? 19 : 16,
          fontSize: big ? 15 : (inChain ? 14 : 13), ...SK.label, overflow: 'truncate' },
        upperLabel: { show: !inChain, height: big ? 26 : 22, fontSize: big ? 13 : 12, ...SK.upper },
        itemStyle: { borderColor: SK.border, borderWidth: 2, gapWidth: 2 },
        levels: inChain ? [{ itemStyle: { gapWidth: 2 } }]
          : [{ itemStyle: { borderColor: SK.border, borderWidth: 3, gapWidth: 3 } }, { itemStyle: { gapWidth: 1 } }],
        data }] } };
  }

  function heatChips(chains, box, cur, onPick) {
    if (!box) return;
    const order = Object.keys(chains).sort((a, b) =>
      chains[b].reduce((s, g) => s + g.turnover, 0) - chains[a].reduce((s, g) => s + g.turnover, 0));
    box.innerHTML = `<button data-c="" class="${cur ? '' : 'on'}">全部</button>`
      + order.map(cid => {
        const sh = chains[cid].reduce((s, g) => s + (g.turnover_share || 0), 0);
        return `<button data-c="${cid}" class="${cur === cid ? 'on' : ''}">${chainLabel(cid)}<em>${fmt.n(sh, 1)}%</em></button>`;
      }).join('');
    $$('button', box).forEach(b => b.onclick = () => onPick(b.dataset.c || null));
  }

  function renderHeat(gt, rot) {
    if (!gt || !gt.length) return empty('heat');
    const { chains, inChain, option } = heatOption(gt, rot, heatChain, false);
    if (heatChain && !chains[heatChain]) heatChain = null;
    heatChips(chains, $('#heatChips'), heatChain, (c) => { heatChain = c; renderHeat(gt, rot); });
    const list = inChain || gt.filter(g => !g.group_id.startsWith('ind_'));
    linkRow('heat', list.slice().sort((a, b) => b.turnover - a.turnover).slice(0, 14)
      .map(g => L.group(g.group_id, g.group_name)).join(''), '族群');
    const c = chart('heat', option);
    wheelZoom($('#heatWrap'), { onZoom: () => { const i = echarts.getInstanceByDom($('#heat')); if (i) i.resize(); } });
    if (c) c.off('click').on('click', p => {
      if (!p.data) return;
      if (p.data.gid) heatPanel('heatPanel', p.data.gid, p.name,
        `成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）　${fmt.pct(p.data.chg)}`);
      else if (p.data.cid) { heatChain = p.data.cid; renderHeat(gt, rot); }
    });
    const zb = $('#heatZoom');
    if (zb) zb.onclick = () => openZoom('資金熱力圖', (body, chipBox) => {
      let ch = heatChain;
      const draw = () => {
        const r = heatOption(gt, rot, ch, true);
        heatChips(r.chains, chipBox, ch, (c2) => { ch = c2; draw(); });
        const bc = chart(body, r.option);
        if (bc) bc.off('click').on('click', p => {
          if (!p.data) return;
          if (p.data.gid) location.hash = '#industry/group/' + p.data.gid;
          else if (p.data.cid) { ch = p.data.cid; draw(); }
        });
      };
      draw();
    });
  }

  /* 輪動階段的四個顏色。
     ★ `color` 是 **getter**，不是寫死的色碼（Andy 2026-09-16：
       「一開始製作是黑色底，很多數據都是白色線條及文字，檢查所有切換回白色 UI 後需要更改的顏色」）。
     以前這裡寫死深色主題的螢光色（#3ee0ff / #ffb454 / #2ee59d），切到淺色主題之後
     這些字直接印在近白色的面板上 —— 實測對比度只有 1.41～1.57，等於看不見。
     改成讀 `CH`（切主題時 refreshPalette() 會就地改寫它），讀的當下才取值，
     所有既有的 `STAGE[k].color` 不用改就跟著主題走。*/
  const STAGE = (() => {
    const raw = {
      improving: { name: '改善', ck: 'cyan', sub: '還是比大盤弱，但動能轉強了', act: '資金剛開始進場，最早可以布局的一段' },
      leading: { name: '領先', ck: 'up', sub: '比大盤強，而且還在變強', act: '現在的主流，回檔找買點、不要追高' },
      weakening: { name: '轉弱', ck: 'amber', sub: '還是比大盤強，但動能在掉', act: '主流開始鬆動，手上有的先設好停利' },
      lagging: { name: '落後', ck: 'down', sub: '比大盤弱，而且還在變弱', act: '資金還在跑，別急著抄底' },
    };
    Object.keys(raw).forEach(k => Object.defineProperty(raw[k], 'color', {
      get() { return CH[raw[k].ck]; }, enumerable: true,
    }));
    return raw;
  })();
  const STAGE_ORDER = ['improving', 'leading', 'weakening', 'lagging'];
  const stageOf = (x, y) => (x >= 100 ? (y >= 100 ? 'leading' : 'weakening') : (y >= 100 ? 'improving' : 'lagging'));

  function rotRows(rrg, back) {
    return (rrg && rrg.points ? rrg.points : []).map(p => {
      const t = p.trail || [];
      const prev = t.length > back ? t[t.length - 1 - back] : null;
      const was = prev ? stageOf(prev[1], prev[2]) : null;
      return {
        gid: p.group_id, name: p.group_name, share: p.share || 0, trail: t,
        rs: p.x, mo: p.y, stage: p.quadrant || stageOf(p.x, p.y),
        was, moved: was && was !== (p.quadrant || stageOf(p.x, p.y)),
        dmo: prev ? p.y - prev[2] : null, drs: prev ? p.x - prev[1] : null,
      };
    }).sort((a, b) => b.share - a.share);
  }

  /* 一列族群：名稱、相對大盤強弱、動能方向、成交值佔比。
     `full`＝連**動能的數值**一起寫出來。只有象限展開面板用 full：
     總覽那塊 compact 看板的格子只有 12px 字、寬度不到 160px，多一段字就會換行疊起來
     （`_preview.py` 抓的正是這種重疊），而那裡本來就只需要「往上還是往下」。*/
  function rotItem(r, full) {
    const arrow = r.dmo == null ? '' : r.dmo > 0.15 ? '<span class="ar up">↑</span>' : r.dmo < -0.15 ? '<span class="ar dn">↓</span>' : '<span class="ar fl">→</span>';
    const mo = full && r.mo != null ? `　動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 1)}` : '';
    /* 換段徽章：「這 5 個交易日從哪一段換到哪一段」。
       2026-09-23 之前這件事另外有一整排常駐的 `#rotMove`，那一排已經移除，
       所以這顆徽章現在是換段資訊**唯一**的出口 —— 不要順手拿掉。*/
    const jump = full && r.moved && r.was
      ? `<span class="jmp" style="--c:${STAGE[r.stage].color}">${STAGE[r.was].name}→${STAGE[r.stage].name}</span>` : '';
    return `<li data-gid="${r.gid}"><span class="g">${fmt.esc(r.name)}</span>${arrow}${jump}
      <span class="m">強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 1)}${mo}　佔比 ${fmt.n(r.share, 1)}%</span></li>`;
  }

  /* ================================================================ 輪動階段併進輪動時鐘（Andy 2026-09-23）
     他的原話：「**下方的輪動階段需要與上方的輪動時鐘合併，如圖所示，輪動時鐘四周的四段
     需要有對應顏色 並且點擊後會出現目前該項線的股票強弱 占比，做完後下方的輪動階段即可移除**」，
     截圖用紅線把下方那四顆階段卡一顆一顆連到時鐘的四個象限標籤上。

     為什麼這樣併得起來：那四顆卡片和時鐘的四個象限**本來就是同一件事的兩種畫法** ——
     卡片是「這一段裡有誰」的清單，象限是「這一段在盤面上的哪個方向」。
     分成上下兩塊的代價是使用者要自己把「左上角那一片藍」和「下面第一張藍色卡片」對起來，
     那正是 Andy 說的「逼使用者自己做兩步推論」。

     做法：象限標籤改成**可以點的卡片**（吃 STAGE 的顏色，和卡片、排行、即時晶片同一份色），
     點下去在時鐘正下方展開那一段的族群清單（強弱／動能／佔比），再點一次收起來。
     顏色一律讀 `STAGE[k].color`（那是 getter，切淺色主題會自己換），**不在這裡另寫一套色碼**。*/
  let rotStageOpen = '';           // 目前展開哪一段（''＝都沒開）；同時只開一段

  /* 象限卡與展開面板共用的**同一份**名單。三件事一次套齊，順序不能換：
       ① 共用篩選（rotPickSet）—— 時鐘上只剩 3 個族群時，象限卡不可以還寫 12
       ② 「看哪一天」（rotFrame）—— 刷回 10 天前，階段要用那一天的座標重算
       ③ 盤中即時（RLV）—— 開著即時就用續算出來的那一點，和時鐘上的點同一個口徑
     ②③ 互斥（拖時間軸本來就會退出即時），所以這裡也只會套到其中一個。*/
  function rotStageAll() {
    const rows = rotRows(rotF3 && rotF3.rrg, ROT_BOARD_WIN);
    const pick = rotPickSet();
    const frame = Math.max(0, +rotFrame || 0);
    const liveOn = !!(RLV.on && !RLV.err && frame === 0 && Object.keys(RLV.pt).length);
    return rows.filter(r => !pick.size || pick.has(r.gid)).map(r => {
      if (liveOn) {
        const v = RLV.pt[r.gid];
        // 沒抓到報價的族群維持盤後位置（和時鐘上那些「沒有箭頭的點」一致，不要自己編一個數字）
        if (v) return { ...r, stage: v.stage, rs: v.fx, mo: v.fy, was: STAGE[v.stage0] ? v.stage0 : null, moved: v.stage0 !== v.stage, isLive: true };
        return r;
      }
      if (frame > 0) {
        const w = rotAtFrame(r.trail || [], frame);
        if (w) return { ...r, rs: w[1], mo: w[2], stage: stageOf(w[1], w[2]), was: null, moved: false };
      }
      return r;
    });
  }
  const rotStageCounts = () => {
    const c = {};
    rotStageAll().forEach(r => { c[r.stage] = (c[r.stage] || 0) + 1; });
    return c;
  };

  /* 四顆象限卡。位置用「極座標算回像素」而不是貼在容器四角 ——
     貼四角的話它們會撞到左右兩欄的族群名標籤（layoutRotLabels 把名字排在容器兩側），
     而象限中線（45°/135°/225°/315°）上的那個位置，本來就是 ECharts 原本畫象限標籤的地方，
     所以換成卡片之後**版面的佔用完全沒變**，`_preview.py` 的重疊風險也沒變大。
     ★ ECharts 原本那組 axisLabel 會被關掉（見 axisLabel.show），不然同一個名字會出現兩次。*/
  function rotQuadChips(el) {
    if (!el) return;
    let host = el.querySelector('.rotquads');
    if (!host) { host = document.createElement('div'); host.className = 'rotquads'; el.appendChild(host); }
    const W = el.clientWidth, H = el.clientHeight;
    if (!W || !H) { host.innerHTML = ''; return; }
    // 和 polar 的設定一致：center 50%/50%、radius 84%（百分比的基準是 min(寬,高)/2）
    const R = 0.84 * Math.min(W, H) / 2, cx = W / 2, cy = H / 2;
    const ANG = { leading: 45, improving: 135, lagging: 225, weakening: 315 };
    const cnt = rotStageCounts();
    host.innerHTML = STAGE_ORDER.map(k => {
      const a = ANG[k] * Math.PI / 180;
      const x = cx + Math.cos(a) * R * 1.02, y = cy - Math.sin(a) * R * 1.02;
      const on = rotStageOpen === k;
      return `<button type="button" class="rq${on ? ' on' : ''}" data-k="${k}" aria-expanded="${on ? 'true' : 'false'}"
        style="--c:${STAGE[k].color};left:${x.toFixed(1)}px;top:${y.toFixed(1)}px"
        title="${fmt.esc(STAGE[k].sub)}；${fmt.esc(STAGE[k].act)}。點一下在時鐘下面展開這一段有哪些族群"
        >${STAGE[k].name}<em>${cnt[k] || 0}</em></button>`;
    }).join('');
    $$('.rq', host).forEach(b => b.onclick = (ev) => { ev.stopPropagation(); rotStageToggle(b.dataset.k); });
  }

  /* 點象限：同時只展開一段（點另一段就換過去、點自己就收起來）。
     只改卡片的 class，**不重畫整張時鐘** —— 重畫會把還在跑的補間動畫從頭開始。

     ★ 2026-09-23（D2）：面板搬到時鐘**右邊**之後多了一件事要做。
       面板一開，`.rotstagerow` 就從「時鐘吃滿整欄」變成「時鐘 ＋ 300px 面板」，
       時鐘的容器寬度因此縮水。ECharts 那張圖有 ResizeObserver 會自己重畫，
       但**四顆象限卡是 HTML、位置是從 `el.clientWidth/clientHeight` 算出來的**
       （`rotQuadChips`），沒有人叫它就會停在舊寬度算出來的座標上 ——
       畫面上看到的是「四個象限名飄到盤外、其中兩個被卡片邊緣切掉」。
       `renderRotClock` 裡的 `relayout()` 已經處理過同一件事（它也重排族群名標籤），
       所以這裡直接借用容器上掛著的那一支，不要另外寫第二套。
       用 `requestAnimationFrame` 是因為 `box.hidden = false` 之後要等瀏覽器
       重排完一幀，`clientWidth` 才是新的值。*/
  function rotStageToggle(k) {
    rotStageOpen = rotStageOpen === k ? '' : k;
    $$('#rotClock .rotquads .rq').forEach(b => {
      const on = b.dataset.k === rotStageOpen;
      b.classList.toggle('on', on); b.setAttribute('aria-expanded', on ? 'true' : 'false');
    });
    renderStagePanel();
    requestAnimationFrame(() => {
      const el = $('#rotClock'); if (!el) return;
      try {
        const c = window.echarts && echarts.getInstanceByDom(el);
        if (c) c.resize();
      } catch (e) { /* 圖還沒建好就算了 */ }
      const f = el._rotRelayout;
      if (f) f(); else rotQuadChips(el);
    });
  }

  /* 展開面板。
     ★ 2026-09-23（Andy：「我點選領先，底下資訊是顯示在旁邊的」，紅框標的是時鐘右側那塊空白）：
       從「時鐘正下方」搬到**時鐘右邊**（`.rotstagerow` 的第二欄）。
       那塊空白本來就是時鐘畫不到的地方 —— 盤是圓的、欄是長方形的，
       所以面板放在那裡等於把一塊一直閒置的版面用起來，卡片也不會因此變高。
     · 仍然**不做浮層**：浮層會蓋住點與軌跡。
     · 仍然**不會蓋到「資金流向排行」**：它在 `.g21` 的第二欄，是另一個格子，
       面板只佔時鐘那一欄的右半邊（300px），排行那一欄一個像素都沒有被吃掉。
     · 窄畫面（≤1100px）`.rotstagerow` 退回單欄，面板掉到時鐘下面 —— 300px 的面板
       和一張讀得出來的時鐘在 800px 裡放不下，那是合理的退讓（CSS 在 index.html）。*/
  function renderStagePanel() {
    const box = $('#stagePanel'); if (!box) return;
    const k = rotStageOpen;
    if (!k || !STAGE[k]) { box.hidden = true; box.innerHTML = ''; return; }
    const s = STAGE[k];
    const list = rotStageAll().filter(r => r.stage === k);
    const live = list.some(r => r.isLive);
    box.hidden = false;
    box.dataset.k = k;
    box.innerHTML = `<div class="ph"><i style="background:${s.color}"></i>
        <b style="color:${s.color}">${s.name}</b><span class="n">${list.length} 個族群</span>
        <span class="muted">${s.sub}　·　<em>${s.act}</em></span>
        <span class="sp"></span><button type="button" class="btn small" data-x="1">收起 ✕</button></div>
      <div class="sd muted">依成交值佔比排序${live ? '　·　<b>⚡ 盤中即時</b>（沒抓到報價的族群維持盤後位置）' : ''}
        　·　點族群名稱會在右邊「資金流向排行」下面展開它的成分股，再點成分股就畫到時鐘上。</div>
      <ul class="ms">${list.map(r => rotItem(r, true)).join('')
        || '<li class="none">這一段目前沒有族群（可能是上面的篩選只留了別段的族群）</li>'}</ul>`;
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => rotStageToggle(k);
    /* 展開成分股走**既有**那條路（`drillOpen` → `#rankPanel`），和即時那排 `rlvchip`、
       排行長條、族群下拉完全一樣 —— 全站只有一套「點族群展開成分股」的邏輯。*/
    $$('li[data-gid]', box).forEach(li => li.onclick = () => {
      const gid = li.dataset.gid;
      const r = list.find(z => z.gid === gid);
      drillOpen(gid, (r && r.name) || L.gname[gid] || gid,
        r ? `${s.name}　·　強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 1)}　動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 1)}　佔比 ${fmt.n(r.share, 1)}%` : '',
        'rankPanel');
    });
  }

  /* ================================================================ 盤中即時輪動時鐘（RLV）
     Andy 2026-09-22：「輪動時鐘理論上也有辦法與資金去向做到即時對吧？
     **有成交價以及數量，就可以透過這方式計算每個族群的方向**，幫我也做一個即時功能像是圖一那樣。」
     「圖一」＝資金去向（桑基圖）那顆「即時」鈕，所以這裡刻意**照抄那一套操作習慣**：
     同一顆 `.pb.livebtn`、按下去切換、再按退回盤後、每分鐘一輪、拖時間軸就自動退出（互斥）。

     ── 這張圖在即時模式下回答的問題（一句話，畫面上也寫著）──
       **「今天盤中到現在，錢正在把哪個族群往前推、哪個往後拉？」**
       答案是那條「上一個收盤 → 現在」的線，而它**刻意畫成兩段**（見下面「持平基準」那一段）：
         灰虛線＝慣性（就算平盤也會走到那裡）　／　亮色箭頭＝今天的錢真正推出來的。

     ── 續算公式（後端 `pipeline/compute/rrg.py` 已經把 `live_state` 備好了）──
       ① rs_new   = rs_last × (1 + 族群今日報酬) ÷ (1 + 大盤今日報酬)
          rs 的定義就是「族群指數 ÷ 大盤指數」，多一天只是再乘一天的相對報酬，
          所以這一步**是精確的，不是近似**。
       ② α = 2 / (rs_smooth + 1)；rs_s_new = α×rs_new + (1−α)×rs_s_last     ← EMA 的遞迴式
       ③ x_new = 100 + 100 × ( rs_s_new ÷ mean(rs_s_tail 末 rs_base−1 筆 ＋ rs_s_new) − 1 )
          y_new = 100 + 100 × ( x_new ÷ x_{−mom_roc} − 1 )                  ← x_{−mom_roc} 取自 trail
     ★ 三個參數一律從 `live_params` 讀，**不准在這支 JS 裡寫死** ——
       `KInd` 與 `indicators.py` 就踩過「兩邊各寫一套、之後悄悄分岔」那個坑。

     ── 位移很小是事實，不准放大；而且位移裡有一半不是「今天的錢」 ──
       三組實測（2026-09-22，拿這一份 `live_state` 餵不同的假報價量的）：
         · 每一檔都 0%（族群報酬＝大盤報酬）→ 點**照樣會走**：中位 0.59 點、最大 1.42 點（18px）
         · 只有晶圓代工 +2%、其餘 0% → 總位移 0.50 點（6.3px），其中**今天真正貢獻的只有 0.35 點**（≈4.5px）
         · 同一張盤的 x 分布是 90.05 ～ 106.29（**16.2 點**）
       第一組是關鍵：**開盤什麼都還沒發生，箭頭就已經比「贏大盤 2%」還長。**
       所以只畫一條「收盤 → 現在」＝畫一張看起來有在動、但動的其實是指標自己的圖。
       （位移之所以這麼小，根因是 2026-09-20 為了「一天不該把點甩到盤緣」加的 EMA 平滑。
         那個修正是對的，代價就是即時位移很小 —— 不可以為了補償它而把位移放大。）

       所以處理方式是把真實的小位移**拆清楚、畫清楚**，不是誇大它：
         · 圖上：灰虛線（慣性）＋ 亮色箭頭（今天推的，針身用 `CH.ink`、外圈用階段色）
                 ＋ 端點漣漪（會動）＋ 跨象限就發光
         · 圖下：「今天被推得最多的族群」那一排，直接把**亮色那一段**的數字印出來，
                 而且每一顆都點得進成分股
       **不准為了讓它看起來有動而把位移乘上任何倍數。** 那是造假，不是設計。

     ── 兩條誠實界線（`rlvStamp()` 會把它們印在畫面上，不准省略）──
       1. **權重是估的、報酬是真的。** 成交值用「最新價 × 累積張數」估（即時端點沒有每檔的
          累積成交金額），但漲跌幅是真的（現價 vs 昨收）。所以**族群方向可信**，
          只有「誰的權重大一點」是估的。
       2. **即時的大盤是代理值。** 時鐘原本的大盤是「全市場成交值加權」，盤中只抓得到
          族群成分股那一批，所以要算出並顯示「這批涵蓋台股總成交值的百分之幾」
          （分母用 `window.Market3.marketAmt`，那是證交所的真實總額），不可以假裝它是全市場。

     ── 範圍（和資金去向那顆鈕同一個理由）──
       只算**人工族群**（43 個、291 檔 ＝ 3 個請求／分鐘）。
       `ind_*` 自動桶（ETF、〇〇・其他）光成分股就 1367 檔 ＝ 14 個請求／分鐘，做不到；
       所以它們一律留在盤後位置、不畫箭頭，並在狀態列講明。*/
  const RLV = {
    on: false, busy: false, at: 0, err: '',
    pt: {},              // gid → {x, y, x0, y0, dx, dy, ret, stage, stage0, n}
    mkt: null,           // 大盤今日報酬（小數；成交值加權，套在抓得到的全部個股上）
    uniAmt: 0,           // 這批個股的估算成交值加總（涵蓋率的分子）
    marketAmt: null,     // 證交所公布的台股總成交值（涵蓋率的分母，真實值）
    cover: null,         // 涵蓋率 %
    codes: 0, hit: 0, reqs: 0, skipped: 0, quoteAt: '',
    intraday: true, timer: null,
  };
  const RLV_BATCH = 100;               // 一個請求塞幾檔（沿用 live.js 實測的批次大小）
  const RLV_MS = 60 * 1000;            // 每分鐘一輪（和資金去向的即時同節奏）
  let rlvRedraw = () => {};            // renderFlow 會換成「卡片＋放大視窗一起重畫」

  /* 這一輪要抓哪些股票：所有**有 live_state 的人工族群**的成分股（去重）。
     自動桶（ind_*）直接跳過 —— 見上面「範圍」那一段。*/
  function rlvCodes(rrg) {
    const det = D.groups_detail || {};
    const codes = [], seen = new Set();
    const gids = [];
    ((rrg && rrg.points) || []).forEach(p => {
      if (isAutoBucket(p.group_id) || !p.live_state) return;
      gids.push(p.group_id);
      ((det[p.group_id] || {}).members || []).forEach(m => {
        const c = String(m.code); if (c && !seen.has(c)) { seen.add(c); codes.push(c); }
      });
    });
    return { codes, gids };
  }

  /* 把報價續算成「現在這一刻」的時鐘座標。
     ★ 族群報酬用**成交值加權、而且做 1/n 拆分** —— 後端 `compute/flow.py` 的族群 chg_pct
       就是這樣算的（`_chgw / _wsum`，權重是 turnover × 1/n）。兩邊口徑一定要一樣，
       不然盤中畫的點和收盤後重算出來的點會對不起來。
     ★ 大盤報酬**不做 1/n 拆分**：`rrg.market_index()` 是逐檔成交值加權，
       那張表裡一檔股票就是一列，沒有「掛在幾個族群」這回事。*/
  function rlvCompute(rrg, q) {
    const P = rrg && rrg.live_params;
    if (!P || !P.rs_smooth || !P.rs_base || !P.mom_roc) {
      throw new Error('這份資料還沒有即時續算參數（rrg.live_params），請等下一輪盤後管線');
    }
    const det = D.groups_detail || {};
    const w = sklWeights();                        // 和資金去向共用同一份 1/n 權重
    const stv = {}, chg = {};
    let uni = 0, at = '', hit = 0;
    Object.keys(q).forEach(c => {
      const x = q[c];
      if (!x || x.price == null || x.volume == null) return;
      const v = x.price * x.volume * 1000;         // ★ 估算：端點沒有每檔的累積成交金額
      if (!(v > 0)) return;
      stv[c] = v; uni += v; hit++;
      if (x.chgPct != null) chg[c] = x.chgPct / 100;
      if (x.time && x.time > at) at = x.time;
    });
    let mw = 0, mc = 0;
    Object.keys(stv).forEach(c => { if (chg[c] == null) return; mw += stv[c]; mc += chg[c] * stv[c]; });
    if (!(mw > 0)) throw new Error('報價回來了，但沒有一檔同時有價、量、漲跌幅，算不出大盤報酬');
    const mkt = mc / mw;                           // 大盤今日報酬（代理值，見誠實界線 2）
    const alpha = 2 / (P.rs_smooth + 1);
    const pt = {};
    let skipped = 0;
    ((rrg && rrg.points) || []).forEach(p => {
      const ls = p.live_state;
      if (!ls || ls.rs == null || ls.rs_s == null || !(ls.rs_s_tail || []).length) { skipped++; return; }
      if (isAutoBucket(p.group_id)) { skipped++; return; }
      const t = p.trail || [];
      if (t.length <= P.mom_roc) { skipped++; return; }   // 軌跡不夠長就算不出 y（ROC 的分母）
      let gw = 0, gc = 0, n = 0;
      ((det[p.group_id] || {}).members || []).forEach(m => {
        const c = String(m.code);
        if (stv[c] == null || chg[c] == null) return;
        const ww = stv[c] / Math.max(1, w[c] || 1);
        gw += ww; gc += chg[c] * ww; n++;
      });
      if (!(gw > 0)) { skipped++; return; }              // 這個族群一檔都沒抓到 → 維持盤後位置
      const gr = gc / gw;                                 // 族群今日報酬（成交值加權）
      const xPrev = t[t.length - 1 - P.mom_roc][1];
      if (!(xPrev > 0)) { skipped++; return; }
      /* 續算一步。`ret` 帶進來的相對報酬只影響第 ① 步，其餘完全一樣，
         所以把 ①②③ 包成一支，等一下拿它算兩次（真實報酬、以及「持平」）。*/
      const step = (ret) => {
        const rsNew = ls.rs * (1 + ret) / (1 + mkt);        // ①（精確）
        const rsS = alpha * rsNew + (1 - alpha) * ls.rs_s;  // ②
        const tail = ls.rs_s_tail.slice(-(P.rs_base - 1)).concat([rsS]);
        let s = 0; tail.forEach(v => { s += v; });
        const base = s / tail.length;
        if (!(base > 0)) return null;
        const xx = 100 + 100 * (rsS / base - 1);            // ③
        return { x: xx, y: 100 + 100 * (xx / xPrev - 1) };
      };
      const now = step(gr);
      /* ★★ 「持平基準」——**這一段是這張圖能不能被讀懂的關鍵，不要拿掉。**
         實測（2026-09-22，每一檔都餵 0% 的一輪）：就算族群報酬完全等於大盤，
         續算出來的點還是會離收盤那一點 **中位數 0.59 點、最大 1.42 點（18px）**，
         而「贏大盤 2%」貢獻的只有 **0.35 點（4.5px）**。
         也就是說：如果只畫一條「收盤 → 現在」的箭頭，**箭頭裡有一大半是指標自己的慣性**
         （EMA 只讓當天的相對報酬進來 α=2/11≈18%，而 40 日基準線的窗口每天會往前滾一格），
         盤一開、什麼都還沒發生，箭頭就已經很長了 —— 那會讓人以為「錢在動」，
         但那不是錢在動，是指標在動。那就是一張騙人的圖。
         所以把它拆成兩段：
           收盤 → 持平基準　＝ 慣性（就算今天平盤也會走到那裡）→ 畫成灰色虛線
           持平基準 → 現在　＝ **今天的成交價與成交量真正推出來的那一段** → 畫成亮色實線＋箭頭
         「走得最多的族群」那一排排序與數字用的也是**後面那一段**。*/
      const flat = step(mkt);
      if (!now || !flat || !isFinite(now.x) || !isFinite(now.y)) { skipped++; return; }
      const x = now.x, y = now.y, x0 = p.x, y0 = p.y;
      pt[p.group_id] = { x, y, x0, y0, fx: flat.x, fy: flat.y,
        dx: x - x0, dy: y - y0,                 // 總位移（收盤 → 現在）
        tdx: x - flat.x, tdy: y - flat.y,       // 今天真正推出來的那一段（持平基準 → 現在）
        ret: gr, n, stage: stageOf(x, y), stage0: p.quadrant || stageOf(x0, y0) };
    });
    if (!Object.keys(pt).length) throw new Error('報價回來了，但沒有一個族群算得出即時座標');
    return { pt, mkt, uni, at, hit, skipped };
  }

  async function rlvFetch() {
    if (!window.Live || !window.Live.fetchQuotes) throw new Error('即時報價層還沒載入（live.js）');
    const rrg = rotF3 && rotF3.rrg;
    if (!rrg || !(rrg.points || []).length) throw new Error('輪動資料還沒載入');
    const codes = rlvCodes(rrg).codes;
    if (!codes.length) throw new Error('這張圖上的族群還沒有成分股資料，抓不了即時');
    const q = {};
    let reqs = 0;
    for (let i = 0; i < codes.length; i += RLV_BATCH) {
      Object.assign(q, await window.Live.fetchQuotes(codes.slice(i, i + RLV_BATCH)));
      reqs++;
    }
    const r = rlvCompute(rrg, q);
    /* 涵蓋率的分母：Market3 有多久沒更新就自己叫它一次（和資金去向那邊同一套理由 ——
       使用者開過「總覽」的話它本來就每分鐘在跑，零額外請求）。
       抓不到就把涵蓋率留成 null，狀態列會誠實寫「這一輪沒取到」，
       **不要**拿估算值去湊一個看起來像真的百分比。*/
    try {
      const M = window.Market3;
      if (M) {
        if (!M.lastAt || Date.now() - M.lastAt > 90 * 1000) await M.refresh(true);
        RLV.marketAmt = M.marketAmt;
      }
    } catch (e) { RLV.marketAmt = null; }
    RLV.pt = r.pt; RLV.mkt = r.mkt; RLV.uniAmt = r.uni;
    RLV.cover = RLV.marketAmt ? r.uni / RLV.marketAmt * 100 : null;
    RLV.codes = codes.length; RLV.hit = r.hit; RLV.reqs = reqs; RLV.skipped = r.skipped;
    RLV.quoteAt = r.at; RLV.at = Date.now(); RLV.err = '';
  }

  /* 走得最多的前 n 個族群。排序用「位移長度」而不是 Δ強弱 ——
     往「動能」那個方向走一樣是在走，只看單軸會漏掉剛轉向的那幾個。

     ★ 只列**現在真的畫在盤上**的那幾個（`rlvShown` 由 renderRotClock 填）。
       時鐘最多畫 16 顆點（還可能被篩選再砍），但 `RLV.pt` 有 43 個族群 ——
       列一個盤上根本找不到箭頭的名字，使用者會去圖上找那條線、然後找不到。
       這一排是那些箭頭的**讀數**，不是另一份排行榜。*/
  let rlvShown = null;                 // Set(gid)：這一輪畫在盤上的族群
  function rlvTop(n) {
    const keys = Object.keys(RLV.pt).filter(g => !rlvShown || !rlvShown.size || rlvShown.has(g));
    return keys.map(gid => {
      const v = RLV.pt[gid];
      return { gid, name: (rotGroupMeta[gid] || {}).name || L.gname[gid] || gid,
        // ★ 排序與顯示都用「今天推出來的那一段」（tdx/tdy），不是總位移 —— 理由見 rlvCompute 的註解
        tdx: +v.tdx.toFixed(3), tdy: +v.tdy.toFixed(3),
        dx: +v.dx.toFixed(3), dy: +v.dy.toFixed(3), ret: +(v.ret * 100).toFixed(2),
        jump: v.stage0 !== v.stage, stage: v.stage, stage0: v.stage0,
        d: +Math.hypot(v.tdx, v.tdy).toFixed(4) };
    }).sort((a, b) => b.d - a.d).slice(0, n || 6);
  }

  /* 狀態列。★ 誠實標示全部寫在這裡、不散在圖上 —— 圖上塞不下，
     而這幾句話少一句整張圖就會被讀錯。*/
  function rlvStamp() {
    const btn = $('#rotLiveBtn');
    if (btn) { btn.classList.toggle('on', RLV.on); btn.setAttribute('aria-pressed', RLV.on ? 'true' : 'false'); }
    const el = $('#rotLive');
    if (!el) return;
    if (!RLV.on) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    if (RLV.busy && !RLV.at) { el.innerHTML = '<b>即時</b>　抓取中…'; return; }
    if (RLV.err) {
      el.innerHTML = `<b class="bad">即時抓不到報價</b>　${fmt.esc(RLV.err)}`
        + '　·　時鐘上畫的仍然是<b>盤後</b>那一份資料（圖沒有變空白）'
        + '　<button type="button" class="btn small" id="rotLiveBack">一鍵退回盤後</button>';
      const b = $('#rotLiveBack'); if (b) b.onclick = () => rlvOff();
      return;
    }
    /* 涵蓋率：算式細節放進 `title`，畫面上只留百分比。
       2026-09-22 在 390px 量過：整段狀態列寫滿會吃掉 330px（Andy 2026-09-21 才剛把
       圖下方那段 622 字的常駐說明砍掉，理由就是它在手機上比半個螢幕還長）——
       所以這裡的原則是「不看到就會把圖讀錯的留在畫面上，其餘進 title 或『怎麼看 ?』」。*/
    const cov = RLV.cover != null
      ? `<b>涵蓋率 ${fmt.n(RLV.cover, 1)}%</b>`
        /* 分子是估的、分母只有上市，所以**真的有可能超過 100%**。
           與其把它夾在 100% 讓人以為「剛好全涵蓋」，不如照實印出來並講清楚為什麼。*/
        + (RLV.cover > 100 ? '<b class="warn">（⚠ 超過 100%：估的分子已經大於上市總額 ——'
          + '這批含上櫃，分母只有上市）</b>' : '')
      : '<b>涵蓋率：這一輪沒取到</b>';
    const covTip = RLV.cover != null
      ? `這批 ${RLV.hit} 檔的估算成交值 ${fmt.yi(RLV.uniAmt)} ÷ 證交所公布的台股總成交值 ${fmt.yi(RLV.marketAmt)}`
      : '證交所的總成交值這一輪抓不到，所以算不出涵蓋率';
    const chips = rlvTop(6).map(r => `<button type="button" class="rlvchip${r.jump ? ' jump' : ''}" data-g="${r.gid}" style="--c:${STAGE[r.stage].color}" title="族群報酬 ${fmt.pct(r.ret, 2)}（大盤代理值 ${fmt.pct((RLV.mkt || 0) * 100, 2)}）；含慣性的總位移 強弱 ${fmt.n(r.dx, 2)} / 動能 ${fmt.n(r.dy, 2)}。點一下在下面展開這個族群的成分股"><span class="g">${fmt.esc(r.name)}</span><span class="d">強弱 ${r.tdx >= 0 ? '+' : ''}${fmt.n(r.tdx, 2)}　動能 ${r.tdy >= 0 ? '+' : ''}${fmt.n(r.tdy, 2)}</span>${r.jump ? `<span class="j">${STAGE[r.stage0].name}→${STAGE[r.stage].name}</span>` : ''}</button>`).join('');
    el.innerHTML = (RLV.intraday
      ? `<b class="live">即時</b>　報價 ${fmt.esc(RLV.quoteAt || '—')}　每分鐘更新`
      : '<b class="warn">現在不是盤中</b>（現貨 09:00–13:30）　下面畫的是<b>最後一次報價的快照</b>，不是盤中變化')
      + `　·　大盤（代理值）${fmt.pct(RLV.mkt * 100, 2)}　·　<span title="${fmt.esc(covTip)}">${cov}</span>`
      /* 底下兩句是**不准省略**的誠實標示，第三句是「怎麼讀這條線」。
         長版（含實測數字與原理）在「怎麼看 ?」裡。這裡只留「不看到就會把圖讀錯」的那幾句。*/
      + '<br>· <b>線分兩段</b>：<span class="muted">灰虛線＝<b>慣性</b>（40 日基準線的窗口每天往前滾一格，'
      + '<b>平盤也會走</b>，實測中位 0.59 點）</span>；<b>亮色箭頭＝今天真正推出來的</b>'
      + '（贏大盤 2% 只有 0.35 點、4~5 px，<b>我們沒有放大它</b>）。下面那排數字就是亮色那一段。'
      + '<br>· <b>權重是估的、報酬是真的</b>：成交值用「價 × 量」<b>估算</b>（端點沒有每檔的累積成交金額），'
      + '漲跌幅是<b>真的</b>（現價 vs 昨收）。'
      + '<b>即時的大盤是代理值</b>：原本是<b>全市場</b>成交值加權，盤中只抓得到這批，'
      + `所以 x 軸的「相對大盤」是拿這批算的。　·　${RLV.skipped} 個族群與個股點維持盤後`
      + `　·　${RLV.reqs} 個請求 / ${RLV.codes} 檔`
      + (chips ? '<div class="rlvmov"><span class="t">今天被推得最多的族群'
        + `（盤上這 ${rlvShown ? rlvShown.size : 0} 個；數字＝<b>亮色箭頭那一段</b>，不含慣性）</span>${chips}</div>` : '');
    $$('.rlvchip', el).forEach(b => b.onclick = () => {
      const gid = b.dataset.g;
      drillOpen(gid, (rotGroupMeta[gid] || {}).name || L.gname[gid] || gid, '', 'rankPanel');
    });
  }

  async function rlvTick() {
    if (!RLV.on || RLV.busy) return;
    /* 換到站內別的分頁時容器還在 DOM、只是被藏起來（offsetParent 是 null）。
       這時候不要打報價 —— 使用者根本沒在看這張圖，每分鐘 3 個請求純浪費。*/
    { const el = $('#rotClock'); if (el && el.offsetParent === null) return; }
    RLV.busy = true; RLV.intraday = !window.Live || window.Live.isIntraday();
    rlvStamp();
    try { await rlvFetch(); }
    catch (e) { RLV.err = String((e && e.message) || e).slice(0, 90); RLV.pt = {}; }
    finally {
      RLV.busy = false;
      if (RLV.on) rlvRedraw();
      rlvStamp();
    }
  }

  /* 退出即時。`redraw=false` 給「使用者自己拖時間軸」用 ——
     那一路本來就會接著重畫一次，這裡再畫一次等於同一幀畫兩張圖。*/
  function rlvOff(redraw) {
    if (RLV.timer) { clearInterval(RLV.timer); RLV.timer = null; }
    RLV.on = false; RLV.pt = {}; RLV.err = ''; RLV.cover = null; RLV.mkt = null;
    rlvStamp();
    if (redraw !== false) rlvRedraw();
  }

  function rlvToggle() {
    if (RLV.on) return rlvOff();
    if (RLV.timer) { clearInterval(RLV.timer); RLV.timer = null; }
    RLV.on = true;
    stopAllPlay();                     // 即時和「往回播」是互斥的兩件事，同時跑只會互相蓋
    /* 即時只在「看最新那一天」成立（續算是接在**最後一個收盤**後面的）。
       所以切進來時先把時間軸推回 0；不推的話使用者會看到「我按了即時但點沒動」——
       因為畫的是 20 天前那一天，而那一天沒有即時可言。*/
    if (rotFrame !== 0) {
      rotFrame = 0; flowState.back = 0;
      if (rotBackBar) { try { rotBackBar.set(0); } catch (e) { /* 忽略 */ } }
    }
    RLV.err = ''; RLV.at = 0; RLV.pt = {};
    RLV.intraday = !window.Live || window.Live.isIntraday();
    rlvStamp();
    rlvTick();
    RLV.timer = setInterval(() => { if (!document.hidden) rlvTick(); }, RLV_MS);
  }

  /* 「即時」鈕掛在時鐘那排時間軸上（`#rotBack`＝playBar 的容器，`rangeBar` 會給它 `.rbar`），
     和資金去向那顆**同一顆樣式、同一套行為**。每次 playBar 重建都會把容器的 innerHTML
     換掉，所以這支要在 playBar 之後再叫一次，而且要把「亮起來」的樣子補回去 ——
     不然畫的明明是即時資料、鈕看起來卻是關的。*/
  function rlvMountBtn() {
    const box = $('#rotBack'); if (!box) return;
    if (!$('#rotLiveBtn')) {
      box.classList.add('rbar');
      const b = document.createElement('button');
      b.type = 'button'; b.id = 'rotLiveBtn'; b.className = 'pb livebtn';
      b.textContent = '即時';
      b.title = '切到盤中即時：用當下的成交價與成交量續算每個族群的位置，每分鐘更新；拖時間軸會自動退出';
      b.setAttribute('aria-pressed', 'false');
      b.onclick = rlvToggle;
      box.appendChild(b);
    }
    /* 狀態列本體（`#rotLive`）也在這裡補 —— 它跟著時間軸走，
       不寫死在 index.html 是因為它只有資金流向頁的那張卡用得到。*/
    if (!$('#rotLive')) {
      const row = box.closest('.rottime');
      if (row && row.parentNode) {
        const n = document.createElement('div');
        n.id = 'rotLive'; n.className = 'note livenote rotlivenote'; n.hidden = true;
        row.parentNode.insertBefore(n, row.nextSibling);
      }
    }
    rlvStamp();
  }

  /* 資金輪動時鐘：Andy 看不懂 RRG 的 XY 散布圖（「完全看不懂這張圖」），
     但「時鐘」人人都懂 —— 圓盤切成四段，資金照順時針一段一段跑：
       落後 → 改善 → 領先 → 轉弱 → 回到落後。
     每個族群是一顆點，點在哪一段就代表現在在哪個階段；
     尾巴是牠這幾天走過的路，看得出來是正在往前跑還是倒退。
     離圓心越遠＝和大盤的差距越大，圓心附近＝跟大盤差不多。 */
  const CLOCK_SECTOR = [   // 角度由 0° 起算、逆時針；和 stageOf 的四象限對齊
    { from: 0, to: 90, k: 'leading' },      // 右上：比大盤強且還在變強
    { from: 90, to: 180, k: 'improving' },  // 左上：還弱但動能轉強
    { from: 180, to: 270, k: 'lagging' },   // 左下：又弱又還在變弱
    { from: 270, to: 360, k: 'weakening' }, // 右下：還強但動能在掉
  ];
  const CLOCK_MAXR = 1.25;
  /* 盤緣（外圈虛線）**外面**留的那條緩衝帶，單位是 CLOCK_MAXR 的倍數。
     回放到「比今天更極端」的日子時，那些族群落在這裡而不是被硬夾在盤緣上
     （見 renderRotClock 的 pos()）。radiusAxis 的 max 也用同一個數，兩邊一定要一致。
     0.18 是量出來的：緩衝帶要在畫面上寬到看得出誰在外面誰更外面 ——
     1440px 時盤面半徑約 190px，0.18 ≈ 34px，夠分得開三四顆點；
     再大就是拿整張盤面的尺寸去換一條大部分時候空著的帶子。*/
  const CLOCK_TAIL = 0.18;
  /* ★ 2026-09-20（Andy：「每天的移動都需要平均速率，絲滑呈現，而非段點段點式移動」）
     這兩個數字是同一件事的兩半，**必須相等**，改一個就要改另一個：
       ROT_ANIM_MS  ECharts 把大圈從「昨天的位置」補間到「今天的位置」要花多久（linear）
       播放的間隔    playBar 多久推進一天
     以前是 620 / 820 —— 每一天走完之後有 200ms 站在原地不動，
     那個空檔就是他說的「段點段點式移動」。改成兩邊都 420 之後首尾相接：
     一天固定走 420ms（60fps 下約 25 幀），速率完全一致，中間沒有停頓。
     順帶一提這樣整段 30 天播完是 12.6 秒，比舊的 24.6 秒還快。 */
  const ROT_ANIM_MS = 420;
  const LBL_FS = 11.5;                 // 標籤字級；排版與驗收都用同一個值
  /* 這一輪排好的標籤位置：`rotLbl[圖表 id][scatter 的 dataIndex]`。
     labelLayout 是每個標籤各呼叫一次的，拿不到「全部標籤」，
     所以先自己算好放這裡，labelLayout 只負責查表。
     ★ 2026-09-20（E2）：本來是一個共用物件，**卡片時鐘與放大時鐘會互相覆蓋** ——
       放大視窗開著的時候，卡片那張圖的 ResizeObserver 只要被觸發一次，
       就會把放大視窗排好的標籤位置整個洗掉（名字停在別張圖的像素座標上）。
       兩張圖是兩套座標，所以狀態也要分開，以圖表 id 當 key。*/
  const rotLbl = {};
  // N3：上一次畫的是哪一組族群 —— 一樣就用 merge（點會自己走過去），不一樣才 notMerge
  // （同上：以圖表 id 當 key，兩張圖不可以共用一個指紋，否則會互相逼對方 notMerge）
  const rotLastShape = {};

  /* 左右兩欄＋引線的排版（和 3D 剖析圖 E1 同一套）。
     先把每個點用 convertToPixel 轉成像素座標，依 x 分左右欄；
     欄內由上而下擺，擠不下就往下推，推到底再由下往上收，最後夾在畫布內。
     回傳 {dataIndex: {side, x, y, px, py, rect}}；rect 是給驗收量重疊用的。*/
  function layoutRotLabels(c, el, pts) {
    const out = {};
    if (!c || !el) return out;
    const W = el.clientWidth || 0, H = el.clientHeight || 0;
    if (!W || !H) return out;
    const si = (c.getOption().series || []).findIndex(x => x.type === 'scatter');
    if (si < 0) return out;
    const LH = LBL_FS + 5.5;                 // 一行的高度（含行距）
    const PAD = 6;
    const wide = (name) => Math.min(W * 0.34, 10 + String(name).length * (LBL_FS * 1.02));
    const px = [];
    pts.forEach((r, i) => {
      let q;
      try { q = c.convertToPixel({ seriesIndex: si }, [r.p[0], r.p[1]]); }
      catch (e) { q = null; }
      if (!q || !isFinite(q[0]) || !isFinite(q[1])) return;
      px.push({ i, x: q[0], y: q[1], name: r.lbl || r.name });
    });
    const cx = W / 2;
    const cols = { left: px.filter(p => p.x < cx), right: px.filter(p => p.x >= cx) };
    Object.keys(cols).forEach(side => {
      const arr = cols[side].sort((a, b) => a.y - b.y);
      let prev = -Infinity;
      arr.forEach(p => { p.ly = Math.max(p.y, prev + LH); prev = p.ly; });     // 由上而下擺
      let next = H - PAD - LH / 2;
      for (let k = arr.length - 1; k >= 0; k--) { arr[k].ly = Math.min(arr[k].ly, next); next = arr[k].ly - LH; }
      arr.forEach(p => { p.ly = Math.max(PAD + LH / 2, Math.min(H - PAD - LH / 2, p.ly)); });  // 夾在畫布內
      /* ★ 對齊方向不能反。
         左欄的錨點在左緣，文字要**往右**長（align:left）；右欄錨點在右緣，往左長（align:right）。
         寫反的話左欄會從 x=6 往左長成負座標、右欄會超出畫布右緣 ——
         2026-09-18 第一次跑 _uitest 就是被「每個族群名稱都在畫布內」這條抓到的。*/
      const lx = side === 'left' ? PAD : W - PAD;
      arr.forEach(p => {
        const w = wide(p.name);
        out[p.i] = { side, x: lx, y: p.ly, px: p.x, py: p.y,
          rect: { x: side === 'left' ? lx : lx - w, y: p.ly - LH / 2, w, h: LH, name: p.name } };
      });
    });
    return out;
  }

  /* opts（2026-09-18 Andy 圖二、2026-09-20 Andy A4／E1～E3）：
       pick   Set|null  只看這幾個族群（篩選）；null＝全部
       frame  int       **看哪一天**：大圈移到「第 frame 天前」那一天的座標；0＝今天
       span   int       軌跡要畫幾天（預設＝back）
       trail  bool      軌跡開關（false＝線還在但資料清空，A4 第 7 條「軌跡可以開啟關閉」）
       chips  bool      要不要在圖下方掛族群晶片列（**只有卡片上的時鐘要**）
       expose bool      要不要把這張圖的量測值寫到 window.App（驗收用；只有卡片那張寫）

     ★ chips / expose 是旗標不是 id 比對（E2）：放大視窗的容器 id 是 `zoomBody`，
       以前那段 `if (!compact) groupChips(...)` 對它也成立，於是放大視窗裡被塞進一排
       綁在**卡片** rankSel 上的族群晶片 —— 實測 #zoomBody 704×756、那排晶片 704×748，
       放大視窗一半的版面被吃掉，而且按下去對放大的那張圖完全沒有作用。
       用 id 字串擋只是把同一個坑換個位置埋，所以改成由呼叫端明講要不要。

     ★ A4 第 7 條把這支拉Bar 的語意從「畫多長」換成「看哪一天」之後，
       正規化的尺度**一定要固定**，不能再用「當下這一幀的最大偏離量」。
       理由：尺度一變，所有族群的座標會同時被重新縮放 ——
       使用者看到的是「我只是往前拉一天，整盤東西全部跳了一下」，
       那正是 Andy 講的「一天的差距在圖上卻是各種歪曲」的另一半。
       所以尺度改成用**整段軌跡的最大偏離量**算一次，刷動期間完全不動。*/
  /* 回放：把每個族群的位置換成 trail 裡「frame 天前」那一筆。
     trail 是 [日期, rs_ratio, rs_mom] 由舊到新，所以第 k 天前＝倒數第 k+1 筆。

     ★ 2026-09-20：frame 允許**小數**。拖曳與播放時 ECharts 會自己在相鄰兩天之間補間，
       但「軌跡要畫到哪裡」必須跟大圈站在同一個位置上，所以兩邊共用這一支取值，
       小數就在相鄰兩筆之間線性內插。回傳的第 4 個值是「由舊到新的索引」，
       軌跡那一段要用它決定畫到哪裡為止。
     ★ 2026-09-23 從 renderRotClock 裡提到模組層：輪動階段看板併進時鐘之後，
       象限卡的計數與展開面板也要跟著「看哪一天」走 —— 兩邊各寫一份取值公式，
       刷時間軸時就會出現「點已經走到領先、象限卡還寫著落後」。*/
  const rotAtFrame = (t, f) => {
    const n = t.length; if (!n) return null;
    const idx = Math.max(0, Math.min(n - 1, n - 1 - f));
    const i0 = Math.floor(idx), i1 = Math.min(n - 1, i0 + 1), u = idx - i0;
    const a = t[i0], b = t[i1];
    return [a[0], a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, idx];
  };

  function renderRotClock(rows, back, id, compact, opts) {
    opts = opts || {};
    const el = $('#' + id); if (!el) return;
    const cap = compact ? 10 : 16;
    let top0 = rows.slice(0, cap);                       // rotRows 已照成交值佔比排序
    if (opts.pick && opts.pick.size) {
      const picked = rows.filter(r => opts.pick.has(r.gid));
      if (picked.length) top0 = picked;
    }
    /* 階段三：把使用者在成分股清單裡點開的個股接到同一份 rows 上。
       形狀和族群完全一樣，所以底下的回放、軌跡、正規化尺度一行都不用改。
       ★ 總覽的小圖（compact）不接：它只有 300px 高，十顆族群點已經是上限。
       ★ 尺度（sx/sy）是從 `scope` 算的，而 `scope` 就是這一行之後的 top0 ——
         也就是說**個股會一起參與正規化**。不這樣做的話，偏離比族群大的個股
         會被夾在盤緣（clamp），看起來每一檔都「跟大盤差最多」，那是假的。*/
    const stkRows = compact ? [] : drillRotRows();
    if (stkRows.length) top0 = top0.concat(stkRows);
    const atFrame = rotAtFrame;      // 模組層那一支（象限卡與展開面板也吃同一條公式）
    const scope = top0;                       // 尺度與軌跡都用「還沒被 frame 換掉」的原始資料
    const frame = Math.max(0, +opts.frame || 0);
    let frameDate = null;
    if (frame > 0) {
      top0 = top0.map(r => {
        const w = atFrame(r.trail || [], frame);
        if (!w) return r;
        frameDate = w[0];
        // 階段要跟著當天的座標重算，否則回放時點還在動、顏色卻停在「今天的階段」
        return { ...r, rs: w[1], mo: w[2], stage: stageOf(w[1], w[2]), was: null, moved: false };
      });
    }
    /* 盤中即時（RLV）：把族群的位置換成「用當下報價續算出來的那一點」。
       ★ 只在 frame === 0（看最新那一天）成立 —— 續算是接在最後一個收盤後面的，
         而拖時間軸本來就會自動退出即時，所以這裡只是再擋一次。
       ★ `scope`（正規化的那把尺）**刻意仍然是收盤那一份**：
         尺一起跟著動的話，切到即時會看到「整盤東西全部縮放了一下」——
         那正是 Andy 2026-09-20 講的「一天的差距在圖上卻是各種歪曲」。
         尺不動，使用者看到的就只有「點往某個方向挪了一小段」，那才是事實。
       ★ 個股點（isStock）不套用：後端沒有給個股 live_state，
         硬用族群的參數去續算個股等於自己編一個數字。狀態列會講明它們停在盤後位置。*/
    /* `!compact`：總覽頁那張小時鐘**不套用即時**。它旁邊沒有狀態列、沒有那排數字，
       也沒有「即時」鈕 —— 點默默跑到另一個位置，使用者無從得知那是即時還是盤後。
       誠實標示和圖是一組的，標示放不下就不要畫那張圖。*/
    const liveOn = !!(RLV.on && !RLV.err && !compact && frame === 0 && Object.keys(RLV.pt).length);
    if (liveOn) {
      top0 = top0.map(r => {
        const v = RLV.pt[r.gid];
        if (!v || r.isStock) return r;
        /* `moved` 沿用既有那條「換段就發光」的路（shadowBlur）——
           即時模式下「換段」的意思換成「盤中跨過象限」，語意一致，不必再長一套樣式。*/
        return { ...r, rs: v.x, mo: v.y, stage: stageOf(v.x, v.y), live: v,
          was: null, moved: v.stage0 !== stageOf(v.x, v.y) };
      });
    }
    if (!top0.length) return empty(id, '輪動時鐘需要至少 20 個交易日');
    /* 兩個軸的尺度差很多：相對強弱常常差好幾點，動能只差零點幾。
       直接拿原始值算角度，所有族群會擠在水平線上（＝兩段的交界），根本看不出在哪一段。
       所以各自除以自己的最大偏離量再算角度 —— 正負號沒動，四段的歸屬完全不變，
       但分佈攤得開，一眼就看得出誰在哪一段、離中心多遠。
       ★ 分母一律取**今天**那一天的最大偏離量（`scope` 是還沒被 frame 換掉的原始資料，
         所以它的 rs/mo 永遠是今天的值）—— 刷動時間軸時這個分母完全不動。
         ★★ 不要改成「整段軌跡的最大偏離量」。2026-09-20 試過，量出來的後果是：
            這一份資料的動能軸，今天的散佈只有 8.5、過去 30 天卻到 20.9，
            改成取整段之後 y 軸被壓掉 2.6 倍，靠圓心那一圈的族群全部擠在一起 ——
            驗收「點時鐘上的第一顆點會進它的族群頁」直接點到隔壁的族群
            （晶圓代工 → 金融），也就是說**使用者真的點不到自己要的那一顆**。
            代價是回放到很久以前時，少數點會被夾在盤緣（實測 9.5%，
            和改動前完全一樣 —— 舊版本來就是用今天的尺度畫尾巴的）。*/
    let sx = 1e-6, sy = 1e-6;
    scope.forEach(r => {
      sx = Math.max(sx, Math.abs((r.rs || 100) - 100));
      sy = Math.max(sy, Math.abs((r.mo || 100) - 100));
    });
    /* ★ 2026-09-21（Andy：「部分族群一直貼在圓圈邊緣上，是否數值過大 導致一直維持最大值」）。

       ── 我先照「理論上限」的假設改了一版，量完發現那不是主因，記在這裡免得有人改回去 ──
       原本半徑是 `√(dx²+dy²)` 直接夾在 `CLOCK_MAXR`(1.25)，而 dx、dy 各自上限是 1，
       所以理論上限是 √2≈1.414。但這份資料**今天**的最大值只有 1.288 ——
       換句話說「理論上會超過」在實務上只讓 1 個族群多跨過門檻，改了幾乎沒差
       （實測：frame 0 時舊尺 1 個貼邊、新尺還是 1 個）。

       ── 真正的根因（量出來的）──
       尺是**凍結在今天**的（DECISIONS 已拍板：改用整段軌跡的最大值會把靠圓心那圈全部
       擠在一起，使用者點不到自己要的那顆點），而過去 30 天的偏離可以遠大於今天：
         今天最大偏離 sr = 1.288，整段 30 天的最大偏離 srAll = 2.476（**1.92 倍**）。
       於是硬夾的後果是：
         被動元件 MLCC　31 天裡 **31 天**都被夾在盤緣　矽晶圓 28/31　矽光子與 CPO 8/31
       —— 播放整段從頭到尾，這兩顆點的半徑動也不動。那就是他說的「一直維持最大值」。

       ── 修法：盤緣外留一條**壓縮過的緩衝帶**，不要硬夾 ──
         · `u ≤ 1`（今天的尺度內）：完全線性，和以前一模一樣 ——
           兩圈虛線「今天最大偏離的一半 / 今天偏離最大的那個族群」的意思一字不變，
           今天這一天的畫面也一個像素都沒動。
         · `u > 1`（回放到比今天更極端的日子）：把 `1 → srAll/sr` 這一段壓進
           盤緣外的 `CLOCK_TAIL` 那條帶子裡。點會落在外圈虛線**外面**，
           而那正是事實（那一天它真的比今天任何族群都離大盤更遠），
           重點是**它們彼此分得開、而且會跟著時間軸動**。
       兩個分母（sr、srAll）都只吃 `scope`＝**今天**那一份原始資料，
       所以刷時間軸時整把尺完全不動，拍板過的約束沒有被破壞。*/
    const rawR = (x, y) => Math.hypot(((x || 100) - 100) / sx, ((y || 100) - 100) / sy);
    let sr = 1e-9, srAll = 1e-9;
    scope.forEach(r => {
      sr = Math.max(sr, rawR(r.rs, r.mo));
      (r.trail || []).forEach(w => { if (w && w[1] != null && w[2] != null) srAll = Math.max(srAll, rawR(w[1], w[2])); });
    });
    srAll = Math.max(srAll, sr);
    const tailSpan = Math.max(1e-6, srAll / sr - 1);     // 緩衝帶要裝下「比今天多出來」的那一截
    const pos = (x, y) => {                              // (相對強弱, 動能) → [半徑, 角度]
      const dx = ((x || 100) - 100) / sx, dy = ((y || 100) - 100) / sy;
      let a = Math.atan2(dy, dx) * 180 / Math.PI; if (a < 0) a += 360;
      const u = Math.sqrt(dx * dx + dy * dy) / sr;       // 1＝今天偏離最大的那個族群（＝外圈虛線）
      const k = u <= 1 ? u : 1 + CLOCK_TAIL * (u - 1) / tailSpan;
      return [Math.min(CLOCK_MAXR * (1 + CLOCK_TAIL), k * CLOCK_MAXR), a];
    };
    /* 即時模式下一個族群有**三個**位置（見 rlvCompute 的註解）：
         p0 上一個收盤　→　pf 持平基準（今天完全平盤也會走到的地方）　→　p 現在。
       p0→pf 是慣性、pf→p 才是今天的錢推出來的。*/
    const pts = top0.map(r => ({ ...r, p: pos(r.rs, r.mo),
      p0: r.live ? pos(r.live.x0, r.live.y0) : null,
      pf: r.live ? pos(r.live.fx, r.live.fy) : null }));
    /* 順序固定成「族群在前、個股在後」：兩個 scatter series 共用同一張標籤位置表
       （rotLbl[id]），族群的 dataIndex 就是 i、個股的是 nG + j。
       順序一亂，名字就會掛到別人頭上。*/
    const top = pts.filter(r => !r.isStock).concat(pts.filter(r => r.isStock));
    const nG = top.filter(r => !r.isStock).length;
    const maxR = CLOCK_MAXR;
    /* 在極座標上補點，讓線**貼著圓弧走**（Andy 2026-09-18：
       「他的線需要沿著圓圈變化，而不是一個斷點直線跑過去」）。
       ECharts 的 line series 就算掛在 polar 上，兩點之間仍然是在螢幕上連一條直線 ——
       角度差一大，那條線就直接橫跨過圓心，看起來像「跳過去」而不是「轉過去」。
       所以自己在角度與半徑上各補中間點；角度一律走較短的那一邊，
       不然從 350° 到 10° 會沿著圓繞一大圈回去。*/
    /* ★ 2026-09-20（E1，Andy：「軌跡線不能比圓圈還動的快」）：
       補點的過程**全程用不取模的連續角度**，最後一步才取模還給 ECharts。
       以前每補一個點就 `% 360`，於是 350°→10° 之間會出現 -340 的數值跳躍；
       接下來要照弧長重取樣，那一段會被算成「繞了大半圈」，整條尾巴就歪掉。*/
    const unwrap = (pts) => {
      let cur = pts.length ? pts[0][1] : 0;
      return pts.map(([r, a], i) => {
        if (i === 0) return [r, cur];
        let d = a - cur;
        d = ((d % 360) + 540) % 360 - 180;      // 收進 (-180, 180]＝一律走短的那一邊
        cur += d;
        return [r, cur];
      });
    };
    const densify = (pts) => {
      const out = [];
      for (let i = 0; i < pts.length - 1; i++) {
        const [r0, a0] = pts[i], [r1, a1] = pts[i + 1];
        const d = a1 - a0;                       // 已經是連續角度，不用再挑邊
        const n = Math.max(2, Math.min(24, Math.round(Math.abs(d) / 6) + 2));
        for (let k = 0; k < n; k++) { const u = k / n; out.push([r0 + (r1 - r0) * u, a0 + d * u]); }
      }
      if (pts.length) out.push(pts[pts.length - 1]);
      return out;
    };
    /* ★ E1 的解法本體：把整條路**重取樣成固定點數**。
       Andy 看到的現象是「尾巴比圓圈動得快」，量出來的根因是點數會變：
       時間軸每前進一天，trail() 回傳的點數就多一段（span=5 是 259 點、span=10 是 519 點）。
       ECharts 做 merge 更新時只有「新舊都存在的索引」會補間，
       新長出來的那一段沒有對應的舊位置 —— 所以尾巴的尖端是**瞬移**過去的，
       而大圈是用 animationDurationUpdate(420ms, linear) 慢慢滑過去的。
       兩者的位置來源（atFrame）其實一模一樣，差別完全在「一個瞬移、一個補間」。
       固定成 48 點之後，每一個索引在前後兩幀都有對應，整條線就跟大圈同一個
       duration/easing 一起滑，尖端永遠貼著大圈。
       取樣依據是**弧長**不是天數：轉得急的那一段弧長本來就長，會自動分到比較多點，
       圓弧的形狀才不會被 48 點拉成直線。*/
    const TRAIL_PTS = 48;
    const resample = (dense, n) => {
      const out = [];
      const xy = dense.map(([r, a]) => { const t = a * Math.PI / 180; return [r * Math.cos(t), r * Math.sin(t)]; });
      const cum = [0];
      for (let i = 1; i < xy.length; i++) {
        const dx = xy[i][0] - xy[i - 1][0], dy = xy[i][1] - xy[i - 1][1];
        cum.push(cum[i - 1] + Math.sqrt(dx * dx + dy * dy));
      }
      const total = cum[cum.length - 1];
      /* 整條路還縮在一個點上（軌跡剛站上起點）：48 個點全部重疊 ——
         這正好就是「還沒走出軌跡」該有的樣子，不要特別處理成「只畫一個點」，
         那會讓點數又變成會動的量，E1 的病根就回來了。*/
      if (!(total > 1e-9)) {
        for (let k = 0; k < n; k++) out.push(dense[dense.length - 1]);
        return out;
      }
      let j = 1;
      for (let k = 0; k < n; k++) {
        const want = total * k / (n - 1);
        while (j < cum.length - 1 && cum[j] < want) j++;
        const seg = cum[j] - cum[j - 1] || 1;
        const u = Math.max(0, Math.min(1, (want - cum[j - 1]) / seg));
        out.push([dense[j - 1][0] + (dense[j][0] - dense[j - 1][0]) * u,
          dense[j - 1][1] + (dense[j][1] - dense[j - 1][1]) * u]);
      }
      // 兩端要「完全」落在原來的端點上：尖端差幾個像素就是 Andy 會看到的脫節
      out[0] = dense[0]; out[n - 1] = dense[dense.length - 1];
      return out;
    };
    /* 尾巴：**已經走過**的那一段路（Andy 2026-09-20：「只有經過才留下軌跡，
       不是馬上所有軌跡都先印出來」）。

       以前是一開始就把整整 span 天的路全部印出來、大圈在上面滑 ——
       看起來像「路本來就在那裡」，不是「牠自己走出來的」。現在改成漸進式：
         起點  = max(0, 目前位置 - span)          ← 所以 span 的語意仍然是「軌跡畫幾天」
         終點  = 大圈現在站的位置（可小數，最後補一小段殘段）
       主卡片的 span 固定 30、而 trail 只存 31 天，所以起點永遠是最舊那一天，
       時間軸刷到「前 30 天」時只剩起點一個點，往「今天」刷才一天一天長出來 ——
       這就是他要的那個效果。放大視窗的 span 是可調的，語意自然變成「跟在後面的尾巴多長」。

       路標仍然畫滿每一天（不再像 2026-09-18 那版只挑 6 個）：後端把 RS 平滑掉之後
       一日步長只有盤面半徑的 0.053，畫滿才看得到「一天走一小步」。
       上限 40 個路標純粹是防呆。*/
    const span = opts.span != null ? opts.span : back;
    const trailOn = opts.trail !== false;
    // 這條軌跡實際走過幾天（＝終點索引 − 起點索引）。固定點數之後「幾個點」不再有鑑別度，
    // 驗收改量這個值：刷到最舊那一天是 0，往今天刷才一天一天長出來。
    const trailDays = (r) => {
      const t = r.trail || [];
      if (!t.length || !trailOn) return 0;
      const end = atFrame(t, frame);
      if (!end) return 0;
      return Math.max(0, end[3] - Math.max(0, Math.floor(end[3]) - span));
    };
    const trail = (r) => {
      const t = r.trail || [];
      if (!t.length || !trailOn) return [];
      const end = atFrame(t, frame);
      if (!end) return [];
      const iEnd = end[3];
      const i0 = Math.max(0, Math.floor(iEnd) - span);
      const way = [];
      for (let i = i0; i <= Math.floor(iEnd); i++) way.push([t[i][1], t[i][2]]);
      if (Math.floor(iEnd) < iEnd - 1e-9) way.push([end[1], end[2]]);   // 走到一半的殘段
      const step = Math.max(1, Math.ceil((way.length - 1) / 40));
      const picked = way.filter((_, i) => i % step === 0);
      if (picked[picked.length - 1] !== way[way.length - 1]) picked.push(way[way.length - 1]);
      const dense = densify(unwrap(picked.map(w => pos(w[0], w[1]))));
      // 最後一步才取模：ECharts 的 angleAxis 是 0~360，連續角度餵進去會被畫到盤外
      return resample(dense, TRAIL_PTS).map(p => [p[0], ((p[1] % 360) + 360) % 360]);
    };
    /* A4 第 6 條（Andy：「越外圈顏色越深」）。
       做法是把族群色**往面板底色調淡**，離圓心越近調得越淡、越外圈越接近原色。
       為什麼不是反過來把外圈「調黑」：深色主題的底本來就是黑的，
       往黑調等於把最重要的那幾個族群變不見。
       往底色調淡在深淺兩種主題下都成立 —— 淡＝跟背景融在一起＝跟大盤差不多，
       濃＝跳出背景＝和大盤差得多，剛好就是這張圖要傳達的事。
       下限 0.42 是為了「圓心附近的點還看得見」，不是隨便取的：
       再低於這個值，靠圓心的族群在 1440px 上已經讀不出顏色屬於哪一段。*/
    const DEPTH_MIN = 0.42;
    const depthColor = (r) => mixHex(CH.panel, STAGE[r.stage].color,
      DEPTH_MIN + (1 - DEPTH_MIN) * Math.max(0, Math.min(1, r.p[0] / maxR)));
    const sectorColor = {};
    CLOCK_SECTOR.forEach(s => { sectorColor[s.k] = STAGE[s.k].color; });
    const areaColors = CLOCK_SECTOR.flatMap(s => [hexA(STAGE[s.k].color, .13), hexA(STAGE[s.k].color, .13)]);
    /* 即時模式要畫的那幾條「上一個收盤 → 現在」。
       只收**真的有續算結果**的族群 —— 沒抓到報價的那幾個就維持盤後位置、不畫箭頭，
       畫一條長度 0 的線只會讓人以為「它今天沒動」，而事實是「我們沒拿到它的報價」。*/
    const liveArr = liveOn ? top.filter(r => r.p0 && r.live) : [];
    const o = {
      tooltip: {
        ...tip, trigger: 'item', formatter: (q) => {
          const r = q.data && q.data.row; if (!r) return '';
          const s = STAGE[r.stage];
          // 個股點：分母是所屬族群（和成分股清單、資金去向的葉節點同一個口徑）
          if (r.isStock) {
            return `<b>${fmt.esc(r.name)} ${fmt.esc(r.code)}</b>　<span style="color:${s.color}">${s.name}</span>`
              + `<br><span class="muted">屬於「${fmt.esc(r.gname || '')}」的成分股</span>`
              + `<br>相對大盤強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 2)}`
              + `<br>動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 2)}`
              + `<br>佔族群成交值 ${fmt.n(r.share, 1)}%`
              + (r.has_page ? '<br><small>點一下進個股頁（要拿掉它就再點一次清單裡那一列）</small>'
                : '<br><small>這一檔還沒有個股頁；點一下從盤上拿掉</small>');
          }
          return `<b>${fmt.esc(r.name)}</b>　<span style="color:${s.color}">${s.name}</span>`
            + `<br>相對大盤強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 2)}`
            + `<br>動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 2)}`
            + (r.was ? `<br>${back} 天前在「${STAGE[r.was].name}」${r.moved ? '　<b>已經換段</b>' : ''}` : '')
            /* 即時模式：把「上一個收盤在哪、現在在哪、走了多遠」三件事一次講完。
               只寫「現在在哪」的話，使用者看到一顆幾乎沒動的點會以為功能壞了。*/
            + (r.live ? `<br><span style="color:${s.color}">⚡ 盤中即時</span>`
              + `　族群報酬 ${fmt.pct(r.live.ret * 100, 2)}（大盤代理值 ${fmt.pct((RLV.mkt || 0) * 100, 2)}）`
              + `<br>上一個收盤 強弱 ${fmt.n(r.live.x0 - 100, 2)} / 動能 ${fmt.n(r.live.y0 - 100, 2)}`
              + `<br><span class="muted">慣性（平盤也會走）強弱 ${r.live.fx - r.live.x0 >= 0 ? '+' : ''}${fmt.n(r.live.fx - r.live.x0, 2)}　動能 ${r.live.fy - r.live.y0 >= 0 ? '+' : ''}${fmt.n(r.live.fy - r.live.y0, 2)}</span>`
              + `<br><b>今天推的</b> 強弱 ${r.live.tdx >= 0 ? '+' : ''}${fmt.n(r.live.tdx, 2)}　動能 ${r.live.tdy >= 0 ? '+' : ''}${fmt.n(r.live.tdy, 2)}`
              + (r.live.stage0 !== r.live.stage
                ? `　<b>跨過象限：${STAGE[r.live.stage0].name} → ${STAGE[r.live.stage].name}</b>` : '')
              + `<br><span class="muted">權重是「價 × 量」估的，漲跌幅是真的</span>` : '')
            + `<br>成交值佔比 ${fmt.n(r.share, 1)}%<br><small>點一下看成分股</small>`;
        },
      },
      // N5（Andy 2026-09-19「輪動時鐘圓圈範圍擴大點」）：72% → 84%。
      // 標籤已經改成左右兩欄＋引線（不佔盤面），所以盤可以放大。
      polar: { center: ['50%', compact ? '52%' : '50%'], radius: compact ? '66%' : '84%' },
      angleAxis: {
        type: 'value', min: 0, max: 360, startAngle: 0, clockwise: false, interval: 45,
        axisLine: { show: false }, axisTick: { show: false },
        splitLine: { lineStyle: { color: CH.grid } },
        splitArea: { show: true, areaStyle: { color: areaColors } },
        axisLabel: {
          /* opts.quads＝這張圖的象限標籤改由 HTML 卡片畫（可點、可展開），
             ECharts 這一組就要關掉，不然「領先」會在同一個位置疊出兩份。*/
          show: !opts.quads,
          margin: compact ? 6 : 10, fontSize: compact ? 12 : 14, fontWeight: 700,
          formatter: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].name : ''; },
          color: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].color : 'transparent'; },
        },
      },
      /* 2026-09-18（Andy 圖二「需要補充圓心到圓外 差異為何」）：
         以前是等距好幾圈細線，看不出哪一圈代表什麼。改成只留兩圈**虛線**，
         並在「怎麼看 ?」裡講清楚它們是什麼（2026-09-21 前是圖下方常駐的 #rotCenterNote，已移除）：
           0.5 圈＝今天最大偏離的一半　/　1.0 圈＝今天偏離最大的那個族群。
         `interval: maxR/2` 就是這兩圈，**軸的上限變了也不會跟著跑掉**。
         ★ 軸的上限 = 1.0 圈 ＋ 緩衝帶（CLOCK_TAIL）＋ 6% ——
           最後那 6% 是「點的半徑」本身要站的地方，不留的話回放到最極端那一天時
           那顆大圈會有一半落在盤外。*/
      radiusAxis: { type: 'value', min: 0, max: maxR * (1 + CLOCK_TAIL) * 1.06, axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: true, lineStyle: { color: hexA(CH.ink3, .45), type: 'dashed', width: 1 } },
        splitNumber: 2, interval: maxR / 2 },
      series: [
        // 尾巴：這幾天走過的路
        ...top.map(r => ({
          // 只在「N 天前」那一端點一個小圈圈（line series 的 symbol 不吃陣列，要用 symbolSize 挑）
          type: 'line', coordinateSystem: 'polar', silent: true, symbol: 'circle',
          gid: r.gid,                                   // 給 highlightClock 認人用（圖四點長條時只亮這一族群）
          symbolSize: (v, q) => (q.dataIndex === 0 ? 6 : 0), data: trail(r), z: 2,
          itemStyle: { color: hexA(STAGE[r.stage].color, r.isStock ? .4 : .55) },
          // 個股的尾巴刻意更細、而且是虛線 —— 一眼就分得出「哪一條是族群、哪一條是個股」
          lineStyle: { color: hexA(STAGE[r.stage].color, r.isStock ? .34 : .42),
            width: r.isStock ? 1 : 1.6, type: r.isStock ? 'dashed' : 'solid' },
        })),
        /* ★ 盤中即時的主角：那條「上一個收盤 → 現在」的箭頭。

           為什麼用 `custom` 而不是 line＋`symbol:'arrow'`：
           ECharts 的 line series 不會把箭頭**轉到線的方向**（symbolRotate 是固定值），
           在極座標上每條線的方向都不一樣，所以那條路走不通。
           `custom` 的 `renderItem` 拿得到 `api.coord()`（極座標 → 像素），
           於是箭頭可以在**像素空間**算得精準，粗細也不會被半徑縮放影響。

           ★★ 箭頭大小跟著「真實位移的長度」縮放（`L * 0.45`，上限 9px）。
              固定大小的箭頭會讓 4px 的位移看起來像 12px —— 那就是變相放大位移。
              位移小，箭頭就小；位移大，箭頭才大。**位置本身一個像素都沒有被動過。** */
        /* ★★ 這兩個 series **永遠都在**（關掉即時時 data 是空陣列），不要寫成
           `...(liveArr.length ? [...] : [])`。
           2026-09-22 第一次跑驗收就被「那條線也真的不見了」抓到：
           重畫時大多數情況走的是 `notMerge: false`（點才會平滑滑過去），
           而 **merge 是照索引對的 —— 新的 series 陣列變短，ECharts 不會把多出來的舊 series 移掉**，
           於是按「退回盤後」之後箭頭還留在圖上。
           固定 series 數是最省事也最不容易再犯的解法：數量不變，merge 就只是把資料換成空的。*/
        {
          /* z 要**比族群點（5）與個股點（6）都高**。
             2026-09-22 第一版寫 z:4，截圖之後發現「彩色那一段只有 4px，而族群點的直徑最大 26px」——
             箭頭整段藏在圓圈底下，等於沒畫。畫在上面之後它像一根指針貼在圓圈上，
             走得多的那幾個（8～20px）則會明顯戳出圓圈外。*/
          type: 'custom', coordinateSystem: 'polar', z: 7, silent: true, name: '即時位移',
          data: liveArr.map(r => ({ value: [r.p[0], r.p[1]], row: r })),
          renderItem: (params, api) => {
            const r = liveArr[params.dataIndex]; if (!r) return null;
            const a = api.coord([r.p0[0], r.p0[1]]);      // 上一個收盤
            const f = api.coord([r.pf[0], r.pf[1]]);      // 持平基準（慣性走到的地方）
            const b = api.coord([r.p[0], r.p[1]]);        // 現在
            if (!a || !f || !b) return null;
            const col = STAGE[r.stage].color;
            const kids = [];
            // ① 慣性那一段：灰色虛線、細。它**不是**今天的錢做的，所以不可以搶眼。
            const iL = Math.hypot(f[0] - a[0], f[1] - a[1]);
            if (iL > 0.4) {
              kids.push({ type: 'line', shape: { x1: a[0], y1: a[1], x2: f[0], y2: f[1] },
                style: { stroke: hexA(CH.ink2, .8), lineWidth: 1.8, lineDash: [3, 3] } });
              // 起點（上一個收盤）留一顆空心小圈，才看得出「從這裡走到那裡」
              kids.push({ type: 'circle', shape: { cx: a[0], cy: a[1], r: 2.6 },
                style: { fill: CH.panel, stroke: hexA(CH.ink3, .9), lineWidth: 1.2 } });
            }
            /* ② 今天的錢推出來的那一段：粗、亮色、有箭頭。這才是使用者要看的東西。
               ★★ 箭頭大小跟著**真實長度**縮放（L × 0.45，上限 9px）。
                  固定大小的箭頭會讓 4px 的位移看起來像 12px —— 那就是變相放大位移。*/
            const dx = b[0] - f[0], dy = b[1] - f[1];
            const L = Math.hypot(dx, dy);
            if (L > 0.4) {
              const ux = dx / L, uy = dy / L;
              const head = Math.min(9, Math.max(2, L * 0.45));
              const hw = head * 0.45;
              const bx = b[0] - ux * head, by = b[1] - uy * head;
              /* ★ 針身用 `CH.ink`（深色主題近白、淺色主題近黑），外圈才用族群的階段色。
                 2026-09-22 截圖之後改的：本來針身是階段色、外圈描面板底色，
                 而這根針**就站在同一個階段色的圓圈上** —— 同色疊同色，等於看不見。
                 亮色針 ＋ 彩色光暈在深淺兩種主題下都跳得出來，
                 而且顏色的語意沒有被搶走（階段仍然由那顆圓圈的顏色講）。*/
              kids.push({ type: 'line', shape: { x1: f[0], y1: f[1], x2: bx, y2: by },
                style: { stroke: col, lineWidth: 5.6, lineCap: 'round', opacity: .95 } });
              kids.push({ type: 'line', shape: { x1: f[0], y1: f[1], x2: bx, y2: by },
                style: { stroke: CH.ink, lineWidth: 2.6, lineCap: 'round' } });
              kids.push({ type: 'polygon', shape: { points: [[b[0], b[1]],
                [bx - uy * hw, by + ux * hw], [bx + uy * hw, by - ux * hw]] },
                style: { fill: CH.ink, stroke: col, lineWidth: 1.4 } });
            }
            // 兩段都小於一個像素就整個不畫（畫出來只是一顆看不出方向的髒點）
            if (!kids.length) return null;
            return { type: 'group', children: kids };
          },
        },
        /* 端點的漣漪：Andy 要「會動」。這一圈純粹是「這顆點是即時的」的標記，
           它**不代表任何數值**，所以不會讓人把它讀成「走了這麼遠」。
           （和上面那個 custom 一樣：永遠存在，關掉即時時 data 是空的。）*/
        {
          type: 'effectScatter', coordinateSystem: 'polar', z: 3, silent: true, name: '即時',
          showEffectOn: 'render', rippleEffect: { brushType: 'stroke', scale: 3.2, period: 3.4 },
          symbolSize: 6,
          data: liveArr.map(r => ({ value: [r.p[0], r.p[1]],
            itemStyle: { color: STAGE[r.stage].color, opacity: .9 } })),
        },
        // 現在的位置（族群：實心圓）
        {
          type: 'scatter', coordinateSystem: 'polar', z: 5, name: '族群',
          data: top.slice(0, nG).map(r => ({ value: [r.p[0], r.p[1]], row: r,
            itemStyle: { color: depthColor(r), borderColor: CH.panel, borderWidth: 1.5,
              shadowBlur: r.moved ? 14 : 0, shadowColor: STAGE[r.stage].color },
            // 左半邊的點把名字放左邊、右半邊放右邊，字才不會全部擠在同一側疊住
            label: { position: r.p[1] > 95 && r.p[1] < 265 ? 'left' : 'right' } })),
          symbolSize: (v, q) => { const r = q.data.row; return Math.max(9, Math.min(26, 8 + Math.sqrt(r.share) * 5)); },
          label: { show: !compact, distance: 7, color: CH.ink2, fontSize: LBL_FS,
            // 描邊用面板底色，深淺主題都要跟著換（以前寫死 '#0b0f1a'，淺色主題下是黑邊白底）
            textBorderColor: CH.panel, textBorderWidth: 3,
            formatter: (q) => q.data.row.name },
          labelLine: { show: !compact, lineStyle: { color: hexA(CH.ink3, .55), width: 1 } },
          /* ★ 不要用 labelLayout: { hideOverlap: true }。
             那是「疊到就把後面那個**藏起來**」—— Andy 2026-09-18 圖二講的
             「自體態粗都擠在一起了」正是這個：名字沒排開，是被吃掉。
             改成左右兩欄＋引線（和 3D 剖析圖 E1 同一套）：
             先把每個點轉成像素座標，依 x 決定排左欄還是右欄，欄內依 y 由上而下擺，
             擺不下就由下往上收，最後夾在畫布內。每個標籤再拉一條細線回到自己的點。*/
          labelLayout: (q) => {
            const m = (rotLbl[id] || {})[q.dataIndex];
            if (!m) return {};
            // 左欄往右長、右欄往左長（見 layoutRotLabels 的註解）
            const align = m.side === 'left' ? 'left' : 'right';
            // 引線從點拉到文字的「內側」那一端，不要穿過文字
            const tip = m.side === 'left' ? m.x + m.rect.w + 4 : m.x - m.rect.w - 4;
            return { x: m.x, y: m.y, align, verticalAlign: 'middle',
              labelLinePoints: [[m.px, m.py], [tip, m.y], [m.side === 'left' ? m.x + m.rect.w : m.x - m.rect.w, m.y]] };
          },
        },
        /* 階段三：使用者點開的個股（Andy 2026-09-21「也可以點擊，並顯示在圖上」）。
           ★ **樣式一定要和族群分得出來**：族群是實心圓、個股是空心圓（只有一圈邊）＋
             細虛線軌跡，「怎麼看 ?」裡也寫了哪個是哪個。
             一樣畫成實心圓的話，盤上會變成 26 顆長得一模一樣的點，
             使用者根本不知道自己剛剛點開的是哪幾顆。
           ★ 圈圈大小改用「佔所屬族群成交值的比例」（族群那一顆用的是佔全市場），
             兩者的分母不同，直接共用同一支 symbolSize 會讓個股全部比族群還大。*/
        ...(top.length > nG ? [{
          type: 'scatter', coordinateSystem: 'polar', z: 6, name: '個股',
          data: top.slice(nG).map(r => ({ value: [r.p[0], r.p[1]], row: r,
            itemStyle: { color: hexA(STAGE[r.stage].color, .16), borderColor: depthColor(r), borderWidth: 2 },
            label: { position: r.p[1] > 95 && r.p[1] < 265 ? 'left' : 'right' } })),
          symbolSize: (v, q) => { const r = q.data.row;
            return Math.max(8, Math.min(17, 7 + Math.sqrt(Math.max(0, r.share || 0)) * 1.3)); },
          label: { show: !compact, distance: 7, color: CH.ink3, fontSize: LBL_FS,
            textBorderColor: CH.panel, textBorderWidth: 3,
            formatter: (q) => q.data.row.lbl || q.data.row.name },
          labelLine: { show: !compact, lineStyle: { color: hexA(CH.ink3, .45), width: 1, type: 'dashed' } },
          // 標籤位置查的是同一張表，索引要加上族群的筆數（見上面 `top` 的排序註解）
          labelLayout: (q) => {
            const m = (rotLbl[id] || {})[nG + q.dataIndex];
            if (!m) return {};
            const align = m.side === 'left' ? 'left' : 'right';
            const tip = m.side === 'left' ? m.x + m.rect.w + 4 : m.x - m.rect.w - 4;
            return { x: m.x, y: m.y, align, verticalAlign: 'middle',
              labelLinePoints: [[m.px, m.py], [tip, m.y], [m.side === 'left' ? m.x + m.rect.w : m.x - m.rect.w, m.y]] };
          },
        }] : []),
      ],
      graphic: compact ? [] : [
        /* ★ 2026-09-20：圖裡的四個 ↻ 箭頭移除，方向改用圖下方那一行字講。
           查出來的事實（多寬度掃描量的，不是感覺）：
             · 放在「兩段的交界」（正上下左右，41%）→ 撞到跑到圓周上的族群名
               （1280px：↻ × 晶圓代工 重疊 17×12px）；
             · 挪到「每一段的外角」（47%）→ 撞到該段自己的名字
               （落後／改善／領先／轉弱 本來就寫在那個角度的圓周外側）。
           極座標圓上能放東西的位置就這兩種，兩種都已經有人了 ——
           再調數字只是在換一個會撞的日子，所以不繼續研究，直接把方向講成文字。
           （Andy 在 A4 輪動時鐘的需求第 2 條本來就寫「移除旋轉箭頭」。）*/
        /* ★ 2026-09-20：原本這裡有三行說明，在 1280px 的畫面上整串凸出容器 26px、
            而且壓到右下角那個 ↻ 箭頭（新的多寬度掃描量出來的）。
            「↻ 箭頭＝行進方向」那一句搬到文字說明裡（當時是 #rotCenterNote，
            2026-09-21 起併進「怎麼看 ?」）—— 它是 HTML，
            會自己換行，任何寬度都不可能溢出。圖裡只留「回放日期」與一行最短的比例說明。*/
        { type: 'text', right: 12, bottom: 8, silent: true,
          style: { text: (frameDate ? '⏱ 回放：' + frameDate + '\n' : '')
              /* 即時模式時多一行講箭頭是什麼。只有一行、而且刻意不寫數字 ——
                 數字全部在圖下方那條狀態列裡，圖上塞數字一定會撞到族群名。*/
              + (liveArr.length ? '⚡ 即時：灰虛線＝慣性　亮色箭頭＝今天推的\n' : '')
              + '圈圈大＝佔比高　·　離圓心遠＝差大盤多',
            fill: hexA(CH.ink2, .55), fontSize: 11.5, lineHeight: 16, textAlign: 'right' },
        }],
    };
    /* N3（Andy 2026-09-19「族群在時鐘上要像螞蟻一樣可以緩步移動，而非定格方式，
       這樣播放才有趨勢性」）：回放時**不要** notMerge。
       notMerge 會把整個 series 換掉 —— ECharts 認不出「還是同一顆點」，
       所以每一幀都是重畫、看起來像跳格。用 merge 的話它會把舊位置補間到新位置，
       點就自己沿著路徑走過去了。
       只有「族群數真的變了」（換篩選、換天數）才需要 notMerge，否則會留下殘線。*/
    const shape = top.length + '|' + top.map(r => r.gid).join(',');
    const sameShape = rotLastShape[id] === shape;
    rotLastShape[id] = shape;
    /* 補間時間＝播放間隔（ROT_ANIM_MS）。兩者相等的時候一天接著一天、中間沒有空檔，
       所以看起來是「等速滑過去」而不是「走一步停一下」。easing 一定要 linear：
       easeOut 會在每一天的尾巴急停，那正是「段點段點」的另一個來源。*/
    o.animationDurationUpdate = ROT_ANIM_MS;
    o.animationEasingUpdate = 'linear';
    const c = chart(id, o, { notMerge: !sameShape });
    /* 標籤排版要等圖畫完（要有像素座標才知道誰在左誰在右），
       所以先畫一次、算好位置、再 setOption 一次讓 labelLayout 查表。
       第二次不用 notMerge，只是重跑一次標籤排版，不重建尾巴。*/
    /* 驗收要「用數值比，不要用眼睛」量「越外圈顏色越深」，所以把每顆點的
       半徑、混出來的顏色、以及那一段的原色一起攤出來 ——
       混色是 mixHex(底色, 原色, w)，量的人可以從 (顏色, 原色, 底色) 反推出 w，
       再驗 w 真的隨半徑遞增。攤的是**畫上去的值**，不是我心裡想的值。*/
    if (opts.expose) {
      window.App._rotBg = CH.panel;
      window.App._rotPts = top.map(r => ({ gid: r.gid, name: r.name,
        // 下鑽之後盤上會同時有族群與個股，驗收要分得出來（點數變多的是哪一種）
        code: r.code || null, stock: !!r.isStock,
        /* 驗收「即時模式下座標真的變了／退出後真的變回來」量的是這兩個值 ——
           它們就是畫上去的那一點，不是我心裡想的那一點。*/
        x: +(+r.rs).toFixed(4), y: +(+r.mo).toFixed(4), live: !!r.live,
        r: +(r.p[0] / maxR).toFixed(4), color: depthColor(r), base: STAGE[r.stage].color }));
      /* 那條「上一個收盤 → 現在」的線：把兩端的**極座標**攤出來，
         驗收再用 `App.rotLiveSeg()` 換成像素長度（那才是「使用者真的看到一條線」）。*/
      // 這一輪盤上真的有箭頭的族群 —— 圖下方那排讀數只列這幾個（見 rlvTop 的註解）
      rlvShown = new Set(liveArr.map(r => r.gid));
      window.App._rotLiveAt = liveArr.map(r => ({ gid: r.gid, name: r.name,
        p0: r.p0, pf: r.pf, p1: r.p,
        dx: +r.live.dx.toFixed(4), dy: +r.live.dy.toFixed(4),
        tdx: +r.live.tdx.toFixed(4), tdy: +r.live.tdy.toFixed(4),
        jump: r.live.stage0 !== r.live.stage }));
      window.App._rotFrame = { frame, date: frameDate, span, trail: trailOn,
        /* ★ 2026-09-20（E1）：軌跡改成固定 48 點之後，「畫了幾個點」變成常數、
           再也量不出任何東西。驗收改量**軌跡實際走過幾天**（所有族群加總）——
           刷到最舊那一天是 0，往今天刷會一天一天長出來，語意跟漸進式軌跡一致。*/
        trailDays: +top.reduce((a, r) => a + trailDays(r), 0).toFixed(2),
        trailPts: TRAIL_PTS };                // 固定值，只是讓人知道一條尾巴幾個點
    }
    if (c && !compact) {
      /* ★ 2026-09-20：標籤排版必須**跟著容器大小重算**。
         `chart()` 掛的 ResizeObserver 只會呼叫 ECharts 的 `resize()` ——
         圖會重畫，但 labelLayout 查的是 `rotLbl` 這張表，那是上一次的像素座標，
         所以視窗一改變寬度，族群名就停在舊位置、整排掉到圖外面。
         實測（1500px → 800px → 1500px）：標籤還停在 800px 那一版的 x=624~728，
         但容器已經縮回 502 —— 六個族群名全部在畫布外。
         這不是只有驗收會遇到，Andy 的 C2「換一台電腦版面就跑掉」就是同一件事。
         所以這裡自己掛一個 ResizeObserver，尺寸真的變了才重排（120ms 去抖動）。*/
      const relayout = () => {
        if (!el.isConnected) return;
        const cur = window.echarts && echarts.getInstanceByDom(el);
        if (cur !== c) return;                       // 圖被換掉或 dispose 了就不要再動它
        rotLbl[id] = layoutRotLabels(c, el, top);
        // 驗收用：量兩兩不重疊、全在畫布內（只有卡片那張圖要攤出來，不然放大時會互相蓋掉）
        if (opts.expose) window.App._rotLabels = Object.keys(rotLbl[id]).map(k => rotLbl[id][k].rect);
        // 象限卡的位置是從容器尺寸算出來的，所以和族群名標籤走同一個重排時機（含 120ms 去抖動）
        if (opts.quads) rotQuadChips(el);
        try { c.setOption({ series: o.series }, { notMerge: false, lazyUpdate: false }); } catch (e) { /* 忽略 */ }
      };
      relayout();
      el._rotRelayout = relayout;                    // 永遠指向「最後一次畫的那一版」
      if (!el.dataset.rotRo && window.ResizeObserver) {
        el.dataset.rotRo = '1';
        let t = null, lastW = el.clientWidth, lastH = el.clientHeight;
        new ResizeObserver(() => {
          if (el.clientWidth === lastW && el.clientHeight === lastH) return;
          lastW = el.clientWidth; lastH = el.clientHeight;
          clearTimeout(t);
          t = setTimeout(() => { const f = el._rotRelayout; if (f) f(); }, 120);
        }).observe(el);
      }
    } else if (compact) {
      rotLbl[id] = {};
    }
    /* ★ 2026-09-21（Andy 的兩階段）：點族群**不再跳頁**，改成原地展開成分股。
       他的規矩是「點擊優先在原地展開，不要動不動就把人帶離當前頁面」——
       真的要進族群頁的話，展開的面板標題右邊有「進族群頁 →」。
       點盤上的個股點則是進個股頁（能點的東西要能點到底）；沒有個股頁的就從盤上拿掉。*/
    if (c) c.off('click').on('click', q => {
      const r = q.data && q.data.row; if (!r) return;
      if (r.isStock) { if (r.has_page) goStock(r.code); else drillToggleStock(r.code); return; }
      drillOpen(r.gid, r.name);
    });
    /* ★ 2026-09-21：族群晶片列**不再由這裡產**。它搬進 `.rotfilter`（產業鏈 seg 的正下方），
       所以由 `wireRotFilter()` 一支負責 —— 一份名單、一套樣式、一個插入點。
       順帶解決一個播放時的老問題：以前每 420ms 重畫時鐘都要判斷要不要重建晶片列
       （`rotChipKey` 指紋），現在播放完全不會碰到晶片列。*/
  }

  /* ★ 2026-09-23：這一支現在**只負責時鐘**。
     原本它還會畫三塊東西，三塊都在 2026-09-23 這一批被 Andy 指定移除了：
       · `ids.board`（改善／領先／轉弱／落後四格階段卡）
         —— 資金流向頁那一份早先已併進時鐘的四個象限卡；
            總覽頁那一份（`#rotMini`）這一批換成「昨日資金去向分流圖」（D7）。
       · `ids.cycle`（改善→領先→轉弱→落後 ↩ 那一列）—— 時鐘順時針轉一圈就是同一件事。
       · `ids.move`（最近 5 個交易日換階段的族群）—— Andy 2026-09-23 指定拿掉；
         換段資訊改由象限展開面板每一列的徽章（`rotItem(r, true)` 的 `jump`）承擔。
     所以參數只剩 `clock` 這一組。`toggleRotMembers()` **不要跟著刪** ——
     季節性那塊 `#seasonBoard` 還在用同一支（同樣是 `.stage` 卡片裡點族群展開成分股）。*/
  function renderRotation(rrg, back, ids) {
    const rows = rotRows(rrg, back);
    if (!rows.length) {
      if (ids.clock) empty(ids.clock, '輪動時鐘需要至少 20 個交易日');
      return;
    }
    if (ids.clock) renderRotClock(rows, back, ids.clock, !!ids.compact,
      { pick: ids.pick, frame: ids.frame, span: ids.span, trail: ids.trail,
        // 象限卡只長在資金流向頁那張時鐘上（總覽小圖太小、放大視窗是另一份 DOM）
        quads: !!ids.quads,
        // 量測值只屬於「卡片上那張時鐘」（E2）：總覽小圖與放大視窗都不要
        expose: !!ids.expose });
  }

  /* 點族群 → 在它下面原地展開成分股（依成交值排序取前 12 檔）。再點一次收合。
     資料來自 groups_detail（總覽與資金流向兩頁進來之前都會先 load 它）。*/
  function toggleRotMembers(li) {
    const gid = li.dataset.gid;
    const nx = li.nextElementSibling;
    if (nx && nx.classList.contains('mem')) { nx.remove(); li.classList.remove('open'); return; }
    // 同一格裡一次只開一個，不然四格高度會亂跳
    const ul = li.parentNode;
    $$('li.mem', ul).forEach(e => e.remove());
    $$('li.open', ul).forEach(e => e.classList.remove('open'));
    const det = (D.groups_detail || {})[gid] || {};
    const ms = (det.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 12);
    const el = document.createElement('li');
    el.className = 'mem';
    el.innerHTML = ms.length
      ? ms.map(m => L.stock(m.code, m.name, { cls: 'sm' })).join('')
        + `<a class="pill cyan go" href="#industry/group/${gid}">進族群頁 →</a>`
      : `<span class="muted">成分股資料還在產出</span><a class="pill cyan go" href="#industry/group/${gid}">進族群頁 →</a>`;
    li.classList.add('open');
    li.parentNode.insertBefore(el, li.nextSibling);
  }

  /* ================================================================ 昨日資金去向分流圖（總覽右下）
     Andy 2026-09-23：「下方的紅框處改成昨日的資金去向分流圖（**不需要動畫，只顯示線條粗細即可，
     並且只顯示到族群即可。個股也不用**）」。紅框圈的是總覽「輪動階段」卡片下方
     「改善／領先／轉弱／落後」那四格階段卡（`#rotMini`）。

     ── 這張圖回答的問題（寫在卡片小標上）──
       **「最近一個交易日收盤，錢分到哪幾條產業鏈、鏈裡又分給哪幾個族群？」**
     四格階段卡回答的是「誰在強弱循環的哪一段」，那件事上面那張時鐘已經完整回答了
     （象限名 ＋ 顏色 ＋ 點的位置），四格卡只是把同一件事再用清單講一次 ——
     換成分流圖之後這張卡才有兩個**不同**的問題：上面「誰在轉強」、下面「錢分給了誰」。

     ── 資料來源與口徑（和資金流向頁那張桑基圖**同一份檔案、同一個口徑**）──
       · `site/data/sankey_daily.json`，取 `dates` 的**最後一天**（＝最近一個交易日的盤後結算值）。
         盤中不會動它 —— Andy 指定「資料是昨日（盤後結算）」，所以這張圖**刻意不接即時**。
       · 族群成交值對「同時掛在兩個板塊」的股票做過 **1/n 拆分**（後端 `compute/flow.py` 的口徑），
         所以族群加總會略小於逐檔加總。這句話和資金流向頁 tooltip 裡寫的是同一件事，
         **圖變簡單不等於可以把口徑說明拿掉**，所以下面那行 note 一定要留著。
       · 每一層的 % 都是「佔它上一層」的比重（和資金流向頁同一條規矩）。
       · 「〇〇・其他」這種自動桶（`ind_*`）是「不屬於任何人工族群」的收容桶，**照樣畫**
         （它真的有成交值，藏起來會讓 % 加不到 100），但名字本來就寫著「・其他」。

     ── 刻意砍掉的東西（Andy 指定）──
       · **不要動畫**：`animation: false`，換主題重畫也不補間。
       · **只用線條粗細表示流量**：不做漸層、不做流動點、不發光。
         節點只是很小的圓點，顏色沿用族群色（那是「這是誰」的識別，不是流量編碼）。
       · **只畫到族群層**：`initialTreeDepth: 2`，不掛代表股、不展開個股。
     ── 但是「能點的東西要能點到底」──
       族群名可以點，直接進族群頁（那一頁就有成分股）。總覽這張卡片沒有可以就地展開的
       側欄，硬塞一個面板會把卡片撐到比左邊的熱力圖高一倍，所以這裡是少數「跳頁」是對的地方。*/
  function renderOvFlow(sd) {
    const el = $('#ovFlow'); if (!el) return;
    const sub = $('#ovFlowSub');
    const bail = (msg) => { el.style.height = ''; if (sub) sub.textContent = ''; return empty('ovFlow', msg); };
    if (!sd || !(sd.dates || []).length || !(sd.groups || []).length) {
      return bail('資金去向的逐日資料還沒產出（下一輪盤後管線就會有）');
    }
    const day = sd.dates[sd.dates.length - 1];
    const k = sd.dates.length - 1;
    const gs = sd.groups.map(g => ({ gid: g.gid, name: g.name, chain: g.chain || 'other',
      chainName: g.chain_name || chainLabel(g.chain || 'other'), v: (g.tv || [])[k] || 0 }))
      .filter(g => g.v > 0);
    if (!gs.length) return bail(`${day} 這天沒有成交值資料`);
    const total = gs.reduce((a, g) => a + g.v, 0) || 1;
    const maxV = gs.reduce((a, g) => Math.max(a, g.v), 1);
    const pct = (v, base) => fmt.n((v || 0) / (base || 1) * 100, 1);
    /* 粗細是這張圖**唯一**的流量編碼，所以刻意用 sqrt：線性會讓最大的那條粗到 10px、
       後面十幾條全部擠在 1px 分不出來（實測 maxV 是中位數的 9 倍）。
       sqrt 把 1.2px～9px 分配得開，同時「粗的還是明顯比細的粗」。*/
    const width = (v, scale) => 1.2 + 7.8 * Math.sqrt(Math.min(1, (v || 0) / (scale || maxV)));
    const lt = theme() === 'light';
    const lineCol = hexA(CH.ink3, lt ? .55 : .5);   // 單一顏色：粗細已經在講流量，顏色不要再講一次

    // 產業鏈層：依成交值由大到小（這張圖是靜態的，不需要「位置固定」那條規矩）
    const chains = {};
    gs.forEach(g => {
      (chains[g.chain] = chains[g.chain] || { cid: g.chain, name: g.chainName, v: 0, kids: [] });
      chains[g.chain].v += g.v; chains[g.chain].kids.push(g);
    });
    const chainArr = Object.values(chains).sort((a, b) => b.v - a.v);
    const maxC = chainArr.reduce((a, c) => Math.max(a, c.v), 1);
    const narrow = (el.clientWidth || 9999) < 420;
    const nodeOf = (name, v, base, col, wpx, extra) => ({
      name, value: v, base,
      symbolSize: 7,
      itemStyle: { color: col, borderColor: 'transparent' },
      lineStyle: { color: lineCol, width: wpx, curveness: .5 },
      ...extra,
    });
    /* ★ 根節點**不畫**（symbolSize 0、label 不顯示）。
       總覽這一欄只有 1/3 版面寬，多一個「台股成交值 8271 億」的節點會把它的標籤
       一路壓到產業鏈那一欄的名字上（_preview 在 1280px 量到「其他產業別 10.5%」
       和「ETF 100.0%」重疊）。總成交值改寫在小標上，資訊沒有消失、版面省一整欄。
       ECharts 的 tree 需要一個根，所以節點留著、只是看不見。*/
    const data = [{
      name: '台股成交值', value: total, symbolSize: 0,
      itemStyle: { color: 'transparent', borderColor: 'transparent' },
      label: { show: false },
      children: chainArr.map(c => nodeOf(c.name, c.v, total, hexA(L.gcolor[c.kids[0].gid] || CH.cyan, lt ? .8 : .95),
        width(c.v, maxC), {
          label: { formatter: `${c.name} ${pct(c.v, total)}%`, fontWeight: 700, fontSize: 11.5 },
          children: c.kids.slice().sort((a, b) => b.v - a.v).map(g => nodeOf(
            g.name, g.v, c.v, hexA(L.gcolor[g.gid] || CH.cyan, lt ? .75 : .9), width(g.v), {
              gid: g.gid,
              label: { formatter: `${g.name} ${pct(g.v, c.v)}%`, fontSize: 11 },
            })),
        })),
    }];

    /* 高度自己算：ECharts 的 tree 把縱向空間平均分給葉子，族群數之後會變，
       寫死在 CSS 就是埋一顆以後才會爆的雷（和資金去向那張同一條理由）。*/
    el.style.height = Math.max(300, gs.length * 22 + 46) + 'px';
    const c = chart('ovFlow', {
      animation: false,                 // Andy 指定「不需要動畫」——連初次繪製的生長動畫也關掉
      tooltip: { ...tip, trigger: 'item',
        formatter: (p) => {
          const d = p.data || {};
          if (d.value == null) return p.name;
          return `<b>${fmt.esc(d.gid ? d.name : p.name)}</b><br>成交值 ${fmt.yi(d.value)}`
            + (d.base ? `<br>佔上一層 <b>${pct(d.value, d.base)}%</b>` : '')
            + `<br>佔全場 ${pct(d.value, total)}%`
            + `<br><span class="muted">${fmt.esc(day)} 盤後結算值；族群成交值已照 1/n 拆分</span>`
            + (d.gid ? '<br><small>點一下進族群頁看成分股</small>' : '');
        } },
      series: [{
        type: 'tree', orient: 'LR', layout: 'orthogonal', edgeShape: 'curve',
        left: 8, right: narrow ? 104 : 124, top: 12, bottom: 12,
        initialTreeDepth: 2,            // 只到族群那一層（Andy：個股不用）
        expandAndCollapse: false, roam: false, symbol: 'circle',
        /* 產業鏈那一層的名字放在節點**正上方**，不是右邊。
           右邊是它的族群那一欄：只有一個族群的鏈（例如「其他產業別」只有 ETF 一格）
           父子會落在同一條水平線上，標籤就會直接疊在一起。*/
        label: { position: 'top', distance: 4, color: CH.ink2, fontSize: 11,
          textBorderColor: CH.panel, textBorderWidth: 3,
          ...(narrow ? { width: 96, overflow: 'truncate' } : {}) },
        leaves: { label: { position: 'right', distance: 6, fontSize: 11, color: CH.ink3, align: 'left',
          ...(narrow ? { width: 96, overflow: 'truncate' } : {}) } },
        emphasis: { focus: 'relative', blurScope: 'series' },
        blur: { itemStyle: { opacity: .2 }, lineStyle: { opacity: .12 }, label: { opacity: .3 } },
        data,
      }],
    }, { notMerge: true });
    if (c) c.off('click').on('click', p => {
      const gid = (p.data || {}).gid;
      if (gid) location.hash = '#industry/group/' + gid;
    });
    if (sub) sub.textContent = `${day} 盤後結算，這 ${gs.length} 個族群合計 ${fmt.yi(total)}`
      + '　·　產業鏈 → 族群（只到族群層）'
      + '　·　每一層的 % 都是「佔它上一層」的比重　·　線越粗＝流過的成交值越大（沒有動畫）';
  }

  function renderThemeStrip(th) {
    const el = $('#themeStrip'); if (!th || !th.themes || !th.themes.length) { el.innerHTML = '<div class="empty">尚無題材資料</div>'; return; }
    el.innerHTML = `<div class="tiles">` + th.themes.slice(0, 8).map(t => `<div class="tile" onclick="location.hash='#themes/${t.id}'"><div class="t">${fmt.esc(t.name)}</div><div class="m">${t.n} 檔 · 佔比 ${fmt.n(t.share, 1)}% · 新聞 ${t.news7}</div><div class="v"><span style="color:${t.heat >= 70 ? CH.up : t.heat >= 45 ? CH.amber : CH.ink2}">熱度 ${t.heat}</span> <small class="${fmt.cls(t.chg_pct)}" style="font-size:12px">${fmt.pct(t.chg_pct)}</small></div><div class="lks">${(t.members || []).slice(0, 4).map(m => L.stock(m.code, m.name)).join('')}</div></div>`).join('') + '</div>';
  }

  // ---- 候選名單：綜合／籌碼／技術／基本面四種切法 ----------------------------
  const num = (v, d = 1) => `<span class="num">${v != null ? fmt.n(v, d) : '—'}</span>`;
  const C = {
    /* ★ 第 5 欄＝排序用的值（沒寫就用 r[key]）。
       2026-09-18 抓到：這一欄顯示的是「有 grade 就 A＋判定文字，沒有就只有判定文字」，
       但排序用 r.grade —— 380 檔裡 377 檔沒有 grade，全部同分，
       所以使用者點「判定」表頭，畫面幾乎不動（等於排序壞掉）。
       改成排「畫面上真正看到的那串字」，點了才會有反應。*/
    grade: ['grade', '判定', r => `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span>`, 'l',
      r => (r.grade ? r.grade + ' ' : 'Z ') + (r.verdict || '')],
    code: ['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'],
    name: ['name', '簡稱', r => L.stock(r.code, r.name), 'l'],
    group: ['group', '族群', r => L.group(r.group_id, r.group), 'l'],
    // data-live / data-lc 是給 live.js 認的：盤中每分鐘把這兩格換成即時價。
    // 只標記，不改算法 —— 收盤後這兩格仍然是資料湖裡的收盤價。
    close: ['close', '收盤', r => `<span class="num" data-live="close" data-lc="${r.code}">${r.close != null ? fmt.n(r.close) : '—'}</span>`],
    chg: ['chg_pct', '漲跌', r => `<span class="num ${fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${fmt.pct(r.chg_pct, 2)}</span>`],
    sAll: ['score_all', '綜合', r => num(r.score_all, 0)],
    sChip: ['score_chip', '籌碼', r => num(r.score_chip, 0)],
    sTech: ['score_tech', '技術', r => num(r.score_tech, 0)],
    sFund: ['score_fund', '基本', r => num(r.score_fund, 0)],
    tech: ['tech_score', '技術分', r => num(r.tech_score, 0)],
    rsi: ['rsi', 'RSI', r => num(r.rsi, 0)],
    bias: ['bias20', '乖離', r => `<span class="num">${fmt.pct(r.bias20)}</span>`],
    vol: ['vol_ratio', '量比', r => num(r.vol_ratio, 1)],
    stop: ['stop', '停損', r => num(r.stop)],
    rr: ['rr', '風報比', r => num(r.rr, 1)],
    pe: ['pe', '本益比', r => num(r.pe, 1)],
    pct: ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`],
    yoy: ['rev_yoy', '營收YoY', r => `<span class="num ${fmt.cls(r.rev_yoy)}">${fmt.pct(r.rev_yoy)}</span>`],
    streak: ['rev_streak', '連增月', r => `<span class="num">${r.rev_streak != null ? r.rev_streak + ' 月' : '—'}</span>`],
    mom: ['momentum_score', '動能分', r => num(r.momentum_score, 0)],
    trust: ['trust_net', '投信', r => `<span class="num ${fmt.cls(r.trust_net)}">${r.trust_net != null ? fmt.lot(r.trust_net / 1000) : '—'}</span>`],
    foreign: ['foreign_net', '外資', r => `<span class="num ${fmt.cls(r.foreign_net)}">${r.foreign_net != null ? fmt.lot(r.foreign_net / 1000) : '—'}</span>`],
    turn: ['avg_turnover', '日均量', r => `<span class="num">${r.avg_turnover != null ? fmt.yi(r.avg_turnover) : '—'}</span>`],
  };
  const HEAD = [C.grade, C.code, C.name, C.group, C.close, C.chg];
  const FACETS = {
    all: { label: '綜合', sub: '四面向加權', key: 'score_all',
      hint: '綜合分 = 技術 40% + 籌碼 30% + 基本面 30%（某一面向沒資料時，權重按比例分給其他面向）。每一列下方寫出這一檔在這個面向被挑中的實際理由。',
      cols: [...HEAD, C.sAll, C.sChip, C.sTech, C.sFund, C.pe, C.rr] },
    chip: { label: '籌碼', sub: '法人與大戶', key: 'score_chip',
      hint: '籌碼分看的是「誰在買」：投信／外資連續買超天數、法人五日淨買佔同期成交值的比例、集保大戶（400 張以上）四週持股增減、券商調升目標價。買超金額要相對於這檔自己的量才有意義，所以用佔比而不是絕對張數。',
      cols: [...HEAD, C.sChip, C.trust, C.foreign, C.turn, C.sAll] },
    tech: { label: '技術', sub: '結構與時機', key: 'score_tech',
      hint: '技術分把指標分、SMC 結構判定（A 回檔承接 / B 突破追進）、均線位置、風報比、量能與乖離合成一個分數。被硬性條件排除的（流動性不足、漲停鎖死、乖離過大）會直接扣分，理由列會寫出被排除的原因。',
      cols: [...HEAD, C.sTech, C.tech, C.rsi, C.vol, C.bias, C.stop, C.rr] },
    fund: { label: '基本面', sub: '營收與估值', key: 'score_fund',
      hint: '基本面分來自月營收動能（YoY 經 1-2 月合併調整、連增月數、近三月合計 YoY）與同族群估值分位。分位低 = 相對同業便宜。營收 YoY 超過 100% 會標示可能是併購或一次性，不當成長看。',
      cols: [...HEAD, C.sFund, C.yoy, C.streak, C.mom, C.pe, C.pct] },
  };
  let candFacet = 'all';
  let candSort = { key: null, dir: 1 };
  let candOpen = null;
  /* 族群篩選（Andy：「可勾選特定族群，下拉清單那樣，可以參考 EXCEL」）：
     null ＝ 全部；是 Set 就只看勾起來的那幾個（全部取消勾選＝什麼都不顯示，跟 Excel 一樣）。
     選擇存 localStorage，重新整理、換面向都還在。 */
  let candGroups = (() => {
    try { const v = JSON.parse(localStorage.getItem('tw.candGroups') || 'null'); return Array.isArray(v) ? new Set(v) : null; }
    catch (e) { return null; }
  })();
  const saveCandGroups = () => {
    try {
      if (candGroups) localStorage.setItem('tw.candGroups', JSON.stringify([...candGroups]));
      else localStorage.removeItem('tw.candGroups');
    } catch (e) { /* 忽略 */ }
  };

  function whyHtml(r, facet) {
    const w = (r.why || {})[facet] || {};
    const bits = (w.pros || []).map(t => `<span class="pro">✓ ${fmt.esc(t)}</span>`)
      .concat((w.cons || []).map(t => `<span class="con">！ ${fmt.esc(t)}</span>`));
    return bits.length ? `<div class="why">${bits.join('')}</div>`
      : '<div class="why"><span>這一檔在這個面向沒有明顯的理由，只是相對排名靠前</span></div>';
  }

  /* Excel 欄位篩選那種下拉：搜尋框 ＋ 全選／全部清除 ＋ 勾選清單（每個族群後面是筆數）。
     點面板以外的地方就收起來；勾一個就立刻重畫表格。 */
  function renderCandFilter(cands) {
    const host = $('#candGroupFilter'); if (!host) return;
    const counts = new Map();
    cands.forEach(r => { const g = r.group || '（未分類）'; counts.set(g, (counts.get(g) || 0) + 1); });
    const all = [...counts.keys()].sort((a, b) => counts.get(b) - counts.get(a) || a.localeCompare(b, 'zh-Hant'));
    const labelOf = (g) => !g ? '全部族群'
      : g.size === 0 ? '沒有勾選任何族群'
      : g.size === 1 ? [...g][0]
      : `已選 ${g.size} 個族群`;
    const sel = candGroups;
    host.innerHTML = `<button class="btn small ${sel ? 'on' : ''}" id="cgBtn"
        title="只看勾起來的族群（像 Excel 的欄位篩選）">族群：${fmt.esc(labelOf(sel))} ▾</button>
      <div class="cgpop" id="cgPop" hidden>
        <input id="cgSearch" placeholder="搜尋族群…" autocomplete="off">
        <div class="cgact"><button class="btn small" id="cgAll">全選</button>
          <button class="btn small" id="cgNone">全部清除</button>
          <span class="muted" id="cgCount"></span></div>
        <div class="cglist" id="cgList">${all.map(g => `
          <label data-g="${fmt.esc(g)}"><input type="checkbox" value="${fmt.esc(g)}"
            ${!sel || sel.has(g) ? 'checked' : ''}><span>${fmt.esc(g)}</span><em>${counts.get(g)}</em></label>`).join('')}</div>
      </div>`;
    const pop = $('#cgPop', host), btn = $('#cgBtn', host);
    const boxes = () => $$('#cgList input[type=checkbox]', host);
    const paintCount = () => { const n = boxes().filter(b => b.checked).length;
      $('#cgCount', host).textContent = `${n} / ${all.length}`; };
    const apply = () => {
      const on = boxes().filter(b => b.checked).map(b => b.value);
      candGroups = on.length === all.length ? null : new Set(on);
      saveCandGroups(); paintCount();
      btn.textContent = `族群：${labelOf(candGroups)} ▾`;
      btn.classList.toggle('on', !!candGroups);
      renderCandidates(cands, { keepOpen: true });
    };
    btn.onclick = (e) => { e.stopPropagation(); pop.hidden = !pop.hidden; if (!pop.hidden) $('#cgSearch', host).focus(); };
    pop.onclick = (e) => e.stopPropagation();
    $('#cgSearch', host).oninput = (e) => {
      const q = e.target.value.trim().toLowerCase();
      $$('#cgList label', host).forEach(l => { l.hidden = !!q && !l.dataset.g.toLowerCase().includes(q); });
    };
    $('#cgAll', host).onclick = () => { boxes().forEach(b => { if (!b.closest('label').hidden) b.checked = true; }); apply(); };
    $('#cgNone', host).onclick = () => { boxes().forEach(b => { if (!b.closest('label').hidden) b.checked = false; }); apply(); };
    boxes().forEach(b => b.onchange = apply);
    paintCount();
    if (!renderCandFilter._wired) {          // 點面板外面收起來，只掛一次
      document.addEventListener('click', () => { const q = document.getElementById('cgPop'); if (q) q.hidden = true; });
      renderCandFilter._wired = true;
    }
  }

  function renderCandidates(cands, opt) {
    if (!cands) return;
    if (!(opt && opt.keepOpen)) renderCandFilter(cands);
    const F = FACETS[candFacet], cols = F.cols;
    $('#candFacets').innerHTML = Object.keys(FACETS).map(k =>
      `<button data-f="${k}" class="${k === candFacet ? 'on' : ''}"><b>${FACETS[k].label}</b><em>${FACETS[k].sub}</em></button>`).join('');
    $$('#candFacets button').forEach(b => b.onclick = () => {
      candFacet = b.dataset.f; candSort = { key: null, dir: 1 }; candOpen = null; renderCandidates(cands);
    });
    $('#candHint').textContent = F.hint;

    const sk = candSort.key || F.key;
    const dir = candSort.key ? candSort.dir : -1;
    // candGroups === null ＝ 全部；是 Set 就只看勾起來的
    const pool = candGroups ? cands.filter(r => candGroups.has(r.group || '（未分類）')) : cands;
    // 先把即時值疊回去，排的才是使用者眼睛看到的那個數字
    // 這一欄有沒有自訂的「排序用的值」（cols 的第 5 欄）
    const sortCol = cols.find(c => c[0] === sk);
    const val = (r) => (sortCol && sortCol[4] ? sortCol[4](r) : r[sk]);
    const rows = liveMerge(pool.slice()).sort((a, b) => {
      const x = val(a), y = val(b);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * dir;
    });

    $('#candTable thead').innerHTML = '<tr>' + cols.map(c =>
      `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${sk === c[0] ? (dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
    $('#candBody').innerHTML = rows.slice(0, 60).map(r => {
      const tr = `<tr data-code="${r.code}">` + cols.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>';
      return r.code === candOpen
        ? tr + `<tr class="whyrow"><td colspan="${cols.length}">${whyHtml(r, candFacet)}</td></tr>` : tr;
    }).join('') || `<tr><td colspan="${cols.length}" class="l muted">勾選的族群今天沒有候選股，換幾個族群或按「全選」</td></tr>`;
    const cn = $('#candNum');
    if (cn) cn.textContent = candGroups
      ? `${rows.length} 檔（已篩 ${candGroups.size} 個族群，全部 ${cands.length} 檔）`
      : `${rows.length} 檔`;
    $$('#candTable th').forEach(th => th.onclick = () => {
      const k = th.dataset.k;
      candSort = { key: k, dir: candSort.key === k ? -candSort.dir : -1 };
      renderCandidates(cands);
    });
    // 即時層更新之後重排一次（只有正照著收盤／漲跌排序時才需要）
    onLive($('#candTable'), () => { if (LIVE_KEYS.includes(candSort.key || F.key)) renderCandidates(cands); });
    // 單擊展開「為何選它」，再點一次收起；要看個股頁用簡稱那個連結
    $$('#candBody tr[data-code]').forEach(tr => tr.onclick = (e) => {
      if (e.target.closest('a')) return;
      candOpen = candOpen === tr.dataset.code ? null : tr.dataset.code;
      renderCandidates(cands);
    });
    // 表格比容器寬時會橫向捲動，理由那一列如果跟著撐開就會被推到畫面外。
    // 把它釘在捲動容器的左邊、寬度綁住容器，理由才會在看得到的地方換行。
    const box = $('#candTable').closest('.tw');
    $$('#candBody .why').forEach(el => {
      el.style.position = 'sticky';
      el.style.left = '0';
      el.style.width = Math.max(280, box.clientWidth - 24) + 'px';
    });

    $('#candCards').innerHTML = rows.slice(0, 30).map(r => {
      const w = ((r.why || {})[candFacet] || {}).pros || [];
      return `<div class="scard" onclick="goStock('${r.code}')">
        <div class="h"><b>${fmt.esc(r.name)} <span class="mono muted">${r.code}</span></b><span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span></div>
        <div class="r"><span>${L.group(r.group_id, r.group)}</span><span class="num" data-live="close" data-lc="${r.code}">${fmt.n(r.close)}</span><span class="num ${fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${fmt.pct(r.chg_pct, 2)}</span><span>${F.label} ${r[F.key] != null ? fmt.n(r[F.key], 0) : '—'}</span></div>
        ${w.length ? `<div class="why"><span class="pro">✓ ${fmt.esc(w[0])}</span></div>` : ''}
      </div>`;
    }).join('');
  }

  /* 市場寬度：四根長條（其中兩根還常常是 0%）看不出「現在市場健不健康」。
     改成一個儀表＋一個漲跌環：儀表是站上 20 日均線的比例（多數股票在均線之上＝多頭結構），
     環是今天的漲／平／跌家數。兩個加起來才回答得了「今天是真的漲還是指數漲而已」。 */
  function renderBreadth(heat) {
    const bel0 = $('#breadth');
    // 沒資料時要把上一輪設進去的 inline 高度清掉，否則 .isempty 收不掉那個 236px 的黑方塊
    const b = heat && heat.breadth;
    if (!b) { if (bel0) { bel0.style.height = ''; bel0.style.minHeight = ''; } return empty('breadth'); }
    const p20 = b.pct_above_ma20 || 0, p60 = b.pct_above_ma60 || 0;
    const up = heat.advancers || 0, dn = heat.decliners || 0, fl = heat.unchanged || 0;
    const zone = p20 >= 70 ? '多數股票在均線之上，結構偏多' : p20 >= 45 ? '多空拉鋸，選股比押方向重要'
      : p20 >= 25 ? '偏弱，多數股票在均線之下' : '普遍破線，別急著搶反彈';
    /* ★ 2026-09-20 重排（Andy：「換一台電腦、螢幕大小不同就會影響整體變化」）。
       舊版是「儀表在左、甜甜圈在右」，而且兩個都用百分比定位
       （center: ['30%','72%'] 與 ['78%','52%']、radius '92%'）。
       實測這張卡永遠在 g3 的 1/3 欄裡，容器寬度只有 300～520px ——
       一分為二之後每邊不到 260px，「儀表的半徑」加上「甜甜圈往外拉的引線標籤」
       在物理上放不下，所以不是「窄的時候才壞」，是**每一個寬度都壞**：
       1440px 量到儀表的弧線已經超出容器左緣與下緣、「100」那個刻度掉到框外 19px。
       所以不是改成「窄的時候上下排」，是**一律上下排**，而且位置全部寫成 px：
         上半＝站上 20 日均線的儀表（半徑 px 固定）
         下半＝漲／平／跌的堆疊長條（取代甜甜圈）
       甜甜圈換成堆疊長條的理由：漲平跌是「一個總量的三塊」，堆疊長條本來就比環圈好讀，
       而且標籤寫在色塊裡面、不需要引線 —— 引線正是舊版壓到儀表的那個東西。
       容器高度也寫死 px，這樣 1280 跟 1920 畫出來完全一樣。 */
    const bel = bel0;
    const BH = 236;                    // 儀表 + 長條的總高（px，不隨寬度變；量過：弧線 38～146、長條 182～208）
    // minHeight 也要一起設：HTML 上那個 min-height:250px 會蓋過 height，
    // 只設 height 的話下緣會多出 14px 的空白（量過）
    if (bel) { bel.style.height = BH + 'px'; bel.style.minHeight = BH + 'px'; }
    const tot = Math.max(up + fl + dn, 1);
    // 色塊太窄就不寫字（寫了一定壓到隔壁）；數字在下面那排 pill 與 tooltip 裡都還看得到
    const segLabel = (name, v, col) => ({
      name, type: 'bar', stack: 'ad', barWidth: 26,
      itemStyle: { color: col }, emphasis: { disabled: true },
      label: { show: v / tot >= 0.14, position: 'inside', color: '#0b1022', fontSize: 11.5, fontWeight: 700,
        formatter: () => `${name} ${v}` },
      data: [v],
    });
    chart('breadth', {
      tooltip: { ...tip, trigger: 'item', formatter: q => q.seriesType === 'bar'
        ? `${q.seriesName} <b>${q.value}</b> 檔（${fmt.n(q.value / tot * 100, 1)}%）`
        : `站上 20 日均線 <b>${fmt.n(q.value, 1)}%</b>` },
      grid: { left: 12, right: 12, top: 182, height: 26 },
      xAxis: { type: 'value', max: tot, show: false },
      yAxis: { type: 'category', data: [''], show: false },
      series: [
        { type: 'gauge', startAngle: 200, endAngle: -20, min: 0, max: 100, radius: 80, center: ['50%', 118],
          progress: { show: true, width: 13, roundCap: true,
            itemStyle: { color: p20 >= 60 ? '#ff4d6d' : p20 >= 40 ? '#ffb454' : '#2ee59d' } },
          axisLine: { lineStyle: { width: 13, color: [[1, CH.grid]] } },
          axisTick: { show: false }, splitLine: { show: false },
          // 刻度數字拿掉：0 與 50 都被弧線蓋住，只剩右邊孤零零一個「100」，是雜訊不是資訊
          axisLabel: { show: false },
          pointer: { show: false },
          anchor: { show: false },
          title: { show: true, offsetCenter: [0, 32], color: CH.ink3, fontSize: 11.5 },
          detail: { valueAnimation: true, offsetCenter: [0, -4], fontSize: 26, fontFamily: 'JetBrains Mono',
            fontWeight: 700, color: theme() === 'light' ? CH.ink : '#e8eeff', formatter: v => v.toFixed(1) + '%' },
          data: [{ value: p20, name: '站上 20 日均線' }] },
        segLabel('上漲', up, '#ff4d6d'),
        segLabel('平盤', fl, '#6f7ea3'),
        segLabel('下跌', dn, '#2ee59d'),
      ],
    }, { notMerge: true });
    // 圖下面一行把「還有什麼可以看」補上，不用再畫兩根 0% 的長條。
    // 漲／平／跌三個數字一定要在這裡各出現一次 —— 長條裡的字會因為色塊太窄被關掉。
    linkRow('breadth', `<span class="pill ${p20 >= 50 ? 'up' : 'down'}">${zone}</span>`
      + `<span class="pill up">漲 ${up}</span><span class="pill">平 ${fl}</span><span class="pill down">跌 ${dn}</span>`
      + `<span class="pill">MA60 ${fmt.n(p60, 1)}%</span>`
      + `<span class="pill">60 日新高 ${b.new_high_60 ?? 0} 檔</span>`
      + `<span class="pill">樣本 ${b.n ?? 0} 檔</span>`
      + `<a class="pill cyan" href="#market/ma">看各族群 →</a>`);
  }

  /* 投信連續買超：長條圖只講得出「買幾天」，講不出「買多少」。
     改成氣泡圖：橫軸＝連續天數、縱軸＝這段期間累計買超張數、泡泡大小＝累計張數。
     右上角那幾顆才是真的在收貨（買得久而且買得多），只買一天大單的不會跑到右邊。 */
  /* 法人連續買超。Andy 2026-09-15：「圖表可以縮放，並且可以游標抓取移動，
     還能切換買超週期 不限只有3天，還要加上外資買超，以及綜合」。
     三種法人的資料在 `inst_streak`（投信/外資/合計各一份，門檻放寬到 2 天由前端篩）；
     舊的 `trust_streak` 留著當退路，換版當下不會開天窗。 */
  const streakState = { who: 'trust', days: 3 };
  const STREAK_NAME = { trust: '投信', foreign: '外資', total: '三大法人合計' };

  function renderTrust(trust, cands) {
    const all = D.inst_streak || {};
    const src = (all[streakState.who] && all[streakState.who].length)
      ? all[streakState.who]
      : (streakState.who === 'trust' ? (trust || []) : []);
    const rows0 = (src || []).filter(r => (r.streak_days || 0) >= streakState.days);
    const sub = $('#streakSub');
    if (sub) sub.textContent = `${STREAK_NAME[streakState.who]} ≥${streakState.days} 天 · ${rows0.length} 檔`;
    if (!rows0.length) {
      empty('trust', `${STREAK_NAME[streakState.who]}目前沒有連續買超 ${streakState.days} 天以上的股票`);
      linkRow('trust', '');
      return;
    }
    const names = {}; (cands || []).forEach(c => { names[c.code] = c.name; });
    const nm = (code) => names[code] || L.cname[code] || code;
    const rows = rows0.slice(0, 40).map(r => ({ ...r, lots: (r.accumulated || 0) / 1000 }));
    const maxLots = Math.max(...rows.map(r => Math.abs(r.lots)), 1);
    const maxDay = Math.max(...rows.map(r => r.streak_days || 0), streakState.days + 1);
    /* ★ 2026-09-20（Andy 截圖：「玉山金」的標籤跑到圖框外面被卡片切掉）。
       量到的比他看到的更糟：1440px 下這張圖裡有 56 組文字互相重疊 ——
       40 顆泡泡全部標名字，塞在 184px 高的畫布裡，底下那一排小泡泡的名字疊成一團黑。
       以前看不到是因為圖是 canvas 畫的、那些字在 DOM 上不存在
       （所以 `_preview.py` 永遠報「重疊 0 筆」）。
       兩道修正：
         1. 只標「真的在收貨」的前 10 名（累計張數）。其餘的名字在 tooltip 裡，
            滑過去就看得到 —— 不是把資訊拿掉，是不要在 184px 裡塞 40 個名字。
         2. labelLayout 改成函式，把標籤夾回容器內（玉山金那一顆就是被夾回來的），
            並且開 hideOverlap 讓剩下真的撞在一起的自己讓位。 */
    const host = $('#trust');
    const labelled = new Set(rows.slice().sort((a, b) => Math.abs(b.lots) - Math.abs(a.lots))
      .slice(0, 10).map(r => r.code));
    const clampLabel = (p) => {
      const W = (host && host.clientWidth) || 300, H = (host && host.clientHeight) || 250, L = p.labelRect;
      let dx = 0, dy = 0;
      if (L.x + L.width > W - 3) dx = (W - 3) - (L.x + L.width);
      if (L.x + dx < 3) dx = 3 - L.x;                  // 兩邊都超出時以靠左為準（左邊是軸，比較不容易被切）
      if (L.y + L.height > H - 3) dy = (H - 3) - (L.y + L.height);
      if (L.y + dy < 3) dy = 3 - L.y;
      return { dx, dy, hideOverlap: true };
    };
    const c = chart('trust', {
      tooltip: { ...tip, formatter: q => `<b>${q.data.nm} ${q.data.code}</b><br>${STREAK_NAME[streakState.who]}連續買超 <b>${q.value[0]}</b> 天<br>期間累計 <b>${fmt.lot(q.value[1])}</b><br>${q.data.g ? fmt.esc(q.data.g) + '<br>' : ''}<small>點一下進個股頁</small>` },
      /* top 從 26 加到 46：最大的泡泡直徑可到 40px，它又一定落在 y 軸頂端，
         標籤寫在泡泡上方時就會被推到容器外（玉山金那一顆量到 -5px）。
         labelLayout 的 dx/dy 在這裡沒有把它夾回來（實測第一次 render 不生效，
         第二次 setOption 才生效），與其研究那個機制，不如直接把空間留出來 ——
         46 = 泡泡半徑 20 + 標籤高 12 + 上方留白 14，算得出來、不依賴任何機制。 */
      grid: { left: 62, right: 22, top: 46, bottom: 40 },
      /* 縮放與平移不用 ECharts 的 dataZoom，用全站那一套 wheelZoom（見下面的 renderTrust 呼叫）。
         dataZoom 的 inside 會把 wheel 事件吃掉，滑鼠停在圖上就捲不動頁面 ——
         那正是 Andy 09-13 抱怨過、要我把其他圖的縮放拿掉的原因。
         wheelZoom 在 1 倍時把 wheel 交還給頁面，放大後才攔，而且有「拖曳移動 · 雙擊還原」的徽章。 */
      xAxis: { ...axisStyle, name: '連續買超天數 →', nameLocation: 'middle', nameGap: 24,
        nameTextStyle: { color: CH.ink3, fontSize: 11 },
        min: Math.max(0, streakState.days - 1), max: maxDay + 1, splitLine: { show: false } },
      yAxis: { ...axisStyle, name: '累計張數 ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 },
        scale: true, axisLabel: { formatter: v => fmt.lot(v) } },
      series: [{ type: 'scatter',
        data: rows.map(r => { const gid = L.cgroup[r.code];
          return { value: [r.streak_days, +r.lots.toFixed(0)], code: r.code, nm: nm(r.code), g: L.gname[gid],
            symbolSize: Math.max(10, Math.min(40, Math.sqrt(Math.abs(r.lots) / maxLots) * 40)),
            itemStyle: { color: L.gcolor[gid] || '#ffb454', opacity: .85, borderColor: CH.panel, borderWidth: 1 } }; }),
        /* 標籤加一塊半透明底板：泡泡很密的時候名字一定會落在別人的泡泡上，
           有底板才讀得出來（沒底板就是 Andy 截圖裡那種深色字壓在深色圓上）。
           底板也讓 hideOverlap 量到的框變大，該讓位的會自己讓。*/
        label: { show: true, formatter: q => (labelled.has(q.data.code) ? q.data.nm : ''),
          position: 'top', color: CH.ink, fontSize: 11,
          backgroundColor: hexA(CH.panel, .78), padding: [1, 4], borderRadius: 4 },
        labelLayout: clampLabel }],
    }, { notMerge: true });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.code) goStock(q.data.code); });
    // Andy 2026-09-15：「圖表可以縮放，並且可以游標抓取移動」——
    // 跟資金熱力圖同一套：滾輪放大、放大後拖曳、雙擊還原，1 倍時滾輪照常捲頁面
    wheelZoom($('#trustWrap'), { onZoom: () => { const i = echarts.getInstanceByDom($('#trust')); if (i) i.resize(); } });
    linkRow('trust', rows.slice(0, 12).map(r => L.stock(r.code, nm(r.code))).join(''));
  }

  function wireStreak(trust, cands) {
    $$('#streakWho button').forEach(b => b.onclick = () => {
      $$('#streakWho button').forEach(x => x.classList.toggle('on', x === b));
      streakState.who = b.dataset.w; renderTrust(trust, cands);
    });
    const sel = $('#streakDays');
    if (sel) { sel.value = String(streakState.days);
      sel.onchange = () => { streakState.days = +sel.value; renderTrust(trust, cands); }; }
  }

  /* ★ 2026-09-23（Andy：「估值篩選拿掉」，追問後回覆「OK」＝連總覽這張也一起砍）：
     總覽的「族群估值」散布圖（`#gval` / `renderGval`，族群本益比中位 × 資金流入）已整塊移除，
     連同它的卡片、族群篩選晶片，以及唯一讀 `group_valuation.json` 的那次 `load()`。
     原因是「貴不貴」這條線在這份儀表板上已經由資金流向頁的排行與輪動時鐘回答，
     而本益比中位跨族群比較本來就沒有意義（DECISIONS #13：絕不跨族群比 PE），
     圖上四個象限反而在鼓勵那種比較。資料端照舊產出，只是前端不再有人讀。 */
  // ---------------------------------------------------------------- 資金流向
  // ================================================================ 資金流向頁
  // Andy 的要求：「需要有趨勢 好比說上週 上上週 上個月等等 可以查到不同時期 資金走向為何」
  //             「右側本益比需要多可篩選功能 全部在一起」「也需要附上說明怎麼觀看」
  // 所以整頁由上方一個期間切換列統一控制「什麼時候」，每張圖都有一顆「怎麼看」。
  const HOW = {
    /* ★ 2026-09-21：HOW.rank 整段刪掉，內容併進 HOW.rot（兩張圖合併成一張卡，
       只留一顆「怎麼看 ?」）。留著不會被叫到，就是死碼。*/
    bump: `<b>這張圖回答：主流是穩穩的還是一直換人。</b>
      <ul><li>每條線是一個族群，<em>位置越高＝成交值排名越前面</em>（1 名在最上面）。</li>
      <li>線一路往上＝資金連續好幾週往它集中，通常比單週衝上來的更值得跟。</li>
      <li>線上下亂跳＝那一段時間在輪動，沒有明確主流，追高容易兩面挨巴掌。</li>
      <li>滑鼠移上去看每一週的實際佔比；點線上的點可以進該族群。</li></ul>`,
    /* ★ 2026-09-21 合併之後，這一段同時是「輪動時鐘」與「資金流向排行」的說明
       （原本 HOW.rank 那一段併進來了）—— 同一張卡不該有兩顆問號鈕。
       開頭先把兩張圖各自回答什麼講清楚，再講怎麼一起用：
       Andy 的標準是「每張圖都要能回答一個具體問題，而且說明要寫到『所以我該怎麼用』」。*/
    rot: `<b>這張卡回答兩件事：<em>錢這幾天往哪個族群跑</em>（右邊的排行），
        以及<em>那個族群跑到強弱循環的哪一段</em>（左邊的時鐘）。</b>
      <ul><li><b>兩張圖吃同一份設定</b>：上面那兩個下拉清單（先挑<em>產業鏈</em>，
        再從第二個清單勾<em>族群</em>，可複選）與「只看前 10 大」是**共用**的，
        改一次兩張圖一起篩。</li>
      <li><b>時間只有一條桿（兩個把手）</b>：<em>青色的右把手＝看哪一天</em> ——
        它同時決定時鐘大圈落在哪一天、以及排行那一段的結尾是哪一天，所以兩張圖永遠在講同一天的事；
        <em>灰色的左把手＝這一段的起點</em>，兩個把手之間的距離就是排行往回看幾個交易日。
        桿子右邊寫著「最近 12 天 · 截止 5 天前」，那就是你現在看的那一段。
        <b>怎麼用</b>：想看「最近這一段誰在吸金」就把右把手推到底（＝最新），用左把手決定要看多久；
        想回放某一天就拖右把手，或按 <em>▶</em> 讓整段自己往「最新」滑。
        <em>＋ −</em> 是整段前後各挪一個交易日（長度不變）。
        ⚠ 兩個把手在同一根 0～30 的軸上，所以最遠看到 30 個交易日前 ——
        時鐘的軌跡本來就只有 31 天，再往前只有排行看得到、時鐘看不到。</li>
      <li><b>怎麼一起用</b>：先看右邊排行最上面那幾個（錢正在進去），
        再到左邊時鐘找同一個名字 —— <em>錢在進、而且位置在「改善」或「領先」</em>的才值得追；
        錢在進但還卡在「落後」的，多半是單日題材。</li>
      <li><b>（排行）</b>長條長度＝這個族群的<em>成交值佔比變化</em>（和上一段同樣長度的期間比），
        單位是百分點 pp。<em>紅色向右</em>＝資金流進來，<em>綠色向左</em>＝資金退出去。
        只看金額會被大盤量能帶著走，所以看佔比。名字後面的 <em>3 ↑</em> 是成交值排名進步了 3 名；
        長條右邊那個百分比是這段期間的族群報酬。<b>點長條</b>會在下面列出它的成分股，
        同時左邊的時鐘只亮這一個族群。</li>
      <li><b>四周那四顆卡片（改善／領先／轉弱／落後）就是以前圖下方的「輪動階段」</b>：
        卡片上的數字＝現在落在那一段的族群有幾個，<em>點一下就在時鐘<b>右邊</b>那塊空白列出是哪幾個</em>
        （附強弱、動能、佔比；畫面窄的時候改列在時鐘下面），
        再點族群名稱會在右邊排行下面展開它的成分股。再點卡片一次收起來。
        每一列如果最近 5 個交易日換過段，名字旁邊會有「改善→領先」這種徽章。
        盤中開著「即時」時，這四顆卡片算的是<b>續算後</b>的位置，和盤上的點同一個口徑。</li>
      <li><b>先看那個圓盤（資金輪動時鐘）</b>：圓盤切成四塊，就是循環的四段。
        一顆點是一個族群，<em>點落在哪一塊＝現在在哪一段</em>；點越大＝成交值佔比越高。</li>
      <li>資金照<em>順時針</em>一塊一塊跑：落後（左下）→ 改善（左上）→ 領先（右上）→ 轉弱（右下）→ 回落後。
        點後面那條尾巴是牠這幾天走過的路，尾巴往前拉＝正在往下一段前進，往回縮＝走回頭路。</li>
      <li><em>離圓心越遠＝和大盤差距越大</em>；擠在圓心附近就是跟大盤差不多，沒特色。
        盤面上兩圈虛線由內而外是「今天最大偏離的一半」與「今天偏離最大的那個族群」——
        所以<b>今天的畫面上剛好有一個族群踩在最外圈</b>，其他人都在它裡面。
        這把尺是<em>鎖在今天</em>的，往回刷時間軸時不會變，所以看得出那一天大家離大盤更近還是更遠；
        <em>跑到外圈虛線外面</em>的，就是那一天比今天任何族群都還偏離大盤的。</li>
      <li><b>只想看某幾個族群</b>：點圖上方那一排族群名稱（就在「全部／半導體／…」那一排的正下方），
        可多選、再點一次取消，<em>時鐘與右邊的資金流向排行會一起跟著篩</em>。</li>
      <li><b>回放</b>：「看哪一天」拖到幾天前，按 <em>▶</em> 就會一天 0.42 秒等速播回今天，
        軌跡是「走到哪畫到哪」；右上角「⤢ 放大」可以整張放大來看，控制項完全一樣。</li>
      <li><b>按「即時」就換一種讀法</b>：時間軸旁邊那顆「即時」會用<em>當下的成交價與成交量</em>
        把每個族群往前續算一步，每分鐘更新一次。圖上每個族群多出一條線，而它<b>刻意分成兩段</b>：
        <em>灰色虛線</em>（從空心小圈出發）＝<b>慣性</b> —— 這張圖的 x 是「10 日 EMA 相對 40 日均線」，
        就算今天完全平盤，那條均線的窗口也會往前滾一天，所以點本來就會走
        （實測中位 0.59 點，比「贏大盤 2%」還多）；<em>亮色粗箭頭</em>
        （針身是亮色、外圈是族群的階段色，終點有一圈漣漪在動）
        ＝<b>今天的成交價與成交量真正推出來的那一段</b>。
        所以<b>怎麼用</b>：<em>只看亮色那一段</em> —— 它朝「改善／領先」那半邊指，就是盤中有人在買；
        朝「轉弱／落後」指，就是在被賣。<em>跨過象限的那幾個會發光</em>，那是今天最值得看的事件。
        <b>亮色那段很短是正常的</b>（贏大盤 2% 也只有 0.35 點、畫面上 4～5 個像素，而整盤分布有 16 點）——
        我們<em>沒有把位移放大</em>，要比較誰被推得多就看圖下方那一排數字（每一顆都點得進成分股）。
        ⚠ 兩件事一定要知道：族群成交值是用「價 × 量」<em>估</em>的（漲跌幅是真的），
        而且盤中只抓得到人工族群那批股票，所以<em>「大盤」是代理值</em> ——
        涵蓋台股總成交值的百分之幾就寫在狀態列上。拖時間軸就會自動退出即時（兩者互斥）。</li>
      <li>族群跟著大盤轉，順序幾乎都是 <em>改善 → 領先 → 轉弱 → 落後 → 再回改善</em>。</li>
      <li><em>改善</em>：還比大盤弱，但動能已經轉強 —— 資金剛進場，這是最早可以布局的一段。</li>
      <li><em>領先</em>：現在的主流。回檔找買點，別追高，因為下一站是轉弱。</li>
      <li><em>轉弱</em>：還是比大盤強，但動能在掉。手上有的先設好停利。</li>
      <li><em>落後</em>：資金還在跑，別急著抄底，等它走到改善再說。</li>
      <li>名字後面的 <em>↑↓</em> 是動能的方向、「強弱」是相對大盤多少（0 就是跟大盤一樣）。</li>
      <li>最上面那條「換階段的族群」才是重點 —— 已經在領先的你早就知道了，<em>剛從落後轉進改善的</em>才是新機會。
        上面的鈕可以改成和 10 天或 20 天前比。</li>
      <li><b>看完族群要往下看個股：點盤上任何一顆點</b>（或下方那排族群名稱），
        右邊就會列出它的成分股（依成交值排序）。<em>再點清單裡的名字，那一檔就會被畫到同一張盤上</em>，
        族群是實心圓、個股是<em>空心圓＋虛線尾巴</em>，可以多選、再點一次拿掉。</li>
      <li>怎麼用這一層：族群在「改善」不代表裡面每一檔都在改善。
        把成交值最大的兩三檔叫上盤面，<em>落在族群外圈同一段的那幾檔＝真正帶著族群跑的人</em>，
        還縮在圓心或落在別段的，就是搭順風車、跟不上的。要買的是前者。</li>
      <li>回到只看族群：按面板左上的「‹ 全部族群」、「收起 ✕」，或直接按 <em>ESC</em>。</li></ul>`,
    rotm: `<b>族群現在跑到強弱循環的哪一段。</b>
      <ul><li>順序是 <em>改善 → 領先 → 轉弱 → 落後</em>，然後再回改善。</li>
      <li><em>改善</em>＝資金剛進場，最早可以布局；<em>領先</em>＝現在的主流，回檔找買點；
        <em>轉弱</em>＝動能在掉，設好停利；<em>落後</em>＝別急著抄底。</li>
      <li><em>圓心</em>＝這段時間跟大盤走得一樣；<em>越往外</em>＝相對強弱與動能偏離大盤越多。
        兩圈虛線由內而外是「偏離程度的一半」與「偏離最大的那個族群」。</li>
      <li>右上角「⤢ 放大」可以放大，放大後才有天數拉 Bar、族群篩選與回放。</li>
      <li>完整的版本（含「誰剛換階段」）在「資金流向」分頁。</li></ul>`,
    mkt: `<b>這一頁是總覽上方那排數字的完整名單。</b>
      <ul><li><em>漲跌家數</em>：漲停通常是題材發動的第一天；跌停要看是個股利空還是整個族群一起倒；
        成交值前段才是今天真正的戰場。</li>
      <li><em>站上均線</em>：大盤那個百分比拆到族群，才知道是哪幾個在撐、哪幾個在拖。</li>
      <li><em>資金集中</em>：前幾大族群吃掉多少量；越集中，冷門股越不容易動。</li>
      <li><em>今日候選</em>：A 回檔承接、B 突破追進；沒有 A/B 的日子列綜合分前段當觀察名單。</li>
      <li><b>「⚡ 即時」鈕</b>（漲跌家數那一頁最上面）：把漲跌家數與漲跌分佈換成<em>現在這一刻</em>的樣子。
        <b>怎麼用</b>：盤中想知道「現在是普漲還是只有權值股在漲」就按它，看分佈的重心偏左還偏右；
        要看今天收盤的全貌就切回「盤後」。
        <b>三件一定要先知道的事</b>：① 它<em>不是全市場</em> —— 即時報價逐檔打，只抓「有人工分族群」的
        成分股聯集（約 440 檔，全市場 2300 多檔），涵蓋率印在鈕的下面；
        ② 這一批<em>偏中大型、偏電子</em>，所以分佈會比全市場窄，別當成全市場的縮影；
        ③ <em>漲跌幅是真的</em>（現價 vs 昨收），但<em>成交值是估的</em>（現價 × 累計張數），
        所以「成交值前段」那一格的金額和盤後那一版不是同一個東西。
        非盤中按下去畫的是最後一次報價的快照。</li>
      <li>每一列都點得進個股頁，族群名稱點得進族群頁。</li></ul>`,
    heat: `<b>這張圖回答：今天的錢集中在哪些族群。</b>
      <ul><li>方塊<em>大小</em>＝這個族群吃掉多少成交值，方塊<em>顏色</em>＝資金在流入（紅）還是流出（綠），
        看的是 5 日佔比減 20 日佔比，不是今天的漲跌。</li>
      <li>所以會出現「紅方塊但今天收綠」——那代表股價在回檔，但錢還在往裡面放。</li>
      <li>上面那排可以只看一條產業鏈，小方塊就會變大、看得清楚；點方塊直接看成分股。</li></ul>`,
    sankey: `<b>這張圖回答：這一天的量最後流進了誰的口袋，以及它比前一天變多還是變少。</b>
      <ul><li>由左到右<em>四層</em>：台股成交值 → <b>產業鏈</b> → 族群 → 當天量最大的代表股。
        半導體的 IC 設計／晶圓代工／封測是同一條鏈上的三個環節，所以掛在<em>同一個「半導體」節點</em>底下，
        不跟法定產業別的收容桶（半導體業、電子零組件業、ETF…）並排 —— 那些歸在「其他產業別」。</li>
      <li><b>每一層的 % 都是「佔它上一層」的比重</b>：產業鏈的 % 是佔全場，
        族群的 % 是佔它那條產業鏈，代表股的 % 是佔它那個族群。
        所以「台積電 49.8%」讀作「台積電吃掉晶圓代工的一半」，不是佔全台股一半。
        滑鼠移上去的小框裡兩種分母都寫（佔上一層、佔全場），還會寫出比前一天增減多少。</li>
      <li><em>圓圈越大、線越粗＝錢越多</em>，線上小圓點的<em>密度</em>也是同一件事；
        <em>三段線都會跑點</em>，一眼看得出錢是一路傳到哪一檔股票。
        節點名字後面的 <em>▲▼</em> 是和前一天比的增減（紅增綠減）。</li>
      <li><em>回放時位置固定不動</em>，換日期只會改粗細與大小 ——
        所以<b>怎麼用</b>：拖「看哪一天」往回走（或按 ▶ 一天一天播），盯住<em>同一個位置</em>的那條線，
        它變粗就是錢在往這個族群集中，變細就是在退場；灰掉寫「無資料」的是那天完全沒量。</li>
      <li><b>按「即時」就換一種讀法</b>：那一刻起產業鏈與族群<em>會依當下成交值重新排名、名次變了就換位</em>
        （每分鐘一輪，有補間動畫；名次沒變就完全不動）。
        所以<b>怎麼用</b>：盯著<em>往上爬</em>的那一格 —— 回放看的是「這 60 天誰一直在變粗」，
        即時看的是「現在這一刻誰突然插隊」，那才是盤中要抓的東西。
        自動桶（〇〇・其他）抓不到即時，一律標「盤後」、排在最後、不進分母。</li>
      <li>大小是跟<em>這 60 天的最大值</em>比，不是跟當天的第一名比 ——
        所以整排一起變細，代表的是大盤量縮，不是族群輪動。</li>
      <li><b>點族群</b>（圖上的圓圈或下面那排晶片）＝<em>水流就地延伸</em>：
        原本只畫前 3 大代表股，點下去會展開成<em>該族群全部成分股</em>（名字 ＋ 佔這個族群的 %），
        右邊同時列出成交值排序、圖上其餘壓暗；再點一次、點背景或按 ESC 收回。
        成分股超過 20 檔的（實務上只有 ETF 那一格）只畫前 20，
        自動桶（「〇〇・其他」、ETF 這種收容桶）<b>不展開</b> —— 它們是「沒有被歸進任何族群的股票」，
        攤開幾百檔讀不出東西；點它一樣會開右邊的清單。
        所以<b>怎麼用</b>：展開之後比的是「這個族群的錢是集中在一兩檔，還是整排都在動」——
        前者是單一公司的事，後者才是族群輪動。
        <b>點產業鏈</b>＝只看那一條鏈；晶片名字右邊的 → 是進族群頁。</li>
      <li><b>右邊清單裡再點個股的名字，那一檔就會掛到它族群底下變成一個新的葉節點</b>
        （邊框比較亮、線是虛線，和固定那三檔代表股分得出來），可以多選、再點一次拿掉；
        這份選擇和左邊的輪動時鐘是<em>同一份</em>，所以兩張圖會一起變。
        每一列最右邊的 <b>→</b> 才是進個股頁。</li>
      <li>怎麼用這一層：固定只畫前 3 大代表股，看不出第 4～10 名在不在吸金。
        <em>把你關心的那幾檔叫出來，看它的線有沒有比代表股粗</em> ——
        粗就是錢其實正在往它集中，只是排名還沒輪到它。</li>
      <li><b>點產業鏈那一格</b>（例如「AI 伺服器」）＝右邊列出<em>它底下所有族群</em>，依成交值排序、
        寫出佔這條鏈多少與今天漲跌；每一列都能<em>就地展開</em>看成分股，展開後點個股就進個股頁，
        最右邊的 <b>◎</b> 是「圖上只看這個族群」。
        <b>怎麼用</b>：先用產業鏈那一欄挑出今天最吸金的那條鏈，再往下看錢集中在鏈上的哪一段
        （例如 AI 伺服器的錢是跑到組裝，還是跑到散熱與電源），最後才看是哪幾檔在吃。</li>
      <li>回到上一階：按面板左上的麵包屑（從鏈點進族群時它會寫「‹ AI 伺服器」，<em>一次只退一階</em>）、
        「收起 ✕」、按 <em>ESC</em>，或直接<b>點圖上的空白處</b> —— 四個入口是同一件事。</li>
      <li><b>「即時」鈕</b>（拉Bar 那一排最右邊）＝切到盤中即時。切下去之後：
        <em>手寫板塊每分鐘更新</em>，成交值是「最後成交價 × 累積成交張數」的<b>估算值</b>
        （即時端點沒有每檔的累積成交金額；雙掛兩個板塊的股票已照 1/n 拆分）；
        <em>「〇〇・其他」自動桶做不到</em>（光 ETF 一格就 358 檔），一律標<b>盤後</b>、
        而且<b>不進佔比的分母</b> —— 拿盤中的半天成交值去跟收盤的整天成交值比，
        自動桶會被灌成第一名。最上面那一格的「台股總成交值」是證交所的<b>真實值</b>（不是估算），
        但它只作展示，<em>% 的分母是「所有即時板塊加總」</em>。
        非盤中（現貨 09:00–13:30 以外）按下去會明講「現在不是盤中」，畫的是最近一次的報價快照。
        <b>怎麼用</b>：盤中想知道「今天的錢正在往哪跑」就按它，看哪一條鏈的線比它平常的位置更粗；
        要看歷史就拖時間軸（一拖就自動退出即時）。</li></ul>`,
    inst: `<b>這張圖回答：這段時間法人把錢放在哪裡。</b>
      <ul><li>三段堆疊分別是外資、投信、自營，<em>向右＝買超、向左＝賣超</em>（單位張）。</li>
      <li><em>投信</em>的錢比較黏（有作帳壓力、不太會隔天就跑），連續買超的族群參考價值比外資單日大買高。</li>
      <li>跟著上方期間切換一起變；點任一列看成分股。</li></ul>`,
    conc: `<b>這張圖回答：現在是「少數股票撐盤」還是「雨露均霑」。</b>
      <ul><li>線＝前幾大族群吃掉多少成交值，虛線是它的 20 日平均。</li>
      <li><em>往上＝縮圈</em>，行情集中在少數主流，這時候買冷門股很容易不會動。</li>
      <li><em>往下＝擴散</em>，通常是輪動或補漲，這時候主流反而容易休息。</li>
      <li>前 5 大看「主流有多獨」，前 10 大看「主流圈子有多大」；兩條走勢分岔時是換主流。</li></ul>`,
  };
  function wireHowto(root) {
    $$('.howbtn', root || document).forEach(b => b.onclick = () => {
      const box = $('#how-' + b.dataset.how); if (!box) return;
      const open = box.hidden;
      if (open && !box.dataset.filled) { box.innerHTML = HOW[b.dataset.how] || ''; box.dataset.filled = '1'; }
      box.hidden = !open; b.classList.toggle('on', open);
      b.textContent = open ? '收起說明' : '怎麼看 ?';
      Object.values(charts).forEach(c => c && c.resize && c.resize());
    });
  }

  /* ★ 2026-09-21（合併成一張卡之後才浮出來的舊毛病）：`back` 一直被當成兩件事用 --
     `renderRotation(rrg, back, ...)` 裡它是**窗長**（「最近 N 個交易日換階段的族群」），
     而同一個值又被餵給 `frame`（**大圈停在哪一天**）。兩件事方向一樣、意思不一樣。
     以前看不出來，是因為排行永遠顯示最新一天、各看各的；
     現在排行跟著「看哪一天」走，預設 5 就會讓**整張卡一打開就停在 5 個交易日前**
     （截圖實測：最新交易日 2026-09-18，卡片卻寫「回放 2026-09-11」）。
     所以拆開：
       - `flowState.back` 只剩「看哪一天」（＝ rotFrame），預設 ROT_MIN_BACK＝最新一天
       - 輪動階段看板的比較窗長獨立成 ROT_BOARD_WIN，固定 5 天，不隨時間軸變
     看板上寫的字本來就是「最近 5 個交易日換階段的族群」，固定成 5 反而跟文案對得上。*/
  const ROT_BOARD_WIN = 5;         // 輪動階段看板：和幾個交易日前比（窗長，與「看哪一天」無關）
  let flowState = { period: 'w0', back: 0, concTop: 5 };
  async function renderFlow() {
    // groups_detail：輪動板點族群要原地展開成分股（Andy 2026-09-18 圖五），這頁也要先載
    const [f3, conc] = await Promise.all([load('flow_v3'), load('concentration'), load('groups_detail')]);
    wireHowto($('#v-flow'));

    /* ★ 2026-09-20（Andy 拍板「合併：只留拉 Bar」）
       原本這裡會依 f3.periods 畫一列期間鈕（本週／上週／…／近三月），
       而排行與法人的拉 Bar 又各自有一個 0＝「跟著上方期間走」——
       **同一頁兩套選時間的方式，互相抵觸**，使用者看不出現在到底在看哪一段。
       現在時間全部由每張圖自己的拉 Bar 決定，兩支拉 Bar 的下限也從 0 改成 1
       （0 已經沒有意義了）。日期範圍寫在各自的副標裡，資訊沒有消失。
       f3.periods 後端照樣產出，之後若要做「快速跳到本月／近三月」再接回來就好。 */
    let instDays = null;   // ★ D1：rankDays 已併進 rotBackBar（雙把手區間桿），不再是獨立的一支
    const DEFAULT_DAYS = 20;   // 約一個月的交易日；以前 0（跟著上方期間）的替代預設值
    const drawPeriod = () => {
      drawRankDays(rankVal());
      drawInstDays(instDays ? Math.max(1, +instDays.value || DEFAULT_DAYS) : DEFAULT_DAYS);
    };
    /* 圖四（Andy 2026-09-18：「資金流向排行需要跟資金輪動一樣以拉Bar 形式呈現，
       並且一樣的設計，也是可以選時間週期拉Bar 1-30 天」）。
       0 保留成「跟著上方期間走」，跟 I1 同一套語彙。
       比較基準是「再往前同樣長度的一段」，所以後端 share_daily 給 60 天（拉滿 30 天時剛好夠）。*/
    /* ★ 2026-09-21（Andy：「這兩張圖合併，共用同個篩選資訊 週期 分類等等」）。
       「共用週期」的實質不只是把兩排篩選併成一排，而是**排行也要吃「看哪一天」**：
       以前時鐘刷到「20 天前」、排行卻永遠結尾在最新一天，兩張圖並排看起來像同一段時間，
       其實差了 20 天 —— 那是最糟的一種誤導（看得懂但看錯）。
       資料撐得住：`share_daily` 有 60 天的逐日欄位，`rrg.points[].trail` 有 31 天，
       兩邊最後一天是同一天，所以**用日期字串對**（不要用索引減法，兩份資料長度不一樣）。 */
    const rotFrameDate = () => {
      const t = (((f3 && f3.rrg && f3.rrg.points) || [])[0] || {}).trail || [];
      if (!t.length) return null;
      // 和 renderRotClock 的 atFrame() 同一條公式：frame 允許小數，取 floor 才對得上大圈那一天
      const i = Math.max(0, Math.min(t.length - 1, t.length - 1 - Math.floor(rotFrame || 0)));
      return (t[i] || [])[0] || null;
    };
    const drawRankDays = (n) => {
      const src = f3 && f3.share_daily;
      if (!src || !src.dates || !src.dates.length) {
        return empty('rankFlow', '逐日佔比資料還沒產出（下一輪盤後管線就會有）');
      }
      const D2 = src.dates, N = D2.length;   // 不要叫 L —— 外層的 L 是連結工具（L.group/L.stock）
      /* 截止日＝時鐘大圈落在的那一天。對不到（例如那一天不在逐日佔比裡）就退回最新一天，
         並且在副標寫清楚 —— 兩張圖的日期看起來一樣其實不一樣，比少一個功能糟得多。*/
      const fd = rotFrameDate();
      const fi = fd ? D2.indexOf(fd) : -1;
      const end = fi >= 0 ? fi + 1 : N;      // 1-based 的「不含」結尾
      const k = Math.min(n, end);
      const curFrom = end - k, prevFrom = Math.max(0, end - 2 * k), prevTo = curFrom;
      const avg = (arr, a, b) => { let s = 0, c = 0;
        for (let i = a; i < b; i++) { const v = (arr || [])[i]; if (v != null) { s += v; c++; } }
        return c ? s / c : null; };
      const sum = (arr, a, b) => { let s = null;
        for (let i = a; i < b; i++) { const v = (arr || [])[i]; if (v != null) s = (s || 0) + v; } return s; };
      // 期間報酬要用日漲跌**連乘**，不是相加 —— 相加在 20 天以上會明顯高估
      const compound = (arr, a, b) => { let f = 1, c = 0;
        for (let i = a; i < b; i++) { const v = (arr || [])[i]; if (v != null) { f *= 1 + v / 100; c++; } }
        return c ? (f - 1) * 100 : null; };
      let gs = src.groups.map(g => ({
        group_id: g.group_id, group_name: g.group_name, chain: g.chain,
        share: avg(g.share, curFrom, end),
        share_prev: prevTo > prevFrom ? avg(g.share, prevFrom, prevTo) : null,
        turnover: sum(g.turnover, curFrom, end),
        ret: compound(g.chg, curFrom, end),
      })).filter(g => g.share != null);
      gs.forEach(g => { g.share_chg = g.share_prev == null ? null : g.share - g.share_prev; });
      // 名次：這一段與上一段各自按佔比排一次，才算得出 rank_chg
      const rankOf = (key) => { const ord = gs.filter(g => g[key] != null).slice()
        .sort((a, b) => b[key] - a[key]); const m = {}; ord.forEach((g, i) => { m[g.group_id] = i + 1; }); return m; };
      const rc = rankOf('share'), rp = rankOf('share_prev');
      gs.forEach(g => { g.rank = rc[g.group_id] || null; g.rank_prev = rp[g.group_id] || null;
        g.rank_chg = (g.rank && g.rank_prev) ? g.rank_prev - g.rank : 0; });
      const from = D2[curFrom], to = D2[end - 1];
      /* ★ 2026-09-20：期間卡拿掉之後 #periodNote 不存在了，
         所以日期範圍與比較基準改寫進排行自己的副標 —— 使用者仍然看得到
         「現在這張圖是哪一段、跟誰比」，資訊沒有因為拿掉那張卡而消失。
         ★ 2026-09-21：再加一句「截止日是誰決定的」。合併之後兩張圖並排、共用一支
           「看哪一天」，副標必須讓人一眼看出排行看的就是同一天結尾的那一段；
           對不到截止日時要**明講**是最新一天，不可以讓它看起來跟著時鐘走。 */
      $('#rankSub').textContent = `${from} ～ ${to}（${k} 個交易日）`
        + (prevTo > prevFrom ? `　·　和前 ${prevTo - prevFrom} 個交易日相比` : '　·　沒有可比的上一段')
        + (fi >= 0 ? '　·　截止日跟著「看哪一天」' : '　·　截止到最新一天（時鐘那一天沒有逐日佔比）');
      renderRankFlow({ label: `最近 ${k} 天`, from, to, days: k,
        prev_from: prevTo > prevFrom ? D2[prevFrom] : null, groups: gs });
    };
    /* I1（Andy 2026-09-18：「族群 × 法人需要新增時間週期也是拉 Bar 式，0-30 天，
       且需要新增占比 % 單位」）。0 保留成「跟著上方期間走」，不然 0 天沒有意義。*/
    /* 圖八（Andy 2026-09-18「族群 × 法人一樣需要新增拉Bar +&- 播放功能」）：
       「最近 N 天」的長度不變，改成讓**截止日**往回挪 —— 這樣播放時看到的是
       「同樣長度的窗，一天一天往前滑」，而不是窗越拉越長。
       後端 inst_daily 已從 30 天拉到 120 天，回放才有東西可放。*/
    let instEnd = null;                 // 截止日索引（1-based）；null＝最新
    const drawInstDays = (n) => {
      const src = f3 && f3.inst_daily;
      if (!src || !src.dates || !src.dates.length) {
        return empty('instGroups', '逐日法人資料還沒產出（下一輪盤後管線就會有）');
      }
      const end = instEnd == null ? src.dates.length : Math.max(1, Math.min(src.dates.length, instEnd));
      const k = Math.min(n, end);
      const from = end - k;
      const sum = (arr) => { let s = null; for (let i = from; i < end; i++) {
        const v = (arr || [])[i]; if (v != null) s = (s || 0) + v; } return s; };
      const gs = src.groups.map(g => ({
        group_id: g.group_id, group_name: g.group_name,
        foreign: sum(g.foreign), trust: sum(g.trust), dealer: sum(g.dealer),
      })).map(g => ({ ...g, total: (g.foreign || 0) + (g.trust || 0) + (g.dealer || 0) }))
        .filter(g => g.foreign != null || g.trust != null || g.dealer != null);
      $('#instSub').textContent = `${src.dates[from] || ''} ～ ${src.dates[end - 1] || ''}（${k} 個交易日）三大法人淨買超（張）`;
      renderInstPeriod({ label: `最近 ${k} 天`, days: k, groups: gs });
    };
    /* 名次變化（bump）整張拿掉 —— Andy 2026-09-18 圖四：
       「右邊的名次變化刪掉，改成當資金流向排行點選長條圖時，會顯示對應股票，
         並且顯示在資金輪動上方」。那一格現在給輪動時鐘。
       名次資訊沒有消失：排行的 y 軸標籤仍然帶 `3↑` `2↓`，tooltip 也仍然寫名次。*/
    // ★ drawPeriod() 統一放在兩支拉 Bar 都建好之後才呼叫（它會讀 instDays / rankDays 的值）；
    //   在這裡先叫一次的話會先用「跟著期間」畫一張，再被拉 Bar 記住的值重畫，畫面會閃一下。

    // ---- 輪動階段：和幾天前比，用來判斷誰剛換階段
    // N2：兩張圖共用的完整族群名單（依成交值佔比排序），在畫圖之前就算好
    rotAllGroups = rotRows(f3 && f3.rrg, ROT_BOARD_WIN)
      .map(r => ({ gid: r.gid, name: r.name }));
    /* ★ 2026-09-23：對照表要在**畫任何一張圖之前**建好 —— 資金去向（桑基）下面那排下拉
       的第一層也讀 `rotGroupMeta`，而它有可能比 `wireRotFilter()` 早畫。
       沒先建的話第一層只會剩一個「全部」，而且不會自己好（那張圖不會再重畫一次）。*/
    rotFillMeta(f3);
    /* C4（Andy 2026-09-20：「資金流向排行、輪動時鐘，改用圖一這樣方式呈現，
       也可以篩選想要的股票」）—— 圖一指的是漲跌分佈那張卡的篩選列。
       這裡把同一套語彙搬過來，`rotFilter` 是排行與時鐘**共用**的那一份選擇。*/
    /* ★ 2026-09-23：第二個參數 `only` 拿掉了。它以前的意思是「這一幀只更新時鐘、
       不要重建下面那塊輪動階段看板」，而看板與「換階段的族群」那一排都已經移除，
       `renderRotation` 現在本來就只畫時鐘 —— 留著一個永遠沒有作用的參數，
       下一個人會以為關掉它就會多畫點什麼。*/
    const drawRot = (frame) => {
      /* ★ 2026-09-23：`board`（輪動階段四格）與 `cycle`（四段循環列）不再傳 ——
         那一整塊已經併進時鐘的四個象限卡（`quads`）。
         ★ 2026-09-23 追加：`move`（最近 5 個交易日換階段的族群）也拿掉了（Andy 指定），
           所以這裡只剩 `clock` 與 `quads`。*/
      renderRotation(f3 && f3.rrg, ROT_BOARD_WIN,
        { clock: 'rotClock', quads: true,
          pick: rotPickSet(), frame: frame || 0,
          /* 軌跡固定畫滿 30 天：拉Bar 是「看哪一天」，不是「畫多長」（A4 第 7 條）。
             span＝30 而後端只存 31 天，所以軌跡的起點永遠是最舊那一天 ——
             配上漸進式軌跡，刷到「前 30 天」就只剩起點一個點，往今天刷才一路長出來
             （Andy 2026-09-20：「只有經過才留下軌跡」）。*/
          span: ROT_SPAN, trail: ROT.trail, expose: true });
      // 排行選了誰，時鐘就跟著只亮誰（圖四點長條的連動）
      if (rankSel) highlightClock(rankSel);
    };
    /* 時間軸刷動／播放：時鐘**立刻**跟著動（這是「絲滑」的來源），
       底下的輪動階段看板用 160ms debounce 補上 —— 它是整頁最貴的 DOM 重建，
       每 420ms 跟著重建一次會把補間動畫拖到掉幀。*/
    let rotBoardT = null;
    /* 只更新下面那塊輪動階段看板，**不要碰時鐘**。
       ★ 2026-09-20（E1 量出來的）：以前這裡是 `drawRot(rotFrame)`（連時鐘一起重畫）。
         播放時每 420ms 推進一天、160ms 後又整張重設一次 series，
         第二次 setOption 會**把還在跑的補間動畫從中途重新開始**（又是 420ms 到同一個目標），
         於是每一幀都沒跑完就被下一幀接手 —— 尾巴與大圈的脫節會一路累積。
         實測：播到第 5 天時「光電業」的尾巴尖端已經落後大圈 41px（大圈半徑只有 6.5px）。
         看板本來就不需要時鐘陪著重畫，分開之後脫節回到 3px 以內。*/
    /* 原本的 `drawBoard`。看板與「換階段的族群」那一排都拆掉之後，
       它只剩一件事：把展開中的象限面板換成新的那一天。
       ★ 去抖動**照舊留著**（不要順手刪）：面板一次要重建幾十個 `<li>`，
         播放是每 420ms 推進一天，跟著重建一樣會把時鐘的補間動畫拖到掉幀。*/
    const drawBoard = () => { renderStagePanel(); };
    /* ★ 2026-09-21：刷「看哪一天」時，排行也要跟著換截止日。
       但**不要每一幀都重畫** —— 播放是每 420ms 推進一天，排行是整張 notMerge 重畫
       （量測：1500px 下 60~90ms），跟著跑會把時鐘的補間動畫拖到掉幀，
       那就又回到 Andy 說的「段點段點式移動」。所以和輪動階段看板共用同一個 160ms 去抖動：
       手放開（或播放停下來）之後 160ms，排行一次補到對的那一段。*/
    /* ★ D1：排行「往回看幾天」＝區間桿兩個把手之間的距離（`spanBar` 的 `days`）。
       拉Bar 還沒建好時（第一次畫圖的那一瞬間）退回 DEFAULT_DAYS，行為和合併前一樣。*/
    const rankVal = () => (rotBackBar && rotBackBar.days ? rotBackBar.days : DEFAULT_DAYS);
    /* ★ D1：`exitLive` 是合併之後才需要的參數。
       區間桿的**左把手**只改「這一段有多長」（排行往回看幾天），截止日沒有動 ——
       那件事和「即時」不衝突，不該把使用者剛按下的即時模式踢掉。
       只有右把手／＋ −／播放真的換了截止日時才退出即時。*/
    const rotSeek = (v, exitLive) => {
      /* ★ 拖時間軸（或按 ▶ 播放）就自動退出即時 —— 兩者互斥，和資金去向那顆鈕同一條規矩。
         即時是「接在最後一個收盤後面續算出來的那一點」，往回看某一天時它沒有意義。
         `false`＝不要在這裡再重畫一次，下一行本來就會畫。*/
      if (exitLive !== false && RLV.on) rlvOff(false);
      flowState.back = v; rotFrame = v;
      drawRot(v);
      clearTimeout(rotBoardT);
      rotBoardT = setTimeout(() => { drawBoard(); drawRankDays(rankVal()); }, 160);
    };
    /* 篩選（產業鏈／前 10 大／個股／族群晶片）變了就重畫。
       放大視窗開著時它也要跟著重畫 —— 兩邊吃的是同一份 ROT 狀態，
       只更新其中一邊的話，使用者關掉放大就會看到「剛剛按的東西不見了」。*/
    rotRedraw = () => { drawRot(rotFrame); drawPeriod(); renderStagePanel(); if (rotZoomDraw) rotZoomDraw(); };
    /* 即時那一輪只要重畫「時鐘」（卡片＋放大視窗）。
       刻意**不叫 `rotRedraw`** —— 它連排行與期間卡一起重畫，那兩張和即時完全無關，
       每分鐘白重建一次只會讓畫面閃一下。*/
    rlvRedraw = () => { drawRot(rotFrame); renderStagePanel(); if (rotZoomDraw) rotZoomDraw(); };
    /* 放大視窗關掉時把卡片補回來：天數（rotFrame）與篩選都是在放大視窗裡改的，
       卡片那張圖在那段期間刻意沒有跟著重畫（每 420ms 重畫兩張會掉幀）。*/
    rotSyncCard = () => {
      if (rotBackBar) { try { rotBackBar.set(rotFrame); } catch (e) { /* 忽略 */ } }
      flowState.back = rotFrame;
      $$('.rot-trail').forEach(x => { x.checked = ROT.trail; });
      wireRotFilter(); drawRot(rotFrame); drawPeriod();
    };
    wireRotFilter(f3);
    /* ★ 2026-09-21（Andy：「下方這段也移除」，指的是圖下方那一整段
       「圓心＝跟大盤走得一模一樣…」的長說明）。
       `#rotCenterNote` 是**常駐**的，622 個字，量起來在 1440px 佔掉 225px、
       800px 206px、390px **469px**（手機上比半個螢幕還長），
       而它講的每一件事「怎麼看 ?」那顆鈕裡都有（或已經補進去了）。
       他要拿掉的是「一直佔著版面的那一段」，不是說明本身 ——
       所以整段刪掉、說明留在按鈕後面，需要的人自己展開。*/
    /* 放大（已拍板：拉Bar／篩選／播放都放在放大視窗裡，卡片上只留一顆「放大」）。
       重用既有的 openZoom()，所以 Esc、點背景關閉、關閉時 dispose 都是現成的。*/
    const zb = $('#rotZoomBtn');
    if (zb) zb.onclick = () => openRotZoom(f3 && f3.rrg, ROT_BOARD_WIN);
    /* F2（Andy 2026-09-18：「右上角的 5 10 20 天改成拉 Bar」）→ N4（2026-09-19）拉到 30 天
       → **A4（2026-09-20）第 1、3、5、7 條，四件事都在這一支拉Bar 上**：

       · 第 1 條「新增 ＋ / −」與第 5 條「新增播放功能」：改用 `playBar`（它就是
         rangeBar ＋ − ＋ ▶ 三顆鈕），所以不用為了這張圖另外長一套按鈕。
         `dir: -1` 是這次替 playBar 加的：值＝「幾天前」，所以播放要**由大往小**跑，
         時間才是往前走的。
       · 第 3 條「前一天 ～ 前三十天」：min 5 → **1**。
       · 第 7 條「大圈要落在那一天，而且是慢慢移過去」：這支的值現在同時是
         `frame`（看哪一天）—— 拉Bar 從「軌跡畫多長」變成「時間軸刷到哪一天」。
         軌跡長度改由 ROT_SPAN 固定成 30 天，所以整條路一直在，大圈沿著它走。
         平滑移動靠 renderRotClock 的 merge ＋ animationDurationUpdate，不是這裡。

       ★ 2026-09-21 起這支**只管「看哪一天」**；輪動階段看板的比較窗長
         已拆成獨立的 ROT_BOARD_WIN（固定 5 天）。舊註解留著當紀錄：
         兩件事的方向一致（都是「把時間往回拉 N 天」），所以共用同一個值不會打架：
         時鐘回答「N 天前大家在哪」，看板回答「這 N 天誰換了階段」。*/
    /* ★ 2026-09-20：frame 820 → ROT_ANIM_MS（420），和時鐘的補間時間**相等**。
       以前補間 620ms、每 820ms 才推進一天 → 每天走完站著不動 200ms，
       那就是 Andy 說的「段點段點式移動」。相等之後首尾相接、等速。*/
    /* ★ group: 'rot.back' —— 卡片這支和放大視窗那支 `#rotZoomBack` 控制的是**同一個值**，
       所以歸成同一組：一次只准一支在播，按 ⏸ 兩支一起停（2026-09-21 的「暫停停不下來」）。*/
    /* ★ D1（2026-09-23）：`playBar('rotBack')` ＋ `rangeBar('rankDays')` 兩條合併成
       一條雙把手的 `spanBar`（做法與代價寫在 spanBar 的檔頭註解）。
       容器沿用 `#rotBack` 是刻意的：`rlvMountBtn()`（「即時」鈕與狀態列）掛的就是這個容器，
       換 id 等於同時改兩支程式、卻沒有換到任何好處。
       `onChange` 一次收到兩個值：`to`＝截止日是幾天前（餵 `rotSeek` → 時鐘大圈 ＋ 排行截止日），
       `days`＝這一段有幾個交易日（`rankVal()` 會讀回去餵排行）。*/
    rotBackBar = spanBar('rotBack', { max: 30, to: flowState.back, days: DEFAULT_DAYS,
      keyTo: 'tw.rot.back3', keyDays: 'tw.rank.days', frame: ROT_ANIM_MS, group: 'rot.back',
      label: '期間',
      onChange: (to) => rotSeek(to, to !== flowState.back) });
    rotFrame = rotBackBar ? rotBackBar.value : ROT_MIN_BACK;
    flowState.back = rotFrame;
    /* 「即時」鈕要等 playBar 建好才掛得上去（playBar 會把 `#rotBack` 的 innerHTML 換掉）。
       換主題／換頁回來時這裡會再跑一次，`rlvMountBtn()` 內部會把「亮起來」的樣子補回去。*/
    rlvMountBtn();
    wireRotTrailToggle(() => drawRot(rotFrame));
    drawRot(rotFrame);

    // I1 的拉 Bar 要在 drawPeriod 之前建好（drawPeriod 會讀它的值）
    // ★ 2026-09-20：min 0 → 1、預設 20。0 以前代表「跟著上方期間走」，
    //   期間卡拿掉之後那個值沒有意義了，留著只會讓人拉到一個什麼都不會發生的位置。
    instDays = rangeBar('instDays', { min: 1, max: 30, value: DEFAULT_DAYS, key: 'tw.inst.days',
      label: '最近', fmt: (v) => v + ' 天',
      onChange: () => drawPeriod() });
    // 圖八的截止日：往回拉看以前的樣子，按 ▶ 一天一天播
    {
      const idl = (f3 && f3.inst_daily && f3.inst_daily.dates) || [];
      if (idl.length > 5) {
        /* ★ 2026-09-20（Andy：「圖二族群法人播放功能移除」）：playBar → rangeBar。
           ＋ − ▶ 三顆鈕整組拿掉，截止日本身還能拖 —— 他要拿掉的是「自己會跑的播放」，
           不是「看以前那一天」這個能力。*/
        rangeBar('instEnd', { min: 5, max: idl.length, value: idl.length, key: 'tw.inst.end',
          label: '截止', fmt: (v) => (v >= idl.length ? '最新' : (idl[v - 1] || v)),
          onChange: (v) => { instEnd = v; drawInstDays(instDays ? Math.max(1, +instDays.value || DEFAULT_DAYS) : DEFAULT_DAYS); } });
      }
    }
    /* ★ D1（2026-09-23）：排行的「最近 N 天」拉Bar（`#rankDays`）已經併進上面那條區間桿的
       左把手，這裡不再單獨建一支。`drawPeriod()` 仍然要叫一次，把排行畫出來。*/
    drawPeriod();

    /* 圖六：改吃獨立檔 sankey_daily（60 天），配一支「看哪一天」的拉 Bar。
       這份檔案只有這一頁會載，所以在這裡才 load。
       ★ 2026-09-20 上午：播放鈕拿掉（rangeBar）。
       ★ 2026-09-20 下午（Andy：「並且需要具備播放功能」）：**加回來**（playBar）。
         方向和輪動時鐘相反：這支的值是「第幾個交易日」，由小到大就是時間往前走，
         所以用 playBar 的預設方向（dir = +1），不要抄時鐘那支的 dir:-1。
         間隔 650ms 是量出來的：一次 renderSankey 是整張 notMerge 重畫
         （5 條鏈 ＋ 18 個族群 ＋ 54 個葉子），在 1500px 上約 90~140ms，
         留三倍以上的餘裕才不會播到一半卡住。
       ⚠ 這一頁其餘三支拉Bar（排行、族群×法人、法人截止日）**維持沒有播放鈕**，
         那是 2026-09-20 上午拍板要移除的，不要順手一起加回去。*/
    load('sankey_daily', { fallback: { dates: [], groups: [], leaves: {} } }).then(sd => {
      const n = (sd && sd.dates && sd.dates.length) || 0;
      renderSankey(sd, n ? n - 1 : 0);
      if (n > 1) {
        playBar('sankeyDays', { min: 0, max: n - 1, value: n - 1, key: 'tw.sankey.day',
          frame: 650, label: '看哪一天', fmt: (v) => (v >= n - 1 ? '最新' : sd.dates[v]),
          /* 拖時間軸＝「我要看過去某一天」，和「即時」是互斥的兩件事。
             不退出的話拉Bar 看起來完全沒作用（畫面還是盤中那一張），像壞掉。*/
          onChange: (v) => { if (SKL.on) sklOff(false); renderSankey(sd, v, sankeySel); } });
      }
      // ★「即時」鈕掛在同一列（Andy：「在紅框那排」）。playBar 會換掉整個容器的
      //   innerHTML，所以一定要等它建完才 append。
      sklMountBtn();
    });
    /* ★ 2026-09-20（Andy：「圖四五 將時間週期以及族群佔比河流圖移除」）：
       「族群佔比河流」整塊（圖表 ＋ 它的『最近 N 天』時間週期拉Bar ＋ 截止日回放）
       已從 index.html 與這裡一起移除。河流圖回答的問題（這 60 天主流換過幾次）
       和「資金集中度」高度重疊，而集中度那張還多了均線與逐日鑽取。
       `renderRiver` / `sliceShare` 也一併刪掉 —— 留著沒有人呼叫的函式只會讓下一個人以為還在用。*/
    const drawConc = () => renderConc(conc, flowState.concTop);
    drawConc();
    $$('#concSeg button').forEach(b => b.onclick = () => {
      $$('#concSeg button').forEach(x => x.classList.toggle('on', x === b)); flowState.concTop = +b.dataset.v; drawConc();
    });
    // 資金流向頁的六張圖不加滾輪縮放（Andy 09-13）；圖本身已經用足卡片寬度
  }

  /* 量一批字在畫面上實際有多寬（取最寬的那一個）。
     ECharts 的軸標籤是畫在 canvas 上的，DOM 上量不到，所以自己用 canvas 的 measureText，
     字型跟 chart() 給的 textStyle 一致 —— 不一致的話量出來的數字沒有意義。*/
  let _measCtx = null;
  function textW(list, fs) {
    try {
      if (!_measCtx) _measCtx = document.createElement('canvas').getContext('2d');
      _measCtx.font = `${fs}px "Noto Sans TC", "JetBrains Mono", sans-serif`;
      return (list || []).reduce((m, t) => Math.max(m, _measCtx.measureText(String(t)).width), 0);
    } catch (e) { return 0; }                    // 量不到就讓呼叫端用自己的下限
  }

  // ---- 資金流向排行：這段期間誰的成交值佔比長大、誰縮小
  function renderRankFlow(p) {
    let gs = (p.groups || []).filter(g => g.share_chg != null);
    /* C4：排行與輪動時鐘吃**同一份**篩選（rotPickSet）。
       篩到一個都不剩就當作沒篩 —— 空白的圖比「全部」更沒用，
       而且使用者八成是勾到一個今天沒進排行的族群。*/
    const pk = rotPickSet();
    if (pk.size) {
      const sub = gs.filter(g => pk.has(g.group_id));
      if (sub.length) gs = sub;
    }
    /* ★ 2026-09-21：截止日跟著「看哪一天」之後，多了一種空狀態 ——
       截止日往回拉太多、又要看很多天時，它前面就沒有「同樣長度的上一段」可以比了
       （逐日佔比只存 60 天）。文案要指名是哪兩顆旋鈕造成的，不然使用者只會以為圖壞了。*/
    if (!gs.length) return empty('rankFlow', p.prev_from ? '這個期間沒有可比的族群'
      : '這一段前面沒有同樣長度的上一段可以比（逐日佔比只存 60 天）——'
        + '把「看哪一天」往今天拉，或把「最近 N 天」調小一點');
    const up = gs.slice().sort((a, b) => b.share_chg - a.share_chg).slice(0, 9);
    const down = gs.slice().sort((a, b) => a.share_chg - b.share_chg).slice(0, 6).reverse();
    const rows = up.concat(down.filter(d => !up.some(u => u.group_id === d.group_id)));
    rows.sort((a, b) => a.share_chg - b.share_chg);      // 由下往上＝由小到大，最會吸金的在最上面
    const label = (g) => {
      const arrow = g.rank_chg > 0 ? ` ${g.rank_chg}↑` : g.rank_chg < 0 ? ` ${-g.rank_chg}↓` : '';
      return `${g.group_name}${arrow}`;
    };
    /* ★ F3（Andy 2026-09-20：「圖二的版面配比需要 2:1，資金流向排行改成在右邊」）。
       這張圖從「半個版面」變成「三分之一個版面」，左右兩塊留白就得跟著縮 ——
       原本左 132 右 96 共吃掉 228px，1101px 的畫面上這一欄只有 ~300px，
       長條會只剩 70px，族群名也會被容器裁掉。
       所以依**量到的容器寬度**分三級：字級、右邊留白跟著縮，
       最窄的時候右邊那串只留佔比變化（期間報酬讓位給族群名，tooltip 裡還看得到）。*/
    const rfw = (document.getElementById('rankFlow') || {}).clientWidth || 600;
    const narrow = rfw < 380, mid = rfw < 470;
    const GR = narrow ? 58 : mid ? 76 : 96;
    const FS = narrow ? 11.5 : 12.5;          // 手機也不得小於 11px
    /* 左留白**量出來**，不要寫死：族群名長度差很多（「金融」2 個字 vs
       「連接器 / 高速傳輸 3↑」13 個字），而且畫出來是誰會隨著天數換人。
       2026-09-20 第一版寫死 104px，換一個期間就被「連接器 / 高速傳輸 3↑」凸出容器 9px ——
       那不是「這個名字太長」，是「留白不該是常數」。
       下限是為了讓短名字的時候長條不要貼著卡片邊；上限鎖在欄寬的一半，
       不然窄欄位會被名字整個吃掉、長條沒有地方畫。*/
    const GL = Math.max(narrow ? 96 : mid ? 108 : 124,
      Math.min(Math.round(rfw * 0.5), Math.ceil(textW(rows.map(label), FS)) + 12));
    /* ★ 2026-09-21：留白有上限（欄寬的一半，否則長條沒地方畫），所以**名字仍然可能放不下**。
       實測：1280px 合併版面下右欄只剩 ~330px，「NOR Flash 利基記憶體 1↓」凸出容器 4px。
       上面那段註解說「留白不該是常數」是對的，但它沒處理「量出來也還是不夠」這種情形。
       所以這裡再補一層：量到放不下就**截斷加省略號**，完整名稱 tooltip 裡還在。
       截斷而不是縮字級 —— 字級已經有 11px 的下限（手機可讀性），不能再往下壓。*/
    const LBUD = GL - 12;
    const fit = (t) => {
      if (textW([t], FS) <= LBUD) return t;
      let lo = 1, hi = t.length;
      while (lo < hi) { const m = (lo + hi + 1) >> 1;
        if (textW([t.slice(0, m) + '…'], FS) <= LBUD) lo = m; else hi = m - 1; }
      return t.slice(0, lo) + '…';
    };
    const c = chart('rankFlow', {
      tooltip: {
        ...tip, trigger: 'item', formatter: (q) => { const g = rows[q.dataIndex];
          return `<b>${g.group_name}</b><br>成交值佔比 ${fmt.n(g.share, 2)}%（上一段 ${g.share_prev != null ? fmt.n(g.share_prev, 2) + '%' : '—'}）`
            + `<br>變化 <span style="color:${upDown(g.share_chg)}">${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp</span>`
            + `<br>名次 ${g.rank_prev != null ? g.rank_prev + ' → ' : ''}${g.rank}`
            + `<br>期間報酬 <span style="color:${upDown(g.ret)}">${fmt.pct(g.ret, 1)}</span>`
            + `<br>成交值 ${fmt.yi(g.turnover)}<br><small>點一下看成分股</small>`; },
      },
      // bottom 30→38、nameGap 24→22：原本「佔比變化 (pp)」整行掉出容器下緣 6px
      grid: { left: GL, right: GR, top: 12, bottom: 38 },
      xAxis: { ...axisStyle, name: '佔比變化 (pp)', nameLocation: 'middle', nameGap: 22, nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3, hideOverlap: true } },
      yAxis: { ...axisStyle, type: 'category', data: rows.map(g => fit(label(g))), axisLabel: { color: CH.ink2, fontSize: FS } },
      series: [{
        type: 'bar', barWidth: 15,
        data: rows.map(g => ({ value: +g.share_chg.toFixed(3), gid: g.group_id,
          itemStyle: { color: chgColor(g.share_chg, 1.5), borderRadius: g.share_chg >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
        label: { show: true, position: 'right', color: CH.ink2, fontSize: 11.5, fontFamily: 'JetBrains Mono',
          // 窄欄位只寫佔比變化（這張圖回答的就是「誰把錢吸走了」）；期間報酬在 tooltip 裡還在
          formatter: (q) => { const g = rows[q.dataIndex];
            const v = `${g.share_chg > 0 ? '+' : ''}${g.share_chg.toFixed(2)}`;
            return narrow ? v : `${v}　${fmt.pct(g.ret, 1)}`; } },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: hexA(CH.ink3, .6) }, data: [{ xAxis: 0 }], label: { show: false } },
      }],
    });
    /* 2026-09-18（Andy 圖四）：「當資金流向排行點選長條圖時，會顯示對應股票，
       並且顯示在資金輪動上方，也可變成另類篩選」。
       所以點長條**不跳頁**：① 在排行卡下方原地展開成分股（重用 heatPanel）
       ② 同時把旁邊的輪動時鐘只亮這個族群、其餘壓暗 —— 兩張圖現在並排，一眼對得起來。
       再點同一根就取消（回到全亮）。*/
    if (c) c.off('click').on('click', q => {
      const gid = q.data && q.data.gid; if (!gid) return;
      const g = rows.find(x => x.group_id === gid) || {};
      /* ★ 2026-09-21：這裡展開的清單改成兩階段共用的那一支（drillOpen）——
         以前是 heatPanel，點下去只能連到個股頁；現在同一份清單還可以把個股畫到圖上。
         面板就在圖正下方，所以一樣不自己捲動（heatPanel 的 scroll:false 是同一個理由）。*/
      if (rankSel === gid) { rankSel = null; drillClose(); highlightClock(null); return; }
      rankSel = gid;
      /* ★ 2026-09-21：時鐘只畫前 16 個族群（成交值佔比），而這張排行是依**佔比變化**排的 ——
         變化最大的那一個未必在時鐘上。以前碰到這種情形會把 16 個全部壓暗（整張圖灰掉），
         現在 highlightClock 會回 false、不動時鐘，改成在面板的說明裡**明講一句**，
         不要讓使用者以為自己點壞了。*/
      const onClock = highlightClock(gid);
      drillOpen(gid, g.group_name,
        `佔比 ${fmt.n(g.share, 2)}%　·　變化 ${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp　·　期間報酬 ${fmt.pct(g.ret, 1)}`
        + (onClock ? '' : '　·　這個族群不在左邊時鐘的前 16 名內，所以時鐘沒有變化'),
        'rankPanel');
    });
    lastRankRows = rows;
    /* 欄寬變了一定要**重畫**，不能只 resize：grid 的 left/right 是像素值，
       `chart()` 掛的 ResizeObserver 只會呼叫 resize()，留白仍然是舊的那一組，
       於是把瀏覽器縮窄之後長條只剩一點點、族群名被裁掉 —— 這就是 C2「換一台電腦
       版面就跑掉」在這張圖上的樣子。所以這裡自己盯寬度（120ms 去抖動）。*/
    {
      const el = document.getElementById('rankFlow');
      if (el) {
        el._rfRedraw = () => renderRankFlow(p);
        if (!el.dataset.rfRo && window.ResizeObserver) {
          el.dataset.rfRo = '1';
          let t = null, lastW = el.clientWidth;
          new ResizeObserver(() => {
            if (Math.abs(el.clientWidth - lastW) < 8) return;
            lastW = el.clientWidth;
            clearTimeout(t);
            t = setTimeout(() => { const f = el._rfRedraw; if (f && el.isConnected) f(); }, 120);
          }).observe(el);
        }
      }
    }
    /* ★ 2026-09-21：排行卡下方那一排族群晶片也搬到 `.rotfilter[data-rf="rank"]` 裡
       （產業鏈 seg 的正下方），所以這裡不再插一排 —— 見 wireRotFilter()。*/
  }

  /* 輪動時鐘的放大視窗（Andy 2026-09-18 圖二：「右上角 可以放大這圖」）。

     ★ 2026-09-20（E2，Andy：「放大之後的功能都沒反應」）—— 兩個根因，都已經量過：
       ① `renderRotClock` 結尾那段 `if (!compact) groupChips(...)` 對放大視窗也成立，
          於是 `.linkrow.gchips` 被插在 `#zoomBody` 的下一個兄弟，而 `.zb` 是 flex ——
          實測 `#zoomBody` 704×756、那排晶片 704×748，**放大視窗一半的版面被晶片吃掉**；
          更糟的是那排晶片綁的是**卡片**的選取，在放大視窗裡按下去對這張圖完全沒有作用。
       ② 這裡本來維護**第二套**控制項（只有 16 顆的簡化晶片 ＋ 兩支語意不同的拉Bar），
          兩套行為不一致就是這個 bug 的溫床。
     改法：放大視窗吃**同一份 ROT 狀態、同一組控制項**（產業鏈 seg／族群晶片列／
     只看前 10 大／清除篩選／看哪一天／顯示軌跡），關掉時把卡片同步回來。
     ★ 2026-09-21：族群晶片列搬進 `.rotfilter` 之後，這裡連 `#rotZoomChips` 都不用自己維護了 ——
       `wireRotFilter()` 會把三排（時鐘卡／排行卡／放大視窗）一起填好。*/
  function openRotZoom(rrg, back0) {
    const rows0 = rotRows(rrg, back0);
    if (!rows0.length) return;
    /* ★ 2026-09-21：卡片那支如果正在播，開放大之前先停掉。
       不停的話它會躲在遮罩後面繼續每 420ms 推進 `rotFrame`，
       而使用者在放大視窗裡按的 ⏸ 停的是另一支 —— 關掉放大就會看到時鐘還在自己跑。
       （量測：ESC 之後「幾天前」3 秒內從 3 跑到 27。）*/
    if (rotBackBar) { try { rotBackBar.stop(); } catch (e) { /* 忽略 */ } }
    let bar = null;
    openZoom('輪動時鐘', (body, chipBox, close) => {
      /* 控制項一律用 class 或「Zoom」字樣的 id，**不可以和卡片上的 id 撞名** ——
         同一個 id 出現兩次時 getElementById 只抓得到第一個，另一邊就按了沒反應。*/
      const tools = $('#zoomTools');
      if (tools) tools.innerHTML = '<div class="rotfilter" data-rf="zoom"></div>'
        + '<div id="rotZoomBack" title="看哪一天：拖曳把時間軸往回刷，大圈會慢慢移過去"></div>'
        + '<div class="rottools" id="rotZoomTools"></div>';
      const draw = () => renderRotClock(rows0, ROT_SPAN, 'zoomBody', false,
        { pick: rotPickSet(), frame: rotFrame, span: ROT_SPAN, trail: ROT.trail });
      rotZoomDraw = draw;
      draw();
      wireRotFilter();                        // 放大視窗那排 .rotfilter 也由同一支填
      /* 「看哪一天」：和卡片上那支**同一個值、同一個 localStorage key、同一個方向**。
         值變了只重畫這張放大的圖 —— 播放是每 420ms 一幀，
         連卡片那張一起重畫會掉幀（那就又回到「段點段點」了）；
         關閉時 `rotSyncCard()` 會把卡片一次補上。*/
      bar = playBar('rotZoomBack', { min: ROT_MIN_BACK, max: 30, value: rotFrame, key: 'tw.rot.back3',
        dir: -1, frame: ROT_ANIM_MS, group: 'rot.back', label: '看哪一天',
        fmt: (v) => (+v === 0 ? '最新' : v + ' 天前'),   // 和卡片那支同一套口徑
        // 拖時間軸就退出即時（和卡片那支同一條規矩；`false`＝下一行本來就會重畫）
        onChange: (v) => { if (RLV.on) rlvOff(false); rotFrame = v; draw(); } });
      wireRotTrailToggle(draw, 'rotZoomTools');
    }, () => {
      // 關閉：停掉播放（拉Bar 的 DOM 已經被清掉了，再跑下去只是空轉）、把卡片同步回來
      if (bar) { try { bar.stop(); } catch (e) { /* 忽略 */ } }
      bar = null; rotZoomDraw = null;
      rotSyncCard();
    });
  }

  /* N2（Andy 2026-09-19 圖一：「兩邊族群對不上，有些為何篩選不到」）。
     根因：排行卡下面那排晶片列的是**排行圖上畫出來的 15 檔**（依佔比變化挑的），
     時鐘卡下面那排列的是**成交值前 16 大**，兩邊挑法不同、名單當然對不上；
     而且那些晶片是 `<a href="#industry/group/…">`，點下去是**跳頁**不是篩選 ——
     所以他說「有些篩選不到」。

     改法：兩張圖共用同一份名單（輪動資料裡的全部族群，依成交值佔比排序），
     而且晶片改成**篩選鈕**（點一次選、再點一次取消）。要進族群頁的話晶片右邊有個 `→`。
     ★ 當初「選起來」的效果是「排行展開成分股＋時鐘只亮它」，2026-09-20 的 E3 改成
       **真的把兩張圖都篩掉其他族群**；理由寫在下面那一段。*/
  /* ★ 2026-09-20（E3，Andy：「篩選族群功能覆蓋下方的族群選取功能」）。
     量出來的事實：`.rotpick` 面板和這一排在 1440/1280/1024/900/560 五個寬度下
     **幾何重疊都是 0**，所以他講的「覆蓋」不是壓在上面，是**功能上蓋過去** ——
     同一張卡片裡有兩份 36 個族群的清單：上面那排「族群篩選」真的會篩圖，
     這一排卻只 highlight／展開成分股、圖一個族群都沒少。
     兩排長得幾乎一樣、行為卻不同，上面那排就把這一排的意義吃掉了。

     決議：**族群選取只留這一處**（它離圖最近，而且「點族群展開個股」本來就長在它身上），
     上面那顆「族群篩選」鈕與它展開的族群清單移除，這一排改成**真的改 ROT.groups**。
     ★ 2026-09-23：這一排晶片本身也退場了（改成兩層下拉，見 `wireRotFilter`），
       原本產 HTML 的 `rotChipsHTML()` 一併刪掉 —— 留著就是沒人叫的死碼。*/
  /* ★ 2026-09-20（Andy）：「所有圖表的族群小Tip都需要具備點擊後就會在對應圖表上被篩選出去，
     以此達到篩選功能」。

     以前圖下方那排族群小 Tip 是 `linkRow()` 產的純連結 —— 點下去直接跳到族群頁，
     那是導覽不是篩選，而且會把人帶離當前頁面（違反「能點的東西就要能點到底、
     優先在原地展開」）。

     這裡抽一支共用的 `filterChips()`，每張圖只要回答一件事：
     「被選中的時候你要變成什麼樣子」（`onPick(gid|null)`）。
     這樣就不會變成每張圖各寫一套篩選，行為與樣式（.gchip）也跟 N2 那兩排一致：
     點名字＝只看它、再點一次取消；右邊的 → 才是進族群頁。
     選取狀態記在 `chipSel[chartId]`，換日期／重畫時沿用同一個選取。*/
  const chipSel = {};
  function filterChips(chartId, list, sel, onPick) {
    const el = document.getElementById(chartId); if (!el) return;
    const at = el.closest('.zwrap') || el;
    let row = at.nextElementSibling;
    if (!row || !row.classList.contains('linkrow')) {
      row = document.createElement('div'); row.className = 'linkrow';
      at.parentNode.insertBefore(row, at.nextSibling);
    }
    row.classList.add('gchips');
    row.dataset.for = chartId;
    chipSel[chartId] = sel || null;
    row.innerHTML = (sel ? '<span class="muted">篩選中（再點一次取消）</span>' : '')
      + list.map(g => `<span class="gchip${sel === g.gid ? ' on' : ''}" data-g="${g.gid}"
           style="--c:${L.gcolor[g.gid] || CH.cyan}">
         <button class="pick" title="只看這個族群">${fmt.esc(g.name)}</button>
         <a class="go" href="#industry/group/${g.gid}" title="進族群頁">→</a></span>`).join('');
    $$('.gchip .pick', row).forEach(b => b.onclick = () => {
      const gid = b.parentNode.dataset.g;
      const nx = chipSel[chartId] === gid ? null : gid;
      chipSel[chartId] = nx;
      onPick(nx);
    });
  }

  /* ★★ 2026-09-23（Andy：「**圖一二 兩個標籤式都需要做成下拉清單 篩選，所以他會是 族群->題材**，
     例如 半導體，下面就會有圖三那些，所以並非所有族群都在同一個下拉清單，
     而是對應族群出現對應個股」）—— 圖二＝**資金去向（桑基圖）下面那一整片族群晶片**
     （晶圓代工、ETF、面板產業、HPC 與網通 IC…排滿兩整行）。

     這支是 `filterChips()` 的下拉版，用在**單選**的圖上：
       第一層　產業鏈（和資金輪動那兩排同一份 `rotGroupMeta` / `chainLabel()`，不另建對照表）
       第二層　被第一層篩過的族群，**單選**（點一下就選定並收起來）

     ★ 刻意**不併進 `ROT`**。桑基的選取一直是自己的一份（`chipSel.sankey`），
       併進去會讓「我在資金去向點了一個族群」連帶把輪動時鐘也篩掉 —— 那是行為退化。
       要統一的是**外觀與操作方式**（都是兩層下拉），不是資料狀態。
     ★ 也因此第二層是單選樣式而不是 checkbox：複選是資金輪動那邊的需求，
       這張圖從第一天起就是「一次只看一個族群」，硬套 checkbox 只會讓人以為可以多選。 */
  const ddChain = {};              // chartId → 第一層選到的產業鏈（''＝全部）
  function filterDropdown(chartId, list, sel, onPick) {
    const el = document.getElementById(chartId); if (!el) return;
    const at = el.closest('.zwrap') || el;
    let row = at.nextElementSibling;
    if (!row || !row.classList.contains('ddrow')) {
      row = document.createElement('div'); row.className = 'ddrow rotfilter';
      at.parentNode.insertBefore(row, at.nextSibling);
    }
    row.dataset.for = chartId;
    chipSel[chartId] = sel || null;
    const meta = (g) => rotGroupMeta[g] || {};
    /* 選到的族群不屬於目前第一層時，第一層**自動跳到它所屬的那條鏈** ——
       這條是給「從圖上點節點」那條路用的：使用者沒碰下拉，但選取變了，
       不跟著跳的話按鈕上會寫著「半導體 · 金融股」這種自相矛盾的摘要。*/
    if (sel && meta(sel).chain) ddChain[chartId] = meta(sel).chain;
    const chains = [...new Set(list.map(g => meta(g.gid).chain).filter(Boolean))];
    const cur = chains.indexOf(ddChain[chartId]) >= 0 ? ddChain[chartId] : '';
    ddChain[chartId] = cur;
    const sub = cur ? list.filter(g => meta(g.gid).chain === cur) : list;
    const chainName = cur ? chainLabel(cur) : '全部';
    const selName = sel ? ((list.find(g => g.gid === sel) || {}).name || L.gname[sel] || sel) : '';
    const rf = 'dd-' + chartId;                        // 開合狀態的 key（和資金輪動那兩排共用一套）
    row.innerHTML = `<div class="rotdd" data-dd="chain">
        <button type="button" class="ddbtn" aria-haspopup="listbox" aria-expanded="false"
          title="第一層：先挑產業鏈">產業鏈：<b>${fmt.esc(chainName)}</b><i aria-hidden="true">▾</i></button>
        <div class="ddpanel" role="listbox" aria-label="產業鏈" hidden>
          <button type="button" role="option" class="ddopt${cur ? '' : ' on'}" data-c=""
            aria-selected="${cur ? 'false' : 'true'}">全部（${list.length} 個族群）</button>
          ${chains.map(c => {
            const n = list.filter(g => meta(g.gid).chain === c).length;
            return `<button type="button" role="option" class="ddopt${cur === c ? ' on' : ''}" data-c="${fmt.esc(c)}"
              aria-selected="${cur === c ? 'true' : 'false'}">${fmt.esc(chainLabel(c))}<em>${n}</em></button>`;
          }).join('')}
        </div>
      </div>
      <div class="rotdd wide" data-dd="group">
        <button type="button" class="ddbtn" aria-haspopup="listbox" aria-expanded="false"
          title="第二層：這條鏈底下的族群，一次看一個">族群：<b>${fmt.esc(chainName)} · ${sel ? fmt.esc(selName) : '未篩選'}</b><i aria-hidden="true">▾</i></button>
        <div class="ddpanel" role="listbox" aria-label="族群（單選）" hidden>
          <div class="ddbar"><span class="muted">${fmt.esc(chainName)}底下 ${sub.length} 個族群，一次看一個</span></div>
          <div class="ddlist">
            <button type="button" role="option" class="ddopt one${sel ? '' : ' on'}" data-g=""
              aria-selected="${sel ? 'false' : 'true'}">全部族群（不篩選）</button>
            ${sub.map(g => `<div class="ddopt one row${sel === g.gid ? ' on' : ''}" style="--c:${L.gcolor[g.gid] || CH.cyan}">
                <button type="button" role="option" class="nm" data-g="${g.gid}"
                  aria-selected="${sel === g.gid ? 'true' : 'false'}">${fmt.esc(g.name)}</button>
                <a class="go" href="#industry/group/${g.gid}" title="進族群頁">→</a></div>`).join('')
              || '<div class="muted" style="padding:8px">這條鏈目前沒有族群資料</div>'}
          </div>
        </div>
      </div>
      ${sel || cur ? '<button type="button" class="btn small dd-clear">清除</button>' : ''}
      <span class="muted">${sel ? `資金去向只看「${fmt.esc(selName)}」這一支（選「全部族群」或按清除就回到整張圖）`
        : '先挑產業鏈，再挑一個族群 —— 圖上就只剩它那一條分支'}</span>`;

    // 開合：和資金輪動那兩排共用 `rotMenu` / `rotCloseMenus()`，所以點別處、Esc 的行為完全一致
    $$('.rotdd', row).forEach(dd => {
      const kind = dd.dataset.dd;
      const btn = dd.querySelector('.ddbtn');
      const pan = dd.querySelector('.ddpanel');
      const lst = dd.querySelector('.ddlist');
      if (rotMenu && rotMenu.rf === rf && rotMenu.kind === kind) {
        pan.hidden = false; dd.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
        if (lst) lst.scrollTop = rotMenuTop;
      }
      if (lst) lst.onscroll = () => { rotMenuTop = lst.scrollTop; };
      btn.onclick = (ev) => {
        ev.stopPropagation();
        const willOpen = pan.hidden;
        rotCloseMenus();
        if (willOpen) {
          rotMenu = { rf, kind }; if (kind === 'group') rotMenuTop = 0;
          pan.hidden = false; dd.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
        }
      };
      dd.onkeydown = (ev) => { if (ev.key === 'Escape') { ev.stopPropagation(); rotCloseMenus(); btn.focus(); } };
    });
    // 第一層：挑鏈。挑完直接把第二層打開（和資金輪動那兩排同一個動作）
    $$('.rotdd[data-dd="chain"] .ddopt', row).forEach(b => b.onclick = () => {
      ddChain[chartId] = b.dataset.c;
      rotMenu = { rf, kind: 'group' }; rotMenuTop = 0;
      /* 換鏈時**不動選取**：這張圖是單選，硬把選取清掉會讓圖突然跳回整張，
         而使用者只是想換一條鏈來找族群。選取和鏈對不上時，上面那段會讓第一層跟著跳回去。*/
      filterDropdown(chartId, list, chipSel[chartId], onPick);
    });
    // 第二層：單選。點一下就選定並收起來（沒有「再點一次取消」——「全部族群」那一項就是取消）
    $$('.rotdd[data-dd="group"] [data-g]', row).forEach(b => b.onclick = (ev) => {
      ev.stopPropagation();
      const gid = b.dataset.g || null;
      rotCloseMenus();
      chipSel[chartId] = gid;
      onPick(gid);
    });
    $$('.rotdd[data-dd="group"] .go', row).forEach(a => a.onclick = () => { rotCloseMenus(); });
    const clr = row.querySelector('.dd-clear');
    if (clr) clr.onclick = () => {
      ddChain[chartId] = ''; rotCloseMenus();
      chipSel[chartId] = null; onPick(null);
    };
  }

  /* 把一個族群加進／移出篩選集合（E3 的核心：晶片列要**真的篩圖**）。
     只動狀態，不管畫面 —— 卡片與放大視窗各自的「點了要變成什麼樣」由呼叫端接。*/
  function rotToggleGroup(gid) {
    if (!gid) return false;
    ROT.groups = ROT.groups || new Set();
    const on = !ROT.groups.has(gid);
    if (on) ROT.groups.add(gid); else ROT.groups.delete(gid);
    if (!ROT.groups.size) ROT.groups = null;
    saveRotSel();
    return on;
  }

  /* 點卡片下方那一排的族群晶片：**兩張圖真的只剩它**（圖上的族群數會變少），
     同時在排行卡下方原地展開成分股；再點一次取消。
     ★ 順手把 `rankSel`（排行長條的「只亮這一個、其餘壓暗」）清掉 ——
       圖上本來就只剩選到的族群了，再壓暗其他人只會讓人以為畫面壞了。*/
  function pickGroup(gid) {
    if (!gid) return;
    const on = rotToggleGroup(gid);
    rankSel = null;
    const box = $('#rankPanel');
    if (on) {
      const g = (lastRankRows || []).find(x => x.group_id === gid);
      // ★ 2026-09-21：展開的清單改成兩階段共用的那一支（點名字就把個股畫到圖上）
      drillOpen(gid, (g && g.group_name) || (rotGroupMeta[gid] || {}).name || L.gname[gid],
        g ? `佔比 ${fmt.n(g.share, 2)}%　·　變化 ${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp　·　期間報酬 ${fmt.pct(g.ret, 1)}`
          : '', 'rankPanel');
    } else if (DRILL.gid === gid) drillClose();
    else if (box) box.hidden = true;
    wireRotFilter();            // 篩選列的計數與「清除篩選」要跟著出現／消失
    rotRedraw();                // 兩張圖（開著的話連放大視窗）一起重畫
  }
  /* ---------------------------------------------------------------- C4 ＋ A4 的共用狀態
     C4（Andy 2026-09-20）：「資金流向排行、輪動時鐘，改用圖一這樣方式呈現，
     也可以篩選想要的股票」。圖一＝漲跌分佈那張卡的篩選列（`wireDistFilter`）：
     一排 seg ＋ 一個勾選 ＋ 一顆「族群篩選（N）」＋ 一格可捲的複選晶片。
     這裡把同一套搬到排行與時鐘 **共用一份選擇**，所以兩張圖永遠在講同一批族群。

     ★「也可以篩選想要的股票」做成 (a)：篩選面板裡除了族群也能勾**個股**，
       勾了個股就把**它所屬的族群**留在圖上（單位仍然是族群，圖沒有被改成個股圖）。
       做成 (b)「勾族群再下鑽個股」的話，這兩張圖會變成第三個成分股清單 ——
       成分股在排行卡下方的面板與輪動階段看板裡各有一份了，再加一份只是重複。*/
  const ROT_SPAN = 30;             // 軌跡固定畫 30 天（拉Bar 現在是「看哪一天」）
  /* ★ 2026-09-21 Andy 拍板下限 1 -> 0：「看哪一天」要看得到**最新那一天**。
     原本是 A4 第 3 條（2026-09-20）的「前一天 ～ 前三十天」，下限 1。
     兩張卡合併之後排行也跟著這支走，於是「最新」只到前一天（09-17），
     而頁首明明寫著資料更新到 09-18 —— 圖跟字對不起來。
     0 ＝ 資料裡的最後一個交易日（rrg.trail 與 share_daily 的最後一筆）。*/
  const ROT_MIN_BACK = 0;          // 0＝最新一天 ～ 前三十天（Andy 2026-09-21）
  const ROT = { chain: '', groups: null, trail: true, topOnly: false };   // 2026-09-21：個股篩選移除，stocks 一併拿掉
  let rotFrame = ROT_MIN_BACK;     // 時間軸刷到第幾天前
  let rotBackBar = null;           // #rotBack 那支 playBar（播放／＋／−）
  /* 篩選變了就重畫。預設只重畫放大視窗 —— 從總覽直接按「放大」時資金流向頁還沒渲染過，
     這支會在 renderFlow 裡被換成「兩張卡片＋放大視窗」的版本。*/
  let rotRedraw = () => { if (rotZoomDraw) rotZoomDraw(); };
  let rotGroupMeta = {};           // gid → {name, chain}
  let rotF3 = null;                // 最後一次拿到的 flow_v3（晶片列／放大視窗要重建篩選列時用）
  let rotZoomDraw = null;          // 放大視窗開著時＝重畫它的函式；關掉就設回 null
  /* 兩層下拉的開合狀態。勾一個族群就把整排重建一次，所以「剛才開著哪一個」必須記在
     模組層才還原得回來 —— 不記的話複選等於不能用（每勾一次面板就關一次）。
     `rf` 分得出是卡片那排還是放大視窗那排，兩排同時存在時才不會一起彈開。*/
  let rotMenu = null;              // {rf:'flow'|'zoom', kind:'chain'|'group'}；null＝全部收起來
  let rotMenuTop = 0;              // 第二層清單的捲動位置
  let rotSyncCard = () => {};      // 關掉放大視窗時把卡片那張圖同步回來（天數／篩選都共用）

  /* 目前生效的族群集合（null／空＝全部）。
     2026-09-21：個股勾選移除之後只剩「族群晶片 ∩ 產業鏈 ∩ 前 10 大」。*/
  function rotPickSet() {
    const out = new Set();
    if (ROT.groups) ROT.groups.forEach(g => out.add(g));
    if (ROT.chain) {
      // 產業鏈 seg：沒有另外勾東西時＝只看這條鏈；有勾就再和鏈取交集
      const inChain = (rotAllGroups || []).filter(r => (rotGroupMeta[r.gid] || {}).chain === ROT.chain).map(r => r.gid);
      if (!out.size) inChain.forEach(g => out.add(g));
      else [...out].forEach(g => { if (inChain.indexOf(g) < 0) out.delete(g); });
    }
    if (ROT.topOnly) {
      // rotAllGroups 已依成交值佔比排序，直接取前 10
      const top = new Set((rotAllGroups || []).slice(0, 10).map(r => r.gid));
      if (!out.size) top.forEach(g => out.add(g));
      else [...out].forEach(g => { if (!top.has(g)) out.delete(g); });
    }
    return out;
  }

  /* 篩選列本體。結構刻意和 `wireDistFilter()` 一模一樣（seg ＋ 勾選 ＋ 狀態說明）。

     ★ 2026-09-21（Andy：「個股篩選拿掉，下方的族群篩選幫我改到 全部、半導體、…、傳產
       下方 包含資金流向排行，並且需要縮小一點 我只是需要篩選選取」）——
     兩件事一起改，理由都是「這一排是功能鈕，不是閱讀內容」：

       ① **「個股篩選」整顆移除。** 它選的是個股，但這兩張圖的單位是族群，
          勾了個股只是把「它所屬的族群」留在圖上 —— 繞了一圈做的事和直接點族群一樣。
          兩階段下鑽（點族群 → 列成分股 → 點名字畫上盤面）上線之後，
          「我要看某一檔」已經有一條更直接的路，這顆鈕只剩重複。
       ② **族群晶片列從「圖下方」搬到「產業鏈 seg 的正下方」。**
          它和產業鏈 seg 是同一件事的粗細兩層（先挑鏈、再挑族群），
          放在一起才看得出是同一組控制項；而且以前那一排夾在圖與說明之間，
          在窄畫面上會把圖推得很遠。字級與 padding 一起縮小（見 index.html 的
          `.rotfilter .gchips`），因為它是選單不是內文。

     ★★ 2026-09-23（Andy：「圖一二 兩個標籤式都需要做成下拉清單 篩選，所以他會是 族群->題材，
        例如 半導體，下面就會有圖三那些，所以並非所有族群都在同一個下拉清單，
        而是對應族群出現對應個股」）—— 晶片列整排換成**兩層連動的下拉清單**：

          第一層　產業鏈（全部／半導體／一般電子／AI 伺服器／傳產與內需／金融／其他產業別）
          第二層　**被第一層篩過**的族群，checkbox 複選

        為什麼換：48 個族群平鋪成一片要佔三四行，而且那是一個「沒有層次的清單」——
        使用者要先自己知道「矽晶圓屬於半導體」才找得到它。兩層之後，
        第一層先把 48 個收斂成十幾個，第二層的每一項都跟第一層有明確的從屬關係。
        收起來時按鈕上直接寫「半導體 · 已選 3 個」，不必點開才知道自己選了什麼。

        為什麼不用原生 `<select multiple>`：它在手機上是系統的全螢幕選單、吃不到站上的主題色，
        而且看不到族群的顏色點。所以自己做 checkbox 面板。

        沒有退化的東西：複選、「只看前 10 大」、「排行與時鐘顯示全部 N 個族群」那句說明、
        以及**兩排（卡片／放大視窗）共用同一份 ROT 狀態** —— 這支仍然是「對每個 box 各產一份」，
        任何一邊改了都重建兩邊。 */
  /* 族群 → {name, chain} 的對照。第一層（產業鏈）與顯示名稱**全站只有這一份** ——
     資金輪動那兩排下拉與資金去向桑基下面那排下拉都讀它，不准各建一份。*/
  function rotFillMeta(f3) {
    if (!f3) return;
    rotGroupMeta = {};
    ((f3.rrg && f3.rrg.points) || []).forEach(p => {
      rotGroupMeta[p.group_id] = { name: p.group_name, chain: p.chain || '' };
    });
  }

  function wireRotFilter(f3) {
    /* f3 只有第一次（renderFlow）會傳進來；之後下拉清單、放大視窗、清除篩選都會再呼叫一次，
       那些地方手上沒有 f3，所以記在模組層。沒有它就沒有第一層（產業鏈）的選項。*/
    if (f3) rotF3 = f3; else f3 = rotF3;
    const boxes = $$('.rotfilter');
    if (!boxes.length) return;
    rotFillMeta(f3);
    const chains = [...new Set((rotAllGroups || []).map(r => (rotGroupMeta[r.gid] || {}).chain).filter(Boolean))];
    const nG = ROT.groups ? ROT.groups.size : 0;
    const picked = rotPickSet().size;
    const list = rotAllGroups || [];
    /* 第二層的清單＝被第一層篩過的族群。Andy 的原話：「並非所有族群都在同一個下拉清單，
       而是對應族群出現對應個股」—— 所以選了半導體，第二層就只列半導體鏈底下那十幾個。*/
    const sub = ROT.chain ? list.filter(r => (rotGroupMeta[r.gid] || {}).chain === ROT.chain) : list;
    const chainName = ROT.chain ? chainLabel(ROT.chain) : '全部';
    /* 收起來的時候按鈕上要看得到自己選了什麼，不必點開才知道（Andy 要的「半導體 · 已選 3 個」）。*/
    const gSummary = nG ? `${chainName} · 已選 ${nG} 個` : `${chainName} · 全部族群`;
    /* ★ 2026-09-21 合併之後，卡片上只剩**一排**（`data-rf="flow"`）；
       放大視窗打開時會多一排（`data-rf="zoom"`），所以這裡仍然是「對每個 box 各產一份」。
       裡面的控制項一律用 class 不用 id —— 同一個 id 出現兩次的話
       `document.getElementById` 只會抓到第一個，另一排就變成按了沒反應。*/
    boxes.forEach(box => {
      const zoom = box.dataset.rf === 'zoom';
      const rf = box.dataset.rf || 'flow';
      /* `data-sync="n2"` 留著當 CSS 與驗收的抓手（沿用晶片列時代的名字，改名要連動一整批選擇器）。*/
      box.innerHTML = `<div class="rotdd" data-dd="chain" data-sync="n2">
          <button type="button" class="ddbtn" aria-haspopup="listbox" aria-expanded="false"
            title="第一層：先挑產業鏈">產業鏈：<b>${fmt.esc(chainName)}</b><i aria-hidden="true">▾</i></button>
          <div class="ddpanel" role="listbox" aria-label="產業鏈" hidden>
            <button type="button" role="option" class="ddopt${ROT.chain ? '' : ' on'}" data-c=""
              aria-selected="${ROT.chain ? 'false' : 'true'}">全部（${list.length} 個族群）</button>
            ${chains.map(c => {
              const n = list.filter(r => (rotGroupMeta[r.gid] || {}).chain === c).length;
              return `<button type="button" role="option" class="ddopt${ROT.chain === c ? ' on' : ''}" data-c="${fmt.esc(c)}"
                aria-selected="${ROT.chain === c ? 'true' : 'false'}">${fmt.esc(chainLabel(c))}<em>${n}</em></button>`;
            }).join('')}
          </div>
        </div>
        <div class="rotdd wide" data-dd="group">
          <button type="button" class="ddbtn" aria-haspopup="true" aria-expanded="false"
            title="第二層：這條鏈底下的族群，可以複選">族群：<b>${fmt.esc(gSummary)}</b><i aria-hidden="true">▾</i></button>
          <div class="ddpanel" aria-label="族群（可複選）" hidden>
            <div class="ddbar"><span class="muted">${fmt.esc(chainName)}底下 ${sub.length} 個族群，可複選</span>
              <button type="button" class="btn small dd-all">全選</button>
              <button type="button" class="btn small dd-none">全不選</button></div>
            <div class="ddlist">${sub.map(g => `<div class="ddopt chk" style="--c:${L.gcolor[g.gid] || CH.cyan}">
                <label><input type="checkbox" data-g="${g.gid}"${ROT.groups && ROT.groups.has(g.gid) ? ' checked' : ''}>
                  <span class="nm">${fmt.esc(g.name)}</span></label>
                <a class="go" href="#industry/group/${g.gid}" title="進族群頁">→</a></div>`).join('')
              || '<div class="muted" style="padding:8px">這條鏈目前沒有族群資料</div>'}</div>
          </div>
        </div>
        <label class="rotchk"><input type="checkbox" class="rot-top10" ${ROT.topOnly ? 'checked' : ''}>只看前 10 大</label>
        ${(nG || ROT.chain || ROT.topOnly) ? '<button class="btn small rot-clear">清除</button>' : ''}
        <span class="muted rot-note">${picked ? `排行與時鐘都只看這 ${picked} 個族群`
          : `排行與時鐘顯示全部 ${list.length} 個族群`}${nG ? `（其中 ${nG} 個是你自己勾的，再勾一次取消）`
          : '　·　先挑產業鏈，再從第二個清單勾族群（可複選）'}</span>`;

      /* 重建之後要把「剛才打開的那個下拉」原樣還原 —— 勾一個族群就整排重建，
         不還原的話使用者每勾一個就被關掉一次，複選等於不能用。*/
      $$('.rotdd', box).forEach(dd => {
        const kind = dd.dataset.dd;
        const btn = dd.querySelector('.ddbtn');
        const pan = dd.querySelector('.ddpanel');
        const lst = dd.querySelector('.ddlist');
        if (rotMenu && rotMenu.rf === rf && rotMenu.kind === kind) {
          pan.hidden = false; dd.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
          if (lst) lst.scrollTop = rotMenuTop;      // 捲動位置也要留，不然勾一個彈回最上面
        }
        if (lst) lst.onscroll = () => { rotMenuTop = lst.scrollTop; };
        btn.onclick = (ev) => {
          ev.stopPropagation();
          const willOpen = pan.hidden;
          rotCloseMenus();
          if (willOpen) {
            rotMenu = { rf, kind }; if (kind === 'group') rotMenuTop = 0;
            pan.hidden = false; dd.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
          }
        };
        // Esc 關掉並把焦點還給按鈕（鍵盤使用者不能被關在面板裡）
        dd.onkeydown = (ev) => { if (ev.key === 'Escape') { ev.stopPropagation(); rotCloseMenus(); btn.focus(); } };
      });

      // 第一層：挑產業鏈。挑完直接把第二層打開 —— 這就是「族群 → 題材」兩層連動要的動作。
      $$('.rotdd[data-dd="chain"] .ddopt', box).forEach(b => b.onclick = () => {
        ROT.chain = b.dataset.c;
        rotPruneGroups();                       // 第二層換了一批，留著別鏈的勾選只會讓摘要對不上畫面
        rotMenu = { rf, kind: 'group' }; rotMenuTop = 0;
        wireRotFilter(f3); rotRedraw();
      });
      /* 第二層：勾族群＝真的改 `ROT.groups`（兩張圖一起篩），右邊的 → 才是進族群頁。
         放大視窗那一排只做「切換＋重畫」—— `pickGroup` 還會去展開排行卡下方的成分股面板，
         而那張面板整個被遮罩蓋住，使用者看不到，等於按了沒反應。*/
      $$('.rotdd[data-dd="group"] .ddlist input[type="checkbox"]', box).forEach(c => c.onchange = () => {
        rotMenu = { rf, kind: 'group' };         // 複選：勾完不收起來
        const gid = c.dataset.g;
        if (zoom) { rotToggleGroup(gid); wireRotFilter(f3); rotRedraw(); } else pickGroup(gid);
      });
      /* 「→ 進族群頁」刻意放在 `<label>` 外面：放在裡面的話點它會連帶觸發 label
         把 checkbox 也勾掉（瀏覽器的原生行為，不是靠監聽器擋得掉的）。*/
      $$('.rotdd[data-dd="group"] .ddopt .go', box).forEach(a => a.onclick = () => { rotCloseMenus(); });
      const all = box.querySelector('.dd-all');
      if (all) all.onclick = () => {
        ROT.groups = ROT.groups || new Set();
        sub.forEach(g => ROT.groups.add(g.gid));
        saveRotSel(); rotMenu = { rf, kind: 'group' }; wireRotFilter(f3); rotRedraw();
      };
      const none = box.querySelector('.dd-none');
      if (none) none.onclick = () => {
        if (ROT.groups) { sub.forEach(g => ROT.groups.delete(g.gid)); if (!ROT.groups.size) ROT.groups = null; }
        saveRotSel(); rotMenu = { rf, kind: 'group' }; wireRotFilter(f3); rotRedraw();
      };
      const t10 = box.querySelector('.rot-top10');
      if (t10) t10.onchange = () => { ROT.topOnly = t10.checked; wireRotFilter(f3); rotRedraw(); };
      const clr = box.querySelector('.rot-clear');
      if (clr) clr.onclick = () => {
        ROT.chain = ''; ROT.groups = null; ROT.topOnly = false;
        rotMenu = null;
        saveRotSel(); wireRotFilter(f3); rotRedraw();
      };
    });
  }

  /* 換了產業鏈就把不屬於這條鏈的勾選丟掉。
     理由是「按鈕上的摘要要跟畫面一致」：留著別鏈的族群，`rotPickSet()` 取交集之後會變成空集合
     （＝退回全部），但按鈕上還寫著「已選 3 個」—— 使用者會以為圖壞了。*/
  function rotPruneGroups() {
    if (!ROT.chain || !ROT.groups) return;
    [...ROT.groups].forEach(g => { if ((rotGroupMeta[g] || {}).chain !== ROT.chain) ROT.groups.delete(g); });
    if (!ROT.groups.size) ROT.groups = null;
    saveRotSel();
  }

  /* 收掉所有打開的下拉（點別處、Esc、換頁都會走這裡）。
     ★ 一定要對「全站所有 .rotdd」下手，不是只對某一個 box ——
       放大視窗開著時卡片那排也在 DOM 裡，只收一邊會留下一個關不掉的浮層。*/
  function rotCloseMenus() {
    rotMenu = null;
    $$('.rotdd').forEach(dd => {
      dd.classList.remove('open');
      const p = dd.querySelector('.ddpanel'); if (p) p.hidden = true;
      const b = dd.querySelector('.ddbtn'); if (b) b.setAttribute('aria-expanded', 'false');
    });
  }
  // 點面板以外的地方就收起來；Esc 不管焦點在哪都收得掉（面板裡的 Esc 由 dd.onkeydown 先接走）
  document.addEventListener('click', (e) => {
    if (!rotMenu) return;
    if (e.target && e.target.closest && e.target.closest('.rotdd')) return;
    rotCloseMenus();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && rotMenu) rotCloseMenus(); });

  /* 選擇要記住（Andy 的驗收會檢查 localStorage 真的寫進去）。
     只存「使用者自己勾的」兩組，seg 與前 10 大是一眼就看得出來的狀態，不必記。*/
  function saveRotSel() {
    try {
      localStorage.setItem('tw.rot.filter', JSON.stringify({
        groups: ROT.groups ? [...ROT.groups] : null,
      }));
    } catch (e) { /* 私密視窗 */ }
  }
  (function loadRotSel() {
    try {
      const o = JSON.parse(localStorage.getItem('tw.rot.filter') || 'null');
      if (o && o.groups && o.groups.length) ROT.groups = new Set(o.groups);
      /* ★ 2026-09-21：舊版存進去的 `stocks` 直接忽略（個股篩選已移除）。
         不用特地去刪那個鍵 —— 這裡不讀它，它就不會再影響任何東西；
         主動刪反而會在使用者同時開著舊分頁時互相打架。*/
    } catch (e) { /* 忽略壞掉的值 */ }
  })();

  /* A4 第 7 條的後半：「新增軌跡是可以開啟關閉」。
     關掉之後線還在（series 數量不變，highlightClock 認 gid 的那段就不用改），
     只是資料清空 —— 所以「軌跡有沒有關掉」量的是**點數**，不是 series 數。*/
  function wireRotTrailToggle(redraw, boxId) {
    const box = $('#' + (boxId || 'rotTools')); if (!box) return;
    /* ★ class 不用 id：卡片與放大視窗各有一個軌跡開關，
       同一個 id 出現兩次的話 getElementById 只會抓到第一個，另一個就變成按了沒反應
       （這正是 Andy 說的「放大之後的功能都沒反應」那一類的坑）。*/
    box.innerHTML = '<label class="rotchk"><input type="checkbox" class="rot-trail"'
      + (ROT.trail ? ' checked' : '') + '>顯示軌跡</label>'
      /* ★ 2026-09-20：文案跟著改成漸進式的語意。以前寫「這 30 天走過的路」，
         那是「整條路一開始就畫好」的說法，和 Andy 要的「只有經過才留下軌跡」剛好相反。*/
      + '<span class="muted">大圈＝你選的那一天；線＝牠<b>已經走過</b>的那一段'
      + '（刷到「前 30 天」只剩起點，往今天刷才一天一天長出來）</span>';
    const c = $('.rot-trail', box);
    if (c) c.onchange = () => {
      ROT.trail = c.checked;
      // 兩邊的勾選狀態要一致（放大視窗開著時卡片那個也要跟著打勾）
      $$('.rot-trail').forEach(x => { x.checked = ROT.trail; });
      redraw();
    };
  }

  /* ================================================================ 兩階段下鑽（Andy 2026-09-21）
     他的原話：「"輪動時鐘" &"資金去向" 會分兩階段，第一階段式顯示族群，
     而點擊族群後可以顯示對應個股，也可以點擊，並顯示在圖上，
     一樣維持有既有功能，以上止差別資訊完整度」。

       階段一　圖上是族群（＝原本的樣子；篩選／播放／看哪一天／軌跡／放大／族群晶片全部沒動）
       階段二　點族群（時鐘上的點、資金去向的節點、排行的長條、下方的族群晶片都算）
               → 在圖旁邊列出它的成分股，依成交值排序
       階段三　點成分股 → 那一檔**畫到圖上**：時鐘多一顆空心圓＋虛線軌跡、
               資金去向在它所屬的族群底下多一個葉節點。再點一次拿掉。
       回到階段一　麵包屑的「全部族群」、面板的「收起 ✕」、或按 ESC。

     ★ 兩張圖共用**同一份**狀態與同一個返回機制（不是各寫一套）——
       它們在同一頁、講的是同一批族群；各記各的話，使用者在時鐘下鑽了晶圓代工、
       滑到資金去向卻停在別的族群，他會以為其中一張壞了。
     ★ 清單沿用全站的 `.hpanel` / `.hpanel .ms`（固定高度＋自己的捲軸），
       不另開第三種清單樣式 —— 那正是 E3「兩份長得一樣、行為卻不同的清單」的教訓。*/
  const DRILL = {
    gid: null, name: '', stocks: new Set(),
    data: null,           // rrg_members.json（下鑽時才抓）
    state: '',            // ''｜loading｜ok｜fail
    notes: {},            // panelId → 那個面板專屬的一行說明（例如資金去向的「這一天」）
    /* ★ 2026-09-21（Andy：「當點擊 AI 伺服器第一個 Node 右邊應當顯示 AI 伺服器，
       並下面多出裡面還蓋族群，並且都具備下拉選單可以看個股」）——
       多一個「產業鏈」階段。以前只有「族群 → 個股」兩階，點產業鏈節點右邊什麼都不會發生，
       等於圖上最粗的那幾個點是死的。
       chain 與 gid 可以同時有值：那代表「從 AI 伺服器鏈點進 CCL 銅箔基板」，
       麵包屑要寫成「‹ AI 伺服器 › CCL 銅箔基板」，返回鍵回到鏈而不是直接關掉 ——
       「點擊優先在原地展開」的另一面是「返回也要一階一階回」。*/
    chain: null,          // 產業鏈 id（cid）
    chainName: '',
    chainRows: [],        // [{gid, name, v, share, chg}]：點下去那一刻的族群排序快照
    open: new Set(),      // 鏈模式下被展開（下拉）的族群 gid
  };
  // 哪一個面板服務哪一張圖（兩個都吃同一份 DRILL）
  const DRILL_PANELS = ['rankPanel', 'sankeyPanel'];

  /* 個股的輪動座標是**獨立一支 JSON**，而且下鑽時才抓（lazy load）。
     為什麼不併進 flow_v3：那一份是進站就要載的，把 36 族群 × 10 檔 × 31 天塞進去，
     連只想看總覽的人都要多等它。*/
  function drillLoad() {
    if (DRILL.state === 'ok' || DRILL.state === 'loading') return Promise.resolve(DRILL.data);
    DRILL.state = 'loading';
    return load('rrg_members', { fallback: null }).then(d => {
      DRILL.data = (d && typeof d === 'object' && !Array.isArray(d)) ? d : null;
      DRILL.state = DRILL.data ? 'ok' : 'fail';
      return DRILL.data;
    });
  }
  // 這個族群「畫得上去」的個股：code → 它的座標與軌跡（後端算不出來的根本不會出現）
  function drillMembers(gid) {
    const out = {};
    ((DRILL.data || {})[gid] || []).forEach(x => { out[String(x.code)] = x; });
    return out;
  }
  /* 已經被畫到圖上的個股，**形狀和族群的 rotRows() 一模一樣**。
     故意共用同一個形狀：時鐘的回放、軌跡、正規化尺度全部是照那個形狀寫的，
     個股再長一套的話兩邊遲早走鐘（後端的 rrg_axes 也是同一個理由）。*/
  function drillRotRows() {
    if (!DRILL.gid || !DRILL.stocks.size) return [];
    const mm = drillMembers(DRILL.gid);
    const out = [];
    DRILL.stocks.forEach(code => {
      const x = mm[String(code)];
      if (!x || x.x == null || x.y == null) return;      // 樣本不足的不畫（後端也不輸出）
      out.push({
        gid: 'stk:' + code, code: String(code), name: x.name || String(code),
        lbl: (x.name || code) + ' ' + code, share: x.share || 0, trail: x.trail || [],
        rs: x.x, mo: x.y, stage: x.quadrant || stageOf(x.x, x.y), was: null, moved: false,
        isStock: true, gidOf: DRILL.gid, gname: DRILL.name, has_page: !!x.has_page,
      });
    });
    return out;
  }

  /* keepChain＝這一次下鑽是「從產業鏈面板點進去的」，麵包屑要保留上一階。
     其餘入口（族群晶片、圖上的族群節點、輪動時鐘）都是直接跳到族群那一階，
     這時候要把鏈清掉 —— 不清的話麵包屑會寫著一條你根本沒點過的鏈。*/
  function drillOpen(gid, gname, note, panelId, keepChain) {
    if (!gid) return;
    gid = String(gid);
    if (!keepChain && DRILL.chain) { DRILL.chain = null; DRILL.chainName = ''; DRILL.chainRows = []; DRILL.open = new Set(); }
    const same = DRILL.gid === gid;
    const had = DRILL.stocks.size;
    if (panelId) DRILL.notes[panelId] = note || '';
    else if (note != null) DRILL.notes.rankPanel = note;
    DRILL.gid = gid;
    DRILL.name = gname || L.gname[gid] || gid;
    // 換族群就把上一個族群畫上去的個股清掉：盤上混著兩個族群的成分股就分不出誰是誰了
    if (!same) DRILL.stocks = new Set();
    renderDrillPanels();
    if (DRILL.state !== 'ok') drillLoad().then(() => renderDrillPanels());
    if (!same && had) drillRedraw();                     // 只有真的少掉點才需要重畫
  }

  /* 點產業鏈節點：右邊列出「這條鏈底下的族群」，每一列可以就地展開看個股。
     rows 是點下去那一刻算好的快照（值來自目前這一天的桑基資料），
     不在面板裡自己再算一次 —— 面板要是自己算，拖時間軸時兩邊就會對不起來。*/
  function drillOpenChain(cid, cname, rows, note, panelId) {
    if (!cid) return;
    const same = DRILL.chain === cid;
    const had = DRILL.stocks.size;
    if (panelId) DRILL.notes[panelId] = note || '';
    DRILL.chain = String(cid);
    DRILL.chainName = cname || String(cid);
    DRILL.chainRows = rows || [];
    if (!same) DRILL.open = new Set();
    // 回到「整條鏈」這一階：族群層級的聚焦與畫上圖的個股都要收掉，不然圖上會留著上一階的殘影
    DRILL.gid = null; DRILL.name = ''; DRILL.stocks = new Set();
    renderDrillPanels();
    if (had) drillRedraw();
  }

  /* 回到階段一。三個入口（麵包屑／收起 ✕／ESC）都走這一支，
     所以「返回之後圖上剩下什麼」只有一種答案。*/
  function drillClose() {
    const had = DRILL.stocks.size;
    DRILL.gid = null; DRILL.name = ''; DRILL.stocks = new Set(); DRILL.notes = {};
    DRILL.chain = null; DRILL.chainName = ''; DRILL.chainRows = []; DRILL.open = new Set();
    DRILL_PANELS.forEach(id => { const b = $('#' + id); if (b) { b.hidden = true; b.dataset.gid = ''; b.dataset.sig = ''; } });
    // 排行的「只亮這一個族群」與資金去向的聚焦也一起還原，不然圖上會留著壓暗的殘影
    if (rankSel) { rankSel = null; highlightClock(null); }
    if (chipSel.sankey) chipSel.sankey = null;
    if (sankeyState) { sankeySel = null; renderSankey(sankeyState.sd, sankeyState.k, null); }
    if (had) drillRedraw();
  }

  /* 從族群那一階退回產業鏈那一階（麵包屑左邊那顆鈕）。
     圖上的聚焦也要跟著從 {gid} 換成 {chain}，不然清單回到整條鏈、圖卻還壓著只看一個族群。*/
  function drillBackToChain() {
    const cid = DRILL.chain; if (!cid) return drillClose();
    const had = DRILL.stocks.size;
    DRILL.gid = null; DRILL.name = ''; DRILL.stocks = new Set();
    const rank = $('#rankPanel'); if (rank) { rank.hidden = true; rank.dataset.gid = ''; rank.dataset.sig = ''; }
    if (rankSel) { rankSel = null; highlightClock(null); }
    chipSel.sankey = null;
    renderDrillPanels();
    if (sankeyState) { sankeySel = { chain: cid }; renderSankey(sankeyState.sd, sankeyState.k, { chain: cid }); }
    else if (had) drillRedraw();
  }

  function drillToggleStock(code) {
    code = String(code);
    if (DRILL.stocks.has(code)) DRILL.stocks.delete(code); else DRILL.stocks.add(code);
    renderDrillPanels();
    drillRedraw();
  }

  // 兩張圖一起重畫（狀態是共用的，只重畫一邊就會出現「另一邊沒跟上」）
  function drillRedraw() {
    try { if (typeof rotRedraw === 'function') rotRedraw(); } catch (e) { /* 時鐘還沒建好 */ }
    if (sankeyState) { try { renderSankey(sankeyState.sd, sankeyState.k, sankeySel); } catch (e) { /* 同上 */ } }
  }

  function renderDrillPanels() { DRILL_PANELS.forEach(renderDrillPanel); }

  /* 階段〇：整條產業鏈。只有資金去向那一欄畫得出來（輪動時鐘的單位是族群，沒有鏈這一層），
     所以 rankPanel 在鏈模式下維持收起 —— 與其給它一份看起來像壞掉的空清單，不如不開。*/
  function renderDrillChainPanel(box, panelId) {
    const rows = DRILL.chainRows || [];
    const extra = DRILL.notes[panelId] || '';
    const sig = ['chain', DRILL.chain, rows.length, [...DRILL.open].sort().join(','), extra].join('|');
    if (box.dataset.sig === sig && !box.hidden) return;
    box.dataset.sig = sig; box.dataset.gid = '';
    const det = D.groups_detail || {};
    const li = rows.map(r => {
      const col = L.gcolor[r.gid] || CH.cyan;
      const on = DRILL.open.has(r.gid);
      const ms = ((det[r.gid] || {}).members || []).slice()
        .map(m => ({ ...m, tv: +m.turnover || 0 })).sort((a, b) => b.tv - a.tv);
      const sum = ms.reduce((s, m) => s + m.tv, 0) || 1;
      /* 族群那一列橫跨整排（grid-column:1/-1），所以它底下展開的個股會自己另起一行，
         而且還是走 .hpanel .ms 的多欄格線 —— 不用為了「下拉」另外發明一套版面。*/
      /* 兩行：第一行是「▸ 族群名　◎」，第二行才是數字。
         右欄只有 300px，硬擠成一行的話族群名會被折成「CCL 銅箔／基板」、
         「4 檔」還會被推到下一行 —— 看起來像壞掉（1440px 截圖量到的）。*/
      const head = `<a class="dp grow${on ? ' ison' : ''}" data-g="${fmt.esc(r.gid)}"`
        + ` style="border-color:${on ? col : 'transparent'};--c:${col}"`
        + ` title="${fmt.esc(r.name)}　${ms.length} 檔　${on ? '再點一次收起來' : '點一下展開成分股'}">`
        + `<span class="tw2">${on ? '▾' : '▸'}</span>`
        + `<span class="nm">${fmt.esc(r.name)}</span>`
        + `<span class="c go" data-only="1" title="只看這個族群（圖上其餘壓暗）">◎</span>`
        + `<span class="g">${fmt.yi(r.v)}　<b>${fmt.n(r.share * 100, 1)}%</b>`
        + (r.chg == null ? '' : `　<b class="${fmt.cls(r.chg)}">${fmt.pct(r.chg)}</b>`)
        + `　${ms.length} 檔</span></a>`;
      if (!on) return head;
      const kids = ms.length ? ms.map(m => {
        const code = String(m.code);
        return `<a class="dp sub" data-code="${fmt.esc(code)}" data-tv="${Math.round(m.tv)}"`
          + `${m.has_page ? ` href="#stock/${fmt.esc(code)}"` : ''} title="進個股頁">`
          + `<span>${fmt.esc(m.name || code)}</span><span class="c">${fmt.esc(code)}</span>`
          + `<span class="g">${fmt.yi(m.tv)}　${fmt.n(m.tv / sum * 100, 1)}%　`
          + `<b class="${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct)}</b></span></a>`;
      }).join('') : '<a class="dp sub muted">這個族群的成分股整理中</a>';
      return head + kids;
    }).join('');
    box.hidden = false;
    box.innerHTML = `<div class="hh">
        <button class="btn small" data-all="1" title="回到全部產業鏈（按 ESC 也可以）">‹ 全部族群</button>
        <b>› ${fmt.esc(DRILL.chainName)}</b>
        <span class="m">${rows.length} 個族群 · 依成交值排序</span>
        <span class="sp"></span>
        <button class="btn small" data-x="1">收起 ✕</button></div>
      <div class="note" style="margin:6px 0 0">點族群名稱＝<b>就地展開</b>它的成分股（再點一次收起來）；展開後點個股就進個股頁；最右邊的 <b>◎</b> 是「圖上只看這個族群」。${extra ? '　' + extra : ''}</div>
      ${rows.length ? `<div class="ms tree">${li}</div>` : '<div class="empty">這條產業鏈今天沒有量</div>'}`;
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => drillClose();
    const all = box.querySelector('[data-all]'); if (all) all.onclick = () => drillClose();
    $$('.ms a.grow', box).forEach(a => {
      a.onclick = (e) => {
        e.preventDefault();
        const gid = a.dataset.g;
        // ◎ ＝ 走到下一階（族群），麵包屑保留「‹ AI 伺服器」這一層
        if (e.target && e.target.dataset && e.target.dataset.only) {
          const r = (DRILL.chainRows || []).find(z => z.gid === gid) || {};
          drillOpen(gid, r.name || L.gname[gid] || gid, DRILL.notes[panelId], panelId, true);
          chipSel.sankey = gid;
          if (sankeyState) renderSankey(sankeyState.sd, sankeyState.k, { gid });
          return;
        }
        if (DRILL.open.has(gid)) DRILL.open.delete(gid); else DRILL.open.add(gid);
        renderDrillPanel(panelId);
      };
    });
  }

  function renderDrillPanel(panelId) {
    const box = $('#' + panelId); if (!box) return;
    const gid = DRILL.gid;
    if (!gid && DRILL.chain && panelId === 'sankeyPanel') return renderDrillChainPanel(box, panelId);
    if (!gid) { box.hidden = true; box.dataset.gid = ''; box.dataset.sig = ''; return; }
    const det = (D.groups_detail || {})[gid] || {};
    const ms = (det.members || []).slice().map(m => ({ ...m, tv: +m.turnover || 0 }))
      .sort((a, b) => b.tv - a.tv);
    const mm = drillMembers(gid);
    const nRRG = Object.keys(mm).length;
    const extra = DRILL.notes[panelId] || '';
    /* ★ 播放中每 420ms／650ms 就會重畫一次圖，但這一欄的內容只跟
       「哪個族群 × 選了哪幾檔」有關。整份 196 列重建一次要 DOM 全換，
       不擋的話播放會跟著卡（sankeyStockPanel 當初就是為了這件事才加快取的）。*/
    const sig = [gid, DRILL.chain || '', [...DRILL.stocks].sort().join(','), DRILL.state, ms.length, extra].join('|');
    if (box.dataset.sig === sig && !box.hidden) return;
    box.dataset.sig = sig; box.dataset.gid = String(gid);
    const sum = ms.reduce((s, m) => s + m.tv, 0) || 1;
    const gname = DRILL.name || det.group_name || gid;
    const col = L.gcolor[gid] || CH.cyan;
    /* 拿不到個股輪動資料時**不要讓整張圖變空白**，也不要默默什麼都不做 ——
       清單照列（那一份來自 groups_detail，本來就在），只是講清楚畫不上去而已。*/
    const warn = DRILL.state === 'loading' ? '個股輪動資料載入中…'
      : DRILL.state === 'fail' ? '這個族群的個股輪動資料還沒算出來（下一輪盤後管線就會有），所以現在只能看清單，還畫不到時鐘上。'
        : nRRG ? '' : '這個族群的個股輪動資料還沒算出來（上市未滿 50 個交易日的個股本來就不會有），所以現在只能看清單。';
    box.hidden = false;
    box.innerHTML = `<div class="hh">
        <button class="btn small" data-all="1" title="${DRILL.chain ? '回到「' + fmt.esc(DRILL.chainName) + '」這條產業鏈' : '回到只看族群（按 ESC 也可以）'}">‹ ${DRILL.chain ? fmt.esc(DRILL.chainName) : '全部族群'}</button>
        <b>› ${fmt.esc(gname)}</b>
        <span class="m">${ms.length} 檔 · 依成交值排序${DRILL.stocks.size ? ` · 已畫上圖 ${DRILL.stocks.size} 檔` : ''}</span>
        <span class="sp"></span>
        <a class="pill cyan" href="#industry/group/${fmt.esc(gid)}">進族群頁 →</a>
        <button class="btn small" data-x="1">收起 ✕</button></div>
      <div class="note" style="margin:6px 0 0">點名字＝把這一檔畫到圖上（時鐘是<b>空心圓</b>、資金去向是多一個葉節點），再點一次拿掉；點最右邊的 <b>→</b> 進個股頁。${extra ? '　' + extra : ''}${warn ? `<br><span class="muted">${warn}</span>` : ''}</div>
      ${ms.length ? `<div class="ms">${ms.map(m => {
        const code = String(m.code);
        const on = DRILL.stocks.has(code);
        const can = !!mm[code];
        return `<a data-code="${fmt.esc(code)}" data-tv="${Math.round(m.tv)}"${m.has_page ? ` href="#stock/${fmt.esc(code)}"` : ''}`
          + ` class="dp${on ? ' ison' : ''}${can ? '' : ' noplot'}"${on ? ` style="border-color:${col};background:${hexA(col, .18)}"` : ''}`
          + ` title="${can ? (on ? '再點一次就從圖上拿掉' : '點一下把它畫到圖上') : '上市未滿 50 個交易日，算不出輪動座標，畫不到時鐘上'}">`
          + `<span>${on ? '● ' : ''}${fmt.esc(m.name || code)}</span><span class="c">${fmt.esc(code)}</span>`
          + `<span class="g">${fmt.yi(m.tv)}　${fmt.n(m.tv / sum * 100, 1)}%　<b class="${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct)}</b></span>`
          + (m.has_page ? '<span class="c go" title="進個股頁">→</span>' : '') + '</a>';
      }).join('')}</div>` : '<div class="empty">這個族群的成分股整理中</div>'}`;
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => drillClose();
    /* 返回鍵一次只退一階：從鏈點進來的就退回鏈，直接點族群進來的才整個關掉。
       一次退到底的話，Andy 從 AI 伺服器鏈點進 CCL 之後想回去看隔壁族群，
       得重新在圖上找到那個節點再點一次 —— 那正是「不要動不動就把人帶離現場」。*/
    const all = box.querySelector('[data-all]');
    if (all) all.onclick = () => { if (DRILL.chain) return drillBackToChain(); drillClose(); };
    $$('.ms a', box).forEach(a => {
      a.onclick = (e) => {
        e.preventDefault();                    // 點整列＝畫到圖上，不是跳頁
        const code = a.dataset.code;
        if (e.target && e.target.classList.contains('go')) return goStock(code);
        // 沒有座標就不要假裝畫得上去（樣本不足要標示，不可以給一個假的點）
        if (!drillMembers(DRILL.gid)[code]) return;
        drillToggleStock(code);
      };
    });
  }

  /* ESC 回到階段一。放大視窗開著時先讓它關（openZoom 自己綁了一個 ESC）——
     一次按下去兩件事同時發生，使用者會覺得「按一下跳太多」。*/
  /* ★ 2026-09-21：條件從「只看 DRILL.gid」放寬到「任何下鑽狀態」。
     以前只點了產業鏈（或只點了族群晶片做篩選）時 DRILL.gid 還是 null，
     按 ESC 完全沒反應 —— 使用者會以為圖卡住了。
     點桑基圖空白處走的也是這一支（Andy：「當點擊背景時會恢復 Default 狀態」），
     ESC 與空白處一定要是同一套，不要寫第二個「復原」。*/
  const drillActive = () => !!(DRILL.gid || DRILL.chain || sankeySel || DRILL.stocks.size);
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || !drillActive()) return;
    const ov = document.getElementById('zoomOv');
    if (ov && !ov.hidden) return;
    drillClose();
  });

  let lastRankRows = null;         // 給 pickGroup 查佔比／變化用
  /* 兩張圖共用的族群名單。輪動資料（rrg.points）是最完整的一份 ——
     排行只畫得下 15 檔、時鐘只畫得下 16 顆點，但**晶片列要列全部**，
     否則就會出現 Andy 講的「有些篩選不到」。*/
  let rotAllGroups = null;

  /* 排行選了哪個族群（null＝沒選）。輪動時鐘用它決定誰亮誰暗。*/
  let rankSel = null;
  /* 只亮某一個族群：其餘的點與尾巴壓到 0.18 透明度。
     用 setOption 就地改（notMerge 預設 false），不重建圖表 ——
     重建的話尾巴會整個重畫一次，看起來像閃了一下。*/
  /* ★ 2026-09-21：`gid` 不在時鐘上時**什麼都不要做**。
     這是合併成一張卡之後才浮出來的既有 bug：時鐘為了看得清楚只畫前 16 個族群，
     而排行是依「佔比變化」排的 —— 變化最大的那一個未必在成交值前 16 名裡。
     以前的寫法是「不等於 gid 的一律壓到 0.18」，所以點到一個時鐘上沒有的族群時，
     16 個全部被壓暗、整張圖灰掉（實測 lo=hi=0.18），看起來像壞掉。
     現在先確認它真的畫在上面，不在就原樣不動，並回傳 false 讓呼叫端去說明。*/
  function highlightClock(gid) {
    const el = document.getElementById('rotClock');
    const c = el && window.echarts && echarts.getInstanceByDom(el);
    if (!c) return false;
    const o = c.getOption(); if (!o || !o.series) return false;
    if (gid) {
      const on = (o.series || []).some(sr => sr.gid === gid
        || (sr.type === 'scatter' && (sr.data || []).some(d => d && d.row && d.row.gid === gid)));
      if (!on) return false;                     // 不在時鐘上：不要把整張圖壓暗
    }
    const series = o.series.map(sr => {
      const own = sr.gid;                         // renderRotClock 幫每條尾巴都標了 gid
      if (sr.type === 'line') {
        const on = !gid || own === gid;
        return { lineStyle: { opacity: on ? 1 : 0.12 }, itemStyle: { opacity: on ? 1 : 0.12 } };
      }
      if (sr.type === 'scatter') {
        return { data: (sr.data || []).map(d => {
          const on = !gid || (d.row && d.row.gid === gid);
          return { ...d, itemStyle: { ...(d.itemStyle || {}), opacity: on ? 1 : 0.18 },
                   label: { ...(d.label || {}), opacity: on ? 1 : 0.18 } };
        }) };
      }
      return {};
    });
    c.setOption({ series }, { notMerge: false, lazyUpdate: true });
    return true;
  }

  /* 名次變化（bump）已於 2026-09-18 整張移除（Andy 圖四：「右邊的名次變化刪掉」），
     那一格改放輪動時鐘。名次資訊沒有消失 —— 排行的 y 軸標籤仍然帶 `3↑` `2↓`，
     tooltip 也仍然寫「名次 7 → 4」。後端的 bump / bumps 欄位先留著不動
     （拿掉要改 pipeline 與測試，這批不順手做），只是前端不再讀它。*/

  /* 資金去向（Andy 2026-09-18 三件）：
     G1 改成**垂直、由上往下**；G2 要有**電流流動感（會動）**；G3 要有**占比 %**。

     G2 的做法：ECharts 的 sankey 沒有內建流動效果。硬換成 graph + lines effect 會失去
     sankey 自己算好的版面，不划算。所以用「相位脈動」—— 每一條連線的透明度依它的**深度**
     錯開相位，逐格推進，看起來就是一波亮度由上往下掃過去，像電流在走。
     只改 lineStyle.opacity（不重算版面），所以很便宜；而且：
       · 使用者系統設定「減少動態效果」就不動（prefers-reduced-motion）
       · 分頁切走就停（visibilitychange），不在背景燒 CPU
       · 換頁時 destroy 掉，不會留下一個永遠在跑的計時器 */
  /* ★ 2026-09-20 改成「小圓點傳輸」（Andy：「從台股成交直到個族群之間會有小圓圈傳輸特效，
     並且資金越多的頻率越高，點點大小越大」）。上面那段「相位脈動」已整段換掉。

     為什麼自己疊一層 canvas，而不是用 ECharts 內建的 lines + effect：
     lines 系列一定要掛在座標系（cartesian2d / geo）上，掛上去就得自己算整張圖的版面，
     等於把 tree 已經算好的位置丟掉。這裡改成在圖的容器裡疊一層透明 canvas，
     節點座標直接跟 zrender 要（`transformCoordToGlobal(0,0)` 回的就是圖表 canvas 的
     像素座標，跟疊上去的那層是同一個座標系），所以圓點一定落在看得到的那條線上。
     曲線用和 ECharts `edgeShape:'curve'` 完全一樣的三次貝茲（控制點在兩端 x 的中點）。

     效能與禮貌（`docs/diagram_specs/dg3d_standard.md` 的效能驗收）：
       · 分頁切到背景就停（visibilitychange），回到前景才續 —— 不在背景燒 CPU
       · 換到站內別的分頁（容器還在 DOM、只是被藏起來）只空轉不畫；
         ★ 這裡不可以直接收掉 —— route() 對已經畫過的 view 不會再跑一次 render，
           收掉之後回到資金流向頁小圓點就永遠不會回來（2026-09-20 實測過）
       · 容器真的離開 DOM、或整張圖重畫時，自己收掉 canvas 與 rAF，不留孤兒計時器
       · 系統設定「減少動態效果」就完全不啟動
       · 一條線上的點數上限 6、總數上限 SANKEY_DOT_MAX，單一 rAF 迴圈畫完 */
  /* ★ 2026-09-20：90 → 170。四層之後要發點的線從 12 條變成
     （5 條產業鏈 ＋ 18 個族群 ＋ 最多 54 檔代表股）＝ 77 條，
     每條至少 1 顆的話 90 顆連「每條線上都有一顆」都做不到，
     最末段（族群 → 代表股）會整排沒有點 —— 那正是 Andy 要的那一段。
     ★ 2026-09-21（Andy：「傳輸密度提升，需要差異大點」）：170 → 420、
       單線上限 5 → 14，而且「錢多」現在同時吃三個通道 —— 點數、點大小、**速度**。
       為什麼要三個一起動：單靠點數的話對比被單線上限夾死（以前最粗 5 顆、最細 1 顆，
       只有 5 倍），而 5 顆和 1 顆在一條 300px 的曲線上看起來都只是「幾顆點」。
       量出來的差別（1500px、最新交易日、實測見回報）：
         改前 最粗 5 顆 / 最細 1 顆 ＝ 5.0 倍，通過率（顆/秒）也是 5.0 倍
         改後 最粗 14 顆 / 最細 1 顆 ＝ 14 倍，通過率 14 × 1.5 ÷ (1 × 0.55) ≈ 38 倍
       ★ 保留「每條線至少 1 顆」（D4 修過的 bug，不要退回去）—— 下面配點那段照舊先發 1 顆。*/
  const SANKEY_DOT_MAX = 420;
  const SANKEY_DOT_LINE_MAX = 14;      // 單一條線最多幾顆點
  /* 一顆點從頭走到尾要幾毫秒。★ 2026-09-21 起**不再固定**：每條線自己帶一個
     `spd`（0.55 ~ 1.5 倍），錢多的線跑得快。所以「頻率（單位時間通過幾顆）」
     ＝ 點數 × 速度，兩個通道相乘才拉得開差距。*/
  const SANKEY_TRAVEL = 2600;
  /* 流量 → 點數／點大小／速度。三支都吃同一個 r（＝這條線的量 ÷ 全期間最大值，0~1）。
     點數用 r^0.8 而不是線性：線性時 r=0.1 只拿到 2.3 顆，中段的族群會整片塌在 1~2 顆，
     看起來就像「只有第一名有點」；^0.8 讓中段拉開到 3~9 顆，兩端的 1 與 14 不變。*/
  const dotN = (r) => Math.max(1, Math.min(SANKEY_DOT_LINE_MAX,
    Math.round(1 + (SANKEY_DOT_LINE_MAX - 1) * Math.pow(Math.max(0, r), 0.8))));
  const dotR = (r) => 1.3 + 4.6 * Math.pow(Math.max(0, r), 0.6);   // 半徑 1.3 ~ 5.9（面積差 20 倍）
  const dotSpd = (r) => 0.55 + 0.95 * Math.max(0, r);              // 0.55 ~ 1.5 倍速
  let sankeyFx = null;
  let sankeyFlows = [];                // 目前這一輪配好的連線（驗收要量密度對比）
  function stopSankeyFlow() { if (sankeyFx) { try { sankeyFx.stop(); } catch (e) { /* 忽略 */ } sankeyFx = null; } }

  /* 把 tree 每個節點的像素座標讀出來（key＝節點名稱，名稱在這張圖裡是唯一的）。
     zrender 換版本時這組 API 有可能變，所以整段包在 try 裡 ——
     讀不到就只是沒有小圓點，不可以讓整張圖掛掉。 */
  function sankeyNodePos(c) {
    try {
      const data = c.getModel().getSeriesByIndex(0).getData();
      const out = {};
      for (let i = 0; i < data.count(); i++) {
        const g = data.getItemGraphicEl(i); if (!g) continue;
        const p = g.transformCoordToGlobal ? g.transformCoordToGlobal(0, 0) : [g.x, g.y];
        if (p && p[0] != null) out[data.getName(i)] = { x: p[0], y: p[1] };
      }
      return out;
    } catch (e) { return null; }
  }

  function startSankeyFlow(el, flows) {
    if (!el || !flows || !flows.length) return null;
    try { if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return null; }
    catch (e) { /* 忽略 */ }
    const cv = document.createElement('canvas');
    cv.className = 'dotfx'; cv.setAttribute('aria-hidden', 'true');
    el.appendChild(cv);
    const g = cv.getContext('2d');
    if (!g) { cv.remove(); return null; }
    const dots = [];
    /* flows 用一層 ref 包起來（不是直接用參數）：換一天時族群的位置完全沒變，
       只有粗細與顆數要換 —— 這時候只換 flowsRef 就好，
       把整層 canvas 拆掉重建會讓小圓點閃一下（2026-09-20 加播放之後每 650ms 就閃一次）。*/
    let flowsRef = flows;
    let raf = null, alive = true;
    const sizeTo = () => {
      const w = el.clientWidth, h = el.clientHeight;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
        cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
        cv.style.width = w + 'px'; cv.style.height = h + 'px';
      }
      return dpr;
    };
    // 和 ECharts edgeShape:'curve' 同一條線：控制點放在兩端 x 的中點
    const bez = (a, b, t) => {
      const mx = (a.x + b.x) / 2, u = 1 - t;
      return [u * u * u * a.x + 3 * u * u * t * mx + 3 * u * t * t * mx + t * t * t * b.x,
        u * u * u * a.y + 3 * u * u * t * a.y + 3 * u * t * t * b.y + t * t * t * b.y];
    };
    const step = (ts) => {
      raf = null;
      if (!alive) return;
      // 容器離開 DOM，或整層 canvas 被別人清掉（例如 empty() 把容器 innerHTML 換掉）就收工
      if (!el.isConnected || !cv.isConnected) { stop(); return; }
      // 換到別的分頁時容器還在 DOM 裡、只是被藏起來（offsetParent 會是 null）：
      // 這時候什麼都不畫，但迴圈留著，回到這一頁就自己接上
      if (el.offsetParent === null) { raf = requestAnimationFrame(step); return; }
      const dpr = sizeTo();
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, cv.width, cv.height);
      dots.length = 0;
      for (const f of flowsRef) {
        for (let i = 0; i < f.n; i++) {
          /* 同一條線上的點等距排開；再乘上這條線自己的速度倍率 ——
             單位時間通過的顆數 ＝ 點數 × 速度，那就是「錢的流量」。*/
          const t = ((ts * (f.spd || 1) / SANKEY_TRAVEL) + f.phase + i / f.n) % 1;
          const p = bez(f.a, f.b, t);
          dots.push({ x: Math.round(p[0]), y: Math.round(p[1]), r: f.size, gid: f.gid, lvl: f.lvl });
          g.beginPath(); g.arc(p[0], p[1], f.size, 0, 6.2832);
          g.fillStyle = f.color; g.fill();
        }
      }
      raf = requestAnimationFrame(step);
    };
    const onVis = () => {
      if (document.hidden) { if (raf) { cancelAnimationFrame(raf); raf = null; } }
      else if (alive && !raf) raf = requestAnimationFrame(step);
    };
    function stop() {
      alive = false;
      if (raf) { cancelAnimationFrame(raf); raf = null; }
      document.removeEventListener('visibilitychange', onVis);
      if (cv.parentNode) cv.parentNode.removeChild(cv);
      dots.length = 0;
    }
    document.addEventListener('visibilitychange', onVis);
    raf = requestAnimationFrame(step);
    return { stop, dots, running: () => !!raf, alive: () => alive, host: el,
      setFlows: (f) => { flowsRef = f || []; } };
  }

  /* 資金去向（Andy 2026-09-18 圖六）：
       「改成水平並且全部都以點跟線呈現，金資越多的 顏色越深也越粗，
         並且一樣都具備相資金輪動的拉Bar 可以觀察並搭配播放功能，
         白色頁面時 顏色不要太深 親和一點」

     所以整張圖從桑基改成**水平的樹**，全部是點跟線
     （層數在 2026-09-20 從三層加到四層，見下面那段註解）。
     - 點的大小、線的粗細、顏色深淺，三者都綁在「這條分支的成交值」上
     - 資料改吃 sankey_daily（獨立檔，60 天），所以可以往回拉、可以播
     - 原本那個「電流沿著深度跑」的脈動整段拿掉：它每 90ms 就 setOption 一次，
       而現在有播放功能了，動的東西已經夠多

     ★ 淺色主題的透明度上限壓到 0.62（深色是 0.95）。
       白底上濃到 0.95 的線會變成一團黑，那正是他說的「顏色不要太深」。*/
  /* ★ 2026-09-20（Andy）：「需要將所有族群固定，只會差別在線條的粗細 和圓圈大小」

     以前每換一天就 `filter(v>0)` 再 `sort` 一次，於是族群整組換掉、位置也全部重排 ——
     拖時間軸看到的是「洗牌」，而他要看的是**同一個族群的錢變多還是變少**。
     現在：
       · 名單與順序固定成 `sankey_daily.groups` 的原始順序（後端依最新一天成交值排一次，之後不動）
       · 當天沒量的族群**留在原位**，畫成最小的點＋最細的線＋壓到 18% 的顏色，
         標籤寫「0.0%」或「無資料」。刻意不隱藏 —— 位置一空掉就等於又在洗牌。
       · 點的大小與線的粗細改成跟**全期間最大值**比（不是當天最大值）。
         跟當天比的話，量能腰斬但仍是第一名的族群畫出來一樣大，等於把他要看的變化抹掉。
       · 每個族群一律配 `SANKEY_KIDS` 個代表股格子，不足的補**看不見的佔位節點**。
         ECharts 的 tree 是按葉子數量分配縱向空間的，葉子數一變族群的 y 就會跳，
         「位置固定」就破功了。

     （聚焦參數在 2026-09-20 從「一個族群 id」換成 {gid} / {chain} 兩種，見下段。）*/
  /* ★★ 2026-09-21（Andy 本人推翻上面那條的**一半**，不是整條）：
       「我這邊提到的即時包含 他突然某個族群、個我變大，會自動交換位置，這點功能需要達成
         另外需新增當我點擊族群 會延伸顯示其他股票…並且這功能都在這圖表內建立
         不是即時的也要，一樣顯示名稱百分比」

     所以「位置固定」從**一條通則**改成**分模式**，兩邊的理由不一樣，不要合併：

       · **歷史回放（拖時間軸／▶ 播放）＝ 位置固定，照舊。**
         回放要看的是「同一個族群這 60 天變粗還是變細」，一洗牌就看不到了 ——
         上面 2026-09-20 那一整段的理由到今天仍然成立，一個字都沒有過期。
       · **即時模式（`SKL.on`）＝ 依當下成交值重排（產業鏈層與族群層都排）。**
         即時要看的是「現在誰突然變大」，而「名次換了」本身就是那個訊號；
         位置鎖死的話，第 8 名衝到第 2 名在畫面上只會變成「那顆點大了一點」。
         每分鐘一輪，名次沒變就不會有任何位移（setOption 合併、座標一樣）。

     換位一定要**補間動畫**，不能瞬間跳 —— 跳一下人眼追不到「誰跟誰換了」，
     那就退化成「圖每分鐘閃一次」。做法是重排時走 `setOption`（合併、保留 series 身分），
     讓 ECharts 自己用 `animationDurationUpdate` 補間；只有版面**型態**真的變了
     （窄畫面翻面）才 `notMerge: true` 整張重建，見下面 `skShape`。

     展開全部成分股（`SANKEY_EXPAND_MAX`）也會讓位置動：ECharts 的 tree 是按葉子數
     分配縱向空間的，某個族群從 3 片葉子變成 20 片，它的兄弟一定會被推開 ——
     這是版面演算法的物理限制，繞不過去。接受它，用同一套動畫緩解。*/
  const SANKEY_KIDS = 3;
  /* 展開之後最多畫幾檔。20 是量出來的：這張圖上 18 個族群，
     除了 `ind_ETF`（356 檔有量）之外最大的是 `bank` 16 檔，其餘都 ≤ 11 檔 ——
     也就是說 20 這條線只會夾到自動桶那一格，真正的題材族群全部畫得完整。
     超過的收成一個「其餘 N 檔 X.X%」節點（量有加回去，不是丟掉）。
     為什麼不畫滿 356 檔：那要 5,700px 的高度，而且每片葉子分不到 16px，
     標籤會整片疊在一起 —— 那不是「完整」，是「看不懂」。*/
  const SANKEY_EXPAND_MAX = 20;
  /* ★ 2026-09-20（Andy）：「半導體產業涵蓋 IC 設計、代工、封測，不應該將他們拆開，
     所以需要整理清楚哪個產業在哪裡…一個節點是半導體產業，後面接續是 IC 設計、代工、封裝」

     他看到的問題是**呈現**，不是數字。查過 `pipeline/compute/flow.py` 的 `_attach_groups()`：
     `ind_*`（半導體業、電子零組件業、ETF…）是「不屬於任何人工族群的股票」的收容桶
     （只有 `group_id.isna()` 才會掛上去），台積電只算在「晶圓代工」裡，量能也是 1/n 拆分的 ——
     所以沒有重複計算。真正的毛病是畫面把收容桶和真族群**並排在同一層**，
     看起來就像半導體被拆成好幾塊。

     所以改成四層：台股成交值 → 產業鏈 → 族群 → 代表股。
     產業鏈這一層直接吃 `groups.yaml` 的 `chains:`（唯一人工維護的分類表，
     28 個族群全部收得進去，沒有落單），後端在 `sankey_daily` 把 `chain_name` 一起送過來。
     `chain: industry` 的收容桶歸到「其他產業別」，不跟真族群並排。

     位置固定這條（2026-09-20 早上拍板）繼續守著，而且現在要多守一層：
       · 產業鏈的順序用**最後一天**的成交值排一次就不再動
       · 族群順序沿用後端 `sd.groups` 的原始順序
       · 每個族群一律配 SANKEY_KIDS 個代表股格子，不足補看不見的佔位節點
     三者都不隨「看哪一天」改變，所以拖時間軸看到的只有粗細與圓圈大小在變。

     sel＝目前聚焦的東西（族群晶片或點節點傳進來）：
       { gid }   只看這個族群      { chain } 只看這條產業鏈
     被排除的整棵子樹**壓暗**而不是拿掉 —— 拿掉位置就又變了。*/
  // 代表股顯示名：後端給的 name 如果是空的或字串 "nan"，一律退回全市場索引的簡稱、再退回代號
  const leafName = (x) => { const n = String((x && x.name) || '').trim();
    return (!n || n.toLowerCase() === 'nan') ? (L.cname[x.code] || x.code) : n; };
  /* 節點名稱是 sankeyNodePos() 的 key，**一定要唯一**（撞名的話小圓點會飛到別人身上）。
     產業鏈名和族群名理論上不會撞，但 groups.yaml 是人工維護的，撞了也不該讓圖壞掉，
     所以撞名時補一個髮際空格（U+200A，看不見、但字串不同）。*/
  const uniqName = (seen, name) => { let n = name; while (seen.has(n)) n += ' '; seen.add(n); return n; };

  /* 族群當天的漲跌幅（%）。產業鏈面板那一欄要「佔比與漲跌」兩個數字，
     而 sankey_daily 只送成交值 —— 漲跌在 groups_today 裡（同樣是最新交易日的口徑）。
     每呼叫一次就掃一遍 117 列太浪費，所以第一次用到時建索引
     （HANDOFF 2026-09-21 記過的熱路徑教訓：逐列轉換一律先拿字典）。*/
  let _gchg = null;
  function gchgOf(gid) {
    if (!_gchg) {
      _gchg = {};
      (D.groups_today || []).forEach(g => { if (g.group_id != null) _gchg[g.group_id] = g.chg_pct; });
    }
    const v = _gchg[gid];
    return v == null ? null : v;
  }

  /* 點族群（或點族群節點）之後右邊那一欄：該族群個股的成交值排序。
     ★ 沿用 `.hpanel` / `.hpanel .ms` 那一套（排行下方的成分股面板、資金集中度側欄都是它），
       固定高度＋自己的捲軸，不另外發明第三種清單樣式。
     ★ 資料來源是 `groups_detail`（最新交易日的全成分股，含成交值）——
       `sankey_daily.leaves` 每天只留前 3 檔，撐不出一份「排序」。
       所以時間軸刷到過去時，標題會明講清單是最新交易日的，不要讓人以為那是那一天的數字。*/
  const sankeyNote = (day, isLatest) => (
    /* 即時模式下圖上的葉子是「價 × 量」的估算，這一欄卻是收盤值 —— 兩邊數字會不一樣。
       不寫出來的話看起來就像其中一邊算錯了（而且無從判斷是哪一邊）。*/
    (SKL.on && !SKL.err && Object.keys(SKL.tv).length)
      ? `即時模式：圖上展開的個股是「價 × 量」的即時估算，這一欄仍是最新交易日（${fmt.esc(day)}）的收盤值，兩者不是同一個時點`
      : isLatest
        ? `依最新交易日（${fmt.esc(day)}）的成交值排序，百分比＝佔這個族群的比重（和圖上展開的葉子同一個分母）`
        : `時間軸目前在 ${fmt.esc(day)}，但成分股排序只有最新交易日的版本（逐日檔每天只留前 3 檔）`);
  /* ★ 2026-09-21：`sankeyStockPanel()` 移除。資金去向與輪動時鐘現在共用同一支
     成分股面板（`renderDrillPanel`），兩階段下鑽的狀態也只有一份。
     留著一支沒有人呼叫的舊面板，只會讓下一個人以為資金去向還有自己的一套。*/
  /* 目前聚焦的東西（{gid} / {chain} / null）。放在外面是因為播放拉Bar 的 onChange
     是在建 playBar 的時候就綁好的閉包，拿不到後來才選的那一個。*/
  let sankeySel = null;
  let sankeyState = null;          // {sd, k}：換寬度要重畫時得知道現在在看哪一天
  /* 容器窄到這個寬度以下就**收掉代表股那一層**（只畫三層）。
     為什麼要收：四層各佔一欄，扣掉右邊留給葉子標籤的 132px 之後，
     390px 的手機一欄只剩 45px —— 族群名和代表股名會整片疊在一起，
     那不是「小」，是「看不懂」。收掉之後族群那一層反而讀得出來，
     而代表股並沒有不見：點族群，下面那一欄就是完整的成交值排序（手機上面板會掉到圖下方）。
     700 這個數字是量出來的：再低於它，「PCB / ABF 載板 41.6% ▲3%」這種長標籤
     就開始壓到隔壁欄。 */
  const SANKEY_NARROW = 700;

  /* ------------------------------------------------ 盤中即時資金去向（Andy 2026-09-21）
     「好那在幫我多新增一個『即時』項目可以點選觀看　在紅框那排」
     （紅框那排＝「看哪一天 − ▬▬ ＋ 最新 ▶」那一列）。

     ★★ 口徑（這一段是整個功能的重點，寫錯整張圖就是假的）

     分母：`Market3.marketAmt` 是台股當日累積成交值（元），盤中就有、**真實值不是估算**
       —— 它來自加權指數那一筆 mis 報價的 `info.v`，大盤三張圖本來每分鐘就會抓。
       但它**只拿來顯示「台股總成交值」那一格**。

     分子：即時報價端點（/quote?ex_ch=…）給的是「最後成交價」與「累積成交量（張）」，
       **沒有每檔的累積成交金額**，所以板塊成交值只能用 `價 × 量 × 1000` 估。

     所以佔比一律是「板塊 ÷ 所有即時板塊加總」，**不拿估算的分子去除真實的 marketAmt** ——
     那個百分比會系統性偏掉（分子低估、分母是全市場，每一格都會偏小，而且偏多少不一定）。

     ★ 1/n 拆分：一檔股票同時掛在兩個手寫板塊時，成交值要各算一半。
       這是後端 `compute/flow.py` 的口徑，實測對得起來（osat 用 1/n 算出 326.9 億，
       `groups_today` 也是 326.9 億；不拆的話是 434.2 億，差 33%）。

     ★ 範圍與誠實標示（不准打折）
       · 手寫板塊（這張圖上目前 17 個、111 檔成分股）→ 每分鐘更新，標「即時」
       · 「〇〇・其他」自動桶（ind_*，光 ETF 一格就 358 檔）→ **做不到**，
         要多 4 個請求/分鐘而且那一格本來就不是題材，一律標「盤後」、
         **不進佔比的分母**（拿盤中的部分成交值去和收盤的整天成交值比，
         上午十點時自動桶會被灌成第一名 —— 那比不做還糟）
       · 成交值本身寫明「估算值」

     請求量：111 檔 ÷ 每批 100 檔 ＝ **2 個請求/分鐘**，沿用 live.js 的 Worker 代理與批次。 */
  const SKL = {
    on: false, busy: false, at: 0, err: '',
    tv: {},            // gid  → 估算成交值（元）
    stv: {},           // code → 估算成交值（元）
    codes: 0, reqs: 0, quoteAt: '', marketAmt: null,
    intraday: true, timer: null,
  };
  const SKL_BATCH = 100;               // 一個請求塞幾檔（live.js 實測 120 檔 OK，留邊際）
  const SKL_MS = 60 * 1000;            // 每分鐘一輪（和 live.js 的盤中節奏一致）
  const isAutoBucket = (gid) => /^ind_/.test(String(gid));

  /* 一檔股票掛在幾個手寫板塊 → 它的成交值要拆成幾份。
     用 groups_detail 的全部 83 個手寫板塊算（不是只算這張圖上的 17 個）——
     後端就是這樣拆的，只算圖上的會把雙掛股灌大。*/
  function sklWeights() {
    const n = {};
    Object.entries(D.groups_detail || {}).forEach(([gid, det]) => {
      if (isAutoBucket(gid)) return;
      (det.members || []).forEach(m => { const c = String(m.code); n[c] = (n[c] || 0) + 1; });
    });
    return n;
  }

  async function sklFetch(sd) {
    if (!window.Live || !window.Live.fetchQuotes) throw new Error('即時報價層還沒載入（live.js）');
    const det = D.groups_detail || {};
    const gids = ((sd && sd.groups) || []).map(g => g.gid).filter(g => !isAutoBucket(g));
    const codes = [], seen = new Set();
    gids.forEach(gid => ((det[gid] || {}).members || []).forEach(m => {
      const c = String(m.code); if (c && !seen.has(c)) { seen.add(c); codes.push(c); }
    }));
    if (!codes.length) throw new Error('這張圖上的板塊還沒有成分股資料，抓不了即時');
    const q = {};
    let reqs = 0;
    for (let i = 0; i < codes.length; i += SKL_BATCH) {
      Object.assign(q, await window.Live.fetchQuotes(codes.slice(i, i + SKL_BATCH)));
      reqs++;
    }
    const w = sklWeights();
    const stv = {}, tv = {};
    let at = '';
    codes.forEach(c => {
      const x = q[c];
      if (!x || x.price == null || x.volume == null) return;
      stv[c] = x.price * x.volume * 1000;          // ★ 估算：端點沒有每檔的累積成交金額
      if (x.time && x.time > at) at = x.time;
    });
    gids.forEach(gid => {
      let sum = 0, hit = 0;
      ((det[gid] || {}).members || []).forEach(m => {
        const c = String(m.code);
        if (stv[c] == null) return;
        hit++; sum += stv[c] / Math.max(1, w[c] || 1);
      });
      if (hit) tv[gid] = sum;
    });
    if (!Object.keys(tv).length) throw new Error('報價回來了，但沒有一個板塊算得出成交值');
    /* 分母那一格：Market3 有多久沒更新就自己叫它一次。使用者開過「總覽」的話
       它本來就每分鐘在跑（零額外請求）；沒開過的話這裡會多 3 個請求，
       而那是「台股總成交值」這一格唯一的真實來源，值得。*/
    try {
      const M = window.Market3;
      if (M) {
        if (!M.lastAt || Date.now() - M.lastAt > 90 * 1000) await M.refresh(true);
        SKL.marketAmt = M.marketAmt;
      }
    } catch (e) { SKL.marketAmt = null; }          // 大盤抓不到不該讓整個即時模式失敗
    SKL.tv = tv; SKL.stv = stv; SKL.codes = codes.length; SKL.reqs = reqs;
    SKL.quoteAt = at; SKL.at = Date.now(); SKL.err = '';
    return tv;
  }

  // 狀態列（就在拉Bar 底下那一行）。誠實標示全部寫在這裡，不要散在圖上。
  function sklStamp() {
    const el = $('#sankeyLive');
    const btn = $('#sankeyLiveBtn');
    if (btn) { btn.classList.toggle('on', SKL.on); btn.setAttribute('aria-pressed', SKL.on ? 'true' : 'false'); }
    if (!el) return;
    if (!SKL.on) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    if (SKL.busy && !SKL.at) { el.innerHTML = '<b>即時</b>　抓取中…'; return; }
    if (SKL.err) { el.innerHTML = `<b class="bad">即時抓不到</b>　${fmt.esc(SKL.err)}　·　再按一次「即時」可退回盤後資料`; return; }
    const amt = SKL.marketAmt != null ? `台股總成交值 <b>${fmt.yi(SKL.marketAmt)}</b>（證交所真實值）` : '台股總成交值：這一輪沒取到';
    el.innerHTML = (SKL.intraday
      ? `<b class="live">即時</b>　報價 ${fmt.esc(SKL.quoteAt || '—')}　每分鐘更新`
      : '<b class="warn">現在不是盤中</b>（現貨 09:00–13:30）　下面畫的是<b>最近一次收盤後的報價快照</b>，不是盤中變化')
      + `　·　${amt}`
      + `　·　板塊成交值是 <b>價 × 量</b> 的<b>估算值</b>（端點沒有每檔的累積成交金額）`
      + `　·　% 的分母＝<b>${Object.keys(SKL.tv).length} 個即時板塊加總</b>，`
      + `「〇〇・其他」自動桶要 4 個請求/分鐘、做不到，一律標<b>盤後</b>且不進分母`
      + `　·　這一輪 ${SKL.reqs} 個請求 / ${SKL.codes} 檔`;
  }

  async function sklTick() {
    if (!SKL.on || SKL.busy) return;
    const st = sankeyState; if (!st) return;
    /* 換到站內別的分頁時容器還在 DOM、只是被藏起來（offsetParent 是 null）。
       這時候不要打報價 —— 使用者根本沒在看這張圖，每分鐘 2 個請求純浪費。
       回到資金流向頁時計時器還在，下一輪就自己接上。*/
    { const el = $('#sankey'); if (el && el.offsetParent === null) return; }
    SKL.busy = true; SKL.intraday = !window.Live || window.Live.isIntraday();
    sklStamp();
    try { await sklFetch(st.sd); }
    catch (e) { SKL.err = String((e && e.message) || e).slice(0, 80); SKL.tv = {}; SKL.stv = {}; }
    finally {
      SKL.busy = false;
      const s2 = sankeyState;
      if (SKL.on && s2) renderSankey(s2.sd, s2.k, sankeySel);
      sklStamp();
    }
  }

  /* 退出即時。`redraw=false` 給「使用者自己拖時間軸」用 ——
     那一路本來就會接著重畫一次，這裡再畫一次等於同一幀畫兩張圖。*/
  function sklOff(redraw) {
    if (SKL.timer) { clearInterval(SKL.timer); SKL.timer = null; }
    SKL.on = false; SKL.tv = {}; SKL.stv = {}; SKL.err = '';
    sklStamp();
    if (redraw !== false) { const st = sankeyState; if (st) renderSankey(st.sd, st.k, sankeySel); }
  }

  function sklToggle() {
    if (SKL.on) return sklOff();
    if (SKL.timer) { clearInterval(SKL.timer); SKL.timer = null; }
    SKL.on = true;
    stopAllPlay();                     // 即時和「往回播」是互斥的兩件事，同時跑只會互相蓋
    SKL.err = ''; SKL.at = 0; SKL.tv = {}; SKL.stv = {};
    SKL.intraday = !window.Live || window.Live.isIntraday();
    sklStamp();
    sklTick();
    SKL.timer = setInterval(() => { if (!document.hidden) sklTick(); }, SKL_MS);
  }

  // 拉Bar 建好之後才掛得上去（playBar 會把整個容器的 innerHTML 換掉）
  function sklMountBtn() {
    const box = $('#sankeyDays'); if (!box || $('#sankeyLiveBtn')) return;
    box.classList.add('rbar');         // 沒有拉Bar（只有一天資料）時容器還沒有這個類，鈕會沒有樣式
    const b = document.createElement('button');
    b.type = 'button'; b.id = 'sankeyLiveBtn'; b.className = 'pb livebtn';
    b.textContent = '即時';
    b.title = '切到盤中即時：板塊成交值改用即時報價估算（價 × 量），每分鐘更新';
    b.setAttribute('aria-pressed', 'false');
    b.onclick = sklToggle;
    box.appendChild(b);
    /* 換主題會把整頁重畫一次（applyTheme → route），playBar 連帶把這一排的 innerHTML
       換掉，所以這顆鈕是全新的一顆。即時模式如果還開著，要把「亮起來」的樣子補回去，
       不然畫的明明是即時資料、鈕看起來卻是關的。*/
    sklStamp();
  }

  function renderSankey(sd, idx, sel) {
    const el = $('#sankey'); if (!el) return;
    /* 空狀態要把 JS 量出來的高度也清掉 —— `.isempty` 收的是 CSS 的 min-height，
       收不掉寫在 style 上的 height，不清就會留一個 900px 的黑方塊。*/
    const bail = (msg) => { el.style.height = ''; el._skShape = ''; return empty('sankey', msg); };
    if (!sd || !sd.dates || !sd.dates.length) return bail('資金去向的逐日資料還沒產出（下一輪盤後管線就會有）');
    const D2 = sd.dates;
    const k = Math.max(0, Math.min(D2.length - 1, idx == null ? D2.length - 1 : idx));
    const day = D2[k];
    const roster = (sd.groups || []);
    if (!roster.length) return bail(`${day} 這天沒有資料`);
    sel = sel || null;
    sankeySel = sel;
    sankeyState = { sd, k };
    /* ★ 先決定「面板要放右邊還是放下面」，再量圖有多寬 —— 順序不能反。
       右側面板固定 300px ＋ 14px 間距，1280～1440 的筆電一開面板圖就掉到 700px 以下，
       接著被判成窄畫面、代表股那一層整個被收掉：**點族群想看成分股，反而看不到成分股**。
       所以量一下「如果面板放右邊，圖還剩幾 px」，撐不住四層就把面板改放到圖下面。
       判準是「圖剩幾 px」不是「螢幕幾 px」（中間隔著側欄與卡片內距），所以只能用 JS 量，
       媒體查詢算不出來。*/
    const row = $('#sankeyRow');
    if (row) {
      const rw = row.clientWidth || 0;
      row.classList.toggle('stack', rw > 0 && rw - 314 < SANKEY_NARROW);
    }
    const narrow = (el.clientWidth || 9999) < SANKEY_NARROW;
    const selG = sel && sel.gid, selC = sel && sel.chain;
    const gs = roster.map(g => ({ ...g, v: (g.tv || [])[k],
      prev: k > 0 ? (g.tv || [])[k - 1] : null }));       // 前一天：給「比昨天多還是少」用
    /* ★ 即時模式（Andy 2026-09-21「即時」鈕）：把手寫板塊的成交值換成即時估算值。
       自動桶（ind_*）抓不到，所以**留著收盤值、標成「盤後」、而且不進分母** ——
       上午十點拿「板塊的部分成交值」去和「自動桶的整天成交值」比，
       自動桶會被灌成第一名，那比不做還糟。*/
    const live = SKL.on && !SKL.err && Object.keys(SKL.tv).length ? SKL : null;
    if (live) gs.forEach(g => {
      const lv = live.tv[g.gid];
      if (lv != null) { g.v = lv; g.prev = null; g.live = true; }
      else { g.stale = true; g.prev = null; }             // 盤後：不比前一天（兩邊不是同一個時點）
    });
    const leaves = (sd.leaves || {})[day] || [];
    const prevLeaves = k > 0 ? ((sd.leaves || {})[D2[k - 1]] || []) : [];
    /* 分母。即時模式只加總「有即時值」的板塊 —— 這就是那條不准打折的規矩：
       佔比一定要用「板塊 ÷ 所有即時板塊加總」，不要拿估算的分子去除
       `Market3.marketAmt` 那個真實分母（會系統性偏掉）。*/
    const total = (live ? gs.filter(g => g.live) : gs).reduce((s2, g) => s2 + (g.v || 0), 0) || 1;
    /* 大小的基準。平常是「全期間最大值」（換日期時大小才有可比性）；
       即時模式改成「這一輪的最大值」—— 盤中累積的成交值本來就比整天小，
       跟 60 天最大值比的話開盤半小時整張圖只剩幾個小點，等於看不到東西。*/
    let maxV = 1;
    if (live) gs.forEach(g => { if (g.live && g.v > maxV) maxV = g.v; });
    else roster.forEach(g => (g.tv || []).forEach(v => { if (v != null && v > maxV) maxV = v; }));
    const lt = theme() === 'light';
    const HI = lt ? .62 : .95, LO = lt ? .22 : .30;          // 顏色深淺的上下限
    const DIM = 0.14;                                        // 沒量／沒被選中時壓到多暗
    const ratio = (v) => Math.min(1, Math.max(0, (v || 0) / maxV));
    const alpha = (v) => LO + (HI - LO) * ratio(v);
    const size = (v) => 8 + 22 * Math.sqrt(ratio(v));
    const width = (v) => 1 + 7 * ratio(v);
    /* 每一層的 % 都是「佔它上一層」的比重（分母寫在 #sankeySub 與「怎麼看」裡）。
       為什麼不全部用全市場當分母：代表股對全市場的佔比常常是 0.1%、0.2%，
       整欄看起來都一樣，等於沒寫；「台積電佔晶圓代工 49.8%」才回答得了
       「這個族群的錢是不是集中在一檔上」。*/
    const pct = (v, base) => fmt.n((v || 0) / (base || 1) * 100, 1);
    /* 比昨天多還是少（Andy「更豐富」）：紅漲綠跌，用 rich text 才能只給箭頭上色、
       族群名維持原本的顏色。沒有前一天（第一天）就不畫。*/
    const RICH = { up: { color: CH.up, fontSize: 11 }, dn: { color: CH.down, fontSize: 11 },
      fl: { color: CH.ink3, fontSize: 11 } };
    const dodTag = (v, prev) => {
      if (v == null || prev == null || prev <= 0) return '';
      const d = (v - prev) / prev * 100;
      if (!isFinite(d)) return '';
      const key = d > 1 ? 'up' : d < -1 ? 'dn' : 'fl';
      const arrow = d > 1 ? '▲' : d < -1 ? '▼' : '＝';
      return `{${key}| ${arrow}${fmt.n(Math.abs(d), 0)}%}`;
    };
    const dodText = (v, prev) => {
      if (v == null || prev == null || prev <= 0) return '';
      const d = (v - prev) / prev * 100;
      if (!isFinite(d)) return '';
      return `<br>比前一天 <span style="color:${upDown(d)}">${d > 0 ? '+' : ''}${fmt.n(d, 1)}%</span>`;
    };

    const byG = {};
    /* 即時模式下代表股那一欄也換成估算值（報價本來就是逐檔抓的，不多打一個請求）。
       自動桶底下的代表股抓不到，維持收盤值並標 stale。*/
    leaves.forEach(x => {
      const lv = live ? live.stv[String(x.code)] : null;
      const row = live ? { ...x, tv: lv == null ? x.tv : lv, stale: lv == null } : x;
      (byG[x.gid] = byG[x.gid] || []).push(row);
    });
    const prevByCode = {};
    prevLeaves.forEach(x => { prevByCode[x.gid + '|' + x.code] = x.tv; });

    /* ---- 第 1 層：產業鏈。
       **歷史回放**：順序用最後一天排一次，之後不隨日期改變（位置固定，2026-09-20 拍板）。
       **即時模式**：改用這一輪的即時值重排（Andy 2026-09-21「會自動交換位置」）。
       整條鏈都抓不到即時（例如「其他產業別」全是自動桶）的排到最後 ——
       它留著的是上一個收盤的整天成交值，混進來排就會永遠佔著第一名。*/
    const lastIdx = D2.length - 1;
    const chainOrder = [];
    const chainOf = {};
    const gOf = {};
    gs.forEach(g => { gOf[g.gid] = g; });
    roster.forEach(g => {
      const cid = g.chain || 'other';
      if (!chainOf[cid]) { chainOf[cid] = { cid, name: g.chain_name || chainLabel(cid), gids: [], last: 0, nowV: 0, anyLive: false }; chainOrder.push(chainOf[cid]); }
      chainOf[cid].gids.push(g.gid);
      chainOf[cid].last += (g.tv || [])[lastIdx] || 0;
      const cur = gOf[g.gid];
      if (cur && cur.live) { chainOf[cid].nowV += cur.v || 0; chainOf[cid].anyLive = true; }
    });
    chainOrder.sort(live
      ? (a, b) => (b.anyLive ? b.nowV : -1) - (a.anyLive ? a.nowV : -1)
      : (a, b) => b.last - a.last);

    const seen = new Set(['台股成交值']);
    const nameOfG = {};

    /* ★ 點族群 → 水流延伸出**全部**成分股（Andy 2026-09-21：「當我點擊族群 會延伸顯示
       其他股票…水流原本出現前三名，但因為我點擊了那個族群，他就會延伸前三名之後的全部顯示」）。
       掛在既有的 `DRILL.gid` 上（點節點、點晶片、點輪動時鐘都是同一份狀態），
       不另開一套「展開中」的旗標 —— 再點一次／點背景／ESC 都已經會 `drillClose()`，
       收回自然就跟著發生，不用寫第二套復原。

       ★★ 口徑：**分母用「這個族群成分股成交值的加總」，不是族群節點自己的值。**
       兩者在多數族群相等，但有股票同時掛兩個板塊時不相等 —— 後端的族群成交值是
       1/n 拆分過的（例如 HBM 少 12%）。展開之後全部成分股都在畫面上，
       拿族群值當分母的話百分比會加到 111%，一眼就看得出是錯的；
       而且右側 `#sankeyPanel` 面板用的就是「成分股加總」這個分母
       （`renderDrillPanel` 的 `sum`），兩邊對不起來就是 bug。
       所以這裡刻意和面板走同一份資料（`groups_detail`）、同一個分母。

       即時模式下值換成 `SKL.stv` 的估算（報價本來就逐檔抓，不多打一個請求），
       分母同步換成「有報價的成分股加總」，圖上仍然自洽；
       右側面板是盤後那一份，差異寫在 tooltip 與副標裡，不假裝一樣。*/
    const expandRows = (gid) => {
      const det = (D.groups_detail || {})[gid] || {};
      const rows = (det.members || []).map(m => {
        const code = String(m.code);
        const lv = live ? live.stv[code] : null;
        return { code, name: m.name || code, tv: live ? (+lv || 0) : (+m.turnover || 0) };
      }).filter(r => r.tv > 0).sort((a, b) => b.tv - a.tv);   // 當天沒量的不列
      return { rows, sum: rows.reduce((s2, r) => s2 + r.tv, 0) };
    };
    const expandBabies = (g, col, off, fade) => {
      const { rows, sum } = expandRows(g.gid);
      if (!rows.length || !(sum > 0)) return null;            // 一檔都算不出來就退回原本的三檔
      const head = rows.slice(0, SANKEY_EXPAND_MAX);
      /* 被使用者點開、要單獨畫一顆的那幾檔從「其餘」裡扣掉 ——
         不扣的話同一檔會同時出現在自己的節點和「其餘 N 檔」的加總裡。*/
      const rest = rows.slice(SANKEY_EXPAND_MAX).filter(r => !DRILL.stocks.has(r.code));
      /* 展開之後全部成分股本來就都在圖上了，所以「從右欄點個股」不再是「多長一顆」，
         而是**把已經在的那一顆標起來**（亮邊框＋虛線，和收合狀態下那顆自己長出來的一樣）。
         不標的話使用者點了清單，圖上完全沒有回應，會以為點壞了。*/
      const out = head.map(r => {
        const pk = DRILL.stocks.has(r.code);
        return {
          name: uniqName(seen, `${r.name} ${r.code}`), value: r.tv, code: r.code, gidOf: g.gid,
          shown: r.name, dim: off, share: r.tv / sum, base: sum, expanded: true, gsum: sum,
          picked: pk,
          symbolSize: Math.max(pk ? 7 : 6, size(r.tv) * .62),
          itemStyle: { color: hexA(col, alpha(r.tv) * (pk ? .95 : .85)),
            borderColor: pk ? hexA(CH.ink2, .9) : 'transparent', borderWidth: pk ? 1.4 : 0, opacity: fade },
          lineStyle: { color: hexA(col, alpha(r.tv) * .7), width: Math.max(1, width(r.tv) * .7),
            ...(pk ? { type: 'dashed' } : {}), opacity: fade },
          label: { formatter: `${r.name} ${pct(r.tv, sum)}%`, opacity: fade, rich: RICH },
        };
      });
      if (rest.length) {
        const rv = rest.reduce((s2, r) => s2 + r.tv, 0);
        /* 「其餘 N 檔」：量沒有被丟掉，只是收成一顆灰色虛線的點。
           不給 code＝點它不會跳頁（它不是一檔股票）；要看完整名單就看右邊那一欄。*/
        out.push({
          name: uniqName(seen, `其餘 ${g.gid}`), value: rv, gidOf: g.gid, restN: rest.length,
          shown: `其餘 ${rest.length} 檔`, dim: off, share: rv / sum, base: sum, expanded: true, gsum: sum,
          symbolSize: Math.max(6, size(rv) * .62),
          itemStyle: { color: hexA(CH.ink3, .55), borderColor: 'transparent', opacity: fade },
          lineStyle: { color: hexA(CH.ink3, .45), width: Math.max(1, width(rv) * .6), type: 'dashed', opacity: fade },
          label: { formatter: `其餘 ${rest.length} 檔 ${pct(rv, sum)}%`, opacity: fade, rich: RICH },
        });
      }
      return out;
    };
    const chainNodes = chainOrder.map(ch => {
      const mine = gs.filter(g => (g.chain || 'other') === ch.cid);
      /* 族群層的排序和上面產業鏈層同一條規矩：歷史回放沿用 `sd.groups` 的原始順序
         （後端依最新一天排過一次，位置固定）；即時模式依這一輪的即時值重排，
         抓不到即時的自動桶排到最後。*/
      if (live) mine.sort((a, b) => (b.live ? b.v || 0 : -1) - (a.live ? a.v || 0 : -1));
      // 即時模式：鏈的值只加總有即時值的板塊，和上面的 total 同一個分母口徑
      const cv = (live ? mine.filter(g => g.live) : mine).reduce((s2, g) => s2 + (g.v || 0), 0);
      const cprev = mine.reduce((s2, g) => s2 + (g.prev || 0), 0);
      const cAllStale = !!live && !mine.some(g => g.live);      // 整條鏈都是自動桶（例如「其他產業別」）
      const cOff = (selC && selC !== ch.cid) || (selG && !ch.gids.includes(selG));
      const cFade = cOff ? DIM : 1;
      const ccol = L.gcolor[ch.gids[0]] || CH.cyan;
      const kids = mine.map(g => {
        const col = L.gcolor[g.gid] || CH.cyan;
        const has = g.v != null && g.v > 0;
        const off = cOff || (selG && selG !== g.gid);
        const fade = off ? DIM : 1;
        const gv = g.v || 0;
        /* 展開中的那一個族群（`DRILL.gid`）：葉子從固定 3 檔換成全部成分股。
           窄畫面（< SANKEY_NARROW）本來就沒有代表股這一層，所以不展開 ——
           那時候完整名單在圖下方的面板裡，字還讀得到。*/
        /* ★ 2026-09-21 Andy 對「ETF 那桶 356 檔、上限 20 ＋『其餘 336 檔』」的答覆是「不用」。
           所以展開**只給人工族群**，`ind_*` 自動桶（半導體業・其他、ETF…）不展開 ——
           它們是「不屬於任何人工族群的股票」的收容桶，不是一個有意義的族群，
           把 356 檔 ETF 攤在圖上也讀不出任何東西。點它一樣會開右邊的面板，
           要看完整名單就在那裡看。
           自動桶排除之後，真正的族群最大是 bank 16 檔、其餘 ≤ 11 檔，
           所以 20 檔上限與「其餘 N 檔」那顆節點都不會再被觸發 ——
           程式留著當防線（YAML 是人工維護的，哪天有人加到 21 檔也不會爆版面），
           但正常情況下畫的一律是完整名單。*/
        const canExpand = DRILL.gid === g.gid && !String(g.gid || '').startsWith('ind_');
        const expanded = !narrow && canExpand ? expandBabies(g, col, off, fade) : null;
        const babies = expanded || (narrow ? [] : (byG[g.gid] || []).slice().sort((a2, b2) => b2.tv - a2.tv)
          .slice(0, SANKEY_KIDS).map(x => {
            /* 前端這一層也擋一次「nan」。根因在後端（見 pipeline/compute/rrg.py 的註解）已經修掉，
               但使用者的瀏覽器可能還快取著舊的 sankey_daily.json，那一份裡每一檔都叫「nan」。*/
            const nm = leafName(x);
            const p = prevByCode[x.gid + '|' + x.code];
            return {
              name: uniqName(seen, `${nm} ${x.code}`), value: x.tv, code: x.code, gidOf: g.gid,
              shown: nm, dim: off, share: gv > 0 ? x.tv / gv : null, prev: p == null ? null : p,
              stale: !!x.stale,
              symbolSize: x.stale ? 5 : Math.max(6, size(x.tv) * .62),
              itemStyle: { color: hexA(col, x.stale ? DIM : alpha(x.tv) * .85), borderColor: 'transparent', opacity: fade },
              lineStyle: { color: hexA(col, (x.stale ? DIM : alpha(x.tv) * .7)), width: x.stale ? 0.8 : Math.max(1, width(x.tv) * .7), opacity: fade },
              /* ★ 代表股那一欄也要標占比（Andy 2026-09-20 第 3 件）。
                 分母是**所屬族群**，畫面上寫清楚（#sankeySub 與「怎麼看」都寫了）。*/
              label: { formatter: x.stale ? `${nm} 盤後` : gv > 0 ? `${nm} ${pct(x.tv, gv)}%` : nm,
                opacity: fade, rich: RICH },
            };
          }));
        /* 階段三（Andy 2026-09-21「也可以點擊，並顯示在圖上」）：
           使用者在成分股清單裡點開的個股，要掛在**它所屬的族群**底下多長出一個葉節點。
           流量用成交值、% 的分母是所屬族群（沿用 D4 已經拍板的口徑）。
           ★ 值的來源有兩種，因為逐日檔（sankey_daily）每天每族群只存前 3 大：
             · 那一天剛好在前 3 大 → 用當天的值（和固定那三顆同一個基準）
             · 不在 → 退回 groups_detail 的**最新交易日**成交值，並在小框裡標「最新」，
               不要讓使用者以為那是他正在看的那一天的數字。
           ★ 邊框用 ink2、線用虛線：一眼看得出「這顆是我自己點開的」，
             和固定的三顆代表股分得出來。*/
        if (!narrow && DRILL.gid === g.gid && DRILL.stocks.size) {
          const have = new Set(babies.filter(b => b.code).map(b => String(b.code)));
          const det = (D.groups_detail || {})[g.gid] || {};
          DRILL.stocks.forEach(code => {
            code = String(code);
            if (have.has(code)) return;
            const m = (det.members || []).find(z => String(z.code) === code);
            const dayRow = (byG[g.gid] || []).find(z => String(z.code) === code);
            const tv = dayRow ? +dayRow.tv : (m ? +m.turnover : 0);
            if (!(tv > 0)) return;
            const nm = (dayRow && leafName(dayRow)) || (m && m.name) || code;
            babies.push({
              name: uniqName(seen, `${nm} ${code}`), value: tv, code, gidOf: g.gid,
              shown: nm, dim: off, share: gv > 0 ? tv / gv : null, picked: true,
              est: !dayRow, prev: null,
              symbolSize: Math.max(7, size(tv) * .62),
              itemStyle: { color: hexA(col, alpha(tv) * .9), borderColor: hexA(CH.ink2, .9),
                borderWidth: 1.4, opacity: fade },
              lineStyle: { color: hexA(col, alpha(tv) * .75), width: Math.max(1.2, width(tv) * .7),
                type: 'dashed', opacity: fade },
              label: { formatter: gv > 0 ? `${nm} ${pct(tv, gv)}%` : nm, opacity: fade, rich: RICH },
            });
          });
        }
        // 補到固定格數：看不見的佔位節點，只為了讓縱向空間每天都一樣
        for (let i = babies.length; !narrow && i < SANKEY_KIDS; i++) {
          babies.push({ name: uniqName(seen, ` ${g.gid}#${i}`), value: null, placeholder: true,
            symbolSize: 0, itemStyle: { opacity: 0 }, lineStyle: { opacity: 0 }, label: { show: false } });
        }
        const gname = uniqName(seen, g.name);
        nameOfG[g.gid] = gname;
        /* ★ 即時模式：抓不到的自動桶一律標「盤後」而且不給 % ——
           它的值是上一個收盤的整天成交值，和旁邊的盤中估算值不是同一個時點，
           放一個百分比在旁邊就是在騙人（不准假裝整張圖都是即時的）。*/
        /* ★ 即時模式下自動桶要畫成「不參與比較」的樣子（小點＋細線＋壓暗）。
           它留著的是**上一個收盤的整天成交值**，比盤中半天的估算值大得多 ——
           照原本的規則畫，ETF 會變成整張圖最粗的那一條、旁邊還寫著「盤後」，
           那是最糟的一種誤導：標示是對的，但圖在說另一件事。*/
        const shrink = !!g.stale;
        const drawn = has && !shrink;
        return { name: gname, value: gv, gid: g.gid, chainOf: ch.cid, children: babies,
          nodata: !has, dim: off, prev: g.prev, base: cv, stale: !!g.stale, isLive: !!g.live,
          expanded: !!expanded, esum: expanded ? expanded[0].gsum : null,
          symbolSize: drawn ? size(g.v) : 6,
          itemStyle: { color: hexA(col, drawn ? alpha(g.v) : DIM), borderColor: 'transparent', opacity: fade },
          lineStyle: { color: hexA(col, (drawn ? alpha(g.v) : DIM) * .8), width: drawn ? width(g.v) : 0.8, opacity: fade },
          /* 窄畫面把名稱與百分比拆成兩行、並且不畫 ▲▼：
           324px 的手機一欄只有 60~70px，寫成一行的話「電腦及週邊設備業 6.6% ▲32%」
           會直接被畫布右緣裁掉，連百分比都看不到（截圖量到的）。
           兩行＋截斷之後至少「是誰、佔多少」一定讀得到，▲▼ 點一下看小框還是有。*/
        label: { formatter: g.stale ? `${g.name}${narrow ? '\n' : ' '}盤後`
          : has ? (narrow ? `${g.name}\n${pct(gv, cv)}%`
            // ▾ ＝ 這個族群現在是展開的（再點一次收回）。標在名字前面，不用讀說明也知道。
            : `${expanded ? '▾ ' : ''}${g.name} ${pct(gv, cv)}%${dodTag(gv, g.prev)}`) : `${g.name} 無資料`,
          ...(narrow ? { width: 116, overflow: 'truncate', lineHeight: 13, fontSize: 10.5 } : {}),
          opacity: off ? 0.35 : (drawn ? 1 : 0.55), rich: RICH } };
      });
      const cname = uniqName(seen, ch.name);
      ch.node = cname;
      return { name: cname, value: cv, chain: ch.cid, children: kids, prev: cprev, base: total,
        stale: cAllStale,
        symbolSize: Math.max(10, size(cv / 2)),
        itemStyle: { color: hexA(ccol, cOff ? DIM : Math.min(1, alpha(cv / 2) + .1)), borderColor: 'transparent', opacity: cFade },
        lineStyle: { color: hexA(ccol, (cOff ? DIM : alpha(cv / 2)) * .85), width: Math.max(1.4, width(cv / 2)), opacity: cFade },
        label: { formatter: cAllStale ? `${ch.name}${narrow ? '\n' : ' '}盤後`
          : narrow ? `${ch.name}\n${pct(cv, total)}%`
            : `${ch.name} ${pct(cv, total)}%${dodTag(cv, cprev)}`,
          ...(narrow ? { width: 108, overflow: 'truncate', lineHeight: 13, fontSize: 11 } : {}),
          fontSize: 12.5, fontWeight: 700, opacity: cOff ? 0.4 : 1, rich: RICH } };
    });
    /* 根節點。★ 即時模式下這一格是唯一一個「真實值」—— `Market3.marketAmt` 是
       台股當日累積成交值（元），盤中就有。第二行才是這張圖底下 % 的分母
       （即時板塊的估算加總），兩個數字一定要分開寫，不然會被讀成同一件事。*/
    const rootLbl = live
      ? `台股成交值 ${SKL.marketAmt != null ? fmt.yi(SKL.marketAmt) : '—'}（真實）`
        + `\n即時板塊合計 ${fmt.yi(total)}（估算 · % 的分母）`
      : `台股成交值 ${fmt.yi(total)}`;
    const root = { name: '台股成交值', value: total, symbolSize: 26, marketAmt: live ? SKL.marketAmt : null,
      itemStyle: { color: hexA(CH.cyan, lt ? .55 : .9), borderColor: 'transparent' },
      /* ★ 窄畫面把根節點的標籤改放**正下方**。
         放右邊的話「台股成交值 8271 億」這一串在 390px 上會橫跨到第二欄，
         整片蓋住產業鏈那幾顆點 —— 實測：在 AI 伺服器那顆點上按下去，
         ECharts 判定你點的是**根節點的標籤**（`p.name` 回「台股成交值」），
         所以「點產業鏈」在手機上完全點不動，而且畫面沒有任何異狀可以看出原因。*/
      label: { formatter: rootLbl, fontWeight: 700, lineHeight: 15, rich: RICH,
        ...(narrow ? { position: 'bottom', distance: 8, align: 'left', fontSize: 11 } : {}) },
      children: chainNodes };

    // 哪一個族群現在是展開的（給副標寫「已展開 N 檔」用；沒有就是 null）
    const expNode = chainNodes.reduce((f, c) => f || (c.children || []).find(g => g.expanded), null);
    const sub = $('#sankeySub');
    if (sub) {
      const selName = selG ? (L.gname[selG] || selG) : selC ? (chainOf[selC] || {}).name : '';
      const when = live
        ? (SKL.intraday ? `盤中即時（報價 ${SKL.quoteAt || '—'}）` : '即時報價快照（現在不是盤中）')
        : day;
      sub.textContent = (narrow
        ? `${when}：台股 → 產業鏈 → 族群（畫面太窄，代表股那一層先收起來 ——`
          + `點族群，下面就是它的成交值排序）`
        : `${when}：台股 → 產業鏈 → 族群 → 代表股`)
        + `　·　每一層的 % 都是「佔它上一層」的比重`
        /* ★ 這一句一定要跟著模式換（Andy 2026-09-21）——
           即時模式真的會換位，副標卻寫著「位置固定」就是「圖在動、字說不會動」。*/
        + (live ? '　·　依當下成交值即時排名，名次變了就會換位（有補間動畫）'
          + '　·　板塊成交值是「價 × 量」的估算值，自動桶標「盤後」且不進分母'
          : '　·　位置固定（往回拖／播放都不洗牌），只有線的粗細與圓圈大小會變')
        + (selName ? `　·　只看「${selName}」` : '')
        + (expNode
          ? `　·　已展開「${expNode.gid ? (L.gname[expNode.gid] || expNode.gid) : ''}」的 `
            + `${expNode.children.length} 格成分股（再點一次族群、點背景或按 ESC 收回）`
          : (narrow ? '' : '　·　點族群的圓圈＝把它的代表股展開成全部成分股'));
    }

    /* 葉子數決定這張圖要多高：ECharts 的 tree 是把縱向空間平均分給葉子的，
       高度不夠就會變成一排擠在一起的 11px 字。所以量完葉子數自己算高度，
       不寫死在 CSS（族群數之後會變，寫死等於埋一個以後才會爆的雷）。*/
    const gRows = chainNodes.reduce((s2, c) => s2 + c.children.length, 0);
    /* ★ 2026-09-21：改成數**真正的葉子數**，不再用「族群數 × SANKEY_KIDS」估。
       以前每個族群一定是 3 片葉子，兩者相等；現在展開的族群可以有到 21 片
       （20 檔 ＋「其餘 N 檔」），估算值會少算一大截，標籤就會擠在一起。
       順手也修掉一個一直都在的小問題：使用者從右欄點開的個股本來就會多長葉子，
       高度卻沒跟著加，多開幾檔就開始擠。
       一片葉子 16px 是現況量出來的（54 片 → 928px，沒有重疊）；
       展開之後最多 17 × 3 ＋ 21 ＝ 72 片 → 1216px，所以上限從 1040 放到 1400。*/
    const leafRows = chainNodes.reduce((s2, c) =>
      s2 + c.children.reduce((t, g) => t + (g.children || []).length, 0), 0);
    el.style.height = (narrow ? Math.max(420, gRows * 36 + 48)
      : Math.max(560, Math.min(expNode ? 1400 : 1040, leafRows * 16 + 64))) + 'px';
    /* ★ 高度變了就**先自己 resize 一次**，再去 setOption。
       原因：ECharts 記的是上一次量到的寬高，不會自己去讀 DOM。
       不先 resize 的話它會用「舊高度」算好版面、開始補間，
       然後 ResizeObserver 在下一幀補一次 resize —— resize 是立刻重排、不補間，
       動畫就在第一幀被切斷（實測 y 從 885 直接跳到 1007）。
       先 resize 等於把「容器長高」這件事一次做完，接著的 setOption 才是純粹的位置補間。
       `_roSize` 要同步蓋掉，免得 ResizeObserver 等一下又來一次（見 chart() 裡那道閘門）。*/
    try {
      const prev = window.echarts && echarts.getInstanceByDom(el);
      if (prev && el.clientHeight > 0) {
        const sig = el.clientWidth + 'x' + el.clientHeight;
        if (el._roSize !== sig) { el._roSize = sig; prev.resize(); }
      }
    } catch (e) { /* 拿不到實例就算了，最多就是少一段動畫 */ }

    const c = chart('sankey', {
      tooltip: { ...tip, trigger: 'item', triggerOn: 'mousemove',
        formatter: (p) => {
          const d = p.data || {};
          if (d.placeholder) return '';
          if (d.nodata) return `<b>${p.name}</b><br>${day} 這天沒有量`;
          const v = d.value;
          if (v == null) return p.name;
          // 即時模式下自動桶（以及整條都是自動桶的鏈）拿的是收盤值，要講清楚，不要給假的佔比
          if (live && d.stale) {
            return `<b>${fmt.esc(p.name)}</b><br><b>盤後</b>：這一格抓不到即時`
              + `<br>「〇〇・其他」自動桶光 ETF 一格就 358 檔，每分鐘要多 4 個請求`
              + `<br>下面是 ${fmt.esc(day)} <b>收盤</b>的成交值 ${fmt.yi(v)}`
              + `<br><span class="muted">它不進即時佔比的分母（時點不同，比了會騙人）</span>`;
          }
          // 每一層都把「金額 ＋ 佔上一層 ＋ 佔全場 ＋ 比前一天」講滿（Andy「需要更豐富」）
          const own = d.code ? (d.shown + ' ' + d.code) : (d.shown || p.name);
          const base = d.base != null ? d.base : (d.share != null ? v / d.share : null);
          return `<b>${fmt.esc(own)}</b><br>成交值 ${fmt.yi(v)}`
            + (base ? `<br>佔上一層 <b>${pct(v, base)}%</b>` : '')
            + `<br>佔全場 ${pct(v, total)}%`
            + dodText(v, d.prev)
            /* 展開狀態下的葉子：分母是「成分股加總」不是族群節點的值，講清楚 ——
               有股票同時掛兩個板塊時族群值是 1/n 拆過的，兩個數字對不起來很正常，
               但沒寫出來的話看起來就像算錯。*/
            + (d.gsum != null ? '<br><span class="muted">分母＝這個族群成分股成交值加總，和右邊清單同一份</span>' : '')
            + (d.restN ? `<br><span class="muted">第 ${SANKEY_EXPAND_MAX + 1} 名之後的 ${d.restN} 檔收成這一顆`
              + '（量沒有丟掉，是加總）。完整名單在右邊那一欄</span>' : '')
            + (d.expanded && d.esum != null && Math.abs(d.esum - v) / (v || 1) > 0.01
              ? `<br><span class="muted">成分股加總 ${fmt.yi(d.esum)}：比這一格大，`
                + '因為有股票同時掛在別的板塊，族群成交值是 1/n 拆分過的</span>' : '')
            + (d.est ? '<br><span class="muted">（逐日明細每天只存前 3 大，這一檔用的是最新交易日的成交值）</span>' : '')
            + (live ? '<br><span class="muted">即時模式：成交值是「最後成交價 × 累積成交張數 × 1000」的<b>估算值</b>'
              + '（端點沒有每檔的累積成交金額）；雙掛兩個板塊的股票已照 1/n 拆分</span>'
              + (d.marketAmt != null ? `<br>台股總成交值 <b>${fmt.yi(d.marketAmt)}</b>（證交所真實值，不是估算）` : '') : '')
            + (d.picked ? '<br><small>你自己點開的個股 · 要拿掉就再點一次右邊清單裡那一列</small>' : '')
            + (d.code ? '<br><small>點一下進個股頁</small>'
              : d.restN ? ''
                : d.gid ? (d.expanded
                  ? '<br><small>再點一次＝把水流收回成 3 檔代表股</small>'
                  : '<br><small>點一下：水流延伸成全部成分股，右邊同時列出成交值排序</small>')
                  : d.chain ? '<br><small>點一下只看這條產業鏈</small>' : '');
        } },
      series: [{
        type: 'tree', orient: 'LR', layout: 'orthogonal', edgeShape: 'curve',
        left: 10, right: narrow ? 124 : 132, top: 14, bottom: 18,
        initialTreeDepth: 3, expandAndCollapse: false, roam: false,
        symbol: 'circle',
        label: { position: 'right', distance: 7, color: CH.ink2, fontSize: 11.5,
          textBorderColor: CH.panel, textBorderWidth: 3, align: 'left', rich: RICH },
        leaves: { label: { position: 'right', distance: 6, fontSize: 11, color: CH.ink3, rich: RICH } },
        /* hover 一條就把**整條路徑**亮起來、其餘壓暗（Andy 2026-09-20「更豐富」）。
           用 'relative' 不用 'ancestor'：滑到代表股時兩者一樣（葉子沒有子孫），
           但滑到族群時 'relative' 會連它的代表股一起亮 —— 那正是「這個族群的錢去了哪幾檔」。*/
        emphasis: { focus: 'relative', blurScope: 'series' },
        blur: { itemStyle: { opacity: 0.18 }, lineStyle: { opacity: 0.12 }, label: { opacity: 0.25 } },
        /* ★ 2026-09-21：換位與展開都要**補間**，不能瞬間跳（Andy「會自動交換位置」）。
           跳一下人眼追不到誰跟誰換了，那就退化成「圖每分鐘閃一次」。
           `animationDurationUpdate` 只有在 series 身分被保留（setOption 合併）時才有用，
           所以下面的 notMerge 不是常數了。*/
        animationDurationUpdate: 520,
        animationEasingUpdate: 'cubicInOut',
        data: [root],
      }],
      /* ★ 只有版面**型態**真的變了才整張重建（notMerge: true），其餘一律合併。
         型態＝窄畫面翻面（層數從四層變三層）。那一刻本來就沒有「誰換到哪裡」
         這回事，補間反而會看到一堆節點從畫面外飛進來。
         其他情況（換日期、即時重排、展開／收回、聚焦）節點集合大致相同，
         合併才補得了間 —— ECharts 對 tree 是用節點名稱對位的，
         而這張圖的名稱唯一（`uniqName`），所以對得上。
         ⚠ `series[].data` 在合併時是**整個換掉**（ECharts 不會深層合併 data），
           所以「收回」時多出來的葉子會真的消失，不會殘留。*/
    }, { notMerge: el._skShape !== (narrow ? 'n' : 'w') });
    el._skShape = narrow ? 'n' : 'w';
    if (c) c.off('click').on('click', p => {
      const d = p.data || {};
      if (d.placeholder) return;
      // 「其餘 N 檔」不是一檔股票，點它不該跳到任何地方（完整名單在右邊那一欄）
      if (d.restN) return;
      if (d.code) return goStock(d.code);
      /* ★ 點族群**不跳頁**：在右邊原地展開成分股的成交值排序（Andy 2026-09-20 第 4 件）。
         要去族群頁的話，面板標題右邊與下方晶片列的 → 都還在。*/
      if (d.gid) {
        // 再點同一個就取消（和下面晶片列、和產業鏈節點同一套語彙）
        if (selG === d.gid) { chipSel.sankey = null; return drillClose(); }
        chipSel.sankey = d.gid;
        // ★ 2026-09-21：和輪動時鐘共用同一份下鑽狀態與同一支清單
        drillOpen(d.gid, L.gname[d.gid] || d.gid, sankeyNote(day, k === lastIdx), 'sankeyPanel');
        return renderSankey(sd, k, { gid: d.gid });
      }
      /* ★ 2026-09-21（Andy：「當點擊 AI 伺服器第一個 Node 右邊應當顯示 AI 伺服器，
         並下面多出裡面還蓋族群，並且都具備下拉選單可以看個股」）。
         以前點產業鏈只會把其餘壓暗，右邊什麼都不會出現 —— 圖上最粗的那幾顆點是死的。*/
      if (d.chain) {
        if (selC === d.chain) { return drillClose(); }        // 再點同一條＝取消（和族群同一套語彙）
        const node = chainNodes.find(z => z.chain === d.chain) || {};
        const cv2 = node.value || 0;
        const rows = (node.children || []).map(g => ({
          gid: g.gid, name: L.gname[g.gid] || g.gid, v: g.value || 0,
          share: cv2 > 0 ? (g.value || 0) / cv2 : 0, chg: gchgOf(g.gid),
        })).sort((a, b) => b.v - a.v);
        drillOpenChain(d.chain, (chainOf[d.chain] || {}).name || d.chain, rows,
          `${sankeyNote(day, k === lastIdx)}　·　族群的 % 是佔「${(chainOf[d.chain] || {}).name || d.chain}」這條鏈`,
          'sankeyPanel');
        return renderSankey(sd, k, { chain: d.chain });
      }
      // 根節點（台股成交值）＝回到最上層，和點背景／ESC 同一個結果
      if (p.name === '台股成交值' || p.dataIndex === 0) return drillClose();
    });
    /* ★ 點背景就回復預設（Andy 2026-09-21：「當點擊背景時會恢復 Default 狀態」）。
       ECharts 的 series click 只在點到圖元時才發，所以「點到空白」要跟 zrender 要 ——
       `ev.target` 是 null 就代表這一下沒有打到任何圖元。
       疊在上面那層小圓點 canvas 是 `pointer-events:none`，不會把事件吃掉。
       復原走的是既有的 drillClose()，和 ESC、麵包屑完全同一支（不要寫第二套復原）。*/
    if (c) {
      try {
        const zr = c.getZr();
        /* ★ 絕對不可以寫 `zr.off('click')`。ECharts 自己**也是**在 zrender 上掛 click
           來把原生事件翻譯成 series 的 click —— 整個關掉的話圖上所有節點都點不動了
           （2026-09-21 我就是這樣寫，實測「點 AI 伺服器沒反應」，
           zr 收得到事件、series 的 click 一次都沒進來）。
           所以只解除**上一次自己掛的那一支**，用具名 handler 存在元素上。*/
        if (el._skBlank) zr.off('click', el._skBlank);
        el._skBlank = (ev) => { if (!ev || !ev.target) { if (drillActive()) drillClose(); } };
        zr.on('click', el._skBlank);
      } catch (e) { /* zrender 換版本時最多就是沒有這個功能，不能讓整張圖掛掉 */ }
    }
    /* 族群晶片改成篩選（Andy 2026-09-20：「所有圖表的族群小Tip都需要具備點擊後
       就會在對應圖表上被篩選出去」）。名單也用固定名單，不是只有當天有量的那幾個。
       ★ 2026-09-23：那一整片晶片（排滿兩整行）換成**兩層下拉**（Andy 的「圖二」）。
         行為完全沒變 —— 仍然是單選、仍然是 `chipSel.sankey`、仍然只篩這張圖。*/
    filterDropdown('sankey', gs.map(g => ({ gid: g.gid, name: g.name })), selG,
      (nx) => {
        if (!nx) return drillClose();
        drillOpen(nx, L.gname[nx] || nx, sankeyNote(day, k === lastIdx), 'sankeyPanel');
        renderSankey(sd, k, { gid: nx });
      });
    // 面板開著的話跟著換日期重畫（標題裡的日期與「是不是最新」要跟著走）
    { const box = $('#sankeyPanel');
      // keepChain＝true：換日期不可以把「我是從哪條鏈點進來的」洗掉（麵包屑會突然少一階）
      if (box && !box.hidden && selG) drillOpen(selG, L.gname[selG] || selG, sankeyNote(day, k === lastIdx), 'sankeyPanel', true);
      else if (box && !box.hidden && DRILL.chain && selC === DRILL.chain) {
        // 鏈模式：換日期要把佔比與成交值一起換掉，否則清單會停在剛點下去的那一天
        const node = chainNodes.find(z => z.chain === DRILL.chain);
        if (node) {
          const cv2 = node.value || 0;
          DRILL.chainRows = (node.children || []).map(g => ({
            gid: g.gid, name: L.gname[g.gid] || g.gid, v: g.value || 0,
            share: cv2 > 0 ? (g.value || 0) / cv2 : 0, chg: gchgOf(g.gid),
          })).sort((a, b) => b.v - a.v);
          DRILL.notes.sankeyPanel = `${sankeyNote(day, k === lastIdx)}　·　族群的 % 是佔「${DRILL.chainName}」這條鏈`;
          renderDrillPanel('sankeyPanel');
        }
      } }

    /* 小圓點傳輸：等 tree 的版面算完（finished）才讀得到節點座標。
       ★ 2026-09-20 第 2 件（Andy：「並都需要具備資金流傳輸效果」）——
         以前只有第一段（大盤 → 族群）有點，現在**三段都要有**：
         大盤 → 產業鏈 → 族群 → 代表股。*/
    if (c) {
      c.off('finished');
      let armed = true;
      c.on('finished', () => {
        if (!armed) return;              // finished 會重複觸發，只接第一次
        armed = false;
        const pos = sankeyNodePos(c); if (!pos) return;
        const a = pos['台股成交值']; if (!a) return;
        const flows = [];
        const push = (from, to, v, gid, col, scale, lvl) => {
          if (!from || !to || !(v > 0)) return;
          const r = ratio(v * (scale || 1));
          flows.push({ a: from, b: to, gid, lvl, r,
            /* 資金越多 → 點越多、點越大、跑得越快。三個通道一起動，
               「哪條線的錢比較多」才一眼看得出來（Andy 2026-09-21）。*/
            n: dotN(r),
            size: dotR(r),
            spd: dotSpd(r),
            // 錯開相位，不要整排同時發車。用名稱的字元和當雜湊
            phase: ([...String(gid)].reduce((h, ch2) => (h * 31 + ch2.charCodeAt(0)) % 997, 7) % 100) / 100,
            color: hexA(col, lt ? .75 : .95) });
        };
        chainNodes.forEach(cn => {
          const cOff = (selC && selC !== cn.chain) || (selG && !cn.children.some(g => g.gid === selG));
          if (cOff || cn.stale) return;
          const cp = pos[cn.name];
          push(a, cp, cn.value, cn.chain, L.gcolor[(cn.children[0] || {}).gid] || CH.cyan, 0.5, 1);
          cn.children.forEach(g => {
            if (selG && selG !== g.gid) return;
            if (g.stale) return;            // 即時模式的自動桶：不是即時流量，不發點
            const gp = pos[g.name];
            const col = L.gcolor[g.gid] || CH.cyan;
            push(cp, gp, g.value, g.gid, col, 1, 2);
            g.children.forEach(x => {
              if (x.placeholder) return;
              push(gp, pos[x.name], x.value, g.gid + (x.code || 'rest'), col, 1, 3);
            });
          });
        });
        /* 配點：**先保證每一條線都至少有一顆**，剩下的預算才照金額多寡加密。
           以前是「照 size 由大到小塞滿預算」—— 四層之後最末段（族群 → 代表股）
           的線又細又多、排在最後面，預算一用完那一整段就一顆點都沒有，
           而那正是 Andy 這次點名要的「都需要具備資金流傳輸效果」。*/
        const use = flows.slice(0, SANKEY_DOT_MAX).map(f => ({ ...f, n: 1 }));
        let budget = SANKEY_DOT_MAX - use.length;
        flows.slice(0, use.length).map((f, i) => [f.n - 1, i])
          .sort((x, y) => y[0] - x[0])
          .forEach(([extra, i]) => { const add = Math.max(0, Math.min(extra, budget));
            use[i].n += add; budget -= add; });
        sankeyFlows = use;               // 給驗收量「最粗 vs 最細的線各有幾顆點」
        /* ★ 不要每換一天就把整層 canvas 拆掉重建：族群位置是固定的，
           拆掉重建只會讓小圓點閃一下。有活著的就只換 flows。*/
        if (sankeyFx && sankeyFx.alive() && sankeyFx.host === el) sankeyFx.setFlows(use);
        else { stopSankeyFlow(); sankeyFx = startSankeyFlow(el, use); }
      });
    }
    /* 寬度跨過 SANKEY_NARROW 就要換層數，所以得自己盯著容器 ——
       `chart()` 掛的那個 ResizeObserver 只會叫 ECharts resize()，
       它不知道「層數要變」這回事（和輪動時鐘的標籤重排是同一類問題）。
       只有**判定翻面**時才重畫，所以拖視窗不會一直重算。*/
    /* ★ 2026-09-21：除了「層數要不要變」，也要盯「面板該放右邊還是放下面」。
       可用寬度不只跟著視窗走 —— 開／關「今日事件」那個抽屜就會讓整列寬度差 360px
       （1440 上量到 1358 vs 998）。只盯層數的話，關掉抽屜之後面板會一直留在圖下面。
       `.stack` 的判準只吃 `#sankeyRow` 的寬度（不吃 `.stack` 自己），所以不會來回跳。*/
    const stackWanted = () => { const r2 = $('#sankeyRow');
      return !!(r2 && r2.clientWidth > 0 && r2.clientWidth - 314 < SANKEY_NARROW); };
    if (!el.dataset.skRo && window.ResizeObserver) {
      el.dataset.skRo = '1';
      let t = null, was = narrow, wasStack = stackWanted();
      new ResizeObserver(() => {
        const nw = (el.clientWidth || 9999) < SANKEY_NARROW;
        const sk = stackWanted();
        if (nw === was && sk === wasStack) return;
        was = nw; wasStack = sk;
        clearTimeout(t);
        t = setTimeout(() => { const st = sankeyState;
          if (st && el.isConnected) renderSankey(st.sd, st.k, sankeySel); }, 160);
      }).observe(el);
    }
  }

  // ---- 族群 × 法人：跟著上方期間走（期間資料裡已經有這段的法人合計）
  /* pick＝只看某一個族群（下方族群晶片點下去會傳進來，Andy 2026-09-20）。
     做法是**把其餘的長條壓暗**而不是整組抽掉 —— 抽掉之後 y 軸只剩一列，
     使用者會失去「它在這些族群裡排第幾」這個對照，那正是這張圖的重點。*/
  let instPick = null;
  function renderInstPeriod(p, pick) {
    if (pick !== undefined) instPick = pick;
    pick = instPick;
    const gs = (p.groups || []).filter(g => g.foreign != null || g.trust != null || g.dealer != null)
      .map(g => ({ ...g, total: (g.foreign || 0) + (g.trust || 0) + (g.dealer || 0) }));
    /* 法人比價量晚落地（價量 15:30、法人 18:30），所以每個交易日下午「本週」這一段
       會出現「價量有、法人還沒有」。以前只寫「這個期間沒有法人資料」，看起來像壞掉 ——
       講清楚是還沒出，並告訴他上一段看得到。 */
    if (!gs.length) {
      const late = (D.meta || {}).inst_date && (D.meta || {}).data_date
        && D.meta.inst_date < D.meta.data_date;
      return empty('instGroups', late || (p.days || 0) <= 1
        ? `${p.label || '這個期間'}的法人資料還沒出（價量 15:30 就有、三大法人要等 18:30 那輪），先看「上週」那一段`
        : '這個期間沒有法人資料');
    }
    gs.sort((a, b) => b.total - a.total);
    const top = gs.slice(0, 8).concat(gs.slice(-6).filter(x => !gs.slice(0, 8).some(y => y.group_id === x.group_id)));
    const denom = top.reduce((s, g) => s + Math.abs(g.total || 0), 0);
    const c = chart('instGroups', {
      /* 占比 %（Andy 2026-09-18）：分母用「畫面上這些族群淨買超絕對值的總和」——
         法人有買有賣，直接加總會正負相抵、分母趨近 0，百分比就會爆掉。*/
      tooltip: { ...tip, trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: ps => `<b>${ps[0].name}</b><br>` + ps.map(q => `${q.marker}${q.seriesName} ${fmt.lot(q.value / 1000)}`).join('<br>')
          + `<br>占比 <b>${fmt.n(Math.abs(ps.reduce((s, q) => s + (q.value || 0), 0)) / (denom || 1) * 100, 1)}%</b>`
          + '<br><small>點一下看成分股</small>' },
      /* ★ 2026-09-20：right 24 → 42。最右邊那個刻度標籤是**置中對齊在刻度上**的，
         所以它有一半會伸出格線外；「100.0 萬張」在 11px 下約 62px 寬，一半 31px，
         加上留白取 42 —— 這個數字是算出來的，不是試出來的。
         24 的時候在 1536px / 1920px 量到它跑出容器 5px（多寬度掃描抓到的）。
         天數拉 Bar 的預設從「跟著期間」改成 20 天之後，資料範圍變了、刻度也跟著變寬，
         才把這個一直都在的邊界問題逼出來。 */
      legend: { textStyle: { color: CH.ink2 }, top: 0 }, grid: { left: 108, right: 42, top: 30, bottom: 22 },
      // hideOverlap：1280px 量到「-250.0 萬張」和「-200.0 萬張」疊在一起（刻度太密）
      xAxis: { ...axisStyle, axisLabel: { formatter: v => fmt.lot(v / 1000), color: CH.ink3, hideOverlap: true } },
      yAxis: { ...axisStyle, type: 'category', inverse: true,
        // 族群名後面直接掛占比 %，不用滑過去才看得到
        data: top.map(g => `${g.group_name}  ${fmt.n(Math.abs(g.total || 0) / (denom || 1) * 100, 1)}%`),
        // width/overflow：「電子零組件業  2.1%」比 grid.left 的 108px 還長，會凸出容器左緣
        axisLabel: { color: CH.ink2, width: 100, overflow: 'truncate' } },
      series: [['外資', 'foreign', '#3ee0ff'], ['投信', 'trust', '#ffb454'], ['自營', 'dealer', '#8b7bff']].map(([n, k, col]) => ({
        name: n, type: 'bar', stack: 'a', barWidth: 14,
        data: top.map(g => ({ value: g[k] || 0, gid: g.group_id, dim: !!(pick && pick !== g.group_id),
          itemStyle: { color: col, opacity: (pick && pick !== g.group_id) ? 0.14 : 1 } })),
        itemStyle: { color: col } })),
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.gid) location.hash = '#industry/group/' + q.data.gid; });
    filterChips('instGroups', top.map(g => ({ gid: g.group_id, name: g.group_name })), pick,
      (nx) => renderInstPeriod(p, nx));
  }

  /* 資金集中度（Andy 2026-09-18）：
       「前幾大當我游標點選那天時，會旁邊出現對應族群，
         且對應族群在點會出現對應股票，此時的股票點選才會聯街道個股畫面，
         均線可以設定最多6條 分別 5、10、20、60、120、240並且可以篩選」

     三件事：
     ① 均線six條可勾選 —— 前端自己用收盤序列算，不必回頭改後端（也不必動 indicators.py，
        那是 K 線用的，口徑不同不要混）。勾選記在 localStorage。
     ② 點某一天 → 右側列出那天的前 N 大族群（資料在 concentration 每列的 top 欄位）。
     ③ 再點族群 → 原地展開那天那個族群的前 5 檔（concentration_members，獨立檔）。
        **只有股票才連到個股頁**，族群晶片只是展開，不跳頁。
     後端的 concentration 已從 120 天拉到 400 天，不然 240 日均線根本算不出來。*/
  const CONC_MAS = [5, 10, 20, 60, 120, 240];
  let concMaOn = null;                       // Set；null＝還沒讀過 localStorage
  function concMaSet() {
    if (concMaOn) return concMaOn;
    let v = null;
    try { v = JSON.parse(localStorage.getItem('tw.conc.ma') || 'null'); } catch (e) { /* 私密視窗 */ }
    concMaOn = new Set(Array.isArray(v) && v.length ? v : [20, 60]);
    return concMaOn;
  }
  // 簡單移動平均；前面不足 n 筆的那幾格給 null（不要用半截資料充數）
  function sma(arr, n) {
    const out = []; let sum = 0, cnt = 0;
    for (let i = 0; i < arr.length; i++) {
      const v = arr[i];
      if (v != null) { sum += v; cnt++; }
      if (i >= n) { const old = arr[i - n]; if (old != null) { sum -= old; cnt--; } }
      out.push(i >= n - 1 && cnt === n ? sum / n : null);
    }
    return out;
  }

  function renderConc(conc, topN) {
    if (!conc || !conc.length) return empty('conc');
    const key = topN === 10 ? 'top10_share' : 'top_share';
    const has10 = conc.some(r => r.top10_share != null);
    if (topN === 10 && !has10) { $('#concState').textContent = '前 10 大的歷史還在回補'; return empty('conc', '前 10 大集中度還在回補，先看前 5 大'); }
    const vals = conc.map(r => (r[key] == null ? null : +r[key]));
    const last = conc[conc.length - 1] || {};
    const cur = last[key], ma20 = sma(vals, 20)[vals.length - 1];
    if (cur != null && ma20 != null) {
      const diff = cur - ma20;
      $('#concState').textContent = `前 ${topN} 大目前 ${fmt.n(cur, 1)}%，`
        + (diff > 0.8 ? '高於 20 日均 → 行情縮圈在主流，冷門股不容易動'
          : diff < -0.8 ? '低於 20 日均 → 資金在擴散輪動，主流容易休息'
            : '貼著 20 日均 → 沒有明顯的縮圈或擴散');
    }
    // ---- 均線勾選列（每次重畫都重建，才跟得上主題換色）
    const on = concMaSet();
    const box = $('#concMa');
    if (box) {
      box.innerHTML = '<span class="muted">均線</span>' + CONC_MAS.map((n, i) =>
        `<label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer">
           <input type="checkbox" data-ma="${n}" ${on.has(n) ? 'checked' : ''}>
           <span style="color:${PALETTE[i % PALETTE.length]}">${n} 日</span></label>`).join('');
      $$('input[data-ma]', box).forEach(inp => inp.onchange = () => {
        const n = +inp.dataset.ma;
        if (inp.checked) on.add(n); else on.delete(n);
        try { localStorage.setItem('tw.conc.ma', JSON.stringify([...on])); } catch (e) { /* 忽略 */ }
        renderConc(conc, topN);
      });
    }
    const maSeries = CONC_MAS.filter(n => on.has(n)).map((n) => ({
      name: `${n} 日均`, type: 'line', data: sma(vals, n), smooth: .3, showSymbol: false,
      lineStyle: { color: PALETTE[CONC_MAS.indexOf(n) % PALETTE.length], width: 1.4,
        type: n >= 120 ? 'dashed' : 'solid' },
    }));
    const c = chart('conc', {
      tooltip: { ...tip, trigger: 'axis' }, grid: { left: 50, right: 20, top: 30, bottom: 30 },
      legend: { type: 'scroll', textStyle: { color: CH.ink2 }, pageTextStyle: { color: CH.ink3 }, top: 0 },
      xAxis: { ...axisStyle, type: 'category', data: conc.map(r => r.date), axisLabel: { color: CH.ink3, formatter: v => v.slice(5) } },
      yAxis: { ...axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: `前 ${topN} 族群佔比`, type: 'line', data: vals, smooth: .3, showSymbol: false,
        lineStyle: { color: CH.cyan, width: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
          [{ offset: 0, color: hexA(CH.cyan, theme() === 'light' ? .22 : .35) }, { offset: 1, color: hexA(CH.cyan, 0) }]) } },
      ...maSeries],
    }, { notMerge: true });
    /* ---- 點某一天 → 右側列出那天的前 N 大族群
       ★ 不能用 c.on('click')：這是一條 showSymbol:false 的折線，圖上沒有可點的點，
         series 的 click 只有「剛好點在線上」才會觸發 —— 使用者其實點不到
         （2026-09-19 驗收抓到：點下去側欄沒開）。
         改成掛在 zrender 上：整張圖任何位置都能點，再用 convertFromPixel
         換回是哪一天。這也是 ECharts 官方建議「點空白處」的做法。*/
    if (c) {
      const zr = c.getZr();
      zr.off('click');
      zr.on('click', (ev) => {
        const pt = [ev.offsetX, ev.offsetY];
        if (!c.containPixel({ gridIndex: 0 }, pt)) return;
        const idx = c.convertFromPixel({ seriesIndex: 0 }, pt);
        const i = Math.round(Array.isArray(idx) ? idx[0] : idx);
        const row = conc[Math.max(0, Math.min(conc.length - 1, i))];
        if (row) concDay(row);
      });
    }
  }

  /* 點到某一天之後的側欄：那天的前 N 大族群 → 點族群原地展開那天的前 5 檔成分股。
     ★ 只有股票會連到個股頁；族群晶片只展開、不跳頁（Andy 講得很清楚）。*/
  async function concDay(row) {
    const box = $('#concSide'); if (!box) return;
    const top = row.top || [];
    box.hidden = false;
    if (!top.length) {
      box.innerHTML = `<div class="hh"><b>${row.date}</b><span class="m">這一天沒有留族群明細</span>
        <span class="sp"></span><button class="btn small" data-x="1">收起 ✕</button></div>`;
    } else {
      box.innerHTML = `<div class="hh"><b>${row.date}</b>
          <span class="m">前 ${top.length} 大族群（點族群看那天的成分股）</span>
          <span class="sp"></span><button class="btn small" data-x="1">收起 ✕</button></div>
        <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px" id="concGs">
          ${top.map(t => `<button class="pill" data-g="${t.g}">${fmt.esc(t.n)} <b>${fmt.n(t.share, 1)}%</b></button>`).join('')}
        </div><div id="concMs" style="margin-top:8px"></div>`;
      const mem = await load('concentration_members', { fallback: {} });
      const day = (mem || {})[row.date] || {};
      $$('#concGs button').forEach(b => b.onclick = () => {
        const gid = b.dataset.g;
        const openNow = b.classList.contains('on');
        $$('#concGs button').forEach(x => x.classList.remove('on'));
        const ms = $('#concMs');
        if (openNow) { ms.innerHTML = ''; return; }
        b.classList.add('on');
        const list = day[gid] || [];
        ms.innerHTML = list.length
          ? `<div class="row" style="gap:6px;flex-wrap:wrap">`
            + list.map(m => L.stock(m.code, m.name, { cls: 'sm' })).join('')
            + `<a class="pill cyan" href="#industry/group/${gid}">進族群頁 →</a></div>`
          : `<div class="muted">${row.date} 這天沒有留這個族群的成分股（只保留最近 400 個交易日）</div>`;
      });
    }
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => { box.hidden = true; };
  }

  /* ★ 2026-09-23（Andy：「估值篩選 拿掉」）：
     「估值篩選」整張卡片（本益比／股價淨值比／ROE／市值／族群一起篩 ＋ 散點圖 ＋ 右側表格）
     已從 `#flow` 與這裡一起移除，連同它專用的 `VF` 狀態與 `renderVal()`。
     它是這一頁唯一一個讀 `fundamental.json` 的東西，所以那一份也不再載入。
     ⚠ 總覽頁的「族群估值」（`#gval` / `renderGval`）原本判斷是另一張圖、先留著，
       但 2026-09-23 向 Andy 確認後他回「OK」＝ 一起砍，所以那張也已經移除（見 renderTrust 下方的註解）。 */

  // ---------------------------------------------------------------- 題材
  async function renderThemes() {
    const th = await load('themes'); if (!th || !th.themes || !th.themes.length) { empty('themeMap'); return; }
    $('#themeNote').textContent = th.note || '';
    const data = th.themes.map(t => ({ name: t.name, value: t.turnover, id: t.id, heat: t.heat, chg: t.chg_pct, share: t.share, news7: t.news7, itemStyle: { color: heatColor(t.heat) } }));
    const themeOpt = (big) => { const SK = treeSkin(); return ({ tooltip: { ...tip, formatter: p => `<b>${p.name}</b><br>熱度 ${p.data.heat} · 成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>平均漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span> · 近 7 天新聞 ${p.data.news7}<br><small>點一下看這個題材</small>` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', visibleMin: big ? 20 : 60, label: { overflow: 'truncate', formatter: p => `${p.name}\n熱度 ${p.data.heat} · ${fmt.pct(p.data.chg)}`, fontSize: big ? 15 : 13, ...SK.label }, itemStyle: { borderColor: SK.border, borderWidth: 3, gapWidth: 3 }, data }] }); };
    const c = chart('themeMap', themeOpt(false));
    wheelZoom($('#themeMapWrap'), { onZoom: () => { const i = echarts.getInstanceByDom($('#themeMap')); if (i) i.resize(); } });
    // 點方塊：換下方明細（hash 一樣時 route 不會觸發，所以直接重畫）並捲到明細
    if (c) c.off('click').on('click', p => {
      if (!p.data || !p.data.id) return;
      const h = '#themes/' + p.data.id;
      if (location.hash === h) renderThemeDetail(th, p.data.id); else location.hash = h;
      const d = $('#themeDetail'); if (d && d.scrollIntoView) setTimeout(() => d.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
    });
    const tz = $('#themeZoom');
    if (tz) tz.onclick = () => openZoom('題材資金熱力', (body, chipBox, close) => {
      const bc = chart(body, themeOpt(true));
      if (bc) bc.off('click').on('click', p => {
        if (!p.data || !p.data.id) return;
        close(); location.hash = '#themes/' + p.data.id;
      });
    });
    const sel = location.hash.split('/')[1];
    renderThemeDetail(th, sel || th.themes[0].id);
  }
  // 題材產品圖：點零件→列出該零件的個股（成員表已於 2026-09-23 移除，所以不再有「滑過成員列」那一端）。
  function wireThemeDiagram(host, t) {
    const root = $('#themeDiagram', host); if (!root) return;
    const box = $('#themeParts', host);
    const nodes = $$('[data-part]', root);
    const color = {}, codesOf = {}, used = new Set();
    let i = 0;
    // 顏色規則：能對到供應鏈環節就用環節色（跟產業鏈頁一致）；同一張圖裡顏色不重複，
    // 否則五個零件都掛在「電源」環節時整張圖會變成同一色，反而分不出來。
    const pick = (seg) => {
      const sc = seg && L.segColor(seg);
      if (sc && !used.has(sc)) { used.add(sc); return sc; }
      while (used.has(PALETTE[i % PALETTE.length]) && i < PALETTE.length * 2) i++;
      const c = PALETTE[i++ % PALETTE.length]; used.add(c); return c;
    };
    nodes.forEach(n => {
      const id = n.dataset.part; if (!id) return;
      if (!(id in color)) color[id] = pick(n.dataset.seg);
      if (n.dataset.codes) codesOf[id] = n.dataset.codes.split(',').filter(Boolean);
    });
    nodes.forEach(n => { if (n.dataset.part) n.style.setProperty('--c', color[n.dataset.part]); });
    $$('[data-chain]', root).forEach(n => { n.style.cursor = 'pointer'; n.onclick = () => { location.hash = '#industry/' + n.dataset.chain; }; });
    // 圖上的代號標籤直接進個股頁（不必先點環節）
    $$('.scode', root).forEach(n => { n.onclick = (e) => { e.stopPropagation(); goStock(n.dataset.code); }; });
    const paint = (id) => {
      nodes.forEach(n => { n.classList.toggle('sel', !!id && n.dataset.part === id); n.classList.toggle('dim', !!id && n.dataset.part !== id); });
      if (!box) return;
      if (!id || !(codesOf[id] || []).length) { box.innerHTML = ''; return; }
      const n = nodes.find(x => x.dataset.part === id && x.classList.contains('stn')) || nodes.find(x => x.dataset.part === id);
      const ttl = (n && $('.lbl', n) && $('.lbl', n).textContent) || '';
      const mem = new Set((t.members || []).map(m => m.code));
      // 依族群分組列出這個環節的台股，才看得出來誰跟誰是同一塊的競爭對手
      const byG = {};
      codesOf[id].forEach(c => { const g = L.cgroup[c] || '_'; (byG[g] = byG[g] || []).push(c); });
      box.innerHTML = `<div class="segbox" style="--c:${color[id]}"><b class="t">${fmt.esc(ttl)}</b>
        <span class="muted" style="font-size:12px">灰色＝目前不在這個題材成員名單裡，但同樣做這塊</span>
        ${Object.entries(byG).map(([g, cs]) => `<div class="row"><span class="muted" style="min-width:7em">${g === '_' ? '未分類' : L.group(g)}</span>${cs.map(c => L.stock(c, null, { cls: mem.has(c) ? '' : 'out' })).join('')}</div>`).join('')}</div>`;
    };
    let cur = null;
    nodes.forEach(n => { n.onclick = (e) => { e.stopPropagation(); cur = (cur === n.dataset.part) ? null : n.dataset.part; paint(cur); }; });
  }
  /* ★ 2026-09-23（Andy：「題材這頁 將中間這兩個表格拿掉」）：
     原本這裡有兩張卡片 —— 左邊「題材標題 ＋ 五個數字方塊 ＋ 熱度走勢折線」、
     右邊「成員表（依族群分組）」—— 兩張整塊移除，只留下產品剖析圖與「其他題材」那排標籤。
     連帶拆掉的東西（留著只會變成永遠收不到訊息的死碼）：
       ① `themeMembersByGroup()`：只有成員表在用。
       ② `#themeSeries` 那張折線圖：`themes.json` 的 `series` 仍在，只是前端不再畫。
       ③ `wireThemeDiagram()` 裡「滑過成員列 → 剖析圖零件亮起」的兩端（發送端是成員列，
          接收端是 `paint()` 對 `#themeMembers tr` 加 `.sel`）。
       ④ 「← 回題材總覽」鈕：上方的題材熱力圖本來就一直在同一頁，點別塊就換題材，
          所以回得去，不必另外補一顆鈕。
     ⚠ 22 個題材裡有 3 個（面板封裝／石化／被動元件）還沒畫剖析圖，兩張卡拿掉之後
       它們會整塊空白，所以留一句說明，不要讓使用者以為網頁壞了。*/
  function renderThemeDetail(th, id) {
    const t = th.themes.find(x => x.id === id) || th.themes[0]; if (!t) return;
    const el = $('#themeDetail');
    const dg = (window.ThemeDiagrams || {})[t.id];
    // 標題被拿掉了，所以把題材名接到剖析圖的抬頭上 —— 不然使用者看不出現在看的是哪一個題材
    const head = `<h3>產品剖析圖 <small>${fmt.esc(t.name)}${t.desc ? '　' + fmt.esc(t.desc) : ''}</small></h3>`;
    const other = `<div class="linkrow" style="margin-top:12px"><span class="muted">其他題材</span>${th.themes.filter(x => x.id !== t.id).slice(0, 12).map(x => L.theme(x.id, x.name)).join('')}</div>`;
    el.innerHTML = dg
      ? `<div class="card"><div class="row spread">${head}<small class="muted">上游 → 中游 → 下游；原創等角示意圖，非實物比例。點環節看該段台股、點代號直接進個股頁</small></div>
        <div id="themeDiagram" class="dgwrap">${dg()}</div><div id="themeParts"></div>${other}</div>`
      : `<div class="card">${head}<div class="note">這個題材還沒有產品剖析圖，先從上方熱力圖挑別的題材，或按下面的標籤切換。</div>${other}</div>`;
    if (dg) {
      // 爆炸圖的零件高矮差很多，字串階段量不到尺寸，進 DOM 之後再等比縮到各自那一列
      if (window.ThemeDiagrams.fit) window.ThemeDiagrams.fit($('#themeDiagram', el));
      // 剖析圖不加滾輪縮放（跟產業／個股剖析圖一致，DECISIONS #84；Andy 09-13 再確認）
      // 要看大圖按右上角「放大」，那是明確的按鈕，不會搶走頁面捲動
      wireThemeDiagram(el, t);
    }
  }

  // ---------------------------------------------------------------- 季節性
  /* 任務板（Andy 2026-09-20 選的方案）。資料由 build_payload 從 obsidian/tasks.yaml 轉出來，
     這裡只負責載入與交給 tasks.js 畫。找不到檔案就顯示提示，不要讓整頁空白。 */
  async function renderTasks() {
    const el = document.getElementById('v-tasks'); if (!el) return;
    const d = await load('tasks', { fallback: null });
    if (window.TaskBoard) window.TaskBoard.render(d, el);
  }

  async function renderSeason() {
    const s3 = await load('seasonality_v3'); if (!s3 || !s3.periods || !Object.keys(s3.periods).length) { empty('seasonHeat', '季節性需要歷史回補完成'); return; }
    let period = s3.periods['all'] ? 'all' : Object.keys(s3.periods)[0], metric = 'avg_excess';
    let view = 'heat';
    try { const v = localStorage.getItem('tw.season.view'); if (v === 'line' || v === 'heat') view = v; } catch (e) { /* 忽略 */ }

    /* J1 曲線圖：x 軸是 1–12 月，一條線一個族群。
       只畫「波動最大的前 8 個族群」—— 26 條線疊在一起是一團毛線，看不出任何東西；
       其餘的收進圖例，想看自己點開。0 那條基準線畫粗一點，正負一眼分得出來。*/
    const drawLine = () => {
      const P = s3.periods[period]; if (!P) return empty('seasonLine');
      const byG = {};
      P.cells.forEach(c => { (byG[c.group_id] = byG[c.group_id] || { name: c.group_name, m: {} }).m[c.month] = c[metric]; });
      const isWin = metric === 'win_rate';
      const rank = Object.entries(byG).map(([gid, g]) => {
        const vs = Object.values(g.m).filter(v => v != null);
        const base = isWin ? 50 : 0;
        return { gid, name: g.name, m: g.m,
                 amp: vs.length ? Math.max(...vs.map(v => Math.abs(v - base))) : 0 };
      }).sort((a, b) => b.amp - a.amp);
      const months = Array.from({ length: 12 }, (_, i) => (i + 1) + ' 月');
      const c = chart('seasonLine', {
        tooltip: { ...tip, trigger: 'axis',
          formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.filter(q => q.value != null)
            .sort((a, b) => b.value - a.value).slice(0, 12)
            .map(q => `${q.marker}${q.seriesName} ${isWin ? fmt.n(q.value, 0) + '%' : fmt.pct(q.value)}`).join('<br>') },
        legend: { type: 'scroll', top: 0, textStyle: { color: CH.ink2 }, pageTextStyle: { color: CH.ink3 },
          selected: rank.reduce((o, r, i) => { o[r.name] = i < 8; return o; }, {}) },
        grid: { left: 58, right: 96, top: 38, bottom: 30 },
        xAxis: { ...axisStyle, type: 'category', boundaryGap: false, data: months, axisLabel: { color: CH.ink2 } },
        yAxis: { ...axisStyle, axisLabel: { color: CH.ink3, formatter: (v) => (isWin ? v + '%' : (v > 0 ? '+' : '') + v + '%') } },
        series: rank.map((r, i) => ({
          name: r.name, type: 'line', smooth: 0.35, symbol: 'circle', symbolSize: 6, connectNulls: true,
          data: Array.from({ length: 12 }, (_, k) => { const v = r.m[k + 1]; return v == null ? null : +v.toFixed(2); }),
          lineStyle: { width: i < 3 ? 2.6 : 1.7, color: L.gcolor[r.gid] || PALETTE[i % PALETTE.length] },
          itemStyle: { color: L.gcolor[r.gid] || PALETTE[i % PALETTE.length] },
          endLabel: { show: i < 8, color: L.gcolor[r.gid] || PALETTE[i % PALETTE.length], fontSize: 11,
            formatter: (q) => q.seriesName },
          labelLayout: { moveOverlap: 'shiftY' },
          markLine: i === 0 ? { silent: true, symbol: 'none', label: { show: false },
            lineStyle: { color: hexA(CH.ink3, .6), type: 'dashed', width: 1.4 },
            data: [{ yAxis: isWin ? 50 : 0 }] } : undefined,
          gid: r.gid,
        })),
      }, { notMerge: true });
      if (c) c.off('click').on('click', q => { const r = rank[q.seriesIndex];
        if (r && r.gid) location.hash = '#industry/group/' + r.gid; });
    };

    const paintView = () => {
      $('#seasonHeat').hidden = view !== 'heat';
      $('#seasonLine').hidden = view !== 'line';
      $$('#seasonView button').forEach(b => b.classList.toggle('on', b.dataset.v === view));
    };

    const draw = () => {
      const P = s3.periods[period]; if (!P) return empty('seasonHeat');
      $('#seasonRange').textContent = `${P.from} ～ ${P.to}，${P.years} 年`;
      /* ★ 2026-09-19（Andy 圖三「超額 & 絕對報酬沒變化」）：
         以前超額算不出來時，這裡**靜靜**把指標換成絕對報酬 ——
         使用者按了「超額報酬」卻看到一模一樣的圖，只會以為按鈕壞了。
         現在退回時要**講出來**（畫面上寫一行），不要無聲退回。*/
      const hasExcess = P.cells.some(c => c.avg_excess != null);
      let fellBack = false;
      if (metric === 'avg_excess' && !hasExcess) {
        metric = 'avg_return'; fellBack = true;
        $$('#seasonMetric button').forEach(b => b.classList.toggle('on', b.dataset.v === metric));
      }
      const groups = s3.groups; const gi = {}; groups.forEach((g, i) => { gi[g.group_id] = i; });
      const data = P.cells.map(c => [c.month - 1, gi[c.group_id], c[metric], c]);
      const isWin = metric === 'win_rate'; const vals = data.map(d => d[2]).filter(v => v != null);
      /* 色階上下界：以前用 max|v|，只要有一格離群（例如某族群某月 +48%），
         其餘 300 格就全部擠在色階中央＝看起來全同色。改用 |v| 的 90 分位，
         超界的格子走 outOfRange 用最濃的顏色，不會被截斷資訊（Andy 2026-09-18 圖19）。*/
      const q90 = (xs) => { if (!xs.length) return 5; const a = xs.slice().sort((x, y) => x - y); return a[Math.min(a.length - 1, Math.floor(a.length * 0.9))] || 5; };
      const cap = q90(vals.map(Math.abs));
      const lim = isWin ? [0, 100] : [-cap, cap];
      const lt = theme() === 'light';
      // 淺色主題要整組換掉：深藍中點（#16203a）在白底上是一塊深色，反而變成最顯眼的東西
      const ramp = isWin
        ? (lt ? ['#f3f5fa', '#7c6ce0', '#dc2440'] : ['#16203a', '#8b7bff', '#ff6b84'])
        : (lt ? ['#1a9e6f', '#f3f5fa', '#e04a66'] : ['#19c489', '#16203a', '#ff6b84']);
      // 格子上的數字：淺色主題的兩端是飽和紅綠，單靠深色字對比不夠，補一圈白色描邊
      const cellLabel = lt
        ? { color: CH.ink, textBorderColor: 'rgba(255,255,255,.85)', textBorderWidth: 2.5 }
        : { color: '#e8eeff' };
      const c = chart('seasonHeat', { tooltip: { ...tip, formatter: p => { const cl = p.data[3]; return `<b>${cl.group_name}</b> ${cl.month} 月<br>平均超額 ${cl.avg_excess != null ? fmt.pct(cl.avg_excess) : '—'}（勝率 ${cl.excess_win_rate ?? '—'}%）<br>平均報酬 ${cl.avg_return != null ? fmt.pct(cl.avg_return) : '—'}（勝率 ${cl.win_rate ?? '—'}%）<br>樣本 ${cl.samples} 年`; } },
        grid: { left: 130, right: 70, top: 10, bottom: 30 }, xAxis: { type: 'category', data: Array.from({ length: 12 }, (_, i) => (i + 1) + ' 月'), ...axisStyle, splitArea: { show: false }, axisLabel: { color: CH.ink2 } },
        yAxis: { type: 'category', data: groups.map(g => g.group_name), ...axisStyle, axisLabel: { color: CH.ink2, fontSize: 12 } },
        /* ★ dimension: 2 不能省。
           資料列是 [月, 族群, 數值, 原始格子物件] 四維，visualMap 沒指定維度時
           ECharts 取「最後一維」＝那個物件 → 轉數字是 NaN → 每一格都落在範圍外 → 全部同色。
           Andy 2026-09-18 圖19「熱力圖根本沒有依據數字變換顏色」就是這一行造成的。*/
        visualMap: { min: lim[0], max: lim[1], dimension: 2, calculable: false, orient: 'vertical', right: 0, top: 'center',
          textStyle: { color: CH.ink3 }, inRange: { color: ramp },
          outOfRange: { color: [ramp[0], ramp[ramp.length - 1]] } },
        series: [{ type: 'heatmap', data: data.map(d => [d[0], d[1], d[2] == null ? null : +d[2].toFixed(1), d[3]]), label: { show: true, ...cellLabel, fontSize: 11, fontFamily: 'JetBrains Mono', formatter: p => p.data[2] == null ? '' : (isWin ? p.data[2] : (p.data[2] > 0 ? '+' : '') + p.data[2]) }, itemStyle: { borderColor: CH.panel, borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.6)' } } }] });
      if (c) c.off('click').on('click', p => drill(p.data[3]));
      $('#seasonNote').innerHTML = fmt.esc(s3.note)
        + `　基準：<b>${fmt.esc(s3.benchmark_source || '大盤')}</b>（${s3.benchmark_months} 個月）。`
        + (fellBack ? '　<b style="color:var(--amber)">這個期間算不出超額報酬（缺大盤同月基準），已自動改看絕對報酬。</b>' : '');
      topThisMonth(P);
      drawLine();          // 兩張圖吃同一份資料、同一個期間與指標，切過去不用等
      paintView();
    };
    const drill = (cell) => {
      const det = (s3.detail || {})[cell.group_id] || {}; const years = Object.keys(det).sort();
      const vals = years.map(y => det[y][cell.month] ?? det[y][String(cell.month)]);
      $('#seasonDrillTitle').innerHTML = `${L.group(cell.group_id, cell.group_name)} · ${cell.month} 月逐年超額報酬 <small>紅正綠負 · 點族群名看成分股</small>`;
      chart('seasonDrill', { tooltip: { ...tip, formatter: p => `${p.name} 年：${p.value != null ? fmt.pct(p.value) : '—'}` }, grid: { left: 50, right: 16, top: 16, bottom: 30 }, xAxis: { ...axisStyle, type: 'category', data: years, axisLabel: { color: CH.ink3 } }, yAxis: { ...axisStyle, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'bar', data: vals.map(v => ({ value: v, itemStyle: { color: v > 0 ? CH.up : CH.down, borderRadius: 3 } })), barWidth: '55%' }] });
    };
    /* N10（Andy 2026-09-19：「圖四 下方族群可以變成輪動階段 四段循環與換段的族群
       這樣形式呈現」）：原本是一張表，改成跟輪動階段同一種四段卡片。
       季節性沒有「循環」，所以四段改成**強弱四級**：
       強勢／偏強／偏弱／弱勢，依「超額報酬勝率 × 0.6 ＋ 平均超額」分。
       樣本少於 3 年的不列（跟熱力圖同一條門檻）。*/
    const SEASON_TIER = [
      { k: 'strong', name: '強勢', color: '#ff4d6d', sub: '這個月歷史上最會漲的一群', act: '可以優先看' },
      { k: 'good', name: '偏強', color: '#ffb454', sub: '勝率或幅度其中一項不錯', act: '可以留意，但別只靠這一項' },
      { k: 'soft', name: '偏弱', color: '#8b7bff', sub: '這個月表現平平', act: '沒有季節性優勢' },
      { k: 'weak', name: '弱勢', color: '#2ee59d', sub: '這個月歷史上偏弱', act: '要買得有別的理由' },
    ];
    const topThisMonth = (P) => {
      const m = new Date().getMonth() + 1;
      const all = P.cells
        .filter(c => c.month === m && c.samples >= 3 && (c.avg_excess != null || c.avg_return != null))
        .map(c => ({ ...c, score: (c.excess_win_rate ?? c.win_rate ?? 0) * 0.6
          + Math.max(-20, Math.min(20, c.avg_excess ?? c.avg_return ?? 0)) }))
        .sort((a, b) => b.score - a.score);
      const box = $('#seasonTop');
      if (!box) return;
      if (!all.length) { box.innerHTML = '<div class="empty">本月尚無足夠樣本</div>'; return; }
      // 四等分（不足 4 個就往前塞）
      const q = Math.max(1, Math.ceil(all.length / 4));
      const buckets = [all.slice(0, q), all.slice(q, q * 2), all.slice(q * 2, q * 3), all.slice(q * 3)];
      box.innerHTML = `<div class="stageboard" id="seasonBoard">${SEASON_TIER.map((t, i2) => {
        const list = buckets[i2] || [];
        return `<div class="stage" style="--c:${t.color}">
          <div class="sh"><b style="color:${t.color}">${t.name}</b><span class="n">${list.length}</span></div>
          <div class="sd">${t.sub}<br><em>${t.act}</em></div>
          <ul>${list.map(r => `<li data-gid="${r.group_id}"><span class="g">${fmt.esc(r.group_name)}</span>
            <span class="m">超額 ${r.avg_excess != null ? fmt.pct(r.avg_excess) : '—'}　勝率 ${r.excess_win_rate ?? r.win_rate ?? '—'}%　${r.samples} 年</span></li>`).join('')
            || '<li class="none">這一段沒有族群</li>'}</ul></div>`;
      }).join('')}</div>
        <div class="note" style="margin-top:8px">${m} 月，依「超額報酬勝率 × 0.6 ＋ 平均超額」分四段；樣本少於 3 年不列。點族群看成分股。</div>`;
      $$('#seasonBoard li[data-gid]').forEach(li => li.onclick = () => toggleRotMembers(li));
    };
    $$('#seasonPeriod button').forEach(b => b.onclick = () => { $$('#seasonPeriod button').forEach(x => x.classList.toggle('on', x === b)); period = b.dataset.v; draw(); });
    $$('#seasonMetric button').forEach(b => b.onclick = () => { $$('#seasonMetric button').forEach(x => x.classList.toggle('on', x === b)); metric = b.dataset.v; draw(); });
    $$('#seasonView button').forEach(b => b.onclick = () => {
      view = b.dataset.v; paintView();
      try { localStorage.setItem('tw.season.view', view); } catch (e) { /* 忽略 */ }
      // 藏起來的容器量不到寬高，切過來要讓 ECharts 重新量一次
      const inst = window.echarts && echarts.getInstanceByDom($('#' + (view === 'line' ? 'seasonLine' : 'seasonHeat')));
      if (inst) setTimeout(() => inst.resize(), 30);
    });
    $$('#seasonPeriod button').forEach(b => { b.style.display = s3.periods[b.dataset.v] ? '' : 'none'; });
    draw();
  }

  // ---------------------------------------------------------------- 事件側欄
  async function renderEvents() {
    const [news, bv] = await Promise.all([load('news'), load('broker_views')]);
    const items = (news || []).map(n => ({ ...n, cat: n.category || '台股' }));
    (bv || []).forEach(b => items.push({ date: b.date, title: `${b.broker || '券商'} 目標價 ${b.target_price}${b.name ? '（' + b.name + ' ' + b.code + '）' : ''}${b.action ? ' · ' + b.action : ''}`, url: b.url, source: '新聞引述', cat: '券商', code: b.code }));
    /* 每一則的日期用同一個口徑取：先 published_at 再 date。
       以前標題旁邊寫的是 meta.data_date（價量資料的日期），清單裡卻有比它新的券商目標價 ——
       Andy 2026-09-14 截圖回報「今日事件那需要對應正確日期」就是這個：
       標題寫 09-11、裡面卻列著 09-14 的項目。現在改成顯示「清單裡真正最新的那一天」，
       而且會跟著分類切換重算（切到「券商」跟切到「總經」最新日期本來就不同）。 */
    const dt = (i) => {
      const raw = String(i.published_at || i.date || '').trim();
      if (!raw) return '';
      if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
      // 新聞的 published_at 是 RFC 2822（'Fri, 11 Sep 2026 22:00:36 +0800'），
      // 直接切前十個字會變成 'Fri, 11 Se'，排序也會變成照星期幾的英文字母排。
      const ms = Date.parse(raw);
      return isNaN(ms) ? String(i.date || '').slice(0, 10)
        : new Date(ms).toLocaleDateString('sv-SE', { timeZone: 'Asia/Taipei' });
    };
    items.forEach(i => { i._d = dt(i); });
    items.sort((a, b) => b._d.localeCompare(a._d));
    $('#evCount').textContent = items.length;
    const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Taipei' });   // 'YYYY-MM-DD'
    /* 日期改成下拉選單（Andy 2026-09-15：「日期那邊可以變成清單選項選擇日期」，
       而且「保留前 1 個禮拜資訊」）。選項只列最近七天，每個後面帶那一天的筆數 ——
       不然選到一個空日期只會看到「沒有這類事件」，不知道是選錯還是真的沒事。
       日期選單跟著分類走：切到「券商」時，沒有券商目標價的那幾天就不該出現在選單裡。 */
    const WEEK = 7;
    const weekStart = (() => { const d = new Date(today + 'T00:00:00'); d.setDate(d.getDate() - (WEEK - 1)); return d.toLocaleDateString('sv-SE'); })();
    const MD = (d) => d.slice(5).replace('-', '/');
    let cat = 'all', pick = 'all';
    const sel = $('#evDate');
    const draw = () => {
      const byCat = items.filter(i => cat === 'all' || i.cat === cat);
      // 最近一週的日期（新到舊）；更早的仍留在「全部」裡，只是不單獨列一個選項
      const cnt = new Map();
      byCat.forEach(i => { if (i._d && i._d >= weekStart) cnt.set(i._d, (cnt.get(i._d) || 0) + 1); });
      const days = [...cnt.keys()].sort().reverse();
      if (pick !== 'all' && !cnt.has(pick)) pick = 'all';     // 換分類後那天沒東西了就退回全部
      const newest = days[0] || (byCat[0] || {})._d || '';
      sel.innerHTML = `<option value="all">全部（${byCat.length}）</option>`
        + days.map(d => `<option value="${d}"${d === pick ? ' selected' : ''}>${d === today ? '今天 ' + MD(d) : MD(d)}（${cnt.get(d)}）</option>`).join('');
      sel.value = pick;
      const stale = !!newest && newest < today;
      sel.className = 'minisel' + (stale ? ' stale' : '');
      sel.title = stale ? `最新一則是 ${newest}，今天（${today}）還沒有新事件` : '選一天看那天發生什麼（保留最近一週）';
      const list = pick === 'all' ? byCat : byCat.filter(i => i._d === pick);
      $('#evList').innerHTML = list.slice(0, 120).map(i => `<div class="ev"><a href="${fmt.esc(i.url || '#')}" target="_blank" rel="noopener">${fmt.esc(i.title)}</a><div class="m"><span class="mono">${fmt.esc(i._d)}</span><span class="cat">${fmt.esc(i.cat)}</span><span>${fmt.esc(i.source || '')}</span>${(i.code ? [i.code] : String(i.codes || '').split(/[,\s]+/).filter(Boolean)).slice(0, 4).map(c => L.stock(c, L.cname[c] || c, { cls: 'sm' })).join('')}</div></div>`).join('')
        || `<div class="empty">${pick === 'all' ? '沒有這類事件' : pick + ' 沒有這類事件'}</div>`;
    };
    $$('#evFilters button').forEach(b => b.onclick = () => { $$('#evFilters button').forEach(x => x.classList.toggle('on', x === b)); cat = b.dataset.c; draw(); });
    sel.onchange = () => { pick = sel.value; draw(); };
    draw();
    /* 事件側欄要真的關得掉。手機用 .open 滑出來，桌機要靠 .layout.noside 把那一欄收掉 ——
       以前只 toggle .open，桌機按了完全沒反應，而且側欄佔掉 360px 讓候選表的六個欄位躲進捲軸。 */
    const SIDE_KEY = 'tw.side';
    /* ★ 820px 以下這個側欄不是「一欄」，是**蓋在內容上的浮層**
       （index.html 的 `@media (max-width:820px)` 把 aside 改成 position:fixed）。
       2026-09-22 量到的事實：800px 時浮層從 x=440 蓋到 800，
       而圖別選單裡「MLCC」那張卡的中心在 x=586 —— **真人點下去點到的是浮層，不是那張卡**。
       （1100px 時卡片右緣 699、浮層左緣 740，只差 41px；1440px 以上才真的不重疊。）
       這不是測試環境的怪象：任何人把瀏覽器縮成半邊，右半頁就是點不動的。

       兩個修法一起下：
         ① 窄畫面一進站**一律先關著**。存起來的偏好是「桌機要不要留那一欄」，
            不該拿來決定「手機要不要彈出一個蓋住半頁的浮層」。
         ② 浮層狀態下**點外面就關掉**（浮層本來就該這樣）。
       ⚠ 自動關的時候**不准覆寫存起來的偏好** —— 不然使用者在手機上開一次，
         回到桌機那一欄就莫名其妙不見了。 */
    const SIDE_OVERLAY_MAX = 820;                      // 跟 index.html 的 media query 同一個數字
    const sideIsOverlay = () => window.innerWidth <= SIDE_OVERLAY_MAX;
    const setSide = (open, remember = true) => {
      $('#side').classList.toggle('open', open);
      $('#layout').classList.toggle('noside', !open);
      if (remember) { try { localStorage.setItem(SIDE_KEY, open ? '1' : '0'); } catch (e) { /* 忽略 */ } }
      window.dispatchEvent(new Event('resize'));       // 欄寬變了，圖表要重畫
    };
    let sideOpen = true;
    try { sideOpen = localStorage.getItem(SIDE_KEY) !== '0'; } catch (e) { /* 忽略 */ }
    setSide(sideIsOverlay() ? false : sideOpen, false);
    /* 讓別的模組也開得了關得了這一欄（DECISIONS #248：成分股可以暫時蓋住事件面板）。
       第二個參數 remember=false 很重要 —— 那是「暫時蓋住」，不是使用者改了偏好，
       關掉之後要回到他自己設定的狀態。*/
    window.twSetSide = setSide;
    window.twSideWanted = () => { try { return localStorage.getItem(SIDE_KEY) !== '0'; } catch (e) { return true; } };
    $('#evToggle').onclick = () => setSide($('#layout').classList.contains('noside'));
    $('#evClose').onclick = () => setSide(false);
    // 點浮層外面就收掉。用 capture 才攔得到那些自己 stopPropagation 的元件（剖析圖的零件就是）。
    document.addEventListener('pointerdown', (e) => {
      if (!sideIsOverlay()) return;
      const a = $('#side');
      if (!a || !a.classList.contains('open')) return;
      if (e.target.closest('#side') || e.target.closest('#evToggle')) return;
      setSide(false, false);                           // 不覆寫桌機的偏好
    }, true);
    // 從寬拖窄：那一欄變成浮層的瞬間要收掉，不然一樣蓋住內容
    window.addEventListener('resize', () => {
      if (sideIsOverlay() && $('#side').classList.contains('open')) setSide(false, false);
    });
  }

  // ---------------------------------------------------------------- 搜尋
  async function initSearch() {
    const idx = {};
    (L.all || []).forEach(c => { idx[c.code] = c.name || c.code; });
    if (!Object.keys(idx).length) {           // 索引還沒產出時的退路
      const cands = await load('candidates'); const gd = await load('groups_detail');
      (cands || []).forEach(c => { idx[c.code] = c.name; });
      Object.values(gd || {}).forEach(g => (g.members || []).forEach(m => { if (!idx[m.code]) idx[m.code] = m.name; }));
    }
    const list = Object.entries(idx);
    const q = $('#q'), sg = $('#sugg');
    q.addEventListener('input', () => { const v = q.value.trim().toLowerCase(); if (!v) { sg.style.display = 'none'; return; } const hits = list.filter(([c, n]) => c.startsWith(v) || (n || '').toLowerCase().includes(v)).slice(0, 12); sg.innerHTML = hits.map(([c, n]) => `<div data-c="${c}"><span class="code">${c}</span>${fmt.esc(n)}<span class="g">${fmt.esc(L.gname[L.cgroup[c]] || '')}</span></div>`).join(''); sg.style.display = hits.length ? 'block' : 'none'; $$('div', sg).forEach(d => d.onclick = () => { sg.style.display = 'none'; q.value = ''; goStock(d.dataset.c); }); });
    q.addEventListener('keydown', e => { if (e.key === 'Enter') { const v = q.value.trim(); const hit = list.find(([c]) => c === v) || list.find(([c, n]) => (n || '') === v); if (hit) { sg.style.display = 'none'; q.value = ''; goStock(hit[0]); } } });
    document.addEventListener('click', e => { if (!e.target.closest('.search')) sg.style.display = 'none'; });
  }

  /* 資料新鮮度（Andy：「我今天盤後才看到，等到隔天才買」「不知道到底更新了沒」）：
     把「更新到哪一天、落後多少、哪些來源沒回資料、上次跑是什麼時候」直接攤在頁面頂端。
     以前只有「3 天沒更新」才會跳提示，而且來源失敗完全看不出來（errors 一直是空陣列）。*/
  /* 網頁版號（Andy 2026-09-16：「每次說有更新，但打開來跟原本一樣」）。
     來源是 <meta name="tw:build">，部署前由 scripts/stamp_assets.py 填成
     「commit 前 7 碼|建置時間」。這一支刻意跟資料日期分開講 ——
     「網頁換版了沒」跟「資料更新到哪一天」是兩件事，以前混在一起所以永遠講不清。*/
  function buildInfo() {
    const m = document.querySelector('meta[name="tw:build"]');
    const raw = (m && m.getAttribute('content') || '').trim();
    const [ver, at] = raw.split('|');
    const c = document.querySelector('meta[name="tw:commit"]');
    return { ver: (ver || 'dev').trim(), at: (at || '').trim(),
             sha: ((c && c.getAttribute('content')) || '').trim(), raw };
  }

  /* 版號改成「西元日期＋今天第幾版」（Andy 2026-09-18：「版號用西元＋日期，
     以及第幾次改動命名」）。之前寫 commit 前 7 碼 —— 對得上 GitHub，
     但人看不出這是今天第幾版，也看不出兩個版本誰新誰舊（sha 是亂碼、沒有順序）。
     commit 短碼沒有丟掉，移到 tooltip 與連結上，要對照 GitHub 時還在。*/
  function renderBuild() {
    const b = buildInfo();
    const el = $('#buildver');
    if (!el) return b;
    el.textContent = b.at ? `v ${b.ver} · ${b.at}` : `v ${b.ver}`;
    const isCommit = /^[0-9a-f]{7,40}$/.test(b.sha);
    el.title = (b.ver === 'dev' ? '本機開發版，還沒經過部署流程'
                 : `這個網頁的版本：${b.ver}${b.at ? '，建置於 ' + b.at + '（台北）' : ''}`)
      + (isCommit ? `\ncommit ${b.sha} —— 點開對照 GitHub` : '');
    el.href = isCommit
      ? `https://github.com/MiaoZiKe/tw-rotation/commit/${b.sha}`
      : 'https://github.com/MiaoZiKe/tw-rotation/commits/main';
    return b;
  }

  function renderFreshness(meta) {
    const pad = (n) => String(n).padStart(2, '0');
    const tpe = (iso) => { if (!iso) return null; const d = new Date(iso);
      const t = new Date(d.getTime() + 8 * 3600e3);    // 轉台北時間
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())} ${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}`; };
    const D_ = meta.data_date || '';
    $('#asof').textContent = D_ ? `${D_} 盤後` : '—';

    const bits = [];
    let level = '';                                     // '' 正常 / 'warn' / 'bad'
    // 1) 資料湖已經有更新的一天，但前端沒採用 → 那天的上市資料沒到齊
    if (meta.price_ahead_of_payload && meta.price_latest) {
      bits.push(`資料湖已經有 <b>${fmt.esc(String(meta.price_latest))}</b> 的價格，但那天的上市資料沒到齊，所以畫面仍顯示 <b>${fmt.esc(D_)}</b>`);
      level = 'warn';
    }
    // 2) 多久沒更新
    const gen = meta.generated_at ? new Date(meta.generated_at) : null;
    if (gen) {
      const hrs = (Date.now() - gen.getTime()) / 3600e3;
      if (hrs > 72) { bits.push(`已經 <b>${Math.floor(hrs / 24)} 天</b>沒有重新產出，排程可能掛了`); level = 'bad'; }
      else if (hrs > 30) { bits.push(`上次產出是 ${Math.floor(hrs)} 小時前`); level = level || 'warn'; }
    }
    // 2b) 今天的價量是 mis 補的暫定值嗎
    //     開高低收是準的（三個來源對過一字不差），但成交量是盤中口徑、不含盤後定價交易，
    //     逐檔少 0.5%～15%。跟成交值有關的東西（資金流向、成交值排名）今天要打折看。
    const prov = meta.provisional || {};
    if (prov.is_provisional) {
      bits.push(`<b>${fmt.esc(D_)}</b> 的價量是收盤即時報價補的<b>暫定值</b>：`
        + `開高低收準確，但<b>成交量與成交值偏低</b>（不含盤後定價交易，逐檔少 0.5%～15%），`
        + `資金流向與成交值排名今天請打折看。證交所正式資料進來後會自動覆蓋`);
      level = level || 'warn';
    }
    // 3) 哪些來源沒回資料
    const empt = meta.last_run_empty || [], errs = meta.last_run_errors || [];
    if (errs.length) { bits.push(`來源出錯：<b>${errs.slice(0, 4).map(e => fmt.esc(String(e).split(':')[0])).join('、')}</b>`); level = 'bad'; }
    if (empt.length) { bits.push(`沒回資料的來源：<b>${empt.slice(0, 6).map(fmt.esc).join('、')}</b>`); level = level || 'warn'; }
    if (meta.demo) { bits.push('這是示範資料，不是真實行情'); level = 'bad'; }

    const tail = [];
    // 盤後第一輪（台北 15:30）只抓價量，法人／融資券要傍晚才出。
    // 講清楚是「還沒到」而不是「掛了」，否則每天下午都會被誤會。
    if (meta.last_run_phase === 'price') tail.push('這輪只更新價量（法人與融資券傍晚那輪才補）');
    if (meta.last_run_at) tail.push(`上次抓資料 ${tpe(meta.last_run_at)}`);
    if (gen) tail.push(`上次產出 ${tpe(meta.generated_at)}`);
    // 網頁版號也寫進來：手機上頂部那顆徽章是藏起來的，這一行是手機唯一看得到版本的地方
    const bd = renderBuild();
    tail.push(`網頁版本 ${fmt.esc(bd.ver)}${bd.at ? '（' + fmt.esc(bd.at) + ' 建置）' : ''}`);
    const b = $('#banner');
    if (!bits.length) {                                  // 一切正常也要講一句，讓人知道系統是活的
      b.innerHTML = `<b>資料更新到 ${fmt.esc(D_)} 盤後</b>，所有來源正常。${tail.length ? '<span class="muted">（' + tail.join('、') + '，台北時間）</span>' : ''}`;
      b.className = 'banner on ok';
    } else {
      b.innerHTML = `<b>資料更新到 ${fmt.esc(D_)} 盤後</b>　·　${bits.join('　·　')}${tail.length ? '<br><span class="muted">' + tail.join('、') + '（台北時間）</span>' : ''}`;
      b.className = 'banner on ' + (level === 'bad' ? 'bad' : 'warn');
    }
  }

  // ---------------------------------------------------------------- 啟動
  async function boot() {
    if (typeof echarts === 'undefined' || typeof LightweightCharts === 'undefined') { $('#banner').textContent = '圖表函式庫載入失敗（vendor/ 目錄缺檔），請重新整理。'; $('#banner').classList.add('on'); }
    // 版號先畫：meta.json 抓失敗時橫幅不會跑，但「網頁是哪一版」這件事還是要看得到
    renderBuild();
    // 主題：<head> 的那段小 script 已經把 data-theme 設好（避免閃一下），這裡只補色票與按鈕
    applyTheme(theme(), false);
    // 分頁切到背景就停播放：省 CPU，也避免回來時一次補跑幾十幀
    document.addEventListener('visibilitychange', () => { if (document.hidden) stopAllPlay(); });
    const tb = document.getElementById('themeBtn');
    if (tb) tb.onclick = () => applyTheme(theme() === 'light' ? 'dark' : 'light', true);
    const meta = await load('meta');
    if (meta) { renderFreshness(meta); }
    window.App = { load, chart, fmt, tip, axisStyle, CH, PALETTE, chgColor, heatColor, treeSkin, hexA, upDown, empty, charts, goStock, D, L, wheelZoom, rangeBar, playBar, theme, applyTheme, liveMerge, onLive, LIVE_KEYS,
      /* 給 scripts/_uitest.py 量「小圓點真的在動」用：回傳當下每一顆點的座標。
         用座標而不是 canvas 指紋 —— WebGL/Canvas 的指紋在這個容器裡量過是
         「永遠不會紅的假驗收」（DECISIONS #199），座標會變才是真的在動。*/
      sankeyDots: () => (sankeyFx ? sankeyFx.dots.map(d => [d.x, d.y, d.lvl]) : []),
      sankeyFxRunning: () => !!(sankeyFx && sankeyFx.running()),
      /* 量密度對比用：每條連線配到幾顆點、多大、多快。
         Andy 要的是「一眼看出哪條線的錢比較多」，而那是量得出來的 ——
         最粗與最細的線各有幾顆點、通過率差幾倍。*/
      sankeyFlowStats: () => {
        const f = (sankeyFlows || []).filter(x => x && x.n);
        if (!f.length) return null;
        const by = f.slice().sort((a, b) => b.r - a.r);
        const top = by[0], bot = by[by.length - 1];
        const rate = (x) => x.n * (x.spd || 1);          // 單位時間通過幾顆＝點數 × 速度
        return { lines: f.length, dots: f.reduce((s2, x) => s2 + x.n, 0),
          maxN: Math.max(...f.map(x => x.n)), minN: Math.min(...f.map(x => x.n)),
          top: { n: top.n, size: +top.size.toFixed(2), spd: +(top.spd || 1).toFixed(2), r: +top.r.toFixed(4) },
          bot: { n: bot.n, size: +bot.size.toFixed(2), spd: +(bot.spd || 1).toFixed(2), r: +bot.r.toFixed(4) },
          nRatio: +(top.n / bot.n).toFixed(2), rateRatio: +(rate(top) / rate(bot)).toFixed(2) };
      },
      // 即時資金去向：現在是不是開著、這一輪打了幾個請求、算出幾個板塊
      sankeyLive: () => ({ on: SKL.on, busy: SKL.busy, err: SKL.err, at: SKL.at,
        intraday: SKL.intraday, boards: Object.keys(SKL.tv).length,
        codes: SKL.codes, reqs: SKL.reqs, marketAmt: SKL.marketAmt, quoteAt: SKL.quoteAt }),
      sankeyLiveToggle: () => sklToggle(),
      /* 驗收「即時模式真的換位」用：把每個節點在畫布上的座標讀出來。
         驗排序陣列是不夠的 —— 陣列換了但畫面沒動（例如整張圖是 notMerge 重建、
         或動畫被吃掉）在驗收上會過，使用者看到的卻還是舊版面。
         y 座標是使用者真正看到的東西，所以驗這個。*/
      sankeyNodeXY: () => {
        const el = document.getElementById('sankey');
        const c = el && (window.echarts ? window.echarts.getInstanceByDom(el) : null);
        return c ? sankeyNodePos(c) : null;
      },
      // 手動催一輪即時（驗收用；平常是 setInterval 每分鐘一次，等不了）
      sankeyLiveTick: () => sklTick(),
      /* ── 盤中即時輪動時鐘（RLV）的量測窗口 ──
         `cover` 就是畫面上那個涵蓋率、`top` 就是「走得最多的族群」那一排的數字，
         驗收量的是**真的畫出去的那一份**，不是另外算一次。*/
      rotLive: () => ({ on: RLV.on, busy: RLV.busy, err: RLV.err, at: RLV.at,
        intraday: RLV.intraday, groups: Object.keys(RLV.pt).length,
        codes: RLV.codes, hit: RLV.hit, reqs: RLV.reqs, skipped: RLV.skipped,
        mkt: RLV.mkt, cover: RLV.cover, uniAmt: RLV.uniAmt, marketAmt: RLV.marketAmt,
        quoteAt: RLV.quoteAt, top: rlvTop(6) }),
      rotLiveToggle: () => rlvToggle(),
      rotLiveTick: () => rlvTick(),
      /* 那條「上一個收盤 → 現在」在**畫面上**有多長（像素）。
         驗「線真的畫出來了」只能量像素 —— 陣列裡有兩個點不代表使用者看得到一條線
         （極座標兩點可能落在同一個像素上）。*/
      rotLiveSeg: () => {
        const el = document.getElementById('rotClock');
        const c = el && window.echarts && echarts.getInstanceByDom(el);
        const at = (window.App && window.App._rotLiveAt) || [];
        if (!c || !at.length) return [];
        const si = ((c.getOption() || {}).series || []).findIndex(x => x.type === 'scatter');
        if (si < 0) return [];
        const at2px = (v) => { try { return c.convertToPixel({ seriesIndex: si }, v); }
          catch (e) { return null; } };
        return at.map(r => {
          const a = at2px(r.p0), f = at2px(r.pf), b = at2px(r.p1);
          const len = (u, v) => ((u && v) ? +Math.hypot(v[0] - u[0], v[1] - u[1]).toFixed(2) : null);
          return { gid: r.gid, name: r.name, dx: r.dx, dy: r.dy,
            tdx: r.tdx, tdy: r.tdy, jump: r.jump, a, f, b,
            px: len(a, b),               // 整條（上一個收盤 → 現在）
            pxInertia: len(a, f),        // 灰虛線那段（慣性）
            pxToday: len(f, b) };        // 亮色箭頭那段（今天的錢推的）
        });
      },
      // 下鑽狀態（驗收「點背景回復預設」用）
      drillState: () => ({ gid: DRILL.gid, chain: DRILL.chain, open: [...DRILL.open],
        stocks: [...DRILL.stocks], sel: sankeySel }) };
    const [im, gt, cands, th, sc, all] = await Promise.all([load('industry_map'), load('groups_today'), load('candidates'), load('themes'), load('supply_chain'), load('stocks', { fallback: [] })]);
    L.init(im, gt, cands, th, sc, all);
    await Promise.all([renderEvents(), initSearch()]);
    await route();
    // 盤中即時層。放在 route() 之後：畫面上先有代號，Live 才知道要抓哪些。
    if (window.Live) window.Live.start();
  }
  boot();
})();
