const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const {out,put}=require('./gen.js');
const T=['T1','T2','T3','T4'];
(async()=>{for(const t of T)put(t,out[t+'css'],out[t]);
const b=await chromium.launch();const res={};
const CHECK=`()=>{const els=[...document.querySelectorAll('[data-o]')].map(e=>{const r=e.getBoundingClientRect();return {o:e.dataset.o,inn:e.dataset.in||'',x:r.left,y:r.top,w:r.right,h:r.bottom,e}});
const ov=[],gap=[],clip=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],c=els[j];if(a.inn===c.o||c.inn===a.o)continue;
const gx=Math.max(a.x-c.w,c.x-a.w),gy=Math.max(a.y-c.h,c.y-a.h),g=Math.max(gx,gy);
if(g<0)ov.push(a.o+'×'+c.o);else if(g<24)gap.push(a.o+'×'+c.o+' '+Math.round(g)+'px')}
const W=1080,H=1350;const oob=els.filter(e=>e.x<0||e.y<0||e.w>W||e.h>H).map(e=>e.o);
document.querySelectorAll('[data-o],[data-o] *').forEach(e=>{if(e.scrollHeight>e.clientHeight+2&&e.clientHeight>0&&getComputedStyle(e).display!=='inline'&&e.tagName!=='TABLE'&&e.tagName!=='svg')clip.push((e.dataset&&e.dataset.o)||e.className||e.tagName)});
const minDisc=Math.min(...[...document.querySelectorAll('.disc')].map(e=>parseFloat(getComputedStyle(e).fontSize)));
const small=[...document.querySelectorAll('[data-o],[data-o] *')].filter(e=>e.childNodes.length&&[...e.childNodes].some(n=>n.nodeType==3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<28).map(e=>e.textContent.slice(0,8));
return {n:els.length,overlap:ov,gap24:gap,oob,clip,minDisc,small}}`;
for(const t of T)for(let i=1;i<=4;i++){const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+process.cwd()+`/html/${t}_${i}.html`);await pg.waitForTimeout(150);
fs.mkdirSync('png',{recursive:true});await pg.screenshot({path:`png/${t}_${i}.png`});res[`${t}_${i}`]=await pg.evaluate(eval(CHECK));await pg.close()}
await b.close();fs.writeFileSync('check_result.json',JSON.stringify(res,null,1));
for(const k in res){const r=res[k];console.log(k,'ov',r.overlap.join(','),'gap',r.gap24.join(','),'oob',r.oob.join(','),'clip',r.clip.join(','),'small',r.small.join(','))}})()
