/* 交易練習室回測 Worker：大量計算（參數掃描、全歷史 × 21 種策略）不卡頁面。引擎本體在 engine.js，這裡只收發訊息。 */
'use strict';
importScripts('engine.js' + (self.location.search || ''));
self.onmessage = function (e) {
  const m = e.data;
  try { self.postMessage({ id: m.id, ok: true, res: self.LabEngine.handle(m) }); }
  catch (err) { self.postMessage({ id: m.id, ok: false, err: String(err && err.message || err) }); }
};
