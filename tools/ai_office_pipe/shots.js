// 用法：node shots.js <shots.json> <outdir>   shots.json = [{name,w,h,dpr,opts}]
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root='/home/user/tw-rotation/site/office';const shots=JSON.parse(fs.readFileSync(process.argv[2]));const out=process.argv[3];
const T={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png','.css':'text/css'};
const srv=http.createServer((q,s)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(p)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
 let pg=null,key='';
 for(const s of shots){const k=`${s.w||520}x${s.h||640}x${s.dpr||1}`;
  if(k!==key){ if(pg) await pg.close(); const cx=await b.newContext({viewport:{width:s.w||520,height:s.h||640},deviceScaleFactor:s.dpr||1}); pg=await cx.newPage(); pg.on('console',m=>{if(m.type()==='error'||m.type()==='warning')console.log('C:',m.text().slice(0,300))});pg.on('pageerror',e=>console.log('E:',e.message));
   await pg.goto(`http://localhost:${srv.address().port}/model.html?shot=1`);await pg.waitForFunction('window.READY',{timeout:90000});key=k;}
  await pg.evaluate(o=>window.stage.set(o),s.opts||{}); await pg.screenshot({path:path.join(out,s.name+'.png')});}
 await b.close();srv.close();console.log('ok',shots.length)});
