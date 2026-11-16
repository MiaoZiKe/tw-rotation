 coinjar:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#E4D3B8"/>`;
  const sw=2.5*DECAY(t-1.05,3,14);g+=`<g transform="rotate(${sw.toFixed(2)} 444 ${h-80})"><path d="M330 ${h-80} v-200 q0 -30 30 -36 h168 q30 6 30 36 v200Z" fill="#F5F0E6" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/><rect x="350" y="${h-336}" width="188" height="28" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  // 罐底已有的硬幣
  for(let i=0;i<4;i++)g+=`<ellipse cx="${384+i*40}" cy="${h-98}" rx="26" ry="10" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`;
  const c1=SPR(t-.15,.5,14),y1=h-420+(h-140-(h-420))*c1;if(t>.15)g+=`<g transform="translate(410,${y1.toFixed(1)})"><circle r="24" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/>${T(0,10,'學',26+6,700,TXT)}</g>`;
  const fall=clamp((t-.7)/.35),y2=fall<1?(h-460)+(h-180-(h-460))*fall*fall:(h-180)-26*Math.abs(DECAY(t-1.05,4,11));if(t>.7)g+=`<g transform="translate(474,${y2.toFixed(1)})"><circle r="40" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,13,'1%',34,700,'#FFFFFF')}</g>`;
  g+=`</g>`;
  [[372,h-260],[520,h-230],[430,h-300]].forEach(([x,y],i)=>g+=sparkle(x,y,10,.35+.4*tw(t,i*2,3.2)));
  return g},
  sfx(t0,s,E){E(t0+.3,'tick');E(t0+1.05,'thump',{g:.4});E(t0+1.25,'tick',{g:.7})}}
