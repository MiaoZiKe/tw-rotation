/* ============================================================================
   市場明細的兩頁期貨籌碼（Andy 2026-10-20：「第三 台指期三大法人未平倉」「第四 微台指散戶多空比」）
     #market/futoi    台指期三大法人未平倉（資料 data/fut_oi.json）
     #market/retail   微台指散戶多空比（資料 data/retail_ratio.json）
   只參考別站的「內容與版面」，樣式與文字都是自己的；台股慣例紅＝多／漲、綠＝空／跌（別站顏色是反的，照我們的）。
   接點：app.js 的 drawMarket 在 kind 是這兩頁時呼叫 window.TwFut.draw(kind, body, title)，其餘全在這支檔。
   資料不存在（還沒上線、或 404）→ 卡片寫「資料準備中」，不報錯。
   連動（style_guide §18）：圖、表、大數字同一個「焦點日期」——滑過一起亮、點一下鎖定、再點同一天或點圖外取消；
   時間序列沒有「一個扇區」可以變淡，所以圖上是垂直標示線（鎖定＝實線、滑過＝虛線），表格那列 .hl／.sel，大數字換成那一天。
   自動解讀的規則寫在 docs/futpages_rules.md（只陳述資料，不給買賣建議）。
   免付費牆：功能開關歸 features.js／plan_presets，這兩頁先全開放（Andy：不自己做 Pro 鎖）。
   驗收：scripts/uitest_sections/20261020_futpages.py。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const isM = () => document.documentElement.classList.contains('m4') || window.matchMedia('(max-width:640px)').matches;
  const nf = (v) => (v == null || Number.isNaN(v) ? '—' : Math.round(v).toLocaleString('zh-TW'));
  const sg = (v) => (v == null || Number.isNaN(v) ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(Math.round(v)).toLocaleString('zh-TW'));
  const sgd = (v, d) => (v == null || Number.isNaN(v) ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d));
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');

  /* 全站一次性樣式：期貨籌碼／三大法人／信用交易三頁拿掉卡內重複標題（頁首已有）；
     電腦版子頁在側欄、#mktSeg2 本來就藏起來 → 整條標題列收掉；沒有側欄的寬度保留分頁鈕那半邊。 */
  if (!document.getElementById('fpGlobalCss')) {
    const g = document.createElement('style'); g.id = 'fpGlobalCss';
    /* 配色 token（Andy 10-20）：三大法人／期貨籌碼／信用交易同一套；JS 用 tok() 讀成實色給 ECharts */
    g.textContent = ':root{--c-foreign:#2563EB;--c-trust:#F97316;--c-dealer:#A855F7;--c-retail:#14B8A6;--c-tx:#0F172A;--c-mgn-ratio:#E11D48;--c-mgn-bal:#0EA5E9;--c-short:#F59E0B}:root:not([data-theme="light"]){--c-tx:#E2E8F0}'
      + '#v-market .card.mkt-notitle .mkthead>h3{display:none!important}:root.l4 #v-market .card.mkt-notitle>.mkthead{display:none}';
    document.head.appendChild(g);
  }

  /* 台股慣例：紅＝多／漲、綠＝空／跌。 */
  /* 配色（Andy 10-20，三大法人那組同一套）：外資藍、投信橘、自營紫、散戶青綠；加權指數線淺色深藍黑／深色淺灰白，線寬 2。
     紅綠只留給數字（買超賣超、漲跌）與個股長條，這裡的線與柱不用。 */
  const tok = (n, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d; } catch (e) { return d; } };
  const PAL = { get f() { return tok('--c-foreign', '#2563EB'); }, get t() { return tok('--c-trust', '#F97316'); }, get d() { return tok('--c-dealer', '#A855F7'); }, get r() { return tok('--c-retail', '#14B8A6'); } };
  /* Andy 10-20「直條實色不漸層」：app.js 的 BAR.apply 會把所有長條的 #hex／rgb 色換成同色漸層（10-07 全站規矩），
     但它只認 #hex／rgb()／rgba()，認不得的色字串原樣保留 → 把 token 色轉成等價的 hsl() 字串，這張圖的柱子就維持實色（不動全站規矩）。 */
  const solidHsl = (hex) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex); if (!m) return hex;
    const r = parseInt(m[1].slice(0, 2), 16) / 255, g = parseInt(m[1].slice(2, 4), 16) / 255, b = parseInt(m[1].slice(4), 16) / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    let h = 0, sat = 0;
    if (d) { sat = d / (1 - Math.abs(2 * l - 1)); h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h = (h * 60 + 360) % 360; }
    return `hsl(${Math.round(h)},${Math.round(sat * 100)}%,${Math.round(l * 100)}%)`;
  };
  const isDark = () => document.documentElement.getAttribute('data-theme') !== 'light';
  const txColor = () => tok('--c-tx', isDark() ? '#E2E8F0' : '#0F172A');
  const col = () => { const c = (A() && A().CH) || {}; return { up: c.up || '#ff4d6d', down: c.down || '#2ee59d', ink2: c.ink2 || '#a9b6d6', ink3: c.ink3 || '#6f7ea3', ink: c.ink || '#e8eeff', cyan: c.cyan || '#3ee0ff', amber: c.amber || '#ffb454', violet: c.violet || '#8b7bff', line: c.line || '#1e2a48' }; };

  /* 期間：futoi 以月為單位；retail 的「2 週」以天算。m＝月數、d＝天數、0＝全部 */
  const PERIODS = {
    futoi: { def: '6m', list: [['1m', '1月', 1, 0], ['3m', '3月', 3, 0], ['6m', '6月', 6, 0], ['1y', '1年', 12, 0], ['3y', '3年', 36, 0], ['5y', '5年', 60, 0], ['all', '全部', 0, 0]] },
    retail: { def: '2w', list: [['2w', '2週', 0, 14], ['3m', '3月', 3, 0], ['6m', '6月', 6, 0], ['1y', '1年', 12, 0], ['3y', '3年', 36, 0], ['5y', '5年', 60, 0], ['all', '全部', 0, 0]] },
  };
  const cutoffOf = (last, p) => {
    const d = new Date(last + 'T00:00:00Z');
    if (p[3]) d.setUTCDate(d.getUTCDate() - p[3]); else d.setUTCMonth(d.getUTCMonth() - p[2]);
    return d.toISOString().slice(0, 10);
  };

  /* ---------------- 資料整理：合約欄位陣列 → 由舊到新的列物件 ---------------- */
  function normalize(kind, raw) {
    if (!raw || !Array.isArray(raw.dates) || !raw.dates.length) return null;
    const n = raw.dates.length, rev = raw.order === 'desc';
    const at = (arr, i) => (arr && arr[i] != null ? Number(arr[i]) : null);
    const rows = [];
    for (let i = 0; i < n; i++) {
      const j = rev ? n - 1 - i : i;
      const r = { date: raw.dates[j], tx: at(raw.taiex, j) };
      if (kind === 'futoi') {
        ['foreign', 'trust', 'dealer'].forEach((k, q) => {
          const o = raw[k] || {}, p = 'fts'[q] === 'f' ? 'f' : k === 'trust' ? 't' : 'd';
          r[p + 'l'] = at(o.long, j); r[p + 's'] = at(o.short, j);
          r[p + 'n'] = o.net && o.net[j] != null ? Number(o.net[j]) : (r[p + 'l'] != null && r[p + 's'] != null ? r[p + 'l'] - r[p + 's'] : null);
        });
        r.sum = (r.fn == null && r.tn == null && r.dn == null) ? null : (r.fn || 0) + (r.tn || 0) + (r.dn || 0);
      } else {
        r.tot = at(raw.total_oi, j); r.l = at(raw.retail_long, j); r.s = at(raw.retail_short, j);
        r.n = raw.retail_net && raw.retail_net[j] != null ? Number(raw.retail_net[j]) : (r.l != null && r.s != null ? r.l - r.s : null);
        r.p = raw.ratio_pct && raw.ratio_pct[j] != null ? Number(raw.ratio_pct[j]) : (r.tot ? r.n / r.tot * 100 : null);
      }
      rows.push(r);
    }
    return rows;
  }

  /* ---------------- 自動解讀（規則見 docs/futpages_rules.md） ---------------- */
  const streakOf = (rows, key) => {   // 從最新一天往回數：淨值同號連續幾天（0 或缺值就停）
    const last = rows[rows.length - 1]; if (!last || !last[key]) return { n: 0, sign: 0 };
    const sign = last[key] > 0 ? 1 : -1; let n = 0;
    for (let i = rows.length - 1; i >= 0 && rows[i][key] != null && Math.sign(rows[i][key]) === sign; i--) n++;
    return { n, sign };
  };
  function readFut(all, view) {
    const last = all[all.length - 1], prev = all[all.length - 2], out = [];
    [['f', '外資'], ['t', '投信'], ['d', '自營商']].forEach(([p, nm]) => {
      const st = streakOf(all, p + 'n'), v = last[p + 'n'];
      if (!st.n) { out.push({ tag: '持平', c: 'flat', t: `${nm}台指期淨部位為 ${nf(v)} 口（多空相抵）` }); return; }
      out.push({ tag: st.sign > 0 ? '淨多' : '淨空', c: st.sign > 0 ? 'up' : 'down',
        t: `連續 ${st.n} 日${nm}台指期淨部位偏${st.sign > 0 ? '多' : '空'}（目前淨${st.sign > 0 ? '多' : '空'} ${nf(Math.abs(v))} 口）` });
    });
    if (prev && last.fn != null && prev.fn != null) {
      const d = last.fn - prev.fn;
      out.push({ tag: '變化', c: 'flat', t: `外資淨部位較前一交易日${d > 0 ? '增加' : d < 0 ? '減少' : '持平'}${d ? ' ' + nf(Math.abs(d)) + ' 口' : ''}（${sg(prev.fn)} → ${sg(last.fn)} 口）` });
    }
    const a = view[0];
    if (a && a.fn != null && view.length > 1) out.push({ tag: '期間', c: 'flat', t: `${a.date.slice(5)} 至 ${last.date.slice(5)}，外資淨部位由 ${sg(a.fn)} 變為 ${sg(last.fn)} 口` });
    const tot = (last.fn || 0) + (last.tn || 0) + (last.dn || 0);
    out.push({ tag: '合計', c: cls(tot), t: `三大法人合計淨部位 ${sg(tot)} 口（${tot > 0 ? '合計偏多' : tot < 0 ? '合計偏空' : '多空相抵'}）` });
    return out;
  }
  function readRetail(all, view) {
    const last = all[all.length - 1], out = [];
    const st = streakOf(all, 'p');
    if (!st.n) out.push({ tag: '持平', c: 'flat', t: '散戶多空比為 0，多單與空單相等' });
    else out.push({ tag: st.sign > 0 ? '偏多' : '偏空', c: st.sign > 0 ? 'up' : 'down', t: `連續 ${st.n} 日散戶偏${st.sign > 0 ? '多' : '空'}（多空比 ${sgd(last.p, 2)}%）` });
    const a = view[0];
    if (a && view.length > 1 && a.p != null && last.p != null && a.tx && last.tx) {
      const dp = last.p - a.p, dt = (last.tx / a.tx - 1) * 100;
      const txt = `多空比 ${sgd(a.p, 2)}% → ${sgd(last.p, 2)}%（${sgd(dp, 2)}pp）、加權指數 ${sgd(dt, 2)}%`;
      if (dp * dt < 0) out.push({ tag: '分歧', c: 'flat', t: `期間散戶多空比與台指走勢反向：${txt}` });
      else if (dp * dt > 0) out.push({ tag: '同向', c: 'flat', t: `期間散戶多空比與台指走勢同向：${txt}` });
      else out.push({ tag: '持平', c: 'flat', t: txt });
    }
    const vs = view.map((r) => r.p).filter((v) => v != null);
    if (vs.length > 2 && last.p != null) {
      const below = vs.filter((v) => v < last.p).length, pc = Math.round(below / (vs.length - 1) * 100);
      out.push({ tag: '位階', c: 'flat', t: `目前多空比在所選期間的第 ${pc} 百分位（0＝期間最低、100＝期間最高）` });
    }
    return out;
  }

  /* ---------------- 版面 CSS（桌機；手機另寫 site/m4/20261020-futpages.css） ----------------
     Andy 10-20：「上方已經有標題了，拿掉；右側的內容都移動到上面，未平倉圖表與清單並排；微台與未平倉用同個位置、分段式開關切換」
     第一列＝商品分段開關＋「?」＋（靠右）期間鈕；第二列＝數字卡＋自動解讀並排；第三列＝圖（約 6）＋明細表（約 4）等高並排。 */
  function css() {
    if (document.getElementById('fpCss')) return;
    const st = document.createElement('style'); st.id = 'fpCss';
    st.textContent = `
.fp-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:var(--sp-3,14px)}
.fp-bar .fp-right{margin-left:auto;display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
.fp-prod button{white-space:nowrap}
.fp-block{margin-bottom:var(--sp-3,14px)}
.fp-pane{display:flex;flex-direction:column;gap:var(--sp-3,14px)}
.fp-topgrid{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--sp-3,14px);align-items:stretch}
.fp-split{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,4fr);gap:var(--sp-3,14px);align-items:stretch}
.fp-split>.fp-main{min-width:0}
.fp-tblcard{min-width:0;contain:size;display:flex;flex-direction:column}
.fp-tblcard .fp-tw{flex:1 1 0;min-height:0;max-height:none}
.fp-hd{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.fp-hd h3,.fp-card h3,.fp-card h4{margin:0;font-size:16px;color:var(--ink)}
.fp-chart{height:clamp(230px,calc(100vh - 500px),360px);width:100%}
.fp-stale{font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;border:1px solid #F59E0B;color:#F59E0B;white-space:nowrap}
.fp-note{font-size:12.5px;color:var(--ink-3);margin-top:6px;line-height:1.6}
.fp-hint{font-size:12px;color:var(--ink-3);margin:-2px 0 6px}
.fp-per button[disabled]{opacity:.4;cursor:not-allowed}
.fp-big3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
.fp-big3>div{min-width:0}.fp-big3 .l{font-size:12.5px;color:var(--ink-3)}
.fp-big3 .v{font:700 24px/1.25 'JetBrains Mono',monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-big3 .s{font-size:12px;color:var(--ink-3);white-space:nowrap}
.fp-concl{margin-top:8px;font-size:13.5px;line-height:1.6;color:var(--ink-2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.fp-autoh{margin:14px 0 6px;font-size:14px;color:var(--ink)}
.fp-auto ul{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-direction:column;gap:8px}
.fp-auto li{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;line-height:1.6;color:var(--ink-2)}
.fp-tag{flex:0 0 auto;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.fp-tag.up{background:color-mix(in srgb,var(--rise,#ff4d6d) 14%,transparent);border-color:color-mix(in srgb,var(--rise,#ff4d6d) 45%,transparent)}.fp-tag.down{background:color-mix(in srgb,var(--fall,#2ee59d) 12%,transparent);border-color:color-mix(in srgb,var(--fall,#2ee59d) 45%,transparent)}
.fp-disc{font-size:11.5px;color:var(--ink-3);margin-top:8px}
.fp-tw{max-height:380px;overflow:auto;border:1px solid var(--line);border-radius:10px;touch-action:pan-x pan-y;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}
.fp-tw table{border-collapse:separate;border-spacing:0;width:100%;min-width:max-content;font-size:13px}
.fp-tw table thead th{position:sticky;top:0;z-index:2;background:var(--panel-2);padding:7px 6px;text-align:center;white-space:nowrap;cursor:pointer;user-select:none;border-bottom:1px solid var(--line);font-weight:600;color:var(--ink-2)}
.fp-tw table thead th:first-child,.fp-tw table tbody td:first-child{position:sticky;left:0;text-align:left;z-index:3;background:var(--panel-2)}
.fp-tw table tbody td{padding:6px 6px;text-align:center;white-space:nowrap;font-family:'JetBrains Mono',monospace;border-bottom:1px solid var(--line);background:var(--panel)}
.fp-tw table tbody td:first-child{z-index:1;font-family:inherit}
.fp-tw table tbody tr.hl td{background:var(--panel-3)}
.fp-tw table tbody tr.sel td{background:var(--panel-3);box-shadow:inset 0 1px 0 var(--cyan),inset 0 -1px 0 var(--cyan)}
.fp-tw th.sorted::after{content:attr(data-arrow);margin-left:4px;color:var(--cyan)}
.fp-tw tr{cursor:pointer}
.fp-top{margin:0}
.fp-top .bigrow{display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap}
.fp-top .lab{font-size:13px;color:var(--ink-3)}.fp-top .lab b{color:var(--ink-2);font-weight:600}
.fp-top .bignum{font:700 24px/1.25 'JetBrains Mono',monospace;white-space:nowrap}
.fp-top .delta{font-size:13px;color:var(--ink-3);white-space:nowrap}
.fp-top .sum{flex:1 1 220px;min-width:0;font-size:13.5px;line-height:1.7;color:var(--ink-2)}
.fp-top .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
.fp-top .stats .l{font-size:12.5px;color:var(--ink-3)}.fp-top .stats .v{font:700 18px/1.3 'JetBrains Mono',monospace;white-space:nowrap}
/* 窄畫面（含手機）：並排改上下，順序＝數字卡 → 圖 → 自動解讀 → 明細表 */
@media (max-width:900px){
 .fp-pane{display:flex}.fp-topgrid,.fp-split{display:contents}
 .fp-latest,.fp-top{order:1}.fp-main{order:2}.fp-tblcard{order:3;contain:none;display:block}
 .fp-tblcard .fp-tw{max-height:380px}
 .fp-bar .fp-right{margin-left:0}
}`;
    document.head.appendChild(st);
  }

  /* ---------------- 說明文字 ---------------- */
  const HOW = {
    futoi: (src) => `<p>「未平倉」是期貨還沒結清的部位口數。外資、投信、自營商每天收盤後都要向期交所申報手上台指期（大台）的多方與空方未平倉，<b>淨部位＝多方未平倉－空方未平倉</b>：正數代表法人整體押漲（偏多），負數代表整體押跌或避險（偏空）。</p>
      <p>怎麼用：①看<b>方向</b>——外資資金最大，淨空連續擴大代表避險或看空的力道在增加；②看<b>變化</b>——淨部位在加碼還是減碼，比單日正負更有意義；③<b>要跟現貨一起看</b>：外資常用台指期替現貨持股避險，淨空不等於看跌，要對照加權指數與外資現貨買賣超；④投信、自營商口數小，主要看方向有沒有轉折。</p>
      <p>這是統計，不是買賣建議。資料來源：臺灣期貨交易所每日公布的「三大法人－區分各期貨契約」（臺股期貨），經本站整理${src ? '（' + esc(src) + '）' : ''}，收盤後更新。</p>`,
    retail: (src) => `<p>散戶多空比是用期交所公布的數字<b>推算</b>出來的：期交所只公布「全市場未平倉」和「三大法人未平倉」，把全市場扣掉三大法人，剩下的就視為散戶（含法人以外的所有交易人）。</p>
      <p><b>為什麼用微型台指（TMF）？</b>微台一口只有大台的十分之一，門檻低、散戶佔比高，所以它扣掉法人之後的剩餘部位，比大台更接近散戶的真實方向。</p>
      <p>怎麼用：①比率<b>大於 0</b>（紅）＝散戶多單多於空單；<b>小於 0</b>（綠）＝空單較多；②常見讀法是把散戶當<b>反指標</b>——散戶極度偏多時行情容易過熱，極度偏空時可能接近低檔，但這只是統計上的傾向、不保證；③搭配右軸的加權指數看「散戶是在跌的時候加碼偏多、還是漲的時候偏空」，若走勢與多空比反向就是圖旁解讀裡的「分歧」；④結算日（圖上虛線）前後部位會被結清，比率常出現跳動，不用過度解讀。</p>
      <p>不是買賣建議。資料來源：臺灣期貨交易所公布的微型臺指期貨未平倉與三大法人資料，經本站整理${src ? '（' + esc(src) + '）' : ''}。</p>`,
  };

  /* ---------------- 主流程：一頁一個商品、分段開關切換（Andy 10-20） ----------------
     P＝整頁共用狀態：商品 kind、期間（一組 .seg 週期鈕）、焦點日期（hov 滑過／lock 鎖定）、日期軸 axis。
     切商品時下面「數字卡＋自動解讀＋圖＋明細表＋說明」整塊換成那個商品，同一個位置，不再上下堆兩區。
     商品選擇只記在這支檔的變數（同一次瀏覽內重畫、換主題都保留；離開再回來沿用上次，不寫 localStorage）。*/
  const P = { kind: 'futoi', per: '6m', hov: null, lock: null, pers: [], secs: {}, axis: [], first: '' };
  let seq = 0;
  const SECS = { futoi: { file: 'fut_oi', snap: 'fut-oi', title: '台指期三大法人未平倉', how: '台指期三大法人未平倉怎麼看？' }, retail: { file: 'retail_ratio', snap: 'retail-ratio', title: '微台指散戶多空比', how: '什麼是散戶多空比？' } };
  const HOWKEYS = ['futoi', 'retail'];

  async function draw(kind, body, title) {
    css();
    const my = ++seq;
    title.innerHTML = '期貨籌碼';
    body.innerHTML = '<div class="empty">載入中…</div>';
    const [fr, rr] = await Promise.all([A().load('fut_oi', { fallback: null }), A().load('retail_ratio', { fallback: null })]);
    if (my !== seq) return;                       // 等資料的時候使用者已經換頁
    try { const mt = await A().load('meta', { fallback: null }); P.dataDate = (mt && mt.data_date) || ''; } catch (e) { P.dataDate = ''; }
    const futR = normalize('futoi', fr), retR = normalize('retail', rr);
    P.secs = {};
    if (futR) P.secs.futoi = { K: 'futoi', rows: futR, raw: fr, sort: { k: 'date', d: -1 } };
    if (retR) P.secs.retail = { K: 'retail', rows: retR, raw: rr, sort: { k: 'date', d: -1 } };
    P.hov = null; P.lock = null; P.per = '6m';
    if (!futR && !retR) {
      body.innerHTML = '<div class="card fp-card" data-snap="fut-oi"><div class="empty">資料準備中</div></div>';
      body.dataset.snapReady = '1'; return;
    }
    const all = [].concat(futR || [], retR || []);
    P.first = all.reduce((m, r) => (r.date < m ? r.date : m), '9999'); P.last = all.reduce((m, r) => (r.date > m ? r.date : m), '0');
    P.pers = PERIODS.futoi.list.map((p) => ({ id: p[0], lab: p[1], cut: p[0] === 'all' ? null : cutoffOf(P.last, p) }));
    build(body);
    body.dataset.snapReady = '1';
  }
  const addDays = (d, n) => { const x = new Date(d + 'T00:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10); };
  const firstOf = () => { const S = P.secs[P.kind]; return S ? S.rows[0].date : P.first; };
  const perOk = (p) => !p.cut || addDays(firstOf(), 6) <= p.cut;
  const cutNow = () => P.pers.find((q) => q.id === P.per).cut;
  const view = (S) => { const c = cutNow(); return c ? S.rows.filter((r) => r.date >= c) : S.rows; };
  const act = () => (P.secs[P.kind] ? [P.secs[P.kind]] : []);
  const axisNow = () => { const S = P.secs[P.kind]; return S ? view(S).map((r) => r.date) : []; };

  const COLS = {
    futoi: [['date', '日期'], ['fn', '外資淨'], ['tn', '投信淨'], ['dn', '自營淨'], ['sum', '合計']],
    retail: [['date', '日期'], ['tx', '加權指數'], ['l', '散戶多單'], ['s', '散戶空單'], ['n', '散戶淨部位'], ['p', '散戶多空比']],
  };
  const isNet = (k) => k === 'fn' || k === 'tn' || k === 'dn' || k === 'n';
  const emptyCard = (K) => `<section class="fp-block" data-snap="${SECS[K].snap}"><div class="card fp-card"><div class="empty">資料準備中</div></div></section>`;

  function paneHtml(K, S) {
    const num = K === 'futoi'
      ? '<div class="card fp-card fp-latest" id="fpLatest"><h4 id="fpLatT"></h4><div class="fp-big3" id="fpBig3"></div><div class="fp-concl" id="fpConcl"></div></div>'
      : '<div class="card fp-card fp-top" id="fpTop"></div>';
    const tbl = `<div class="card fp-card fp-tblcard"><div class="fp-hd"><h3>每日明細</h3></div><div class="fp-tw" id="fpTw-${K}" tabindex="0"></div></div>`;
    const bs = S.raw.product === 'TMF' || !S.raw.product ? '微台（TMF）' : esc(S.raw.product);
    const chart = K === 'futoi'
      ? `<div class="card fp-card fp-main"><div class="fp-hd"><h3>淨未平倉</h3></div>
          <div id="fpChart-futoi" class="chart fp-chart"></div></div>`
      : `<div class="card fp-card fp-main"><div class="fp-hd"><h3>散戶多空比</h3><span class="fp-hint" id="fpSub" style="margin:0" title="散戶多單／空單＝全市場未平倉－三大法人同方向未平倉；多空比＝（多單－空單）÷全市場未平倉×100%">${bs}・虛線＝結算日</span></div>
          <div id="fpChart-retail" class="chart fp-chart"></div></div>`;
    return `<section class="fp-block fp-pane" data-snap="${SECS[K].snap}"><div class="fp-topgrid">${num}</div><div class="fp-split">${chart}${tbl}</div></section>`;
  }

  function build(body) {
    const prod = `<div class="seg fp-prod" role="group" aria-label="商品">${HOWKEYS.map((k) => `<button type="button" data-k="${k}" class="${k === P.kind ? 'on' : ''}">${SECS[k].title}</button>`).join('')}</div>`;
    const per = `<div class="seg tiny fp-per" role="group" aria-label="期間">${P.pers.map((p) => `<button type="button" data-per="${p.id}">${p.lab}</button>`).join('')}</div>`;
    body.innerHTML = `<div class="fp-bar">${prod}<button class="howbtn pop" id="fpHowBtn" data-how="fut-how" data-ttl="" type="button" aria-label="怎麼看">?</button><div class="fp-right"><span class="fp-stale" id="fpStale" hidden title="資料日比最近一個交易日舊，雲端管線還沒更新到">資料未更新</span>${per}</div></div>`
      + '<div class="howtxt" id="how-fut-how" hidden><div class="howbody"></div></div><div id="fpPaneBox"></div>';
    wireBar(body);
    showKind(body);
  }
  /* 換商品：把舊的圖收掉、整塊內容換成另一個商品（同一個位置） */
  function showKind(body) {
    const box = $('#fpPaneBox', body), K = P.kind, S = P.secs[K];
    $$('[_echarts_instance_]', box).forEach((d) => { try { const i = window.echarts.getInstanceByDom(d); if (i && !i.isDisposed()) i.dispose(); } catch (e) { /* 已收掉 */ } });
    $$('.fp-prod button', body).forEach((x) => x.classList.toggle('on', x.dataset.k === K));
    const hb = $('#fpHowBtn', body); hb.dataset.ttl = SECS[K].how; hb.setAttribute('aria-label', SECS[K].how);
    $('#how-fut-how .howbody', body).innerHTML = S ? HOW[K](S.raw.source) + `<h4 class="fp-autoh">自動解讀</h4><ul class="fp-autoul" id="fpAutoUl-${K}" style="list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px"></ul><p class="fp-disc">依資料自動產生、只陳述數字，不構成投資建議。</p>` : '<p>資料準備中。</p>';
    P.hov = null; P.lock = null;
    if (!perOk(P.pers.find((p) => p.id === P.per))) P.per = 'all';
    $$('.fp-per button', body).forEach((b) => { const p = P.pers.find((q) => q.id === b.dataset.per), ok = perOk(p); b.disabled = !ok; b.title = ok ? '' : `資料只回溯到 ${firstOf()}，不足這個期間`; b.classList.toggle('on', p.id === P.per); });
    { const st = $('#fpStale', body), dd = S && (S.raw.asof || S.rows[S.rows.length - 1].date); if (st) st.hidden = !(dd && P.dataDate && dd < P.dataDate); }
    if (!S) { box.innerHTML = emptyCard(K); return; }
    box.innerHTML = paneHtml(K, S);
    wirePane(box, S);
    paintAll();
  }

  /* ---- 圖 ---- */
  function chartOpt(S, axis) {
    const K = S.kind || S.K, c = col(), long = axis.length > 120, byDate = {};
    S.rows.forEach((r) => { byDate[r.date] = r; });
    const val = (key) => axis.map((d) => (byDate[d] && byDate[d][key] != null ? byDate[d][key] : null));
    const base = {
      animation: false, grid: { left: 64, right: K === 'retail' ? 64 : 24, top: 34, bottom: 34 },
      legend: { top: 0, textStyle: { color: c.ink2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'line' }, confine: true },
      xAxis: { type: 'category', data: axis, boundaryGap: K === 'retail', axisLabel: { color: c.ink3, hideOverlap: true, formatter: (s) => (long ? s.slice(2) : s.slice(5)) } },
    };
    if (K === 'futoi') {
      const mk = (id, nm, key, color) => ({ id, name: nm, type: 'line', showSymbol: false, smooth: false, connectNulls: false, lineStyle: { width: 2, color }, itemStyle: { color }, data: val(key) });
      return Object.assign(base, {
        yAxis: { type: 'value', scale: true, axisLabel: { color: c.ink3, formatter: (x) => (Math.abs(x) >= 1e4 ? (x / 1e4).toFixed(1) + '萬' : x) }, splitLine: { lineStyle: { color: c.line, opacity: .5 } } },
        series: [mk('f', '外資', 'fn', PAL.f), mk('t', '投信', 'tn', PAL.t), mk('d', '自營商', 'dn', PAL.d)],
        tooltip: Object.assign(base.tooltip, { valueFormatter: (x) => sg(x) + ' 口' }),
      });
    }
    const ps = val('p');
    return Object.assign(base, {
      yAxis: [
        { type: 'value', axisLabel: { color: c.ink3, formatter: (x) => x + '%' }, splitLine: { lineStyle: { color: c.line, opacity: .5 } } },
        { type: 'value', scale: true, axisLabel: { color: c.ink3 }, splitLine: { show: false } },
      ],
      series: [
        { id: 'bar', name: '散戶多空比', type: 'bar', barMaxWidth: 18, itemStyle: { color: solidHsl(PAL.r), opacity: 1 }, data: ps },
        { id: 'tx', name: '加權指數', type: 'line', yAxisIndex: 1, showSymbol: false, lineStyle: { width: 2, color: txColor() }, itemStyle: { color: txColor() }, data: val('tx') },
      ],
      tooltip: Object.assign(base.tooltip, { valueFormatter: (x) => (x == null ? '—' : x) }),
    });
  }
  function marks(K) {
    const c = col(), set = new Set(P.axis), data = [];
    if (K === 'retail') ((P.secs.retail.raw.settle_dates) || []).forEach((d) => { if (set.has(d)) data.push({ xAxis: d, lineStyle: { type: 'dashed', color: c.ink3, width: 1, opacity: .7 } }); });
    const f = P.lock || P.hov;
    if (f && set.has(f)) data.push({ xAxis: f, lineStyle: { type: P.lock ? 'solid' : 'dashed', color: c.cyan, width: P.lock ? 2 : 1.5 } });
    return { silent: true, symbol: 'none', label: { show: false }, data };
  }
  function drawChart(S) {
    const K = S.K, el = $('#fpChart-' + K); if (!el) return;
    const o = chartOpt(S, P.axis); o.series[0].markLine = marks(K);
    const ch = A().chart(el, o);
    if (ch && !el._fpWired) {
      el._fpWired = 1;
      const zr = ch.getZr();
      const dateAt = (e) => {
        const p = [e.offsetX, e.offsetY];
        if (!ch.containPixel('grid', p)) return null;
        /* convertFromPixel 對類別軸在這個 ECharts 版本回 NaN → 自己用繪圖區矩形換算 */
        const rc = ch.getModel().getComponent('grid').coordinateSystem.getRect(), n = P.axis.length;
        const gap = K === 'retail', t = (p[0] - rc.x) / rc.width;
        const i = gap ? Math.floor(t * n) : Math.round(t * (n - 1));
        return P.axis[Math.max(0, Math.min(n - 1, i))] || null;
      };
      zr.on('mousemove', (e) => { const d = dateAt(e); if (d && d !== P.hov) { P.hov = d; apply(false); } });
      zr.on('globalout', () => { if (P.hov) { P.hov = null; apply(false); } });
      zr.on('click', (e) => { const d = dateAt(e); P.lock = d && P.lock !== d ? d : null; P.hov = null; apply(true); });
    }
  }

  /* ---- 表 ---- */
  function tableHtml(S) {
    const cols = COLS[S.K], v = view(S).slice(), { k, d } = S.sort;
    const key = (r) => (r[k] == null ? -Infinity : r[k]);
    v.sort((a, b) => (key(a) < key(b) ? -d : key(a) > key(b) ? d : 0));
    const th = cols.map(([ck, lab]) => `<th data-k="${ck}" class="${ck === k ? 'sorted' : ''}" data-arrow="${d < 0 ? '▼' : '▲'}">${lab}</th>`).join('');
    const td = (r, ck) => {
      const x = r[ck];
      if (ck === 'date') return `<td>${r.date}</td>`;
      if (ck === 'tx') return `<td>${x == null ? '—' : x.toLocaleString('zh-TW', { maximumFractionDigits: 2 })}</td>`;
      if (ck === 'p') return `<td class="${cls(x)}">${x == null ? '—' : sgd(x, 2) + '%'}</td>`;
      if (ck === 'sum') return `<td class="${cls(x)}">${sg(x)}</td>`;
      if (isNet(ck)) { const p = ck[0], tip = r[p + 'l'] != null ? ` title="多方 ${nf(r[p + 'l'])}／空方 ${nf(r[p + 's'])} 口"` : ''; return `<td class="${cls(x)}"${tip}>${sg(x)}</td>`; }
      return `<td>${nf(x)}</td>`;
    };
    return `<table><thead><tr>${th}</tr></thead><tbody>${v.map((r) => `<tr data-d="${r.date}">${cols.map(([ck]) => td(r, ck)).join('')}</tr>`).join('')}</tbody></table>`;
  }
  function drawTable(S) {
    const w = $('#fpTw-' + S.K); if (!w) return;
    const sl = w.scrollLeft, st = w.scrollTop;
    w.innerHTML = tableHtml(S); w.scrollLeft = sl; w.scrollTop = st;
    S.rowEls = {}; $$('tbody tr', w).forEach((tr) => { S.rowEls[tr.dataset.d] = tr; });
    S.hlRow = null; S.selRow = null;
  }

  /* ---- 大數字 / 解讀 ---- */
  const focusDate = () => P.lock || P.hov;
  function focusRow(S) { const f = focusDate(), v = view(S); return (f && v.find((r) => r.date === f)) || null; }
  function paintNumbers() {
    const f = focusDate(), S1 = P.kind === 'futoi' ? P.secs.futoi : null, S2 = P.kind === 'retail' ? P.secs.retail : null;
    if (S1) {
      const v = view(S1), r = focusRow(S1) || v[v.length - 1], isLast = !f;
      $('#fpLatT').innerHTML = isLast ? '最新一日淨未平倉' : `${P.lock ? '鎖定日' : '滑過日'}淨未平倉 <span class="muted" style="font-weight:400">${r.date}</span>`;
      $('#fpBig3').innerHTML = [['外資', 'f'], ['投信', 't'], ['自營商', 'd']].map(([nm, p]) => `<div><div class="l">${nm}</div><div class="v ${cls(r[p + 'n'])}">${sg(r[p + 'n'])}</div><div class="s">多 ${nf(r[p + 'l'])}</div><div class="s">空 ${nf(r[p + 's'])}</div></div>`).join('');
    }
    if (S2) {
      const v = view(S2), fr = focusRow(S2), r = fr || v[v.length - 1];
      const miss = f && !fr;                         // 焦點日在微台上市之前：寫明沒資料，數字維持最新一日
      const i = S2.rows.indexOf(r), prev = S2.rows[i - 1], d = prev && prev.p != null && r.p != null ? r.p - prev.p : null;
      const big = r.p == null ? '—' : `${r.p > 0 ? '▲' : r.p < 0 ? '▼' : ''} ${sgd(r.p, 2)}%`;
      const lean = r.p == null ? '' : Math.abs(r.p) < 0.5 ? '多空幾乎打平' : r.p > 0 ? '散戶整體偏多（多單多於空單）' : '散戶整體偏空（空單多於多單）';
      $('#fpTop').innerHTML = `<div class="bigrow"><div><div class="lab">${f && !miss ? `${P.lock ? '鎖定日' : '滑過日'}散戶多空比 <b>${r.date}</b>` : '最新一日散戶多空比'}${miss ? '（' + f + ' 微台尚無資料，顯示最新一日）' : ''}</div>
        <div class="bignum ${cls(r.p)}" id="fpBigNum">${big}</div>
        <div class="delta">較前一交易日 <span class="${cls(d)}">${d == null ? '—' : sgd(d, 2) + 'pp'}</span></div></div>
        <div class="sum">微台全市場未平倉 ${nf(r.tot)} 口，扣掉三大法人後散戶多單 ${nf(r.l)} 口、空單 ${nf(r.s)} 口，${lean}。</div></div>
        <div class="stats"><div><div class="l">散戶多單（口）</div><div class="v up">${nf(r.l)}</div></div><div><div class="l">散戶空單（口）</div><div class="v down">${nf(r.s)}</div></div><div><div class="l">全市場未平倉（口）</div><div class="v">${nf(r.tot)}</div></div></div>`;
    }
  }
  function paintAuto() {
    act().forEach((S) => {
      const v = view(S), items = S.K === 'futoi' ? readFut(S.rows, v) : readRetail(S.rows, v);
      const ul = $('#fpAutoUl-' + S.K);
      if (ul) ul.innerHTML = items.map((x) => `<li style="display:flex;gap:8px;align-items:flex-start;font-size:13.5px;line-height:1.6"><span class="fp-tag ${x.c}">${x.tag}</span><span>${esc(x.t)}</span></li>`).join('');
      /* 數字卡下方一行（最多兩行）結論；完整條目在「?」 */
      const cc = $('#fpConcl');
      if (cc) cc.textContent = items.slice(0, 2).map((x) => x.t).join('；');
    });
  }
  function paintHints() { /* 期間不足的說明改放反灰按鈕的 title，畫面上不再寫「資料回溯至」 */ }

  /* 焦點日期改變：兩區一起更新大數字、圖上標示線、表格列亮起（不重畫整張表／圖） */
  function apply(fromClick) {
    paintNumbers();
    act().forEach((S) => {
      const el = $('#fpChart-' + S.K), ch = el && window.echarts ? window.echarts.getInstanceByDom(el) : null;
      if (ch) ch.setOption({ series: [{ id: S.K === 'futoi' ? 'f' : 'bar', markLine: marks(S.K) }] });
      const rows = S.rowEls || {};
      if (S.hlRow) S.hlRow.classList.remove('hl');
      if (S.selRow) S.selRow.classList.remove('sel');
      S.hlRow = P.hov && rows[P.hov] || null; S.selRow = P.lock && rows[P.lock] || null;
      if (S.hlRow) S.hlRow.classList.add('hl');
      if (S.selRow) {
        S.selRow.classList.add('sel');
        if (fromClick && !isM() && !P.fromRow) { const w = $('#fpTw-' + S.K), t = S.selRow.offsetTop - 40; if (w && (t < w.scrollTop || t > w.scrollTop + w.clientHeight - 80)) w.scrollTop = Math.max(0, t - 60); }
      }
    });
    P.fromRow = false;
  }
  function paintAll() {
    P.axis = axisNow();
    { const r = $('.fp-per'); if (r && P.axis.length) r.title = '目前顯示 ' + P.axis[0] + '～' + P.axis[P.axis.length - 1]; }
    paintHints(); paintNumbers(); paintAuto();
    act().forEach((S) => { drawChart(S); drawTable(S); });
    apply(false);
  }

  /* ---- 事件 ---- */
  function wireBar(body) {
    $$('.fp-prod button', body).forEach((b) => {
      b.onclick = () => { if (b.dataset.k === P.kind) return; P.kind = b.dataset.k; showKind(body); };
    });
    $$('.fp-per button', body).forEach((b) => {
      b.onclick = () => {
        if (b.disabled) return;
        P.per = b.dataset.per; P.hov = null;
        $$('.fp-per button', body).forEach((x) => x.classList.toggle('on', x === b));
        P.axis = axisNow();
        if (P.lock && !P.axis.includes(P.lock)) P.lock = null;
        paintAll();
      };
    });
  }
  function wirePane(box, S) {
    const tw = $('#fpTw-' + S.K, box);
    tw.onclick = (e) => {
      const th = e.target.closest('th');
      if (th) { const k = th.dataset.k; S.sort = S.sort.k === k ? { k, d: -S.sort.d } : { k, d: -1 }; drawTable(S); apply(false); return; }
      const tr = e.target.closest('tr[data-d]');
      if (tr) { const d = tr.dataset.d; P.lock = P.lock === d ? null : d; P.hov = null; P.fromRow = true; apply(true); }
    };
    tw.onmouseover = (e) => { const tr = e.target.closest('tbody tr[data-d]'); if (tr && tr.dataset.d !== P.hov) { P.fromRow = true; P.hov = tr.dataset.d; apply(false); } };
    tw.onmouseleave = () => { if (P.hov) { P.hov = null; apply(false); } };
  }

  if (!window.TwSnapReady) window.TwSnapReady = () => Promise.resolve();   // origin/main 還沒有快照就緒掛鉤時的最小保底
  window.TwFut = { draw, normalize, readFut, readRetail, state: P };
})();
