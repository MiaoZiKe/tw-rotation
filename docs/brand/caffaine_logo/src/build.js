// CaffAIne LOGO 產生器：純 SVG 向量，Playwright 轉 PNG 並量測重疊
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const OUT = path.resolve(__dirname, '..');
const THEMES = {
  dark:  { bg:'#1B130F', fg:'#F4E4CC', ac:'#3DE0D0', mid:'#C98B55', onac:'#1B130F' },
  light: { bg:'#FBF6EE', fg:'#3A2418', ac:'#0E9F96', mid:'#B8743A', onac:'#FBF6EE' },
};
const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";
const CJK = "'WenQuanYi Zen Hei','Noto Sans CJK TC',sans-serif";
const S = (c,w=12,extra='') => `fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${extra}`;
const CUP_BODY = 'M32 92 H132 V120 C132 148 110 166 82 166 C54 166 32 148 32 120 Z';
const CUP_HANDLE = 'M132 104 H146 a16 16 0 0 1 0 32 H128';
const cup = c => `<path d="${CUP_BODY}" ${S(c.fg)}/><path d="${CUP_HANDLE}" ${S(c.fg)}/>`;

// 每個方向：id、名稱、意義、函式(c) 回傳 200x200 畫布內的圖形
const ICONS = [
 { id:'a1', name:'蒸氣電路', meaning:'杯口升起的蒸氣化為三條電路走線，末端節點亮起：咖啡的熱氣就是 AI 的訊號。',
   draw:c=>`${cup(c)}<path d="M50 80 V52" ${S(c.mid,8)}/><circle cx="50" cy="40" r="7" fill="${c.mid}"/>
   <path d="M82 80 V62 L98 46 V30" ${S(c.ac,8)}/><circle cx="98" cy="20" r="9" fill="${c.ac}"/>
   <path d="M114 80 V60 L126 48 V38" ${S(c.mid,8)}/><circle cx="126" cy="28" r="7" fill="${c.mid}"/>
   <path d="M44 182 H120" ${S(c.fg,8)}/>` },
 { id:'a2', name:'拉花 AI', meaning:'俯視一杯咖啡，奶泡拉出的花紋就是 AI 兩個字：端上桌的是新知，不是咖啡而已。',
   draw:c=>`<circle cx="92" cy="100" r="72" ${S(c.fg)}/><path d="M172 84 a16 16 0 0 1 0 32" ${S(c.fg)}/>
   <circle cx="92" cy="100" r="58" fill="${c.mid}"/>
   <path d="M52 134 L72 72 L92 134 M60 112 H84" ${S(c.ac,13)}/><path d="M118 72 V134" ${S(c.ac,13)}/>` },
 { id:'a3', name:'豆中晶片', meaning:'咖啡豆正中的那條縫，換成電路走線與節點：提神的豆子裡跑著 AI。',
   draw:c=>`<g transform="rotate(-32 100 100)"><ellipse cx="100" cy="100" rx="58" ry="78" ${S(c.fg)}/>
   <path d="M100 40 V70 L120 90 V112 L100 132 V160" ${S(c.ac,9)}/><circle cx="100" cy="36" r="8" fill="${c.ac}"/><circle cx="100" cy="164" r="8" fill="${c.ac}"/>
   <path d="M58 84 H44 M58 116 H44 M142 84 H156 M142 116 H156" ${S(c.mid,8)}/></g>` },
 { id:'a4', name:'一杯的時間', meaning:'外圈是倒數的計時環（走了四分之三），圈內一只小杯：一杯咖啡的時間，剛好看完一個新知。',
   draw:c=>{const s=.56; return `<circle cx="100" cy="100" r="82" ${S(c.mid,10,'opacity=".4"')}/>
   <path d="M100 18 A82 82 0 1 1 18 100" ${S(c.ac,12)}/><circle cx="18" cy="100" r="11" fill="${c.ac}"/>
   <g transform="translate(${100-100*s} ${100-136*s}) scale(${s})">${cup({fg:c.fg}).replace(/stroke-width="12"/g,'stroke-width="17"')}<path d="M44 182 H120" ${S(c.fg,14)}/></g>`}},
 { id:'a5', name:'杯中打勾', meaning:'杯裡一個大勾：這個新知看懂了、清單勾掉了；上方兩縷蒸氣是專心的狀態。',
   draw:c=>`${cup(c)}<path d="M52 126 L76 148 L112 108" ${S(c.ac,15)}/>
   <path d="M60 78 q-12 -14 0 -28 q12 -14 0 -28" ${S(c.mid,8)}/><path d="M102 78 q-12 -14 0 -28 q12 -14 0 -28" ${S(c.mid,8)}/><path d="M44 182 H120" ${S(c.fg,8)}/>` },
 { id:'a6', name:'杯剖面晶片', meaning:'把杯子切開，裡面是一顆晶片：杯身兩側長出接腳，杯心是發亮的運算核心。',
   draw:c=>{let pins='';for(const y of [92,116,140]){const xl=30+16*(y-70)/90,xr=134-16*(y-70)/90;pins+=`M${xl-20} ${y} H${xl} M${xr} ${y} H${xr+20} `;}
   return `<g transform="translate(18 -10)"><path d="M30 70 H134 L118 160 H46 Z" ${S(c.fg)}/><path d="${pins}" ${S(c.mid,8)}/>
   <rect x="60" y="92" width="44" height="44" rx="8" fill="${c.ac}"/><path d="M66 42 q-12 -12 0 -24 M98 42 q-12 -12 0 -24" ${S(c.mid,8)}/></g>`}},
 { id:'a7', name:'咖啡因分子', meaning:'咖啡因的雙環結構（六環＋五環）當骨架，最外側的節點換成發亮的 AI：名稱 CaffAIne 的由來。',
   draw:c=>{const r=40,hx=60,hy=104;const hv=a=>[hx+r*Math.cos(a*Math.PI/180),hy+r*Math.sin(a*Math.PI/180)];
   const H=[30,90,150,210,270,330].map(hv);const xe=H[0][0],s=r;const pc=xe+0.688*s,R=0.8507*s;
   const P=[0,72,144,216,288].map(a=>[pc+R*Math.cos(a*Math.PI/180),hy+R*Math.sin(a*Math.PI/180)]);
   const poly=pts=>pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ')+' Z';
   const m=[[H[4],-24],[H[2],-24],[H[3],-24]]; let arms='';
   const ex=(p,ang,l)=>[p[0]+l*Math.cos(ang*Math.PI/180),p[1]+l*Math.sin(ang*Math.PI/180)];
   const arm=[[H[4],270],[H[3],210],[H[1],90]].map(([p,a])=>[p,ex(p,a,22)]);
   arm.forEach(([a,b])=>arms+=`<path d="M${a[0]} ${a[1]} L${b[0]} ${b[1]}" ${S(c.mid,8)}/><circle cx="${b[0]}" cy="${b[1]}" r="8" fill="${c.mid}"/>`);
   let nodes=H.concat([P[1],P[2],P[3],P[4]].slice(0,0)).map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="7" fill="${c.fg}"/>`).join('');
   nodes+= [P[1],P[4]].map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="7" fill="${c.fg}"/>`).join('');
   return `<g transform="translate(10 -4)"><path d="${poly(H)}" ${S(c.fg,8)}/><path d="${poly(P)}" ${S(c.fg,8)}/>${arms}${nodes}
   <circle cx="${P[0][0]}" cy="${P[0][1]}" r="15" fill="${c.ac}"/></g>`}},
 { id:'a8', name:'豆點 AI', meaning:'直接寫出 AI 兩個字母，字母 I 頭上的那一點不是點，是一顆咖啡豆。',
   draw:c=>`<path d="M22 164 L66 54 L110 164 M38 124 H94" ${S(c.ac,19)}/><path d="M150 100 V164" ${S(c.ac,19)}/>
   <g transform="rotate(28 150 62)"><ellipse cx="150" cy="62" rx="17" ry="24" fill="${c.mid}"/><path d="M150 40 C140 54 160 70 150 84" ${S(c.bg,5)}/></g>` },
];

// 文字標：3 種 AI 強調處理。回傳 {svg,w,h}；m(text,weight,size)=寬度
const ASC = .76;
function wordmark(t, c, size, m) {
  const parts = ['Caff','AI','ne']; let x = 0, out = '', base = size*ASC, h = size*ASC, w;
  const T = (txt,wt,col,sz=size,xx=x,dy=0)=>`<text x="${xx.toFixed(1)}" y="${(base+dy).toFixed(1)}" font-family="${FONT}" font-weight="${wt}" font-size="${sz}" fill="${col}" style="font-feature-settings:'cv08'">${txt}</text>`;
  if (t===1) { // AI 換色＋加粗
    const ws=[m(parts[0],500,size),m(parts[1],800,size),m(parts[2],500,size)];
    out+=T(parts[0],500,c.fg);x+=ws[0];out+=T(parts[1],800,c.ac);x+=ws[1];out+=T(parts[2],500,c.fg);x+=ws[2];w=x;
  } else if (t===2) { // AI 放進實心色塊（像杯中咖啡的標籤）
    const pad=size*.12, ws=[m(parts[0],600,size),m(parts[1],800,size),m(parts[2],600,size)];
    out+=T(parts[0],600,c.fg);x+=ws[0]+size*.06;
    out+=`<rect x="${x.toFixed(1)}" y="${(base-size*.76-size*.1).toFixed(1)}" width="${(ws[1]+pad*2).toFixed(1)}" height="${(size*.76+size*.2).toFixed(1)}" rx="${size*.14}" fill="${c.ac}"/>`;
    out+=T(parts[1],800,c.onac,size,x+pad);x+=ws[1]+pad*2+size*.06;out+=T(parts[2],600,c.fg);x+=ws[2];w=x;
    h=base+size*.1; // 色塊下緣
    return {svg:`<g transform="translate(0 ${(size*.1).toFixed(1)})">${out}</g>`,w,h:h+size*.1,off:size*.1};
  } else { // AI 放大 18%、極粗，字母間距收緊，底下一條粗底線
    const sz2=size*1.18, ws=[m(parts[0],300,size),m(parts[1],900,sz2),m(parts[2],300,size)];
    out+=T(parts[0],300,c.fg);x+=ws[0]+size*.02;out+=T(parts[1],900,c.ac,sz2,x);
    out+=`<rect x="${x.toFixed(1)}" y="${(base+size*.1).toFixed(1)}" width="${ws[1].toFixed(1)}" height="${(size*.07).toFixed(1)}" rx="${size*.035}" fill="${c.ac}"/>`;
    x+=ws[1]+size*.02;out+=T(parts[2],300,c.fg);x+=ws[2];w=x;
    h=base+size*.17;
    return {svg:`<g transform="translate(0 ${(sz2*.76-size*.76).toFixed(1)})">${out}</g>`,w,h:h+(sz2*.76-size*.76),off:0};
  }
  return {svg:out,w,h,off:0};
}

(async()=>{
  const br = await chromium.launch(); const pg = await br.newPage();
  const mp=await br.newPage(); await mp.setContent('<canvas id=cv></canvas>');
  const meas = async (txt,wt,size,fam=FONT)=> mp.evaluate(([txt,wt,size,fam])=>{const e=document.createElement('span');e.style.cssText=`position:absolute;white-space:pre;font:${wt} ${size}px ${fam};font-feature-settings:'cv08'`;e.textContent=txt;document.body.appendChild(e);const w=e.getBoundingClientRect().width;e.remove();return w;},[txt,wt,size,fam]);
  // 預先量好寬度快取
  const cache={}; const SIZES=[100,150,160];
  for (const sz of SIZES) for (const wt of [300,500,600,800,900]) for (const tx of ['Caff','AI','ne']) { for (const k of [1,1.18]) { const s=sz*k; cache[`${tx}|${wt}|${s}`]=await meas(tx,wt,s); } }
  const m=(tx,wt,s)=>cache[`${tx}|${wt}|${s}`] ?? (()=>{throw new Error('no cache '+tx+wt+s)})();
  const TAG='一杯咖啡的時間，看懂一個 AI 新知';
  const tagW = async (sz)=>({a:await meas('一杯咖啡的時間，看懂一個 ',400,sz,CJK),b:await meas('AI',700,sz,FONT),c:await meas(' 新知',400,sz,CJK)});
  const rep = {};
  const svgWrap=(w,h,bg,inner,rx=0)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${bg?`<rect width="${w}" height="${h}" rx="${rx}" fill="${bg}"/>`:''}${inner}</svg>`;
  const png = async (svg,file,w,h)=>{await pg.setViewportSize({width:w,height:h});await pg.setContent(`<style>html,body{margin:0;background:transparent}</style>${svg.replace('<svg ',`<svg style="display:block;width:${w}px;height:${h}px" `)}`);await pg.screenshot({path:file,omitBackground:true,clip:{x:0,y:0,width:w,height:h}});};

  // 文字標三款
  fs.mkdirSync(path.join(OUT,'wordmark'),{recursive:true});
  for (const th of ['dark','light']) for (const t of [1,2,3]) {
    const c=THEMES[th]; const wm=wordmark(t,c,150,m); const pad=60;
    const W=Math.ceil(wm.w+pad*2),H=Math.ceil(wm.h+pad*2+20);
    const svg=svgWrap(W,H,c.bg,`<g transform="translate(${pad} ${pad})">${wm.svg}</g>`);
    fs.writeFileSync(path.join(OUT,'wordmark',`wordmark_W${t}_${th}.svg`),svg);
    await png(svg,path.join(OUT,'wordmark',`wordmark_W${t}_${th}.png`),W,H);
  }

  const meta=[];
  for (const ic of ICONS) {
    const dir=path.join(OUT,`${ic.id}_${ic.name.replace(/ /g,'')}`); fs.mkdirSync(dir,{recursive:true});
    for (const th of ['dark','light']) {
      const c=THEMES[th]; const g=ic.draw(c);
      // 方形（1024）
      const sc=1024*.62/200, off=(1024-200*sc)/2;
      const sq=svgWrap(1024,1024,c.bg,`<g transform="translate(${off} ${off}) scale(${sc})">${g}</g>`,224);
      fs.writeFileSync(path.join(dir,`icon_${th}.svg`),sq); await png(sq,path.join(dir,`icon_${th}_1024.png`),1024,1024);
      // 圓形大頭貼
      for (const D of [110,40]) {
        const s2=D*.70/200,o2=(D-200*s2)/2;
        const av=svgWrap(D,D,null,`<circle cx="${D/2}" cy="${D/2}" r="${D/2}" fill="${c.bg}"/><g transform="translate(${o2} ${o2}) scale(${s2})">${g}</g>`);
        fs.writeFileSync(path.join(dir,`avatar_${D}_${th}.svg`),av); await png(av,path.join(dir,`avatar_${D}_${th}.png`),D,D);
      }
      // 橫式完整版
      const wsz=150, wm=wordmark(1,c,wsz,m), tsz=40, tw=await tagW(tsz);
      const tagTotal=tw.a+tw.b+tw.c, icon=360, padX=90, gap=40, gapV=44;
      const tcap=tsz*.8;
      const blockH=wm.h+gapV+tcap, blockW=Math.max(wm.w,tagTotal);
      const W=Math.ceil(padX*2+icon+gap+blockW), H=520;
      const iy=(H-icon)/2, ty=(H-blockH)/2, tx=padX+icon+gap;
      const tagY=ty+wm.h+gapV+tcap*.92;
      const k=icon/200;
      const inner=`<g id="gi" transform="translate(${padX} ${iy}) scale(${k})">${g}</g>
      <g id="gw" transform="translate(${tx} ${ty})">${wm.svg}</g>
      <g id="gt"><text x="${tx}" y="${tagY.toFixed(1)}" font-family="${CJK}" font-size="${tsz}" fill="${c.fg}" opacity=".9">一杯咖啡的時間，看懂一個 <tspan font-family="${FONT}" font-weight="700" fill="${c.ac}" style="font-feature-settings:'cv08'">AI</tspan> 新知</text></g>`;
      const lk=svgWrap(W,H,c.bg,inner);
      fs.writeFileSync(path.join(dir,`lockup_${th}.svg`),lk); await png(lk,path.join(dir,`lockup_${th}.png`),W,H);
      // 重疊檢查（實際渲染 bbox）
      await pg.setViewportSize({width:W,height:H}); await pg.setContent(`<style>body{margin:0}</style>${lk}`);
      const r=await pg.evaluate(()=>{const b=id=>{const e=document.getElementById(id);const bb=e.getBBox();const m=e.getCTM();return {x:bb.x*m.a+m.e,y:bb.y*m.d+m.f,w:bb.width*m.a,h:bb.height*m.d};};
        return {i:b('gi'),w:b('gw'),t:b('gt')};});
      const lay=path.join(require('os').tmpdir(),'cf_layers'); fs.mkdirSync(lay,{recursive:true});
      for (const id of ['gi','gw','gt']) { await pg.evaluate(([id])=>{for(const k of ['gi','gw','gt'])document.getElementById(k).style.display=(k===id?'':'none');document.querySelector('svg>rect').style.display='none';},[id]); await pg.screenshot({path:path.join(lay,`${ic.id}_${th}_${id}.png`),omitBackground:true,clip:{x:0,y:0,width:W,height:H}}); }
      const gapf=(a,b)=>{const dx=Math.max(b.x-(a.x+a.w),a.x-(b.x+b.w));const dy=Math.max(b.y-(a.y+a.h),a.y-(b.y+b.h));return Math.max(dx,dy);};
      meta.push({id:ic.id,th,W,H,gap_icon_word:gapf(r.i,r.w),gap_icon_tag:gapf(r.i,r.t),gap_word_tag:gapf(r.w,r.t)});
    }
  }
  fs.writeFileSync(path.join(OUT,'src','overlap_report.json'),JSON.stringify(meta,null,1));
  console.table(meta.map(x=>({...x,gap_icon_word:x.gap_icon_word.toFixed(1),gap_icon_tag:x.gap_icon_tag.toFixed(1),gap_word_tag:x.gap_word_tag.toFixed(1)})));
  // 總覽
  const rel=(d,f)=>`${d}/${f}`;
  const dirs=ICONS.map(i=>`${i.id}_${i.name.replace(/ /g,'')}`);
  const html=`<!doctype html><meta charset=utf-8><base href="file://${OUT}/"><style>
  body{margin:0;background:#EFE7DB;font-family:'WenQuanYi Zen Hei',Inter,sans-serif;color:#2b1a10;padding:40px;width:2400px;box-sizing:border-box}
  h1{font-size:44px;margin:0 0 6px}h2{font-size:30px;margin:44px 0 16px}p.s{font-size:22px;margin:0 0 20px;opacity:.75}
  .wm{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.wm img{width:100%;border-radius:12px;display:block}
  .wm div{background:#fff;padding:12px;border-radius:14px}.wm b{font-size:22px;display:block;margin:4px 0 10px}
  .g{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
  .card{background:#fff;border-radius:18px;padding:22px;display:grid;grid-template-columns:260px 260px 150px 1fr;gap:18px;align-items:start}
  .card h3{grid-column:1/-1;margin:0;font-size:30px}.card .mean{grid-column:1/-1;font-size:20px;line-height:1.5;margin:-6px 0 4px}
  .card img.big{width:260px;border-radius:26px}.av{display:flex;flex-direction:column;gap:10px;align-items:center}.av small{font-size:15px;opacity:.7}
  .lk{width:100%;border-radius:12px;grid-column:1/-1}.row2{display:flex;gap:10px;align-items:center}
  </style><h1>CaffAIne 頻道③ LOGO 方向總覽</h1><p class=s>一杯咖啡的時間，看懂一個 AI 新知｜深底／淺底、IG 圓形 110px／40px、橫式完整版</p>
  <h2>文字標：AI 的三種強調處理</h2><div class=wm>
  ${[['W1 換色加粗','AI 換成亮青色並加到 ExtraBold，其餘 Medium：最乾淨、最通用'],['W2 色塊嵌字','AI 反白放進實心色塊，像杯上的標籤：辨識度最高，縮小也一眼找到'],['W3 放大底線','AI 放大 18%、Black 字重，其餘 Light，底下一條粗線：層次最強']].map((x,i)=>`<div><b>${x[0]}　<span style="font-weight:400;font-size:17px">${x[1]}</span></b><img src="wordmark/wordmark_W${i+1}_dark.png"><img style="margin-top:8px" src="wordmark/wordmark_W${i+1}_light.png"></div>`).join('')}</div>
  <h2>圖形標 8 個方向</h2><div class=g>
  ${ICONS.map((ic,i)=>`<div class=card><h3>${ic.id.toUpperCase()}　${ic.name}</h3><div class=mean>${ic.meaning}</div>
   <img class=big src="${rel(dirs[i],'icon_dark_1024.png')}"><img class=big src="${rel(dirs[i],'icon_light_1024.png')}">
   <div class=av><img src="${rel(dirs[i],'avatar_110_dark.png')}"><img src="${rel(dirs[i],'avatar_110_light.png')}"><div class=row2><img src="${rel(dirs[i],'avatar_40_dark.png')}"><img src="${rel(dirs[i],'avatar_40_light.png')}"></div><small>110px／40px</small></div><div></div>
   <img class=lk src="${rel(dirs[i],'lockup_dark.png')}"><img class=lk src="${rel(dirs[i],'lockup_light.png')}"></div>`).join('')}</div>`;
  fs.writeFileSync(path.join(OUT,'src','overview.html'),html);
  const p2=await br.newPage({viewport:{width:2400,height:1000}}); await p2.goto('file://'+path.join(OUT,'src','overview.html')); await p2.waitForTimeout(500);
  await p2.screenshot({path:path.join(OUT,'overview.png'),fullPage:true});
  await br.close();
})().catch(e=>{console.error(e);process.exit(1)});
