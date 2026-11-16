// 強調淨空量測用截圖：node v8/em_shots.js <名> <輸出資料夾>；每鏡在強調落定後（t0+2.3 秒，短鏡取 t1−0.1）各截三張：A 原圖、B 隱藏強調、C 隱藏該鏡所有元素（只剩背景）
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const [name,outd]=process.argv.slice(2);fs.mkdirSync(outd,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+path.join(__dirname,'..','html',name+'.html'));await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const res=[];
 for(const s of V.scenes){if(s.type==='outro')continue;const t=Math.min(s.t0+2.3,s.t1-.1);
  await pg.evaluate(t=>window.renderAt(t),t);
  const n=await pg.evaluate(()=>document.querySelectorAll('#stage [data-em]').length);if(!n)continue;
  await pg.screenshot({path:path.join(outd,s.id+'_A.png')});
  await pg.evaluate(()=>document.querySelectorAll('#stage [data-em]').forEach(e=>e.style.visibility='hidden'));await pg.screenshot({path:path.join(outd,s.id+'_B.png')});
  await pg.evaluate(()=>document.querySelectorAll('#stage [data-o], #logo').forEach(e=>e.style.visibility='hidden'));await pg.screenshot({path:path.join(outd,s.id+'_C.png')});
  res.push({id:s.id,t:+t.toFixed(2)})}
 fs.writeFileSync(path.join(outd,'shots.json'),JSON.stringify(res));await b.close()})();
