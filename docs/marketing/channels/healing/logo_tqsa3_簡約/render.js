const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const J=JSON.parse(fs.readFileSync('jobs.json','utf8')).jobs;const b=await chromium.launch();const pg=await b.newPage();
for(const j of J){await pg.setViewportSize({width:j.w,height:j.h});
await pg.setContent(`<style>html,body{margin:0;background:transparent}</style>${fs.readFileSync(j.svg,'utf8')}`);
await pg.evaluate(()=>document.fonts.ready);
if(j.show){await pg.evaluate(s=>{document.querySelectorAll('[data-layer]').forEach(e=>{if(!s.includes(e.dataset.layer))e.style.display='none'})},j.show)}
await pg.waitForTimeout(40);await pg.screenshot({path:j.png,omitBackground:!!j.transparent});}
await b.close();console.log('ok',J.length)})();
