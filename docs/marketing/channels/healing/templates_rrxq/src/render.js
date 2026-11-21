const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const D=__dirname,O=D+'/..';
(async()=>{const mf=JSON.parse(fs.readFileSync(D+'/manifest.json'));const b=await chromium.launch();const rep={};let overlaps=0,n=0;
for(const [name,[w,h]] of Object.entries(mf)){const dir=O+'/'+name.split('_').slice(0,2).join('_');fs.mkdirSync(dir,{recursive:true});
 const pg=await b.newPage({viewport:{width:w,height:h}});await pg.goto('file://'+D+'/html/'+name+'.html');await pg.waitForTimeout(250);
 await pg.screenshot({path:dir+'/'+name+'.png'});
 const r=await pg.evaluate(()=>{
  const els=[...document.querySelectorAll('[data-o]')];const boxes=[];const issues=[];
  for(const e of els){const hasText=[...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim())||e.tagName=='DIV'&&e.textContent.trim()&&!e.querySelector('svg');
    let q;if(hasText&&!e.querySelector('svg')){const rg=document.createRange();rg.selectNodeContents(e);q=rg.getBoundingClientRect()}else q=e.getBoundingClientRect();
    const cs=getComputedStyle(e);boxes.push({o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom,fs:parseFloat(cs.fontSize),txt:hasText&&!e.querySelector('svg'),color:cs.color,t:e.textContent.trim().slice(0,14)});}
  const ov=[];for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],c=boxes[j];
    if(a.o=='gap'||c.o=='gap'){}
    if(!(a.r<=c.x+.5||c.r<=a.x+.5||a.b<=c.y+.5||c.b<=a.y+.5))ov.push(a.o+'×'+c.o)}
  const W=innerWidth,H=innerHeight,oob=[];for(const a of boxes){if(a.x<95.5||a.r>W-95.5)oob.push(a.o+':'+Math.round(a.x)+'-'+Math.round(a.r))}
  const small=boxes.filter(a=>a.txt&&a.fs<30).map(a=>a.o+':'+a.fs);
  const bottom=Math.max(...boxes.map(a=>a.b));
  return {ov,oob,small,bottom,boxes:boxes.map(a=>({o:a.o,x:Math.round(a.x),y:Math.round(a.y),r:Math.round(a.r),b:Math.round(a.b),fs:a.fs,txt:a.txt,color:a.color,t:a.t})),sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight}});
 await pg.addStyleTag({content:'*{color:transparent!important}'});await pg.screenshot({path:D+'/bg_'+name+'.png'});
 rep[name]=r;overlaps+=r.ov.length;n++;await pg.close();
 if(r.ov.length||r.oob.length||r.small.length||r.sw>w||r.sh>h)console.log('問題',name,JSON.stringify({ov:r.ov,oob:r.oob,small:r.small,sw:r.sw,sh:r.sh}))}
fs.writeFileSync(D+'/report.json',JSON.stringify(rep,null,1));await b.close();console.log('張數',n,'重疊筆數',overlaps)})()
