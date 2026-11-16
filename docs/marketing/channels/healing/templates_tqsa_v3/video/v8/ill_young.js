// 談晴說礙 11/19 未滿 25 歲月薪中位數影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261119v_young」）。輪播用過的階梯、薪資袋不再用。
const ILL={
 // s1 通勤腳踏車：車輪轉、0.4 從左騎進畫面（過衝回停）、車籃裡的便當袋晃、背景路燈一盞盞往後退
 bike:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F6E4C8"/><rect x="0" y="${h-110}" width="888" height="110" fill="#CDB896"/>`;
  g+=`<circle cx="730" cy="110" r="56" fill="#F4B860" opacity=".75"/>`;
  for(let i=0;i<4;i++){const x=((i*260-t*120)%1040+1040)%1040-80;g+=`<line x1="${x}" y1="${h-110}" x2="${x}" y2="${h-330}" stroke="#A98C70" stroke-width="6"/><circle cx="${x}" cy="${h-338}" r="12" fill="#FFF1D2" stroke="#A98C70" stroke-width="2"/>`}
  for(let i=0;i<6;i++){const x=((i*170-t*220)%1020+1020)%1020-60;g+=`<rect x="${x}" y="${h-62}" width="80" height="8" rx="4" fill="#FFFDF8" opacity=".7"/>`}
  const bx=380-420*(1-SPR(t-.1,.55,8)),by=h-150+(t>.1?2*Math.sin(t*14):0),rot=t*6;
  const wheel=(cx)=>`<g transform="translate(${cx},0)"><circle r="62" fill="none" stroke="${LINE}" stroke-width="7"/>${[0,1,2,3].map(k=>`<line x1="0" y1="0" x2="${(62*Math.cos(rot+k*Math.PI/4)).toFixed(1)}" y2="${(62*Math.sin(rot+k*Math.PI/4)).toFixed(1)}" stroke="${LINE}" stroke-width="2"/><line x1="0" y1="0" x2="${(-62*Math.cos(rot+k*Math.PI/4)).toFixed(1)}" y2="${(-62*Math.sin(rot+k*Math.PI/4)).toFixed(1)}" stroke="${LINE}" stroke-width="2"/>`).join('')}</g>`;
  const sw=8*DECAY(t-.9,2.5,10);
  g+=`<g transform="translate(${bx.toFixed(1)},${by.toFixed(1)})">${wheel(-100)}${wheel(120)}<path d="M-100 0 L0 -10 L60 -100 L-40 -100Z M0 -10 L120 0 M60 -100 L80 -140 h40 M-40 -100 L-50 -130 h-40" fill="none" stroke="${LAMP}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>`+
   `<g transform="rotate(${sw.toFixed(1)} 120 -140)"><path d="M100 -140 h70 l-10 60 h-50Z" fill="#E9C9A6" stroke="${LINE}" stroke-width="3"/><rect x="112" y="-170" width="46" height="34" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/></g></g>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:300,f1:700,dur:.5,g:.08});E(t0+.6,'tick');E(t0+.9,'bell',{n:[24],g:.3})}},
 // s2 資料櫃：三格抽屜依序拉出（過衝回彈），中間抽屜的資料夾抽起來、標籤寫「薪資統計」；桌上檯曆紙角微動
 cabinet:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/><rect x="250" y="20" width="388" height="${h-70}" rx="14" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<3;i++){const y=40+i*((h-110)/3),hh=(h-110)/3-14,o=40*SPR(t-.15-i*.22,.45,12)*(i===1?1.6:1);
   if(i===1){const up=-90*SPR(t-.9,.5,11);g+=`<g transform="translate(0,${up.toFixed(1)})"><rect x="380" y="${y-20}" width="200" height="90" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><rect x="380" y="${y-48}" width="110" height="34" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(480,y+32,'薪資統計',32,700,'#FFFFFF')}</g>`}
   g+=`<rect x="${(262+o).toFixed(1)}" y="${y}" width="364" height="${hh}" rx="8" fill="#D9B48C" stroke="${LINE}" stroke-width="3"/><rect x="${(410+o).toFixed(1)}" y="${y+hh/2-8}" width="70" height="16" rx="6" fill="${LINE}"/>`}
  g+=`<rect x="680" y="${h-170}" width="150" height="120" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(755,h-98,'1–7 月',32,700,TXT)+`<path d="M800 ${h-170} l30 ${(14+6*Math.sin(t*3)).toFixed(1)} l-30 4Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<path d="M100 ${h-50} v-90 q0 -30 30 -30 h20 q30 0 30 30 v90" fill="#C9D3C9" stroke="${LINE}" stroke-width="3"/><path d="M140 ${h-170} q${(-24+4*Math.sin(t*2)).toFixed(1)} -40 -10 -80 M140 ${h-170} q${(24+4*Math.sin(t*2+1)).toFixed(1)} -40 10 -90" stroke="#7E8F6A" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  return g},
  sfx(t0,s,E){[0,1,2].forEach(i=>E(t0+.15+i*.22,'tick',{g:.7}));E(t0+.9,'glide',{f0:500,f1:900,dur:.25,g:.08})}},
 // s3 小樹苗與大樹：兩棵樹由土裡長出（小的先、大的後），大樹葉子一片片彈出，落葉一片飄下
 trees:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#CDB896"/>`;
  const grow=(x,H,a,lv)=>{const p=SPR(t-a,.6,9),hh=H*p;let s=`<rect x="${x-10}" y="${h-80-hh}" width="20" height="${hh.toFixed(1)}" rx="6" fill="#8A5A44"/>`;
   for(let i=0;i<lv;i++){const u=t-a-.3-i*.07,q=SPR(u,.45,16);if(u<=0)continue;const ang=i/lv*Math.PI*2,r=H*.28,cx=x+r*Math.cos(ang)*.9,cy=h-80-hh-10+r*Math.sin(ang)*.6;s+=`<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${(H*.16*Math.max(.01,q)).toFixed(1)}" fill="${i%2?'#9CB38A':'#8FA078'}"/>`}return s};
  g+=grow(250,120,.1,5)+grow(620,190,.4,9);
  const lf=t-1.6;if(lf>0){const y=h-330+lf*90,x=660+30*Math.sin(lf*4);if(y<h-90)g+=`<ellipse cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" rx="12" ry="7" fill="#E9B98A" transform="rotate(${(lf*120).toFixed(0)} ${x.toFixed(1)} ${y.toFixed(1)})"/>`}
  g+=`<rect x="150" y="${h-74}" width="200" height="62" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`+T(250,h-29,'25 歲前',44,700,TXT)+`<rect x="530" y="${h-74}" width="180" height="62" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`+T(620,h-29,'50 後',44,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:200,f1:500,dur:.4,g:.08});E(t0+.4,'glide',{f0:200,f1:600,dur:.5,g:.1});[0,1,2].forEach(i=>E(t0+.75+i*.14,'sparkle',{n:[22+i*2],g:.5}))}},
 // s4 排隊：九個人形由矮到高依序站好（左→右彈入），正中間那一位亮起、頭上小旗彈出
 queue:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  for(let i=0;i<9;i++){const u=t-.08-i*.07,p=SPR(u,.5,15);if(u<=0)continue;const x=84+i*90,H=80+i*12,mid=i===4,on=mid?clamp((t-.9)*5):0;
   g+=`<g transform="translate(${x},${(h-50+(1-p)*30).toFixed(1)})" opacity="${clamp(u*8)}">${on?glow(0,-H/2,80,.55*on):''}<circle cx="0" cy="${-H-6}" r="20" fill="${on>.5?LAMP:'#B98A6A'}"/><rect x="-24" y="${-H+16}" width="48" height="${H-16}" rx="20" fill="${on>.5?LAMP:'#C9A27A'}"/></g>`}
  const f=SPR(t-1.05,.45,16);if(t>1.05)g+=`<g transform="translate(444,${h-50-128-60}) scale(${Math.max(.01,f).toFixed(3)})" opacity="${clamp((f-.1)/.85).toFixed(3)}"><line x1="0" y1="20" x2="0" y2="-46" stroke="${LINE}" stroke-width="6"/><path d="M0 -46 h66 v44 h-66Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(33,-12,'中',34,700,HINT)}</g>`;
  g+=T(84,h-12,'低',32,700,SUBC)+T(804,h-12,'高',32,700,SUBC);
  return g},
  sfx(t0,s,E){for(let i=0;i<9;i+=2)E(t0+.08+i*.07+.1,'tick',{g:.5});E(t0+.9,'bell',{n:[19],g:.4});E(t0+1.1,'pop')}},
 // s5 兩台小車在跑道：同時起跑（0.2），右邊跑道那台稍微快一點、先到虛線；輪子轉、車後小煙
 race:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/>`;
  [0,1].forEach(i=>{const y=70+i*140;g+=`<rect x="40" y="${y}" width="808" height="110" rx="14" fill="#D9C4A0"/><line x1="60" y1="${y+55}" x2="828" y2="${y+55}" stroke="#FFFDF8" stroke-width="4" stroke-dasharray="20 18"/>`});
  g+=`<line x1="760" y1="60" x2="760" y2="330" stroke="${LINE}" stroke-width="4" stroke-dasharray="12 10"/>`;
  [[0,.244,LAMP],[1,.318,'#B98A6A']].forEach(([i,sp,c])=>{const y=70+i*140+55,run=clamp((t-.2)/2.2),p=1-Math.pow(1-run,3),x=250+(440*sp/.318)*p*.95;
   g+=`<g transform="translate(${x.toFixed(1)},${y})"><rect x="0" y="-30" width="120" height="44" rx="14" fill="${c}" stroke="${LINE}" stroke-width="3"/><rect x="24" y="-54" width="64" height="30" rx="10" fill="${c}" stroke="${LINE}" stroke-width="3"/><circle cx="26" cy="18" r="14" fill="${LINE}"/><circle cx="96" cy="18" r="14" fill="${LINE}"/></g>`;
   if(run<1)for(let k=0;k<3;k++){const u=((t*1.5+k/3)%1);g+=`<circle cx="${(x-14-u*50).toFixed(1)}" cy="${(y+4-u*14).toFixed(1)}" r="${(8+u*8).toFixed(1)}" fill="#FFFDF8" opacity="${(.6*(1-u)*clamp(t-.2)*(1-run)).toFixed(2)}"/>`}});
  g+=`<rect x="52" y="86" width="190" height="44" rx="10" fill="${FACE3}" opacity=".9"/>`+T(62,120,'未滿 25 歲',32,700,HINT,'start')+`<rect x="52" y="226" width="170" height="44" rx="10" fill="${FACE3}" opacity=".9"/>`+T(62,260,'25–29 歲',32,700,TXT,'start');
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:300,f1:800,dur:.6,g:.1});E(t0+.2,'click')}},
 // s6 錢包：三張紙鈔依序滑進錢包（本薪、津貼），另兩張虛線紙鈔（加班費、獎金）浮在外面上下輕飄；錢包扣子「啪」扣上
 wallet:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  g+=`<rect x="220" y="${h-250}" width="360" height="190" rx="24" fill="#8A5A44" stroke="${LINE}" stroke-width="4"/>`;
  [0,1].forEach(i=>{const u=SPR(t-.15-i*.25,.55,11),y=h-330+90*u;g+=`<rect x="${260+i*40}" y="${y.toFixed(1)}" width="230" height="110" rx="8" fill="#CFE0C2" stroke="${LINE}" stroke-width="3"/>`+T(375+i*40,y+42,i?'津貼':'本薪',32,700,TXT)});
  g+=`<rect x="220" y="${h-180}" width="360" height="120" rx="24" fill="#9C6A50" stroke="${LINE}" stroke-width="4"/>`;
  const cl=t>1.0?3*DECAY(t-1.0,6,20):0;g+=`<circle cx="540" cy="${(h-140+cl).toFixed(1)}" r="16" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  [[680,h-300,'加班費',0],[700,h-160,'獎金',1.5]].forEach(([x,y,l,ph])=>{const a=clamp((t-.6)*4);g+=`<g opacity="${(.85*a).toFixed(2)}" transform="translate(0,${(8*Math.sin(t*2.4+ph)).toFixed(1)})"><rect x="${x-90}" y="${y}" width="180" height="90" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3" stroke-dasharray="10 8"/>${T(x,y+56,l,32,700,SUBC)}</g>`});
  return g},
  sfx(t0,s,E){E(t0+.15,'glide',{f0:800,f1:400,dur:.25,g:.07});E(t0+.4,'glide',{f0:800,f1:400,dur:.25,g:.07});E(t0+1.0,'click')}},
 // s7 電梯樓層燈：樓層數字由 1 往上跳（0.2–1.2），每跳一格燈亮一下，停在「?」樓；電梯門縫透光
 elevator:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#E9DFCF"/><rect x="250" y="120" width="388" height="${h-120}" fill="#C9C3B8" stroke="${LINE}" stroke-width="4"/>`;
  const op=8+6*Math.sin(Math.min(t,1.4)*1.8);g+=`<rect x="${444-op}" y="130" width="${op*2}" height="${h-130}" fill="#FFE9B8" opacity=".8"/><rect x="262" y="130" width="${182-op}" height="${h-130}" fill="#D8D2C6" stroke="${LINE}" stroke-width="2"/><rect x="${444+op}" y="130" width="${182-op}" height="${h-130}" fill="#D8D2C6" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="290" y="24" width="308" height="80" rx="14" fill="#3A3836"/>`;
  for(let i=0;i<5;i++){const lit=t>.2+i*.22;g+=`<circle cx="${320+i*62}" cy="64" r="20" fill="${lit?'#F4B860':'#5A5652'}"/>`+T(320+i*62,75,i===4?'?':String(i+1),i===4?32:30+2,700,lit?TXT:'#8E8A84')}
  const ar=t>1.2?-10*DECAY(t-1.2,4,12):0;g+=`<path d="M700 ${200+ar} l30 -36 l30 36Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><rect x="690" y="230" width="80" height="80" rx="40" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<5;i++)E(t0+.2+i*.22,'tick',{g:.6});E(t0+1.2,'bell',{n:[21],g:.35})}},
 // s8 桌上房屋模型：模型由上落下回彈、標價吊牌擺盪衰減、牌上是「?」；旁邊一支鉛筆滾動
 housemodel:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#C9A27A"/>`;
  const d=SPR(t-.15,.42,12),y=(h-90)-(1-d)*-0-(1-d)*160;g+=`<g transform="translate(0,${(-(1-d)*160).toFixed(1)})"><path d="M300 ${h-90} v-150 l120 -90 l120 90 v150Z" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><path d="M280 ${h-230} l140 -105 l140 105" fill="none" stroke="#8A5A44" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/><rect x="390" y="${h-170}" width="60" height="80" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="330" y="${h-210}" width="44" height="44" fill="#FFE9B8" stroke="${LINE}" stroke-width="2"/><rect x="466" y="${h-210}" width="44" height="44" fill="#FFE9B8" stroke="${LINE}" stroke-width="2"/></g>`;
  const sw=18*DECAY(t-.5,1.8,6),px=560,py=h-250;g+=`<line x1="540" y1="${h-238}" x2="${px+20}" y2="${py}" stroke="${LINE}" stroke-width="3" opacity="${clamp(d*2)}"/><g transform="rotate(${sw.toFixed(1)} ${px+20} ${py})" opacity="${clamp(d*2)}"><rect x="${px+20}" y="${py-10}" width="120" height="70" rx="10" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(px+80,py+40,'$ ?',34,700,'#FFFFFF')}</g>`;
  const rl=(1-SPR(t-.8,.6,8))*120;g+=`<g transform="translate(${(720+rl).toFixed(1)},${h-102}) rotate(${(rl*3).toFixed(0)})"><rect x="-70" y="-7" width="140" height="14" rx="5" fill="#F4B860" stroke="${LINE}" stroke-width="2"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.35,'thump',{g:.35});E(t0+.55,'tick');E(t0+.8,'glide',{f0:600,f1:400,dur:.3,g:.06})}}
};
