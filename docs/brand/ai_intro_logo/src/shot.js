const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const jobs=JSON.parse(fs.readFileSync(__dirname+'/html/jobs.json'));const rep={};
for(const j of jobs){const pg=await b.newPage({viewport:{width:j.w,height:j.h}});await pg.goto('file://'+__dirname+'/html/'+j.html);await pg.waitForTimeout(300);
await pg.screenshot({path:j.out,fullPage:!!j.full,omitBackground:!!j.transparent});
if(j.check){rep[j.html]=await pg.evaluate(()=>{const els=[...document.querySelectorAll('[data-el]')].map(e=>{const r=e.getBoundingClientRect();return [e.dataset.el,r.left,r.top,r.right,r.bottom]});
const hits=[];let minGap=1e9;for(let i=0;i<els.length;i++)for(let k=i+1;k<els.length;k++){const a=els[i],c=els[k];if(a[1]<c[3]&&c[1]<a[3]&&a[2]<c[4]&&c[2]<a[4])hits.push(a[0]+'x'+c[0]);
const dx=Math.max(a[1]-c[3],c[1]-a[3]),dy=Math.max(a[2]-c[4],c[2]-a[4]);minGap=Math.min(minGap,Math.max(dx,dy));}
return {n:els.length,hits,out:els.filter(e=>e[1]<0||e[2]<0||e[3]>1080||e[4]>1350).map(e=>e[0]),minGap:Math.round(minGap)}})}
await pg.close()}
console.log(JSON.stringify(rep));await b.close()})()
