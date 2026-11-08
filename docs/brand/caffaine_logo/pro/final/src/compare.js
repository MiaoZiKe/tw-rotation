// final_compare.png：P3（主推）／P7／P5 三欄並排；P3 欄底下附等寬 AI 比較版
const { chromium } = require('playwright');
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');const D=Object.fromEntries(JSON.parse(fs.readFileSync(path.join(__dirname,'dirs.json'))).map(d=>[d.id,d]));
const col=(id,extra='')=>{const d=D[id],p=f=>`../${d.dir}/${f}`;return `<div class="col"><div class="hd"><b>${d.name}</b><span>${d.sub}</span></div>
<div class="ratio">咖啡感 ${d.ratio[0]}%／科技感 ${d.ratio[1]}%</div><p class="mean">${d.meaning}</p>
<div class="row"><img class="ic" src="${p('icon_light_1024.png')}"><img class="ic" src="${p('icon_dark_1024.png')}"></div>
<div class="row av"><img src="${p('avatar_110_light.png')}" width="110"><img src="${p('avatar_110_dark.png')}" width="110"><img src="${p('avatar_40_light.png')}" width="40"><img src="${p('avatar_40_dark.png')}" width="40"><span>110／40px 實寸</span></div>
<img class="lk" src="${p('lockup_light.png')}"><img class="lk" src="${p('lockup_dark.png')}">${extra}
<img class="ig" src="${p('app_ig_profile.png')}"><div class="row"><img class="cup" src="${p('app_cup.png')}"><img class="cv" src="${p('app_post_cover.png')}"></div></div>`};
const b=D.F1b,pb=f=>`../${b.dir}/${f}`;
const extra=`<div class="cmp">比較版：AI 用等寬字（JetBrains Mono）</div><img class="lk" src="${pb('lockup_light.png')}"><img class="lk" src="${pb('lockup_dark.png')}">`;
const html=`<!doctype html><meta charset="utf-8"><style>
body{margin:0;background:#EFE6DA;color:#2B1D16;padding:48px;width:2904px;font-family:Inter,'WenQuanYi Zen Hei'}
h1{font:600 46px Inter,'WenQuanYi Zen Hei';margin:0 0 6px}.sub{font:24px 'WenQuanYi Zen Hei';opacity:.75;margin:0 0 30px}
.wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:32px}.col{background:#FFFBF5;border-radius:28px;padding:30px;display:flex;flex-direction:column;gap:16px}
.hd b{font:700 40px Inter,'WenQuanYi Zen Hei';margin-right:14px}.hd span{font:22px 'WenQuanYi Zen Hei';opacity:.7}
.ratio{font:21px 'WenQuanYi Zen Hei';background:#F1E3D1;padding:6px 14px;border-radius:20px;align-self:flex-start}
.mean{font:21px/1.55 'WenQuanYi Zen Hei';margin:0;opacity:.85;min-height:66px}
.row{display:flex;gap:16px;align-items:center}.ic{width:404px;height:404px;border-radius:20px}.av span{font:17px 'WenQuanYi Zen Hei';opacity:.6}
.lk{width:100%;border-radius:14px}.ig{width:100%;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.08)}.cup,.cv{width:404px;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.08)}
.cmp{font:22px 'WenQuanYi Zen Hei';opacity:.7;margin-top:6px}.col:first-child{outline:4px solid #C2652B}
</style><h1>CaffAIne 定稿候選（精修）：P3 對話杯（主推）｜P7 豆中靈光｜P5 像素蒸氣</h1><p class="sub">每欄：圖形淺／深底、大頭貼 110／40px 實寸、橫式深淺底、IG 個人頁、外帶杯、1080×1350 貼文封面</p>
<div class="wrap">${col('F1',extra)}${col('F2')}${col('F3')}</div>`;
(async()=>{const f=path.join(__dirname,'_cmp.html');fs.writeFileSync(f,html);const br=await chromium.launch();const pg=await br.newPage({viewport:{width:3000,height:1000}});
 await pg.goto('file://'+f);await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(300);await pg.screenshot({path:path.join(ROOT,'final_compare.png'),fullPage:true});await br.close();fs.unlinkSync(f);console.log('ok');})();
