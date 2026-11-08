// CaffAIne 第二輪：休閒溫和咖啡館風，杯子為主體。純 SVG 向量。
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');
const OUT = path.resolve(__dirname, '..', 'round2', 'final');
const BASE = {
  dark:  { bg:'#3B2A22', fg:'#F6E9D6', mid:'#D9B08C', cup:'#F6E9D6', cs:'stroke="none"', hs:'#F6E9D6', ink:'#D9722A', foam:'#FFF3DF', coffee:'#7A4A33' },
  light: { bg:'#FFF7EA', fg:'#5A3A28', mid:'#C9A27E', cup:'#FFEBD0', cs:'stroke="#5A3A28" stroke-width="7" stroke-linejoin="round"', hs:'#5A3A28', ink:'#D9722A', foam:'#FFF3DF', coffee:'#7A4A33' },
};
const ACC = { caramel:{dark:['#F29A4E','#3B2A22'],light:['#D9722A','#FFF7EA']}, sage:{dark:['#A9CFA0','#3B2A22'],light:['#5E9A68','#FFF7EA']}, honey:{dark:['#F7C94B','#3B2A22'],light:['#C98F12','#FFF7EA']} };
const theme=(th,a='caramel')=>({...BASE[th],ac:ACC[a][th][0],onac:ACC[a][th][1]});
const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif", CJK = "'WenQuanYi Zen Hei','Noto Sans CJK TC',sans-serif";
const S=(c,w=12,x='')=>`fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${x}`;
const serifI=(x,y1,y2,c,w,hw=11)=>`<path d="M${x-hw} ${y1} Q${x} ${y1-2} ${x+hw} ${y1} M${x} ${y1} C${x-1.5} ${(y1+y2)/2-6} ${x+1.5} ${(y1+y2)/2+6} ${x} ${y2} M${x-hw} ${y2} Q${x} ${y2+2} ${x+hw} ${y2}" ${S(c,w)}/>`;
// 外帶杯：梯形杯身＋杯蓋
const TBODY='M52 58 H148 L137 176 Q136 184 128 184 H72 Q64 184 63 176 Z';
const lid=c=>`<path d="M41 42 Q41 30 54 30 H146 Q159 30 159 42 V50 Q159 60 148 60 H52 Q41 60 41 50 Z" fill="${c.mid}"/>`;
const takeaway=(c,band)=>`<path d="${TBODY}" fill="${c.cup}" ${c.cs}/>${band||''}${lid(c)}`;
const bandPoly=(fill)=>`<path d="M56 100 H144 L139.5 146 H60.5 Z" fill="${fill}" stroke="${fill}" stroke-width="6" stroke-linejoin="round"/>`;
const mugHandle=(c)=>`<path d="M136 100 H152 a18 18 0 0 1 0 36 H132" ${S(c.hs,12)}/>`;
const CBODY='M32 90 H132 V118 C132 148 112 168 82 168 C52 168 32 148 32 118 Z';
const stA=(x,y,c,w=9)=>`<path d="M${x} ${y+30} C${x+5} ${y+18} ${x+10} ${y+8} ${x+16} ${y} C${x+22} ${y+8} ${x+27} ${y+18} ${x+31} ${y+30} M${x+6} ${y+19} Q${x+16} ${y+16} ${x+26} ${y+20}" ${S(c,w)}/>`;
const ALL=[
 {id:'r1',name:'杯套寫著AI',kind:'外帶杯',meaning:'外帶杯的杯套直接印著 AI：端著它走，就是帶著一個新知。',
  draw:c=>`<g>${takeaway(c,bandPoly(c.ac))}
   <path d="M74 139 L86.5 108 L99 139 M79 127.5 H94" ${S(c.onac,8)}/>${serifI(114,109,138,c.onac,8,10)}</g>`},
 {id:'r2',name:'手寫杯標AI',kind:'外帶杯',meaning:'咖啡師用麥克筆在杯身寫下的 AI 與一道小波浪底線，像請你喝的第一杯。',
  draw:(c,small)=>`${takeaway(c)}<path d="M70 146 C74 128 80 110 88 98 C94 110 100 128 104 146 M76 128 Q88 124 98 129" ${S(c.ink,9)}/>${serifI(121,99,146,c.ink,9,9)}
   ${small?'':`<path d="M74 165 Q86 159 98 164 T118 163" ${S(c.mid,6)}/>`}`},
 {id:'r3',name:'進度杯套',kind:'外帶杯',meaning:'杯套是一條讀到四分之三的進度條（一杯咖啡的時間，看完一個新知），蒸氣捲成 AI。',
  draw:c=>`<g transform="translate(14 38) scale(.86)">${takeaway(c,bandPoly(c.mid).replace('V','V')+`<rect x="62" y="116" width="76" height="16" rx="8" fill="${c.cup}"/><rect x="62" y="116" width="58" height="16" rx="8" fill="${c.ac}"/>`).replace(/<path d="M41 42[^>]*>/, m=>m)}</g>
   ${stA(64,4,c.ac,8)}${serifI(114,6,36,c.ac,8,9)}`},
 {id:'r4',name:'拉花AI',kind:'陶瓷杯',meaning:'俯視一杯拿鐵，奶泡拉出放大的 AI；沒有外圈，只有奶油色杯盤與杯耳。',
  draw:c=>`<circle cx="90" cy="100" r="82" fill="${c.mid}"/><path d="M148 88 H166 a14 14 0 0 1 0 28 H148" ${S(c.hs,12)}/>
   <circle cx="90" cy="100" r="60" fill="${c.cup}"/><circle cx="90" cy="100" r="50" fill="${c.coffee}"/>
   <path d="M60 124 L77 74 L94 124 M65 110 Q77 106 89 111" ${S(c.foam,10)}/>${serifI(113,77,122,c.foam,10,9)}`},
 {id:'r5',name:'握把成AI',kind:'陶瓷杯',meaning:'馬克杯左側的握把是一個側躺的 A，杯身上立著 I：握把加杯身讀作 AI。',
  draw:c=>`<g transform="translate(19 0)"><rect x="54" y="78" width="100" height="94" rx="24" fill="${c.cup}" ${c.cs}/><ellipse cx="104" cy="82" rx="44" ry="9" fill="${c.coffee}"/>
   <path d="M54 102 L14 128 L54 154 M33 116 V140" ${S(c.ac,12)}/>${serifI(104,104,150,c.ink,13,12)}
   <path d="M88 62 q-9 -11 0 -22 M118 62 q-9 -11 0 -22" ${S(c.mid,7)}/></g>`},
 {id:'r6',name:'蒸氣成AI',kind:'陶瓷杯（備選）',meaning:'陶瓷杯升起的暖暖蒸氣捲成 AI；最單純，但也最通用，列為備選。',
  draw:c=>`<path d="${CBODY}" fill="${c.cup}" ${c.cs}/><path d="M132 102 H148 a17 17 0 0 1 0 34 H128" ${S(c.hs,12)}/><path d="M42 183 H122" ${S(c.mid,8)}/>
   ${stA(36,22,c.ac,10)}${serifI(106,24,54,c.ac,10,10)}`.replace('<path d="M42 183',`<path d="M42 183`)},
 {id:'r7',name:'咖啡因分子（圓潤）',kind:'備選',meaning:'咖啡因雙環結構，補上甲基與氧，線條加粗圓頭；亮色節點是藏在 CaffAIne 裡的 AI。',
  draw:c=>{const r=38,hx=58,hy=108;const hv=a=>[hx+r*Math.cos(a*Math.PI/180),hy+r*Math.sin(a*Math.PI/180)];
   const H=[30,90,150,210,270,330].map(hv);const xe=H[0][0];const pc=xe+0.688*r,R=0.8507*r;
   const P=[0,72,144,216,288].map(a=>[pc+R*Math.cos(a*Math.PI/180),hy+R*Math.sin(a*Math.PI/180)]);
   const poly=p=>p.map((q,i)=>(i?'L':'M')+q[0].toFixed(1)+' '+q[1].toFixed(1)).join(' ')+' Z';
   const ex=(p,a,l)=>[p[0]+l*Math.cos(a*Math.PI/180),p[1]+l*Math.sin(a*Math.PI/180)];
   const arms=[[H[4],270,mid=>c.mid,9],[H[2],150,()=>c.mid,9],[H[3],210,()=>c.mid,9],[H[1],90,()=>c.mid,9]].map(([p,a,f,rr])=>{const e=ex(p,a,24);return `<path d="M${p[0]} ${p[1]} L${e[0]} ${e[1]}" ${S(c.fg,10)}/><circle cx="${e[0]}" cy="${e[1]}" r="${rr+2}" fill="${c.mid}"/>`}).join('');
   return `<g transform="translate(14 -8)"><path d="${poly(H)}" fill="${c.mid}" fill-opacity=".3" stroke="none"/><path d="${poly(P)}" fill="${c.mid}" fill-opacity=".3" stroke="none"/>
   <path d="${poly(H)}" ${S(c.fg,10)}/><path d="${poly(P)}" ${S(c.fg,10)}/>${arms}
   ${[P[1],P[4]].map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="9" fill="${c.fg}"/>`).join('')}<circle cx="${P[0][0]}" cy="${P[0][1]}" r="17" fill="${c.ac}"/></g>`}},
];
const ICONS=ALL.filter(i=>['r1','r2','r4'].includes(i.id));
// 文字標（圓潤：同色圓角描邊）。mode: 'text'(換色加粗) | 'cap'(圓角膠囊)
function wordmark(c,size,m,mode){
  const parts=['Caff','AI','ne'],base=size*.76,sw=size*.04,gap=sw;
  const T=(txt,wt,col,x)=>`<text x="${x.toFixed(1)}" y="${base.toFixed(1)}" font-family="${FONT}" font-weight="${wt}" font-size="${size}" fill="${col}" stroke="${col}" stroke-width="${sw}" stroke-linejoin="round" paint-order="stroke" style="font-feature-settings:'cv08'">${txt}</text>`;
  const w0=m('Caff',600,size),w1=m('AI',800,size),w2=m('ne',600,size);let x=0,out='';
  if(mode==='text'){out+=T('Caff',600,c.fg,x);x+=w0+gap;out+=T('AI',800,c.ac,x);x+=w1+gap;out+=T('ne',600,c.fg,x);x+=w2;return{svg:out,w:x,h:base+size*.02};}
  const pad=size*.13;out+=T('Caff',600,c.fg,x);x+=w0+size*.12;
  out+=`<rect x="${x.toFixed(1)}" y="${(base-size*.76-size*.12).toFixed(1)}" width="${(w1+pad*2).toFixed(1)}" height="${(size*.76+size*.24).toFixed(1)}" rx="${(size*.3).toFixed(1)}" fill="${c.ac}"/>`;
  out+=T('AI',800,c.onac,x+pad);x+=w1+pad*2+size*.08;out+=T('ne',600,c.fg,x);x+=w2;
  return{svg:out,w:x,h:base+size*.12};
}
(async()=>{
  const br=await chromium.launch(),pg=await br.newPage(),mp=await br.newPage();await mp.setContent('<body></body>');
  const meas=async(txt,wt,size,fam=FONT)=>mp.evaluate(([txt,wt,size,fam])=>{const e=document.createElement('span');e.style.cssText=`position:absolute;white-space:pre;font:${wt} ${size}px ${fam};font-feature-settings:'cv08'`;e.textContent=txt;document.body.appendChild(e);const w=e.getBoundingClientRect().width;e.remove();return w;},[txt,wt,size,fam]);
  const cache={};for(const sz of [120,150])for(const wt of [600,800])for(const tx of ['Caff','AI','ne'])cache[`${tx}|${wt}|${sz}`]=await meas(tx,wt,sz);
  const m=(t,w,s)=>cache[`${t}|${w}|${s}`];
  const WRAP=(w,h,bg,inner,rx=0)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${bg?`<rect width="${w}" height="${h}" rx="${rx}" fill="${bg}"/>`:''}${inner}</svg>`;
  const DISP=1.1;const FILT=`<defs><filter id="hd" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="${DISP}"/></filter></defs>`;
  const hand=g=>`${FILT}<g filter="url(#hd)">${g}</g>`;
  const png=async(svg,f,w,h)=>{await pg.setViewportSize({width:w,height:h});await pg.setContent(`<style>html,body{margin:0;background:transparent}</style>${svg.replace('<svg ',`<svg style="display:block;width:${w}px;height:${h}px" `)}`);await pg.screenshot({path:f,omitBackground:true,clip:{x:0,y:0,width:w,height:h}});};
  fs.mkdirSync(path.join(OUT,'wordmark'),{recursive:true});
  for(const a of ['caramel'])for(const th of ['dark','light'])for(const mode of ['text','cap']){
    const c=theme(th,a),wm=wordmark(c,150,m,mode),pad=60,W=Math.ceil(wm.w+pad*2),H=Math.ceil(wm.h+pad*2+10);
    const svg=WRAP(W,H,c.bg,`<g transform="translate(${pad} ${pad})">${wm.svg}</g>`);const f=`wordmark_${mode}_${a}_${th}`;
    fs.writeFileSync(path.join(OUT,'wordmark',f+'.svg'),svg);await png(svg,path.join(OUT,'wordmark',f+'.png'),W,H);}
  const lay=path.join(os.tmpdir(),'cf_layers');fs.mkdirSync(lay,{recursive:true});
  const TAGSZ=40;const tw=(await meas('一杯咖啡的時間，看懂一個 ',400,TAGSZ,CJK))+(await meas('AI',700,TAGSZ))+(await meas(' 新知',400,TAGSZ,CJK));
  for(const ic of ICONS){
    const dir=path.join(OUT,`${ic.id}_${ic.name}`);fs.mkdirSync(dir,{recursive:true});
    for(const th of ['dark','light']){
      const c=theme(th),g=hand(ic.draw(c)),g40=hand(ic.draw(c,true));
      const sc=1024*.66/200,off=(1024-200*sc)/2;
      const sq=WRAP(1024,1024,c.bg,`<g transform="translate(${off} ${off}) scale(${sc})">${g}</g>`,260);
      fs.writeFileSync(path.join(dir,`icon_${th}.svg`),sq);await png(sq,path.join(dir,`icon_${th}_1024.png`),1024,1024);
      for(const D of [110,40]){const s2=D*.74/200,o2=(D-200*s2)/2;
        const av=WRAP(D,D,null,`<circle cx="${D/2}" cy="${D/2}" r="${D/2}" fill="${c.bg}"/><g transform="translate(${o2} ${o2}) scale(${s2})">${D===40?g40:g}</g>`);
        fs.writeFileSync(path.join(dir,`avatar_${D}_${th}.svg`),av);await png(av,path.join(dir,`avatar_${D}_${th}.png`),D,D);}
      for(const [mode,pf,suffix] of [['text','r',''],['cap','rc','_capsule']]){
        const wm=wordmark(c,150,m,mode),icon=360,padX=90,gapX=48,gapV=44,tcap=TAGSZ*.8,blockH=wm.h+gapV+tcap,blockW=Math.max(wm.w,tw);
        const W=Math.ceil(padX*2+icon+gapX+blockW),H=520,iy=(H-icon)/2,ty=(H-blockH)/2,tx=padX+icon+gapX,tagY=ty+wm.h+gapV+tcap*.92;
        const inner=`<g id="gi" transform="translate(${padX} ${iy}) scale(${icon/200})">${g}</g><g id="gw" transform="translate(${tx} ${ty})">${wm.svg}</g>
<g id="gt"><text x="${tx}" y="${tagY.toFixed(1)}" font-family="${CJK}" font-size="${TAGSZ}" fill="${c.fg}" opacity=".92">一杯咖啡的時間，看懂一個 <tspan font-family="${FONT}" font-weight="700" fill="${c.ac}" style="font-feature-settings:'cv08'">AI</tspan> 新知</text></g>`;
        const lk=WRAP(W,H,c.bg,inner);fs.writeFileSync(path.join(dir,`lockup${suffix}_${th}.svg`),lk);await png(lk,path.join(dir,`lockup${suffix}_${th}.png`),W,H);
        await pg.setViewportSize({width:W,height:H});await pg.setContent(`<style>body{margin:0}</style>${lk}`);
        const n=ic.id.slice(1);
        for(const id of ['gi','gw','gt']){await pg.evaluate(([id])=>{for(const k of ['gi','gw','gt'])document.getElementById(k).style.display=k===id?'':'none';document.querySelector('svg>rect').style.display='none';},[id]);await pg.screenshot({path:path.join(lay,`${pf}${n}_${th}_${id}.png`),omitBackground:true,clip:{x:0,y:0,width:W,height:H}});}
      }
    }
  }
  const dirs=ICONS.map(i=>`${i.id}_${i.name}`),rel=(d,f)=>`${d}/${f}`;
  const html=`<!doctype html><meta charset=utf-8><base href="file://${OUT}/">
<style>body{margin:0;background:#F3E6D2;font-family:'WenQuanYi Zen Hei',Inter,sans-serif;color:#4A2F22;padding:40px;width:2400px;box-sizing:border-box}h1{font-size:40px;margin:0 0 20px}
.g{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.c{background:#fff;border-radius:22px;padding:22px}.c h3{margin:0 0 14px;font-size:30px}.av{display:flex;gap:14px;align-items:center;margin-bottom:14px}.c img.l{width:100%;border-radius:14px;display:block;margin-top:12px}</style>
<h1>CaffAIne 定稿候選：R4 拉花 AI／R1 杯套 AI／R2 手寫杯標（焦糖橘、膠囊文字標）</h1><div class=g>
${ICONS.map((ic,i)=>`<div class=c><h3>${ic.id.toUpperCase()}　${ic.name}</h3><div class=av><img src="${rel(dirs[i],'avatar_110_dark.png')}"><img src="${rel(dirs[i],'avatar_110_light.png')}"><img src="${rel(dirs[i],'avatar_40_dark.png')}"><img src="${rel(dirs[i],'avatar_40_light.png')}"><small>110px／40px　深淺底</small></div>
<img class=l src="${rel(dirs[i],'lockup_capsule_light.png')}"><img class=l src="${rel(dirs[i],'lockup_capsule_dark.png')}"></div>`).join('')}</div>`;
  fs.writeFileSync(path.join(__dirname,'compare3.html'),html);
  const p2=await br.newPage({viewport:{width:2400,height:900}});await p2.goto('file://'+path.join(__dirname,'compare3.html'));await p2.waitForTimeout(600);
  await p2.screenshot({path:path.join(OUT,'final_compare.png'),fullPage:true});
  await br.close();
})().catch(e=>{console.error(e);process.exit(1)});
