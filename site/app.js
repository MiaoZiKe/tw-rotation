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
       外面已經拿走 PALETTE 參照的地方才會跟著變。*/
  const PALETTE_DARK = ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871', '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a'];
  const PALETTE_LIGHT = ['#0b7fa6', '#5f4ddb', '#b06a00', '#4a8a15', '#c2185b', '#0369a1', '#8a6d00', '#0f766e', '#c2410c', '#6d28d9', '#047857', '#b91c1c', '#1d4ed8', '#a16207'];
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
        if (i && el.clientWidth > 0 && el.clientHeight > 0) i.resize();
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
      const FALLBACK = { hbm: ['memory'], hyperscaler: ['ai_server_odm'], switch: ['networking', 'ai_server_odm'], ic_design: ['ic_design'], foundry: ['foundry'], adv_pkg: ['advanced_packaging'], osat_test: ['osat'], abf_pcb: ['pcb_abf'], ccl: ['pcb_abf'], thermal: ['server_thermal'], power: ['server_power'], optical: ['optical_comm'], assembly: ['ai_server_odm'], ip_eda: ['silicon_ip'],
        // 一般電子鏈這兩格只有外商（康寧／Apple／SpaceX），沒有台股節點，
        // 不接 fallback 的話點下去列不出任何東西。
        display_material: ['panel'], brand_operator: ['handset_chain'] };
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
    if (o.key) { try { const s = +localStorage.getItem(o.key); if (s >= min && s <= max) v = s; } catch (e) { /* 私密視窗 */ } }
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
  const _players = new Set();
  function stopAllPlay() { _players.forEach(p => { try { p.stop(); } catch (e) { /* 忽略 */ } }); }
  function playBar(box, o) {
    box = typeof box === 'string' ? document.getElementById(box) : box;
    if (!box) return null;
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
      const { min, max } = lim();
      const d = dirOf();
      if (d > 0 ? +inp.value >= max : +inp.value <= min) setV(d > 0 ? min : max);   // 已經在尾端就從頭播
      timer = setInterval(tick, o.frame || 600);
      paintBtn();
    };
    bPlay.onclick = () => (timer ? stop() : start());
    bMinus.onclick = () => { stop(); setV(+inp.value - lim().st); paintBtn(); };
    bPlus.onclick = () => { stop(); setV(+inp.value + lim().st); paintBtn(); };
    inp.addEventListener('pointerdown', stop);  // 自己動手拉就停播放
    inp.addEventListener('input', paintBtn);
    paintBtn();
    const api = { get value() { return +inp.value; }, set(x) { setV(x); paintBtn(); }, stop, start, playing: () => !!timer, el: box };
    _players.add(api);
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
  const VIEWS = ['overview', 'flow', 'market', 'industry', 'themes', 'season', 'tasks'];
  const rendered = {};
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
    $$('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + view));
    /* K 線「寬版」只在個股頁生效：離開個股頁要把右側事件欄還回來，
       不然使用者會覺得事件欄莫名其妙消失了（設定本身留著，回個股頁自動復原）。 */
    // 預設就是寬版（Andy：「K 線圖 default 就大一點」）；只有自己按過關掉才會是窄的
    let wide = true;
    try { const v = localStorage.getItem('tw.kwide'); if (v !== null) wide = v === '1'; } catch (e) { /* 忽略 */ }
    document.body.classList.toggle('kwide', head === 'stock' && wide);
    window.scrollTo({ top: 0 });
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
    const all = D.stocks || [];
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
    if (sub) sub.textContent = `${n} 檔　平均 ${fmt.pct(mu)}　標準差 ${fmt.n(sd, 2)}%　`
      + `（虛線＝用這批樣本自己的平均與標準差畫的常態曲線）`;
    // 點某一段 → 下面只列那一段
    if (c) c.off('click').on('click', (p) => {
      const i = p.dataIndex;
      const lo = i === 0 ? -Infinity : edges[i - 1];
      const hi = i === labels.length - 1 ? Infinity : edges[i];
      const rows = pool.filter(r => (i === 0 ? r.chg_pct <= -10
        : i === labels.length - 1 ? r.chg_pct >= 10
          : r.chg_pct > lo && r.chg_pct <= hi))
        .sort((a, b) => b.turnover - a.turnover).slice(0, 80);
      const box = $('#distPick'); if (!box) return;
      box.hidden = false;
      box.innerHTML = `<div class="hh"><b>${labels[i]}%</b><span class="m">${rows.length} 檔（依成交值）</span>
          <span class="sp"></span><button class="btn small" data-x="1">收起 ✕</button></div>
        <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">
          ${rows.map(r => L.stock(r.code, r.name, { cls: 'sm' })).join('') || '<span class="muted">這一段沒有股票</span>'}</div>`;
      const x = box.querySelector('[data-x]'); if (x) x.onclick = () => { box.hidden = true; };
    });
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
      title.innerHTML = `漲跌家數 <small>今天 ${heat.advancers || 0} 漲 / ${heat.decliners || 0} 跌，漲停 ${(mv.counts || {}).limit_up ?? '—'} 檔、跌停 ${(mv.counts || {}).limit_down ?? '—'} 檔</small>`;
      const sets = [
        ['漲停', mv.limit_up, '漲幅 ≥ 9.5%（成交價照檔位跳，實際常落在 9.7~10.0）'],
        ['跌停', mv.limit_down, '跌幅 ≤ -9.5%'],
        ['漲幅前段', mv.up, '今天漲最多的'],
        ['跌幅前段', mv.down, '今天跌最多的'],
        ['成交值前段', mv.turnover, '今天量最大的，這裡才是真正的戰場'],
      ].filter(t => t[1] && t[1].length);
      if (!sets.length) { body.innerHTML = '<div class="empty">今天沒有明細資料</div>'; return; }
      if (mktTab >= sets.length) mktTab = 0;
      const draw = () => {
        const t = sets[mktTab];
        $('#mktInner').innerHTML = `<div class="kpinote">${t[2]}</div>` + stockTable(t[1], [PCT, CLOSE, TO]);
        bind();
      };
      body.innerHTML = `<div class="card" style="margin:0 0 14px;padding:12px 14px">
          <div class="row spread"><h3 style="margin:0">漲跌分佈 <small id="distSub"></small></h3>
            <div class="row" id="distFilter" style="gap:8px;flex-wrap:wrap"></div></div>
          <div id="chgDistBox"><div id="chgDist" class="chart" style="min-height:260px"></div></div>
          <div class="hpanel" id="distPick" hidden></div></div>`
        + `<div class="seg" id="mktTabs">${sets.map((t, i) =>
        `<button data-i="${i}" class="${i === mktTab ? 'on' : ''}">${t[0]} <em>${t[1].length}</em></button>`).join('')}</div>`
        + `<div id="mktInner" style="margin-top:10px"></div>`;
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
    const [heat, gt, rot, cands, f3, th, trust, gval] = await Promise.all([load('market_heat'), load('groups_today'), load('rotation'), load('candidates'), load('flow_v3'), load('themes'), load('trust_streak'), load('group_valuation'), load('groups_detail'), load('inst_streak', { fallback: {} })]);
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
    renderRotation(f3 && f3.rrg, 5, { board: 'rotMini', clock: 'rotClockMini', compact: true });
    // 總覽這張是縮圖，只給一顆「放大」；拉Bar／篩選／播放都在放大視窗裡（已拍板）
    { const mz = $('#rotMiniZoomBtn'); if (mz) mz.onclick = () => openRotZoom(f3 && f3.rrg, 5); }
    renderThemeStrip(th);
    renderCandidates(cands);
    renderBreadth(heat);
    renderTrust(trust, cands);
    wireStreak(trust, cands);
    renderGval(gval, rot, gt);
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
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子',
    traditional: '傳產', infrastructure: '基礎建設', industry: '其他產業別' };
  let heatChain = null;

  /* 放大罩：熱力圖方塊太小看不清楚時，全螢幕看同一張圖。
     刻意不做「拖曳平移」—— treemap 一旦可以拖，整張圖就會被拖走而且回不來
     （Andy 遇到的空白畫面就是這樣來的）。要看細節就放大或下鑽，位置永遠固定。 */
  function openZoom(title, render) {
    const ov = $('#zoomOv'); if (!ov) return;
    $('#zoomTitle').textContent = title;
    ov.hidden = false;
    document.body.style.overflow = 'hidden';
    const close = () => {
      ov.hidden = true; document.body.style.overflow = '';
      const c = echarts.getInstanceByDom($('#zoomBody')); if (c) c.dispose();
      $('#zoomChips').innerHTML = '';
      document.removeEventListener('keydown', esc);
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
      : Object.keys(chains).map(cid => ({ name: CHAIN_NAME[cid] || cid, cid, children: chains[cid].map(mk) }));
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
        return `<button data-c="${cid}" class="${cur === cid ? 'on' : ''}">${CHAIN_NAME[cid] || cid}<em>${fmt.n(sh, 1)}%</em></button>`;
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

  // 一列族群：名稱、相對大盤強弱、動能方向、成交值佔比
  function rotItem(r) {
    const arrow = r.dmo == null ? '' : r.dmo > 0.15 ? '<span class="ar up">↑</span>' : r.dmo < -0.15 ? '<span class="ar dn">↓</span>' : '<span class="ar fl">→</span>';
    return `<li data-gid="${r.gid}"><span class="g">${fmt.esc(r.name)}</span>${arrow}
      <span class="m">強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 1)}　佔比 ${fmt.n(r.share, 1)}%</span></li>`;
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
  const LBL_FS = 11.5;                 // 標籤字級；排版與驗收都用同一個值
  /* 這一輪排好的標籤位置，key＝scatter 的 dataIndex。
     labelLayout 是每個標籤各呼叫一次的，拿不到「全部標籤」，
     所以先自己算好放這裡，labelLayout 只負責查表。*/
  let rotLbl = {};
  // N3：上一次畫的是哪一組族群 —— 一樣就用 merge（點會自己走過去），不一樣才 notMerge
  let rotLastShape = '';

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
      try { q = c.convertToPixel({ seriesIndex: si }, [Math.min(r.p[0], CLOCK_MAXR), r.p[1]]); }
      catch (e) { q = null; }
      if (!q || !isFinite(q[0]) || !isFinite(q[1])) return;
      px.push({ i, x: q[0], y: q[1], name: r.name });
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

  /* opts（2026-09-18 Andy 圖二、2026-09-20 Andy A4）：
       pick  Set|null  只看這幾個族群（篩選）；null＝全部
       frame int       **看哪一天**：大圈移到「第 frame 天前」那一天的座標；0＝今天
       span  int       軌跡要畫幾天（預設＝back）
       trail bool      軌跡開關（false＝線還在但資料清空，A4 第 7 條「軌跡可以開啟關閉」）

     ★ A4 第 7 條把這支拉Bar 的語意從「畫多長」換成「看哪一天」之後，
       正規化的尺度**一定要固定**，不能再用「當下這一幀的最大偏離量」。
       理由：尺度一變，所有族群的座標會同時被重新縮放 ——
       使用者看到的是「我只是往前拉一天，整盤東西全部跳了一下」，
       那正是 Andy 講的「一天的差距在圖上卻是各種歪曲」的另一半。
       所以尺度改成用**整段軌跡的最大偏離量**算一次，刷動期間完全不動。*/
  function renderRotClock(rows, back, id, compact, opts) {
    opts = opts || {};
    const el = $('#' + id); if (!el) return;
    const cap = compact ? 10 : 16;
    let top0 = rows.slice(0, cap);                       // rotRows 已照成交值佔比排序
    if (opts.pick && opts.pick.size) {
      const picked = rows.filter(r => opts.pick.has(r.gid));
      if (picked.length) top0 = picked;
    }
    /* 回放：把每個族群的位置換成 trail 裡「frame 天前」那一筆。
       trail 是 [日期, rs_ratio, rs_mom] 由舊到新，所以第 k 天前＝倒數第 k+1 筆。*/
    const scope = top0;                       // 尺度與軌跡都用「還沒被 frame 換掉」的原始資料
    let frameDate = null;
    if (opts.frame > 0) {
      top0 = top0.map(r => {
        const t = r.trail || [];
        const w = t[t.length - 1 - opts.frame];
        if (!w) return r;
        frameDate = w[0];
        // 階段要跟著當天的座標重算，否則回放時點還在動、顏色卻停在「今天的階段」
        return { ...r, rs: w[1], mo: w[2], stage: stageOf(w[1], w[2]), was: null, moved: false };
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
    const pos = (x, y) => {                              // (相對強弱, 動能) → [半徑, 角度]
      const dx = ((x || 100) - 100) / sx, dy = ((y || 100) - 100) / sy;
      let a = Math.atan2(dy, dx) * 180 / Math.PI; if (a < 0) a += 360;
      return [Math.min(CLOCK_MAXR, Math.sqrt(dx * dx + dy * dy)), a];
    };
    const pts = top0.map(r => ({ ...r, p: pos(r.rs, r.mo) }));
    const top = pts;
    const maxR = CLOCK_MAXR;
    /* 在極座標上補點，讓線**貼著圓弧走**（Andy 2026-09-18：
       「他的線需要沿著圓圈變化，而不是一個斷點直線跑過去」）。
       ECharts 的 line series 就算掛在 polar 上，兩點之間仍然是在螢幕上連一條直線 ——
       角度差一大，那條線就直接橫跨過圓心，看起來像「跳過去」而不是「轉過去」。
       所以自己在角度與半徑上各補中間點；角度一律走較短的那一邊，
       不然從 350° 到 10° 會沿著圓繞一大圈回去。*/
    const arcPath = (pts) => {
      const out = [];
      for (let i = 0; i < pts.length - 1; i++) {
        const [r0, a0] = pts[i], [r1, a1] = pts[i + 1];
        let d = a1 - a0; if (d > 180) d -= 360; if (d < -180) d += 360;
        const n = Math.max(2, Math.min(24, Math.round(Math.abs(d) / 6) + 2));
        for (let k = 0; k < n; k++) {
          const u = k / n;
          out.push([r0 + (r1 - r0) * u, (a0 + d * u + 360) % 360]);
        }
      }
      if (pts.length) out.push(pts[pts.length - 1]);
      return out;
    };
    /* 尾巴：這 N 天真正走過的路。
       以前只取「N 天前」與「現在」兩點連一條直線 —— 註解寫的理由是「畫整段會變一團毛線」。
       折衷：從實際軌跡挑最多 6 個路標（太密才會變毛線），再用 arcPath 把它們接成弧線，
       這樣既看得出真的怎麼繞，也不會糊成一團。小圈圈仍然標在最舊的那一端。*/
    const span = opts.span != null ? opts.span : back;
    const trailOn = opts.trail !== false;
    const trail = (r) => {
      const t = r.trail || [];
      if (!t.length || !trailOn) return [];
      const seg = t.slice(Math.max(0, t.length - 1 - span));
      const way = seg.length > 1 ? seg : [t[0]];
      /* ★ 2026-09-20：以前這裡只挑 6 個路標，理由是「畫整段會變一團毛線」。
         那個理由在後端把 RS 平滑掉之後已經不成立了（pipeline/compute/rrg.py 的量測：
         一日步長從盤面半徑的 0.255 降到 0.053、直線度 0.07 → 0.38）——
         現在畫滿每一天才看得到 Andy 要的「一天就走一小步」。
         上限 40 個路標純粹是防呆（後端只存 31 天，正常走不到）。*/
      const step = Math.max(1, Math.ceil((way.length - 1) / 40));
      const picked = way.filter((_, i) => i % step === 0);
      if (picked[picked.length - 1] !== way[way.length - 1]) picked.push(way[way.length - 1]);
      const pts = picked.map(w => pos(w[1], w[2]));
      return arcPath(pts);
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
    const o = {
      tooltip: {
        ...tip, trigger: 'item', formatter: (q) => {
          const r = q.data && q.data.row; if (!r) return '';
          const s = STAGE[r.stage];
          return `<b>${fmt.esc(r.name)}</b>　<span style="color:${s.color}">${s.name}</span>`
            + `<br>相對大盤強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 2)}`
            + `<br>動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 2)}`
            + (r.was ? `<br>${back} 天前在「${STAGE[r.was].name}」${r.moved ? '　<b>已經換段</b>' : ''}` : '')
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
          margin: compact ? 6 : 10, fontSize: compact ? 12 : 14, fontWeight: 700,
          formatter: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].name : ''; },
          color: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].color : 'transparent'; },
        },
      },
      /* 外圈留一點餘裕，被夾住的「N 天前」小圈圈才不會壓在盤緣上。
         2026-09-18（Andy 圖二「需要補充圓心到圓外 差異為何」）：
         以前是等距好幾圈細線，看不出哪一圈代表什麼。改成只留兩圈**虛線**，
         並在圖下方用一行字講清楚它們是什麼（#rotCenterNote）：
           0.5 圈＝偏離大盤的一半　/　1.0 圈＝偏離最大的那個族群。*/
      radiusAxis: { type: 'value', min: 0, max: maxR * 1.08, axisLine: { show: false }, axisTick: { show: false },
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
          itemStyle: { color: hexA(STAGE[r.stage].color, .55) },
          lineStyle: { color: hexA(STAGE[r.stage].color, .42), width: 1.6 },
        })),
        // 現在的位置
        {
          type: 'scatter', coordinateSystem: 'polar', z: 5,
          data: top.map(r => ({ value: [Math.min(r.p[0], maxR), r.p[1]], row: r,
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
            const m = rotLbl[q.dataIndex];
            if (!m) return {};
            // 左欄往右長、右欄往左長（見 layoutRotLabels 的註解）
            const align = m.side === 'left' ? 'left' : 'right';
            // 引線從點拉到文字的「內側」那一端，不要穿過文字
            const tip = m.side === 'left' ? m.x + m.rect.w + 4 : m.x - m.rect.w - 4;
            return { x: m.x, y: m.y, align, verticalAlign: 'middle',
              labelLinePoints: [[m.px, m.py], [tip, m.y], [m.side === 'left' ? m.x + m.rect.w : m.x - m.rect.w, m.y]] };
          },
        },
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
            「↻ 箭頭＝行進方向」那一句搬到圖下方的 #rotCenterNote —— 它是 HTML，
            會自己換行，任何寬度都不可能溢出。圖裡只留「回放日期」與一行最短的比例說明。*/
        { type: 'text', right: 12, bottom: 8, silent: true,
          style: { text: (frameDate ? '⏱ 回放：' + frameDate + '\n' : '')
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
    const sameShape = rotLastShape === id + '|' + top.length + '|' + top.map(r => r.gid).join(',');
    rotLastShape = id + '|' + top.length + '|' + top.map(r => r.gid).join(',');
    o.animationDurationUpdate = 620;
    o.animationEasingUpdate = 'linear';        // 等速才像「緩步走」，不要 easeOut 那種急停
    const c = chart(id, o, { notMerge: !sameShape });
    /* 標籤排版要等圖畫完（要有像素座標才知道誰在左誰在右），
       所以先畫一次、算好位置、再 setOption 一次讓 labelLayout 查表。
       第二次不用 notMerge，只是重跑一次標籤排版，不重建尾巴。*/
    /* 驗收要「用數值比，不要用眼睛」量「越外圈顏色越深」，所以把每顆點的
       半徑、混出來的顏色、以及那一段的原色一起攤出來 ——
       混色是 mixHex(底色, 原色, w)，量的人可以從 (顏色, 原色, 底色) 反推出 w，
       再驗 w 真的隨半徑遞增。攤的是**畫上去的值**，不是我心裡想的值。*/
    if (!compact) {
      window.App._rotBg = CH.panel;
      window.App._rotPts = top.map(r => ({ gid: r.gid, name: r.name,
        r: Math.min(r.p[0], maxR) / maxR, color: depthColor(r), base: STAGE[r.stage].color }));
      window.App._rotFrame = { frame: opts.frame || 0, date: frameDate, span, trail: trailOn };
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
        rotLbl = layoutRotLabels(c, el, top);
        window.App._rotLabels = Object.keys(rotLbl).map(k => rotLbl[k].rect);  // 驗收用：量兩兩不重疊、全在畫布內
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
      rotLbl = {};
    }
    if (c) c.off('click').on('click', q => { const r = q.data && q.data.row; if (r) location.hash = '#industry/group/' + r.gid; });
    // N2：兩張圖共用同一份名單（輪動資料的全部族群，依成交值佔比排序）
    if (!compact) groupChips(id, rows.map(r => ({ gid: r.gid, name: r.name })), rankSel);
  }

  function renderRotation(rrg, back, ids) {
    const rows = rotRows(rrg, back);
    const board = $('#' + ids.board);
    if (!rows.length) {
      if (board) board.innerHTML = '<div class="empty">相對輪動需要至少 20 個交易日</div>';
      if (ids.clock) empty(ids.clock, '輪動時鐘需要至少 20 個交易日');
      return;
    }
    if (ids.clock) renderRotClock(rows, back, ids.clock, !!ids.compact,
      { pick: ids.pick, frame: ids.frame, span: ids.span, trail: ids.trail });

    if (ids.cycle) {
      const cy = $('#' + ids.cycle);
      if (cy) cy.innerHTML = STAGE_ORDER.map((k, i) =>
        `<span class="st" style="background:${STAGE[k].color}1f;color:${STAGE[k].color};border:1px solid ${STAGE[k].color}55">${STAGE[k].name}</span>`
        + (i < 3 ? '<span class="ar">→</span>' : '<span class="ar">↩ 回到改善</span>')).join('');
    }
    if (ids.move) {
      const mv = $('#' + ids.move);
      const moved = rows.filter(r => r.moved);
      if (mv) mv.innerHTML = moved.length
        ? `<b>最近 ${back} 個交易日換階段的族群</b>` + moved.slice(0, 10).map(r =>
          `<span class="mv" data-gid="${r.gid}"><i style="background:${STAGE[r.was].color}"></i>${STAGE[r.was].name}
             <em>→</em><i style="background:${STAGE[r.stage].color}"></i>${STAGE[r.stage].name}
             <b>${fmt.esc(r.name)}</b></span>`).join('')
        : `<b>最近 ${back} 個交易日沒有族群換階段</b><span class="muted">代表輪動很慢，主流還是同一批</span>`;
      if (mv) $$('.mv', mv).forEach(e => e.onclick = () => { location.hash = '#industry/group/' + e.dataset.gid; });
    }

    /* 2026-09-18（Andy 圖五）：「當點擊族群會拉長清單，看到對應股票，
       若清單太長記得不要延伸原本格式，以拉Bar 方式呈現」。
       ① 以前四格各自只列 12 個（小圖 4 個）再寫一句「還有 N 個」，其餘看不到 ——
          改成全部列出來，格子本身給固定高度＋自己的捲軸（CSS .stage ul），
          四格因此永遠一樣高，也不會把版面撐長。
       ② 點族群不再跳頁，改成在那一列底下原地插一列成分股膠囊，再點一次收合；
          真的要進族群頁的話，展開的那一列右邊有「進族群頁 →」。*/
    board.innerHTML = STAGE_ORDER.map(k => {
      const list = rows.filter(r => r.stage === k);
      const s = STAGE[k];
      return `<div class="stage" style="--c:${s.color}">
        <div class="sh"><b style="color:${s.color}">${s.name}</b><span class="n">${list.length}</span></div>
        <div class="sd">${s.sub}<br><em>${s.act}</em></div>
        <ul>${list.map(rotItem).join('') || '<li class="none">這個階段目前沒有族群</li>'}</ul></div>`;
    }).join('');
    $$('li[data-gid]', board).forEach(li => li.onclick = () => toggleRotMembers(li));
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

  /* 族群估值：單看本益比高低沒有用（IC 設計本來就比航運貴）。
     要看的是「貴不貴」× 「錢有沒有在進來」——
     左上（便宜而且資金流入）才是這張儀表板真正想找的地方，右下（貴又在流出）是該閃的。 */
  function renderGval(gval, rot, gt) {
    if (!gval || !gval.length) return empty('gval');
    const rotMap = {}; (rot || []).forEach(r => { rotMap[r.group_id] = r.rotation; });
    const shareMap = {}; (gt || []).forEach(g => { shareMap[g.group_id] = g.turnover_share; });
    const rows = gval.filter(g => g.metric === 'pe' && g.group_median && !g.group_id.startsWith('ind_')
      && rotMap[g.group_id] != null).map(g => ({ ...g, rot: rotMap[g.group_id], share: shareMap[g.group_id] || 0 }));
    if (rows.length < 3) return empty('gval', '族群估值需要更多有本益比的族群，財報還在回補');
    const pes = rows.map(r => r.group_median);
    const mid = pes.slice().sort((a, b) => a - b)[Math.floor(pes.length / 2)];
    const maxShare = Math.max(...rows.map(r => r.share), 1);
    const xs = [Math.min(...pes) * .9, Math.max(...pes) * 1.06];
    const ys = rows.map(r => r.rot); const yr = Math.max(...ys.map(Math.abs), .5) * 1.25;
    const gvHost = $('#gval');
    const gvClamp = (p) => {
      const W = (gvHost && gvHost.clientWidth) || 300, H = (gvHost && gvHost.clientHeight) || 250, L = p.labelRect;
      let dx = 0, dy = 0;
      if (L.x + L.width > W - 3) dx = (W - 3) - (L.x + L.width);
      if (L.x + dx < 3) dx = 3 - L.x;
      if (L.y + L.height > H - 3) dy = (H - 3) - (L.y + L.height);
      if (L.y + dy < 3) dy = 3 - L.y;
      return { dx, dy, hideOverlap: true };
    };
    const c = chart('gval', {
      tooltip: { ...tip, formatter: q => `<b>${q.data.nm}</b><br>本益比中位 <b>${fmt.n(q.value[0], 1)}</b>（n=${q.data.n}，全市場中位 ${fmt.n(mid, 1)}）<br>資金流向 <span style="color:${upDown(q.value[1])}">${q.value[1] > 0 ? '流入 +' : '流出 '}${fmt.n(q.value[1], 2)} pp</span><br>成交值佔比 ${fmt.n(q.data.share, 1)}%<br><small>點一下看成分股</small>` },
      /* ★ 2026-09-20（Andy 截圖：左上角「便宜 × 資金流入」跟「資金流入」糊成一團）。
         量出來的根因有兩個，都是「用百分比定位 + 不知道旁邊有誰」：
           1. y 軸名稱預設落在軸的最上端，正好就是左上角那個象限標籤的位置；
           2. 四個象限標籤用 left:'13%' / bottom:40 定位，容器一窄就壓到 x 軸刻度
              （1440px 量到「便宜 × 沒人要」和「-1.2」重疊 10×10px）。
         改法：y 軸名稱轉成直的貼在最左邊（那一帶本來就空著）、
         x 軸名稱拿掉（四個象限標籤已經把「左便宜右貴」講完了，留著只是再壓一次），
         四個象限標籤改成**依 grid 用 px 算**、固定貼在繪圖區的四個角 ——
         位置不再跟容器寬度成比例，1280 跟 1920 看到的是同一個版面。 */
      grid: { left: 52, right: 18, top: 26, bottom: 30 },
      xAxis: { ...axisStyle, min: +xs[0].toFixed(0), max: +xs[1].toFixed(0), splitLine: { show: false } },
      yAxis: { ...axisStyle, name: '資金流入 ↑', nameLocation: 'middle', nameRotate: 90, nameGap: 38,
        nameTextStyle: { color: CH.ink3, fontSize: 11 },
        min: -yr, max: yr, axisLabel: { formatter: v => v.toFixed(1) }, splitLine: { show: false } },
      graphic: (() => {
        const gL = 52 + 6, gR = 18 + 6, gT = 26 + 2, gB = 30 + 2;
        const f = { fontSize: 11.5, fontWeight: 700 };
        return [
          { type: 'text', left: gL, top: gT, style: { ...f, text: '便宜 × 資金流入', fill: 'rgba(255,77,109,.75)' } },
          { type: 'text', right: gR, top: gT, style: { ...f, text: '貴 × 資金流入', fill: 'rgba(255,180,84,.7)', align: 'right' } },
          { type: 'text', left: gL, bottom: gB, style: { ...f, text: '便宜 × 沒人要', fill: 'rgba(110,126,163,.8)' } },
          { type: 'text', right: gR, bottom: gB, style: { ...f, text: '貴 × 資金流出', fill: 'rgba(46,229,157,.7)', align: 'right' } },
        ];
      })(),
      series: [{ type: 'scatter',
        data: rows.map(r => ({ value: [+r.group_median.toFixed(1), +r.rot.toFixed(2)], gid: r.group_id,
          nm: r.group_name, n: r.group_n, share: r.share,
          symbolSize: Math.max(11, Math.min(34, Math.sqrt(r.share / maxShare) * 34)),
          itemStyle: { color: L.gcolor[r.group_id] || PALETTE[0], opacity: .85, borderColor: CH.panel, borderWidth: 1 },
          /* 靠右邊的族群名字一律寫在點的左邊（1280px 量到「封測」整串凸出容器 2px）。
             label 的位置可以逐筆指定，所以直接讓標籤一律朝畫面中央長，
             不必依賴 labelLayout 把它夾回來。 */
          label: { position: r.group_median > xs[0] + (xs[1] - xs[0]) * .6 ? 'left' : 'right' } })),
        label: { show: true, formatter: q => q.data.nm, position: 'right', color: CH.ink2, fontSize: 11 },
        // 靠右邊那幾個族群的名字會整串長到框外；跟法人連續買超同一套夾回容器內
        labelLayout: gvClamp },
      { type: 'line', data: [], markLine: { silent: true, symbol: 'none',
        lineStyle: { color: hexA(CH.ink3, .55), type: 'dashed' },
        data: [{ xAxis: +mid.toFixed(1) }, { yAxis: 0 }], label: { show: false } } }],
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.gid) location.hash = '#industry/group/' + q.data.gid; });
    /* 族群小 Tip 改成篩選（Andy 2026-09-20，同 filterChips 那一段的理由）。
       散布圖的做法是把沒選到的圓點壓到 12% 透明度、標籤一起壓暗 ——
       抽掉的話就看不出「它在便宜／貴這兩軸上站在哪裡」，那正是這張圖唯一的用途。*/
    const gvPick = chipSel.gval || null;
    if (c && gvPick) {
      c.setOption({ series: [{ data: rows.map(r => ({
        value: [+r.group_median.toFixed(1), +r.rot.toFixed(2)], gid: r.group_id,
        nm: r.group_name, n: r.group_n, share: r.share,
        symbolSize: Math.max(11, Math.min(34, Math.sqrt(r.share / maxShare) * 34)),
        itemStyle: { color: L.gcolor[r.group_id] || PALETTE[0],
          opacity: r.group_id === gvPick ? .95 : .12,
          borderColor: CH.panel, borderWidth: 1 },
        label: { opacity: r.group_id === gvPick ? 1 : .18 } })) }] }, { notMerge: false, lazyUpdate: true });
    }
    filterChips('gval', rows.slice().sort((a, b) => b.rot - a.rot).slice(0, 12)
      .map(r => ({ gid: r.group_id, name: r.group_name })), gvPick, () => renderGval(gval, rot, gt));
  }

  // ---------------------------------------------------------------- 資金流向
  // ================================================================ 資金流向頁
  // Andy 的要求：「需要有趨勢 好比說上週 上上週 上個月等等 可以查到不同時期 資金走向為何」
  //             「右側本益比需要多可篩選功能 全部在一起」「也需要附上說明怎麼觀看」
  // 所以整頁由上方一個期間切換列統一控制「什麼時候」，每張圖都有一顆「怎麼看」。
  const HOW = {
    rank: `<b>這張圖回答：這段時間錢往哪裡跑。</b>
      <ul><li>長條長度＝這個族群的<em>成交值佔比變化</em>（和上一段同樣長度的期間比），單位是百分點 pp。</li>
      <li><em>紅色向右</em>＝資金流進來，<em>綠色向左</em>＝資金退出去。只看金額會被大盤量能帶著走，所以看佔比。</li>
      <li>名字後面的 <em>3 ↑</em> 是成交值排名進步了 3 名；括號是這段期間的族群報酬。</li>
      <li>用法：先看誰在最上面（主流在換人），再去「名次變化」確認是一天的事還是連續好幾週。</li></ul>`,
    bump: `<b>這張圖回答：主流是穩穩的還是一直換人。</b>
      <ul><li>每條線是一個族群，<em>位置越高＝成交值排名越前面</em>（1 名在最上面）。</li>
      <li>線一路往上＝資金連續好幾週往它集中，通常比單週衝上來的更值得跟。</li>
      <li>線上下亂跳＝那一段時間在輪動，沒有明確主流，追高容易兩面挨巴掌。</li>
      <li>滑鼠移上去看每一週的實際佔比；點線上的點可以進該族群。</li></ul>`,
    rot: `<b>這張圖回答：每個族群現在跑到「強弱循環」的哪一段，以及該怎麼辦。</b>
      <ul><li><b>先看那個圓盤（資金輪動時鐘）</b>：圓盤切成四塊，就是循環的四段。
        一顆點是一個族群，<em>點落在哪一塊＝現在在哪一段</em>；點越大＝成交值佔比越高。</li>
      <li>資金照<em>順時針</em>一塊一塊跑：落後（左下）→ 改善（左上）→ 領先（右上）→ 轉弱（右下）→ 回落後。
        點後面那條尾巴是牠這幾天走過的路，尾巴往前拉＝正在往下一段前進，往回縮＝走回頭路。</li>
      <li><em>離圓心越遠＝和大盤差距越大</em>；擠在圓心附近就是跟大盤差不多，沒特色。
        盤面上兩圈虛線由內而外是「偏離程度的一半」與「偏離最大的那個族群」。</li>
      <li>右上角「⤢ 放大」可以放大；放大後才有<em>族群篩選</em>與<em>回放</em>（按 ▶ 會把你拉的那段時間一天一天播出來）。</li>
      <li>族群跟著大盤轉，順序幾乎都是 <em>改善 → 領先 → 轉弱 → 落後 → 再回改善</em>。</li>
      <li><em>改善</em>：還比大盤弱，但動能已經轉強 —— 資金剛進場，這是最早可以布局的一段。</li>
      <li><em>領先</em>：現在的主流。回檔找買點，別追高，因為下一站是轉弱。</li>
      <li><em>轉弱</em>：還是比大盤強，但動能在掉。手上有的先設好停利。</li>
      <li><em>落後</em>：資金還在跑，別急著抄底，等它走到改善再說。</li>
      <li>名字後面的 <em>↑↓</em> 是動能的方向、「強弱」是相對大盤多少（0 就是跟大盤一樣）。</li>
      <li>最上面那條「換階段的族群」才是重點 —— 已經在領先的你早就知道了，<em>剛從落後轉進改善的</em>才是新機會。
        上面的鈕可以改成和 10 天或 20 天前比。</li></ul>`,
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
      <li>每一列都點得進個股頁，族群名稱點得進族群頁。</li></ul>`,
    heat: `<b>這張圖回答：今天的錢集中在哪些族群。</b>
      <ul><li>方塊<em>大小</em>＝這個族群吃掉多少成交值，方塊<em>顏色</em>＝資金在流入（紅）還是流出（綠），
        看的是 5 日佔比減 20 日佔比，不是今天的漲跌。</li>
      <li>所以會出現「紅方塊但今天收綠」——那代表股價在回檔，但錢還在往裡面放。</li>
      <li>上面那排可以只看一條產業鏈，小方塊就會變大、看得清楚；點方塊直接看成分股。</li></ul>`,
    sankey: `<b>這張圖回答：這一天的量最後流進了誰的口袋，以及它比前幾天變多還是變少。</b>
      <ul><li>由左到右：大盤 → 族群 → 當天量最大的代表股。
        <em>圓圈越大、線越粗＝錢越多</em>，小圓點的<em>密度</em>也是同一件事（發得越密＝錢越多）。</li>
      <li><em>族群的位置固定不動</em>，換日期只會改粗細與大小 ——
        所以<b>怎麼用</b>：拖「看哪一天」往回走，盯住<em>同一個位置</em>的那條線，
        它變粗就是錢在往這個族群集中，變細就是在退場；灰掉寫「無資料」的是那天完全沒量。</li>
      <li>大小是跟<em>這 60 天的最大值</em>比，不是跟當天的第一名比 ——
        所以整排一起變細，代表的是大盤量縮，不是族群輪動。</li>
      <li>下面那排族群點一下＝只看它（其餘壓暗），再點一次取消；點名字右邊的 → 才進族群頁。
        圖上點族群看成分股、點個股直接進個股頁。</li></ul>`,
    inst: `<b>這張圖回答：這段時間法人把錢放在哪裡。</b>
      <ul><li>三段堆疊分別是外資、投信、自營，<em>向右＝買超、向左＝賣超</em>（單位張）。</li>
      <li><em>投信</em>的錢比較黏（有作帳壓力、不太會隔天就跑），連續買超的族群參考價值比外資單日大買高。</li>
      <li>跟著上方期間切換一起變；點任一列看成分股。</li></ul>`,
    conc: `<b>這張圖回答：現在是「少數股票撐盤」還是「雨露均霑」。</b>
      <ul><li>線＝前幾大族群吃掉多少成交值，虛線是它的 20 日平均。</li>
      <li><em>往上＝縮圈</em>，行情集中在少數主流，這時候買冷門股很容易不會動。</li>
      <li><em>往下＝擴散</em>，通常是輪動或補漲，這時候主流反而容易休息。</li>
      <li>前 5 大看「主流有多獨」，前 10 大看「主流圈子有多大」；兩條走勢分岔時是換主流。</li></ul>`,
    val: `<b>這張表回答：這些族群現在貴不貴。</b>
      <ul><li>本益比只有<em>同族群</em>比才有意義（IC 設計跟航運的合理倍數本來就差很多），所以有「只看低於族群中位」這個條件。</li>
      <li>左圖橫軸本益比、縱軸 ROE，<em>右下＝貴又賺得少、左上＝便宜又賺得多</em>；圈圈大小是市值。</li>
      <li>本益比用自算 TTM EPS（近四季），虧損的公司沒有本益比，預設已排除。</li>
      <li>條件可以疊加，改任何一個右上角的檔數就會跟著變；點任一列進個股頁。</li></ul>`,
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

  let flowState = { period: 'w0', back: 5, concTop: 5 };
  async function renderFlow() {
    // groups_detail：輪動板點族群要原地展開成分股（Andy 2026-09-18 圖五），這頁也要先載
    const [f3, conc, fund] = await Promise.all([load('flow_v3'), load('concentration'), load('fundamental'), load('groups_detail')]);
    wireHowto($('#v-flow'));

    /* ★ 2026-09-20（Andy 拍板「合併：只留拉 Bar」）
       原本這裡會依 f3.periods 畫一列期間鈕（本週／上週／…／近三月），
       而排行與法人的拉 Bar 又各自有一個 0＝「跟著上方期間走」——
       **同一頁兩套選時間的方式，互相抵觸**，使用者看不出現在到底在看哪一段。
       現在時間全部由每張圖自己的拉 Bar 決定，兩支拉 Bar 的下限也從 0 改成 1
       （0 已經沒有意義了）。日期範圍寫在各自的副標裡，資訊沒有消失。
       f3.periods 後端照樣產出，之後若要做「快速跳到本月／近三月」再接回來就好。 */
    let instDays = null, rankDays = null;
    const DEFAULT_DAYS = 20;   // 約一個月的交易日；以前 0（跟著上方期間）的替代預設值
    const drawPeriod = () => {
      drawRankDays(rankDays ? Math.max(1, +rankDays.value || DEFAULT_DAYS) : DEFAULT_DAYS);
      drawInstDays(instDays ? Math.max(1, +instDays.value || DEFAULT_DAYS) : DEFAULT_DAYS);
    };
    /* 圖四（Andy 2026-09-18：「資金流向排行需要跟資金輪動一樣以拉Bar 形式呈現，
       並且一樣的設計，也是可以選時間週期拉Bar 1-30 天」）。
       0 保留成「跟著上方期間走」，跟 I1 同一套語彙。
       比較基準是「再往前同樣長度的一段」，所以後端 share_daily 給 60 天（拉滿 30 天時剛好夠）。*/
    const drawRankDays = (n) => {
      const src = f3 && f3.share_daily;
      if (!src || !src.dates || !src.dates.length) {
        return empty('rankFlow', '逐日佔比資料還沒產出（下一輪盤後管線就會有）');
      }
      const D2 = src.dates, N = D2.length;   // 不要叫 L —— 外層的 L 是連結工具（L.group/L.stock）
      const k = Math.min(n, N);
      const curFrom = N - k, prevFrom = Math.max(0, N - 2 * k), prevTo = curFrom;
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
        share: avg(g.share, curFrom, N),
        share_prev: prevTo > prevFrom ? avg(g.share, prevFrom, prevTo) : null,
        turnover: sum(g.turnover, curFrom, N),
        ret: compound(g.chg, curFrom, N),
      })).filter(g => g.share != null);
      gs.forEach(g => { g.share_chg = g.share_prev == null ? null : g.share - g.share_prev; });
      // 名次：這一段與上一段各自按佔比排一次，才算得出 rank_chg
      const rankOf = (key) => { const ord = gs.filter(g => g[key] != null).slice()
        .sort((a, b) => b[key] - a[key]); const m = {}; ord.forEach((g, i) => { m[g.group_id] = i + 1; }); return m; };
      const rc = rankOf('share'), rp = rankOf('share_prev');
      gs.forEach(g => { g.rank = rc[g.group_id] || null; g.rank_prev = rp[g.group_id] || null;
        g.rank_chg = (g.rank && g.rank_prev) ? g.rank_prev - g.rank : 0; });
      const from = D2[curFrom], to = D2[N - 1];
      /* ★ 2026-09-20：期間卡拿掉之後 #periodNote 不存在了，
         所以日期範圍與比較基準改寫進排行自己的副標 —— 使用者仍然看得到
         「現在這張圖是哪一段、跟誰比」，資訊沒有因為拿掉那張卡而消失。 */
      $('#rankSub').textContent = `${from} ～ ${to}（${k} 個交易日）`
        + (prevTo > prevFrom ? `　·　和前 ${prevTo - prevFrom} 個交易日相比` : '　·　沒有可比的上一段');
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
    rotAllGroups = rotRows(f3 && f3.rrg, flowState.back)
      .map(r => ({ gid: r.gid, name: r.name }));
    /* C4（Andy 2026-09-20：「資金流向排行、輪動時鐘，改用圖一這樣方式呈現，
       也可以篩選想要的股票」）—— 圖一指的是漲跌分佈那張卡的篩選列。
       這裡把同一套語彙搬過來，`rotFilter` 是排行與時鐘**共用**的那一份選擇。*/
    const drawRot = (frame) => {
      renderRotation(f3 && f3.rrg, flowState.back,
        { board: 'rotBoard', cycle: 'rotCycle', move: 'rotMove', clock: 'rotClock',
          pick: rotPickSet(), frame: frame || 0,
          // 軌跡固定畫滿 30 天：拉Bar 現在是「看哪一天」，不再是「畫多長」（A4 第 7 條）
          span: ROT_SPAN, trail: ROT.trail });
      // 排行選了誰，時鐘就跟著只亮誰（圖四點長條的連動）
      if (rankSel) highlightClock(rankSel);
    };
    rotRedraw = () => { drawRot(rotFrame); drawPeriod(); };
    wireRotFilter(f3);
    /* 圖二「需要補充圓心到圓外 差異為何」：圖下方固定寫一行，不要讓使用者去猜。*/
    const note = $('#rotCenterNote');
    if (note) {
      /* A4 第 4 條（Andy：「補充說明圓心到圓圈邊緣代表什麼」）。
         ★ 只解釋座標等於沒寫 —— 最後一句一定要講「所以我該怎麼用」。*/
      note.textContent = '圓心＝跟大盤走得一模一樣；越往外＝和大盤差得越多，'
        + '顏色也跟著越深（A4：越外圈顏色越深）。'
        + '兩圈虛線由內而外分別是「今天最大偏離的一半」與「偏離最大的那個族群」，'
        + '所以最外圈那一圈＝今天全場跟大盤差最多的那個族群，其他人都在它裡面；'
        + '往回刷時間軸時尺度不變，所以看得出那一天大家離大盤更近還是更遠。'
        + '資金照順時針一段一段跑：落後 → 改善 → 領先 → 轉弱 → 再回落後。'
        + '　怎麼用：先看外圈（差距大、值得追）再看它在哪一段 ——'
        + '「改善」外圈是剛起漲的候選、「領先」外圈是還在強的主流、'
        + '「轉弱」外圈是該準備減碼的，圓心附近的族群跟大盤沒兩樣，先不用花時間。';
    }
    /* 放大（已拍板：拉Bar／篩選／播放都放在放大視窗裡，卡片上只留一顆「放大」）。
       重用既有的 openZoom()，所以 Esc、點背景關閉、關閉時 dispose 都是現成的。*/
    const zb = $('#rotZoomBtn');
    if (zb) zb.onclick = () => openRotZoom(f3 && f3.rrg, flowState.back);
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

       ★ 值同時餵給輪動階段看板的「和 N 天前比」（flowState.back）——
         兩件事的方向一致（都是「把時間往回拉 N 天」），所以共用同一個值不會打架：
         時鐘回答「N 天前大家在哪」，看板回答「這 N 天誰換了階段」。*/
    rotBackBar = playBar('rotBack', { min: ROT_MIN_BACK, max: 30, value: flowState.back,
      key: 'tw.rot.back', dir: -1, frame: 820,
      label: '看哪一天', fmt: (v) => v + ' 天前',
      onChange: (v) => { flowState.back = v; rotFrame = v; drawRot(v); } });
    rotFrame = rotBackBar ? rotBackBar.value : ROT_MIN_BACK;
    flowState.back = rotFrame;
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
    /* 圖四：天數拉 Bar 現在就是這一頁唯一的時間控制。
       ★ 2026-09-20（Andy：「圖三資金流向移除播放功能」）：playBar → rangeBar，
         ＋ − ▶ 三顆鈕拿掉，天數還是可以拖。
       ★ 2026-09-20（Andy 拍板「合併：只留拉 Bar」）：min 0 → 1、預設 20。*/
    rankDays = rangeBar('rankDays', { min: 1, max: 30, value: DEFAULT_DAYS, key: 'tw.rank.days',
      label: '最近', fmt: (v) => v + ' 天',
      onChange: () => drawPeriod() });
    drawPeriod();

    /* 圖六：改吃獨立檔 sankey_daily（60 天），配一支「看哪一天」的拉 Bar。
       這份檔案只有這一頁會載，所以在這裡才 load。
       ★ 2026-09-20：播放鈕拿掉（rangeBar），但「看哪一天」保留 ——
         族群固定之後，拖這支才看得出同一個族群的錢變多還是變少，那是圖六現在的主要用途。*/
    load('sankey_daily', { fallback: { dates: [], groups: [], leaves: {} } }).then(sd => {
      const n = (sd && sd.dates && sd.dates.length) || 0;
      renderSankey(sd, n ? n - 1 : 0);
      if (n > 1) {
        rangeBar('sankeyDays', { min: 0, max: n - 1, value: n - 1, key: 'tw.sankey.day',
          label: '看哪一天', fmt: (v) => (v >= n - 1 ? '最新' : sd.dates[v]),
          onChange: (v) => renderSankey(sd, v, chipSel.sankey || null) });
      }
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
    renderVal(fund);
    // 資金流向頁的六張圖不加滾輪縮放（Andy 09-13）；圖本身已經用足卡片寬度
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
    if (!gs.length) return empty('rankFlow', p.prev_from ? '這個期間沒有可比的族群' : '沒有上一段期間可以比，換一個期間看看');
    const up = gs.slice().sort((a, b) => b.share_chg - a.share_chg).slice(0, 9);
    const down = gs.slice().sort((a, b) => a.share_chg - b.share_chg).slice(0, 6).reverse();
    const rows = up.concat(down.filter(d => !up.some(u => u.group_id === d.group_id)));
    rows.sort((a, b) => a.share_chg - b.share_chg);      // 由下往上＝由小到大，最會吸金的在最上面
    const label = (g) => {
      const arrow = g.rank_chg > 0 ? ` ${g.rank_chg}↑` : g.rank_chg < 0 ? ` ${-g.rank_chg}↓` : '';
      return `${g.group_name}${arrow}`;
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
      grid: { left: 132, right: 96, top: 12, bottom: 38 },
      xAxis: { ...axisStyle, name: '佔比變化 (pp)', nameLocation: 'middle', nameGap: 22, nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3, hideOverlap: true } },
      yAxis: { ...axisStyle, type: 'category', data: rows.map(label), axisLabel: { color: CH.ink2, fontSize: 12.5 } },
      series: [{
        type: 'bar', barWidth: 15,
        data: rows.map(g => ({ value: +g.share_chg.toFixed(3), gid: g.group_id,
          itemStyle: { color: chgColor(g.share_chg, 1.5), borderRadius: g.share_chg >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
        label: { show: true, position: 'right', color: CH.ink2, fontSize: 11.5, fontFamily: 'JetBrains Mono',
          formatter: (q) => { const g = rows[q.dataIndex]; return `${g.share_chg > 0 ? '+' : ''}${g.share_chg.toFixed(2)}　${fmt.pct(g.ret, 1)}`; } },
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
      if (rankSel === gid) { rankSel = null; const bx = $('#rankPanel'); if (bx) bx.hidden = true; }
      else {
        rankSel = gid;
        heatPanel('rankPanel', gid, g.group_name,
          `佔比 ${fmt.n(g.share, 2)}%　·　變化 ${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp　·　期間報酬 ${fmt.pct(g.ret, 1)}`,
          { scroll: false });   // 面板就在圖正下方，再捲一次會把圖推出畫面
      }
      highlightClock(rankSel);
    });
    lastRankRows = rows;
    // N2：跟輪動時鐘用同一份名單、同一個選取狀態
    groupChips('rankFlow', (rotAllGroups || rows.map(g => ({ gid: g.group_id, name: g.group_name }))), rankSel);
  }

  /* 輪動時鐘的放大視窗（Andy 2026-09-18 圖二：「右上角 可以放大這圖」）。
     已拍板：拉Bar／篩選／播放通通放在這裡，卡片上只留一顆「放大」——
     卡片本來就只有半個版面，再塞三排控制項就沒有圖了。*/
  function openRotZoom(rrg, back0) {
    const rows0 = rotRows(rrg, back0);
    if (!rows0.length) return;
    openZoom('輪動時鐘', (body, chipBox, close) => {
      const tools = $('#zoomTools'); if (tools) tools.innerHTML = '<div id="rotZoomBack"></div><div id="rotZoomPlay"></div>';
      const pick = new Set();
      let back = back0, frame = 0;
      const draw = () => {
        renderRotClock(rows0, back, 'zoomBody', false, { pick, frame });
        // 篩選晶片：點一下只看那個族群，再點取消；沒選＝全部
        chipBox.innerHTML = `<button data-g="" class="${pick.size ? '' : 'on'}">全部</button>`
          + rows0.slice(0, 16).map(r =>
            `<button data-g="${r.gid}" class="${pick.has(r.gid) ? 'on' : ''}">${fmt.esc(r.name)}</button>`).join('');
        $$('button', chipBox).forEach(b => b.onclick = () => {
          const g = b.dataset.g;
          if (!g) pick.clear(); else if (pick.has(g)) pick.delete(g); else pick.add(g);
          draw();
        });
      };
      draw();
      // 「和幾天前比」：跟卡片上那支同一個 localStorage key，兩邊一致
      /* 放大視窗裡這支保留原本的語意＝**軌跡要畫幾天**（卡片上那支已經改成「看哪一天」）。
         兩支分工：這裡決定「看多長的一段路」，下面那支回放決定「停在哪一天」。
         2026-09-20：min 5 → 1，和卡片上的範圍一致（A4 第 3 條）。*/
      rangeBar('rotZoomBack', { min: 1, max: 30, value: back, key: 'tw.rot.back',
        label: '軌跡畫幾天', fmt: (v) => v + ' 天',
        onChange: (v) => { back = v; draw(); } });
      /* 播放：Andy「點擊後可以播放我拉Bar 選定的時間」。
         幀＝「第 N 天前」，所以要從舊播到新 —— 拉Bar 由大到小跑完才是「時間往前走」。
         playBar 本身只會由小往大遞增，所以這裡把值反過來解讀：值 v → frame = back - v。*/
      /* ★ 上限寫死 30，不要用 `back` —— back 是軌跡長度，被拉到 1 的時候
         回放就只剩兩格可以播，看起來像播放壞了（2026-09-20 改成兩支分工之後才會發生）。*/
      const PLAY_MAX = 30;
      playBar('rotZoomPlay', { min: 0, max: PLAY_MAX, value: PLAY_MAX, frame: 700,
        label: '回放', fmt: (v) => (v >= PLAY_MAX ? '現在' : (PLAY_MAX - v) + ' 天前'),
        onChange: (v) => { frame = Math.max(0, PLAY_MAX - v); draw(); } });
      if (close) { /* close 由 openZoom 提供，這裡不另外包裝 */ }
    });
  }

  /* N2（Andy 2026-09-19 圖一：「兩邊族群對不上，有些為何篩選不到」）。
     根因：排行卡下面那排晶片列的是**排行圖上畫出來的 15 檔**（依佔比變化挑的），
     時鐘卡下面那排列的是**成交值前 16 大**，兩邊挑法不同、名單當然對不上；
     而且那些晶片是 `<a href="#industry/group/…">`，點下去是**跳頁**不是篩選 ——
     所以他說「有些篩選不到」。

     改法：兩張圖共用同一份名單（輪動資料裡的全部族群，依成交值佔比排序），
     而且晶片改成**篩選鈕**：點一下同時「排行展開那個族群的成分股」＋
     「時鐘只亮那個族群」，再點一次取消。要進族群頁的話晶片右邊有個 `→`。*/
  function groupChips(afterId, list, sel) {
    const el = document.getElementById(afterId); if (!el) return;
    const at = el.closest('.zwrap') || el;
    let row = at.nextElementSibling;
    if (!row || !row.classList.contains('linkrow')) {
      row = document.createElement('div'); row.className = 'linkrow';
      at.parentNode.insertBefore(row, at.nextSibling);
    }
    row.classList.add('gchips');
    // data-sync="n2"：排行與時鐘這兩排是「同一個選取」，pickGroup 只同步這兩排。
    // 2026-09-20 資金去向與族群×法人也長出自己的晶片列（filterChips），
    // 沒有這個標記的話它們會被 pickGroup 一起點亮，但圖上其實沒有被篩選。
    row.dataset.sync = 'n2';
    /* 2026-09-20（C4）：這一排和上面那排篩選列**不是同一件事**，所以要講清楚，
       不然兩排長得很像的東西擺在一起，使用者會不知道該按哪一個：
         上面那排「族群篩選」＝多選過濾（圖上只留這幾個）
         這一排點名字＝單選聚焦（排行原地展開成分股、時鐘只亮它） */
    row.innerHTML = '<span class="muted" style="font-size:11.5px">點名字＝聚焦並展開成分股（多選過濾請用上面的「族群篩選」）</span>'
      + list.map(g =>
      `<span class="gchip${sel === g.gid ? ' on' : ''}" data-g="${g.gid}" style="--c:${L.gcolor[g.gid] || CH.cyan}">
         <button class="pick" title="只看這個族群">${fmt.esc(g.name)}</button>
         <a class="go" href="#industry/group/${g.gid}" title="進族群頁">→</a></span>`).join('');
    $$('.gchip .pick', row).forEach(b => b.onclick = () => {
      const gid = b.parentNode.dataset.g;
      pickGroup(rankSel === gid ? null : gid);
    });
  }

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

  /* 選一個族群（null＝取消）：排行原地展開成分股、時鐘只亮它、兩排晶片同步。*/
  function pickGroup(gid) {
    rankSel = gid;
    const box = $('#rankPanel');
    if (!gid) { if (box) box.hidden = true; }
    else {
      const g = (lastRankRows || []).find(x => x.group_id === gid);
      heatPanel('rankPanel', gid, g && g.group_name,
        g ? `佔比 ${fmt.n(g.share, 2)}%　·　變化 ${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp　·　期間報酬 ${fmt.pct(g.ret, 1)}`
          : '', { scroll: false });
    }
    highlightClock(gid);
    // 兩排晶片一起換狀態（這就是「兩邊對不上」的解法：同一份名單、同一個選取）
    $$('.gchips[data-sync="n2"] .gchip').forEach(c => c.classList.toggle('on', c.dataset.g === gid));
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
  const ROT_MIN_BACK = 1;          // A4 第 3 條：前一天 ～ 前三十天
  const ROT = { chain: '', groups: null, stocks: null, trail: true, topOnly: false };
  let rotFrame = ROT_MIN_BACK;     // 時間軸刷到第幾天前
  let rotBackBar = null;           // #rotBack 那支 playBar（播放／＋／−）
  let rotRedraw = () => {};        // 篩選變了就重畫兩張圖
  let rotGroupMeta = {};           // gid → {name, chain}
  let rotStockIndex = [];          // [{code, name, gid, gname}]，個股篩選用

  /* 目前生效的族群集合（null／空＝全部）。族群勾選與個股勾選是 **聯集**：
     兩邊都有勾就兩邊都留，因為使用者的意思是「這些我都想看」，不是「同時滿足」。*/
  function rotPickSet() {
    const out = new Set();
    if (ROT.groups) ROT.groups.forEach(g => out.add(g));
    if (ROT.stocks) ROT.stocks.forEach(code => {
      const g = rotStockIndex.find(x => x.code === code);
      if (g) out.add(g.gid);
    });
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

  /* 篩選列本體。結構刻意和 `wireDistFilter()` 一模一樣（seg ＋ 勾選 ＋ 兩顆展開鈕），
     展開的複選格也沿用 `.chainchips` 與「max-height ＋ overflow:auto」——
     族群有 36 個、個股上千檔，不給高度上限會把整張卡片撐爛。*/
  function wireRotFilter(f3) {
    const boxes = $$('.rotfilter');
    if (!boxes.length) return;
    rotGroupMeta = {};
    ((f3 && f3.rrg && f3.rrg.points) || []).forEach(p => {
      rotGroupMeta[p.group_id] = { name: p.group_name, chain: p.chain || '' };
    });
    // 個股索引：groups_detail 是 gid → members，這頁進來之前已經 load 過
    const gd = D.groups_detail || {};
    rotStockIndex = [];
    (rotAllGroups || []).forEach(r => {
      ((gd[r.gid] || {}).members || []).forEach(m => {
        rotStockIndex.push({ code: String(m.code), name: m.name || String(m.code), gid: r.gid, gname: r.name });
      });
    });
    const chains = [...new Set((rotAllGroups || []).map(r => (rotGroupMeta[r.gid] || {}).chain).filter(Boolean))];
    const nG = ROT.groups ? ROT.groups.size : 0, nS = ROT.stocks ? ROT.stocks.size : 0;
    const picked = rotPickSet().size;
    /* ★ 兩張卡各有一排（排行一排、時鐘一排），但**吃同一份狀態**，
       所以裡面的控制項一律用 class 不用 id —— 同一個 id 出現兩次的話
       `document.getElementById` 只會抓到第一個，另一排就變成按了沒反應。*/
    boxes.forEach(box => {
      box.innerHTML = `<div class="seg tiny rotchain">
          <button data-c="" class="${ROT.chain ? '' : 'on'}">全部</button>
          ${chains.map(c => `<button data-c="${fmt.esc(c)}" class="${ROT.chain === c ? 'on' : ''}">${fmt.esc(CHAIN_NAME[c] || c)}</button>`).join('')}
        </div>
        <label class="rotchk"><input type="checkbox" class="rot-top10" ${ROT.topOnly ? 'checked' : ''}>只看前 10 大</label>
        <button class="btn small rot-gbtn">族群篩選${nG ? `（${nG}）` : ''}</button>
        <button class="btn small rot-sbtn">個股篩選${nS ? `（${nS}）` : ''}</button>
        ${(nG || nS || ROT.chain || ROT.topOnly) ? '<button class="btn small rot-clear">清除篩選</button>' : ''}
        <span class="muted rot-note">${picked ? `排行與時鐘都只看這 ${picked} 個族群` : '排行與時鐘顯示全部族群'}</span>`;
      $$('.rotchain button', box).forEach(b => b.onclick = () => {
        ROT.chain = b.dataset.c; wireRotFilter(f3); rotRedraw();
      });
      const t10 = box.querySelector('.rot-top10');
      if (t10) t10.onchange = () => { ROT.topOnly = t10.checked; wireRotFilter(f3); rotRedraw(); };
      const clr = box.querySelector('.rot-clear');
      if (clr) clr.onclick = () => {
        ROT.chain = ''; ROT.groups = null; ROT.stocks = null; ROT.topOnly = false;
        saveRotSel(); wireRotFilter(f3); rotRedraw();
      };
      /* 展開的複選格插在這一排的正下方（和 wireDistFilter 的 #distGroups 一樣），
         再點同一顆鈕就收起來。高度上限＋自己的捲軸：族群 36 個、個股上千檔。*/
      const panel = (kind, fill) => {
        let w = box.nextElementSibling;
        if (!w || !w.classList.contains('rotpick')) {
          w = document.createElement('div'); w.className = 'chainchips rotpick';
          box.parentNode.insertBefore(w, box.nextSibling);
        }
        if (w.dataset.open === kind) { w.dataset.open = ''; w.innerHTML = ''; w.hidden = true; return; }
        w.dataset.open = kind; w.hidden = false; fill(w);
      };
      const gb = box.querySelector('.rot-gbtn');
      if (gb) gb.onclick = () => panel('groups', (w) => {
        w.innerHTML = '<button data-g="">全部</button>'
          + (rotAllGroups || []).map(r => `<button data-g="${fmt.esc(r.gid)}"
               class="${ROT.groups && ROT.groups.has(r.gid) ? 'on' : ''}">${fmt.esc(r.name)}</button>`).join('');
        $$('button', w).forEach(b => b.onclick = () => {
          const g = b.dataset.g;
          if (!g) ROT.groups = null;
          else {
            ROT.groups = ROT.groups || new Set();
            if (ROT.groups.has(g)) ROT.groups.delete(g); else ROT.groups.add(g);
            if (!ROT.groups.size) ROT.groups = null;
          }
          $$('button', w).forEach(x => x.classList.toggle('on', !!ROT.groups && ROT.groups.has(x.dataset.g)));
          saveRotSel(); wireRotFilter(f3); rotRedraw();
        });
      });
      const sb = box.querySelector('.rot-sbtn');
      if (sb) sb.onclick = () => panel('stocks', (w) => {
        /* 個股上千檔，一次全列出來沒有人找得到，所以給一個搜尋框（打代號或名字都行）；
           沒打字時只列「每個族群成交值最大的那一檔」當入口。
           ★ 勾個股＝把**它所屬的族群**留在圖上（這兩張圖的單位是族群，不是個股）。*/
        w.innerHTML = '<input class="rotsearch" placeholder="打代號或名字找個股，例如 2330 或 台積電">'
          + '<div class="rotstocklist"></div>';
        const list = w.querySelector('.rotstocklist');
        const draw = (kw) => {
          const q = String(kw || '').trim();
          const pool = q ? rotStockIndex.filter(x => x.code.indexOf(q) >= 0 || x.name.indexOf(q) >= 0
              || x.gname.indexOf(q) >= 0).slice(0, 120)
            : (rotAllGroups || []).map(r => rotStockIndex.find(x => x.gid === r.gid)).filter(Boolean);
          list.innerHTML = '<button data-s="">全部</button>'
            + pool.map(x => `<button data-s="${fmt.esc(x.code)}" title="屬於「${fmt.esc(x.gname)}」"
                 class="${ROT.stocks && ROT.stocks.has(x.code) ? 'on' : ''}">${fmt.esc(x.name)} ${fmt.esc(x.code)}</button>`).join('');
          $$('button', list).forEach(b => b.onclick = () => {
            const c = b.dataset.s;
            if (!c) ROT.stocks = null;
            else {
              ROT.stocks = ROT.stocks || new Set();
              if (ROT.stocks.has(c)) ROT.stocks.delete(c); else ROT.stocks.add(c);
              if (!ROT.stocks.size) ROT.stocks = null;
            }
            $$('button', list).forEach(x => x.classList.toggle('on', !!ROT.stocks && ROT.stocks.has(x.dataset.s)));
            saveRotSel(); wireRotFilter(f3); rotRedraw();
          });
        };
        const q = w.querySelector('.rotsearch');
        if (q) q.oninput = () => draw(q.value);
        draw('');
      });
    });
  }

  /* 選擇要記住（Andy 的驗收會檢查 localStorage 真的寫進去）。
     只存「使用者自己勾的」兩組，seg 與前 10 大是一眼就看得出來的狀態，不必記。*/
  function saveRotSel() {
    try {
      localStorage.setItem('tw.rot.filter', JSON.stringify({
        groups: ROT.groups ? [...ROT.groups] : null,
        stocks: ROT.stocks ? [...ROT.stocks] : null,
      }));
    } catch (e) { /* 私密視窗 */ }
  }
  (function loadRotSel() {
    try {
      const o = JSON.parse(localStorage.getItem('tw.rot.filter') || 'null');
      if (o && o.groups && o.groups.length) ROT.groups = new Set(o.groups);
      if (o && o.stocks && o.stocks.length) ROT.stocks = new Set(o.stocks);
    } catch (e) { /* 忽略壞掉的值 */ }
  })();

  /* A4 第 7 條的後半：「新增軌跡是可以開啟關閉」。
     關掉之後線還在（series 數量不變，highlightClock 認 gid 的那段就不用改），
     只是資料清空 —— 所以「軌跡有沒有關掉」量的是**點數**，不是 series 數。*/
  function wireRotTrailToggle(redraw) {
    const box = $('#rotTools'); if (!box) return;
    box.innerHTML = '<label class="rotchk"><input type="checkbox" id="rotTrail"'
      + (ROT.trail ? ' checked' : '') + '>顯示軌跡</label>'
      + '<span class="muted">大圈＝你選的那一天；線＝這 30 天走過的路</span>';
    const c = $('#rotTrail', box);
    if (c) c.onchange = () => { ROT.trail = c.checked; redraw(); };
  }

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
  function highlightClock(gid) {
    const el = document.getElementById('rotClock');
    const c = el && window.echarts && echarts.getInstanceByDom(el);
    if (!c) return;
    const o = c.getOption(); if (!o || !o.series) return;
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
  const SANKEY_DOT_MAX = 90;
  const SANKEY_TRAVEL = 2600;          // 一顆點從大盤走到族群要幾毫秒（固定，所以「頻率」＝點數）
  let sankeyFx = null;
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
      if (!el.isConnected) { stop(); return; }
      // 換到別的分頁時容器還在 DOM 裡、只是被藏起來（offsetParent 會是 null）：
      // 這時候什麼都不畫，但迴圈留著，回到這一頁就自己接上
      if (el.offsetParent === null) { raf = requestAnimationFrame(step); return; }
      const dpr = sizeTo();
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, cv.width, cv.height);
      dots.length = 0;
      for (const f of flows) {
        for (let i = 0; i < f.n; i++) {
          // 同一條線上的點等距排開：資金越多 → 點越多 → 單位時間通過的顆數越多＝頻率越高
          const t = ((ts / SANKEY_TRAVEL) + f.phase + i / f.n) % 1;
          const p = bez(f.a, f.b, t);
          dots.push({ x: Math.round(p[0]), y: Math.round(p[1]), r: f.size, gid: f.gid });
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
    return { stop, dots, running: () => !!raf };
  }

  /* 資金去向（Andy 2026-09-18 圖六）：
       「改成水平並且全部都以點跟線呈現，金資越多的 顏色越深也越粗，
         並且一樣都具備相資金輪動的拉Bar 可以觀察並搭配播放功能，
         白色頁面時 顏色不要太深 親和一點」

     所以整張圖從桑基改成**水平的樹**：大盤 → 族群 → 代表股，全部是點跟線。
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

     第三個參數 pick＝只看某一個族群（族群晶片點下去會傳進來）：
     其餘的整棵子樹壓暗，不是整個拿掉 —— 拿掉位置又會變。*/
  const SANKEY_KIDS = 3;
  // 代表股顯示名：後端給的 name 如果是空的或字串 "nan"，一律退回全市場索引的簡稱、再退回代號
  const leafName = (x) => { const n = String((x && x.name) || '').trim();
    return (!n || n.toLowerCase() === 'nan') ? (L.cname[x.code] || x.code) : n; };
  function renderSankey(sd, idx, pick) {
    stopSankeyFlow();
    const el = $('#sankey'); if (!el) return;
    if (!sd || !sd.dates || !sd.dates.length) return empty('sankey', '資金去向的逐日資料還沒產出（下一輪盤後管線就會有）');
    const D2 = sd.dates;
    const k = Math.max(0, Math.min(D2.length - 1, idx == null ? D2.length - 1 : idx));
    const day = D2[k];
    const roster = (sd.groups || []);
    if (!roster.length) return empty('sankey', `${day} 這天沒有資料`);
    const gs = roster.map(g => ({ ...g, v: (g.tv || [])[k] }));       // 不過濾、不重排
    const leaves = (sd.leaves || {})[day] || [];
    const total = gs.reduce((s2, g) => s2 + (g.v || 0), 0) || 1;
    // 全期間最大值：換日期時大小才有可比性
    let maxV = 1;
    roster.forEach(g => (g.tv || []).forEach(v => { if (v != null && v > maxV) maxV = v; }));
    const lt = theme() === 'light';
    const HI = lt ? .62 : .95, LO = lt ? .22 : .30;          // 顏色深淺的上下限
    const DIM = 0.14;                                        // 沒量／沒被選中時壓到多暗
    const ratio = (v) => Math.min(1, Math.max(0, (v || 0) / maxV));
    const alpha = (v) => LO + (HI - LO) * ratio(v);
    const size = (v) => 8 + 22 * Math.sqrt(ratio(v));
    const width = (v) => 1 + 7 * ratio(v);
    const pct = (v) => fmt.n((v || 0) / total * 100, 1);

    const byG = {};
    leaves.forEach(x => { (byG[x.gid] = byG[x.gid] || []).push(x); });
    const children = gs.map(g => {
      const col = L.gcolor[g.gid] || CH.cyan;
      const has = g.v != null && g.v > 0;
      const off = pick && pick !== g.gid;                    // 被篩掉的：壓暗但留在原位
      const fade = off ? DIM : 1;
      const kids = (byG[g.gid] || []).slice().sort((a2, b2) => b2.tv - a2.tv)
        .slice(0, SANKEY_KIDS).map(x => ({
          /* 前端這一層也擋一次「nan」。根因在後端（見 pipeline/compute/rrg.py 的註解）已經修掉，
             但使用者的瀏覽器可能還快取著舊的 sankey_daily.json，那一份裡每一檔都叫「nan」。
             寧可顯示代號，也不要讓整排寫 nan。*/
          name: `${leafName(x)} ${x.code}`, value: x.tv, code: x.code, gidOf: g.gid, dim: off,
          symbolSize: Math.max(6, size(x.tv) * .62),
          itemStyle: { color: hexA(col, alpha(x.tv) * .85), borderColor: 'transparent', opacity: fade },
          lineStyle: { color: hexA(col, alpha(x.tv) * .7), width: Math.max(1, width(x.tv) * .7), opacity: fade },
          label: { formatter: `${leafName(x)}`, opacity: fade },
        }));
      // 補到固定格數：看不見的佔位節點，只為了讓縱向空間每天都一樣
      for (let i = kids.length; i < SANKEY_KIDS; i++) {
        kids.push({ name: ` ${g.gid}#${i}`, value: null, placeholder: true,
          symbolSize: 0, itemStyle: { opacity: 0 }, lineStyle: { opacity: 0 }, label: { show: false } });
      }
      return { name: g.name, value: g.v == null ? 0 : g.v, gid: g.gid, children: kids,
        nodata: !has, dim: off,
        symbolSize: has ? size(g.v) : 6,
        itemStyle: { color: hexA(col, has ? alpha(g.v) : DIM), borderColor: 'transparent', opacity: fade },
        lineStyle: { color: hexA(col, (has ? alpha(g.v) : DIM) * .8), width: has ? width(g.v) : 0.8, opacity: fade },
        label: { formatter: has ? `${g.name} ${pct(g.v)}%` : `${g.name} 無資料`,
          opacity: off ? 0.35 : (has ? 1 : 0.55) } };
    });
    const root = { name: '台股成交值', value: total, symbolSize: 26,
      itemStyle: { color: hexA(CH.cyan, lt ? .55 : .9), borderColor: 'transparent' },
      children };

    const sub = $('#sankeySub');
    if (sub) {
      sub.textContent = `${day}：族群固定在原位，只有線的粗細與圓圈大小會變`
        + (pick ? `　·　只看「${L.gname[pick] || pick}」` : '');
    }

    const c = chart('sankey', {
      tooltip: { ...tip, trigger: 'item', triggerOn: 'mousemove',
        formatter: (p) => {
          if (p.data && p.data.placeholder) return '';
          if (p.data && p.data.nodata) return `<b>${p.name}</b><br>${day} 這天沒有量`;
          const v = p.data && p.data.value;
          if (v == null) return p.name;
          return `<b>${p.name}</b><br>成交值 ${fmt.yi(v)}　<b>${pct(v)}%</b>`
            + (p.data.code ? '<br><small>點一下進個股頁</small>'
              : p.data.gid ? '<br><small>點一下看成分股</small>' : '');
        } },
      series: [{
        type: 'tree', orient: 'LR', layout: 'orthogonal', edgeShape: 'curve',
        left: 10, right: 130, top: 14, bottom: 14,
        initialTreeDepth: 2, expandAndCollapse: false, roam: false,
        symbol: 'circle',
        label: { position: 'right', distance: 7, color: CH.ink2, fontSize: 11.5,
          textBorderColor: CH.panel, textBorderWidth: 3, align: 'left' },
        leaves: { label: { position: 'right', distance: 6, fontSize: 11, color: CH.ink3 } },
        emphasis: { focus: 'relative' },
        animationDurationUpdate: 420,
        data: [root],
      }],
    }, { notMerge: true });
    if (c) c.off('click').on('click', p => {
      if (!p.data || p.data.placeholder) return;
      if (p.data.code) goStock(p.data.code);
      else if (p.data.gid) location.hash = '#industry/group/' + p.data.gid;
    });
    /* 族群晶片改成篩選（Andy 2026-09-20：「所有圖表的族群小Tip都需要具備點擊後
       就會在對應圖表上被篩選出去」）。名單也用固定名單，不是只有當天有量的那幾個。*/
    filterChips('sankey', gs.map(g => ({ gid: g.gid, name: g.name })), pick,
      (nx) => renderSankey(sd, k, nx));

    // 小圓點傳輸：等 tree 的版面算完（finished）才讀得到節點座標
    if (c) {
      c.off('finished');
      let armed = true;
      c.on('finished', () => {
        if (!armed) return;              // finished 會重複觸發，只接第一次
        armed = false;
        const pos = sankeyNodePos(c); if (!pos) return;
        const a = pos['台股成交值']; if (!a) return;
        const flows = [];
        gs.forEach(g => {
          const b = pos[g.name]; if (!b) return;
          const r = ratio(g.v);
          if (!(g.v > 0) || (pick && pick !== g.gid)) return;   // 沒量／被篩掉就不發點
          flows.push({ a, b, gid: g.gid,
            // 資金越多 → 同一條線上的點越多 → 單位時間通過的顆數越多＝頻率越高
            n: Math.max(1, Math.min(6, Math.round(1 + 5 * r))),
            size: 1.6 + 3.4 * Math.sqrt(r),
            // 錯開相位，不要整排同時發車。用 gid 的字元和當雜湊 ——
            // 只用長度的話同長度的 gid 會完全同步，看起來像整排一起跳
            phase: ([...g.gid].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 997, 7) % 100) / 100,
            color: hexA(L.gcolor[g.gid] || CH.cyan, lt ? .75 : .95) });
        });
        let budget = SANKEY_DOT_MAX;
        const use = [];
        flows.sort((x, y) => y.size - x.size).forEach(f => { if (budget - f.n >= 0) { budget -= f.n; use.push(f); } });
        stopSankeyFlow();
        sankeyFx = startSankeyFlow(el, use);
      });
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

  // ---- 估值篩選：本益比、股價淨值比、ROE、市值、族群，全部條件放在一起
  const VF = { pe: [null, null], pb: null, roe: null, cap: null, group: '', market: '', below: false, profit: true };
  function renderVal(fund) {
    const all = (fund || []).filter(r => r.pe != null || r.pb != null);
    if (!all.length) { $('#valCount') && ($('#valCount').textContent = ''); empty('valScatter', '估值資料還在回補'); $('#valBody').innerHTML = ''; return; }
    const gsel = $('#vGroup');
    if (gsel && gsel.options.length <= 1) {
      const names = [...new Set(all.map(r => r.group_name).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-TW'));
      gsel.innerHTML = '<option value="">全部族群</option>' + names.map(n => `<option value="${fmt.esc(n)}">${fmt.esc(n)}</option>`).join('');
    }
    const num = (el) => { const v = parseFloat(($(el) || {}).value); return Number.isFinite(v) ? v : null; };
    const apply = () => {
      VF.pe = [num('#vPeLo'), num('#vPeHi')]; VF.pb = num('#vPb'); VF.roe = num('#vRoe'); VF.cap = num('#vCap');
      VF.group = ($('#vGroup') || {}).value || ''; VF.market = ($('#vMarket') || {}).value || '';
      VF.below = !!($('#vBelow') || {}).checked; VF.profit = !!($('#vProfit') || {}).checked;
      const rows = all.filter(r => {
        if (VF.profit && (r.is_loss || r.pe == null)) return false;
        if (VF.group && r.group_name !== VF.group) return false;
        if (VF.market && r.market !== VF.market) return false;
        if (VF.pe[0] != null && !(r.pe != null && r.pe >= VF.pe[0])) return false;
        if (VF.pe[1] != null && !(r.pe != null && r.pe <= VF.pe[1])) return false;
        if (VF.pb != null && !(r.pb != null && r.pb <= VF.pb)) return false;
        if (VF.roe != null && !(r.roe != null && r.roe >= VF.roe)) return false;
        if (VF.cap != null && !(r.market_cap != null && r.market_cap >= VF.cap * 1e8)) return false;
        if (VF.below && !(r.vs_median != null && r.vs_median < 0)) return false;
        return true;
      });
      $('#vCount').textContent = `符合 ${rows.length} 檔（全市場有估值的 ${all.length} 檔）`;
      drawScatter(rows); drawTable(rows);
    };
    const drawScatter = (rows) => {
      const pts = rows.filter(r => r.pe != null && r.roe != null);
      if (!pts.length) return empty('valScatter', '這組條件沒有同時有本益比與 ROE 的股票');
      const caps = pts.map(r => r.market_cap || 0); const maxCap = Math.max(...caps, 1);
      const c = chart('valScatter', {
        tooltip: { ...tip, formatter: q => `<b>${q.data.name} ${q.data.code}</b><br>${fmt.esc(q.data.g || '')}<br>本益比 ${fmt.n(q.value[0], 1)}　ROE ${fmt.n(q.value[1], 1)}%<br>股價淨值比 ${fmt.n(q.data.pb)}　市值 ${fmt.yi(q.data.cap)}<br><small>點一下進個股頁</small>` },
        // top 20→34：y 軸名稱「ROE ↑」預設畫在軸的上方 15px 處，20px 的上緣留不住它（量到 -7px）
        grid: { left: 52, right: 20, top: 34, bottom: 40 },
        xAxis: { ...axisStyle, name: '本益比 →', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, max: Math.min(80, Math.max(...pts.map(r => r.pe))) },
        yAxis: { ...axisStyle, name: 'ROE ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'scatter', data: pts.map(r => ({ value: [r.pe, r.roe], code: r.code, name: r.name, g: r.group_name, pb: r.pb, cap: r.market_cap,
          symbolSize: Math.max(8, Math.min(34, Math.sqrt((r.market_cap || 0) / maxCap) * 34)),
          itemStyle: { color: L.gcolor[r.group_id] || PALETTE[0], opacity: .78, borderColor: CH.panel, borderWidth: 1 } })),
          label: { show: pts.length <= 40, formatter: q => q.data.name, position: 'right', color: CH.ink2, fontSize: 11 }, labelLayout: { hideOverlap: true } }],
      });
      if (c) c.off('click').on('click', q => { if (q.data && q.data.code) goStock(q.data.code); });
    };
    const drawTable = (rows) => {
      const top = rows.slice().sort((a, b) => (a.pe ?? 1e9) - (b.pe ?? 1e9)).slice(0, 80);
      $('#valTable thead').innerHTML = '<tr><th class="l">股票</th><th class="l">族群</th><th>本益比</th><th>族群中位</th><th>淨值比</th><th>ROE</th><th>市值</th></tr>';
      $('#valBody').innerHTML = top.map(r => `<tr data-code="${r.code}">
        <td class="l">${L.stock(r.code, r.name)}</td>
        <td class="l">${r.group_id ? L.group(r.group_id, r.group_name) : fmt.esc(r.group_name || '—')}</td>
        <td class="num">${fmt.n(r.pe, 1)}</td>
        ${(() => {
          /* ★ 2026-09-19：這一欄不能只印 group_median 的數字。
             groups.yaml 的 valuation_metric 允許族群改用別的口徑（生技醫療用 ps 股價營收比，
             金融用 pb_roe），這時 group_median 是**那個口徑**的中位數，不是本益比的中位數。
             原本的寫法把「本益比 12.4」跟「族群中位 2.7（那是 PS 中位）」並排印，
             使用者只會讀成「這檔貴了四倍」—— 實際上它的 PS 比同業低 37%。
             所以非 PE 口徑時要把口徑名稱與本檔的數值一起標出來。 */
          const mt = r.metric || 'pe';
          const col = r.vs_median != null ? upDown(-r.vs_median) : CH.ink3;
          if (r.group_median == null) return `<td class="num" style="color:${CH.ink3}">—</td>`;
          if (mt === 'pe') return `<td class="num" data-metric="pe" style="color:${col}">${fmt.n(r.group_median, 1)}</td>`;
          const MN = { ps: '股價營收比', pb_roe: '股價淨值比', pb: '股價淨值比' }[mt] || mt;
          return `<td class="num" data-metric="${fmt.esc(mt)}" data-mv="${r.metric_value ?? ''}" style="color:${col}"
            title="${fmt.esc(r.group_name || '')}這個族群用${fmt.esc(MN)}比較，不是本益比：本檔 ${fmt.n(r.metric_value, 2)}、族群中位 ${fmt.n(r.group_median, 2)}">${fmt.n(r.group_median, 1)}<small class="muted"> ${fmt.esc(mt.toUpperCase())}</small></td>`;
        })()}
        <td class="num">${fmt.n(r.pb)}</td><td class="num">${r.roe != null ? fmt.n(r.roe, 1) + '%' : '—'}</td>
        <td class="num">${fmt.yi(r.market_cap)}</td></tr>`).join('')
        || '<tr><td colspan="7" class="l muted" style="padding:16px">沒有符合條件的股票，放寬一點試試</td></tr>';
      $$('#valBody tr[data-code]').forEach(tr => tr.onclick = (e) => { if (e.target.closest('a')) return; goStock(tr.dataset.code); });
    };
    ['#vPeLo', '#vPeHi', '#vPb', '#vRoe', '#vCap'].forEach(s => { const el = $(s); if (el) el.oninput = apply; });
    ['#vGroup', '#vMarket'].forEach(s => { const el = $(s); if (el) el.onchange = apply; });
    ['#vBelow', '#vProfit'].forEach(s => { const el = $(s); if (el) el.onchange = apply; });
    const rst = $('#vReset');
    if (rst) rst.onclick = () => {
      ['#vPeLo', '#vPeHi', '#vPb', '#vRoe', '#vCap'].forEach(s => { const el = $(s); if (el) el.value = ''; });
      $('#vGroup').value = ''; $('#vMarket').value = ''; $('#vBelow').checked = false; $('#vProfit').checked = true; apply();
    };
    apply();
  }

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
  // 題材產品圖：零件 ↔ 個股雙向互通。點零件→列出該零件的個股；滑過成員→圖上對應零件同色亮起。
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
      $$('#themeMembers tr', host).forEach(tr => tr.classList.toggle('sel', !!id && (codesOf[id] || []).includes(tr.dataset.code)));
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
    $$('#themeMembers tr', host).forEach(tr => {
      tr.onmouseenter = () => { if (cur) return; const hit = Object.keys(codesOf).find(k => codesOf[k].includes(tr.dataset.code)); nodes.forEach(n => n.classList.toggle('sel', !!hit && n.dataset.part === hit)); };
      tr.onmouseleave = () => { if (!cur) nodes.forEach(n => n.classList.remove('sel')); };
    });
  }
  // 題材成員依族群分組：同族群的擺在一起，才看得出來誰跟誰在搶同一塊
  function themeMembersByGroup(t) {
    const by = new Map();
    (t.members || []).forEach(m => {
      const g = L.cgroup[m.code] || '_';
      if (!by.has(g)) by.set(g, { gid: g, name: g === '_' ? '未分類' : (L.gname[g] || g), rows: [], turnover: 0 });
      const e = by.get(g); e.rows.push(m); e.turnover += m.turnover || 0;
    });
    return [...by.values()].sort((a, b) => b.turnover - a.turnover);
  }
  function renderThemeDetail(th, id) {
    const t = th.themes.find(x => x.id === id) || th.themes[0]; if (!t) return;
    const el = $('#themeDetail');
    const dg = (window.ThemeDiagrams || {})[t.id];
    const groups = themeMembersByGroup(t);
    el.innerHTML = `<div class="grid g12"><div class="card"><div class="row spread"><h3>${fmt.esc(t.name)} <small>${fmt.esc(t.desc || '')}</small></h3>
      <button class="btn small" id="themeBack">← 回題材總覽</button></div>
      <div class="kvs" style="margin:10px 0"><div class="k"><div class="l">熱度</div><div class="v" style="color:${t.heat >= 70 ? CH.up : CH.amber}">${t.heat}</div></div><div class="k"><div class="l">成交值佔比</div><div class="v">${fmt.n(t.share, 1)}%</div></div><div class="k"><div class="l">5 日 vs 60 日</div><div class="v ${fmt.cls(t.flow_z)}">${t.flow_z != null ? (t.flow_z > 0 ? '+' : '') + t.flow_z.toFixed(1) + 'σ' : '—'}</div></div><div class="k"><div class="l">法人 5 日</div><div class="v ${fmt.cls(t.inst5)}">${t.inst5 != null ? fmt.lot(t.inst5 / 1000) : '—'}</div></div><div class="k"><div class="l">新聞 7 天</div><div class="v">${t.news7}</div></div></div>
      <div id="themeSeries" class="chart short"></div></div>
      <div class="card"><h3>成員 <small>依族群分組、組內依漲幅；滑過任一列會亮出它在產品圖上的位置</small></h3><div class="tw cap-md"><table id="themeMembers"><thead><tr><th class="l">代號</th><th class="l">簡稱</th><th>漲跌</th><th>成交值</th><th>法人</th></tr></thead><tbody>${groups.map(g => `<tr class="ghead"><td class="l" colspan="5">${g.gid === '_' ? '<span class="muted">未分類</span>' : L.group(g.gid)} <span class="muted">${g.rows.length} 檔 · ${fmt.yi(g.turnover)}</span></td></tr>`
      + g.rows.sort((a, b) => (b.chg_pct == null ? -Infinity : b.chg_pct) - (a.chg_pct == null ? -Infinity : a.chg_pct)).map(m => `<tr data-code="${m.code}" onclick="goStock('${m.code}')"><td class="l mono">${m.code}</td><td class="l">${L.stock(m.code, m.name)}</td><td class="num ${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct, 2)}</td><td class="num">${fmt.yi(m.turnover)}</td><td class="num ${fmt.cls(m.inst_net)}">${m.inst_net != null ? fmt.lot(m.inst_net / 1000) : '—'}</td></tr>`).join('')).join('')}</tbody></table></div>
      <div class="linkrow" style="margin-top:8px"><span class="muted">其他題材</span>${th.themes.filter(x => x.id !== t.id).slice(0, 12).map(x => L.theme(x.id, x.name)).join('')}</div></div></div>
      ${dg ? `<div class="card" style="margin-top:16px"><div class="row spread"><h3>產品剖析圖 <small>上游 → 中游 → 下游；原創等角示意圖，非實物比例。點環節看該段台股、點代號直接進個股頁</small></h3></div>
        <div id="themeDiagram" class="dgwrap">${dg()}</div><div id="themeParts"></div></div>` : ''}`;
    if (dg) {
      // 爆炸圖的零件高矮差很多，字串階段量不到尺寸，進 DOM 之後再等比縮到各自那一列
      if (window.ThemeDiagrams.fit) window.ThemeDiagrams.fit($('#themeDiagram', el));
      // 剖析圖不加滾輪縮放（跟產業／個股剖析圖一致，DECISIONS #84；Andy 09-13 再確認）
      // 要看大圖按右上角「放大」，那是明確的按鈕，不會搶走頁面捲動
      wireThemeDiagram(el, t);
    }
    // 點進某個題材之後要回得去（不然只能按瀏覽器上一頁）
    const back = $('#themeBack', el);
    if (back) back.onclick = () => {
      location.hash = '#themes';
      const m = $('#themeMap'); if (m && m.scrollIntoView) m.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const s = th.series[t.id] || [];
    chart('themeSeries', { tooltip: { ...tip, trigger: 'axis' }, grid: { left: 44, right: 16, top: 16, bottom: 26 }, xAxis: { ...axisStyle, type: 'category', data: s.map(x => x[0]), axisLabel: { color: CH.ink3, formatter: v => v.slice(5) } }, yAxis: { ...axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: '成交值佔比', type: 'line', data: s.map(x => x[1]), smooth: .3, showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 }, areaStyle: { color: 'rgba(255,143,171,.15)' } }] });
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
    const setSide = (open) => {
      $('#side').classList.toggle('open', open);
      $('#layout').classList.toggle('noside', !open);
      try { localStorage.setItem(SIDE_KEY, open ? '1' : '0'); } catch (e) { /* 忽略 */ }
      window.dispatchEvent(new Event('resize'));       // 欄寬變了，圖表要重畫
    };
    let sideOpen = true;
    try { sideOpen = localStorage.getItem(SIDE_KEY) !== '0'; } catch (e) { /* 忽略 */ }
    setSide(sideOpen);
    $('#evToggle').onclick = () => setSide($('#layout').classList.contains('noside'));
    $('#evClose').onclick = () => setSide(false);
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
      sankeyDots: () => (sankeyFx ? sankeyFx.dots.map(d => [d.x, d.y]) : []),
      sankeyFxRunning: () => !!(sankeyFx && sankeyFx.running()) };
    const [im, gt, cands, th, sc, all] = await Promise.all([load('industry_map'), load('groups_today'), load('candidates'), load('themes'), load('supply_chain'), load('stocks', { fallback: [] })]);
    L.init(im, gt, cands, th, sc, all);
    await Promise.all([renderEvents(), initSearch()]);
    await route();
    // 盤中即時層。放在 route() 之後：畫面上先有代號，Live 才知道要抓哪些。
    if (window.Live) window.Live.start();
  }
  boot();
})();
