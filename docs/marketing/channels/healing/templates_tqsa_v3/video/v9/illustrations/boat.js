 boat:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F4E8D4"/><circle cx="720" cy="90" r="46" fill="#F4B860" opacity=".8"/>`;
  const wave=(x,ph,a)=>a*Math.sin(x/90+t*2.2+ph);let d=`M0 ${h}`;for(let x=0;x<=888;x+=24)d+=` L${x} ${(h-120+wave(x,0,14)).toFixed(1)}`;g+=`<path d="${d} L888 ${h}Z" fill="#C9D3C9" opacity=".7"/>`;
  const big=-46*DECAY(t-.3,1.5,4.2),by=h-150+wave(444,0,14)+big,rot=6*Math.cos(444/90+t*2.2)+8*DECAY(t-.3,1.5,4.2);
  g+=`<g transform="translate(444,${by.toFixed(1)}) rotate(${rot.toFixed(2)})"><path d="M-130 0 h260 l-40 54 h-180Z" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><line x1="0" y1="0" x2="0" y2="-170" stroke="${LINE}" stroke-width="7"/><path d="M6 -160 l100 120 h-100Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M-6 -150 l-80 104 h80Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`+
   `<path d="M0 -170 q${(20+6*Math.sin(t*6)).toFixed(1)} -8 34 ${(4*Math.sin(t*6)).toFixed(1)} l-34 12Z" fill="${LAMP}"/></g>`;
  d=`M0 ${h}`;for(let x=0;x<=888;x+=24)d+=` L${x} ${(h-90+wave(x,1.3,18)).toFixed(1)}`;g+=`<path d="${d} L888 ${h}Z" fill="#AFC0B6"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'glide',{f0:260,f1:520,dur:.45,g:.12});E(t0+.9,'thump',{g:.25})}}
