const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const J=JSON.parse(fs.readFileSync('jobs.json','utf8')).jobs;const b=await chromium.launch();const out={};
const pg0=await b.newPage();
for(const j of J){const pg=pg0;await pg.setViewportSize({width:j.w,height:j.h});
await pg.setContent(`<style>body{margin:0;background:transparent}</style>${fs.readFileSync(j.svg,'utf8')}`);await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(60);
out[j.svg]=await pg.evaluate(ids=>{const o={};const cv=document.createElement('canvas').getContext('2d');
for(const i of ids){const e=document.getElementById(i);if(!e)continue;const x=e.getBoundingClientRect();
 if(e.tagName==='text'){const fs=+e.dataset.fs,fam=e.getAttribute('font-family').split(',')[0].replace(/'/g,''),w=e.getAttribute('font-weight');cv.font=`${w} ${fs}px "${fam}"`;const t=e.textContent;const m=cv.measureText(t);
  const ls=+(e.getAttribute('letter-spacing')||0);const c=e.getScreenCTM();const sc=c.d;const base=c.f+sc*(+e.getAttribute('y'));o[i]=[x.left,base-sc*m.actualBoundingBoxAscent,x.right-(e.getAttribute('text-anchor')==='start'?ls*sc:0),base+sc*m.actualBoundingBoxDescent];}
 else o[i]=[x.left,x.top,x.right,x.bottom]}return o},j.ids||[]);
await pg.screenshot({path:j.png,omitBackground:!!j.transparent});}
fs.writeFileSync('boxes.json',JSON.stringify(out));await b.close();console.log('ok',J.length)})();
