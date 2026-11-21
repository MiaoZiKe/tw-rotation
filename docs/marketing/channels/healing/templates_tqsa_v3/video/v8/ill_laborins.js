// 談晴說礙 11/21 勞保精算影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261121v_laborins」）。輪播用過的沙漏、存錢筒不再用。
const ILL={
 // s1 儲水塔：水位刻度、出水口一直滴（流出），0.5 起進水管補一次水（政府撥補示意：水位短暫上升），之後水位慢慢下降；水面波紋
 tank:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EEE5D6"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const x0=280,w=330,top=80,bot=h-120;g+=`<rect x="${x0}" y="${top}" width="${w}" height="${bot-top}" rx="18" fill="#F7F2E8" stroke="${LINE}" stroke-width="5"/>`;
  const lv=.62+.08*SPR(t-.5,.6,6)*Math.exp(-Math.max(0,t-1.2)*.6)-.03*Math.max(0,t-.2),wy=bot-(bot-top)*lv;
  let d=`M${x0+4} ${wy}`;for(let x=0;x<=w-8;x+=16)d+=` L${x0+4+x} ${(wy+4*Math.sin(x/30+t*4)).toFixed(1)}`;g+=`<path d="${d} L${x0+w-4} ${bot-4} L${x0+4} ${bot-4}Z" fill="#B9CFC8" opacity=".9"/>`;
  for(let i=1;i<5;i++)g+=`<line x1="${x0+w-40}" y1="${top+i*(bot-top)/5}" x2="${x0+w-6}" y2="${top+i*(bot-top)/5}" stroke="${LINE}" stroke-width="3"/>`;
  g+=`<rect x="${x0+w}" y="${bot-40}" width="90" height="24" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  for(let k=0;k<3;k++){const u=((t*1.6+k/3)%1);g+=`<ellipse cx="${x0+w+84}" cy="${(bot-10+u*80).toFixed(1)}" rx="7" ry="10" fill="#9CB8AE" opacity="${(1-u).toFixed(2)}"/>`}
  const fl=t>.5&&t<1.3;g+=`<path d="M120 ${top+20} h200 v30" fill="none" stroke="#B98A6A" stroke-width="22" stroke-linejoin="round"/>`;if(fl)g+=`<rect x="306" y="${top+50}" width="12" height="${(wy-top-50).toFixed(1)}" fill="#9CB8AE" opacity=".8"/>`;
  const vr=fl?0:-90*SPR(t-1.3,.5,12);g+=`<g transform="rotate(${(t<.5?-90*(1-SPR(t-.2,.5,12)):vr).toFixed(1)} 180 ${top+20})"><rect x="150" y="${top+12}" width="60" height="16" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=T(445,bot+40,'勞保基金',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:300,f1:600,dur:.6,g:.08});E(t0+1.3,'click')}},
 // s2 車票改期：一張車票滑進來（0.2）、改期章「蓋」上去（0.8，壓下回彈），日期由 2028 被劃掉、旁邊換成 2031；剪票孔亮一下
 ticket:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  const sl=(1-SPR(t-.2,.6,11))*-500;g+=`<g transform="translate(${sl.toFixed(1)},0)"><rect x="160" y="60" width="560" height="${h-140}" rx="18" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><line x1="560" y1="70" x2="560" y2="${h-90}" stroke="${LINE}" stroke-width="3" stroke-dasharray="10 10"/>`;
  g+=T(200,120,'推估車票',32,700,SUBC,'start')+T(200,200,'2028',56,700,TXT,'start');
  const cr=pr(t,.8,.25);if(cr>0)g+=`<line x1="196" y1="182" x2="${196+142*cr}" y2="182" stroke="${LAMP}" stroke-width="7"/>`;
  const nw=SPR(t-1.0,.45,15);if(t>1.0)g+=`<g transform="translate(260,262) scale(${Math.max(.01,nw).toFixed(3)})" opacity="${clamp((nw-.1)/.85).toFixed(3)}">${T(0,10,'2031',56,700,HINT)}</g>`;
  const on=t>.6&&t<1.0?1:0;g+=`<circle cx="640" cy="${(h-90)/2+30}" r="22" fill="${on?'#F4B860':FACE}" stroke="${LINE}" stroke-width="3"/></g>`;
  {const cy=Math.min(1,Math.max(0,(t-.35)/.4));g+=`<g opacity="${clamp(t*3)}"><rect x="740" y="${h-190}" width="130" height="56" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(805,h-150,'已撥補',30,700,TXT)}<circle cx="805" cy="${(h-300+110*cy*cy).toFixed(1)}" r="24" fill="#F4B860" stroke="${LINE}" stroke-width="3" opacity="${cy>=1?0:1}"/></g>`}
  const st=t<.55?-80*(1-EO(t/.55)):t<.8?-80*(1-(t-.55)/.25):6*DECAY(t-.8,6,18);g+=`<g transform="translate(0,${st.toFixed(1)})" opacity="${clamp(t*4)}"><rect x="400" y="${h-210}" width="100" height="50" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><rect x="430" y="${h-290}" width="40" height="80" rx="10" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:700,f1:350,dur:.3,g:.07});E(t0+.8,'thump',{g:.4});E(t0+1.0,'pop')}},
 // s3 天秤：左盤小砝碼「11%」、右盤大砝碼「31.42%」落下（0.4），橫桿往右傾、過衝回彈衰減；支點小燈
 balance:{draw(t,h){let g=`<rect x="0" y="${h-40}" width="888" height="40" fill="#E4D3B8"/><path d="M400 ${h-40} h88 l-24 -30 h-40Z" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><line x1="444" y1="${h-70}" x2="444" y2="110" stroke="${LINE}" stroke-width="10"/>`;
  const ang=8*SPR(t-.55,.35,8),r=ang*Math.PI/180,L=300,lx=444-L*Math.cos(r),ly=70-L*Math.sin(r)*-1*-1,rx=444+L*Math.cos(r);const yl=110-L*Math.sin(r),yr=110+L*Math.sin(r);
  g+=`<line x1="${lx.toFixed(1)}" y1="${yl.toFixed(1)}" x2="${rx.toFixed(1)}" y2="${yr.toFixed(1)}" stroke="#B98A6A" stroke-width="12" stroke-linecap="round"/><circle cx="444" cy="110" r="14" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  const pan=(x,y,w2,lab,c,drop)=>`<line x1="${x}" y1="${y}" x2="${x-70}" y2="${y+110}" stroke="${LINE}" stroke-width="2"/><line x1="${x}" y1="${y}" x2="${x+70}" y2="${y+110}" stroke="${LINE}" stroke-width="2"/><path d="M${x-90} ${y+110} h180 q-10 24 -90 24 q-80 0 -90 -24Z" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/><g transform="translate(0,${drop.toFixed(1)})"><rect x="${x-w2/2}" y="${y+110-w2*.7}" width="${w2}" height="${w2*.7}" rx="10" fill="${c}" stroke="${LINE}" stroke-width="3"/>${T(x,y+110-w2*.35+12,lab,32,700,'#FFFFFF')}</g>`;
  const dr=t<.4?-200:-200*(1-Math.min(1,(t-.4)/.15)**2)+(t>.55?-6*Math.abs(DECAY(t-.55,6,14)):0);
  g+=pan(lx,yl,80,'11%','#B98A6A',0)+(t>.4?pan(rx,yr,150,'31.42%',LAMP,dr):pan(rx,yr,0.01,'',LAMP,0));
  return g},
  sfx(t0,s,E){E(t0+.55,'thump',{g:.45});E(t0+.8,'tick')}},
 // s4 擴音器：擴音器聲波一圈圈擴散（常說），右邊一疊文件被翻開一頁；聲波碰到文件就消散
 megaphone:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  const kick=-8*DECAY(t-.2,4,14);g+=`<g transform="rotate(${kick.toFixed(1)} 150 ${h/2})"><path d="M90 ${h/2-30} h50 l140 -80 v220 l-140 -80 h-50Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><rect x="110" y="${h/2+30}" width="30" height="60" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  for(let k=0;k<4;k++){const u=((t*.9+k/4)%1);if(t<.2)break;g+=`<path d="M${300+u*220} ${h/2-60-u*30} q${30+u*20} ${60+u*30} 0 ${120+u*60}" fill="none" stroke="${LAMP}" stroke-width="${(6*(1-u)).toFixed(1)}" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=`<rect x="600" y="${h/2-100}" width="200" height="230" rx="8" fill="#F3EADB" stroke="${LINE}" stroke-width="3"/><rect x="590" y="${h/2-110}" width="200" height="230" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(690,h/2-56,'精算報告',32,700,TXT);
  for(let i=0;i<4;i++)g+=`<line x1="612" y1="${h/2-10+i*30}" x2="${770-(i%2)*40}" y2="${h/2-10+i*30}" stroke="${LINE}" stroke-width="2" opacity=".45"/>`;
  const pg=clamp((t-1.0)/.5);if(pg>0&&pg<1){const x=790-200*pg;g+=`<path d="M790 ${h/2-110} L${x} ${h/2-110-30*Math.sin(Math.PI*pg)} L${x} ${h/2+120-30*Math.sin(Math.PI*pg)} L790 ${h/2+120}Z" fill="#F7F0E4" stroke="${LINE}" stroke-width="2"/>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:500,f1:300,dur:.3,g:.08});E(t0+1.0,'glide',{f0:900,f1:500,dur:.4,g:.06})}},
 // s5 雪球：一顆球從坡頂滾下（0.2–1.4）越滾越大、滾過的地方留痕，停在坡底時壓扁回彈；雪花飄
 snowball:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3ECE0"/><path d="M0 70 L888 ${h-60} V${h} H0Z" fill="#B98A6A"/><path d="M0 70 L888 ${h-60}" stroke="#8A5A44" stroke-width="6"/>`;
  const p=EO(clamp((t-.15)/1.8)),x=70+620*p,yLine=v=>70+(h-130)*(v/888),r=34+46*p,y=yLine(x)-r;
  g+=`<path d="M60 ${yLine(60)} L${x} ${yLine(x)}" stroke="#E9DFC9" stroke-width="${(r*1.2).toFixed(1)}" opacity=".7" stroke-linecap="round"/>`;
  const sq=t>1.95?.08*DECAY(t-1.95,7,22):0;g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${(1+sq).toFixed(3)},${(1-sq).toFixed(3)}) rotate(${(p*540).toFixed(0)})"><circle r="${r.toFixed(1)}" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M${(-r*.9).toFixed(1)} ${(r*.25).toFixed(1)} A ${r.toFixed(1)} ${r.toFixed(1)} 0 0 0 ${(r*.9).toFixed(1)} ${(r*.25).toFixed(1)} Q 0 ${(r*.7).toFixed(1)} ${(-r*.9).toFixed(1)} ${(r*.25).toFixed(1)}Z" fill="#E8E4DC" opacity=".8"/><circle cx="${(-r*.35).toFixed(1)}" cy="${(-r*.35).toFixed(1)}" r="${(r*.18).toFixed(1)}" fill="#FFFFFF"/><circle cx="${(r*.3).toFixed(1)}" cy="${(-r*.15).toFixed(1)}" r="${(r*.12).toFixed(1)}" fill="#FFFFFF"/></g><ellipse cx="${x.toFixed(1)}" cy="${(yLine(x)+4).toFixed(1)}" rx="${(r*.8).toFixed(1)}" ry="8" fill="#6E4636" opacity=".25"/>`;
  for(let i=0;i<10;i++){const u=((t*.25+i/10)%1);g+=`<circle cx="${(40+i*86+10*Math.sin(t*2+i)).toFixed(1)}" cy="${(u*(h-40)).toFixed(1)}" r="4" fill="#FFFFFF" stroke="#C9CFC2" stroke-width="1" opacity="${(.9*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  g+=`<rect x="30" y="${h-110}" width="200" height="60" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(130,h-68,'未提存給付',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.15,'glide',{f0:200,f1:120,dur:1.7,g:.1});E(t0+1.95,'thump',{g:.4})}},
 // s6 齒輪組：三個齒輪（報酬率、投保人數、物價）互相咬合轉動，0.6 中間齒輪被撥一下加速再回穩；指針跟著擺
 gears:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE4D4"/>`;
  const gear=(cx,cy,R,n,a,c,lab)=>{let d='';for(let i=0;i<n*2;i++){const r=i%2?R:R+16,aa=a+i*Math.PI/n;d+=(i?'L':'M')+(cx+r*Math.cos(aa)).toFixed(1)+' '+(cy+r*Math.sin(aa)).toFixed(1)}return `<path d="${d}Z" fill="${c}" stroke="${LINE}" stroke-width="3"/><circle cx="${cx}" cy="${cy}" r="${R*.55}" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(cx,cy+12,lab,32,700,TXT)}`};
  const sp=t*.8+1.2*(1-Math.exp(-Math.max(0,t-.6)*3))*(t>.6?1:0);
  g+=gear(220,h/2+20,100,12,sp,'#B98A6A','報酬')+gear(444,h/2-30,80,10,-sp*1.25+.2,LAMP,'人數')+gear(650,h/2+30,95,12,sp*1.05+.1,'#C9A27A','物價');
  return g},
  sfx(t0,s,E){E(t0+.6,'click');E(t0+.62,'glide',{f0:300,f1:700,dur:.4,g:.08})}},
 // s7 搖椅：空搖椅被輕推（0.3）前後搖、阻尼衰減；窗邊盆栽、小茶几上的毛線球滾一下
 rocker:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E5D2"/><rect x="0" y="${h-70}" width="888" height="70" fill="#C9A27A"/><rect x="560" y="50" width="260" height="200" rx="10" fill="#F9EEDC" stroke="${LINE}" stroke-width="4"/><line x1="690" y1="50" x2="690" y2="250" stroke="${LINE}" stroke-width="3"/>`;
  const a=10*DECAY(t-.3,.9,4.5);g+=`<g transform="rotate(${a.toFixed(2)} 330 ${h-70})"><path d="M180 ${h-70} q150 24 300 0" fill="none" stroke="#8A5A44" stroke-width="12" stroke-linecap="round"/><path d="M230 ${h-80} v-110 h170 v110" fill="none" stroke="#8A5A44" stroke-width="10"/><path d="M230 ${h-190} l-30 -150 h40 l30 150" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="226" y="${h-200}" width="180" height="22" rx="8" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/></g>`;
  const rl=(1-SPR(t-1.0,.6,8))*-60;g+=`<circle cx="${(640+rl).toFixed(1)}" cy="${h-96}" r="26" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M${(620+rl).toFixed(1)} ${h-104} q20 -10 40 4" stroke="${LINE}" stroke-width="2" fill="none"/>`;
  g+=`<rect x="760" y="${h-140}" width="70" height="70" rx="8" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/><path d="M795 ${h-140} q${(-20+3*Math.sin(t*2)).toFixed(1)} -50 -10 -90 M795 ${h-140} q${(20+3*Math.sin(t*2+1)).toFixed(1)} -50 10 -100" stroke="#7E8F6A" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'tick');E(t0+1.0,'glide',{f0:500,f1:300,dur:.3,g:.06})}},
 // s8 漱口杯：一支牙刷先在杯裡，第二支從上方滑進杯（0.4）、兩支輕碰一下（1.0）、杯子水珠閃
 toothbrush:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/><rect x="0" y="0" width="888" height="${h-60}" fill="#EDEFE9"/>`;
  for(let i=0;i<6;i++)for(let j=0;j<4;j++)g+=`<rect x="${i*150}" y="${j*80}" width="148" height="78" fill="none" stroke="#D8DCD2" stroke-width="2"/>`;
  const brush=(x,y,ang,c)=>`<g transform="translate(${x},${y}) rotate(${ang.toFixed(1)})"><rect x="-9" y="-150" width="18" height="150" rx="9" fill="${c}" stroke="${LINE}" stroke-width="3"/><rect x="-14" y="-192" width="28" height="46" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/></g>`;
  const d=SPR(t-.4,.5,12),tap=4*DECAY(t-1.0,4,16);g+=brush(420,h-150,-12-tap,'#B98A6A')+brush(470,h-150-(1-d)*170,12+tap,LAMP);
  g+=`<path d="M360 ${h-60} l-14 -150 h196 l-14 150Z" fill="#DCE8E4" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/>`;
  [[400,h-140],[500,h-110]].forEach(([x,y],i)=>g+=sparkle(x,y,9,.3+.5*tw(t,i*2,3)));
  g+=`<rect x="640" y="${h-170}" width="160" height="110" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(720,h-104,'兩個人',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.4,'glide',{f0:800,f1:400,dur:.3,g:.06});E(t0+1.0,'tick',{g:.8})}}
};
