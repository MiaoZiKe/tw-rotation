// CaffAIne 專業版：產出 8 方向全部檔案＋重疊檢查圖層
// 用法：node build.js [P1,P2...]
const { chromium } = require('playwright');
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');
const LAYERS=process.env.CF_LAYERS||path.join(ROOT,'src','_layers');
const LIB=fs.readFileSync(path.join(__dirname,'lib.js'),'utf8');
(async()=>{
 const br=await chromium.launch();const lp=await br.newPage();await lp.setContent('<html><body></body></html>');await lp.addScriptTag({content:LIB});
 await lp.evaluate(()=>document.fonts.ready);
 const rp=await br.newPage();
 const png=async(svg,f,w,h)=>{await rp.setViewportSize({width:w,height:h});
  await rp.setContent(`<html><head><style>html,body{margin:0;background:transparent}</style></head><body>${svg.replace('<svg ',`<svg style="display:block;width:${w}px;height:${h}px" `)}</body></html>`);
  await rp.evaluate(()=>document.fonts.ready);await rp.screenshot({path:f,omitBackground:true,clip:{x:0,y:0,width:w,height:h}});};
 const dims=s=>{const m=s.match(/viewBox="0 0 (\d+) (\d+)"/);return [+m[1],+m[2]];};
 // 圖層：只顯示一個 data-el，其餘隱藏（背景也隱藏），供 Python 量真實墨水邊界
 const layers=async(svg,tag,man)=>{const [w,h]=dims(svg);const els=[...new Set([...svg.matchAll(/data-el="([^"]+)"/g)].map(m=>m[1]))];man[tag]={w,h,els:{}};
  for(const e of els){const s=svg.replace('</svg>',`<style>svg *{visibility:hidden}[data-el="${e}"],[data-el="${e}"] *{visibility:visible}</style></svg>`);
   const f=path.join(LAYERS,`${tag}__${e}.png`);await png(s,f,w,h);man[tag].els[e]=f;}};
 fs.mkdirSync(LAYERS,{recursive:true});
 const DIRS=await lp.evaluate(()=>CF.DIRS);const only=(process.argv[2]||'').split(',').filter(Boolean);
 const man={};
 for(const D of DIRS){if(only.length&&!only.includes(D.id))continue;const out=path.join(ROOT,D.dir);fs.mkdirSync(out,{recursive:true});
  const put=async(name,svg,pw,ph)=>{fs.writeFileSync(path.join(out,name+'.svg'),svg);const [w,h]=dims(svg);await png(svg,path.join(out,name+(pw?`_${pw}`:'')+'.png'),pw||w,ph||(pw?pw*h/w:h));};
  for(const th of ['light','dark']){
   await put(`icon_${th}`,await lp.evaluate(([d,t])=>CF.icon(d,t),[D.id,th]),1024,1024);
   for(const px of [110,40]){const s=await lp.evaluate(([d,t,p])=>CF.avatar(d,t,p),[D.id,th,px]);fs.writeFileSync(path.join(out,`avatar_${px}_${th}.svg`),s);await png(s,path.join(out,`avatar_${px}_${th}.png`),px,px);}
   const lk=await lp.evaluate(([d,t])=>CF.lockup(d,t),[D.id,th]);await put(`lockup_${th}`,lk);await layers(lk,`${D.id}_lockup_${th}`,man);
  }
  for(const [fn,name] of [['igProfile','app_ig_profile'],['cupMock','app_cup'],['postCover','app_post_cover']]){
   const s=await lp.evaluate(([f,d])=>CF[f](d),[fn,D.id]);await put(name,s);await layers(s,`${D.id}_${name}`,man);}
  if(false&&D.id==='Q6')for(const th of ['light','dark']){const s=await lp.evaluate(t=>CF.storyboard(t),th);await put(`storyboard_${th}`,s);await layers(s,`Q6_storyboard_${th}`,man);}
  console.log('done',D.id);
 }
 const mf=path.join(LAYERS,'manifest.json');const old=fs.existsSync(mf)?JSON.parse(fs.readFileSync(mf)):{};
 fs.writeFileSync(mf,JSON.stringify({...old,...man},null,1));
 fs.writeFileSync(path.join(ROOT,'src','dirs.json'),JSON.stringify(DIRS,null,1));
 await br.close();
})();
