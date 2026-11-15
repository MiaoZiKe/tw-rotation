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
  if(V.runtime&&/v5/.test(V.runtime)){   // v5：片尾 LOGO 圖形與四字逐幀淨空（≥24px；LOGO 框外加 22px 描邊）
   const gp=await pg.evaluate(()=>{const l=document.querySelector('#stage [data-chk=logo]'),cs=[...document.querySelectorAll('#stage [data-chk=char]')];if(!l||!cs.length)return null;
    const lb=l.getBoundingClientRect(),res=[];cs.forEach((c,i)=>{let x=c,vis=1;while(x&&x!==document.body){vis*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}if(vis<.3)return;const b=c.getBoundingClientRect();
     const ox=Math.min(lb.right+22,b.right)-Math.max(lb.left-22,b.left),gap=b.top-(lb.bottom+22);res.push({i,gap:+gap.toFixed(1),ox:+ox.toFixed(1)})});return res});
   if(gp)gp.forEach(r=>{(rep.logoGap=rep.logoGap||[]).push({t:+t.toFixed(3),i:r.i,gap:r.gap});rep.logoGapMin=Math.min(rep.logoGapMin==null?1e9:rep.logoGapMin,r.gap);if(r.gap<24)(rep.logoOverlap=rep.logoOverlap||[]).push(t.toFixed(3)+'s 字'+r.i+' 離雲 '+r.gap+'px')})}
  if(V.runtime&&/v4/.test(V.runtime)){   // v4：插圖面板外框尺寸與面板底板尺寸逐幀記錄（同一鏡內只准一組＝沒有縮放、沒有平移）
   const q=await pg.evaluate(()=>{const e=document.querySelector('#stage [data-o=illus]');if(!e)return null;const r=e.getBoundingClientRect(),b=e.querySelector('svg g > rect'),br=b?b.getBoundingClientRect():null,g=e.querySelector('svg > g');return{o:[r.left,r.top,r.width,r.height].map(x=>+x.toFixed(2)).join(','),b:br?[br.left,br.top,br.width,br.height].map(x=>+x.toFixed(2)).join(','):'',tf:g?(g.getAttribute('transform')||''):''}});
   if(q){const sc=V.scenes.find(x=>t>=x.t0&&t<x.t1)||V.scenes[V.scenes.length-1];const m=(rep.panel=rep.panel||{});const r=(m[sc.id]=m[sc.id]||{frame:{},base:{},transform:{}});r.frame[q.o]=(r.frame[q.o]||0)+1;r.base[q.b]=(r.base[q.b]||0)+1;r.transform[q.tf||'（無）']=(r.transform[q.tf||'（無）']||0)+1}}
  await pg.screenshot({path:path.join(tmp,String(f).padStart(5,'0')+'.png')});
  if(f%Math.round(V.fps/2)===0){rep.checked++;
   const r=await pg.evaluate((E)=>{const els=[...document.querySelectorAll('[data-o]')].filter(e=>{let x=e;while(x&&x!==document.body){if(parseFloat(getComputedStyle(x).opacity)<0.02)return false;x=x.parentElement}return true}).map(e=>{const q=e.getBoundingClientRect();return{o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom}});
    const ov=[],oob=[],ws=[];
    // v1：Reels 安全區（上 220／下 420）。v2（V.edge60）：2026-11-15 Andy「紅框處還有空間」→ 上下留白各 ≤60px、字幕卡下緣 ≤1700、1700 以下只放出處與頁尾帶
    const Y0=E?40:220,Y1=E?1880:1500;
    if(E&&els.length){const top=Math.min(...els.map(e=>e.y)),bot=1920-Math.max(...els.map(e=>e.b));if(top>60)ws.push('頂端留白 '+Math.round(top)+'px');if(bot>60)ws.push('底端留白 '+Math.round(bot)+'px');
     els.forEach(e=>{if(e.b>1700&&!['src','foot'].includes(e.o))ws.push(e.o+' 下緣 '+Math.round(e.b)+'>1700')});ws.top=top;ws.bot=bot}
    // v3 起：小字檢查。v5 修正：舊版只看 CSS font-size，漏掉被 svg 縮放的字；改用「字級 × 實際螢幕縮放」（svg 取 getScreenCTM），且只量完全可見（不透明度 ≥.9）的字
    if(E){[...document.querySelectorAll('#stage text, #stage div')].forEach(e=>{if(!e.textContent.trim()||e.children.length&&e.tagName!=='text'||e.closest('clipPath'))return;let x=e,vis=1;while(x&&x!==document.body){vis*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}
     let fs=parseFloat(getComputedStyle(e).fontSize);if(e.tagName==='text'&&e.getScreenCTM){const m=e.getScreenCTM();fs*=Math.hypot(m.a,m.b)}
     if(vis>=.9&&fs<29.5&&!e.closest('[data-x]'))ws.push('小字 '+fs.toFixed(1)+'px「'+e.textContent.trim().slice(0,8)+'」')})}
    for(let i=0;i<els.length;i++){const a=els[i];if(a.x<90||a.r>990||a.y<Y0||a.b>Y1)oob.push(a.o);for(let j=i+1;j<els.length;j++){const c=els[j];if(!(a.r<=c.x||c.r<=a.x||a.b<=c.y||c.b<=a.y))ov.push(a.o+'×'+c.o)}}return{ov,oob,ws,top:ws.top,bot:ws.bot}},!!V.edge60);
   r.ov.forEach(x=>rep.overlap.push(t.toFixed(1)+'s '+x));r.oob.forEach(x=>rep.oob.push(t.toFixed(1)+'s '+x));
   if(V.edge60){(rep.edge=rep.edge||[]).push(...r.ws.map(x=>t.toFixed(1)+'s '+x));rep.gapTopMax=Math.max(rep.gapTopMax||0,r.top);rep.gapBotMax=Math.max(rep.gapBotMax||0,r.bot)}}}
 await b.close();
 // 有旁白音檔（segments.json 的 audio）就用旁白；沒有就放靜音音軌（相容性）
 let AIN=V.audio&&fs.existsSync(V.audio)?['-i',V.audio]:['-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100'];
 // v3：音效（video_runtime_v3.js 的 sfxEvents）＋旁白 → sfx_v3.py 合成、限幅、量片尾響度與開頭起音 → AAC，直接接進影片
 if(V.sfx){const b2=await chromium.launch();const p2=await b2.newPage();await p2.goto('file://'+html);await p2.waitForTimeout(300);
  const ev=await p2.evaluate(()=>window.sfxEvents());await b2.close();const evp=path.join(tmp,'sfx_events.json');fs.writeFileSync(evp,JSON.stringify(ev));
  const ot=(V.scenes.find(x=>x.type==='outro')||{t0:V.dur}).t0,am=path.join(tmp,'audio.m4a'),base=OUT.replace(/\.mp4$/,'');
  execFileSync('python3',[path.join(__dirname,'sfx_v3.py'),evp,String(n/V.fps),String(ot),am,path.join(out,base+'_audio.json'),V.audio&&fs.existsSync(V.audio)?V.audio:'',path.join(out,base+'_outro_sfx.mp3')],{stdio:'inherit',env:Object.assign({},process.env,{OUTRO_LUFS:String(V.outro_lufs||-11.5)})});
  AIN=['-i',am]}
 execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(V.fps),'-i',path.join(tmp,'%05d.png'),...AIN,
  '-t',String(n/V.fps),'-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-crf','20','-r',String(V.fps),...(V.sfx?['-c:a','copy']:['-c:a','aac','-b:a','128k']),'-movflags','+faststart',path.join(out,OUT)]);
 execFileSync('ffmpeg',['-y','-loglevel','error','-i',path.join(tmp,String(Math.round(CT*V.fps)).padStart(5,'0')+'.png'),'-q:v','3',path.join(out,COVER)]);
 rep.dur=n/V.fps;rep.timing=V.timing||'default';rep.scenes=(V.scenes||[]).map(x=>({id:x.id,type:x.type,t0:x.t0,t1:x.t1}));
 fs.writeFileSync(path.join(out,REP),JSON.stringify(rep,null,1));
 if(rep.panel){const bad=Object.entries(rep.panel).filter(([k,v])=>Object.keys(v.frame).length>1||Object.keys(v.base).length>1||Object.keys(v.transform).length>1);rep.panelChangedScenes=bad.map(x=>x[0]);console.log('插圖面板外框／底板／縮放變動的鏡：',bad.length?bad.map(x=>x[0]).join(','):'無（全片每幀每鏡固定）')}fs.writeFileSync(path.join(out,REP),JSON.stringify(rep,null,1));
 if(rep.logoGapMin!=null)console.log('片尾四字與 LOGO 最小淨空',rep.logoGapMin,'px；不足 24px 的幀：',(rep.logoOverlap||[]).length);
 console.log('幀數',n,'抽檢',rep.checked,'重疊',rep.overlap.length,'出界',rep.oob.length,'上下留白錯誤',(rep.edge||[]).length,'頂端最大留白',rep.gapTopMax,'底端最大留白',rep.gapBotMax);(rep.edge||[]).slice(0,10).forEach(x=>console.log('留白',x));rep.overlap.slice(0,10).forEach(x=>console.log(x));rep.oob.slice(0,10).forEach(x=>console.log('出界',x))})();
