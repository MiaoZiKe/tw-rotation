 scale:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  const drop=clamp((t-.4)/.3),land=t>.7,sink=land?14*(1-Math.exp(-(t-.7)*6))+8*DECAY(t-.7,4,14):0;
  g+=`<rect x="250" y="${h-150}" width="388" height="90" rx="16" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="360" y="${h-128}" width="168" height="50" rx="8" fill="#3A3836"/>`;
  const v=land?Math.round(1400*clamp((t-.7)/.5)):0,flick=t>.7&&t<1.2?Math.floor(t*30)%2:0;g+=T(444,h-90,'+'+F1(v),34,700,flick?'#FFE9B8':'#F4B860');
  g+=`<g transform="translate(0,${sink.toFixed(1)})"><rect x="210" y="${h-180}" width="468" height="24" rx="10" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<7;i++)g+=`<ellipse cx="${330+(i%4)*60+(i>3?30:0)}" cy="${h-196-(i>3?20:0)}" rx="34" ry="12" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`;
  g+=`</g>`;const cy=drop<1?(h-440)+(h-270-(h-440))*drop*drop:(h-270+sink-12*Math.abs(DECAY(t-.7,4,12)));if(t>.4)g+=`<g transform="translate(560,${cy.toFixed(1)})"><circle r="64" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,12,'+1,400',32,700,'#FFFFFF')}</g>`;
  [[150,90],[740,120]].forEach(([x,y],i)=>g+=sparkle(x,y,12,.3+.4*tw(t,i*3,3)));
  return g},
  sfx(t0,s,E){E(t0+.7,'thump',{g:.4});E(t0+.75,'tick');E(t0+1.2,'bell',{n:[21],g:.35})}}
