// 字幕同步抽查：node v8/sync_check.js <名>；從 segments.json 均勻抽 5 段，在「開口後 0.3 秒」與「該段結束前 0.2 秒」讀畫面字幕，確認是這一段的字（多句分段時是其中一句）
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const name=process.argv[2];
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+path.join(__dirname,'..','html',name+'.html'));await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const S=V.scenes.filter(s=>s.voiceAt!=null&&s.type!=='outro');const pick=[0,1,2,3,4].map(i=>S[Math.round(i*(S.length-1)/4)]);const res=[];
 const norm=x=>x.replace(/[，。、；：？！「」（）\s<br>]/g,'');
 for(const s of pick){for(const dt of [s.voiceAt+.3,(s.t1-s.t0)-.2]){const t=s.t0+dt;await pg.evaluate(t=>window.renderAt(t),t);
  const cap=await pg.evaluate(()=>{const e=document.querySelector('#stage .layer:not([data-L]) [data-o=cap]')||document.querySelector('#stage [data-o=cap]');return e?e.innerText:''});
  res.push({id:s.id,t:+t.toFixed(2),seg:s.cap,shown:cap.replace(/\n/g,''),ok:!!cap&&norm(s.cap).includes(norm(cap))})}}
 console.log(JSON.stringify(res,null,0));await b.close()})();
