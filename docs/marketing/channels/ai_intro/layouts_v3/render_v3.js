// 產生 A~F 各 4 張並做版面檢查。node render_v3.js [字母...]
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const {STY,NAMES}=require('./gen_v3.js');
const src=fs.readFileSync('../layouts_v2/scifi/render_scifi.js','utf8');
const CHECK=eval('`'+src.match(/const CHECK=`([\s\S]*?)`;\n\(async/)[1]+'`');
(async()=>{const b=await chromium.launch();const res={};const want=process.argv.slice(2);
for(const k of Object.keys(STY)){if(want.length&&!want.includes(k))continue;const {css,pages,base}=STY[k];
 for(let i=0;i<4;i++){const f=`html/${k}_${i+1}.html`;
  fs.writeFileSync(f,`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${css}</style><body>${pages[i]}</body></html>`);
  const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+process.cwd()+'/'+f);await pg.waitForTimeout(300);
  await pg.screenshot({path:`png/${k}_${i+1}.png`});
  const r=await pg.evaluate(eval(CHECK),[base,'']);res[`${k}_${i+1}`]=r;await pg.close()}}
await b.close();fs.writeFileSync('check_result.json',JSON.stringify(res,null,1));
for(const k in res){const r=res[k];const bad=[...r.overlap.map(x=>'重疊'+x),...r.gap24.map(x=>'間距'+x),...r.oob.map(x=>'越界'+x),...r.clip.map(x=>'溢出'+x),...r.side,...r.decoOnText.map(x=>'穿字'+x),...r.decoOnDeco.map(x=>'疊裝飾'+x),...r.small.map(x=>'小字'+x)];
 console.log(k,bad.length?bad.join(' | '):'OK','對比',r.minContrast,r.lowContrast.join(','),'揭露',r.minDisc)}})()
