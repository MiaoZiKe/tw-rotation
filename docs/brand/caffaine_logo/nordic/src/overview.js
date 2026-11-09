const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const { dirs } = require('./marks');
const OUT = path.resolve(__dirname, '..');
const b64 = f => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64');
(async () => {
  const cards = dirs.map((d, i) => { const p = f => b64(path.join(OUT, d.id, f));
    return `<div class="card"><div class="hd"><b>${String(i + 1).padStart(2, '0')}</b> ${d.name}<span>${d.style}｜${d.ratio}</span></div>
    <div class="row"><img class="mk" src="${p('mark_light.png')}"><img class="mk" src="${p('mark_dark.png')}">
    <div class="av"><img src="${p('avatar_110.png')}" width="110"><img src="${p('avatar_40.png')}" width="40"></div>
    <img class="cv" src="${p('mock_takeaway_cup.png')}"></div>
    <img class="hz" src="${p('horizontal_light.png')}"><p>${d.meaning}</p></div>`; }).join('');
  const html = `<html><head><style>body{margin:0;background:#EDE6DB;font-family:'WenQuanYi Zen Hei';color:#2E2420;padding:40px;width:1920px}
  h1{font:700 44px 'Bitstream Charter';margin:0 0 6px}h1 small{font:400 24px 'WenQuanYi Zen Hei';margin-left:16px;opacity:.7}
  .g{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:24px}.card{background:#FBF7F1;border-radius:22px;padding:26px}
  .hd{font-size:28px;margin-bottom:16px}.hd b{font-family:Inter;color:#C8643B;margin-right:6px}.hd span{float:right;font-size:20px;opacity:.65;margin-top:6px}
  .row{display:flex;gap:18px;align-items:center}.mk{width:200px;height:200px;border-radius:14px}.cv{width:200px;height:200px;border-radius:14px}
  .av{display:flex;flex-direction:column;align-items:center;gap:18px;width:120px}.hz{width:100%;margin-top:18px;border-radius:12px}p{font-size:21px;line-height:1.55;margin:14px 2px 0;opacity:.85}</style></head>
  <body><h1>CaffAIne LOGO ｜ 日系・北歐・溫暖線畫 8 方向<small>一杯咖啡的時間，看懂一個 AI 新知</small></h1><div class="g">${cards}</div></body></html>`;
  fs.writeFileSync(path.join(__dirname, 'overview.html'), html);
  const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 2000, height: 1000 } });
  await pg.goto('file://' + path.join(__dirname, 'overview.html')); await pg.screenshot({ path: path.join(OUT, 'overview.png'), fullPage: true }); await br.close();
})();
