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
  sfx(t0,s,E){for(let i=0;i<11;i++)E(t0+.2+i*.13,'tick',{g:.5});E(t0+1.7,'bell',{n:[21],g:.4});E(t0+1.7,'sparkle',{n:[24]})}}
