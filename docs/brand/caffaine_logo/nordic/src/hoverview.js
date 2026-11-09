const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const { dirs } = require('./hanko_marks');
const OUT = path.resolve(__dirname, '..', 'hanko'), ORIG = path.resolve(__dirname, '..', 'n3_像素印章');
const b64 = f => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64');
const card = (title, sub, p, desc, diff, orig) => `<div class="card${orig ? ' orig' : ''}"><div class="hd">${title}<span>${sub}</span></div>
  <div class="row"><img class="mk" src="${p('mark_light.png')}"><img class="mk" src="${p('mark_dark.png')}">
  <div class="av"><div><img src="${p('avatar_110.png')}" width="110">${orig ? '' : `<img src="${p('avatar_110_dark.png')}" width="110">`}</div><div><img src="${p('avatar_40.png')}" width="40">${orig ? '' : `<img src="${p('avatar_40_dark.png')}" width="40">`}</div></div>
  <img class="cv" src="${p('mock_takeaway_cup.png')}"></div><img class="hz" src="${p('horizontal_light.png')}"><p>${desc}</p>${diff ? `<p class="df">和原版差在哪：${diff}</p>` : ''}</div>`;
(async () => {
  const head = card('<b>原版</b> 03 像素印章', '對照用', f => path.join(ORIG, f), '原版：朱紅圓角方印，陰刻 12 格像素的「AI」與咖啡杯。美術總監指出它和 Adobe 系圖示太像（圓角方塊＋實心亮紅＋白字）。', '', true)
    .replace(/src="([^"]+\.png)"/g, (m, f) => `src="${b64(f)}"`);
  const cards = dirs.map((d, i) => card(`<b>${String(i + 1).padStart(2, '0')}</b> ${d.name}`, d.style, f => path.join(OUT, d.id, f), d.desc, d.diff).replace(/src="([^"]+\.png)"/g, (m, f) => `src="${b64(f)}"`)).join('');
  const html = `<html><head><style>body{margin:0;background:#EDE6DB;font-family:'WenQuanYi Zen Hei';color:#2E2420;padding:40px;width:1920px}
  h1{font:700 42px 'WenQuanYi Zen Hei';margin:0}.g{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:22px}
  .card{background:#FBF7F1;border-radius:20px;padding:24px}.orig{grid-column:1/3;display:grid;grid-template-columns:auto 1fr;column-gap:30px;outline:3px dashed #B9A68E}
  .orig .hd{grid-column:1/3}.orig .hz{margin-top:0;width:820px}.orig p{grid-column:1/3}
  .hd{font-size:27px;margin-bottom:14px}.hd b{color:#A9473A;margin-right:6px}.hd span{float:right;font-size:20px;opacity:.65;margin-top:6px}
  .row{display:flex;gap:16px;align-items:center}.mk,.cv{width:190px;height:190px;border-radius:12px}
  .av{display:flex;flex-direction:column;gap:12px;width:240px}.av div{display:flex;gap:12px;align-items:center}
  .hz{width:100%;margin-top:16px;border-radius:12px}p{font-size:20px;line-height:1.55;margin:12px 2px 0}.df{color:#7A5A44}</style></head>
  <body><h1><span style="font-family:'Bitstream Charter'">CaffAIne</span> 像素印章 10 變體（第一列為原版對照）</h1><div class="g">${head}${cards}</div></body></html>`;
  fs.writeFileSync(path.join(__dirname, 'hanko_overview.html'), html);
  const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 2000, height: 1000 } });
  await pg.goto('file://' + path.join(__dirname, 'hanko_overview.html')); await pg.screenshot({ path: path.join(OUT, 'overview.png'), fullPage: true }); await br.close();
})();
