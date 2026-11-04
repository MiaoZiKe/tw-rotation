// 產生 S1/S2/S3 各 4 張並做版面檢查。node render_scifi.js
const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');
const {build,THEMES}=require('./gen_scifi.js');
// 版面算完後：星點避開文字與面板（星點屬背景層，不得出現在文字或面板上）
const PRUNE=`()=>{const tr=[];const wk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=wk.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('style,svg'))continue;const r=document.createRange();r.selectNodeContents(n);for(const q of r.getClientRects())if(q.width>0)tr.push([q.left-12,q.top-12,q.right+12,q.bottom+12])}
document.querySelectorAll('.card,.tw,.ph,.badge,.tag,.pill,.disc').forEach(e=>{const q=e.getBoundingClientRect();tr.push([q.left-10,q.top-10,q.right+10,q.bottom+10])});
let rm=0;document.querySelectorAll('.st,.st2').forEach(e=>{const q=e.getBoundingClientRect();if(tr.some(t=>q.left<t[2]&&q.right>t[0]&&q.top<t[3]&&q.bottom>t[1])){e.remove();rm++}});return rm}`;
const CHECK=`(A)=>{const BASE=A[0],HD=A[1];const els=[...document.querySelectorAll('[data-o]')].map(e=>{const r=e.getBoundingClientRect();return {o:e.dataset.o,inn:e.dataset.in||'',x:r.left,y:r.top,w:r.right,h:r.bottom}});
const ov=[],gap=[],clip=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],c=els[j];if(a.inn===c.o||c.inn===a.o)continue;
const g=Math.max(Math.max(a.x-c.w,c.x-a.w),Math.max(a.y-c.h,c.y-a.h));if(g<0)ov.push(a.o+'×'+c.o);else if(g<24)gap.push(a.o+'×'+c.o+' '+Math.round(g))}
const oob=els.filter(e=>e.x<0||e.y<0||e.w>1080||e.h>1350).map(e=>e.o);
document.querySelectorAll('[data-o],[data-o] *').forEach(e=>{const cs=getComputedStyle(e);if(cs.display==='inline'||e.tagName==='TABLE'||e.tagName==='svg'||e.closest('svg'))return;if(e.clientWidth>0&&e.scrollWidth>e.clientWidth+2)clip.push('寬:'+(e.dataset.o||e.className||e.tagName));if(e.clientHeight>0&&e.scrollHeight>e.clientHeight+2&&e.dataset.o)clip.push('高:'+e.dataset.o)});
const tr=[];const wk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=wk.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('style,svg'))continue;const r=document.createRange();r.selectNodeContents(n);for(const q of r.getClientRects())if(q.width>0)tr.push({x:q.left,y:q.top,w:q.right,h:q.bottom,t:n.textContent.trim().slice(0,6)})}
const side=tr.filter(t=>t.x<62||t.w>1018).map(t=>'邊距:'+t.t);
// 裝飾穿過文字：沿線／圓／路徑取樣點，點落在文字框（外擴 3px）內即算
const dcx=[];document.querySelectorAll('.dc').forEach(d=>{let pts=[];const m=d.getScreenCTM();
 if(d.getTotalLength){const L=d.getTotalLength();const k=Math.max(2,Math.ceil(L/4));for(let i=0;i<=k;i++){const p=d.getPointAtLength(L*i/k);pts.push([m.a*p.x+m.c*p.y+m.e,m.b*p.x+m.d*p.y+m.f])}}
 else{const q=d.getBoundingClientRect();pts=[[q.left,q.top],[q.right,q.bottom]]}
 const sw=parseFloat(d.getAttribute('stroke-width')||0)/2;
 for(const t of tr){if(pts.some(p=>p[0]>t.x-3-sw&&p[0]<t.w+3+sw&&p[1]>t.y-3-sw&&p[1]<t.h+3+sw)){dcx.push(t.t+'×'+d.tagName);break}}});

// 裝飾疊裝飾：不同群組（刻度尺／儀表／側刻度／底部／地平線…）的取樣點距離 <2.5px 即算
const gp={};document.querySelectorAll('.dc:not(.st)').forEach(d=>{const g=d.closest('[data-g]');if(!g)return;const m=d.getScreenCTM();const L=d.getTotalLength?d.getTotalLength():0;const k=Math.max(1,Math.ceil(L/3));const a=gp[g.dataset.g]=gp[g.dataset.g]||[];for(let i=0;i<=k;i++){const p=L?d.getPointAtLength(L*i/k):{x:0,y:0};a.push([m.a*p.x+m.c*p.y+m.e,m.b*p.x+m.d*p.y+m.f])}});
const dd=[];const ks=Object.keys(gp);for(let i=0;i<ks.length;i++)for(let j=i+1;j<ks.length;j++){let hit=false;for(const p of gp[ks[i]]){for(const q of gp[ks[j]]){if(Math.abs(p[0]-q[0])<2.5&&Math.abs(p[1]-q[1])<2.5){hit=true;break}}if(hit)break}if(hit)dd.push(ks[i]+'×'+ks[j])}
const small=[...document.querySelectorAll('[data-o],[data-o] *')].filter(e=>[...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<28).map(e=>e.textContent.slice(0,8));
const minDisc=Math.min(...[...document.querySelectorAll('.disc')].map(e=>parseFloat(getComputedStyle(e).fontSize)));
const badge=Math.min(...[...document.querySelectorAll('.badge')].map(e=>parseFloat(getComputedStyle(e).fontSize)));
// 對比：文字色與逐層疊合的背景色
const P=s=>{const m=s.match(/[\\d.]+/g).map(Number);return {r:m[0],g:m[1],b:m[2],a:m.length>3?m[3]:1}};
const lum=c=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b)};
const over=(f,b)=>({r:f.r*f.a+b.r*(1-f.a),g:f.g*f.a+b.g*(1-f.a),b:f.b*f.a+b.b*(1-f.a),a:1});
const hex=h=>({r:parseInt(h.slice(1,3),16),g:parseInt(h.slice(3,5),16),b:parseInt(h.slice(5,7),16),a:1});
let minC=99;const low=[];
document.querySelectorAll('[data-o],[data-o] *').forEach(e=>{if(!([...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim())))return;
 const chain=[];for(let p=e;p&&p!==document.documentElement;p=p.parentElement)chain.push(p);
 let bg=hex(BASE);for(let i=chain.length-1;i>=0;i--){const c=P(getComputedStyle(chain[i]).backgroundColor);if(c.a>0)bg=over(c,bg);if(chain[i].classList.contains('hd')&&HD)bg=hex(HD)}
 const fg=over(P(getComputedStyle(e).color),bg);const l1=lum(fg),l2=lum(bg);const cr=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
 if(cr<minC)minC=cr;if(cr<4.5)low.push(e.textContent.trim().slice(0,8)+' '+cr.toFixed(1))});
return {n:els.length,overlap:ov,gap24:gap,oob,clip,side,decoOnText:dcx,decoOnDeco:dd,minDisc,badge,small,minContrast:+minC.toFixed(2),lowContrast:low}}`;
(async()=>{const b=await chromium.launch();const res={};
for(const v of ['s1','s2','s3']){const {css,pages}=build(v);const nm=v.toUpperCase();
 for(let i=0;i<4;i++){const f=`html/${nm}_${i+1}.html`;
  fs.writeFileSync(f,`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${css}</style><body>${pages[i]}</body></html>`);
  const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+process.cwd()+'/'+f);await pg.waitForTimeout(250);
  const rm=await pg.evaluate(eval(PRUNE));
  await pg.screenshot({path:`png/${nm}_${i+1}.png`});
  const r=await pg.evaluate(eval(CHECK),[THEMES[v].base,v==='s3'?'#0C1D33':'']);r.starsPruned=rm;res[`${nm}_${i+1}`]=r;await pg.close()}}
await b.close();fs.writeFileSync('check_result.json',JSON.stringify(res,null,1));
for(const k in res){const r=res[k];const bad=[...r.overlap,...r.gap24.map(x=>'間距'+x),...r.oob.map(x=>'越界'+x),...r.clip.filter(x=>x!=='高:標題').map(x=>'溢出'+x),...r.side,...r.decoOnText.map(x=>'穿字'+x),...r.decoOnDeco.map(x=>'疊裝飾'+x),...r.small.map(x=>'小字'+x)];
 console.log(k,bad.length?bad.join(' | '):'OK',' 對比最低',r.minContrast,r.lowContrast.join(','),' 揭露',r.minDisc,'標章',r.badge,'星點移除',r.starsPruned)}})()
