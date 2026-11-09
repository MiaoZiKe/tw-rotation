const {chromium}=require('/opt/node-tools/node_modules/playwright');
const fs=require('fs');
const OUT=process.argv[2], FPS=30, DUR=40.5, mode=process.argv[3]||'all';
(async()=>{
 const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+__dirname+'/video.html');await pg.waitForTimeout(500);
 const rep=[];let N=0;
 if(mode==='test'){for(const t of [0.5,2,3.5,6,9,12,16,20,23,26,29,33,36,39]){await pg.evaluate(t=>render(t),t);const r=await pg.evaluate(()=>check());console.log(t,JSON.stringify(r));await pg.screenshot({path:OUT+'/t_'+t+'.png'})}await b.close();return}
 fs.mkdirSync(OUT+'/frames',{recursive:true});
 const total=Math.round(DUR*FPS);
 for(let f=0;f<total;f++){const t=f/FPS;
  const r=await pg.evaluate(t=>{render(t);return check()},t);N++;
  if(r.length)rep.push({frame:f,t:+t.toFixed(3),issues:r});
  await pg.screenshot({path:`${OUT}/frames/f${String(f).padStart(5,'0')}.png`});}
 // 封面
 await pg.evaluate(()=>render(9.5,{noSub:true}));const rc=await pg.evaluate(()=>check());
 await pg.screenshot({path:OUT+'/cover.png'});
 fs.writeFileSync(OUT+'/overlap_report.json',JSON.stringify({frames_checked:N,fps:FPS,violations:rep.length,cover_issues:rc,details:rep},null,1));
 console.log('frames',N,'violations',rep.length,'cover',rc.length);
 await b.close();})();
