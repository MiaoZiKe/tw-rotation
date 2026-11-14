// 讓 `node --test workers/ai-office-bridge/test/` 這種「指資料夾」的寫法也能跑（Node 22 會把資料夾當模組載入 index.js）。
// 正式的測試在 bridge.test.mjs；部署流程直接跑那支。
import('./bridge.test.mjs');
