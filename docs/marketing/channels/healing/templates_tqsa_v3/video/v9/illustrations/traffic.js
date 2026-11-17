 traffic:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-50}" width="888" height="50" fill="#CDB896"/>`;
  g+=`<line x1="660" y1="${h-50}" x2="660" y2="115" stroke="${LINE}" stroke-width="12"/><line x1="636" y1="115" x2="666" y2="115" stroke="${LINE}" stroke-width="12"/><rect x="250" y="40" width="388" height="150" rx="40" fill="#4A4744" stroke="${LINE}" stroke-width="4"/>`;
  const st=t<.3?-1:t<.7?0:t<1.1?1:2,cols=['#9CC08A','#F2D16B',LAMP];[0,1,2].forEach(i=>{const on=i===st;g+=(on?glow(320+i*124,115,90,.55):'')+`<circle cx="${320+i*124}" cy="115" r="46" fill="${on?cols[i]:'#6A6662'}" stroke="${LINE}" stroke-width="3"/>`});
  g+=T(320,236,'可合理',32,700,SUBC)+T(444,236,'略低',32,700,SUBC)+T(568,236,'偏低',32,700,st===2?HINT:SUBC);
  const sw=8*DECAY(t-1.1,2,8);g+=`<g transform="rotate(${sw.toFixed(1)} 780 ${h-180})"><line x1="780" y1="${h-50}" x2="780" y2="${h-180}" stroke="${LINE}" stroke-width="6"/><rect x="706" y="${h-240}" width="148" height="70" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(780,h-193,'41.46%',32,700,TXT)}</g>`;
  return g},
  sfx(t0,s,E){[.3,.7,1.1].forEach(x=>E(t0+x,'click'));E(t0+1.1,'bell',{n:[17],g:.35})}}
