const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const J=JSON.parse(fs.readFileSync('jobs.json','utf8')).jobs;const b=await chromium.launch();const out={};
for(const j of J){const pg=await b.newPage({viewport:{width:j.w,height:j.h}});
await pg.setContent(`<style>body{margin:0;background:transparent}</style>${fs.readFileSync(j.svg,'utf8')}`);await pg.waitForTimeout(120);
out[j.svg]=await pg.evaluate(()=>{const r=e=>{if(!e)return null;const x=e.getBoundingClientRect();return [x.left,x.top,x.right,x.bottom]};
return {sym:r(document.getElementById('sym')),nm:r(document.getElementById('nm'))}});
await pg.screenshot({path:j.png,omitBackground:!!j.transparent});await pg.close();}
fs.writeFileSync('boxes.json',JSON.stringify(out));await b.close();console.log('ok',J.length)})();
