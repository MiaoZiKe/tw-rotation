// 談晴說礙 11/18 最低工資影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261118v_minwage」）。輪播用過的牆上時鐘＋吊牌不再用。
const ILL={
 // s1 收據印表機：紙捲一格格吐出（0.2–1.2），印出「2027 最低月薪」與金額列、最後一行「30,900」被晴光橘框起、切紙刀落下一次
 printer:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#E4D3B8"/>`;
  const out=Math.floor(clamp((t-.2)/1.0)*6)/6*250+(t>.2&&t<1.2?6*Math.sin(t*60):0),py=h-250-out;
  g+=`<g><rect x="300" y="${py.toFixed(1)}" width="288" height="${(out+40).toFixed(1)}" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  const lines=[['2027 年',''],['最低月薪',''],['30,900 元','hi']];lines.forEach((l,i)=>{const y=py+60+i*70;if(y>h-240)return;g+=l[1]?`<rect x="320" y="${y-44}" width="248" height="60" rx="10" fill="${LAMP}" opacity=".9"/>`+T(444,y,l[0],38,700,'#FFFFFF'):T(444,y,l[0],34,700,TXT)});
  g+=`<path d="M300 ${py} l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<rect x="230" y="${h-250}" width="428" height="170" rx="26" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="280" y="${h-262}" width="328" height="24" rx="8" fill="#4A4744"/>`;
  const led=t<1.2?(Math.floor(t*8)%2):1;g+=`<circle cx="610" cy="${h-180}" r="12" fill="${led?'#9CC08A':'#6E7E66'}" stroke="${LINE}" stroke-width="2"/>`+T(330,h-150,'薪資單',32,700,'#FFFFFF','start');
  const cut=t>1.35?-20*DECAY(t-1.35,4,12):0;g+=`<rect x="276" y="${h-268+cut}" width="336" height="10" rx="4" fill="${LINE}"/>`;
  g+=`<rect x="80" y="${h-160}" width="110" height="70" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M100 ${h-160} v-40 h70 v40" fill="none" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<5;i++){const u=((t*.3+i/5)%1);g+=`<circle cx="${(700+i*30+10*Math.sin(t*2+i)).toFixed(1)}" cy="${(h-140-u*200).toFixed(1)}" r="4" fill="#E0B070" opacity="${(.7*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  return g},
  sfx(t0,s,E){for(let k=0;k<6;k++)E(t0+.2+k*.167,'tick',{g:.6});E(t0+1.35,'click');E(t0+1.4,'bell',{n:[19],g:.4})}},
 // s2 會議桌與議事槌：槌子抬起（預備）→ 0.55 敲下 → 木座震、桌上文件跳一下、三支麥克風燈依序亮
 gavel:{draw(t,h){let g=`<rect x="0" y="${h-130}" width="888" height="130" fill="#B48A60"/><rect x="0" y="${h-140}" width="888" height="14" fill="#9C7450"/>`;
  [[150,'#E9B98A'],[444,'#E0C9A6'],[738,'#E9B98A']].forEach(([x,c],i)=>{const on=clamp((t-1.0-i*.18)*6);g+=`<line x1="${x}" y1="${h-140}" x2="${x+30}" y2="${h-230}" stroke="${LINE}" stroke-width="5"/><circle cx="${x+34}" cy="${h-238}" r="12" fill="${on>.5?'#E36B4A':'#B9B2A8'}" stroke="${LINE}" stroke-width="2"/>`+(on>0?glow(x+34,h-238,30,.5*on):'')});
  const hop=t>.55?-14*Math.abs(DECAY(t-.55,5,16)):0;g+=`<g transform="translate(0,${hop.toFixed(1)})"><rect x="200" y="${h-190}" width="200" height="40" rx="4" fill="#FFFDF8" stroke="${LINE}" stroke-width="2" transform="rotate(-3 300 ${h-170})"/><rect x="230" y="${h-180}" width="190" height="34" rx="4" fill="#F3EADB" stroke="${LINE}" stroke-width="2" transform="rotate(4 320 ${h-160})"/></g>`;
  const jo=t>.55?3*DECAY(t-.55,8,30):0;g+=`<ellipse cx="560" cy="${h-150+jo}" rx="80" ry="18" fill="#6E4636" stroke="${LINE}" stroke-width="3"/>`;
  let a=t<.35?-30*EO(t/.35):t<.55?-30+30*Math.pow((t-.35)/.2,2)+0:8*DECAY(t-.55,6,18);a-=0;const ang=t<.55?(t<.35?-40*EO(t/.35):-40+40*Math.pow((t-.35)/.2,2)):6*DECAY(t-.55,6,18);
  g+=`<g transform="rotate(${ang.toFixed(1)} 700 ${h-210})"><line x1="700" y1="${h-210}" x2="590" y2="${h-180}" stroke="#8A5A44" stroke-width="16" stroke-linecap="round"/><rect x="530" y="${h-230}" width="70" height="90" rx="14" fill="#8A5A44" stroke="${LINE}" stroke-width="3" transform="rotate(-15 565 ${h-185})"/></g>`;
  if(t>.55&&t<.95){const k=(t-.55)/.4;g+=`<ellipse cx="560" cy="${h-150}" rx="${90+90*k}" ry="${20+16*k}" fill="none" stroke="${LAMP}" stroke-width="4" opacity="${(.7*(1-k)).toFixed(2)}"/>`}
  g+=`<rect x="300" y="40" width="288" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,88,'審議會',34,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.55,'thump',{g:.6});E(t0+.55,'click');[0,1,2].forEach(i=>E(t0+1.0+i*.18,'tick'))}},
 // s3 手搖飲吧台：雪克杯上下搖三下（0.2–1.0）、倒進杯子（液面升起）、杯子沿檯面滑出停住、吸管插下
 drinkbar:{draw(t,h){let g=`<rect x="0" y="${h-120}" width="888" height="120" fill="#C9A27A"/><rect x="0" y="${h-128}" width="888" height="12" fill="#9C7450"/>`;
  g+=`<rect x="30" y="30" width="190" height="80" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(125,84,'今日手搖',34,700,TXT);
  const sh=t<1.0?-26*Math.abs(Math.sin(t*Math.PI*3/0.8)):0,tilt=t>1.0&&t<1.6?-60*Math.sin(Math.PI*(t-1.0)/.6):0;
  g+=`<g transform="translate(250,${(h-260+sh).toFixed(1)}) rotate(${tilt.toFixed(1)} 40 60)"><path d="M0 0 h80 l-10 140 h-60Z" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/><rect x="-4" y="-30" width="88" height="34" rx="8" fill="#BFC3BB" stroke="${LINE}" stroke-width="3"/></g>`;
  const lv=clamp((t-1.1)/.5),sl=t>1.7?(1-SPR(t-1.7,.55,11))*0:0,cx=420+200*SPR(t-1.7,.55,10);
  g+=`<g transform="translate(${cx.toFixed(1)},${h-128})"><path d="M-60 -170 h120 l-14 170 h-92Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="3"/><path d="M${-60+14*(1-lv)} ${-150*lv} h${120-28*(1-lv)} l${-14*lv} ${150*lv} h${-92}Z" fill="#C79A6B"/>`;
  for(let i=0;i<5;i++)g+=`<circle cx="${-30+i*14}" cy="${-14-(i%2)*14}" r="7" fill="#4A3B30" opacity="${lv.toFixed(2)}"/>`;
  const st=SPR(t-2.1,.5,14);if(t>2.1)g+=`<line x1="18" y1="${(-260+80*st).toFixed(1)}" x2="${(30).toFixed(1)}" y2="${(-40).toFixed(1)}" stroke="${LAMP}" stroke-width="10" stroke-linecap="round"/>`;g+=`</g>`;
  if(t>1.0&&t<1.6)g+=`<path d="M300 ${h-210} q60 20 100 60" stroke="#C79A6B" stroke-width="8" fill="none" opacity=".8"/>`;
  return g},
  sfx(t0,s,E){[.27,.53,.8].forEach(x=>E(t0+x,'tick',{g:.8}));E(t0+1.1,'glide',{f0:300,f1:600,dur:.4,g:.08});E(t0+1.7,'glide',{f0:700,f1:300,dur:.3,g:.08});E(t0+2.15,'pop')}},
 // s4 電子秤：左盤已有 29,500 的硬幣堆，0.4 起再落下一枚「+1,400」硬幣，秤盤下沉回彈、指示數字跳動停在 +1,400
 scale:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  const drop=clamp((t-.4)/.3),land=t>.7,sink=land?14*(1-Math.exp(-(t-.7)*6))+8*DECAY(t-.7,4,14):0;
  g+=`<rect x="250" y="${h-150}" width="388" height="90" rx="16" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="360" y="${h-128}" width="168" height="50" rx="8" fill="#3A3836"/>`;
  const v=land?Math.round(1400*clamp((t-.7)/.5)):0,flick=t>.7&&t<1.2?Math.floor(t*30)%2:0;g+=T(444,h-90,'+'+F1(v),34,700,flick?'#FFE9B8':'#F4B860');
  g+=`<g transform="translate(0,${sink.toFixed(1)})"><rect x="210" y="${h-180}" width="468" height="24" rx="10" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<7;i++)g+=`<ellipse cx="${330+(i%4)*60+(i>3?30:0)}" cy="${h-196-(i>3?20:0)}" rx="34" ry="12" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`;
  g+=`</g>`;const cy=drop<1?(h-440)+(h-270-(h-440))*drop*drop:(h-270+sink-12*Math.abs(DECAY(t-.7,4,12)));if(t>.4)g+=`<g transform="translate(560,${cy.toFixed(1)})"><circle r="64" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,12,'+1,400',32,700,'#FFFFFF')}</g>`;
  [[150,90],[740,120]].forEach(([x,y],i)=>g+=sparkle(x,y,12,.3+.4*tw(t,i*3,3)));
  return g},
  sfx(t0,s,E){E(t0+.7,'thump',{g:.4});E(t0+.75,'tick');E(t0+1.2,'bell',{n:[21],g:.35})}},
 // s4 門框身高刻痕：鉛筆在門框上由下往上一格格畫出十一道刻痕（0.2–1.6，每道一個小回彈），最高那道被晴光橘框起、門板微微晃一下；旁邊小鉛筆彈跳
 doorframe:{draw(t,h){let g=`<rect x="0" y="${h-70}" width="888" height="70" fill="#E4D3B8"/>`;
  g+=`<rect x="250" y="40" width="388" height="${h-110}" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><rect x="262" y="52" width="364" height="${h-134}" fill="#F3E6D0" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="226" y="30" width="24" height="${h-100}" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="638" y="30" width="24" height="${h-100}" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  g+=`<circle cx="590" cy="${(h-70)/2+20}" r="12" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  const n=11,y0=h-110,y1=120;
  for(let i=0;i<n;i++){const a=.2+i*.13,u=t-a;if(u<0)continue;const y=y0-(y0-y1)*i/(n-1),L=(i==n-1?120:70+(i%3)*10)*Math.min(1,u*8),bump=-4*DECAY(u,5,16);
   const top=i==n-1;g+=`<line x1="226" y1="${(y+bump).toFixed(1)}" x2="${(226+L).toFixed(1)}" y2="${(y+bump).toFixed(1)}" stroke="${top?LAMP:LINE}" stroke-width="${top?16:10}" stroke-linecap="round"/>`;if(top&&u>.15)g+=T(226+L+14,y+12,'2027',34,700,LAMP,'start');
   if(top&&u>.15)g+=glow(226+120,y,50,.4*clamp((u-.15)*4))}
  const pk=clamp((t-1.7)*3);if(pk>0)g+=sparkle(330,y1-30,14,.3+.5*tw(t,2,3));
  const pen=Math.min(10,(t-.2)/1.4*10),py=y0-(y0-y1)*clamp((t-.2)/1.5),bounce=t<1.7?4*Math.sin(t*30):0;
  g+=`<g transform="translate(${(120).toFixed(1)},${(py+bounce).toFixed(1)}) rotate(-35)"><rect x="-10" y="-70" width="20" height="70" fill="#F4B860" stroke="${LINE}" stroke-width="3"/><path d="M-10 0 h20 l-10 22Z" fill="#E4C9A0" stroke="${LINE}" stroke-width="3"/><rect x="-10" y="-84" width="20" height="14" fill="#E36B4A" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="690" y="40" width="160" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(770,88,'十年',34,700,TXT);
  const sw=t>1.7?2*DECAY(t-1.7,3,10):0;g+=`<g transform="rotate(${sw.toFixed(2)} 444 40)"></g>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<11;i++)E(t0+.2+i*.13,'tick',{g:.5});E(t0+1.7,'bell',{n:[21],g:.4});E(t0+1.7,'sparkle',{n:[24]})}},
 // s5 制服掛架：五件制服（圍裙、廚師帽、工作背心、超商制服、安全帽）依序滑進掛架並擺盪衰減
 uniforms:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/><line x1="40" y1="70" x2="848" y2="70" stroke="${LINE}" stroke-width="8" stroke-linecap="round"/><line x1="60" y1="70" x2="60" y2="${h-50}" stroke="${LINE}" stroke-width="6"/><line x1="828" y1="70" x2="828" y2="${h-50}" stroke="${LINE}" stroke-width="6"/>`;
  const items=[['#E9B98A','圍裙'],['#FFFDF8','廚師'],['#F4B860','背心'],['#C9D3C9','超商'],['#B98A6A','倉儲']];
  items.forEach((it,i)=>{const a=.1+i*.16,u=t-a;if(u<0)return;const x=140+i*150,sl=(1-SPR(u,.55,12))*-300,sw=10*DECAY(u-.3,2.2,7)+3*DECAY(t-1.9-i*.1,2.5,8);
   g+=`<g transform="translate(${(x+sl).toFixed(1)},70) rotate(${sw.toFixed(1)})"><path d="M0 0 v18 M-36 40 l36 -22 l36 22" fill="none" stroke="${LINE}" stroke-width="4"/><path d="M-50 40 h100 l10 ${h-200} h-120Z" fill="${it[0]}" stroke="${LINE}" stroke-width="3"/>${T(0,140,it[1],32,700,TXT)}</g>`});
  return g},
  sfx(t0,s,E){[0,1,2,3,4].forEach(i=>E(t0+.1+i*.16+.15,'tick',{g:.6}))}},
 // s6 公文送件：信封從左飛向「行政院」建築（弧線）、0.9 進門、門口旗子飄、窗格亮起一格（還沒核定：只亮一格）
 govbuilding:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/><rect x="0" y="${h-60}" width="888" height="60" fill="#D9C4A0"/>`;
  g+=`<path d="M430 120 L640 60 L850 120Z" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="450" y="120" width="380" height="${h-180}" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<5;i++)g+=`<rect x="${470+i*72}" y="140" width="22" height="${h-210}" fill="#E4D8C4" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="600" y="${h-150}" width="80" height="90" rx="6" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`+T(640,104,'行政院',32,700,'#FFFFFF');
  const on=clamp((t-1.1)*5);g+=`<rect x="510" y="160" width="40" height="40" fill="${on>.5?'#FFE9B8':'#E4D8C4'}" stroke="${LINE}" stroke-width="2"/>`+(on>0?glow(530,180,46,.5*on):'');
  const fw=Math.sin(t*5)*8;g+=`<line x1="460" y1="120" x2="460" y2="20" stroke="${LINE}" stroke-width="4"/><path d="M462 24 q30 ${fw.toFixed(1)} 60 0 v36 q-30 ${(-fw).toFixed(1)} -60 0Z" fill="${LAMP}"/>`;
  const u=clamp((t-.2)/.7),e=EO(u),x=80+(640-80)*e,y=(h-160)-200*Math.sin(Math.PI*e),sc=1-.5*e;if(u<1)g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${(-10+20*e).toFixed(1)}) scale(${sc.toFixed(3)})"><rect x="-70" y="-46" width="140" height="92" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M-70 -46 L0 6 L70 -46" fill="none" stroke="${LINE}" stroke-width="3"/></g>`;
  for(let i=0;i<3;i++){const u2=clamp((t-.2-i*.06)/.7);if(u2<=0||u2>=1)continue;const e2=EO(u2);g+=`<circle cx="${(80+560*e2-30).toFixed(1)}" cy="${((h-160)-200*Math.sin(Math.PI*e2)+10).toFixed(1)}" r="${(6-i*1.5).toFixed(1)}" fill="${LAMP}" opacity="${(.5-i*.12).toFixed(2)}"/>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:400,f1:900,dur:.6,g:.08});E(t0+.9,'thump',{g:.25});E(t0+1.1,'sparkle',{n:[24]})}},
 // s7 手機入帳通知：手機在桌上震兩下（0.3／0.5）、通知卡由上滑下、金額欄是「?」，金額卡片輕輕晃
 phonebank:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#D9C4A0"/>`;
  const vib=(t>.3&&t<.42)||(t>.5&&t<.62)?Math.sin(t*160)*5:0;g+=`<g transform="translate(${(444+vib).toFixed(1)},${h-80}) rotate(-8)"><rect x="-130" y="-380" width="260" height="380" rx="34" fill="#4A4744" stroke="${LINE}" stroke-width="4"/><rect x="-112" y="-356" width="224" height="330" rx="20" fill="#F7EFE2"/>`;
  const sl=SPR(t-.55,.55,12);g+=`<g transform="translate(0,${(-356+(1-sl)*-90).toFixed(1)})" opacity="${clamp((t-.55)*6)}"><rect x="-104" y="20" width="208" height="150" rx="16" fill="${FACE3}" stroke="${LAMP}" stroke-width="3"/>${T(0,66,'薪資入帳',32,700,TXT)}${T(0,(132-14*Math.abs(Math.sin(Math.PI*Math.min(1,((t-1.2)%1.0)/.45)))*(t>1.2&&((t-1.2)%1.0)<.45?1:0)).toFixed(1),'NT$ ?',36,700,HINT)}</g></g>`;
  if(t>.3&&t<.7)[-1,1].forEach(s=>g+=`<path d="M${444+s*170} ${h-300} q${s*20} 30 0 60" stroke="${LAMP}" stroke-width="4" fill="none" opacity=".7"/>`);
  g+=`<rect x="120" y="${h-150}" width="160" height="70" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><line x1="140" y1="${h-120}" x2="250" y2="${h-120}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  g+=`<path d="M680 ${h-80} v-80 q0 -26 26 -26 h40 q26 0 26 26 v80" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M700 ${h-200} q8 -20 0 -40" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.2+.25*tw(t,0,2.5)).toFixed(2)}"/><path d="M730 ${h-196} q8 -20 0 -40" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.2+.25*tw(t,2,2.5)).toFixed(2)}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'tick',{g:.7});E(t0+.5,'tick',{g:.7});E(t0+.6,'glide',{f0:900,f1:600,dur:.2,g:.08})}},
 // s8 捲尺：尺帶由左拉出（0.2–0.9），停在中段晃一下、刻度上一個「?」標籤彈出、尺盒小幅回彈
 tape:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#E4D3B8"/>`;
  const ext=600*SPR(t-.2,.55,10)+(t>1.4?6*Math.sin((t-1.4)*5):0),y=h-170;   // 尺帶在手上輕輕來回（環境動作）g+=`<rect x="140" y="${y}" width="${ext.toFixed(1)}" height="50" fill="#F4D27A" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i*30<ext;i++)g+=`<line x1="${140+i*30}" y1="${y}" x2="${140+i*30}" y2="${y+(i%5?16:28)}" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="${136+ext}" y="${y-12}" width="14" height="74" rx="3" fill="${LINE}"/>`;
  const rb=-6*DECAY(t-.9,4,14);g+=`<g transform="translate(${rb.toFixed(1)},0)"><rect x="40" y="${y-90}" width="180" height="180" rx="40" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><circle cx="130" cy="${y}" r="34" fill="#F3DDB8" stroke="${LINE}" stroke-width="3"/></g>`;
  const q=SPR(t-1.1,.45,16);if(t>1.1)g+=`<g transform="translate(560,${y-90}) scale(${Math.max(.01,q).toFixed(3)})" opacity="${clamp((q-.1)/.85).toFixed(3)}"><rect x="-50" y="-40" width="100" height="70" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(0,14,'?',44,700,HINT)}<path d="M-10 30 l10 16 l10 -16" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="300" y="40" width="288" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,88,'25 歲以前',34,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:900,f1:500,dur:.5,g:.07});E(t0+.9,'click');E(t0+1.15,'pop')}}
};
