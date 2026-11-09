// 總覽圖：8 方向並排（圖形深淺、大頭貼 110／40、橫式、三個應用情境）
const { chromium } = require('playwright');
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');const DIRS=JSON.parse(fs.readFileSync(path.join(__dirname,'dirs.json')));
const only=(process.argv[2]||'').split(',').filter(Boolean);const OUT=process.argv[3]||path.join(ROOT,'overview.png');
const list=DIRS.filter(d=>!only.length||only.includes(d.id));
const card=D=>{const p=f=>`../${D.dir}/${f}`;return `<div class="card"><div class="hd"><b>${D.id}　${D.name}</b><span class="en">${D.en}</span><span class="ratio">咖啡感 ${D.ratio[0]}%／科技感 ${D.ratio[1]}%</span></div>
<p class="mean">${D.meaning}</p>
<div class="row"><img class="ic" src="${p('icon_light_1024.png')}"><img class="ic" src="${p('icon_dark_1024.png')}">
<div class="avs"><div><img src="${p('avatar_110_light.png')}" width="110"><img src="${p('avatar_110_dark.png')}" width="110"></div><div><img src="${p('avatar_40_light.png')}" width="40"><img src="${p('avatar_40_dark.png')}" width="40"><span>110／40px</span></div></div>
<div class="lks"><img src="${p('lockup_light.png')}"><img src="${p('lockup_dark.png')}"></div></div>
<div class="row apps"><img class="ig" src="${p('app_ig_profile.png')}"><img class="cup" src="${p('app_cup.png')}"><img class="cv" src="${p('app_post_cover.png')}"></div>${D.id==='Q6'?`<div class="row apps"><img style="width:900px" src="${p('storyboard_light.png')}"></div>`:''}</div>`};
const html=`<!doctype html><meta charset="utf-8"><style>
body{margin:0;background:#EFE6DA;font-family:'Inter','WenQuanYi Zen Hei';color:#2B1D16;padding:48px;width:${list.length>1?3300:1640}px}
h1{font:600 46px 'Inter','WenQuanYi Zen Hei';margin:0 0 8px}.sub{font:24px 'WenQuanYi Zen Hei';margin:0 0 36px;opacity:.75}
.grid{display:grid;grid-template-columns:${list.length>1?'1fr 1fr':'1fr'};gap:36px}
.card{background:#FFFBF5;border-radius:28px;padding:30px 34px}
.hd{display:flex;gap:18px;align-items:baseline}.hd b{font:700 34px 'Inter','WenQuanYi Zen Hei'}.en{font:500 22px Inter;opacity:.6}.ratio{margin-left:auto;font:22px 'WenQuanYi Zen Hei';background:#F1E3D1;padding:6px 14px;border-radius:20px}
.mean{font:21px/1.55 'WenQuanYi Zen Hei';margin:10px 0 18px;opacity:.85}
.row{display:flex;gap:18px;align-items:center}.ic{width:190px;height:190px;border-radius:18px}
.avs{display:flex;flex-direction:column;gap:10px}.avs div{display:flex;gap:10px;align-items:center}.avs span{font:16px 'WenQuanYi Zen Hei';opacity:.6}
.lks{display:flex;flex-direction:column;gap:10px}.lks img{height:116px;border-radius:12px}
.apps{margin-top:18px;align-items:flex-start}.apps img{border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.08)}.ig{width:560px}.cup{width:316px}.cv{width:316px}
</style><h1>CaffAIne LOGO 專業版第三批：8 個新方向</h1><p class="sub">每張卡：圖形淺／深底、圓形大頭貼 110／40px、橫式完整版、應用情境（IG 個人頁、外帶杯、1080×1350 貼文封面）</p><div class="grid">${list.map(card).join('')}</div>`;
(async()=>{const f=path.join(__dirname,'_overview.html');fs.writeFileSync(f,html);const br=await chromium.launch();const pg=await br.newPage({viewport:{width:list.length>1?3396:1736,height:1000}});
 await pg.goto('file://'+f);await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(300);await pg.screenshot({path:OUT,fullPage:true});await br.close();fs.unlinkSync(f);console.log(OUT);})();
