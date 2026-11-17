 drinkbar:{draw(t,h){let g=`<rect x="0" y="${h-120}" width="888" height="120" fill="#C9A27A"/><rect x="0" y="${h-128}" width="888" height="12" fill="#9C7450"/>`;
  g+=`<rect x="30" y="30" width="190" height="80" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(125,84,'今日手搖',34,700,TXT);
  const sh=t<1.0?-26*Math.abs(Math.sin(t*Math.PI*3/0.8)):0,tilt=t>1.0&&t<1.6?-60*Math.sin(Math.PI*(t-1.0)/.6):0;
  g+=`<g transform="translate(250,${(h-260+sh).toFixed(1)}) rotate(${tilt.toFixed(1)} 40 60)"><path d="M0 0 h80 l-10 140 h-60Z" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/><rect x="-4" y="-30" width="88" height="34" rx="8" fill="#BFC3BB" stroke="${LINE}" stroke-width="3"/></g>`;
  const lv=clamp((t-1.1)/.5),sl=t>1.7?(1-SPR(t-1.7,.55,11))*0:0,cx=420+200*SPR(t-1.7,.55,10);
  g+=`<g transform="translate(${cx.toFixed(1)},${h-128})"><path d="M-60 -170 h120 l-14 170 h-92Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="3"/><path d="M${-60+14*(1-lv)} ${-150*lv} h${120-28*(1-lv)} l${-14*lv} ${150*lv} h${-92}Z" fill="#C79A6B"/>`;
  for(let i=0;i<5;i++)g+=`<circle cx="${-30+i*14}" cy="${-14-(i%2)*14}" r="7" fill="#4A3B30" opacity="${lv.toFixed(2)}"/>`;
  const st=SPR(t-2.1,.5,14);if(t>2.1)g+=`<line x1="18" y1="${(-260+80*st).toFixed(1)}" x2="${(30).toFixed(1)}" y2="${(-40).toFixed(1)}" stroke="${LAMP}" stroke-width="10" stroke-linecap="round"/>`;g+=`</g>`;
  if(t>1.0&&t<1.6)g+=`<path d="M300 ${h-210} q60 20 100 60" stroke="#C79A6B" stroke-width="8" fill="none" opacity=".8"/>`;
  return g},
  sfx(t0,s,E){[.27,.53,.8].forEach(x=>E(t0+x,'tick',{g:.8}));E(t0+1.1,'glide',{f0:300,f1:600,dur:.4,g:.08});E(t0+1.7,'glide',{f0:700,f1:300,dur:.3,g:.08});E(t0+2.15,'pop')}}
