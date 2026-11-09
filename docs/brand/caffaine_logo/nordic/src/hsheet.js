const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { dirs } = require('./hanko_marks');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2000, height: 600 } });
  const cell = (d, v, s, sm) => `<div style="background:${d[v].bg};padding:8px;display:inline-block"><svg width="${s}" height="${s}" viewBox="0 0 200 200">${sm ? d.markSmall(d[v]) : d.mark(d[v])}</svg></div>`;
  await p.setContent(`<body style="margin:0">${dirs.map(d => cell(d, 'light', 180)).join('')}<br>${dirs.map(d => cell(d, 'dark', 180)).join('')}<br>${dirs.map(d => cell(d, 'light', 40, 1) + cell(d, 'dark', 40, 1)).join('')}</body>`);
  await p.screenshot({ path: process.argv[2], fullPage: true }); await b.close(); })();
