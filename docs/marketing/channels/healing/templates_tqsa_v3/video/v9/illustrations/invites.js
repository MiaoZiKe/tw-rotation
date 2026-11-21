 invites:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#C9A27A"/>`;
  for(let i=0;i<6;i++){const u=t-.1-i*.15,p=SPR(u,.5,14);if(u<=0)continue;const x=300+i*10+(1-p)*500,y=h-110-i*14,rt=-6+i*2.4;g+=`<g transform="translate(${x.toFixed(1)},${y}) rotate(${rt.toFixed(1)})"><rect x="-120" y="-80" width="240" height="140" rx="8" fill="${i%2?'#D9822B':'#C9693E'}" stroke="${LINE}" stroke-width="3"/><path d="M-120 -80 l120 70 l120 -70" fill="none" stroke="#F4D0A0" stroke-width="3"/></g>`}
  const sw=t>1.05?SPR(t-1.05,.45,16):0;if(t>1.05)g+=glow(360,h-210,70,.5*(1-clamp(t-1.3)))+`<circle cx="360" cy="${h-200}" r="${(22*Math.max(.01,sw)).toFixed(1)}" fill="#F4B860" stroke="${LINE}" stroke-width="3"/>`;
  let d='M40 40';for(let x=40;x<=848;x+=24)d+=` L${x} ${(40+14*Math.sin(x/60+t*3)).toFixed(1)}`;g+=`<path d="${d}" fill="none" stroke="${LAMP}" stroke-width="4"/>`;
  for(let i=0;i<9;i++){const x=70+i*94,y=40+14*Math.sin(x/60+t*3);g+=`<path d="M${x-14} ${y.toFixed(1)} l14 30 l14 -30Z" fill="${i%2?'#F4D0A0':'#E9B98A'}"/>`}
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i+=2)E(t0+.1+i*.15+.15,'tick',{g:.6});E(t0+1.05,'thump',{g:.3});E(t0+1.1,'sparkle',{n:[24]})}}
