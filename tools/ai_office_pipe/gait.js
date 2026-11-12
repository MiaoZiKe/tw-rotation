// 步態驗證：node gait.js <輸出資料夾> [walk|run|video|all]
// 1) 一個完整步態週期等間隔 16 格（正側面、正面）拼成分格圖  2) 量測著地腳的世界座標位移、骨盆高度、每格姿勢變化量
// 3) 逐格合成影片（走一段、轉彎、停下；再跑一段）
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path'),cp=require('child_process');
const root=path.resolve(__dirname,'../../site/office'),out=process.argv[2],what=process.argv[3]||'all';
const T={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png'};
const srv=http.createServer((q,s)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(p)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
 const open=async(w,h)=>{const cx=await b.newContext({viewport:{width:w,height:h}});const pg=await cx.newPage();pg.on('pageerror',e=>console.log('E:',e.message));
  await pg.goto(`http://localhost:${srv.address().port}/model.html?shot=1`);await pg.waitForFunction('window.READY',{timeout:90000});return pg;};
 const report={};
 async function cycle(action,name,views){
  const pg=await open(300,400); const dt=1/120;
  const p0=await pg.evaluate(a=>window.stage.set({action:a,t:4,route:[[0,400]],dist:5.2,target:[0,0.85,0]}),action);
  const Tc=await pg.evaluate(()=>window.stage.loco.g.T), sub=Math.round(Tc/16/dt), all=[];
  for(const [vn,az] of views){
   await pg.evaluate(a=>window.stage.set({action:a,t:4,route:[[0,400]]}),action);
   for(let i=0;i<16;i++){ const pr=await pg.evaluate(([dt,n,c])=>window.stage.step(dt,n,c),[dt,sub,{dist:5.2,target:[0,0.85,0],az,el:0.05}]); if(vn===views[0][0]) all.push(...pr);
    await pg.screenshot({path:path.join(out,`_${name}_${vn}_${String(i).padStart(2,'0')}.png`)}); }
   cp.execFileSync('python3',[path.join(__dirname,'sheet.py'),path.join(out,`${name}_cycle_${vn}.png`),'8','1',...Array.from({length:16},(_,i)=>path.join(out,`_${name}_${vn}_${String(i).padStart(2,'0')}.png`))]);
  }
  // 再多模擬兩個週期做量測
  const more=await pg.evaluate(([dt,n])=>window.stage.step(dt,n),[dt,sub*32]); all.push(...more);
  const R={T:Tc,v:all[0].v,steps:all.length,dt};
  for(const n of ['L','R']){ let maxSlip=0,ref=null,kind=null,minY=9,maxDrift=0,stances=0,maxReach=0;
   for(const f of all){ const ft=f.feet[n]; maxReach=Math.max(maxReach,ft.reach||0);
    if(ft.swing){ref=null;kind=null;continue;}
    const k=ft.pitch>=0?'ball':'heel', p=ft[k]; minY=Math.min(minY,ft.ball[1],ft.heel[1]);
    if(kind!==k){ if(ref===null) stances++; ref=p; kind=k; }
    const d=Math.hypot(p[0]-ref[0],p[2]-ref[2]); maxSlip=Math.max(maxSlip,d); }
   R['foot'+n]={stances,maxContactSlip:+maxSlip.toFixed(5),minContactY:+minY.toFixed(4),maxLegReach:+maxReach.toFixed(4)}; }
  const py=all.map(f=>f.pelvisY); R.pelvisY={min:+Math.min(...py).toFixed(4),max:+Math.max(...py).toFixed(4),curve16:Array.from({length:16},(_,i)=>+py[i*sub].toFixed(3))};
  // 每格姿勢變化量（所有骨頭轉動角度的最大值，度／格）
  const ang=(a,b)=>{const d=Math.abs(a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3]*b[3]);return 2*Math.acos(Math.min(1,d))*180/Math.PI};
  const ch=[];for(let i=1;i<all.length;i++){let m=0;for(const k in all[i].quats)m=Math.max(m,ang(all[i].quats[k],all[i-1].quats[k]));ch.push(m);}
  const srt=[...ch].sort((x,y)=>x-y);R.poseChangeDegPerFrame={median:+srt[srt.length>>1].toFixed(2),p99:+srt[Math.floor(srt.length*0.99)].toFixed(2),max:+srt[srt.length-1].toFixed(2)};
  const sp=[];for(let i=1;i<all.length;i++)sp.push(Math.hypot(all[i].x-all[i-1].x,all[i].z-all[i-1].z)/dt);R.speed={min:+Math.min(...sp).toFixed(3),max:+Math.max(...sp).toFixed(3)};
  R.strideLen=+(R.v*Tc).toFixed(3); report[name]=R; await pg.context().close();
  for(const f of fs.readdirSync(out)) if(f.startsWith('_'+name+'_')) fs.unlinkSync(path.join(out,f));
 }
 async function video(name,opts,secs,acts){
  const pg=await open(720,480); const fps=30, dir=path.join(out,'_frames_'+name); fs.mkdirSync(dir,{recursive:true});
  await pg.evaluate(o=>window.stage.set(o),opts); const slips=[];
  for(let i=0;i<secs*fps;i++){ const tt=i/fps; for(const [at,k] of acts) if(Math.abs(tt-at)<0.5/fps) await pg.evaluate(k=>window.stage.act(k),k);
   const pr=await pg.evaluate(([dt,c])=>window.stage.step(dt,2,c),[1/fps/2,opts.cam]); slips.push(...pr);
   await pg.screenshot({path:path.join(dir,String(i).padStart(4,'0')+'.png')}); }
  cp.execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(fps),'-i',path.join(dir,'%04d.png'),'-pix_fmt','yuv420p','-vf','scale=720:480',path.join(out,name+'.mp4')]);
  cp.execFileSync('ffmpeg',['-y','-loglevel','error','-framerate',String(fps),'-i',path.join(dir,'%04d.png'),'-vf','fps=15,scale=480:-1',path.join(out,name+'.gif')]);
  // 整段（含起步、轉彎、停步）的著地腳位移
  let mx=0;for(const n of ['L','R']){let ref=null,kind=null;for(const f of slips){const ft=f.feet[n];if(ft.swing){ref=null;kind=null;continue;}const k=ft.pitch>=0?'ball':'heel',p=ft[k];if(kind!==k){ref=p;kind=k;}mx=Math.max(mx,Math.hypot(p[0]-ref[0],p[2]-ref[2]));}}
  report[name]={frames:secs*fps,maxContactSlipWholeClip:+mx.toFixed(5),endSpeed:slips[slips.length-1].v,endAction:slips[slips.length-1].action};
  const pick=[0.08,0.2,0.32,0.44,0.56,0.68,0.8,0.95].map(f=>path.join(dir,String(Math.floor(f*secs*fps)).padStart(4,'0')+'.png'));
  cp.execFileSync('python3',[path.join(__dirname,'sheet.py'),path.join(out,name+'_frames.png'),'4','0.7',...pick]);
  fs.rmSync(dir,{recursive:true}); await pg.context().close();
 }
 if(what==='walk'||what==='all') await cycle('walk','walk',[['side',Math.PI/2],['front',0]]);
 if(what==='run'||what==='all') await cycle('run','run',[['side',Math.PI/2]]);
 if(what==='video'||what==='all'){
  await video('walk_turn_stop',{action:'walk',t:0,route:[[0,2.4],[2.6,2.4],[2.6,0.2]],routeOnce:true,follow:false,cam:{follow:false,dist:7.6,target:[1.3,0.8,1.2],az:-0.75,el:0.3}},11,[[10.2,'talk']]);
  await video('run_loop',{action:'idle',t:0,follow:false,cam:{follow:false,dist:9.5,target:[0,0.8,0.2],az:0.5,el:0.35}},9,[[0.5,'run'],[6.5,'idle']]);
 }
 fs.writeFileSync(path.join(out,'gait_report.json'),JSON.stringify(report,null,1)); console.log(JSON.stringify(report,null,1));
 await b.close();srv.close();});
