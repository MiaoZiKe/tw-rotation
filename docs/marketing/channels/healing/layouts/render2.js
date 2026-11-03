const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const CHECK=fs.readFileSync('check.js.txt','utf8');const all={};
for(const p of ['post1','post2','post3']){const d=process.cwd()+'/../samples/20261104/'+p;const mf=JSON.parse(fs.readFileSync(d+'/manifest.json'));const out={};
for(const [n,H] of Object.entries(mf)){const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+d+'/html/'+n+'.html');await pg.waitForTimeout(300);
await pg.screenshot({path:d+'/'+n+'.png'});out[n]=await pg.evaluate(eval(CHECK),{});await pg.close()}
fs.writeFileSync(d+'/overlap_report.json',JSON.stringify(out,null,1));all[p]=out}
await b.close();let n=0,bad=0;for(const p in all)for(const k in all[p]){n++;if(all[p][k].overlap.length)bad+=all[p][k].overlap.length}console.log('張數',n,'重疊筆數',bad);
for(const p in all)for(const k in all[p]){const r=all[p][k];if(r.overlap.length||r.oob_margin.length||r.gap32.length||r.minFont<28)console.log(p,k,JSON.stringify(r))}})()
