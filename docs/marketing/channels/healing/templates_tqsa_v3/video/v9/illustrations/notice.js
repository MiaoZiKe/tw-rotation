 notice:{draw(t,h){let g=`<rect x="40" y="24" width="808" height="${h-48}" rx="18" fill="#C9A27A" stroke="${LINE}" stroke-width="4"/><rect x="60" y="44" width="768" height="${h-88}" rx="10" fill="#D9B48C"/>`;
  g+=`<rect x="90" y="70" width="200" height="140" rx="4" fill="#F3EADB" transform="rotate(-5 190 140)" stroke="${LINE}" stroke-width="2"/><rect x="620" y="64" width="180" height="120" rx="4" fill="#EFE7D7" transform="rotate(4 710 124)" stroke="${LINE}" stroke-width="2"/>`;
  const drop=SPR(t-.15,.45,15),ty=-60*(1-drop),fl=14*DECAY(t-.9,1.8,8)+8*DECAY(t-2.2,2,8);
  g+=`<g transform="translate(0,${ty.toFixed(1)})" opacity="${clamp((t-.1)*6)}"><path d="M320 54 h250 v${(h-130).toFixed(0)} l-${(30+fl).toFixed(1)} 10 h-220Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(445,110,'就學貸款公告',32,700,TXT)}`;
  for(let i=0;i<4;i++)g+=`<line x1="346" y1="${146+i*34}" x2="${546-(i%2)*60}" y2="${146+i*34}" stroke="${LINE}" stroke-width="2" opacity=".45"/>`;g+=`<circle cx="445" cy="58" r="11" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  const mx=740-160*SPR(t-.8,.55,10),my=h-96+6*Math.sin(t*2.2);g+=`<g transform="translate(${mx.toFixed(1)},${my.toFixed(1)})"><circle r="46" fill="#FFF8EA" fill-opacity=".6" stroke="${LINE}" stroke-width="7"/><line x1="32" y1="32" x2="78" y2="78" stroke="${LINE}" stroke-width="12" stroke-linecap="round"/>${T(0,14,'?',40,700,HINT)}</g>`;
  return g},
  sfx(t0,s,E){E(t0+.35,'thump',{g:.3});E(t0+.9,'glide',{f0:700,f1:400,dur:.3,g:.08})}}
