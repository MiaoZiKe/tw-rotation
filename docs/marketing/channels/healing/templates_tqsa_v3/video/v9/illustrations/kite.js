 kite:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F4E6D0"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const p=SPR(t-.15,.5,6),kx=620-140*p,ky=h-120-(h-220)*p,rot=-10+8*Math.sin(t*2.4);
  g+=`<path d="M160 ${h-80} Q ${(kx-160).toFixed(1)} ${(ky+160).toFixed(1)} ${kx.toFixed(1)} ${(ky+50).toFixed(1)}" fill="none" stroke="${LINE}" stroke-width="2"/>`;
  let tail=`M${kx} ${ky+60}`;for(let i=1;i<=4;i++)tail+=` L${(kx+18*Math.sin(t*4+i)+i*10).toFixed(1)} ${(ky+60+i*34).toFixed(1)}`;g+=`<path d="${tail}" fill="none" stroke="${LINE}" stroke-width="2"/>`;
  for(let i=1;i<=4;i++)g+=`<path d="M${(kx+18*Math.sin(t*4+i)+i*10-10).toFixed(1)} ${(ky+60+i*34-6).toFixed(1)} l20 12 l0 -12 l-20 12Z" fill="${i%2?LAMP:'#E9B98A'}"/>`;
  g+=`<g transform="rotate(${rot.toFixed(1)} ${kx.toFixed(1)} ${ky.toFixed(1)})"><path d="M${kx} ${ky-70} l50 60 l-50 70 l-50 -70Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><line x1="${kx}" y1="${ky-70}" x2="${kx}" y2="${ky+60}" stroke="${LINE}" stroke-width="2"/><line x1="${kx-50}" y1="${ky-10}" x2="${kx+50}" y2="${ky-10}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<g transform="translate(160,${h-80}) rotate(${(t*200).toFixed(0)})"><circle r="24" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><line x1="-24" y1="0" x2="24" y2="0" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="600" y="${h-150}" width="220" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(710,h-104,'25–29 歲',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.15,'glide',{f0:300,f1:800,dur:.6,g:.08})}}
