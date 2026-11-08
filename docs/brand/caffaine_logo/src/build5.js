// CaffAIne 第三輪：簡約。單一線寬、最多 2 色（深可可＋焦糖，底為奶油／深可可），無濾鏡。
const { chromium } = require('playwright');
const fs=require('fs'),path=require('path'),os=require('os');
const OUT=path.resolve(__dirname,'..','round3','final');
const TH={dark:{bg:'#3B2A22',ink:'#FFF7EA',ac:'#F0893A'},light:{bg:'#FFF7EA',ink:'#3B2A22',ac:'#D9772B'}};
const FONT="Inter,'Helvetica Neue',Arial,sans-serif",CJK="'WenQuanYi Zen Hei','Noto Sans CJK TC',sans-serif";
const S=(c,w=12)=>`fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"`;
const letterA=(x,y,h,c,w,k=.36)=>{const hw=h*k;return `<path d="M${x-hw} ${y+h} L${x} ${y} L${x+hw} ${y+h} M${x-hw*.62} ${y+h*.74} H${x+hw*.62}" ${S(c,w)}/>`};
const letterI=(x,y,h,c,w,hw)=>`<path d="M${x-hw} ${y} H${x+hw} M${x} ${y} V${y+h} M${x-hw} ${y+h} H${x+hw}" ${S(c,w)}/>`;
const CUPBODY='M52 56 H148 L138 176 H62 Z';
const ALL=[
 {id:'q1',name:'杯套色帶AI',meaning:'一只外帶杯，杯套是一條焦糖色帶，色帶上留白寫著 AI。',
  draw:c=>`<path d="M54 84 H146 L141 158 H59 Z" fill="${c.ac}"/><path d="${CUPBODY}" ${S(c.ink)}/><path d="M42 38 H158" ${S(c.ink)}/>${letterA(85,96,50,c.bg,12,.3)}${letterI(124,96,50,c.bg,12,6)}`},
 {id:'q2',name:'負空間AI',meaning:'實心外帶杯，AI 是杯身挖空的留白；只有杯蓋一道焦糖。',
  draw:c=>`<path d="M50 62 H150 L139 178 H61 Z" fill="${c.ink}" stroke="${c.ink}" stroke-width="8" stroke-linejoin="round"/><path d="M40 40 H160" ${S(c.ac,18.4)}/>${letterA(88,100,52,c.bg,12)}${letterI(122,100,52,c.bg,12,10)}`},
 {id:'q3',name:'俯視杯口AI',meaning:'俯視杯口，一圈線加一只杯耳，圈中心是焦糖色的 AI。',
  draw:c=>`<circle cx="88" cy="100" r="70" ${S(c.ink)}/><path d="M158 86 H172 a14 14 0 0 1 0 28 H158" ${S(c.ink)}/>${letterA(66,72,52,c.ac,12)}${letterI(112,72,52,c.ac,12,10)}`},
 {id:'q4',name:'單線馬克杯',meaning:'一筆畫出的馬克杯，杯中寫一個焦糖色 AI；沒有蒸氣、沒有裝飾。',
  draw:c=>`<g transform="translate(-9 0)"><path d="M38 58 V136 Q38 172 74 172 H114 Q150 172 150 136 V58 Z" ${S(c.ink,15)}/><path d="M150 82 H166 Q184 82 184 102 V116 Q184 136 166 136 H150" ${S(c.ink,15)}/>${letterA(80,92,52,c.ac,11,.36)}${letterI(123,92,52,c.ac,11,7)}</g>`},
 {id:'q5',name:'杯蓋剖影',meaning:'外帶杯蓋的側面剪影：圓頂加底部拱形留白構成 A，旁邊的吸管就是 I。',
  draw:c=>`<rect x="26" y="150" width="148" height="22" rx="11" fill="${c.ink}"/><path d="M54 152 L72 70 H128 L146 152 Z" fill="${c.ink}" stroke="${c.ink}" stroke-width="8" stroke-linejoin="round"/>
   <path d="M84 152 V126 a16 16 0 0 1 32 0 V152 Z" fill="${c.bg}"/><rect x="92" y="92" width="16" height="14" rx="7" fill="${c.bg}"/><path d="M158 140 V34 M144 34 H172" ${S(c.ac)}/>`},
 {id:'q6',name:'一縷蒸氣成I',meaning:'馬克杯上只有一縷蒸氣，兩端加上短橫就是襯線 I，字母 A 留給文字標。',
  draw:c=>`<path d="M44 90 V140 Q44 176 80 176 H108 Q144 176 144 140 V90 Z" ${S(c.ink)}/><path d="M144 108 H158 Q176 108 176 126 V134 Q176 152 158 152 H144" ${S(c.ink)}/>
   <path d="M94 76 C80 62 108 48 94 34" ${S(c.ac)}/><path d="M80 30 H108 M80 80 H108" ${S(c.ac)}/>`},
];
const ICONS=ALL.filter(i=>['q1','q2','q4'].includes(i.id));
// 文字標（乾淨無襯線，AI 只用顏色＋字重）
const WM={text:{p:['Caff','AI','ne'],ls:0},lower:{p:['caff','ai','ne'],ls:0},upper:{p:['CAFF','AI','NE'],ls:.06}};
function wordmark(c,size,m,mode){const {p,ls}=WM[mode],base=size*.76,tr=ls*size;let x=0,out='';
  const T=(t,wt,col,x)=>`<text x="${x.toFixed(1)}" y="${base.toFixed(1)}" font-family="${FONT}" font-weight="${wt}" font-size="${size}" letter-spacing="${tr}" fill="${col}" style="font-feature-settings:'cv08'">${t}</text>`;
  const ws=[m(p[0],500,mode),m(p[1],800,mode),m(p[2],500,mode)];
  out+=T(p[0],500,c.ink,x);x+=ws[0];out+=T(p[1],800,c.ac,x);x+=ws[1];out+=T(p[2],500,c.ink,x);x+=ws[2]-tr;return{svg:out,w:x,h:base};}
(async()=>{
  const br=await chromium.launch(),pg=await br.newPage(),mp=await br.newPage();await mp.setContent('<body></body>');
  const meas=(txt,wt,size,fam=FONT,ls=0)=>mp.evaluate(([txt,wt,size,fam,ls])=>{const e=document.createElement('span');e.style.cssText=`position:absolute;white-space:pre;font:${wt} ${size}px ${fam};letter-spacing:${ls}px;font-feature-settings:'cv08'`;e.textContent=txt;document.body.appendChild(e);const w=e.getBoundingClientRect().width;e.remove();return w;},[txt,wt,size,fam,ls]);
  const cache={};for(const mode of Object.keys(WM))for(const [i,wt] of [[0,500],[1,800],[2,500]]){const t=WM[mode].p[i];cache[`${t}|${wt}|${mode}`]=await meas(t,wt,150,FONT,WM[mode].ls*150);}
  const m=(t,wt,mode)=>cache[`${t}|${wt}|${mode}`];
  const WRAP=(w,h,bg,inner,rx=0)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${bg?`<rect width="${w}" height="${h}" rx="${rx}" fill="${bg}"/>`:''}${inner}</svg>`;
  const png=async(svg,f,w,h)=>{await pg.setViewportSize({width:w,height:h});await pg.setContent(`<style>html,body{margin:0;background:transparent}</style>${svg.replace('<svg ',`<svg style="display:block;width:${w}px;height:${h}px" `)}`);await pg.screenshot({path:f,omitBackground:true,clip:{x:0,y:0,width:w,height:h}});};
  fs.mkdirSync(path.join(OUT,'wordmark'),{recursive:true});
  for(const th of ['dark','light'])for(const mode of ['text']){const c=TH[th],wm=wordmark(c,150,m,mode),pad=60,W=Math.ceil(wm.w+pad*2),H=Math.ceil(wm.h+pad*2);
    const svg=WRAP(W,H,c.bg,`<g transform="translate(${pad} ${pad})">${wm.svg}</g>`);const f=`wordmark_${mode}_${th}`;fs.writeFileSync(path.join(OUT,'wordmark',f+'.svg'),svg);await png(svg,path.join(OUT,'wordmark',f+'.png'),W,H);}
  const lay=path.join(os.tmpdir(),'cf_layers');fs.rmSync(lay,{recursive:true,force:true});fs.mkdirSync(lay,{recursive:true});
  const TS=40,tw=(await meas('一杯咖啡的時間，看懂一個 ',400,TS,CJK))+(await meas('AI',700,TS))+(await meas(' 新知',400,TS,CJK));
  for(const ic of ICONS){const dir=path.join(OUT,`${ic.id}_${ic.name}`);fs.mkdirSync(dir,{recursive:true});
    for(const th of ['dark','light']){const c=TH[th],g=ic.draw(c);
      const sc=1024*.66/200,off=(1024-200*sc)/2;const sq=WRAP(1024,1024,c.bg,`<g transform="translate(${off} ${off}) scale(${sc})">${g}</g>`,260);
      fs.writeFileSync(path.join(dir,`icon_${th}.svg`),sq);await png(sq,path.join(dir,`icon_${th}_1024.png`),1024,1024);
      for(const D of [110,40]){const s2=D*.74/200,o2=(D-200*s2)/2;const av=WRAP(D,D,null,`<circle cx="${D/2}" cy="${D/2}" r="${D/2}" fill="${c.bg}"/><g transform="translate(${o2} ${o2}) scale(${s2})">${g}</g>`);
        fs.writeFileSync(path.join(dir,`avatar_${D}_${th}.svg`),av);await png(av,path.join(dir,`avatar_${D}_${th}.png`),D,D);}
      const wm=wordmark(c,150,m,'text'),icon=360,padX=90,gapX=48,gapV=44,tcap=TS*.8,bh=wm.h+gapV+tcap,bw=Math.max(wm.w,tw);
      const W=Math.ceil(padX*2+icon+gapX+bw),H=520,iy=(H-icon)/2,ty=(H-bh)/2,tx=padX+icon+gapX,tagY=ty+wm.h+gapV+tcap*.92;
      const lk=WRAP(W,H,c.bg,`<g id="gi" transform="translate(${padX} ${iy}) scale(${icon/200})">${g}</g><g id="gw" transform="translate(${tx} ${ty})">${wm.svg}</g><g id="gt"><text x="${tx}" y="${tagY.toFixed(1)}" font-family="${CJK}" font-size="${TS}" fill="${c.ink}" opacity=".9">一杯咖啡的時間，看懂一個 <tspan font-family="${FONT}" font-weight="700" fill="${c.ac}" style="font-feature-settings:'cv08'">AI</tspan> 新知</text></g>`);
      fs.writeFileSync(path.join(dir,`lockup_${th}.svg`),lk);await png(lk,path.join(dir,`lockup_${th}.png`),W,H);
      await pg.setViewportSize({width:W,height:H});await pg.setContent(`<style>body{margin:0}</style>${lk}`);
      for(const id of ['gi','gw','gt']){await pg.evaluate(([id])=>{for(const k of ['gi','gw','gt'])document.getElementById(k).style.display=k===id?'':'none';document.querySelector('svg>rect').style.display='none';},[id]);await pg.screenshot({path:path.join(lay,`q${ic.id.slice(1)}_${th}_${id}.png`),omitBackground:true,clip:{x:0,y:0,width:W,height:H}});}
    }}
  const dirs=ICONS.map(i=>`${i.id}_${i.name}`);
  const html=`<!doctype html><meta charset=utf-8><base href="file://${OUT}/"><style>body{margin:0;background:#F3E8D6;font-family:'WenQuanYi Zen Hei',Inter,sans-serif;color:#3B2A22;padding:40px;width:2400px;box-sizing:border-box}h1{font-size:40px;margin:0 0 20px}.g{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.c{background:#fff;border-radius:22px;padding:22px}h3{margin:0 0 14px;font-size:30px}.av{display:flex;gap:14px;align-items:center;margin-bottom:14px}.l{width:100%;border-radius:14px;display:block;margin-top:12px}</style>
<h1>CaffAIne 第三輪定稿候選：Q2 負空間 AI／Q1 杯套色帶 AI／Q4 單線馬克杯</h1><div class=g>${ICONS.map((ic,i)=>`<div class=c><h3>${ic.id.toUpperCase()}　${ic.name}</h3><div class=av><img src="${dirs[i]}/avatar_110_dark.png"><img src="${dirs[i]}/avatar_110_light.png"><img src="${dirs[i]}/avatar_40_dark.png"><img src="${dirs[i]}/avatar_40_light.png"><small>110px／40px　深淺底</small></div><img class=l src="${dirs[i]}/lockup_light.png"><img class=l src="${dirs[i]}/lockup_dark.png"></div>`).join('')}</div>`;
  fs.writeFileSync(path.join(__dirname,'compare4.html'),html);
  const p2=await br.newPage({viewport:{width:2400,height:900}});await p2.goto('file://'+path.join(__dirname,'compare4.html'));await p2.waitForTimeout(600);await p2.screenshot({path:path.join(OUT,'final_compare_round3.png'),fullPage:true});
  await br.close();
})().catch(e=>{console.error(e);process.exit(1)});
