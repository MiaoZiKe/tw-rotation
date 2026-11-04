const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const d=__dirname+'/post1';const h=fs.readFileSync(d+'/html/threads.html','utf8');
for(const p of 'NFM'){const f=d+'/html/_cmp_'+p+'.html';fs.writeFileSync(f,h.replace('data-palette="N"','data-palette="'+p+'"'));
const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+f);await pg.waitForTimeout(300);await pg.screenshot({path:d+'/_cmp_'+p+'.png'});await pg.close();fs.unlinkSync(f)}
await b.close()})()
