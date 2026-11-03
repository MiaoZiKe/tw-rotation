const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const out={};const names=fs.readdirSync('.').filter(x=>x.endsWith('.svg')).map(x=>x.slice(0,-4));
for(const n of names){const svg=fs.readFileSync(n+'.svg','utf8');const pg=await b.newPage({viewport:{width:512,height:512}});
await pg.setContent(`<style>body{margin:0}.c{border-radius:50%;overflow:hidden;width:512px;height:512px}</style><div id=s>${svg}</div>`);await pg.waitForTimeout(200);
await pg.screenshot({path:n+'.png'});
// 安全區：IG 圓形頭像內容須在中央直徑 80%（512 底圖半徑 204.8）圓內；另查符號與字標外框是否相交
out[n]=await pg.evaluate(()=>{const els=[...document.querySelectorAll('svg > :not(rect)')];const bb=els.map(e=>e.getBBox());
const maxR=Math.round(Math.max(...bb.map(r=>Math.max(...[[r.x,r.y],[r.x+r.width,r.y],[r.x,r.y+r.height],[r.x+r.width,r.y+r.height]].map(([x,y])=>Math.hypot(x-256,y-256))))));
const ov=[];for(let i=0;i<bb.length;i++)for(let j=i+1;j<bb.length;j++){const a=bb[i],c=bb[j];if(!(a.x+a.width<=c.x||c.x+c.width<=a.x||a.y+a.height<=c.y||c.y+c.height<=a.y))ov.push(els[i].tagName+i+'×'+els[j].tagName+j)}
return {maxR,safeR:204.8,inSafe:maxR<=204.8,overlap:ov}});
await pg.evaluate(()=>{document.getElementById('s').className='c'});await pg.screenshot({path:n+'_圓形.png',omitBackground:true});
await pg.setViewportSize({width:110,height:110});await pg.evaluate(()=>{const s=document.querySelector('svg');s.setAttribute('width',110);s.setAttribute('height',110);document.getElementById('s').style.cssText='width:110px;height:110px;border-radius:50%;overflow:hidden';document.getElementById('s').className=''});
await pg.screenshot({path:n+'_110圓形.png',omitBackground:true});await pg.close()}
await b.close();fs.writeFileSync('overlap_report.json',JSON.stringify(out,null,1));console.log(JSON.stringify(out))})()
