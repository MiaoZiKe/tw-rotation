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

  function view(input, fmt) {
    const s = (input && input.summary) || {};
    const verdict = input && input.verdict;
    return `<div class="card"><h3>技術面訊號</h3><div class="lights" style="margin-top:8px">${[['均線', s.ma_align > 0 ? '多頭排列' : s.ma_align < 0 ? '空頭排列' : '糾結', s.ma_align], ['結構', s.trend > 0 ? '多頭（HH/HL）' : s.trend < 0 ? '空頭（LH/LL）' : '盤整', s.trend], ['RSI', s.rsi != null ? s.rsi.toFixed(0) : '—', s.rsi > 50 ? 1 : -1], ['KD', s.k != null ? `K ${s.k.toFixed(0)} D ${s.d.toFixed(0)}` : '—', s.k > s.d ? 1 : -1], ['MACD OSC', s.osc != null ? s.osc.toFixed(2) : '—', s.osc > 0 ? 1 : -1], ['乖離 20', s.bias20 != null ? fmt.pct(s.bias20) : '—', 0], ['BOS', s.bos ? '出現' : '—', s.bos ? 1 : 0], ['CHoCH', s.choch ? '出現' : '—', s.choch ? 1 : 0], ['假跌破', s.sweep_low ? '出現' : '—', s.sweep_low ? 1 : 0]].map(x => `<span class="light ${x[2] > 0 ? 'pos' : x[2] < 0 ? 'neg' : ''}">${x[0]} ${x[1]}</span>`).join('')}</div>${verdict && verdict.invalidation ? `<div class="note" data-readout style="margin-top:8px">失效條件：${fmt.esc(verdict.invalidation)}</div>` : ''}<div class="note" style="margin-top:6px" title="本頁為決策輔助，技術評分與規則權重尚未經 walk-forward 檢驗；不構成投資建議。">決策輔助，權重未經 walk-forward 檢驗；非投資建議</div></div>`;
  }

  window.StockSignal = { id: 'stock.signal', view };
})();
