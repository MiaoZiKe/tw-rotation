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
   功能鍵：mkt.fut（features.js／plan_presets.js，2026-11-02 起訪客 3／註冊會員 5／Plus 50／Pro 不限，閘門在 perm.js／quota.js，本檔不自己做鎖）。
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
          r[p + 'v'] = o.day_net && o.day_net[j] != null ? Number(o.day_net[j]) : null;   // 當日買賣超（交易口數淨額）
        });
        r.sumv = (r.fv == null && r.tv == null && r.dv == null) ? null : (r.fv || 0) + (r.tv || 0) + (r.dv || 0);
        r.sum = (r.fn == null && r.tn == null && r.dn == null) ? null : (r.fn || 0) + (r.tn || 0) + (r.dn || 0);
      } else {
        r.tot = at(raw.total_oi, j); r.l = at(raw.retail_long, j); r.s = at(raw.retail_short, j);
        r.n = raw.retail_net && raw.retail_net[j] != null ? Number(raw.retail_net[j]) : (r.l != null && r.s != null ? r.l - r.s : null);
        r.p = raw.ratio_pct && raw.ratio_pct[j] != null ? Number(raw.ratio_pct[j]) : (r.tot ? r.n / r.tot * 100 : null);
      }
      rows.push(r);
    }
    /* 沒有交易口數淨額欄位時（舊 JSON）：當日＝今日淨未平倉－前一交易日淨未平倉；第一天留空 */
    if (kind === 'futoi') rows.forEach((r, i) => {
      ['f', 't', 'd'].forEach((p) => { if (r[p + 'v'] == null) r[p + 'v'] = i && r[p + 'n'] != null && rows[i - 1][p + 'n'] != null ? r[p + 'n'] - rows[i - 1][p + 'n'] : null; });
      r.sumv = (r.fv == null && r.tv == null && r.dv == null) ? null : (r.fv || 0) + (r.tv || 0) + (r.dv || 0);
    });
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
.fp-latest{padding-top:10px;padding-bottom:10px}
.fp-lrow{display:flex;align-items:center;gap:16px;flex-wrap:wrap}.fp-lrow h4{flex:0 0 auto;font-size:13px;line-height:1.4;white-space:nowrap}
.fp-big3{flex:1 1 360px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0}
.fp-big3>div{min-width:0}.fp-big3 .l{font-size:12.5px;color:var(--ink-3);display:inline-block;margin-right:6px}
.fp-big3 .v{display:inline-block;font:700 20px/1.25 'JetBrains Mono',monospace;white-space:nowrap}
.fp-big3 .s{font-size:12px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-concl{margin-top:4px;font-size:13px;line-height:1.5;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-prodseg{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 2px}.fp-prodseg .muted{font-size:12px}
.fp-prodseg button[disabled]{opacity:.38;cursor:not-allowed}
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
      <p><b>兩種數字別混在一起：</b>上方四張卡的大字是「當日買賣超」＝法人<b>這一天</b>台指期的交易口數淨額（期交所「交易口數淨額」＝當天買進口數－賣出口數；紅＝買超、綠＝賣超），小字是「期間累積」（所選期間每天加總、起點 0）與「淨未平倉」（到這一天為止手上還沒結清的多空差＝累計部位）。當日買超是在加碼，不等於累計部位就轉多。若某天資料缺交易口數，當日改用「未平倉增減」（今日淨未平倉－前一交易日淨未平倉），口徑以畫面下方的資料來源為準。</p>
      <p>三張圖表：左＝每日買賣超（三法人堆疊直條）加加權指數線；中＝期間累積買賣超，可切換成「淨未平倉」看累計部位；右＝每日明細（預設當日買賣超，按「看累計部位」多出累計欄）。滑過一天，圖與表同一天一起亮，點一下鎖定、再點取消。</p>
      <p>怎麼用：①看<b>方向</b>——外資資金最大，淨空連續擴大代表避險或看空的力道在增加；②看<b>變化</b>——淨部位在加碼還是減碼，比單日正負更有意義；③<b>要跟現貨一起看</b>：外資常用台指期替現貨持股避險，淨空不等於看跌，要對照加權指數與外資現貨買賣超；④投信、自營商口數小，主要看方向有沒有轉折。</p>
      <p>這是統計，不是買賣建議。資料來源：臺灣期貨交易所每日公布的「三大法人－區分各期貨契約」（臺股期貨），經本站整理${src ? '（' + esc(src) + '）' : ''}，收盤後更新。</p>`,
    retail: (src) => `<p>散戶多空比是用期交所公布的數字<b>推算</b>出來的：期交所只公布「全市場未平倉」和「三大法人未平倉」，把全市場扣掉三大法人，剩下的就視為散戶（含法人以外的所有交易人）。</p>
      <p><b>大台、小台、微台怎麼選？</b>三種都是台指期，只差一口的大小：大台（TX）最大，法人與大戶為主；小台（MTX）一口是大台的四分之一，散戶佔比高，台股常看的散戶多空比多半看小台，所以預設小台；微台（TMF）一口只有大台的十分之一，門檻最低、散戶最多但量最小。三種商品各自算各自的多空比，切換上方開關即可對照。</p>
      <p>怎麼用：①比率<b>大於 0</b>（紅）＝散戶多單多於空單；<b>小於 0</b>（綠）＝空單較多；②常見讀法是把散戶當<b>反指標</b>——散戶極度偏多時行情容易過熱，極度偏空時可能接近低檔，但這只是統計上的傾向、不保證；③搭配右軸的加權指數看「散戶是在跌的時候加碼偏多、還是漲的時候偏空」，若走勢與多空比反向就是圖旁解讀裡的「分歧」；④結算日（圖上虛線）前後部位會被結清，比率常出現跳動，不用過度解讀。</p>
      <p>不是買賣建議。資料來源：臺灣期貨交易所公布的微型臺指期貨未平倉與三大法人資料，經本站整理${src ? '（' + esc(src) + '）' : ''}。</p>`,
  };

  /* ---------------- 主流程：一頁一個商品、分段開關切換（Andy 10-20） ----------------
     P＝整頁共用狀態：商品 kind、期間（一組 .seg 週期鈕）、焦點日期（hov 滑過／lock 鎖定）、日期軸 axis。
     切商品時下面「數字卡＋自動解讀＋圖＋明細表＋說明」整塊換成那個商品，同一個位置，不再上下堆兩區。
     商品選擇只記在這支檔的變數（同一次瀏覽內重畫、換主題都保留；離開再回來沿用上次，不寫 localStorage）。*/
  const P = { kind: 'futoi', per: '6m', hov: null, lock: null, pers: [], secs: {}, axis: [], first: '', prod: 'MTX', prods: {} };
  const PROD_NAME = { TX: '大台', MTX: '小台', TMF: '微台' };   // 台指期三種契約（一口大小不同）；預設小台（Andy 10-20）
  let seq = 0;
  const SECS = { futoi: { file: 'fut_oi', snap: 'fut-oi', title: '台指期三大法人未平倉', how: '台指期三大法人未平倉怎麼看？' }, retail: { file: 'retail_ratio', snap: 'retail-ratio', title: '台指散戶多空比', how: '什麼是散戶多空比？' } };
  const HOWKEYS = ['futoi', 'retail'];

  async function draw(kind, body, title) {
    css();
    const my = ++seq;
    title.innerHTML = '期貨籌碼';
    body.innerHTML = '<div class="empty">載入中…</div>';
    const [fr, rr] = await Promise.all([A().load('fut_oi', { fallback: null }), A().load('retail_ratio', { fallback: null })]);
    if (my !== seq) return;                       // 等資料的時候使用者已經換頁
    try { const mt = await A().load('meta', { fallback: null }); P.dataDate = (mt && mt.data_date) || ''; } catch (e) { P.dataDate = ''; }
    const futR = normalize('futoi', fr);
    /* 散戶多空比合約：{asof, order, products:{TX,MTX,TMF:{dates,taiex,total_oi,retail_long,…}}}；舊格式（頂層直接是 TMF 那包）也吃 */
    P.prods = {};
    if (rr && rr.products && typeof rr.products === 'object') {
      Object.keys(PROD_NAME).forEach((k) => { const o = rr.products[k]; if (!o) return;
        const raw = Object.assign({ asof: rr.asof, source: rr.source, order: rr.order }, o, { product: k });
        const rows = normalize('retail', raw); if (rows) P.prods[k] = { rows, raw }; });
    } else if (rr && Array.isArray(rr.dates)) {
      const k = PROD_NAME[rr.product] ? rr.product : 'TMF', rows = normalize('retail', Object.assign({}, rr, { product: k })); if (rows) P.prods[k] = { rows, raw: Object.assign({}, rr, { product: k }) };
    }
    if (!P.prods[P.prod]) P.prod = P.prods.MTX ? 'MTX' : (Object.keys(P.prods)[0] || 'MTX');
    const retR = P.prods[P.prod] ? P.prods[P.prod].rows : null;
    P.secs = {};
    P.src = fr && fr.foreign && Array.isArray(fr.foreign.day_net) && fr.foreign.day_net.length ? 'vol' : 'oi';
    if (futR) P.secs.futoi = { K: 'futoi', rows: futR, raw: fr, sort: { k: 'date', d: -1 } };
    if (retR) P.secs.retail = { K: 'retail', rows: retR, raw: P.prods[P.prod].raw, sort: { k: 'date', d: -1 } };
    P.hov = null; P.lock = null; P.per = '6m';
    if (!futR && !retR) {
      body.innerHTML = '<div class="card fp-card" data-snap="fut-oi"><div class="empty">資料準備中</div></div>';
      body.dataset.snapReady = '1'; return;
    }
    const all = [].concat(futR || [], ...Object.keys(P.prods).map((k) => P.prods[k].rows));
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
    futoi: [['date', '日期'], ['fv', '外資當日'], ['fn', '外資累計'], ['tv', '投信當日'], ['tn', '投信累計'], ['dv', '自營當日'], ['dn', '自營累計'], ['sumv', '合計當日'], ['sum', '合計累計']],
    retail: [['date', '日期'], ['tx', '加權指數'], ['l', '散戶多單'], ['s', '散戶空單'], ['n', '散戶淨部位'], ['p', '散戶多空比']],
  };
  const isNet = (k) => k === 'fn' || k === 'tn' || k === 'dn' || k === 'n' || k === 'fv' || k === 'tv' || k === 'dv';
  const emptyCard = (K) => `<section class="fp-block" data-snap="${SECS[K].snap}"><div class="card fp-card"><div class="empty">資料準備中</div></div></section>`;

  function paneHtml(K, S) {
    if (K === 'futoi') return futHtml();
    const num = K === 'futoi'
      ? '<div class="card fp-card fp-latest" id="fpLatest"><div class="fp-lrow"><h4 id="fpLatT"></h4><div class="fp-big3" id="fpBig3"></div></div><div class="fp-concl" id="fpConcl"></div></div>'
      : '<div class="card fp-card fp-top" id="fpTop"></div>';
    const tbl = `<div class="card fp-card fp-tblcard"><div class="fp-hd"><h3>每日明細</h3></div><div class="fp-tw" id="fpTw-${K}" tabindex="0"></div></div>`;
    const bs = PROD_NAME[P.prod] ? `${PROD_NAME[P.prod]}（${P.prod}）` : esc(S.raw.product || '');
    const pseg = `<div class="fp-prodseg"><div class="seg tiny" id="fpProdSeg" role="group" aria-label="契約：大台、小台、微台">${Object.keys(PROD_NAME).map((k) => `<button type="button" data-p="${k}" class="${k === P.prod ? 'on' : ''}"${P.prods[k] ? '' : ` disabled aria-disabled="true" title="${PROD_NAME[k]}資料準備中"`}>${PROD_NAME[k]}</button>`).join('')}</div><span class="muted">台指期的三種契約，一口大小不同</span></div>`;
    const chart = K === 'futoi'
      ? `<div class="card fp-card fp-main"><div class="fp-hd"><h3>累計淨未平倉（上）與當日買賣超（下）</h3></div>
          <div id="fpChart-futoi" class="chart fp-chart fp-chart-tall"></div></div>`
      : `<div class="card fp-card fp-main"><div class="fp-hd"><h3>散戶多空比</h3><span class="fp-hint" id="fpSub" style="margin:0" title="散戶多單／空單＝全市場未平倉－三大法人同方向未平倉；多空比＝（多單－空單）÷全市場未平倉×100%">${bs}・虛線＝結算日</span></div>
          <div id="fpChart-retail" class="chart fp-chart"></div></div>`;
    return `<section class="fp-block fp-pane" data-snap="${SECS[K].snap}">${K === 'retail' ? pseg : ''}<div class="fp-topgrid">${num}</div><div class="fp-split">${chart}${tbl}</div></section>`;
  }

  function build(body) {
    const prod = `<div class="seg fp-prod" role="group" aria-label="商品">${HOWKEYS.map((k) => `<button type="button" data-k="${k}" class="${k === P.kind ? 'on' : ''}">${SECS[k].title}</button>`).join('')}</div>`;
    const per = `<div class="seg tiny fp-per" role="group" aria-label="期間">${P.pers.map((p) => `<button type="button" data-per="${p.id}">${p.lab}</button>`).join('')}</div>`;
    body.innerHTML = `<div class="fp-bar mktstreakbar">${prod}<button class="howbtn pop" id="fpHowBtn" data-how="fut-how" data-ttl="" type="button" aria-label="怎麼看">?</button><div class="fp-right"><span class="fp-stale" id="fpStale" hidden title="資料日比最近一個交易日舊，雲端管線還沒更新到">資料未更新</span>${per}</div></div>`
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
    $$('.fp-per button', body).forEach((b) => { const p = P.pers.find((q) => q.id === b.dataset.per), ok = perOk(p); b.disabled = !ok; b.title = ok ? '' : `資料自 ${firstOf().slice(5).replace('-', '/')} 起，不足${p.lab}`; b.classList.toggle('on', p.id === P.per); });
    { const st = $('#fpStale', body), dd = S && (S.raw.asof || S.rows[S.rows.length - 1].date); if (st) st.hidden = !(dd && P.dataDate && dd < P.dataDate); }
    if (!S) { box.innerHTML = emptyCard(K); return; }
    box.innerHTML = paneHtml(K, S);
    if (K === 'futoi') futWire(box, S); else wirePane(box, S);
    paintAll();
  }

  /* ================= 台指期三大法人：版面照「三大法人買賣超日報」（#market/inst，Andy 2026-11-09 17:35）=================
     共用 index.html 裡那一套 class：mktstreakbar／itiles／itile／irtri／irc／irtbl，圖的樣式與提示框規矩也照 app.js 的 irCharts
     （三法人當日直條堆疊＋加權指數雙 Y 軸、中圖起點 0 的累積線、右表、滑過連動、點一下鎖定、單一提示框）。
     「當日買賣超」＝期交所「交易口數淨額」（多方交易口數－空方交易口數）；舊 JSON 沒這欄時用未平倉增減（今日累計－前一交易日累計）。
     期貨特有的「累計淨未平倉」保留：每張卡一行小字、中圖可切「累積買賣超｜淨未平倉」、右表可展開累計部位欄。 */
  const FW = [['f', '外資', 'fv', 'fn'], ['t', '投信', 'tv', 'tn'], ['d', '自營商', 'dv', 'dn'], ['s', '三大法人合計', 'sumv', 'sum']];
  const FPERS = { '1m': 21, '3m': 63, '6m': 126, '1y': 252, '3y': 756, '5y': 1260, all: Infinity };
  const FUT = { c1: null, c2: null, mid: 'cum', cum: false, all: false, sk: 'date', sd: -1 };
  const md = (d) => (d ? d.slice(5).replace('-', '/') : '—');
  const perLabOf = () => { const p = P.pers.find((q) => q.id === P.per); return p ? p.lab : ''; };
  const dayLabel = () => (P.src === 'vol' ? '交易口數淨額' : '未平倉增減');

  function futHtml() {
    return `<section class="fp-block fp-pane" data-snap="fut-oi" id="fpFut">
      <div class="card irc irtop"><div class="itiles" id="fpTiles"></div></div>
      <div class="irtri">
        <div class="card irc"><h3>每日買賣超・加權指數 <small>口</small></h3><div id="fpBars" class="chart" style="min-height:320px"></div></div>
        <div class="card irc"><div class="fp-hd" style="margin-bottom:4px"><h3 id="fpMidT">累積買賣超 <small>口・起點 0</small></h3><div class="seg tiny" id="fpMidSeg" role="group" aria-label="中圖看什麼"><button type="button" data-m="cum" class="on">累積買賣超</button><button type="button" data-m="oi">淨未平倉</button></div></div><div id="fpLines" class="chart" style="min-height:250px"></div></div>
        <div class="card irc"><div class="fp-hd" style="margin-bottom:4px"><h3>每日明細 <small>口・當日買賣超</small></h3><button type="button" class="btn small" id="fpCumBtn" aria-pressed="false">看累計部位</button></div><div class="tw irtbl" id="fpTbl"></div></div>
      </div></section>`;
  }
  function futTiles(S) {
    const v = view(S), rows = S.rows, hist = rows.slice(-252), last = v[v.length - 1], pl = perLabOf();
    $('#fpTiles').innerHTML = FW.map(([k, nm, dk, nk]) => {
      const cum = v.reduce((a, r) => a + (r[dk] || 0), 0), xs = hist.map((r) => r[dk]).filter((x) => x != null);
      const p = xs.length && last[dk] != null ? Math.round(xs.filter((x) => x <= last[dk]).length / xs.length * 100) : 0;
      return `<div class="itile" data-k="${k}" title="細條＝最新一日在近 1 年（${xs.length} 個交易日）每日買賣超裡的百分位，越高越偏買超"><span class="il">${nm}</span><b class="iv num ${cls(last[dk])}">${sg(last[dk])} 口</b>
        <span class="icu">${pl}累積 <b class="num ${cls(cum)}">${sg(cum)}</b> 口</span>
        <span class="icu fp-oi">淨未平倉 <b class="num ${cls(last[nk])}">${sg(last[nk])}</b> 口</span>
        <span class="ipct"><span class="trk"><i style="width:${p}%"></i></span><em>${p}%</em></span></div>`;
    }).join('');
  }
  function futCharts(S) {
    const rows = view(S), dates = rows.map((r) => r.date), hasTw = rows.some((r) => r.tx != null);
    const CH = A().CH, tip = A().tip, axisStyle = A().axisStyle, chip = window.TwChipColors || {};
    const colr = { f: chip.foreign || PAL.f, t: chip.trust || PAL.t, d: chip.dealer || PAL.d };
    const idxCol = isDark() ? (chip.idxDark || '#E2E8F0') : (chip.idxLight || '#0F172A');
    const axX = { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: CH.line } }, axisLabel: { color: CH.ink3, fontSize: 12, formatter: md, hideOverlap: true }, axisTick: { show: false } };
    [FUT.c1, FUT.c2].forEach((x) => { try { if (x && !x.isDisposed() && !x.getDom().isConnected) x.dispose(); } catch (e) { /* 已收掉 */ } });
    const lkSer = { id: 'lk', type: 'line', data: [], silent: true, markLine: { data: [] } };
    const W3 = FW.slice(0, 3);
    const bars = W3.map(([k, nm, dk]) => ({ name: nm, type: 'bar', stack: 'n', barMaxWidth: 18, solid: true, itemStyle: { color: colr[k], opacity: 1 }, data: rows.map((r) => r[dk]) }));
    FUT.c1 = A().chart(document.getElementById('fpBars'), {
      grid: { left: 8, right: 8, top: 34, bottom: 28, containLabel: true },
      legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 }, itemWidth: 12, itemHeight: 8, data: W3.map((x) => x[1]).concat(hasTw ? ['加權指數'] : []) },
      tooltip: Object.assign({}, tip, { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (ps) => { const r = rows[ps[0].dataIndex]; if (!r) return '';
        return `<b>${r.date}</b>（當日買賣超）<br>` + W3.map(([k, nm, dk]) => `${nm}　<b style="color:${r[dk] > 0 ? CH.up : r[dk] < 0 ? CH.down : CH.ink2}">${sg(r[dk])}</b> 口`).join('<br>')
          + `<br>合計　<b style="color:${r.sumv > 0 ? CH.up : CH.down}">${sg(r.sumv)}</b> 口` + (r.tx != null ? `<br>加權指數　${Math.round(r.tx).toLocaleString('zh-TW')}` : ''); } }),
      xAxis: axX,
      yAxis: [Object.assign({}, axisStyle, { type: 'value', axisLabel: { color: CH.ink3, fontSize: 12 } }),
        { type: 'value', scale: true, show: hasTw, splitLine: { show: false }, axisLine: { show: false }, axisLabel: { color: CH.ink3, fontSize: 12 } }],
      series: [...bars, ...(hasTw ? [{ name: '加權指數', type: 'line', yAxisIndex: 1, showSymbol: false, symbol: 'none', smooth: false, z: 5, lineStyle: { width: chip.lineW || 2, color: idxCol }, itemStyle: { color: idxCol }, data: rows.map((r) => r.tx) }] : []), lkSer],
    }, { notMerge: true });
    const acc = { f: 0, t: 0, d: 0 }, cums = { f: [], t: [], d: [] };
    rows.forEach((r) => W3.forEach(([k, , dk]) => { acc[k] += r[dk] || 0; cums[k].push(acc[k]); }));
    const oi = FUT.mid === 'oi', lv = { f: rows.map((r) => r.fn), t: rows.map((r) => r.tn), d: rows.map((r) => r.dn) }, ser = oi ? lv : cums;
    FUT.c2 = A().chart(document.getElementById('fpLines'), {
      grid: { left: 8, right: 8, top: 34, bottom: 28, containLabel: true },
      legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 }, itemWidth: 14, itemHeight: 8 },
      tooltip: Object.assign({}, tip, { trigger: 'axis', axisPointer: { type: 'line' }, formatter: (ps) => { const i = ps[0].dataIndex; return `<b>${dates[i]}</b>（${oi ? '淨未平倉' : '累積'}）<br>` + W3.map(([k, nm]) => `${nm}　<b style="color:${ser[k][i] > 0 ? CH.up : CH.down}">${sg(ser[k][i])}</b> 口`).join('<br>'); } }),
      xAxis: axX, yAxis: Object.assign({}, axisStyle, { type: 'value', scale: oi, axisLabel: { color: CH.ink3, fontSize: 12, formatter: (x) => (Math.abs(x) >= 1e4 ? (x / 1e4).toFixed(1) + '萬' : x) } }),
      series: [...W3.map(([k, nm]) => ({ name: nm, type: 'line', showSymbol: false, symbol: 'none', lineStyle: { width: chip.lineW || 2, color: colr[k] }, itemStyle: { color: colr[k] }, data: ser[k] })), lkSer],
    }, { notMerge: true });
    $('#fpMidT').innerHTML = oi ? '淨未平倉 <small>口・累計部位</small>' : '累積買賣超 <small>口・起點 0</small>';
    if (!FUT.c1 || !FUT.c2) return;
    FUT.one = window.TwOneTip ? window.TwOneTip([FUT.c1, FUT.c2]) : null;
    try { echarts.connect([FUT.c1, FUT.c2]); } catch (e) { /* 舊版沒有 connect */ }
    const dateAt = (ch, ev) => { const p = [ev.offsetX, ev.offsetY]; if (!ch.containPixel('grid', p)) return null; const i = Math.round(ch.convertFromPixel({ xAxisIndex: 0 }, p[0])); return dates[Math.max(0, Math.min(dates.length - 1, i))]; };
    [FUT.c1, FUT.c2].forEach((ch) => {
      ch.on('updateAxisPointer', (e) => { const a = e.axesInfo && e.axesInfo[0]; if (!a) return; const v = typeof a.value === 'number' ? dates[a.value] : a.value; if (v && v !== P.hov) { P.hov = v; futApply(false); } });
      ch.getZr().on('globalout', () => { if (P.hov) { P.hov = null; futApply(false); } });
      ch.getZr().on('click', (ev) => { const d = dateAt(ch, ev); P.lock = !d || P.lock === d ? null : d; futApply(true); });
    });
  }
  function futTable(S) {
    const tb = $('#fpTbl'); if (!tb) return;
    const base = [['date', '日期', 'l'], ['fv', '外資'], ['tv', '投信'], ['dv', '自營商'], ['sumv', '合計']];
    const cums = [['fn', '外資累計'], ['tn', '投信累計'], ['dn', '自營累計'], ['sum', '合計累計']];
    const cols = FUT.cum ? base.concat(cums) : base, rows = view(S).slice(), { sk, sd } = FUT;
    rows.sort((a, b) => (sk === 'date' ? (a.date < b.date ? -1 : 1) : ((a[sk] == null ? -Infinity : a[sk]) - (b[sk] == null ? -Infinity : b[sk]))) * sd);
    const m4 = isM(), shown = m4 && !FUT.all ? rows.slice(0, 6) : rows;
    tb.innerHTML = `<table><thead><tr>${cols.map(([k, l, c]) => `<th class="${c || ''}${k === sk ? ' sorted' : ''}" data-k="${k}" role="button" tabindex="0">${l}${k === sk ? (sd > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${shown.map((r) =>
      `<tr data-d="${r.date}" title="${r.date}　加權指數 ${r.tx == null ? '—' : Math.round(r.tx).toLocaleString('zh-TW')}　累計淨未平倉 外資 ${sg(r.fn)}／投信 ${sg(r.tn)}／自營商 ${sg(r.dn)}"><td class="l">${rows.length <= 260 ? md(r.date).replace('/', '-') : r.date}</td>`
      + cols.slice(1).map(([k]) => `<td class="num ${cls(r[k])}">${sg(r[k])}</td>`).join('') + '</tr>').join('')}</tbody></table>`
      + (m4 && rows.length > 6 ? `<div class="srmore"><button type="button" class="btn small" id="fpTblAll">${FUT.all ? '收起，只看前 6 筆' : `看全部（${rows.length} 筆）`}</button></div>` : '');
    $$('th[data-k]', tb).forEach((h) => { const go = () => { const k = h.dataset.k; if (FUT.sk === k) FUT.sd *= -1; else { FUT.sk = k; FUT.sd = -1; } futTable(S); futApply(false); }; h.onclick = go; h.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } }; });
    $$('tr[data-d]', tb).forEach((r) => {
      r.onmouseenter = () => { P.hov = r.dataset.d; futApply(false); if (FUT.one) FUT.one.reset(); const i = view(S).findIndex((x) => x.date === r.dataset.d); try { if (FUT.c1 && i >= 0) FUT.c1.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: i }); } catch (e) { /* 圖還沒畫好 */ } };
      r.onmouseleave = () => { P.hov = null; futApply(false); };
      r.onclick = () => { P.lock = P.lock === r.dataset.d ? null : r.dataset.d; futApply(false); };
    });
    const all = $('#fpTblAll', tb); if (all) all.onclick = () => { FUT.all = !FUT.all; futTable(S); futApply(false); };
    futApply(false);
  }
  /* 圖與表同一天連動：hov＝滑過、lock＝點一下鎖定（沿用 P.hov／P.lock，換期間回預設） */
  function futApply(scroll) {
    const tb = $('#fpTbl'); if (!tb) return;
    $$('tr[data-d]', tb).forEach((r) => { r.classList.toggle('hl', r.dataset.d === P.hov); r.classList.toggle('lk', r.dataset.d === P.lock); r.classList.toggle('dim', !!P.lock && r.dataset.d !== P.lock); });
    const root = $('#fpFut'); if (root) { root.dataset.hov = P.hov || ''; root.dataset.sel = P.lock || ''; }
    const CHc = A().CH;
    [FUT.c1, FUT.c2].forEach((ch) => { if (!ch || ch.isDisposed()) return;
      ch.setOption({ series: [{ id: 'lk', markLine: { silent: true, symbol: 'none', animation: false, label: { show: false }, lineStyle: { color: CHc.ink2, type: 'dashed', width: 1 }, data: P.lock ? [{ xAxis: P.lock }] : [] } }] }); });
    if (scroll && P.lock) { const r = tb.querySelector(`tr[data-d="${P.lock}"]`); if (r) tb.scrollTop = Math.max(0, r.offsetTop - tb.clientHeight / 2); }
  }
  function futDraw(S) { futTiles(S); futCharts(S); futTable(S); }
  function futWire(box, S) {
    $$('#fpMidSeg button', box).forEach((b) => { b.onclick = () => { if (b.dataset.m === FUT.mid) return; FUT.mid = b.dataset.m; $$('#fpMidSeg button', box).forEach((x) => x.classList.toggle('on', x === b)); futCharts(S); futApply(false); }; });
    const cb = $('#fpCumBtn', box);
    cb.onclick = () => { FUT.cum = !FUT.cum; cb.setAttribute('aria-pressed', FUT.cum ? 'true' : 'false'); cb.textContent = FUT.cum ? '收起累計部位' : '看累計部位'; futTable(S); };
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
      if (ck === 'sum' || ck === 'sumv') return `<td class="${cls(x)}">${sg(x)}</td>`;
      if (isNet(ck)) { const p = ck[0], tip = r[p + 'l'] != null && ck[1] === 'n' ? ` title="多方 ${nf(r[p + 'l'])}／空方 ${nf(r[p + 's'])} 口"` : ''; return `<td class="${cls(x)}"${tip}>${sg(x)}</td>`; }
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
    const f = focusDate(), S2 = P.kind === 'retail' ? P.secs.retail : null;
    if (S2) {
      const v = view(S2), fr = focusRow(S2), r = fr || v[v.length - 1];
      const miss = f && !fr;                         // 焦點日在微台上市之前：寫明沒資料，數字維持最新一日
      const i = S2.rows.indexOf(r), prev = S2.rows[i - 1], d = prev && prev.p != null && r.p != null ? r.p - prev.p : null;
      const big = r.p == null ? '—' : `${r.p > 0 ? '▲' : r.p < 0 ? '▼' : ''} ${sgd(r.p, 2)}%`;
      const lean = r.p == null ? '' : Math.abs(r.p) < 0.5 ? '多空幾乎打平' : r.p > 0 ? '散戶整體偏多（多單多於空單）' : '散戶整體偏空（空單多於多單）';
      $('#fpTop').innerHTML = `<div class="bigrow"><div><div class="lab">${f && !miss ? `${P.lock ? '鎖定日' : '滑過日'}散戶多空比 <b>${r.date}</b>` : '最新一日散戶多空比'}${miss ? '（' + f + ' ' + (PROD_NAME[P.prod] || '') + '尚無資料，顯示最新一日）' : ''}</div>
        <div class="bignum ${cls(r.p)}" id="fpBigNum">${big}</div>
        <div class="delta">較前一交易日 <span class="${cls(d)}">${d == null ? '—' : sgd(d, 2) + 'pp'}</span></div></div>
        <div class="sum">${PROD_NAME[P.prod] || ''}全市場未平倉 ${nf(r.tot)} 口，扣掉三大法人後散戶多單 ${nf(r.l)} 口、空單 ${nf(r.s)} 口，${lean}。</div></div>
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
      if (S.K === 'futoi') { futApply(fromClick); return; }
      const el = $('#fpChart-' + S.K), ch = el && window.echarts ? window.echarts.getInstanceByDom(el) : null;
      if (ch) ch.setOption({ series: [{ id: 'bar', markLine: marks(S.K) }] });
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
    act().forEach((S) => { if (S.K === 'futoi') futDraw(S); else { drawChart(S); drawTable(S); } });
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
    $$('#fpProdSeg button', box).forEach((b) => {
      b.onclick = () => {
        if (b.disabled || b.dataset.p === P.prod) return;
        const o = P.prods[b.dataset.p]; if (!o) return;
        P.prod = b.dataset.p; P.secs.retail = { K: 'retail', rows: o.rows, raw: o.raw, sort: S.sort };
        showKind(box.parentNode);
      };
    });
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
