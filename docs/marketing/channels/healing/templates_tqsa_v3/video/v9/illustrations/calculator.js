 calculator:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/><rect x="270" y="20" width="348" height="${h-70}" rx="28" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="300" y="44" width="288" height="70" rx="10" fill="#DCE3CF" stroke="${LINE}" stroke-width="3"/>`;
  const seq=[0,5,10,3,7,15],at=k=>.2+k*.2;let pressed=-1;seq.forEach((k,i)=>{if(t>=at(i)&&t<at(i)+.14)pressed=k});
  const shown=['7','70%','20','20 年','×','='][Math.min(5,Math.max(0,Math.floor((t-.2)/.2)))]||'';g+=T(570,96,t<.2?'0':shown,36,700,TXT,'end');
  for(let r=0;r<4;r++)for(let c=0;c<4;c++){const k=r*4+c,dn=k===pressed?5:0,eq=k===15&&t>1.2;g+=`<rect x="${300+c*74}" y="${(134+r*(h-210)/4+dn).toFixed(1)}" width="62" height="${((h-210)/4-12).toFixed(1)}" rx="10" fill="${eq?LAMP:'#F3EADB'}" stroke="${LINE}" stroke-width="2"/>`}
  const rl=10*Math.sin(t*2);g+=`<path d="M630 ${h-50} q60 ${-30-rl} 120 -40 v-120 q-60 10 -120 40Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><line x1="650" y1="${h-140}" x2="730" y2="${h-170}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i++)E(t0+.2+i*.2,'tick',{g:.7});E(t0+1.25,'bell',{n:[19],g:.35})}}
