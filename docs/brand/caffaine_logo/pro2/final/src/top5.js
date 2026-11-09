// final_top5.png：兩批合併前 5 名並排（P3、Q2、P7 用精修版）
const { chromium } = require('playwright');const fs=require('fs'),path=require('path');
const B=path.resolve(__dirname,'..','..','..');
const J=f=>Object.fromEntries(JSON.parse(fs.readFileSync(f)).map(d=>[d.id,d]));
const A=J(path.join(B,'pro/final/src/dirs.json')),Q=J(path.join(__dirname,'dirs.json'));
const L=[['1','P3 對話杯',`pro/final/${A.F1.dir}`,A.F1.meaning],['2','Q2 一筆拉花',`pro2/final/${Q.Q2.dir}`,Q.Q2.meaning],['3','P7 豆中靈光',`pro/final/${A.F2.dir}`,A.F2.meaning],['4','Q4 等角方糖',`pro2/final/${Q.Q4.dir}`,Q.Q4.meaning],['5','Q7 復古未來徽章',`pro2/final/${Q.Q7.dir}`,Q.Q7.meaning]];
const col=([n,name,dir,m])=>{const p=f=>'file://'+path.join(B,dir,f);return `<div class="col"><div class="hd"><span class="n">${n}</span><b>${name}</b></div>
<div class="av"><img src="${p('avatar_110_light.png')}" width="110"><img src="${p('avatar_110_dark.png')}" width="110"><img src="${p('avatar_40_light.png')}" width="40"><img src="${p('avatar_40_dark.png')}" width="40"></div>
<img class="lk" src="${p('lockup_light.png')}"><img class="lk" src="${p('lockup_dark.png')}"><p>${m}</p></div>`};
const html=`<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#EFE6DA;color:#2B1D16;padding:44px;width:3112px;font-family:Inter,'WenQuanYi Zen Hei'}
h1{font:600 44px Inter,'WenQuanYi Zen Hei';margin:0 0 6px}.s{font:22px 'WenQuanYi Zen Hei';opacity:.7;margin:0 0 28px}
.g{display:grid;grid-template-columns:repeat(5,1fr);gap:24px}.col{background:#FFFBF5;border-radius:24px;padding:24px;display:flex;flex-direction:column;gap:14px}
.hd{display:flex;align-items:center;gap:12px}.hd b{font:700 32px Inter,'WenQuanYi Zen Hei'}.n{background:#C2652B;color:#fff;font:700 24px Inter;width:42px;height:42px;border-radius:21px;display:flex;align-items:center;justify-content:center}
.av{display:flex;gap:12px;align-items:center}.lk{width:100%;border-radius:12px}p{font:21px/1.6 'WenQuanYi Zen Hei';margin:4px 0 0;opacity:.88}.col:first-child{outline:4px solid #C2652B}</style>
<h1>CaffAIne 兩批合併前 5 名</h1><p class="s">每欄：大頭貼 110／40px（淺、深）、淺底橫式、深底橫式、一句含義；P3、P7 為第一批精修版，Q2、Q4、Q7 為第二批精修版</p><div class="g">${L.map(col).join('')}</div>`;
(async()=>{const f=path.join(__dirname,'_t5.html');fs.writeFileSync(f,html);const br=await chromium.launch();const pg=await br.newPage({viewport:{width:3200,height:900}});
 await pg.goto('file://'+f);await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(300);await pg.screenshot({path:path.join(B,'pro2/final/final_top5.png'),fullPage:true});await br.close();fs.unlinkSync(f);console.log('ok');})();
