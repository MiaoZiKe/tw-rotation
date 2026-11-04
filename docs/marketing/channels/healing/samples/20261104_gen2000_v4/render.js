const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const CHECK=fs.readFileSync(__dirname+'/../../layouts/check.js.txt','utf8');
(async()=>{const b=await chromium.launch();let n=0,bad=0,lines=[];
for(const p of ["post1","post2","post3","post4"]){const d=__dirname+'/'+p;const mf=JSON.parse(fs.readFileSync(d+'/manifest.json'));const out={};
for(const [name,H] of Object.entries(mf)){const pg=await b.newPage({viewport:{width:1080,height:H}});await pg.goto('file://'+d+'/html/'+name+'.html');await pg.waitForTimeout(400);
await pg.screenshot({path:d+'/'+name+'.png'});
const r=await pg.evaluate(eval(CHECK),{});
const ex=await pg.evaluate(()=>{
 const lineCol=getComputedStyle(document.body).getPropertyValue('--w-line').trim();
 const els=[...document.querySelectorAll('[data-o]')].filter(e=>e.dataset.o!=='illus');
 const bottom=[],right=[];
 for(const e of els){const o=e.dataset.o;const rg=document.createRange();rg.selectNodeContents(e);const t=rg.getBoundingClientRect();const r=e.getBoundingClientRect();
  const bt=Math.max(r.bottom,t.bottom),rt=Math.max(r.right,t.right);
  if(o!=='foot'&&o!=='acct'&&bt>1190)bottom.push(o+':'+Math.round(bt));
  if(o!=='pg'&&o!=='acct'&&rt>960.5)right.push(o+':'+Math.round(rt));}
 // 提示色只准一次
 const hint=document.querySelectorAll('.hintuse,.bar.now').length;
 // 長條比例
 const bars=[...document.querySelectorAll('.bar[data-v],.fl[data-v]')].map(e=>({v:parseFloat(e.dataset.v),w:e.getBoundingClientRect().width,h:e.className}));
 // 文字清單（供對比檢查）
 const tx=[];document.querySelectorAll('body *').forEach(e=>{if(![...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim()))return;
  if(e.closest('svg'))return;const rg=document.createRange();rg.selectNodeContents(e);const rc=rg.getBoundingClientRect();const cs=getComputedStyle(e);
  tx.push({t:e.textContent.trim().slice(0,12),x:rc.left,y:rc.top,w:rc.width,h:rc.height,color:cs.color,fs:parseFloat(cs.fontSize)})});
 // 光暈範圍（svg 內 data-g）不得與文字框相交
 const ill=document.querySelector('.illus');const ir=ill?ill.getBoundingClientRect():null;
 const gl=ir?[...document.querySelectorAll("[data-g]")].map(e=>{const q=e.getBoundingClientRect();return {left:Math.max(q.left,ir.left),right:Math.min(q.right,ir.right),top:Math.max(q.top,ir.top),bottom:Math.min(q.bottom,ir.bottom)}}):[];
 const glowHit=[];for(const g of gl)for(const e of els){if(e.dataset.o==='illus')continue;const q=e.getBoundingClientRect();if(!(q.right<g.left||q.left>g.right||q.bottom<g.top||q.top>g.bottom))glowHit.push(e.dataset.o)}
 return {bottom,right,hint,bars,tx,glowHit,illus:ir&&{x:ir.left,y:ir.top,w:ir.width,h:ir.height}}});
r.extra={bottom_over_1190:ex.bottom,right_over_960:ex.right,hint_uses:ex.hint,glow_hits:ex.glowHit,illus_box:ex.illus,bars:ex.bars};
// 比例檢查（同一組 bar 的 w/v 一致）
const bs=ex.bars.filter(x=>x.h.includes('bar'));if(bs.length){const k=bs.map(x=>x.w/x.v);r.extra.bar_ratio_spread=(Math.max(...k)-Math.min(...k))/Math.max(...k)}
const fl=ex.bars.filter(x=>x.h.includes('fl'));if(fl.length)r.extra.strip_pct=fl[0].w/(864-48-6)*100;
r.bodyScrollH=await pg.evaluate(()=>document.documentElement.scrollHeight);
// 無字底圖（對比檢查用）
await pg.addStyleTag({content:'*{color:transparent!important}'});await pg.screenshot({path:d+'/'+name+'.bg.png'});
fs.writeFileSync(d+'/'+name+'.tx.json',JSON.stringify(ex.tx));
out[name]=r;await pg.close();
n++;bad+=r.overlap.length;
if(r.overlap.length||r.oob_margin.length||r.gap32.length||r.minFont<28||ex.bottom.length||ex.right.length||ex.hint>1||ex.glowHit.length)lines.push(p+' '+name+' '+JSON.stringify({o:r.overlap,g:r.gap32,oob:r.oob_margin,f:r.minFont,b:ex.bottom,r:ex.right,h:ex.hint,gl:ex.glowHit}))}
fs.writeFileSync(d+'/overlap_report.json',JSON.stringify(out,null,1))}
await b.close();console.log('張數',n,'重疊筆數',bad);lines.forEach(l=>console.log(l))})()
