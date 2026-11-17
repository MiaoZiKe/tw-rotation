 envelopes:{draw(t,h){let g=`<rect x="0" y="${h-120}" width="888" height="120" fill="#D9C4A0"/>`;
  const env=(x,y,lab,col,flap)=>`<g transform="translate(${x},${y})"><rect x="0" y="0" width="300" height="190" rx="12" fill="${col}" stroke="${LINE}" stroke-width="4"/><path d="M0 0 L150 ${(100*Math.cos(flap)).toFixed(1)} L300 0" fill="${col}" stroke="${LINE}" stroke-width="3"/>${T(150,160,lab,36,700,TXT)}</g>`;
  const fo=Math.PI*clamp(SPR(t-.35,.5,12));const bill=clamp(SPR(t-.4,.55,11));
  if(fo>Math.PI/2)g+=`<rect x="${130}" y="${h-330-60*bill}" width="150" height="90" rx="6" fill="#CFE0C2" stroke="${LINE}" stroke-width="3"/>`+T(205,h-275-60*bill,'$',36,700,TXT);
  g+=env(80,h-320,'薪水','#FFFDF8',fo);
  const px=(1-SPR(t-.6,.6,10))*60;g+=env(508+px,h-300,'學貸帳單','#F3E6D0',0);
  const cu=t-1.0,ang=cu<0?0:-70*clamp(cu/1.2)+20*DECAY(cu,1.5,9)*(1-clamp(cu/1.2));g+=`<g transform="translate(444,${h-130}) rotate(${ang.toFixed(1)})"><ellipse cx="0" cy="-40" rx="16" ry="40" fill="#E0B070" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<path d="M700 ${h-330} q10 -24 0 -48" stroke="${LINE}" stroke-width="2" fill="none" opacity="${(.2+.2*tw(t,1,2.6)).toFixed(2)}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.4,'click');E(t0+.7,'glide',{f0:600,f1:350,dur:.25,g:.08});E(t0+2.2,'thump',{g:.22})}}
