// 除錯用：node dbg.js "<在頁面裡執行的運算式>"（頁面已載入 ?shot=1，可用 window.stage）
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../../site/office');const T={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png'};
const srv=http.createServer((q,s)=>{let p=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(p)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});const pg=await b.newPage({viewport:{width:300,height:400}});pg.on('pageerror',e=>console.log('E:',e.message));pg.on('console',m=>console.log('C:',m.text().slice(0,400)));
 await pg.goto(`http://localhost:${srv.address().port}/model.html?shot=1`);await pg.waitForFunction('window.READY',{timeout:90000});
 console.log(JSON.stringify(await pg.evaluate(process.argv[2])));await b.close();srv.close();});
