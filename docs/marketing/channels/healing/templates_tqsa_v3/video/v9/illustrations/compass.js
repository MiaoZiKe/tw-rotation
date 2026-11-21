 compass:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><path d="M80 ${h-60} l200 -60 l200 40 l200 -50 l140 30 v80 h-740Z" fill="#E9DFC9" stroke="${LINE}" stroke-width="2"/>`;
  const cx=330,cy=200;g+=`<circle cx="${cx}" cy="${cy}" r="140" fill="#FFFDF8" stroke="#8A5A44" stroke-width="12"/>`;
  [['北',0],['東',90],['南',180],['西',270]].forEach(([l,a])=>{const r=a*Math.PI/180;g+=T(cx+104*Math.sin(r),cy-104*Math.cos(r)+12,l,32,700,SUBC)});
  const ang=t<.2?20:20+340*EO((t-.2)/1.2)+60*DECAY(t-.2,1.6,7);g+=`<g transform="rotate(${ang.toFixed(1)} ${cx} ${cy})"><path d="M${cx} ${cy-90} l16 90 l-16 16 l-16 -16Z" fill="${LAMP}"/><path d="M${cx} ${cy+90} l16 -74 h-32Z" fill="#B9B2A8"/></g><circle cx="${cx}" cy="${cy}" r="10" fill="${LINE}"/>`;
  const fl=1-SPR(t-.6,.7,6),x=650+260*fl,y=150+16*Math.sin(t*3);g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><path d="M-60 0 l60 -20 l50 30 l-50 -6Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/><path d="M0 -20 l-10 40 l10 4Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:400,f1:900,dur:.9,g:.06});E(t0+1.4,'tick')}}
