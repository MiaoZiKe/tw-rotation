 balloon:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F5E6CF"/>`;
  for(let i=0;i<3;i++){const y=((80+i*170+t*30)%(h+60))-30;g+=`<ellipse cx="${120+i*260}" cy="${y.toFixed(1)}" rx="${70-i*8}" ry="22" fill="#FFFDF8" opacity=".8"/>`}
  const rx=760,top=60,bot=h-40,sy=v=>bot-(bot-top)*(v-20)/(40-20);g+=`<line x1="${rx}" y1="${top}" x2="${rx}" y2="${bot}" stroke="${LINE}" stroke-width="4"/>`;
  [20,25,30,35,40].forEach(v=>g+=`<line x1="${rx}" y1="${sy(v)}" x2="${rx+(v===30?40:24)}" y2="${sy(v)}" stroke="${v===30?LAMP:LINE}" stroke-width="${v===30?6:3}"/>`+T(rx+70,sy(v)+11,String(v),32,v===30?700:400,v===30?HINT:SUBC,'start'));
  const p=SPR(t-.2,.7,4.5),y=(bot+120)-((bot+120)-sy(32.4))*p,sw=6*Math.sin(t*2.2)*.6+5*DECAY(t-1.3,1.5,6);
  g+=`<line x1="${rx-10}" y1="${(y+150).toFixed(1)}" x2="${rx-10}" y2="${(y+150).toFixed(1)}"/>`;
  g+=`<g transform="translate(420,${y.toFixed(1)}) rotate(${sw.toFixed(1)} 0 150)"><path d="M0 -120 c90 0 120 70 100 130 c-16 44 -60 70 -70 90 h-60 c-10 -20 -54 -46 -70 -90 c-20 -60 10 -130 100 -130Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><path d="M0 -120 c-30 40 -34 140 -20 220 M0 -120 c30 40 34 140 20 220" fill="none" stroke="#F4D0A0" stroke-width="6"/>`+
   `<line x1="-30" y1="100" x2="-22" y2="140" stroke="${LINE}" stroke-width="3"/><line x1="30" y1="100" x2="22" y2="140" stroke="${LINE}" stroke-width="3"/><rect x="-34" y="140" width="68" height="44" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  if(t>.2&&t<1.6)for(let k=0;k<3;k++){const u=((t*2+k/3)%1);g+=`<circle cx="${(420+Math.sin(k*2)*14).toFixed(1)}" cy="${(y+200+u*60).toFixed(1)}" r="${(6*(1-u)).toFixed(1)}" fill="#FFFDF8" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=T(rx-20,top+40,'歲',32,700,SUBC,'end');
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:220,f1:520,dur:1.0,g:.1});E(t0+.85,'tick');E(t0+1.3,'bell',{n:[19],g:.35})}}
