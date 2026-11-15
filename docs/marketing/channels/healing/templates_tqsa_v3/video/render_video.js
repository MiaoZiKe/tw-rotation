// 逐幀渲染：node render_video.js <名>  → 幀 PNG（tmp）→ ffmpeg H.264＋靜音 AAC（IG Reels／Threads 相容）→ queue/<名>/video.mp4
// 同時抽 0.5 秒一格做重疊檢查（data-o 元素兩兩不相交、不出邊界、不進 Reels 上 220／下 420 安全區），寫 overlap_report_video.json
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');const {execFileSync}=require('child_process');
const name=process.argv[2];const html=path.join(__dirname,'html',name+'.html');
const tmp=path.join(__dirname,'tmp',name);
fs.rmSync(tmp,{recursive:true,force:true});fs.mkdirSync(tmp,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+html);await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const out=path.join(__dirname,'..','..','queue',V.queue||name);
 const OUT=V.out||'video.mp4',COVER=V.cover||'video_cover.jpg',REP=V.report||'overlap_report_video.json',CT=V.cover_t==null?4.6:V.cover_t;const n=Math.round(V.dur*V.fps);const rep={frames:n,checked:0,overlap:[],oob:[]};if(V.edge60)rep.edge=[];
 for(let f=0;f<n;f++){const t=f/V.fps;await pg.evaluate(t=>window.renderAt(t),t);
  await pg.screenshot({path:path.join(tmp,String(f).padStart(5,'0')+'.png')});
  if(f%Math.round(V.fps/2)===0){rep.checked++;
   const r=await pg.evaluate((E)=>{const els=[...document.querySelectorAll('[data-o]')].filter(e=>{let x=e;while(x&&x!==document.body){if(parseFloat(getComputedStyle(x).opacity)<0.02)return false;x=x.parentElement}return true}).map(e=>{const q=e.getBoundingClientRect();return{o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom}});
    const ov=[],oob=[],ws=[];
    // v1：Reels 安全區（上 220／下 420）。v2（V.edge60）：2026-11-15 Andy「紅框處還有空間」→ 上下留白各 ≤60px、字幕卡下緣 ≤1700、1700 以下只放出處與頁尾帶
    const Y0=E?40:220,Y1=E?1880:1500;
    if(E&&els.length){const top=Math.min(...els.map(e=>e.y)),bot=1920-Math.max(...els.map(e=>e.b));if(top>60)ws.push('頂端留白 '+Math.round(top)+'px');if(bot>60)ws.push('底端留白 '+Math.round(bot)+'px');
     els.forEach(e=>{if(e.b>1700&&!['src','foot'].includes(e.o))ws.push(e.o+' 下緣 '+Math.round(e.b)+'>1700')});ws.top=top;ws.bot=bot}
    for(let i=0;i<els.length;i++){const a=els[i];if(a.x<90||a.r>990||a.y<Y0||a.b>Y1)oob.push(a.o);for(let j=i+1;j<els.length;j++){const c=els[j];if(!(a.r<=c.x||c.r<=a.x||a.b<=c.y||c.b<=a.y))ov.push(a.o+'×'+c.o)}}return{ov,oob,ws,top:ws.top,bot:ws.bot}},!!V.edge60);
   r.ov.forEach(x=>rep.overlap.push(t.toFixed(1)+'s '+x));r.oob.forEach(x=>rep.oob.push(t.toFixed(1)+'s '+x));
   if(V.edge60){(rep.edge=rep.edge||[]).push(...r.ws.map(x=>t.toFixed(1)+'s '+x));rep.gapTopMax=Math.max(rep.gapTopMax||0,r.top);rep.gapBotMax=Math.max(rep.gapBotMax||0,r.bot)}}}
 await b.close();
 // 有旁白音檔（segments.json 的 audio）就用旁白；沒有就放靜音音軌（相容性）
 const AIN=V.audio&&fs.existsSync(V.audio)?['-i',V.audio]:['-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100'];
 execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(V.fps),'-i',path.join(tmp,'%05d.png'),...AIN,
  '-t',String(n/V.fps),'-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-crf','20','-r',String(V.fps),'-c:a','aac','-b:a','128k','-movflags','+faststart',path.join(out,OUT)]);
 execFileSync('ffmpeg',['-y','-loglevel','error','-i',path.join(tmp,String(Math.round(CT*V.fps)).padStart(5,'0')+'.png'),'-q:v','3',path.join(out,COVER)]);
 rep.dur=n/V.fps;rep.timing=V.timing||'default';rep.scenes=(V.scenes||[]).map(x=>({id:x.id,type:x.type,t0:x.t0,t1:x.t1}));
 fs.writeFileSync(path.join(out,REP),JSON.stringify(rep,null,1));
 console.log('幀數',n,'抽檢',rep.checked,'重疊',rep.overlap.length,'出界',rep.oob.length,'上下留白錯誤',(rep.edge||[]).length,'頂端最大留白',rep.gapTopMax,'底端最大留白',rep.gapBotMax);(rep.edge||[]).slice(0,10).forEach(x=>console.log('留白',x));rep.overlap.slice(0,10).forEach(x=>console.log(x));rep.oob.slice(0,10).forEach(x=>console.log('出界',x))})();
