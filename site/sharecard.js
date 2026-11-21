/* ============================================================================
   一鍵分享圖卡（site/sharecard.js）—— P-1107-05（docs/feature_proposals/weekly_2026-W45.md）
   ----------------------------------------------------------------------------
   做什麼：在總覽「強弱輪動」「昨日資金分流樹」「恐慌指數走勢」、資金流向「輪盤」、產業地圖「族群漲跌幅」
   的標題列加一顆「分享圖卡」鈕；按下去把那張圖套上統一圖卡版型（標題＋資料日期＋圖＋網站名稱與網址），
   讓使用者下載 PNG 或（手機）直接用系統分享丟給朋友。這是網站自己的擴散管道：圖卡上自帶網址。

   為什麼只做「大盤與族群層級」：提案的法遵守則——不提供分享個股買賣建議的圖卡；圖卡固定帶
   「資料日期＋僅供研究參考」一行；文字只陳述事實，不寫買賣建議。
   不放比比（2026-11-02 規定：社群貼文圖一律不放比比）。

   網址與流量：圖卡上的網址是 https://liguligu-puipui.com/?src=card#<該頁路由>。
   提案原寫 `#路由?src=card`，但本站路由吃 location.hash（帶 ? 會被當成路由的一部分），
   所以改放在 search 段；account.js 的 srcFromUrl 認得 ?src=card → 記成第一次來源「card」（land 事件），
   不必改 Worker：land 的細項（來源）是自由字串。每產生一張圖另外記 TwT('share.card', 動作.版型)。

   版型（Canvas 2D 自己合成，不依賴 DOM 截圖）：
     · 標題（可縮字級放進一行）、資料日期列、右上角標（非 Plus 才有）、圖（等比放進圖區）、頁尾一行「哩股哩股＋網址」。
     · 每個元素都量文字外框，兩兩不得相交、不得超出畫布；結果放在 TwShareCard.last（驗收讀它）。
     · 色彩跟著目前主題（淺色為主；深色主題輸出深色圖卡，因為圖本身的字色是跟主題走的）。
   尺寸：直式 1080×1350、橫式 1200×630（人人有）；方形 1080×1080、限動直式 1080×1920（Plus 以上，功能鍵 share.card.plus）。
   功能鍵：share.card（每日次數：訪客 3／註冊會員 5／Plus 50／Pro 不限）、share.card.plus（去角標、選尺寸）。
   手機：支援 navigator.share 帶檔案就直接分享圖，不支援就下載。
   ============================================================================ */
(function () {
  'use strict';
  const ORIGIN = 'https://liguligu-puipui.com/';
  const FONT = "'Noto Sans TC','PingFang TC','Microsoft JhengHei','Heiti TC',sans-serif";
  const SIZES = {
    portrait: { w: 1080, h: 1350, name: '直式', desc: '1080×1350', plus: false },
    land: { w: 1200, h: 630, name: '橫式', desc: '1200×630', plus: false },
    square: { w: 1080, h: 1080, name: 'IG 方形', desc: '1080×1080', plus: true },
    story: { w: 1080, h: 1920, name: '限動直式', desc: '1080×1920', plus: true }
  };
  const ORDER = ['portrait', 'land', 'square', 'story'];
  const q = (s, r) => (r || document).querySelector(s);
  const qa = (s, r) => Array.from((r || document).querySelectorAll(s));
  const vis = (e) => !!e && e.getClientRects().length > 0 && e.offsetWidth > 8 && e.offsetHeight > 8;
  const txt = (e) => (e ? String(e.textContent || '').replace(/\s+/g, ' ').trim() : '');

  /* 每個可分享的卡：card＝外框（up：往上找最近的祖先）、head＝按鈕要放進去的標題列（在 card 裡找）、
     fig＝要拍的圖（選擇器）、title＝圖卡標題（函式，現場讀畫面）。fig 還沒畫好、被收起 → 不放按鈕。 */
  const TARGETS = [
    { id: 'ov-rot', card: '#ovRotCard', head: '#ovRotHead', fig: '#ovRotCard .chart', title: () => '強弱輪動（價格相對大盤）' },
    { id: 'ov-flow', card: '#ovFlowCard', head: '#ovFlowHead', fig: '#ovFlowWrap', title: () => '昨日資金分流樹' },
    { id: 'ov-fear', card: '#ovFearCard', head: '.fz-hd', fig: '#ovFearFull',
      title: () => '恐慌指數走勢・' + (txt(q('#fzMkt button.on')) || '台股'),
      /* 圖例是 HTML（不在 canvas 裡），不補的話圖上幾條線各是誰就看不出來 → 圖卡自己畫一列圖例 */
      legend: () => qa('#fzLeg > *').map((e) => ({ c: (e.querySelector('i') && e.querySelector('i').style.getPropertyValue('--c')) || '', text: txt(e) })).filter((x) => x.text) },
    { id: 'flow-rot', card: '#rotClock', up: '.card', head: '.rotchead', fig: '#rotClock',
      title: () => (txt(q('#rotModeTitle')) || '強弱輪動') + (txt(q('#rotSub')) ? '・' + txt(q('#rotSub')) : '') },
    { id: 'grp', card: '#gpSec', head: '.gplive', fig: '#gpBar',
      title: () => {
        const h = q('#gpTitle'); if (!h) return '族群漲跌幅';
        const c = h.cloneNode(true); qa('.howbtn,small,.ticon', c).forEach((x) => x.remove());
        const t = txt(c).replace(/族群漲幅與占比$/, '');
        return (t || '族群') + '・族群漲跌幅';
      } }
  ];

  const S = { tgt: null, size: 'portrait', canvas: null, rep: null, dlg: null, opener: null, out: null };
  const A = () => window.App || null;
  const P = () => window.TwPerm || null;
  const plus = () => { try { return !P() || P().can('share.card.plus'); } catch (e) { return true; } };
  const dataDate = () => { try { return (A() && A().D && A().D.meta && A().D.meta.data_date) || ''; } catch (e) { return ''; } };
  const cssv = (n, fb) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || fb; } catch (e) { return fb; } };

  /* ---------------------------------------------------------------- 找圖 */
  function cardOf(t) {
    const e = q(t.card);
    return e && t.up ? (e.closest(t.up) || e) : e;
  }
  const figEl = (t) => { const e = q(t.fig); return e && vis(e) ? e : null; };
  function figReady(t) {
    const e = figEl(t); if (!e) return false;
    const c = cardOf(t);
    if (c && c.querySelector('.isempty')) return false;
    return !!(e.querySelector('canvas,svg') || e.tagName === 'CANVAS');
  }

  /* 把一塊區域拍成一張 canvas：ECharts 實例用 getDataURL（解析度高），其餘 canvas／svg 依位置疊上去。 */
  const loadImg = (src) => new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = src; });
  async function grab(el, bg) {
    const box = el.getBoundingClientRect();
    const R = 2;
    const cv = document.createElement('canvas');
    cv.width = Math.max(2, Math.round(box.width * R)); cv.height = Math.max(2, Math.round(box.height * R));
    const g = cv.getContext('2d');
    g.fillStyle = bg; g.fillRect(0, 0, cv.width, cv.height);
    const items = [];
    const ecDoms = qa('[_echarts_instance_]', el).concat(el.hasAttribute('_echarts_instance_') ? [el] : []);
    ecDoms.forEach((d) => {
      const inst = window.echarts && window.echarts.getInstanceByDom(d);
      if (inst && vis(d)) items.push({ dom: d, kind: 'ec', inst });
    });
    qa('canvas,svg', el).forEach((d) => {
      if (!vis(d) || ecDoms.some((e) => e.contains(d))) return;
      if (d.closest('button,.howbtn')) return;
      items.push({ dom: d, kind: d.tagName.toLowerCase() === 'canvas' ? 'cv' : 'svg' });
    });
    items.sort((a, b) => (a.dom.compareDocumentPosition(b.dom) & 4 ? -1 : 1));
    for (const it of items) {
      const r = it.dom.getBoundingClientRect();
      const x = (r.left - box.left) * R, y = (r.top - box.top) * R, w = r.width * R, h = r.height * R;
      try {
        if (it.kind === 'ec') {
          const im = await loadImg(it.inst.getDataURL({ type: 'png', pixelRatio: R, backgroundColor: bg }));
          if (im) g.drawImage(im, x, y, w, h);
        } else if (it.kind === 'cv') {
          g.drawImage(it.dom, x, y, w, h);
        } else {
          const c = it.dom.cloneNode(true);
          c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
          c.setAttribute('width', r.width); c.setAttribute('height', r.height);
          const im = await loadImg('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(c)));
          if (im) g.drawImage(im, x, y, w, h);
        }
      } catch (e) { /* 被污染的 canvas 等：略過這一層，不讓整張圖卡失敗 */ }
    }
    return { cv, w: box.width, h: box.height, n: items.length };
  }

  /* ---------------------------------------------------------------- 版型 */
  const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  /* 先縮字；縮到下限還放不下就截尾加「…」（寧可少幾個字，也不能壓到旁邊的元素）。回傳實際畫的字串 */
  function shrink(g, text, weight, size, maxW, minSize, keep) {
    let s = size;
    for (; ; s -= 1) {
      g.font = `${weight} ${s}px ${FONT}`;
      if (g.measureText(text).width <= maxW || s <= minSize) break;
    }
    let t = text;
    if (!keep && g.measureText(t).width > maxW) {
      while (t.length > 1 && g.measureText(t + '…').width > maxW) t = t.slice(0, -1);
      t += '…';
    }
    return { s, w: g.measureText(t).width, t };
  }
  const routeOf = () => { const h = location.hash || '#overview'; return h === '#' ? '#overview' : h; };
  const cardUrl = () => ORIGIN + '?src=card' + routeOf();
  const rr = (g, x, y, w, h, r) => { g.beginPath(); if (g.roundRect) g.roundRect(x, y, w, h, r); else g.rect(x, y, w, h); };

  /* ECharts 圖以目標尺寸重新渲染：離屏容器寬高＝內容區 ÷ k，pixelRatio＝2k，所以字級在圖卡上約放大 k 倍（k≈2.2：12px 字→26px），
     而且版面（格線、軸、圖例）是依圖卡內容區重新排的，不是把小圖拉大。
     輸出排除互動零件：dataZoom 拉Bar、toolbox、提示框一律不畫（拉Bar 拿掉後把它佔的下緣空間還給最底下那格圖）。
     這個元素裡不是剛好一個 ECharts 實例（例如分流樹是自繪 canvas）→ 回傳 null，由 grab 等比縮放。 */
  async function rerender(el, bg, cw, ch, land) {
    if (!el || !window.echarts) return null;
    const doms = qa('[_echarts_instance_]', el).concat(el.hasAttribute('_echarts_instance_') ? [el] : []);
    if (doms.length !== 1) return null;
    const inst = window.echarts.getInstanceByDom(doms[0]);
    if (!inst) return null;
    const r0 = el.getBoundingClientRect(), r1 = doms[0].getBoundingClientRect();
    if (r1.width < r0.width * 0.85 || r1.height < r0.height * 0.85) return null;   // 容器裡還有別的東西（圖例、表格），不當單一圖處理
    const k = Math.max(1, Math.min(2.2, ch / (land ? 200 : 300)));
    const w = Math.round(cw / k), h = Math.round(ch / k);
    const host = document.createElement('div');
    host.style.cssText = `position:fixed;left:-99999px;top:0;width:${w}px;height:${h}px;pointer-events:none;`;
    document.body.appendChild(host);
    let c2 = null;
    try {
      /* JSON 化會丟掉函式（formatter、custom renderItem），所以改用淺拷貝保留函式，只動要改的欄位 */
      const src = inst.getOption();
      /* custom／graphic（輪盤的圓、象限底色）是照「原容器大小」算好像素位置的，換尺寸重畫會被切掉 → 這種圖不重新渲染，改等比縮放（向量解析度 2 倍拍下來再放大，不糊） */
      if ((src.series || []).some((x) => x && x.type === 'custom') || (Array.isArray(src.graphic) && src.graphic.length)) return null;
      const o = Object.assign({}, src);
      let freed = 0;
      if (Array.isArray(o.dataZoom)) {
        o.dataZoom.filter((z) => z && z.type === 'slider').forEach((z) => { freed = Math.max(freed, (+z.height || 30) + (+z.bottom || 0)); });
        o.dataZoom = o.dataZoom.filter((z) => !(z && z.type === 'slider'));
      }
      /* 格線是「top＋固定 height（px）」排的圖（恐慌指數兩格）：容器換了高度，格線不會跟著長 → 依新容器高度把每格的 top／height 等比放大，
         下緣留給 x 軸字（拉Bar 佔的空間還給它，但至少 34px 才放得下日期字）。bottom 型（百分比）的圖本來就會跟容器伸縮，不動。 */
      if (Array.isArray(o.grid) && o.grid.length && o.grid.every((gd) => gd && gd.height != null && isFinite(+gd.height) && isFinite(+gd.top) && (gd.bottom == null || gd.bottom === 'auto'))) {
        const G = Math.max(...o.grid.map((gd) => +gd.top + +gd.height));
        const below0 = Math.max(0, r1.height - G);
        const nb = freed ? 36 : Math.max(Math.min(below0, 60), 30);
        const fv = Math.max(0.3, (h - nb) / G);
        o.grid = o.grid.map((gd) => Object.assign({}, gd, { top: +gd.top * fv, height: +gd.height * fv }));
      }
      delete o.toolbox; o.tooltip = { show: false }; o.animation = false; o.backgroundColor = bg;
      if (Array.isArray(o.series)) o.series = o.series.map((x) => Object.assign({}, x, { animation: false }));
      c2 = window.echarts.init(host, null, { renderer: 'canvas', width: w, height: h });
      c2.setOption(o, true);
      const url = c2.getDataURL({ type: 'png', pixelRatio: 2 * k, backgroundColor: bg });
      const im = await loadImg(url);
      if (!im) return null;
      const cv = document.createElement('canvas'); cv.width = Math.round(cw * 2); cv.height = Math.round(ch * 2);
      cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height);
      return { cv, k, slider: (o.dataZoom || []).filter((z) => z && z.type === 'slider').length, axisPx: +(k * Math.min(...[].concat(o.xAxis || [], o.yAxis || []).filter((a) => a && a.show !== false && !(a.axisLabel && a.axisLabel.show === false)).map((a) => +((a.axisLabel || {}).fontSize) || 12))).toFixed(1) };
    } catch (e) { return null; } finally { try { if (c2) c2.dispose(); } catch (e) { /* 略 */ } host.remove(); }
  }

  async function compose(t, sizeKey) {
    const sz = SIZES[sizeKey] || SIZES.portrait;
    const W = sz.w, H = sz.h, land = W > H * 1.5;
    const isPlus = plus();
    const dark = (document.documentElement.getAttribute('data-theme') || 'dark') !== 'light';
    const bg = cssv('--bg', dark ? '#0e1830' : '#F2EFE8');
    const panel = cssv('--panel', dark ? '#142142' : '#ffffff');
    const ink = cssv('--ink', dark ? '#fbfaf6' : '#14213D');
    const ink3 = cssv('--ink-3', dark ? '#9ba8c4' : '#576175');
    const line = cssv('--line-2', dark ? '#3b4f7f' : '#D6D2C8');

    const figNode = figEl(t);

    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const g = cv.getContext('2d');
    g.textBaseline = 'top';
    g.fillStyle = bg; g.fillRect(0, 0, W, H);

    const m = Math.round(W * (land ? 0.04 : 0.05));
    const boxes = [];
    const add = (name, x, y, w, h) => { const b = { name, x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) }; boxes.push(b); return b; };

    // 角標（非 Plus）：右上角的小膠囊，網址當浮水印
    let badgeW = 0;
    const badgeText = 'liguligu-puipui.com';
    const bs = land ? 20 : 24;
    if (!isPlus) { g.font = `600 ${bs}px ${FONT}`; badgeW = g.measureText(badgeText).width + bs * 1.4; }
    // 標題（一行，必要時縮字）
    const titleMax = W - 2 * m - (badgeW ? badgeW + m * 0.5 : 0);
    const ts = shrink(g, t.title(), 700, land ? 44 : 56, titleMax, 26);
    const title = ts.t;
    const tb = add('title', m, m, ts.w, ts.s * 1.25);
    g.fillStyle = ink; g.font = `700 ${ts.s}px ${FONT}`; g.fillText(title, tb.x, tb.y);
    if (!isPlus) {
      const bh = bs * 1.9, bx = W - m - badgeW, by = tb.y + (tb.h - bh) / 2;
      const bb = add('badge', bx, Math.max(m * 0.4, by), badgeW, bh);
      g.fillStyle = panel; g.strokeStyle = line; g.lineWidth = 2;
      rr(g, bb.x, bb.y, bb.w, bb.h, bb.h / 2); g.fill(); g.stroke();
      g.fillStyle = ink3; g.font = `600 ${bs}px ${FONT}`; g.textBaseline = 'middle';
      g.fillText(badgeText, bb.x + bs * 0.7, bb.y + bb.h / 2 + 1); g.textBaseline = 'top';
    }
    // 資料日期列
    const dd = dataDate();
    const dateText0 = (dd ? '資料日期 ' + dd : '資料日期 —') + '・僅供研究參考';
    const ds = shrink(g, dateText0, 500, land ? 22 : 28, W - 2 * m, 16);
    const dateText = ds.t;
    const db = add('date', m, tb.y + tb.h + (land ? 6 : 10), ds.w, ds.s * 1.25);
    g.fillStyle = ink3; g.font = `500 ${ds.s}px ${FONT}`; g.fillText(dateText, db.x, db.y);

    // 圖例列（有 legend 的圖才有）：色點＋名稱，一行放不下就縮字
    let lgb = null;
    let lg = t.legend ? t.legend() : [];
    if (lg.length) {
      const dot = land ? 14 : 18, gp2 = land ? 10 : 14, tx = land ? 20 : 24;
      const widthAt = (fs) => { g.font = `500 ${fs}px ${FONT}`; return lg.reduce((a, x) => a + (x.c ? dot + 6 : 0) + g.measureText(x.text).width + gp2, 0) - gp2; };
      let fs = tx; while (fs > 14 && widthAt(fs) > W - 2 * m) fs -= 1;
      while (lg.length > 1 && widthAt(fs) > W - 2 * m) lg = lg.slice(0, -1);   // 縮到 14px 還放不下：從尾端少畫幾項
      const lw = widthAt(fs);
      lgb = add('legend', m, db.y + db.h + (land ? 8 : 12), lw, Math.max(fs, dot) * 1.25);
      let x = lgb.x; g.font = `500 ${fs}px ${FONT}`; g.textBaseline = 'middle';
      lg.forEach((it) => {
        const cy = lgb.y + lgb.h / 2;
        if (it.c) { g.fillStyle = it.c; g.beginPath(); g.arc(x + dot / 2, cy, dot / 2, 0, 6.2832); g.fill(); x += dot + 6; }
        g.fillStyle = ink3; g.fillText(it.text, x, cy + 1); x += g.measureText(it.text).width + gp2;
      });
      g.textBaseline = 'top';
    }
    const headBot = (lgb || db).y + (lgb || db).h;

    // 頁尾：哩股哩股＋網址（一行）
    const url = cardUrl();
    const nameText = '哩股哩股';
    const fs0 = land ? 24 : 30;
    g.font = `700 ${fs0}px ${FONT}`;
    const nameW = g.measureText(nameText).width;
    const gap = fs0 * 0.8;
    const us = shrink(g, url, 500, fs0, W - 2 * m - nameW - gap, 12, true);
    const fh = Math.max(fs0, us.s) * 1.25;
    const fy = H - m - fh;
    const nb = add('footerName', m, fy, nameW, fh);
    g.fillStyle = ink; g.font = `700 ${fs0}px ${FONT}`; g.fillText(nameText, nb.x, nb.y + (fh - fs0 * 1.25) / 2);
    const ub = add('footerUrl', m + nameW + gap, fy, us.w, fh);
    g.fillStyle = ink3; g.font = `500 ${us.s}px ${FONT}`; g.fillText(url, ub.x, ub.y + (fh - us.s * 1.25) / 2);
    const lineY = fy - m * 0.35;
    g.strokeStyle = line; g.lineWidth = 2; g.beginPath(); g.moveTo(m, lineY); g.lineTo(W - m, lineY); g.stroke();

    // 圖：填滿標題列與頁尾線之間的整個內容區（上下留白 ≤ 24px）。
    // ECharts 圖：在離屏容器「以目標尺寸重新渲染」（不是把像素圖放大），字級保持清楚；其他 canvas／svg 圖才等比縮放。
    const topY = headBot + (land ? 10 : 20), botY = lineY - (land ? 10 : 20);
    const aw = W - 2 * m, ah = botY - topY, pad = land ? 8 : 12;
    const area = aw * ah;
    let pb, figN = 0, mode = 'scale', kk = 1, sc = 1, drawn = 0, extra = { slider: 0, axisPx: 0 };
    const rer = await rerender(figNode, panel, (aw - 2 * pad), (ah - 2 * pad), land);
    if (rer) {
      pb = add('figure', m, topY, aw, ah);
      g.fillStyle = panel; g.strokeStyle = line; g.lineWidth = 2; rr(g, pb.x, pb.y, pb.w, pb.h, 16); g.fill(); g.stroke();
      g.drawImage(rer.cv, pb.x + pad, pb.y + pad, aw - 2 * pad, ah - 2 * pad);
      figN = 1; mode = 'rerender'; kk = rer.k; extra = { slider: rer.slider, axisPx: rer.axisPx }; drawn = (aw - 2 * pad) * (ah - 2 * pad);
    } else {
      const fig = await grab(figNode, panel);
      sc = Math.min((aw - 2 * pad) / fig.w, (ah - 2 * pad) / fig.h, 2.2);
      const fw = fig.w * sc, fh2 = fig.h * sc;
      // 圖比內容區矮（寬扁、或接近方形的圖等比縮放後會留空）：面板貼著圖，標題區連同面板一起在「上邊緣與頁尾線之間」置中，
      // 這樣標題到圖之間不會開一大片空白（空白分給最上緣與圖下方，各一半）
      const ph = fh2 + 2 * pad, left = Math.max(0, ah - ph), dy = left > 40 ? Math.round(left / 2) : 0;
      if (dy) {
        const tmp = document.createElement('canvas'); tmp.width = W; tmp.height = Math.ceil(topY); tmp.getContext('2d').drawImage(cv, 0, 0);
        g.fillStyle = bg; g.fillRect(0, 0, W, Math.ceil(topY)); g.drawImage(tmp, 0, dy);
        boxes.forEach((bx) => { if (bx.name !== 'footerName' && bx.name !== 'footerUrl') bx.y += dy; });
      }
      pb = add('figure', m, topY + dy, aw, ph);
      g.fillStyle = panel; g.strokeStyle = line; g.lineWidth = 2; rr(g, pb.x, pb.y, pb.w, pb.h, 16); g.fill(); g.stroke();
      g.imageSmoothingQuality = 'high';
      g.drawImage(fig.cv, pb.x + (aw - fw) / 2, pb.y + pad, fw, fh2);
      figN = fig.n; drawn = fw * fh2;
    }
    const fill = +(drawn / area).toFixed(3);

    // 重疊與出界檢查（圖卡的版型契約；驗收也讀這份）
    const overlaps = [];
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) if (hit(boxes[i], boxes[j])) overlaps.push(boxes[i].name + '×' + boxes[j].name);
    const outside = boxes.filter((b) => b.x < 0 || b.y < 0 || b.x + b.w > W + 0.5 || b.y + b.h > H + 0.5).map((b) => b.name);
    return { cv, rep: { size: sizeKey, W, H, boxes, overlaps, outside, url, title, date: dateText, badge: !isPlus, figN, theme: dark ? 'dark' : 'light', plus: isPlus, figScale: +sc.toFixed(2), mode, k: kk, fill, slider: extra.slider, axisPx: extra.axisPx, area: { x: m, y: topY, w: aw, h: ah } } };
  }

  /* ---------------------------------------------------------------- 輸出 */
  const fname = (t, size) => `liguligu-${t.id}-${(dataDate() || 'card').replace(/-/g, '')}-${size}.png`;
  const toBlob = (cv) => new Promise((res) => cv.toBlob((b) => res(b), 'image/png'));
  function download(blob, name) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.rel = 'noopener';
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  }
  function trk(ev) { try { if (window.TwT) window.TwT('share.card', ev + '.' + S.size); } catch (e) { /* 統計失敗不影響分享 */ } }
  async function shareOrSave(viaShare) {
    if (!S.canvas || !S.tgt) return 'none';
    const blob = await toBlob(S.canvas);
    const name = fname(S.tgt, S.size);
    S.out = { name, bytes: blob ? blob.size : 0, via: 'download', w: S.canvas.width, h: S.canvas.height };
    if (viaShare) {
      try {
        const f = new File([blob], name, { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [f] }) && navigator.share) {
          S.out.via = 'share';
          await navigator.share({ files: [f], title: S.rep.title, text: S.rep.title + '・哩股哩股', url: cardUrl() });
          trk('share'); return 'share';
        }
      } catch (e) { if (e && e.name === 'AbortError') return 'abort'; /* 其他錯誤退回下載 */ }
    }
    S.out.via = 'download';
    download(blob, name); trk('download');
    return 'download';
  }

  /* ---------------------------------------------------------------- 視窗 */
  const canShareFiles = () => {
    try { return !!navigator.share && !!navigator.canShare && navigator.canShare({ files: [new File([new Blob(['x'])], 'a.png', { type: 'image/png' })] }); } catch (e) { return false; }
  };
  function onKey(e) { if (e.key === 'Escape') { e.stopPropagation(); closeDlg(); } }
  function closeDlg() {
    if (!S.dlg) return;
    S.dlg.remove(); S.dlg = null; document.removeEventListener('keydown', onKey, true);
    if (S.opener && S.opener.isConnected) { try { S.opener.focus(); } catch (e) { /* 略 */ } }
  }
  async function render(sizeKey) {
    if (!S.dlg) return;
    const box = q('.scPrev', S.dlg), note = q('.scNote', S.dlg);
    box.setAttribute('aria-busy', 'true');
    let r;
    try { r = await compose(S.tgt, sizeKey); } catch (e) { box.removeAttribute('aria-busy'); note.textContent = '這張圖暫時無法輸出，請稍後再試'; return; }
    if (!S.dlg) return;
    S.size = sizeKey; S.canvas = r.cv; S.rep = r.rep; window.TwShareCard.last = r.rep;
    r.cv.className = 'scCv'; r.cv.setAttribute('role', 'img'); r.cv.setAttribute('aria-label', '圖卡預覽：' + r.rep.title);
    box.innerHTML = ''; box.appendChild(r.cv); box.removeAttribute('aria-busy');
    qa('.scSz button', S.dlg).forEach((b) => { const on = b.dataset.sz === sizeKey; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
    note.textContent = `${SIZES[sizeKey].name} ${SIZES[sizeKey].desc}${r.rep.badge ? '・Plus 以上可去角標、選更多尺寸' : ''}`;
  }
  function openDlg(t, opener) {
    closeDlg();
    S.tgt = t; S.opener = opener; S.out = null;
    const d = document.createElement('div');
    d.className = 'scDlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '分享圖卡');
    const isP = plus(), mob = canShareFiles();
    d.innerHTML = `<div class="scBox"><div class="scHd"><b>分享圖卡</b><button type="button" class="scX" aria-label="關閉">✕</button></div>
      <div class="scSz" role="group" aria-label="尺寸">${ORDER.map((k) => {
        const z = SIZES[k], lock = z.plus && !isP;
        return `<button type="button" data-sz="${k}" aria-pressed="false"${lock ? ' disabled title="Plus 以上可選"' : ''}>${z.name}<small>${z.desc}${lock ? '・Plus' : ''}</small></button>`;
      }).join('')}</div>
      <div class="scPrev" aria-live="polite"><span class="muted">產生中…</span></div>
      <div class="scNote muted"></div>
      <div class="scAct">${mob ? '<button type="button" class="btn scGo" data-go="share">分享圖片</button><button type="button" class="btn small" data-go="save">下載 PNG</button>'
        : '<button type="button" class="btn scGo" data-go="save">下載 PNG</button>'}</div></div>`;
    document.body.appendChild(d); S.dlg = d;
    d.addEventListener('click', (e) => {
      if (e.target === d || e.target.closest('.scX')) { closeDlg(); return; }
      const z = e.target.closest('.scSz button'); if (z && !z.disabled) { render(z.dataset.sz); return; }
      const go = e.target.closest('[data-go]'); if (go) shareOrSave(go.dataset.go === 'share');
    });
    document.addEventListener('keydown', onKey, true);
    const first = q('.scX', d); if (first) first.focus();
    // 寬扁的圖（恐慌指數走勢）直式會縮成一條，預設改橫式；其他預設直式。使用者在視窗裡自己切的尺寸照舊
    const fe = figEl(t), r0 = fe ? fe.getBoundingClientRect() : null;
    // ECharts 圖會依內容區重新渲染，直式一律填得滿；只有寬扁的非 ECharts 圖（等比縮放會留白）才預設橫式
    const hasEc = !!(fe && (fe.hasAttribute('_echarts_instance_') || fe.querySelector('[_echarts_instance_]')));
    S.size = !hasEc && r0 && r0.width / Math.max(1, r0.height) > 1.5 ? 'land' : 'portrait';
    render(S.size);
  }

  /* ---------------------------------------------------------------- 按鈕 */
  const ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M12 3v12"/><path d="M8 7l4-4 4 4"/></svg>';
  function onBtn(t, btn) {
    // 每產生一張圖卡算一次（切尺寸、下載不重算）；用完時按鈕已被 quota.js 反灰擋掉，這裡再問一次保險
    if (window.TwQuota && window.TwQuota.use && !window.TwQuota.use('share.card', btn)) return;
    try { if (window.TwT) window.TwT('share.card', 'open.' + t.id); } catch (e) { /* 略 */ }
    openDlg(t, btn);
  }
  function ensure() {
    TARGETS.forEach((t) => {
      const cardEl = cardOf(t);
      const head = cardEl && q(t.head, cardEl);
      const old = qa('.scBtn[data-sct="' + t.id + '"]');
      const ok = !!head && vis(cardEl) && figReady(t);
      if (!ok) { old.forEach((b) => b.remove()); return; }
      if (old.some((b) => head.contains(b))) return;
      old.forEach((b) => b.remove());
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'btn small scBtn'; b.dataset.sct = t.id;
      b.setAttribute('aria-label', '分享圖卡：' + t.title()); b.title = '產生一張自帶網址的分享圖卡（PNG）';
      b.innerHTML = ICON + '<span>分享圖卡</span>';
      b.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); onBtn(t, b); });
      head.appendChild(b);
    });
  }
  let tm = 0;
  const sched = () => { clearTimeout(tm); tm = setTimeout(ensure, 300); };
  function init() {
    ensure();
    try { new MutationObserver(sched).observe(document.body, { childList: true, subtree: true }); } catch (e) { setInterval(ensure, 2000); }
    window.addEventListener('hashchange', sched);
    /* 手機（html.m4）切子分頁只是換 class／hidden，不是新增節點，MutationObserver(childList) 看不到 → 再加一個低頻輪詢（5 個目標、每次只做幾個選擇器查詢，頁面藏起來時不跑） */
    setInterval(() => { if (!document.hidden) ensure(); }, 1500);
  }
  window.TwShareCard = { compose, ensure, open: (id) => { const t = TARGETS.find((x) => x.id === id); if (t) openDlg(t, null); }, targets: TARGETS.map((t) => t.id), sizes: SIZES, cardUrl, last: null, state: S };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
