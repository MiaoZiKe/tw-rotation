// 談晴說礙 11/22 平均初婚年齡影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261122v_firstmarriage」）。
// 不用：桌上兩杯飲料（輪播 s1、結婚 v3 s7）、蛋糕蠟燭、年曆、搖籃、婚紗店、戶政櫃台、喜宴（結婚影片用過）。
const ILL={
 // s1 熱氣球升空：氣球從下方升起（0.2–1.3，減速）飛過右側高度尺的「30」刻度後停在 31～33 之間，吊籃輕晃；雲往下飄
 balloon:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F5E6CF"/>`;
  for(let i=0;i<3;i++){const y=((80+i*170+t*30)%(h+60))-30;g+=`<ellipse cx="${120+i*260}" cy="${y.toFixed(1)}" rx="${70-i*8}" ry="22" fill="#FFFDF8" opacity=".8"/>`}
  const rx=760,top=60,bot=h-40,sy=v=>bot-(bot-top)*(v-20)/(40-20);g+=`<line x1="${rx}" y1="${top}" x2="${rx}" y2="${bot}" stroke="${LINE}" stroke-width="4"/>`;
  [20,25,30,35,40].forEach(v=>g+=`<line x1="${rx}" y1="${sy(v)}" x2="${rx+(v===30?40:24)}" y2="${sy(v)}" stroke="${v===30?LAMP:LINE}" stroke-width="${v===30?6:3}"/>`+T(rx+70,sy(v)+11,String(v),32,v===30?700:400,v===30?HINT:SUBC,'start'));
  const p=SPR(t-.2,.7,4.5),y=(bot+120)-((bot+120)-sy(32.4))*p,sw=6*Math.sin(t*2.2)*.6+5*DECAY(t-1.3,1.5,6);
  g+=`<line x1="${rx-10}" y1="${(y+150).toFixed(1)}" x2="${rx-10}" y2="${(y+150).toFixed(1)}"/>`;
  g+=`<g transform="translate(420,${y.toFixed(1)}) rotate(${sw.toFixed(1)} 0 150)"><path d="M0 -120 c90 0 120 70 100 130 c-16 44 -60 70 -70 90 h-60 c-10 -20 -54 -46 -70 -90 c-20 -60 10 -130 100 -130Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><path d="M0 -120 c-30 40 -34 140 -20 220 M0 -120 c30 40 34 140 20 220" fill="none" stroke="#F4D0A0" stroke-width="6"/>`+
   `<line x1="-30" y1="100" x2="-22" y2="140" stroke="${LINE}" stroke-width="3"/><line x1="30" y1="100" x2="22" y2="140" stroke="${LINE}" stroke-width="3"/><rect x="-34" y="140" width="68" height="44" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  if(t>.2&&t<1.6)for(let k=0;k<3;k++){const u=((t*2+k/3)%1);g+=`<circle cx="${(420+Math.sin(k*2)*14).toFixed(1)}" cy="${(y+200+u*60).toFixed(1)}" r="${(6*(1-u)).toFixed(1)}" fill="#FFFDF8" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=T(rx-20,top+40,'歲',32,700,SUBC,'end');
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:220,f1:520,dur:1.0,g:.1});E(t0+.85,'tick');E(t0+1.3,'bell',{n:[19],g:.35})}},
 // s2 書架：一排書，《人口統計年刊》那本被抽出一半（0.3，過衝回彈）並傾斜，書籤絲帶擺盪衰減；旁邊書擋小盆栽
 bookshelf:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="60" y="${h-70}" width="768" height="24" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`;
  const cols=['#C9A27A','#B98A6A','#D9B48C','#9C6A50','#E0C9A6','#B98A6A','#C9D3C9','#D9B48C','#9C6A50','#C9A27A'];
  cols.forEach((c,i)=>{const x=90+i*66,hh=200+((i*37)%60),hi=i===5,pull=hi?-60*SPR(t-.3,.5,11):0,tilt=hi?-6*SPR(t-.5,.5,9):0;
   g+=`<g transform="translate(0,${pull.toFixed(1)}) rotate(${tilt.toFixed(1)} ${x+28} ${h-70})"><rect x="${x}" y="${h-70-hh}" width="56" height="${hh}" rx="4" fill="${hi?LAMP:c}" stroke="${LINE}" stroke-width="3"/>${hi?`<text x="${x+28}" y="${h-70-hh+30}" font-size="32" font-weight="700" fill="#FFFFFF" font-family="Noto Sans CJK TC" writing-mode="tb" text-anchor="start">年刊</text><path d="M${x+40} ${h-70-hh} q${(6*DECAY(t-.35,2,9)).toFixed(1)} 40 ${(-4+10*DECAY(t-.35,2,9)).toFixed(1)} 80" stroke="#F4D0A0" stroke-width="5" fill="none"/>`:''}</g>`});
  g+=`<rect x="770" y="${h-150}" width="56" height="80" rx="8" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/><path d="M798 ${h-150} q${(-20+3*Math.sin(t*2)).toFixed(1)} -40 -6 -76 M798 ${h-150} q${(18+3*Math.sin(t*2+1)).toFixed(1)} -40 8 -84" stroke="#7E8F6A" stroke-width="8" fill="none" stroke-linecap="round"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'glide',{f0:600,f1:300,dur:.3,g:.07});E(t0+.6,'tick')}},
 // s3 簽名簿：攤開的簿子，一支筆在第一行寫下一條手寫線（0.3–1.1，描線），寫完筆抬起；第二行留白，頁角微翹
 guestbook:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/>`;
  g+=`<path d="M120 50 q160 -20 324 10 v${h-90} q-164 -30 -324 -10Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M444 60 q160 -30 324 -10 v${h-90} q-164 -20 -324 10Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(282,110,'第一次',32,700,SUBC);for(let i=0;i<3;i++)g+=`<line x1="160" y1="${160+i*60}" x2="410" y2="${158+i*60}" stroke="${LINE}" stroke-width="2" opacity=".35"/><line x1="480" y1="${150+i*60}" x2="730" y2="${152+i*60}" stroke="${LINE}" stroke-width="2" opacity=".35"/>`;
  const w=pr(t,.3,.8);g+=`<path d="M170 150 q30 -26 50 0 t50 0 t50 -6 t50 4" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" ${draw(w)}/>`;
  const px=170+200*w,py=150-(t>1.1?40*SPR(t-1.1,.6,10):0)+(w>0&&w<1?6*Math.sin(t*30):0);g+=`<g transform="translate(${px.toFixed(1)},${py.toFixed(1)}) rotate(35)"><rect x="-8" y="-120" width="16" height="110" rx="6" fill="#8A5A44" stroke="${LINE}" stroke-width="2"/><path d="M-8 -10 l8 16 l8 -16Z" fill="${LINE}"/></g>`;
  g+=`<path d="M768 ${h-40} l-30 ${(-4-6*tw(t,0,2)).toFixed(1)} l26 -26Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'glide',{f0:900,f1:700,dur:.8,g:.04});E(t0+1.1,'tick')}},
 // s4 喜帖：一疊紅帖由右飛進桌面依序疊起（0.1–1.0，每張彈一下）、最上面一張封蠟壓下發光；背景彩帶擺
 invites:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#C9A27A"/>`;
  for(let i=0;i<6;i++){const u=t-.1-i*.15,p=SPR(u,.5,14);if(u<=0)continue;const x=300+i*10+(1-p)*500,y=h-110-i*14,rt=-6+i*2.4;g+=`<g transform="translate(${x.toFixed(1)},${y}) rotate(${rt.toFixed(1)})"><rect x="-120" y="-80" width="240" height="140" rx="8" fill="${i%2?'#D9822B':'#C9693E'}" stroke="${LINE}" stroke-width="3"/><path d="M-120 -80 l120 70 l120 -70" fill="none" stroke="#F4D0A0" stroke-width="3"/></g>`}
  const sw=t>1.05?SPR(t-1.05,.45,16):0;if(t>1.05)g+=glow(360,h-210,70,.5*(1-clamp(t-1.3)))+`<circle cx="360" cy="${h-200}" r="${(22*Math.max(.01,sw)).toFixed(1)}" fill="#F4B860" stroke="${LINE}" stroke-width="3"/>`;
  let d='M40 40';for(let x=40;x<=848;x+=24)d+=` L${x} ${(40+14*Math.sin(x/60+t*3)).toFixed(1)}`;g+=`<path d="${d}" fill="none" stroke="${LAMP}" stroke-width="4"/>`;
  for(let i=0;i<9;i++){const x=70+i*94,y=40+14*Math.sin(x/60+t*3);g+=`<path d="M${x-14} ${y.toFixed(1)} l14 30 l14 -30Z" fill="${i%2?'#F4D0A0':'#E9B98A'}"/>`}
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i+=2)E(t0+.1+i*.15+.15,'tick',{g:.6});E(t0+1.05,'thump',{g:.3});E(t0+1.1,'sparkle',{n:[24]})}},
 // s5 紙箱：三個搬家紙箱一個個疊上（0.1–0.9），最上面的箱子蓋子彈開、跳出一盞小檯燈；地上膠帶捲滾
 boxes:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  [[260,h-50,200,110],[280,h-160,170,96],[300,h-256,140,82]].forEach(([x,y,w,hh],i)=>{const u=t-.1-i*.25,p=SPR(u,.5,13);if(u<=0)return;const dy=(1-p)*-120+(i===2?-12*Math.abs(DECAY(u-.3,4,12)):0);/* 頂層紙箱落定再彈一下（約 12px） */g+=`<g transform="translate(0,${dy.toFixed(1)})" opacity="${clamp(u*6)}"><rect x="${x}" y="${y-hh}" width="${w}" height="${hh}" fill="#D9B48C" stroke="${LINE}" stroke-width="3"/><line x1="${x+w/2}" y1="${y-hh}" x2="${x+w/2}" y2="${y-hh+30}" stroke="#B98A6A" stroke-width="10"/></g>`});
  const lp=SPR(t-1.0,.4,14);if(t>1.0)g+=`<g transform="rotate(${(-70*lp).toFixed(1)} 300 ${h-338})"><rect x="300" y="${h-346}" width="70" height="10" fill="#C9A27A" stroke="${LINE}" stroke-width="2"/></g><g transform="translate(372,${(h-338-46*lp).toFixed(1)})"><path d="M-24 0 h48 l-10 -34 h-28Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><line x1="0" y1="0" x2="0" y2="30" stroke="${LINE}" stroke-width="4"/></g>`;
  const rl=(1-SPR(t-.5,.6,8))*200;g+=`<g transform="translate(${(620+rl).toFixed(1)},${h-80})"><circle r="30" fill="#F3D9A8" stroke="${LINE}" stroke-width="3"/><circle r="12" fill="${FACE}" stroke="${LINE}" stroke-width="2"/><line x1="0" y1="-30" x2="${(30*Math.sin(rl/30)).toFixed(1)}" y2="${(-30*Math.cos(rl/30)).toFixed(1)}" stroke="${LINE}" stroke-width="2" opacity=".5"/></g>`;
  return g},
  sfx(t0,s,E){[0,1,2].forEach(i=>E(t0+.1+i*.25+.2,'thump',{g:.25}));E(t0+1.05,'pop')}},
 // s6 指南針：指針亂轉（0.2–1.4）阻尼停住；底下一張空白小地圖、一隻紙鶴從右邊滑翔進來
 compass:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><path d="M80 ${h-60} l200 -60 l200 40 l200 -50 l140 30 v80 h-740Z" fill="#E9DFC9" stroke="${LINE}" stroke-width="2"/>`;
  const cx=330,cy=200;g+=`<circle cx="${cx}" cy="${cy}" r="140" fill="#FFFDF8" stroke="#8A5A44" stroke-width="12"/>`;
  [['北',0],['東',90],['南',180],['西',270]].forEach(([l,a])=>{const r=a*Math.PI/180;g+=T(cx+104*Math.sin(r),cy-104*Math.cos(r)+12,l,32,700,SUBC)});
  const ang=t<.2?20:20+340*EO((t-.2)/1.2)+60*DECAY(t-.2,1.6,7);g+=`<g transform="rotate(${ang.toFixed(1)} ${cx} ${cy})"><path d="M${cx} ${cy-90} l16 90 l-16 16 l-16 -16Z" fill="${LAMP}"/><path d="M${cx} ${cy+90} l16 -74 h-32Z" fill="#B9B2A8"/></g><circle cx="${cx}" cy="${cy}" r="10" fill="${LINE}"/>`;
  const fl=1-SPR(t-.6,.7,6),x=650+260*fl,y=150+16*Math.sin(t*3);g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><path d="M-60 0 l60 -20 l50 30 l-50 -6Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/><path d="M0 -20 l-10 40 l10 4Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:400,f1:900,dur:.9,g:.06});E(t0+1.4,'tick')}},
 // s7 步道（下集：一年工時）：步道牌從地上彈起（0.3）、箭頭牌擺盪、「30」小旗插下；路上光點往上流
 trail:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><path d="M0 ${h-40} q240 -150 480 -170 q220 -20 408 -150 V${h} H0Z" fill="#CDB896"/><path d="M80 ${h} q200 -130 400 -190 q200 -60 360 -170" fill="none" stroke="#E9DFC9" stroke-width="28" stroke-linecap="round"/>`;
  for(let k=0;k<5;k++){const u=((t*.4+k/5)%1),x=80+760*u,y=h-(130+260*u);g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6" fill="#FFF4D6" opacity="${(.8*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  const p=SPR(t-.3,.45,13),sw=8*DECAY(t-.55,2,7);g+=`<g transform="translate(240,${(h-110+(1-p)*120).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-150" stroke="#8A5A44" stroke-width="10"/><g transform="rotate(${sw.toFixed(1)} 0 -140)"><path d="M-10 -170 h170 l26 26 l-26 26 h-170Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(78,-133,'下班時間',32,700,TXT)}</g></g>`;
  const f=SPR(t-.9,.45,15);if(t>.9)g+=`<g transform="translate(640,${(h-250+(1-f)*-60).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-90" stroke="${LINE}" stroke-width="5"/><path d="M0 -90 h70 l-14 22 l14 22 h-70Z" fill="${LAMP}"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'thump',{g:.3});E(t0+.9,'tick')}}
};
