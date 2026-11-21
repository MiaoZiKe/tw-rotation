// 渲染 PNG＋逐張檢查（元素兩兩不相交、間距≥32、不出邊界、字級≥30、插圖內容不溢出）；結果寫 ../overlap_report.json
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const mf=JSON.parse(fs.readFileSync(__dirname+'/manifest_long.json','utf8'));
fs.mkdirSync(__dirname+'/tmp',{recursive:true});
const CHECK=()=>{
 const els=[...document.querySelectorAll('[data-o]')].map(e=>{const rg=document.createRange();rg.selectNodeContents(e);const r=e.getBoundingClientRect();const t=rg.getBoundingClientRect();
  const isIll=e.dataset.o==='illus';
  return {o:e.dataset.o,x:isIll?r.left:Math.min(r.left,t.width?t.left:r.left),y:isIll?r.top:Math.min(r.top,t.height?t.top:r.top),r:isIll?r.right:Math.max(r.right,t.width?t.right:r.right),b:isIll?r.bottom:Math.max(r.bottom,t.height?t.bottom:r.bottom)}});
 const ov=[],gap=[];
 for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],b=els[j];
  const g=Math.max(Math.max(a.x-b.r,b.x-a.r),Math.max(a.y-b.b,b.y-a.b));
  if(g<0)ov.push(a.o+'×'+b.o);else if(g<32)gap.push(a.o+'×'+b.o+' '+Math.round(g)+'px')}
 const W=document.body.clientWidth,H=document.body.clientHeight;
 const oob=els.filter(e=>e.x<95||e.y<48||e.r>(e.o==='logo'?996:985)||e.b>H-48).map(e=>e.o+' ['+Math.round(e.x)+','+Math.round(e.y)+','+Math.round(e.r)+','+Math.round(e.b)+']');
 const minFont=Math.min(...[...document.querySelectorAll('[data-o] *,[data-o]')].filter(e=>[...e.childNodes].some(n=>n.nodeType==3&&n.textContent.trim())).map(e=>parseFloat(getComputedStyle(e).fontSize)));
 // 插圖墨跡（不含光暈）是否在插圖框內
 let ink=null;const g=document.getElementById('ink'),ill=document.querySelector('.illus');
 if(g&&ill){const kids=[...g.children].filter(c=>!c.hasAttribute('data-g'));let L=1e9,T=1e9,Rr=-1e9,Bb=-1e9;
  for(const c of kids){const q=c.getBoundingClientRect?c.getBoundingClientRect():null;if(!q||!q.width)continue;
   // 被 clip-path 裁切的群組以 bbox 為上限，仍算入
   L=Math.min(L,q.left);T=Math.min(T,q.top);Rr=Math.max(Rr,q.right);Bb=Math.max(Bb,q.bottom)}
  const ib=ill.getBoundingClientRect();ink={L:Math.round(L),T:Math.round(T),R:Math.round(Rr),B:Math.round(Bb),box:[ib.left,ib.top,ib.right,ib.bottom].map(Math.round),inside:(L>=ib.left-1&&T>=ib.top-1&&Rr<=ib.right+1&&Bb<=ib.bottom+1)}}
 const tx=[];document.querySelectorAll('body *').forEach(e=>{if(e.closest('svg')&&e.tagName!=='text')return;if(![...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim()))return;
  const rg=document.createRange();rg.selectNodeContents(e);const rc=rg.getBoundingClientRect();const cs=getComputedStyle(e);
  tx.push({t:e.textContent.trim().slice(0,12),x:rc.left,y:rc.top,w:rc.width,h:rc.height,color:cs.color,fs:parseFloat(cs.fontSize)})});
 return {n:els.length,overlap:ov,gap32:gap,oob,minFont,ink,tx}};
(async()=>{const b=await chromium.launch();const rep={};let bad=0,n=0;const lines=[];
 for(const m of mf){const pg=await b.newPage({viewport:{width:m.W,height:m.H}});
  await pg.goto('file://'+path.join(__dirname,m.html));await pg.waitForTimeout(350);
  fs.mkdirSync(path.dirname(path.join(__dirname,m.png)),{recursive:true});
  await pg.screenshot({path:path.join(__dirname,m.png)});
  const r=await pg.evaluate(CHECK);
  r.scrollH=await pg.evaluate(()=>document.documentElement.scrollHeight);
  if(m.safe){const bs=await pg.evaluate(()=>[...document.querySelectorAll('[data-o]')].map(e=>{const q=e.getBoundingClientRect();return [e.dataset.o,q.top,q.bottom]}));
   r.outside_safe=bs.filter(x=>x[1]<m.safe[0]||x[2]>m.safe[1]).map(x=>x[0]);}
  await pg.addStyleTag({content:'*{color:transparent!important}'});
  const bgp=path.join(__dirname,'tmp',m.key.replace(/\//g,'__')+'.bg.png');await pg.screenshot({path:bgp});
  fs.writeFileSync(bgp.replace('.bg.png','.tx.json'),JSON.stringify(r.tx));delete r.tx;
  rep[m.key]=r;n++;bad+=r.overlap.length;
  if(r.overlap.length||r.gap32.length||r.oob.length||r.minFont<30||r.scrollH>m.H||(r.ink&&!r.ink.inside)||(r.outside_safe&&r.outside_safe.length))lines.push(m.key+' '+JSON.stringify({o:r.overlap,g:r.gap32,oob:r.oob,f:r.minFont,sh:r.scrollH,ink:r.ink,safe:r.outside_safe}));
  await pg.close()}
 fs.writeFileSync(path.join(__dirname,'..','首篇_長版2頁','overlap_report.json'),JSON.stringify(rep,null,1));
 await b.close();console.log('張數',n,'重疊筆數',bad);lines.forEach(l=>console.log(l))})()
