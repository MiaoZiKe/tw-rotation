 forsale:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/>`;
  const cl=(t*16)%1000;g+=`<ellipse cx="${(120+cl)%1000-60}" cy="70" rx="80" ry="24" fill="#FFFDF8" opacity=".8"/><ellipse cx="${(640+cl*.6)%1000-60}" cy="110" rx="60" ry="18" fill="#FFFDF8" opacity=".7"/>`;
  g+=`<rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  g+=`<rect x="240" y="80" width="408" height="${h-140}" fill="#E9D9BF" stroke="${LINE}" stroke-width="4"/>`;
  for(let r=0;r<7;r++)for(let c=0;c<4;c++)g+=`<rect x="${270+c*94}" y="${110+r*52}" width="60" height="34" rx="3" fill="#C9D3C9" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="410" y="${h-130}" width="68" height="70" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`;
  [80,720].forEach((x,i)=>g+=`<rect x="${x}" y="${h-200-i*40}" width="${88}" height="${140+i*40}" fill="#D9C4A0" stroke="${LINE}" stroke-width="3"/>`);
  const un=SPR(t-.2,.6,9),L=260*un,sw=6*DECAY(t-.6,1.6,6)+3*Math.sin(t*3);g+=`<g transform="rotate(${sw.toFixed(2)} 600 84)"><rect x="560" y="84" width="80" height="${L.toFixed(1)}" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${L>200?T(600,170,'售',44,700,'#FFFFFF')+T(600,240,'屋',44,700,'#FFFFFF'):''}</g><rect x="548" y="74" width="104" height="14" rx="4" fill="${LINE}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:900,f1:400,dur:.5,g:.08});E(t0+.7,'thump',{g:.25})}}
