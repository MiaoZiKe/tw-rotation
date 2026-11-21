 printer:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#E4D3B8"/>`;
  const out=Math.floor(clamp((t-.2)/1.0)*6)/6*250+(t>.2&&t<1.2?6*Math.sin(t*60):0),py=h-250-out;
  g+=`<g><rect x="300" y="${py.toFixed(1)}" width="288" height="${(out+40).toFixed(1)}" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  const lines=[['2027 年',''],['最低月薪',''],['30,900 元','hi']];lines.forEach((l,i)=>{const y=py+60+i*70;if(y>h-240)return;g+=l[1]?`<rect x="320" y="${y-44}" width="248" height="60" rx="10" fill="${LAMP}" opacity=".9"/>`+T(444,y,l[0],38,700,'#FFFFFF'):T(444,y,l[0],34,700,TXT)});
  g+=`<path d="M300 ${py} l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12 l24 -12 l24 12" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<rect x="230" y="${h-250}" width="428" height="170" rx="26" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="280" y="${h-262}" width="328" height="24" rx="8" fill="#4A4744"/>`;
  const led=t<1.2?(Math.floor(t*8)%2):1;g+=`<circle cx="610" cy="${h-180}" r="12" fill="${led?'#9CC08A':'#6E7E66'}" stroke="${LINE}" stroke-width="2"/>`+T(330,h-150,'薪資單',32,700,'#FFFFFF','start');
  const cut=t>1.35?-20*DECAY(t-1.35,4,12):0;g+=`<rect x="276" y="${h-268+cut}" width="336" height="10" rx="4" fill="${LINE}"/>`;
  g+=`<rect x="80" y="${h-160}" width="110" height="70" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M100 ${h-160} v-40 h70 v40" fill="none" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<5;i++){const u=((t*.3+i/5)%1);g+=`<circle cx="${(700+i*30+10*Math.sin(t*2+i)).toFixed(1)}" cy="${(h-140-u*200).toFixed(1)}" r="4" fill="#E0B070" opacity="${(.7*Math.sin(Math.PI*u)).toFixed(2)}"/>`}
  return g},
  sfx(t0,s,E){for(let k=0;k<6;k++)E(t0+.2+k*.167,'tick',{g:.6});E(t0+1.35,'click');E(t0+1.4,'bell',{n:[19],g:.4})}}
