 signpost:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const p=SPR(t-.15,.45,13),sw=10*DECAY(t-.45,1.8,7);g+=`<g transform="translate(260,${(h-60+(1-p)*200).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-200" stroke="#8A5A44" stroke-width="12"/><g transform="rotate(${sw.toFixed(1)} 0 -200)"><path d="M0 -200 l-110 0 l0 -110 h220 v110Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/>${T(0,-240,'注意口徑',36,700,'#FFFFFF')}</g></g>`;
  g+=`<rect x="460" y="120" width="360" height="140" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(640,180,'全職＋兼職',34,700,TXT)+T(640,226,'一起平均',32,400,SUBC);
  const mx=440+380*EO(clamp((t-.8)/1.2));g+=`<g transform="translate(${mx.toFixed(1)},${h-90})"><circle r="34" fill="#FFF8EA" fill-opacity=".5" stroke="${LINE}" stroke-width="6"/><line x1="24" y1="24" x2="56" y2="56" stroke="${LINE}" stroke-width="10" stroke-linecap="round"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'thump',{g:.3});E(t0+.8,'glide',{f0:600,f1:900,dur:.6,g:.05})}}
