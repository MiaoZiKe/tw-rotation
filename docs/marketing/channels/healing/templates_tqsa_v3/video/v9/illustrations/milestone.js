 milestone:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/><path d="M0 ${h} L380 120 L508 120 L888 ${h}Z" fill="#D9C4A0"/><path d="M444 ${h} L444 120" stroke="#FFFDF8" stroke-width="6" stroke-dasharray="24 22"/>`;
  [[180,h-90,1],[290,h-190,.8],[360,h-250,.62],[400,h-290,.5]].forEach(([x,y,sc],i)=>{const u=t-.2-i*.22,p=SPR(u,.45,16);if(u<=0)return;g+=`<g transform="translate(${x},${y}) scale(${(sc*Math.max(.01,p)).toFixed(3)})"><path d="M-40 0 v-70 q0 -30 40 -30 q40 0 40 30 v70Z" fill="${i===3?LAMP:FACE3}" stroke="${LINE}" stroke-width="4"/></g>`});
  for(let k=0;k<6;k++){const u=((t*.5+k/6)%1);g+=`<circle cx="444" cy="${(h-u*(h-140)).toFixed(1)}" r="${(8-6*u).toFixed(1)}" fill="#FFF4D6" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=`<rect x="600" y="40" width="220" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(710,88,'退休那天',32,700,TXT);
  return g},
  sfx(t0,s,E){[0,1,2,3].forEach(i=>E(t0+.2+i*.22+.08,'tick',{g:.6}));E(t0+.95,'pop')}}
