const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const CHECK=fs.readFileSync('check_a.js.txt','utf8');const out={};
for(const n of ['A_cover','A_reels','A_shot','A_table','A_end']){const H=n=='A_reels'?1920:1350;
for(let k=0;k<4;k++){const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+process.cwd()+'/html/'+n+'.html');await pg.waitForTimeout(200);
try{await pg.screenshot({path:n+'.png'});out[n]=await pg.evaluate(eval(CHECK));await pg.close();break}catch(e){await pg.close()}}}
await b.close();console.log(JSON.stringify(out,null,1))})()
