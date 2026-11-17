 train:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE2D0"/><rect x="0" y="${h-70}" width="888" height="70" fill="#C9B9A2"/><rect x="0" y="${h-80}" width="888" height="12" fill="#F4D27A"/>`;
  const p=1-Math.exp(-Math.max(0,t-.1)*3.2),x=900-760*p+(t>1.0?4*DECAY(t-1.0,5,14):0);
  for(let c=0;c<3;c++){const cx=x+c*290+(t>.9?2*c*DECAY(t-.9,5,16):0);g+=`<rect x="${cx.toFixed(1)}" y="${h-250}" width="280" height="160" rx="22" fill="#E9E4DA" stroke="${LINE}" stroke-width="4"/><rect x="${(cx).toFixed(1)}" y="${h-130}" width="280" height="14" fill="${LAMP}"/>`;
   for(let wi=0;wi<3;wi++)g+=`<rect x="${(cx+24+wi*86).toFixed(1)}" y="${h-226}" width="64" height="56" rx="8" fill="#C9D3C9" stroke="${LINE}" stroke-width="2"/>`}
  g+=`<circle cx="150" cy="80" r="44" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;const sc=(Math.floor(t*2)+SPR((t*2)%1,.45,40))*Math.PI/30*6;g+=`<line x1="150" y1="80" x2="${150+36*Math.sin(sc)}" y2="${80-36*Math.cos(sc)}" stroke="${LAMP}" stroke-width="3"/><line x1="150" y1="80" x2="150" y2="52" stroke="${TXT}" stroke-width="5"/>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:300,f1:120,dur:.9,g:.1});E(t0+1.0,'thump',{g:.3})}}
