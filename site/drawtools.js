/* =====================================================================================
 * drawtools.js —— 個股 K 線的手繪工具（DECISIONS #289，2026-10-02）
 *
 * 為什麼抽成獨立一支檔：
 *   以前畫線邏輯分散在 chart.js（DrawPrimitive／Drawings 兩個 class）與 industry.js（工具列 drawBar）。
 *   這一批要加文字框、橡皮擦、屬性列、選取／拖曳、測量、成交量分佈，程式量是原本的五倍；
 *   同時有兩個 agent 在改 chart.js（分時）與 industry.js（個股頁版面）。全部集中在這裡，
 *   chart.js 只剩 `enableDrawing()` 一行轉接、industry.js 只剩工具列掛載一行，三邊才不會互相踩到。
 *
 * 操作手感照 TradingView（只參考互動方式，程式碼與圖示全部自己寫、自己畫）：
 *   - 兩點工具（趨勢線／射線／箭頭／方框／測量／成交量分佈）：
 *       點一下 → 起點出現小圓圈、線跟著滑鼠拉；再點一下 → 固定終點、圓圈消失、完成。
 *       按住拖曳也可以（放開＝終點），舊的驗收與習慣都還能用。
 *   - 畫完自動回到「選取」；點圖形＝選取（兩端出現圓圈，可拖端點、拖線身整條移動）；點背景＝取消選取。
 *   - 文字：點一下就在原地出現可編輯的文字框（不再跳 window.prompt），Enter／點背景完成、Esc 取消；
 *     之後點文字可以再編輯、拖曳移動，屬性列改顏色與字級。
 *   - 橡皮擦：游標變成橡皮擦，點到哪個圖形就刪哪個；「全部清除」在它旁邊，要二次確認。
 *   - 選了工具或選取了圖形，圖上方出現屬性列（顏色、線寬、方框填滿／透明＋透明度、字級、分佈檔數…）。
 *
 * 錨點（★ 箭頭錯位的根因之一，見 DECISIONS #289）：
 *   每個點存 {t, p, o}：t＝K 棒時間、p＝價格、o＝「超出資料範圍的 K 棒根數」（未來空白區才有）。
 *   畫面座標一律用 時間→邏輯索引→座標 換算，縮放、捲動、換週期、重新整理都錨在時間與價格上，不是錨在像素。
 *   舊資料（{kind,a:{t,p},b:{t,p},color,w,fill,text}）沒有 o 與 id，讀進來照用、補上預設值即可。
 * ===================================================================================== */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------- 工具定義（圖示全部自己畫，18×18）
  const I = {
    cursor: '<path d="M4,2 L4,15 L7.5,11.6 L10,16 L12,15 L9.5,10.7 L14,10.5 Z"/>',
    trend: '<path d="M4.4,13.6 L13.6,4.4"/><circle cx="3.2" cy="14.8" r="1.7"/><circle cx="14.8" cy="3.2" r="1.7"/>',
    ray: '<circle cx="3.6" cy="14.4" r="1.8"/><path d="M5,13 L16.5,1.5"/><path d="M12.5,9.5 L15,9.5 M14,12 L16.5,12" stroke-dasharray="1.5 1.5"/>',
    arrow: '<path d="M3,15 L14,4"/><path d="M8.2,3.6 L14.4,3.6 L14.4,9.8" />',
    hline: '<path d="M1.5,9 H16.5"/><circle cx="9" cy="9" r="1.8"/>',
    rect: '<rect x="3" y="4" width="12" height="10" rx="1"/>',
    text: '<path d="M4,4.2 H14 M9,4.2 V15 M7,15 H11"/>',
    measure: '<rect x="2.5" y="2.5" width="13" height="13" rx="1.5" stroke-dasharray="2 1.6"/><path d="M9,5.2 V12.8 M6.6,7.6 L9,5.2 L11.4,7.6"/>',
    vp: '<path d="M3,2.5 V15.5"/><path d="M3,4.5 H8 M3,7.5 H14 M3,10.5 H11 M3,13.5 H6" stroke-width="2.2"/>',
    erase: '<path d="M2.8,12.2 L9.6,5.4 L14.4,10.2 L9.4,15.2 H5.8 Z"/><path d="M6.4,8.6 L11.2,13.4 M9.6,15.2 H16"/>',
    clear: '<path d="M2.5,4.5 H11 M2.5,8.5 H9 M2.5,12.5 H7.5"/><path d="M11,10 L16,15 M16,10 L11,15"/>',
    undo: '<path d="M7,4 L3,8 L7,12 M3,8 H11 a4,4 0 0 1 0,8 H8"/>',
    del: '<path d="M4,5 H14 M7,5 V3.5 H11 V5 M5.5,5 L6.3,15 H11.7 L12.5,5"/>',
  };
  const TOOLS = [
    { k: 'cursor', label: '選取（點圖形可拖曳、改端點）', pts: 0 },
    { k: 'trend', label: '趨勢線', pts: 2 },
    { k: 'ray', label: '射線（從起點往終點方向延伸到圖邊）', pts: 2 },
    { k: 'arrow', label: '箭頭（從起點指向終點）', pts: 2 },
    { k: 'hline', label: '水平線', pts: 1 },
    { k: 'rect', label: '方框', pts: 2 },
    { k: 'text', label: '文字', pts: 1 },
    { k: 'measure', label: '測量（價差、漲跌幅、K 棒根數、天數、區間量）', pts: 2 },
    { k: 'vp', label: '固定範圍成交量分佈（點起點、再點終點）', pts: 2 },
    { k: 'erase', label: '橡皮擦（點到哪個圖形就刪哪個）', pts: 0 },
  ].map(t => Object.assign(t, { icon: I[t.k] }));
  const KINDS = { trend: '趨勢線', ray: '射線', arrow: '箭頭', hline: '水平線', rect: '方框', text: '文字', measure: '測量', vp: '成交量分佈' };
  // 最後一個原本是 #e8eeff（近白），淺色主題畫在白底上等於沒畫；改成中性灰兩邊都看得見
  const COLORS = ['#3ee0ff', '#ffd166', '#ff4d6d', '#2ee59d', '#8b7bff', '#8ea0c4'];
  const WIDTHS = [1, 1.5, 2.5, 4, 6];
  const FONT_SIZES = [12, 14, 18, 24];
  const VP_ROWS = [12, 24, 36, 48, 60];

  // ---------------------------------------------------------------- 預設樣式（tw.draw.style，跟舊版同一個 key，舊欄位 w/c/fill 照讀）
  const STYLE_KEY = 'tw.draw.style';
  const STYLE = { c: COLORS[0], w: 1.5, fill: false, alpha: 0.28, fs: 14, vpRows: 24, vpPoc: true, vpVa: true, vpAlpha: 0.6 };
  try {
    const st = JSON.parse(localStorage.getItem(STYLE_KEY) || '{}');
    if (WIDTHS.indexOf(+st.w) >= 0) STYLE.w = +st.w;
    if (COLORS.indexOf(st.c) >= 0) STYLE.c = st.c;
    STYLE.fill = !!st.fill;
    if (st.alpha >= 0.05 && st.alpha <= 0.95) STYLE.alpha = +st.alpha;
    if (FONT_SIZES.indexOf(+st.fs) >= 0) STYLE.fs = +st.fs;
    if (+st.vpRows >= 12 && +st.vpRows <= 60) STYLE.vpRows = Math.round(+st.vpRows);
    if (typeof st.vpPoc === 'boolean') STYLE.vpPoc = st.vpPoc;
    if (typeof st.vpVa === 'boolean') STYLE.vpVa = st.vpVa;
    if (st.vpAlpha >= 0.1 && st.vpAlpha <= 1) STYLE.vpAlpha = +st.vpAlpha;
  } catch (e) { /* 私密模式等情況忽略 */ }
  const saveStyle = () => { try { localStorage.setItem(STYLE_KEY, JSON.stringify(STYLE)); } catch (e) { /* 忽略 */ } };

  // ---------------------------------------------------------------- 小工具
  const UP = () => ((global.KUtil && global.KUtil.colors && global.KUtil.colors.up) || '#ff4d6d');
  const DN = () => ((global.KUtil && global.KUtil.colors && global.KUtil.colors.down) || '#2ee59d');
  function rgba(hex, a) {
    const h = String(hex || '#3ee0ff').replace('#', '');
    const f = h.length === 3 ? h.split('').map(c => c + c).join('') : h.slice(0, 6);
    const n = parseInt(f, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }
  const uid = () => 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const tkey = (t) => (t && typeof t === 'object') ? `${t.year}-${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}` : String(t);
  function tnum(t) {   // 任何一種時間 → 秒（只拿來比大小與內插）
    if (typeof t === 'number') return t;
    if (t && typeof t === 'object') return Date.UTC(t.year, t.month - 1, t.day) / 1000;
    const ms = Date.parse(String(t).length === 10 ? t + 'T00:00:00Z' : t);
    return isNaN(ms) ? 0 : ms / 1000;
  }
  const fmtNum = (v, d) => (+v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const pdig = (p) => (Math.abs(p) >= 1000 ? 1 : 2);
  function fmtLots(shares) {
    const lots = (shares || 0) / 1000;
    if (lots >= 1e4) return fmtNum(lots / 1e4, 2) + ' 萬張';
    return fmtNum(Math.round(lots), 0) + ' 張';
  }
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  let MCTX = null;   // 量文字寬用的離屏 canvas（命中測試不能等畫完才知道文字多寬）
  function textW(str, fs) {
    if (!MCTX) MCTX = document.createElement('canvas').getContext('2d');
    MCTX.font = `600 ${fs}px "Noto Sans TC", sans-serif`;
    return MCTX.measureText(str).width;
  }
  function segDist(px, py, ax, ay, bx, by) {
    const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
    const u = L2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L2)) : 0;
    return Math.hypot(px - (ax + u * dx), py - (ay + u * dy));
  }

  // ---------------------------------------------------------------- 樣式表（集中在這支檔，不去動 index.html 的大樣式表）
  /* 橡皮擦游標：自己畫的 24×24 SVG，熱點在左下角的擦頭。用 !important 是因為圖表庫會在自己的 canvas 上寫 cursor。*/
  const ERASER_CUR = "url(\"data:image/svg+xml;utf8," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
    + '<path d="M3.5,16.5 L13,7 L19.5,13.5 L12.5,20.5 H7.5 Z" fill="#ff8fa3" stroke="#0a1020" stroke-width="1.6" stroke-linejoin="round"/>'
    + '<path d="M8.2,11.3 L14.7,17.8" stroke="#0a1020" stroke-width="1.6"/>'
    + '<path d="M13,7 L19.5,13.5" stroke="#fff" stroke-width="1" opacity=".6"/></svg>') + "\") 4 20, crosshair";
  function injectCss() {
    if (document.getElementById('dtCss')) return;
    const st = document.createElement('style'); st.id = 'dtCss';
    st.textContent = `
.dt-cross,.dt-cross *{cursor:crosshair!important}
.dt-erase,.dt-erase *{cursor:${ERASER_CUR}!important}
.dt-move,.dt-move *{cursor:move!important}
.dt-grab,.dt-grab *{cursor:grab!important}
.dt-lock,.dt-lock *{touch-action:none!important}
.dt-props{position:absolute;left:10px;z-index:6;display:flex;flex-wrap:wrap;align-items:center;gap:4px;
  max-width:calc(100% - 96px);padding:4px 6px;border:1px solid var(--line-2);border-radius:9px;
  background:var(--panel);box-shadow:0 8px 22px var(--drop,rgba(0,0,0,.35));font-size:12px;color:var(--ink-2);user-select:none}
.dt-props[hidden]{display:none!important}
.dt-props .dt-pl{font-weight:700;color:var(--ink);padding:0 4px 0 2px;white-space:nowrap}
.dt-props .dt-sep{width:1px;align-self:stretch;background:var(--line-2);margin:0 2px}
.dt-props button{font:inherit;color:inherit;background:transparent;border:1px solid transparent;border-radius:6px;cursor:pointer;padding:0;min-height:24px}
.dt-props .dt-c{width:20px;height:20px;min-height:20px;border:2px solid transparent;background:var(--c)}
.dt-props .dt-c.on{border-color:var(--ink)}
.dt-props .dt-w{width:24px;display:grid;place-items:center}
.dt-props .dt-w i{display:block;width:16px;background:currentColor;border-radius:2px}
.dt-props .dt-w.on,.dt-props .dt-seg button.on,.dt-props .dt-tg.on{background:rgba(62,224,255,.14);border-color:var(--cyan);color:var(--cyan)}
.dt-props .dt-seg{display:inline-flex;border:1px solid var(--line-2);border-radius:7px;overflow:hidden}
.dt-props .dt-seg button{border-radius:0;padding:0 8px;white-space:nowrap}
.dt-props .dt-tg,.dt-props .dt-act{padding:0 8px;border-color:var(--line-2);white-space:nowrap}
.dt-props .dt-del{width:26px;display:grid;place-items:center;color:var(--rise,#ff4d6d)}
.dt-props .dt-del svg,.dt-props .dt-act svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.dt-props label{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.dt-props input[type=range]{width:78px;accent-color:var(--cyan)}
.dt-props select{font:inherit;background:var(--panel-3);color:var(--ink);border:1px solid var(--line-2);border-radius:6px;padding:1px 4px}
.dt-props .dt-hint{color:var(--ink-3);white-space:nowrap}
.dt-props .dt-off{opacity:.4;pointer-events:none}
.dt-edit{position:absolute;z-index:8;margin:0;padding:1px 6px;border:1px dashed currentColor;border-radius:4px;
  background:rgba(10,16,32,.88);outline:none;font-weight:600;font-family:"Noto Sans TC",sans-serif;min-width:60px;box-sizing:content-box}
.dt-edit::placeholder{color:currentColor;opacity:.5}
.dt-confirm{position:absolute;z-index:30;left:calc(100% + 6px);top:0;width:178px;padding:8px 10px;border:1px solid var(--rise,#ff4d6d);
  border-radius:9px;background:var(--panel);box-shadow:0 10px 26px var(--drop,rgba(0,0,0,.4));font-size:12.5px;color:var(--ink);line-height:1.45}
.dt-confirm .dt-cb{display:flex;gap:6px;margin-top:7px}
.dt-confirm button{flex:1;min-height:28px;border-radius:6px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font:inherit}
.dt-confirm button[data-ok]{background:var(--rise,#ff4d6d);border-color:var(--rise,#ff4d6d);color:#fff;font-weight:700}
.drawbar{position:relative}
.drawbar .dtool.dt-danger{color:var(--rise,#ff4d6d)}
@media (max-width:760px){.dt-confirm{left:0;top:calc(100% + 6px)}.chartwrap.drawon>.adjtag{top:calc(var(--dtbar-h,0px) + 14px)}}
@media (max-width:820px){.dt-props{gap:3px;padding:4px;max-width:calc(100% - 70px)}.dt-props .dt-c{width:22px;height:22px}
  .dt-props button{min-height:28px}.dt-props .dt-w{width:28px}.dt-props input[type=range]{width:64px}}
`;
    document.head.appendChild(st);
  }

  // ---------------------------------------------------------------- 畫在圖上的那一層（Lightweight Charts 的 series primitive）
  class DrawPrim {
    constructor(m) { this.m = m; }
    attached(p) { this._series = p.series; this._chart = p.chart; this._req = p.requestUpdate; }
    detached() { this._series = null; }
    update() { if (this._req) this._req(); }
    updateAllViews() {}
    paneViews() {
      const self = this;
      return [{ zOrder: () => 'top', renderer: () => ({ draw(target) {
        target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
          if (!self._series || !self._chart) return;
          self.m._render(ctx, mediaSize.width, mediaSize.height);
        });
      } }) }];
    }
  }

  // ---------------------------------------------------------------- 主體
  class Drawings {
    constructor(kc, key) {
      injectCss();
      this.kc = kc; this.key = key;
      this.shapes = []; this.draft = null; this.tool = 'cursor';
      this.sel = null; this.hover = null; this.editing = null; this.hist = [];
      this.rendered = {};          // id → 這一輪畫出來的資訊（文字框大小、測量的字、分佈長條數）；命中測試與驗收用
      this.stats = { prompt: 0 };  // 驗收用
      this.prim = new DrawPrim(this);
      kc.candle.attachPrimitive(this.prim);
      this.load();
      this._bind();
      global.DrawTools.active = this;
    }

    // ---- 舊 API（industry.js 與舊驗收還在叫）
    setTool(t) {
      if (this.draft) { this.draft = null; this._placing = false; this._place = null; this._win(false); }
      if (this._drag) this._endDrag();
      if (this.editing) this._commitEdit();
      this.tool = t;
      if (t !== 'cursor') this._select(null, true);
      this._lock(t !== 'cursor');
      this._cursorCls();
      this._props();
      this.prim.update();
    }
    setColor(c) { this._setProp('color', c); }
    setWidth(w) { this._setProp('w', +w); }
    setFill(on) { this._setProp('fill', !!on); }
    undo() {
      if (this.editing) this._cancelEdit();
      if (this.hist.length) this.shapes = JSON.parse(this.hist.pop());
      else this.shapes.pop();
      this._select(null, true); this.save(); this.prim.update();
    }
    clear() { if (this.shapes.length) this._snap(); this.shapes = []; this._select(null, true); this.save(); this.prim.update(); }
    save() { try { localStorage.setItem(this.key, JSON.stringify(this.shapes)); } catch (e) { /* 私密模式等情況忽略 */ } }
    load() {
      let arr = [];
      try { const s = localStorage.getItem(this.key); arr = s ? JSON.parse(s) : []; } catch (e) { arr = []; }
      // 舊格式相容：沒有 id 就補一個（存的時候才寫回去）；壞掉的筆數跳過，不讓一筆壞資料弄掉整組
      this.shapes = (Array.isArray(arr) ? arr : []).filter(s => s && s.kind && s.a && s.a.t != null && isFinite(s.a.p))
        .map(s => { if (!s.id) s.id = uid(); return s; });
    }
    destroy() {
      if (this.editing) this._commitEdit();
      this._endDrag();
      const el = this.kc.el, h = this._h || {};
      el.removeEventListener('pointerdown', h.down, true);
      el.removeEventListener('pointermove', h.hover, true);
      el.removeEventListener('pointerleave', h.leave, true);
      el.removeEventListener('touchmove', h.tmove, true);
      el.removeEventListener('dblclick', h.dbl, true);
      document.removeEventListener('keydown', h.key, true);
      el.classList.remove('dt-cross', 'dt-erase', 'dt-move', 'dt-grab', 'dt-lock');
      if (this._propsEl && this._propsEl.parentNode) this._propsEl.parentNode.removeChild(this._propsEl);
      try { this.kc.candle.detachPrimitive(this.prim); } catch (e) { /* 圖已銷毀 */ }
      if (global.DrawTools.active === this) global.DrawTools.active = null;
      this._dead = true;
    }

    // ---- 座標換算（時間 ↔ 邏輯索引 ↔ 螢幕）
    _cache() {
      const d = this.kc.data || [];
      const c = this._tc;
      if (c && c.d === d && c.n === d.length && c.first === (d[0] && d[0].time) && c.last === (d[d.length - 1] && d[d.length - 1].time)) return c;
      const map = new Map(), nums = new Float64Array(d.length);
      for (let i = 0; i < d.length; i++) { map.set(tkey(d[i].time), i); nums[i] = tnum(d[i].time); }
      const n = d.length;
      const step = n > 1 ? (nums[n - 1] - nums[0]) / (n - 1) : 86400;
      this._tc = { d, n, map, nums, step: step || 86400, first: d[0] && d[0].time, last: d[n - 1] && d[n - 1].time };
      return this._tc;
    }
    _idxOf(t) {
      const c = this._cache();
      if (!c.n) return 0;
      const hit = c.map.get(tkey(t));
      if (hit !== undefined) return hit;
      // 這個時間不在目前的資料裡（還沒回補到的更舊歷史、或資料換過）：用前後兩根內插，超出兩端用平均間距外推
      const v = tnum(t), a = c.nums;
      if (v <= a[0]) return (v - a[0]) / c.step;
      if (v >= a[c.n - 1]) return c.n - 1 + (v - a[c.n - 1]) / c.step;
      let lo = 0, hi = c.n - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (a[mid] <= v) lo = mid; else hi = mid; }
      return lo + (v - a[lo]) / ((a[hi] - a[lo]) || 1);
    }
    _lx(pt) { return this._idxOf(pt.t) + (pt.o || 0); }
    _x(pt) { const v = this.kc.chart.timeScale().logicalToCoordinate(this._lx(pt)); return v == null ? null : v; }
    _y(p) { const v = this.kc.candle.priceToCoordinate(p); return v == null ? null : v; }
    _fromL(L) {          // 邏輯索引 → {t, o}（吸附到最近的一根 K 棒；超出資料範圍的部分記在 o）
      const c = this._cache(); if (!c.n) return null;
      const i = Math.round(L);
      if (i < 0) return { t: c.d[0].time, o: i };
      if (i > c.n - 1) return { t: c.d[c.n - 1].time, o: i - (c.n - 1) };
      return { t: c.d[i].time };
    }
    _pt(x, y) {
      const L = this.kc.chart.timeScale().coordinateToLogical(x);
      const p = this.kc.candle.coordinateToPrice(y);
      if (L == null || p == null) return null;
      const r = this._fromL(L); if (!r) return null;
      r.p = p; return r;
    }
    _tsec(pt) { const c = this._cache(); return tnum(pt.t) + (pt.o || 0) * c.step; }
    _paneH() { try { const ps = this.kc.chart.panes(); return ps && ps[0] ? ps[0].getHeight() : this.kc.el.clientHeight; } catch (e) { return this.kc.el.clientHeight; } }
    _plotW() { try { return this.kc.chart.timeScale().width(); } catch (e) { return this.kc.el.clientWidth; } }
    _local(e) { const r = this.kc.el.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }

    // ---- 幾何：每種圖形在螢幕上的樣子（畫圖與命中測試共用同一份，不會「看到的」跟「點得到的」不一樣）
    _geo(s, W, H) {
      const ax = s.a ? this._x(s.a) : null, ay = s.a ? this._y(s.a.p) : null;
      const two = s.kind !== 'hline' && s.kind !== 'text';
      const bx = two && s.b ? this._x(s.b) : null, by = two && s.b ? this._y(s.b.p) : null;
      if (ay === null || (s.kind !== 'hline' && ax === null)) return null;
      if (two && (bx === null || by === null)) return null;
      const g = { ax, ay, bx, by, handles: [] };
      if (s.kind === 'hline') {
        g.handles = [{ x: Math.max(20, Math.min(W - 20, W * 0.5)), y: ay, k: 'a' }];
      } else if (s.kind === 'text') {
        const fs = s.fs || 12, t = s.text || '文字';
        const w = textW(t, fs);
        g.box = { x: ax - 4, y: ay - fs - 2, w: w + 9, h: fs + 7 };
      } else if (s.kind === 'rect' || s.kind === 'measure') {
        g.box = { x: Math.min(ax, bx), y: Math.min(ay, by), w: Math.abs(bx - ax), h: Math.abs(by - ay) };
        g.handles = [{ x: ax, y: ay, k: 'aa' }, { x: bx, y: ay, k: 'ba' }, { x: bx, y: by, k: 'bb' }, { x: ax, y: by, k: 'ab' }];
      } else if (s.kind === 'vp') {
        const v = this.vpCalc(s);
        if (v) {
          const y1 = this._y(v.hi), y2 = this._y(v.lo);
          g.vp = v;
          if (y1 !== null && y2 !== null) g.box = { x: Math.min(ax, bx), y: Math.min(y1, y2), w: Math.abs(bx - ax), h: Math.max(4, Math.abs(y2 - y1)) };
        }
        g.handles = [{ x: ax, y: ay, k: 'a' }, { x: bx, y: by, k: 'b' }];
      } else {
        g.handles = [{ x: ax, y: ay, k: 'a' }, { x: bx, y: by, k: 'b' }];
        if (s.kind === 'ray') {
          /* ★ 射線往「起點→終點」那個方向延伸，左右上下都一樣。
             舊版只算往右：k=(圖寬−起點x)/dx，往左拉時 dx<0 → k<0 → 整段不延伸（DECISIONS #289 根因 ②）。*/
          const dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy) || 1, k = (W + H) * 2 / L;
          g.ex = ax + dx * k; g.ey = ay + dy * k;
        }
      }
      return g;
    }
    _hit(x, y, touch) {
      const W = this._plotW(), H = this._paneH(), tol = touch ? 14 : 7;
      for (let i = this.shapes.length - 1; i >= 0; i--) {
        const s = this.shapes[i]; if (s === this.editing) continue;
        const g = this._geo(s, W, H); if (!g) continue;
        if (this._onShape(s, g, x, y, tol)) return s;
      }
      return null;
    }
    _onShape(s, g, x, y, tol) {
      if (s.kind === 'hline') return Math.abs(y - g.ay) <= tol;
      if (g.box && (s.kind === 'text' || s.kind === 'measure' || s.kind === 'vp' || (s.kind === 'rect'))) {
        const b = g.box;
        const inside = x >= b.x - tol && x <= b.x + b.w + tol && y >= b.y - tol && y <= b.y + b.h + tol;
        if (s.kind === 'rect' && !s.fill) {
          // 透明方框只認框線（不然整塊都「點得到」，蓋住底下的 K 棒與其他圖形）
          const nearEdge = inside && (Math.abs(x - b.x) <= tol || Math.abs(x - b.x - b.w) <= tol || Math.abs(y - b.y) <= tol || Math.abs(y - b.y - b.h) <= tol);
          return nearEdge;
        }
        if (inside) return true;
        return (g.handles || []).some(h => Math.hypot(h.x - x, h.y - y) <= tol + 2);
      }
      if (s.kind === 'ray') return segDist(x, y, g.ax, g.ay, g.ex, g.ey) <= tol;
      return segDist(x, y, g.ax, g.ay, g.bx, g.by) <= tol;
    }
    _hitHandle(s, x, y, touch) {
      if (!s) return null;
      const g = this._geo(s, this._plotW(), this._paneH()); if (!g) return null;
      const r = touch ? 16 : 8;
      for (const h of g.handles) if (Math.hypot(h.x - x, h.y - y) <= r) return h.k;
      return null;
    }

    // ---- 量測（測量工具與驗收共用）
    measureInfo(s) {
      const c = this._cache();
      const la = this._lx(s.a), lb = this._lx(s.b);
      const bars = Math.round(lb) - Math.round(la);
      const diff = s.b.p - s.a.p, pct = s.a.p ? diff / s.a.p * 100 : 0;
      const span = Math.abs(this._tsec(s.b) - this._tsec(s.a));
      let vol = 0;
      if (c.n) {
        const i0 = Math.max(0, Math.round(Math.min(la, lb))), i1 = Math.min(c.n - 1, Math.round(Math.max(la, lb)));
        for (let i = i0; i <= i1; i++) vol += +c.d[i].volume || 0;
      }
      const intraday = typeof (c.d[0] && c.d[0].time) === 'number';
      let spanTxt;
      if (intraday && span < 86400) { const h = Math.floor(span / 3600), mi = Math.round((span % 3600) / 60); spanTxt = h ? `${h} 小時${mi ? ' ' + mi + ' 分' : ''}` : `${mi} 分`; }
      else spanTxt = `${Math.round(span / 86400)} 天`;
      const sg = diff > 0 ? '+' : diff < 0 ? '−' : '';
      const lines = [
        `${sg}${fmtNum(Math.abs(diff), 2)}（${sg}${fmtNum(Math.abs(pct), 2)}%）`,
        `${Math.abs(bars)} 根・${spanTxt}`,
        `量 ${fmtLots(vol)}`,
      ];
      return { diff, pct, bars, span, days: Math.round(span / 86400), vol, up: diff >= 0, lines };
    }
    /* 固定範圍成交量分佈（Andy 2026-10-02 第 8 項；演算法寫在 DECISIONS #289 同一段）：
       ① 範圍＝兩端點吸附到的 K 棒（含兩端），用目前週期的 K 棒，日／1時／4時都一樣算。
       ② 價格區間＝範圍內最低的 low 到最高的 high，等分成 N 檔（預設 24，屬性列 12～60）。
       ③ 每根 K 棒的量依它的 [low, high] 跟每一檔重疊的長度比例攤進去；high＝low 的整根放進收盤那一檔。
       ④ 收盤 > 開盤算上漲量（紅），其餘（含平盤）算下跌量（綠）。
       ⑤ POC＝總量最大的那一檔；價值區（70%）從 POC 往上下比較相鄰一檔，哪邊大就先併哪邊，直到累積 ≥ 70%。*/
    vpCalc(s) {
      const c = this._cache(); if (!c.n || !s.b) return null;
      const la = Math.round(this._lx(s.a)), lb = Math.round(this._lx(s.b));
      const i0 = Math.max(0, Math.min(la, lb)), i1 = Math.min(c.n - 1, Math.max(la, lb));
      if (i1 < i0) return null;
      const N = Math.max(12, Math.min(60, Math.round(s.rows || STYLE.vpRows)));
      const ck = `${i0}|${i1}|${N}|${c.n}|${tkey(c.d[i0].time)}|${c.d[i1].close}|${c.d[i1].volume}`;
      if (s._vp && s._vpk === ck) return s._vp;
      let lo = Infinity, hi = -Infinity, total = 0;
      for (let i = i0; i <= i1; i++) { const d = c.d[i]; lo = Math.min(lo, d.low); hi = Math.max(hi, d.high); total += +d.volume || 0; }
      const step = (hi - lo) / N;
      const rows = []; for (let r = 0; r < N; r++) rows.push({ lo: lo + r * step, hi: r === N - 1 ? hi : lo + (r + 1) * step, up: 0, dn: 0 });
      for (let i = i0; i <= i1; i++) {
        const d = c.d[i], v = +d.volume || 0; if (!v) continue;
        const side = d.close > d.open ? 'up' : 'dn';
        if (!(step > 0) || !(d.high > d.low)) {
          const r = step > 0 ? Math.max(0, Math.min(N - 1, Math.floor((d.close - lo) / step))) : 0;
          rows[r][side] += v; continue;
        }
        const r0 = Math.max(0, Math.floor((d.low - lo) / step)), r1 = Math.min(N - 1, Math.floor((d.high - lo) / step));
        const span = d.high - d.low;
        for (let r = r0; r <= r1; r++) {
          const ov = Math.min(d.high, rows[r].hi) - Math.max(d.low, rows[r].lo);
          if (ov > 0) rows[r][side] += v * ov / span;
        }
      }
      let poc = 0, sum = 0;
      rows.forEach((r, k) => { r.v = r.up + r.dn; sum += r.v; if (r.v > rows[poc].v) poc = k; });
      let a = poc, b = poc, acc = rows[poc].v;
      while (acc < sum * 0.7) {
        const up = b + 1 < N ? rows[b + 1].v : -1, dn = a - 1 >= 0 ? rows[a - 1].v : -1;
        if (up < 0 && dn < 0) break;
        if (up >= dn) { b++; acc += up; } else { a--; acc += dn; }
      }
      const out = { i0, i1, lo, hi, rows, poc, va: [a, b], total, sum, n: N };
      Object.defineProperty(s, '_vp', { value: out, writable: true, configurable: true, enumerable: false });
      Object.defineProperty(s, '_vpk', { value: ck, writable: true, configurable: true, enumerable: false });
      return out;
    }

    // ---- 畫
    _render(ctx, W, H) {
      this.rendered = {};
      const list = this.shapes.concat(this.draft ? [this.draft] : []);
      for (const s of list) {
        if (s === this.editing) continue;
        const g = this._geo(s, W, H); if (!g) continue;
        ctx.save();
        const hot = (s === this.hover && s !== this.sel);
        if (hot) { ctx.shadowColor = this.tool === 'erase' ? UP() : (s.color || STYLE.c); ctx.shadowBlur = 10; }
        try { this._draw(ctx, s, g, W, H); } catch (e) { /* 單一圖形畫壞不影響其他 */ }
        ctx.restore();
        if (s === this.sel || s === this.draft) this._drawHandles(ctx, s, g);
      }
      // 編輯中的文字框跟著錨點走（使用者邊打字邊捲動也不會飄掉）
      if (this.editing && this._edit) this._placeEdit();
    }
    _draw(ctx, s, g, W, H) {
      const col = s.color || STYLE.c;
      ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = s.w || 1.5;
      ctx.setLineDash(s.dash ? [5, 4] : []);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      const { ax, ay, bx, by } = g;
      switch (s.kind) {
        case 'hline': {
          ctx.beginPath(); ctx.moveTo(0, ay); ctx.lineTo(W, ay); ctx.stroke();
          ctx.shadowBlur = 0;
          ctx.font = '600 11px "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace'; ctx.textAlign = 'left';
          const lab = fmtNum(s.a.p, pdig(s.a.p));
          ctx.fillStyle = 'rgba(10,16,32,.85)'; ctx.fillRect(3, ay - 13, ctx.measureText(lab).width + 8, 14);
          ctx.fillStyle = col; ctx.fillText(lab, 7, ay - 2.5);
          break;
        }
        case 'text': {
          const fs = s.fs || 12, b = g.box;
          ctx.font = `600 ${fs}px "Noto Sans TC", sans-serif`; ctx.textAlign = 'left';
          ctx.fillStyle = 'rgba(10,16,32,.8)'; ctx.fillRect(b.x, b.y, b.w, b.h);
          if (s === this.sel) { ctx.setLineDash([3, 3]); ctx.lineWidth = 1; ctx.strokeRect(b.x + .5, b.y + .5, b.w, b.h); }
          ctx.fillStyle = col; ctx.fillText(s.text || '文字', ax + 1, ay);
          this.rendered[s.id] = { box: b, text: s.text };
          break;
        }
        case 'rect': {
          const b = g.box;
          // fill=true 實心（透明度可調，看得出範圍）、false 只有框線（不遮住 K 棒）
          if (s.fill) { ctx.fillStyle = rgba(col, s.alpha != null ? s.alpha : 0.28); ctx.fillRect(b.x, b.y, b.w, b.h); }
          ctx.strokeRect(b.x + .5, b.y + .5, b.w, b.h);
          this.rendered[s.id] = { box: b, fill: !!s.fill, alpha: s.fill ? (s.alpha != null ? s.alpha : 0.28) : 0 };
          break;
        }
        case 'measure': this._drawMeasure(ctx, s, g, W, H); break;
        case 'vp': this._drawVp(ctx, s, g, W, H); break;
        case 'arrow': {
          /* ★ 箭頭：從起點指向終點，箭頭畫在終點（DECISIONS #289 根因 ①：舊工具列那顆「箭頭」圖示其實是射線，
             畫出來沒有箭頭、還會衝到圖邊）。線收在箭頭底部，粗線才不會從尖端戳出來。*/
          const ang = Math.atan2(by - ay, bx - ax), len = Math.hypot(bx - ax, by - ay);
          const hl = Math.min(Math.max(10, (s.w || 1.5) * 4.2), len * 0.6 || 10), hw = 0.48;
          const baseX = bx - Math.cos(ang) * hl * 0.82, baseY = by - Math.sin(ang) * hl * 0.82;
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(baseX, baseY); ctx.stroke();
          ctx.setLineDash([]);
          ctx.beginPath(); ctx.moveTo(bx, by);
          ctx.lineTo(bx - Math.cos(ang - hw) * hl, by - Math.sin(ang - hw) * hl);
          ctx.lineTo(bx - Math.cos(ang + hw) * hl, by - Math.sin(ang + hw) * hl);
          ctx.closePath(); ctx.fill();
          this.rendered[s.id] = { tip: { x: bx, y: by }, tail: { x: ax, y: ay } };
          break;
        }
        case 'ray':
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(g.ex, g.ey); ctx.stroke();
          this.rendered[s.id] = { from: { x: ax, y: ay }, to: { x: g.ex, y: g.ey } };
          break;
        default:
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
      }
    }
    _drawMeasure(ctx, s, g, W, H) {
      const mi = this.measureInfo(s), col = mi.up ? UP() : DN(), b = g.box;
      ctx.setLineDash([]); ctx.lineWidth = 1;
      ctx.fillStyle = rgba(col, 0.16); ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeStyle = rgba(col, 0.7); ctx.strokeRect(b.x + .5, b.y + .5, b.w, b.h);
      // 中間一支直的、一支橫的箭頭：一眼看出往哪邊、走多遠
      const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
      const arr = (x1, y1, x2, y2) => {
        if (Math.hypot(x2 - x1, y2 - y1) < 8) return;
        const a = Math.atan2(y2 - y1, x2 - x1);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x2, y2); ctx.lineTo(x2 - Math.cos(a - .5) * 7, y2 - Math.sin(a - .5) * 7);
        ctx.moveTo(x2, y2); ctx.lineTo(x2 - Math.cos(a + .5) * 7, y2 - Math.sin(a + .5) * 7); ctx.stroke();
      };
      ctx.strokeStyle = col; ctx.lineWidth = 1.3;
      arr(cx, g.ay, cx, g.by); arr(g.ax, cy, g.bx, cy);
      // 數字框：放在終點那一側（往上量放上面、往下量放下面），夾在圖內
      ctx.font = '600 12px "JetBrains Mono", "Noto Sans TC", monospace'; ctx.textAlign = 'center';
      const lw = Math.max(...mi.lines.map(l => ctx.measureText(l).width)) + 16, lh = 17, bh = lh * mi.lines.length + 8;
      let lx = cx - lw / 2, ly = mi.up ? b.y - bh - 6 : b.y + b.h + 6;
      if (ly < 2) ly = b.y + b.h + 6;
      if (ly + bh > H - 2) ly = Math.max(2, b.y - bh - 6);
      lx = Math.max(2, Math.min(W - lw - 2, lx));
      ctx.fillStyle = rgba(col, 0.88); ctx.fillRect(lx, ly, lw, bh);
      ctx.fillStyle = '#fff';
      mi.lines.forEach((l, k) => ctx.fillText(l, lx + lw / 2, ly + 4 + lh * (k + 1) - 4.5));
      this.rendered[s.id] = { lines: mi.lines, box: b, label: { x: lx, y: ly, w: lw, h: bh }, up: mi.up };
    }
    _drawVp(ctx, s, g, W, H) {
      const v = g.vp, xl = Math.min(g.ax, g.bx), xr = Math.max(g.ax, g.bx);
      ctx.setLineDash([]);
      if (!v || !g.box) { this.rendered[s.id] = { bars: 0 }; return; }
      const b = g.box, alpha = s.alpha != null ? s.alpha : STYLE.vpAlpha;
      ctx.fillStyle = 'rgba(62,224,255,.06)'; ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeStyle = 'rgba(62,224,255,.28)'; ctx.lineWidth = 1; ctx.strokeRect(b.x + .5, b.y + .5, b.w, b.h);
      const maxV = Math.max(...v.rows.map(r => r.v)) || 1;
      const maxW = Math.max(24, (xr - xl) * 0.7);
      const va = s.va !== false && (s.va != null ? s.va : STYLE.vpVa);
      let drawn = 0;
      v.rows.forEach((r, k) => {
        const y1 = this._y(r.hi), y2 = this._y(r.lo); if (y1 === null || y2 === null) return;
        const top = Math.min(y1, y2), h = Math.max(1, Math.abs(y2 - y1) - 1);
        const len = r.v / maxV * maxW, ul = r.v ? r.up / r.v * len : 0;
        const inVa = !va || (k >= v.va[0] && k <= v.va[1]);
        const a = inVa ? alpha : alpha * 0.45;
        ctx.fillStyle = rgba(UP(), a); ctx.fillRect(xl, top, ul, h);
        ctx.fillStyle = rgba(DN(), a); ctx.fillRect(xl + ul, top, len - ul, h);
        drawn++;
      });
      const showPoc = s.poc != null ? s.poc : STYLE.vpPoc;
      let pocY = null;
      if (showPoc) {
        const pr = v.rows[v.poc], py = this._y((pr.lo + pr.hi) / 2);
        if (py !== null) {
          pocY = py;
          ctx.strokeStyle = '#ffd166'; ctx.lineWidth = 1.6;
          ctx.beginPath(); ctx.moveTo(xl, py); ctx.lineTo(xr, py); ctx.stroke();
          ctx.font = '700 11px "JetBrains Mono", monospace'; ctx.textAlign = 'right';
          const lab = 'POC ' + fmtNum((pr.lo + pr.hi) / 2, pdig(pr.hi));
          const tw = ctx.measureText(lab).width;
          ctx.fillStyle = 'rgba(10,16,32,.85)'; ctx.fillRect(xr - tw - 8, py - 14, tw + 6, 13);
          ctx.fillStyle = '#ffd166'; ctx.fillText(lab, xr - 5, py - 4);
        }
      }
      this.rendered[s.id] = { bars: drawn, rows: v.n, poc: v.poc, pocY, total: v.total, sum: v.sum, box: b };
    }
    _drawHandles(ctx, s, g) {
      ctx.save();
      ctx.setLineDash([]);
      const col = s.kind === 'measure' ? (this.measureInfo(s).up ? UP() : DN()) : (s.color || STYLE.c);
      const touch = this._touchUi;
      const r = touch ? 7 : 5;
      let hs = g.handles;
      if (s === this.draft && s.kind !== 'rect' && s.kind !== 'measure') hs = hs.slice(0, 2);
      if (s === this.draft && (s.kind === 'rect' || s.kind === 'measure')) hs = [hs[0], hs[2]];
      for (const h of hs) {
        ctx.beginPath(); ctx.arc(h.x, h.y, r, 0, Math.PI * 2);
        ctx.fillStyle = (global.KUtil && global.KUtil.colors && global.KUtil.colors.bg) || '#0a1020'; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
      }
      ctx.restore();
      this.rendered._handles = (this.rendered._handles || 0) + hs.length;
    }

    // ---- 事件
    _bind() {
      const el = this.kc.el;
      this._h = {
        down: (e) => this._down(e),
        hover: (e) => this._hoverMove(e),
        leave: () => { if (this.hover) { this.hover = null; this._cursorCls(); this.prim.update(); } },
        tmove: (e) => { if (this._drag || this._placing || this.tool !== 'cursor') e.preventDefault(); },
        key: (e) => this._key(e),
        dbl: (e) => { if (this._swallowDbl) { e.stopPropagation(); this._swallowDbl = false; } },
      };
      el.addEventListener('pointerdown', this._h.down, true);
      el.addEventListener('pointermove', this._h.hover, true);
      el.addEventListener('pointerleave', this._h.leave, true);
      el.addEventListener('touchmove', this._h.tmove, { capture: true, passive: false });
      el.addEventListener('dblclick', this._h.dbl, true);
      document.addEventListener('keydown', this._h.key, true);
    }
    _lock(on) {
      try { this.kc.chart.applyOptions({ handleScroll: { pressedMouseMove: !on, horzTouchDrag: !on }, handleScale: { axisPressedMouseMove: { time: !on, price: !on } } }); } catch (e) { /* 圖已銷毀 */ }
      this._locked = on;
      this._cursorCls();
    }
    _cursorCls(over) {
      const el = this.kc.el; if (!el) return;
      const t = this.tool;
      el.classList.toggle('dt-erase', t === 'erase');
      el.classList.toggle('dt-cross', t !== 'cursor' && t !== 'erase');
      el.classList.toggle('dt-move', t === 'cursor' && over === 'move');
      el.classList.toggle('dt-grab', t === 'cursor' && over === 'grab');
      // 觸控：拿著工具或選著圖形時，手指在圖上滑不能捲動整頁（不然拖不動端點）
      el.classList.toggle('dt-lock', t !== 'cursor' || !!this.sel);
    }
    _emitTool() {
      try { document.dispatchEvent(new CustomEvent('tw:drawtool', { detail: { tool: this.tool } })); } catch (e) { /* 忽略 */ }
    }
    _done() {   // 畫完一個圖形：回到選取（TradingView 預設行為），工具列跟著亮回「選取」
      this.tool = 'cursor'; this._lock(false); this._emitTool(); this._props();
    }
    _snap() { this.hist.push(JSON.stringify(this.shapes)); if (this.hist.length > 60) this.hist.shift(); }
    _swallow(e) { e.preventDefault(); e.stopPropagation(); }
    _down(e) {
      if (this._dead) return;
      if (e.button > 0) return;
      const tgt = e.target;
      if (!(tgt instanceof HTMLCanvasElement)) return;            // 屬性列、文字框、重設縮放鈕、圖例都不是畫布
      const touch = e.pointerType === 'touch' || e.pointerType === 'pen';
      this._touchUi = touch;
      const L = this._local(e), W = this._plotW(), H = this._paneH();
      const inMain = L.x >= 0 && L.x <= W && L.y >= 0 && L.y <= H;
      // 編輯文字中：點哪裡都先完成編輯（點背景完成），這一下不做別的事
      if (this.editing) { this._commitEdit(); this._swallow(e); return; }
      // 兩點工具「點一下、再點一下」的第二下：固定終點、完成
      if (this._placing && this.draft) {
        const p = this._pt(Math.max(0, Math.min(W, L.x)), Math.max(0, Math.min(H, L.y)));
        if (p) this._setDraftB(p, e.shiftKey);
        this._swallow(e); this._swallowDbl = true;
        this._commitDraft();
        return;
      }
      if (this.tool === 'erase') {
        if (!inMain) return;
        const s = this._hit(L.x, L.y, touch);
        if (s) this._remove(s);
        this._swallow(e);
        return;
      }
      if (this.tool === 'cursor') {
        if (!inMain) return;
        const hk = this._hitHandle(this.sel, L.x, L.y, touch);
        if (hk) { this._startDrag(e, this.sel, 'handle', hk, L); this._swallow(e); return; }
        const s = this._hit(L.x, L.y, touch);
        if (s) {
          const was = this.sel === s;
          this._select(s);
          this._startDrag(e, s, 'move', null, L, was);
          this._swallow(e);
          return;
        }
        if (this.sel) { this._select(null); }
        return;                                                    // 點背景：取消選取，事件照樣交給圖表（可以拖著平移）
      }
      // ---- 畫圖工具
      if (!inMain) return;
      const p = this._pt(L.x, L.y); if (!p) return;
      this._swallow(e);
      const def = TOOLS.find(d => d.k === this.tool) || {};
      if (this.tool === 'text') { this._newText(p); return; }
      if (def.pts === 1) {
        this._snap();
        const s = { id: uid(), kind: this.tool, a: { t: p.t, p: p.p }, color: STYLE.c, w: STYLE.w };
        if (p.o) s.a.o = p.o;
        this.shapes.push(s); this.save(); this._done(); this.prim.update();
        this._drawEnd();
        return;
      }
      const a = { t: p.t, p: p.p }; if (p.o) a.o = p.o;
      this.draft = this._newShape(this.tool, a);
      this._placing = false;
      this._place = { x: L.x, y: L.y, moved: false, start: Object.assign({}, a, { x: L.x, y: L.y }) };
      this._select(null, true);
      this._win(true);
      this.prim.update();
    }
    _newShape(kind, a) {
      const s = { id: uid(), kind, a, b: Object.assign({}, a), color: STYLE.c, w: STYLE.w };
      if (kind === 'rect') { s.fill = STYLE.fill; s.alpha = STYLE.alpha; }
      if (kind === 'vp') { s.rows = STYLE.vpRows; s.poc = STYLE.vpPoc; s.va = STYLE.vpVa; s.alpha = STYLE.vpAlpha; }
      if (kind === 'measure') { delete s.color; delete s.w; }
      return s;
    }
    _setDraftB(p, shift) {
      const d = this.draft; if (!d) return;
      let t = p.t, o = p.o, pr = p.p;
      /* Andy 2026-09-15：「當拉線時，按著 Shift 會主動變成水平線」。往左右拉得比較多就鎖水平（價格不變），
         往上下拉得比較多就鎖垂直（時間不變）。*/
      if (shift && this._place) {
        const st = this._place.start, x = this._x(p), y = this._y(p.p);
        if (x !== null && y !== null && Math.abs(x - st.x) >= Math.abs(y - st.y)) pr = st.p;
        else { t = st.t; o = st.o; }
      }
      d.b = { t, p: pr }; if (o) d.b.o = o;
      d.shift = !!shift;
    }
    _commitDraft() {
      const d = this.draft; this.draft = null; this._placing = false; this._place = null; this._win(false);
      if (!d) return;
      const ax = this._x(d.a), bx = this._x(d.b), ay = this._y(d.a.p), by = this._y(d.b.p);
      // 兩下點在同一點（長度 0）不算一個圖形
      if (ax !== null && bx !== null && ay !== null && by !== null && Math.hypot(bx - ax, by - ay) < 3) { this.prim.update(); return; }
      this._snap();
      this.shapes.push(d); this.save(); this._done(); this.prim.update();
      this._drawEnd();
    }
    _drawEnd() { if (this.kc.opts && this.kc.opts.onDrawEnd) this.kc.opts.onDrawEnd(); }
    _win(on) {
      if (on && !this._wh) {
        this._wh = { move: (e) => this._winMove(e), up: (e) => this._winUp(e) };
        window.addEventListener('pointermove', this._wh.move, true);
        window.addEventListener('pointerup', this._wh.up, true);
        window.addEventListener('pointercancel', this._wh.up, true);
      } else if (!on && this._wh) {
        window.removeEventListener('pointermove', this._wh.move, true);
        window.removeEventListener('pointerup', this._wh.up, true);
        window.removeEventListener('pointercancel', this._wh.up, true);
        this._wh = null;
      }
    }
    _winMove(e) {
      const L = this._local(e), W = this._plotW(), H = this._paneH();
      const cx = Math.max(0, Math.min(W, L.x)), cy = Math.max(0, Math.min(H, L.y));
      if (this.draft && this._place) {
        if (Math.hypot(L.x - this._place.x, L.y - this._place.y) > 5) this._place.moved = true;
        const p = this._pt(cx, cy); if (p) this._setDraftB(p, e.shiftKey);
        this.prim.update();
        e.preventDefault();
        return;
      }
      if (this._drag) { this._dragMove(cx, cy, L); e.preventDefault(); }
    }
    _winUp(e) {
      if (this.draft && this._place) {
        if (this._place.moved || e.type === 'pointercancel') { this._commitDraft(); return; }
        // 沒拖動＝「點一下」：進入第二點模式，線跟著滑鼠走，等下一次點擊
        this._placing = true; this._win(false);
        return;
      }
      if (this._drag) this._endDrag(true);
    }
    _hoverMove(e) {
      if (this._dead || this._drag) return;
      const L = this._local(e);
      if (this._placing && this.draft) {
        const W = this._plotW(), H = this._paneH();
        const p = this._pt(Math.max(0, Math.min(W, L.x)), Math.max(0, Math.min(H, L.y)));
        if (p) { this._setDraftB(p, e.shiftKey); this.prim.update(); }
        return;
      }
      if (e.pointerType === 'touch') return;
      if (this.tool !== 'cursor' && this.tool !== 'erase') return;
      const tgt = e.target;
      const onCanvas = tgt instanceof HTMLCanvasElement;
      let hov = null, over = null;
      if (onCanvas && L.x <= this._plotW() && L.y <= this._paneH()) {
        if (this.tool === 'cursor' && this._hitHandle(this.sel, L.x, L.y, false)) over = 'grab';
        hov = this._hit(L.x, L.y, false);
        if (hov && !over) over = 'move';
      }
      if (hov !== this.hover) { this.hover = hov; this.prim.update(); }
      this._cursorCls(over);
    }
    _startDrag(e, s, mode, hk, L, wasSel) {
      const pts = {};
      ['a', 'b'].forEach(k => { if (s[k]) pts[k] = { L: this._lx(s[k]), p: s[k].p }; });
      const p0 = this._pt(L.x, L.y);
      this._drag = { s, mode, hk, x: L.x, y: L.y, L0: this.kc.chart.timeScale().coordinateToLogical(L.x), p0: p0 ? p0.p : null,
        pts, moved: false, wasSel, snapped: false };
      this._lock(true);
      this._win(true);
    }
    _dragMove(cx, cy, L) {
      const d = this._drag, s = d.s;
      if (!d.moved && Math.hypot(L.x - d.x, L.y - d.y) < 3) return;
      if (!d.snapped) { this._snap(); d.snapped = true; }
      d.moved = true;
      const p = this._pt(cx, cy); if (!p) return;
      if (d.mode === 'handle') {
        const k = d.hk;
        if (k.length === 2) {          // 方框／測量的角：第一個字＝時間用哪一點、第二個字＝價格用哪一點
          const tk = k[0], pk = k[1];
          s[tk].t = p.t; if (p.o) s[tk].o = p.o; else delete s[tk].o;
          s[pk].p = p.p;
        } else if (s.kind === 'hline') {
          s.a.p = p.p;
        } else {
          s[k] = { t: p.t, p: p.p }; if (p.o) s[k].o = p.o;
        }
      } else {
        const Ln = this.kc.chart.timeScale().coordinateToLogical(cx);
        const dL = (Ln == null || d.L0 == null) ? 0 : Math.round(Ln) - Math.round(d.L0);
        const dP = (d.p0 == null) ? 0 : p.p - d.p0;
        Object.keys(d.pts).forEach(k => {
          const o = d.pts[k];
          if (s.kind !== 'hline') { const r = this._fromL(o.L + dL); if (r) { s[k].t = r.t; if (r.o) s[k].o = r.o; else delete s[k].o; } }
          s[k].p = o.p + dP;
        });
      }
      this.prim.update();
    }
    _endDrag(fromUp) {
      const d = this._drag; if (!d) return;
      this._drag = null; this._win(false); this._lock(this.tool !== 'cursor');
      if (d.moved) { this.save(); this._drawEnd(); }
      else if (fromUp && d.mode === 'move' && d.s.kind === 'text') this._editText(d.s, false);   // 點一下文字＝編輯內容
      this.prim.update();
    }
    _key(e) {
      if (this._dead || !this.kc.el.isConnected) return;
      const t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
      if (typing) return;
      if (e.key === 'Escape') {
        if (this.draft) { this.draft = null; this._placing = false; this._place = null; this._win(false); this.prim.update(); e.stopPropagation(); return; }
        if (this.sel) { this._select(null); e.stopPropagation(); return; }
        if (this.tool !== 'cursor') { this.setTool('cursor'); this._emitTool(); e.stopPropagation(); }
        return;
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && this.sel) { this._remove(this.sel); e.preventDefault(); e.stopPropagation(); }
    }
    _select(s, quiet) {
      if (this.sel === s) return;
      this.sel = s; this.hover = null;
      this._cursorCls();
      if (!quiet) { this._props(); this.prim.update(); } else this._props();
    }
    _remove(s) {
      const i = this.shapes.indexOf(s); if (i < 0) return;
      this._snap();
      this.shapes.splice(i, 1);
      if (this.sel === s) this.sel = null;
      if (this.hover === s) this.hover = null;
      this.save(); this._cursorCls(); this._props(); this.prim.update();
    }

    // ---- 文字框（就地編輯，不再用 window.prompt）
    _newText(p) {
      const s = { id: uid(), kind: 'text', a: { t: p.t, p: p.p }, color: STYLE.c, w: STYLE.w, fs: STYLE.fs, text: '' };
      if (p.o) s.a.o = p.o;
      this.tool = 'cursor'; this._lock(false); this._emitTool();
      this._editText(s, true);
    }
    _editText(s, isNew) {
      if (this.editing) this._commitEdit();
      const inp = document.createElement('input');
      inp.type = 'text'; inp.className = 'dt-edit'; inp.placeholder = '新增文字'; inp.maxLength = 80;
      inp.value = s.text || ''; inp.setAttribute('aria-label', '圖上文字');
      inp.style.color = s.color || STYLE.c; inp.style.fontSize = (s.fs || 12) + 'px';
      this.kc.el.appendChild(inp);
      this.editing = s; this._edit = { inp, isNew, orig: s.text || '' };
      if (!isNew) this._select(s, true); else this._select(null, true);
      this._props();
      const fit = () => { inp.style.width = Math.max(60, textW(inp.value || inp.placeholder, s.fs || 12) + 6) + 'px'; };
      fit(); this._placeEdit();
      inp.addEventListener('input', () => { fit(); });
      inp.addEventListener('keydown', (ev) => {
        ev.stopPropagation();
        if (ev.key === 'Enter') { ev.preventDefault(); this._commitEdit(); }
        else if (ev.key === 'Escape') { ev.preventDefault(); this._cancelEdit(); }
      });
      inp.addEventListener('blur', () => { if (this._edit && this._edit.inp === inp) this._commitEdit(); });
      inp.addEventListener('pointerdown', (ev) => ev.stopPropagation());
      this.prim.update();
      setTimeout(() => { try { inp.focus(); inp.select(); } catch (e) { /* 忽略 */ } }, 0);
    }
    _placeEdit() {
      const s = this.editing, ed = this._edit; if (!s || !ed) return;
      const x = this._x(s.a), y = this._y(s.a.p); if (x === null || y === null) return;
      const fs = s.fs || 12;
      ed.inp.style.left = Math.round(x - 7) + 'px';
      ed.inp.style.top = Math.round(y - fs - 3) + 'px';
    }
    _commitEdit() {
      const s = this.editing, ed = this._edit; if (!s || !ed) return;
      this.editing = null; this._edit = null;
      const v = (ed.inp.value || '').trim();
      if (ed.inp.parentNode) ed.inp.parentNode.removeChild(ed.inp);
      if (ed.isNew) {
        if (v) { this._snap(); s.text = v; this.shapes.push(s); this.save(); this._drawEnd(); }
      } else if (!v) {
        this._remove(s);
      } else if (v !== ed.orig) {
        this._snap(); s.text = v; this.save();
      }
      this._props(); this.prim.update();
    }
    _cancelEdit() {
      const ed = this._edit; if (!ed) return;
      this.editing = null; this._edit = null;
      if (ed.inp.parentNode) ed.inp.parentNode.removeChild(ed.inp);
      this._props(); this.prim.update();
    }

    // ---- 屬性列
    _ctxKind() {
      if (this.sel) return this.sel.kind;
      if (this.editing) return 'text';
      if (this.tool !== 'cursor' && this.tool !== 'erase') return this.tool;
      return null;
    }
    _target() { return this.sel || this.editing || null; }
    _val(field) {
      const s = this._target();
      const def = { color: STYLE.c, w: STYLE.w, fill: STYLE.fill, alpha: STYLE.alpha, fs: STYLE.fs, rows: STYLE.vpRows, poc: STYLE.vpPoc, va: STYLE.vpVa, vpAlpha: STYLE.vpAlpha };
      if (!s) return def[field];
      if (field === 'vpAlpha') return s.alpha != null ? s.alpha : STYLE.vpAlpha;
      if (field === 'alpha') return s.alpha != null ? s.alpha : STYLE.alpha;
      if (field === 'fs') return s.fs || 12;
      if (field === 'color') return s.color || STYLE.c;
      if (s[field] == null) return def[field];
      return s[field];
    }
    _setProp(field, val, noSnap) {
      const s = this._target();
      const map = { color: 'c', w: 'w', fill: 'fill', alpha: 'alpha', fs: 'fs', rows: 'vpRows', poc: 'vpPoc', va: 'vpVa', vpAlpha: 'vpAlpha' };
      if (map[field]) { STYLE[map[field]] = val; saveStyle(); }
      if (s) {
        if (!noSnap && this.shapes.indexOf(s) >= 0) this._snap();
        if (field === 'vpAlpha') s.alpha = val; else s[field] = val;
        if (this.editing === s && this._edit) {
          this._edit.inp.style.color = s.color || STYLE.c; this._edit.inp.style.fontSize = (s.fs || 12) + 'px';
          this._edit.inp.style.width = Math.max(60, textW(this._edit.inp.value || '新增文字', s.fs || 12) + 6) + 'px';
          this._placeEdit();
        }
        if (this.shapes.indexOf(s) >= 0) this.save();
      }
      if (global.DrawTools._onStyle) global.DrawTools._onStyle(STYLE);
      this.prim.update();
    }
    _props() {
      const k = this._ctxKind();
      let el = this._propsEl;
      if (!k) { if (el) el.hidden = true; return; }
      if (!el) {
        el = this._propsEl = document.createElement('div');
        el.className = 'dt-props'; el.setAttribute('role', 'toolbar');
        el.addEventListener('pointerdown', (e) => { e.stopPropagation(); if (e.target.type === 'range') { const s = this._target(); if (s && this.shapes.indexOf(s) >= 0) this._snap(); } });
        el.addEventListener('mousedown', (e) => { if (this.editing && e.target.tagName !== 'SELECT' && e.target.tagName !== 'INPUT') e.preventDefault(); });   // 改字級／顏色時文字框不要失焦
        el.addEventListener('click', (e) => this._propClick(e));
        el.addEventListener('input', (e) => this._propInput(e));
        el.addEventListener('change', (e) => this._propInput(e, true));
        this.kc.el.appendChild(el);
      }
      el.hidden = false;
      const s = this._target();
      const cols = COLORS.map(c => `<button class="dt-c ${c === this._val('color') ? 'on' : ''}" data-c="${c}" style="--c:${c}" title="${k === 'rect' ? '邊框色' : '顏色'}" aria-label="顏色 ${c}"></button>`).join('');
      const wid = WIDTHS.map(w => `<button class="dt-w dw ${w === this._val('w') ? 'on' : ''}" data-w="${w}" title="線寬 ${w}px"><i style="height:${w}px"></i></button>`).join('');
      const sep = '<span class="dt-sep"></span>';
      let body = '';
      if (k === 'trend' || k === 'ray' || k === 'arrow' || k === 'hline') body = cols + sep + wid;
      else if (k === 'rect') {
        const f = !!this._val('fill'), a = Math.round(this._val('alpha') * 100);
        body = cols + sep + wid + sep
          + `<div class="dt-seg dt-fillseg"><button data-fill="1" class="${f ? 'on' : ''}" title="方框填滿（顏色跟邊框一樣）">填滿</button><button data-fill="0" class="${f ? '' : 'on'}" title="方框只留邊框，不遮住 K 棒">透明</button></div>`
          + `<label class="dt-op ${f ? '' : 'dt-off'}" title="填滿的透明度">透明度 <input type="range" min="10" max="90" step="5" value="${a}" data-r="alpha"><b>${a}%</b></label>`;
      } else if (k === 'text') {
        const fs = this._val('fs');
        body = cols + sep + `<div class="dt-seg dt-fs" title="字級">${FONT_SIZES.map(z => `<button data-fs="${z}" class="${z === fs ? 'on' : ''}">${z}</button>`).join('')}</div>`
          + (this.sel && !this.editing ? `<button class="dt-act" data-act="edit" title="編輯文字內容">編輯</button>` : '');
      } else if (k === 'measure') {
        body = `<span class="dt-hint">紅底＝上漲・綠底＝下跌；可拖四個角調整範圍</span>`;
      } else if (k === 'vp') {
        const rows = this._val('rows'), a = Math.round(this._val('vpAlpha') * 100);
        body = `<label title="價格分成幾檔（12～60）">檔數 <select data-r="rows">${VP_ROWS.concat(VP_ROWS.indexOf(rows) < 0 ? [rows] : []).sort((x, y) => x - y).map(n => `<option value="${n}" ${n === rows ? 'selected' : ''}>${n}</option>`).join('')}</select></label>`
          + `<button class="dt-tg ${this._val('poc') ? 'on' : ''}" data-tg="poc" title="成交量最大的那一檔畫一條線">POC</button>`
          + `<button class="dt-tg ${this._val('va') ? 'on' : ''}" data-tg="va" title="價值區：從 POC 往外累積到 70% 的量；區外的長條變淡">價值區 70%</button>`
          + `<label title="長條透明度">透明度 <input type="range" min="10" max="100" step="5" value="${a}" data-r="vpAlpha"><b>${a}%</b></label>`;
      }
      const del = this.sel ? `${sep}<button class="dt-del" data-act="del" title="刪除這個圖形（Delete 鍵也可以）" aria-label="刪除">${'<svg viewBox="0 0 18 18">' + I.del + '</svg>'}</button>` : '';
      el.dataset.kind = k;
      el.innerHTML = `<span class="dt-pl">${esc(KINDS[k] || '')}${s ? '' : '<small style="font-weight:400;color:var(--ink-3)">・預設</small>'}</span>` + body + del;
      /* 位置：桌機放在左上角圖例正下方；手機（≤640）圖例本身就佔掉三行，再疊一條屬性列會把整個主圖上半部蓋掉，
         所以手機改放主圖底部（右下角是「重設縮放」，屬性列靠左，不會撞到）。*/
      const lg = this.kc.legendRect ? this.kc.legendRect() : null;
      let narrow = false; try { narrow = global.matchMedia('(max-width:820px)').matches; } catch (e) { /* 忽略 */ }
      const top = narrow ? Math.max(8, this._paneH() - el.offsetHeight - 10) : (lg ? lg.y + lg.h + 6 : 8);
      el.style.top = Math.round(top) + 'px';
    }
    _propClick(e) {
      const b = e.target.closest('button'); if (!b) return;
      e.stopPropagation();
      if (b.dataset.c) this._setProp('color', b.dataset.c);
      else if (b.dataset.w) this._setProp('w', +b.dataset.w);
      else if (b.dataset.fill) this._setProp('fill', b.dataset.fill === '1');
      else if (b.dataset.fs) this._setProp('fs', +b.dataset.fs);
      else if (b.dataset.tg) this._setProp(b.dataset.tg, !this._val(b.dataset.tg));
      else if (b.dataset.act === 'del' && this.sel) { this._remove(this.sel); return; }
      else if (b.dataset.act === 'edit' && this.sel && this.sel.kind === 'text') { this._editText(this.sel, false); return; }
      this._props();
    }
    _propInput(e, done) {
      const t = e.target, r = t.dataset && t.dataset.r; if (!r) return;
      if (r === 'rows') { if (done) { this._setProp('rows', +t.value); this._props(); } return; }
      const v = Math.round(+t.value) / 100;
      this._setProp(r, v, true);
      const lab = t.parentNode && t.parentNode.querySelector('b'); if (lab) lab.textContent = Math.round(v * 100) + '%';
    }
  }

  // ---------------------------------------------------------------- 左側工具列（industry.js 的 #drawBar 掛這個）
  /* api：{ tool, get: () => 目前的 Drawings 或 null, onTool(t), onStyle(style) }
     工具列上只剩工具本身（選取／線／箭頭／水平線／方框／文字／測量／成交量分佈｜橡皮擦／全部清除／復原），
     顏色、線寬、填滿這些「屬性」全部搬進圖上的屬性列 —— 以前「方框：填滿」是一顆離方框很遠的獨立鈕，
     Andy 2026-10-02 指出這樣很奇怪（第 4 項）。*/
  let BAR = null;
  function paintBar() {
    if (!BAR || !BAR.el.isConnected) return;
    BAR.el.querySelectorAll('.dtool[data-t]').forEach(b => b.classList.toggle('on', b.dataset.t === BAR.tool));
  }
  document.addEventListener('tw:drawtool', (e) => { if (BAR) { BAR.tool = e.detail.tool; if (BAR.api.onTool) BAR.api.onTool(BAR.tool); paintBar(); } });
  function mountBar(el, api) {
    injectCss();
    BAR = { el, api, tool: api.tool || 'cursor' };
    global.DrawTools._onStyle = api.onStyle || null;
    const btn = (t, extra) => `<button class="dtool ${t.k === BAR.tool ? 'on' : ''} ${extra || ''}" data-t="${t.k}" title="${esc(t.label)}${t.pts === 2 ? '（點起點、再點終點；按住 Shift ＝ 鎖水平／垂直）' : ''}" aria-label="${esc(t.label)}">
         <svg viewBox="0 0 18 18">${t.icon}</svg></button>`;
    el.innerHTML = TOOLS.filter(t => t.k !== 'erase').map(t => btn(t)).join('')
      + `<div class="dsep"></div>`
      + btn(TOOLS.find(t => t.k === 'erase'))
      + `<button class="dtool dt-danger" data-a="clear" title="全部清除（會先問一次）" aria-label="全部清除"><svg viewBox="0 0 18 18">${I.clear}</svg></button>`
      + `<button class="dtool" data-a="undo" title="復原上一步" aria-label="復原"><svg viewBox="0 0 18 18">${I.undo}</svg></button>`;
    /* 手機（≤760）工具列是橫排、在圖的正上方，右上角的「還原」小標（絕對定位在 .chartwrap 上）會蓋住方框那顆鈕
       （2026-10-02 390px 實測：點「方框」點到的是「還原」）。量工具列高度交給 CSS 把小標往下推。*/
    const wrap = el.parentElement;
    if (wrap && global.ResizeObserver) {
      if (el._dtRo) el._dtRo.disconnect();
      el._dtRo = new ResizeObserver(() => { wrap.style.setProperty('--dtbar-h', (el.offsetHeight || 0) + 'px'); });
      el._dtRo.observe(el);
    }
    el.querySelectorAll('.dtool[data-t]').forEach(b => b.onclick = () => {
      BAR.tool = b.dataset.t; if (api.onTool) api.onTool(BAR.tool);
      const d = api.get && api.get(); if (d) d.setTool(BAR.tool);
      paintBar();
    });
    el.querySelectorAll('.dtool[data-a]').forEach(b => b.onclick = (e) => {
      const d = api.get && api.get();
      if (b.dataset.a === 'undo') { if (d) d.undo(); return; }
      e.stopPropagation();
      openConfirm(el, b, d);
    });
  }
  function openConfirm(bar, anchor, d) {
    const old = bar.querySelector('.dt-confirm'); if (old) { old.remove(); return; }
    const n = d ? d.shapes.length : 0;
    const pop = document.createElement('div');
    pop.className = 'dt-confirm'; pop.setAttribute('role', 'dialog');
    let narrow = false; try { narrow = global.matchMedia('(max-width:760px)').matches; } catch (e) { /* 忽略 */ }
    if (!narrow) pop.style.top = (anchor.offsetTop || 0) + 'px';   // 桌機：貼在那顆鈕旁邊；手機：工具列正下方（CSS）
    pop.innerHTML = n
      ? `清除這檔、這個週期的<b>全部 ${n} 個圖形</b>？<div class="dt-cb"><button data-ok>全部清除</button><button data-no>取消</button></div>`
      : `這個週期還沒有畫任何東西。<div class="dt-cb"><button data-no>好</button></div>`;
    bar.appendChild(pop);
    const close = () => { pop.remove(); document.removeEventListener('pointerdown', out, true); };
    const out = (e) => { if (!pop.contains(e.target) && e.target !== anchor && !anchor.contains(e.target)) close(); };
    setTimeout(() => document.addEventListener('pointerdown', out, true), 0);
    pop.addEventListener('click', (e) => {
      e.stopPropagation();
      if (e.target.closest('[data-ok]')) { if (d) d.clear(); close(); }
      else if (e.target.closest('[data-no]')) close();
    });
  }

  global.DrawTools = { TOOLS, COLORS, WIDTHS, FONT_SIZES, VP_ROWS, STYLE, Drawings, mountBar, active: null, _onStyle: null, saveStyle };
})(window);
