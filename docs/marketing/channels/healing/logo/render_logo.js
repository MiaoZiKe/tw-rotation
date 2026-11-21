const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const out={};const names=fs.readdirSync('.').filter(x=>x.endsWith('.svg')).map(x=>x.slice(0,-4));
for(const n of names){const wm=n.includes('橫式');const [W,H]=wm?[1400,400]:[512,512];const svg=fs.readFileSync(n+'.svg','utf8');
const pg=await b.newPage({viewport:{width:W,height:H}});await pg.setContent(`<style>body{margin:0}.c{border-radius:50%;overflow:hidden}</style><div id=s style="width:${W}px;height:${H}px">${svg}</div>`);await pg.waitForTimeout(200);
await pg.screenshot({path:n+'.png'});
if(!n.includes('單色')||true){out[n]=await pg.evaluate((wm)=>{const els=[...document.querySelectorAll('svg > g > *, svg > text, svg > g')].filter(e=>e.tagName!='rect');
const rs=[...document.querySelectorAll('svg > g, svg > text')].map(e=>({t:e.tagName,r:e.getBoundingClientRect()}));
if(wm){const g=rs.find(x=>x.t=='g').r,t=rs.find(x=>x.t=='text').r;return {符號右緣:Math.round(g.right),字標左緣:Math.round(t.left),間距:Math.round(t.left-g.right),字標高度:Math.round(t.height),門檻_0點25倍字高:Math.round(t.height*.25),通過:(t.left-g.right)>=t.height*.25&&t.left>=g.right}}
const r=rs.find(x=>x.t=='g').r;const half=Math.max(Math.abs(r.left-256),Math.abs(r.right-256),Math.abs(r.top-256),Math.abs(r.bottom-256));
// 取包住全部圖形的最小方框之半徑（對圓與弧為保守值：方框角在圓外）；圓章直接用半徑
const cx=(r.left+r.right)/2,cy=(r.top+r.bottom)/2;return {外接框左右上下最遠距中心:Math.round(half),安全半徑:204.8,通過:half<=204.8,偏心:[Math.round(cx-256),Math.round(cy-256)]}},wm);}
if(!wm){await pg.evaluate(()=>{document.getElementById('s').className='c'});await pg.screenshot({path:n+'_圓形.png',omitBackground:true});
for(const S of [110,44]){await pg.setViewportSize({width:S,height:S});await pg.evaluate((S)=>{const s=document.querySelector('svg');s.setAttribute('width',S);s.setAttribute('height',S);const d=document.getElementById('s');d.style.cssText=`width:${S}px;height:${S}px;border-radius:50%;overflow:hidden`},S);await pg.screenshot({path:`${n}_${S}圓形.png`,omitBackground:true})}}
await pg.close()}
await b.close();fs.writeFileSync('overlap_report.json',JSON.stringify(out,null,1));const bad=Object.entries(out).filter(([k,v])=>v.通過===false);console.log('檢查',Object.keys(out).length,'張，未通過',bad.length,JSON.stringify(bad))})()
