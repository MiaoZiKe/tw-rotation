 rateboard:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-110}" width="888" height="110" fill="#E4D3B8"/>`;
  g+=`<rect x="90" y="40" width="708" height="300" rx="22" fill="#4A4744" stroke="${LINE}" stroke-width="4"/><rect x="112" y="62" width="664" height="256" rx="14" fill="#3A3836"/>`;
  g+=T(444,118,'就學貸款・學生負擔利率',34,700,'#F3DDB8');
  const p=EO((t-.3)/.8),v=1.775-1*p,str=v.toFixed(3)+'%';g+=`<clipPath id="rbc"><rect x="130" y="140" width="628" height="160"/></clipPath><g clip-path="url(#rbc)">`;
  const jit=t>.3&&t<1.1?Math.sin(t*90)*3:0;g+=T(444,262+jit,str,130,700,p>.98?'#F4B860':'#FFE9B8')+`</g>`;
  for(let i=0;i<14;i++){const x=120+i*49,on=clamp((t-.2-i*.05)*6);g+=`<circle cx="${x}" cy="52" r="6" fill="#F4B860" opacity="${(.25+.75*on*(.75+.25*tw(t,i,3))).toFixed(2)}"/>`}
  // 叫號燈
  const bl=t>1.3&&t<1.6?1:0;g+=`<rect x="650" y="${h-170}" width="120" height="64" rx="12" fill="${bl?'#F4B860':'#D8C6A8'}" stroke="${LINE}" stroke-width="3"/>`+T(710,h-126,'032',32,700,TXT)+(bl?glow(710,h-138,90,.5):'');
  // 申請書（掀角：衰減擺動）
  const fl=10*DECAY(t-.6,1.6,7)+6*DECAY(t-1.9,1.8,8);g+=`<g transform="translate(130,${h-150})"><rect x="0" y="0" width="300" height="120" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3" transform="rotate(-4)"/>`+T(140,46,'申請書',32,700,TXT)+`<line x1="24" y1="74" x2="250" y2="62" stroke="${LINE}" stroke-width="2" opacity=".5"/><path d="M270 ${-20} l30 ${(18+fl).toFixed(1)} l-34 4Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<path d="M560 ${h-60} q12 -30 0 -60" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.25+.2*tw(t,0,2.4)).toFixed(2)}"/><rect x="530" y="${h-60}" width="60" height="44" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  return g},
  sfx(t0,s,E){for(let k=0;k<6;k++)E(t0+.3+k*.13,'tick',{g:.5});E(t0+1.1,'bell',{n:[19],g:.45});E(t0+1.3,'click')}}
