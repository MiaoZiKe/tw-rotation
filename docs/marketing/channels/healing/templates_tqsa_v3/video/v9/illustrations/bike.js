 bike:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F6E4C8"/><rect x="0" y="${h-110}" width="888" height="110" fill="#CDB896"/>`;
  g+=`<circle cx="730" cy="110" r="56" fill="#F4B860" opacity=".75"/>`;
  for(let i=0;i<4;i++){const x=((i*260-t*120)%1040+1040)%1040-80;g+=`<line x1="${x}" y1="${h-110}" x2="${x}" y2="${h-330}" stroke="#A98C70" stroke-width="6"/><circle cx="${x}" cy="${h-338}" r="12" fill="#FFF1D2" stroke="#A98C70" stroke-width="2"/>`}
  for(let i=0;i<6;i++){const x=((i*170-t*220)%1020+1020)%1020-60;g+=`<rect x="${x}" y="${h-62}" width="80" height="8" rx="4" fill="#FFFDF8" opacity=".7"/>`}
  const bx=380-420*(1-SPR(t-.1,.55,8)),by=h-150+(t>.1?2*Math.sin(t*14):0),rot=t*6;
  const wheel=(cx)=>`<g transform="translate(${cx},0)"><circle r="62" fill="none" stroke="${LINE}" stroke-width="7"/>${[0,1,2,3].map(k=>`<line x1="0" y1="0" x2="${(62*Math.cos(rot+k*Math.PI/4)).toFixed(1)}" y2="${(62*Math.sin(rot+k*Math.PI/4)).toFixed(1)}" stroke="${LINE}" stroke-width="2"/><line x1="0" y1="0" x2="${(-62*Math.cos(rot+k*Math.PI/4)).toFixed(1)}" y2="${(-62*Math.sin(rot+k*Math.PI/4)).toFixed(1)}" stroke="${LINE}" stroke-width="2"/>`).join('')}</g>`;
  const sw=8*DECAY(t-.9,2.5,10);
  g+=`<g transform="translate(${bx.toFixed(1)},${by.toFixed(1)})">${wheel(-100)}${wheel(120)}<path d="M-100 0 L0 -10 L60 -100 L-40 -100Z M0 -10 L120 0 M60 -100 L80 -140 h40 M-40 -100 L-50 -130 h-40" fill="none" stroke="${LAMP}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>`+
   `<g transform="rotate(${sw.toFixed(1)} 120 -140)"><path d="M100 -140 h70 l-10 60 h-50Z" fill="#E9C9A6" stroke="${LINE}" stroke-width="3"/><rect x="112" y="-170" width="46" height="34" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/></g></g>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:300,f1:700,dur:.5,g:.08});E(t0+.6,'tick');E(t0+.9,'bell',{n:[24],g:.3})}}
