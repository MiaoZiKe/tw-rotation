 wallet:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  g+=`<rect x="220" y="${h-250}" width="360" height="190" rx="24" fill="#8A5A44" stroke="${LINE}" stroke-width="4"/>`;
  [0,1].forEach(i=>{const u=SPR(t-.15-i*.25,.55,11),y=h-330+90*u;g+=`<rect x="${260+i*40}" y="${y.toFixed(1)}" width="230" height="110" rx="8" fill="#CFE0C2" stroke="${LINE}" stroke-width="3"/>`+T(375+i*40,y+42,i?'津貼':'本薪',32,700,TXT)});
  g+=`<rect x="220" y="${h-180}" width="360" height="120" rx="24" fill="#9C6A50" stroke="${LINE}" stroke-width="4"/>`;
  const cl=t>1.0?3*DECAY(t-1.0,6,20):0;g+=`<circle cx="540" cy="${(h-140+cl).toFixed(1)}" r="16" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  [[680,h-300,'加班費',0],[700,h-160,'獎金',1.5]].forEach(([x,y,l,ph])=>{const a=clamp((t-.6)*4);g+=`<g opacity="${(.85*a).toFixed(2)}" transform="translate(0,${(8*Math.sin(t*2.4+ph)).toFixed(1)})"><rect x="${x-90}" y="${y}" width="180" height="90" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3" stroke-dasharray="10 8"/>${T(x,y+56,l,32,700,SUBC)}</g>`});
  return g},
  sfx(t0,s,E){E(t0+.15,'glide',{f0:800,f1:400,dur:.25,g:.07});E(t0+.4,'glide',{f0:800,f1:400,dur:.25,g:.07});E(t0+1.0,'click')}}
