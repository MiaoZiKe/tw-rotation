/* ============================================================================
   卡片標題小圖示（site/icons.js）—— 全站共用的一支機制
   ----------------------------------------------------------------------------
   Andy 2026-09-28：「圖五，需要將每個標題都新增小圖示，增加互動性，且需要對應配色」。
   規格與配色規則：docs/design_title_icons.md（設計系統的一節）。

   怎麼用（新卡片只要做其中一件）：
     1. 什麼都不做 —— 卡片標題（`.card h3` 等，見 AUTO）會依「標題文字」查 RULES 自動配圖示與語意色。
     2. 標題文字查不到、或想指定 → 在標題元素上加 `data-icon="<鍵>"`（鍵見 ICONS／ALIAS），
        語意色預設跟著圖示走（ICON_TONE），要改就再加 `data-tone="<語意>"`（見 TONES）。
     3. 不要圖示 → `data-icon="none"`。
   標題被 innerHTML 重畫、文字換掉（例如市場明細的分頁標題）都會自動補上／換掉：
   整頁掛一個 MutationObserver，一幀最多掃一次；掃完沒有變化就不動 DOM（不會自己觸發自己）。

   圖示來源：Lucide（ISC 授權；其中源自 Feather 的圖示為 MIT），只取內層 path 內嵌在這支檔裡，
   **不走 CDN**（Andy 公司網路擋 CDN）。授權全文：site/vendor/lucide.LICENSE。
   對照：本站鍵 → Lucide 名稱寫在 LUCIDE_NAME（換圖示時照名字回 lucide-static 找）。

   ⚠ 不動 `--dg-*`（剖析圖視覺變數歸 art-director）；不改標題列高度（圖示 18px，標題行高 ≥ 23px）。
   ============================================================================ */
(function () {
  'use strict';
  if (window.TwIcons) return;

  /* ---- 圖示（Lucide 24×24 內層） ---------------------------------------- */
  var ICONS = {
    "heart": "<path d=\"M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5\"/>",
    "pie": "<path d=\"M21 12c.552 0 1.005-.449.95-.998a10 10 0 0 0-8.953-8.951c-.55-.055-.998.398-.998.95v8a1 1 0 0 0 1 1z\"/> <path d=\"M21.21 15.89A10 10 0 1 1 8 2.83\"/>",
    "pulse": "<path d=\"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2\"/>",
    "up": "<path d=\"M16 7h6v6\"/> <path d=\"m22 7-8.5 8.5-5-5L2 17\"/>",
    "down": "<path d=\"M16 17h6v-6\"/> <path d=\"m22 17-8.5-8.5-5 5L2 7\"/>",
    "bars": "<path d=\"M3 3v16a2 2 0 0 0 2 2h16\"/> <path d=\"M18 17V9\"/> <path d=\"M13 17V5\"/> <path d=\"M8 17v-3\"/>",
    "bars-up": "<path d=\"M13 17V9\"/> <path d=\"M18 17V5\"/> <path d=\"M3 3v16a2 2 0 0 0 2 2h16\"/> <path d=\"M8 17v-3\"/>",
    "line": "<path d=\"M3 3v16a2 2 0 0 0 2 2h16\"/> <path d=\"M7 16c.5-2 1.5-7 4-7 2 0 2 3 4 3 2.5 0 4.5-5 5-7\"/>",
    "arrow-up": "<path d=\"M7 7h10v10\"/> <path d=\"M7 17 17 7\"/>",
    "scale": "<path d=\"M12 3v18\"/> <path d=\"m19 8 3 8a5 5 0 0 1-6 0zV7\"/> <path d=\"M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1\"/> <path d=\"m5 8 3 8a5 5 0 0 1-6 0zV7\"/> <path d=\"M7 21h10\"/>",
    "coins": "<path d=\"M13.744 17.736a6 6 0 1 1-7.48-7.48\"/> <path d=\"M15 6h1v4\"/> <path d=\"m6.134 14.768.866-.5 2 3.464\"/> <circle cx=\"16\" cy=\"8\" r=\"6\"/>",
    "sparkles": "<path d=\"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z\"/> <path d=\"M20 2v4\"/> <path d=\"M22 4h-4\"/> <circle cx=\"4\" cy=\"20\" r=\"2\"/>",
    "flame": "<path d=\"M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4\"/>",
    "radar": "<path d=\"M19.07 4.93A10 10 0 0 0 6.99 3.34\"/> <path d=\"M4 6h.01\"/> <path d=\"M2.29 9.62A10 10 0 1 0 21.31 8.35\"/> <path d=\"M16.24 7.76A6 6 0 1 0 8.23 16.67\"/> <path d=\"M12 18h.01\"/> <path d=\"M17.99 11.66A6 6 0 0 1 15.77 16.67\"/> <circle cx=\"12\" cy=\"12\" r=\"2\"/> <path d=\"m13.41 10.59 5.66-5.66\"/>",
    "compass": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z\"/>",
    "flow": "<circle cx=\"12\" cy=\"18\" r=\"3\"/> <circle cx=\"6\" cy=\"6\" r=\"3\"/> <circle cx=\"18\" cy=\"6\" r=\"3\"/> <path d=\"M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9\"/> <path d=\"M12 12v3\"/>",
    "split": "<path d=\"M16 3h5v5\"/> <path d=\"M8 3H3v5\"/> <path d=\"M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3\"/> <path d=\"m15 9 6-6\"/>",
    "treemap": "<rect width=\"7\" height=\"9\" x=\"3\" y=\"3\" rx=\"1\"/> <rect width=\"7\" height=\"5\" x=\"14\" y=\"3\" rx=\"1\"/> <rect width=\"7\" height=\"9\" x=\"14\" y=\"12\" rx=\"1\"/> <rect width=\"7\" height=\"5\" x=\"3\" y=\"16\" rx=\"1\"/>",
    "rotate": "<path d=\"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8\"/> <path d=\"M21 3v5h-5\"/> <path d=\"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16\"/> <path d=\"M8 16H3v5\"/>",
    "landmark": "<path d=\"M10 18v-7\"/> <path d=\"M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949z\"/> <path d=\"M14 18v-7\"/> <path d=\"M18 18v-7\"/> <path d=\"M3 22h18\"/> <path d=\"M6 18v-7\"/>",
    "users": "<path d=\"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2\"/> <path d=\"M16 3.128a4 4 0 0 1 0 7.744\"/> <path d=\"M22 21v-2a4 4 0 0 0-3-3.87\"/> <circle cx=\"9\" cy=\"7\" r=\"4\"/>",
    "target": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <circle cx=\"12\" cy=\"12\" r=\"6\"/> <circle cx=\"12\" cy=\"12\" r=\"2\"/>",
    "calendar": "<path d=\"M8 2v3\"/> <path d=\"M16 2v3\"/> <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/> <path d=\"M3 9h18\"/> <path d=\"M8 13h.01\"/> <path d=\"M12 13h.01\"/> <path d=\"M16 13h.01\"/> <path d=\"M8 17h.01\"/> <path d=\"M12 17h.01\"/> <path d=\"M16 17h.01\"/>",
    "news": "<path d=\"M15 18h-5\"/> <path d=\"M18 14h-8\"/> <path d=\"M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2\"/> <rect width=\"8\" height=\"4\" x=\"10\" y=\"6\" rx=\"1\"/>",
    "bell": "<path d=\"M10.268 21a2 2 0 0 0 3.464 0\"/> <path d=\"M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326\"/>",
    "building": "<path d=\"M10 12h4\"/> <path d=\"M10 8h4\"/> <path d=\"M14 21v-3a2 2 0 0 0-4 0v3\"/> <path d=\"M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2\"/> <path d=\"M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16\"/>",
    "file": "<path d=\"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z\"/> <path d=\"M14 2v5a1 1 0 0 0 1 1h5\"/> <path d=\"M10 9H8\"/> <path d=\"M16 13H8\"/> <path d=\"M16 17H8\"/>",
    "table": "<path d=\"M3 9h18\"/> <path d=\"M9 3v18\"/> <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/>",
    "cpu": "<path d=\"M12 20v2\"/> <path d=\"M12 2v2\"/> <path d=\"M17 20v2\"/> <path d=\"M17 2v2\"/> <path d=\"M2 12h2\"/> <path d=\"M2 17h2\"/> <path d=\"M2 7h2\"/> <path d=\"M20 12h2\"/> <path d=\"M20 17h2\"/> <path d=\"M20 7h2\"/> <path d=\"M7 20v2\"/> <path d=\"M7 2v2\"/> <rect x=\"4\" y=\"4\" width=\"16\" height=\"16\" rx=\"2\"/> <rect x=\"8\" y=\"8\" width=\"8\" height=\"8\" rx=\"1\"/>",
    "server": "<rect width=\"20\" height=\"8\" x=\"2\" y=\"2\" rx=\"2\" ry=\"2\"/> <rect width=\"20\" height=\"8\" x=\"2\" y=\"14\" rx=\"2\" ry=\"2\"/> <line x1=\"6\" x2=\"6.01\" y1=\"6\" y2=\"6\"/> <line x1=\"6\" x2=\"6.01\" y1=\"18\" y2=\"18\"/>",
    "board": "<rect width=\"18\" height=\"18\" x=\"3\" y=\"3\" rx=\"2\"/> <path d=\"M11 9h4a2 2 0 0 0 2-2V3\"/> <circle cx=\"9\" cy=\"9\" r=\"2\"/> <path d=\"M7 21v-4a2 2 0 0 1 2-2h4\"/> <circle cx=\"15\" cy=\"15\" r=\"2\"/>",
    "factory": "<path d=\"M12 16h.01\"/> <path d=\"M16 16h.01\"/> <path d=\"M3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5a.5.5 0 0 0-.769-.422l-4.462 2.844A.5.5 0 0 1 15 10.5v-2a.5.5 0 0 0-.769-.422L9.77 10.922A.5.5 0 0 1 9 10.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z\"/> <path d=\"M8 16h.01\"/>",
    "code": "<path d=\"m18 16 4-4-4-4\"/> <path d=\"m6 8-4 4 4 4\"/> <path d=\"m14.5 4-5 16\"/>",
    "network": "<rect x=\"16\" y=\"16\" width=\"6\" height=\"6\" rx=\"1\"/> <rect x=\"2\" y=\"16\" width=\"6\" height=\"6\" rx=\"1\"/> <rect x=\"9\" y=\"2\" width=\"6\" height=\"6\" rx=\"1\"/> <path d=\"M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3\"/> <path d=\"M12 12V8\"/>",
    "candle": "<path d=\"M9 5v4\"/> <rect width=\"4\" height=\"6\" x=\"7\" y=\"9\" rx=\"1\"/> <path d=\"M9 15v2\"/> <path d=\"M17 3v2\"/> <rect width=\"4\" height=\"8\" x=\"15\" y=\"5\" rx=\"1\"/> <path d=\"M17 13v3\"/> <path d=\"M3 3v16a2 2 0 0 0 2 2h16\"/>",
    "checks": "<path d=\"M13 5h8\"/> <path d=\"M13 12h8\"/> <path d=\"M13 19h8\"/> <path d=\"m3 17 2 2 4-4\"/> <path d=\"m3 7 2 2 4-4\"/>",
    "gauge": "<path d=\"m12 14 4-4\"/> <path d=\"M3.34 19a10 10 0 1 1 17.32 0\"/>",
    "banknote": "<rect width=\"20\" height=\"12\" x=\"2\" y=\"6\" rx=\"2\"/> <circle cx=\"12\" cy=\"12\" r=\"2\"/> <path d=\"M6 12h.01M18 12h.01\"/>",
    "waves": "<path d=\"M2 12q2.5 2 5 0t5 0 5 0 5 0\"/> <path d=\"M2 19q2.5 2 5 0t5 0 5 0 5 0\"/> <path d=\"M2 5q2.5 2 5 0t5 0 5 0 5 0\"/>",
    "layers": "<path d=\"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z\"/> <path d=\"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12\"/> <path d=\"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17\"/>",
    "clipboard": "<rect width=\"8\" height=\"4\" x=\"8\" y=\"2\" rx=\"1\" ry=\"1\"/> <path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\"/> <path d=\"m9 14 2 2 4-4\"/>",
    "crosshair": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <line x1=\"22\" x2=\"18\" y1=\"12\" y2=\"12\"/> <line x1=\"6\" x2=\"2\" y1=\"12\" y2=\"12\"/> <line x1=\"12\" x2=\"12\" y1=\"6\" y2=\"2\"/> <line x1=\"12\" x2=\"12\" y1=\"22\" y2=\"18\"/>",
    "updown": "<path d=\"m21 16-4 4-4-4\"/> <path d=\"M17 20V4\"/> <path d=\"m3 8 4-4 4 4\"/> <path d=\"M7 4v16\"/>",
    "wallet": "<path d=\"M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1\"/> <path d=\"M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4\"/>",
    "star": "<path d=\"M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z\"/>",
    "zap": "<path d=\"M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z\"/>",
    "hammer": "<path d=\"m15 12-9.373 9.373a1 1 0 0 1-3.001-3L12 9\"/> <path d=\"m18 15 4-4\"/> <path d=\"m21.5 11.5-1.914-1.914A2 2 0 0 1 19 8.172v-.344a2 2 0 0 0-.586-1.414l-1.657-1.657A6 6 0 0 0 12.516 3H9l1.243 1.243A6 6 0 0 1 12 8.485V10l2 2h1.172a2 2 0 0 1 1.414.586L18.5 14.5\"/>",
    "shopping": "<path d=\"m2.05 2.05 1.099-.028a1 1 0 0 1 1.008.815l2.69 14.347A1 1 0 0 0 7.83 18H18\"/> <path d=\"M4.563 5h16.435a1 1 0 0 1 .981 1.204l-1.026 6.226A2 2 0 0 1 18.962 14H6.25\"/> <circle cx=\"18\" cy=\"20\" r=\"2\"/> <circle cx=\"8\" cy=\"20\" r=\"2\"/>",
    "receipt": "<path d=\"M12 17V7\"/> <path d=\"M16 8h-6a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8\"/> <path d=\"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z\"/>",
    "percent": "<line x1=\"19\" x2=\"5\" y1=\"5\" y2=\"19\"/> <circle cx=\"6.5\" cy=\"6.5\" r=\"2.5\"/> <circle cx=\"17.5\" cy=\"17.5\" r=\"2.5\"/>",
    "hard-hat": "<path d=\"M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5\"/> <path d=\"M14 6a6 6 0 0 1 6 6v3\"/> <path d=\"M4 15v-3a6 6 0 0 1 6-6\"/> <rect x=\"2\" y=\"15\" width=\"20\" height=\"4\" rx=\"1\"/>",
    "leaf": "<path d=\"M11 20a10 10 0 0010-10 25.9 25.9 0 00-1.04-7.281 1 1 0 00-1.755-.325C15.833 5.5 13 5.5 9.8 6.1A7 7 0 0011 20\"/> <path d=\"M2 21a5 5 0 012.911-4.544C7.613 15.212 8.351 15.24 11 13\"/>",
    "box": "<path d=\"M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z\"/> <path d=\"m3.3 7 8.7 5 8.7-5\"/> <path d=\"M12 22V12\"/>"
  };
  var LUCIDE_NAME = { heart: 'heart', pie: 'chart-pie', pulse: 'activity', up: 'trending-up', down: 'trending-down',
    bars: 'chart-column', 'bars-up': 'chart-column-increasing', line: 'chart-spline', 'arrow-up': 'arrow-up-right',
    scale: 'scale', coins: 'coins', sparkles: 'sparkles', flame: 'flame', radar: 'radar', compass: 'compass',
    flow: 'git-fork', split: 'split', treemap: 'layout-dashboard', rotate: 'refresh-cw', landmark: 'landmark',
    users: 'users', target: 'target', calendar: 'calendar-days', news: 'newspaper', bell: 'bell',
    building: 'building-2', file: 'file-text', table: 'table-2', cpu: 'cpu', server: 'server', board: 'circuit-board',
    factory: 'factory', code: 'code-xml', network: 'network', candle: 'chart-candlestick', checks: 'list-checks',
    gauge: 'gauge', banknote: 'banknote', waves: 'waves', layers: 'layers', clipboard: 'clipboard-check',
    crosshair: 'crosshair', updown: 'arrow-up-down', wallet: 'wallet', star: 'star', zap: 'zap', hammer: 'hammer',
    shopping: 'shopping-cart', receipt: 'receipt', percent: 'percent', 'hard-hat': 'hard-hat', leaf: 'leaf', box: 'box' };

  /* 別名：其他 agent／舊習慣用 Lucide 原名或英文俗名也對得到 */
  var ALIAS = { 'git-branch': 'flow', 'git-fork': 'flow', sankey: 'flow', 'chart-pie': 'pie', activity: 'pulse',
    'trending-up': 'up', 'trending-down': 'down', 'chart-column': 'bars', 'chart-bar': 'bars',
    'chart-spline': 'line', 'chart-line': 'line', newspaper: 'news', 'building-2': 'building',
    'calendar-days': 'calendar', 'layout-dashboard': 'treemap', heatmap: 'treemap', 'refresh-cw': 'rotate',
    'chart-candlestick': 'candle', kline: 'candle', 'list-checks': 'checks', fire: 'flame', watch: 'heart',
    'clipboard-check': 'clipboard', 'table-2': 'table', 'arrow-up-right': 'arrow-up', 'circuit-board': 'board',
    'code-xml': 'code', 'arrow-up-down': 'updown', 'shopping-cart': 'shopping', ai: 'sparkles' };

  /* ---- 語意色（docs/design_title_icons.md §2） -------------------------
     語意 → 色。★ 這支檔**不寫任何色碼**：每個語意都對到主題本來就有的變數
     （--cyan／--violet／--amber／--lime／--rise／--fall），深淺主題、v4 三主題換了那組變數，圖示就跟著換，
     而那組變數本來就為了「對卡片底 ≥4.5」調過，所以圖形 ≥3:1 是站在它們肩膀上（_uitest「標題圖示」逐主題實量）。
     15 個語意收成 5 個色系（同一頁最多 5 種顏色，才叫「搭配」而不是彩虹）：
       資金面 M1（flow／rot／dest）→ --cyan；技術面 M3、K 線、AI（tech）→ --violet；
       基本面、產業（fund）→ --cyan 與 --violet 各半；題材熱度、估值、事件、股利、自選（heat／val／event／yield／watch）→ --amber；
       籌碼、營收成長（chip／grow）→ --lime；漲／跌（up／down）→ --rise／--fall（紅漲綠跌）。*/
  var TONES = {
    flow: 'sky',      // 資金、流向（青藍）
    rot: 'cyan',      // 輪動、輪盤（青）
    dest: 'blue',     // 資金去向、占比（藍）
    fund: 'blue',     // 基本面、產業結構（藍）
    grow: 'teal',     // 營收成長（青綠）
    tech: 'violet',   // 技術面、K 線、AI（紫）
    val: 'orange',    // 估值（橘）
    heat: 'heat',     // 熱門題材、成交量（橘紅）
    chip: 'emerald',  // 籌碼、法人（綠）
    event: 'yellow',  // 事件、新聞（黃）
    watch: 'rose',    // 自選（紅心）
    yield: 'pink',    // 股利、殖利率（粉）
    up: 'up',         // 漲、多（紅，＝ --rise）
    down: 'down',     // 跌、空（綠，＝ --fall）
    mix: 'mix'        // 漲跌並陳（上紅下綠漸層）
  };

  var ICON_TONE = { heart: 'watch', star: 'watch', pie: 'flow', pulse: 'mix', updown: 'mix', up: 'up', down: 'down',
    bars: 'fund', 'bars-up': 'fund', line: 'tech', candle: 'tech', checks: 'tech', gauge: 'tech', crosshair: 'tech',
    sparkles: 'tech', calendar: 'tech', 'arrow-up': 'grow', scale: 'val', waves: 'val', percent: 'val',
    coins: 'yield', receipt: 'yield', flame: 'heat', radar: 'rot', compass: 'rot', rotate: 'rot',
    flow: 'dest', split: 'dest', treemap: 'flow', table: 'flow', target: 'flow', landmark: 'chip', users: 'chip',
    banknote: 'chip', news: 'event', bell: 'event', zap: 'event', building: 'fund', file: 'fund', cpu: 'fund',
    server: 'fund', board: 'fund', factory: 'fund', code: 'fund', network: 'fund', layers: 'fund', clipboard: 'fund',
    wallet: 'fund', hammer: 'fund', shopping: 'fund', 'hard-hat': 'fund', leaf: 'fund', box: 'fund' };

  /* ---- 標題文字 → [圖示, 語意]（由上往下第一個比中的算；越特定的放越前面） ---- */
  var RULES = [
    // 自選
    [/^(觀察列表|觀察清單|自選|我的自選)/, 'heart', 'watch'],
    // 大盤、K 線
    [/^(加權指數|櫃買指數|台指期|大盤|指數|國際|美股)/, 'candle', 'tech'],
    [/^(分時|即時走勢|盤中走勢)/, 'line', 'tech'],
    // 資金面（M1）
    [/^資金熱力/, 'treemap', 'flow'],
    [/^(題材資金熱力|熱門題材|題材)/, 'flame', 'heat'],
    [/^(資金輪盤|足跡輪盤|輪盤)/, 'radar', 'rot'],
    [/^(資金輪動|輪動)/, 'rotate', 'rot'],
    [/^(昨日)?資金去向/, 'flow', 'dest'],
    [/^(資金流向排行|資金排行|資金流向)/, 'bars', 'flow'],
    [/^資金集中度/, 'target', 'flow'],
    [/^外資/, 'pie', 'flow'],
    [/^(全市場族群|成交值占比|成交值佔比|占比|佔比)/, 'pie', 'dest'],
    // 漲跌
    [/^漲跌家數/, 'pulse', 'mix'],
    [/^(漲跌分佈|漲跌分布|族群漲跌幅)/, 'bars', 'mix'],
    [/^(整個台股|產業熱力|熱力圖)/, 'treemap', 'mix'],
    [/^((當日|今日)?漲幅|強勢|漲停)/, 'up', 'up'],
    [/^((當日|今日)?跌幅|弱勢|跌停)/, 'down', 'down'],
    [/^(當日|今日)?成交(量|值)/, 'pulse', 'heat'],
    // 籌碼
    [/^籌碼集中/, 'bars', 'chip'],
    [/^(法人連續|族群 ?[×x] ?法人|三大法人|法人|投信|自營|主力)/, 'landmark', 'chip'],
    [/^(資券|融資|融券|借券)/, 'banknote', 'chip'],
    [/^(大戶|散戶|股東人數|千張)/, 'users', 'chip'],
    [/^籌碼/, 'bars', 'chip'],
    // 事件、新聞
    [/^(今日事件|事件)/, 'bell', 'event'],
    [/^(公告|新聞|券商觀點)/, 'news', 'event'],
    // 技術面（M3）
    [/^AI ?分析/, 'sparkles', 'tech'],
    [/^趨勢/, 'sparkles', 'tech'],
    [/^技術面/, 'line', 'tech'],
    [/^(符合.*指標|指標)/, 'checks', 'tech'],
    [/^站上均線/, 'line', 'tech'],
    [/^(今日候選|候選)/, 'crosshair', 'tech'],
    [/^(週期統計|季節性|1\s*[–-]\s*12 ?月)/, 'calendar', 'tech'],
    // 基本面（M2）／估值
    [/^月營收明細/, 'table', 'grow'],
    [/^逐年同月/, 'bars-up', 'grow'],
    [/^(營收)/, 'arrow-up', 'grow'],
    [/^本益比河流/, 'waves', 'val'],
    [/^(本益比|估值|股價淨值|PER?\b|PBR?\b)/, 'scale', 'val'],
    [/^(EPS|三率|獲利)/, 'bars-up', 'fund'],
    [/^(季報明細|財報)/, 'file', 'fund'],
    [/^基本面/, 'bars', 'fund'],
    [/^(基本資料|公司)/, 'building', 'fund'],
    [/^股利政策/, 'receipt', 'yield'],
    [/^股利公告/, 'news', 'yield'],
    [/^(各年度股利|股利|殖利率|高殖利率)/, 'coins', 'yield'],
    [/^除權息/, 'calendar', 'yield'],
    // 產業
    [/^半導體/, 'cpu', 'fund'],
    [/^AI ?伺服器/, 'server', 'fund'],
    [/^一般電子/, 'board', 'fund'],
    [/^軟體/, 'code', 'fund'],
    [/^金融/, 'wallet', 'fund'],
    [/^傳產/, 'factory', 'fund'],
    [/^基礎建設/, 'zap', 'fund'],
    [/^(供應鏈|關聯圖|產業關係)/, 'network', 'fund'],
    // 族群頁三欄（.gpcard > h5）：誰供給它／它供給誰／同業
    [/^上游/, 'box', 'fund'],
    [/^下游/, 'shopping', 'fund'],
    [/^同業/, 'users', 'fund'],
    [/^產品剖析/, 'layers', 'fund'],
    // 其他頁
    [/^市場明細/, 'table', 'flow'],
    [/^交付清單/, 'clipboard', 'fund']
  ];

  /* 標題文字比不中時，再看它所在卡片的 id（標題改字也不會掉圖示） */
  var CARD_ID = { ovHeatCard: ['treemap', 'flow'], ovThemeCard: ['flame', 'heat'], ovRotCard: ['radar', 'rot'],
    ovBreadthCard: ['pulse', 'mix'], ovTrustCard: ['landmark', 'chip'], flowRotCard: ['rotate', 'rot'],
    flowSankeyCard: ['flow', 'dest'], flowInstCard: ['landmark', 'chip'], flowConcCard: ['target', 'flow'],
    themeMapCard: ['flame', 'heat'], seasonHeatCard: ['calendar', 'tech'], indHeat: ['treemap', 'mix'],
    tagCard: ['checks', 'tech'], msCard: ['calendar', 'tech'], stockNews: ['news', 'event'],
    divPerCard: ['receipt', 'yield'], skAi: ['sparkles', 'tech'], side: ['bell', 'event'] };

  /* 會自動加圖示的標題。其餘地方要圖示就加 data-icon。*/
  var AUTO = [
    '.card h3', '.card h4.subh', '.card .rothead h4', '#ovFlowHead', '#relHead h4', '#gpTitle', '.gpcard > h5',
    '.nbhead > h2', '#v-delivery .card h2', '.mhead h3', '.side-h h3', '.m3-card h3', '.aihead h3', '[data-icon]'
  ].join(',');
  /* 不加：說明盒、外商小面板、對話框、剖析圖內部（--dg 歸 art-director）、個股名稱（左邊已經有公司 logo） */
  var SKIP = '.osc-ic, .howtxt, .howbox, #coBox, [role="dialog"], .modal, svg, .dg, [data-dg], #skIdent, .tip, .ttip';

  var SW = 1.75;
  var FALLBACK = ['bars', 'flow'];

  function norm(k) { k = String(k || '').trim().toLowerCase(); return ICONS[k] ? k : (ALIAS[k] || null); }

  function svg(key, size) {
    var k = norm(key) || FALLBACK[0], s = size || 17;
    return '<svg viewBox="0 0 24 24" width="' + s + '" height="' + s + '" fill="none" stroke="currentColor" stroke-width="' + SW +
      '" stroke-linecap="round" stroke-linejoin="round" focusable="false" aria-hidden="true">' + ICONS[k] + '</svg>';
  }

  /* 標題文字：只取文字節點與行內的 span／b／a（例如 #mktTitle），略過小字、按鈕、提示框 */
  function titleText(h) {
    var t = '';
    for (var i = 0; i < h.childNodes.length; i++) {
      var n = h.childNodes[i];
      if (n.nodeType === 3) t += n.nodeValue;
      else if (n.nodeType === 1 && /^(SPAN|B|A|STRONG|EM)$/.test(n.tagName) && !n.classList.contains('ticon') &&
               !n.classList.contains('rotlivewrap') && !n.hasAttribute('data-readout')) t += n.textContent;
    }
    return t.replace(/\s+/g, ' ').trim();
  }

  function resolve(h) {
    var di = h.getAttribute('data-icon');
    if (di === 'none') return null;
    var dt = h.getAttribute('data-tone');
    if (di) {
      var k = norm(di) || FALLBACK[0];
      return { k: k, tone: TONES[dt] ? dt : (ICON_TONE[k] || 'fund'), fb: !norm(di) };
    }
    var t = titleText(h);
    for (var i = 0; i < RULES.length; i++) {
      if (RULES[i][0].test(t)) return { k: RULES[i][1], tone: TONES[dt] ? dt : RULES[i][2], fb: false };
    }
    var c = h.closest('[id]');
    while (c) {
      if (CARD_ID[c.id]) return { k: CARD_ID[c.id][0], tone: TONES[dt] ? dt : CARD_ID[c.id][1], fb: false };
      c = c.parentElement && c.parentElement.closest('[id]');
    }
    if (h.closest('.m3-card')) return { k: 'candle', tone: 'tech', fb: false };
    return { k: FALLBACK[0], tone: TONES[dt] ? dt : FALLBACK[1], fb: true };
  }

  function decorate(h) {
    if (h.closest(SKIP)) return;
    var r = resolve(h);
    var cur = h.firstElementChild && h.firstElementChild.classList.contains('ticon') ? h.firstElementChild : null;
    if (!r) { if (cur) cur.remove(); return; }
    if (cur && cur.getAttribute('data-k') === r.k && cur.getAttribute('data-tone') === r.tone) return;
    var sp = cur || document.createElement('span');
    sp.className = 'ticon';
    sp.setAttribute('aria-hidden', 'true');
    sp.setAttribute('data-k', r.k);
    sp.setAttribute('data-tone', r.tone);
    if (r.fb) sp.setAttribute('data-fb', '1'); else sp.removeAttribute('data-fb');
    sp.innerHTML = svg(r.k);
    if (!cur) h.insertBefore(sp, h.firstChild);
    fixGap(h, sp);
    h._tiFit = '';
    watch(h);
  }

  /* 圖示與文字的距離固定 6px（＝ --s2）：標題若是 flex＋gap（.card h3 是 gap 10px），就用負的 margin 吃回來 */
  function fixGap(h, sp) {
    var cs = getComputedStyle(h), g = 0;
    if (/flex|grid/.test(cs.display)) { g = parseFloat(cs.columnGap) || 0; }
    var m = Math.round(6 - g);
    if (sp.style.marginRight !== m + 'px') sp.style.marginRight = m + 'px';
  }

  /* ★ 不擠篩選器：標題跟篩選器排在同一條「可換行的 flex 列」（.row.spread）時，
     圖示多出來的 1em＋6px 可能剛好讓篩選器被擠到第二行（_uitest 實測：800 寬「族群 × 法人」列 40 → 72px）。
     flex 換行是照「標題的最大內容寬」判斷的，所以這裡量「沒有圖示時標題多寬」，把標題的 max-width 釘在那個寬度：
     換不換行跟加圖示前一模一樣，多出來的那一點寬度改由標題自己內部吸收（副標本來就會在標題內換行）。
     只在「加了圖示真的讓那一列變高」時才動；列寬變了（換寬度、側欄開關）重量一次。 */
  function fit(h, sp) {
    var p = h.parentElement;
    if (!p || p.children.length < 2 || !h.getClientRects().length) return;
    var key = p.clientWidth + '|' + h.textContent.length;
    if (h._tiFit === key) return;
    var cs = getComputedStyle(p);
    if (cs.display.indexOf('flex') < 0 || cs.flexWrap === 'nowrap' || cs.flexDirection.indexOf('row') < 0) { h._tiFit = key; return; }
    if (h.getAttribute('data-ti-fit')) { h.style.maxWidth = ''; h.removeAttribute('data-ti-fit'); }
    sp.style.display = 'none';
    var h0 = p.getBoundingClientRect().height, w0 = h.getBoundingClientRect().width;
    sp.style.display = '';
    var h1 = p.getBoundingClientRect().height;
    if (h1 > h0 + 1) { h.style.maxWidth = Math.ceil(w0) + 'px'; h.setAttribute('data-ti-fit', '1'); }
    h._tiFit = p.clientWidth + '|' + h.textContent.length;
  }
  function fitAll() {
    var l = document.querySelectorAll('.ticon');
    for (var i = 0; i < l.length; i++) { var h = l[i].parentElement; if (h && !h.classList.contains('osc-ic')) fit(h, l[i]); }
  }

  /* 總覽摘要卡（.osc）左上那格：跟下方同名大卡用同一個圖示與語意色（輪盤＝radar、去向＝flow…），
     一眼就對得到「這張小卡是下面哪張大卡的摘要」。只換 svg 與 data-tone，不動那格的尺寸。 */
  var OSC = { updown: ['pulse', 'mix'], rot: ['radar', 'rot'], flow: ['flow', 'dest'], theme: ['flame', 'heat'] };
  function slot(el) {
    var c = el.closest('.osc'), m = c && OSC[c.getAttribute('data-k')];
    if (!m) return;
    if (el.getAttribute('data-tk') === m[0] && el.getAttribute('data-tone') === m[1]) return;
    el.setAttribute('data-tk', m[0]);
    el.setAttribute('data-tone', m[1]);
    el.innerHTML = svg(m[0], 14);
  }

  var pending = 0;
  function scan() {
    pending = 0;
    var list = document.querySelectorAll(AUTO);
    for (var i = 0; i < list.length; i++) decorate(list[i]);
    var sl = document.querySelectorAll('.osc-ic');
    for (var j = 0; j < sl.length; j++) slot(sl[j]);
    fitAll();
  }
  /* 標題列尺寸一變（換寬度、手機分段從隱藏變顯示、側欄開關）就重量一次 fit；只看列，不看整頁 */
  var ro = window.ResizeObserver ? new ResizeObserver(function () { schedule(); }) : null;
  var watched = window.WeakSet ? new WeakSet() : null;
  function watch(h) {
    var p = h.parentElement;
    if (!ro || !watched || !p || watched.has(p)) return;
    watched.add(p); ro.observe(p);
  }
  function schedule() { if (!pending) pending = requestAnimationFrame(scan); }

  /* ---- 樣式（色票＋動效）；跟著這支檔走，不必改 index.html 的大樣式段 ---- */
  var CSS = [
    /* 色：全部走主題變數（見上面 TONES 的註解）。「性格」變數只有 v4 三主題會改 */
    ':root{--ti-flow:var(--cyan);--ti-tech:var(--violet);--ti-fund:color-mix(in oklab,var(--cyan) 50%,var(--violet));',
    '--ti-warm:var(--amber);--ti-chip:var(--lime);--ti-sw:1.75;--ti-chip-a:0%;--ti-chip-r:50%;--ti-glow:0px}',
    ':root[data-theme4="casual"]{--ti-chip-a:14%;--ti-chip-r:50%}',
    ':root[data-theme4="hud"]{--ti-sw:1.6;--ti-glow:4px}',
    ':root[data-theme4="pro"]{--ti-sw:2.1;--ti-chip-r:3px}',
    /* 尺寸：1em＝跟著標題字級走（h3 16px → 16px；h4.subh 13～14px → 同大），夾在 14～20px。
       高度 1em ≤ 標題行高，所以不會把標題列撐高；寬度吃掉的是「1em＋與字距 6px」。 */
    '.ticon{position:relative;display:inline-flex;align-items:center;justify-content:center;flex:none;',
    'width:clamp(14px,1em,20px);height:clamp(14px,1em,20px);align-self:center;vertical-align:-.14em;',
    'color:var(--tc,var(--ti-flow));line-height:0;',
    'transition:color var(--dur-fast,120ms) var(--ease,ease),filter var(--dur-fast,120ms) var(--ease,ease)}',
    '.ticon>svg{position:relative;z-index:1;width:100%;height:100%;stroke-width:var(--ti-sw);overflow:visible}',
    /* 底下那顆淡色圓：平常看不到（休閒主題常駐 14%），滑過卡片時浮出來 —— absolute，不佔版面 */
    '.ticon::before{content:"";position:absolute;inset:-3px;border-radius:var(--ti-chip-r);',
    'background:color-mix(in srgb,var(--tc) var(--ti-chip-a),transparent);transition:background var(--dur-fast,120ms) var(--ease,ease);pointer-events:none}',
    ':root[data-theme4="hud"] .ticon{filter:drop-shadow(0 0 var(--ti-glow) color-mix(in srgb,var(--tc) 45%,transparent))}',
    '.ticon[data-tone="flow"],.ticon[data-tone="rot"],.ticon[data-tone="dest"]{--tc:var(--ti-flow)}',
    '.ticon[data-tone="tech"]{--tc:var(--ti-tech)}.ticon[data-tone="fund"]{--tc:var(--ti-fund)}',
    '.ticon:is([data-tone="heat"],[data-tone="val"],[data-tone="event"],[data-tone="yield"],[data-tone="watch"]){--tc:var(--ti-warm)}',
    '.ticon:is([data-tone="chip"],[data-tone="grow"]){--tc:var(--ti-chip)}',
    '.ticon[data-tone="up"],.ticon[data-tone="mix"]{--tc:var(--rise)}.ticon[data-tone="down"]{--tc:var(--fall)}',
    '.ticon[data-tone="mix"]>svg{stroke:url(#ti-mix)}',
    /* 摘要卡（總覽 K 線上方 .osc-ic）：那格原本是 app.js 的暫時圖示，由這支換成同一套圖與色，
       底色淡圓沿用它自己的 16%（它的 --ic 是 inline style，所以這裡要 !important 才蓋得過） */
    '.osc-ic[data-tone]{color:var(--tc)!important;background:color-mix(in srgb,var(--tc) 16%,transparent)!important}',
    '.osc-ic[data-tone="mix"] svg{stroke:url(#ti-mix)}',
    '.osc-ic[data-tone="flow"],.osc-ic[data-tone="rot"],.osc-ic[data-tone="dest"]{--tc:var(--ti-flow)}',
    '.osc-ic[data-tone="heat"]{--tc:var(--ti-warm)}.osc-ic[data-tone="mix"]{--tc:var(--rise)}',
    /* 互動（docs/ui_polish_spec.md §7.2：hover 只准改顏色，不准位移／放大）：
       滑過卡片 → 圖示提亮一階、底圓浮出；可填色的圖示再填一層淡色。120ms。 */
    '@media (hover:hover){',
    ':is(.card,.m3-card,.gpcard,aside):hover .ticon{color:color-mix(in srgb,var(--tc) 80%,var(--ink,#fff))}',
    ':is(.card,.m3-card,.gpcard,aside):hover .ticon::before{background:color-mix(in srgb,var(--tc) 18%,transparent)}',
    ':is(.card,.m3-card,.gpcard,aside):hover .ticon:is([data-k="heart"],[data-k="pie"],[data-k="star"],[data-k="coins"]) svg{fill:color-mix(in srgb,var(--tc) 22%,transparent)}',
    '}',
    /* 觸控：點卡片時底圓亮一下（.ti-tap 由 pointerdown 加，240ms 拿掉；不縮放 —— 標題不是按鈕，§7.3 的縮放只給整顆按鈕） */
    '.ticon.ti-tap::before{background:color-mix(in srgb,var(--tc) 26%,transparent)}',
    '@media (prefers-reduced-motion:reduce){.ticon,.ticon::before{transition:none}}'
  ].join('');

  function injectCss() {
    if (document.getElementById('ticon-css')) return;
    var st = document.createElement('style');
    st.id = 'ticon-css';
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /* 漲跌並陳用的漸層（上紅下綠）：全站共用一份。不可用 display:none（Firefox 會讓漸層失效），改成 0×0 */
  function injectDefs() {
    if (document.getElementById('ti-defs')) return;
    var d = document.createElement('div');
    d.id = 'ti-defs';
    d.setAttribute('aria-hidden', 'true');
    d.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none';
    d.innerHTML = '<svg width="0" height="0" focusable="false"><defs><linearGradient id="ti-mix" gradientUnits="userSpaceOnUse" x1="12" y1="3" x2="12" y2="21">' +
      '<stop offset="0" style="stop-color:var(--rise)"/><stop offset=".45" style="stop-color:var(--rise)"/>' +
      '<stop offset=".55" style="stop-color:var(--fall)"/><stop offset="1" style="stop-color:var(--fall)"/></linearGradient></defs></svg>';
    document.body.appendChild(d);
  }

  /* 手機（觸控）點卡片的回饋 */
  function onTap(e) {
    if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
    var card = e.target.closest && e.target.closest('.card, .m3-card, .gpcard, .mhead, .side-h');
    if (!card) return;
    var ic = card.querySelector('.ticon');
    if (!ic) return;
    ic.classList.add('ti-tap');
    clearTimeout(ic._tiT);
    ic._tiT = setTimeout(function () { ic.classList.remove('ti-tap'); }, 240);
  }

  var rsT = 0;
  function start() {
    injectCss();
    injectDefs();
    scan();
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true, characterData: true });
    document.addEventListener('pointerdown', onTap, { passive: true, capture: true });
    // 版面斷點會改標題的 display／gap（手機版），換寬度後重算一次距離
    window.addEventListener('resize', function () {
      clearTimeout(rsT);
      rsT = setTimeout(function () {
        var l = document.querySelectorAll('.ticon');
        for (var i = 0; i < l.length; i++) if (l[i].parentElement) fixGap(l[i].parentElement, l[i]);
      }, 150);
    });
  }

  window.TwIcons = { svg: svg, scan: scan, resolve: resolve, ICONS: ICONS, ALIAS: ALIAS, TONES: TONES,
    ICON_TONE: ICON_TONE, RULES: RULES, CARD_ID: CARD_ID, LUCIDE_NAME: LUCIDE_NAME };
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();
