const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const CHECK=fs.readFileSync(__dirname+'/../../layouts/check.js.txt','utf8');
(async()=>{const b=await chromium.launch();let n=0,bad=0,lines=[];
for(const p of ['post1','post2','post3']){const d=__dirname+'/'+p;const mf=JSON.parse(fs.readFileSync(d+'/manifest.json'));const out={};
for(const [name,H] of Object.entries(mf)){const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+d+'/html/'+name+'.html');await pg.waitForTimeout(300);
await pg.screenshot({path:d+'/'+name+'.png'});const r=await pg.evaluate(eval(CHECK),{});
r.bodyScrollH=await pg.evaluate(()=>document.documentElement.scrollHeight);out[name]=r;await pg.close();
n++;bad+=r.overlap.length;if(r.overlap.length||r.oob_margin.length||r.gap32.length||r.minFont<28)lines.push(p+' '+name+' '+JSON.stringify(r))}
fs.writeFileSync(d+'/overlap_report.json',JSON.stringify(out,null,1))}
await b.close();console.log('張數',n,'重疊筆數',bad);lines.forEach(l=>console.log(l))})()
