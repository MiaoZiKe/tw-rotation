const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const out={};
for(const f of fs.readdirSync('.').filter(x=>x.startsWith('_')&&x.endsWith('.html'))){const n=f.slice(1,-5);
const pg=await b.newPage({viewport:{width:512,height:512}});await pg.goto('file://'+process.cwd()+'/'+f);await pg.waitForTimeout(200);
await pg.screenshot({path:n+'.png'});
// 圓形頭像：只有圓內 80% 為安全區；檢查文字與圖形外框四角是否落在半徑 230 圓內
out[n]=await pg.evaluate(()=>[...document.querySelectorAll('svg > g, svg > path, svg > text')].map(e=>{const r=e.getBBox();const pts=[[r.x,r.y],[r.x+r.width,r.y],[r.x,r.y+r.height],[r.x+r.width,r.y+r.height]];return {tag:e.tagName,maxR:Math.round(Math.max(...pts.map(([x,y])=>Math.hypot(x-256,y-256))))}}));
await pg.evaluate(()=>{document.getElementById('s').className='c'});await pg.screenshot({path:n+'_圓形預覽.png',omitBackground:true});await pg.close()}
await b.close();fs.writeFileSync('overlap_report.json',JSON.stringify(out,null,1));console.log(JSON.stringify(out))})()
