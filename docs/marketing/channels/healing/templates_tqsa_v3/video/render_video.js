// 逐幀渲染：node render_video.js <名>  → 幀 PNG（tmp）→ ffmpeg H.264＋靜音 AAC（IG Reels／Threads 相容）→ queue/<名>/video.mp4
// 同時抽 0.5 秒一格做重疊檢查（data-o 元素兩兩不相交、不出邊界、不進 Reels 上 220／下 420 安全區），寫 overlap_report_video.json
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');const {execFileSync}=require('child_process');
const name=process.argv[2];const html=path.join(__dirname,'html',name+'.html');
const out=path.join(__dirname,'..','..','queue',name);const tmp=path.join(__dirname,'tmp',name);
fs.rmSync(tmp,{recursive:true,force:true});fs.mkdirSync(tmp,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+html);await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const n=Math.round(V.dur*V.fps);const rep={frames:n,checked:0,overlap:[],oob:[]};
 for(let f=0;f<n;f++){const t=f/V.fps;await pg.evaluate(t=>window.renderAt(t),t);
  await pg.screenshot({path:path.join(tmp,String(f).padStart(5,'0')+'.png')});
  if(f%Math.round(V.fps/2)===0){rep.checked++;
   const r=await pg.evaluate(()=>{const els=[...document.querySelectorAll('[data-o]')].filter(e=>{let x=e;while(x&&x!==document.body){if(parseFloat(getComputedStyle(x).opacity)<0.02)return false;x=x.parentElement}return true}).map(e=>{const q=e.getBoundingClientRect();return{o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom}});
    const ov=[],oob=[];for(let i=0;i<els.length;i++){const a=els[i];if(a.x<90||a.r>990||a.y<220||a.b>1500)oob.push(a.o);for(let j=i+1;j<els.length;j++){const c=els[j];if(!(a.r<=c.x||c.r<=a.x||a.b<=c.y||c.b<=a.y))ov.push(a.o+'×'+c.o)}}return{ov,oob}});
   r.ov.forEach(x=>rep.overlap.push(t.toFixed(1)+'s '+x));r.oob.forEach(x=>rep.oob.push(t.toFixed(1)+'s '+x))}}
 await b.close();
 execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(V.fps),'-i',path.join(tmp,'%05d.png'),'-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100',
  '-shortest','-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-crf','20','-r',String(V.fps),'-c:a','aac','-b:a','128k','-movflags','+faststart',path.join(out,'video.mp4')]);
 execFileSync('ffmpeg',['-y','-loglevel','error','-i',path.join(tmp,String(Math.round(4.6*V.fps)).padStart(5,'0')+'.png'),'-q:v','3',path.join(out,'video_cover.jpg')]);
 fs.writeFileSync(path.join(out,'overlap_report_video.json'),JSON.stringify(rep,null,1));
 console.log('幀數',n,'抽檢',rep.checked,'重疊',rep.overlap.length,'出界',rep.oob.length);rep.overlap.slice(0,10).forEach(x=>console.log(x));rep.oob.slice(0,10).forEach(x=>console.log('出界',x))})();
