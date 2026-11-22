 otfilter:{draw(t,h){const N=+'9',K=+'3';   // 參數：N 個人、前 K 個是「有加班」（約三分之一）；其餘 N-K 個淡掉＝不算進平均（2026-11-22 新做，加班片「只算有加班的人」）
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-50}" width="888" height="50" fill="#CDB896"/>`;
  const sp=84,x0=444-sp*(N-1)/2,cy=h-50-6,fk=pr(t,1.0,.5),pulse=t>2.2?.5+.5*Math.sin((t-2.2)*4):0;
  for(let i=0;i<N;i++){const u=t-.1-i*.07,p=SPR(u,.4,13);if(u<=0)continue;const x=x0+i*sp,A=i<K,op=A?1:1-.62*fk,dy=(1-p)*-40;
   g+=`<g transform="translate(${x.toFixed(1)},${(cy+dy).toFixed(1)})" opacity="${(clamp(u*6)*op).toFixed(3)}"><circle cx="0" cy="-92" r="20" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M-28 0 q0 -62 28 -62 q28 0 28 62Z" fill="${A&&fk>0?LAMP:'#B98A6A'}" stroke="${LINE}" stroke-width="3"/></g>`}
  if(fk>0){const xa=x0-sp/2+4,w=sp*K-8,y=cy-150;g+=`<rect x="${xa.toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="160" rx="18" fill="none" stroke="${LAMP}" stroke-width="${(5+2*pulse).toFixed(1)}" stroke-dasharray="14 9" ${draw(fk)}/>`;
   g+=`<g opacity="${pr(t,1.3,.3)}">${T(xa+w/2,y-18,'有加班：算',32,700,HINT)}${T(x0+sp*(K+(N-K-1)/2),y-18,'沒加班：不算',32,700,SUBC)}</g>`}
  return g},
  sfx(t0,s,E){for(let i=0;i<9;i++)E(t0+.15+i*.07,'tick',{g:.3});E(t0+1.0,'glide',{f0:500,f1:800,dur:.4,g:.06})}}
