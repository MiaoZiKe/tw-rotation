const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const B = path.resolve(__dirname, '..'), b64 = f => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64');
const cols = [
  ['原版 03 像素印章（對照）', path.join(B, 'n3_像素印章'), '朱紅圓角實心方印＋白字，有 Adobe 撞臉風險'],
  ['主款｜07 八位元衝框', path.join(B, 'hanko/final/f07_八位元衝框_主款'), '文字標 A 頂端削角、A 與 I 多空一格；框缺口放大一格；40px 版蒸氣只留一道、階梯角放大、框線加粗'],
  ['備案｜05 歪印雙色', path.join(B, 'hanko/final/f05_歪印雙色_備案'), '大頭貼改不歪的正印、框線加粗、墨色實心、AI 放大；歪斜只留在橫式與貼文；框線 9→10'],
  ['第三｜01 落款長印', path.join(B, 'hanko/final/f01_落款長印_第三'), '印面加寬約 15%、A／I／杯都放大；40px 版拿掉暈染毛邊'],
];
(async () => {
  const col = ([t, d, note], i) => { const p = f => fs.existsSync(path.join(d, f)) ? b64(path.join(d, f)) : '';
    const img = (f, w, cls = '') => p(f) ? `<img class="${cls}" src="${p(f)}" width="${w}">` : `<span style="display:inline-block;width:${w}px"></span>`;
    return `<div class="c${i ? '' : ' o'}"><h2>${t}</h2><div class="r">${img('mark_light.png', 250, 'm')}${img('mark_dark.png', 250, 'm')}</div>
    <div class="r av">${img('avatar_110.png', 110)}${img('avatar_110_dark.png', 110)}${img('avatar_40.png', 40)}${img('avatar_40_dark.png', 40)}</div>
    ${img('horizontal_light.png', 520, 'h')}${img('horizontal_dark.png', 520, 'h')}${img('mock_takeaway_cup.png', 520, 'h')}<p>${note}</p></div>`; };
  const html = `<html><head><style>body{margin:0;background:#EDE6DB;padding:36px;width:2260px;font-family:'WenQuanYi Zen Hei';color:#2E2420}
  h1{font-size:40px;margin:0 0 20px}.g{display:grid;grid-template-columns:repeat(4,540px);gap:24px}.c{background:#FBF7F1;border-radius:18px;padding:10px}
  .o{outline:3px dashed #B9A68E;opacity:.92}h2{font-size:26px;margin:6px 6px 12px}.r{display:flex;gap:10px;margin-bottom:10px;align-items:center}.av{gap:16px;padding:6px;background:#D9CFC2;border-radius:10px}
  .m{border-radius:10px}.h{display:block;border-radius:10px;margin-bottom:10px}p{font-size:19px;line-height:1.55;margin:6px}</style></head>
  <body><h1><span style="font-family:'Bitstream Charter'">CaffAIne</span> 像素印章精修：原版對照＋三款</h1><div class="g">${cols.map(col).join('')}</div></body></html>`;
  const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 2340, height: 1000 } });
  await pg.setContent(html); await pg.screenshot({ path: path.join(B, 'hanko/final/hanko_final_compare.png'), fullPage: true }); await br.close();
})();
