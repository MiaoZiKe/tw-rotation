 shoerack:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-60}" width="888" height="60" fill="#C9A27A"/>`;
  g+=`<rect x="80" y="40" width="728" height="${h-110}" rx="12" fill="#D9B48C" stroke="${LINE}" stroke-width="4"/><line x1="80" y1="${(h-70)/2+20}" x2="808" y2="${(h-70)/2+20}" stroke="${LINE}" stroke-width="4"/>`;
  const shoe=(x,y,w,c)=>`<path d="M${x} ${y} h${w*.65} q${w*.35} 0 ${w*.35} ${w*.4} h-${w}Z" fill="${c}" stroke="${LINE}" stroke-width="2"/>`;
  [[130,170,'#6E4636'],[330,140,'#9C6A50'],[510,100,'#E9B98A']].forEach(([x,w,c],i)=>{const u=t-.1-i*.18,p=SPR(u,.5,14);if(u<=0)return;const y=(h-70)/2+20-(1-p)*30;g+=`<g opacity="${clamp(u*6)}">${shoe(x,y,w*.5,c)}${shoe(x+w*.55,y,w*.5,c)}</g>`});
  const u=t-1.0,p=SPR(u,.4,16);if(u>0){const y=(h-60)-(1-p)*80,lc=14*DECAY(u,2.2,9);g+=`<g>${shoe(560,y,120,'#FFFDF8')}${shoe(690,y,120,'#FFFDF8')}<path d="M600 ${y-14} q20 ${(-20+lc).toFixed(1)} 40 0" stroke="${LAMP}" stroke-width="5" fill="none"/></g>`}
  g+=T(340,90,'家戶',32,700,SUBC)+T(680,(h-70)/2+80,'剛出社會',32,700,HINT);
  return g},
  sfx(t0,s,E){[.1,.28,.46].forEach(x=>E(t0+x+.12,'tick',{g:.5}));E(t0+1.1,'thump',{g:.3})}}
