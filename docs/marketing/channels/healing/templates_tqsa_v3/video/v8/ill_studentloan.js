// 談晴說礙 11/17 學貸影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261117v_studentloan」）。
// 動作原則同 v4：面板固定不縮放不平移；物件預備→主動作→過衝→阻尼回彈；另有細小環境動作（避免靜止段 >1.2 秒）。
const ILL={
 // s1 銀行利率電子看板：數字由 1.775% 滾到 0.775%（0.3–1.1）、看板邊燈依序亮、櫃台叫號燈閃一次、申請書被風掀角
 rateboard:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-110}" width="888" height="110" fill="#E4D3B8"/>`;
  g+=`<rect x="90" y="40" width="708" height="300" rx="22" fill="#4A4744" stroke="${LINE}" stroke-width="4"/><rect x="112" y="62" width="664" height="256" rx="14" fill="#3A3836"/>`;
  g+=T(444,118,'就學貸款・學生負擔利率',34,700,'#F3DDB8');
  const p=EO((t-.3)/.8),v=1.775-1*p,str=v.toFixed(3)+'%';g+=`<clipPath id="rbc"><rect x="130" y="140" width="628" height="160"/></clipPath><g clip-path="url(#rbc)">`;
  const jit=t>.3&&t<1.1?Math.sin(t*90)*3:0;g+=T(444,262+jit,str,130,700,p>.98?'#F4B860':'#FFE9B8')+`</g>`;
  for(let i=0;i<14;i++){const x=120+i*49,on=clamp((t-.2-i*.05)*6);g+=`<circle cx="${x}" cy="52" r="6" fill="#F4B860" opacity="${(.25+.75*on*(.75+.25*tw(t,i,3))).toFixed(2)}"/>`}
  // 叫號燈
  const bl=t>1.3&&t<1.6?1:0;g+=`<rect x="650" y="${h-170}" width="120" height="64" rx="12" fill="${bl?'#F4B860':'#D8C6A8'}" stroke="${LINE}" stroke-width="3"/>`+T(710,h-126,'032',32,700,TXT)+(bl?glow(710,h-138,90,.5):'');
  // 申請書（掀角：衰減擺動）
  const fl=10*DECAY(t-.6,1.6,7)+6*DECAY(t-1.9,1.8,8);g+=`<g transform="translate(130,${h-150})"><rect x="0" y="0" width="300" height="120" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3" transform="rotate(-4)"/>`+T(140,46,'申請書',32,700,TXT)+`<line x1="24" y1="74" x2="250" y2="62" stroke="${LINE}" stroke-width="2" opacity=".5"/><path d="M270 ${-20} l30 ${(18+fl).toFixed(1)} l-34 4Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<path d="M560 ${h-60} q12 -30 0 -60" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.25+.2*tw(t,0,2.4)).toFixed(2)}"/><rect x="530" y="${h-60}" width="60" height="44" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  return g},
  sfx(t0,s,E){for(let k=0;k<6;k++)E(t0+.3+k*.13,'tick',{g:.5});E(t0+1.1,'bell',{n:[19],g:.45});E(t0+1.3,'click')}},
 // s2 玻璃罐：學生投一枚小硬幣（0.775），政府那枚大硬幣「1%」由上方落下、彈兩下、罐子晃一下
 coinjar:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#E4D3B8"/>`;
  const sw=2.5*DECAY(t-1.05,3,14);g+=`<g transform="rotate(${sw.toFixed(2)} 444 ${h-80})"><path d="M330 ${h-80} v-200 q0 -30 30 -36 h168 q30 6 30 36 v200Z" fill="#F5F0E6" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/><rect x="350" y="${h-336}" width="188" height="28" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  // 罐底已有的硬幣
  for(let i=0;i<4;i++)g+=`<ellipse cx="${384+i*40}" cy="${h-98}" rx="26" ry="10" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`;
  const c1=SPR(t-.15,.5,14),y1=h-420+(h-140-(h-420))*c1;if(t>.15)g+=`<g transform="translate(410,${y1.toFixed(1)})"><circle r="24" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/>${T(0,10,'學',26+6,700,TXT)}</g>`;
  const fall=clamp((t-.7)/.35),y2=fall<1?(h-460)+(h-180-(h-460))*fall*fall:(h-180)-26*Math.abs(DECAY(t-1.05,4,11));if(t>.7)g+=`<g transform="translate(474,${y2.toFixed(1)})"><circle r="40" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,13,'1%',34,700,'#FFFFFF')}</g>`;
  g+=`</g>`;
  [[372,h-260],[520,h-230],[430,h-300]].forEach(([x,y],i)=>g+=sparkle(x,y,10,.35+.4*tw(t,i*2,3.2)));
  return g},
  sfx(t0,s,E){E(t0+.3,'tick');E(t0+1.05,'thump',{g:.4});E(t0+1.25,'tick',{g:.7})}},
 // s3 畢業後的路：小路延伸、路邊「還款」路牌被往遠處推一格（1 年→2 年）、路燈依序亮、遠山雲飄
 road:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/>`;
  const cl=(t*14)%1000;g+=`<g opacity=".7"><ellipse cx="${(200+cl)%1000-60}" cy="70" rx="70" ry="22" fill="#FFFDF8"/><ellipse cx="${(620+cl*.7)%1000-60}" cy="96" rx="54" ry="18" fill="#FFFDF8"/></g>`;
  g+=`<path d="M0 ${h-150} q220 -60 444 -40 q220 20 444 -30 V${h} H0Z" fill="#D9C4A0"/><path d="M380 ${h} L470 ${h-140} L520 ${h-140} L700 ${h}Z" fill="#C9B28C"/>`;
  for(let i=0;i<5;i++){const y=h-20-i*26;g+=`<rect x="${532-i*8}" y="${y}" width="${30-i*4}" height="6" fill="#FFFDF8" opacity=".8"/>`}
  // 學士帽不用（輪播已用）；改畫一雙新皮鞋在路口
  g+=`<g transform="translate(240,${h-70})"><path d="M0 0 h70 q20 0 20 18 h-90Z" fill="#6E4636" stroke="${LINE}" stroke-width="2"/><path d="M96 6 h70 q20 0 20 18 h-90Z" fill="#6E4636" stroke="${LINE}" stroke-width="2"/></g>`;
  // 路牌：0.5 往右遠處滑一格（預備往左一點→滑出→過衝回彈）
  const pre=t>.4&&t<.55?-8*Math.sin(Math.PI*(t-.4)/.15):0,mv=SPR(t-.55,.5,11),x=560+150*mv+pre,sc=1;
  g+=`<g transform="translate(${x.toFixed(1)},${(h-150-10*mv).toFixed(1)}) scale(${sc.toFixed(3)})"><line x1="0" y1="0" x2="0" y2="-150" stroke="${LINE}" stroke-width="7"/><rect x="-74" y="-206" width="148" height="66" rx="10" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>${T(0,-160,'還款',34,700,'#FFFFFF')}</g>`;
  g+=`<g transform="translate(470,${h-150})"><line x1="0" y1="0" x2="0" y2="-120" stroke="${LINE}" stroke-width="6"/><rect x="-66" y="-170" width="132" height="58" rx="10" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,-130,'寬限',32,700,'#FFFFFF')}</g>`;
  [[110,h-160],[790,h-180]].forEach(([lx,ly],i)=>{const on=clamp((t-1.2-i*.25)*5);g+=(on>0?glow(lx,ly-110,60,.55*on):'')+`<line x1="${lx}" y1="${ly}" x2="${lx}" y2="${ly-100}" stroke="${LINE}" stroke-width="5"/><circle cx="${lx}" cy="${ly-108}" r="13" fill="${on>.5?'#F4B860':'#D8C6A8'}" stroke="${LINE}" stroke-width="2"/>`});
  return g},
  sfx(t0,s,E){E(t0+.55,'glide',{f0:500,f1:260,dur:.35,g:.12});E(t0+1.0,'thump',{g:.3});E(t0+1.2,'sparkle',{n:[24]});E(t0+1.45,'sparkle',{n:[26]})}},
 // s4 公告欄：公告紙被圖釘釘上（0.3）、右下角被風掀起又落下、放大鏡由右滑進停在「?」上
 notice:{draw(t,h){let g=`<rect x="40" y="24" width="808" height="${h-48}" rx="18" fill="#C9A27A" stroke="${LINE}" stroke-width="4"/><rect x="60" y="44" width="768" height="${h-88}" rx="10" fill="#D9B48C"/>`;
  g+=`<rect x="90" y="70" width="200" height="140" rx="4" fill="#F3EADB" transform="rotate(-5 190 140)" stroke="${LINE}" stroke-width="2"/><rect x="620" y="64" width="180" height="120" rx="4" fill="#EFE7D7" transform="rotate(4 710 124)" stroke="${LINE}" stroke-width="2"/>`;
  const drop=SPR(t-.15,.45,15),ty=-60*(1-drop),fl=14*DECAY(t-.9,1.8,8)+8*DECAY(t-2.2,2,8);
  g+=`<g transform="translate(0,${ty.toFixed(1)})" opacity="${clamp((t-.1)*6)}"><path d="M320 54 h250 v${(h-130).toFixed(0)} l-${(30+fl).toFixed(1)} 10 h-220Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(445,110,'就學貸款公告',32,700,TXT)}`;
  for(let i=0;i<4;i++)g+=`<line x1="346" y1="${146+i*34}" x2="${546-(i%2)*60}" y2="${146+i*34}" stroke="${LINE}" stroke-width="2" opacity=".45"/>`;g+=`<circle cx="445" cy="58" r="11" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  const mx=740-160*SPR(t-.8,.55,10),my=h-96+6*Math.sin(t*2.2);g+=`<g transform="translate(${mx.toFixed(1)},${my.toFixed(1)})"><circle r="46" fill="#FFF8EA" fill-opacity=".6" stroke="${LINE}" stroke-width="7"/><line x1="32" y1="32" x2="78" y2="78" stroke="${LINE}" stroke-width="12" stroke-linecap="round"/>${T(0,14,'?',40,700,HINT)}</g>`;
  return g},
  sfx(t0,s,E){E(t0+.35,'thump',{g:.3});E(t0+.9,'glide',{f0:700,f1:400,dur:.3,g:.08})}},
 // s5 書桌：檯燈「喀」一聲亮起（0.5，閃一下才穩）、書頁翻一頁（1.0）、鉛筆滾半圈停住、燈下塵光飄
 desklamp:{draw(t,h){let g=`<rect x="0" y="${h-110}" width="888" height="110" fill="#C9A27A"/><rect x="0" y="${h-118}" width="888" height="12" fill="#B48A60"/>`;
  const on=t<.5?0:t<.56?1:t<.62?.2:1;if(on)g+=`<path d="M600 120 L420 ${h-110} H860Z" fill="#FFE9B8" opacity="${(.45*on).toFixed(2)}"/>`+glow(640,150,120,.5*on);
  g+=`<path d="M760 ${h-118} h120 v-14 h-120Z" fill="${LINE}"/><line x1="820" y1="${h-130}" x2="740" y2="150" stroke="${LINE}" stroke-width="10"/><line x1="740" y1="150" x2="640" y2="110" stroke="${LINE}" stroke-width="10"/><path d="M560 110 q80 -70 140 10Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3" transform="rotate(${(-3*DECAY(t-.5,4,16)).toFixed(2)} 640 110)"/>`;
  g+=`<path d="M180 ${h-130} q130 -30 250 0 v-130 q-120 -30 -250 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M430 ${h-130} q130 -30 250 0 v-130 q-120 -30 -250 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3" transform="translate(-250,0) scale(-1,1) translate(-860,0)"/>`;
  const fp=clamp((t-1.0)/.45),fx=430-250*Math.sin(Math.PI/2*fp)*(fp<.5?1:1);if(fp>0&&fp<1)g+=`<path d="M430 ${h-130} q${(fx-430)/2} -30 ${fx-430} 0 v-130 q${-(fx-430)/2} -30 ${-(fx-430)} 0" fill="#F6EFE2" stroke="${LINE}" stroke-width="2"/>`;
  for(let i=0;i<4;i++)g+=`<line x1="210" y1="${h-220+i*22}" x2="400" y2="${h-226+i*22}" stroke="${LINE}" stroke-width="2" opacity=".35"/>`;
  const rl=60*(1-SPR(t-.3,.6,8)),rot=rl*4;g+=`<g transform="translate(${(600-rl).toFixed(1)},${h-126}) rotate(${rot.toFixed(1)})"><rect x="-80" y="-8" width="160" height="16" rx="6" fill="#F4B860" stroke="${LINE}" stroke-width="2"/><path d="M80 -8 l22 8 l-22 8Z" fill="#E9C9A6"/></g>`;
  for(let i=0;i<6;i++){const u=((t*.18+i/6)%1),x=520+i*48+16*Math.sin(t+i),y=150+u*(h-280);g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#FFF4D6" opacity="${(on*.8*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  return g},
  sfx(t0,s,E){E(t0+.5,'click');E(t0+.62,'click');E(t0+1.0,'glide',{f0:900,f1:500,dur:.3,g:.07});E(t0+.6,'tick',{g:.5})}},
 // s6 小船在浪上：浪一直起伏（機動），0.3 一道大浪把船推高（過衝）再衰減，桅上小旗擺動
 boat:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F4E8D4"/><circle cx="720" cy="90" r="46" fill="#F4B860" opacity=".8"/>`;
  const wave=(x,ph,a)=>a*Math.sin(x/90+t*2.2+ph);let d=`M0 ${h}`;for(let x=0;x<=888;x+=24)d+=` L${x} ${(h-120+wave(x,0,14)).toFixed(1)}`;g+=`<path d="${d} L888 ${h}Z" fill="#C9D3C9" opacity=".7"/>`;
  const big=-46*DECAY(t-.3,1.5,4.2),by=h-150+wave(444,0,14)+big,rot=6*Math.cos(444/90+t*2.2)+8*DECAY(t-.3,1.5,4.2);
  g+=`<g transform="translate(444,${by.toFixed(1)}) rotate(${rot.toFixed(2)})"><path d="M-130 0 h260 l-40 54 h-180Z" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><line x1="0" y1="0" x2="0" y2="-170" stroke="${LINE}" stroke-width="7"/><path d="M6 -160 l100 120 h-100Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M-6 -150 l-80 104 h80Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`+
   `<path d="M0 -170 q${(20+6*Math.sin(t*6)).toFixed(1)} -8 34 ${(4*Math.sin(t*6)).toFixed(1)} l-34 12Z" fill="${LAMP}"/></g>`;
  d=`M0 ${h}`;for(let x=0;x<=888;x+=24)d+=` L${x} ${(h-90+wave(x,1.3,18)).toFixed(1)}`;g+=`<path d="${d} L888 ${h}Z" fill="#AFC0B6"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'glide',{f0:260,f1:520,dur:.45,g:.12});E(t0+.9,'thump',{g:.25})}},
 // s7 桌上兩只信封：左「薪水」信封封口彈開、紙鈔探出；右「帳單」信封被推近一點；中間一枚硬幣立起來晃，最後倒向左邊
 envelopes:{draw(t,h){let g=`<rect x="0" y="${h-120}" width="888" height="120" fill="#D9C4A0"/>`;
  const env=(x,y,lab,col,flap)=>`<g transform="translate(${x},${y})"><rect x="0" y="0" width="300" height="190" rx="12" fill="${col}" stroke="${LINE}" stroke-width="4"/><path d="M0 0 L150 ${(100*Math.cos(flap)).toFixed(1)} L300 0" fill="${col}" stroke="${LINE}" stroke-width="3"/>${T(150,160,lab,36,700,TXT)}</g>`;
  const fo=Math.PI*clamp(SPR(t-.35,.5,12));const bill=clamp(SPR(t-.4,.55,11));
  if(fo>Math.PI/2)g+=`<rect x="${130}" y="${h-330-60*bill}" width="150" height="90" rx="6" fill="#CFE0C2" stroke="${LINE}" stroke-width="3"/>`+T(205,h-275-60*bill,'$',36,700,TXT);
  g+=env(80,h-320,'薪水','#FFFDF8',fo);
  const px=(1-SPR(t-.6,.6,10))*60;g+=env(508+px,h-300,'學貸帳單','#F3E6D0',0);
  const cu=t-1.0,ang=cu<0?0:-70*clamp(cu/1.2)+20*DECAY(cu,1.5,9)*(1-clamp(cu/1.2));g+=`<g transform="translate(444,${h-130}) rotate(${ang.toFixed(1)})"><ellipse cx="0" cy="-40" rx="16" ry="40" fill="#E0B070" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<path d="M700 ${h-330} q10 -24 0 -48" stroke="${LINE}" stroke-width="2" fill="none" opacity="${(.2+.2*tw(t,1,2.6)).toFixed(2)}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.4,'click');E(t0+.7,'glide',{f0:600,f1:350,dur:.25,g:.08});E(t0+2.2,'thump',{g:.22})}},
 // s8 打卡鐘：卡片由上插入（0.35）、打卡「咔」一聲、指針跳一格、卡片彈出一點、上方時鐘秒針走
 punchclock:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  g+=`<rect x="300" y="60" width="288" height="${h-120}" rx="24" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><circle cx="444" cy="150" r="70" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${444+56*Math.cos(a)}" y1="${150+56*Math.sin(a)}" x2="${444+64*Math.cos(a)}" y2="${150+64*Math.sin(a)}" stroke="${LINE}" stroke-width="3"/>`}
  const mn=(2+(t>.6?1:0)*SPR(t-.6,.4,30))*6*Math.PI/180,sec=(Math.floor(t*2)+SPR((t*2)%1,.45,40))*12*Math.PI/180;
  g+=`<line x1="444" y1="150" x2="${444+46*Math.sin(mn)}" y2="${150-46*Math.cos(mn)}" stroke="${TXT}" stroke-width="6" stroke-linecap="round"/><line x1="444" y1="150" x2="${444+30*Math.sin(Math.PI*5/6)}" y2="${150-30*Math.cos(Math.PI*5/6)}" stroke="${TXT}" stroke-width="8" stroke-linecap="round"/><line x1="444" y1="150" x2="${444+58*Math.sin(sec)}" y2="${150-58*Math.cos(sec)}" stroke="${LAMP}" stroke-width="3"/>`;
  g+=`<rect x="360" y="250" width="168" height="16" rx="6" fill="#4A4744"/>`;
  const ins=SPR(t-.2,.6,12),pop=t>.75?-18*DECAY(t-.75,3,9):0,cy=40+200*ins+pop;g+=`<g transform="translate(0,${cy.toFixed(1)})"><rect x="384" y="-40" width="120" height="180" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(444,10,'時薪',32,700,TXT)}<line x1="400" y1="40" x2="488" y2="40" stroke="${LINE}" stroke-width="2" opacity=".5"/></g>`;
  g+=`<rect x="300" y="250" width="288" height="${h-310}" rx="0" fill="#B98A6A"/><rect x="300" y="250" width="288" height="4" fill="${LINE}"/>`;
  if(t>.6&&t<.9)g+=glow(444,262,70,.6*(1-(t-.6)/.3));
  g+=`<rect x="640" y="${h-170}" width="160" height="110" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(720,h-104,'2027',34,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.6,'thump',{g:.4});E(t0+.6,'click');E(t0+.75,'tick')}}
};
