 ticket:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  const sl=(1-SPR(t-.2,.6,11))*-500;g+=`<g transform="translate(${sl.toFixed(1)},0)"><rect x="160" y="60" width="560" height="${h-140}" rx="18" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><line x1="560" y1="70" x2="560" y2="${h-90}" stroke="${LINE}" stroke-width="3" stroke-dasharray="10 10"/>`;
  g+=T(200,120,'推估車票',32,700,SUBC,'start')+T(200,200,'2028',56,700,TXT,'start');
  const cr=pr(t,.8,.25);if(cr>0)g+=`<line x1="196" y1="182" x2="${196+142*cr}" y2="182" stroke="${LAMP}" stroke-width="7"/>`;
  const nw=SPR(t-1.0,.45,15);if(t>1.0)g+=`<g transform="translate(260,262) scale(${Math.max(.01,nw).toFixed(3)})" opacity="${clamp((nw-.1)/.85).toFixed(3)}">${T(0,10,'2031',56,700,HINT)}</g>`;
  const on=t>.6&&t<1.0?1:0;g+=`<circle cx="640" cy="${(h-90)/2+30}" r="22" fill="${on?'#F4B860':FACE}" stroke="${LINE}" stroke-width="3"/></g>`;
  {const cy=Math.min(1,Math.max(0,(t-.35)/.4));g+=`<g opacity="${clamp(t*3)}"><rect x="740" y="${h-190}" width="130" height="56" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(805,h-150,'已撥補',30,700,TXT)}<circle cx="805" cy="${(h-300+110*cy*cy).toFixed(1)}" r="24" fill="#F4B860" stroke="${LINE}" stroke-width="3" opacity="${cy>=1?0:1}"/></g>`}
  const st=t<.55?-80*(1-EO(t/.55)):t<.8?-80*(1-(t-.55)/.25):6*DECAY(t-.8,6,18);g+=`<g transform="translate(0,${st.toFixed(1)})" opacity="${clamp(t*4)}"><rect x="400" y="${h-210}" width="100" height="50" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><rect x="430" y="${h-290}" width="40" height="80" rx="10" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:700,f1:350,dur:.3,g:.07});E(t0+.8,'thump',{g:.4});E(t0+1.0,'pop')}}
