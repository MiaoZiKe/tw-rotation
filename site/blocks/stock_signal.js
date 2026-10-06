/* ============================================================================
   積木 `stock.signal`　個股技術面訊號卡　法遵 🔴
   ----------------------------------------------------------------------------
   為什麼從 industry.js 搬出來（docs/feature_modules.md §4 第 3 項，2026-09-24 第一梯次）：
     個股頁「總覽」分頁以前是**一個 template literal 一次輸出三張卡**
     （基本面／籌碼快照／技術面訊號）。前兩張是公開財報與籌碼的事實（🟡），
     這一張是九顆燈號＋「失效條件」（`verdict.invalidation` ＝ 進出場規則，🔴）。
     綁在同一行字串裡，法遵分層表就放不下它 —— 要拿掉這張卡只能去改那一行長字串。

   規則：
     · **一份輸入**：`{ summary, verdict }`（個股頁 JSON 的同名兩個欄位），不讀別的。
     · **一個出口**：`StockSignal.view(input, fmt)` → 一張 `.card` 的 HTML 字串。
     · 可以單獨關掉：這支檔不載入時，industry.js 的總覽分頁只剩前兩張卡，其他照常。

   ⚠ 這一批是**純重構**：字串跟搬家前一個字元都不差（桌機 1440／手機 390 逐頁像素比對）。
     「本頁為決策輔助…不構成投資建議」是**全站目前唯一的一句免責**，跟著這張卡走 ——
     關掉這張卡的同時它也跟著消失，那是對的：沒有訊號就沒有需要免責的東西。
   ============================================================================ */
(function () {
  'use strict';

  /* ★ 2026-09-28：九顆燈號抽成 lights()，讓「AI 分析」的「技術面訊號」標籤頁（stock_ai.js）拿同一份，
     兩處永遠一致（Andy：「將 "AI分析" 內容替換掉 籌碼 -> 技術面訊號」）。回傳 [名稱, 值, 方向(+1/−1/0)]。
     ⚠ 沒有數值（—）的燈一律方向 0：以前 RSI／KD／MACD 缺值時被判成 −1（綠），AI 標籤頁的多空計數會把「缺資料」算成偏空。
       這張卡的外觀只有缺值那一格從綠變灰，有數值時跟以前一個字元都不差。*/
  function lights(s, fmt) {
    s = s || {};
    return [['均線', s.ma_align > 0 ? '多頭排列' : s.ma_align < 0 ? '空頭排列' : '糾結', s.ma_align > 0 ? 1 : s.ma_align < 0 ? -1 : 0],
      ['結構', s.trend > 0 ? '多頭（HH/HL）' : s.trend < 0 ? '空頭（LH/LL）' : '盤整', s.trend > 0 ? 1 : s.trend < 0 ? -1 : 0],
      ['RSI', s.rsi != null ? s.rsi.toFixed(0) : '—', s.rsi == null ? 0 : s.rsi > 50 ? 1 : -1],
      ['KD', s.k != null && s.d != null ? `K ${s.k.toFixed(0)} D ${s.d.toFixed(0)}` : '—', s.k == null || s.d == null ? 0 : s.k > s.d ? 1 : -1],
      ['MACD OSC', s.osc != null ? s.osc.toFixed(2) : '—', s.osc == null ? 0 : s.osc > 0 ? 1 : -1],
      ['乖離 20', s.bias20 != null ? fmt.pct(s.bias20) : '—', 0],
      ['BOS', s.bos ? '出現' : '—', s.bos ? 1 : 0], ['CHoCH', s.choch ? '出現' : '—', s.choch ? 1 : 0], ['假跌破', s.sweep_low ? '出現' : '—', s.sweep_low ? 1 : 0]];
  }
  const chip = (x) => `<span class="light ${x[2] > 0 ? 'pos' : x[2] < 0 ? 'neg' : ''}">${x[0]} ${x[1]}</span>`;

  /* ★ 2026-09-28（Andy：「我是要給讀者看，他不需要知道這類資訊」）：底下小字改前「權重未經 walk-forward 檢驗」
     是寫給開發者的回測術語 → 改後只留「決策輔助，非投資建議」，滑過說明也改成讀者語言。*/
  /* ★ 2026-10-02（DECISIONS #294）：個股「總覽」分頁改成四張面向小卡並排（技術面｜技術面訊號｜基本面｜消息面），
     這張就是第二張。第三個參數 o 可選：o.tag＝標題旁加「4多2空」小標籤（跟另外三張的「偏多／中性」同一個位置），
     o.id＝卡片 id（「AI 分析重點」的標籤點了要捲到這一張）。不給 o 時輸出跟改前一個字元都不差。*/
  function view(input, fmt, o) {
    const s = (input && input.summary) || {};
    const verdict = input && input.verdict;
    const L = lights(s, fmt);
    let tag = '';
    if (o && o.tag) {
      const pos = L.filter(x => x[2] > 0).length, neg = L.filter(x => x[2] < 0).length;
      tag = ` <span class="aitag ${pos > neg ? 'pos' : neg > pos ? 'neg' : ''}" title="九顆燈號：偏多 ${pos}、偏空 ${neg}">${pos}多${neg}空</span>`;
    }
    const attrs = o && o.id ? ` id="${o.id}" data-facet="sig"` : '';
    /* ★ 2026-10-07（Andy：統計計算、不構成投資建議的提醒放在上方、一行小字）：改前卡底「決策輔助，非投資建議」→ 改後標題下一行（放在 h3 裡、display:block 換行 —— 不直接掛在卡片底下，免得它的父元素就是有底色有框的卡片），
       跟全站同一句（App.DISC_LINE）。這張卡在 AI 卡裡面時（技術面那一面）AI 卡標題下已經有同一句，CSS 把這裡藏掉，不出現兩次。*/
    const DL = (window.App && window.App.DISC_LINE) || '以下為依公開資料統計計算之結果，不構成任何投資建議或參考';
    const disc = `<small class="sigdisc" role="note" data-sdisc="tech" title="燈號由固定規則計算，只描述目前的技術狀態，不構成投資建議。">${DL}</small>`;
    return `<div class="card"${attrs}><h3>技術面訊號${tag}${disc}</h3><div class="lights" style="margin-top:8px">${L.map(chip).join('')}</div>${verdict && verdict.invalidation ? `<div class="note" data-readout style="margin-top:8px">失效條件：${fmt.esc(verdict.invalidation)}</div>` : ''}</div>`;
  }

  window.StockSignal = { id: 'stock.signal', view, lights, chip };
})();
