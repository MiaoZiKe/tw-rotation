 jarpair:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#E4D3B8"/>`;
  // 左：平均那罐（有存）——小硬幣先落、大硬幣彈兩下、罐子晃一下
  const sw=2.5*DECAY(t-1.05,3,14);g+=`<g transform="translate(-190 0)"><g transform="rotate(${sw.toFixed(2)} 444 ${h-80})"><path d="M330 ${h-80} v-200 q0 -30 30 -36 h168 q30 6 30 36 v200Z" fill="#F5F0E6" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/><rect x="350" y="${h-336}" width="188" height="28" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<4;i++)g+=`<ellipse cx="${384+i*40}" cy="${h-98}" rx="26" ry="10" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`;
  const c1=SPR(t-.15,.5,14),y1=h-420+(h-140-(h-420))*c1;if(t>.15)g+=`<g transform="translate(410,${y1.toFixed(1)})"><circle r="24" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/>${T(0,10,'存',32,700,TXT)}</g>`;
  const fall=clamp((t-.7)/.35),y2=fall<1?(h-460)+(h-180-(h-460))*fall*fall:(h-180)-26*Math.abs(DECAY(t-1.05,4,11));if(t>.7)g+=`<g transform="translate(474,${y2.toFixed(1)})"><circle r="40" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,13,'29萬',30,700,'#FFFFFF')}</g>`;
  g+=`</g></g>`;
  g+=T(284,h-30,'全體平均',30,700,TXT);
  // 右：最低兩成那罐（空）——0.5 起罐子被推倒、彈一下躺平，裡面一枚硬幣都沒有（虛線圈圈代表「倒不出東西」）
  const tip=SPR(t-.5,.45,9),ang=90*tip,px=560,py=h-80;
  g+=`<g transform="rotate(${ang.toFixed(2)} ${px} ${py})"><path d="M${px-150} ${py} v-170 q0 -30 30 -34 h90 q30 4 30 34 v170Z" fill="#F5F0E6" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/><rect x="${px-136}" y="${py-226}" width="122" height="24" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  if(t>1.1)g+=`<circle cx="${px+250}" cy="${py-30}" r="22" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 7" opacity=".6"/>`;
  g+=T(660,h-30,'最低20%',30,700,TXT)+(t>1.2?T(px+100,py-170,'-17,703',34,700,LAMP):'');
  [[160,h-250],[340,h-210]].forEach(([x,y],i)=>g+=sparkle(x,y,10,.3+.35*tw(t,i*2,3.2)));
  return g},
  sfx(t0,s,E){E(t0+.3,'tick');E(t0+.5,'glide',{f0:500,f1:220,dur:.45,g:.07});E(t0+1.05,'thump',{g:.4});E(t0+1.15,'thump',{g:.25})}}
