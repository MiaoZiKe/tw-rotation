 yearwalk:{draw(t,h){const gy=h-70;let g=`<rect x="0" y="${gy}" width="888" height="70" fill="#E4D3B8"/><line x1="0" y1="${gy}" x2="888" y2="${gy}" stroke="${LINE}" stroke-width="4"/>`;
  const sc=(t*60)%80;for(let i=-1;i<12;i++){const x=i*80-sc+40;if(x>-10&&x<880)g+=`<line x1="${x.toFixed(1)}" y1="${gy+14}" x2="${x.toFixed(1)}" y2="${gy+34}" stroke="#B98A6A" stroke-width="5" stroke-linecap="round"/>`}
  g+=`<rect x="56" y="28" width="150" height="124" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><rect x="56" y="28" width="150" height="34" rx="14" fill="#E9B98A" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<4;i++){const u=((t*1.5+i*.25)%1),k=1-u;g+=`<g transform="translate(131 70) scale(1 ${Math.max(.02,k).toFixed(3)})" opacity="${(.35+.65*k).toFixed(2)}"><rect x="-58" y="0" width="116" height="${70-i*4}" rx="6" fill="${i%2?'#F3E6D0':'#FFFFFF'}" stroke="${LINE}" stroke-width="2"/></g>`}
  const lx=470;g+=`<line x1="${lx}" y1="48" x2="${lx}" y2="${gy}" stroke="${LAMP}" stroke-width="5" stroke-dasharray="14 12"/><rect x="${lx-52}" y="30" width="104" height="44" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(lx,62,'30 歲',30,700,TXT);
  const p=clamp((t-.2)/1.5),e=1-Math.pow(1-p,3),walk=p<1?Math.sin(t*16):0;
  const fig=(x0,x1,col,hair,lab,ph)=>{const x=x0+(x1-x0)*e,b=p<1?Math.abs(Math.sin(t*16+ph))*5:1.5*Math.sin(t*2+ph),y=gy-b,s=p<1?Math.sin(t*16+ph)*14:0;
   return `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)})"><line x1="-10" y1="-50" x2="${(-10+s).toFixed(1)}" y2="0" stroke="${LINE}" stroke-width="9" stroke-linecap="round"/><line x1="10" y1="-50" x2="${(10-s).toFixed(1)}" y2="0" stroke="${LINE}" stroke-width="9" stroke-linecap="round"/><rect x="-26" y="-130" width="52" height="86" rx="22" fill="${col}" stroke="${LINE}" stroke-width="4"/><circle cx="0" cy="-152" r="24" fill="#F3E6D0" stroke="${LINE}" stroke-width="4"/><path d="M-24 -156 q24 -34 48 0 q-24 -12 -48 0Z" fill="${hair}"/></g>`+T((x).toFixed(1),(y-196).toFixed(1),lab,32,700,TXT)};
  g+=fig(250,640,'#C9A27A','#8A5A44','男',0)+fig(150,540,'#F4B860','#8A5A44','女',1.6);
  if(t>1.7)g+=sparkle(700,gy-150,14,.3+.5*tw(t,2,3));
  return g},
  sfx(t0,s,E){for(let i=0;i<7;i++)E(t0+.25+i*.2,'tick',{g:.4});E(t0+1.7,'bell',{n:[21],g:.3})}}
