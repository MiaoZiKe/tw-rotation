 elevator:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#E9DFCF"/><rect x="250" y="120" width="388" height="${h-120}" fill="#C9C3B8" stroke="${LINE}" stroke-width="4"/>`;
  const op=8+6*Math.sin(Math.min(t,1.4)*1.8);g+=`<rect x="${444-op}" y="130" width="${op*2}" height="${h-130}" fill="#FFE9B8" opacity=".8"/><rect x="262" y="130" width="${182-op}" height="${h-130}" fill="#D8D2C6" stroke="${LINE}" stroke-width="2"/><rect x="${444+op}" y="130" width="${182-op}" height="${h-130}" fill="#D8D2C6" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="290" y="24" width="308" height="80" rx="14" fill="#3A3836"/>`;
  for(let i=0;i<5;i++){const lit=t>.2+i*.22;g+=`<circle cx="${320+i*62}" cy="64" r="20" fill="${lit?'#F4B860':'#5A5652'}"/>`+T(320+i*62,75,i===4?'?':String(i+1),i===4?32:30+2,700,lit?TXT:'#8E8A84')}
  const ar=t>1.2?-10*DECAY(t-1.2,4,12):0;g+=`<path d="M700 ${200+ar} l30 -36 l30 36Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><rect x="690" y="230" width="80" height="80" rx="40" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<5;i++)E(t0+.2+i*.22,'tick',{g:.6});E(t0+1.2,'bell',{n:[21],g:.35})}}
