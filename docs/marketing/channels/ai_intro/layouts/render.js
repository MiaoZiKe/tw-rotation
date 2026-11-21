const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const CHECK=fs.readFileSync('check.js.txt','utf8');const out={};
for(const f of fs.readdirSync('html')){const n=f.replace('.html','');const H=n.endsWith('reels')?1920:1350;
const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+process.cwd()+'/html/'+f);await pg.waitForTimeout(200);
try{await pg.screenshot({path:n+'.png'})}catch(e){console.error('FAIL',n);await pg.close();continue}out[n]=await pg.evaluate(eval(CHECK));await pg.close()}
await b.close();console.log(JSON.stringify(out))})()
