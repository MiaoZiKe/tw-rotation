// 預覽／抽格：node preview_frames.js <名> <輸出資料夾> <t1,t2,...|scene:<id>:<n>[:起:終]> [crop=x,y,w,h]
// 例：node preview_frames.js 20261116_marriage_v4 /tmp/p 0.5,1,1.5   或   scene:s5:6（該鏡前 70% 時間均分 6 格，用於動作序列）
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const [name,outd,spec,crop]=process.argv.slice(2);fs.mkdirSync(outd,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 const errs=[];pg.on('pageerror',e=>errs.push(e.message));
 await pg.goto('file://'+path.join(__dirname,'html',name+'.html'));await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);let ts=[];
 if(spec.startsWith('scene:')){const [,id,n,a,bb]=spec.split(':');const s=V.scenes.find(x=>x.id===id);const t0=s.t0+(+a||0),t1=s.t0+(+bb||(s.t1-s.t0)*.7);for(let i=0;i<+n;i++)ts.push(+(t0+(t1-t0)*i/(n-1)).toFixed(3))}
 else ts=spec.split(',').map(Number);
 const c=crop?crop.split(',').map(Number):null;
 for(const t of ts){await pg.evaluate(t=>window.renderAt(t),t);const f=path.join(outd,'t'+t.toFixed(3).padStart(7,'0')+'.png');await pg.screenshot(c?{path:f,clip:{x:c[0],y:c[1],width:c[2],height:c[3]}}:{path:f})}
 console.log(ts.join(' '),errs.length?'ERR '+errs.join('|'):'');await b.close()})();
