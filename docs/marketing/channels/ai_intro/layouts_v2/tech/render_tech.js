const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const {build}=require('./gen_tech.js');
const CHECK=`()=>{const els=[...document.querySelectorAll('[data-o]')].map(e=>{const r=e.getBoundingClientRect();return {o:e.dataset.o,inn:e.dataset.in||'',x:r.left,y:r.top,w:r.right,h:r.bottom}});
const ov=[],gap=[],clip=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],c=els[j];if(a.inn===c.o||c.inn===a.o)continue;
const g=Math.max(Math.max(a.x-c.w,c.x-a.w),Math.max(a.y-c.h,c.y-a.h));if(g<0)ov.push(a.o+'×'+c.o);else if(g<24)gap.push(a.o+'×'+c.o+' '+Math.round(g))}
const oob=els.filter(e=>e.x<0||e.y<0||e.w>1080||e.h>1350).map(e=>e.o);
document.querySelectorAll('[data-o],[data-o] *').forEach(e=>{const cs=getComputedStyle(e);if(cs.display==='inline'||e.tagName==='TABLE'||e.tagName==='svg'||e.closest('svg'))return;if(e.clientWidth>0&&e.scrollWidth>e.clientWidth+2)clip.push('寬:'+(e.dataset.o||e.className||e.tagName));if(e.clientHeight>0&&e.scrollHeight>e.clientHeight+2&&e.dataset.o)clip.push('高:'+e.dataset.o)});
// 文字節點矩形
const tr=[];const wk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=wk.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('style,svg'))continue;const r=document.createRange();r.selectNodeContents(n);for(const q of r.getClientRects())if(q.width>0)tr.push({x:q.left,y:q.top,w:q.right,h:q.bottom,t:n.textContent.trim().slice(0,6)})}
const dcx=[];document.querySelectorAll('.dc').forEach(d=>{const q=d.getBoundingClientRect();for(const t of tr){if(q.left<t.w&&q.right>t.x&&q.top<t.h&&q.bottom>t.y){dcx.push(t.t);break}}});
const small=tr.length?[...document.querySelectorAll('[data-o],[data-o] *')].filter(e=>[...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<28).map(e=>e.textContent.slice(0,8)):[];
const minDisc=Math.min(...[...document.querySelectorAll('.disc')].map(e=>parseFloat(getComputedStyle(e).fontSize)));
return {n:els.length,overlap:ov,gap24:gap,oob,clip,decoOnText:dcx,minDisc,small}}`;
(async()=>{const b=await chromium.launch();const res={};
for(const v of ['a','b','c']){const {css,pages}=build(v);const nm='T4'+v;
 for(let i=0;i<4;i++){const html=`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${css}</style><body>${pages[i]}</body></html>`;
  fs.writeFileSync(`html/${nm}_${i+1}.html`,html);
  const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+process.cwd()+`/html/${nm}_${i+1}.html`);await pg.waitForTimeout(200);
  await pg.screenshot({path:`png/${nm}_${i+1}.png`});res[`${nm}_${i+1}`]=await pg.evaluate(eval(CHECK));await pg.close()}}
await b.close();fs.writeFileSync('check_result.json',JSON.stringify(res,null,1));
for(const k in res){const r=res[k];console.log(k,'ov',r.overlap.join(','),'gap',r.gap24.join(','),'oob',r.oob.join(','),'clip',r.clip.join(','),'decoText',r.decoOnText.join(','),'small',r.small.join(','))}})()
