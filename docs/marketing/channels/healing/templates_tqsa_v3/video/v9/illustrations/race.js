 race:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/>`;
  [0,1].forEach(i=>{const y=70+i*140;g+=`<rect x="40" y="${y}" width="808" height="110" rx="14" fill="#D9C4A0"/><line x1="60" y1="${y+55}" x2="828" y2="${y+55}" stroke="#FFFDF8" stroke-width="4" stroke-dasharray="20 18"/>`});
  g+=`<line x1="760" y1="60" x2="760" y2="330" stroke="${LINE}" stroke-width="4" stroke-dasharray="12 10"/>`;
  [[0,.244,LAMP],[1,.318,'#B98A6A']].forEach(([i,sp,c])=>{const y=70+i*140+55,run=clamp((t-.2)/2.2),p=1-Math.pow(1-run,3),x=250+(440*sp/.318)*p*.95;
   g+=`<g transform="translate(${x.toFixed(1)},${y})"><rect x="0" y="-30" width="120" height="44" rx="14" fill="${c}" stroke="${LINE}" stroke-width="3"/><rect x="24" y="-54" width="64" height="30" rx="10" fill="${c}" stroke="${LINE}" stroke-width="3"/><circle cx="26" cy="18" r="14" fill="${LINE}"/><circle cx="96" cy="18" r="14" fill="${LINE}"/></g>`;
   if(run<1)for(let k=0;k<3;k++){const u=((t*1.5+k/3)%1);g+=`<circle cx="${(x-14-u*50).toFixed(1)}" cy="${(y+4-u*14).toFixed(1)}" r="${(8+u*8).toFixed(1)}" fill="#FFFDF8" opacity="${(.6*(1-u)*clamp(t-.2)*(1-run)).toFixed(2)}"/>`}});
  g+=`<rect x="52" y="86" width="190" height="44" rx="10" fill="${FACE3}" opacity=".9"/>`+T(62,120,'未滿 25 歲',32,700,HINT,'start')+`<rect x="52" y="226" width="170" height="44" rx="10" fill="${FACE3}" opacity=".9"/>`+T(62,260,'25–29 歲',32,700,TXT,'start');
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:300,f1:800,dur:.6,g:.1});E(t0+.2,'click')}}
