// 真的操作展示頁：node ui.js <輸出資料夾>（1440 與 390 兩種寬度，每顆鈕都按，驗畫面真的改變）
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../../site/office'),out=process.argv[2];
const T={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png'};
const srv=http.createServer((q,s)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(p)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
 for(const [w,h,n] of [[1440,900,'ui_1440'],[390,844,'ui_390']]){
  const cx=await b.newContext({viewport:{width:w,height:h},deviceScaleFactor:1,hasTouch:w<500});const pg=await cx.newPage();const errs=[];
  pg.on('console',m=>{if(m.type()==='error')errs.push(m.text().slice(0,200))});pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto(`http://localhost:${srv.address().port}/model.html`);await pg.waitForFunction('window.READY',{timeout:90000});await pg.waitForTimeout(1500);
  await pg.screenshot({path:path.join(out,n+'.png')});
  const lay=await pg.evaluate(()=>{const v=document.getElementById('view').getBoundingClientRect(),p=document.getElementById('panel');return {viewH:Math.round(v.height),panelScroll:p.scrollHeight-p.clientHeight,docScroll:document.documentElement.scrollHeight-innerHeight,sw:document.documentElement.scrollWidth}});
  const sig=()=>pg.evaluate(()=>JSON.stringify(['upperArmL','upperArmR','thighL','head'].map(k=>window.stage.char.bones[k].quaternion.toArray().map(v=>+v.toFixed(2)))));
  const res=[];
  for(const k of ['walk','talk','run','sit','look','argue','note','raise','clap','cheer','hit','idle']){
   const before=await sig(), p0=await pg.evaluate(()=>[stage.loco.x,stage.loco.z]);
   await pg.locator(`#acts .chip[data-k="${k}"]`).click();
   await pg.waitForFunction(k=>window.stage.state.action===k,k,{timeout:8000}).catch(()=>{});
   await pg.waitForTimeout(k==='walk'||k==='run'?1800:700);
   const after=await sig(), st=await pg.evaluate(()=>({a:stage.state.action,x:stage.loco.x,z:stage.loco.z,v:stage.loco.v}));
   const on=await pg.evaluate(k=>document.querySelector(`#acts .chip[data-k="${k}"]`).classList.contains('on'),k);
   const moved=Math.hypot(st.x-p0[0],st.z-p0[1]);
   res.push(`${k}:${st.a===k?'已切換':'沒切換'}/${before!==after?'姿勢有變':'沒變'}/${on?'亮':'沒亮'}${k==='walk'||k==='run'?'/位移'+moved.toFixed(2):''}${k==='talk'||k==='sit'?'/停下速度'+st.v.toFixed(2):''}`);
   if(k==='walk') await pg.screenshot({path:path.join(out,n+'_walk.png')});
  }
  const ex=[];for(const k of ['happy','talk','surprised','angry','sad','smug','focus','dizzy','auto']){const b0=await pg.evaluate(()=>stage.char.face.key);await pg.locator(`#exprs .chip[data-k="${k}"]`).click();await pg.waitForTimeout(450);const b1=await pg.evaluate(()=>stage.char.face.key);ex.push(`${k}:${b0!==b1?'臉有變':'沒變'}`);}
  await pg.locator('#modes .chip[data-k="proj"]').click();const m1=await pg.evaluate(()=>stage.char.uniforms.uProj.value);await pg.locator('#modes .chip[data-k="clay"]').click();const m2=await pg.evaluate(()=>stage.char.uniforms.uFlat.value);await pg.locator('#modes .chip[data-k="part"]').click();
  await pg.locator('#lods .chip[data-k="lo"]').click();await pg.waitForTimeout(900);const t1=await pg.evaluate(()=>stage.char.count.tris);await pg.locator('#lods .chip[data-k="hi"]').click();await pg.waitForTimeout(900);const t2=await pg.evaluate(()=>stage.char.count.tris);
  await pg.locator('#opts .chip[data-k="skel"]').click();const sk=await pg.evaluate(()=>stage.state.skel);await pg.locator('#opts .chip[data-k="skel"]').click();
  await pg.locator('#opts .chip[data-k="spin"]').click();const c0=await pg.evaluate(()=>stage.scene&&1);await pg.waitForTimeout(500);await pg.locator('#opts .chip[data-k="spin"]').click();
  const cam0=await pg.evaluate(()=>window.stage.state.t);await pg.mouse.move(w*0.3,h*0.25);await pg.mouse.down();await pg.mouse.move(w*0.3+90,h*0.25+10,{steps:6});await pg.mouse.up();await pg.waitForTimeout(300);
  await pg.screenshot({path:path.join(out,n+'_b.png')});
  console.log(n,JSON.stringify(lay),'\n 動作',res.join(' | '),'\n 表情',ex.join(' | '),`\n 投影${m1} 素模${m2} 面數${t1}/${t2} 骨架${sk}`,'errors:',errs.length,errs.slice(0,3));await cx.close();}
 await b.close();srv.close();});
