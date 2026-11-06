// 轉圖＋重疊檢查：所有 data-o 元素（文字框、插圖框、LOGO、頁碼、膠囊、小圖）兩兩不相交、不出邊界（左右 96px 安全距）、文字不溢出、字級 ≥30
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const D=__dirname,O=D+'/..';
(async()=>{const mf=JSON.parse(fs.readFileSync(D+'/manifest.json'));const b=await chromium.launch();const rep={};let overlaps=0,n=0,boxesN=0;
for(const [name,[w,h]] of Object.entries(mf)){const png=O+'/'+name+'.png';fs.mkdirSync(require('path').dirname(png),{recursive:true});
 const pg=await b.newPage({viewport:{width:w,height:h}});await pg.goto('file://'+D+'/html/'+name+'.html');await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(200);
 await pg.screenshot({path:png});
 const r=await pg.evaluate(()=>{
  const els=[...document.querySelectorAll('[data-o]')];const boxes=[];
  for(const e of els){const isImg=e.tagName=='IMG'||e.querySelector('svg')||e.tagName=='svg';const hasText=!isImg&&e.textContent.trim();
    let q;if(hasText){const rg=document.createRange();rg.selectNodeContents(e);q=rg.getBoundingClientRect()}else q=e.getBoundingClientRect();
    const cs=getComputedStyle(e);const cols=[cs.color];e.querySelectorAll('span').forEach(s=>cols.push(getComputedStyle(s).color));
    boxes.push({o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom,fs:parseFloat(cs.fontSize),txt:!!hasText,colors:cols,t:e.textContent.trim().slice(0,14)});}
  const ov=[];for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],c=boxes[j];
    if(!(a.r<=c.x+.5||c.r<=a.x+.5||a.b<=c.y+.5||c.b<=a.y+.5))ov.push(a.o+'×'+c.o)}
  const W=innerWidth,H=innerHeight,oob=[];for(const a of boxes){if(a.x<95.5||a.r>W-95.5||a.y<0||a.b>H)oob.push(a.o+':'+Math.round(a.x)+'-'+Math.round(a.r))}
  const small=boxes.filter(a=>a.txt&&a.fs<30).map(a=>a.o+':'+a.fs);
  const ill=boxes.filter(a=>a.o=='illus').map(a=>a.b-a.y);
  return {ov,oob,small,ill:ill[0]||0,boxes:boxes.map(a=>({o:a.o,x:Math.round(a.x),y:Math.round(a.y),r:Math.round(a.r),b:Math.round(a.b),fs:a.fs,txt:a.txt,colors:a.colors,t:a.t})),sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight}});
 await pg.addStyleTag({content:'*{color:transparent!important}'});await pg.screenshot({path:D+'/bg/'+name.replace(/\//g,'__')+'.png'});
 rep[name]=r;overlaps+=r.ov.length;boxesN+=r.boxes.length;n++;await pg.close();
 if(r.ov.length||r.oob.length||r.small.length||r.sw>w||r.sh>h)console.log('問題',name,JSON.stringify({ov:r.ov,oob:r.oob,small:r.small,sw:r.sw,sh:r.sh}))}
fs.writeFileSync(D+'/report.json',JSON.stringify(rep,null,1));
const out={張數:n,元素數:boxesN,重疊筆數:overlaps,逐張:Object.fromEntries(Object.entries(rep).map(([k,v])=>[k,{元素:v.boxes.length,重疊:v.ov,出界:v.oob,字級過小:v.small,插圖高佔比:+(v.ill/mf[k][1]).toFixed(2),捲動溢出:v.sw>mf[k][0]||v.sh>mf[k][1]}]))};
fs.writeFileSync(O+'/overlap_report.json',JSON.stringify(out,null,1));await b.close();console.log('張數',n,'重疊筆數',overlaps)})()
