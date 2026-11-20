 stairs10:{draw(t,h){const N=+'10';   // 參數：階數＝連續下降幾年（10）；一級一級往下亮，滾球停在最後一級
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3ECE0"/>`;
  const x0=40,sw=(888-80)/N,top0=60,stepH=(h-top0-80)/N;let bx=0,by=0;
  for(let i=0;i<N;i++){const x=x0+i*sw,y=top0+i*stepH,u=t-.2-i*.16,on=u>0,k=clamp(u*6);
    g+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(sw+1).toFixed(1)}" height="${(h-y).toFixed(1)}" fill="${on?LAMP:'#E9DFC9'}" fill-opacity="${(on?(.35+.45*k):1).toFixed(2)}" stroke="${LINE}" stroke-width="3"/>`;
    g+=T(x+sw/2,y+38,String(i+1),32,700,on?TXT:SUBC);
    if(on&&u<.5)g+=`<rect x="${x.toFixed(1)}" y="${(y-3-6*Math.sin(Math.PI*u/.5)).toFixed(1)}" width="${sw.toFixed(1)}" height="6" fill="#FFFFFF" opacity=".7"/>`}
  // 球：每亮一級就從上一級滾落一級（落地小彈一下）
  const f=clamp((t-.2)/.16-0,0,N-1)+0,idx=Math.min(N-1,Math.floor((t-.2)/.16)),fr=((t-.2)/.16)-idx;
  if(t>.2){const i=idx<0?0:idx,x=x0+i*sw+sw/2,y=top0+i*stepH,pf=clamp(fr),bounce=i<N-1?-34*Math.sin(Math.PI*pf):-10*Math.abs(DECAY(t-(.2+(N-1)*.16),4,12));
    const nx=i<N-1?x+sw*pf:x,ny=(i<N-1?y+stepH*pf:y)+bounce;g+=`<circle cx="${nx.toFixed(1)}" cy="${(ny-18).toFixed(1)}" r="18" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`}
  g+=`<rect x="30" y="${h-70}" width="200" height="50" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(130,h-34,'第 1 年',30,700,TXT)+`<rect x="658" y="14" width="200" height="50" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(758,50,'第 10 年',30,700,TXT);
  return g},
  sfx(t0,s,E){for(let i=0;i<10;i++)E(t0+.2+i*.16,'tick',{g:.35});E(t0+1.9,'thump',{g:.35})}}
