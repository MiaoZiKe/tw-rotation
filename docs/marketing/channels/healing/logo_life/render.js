const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const J=JSON.parse(fs.readFileSync('jobs.json','utf8')).jobs;const b=await chromium.launch();const out={};
for(const j of J){const pg=await b.newPage({viewport:{width:j.w,height:j.h}});
await pg.setContent(`<style>body{margin:0;background:transparent}</style>${fs.readFileSync(j.svg,'utf8')}`);await pg.waitForTimeout(150);
out[j.svg]=await pg.evaluate(ids=>{const o={};for(const i of ids){const e=document.getElementById(i);if(e){const x=e.getBoundingClientRect();o[i]=[x.left,x.top,x.right,x.bottom]}}return o},j.ids||[]);
await pg.screenshot({path:j.png,omitBackground:!!j.transparent});await pg.close();}
fs.writeFileSync('boxes.json',JSON.stringify(out));await b.close();console.log('ok',J.length)})();
