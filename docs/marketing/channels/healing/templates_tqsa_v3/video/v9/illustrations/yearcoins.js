 yearcoins:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  // s3 一年 12 格存錢格：1～12 月十二個小格子排成一排，每格依序落下一枚「1,400」硬幣（0.2 起每 0.1 秒，落地彈一下），右上計數牌跟著加到 16,800（2026-11-27 新做，最低工資）
  const n=12,cw=64,x0=444-n*cw/2,base=h-80;let k=0;
  g+=`<rect x="${x0-14}" y="${base-120}" width="${n*cw+28}" height="128" rx="16" fill="#D9C4A0" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<n;i++){const x=x0+i*cw+cw/2;g+=`<rect x="${x-26}" y="${base-106}" width="52" height="96" rx="8" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/>`+T(x,base+40,(i+1)+'月',24,400,SUBC);
   const u=t-.2-i*.1;if(u>0){k++;const p=clamp(u/.22),yy=u<.22?(base-260+(200)*p*p):(base-60-10*Math.abs(DECAY(u-.22,5,14)));g+=`<ellipse cx="${x}" cy="${yy.toFixed(1)}" rx="22" ry="22" fill="#E0B070" stroke="${LINE}" stroke-width="2"/>`}}
  g+=`<rect x="584" y="22" width="270" height="76" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(719,74,'+'+F1(1400*k),40,700,k===n?TXT:SUBC);
  g+=T(150,74,'一年 12 個月',32,700,TXT);
  if(k===n){const q=clamp((t-1.5)/.3);g+=`<rect x="580" y="18" width="278" height="84" rx="16" fill="none" stroke="${LAMP}" stroke-width="6" ${draw(q)}/>`}
  return g},
  sfx(t0,s,E){for(let i=0;i<12;i++)E(t0+.42+i*.1,'tick',{g:.3});E(t0+1.55,'bell',{n:[21],g:.3})}}
