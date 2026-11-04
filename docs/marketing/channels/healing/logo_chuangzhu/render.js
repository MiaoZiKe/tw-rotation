const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const J=JSON.parse(fs.readFileSync('jobs.json','utf8')).jobs;const b=await chromium.launch();const pg=await b.newPage();
for(const j of J){await pg.setViewportSize({width:j.w,height:j.h});
await pg.setContent(`<style>body{margin:0;background:transparent}svg{display:block}</style>${fs.readFileSync(j.svg,'utf8')}`);
await pg.screenshot({path:j.png,omitBackground:!!j.transparent});}
await b.close();console.log('ok',J.length)})();
