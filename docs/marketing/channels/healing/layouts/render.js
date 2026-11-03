const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const CHECK=fs.readFileSync('check.js.txt','utf8');const out={};
const list=[['A_quote',1350],['A_inner',1350],['B_post',1350],['B_reels',1920],['C_list',1350]];
for(const [n,H] of list){const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+process.cwd()+'/html/'+n+'.html');await pg.waitForTimeout(300);
await pg.screenshot({path:n+'.png'});const opts=n=='B_reels'?{safe:[250,1580]}:{};out[n]=await pg.evaluate(eval(CHECK),opts);await pg.close()}
await b.close();fs.writeFileSync('overlap_report.json',JSON.stringify(out,null,1));console.log(JSON.stringify(out,null,1))})()
