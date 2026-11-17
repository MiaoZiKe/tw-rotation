 trail:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><path d="M0 ${h-40} q240 -150 480 -170 q220 -20 408 -150 V${h} H0Z" fill="#CDB896"/><path d="M80 ${h} q200 -130 400 -190 q200 -60 360 -170" fill="none" stroke="#E9DFC9" stroke-width="28" stroke-linecap="round"/>`;
  for(let k=0;k<5;k++){const u=((t*.4+k/5)%1),x=80+760*u,y=h-(130+260*u);g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6" fill="#FFF4D6" opacity="${(.8*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  const p=SPR(t-.3,.45,13),sw=8*DECAY(t-.55,2,7);g+=`<g transform="translate(240,${(h-110+(1-p)*120).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-150" stroke="#8A5A44" stroke-width="10"/><g transform="rotate(${sw.toFixed(1)} 0 -140)"><path d="M-10 -170 h170 l26 26 l-26 26 h-170Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(78,-133,'下班時間',32,700,TXT)}</g></g>`;
  const f=SPR(t-.9,.45,15);if(t>.9)g+=`<g transform="translate(640,${(h-250+(1-f)*-60).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-90" stroke="${LINE}" stroke-width="5"/><path d="M0 -90 h70 l-14 22 l14 22 h-70Z" fill="${LAMP}"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'thump',{g:.3});E(t0+.9,'tick')}}
