const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root='/home/user/tw-rotation/site/office',out=process.argv[2];
const T={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png'};
const srv=http.createServer((q,s)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(p)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
 for(const [w,h,n] of [[1440,900,'ui_1440'],[390,844,'ui_390']]){
  const cx=await b.newContext({viewport:{width:w,height:h},deviceScaleFactor:1,hasTouch:w<500});const pg=await cx.newPage();const errs=[];
  pg.on('console',m=>{if(m.type()==='error')errs.push(m.text().slice(0,200))});pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto(`http://localhost:${srv.address().port}/model.html`);await pg.waitForFunction('window.READY',{timeout:90000});await pg.waitForTimeout(1500);
  await pg.screenshot({path:path.join(out,n+'.png')});
  // 真的按：每個動作鈕按下去，骨頭姿勢要變、鈕要亮
  const res=[];
  for(const k of ['walk','run','sit','talk','argue','note','raise','clap','cheer','hit','idle']){
   const before=await pg.evaluate(()=>JSON.stringify(window.stage.char.bones.upperArmL.quaternion.toArray().map(v=>+v.toFixed(3))));
   await pg.click(`#acts .chip[data-k="${k}"]`);await pg.waitForTimeout(250);
   const mid=await pg.evaluate(()=>window.stage.char.blend);
   await pg.waitForTimeout(650);
   const after=await pg.evaluate(()=>JSON.stringify(window.stage.char.bones.upperArmL.quaternion.toArray().map(v=>+v.toFixed(3))));
   const on=await pg.evaluate(k=>document.querySelector(`#acts .chip[data-k="${k}"]`).classList.contains('on'),k);
   res.push(`${k}:${before!==after?'姿勢有變':'沒變'}/${on?'亮':'沒亮'}/過渡中${mid.toFixed(2)}`);
   if(k==='walk') await pg.screenshot({path:path.join(out,n+'_blend.png')});
  }
  await pg.click('#exprs .chip[data-k="angry"]');await pg.click('#modes .chip[data-k="proj"]');await pg.click('#lods .chip[data-k="lo"]');await pg.waitForTimeout(800);await pg.click('#opts .chip[data-k="skel"]');
  const st=await pg.evaluate(()=>({expr:stage.state.expr,mode:stage.state.mode,lod:stage.state.lod,tris:stage.char.count.tris,skel:stage.state.skel,info:document.getElementById('info').textContent,sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth}));
  await pg.mouse.move(w*0.3,h*0.3);await pg.mouse.down();await pg.mouse.move(w*0.3+80,h*0.3+10,{steps:5});await pg.mouse.up();await pg.waitForTimeout(300);
  await pg.screenshot({path:path.join(out,n+'_b.png')});
  console.log(n,res.join(' | '),JSON.stringify(st),'errors:',errs.length,errs.slice(0,3));await cx.close();}
 await b.close();srv.close();});
