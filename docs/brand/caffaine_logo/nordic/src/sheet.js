const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { dirs } = require('./marks');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 800 } });
  const cell = (d, v) => `<div style="background:${d[v].bg};padding:10px;display:inline-block"><svg width="180" height="180" viewBox="0 0 200 200">${d.mark(d[v])}</svg></div>`;
  await p.setContent(`<body style="margin:0">${dirs.map(d => cell(d, 'light')).join('')}<br>${dirs.map(d => cell(d, 'dark')).join('')}<br>${dirs.map(d => `<div style="background:${d.light.bg};display:inline-block;padding:4px;margin:4px"><svg width="40" height="40" viewBox="0 0 200 200">${d.mark(d.light)}</svg></div>`).join('')}</body>`);
  await p.screenshot({ path: process.argv[2], fullPage: true }); await b.close();
})();
