 uniforms:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/><line x1="40" y1="70" x2="848" y2="70" stroke="${LINE}" stroke-width="8" stroke-linecap="round"/><line x1="60" y1="70" x2="60" y2="${h-50}" stroke="${LINE}" stroke-width="6"/><line x1="828" y1="70" x2="828" y2="${h-50}" stroke="${LINE}" stroke-width="6"/>`;
  const items=[['#E9B98A','圍裙'],['#FFFDF8','廚師'],['#F4B860','背心'],['#C9D3C9','超商'],['#B98A6A','倉儲']];
  items.forEach((it,i)=>{const a=.1+i*.2,u=t-a;if(u<0)return;const x=140+i*150,sl=(1-SPR(u,.55,12))*-80,sw=5*DECAY(u-.3,2.2,7)+2*DECAY(t-1.9-i*.1,2.5,8);
   g+=`<g transform="translate(${(x+sl).toFixed(1)},70) rotate(${sw.toFixed(1)})"><path d="M0 0 v18 M-36 40 l36 -22 l36 22" fill="none" stroke="${LINE}" stroke-width="4"/><path d="M-50 40 h100 l10 ${h-200} h-120Z" fill="${it[0]}" stroke="${LINE}" stroke-width="3"/>${T(0,140,it[1],32,700,TXT)}</g>`});
  return g},
  sfx(t0,s,E){[0,1,2,3,4].forEach(i=>E(t0+.1+i*.2+.15,'tick',{g:.6}))}}
