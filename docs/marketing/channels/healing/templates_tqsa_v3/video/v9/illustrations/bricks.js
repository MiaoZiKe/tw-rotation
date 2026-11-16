 bricks:{draw(t,h){let g=`<rect x="0" y="${h-40}" width="888" height="40" fill="#E4D3B8"/>`;
  for(let i=0;i<10;i++){const u=t-.1-i*.11,p=SPR(u,.5,16);if(u<=0)continue;const half=i===9,w=half?110*.47*2:220,row=Math.floor(i/2),col=i%2,x=(row%2?260:240)+col*230,y=h-40-38*(row+1)-(1-p)*60;
   g+=`<rect x="${x}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="34" rx="4" fill="${half?LAMP:'#B98A6A'}" stroke="${LINE}" stroke-width="2" opacity="${clamp(u*8)}" ${half?`transform="rotate(${(4*DECAY(u-.15,4,14)).toFixed(1)} ${x} ${y})"`:''}/>`}
  g+=`<rect x="560" y="30" width="290" height="92" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(705,92,'約 9.47 倍',48,700,TXT);
  g+=T(30,92,'1 塊＝1 年所得',44,400,SUBC,'start');
  return g},
  sfx(t0,s,E){for(let i=0;i<10;i+=2)E(t0+.1+i*.11+.1,'tick',{g:.6});E(t0+1.2,'thump',{g:.25})}}
