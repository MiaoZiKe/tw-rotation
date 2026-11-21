 cardrack:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE2D0"/><rect x="80" y="40" width="728" height="${h-90}" rx="14" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<25;i++){const u=t-.1-i*.035,p=SPR(u,.5,15);const x=104+i*28.4,pt=i===24;if(u<=0){g+=`<rect x="${x.toFixed(1)}" y="150" width="22" height="18" fill="#8A5A44"/>`;continue}
   g+=`<rect x="${x.toFixed(1)}" y="${(70-(1-p)*60).toFixed(1)}" width="22" height="160" rx="3" fill="${pt?LAMP:'#FFFDF8'}" stroke="${LINE}" stroke-width="2"/><rect x="${x.toFixed(1)}" y="150" width="22" height="18" fill="#8A5A44"/>`}
  g+=T(400,h-74,'全職',32,700,'#FFFFFF')+T(770,h-74,'兼職',32,700,'#FFFFFF');
  return g},
  sfx(t0,s,E){for(let i=0;i<14;i+=3)E(t0+.1+i*.06+.1,'tick',{g:.5});E(t0+.9,'tick',{g:.9})}}
