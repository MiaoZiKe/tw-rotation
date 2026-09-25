/* ============================================================================
   積木 `broker.views`　券商觀點（目標價／評等／調升調降）　法遵 🔴🔴
   ----------------------------------------------------------------------------
   為什麼要單獨一支檔（docs/feature_modules.md §4 第 2 項，2026-09-24 第一梯次）：
     這份資料以前**沒有邊界** —— 同一份 `broker_views` 被兩個地方各自拆欄位、各自拼字串：
       · 個股頁「公告 / 新聞」分頁的「券商觀點（新聞引述）」表格（industry.js tabNews）
       · 右側「今日事件」抽屜的「券商」分類（app.js renderEvents）
     而它是全站法遵風險最高的一塊（`docs/compliance_and_tiers.md`：士林地院 107 金訴 2，
     「把各家投顧分析師的分析與投資建議納入自己網站，即屬 §4 之行為」）。
     混在兩支檔裡，要「拿掉 rating 欄位」或「整塊關掉」就得在兩個地方找字串 —— 一定會漏一個。

   規則（原則二「積木之間只准透過資料溝通」的具體版本）：
     · **一份輸入**：`broker_views` 的列（`broker_views.json` 或個股頁 JSON 裡的同名欄位）。
     · **一個出口**：`BrokerViews.view(rows, as, fmt)`。`as` 決定長相：
         'feed' → 給事件抽屜的清單項目（陣列）
         'card' → 給個股頁的表格卡片（HTML 字串）
     · **欄位只在 `pick()` 裡決定**。compliance §2-5 第 4 項「連免費層都拿掉 rating」
       就是改 `pick()` 一行，兩處同時生效。
     · 可以單獨關掉：這支檔不載入時，兩個呼叫端都拿到「空」（見 app.js／industry.js 的 `window.BrokerViews &&`），
       事件抽屜少一類、個股頁少一張卡，其他東西照常。

   ⚠ 這一批是**純重構**：輸出的字串與物件跟搬家前一個字元都不差（桌機 1440／手機 390 逐頁像素比對）。
     所以 `b.date` 在表格裡仍然沒有經過 esc（搬家前就是這樣，資料來源是自家管線的 ISO 日期）。
   ============================================================================ */
(function () {
  'use strict';

  /* 對外露出哪些欄位 —— 全站唯一決定的地方。 */
  function pick(b) {
    return {
      date: b.date, broker: b.broker, target_price: b.target_price,
      action: b.action, rating: b.rating, name: b.name, code: b.code, url: b.url,
    };
  }

  /* 事件抽屜的一則。欄位形狀跟 news.json 的一則對齊（date／title／url／source／cat／code），
     抽屜那邊才能把兩種來源混在同一份清單裡排序。 */
  function feedItem(b) {
    return {
      date: b.date,
      title: `${b.broker || '券商'} 目標價 ${b.target_price}${b.name ? '（' + b.name + ' ' + b.code + '）' : ''}${b.action ? ' · ' + b.action : ''}`,
      url: b.url, source: '新聞引述', cat: '券商', code: b.code,
    };
  }

  /* 個股頁的表格卡片。點一列開原始新聞（我們只引述，不轉述）。 */
  function card(rows, fmt) {
    const esc = fmt.esc, n = fmt.n;
    return `<div class="card"><h3>券商觀點（新聞引述） <small data-warn>不是本站預估</small></h3>${rows.length ? `<div class="tw"><table><thead><tr><th class="l">日期</th><th class="l">券商</th><th>目標價</th><th class="l">動作</th></tr></thead><tbody>${rows.map(b => `<tr onclick="window.open('${esc(b.url || '#')}','_blank')"><td class="l mono">${b.date}</td><td class="l">${esc(b.broker || '—')}</td><td class="num">${n(b.target_price)}</td><td class="l">${esc(b.action || b.rating || '—')}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">近 60 天沒有引述到目標價的新聞</div>'}</div>`;
  }

  /* 唯一的出口。`fmt` 是全站共用的格式化工具（App.fmt），不是別塊積木的內部函式。 */
  function view(rows, as, fmt) {
    const list = (rows || []).map(pick);
    if (as === 'feed') return list.map(feedItem);
    if (as === 'card') return card(list, fmt || (window.App && window.App.fmt));
    throw new Error('BrokerViews.view：不認得的 as＝' + as);
  }

  window.BrokerViews = { id: 'broker.views', view };
})();
