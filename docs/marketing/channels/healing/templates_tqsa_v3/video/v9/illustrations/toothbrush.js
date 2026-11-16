 toothbrush:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/><rect x="0" y="0" width="888" height="${h-60}" fill="#EDEFE9"/>`;
  for(let i=0;i<6;i++)for(let j=0;j<4;j++)g+=`<rect x="${i*150}" y="${j*80}" width="148" height="78" fill="none" stroke="#D8DCD2" stroke-width="2"/>`;
  const brush=(x,y,ang,c)=>`<g transform="translate(${x},${y}) rotate(${ang.toFixed(1)})"><rect x="-9" y="-150" width="18" height="150" rx="9" fill="${c}" stroke="${LINE}" stroke-width="3"/><rect x="-14" y="-192" width="28" height="46" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/></g>`;
  const d=SPR(t-.4,.5,12),tap=4*DECAY(t-1.0,4,16);g+=brush(420,h-150,-12-tap,'#B98A6A')+brush(470,h-150-(1-d)*170,12+tap,LAMP);
  g+=`<path d="M360 ${h-60} l-14 -150 h196 l-14 150Z" fill="#DCE8E4" fill-opacity=".9" stroke="${LINE}" stroke-width="4"/>`;
  [[400,h-140],[500,h-110]].forEach(([x,y],i)=>g+=sparkle(x,y,9,.3+.5*tw(t,i*2,3)));
  g+=`<rect x="640" y="${h-170}" width="160" height="110" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(720,h-104,'兩個人',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.4,'glide',{f0:800,f1:400,dur:.3,g:.06});E(t0+1.0,'tick',{g:.8})}}
