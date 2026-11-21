const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const CHECK=fs.readFileSync(__dirname+'/check_a.js.txt','utf8');
(async()=>{const b=await chromium.launch();const jobs=JSON.parse(fs.readFileSync(__dirname+'/html_samples/jobs.json'));let tot=0,bad=0;
for(const j of jobs){const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+j.html);await pg.waitForTimeout(250);
await pg.screenshot({path:j.out});const r=await pg.evaluate(eval(CHECK));tot++;
const cl=await pg.evaluate(()=>[...document.querySelectorAll('[data-o]')].filter(e=>(e.scrollHeight>e.clientHeight+1||e.scrollWidth>e.clientWidth+1)&&e.dataset.o!=='hook').map(e=>e.dataset.o));if(cl.length){r.oob=r.oob.concat(cl.map(x=>'裁切:'+x))}
const ovl=r.overlap.length+r.gap24.length+r.oob.length;if(ovl)bad++;
console.log(j.post.slice(0,5),j.out.split('/').pop(),'n='+r.n,ovl?JSON.stringify({o:r.overlap,g:r.gap24,oob:r.oob}):'OK','disc'+r.discFont);await pg.close()}
console.log('張數',tot,'有問題',bad);await b.close()})()
