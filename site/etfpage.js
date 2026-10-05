/* ============================================================================
   ETF 專區（#etf）—— Andy 2026-10-05（參考別家 ETF 專區的截圖，名稱與版面自己做）
   規格與每個數字的口徑：docs/etf_page_spec.md（分類規則、熱門定義、殖利率、年化報酬）。

   這一頁回答四個問題（每張卡的標題底下都寫著它回答哪一題）：
     1. 現在有哪些 ETF、各是哪一型、殖利率多少？           → 「ETF 一覽」卡片清單（點卡片進個股頁）
     2. 最近大家在買哪幾檔？                               → 「最近最受歡迎前 5 名」
     3. 這個月哪幾天有 ETF 除息、配多少？                  → 「配息行事曆」（點日期在原地展開清單）
     4. 同一型的前五大，長期抱下來誰報酬比較好？配息算進去差多少？ → 「前五名報酬比較」

   資料：data/etf.json（pipeline/compute/etf.py）。
   ⚠ 預覽分支吃的是正式站的資料，etf.json 上正式站之前不存在 —— 那時退回 stocks.json（ETF 也在裡面）
     列出卡片清單與名稱分類，其他三張卡明確標「資料準備中」，不留空白、不編數字。
   為什麼是新檔：同 watchpage.js —— 整頁 UI 放在自己的檔案，app.js 只多路由那一行。
   驗收：scripts/_uitest.py「ETF專區1005」。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const LS = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const CATS = ['配息型', '市值型', '主題型', '債券型', '槓桿反向', '主動式', '其他'];
  const CAT_TONE = { 配息型: 'amber', 市值型: 'cyan', 主題型: 'violet', 債券型: 'lime', 槓桿反向: 'up', 主動式: 'cyan', 其他: 'ink3' };
  const PAGE = 48;   // 一次列幾張卡（「顯示更多」再加）

  /* ---- 名稱分類（只給「etf.json 還不存在」的退回模式用）：跟 pipeline/compute/etf.py classify() 同一套規則。
     少了「近 400 天除息 ≥ 4 次」那一條（退回模式沒有配息資料），所以名稱沒寫「息」的月配 ETF 會落在主題型 ——
     畫面上有寫「依名稱暫分」。改規則兩邊一起改。 */
  const RE = {
    lev: /正2|反1|反向|槓桿|正向2|2倍|-1倍/, bond: /債|美債|公債|投資級|非投等/,
    mcap: /台灣50|台50|臺灣50|中型100|加權|MSCI台灣|摩台|富時台灣|台灣領袖/,
    div: /高股息|高息|股息|收益|優息|月配|季配|息收|股利|優利|高利|穩利|配息|高收/,
    com: /^期|黃金|原油|白銀|黃豆|小麥|商品|美元|日圓|期街口/,
  };
  function classify(code, name) {
    const c = String(code), n = String(name || ''), t = c.slice(-1);
    if (t === 'L' || t === 'R' || RE.lev.test(n)) return '槓桿反向';
    if (t === 'B' || RE.bond.test(n)) return '債券型';
    if (t === 'U' || RE.com.test(n)) return '其他';
    if (t === 'A' || n.indexOf('主動') === 0) return '主動式';
    if (RE.mcap.test(n) && !/正2|反1/.test(n)) return '市值型';
    if (RE.div.test(n)) return '配息型';
    return n ? '主題型' : '其他';
  }

  const S = { data: null, fallback: false, cat: 'all', sort: 'tv', shown: PAGE, pop: 'holders',
    month: null, day: null, grp: '配息型', per: '5y', from: null, basis: 'tr' };
  const pct = (v, d = 1) => (v == null || Number.isNaN(v) ? '—' : (v > 0 ? '+' : '') + (v * 100).toFixed(d) + '%');
  const pctU = (v, d = 2) => (v == null || Number.isNaN(v) ? '—' : (v * 100).toFixed(d) + '%');
  const yi = (v) => (v == null ? '—' : A().fmt.yi(v));
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');

  function injectCSS() {
    if (document.getElementById('etfCss')) return;
    const s = document.createElement('style'); s.id = 'etfCss';
    s.textContent = `
#v-etf .etfdisc{display:flex;gap:8px;align-items:flex-start;padding:10px 14px;border:1px solid var(--line-2);border-left:3px solid var(--amber);
  border-radius:10px;background:var(--panel-2);color:var(--ink-2);font-size:13px;line-height:1.55;margin-bottom:var(--sp-3)}
#v-etf .etfdisc b{color:var(--ink)}
#v-etf .card{margin-bottom:var(--sp-3)}
#v-etf .etfq{margin:2px 0 10px;font-size:13px;color:var(--ink-2)}
#v-etf .etfq b{color:var(--ink)}
#v-etf .etfprep{padding:18px;border:1px dashed var(--line-2);border-radius:10px;color:var(--ink-2);font-size:13.5px;line-height:1.6}
#v-etf .etfrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#v-etf .etfrow .sp{flex:1}
#v-etf .etfgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:10px;margin-top:10px}
#v-etf .etfc{position:relative;display:flex;flex-direction:column;gap:4px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;
  background:var(--panel-2);cursor:pointer;text-align:left;color:var(--ink);font:inherit;min-width:0}
#v-etf .etfc:hover,#v-etf .etfc:focus-visible{border-color:var(--cyan);outline:none}
#v-etf .etfc .h{display:flex;align-items:baseline;gap:6px;min-width:0}
#v-etf .etfc .nm{font-weight:700;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .etfc .cd{font:12px var(--mono);color:var(--ink-3)}
#v-etf .etfc .px{display:flex;align-items:center;gap:8px}
#v-etf .etfc .px b{font:700 17px var(--mono)}
#v-etf .etfc .px .sp{flex:1}
#v-etf .etfc dl{display:grid;grid-template-columns:auto 1fr;gap:1px 8px;margin:2px 0 0;font-size:12px}
#v-etf .etfc dt{color:var(--ink-3)} #v-etf .etfc dd{margin:0;text-align:right;font-family:var(--mono);color:var(--ink-2)}
#v-etf .etag{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:999px;border:1px solid currentColor;white-space:nowrap;line-height:17px}
#v-etf .etag.amber{color:var(--amber)} #v-etf .etag.cyan{color:var(--cyan)} #v-etf .etag.violet{color:var(--violet)}
#v-etf .etag.lime{color:var(--lime)} #v-etf .etag.up{color:var(--up)} #v-etf .etag.ink3{color:var(--ink-3)}
#v-etf .up{color:var(--up)} #v-etf .down{color:var(--down)} #v-etf .flat{color:var(--ink-2)}
#v-etf .etfmore{margin-top:10px;text-align:center}
#v-etf .poplist{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:6px}
#v-etf .popc{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--panel-2);cursor:pointer;color:var(--ink);text-align:left;font:inherit;min-width:0}
#v-etf .popc:hover{border-color:var(--cyan)}
#v-etf .popc .rk{font:700 22px var(--mono);color:var(--amber)}
#v-etf .popc .nm{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf .popc .mv{font:600 13px var(--mono);color:var(--ink-2)}
#v-etf .calwrap{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:14px;margin-top:6px}
#v-etf .calhd{display:flex;align-items:center;gap:8px;margin-bottom:6px}
#v-etf .calhd b{font-size:16px;min-width:110px;text-align:center}
#v-etf .calg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}
#v-etf .calg .wd{font-size:12px;color:var(--ink-3);text-align:center;padding:2px 0}
#v-etf .cald{min-height:58px;border:1px solid var(--line);border-radius:8px;padding:4px 6px;background:var(--panel-2);font-size:12px;color:var(--ink-3);
  cursor:default;text-align:left;font-family:inherit;display:flex;flex-direction:column;gap:2px}
#v-etf .cald.has{cursor:pointer;color:var(--ink)} #v-etf .cald.has:hover{border-color:var(--cyan)}
#v-etf .cald.sel{border-color:var(--amber);box-shadow:0 0 0 1px var(--amber) inset}
#v-etf .cald.pad{visibility:hidden}
#v-etf .cald .n{font:600 12px var(--mono)}
#v-etf .cald .c{font-size:11.5px;color:var(--amber);font-weight:700}
#v-etf .callist{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--panel-2);max-height:420px;overflow:auto}
#v-etf table.et{width:100%;border-collapse:collapse;font-size:13px}
#v-etf table.et th{color:var(--ink-3);font-weight:600;text-align:right;padding:5px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
#v-etf table.et td{text-align:right;padding:5px 6px;border-bottom:1px solid var(--line);font-family:var(--mono);white-space:nowrap}
#v-etf table.et th:first-child,#v-etf table.et td:first-child{text-align:left;font-family:inherit}
#v-etf table.et tr[data-code]{cursor:pointer} #v-etf table.et tr[data-code]:hover td{background:var(--panel-3)}
#v-etf .na{color:var(--ink-3);font-family:inherit;font-size:12px}
#v-etf .retcharts{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:14px;margin-top:8px}
#v-etf .retcharts .chart{height:320px}
#v-etf select.etsel{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:inherit;font-size:13px}
@media (max-width:1100px){#v-etf .poplist{grid-template-columns:repeat(3,minmax(0,1fr))}#v-etf .calwrap,#v-etf .retcharts{grid-template-columns:1fr}}
`;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 資料 */
  async function loadData() {
    const a = A();
    let d = null;
    try { if (a.sparkLoad) await a.sparkLoad(); } catch (e) { /* 迷你走勢讀不到就不畫，不擋整頁 */ }
    try { d = await a.load('etf', { fallback: null }); } catch (e) { d = null; }
    if (d && Array.isArray(d.items) && d.items.length) { S.data = d; S.fallback = false; return; }
    // 退回：stocks.json 裡的 ETF（代號 00 開頭）＋名稱分類
    const st = (await a.load('stocks', { fallback: [] })) || [];
    const items = st.filter((r) => r && /^00/.test(String(r.code))).map((r) => ({
      code: String(r.code), name: r.name || '', cat: classify(r.code, r.name), close: r.close, chg_pct: r.chg_pct,
      tv20: null, tv: r.turnover, yield_ttm: null, freq: null, size: null, holders: null, d_holders: null, stats: {},
    }));
    S.data = { items, top: {}, popular: {}, calendar: [], series: {}, periods: {}, asof: null };
    S.fallback = true;
  }
  const items = () => (S.data && S.data.items) || [];
  const byCode = () => { const m = new Map(); items().forEach((it) => m.set(it.code, it)); return m; };

  /* ------------------------------------------------------------------ 骨架 */
  function skeleton(root) {
    const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
    root.innerHTML = `
<div class="etfdisc" id="etfDisc" role="note"><span aria-hidden="true">ⓘ</span><div><b>本頁僅為公開資料整理與統計，非投資顧問、不構成任何投資建議或推薦。</b>
過去績效不代表未來報酬；殖利率與報酬率依下方各卡「?」寫明的口徑計算，資料不足的一律標「無資料」，不以 0 或推估代替。</div></div>

<div class="card" id="etfPopCard">
  <div class="row spread"><h3>最近最受歡迎前 5 名 <small id="etfPopSub"></small>
    <button class="howbtn pop" data-how="etfpop" data-ttl="最受歡迎怎麼算" type="button" aria-label="最受歡迎怎麼算">?</button></h3>
    <div class="seg" id="etfPopSeg"><button data-v="holders">受益人數週增加</button><button data-v="turnover">近 20 日均成交值</button></div></div>
  ${how('etfpop', '這張回答：最近錢與人潮往哪幾檔 ETF 去？', [
    '<b>受益人數週增加</b>：集保結算所每週公布的受益人數（合計列），最新一週減前一週，增加最多的前 5 檔。代表「新進場的人」。',
    '<b>近 20 日均成交值</b>：最近 20 個交易日成交金額的平均。代表「交易熱度」，槓桿型與大型市值型通常排前面。',
    '所以：兩個口徑都在前面的，是人潮與交易都熱的；只在成交值前面的，多半是短線交易工具。點卡片進個股頁看 K 線。'])}
  <p class="etfq">回答：<b>最近大家在買哪幾檔 ETF？</b></p>
  <div id="etfPop"></div>
</div>

<div class="card" id="etfListCard">
  <div class="row spread"><h3>ETF 一覽 <small id="etfCount"></small>
    <button class="howbtn pop" data-how="etflist" data-ttl="ETF 分類與欄位" type="button" aria-label="ETF 分類與欄位怎麼看">?</button></h3>
    <div class="etfrow"><label class="note" for="etfSort">排序</label>
      <select id="etfSort" class="etsel"><option value="tv">成交值</option><option value="size">規模</option><option value="yield">殖利率</option><option value="chg">今日漲跌</option></select></div></div>
  ${how('etflist', '這張回答：有哪些 ETF、各是哪一型、殖利率多少？', [
    '<b>分類</b>（依序判斷，先符合先歸類）：槓桿反向（代號尾 L/R 或名稱含 正2／反1）→ 債券型（尾 B 或名稱含「債」）→ 其他（期貨／商品／貨幣，尾 U 或「期」開頭）→ 主動式（尾 A）→ 市值型（名稱含 台灣50、台50、中型100、加權、MSCI台灣、摩台）→ 配息型（名稱含 高股息／高息／股息／收益／優息…，或近 400 天除息 ≥ 4 次）→ 其餘股票型為主題型。',
    '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。<b>配息頻率</b>＝近 400 天除息次數（≥10 月配、≥3 季配、2 半年配、1 年配）。',
    '<b>規模</b>＝集保受益權單位數 × 收盤（估算值，不是投信公告的基金淨資產）。<b>成交值</b>＝近 20 日平均。',
    '所以：先用上方分類切出同一型，再用「殖利率」或「規模」排序比較；點卡片進個股頁看 K 線與除權息。'])}
  <p class="etfq">回答：<b>現在有哪些 ETF、各是哪一型、殖利率多少？</b> <span id="etfFbNote"></span></p>
  <div class="seg" id="etfCatSeg" role="tablist" aria-label="ETF 分類"></div>
  <div class="etfgrid" id="etfGrid"></div>
  <div class="etfmore"><button type="button" class="btn small" id="etfMore" hidden>顯示更多</button></div>
</div>

<div class="card" id="etfCalCard">
  <div class="row spread"><h3>配息行事曆 <small id="etfCalSub"></small>
    <button class="howbtn pop" data-how="etfcal" data-ttl="配息行事曆怎麼看" type="button" aria-label="配息行事曆怎麼看">?</button></h3></div>
  ${how('etfcal', '這張回答：這個月哪幾天有 ETF 除息、各配多少？', [
    '格子上的數字＝那天除息的 ETF 檔數；點格子，右邊列出那天每一檔的配息金額、發放日與當次殖利率。',
    '<b>當次殖利率</b>＝該次配息 ÷ 除息前一個交易日收盤；尚未除息的（未來日期）改用最新收盤估算，清單上會標明。',
    '所以：想領某個月的息，就要在除息日「前一個交易日」收盤前持有；發放日才是錢入帳的日子。',
    '資料：FinMind 股利公告（TaiwanStockDividend）與除權息結果，逐檔回補進資料湖；沒回補到的 ETF 不會出現在月曆上。'])}
  <p class="etfq">回答：<b>這個月哪幾天有 ETF 除息、配多少？</b></p>
  <div id="etfCal"></div>
</div>

<div class="card" id="etfRetCard">
  <div class="row spread"><h3>前五名報酬比較 <small id="etfRetSub"></small>
    <button class="howbtn pop" data-how="etfret" data-ttl="報酬比較的口徑" type="button" aria-label="報酬比較的口徑">?</button></h3>
    <div class="etfrow">
      <div class="seg" id="etfGrpSeg"><button data-v="配息型">配息型</button><button data-v="市值型">市值型</button></div>
      <div class="seg" id="etfPerSeg"><button data-v="3y">3 年</button><button data-v="5y">5 年</button><button data-v="10y">10 年</button><button data-v="custom">自訂</button></div>
      <select id="etfFrom" class="etsel" aria-label="自訂起始年" hidden></select>
      <div class="seg" id="etfBasisSeg"><button data-v="tr">含息</button><button data-v="price">不含息</button></div>
    </div></div>
  ${how('etfret', '這張回答：同一型的前五大，長期抱下來誰報酬好？配息算進去差多少？', [
    '<b>前五名</b>＝該分類裡規模（集保單位數 × 收盤）最大的 5 檔；沒有規模資料時以近 20 日均成交值排。',
    '<b>價格年化（不含息）</b>＝(期末收盤 ÷ 期初收盤)^(1/年數) − 1；分割（例：0050 2025-06 一拆四）已還原，配息不算進去。',
    '<b>含息總報酬年化</b>＝配息在除息日以當天收盤再投入（還原權值）後的年化報酬。',
    '<b>期間平均殖利率</b>＝期間累計配息 ÷ 年數 ÷ 期間平均收盤；<b>配息年化</b>＝(1 ＋ 期間累計配息 ÷ 期初收盤)^(1/年數) − 1。',
    '期間：3／5／10 年＝從資料最後一天往回推；自訂＝從該年 1 月第一個交易日到最新。<b>上市未滿</b>或湖裡沒有那段歷史的，一律標「上市未滿 N 年／價量歷史尚未回補」，不以 0 或外插代替。',
    '所以：左圖看一路走勢（同起點 = 0%），右圖直接比年化數字；含息與不含息差距越大，代表報酬越依賴配息。'])}
  <p class="etfq">回答：<b>同一型的前五大，長期抱下來誰報酬好？配息算進去差多少？</b></p>
  <div id="etfRetBody"></div>
</div>`;
  }

  /* ------------------------------------------------------------------ 1. 卡片清單 */
  function sortVal(it) {
    if (S.sort === 'size') return it.size == null ? -Infinity : it.size;
    if (S.sort === 'yield') return it.yield_ttm == null ? -Infinity : it.yield_ttm;
    if (S.sort === 'chg') return it.chg_pct == null ? -Infinity : it.chg_pct;
    return (it.tv20 != null ? it.tv20 : it.tv) || 0;
  }
  function spark(code) {
    const a = A();
    return a.sparkSVG ? `<span class="spkw" data-spk="${esc(code)}" data-w="80" data-h="26">${a.sparkSVG(code, { w: 80, h: 26 })}</span>` : '';
  }
  function cardHTML(it) {
    const y = it.yield_ttm != null ? pctU(it.yield_ttm) : '—';
    const fq = it.freq || '—';
    return `<button type="button" class="etfc" data-code="${esc(it.code)}" title="進 ${esc(it.name)} 個股頁">
  <div class="h"><span class="nm">${esc(it.name)}</span><span class="cd">${esc(it.code)}</span><span class="sp" style="flex:1"></span>
    <span class="etag ${CAT_TONE[it.cat] || 'ink3'}">${esc(it.cat)}</span></div>
  <div class="px"><b class="${cls(it.chg_pct)}" data-live="close" data-code="${esc(it.code)}">${it.close != null ? A().fmt.n(it.close, 2) : '—'}</b>
    <span class="${cls(it.chg_pct)}" data-live="chg" data-code="${esc(it.code)}">${it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—'}</span>
    <span class="sp"></span>${spark(it.code)}</div>
  <dl><dt>成交值${it.tv20 != null ? '（20日均）' : ''}</dt><dd>${yi(it.tv20 != null ? it.tv20 : it.tv)}</dd>
      <dt>殖利率</dt><dd>${y}</dd><dt>配息頻率</dt><dd>${esc(fq)}</dd><dt>規模（估）</dt><dd>${yi(it.size)}</dd></dl>
</button>`;
  }
  function drawList() {
    const all = items();
    const cnt = {}; all.forEach((it) => { cnt[it.cat] = (cnt[it.cat] || 0) + 1; });
    const seg = $('#etfCatSeg');
    seg.innerHTML = `<button data-v="all" role="tab">全部 ${all.length}</button>` + CATS.filter((c) => cnt[c])
      .map((c) => `<button data-v="${c}" role="tab">${c} ${cnt[c]}</button>`).join('');
    $$('button', seg).forEach((b) => { b.classList.toggle('on', b.dataset.v === S.cat); b.setAttribute('aria-selected', b.dataset.v === S.cat);
      b.onclick = () => { S.cat = b.dataset.v; S.shown = PAGE; LS.set('tw.etf.cat', S.cat); drawList(); }; });
    const list = all.filter((it) => S.cat === 'all' || it.cat === S.cat).sort((a, b) => sortVal(b) - sortVal(a));
    $('#etfCount').textContent = `${list.length} 檔${S.data.asof ? '・資料日 ' + S.data.asof : ''}`;
    const g = $('#etfGrid');
    g.innerHTML = list.slice(0, S.shown).map(cardHTML).join('') || '<div class="etfprep">這個分類目前沒有 ETF。</div>';
    $$('.etfc', g).forEach((c) => { c.onclick = () => A().goStock(c.dataset.code); });
    const more = $('#etfMore'); more.hidden = list.length <= S.shown;
    more.textContent = `顯示更多（還有 ${Math.max(0, list.length - S.shown)} 檔）`;
    more.onclick = () => { S.shown += PAGE; drawList(); };
    $('#etfFbNote').innerHTML = S.fallback
      ? '<span class="note">（ETF 專區資料準備中：目前依名稱暫分，殖利率／配息頻率／規模待資料產出後顯示）</span>' : '';
    g.dataset.n = String(Math.min(list.length, S.shown)); g.dataset.cat = S.cat;
  }

  /* ------------------------------------------------------------------ 2. 熱門前 5 */
  function drawPop() {
    const box = $('#etfPop');
    const P = (S.data && S.data.popular) || {};
    $$('#etfPopSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.pop);
      b.onclick = () => { S.pop = b.dataset.v; LS.set('tw.etf.pop', S.pop); drawPop(); }; });
    const codes = P[S.pop] || [];
    if (S.fallback || !codes.length) {
      box.innerHTML = `<div class="etfprep">${S.fallback ? '資料準備中：ETF 專區的排行要等下一次資料產出（etf.json）後才有。' : '這個口徑目前沒有資料（集保受益人數至少要兩週才算得出週增加）。'}</div>`;
      box.dataset.codes = ''; return;
    }
    const m = byCode();
    const wk = P.holders_week || [];
    $('#etfPopSub').textContent = S.pop === 'holders' && wk[1] ? `集保 ${wk[0] || '?'} → ${wk[1]}` : '近 20 個交易日';
    box.innerHTML = '<div class="poplist">' + codes.map((c, i) => {
      const it = m.get(c) || { code: c, name: c };
      const mv = S.pop === 'holders' ? `受益人 ${it.d_holders > 0 ? '+' : ''}${A().fmt.i(it.d_holders)} 人`
        : `日均 ${yi(it.tv20)}`;
      return `<button type="button" class="popc" data-code="${esc(c)}"><div class="rk">${i + 1}</div>
        <div class="nm">${esc(it.name)} <span class="cd note">${esc(c)}</span></div>
        <div class="mv">${mv}</div><div class="note"><span class="etag ${CAT_TONE[it.cat] || 'ink3'}">${esc(it.cat || '')}</span>
        <span class="${cls(it.chg_pct)}">${it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : ''}</span></div></button>`;
    }).join('') + '</div>';
    box.dataset.codes = codes.join(',');
    $$('.popc', box).forEach((b) => { b.onclick = () => A().goStock(b.dataset.code); });
  }

  /* ------------------------------------------------------------------ 3. 配息行事曆 */
  function drawCal() {
    const box = $('#etfCal');
    const cal = (S.data && S.data.calendar) || [];
    if (S.fallback || !cal.length) {
      box.innerHTML = `<div class="etfprep">${S.fallback ? '資料準備中：配息行事曆要等 ETF 專區資料產出後才有。'
        : '配息資料尚未取得：ETF 的除息紀錄正在回補（歷史回補排程的 ETF 步驟），補進資料湖後這裡會自動出現。'}</div>`;
      $('#etfCalSub').textContent = ''; box.dataset.month = ''; return;
    }
    const asof = S.data.asof || cal[cal.length - 1].ex;
    if (!S.month) {
      const cur = asof.slice(0, 7);
      // 這個月還沒有任何除息就跳到下一個有資料的月份（最近的），避免一打開是空月曆
      S.month = cal.some((e) => e.ex.slice(0, 7) === cur) ? cur : (cal.find((e) => e.ex.slice(0, 7) >= cur) || cal[cal.length - 1]).ex.slice(0, 7);
    }
    const [y, mo] = S.month.split('-').map(Number);
    const first = new Date(Date.UTC(y, mo - 1, 1)), days = new Date(Date.UTC(y, mo, 0)).getUTCDate();
    const by = {}; cal.forEach((e) => { (by[e.ex] = by[e.ex] || []).push(e); });
    const ym = (d) => `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const nIn = cal.filter((e) => e.ex.slice(0, 7) === S.month).length;
    $('#etfCalSub').textContent = `${S.month} 共 ${nIn} 筆除息`;
    let cells = ['日', '一', '二', '三', '四', '五', '六'].map((w) => `<div class="wd">${w}</div>`).join('');
    for (let i = 0; i < first.getUTCDay(); i++) cells += '<div class="cald pad"></div>';
    for (let d = 1; d <= days; d++) {
      const k = ym(d), L = by[k] || [];
      cells += `<button type="button" class="cald${L.length ? ' has' : ''}${S.day === k ? ' sel' : ''}" data-d="${k}" ${L.length ? '' : 'tabindex="-1"'}
        aria-label="${k}${L.length ? ' 有 ' + L.length + ' 檔除息' : ''}"><span class="n">${d}</span>${L.length ? `<span class="c">${L.length} 檔</span>` : ''}</button>`;
    }
    const sel = S.day && by[S.day] ? by[S.day] : null;
    box.innerHTML = `<div class="calwrap"><div><div class="calhd"><button type="button" class="btn small" id="etfCalPrev" aria-label="上個月">‹ 上月</button>
      <b id="etfCalMonth">${y} 年 ${mo} 月</b><button type="button" class="btn small" id="etfCalNext" aria-label="下個月">下月 ›</button></div>
      <div class="calg" id="etfCalGrid">${cells}</div></div>
      <div class="callist" id="etfCalList">${sel ? calList(S.day, sel) : `<p class="note">點有標「檔」的日期，這裡列出當天除息的 ETF。</p>${monthList(cal.filter((e) => e.ex.slice(0, 7) === S.month))}`}</div></div>`;
    box.dataset.month = S.month; box.dataset.day = S.day || '';
    const shift = (n) => { const d = new Date(Date.UTC(y, mo - 1 + n, 1)); S.month = d.toISOString().slice(0, 7); S.day = null; drawCal(); };
    $('#etfCalPrev').onclick = () => shift(-1); $('#etfCalNext').onclick = () => shift(1);
    $$('.cald.has', box).forEach((c) => { c.onclick = () => { S.day = S.day === c.dataset.d ? null : c.dataset.d; drawCal(); }; });
    $$('tr[data-code]', box).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
  }
  function calRows(L, withDate) {
    return L.map((e) => `<tr data-code="${esc(e.code)}"><td>${withDate ? `<span class="note">${e.ex.slice(5)}</span> ` : ''}${esc(e.name)} <span class="note">${esc(e.code)}</span></td>
      <td>${A().fmt.n(e.amt, 3)}</td><td title="${esc(e.basis)}">${pctU(e.y)}${/估/.test(e.basis) ? '<span class="na">（估）</span>' : ''}</td><td>${e.pay ? e.pay.slice(5) : '<span class="na">—</span>'}</td></tr>`).join('');
  }
  function calList(day, L) {
    return `<b>${day} 除息（${L.length} 檔）</b><table class="et"><thead><tr><th>ETF</th><th>配息（元）</th><th>當次殖利率</th><th>發放日</th></tr></thead>
      <tbody>${calRows(L, false)}</tbody></table>`;
  }
  function monthList(L) {
    if (!L.length) return '<p class="note">這個月沒有除息紀錄。</p>';
    return `<table class="et"><thead><tr><th>ETF（除息日）</th><th>配息（元）</th><th>當次殖利率</th><th>發放日</th></tr></thead><tbody>${calRows(L, true)}</tbody></table>`;
  }

  /* ------------------------------------------------------------------ 4. 前五名報酬比較 */
  function perKey() { return S.per === 'custom' ? 'Y' + (S.from || '') : S.per; }
  function drawRet() {
    const body = $('#etfRetBody');
    $$('#etfGrpSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.grp); b.onclick = () => { S.grp = b.dataset.v; drawRet(); }; });
    $$('#etfPerSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.per); b.onclick = () => { S.per = b.dataset.v; drawRet(); }; });
    $$('#etfBasisSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.basis); b.onclick = () => { S.basis = b.dataset.v; drawRet(); }; });
    const sel = $('#etfFrom');
    const years = Object.keys((S.data && S.data.periods) || {}).filter((k) => k[0] === 'Y').map((k) => k.slice(1)).sort();
    if (!S.from && years.length) S.from = years[Math.max(0, years.length - 6)];
    sel.innerHTML = years.map((y) => `<option value="${y}"${y === S.from ? ' selected' : ''}>${y} 年起～至今</option>`).join('');
    sel.hidden = S.per !== 'custom';
    sel.onchange = () => { S.from = sel.value; drawRet(); };
    const codes = ((S.data && S.data.top) || {})[S.grp] || [];
    if (S.fallback || !codes.length) {
      body.innerHTML = `<div class="etfprep">${S.fallback ? '資料準備中：報酬比較要等 ETF 專區資料產出後才有。' : '這個分類目前沒有可比較的 ETF。'}</div>`;
      body.dataset.k = ''; return;
    }
    const m = byCode(), pk = perKey(), start = (S.data.periods || {})[pk];
    const rows = codes.map((c) => ({ it: m.get(c) || { code: c, name: c, stats: {} }, st: ((m.get(c) || {}).stats || {})[pk] || { ok: false, why: '無資料' } }));
    $('#etfRetSub').textContent = start ? `${start} 起～${S.data.asof}` : '';
    const isDiv = S.grp === '配息型';
    const num = (v, f) => (v == null ? '<span class="na">—</span>' : f(v));
    const why = (st) => `<span class="na">${esc(st.why || '無資料')}</span>`;
    body.innerHTML = `<div class="retcharts"><div><div class="note">累積報酬走勢（${S.basis === 'tr' ? '含息總報酬' : '價格，不含息'}；期初 = 0%）</div><div id="etfRetLine" class="chart"></div></div>
      <div><div class="note">年化報酬率（不含息 vs 含息）</div><div id="etfRetBar" class="chart"></div></div></div>
      <table class="et" id="etfRetTbl" style="margin-top:10px"><thead><tr><th>ETF</th><th>期間</th><th>價格年化（不含息）</th><th>含息總報酬年化</th>
      ${isDiv ? '<th>期間平均殖利率</th><th>配息年化</th>' : ''}<th>近 12 月殖利率</th></tr></thead><tbody>
      ${rows.map(({ it, st }) => `<tr data-code="${esc(it.code)}"><td>${esc(it.name)} <span class="note">${esc(it.code)}</span></td>
        ${st.ok ? `<td>${st.from}～ <span class="note">${st.years} 年</span></td><td class="${cls(st.price_ann)}">${num(st.price_ann, (v) => pct(v, 2))}</td>
        <td class="${cls(st.tr_ann)}">${st.tr_ann == null ? `<span class="na">${esc(st.why_div || '無資料')}</span>` : pct(st.tr_ann, 2)}</td>
        ${isDiv ? `<td>${num(st.avg_yield, (v) => pctU(v))}</td><td>${num(st.div_ann, (v) => pctU(v))}</td>` : ''}`
        : `<td colspan="${isDiv ? 5 : 3}">${why(st)}</td>`}
        <td>${num(it.yield_ttm, (v) => pctU(v))}</td></tr>`).join('')}</tbody></table>`;
    body.dataset.k = pk + '|' + S.grp + '|' + S.basis;
    $$('tr[data-code]', body).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
    drawRetCharts(rows, start);
  }
  function drawRetCharts(rows, start) {
    const a = A(), CH = a.CH, PAL = [CH.cyan, CH.amber, CH.violet, CH.lime, CH.up];
    const ser = (S.data && S.data.series) || {};
    const lines = [];
    rows.forEach(({ it, st }, i) => {
      const s = ser[it.code]; if (!s || !st.ok) return;
      const vals = S.basis === 'tr' ? s.t : s.p; if (!vals) return;
      let i0 = s.d.findIndex((d) => d >= st.from); if (i0 < 0) return;
      const base = vals[i0];
      lines.push({ name: `${it.name} ${it.code}`, type: 'line', showSymbol: false, smooth: false, lineStyle: { width: 1.8, color: PAL[i % 5] }, itemStyle: { color: PAL[i % 5] },
        data: s.d.slice(i0).map((d, j) => [d, +((vals[i0 + j] / base - 1) * 100).toFixed(2)]) });
    });
    const lineEl = $('#etfRetLine');
    if (!lines.length) {
      a.empty('etfRetLine', S.basis === 'tr' ? '含息走勢無資料（配息資料尚未取得，或期間內上市未滿）—— 可切「不含息」看價格走勢' : '這段期間沒有任何一檔有完整資料');
    } else {
      a.chart('etfRetLine', {
        grid: { left: 52, right: 14, top: 34, bottom: 28 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 }, type: 'scroll' },
        tooltip: { trigger: 'axis', valueFormatter: (v) => (v > 0 ? '+' : '') + v + '%' },
        xAxis: { type: 'time', ...a.axisStyle, splitLine: { show: false } },
        yAxis: { type: 'value', ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, formatter: (v) => v + '%' } },
        series: lines,
      });
    }
    if (lineEl) lineEl.dataset.n = String(lines.length);
    const ok = rows.filter(({ st }) => st.ok);
    if (!ok.length) { a.empty('etfRetBar', '這段期間前五名都資料不足（見下表理由）'); $('#etfRetBar').dataset.n = '0'; return; }
    const sorted = ok.slice().sort((x, y) => ((y.st.tr_ann != null ? y.st.tr_ann : y.st.price_ann) - (x.st.tr_ann != null ? x.st.tr_ann : x.st.price_ann)));
    const names = sorted.map(({ it }) => it.name);
    const v = (x) => (x == null ? null : +(x * 100).toFixed(2));
    a.chart('etfRetBar', {
      grid: { left: 96, right: 40, top: 30, bottom: 24 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => (x == null ? '無資料' : x + '%') },
      xAxis: { type: 'value', ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, formatter: (x) => x + '%' } },
      yAxis: { type: 'category', inverse: true, data: names, ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, fontSize: 12, width: 86, overflow: 'truncate' } },
      series: [
        { name: '不含息', type: 'bar', data: sorted.map(({ st }) => v(st.price_ann)), itemStyle: { color: CH.cyan }, barMaxWidth: 14,
          label: { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '' : p.value + '%') } },
        { name: '含息', type: 'bar', data: sorted.map(({ st }) => v(st.tr_ann)), itemStyle: { color: CH.amber }, barMaxWidth: 14,
          label: { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '無資料' : p.value + '%') } },
      ],
    });
    $('#etfRetBar').dataset.n = String(ok.length);
  }

  /* ------------------------------------------------------------------ 入口 */
  async function render() {
    injectCSS();
    const root = document.getElementById('v-etf'); if (!root) return;
    S.cat = LS.get('tw.etf.cat', 'all'); S.pop = LS.get('tw.etf.pop', 'holders');
    skeleton(root);
    $('#etfSort').onchange = (e) => { S.sort = e.target.value; S.shown = PAGE; drawList(); };
    $('#etfGrid').innerHTML = '<div class="etfprep">載入中…</div>';
    await loadData();
    if (S.cat !== 'all' && !items().some((it) => it.cat === S.cat)) S.cat = 'all';
    drawPop(); drawList(); drawCal(); drawRet();
    root.dataset.ready = S.fallback ? 'fallback' : 'full';
  }
  window.TwEtfPage = { render, classify, state: S };
})();
