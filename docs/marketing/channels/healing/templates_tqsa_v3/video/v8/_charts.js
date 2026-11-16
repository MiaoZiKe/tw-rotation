// ───────── v8 通用鏡型（2026-11-16 總編輯）：資料驅動，一支片的每鏡＝量身插圖（ILL[s.ill]）＋一種資料圖（s.type）──────────
// 版面：標題 170、狀態標籤 306、插圖面板 392（高 IH）、資料圖 776～1500、字幕卡下緣 1690、出處 1806、頁尾帶 1866。
// 動作節奏（審片標準：靜止段 ≤1.2 秒）：第一拍 0～0.9 秒資料圖長出 → 第二拍約 1.4 秒強調出現（每鏡唯一）→ 第三拍約 2.4 秒掃光／物件回應；插圖物件自己有預備→主動作→過衝→回彈，另有細小環境動作（蒸氣、秒針、波紋）。
// 強調只用：差距括號＋箭頭、淡橘底膠囊彈入、數字後方螢光底；不用手繪圈；強調元素包在 data-em 群組裡（check_v8.py 量與文字／線稿最短距離）。
const IH=368,CT=776,CH=724;
// v8.1（animation-director 11-16 退件：鏡內 2 秒後只剩光點不算主體動作）：每鏡 2.0 秒起每 1.0 秒一拍——狀態標籤輕跳（2.0、3.0…），強調膠囊輕跳（2.5、3.5…）；位移 ≤7px、每拍衰減落定，不縮放、不閃爍
let _LT=0,_ONCE=false;   // _ONCE：scene.once 開啟時，光點／亮帶只做一次就停（預設循環，其他片不受影響）
let _BEATS=null,_TAGALL=false;   // 有旁白時＝這一鏡對準字詞起音的拍點（gen_v8.py 算好）；偶數拍跳狀態標籤、奇數拍跳強調膠囊
function beatHop(lt,off,amp){let y=0;if(_BEATS){_BEATS.forEach((b,i)=>{if((off===-1||(i%2)===((off||0)>0?1:0))&&b<lt+.01)y+=-(amp||7)*DECAY(lt-b,6,15)});return y}for(let b=2.0+(off||0);b<lt+.01&&b<14;b+=1.0)y+=-(amp||7)*DECAY(lt-b,6,15);return y}
const F1=(v,d)=>Number(v).toLocaleString('en-US',{minimumFractionDigits:d||0,maximumFractionDigits:d||0});
function capsule(cx,cy,w,h,txt,fs,p,col){if(p<=0)return'';const k=Math.max(.01,p);return `<g data-em="1" opacity="${clamp((p-.1)/.85).toFixed(3)}" transform="translate(${cx},${(cy+beatHop(_LT,.5,6)).toFixed(1)}) scale(${k.toFixed(3)})"><rect x="${-w/2}" y="${-h/2}" width="${w}" height="${h}" rx="${h/2}" fill="${col||'#F6D9B8'}" stroke="#E7B07A" stroke-width="2"/>${T(0,fs*.36,txt,fs,700,HINT)}</g>`}
// 差距括號：x 位置、上下 y、由上往下畫出；箭頭頭；中段文字在括號右側
function bracketV(x,y0,y1,p,lab,side){if(p<=0)return'';const s=side||1,yy=y0+(y1-y0)*clamp(p*1.4);let g=`<g data-em="1"><path d="M${x} ${y0} h${12*s} V${yy}${p>.7?' h'+(-12*s):''}" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>`;
 const q=clamp((p-.55)/.45);if(q>0)g+=`<g opacity="${q.toFixed(2)}" transform="translate(${(1-q)*-14*s},0)">${T(x+34*s,(y0+y1)/2+14,lab,40,700,HINT,s>0?'start':'end')}</g>`;return g+'</g>'}
function bracketH(x0,x1,y,p,lab,below){if(p<=0)return'';const xx=x0+(x1-x0)*clamp(p*1.4),dv=below?-14:14;let g=`<g data-em="1"><path d="M${x0} ${y} v${-dv} H${xx}${p>.7?' v'+dv:''}" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>`;
 const q=clamp((p-.55)/.45);if(q>0)g+=`<g opacity="${q.toFixed(2)}" transform="translate(0,${(1-q)*10})">${T((x0+x1)/2,below?y+56:y-34,lab,40,700,HINT)}</g>`;return g+'</g>'}
function hiliteBg(x,y,w,h,p){return p<=0?'':`<rect data-em="1" x="${x}" y="${y}" width="${(w*clamp(p)).toFixed(1)}" height="${h}" rx="10" fill="${LAMP}" opacity=".26"/>`}
const sweepBar=(x,y,w,h,lt,at)=>{if(lt<at||w<=1||window.NOGLINT)return'';const k=((lt-at)%(_ONCE?1e9:1.3))/.7;if(k>=1)return'';const id='sw'+Math.round(x)+'_'+Math.round(y),sx=x-90+(w+180)*EO(k);   // v8.1：羽化斜向亮帶（線性漸層、兩側透明、裁在圓角內），不再用硬邊方塊
 return `<defs><linearGradient id="${id}g" x1="0" x2="1"><stop offset="0" stop-color="#FFF4D6" stop-opacity="0"/><stop offset=".5" stop-color="#FFF4D6" stop-opacity=".75"/><stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></linearGradient><clipPath id="${id}c"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/></clipPath></defs><g clip-path="url(#${id}c)"><path d="M${(sx-50).toFixed(1)} ${y+h} L${(sx).toFixed(1)} ${y} L${(sx+70).toFixed(1)} ${y} L${(sx+20).toFixed(1)} ${y+h}Z" fill="url(#${id}g)" opacity="${Math.sin(Math.PI*k).toFixed(2)}"/></g>`};
// v8 第三拍（審片標準：靜止段 ≤1.2 秒）：沿一條折線走一顆暖白光點，at 秒第一次、之後每 per 秒一次（不閃爍、不縮放）
function glide(pts,lt,at,per){if(lt<at||window.NOGLINT)return'';const ph=((lt-at)%(_ONCE?1e9:(per||1.2)))/.7;if(ph>=1)return'';let L=0;const seg=[];for(let i=1;i<pts.length;i++){const d=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);seg.push(d);L+=d}
 const at2=e=>{let r=e*L,i=0;while(i<seg.length-1&&r>seg[i]){r-=seg[i];i++}const u=seg[i]?r/seg[i]:0;return [pts[i][0]+(pts[i+1][0]-pts[i][0])*u,pts[i][1]+(pts[i+1][1]-pts[i][1])*u]};
 const a=Math.sin(Math.PI*ph);let g='';[0,1,2,3].forEach(k=>{const e=EO(Math.max(0,ph-k*.06));const [x,y]=at2(e);g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${16-k*3}" fill="#FFF4D6" stroke="#F4B860" stroke-width="${k?0:2}" opacity="${(a*(1-k*.22)).toFixed(2)}"/>`});return g}   // 帶 4 節拖尾的暖白光點
function ILLbox(s,lt,d,top,h){const f=ILL[s.ill];return box('illus',top||392,h||IH,`<rect x="0" y="0" width="888" height="${h||IH}" rx="26" fill="${FACE}"/>`+(f?f.draw(lt,h||IH,s):''),lt,d,{})}
function head(s,lt,o){o=o||{};if(s.tfs)o=Object.assign({fs:s.tfs},o);let h=title(s.title,lt,o);if(s.tag)h+=tag(s.tag,lt,s.tagAt!=null?s.tagAt:(o.tagAt==null?.15:o.tagAt),306);return h}

// ── 鉤子專用小圖（高 232）──
const MINI={
 slope(m,lt){const p=pr(lt,0,.5),base=180,k=130/m.vmax,ya=base-m.a.v*k,yb=base-m.b.v*k,xa=500,xb=780,xe=xa+(xb-xa)*p,ye=ya+(yb-ya)*p;
  let g=T(0,62,m.label,40,700,TXT,'start')+T(0,116,m.sub,32,400,SUBC,'start');
  g+=`<line x1="440" y1="${base}" x2="860" y2="${base}" stroke="${LINE}" stroke-width="2.5"/><line x1="${xa}" y1="${ya}" x2="${xe}" y2="${ye}" stroke="${LAMP}" stroke-width="10" stroke-linecap="round"/><circle cx="${xa}" cy="${ya}" r="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><circle cx="${xe}" cy="${ye}" r="${14*settle(lt,.5)}" fill="${LAMP}"/>`;
  if(lt>.5&&!window.NOGLINT){const u0=lt-.5,ph=1.2*(1-Math.exp(-1.1*u0))+.3*u0,fade=clamp(u0/.2);for(let j=0;j<8;j++){const u=((ph+j/8)%1+1)%1;g+=`<circle cx="${(xa+(xb-xa)*u).toFixed(1)}" cy="${(ya+(yb-ya)*u).toFixed(1)}" r="5" fill="#FFF4D6" opacity="${(fade*.85).toFixed(2)}"/>`}}
  const lp=pr(lt,.55,.3);g+=`<g opacity="${lp}">${T(xa,ya-26,m.a.lab,36,700,TXT)}${T(xb,yb-26,m.b.lab,36,700,TXT)}${T(xa,base+40,m.a.x,32,400,SUBC)}${T(xb,base+40,m.b.x,32,400,SUBC)}</g>`;return g},
 bar2(m,lt){let g=T(0,46,m.label,40,700,TXT,'start');const x0=230,W=m.w||520;
  m.rows.forEach((r,i)=>{const y=86+i*72,p=pr(lt,.05+i*.18,.55,BACK),w=W*r.v/m.vmax*Math.min(1.03,p);g+=T(0,y+40,r.lab,34,400,TXT,'start')+`<rect x="${x0}" y="${y}" width="${Math.max(0,w).toFixed(1)}" height="52" rx="8" fill="${r.hi?LAMP:'#B98A6A'}"/>`+`<g opacity="${pr(lt,.45+i*.18,.25)}">${T(x0+Math.min(W*r.v/m.vmax,W)+14,y+38,r.txt,34,700,TXT,'start')}</g>`});
  g+=glide([[x0,86+m.rows.length*72-36],[x0+W*m.rows[m.rows.length-1].v/m.vmax,86+m.rows.length*72-36]],lt,1.6,1.2);
  if(m.ref!=null){const x=x0+W*m.ref/m.vmax;g+=`<line x1="${x}" y1="74" x2="${x}" y2="228" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6" opacity="${pr(lt,.6,.3)}"/>`}return g},
 pctbar(m,lt){let g=T(0,52,m.label,40,700,TXT,'start')+T(888,52,m.sub,32,400,SUBC,'end');const x0=0,W=888,y=92,p=pr(lt,.05,.7);
  g+=`<rect x="${x0}" y="${y}" width="${W}" height="72" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="2.5"/><rect x="${x0}" y="${y}" width="${(W*m.v/100*p).toFixed(1)}" height="72" rx="14" fill="${LAMP}"/>`+sweepBar(x0,y,W*m.v/100,72,lt,1.0);
  for(let i=1;i<10;i++)g+=`<line x1="${W*i/10}" y1="${y+8}" x2="${W*i/10}" y2="${y+64}" stroke="#FFFFFF" stroke-width="2" opacity=".55"/>`;
  g+=glide([[x0+8,y+36],[W*m.v/100-8,y+36]],lt,1.6,1.2);g+=`<g opacity="${pr(lt,.6,.3)}">${T(W*m.v/100,y+118,m.mark,34,700,TXT)}${T(W,y+118,'100',32,400,SUBC,'end')}${T(0,y+118,'0',32,400,SUBC,'start')}</g>`;return g},
 axis(m,lt){let g=T(0,46,m.label,40,700,TXT,'start');const x0=40,x1=848,sx=v=>x0+(x1-x0)*(v-m.lo)/(m.hi-m.lo),ay=150;
  g+=`<line x1="${x0}" y1="${ay}" x2="${x0+(x1-x0)*pr(lt,0,.4)}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  m.ticks.forEach((v,i)=>{g+=`<g opacity="${pr(lt,.05+i*.05,.25)}"><line x1="${sx(v)}" y1="${ay-10}" x2="${sx(v)}" y2="${ay+10}" stroke="${LINE}" stroke-width="2"/>${T(sx(v),ay+50,String(v)+(m.unit||''),32,400,SUBC)}</g>`});
  if(m.ref!=null)g+=`<line x1="${sx(m.ref)}" y1="${ay-66}" x2="${sx(m.ref)}" y2="${ay+14}" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6" opacity="${pr(lt,.3,.3)}"/>`+`<g opacity="${pr(lt,.3,.3)}">${T(sx(m.ref)+12,ay-44,m.refLab,32,400,SUBC,'start')}</g>`;
  const p=pr(lt,.3,.6),x=sx(m.lo+(m.v-m.lo)*p);g+=glide([[x0,ay],[sx(m.v),ay]],lt,1.6,1.2);g+=`<line x1="${x0}" y1="${ay}" x2="${x}" y2="${ay}" stroke="${LAMP}" stroke-width="8" stroke-linecap="round" opacity=".55"/><circle cx="${x}" cy="${ay}" r="${12*settle(lt,.9)}" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;return g},
 years(m,lt){let g=T(0,46,m.label,40,700,TXT,'start');const x0=40,x1=848,n=m.to-m.from,sx=y=>x0+(x1-x0)*(y-m.from)/n,ay=150;
  g+=`<line x1="${x0}" y1="${ay}" x2="${x1}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  for(let y=m.from;y<=m.to;y++){const q=pr(lt,.05+(y-m.from)*.09,.2,BACK),on=y===m.to;g+=`<g opacity="${clamp(q*2)}"><circle cx="${sx(y)}" cy="${ay}" r="${(on?18:10)*Math.max(.01,q)}" fill="${on?LAMP:FACE3}" stroke="${LINE}" stroke-width="3"/>${T(sx(y),ay+52,String(y),32,on?700:400,on?TXT:SUBC)}</g>`}
  const p=pr(lt,.2,.9),x=x0+(x1-x0)*p;g+=`<line x1="${x0}" y1="${ay}" x2="${x}" y2="${ay}" stroke="${LAMP}" stroke-width="8" stroke-linecap="round" opacity=".5"/>`+glide([[x0,ay],[x1,ay]],lt,1.6,1.2);return g}
};

MINI.grid100=(m,lt)=>{let g='';const cs=19,gp=2,x0=4,y0=10;   // 方陣約 210px（資料圖區高 232px 放得下的最大）   // v8.1：10×10 方陣（不再排兩條，避免讀成 83%）；亮 41 格、第 42 格亮 46%
 for(let i=0;i<100;i++){const r=Math.floor(i/10),c=i%10,x=x0+c*(cs+gp),y=y0+r*(cs+gp),u=lt-(.05+i*.008),fill=i<Math.floor(m.v)?1:(i===Math.floor(m.v)?m.v%1:0);
  g+=`<rect x="${x}" y="${y}" width="${cs}" height="${cs}" rx="3" fill="${FACE3}" stroke="${LINE}" stroke-width="1.2"/>`;if(fill>0&&u>0)g+=`<rect x="${x}" y="${y}" width="${(cs*fill*Math.min(1,u*6)).toFixed(1)}" height="${cs}" rx="3" fill="${LAMP}"/>`}
 g+=T(260,64,m.label,38,700,TXT,'start')+`<g opacity="${pr(lt,.9,.3)}">${T(260,140,m.big,64,700,HINT,'start')}${T(260,196,m.sub,32,400,TXT,'start')}</g>`;
 g+=glide([[x0,y0+4*(cs+gp)+cs/2],[x0+9*(cs+gp)+cs,y0+4*(cs+gp)+cs/2]],lt,1.6,1.2);return g};
MINI.pair=(m,lt)=>{let g=T(0,40,m.label,38,700,TXT,'start');m.items.forEach((it,i)=>{const cx=220+i*440,p=SPR(lt-.1-i*.2,.5,14),hop=-8*DECAY(lt-1.6-i*.5,5,14);if(lt<.1+i*.2)return;
  g+=`<g transform="translate(${cx},${(150+(1-p)*30+hop).toFixed(1)})" opacity="${clamp((lt-.1-i*.2)*6)}"><circle cx="-120" cy="-38" r="22" fill="${it.hi?LAMP:'#B98A6A'}"/><path d="M-150 30 q0 -46 30 -46 q30 0 30 46Z" fill="${it.hi?LAMP:'#B98A6A'}"/>${T(-70,-6,it.lab,34,700,TXT,'start')}${T(-70,48,it.txt,56,700,TXT,'start')}</g>`});
 if(m.ref)g+=`<g opacity="${pr(lt,.8,.3)}">${T(888,40,m.ref,32,400,TXT,'end')}</g>`;return g};
const SCV={
 hook(s,lt,d){let h=title(s.title,lt,{full:true});const u=pr(lt,.45,.4);
  h+=`<svg data-o="ul" class="abs" style="left:96px;top:398px" width="${s.ulw+10}" height="22"><path d="M4 12 C ${s.ulw*.25} 4, ${s.ulw*.55} 18, ${s.ulw} 8" stroke="${LAMP}" stroke-width="9" fill="none" stroke-linecap="round" ${draw(u)}/></svg>`;
  h+=tag(s.tag,lt,.5,430);
  const bu=lt-.42;let bdy=bu<=0?0:bu<.08?18*Math.pow(bu/.08,2):18*(1-SPR(bu-.08,.3,22));for(let b=1.8;b<lt&&b<14;b+=2.0)bdy+=10*Math.abs(DECAY(lt-b,5,13));   // v8.1：鉤子大字下壓 18px 回彈；1.8、3.8…秒再輕跳一次
  h+=`<div data-o="big" class="abs bignum" style="top:${(492+bdy).toFixed(1)}px">${esc(s.big)}</div>`;   // v8.1：下壓 18px 不碰資料圖（上緣 734），回彈不碰標籤（下緣 482）
  h+=box('chart',734,232,MINI[s.mini.type](s.mini,lt),lt,d,{});
  h+=ILLbox(s,lt,d,978,528);return h},
 stack(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.stack,W=808,x0=40,tot=c.segs.reduce((a,b)=>a+b.v,0),y=170;let g=T(x0,70,c.label,40,700,TXT,'start'),x=x0;
  c.segs.forEach((sg,i)=>{const p=pr(lt,.1+i*.45,.5,BACK),w=W*sg.v/tot,ww=w*Math.min(1.02,p);
   g+=`<rect x="${x}" y="${y}" width="${Math.max(0,ww).toFixed(1)}" height="120" rx="${i?0:16}" fill="${sg.hi?LAMP:'#B98A6A'}" ${sg.dash?'opacity=".9"':''}/>`;
   if(i)g+=`<line x1="${x}" y1="${y-10}" x2="${x}" y2="${y+130}" stroke="${FACE3}" stroke-width="6" opacity="${clamp(p*3)}"/>`;
   const q=pr(lt,.45+i*.45,.3);g+=`<g opacity="${q}" transform="translate(0,${(1-q)*12})">${T(x+w/2,y+76,sg.val,44,700,'#FFFFFF')}${T(x+w/2,y+190,sg.lab,36,700,TXT)}${sg.lab2?T(x+w/2,y+236,sg.lab2,32,400,SUBC):''}</g>`;x+=w});
  g+=sweepBar(x0,y,W,120,lt,2.3);
  g+=`<g opacity="${pr(lt,1.1,.35)}"><line x1="${x0}" y1="${y+300}" x2="${x0+W}" y2="${y+300}" stroke="${LINE}" stroke-width="3"/><line x1="${x0}" y1="${y+286}" x2="${x0}" y2="${y+314}" stroke="${LINE}" stroke-width="3"/><line x1="${x0+W}" y1="${y+286}" x2="${x0+W}" y2="${y+314}" stroke="${LINE}" stroke-width="3"/>${T(x0+W/2,y+370,c.total,44,700,TXT)}</g>`;
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,84,c.em.txt,40,SPR(lt-1.45,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 gantt(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.gantt,x0=200,x1=820,sx=v=>x0+(x1-x0)*(v-c.lo)/(c.hi-c.lo);let g='';
  g+=`<line x1="${x0}" y1="90" x2="${x1}" y2="90" stroke="${LINE}" stroke-width="3" opacity="${pr(lt,0,.3)}"/>`;
  c.ticks.forEach((v,i)=>{g+=`<g opacity="${pr(lt,.04*i,.25)}"><line x1="${sx(v)}" y1="80" x2="${sx(v)}" y2="100" stroke="${LINE}" stroke-width="2"/>${T(sx(v),60,c.tl[i],32,400,SUBC)}<line x1="${sx(v)}" y1="110" x2="${sx(v)}" y2="${140+(c.rows.length-1)*(c.step||170)+100}" stroke="${LINE}" stroke-width="1.5" stroke-dasharray="4 8" opacity=".35"/></g>`});
  c.rows.forEach((r,i)=>{const y=140+i*(c.step||170),a=.2+i*.55;g+=`<g opacity="${pr(lt,a,.25)}">${T(0,y+60,r.lab,38,700,TXT,'start')}${r.lab2?T(0,y+104,r.lab2,32,400,SUBC,'start'):''}</g>`;
   r.segs.forEach((sg,j)=>{const p=pr(lt,a+j*.2,.55,BACK),w=(sx(sg.to)-sx(sg.from))*Math.min(1.02,p);const fill=sg.kind==='grace'?(r.hi?LAMP:'#E9B98A'):sg.kind==='pay'?'#B98A6A':FACE3;
    g+=`<rect x="${sx(sg.from)}" y="${y+12}" width="${Math.max(0,w).toFixed(1)}" height="76" rx="12" fill="${fill}" ${sg.kind==='open'?`stroke="${LINE}" stroke-width="2.5" stroke-dasharray="10 8"`:''}/>`;
    if(sg.lab)g+=`<g opacity="${pr(lt,a+j*.2+.4,.25)}">${T((sx(sg.from)+sx(sg.to))/2,y+62,sg.lab,34,700,sg.kind==='open'?TXT:'#FFFFFF')}</g>`})});
  if(c.em){const e=c.em;g+=bracketH(sx(e.from),sx(e.to),e.y,pr(lt,1.45,.5),e.txt,e.below)}
  if(c.foot)g+=`<g opacity="${pr(lt,1.1,.3)}">${T(444,c.footY||640,c.foot,34,400,TXT)}</g>`;
  {const hr=c.rows.findIndex(r=>r.hi);if(hr>=0){const sg=c.rows[hr].segs[0];g+=sweepBar(sx(sg.from),140+hr*(c.step||170)+12,sx(sg.to)-sx(sg.from),76,lt,2.4)}}
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 versus(s,lt,d){let h=head(s,lt,{tagAt:.1})+ILLbox(s,lt,d,392,300);const pa=pr(lt,.05,.4,BACK),pb=pr(lt,.5,.42,BACK);let g='';const top=12,ht=600;
  [[s.a,pa,false,0],[s.b,pb,true,452]].forEach(([c,p,hi,x])=>{const dy=(1-clamp(p))*50;
   g+=`<g opacity="${clamp(p*1.6)}" transform="translate(0,${dy})"><rect x="${x+8}" y="${top}" width="420" height="${ht}" rx="28" fill="${hi?FACE3:FACE}" stroke="${hi?LAMP:LINE}" stroke-width="${hi?4:3}" ${hi?'':'stroke-dasharray="12 10"'}/>`+
   T(x+218,top+80,c.k,38,700,hi?HINT:SUBC)+c.lines.map((l,i)=>T(x+218,top+220+i*92,l,c.fs||64,700,TXT)).join('')+T(x+218,top+ht-42,c.foot,32,400,SUBC)+`</g>`});
  const ar=pr(lt,1.25,.45),ah=pr(lt,1.55,.2,BACK);
  if(ar>0)g+=`<path d="M300 ${top+ht/2+70} C 380 ${top+ht/2+40}, 520 ${top+ht/2+40}, 590 ${top+ht/2+70}" fill="none" stroke="${LAMP}" stroke-width="7" stroke-linecap="round" ${draw(ar)}/><path d="M572 ${top+ht/2+48} L596 ${top+ht/2+72} L566 ${top+ht/2+82}" fill="none" stroke="${LAMP}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="${clamp(ah*2)}"/>`;
  {const bx=(a,b,c,d,u)=>Math.pow(1-u,3)*a+3*Math.pow(1-u,2)*u*b+3*(1-u)*u*u*c+u*u*u*d,pts=[];for(let k=0;k<=12;k++){const u=k/12;pts.push([bx(300,380,520,590,u),bx(top+ht/2+70,top+ht/2+40,top+ht/2+40,top+ht/2+70,u)])}g+=glide(pts,lt,2.2,1.1)}   // 第三拍：光點沿箭頭重複流過
  g+=`<g opacity="${pr(lt,1.0,.3)}" transform="translate(0,${(1-pr(lt,1.0,.3))*16})">${T(444,top+ht+66,s.mid,40,700,TXT)}</g>`;
  g+=capsule(660,top+ht+136,s.emw||300,76,s.em,38,SPR(lt-1.9,.45,16));
  h+=box('chart',708,792,g,lt,d,{});return h},
 card(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.card,cp=pr(lt,0,.4,BACK),val=c.to*EO((lt-.15)/.95),sc=settle(lt,.9);
  let g=`<g opacity="${clamp(cp*1.5)}" transform="translate(0,${(1-clamp(cp))*30})"><rect x="64" y="20" width="760" height="440" rx="32" fill="${FACE3}" stroke="${LAMP}" stroke-width="4"/>`+T(444,110,c.lab,44,400,TXT)+(c.foot?T(444,420,c.foot,34,400,SUBC):'')+`</g>`;
  g+=glow(444,290,230,pr(lt,.95,.35)*.7);
  g+=`<g transform="translate(444,340) scale(${sc.toFixed(3)})">${T(0,0,(c.pre||'')+F1(Math.max(0,val),c.dec)+(c.unit||''),c.fs||170,700,TXT)}</g>`;
  if(c.bar){const bx=124,bw=640,by=c.by||510,bp=pr(lt,.3,.9),r=c.bar.v/c.bar.max;
   g+=`<g opacity="${pr(lt,.2,.3)}"><rect x="${bx}" y="${by}" width="${bw}" height="44" rx="8" fill="none" stroke="${LINE}" stroke-width="2"/><rect x="${bx}" y="${by}" width="${bw*r*bp}" height="44" rx="8" fill="${LAMP}" opacity=".85"/>`+T(bx,by+86,c.bar.l0,34,400,SUBC,'start')+T(bx+bw,by+86,c.bar.l1,34,400,SUBC,'end')+`</g>`+sweepBar(bx,by,bw*r,44,lt,2.2)}
  if(!c.bar)g+=glide([[100,460],[788,460]],lt,2.0,1.2);
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,80,c.em.txt,38,SPR(lt-1.4,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 gauge(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.gauge,cx=444,cy=c.cy||400,R=320;let g='';
  const ang=v=>Math.PI*(1-(v-c.lo)/(c.hi-c.lo)),pt=(v,r)=>[cx+r*Math.cos(ang(v)),cy-r*Math.sin(ang(v))];
  const ap=pr(lt,0,.6);const a0=pt(c.lo,R),a1=pt(c.lo+(c.hi-c.lo)*ap,R);g+=`<path d="M${a0[0]} ${a0[1]} A ${R} ${R} 0 0 1 ${a1[0].toFixed(1)} ${a1[1].toFixed(1)}" fill="none" stroke="${FACE}" stroke-width="56" stroke-linecap="round"/>`;
  c.ticks.forEach((v,i)=>{const q=pr(lt,.1+i*.06,.25),p1=pt(v,R-44),p2=pt(v,R-70),pl=pt(v,R-118);g+=`<g opacity="${q}"><line x1="${p1[0]}" y1="${p1[1]}" x2="${p2[0]}" y2="${p2[1]}" stroke="${LINE}" stroke-width="3"/>${T(pl[0],pl[1]+12,String(v)+(c.unit||''),32,400,SUBC)}</g>`});
  // 指針：機動利率＝會動的指針；0.4 甩到 0.775，阻尼擺盪；第二拍 1.9 再輕推一次（示意「會隨基準調整」，振幅小、衰減）
  const v=c.lo+(c.v-c.lo)*SPR(lt-.35,.32,9)+(c.hi-c.lo)*.035*DECAY(lt-1.9,2.6,9),pn=pt(v,R-140);
  g+=`<line x1="${cx}" y1="${cy}" x2="${pn[0].toFixed(1)}" y2="${pn[1].toFixed(1)}" stroke="${TXT}" stroke-width="10" stroke-linecap="round" opacity="${clamp((lt-.3)*8)}"/><circle cx="${cx}" cy="${cy}" r="24" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  {const pts=[];for(let k=0;k<=16;k++){pts.push(pt(c.lo+(c.v-c.lo)*k/16,R))}g+=glide(pts,lt,2.4,1.2)}
  const vp=pr(lt,.9,.3);g+=`<g opacity="${vp}">${T(cx,cy+96,c.val,64,700,TXT)}${T(cx,cy+146,c.lab,34,400,SUBC)}</g>`;
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,76,c.em.txt,36,SPR(lt-1.4,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 vbars(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.vbars,n=c.rows.length,bw=c.bw||136,gap=(808-n*bw)/(n-1),base=560,Hh=400;let g=T(40,60,c.label,36,400,SUBC,'start');
  g+=`<line x1="20" y1="${base}" x2="868" y2="${base}" stroke="${LINE}" stroke-width="3"/>`;
  c.rows.forEach((r,i)=>{const x=40+i*(bw+gap),p=pr(lt,.1+i*.16,.55,BACK),hh=Hh*(r.v-c.lo)/(c.hi-c.lo)*Math.min(1.03,p);
   g+=`<rect x="${x}" y="${(base-hh).toFixed(1)}" width="${bw}" height="${Math.max(0,hh).toFixed(1)}" rx="10" fill="${r.hi?LAMP:'#B98A6A'}" ${r.dash?`fill-opacity=".35" stroke="${LAMP}" stroke-width="3" stroke-dasharray="10 8"`:''}/>`;
   const q=pr(lt,.45+i*.16,.25);g+=`<g opacity="${q}">${T(x+bw/2,base-Hh*(r.v-c.lo)/(c.hi-c.lo)-20,r.txt,36,700,TXT)}</g>${T(x+bw/2,base+50,r.lab,34,r.hi?700:400,r.hi?TXT:SUBC)}`});
  if(c.base0)g+=T(868,base+96,c.base0,32,400,SUBC,'end');
  if(c.em){const e=c.em;g+=capsule(e.x,e.y,e.w,80,e.txt,38,SPR(lt-1.45,.45,16))}
  const last=c.rows.length-1,lx=40+last*(bw+gap);g+=sweepBar(lx,base-Hh*(c.rows[last].v-c.lo)/(c.hi-c.lo),bw,Hh*(c.rows[last].v-c.lo)/(c.hi-c.lo),lt,2.3);
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 slope(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.slope,xa=190,xb=700,base=560,Hh=420,y=v=>base-Hh*(v-c.lo)/(c.hi-c.lo);let g='';
  g+=`<line x1="${xa}" y1="${base}" x2="${xa}" y2="${c.ems?190:60}" stroke="${LINE}" stroke-width="2" opacity=".35"/><line x1="${xb}" y1="${base}" x2="${xb}" y2="${c.ems?190:60}" stroke="${LINE}" stroke-width="2" opacity=".35"/><line x1="40" y1="${base}" x2="848" y2="${base}" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(xa,base+50,c.a.x,34,400,SUBC)+T(xb,base+50,c.b.x,34,700,TXT)+(c.base0?T(848,36,c.base0,32,400,SUBC,'end'):'');
  const p=pr(lt,.3,.7),ya=y(c.a.v),yb=y(c.b.v),xe=xa+(xb-xa)*p,ye=ya+(yb-ya)*p;
  g+=`<g opacity="${pr(lt,0,.3)}"><circle cx="${xa}" cy="${ya}" r="20" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>${T(xa-36,ya+14,c.a.txt,44,700,TXT,'end')}</g>`;
  if(p>0)g+=`<line x1="${xa}" y1="${ya}" x2="${xe}" y2="${ye}" stroke="${LAMP}" stroke-width="12" stroke-linecap="round"/><circle cx="${xe}" cy="${ye}" r="${22*settle(lt,1.0)}" fill="${LAMP}"/>`;
  g+=`<g opacity="${pr(lt,.95,.3)}">${c.b.above?T(xb,yb-40,c.b.txt,44,700,TXT):T(xb+36,yb+14,c.b.txt,44,700,TXT,'start')}</g>`;
  if(c.ems)c.ems.forEach((e,i)=>{g+=capsule(e.x,e.y,e.w,80,e.txt,38,SPR(lt-1.45-i*.3,.45,16))});
  if(c.em){const e=c.em;g+=e.kind==='cap'?capsule(e.x,e.y,e.w,80,e.txt,38,SPR(lt-1.45,.45,16)):bracketV(xb+e.dx,Math.min(ya,yb),Math.max(ya,yb),pr(lt,1.45,.5),e.txt,e.side||1)}
  // 第三拍：光點沿線流一次
  g+=glide([[xa,ya],[xb,yb]],lt,2.2,1.2);
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 people(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.people,cols=c.cols||9,sz=c.sz||80,x0=(888-cols*sz)/2,y0=70;let g=T(444,40,c.legend,34,400,SUBC);
  let k=0;c.groups.forEach((gr,gi)=>{for(let i=0;i<gr.n;i++,k++){const col=k%cols,row=Math.floor(k/cols),x=x0+col*sz+sz/2,y=y0+row*(sz+(c.vgap||18))+sz/2,u=lt-(.1+k*.035),sp=SPR(u,.42,18);if(u<=0)continue;
   const f=gr.hi?LAMP:'#B98A6A',part=(i===gr.n-1&&gr.part)?gr.part:1;
   g+=`<g transform="translate(${x},${(y+(1-sp)*-26).toFixed(1)}) scale(${c.isc||1})" opacity="${clamp(u*8)}"><circle cx="0" cy="-20" r="13" fill="${f}"/><path d="M-20 26 q0 -32 20 -32 q20 0 20 32Z" fill="${f}"/>${part<1?`<rect x="${(-22+44*part).toFixed(1)}" y="-36" width="${(44*(1-part)).toFixed(1)}" height="64" fill="${FACE3}" opacity=".85"/>`:''}</g>`}});
  g+=glide([[x0+sz/2,y0+sz+4],[x0+cols*sz-sz/2,y0+sz+4]],lt,2.0,1.2);
  const rows=Math.ceil(k/cols),ly=y0+rows*(sz+(c.vgap||18))+40;
  c.groups.forEach((gr,gi)=>{const q=pr(lt,1.0+gi*.15,.3);g+=`<g opacity="${q}"><rect x="${60+gi*410}" y="${ly}" width="34" height="34" rx="8" fill="${gr.hi?LAMP:'#B98A6A'}"/>${T(110+gi*410,ly+30,gr.lab,36,700,TXT,'start')}</g>`});
  if(c.em)g+=capsule(444,ly+120,c.em.w,84,c.em.txt,42,SPR(lt-1.5,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 steps(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.steps,n=c.rows.length;let g='';
  c.rows.forEach((r,i)=>{const y=90+i*200,a=.1+i*.4,p=pr(lt,a,.35,BACK);
   if(i<n-1){const lp=pr(lt,a+.25,.35);g+=`<line x1="90" y1="${y+64}" x2="90" y2="${y+64+136*lp}" stroke="${r.done?LAMP:LINE}" stroke-width="6" ${r.done?'':'stroke-dasharray="10 10"'}/>`}
   g+=`<g opacity="${clamp(p*1.5)}" transform="translate(${(1-clamp(p))*-30},0)"><circle cx="90" cy="${y}" r="52" fill="${r.done?LAMP:FACE3}" stroke="${r.done?LAMP:LINE}" stroke-width="4" ${r.done?'':'stroke-dasharray="10 8"'}/>`+
    `<rect x="170" y="${y-62}" width="690" height="124" rx="22" fill="${r.done?FACE3:FACE}" stroke="${LINE}" stroke-width="2.5"/>${T(200,y-6,r.lab,42,700,TXT,'start')}${T(200,y+40,r.sub,32,400,SUBC,'start')}</g>`;
   const ck=pr(lt,a+.3,.3);if(r.done&&ck>0)g+=`<path d="M66 ${y} l18 18 l32 -36" fill="none" stroke="#FFFFFF" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" ${draw(ck)}/>`;
   if(!r.done)g+=`<g opacity="${pr(lt,a+.3,.3)}">${T(90,y+20,'?',56,700,HINT)}</g>`});
  g+=glide([[90,90],[90,90+(n-1)*200]],lt,2.0,1.2);
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,76,c.em.txt,36,SPR(lt-1.5,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 hbars(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.hbars,x0=c.x0||260,W=c.w||560,rh=c.rh||96,gap=c.gap||40;let g=c.label?T(888,40,c.label,32,400,SUBC,'end'):'';
  c.rows.forEach((r,i)=>{const y=(c.y0||70)+i*(rh+gap),p=pr(lt,.1+i*.16,.55,BACK),w=W*(r.v/c.vmax)*Math.min(1.03,p);
   g+=T(0,y+rh/2+14,r.lab,38,r.hi?700:400,TXT,'start')+`<rect x="${x0}" y="${y}" width="${Math.max(0,w).toFixed(1)}" height="${rh}" rx="12" fill="${r.hi?LAMP:'#B98A6A'}" ${r.dash?`fill-opacity=".3" stroke="${LINE}" stroke-width="2.5" stroke-dasharray="10 8"`:''}/>`;
   const q=pr(lt,.5+i*.16,.25);g+=`<g opacity="${q}">${T(x0+W*r.v/c.vmax+16,y+rh/2+14,r.txt,40,700,TXT,'start')}</g>`});
  if(c.note)g+=`<g opacity="${pr(lt,1.0,.3)}">${T(0,(c.y0||70)+c.rows.length*(rh+gap)+30,c.note,34,400,TXT,'start')}</g>`;
  if(c.em){const e=c.em;if(e.kind==='bv')g+=bracketV(e.x,e.y0,e.y1,pr(lt,1.45,.5),e.txt,e.side||1);else g+=capsule(e.x,e.y,e.w,80,e.txt,38,SPR(lt-1.45,.45,16))}
  const hi=c.rows.findIndex(r=>r.hi);if(hi>=0){const y=(c.y0||70)+hi*(rh+gap);g+=sweepBar(x0,y,W*c.rows[hi].v/c.vmax,rh,lt,2.3)}
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 dumbbell(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.dumbbell,x0=60,x1=828,sx=v=>x0+(x1-x0)*(v-c.lo)/(c.hi-c.lo),ay=c.ay||300;let g='';
  g+=`<line x1="${x0}" y1="${ay}" x2="${x0+(x1-x0)*pr(lt,0,.45)}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  c.ticks.forEach((v,i)=>{g+=`<g opacity="${pr(lt,.05+i*.05,.25)}"><line x1="${sx(v)}" y1="${ay-10}" x2="${sx(v)}" y2="${ay+10}" stroke="${LINE}" stroke-width="2"/>${T(sx(v),ay+52,(c.tl?c.tl[i]:String(v)+(c.unit||'')),32,400,SUBC)}</g>`});
  const pa=pr(lt,.3,.5,BACK),pb=pr(lt,.55,.5,BACK),A=c.a,B=c.b,xa=sx(A.v),xb=sx(B.v);
  const lp=pr(lt,.8,.4);if(lp>0)g+=`<line x1="${xa}" y1="${ay}" x2="${xa+(xb-xa)*lp}" y2="${ay}" stroke="${LAMP}" stroke-width="12" stroke-linecap="round" opacity=".6"/>`;
  [[A,xa,pa,-1],[B,xb,pb,1]].forEach(([P,x,p,up])=>{if(p<=0)return;g+=`<circle cx="${x}" cy="${ay}" r="${(22*Math.min(1.1,p)).toFixed(1)}" fill="${P.hi?LAMP:'#B98A6A'}" stroke="${LINE}" stroke-width="3"/><g opacity="${clamp(p)}">${T(x,ay-(P.up?130:-0)+(P.up?0:170),P.txt,56,700,TXT)}${T(x,ay-(P.up?82:-0)+(P.up?0:214),P.lab,34,400,SUBC)}</g>`});
  g+=glide([[xa,ay],[xb,ay]],lt,2.2,1.2);
  if(c.em)g+=bracketH(xa,xb,c.em.y||ay-200,pr(lt,1.45,.5),c.em.txt);
  if(c.axisLab)g+=`<g opacity="${pr(lt,.4,.3)}">${T(828,ay+104,c.axisLab,32,400,TXT,'end')}</g>`;
  if(c.foot)g+=`<g opacity="${pr(lt,1.0,.3)}">${T(444,ay+(c.footDy||150),c.foot,34,400,TXT)}</g>`;
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 lollipop(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.lollipop,x0=280,W=c.w||440,sx=v=>x0+W*v/c.vmax,ST=c.step||170;let g='';
  g+=`<line x1="${x0}" y1="40" x2="${x0}" y2="${80+c.rows.length*ST}" stroke="${LINE}" stroke-width="3"/>`;
  c.ticks.forEach((v,i)=>g+=`<g opacity="${pr(lt,.05*i,.25)}"><line x1="${sx(v)}" y1="40" x2="${sx(v)}" y2="${80+c.rows.length*ST}" stroke="${LINE}" stroke-width="1.5" stroke-dasharray="4 8" opacity=".4"/>${T(sx(v),130+c.rows.length*ST,v+(c.unit!=null?c.unit:'%'),32,400,SUBC)}</g>`);
  c.rows.forEach((r,i)=>{const y=130+i*ST,p=pr(lt,.15+i*.3,.6),x=x0+(sx(r.v)-x0)*p;g+=T(0,y+14,r.lab,38,r.hi?700:400,TXT,'start')+`<line x1="${x0}" y1="${y}" x2="${x}" y2="${y}" stroke="${r.hi?LAMP:'#B98A6A'}" stroke-width="10" stroke-linecap="round"/>`;
   if(p>0)g+=`<circle cx="${x}" cy="${y}" r="${(26*settle(lt,.75+i*.3)).toFixed(1)}" fill="${r.hi?LAMP:'#B98A6A'}"/>`;g+=`<g opacity="${pr(lt,.7+i*.3,.25)}">${T(sx(r.v)+44,y+14,r.txt,42,700,TXT,'start')}</g>`});
  c.rows.forEach((r,i)=>{g+=glide([[x0,130+i*ST],[sx(r.v),130+i*ST]],lt,2.0+i*.6,c.once?99:1.2)});
  if(c.em){const e=c.em;g+=bracketV(e.x,130,300,pr(lt,1.45,.5),e.txt,e.side||1)}
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 donut(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.donut,cx=300,cy=300,R=210,p=pr(lt,.1,.9),a=2*Math.PI*c.v/100*p;let g='';
  g+=`<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="${FACE}" stroke-width="80"/>`;
  if(p>0){const x=cx+R*Math.sin(a),y=cy-R*Math.cos(a);g+=`<path d="M${cx} ${cy-R} A ${R} ${R} 0 ${a>Math.PI?1:0} 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${LAMP}" stroke-width="80"/>`}
  for(let i=0;i<10;i++){const b=i/10*2*Math.PI;g+=`<line x1="${cx+(R-40)*Math.sin(b)}" y1="${cy-(R-40)*Math.cos(b)}" x2="${cx+(R+40)*Math.sin(b)}" y2="${cy-(R+40)*Math.cos(b)}" stroke="${FACE3}" stroke-width="4"/>`}
  g+=`<g transform="translate(${cx},${cy+24}) scale(${settle(lt,1.0).toFixed(3)})">${T(0,0,F1(c.v*EO((lt-.1)/.9),2)+'%',70,700,TXT)}</g>`;
  if(!c.noglide){const n=16,pts=[];for(let k=0;k<=n;k++){const b=2*Math.PI*c.v/100*k/n;pts.push([cx+R*Math.sin(b),cy-R*Math.cos(b)])}g+=glide(pts,lt,2.0,1.2)}
  c.legend.forEach((l,i)=>{const q=pr(lt,.6+i*.2,.3);g+=`<g opacity="${q}"><rect x="580" y="${150+i*110}" width="40" height="40" rx="8" fill="${i?FACE:LAMP}" stroke="${LINE}" stroke-width="2"/>${T(636,184+i*110,l[0],36,700,TXT,'start')}${T(636,228+i*110,l[1],32,400,SUBC,'start')}</g>`});
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,80,c.em.txt,38,SPR(lt-1.45,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 band(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.band,x0=40,W=808,sx=v=>x0+W*v/c.max,y=200;let g='';
  c.grades.forEach((gr,i)=>{const p=pr(lt,.05+i*.15,.35);g+=`<g opacity="${p}"><rect x="${sx(gr.from)+2}" y="${y}" width="${(sx(gr.to)-sx(gr.from)-4)*Math.min(1,p*1.2)}" height="100" rx="10" fill="${gr.col}"/>${T((sx(gr.from)+sx(gr.to))/2,y+62,gr.lab,34,700,gr.dark?'#FFFFFF':TXT)}</g>`});
  c.ticks.forEach((v,i)=>g+=`<g opacity="${pr(lt,.4,.3)}">${T(sx(v),y+150,v+'%',32,400,SUBC)}</g>`);
  const p=pr(lt,.7,.7),v=c.v*p,mx=sx(v);if(p>0)g+=`<g><path d="M${mx} ${y-14} l-22 -36 h44Z" fill="${LAMP}" stroke="${LINE}" stroke-width="2.5"/><line x1="${mx}" y1="${y-14}" x2="${mx}" y2="${y+108}" stroke="${TXT}" stroke-width="5"/></g><g opacity="${pr(lt,1.3,.3)}">${T(mx,y-70,c.mark,48,700,TXT)}</g>`;
  if(!c.noglide)g+=glide([[x0,y+100],[sx(c.v),y+100]],lt,2.3,1.2);
  if(c.note)g+=`<g opacity="${pr(lt,.3,.3)}">${T(444,64,c.note,32,400,SUBC)}</g>`;
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,80,c.em.txt,38,SPR(lt-1.7,.45,16));
  if(c.foot)g+=`<g opacity="${pr(lt,1.0,.3)}">${T(444,y+260,c.foot,34,400,SUBC)}</g>`;
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 split2(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.split2,x0=40,W=808;let g=T(x0,56,c.l1,38,700,TXT,'start');const y=90,sg=c.segs;let x=x0;
  sg.forEach((q,i)=>{const p=pr(lt,.05+i*.35,.45,BACK),w=W*q.v/100;g+=`<rect x="${x}" y="${y}" width="${Math.max(0,w*Math.min(1.02,p)).toFixed(1)}" height="110" rx="${i?0:14}" fill="${q.hi?LAMP:FACE3}" ${q.hi?'':`stroke="${LINE}" stroke-width="2.5" stroke-dasharray="10 8"`}/>`+`<g opacity="${pr(lt,.35+i*.35,.25)}">${T(x+w/2,y+70,q.lab,40,700,q.hi?'#FFFFFF':TXT)}</g>`;x+=w});
  g+=T(x0,330,c.l2,38,700,TXT,'start');const n=c.years,cw=W/n;for(let i=0;i<n;i++){const u=lt-(.8+i*.045),sp=SPR(u,.45,18);if(u<=0)continue;
   g+=`<rect x="${(x0+i*cw+3).toFixed(1)}" y="${(370+(1-sp)*-20).toFixed(1)}" width="${(cw-6).toFixed(1)}" height="90" rx="8" fill="${i%5===4?'#B98A6A':'#E9B98A'}" opacity="${clamp(u*8)}"/>`}
  g+=glide([[x0+10,415],[x0+W-10,415]],lt,2.1,1.2);
  g+=`<g opacity="${pr(lt,1.8,.3)}">${T(x0,510,'第 1 年',32,400,SUBC,'start')}${T(x0+W,510,'第 '+n+' 年',32,400,SUBC,'end')}</g>`;
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,80,c.em.txt,38,SPR(lt-1.3,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 tiles(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.tiles;let g='';
  const st=c.step||200,th=c.th||170;c.rows.forEach((r,i)=>{const y=20+i*st,p=pr(lt,.1+i*.3,.4,BACK);g+=`<g opacity="${clamp(p*1.5)}" transform="translate(${(1-clamp(p))*60},0)"><rect x="20" y="${y}" width="848" height="${th}" rx="26" fill="${i===c.hi?FACE3:FACE}" stroke="${i===c.hi?LAMP:LINE}" stroke-width="${i===c.hi?4:2.5}"/>${T(70,y+th/2-9,r.lab,38,700,TXT,'start')}${T(70,y+th/2+41,r.sub,32,400,SUBC,'start')}`+
   `<g transform="translate(818,${y+th/2+25}) scale(${settle(lt,.5+i*.3).toFixed(3)})">${T(0,0,r.val,64,700,TXT,'end')}</g></g>`});
  {const y=20+(c.hi||0)*st;g+=glide([[40,y],[848,y]],lt,2.0,1.2)}
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,76,c.em.txt,36,SPR(lt-1.5,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 odometer(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.odo,str=F1(c.v),n=str.length,cw=104,x0=444-n*cw/2;let g=T(444,60,c.lab,40,700,TXT);let di=0;
  for(let i=0;i<n;i++){const ch=str[i],x=x0+i*cw;if(ch===','){g+=T(x+cw/2,330,',',110,700,TXT);continue}
   const dig=+ch,p=clamp((lt-.15-di*.12)/(.9+di*.1)),e=1-Math.pow(1-p,3),roll=(dig+10*(2+(n-i)%3))*e,base=Math.floor(roll),fr=roll-base;di++;
   g+=`<rect x="${x+6}" y="140" width="${cw-12}" height="250" rx="16" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><clipPath id="od${i}"><rect x="${x+6}" y="146" width="${cw-12}" height="238" rx="12"/></clipPath><g clip-path="url(#od${i})">`+
    T(x+cw/2,330-fr*170,String(base%10),130,700,TXT)+T(x+cw/2,330+170-fr*170,String((base+1)%10),130,700,TXT)+`</g>`}
  g+=glide([[x0+6,396],[x0+n*cw-6,396]],lt,2.0,1.2);
  g+=`<g opacity="${pr(lt,1.2,.3)}">${T(444,470,c.unit,44,700,TXT)}</g>`;
  if(c.em)g+=capsule(444,580,c.em.w,80,c.em.txt,38,SPR(lt-1.5,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 lanes(s,lt,d){let h=head(s,lt)+ILLbox(s,lt,d);const c=s.lanes,x0=40,x1=848,sx=v=>x0+(x1-x0)*(v-c.lo)/(c.hi-c.lo);let g='';
  g+=`<line x1="${x0}" y1="${c.rows.length*120+60}" x2="${x1}" y2="${c.rows.length*120+60}" stroke="${LINE}" stroke-width="3"/>`;
  c.ticks.forEach(v=>g+=`<g opacity="${pr(lt,.05,.3)}">${T(sx(v),c.rows.length*120+108,v+' 歲',32,400,SUBC)}</g>`);
  c.marks.forEach((m,i)=>{const p=pr(lt,1.1+i*.2,.35,BACK),x=sx(m.v),yb=c.rows.length*120+60;if(p<=0)return;g+=`<line x1="${x}" y1="${yb}" x2="${x}" y2="${yb-(c.rows.length*120+40)*Math.min(1,p)}" stroke="${LAMP}" stroke-width="5" stroke-dasharray="10 8"/><g opacity="${clamp(p)}">${T(x+(i?14:-14),yb+(i?156:156),m.lab,36,700,HINT,i?'start':'end')}</g>`});
  g+=glide([[x0,c.rows.length*120+60],[x1,c.rows.length*120+60]],lt,2.0,1.2);
  c.rows.forEach((r,i)=>{const y=20+i*120,p=pr(lt,.15+i*.25,.5,BACK),w=(sx(r.to)-sx(r.from))*Math.min(1.02,p);g+=`<rect x="${sx(r.from)}" y="${y}" width="${Math.max(0,w).toFixed(1)}" height="88" rx="14" fill="${r.col||'#E9B98A'}"/><g opacity="${pr(lt,.45+i*.25,.25)}">${T(sx(r.from)+24,y+58,r.lab,36,700,TXT,'start')}</g>`});
  if(c.em)g+=capsule(c.em.x,c.em.y,c.em.w,76,c.em.txt,36,SPR(lt-1.6,.45,16));
  h+=box('chart',CT,CH,g,lt,d,{});return h},
 ask(s,lt,d){let h=title(s.title,lt,{cls:'hint'})+tag(s.tag,lt,.3,306);h+=ILLbox(s,lt,d,392,500);
  let g='';s.recap.forEach((r,i)=>{const p=pr(lt,.15+i*.1,.4);g+=`<g opacity="${p}" transform="translate(${(1-p)*-40},0)"><rect x="20" y="${10+i*112}" width="848" height="92" rx="20" fill="${FACE}" stroke="${LINE}" stroke-width="2"/>${T(56,10+i*112+60,r[0],34,400,SUBC,'start')}${T(832,10+i*112+62,r[1],42,700,TXT,'end')}</g>`});
  const q=pr(lt,.65,.4,BACK),oy=s.recap.length*112+40;const cyc=!!s.btnCycle,alt=cyc&&lt>2.0?(Math.floor((lt-2.0)/.9)%2):-1,ac0=alt==0?LAMP:LINE,ac1=alt==1?LAMP:LINE,aw0=alt==0?5:3,aw1=alt==1?5:3;
  g+=`<g opacity="${clamp(q*1.5)}" transform="translate(0,${(1-clamp(q))*20})">${T(444,oy+20,'二選一',32,700,HINT)}`+
   `<rect x="40" y="${oy+44}" width="380" height="96" rx="48" fill="${FACE3}" stroke="${ac0}" stroke-width="${aw0}"/>${T(230,oy+106,s.opt[0],40,700,TXT)}`+
   `<rect x="468" y="${oy+44}" width="380" height="96" rx="48" fill="${FACE3}" stroke="${ac1}" stroke-width="${aw1}" stroke-dasharray="10 8"/>${T(658,oy+106,s.opt[1],40,700,TXT)}</g>`;
  // 第二拍：兩顆膠囊依序輕跳（位移，不縮放）
  const j1=-10*DECAY(lt-1.5,5,14)-(cyc&&lt>2.2?6*Math.max(0,Math.sin(Math.PI*((lt-2.2)%1.2)/.5))*((lt-2.2)%1.2<.5?1:0):0),j2=-10*DECAY(lt-1.75,5,14)-(cyc&&lt>2.8?6*Math.max(0,Math.sin(Math.PI*((lt-2.8)%1.2)/.5))*((lt-2.8)%1.2<.5?1:0):0);g=g.replace(`<rect x="40" y="${oy+44}"`,`<rect x="40" y="${(oy+44+j1).toFixed(1)}"`).replace(`<rect x="468" y="${oy+44}"`,`<rect x="468" y="${(oy+44+j2).toFixed(1)}"`);
  h+=box('chart',908,592,g,lt,d,{});return h},
 next(s,lt,d){let h=head(s,lt,{tagAt:.25})+ILLbox(s,lt,d);const p=pr(lt,.05,.45,BACK),rows=[0,1,2,3,4];
  let g=`<g opacity="${clamp(p*1.5)}" transform="translate(0,${(1-clamp(p))*30})"><rect x="104" y="40" width="680" height="560" rx="22" fill="${FACE}" stroke="${LINE}" stroke-width="3" stroke-dasharray="12 10"/>`+
   `<rect x="104" y="40" width="680" height="84" rx="22" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,96,s.slip,38,700,TXT)+`</g>`;
  rows.forEach(i=>{const q=pr(lt,.35+i*.09,.3);g+=`<g opacity="${q}">${i===0?T(160,236,s.row,36,400,TXT,'start'):''}<line x1="160" y1="${270+i*70}" x2="${160+(i===0?560:i%2?420:500)*q}" y2="${270+i*70}" stroke="${LINE}" stroke-width="2" opacity="${i?.35:.55}"/></g>`});
  if(lt>1.2){const u=lt-1.2,row=1+Math.floor(u/1.0)%4,k=(u%1.0)/.8;if(k<1)g+=`<line x1="160" y1="${270+row*70-14}" x2="${(160+300*EO(k)).toFixed(1)}" y2="${270+row*70-14}" stroke="${LAMP}" stroke-width="5" stroke-linecap="round" opacity="${(.55*(1-k*k)).toFixed(2)}"/><circle cx="${(160+300*EO(k)).toFixed(1)}" cy="${270+row*70-14}" r="7" fill="${LAMP}" opacity="${(.8*(1-k*k)).toFixed(2)}"/>`}   // 第三拍：還沒寫上的列，一行行有筆跡劃過（下集還沒公布）
  const pp=SPR(lt-.55,.45,16),qp=SPR(lt-.68,.38,18);let qr=-14*(1-clamp(qp));for(let b=1.6;b<lt&&b<14;b+=1.0)qr+=12*DECAY(lt-b,4.5,14);g+='<g data-em="1">';
  if(pp>0)g+=`<g transform="translate(677,200) scale(${Math.max(.01,pp).toFixed(3)})"><rect x="-66" y="-48" width="132" height="96" rx="48" fill="#F6D9B8" stroke="#E7B07A" stroke-width="2"/></g>`;
  if(qp>0)g+=`<g transform="translate(677,229) rotate(${qr.toFixed(1)}) scale(${Math.max(.01,qp).toFixed(3)})" opacity="${clamp((lt-.68)*12)}">${T(0,0,'?',84,700,HINT)}</g>`;g+='</g>';
  h+=box('chart',CT,660,g,lt,d,{});return h},
