/* ============================================================================
   積木 `stock.mtf`　個股頁「AI 分析」卡（多週期＋籌碼＋基本＋消息，規則式自動判讀）　法遵 🔴
   ----------------------------------------------------------------------------
   Andy 2026-09-26（#stock/3026 禾伸堂）：「觀望部分需要標示 AI 分析，並且需要說明原因；
   AI 分析是可以收納的選項，與多週期合併，裡面分析需要分不同時間週期的說明（只到週級別）
   → 這是技術面，需要有籌碼面、基本面、消息面看法」。

   取代兩塊：K 線卡右上的判讀卡（#skVerdict）與下方「多週期判讀」卡（#mtfCard）。
   版面的取捨（為什麼右上留一行、卡片放原多週期的位置）：
     · 右上那一行（#skAiLine）是**第一屏就看得到的結論**：狀態（觀望／可留意／偏空）＋一句帶數字的原因
       ＋四個面向的標籤。只有一行高，不再把 K 線工具列往下推。
     · 完整分析（#aiCard）放在 K 線與分頁之間，也就是原本多週期判讀的位置 —— 讀完圖往下捲就接著看原因。
     · 卡片標題列（含同一行結論與四個標籤）永遠顯示；內文可收合，狀態記在 localStorage `tw.aiOpen`。
       沒記過的人：桌機預設展開（Andy 要看原因）、手機（≤640）預設收起（內文很長，收起來才滑得到分頁）。
     · 右上「展開分析 ▾」＝展開卡片並捲過去；兩個入口改的是同一個狀態。

   ⚠ 誠實標示：內容全部來自 payload 的 `analysis`（pipeline/compute/analysis.py），
     是寫死的規則＋數字組出來的，**不是大型語言模型**。標題寫「AI 分析」是 Andy 要的字樣，
     旁邊一定緊接「規則式自動判讀，非投資建議」，「?」裡寫清楚依哪些規則與資料。
     所有文字是描述式／條件式（「目前…」「若…則…」），不寫買進、賣出這類指示用語。

   規則（跟 stock_signal.js 同一套積木規矩）：
     · 一份輸入：個股頁 JSON（讀 analysis、verdict、mtf.summary 三個欄位，其餘不讀）
     · 出口：line(pg) → 右上一行的 HTML；card(pg) → 卡片內部 HTML；mount(pg, host) → 畫進去並掛事件
     · 這支檔不載入時，industry.js 不畫這兩塊，其他照常（可以單獨關閉）
   ============================================================================ */
(function () {
  'use strict';

  const KEY = 'tw.aiOpen';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const FACETS = [['tech', '技術面'], ['chip', '籌碼面'], ['fund', '基本面'], ['news', '消息面']];
  const SHORT = { tech: '技術', chip: '籌碼', fund: '基本', news: '消息' };
  // 紅漲綠跌：偏多用 .pos（紅）、偏空用 .neg（綠）；留意＝琥珀色
  const toneCls = (lb) => lb === '偏多' ? 'pos' : lb === '偏空' ? 'neg' : lb === '留意' ? 'warn' : '';
  const stanceCls = (s) => s === '可留意' ? 'A' : s === '偏空' ? 'N' : 'W';

  function readOpen() {
    try { const v = localStorage.getItem(KEY); if (v === '1' || v === '0') return v === '1'; } catch (e) { /* 私密視窗 */ }
    return !(window.innerWidth <= 640);
  }
  function saveOpen(v) { try { localStorage.setItem(KEY, v ? '1' : '0'); } catch (e) { /* 忽略 */ } }

  function css() {
    if (document.getElementById('stockAiCss')) return;
    const st = document.createElement('style');
    st.id = 'stockAiCss';
    st.textContent = `
.ailine{display:flex;flex-direction:column;gap:6px;align-items:flex-end;max-width:560px;min-width:0}
.ailine .r1{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.ailine .aibrief{color:var(--ink-2);font-size:13px;line-height:1.45}
.ailine .aitags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.aitag{padding:2px 8px;border-radius:6px;font-size:12px;background:var(--panel-3);color:var(--ink-2);white-space:nowrap}
.aitag.pos{background:rgba(255,77,109,.16);color:var(--rise)} .aitag.neg{background:rgba(46,229,157,.16);color:var(--fall)}
.aitag.warn{background:rgba(255,180,84,.16);color:var(--amber)}
.grade.N{background:rgba(46,229,157,.16);color:var(--fall)}
#aiCard .aihead{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
#aiCard .aihead h3{margin:0;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#aiCard .aihead h3 small{font-size:12px;color:var(--amber);font-weight:500}
#aiCard .aisum{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:13.5px;color:var(--ink-2)}
#aiCard .aibody{margin-top:12px}
#aiCard .aisec{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
#aiCard .aisec:first-child{border-top:0;padding-top:0;margin-top:0}
#aiCard .aisec h4{margin:0 0 6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#aiCard .aisec h4 .why{font-weight:400;font-size:13px;color:var(--ink-2)}
#aiCard ul{margin:4px 0 0;padding-left:18px;color:var(--ink-2);font-size:13.5px;line-height:1.6}
#aiCard li{margin:2px 0}
#aiCard .aitfs{display:grid;grid-template-columns:auto auto 1fr;gap:6px 10px;align-items:baseline;font-size:13.5px}
#aiCard .aitfs .tfn{color:var(--ink-3);white-space:nowrap}
#aiCard .aitfs .tfp{color:var(--ink-2);line-height:1.55}
#aiCard .aisub{margin-top:10px;font-size:13px;color:var(--ink-3);font-weight:600}
#aiCard .aigrid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
#aiCard .aigrid3 .aisec{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
#aiCard .ailv{display:grid;grid-template-columns:1fr 1fr;gap:12px}
#aiCard .ailv .k{background:var(--panel-3);border-radius:9px;padding:6px 10px;margin-top:6px;font-size:13px}
#aiCard .ailv .k b{font-family:var(--mono)}
#aiCard details.aick{margin-top:8px;font-size:13px;color:var(--ink-2)}
#aiCard details.aick summary{cursor:pointer;color:var(--ink-3)}
#aiCard .ck{display:flex;gap:6px;margin:3px 0} #aiCard .ck .m{flex:none;width:14px;font-weight:700}
#aiCard .ck.ok .m{color:var(--rise)} #aiCard .ck.no .m{color:var(--ink-3)}
#aiCard .ainews a{color:var(--cyan)}
#aiCard .ainews .kind{font-size:11.5px;color:var(--ink-3);margin-right:4px}
@media (max-width:1100px){ #aiCard .aigrid3{grid-template-columns:1fr} #aiCard .aigrid3 .aisec{margin-top:12px} }
@media (max-width:640px){
  .ailine{align-items:flex-start;max-width:none} .ailine .r1,.ailine .aitags{justify-content:flex-start}
  #aiCard .aitfs{grid-template-columns:auto 1fr} #aiCard .aitfs .tfp{grid-column:1 / -1;margin:-2px 0 4px}
  #aiCard .ailv{grid-template-columns:1fr}
}`;
    document.head.appendChild(st);
  }

  function tags(an) {
    const f = (an && an.facets) || {};
    return FACETS.map(([k]) => {
      const x = f[k] || {}; const lb = x.label || '資料缺';
      return `<span class="aitag ${toneCls(lb)}" data-facet="${k}" title="${esc(x.why || '')}">${SHORT[k]} ${esc(lb)}</span>`;
    }).join('');
  }

  // 右上一行：狀態＋一句原因＋四個標籤＋「展開分析」鈕
  function line(pg) {
    css();
    const an = pg && pg.analysis;
    const v = (pg && pg.verdict) || {};
    const hd = (an && an.headline) || {};
    const stance = hd.stance || v.verdict || '—';
    const brief = hd.brief || ((v.reasons || [])[0] || '');
    return `<div class="ailine" id="skAiLine" data-readout>
      <div class="r1"><span class="grade ${stanceCls(stance)}" id="skAiStance">${esc(stance)}</span>
        <span class="aibrief">${esc(brief)}</span>
        <button class="btn small" id="aiJump" type="button" aria-controls="aiCard">${readOpen() ? '看分析 ↓' : '展開分析 ▾'}</button></div>
      ${an ? `<div class="aitags">${tags(an)}</div>` : ''}</div>`;
  }

  function facetHead(name, x) {
    const lb = (x && x.label) || '資料缺';
    return `<h4>${name} <span class="aitag ${toneCls(lb)}">${esc(lb)}</span><span class="why">${esc((x && x.why) || '')}</span></h4>`;
  }
  const ul = (arr) => arr && arr.length ? `<ul>${arr.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : '';

  function techHTML(t, fmt) {
    if (!t) return '';
    const tfs = (t.tfs || []).map(r => `<span class="tfn" data-tf="${esc(r.tf)}">${esc(r.label)}</span>`
      + `<span class="aitag ${r.trend > 0 ? 'pos' : r.trend < 0 ? 'neg' : ''}">${esc(r.word)}</span>`
      + `<span class="tfp">${esc((r.points || []).join('・'))}</span>`).join('');
    const ck = t.checks;
    const ckList = (arr) => (arr || []).map(c => `<div class="ck ${c.ok ? 'ok' : 'no'}"><span class="m">${c.ok ? '✓' : '✗'}</span><span><b>${esc(c.name)}</b>：${esc(c.text)}</span></div>`).join('');
    const lv = t.levels || {};
    const zrow = (z) => `<div class="k"><span class="muted">${esc(z.label || '')}</span> <b>${esc(fmt.n(z.low))} – ${esc(fmt.n(z.high))}</b> <span class="muted">距 ${esc(fmt.pct(z.dist_pct))}</span></div>`;
    return `<div class="aisec" data-facet="tech">${facetHead('技術面', t)}
      <div class="aitfs" id="aiTfs">${tfs}</div>
      <div class="aisub">綜合：<span class="grade ${stanceCls(t.stance)}">${esc(t.stance || '—')}</span> 的原因</div>
      <ul class="aiwhy" id="aiWhy">${(t.reasons || []).map(x => `<li>${esc(x)}</li>`).join('') || '<li>—</li>'}</ul>
      ${t.ifs && t.ifs.length ? `<div class="aisub">若…則…（狀態會在什麼情況下改變）</div>${ul(t.ifs)}` : ''}
      ${t.plan ? `<div class="aisub">${esc(t.plan)}</div>` : ''}
      ${ck ? `<details class="aick"><summary>逐條條件：回檔型態 ${ck.met_a}/${ck.n_a}・突破型態 ${ck.met_b}/${ck.n_b}</summary>
        <div class="aisub">回檔型態（A）</div>${ckList(ck.a)}
        <div class="aisub">突破型態（B）</div>${ckList(ck.b)}
        ${ck.risk && ck.risk.a ? `<div class="ck ${ck.risk.a.ok ? 'ok' : 'no'}"><span class="m">${ck.risk.a.ok ? '✓' : '✗'}</span><span><b>停損距離</b>：${esc(ck.risk.a.text)}</span></div>` : ''}
      </details>` : ''}
      <div class="aisub">支撐／壓力區（1 小時～週線，由近到遠）</div>
      <div class="ailv"><div>${(lv.support || []).map(zrow).join('') || '<div class="k muted">下方沒有通過門檻的需求區</div>'}</div>
        <div>${(lv.resistance || []).map(zrow).join('') || '<div class="k muted">上方沒有通過門檻的供給區</div>'}</div></div>
    </div>`;
  }

  function newsHTML(x) {
    if (!x) return '';
    const items = (x.items || []).map(it => {
      const d = esc(String(it.date || '').slice(5));
      if (it.kind === '新聞' && it.url) {
        return `<li><span class="kind">新聞</span><span class="mono">${d}</span> <a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a></li>`;
      }
      return `<li><span class="kind">${esc(it.kind)}</span><span class="mono">${d}</span> <a href="#" data-aitab="news">${esc(it.title)}</a></li>`;
    }).join('');
    return `<div class="aisec" data-facet="news">${facetHead('消息面', x)}${ul(x.points)}
      ${items ? `<div class="aisub">最新 ${(x.items || []).length} 則</div><ul class="ainews">${items}</ul>` : ''}</div>`;
  }

  function card(pg, fmt) {
    const an = pg && pg.analysis;
    const open = readOpen();
    const how = window.App && window.App.howHTML ? window.App.howHTML('這張卡：四個面向的規則式判讀。', [
      '「AI 分析」是寫死的規則算的，非語言模型',
      '技術：SMC 結構、均線、RSI、支撐壓力',
      '狀態＝回檔、突破兩套型態條件是否成立',
      '籌碼看法人融資集保；基本看估值營收 EPS',
      '消息只數公告新聞；四面向不加總、非建議',
    ]) : '';
    const head = `<div class="aihead"><h3>AI 分析 <small data-warn id="aiWarn" title="這張卡由固定規則與公開資料自動產生（technical_score、SMC 結構、A／B 進場條件、法人／融資／集保、本益比分位、營收與 EPS、公告新聞則數），不是大型語言模型，也不是任何人的投資建議。同一份資料永遠得到同一段文字。">規則式自動判讀，非投資建議</small>
        <button class="howbtn pop" data-how="ai" type="button" aria-label="AI 分析怎麼看">?</button></h3>
      <button class="btn small" id="aiTgl" type="button" aria-expanded="${open}" aria-controls="aiBody">${open ? '收合 ▴' : '展開 ▾'}</button></div>
      <div class="howtxt" id="how-ai" hidden>${how}</div>`;
    if (!an) {
      const sm = pg && pg.mtf && pg.mtf.summary;
      return head + `<div class="aisum" data-readout>${sm && sm.headline ? esc(sm.headline) : '資料不足'}</div>
        <div class="aibody" id="aiBody"${open ? '' : ' hidden'}><div class="empty">這一版資料包還沒有 AI 分析（下一次盤後更新後出現）</div></div>`;
    }
    const hd = an.headline || {}, f = an.facets || {};
    return head + `<div class="aisum" data-readout><span class="grade ${stanceCls(hd.stance)}">${esc(hd.stance || '—')}</span><span>${esc(hd.brief || '')}</span>${tags(an)}</div>
      <div class="aibody" id="aiBody" data-readout${open ? '' : ' hidden'}>
        ${techHTML(f.tech, fmt)}
        <div class="aigrid3">
          <div class="aisec" data-facet="chip">${facetHead('籌碼面', f.chip)}${ul((f.chip || {}).points)}</div>
          <div class="aisec" data-facet="fund">${facetHead('基本面', f.fund)}${ul((f.fund || {}).points)}</div>
          ${newsHTML(f.news)}
        </div>
        <div class="note" style="margin-top:12px">資料到 ${esc(an.as_of || '—')}</div>
      </div>`;
  }

  function setOpen(host, v) {
    const body = host.querySelector('#aiBody'), tgl = host.querySelector('#aiTgl'), jump = document.getElementById('aiJump');
    if (body) body.hidden = !v;
    if (tgl) { tgl.textContent = v ? '收合 ▴' : '展開 ▾'; tgl.setAttribute('aria-expanded', String(v)); }
    if (jump) jump.textContent = v ? '看分析 ↓' : '展開分析 ▾';
    host.classList.toggle('aiopen', !!v);
  }

  function mount(pg, host, fmt) {
    if (!host) return;
    css();
    host.innerHTML = card(pg, fmt);
    setOpen(host, readOpen());
    const tgl = host.querySelector('#aiTgl');
    if (tgl) tgl.onclick = () => { const v = host.querySelector('#aiBody').hidden; saveOpen(v); setOpen(host, v); };
    const jump = document.getElementById('aiJump');
    if (jump) jump.onclick = () => {
      saveOpen(true); setOpen(host, true);
      /* 手機是分段導覽（app.js miaPager）：卡片在「AI 分析」那一段，沒切過去時整塊是藏著的（.mp-off），
         直接 scrollIntoView 什麼都看不到 —— 先按那一段的分頁鈕。*/
      if (host.classList.contains('mp-off')) {
        const tab = [...document.querySelectorAll('.mpager button')].find(b => b.textContent.trim() === 'AI 分析');
        if (tab) tab.click();
      }
      try { host.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { host.scrollIntoView(); }
    };
    // 重大訊息沒有外部網址：點標題切到下方「公告 / 新聞」分頁（站內既有的那一頁，有觀測站連結與全文摘要）
    host.querySelectorAll('[data-aitab]').forEach(a => a.onclick = (e) => {
      e.preventDefault();
      const b = document.querySelector(`#stockTabs button[data-t="${a.dataset.aitab}"]`);
      if (b) { b.click(); try { b.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (er) { b.scrollIntoView(); } }
    });
  }

  window.StockAI = { id: 'stock.mtf', line, card, mount, _key: KEY };
})();
