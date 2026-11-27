// 逐幀渲染：node render_video.js <名>  → 幀 PNG（tmp）→ ffmpeg H.264＋靜音 AAC（IG Reels／Threads 相容）→ queue/<名>/video.mp4
// 同時抽 0.5 秒一格做重疊檢查（data-o 元素兩兩不相交、不出邊界、不進 Reels 上 220／下 420 安全區），寫 overlap_report_video.json
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');const {execFileSync}=require('child_process');
const name=process.argv[2];const A=process.argv.slice(3);const arg=k=>{const i=A.indexOf(k);return i<0?null:A[i+1]};
// 2026-11-27 分段渲染（給 .github/workflows/healing_render.yml 多台同時跑；不帶下列參數＝原行為，整片一台渲完）：
//   --from A --to B --seg DIR   只渲第 A～B-1 幀（A 要是 fps/2 的倍數）→ DIR/seg_<A>.mp4（只有畫面、各段獨立 IDR 起頭、自帶時間戳）＋DIR/rep_<tag>.json（該段的重疊檢查）＋含封面幀的段會存 DIR/cover.png
//   --chunk C --job K --jobs J --seg DIR   總幀數依 C 幀切段，這台渲第 K、K+J、K+2J… 段（交錯）
//   --dense N   （2026-11-27 起）除了每 0.5 秒一格，另每 N 幀（建議 2）加查一次「這一幀與上一次抽檢相比位置有動」的元素／文字重疊（只報有動的那邊參與的重疊；不查出界與留白）；不帶＝原行為
//   --assemble DIR   不渲染；把 DIR 的各段 mp4 用 concat 分離器依序接起來、合併各段檢查報告，再配音軌（含 sfx）出 video.mp4／cover.jpg／overlap_report_video.json（與整片版同樣的檔名與內容）
const SEG=arg('--seg'),ASM=arg('--assemble');const html=path.join(__dirname,'html',name+'.html');
const tmp=path.join(__dirname,'tmp',name);
fs.rmSync(tmp,{recursive:true,force:true});fs.mkdirSync(tmp,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+html);await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const out=path.join(__dirname,'..','..','queue',V.queue||name);
 const OUT=V.out||'video.mp4',COVER=V.cover||'video_cover.jpg',REP=V.report||'overlap_report_video.json',CT=V.cover_t==null?4.6:V.cover_t;const n=Math.round(V.dur*V.fps);const HF=Math.round(V.fps/2);let RANGES=[[0,n]];
 if(arg('--from')!=null||arg('--to')!=null)RANGES=[[+(arg('--from')||0),Math.min(n,+(arg('--to')||n))]];
 else if(arg('--chunk')){const C=+arg('--chunk'),J=+(arg('--jobs')||1),K=+(arg('--job')||0);if(C%HF)throw new Error('--chunk 要是 '+HF+' 的倍數');RANGES=[];for(let i=0,a=0;a<n;i++,a+=C)if(i%J===K)RANGES.push([a,Math.min(n,a+C)])}
 if(RANGES.some(r=>r[0]%HF))throw new Error('起始幀要是 '+HF+' 的倍數（抽檢每 0.5 秒一格）');
 if(!SEG&&!ASM&&RANGES.length&&(RANGES[0][0]!==0||RANGES[0][1]!==n))throw new Error('只渲一部分幀要加 --seg DIR');
const DENSE=+(arg('--dense')||0);let PREV={};const rep={frames:n,checked:0,overlap:[],oob:[]};if(DENSE)rep.dense=DENSE,rep.denseChecked=0;if(V.edge60)rep.edge=[];
 for(const [r0,r1] of (ASM?[]:RANGES)){for(let f=r0;f<r1;f++){const t=f/V.fps;await pg.evaluate(t=>window.renderAt(t),t);
  if(V.runtime&&/v[678]/.test(V.runtime)){   // v6：換鏡 5 幀逐幀記錄「舊鏡文字數／新鏡文字數」，同一幀兩邊都 >0＝前後鏡文字同框
   const co=await pg.evaluate(()=>{const ls=[...document.querySelectorAll('#stage .layer[data-L]')];if(!ls.length)return null;const r={old:0,new:0};
    ls.forEach(l=>{const [x0,x1]=l.dataset.clip.split(',').map(Number);l.querySelectorAll('text,div').forEach(e=>{if(e.children.length&&e.tagName!=='text'||!e.textContent.trim())return;let x=e,vis=1;while(x&&x!==l){vis*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}if(vis<.05)return;const b=e.getBoundingClientRect();if(b.right>x0&&b.left<x1)r[l.dataset.L]++})});return r});
   if(co){(rep.transitionFrames=rep.transitionFrames||[]).push({t:+t.toFixed(3),old:co.old,new:co.new});if(co.old>0&&co.new>0)(rep.coText=rep.coText||[]).push(t.toFixed(3)+'s')}}
  if(V.runtime&&/v[5678]/.test(V.runtime)){   // v5：片尾 LOGO 圖形與四字逐幀淨空（≥24px；LOGO 框外加 22px 描邊）
   const gp=await pg.evaluate(()=>{const l=document.querySelector('#stage [data-chk=logo]'),cs=[...document.querySelectorAll('#stage [data-chk=char]')];if(!l||!cs.length)return null;
    const lb=l.getBoundingClientRect(),res=[];cs.forEach((c,i)=>{let x=c,vis=1;while(x&&x!==document.body){vis*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}if(vis<.3)return;const b=c.getBoundingClientRect();
     const ox=Math.min(lb.right+22,b.right)-Math.max(lb.left-22,b.left),gap=b.top-(lb.bottom+22);res.push({i,gap:+gap.toFixed(1),ox:+ox.toFixed(1)})});return res});
   if(gp)gp.forEach(r=>{(rep.logoGap=rep.logoGap||[]).push({t:+t.toFixed(3),i:r.i,gap:r.gap});rep.logoGapMin=Math.min(rep.logoGapMin==null?1e9:rep.logoGapMin,r.gap);if(r.gap<24)(rep.logoOverlap=rep.logoOverlap||[]).push(t.toFixed(3)+'s 字'+r.i+' 離雲 '+r.gap+'px')})}
  if(V.runtime&&/v[45678]/.test(V.runtime)){   // v4：插圖面板外框尺寸與面板底板尺寸逐幀記錄（同一鏡內只准一組＝沒有縮放、沒有平移）
   const q=await pg.evaluate(()=>{const e=document.querySelector('#stage [data-o=illus]');if(!e)return null;const r=e.getBoundingClientRect(),b=e.querySelector('svg g > rect'),br=b?b.getBoundingClientRect():null,g=e.querySelector('svg > g');return{o:[r.left,r.top,r.width,r.height].map(x=>+x.toFixed(2)).join(','),b:br?[br.left,br.top,br.width,br.height].map(x=>+x.toFixed(2)).join(','):'',tf:g?(g.getAttribute('transform')||''):''}});
   if(q){const sc=V.scenes.find(x=>t>=x.t0&&t<x.t1)||V.scenes[V.scenes.length-1];const m=(rep.panel=rep.panel||{});const r=(m[sc.id]=m[sc.id]||{frame:{},base:{},transform:{}});r.frame[q.o]=(r.frame[q.o]||0)+1;r.base[q.b]=(r.base[q.b]||0)+1;r.transform[q.tf||'（無）']=(r.transform[q.tf||'（無）']||0)+1}}
  await pg.screenshot({path:path.join(tmp,String(f).padStart(5,'0')+'.png')});
  const FULL=f%HF===0,DN=!FULL&&DENSE>0&&f%DENSE===0;if(FULL||DN){if(FULL)rep.checked++;else rep.denseChecked++;
   const r=await pg.evaluate(([E,PV,DN])=>{const POS={};const els=[...document.querySelectorAll('[data-o]')].filter(e=>{let x=e;while(x&&x!==document.body){if(parseFloat(getComputedStyle(x).opacity)<0.02)return false;x=x.parentElement}return true}).map(e=>{const q=e.getBoundingClientRect();return{o:e.dataset.o,x:q.left,y:q.top,r:q.right,b:q.bottom}});els.forEach((e,i)=>{const k='o'+i+e.o,p=PV[k];POS[k]=[e.x,e.y];e.mv=!!DN&&(!p||Math.abs(p[0]-e.x)>.5||Math.abs(p[1]-e.y)>.5)});
    const ov=[],oob=[],ws=[];
    // v1：Reels 安全區（上 220／下 420）。v2（V.edge60）：2026-11-15 Andy「紅框處還有空間」→ 上下留白各 ≤60px、字幕卡下緣 ≤1700、1700 以下只放出處與頁尾帶
    const Y0=E?40:220,Y1=E?1880:1500;
    if(E&&els.length&&!DN){const top=Math.min(...els.map(e=>e.y)),bot=1920-Math.max(...els.map(e=>e.b));if(top>60)ws.push('頂端留白 '+Math.round(top)+'px');if(bot>60)ws.push('底端留白 '+Math.round(bot)+'px');
     els.forEach(e=>{if(e.b>1700&&!['src','foot'].includes(e.o))ws.push(e.o+' 下緣 '+Math.round(e.b)+'>1700')});ws.top=top;ws.bot=bot}
    // v3 起：小字檢查。v5 修正：舊版只看 CSS font-size，漏掉被 svg 縮放的字；改用「字級 × 實際螢幕縮放」（svg 取 getScreenCTM），且只量完全可見（不透明度 ≥.9）的字
    if(E&&!DN){[...document.querySelectorAll('#stage text, #stage div')].forEach(e=>{if(!e.textContent.trim()||e.children.length&&e.tagName!=='text'||e.closest('clipPath'))return;let x=e,vis=1;while(x&&x!==document.body){vis*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}
     let fs=parseFloat(getComputedStyle(e).fontSize);if(e.tagName==='text'&&e.getScreenCTM){const m=e.getScreenCTM();fs*=Math.hypot(m.a,m.b)}
     if(vis>=.9&&fs<29.5&&!e.closest('[data-x]'))ws.push('小字 '+fs.toFixed(1)+'px「'+e.textContent.trim().slice(0,8)+'」')})}
    // v9：文字壓文字（2026-11-17 審片：註腳被標籤壓住、容器級檢查抓不到）——任兩個可見文字元素的外框相交即算重疊（外框上下各縮 12%、左右縮 2px 去掉字體留白），寫成「txt:「甲」×「乙」」
    try{const tx=[...document.querySelectorAll('#stage text, #stage div.cap')].filter(e=>{if(!e.textContent.trim()||e.closest('clipPath')||e.closest('defs')||e.querySelector('text'))return false;let x=e,v=1;while(x&&x!==document.body){v*=parseFloat(getComputedStyle(x).opacity);x=x.parentElement}return v>=.3}).map(e=>{const q=e.getBoundingClientRect(),h=q.bottom-q.top;let o={t:e.textContent.trim().slice(0,10),x:q.left+2,r:q.right-2,y:q.top+h*.12,b:q.bottom-h*.12};const cg=e.closest('[data-cb]'),cr=cg&&document.getElementById(cg.getAttribute('data-cb'));if(cr){const k=cr.getBoundingClientRect();o.x=Math.max(o.x,k.left);o.r=Math.min(o.r,k.right);o.y=Math.max(o.y,k.top);o.b=Math.min(o.b,k.bottom);if(o.b<=o.y)o.r=o.x}POS['t'+e.textContent.trim().slice(0,10)+Math.round(q.width)]=[o.x,o.y];const pp=PV['t'+e.textContent.trim().slice(0,10)+Math.round(q.width)];o.mv=!!DN&&(!pp||Math.abs(pp[0]-o.x)>.5||Math.abs(pp[1]-o.y)>.5);return o});   // 2026-11-22：翻牌數字只算牌面內可見部分（被牌面裁掉的上下一位不算重疊）
     for(let i=0;i<tx.length;i++)for(let j=i+1;j<tx.length;j++){const a=tx[i],c=tx[j];if(a.r<=a.x||c.r<=c.x)continue;if((!DN||a.mv||c.mv)&&!(a.r<=c.x||c.r<=a.x||a.b<=c.y||c.b<=a.y))ov.push('txt:「'+a.t+'」×「'+c.t+'」')}}catch(err){}
    for(let i=0;i<els.length;i++){const a=els[i];if(!DN&&(a.x<90||a.r>990||a.y<Y0||a.b>Y1))oob.push(a.o);for(let j=i+1;j<els.length;j++){const c=els[j];if((!DN||a.mv||c.mv)&&!(a.r<=c.x||c.r<=a.x||a.b<=c.y||c.b<=a.y))ov.push(a.o+'×'+c.o)}}return{ov,oob,ws,top:ws.top,bot:ws.bot,POS}},[!!V.edge60,PREV,DN]);PREV=r.POS;
   r.ov.forEach(x=>rep.overlap.push(t.toFixed(FULL?1:3)+'s '+x+(FULL?'':'（逐幀）')));r.oob.forEach(x=>rep.oob.push(t.toFixed(1)+'s '+x));
   if(V.edge60&&FULL){(rep.edge=rep.edge||[]).push(...r.ws.map(x=>t.toFixed(1)+'s '+x));rep.gapTopMax=Math.max(rep.gapTopMax||0,r.top);rep.gapBotMax=Math.max(rep.gapBotMax||0,r.bot)}}}
  if(SEG){fs.mkdirSync(SEG,{recursive:true});const P5=x=>String(x).padStart(5,'0')+'.png';
   execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(V.fps),'-start_number',String(r0),'-i',path.join(tmp,'%05d.png'),'-frames:v',String(r1-r0),'-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-crf','20','-r',String(V.fps),'-f','mp4',path.join(SEG,'seg_'+String(r0).padStart(6,'0')+'.mp4')]);
   const ci=Math.round(CT*V.fps);if(ci>=r0&&ci<r1)fs.copyFileSync(path.join(tmp,P5(ci)),path.join(SEG,'cover.png'));
   for(let f=r0;f<r1;f++)fs.rmSync(path.join(tmp,P5(f)),{force:true})}}
 await b.close();
 if(SEG){fs.mkdirSync(SEG,{recursive:true});fs.writeFileSync(path.join(SEG,'rep_'+(arg('--tag')||RANGES.map(r=>r[0]).join('_'))+'.json'),JSON.stringify(rep));console.log('分段完成',RANGES.map(r=>r.join('-')).join(','),'抽檢',rep.checked,'重疊',rep.overlap.length,'出界',rep.oob.length);return}
 let ALLH=null;
 if(ASM){   // 接段：各段 mp4 依幀序用 concat 分離器接起（各段獨立 IDR）＋合併各段檢查報告
  // 2026-11-27 修卡頓：舊版各段輸出裸 h264（含 B 幀）再 cat 接起來、-f h264 -c:v copy 封裝 → 裸流沒有時間戳，封裝時 PTS 照解碼順序配，
  //   B 幀顯示順序整片錯亂（外食片 1530 幀有 673 幀 PTS 倒退、還掉 2 幀）＝播放器前後跳格「卡卡」。改成每段 mp4（自帶 PTS/DTS）＋ffmpeg concat 分離器 -c copy 接段。
  const segs=fs.readdirSync(ASM).filter(x=>/^seg_\d+\.mp4$/.test(x)).sort();ALLH=path.join(ASM,'concat.txt');
  if(fs.readdirSync(ASM).some(x=>/^seg_\d+\.h264$/.test(x)))throw new Error('接段：看到舊格式 seg_*.h264（時間戳會錯亂），請用新版 render_video.js 重渲各段');
  fs.writeFileSync(ALLH,segs.map(x=>"file '"+path.join(ASM,x).replace(/'/g,"'\\''")+"'").join('\n')+'\n');
  const reps=fs.readdirSync(ASM).filter(x=>/^rep_.*\.json$/.test(x)).map(x=>JSON.parse(fs.readFileSync(path.join(ASM,x),'utf8')));
  const tt=x=>parseFloat(typeof x==='string'?x:x.t);
  for(const r of reps){rep.checked+=r.checked;if(r.dense){rep.dense=r.dense;rep.denseChecked=(rep.denseChecked||0)+(r.denseChecked||0)}['overlap','oob','edge','coText','transitionFrames','logoGap','logoOverlap'].forEach(k=>{if(r[k]){rep[k]=(rep[k]||[]).concat(r[k])}});
   if(r.gapTopMax!=null)rep.gapTopMax=Math.max(rep.gapTopMax||0,r.gapTopMax);if(r.gapBotMax!=null)rep.gapBotMax=Math.max(rep.gapBotMax||0,r.gapBotMax);
   if(r.logoGapMin!=null)rep.logoGapMin=Math.min(rep.logoGapMin==null?1e9:rep.logoGapMin,r.logoGapMin);
   if(r.panel){rep.panel=rep.panel||{};for(const [sid,v] of Object.entries(r.panel)){const d=(rep.panel[sid]=rep.panel[sid]||{frame:{},base:{},transform:{}});['frame','base','transform'].forEach(k=>{for(const [kk,c] of Object.entries(v[k]))d[k][kk]=(d[k][kk]||0)+c})}}}
  ['overlap','oob','edge','coText','transitionFrames','logoGap','logoOverlap'].forEach(k=>{if(rep[k])rep[k].sort((a,c)=>tt(a)-tt(c))});
  if(rep.checked!==Math.ceil(n/HF))throw new Error('接段：抽檢格數 '+rep.checked+' ≠ 應有 '+Math.ceil(n/HF)+'，有段漏掉');
  const sz=segs.reduce((a,x)=>a+fs.statSync(path.join(ASM,x)).size,0);console.log('接段：',segs.length,'段 mp4',sz,'bytes，幀數',n)}
 // 有旁白音檔（segments.json 的 audio）就用旁白；沒有就放靜音音軌（相容性）
 let AIN=V.audio&&fs.existsSync(V.audio)?['-i',V.audio]:['-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100'];
 // v3：音效（video_runtime_v3.js 的 sfxEvents）＋旁白 → sfx_v3.py 合成、限幅、量片尾響度與開頭起音 → AAC，直接接進影片
 if(V.sfx){const b2=await chromium.launch();const p2=await b2.newPage();await p2.goto('file://'+html);await p2.waitForTimeout(300);
  const ev=await p2.evaluate(()=>window.sfxEvents());await b2.close();const evp=path.join(tmp,'sfx_events.json');fs.writeFileSync(evp,JSON.stringify(ev));
  const ot=(V.scenes.find(x=>x.type==='outro')||{t0:V.dur}).t0,am=path.join(tmp,'audio.m4a'),base=OUT.replace(/\.mp4$/,'');
  execFileSync('python3',[path.join(__dirname,'sfx_v3.py'),evp,String(n/V.fps),String(ot),am,path.join(out,base+'_audio.json'),V.audio&&fs.existsSync(V.audio)?V.audio:'',path.join(out,base+'_outro_sfx.mp3')],{stdio:'inherit',env:Object.assign({},process.env,{OUTRO_LUFS:String(V.outro_lufs||-11.5)})});
  AIN=['-i',am]}
 execFileSync('ffmpeg',['-y','-loglevel','error',...(ASM?['-f','concat','-safe','0','-i',ALLH]:['-framerate',String(V.fps),'-i',path.join(tmp,'%05d.png')]),...AIN,
  '-t',String(n/V.fps),...(ASM?['-c:v','copy']:['-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-crf','20','-r',String(V.fps)]),...(V.sfx?['-c:a','copy']:['-c:a','aac','-b:a','128k']),'-movflags','+faststart',path.join(out,OUT)]);
 {const pts=execFileSync('ffprobe',['-v','error','-select_streams','v','-show_entries','frame=pts_time','-of','csv=p=0',path.join(out,OUT)]).toString().split('\n').map(x=>parseFloat(x)).filter(x=>!isNaN(x));let bad=0;for(let i=1;i<pts.length;i++)if(pts[i]<=pts[i-1])bad++;
  console.log('時間戳檢查：幀數',pts.length,'／應有',n,'；PTS 倒退或重複',bad);if(bad||pts.length!==n)throw new Error('成品時間戳錯亂（倒退 '+bad+'、幀數 '+pts.length+'≠'+n+'），播放會卡頓')}
 execFileSync('ffmpeg',['-y','-loglevel','error','-i',ASM?path.join(ASM,'cover.png'):path.join(tmp,String(Math.round(CT*V.fps)).padStart(5,'0')+'.png'),'-q:v','3',path.join(out,COVER)]);
 rep.dur=n/V.fps;rep.timing=V.timing||'default';rep.scenes=(V.scenes||[]).map(x=>({id:x.id,type:x.type,t0:x.t0,t1:x.t1}));
 fs.writeFileSync(path.join(out,REP),JSON.stringify(rep,null,1));
 if(rep.panel){const bad=Object.entries(rep.panel).filter(([k,v])=>Object.keys(v.frame).length>1||Object.keys(v.base).length>1||Object.keys(v.transform).length>1);rep.panelChangedScenes=bad.map(x=>x[0]);console.log('插圖面板外框／底板／縮放變動的鏡：',bad.length?bad.map(x=>x[0]).join(','):'無（全片每幀每鏡固定）')}fs.writeFileSync(path.join(out,REP),JSON.stringify(rep,null,1));
 console.log('換鏡逐幀（舊鏡文字／新鏡文字同框的幀數）：',(rep.coText||[]).length,'；記錄幀數',(rep.transitionFrames||[]).length);
 if(rep.logoGapMin!=null)console.log('片尾四字與 LOGO 最小淨空',rep.logoGapMin,'px；不足 24px 的幀：',(rep.logoOverlap||[]).length);
 console.log('幀數',n,'抽檢',rep.checked,'重疊',rep.overlap.length,'出界',rep.oob.length,'上下留白錯誤',(rep.edge||[]).length,'頂端最大留白',rep.gapTopMax,'底端最大留白',rep.gapBotMax);(rep.edge||[]).slice(0,10).forEach(x=>console.log('留白',x));rep.overlap.slice(0,10).forEach(x=>console.log(x));rep.oob.slice(0,10).forEach(x=>console.log('出界',x))})();
