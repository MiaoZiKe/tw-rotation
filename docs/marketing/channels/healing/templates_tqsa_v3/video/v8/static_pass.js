// 主體靜止段檢查（animation-director 11-16：光點在動不算主體在動）：關掉所有光點／亮帶（window.NOGLINT），逐幀以 1/4 解析度截圖，輸出到資料夾給 check_v8.py 比較
// 用法：node v8/static_pass.js <名> <輸出資料夾>
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const [name,outd]=process.argv.slice(2);fs.rmSync(outd,{recursive:true,force:true});fs.mkdirSync(outd,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:.25});
 await pg.addInitScript(()=>{window.NOGLINT=true});await pg.goto('file://'+path.join(__dirname,'..','html',name+'.html'));await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const n=Math.round(V.dur*V.fps);
 for(let f=0;f<n;f++){await pg.evaluate(t=>window.renderAt(t),f/V.fps);await pg.screenshot({path:path.join(outd,String(f).padStart(5,'0')+'.png')})}
 await b.close();console.log('frames',n)})();
