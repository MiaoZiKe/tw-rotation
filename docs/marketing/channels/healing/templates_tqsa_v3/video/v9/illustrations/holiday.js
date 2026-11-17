 holiday:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/>`;
  const sp=SPR(t-.05,.6,8);let d='M30 80';for(let x=30;x<=30+828*sp;x+=20)d+=` L${x} ${(80+40*Math.sin(Math.PI*(x-30)/828)).toFixed(1)}`;g+=`<path d="${d}" fill="none" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<9;i++){const x=60+i*96;if(x>30+828*sp)continue;const y=80+40*Math.sin(Math.PI*(x-30)/828),nw=i===2||i===5||i===7,a=nw?.6+[2,5,7].indexOf(i)*.2:0,p=nw?SPR(t-a,.45,15):1;if(nw&&t<a)continue;const sw=6*DECAY(t-(nw?a:.3),2,9);
   g+=`<g transform="translate(${x},${y.toFixed(1)}) rotate(${sw.toFixed(1)}) scale(${Math.max(.01,p).toFixed(3)})" opacity="${clamp((p-.1)/.85).toFixed(3)}"><path d="M-36 0 h72 l-36 70Z" fill="${nw?LAMP:'#E9D9BF'}" stroke="${LINE}" stroke-width="2"/>${nw?T(0,36,'假',32,700,'#FFFFFF'):''}</g>`}
  g+=`<rect x="0" y="${h-90}" width="888" height="90" fill="#D9C4A0"/><rect x="560" y="${h-170}" width="240" height="90" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(680,h-112,'2025 新增',32,700,TXT);
  return g},
  sfx(t0,s,E){[.6,.8,1.0].forEach(x=>E(t0+x,'pop'))}}
