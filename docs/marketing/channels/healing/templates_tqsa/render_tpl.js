// 出圖＋重疊檢查：各區塊（logo、頁碼、插畫、標題、副標、結尾）的實際範圍兩兩不相交、不出畫面；文字不溢出
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
(async()=>{const tone=process.argv[2];const J=JSON.parse(fs.readFileSync(`jobs_${tone}.json`,'utf8'));const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1350}});
const rep=[];
for(const j of J){await pg.goto('file://'+process.cwd()+'/'+j.html);await pg.evaluate(()=>document.fonts.ready);
 const r=await pg.evaluate(()=>{const o={};document.querySelectorAll('[data-k]').forEach(e=>{let bb=e.getBoundingClientRect();
   if(e.tagName.toLowerCase()==='svg'&&e.classList.contains('ill')){const g=e.getBBox?e.getBBox():null;const m=e.getScreenCTM();if(g&&m){bb={left:m.a*g.x+m.e,top:m.d*g.y+m.f,right:m.a*(g.x+g.width)+m.e,bottom:m.d*(g.y+g.height)+m.f}}}
   if(e.tagName==='DIV'){const rg=document.createRange();rg.selectNodeContents(e);const rr=rg.getBoundingClientRect();bb={left:rr.left,top:rr.top,right:rr.right,bottom:rr.bottom}}
   o[e.dataset.k]={l:bb.left,t:bb.top,r:bb.right,b:bb.bottom}});return o});
 const ks=Object.keys(r);const fails=[];let n=0;
 for(let a=0;a<ks.length;a++){const A=r[ks[a]];n++;if(A.l<0||A.t<0||A.r>1080||A.b>1350)fails.push(ks[a]+' 出畫面');
  for(let c=a+1;c<ks.length;c++){const B=r[ks[c]];n++;if(!(A.r<=B.l||B.r<=A.l||A.b<=B.t||B.b<=A.t))fails.push(ks[a]+'×'+ks[c])}}
 const ill=r.ill;const area=(ill.b-ill.t)*(ill.r-ill.l);
 rep.push({page:j.png,checked:n,fails,ill_ratio:+((r.ill.b-r.ill.t)/1350).toFixed(2)});
 await pg.screenshot({path:j.png});}
fs.writeFileSync(`overlap_report_${tone}.json`,JSON.stringify(rep,null,1));await b.close();
console.log(rep.map(x=>`${x.page} 檢查${x.checked} 失敗${x.fails.length} ${x.fails.join(',')} 插畫高佔比${x.ill_ratio}`).join('\n'))})();
