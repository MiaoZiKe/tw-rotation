 queue:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  for(let i=0;i<9;i++){const u=t-.08-i*.07,p=SPR(u,.5,15);if(u<=0)continue;const x=84+i*90,H=80+i*12,mid=i===4,on=mid?clamp((t-.9)*5):0;
   g+=`<g transform="translate(${x},${(h-50+(1-p)*30).toFixed(1)})" opacity="${clamp(u*8)}">${on?glow(0,-H/2,80,.55*on):''}<circle cx="0" cy="${-H-6}" r="20" fill="${on>.5?LAMP:'#B98A6A'}"/><rect x="-24" y="${-H+16}" width="48" height="${H-16}" rx="20" fill="${on>.5?LAMP:'#C9A27A'}"/></g>`}
  const f=SPR(t-1.05,.45,16);if(t>1.05)g+=`<g transform="translate(444,${h-50-128-60}) scale(${Math.max(.01,f).toFixed(3)})" opacity="${clamp((f-.1)/.85).toFixed(3)}"><line x1="0" y1="20" x2="0" y2="-46" stroke="${LINE}" stroke-width="6"/><path d="M0 -46 h66 v44 h-66Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(33,-12,'中',34,700,HINT)}</g>`;
  g+=T(84,h-12,'低',32,700,SUBC)+T(804,h-12,'高',32,700,SUBC);
  return g},
  sfx(t0,s,E){for(let i=0;i<9;i+=2)E(t0+.08+i*.07+.1,'tick',{g:.5});E(t0+.9,'bell',{n:[19],g:.4});E(t0+1.1,'pop')}}
